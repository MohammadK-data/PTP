"""Dallas (DCAD) market fragment: work/dallas/{market,segments,firms}.csv.

Sources (CAD Website/Dallas/Data):
  roll 2026  DCAD2026_CURRENT/ (dallascad.org "DCAD2026_CURRENT.ZIP", downloaded 2026-10-30)
             + 157 accounts only in DCAD2026_CERTIFIED_07232026/
             + 2026-protested accounts missing from both 2026 files (still under protest when exported) taken
               from DCAD2027_CURRENT/ (state code, tax rep, homestead as shown there)
  roll 2025/2024  dcad_download_20261114/DCAD2025_CURRENT/, DCAD2024_CURRENT/ (final rolls for those years)
  protests   dcad_download_20261114/ARB_CURRENT/ARB_CURRENT.csv (2026) and ARB_ARCHIVE/ (earlier years)
  tax rep    ACCOUNT_APPRL_YEAR.TAXPAYER_REP ("<rep id> <name>"), no appointment dates; PTP = 306.

Run: /Users/user2/PTP/.venv/bin/python -I "Market Analysis/etl/dallas_market.py"
"""
import glob
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/user2/PTP")
D = ROOT / "CAD Website" / "Dallas" / "Data"
DL = D / "dcad_download_20261114"
OUT = ROOT / "Market Analysis" / "work" / "dallas"
OUT.mkdir(parents=True, exist_ok=True)
PTP = "306"
BLANK_REP = {"UNASSIGNED", "NONE", "0", "000"}
ROLL_COLS = ["ACCOUNT_NUM", "APPRAISAL_YR", "DIVISION_CD", "TAXPAYER_REP", "SPTD_CODE"]

BRANDS = [
    (r"^PROPERTY TAX PROTEST\b", "Property Tax Protest"), (r"OWNWELL", "Ownwell"), (r"\bRYAN\b", "Ryan LLC"),
    (r"O ?'?CONNOR", "O'Connor & Associates"), (r"RESOLUTE PROPERTY TAX", "Resolute Property Tax Solution"),
    (r"RAY TAX GROUP", "The Ray Tax Group"), (r"SOUTHLAND PROPERTY TAX", "Southland Property Tax Consultants"),
    (r"^TEXAS TAX PROTEST", "Texas Tax Protest"), (r"PEYCO", "Peyco Southwest Realty"),
    (r"PROPERTY TAX LOCK", "Property Tax Lock"), (r"INTEGRATAX", "Integratax"),
    (r"NORTH TEXAS PROPERTY TAX", "North Texas Property Tax Services"), (r"TEXAS PROTAX", "Texas ProTax"),
    (r"TEXAS PROPERTY TAX REDUCTIONS", "Texas Property Tax Reductions"), (r"POPP HUTCHESON", "Popp Hutcheson"),
    (r"KROLL", "Kroll"), (r"POER", "Marvin F. Poer"), (r"DUCHARME", "DuCharme McMillen"),
    (r"GOODRICH REALTY", "Goodrich Realty Consulting"), (r"CANTRELL MCCULLOCH", "Cantrell McCulloch"),
    (r"GILL DENSON", "Gill Denson & Company"), (r"CHANDLER CROUCH", "Chandler Crouch"),
    (r"RUBIN CANDACE|CANDACE RUBIN|OVERTAXED", "Candace Rubin / Overtaxed"), (r"HEGWOOD", "Hegwood Group"),
    (r"ANDREWS K ?E|K ?E ANDREWS", "K.E. Andrews & Co"), (r"FIVE STONE", "Five Stone Tax Advisers"),
]


def firm_of(name, rid):
    n = re.sub(r"\s+", " ", str(name or "").upper().replace(".", "").replace(",", "")).strip()
    for pat, f in BRANDS:
        if re.search(pat, n):
            return f
    if not n:
        return f"Tax rep {rid}"
    return re.sub(r"\b(LLC|INC|LP|LTD|CORP|CO|PLLC|DA|ATTN.*)\b", "", n).strip()


def read(path, cols):
    return pd.read_csv(path, dtype=str, keep_default_na=False, usecols=cols, encoding="latin-1")


def load_dir(d):
    r = read(d / "ACCOUNT_APPRL_YEAR.CSV", ROLL_COLS)
    e = read(d / "APPLIED_STD_EXEMPT.CSV", ["ACCOUNT_NUM", "HOMESTEAD_EFF_DT"])
    hs = set(e.ACCOUNT_NUM[e.HOMESTEAD_EFF_DT.str.strip().ne("")])
    r["hs"] = r.ACCOUNT_NUM.isin(hs)
    r["rep"] = r.TAXPAYER_REP.str.strip().str.split(n=1).str[0].fillna("")
    r.loc[r.rep.str.upper().isin(BLANK_REP), "rep"] = ""
    r["rep_name"] = r.TAXPAYER_REP.str.strip().str.split(n=1).str[1].fillna("")
    r["sc"] = r.SPTD_CODE.str.strip().str.upper()
    return r


