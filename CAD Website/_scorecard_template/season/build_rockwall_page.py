"""Rockwall scorecard page with the Season setting (same template and rules as build_season_pages.py).

Seasons
    2023-2025  developers' Rockwall file (rockwall_protests_2023-2026.csv). We had no Rockwall clients before 2026
               (agent 1044073 is on RCAD's agent list, but no property lists it and no protest is filed under it).
    2026       output/rockwall_values_2026.csv (developers' 2026 rows + RCAD May 26 / Oct 9 exports)

Run:  .venv/bin/python -I "CAD Website/_scorecard_template/season/build_rockwall_page.py" <outdir>
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
    d = bsp.read_dev("Rockwall/rockwall_protests_2023-2026.csv")
    for c in ("hearing_actual_date", "hearing_date"):
        if c not in d:
            d[c] = ""
    return [bsp.dev_season(d, y) for y in (2023, 2024, 2025)]


def y2026():
    v = pd.read_csv(ROOT / "Rockwall/output/rockwall_values_2026.csv", dtype=str, keep_default_na=False)
    v = v[v.protested.eq("True")]
    firm = v.agent_name.map(bsp.canon)
    A = np.select([v.is_ours.eq("True"), v.agent.ne("") & firm.ne(""), v.agent.ne(""), v.appealedByType.eq("Owner")],
                  [sd.US, firm, sd.OTHER, sd.OWNERS], default=sd.OTHER)
    R = pd.DataFrame({"Y": 2026, "pid": v.pID.str.lstrip("0"), "A": A,
                      "sub": np.where(v.stateCd.str.upper().str.startswith("A"), "Residential", "Non-residential"),
                      "HS": v.homestead.eq("True").astype(int),
                      "path": v.path.map({"Informal": "Informal", "ARB": "ARB"}).fillna("Other"),
                      "open": v.path.eq("Open"), "resT": v.path.map(bsp.RES_T).fillna("Other / closed"),
                      "bM": bsp.num(v.notice_value), "fM": bsp.num(v.final_value), "nb": v.nb, "city": v.city,
                      "yrb": v.yrb, "sf": v.sf, "hmon": bsp.month(v.hearing_dt)})
    R.loc[v.check_values.eq("True").values, "fM"] = np.nan
    print(f"  2026: {len(R):,} properties, ours {int((R.A == sd.US).sum()):,}")
    return R


bsp.TEXT["rockwall"] = dict(
    name="Rockwall", agent="Agent 1044073 · Rockwall CAD (RCAD)", data="Developers' file Oct 14 · RCAD exports May 26 + Oct 9",
    years="2023–2026", nb="RCAD neighborhood code", own=True,
    draft="<b>Draft for review.</b> Every season comes from the developers' Rockwall protest file (Oct 14); RCAD publishes no protest list of its own. <b>We had no Rockwall clients before 2026:</b> agent 1044073 has been on RCAD's agent list since 2023, but no property lists it and no protest was filed under it until 2026, so 2023–2025 show the market only. <b>Small book:</b> 36 properties in 2026, so our rates move a lot with a few cases. Details under <a href=\"#method\">Method &amp; open questions</a>.",
    method=["<b>Seasons.</b> 2023–2026: <span class=\"mono\">rockwall_protests_2023-2026.csv</span> (developers, Oct 14). 2026 agents of record, address and owner from RCAD's May 26 and Oct 9 exports (rockwallcad.com/data-exports).",
            "<b>Our properties.</b> Protests filed under agent 1044073 (PROPERTY TAX PROTEST). 1044084 is a dead duplicate (\"DO NOT USE\"); Ballard Property Tax Protest (1114733) is another firm.",
            "<b>Our client list.</b> 43 properties list us as agent on the May or Oct export; 41 were protested in 2026, 36 of them by us. The agent portal shows 49, so a few clients are not linked to 1044073 in RCAD's data.",
            "<b>Earlier seasons.</b> 2023–2025 have no Property Tax Protest rows, so our lines in the explorer, year-over-year and book sections start in 2026."])


if __name__ == "__main__":
    out = Path(sys.argv[1])
    print("== rockwall")
    R = pd.concat([bsp.finish(p) for p in dev_years() + [y2026()]], ignore_index=True)
    D = sd.build(R, as_of="2026-11-14")
    D["bookflow"], D["lost"] = None, None          # no Rockwall clients before 2026
    (out / "rockwall.html").write_text(bsp.page("rockwall", D), encoding="utf-8")
    U = {y: D["yearsT"]["any"][str(y)]["us"] for y in D["seasons"]}
    print("  ours by season:", {y: (u["props"], round(u["won"] / u["props"], 3) if u["props"] else None,
                                    round(u["rM"] / u["bM"], 3) if u["bM"] else None) for y, u in U.items()})
    print(f"  wrote {out / 'rockwall.html'} ({(out / 'rockwall.html').stat().st_size / 1e6:.1f} MB)")
