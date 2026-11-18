"""2026 Property Tax Protest accounts per county: a full detail file and a simple results file, the same pair
Dallas and Tarrant have (dallas_ptp_accounts_2026_build.py / tarrant_ptp_accounts_2026_build.py).

Base: Scorecard Data/<County>/<county>_values_2026.csv rows with is_ours = True.

Outputs (Scorecard Data/<County>)
    <county>_ptp_accounts_2026.csv   everything per account:
        (no prefix)  scorecard fields: path, notice / final value, reduction, outcome, fee estimate ...
        value_2025_roll   2025 market value (where a 2025 source exists, see below)
        appeal_* / arb_*  extra fields of our deciding 2026 protest
        case_*       every 2026 protest / ARB record on the account (all filers)
        roll_*       2026 PACS appraisal export, APPRAISAL_INFO (first owner row of the latest supplement;
                     columns that are blank / zero / F for all our accounts are dropped)
        owners_all, roll_market_total (market value summed over owner rows)
        impr_*       APPRAISAL_IMPROVEMENT_INFO summary;  land_* APPRAISAL_LAND_DETAIL summary
        hist_*       earlier seasons (where a history source exists)
    <county>_ptp_results_2026.csv    simple: what happened, property type, values, dates (Dallas / Tarrant layout)

Sources per county
    bexar       export 2026-10-15 (output/*.csv.gz); BCAD agent export Oct 26 (FID_ARBExport -> arb_ / case_,
                FID_ApprNoticeExport An_prev_market_val -> 2025 value); bexar_seasons 2024-2025 -> hist_
    rockwall    export 2026-10-09 (output/*.csv.gz); APPRAISAL_ARB in the May 26 / Jul 13 / Oct 9 exports -> case_;
                2025 certified export (Data/rockwall_prior_download/rc_2025_cert) -> 2025 value, hist_2025_*
    denton      export 2026-10-14 (output/*.csv); denton_appeals_2026 -> appeal_ / case_; denton_history 2023-2024
                No 2025 roll or 2025 protest file in the download, so value_2025_roll / hist_2025 stay blank.
    montgomery  certified export 2026-08-04 (Data/Certified Appraisal Roll 2026/*.TXT); montgomery_appeals_2026;
                2025 certified export zip -> 2025 value; montgomery_history 2024 (filer / value only, no result)
    travis      export Oct 6 SUPP 335 (output/2026-10-06_2026_APPRAISAL_INFO.csv.gz + Data/... IMP_INFO / LAND_DET
                / AGENT .TXT); travis_appeals_2026. No 2025 roll or protest history on disk.

Run:  .venv/bin/python -I "CAD Website/_scorecard_template/county_ptp_accounts_2026.py" bexar rockwall denton montgomery travis
"""
import io
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LAYOUT = json.loads((ROOT / "Denton/etl/pacs_appraisal_export_layout.json").read_text())

RESULT = {"ARB": "1. ARB Hearing", "Informal": "2. Informal Settlement", "Withdrawn": "3. Withdrawn",
          "Dismissed": "4. Dismissed / No-Show", "No-show": "4. Dismissed / No-Show", "Open": "5. Open - No Result Yet",
          "Other": "6. Other (no jurisdiction / motion)"}
PTYPE = {"R": "Real Property", "Real": "Real Property", "MH": "Mobile Home", "P": "Business Personal Property",
         "MN": "Mineral", "A": "Auto"}
# Texas PTD property categories (first letter, or two characters where the category splits)
PCLASS = {"A": "Single-Family Residential", "B": "Multifamily Residential", "C": "Vacant Lot / Land",
          "D": "Qualified Ag / Open-Space Land", "E": "Rural Land (non-ag) with Home", "F1": "Commercial Real Property",
          "F2": "Industrial Real Property", "F": "Commercial / Industrial Real Property", "J": "Utility",
          "L1": "Commercial Business Personal Property", "L2": "Industrial Business Personal Property",
          "M": "Mobile Home", "O": "Residential Inventory", "X": "Exempt"}
EMPTY = {"", "nan", "<NA>", "None", "NaN"}


# ---------------------------------------------------------------- helpers
def num(s):
    return pd.to_numeric(s, errors="coerce")


def pid(s):
    return s.astype(str).str.strip().str.lstrip("0")


