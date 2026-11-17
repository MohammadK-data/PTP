"""Team hand-off package: one folder per county (Bexar, Travis, Rockwall) under Market Analysis/output/team_share/.

Per county:
  agent_win_rates_<c>.csv        year x filer (firm or "Owners (self-filed)") x property group: protests, outcomes, win rate
  agent_share_<c>.csv            firm share (agent of record + protests filed), copied from the market-analysis outputs
  owner_protests_<c>.csv         every owner-filed protest with notice/final value and outcome (no owner names/addresses)
  owners_alone_no_cut_<c>.csv    owner-filed protests that closed with no reduction
  switching_<c>.csv              filer per account, year to year (Travis: within 2026 only, see README)
  switching_summary_<c>.csv      from -> to counts

Win = closed with final market value below notice market value. Denominator = closed protests with both values
(withdrawn and no-show count as losses; open and "No value" are left out).
No owner names, appellant names, situs/mailing addresses, appraiser or panel names are written.

Run: /Users/user2/PTP/.venv/bin/python -I "Market Analysis/etl/team_share_2026.py"
"""
import importlib.util
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/Users/user2/PTP")
MA = ROOT / "Market Analysis"
OUT = MA / "output" / "team_share"
sys.path.insert(0, str(MA / "etl"))
OWN = "Owners (self-filed)"


def win_rates(p):
    """p: year, filer, home(bool), path, outcome, notice_value, final_value -> one row per year/filer/group."""
    rows = []
    for grp, d in [("All property", p), ("A homes", p[p.home])]:
        for (y, f), g in d.groupby(["year", "filer"]):
            closed = g[~g.outcome.isin(["Open", "No value"])]
            red = closed[closed.outcome.eq("Reduced")]
            rows.append(dict(
                year=y, filer=f, filer_type="Owner" if f == OWN else "Agent", property_group=grp,
                protests=len(g), accounts=g.account.nunique(), closed_with_values=len(closed),
                reduced=len(red), no_change=int(closed.outcome.eq("No change").sum()),
                increased=int(closed.outcome.eq("Increased").sum()),
                of_which_no_show=int(closed.path.eq("No-show").sum()),
                of_which_withdrawn=int(closed.path.eq("Withdrawn").sum()),
                open=int(g.outcome.eq("Open").sum()), no_value=int(g.outcome.eq("No value").sum()),
                win_rate=round(len(red) / len(closed), 4) if len(closed) else np.nan,
                total_reduction=float((red.notice_value - red.final_value).sum()),
                median_reduction_pct_when_won=round(float(((red.notice_value - red.final_value)
                                                           / red.notice_value).median()), 4) if len(red) else np.nan))
    w = pd.DataFrame(rows)
    return w.sort_values(["property_group", "year", "protests"], ascending=[True, True, False])


def outcome_of(open_, nv, fv):
    return np.select([open_, nv.isna() | fv.isna() | nv.le(0) | fv.le(0), fv < nv, fv > nv],
                     ["Open", "No value", "Reduced", "Increased"], default="No change")


def switching_summary(sw):
    s = sw.groupby(["from_year", "to_year", "filer_from", "filer_to"]).size().rename("accounts").reset_index()
    s["switched"] = s.filer_from.ne(s.filer_to)
    return s.sort_values(["from_year", "accounts"], ascending=[True, False])


def full_share(county, rec, filed, homes):
    """Every firm, 2026. rec: (account, agent_id, agent_name, firm) agent of record; filed: protests (account, filer)."""
    rows = []
    fa = filed[filed.filer.ne(OWN)]
    for f, g in rec.groupby("firm"):
        rows.append(dict(county=county, year=2026, firm=f, agent_ids=";".join(sorted(set(g.agent_id))),
                         agent_names=" | ".join(sorted(set(g.agent_name)))[:300],
                         homes_A_agent_of_record=g.loc[g.account.isin(homes), "account"].nunique(),
                         all_accounts_agent_of_record=g.account.nunique()))
    s = pd.DataFrame(rows)
    pf = (fa[fa.account.isin(homes)].groupby("filer").account.nunique()
          .rename("homes_A_protests_filed").rename_axis("firm").reset_index())
    s = s.merge(pf, on="firm", how="outer")
    s["county"], s["year"] = county, 2026
    own = filed.loc[filed.filer.eq(OWN) & filed.account.isin(homes), "account"]
    own = own[~own.isin(fa.account)].nunique()
    s = pd.concat([s, pd.DataFrame([dict(county=county, year=2026, firm=OWN, homes_A_protests_filed=own)])])
    tot = s.homes_A_protests_filed.sum()
    s["share_of_home_protests"] = (s.homes_A_protests_filed / tot).round(4)
    cols = ["county", "year", "firm", "agent_ids", "agent_names", "homes_A_agent_of_record",
            "all_accounts_agent_of_record", "homes_A_protests_filed", "share_of_home_protests"]
    return s[cols].sort_values("homes_A_protests_filed", ascending=False, na_position="last")


