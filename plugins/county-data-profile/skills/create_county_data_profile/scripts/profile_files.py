"""Profile every file dataset in a county manifest with DuckDB.

Usage:
  python profile_files.py manifest.json profile.json            # all file datasets not yet in profile.json
  python profile_files.py manifest.json profile.json KEY [KEY]  # just these keys (re-profiles them)
  python profile_files.py manifest.json profile.json --force    # every file dataset, from scratch
  python profile_files.py manifest.json profile.json --sample-only [KEY ...]
      # only (re)take the sample rows, for datasets profiled before samples existed (one quick read per file)

Without keys, each dataset runs in its own child process so a multi-GB file can't exhaust memory,
and results are saved after each one, so an interrupted run resumes where it stopped.

Values are profiled exactly as the file holds them: no trimming, no blanking, no hidden columns. An empty
field is blank because that is how the CSV reader sees it. Each dataset also gets `sample`: 100 random rows
(manifest "sample": {"rows": N}), values unchanged.
"""
import json, os, subprocess, sys

import duckdb

READ = {
    "csv": "strict_mode=false",
    "pipe_utf16": "encoding='utf-16', delim='|', quote='', escape='', strict_mode=false, ignore_errors=true",
    "pipe_latin1": "encoding='latin-1', delim='|', quote='', escape='', strict_mode=false",
    "pipe_utf8": "delim='|', quote='', escape='', strict_mode=false",
}

ISO = r"\d{4}-\d{2}-\d{2}"
US = r"\d{2}[-/]\d{2}[-/]\d{4}"   # MM-DD-YYYY or MM/DD/YYYY
TS = r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?(\.\d+)?"
PCT = r"-?\d*\.?\d+%"


def opts(d):
    r = d.get("read", "csv")
    return r["opts"] if isinstance(r, dict) else READ[r]


def esc(c):
    return '"' + c.replace('"', '""') + '"'


def load(m, key, con, stream=False):
    """Read the dataset into table v: every column as text, values as they are. Returns (path, read_csv source, cols, rejected, rej_sample).
    stream=True makes v a view over the file instead (enough for one sampling pass, no memory for the whole file)."""
    d = m["datasets"][key]
    path = os.path.join(m["root"], d["path"])
    q = lambda sql: con.execute(sql).fetchall()
    print("==", key, path, flush=True)
    o = opts(d)
    src = f"read_csv('{path}', {o}" + ("" if "header=" in o else ", header=true")   # a headerless file sets header=false
    if stream:
        con.execute(f"CREATE VIEW v AS SELECT * FROM {src}, all_varchar=true)")
        return path, src, [r[0] for r in q("DESCRIBE v")], None, None
    con.execute(f"CREATE OR REPLACE TABLE v AS SELECT * FROM {src}, all_varchar=true, store_rejects=true)")
    rejected = q("SELECT count(DISTINCT line) FROM reject_errors")[0][0]   # one bad line can log several errors
    rej_sample = [list(r) for r in q("SELECT line, error_type, left(csv_line, 160) FROM reject_errors LIMIT 3")]
    cols = [r[0] for r in q("DESCRIBE v")]
    return path, src, cols, rejected, rej_sample


def take_sample(m, con, cols, key=None):
    """`sample` entry: N random rows (repeatable), values unchanged. A dataset's own "sample_rows" overrides the
    manifest's "sample": {"rows": N}, for tables whose rows are very large (drawings as JSON) and would push the page
    past the artifact size limit."""
    n = (m["datasets"].get(key, {}).get("sample_rows") if key else None) or m.get("sample", {}).get("rows", 100)
    sel = ", ".join(esc(c) for c in cols)
    rows = con.execute(f"SELECT {sel} FROM v USING SAMPLE reservoir({n} ROWS) REPEATABLE (42)").fetchall()
    return dict(rows=[list(r) for r in rows])


