"""Rockwall CAD market fragment -> Market Analysis/work/rockwall/{market,segments,firms}.csv

Every source is the PACS appraisal export Rockwall CAD posts at https://www.rockwallcad.com/data-exports.
  roll      certified export (2026-07-13, 2025-07-14, 2024-07-11) APPRAISAL_INFO: state code, hs_exempt
  agents    APPRAISAL_INFO ca_agent_id / arb_agent_id of the export nearest after the May 15 deadline
            (2026: May 26 prelim; 2025: Jun 20 prelim; 2024: cert Jul 11 - the Apr 20 prelim is before the deadline)
            names from APPRAISAL_AGENT. No appointment dates in the export.
  protests  APPRAISAL_ARB rows for the tax year, union over every export of that year we have (each ARB file
            only lists protests on file at that export date) minus 25.25 correction motions. No filer field:
            agent-filed = an ARB agent (arb_agent_id) on the property in the deadline export, or status O-AGT*.
"""
import csv
import gzip
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from market_common_dfw import compute, write  # noqa: E402

W = HERE.parent / "work" / "rockwall"
RW = Path("/Users/user2/PTP/CAD Website/Rockwall")
DL = RW / "Data" / "rockwall_prior_download"
PTP_IDS = {"1044073", "1044084"}   # both RCAD agent-list entries named PROPERTY TAX PROTEST (1044084 marked 'DO NOT USE - SEE 549409')
COUNTY = "Rockwall"
L = json.load(open("/Users/user2/PTP/CAD Website/Denton/etl/pacs_appraisal_export_layout.json"))
INFO_COLS = ["prop_id", "prop_type_cd", "prop_val_yr", "sup_num", "hs_exempt", "imprv_state_cd", "land_state_cd",
             "personal_state_cd", "mineral_state_cd", "ca_agent_id", "arb_agent_id", "arb_protest_flag"]


def fixed(path, rec, cols):
    pos = {f[0]: (f[1] - 1, f[2]) for f in L[rec] if f[0] in cols}
    with open(path, encoding="latin-1") as f:
        rows = [[ln[pos[c][0]:pos[c][1]].strip() for c in cols] for ln in f]
    return pd.DataFrame(rows, columns=cols)


def load(export, rec):
    """export = ('csv', '2026-05-26') for the converted 2026 files in CAD Website/Rockwall/output,
       or ('txt', <dir>) for a downloaded raw export."""
    kind, where = export
    if kind == "csv":
        f = RW / "output" / f"{where}_2026_{rec}.csv.gz"
        cols = {"APPRAISAL_INFO": INFO_COLS, "APPRAISAL_ARB": ["prop_id", "prop_val_yr", "arb_status"],
                "APPRAISAL_AGENT": ["agent_id", "agent_name"]}[rec]
        return pd.read_csv(f, dtype=str, keep_default_na=False, usecols=cols)
    f = next(Path(where).glob(f"*_{rec}.TXT"))
    if rec == "APPRAISAL_INFO":
        slim = W / f"{Path(where).name}_info_slim.csv.gz"
        if not slim.exists():
            fixed(f, rec, INFO_COLS).to_csv(slim, index=False)
        return pd.read_csv(slim, dtype=str, keep_default_na=False)
    return fixed(f, rec, {"APPRAISAL_ARB": ["prop_id", "prop_val_yr", "arb_status"],
                          "APPRAISAL_AGENT": ["agent_id", "agent_name"]}[rec])


def roll_of(info):
    c = info.copy()
    c["pid"] = c.prop_id.str.lstrip("0")
    c["sc"] = c.imprv_state_cd.where(c.imprv_state_cd.ne(""), c.land_state_cd.where(
        c.land_state_cd.ne(""), c.personal_state_cd.where(c.personal_state_cd.ne(""), c.mineral_state_cd)))
    hs = c.groupby("pid").hs_exempt.apply(lambda s: s.eq("T").any())
    c["sup"] = pd.to_numeric(c.sup_num, errors="coerce")
    c = c.sort_values(["pid", "sup"]).drop_duplicates("pid", keep="last")
    c["hs"] = c.pid.map(hs)
    return c


def protests_of(exports, year):
    a = pd.concat([load(e, "APPRAISAL_ARB") for e in exports])
    a = a[a.prop_val_yr.str.lstrip("0").eq(str(year))].copy()
    a["pid"] = a.prop_id.str.lstrip("0")
    a = a[~a.arb_status.str.startswith("25.25")]
    a["agt_status"] = a.arb_status.str.startswith("O-AGT")
    return a.groupby("pid").agt_status.any().reset_index()       # one protest per account-year (PACS keys ARB by prop/year)


def pids(exports, year):
    return set(protests_of(exports, year).pid) if exports else set()


