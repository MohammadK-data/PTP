"""Fort Bend CAD: 2026 Orion preliminary export 2026-06-15 (latest 2026 roll with all property types we have;
FBCAD posts no certified 2026 export in our download folder). State code = StateCodeImp, else StateCodeLand.
Market value = sum of the owner-row values (improvement + land HS/NHS, ag & timber market, personal, mineral, auto).
Account = PropertyQuickRefID (R..., P..., M...). Address = SitusStreetAddress / SitusCity / SitusZip.
Notice value = same value sum in the earlier preliminary export 2026-03-27 (notice-run values; "MinusSecured" =
confidential accounts left out, so a few accounts have no notice value).
Run: /Users/user2/PTP/.venv/bin/python -I "Market Analysis/etl/active_accounts_2026/fort_bend.py"
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CAD, fill_notice, main, norm_acct, num  # noqa: E402

D = next((CAD / "For Bend" / "Data" / "2026_06_15_1742-Orion-2026-Preliminary-Export-Redacted-2").glob("*/"))
D_NOTICE = next((CAD / "For Bend" / "Data" / "fbcad_2026_preliminary_0327").glob("*/"))
SOURCE = "FBCAD 2026 Orion preliminary export 2026-06-15 (PropertyExport + OwnerExport)"
DATE = "2026-06-15"
VALS = ["ImpHSValue", "ImpNHSValue", "LandHSValue", "LandNHSValue", "AgMktValue", "TimMktValue", "PersonalValue",
        "MineralValue", "AutoValue"]


def read(name, cols, folder=None):
    f = next((folder or D).glob(f"*_{name}*.txt"))
    return pd.read_csv(f, dtype=str, keep_default_na=False, encoding="utf-8-sig",
                       usecols=lambda c: c.lstrip("﻿") in cols).rename(columns=lambda c: c.lstrip("﻿"))


def values(folder=None):
    o = read("OwnerExport", {"PropertyQuickRefID", *VALS}, folder)
    o["mv"] = o[VALS].apply(num).fillna(0).sum(axis=1)
    return o.groupby(o.PropertyQuickRefID.str.strip()).mv.sum()


def load_roll():
    p = read("PropertyExport", {"PropertyQuickRefID", "PropertyTypeCode", "StateCodeLand", "StateCodeImp", "TaxYear",
                                "SitusStreetAddress", "SitusCity", "SitusZip"})
    p = p.apply(lambda c: c.str.strip()).drop_duplicates("PropertyQuickRefID", keep="last")
    mv = values()
    sc = p.StateCodeImp.where(p.StateCodeImp.ne(""), p.StateCodeLand).str.upper()
    r = pd.DataFrame({
        "key": p.PropertyQuickRefID, "cad_account": p.PropertyQuickRefID, "situs_address": p.SitusStreetAddress,
        "situs_city": p.SitusCity, "situs_zip": p.SitusZip.str[:5], "prop_type": p.PropertyTypeCode,
        "state_code": sc, "imprv_state_cd": p.StateCodeImp, "land_state_cd": p.StateCodeLand,
        "market_value": p.PropertyQuickRefID.map(mv).values,
    })
    nv = values(D_NOTICE)
    return fill_notice(r, dict(zip(nv.index.map(norm_acct), nv.values)), "preliminary export 2026-03-27",
                       only_not_protested=False)


if __name__ == "__main__":
    main("Fort Bend", load_roll, SOURCE, DATE)
