"""Flatten a Travis CAD JSON special export (Travis-protaxExport-<date>.json) into one CSV per nested list.

The export is one JSON array with one object per property, pretty-printed with each property starting on a line
" {" and ending on " }" / " },". Every list of objects inside a property becomes its own table, named by its
path ("owners", "owners.agents", "valuations.details.cost-local.improvements" ...). Nested plain objects are
folded into their parent row with dotted column names; lists of plain values are kept as JSON text. Every row
carries pID and pYear, plus one <list>_i column per enclosing list (its position there), so child rows join back.
Values are written as they are in the file, as text.

Two steps: workers each parse a byte range of the file and write gzipped JSON lines per table; then DuckDB
turns each table's parts into output/<out>/<table>.csv.gz with the union of the keys seen.

Run:  profile/venv/bin/python -I etl/travis_json_flatten.py Data/Travis-protaxExport-20260719.json output/json_2026-07-19 [workers]
"""
import gzip
import json
import os
import shutil
import sys
import time
from multiprocessing import Pool
from pathlib import Path

START, ENDS = b" {\n", (b" }\n", b" },\n", b" }")


def text(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def flatten(obj, table, ctx, out, keys):
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
        child = name if table == "property" else f"{table}.{name}"
        col = name.rsplit(".", 1)[-1] + "_i"
        for i, item in enumerate(items):
            flatten(item, child, {**ctx, col: str(i)}, out, keys)


def work(args):
    src, lo, hi, tmp, n = args
    keys, out, files, count = {}, {}, {}, 0

    def flush():
        for t, rows in out.items():
            f = files.get(t)
            if f is None:
                f = files[t] = gzip.open(tmp / f"{t}.part{n:03d}.jsonl.gz", "wt", encoding="utf-8", compresslevel=1)
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        out.clear()

    with open(src, "rb") as f:
        f.seek(lo)
        if lo:
            f.readline()  # land on a line boundary
        while True:
            pos = f.tell()
            line = f.readline()
            if not line or pos >= hi:
                break
            if line != START:
                continue
            buf = [b"{"]
            for line in f:
                if line in ENDS or line.rstrip(b",\n") == b" }":
                    buf.append(b"}")
                    break
                buf.append(line)
            rec = json.loads(b"".join(buf))
            flatten(rec, "property", {"pID": text(rec.get("pID")), "pYear": text(rec.get("pYear"))}, out, keys)
            count += 1
            if count % 2000 == 0:
                flush()
    flush()
    for f in files.values():
        f.close()
    return count, {t: list(k) for t, k in keys.items()}


def main(src, out_dir, workers=8):
    import duckdb
    src, out_dir = Path(src), Path(out_dir)
    tmp = out_dir / "_parts"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    size = src.stat().st_size
    step = size // workers + 1
    t0 = time.time()
    with Pool(workers) as pool:
        results = pool.map(work, [(src, i * step, min(size, (i + 1) * step), tmp, i) for i in range(workers)])
    total = sum(c for c, _ in results)
    keys = {}
    for _, ks in results:
        for t, cols in ks.items():
            d = keys.setdefault(t, {})
            for c in cols:
                d.setdefault(c, None)
    print(f"parsed {total:,} properties into {len(keys)} tables in {time.time() - t0:.0f}s", flush=True)

    con = duckdb.connect()
    con.execute("SET preserve_insertion_order=false")
    for t, cols in sorted(keys.items()):
        parts = sorted(str(p) for p in tmp.glob(f"{t}.part*.jsonl.gz"))
        colspec = "{" + ", ".join(f"'{c}': 'VARCHAR'" for c in cols) + "}"
        dest = out_dir / f"{t}.csv.gz"
        con.execute(f"COPY (SELECT * FROM read_json({parts!r}, format='newline_delimited', columns={colspec})) "
                    f"TO '{dest}' (HEADER, DELIMITER ',', QUOTE '\"', COMPRESSION gzip)")
        print(f"  {t}: {dest.stat().st_size / 1e6:,.1f} MB, {len(cols)} columns", flush=True)
    (out_dir / "_tables.json").write_text(json.dumps({"source": src.name, "properties": total, "tables": keys}, indent=1))
    shutil.rmtree(tmp)
    print(f"done in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else os.cpu_count() - 2)
