"""Dallas CAD -> active accounts with address, state code, notice value and latest market value.
  values / state code : DCAD2026_CURRENT ACCOUNT_APPRL_YEAR (2026-10-30); accounts missing there (new or split)
                        from DCAD2027_CURRENT, then retired accounts from DCAD2025_CURRENT. value_year says which.
  address             : ACCOUNT_INFO of the same files
  notice value        : protested -> CAD Website/Dallas/output/dallas_values_2026.csv (ARB files);
                        not protested -> certified roll DCAD2026_CERTIFIED_07232026 (= noticed value)
DCAD's own group is DIVISION_CD (RES / COM / BPP). SPTD codes: A11 single family, B11 apartments, B12 duplex,
C11 residential vacant, C12/C13 commercial vacant, F10 commercial, F20 industrial, L10 BPP (see SPTD_CD_XREF.pdf).
Run: /Users/user2/PTP/.venv/bin/python -I "Market Analysis/etl/active_accounts_2026/dallas.py"
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CAD, add_values_file, fill_notice, join_addr, main, norm_acct, num  # noqa: E402

D = CAD / "Dallas" / "Data"
FILES = [("2026", D / "DCAD2026_CURRENT"), ("2027", D / "DCAD2027_CURRENT"),
         ("2025", D / "dcad_download_20261114" / "DCAD2025_CURRENT")]
CERT = D / "DCAD2026_CERTIFIED_07232026" / "ACCOUNT_APPRL_YEAR.CSV"
VALUES = CAD / "Dallas" / "output" / "dallas_values_2026.csv"
VALUES_MAP = {"notice_value": "notice_value", "final_value": "protest_final_value", "protested": "protested",
              "outcome": "protest_outcome", "situs": "situs_address", "city": "situs_city", "zip": "situs_zip"}
SOURCE = "DCAD2026_CURRENT (2026-10-30); missing accounts from DCAD2027_CURRENT, then DCAD2025_CURRENT"
DATE = "2026-10-30"
COLS = ["ACCOUNT_NUM", "APPRAISAL_YR", "IMPR_VAL", "LAND_VAL", "TOT_VAL", "DIVISION_CD", "BLDG_CLASS_CD", "SPTD_CODE"]
ACOLS = ["ACCOUNT_NUM", "APPRAISAL_YR", "STREET_NUM", "STREET_HALF_NUM", "FULL_STREET_NAME", "UNIT_ID",
         "PROPERTY_CITY", "PROPERTY_ZIPCODE"]


def read(path, cols, yr):
    x = pd.read_csv(path, dtype=str, keep_default_na=False, usecols=cols).apply(lambda c: c.str.strip())
    return x[x.APPRAISAL_YR.eq(yr)].drop(columns="APPRAISAL_YR")


def load_roll():
    parts = []
    for yr, folder in FILES:
        v = read(folder / "ACCOUNT_APPRL_YEAR.CSV", COLS, yr)
        if (folder / "ACCOUNT_INFO.CSV").exists():      # the 2025 download has no ACCOUNT_INFO (no address)
            a = read(folder / "ACCOUNT_INFO.CSV", ACOLS, yr).drop_duplicates("ACCOUNT_NUM")
            v = v.merge(a, on="ACCOUNT_NUM", how="left")
        parts.append(v.assign(value_year=yr))
    d = pd.concat(parts[::-1]).fillna("")          # common.run keeps the LAST row per account: preferred year last
    r = pd.DataFrame({
        "key": d.ACCOUNT_NUM, "cad_account": d.ACCOUNT_NUM,
        "situs_address": join_addr(d.STREET_NUM, d.STREET_HALF_NUM, d.FULL_STREET_NAME, d.UNIT_ID).values,
        "situs_city": d.PROPERTY_CITY, "situs_zip": d.PROPERTY_ZIPCODE.str[:5],
        "state_code": d.SPTD_CODE.str.upper(), "value_year": d.value_year, "division": d.DIVISION_CD,
        "bldg_class": d.BLDG_CLASS_CD, "market_value": num(d.TOT_VAL).values, "land_value": num(d.LAND_VAL).values,
        "improvement_value": num(d.IMPR_VAL).values,
    })
    r = r.assign(key=r.key.map(norm_acct)).drop_duplicates("key", keep="last")
    r = add_values_file(r, VALUES, "account", VALUES_MAP, "ARB files")
    cert = read(CERT, ["ACCOUNT_NUM", "APPRAISAL_YR", "TOT_VAL"], "2026")
    r = fill_notice(r, dict(zip(cert.ACCOUNT_NUM.map(norm_acct), num(cert.TOT_VAL).values)),
                    "not protested: certified roll 2026-07-23")
    return r


if __name__ == "__main__":
    main("Dallas", load_roll, SOURCE, DATE)
