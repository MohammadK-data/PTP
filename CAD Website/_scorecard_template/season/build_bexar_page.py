"""Bexar scorecard page with the Season setting (same template and rules as build_season_pages.py).

Seasons 2022-2026 all come from output/bexar_seasons.csv.gz (bexar_values_build.py: BCAD agent export ARB file,
Oct 26 2026, value protests only, one row per property per season). We have Bexar protests in 2026 only.

Run:  .venv/bin/python -I "CAD Website/_scorecard_template/season/build_bexar_page.py" <outdir>
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


def seasons():
    a = pd.read_csv(ROOT / "Bexar/output/bexar_seasons.csv.gz", dtype=str, keep_default_na=False)
    firm = a.agent_name.map(bsp.canon)
    A = np.select([a.ours.eq("True"), firm.ne(""), a.prot_by_type.isin(["AG", "ANR"]), a.prot_by_type.eq("OW")],
                  [sd.US, firm, sd.OTHER, sd.OWNERS], default=sd.OTHER)
    R = pd.DataFrame({"Y": a.year.astype(int), "pid": a.prop_id, "A": A,
                      "sub": np.where(a.state_cd.str.upper().str.startswith("A"), "Residential", "Non-residential"),
                      "HS": a.HS.astype(int), "path": a.path.map({"Informal": "Informal", "ARB": "ARB"}).fillna("Other"),
                      "open": a.path.eq("Open"), "resT": a.resT, "bM": bsp.num(a.bM), "fM": bsp.num(a.fM),
                      "nb": a.hood_cd, "city": a.city, "yrb": a.yrb, "sf": a.sf, "hmon": bsp.num(a.hmon)})
    for y, d in R.groupby("Y"):
        print(f"  {y}: {len(d):,} properties, ours {int((d.A == sd.US).sum()):,}")
    return [R]


bsp.TEXT["bexar"] = dict(
    name="Bexar", agent="Agent 3619474 · Bexar Appraisal District (BCAD)", data="BCAD agent export Oct 26, 2026 · appraisal export Oct 15",
    years="2022–2026", nb="BCAD neighborhood code", own=True,
    draft="<b>Draft for review.</b> Every season comes from BCAD's own agent export (Oct 26, 2026): its ARB file lists every protest back to 1998 with filer, agent, status and starting and final market value. Value protests only. <b>We had no Bexar protests before 2026:</b> agent 3619474 first appears on 2026 protests, so 2022–2025 show the market only. Only 439 of 181,187 2026 protests are still open. Details under <a href=\"#method\">Method &amp; open questions</a>.",
    method=["<b>Source.</b> <span class=\"mono\">FID_ARBExport.txt</span> in BCAD's 2026 agent export (Oct 26), the PACS ProTax ARB layout. Value protests only (type 25PROT); exemption, 25.25, litigation and arbitration filings are left out. Year built and size from <span class=\"mono\">FID_PropDataExport.txt</span>; agents of record, owner and address from the Oct 15 appraisal export.",
            "<b>Our properties.</b> Protests filed under agent \"PROPERTY TAX PROTEST\" (BCAD agent 3619474). 60800 is an older ID with no protests in 2022–2026. 565 properties list us on the Oct 15 roll; 550 were protested by us in 2026.",
            "<b>Status codes (BCAD list).</b> Informal = value agreements (VA, EVA, VANC, VASP) and pre-arbitration settlements; Formal ARB = board orders (ORD.A / ORD.D, including bulk-affidavit orders); No-show = PFNS; Withdrawn = PFWD; Other = no jurisdiction (ORD-NJ), 25.25 motions, litigation; DELDUP duplicates dropped.",
            "<b>Firms.</b> The ARB file names the filing agent but not its ID, so firms are grouped by name."])


if __name__ == "__main__":
    out = Path(sys.argv[1])
    print("== bexar")
    R = pd.concat([bsp.finish(p) for p in seasons()], ignore_index=True)
    D = sd.build(R, as_of="2026-11-16")
    D["bookflow"], D["lost"] = None, None          # no Bexar clients before 2026
    (out / "bexar.html").write_text(bsp.page("bexar", D), encoding="utf-8")
    U = {y: D["yearsT"]["any"][str(y)]["us"] for y in D["seasons"]}
    print("  ours by season:", {y: (u["props"], round(u["won"] / u["props"], 3) if u["props"] else None,
                                    round(u["rM"] / u["bM"], 3) if u["bM"] else None) for y, u in U.items()})
    print(f"  wrote {out / 'bexar.html'} ({(out / 'bexar.html').stat().st_size / 1e6:.1f} MB)")
