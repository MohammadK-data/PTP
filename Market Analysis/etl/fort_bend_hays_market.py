"""Fort Bend + Hays market fragments (work/fort_bend, work/hays) per work/SPEC.md.

Sources (all local, see notes.md for URLs):
  Orion certified exports (PropertyExport / OwnerExport / ExemptionExport / AgentExport):
    Fort Bend 2026 (07-07-2026), 2025 (re-export 08-17-2026), 2024 (re-export 08-19-2026)
    Hays 2026 (07-18-2026)
  Hays 2024 / 2025 "Certified Data Export" (PropertyDataExport CSV format: PROPERTY / OWNER / LAND / IMPROVEMENT)

State code of an account
  Orion: StateCodeImp if present, else StateCodeLand (same rule for every Orion year).
  PropertyDataExport (Hays 2024/25): improvement StateCode of the highest-value improvement, else
  land StateCode of the highest-value land segment.
Home = state code starts with A; B, M reported separately; mineral = state code starts with G.
Homestead = any owner record of the account carries exemption code HS (Orion ExemptionExport; OwnerExport
  ExemptionList for the PropertyDataExport format).
Agent (Hays 2026 only): CAAgentID or ARBAgentID filled on any owner record of the account in the
  certified OwnerExport (current at certification; no effective/expiration dates in the file).
  Fort Bend exports are redacted (no agent ID column anywhere); Hays 2024/25 format has no agent field.
Protests: not published per account by either CAD -> blank. (Orion ARBProtestFlag = protest still open at
  certification, not "protested this year"; reported in notes only.)

Run: /Users/user2/PTP/.venv/bin/python -I "Market Analysis/etl/fort_bend_hays_market.py"
"""
import io
import re
import zipfile
from pathlib import Path

import pandas as pd

CAD = Path("/Users/user2/PTP/CAD Website")
WORK = Path("/Users/user2/PTP/Market Analysis/work")
FB = CAD / "For Bend" / "Data"
HY = CAD / "Hays" / "Data"

MARKET_COLS = ["county", "year", "total_accounts", "accounts_cat_A", "accounts_cat_B", "accounts_cat_M",
               "mineral_accounts", "homes_A_homestead", "homes_A_with_agent", "homes_A_protested",
               "homes_A_protested_by_agent", "homes_A_protested_by_owner", "homes_A_ptp_agent",
               "homes_A_ptp_protested", "all_protests", "all_agent_protests", "source_roll_file",
               "source_agent_file", "source_protest_file", "roll_version_date"]
SEG_COLS = ["county", "year", "homes_A", "seg_agent", "seg_owner_alone", "seg_lapsed", "seg_never",
            "seg_lapsed_or_never", "seg_ptp"]
FIRM_COLS = ["county", "year", "firm", "agent_ids", "homes_A_agent_of_record", "homes_A_protests_filed",
             "all_accounts_agent_of_rec"]

HAYS_PTP = {"A0180641"}

# Firm grouping: first matching pattern on the normalized agent name wins; otherwise the cleaned name.
FIRM_RULES = [
    (r"^(?!.*(BALLARD|KUTNER|WATCHTOWER)).*\bPROPERTY TAX PROTEST\b", "Property Tax Protest"),
    (r"OWNWELL", "Ownwell"),
    (r"TEXAS PROTAX|% TEXAS PROTAX|CAPTA INC", "Texas ProTax"),
    (r"\bRYAN\b", "Ryan LLC"),
    (r"O ?CONNOR", "O'Connor & Associates"),
    (r"KROLL|DUFF & PHELPS", "Kroll"),
    (r"POPP|GRAY & PROUTY|POPP HUTCHESON", "Popp Hutcheson"),
    (r"MARVIN F POER|POER", "Marvin F. Poer"),
    (r"TAX PROTEST CONSULTANTS", "Tax Protest Consultants"),
    (r"TEXAS TAX PROTEST", "Texas Tax Protest"),
    (r"PROPERTY TAX ADVISORS", "Property Tax Advisors"),
    (r"NORTH TEXAS PROPERTY TAX", "North Texas Property Tax Services"),
    (r"HUCKABEE", "Huckabee"),
    (r"TURBO ?PROTEST", "TurboProtest"),
    (r"TAXPROTESTMAP", "TaxProtestMap"),
    (r"PROTEST TAX LLC", "Protest Tax LLC"),
]


