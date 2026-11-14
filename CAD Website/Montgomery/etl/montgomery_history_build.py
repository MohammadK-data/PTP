"""Montgomery protest history (2024, 2026): who protested, one row per property per season.

2025 is not available: MCAD_Certified_2025_071626.zip was exported in Jul 2026, so its ARB file lists 2026
protests (31,204 rows for 2026, 83 for 2025) and its arb_protest_flag is F on every 2025 property.

Sources (Data/cert_2024_2025_download, PACS Legacy8 fixed-width, read straight from the zips)
    Full_Appraisal_Export_2024.zip       2024 roll as of Jul 2 2024
    MCAD_Certified_2025_071626.zip       2025 roll as of Jul 16 2026
      *_APPRAISAL_ARB.TXT   one row per protest (prop_id, year, case, type) - no status, no values, no agent
      *_APPRAISAL_INFO.TXT  arb_agent_id / ca_agent_id, state code, market value (one row per owner)
    output/montgomery_values_2026.csv    the 2026 scorecard rows

What it can and can't show
    Neither export carries a notice (pre-protest) value or a protest result, so earlier seasons have no win rate
    or reduction: only protest counts, who filed (the ARB agent on the property) and value under protest.
    Ours = arb_agent_id 654513.

Output: output/montgomery_history.csv  (state = "count_only" for 2024-25)
Run:    .venv/bin/python -I "CAD Website/Montgomery/etl/montgomery_history_build.py"
"""
import io
import json
import subprocess
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DL = ROOT / "Data" / "cert_2024_2025_download"
OUT = ROOT / "output"
LAYOUT = json.load(open(ROOT.parent / "Denton" / "etl" / "pacs_appraisal_export_layout.json"))
OUR = "654513"
ZIPS = {2024: DL / "Full_Appraisal_Export_2024.zip", 2025: DL / "MCAD_Certified_2025_071626.zip"}
INFO_F = ["prop_id", "prop_type_cd", "prop_val_yr", "sup_num", "arb_protest_flag", "arb_agent_id", "arb_agent_name",
          "ca_agent_id", "ca_agent_name", "imprv_state_cd", "land_state_cd", "market_value"]


def spans(rec, names):
    pos = {f[0]: (f[1] - 1, f[2]) for f in LAYOUT[rec]}
    return {n: pos[n] for n in names}


def member(z, suffix):
    return next(n for n in zipfile.ZipFile(z).namelist() if n.endswith(suffix))


def stream(z, suffix):
    return subprocess.Popen(["unzip", "-p", str(z), member(z, suffix)], stdout=subprocess.PIPE).stdout


def season(year):
    z = ZIPS[year]
    arb_sp = spans("APPRAISAL_ARB", [f[0] for f in LAYOUT["APPRAISAL_ARB"]])
    arb = [{k: line[a:b].strip() for k, (a, b) in arb_sp.items()}
           for line in io.TextIOWrapper(stream(z, "_APPRAISAL_ARB.TXT"), encoding="latin-1")]
    arb = pd.DataFrame(arb)
    arb["prop_id"] = arb.prop_id.str.lstrip("0")
    prot = set(arb.loc[arb.get("prop_val_yr", pd.Series(str(year))).str.lstrip("0").eq(str(year)), "prop_id"]) \
        if "prop_val_yr" in arb else set(arb.prop_id)
    sp = spans("APPRAISAL_INFO", INFO_F)
    rows = []
    for line in io.TextIOWrapper(stream(z, "_APPRAISAL_INFO.TXT"), encoding="latin-1"):
        pid = line[sp["prop_id"][0]:sp["prop_id"][1]].strip().lstrip("0")
        if pid in prot:
            rows.append({k: line[a:b].strip() for k, (a, b) in sp.items()})
    i = pd.DataFrame(rows)
    i["prop_id"] = i.prop_id.str.lstrip("0")
    i["mv"] = pd.to_numeric(i.market_value, errors="coerce")
    i["sup"] = pd.to_numeric(i.sup_num, errors="coerce")
    i = i[i.sup.eq(i.groupby("prop_id").sup.transform("max"))]
    g = i.groupby("prop_id")
    p = pd.DataFrame({"agent": g.arb_agent_id.agg(lambda s: next((x.lstrip("0") for x in s if x.strip("0")), "")),
                      "firm": g.arb_agent_name.agg(lambda s: next((x for x in s if x), "")),
                      "sc": g.imprv_state_cd.first().where(lambda s: s.ne(""), g.land_state_cd.first()),
                      "value": g.mv.sum(min_count=1)}).reset_index()
    p["who"] = np.where(p.agent.eq(OUR), "us", np.where(p.agent.ne(""), "agent", "owner"))
    out = pd.DataFrame({"year": year, "pid": p.prop_id, "res": p.sc.str.upper().str.startswith("A"), "who": p.who,
                        "firm": np.where(p.who.eq("agent"), p.firm, ""), "path": "", "notice": p.value,
                        "final": np.nan, "reduction": np.nan, "state": "count_only"})
    print(f"{year}: {len(arb):,} ARB rows -> {len(prot):,} properties, {len(out):,} found in the roll | "
          f"ours {int(out.who.eq('us').sum()):,} | {out.who.value_counts().to_dict()}")
    return out


def y2026():
    v = pd.read_csv(OUT / "montgomery_values_2026.csv", dtype=str, keep_default_na=False)
    v = v[v.protested.eq("True")]
    import re
    names = {}
    for s in v.agents_all:
        for nm, k in re.findall(r"([^|]+?) \((\d+)\)", s):
            names.setdefault(k, nm.strip())
    who = np.where(v.is_ours.eq("True"), "us", np.where(v.agent.ne(""), "agent",
                   np.where(v.appealedByType.str.upper().str.startswith("O"), "owner", "other")))
    out = pd.DataFrame({"year": 2026, "pid": v.pID, "res": v.stateCd.str.upper().str.startswith("A"), "who": who,
                        "firm": [names.get(a, "") if w == "agent" else "" for a, w in zip(v.agent, who)],
                        "path": v.path.replace({"Dismissed": "Withdrawn"}),
                        "notice": pd.to_numeric(v.notice_value, errors="coerce"),
                        "final": pd.to_numeric(v.final_value, errors="coerce")})
    out["reduction"] = out.notice - out.final
    out["state"] = np.select([out.path.eq("Open"), v.check_values.eq("True").values], ["open", "flag"], default="closed")
    print(f"2026: {len(out):,} properties | ours {int(out.who.eq('us').sum()):,}")
    return out


if __name__ == "__main__":
    print("ARB layout:", [f[0] for f in LAYOUT["APPRAISAL_ARB"]])
    h = pd.concat([season(2024), y2026()], ignore_index=True)
    h.to_csv(OUT / "montgomery_history.csv", index=False)
    print("wrote", OUT / "montgomery_history.csv", f"{len(h):,}")
