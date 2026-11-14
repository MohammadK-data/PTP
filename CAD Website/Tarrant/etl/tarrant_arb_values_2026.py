"""Tarrant 2026: one row per account, with notice / first / final value and how the protest went.

Inputs (CAD Website/Tarrant/Data):
    PropertyData(Delimited)_2026.txt          full 2026 roll, all property types (agent portal download)
    PropertyData(Delimited)_R_2026.txt        newer residential-only roll (Nov 11) -> cross-check of final value
    PropertyData_2025.txt                     2025 roll -> prior-year value
    ORR20261019 - ... ARB Info 2026.csv       every 2026 protest case (open records request, Oct 19)
    2026-11-13T12-39_export.csv               agent portal export (first 10,000 rows of the 2026 roll) -> check

Outputs (CAD Website/Tarrant/output):
    tarrant_property_2026_dedup.csv           roll, one row per Account_Num
    tarrant_arb_2026_dedup.csv                ARB, one row per pID (the case that decided the value)
    tarrant_values_2026.csv                   one row per account: values, reduction, outcome, ours flag
    tarrant_values_2026_summary.csv           how the season went, us vs. everyone else

Rules
-----
Roll duplicates: the same account appears 2-5 times when it has several deed instruments; every other
column is identical. Keep the row with the latest Instrument_No (deed book/page come with it).

ARB duplicates: TAD lists one case once per agent on the account, so a case shared by us and another
firm shows up twice with the same CaseNumber and values; some accounts also have extra cases
(set up in error, withdrawn, re-filed). One row per pID is picked:
    1. ours: if any non-error case lists agentID 1487 (Property Tax Protest), the account is ours
       and only our rows are candidates.
    2. by status: resolved > still open > closed without a result (FTA, withdrawn, dismissed)
       > not a real protest (setup in error, filed untimely).
    3. ties: latest finalizedDt, then latest ProtestFilingDate, then highest CaseNumber.

Values
    prior_year_value   2025 roll Total_Value (market)
    notice_value       ARB NoticeMarketValue = value on the 2026 notice (first 2026 value)
                       not protested: 2026 roll Total_Value (no change)
    owner_net_value    ARB ownerNetAppraisedValue (equals final_value 95% of the time; NOT the owner's ask)
    final_value        ARB finalMarketValue (case resolved); open case -> notice_value
    roll_value_oct     Total_Value in the full 2026 roll file
    roll_value_nov     Total_Value in the Nov residential roll (R only) -> should equal final_value

Run:  .venv/bin/python "CAD Website/Tarrant/etl/tarrant_arb_values_2026.py"
"""

from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "Data"
OUT = HERE.parent / "output"
OUT.mkdir(exist_ok=True)

ROLL = DATA / "PropertyData(Delimited)_2026.txt"
ROLL_R = DATA / "PropertyData(Delimited)_R_2026.txt"
ROLL_2025 = DATA / "PropertyData_2025.txt"
ARB = DATA / "ORR20261019 - Avetik Ghazaryan - ARB Info 2026.csv"
PORTAL_EXPORT = DATA / "2026-11-13T12-39_export.csv"
OUR_AGENT_ID = "1487"

RESOLVED = {
    "Joint Motion 41.47(g-1) - Filed", "Joint Motion 41.47(g-1) - Agreed Order Sent", "Resolved Value",
    "Resolved Value - Hearing Agreement", "Pending Ratification", "Ratified - Final Order Sent",
    "Resolved By Authorized Party", "JOINT MOTION 25.25(h) RESOLVED", "25.25(b) Correction",
}
OPEN = {
    "ARB HEARING SCHEDULED", "AWAITING SCHED", "RESCHEDULE GRANTED", "RESCHEDULE REQUESTED",
    "PENDING CONTINGENCY", "Pending QC", "Pending QC JM", "41.45 (e-1) Granted -Scheduled",
}
NO_RESULT = {
    "FAILURE TO APPEAR", "WITHDRAWN", "Withdrawn By Joint Motion 41.47(g-1)", "DISMISSED",
    "41.45 (e-1) Denial Sent", "41.45 (e-1) Denied",
}
NOT_PROTEST = {"Protest Setup in Error", "Filed Untimely"}
STATUS_RANK = {**{s: 0 for s in RESOLVED}, **{s: 1 for s in OPEN}, **{s: 2 for s in NO_RESULT},
               **{s: 3 for s in NOT_PROTEST}}


