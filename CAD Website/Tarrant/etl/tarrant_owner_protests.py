"""Tarrant: accounts protested by the owner (no agent), with notice and final market value, 2024-2026.

One row per account per season, the case that decided the value (same pick as tarrant_history_build.py:
ours first, then resolved > open > no result > not a protest, then the latest case). Kept when that case
was filed by the owner:
    2024  AgentSummaryData_2024/..._9_ReviewBoard.txt, Agency blank
    2025  ORR ... ARB Info 2025.csv, AppellantType = Owner
    2026  output/tarrant_values_2026.csv, AppellantType = Owner
Cases that are not a real protest (setup in error, filed untimely) are dropped.

Values
    notice_value  the case's notice / initial market value; when TAD left it blank (half of 2025 cases),
                  NoticeValue from that year's PropertyDataSupplemental_{R,C,M,P} file  -> notice_source
    final_value   2024-25: certified roll Total_Value (the ARB file's finalMarketValue disagrees with the
                  roll on ~4.5% of 2025 cases and is off by 50%+ on many; appraisedValue matches the roll 98%);
                  ARB final only when the account is missing from the roll -> final_source.
                  2026: ARB finalMarketValue (the 2026 roll is not certified yet).
                  arb_final_value keeps the ARB file's own final value for reference.
    value_check   final is more than 25% above notice or less than a quarter of it: a notice value
                  that is likely partial or wrong (common in the 2025 ARB file); check before using
                  open cases: blank

Output: output/tarrant_owner_protests_2024_2026.csv
Run:    .venv/bin/python -I "CAD Website/Tarrant/etl/tarrant_owner_protests.py"
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tarrant_arb_values_2026 as t  # noqa: E402
import tarrant_history_build as h  # noqa: E402

DATA, OUT = t.DATA, t.OUT
COLS = ["year", "Account_Num", "RP", "Property_Class", "Situs_Address", "Owner_Name", "AppellantName",
        "CaseNumber", "CaseStatus", "path", "outcome", "notice_value", "final_value", "reduction",
        "reduction_pct", "value_check", "notice_source", "final_source", "arb_final_value", "finalizedDt"]


def roll(year):
    r = t.dedup_roll(t.load_roll(DATA / f"PropertyData_{year}.txt"))
    r = r.set_index(r.Account_Num.str.lstrip("0"))
    return r[["RP", "Property_Class", "Situs_Address", "Owner_Name"]].assign(roll_value=t.num(r.Total_Value))


def supp_notice(year):
    parts = []
    for rp in "RCMP":
        f = DATA / f"PropertyDataSupplemental_{rp}_{year}.txt"
        if f.read_bytes()[:2] == b"\xff\xfe":                        # C files are UTF-16
            s = pd.read_csv(f, sep="|", encoding="utf-16", dtype=str, keep_default_na=False,
                            usecols=["AccountNumber", "NoticeValue"]).apply(lambda c: c.str.strip())
        else:
            s = t.load_roll(f)
        parts.append(pd.Series(t.num(s.NoticeValue).values, index=s.AccountNumber.str.lstrip("0")))
    s = pd.concat(parts)
    return s[s > 0].groupby(level=0).max()


def cases(year):
    if year == 2024:
        r = pd.read_csv(DATA / "AgentSummaryData_2024/AgentSummaryData_9_ReviewBoard.txt", sep="|",
                        encoding="utf-16", dtype=str, keep_default_na=False)
        r.columns = [c.strip() for c in r.columns]
        r = r.apply(lambda s: s.str.strip())
        r = r[r.Year.eq("2024")]
        a = pd.DataFrame({"pid": r.AccountNumber.str.lstrip("0"), "case": r.CaseNumber, "date": r.HearingDateTime,
                          "status": r.CaseStatus, "name": r.Appellant, "notice": t.num(r.InitialValue),
                          "final": t.num(r.FinalValue), "owner": r.Agency.eq("")})
        ours = r.Agency.eq(h.OURS[2024])
    else:
        r = pd.read_csv(DATA / f"ORR20261019 - Avetik Ghazaryan - ARB Info {year}.csv", dtype=str,
                        keep_default_na=False).drop_duplicates()
        a = pd.DataFrame({"pid": r.pID.str.lstrip("0"), "case": t.num(r.CaseNumber), "date": r.finalizedDt,
                          "status": r.CaseStatus, "name": r.AppellantName, "notice": t.num(r.NoticeMarketValue),
                          "final": t.num(r.finalMarketValue), "owner": r.AppellantType.eq("Owner")})
        ours = r.agentID.eq(h.OURS[year])
    a["path"] = a.status.map(h.path_hist)
    p = h.pick(a, ours.values)
    return p[p.owner & ~p.is_ours & p.path.ne("Not a protest")]


def season(year):
    p, rl, sn = cases(year), roll(year), supp_notice(year)
    o = pd.DataFrame({"year": year, "Account_Num": p.pid, "AppellantName": p.name, "CaseNumber": p.case,
                      "CaseStatus": p.status, "path": p.path, "finalizedDt": p.date})
    o = o.join(rl, on="Account_Num")
    o["notice_value"] = p.notice.where(p.notice > 0)
    o["notice_source"] = np.where(o.notice_value.notna(), "ARB", "")
    fill = o.notice_value.isna()
    o.loc[fill, "notice_value"] = o.loc[fill, "Account_Num"].map(sn)
    o.loc[fill & o.notice_value.notna(), "notice_source"] = "supplemental"
    o["arb_final_value"] = p.final.where(p.final > 0)
    o["final_value"] = o.roll_value.where(o.roll_value > 0)
    o["final_source"] = np.where(o.final_value.notna(), "roll", "")
    fill = o.final_value.isna()
    o.loc[fill, "final_value"] = o.loc[fill, "arb_final_value"]
    o.loc[fill & o.final_value.notna(), "final_source"] = "ARB"
    o.loc[o.path.eq("Open"), ["final_value", "final_source"]] = [np.nan, ""]
    return o


def y2026():
    v = pd.read_csv(OUT / "tarrant_values_2026.csv", dtype=str, low_memory=False)
    v = v[v.AppellantType.eq("Owner") & ~v.outcome.str.startswith("Not a protest")]
    pmap = {"Informal (joint motion)": "Informal", "ARB hearing": "ARB", "Failure to appear": "No-show",
            "Withdrawn / dismissed": "Withdrawn", "Open": "Open"}
    o = pd.DataFrame({"year": 2026, "Account_Num": v.Account_Num.str.lstrip("0"), "RP": v.RP,
                      "Property_Class": v.Property_Class, "Situs_Address": v.Situs_Address,
                      "Owner_Name": v.Owner_Name, "AppellantName": v.AppellantName, "CaseNumber": v.CaseNumber,
                      "CaseStatus": v.CaseStatus, "path": v.path.map(pmap).fillna("Other"),
                      "finalizedDt": v.finalizedDt, "notice_value": t.num(v.notice_value),
                      "final_value": t.num(v.final_value), "arb_final_value": t.num(v.final_value), "notice_source": "ARB", "final_source": "ARB"})
    o.loc[o.path.eq("Open"), ["final_value", "final_source"]] = [np.nan, ""]
    return o


if __name__ == "__main__":
    o = pd.concat([season(2024), season(2025), y2026()], ignore_index=True)
    o.loc[o.notice_value.le(0), "notice_value"] = np.nan          # mobile homes: TAD sends 0
    o["reduction"] = o.notice_value - o.final_value
    o["reduction_pct"] = (o.reduction / o.notice_value).round(4)
    o["value_check"] = (o.final_value > o.notice_value * 1.25) | (o.final_value < o.notice_value * 0.25)
    o["outcome"] = np.select(
        [o.path.eq("Open"), o.notice_value.isna() | o.final_value.isna(), o.reduction > 0, o.reduction < 0],
        ["Open", "No value", "Reduced", "Increased"], default="No change")
    o = o[COLS].sort_values(["year", "RP", "reduction"], ascending=[False, True, False])
    o.to_csv(OUT / "tarrant_owner_protests_2024_2026.csv", index=False)
    print(o.groupby("year").size())
    print(o.groupby(["year", "outcome"]).size().unstack(fill_value=0))
    print(o.groupby(["year", "notice_source"]).size().unstack(fill_value=0))
    print(o.groupby(["year", "final_source"]).size().unstack(fill_value=0))
    print(o.groupby("year").value_check.sum())
    c = o[o.outcome.isin(["Reduced", "Increased", "No change"]) & ~o.value_check]
    print(c.groupby("year")[["notice_value", "final_value", "reduction"]].sum().assign(
        pct=lambda d: d.reduction / d.notice_value))