def day(s):
    d = pd.to_datetime(s.replace("", np.nan), errors="coerce", format="mixed")
    out = d.dt.strftime("%Y-%m-%d").fillna("")
    return out.where(~out.str.startswith("1900"), "")


def money(x):
    return "" if pd.isna(x) else f"${x:,.0f}"


def join_unique(s):
    return " | ".join(x for x in dict.fromkeys(s) if x and x not in EMPTY)


def tidy(df):
    """Strip, and turn zero-padded numbers ("000000123", "0000012.5000") into plain numbers."""
    df = df.apply(lambda s: s.astype(str).str.strip())
    for c in df.columns:
        s = df[c][~df[c].isin(EMPTY)]
        if len(s) and s.str.fullmatch(r"-?\d+(\.\d+)?").all() and s.str.match(r"-?0\d").any():
            df[c] = df[c].where(df[c].isin(EMPTY), num(df[c]).map(lambda x: f"{x:.10g}"))
    return df


def lines(src):
    """Byte lines of a fixed-width TXT file, or of a member inside a zip (src = (zip, member))."""
    if isinstance(src, tuple):
        p = subprocess.Popen(["unzip", "-p", str(src[0]), src[1]], stdout=subprocess.PIPE)
        yield from p.stdout
        p.wait()
    else:
        with open(src, "rb") as f:
            yield from f


def pacs(src, record, ids):
    """Rows of one PACS export record for the given prop_ids, from a parsed .csv(.gz) or a raw fixed-width TXT."""
    if str(src[0] if isinstance(src, tuple) else src).endswith((".csv", ".csv.gz")):
        parts = [ch[pid(ch.prop_id).isin(ids)] for ch in
                 pd.read_csv(src, dtype=str, keep_default_na=False, chunksize=200_000, encoding="latin-1")]
        df = pd.concat(parts)
    else:
        spec = [(n, a - 1, b) for n, a, b in LAYOUT[record]]
        bids = {i.encode() for i in ids}
        rows = []
        for ln in lines(src):
            if ln[:12].lstrip(b"0") in bids:
                s = ln.decode("latin-1")
                rows.append({n: s[a:b] for n, a, b in spec})
        df = pd.DataFrame(rows, columns=[n for n, _, _ in spec])
    df = tidy(df.drop(columns=[c for c in df.columns if c.startswith("filler")]))
    df["prop_id"] = pid(df.prop_id)
    if "prop_val_yr" in df:
        df["prop_val_yr"] = pid(df.prop_val_yr)
    return df


def agent_names(src):
    if str(src).endswith((".csv", ".csv.gz")):
        a = pd.read_csv(src, dtype=str, keep_default_na=False, encoding="latin-1", usecols=["agent_id", "agent_name"])
        return dict(zip(pid(a.agent_id), a.agent_name.str.strip()))
    return {ln[:12].decode().strip().lstrip("0"): ln[12:82].decode("latin-1").strip() for ln in lines(src)}


def roll_parts(cfg, ids):
    """roll_* (APPRAISAL_INFO), impr_*, land_* for our accounts."""
    info = pacs(cfg["info"], "APPRAISAL_INFO", ids)
    info = info[info.prop_val_yr.eq("2026")].copy()
    info["_sup"], info["_mv"] = num(info.sup_num), num(info.market_value)
    info = info[info._sup.eq(info.groupby("prop_id")._sup.transform("max"))]
    # one row per owner; a property listed twice for the same owner (e.g. two geo_ids) counts once
    info = info.sort_values(["prop_id", "py_owner_id", "_mv"]).drop_duplicates(["prop_id", "py_owner_id"], keep="last")
    g = info.groupby("prop_id")
    extra = pd.DataFrame({"roll_owner_rows": g.size(), "roll_market_total": g._mv.sum(min_count=1),
                          "owners_all": g.py_owner_name.agg(join_unique)})
    first = info.drop_duplicates("prop_id").set_index("prop_id").drop(columns=["_sup", "_mv"])
    keep = [c for c in first.columns if not first[c].isin(EMPTY | {"0", "F", "N"}).all() and "unmapped" not in c]
    roll = first[keep].add_prefix("roll_").join(extra)

    im = pacs(cfg["impr"], "APPRAISAL_IMPROVEMENT_INFO", ids)
    im = im[im.prop_val_yr.eq("2026")] if "prop_val_yr" in im else im
    gi = im.groupby("prop_id")
    impr = pd.DataFrame({"impr_count": gi.size(), "impr_types": gi.imprv_type_desc.agg(join_unique),
                         "impr_state_cds": gi.imprv_state_cd.agg(join_unique),
                         "impr_val_total": gi.imprv_val.apply(lambda s: num(s).sum())})

    ld = pacs(cfg["land"], "APPRAISAL_LAND_DETAIL", ids)
    ld = ld[ld.prop_val_yr.eq("2026")] if "prop_val_yr" in ld else ld
    gl = ld.groupby("prop_id")
    land = pd.DataFrame({"land_segments": gl.size(), "land_types": gl.land_type_desc.agg(join_unique),
                         "land_state_cds": gl.state_cd.agg(join_unique),
                         "land_acres_total": gl.size_acres.apply(lambda s: num(s).sum()),
                         "land_sqft_total": gl.size_square_feet.apply(lambda s: num(s).sum()),
                         "land_eff_front": gl.effective_front.first(), "land_eff_depth": gl.effective_depth.first(),
                         "land_mkt_method": gl.mkt_ls_method.agg(join_unique),
                         "land_mkt_val_total": gl.land_seg_mkt_val.apply(lambda s: num(s).sum()),
                         "land_ag_apply": gl.ag_apply.agg(join_unique),
                         "land_ag_val_total": gl.ag_value.apply(lambda s: num(s).sum())})
    print(f"  roll rows {len(roll):,} | improvements on {len(impr):,} | land on {len(land):,}")
    return [roll, impr, land]


