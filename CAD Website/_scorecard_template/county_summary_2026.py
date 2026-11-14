"""How the 2026 season went, us vs. everyone else: <county>_values_2026_summary.csv, same columns as Tarrant's.

Reads CAD Website/<County>/output/<county>_values_2026.csv (built by <county>_values_2026_build.py).

Groups (who): Property Tax Protest (us) / Other agents / Owners / Other appellant, by the filer of the deciding appeal.
RP: propType (R, P, MH, ...), plus "Residential" (state code A*, the scorecards' residential filter) and "ALL".
Rates use closed appeals only and leave out flagged values (check_values), as the scorecards do.

Run:  .venv/bin/python -I "CAD Website/_scorecard_template/county_summary_2026.py" travis montgomery denton
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
COLS = ["pID", "propType", "stateCd", "protested", "is_ours", "appealedByType", "agent", "path",
        "notice_value", "final_value", "reduction", "check_values"]


def summarize(county):
    src = ROOT / county.capitalize() / "output" / f"{county}_values_2026.csv"
    v = pd.read_csv(src, dtype=str, keep_default_na=False, usecols=COLS)
    p = v[v.protested.eq("True")].copy()
    for c in ["notice_value", "final_value", "reduction"]:
        p[c] = pd.to_numeric(p[c], errors="coerce")
    p["flag"] = p.check_values.eq("True")
    p["who"] = np.where(p.is_ours.eq("True"), "Property Tax Protest (us)",
                        np.where(p.agent.ne(""), "Other agents",
                                 np.where(p.appealedByType.str.upper().str.startswith("O") & ~p.appealedByType.str.upper().eq("OTH"),
                                          "Owners", "Other appellant")))
    p["pct"] = (p.reduction / p.notice_value).where(p.notice_value > 0)
    segs = [(rp, p[p.propType.eq(rp)]) for rp in sorted(p.propType.unique())]
    segs += [("Residential", p[p.stateCd.str.startswith("A")]), ("ALL", p)]
    rows = []
    for rp, s in segs:
        for who, d in s.groupby("who"):
            closed = d[~d.path.eq("Open") & ~d.flag]
            nv = closed.notice_value.sum()
            rows.append({
                "who": who, "RP": rp, "accounts": len(d), "open": int(d.path.eq("Open").sum()),
                "flagged_values": int(d.flag.sum()), "closed_with_result": len(closed),
                "reduced": int((closed.reduction > 0).sum()),
                "win_rate": (closed.reduction > 0).mean() if len(closed) else np.nan,
                "informal": int(d.path.eq("Informal").sum()), "arb_hearing": int(d.path.eq("ARB").sum()),
                "fta": int(d.path.eq("No-show").sum()), "withdrawn": int(d.path.isin(["Withdrawn", "Dismissed"]).sum()),
                "notice_total": nv, "final_total": closed.final_value.sum(), "reduction_total": closed.reduction.sum(),
                "reduction_pct_of_notice": closed.reduction.sum() / nv if nv else np.nan,
                "avg_reduction_pct": closed.pct.clip(lower=0).mean(), "median_reduction_pct": closed.pct.median(),
            })
    out = pd.DataFrame(rows)
    dst = src.with_name(f"{county}_values_2026_summary.csv")
    out.to_csv(dst, index=False)
    print(f"== {county}: {dst}")
    print(out[out.RP.isin(["ALL", "Residential"])][["who", "RP", "accounts", "open", "closed_with_result", "win_rate",
                                                   "reduction_pct_of_notice", "avg_reduction_pct"]].round(3).to_string(index=False))


if __name__ == "__main__":
    for c in sys.argv[1:] or ["travis", "montgomery", "denton"]:
        summarize(c.lower())
