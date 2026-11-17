"""Dallas 2026: every Property Tax Protest (rep 306) protested account, one row each, with all related details.

Base: Scorecard Data/Dallas/dallas_values_2026.csv rows with is_ours = True (3,869 accounts:
ARB 3,617 / Withdrawn 198 / Dismissed 45 / Informal 7 / Open 2). Columns added per account:

    (no prefix)  scorecard fields: path, notice / final value, reduction, outcome, fee estimate ...
    arb_*        the full 2026 DCAD protest row for our protest (ARB_CURRENT Nov 9, else ARB_ARCHIVE Jul 20)
    hist_*       2022-2025 protest history from ARB_ARCHIVE (years, agents, notice/final values)
    roll_source  which roll file the roll details came from (2026 current / 2026 certified / 2027 current)
    info_*       ACCOUNT_INFO (owner, mailing address, situs, legal, neighborhood, deed date)
    appr_*       ACCOUNT_APPRL_YEAR (values, jurisdictions, taxable values, rep, state code)
    res_*        RES_DETAIL main building (+ building count); addl_* RES_ADDL summary
    com_*        COM_DETAIL main building (+ building count, total gross area)
    land_*       LAND summary (sections, area, value, zoning)
    exm_*        exemptions (applied standard exemption, exemption values, total exemption, abatement, freeport)
    owners_all, tif_zone

Roll source per account: the first of DCAD2026_CURRENT, DCAD2026_CERTIFIED_07232026, DCAD2027_CURRENT that has
the account. Accounts still under protest when the 2026 files were cut are only in the 2027 file, so their roll
details are 2027 facts (flagged by roll_source).

Output: CAD Website/Scorecard Data/Dallas/dallas_ptp_accounts_2026.csv
Run:    .venv/bin/python -I "CAD Website/Dallas/etl/dallas_ptp_accounts_2026_build.py"
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "Data"
DL = DATA / "dcad_download_20261114"
SC = ROOT.parent / "Scorecard Data" / "Dallas"
REPS = ROOT.parent.parent / "Market Analysis" / "work" / "dallas" / "tax_rep_names.csv"
OUR, YEAR = "306", "2026"
ROLLS = [("2026 current", DATA / "DCAD2026_CURRENT"), ("2026 certified", DATA / "DCAD2026_CERTIFIED_07232026"),
         ("2027 current", DATA / "DCAD2027_CURRENT")]


def read_for(path, accts, **kw):
    parts = [ch[ch.ACCOUNT_NUM.isin(accts)] for ch in
             pd.read_csv(path, dtype=str, keep_default_na=False, chunksize=500_000, encoding="latin-1", **kw)]
    return pd.concat(parts).apply(lambda s: s.str.strip())


def num(s):
    return pd.to_numeric(s, errors="coerce")


def join_unique(s):
    vals = [x for x in dict.fromkeys(s) if x]
    return " | ".join(vals)


def main():
    v = pd.read_csv(SC / "dallas_values_2026.csv", dtype=str, keep_default_na=False)
    v = v[v.is_ours.eq("True")].copy()
    accts = set(v.account)
    print(f"our accounts: {len(v):,} {v.path.value_counts().to_dict()}")

    # ---- full 2026 protest row (same selection as dallas_values_2026_build.py)
    cur = read_for(DL / "ARB_CURRENT/ARB_CURRENT.csv", accts)
    arch = read_for(DL / "ARB_ARCHIVE/ARB_ARCHIVE.CSV", accts)
    hist = arch[arch.PROTEST_YR.isin(["2022", "2023", "2024", "2025"])].copy()
    c26, a26 = cur[cur.PROTEST_YR.eq(YEAR)], arch[arch.PROTEST_YR.eq(YEAR)]
    a = pd.concat([c26, a26[~a26.ACCOUNT_NUM.isin(set(c26.ACCOUNT_NUM))]], ignore_index=True)
    p2525 = a[[c for c in a.columns if c.startswith("P2525")]].eq("Y").any(axis=1)
    a = a[~a.PROTEST_RCVD_CDX.eq("X") & ~p2525 & a.AUTH_TAX_REP_ID.eq(OUR)]
    a = a.assign(_rk=a.RESOLVED_CDX.eq("F").map({True: 0, False: 1})).sort_values(["ACCOUNT_NUM", "_rk"])
    a = a.drop_duplicates("ACCOUNT_NUM").drop(columns="_rk").set_index("ACCOUNT_NUM")
    a.columns = ["arb_" + c for c in a.columns]
    print(f"2026 protest rows matched: {len(a):,}")

    # ---- 2022-2025 protest history
    reps = pd.read_csv(REPS, dtype=str, keep_default_na=False).drop_duplicates("rep_id").set_index("rep_id").name
    hist["who"] = np.where(hist.AUTH_TAX_REP_ID.ne(""),
                           hist.AUTH_TAX_REP_ID.map(reps).fillna("").str.strip() + " (" + hist.AUTH_TAX_REP_ID + ")",
                           np.where(hist.OWNER_PROTEST_IND.eq("Y"), "Owner", ""))
    hist = hist.sort_values(["ACCOUNT_NUM", "PROTEST_YR"])
    g = hist.groupby("ACCOUNT_NUM")
    h = pd.DataFrame({"hist_protest_years": g.PROTEST_YR.agg(join_unique),
                      "hist_protest_count": g.size(),
                      "hist_filers": g.who.agg(join_unique),
                      "hist_ptp_years": hist[hist.AUTH_TAX_REP_ID.eq(OUR)].groupby("ACCOUNT_NUM").PROTEST_YR.agg(join_unique)})
    for yr in ["2025", "2024"]:
        y = hist[hist.PROTEST_YR.eq(yr)].drop_duplicates("ACCOUNT_NUM", keep="last").set_index("ACCOUNT_NUM")
        h[f"hist_{yr}_filer"] = y.who
        h[f"hist_{yr}_notice_val"] = y.NOTIFIED_VAL
        h[f"hist_{yr}_final_val"] = y.PANEL_VAL.where(num(y.PANEL_VAL) > 0, y.NEW_VAL)

    # ---- roll source per account
    src = {}
    for name, d in ROLLS:
        ids = set(read_for(d / "ACCOUNT_APPRL_YEAR.CSV", accts, usecols=["ACCOUNT_NUM"]).ACCOUNT_NUM)
        for x in ids - set(src):
            src[x] = name
    by_src = {name: {x for x, s in src.items() if s == name} for name, _ in ROLLS}
    print("roll source:", {k: len(s) for k, s in by_src.items()}, "| none:", len(accts - set(src)))

    def roll(table, **kw):
        return pd.concat([read_for(d / table, by_src[name], **kw) for name, d in ROLLS if by_src[name]])

    info = roll("ACCOUNT_INFO.CSV").drop_duplicates("ACCOUNT_NUM").set_index("ACCOUNT_NUM").add_prefix("info_")
    appr = roll("ACCOUNT_APPRL_YEAR.CSV").drop_duplicates("ACCOUNT_NUM").set_index("ACCOUNT_NUM").add_prefix("appr_")

    res = roll("RES_DETAIL.CSV").sort_values(["ACCOUNT_NUM", "TAX_OBJ_ID"])
    res_n = res.groupby("ACCOUNT_NUM").size().rename("res_bldg_count")
    res = res.drop_duplicates("ACCOUNT_NUM").set_index("ACCOUNT_NUM").drop(columns="APPRAISAL_YR").add_prefix("res_")

    addl = roll("RES_ADDL.CSV")
    ga = addl.groupby("ACCOUNT_NUM")
    addl = pd.DataFrame({"addl_count": ga.size(), "addl_items": ga.IMPR_TYP_DESC.agg(join_unique),
                         "addl_total_val": ga.VAL_AMT.apply(lambda s: num(s).sum())})

    com = roll("COM_DETAIL.CSV").sort_values(["ACCOUNT_NUM", "TAX_OBJ_ID"])
    gc = com.groupby("ACCOUNT_NUM")
    com_s = pd.DataFrame({"com_bldg_count": gc.size(), "com_total_gross_area": gc.GROSS_BLDG_AREA.apply(lambda s: num(s).sum())})
    com = com.drop_duplicates("ACCOUNT_NUM").set_index("ACCOUNT_NUM").drop(columns="APPRAISAL_YR").add_prefix("com_")

    land = roll("LAND.CSV").sort_values(["ACCOUNT_NUM", "SECTION_NUM"])
    gl = land.groupby("ACCOUNT_NUM")
    land = pd.DataFrame({"land_sections": gl.size(),
                         "land_sptd": gl.SPTD_DESC.agg(join_unique), "land_zoning": gl.ZONING.agg(join_unique),
                         "land_front_dim": gl.FRONT_DIM.first(), "land_depth_dim": gl.DEPTH_DIM.first(),
                         "land_area_total": gl.AREA_SIZE.apply(lambda s: num(s).sum()),
                         "land_area_uom": gl.AREA_UOM_DESC.agg(join_unique),
                         "land_pricing_meth": gl.PRICING_METH_DESC.agg(join_unique),
                         "land_cost_per_uom": gl.COST_PER_UOM.first(), "land_market_adj_pct": gl.MARKET_ADJ_PCT.first(),
                         "land_val_total": gl.VAL_AMT.apply(lambda s: num(s).sum()),
                         "land_ag_use": gl.AG_USE_IND.agg(join_unique)})

    std = roll("APPLIED_STD_EXEMPT.CSV").sort_values(["ACCOUNT_NUM", "OWNER_SEQ_NUM"])
    std = std.drop_duplicates("ACCOUNT_NUM").set_index("ACCOUNT_NUM")[
        ["EXEMPT_STATUS_CD", "OWNERSHIP_PCT", "APPLICANT_NAME", "HOMESTEAD_EFF_DT", "OVER65_DESC", "DISABLED_DESC",
         "TAX_DEFERRED_DESC", "DISABLE_EFF_DT", "VET_EFF_YR", "VET_DISABLE_PCT", "CAPPED_HS_AMT", "HS_PCT", "TOT_VAL",
         "OVER65_PCT", "DISABLEDPCT", "CIRCUIT_BK_FLG"]].add_prefix("exm_std_")
    ev = roll("ACCT_EXEMPT_VALUE.CSV")
    ge = ev.groupby("ACCOUNT_NUM")
    ev = pd.DataFrame({"exm_list": ge.EXEMPTION.agg(join_unique),
                       "exm_city_applied": ge.CITY_APPLD_VAL.apply(lambda s: num(s).sum()),
                       "exm_county_applied": ge.CNTY_APPLD_VAL.apply(lambda s: num(s).sum()),
                       "exm_isd_applied": ge.ISD_APPLD_VAL.apply(lambda s: num(s).sum())})
    tot = roll("TOTAL_EXEMPTION.CSV").groupby("ACCOUNT_NUM").TE_REASON.agg(join_unique).rename("exm_total_reason")
    abt = roll("ABATEMENT_EXEMPT.CSV").drop_duplicates("ACCOUNT_NUM").set_index("ACCOUNT_NUM")
    abt = (num(abt.CITY_EXEMPTION_AMT).fillna(0) + num(abt.CNTY_EXEMPTION_AMT).fillna(0)
           + num(abt.ISD_EXEMPTION_AMT).fillna(0)).rename("exm_abatement_amt")
    fp = roll("FREEPORT_EXEMPTION.CSV").drop_duplicates("ACCOUNT_NUM").set_index("ACCOUNT_NUM")
    fp = pd.Series("Y", index=fp.index, name="exm_freeport")
    mo = roll("MULTI_OWNER.CSV").sort_values(["ACCOUNT_NUM", "OWNER_SEQ_NUM"])
    mo["o"] = mo.OWNER_NAME + " (" + mo.OWNERSHIP_PCT + "%)"
    mo = mo.groupby("ACCOUNT_NUM").o.agg(join_unique).rename("owners_all")
    tif = roll("ACCOUNT_TIF.CSV").groupby("ACCOUNT_NUM").TIF_ZONE_DESC.agg(join_unique).rename("tif_zone")

    out = v.set_index("account", drop=False)
    out["roll_source"] = out.index.map(src)
    for part in [a, h, info, appr, res, res_n, addl, com, com_s, land, std, ev, tot, abt, fp, mo, tif]:
        out = out.join(part)
    out = out.reset_index(drop=True)
    out = out.dropna(axis=1, how="all")
    out = out.loc[:, ~(out.astype(str).isin(["", "nan"]).all())]   # drop columns empty for all our accounts

    dest = SC / "dallas_ptp_accounts_2026.csv"
    out.to_csv(dest, index=False)
    print(f"{dest.name}: {len(out):,} rows x {out.shape[1]} columns")


if __name__ == "__main__":
    main()
