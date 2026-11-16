"""Bexar protests 2022-2026, one row per property per season, plus the 2026 values file in the shared layout.

Sources (CAD Website/Bexar)
    output/bexar_arb_2022_2026.csv.gz   from bexar_arb_extract.py (BCAD agent export ARB file, Oct 26 2026)
    Data/2026 Agent Export as of 2026-10-26.zip            FID_PropDataExport.txt -> year built, living area
    Data/2026 Appraisal Data Export as of 2026-10-08_Sup 298  APPRAISAL_INFO / _AGENT (Oct 15) -> agents of record,
                                                           owner, address (PACS layout 8.0.34, same positions)

Rules
    Value protests only (prot_type 25PROT). One protest per property per season: ours first, then closed over open,
    settled (informal / ARB) over no-show or withdrawn, then the lowest final value.
    Ours = agent_name "PROPERTY TAX PROTEST" (BCAD agent 3619474; 60800 is an older ID with no protests 2022-26).
    Status (BCAD ARB status codes):
      Informal  VA, EVA, VANC, VASP, EA, PFVA, TOPLN, ETOPLN, ADR-PRE, SOAH-PRE (value agreements / settlements)
      ARB       ORD.A, ORD.A-BULK, ORD.D, ORD.D-BULK, CG, FULL (board orders)
      No-show   PFNS, PFNSW;  Withdrawn  PFWD, EWD
      Other     ORD-NJ, ORD-NON, ORD-11.43D, MOT.A, MOT.D, NJ, LIT-*, ADR, BDA, SOAH, SOAH ALJ, CL, PCL
      not a protest  DELDUP;  anything else = still open
    Notice = begin_market, final = final_market. Residential = state code A*. Homestead = HS in exemptions.

Outputs: output/bexar_seasons.csv.gz (season rows for the page), output/bexar_values_2026.csv
Run:     .venv/bin/python -I "CAD Website/Bexar/etl/bexar_values_build.py"
"""
import io
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
AGZ = ROOT / "Data" / "2026 Agent Export as of 2026-10-26.zip"
APZ = ROOT / "Data" / "2026 Appraisal Data Export as of 2026-10-08_Sup 298" / "2026 Appraisal Data Export as of 2026-10-08_Sup 298.zip"
LAYOUT = json.load(open(ROOT.parent / "Denton/etl/pacs_appraisal_export_layout.json"))
US_NAME, OUR_IDS = "PROPERTY TAX PROTEST", {"3619474", "60800"}

INF = {"VA", "EVA", "VANC", "VASP", "EA", "PFVA", "TOPLN", "ETOPLN", "ADR-PRE", "SOAH-PRE"}
ARB = {"ORD.A", "ORD.A-BULK", "ORD.D", "ORD.D-BULK", "CG", "FULL"}
NS, WD = {"PFNS", "PFNSW"}, {"PFWD", "EWD"}
OTH = {"ORD-NJ", "ORD-NON", "ORD-11.43D", "MOT.A", "MOT.D", "NJ", "LIT-D", "LIT-F", "LIT-N", "ADR", "BDA", "SOAH",
       "SOAH ALJ", "CL", "PCL"}


def path_of(s):
    return ("Informal" if s in INF else "ARB" if s in ARB else "No-show" if s in NS else "Withdrawn" if s in WD
            else "Other" if s in OTH else "Not a protest" if s == "DELDUP" else "Open")


def stream(zipf, member):
    return io.TextIOWrapper(subprocess.Popen(["unzip", "-p", str(zipf), member], stdout=subprocess.PIPE).stdout, encoding="latin-1")


def roll():
    cache = OUT / "bexar_roll_2026_slim.csv.gz"
    if cache.exists():
        return pd.read_csv(cache, dtype=str, keep_default_na=False)
    want = ["prop_id", "sup_num", "py_owner_name", "situs_num", "situs_street", "situs_city", "ca_agent_id", "arb_agent_id", "market_value"]
    sp = {f[0]: (f[1] - 1, f[2]) for f in LAYOUT["APPRAISAL_INFO"] if f[0] in want}
    rows = [{k: line[a:b].strip() for k, (a, b) in sp.items()} for line in stream(APZ, "2026-10-15_007456_APPRAISAL_INFO.TXT")]
    r = pd.DataFrame(rows)
    for c in ("prop_id", "ca_agent_id", "arb_agent_id"):
        r[c] = r[c].str.lstrip("0")
    r["sup"] = pd.to_numeric(r.sup_num, errors="coerce")
    r = r.sort_values("sup").drop_duplicates("prop_id", keep="last").drop(columns=["sup"])
    r.to_csv(cache, index=False)
    return r


