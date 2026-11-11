"""Flatten the Montgomery protax JSON export into one gzipped CSV per section (with headers).

Montgomery has no PACS TXT export -- the protax JSON (Data/Montgomery-protaxExport-20260804.json, ~21 GB,
one pretty-printed array of property records) is the only source. This streams it record by record
(memory stays at about one record) and writes to output/protax_csv/:

    20260804_properties.csv.gz        one row per property: the top-level scalar fields (pID, propType, noticeDt, ...)
    20260804_<section>.csv.gz         one row per item of each list section, keyed by pID:
                                      propertyIdentification, propertyLegalDescription, propertyCharacteristics,
                                      propertyProfile, situses, deeds, taxingunits, valuations, sales, permits,
                                      tags, inspections, appeals, smartgroups, links, notes, events
    20260804_owners.csv.gz            one row per owner (pID, pAccountID, ownerID, name, address, ownerPct ...)
    20260804_owner_values.csv.gz      owners[].ownerValue   (market / appraised / net appraised ...)
    20260804_owner_taxable.csv.gz     owners[].ownerTaxable (taxable value by taxing unit)
    20260804_owner_agents.csv.gz      owners[].agents
    20260804_owner_exemptions.csv.gz  owners[].exemptions

Owner sub-tables carry pID, pAccountID and ownerID so they join back to owners. Values that are themselves
lists/objects (e.g. valuations.details, appeals.claimantEvidence, ownerTaxable.exemptions) are kept as JSON text.
Columns come from a first look at the opening records; a key that only shows up later goes into an `_extra`
column (JSON) instead of being dropped, and the run reports how many rows needed it.

Usage (from the Montgomery folder):
    python3 etl/montgomery_protax_etl.py                 # full run (~20-30 min)
    python3 etl/montgomery_protax_etl.py --limit 5000    # quick test on the first 5,000 records
    python3 etl/montgomery_protax_etl.py --src <other protax json> --out <dir> --prefix <name>

Read the output with pandas (pd.read_csv("....csv.gz", dtype=str)) or DuckDB (read_csv('....csv.gz')).
"""

import argparse
import csv
import gzip
import json
import os
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
MONTGOMERY = os.path.dirname(HERE)
DEFAULT_SRC = os.path.join(MONTGOMERY, "Data", "Montgomery-protaxExport-20260804.json")
DEFAULT_OUT = os.path.join(MONTGOMERY, "output", "protax_csv")
DEFAULT_PREFIX = "20260804"

OWNER_SUBTABLES = {"ownerValue": "owner_values", "ownerTaxable": "owner_taxable",
                   "agents": "owner_agents", "exemptions": "owner_exemptions"}
OWNER_KEYS = ["pID", "pAccountID", "ownerID"]
SCHEMA_SAMPLE = 20_000      # records read up front to fix each table's columns


def iter_records(path, limit=None):
    """Yield each top-level record. Records start with a line ' {' and end with ' }' or ' },'."""
    n = 0
    buf = None
    with open(path, "rb") as f:
        for lineno, line in enumerate(f, 1):
            s = line.rstrip(b"\r\n")
            if buf is None:
                if s == b" {":
                    buf = [line]
                elif s not in (b"[", b"]", b""):
                    raise ValueError(f"Unexpected line {lineno} between records: {s[:120]!r}")
                continue
            if s in (b" }", b" },"):
                buf.append(b" }")
                yield json.loads(b"".join(buf))
                buf = None
                n += 1
                if limit and n >= limit:
                    return
            else:
                buf.append(line)
    if buf is not None:
        raise ValueError("File ended in the middle of a record (truncated or still copying?)")


def cell(v):
    if v is None:
        return ""
    if isinstance(v, (list, dict)):
        return json.dumps(v, separators=(",", ":"), ensure_ascii=False)
    return v


def rows_of(rec):
    """Yield (table, row dict) for one property record."""
    pid = rec.get("pID")
    yield "properties", {k: v for k, v in rec.items() if not isinstance(v, list) or
                         (v and not isinstance(v[0], dict)) or k == "geometry"}
    for k, v in rec.items():
        if not isinstance(v, list) or not v or not isinstance(v[0], dict) or k == "owners":
            continue
        for item in v:
            yield k, {"pID": pid, **item}
    for o in rec.get("owners") or []:
        keys = {"pID": pid, "pAccountID": o.get("pAccountID"), "ownerID": o.get("ownerID")}
        yield "owners", {k: v for k, v in o.items() if k not in OWNER_SUBTABLES}
        for src, table in OWNER_SUBTABLES.items():
            items = o.get(src) or []
            if isinstance(items, dict):
                items = [items]
            for item in items:
                yield table, {**keys, **{k: v for k, v in item.items() if k not in keys}}


class Writer:
    def __init__(self, out_dir, prefix, schemas):
        self.out_dir, self.prefix, self.schemas = out_dir, prefix, schemas
        self.files, self.writers, self.counts, self.extra = {}, {}, Counter(), Counter()

    def write(self, table, row):
        cols = self.schemas.get(table)
        if cols is None:                         # table never seen in the sample: fix its columns now
            cols = self.schemas[table] = list(row)
        if table not in self.writers:
            path = os.path.join(self.out_dir, f"{self.prefix}_{table}.csv.gz")
            f = gzip.open(path, "wt", newline="", encoding="utf-8", compresslevel=4)
            w = csv.writer(f)
            w.writerow(cols + ["_extra"])
            self.files[table], self.writers[table] = f, w
        known = set(cols)
        extra = {k: v for k, v in row.items() if k not in known}
        if extra:
            self.extra[table] += 1
        self.writers[table].writerow([cell(row.get(c)) for c in cols] + [cell(extra) if extra else ""])
        self.counts[table] += 1

    def close(self):
        for f in self.files.values():
            f.close()


def discover_schemas(src, n):
    cols = {}
    for rec in iter_records(src, limit=n):
        for table, row in rows_of(rec):
            seen = cols.setdefault(table, {})
            for k in row:
                seen.setdefault(k, None)
    return {t: list(c) for t, c in cols.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=DEFAULT_SRC)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--prefix", default=DEFAULT_PREFIX)
    ap.add_argument("--limit", type=int, help="only the first N records (for a test run)")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    t0 = time.time()
    print(f"schema from the first {SCHEMA_SAMPLE:,} records ...", flush=True)
    schemas = discover_schemas(args.src, min(SCHEMA_SAMPLE, args.limit or SCHEMA_SAMPLE))
    w = Writer(args.out, args.prefix, schemas)
    n = 0
    try:
        for rec in iter_records(args.src, limit=args.limit):
            for table, row in rows_of(rec):
                w.write(table, row)
            n += 1
            if n % 50_000 == 0:
                print(f"  {n:,} records, {time.time() - t0:,.0f}s", flush=True)
    finally:
        w.close()

    print(f"\n{n:,} properties in {time.time() - t0:,.0f}s -> {args.out}")
    for table in sorted(w.counts):
        path = os.path.join(args.out, f"{args.prefix}_{table}.csv.gz")
        note = f"   ({w.extra[table]:,} rows with keys in _extra)" if w.extra[table] else ""
        print(f"  {table:28} {w.counts[table]:>11,} rows  {len(w.schemas[table]):>4} cols  "
              f"{os.path.getsize(path) / 1e6:>9,.1f} MB{note}")
    if w.counts["properties"] != n:
        sys.exit(f"ERROR: properties rows {w.counts['properties']:,} != records {n:,}")


if __name__ == "__main__":
    main()
