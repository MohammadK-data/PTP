"""Denton CAD market fragment -> Market Analysis/work/denton/{market,segments,firms}.csv

All files from Denton CAD (https://www.dentoncad.com/data-downloads -> https://dentoncad.net/data/_uploaded/files/datafiles/<yr>/...).

2026  roll     certified PACS export 2026-07-27 APPRAISAL_INFO (slim: pacs_info_slim.py)
      agents   protax JSON 2026-07-27, owners[].agents with dates (denton_agent_dates.py): active at the protest deadline
      protests protax JSON 2026 appeals (CAD Website/Denton/output/denton_appeals_2026.csv.gz), CLERICAL excluded
2025  roll     certified PACS export 2025 (Denton_AppraisalDataExtracts_ALL(CERTIFIED).zip) APPRAISAL_INFO
      agents + protests   certified protax JSON 2025 (Denton_AppraisalDataExtract_JSON_ALL(CERTIFIED).zip), same rules as 2026
2024  roll + agents  certified PACS export 2024-07-22 APPRAISAL_INFO (arb_agent_id or ca_agent_id; no dates)
      protests ProTax_ARBExport.txt 2024 (certified ProTax set), filer AG/OW, 0DUPE excluded
History (seg_lapsed): accounts protested 2022..year-1 = ProTax_ARBExport 2022/2023/2024 + JSON 2025 appeals.
"""
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from market_common_dfw import compute, write  # noqa: E402

W = HERE.parent / "work" / "denton"
DEN = Path("/Users/user2/PTP/CAD Website/Denton")
DL = DEN / "Data" / "denton_prior_download"
PTP_IDS = {"245", "718105"}   # both DCAD agent-list entries named exactly PROPERTY TAX PROTEST
COUNTY = "Denton"
NOT_PROTEST_JSON = {"CLERICAL"}
NOT_PROTEST_ARB = {"0DUPE"}


def slim_roll(path):
    c = pd.read_csv(path, dtype=str, keep_default_na=False)
    c["pid"] = c.prop_id.str.lstrip("0")
    c["sc"] = c.imprv_state_cd.where(c.imprv_state_cd.ne(""), c.land_state_cd.where(
        c.land_state_cd.ne(""), c.personal_state_cd.where(c.personal_state_cd.ne(""), c.mineral_state_cd)))
    hs = c.groupby("pid").hs_exempt.apply(lambda s: s.eq("T").any())
    c["sup"] = pd.to_numeric(c.sup_num, errors="coerce")
    c = c.sort_values(["pid", "sup"]).drop_duplicates("pid", keep="last")
    c["hs"] = c.pid.map(hs)
    return c


def active_agents(g, notice, year):
    """g: pID, agentID, name, applicationDt, effectiveDt, expirationDt. Active on the protest deadline
    (May 15, or noticeDt + 30 days if later); no start date -> active; no expiration -> active."""
    may15 = pd.Timestamp(f"{year}-05-15")
    deadline = (notice + pd.Timedelta(days=30)).clip(lower=may15)
    g = g.copy()
    g["dl"] = g.pID.map(deadline).fillna(may15)
    start = pd.to_datetime(g.effectiveDt.str[:10], errors="coerce").fillna(pd.to_datetime(g.applicationDt.str[:10], errors="coerce"))
    exp = pd.to_datetime(g.expirationDt.str[:10], errors="coerce")
    g["active"] = (start.isna() | (start <= g.dl)) & (exp.isna() | (exp > g.dl))
    print(f"  {year}: appointments {len(g):,}, active at deadline {g.active.sum():,}, no start date {start.isna().sum():,}")
    return g[g.active].rename(columns={"pID": "pid", "agentID": "agent_id"})[["pid", "agent_id", "name"]]


def json_appeals(a, year):
    a = a[a.pYear.astype(str).str.replace(r"\.0$", "", regex=True).eq(str(year)) & ~a.appealStatus.str.strip().isin(NOT_PROTEST_JSON)]
    return pd.DataFrame({"pid": a.pID.astype(str), "filer": a.appealedByType.str.strip(),
                         "agent_id": a.appealedByAgentID.astype(str).str.replace(r"\.0$", "", regex=True)})