def main():
    a = pd.read_csv(OUT / "bexar_arb_2022_2026.csv.gz", dtype=str, keep_default_na=False)
    a = a[a.prot_type.eq("25PROT") & a.year.isin([str(y) for y in range(2022, 2027)])].copy()
    a["path"] = a.prot_status.map(path_of)
    a = a[a.path.ne("Not a protest")]
    a["ours"] = a.agent_name.eq(US_NAME)
    a["bM"], a["fM"] = pd.to_numeric(a.begin_market, errors="coerce"), pd.to_numeric(a.final_market, errors="coerce")
    a["open"] = a.path.eq("Open")
    a["rk"] = a.path.map({"Informal": 0, "ARB": 0, "Other": 1, "Open": 2}).fillna(1)
    a["rows_for_account"] = a.groupby(["year", "prop_id"]).prop_id.transform("size")
    ours = set(zip(a.loc[a.ours, "year"], a.loc[a.ours, "prop_id"]))
    keyo = pd.Series(list(zip(a.year, a.prop_id)), index=a.index).isin(ours)
    a = a[~keyo | a.ours].sort_values(["year", "prop_id", "open", "rk", "fM"]).drop_duplicates(["year", "prop_id"])
    a.loc[a.path.isin(["No-show", "Withdrawn", "Other"]) & ~(a.fM > 0), "fM"] = a.bM
    print("seasons:", a.groupby("year").agg(props=("prop_id", "size"), ours=("ours", "sum"), open=("open", "sum")).to_dict("index"))

    # property traits (2026 file, used for every season)
    pdx = pd.read_csv(stream(AGZ, "FID_PropDataExport.txt"), sep="|", header=None, dtype=str, keep_default_na=False,
                      usecols=[0, 2, 3], names=["prop_id", "yrb", "sf"], quoting=3, on_bad_lines="skip")
    pdx = pdx.drop_duplicates("prop_id").set_index("prop_id")
    a["yrb"] = a.prop_id.map(pdx.yrb).fillna("")
    a["sf"] = a.prop_id.map(pdx.sf).fillna("")
    a["city"] = a.situs.str.extract(r"\s{2,}([A-Z][A-Z .'-]+?),\s*TX", expand=False).fillna("").str.strip()
    a["zip"] = a.situs.str.extract(r"TX\s+(\d{5})", expand=False).fillna("")
    a["HS"] = a.exemptions.str.contains(r"\bHS\b").astype(int)
    a["hmon"] = pd.to_datetime(a.docket_start.str[:10], format="%m/%d/%Y", errors="coerce").dt.month
    a["resT"] = a.path.map({"Informal": "Informal settlement", "ARB": "ARB hearing", "No-show": "Dismissed / no-show",
                            "Withdrawn": "Withdrawn"}).fillna("Other / closed")
    a.to_csv(OUT / "bexar_seasons.csv.gz", index=False)

    # 2026 values file (shared layout, as dallas_values_2026.csv)
    r = roll().set_index("prop_id")
    agz = {line[:12].strip().lstrip("0"): line[12:82].strip() for line in stream(APZ, "2026-10-15_007456_APPRAISAL_AGENT.TXT")}
    v = a[a.year.eq("2026")].copy()
    rr = r.reindex(v.prop_id)
    ids = [[x for x in dict.fromkeys([c, b]) if x] for c, b in zip(rr.ca_agent_id.fillna(""), rr.arb_agent_id.fillna(""))]
    bytype = v.prot_by_type.map({"AG": "Agent", "ANR": "Agent", "OW": "Owner"}).fillna("Other")
    out = pd.DataFrame({
        "pID": v.prop_id.values, "account": v.geo_id.values, "propType": v.prop_type_cd.values, "stateCd": v.state_cd.values,
        "protested": True, "is_ours": v.ours.values, "appealedByType": np.where(v.ours, "Agent", bytype),
        "agent": np.where(v.ours, "3619474", np.where(v.agent_name.ne(""), "name:" + v.agent_name, "")),
        "agent_name": v.agent_name.values, "agent_ids_all": [" | ".join(x) for x in ids],
        "agents_current": [" | ".join(f"{agz.get(i, i)} ({i})" for i in x) for x in ids],
        "agents_all": [" | ".join(f"{agz.get(i, i)} ({i})" for i in x) for x in ids],
        "path": v.path.values, "status": v.prot_status.values, "source": "BCAD agent export Oct 26",
        "rows_for_account": v.rows_for_account.values, "notice_value": v.bM.values, "final_value": v.fM.values,
        "roll_value": pd.to_numeric(rr.market_value, errors="coerce").values,
        "situs": v.situs.str.replace(r"\s{2,}.*$", "", regex=True).values, "owner": rr.py_owner_name.fillna("").values,
        "city": v.city.values, "zip": v.zip.values, "nb": v.hood_cd.values, "yrb": v.yrb.values, "sf": v.sf.values,
        "homestead": v.HS.eq(1).values, "hearing_dt": v.docket_start.str[:10].values, "resolved_dt": "", "consent_dt": "",
        "arb_panel": ""})
    out["reduction"] = out.notice_value - out.final_value
    out["reduction_pct"] = (out.reduction / out.notice_value).where(out.notice_value > 0)
    out["check_values"] = ~out.path.eq("Open") & ((out.notice_value.fillna(0) <= 0) | (out.final_value > out.notice_value * 1.25))
    out["outcome"] = np.select([out.path.eq("Open"), out.reduction > 0, out.reduction < 0], ["Open", "Reduced", "Increased"], "No change")
    out["est_fee_1pct"] = (out.reduction.clip(lower=0) * 0.01).where(out.is_ours & out.path.ne("Open"))
    out.to_csv(OUT / "bexar_values_2026.csv", index=False)
    o = out[out.is_ours]
    oc = o[o.path.ne("Open") & ~o.check_values]
    listed = r.index[r.ca_agent_id.isin(OUR_IDS) | r.arb_agent_id.isin(OUR_IDS)]
    print(f"bexar_values_2026.csv: {len(out):,} | ours {len(o)} {o.path.value_counts().to_dict()} | win {(oc.reduction > 0).mean():.1%} "
          f"| cut {oc.reduction.sum() / oc.notice_value.sum():.1%} | roll lists us on {len(listed):,} properties, "
          f"{len(set(listed) & set(o.pID)):,} of them our 2026 protests")


if __name__ == "__main__":
    main()
