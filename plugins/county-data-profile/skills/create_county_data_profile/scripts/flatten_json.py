"""Flatten a JSON export (one object per record) into one gzipped CSV per nested list, ready to profile.

The shape is read from the file, not assumed:
  - a JSON array, pretty-printed (each record starts on its own line at one indent) or one record per line
  - newline-delimited JSON (one object per line)
  - anything else (a minified array, or one object holding the list) is read in a single process
Every list of objects inside a record becomes its own table, named by its path ("owners", "owners.agents",
"a.b.c"); the record's own fields are the root table (--root, default "record"). Nested plain objects fold into
their parent row as dotted columns; lists of plain values stay as JSON text. Values are written as text, as they
are in the file. Every row carries the record's key columns, plus one <list>_i column per enclosing list (its
position there, 0 = first), so child rows join back to their parent.

Key columns: --keys a,b; otherwise the first top-level field (or pair of fields) that is filled and unique in the
first 5,000 records. The choice is printed; check it holds for the whole file before you rely on it.

Writes <out>/<table>.csv.gz and <out>/_tables.json ({source, records, keys, root, tables: {table: [columns]}}),
which add_tables.py reads.

Usage: python3 -I flatten_json.py <file.json> <out folder> [--keys a,b] [--root name] [--workers n]
"""
import gzip
import itertools
import json
import os
import re
import shutil
import sys
import time
from multiprocessing import Pool
from pathlib import Path


