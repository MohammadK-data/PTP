"""Combine per-county fragments (work/<county>/) into the four deliverables in output/.

  output/county_market.csv, output/county_segments.csv, output/firm_share.csv, output/source_log.md

Runs the checks (homes_A bounds, segment sums, Comptroller survey 2024/2025 within 5%,
PTP 2026 home protests vs. portal counts) and writes them into source_log.md.
Run:  /Users/user2/PTP/.venv/bin/python -I "Market Analysis/etl/assemble.py"
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
WORK, OUT = ROOT / "work", ROOT / "output"
COUNTIES = [("Dallas", "dallas"), ("Denton", "denton"), ("Fort Bend", "fort_bend"), ("Hays", "hays"),
            ("Montgomery", "montgomery"), ("Rockwall", "rockwall"), ("Tarrant", "tarrant"), ("Travis", "travis")]

MARKET = ["county", "year", "total_accounts", "accounts_cat_A", "accounts_cat_B", "accounts_cat_M", "mineral_accounts",
          "homes_A_homestead", "homes_A_with_agent", "homes_A_protested", "homes_A_protested_by_agent",
          "homes_A_protested_by_owner", "homes_A_ptp_agent", "homes_A_ptp_protested", "all_protests",
          "all_agent_protests", "source_roll_file", "source_agent_file", "source_protest_file", "roll_version_date"]
SEG = ["county", "year", "homes_A", "seg_agent", "seg_owner_alone", "seg_lapsed", "seg_never", "seg_lapsed_or_never",
       "seg_ptp"]
FIRM = ["county", "year", "firm", "agent_ids", "homes_A_agent_of_record", "homes_A_protests_filed",
        "all_accounts_agent_of_rec"]
TEXT = {"county", "firm", "agent_ids", "source_roll_file", "source_agent_file", "source_protest_file",
        "roll_version_date"}
PORTAL_2026 = {"Tarrant": 4185, "Denton": 3100, "Travis": 2890, "Fort Bend": 930, "Montgomery": 783, "Hays": 98,
               "Rockwall": 49}


def load(name, cols):
    parts, missing = [], []
    for county, slug in COUNTIES:
        p = WORK / slug / name
        if not p.exists():
            missing.append(county)
            continue
        d = pd.read_csv(p, dtype=str, keep_default_na=False)
        extra = set(d.columns) - set(cols)
        if extra:
            raise SystemExit(f"{p}: unexpected columns {sorted(extra)}")
        for c in cols:
            if c not in d.columns:
                d[c] = ""
        d["county"] = county
        parts.append(d[cols])
    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=cols)
    for c in cols:
        if c not in TEXT:
            v = pd.to_numeric(df[c].str.replace(",", "").str.strip(), errors="coerce")
            df[c] = v.astype("Int64")
    return df, missing


# One name per firm across counties (CADs spell the same firm differently). Keys are upper-cased raw names.
FIRM_CANON = {
    "AMBROSE & ASSOCIATES": "Ambrose & Associates", "AMBROSE AND ASSOCIATES": "Ambrose & Associates",
    "AMBROSE & ASSOC": "Ambrose & Associates",
    "AMERICAN PROPERTY SERVICES LLP": "American Property Services",
    "CBRE GEORGIA": "CBRE",
    "CANDACE RUBIN": "Candace Rubin / Overtaxed", "CANDACE RUBIN / OVERTAXED": "Candace Rubin / Overtaxed",
    "D ALAN BOWLBY & ASSOCIATES": "D Alan Bowlby & Associates", "BOWLBY D ALAN & ASSOC": "D Alan Bowlby & Associates",
    "DOMUTAX": "Domu Tax", "DOMU TAX": "Domu Tax",
    "ELLIOTT-WELLMAN": "Elliott-Wellman", "ELLIOTT WELLMAN": "Elliott-Wellman",
    "ELLIOTT-WELLMAN AD VALOREM TAX CONSULTANTS": "Elliott-Wellman",
    "FIVE STONE PROPERTY TAX": "Five Stone Property Tax", "FIVE STONE TAX ADVISERS": "Five Stone Property Tax",
    "GILL DENSON & COMPANY": "Gill Denson & Company", "GILL DENSON": "Gill Denson & Company",
    "GOODRICH REALTY CONSULTING": "Goodrich Realty Consulting",
    "GOODRICH REALTY CONSULTING (JIM GOODRICH)": "Goodrich Realty Consulting",
    "HAMIL TIFFANY L LAW OFFICE OF": "Law Office of Tiffany Hamil",
    "LAW OFFICE OF TIFFANY HAMIL": "Law Office of Tiffany Hamil",
    "LAW OFFICE OF TIFFANY L HAMIL": "Law Office of Tiffany Hamil",
    "INTEGRATAX PROPERTY TAX SERVICES": "Integratax",
    "K.E. ANDREWS & CO": "KE Andrews & Company", "KE ANDREWS & COMPANY": "KE Andrews & Company",
    "LAW OFFICE O KUSH PATEL": "Law Office of Kush Patel", "THE LAW OFFICE OF KUSH PATEL": "Law Office of Kush Patel",
    "THE LAW OFFICES OF KUSH PATEL": "Law Office of Kush Patel",
    "METROTAX PTC": "Metrotax Property Tax Consultants",
    "METROTAX PROPERTY TAX CONSULTANTS": "Metrotax Property Tax Consultants",
    "OLA TAX & PROPERTY": "Ola Tax & Property", "ROBERT OLA COMPANY  DBA OLA TAX": "Ola Tax & Property",
    "RAINBOLT": "Rainbolt & Alexander", "RAINBOLT ALEXANDER & WILLIAMS": "Rainbolt & Alexander",
    "RESOLUTE PROPERTY TAX SOLUTION": "Resolute Property Tax Solutions",
    "TAXPROTESTMAP": "TaxProtestMap",
    "UPTG": "UPTG (United Paramount Tax Group)", "UPTG SOURCE ADVISORS": "UPTG (United Paramount Tax Group)",
    "UNITED PARAMOUNT TAX GROUP": "UPTG (United Paramount Tax Group)",
    "BRUSNIAK TURNER PC": "Brusniak Turner Fine", "BRUSNIAK TURNER FINE": "Brusniak Turner Fine",
    "CANTRELL MCCULLOCH": "Cantrell McCulloch", "BALLARD PROPERTY TAX PROTEST": "Ballard Property Tax Protest",
}
KEEP_UPPER = {"LLC", "LLP", "PC", "CBRE", "JLL", "UPTG", "PTC", "AIA", "TX", "FW", "LP", "II", "III"}


def canon_firm(name):
    if name in ("Property Tax Protest", "All other agents", "Owners (self-filed)"):
        return name
    key = " ".join(name.upper().split()) if name.upper() != "ROBERT OLA COMPANY  DBA OLA TAX" else name.upper()
    if key in FIRM_CANON or name.upper() in FIRM_CANON:
        return FIRM_CANON.get(key, FIRM_CANON.get(name.upper()))
    if name.isupper():   # Dallas/Tarrant lists are all caps -> same casing as the other counties
        return " ".join(w if w in KEEP_UPPER else w.capitalize() for w in name.split())
    return name


def harmonize_firms(f):
    f = f.copy()
    f["firm"] = f.firm.map(canon_firm)
    f.loc[f.firm.isin(["All other agents", "Owners (self-filed)"]), "agent_ids"] = ""
    num = ["homes_A_agent_of_record", "homes_A_protests_filed", "all_accounts_agent_of_rec"]
    g = f.groupby(["county", "year", "firm"], sort=False)
    out = g.agg({**{c: lambda s: s.sum(min_count=1) for c in num},
                 "agent_ids": lambda s: ";".join(dict.fromkeys(i for v in s for i in v.split(";") if i))})
    out = out.reset_index()
    for c in num:
        out[c] = out[c].astype("Int64")
    return out[FIRM]


def write_csv(df, name):
    df.to_csv(OUT / name, index=False, encoding="utf-8")


def checks(m, s, f):
    out = []
    n = lambda x: pd.notna(x)  # noqa: E731
    out.append("### Internal consistency")
    bad = 0
    for r in m.itertuples(index=False):
        for col in ("homes_A_with_agent", "homes_A_protested", "homes_A_homestead"):
            v = getattr(r, col)
            if n(v) and n(r.accounts_cat_A) and v > r.accounts_cat_A:
                out.append(f"- FAIL {r.county} {r.year}: {col} {v:,} > accounts_cat_A {r.accounts_cat_A:,}"); bad += 1
        if n(r.homes_A_protested) and n(r.homes_A_protested_by_agent) and n(r.homes_A_protested_by_owner):
            if r.homes_A_protested_by_agent + r.homes_A_protested_by_owner > r.homes_A_protested:
                out.append(f"- FAIL {r.county} {r.year}: agent+owner home protests exceed homes_A_protested"); bad += 1
        if n(r.homes_A_ptp_protested) and n(r.homes_A_protested_by_agent) and r.homes_A_ptp_protested > r.homes_A_protested_by_agent:
            out.append(f"- note {r.county} {r.year}: PTP home protests exceed all agent-filed home protests")
    for r in s.itertuples(index=False):
        tail = r.seg_lapsed + r.seg_never if n(r.seg_lapsed) and n(r.seg_never) else r.seg_lapsed_or_never
        if n(r.homes_A) and n(r.seg_agent) and n(r.seg_owner_alone) and n(tail):
            tot = r.seg_agent + r.seg_owner_alone + tail
            if tot != r.homes_A:
                out.append(f"- FAIL {r.county} {r.year}: segments sum {tot:,} != homes_A {r.homes_A:,}"); bad += 1
        mm = m[(m.county == r.county) & (m.year == r.year)]
        if len(mm) and n(r.homes_A) and n(mm.accounts_cat_A.iloc[0]) and r.homes_A != mm.accounts_cat_A.iloc[0]:
            out.append(f"- FAIL {r.county} {r.year}: segments homes_A != market accounts_cat_A"); bad += 1
    out.append(f"- {bad} failures." if bad else "- All bounds and segment sums pass.")

    out.append("\n### Comptroller Appraisal District Operations Survey (Q9.1 protests filed, Q9.3 filed by agents)")
    out.append("| county | year | our all_protests | survey 9.1 | diff | our all_agent_protests | survey 9.3 | diff | flag |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    bench = pd.read_csv(WORK / "comptroller" / "survey_benchmark.csv")
    for b in bench.itertuples(index=False):
        mm = m[(m.county == b.county) & (m.year == b.year)]
        ap = mm.all_protests.iloc[0] if len(mm) else pd.NA
        aa = mm.all_agent_protests.iloc[0] if len(mm) else pd.NA
        d1 = (ap - b.survey_protests_filed) / b.survey_protests_filed if n(ap) else None
        d3 = (aa - b.survey_agent_protests) / b.survey_agent_protests if n(aa) else None
        flag = "no data" if d1 is None and d3 is None else (
            ">5%" if any(x is not None and abs(x) > 0.05 for x in (d1, d3)) else "ok")
        fmt = lambda v: f"{v:,}" if n(v) else "blank"  # noqa: E731
        pct = lambda v: f"{v:+.1%}" if v is not None else ""  # noqa: E731
        out.append(f"| {b.county} | {b.year} | {fmt(ap)} | {b.survey_protests_filed:,} | {pct(d1)} | {fmt(aa)} | "
                   f"{b.survey_agent_protests:,} | {pct(d3)} | {flag} |")

    out.append("\n### PTP 2026 home protests vs. our portal counts")
    out.append("| county | homes_A_ptp_protested | portal count | diff |")
    out.append("|---|---|---|---|")
    for c, k in PORTAL_2026.items():
        mm = m[(m.county == c) & (m.year == 2026)]
        v = mm.homes_A_ptp_protested.iloc[0] if len(mm) else pd.NA
        d = f"{(v - k) / k:+.1%}" if n(v) else ""
        out.append(f"| {c} | {f'{v:,}' if n(v) else 'blank'} | {k:,} | {d} |")
    return "\n".join(out)


def main():
    OUT.mkdir(exist_ok=True)
    m, mm = load("market.csv", MARKET)
    s, sm = load("segments.csv", SEG)
    f, fm = load("firms.csv", FIRM)
    m = m.sort_values(["county", "year"]); s = s.sort_values(["county", "year"])
    f = harmonize_firms(f)
    order = {"Property Tax Protest": 0, "All other agents": 2, "Owners (self-filed)": 3}
    f = f.assign(_o=f.firm.map(order).fillna(1), _n=-f.homes_A_agent_of_record.fillna(-1).astype("float"))
    f = f.sort_values(["county", "year", "_o", "_n"]).drop(columns=["_o", "_n"])
    write_csv(m, "county_market.csv"); write_csv(s, "county_segments.csv"); write_csv(f, "firm_share.csv")

    log = ["# Source log: PTP property tax protest market analysis",
           "",
           "Built from each appraisal district's own bulk files. Counts are unique accounts unless a column says otherwise.",
           "Blank cells mean the source was not published or not available. Nothing is estimated.",
           "Scripts: `Market Analysis/etl/` (one per county plus `assemble.py`). Intermediate files: `Market Analysis/work/`.",
           ""]
    if mm or sm or fm:
        log.append(f"**Missing fragments:** market {mm}, segments {sm}, firms {fm}\n")
    rf = WORK / "READ_FIRST.md"
    if rf.exists():
        log.append(rf.read_text(encoding="utf-8").strip() + "\n")
    log.append("## Checks\n")
    log.append(checks(m, s, f))
    log.append("\nComptroller files: https://comptroller.texas.gov/taxes/property-tax/docs/operations-survey-data-2024.xlsx "
               "and -2025.xlsx (sheet 9, Protests).\n")
    for county, slug in COUNTIES:
        p = WORK / slug / "notes.md"
        txt = p.read_text(encoding="utf-8").strip() if p.exists() else "_No notes produced._"
        if not txt.startswith("## "):
            log.append(f"\n## {county}\n")
        log.append("\n" + txt)
    (OUT / "source_log.md").write_text("\n".join(log) + "\n", encoding="utf-8")
    print(checks(m, s, f))


if __name__ == "__main__":
    main()
