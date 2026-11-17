"""Tarrant AD -> active accounts with address, state code, notice value and latest market value.
  roll  : PropertyData(Delimited)_2026.txt (all classes, 2026-10-26) updated with the newer residential file
          PropertyData(Delimited)_R_2026.txt (2026-11-11). State_Use_Code is the PTD code; Property_Class is TAD's
          class (C1C/C2C = commercial vacant land). Market value = Total_Value.
  notice: CAD Website/Tarrant/output/tarrant_values_2026.csv (earlier protest build); not protested -> Oct roll value
  TAD publishes no situs city or zip, only Situs_Address (situs_zip is blank).
Run: /Users/user2/PTP/.venv/bin/python -I "Market Analysis/etl/active_accounts_2026/tarrant.py"
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CAD, add_values_file, fill_notice, main, norm_acct, num  # noqa: E402

D = CAD / "Tarrant" / "Data"
FILES = [D / "PropertyData(Delimited)_2026.txt", D / "PropertyData(Delimited)_R_2026.txt"]   # later file wins
VALUES = CAD / "Tarrant" / "output" / "tarrant_values_2026.csv"
VALUES_MAP = {"notice_value": "notice_value", "final_value": "protest_final_value", "protested": "protested",
              "outcome": "protest_outcome"}
SOURCE = "TAD PropertyData(Delimited)_2026.txt (2026-10-26) + PropertyData(Delimited)_R_2026.txt (2026-11-11)"
DATE = "2026-11-11"
COLS = ["Appraisal_Year", "Account_Num", "Property_Class", "State_Use_Code", "Situs_Address", "Land_Value",
        "Improvement_Value", "Total_Value", "Appraised_Value", "Notice_Date"]


def load_roll():
    parts = []
    for i, f in enumerate(FILES):
        d = pd.read_csv(f, sep="|", dtype=str, keep_default_na=False, usecols=COLS, encoding="latin-1", quoting=3)
        parts.append(d.assign(file_order=i))
    d = pd.concat(parts)
    d = d[d.Appraisal_Year.str.strip().eq("2026")].sort_values("file_order", kind="stable")
    d[COLS] = d[COLS].apply(lambda c: c.str.strip())
    sc = d.State_Use_Code.where(d.State_Use_Code.ne(""), d.Property_Class).str.upper()
    r = pd.DataFrame({
        "key": d.Account_Num.map(norm_acct), "cad_account": d.Account_Num, "situs_address": d.Situs_Address,
        "state_code": sc, "tad_property_class": d.Property_Class, "market_value": num(d.Total_Value).values,
        "appraised_value": num(d.Appraised_Value).values, "land_value": num(d.Land_Value).values,
        "improvement_value": num(d.Improvement_Value).values, "notice_date": d.Notice_Date.str[:10],
    }).drop_duplicates("key", keep="last")
    r = add_values_file(r, VALUES, "Account_Num", VALUES_MAP, "protest build")
    oct_roll = d[d.file_order.eq(0)].drop_duplicates("Account_Num", keep="last")
    r = fill_notice(r, dict(zip(oct_roll.Account_Num.map(norm_acct), num(oct_roll.Total_Value).values)),
                    "not protested: roll value 2026-10-26")
    return r


if __name__ == "__main__":
    main("Tarrant", load_roll, SOURCE, DATE)