def roll(year, prot_accts):
    if year == 2026:
        cur = load_dir(D / "DCAD2026_CURRENT")
        cert = load_dir(D / "DCAD2026_CERTIFIED_07232026")
        r = pd.concat([cur, cert[~cert.ACCOUNT_NUM.isin(set(cur.ACCOUNT_NUM))]])
        n_cert_only = len(r) - len(cur)
        miss = prot_accts - set(r.ACCOUNT_NUM)
        nxt = load_dir(D / "DCAD2027_CURRENT")
        add = nxt[nxt.ACCOUNT_NUM.isin(miss)]
        r = pd.concat([r, add])
        info = dict(cert_only=n_cert_only, from_2027=len(add), protested_not_found=len(miss) - len(add))
        src = "DCAD2026_CURRENT.ZIP (+DCAD2026_CERTIFIED_07232026.zip, +DCAD2027_CURRENT.ZIP for accounts under protest)"
        date = "2026-10-30 (current roll download); certified 2026-07-23"
    else:
        d = DL / f"DCAD{year}_CURRENT"
        r = load_dir(d)
        miss = prot_accts - set(r.ACCOUNT_NUM)
        info = dict(protested_not_found=len(miss))
        src = f"DCAD{year}_CURRENT.ZIP"
        date = "2026-11-14 (download of final roll)"
    assert r.ACCOUNT_NUM.is_unique
    return r, src, date, info


def arb():
    files = [DL / "ARB_CURRENT" / "ARB_CURRENT.csv"] + [DL / "ARB_ARCHIVE" / "ARB_ARCHIVE.CSV"]
    cols = ["PROTEST_YR", "ACCOUNT_NUM", "OWNER_PROTEST_IND", "PROTEST_RCVD_CDX", "AUTH_TAX_REP_ID",
            "P2525C1_IND", "P2525D_IND", "P2525H_IND", "P2525C2_IND", "P2525C3_IND", "P2525B_IND"]
    parts = []
    for f in files:
        h = pd.read_csv(f, nrows=0, encoding="latin-1").columns
        a = read(f, [c for c in cols if c in h])
        a["file"] = f.name
        parts.append(a)
    a = pd.concat(parts).fillna("N")
    a = a.drop_duplicates(subset=[c for c in a.columns if c != "file"])
    flags = [c for c in a.columns if c.startswith("P2525")]
    a["is_2525"] = a[flags].eq("Y").any(axis=1)
    a["exempt"] = a.PROTEST_RCVD_CDX.eq("X")
    a["valid"] = ~a.is_2525 & ~a.exempt
    a["rep"] = a.AUTH_TAX_REP_ID.str.strip()
    a.loc[a.rep.str.upper().isin(BLANK_REP), "rep"] = ""
    a["agent_filed"] = a.OWNER_PROTEST_IND.eq("N")
    a["year"] = a.PROTEST_YR.astype(int)
    return a, files