def _sep(path):
    h = open(path, encoding="utf-8-sig", errors="replace").readline()
    return "|" if h.startswith("prop_id|") else "\t"


def _arb_rows(path):
    """Yield field lists; rejoin records whose free-text fields contain line breaks."""
    sep = _sep(path)
    lines = open(path, encoding="utf-8-sig", errors="replace").read().split("\n")
    head = lines[0].rstrip("\r").split(sep)
    has_header = head[0] == "prop_id"
    n = len(head) if has_header else 78
    cur = None
    for ln in (lines[1:] if has_header else lines):
        r = ln.rstrip("\r").split(sep)
        if cur is not None and len(cur) < n:
            cur[-1] += " " + r[0]
            cur += r[1:]
        else:
            if cur is not None:
                yield cur
            cur = r
    if cur is not None:
        yield cur
    return


def arb_export(year, name2id=None):
    """ProTax_ARBExport.txt from the certified ProTax set.
    2022 file: no header, 78 fields: 0 year, 2 prop id, 11 agent ('NAME-ID' or 'NAME'), 18 protest type, 19 status,
               filer AG/OW = 56th field from the end (free text in between sometimes holds tabs).
    2023/2024: header row (prop_id, prop_val_yr, agent_name, prot_type, prot_status, prot_by_type ...).
    Kept: rows of the tax year; dropped: 25.25 correction motions and duplicate cases (status DUPE/0DUPE)."""
    path = DL / f"protax_{year}" / "ProTax_ARBExport.txt"
    first = open(path, encoding="utf-8-sig", errors="replace").readline().rstrip("\r\n").split(_sep(path))
    rows = []
    if first[0] == "prop_id":
        H = [h.strip() for h in first]
        ix = {k: H.index(k) for k in ["prop_id", "prop_val_yr", "agent_name", "prot_type", "prot_status", "prot_by_type"]}
        for r in _arb_rows(path):
            if len(r) < len(H):
                continue
            rows.append((r[ix["prop_val_yr"]].strip(), r[ix["prop_id"]].strip(), r[ix["agent_name"]].strip(),
                         r[ix["prot_type"]].strip(), r[ix["prot_status"]].strip(), r[ix["prot_by_type"]].strip()))
    else:
        for r in _arb_rows(path):
            if len(r) < 78:
                continue
            rows.append((r[0].strip(), r[2].strip(), r[11].strip(), r[18].strip(), r[19].strip(), r[len(r) - 56].strip()))
    a = pd.DataFrame(rows, columns=["yr", "pid", "agent", "ptype", "status", "filer_raw"])
    a = a[a.yr.eq(str(year)) & ~a.ptype.str.replace(" ", "").str.startswith("25.25") & ~a.status.isin({"DUPE", "0DUPE"})].copy()
    m = a.agent.str.extract(r"^(.*?)\s*(?:-|\()\s*(\d+)\)?$")   # 'NAME-ID' (2022/23) or 'NAME (ID)' (2024)
    a["agent_id"] = m[1].fillna("")
    nm = a.agent.where(m[0].isna(), m[0]).replace("NULL", "")
    if name2id is not None:
        a.loc[a.agent_id.eq("") & nm.ne(""), "agent_id"] = nm.str.upper().map(name2id).fillna("")
    a.loc[nm.str.upper().str.strip().eq("PROPERTY TAX PROTEST") & a.agent_id.eq(""), "agent_id"] = "245"
    a["filer"] = a.filer_raw.map({"AG": "A", "OW": "O"}).fillna("")
    print(f"  ARB {year}: {len(a):,} protests on {a.pid.nunique():,} accounts; filer {a.filer.value_counts().to_dict()}")
    return a


def history(year):
    h = set()
    for y in range(2022, year):
        if y <= 2024 and (DL / f"protax_{y}" / "ProTax_ARBExport.txt").exists():
            h |= set(arb_export(y).pid)
        elif y == 2025:
            f = W / "denton_2025_json_appeals.csv.gz"
            if f.exists():
                h |= set(json_appeals(pd.read_csv(f, dtype=str, keep_default_na=False), 2025).pid)
            else:
                return None
        else:
            return None
    return h