def protax_cases(appeals_csv, v, names):
    """case_* from every 2026 appeal on the account, appeal_* = extra fields of our deciding appeal."""
    a = pd.read_csv(appeals_csv, dtype=str, keep_default_na=False)
    a = a[a.pID.isin(set(v.pID))].apply(lambda s: s.str.strip())
    a["agent"] = a.appealedByAgentID.str.replace(r"\.0$", "", regex=True)
    a["who"] = np.where(a.agent.ne(""), a.agent.map(names).fillna("agent") + " (" + a.agent + ")",
                        a.appealedByType.map({"O": "Owner", "A": "Agent", "C": "Appraisal district"})
                        .fillna(a.appealedByType))
    a["case"] = a.appealID + " " + a.appealType + " " + a.appealStatus
    g = a.sort_values(["pID", "appealID"]).groupby("pID")
    cases = pd.DataFrame({"case_count": g.size(), "case_all": g.case.agg(join_unique),
                          "case_filers_all": g.who.agg(join_unique)})
    have = set(v.columns)
    ours = a[a.appealID.isin(set(v.appealID))].drop_duplicates("appealID").set_index("pID")
    ours = ours[[c for c in ours.columns if c not in have and c not in {"who", "case", "agent"}]].add_prefix("appeal_")
    return [cases, ours]


def history(path, ids, years):
    h = pd.read_csv(path, dtype=str, keep_default_na=False)
    h = h[h.pid.isin(ids) & h.year.isin(years)]
    out = pd.DataFrame(index=sorted(ids))
    for yr in years:
        y = h[h.year.eq(yr)].drop_duplicates("pid").set_index("pid").reindex(out.index)
        out[f"hist_{yr}_filer"] = np.where(y.who.eq("agent"), y.firm, y.who)
        for c in ["path", "notice", "final", "reduction"]:
            out[f"hist_{yr}_{c}"] = y[c]
    return out.replace("", np.nan)