def sample_one(m, key, out):
    con = duckdb.connect()
    con.execute("SET threads=8")
    load(m, key, con, stream=True)
    result = json.load(open(out))
    result[key]["sample"] = take_sample(m, con, [c["name"] for c in result[key]["columns"]], key)
    json.dump(result, open(out, "w"), default=str)
    print(f"sampled {key}: {len(result[key]['sample']['rows'])} rows", flush=True)


def profile_one(m, key, out):
    d = m["datasets"][key]
    con = duckdb.connect()
    con.execute("SET threads=8")
    con.execute("SET preserve_insertion_order=false")
    q = lambda sql: con.execute(sql).fetchall()
    path, src, cols, rejected, rej_sample = load(m, key, con)
    loader = {r[0]: r[1] for r in q(f"DESCRIBE SELECT * FROM {src}, sample_size=200000)")}
    nrows = q("SELECT count(*) FROM v")[0][0]
    force = d.get("force", {})
    max_year = m.get("max_year", 2026)

    colinfo = []
    for c in cols:
        e = esc(c)
        nonnull, distinct, minlen, maxlen, n_int, n_dec, n_iso, n_us, n_ts, n_pct, n_lz = q(f"""
            SELECT count({e}), approx_count_distinct({e}), min(length({e})), max(length({e})),
              count(*) FILTER (WHERE regexp_full_match({e}, '-?\\d+')),
              count(*) FILTER (WHERE regexp_full_match({e}, '-?\\d*\\.\\d+|-?\\d+')),
              count(*) FILTER (WHERE regexp_full_match({e}, '{ISO}')),
              count(*) FILTER (WHERE regexp_full_match({e}, '{US}')),
              count(*) FILTER (WHERE regexp_full_match({e}, '{TS}')),
              count(*) FILTER (WHERE regexp_full_match({e}, '{PCT}')),
              count(*) FILTER (WHERE regexp_full_match({e}, '0\\d+'))
            FROM v""")[0]
        distinct = min(distinct, nonnull)
        datefmt = None
        if nonnull == 0:
            typ = "Empty"
        elif max(n_iso, n_us, n_ts) >= 0.98 * nonnull:
            typ = "Date"
            datefmt = {n_iso: ("'%Y-%m-%d'", ISO), n_us: ("['%m-%d-%Y', '%m/%d/%Y']", US), n_ts: (None, TS)}[max(n_iso, n_us, n_ts)]
        elif n_int == nonnull:
            typ = "Code (numeric text)" if n_lz > 0 else "Integer"
        elif n_dec == nonnull:
            typ = "Decimal"
        elif n_pct == nonnull:
            typ = "Percent"
        elif distinct <= 3 and maxlen == 1:
            typ = "Flag"
        else:
            typ = "Text"
        typ = force.get(c, typ)
        info = dict(name=c, loader=loader.get(c, "?"), type=typ, nonnull=nonnull,
                    nulls=nrows - nonnull, distinct=distinct, minlen=minlen, maxlen=maxlen)
        info["top"] = [list(r) for r in q(f"SELECT {e}, count(*) n FROM v GROUP BY 1 ORDER BY n DESC LIMIT 12")]
        if typ in ("Integer", "Decimal", "Percent"):
            num = f"TRY_CAST(replace({e}, '%', '') AS DOUBLE)"
            mn, mx, avg, p = q(f"""SELECT min({num}), max({num}), avg({num}),
                quantile_cont({num}, [0.01,0.05,0.25,0.5,0.75,0.95,0.99]) FROM v""")[0]
            zeros = q(f"SELECT count(*) FROM v WHERE {num} = 0")[0][0]
            bad = q(f"SELECT count(*) FROM v WHERE {e} IS NOT NULL AND {num} IS NULL")[0][0]
            info["stats"] = dict(min=mn, max=mx, mean=avg, p=p, zeros=zeros, unparsed=bad)
            lo, hi = q(f"SELECT quantile_cont({num},0.01), quantile_cont({num},0.99) FROM v")[0]
            if lo is not None and hi is not None and hi > lo:
                if typ == "Integer" and hi - lo + 1 <= 30:
                    rows = q(f"""SELECT {num} b, count(*) FROM v
                        WHERE {num} BETWEEN {lo} AND {hi} GROUP BY 1 ORDER BY 1""")
                    info["hist"] = dict(kind="discrete", bins=[list(r) for r in rows])
                else:
                    nb, w = 20, (hi - lo) / 20
                    rows = q(f"""SELECT least(floor(({num} - {lo}) / {w}), {nb - 1})::INT b, count(*)
                        FROM v WHERE {num} BETWEEN {lo} AND {hi} GROUP BY 1 ORDER BY 1""")
                    dd = dict(rows)
                    info["hist"] = dict(kind="range", lo=lo, w=w, bins=[[lo + i * w, dd.get(i, 0)] for i in range(nb)])
                info["hist"]["outside"] = q(f"""SELECT count(*) FROM v
                    WHERE {num} < {lo} OR {num} > {hi}""")[0][0]
        elif typ == "Date":
            fmt, _ = datefmt
            dexp = f"TRY_CAST({e} AS TIMESTAMP)" if fmt is None else f"TRY_STRPTIME({e}, {fmt})"
            mn, mx, bad = q(f"""SELECT min({dexp}), max({dexp}),
                count(*) FILTER (WHERE {e} IS NOT NULL AND {dexp} IS NULL) FROM v""")[0]
            bins = [list(r) for r in q(f"SELECT year({dexp}) y, count(*) FROM v WHERE {dexp} IS NOT NULL GROUP BY 1 ORDER BY 1")]
            info["stats"] = dict(min=str(mn)[:10], max=str(mx)[:10], unparsed=bad,
                                 future=sum(n for y, n in bins if y > max_year))
            info["hist"] = dict(kind="year", bins=bins)
        colinfo.append(info)
        print(" ", c, typ, flush=True)
    sample = take_sample(m, con, cols, key)
    result = json.load(open(out)) if os.path.exists(out) else {}
    result[key] = dict(file=d["path"], size=os.path.getsize(path), rows=nrows, rejected=rejected,
                       rej_sample=rej_sample, columns=colinfo, sample=sample)
    json.dump(result, open(out, "w"), default=str)
    print(f"done {key}: {nrows:,} rows, {len(cols)} columns, {rejected} rejected lines", flush=True)