def firm_of(name):
    n = re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9&% ]", " ", str(name).upper())).strip()
    n = re.sub(r"^\+*\s*DO NOT USE\s*\+*\s*", "", n).strip()
    for pat, firm in FIRM_RULES:
        if re.search(pat, n):
            return firm
    n = re.sub(r"\b(INC|LLC|LP|LLP|PLLC|CORP|CO|COMPANY|LTD)\b\.?", "", n)
    n = re.sub(r"[\s&%]+$", "", re.sub(r"\s+", " ", n)).strip()
    return n.title() or "(blank name)"


def cat_counts(sc):
    first = sc.str[:1]
    return dict(total_accounts=len(sc), accounts_cat_A=int((first == "A").sum()),
                accounts_cat_B=int((first == "B").sum()), accounts_cat_M=int((first == "M").sum()),
                mineral_accounts=int((first == "G").sum()))


def read(path, cols, **kw):
    return pd.read_csv(path, dtype=str, keep_default_na=False, usecols=lambda c: c.lstrip("﻿?\"") in cols,
                       encoding="utf-8-sig", **kw).rename(columns=lambda c: c.lstrip("﻿?\""))


def orion(folder):
    """-> DataFrame one row per account: state code, homestead, agent ids (set)."""
    folder = Path(folder)
    f = {k: next(folder.glob(f"*_{k}Export.txt")) for k in ["Property", "Owner", "Exemption", "Agent"]}
    p = read(f["Property"], {"PropertyQuickRefID", "StateCodeLand", "StateCodeImp", "ARBProtestFlag", "TaxYear",
                             "SupplementNumber"})
    p = p.drop_duplicates("PropertyQuickRefID")
    p["sc"] = p.StateCodeImp.str.strip().where(p.StateCodeImp.str.strip() != "", p.StateCodeLand.str.strip())
    ocols = {"PropertyQuickRefID", "OwnerQuickRefID", "CAAgentID", "ARBAgentID"}
    o = read(f["Owner"], ocols)
    e = read(f["Exemption"], {"OwnerQuickRefID", "ExemptionCode"})
    hs_owner = set(e.loc[e.ExemptionCode.str.strip().eq("HS"), "OwnerQuickRefID"])
    hs_prop = set(o.loc[o.OwnerQuickRefID.isin(hs_owner), "PropertyQuickRefID"])
    p["hs"] = p.PropertyQuickRefID.isin(hs_prop)
    has_agent_col = "CAAgentID" in o.columns
    if has_agent_col:
        a = pd.concat([o[["PropertyQuickRefID", c]].rename(columns={c: "aid"}) for c in ["CAAgentID", "ARBAgentID"]])
        a = a[a.aid.str.strip() != ""].drop_duplicates()
        ag = a.groupby("PropertyQuickRefID").aid.agg(set)
        p["agents"] = p.PropertyQuickRefID.map(ag)
    else:
        p["agents"] = None
    agents = read(f["Agent"], {"AgentID", "AgentName"})
    return p, agents, has_agent_col, f


def pde(folder):
    """Hays PropertyDataExport format (2024/2025 certified data export zips)."""
    folder = Path(folder)

    def zread(key, cols):
        def tag(n):
            return re.sub(r"PROPERTY[- ]DATA[- ]EXPORT|CERTIFIED[- ]DATA[- ]EXPORT", "", n.upper())
        z = [x for x in folder.rglob("*.zip") if key in tag(x.name)]
        assert len(z) == 1, (key, z)
        z = z[0]
        zf = zipfile.ZipFile(z)
        inner = zf.infolist()[0]
        with zf.open(inner) as fh:
            df = pd.read_csv(io.TextIOWrapper(fh, encoding="utf-8-sig", errors="replace"), dtype=str,
                             keep_default_na=False, usecols=cols)
        return df, z.name, inner.filename

    p, pn, _ = zread("PROPERTY", ["PropertyID", "QuickRefID"])
    o, on, _ = zread("OWNER", ["PropertyID", "ExemptionList"])
    imp, imn, _ = zread("IMPROVEMENT", ["PropertyID", "StateCode", "ImpValue"])
    land, ln, _ = zread("LAND", ["PropertyID", "StateCode", "Value"])
    p = p.drop_duplicates("PropertyID")
    imp["v"] = pd.to_numeric(imp.ImpValue, errors="coerce").fillna(0)
    land["v"] = pd.to_numeric(land.Value, errors="coerce").fillna(0)
    isc = imp[imp.StateCode.str.strip() != ""].sort_values("v").drop_duplicates("PropertyID", keep="last") \
        .set_index("PropertyID").StateCode.str.strip()
    lsc = land[land.StateCode.str.strip() != ""].sort_values("v").drop_duplicates("PropertyID", keep="last") \
        .set_index("PropertyID").StateCode.str.strip()
    p["sc"] = p.PropertyID.map(isc).fillna(p.PropertyID.map(lsc)).fillna("")
    hs = set(o.loc[o.ExemptionList.str.split(",").apply(lambda xs: "HS" in [x.strip() for x in xs]), "PropertyID"])
    p["hs"] = p.PropertyID.isin(hs)
    return p, [pn, on, imn, ln]