def owner_no_cut(o):
    return o[o.outcome.isin(["No change", "Increased"])]


def save(df, county, name):
    d = OUT / county
    d.mkdir(parents=True, exist_ok=True)
    df.to_csv(d / f"{name}_{county.lower()}.csv", index=False)
    print(f"  {county}/{name}: {len(df):,} rows")


def firm_share(county, src):
    f = pd.read_csv(src, dtype=str, keep_default_na=False)
    return f[f.county.eq(county)]


# ------------------------------------------------------------------ Bexar
def bexar():
    print("Bexar")
    INF = {"VA", "EVA", "VANC", "VASP", "EA", "PFVA", "TOPLN", "ETOPLN", "ADR-PRE", "SOAH-PRE"}
    ARB = {"ORD.A", "ORD.A-BULK", "ORD.D", "ORD.D-BULK", "CG", "FULL", "ORD-NJ", "ORD-NON", "ORD-11.43D", "ORD.E", "ORD.ED"}
    NS, WD = {"PFNS", "PFNSW"}, {"PFWD", "EWD"}
    from firm_names_dfw import firm_of
    p = pd.read_csv(ROOT / "CAD Website/Bexar/output/bexar_arb_2022_2026.csv.gz", dtype=str, keep_default_na=False,
                    usecols=["prop_id", "year", "case_id", "state_cd", "agent_name", "prot_type", "prot_status",
                             "prot_by_type", "begin_market", "final_market"])
    p = p[p.prot_by_type.isin(["AG", "OW"]) & ~p.prot_type.isin({"LIT", "ADR", "SOAH"}) & p.prot_status.ne("DELDUP")
          & p.year.isin(["2024", "2025", "2026"])].copy()
    p["year"] = p.year.astype(int)
    p["account"] = p.prop_id.str.strip().str.lstrip("0")
    p["home"] = p.state_cd.str.strip().str.upper().str.startswith("A")
    is_ag = p.prot_by_type.eq("AG") | p.agent_name.str.strip().ne("")
    p["filer"] = [firm_of(n) if a else OWN for n, a in zip(p.agent_name, is_ag)]
    p.loc[is_ag & p.agent_name.str.strip().eq(""), "filer"] = "(agent, name blank)"
    s = p.prot_status
    p["path"] = np.select([s.isin(INF), s.isin(ARB), s.isin(NS), s.isin(WD)],
                          ["Informal", "ARB", "No-show", "Withdrawn"], default="Open")
    p["notice_value"] = pd.to_numeric(p.begin_market, errors="coerce")
    p["final_value"] = pd.to_numeric(p.final_market, errors="coerce")
    p["outcome"] = outcome_of(p.path.eq("Open"), p.notice_value, p.final_value)
    save(win_rates(p), "Bexar", "agent_win_rates")
    save(firm_share("Bexar", MA / "output/bexar/firm_share.csv"), "Bexar", "agent_share")
    o = pd.read_csv(MA / "output/bexar/owner_protests_bexar_2024_2026.csv", dtype=str, keep_default_na=False)
    save(o, "Bexar", "owner_protests")
    save(owner_no_cut(o), "Bexar", "owners_alone_no_cut")
    sw = pd.read_csv(MA / "output/bexar/switching_bexar.csv", dtype=str, keep_default_na=False)
    save(sw, "Bexar", "switching")
    save(switching_summary(sw), "Bexar", "switching_summary")


