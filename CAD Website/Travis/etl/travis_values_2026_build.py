"""Travis 2026: one row per property with notice / final value and how the protest went.

Sources (2026 only):
    output/travis_props_2026.csv.gz     from travis_protax_extract_2026.py (protax JSON, Oct 6)
    output/travis_appeals_2026.csv.gz   2026 appeals from the same JSON
    output/2026-10-06_2026_APPRAISAL_INFO.csv.gz   certified export SUPP 335 (Oct 6), fallback only

Rules
    Protest = a 2026 appeal of type P. One appeal per property decides the result:
      ours first (appealedByAgentID in OUR_IDS), then finalized over open, then the latest appealID.
    Notice  = first 2026 appeal's initialMarketValue (travis_values rules, multi-owner basis adjusted).
              Missing -> certified market_value (flagged).
    Final   = latest finalized appeal's finalMarketValue (same rules).
              Appeal still open, or finalized with no final value -> certified market_value (Oct 6), flagged.
    Path    = Informal (ORDT / EF_AS / I with an informal decision), ARB (ORD2..ORD13, ORDM, formal decisions),
              No-show (FTA), Withdrawn (W, EF_WD), Dismissed (D, LD), Open (not finalized).
    Neighborhood = JSON marketArea, else certified hood_cd.

Output: output/travis_values_2026.csv, output/travis_values_2026_summary.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "output"
OUR_IDS = {"1863738", "1898343", "1898284"}       # every agent ID TCAD lists as PROPERTY TAX PROTEST (not AKA WATCHTOWER)


def num(s):
    return pd.to_numeric(s, errors="coerce")


def main():
    p = pd.read_csv(OUT / "travis_props_2026.csv.gz", dtype=str, keep_default_na=False)
    a = pd.read_csv(OUT / "travis_appeals_2026.csv.gz", dtype=str, keep_default_na=False)
    cert = pd.read_csv(OUT / "2026-10-06_2026_APPRAISAL_INFO.csv.gz", dtype=str, keep_default_na=False,
                       usecols=["prop_id", "prop_val_yr", "sup_num", "hood_cd", "market_value", "situs_city", "arb_protest_flag"])
    cert = cert[cert.prop_val_yr.str.strip().str.lstrip("0").eq("2026")].copy()
    cert["prop_id"] = cert.prop_id.str.strip().str.lstrip("0")
    cert["sup_n"] = num(cert.sup_num)
    cert = cert.sort_values(["prop_id", "sup_n"]).drop_duplicates("prop_id", keep="last")
    cert["cert_market"] = num(cert.market_value)
    print(f"certified rows (2026, one per prop): {len(cert):,}")

    a = a[a.appealType.eq("P")].copy()
    a["agent"] = a.appealedByAgentID.str.replace(r"\.0$", "", regex=True)
    a["is_our"] = a.agent.isin(OUR_IDS)
    a["fin"] = a.finalized.eq("1")
    st = a.appealStatus.str.strip()
    a["path"] = np.select(
        [~a.fin, st.eq("FTA"), st.isin(["W", "EF_WD"]), st.isin(["D", "LD"]),
         st.isin(["ORDT", "EF_AS", "I"]) | a.valueDecisionAdjustmentType.eq("I"),
         st.str.startswith("ORD") | a.valueDecisionAdjustmentType.eq("F")],
        ["Open", "No-show", "Withdrawn", "Dismissed", "Informal", "ARB"], default="Other")
    a["rank"] = a.path.map({"Informal": 0, "ARB": 0, "Other": 1, "Open": 2, "No-show": 3, "Withdrawn": 3, "Dismissed": 3})
    a["aid"] = num(a.appealID)
    ours_p = set(a.loc[a.is_our, "pID"])
    a["ours_acct"] = a.pID.isin(ours_p)
    g = a.groupby("pID")
    filers = a.assign(f=np.where(a.agent.ne(""), "agent " + a.agent, a.appealedByType)).groupby("pID").f.agg(lambda s: " | ".join(sorted(set(s))))
    a["n_appeals"] = g.pID.transform("size")
    cand = a[~a.ours_acct | a.is_our].sort_values(["pID", "rank", "aid"], ascending=[True, True, False])
    pick = cand.drop_duplicates("pID").copy()
    pick["filers"] = pick.pID.map(filers)
    print(f"2026 protests (type P): {len(a):,} appeals on {len(pick):,} properties; ours {len(ours_p):,}")

    v = p.merge(pick[["pID", "appealID", "appealStatus", "path", "agent", "appealedByType", "is_our", "n_appeals", "filers",
                      "finalizedDt", "docketDt", "informalStartMeeting", "formalStartMeeting", "informalAppraiser",
                      "formalAppraiser", "panelMembers", "claimantOpinionOfValue", "finalMarketValue"]],
                on="pID", how="left")
    v = v.merge(cert[["prop_id", "hood_cd", "cert_market", "situs_city"]], left_on="pID", right_on="prop_id", how="left")
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
    miss_f = v.final_value.isna()
    v.loc[miss_f, "final_value"] = v.loc[miss_f, "cert_market"].fillna(v.loc[miss_f, "current_market"])
    v.loc[miss_f & v.protested & v.path.eq("Open"), "final_source"] = "certified (appeal open)"
    v.loc[miss_f & v.protested & v.path.ne("Open"), "final_source"] = "certified (no final value)"
    v.loc[miss_f & ~v.protested, "final_source"] = "certified (not protested)"
    # a closed appeal with no change: final = notice
    nochg = v.protested & v.path.isin(["No-show", "Withdrawn", "Dismissed"]) & v.final_value.isna()
    v.loc[nochg, "final_value"] = v.loc[nochg, "notice_value"]

    v["reduction"] = v.notice_value - v.final_value
    v["reduction_pct"] = (v.reduction / v.notice_value).where(v.notice_value > 0)
    v["final_vs_cert"] = (v.final_value - v.cert_market)
    v["check_values"] = v.protested & ((v.notice_value.fillna(0) <= 0) | (v.final_value > v.notice_value * 1.25))
    v["outcome"] = np.select([~v.protested, v.path.eq("Open"), v.reduction > 0, v.reduction < 0],
                             ["Not protested", "Open", "Reduced", "Increased"], default="No change")
    v["nb"] = v.marketArea.where(v.marketArea.ne(""), v.hood_cd)
    v["homestead"] = v.exemptions.str.contains(r"\bHS\b", regex=True)
    v["est_fee_1pct"] = (v.reduction.clip(lower=0) * 0.01).where(v.is_ours & v.path.ne("Open"))
    v = v.drop(columns=["prop_id", "is_our", "final_market", "initial_market"])
    v.to_csv(OUT / "travis_values_2026.csv", index=False)

    pr = v[v.protested]
    print(f"travis_values_2026.csv: {len(v):,} properties, {len(pr):,} protested")
    print("path", pr.path.value_counts().to_dict())
    print("notice source", pr.notice_source.value_counts(dropna=False).to_dict())
    print("final source", pr.final_source.value_counts(dropna=False).to_dict())
    print("flagged", int(pr.check_values.sum()), "| ours flagged", int(pr[pr.is_ours].check_values.sum()))
    cl = pr[pr.path.ne("Open") & pr.final_source.eq("appeal")]
    print("final == certified (closed, appeal values):", f"{(cl.final_vs_cert.abs() <= 2).mean():.1%} of {cl.final_vs_cert.notna().sum():,}")
    o = pr[pr.is_ours]
    print("ours", len(o), o.path.value_counts().to_dict(), "| win", f"{(o[o.path.ne('Open')].reduction > 0).mean():.1%}",
          "| cut %", f"{o[o.path.ne('Open')].reduction.sum() / o[o.path.ne('Open')].notice_value.sum():.1%}")


if __name__ == "__main__":
    main()
