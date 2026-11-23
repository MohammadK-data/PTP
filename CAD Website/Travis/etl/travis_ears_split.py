"""Split a Travis CAD EARS submission (227EARSmmddyy.csv, no header) into one gzipped CSV per record type.

The Comptroller's EARS file mixes three record types, told apart by the first field: AJR (account per taxing
unit and category), AUD (ag-use detail) and TU2 (top-10 taxpayers). Column names come from the 96-1051 manual,
parsed into Data/ears_download/ears_fields.json, as "<field id>_<name>" (AJR031_category). Each year's AJR has
only the fields its manual release had (97 in 2024, 102 in 2025, 111 in 2026); the row's own field count decides.
Also converts the year's 50-897 tax-office file (.xlsx or .csv) to CSV.

Run:  profile/venv/bin/python -I etl/travis_ears_split.py Data/ears_download/EARS_082626 output/ears/2026
"""
import csv
import gzip
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIELDS = json.loads((HERE.parent / "Data/ears_download/ears_fields.json").read_text())


def slug(fid, name):
    s = re.sub(r"[^a-z0-9]+", "_", name.lower().replace("%", " pct ").replace("$", "")).strip("_")
    return f"{fid}_{s[:48].rstrip('_')}"


def header(kind, n):
    fs = list(FIELDS[kind].items())
    if n > len(fs):
        raise SystemExit(f"{kind} row has {n} fields, the manual lists {len(fs)}")
    return [slug(fid, name) for fid, name in fs[:n]]


def main(folder, out_dir):
    folder, out_dir = Path(folder), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    src = next(folder.glob("227EARS*.csv"))
    writers, files, counts = {}, {}, {}
    with open(src, newline="", encoding="latin-1") as f:
        for row in csv.reader(f):
            kind = row[0]
            w = writers.get(kind)
            if w is None:
                files[kind] = gzip.open(out_dir / f"{kind}.csv.gz", "wt", newline="", encoding="utf-8", compresslevel=1)
                w = writers[kind] = csv.writer(files[kind])
                w.writerow(header(kind, len(row)))
                counts[kind] = [0, len(row)]
            if len(row) != counts[kind][1]:
                raise SystemExit(f"{kind} row {counts[kind][0]} has {len(row)} fields, expected {counts[kind][1]}")
            w.writerow(row)
            counts[kind][0] += 1
    for f in files.values():
        f.close()
    print(src.name, {k: f"{c:,} rows, {n} fields" for k, (c, n) in counts.items()})

    tax = [p for p in folder.glob("227_50_897_*") if p.suffix in (".xlsx", ".csv")]
    if tax:
        p = tax[0]
        dest = out_dir / "50_897.csv.gz"
        with gzip.open(dest, "wt", newline="", encoding="utf-8") as out:
            w = csv.writer(out)
            if p.suffix == ".csv":
                with open(p, newline="", encoding="utf-8-sig") as f:
                    rows = sum(1 for _ in map(w.writerow, csv.reader(f))) - 1
            else:
                import openpyxl
                ws = openpyxl.load_workbook(p, read_only=True, data_only=True).worksheets[0]
                rows = sum(1 for _ in map(w.writerow, ([("" if v is None else v) for v in r] for r in ws.iter_rows(values_only=True)))) - 1
        print(p.name, f"{rows:,} rows")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
