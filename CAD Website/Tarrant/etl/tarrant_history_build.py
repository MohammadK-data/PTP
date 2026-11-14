"""Tarrant protest history, one row per account per season (2024, 2025, 2026), for the Year-over-year section.

Sources (CAD Website/Tarrant/Data)
    2024  AgentSummaryData_2024/AgentSummaryData_9_ReviewBoard.txt  every 2024 case (UTF-16, pipe)
          PropertyData_2024.txt                                       2024 roll -> final value when the case has none
          our agency code in this file: 00795 (appellant "PROPERTY TAX PROTEST")
    2025  ORR20261019 ... ARB Info 2025.csv                           every 2025 case (same layout as 2026)
          PropertyData_2025.txt                                       2025 roll -> final value when the case has none
          our agent ID: 1487
    2026  output/tarrant_values_2026.csv                              the scorecard's own rows

Rules (same as 2026)
    One case per account: ours first, then resolved > open > no result > not a protest, then the latest case.
    Notice = the case's notice / initial market value. TAD leaves it blank on about half of 2024-25 cases;
             those accounts count as protests but stay out of rates and dollars (no_value).
    Final  = the case's final market value, else the season's roll value (certified, downloaded Oct 2026).
    "Withdrawn By Joint Motion 41.47(g-1)" is how TAD closes a joint-motion settlement after the season:
             counted as informal (92% of them end below notice).

Output: output/tarrant_history.csv  (year, pid, res, who, firm, path, notice, final, reduction, state)
Run:    .venv/bin/python -I "CAD Website/Tarrant/etl/tarrant_history_build.py"
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tarrant_arb_values_2026 as t  # noqa: E402

DATA, OUT = t.DATA, t.OUT
OURS = {2024: "00795", 2025: "1487"}


def path_hist(status):
    s = status.strip()
    if s == "Withdrawn By Joint Motion 41.47(g-1)" or s.startswith("Joint Motion") or s in {
            "Resolved By Authorized Party", "JOINT MOTION 25.25(h) RESOLVED", "25.25(b) Correction"}:
        return "Informal"
    if s.startswith("Resolved Value") or s in {"Pending Ratification", "Ratified - Final Order Sent",
                                               "Closed By ARB Determination"}:
        return "ARB"
    su = s.upper()
    if su in {"FAILURE TO APPEAR", "DID NOT APPEAR"}:
        return "No-show"
    if su in {"WITHDRAWN", "PROTEST WITHDRAWN", "DISMISSED"} or su.startswith("41.45 (E-1) DENI"):
        return "Withdrawn"
    if su in {"PROTEST SETUP IN ERROR", "FILED UNTIMELY", "PROTEST FILED UNTIMELY", "REFERENCE ONLY ACCOUNT"}:
        return "Not a protest"
    if s == "":
        return "Open"
    return "Open" if any(k in su for k in ("SCHED", "AWAIT", "PENDING", "RESCHEDULE", "TENTATIVE")) else "Other"


RANK = {"Informal": 0, "ARB": 0, "Open": 1, "Other": 1, "No-show": 2, "Withdrawn": 2, "Not a protest": 3}


def roll_values(year):
    r = t.dedup_roll(t.load_roll(DATA / f"PropertyData_{year}.txt"))
    return r.set_index(r.Account_Num.str.lstrip("0"))[["Total_Value", "RP"]].assign(
        Total_Value=lambda d: t.num(d.Total_Value))


def pick(a, ours_mask):
    a = a.assign(our_row=ours_mask, rank=a.path.map(RANK))
    ours = set(a.loc[a.our_row & a["rank"].lt(3), "pid"])
    a["is_ours"] = a.pid.isin(ours)
    a = a[~a.is_ours | a.our_row]
    return a.sort_values(["pid", "rank", "date", "case"], ascending=[True, True, False, False]).drop_duplicates("pid")


def finish(p, year, roll):
    p = p[p.path.ne("Not a protest")].copy()
    p["year"] = year
    p["RP"] = p.pid.map(roll.RP)
    p["res"] = p.RP.eq("R")
    p["final"] = p.final.where(p.final > 0, p.pid.map(roll.Total_Value))
    p.loc[p.path.isin(["No-show", "Withdrawn"]) & p.final.isna(), "final"] = p.notice
    p["reduction"] = p.notice - p.final
    p["state"] = np.select(
        [p.path.eq("Open"), ~(p.notice > 0) | p.final.isna(), p.final > p.notice * 1.25],
        ["open", "no_value", "flag"], default="closed")
    print(year, len(p), "accounts | ours", int(p.who.eq("us").sum()), "|", p.state.value_counts().to_dict(),
          "| no_value by who", p.groupby("who").state.apply(lambda s: round(s.eq("no_value").mean(), 3)).to_dict())
    return p[["year", "pid", "res", "who", "firm", "path", "notice", "final", "reduction", "state"]]


def y2024():
    r = pd.read_csv(DATA / "AgentSummaryData_2024/AgentSummaryData_9_ReviewBoard.txt", sep="|", encoding="utf-16",
                    dtype=str, keep_default_na=False)
    r.columns = [c.strip() for c in r.columns]
    r = r.apply(lambda s: s.str.strip())
    r = r[r.Year.eq("2024")]
    a = pd.DataFrame({"pid": r.AccountNumber.str.lstrip("0"), "case": r.CaseNumber, "date": r.HearingDateTime,
                      "path": r.CaseStatus.map(path_hist), "agency": r.Agency, "name": r.Appellant,
                      "notice": t.num(r.InitialValue), "final": t.num(r.FinalValue)})
    p = pick(a, a.agency.eq(OURS[2024]))
    p["who"] = np.where(p.is_ours, "us", np.where(p.agency.ne(""), "agent", "owner"))
    p["firm"] = np.where(p.who.eq("agent"), p.name, "")
    return finish(p, 2024, roll_values(2024))


def y2025():
    r = pd.read_csv(DATA / "ORR20261019 - Avetik Ghazaryan - ARB Info 2025.csv", dtype=str, keep_default_na=False)
    r = r.drop_duplicates()
    a = pd.DataFrame({"pid": r.pID.str.lstrip("0"), "case": t.num(r.CaseNumber), "date": r.finalizedDt,
                      "path": r.CaseStatus.map(path_hist), "agent": r.agentID, "type": r.AppellantType,
                      "name": r.AppellantName, "notice": t.num(r.NoticeMarketValue), "final": t.num(r.finalMarketValue)})
    p = pick(a, a.agent.eq(OURS[2025]))
    p["who"] = np.where(p.is_ours, "us", np.where(p.type.eq("Agent"), "agent", np.where(p.type.eq("Owner"), "owner", "other")))
    p["firm"] = np.where(p.who.eq("agent"), p.name, "")
    return finish(p, 2025, roll_values(2025))


def y2026():
    v = pd.read_csv(OUT / "tarrant_values_2026.csv", dtype=str, keep_default_na=False)
    v = v[v.protested.eq("True")]
    pmap = {"Informal (joint motion)": "Informal", "ARB hearing": "ARB", "Failure to appear": "No-show",
            "Withdrawn / dismissed": "Withdrawn", "Open": "Open"}
    p = pd.DataFrame({"year": 2026, "pid": v.Account_Num.str.lstrip("0"), "res": v.RP.eq("R"),
                      "who": np.where(v.is_ours.eq("True"), "us", np.where(v.AppellantType.eq("Agent"), "agent",
                                      np.where(v.AppellantType.eq("Owner"), "owner", "other"))),
                      "path": v.path.map(pmap).fillna("Other"),
                      "notice": t.num(v.notice_value), "final": t.num(v.final_value)})
    p["firm"] = np.where(p.who.eq("agent"), v.AppellantName, "")
    p["reduction"] = p.notice - p.final
    p["state"] = np.select([p.path.eq("Open"), v.check_values.eq("True").values], ["open", "flag"], default="closed")
    print(2026, len(p), "accounts | ours", int(p.who.eq("us").sum()), p.state.value_counts().to_dict())
    return p


if __name__ == "__main__":
    h = pd.concat([y2024(), y2025(), y2026()], ignore_index=True)
    h.to_csv(OUT / "tarrant_history.csv", index=False)
    print("wrote", OUT / "tarrant_history.csv", len(h))