def run(year, cert, deadline_export, arb_exports, history_exports, src):
    roll = roll_of(load(cert, "APPRAISAL_INFO"))
    dl = roll_of(load(deadline_export, "APPRAISAL_INFO"))
    names = load(deadline_export, "APPRAISAL_AGENT")
    nm = dict(zip(names.agent_id.str.lstrip("0"), names.agent_name))
    ag = pd.concat([pd.DataFrame({"pid": dl.pid, "agent_id": dl[c].str.lstrip("0")}) for c in ["arb_agent_id", "ca_agent_id"]])
    ag = ag[ag.agent_id.ne("")].drop_duplicates()
    ag["name"] = ag.agent_id.map(nm).fillna("")
    appeals = None
    if arb_exports:
        p = protests_of(arb_exports, year)
        arb_ag = dict(zip(dl.pid, dl.arb_agent_id.str.lstrip("0")))
        p["agent_id"] = p.pid.map(arb_ag).fillna("")
        p["filer"] = (p.agent_id.ne("") | p.agt_status).map({True: "A", False: "O"})
        appeals = p[["pid", "filer", "agent_id"]]
    hist = None
    if history_exports is not None:
        hist = set()
        for y, ex in history_exports.items():
            hist |= pids(ex, y)
    print(year, "history accounts", None if hist is None else len(hist))
    return compute(COUNTY, year, roll[["pid", "sc", "hs"]], ag[["pid", "agent_id", "name"]], appeals, PTP_IDS, hist, src)


def T(name):
    return ("txt", str(DL / name))


if __name__ == "__main__":
    have = {d.name for d in DL.iterdir() if d.is_dir()} if DL.exists() else set()
    out = []
    # history: every ARB snapshot of an earlier year 2022.. that we have (prior-year rows inside later exports included)
    snaps = {2026: [("csv", d) for d in ["2026-03-16", "2026-05-26", "2026-07-13", "2026-10-09"]],
             2025: [T(n) for n in ["rc_2025_prelim_0620", "rc_2025_cert"] if n in have],
             2024: [T(n) for n in ["rc_2024_prelim_0420", "rc_2024_cert_0711"] if n in have],
             2023: [T(n) for n in ["rc_2023_prelim_0605"] if n in have]}
    later = lambda y: [e for yy, ex in snaps.items() if yy >= y for e in ex]   # prior-year rows also show in later files
    # No complete protest list for 2022 (certified-only, July) or 2024 (Apr 20 prelim needs a Google sign-in; the
    # 'July 11' file is an Aug 23 export with only still-open protests) -> history incomplete -> seg_lapsed_or_never.
    hist_for = lambda y: None
    out.append(run(2026, ("csv", "2026-07-13"), ("csv", "2026-05-26"), snaps[2026], hist_for(2026),
                   {"source_roll_file": "RCAD CERT 2026 APP ROLL 07_13_2026 / 2026-07-13_2026_APPRAISAL_INFO.TXT",
                    "source_agent_file": "RCAD PRELIM 2026 APP ROLL 05_26_2026 / APPRAISAL_INFO ca_agent_id+arb_agent_id, APPRAISAL_AGENT",
                    "source_protest_file": "APPRAISAL_ARB.TXT of the 2026-03-16, 05-26, 07-13, 10-09 exports (union, excl. 25.25)",
                    "roll_version_date": "2026-07-13"}))
    if "rc_2025_cert" in have and "rc_2025_prelim_0620" in have:
        out.append(run(2025, T("rc_2025_cert"), T("rc_2025_prelim_0620"), None, hist_for(2025),
                       {"source_roll_file": "2025 CERTIFIED APPRAISAL ROLL as of July 14, 2025 / 2025-07-14_2025_APPRAISAL_INFO.TXT",
                        "source_agent_file": "2025 PRELIMINARY APPRAISAL ROLL as of June 20, 2025 / APPRAISAL_INFO agent ids, APPRAISAL_AGENT",
                        "source_protest_file": "",
                        "roll_version_date": "2025-07-14"}))
    if "rc_2024_cert_0711" in have:
        out.append(run(2024, T("rc_2024_cert_0711"), T("rc_2024_cert_0711"), None, None,
                       {"source_roll_file": "'2024 CERTIFIED APPRAISAL ROLL as of July 11, 2024' link (file inside: 2024-08-23_2024_APPRAISAL_INFO.TXT)",
                        "source_agent_file": "same export: APPRAISAL_INFO ca_agent_id+arb_agent_id, APPRAISAL_AGENT (Aug 23, after the deadline)",
                        "source_protest_file": "",
                        "roll_version_date": "2024-08-23"}))
    # 2025 ARB rows (Jun 20 + Jul 14 + 2026 exports) give only a lower bound -> reported in notes.md, not in market.csv
    if "rc_2025_prelim_0620" in have:
        p25 = protests_of(later(2025), 2025)
        r25 = roll_of(load(T("rc_2025_cert"), "APPRAISAL_INFO"))
        h25 = set(r25.loc[r25.sc.str.startswith("A"), "pid"])
        print("2025 ARB-snapshot lower bound: accounts", len(p25), "homes", len(set(p25.pid) & h25))
    write(W, [o[0] for o in out], [o[1] for o in out], [f for o in out for f in o[2]])
    print(pd.read_csv(W / "market.csv").T.to_string())
    print(pd.read_csv(W / "segments.csv").to_string())
    print(pd.read_csv(W / "firms.csv").to_string())