def path_of(status):
    """How the value was settled."""
    if status.startswith("Joint Motion") or status in {"Resolved By Authorized Party", "JOINT MOTION 25.25(h) RESOLVED", "25.25(b) Correction"}:
        return "Informal (joint motion)"
    if status.startswith("Resolved Value") or status in {"Pending Ratification", "Ratified - Final Order Sent"}:
        return "ARB hearing"
    if status in OPEN:
        return "Open"
    if status in NO_RESULT:
        return "Failure to appear" if status == "FAILURE TO APPEAR" else "Withdrawn / dismissed"
    if status in NOT_PROTEST:
        return "Not a protest"
    return "Other"


# ---------------------------------------------------------------- roll

def load_roll(path):
    """TAD pipe file. A few rows carry a ' | ' inside a text field (e.g. PIDN 'P | BPP');
    those pieces are joined back so every row has the header's column count."""
    with open(path, encoding="latin-1") as f:
        hdr = [h.strip() for h in f.readline().rstrip("\r\n").split("|")]
        n, rows, repaired = len(hdr), [], 0
        for line in f:
            parts = line.rstrip("\r\n").split("|")
            if len(parts) != n:
                repaired += 1
                extra = len(parts) - n
                for j in range(len(parts) - 1):
                    if extra > 0 and parts[j].endswith(" ") and parts[j + 1].startswith(" "):
                        parts[j:j + extra + 1] = ["|".join(parts[j:j + extra + 1])]
                        break
                parts = (parts + [""] * n)[:n]
            rows.append(parts)
    df = pd.DataFrame(rows, columns=hdr)
    for c in df.columns:
        df[c] = df[c].str.strip()
    print(f"{path.name}: {len(df):,} rows, {repaired} repaired")
    return df


def dedup_roll(df):
    df = df.copy()
    df["_n"] = df.groupby("Account_Num")["Account_Num"].transform("size")
    df = df.sort_values(["Account_Num", "Instrument_No"], ascending=[True, False], kind="stable")
    out = df.drop_duplicates("Account_Num").rename(columns={"_n": "rows_in_file"})
    print(f"  -> {len(out):,} accounts ({(out.rows_in_file > 1).sum():,} had duplicate rows)")
    return out


def num(s):
    return pd.to_numeric(s, errors="coerce")


# ---------------------------------------------------------------- ARB

def dedup_arb(a):
    a = a.copy()
    a["is_our_row"] = a["agentID"].eq(OUR_AGENT_ID)
    a["status_rank"] = a["CaseStatus"].map(STATUS_RANK).fillna(2)
    ours_pids = set(a.loc[a.is_our_row & (a.status_rank < 3), "pID"])
    a["is_ours"] = a["pID"].isin(ours_pids)

    g = a.groupby("pID")
    a["cases_on_account"] = g["CaseNumber"].transform("nunique")
    a["rows_on_account"] = g["pID"].transform("size")
    # every agent on the account's cases, and every agent sharing the picked case
    agents = a.dropna(subset=["agentID"]).assign(nm=lambda d: d.AppellantName.fillna("") + " (" + d.agentID + ")")
    all_agents = agents.groupby("pID")["nm"].agg(lambda s: " | ".join(sorted(set(s))))
    case_agents = agents.groupby(["pID", "CaseNumber"])["nm"].agg(lambda s: " | ".join(sorted(set(s))))

    cand = a[~a.is_ours | a.is_our_row]           # ours -> only our rows compete
    cand = cand.assign(CaseNumber_n=num(cand.CaseNumber)).sort_values(
        ["pID", "status_rank", "finalizedDt", "ProtestFilingDate", "CaseNumber_n"],
        ascending=[True, True, False, False, False], na_position="last", kind="stable",
    )
    pick = cand.drop_duplicates("pID").drop(columns=["CaseNumber_n"]).copy()
    pick["agents_on_account"] = pick["pID"].map(all_agents)
    pick["agents_on_case"] = [case_agents.get((p, c), "") for p, c in zip(pick.pID, pick.CaseNumber)]
    pick["shared_with_other_agent"] = pick.is_ours & pick.agents_on_case.str.contains(r"\((?!1487\))", regex=True)
    pick["path"] = pick["CaseStatus"].map(path_of)
    print(f"ARB: {len(a):,} rows -> {len(pick):,} accounts; ours {pick.is_ours.sum():,}")
    return pick