# ------------------------------------------------------------------ Travis
def travis():
    print("Travis")
    from travis_montgomery_market import firm_of, load_cert
    PTP_IDS = {"1863738", "1328537"}
    roll = load_cert(MA / "work/travis/info_2026_cert.csv.gz")
    homes = set(roll.loc[roll.cat.eq("A"), "prop_id"])
    ag = pd.read_csv(MA / "work/travis/travis_agents_2026.csv.gz", dtype=str, keep_default_na=False)
    ag["agentID"] = ag.agentID.str.replace(r"\.0$", "", regex=True)
    id2name = dict(zip(ag.agentID, ag.name))
    fid = lambda a: "Property Tax Protest" if a in PTP_IDS else firm_of(id2name.get(a, f"Agent {a}"))

    a = pd.read_csv(ROOT / "CAD Website/Travis/output/travis_appeals_2026.csv.gz", dtype=str, keep_default_na=False,
                    usecols=["pID", "appealID", "appealType", "appealStatus", "appealedByType", "appealedByAgentID",
                             "valueDecisionAdjustmentType", "initialMarketValue", "finalMarketValue", "finalized",
                             "finalizedDt"])
    a = a[a.appealType.eq("P") & a.appealedByType.isin(["A", "O"])].copy()
    a["year"] = 2026
    a["account"] = a.pID
    a["home"] = a.pID.isin(homes)
    a["aid"] = a.appealedByAgentID.str.replace(r"\.0$", "", regex=True)
    a["filer"] = np.where(a.appealedByType.eq("A"), [fid(x) if x else "(agent, no ID)" for x in a.aid], OWN)
    st, vt, fin = a.appealStatus.str.strip(), a.valueDecisionAdjustmentType, a.finalized.eq("1")
    a["path"] = np.select([~fin, st.eq("FTA"), st.isin(["W", "EF_WD", "WD", "D", "LD"]), vt.eq("F"), vt.eq("I"),
                           st.str.startswith("ORD")],
                          ["Open", "No-show", "Withdrawn", "ARB", "Informal", "ARB"], default="Other closed")
    a["notice_value"] = pd.to_numeric(a.initialMarketValue, errors="coerce")
    a["final_value"] = pd.to_numeric(a.finalMarketValue, errors="coerce")
    a["outcome"] = outcome_of(~fin, a.notice_value, a.final_value)
    save(win_rates(a), "Travis", "agent_win_rates")
    ag["eff"] = pd.to_datetime(ag.effectiveDt, errors="coerce")
    ag["exp"] = pd.to_datetime(ag.expirationDt, errors="coerce")
    ag["firm"] = [fid(x) for x in ag.agentID]
    t = pd.Timestamp("2026-05-15")  # protest deadline: agent of record = appointment active that day
    rec = ag[(ag.eff.isna() | (ag.eff <= t)) & (ag.exp.isna() | (ag.exp >= t))]
    rec = rec.rename(columns={"pID": "account", "agentID": "agent_id", "name": "agent_name"})
    save(full_share("Travis", rec[["account", "agent_id", "agent_name", "firm"]], a, homes), "Travis", "agent_share")

    cls = roll.set_index("prop_id")
    sc = cls.imprv_state_cd.where(cls.imprv_state_cd.ne(""), cls.land_state_cd)
    o = a[a.filer.eq(OWN)].copy()
    o = pd.DataFrame({"year": 2026, "Account_Num": o.pID, "RP": "", "Property_Class": o.pID.map(sc),
                      "CaseNumber": o.appealID, "CaseStatus": o.appealStatus.str.strip(), "path": o.path,
                      "outcome": o.outcome, "notice_value": o.notice_value, "final_value": o.final_value,
                      "reduction": o.notice_value - o.final_value,
                      "reduction_pct": ((o.notice_value - o.final_value) / o.notice_value * 100).round(2),
                      "notice_source": "initialMarketValue", "final_source": "finalMarketValue",
                      "finalizedDt": o.finalizedDt})
    o["RP"] = o.Account_Num.map(cls.prop_type_cd) if "prop_type_cd" in cls else ""
    save(o, "Travis", "owner_protests")
    save(owner_no_cut(o), "Travis", "owners_alone_no_cut")

    # switching: no 2024/2025 agent data exists, so compare agent of record on 2026-01-01 vs at the Oct 6 2026 export
    def on(day):
        t = pd.Timestamp(day)
        x = ag[(ag.eff.isna() | (ag.eff <= t)) & (ag.exp.isna() | (ag.exp > t))]
        return x.sort_values("eff").groupby("pID").firm.last()
    j, n = on("2026-01-01"), on("2026-10-06")
    filed = a.sort_values("finalizedDt").groupby("pID").filer.last()
    ids = sorted((set(j.index) | set(n.index)) & homes, key=int)
    sw = pd.DataFrame({"county": "Travis", "from_year": "2026-01-01", "to_year": "2026-10-06", "Account_Num": ids,
                       "filer_from": j.reindex(ids).fillna("(no agent)").values,
                       "filer_to": n.reindex(ids).fillna("(no agent)").values,
                       "filed_2026_protest": filed.reindex(ids).fillna("(no protest)").values,
                       "basis": "agent_of_record_within_2026"})
    save(sw, "Travis", "switching")
    save(switching_summary(sw), "Travis", "switching_summary")


