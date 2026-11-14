"""One pass over the Denton protax JSON (2026-07-27 export): one row per property and one row per 2026 appeal.

Uses the byte index output/protax_review/protax_index.csv (built by denton_lookup.py --build-index) and the
value rules of denton_values._appeals (notice = first 2026 non-CLERICAL appeal's initialMarketValue,
final = latest finalized appeal's finalMarketValue, multi-owner basis adjustment). Only 2026 appeals are kept;
every 2026 appeal is written (CLERICAL included) so the build script can decide what counts as a protest.

Outputs (output/):
    denton_props_2026.csv.gz     one row per pID
    denton_appeals_2026.csv.gz   one row per 2026 appeal

Run:  .venv/bin/python -I "CAD Website/Denton/etl/denton_protax_extract_2026.py" [workers]
"""
import json
import math
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DENTON = HERE.parent
SRC = DENTON / "Data" / "Denton-protaxExport-20260727.json"
INDEX = DENTON / "output" / "protax_review" / "protax_index.csv"
OUT = DENTON / "output"
YEAR = 2026
EXPORT_DATE = "2026-07-27"
NOT_PROTEST = {"CLERICAL"}   # corrections, not protests (see denton_values.py)

APPEAL_KEYS = ["appealID", "appealType", "appealStatus", "appealedByType", "appealedByAgentID", "appealedByID",
               "informal", "informalAppraiser", "informalStartMeeting", "informalDt", "informalDecisionValueAdjustment",
               "informalDecisionAdjustmentValue", "formalAppraiser", "formalStartMeeting", "formalEndMeeting",
               "formalDecisionValueAdjustment", "formalDecisionAdjustmentValue", "initialMarketValue",
               "initialAppraisedValue", "finalMarketValue", "finalAppraisedValue", "finalized", "finalizedDt",
               "docketDt", "panelID", "panelMembers", "decision", "decisionReason", "valueDecisionAdjustmentType",
               "claimantOpinionOfValue", "dueDiligenceEvidenceRequestDt", "hearingLetterDt", "protesterScheduled"]


def first(lst):
    return lst[0] if isinstance(lst, list) and lst else (lst if isinstance(lst, dict) else {})


def agent_name(a):
    return (a.get("companyName") or a.get("contactName") or
            " ".join(x for x in (a.get("firstName"), a.get("lastName")) if x) or "").strip()


def extract(rec):
    """denton_values._appeals value rules for one record."""
    ovs = [first(o.get("ownerValue")) for o in rec.get("owners") or []]

    def owner_sum(key):
        vals = [v.get(key) for v in ovs if v.get(key) is not None]
        return sum(vals) if vals else None

    cur = owner_sum("ownerMarketValue")
    pcts = [o.get("ownerPct") or 0 for o in rec.get("owners") or []]
    pct = sum(pcts)

    def basis_factor(v, initial=False):
        positive = [q for q in pcts if q > 0]
        if not v or not cur or not positive or (len(positive) == 1 and pct >= 99.99):
            return 1.0
        cands = [1.0, pct / 100] + [pct / q for q in set(positive)]
        if initial:
            cands = [f_ for f_ in cands if v * f_ >= cur - 2] or cands
        return min(cands, key=lambda f_: (abs(math.log(v * f_ / cur)), f_ != 1.0))

    def on_basis(v, f_):
        if v is None or f_ == 1.0:
            return v
        x = v * f_
        return cur if abs(x - cur) <= 2 else round(x)

    row = {"current_market": cur, "current_appraised": owner_sum("ownerAppraisedValue"),
           "net_appraised": owner_sum("ownerNetAppraisedValue"), "owner_pct": round(pct, 4) if pct else None}
    aps = sorted((a for a in rec.get("appeals") or [] if a.get("pYear") == YEAR
                  and (a.get("appealStatus") or "").strip() not in NOT_PROTEST), key=lambda a: a["appealID"])
    if aps:
        done = [a for a in aps if a.get("finalized") and a.get("finalMarketValue")]
        fi = basis_factor(aps[0].get("initialMarketValue"), initial=True)
        ff = basis_factor(done[-1]["finalMarketValue"]) if done else 1.0
        row.update({"initial_market": on_basis(aps[0].get("initialMarketValue"), fi),
                    "final_market": on_basis(done[-1]["finalMarketValue"], ff) if done else None,
                    "basis_adjusted": fi != 1.0 or ff != 1.0})
    return row


