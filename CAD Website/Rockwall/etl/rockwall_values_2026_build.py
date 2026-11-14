"""Rockwall 2026: one row per protested property with notice / final value, how it ended and who filed it,
in the same columns as dallas_values_2026.csv (so the shared Book & totals, summary and search scripts work).

Sources
    ~/Downloads/County_Protest_Data/Rockwall/rockwall_protests_2023-2026.csv   developers' file (Oct 14), 2026 rows
        Rockwall publishes no protest list, so this is the only complete one.
    Data/RCAD PRELIM 2026 APP ROLL 05_26_2026   PACS export, agents of record after the filing deadline
    Data/RCAD ADJ 2026 (RC6) APP ROLL 100726     PACS export Oct 9: agents now, address, owner, market value

Rules
    One protest per property: ours first, then closed over open, settled over no-show/withdrawn, lowest final.
    Ours = agent 1044073 (PROPERTY TAX PROTEST). 1044084 is a dead duplicate ("DO NOT USE"); Ballard (1114733)
    is another firm. Notice = notice_market_value, final = final_market_value.

Output: output/rockwall_values_2026.csv
Run:    .venv/bin/python -I "CAD Website/Rockwall/etl/rockwall_values_2026_build.py"
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA, OUT = ROOT / "Data", ROOT / "output"
DEV = Path.home() / "Downloads/County_Protest_Data/Rockwall/rockwall_protests_2023-2026.csv"
LAYOUT = json.load(open(ROOT.parent / "Denton/etl/pacs_appraisal_export_layout.json"))
OURS = {"1044073", "1044084"}
INFO_F = ["prop_id", "prop_type_cd", "sup_num", "py_owner_name", "situs_num", "situs_street_prefx", "situs_street",
          "situs_street_suffix", "situs_city", "situs_zip", "hood_cd", "imprv_state_cd", "land_state_cd",
          "ca_agent_id", "arb_agent_id", "market_value", "hs_exempt"]


def roll(folder, stamp):
    d = DATA / folder
    sp = {f[0]: (f[1] - 1, f[2]) for f in LAYOUT["APPRAISAL_INFO"] if f[0] in INFO_F}
    rows = [{k: line[a:b].strip() for k, (a, b) in sp.items()}
            for line in open(d / f"{stamp}_2026_APPRAISAL_INFO.TXT", encoding="latin-1")]
    r = pd.DataFrame(rows)
    r["prop_id"] = r.prop_id.str.lstrip("0")
    for c in ("ca_agent_id", "arb_agent_id"):
        r[c] = r[c].str.lstrip("0")
    r["sup"] = pd.to_numeric(r.sup_num, errors="coerce")
    r = r.sort_values("sup").drop_duplicates("prop_id", keep="last")
    ag = {}
    for line in open(d / f"{stamp}_2026_APPRAISAL_AGENT.TXT", encoding="latin-1"):
        ag[line[:12].strip().lstrip("0")] = line[12:82].strip()
    print(f"{stamp}: {len(r):,} properties")
    return r.set_index("prop_id"), ag


def main():
    may, ag_may = roll("RCAD PRELIM 2026 APP ROLL 05_26_2026", "2026-05-26")
    octr, ag_oct = roll("RCAD ADJ 2026 (RC6) APP ROLL 100726", "2026-10-09")
    names = {**ag_may, **ag_oct}

    d = pd.read_csv(DEV, dtype=str, keep_default_na=False)
    d = d[d.tax_year.eq("2026")].copy()
    d["pid"] = d.account.str.strip().str.lstrip("0")
    d["ours"] = d.is_ours.str.lower().eq("true") | d.agent_id.isin(OURS)
    d["open"] = d.outcome_type.eq("Open / unresolved")
    d["bM"], d["fM"] = pd.to_numeric(d.notice_market_value, errors="coerce"), pd.to_numeric(d.final_market_value, errors="coerce")
    d["rk"] = d.outcome_type.map({"Informal settlement": 0, "ARB hearing": 0}).fillna(1)
    ours = set(d.loc[d.ours, "pid"])
    d["rows_for_account"] = d.groupby("pid").pid.transform("size")
    d = d[~d.pid.isin(ours) | d.ours].sort_values(["pid", "open", "rk", "fM"]).drop_duplicates("pid")
    path = d.outcome_type.map({"Informal settlement": "Informal", "ARB hearing": "ARB", "Dismissed / no-show": "No-show",
                               "Withdrawn": "Withdrawn", "Open / unresolved": "Open"}).fillna("Other")
    final = d.fM.where(~path.isin(["No-show", "Withdrawn", "Other"]) | (d.fM > 0), d.bM)

    def agents(pid, rolls):
        ids = []
        for r in rolls:
            if pid in r.index:
                ids += [x for x in (r.at[pid, "ca_agent_id"], r.at[pid, "arb_agent_id"]) if x]
        return list(dict.fromkeys(ids))
    all_ids = [agents(p, [may, octr]) for p in d.pid]
    cur_ids = [agents(p, [octr]) for p in d.pid]
    o = octr.reindex(d.pid)
    situs = (o.situs_num.fillna("") + " " + o.situs_street_prefx.fillna("") + " " + o.situs_street.fillna("") + " " +
             o.situs_street_suffix.fillna("")).str.replace(r"\s+", " ", regex=True).str.strip()
    v = pd.DataFrame({
        "pID": d.pid.values, "account": d.account.values, "propType": d.acct_type.values, "stateCd": d.state_code.values,
        "protested": True, "is_ours": d.ours.values,
        "appealedByType": d.filed_by.str.title().replace({"Agent": "Agent", "Owner": "Owner"}).values,
        "agent": np.where(d.ours, "1044073", d.agent_id).astype(str),
        "agent_name": np.where(d.ours, "PROPERTY TAX PROTEST", d.agent_name),
        "agent_ids_all": [" | ".join(x) for x in all_ids],
        "agents_current": [" | ".join(f"{names.get(i, i)} ({i})" for i in x) for x in cur_ids],
        "agents_all": [" | ".join(f"{names.get(i, i)} ({i})" for i in x) for x in all_ids],
        "path": path.values, "status": d.status_desc.values, "source": "developers' file Oct 14",
        "rows_for_account": d.rows_for_account.values, "notice_value": d.bM.values, "final_value": final.values,
        "roll_value": pd.to_numeric(o.market_value, errors="coerce").values, "situs": situs.values,
        "owner": o.py_owner_name.values, "city": d.city.values, "zip": d.zip.values, "nb": d.neighborhood_code.values,
        "yrb": d.yr_built.values, "sf": d.living_sf.values, "homestead": d.homestead.eq("T").values,
        "hearing_dt": d.hearing_date.values, "resolved_dt": "", "consent_dt": "", "arb_panel": d.get("arb_panel", "")})
    v["reduction"] = v.notice_value - v.final_value
    v["reduction_pct"] = (v.reduction / v.notice_value).where(v.notice_value > 0)
    v["check_values"] = ~v.path.eq("Open") & ((v.notice_value.fillna(0) <= 0) | (v.final_value > v.notice_value * 1.25))
    v["outcome"] = np.select([v.path.eq("Open"), v.reduction > 0, v.reduction < 0], ["Open", "Reduced", "Increased"], "No change")
    v["est_fee_1pct"] = (v.reduction.clip(lower=0) * 0.01).where(v.is_ours & v.path.ne("Open"))
    v.to_csv(OUT / "rockwall_values_2026.csv", index=False)
    o_ = v[v.is_ours]
    oc = o_[o_.path.ne("Open") & ~o_.check_values]
    listed = sum(bool(OURS & set(x)) for x in all_ids)
    print(f"rockwall_values_2026.csv: {len(v):,} protested properties | ours {len(o_)} ({o_.path.value_counts().to_dict()}) | "
          f"win {(oc.reduction > 0).mean():.1%} | cut {oc.reduction.sum() / oc.notice_value.sum():.1%} | "
          f"protested properties listing us on the rolls: {listed}")
    all_listed = set(p for r in (may, octr) for p in r.index[r.ca_agent_id.isin(OURS) | r.arb_agent_id.isin(OURS)])
    print(f"properties listing us on the May/Oct rolls: {len(all_listed)}; of them protested: {len(all_listed & set(v.pID))}")


if __name__ == "__main__":
    main()