def build_rows(county, year, p, agents_df, has_agent, ptp_ids, roll_file, agent_file, roll_date):
    home = p.sc.str.startswith("A")
    m = {"county": county, "year": year, **cat_counts(p.sc), "homes_A_homestead": int((home & p.hs).sum())}
    seg = {"county": county, "year": year, "homes_A": int(home.sum())}
    firms = []
    if has_agent:
        hasag = p.agents.notna()
        ptp = p.agents.apply(lambda s: bool(s & ptp_ids) if isinstance(s, set) else False)
        m.update(homes_A_with_agent=int((home & hasag).sum()), homes_A_ptp_agent=int((home & ptp).sum()))
        seg.update(seg_agent=int((home & hasag).sum()), seg_ptp=int((home & ptp).sum()))
        # firm attribution: an account counts once per firm (several IDs of one firm = one account)
        names = agents_df.copy()
        names["aid"] = "A" + names.AgentID.str.strip()
        names["firm"] = names.AgentName.apply(firm_of)
        fmap = dict(zip(names.aid, names.firm))
        for i in ptp_ids:
            fmap[i] = "Property Tax Protest"
        ex = p[hasag][["sc", "agents"]].explode("agents")
        ex["firm"] = ex.agents.map(fmap).fillna("(ID not in agent list)")
        ex["home"] = ex.sc.str.startswith("A")
        ex = ex.reset_index().drop_duplicates(["index", "firm"])
        g = ex.groupby("firm").agg(homes=("home", "sum"), allacc=("index", "nunique"))
        ids = ex.groupby("firm").agents.agg(lambda s: ";".join(sorted(set(s))))
        big = g[(g.homes >= 100) | (g.index == "Property Tax Protest")].sort_values("homes", ascending=False)
        for firm, r in big.iterrows():
            firms.append({"county": county, "year": year, "firm": firm, "agent_ids": ids[firm],
                          "homes_A_agent_of_record": int(r.homes), "homes_A_protests_filed": "",
                          "all_accounts_agent_of_rec": int(r.allacc)})
        if "Property Tax Protest" not in big.index:
            firms.append({"county": county, "year": year, "firm": "Property Tax Protest",
                          "agent_ids": ";".join(sorted(ptp_ids)), "homes_A_agent_of_record": 0,
                          "homes_A_protests_filed": "", "all_accounts_agent_of_rec": 0})
        # "All other agents": accounts whose agents are all outside the listed firms
        listed = set(big.index) | {"Property Tax Protest"}
        acc_firms = ex.groupby("index").firm.agg(set)
        other = acc_firms[acc_firms.apply(lambda s: not (s & listed))].index
        oth = p.loc[other]
        firms.append({"county": county, "year": year, "firm": "All other agents",
                      "agent_ids": f"{ex.loc[~ex.firm.isin(listed), 'agents'].nunique()} other IDs",
                      "homes_A_agent_of_record": int(oth.sc.str.startswith("A").sum()),
                      "homes_A_protests_filed": "", "all_accounts_agent_of_rec": len(oth)})
        firms.append({"county": county, "year": year, "firm": "Owners (self-filed)", "agent_ids": "",
                      "homes_A_agent_of_record": "", "homes_A_protests_filed": "", "all_accounts_agent_of_rec": ""})
        fm = names[["firm", "aid", "AgentName"]]
    else:
        fm = None
        if ptp_ids is not None and year == 2026:
            # placeholder rows so the table shows the county; no account-level agent or protest data
            for firm, ids in [("Property Tax Protest", ";".join(sorted(ptp_ids))), ("All other agents", ""),
                              ("Owners (self-filed)", "")]:
                firms.append({"county": county, "year": year, "firm": firm, "agent_ids": ids,
                              "homes_A_agent_of_record": "", "homes_A_protests_filed": "",
                              "all_accounts_agent_of_rec": ""})
    m.update(source_roll_file=roll_file, source_agent_file=agent_file, source_protest_file="",
             roll_version_date=roll_date)
    return m, seg, firms, fm


