"""Travis + Montgomery market fragments -> Market Analysis/work/<county>/{market,segments,firms}.csv

2026 (both counties)
    Roll      certified PACS export, slim: work/<c>/info_2026_cert.csv.gz (travis_montgomery_pacs_slim.py)
              Travis   "2026 Certified Appraisal Export Supp 0_07182026/PROP.TXT"   (07/18/2026)
              Montgomery "Certified Appraisal Roll 2026/2026-08-04_2026_APPRAISAL_INFO.TXT" (08/03/2026)
              one row per prop_id (first row kept; Montgomery repeats a prop once per geo_id).
    Agents    protax JSON appointments with effective / expiration dates
              Travis      work/travis/travis_agents_2026.csv.gz (travis_agents_2026.py, JSON of 10/06/2026)
              Montgomery  CAD Website/Montgomery/output/protax_csv/20260804_owner_agents.csv.gz (JSON of 08/04/2026)
    Protests  2026 appeals from the same JSON: CAD Website/<C>/output/<c>_appeals_2026.csv.gz
              Travis value protests = appealType P; Montgomery = PROT, PROTPH, P
              (left out: Travis PY / T, Montgomery 25.25C / 25.25D / 26.09D1 = correction motions, not protests)
2024, 2025
    Travis      EARS roll submissions (work/travis/ears_<y>.csv.gz, travis_ears_slim.py): roll counts only
    Montgomery  certified PACS exports (work/montgomery/info_<y>_cert.csv.gz): roll counts + ca_agent_id
                (agent of record at certification, no dates). No protest source for either.

Rules
    category   account is A if any of imprv/land/personal/mineral state code starts with A (EARS: any AJR031),
               else B if any starts with B, else M if any starts with M. mineral = any code starting with G.
    homestead  PACS hs_exempt = T; EARS AJR039 = Y.
    has agent  2026: an appointment effective on/before the deadline (max(May 15, noticeDt + 30 days)) and not
               expired before it (expirationDt missing or >= deadline); effectiveDt missing counts as effective.
               PLUS any account whose 2026 protest was filed by an agent (the filing proves an appointment, even
               when it was dated after the deadline). homes_A_with_agent and seg_agent use this combined flag.
    protested  >= 1 value protest in 2026. Filer: appealedByType A = agent, O = owner, OTH = other (neither).
               An account with both an agent and an owner filing counts as agent-filed.
    all_protests / all_agent_protests  count protest cases (appeal rows), all property types.
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CAD = ROOT / "CAD Website"
WORK = ROOT / "Market Analysis" / "work"

PTP = {"travis": {"1863738", "1328537"}, "montgomery": {"654513", "412"}}
PROTEST_TYPES = {"travis": {"P"}, "montgomery": {"PROT", "PROTPH", "P"}}

M_COLS = ["county", "year", "total_accounts", "accounts_cat_A", "accounts_cat_B", "accounts_cat_M", "mineral_accounts",
          "homes_A_homestead", "homes_A_with_agent", "homes_A_protested", "homes_A_protested_by_agent",
          "homes_A_protested_by_owner", "homes_A_ptp_agent", "homes_A_ptp_protested", "all_protests",
          "all_agent_protests", "source_roll_file", "source_agent_file", "source_protest_file", "roll_version_date"]
S_COLS = ["county", "year", "homes_A", "seg_agent", "seg_owner_alone", "seg_lapsed", "seg_never",
          "seg_lapsed_or_never", "seg_ptp"]
F_COLS = ["county", "year", "firm", "agent_ids", "homes_A_agent_of_record", "homes_A_protests_filed",
          "all_accounts_agent_of_rec"]

# ---------- firm grouping ----------
BRANDS = [  # (regex on normalized name, firm)
    (r"^PROPERTY TAX PROTEST$", "Property Tax Protest"),
    (r"OWNWELL", "Ownwell"),
    (r"TEXAS PRO ?TAX", "Texas ProTax"),
    (r"^RYAN\b", "Ryan LLC"),
    (r"^O ?CONNOR (&|AND) ASSOC", "O'Connor & Associates"),
    (r"^QUATRO", "Quatro Tax"),
    (r"POKORNY", "Pokorny Property Tax Consultants"),
    (r"KROLL", "Kroll"),
    (r"HOMETOWN PROPERTY TAX", "Hometown Property Tax"),
    (r"PROPERTY TAX ADVISORS|PTAX ADVISORS", "Property Tax Advisors"),
    (r"FIVE STONE", "Five Stone Property Tax"),
    (r"NORTH AMERICAN PROPERTY TAX", "North American Property Tax"),
    (r"PERRYMAN", "Perryman"),
    (r"POPP ?HUTCHESON|POPP", "Popp Hutcheson"),
    (r"MARVIN F POER|POER", "Marvin F. Poer"),
    (r"DUFF ?& ?PHELPS|DUFF AND PHELPS", "Kroll"),
    (r"TAX ?EASE|TAXEASE", "TaxEase"),
    (r"HUSCH", "Husch Blackwell"),
    (r"PROTEST ?PROPERTY ?TAX|PROTESTPROPERTYTAX", "ProtestPropertyTax"),
    (r"ROBERTS TAX APPEALS", "Roberts Tax Appeals"),
]
ID_NAME = {}  # agentID -> name from the 2026 JSON, so an ID keeps one firm across years
SUFFIX = re.compile(r"\b(LLC|L L C|INC|INCORPORATED|LP|LLP|PLLC|PC|CO|CORP|CORPORATION|COMPANY|LTD)\b")


def firm_of(name):
    n = (name or "").upper().replace("*", " ")
    n = re.split(r"\s+(?:-\s|AKA\b|A/K/A\b|DBA\b|D/B/A\b|FKA\b|F/K/A\b|FKN\b|C/O\b)", n)[0]
    n = re.sub(r"[^A-Z0-9& ]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    for rx, f in BRANDS:
        if re.search(rx, n):
            return f
    n2 = re.sub(r"\s+", " ", SUFFIX.sub(" ", n)).strip(" &")
    return n2.title() if n2 else "(no name)"


# ---------- helpers ----------
def category(df, cols):
    codes = df[cols].fillna("").astype(str)
    anyst = lambda ch: codes.apply(lambda s: s.str.upper().str.startswith(ch)).any(axis=1)
    a, b, m, g = anyst("A"), anyst("B"), anyst("M"), anyst("G")
    cat = np.select([a, b, m], ["A", "B", "M"], default="")
    return pd.Series(cat, index=df.index), g


def load_cert(path):
    i = pd.read_csv(path, dtype=str, keep_default_na=False)
    i = i.drop_duplicates("prop_id", keep="first").copy()
    i["cat"], i["mineral"] = category(i, ["imprv_state_cd", "land_state_cd", "personal_state_cd", "mineral_state_cd"])
    i["hs"] = i.hs_exempt.eq("T")
    return i


def roll_counts(r):
    return dict(total_accounts=len(r), accounts_cat_A=int(r.cat.eq("A").sum()), accounts_cat_B=int(r.cat.eq("B").sum()),
                accounts_cat_M=int(r.cat.eq("M").sum()), mineral_accounts=int(r.mineral.sum()),
                homes_A_homestead=int((r.cat.eq("A") & r.hs).sum()))


def firm_rows(county, year, agents, homes, protests_by_acct_agent, all_ids_names):
    """agents: DataFrame [pID, agentID] (agent of record); homes: set of home pIDs;
    protests_by_acct_agent: DataFrame [pID, agentID] for agent-filed home protests (or None)."""
    names = all_ids_names.copy()
    names["name"] = names.agentID.map(ID_NAME).fillna(names.name)
    names["firm"] = names.name.map(firm_of)
    id2firm = dict(zip(names.agentID, names.firm))
    ag = agents.copy()
    ag["firm"] = ag.agentID.map(id2firm).fillna("(unnamed agent)")
    ag["home"] = ag.pID.isin(homes)
    home_rec = ag[ag.home].groupby("firm").pID.nunique()
    all_rec = ag.groupby("firm").pID.nunique()
    if protests_by_acct_agent is not None:
        pr = protests_by_acct_agent.copy()
        pr["firm"] = pr.agentID.map(id2firm).fillna("(unnamed agent)")
        home_pr = pr.groupby("firm").pID.nunique()
    else:
        pr, home_pr = None, pd.Series(dtype=int)
    big = set(home_rec[home_rec >= 100].index) | {"Property Tax Protest"}
    rows = []
    for f in sorted(big, key=lambda f: -home_rec.get(f, 0)):
        ids = sorted(set(names.loc[names.firm.eq(f), "agentID"]) & set(ag.agentID), key=lambda x: int(x) if x.isdigit() else 0)
        if f == "Property Tax Protest":
            ids = sorted(PTP[county] & set(ag.agentID)) or sorted(PTP[county])
        rows.append(dict(county=county.title(), year=year, firm=f, agent_ids=";".join(ids),
                         homes_A_agent_of_record=int(home_rec.get(f, 0)),
                         homes_A_protests_filed=(int(home_pr.get(f, 0)) if pr is not None else ""),
                         all_accounts_agent_of_rec=int(all_rec.get(f, 0))))
    rest = ag[~ag.firm.isin(big)]
    rows.append(dict(county=county.title(), year=year, firm="All other agents", agent_ids="",
                     homes_A_agent_of_record=int(rest[rest.home].pID.nunique()),
                     homes_A_protests_filed=(int(pr[~pr.firm.isin(big)].pID.nunique()) if pr is not None else ""),
                     all_accounts_agent_of_rec=int(rest.pID.nunique())))
    mapping = names[names.agentID.isin(ag.agentID)].groupby("firm").agentID.apply(lambda s: sorted(set(s)))
    return rows, mapping


# ---------- 2026 ----------
def year_2026(county):
    C = county.capitalize()
    cert_file = WORK / county / "info_2026_cert.csv.gz"
    r = load_cert(cert_file)
    out = roll_counts(r)

    props = pd.read_csv(CAD / C / "output" / f"{county}_props_2026.csv.gz", dtype=str, keep_default_na=False,
                        usecols=["pID", "noticeDt"])
    if county == "travis":
        ag = pd.read_csv(WORK / "travis" / "travis_agents_2026.csv.gz", dtype=str, keep_default_na=False)
        agent_src = "Travis-protaxExport-20261006.json (owners[].agents)"
    else:
        ag = pd.read_csv(CAD / C / "output/protax_csv/20260804_owner_agents.csv.gz", dtype=str, keep_default_na=False,
                         usecols=["pID", "agentID", "companyName", "contactName", "firstName", "lastName",
                                  "effectiveDt", "expirationDt"])
        ag["name"] = ag.companyName.where(ag.companyName.str.strip().ne(""),
                                          ag.contactName.where(ag.contactName.str.strip().ne(""),
                                                               (ag.firstName + " " + ag.lastName).str.strip()))
        agent_src = "Montgomery-protaxExport-20260804.json (owners[].agents; flattened 20260804_owner_agents.csv.gz)"
    ag["agentID"] = ag.agentID.str.replace(r"\.0$", "", regex=True)
    ag = ag.merge(props, on="pID", how="left")
    nd = pd.to_datetime(ag.noticeDt, errors="coerce") + pd.Timedelta(days=30)
    deadline = nd.where(nd > pd.Timestamp("2026-05-15"), pd.Timestamp("2026-05-15")).fillna(pd.Timestamp("2026-05-15"))
    eff = pd.to_datetime(ag.effectiveDt, errors="coerce")
    exp = pd.to_datetime(ag.expirationDt, errors="coerce")
    active = (eff.isna() | (eff <= deadline)) & (exp.isna() | (exp >= deadline))
    rec = ag.loc[active, ["pID", "agentID"]].drop_duplicates()

    ap = pd.read_csv(CAD / C / "output" / f"{county}_appeals_2026.csv.gz", dtype=str, keep_default_na=False,
                     usecols=["pID", "appealID", "appealType", "appealedByType", "appealedByAgentID"])
    ap = ap[ap.appealType.isin(PROTEST_TYPES[county])].copy()
    ap["agentID"] = ap.appealedByAgentID.str.replace(r"\.0$", "", regex=True)
    ap["by_agent"] = ap.appealedByType.eq("A")
    ap["by_owner"] = ap.appealedByType.eq("O")

    homes = set(r.loc[r.cat.eq("A"), "prop_id"])
    allp = set(r.prop_id)
    apr = ap[ap.pID.isin(allp)]
    agent_filed = set(apr.loc[apr.by_agent, "pID"])
    owner_filed = set(apr.loc[apr.by_owner, "pID"])
    protested = set(apr.pID)
    rec_ids = set(rec.pID)
    has_agent = rec_ids | agent_filed
    ptp_filed = set(apr.loc[apr.by_agent & apr.agentID.isin(PTP[county]), "pID"])
    ptp_rec_rule = set(rec.loc[rec.agentID.isin(PTP[county]), "pID"])
    ptp_rec = ptp_rec_rule | ptp_filed          # same combined rule as has_agent

    hA = lambda s: len(s & homes)
    out.update(homes_A_with_agent=hA(has_agent), homes_A_protested=hA(protested),
               homes_A_protested_by_agent=hA(agent_filed), homes_A_protested_by_owner=hA(owner_filed - agent_filed),
               homes_A_ptp_agent=hA(ptp_rec), homes_A_ptp_protested=hA(ptp_filed),
               all_protests=int(len(ap)), all_agent_protests=int(ap.by_agent.sum()))
    extra = dict(homes_A_agent_rule_only=hA(rec_ids), homes_A_agent_filed_no_record=hA(agent_filed - rec_ids),
                 homes_A_protested_other_filer=hA(protested - agent_filed - owner_filed),
                 ptp_rec_all=len(ptp_rec), homes_A_ptp_rule_only=hA(ptp_rec_rule), ptp_filed_all=len(ptp_filed),
                 protests_not_in_cert_roll=int((~ap.pID.isin(allp)).sum()),
                 protest_accounts_all=int(ap.pID.nunique()))
    seg_agent = hA(has_agent)
    seg_owner = hA(protested - has_agent)
    seg = dict(county=county.title(), year=2026, homes_A=len(homes), seg_agent=seg_agent, seg_owner_alone=seg_owner,
               seg_lapsed="", seg_never="", seg_lapsed_or_never=len(homes) - seg_agent - seg_owner, seg_ptp=hA(ptp_rec))

    # firms: agent of record (+ agent who filed this year's protest, same as has_agent)
    filed_pairs = apr.loc[apr.by_agent, ["pID", "agentID"]].drop_duplicates()
    rec_all = pd.concat([rec, filed_pairs]).drop_duplicates()
    names = ag[["agentID", "name"]].drop_duplicates("agentID")
    ID_NAME.clear()
    ID_NAME.update(dict(zip(names.agentID, names.name)))
    fr, mapping = firm_rows(county, 2026, rec_all, homes, filed_pairs[filed_pairs.pID.isin(homes)], names)
    fr.append(dict(county=county.title(), year=2026, firm="Owners (self-filed)", agent_ids="",
                   homes_A_agent_of_record="", homes_A_protests_filed=hA(owner_filed - agent_filed),
                   all_accounts_agent_of_rec=""))
    if county == "travis":
        roll_src, prot_src, ver = ("2026 Certified Appraisal Export Supp 0_07182026.zip / PROP.TXT",
                                   "Travis-protaxExport-20261006.json (appeals[], 2026, type P)", "2026-07-18")
    else:
        roll_src, prot_src, ver = ("Certified Appraisal Roll 2026 / 2026-08-04_2026_APPRAISAL_INFO.TXT",
                                   "Montgomery-protaxExport-20260804.json (appeals[], 2026, PROT/PROTPH/P)", "2026-08-03")
    out.update(county=county.title(), year=2026, source_roll_file=roll_src, source_agent_file=agent_src,
               source_protest_file=prot_src, roll_version_date=ver)
    return out, seg, fr, mapping, extra


# ---------- prior years ----------
def travis_prior(year):
    e = pd.read_csv(WORK / "travis" / f"ears_{year}.csv.gz", dtype=str, keep_default_na=False)
    cats = e.cats.str.split("|")
    has = lambda ch: cats.apply(lambda cs: any(c.upper().startswith(ch) for c in cs))
    a, b, m, g = has("A"), has("B"), has("M"), has("G")
    e["cat"] = np.select([a, b, m], ["A", "B", "M"], default="")
    e["mineral"] = g
    e["hs"] = e.hs.eq("Y")
    out = roll_counts(e)
    f = {2024: ("227EARS082824 (2).zip / 227EARS082824.csv", "2024-08-28"),
         2025: ("227EARS090425.zip / 227EARS090425.csv", "2025-09-04")}[year]
    out.update(county="Travis", year=year, source_roll_file=f[0], source_agent_file="", source_protest_file="",
               roll_version_date=f[1])
    seg = dict(county="Travis", year=year, homes_A=out["accounts_cat_A"])
    return out, seg, [], None


def montgomery_prior(year, src_name, ver):
    r = load_cert(WORK / "montgomery" / f"info_{year}_cert.csv.gz")
    out = roll_counts(r)
    homes = set(r.loc[r.cat.eq("A"), "prop_id"])
    rec = r.loc[r.ca_agent_id.ne(""), ["prop_id", "ca_agent_id", "ca_agent_name"]].rename(
        columns={"prop_id": "pID", "ca_agent_id": "agentID", "ca_agent_name": "name"})
    out.update(homes_A_with_agent=len(set(rec.pID) & homes),
               homes_A_ptp_agent=len(set(rec.loc[rec.agentID.isin(PTP["montgomery"]), "pID"]) & homes),
               county="Montgomery", year=year, source_roll_file=src_name,
               source_agent_file=src_name + " (ca_agent_id at certification)", source_protest_file="",
               roll_version_date=ver)
    fr, mapping = firm_rows("montgomery", year, rec[["pID", "agentID"]], homes, None,
                            rec[["agentID", "name"]].drop_duplicates("agentID"))
    seg = dict(county="Montgomery", year=year, homes_A=len(homes), seg_ptp=out["homes_A_ptp_agent"])
    return out, seg, fr, mapping


def ints(df):
    for c in df.columns:
        if c not in ("county", "firm", "agent_ids") and not c.startswith("source_") and c != "roll_version_date":
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    return df


def write(county, results):
    d = WORK / county
    ints(pd.DataFrame([x[0] for x in results]).reindex(columns=M_COLS)).sort_values("year").to_csv(d / "market.csv", index=False)
    ints(pd.DataFrame([x[1] for x in results]).reindex(columns=S_COLS)).sort_values("year").to_csv(d / "segments.csv", index=False)
    ints(pd.DataFrame([r for x in results for r in x[2]]).reindex(columns=F_COLS)).sort_values(["year"], kind="stable").to_csv(
        d / "firms.csv", index=False)
    with open(d / "firm_mapping.txt", "w") as f:
        for x in results:
            if x[3] is not None:
                f.write(f"== {x[0]['year']}\n")
                for firm, ids in x[3].items():
                    f.write(f"{firm}\t{';'.join(ids)}\n")


def main():
    which = sys.argv[1:] or ["travis", "montgomery"]
    for county in which:
        res = []
        o, s, fr, mp, extra = year_2026(county)
        print(county, 2026, o, "\n  extra:", extra)
        res.append((o, s, fr, mp))
        if county == "travis":
            for y in (2024, 2025):
                res.append(travis_prior(y))
        else:
            for y, src, ver in ((2024, "Full Appraisal Export - 2024.zip / APPRAISAL_INFO.TXT", "2024"),
                                (2025, "MCAD_Certified_2025_071626.zip / APPRAISAL_INFO.TXT", "2025-07-16")):
                if (WORK / "montgomery" / f"info_{y}_cert.csv.gz").exists():
                    res.append(montgomery_prior(y, src, ver))
        write(county, res)


if __name__ == "__main__":
    main()
