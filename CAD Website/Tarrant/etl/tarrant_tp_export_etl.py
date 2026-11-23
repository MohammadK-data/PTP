"""Convert Tarrant's True Prodigy Data-FullSet (PACS Legacy appraisal export, fixed-width .TXT) to gzipped CSV.

Field positions come from the layout JSON written by tarrant_tp_layout.py from the export layout workbook whose
record widths match the files (8.0.33 for the 2026-11-13 export). Values are sliced and their padding stripped,
the same as the Travis and Denton ETLs. Two files are tab-separated without a header (SKETCH_INFO, SB12): they use
the Denton/Travis column names. Files run in parallel; each writes <out>/<RECORD>.csv.gz.

Usage: python3 -I etl/tarrant_tp_export_etl.py <export folder> <layout.json> <out folder> [workers]
"""
import csv
import gzip
import json
import re
import sys
import time
from multiprocessing import Pool
from pathlib import Path

TAB_COLUMNS = {
    "APPRAISAL_SKETCH_INFO": ["prop_id", "prop_val_yr", "imprv_id", "imprv_det_id", "sketch_type", "sketch_cmds",
                              "sketch_json", "_trailing"],
    "APPRAISAL_SB12": ["prop_id", "owner_id", "entity_id", "entity_cd", "entity_name", "tea_district_num",
                       "exmpt_type_cd", "qualify_yr", "seq_num", "tax_yr", "col_11", "record_type", "col_13", "col_14",
                       "col_15", "col_16", "col_17", "col_18", "prop_val_yr", "_trailing"],
}


def first_line(p):
    with open(p, "rb") as f:
        return f.readline().rstrip(b"\r\n").decode("latin-1")


def convert(args):
    path, rec, fields, out = args
    t0 = time.time()
    n = bad = 0
    with open(path, "rb") as src, gzip.open(out, "wt", newline="", encoding="utf-8", compresslevel=1) as dst:
        w = csv.writer(dst)
        if rec in TAB_COLUMNS:
            cols = TAB_COLUMNS[rec]
            w.writerow([c for c in cols if c != "_trailing"])
            for raw in src:
                f = [x.strip() for x in raw.rstrip(b"\r\n").decode("latin-1").split("\t")]
                if len(f) != len(cols):
                    bad += 1
                    f = (f + [""] * len(cols))[:len(cols)]
                w.writerow([v for c, v in zip(cols, f) if c != "_trailing"])
                n += 1
        else:
            width = len(first_line(path))
            names = [x[0] for x in fields]
            sl = [(s - 1, e) for _, s, e, _ in fields]
            if width > fields[-1][2]:
                names.append("unmapped_tail")
                sl.append((fields[-1][2], None))
            w.writerow(names)
            for raw in src:
                line = raw.rstrip(b"\r\n").decode("latin-1")
                if len(line) != width:
                    bad += 1
                w.writerow([line[s:e].strip() for s, e in sl])
                n += 1
    return f"{path.name} -> {out.name}: {n:,} rows, {bad} off-width, {out.stat().st_size / 1e6:,.1f} MB, {time.time() - t0:,.0f}s"


def main(folder, layout, out_dir, workers=8):
    folder, out_dir = Path(folder), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    L = json.loads(Path(layout).read_text())
    jobs = []
    for p in sorted(folder.glob("*.TXT"), key=lambda p: -p.stat().st_size):
        rec = re.sub(r"^\d{4}-\d{2}-\d{2}_\w+?_(?=[A-Z])", "", p.stem)
        if rec not in TAB_COLUMNS and rec not in L:
            raise SystemExit(f"no layout for {p.name}")
        jobs.append((p, rec, L.get(rec, {}).get("fields"), out_dir / f"{rec}.csv.gz"))
    with Pool(int(workers)) as pool:
        for msg in pool.imap_unordered(convert, jobs):
            print(msg, flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