def write(county_dir, markets, segs, firms):
    d = WORK / county_dir
    d.mkdir(parents=True, exist_ok=True)

    def ints(df):
        for c in df.columns:
            if c not in ("county", "firm", "agent_ids") and not c.startswith("source") and c != "roll_version_date":
                df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
        return df
    ints(pd.DataFrame(markets).reindex(columns=MARKET_COLS).sort_values("year")).to_csv(d / "market.csv", index=False)
    ints(pd.DataFrame(segs).reindex(columns=SEG_COLS).sort_values("year")).to_csv(d / "segments.csv", index=False)
    ints(pd.DataFrame(firms, columns=FIRM_COLS)).to_csv(d / "firms.csv", index=False)


def main():
    # ---------------- Fort Bend ----------------
    fb_sets = [
        (2026, FB / "2026_07_07_1746 Orion 2026 Certified Export-Redacted", "2026-07-07"),
        (2025, FB / "fbcad_2025_certified_download" / "2026_08_17_1646 Orion 2025 Certified Export-Redacted", "2026-08-17"),
        (2024, FB / "fbcad_2024_certified_download" / "2026_08_19_1831 Orion 2024 Certified Export", "2026-08-19"),
    ]
    mk, sg, fr = [], [], []
    for year, folder, date in fb_sets:
        p, agents, has_agent, f = orion(folder)
        print(f"Fort Bend {year}: accounts {len(p):,}, open protests at cert (ARBProtestFlag=1) "
              f"{(p.ARBProtestFlag == '1').sum():,} (homes {((p.ARBProtestFlag == '1') & p.sc.str.startswith('A')).sum():,}), "
              f"agent col: {has_agent}")
        m, s, firms, _ = build_rows("Fort Bend", year, p, agents, has_agent, {"A0830173"},
                                    f"{f['Property'].name}; {f['Owner'].name}; {f['Exemption'].name}", "", date)
        mk.append(m); sg.append(s); fr += firms
    write("fort_bend", mk, sg, fr)

    # ---------------- Hays ----------------
    mk, sg, fr = [], [], []
    p, agents, has_agent, f = orion(HY / "2026_07_18_2127-Orion-2026-Certified-Export")
    print(f"Hays 2026: accounts {len(p):,}, open protests at cert {(p.ARBProtestFlag == '1').sum():,}")
    m, s, firms, fm = build_rows("Hays", 2026, p, agents, has_agent, HAYS_PTP,
                                 f"{f['Property'].name}; {f['Owner'].name}; {f['Exemption'].name}",
                                 f"{f['Owner'].name} (CAAgentID/ARBAgentID); {f['Agent'].name}", "2026-07-18")
    mk.append(m); sg.append(s); fr += firms
    fm.sort_values(["firm", "aid"]).to_csv(WORK / "hays" / "firm_mapping_2026.csv", index=False)
    for year, date in [(2025, "2025-07-30"), (2024, "2024-07-26")]:
        p, files = pde(HY / f"hays_{year}_certified_download")
        print(f"Hays {year}: accounts {len(p):,}, no state code {(p.sc == '').sum():,}")
        m, s, _, _ = build_rows("Hays", year, p, None, False, HAYS_PTP, "; ".join(files), "", date)
        mk.append(m); sg.append(s)
    write("hays", mk, sg, fr)
    for c in ["fort_bend", "hays"]:
        print(pd.read_csv(WORK / c / "market.csv").T.to_string())
        print(pd.read_csv(WORK / c / "firms.csv").to_string())


if __name__ == "__main__":
    main()
