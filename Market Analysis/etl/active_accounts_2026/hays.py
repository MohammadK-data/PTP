"""Hays CAD: 2026 property data export as of 2026-10-19 (PROPERTY / IMPROVEMENT / LAND zips).
Market value = CurrMarketValue (checked: matches the 2026 certified Orion export for 98% of accounts;
MarketValue is the prior value). State code = state code of the largest improvement, else of the largest land
segment (same rule as Market Analysis/etl/fort_bend_hays_market.py). Account = QuickRefID (R..., P..., M...). Address = Situs / SitusCity / SitusZip.
Notice value = CurrMarketValue in the 2026 PRELIMINARY export (2026-03-20), the values the notices were based on.
Run: /Users/user2/PTP/.venv/bin/python -I "Market Analysis/etl/active_accounts_2026/hays.py"
"""
import io
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CAD, fill_notice, join_addr, main, norm_acct, num  # noqa: E402

D = CAD / "Hays" / "Data" / "2026-PROPERTY-DATA-EXPORT-FILES-AS-OF-10-19-2026"
PRELIM = CAD / "Hays" / "Data" / "2026 PRELIMINARY DATA EXPORT FILES" / "2026-PRELIM-PROPERTY.zip"
SOURCE = "Hays CAD 2026 property data export files as of 2026-10-19"
DATE = "2026-10-19"


def zread(key, cols, path=None):
    z = zipfile.ZipFile(path or next(D.glob(f"*-FILE-{key}-*.zip")))
    with z.open(z.infolist()[0]) as fh:
        return pd.read_csv(io.TextIOWrapper(fh, encoding="utf-8-sig", errors="replace"), dtype=str,
                           keep_default_na=False, usecols=cols)


def top_code(df, val):
    df = df[df.StateCode.str.strip().ne("")].copy()
    df["v"] = num(df[val]).fillna(0).values
    return df.sort_values("v").drop_duplicates("PropertyID", keep="last").set_index("PropertyID").StateCode.str.strip()


def load_roll():
    p = zread("PROPERTY", ["PropertyID", "QuickRefID", "CurrMarketValue", "CurrAssessedValue", "CurrLandValue",
                           "CurrImprovmentValue", "NbhdCode", "SitusStreetNumber", "SitusPreDirectional",
                           "SitusStreetName", "SitusStreetSuffix", "SitusPostDirectional", "SitusCity",
                           "SitusZip"]).drop_duplicates("PropertyID")
    isc = top_code(zread("IMPROVEMENT", ["PropertyID", "StateCode", "ImpValue"]), "ImpValue")
    lsc = top_code(zread("LAND", ["PropertyID", "StateCode", "CurrValue"]), "CurrValue")
    p["imp_sc"] = p.PropertyID.map(isc).fillna("")
    p["land_sc"] = p.PropertyID.map(lsc).fillna("")
    sc = p.imp_sc.where(p.imp_sc.ne(""), p.land_sc).str.upper()
    r = pd.DataFrame({
        "key": p.QuickRefID, "cad_account": p.QuickRefID, "property_id": p.PropertyID,
        "situs_address": join_addr(p.SitusStreetNumber, p.SitusPreDirectional, p.SitusStreetName,
                                   p.SitusStreetSuffix, p.SitusPostDirectional).values,
        "situs_city": p.SitusCity, "situs_zip": p.SitusZip.str[:5], "state_code": sc,
        "imprv_state_cd": p.imp_sc, "land_state_cd": p.land_sc, "market_value": num(p.CurrMarketValue).values,
        "assessed_value": num(p.CurrAssessedValue).values, "land_value": num(p.CurrLandValue).values,
        "improvement_value": num(p.CurrImprovmentValue).values, "neighborhood": p.NbhdCode,
    })
    pre = zread("PROPERTY", ["QuickRefID", "CurrMarketValue"], PRELIM).drop_duplicates("QuickRefID")
    return fill_notice(r, dict(zip(pre.QuickRefID.map(norm_acct), num(pre.CurrMarketValue).values)),
                       "preliminary export 2026-03-20", only_not_protested=False)


if __name__ == "__main__":
    main("Hays", load_roll, SOURCE, DATE)