def main():
    args = sys.argv[1:]
    force, sample_only = "--force" in args, "--sample-only" in args
    args = [a for a in args if a not in ("--force", "--sample-only")]
    mpath, out, keys = args[0], args[1], args[2:]
    m = json.load(open(mpath))
    if sample_only:
        P = json.load(open(out))
        todo = keys or [k for k in P if k in m["datasets"] and "sample" not in P[k]]
        todo.sort(key=lambda k: P[k]["size"])
        for k in todo:
            if keys:
                sample_one(m, k, out)
            else:   # own process per file, like a full run
                r = subprocess.run([sys.executable, __file__, mpath, out, "--sample-only", k])
                if r.returncode:
                    print(f"FAILED {k} (exit {r.returncode})", flush=True)
        return
    if keys:
        for k in keys:
            profile_one(m, k, out)
        return
    done = set(json.load(open(out))) if os.path.exists(out) and not force else set()
    if force and os.path.exists(out):
        os.remove(out)
    todo = [k for k, d in m["datasets"].items() if d.get("path") and not d.get("placeholder") and k not in done]
    # small files first, so problems show up early
    todo.sort(key=lambda k: os.path.getsize(os.path.join(m["root"], m["datasets"][k]["path"])))
    for k in todo:
        r = subprocess.run([sys.executable, __file__, mpath, out, k])
        if r.returncode:
            print(f"FAILED {k} (exit {r.returncode})", flush=True)


if __name__ == "__main__":
    main()
