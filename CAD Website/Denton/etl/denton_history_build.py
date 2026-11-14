"""Denton protest history, one row per property per season (2023, 2024, 2026), for the Year-over-year section.

2022 is read but left out: the file holds only ~34K protests (partial), and 24% of our "settled" 2022 cases end
above the notice value (0% in 2023-26), so its begin/final values don't line up with the other years.

Sources
    Data/denton_prior_download/protax_<year>/ProTax_ARBExport.txt   DCAD ARB export, one row per protest
        2022: tab, no header, 78 columns (only ~34K protests: a partial export)
        2023: tab, header;  2024: pipe, header.  Free-text comments sometimes break a row over two lines;
        those pieces are joined back.
    output/denton_values_2026.csv                                    the 2026 scorecard rows
    2025: no protest file in the download (json_2025 is empty), so the season is skipped.

Rules
    Ours = agent ID 245, or agent_name exactly "PROPERTY TAX PROTEST" (2022-23 often omit the ID).
    One protest per property: ours first, then settled > open > no result, then the latest case.
    Notice = begin_market, Final = final_market (market value). Residential = state code A*.
    Status: 0TLC (toplined) / 0ACC (accepted) / 0AGR -> Informal; 1ARB* -> ARB (1ARBNOSHOW -> No-show);
            0WDRAW -> Withdrawn; 0DUPE / 0UNAUTH -> not a protest; anything else with no final value -> Open.

Output: output/denton_history.csv
Run:    .venv/bin/python -I "CAD Website/Denton/etl/denton_history_build.py"
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PRIOR = ROOT / "Data" / "denton_prior_download"
OUT = ROOT / "output"
OUR = "245"
COLS_2022 = {0: "prop_val_yr", 1: "case_id", 2: "prop_id", 5: "state_cd", 6: "prop_type_cd", 11: "agent_name",
             18: "prot_type", 19: "prot_status", 22: "prot_by_type", 58: "begin_market", 72: "final_market"}


def read_rows(path, sep, n):
    """Split on sep; a row with too few fields continues on the next line (newline inside a comment)."""
    rows, buf = [], None
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            line = line.rstrip("\r\n")
            buf = line if buf is None else buf + " " + line
            parts = buf.split(sep)
            if len(parts) >= n:
                rows.append(parts[:n] if len(parts) == n else parts[:n - 1] + [sep.join(parts[n - 1:])])
                buf = None
    return rows


def load(year):
    p = PRIOR / f"protax_{year}" / "ProTax_ARBExport.txt"
    if year == 2022:
        rows = read_rows(p, "\t", 78)
        d = pd.DataFrame([[r[i] for i in COLS_2022] for r in rows], columns=list(COLS_2022.values()))
    else:
        sep = "\t" if year == 2023 else "|"
        with open(p, encoding="utf-8-sig") as f:
            hdr = f.readline().rstrip("\r\n").split(sep)
        rows = read_rows(p, sep, len(hdr))[1:]
        d = pd.DataFrame(rows, columns=[h.strip() for h in hdr])
        d = d.loc[:, ~d.columns.duplicated()]
    d = d.apply(lambda s: s.str.strip())
    d = d[d.prop_val_yr.eq(str(year))]
    print(f"{year}: {len(d):,} protest rows")
    return d


def path_of(st, final):
    if st in ("0DUPE", "0UNAUTH"):
        return "Not a protest"
    if st in ("0TLC", "0ACC", "0AGR"):
        return "Informal"
    if st == "1ARBNOSHOW":
        return "No-show"
    if st.startswith("1ARB") and st not in ("1ARBAFF", "1ARBNOAFF"):
        return "ARB"
    if st == "0WDRAW":
        return "Withdrawn"
    return "Open" if not final > 0 else "Other"


def season(year):
    d = load(year)
    d["agent"] = d.agent_name.str.extract(r"[-(]\s*(\d+)\)?\s*$")[0].fillna("")
    d["firm"] = d.agent_name.str.replace(r"\s*[-(]\s*\d+\)?\s*$", "", regex=True).replace("NULL", "")
    d["notice"] = pd.to_numeric(d.begin_market, errors="coerce")
    d["final"] = pd.to_numeric(d.final_market, errors="coerce")
    d["path"] = [path_of(s, f) for s, f in zip(d.prot_status, d.final)]
    d["rank"] = d.path.map({"Informal": 0, "ARB": 0, "Other": 1, "Open": 1, "No-show": 2, "Withdrawn": 2, "Not a protest": 3})
    d["firm"] = d.firm.str.replace(r"\s+", " ", regex=True).str.strip()
    d["our_row"] = d.agent.eq(OUR) | d.firm.eq("PROPERTY TAX PROTEST")   # 2022-23 often list the name without the ID
    ours = set(d.loc[d.our_row & d["rank"].lt(3), "prop_id"])
    d = d[~d.prop_id.isin(ours) | d.our_row]
    d["case_n"] = pd.to_numeric(d.case_id, errors="coerce")
    p = d.sort_values(["prop_id", "rank", "case_n"], ascending=[True, True, False]).drop_duplicates("prop_id")
    p = p[p.path.ne("Not a protest")].copy()
    p["who"] = np.where(p.our_row, "us", np.where(p.firm.ne(""), "agent",
                        np.where(p.prot_by_type.eq("OW"), "owner", "other")))
    p["firm"] = np.where(p.who.eq("agent"), p.firm, "")
    p.loc[p.path.isin(["No-show", "Withdrawn"]) & ~(p.final > 0), "final"] = p.notice
    p["reduction"] = p.notice - p.final
    p["state"] = np.select([p.path.eq("Open"), ~(p.notice > 0) | ~(p.final > 0), p.final > p.notice * 1.25],
                           ["open", "no_value", "flag"], default="closed")
    out = pd.DataFrame({"year": year, "pid": p.prop_id, "res": p.state_cd.str.upper().str.startswith("A"),
                        "who": p.who, "firm": p.firm, "path": p.path, "notice": p.notice, "final": p.final,
                        "reduction": p.reduction, "state": p.state})
    print(f"  {len(out):,} properties | ours {int(out.who.eq('us').sum()):,} | {out.state.value_counts().to_dict()} | "
          f"{out.path.value_counts().to_dict()}")
    return out


def y2026():
    v = pd.read_csv(OUT / "denton_values_2026.csv", dtype=str, keep_default_na=False)
    v = v[v.protested.eq("True")]
    names = {}
    for s in v.agents_all:
        for nm, k in re.findall(r"([^|]+?) \((\d+)\)", s):
            names.setdefault(k, nm.strip())
    who = np.where(v.is_ours.eq("True"), "us", np.where(v.agent.ne(""), "agent",
                   np.where(v.appealedByType.str.upper().str.startswith("O"), "owner", "other")))
    out = pd.DataFrame({"year": 2026, "pid": v.pID, "res": v.stateCd.str.upper().str.startswith("A"), "who": who,
                        "firm": [names.get(a, "") if w == "agent" else "" for a, w in zip(v.agent, who)],
                        "path": v.path.replace({"Dismissed": "Withdrawn"}),
                        "notice": pd.to_numeric(v.notice_value, errors="coerce"),
                        "final": pd.to_numeric(v.final_value, errors="coerce")})
    out["reduction"] = out.notice - out.final
    out["state"] = np.select([out.path.eq("Open"), v.check_values.eq("True").values], ["open", "flag"], default="closed")
    print(f"2026: {len(out):,} properties | ours {int(out.who.eq('us').sum()):,} | {out.state.value_counts().to_dict()}")
    return out


if __name__ == "__main__":
    h = pd.concat([season(2023), season(2024), y2026()], ignore_index=True)   # 2022 left out, see docstring
    h.to_csv(OUT / "denton_history.csv", index=False)
    print("wrote", OUT / "denton_history.csv", f"{len(h):,}")
