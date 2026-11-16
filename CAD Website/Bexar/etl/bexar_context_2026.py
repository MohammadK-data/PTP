"""Bexar 2026 market context, neighborhood names and city fill for the scorecard page.

Sources (CAD Website/Bexar)
    output/2026-10-15_2026_APPRAISAL_INFO.csv.gz   full Oct 15 roll (bexar_appraisal_export_etl.py): state code, HS,
                                                    10% cap, circuit-breaker loss, situs city / zip, neighborhood
    output/2026 Property Summary Export as of 2026-03-28__1st Notice Run Preliminary (with header).csv
                                                    notice market value and prior-year (2025) market value
    output/bexar_seasons.csv.gz                     protested properties per season (bexar_values_build.py)
    Data/2026 Neighborhood Codes.xlsx               BCAD neighborhood names

Context row (template order): [season, residential accounts, median notice change, share with a higher notice,
homesteads held by the 10% cap, non-HS held by the 20% circuit breaker]; protestRate: [season, residential
accounts, residential protested]. Only 2026 has a full roll in the folder, so earlier seasons get no row.

Output: output/bexar_context_2026.json
Run:    .venv/bin/python -I "CAD Website/Bexar/etl/bexar_context_2026.py"
"""
import json
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"


def num(s):
    return pd.to_numeric(s, errors="coerce")


def nb_names():
    z = zipfile.ZipFile(ROOT / "Data" / "2026 Neighborhood Codes.xlsx")
    ss = [re.sub("<[^>]+>", "", s) for s in re.findall(r"<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode(), re.S)]
    ss = [s.replace("&amp;", "&").replace("&apos;", "'").replace("&quot;", '"').strip() for s in ss]
    names = {}
    for row in re.findall(r"<row [^>]*>(.*?)</row>", z.read("xl/worksheets/sheet1.xml").decode(), re.S):
        cells = {}
        for ref, typ, v in re.findall(r'<c r="([A-Z]+)\d+"([^>]*)>(?:<f>.*?</f>)?<v>(.*?)</v></c>', row):
            cells[ref] = ss[int(v)] if 't="s"' in typ else v
        code, name = cells.get("B", "").strip(), cells.get("C", "").strip()
        if code and name and code != "NBHD":
            names[code] = name
    return names


def main():
    cols = ["prop_id", "sup_num", "situs_city", "situs_zip", "hood_cd", "ten_percent_cap", "hs_exempt", "imprv_state_cd",
            "land_state_cd", "nhs_cap_loss", "market_value"]
    r = pd.read_csv(OUT / "2026-10-15_2026_APPRAISAL_INFO.csv.gz", dtype=str, keep_default_na=False, usecols=cols)
    r["prop_id"] = r.prop_id.str.lstrip("0")
    r = r.assign(s=num(r.sup_num)).sort_values("s").drop_duplicates("prop_id", keep="last")
    st = r.imprv_state_cd.str.strip().where(r.imprv_state_cd.str.strip().ne(""), r.land_state_cd.str.strip()).str.upper()
    res = r[st.str.startswith("A")]
    hs = res.hs_exempt.str.upper().eq("T")
    cap_hs = (num(res.ten_percent_cap[hs]).fillna(0) > 0).mean()
    cb_nhs = (num(res.nhs_cap_loss[~hs]).fillna(0) > 0).mean()

    ps = pd.read_csv(OUT / "2026 Property Summary Export as of 2026-03-28__1st Notice Run Preliminary (with header).csv",
                     dtype=str, keep_default_na=False, usecols=["Prop_id", "State_cd", "Market_val", "Prior Mkt val"])
    ps["Prop_id"] = ps.Prop_id.str.replace("﻿", "").str.strip().str.lstrip("0")
    ps = ps.drop_duplicates("Prop_id")
    ps = ps[ps.State_cd.str.replace('"', "").str.strip().str.upper().str.startswith("A")]
    m, p = num(ps.Market_val), num(ps["Prior Mkt val"])
    ok = (m > 0) & (p > 0)
    chg = m[ok] / p[ok] - 1

    s = pd.read_csv(OUT / "bexar_seasons.csv.gz", dtype=str, keep_default_na=False, usecols=["year", "prop_id"])
    prot = s[s.year.eq("2026")].prop_id.isin(set(res.prop_id)).sum()

    ctx = [[2026, len(res), float(chg.median()), float((chg > 0).mean()), float(cap_hs), float(cb_nhs)]]
    pr = [[2026, len(res), int(prot)]]

    # city fill: roll situs city, else the most common city for the zip
    city = r.situs_city.str.strip().str.upper()
    z = r.situs_zip.str.strip().str[:5]
    zc = pd.DataFrame({"z": z, "c": city})[city.ne("") & z.ne("")].groupby("z").c.agg(lambda x: x.mode().iat[0])
    fill = city.where(city.ne(""), z.map(zc)).fillna("")
    out = {"context": ctx, "protestRate": pr, "nbNames": nb_names(),
           "city": dict(zip(r.prop_id, fill)), "zipCity": zc.to_dict(), "rollProps": len(r)}
    (OUT / "bexar_context_2026.json").write_text(json.dumps(out), encoding="utf-8")
    print(f"roll {len(r):,} | residential {len(res):,} | protested {prot:,} ({prot / len(res):.1%}) | notice change median "
          f"{chg.median():.1%}, higher {(chg > 0).mean():.0%} (n={ok.sum():,}) | HS capped {cap_hs:.0%} | non-HS breaker {cb_nhs:.0%}"
          f" | nb names {len(out['nbNames']):,} | city blank after fill {(fill == '').mean():.1%}")


if __name__ == "__main__":
    main()
