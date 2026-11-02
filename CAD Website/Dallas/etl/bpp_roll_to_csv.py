"""Convert the DCAD BPP certified appraisal roll (.DAT) to CSV for review.

The .DAT is a fixed-width mainframe export: one 3,672-character record per
line, laid out in Add_Change_File_Format.xls (field name, type, length,
"start-end" columns). "OCCURS n TIMES" groups are expanded into numbered
columns (e.g. ISD_CEILING_AMOUNT_1..3). FILLER fields are dropped.

NU fields have leading zeros stripped; fields documented as having implied
decimals ("TWO DECIMAL PLACES", "999V99", ...) are divided accordingly.

Usage (from the Dallas folder):
    python3 -I etl/bpp_roll_to_csv.py                  # full CSV
    python3 -I etl/bpp_roll_to_csv.py --limit 1000     # first 1,000 rows
    python3 -I etl/bpp_roll_to_csv.py --layout         # print parsed layout

Outputs go to output/bpp_roll/ (gitignored).
"""

import argparse
import csv
import os
import re
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DALLAS = os.path.dirname(HERE)
ROLL_DIR = os.path.join(DALLAS, "Data", "2026_BPP_CERTIFIED_APPRAISAL_ROLL")
DEFAULT_SRC = os.path.join(ROLL_DIR, "BPP_APRL_ROLL_DALLAS_CO_2026.DAT")
DEFAULT_LAYOUT = os.path.join(ROLL_DIR, "Add_Change_File_Format.xls")
OUT_DIR = os.path.join(DALLAS, "output", "bpp_roll")


def col_name(name):
    return re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_")


def implied_decimals(comment):
    c = comment.upper()
    if "THREE DECIMAL" in c:
        return 3
    if "TWO DECIMAL" in c or "2 DECIMAL" in c or "999V99" in c:
        return 2
    return 0


def load_layout(path):
    """Return [(column, start0, length, type, decimals)] in file order."""
    df = pd.read_excel(path, header=None).iloc[:, :5]
    rows = []
    for cells in df.itertuples(index=False):
        name, typ, length, cols, comment = ("" if pd.isna(c) else str(c).strip() for c in cells)
        if not name or name == "Field Name":
            continue
        rows.append((name, typ, int(float(length)) if length else None, cols, comment))

    fields = []
    i = 0
    while i < len(rows):
        name, typ, length, cols, comment = rows[i]
        i += 1
        if not cols:
            continue  # section heading such as "EXEMPTION DATES"
        start, end = (int(x) for x in cols.split("-"))
        if length is not None:
            if name.upper() != "FILLER":
                fields.append([name, start - 1, length, typ, implied_decimals(comment)])
            continue
        # OCCURS group: sub-fields follow with a length but no columns.
        subs = []
        while i < len(rows) and rows[i][2] is not None and not rows[i][3]:
            subs.append(rows[i])
            i += 1
        m = re.search(r"OCCURS\s+(\d+)", comment.upper())
        times = int(m.group(1)) if m else 1
        width = sum(s[2] for s in subs)
        if width * times != end - start + 1:
            raise ValueError(f"OCCURS group {name!r} is {end - start + 1} wide, sub-fields sum to {width} x {times}")
        pos = start - 1
        for n in range(1, times + 1):
            for sname, styp, slen, _, scomment in subs:
                label = f"{sname} {n}" if times > 1 else sname
                fields.append([label, pos, slen, styp, implied_decimals(scomment)])
                pos += slen

    seen = {}
    for f in fields:
        base = col_name(f[0])
        seen[base] = seen.get(base, 0) + 1
        f[0] = base if seen[base] == 1 else f"{base}_{seen[base]}"
    return [tuple(f) for f in fields]


def convert(raw, typ, decimals):
    v = raw.strip()
    if typ != "NU" or not v.isdigit():
        return v
    if decimals:
        return f"{int(v) / 10 ** decimals:.{decimals}f}"
    return str(int(v))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=DEFAULT_SRC)
    ap.add_argument("--layout-file", default=DEFAULT_LAYOUT)
    ap.add_argument("--limit", type=int, help="stop after N records")
    ap.add_argument("--layout", action="store_true", help="print the parsed layout and exit")
    args = ap.parse_args()

    layout = load_layout(args.layout_file)
    if args.layout:
        for name, start, length, typ, dec in layout:
            print(f"{start + 1:>5}-{start + length:<5} {typ:2} {length:>3} {dec or '':1} {name}")
        print(f"{len(layout)} fields, record length {max(s + l for _, s, l, _, _ in layout)}")
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    stem = os.path.splitext(os.path.basename(args.src))[0]
    suffix = f"_first{args.limit}" if args.limit else ""
    out_path = os.path.join(OUT_DIR, f"{stem}{suffix}.csv")
    record_len = max(s + l for _, s, l, _, _ in layout)

    n = short = 0
    with open(args.src, "r", encoding="latin-1", newline="") as f, \
            open(out_path, "w", encoding="utf-8", newline="") as out:
        w = csv.writer(out)
        w.writerow([name for name, *_ in layout])
        for line in f:
            line = line.rstrip("\r\n")
            if len(line) < record_len:
                short += 1
                line = line.ljust(record_len)
            w.writerow([convert(line[s:s + l], t, d) for _, s, l, t, d in layout])
            n += 1
            if n % 25_000 == 0:
                print(f"  {n:,} records", file=sys.stderr)
            if args.limit and n >= args.limit:
                break

    print(f"{n:,} records x {len(layout)} columns -> {out_path}")
    if short:
        print(f"warning: {short:,} records shorter than {record_len} chars (padded)")


if __name__ == "__main__":
    main()
