"""Make one gzipped CSV from a workbook sheet or from several CSVs that share a header, ready to profile.

  - .xlsx: one sheet (--sheet, default the first) is written as it is, blank cells as empty strings.
    The other sheet names are printed: look for a data dictionary among them.
  - .csv (one or more): the files must have the same header; it is written once, then every file's rows.
    Use this for a report the CAD splits into parts (name_1.csv, name_2.csv ...), so it profiles as one table.
Values are written as they are. CSV inputs are read as UTF-8 (a BOM is dropped) if they decode, otherwise Latin-1.

Usage: python3 -I to_csv_gz.py <out.csv.gz> <input> [input ...] [--sheet name]
"""
import csv
import gzip
import sys
from pathlib import Path


def open_text(p):
    try:
        with open(p, encoding="utf-8-sig") as f:
            for _ in iter(lambda: f.read(1 << 24), ""):
                pass
        return open(p, newline="", encoding="utf-8-sig")
    except UnicodeDecodeError:
        return open(p, newline="", encoding="latin-1")


def main(out, inputs, sheet=None):
    out = Path(out)
    rows = 0
    with gzip.open(out, "wt", newline="", encoding="utf-8") as g:
        w = csv.writer(g)
        if len(inputs) == 1 and Path(inputs[0]).suffix.lower() in (".xlsx", ".xlsm"):
            import openpyxl
            wb = openpyxl.load_workbook(inputs[0], read_only=True, data_only=True)
            ws = wb[sheet] if sheet else wb.worksheets[0]
            print("sheets:", ", ".join(wb.sheetnames), "| writing", ws.title)
            for r in ws.iter_rows(values_only=True):
                w.writerow(["" if v is None else v for v in r])
                rows += 1
            rows -= 1
        else:
            head = None
            for p in inputs:
                with open_text(p) as f:
                    r = csv.reader(f)
                    h = next(r)
                    if head is None:
                        head = h
                        w.writerow(h)
                    elif h != head:
                        raise SystemExit(f"{Path(p).name}: header differs from {Path(inputs[0]).name}")
                    n = sum(1 for _ in map(w.writerow, r))
                    print(f"{Path(p).name}: {n:,} rows")
                    rows += n
    print(f"{out.name}: {rows:,} rows")


if __name__ == "__main__":
    a = sys.argv[1:]
    sheet = None
    if "--sheet" in a:
        i = a.index("--sheet")
        sheet = a[i + 1]
        del a[i:i + 2]
    if len(a) < 2:
        raise SystemExit(__doc__)
    main(a[0], a[1:], sheet)
