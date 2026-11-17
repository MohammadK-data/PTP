"""Harris CAD -> active accounts with address, state code, notice value and latest market value.
  roll   : Real_acct_owner/real_acct.txt (2026 real property, file dated 2026-11-08). state_class is the PTD code
           (A1 single family, B multifamily, C1 res vacant, C2 commercial vacant, F1 commercial, F2 industrial,
           X exempt, Z0-Z5 condos/townhomes). Market value = tot_mkt_val. Business personal property not included.
  notice : Hearing_files/arb_hearings_real.txt Initial_Market_Value (latest hearing row per account);
           protested = account in arb_protest_real.txt; not protested -> current roll value.
Run: /Users/user2/PTP/.venv/bin/python -I "Market Analysis/etl/active_accounts_2026/harris.py"
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CAD, fill_notice, main, norm_acct, num  # noqa: E402

D = CAD / "Harris" / "Data"
FILE = D / "Real_acct_owner" / "real_acct.txt"
HEAR = D / "Hearing_files" / "arb_hearings_real.txt"
PROT = D / "Hearing_files" / "arb_protest_real.txt"
SOURCE = "HCAD Real_acct_owner/real_acct.txt (2026 roll, file dated 2026-11-08) + hearing files 2026-11-08"
DATE = "2026-11-08"
COLS = ["acct", "yr", "state_class", "site_addr_1", "site_addr_2", "site_addr_3", "Neighborhood_Code", "land_val",
        "bld_val", "tot_appr_val", "tot_mkt_val", "value_status", "certified_date"]
LETTER = {"TN": "Hearing held (notice of order)", "WD": "Withdrawn"}


def tsv(path, cols=None):
    return pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False, usecols=cols, encoding="latin-1",
                       quoting=3).apply(lambda c: c.str.strip())


def load_roll():
    d = tsv(FILE, COLS)
    d = d[d.yr.eq("2026")]
    r = pd.DataFrame({
        "key": d.acct.map(norm_acct), "cad_account": d.acct, "situs_address": d.site_addr_1,
        "situs_city": d.site_addr_2, "situs_zip": d.site_addr_3.str[:5], "state_code": d.state_class.str.upper(),
        "market_value": num(d.tot_mkt_val).values, "appraised_value": num(d.tot_appr_val).values,
        "land_value": num(d.land_val).values, "building_value": num(d.bld_val).values,
        "neighborhood": d.Neighborhood_Code, "value_status": d.value_status, "certified_date": d.certified_date,
    })
    h = tsv(HEAR)
    h = h[h.Tax_Year.eq("2026")].copy()
    h["rel"] = pd.to_datetime(h.Release_Date, format="%m/%d/%Y", errors="coerce")
    h = h.sort_values("rel", na_position="first").drop_duplicates("acct", keep="last")
    h["key"] = h.acct.map(norm_acct)
    h = h.set_index("key")
    protested = set(tsv(PROT, ["acct"]).acct.map(norm_acct)) | set(h.index)
    r["protested"] = r.key.isin(protested).map({True: "Y", False: "N"})
    r["notice_value"] = r.key.map(num(h.Initial_Market_Value).set_axis(h.index))
    r["notice_source"] = r.notice_value.notna().map({True: "ARB hearing file: initial market value", False: ""})
    r["protest_final_value"] = r.key.map(num(h.Final_Market_Value).set_axis(h.index))
    r["protest_outcome"] = r.key.map(h.Letter_Type.map(lambda x: LETTER.get(x, x))).fillna("")
    r["hearing_type"] = r.key.map(h.Hearing_Type).fillna("")
    r = fill_notice(r, dict(zip(r.key, r.market_value)), "not protested: current roll value")
    return r


if __name__ == "__main__":
    main("Harris", load_roll, SOURCE, DATE)
