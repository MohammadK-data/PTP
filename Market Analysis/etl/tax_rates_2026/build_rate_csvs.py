"""Merge per-county tax rate pulls into county_rates.csv (Part 1) and
jurisdiction_rates.csv (Part 2).

Inputs:  <parts_dir>/<county>_jurisdiction.csv and <county>_summary.json
Outputs: <out_dir>/jurisdiction_rates.csv, <out_dir>/county_rates.csv

Part 1 method: total levy of all units in the county / county unit's taxable
value * 100. Levy per unit = published levy_usd, else adopted rate x taxable
value / 100. If too few units carry a taxable value, fall back to the
typical commercial rate stack and say so in `method`.

Usage: python build_rate_csvs.py <parts_dir> <out_dir>
"""

import csv
import re
import json
import sys
from pathlib import Path

COUNTIES = ["dallas", "denton", "elpaso", "fortbend", "montgomery", "rockwall", "tarrant", "travis"]
YEARS = ["2025", "2026"]
JUR_COLS = [
    "county", "tax_year", "taxing_unit_name", "unit_type", "cad_entity_code",
    "adopted_rate_per_100", "mo_rate", "is_rate", "taxable_value_usd", "levy_usd",
    "source_name", "source_url", "date_collected",
]
CTY_COLS = [
    "county", "tax_year", "avg_combined_rate_per_100", "total_levy_usd",
    "total_taxable_value_usd", "method", "source_name", "source_url",
    "date_collected", "notes",
]
DATE = "2026-11-18"
# Share of the summed adopted rates that must sit on units with a taxable
# value before the levy/taxable result is trusted.
MIN_LEVY_COVERAGE = 0.80


def num(v):
    try:
        s = str(v).replace(",", "").replace("$", "").strip()
        return float(s) if s else None
    except ValueError:
        return None


def main(parts_dir: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    jur_rows, cty_rows = [], []

    for c in COUNTIES:
        jf, sf = parts_dir / f"{c}_jurisdiction.csv", parts_dir / f"{c}_summary.json"
        if not jf.exists():
            print(f"MISSING {jf.name}")
            continue
        with jf.open(newline="", encoding="utf-8-sig") as fh:
            rows = [{k: (r.get(k) or "").strip() for k in JUR_COLS} for r in csv.DictReader(fh)]
        # PIDs charge assessments, not ad valorem tax; other counties already omit them.
        rows = [r for r in rows if not re.search(r"\bPID\b|public improvement", r["taxing_unit_name"], re.I)]
        jur_rows.extend(rows)
        # 2025 rate per unit, used only in Part 1 when a 2026 rate is missing.
        prior = {(r["cad_entity_code"] or r["taxing_unit_name"]): num(r["adopted_rate_per_100"])
                 for r in rows if r["tax_year"] == "2025"}
        summary = json.loads(sf.read_text()) if sf.exists() else {"years": {}}
        srcs = [x if isinstance(x, dict) else {"name": str(x), "url": str(x) if str(x).startswith("http") else ""}
                for x in (summary.get("sources") or [])]

        for y in YEARS:
            yr = [r for r in rows if r["tax_year"] == y]
            ys = (summary.get("years") or {}).get(y, {}) or {}
            if not yr:
                continue
            county_name = yr[0]["county"]
            denom = num(ys.get("county_unit_taxable_value"))
            if denom is None:
                cu = [r for r in yr if r["unit_type"] == "county" and num(r["taxable_value_usd"])]
                denom = max((num(r["taxable_value_usd"]) for r in cu), default=None)

            levy, rate_with_tv, rate_all, missing, carried, carried_levy = 0.0, 0.0, 0.0, 0, 0, 0.0
            for r in yr:
                rate, tv, lv = num(r["adopted_rate_per_100"]), num(r["taxable_value_usd"]), num(r["levy_usd"])
                if rate is None and y == "2026" and tv:
                    rate = prior.get(r["cad_entity_code"] or r["taxing_unit_name"])
                    if rate is not None:
                        carried += 1
                        carried_levy += rate * tv / 100
                if rate is None:
                    continue
                rate_all += rate
                if lv is None and tv is not None:
                    lv = rate * tv / 100
                if lv is not None:
                    levy += lv
                    rate_with_tv += rate
                else:
                    missing += 1

            published = num(ys.get("published_total_levy_all_units"))
            stack = (ys.get("typical_commercial_stack") or {})
            stack_rate = num(stack.get("total_rate"))
            stack_txt = f"typical commercial stack ({' + '.join(stack.get('units') or [])}) = {stack_rate:.6f}" if stack_rate else ""
            notes = [n for n in [stack_txt, ys.get("notes", ""), summary.get("gaps", "") if y == "2026" else ""] if n]

            coverage = rate_with_tv / rate_all if rate_all else 0
            if published and denom:
                avg, tot, method = published / denom * 100, published, "levy/taxable (published total levy)"
            elif denom and coverage >= MIN_LEVY_COVERAGE:
                avg, tot, method = levy / denom * 100, levy, "levy/taxable"
                if missing:
                    notes.insert(0, f"{missing} units lacked taxable value/levy and are excluded from levy")
            elif stack_rate:
                avg, tot, method = stack_rate, levy or None, "rate stack"
                notes.insert(0, f"levy coverage too thin ({missing} units without taxable value); using typical commercial stack")
            else:
                avg, tot, method = None, None, "insufficient data"

            if carried and method.startswith("levy/taxable"):
                notes.insert(0, f"ESTIMATED: {carried} units had no 2026 adopted rate; their 2025 rate was applied to 2026 taxable value (${carried_levy/1e6:,.1f}M of levy)")
            if y == "2026":
                notes.insert(0, "2026 levy = 2026 adopted rates x 2026 certified taxable values (collector levy rolls not final)")
            if avg is not None and not (1.5 <= avg <= 3.0):
                notes.insert(0, f"FLAG: average {avg:.4f} outside 1.5-3.0 range")

            cty_rows.append({
                "county": county_name, "tax_year": y,
                "avg_combined_rate_per_100": f"{avg:.6f}" if avg is not None else "",
                "total_levy_usd": f"{tot:.0f}" if tot else "",
                "total_taxable_value_usd": f"{denom:.0f}" if denom else "",
                "method": method,
                "source_name": "; ".join(s.get("name", "") for s in srcs[:4]),
                "source_url": "; ".join(s.get("url", "") for s in srcs[:4] if s.get("url")),
                "date_collected": DATE,
                "notes": " | ".join(notes),
            })

    with (out_dir / "jurisdiction_rates.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, JUR_COLS)
        w.writeheader()
        w.writerows(sorted(jur_rows, key=lambda r: (r["county"], r["tax_year"], r["unit_type"], r["taxing_unit_name"])))
    with (out_dir / "county_rates.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, CTY_COLS)
        w.writeheader()
        w.writerows(cty_rows)
    print(f"jurisdiction rows: {len(jur_rows)}; county rows: {len(cty_rows)}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
