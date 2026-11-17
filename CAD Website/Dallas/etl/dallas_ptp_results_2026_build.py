"""Dallas 2026: simple results sheet for our (rep 306) protested accounts - what happened and the values.

Input:  Scorecard Data/Dallas/dallas_ptp_accounts_2026.csv  (from dallas_ptp_accounts_2026_build.py, run that first)
        Data/dcad_download_20261114/DCAD2025_CURRENT/ACCOUNT_APPRL_YEAR.CSV  (2025 final value)
Output: Scorecard Data/Dallas/dallas_ptp_results_2026.csv - one row per account, plain-English columns,
        sorted by Result, then Property Type, then account.
Run:    .venv/bin/python -I "CAD Website/Dallas/etl/dallas_ptp_results_2026_build.py"
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SC = ROOT.parent / "Scorecard Data" / "Dallas"
Y25 = ROOT / "Data" / "dcad_download_20261114" / "DCAD2025_CURRENT" / "ACCOUNT_APPRL_YEAR.CSV"

RESULT = {"ARB": "1. ARB Hearing", "Informal": "2. Informal Settlement", "Withdrawn": "3. Withdrawn",
          "Dismissed": "4. Dismissed / No-Show", "Open": "5. Open - No Result Yet"}
PTYPE = {"RES": "Residential", "COM": "Commercial", "BPP": "Business Personal Property"}
# DCAD SPTD code -> property class (Data/DCAD2026_CURRENT/SPTD_CD_XREF.pdf)
PCLASS = {"A11": "Single-Family Home", "A12": "Townhouse", "A13": "Condo", "A20": "Mobile Home on Owner's Land",
          "B11": "Apartments", "B12": "Duplex", "C11": "Vacant Lot - Residential", "C12": "Vacant Lot - Commercial",
          "C13": "Vacant Lot - Industrial", "C14": "Rural Vacant (<5 acres)", "D10": "Agricultural Land",
          "D20": "Non-Qualified Land", "F10": "Commercial Building", "F20": "Industrial Building",
          "L10": "Commercial Business Property", "L20": "Industrial Business Property",
          "M31": "Mobile Home on Leased Space", "M32": "Mobile Home for Sale"}


def num(s):
    return pd.to_numeric(s, errors="coerce")


def day(s):
    s = s.fillna("").str[:10]
    return s.where(~s.str.startswith("1900"), "")


def money(x):
    return "" if pd.isna(x) else f"${x:,.0f}"


def main():
    d = pd.read_csv(SC / "dallas_ptp_accounts_2026.csv", dtype=str, keep_default_na=False)
    v25 = pd.read_csv(Y25, dtype=str, keep_default_na=False, usecols=["ACCOUNT_NUM", "TOT_VAL"])
    v25 = num(v25.drop_duplicates("ACCOUNT_NUM").set_index("ACCOUNT_NUM").TOT_VAL.str.strip())

    notice, final = num(d.notice_value), num(d.final_value)
    prior = d.account.map(v25)
    cut = notice - final
    pct = (cut / notice * 100).round(1)
    settled = day(d.resolved_dt).where(day(d.resolved_dt).ne(""), day(d.consent_dt))
    code = d.stateCd.str.strip()

    what = np.select(
        [d.path.eq("Open"),
         d.path.eq("Withdrawn"),
         d.path.eq("Dismissed"),
         cut > 0],
        ["Protest still open - no final value yet",
         "Protest withdrawn - value stayed at " + notice.map(money),
         "Protest dismissed / no-show - value stayed at " + notice.map(money),
         "Value cut from " + notice.map(money) + " to " + final.map(money) + " (-" + cut.map(money) + ")"],
        default="No change - value stayed at " + notice.map(money))

    out = pd.DataFrame({
        "Account": d.account,
        "Result": d.path.map(RESULT),
        "Value Change": d.outcome,
        "Property Type": d.propType.map(PTYPE).fillna(d.propType),
        "Property Class": code.map(PCLASS).fillna("Other") + " (" + code + ")",
        "Owner": d.owner.str.strip(),
        "Filed By": np.where(d.appealedByType.eq("Owner"), "Owner (we are agent)", "Us (agent)"),
        "2025 Final Value": prior.round(0),
        "2026 Notice Value": notice.round(0),
        "2026 Final Value": final.round(0),
        "Reduction $": cut.round(0),
        "Reduction %": pct,
        "Change vs 2025 $": (final - prior).round(0),
        "Est. Fee (1% of reduction)": num(d.est_fee_1pct).round(2),
        "Protest Received": day(d.arb_PROTEST_RCVD_DT),
        "Hearing Date": day(d.hearing_dt),
        "Settled / Resolved Date": settled,
        "ARB Panel": d.arb_panel.str.strip(),
        "What Happened": what,
    })
    for c in ["2025 Final Value", "2026 Notice Value", "2026 Final Value", "Reduction $", "Change vs 2025 $"]:
        out[c] = out[c].astype("Int64")
    out = out.sort_values(["Result", "Property Type", "Account"]).reset_index(drop=True)
    dest = SC / "dallas_ptp_results_2026.csv"
    out.to_csv(dest, index=False)
    print(f"{dest.name}: {len(out):,} rows x {out.shape[1]} columns")
    print(pd.crosstab(out.Result, out["Property Type"], margins=True))
    print(pd.crosstab(out.Result, out["Value Change"]))


if __name__ == "__main__":
    main()
