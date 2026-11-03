"""Convert Travis CAD's PACS Appraisal Export (.TXT) to gzipped CSV.

Travis publishes the same PACS 8.0.0.33 export as Denton (same record widths and field positions), only
with short file names (PROP.TXT, PROP_ENT.TXT ...). This reuses Denton's layout and parsing rules from
Denton/etl/denton_appraisal_export_etl.ipynb and writes the same CSV names Denton uses, gzipped to save disk:
output/<export date>_2026_<RECORD>.csv.gz. DuckDB reads .csv.gz directly.

Usage (from the Travis folder):
    python3 -I etl/travis_appraisal_export_etl.py "Data/2026 Certified Appraisal Export Supp 0_07182026"
    python3 -I etl/travis_appraisal_export_etl.py "Data/travis_SUPP 335_2026_WEBSITE EXPORT_Renamed" [FILE.TXT ...]

The export date comes from the file's APPR_HDR.TXT run date.
"""

import csv
import gzip
import json
import sys
import time
from datetime import datetime
from pathlib import Path

TRAVIS = Path(__file__).resolve().parent.parent
OUTPUT_DIR = TRAVIS / "output"
LAYOUT = json.loads((TRAVIS.parent / "Denton" / "etl" / "pacs_appraisal_export_layout.json").read_text())

# Travis file name -> PACS record name (Denton's file names)
RECORDS = {
    "PROP": "APPRAISAL_INFO",
    "PROP_ENT": "APPRAISAL_ENTITY_INFO",
    "TOTALS": "APPRAISAL_ENTITY_TOTALS",
    "ENTITY": "APPRAISAL_ENTITY",
    "IMP_INFO": "APPRAISAL_IMPROVEMENT_INFO",
    "IMP_DET": "APPRAISAL_IMPROVEMENT_DETAIL",
    "IMP_ATR": "APPRAISAL_IMPROVEMENT_DETAIL_ATTR",
    "SKETCH_INFO": "APPRAISAL_SKETCH_INFO",
    "MOBILE_HOME_INFO": "APPRAISAL_MOBILE_HOME_INFO",
    "LAND_DET": "APPRAISAL_LAND_DETAIL",
    "SB12": "APPRAISAL_SB12",
    "TAX_DEFERRAL_INFO": "APPRAISAL_TAX_DEFERRAL_INFO",
    "ARB": "APPRAISAL_ARB",
    "LAWSUIT": "APPRAISAL_LAWSUIT",
    "ARBITRATION": "ARBITRATION_LAWSUIT",
    "AGENT": "APPRAISAL_AGENT",
    "ABS_SUBD": "APPRAISAL_ABSTRACT_SUBDV",
    "STATE_CD": "APPRAISAL_STATE_CODE",
    "COUNTRY": "APPRAISAL_COUNTRY_CODE",
    "APPR_HDR": "APPRAISAL_HEADER",
}

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
    hdr = first_line(export_dir / "APPR_HDR.TXT")
    run_date = datetime.strptime(hdr[:10], "%m/%d/%Y").strftime("%Y-%m-%d")
    year = hdr[56:60]
    OUTPUT_DIR.mkdir(exist_ok=True)

    files = sorted(export_dir.glob("*.TXT"), key=lambda p: p.stat().st_size)
    unknown = [p.name for p in files if p.stem not in RECORDS]
    assert not unknown, f"No record mapping for: {unknown}"
    for path in files:
        if only and path.name not in only:
            continue
        key = RECORDS[path.stem]
        out_path = OUTPUT_DIR / f"{run_date}_{year}_{key}.csv.gz"
        t0 = time.time()
        if "\t" in first_line(path):
            n, bad = parse_tab(path, TAB_COLUMNS[key], out_path)
        else:
            n, bad = parse_fixed_width(path, LAYOUT[key], out_path)
        print(f"{path.name} -> {out_path.name}: {n:,} rows, {bad} bad, "
              f"{out_path.stat().st_size / 1e6:,.1f} MB, {time.time() - t0:,.0f}s", flush=True)


if __name__ == "__main__":
    main()
