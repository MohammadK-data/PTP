"""Denton 2026: one row per property with notice / final value and how the protest went.

Sources (2026 only):
    output/denton_props_2026.csv.gz     from denton_protax_extract_2026.py (protax JSON, 2026-07-27)
    output/denton_appeals_2026.csv.gz   2026 appeals from the same JSON
    output/2026-10-14_2026_APPRAISAL_INFO.csv   PACS export in Data/2026-3 (Oct 14, latest 2026 supplement), fallback only
    Data/2026 CERTIFIED DATA - ALL PROPERTIES is the Jul 27 certified export (same date as the JSON); the Oct 14
    export supersedes it for appeals that were still open on Jul 27, so it is the one used here.

Rules
    Protest = any 2026 appeal except CLERICAL (DCAD value corrections, see denton_values.py).
    One appeal per property decides the result: ours first (appealedByAgentID in OUR_IDS), then finalized over open,
      then the latest appealID.
    Notice  = first 2026 protest's initialMarketValue (denton_values rules, multi-owner basis adjusted).
              Missing -> Oct 14 export market_value (flagged in notice_source).
    Final   = latest finalized protest's finalMarketValue (same rules).
              Appeal still open on Jul 27, or finalized with no final value -> Oct 14 export market_value (flagged).
    Path    = Informal (TOPLINED, AGREEMENT, INFORMAL HELD, or valueDecisionAdjustmentType I),
              ARB (FINAL DETERMINATION, or type F), Withdrawn (WITHDRAWAL), Dismissed (DISMISSED),
              Open (not finalized: SCHEDULED, FILED, REOPENED). DCAD has no separate no-show status.
    Neighborhood = JSON marketArea, else export hood_cd.

Output: output/denton_values_2026.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "output"
OUR_IDS = {"245"}       # the only agent DCAD lists as PROPERTY TAX PROTEST (same ID as the County Scorecards page)
NOT_PROTEST = {"CLERICAL"}


def num(s):
    return pd.to_numeric(s, errors="coerce")


def load_cert():
    cert = pd.read_csv(OUT / "2026-10-14_2026_APPRAISAL_INFO.csv", dtype=str, keep_default_na=False,
                       usecols=["prop_id", "prop_val_yr", "sup_num", "hood_cd", "market_value", "situs_city"])
    cert = cert[cert.prop_val_yr.str.strip().str.lstrip("0").eq("2026")].copy()
    cert["prop_id"] = cert.prop_id.str.strip().str.lstrip("0")
    cert["sup_n"] = num(cert.sup_num)
    cert["mv"] = num(cert.market_value)
    # one row per owner, each with that owner's share: keep the latest supplement, sum across owners
    cert = cert[cert.sup_n.eq(cert.groupby("prop_id").sup_n.transform("max"))]
    g = cert.groupby("prop_id")
    out = pd.DataFrame({"cert_market": g.mv.sum(min_count=1), "hood_cd": g.hood_cd.first(),
                        "cert_city": g.situs_city.first(), "cert_sup": g.sup_n.first()}).reset_index()
    print(f"Oct 14 export rows (2026, one per prop): {len(out):,}")
    return out


def main():
    p = pd.read_csv(OUT / "denton_props_2026.csv.gz", dtype=str, keep_default_na=False)
    a = pd.read_csv(OUT / "denton_appeals_2026.csv.gz", dtype=str, keep_default_na=False)
    cert = load_cert()

    a["appealStatus"] = a.appealStatus.str.strip()
    a = a[~a.appealStatus.isin(NOT_PROTEST)].copy()
    a["agent"] = a.appealedByAgentID.str.replace(r"\.0$", "", regex=True)
    a["is_our"] = a.agent.isin(OUR_IDS)
    a["fin"] = a.finalized.eq("1")
    st, vt = a.appealStatus, a.valueDecisionAdjustmentType
    a["path"] = np.select(
        [~a.fin, st.eq("WITHDRAWAL"), st.eq("DISMISSED"),
         st.isin(["TOPLINED", "AGREEMENT", "INFORMAL HELD"]) | (vt.eq("I") & st.ne("FINAL DETERMINATION")),
         st.eq("FINAL DETERMINATION") | vt.eq("F")],
        ["Open", "Withdrawn", "Dismissed", "Informal", "ARB"], default="Other")
    a["rank"] = a.path.map({"Informal": 0, "ARB": 0, "Other": 1, "Open": 2, "No-show": 3, "Withdrawn": 3, "Dismissed": 3})
    a["aid"] = num(a.appealID)
    ours_p = set(a.loc[a.is_our, "pID"])
    a["ours_acct"] = a.pID.isin(ours_p)
    filers = a.assign(f=np.where(a.agent.ne(""), "agent " + a.agent, a.appealedByType)).groupby("pID").f.agg(lambda s: " | ".join(sorted(set(s))))
    a["n_appeals"] = a.groupby("pID").pID.transform("size")
    cand = a[~a.ours_acct | a.is_our].sort_values(["pID", "rank", "aid"], ascending=[True, True, False])
    pick = cand.drop_duplicates("pID").copy()
    pick["filers"] = pick.pID.map(filers)
    print(f"2026 protests (non-CLERICAL): {len(a):,} appeals on {len(pick):,} properties; ours {len(ours_p):,}")

    v = p.merge(pick[["pID", "appealID", "appealType", "appealStatus", "path", "agent", "appealedByType", "is_our", "n_appeals",
                      "filers", "finalizedDt", "docketDt", "informalStartMeeting", "formalStartMeeting", "informalAppraiser",
                      "formalAppraiser", "panelMembers", "claimantOpinionOfValue", "valueDecisionAdjustmentType"]],
                on="pID", how="left")
    v = v.merge(cert, left_on="pID", right_on="prop_id", how="left")
    v["protested"] = v.appealID.notna()
    v["is_ours"] = v.is_our.eq(True)
    for c in ["current_market", "initial_market", "final_market", "claimantOpinionOfValue"]:
        v[c] = num(v[c])

    v["notice_value"] = v.initial_market.where(v.initial_market > 0)
    v["notice_source"] = np.where(v.notice_value.notna(), "appeal", None)
    miss_n = v.protested & v.notice_value.isna()
    v.loc[miss_n, "notice_value"] = v.loc[miss_n, "cert_market"]
    v.loc[miss_n & v.cert_market.notna(), "notice_source"] = "certified (no initial value)"
    nop = ~v.protested
    v.loc[nop, "notice_value"] = v.loc[nop, "current_market"].fillna(v.loc[nop, "cert_market"])
    v.loc[nop, "notice_source"] = "roll (not protested)"

    v["final_value"] = v.final_market.where(v.final_market > 0)
    v["final_source"] = np.where(v.final_value.notna(), "appeal", None)
    # a closed appeal with no change and no final value: final = notice
    nochg = v.protested & v.path.isin(["Withdrawn", "Dismissed"]) & v.final_value.isna()
    v.loc[nochg, "final_value"] = v.loc[nochg, "notice_value"]
    v.loc[nochg, "final_source"] = "notice (closed, no change)"
    miss_f = v.final_value.isna()
    v.loc[miss_f, "final_value"] = v.loc[miss_f, "cert_market"].fillna(v.loc[miss_f, "current_market"])
    v.loc[miss_f & v.protested & v.path.eq("Open"), "final_source"] = "certified (appeal open)"
    v.loc[miss_f & v.protested & v.path.ne("Open"), "final_source"] = "certified (no final value)"
    v.loc[miss_f & ~v.protested, "final_source"] = "certified (not protested)"

    v["reduction"] = v.notice_value - v.final_value
    v["reduction_pct"] = (v.reduction / v.notice_value).where(v.notice_value > 0)
    v["final_vs_cert"] = (v.final_value - v.cert_market)
    v["check_values"] = v.protested & ((v.notice_value.fillna(0) <= 0) | (v.final_value > v.notice_value * 1.25))
    v["outcome"] = np.select([~v.protested, v.path.eq("Open"), v.reduction > 0, v.reduction < 0],
                             ["Not protested", "Open", "Reduced", "Increased"], default="No change")
    v["marketArea"] = v.marketArea.str.strip()
    v["nb"] = v.marketArea.where(v.marketArea.ne(""), v.hood_cd.fillna("").str.strip())
    v["homestead"] = v.exemptions.str.contains(r"\bHS\b", regex=True)
    v["est_fee_1pct"] = (v.reduction.clip(lower=0) * 0.01).where(v.is_ours & v.path.ne("Open"))
    v = v.drop(columns=["prop_id", "is_our", "final_market", "initial_market"])
    v.to_csv(OUT / "denton_values_2026.csv", index=False)

    pr = v[v.protested]
    print(f"denton_values_2026.csv: {len(v):,} properties, {len(pr):,} protested")
    print("path", pr.path.value_counts().to_dict())
    print("notice source", pr.notice_source.value_counts(dropna=False).to_dict())
    print("final source", pr.final_source.value_counts(dropna=False).to_dict())
    print("flagged", int(pr.check_values.sum()), "| ours flagged", int(pr[pr.is_ours].check_values.sum()))
    print("no nb", int(pr.nb.eq("").sum()), "| nb from export", int((pr.marketArea.eq("") & pr.nb.ne("")).sum()))
    cl = pr[pr.path.ne("Open") & pr.final_source.eq("appeal")]
    print("final == Oct 14 export (closed, appeal values):", f"{(cl.final_vs_cert.abs() <= 2).mean():.1%} of {cl.final_vs_cert.notna().sum():,}")
    o = pr[pr.is_ours]
    oc = o[o.path.ne("Open") & ~o.check_values]
    print("ours", len(o), o.path.value_counts().to_dict(), "| win", f"{(oc.reduction > 0).mean():.1%}",
          "| cut %", f"{oc.reduction.sum() / oc.notice_value.sum():.1%}")


if __name__ == "__main__":
    main()
