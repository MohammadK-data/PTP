"""Shared counting for the Denton / Rockwall fragments (work/<county>/market.csv, segments.csv, firms.csv).

compute() inputs, one county-year:
  roll     DataFrame pid, sc (state code), hs (bool)              one row per account
  agents   DataFrame pid, agent_id, name                          active agent-of-record rows (None -> blank)
  appeals  DataFrame pid, filer ('A' agent / 'O' owner / other), agent_id   one row per value protest (None -> blank)
  history  set of pids protested in an earlier year 2022..year-1 (None -> no history: seg_lapsed_or_never)
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from firm_names_dfw import firm_of  # noqa: E402

MARKET_COLS = ["county", "year", "total_accounts", "accounts_cat_A", "accounts_cat_B", "accounts_cat_M", "mineral_accounts",
               "homes_A_homestead", "homes_A_with_agent", "homes_A_protested", "homes_A_protested_by_agent",
               "homes_A_protested_by_owner", "homes_A_ptp_agent", "homes_A_ptp_protested", "all_protests",
               "all_agent_protests", "source_roll_file", "source_agent_file", "source_protest_file", "roll_version_date"]
SEG_COLS = ["county", "year", "homes_A", "seg_agent", "seg_owner_alone", "seg_lapsed", "seg_never", "seg_lapsed_or_never", "seg_ptp"]
FIRM_COLS = ["county", "year", "firm", "agent_ids", "homes_A_agent_of_record", "homes_A_protests_filed", "all_accounts_agent_of_rec"]


def compute(county, year, roll, agents, appeals, ptp_ids, history, src, min_homes=100):
    ptp_ids = {str(x) for x in ptp_ids}
    roll = roll.drop_duplicates("pid")
    homes = set(roll.loc[roll.sc.str.upper().str.startswith("A"), "pid"])
    m = {"county": county, "year": year, "total_accounts": len(roll),
         "accounts_cat_A": len(homes),
         "accounts_cat_B": int(roll.sc.str.upper().str.startswith("B").sum()),
         "accounts_cat_M": int(roll.sc.str.upper().str.startswith("M").sum()),
         "mineral_accounts": int(roll.sc.str.upper().str.startswith("G").sum()),
         "homes_A_homestead": int(roll.loc[roll.pid.isin(homes), "hs"].sum())}
    m.update(src)
    firms, seg = [], {"county": county, "year": year, "homes_A": len(homes)}

    ag_home = set()
    if agents is not None:
        agents = agents.copy()
        agents["agent_id"] = agents.agent_id.astype(str)
        agents["firm"] = [firm_of(n, i, ptp_ids) for n, i in zip(agents.name, agents.agent_id)]
        agents = agents.drop_duplicates(["pid", "agent_id"])
        ag_home = set(agents.pid) & homes
        m["homes_A_with_agent"] = len(ag_home)
        m["homes_A_ptp_agent"] = agents[agents.agent_id.isin(ptp_ids) & agents.pid.isin(homes)].pid.nunique()
    prot_home = agent_filed = owner_filed = set()
    if appeals is not None:
        appeals = appeals.copy()
        appeals["agent_id"] = appeals.agent_id.fillna("").astype(str)
        is_ag = appeals.filer.eq("A") | appeals.agent_id.ne("")
        prot_home = set(appeals.pid) & homes
        agent_filed = set(appeals.loc[is_ag, "pid"]) & homes
        owner_filed = (set(appeals.loc[appeals.filer.eq("O") & ~is_ag, "pid"]) & homes) - agent_filed
        m.update({"homes_A_protested": len(prot_home), "homes_A_protested_by_agent": len(agent_filed),
                  "homes_A_protested_by_owner": len(owner_filed),
                  "homes_A_ptp_protested": appeals[appeals.agent_id.isin(ptp_ids) & appeals.pid.isin(homes)].pid.nunique(),
                  "all_protests": len(appeals), "all_agent_protests": int(is_ag.sum())})

    # segments: seg_agent = agent of record this year OR protest filed by an agent this year
    if agents is not None and appeals is not None:
        seg_ag = ag_home | agent_filed
        seg_own = prot_home - seg_ag
        rest = homes - seg_ag - seg_own
        seg.update({"seg_agent": len(seg_ag), "seg_owner_alone": len(seg_own),
                    "seg_ptp": m["homes_A_ptp_agent"]})
        if history is not None:
            lapsed = rest & set(history)
            seg.update({"seg_lapsed": len(lapsed), "seg_never": len(rest - lapsed)})
        else:
            seg["seg_lapsed_or_never"] = len(rest)
        assert seg["seg_agent"] + seg["seg_owner_alone"] + seg.get("seg_lapsed", 0) + seg.get("seg_never", 0) \
            + seg.get("seg_lapsed_or_never", 0) == len(homes)

    if agents is not None:
        ah = agents[agents.pid.isin(homes)]
        fh = ah.groupby("firm").pid.nunique()
        keep = set(fh[fh >= min_homes].index) | {"Property Tax Protest"}
        # protests filed per firm (agent id on the appeal mapped through the same id->firm table)
        id2firm = dict(zip(agents.agent_id, agents.firm))
        if appeals is not None:
            ap = appeals[appeals.agent_id.ne("")].copy()
            ap["firm"] = ap.agent_id.map(id2firm).fillna("(not in agent list)")
            ap.loc[ap.agent_id.isin(ptp_ids), "firm"] = "Property Tax Protest"
            fp = ap[ap.pid.isin(homes)].groupby("firm").pid.nunique()
        for f in sorted(keep, key=lambda f: -fh.get(f, 0)):
            ids = sorted(set(agents.loc[agents.firm.eq(f), "agent_id"]) | (ptp_ids if f == "Property Tax Protest" else set()), key=lambda x: int(x) if x.isdigit() else 0)
            firms.append({"county": county, "year": year, "firm": f, "agent_ids": ";".join(ids),
                          "homes_A_agent_of_record": int(fh.get(f, 0)),
                          "homes_A_protests_filed": int(fp.get(f, 0)) if appeals is not None else None,
                          "all_accounts_agent_of_rec": agents[agents.firm.eq(f)].pid.nunique()})
        oth = agents[~agents.firm.isin(keep)]
        oth_only = agents.groupby("pid").firm.apply(lambda s: not (set(s) & keep))
        oth_pids = set(oth_only[oth_only].index)
        row = {"county": county, "year": year, "firm": "All other agents", "agent_ids": f"{oth.agent_id.nunique()} IDs",
               "homes_A_agent_of_record": len(oth_pids & homes), "all_accounts_agent_of_rec": len(oth_pids)}
        if appeals is not None:
            ap_o = ap[~ap.firm.isin(keep)]
            row["homes_A_protests_filed"] = ap_o[ap_o.pid.isin(homes)].pid.nunique()
        firms.append(row)
    if appeals is not None:
        firms.append({"county": county, "year": year, "firm": "Owners (self-filed)", "agent_ids": "",
                      "homes_A_protests_filed": len(owner_filed)})
    return m, seg, firms


def write(outdir, markets, segs, firms):
    outdir = Path(outdir)
    for rows, cols, name in [(markets, MARKET_COLS, "market.csv"), (segs, SEG_COLS, "segments.csv"), (firms, FIRM_COLS, "firms.csv")]:
        df = pd.DataFrame(rows, columns=cols)
        for c in df.columns:
            if c not in ("county", "firm", "agent_ids") and not c.startswith("source_") and c != "roll_version_date":
                df[c] = pd.to_numeric(df[c], errors="coerce").round().astype("Int64")
        df.to_csv(outdir / name, index=False, encoding="utf-8")
