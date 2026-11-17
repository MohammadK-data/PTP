"""Tarrant 2026: every Property Tax Protest (agent 1487) protested account - full detail file and simple results file.

Base: Scorecard Data/Tarrant/tarrant_values_2026.csv rows with is_ours = True (4,064 accounts:
Informal (joint motion) 3,917 / Failure to appear 74 / ARB hearing 63 / Open 7 / Withdrawn / dismissed 3).

Sources (CAD Website/Tarrant)
    output/tarrant_property_2026_dedup.csv            2026 roll, one row per account -> roll_* columns
    Data/ORR20261019 - ... ARB Info 2026.csv          every 2026 case -> case_* (all cases on the account)
    output/tarrant_roll_values_2025.csv               2025 certified roll value (prior year)
    output/tarrant_history.csv                        2024 / 2025 protest per account -> hist_*

Outputs (CAD Website/Scorecard Data/Tarrant)
    tarrant_ptp_accounts_2026.csv   everything per account (scorecard fields, roll, all cases, history)
    tarrant_ptp_results_2026.csv    simple: what happened, property type, values, dates (same layout as Dallas)

Note: 2025 Final Value comes from tarrant_roll_values_2025.csv. The scorecard's prior_year_value is blank for
2,788 of our accounts, so it is not used here.

Run:  .venv/bin/python -I "CAD Website/Tarrant/etl/tarrant_ptp_accounts_2026_build.py"
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUTD = ROOT / "output"
SC = ROOT.parent / "Scorecard Data" / "Tarrant"
ARB = ROOT / "Data" / "ORR20261019 - Avetik Ghazaryan - ARB Info 2026.csv"
OUR = "1487"

RESULT = {"ARB hearing": "1. ARB Hearing", "Informal (joint motion)": "2. Informal Settlement (Joint Motion)",
          "Withdrawn / dismissed": "3. Withdrawn / Dismissed", "Failure to appear": "4. Failure to Appear / No-Show",
          "Open": "5. Open - No Result Yet"}
PTYPE = {"R": "Residential", "C": "Commercial", "P": "Business Personal Property"}
# TAD property class (state code); a trailing C = the same class carried on a commercial account
PCLASS = {"A": "Single-Family Home", "AC": "Single-Family Home (commercial account)", "B": "Multifamily (duplex etc.)",
          "BC": "Multifamily / Apartments", "C1": "Vacant Lot - Residential", "C1C": "Vacant Lot - Commercial",
          "D1": "Agricultural Land", "E": "Rural Land with Home", "F1": "Commercial Building",
          "F2": "Industrial Building", "L1": "Business Personal Property", "M1": "Mobile Home",
          "O": "Residential Inventory (builder lot / new home)"}


def num(s):
    return pd.to_numeric(s, errors="coerce")


def day(s):
    s = s.fillna("").astype(str).str[:10]
    return s.where(~s.str.startswith("1900"), "")


def money(x):
    return "" if pd.isna(x) else f"${x:,.0f}"


def join_unique(s):
    return " | ".join(x for x in dict.fromkeys(s) if x)


def main():
    v = pd.read_csv(SC / "tarrant_values_2026.csv", dtype=str, keep_default_na=False)
    v = v[v.is_ours.eq("True")].copy()
    accts = set(v.Account_Num)
    print(f"our accounts: {len(v):,} {v.path.value_counts().to_dict()}")

    # ---- 2026 roll, full row
    roll = pd.concat(ch[ch.Account_Num.isin(accts)] for ch in
                     pd.read_csv(OUTD / "tarrant_property_2026_dedup.csv", dtype=str, keep_default_na=False,
                                 chunksize=300_000))
    roll = roll.drop_duplicates("Account_Num").set_index("Account_Num").add_prefix("roll_")

    # ---- every 2026 case on the account
    arb = pd.read_csv(ARB, dtype=str, keep_default_na=False).drop_duplicates()
    arb = arb[arb.pID.isin(accts)].apply(lambda s: s.str.strip())
    arb["who"] = arb.AppellantName + np.where(arb.agentID.ne(""), " (" + arb.agentID + ")", "")
    arb["case"] = arb.CaseNumber + " " + arb.CaseStatus
    g = arb.sort_values(["pID", "CaseNumber"]).groupby("pID")
    cases = pd.DataFrame({"case_count": g.CaseNumber.nunique(), "case_all": g.case.agg(join_unique),
                          "case_filers_all": g.who.agg(join_unique)})

    # ---- prior year and history
    p25 = pd.read_csv(OUTD / "tarrant_roll_values_2025.csv", dtype=str, keep_default_na=False)
    p25 = num(p25.drop_duplicates("pid").set_index("pid").value)
    h = pd.read_csv(OUTD / "tarrant_history.csv", dtype=str, keep_default_na=False)
    h = h[h.pid.isin(accts) & h.year.isin(["2024", "2025"])]
    hist = pd.DataFrame(index=sorted(accts))
    for yr in ["2025", "2024"]:
        y = h[h.year.eq(yr)].drop_duplicates("pid").set_index("pid")
        hist[f"hist_{yr}_filer"] = np.where(y.reindex(hist.index).who.eq("agent"), y.reindex(hist.index).firm,
                                            y.reindex(hist.index).who)
        for c in ["path", "notice", "final", "reduction"]:
            hist[f"hist_{yr}_{c}"] = y[c].reindex(hist.index)
    hist = hist.replace("", np.nan)

    full = v.set_index("Account_Num", drop=False)
    full["value_2025_roll"] = full.index.map(p25)
    for part in [roll, cases, hist]:
        full = full.join(part)
    full = full.reset_index(drop=True)
    full = full.loc[:, ~full.astype(str).isin(["", "nan", "<NA>", "None"]).all()]
    full.to_csv(SC / "tarrant_ptp_accounts_2026.csv", index=False)
    print(f"tarrant_ptp_accounts_2026.csv: {len(full):,} rows x {full.shape[1]} columns")

    # ---- simple results file
    d = full
    notice, final = num(d.notice_value), num(d.final_value)
    final = final.where(d.path.ne("Open"))                      # open: no final yet
    prior = num(d.value_2025_roll)
    cut = notice - final
    rp = d.RP.where(d.RP.ne(""), d.get("roll_RP", d.RP))
    code = d.Property_Class.str.strip()
    what = np.select(
        [d.path.eq("Open"), d.path.eq("Withdrawn / dismissed"), d.path.eq("Failure to appear") & (cut <= 0),
         cut > 0, cut < 0],
        ["Protest still open - no final value yet",
         "Protest withdrawn / dismissed - value stayed at " + notice.map(money),
         "Failure to appear - value stayed at " + notice.map(money),
         "Value cut from " + notice.map(money) + " to " + final.map(money) + " (-" + cut.map(money) + ")",
         "Value went UP from " + notice.map(money) + " to " + final.map(money)],
        default="No change - value stayed at " + notice.map(money))
    filed = np.select([d.AppellantType.eq("Owner"), d.AppellantType.eq("Other")],
                      ["Owner (we are agent)", "Appraisal district (we are agent)"], default="Us (agent)")
    out = pd.DataFrame({
        "Account": d.Account_Num,
        "Result": d.path.map(RESULT),
        "Value Change": d.outcome,
        "Property Type": rp.map(PTYPE).fillna("Unknown (not in 2026 roll file)"),
        "Property Class": np.where(code.ne(""), code.map(PCLASS).fillna("Other") + " (" + code + ")", "Unknown"),
        "Owner": d.Owner_Name.str.strip(),
        "Filed By": filed,
        "Other Agent on Case": np.where(d.shared_with_other_agent.eq("True"),
                                        d.agents_on_case.str.replace(r"\s*\|?\s*PROPERTY TAX PROTEST \(1487\)\s*\|?\s*",
                                                                     " | ", regex=True).str.strip(" |"), ""),
        "2025 Final Value": prior.round(0),
        "2026 Notice Value": notice.round(0),
        "2026 Final Value": final.round(0),
        "Reduction $": cut.round(0),
        "Reduction %": (cut / notice * 100).round(1).where(notice > 0),
        "Change vs 2025 $": (final - prior).round(0),
        "Est. Fee (1% of reduction)": num(d.est_fee_1pct).where(d.path.ne("Open")).round(2),
        "Protest Filed": day(d.ProtestFilingDate),
        "Hearing Date": day(d.ScheduledHearingDate),
        "Settled / Resolved Date": day(d.finalizedDt),
        "TAD Case Status": d.CaseStatus,
        "Case Number": d.CaseNumber,
        "What Happened": what,
    })
    for c in ["2025 Final Value", "2026 Notice Value", "2026 Final Value", "Reduction $", "Change vs 2025 $"]:
        out[c] = out[c].astype("Int64")
    out = out.sort_values(["Result", "Property Type", "Account"], key=lambda s: s if s.name != "Account" else num(s))
    out.to_csv(SC / "tarrant_ptp_results_2026.csv", index=False)
    print(f"tarrant_ptp_results_2026.csv: {len(out):,} rows x {out.shape[1]} columns")
    pd.set_option("display.width", 200)
    print(pd.crosstab(out.Result, out["Property Type"], margins=True))
    print(pd.crosstab(out.Result, out["Value Change"]))
    print(out["Property Class"].value_counts().to_dict())


if __name__ == "__main__":
    main()
