"""Readers for PACS (True Automation / Harris Govern) appraisal exports, used by Bexar, Denton, Travis,
Montgomery and Rockwall. APPRAISAL_INFO comes either as the raw fixed-width TXT or as a CSV(.gz) already
converted in CAD Website/<County>/output. Field positions: CAD Website/Denton/etl/pacs_appraisal_export_layout.json."""
import json

import pandas as pd

from common import CAD, join_addr, norm_acct, num

LAYOUT = json.load(open(CAD / "Denton" / "etl" / "pacs_appraisal_export_layout.json"))
INFO_COLS = ["prop_id", "prop_type_cd", "prop_val_yr", "sup_num", "geo_id", "hs_exempt", "imprv_state_cd",
             "land_state_cd", "personal_state_cd", "mineral_state_cd", "appraised_val", "market_value", "situs_num", "situs_street_prefx",
             "situs_street", "situs_street_suffix", "situs_unit", "situs_city", "situs_zip"]


def fixed(path, rec, cols):
    pos = {f[0]: (f[1] - 1, f[2]) for f in LAYOUT[rec] if f[0] in cols}
    cols = [c for c in cols if c in pos]
    with open(path, encoding="latin-1") as f:
        rows = [[ln[pos[c][0]:pos[c][1]].strip() for c in cols] for ln in f]
    return pd.DataFrame(rows, columns=cols)


def read_info(path):
    path = str(path)
    if path.upper().endswith(".TXT"):
        d = fixed(path, "APPRAISAL_INFO", INFO_COLS)
    else:
        d = pd.read_csv(path, dtype=str, keep_default_na=False, usecols=lambda c: c in INFO_COLS)
    for c in INFO_COLS:
        if c not in d:
            d[c] = ""
        d[c] = d[c].astype(str).str.strip()
    return d


def read_state_codes(path):
    """-> dict local state code -> (ptd_state_cd, description)."""
    path = str(path)
    cols = ["state_cd", "state_cd_description", "ptd_state_cd", "ptd_state_cd_description"]
    if path.upper().endswith(".TXT"):
        s = fixed(path, "APPRAISAL_STATE_CODE", cols)
    else:
        s = pd.read_csv(path, dtype=str, keep_default_na=False, usecols=lambda c: c in cols)
    s = s.apply(lambda c: c.str.strip())
    return {r.state_cd.upper(): (r.ptd_state_cd.upper(), r.state_cd_description) for r in s.itertuples()}


def roll(info_path, state_code_path, year="2026"):
    d = read_info(info_path)
    d = d[d.prop_val_yr.str.lstrip("0").eq(year) | d.prop_val_yr.eq("")]
    d["sup"] = pd.to_numeric(d.sup_num, errors="coerce")
    # several rows per prop_id (supplements, undivided owners): homestead if any row has it, keep latest supplement
    hs = d.groupby("prop_id").hs_exempt.apply(lambda s: "Y" if s.eq("T").any() else "N")
    d = d.sort_values(["prop_id", "sup"]).drop_duplicates("prop_id", keep="last").copy()
    d["homestead"] = d.prop_id.map(hs)
    sc = d.imprv_state_cd.where(d.imprv_state_cd.ne(""), d.land_state_cd)
    sc = sc.where(sc.ne(""), d.personal_state_cd).where(lambda x: x.ne(""), d.mineral_state_cd)
    d["state_code"] = sc.str.upper()
    codes = read_state_codes(state_code_path)
    d["ptd_state_code"] = d.state_code.map(lambda c: codes.get(c, (c, ""))[0] or c)
    d["state_code_desc"] = d.state_code.map(lambda c: codes.get(c, ("", ""))[1])
    return pd.DataFrame({
        "key": d.prop_id, "cad_account": d.prop_id.str.lstrip("0"), "geo_id": d.geo_id,
        "situs_address": join_addr(d.situs_num, d.situs_street_prefx, d.situs_street, d.situs_street_suffix,
                                   d.situs_unit).values,
        "situs_city": d.situs_city, "situs_zip": d.situs_zip.str[:5],
        "prop_type": d.prop_type_cd, "state_code": d.state_code, "ptd_state_code": d.ptd_state_code,
        "state_code_desc": d.state_code_desc, "imprv_state_cd": d.imprv_state_cd, "land_state_cd": d.land_state_cd,
        "market_value": num(d.market_value).values, "appraised_value": num(d.appraised_val).values,
        "homestead": d.homestead, "sup_num": d.sup.values,
    })


def market_by_id(info_path, year="2026"):
    """{normalized prop_id: market_value} from an export (used for the notice-run / preliminary export)."""
    d = read_info(info_path)
    d = d[d.prop_val_yr.str.lstrip("0").eq(year) | d.prop_val_yr.eq("")]
    d["sup"] = pd.to_numeric(d.sup_num, errors="coerce")
    d = d.sort_values(["prop_id", "sup"]).drop_duplicates("prop_id", keep="last")
    return dict(zip(d.prop_id.map(norm_acct), num(d.market_value).values))