# ---------------------------------------------------------------- counties
def bexar(v, ids):
    out, ex = ROOT / "Bexar/output", ROOT / "Bexar/Data/2026 Agent Export as of 2026-10-26 CSV"
    cfg = {k: out / f"2026-10-15_2026_APPRAISAL_{t}.csv.gz" for k, t in
           [("info", "INFO"), ("impr", "IMPROVEMENT_INFO"), ("land", "LAND_DETAIL")]}
    parts = roll_parts(cfg, ids)

    arb = pd.read_csv(ex / "FID_ARBExport.csv", dtype=str, keep_default_na=False, encoding="latin-1")
    arb = arb[arb["Property ID"].isin(ids) & arb.Year.eq("2026")].apply(lambda s: s.str.strip())
    arb["who"] = np.where(arb["Agent Name"].ne(""), arb["Agent Name"], arb["Protest By Type"])
    arb["case"] = arb["Case ID"] + " " + arb["Protest Type"] + " " + arb["Protest Status"]
    arb["_cid"] = num(arb["Case ID"])
    g = arb.sort_values(["Property ID", "_cid"]).groupby("Property ID")
    cases = pd.DataFrame({"case_count": g.size(), "case_all": g.case.agg(join_unique),
                          "case_filers_all": g.who.agg(join_unique)})
    ours = arb[arb["Agent Name"].eq("PROPERTY TAX PROTEST") & arb["Protest Type"].eq("25PROT")]
    ours = ours.sort_values("_cid").drop_duplicates("Property ID", keep="last").set_index("Property ID")
    ours = ours.drop(columns=["who", "case", "_cid", "Geo ID", "Year", "Owner Name", "Situs", "State Code",
                              "Property Type", "Exemptions"])
    ours.columns = ["arb_" + re.sub(r"\W+", "_", c).strip("_").lower() for c in ours.columns]

    an = pd.read_csv(ex / "FID_ApprNoticeExport.csv", dtype=str, keep_default_na=False)
    an = an[an.Prop_id.isin(ids) & an.Notice_yr.eq("2026")].assign(n=lambda d: num(d.Notice_num))
    prior = num(an.sort_values("n").drop_duplicates("Prop_id", keep="last").set_index("Prop_id").An_prev_market_val)

    s = pd.read_csv(out / "bexar_seasons.csv.gz", dtype=str, keep_default_na=False,
                    usecols=["prop_id", "year", "agent_name", "prot_by_type", "path", "bM", "fM", "ours"])
    s = s[s.prop_id.isin(ids) & s.year.isin(["2024", "2025"])]
    hist = pd.DataFrame(index=sorted(ids))
    for yr in ["2025", "2024"]:
        y = s[s.year.eq(yr)].drop_duplicates("prop_id").set_index("prop_id").reindex(hist.index)
        hist[f"hist_{yr}_filer"] = np.where(y.agent_name.fillna("").ne(""), y.agent_name, y.prot_by_type)
        hist[f"hist_{yr}_path"], hist[f"hist_{yr}_notice"], hist[f"hist_{yr}_final"] = y.path, y.bM, y.fM
        hist[f"hist_{yr}_reduction"] = num(y.bM) - num(y.fM)
    # the notice file covers only some accounts; else the closed 2025 protest's final value
    p25 = num(hist.hist_2025_final).where(hist.hist_2025_path.isin(["Informal", "ARB", "No-show", "Withdrawn", "Other"]))
    src = pd.Series(np.where(prior.reindex(hist.index).notna(), "2026 notice (prior-year value)",
                             np.where(p25.notna(), "2025 protest final", "")), index=hist.index)
    hist["value_2025_source"] = src
    prior = prior.reindex(hist.index).fillna(p25)
    return parts + [cases, ours, hist.replace("", np.nan)], prior


def rockwall(v, ids):
    out, pr = ROOT / "Rockwall/output", ROOT / "Rockwall/Data/rockwall_prior_download/rc_2025_cert"
    cfg = {k: out / f"2026-10-09_2026_APPRAISAL_{t}.csv.gz" for k, t in
           [("info", "INFO"), ("impr", "IMPROVEMENT_INFO"), ("land", "LAND_DETAIL")]}
    parts = roll_parts(cfg, ids)

    arb = []
    for stamp in ["2026-05-26", "2026-07-13", "2026-10-09"]:
        a = pacs(out / f"{stamp}_2026_APPRAISAL_ARB.csv.gz", "APPRAISAL_ARB", ids)
        arb.append(a[a.arb_status.ne("")].assign(case=stamp + ": " + a.arb_status))
    arb = pd.concat(arb)
    cases = pd.DataFrame({"case_arb_status_by_export": arb.groupby("prop_id").case.agg(join_unique)})

    i25 = pacs(pr / "2025-07-14_2025_APPRAISAL_INFO.TXT", "APPRAISAL_INFO", ids)
    i25["_sup"], i25["_mv"] = num(i25.sup_num), num(i25.market_value)
    i25 = i25[i25._sup.eq(i25.groupby("prop_id")._sup.transform("max"))]
    i25 = i25.sort_values(["prop_id", "py_owner_id", "_mv"]).drop_duplicates(["prop_id", "py_owner_id"], keep="last")
    prior = i25.groupby("prop_id")._mv.sum(min_count=1)
    names = agent_names(pr / "2025-07-14_2025_APPRAISAL_AGENT.TXT")
    a25 = i25.drop_duplicates("prop_id").set_index("prop_id").arb_agent_id
    p25 = set(pacs(pr / "2025-07-14_2025_APPRAISAL_ARB.TXT", "APPRAISAL_ARB", ids).prop_id)
    hist = pd.DataFrame(index=sorted(ids))
    hist["hist_2025_protested"] = np.where(hist.index.isin(p25), "Y", "")
    hist["hist_2025_arb_agent"] = a25.reindex(hist.index).map(
        lambda x: f"{names.get(x, 'agent')} ({x})" if isinstance(x, str) and x not in EMPTY | {"0"} else "")
    return parts + [cases, hist.replace("", np.nan)], prior


