"""List things worth a note in each dataset, from profile.json (no data rescan).

Usage: python find_anomalies.py manifest.json profile.json [KEY ...]

Flags: rejected/short lines, empty columns, columns under 5% filled, negative numbers, year columns
outside 1800..max_year (9999-style placeholders, typos), dates after max_year, values that are not
numbers/dates in a numeric/date column, placeholder runs of zeros, columns that are always zero, and,
for datasets with a `compare`, columns added/dropped and fill-rate or type changes of 5+ points.
Use the output to decide which notes to write; confirm exact counts with a DuckDB query before quoting them.
"""
import json, re, sys

m = json.load(open(sys.argv[1]))
P = json.load(open(sys.argv[2]))
keys = sys.argv[3:] or [k for k in m["datasets"] if k in P]
max_year = m.get("max_year", 2026)
ZEROS = re.compile(r"^0{12,}$")

for k in keys:
    v, d = P[k], m["datasets"].get(k, {})
    rows = v["rows"] or 1
    out = []
    if v.get("rejected"):
        out.append(f"{v['rejected']} lines rejected by the reader, e.g. {v.get('rej_sample', [])[:1]}")
    for c in v["columns"]:
        n, t, s = c["name"], c["type"], c.get("stats") or {}
        fill = c["nonnull"] / rows
        if t == "Empty":
            out.append(f"{n}: blank in every row")
            continue
        if fill < .05:
            out.append(f"{n}: only {c['nonnull']:,} rows filled ({fill:.1%})")
        if s.get("unparsed"):
            out.append(f"{n} ({t}): {s['unparsed']:,} values are not {'dates' if t == 'Date' else 'numbers'}")
        if t == "Date":
            if s.get("future"):
                out.append(f"{n}: {s['future']:,} dates after {max_year} (range {s.get('min')}..{s.get('max')})")
            if s.get("min", "9") < "1850":
                out.append(f"{n}: earliest date {s['min']} (placeholder or typo?)")
        if t in ("Integer", "Decimal", "Percent") and s:
            if s.get("min") is not None and s["min"] < 0:
                out.append(f"{n}: negative values (min {s['min']:,})")
            if "year" in n.lower() and s.get("max") and (s["max"] > max_year or 0 < s.get("min", 0) < 1800):
                out.append(f"{n}: year range {s.get('min')}..{s.get('max')} (9999/typo placeholders?)")
            if s.get("zeros") == c["nonnull"] == v["rows"]:
                out.append(f"{n}: filled but always zero")
        if any(ZEROS.match(str(x[0] or "")) for x in c.get("top", [])[:3]):
            out.append(f"{n}: a run of zeros is used as a placeholder ({c['top'][0]})")
    cmp = d.get("compare")
    if cmp and cmp in P:
        ren = {o: nw for nw, o in (d.get("renames") or {}).items()}
        old = {ren.get(c["name"], c["name"]): c for c in P[cmp]["columns"]}
        new = {c["name"]: c for c in v["columns"]}
        if set(new) - set(old):
            out.append(f"new vs {cmp}: {sorted(set(new) - set(old))}")
        if set(old) - set(new):
            out.append(f"dropped vs {cmp}: {sorted(set(old) - set(new))}")
        out.append(f"rows {P[cmp]['rows']:,} -> {v['rows']:,}")
        for n in set(new) & set(old):
            a, b = old[n], new[n]
            fa, fb = a["nonnull"] / (P[cmp]["rows"] or 1), b["nonnull"] / rows
            if abs(fa - fb) >= .05:
                out.append(f"{n}: filled {fa:.1%} -> {fb:.1%}")
            if a["type"] != b["type"]:
                out.append(f"{n}: type {a['type']} -> {b['type']}")
    print(f"== {k} ({v['rows']:,} rows, {len(v['columns'])} cols)")
    for line in out:
        print("  -", line)
