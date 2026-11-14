"""Denton 2026: one row per (property, agent appointment) from the protax JSON, with dates.
Output: Market Analysis/work/denton/denton_agent_appointments_2026.csv.gz (pID, agentID, name, dates; no owner data)."""
import json, sys, time
from multiprocessing import Pool
from pathlib import Path
import pandas as pd

DENTON = Path("/Users/user2/PTP/CAD Website/Denton")
SRC = DENTON / "Data" / "Denton-protaxExport-20260727.json"
INDEX = DENTON / "output" / "protax_review" / "protax_index.csv"
OUT = Path("/Users/user2/PTP/Market Analysis/work/denton/denton_agent_appointments_2026.csv.gz")


def name(a):
    return (a.get("companyName") or a.get("contactName") or
            " ".join(x for x in (a.get("firstName"), a.get("lastName")) if x) or "").strip()


def work(span):
    lo, hi = span
    idx = pd.read_csv(INDEX, usecols=["pID", "offset", "length"]).iloc[lo:hi]
    rows = []
    with open(SRC, "rb") as f:
        for pid, off, ln in idx.itertuples(index=False):
            f.seek(int(off))
            rec = json.loads(f.read(int(ln)).decode("utf-8").rstrip().rstrip(","))
            for o in rec.get("owners") or []:
                for a in o.get("agents") or []:
                    if a.get("agentID") is None:
                        continue
                    rows.append((rec["pID"], a["agentID"], name(a), a.get("applicationDt"), a.get("effectiveDt"),
                                 a.get("expirationDt"), a.get("authorityProtest")))
    return rows


if __name__ == "__main__":
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    n = len(pd.read_csv(INDEX, usecols=["pID"]))
    step = -(-n // (workers * 8))
    spans = [(i, min(i + step, n)) for i in range(0, n, step)]
    t, R = time.time(), []
    with Pool(workers) as pool:
        for i, r in enumerate(pool.imap(work, spans), 1):
            R += r
            print(f"{i}/{len(spans)} {len(R):,} rows {time.time()-t:,.0f}s", flush=True)
    pd.DataFrame(R, columns=["pID", "agentID", "name", "applicationDt", "effectiveDt", "expirationDt", "authorityProtest"]) \
        .drop_duplicates().to_csv(OUT, index=False)
    print("done", OUT)