# ---------------------------------------------------------------- build

def main():
    roll = dedup_roll(load_roll(ROLL))
    roll_r = dedup_roll(load_roll(ROLL_R))
    roll_25 = dedup_roll(load_roll(ROLL_2025))

    # check against the agent portal export: same data as the roll file
    exp = pd.read_csv(PORTAL_EXPORT, dtype=str, keep_default_na=False).iloc[:, 1:]
    exp = exp.apply(lambda s: s.str.strip())
    chk = dedup_roll(exp).merge(roll, on="Account_Num", suffixes=("_e", ""))
    cols = [c for c in exp.columns if c not in ("Account_Num", "Instrument_No", "Deed_Book", "Deed_Page")]
    bad = {c: int((chk[c + "_e"] != chk[c]).sum()) for c in cols if (chk[c + "_e"] != chk[c]).any()}
    print(f"Portal export check: {len(chk):,} of {exp.Account_Num.nunique():,} accounts matched; columns that differ: {bad or 'none'}")

    roll.drop(columns=[]).to_csv(OUT / "tarrant_property_2026_dedup.csv", index=False)

    arb_raw = pd.read_csv(ARB, dtype=str)
    arb_raw = arb_raw.drop_duplicates()                 # 301 fully identical rows
    arb = dedup_arb(arb_raw)
    arb.to_csv(OUT / "tarrant_arb_2026_dedup.csv", index=False)

    # ---- one row per account
    v = roll[["Account_Num", "RP", "Property_Class", "State_Use_Code", "Owner_Name", "Situs_Address",
              "Exemption_Code", "Notice_Date", "Total_Value", "Appraised_Value", "rows_in_file"]].rename(
        columns={"Total_Value": "roll_value_oct", "Appraised_Value": "roll_appraised_oct"})
    v["roll_value_oct"] = num(v.roll_value_oct)
    v = v.merge(roll_r[["Account_Num", "Total_Value"]].rename(columns={"Total_Value": "roll_value_nov"}),
                on="Account_Num", how="left")
    v = v.merge(roll_25[["Account_Num", "Total_Value"]].rename(columns={"Total_Value": "prior_year_value"}),
                on="Account_Num", how="left")
    a_cols = ["pID", "CaseNumber", "CaseStatus", "path", "ProtestFilingDate", "ScheduledHearingDate", "finalizedDt",
              "AppellantType", "AppellantName", "agentID", "is_ours", "shared_with_other_agent", "agents_on_case",
              "agents_on_account", "cases_on_account", "NoticeMarketValue", "ownerNetAppraisedValue",
              "appraisedValue", "finalMarketValue"]
    v = v.merge(arb[a_cols], left_on="Account_Num", right_on="pID", how="outer", indicator="_m")
    v["Account_Num"] = v.Account_Num.fillna(v.pID)
    v["in_roll"] = v._m.ne("right_only")
    v["protested"] = v._m.ne("left_only") & v.CaseStatus.map(STATUS_RANK).lt(3)
    v["is_ours"] = v.is_ours.fillna(False).astype(bool)
    for c in ["roll_value_nov", "prior_year_value", "NoticeMarketValue", "ownerNetAppraisedValue",
              "appraisedValue", "finalMarketValue"]:
        v[c] = num(v[c])

    v["notice_value"] = v.NoticeMarketValue.fillna(v.roll_value_oct)
    v["owner_net_value"] = v.ownerNetAppraisedValue
    open_case = v.path.eq("Open")
    v["final_value"] = np.where(v.CaseStatus.notna() & ~open_case, v.finalMarketValue,
                                np.where(open_case, v.notice_value, v.roll_value_oct))
    v["reduction"] = v.notice_value - v.final_value
    v["reduction_pct"] = (v.reduction / v.notice_value).where(v.notice_value > 0)
    # values to look at by hand: $0 notice, or final more than 25% above notice
    v["check_values"] = v.protested & ((v.notice_value <= 0) | (v.final_value > v.notice_value * 1.25))
    v["change_vs_prior_year"] = v.final_value - v.prior_year_value
    v["notice_vs_prior_year_pct"] = ((v.notice_value - v.prior_year_value) / v.prior_year_value).where(v.prior_year_value > 0)
    v["outcome"] = np.select(
        [~v.protested & v.CaseStatus.isna(), ~v.protested, open_case, v.reduction > 0, v.reduction < 0],
        ["Not protested", "Not a protest (setup error / untimely)", "Open", "Reduced", "Increased"],
        default="No change")
    # cross-check: the Nov residential roll should carry the final value
    v["final_matches_nov_roll"] = np.where(v.roll_value_nov.notna(), v.final_value == v.roll_value_nov, pd.NA)
    v["est_fee_1pct"] = (v.reduction.clip(lower=0) * 0.01).where(v.is_ours)

    order = ["Account_Num", "RP", "Property_Class", "State_Use_Code", "Situs_Address", "Owner_Name", "Exemption_Code",
             "is_ours", "protested", "outcome", "path", "CaseStatus", "prior_year_value", "notice_value",
             "owner_net_value", "final_value", "reduction", "reduction_pct", "check_values",
             "change_vs_prior_year", "notice_vs_prior_year_pct", "est_fee_1pct", "roll_value_oct", "roll_value_nov",
             "final_matches_nov_roll", "CaseNumber", "ProtestFilingDate", "ScheduledHearingDate", "finalizedDt",
             "AppellantType", "AppellantName", "agentID", "shared_with_other_agent", "agents_on_case",
             "agents_on_account", "cases_on_account", "Notice_Date", "rows_in_file", "in_roll"]
    v = v[order].sort_values("Account_Num", key=lambda s: num(s).fillna(np.inf), kind="stable")
    assert not v.Account_Num.duplicated().any()
    v.to_csv(OUT / "tarrant_values_2026.csv", index=False)
    print(f"tarrant_values_2026.csv: {len(v):,} accounts")

    # ---- summary: us vs everyone else, protested accounts only
    p = v[v.protested].copy()
    p["who"] = np.where(p.is_ours, "Property Tax Protest (us)",
                        np.where(p.AppellantType.eq("Agent"), "Other agents",
                                 np.where(p.AppellantType.eq("Owner"), "Owners", "Other / TAD")))
    rows = []
    for (who, rp), d in list(p.groupby(["who", "RP"])) + [((w, "ALL"), d) for w, d in p.groupby("who")]:
        closed = d[d.outcome.isin(["Reduced", "No change", "Increased"]) & ~d.check_values]
        rows.append({
            "who": who, "RP": rp, "accounts": len(d), "open": int(d.outcome.eq("Open").sum()), "flagged_values": int(d.check_values.sum()),
            "closed_with_result": len(closed), "reduced": int(closed.outcome.eq("Reduced").sum()),
            "win_rate": closed.outcome.eq("Reduced").mean() if len(closed) else np.nan,
            "informal": int(d.path.eq("Informal (joint motion)").sum()), "arb_hearing": int(d.path.eq("ARB hearing").sum()),
            "fta": int(d.path.eq("Failure to appear").sum()), "withdrawn": int(d.path.eq("Withdrawn / dismissed").sum()),
            "notice_total": closed.notice_value.sum(), "final_total": closed.final_value.sum(),
            "reduction_total": closed.reduction.sum(),
            "reduction_pct_of_notice": closed.reduction.sum() / closed.notice_value.sum() if len(closed) else np.nan,
            "avg_reduction_pct": closed.reduction_pct.mean(), "median_reduction_pct": closed.reduction_pct.median(),
        })
    s = pd.DataFrame(rows).sort_values(["RP", "who"])
    s.to_csv(OUT / "tarrant_values_2026_summary.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(s[s.RP.isin(["ALL", "R"])].round(3).to_string(index=False))

    ours = v[v.is_ours]
    print(f"\nOurs: {len(ours):,} accounts; shared case with another agent: {ours.shared_with_other_agent.sum():,}; "
          f"final == Nov roll: {ours.final_matches_nov_roll.dropna().astype(bool).mean():.1%} of {ours.final_matches_nov_roll.notna().sum():,}")
    print("ARB accounts not in the roll file:", int((~v.in_roll).sum()))


if __name__ == "__main__":
    main()