def work(span):
    lo, hi = span
    idx = pd.read_csv(INDEX, usecols=["pID", "offset", "length"]).iloc[lo:hi]
    props, appeals, agents = [], [], {}
    with open(SRC, "rb") as f:
        for pid, off, ln in idx.itertuples(index=False):
            f.seek(int(off))
            rec = json.loads(f.read(int(ln)).decode("utf-8").rstrip().rstrip(","))
            v = extract(rec)
            prof, chars, ident = first(rec.get("propertyProfile")), first(rec.get("propertyCharacteristics")), \
                first(rec.get("propertyIdentification"))
            sit = next((s for s in rec.get("situses") or [] if s.get("primarySitus")), first(rec.get("situses")))
            owners = rec.get("owners") or []
            ag, cur = {}, {}
            for o in owners:
                for a in o.get("agents") or []:
                    k = a.get("agentID")
                    if k is None:
                        continue
                    nm = agent_name(a)
                    ag.setdefault(k, nm)
                    agents.setdefault(k, [nm, 0])
                    agents[k][1] += 1
                    if not a.get("expirationDt") or a["expirationDt"][:10] >= EXPORT_DATE:
                        cur.setdefault(k, nm)
            props.append({
                "pID": rec["pID"], "pYear": rec.get("pYear"), "geoID": ident.get("geoID"), "refID2": ident.get("refID2"),
                "propType": rec.get("propType"), "inactive": rec.get("inactive"), "noticeDt": rec.get("noticeDt"),
                "situs": " ".join(str(x) for x in (sit.get("streetNum"), sit.get("streetPrefix"), sit.get("streetName"),
                                                  sit.get("streetSuffix"), sit.get("streetSecondary")) if x),
                "situs_city": sit.get("city"), "zip": sit.get("zip"),
                "city": prof.get("cityTaxingUnitName"), "school": prof.get("schoolTaxingUnitName"),
                "owner": owners[0].get("name") if owners else None, "owner_count": len(owners),
                "exemptions": prof.get("exemptions"), "stateCd": prof.get("stateCd"), "imprvClass": prof.get("imprvClass"),
                "yrb": prof.get("imprvActualYearBuilt"), "sf": prof.get("imprvMainArea"),
                "marketArea": chars.get("marketArea"), "region": chars.get("region"), "subType": chars.get("subType"),
                "current_market": v.get("current_market"), "current_appraised": v.get("current_appraised"),
                "net_appraised": v.get("net_appraised"), "owner_pct": v.get("owner_pct"),
                "initial_market": v.get("initial_market"), "final_market": v.get("final_market"),
                "basis_adjusted": v.get("basis_adjusted"),
                "agents_current": " | ".join(f"{n} ({k})" for k, n in cur.items()),
                "agents_all": " | ".join(f"{n} ({k})" for k, n in ag.items()),
                "agent_ids_all": " | ".join(str(k) for k in ag),
            })
            for a in rec.get("appeals") or []:
                if a.get("pYear") != YEAR:
                    continue
                row = {"pID": rec["pID"]}
                row.update({k: a.get(k) for k in APPEAL_KEYS})
                appeals.append(row)
    return props, appeals, agents


def main(workers=10):
    t = time.time()
    n = len(pd.read_csv(INDEX, usecols=["pID"]))
    step = -(-n // (workers * 4))
    spans = [(i, min(i + step, n)) for i in range(0, n, step)]
    P, A, AG = [], [], {}
    with Pool(workers) as pool:
        for i, (p, a, ag) in enumerate(pool.imap(work, spans), 1):
            P += p; A += a
            for k, (nm, c) in ag.items():
                AG.setdefault(k, [nm, 0])[1] += c
            print(f"  {i}/{len(spans)} chunks, {len(P):,} props, {time.time() - t:,.0f}s", flush=True)
    pdf = pd.DataFrame(P).drop_duplicates("pID")
    adf = pd.DataFrame(A).drop_duplicates()
    pdf.to_csv(OUT / "denton_props_2026.csv.gz", index=False)
    adf.to_csv(OUT / "denton_appeals_2026.csv.gz", index=False)
    pd.DataFrame([(k, nm, c) for k, (nm, c) in AG.items()], columns=["agentID", "name", "props"]) \
        .sort_values("props", ascending=False).to_csv(OUT / "denton_agents_2026.csv", index=False)
    print(f"props {len(pdf):,} | 2026 appeals {len(adf):,} on {adf.pID.nunique():,} props | {time.time() - t:,.0f}s")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
