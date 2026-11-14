"""Travis 2026: every agent appointment on every property, from the TCAD protax JSON (Oct 6 export).

One pass over the JSON via the byte index built by CAD Website/Travis/etl/travis_lookup.py.
Output: Market Analysis/work/travis/travis_agents_2026.csv.gz
        pID, agentID, name, effectiveDt, expirationDt, authorityProtest
Run:    /Users/user2/PTP/.venv/bin/python -I "Market Analysis/etl/travis_agents_2026.py" [workers]
"""
import json
import sys
from multiprocessing import Pool
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "CAD Website/Travis/Data/Travis-protaxExport-20261006.json"
IDX = ROOT / "CAD Website/Travis/output/protax_review/protax_index_20261006.csv"
OUT = ROOT / "Market Analysis/work/travis/travis_agents_2026.csv.gz"


def name_of(a):
    return (a.get("companyName") or a.get("contactName")
            or " ".join(x for x in (a.get("firstName"), a.get("lastName")) if x) or "").strip()


def work(span):
    lo, hi = span
    idx = pd.read_csv(IDX, usecols=["pID", "offset", "length"]).iloc[lo:hi]
    rows = []
    with open(SRC, "rb") as f:
        for pid, off, ln in idx.itertuples(index=False):
            f.seek(int(off))
            rec = json.loads(f.read(int(ln)).decode("utf-8").rstrip().rstrip(","))
            seen = set()
            for o in rec.get("owners") or []:
                for a in o.get("agents") or []:
                    k = (a.get("agentID"), a.get("effectiveDt"), a.get("expirationDt"))
                    if k in seen:
                        continue
                    seen.add(k)
                    rows.append((rec.get("pID"), a.get("agentID"), name_of(a), a.get("effectiveDt"),
                                 a.get("expirationDt"), a.get("authorityProtest")))
    return rows


def main():
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    n = len(pd.read_csv(IDX, usecols=["pID"]))
    step = 5000
    spans = [(i, min(i + step, n)) for i in range(0, n, step)]
    out = []
    with Pool(workers) as p:
        for i, r in enumerate(p.imap_unordered(work, spans)):
            out.extend(r)
            if i % 20 == 0:
                print(f"{i}/{len(spans)}", flush=True)
    df = pd.DataFrame(out, columns=["pID", "agentID", "name", "effectiveDt", "expirationDt", "authorityProtest"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(len(df), "rows ->", OUT)


if __name__ == "__main__":
    main()
