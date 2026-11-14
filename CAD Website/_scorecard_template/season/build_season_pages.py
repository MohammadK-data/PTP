"""County scorecard pages with the Season setting (the County Scorecards template), one per county.

Seasons and sources (one row per property per season):
    Tarrant     2024 developers' file (tarrant_protests_2024.csv, final value from the 2024 roll where blank)
                2025 developers' file (same rows as the 2025 ARB file, final value from the 2025 roll where blank)
                2026 output/tarrant_values_2026.csv (corrected build)
    Denton      2023-2025 developers' file (denton_protests_2023-2026.csv), 2026 output/denton_values_2026.csv
    Montgomery  2024-2025 developers' file (2023 has no values), 2026 output/montgomery_values_2026.csv
    Travis      2026 output/travis_values_2026.csv (no earlier protest data)
Property traits the 2026 builds lack (Tarrant homestead, neighborhood, year built, size) come from the
developers' 2026 file by account.

Run:  .venv/bin/python -I "CAD Website/_scorecard_template/season/build_season_pages.py" <outdir> [county ...]
Writes <outdir>/<county>.html
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DEV = Path.home() / "Downloads" / "County_Protest_Data"
sys.path.insert(0, str(HERE))
import season_data as sd  # noqa: E402

PATH_OF = {"Informal settlement": "Informal", "ARB hearing": "ARB", "Dismissed / no-show": "Other", "Withdrawn": "Other",
           "Other / closed": "Other"}
RANK = {"Informal": 0, "ARB": 0, "Other": 1}


def canon(name):
    u = re.sub(r"[^A-Z0-9& ]", " ", str(name).upper())
    u = re.sub(r"\s+", " ", u).strip()
    if not u or u in ("NULL",):
        return ""
    if "OWNWELL" in u:
        return sd.OWN
    if u.startswith("RYAN") and "LAW" not in u:
        return "Ryan LLC (all codes)"
    if re.match(r"^O ?CONNOR", u):
        return "O'Connor & Associates"
    if u.startswith("RESOLUTE PROPERTY TAX"):
        return "RESOLUTE PROPERTY TAX SOLUTIONS"
    if "RAY TAX GROUP" in u:
        return "RAY TAX GROUP, THE"
    if u.startswith("TEXAS PROTAX"):
        return "TEXAS PROTAX"
    return re.sub(r"\s+(INC|LLC|L L C|LTD|CO)$", "", u)


def month(s):
    d = pd.to_datetime(s, errors="coerce", format="mixed")
    return d.dt.month


def num(s):
    return pd.to_numeric(s, errors="coerce")


def finish(R):
    R["ok"] = ~R.open & (R.bM > 0) & (R.fM > 0) & ~(R.fM > R.bM * 1.25)
    for c in ("nb", "city", "yrb", "sf"):
        R[c] = R[c].fillna("").astype(str).str.strip()
    R["city"] = R.city.str.upper().str.replace(r"^CITY OF\s+", "", regex=True)
    return R


# ---------------------------------------------------------------- developers' files (earlier seasons)

def dev_season(df, year, roll_final=None):
    d = df[df.tax_year.eq(str(year))].copy()
    d["pid"] = d.account.str.strip().str.lstrip("0")
    d["ours"] = d.is_ours.str.lower().eq("true")
    d["open"] = d.outcome_type.eq("Open / unresolved")
    d["path"] = d.outcome_type.map(PATH_OF).fillna("Other")
    d["bM"], d["fM"] = num(d.notice_market_value), num(d.final_market_value)
    if roll_final is not None:
        d["fM"] = d.fM.where(d.fM > 0, d.pid.map(roll_final))
    d.loc[d.path.eq("Other") & ~(d.fM > 0), "fM"] = d.bM
    d["rk"] = d.path.map(RANK)
    ours = set(d.loc[d.ours, "pid"])
    d = d[~d.pid.isin(ours) | d.ours]
    d = d.sort_values(["pid", "open", "rk", "fM"], ascending=[True, True, True, True]).drop_duplicates("pid")
    fb = d.filed_by.str.upper()
    firm = d.agent_name.map(canon)
    d["A"] = np.select([d.ours, fb.eq("OWNER"), firm.ne("")], [sd.US, sd.OWNERS, firm], default=sd.OTHER)
    hd = d.hearing_actual_date.where(d.hearing_actual_date.ne(""), d.hearing_date)
    R = pd.DataFrame({"Y": year, "pid": d.pid, "A": d.A,
                      "sub": np.where(d.state_code.str.upper().str.startswith("A"), "Residential", "Non-residential"),
                      "HS": d.homestead.eq("T").astype(int), "path": d.path, "open": d.open,
                      "resT": d.outcome_type, "bM": d.bM, "fM": d.fM, "nb": d.neighborhood_code, "city": d.city,
                      "yrb": d.yr_built, "sf": d.living_sf, "hmon": month(hd)})
    print(f"  {year}: {len(R):,} properties, ours {int((R.A == sd.US).sum()):,}, closed with values {int(finish(R.copy()).ok.sum()):,}")
    return R


def read_dev(*files):
    cols = ["tax_year", "account", "filed_by", "agent_name", "is_ours", "outcome_type", "notice_market_value",
            "final_market_value", "homestead", "neighborhood_code", "state_code", "city", "yr_built", "living_sf",
            "hearing_date", "hearing_actual_date"]
    return pd.concat([pd.read_csv(DEV / f, dtype=str, keep_default_na=False, usecols=lambda c: c in cols) for f in files])


# ---------------------------------------------------------------- 2026 corrected builds

RES_T = {"Informal": "Informal settlement", "ARB": "ARB hearing", "No-show": "Dismissed / no-show",
         "Dismissed": "Dismissed / no-show", "Withdrawn": "Withdrawn"}


def json_2026(county):
    v = pd.read_csv(ROOT / county.capitalize() / "output" / f"{county}_values_2026.csv", dtype=str, keep_default_na=False)
    v = v[v.protested.eq("True")]
    names = {}
    for s in v.agents_all:
        for nm, k in re.findall(r"([^|]+?) \((\d+)\)", s):
            names.setdefault(k, nm.strip())
    firm = v.agent.map(lambda a: canon(names.get(a, "")) if a else "")
    A = np.select([v.is_ours.eq("True"), v.agent.ne("") & firm.ne(""), v.agent.ne(""),
                   v.appealedByType.str.upper().str.startswith("O")], [sd.US, firm, sd.OTHER, sd.OWNERS], default=sd.OTHER)
    path = v.path.map({"Informal": "Informal", "ARB": "ARB"}).fillna("Other")
    city = v.situs_city if "situs_city" in v else v.city
    hd = v.formalStartMeeting.where(v.formalStartMeeting.ne(""), v.informalStartMeeting)
    hd = hd.where(hd.ne(""), v.finalizedDt)
    R = pd.DataFrame({"Y": 2026, "pid": v.pID.str.lstrip("0"), "A": A,
                      "sub": np.where(v.stateCd.str.upper().str.startswith("A"), "Residential", "Non-residential"),
                      "HS": v.homestead.eq("True").astype(int), "path": path, "open": v.path.eq("Open"),
                      "resT": v.path.map(RES_T).fillna("Other / closed"), "bM": num(v.notice_value),
                      "fM": num(v.final_value), "nb": v.nb, "city": city, "yrb": v.yrb, "sf": v.sf,
                      "hmon": month(hd.str[:10])})
    R.loc[v.check_values.eq("True").values, "fM"] = np.nan          # flagged values stay out of results
    print(f"  2026: {len(R):,} properties, ours {int((R.A == sd.US).sum()):,}")
    return R


def tarrant_2026():
    v = pd.read_csv(ROOT / "Tarrant/output/tarrant_values_2026.csv", dtype=str, keep_default_na=False)
    v = v[v.protested.eq("True")]
    t = read_dev("Tarrant/tarrant_protests_2026.csv")
    t["pid"] = t.account.str.lstrip("0")
    t = t.drop_duplicates("pid").set_index("pid")
    pid = v.Account_Num.str.lstrip("0")
    firm = v.AppellantName.map(canon)
    A = np.select([v.is_ours.eq("True"), v.AppellantType.eq("Agent") & firm.ne(""), v.AppellantType.eq("Agent"),
                   v.AppellantType.eq("Owner")], [sd.US, firm, sd.OTHER, sd.OWNERS], default=sd.OTHER)
    pmap = {"Informal (joint motion)": "Informal", "ARB hearing": "ARB"}
    rmap = {"Informal (joint motion)": "Informal settlement", "ARB hearing": "ARB hearing",
            "Failure to appear": "Dismissed / no-show", "Withdrawn / dismissed": "Withdrawn"}
    sc = v.State_Use_Code.where(v.State_Use_Code.ne(""), pid.map(t.state_code).fillna(""))
    hd = v.ScheduledHearingDate.where(v.ScheduledHearingDate.ne(""), v.finalizedDt)
    R = pd.DataFrame({"Y": 2026, "pid": pid, "A": A,
                      "sub": np.where(sc.str.upper().str.startswith("A"), "Residential", "Non-residential"),
                      "HS": pid.map(t.homestead).eq("T").astype(int), "path": v.path.map(pmap).fillna("Other"),
                      "open": v.path.eq("Open"), "resT": v.path.map(rmap).fillna("Other / closed"),
                      "bM": num(v.notice_value), "fM": num(v.final_value), "nb": pid.map(t.neighborhood_code),
                      "city": pid.map(t.city), "yrb": pid.map(t.yr_built), "sf": pid.map(t.living_sf),
                      "hmon": month(hd.str[:10])})
    R.loc[v.check_values.eq("True").values, "fM"] = np.nan
    print(f"  2026: {len(R):,} properties, ours {int((R.A == sd.US).sum()):,}")
    return R


def tarrant_roll(year):
    cache = ROOT / "Tarrant/output" / f"tarrant_roll_values_{year}.csv"
    if not cache.exists():
        sys.path.insert(0, str(ROOT / "Tarrant/etl"))
        import tarrant_arb_values_2026 as t
        r = t.dedup_roll(t.load_roll(t.DATA / f"PropertyData_{year}.txt"))
        pd.DataFrame({"pid": r.Account_Num.str.lstrip("0"), "value": num(r.Total_Value)}).to_csv(cache, index=False)
    r = pd.read_csv(cache, dtype={"pid": str})
    return r.set_index("pid").value


# ---------------------------------------------------------------- counties

def tarrant():
    parts = []
    for y in (2024, 2025):
        parts.append(dev_season(read_dev(f"Tarrant/tarrant_protests_{y}.csv"), y, tarrant_roll(y)))
    parts.append(tarrant_2026())
    return parts


def denton():
    d = read_dev("Denton/denton_protests_2023-2026.csv")
    return [dev_season(d, y) for y in (2023, 2024, 2025)] + [json_2026("denton")]


def montgomery():
    d = read_dev("Montgomery/montgomery_protests_2023-2026.csv")
    return [dev_season(d, y) for y in (2024, 2025)] + [json_2026("montgomery")]


def travis():
    return [json_2026("travis")]


# ---------------------------------------------------------------- page text

TEXT = {
    "tarrant": dict(
        name="Tarrant", agent="Agent 1487 (795 in 2024) · Tarrant Appraisal District (TAD)",
        data="ARB files 2024–2026 · 2024–25 rolls", years="2024–2026", nb="TAD neighborhood code", own=True,
        draft="<b>Draft for review.</b> 2024 and 2025 come from the developers' Tarrant files (the TAD ARB records); TAD leaves the final value blank on most joint-motion settlements, so it is taken from that season's certified roll. 2026 is the corrected build (one case per account, values checked against the agent portal export). <b>2025 notice values:</b> TAD left the notice value blank on about half of the 2025 cases, so 2025 results cover the 1,099 of our 2,235 protests (and the same share of everyone else's) that have one. Details under <a href=\"#method\">Method &amp; open questions</a>.",
        method=["<b>Seasons.</b> 2024 and 2025: developers' files <span class=\"mono\">tarrant_protests_2024.csv</span> / <span class=\"mono\">_2025.csv</span>. 2026: <span class=\"mono\">tarrant_values_2026.csv</span> from the Oct 19 ARB file and the 2026 roll.",
                "<b>Our properties.</b> Agent 795 in 2024 (plus cases filed under the name \"Property Tax Protest\"), agent 1487 in 2025 and 2026.",
                "<b>Final value.</b> The case's final market value; where TAD left it blank (most joint motions) the season's certified roll value is used.",
                "<b>Notice value.</b> The case's notice market value. Blank on about half of the 2025 cases (equally for us and other agents); those properties count as protested but stay out of rates and dollars.",
                "<b>Joint motions.</b> \"Withdrawn by joint motion 41.47(g-1)\" closes a settled joint motion after the season and counts as informal."]),
    "denton": dict(
        name="Denton", agent="Agent 245 · Denton CAD (DCAD)", data="Developers' file 2023–2025 · protax JSON 2026",
        years="2023–2026", nb="Denton CAD neighborhood code", own=True,
        draft="<b>Draft for review.</b> 2023–2025 come from the developers' Denton file (Oct 13, one row per protest). 2026 is the protax JSON build (Jul 27) with the Oct 14 export for appeals still open then. Our 2023 protests often carry the name \"Property Tax Protest\" without the ID; both count. Details under <a href=\"#method\">Method &amp; open questions</a>.",
        method=["<b>Seasons.</b> 2023–2025: <span class=\"mono\">denton_protests_2023-2026.csv</span>. 2026: <span class=\"mono\">denton_values_2026.csv</span> (protax JSON + Oct 14 export).",
                "<b>Our properties.</b> Any protest filed under 245 that season (or the name \"Property Tax Protest\" where the ID is blank).",
                "<b>TopLine.</b> TOPLINED settlements count as informal.",
                "<b>Look-alike names.</b> Ballard, Smart Value and Camel Texas \"… Property Tax Protest\" are other firms."]),
    "montgomery": dict(
        name="Montgomery", agent="Agent 654513 · Montgomery CAD (MCAD)", data="Developers' file 2024–2025 · protax JSON 2026",
        years="2024–2026", nb="MCAD neighborhood code", own=True,
        draft="<b>Draft for review.</b> 2024 and 2025 come from the developers' Montgomery file. 2023 is left out: that season has no notice or final values in the file. 2026 is the protax JSON build (Aug 4) with the certified roll for appeals still open then. Details under <a href=\"#method\">Method &amp; open questions</a>.",
        method=["<b>Seasons.</b> 2024–2025: <span class=\"mono\">montgomery_protests_2023-2026.csv</span> (2023 has no values, so it is not shown). 2026: <span class=\"mono\">montgomery_values_2026.csv</span>.",
                "<b>Our properties.</b> Protests filed under agent 654513 that season.",
                "<b>Open status codes.</b> C, DP, AC and HD.NAA in 2026 are still unconfirmed."]),
    "travis": dict(
        name="Travis", agent="Agent 1863738 · Travis CAD (TCAD)", data="Protax JSON Oct 6 · certified roll Oct 6",
        years="2026", nb="TCAD market area", own=True,
        draft="<b>Draft for review.</b> 2026 only: the Travis downloads (EARS 2024 and 2025) are value rolls with no protest or agent fields, so there are no earlier seasons to compare. Ours = agent 1863738, 1898343 or 1898284. Details under <a href=\"#method\">Method &amp; open questions</a>.",
        method=["<b>Season.</b> 2026 from the protax JSON (Oct 6), certified roll for missing values.",
                "<b>Earlier seasons.</b> Not available: the EARS files have values only, no protests or agents.",
                "<b>Which agent IDs are ours?</b> 1863738, 1898343 and 1898284 are counted; 1897915 (\"AKA Watchtower\") is not."]),
}
COMMON_METHOD = [
    "<b>Dedupe.</b> One result per property per season: ours first, then a closed protest over an open one, then settled (informal / ARB) over no-show or withdrawn, then the lowest final value.",
    "<b>Starting value.</b> Notice market value. Cut = notice minus final market value; win = any cut, or the \"Count as a win\" threshold. Values with a final more than 25% above notice are left out.",
    "<b>Buckets.</b> Informal = informal settlements and TopLine/joint-motion agreements; Formal ARB = ARB hearing outcomes; Other = no-show, dismissed, withdrawn and other closures.",
    "<b>Residential.</b> State code starting with A. Like-for-like matches on the neighborhood code: residential $200K–$2M, peer needs 3+ properties.",
    "<b>Fees.</b> No capped values in these files, so fees are a range: 0.5% to 1% of the market cut.",
    "<b>Not available (hidden):</b> market cut vs. tax bill, market context, the open-protest pipeline, appraiser and ARB panel charts, school districts.",
]


def page(county, D):
    T = TEXT[county]
    h = (HERE / "template_page.html").read_text(encoding="utf-8")
    code = (HERE / "template_code.js").read_text(encoding="utf-8")
    CFG = {"county": T["name"], "firms": True, "hasOwnwell": sd.OWN in D["firms"], "hs": True, "assessed": False,
           "tax": False, "appraiser": False, "cfCallout": False, "path": True, "values": False, "capped": False,
           "ownersLabel": None, "nbLabel": T["nb"], "toplineNote": county == "denton",
           "pathNote": "Joint-motion and TopLine settlements count as informal.", "prospectNote": "",
           "remove": [["#isd-tbl", ".panel"], ["#appr-chart", ".panel"], ["#pm-chart", ".grid2"]],
           "hide": [["results", "this section needs assessed (capped) values at the start and end of each protest, plus tax rates. The files don't have both."],
                    ["context", "this section needs the full appraisal roll for every season."],
                    ["pipeline", "the season files don't carry weekly completion dates for every filer."]]}
    if len(D["seasons"]) < 2:
        CFG["hide"].append(["book", "only one season is available, so there is nothing to compare."])
    elif not D.get("bookflow"):
        CFG["hide"].append(["book", "we had no properties here before the latest season, so there is nothing retained or lost yet."])
    yrs = T["years"]
    h = re.sub(r"<title>.*?</title>", f"<title>{T['name']} Protest Scorecard</title>", h, count=1)
    h = h.replace("<span>Agent 245 · Denton CAD (DCAD)</span>", f"<span>{T['agent']}</span>")
    h = re.sub(r'<span>Data</span><b class="mono">.*?</b>', f'<span>Data</span><b class="mono">{T["data"]}</b>', h, count=1)
    h = re.sub(r"<span>Years</span><b>.*?</b>", f"<span>Years</span><b>{yrs}</b>", h, count=1)
    h = re.sub(r"<span>Unit</span><b>.*?</b>", "<span>Unit</span><b>Property (one per season)</b>", h, count=1)
    h = re.sub(r'<div class="draftnote">.*?</div>', f'<div class="draftnote">{T["draft"]}</div>', h, count=1, flags=re.S)
    h = h.replace("<h2>Property Tax Protest, 2023–2026</h2>", f"<h2>Property Tax Protest, {yrs}</h2>")
    bf = f"{D['seasons'][1]}–{D['seasons'][-1]}" if len(D["seasons"]) > 1 else yrs
    h = h.replace('<span class="chip">2024–2026 · all seasons</span>', f'<span class="chip">{bf} · all seasons</span>')
    items = "".join(f"<li>{x}</li>" for x in T["method"] + COMMON_METHOD)
    h = re.sub(r'(<section id="method">.*?<ul class="plain">).*?(</ul>\s*</section>)', lambda m: m.group(1) + items + m.group(2), h, count=1, flags=re.S)
    data = json.dumps(D, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
    script = f"<script>\nconst D={data};\nconst CFG={json.dumps(CFG)};\n{code}</script>"
    return h.replace("<!--SCRIPT-->", script)


if __name__ == "__main__":
    out = Path(sys.argv[1])
    for county in sys.argv[2:] or ["tarrant", "travis", "montgomery", "denton"]:
        print(f"== {county}")
        R = pd.concat([finish(p) for p in globals()[county]()], ignore_index=True)
        D = sd.build(R, as_of="2026-11-14")
        (out / f"{county}.html").write_text(page(county, D), encoding="utf-8")
        U = {y: D["yearsT"]["any"][str(y)]["us"] for y in D["seasons"]}
        print("  ours by season:", {y: (u["props"], round(u["won"] / u["props"], 3) if u["props"] else None,
                                        round(u["rM"] / u["bM"], 3) if u["bM"] else None) for y, u in U.items()})
        print(f"  wrote {out / (county + '.html')} ({(out / (county + '.html')).stat().st_size / 1e6:.1f} MB)")
