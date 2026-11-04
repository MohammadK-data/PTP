"""Convert Rockwall CAD's PACS Appraisal Export (.TXT) to gzipped CSV.

Rockwall publishes the same PACS export as Denton and Travis, with Denton's file names
(<date>_2026_APPRAISAL_INFO.TXT ...). The March prelim is layout 8.0.0.30, the May prelim 8.0.0.32 and the
certified and supp 6 exports 8.0.0.33. Denton's etl/pacs_appraisal_export_layout.json is the 8.0.30 layout, so
it fits all four: the fields the newer versions add to APPRAISAL_INFO, APPRAISAL_ENTITY_INFO and
APPRAISAL_ENTITY_TOTALS land in unmapped_tail. Writes output/<export date>_2026_<RECORD>.csv.gz, the same names
Denton and Travis use. DuckDB reads .csv.gz directly.

Usage (from the Rockwall folder):
    python3 -I etl/rockwall_appraisal_export_etl.py "Data/RCAD CERT 2026 APP ROLL 07_13_2026" [FILE.TXT ...]

The export date comes from the APPRAISAL_HEADER.TXT run date.
"""

import csv
import gzip
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROCKWALL = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROCKWALL / "output"
LAYOUT = json.loads((ROCKWALL.parent / "Denton" / "etl" / "pacs_appraisal_export_layout.json").read_text())

# Same as the Denton ETL notebook
TAB_COLUMNS = {
    "APPRAISAL_SKETCH_INFO": [
        "prop_id", "prop_val_yr", "imprv_id", "imprv_det_id",
        "sketch_type", "sketch_cmds", "sketch_json", "_trailing",
    ],
    "APPRAISAL_SB12": [
        "prop_id", "owner_id", "entity_id", "entity_cd", "entity_name",
        "tea_district_num", "exmpt_type_cd", "qualify_yr", "seq_num", "tax_yr", "col_11",
        "record_type", "col_13", "col_14", "col_15", "col_16", "col_17", "col_18",
        "prop_val_yr", "_trailing",
    ],
}


def record(path):
    """2026-07-13_2026_APPRAISAL_INFO.TXT -> APPRAISAL_INFO"""
    return path.stem.split("_", 2)[2]


def first_line(path):
    with open(path, "rb") as f:
        return f.readline().rstrip(b"\r\n").decode("latin-1")


def parse_fixed_width(path, layout, out_path):
    """Slice each line by the layout positions, strip padding, write CSV. Returns (rows, bad_length_rows)."""
    record_width = len(first_line(path))
    layout_width = layout[-1][2]
    assert record_width >= layout_width, f"{path.name}: {record_width} chars, layout needs {layout_width}"
    names = [name for name, _, _ in layout]
    slices = [(start - 1, end) for _, start, end in layout]
    if record_width > layout_width:
        names.append("unmapped_tail")
        slices.append((layout_width, None))

    n = bad = 0
    with open(path, "rb") as src, gzip.open(out_path, "wt", newline="", encoding="utf-8", compresslevel=1) as dst:
        writer = csv.writer(dst)
        writer.writerow(names)
        for raw_line in src:
            line = raw_line.rstrip(b"\r\n").decode("latin-1")
            if len(line) != record_width:
                bad += 1
                if bad <= 5:
                    print(f"  BAD LENGTH line {n + 1}: {len(line)} chars (expected {record_width})", flush=True)
            writer.writerow([line[s:e].strip() for s, e in slices])
            n += 1
    return n, bad


def parse_tab(path, columns, out_path):
    """Tab-separated, no header. Returns (rows, bad_field_count_rows)."""
    n = bad = 0
    with open(path, "rb") as src, gzip.open(out_path, "wt", newline="", encoding="utf-8", compresslevel=1) as dst:
        writer = csv.writer(dst)
        writer.writerow([c for c in columns if c != "_trailing"])
        for raw_line in src:
            fields = [f.strip() for f in raw_line.rstrip(b"\r\n").decode("latin-1").split("\t")]
            if len(fields) != len(columns):
                bad += 1
                if bad <= 5:
                    print(f"  BAD FIELD COUNT line {n + 1}: {len(fields)} fields (expected {len(columns)})", flush=True)
                fields = (fields + [""] * len(columns))[: len(columns)]
            writer.writerow([v for c, v in zip(columns, fields) if c != "_trailing"])
            n += 1
    return n, bad


def main():
    export_dir = Path(sys.argv[1])
    only = set(sys.argv[2:])
    hdr = first_line(next(export_dir.glob("*_APPRAISAL_HEADER.TXT")))
    run_date = datetime.strptime(hdr[:10], "%m/%d/%Y").strftime("%Y-%m-%d")
    year = hdr[56:60]
    OUTPUT_DIR.mkdir(exist_ok=True)

    files = sorted(export_dir.glob("*.TXT"), key=lambda p: p.stat().st_size)
    unknown = [p.name for p in files if record(p) not in LAYOUT and record(p) not in TAB_COLUMNS]
    assert not unknown, f"No record layout for: {unknown}"
    for path in files:
        if only and path.name not in only:
            continue
        key = record(path)
        out_path = OUTPUT_DIR / f"{run_date}_{year}_{key}.csv.gz"
        t0 = time.time()
        if path.stat().st_size == 0:
            names = [name for name, _, _ in LAYOUT[key]]
            with gzip.open(out_path, "wt", newline="", encoding="utf-8") as dst:
                csv.writer(dst).writerow(names)
            print(f"{path.name} -> {out_path.name}: empty file, header only", flush=True)
            continue
        if "\t" in first_line(path):
            n, bad = parse_tab(path, TAB_COLUMNS[key], out_path)
        else:
            n, bad = parse_fixed_width(path, LAYOUT[key], out_path)
        print(f"{path.name} -> {out_path.name}: {n:,} rows, {bad} bad, "
              f"{out_path.stat().st_size / 1e6:,.1f} MB, {time.time() - t0:,.0f}s", flush=True)


if __name__ == "__main__":
    main()