def main():
    a, files = arb()
    print("ARB rows by year (all / valid):")
    print(a.groupby("year").agg(rows=("valid", "size"), valid=("valid", "sum"), accts=("ACCOUNT_NUM", "nunique")))
    years = [y for y in (2024, 2025, 2026) if y == 2026 or (DL / f"DCAD{y}_CURRENT").exists()]
    market, segs, firms, notes, rep_names = [], [], [], {}, {}
    for y in years:
        p = a[(a.year == y) & a.valid]
        r, rsrc, rdate, info = roll(y, set(p.ACCOUNT_NUM))
        for rid, nm in zip(r.rep, r.rep_name):
            if rid and nm:
                rep_names.setdefault(rid, nm)
        A = set(r.ACCOUNT_NUM[r.sc.str.startswith("A")])
        roll_rep = r.set_index("ACCOUNT_NUM").rep
        prot_rep = p[p.rep.ne("")].groupby("ACCOUNT_NUM").rep.agg(lambda s: set(s))
        # agent of record = roll tax rep, plus any rep named on that year's protest
        recs = {}
        for acct, rid in roll_rep[roll_rep.ne("")].items():
            recs.setdefault(acct, set()).add(rid)
        for acct, s in prot_rep.items():
            recs.setdefault(acct, set()).update(s)
        with_agent = set(recs)
        pa = p.groupby("ACCOUNT_NUM").agent_filed.any()
        protested = set(pa.index)
        agent_filed = set(pa.index[pa])
        owner_only = protested - agent_filed
        ptp_rec = {k for k, s in recs.items() if PTP in s}
        ptp_prot = set(p.ACCOUNT_NUM[p.rep.eq(PTP) & p.agent_filed])
        market.append(dict(
            county="Dallas", year=y, total_accounts=len(r), accounts_cat_A=len(A),
            accounts_cat_B=int(r.sc.str.startswith("B").sum()), accounts_cat_M=int(r.sc.str.startswith("M").sum()),
            mineral_accounts=int(r.sc.str.startswith("G").sum()), homes_A_homestead=int(r.hs[r.sc.str.startswith("A")].sum()),
            homes_A_with_agent=len(A & with_agent), homes_A_protested=len(A & protested),
            homes_A_protested_by_agent=len(A & agent_filed), homes_A_protested_by_owner=len(A & owner_only),
            homes_A_ptp_agent=len(A & ptp_rec), homes_A_ptp_protested=len(A & ptp_prot),
            all_protests=len(protested), all_agent_protests=len(agent_filed),
            source_roll_file=rsrc, source_agent_file=f"{rsrc.split(' ')[0]} ACCOUNT_APPRL_YEAR.TAXPAYER_REP + ARB AUTH_TAX_REP_ID",
            source_protest_file="ARB_ARCHIVE.zip (to 2026-07-20) + ARB_CURRENT.zip (2026-11-09)" if y == 2026 else "ARB_ARCHIVE.zip",
            roll_version_date=rdate))
        hist = set(a.ACCOUNT_NUM[a.valid & a.year.between(2022, y - 1)])
        hist_years = sorted(set(a.year[a.valid & a.year.between(2022, y - 1)]))
        rest = A - with_agent - owner_only
        seg = dict(county="Dallas", year=y, homes_A=len(A), seg_agent=len(A & with_agent),
                   seg_owner_alone=len(A & owner_only - with_agent), seg_ptp=len(A & ptp_rec))
        if hist_years:
            seg.update(seg_lapsed=len(rest & hist), seg_never=len(rest - hist), seg_lapsed_or_never="")
        else:
            seg.update(seg_lapsed="", seg_never="", seg_lapsed_or_never=len(rest))
        assert seg["seg_agent"] + seg["seg_owner_alone"] + len(rest) == len(A)
        segs.append(seg)
        notes[y] = dict(info=info, hist_years=hist_years, cases=len(p), owner_filed_with_rep_on_roll=len(A & owner_only & with_agent))
        # firms
        rows = [(acct, rid) for acct, s in recs.items() for rid in s]
        fr = pd.DataFrame(rows, columns=["acct", "rid"])
        fr["firm"] = [PTP_FIRM if rid == PTP else firm_of(rep_names.get(rid, ""), rid) for rid in fr.rid]
        pf = p[p.agent_filed & p.rep.ne("")][["ACCOUNT_NUM", "rep"]].rename(columns={"ACCOUNT_NUM": "acct", "rep": "rid"})
        pf["firm"] = [PTP_FIRM if rid == PTP else firm_of(rep_names.get(rid, ""), rid) for rid in pf.rid]
        home_rec = fr[fr.acct.isin(A)].groupby("firm").acct.nunique()
        home_prot = pf[pf.acct.isin(A)].groupby("firm").acct.nunique()
        all_rec = fr.groupby("firm").acct.nunique()
        ids = fr.groupby("firm").rid.agg(lambda s: ";".join(sorted(set(s))))
        big = [f for f in home_rec.index if home_rec[f] >= 100] + ([PTP_FIRM] if PTP_FIRM not in home_rec.index or home_rec[PTP_FIRM] < 100 else [])
        for f in sorted(big, key=lambda f: -home_rec.get(f, 0)):
            firms.append(dict(county="Dallas", year=y, firm=f, agent_ids=ids.get(f, PTP),
                              homes_A_agent_of_record=int(home_rec.get(f, 0)), homes_A_protests_filed=int(home_prot.get(f, 0)),
                              all_accounts_agent_of_rec=int(all_rec.get(f, 0))))
        o, op = fr[~fr.firm.isin(big)], pf[~pf.firm.isin(big)]
        firms.append(dict(county="Dallas", year=y, firm="All other agents", agent_ids="",
                          homes_A_agent_of_record=o[o.acct.isin(A)].acct.nunique(),
                          homes_A_protests_filed=op[op.acct.isin(A)].acct.nunique(), all_accounts_agent_of_rec=o.acct.nunique()))
        firms.append(dict(county="Dallas", year=y, firm="Owners (self-filed)", agent_ids="", homes_A_agent_of_record="",
                          homes_A_protests_filed=len(A & owner_only), all_accounts_agent_of_rec=""))
        print(y, notes[y])
    pd.DataFrame(market).to_csv(OUT / "market.csv", index=False)
    pd.DataFrame(segs)[["county", "year", "homes_A", "seg_agent", "seg_owner_alone", "seg_lapsed", "seg_never",
                        "seg_lapsed_or_never", "seg_ptp"]].to_csv(OUT / "segments.csv", index=False)
    pd.DataFrame(firms).to_csv(OUT / "firms.csv", index=False)
    pd.Series(rep_names).sort_index().to_csv(OUT / "tax_rep_names.csv", header=["name"], index_label="rep_id")
    print(pd.DataFrame(market).T.to_string())
    print(pd.DataFrame(segs).to_string())


PTP_FIRM = "Property Tax Protest"

if __name__ == "__main__":
    main()
