"""Split a headerless delimited file that mixes record types into one gzipped CSV per type, ready to profile.

Some files (state submissions such as the Comptroller's EARS file, legacy exports) put several record layouts in
one file, told apart by one field (usually the first). Each type gets its own table: <out>/<TYPE>.csv.gz.

Column names come from --fields, a JSON file you write from the layout document (the manual's field tables):
  {"<TYPE>": {"<field id>": "<field name>", ...}}  -> columns "<field id>_<name slug>", in that order
  {"<TYPE>": ["<name>", ...]}                       -> columns "<name slug>"
Without --fields, or for a type it doesn't list, columns are <TYPE>_01, <TYPE>_02 ...
A layout may list more fields than a year's file has (fields added in later releases): each type takes the first
N names, where N is the field count of its rows. Every row of a type must have the same count; a row that
doesn't stops the run with its line number, because the layout is then unclear.

Values are written as they are. The encoding is read as UTF-8 if the whole file decodes, otherwise Latin-1
(--encoding overrides); the delimiter is sniffed from the first lines (--delim overrides).

Usage: python3 -I split_record_types.py <file> <out folder> [--fields fields.json] [--type-col 0]
                                        [--encoding latin-1] [--delim ,]
"""
import csv
import gzip
import json
import re
import sys
from pathlib import Path


def slug(s):
    s = re.sub(r"[^a-z0-9]+", "_", s.lower().replace("%", " pct ").replace("$", "")).strip("_")
    return s[:48].rstrip("_")


def header(kind, n, fields):
    spec = fields.get(kind)
    if spec is None:
        return [f"{kind}_{i:02d}" for i in range(1, n + 1)]
    names = [f"{fid}_{slug(name)}" for fid, name in spec.items()] if isinstance(spec, dict) else [slug(x) for x in spec]
    if n > len(names):
        raise SystemExit(f"{kind} rows have {n} fields; the layout lists {len(names)}")
    return names[:n]


def encoding_of(path):
    try:
        with open(path, encoding="utf-8") as f:
            for _ in iter(lambda: f.read(1 << 24), ""):
                pass
        return "utf-8"
    except UnicodeDecodeError:
        return "latin-1"


def main(src, out_dir, fields=None, type_col=0, encoding=None, delim=None):
    src, out_dir = Path(src), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fields = json.loads(Path(fields).read_text()) if fields else {}
    encoding = encoding or encoding_of(src)
    with open(src, newline="", encoding=encoding) as f:
        if not delim:
            delim = csv.Sniffer().sniff(f.read(1 << 16), delimiters=",|\t;").delimiter
            f.seek(0)
        writers, files, counts = {}, {}, {}
        for line_no, row in enumerate(csv.reader(f, delimiter=delim), 1):
            if not row:
                continue
            kind = row[type_col].strip()
            w = writers.get(kind)
            if w is None:
                files[kind] = gzip.open(out_dir / f"{slug(kind).upper() or 'BLANK'}.csv.gz", "wt", newline="",
                                        encoding="utf-8", compresslevel=1)
                w = writers[kind] = csv.writer(files[kind])
                w.writerow(header(kind, len(row), fields))
                counts[kind] = [0, len(row)]
            if len(row) != counts[kind][1]:
                raise SystemExit(f"line {line_no}: {kind} row has {len(row)} fields, earlier {kind} rows had {counts[kind][1]}")
            w.writerow(row)
            counts[kind][0] += 1
    for f in files.values():
        f.close()
    print(f"{src.name} ({encoding}, delimiter {delim!r}):",
          "; ".join(f"{k}: {c:,} rows, {n} fields" + ("" if k in fields else " (no layout names)") for k, (c, n) in counts.items()))


if __name__ == "__main__":
    a = sys.argv[1:]
    o = {}
    for flag in ("--fields", "--type-col", "--encoding", "--delim"):
        if flag in a:
            i = a.index(flag)
            o[flag] = a[i + 1]
            del a[i:i + 2]
    if len(a) != 2:
        raise SystemExit(__doc__)
    main(a[0], a[1], o.get("--fields"), int(o.get("--type-col", 0)), o.get("--encoding"), o.get("--delim"))
