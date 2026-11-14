"""Dallas scorecard page with the Season setting (same template and rules as build_season_pages.py).

Seasons
    2022-2025  developers' Dallas files (dallas_protests_2022-2024.csv, dallas_protests_2025-2026.csv), value protests only
    2026       output/dallas_values_2026.csv (DCAD ARB_ARCHIVE Jul 20 + ARB_CURRENT Nov 9, roll of Oct 30)

Run:  .venv/bin/python -I "CAD Website/_scorecard_template/season/build_dallas_page.py" <outdir>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_season_pages as bsp  # noqa: E402
import season_data as sd  # noqa: E402

ROOT = bsp.ROOT


def dev_years():
    cols = ["tax_year", "account", "filed_by", "agent_name", "is_ours", "outcome_type", "notice_market_value",
            "final_market_value", "homestead", "neighborhood_code", "state_code", "city", "yr_built", "living_sf",
            "hearing_date", "protest_type"]
    d = pd.concat([pd.read_csv(bsp.DEV / f, dtype=str, keep_default_na=False, usecols=cols)
                   for f in ("Dallas/dallas_protests_2022-2024.csv", "Dallas/dallas_protests_2025-2026.csv")])
    d = d[d.protest_type.eq("Value")].copy()
    d["homestead"] = np.where(d.homestead.eq("1"), "T", "F")
    d["hearing_actual_date"] = ""
    d["neighborhood_code"] = d.neighborhood_code.replace("UNASSIGNED", "")
    d["agent_name"] = d.agent_name.str.strip().replace("UNASSIGNED", "")   # DCAD's "no rep" placeholder
    return [bsp.dev_season(d, y) for y in (2022, 2023, 2024, 2025)]


def y2026():
    v = pd.read_csv(ROOT / "Dallas/output/dallas_values_2026.csv", dtype=str, keep_default_na=False)
    v = v[v.protested.eq("True")]
    firm = v.agent_name.map(bsp.canon)
    A = np.select([v.is_ours.eq("True"), v.agent.ne("") & firm.ne(""), v.agent.ne(""), v.appealedByType.eq("Owner")],
                  [sd.US, firm, sd.OTHER, sd.OWNERS], default=sd.OTHER)
    hd = v.hearing_dt.where(v.hearing_dt.ne("") & ~v.hearing_dt.str.startswith("1900"), v.resolved_dt)
    R = pd.DataFrame({"Y": 2026, "pid": v.account.str.lstrip("0"), "A": A,
                      "sub": np.where(v.stateCd.str.upper().str.startswith("A"), "Residential", "Non-residential"),
                      "HS": v.homestead.eq("True").astype(int), "path": v.path.map({"Informal": "Informal", "ARB": "ARB"}).fillna("Other"),
                      "open": v.path.eq("Open"), "resT": v.path.map(bsp.RES_T).fillna("Other / closed"),
                      "bM": bsp.num(v.notice_value), "fM": bsp.num(v.final_value),
                      "nb": v.nb.replace("UNASSIGNED", ""), "city": v.city, "yrb": v.yrb, "sf": v.sf, "hmon": bsp.month(hd)})
    R.loc[v.check_values.eq("True").values, "fM"] = np.nan
    print(f"  2026: {len(R):,} properties, ours {int((R.A == sd.US).sum()):,}")
    return R


bsp.TEXT["dallas"] = dict(
    name="Dallas", agent="Agent 306 · Dallas CAD (DCAD)", data="Developers' files 2022–2025 · DCAD ARB files Nov 9, 2026",
    years="2022–2026", nb="DCAD neighborhood code", own=True,
    draft="<b>Draft for review.</b> 2022–2025 come from the developers' Dallas protest files (value protests only). 2026 is rebuilt from DCAD's own ARB files (ARB_ARCHIVE of Jul 20 plus ARB_CURRENT of Nov 9) and the Oct 30 roll, so only 2 of our 3,869 2026 protests are still open (the Sep 3 developers' file had 56% open). <b>\"ARB order at the informal value\":</b> DCAD closes most informal offers with an ARB order (resolved code F), so they count as ARB here, as in the developers' file. Details under <a href=\"#method\">Method &amp; open questions</a>.",
    method=["<b>Seasons.</b> 2022–2025: <span class=\"mono\">dallas_protests_2022-2024.csv</span> and <span class=\"mono\">dallas_protests_2025-2026.csv</span> (value protests; exemption protests left out). 2026: <span class=\"mono\">dallas_values_2026.csv</span> from DCAD's ARB_ARCHIVE (Jul 20) and ARB_CURRENT (Nov 9).",
            "<b>Our properties.</b> Protests filed under tax rep 306 (AUTH_TAX_REP_ID).",
            "<b>2026 paths (DCAD codes).</b> RESOLVED F = ARB (final = panel value, else the informal value); WD D = dismissed / no-show; CONSENT P = informal (final = informal value); WD W/P with RESOLVED X = withdrawn; 25.25 motions and exemption-only protests are left out.",
            "<b>Open question.</b> Most Dallas \"ARB\" results are informal offers signed as an ARB order (\"ARB order at the informal offer value\"). They are counted as ARB here, which makes Dallas look ARB-heavy next to other counties."])


if __name__ == "__main__":
    out = Path(sys.argv[1])
    print("== dallas")
    R = pd.concat([bsp.finish(p) for p in dev_years() + [y2026()]], ignore_index=True)
    D = sd.build(R, as_of="2026-11-14")
    (out / "dallas.html").write_text(bsp.page("dallas", D), encoding="utf-8")
    U = {y: D["yearsT"]["any"][str(y)]["us"] for y in D["seasons"]}
    print("  ours by season:", {y: (u["props"], round(u["won"] / u["props"], 3) if u["props"] else None,
                                    round(u["rM"] / u["bM"], 3) if u["bM"] else None) for y, u in U.items()})
    print(f"  wrote {out / 'dallas.html'} ({(out / 'dallas.html').stat().st_size / 1e6:.1f} MB)")