def denton(v, ids):
    out = ROOT / "Denton/output"
    cfg = {k: out / f"2026-10-14_2026_APPRAISAL_{t}.csv" for k, t in
           [("info", "INFO"), ("impr", "IMPROVEMENT_INFO"), ("land", "LAND_DETAIL")]}
    parts = roll_parts(cfg, ids)
    names = agent_names(out / "2026-10-14_2026_APPRAISAL_AGENT.csv")
    parts += protax_cases(out / "denton_appeals_2026.csv.gz", v, names)
    parts.append(history(out / "denton_history.csv", ids, ["2024", "2023"]))
    return parts, None


def montgomery(v, ids):
    d = ROOT / "Montgomery/Data/Certified Appraisal Roll 2026"
    cfg = {k: d / f"2026-08-04_2026_APPRAISAL_{t}.TXT" for k, t in
           [("info", "INFO"), ("impr", "IMPROVEMENT_INFO"), ("land", "LAND_DETAIL")]}
    parts = roll_parts(cfg, ids)
    names = agent_names(d / "2026-08-04_2026_APPRAISAL_AGENT.TXT")
    parts += protax_cases(ROOT / "Montgomery/output/montgomery_appeals_2026.csv.gz", v, names)
    h = history(ROOT / "Montgomery/output/montgomery_history.csv", ids, ["2024"])
    parts.append(h[["hist_2024_filer", "hist_2024_notice"]].rename(columns={"hist_2024_notice": "hist_2024_value"}))

    z = (ROOT / "Montgomery/Data/cert_2024_2025_download/MCAD_Certified_2025_071626.zip",
         "2026-07-16_2025_APPRAISAL_INFO.TXT")
    i25 = pacs(z, "APPRAISAL_INFO", ids)
    i25 = i25[i25.prop_val_yr.eq("2025")]
    i25["_sup"], i25["_mv"] = num(i25.sup_num), num(i25.market_value)
    i25 = i25[i25._sup.eq(i25.groupby("prop_id")._sup.transform("max"))]
    i25 = i25.sort_values(["prop_id", "py_owner_id", "_mv"]).drop_duplicates(["prop_id", "py_owner_id"], keep="last")
    return parts, i25.groupby("prop_id")._mv.sum(min_count=1)


def travis(v, ids):
    d = ROOT / "Travis/Data/travis_SUPP 335_2026_WEBSITE EXPORT_Renamed"
    cfg = {"info": ROOT / "Travis/output/2026-10-06_2026_APPRAISAL_INFO.csv.gz",
           "impr": d / "IMP_INFO.TXT", "land": d / "LAND_DET.TXT"}
    parts = roll_parts(cfg, ids)
    parts += protax_cases(ROOT / "Travis/output/travis_appeals_2026.csv.gz", v, agent_names(d / "AGENT.TXT"))
    return parts, None


COUNTIES = {"bexar": bexar, "rockwall": rockwall, "denton": denton, "montgomery": montgomery, "travis": travis}


