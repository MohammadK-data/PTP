"""Dallas 2026: one row per account with notice / final market value and how the protest went.

Sources (CAD Website/Dallas/Data)
    dcad_download_20261114/ARB_ARCHIVE/ARB_ARCHIVE.CSV   DCAD protest file, 2022-2026, closed by Jul 20 2026
    dcad_download_20261114/ARB_CURRENT/ARB_CURRENT.csv   DCAD protest file of Nov 9 2026 (protests still open after July)
    DCAD2026_CURRENT/  ACCOUNT_APPRL_YEAR, ACCOUNT_INFO, RES_DETAIL, APPLIED_STD_EXEMPT  (roll of Oct 30 2026)
    DCAD2026_CERTIFIED_07232026/ ACCOUNT_APPRL_YEAR       fallback for accounts the current roll leaves out
    DCAD2027_CURRENT/ ACCOUNT_APPRL_YEAR, ACCOUNT_INFO, RES_DETAIL   state code / address / home traits for 2026
                                                          protests missing from both 2026 files (still open then)
    Market Analysis/work/dallas/tax_rep_names.csv         tax rep ID -> name

Rules (DCAD "ARB Data Descriptions 08-16-16")
    Protest = a 2026 row that is not exemption-only (PROTEST_RCVD_CDX X) and not a 25.25 motion (P2525*_IND Y).
    ARB_CURRENT is the later file: an account found there takes its rows from there, else from ARB_ARCHIVE.
    One row per account: ours first (AUTH_TAX_REP_ID 306), then settled > open > no result, then the lowest final.
    Notice = NOTIFIED_VAL.
    Path:  RESOLVED_CDX F  -> ARB (final = PANEL_VAL, else NEW_VAL)
           PROTEST_WD_CDX D -> Dismissed / no-show (final = notice)
           CONSENT_CDX P    -> Informal (consented to the informal value; final = NEW_VAL)
           PROTEST_WD_CDX W/P with RESOLVED_CDX X -> Withdrawn (final = NEW_VAL if DCAD changed it, else notice)
           CONSENT_CDX X or RESOLVED_CDX X -> Informal
           anything else    -> Open (no final yet)
    Filed by: OWNER_PROTEST_IND N = the tax agent filed, Y = the owner.
    Same mapping the developers' Dallas file uses (it labels F rows ARB hearing, incl. "ARB order at the informal value").

Output: output/dallas_values_2026.csv
Run:    .venv/bin/python -I "CAD Website/Dallas/etl/dallas_values_2026_build.py"
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA, OUT = ROOT / "Data", ROOT / "output"
DL = DATA / "dcad_download_20261114"
REPS = ROOT.parent.parent / "Market Analysis" / "work" / "dallas" / "tax_rep_names.csv"
OUR = "306"
YEAR = "2026"
ARB_COLS = ["PROTEST_YR", "ACCOUNT_NUM", "OWNER_PROTEST_IND", "PROTEST_WD_CDX", "PROTEST_RCVD_CDX", "CONSENT_CDX",
            "RESOLVED_CDX", "RESOLVED_DT", "CONSENT_DT", "P2525C1_IND", "P2525D_IND", "P2525H_IND", "P2525C2_IND",
            "P2525C3_IND", "P2525B_IND", "AUTH_TAX_REP_ID", "ARB_PANEL", "HEARING_DT", "NOTIFIED_VAL", "NEW_VAL",
            "PANEL_VAL", "ACCT_TYPE"]


def num(s):
    return pd.to_numeric(s, errors="coerce")


def read_arb(path, src):
    parts = []
    for ch in pd.read_csv(path, dtype=str, keep_default_na=False, usecols=lambda c: c in ARB_COLS, chunksize=500_000):
        parts.append(ch[ch.PROTEST_YR.str.strip().eq(YEAR)])
    a = pd.concat(parts).apply(lambda s: s.str.strip())
    a["src"] = src
    print(f"{path.name}: {len(a):,} {YEAR} rows")
    return a


def classify(a):
    wd, rs, cs = a.PROTEST_WD_CDX, a.RESOLVED_CDX, a.CONSENT_CDX
    notice, new, panel = num(a.NOTIFIED_VAL), num(a.NEW_VAL), num(a.PANEL_VAL)
    path = np.select([rs.eq("F"), wd.eq("D"), cs.eq("P"), wd.isin(["W", "P"]) & rs.eq("X"), cs.eq("X") | rs.eq("X")],
                     ["ARB", "Dismissed", "Informal", "Withdrawn", "Informal"], default="Open")
    final = np.select([path == "ARB", path == "Dismissed", path == "Informal", path == "Withdrawn"],
                      [panel.where(panel > 0, new.where(new > 0, notice)), notice, new.where(new > 0, notice),
                       new.where(new > 0, notice)], default=np.nan)
    return path, notice, final


def main():
    arch = read_arb(DL / "ARB_ARCHIVE/ARB_ARCHIVE.CSV", "archive Jul 20")
    cur = read_arb(DL / "ARB_CURRENT/ARB_CURRENT.csv", "current Nov 9")
    a = pd.concat([cur, arch[~arch.ACCOUNT_NUM.isin(set(cur.ACCOUNT_NUM))]], ignore_index=True)
    p2525 = a[[c for c in a.columns if c.startswith("P2525")]].eq("Y").any(axis=1)
    a = a[~a.PROTEST_RCVD_CDX.eq("X") & ~p2525].copy()
    a["path"], a["notice"], a["final"] = classify(a)
    a["rank"] = a.path.map({"Informal": 0, "ARB": 0, "Open": 1, "Withdrawn": 2, "Dismissed": 2})
    a["our_row"] = a.AUTH_TAX_REP_ID.eq(OUR)
    ours = set(a.loc[a.our_row, "ACCOUNT_NUM"])
    a["n_rows"] = a.groupby("ACCOUNT_NUM").ACCOUNT_NUM.transform("size")
    a = a[~a.ACCOUNT_NUM.isin(ours) | a.our_row]
    p = a.sort_values(["ACCOUNT_NUM", "rank", "final"]).drop_duplicates("ACCOUNT_NUM").copy()
    print(f"protests: {len(p):,} accounts; ours {p.our_row.sum():,}; {p.path.value_counts().to_dict()}")

    # ---- roll attributes
    yr = pd.read_csv(DATA / "DCAD2026_CURRENT/ACCOUNT_APPRL_YEAR.CSV", dtype=str, keep_default_na=False,
                     usecols=["ACCOUNT_NUM", "TOT_VAL", "TAXPAYER_REP", "SPTD_CODE", "DIVISION_CD", "CITY_JURIS_DESC"])
    cert = pd.read_csv(DATA / "DCAD2026_CERTIFIED_07232026/ACCOUNT_APPRL_YEAR.CSV", dtype=str, keep_default_na=False,
                       usecols=["ACCOUNT_NUM", "TOT_VAL", "TAXPAYER_REP", "SPTD_CODE", "DIVISION_CD", "CITY_JURIS_DESC"])
    # accounts still under protest when the 2026 files were cut are missing from both; take state code from 2027
    nxt = pd.read_csv(DATA / "DCAD2027_CURRENT/ACCOUNT_APPRL_YEAR.CSV", dtype=str, keep_default_na=False,
                      usecols=["ACCOUNT_NUM", "TOT_VAL", "TAXPAYER_REP", "SPTD_CODE", "DIVISION_CD", "CITY_JURIS_DESC"])
    nxt["TOT_VAL"], nxt["TAXPAYER_REP"] = "", ""                    # 2027 value and rep are not 2026 facts
    yr = pd.concat([yr, cert[~cert.ACCOUNT_NUM.isin(set(yr.ACCOUNT_NUM))]])
    yr = pd.concat([yr, nxt[~nxt.ACCOUNT_NUM.isin(set(yr.ACCOUNT_NUM))]]).drop_duplicates("ACCOUNT_NUM").set_index("ACCOUNT_NUM")

    info = pd.read_csv(DATA / "DCAD2026_CURRENT/ACCOUNT_INFO.CSV", dtype=str, keep_default_na=False,
                       usecols=["ACCOUNT_NUM", "OWNER_NAME1", "STREET_NUM", "FULL_STREET_NAME", "UNIT_ID", "PROPERTY_CITY",
                                "PROPERTY_ZIPCODE", "NBHD_CD"]).drop_duplicates("ACCOUNT_NUM").set_index("ACCOUNT_NUM")
    res = pd.read_csv(DATA / "DCAD2026_CURRENT/RES_DETAIL.CSV", dtype=str, keep_default_na=False,
                      usecols=["ACCOUNT_NUM", "YR_BUILT", "TOT_LIVING_AREA_SF"]).drop_duplicates("ACCOUNT_NUM").set_index("ACCOUNT_NUM")
    info2 = pd.read_csv(DATA / "DCAD2027_CURRENT/ACCOUNT_INFO.CSV", dtype=str, keep_default_na=False, usecols=list(info.columns.insert(0, "ACCOUNT_NUM"))).drop_duplicates("ACCOUNT_NUM").set_index("ACCOUNT_NUM")
    info = pd.concat([info, info2[~info2.index.isin(info.index)]])
    res2 = pd.read_csv(DATA / "DCAD2027_CURRENT/RES_DETAIL.CSV", dtype=str, keep_default_na=False, usecols=["ACCOUNT_NUM", "YR_BUILT", "TOT_LIVING_AREA_SF"]).drop_duplicates("ACCOUNT_NUM").set_index("ACCOUNT_NUM")
    res = pd.concat([res, res2[~res2.index.isin(res.index)]])
    hs = pd.read_csv(DATA / "DCAD2026_CURRENT/APPLIED_STD_EXEMPT.CSV", dtype=str, keep_default_na=False,
                     usecols=["ACCOUNT_NUM", "HOMESTEAD_EFF_DT"])
    hs = set(hs.loc[hs.HOMESTEAD_EFF_DT.str.strip().ne(""), "ACCOUNT_NUM"])
    reps = pd.read_csv(REPS, dtype=str, keep_default_na=False).drop_duplicates("rep_id").set_index("rep_id").name

    acct = p.ACCOUNT_NUM
    roll_rep = acct.map(yr.TAXPAYER_REP).fillna("")
    roll_rep_id = roll_rep.str.extract(r"^(\S+)\s")[0].where(~roll_rep.str.startswith("UNASSIGNED"), "").fillna("")
    agent = p.AUTH_TAX_REP_ID
    v = pd.DataFrame({
        "pID": acct.str.lstrip("0"), "account": acct, "propType": p.ACCT_TYPE, "stateCd": acct.map(yr.SPTD_CODE).fillna(""),
        "protested": True, "is_ours": p.our_row,
        "appealedByType": np.where(p.OWNER_PROTEST_IND.eq("Y"), "Owner", "Agent"),
        "agent": agent, "agent_name": agent.map(reps).fillna(""),
        "agent_ids_all": roll_rep_id, "agents_current": np.where(roll_rep_id.ne(""), roll_rep.str.replace(r"^(\S+)\s+(.*)$", r"\2 (\1)", regex=True), ""),
        "agents_all": np.where(roll_rep_id.ne(""), roll_rep.str.replace(r"^(\S+)\s+(.*)$", r"\2 (\1)", regex=True), ""),
        "path": p.path, "status": (p.RESOLVED_CDX + "/" + p.CONSENT_CDX + "/" + p.PROTEST_WD_CDX),
        "source": p.src, "rows_for_account": p.n_rows,
        "notice_value": p.notice, "final_value": p.final, "roll_value": num(acct.map(yr.TOT_VAL)),
        "situs": (acct.map(info.STREET_NUM).fillna("") + " " + acct.map(info.FULL_STREET_NAME).fillna("")).str.strip(),
        "owner": acct.map(info.OWNER_NAME1).fillna(""), "city": acct.map(info.PROPERTY_CITY).fillna("").str.strip(),
        "zip": acct.map(info.PROPERTY_ZIPCODE).fillna("").str.strip(), "nb": acct.map(info.NBHD_CD).fillna(""),
        "yrb": acct.map(res.YR_BUILT).fillna(""), "sf": acct.map(res.TOT_LIVING_AREA_SF).fillna(""),
        "homestead": acct.isin(hs), "hearing_dt": p.HEARING_DT.str[:10], "resolved_dt": p.RESOLVED_DT.str[:10],
        "consent_dt": p.CONSENT_DT.str[:10], "arb_panel": p.ARB_PANEL})
    v["reduction"] = v.notice_value - v.final_value
    v["reduction_pct"] = (v.reduction / v.notice_value).where(v.notice_value > 0)
    v["check_values"] = (v.notice_value.fillna(0) <= 0) | (v.final_value > v.notice_value * 1.25)
    v.loc[v.path.eq("Open"), "check_values"] = False
    v["outcome"] = np.select([v.path.eq("Open"), v.reduction > 0, v.reduction < 0], ["Open", "Reduced", "Increased"], default="No change")
    v["est_fee_1pct"] = (v.reduction.clip(lower=0) * 0.01).where(v.is_ours & v.path.ne("Open"))
    # accounts that list us on the roll but had no 2026 protest (for the client-list funnel)
    rr = yr.TAXPAYER_REP.str.startswith(OUR + " ")
    extra = yr[rr & ~yr.index.isin(set(acct))]
    if len(extra):
        e = pd.DataFrame({"pID": extra.index.str.lstrip("0"), "account": extra.index, "stateCd": extra.SPTD_CODE.values,
                          "protested": False, "is_ours": False, "agent_ids_all": OUR,
                          "agents_current": extra.TAXPAYER_REP.str.replace(r"^(\S+)\s+(.*)$", r"\2 (\1)", regex=True).values,
                          "path": "", "roll_value": num(extra.TOT_VAL).values})
        e["agents_all"] = e.agents_current
        v = pd.concat([v, e], ignore_index=True)
        print(f"added {len(e):,} roll accounts listing rep {OUR} with no 2026 protest")
    v.to_csv(OUT / "dallas_values_2026.csv", index=False)

    v = v[v.protested.eq(True)]
    o = v[v.is_ours]
    oc = o[o.path.ne("Open") & ~o.check_values]
    print(f"dallas_values_2026.csv: {len(v):,} protested accounts")
    print(f"ours {len(o):,}: {o.path.value_counts().to_dict()} | closed {len(oc):,}, win {(oc.reduction > 0).mean():.1%}, "
          f"cut {oc.reduction.sum() / oc.notice_value.sum():.1%} | source {o.source.value_counts().to_dict()}")
    print("roll rep 306 on our accounts:", f"{o.agent_ids_all.eq(OUR).mean():.1%}", "| missing state code:", int(v.stateCd.eq("").sum()))


if __name__ == "__main__":
    main()
