"""Stream-review the Denton protax export JSON without loading it into memory.

The export is a single pretty-printed JSON array (~21 GB). Each top-level
property record starts with a line that is exactly " {" and ends with " }" or
" },", so records are cut out line by line and parsed one at a time.
Memory use stays at roughly one record (~50 KB).

Usage (from the Denton folder):
    python3 -I etl/protax_stream.py count
    python3 -I etl/protax_stream.py sample -n 5 [--skip 1000]
    python3 -I etl/protax_stream.py pid 8 12345
    python3 -I etl/protax_stream.py schema [--limit 20000]
    python3 -I etl/protax_stream.py ndjson

Outputs go to output/protax_review/ (gitignored).
"""

import argparse
import csv
import json
import os
import sys
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DENTON = os.path.dirname(HERE)
DEFAULT_SRC = os.path.join(DENTON, "Data", "Denton-protaxExport-20260727.json")
OUT_DIR = os.path.join(DENTON, "output", "protax_review")


def iter_records(path, progress_every=50_000):
    """Yield (index, record_dict) for each top-level record in the array."""
    start = time.time()
    buf = None
    idx = 0
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            stripped = line.rstrip("\r\n")
            if buf is None:
                if stripped == " {":
                    buf = [line]
                elif stripped not in ("[", "]", ""):
                    raise ValueError(f"Unexpected line {lineno} between records: {stripped[:120]!r}")
                continue
            if stripped in (" }", " },"):
                buf.append(" }\n")
                try:
                    rec = json.loads("".join(buf))
                except json.JSONDecodeError as e:
                    raise ValueError(f"Record {idx} ending at line {lineno} failed to parse: {e}") from e
                buf = None
                yield idx, rec
                idx += 1
                if progress_every and idx % progress_every == 0:
                    print(f"  {idx:,} records, {time.time() - start:,.0f}s", file=sys.stderr)
            else:
                buf.append(line)
    if buf is not None:
        raise ValueError("File ended in the middle of a record (truncated export?)")


def cmd_count(args):
    n = 0
    years, types = defaultdict(int), defaultdict(int)
    for _, rec in iter_records(args.src):
        n += 1
        years[rec.get("pYear")] += 1
        types[rec.get("propType")] += 1
    print(f"records: {n:,}")
    print("pYear:", dict(years))
    print("propType:", dict(types))


def cmd_sample(args):
    out = []
    for i, rec in iter_records(args.src, progress_every=0):
        if i < args.skip:
            continue
        out.append(rec)
        if len(out) >= args.n:
            break
    path = os.path.join(OUT_DIR, f"sample_skip{args.skip}_n{len(out)}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(f"wrote {len(out)} records -> {path}")


def cmd_pid(args):
    wanted = set(args.pids)
    found = []
    for _, rec in iter_records(args.src):
        if rec.get("pID") in wanted:
            found.append(rec)
            wanted.discard(rec["pID"])
            if not wanted:
                break
    for rec in found:
        path = os.path.join(OUT_DIR, f"pid_{rec['pID']}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rec, f, indent=1)
        print(f"wrote {path}")
    if wanted:
        print(f"not found: {sorted(wanted)}")


def _walk(value, path, stats):
    s = stats[path]
    s["present"] += 1
    if value is None:
        s["null"] += 1
        return
    t = type(value).__name__
    s["types"][t] += 1
    if isinstance(value, dict):
        for k, v in value.items():
            _walk(v, f"{path}.{k}" if path else k, stats)
    elif isinstance(value, list):
        s["max_len"] = max(s["max_len"], len(value))
        if not value:
            s["empty"] += 1
        for item in value:
            _walk(item, f"{path}[]", stats)
    else:
        if value == "":
            s["empty"] += 1
        if len(s["examples"]) < 3 and value != "" and value not in s["examples"]:
            s["examples"].append(value)


def cmd_schema(args):
    stats = defaultdict(lambda: {"present": 0, "null": 0, "empty": 0, "max_len": 0,
                                 "types": defaultdict(int), "examples": []})
    n = 0
    for i, rec in iter_records(args.src):
        _walk(rec, "", stats)
        n = i + 1
        if args.limit and n >= args.limit:
            break
    stats.pop("", None)
    suffix = f"first{n}" if args.limit else "full"
    path = os.path.join(OUT_DIR, f"schema_{suffix}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["path", "depth", "present", "null", "empty", "pct_non_null", "types", "max_list_len", "examples"])
        for p in sorted(stats):
            s = stats[p]
            non_null = s["present"] - s["null"]
            w.writerow([p, p.count(".") + p.count("[]"), s["present"], s["null"], s["empty"],
                        f"{non_null / s['present'] * 100:.1f}" if s["present"] else "",
                        "|".join(sorted(s["types"])), s["max_len"] or "",
                        " | ".join(str(x)[:60] for x in s["examples"])])
    print(f"profiled {n:,} records, {len(stats):,} field paths -> {path}")


def cmd_ndjson(args):
    path = os.path.join(OUT_DIR, "Denton-protaxExport-20260727.ndjson")
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for _, rec in iter_records(args.src):
            f.write(json.dumps(rec, separators=(",", ":")))
            f.write("\n")
            n += 1
    print(f"wrote {n:,} records -> {path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=DEFAULT_SRC)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("count")
    p = sub.add_parser("sample")
    p.add_argument("-n", type=int, default=5)
    p.add_argument("--skip", type=int, default=0)
    p = sub.add_parser("pid")
    p.add_argument("pids", type=int, nargs="+")
    p = sub.add_parser("schema")
    p.add_argument("--limit", type=int, default=0, help="stop after N records (0 = whole file)")
    sub.add_parser("ndjson")
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    {"count": cmd_count, "sample": cmd_sample, "pid": cmd_pid,
     "schema": cmd_schema, "ndjson": cmd_ndjson}[args.cmd](args)


if __name__ == "__main__":
    main()