# ---------------------------------------------------------------- build
def results(d):
    notice, final = num(d.notice_value), num(d.final_value)
    final = final.where(d.path.ne("Open"))                      # open: no final yet
    prior = num(d.value_2025_roll) if "value_2025_roll" in d else pd.Series(np.nan, index=d.index)
    cut = notice - final
    code = d.stateCd.str.strip()
    cls = code.str[:2].map(PCLASS).fillna(code.str[:1].map(PCLASS)).fillna("Other")
    what = np.select(
        [d.path.eq("Open"), d.path.eq("Withdrawn"), d.path.isin(["Dismissed", "No-show"]) & (cut <= 0),
         d.path.eq("Other") & (cut <= 0), cut > 0, cut < 0],
        ["Protest still open - no final value yet",
         "Protest withdrawn - value stayed at " + notice.map(money),
         "Dismissed / no-show - value stayed at " + notice.map(money),
         "No change (no jurisdiction / motion) - value stayed at " + notice.map(money),
         "Value cut from " + notice.map(money) + " to " + final.map(money) + " (-" + cut.map(money) + ")",
         "Value went UP from " + notice.map(money) + " to " + final.map(money)],
        default="No change - value stayed at " + notice.map(money))
    col = lambda *names: next((d[n] for n in names if n in d), pd.Series("", index=d.index))
    hearing = day(col("hearing_dt", "docketDt"))
    settled = day(col("resolved_dt", "finalizedDt"))
    # Bexar: board decision date, else hearing end, else the appraiser meeting (informal settlement)
    for c in ["consent_dt", "arb_1st_motion_decision_date", "arb_hearing_end_date_time",
              "arb_appraiser_meeting_date_time"]:
        settled = settled.where(settled.ne(""), day(col(c)))
    out = pd.DataFrame({
        "Account": d.pID,
        "Geo ID": col("geoID", "account").where(col("geoID", "account").ne(d.pID), ""),
        "Result": d.path.map(RESULT).fillna(d.path),
        "Value Change": d.outcome,
        "Property Type": d.propType.map(PTYPE).fillna(d.propType),
        "Property Class": np.where(code.ne(""), cls + " (" + code + ")", "Unknown"),
        "Owner": d.owner.str.strip(),
        "Situs": d.situs.str.strip(),
        "Filed By": np.where(d.appealedByType.isin(["O", "Owner"]), "Owner (we are agent)", "Us (agent)"),
        "2025 Final Value": prior.round(0),
        "2026 Notice Value": notice.round(0),
        "2026 Final Value": final.round(0),
        "Reduction $": cut.round(0),
        "Reduction %": (cut / notice * 100).round(1).where(notice > 0),
        "Change vs 2025 $": (final - prior).round(0),
        "Est. Fee (1% of reduction)": num(d.est_fee_1pct).where(d.path.ne("Open")).round(2),
        "Hearing Date": hearing,
        "Settled / Resolved Date": settled,
        "CAD Case Status": col("appealStatus", "status"),
        "Case Number": col("appealID", "arb_case_id"),
        "What Happened": what,
    })
    out = out.loc[:, ~out.astype(str).isin(EMPTY).all()]
    if out["2025 Final Value"].isna().all():
        out = out.drop(columns=["2025 Final Value", "Change vs 2025 $"])
    for c in ["2025 Final Value", "2026 Notice Value", "2026 Final Value", "Reduction $", "Change vs 2025 $"]:
        if c in out:
            out[c] = out[c].astype("Int64")
    return out.sort_values(["Result", "Property Type", "Account"],
                           key=lambda s: num(s) if s.name == "Account" else s).reset_index(drop=True)


def build(county):
    sc = ROOT / "Scorecard Data" / county.capitalize()
    v = pd.read_csv(sc / f"{county}_values_2026.csv", dtype=str, keep_default_na=False)
    v = v[v.is_ours.eq("True")].copy()
    v["pID"] = pid(v.pID)
    ids = set(v.pID)
    print(f"== {county}: our accounts {len(v):,} {v.path.value_counts().to_dict()}")

    parts, prior = COUNTIES[county](v, ids)
    full = v.set_index("pID", drop=False)
    if prior is not None:
        full["value_2025_roll"] = full.index.map(prior)
        print(f"  2025 value found for {full.value_2025_roll.notna().sum():,} of {len(full):,}")
    for part in parts:
        full = full.join(part)
    full = full.reset_index(drop=True)
    full = full.loc[:, ~full.astype(str).isin(EMPTY).all()]
    full.to_csv(sc / f"{county}_ptp_accounts_2026.csv", index=False)
    print(f"  {county}_ptp_accounts_2026.csv: {len(full):,} rows x {full.shape[1]} columns")

    out = results(full)
    out.to_csv(sc / f"{county}_ptp_results_2026.csv", index=False)
    print(f"  {county}_ptp_results_2026.csv: {len(out):,} rows x {out.shape[1]} columns")
    print(pd.crosstab(out.Result, out["Value Change"], margins=True).to_string())


def main():
    for c in sys.argv[1:] or list(COUNTIES):
        build(c.lower())


if __name__ == "__main__":
    main()
