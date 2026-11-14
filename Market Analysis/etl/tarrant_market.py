"""Tarrant (TAD) market fragment: work/tarrant/{market,segments,firms}.csv  (2024, 2025, 2026).

Sources (CAD Website/Tarrant/Data):
  roll      2026: output/tarrant_property_2026_dedup.csv (PropertyData(Delimited)_2026.txt, deduped per Account_Num
                  by Tarrant/etl/tarrant_arb_values_2026.py)
            2025: PropertyData_2025.txt   2024: PropertyData_2024.txt
  HS        2026: AgentSummaryData_2025/AgentSummaryData_8_Exemption.txt (folder says 2025, rows are TaxYear 2026)
            2025: PropertyData_Exemptions_2025.txt   2024: PropertyData_Exemptions_2024.txt
  protests  2026: ORR20261019 ... ARB Info 2026.csv (open-records request, every case, one row per agent on case)
            2025: ORR20261019 ... ARB Info 2025.csv
            2024: AgentSummaryData_2024/AgentSummaryData_9_ReviewBoard.txt (Agency = agent ID)
  agent of record: TAD publishes no appointment list in these files; an account "has an agent" when an agent ID is
            listed on one of its valid protest cases that year (ARB file lists each case once per agent on the account).

Run: /Users/user2/PTP/.venv/bin/python -I "Market Analysis/etl/tarrant_market.py"
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/user2/PTP")
D = ROOT / "CAD Website" / "Tarrant" / "Data"
TOUT = ROOT / "CAD Website" / "Tarrant" / "output"
OUT = ROOT / "Market Analysis" / "work" / "tarrant"
OUT.mkdir(parents=True, exist_ok=True)
PTP = "1487"
PTP_2024 = "795"   # 2024 ReviewBoard agency code for PROPERTY TAX PROTEST
NOT_PROTEST = {"Protest Setup in Error", "Filed Untimely", "Protest Filed Untimely", "25.25(b) Correction",
               "JOINT MOTION 25.25(h) RESOLVED", "Reference Only Account", "Incomplete Account"}

BRANDS = [  # regex on agent name -> firm
    (r"^PROPERTY TAX PROTEST\b", "Property Tax Protest"), (r"OWNWELL", "Ownwell"), (r"\bRYAN\b", "Ryan LLC"),
    (r"O ?'?CONNOR", "O'Connor & Associates"), (r"CHANDLER CROUCH", "Chandler Crouch"),
    (r"RESOLUTE PROPERTY TAX", "Resolute Property Tax Solution"), (r"RAY TAX GROUP", "The Ray Tax Group"),
    (r"SOUTHLAND PROPERTY TAX", "Southland Property Tax Consultants"), (r"^TEXAS TAX PROTEST", "Texas Tax Protest"),
    (r"PEYCO", "Peyco Southwest Realty"), (r"PROPERTY TAX LOCK", "Property Tax Lock"), (r"INTEGRATAX", "Integratax"),
    (r"NORTH TEXAS PROPERTY TAX", "North Texas Property Tax Services"), (r"TEXAS PROTAX", "Texas ProTax"),
    (r"TEXAS PROPERTY TAX REDUCTIONS", "Texas Property Tax Reductions"), (r"POPP HUTCHESON", "Popp Hutcheson"),
    (r"KROLL", "Kroll"), (r"MARVIN F POER|POER", "Marvin F. Poer"), (r"DUCHARME", "DuCharme McMillen"),
    (r"PROPERTY TAX ADVISORS", "Property Tax Advisors"), (r"FIVE STONE", "Five Stone Tax Advisers"),
]


def firm_of(name, aid):
    n = re.sub(r"\s+", " ", str(name or "").upper().replace(".", "").replace(",", "")).strip()
    for pat, f in BRANDS:
        if re.search(pat, n):
            return f
    if not n:
        return f"Agent ID {aid}" if aid else "Unknown agent"
    return re.sub(r"\b(LLC|INC|LP|LTD|CORP|CO|PLLC)\b", "", n).strip()


def strip0(s):
    return s.astype(str).str.strip().str.lstrip("0")


def read_pipe(path, cols, enc="latin-1"):
    return pd.read_csv(path, sep="|", dtype=str, keep_default_na=False, quoting=3, usecols=cols, encoding=enc)


def read_utf16(path):
    t = open(path, encoding="utf-16").read().splitlines()
    h = [c.strip() for c in t[0].split("|")]
    rows = [(([x.strip() for x in l.split("|")]) + [""] * len(h))[:len(h)] for l in t[1:] if l.strip()]
    return pd.DataFrame(rows, columns=h)


def roll(year):
    if year == 2026:
        r = pd.read_csv(TOUT / "tarrant_property_2026_dedup.csv", dtype=str, keep_default_na=False,
                        usecols=["Account_Num", "State_Use_Code"])
        src = "PropertyData(Delimited)_2026.txt"
    else:
        src = f"PropertyData_{year}.txt"
        r = read_pipe(D / src, ["Account_Num", "State_Use_Code"])
    r["acct"] = strip0(r.Account_Num)
    r["sc"] = r.State_Use_Code.str.strip().str.upper()
    return r.drop_duplicates("acct")[["acct", "sc"]], src


def homestead(year):
    if year == 2026:
        e = read_utf16(D / "AgentSummaryData_2025" / "AgentSummaryData_8_Exemption.txt")
        assert set(e.TaxYear) == {"2026"}
        acc, ex = e.AccountNumber, e.Exemptions
    else:
        e = read_pipe(D / f"PropertyData_Exemptions_{year}.txt", ["Account_Num", "Exemption"])
        acc, ex = e.Account_Num, e.Exemption
    return set(strip0(acc[ex.str.strip().str.startswith("HOMESTEAD GENERAL")]))


def agent_names():
    """agentID -> most common appellant name on Agent-type cases (2025 + 2026 ARB files)."""
    x = pd.concat([pd.read_csv(D / f"ORR20261019 - Avetik Ghazaryan - ARB Info {y}.csv", dtype=str,
                               keep_default_na=False, usecols=["agentID", "AppellantType", "AppellantName"])
                   for y in (2025, 2026)])
    x = x[x.AppellantType.eq("Agent") & x.agentID.ne("") & x.AppellantName.str.strip().ne("")]
    return x.groupby("agentID").AppellantName.agg(lambda s: s.value_counts().index[0]).to_dict()


def protests(year, names):
    """One row per (account, case, agent) with valid protests only. Columns acct, case, aid, agent_filed, firm."""
    if year == 2024:
        src = "AgentSummaryData_2024/AgentSummaryData_9_ReviewBoard.txt"
        p = read_utf16(D / src)
        p = p[~p.CaseStatus.isin(NOT_PROTEST)]
        # 2024 Agency is TAD's older agency code (not the agentID used in 2025/2026): PTP = 00795 (crosswalks
        # to agentID 1487 on 861 shared accounts). Appellant holds the agent's name on agent-filed cases.
        known = {n.strip().upper() for n in names.values()}
        p = pd.DataFrame({"acct": strip0(p.AccountNumber), "case": p.CaseNumber, "aid": strip0(p.Agency),
                          "status": p.CaseStatus, "aname": p.Appellant})
        named = p.aname.str.upper().isin(known)
        p["agent_filed"] = p.aid.ne("") | named
        # agency code -> its most common agent name (fills cases with a code but an owner/blank appellant)
        code_name = p[named & p.aid.ne("")].groupby("aid").aname.agg(lambda s: s.value_counts().index[0])
        p["aname"] = p.aname.where(named, p.aid.map(code_name)).fillna("")
        p.loc[p.aname.str.upper().str.startswith("PROPERTY TAX PROTEST"), "aid"] = PTP_2024
        p.attrs["code_firm"] = {c: firm_of(n, c) for c, n in code_name.items()}
    else:
        src = f"ORR20261019 - Avetik Ghazaryan - ARB Info {year}.csv"
        p = pd.read_csv(D / src, dtype=str, keep_default_na=False)
        p = p[~p.CaseStatus.isin(NOT_PROTEST)]
        p = pd.DataFrame({"acct": strip0(p.pID), "case": p.CaseNumber, "aid": p.agentID.str.strip(),
                          "status": p.CaseStatus, "atype": p.AppellantType, "aname0": p.AppellantName})
        # agent-filed: an agent is listed on the case, or the appellant type is Agent.
        # Owner-filed: Owner, or Other with no agent (2026 "Other" = mostly online filings recorded as
        # "TARRANT APPRAISAL DISTRICT"; 2025 calls the same filings Owner).
        p["agent_filed"] = p.aid.ne("") | p.atype.eq("Agent")
        p["aname"] = p.aid.map(names)
        p["aname"] = p.aname.fillna(p.aname0.where(p.atype.eq("Agent"), "")).fillna("")
    p["firm"] = [firm_of(n, a) if f else "" for n, a, f in zip(p.aname, p.aid, p.agent_filed)]
    p.loc[p.aid.isin([PTP, PTP_2024]), "firm"] = "Property Tax Protest"
    return p, src


def main():
    names = agent_names()
    assert firm_of(names.get(PTP), PTP) == "Property Tax Protest", names.get(PTP)
    years = [2024, 2025, 2026]
    prot = {y: protests(y, names) for y in years}
    market, segs, firms, maps = [], [], [], {}
    for y in years:
        r, rsrc = roll(y)
        hs = homestead(y)
        p, psrc = prot[y]
        A = set(r.acct[r.sc.str.startswith("A")])
        pa = p.groupby("acct").agent_filed.any()
        protested = set(pa.index)
        agent_accts = set(pa.index[pa])
        owner_only = protested - agent_accts
        ptp = set(p.acct[p.firm.eq("Property Tax Protest")])
        ac = p.drop_duplicates("case")
        market.append(dict(
            county="Tarrant", year=y, total_accounts=len(r), accounts_cat_A=len(A),
            accounts_cat_B=int(r.sc.str.startswith("B").sum()), accounts_cat_M=int(r.sc.str.startswith("M").sum()),
            mineral_accounts=int(r.sc.str.startswith("G").sum()), homes_A_homestead=len(A & hs),
            homes_A_with_agent=len(A & agent_accts), homes_A_protested=len(A & protested),
            homes_A_protested_by_agent=len(A & agent_accts), homes_A_protested_by_owner=len(A & owner_only),
            homes_A_ptp_agent=len(A & ptp), homes_A_ptp_protested=len(A & ptp),
            all_protests=len(protested), all_agent_protests=len(agent_accts),
            source_roll_file=rsrc, source_agent_file=psrc + " (agents listed on protest cases)",
            source_protest_file=psrc,
            roll_version_date={2026: "2026-10-26 (download)", 2025: "2026-10-26 (download)",
                               2024: "2026-10-26 (download)"}[y]))
        # segments
        hist = set().union(*[set(prot[h][0].acct) for h in years if h < y]) if y > 2024 else None
        seg = dict(county="Tarrant", year=y, homes_A=len(A), seg_agent=len(A & agent_accts),
                   seg_owner_alone=len(A & owner_only), seg_ptp=len(A & ptp))
        rest = A - protested
        if hist is None:
            seg.update(seg_lapsed="", seg_never="", seg_lapsed_or_never=len(rest))
        else:
            seg.update(seg_lapsed=len(rest & hist), seg_never=len(rest - hist), seg_lapsed_or_never="")
        assert seg["seg_agent"] + seg["seg_owner_alone"] + len(rest) == len(A)
        segs.append(seg)
        # firms
        ag = p[p.firm.ne("")]
        fa = ag.groupby("firm").agg(ids=("aid", lambda s: ";".join(sorted({i for i in s if i}, key=lambda v: int(v) if v.isdigit() else 0)))).ids
        home = ag[ag.acct.isin(A)].groupby("firm").acct.nunique()
        allc = ag.groupby("firm").acct.nunique()
        maps[y] = fa
        if y == 2024:
            cf = pd.Series(p.attrs["code_firm"])
            fa = cf.groupby(cf).apply(lambda s: ";".join(sorted(s.index, key=int)) if all(i.isdigit() for i in s.index) else ";".join(sorted(s.index)))
            fa.index = fa.index.get_level_values(-1) if fa.index.nlevels > 1 else fa.index
        big = [f for f in home.index if (home[f] >= 100 and f != "Unknown agent") or f == "Property Tax Protest"]
        if "Property Tax Protest" not in big:
            big.append("Property Tax Protest")
        for f in sorted(big, key=lambda f: -home.get(f, 0)):
            firms.append(dict(county="Tarrant", year=y, firm=f, agent_ids=fa.get(f, PTP if f == "Property Tax Protest" else ""),
                              homes_A_agent_of_record=int(home.get(f, 0)), homes_A_protests_filed=int(home.get(f, 0)),
                              all_accounts_agent_of_rec=int(allc.get(f, 0))))
        oth = ag[~ag.firm.isin(big)]
        firms.append(dict(county="Tarrant", year=y, firm="All other agents", agent_ids="",
                          homes_A_agent_of_record=oth[oth.acct.isin(A)].acct.nunique(),
                          homes_A_protests_filed=oth[oth.acct.isin(A)].acct.nunique(),
                          all_accounts_agent_of_rec=oth.acct.nunique()))
        firms.append(dict(county="Tarrant", year=y, firm="Owners (self-filed)", agent_ids="",
                          homes_A_agent_of_record="", homes_A_protests_filed=len(A & owner_only),
                          all_accounts_agent_of_rec=""))
        print(y, "cases", len(ac), "accounts", len(protested), "| statuses excluded:", NOT_PROTEST & set(prot[y][0].status))
    pd.DataFrame(market).to_csv(OUT / "market.csv", index=False)
    pd.DataFrame(segs)[["county", "year", "homes_A", "seg_agent", "seg_owner_alone", "seg_lapsed", "seg_never",
                        "seg_lapsed_or_never", "seg_ptp"]].to_csv(OUT / "segments.csv", index=False)
    pd.DataFrame(firms).to_csv(OUT / "firms.csv", index=False)
    with open(OUT / "firm_map.txt", "w") as f:
        for y, fa in maps.items():
            for firm, ids in fa.items():
                f.write(f"{y}\t{firm}\t{ids}\n")
    for y in years:
        print(y, "cases:", prot[y][0].case.nunique())
    print(pd.DataFrame(market).T.to_string())
    print(pd.DataFrame(segs).to_string())


if __name__ == "__main__":
    main()