def text(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def flatten(obj, table, ctx, out, keys, root):
    row = dict(ctx)
    children = []

    def walk(o, prefix):
        for k, v in o.items():
            name = prefix + k
            if isinstance(v, dict):
                walk(v, name + ".")
            elif isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
                children.append((name, v))
            else:
                row[name] = text(v)

    walk(obj, "")
    out.setdefault(table, []).append(row)
    seen = keys.setdefault(table, {})
    for k in row:
        seen.setdefault(k, None)
    for name, items in children:
        child = name if table == root else f"{table}.{name}"
        col = name.rsplit(".", 1)[-1] + "_i"
        if col in ctx:
            col = child.replace(".", "_") + "_i"
        for i, item in enumerate(items):
            flatten(item, child, {**ctx, col: str(i)}, out, keys, root)


# ---- reading records -------------------------------------------------------------------------------------------

def detect(src):
    """('pretty', indent) | ('ndjson', None) | ('whole', None), from the start of the file."""
    with open(src, "rb") as f:
        head = f.read(1 << 20)
    s = head.lstrip()
    if s[:1] == b"[":
        m = re.match(rb"\[[ \t]*\r?\n((?:[ \t]*\r?\n)*)([ \t]*)\{", s)
        if m:
            return "pretty", m.group(2)
        return "whole", None
    if s[:1] == b"{":
        first = s.split(b"\n", 1)[0].strip()
        try:
            json.loads(first)
            return "ndjson", None
        except ValueError:
            return "whole", None
    raise SystemExit("not a JSON array or newline-delimited JSON")


def records_in_range(src, lo, hi, mode, indent):
    """Records whose first line starts in [lo, hi)."""
    start = (indent or b"") + b"{"
    with open(src, "rb") as f:
        f.seek(lo)
        if lo:
            f.readline()
        while True:
            pos = f.tell()
            line = f.readline()
            if not line or pos >= hi:
                return
            if mode == "ndjson":
                line = line.strip()
                if line:
                    yield json.loads(line)
                continue
            if not line.startswith(start):
                continue
            body = line.rstrip().rstrip(b",")
            if body.endswith(b"}"):
                try:
                    yield json.loads(body)
                    continue
                except ValueError:
                    pass
            buf = [line]
            end = indent + b"}"
            for line in f:
                buf.append(line)
                if line.rstrip().rstrip(b",") == end:
                    break
            yield json.loads(b"".join(buf).rstrip().rstrip(b","))


def records_whole(src):
    data = json.loads(Path(src).read_bytes())
    if isinstance(data, list):
        return data
    best = max((v for v in data.values() if isinstance(v, list)), key=len, default=None)
    if not best:
        raise SystemExit("no list of records found in the file")
    return best


def pick_keys(sample):
    cols = [k for k, v in sample[0].items() if not isinstance(v, (dict, list))]
    for n in (1, 2):
        for combo in itertools.combinations(cols, n):
            vals = [tuple(r.get(c) for c in combo) for r in sample]
            if all(all(x is not None and x != "" for x in v) for v in vals) and len(set(vals)) == len(vals):
                return list(combo)
    raise SystemExit("no unique key field in the first records; pass --keys")


# ---- work ------------------------------------------------------------------------------------------------------

def write_parts(recs, tmp, n, key_cols, root):
    keys, out, files, count = {}, {}, {}, 0

    def flush():
        for t, rows in out.items():
            f = files.get(t)
            if f is None:
                f = files[t] = gzip.open(tmp / f"{t}.part{n:03d}.jsonl.gz", "wt", encoding="utf-8", compresslevel=1)
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        out.clear()

    for rec in recs:
        flatten(rec, root, {c: text(rec.get(c)) for c in key_cols}, out, keys, root)
        count += 1
        if count % 2000 == 0:
            flush()
    flush()
    for f in files.values():
        f.close()
    return count, {t: list(k) for t, k in keys.items()}


def work(args):
    src, lo, hi, mode, indent, tmp, n, key_cols, root = args
    return write_parts(records_in_range(src, lo, hi, mode, indent), tmp, n, key_cols, root)


def main(src, out_dir, key_cols=None, root="record", workers=None):
    import duckdb
    src, out_dir = Path(src), Path(out_dir)
    tmp = out_dir / "_parts"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    mode, indent = detect(src)
    t0 = time.time()
    if mode == "whole":
        recs = records_whole(src)
        key_cols = key_cols or pick_keys(recs[:5000])
        print(f"{src.name}: read whole ({len(recs):,} records); keys {key_cols}", flush=True)
        results = [write_parts(recs, tmp, 0, key_cols, root)]
    else:
        sample = list(itertools.islice(records_in_range(src, 0, src.stat().st_size, mode, indent), 5000))
        key_cols = key_cols or pick_keys(sample)
        workers = workers or max(1, (os.cpu_count() or 2) - 2)
        size = src.stat().st_size
        step = size // workers + 1
        print(f"{src.name}: {mode}" + (f" (records at indent {len(indent)})" if mode == "pretty" else "")
              + f"; keys {key_cols}; {workers} workers", flush=True)
        with Pool(workers) as pool:
            results = pool.map(work, [(src, i * step, min(size, (i + 1) * step), mode, indent, tmp, i, key_cols, root)
                                      for i in range(workers)])
    total = sum(c for c, _ in results)
    keys = {}
    for _, ks in results:
        for t, cols in ks.items():
            d = keys.setdefault(t, {})
            for c in cols:
                d.setdefault(c, None)
    print(f"parsed {total:,} records into {len(keys)} tables in {time.time() - t0:.0f}s", flush=True)

    con = duckdb.connect()
    con.execute("SET preserve_insertion_order=false")
    for t, cols in sorted(keys.items()):
        parts = sorted(str(p) for p in tmp.glob(f"{t}.part*.jsonl.gz"))
        colspec = "{" + ", ".join("'" + c.replace("'", "''") + "': 'VARCHAR'" for c in cols) + "}"
        dest = out_dir / f"{t}.csv.gz"
        con.execute(f"COPY (SELECT * FROM read_json({parts!r}, format='newline_delimited', columns={colspec})) "
                    f"TO '{dest}' (HEADER, DELIMITER ',', QUOTE '\"', COMPRESSION gzip)")
        print(f"  {t}: {dest.stat().st_size / 1e6:,.1f} MB, {len(cols)} columns", flush=True)
    (out_dir / "_tables.json").write_text(json.dumps(
        {"source": src.name, "records": total, "keys": key_cols, "root": root, "tables": keys}, indent=1))
    shutil.rmtree(tmp)
    print(f"done in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    opts = {}
    for flag in ("--keys", "--root", "--workers"):
        if flag in a:
            i = a.index(flag)
            opts[flag] = a[i + 1]
            del a[i:i + 2]
    if len(a) != 2:
        raise SystemExit(__doc__)
    main(a[0], a[1], opts["--keys"].split(",") if "--keys" in opts else None, opts.get("--root", "record"),
         int(opts["--workers"]) if "--workers" in opts else None)