# ------------------------------------------------------------------ Rockwall
def rockwall():
    print("Rockwall")
    spec = importlib.util.spec_from_file_location("rr", MA / "output/round2/Rockwall/rockwall_round2.py")
    rr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rr)
    rm = rr.rm
    arb = rr.arb_rows(2026)
    arb["order"] = arb.export.map({"2026-03-16": 0, "2026-05-26": 1, "2026-07-13": 2, "2026-10-09": 3})
    d26 = rr.agents(2026)
    nm = rm.load(("csv", "2026-05-26"), "APPRAISAL_AGENT")
    id2name = dict(zip(nm.agent_id.str.lstrip("0"), nm.agent_name))
    arb_aid = d26.arb_agent_id.str.lstrip("0")
    last = arb.sort_values(["pid", "order"]).drop_duplicates("pid", keep="last").copy()
    # filer: ARB agent on the account in the May 26 export (else agent of record) when agent-filed, else owner
    agent_filed = set(arb.pid[arb.arb_status.str.startswith("O-AGT")]) | set(d26.index[arb_aid.ne("")])
    from firm_names_dfw import firm_of

    def filer(pid):
        if pid not in agent_filed:
            return OWN
        x = arb_aid.get(pid, "")
        if x:
            return firm_of(id2name.get(x, ""), x, rm.PTP_IDS)
        return d26.firm.get(pid) or "(agent, not identified)"
    last["filer"] = [filer(x) for x in last.pid]
    roll = rm.roll_of(rm.load(("csv", "2026-10-09"), "APPRAISAL_INFO")).set_index("pid")
    last["home"] = last.pid.map(roll.sc).fillna("").str.upper().str.startswith("A")
    still_open = last.export.eq("2026-10-09")
    wd = last.arb_status.str.upper().str.match(r"^(WD|W-)|.*-W$|.*-WO$")
    last["path"] = np.select([still_open, wd], ["Open", "Withdrawn"], default="Closed (path not published)")
    last["notice_value"] = last.pid.map(rr.market("2026-05-26"))
    last["final_value"] = last.pid.map(rr.market("2026-10-09"))
    last["outcome"] = outcome_of(still_open, last.notice_value, last.final_value)
    last["year"], last["account"] = 2026, last.pid
    save(win_rates(last), "Rockwall", "agent_win_rates")
    rec = d26[d26.aid.ne("")].reset_index()
    rec = pd.DataFrame({"account": rec.pid, "agent_id": rec.aid, "agent_name": rec.aid.map(id2name).fillna(""),
                        "firm": rec.firm})
    homes = set(roll.index[roll.sc.fillna("").str.upper().str.startswith("A")])
    save(full_share("Rockwall", rec, last, homes), "Rockwall", "agent_share")
    prior = firm_share("Rockwall", MA / "output/firm_share.csv")
    save(prior[prior.year.ne("2026")], "Rockwall", "agent_share_2024_2025_top_firms")
    o = pd.read_csv(MA / "output/round2/Rockwall/owner_protests_rockwall_2026.csv", dtype=str, keep_default_na=False)
    save(o, "Rockwall", "owner_protests")
    save(owner_no_cut(o), "Rockwall", "owners_alone_no_cut")
    sw = pd.read_csv(MA / "output/round2/Rockwall/switching_rockwall.csv", dtype=str, keep_default_na=False)
    save(sw, "Rockwall", "switching")
    save(switching_summary(sw), "Rockwall", "switching_summary")


if __name__ == "__main__":
    if OUT.exists():
        shutil.rmtree(OUT)
    for fn in (bexar, travis, rockwall):
        fn()
