"""One pass over the Montgomery protax JSON (Aug 4 2026 export): one row per property and one row per 2026 appeal.

Uses the byte index built by montgomery_lookup.py and the value rules in montgomery_values._extract
(notice = first 2026 appeal's initialMarketValue, final = latest finalized appeal's finalMarketValue,
multi-owner basis adjustment). Only 2026 appeals are kept.

Outputs (output/):
    montgomery_props_2026.csv.gz     one row per pID
    montgomery_appeals_2026.csv.gz   one row per 2026 appeal

Run:  .venv/bin/python -I "CAD Website/Montgomery/etl/montgomery_protax_extract_2026.py" [workers]
"""
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import montgomery_values as tv  # noqa: E402

SRC = tv.PROTAX_JSON
OUT = HERE.parent / "output"
YEAR = 2026

APPEAL_KEYS = ["appealID", "appealType", "appealStatus", "appealedByType", "appealedByAgentID", "appealedByID",
               "informal", "informalAppraiser", "informalStartMeeting", "informalDecisionValueAdjustment",
               "informalDecisionAdjustmentValue", "formalAppraiser", "formalStartMeeting",
               "formalDecisionValueAdjustment", "formalDecisionAdjustmentValue", "initialMarketValue",
               "initialAppraisedValue", "finalMarketValue", "finalAppraisedValue", "finalized", "finalizedDt",
               "docketDt", "panelID", "panelMembers", "decision", "decisionReason", "valueDecisionAdjustmentType",
               "claimantOpinionOfValue", "dueDiligenceEvidenceRequestDt", "hearingLetterDt"]


def first(lst):
    return lst[0] if isinstance(lst, list) and lst else (lst if isinstance(lst, dict) else {})


def all_agents(rec):
    out = {}
    for o in rec.get("owners") or []:
        for a in o.get("agents") or []:
            name = a.get("companyName") or a.get("contactName") or \
                " ".join(x for x in (a.get("firstName"), a.get("lastName")) if x) or ""
            out.setdefault(a.get("agentID"), (name.strip(), a.get("effectiveDt"), a.get("expirationDt")))
    return out


def work(span):
    lo, hi = span
    idx = pd.read_csv(tv.PROTAX_INDEX, usecols=["pID", "offset", "length"]).iloc[lo:hi]
    props, appeals = [], []
    with open(SRC, "rb") as f:
        for pid, off, ln in idx.itertuples(index=False):
            f.seek(int(off))
            rec = json.loads(f.read(int(ln)).decode("utf-8").rstrip().rstrip(","))
            v = tv._extract(rec)
            prof, chars, sit, ident = first(rec.get("propertyProfile")), first(rec.get("propertyCharacteristics")), \
                first(rec.get("situses")), first(rec.get("propertyIdentification"))
            owners = rec.get("owners") or []
            ag = all_agents(rec)
            cur = tv._current_agents(rec)
            props.append({
                "pID": rec["pID"], "pYear": rec.get("pYear"), "geoID": ident.get("geoID"), "refID2": ident.get("refID2"),
                "propType": rec.get("propType"), "inactive": rec.get("inactive"), "noticeDt": rec.get("noticeDt"),
                "situs": " ".join(str(x) for x in (sit.get("streetNum"), sit.get("streetPrefix"), sit.get("streetName"),
                                                  sit.get("streetSuffix"), sit.get("streetSecondary")) if x),
                "zip": sit.get("zip"), "city": prof.get("cityTaxingUnitName"), "school": prof.get("schoolTaxingUnitName"),
                "owner": owners[0].get("name") if owners else None, "owner_count": len(owners),
                "exemptions": prof.get("exemptions"), "stateCd": prof.get("stateCd"), "imprvClass": prof.get("imprvClass"),
                "yrb": prof.get("imprvActualYearBuilt"), "sf": prof.get("imprvMainArea"),
                "marketArea": chars.get("marketArea"), "subType": chars.get("subType"),
                "current_market": v.get("current_market"), "current_appraised": v.get("current_appraised"),
                "initial_market": v.get("initial_market"), "final_market": v.get("final_market"),
                "basis_adjusted": v.get("basis_adjusted"),
                "agents_current": " | ".join(f"{n} ({k})" for k, n in cur.items() if k is not None),
                "agents_all": " | ".join(f"{n} ({k})" for k, (n, _, _) in ag.items() if k is not None),
                "agent_ids_all": " | ".join(str(k) for k in ag if k is not None),
            })
            for a in rec.get("appeals") or []:
                if a.get("pYear") != YEAR:
                    continue
                row = {"pID": rec["pID"]}
                row.update({k: a.get(k) for k in APPEAL_KEYS})
                appeals.append(row)
    return props, appeals


def main(workers=10):
    t = time.time()
    n = len(pd.read_csv(tv.PROTAX_INDEX, usecols=["pID"]))
    step = -(-n // (workers * 4))
    spans = [(i, min(i + step, n)) for i in range(0, n, step)]
    P, A = [], []
    with Pool(workers) as pool:
        for i, (p, a) in enumerate(pool.imap(work, spans), 1):
            P += p; A += a
            print(f"  {i}/{len(spans)} chunks, {len(P):,} props, {time.time() - t:,.0f}s", flush=True)
    pdf = pd.DataFrame(P).drop_duplicates("pID")
    adf = pd.DataFrame(A).drop_duplicates()
    pdf.to_csv(OUT / "montgomery_props_2026.csv.gz", index=False)
    adf.to_csv(OUT / "montgomery_appeals_2026.csv.gz", index=False)
    print(f"props {len(pdf):,} | 2026 appeals {len(adf):,} on {adf.pID.nunique():,} props | {time.time() - t:,.0f}s")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