def y2026():
    roll = slim_roll(W / "denton_2026_cert_info_slim.csv.gz")
    p = pd.read_csv(DEN / "output/denton_props_2026.csv.gz", dtype=str, keep_default_na=False, usecols=["pID", "noticeDt"])
    notice = pd.to_datetime(p.set_index("pID").noticeDt.str[:10], errors="coerce")
    g = pd.read_csv(W / "denton_agent_appointments_2026.csv.gz", dtype=str, keep_default_na=False)
    agents = active_agents(g, notice, 2026)
    a = pd.read_csv(DEN / "output/denton_appeals_2026.csv.gz", dtype=str, keep_default_na=False)
    a["pYear"] = "2026"
    src = {"source_roll_file": "2026 CERTIFIED DATA - ALL PROPERTIES / 2026-07-27_2026_APPRAISAL_INFO.TXT",
           "source_agent_file": "Denton-protaxExport-20260727.json (owners[].agents, dated)",
           "source_protest_file": "Denton-protaxExport-20260727.json (appeals pYear 2026, excl. CLERICAL)",
           "roll_version_date": "2026-07-27"}
    return compute(COUNTY, 2026, roll[["pid", "sc", "hs"]], agents, json_appeals(a, 2026), PTP_IDS, history(2026), src)


def y2025():
    roll = slim_roll(W / "denton_2025_cert_info_slim.csv.gz")
    p = pd.read_csv(W / "denton_2025_json_props.csv.gz", dtype=str, keep_default_na=False)
    notice = pd.to_datetime(p.set_index("pID").noticeDt.str[:10], errors="coerce")
    g = pd.read_csv(W / "denton_2025_json_agents.csv.gz", dtype=str, keep_default_na=False)
    agents = active_agents(g, notice, 2025)
    a = pd.read_csv(W / "denton_2025_json_appeals.csv.gz", dtype=str, keep_default_na=False)
    src = dict(l.rstrip("\n").split("=", 1) for l in open(W / "denton_2025_src.txt"))
    return compute(COUNTY, 2025, roll[["pid", "sc", "hs"]], agents, json_appeals(a, 2025), PTP_IDS, history(2025), src)


def y2024():
    roll = slim_roll(W / "denton_2024_cert_info_slim.csv.gz")
    names = pd.read_csv(W / "denton_2024_agents.csv", dtype=str, keep_default_na=False)   # agent_id, agent_name
    names["agent_id"] = names.agent_id.str.lstrip("0")
    id2name = dict(zip(names.agent_id, names.agent_name))
    name2id = names.groupby(names.agent_name.str.upper()).agent_id.first().to_dict()
    agents = pd.concat([pd.DataFrame({"pid": roll.pid, "agent_id": roll[c].str.lstrip("0")}) for c in ["arb_agent_id", "ca_agent_id"]])
    agents = agents[agents.agent_id.ne("")].drop_duplicates()
    agents["name"] = agents.agent_id.map(id2name).fillna("")
    a = arb_export(2024, name2id)
    src = dict(l.rstrip("\n").split("=", 1) for l in open(W / "denton_2024_src.txt"))
    return compute(COUNTY, 2024, roll[["pid", "sc", "hs"]], agents, a[["pid", "filer", "agent_id"]],
                   PTP_IDS, history(2024), src)


if __name__ == "__main__":
    out = [y2026()]
    if (W / "denton_2025_src.txt").exists():
        out.append(y2025())
    if (W / "denton_2024_src.txt").exists():
        out.append(y2024())
    write(W, [o[0] for o in out], [o[1] for o in out], [f for o in out for f in o[2]])
    print(pd.read_csv(W / "market.csv").drop(columns=[c for c in ["source_roll_file", "source_agent_file", "source_protest_file"]]).T.to_string())
    print(pd.read_csv(W / "segments.csv").to_string())
    print(pd.read_csv(W / "firms.csv").drop(columns="agent_ids").to_string())
