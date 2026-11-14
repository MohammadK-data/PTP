"""Montgomery scorecard on the County Scorecards season template, with the pieces the shared builder leaves out:
open-protest pipeline (Aug 4 JSON), completion curves for every season, and account search / neighborhood lookup
files for 2024-2026.

Seasons: 2024 and 2025 from the developers' file (montgomery_protests_2023-2026.csv), 2026 from the protax JSON build
(output/montgomery_values_2026.csv). 2023 is left out: the file has outcomes but no notice or final value, and MCAD
publishes no preliminary (notice) roll before 2026, so no 2023 reduction can be measured.

Run:  .venv/bin/python -I "CAD Website/Montgomery/etl/montgomery_season_page.py" <site_dir>
Writes <site_dir>/montgomery.html, <site_dir>/lookup/montgomery.json, <site_dir>/acct/montgomery/*.txt
"""
import base64
import gzip
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "_scorecard_template" / "season"))
import build_season_pages as bsp  # noqa: E402
import season_data as sd  # noqa: E402

OUT = ROOT / "Montgomery" / "output"
DEVF = bsp.DEV / "Montgomery" / "montgomery_protests_2023-2026.csv"
AS_OF = "2026-08-04"
OPEN_LABEL = {"WH": "Waiting for hearing", "EXP-NC": "Expedited, no-change offer pending", "R": "Rescheduled",
              "EF_TL": "E-file TopLine pending", "PROT": "Protest filed", "PROT-SCHD": "Protest scheduled",
              "REOPENED": "Reopened"}


def num(s):
    return pd.to_numeric(s, errors="coerce")


def doy_week(d):
    return ((d.dt.day_of_year - 1) // 7).astype("Int64")


# ---------------------------------------------------------------- season rows

def seasons():
    R = pd.concat([bsp.finish(p) for p in bsp.montgomery()], ignore_index=True)
    return R


# ---------------------------------------------------------------- pipeline (2026 open protests + completions)

def pipeline(R, D):
    a = pd.read_csv(OUT / "montgomery_appeals_2026.csv.gz", dtype=str, keep_default_na=False)
    a = a[a.appealType.isin(["PROT", "P", "PROTPH"])].copy()
    a["fin"] = a.finalized.isin(["1", "1.0", "True"])
    a["pid"] = a.pID.str.lstrip("0")
    a["agent"] = a.appealedByAgentID.str.replace(r"\.0$", "", regex=True)
    r26 = R[R.Y == 2026].set_index("pid")
    a["A"] = a.pid.map(r26.A).fillna(sd.OTHER)
    a.loc[a.agent.eq("654513"), "A"] = sd.US
    a["res"] = a.pid.map(r26["sub"]).eq("Residential")
    o = a[~a.fin].copy()
    o["dk"] = pd.to_datetime(o.docketDt.str[:10], errors="coerce")
    asof = pd.Timestamp(AS_OF)
    fut = o[o.dk >= asof]
    wk = fut.dk - pd.to_timedelta(fut.dk.dt.weekday, unit="D")
    byWeek = [[d.strftime("%Y-%m-%d"), str(n)] for d, n in wk.value_counts().sort_index().head(4).items()]
    st = o.appealStatus.str.strip().value_counts()
    D["open"] = {"byStatus": [[k, OPEN_LABEL.get(k, k), int(n), 0] for k, n in st.items()], "byWeek": byWeek,
                 "noDocket": int((o.dk.isna() | (o.dk < asof)).sum()), "ours": int(o.A.eq(sd.US).sum()),
                 "closedPropsWithOpenCase": 0}
    tot = a.groupby("A").size()
    rows = []
    for f, g in o.groupby("A"):
        d = g.dk[g.dk >= asof]
        rows.append([f, len(g), len(g), d.min().strftime("%Y-%m-%d") if len(d) else None,
                     d.max().strftime("%Y-%m-%d") if len(d) else None, int((g.dk.isna() | (g.dk < asof)).sum()),
                     int(g.res.sum())])
    D["openAgents"] = sorted(rows, key=lambda r: -r[1])
    D["openShare"] = {k: int(v) for k, v in tot.items()}
    D["ourHeld"] = D["open"]["ours"]
    D["excludedOpen"] = 0

    # completion curves: closed protests by week of the finalized date, every season
    dev = pd.read_csv(DEVF, dtype=str, keep_default_na=False, usecols=["tax_year", "account", "is_ours", "finalized_date", "outcome_type"])
    dev = dev[dev.tax_year.isin(["2024", "2025"]) & dev.outcome_type.ne("Open / unresolved")]
    dev["d"] = pd.to_datetime(dev.finalized_date, format="%m/%d/%Y", errors="coerce")
    dev["us"] = dev.is_ours.str.lower().eq("true").astype(int)
    c26 = a[a.fin].assign(d=pd.to_datetime(a.finalizedDt.str[:10], errors="coerce"), us=a.A.eq(sd.US).astype(int))
    wkrows = []
    for y, df in [(2024, dev[dev.tax_year == "2024"]), (2025, dev[dev.tax_year == "2025"]), (2026, c26)]:
        df = df[df.d.dt.year == y]
        g = df.assign(w=doy_week(df.d)).groupby(["us", "w"]).size()
        wkrows += [[y, int(u), int(w), int(n)] for (u, w), n in g.items()]
    D["wk"] = wkrows
    src = []
    for us_, g in c26.groupby("us"):
        for pth, gg in g.assign(p=g.pid.map(r26.path).fillna("Other")).groupby("p"):
            src.append([int(us_), pth, "Finalized date in the JSON", int(gg.d.notna().sum())])
    D["compsrc"] = src
    return D


# ---------------------------------------------------------------- account search + neighborhood lookup

def dump(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64encode(gzip.compress(json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode(), 9)))


def nid(s):
    return re.sub(r"[^A-Z0-9]", "", str(s).upper()).lstrip("0")


def jhash(s):
    h = 0
    for ch in s:
        h = (h * 31 + ord(ch)) % 4294967296
    return h


def search_rows(R):
    """Every protested property, one row per season, with the fields the account search shows."""
    v = pd.read_csv(OUT / "montgomery_values_2026.csv", dtype=str, keep_default_na=False)
    v["pid"] = v.pID.str.lstrip("0")
    ident = v.set_index("pid")[["pID", "situs", "owner", "zip", "stateCd", "situs_city"]]
    p26 = v[v.protested.eq("True")].set_index("pid")
    dev = pd.read_csv(DEVF, dtype=str, keep_default_na=False,
                      usecols=["tax_year", "account", "agent_name", "filed_by", "status_desc", "finalized_date",
                               "hearing_date", "zip", "state_code", "is_ours"])
    dev = dev[dev.tax_year.isin(["2024", "2025"])]
    dev["pid"] = dev.account.str.lstrip("0")
    dev["ours"] = dev.is_ours.str.lower().eq("true")
    dev = dev.sort_values(["pid", "ours"], ascending=[True, False]).drop_duplicates(["tax_year", "pid"])
    dev = dev.set_index(["tax_year", "pid"])
    out = []
    for r in R.itertuples():
        y = int(r.Y)
        base = {"y": y, "pid": r.pid, "firm": "Property Tax Protest" if r.A == sd.US else r.A, "bucket": r.path if not r.open else "Open",
                "outcome": r.resT, "s": r.bM, "f": None if r.open else r.fM,
                "cut": (r.bM - r.fM) if r.ok else None, "win": int(bool(r.ok and r.bM - r.fM > 0)), "op": int(bool(r.open)),
                "hs": int(r.HS), "cls": r.sub, "nb": r.nb, "city": r.city.title() if r.city else None, "yrb": r.yrb, "sf": r.sf,
                "ours": int(r.A == sd.US)}
        if y == 2026 and r.pid in p26.index:
            q = p26.loc[r.pid]
            base.update({"agents": q.agents_current.replace(" | ", "; "), "status": q.appealStatus,
                         "by": {"A": "AG", "O": "OW", "OTH": "OT"}.get(q.appealedByType, q.appealedByType),
                         "heard": (q.formalStartMeeting or q.informalStartMeeting)[:10] or None,
                         "htype": "Formal ARB" if q.formalStartMeeting else ("Informal meeting" if q.informalStartMeeting else None),
                         "res": q.finalizedDt[:10] or None, "nc": q.n_appeals, "sc": q.stateCd, "zip": q.zip,
                         "fee": round(max(r.bM - r.fM, 0) * 0.01) if (r.A == sd.US and r.ok) else None})
        elif (str(y), r.pid) in dev.index:
            q = dev.loc[(str(y), r.pid)]
            fd = pd.to_datetime(q.finalized_date, format="%m/%d/%Y", errors="coerce")
            hd = pd.to_datetime(q.hearing_date, format="%m/%d/%Y", errors="coerce")
            base.update({"agents": q.agent_name or None, "status": q.status_desc or None,
                         "by": {"AGENT": "AG", "OWNER": "OW", "OTHER": "OT"}.get(q.filed_by, None),
                         "res": None if pd.isna(fd) else fd.strftime("%Y-%m-%d"),
                         "heard": None if pd.isna(hd) else hd.strftime("%Y-%m-%d"), "sc": q.state_code, "zip": q.zip,
                         "fee": round(max(r.bM - r.fM, 0) * 0.01) if (r.A == sd.US and r.ok) else None})
        out.append(base)
    return pd.DataFrame(out), ident


def write_search(R, site):
    S, ident = search_rows(R)
    COLS = ['y', 'firm', 'agents', 'by', 'bucket', 'status', 'outcome', 'htype', 's', 'f', 'cut', 'win', 'op', 'hs', 'cls',
            'sc', 'nb', 'city', 'zip', 'yrb', 'sf', 'filed', 'heard', 'res', 'nc', 'fee', 'tsav', 'sAss', 'fAss', 'cap',
            'panel', 'appr', 'ours', 'extra']
    DICT = ["status", "by", "htype", "panel", "city", "firm", "extra", "nb", "appr", "agents", "bucket", "sc", "outcome", "zip", "cls"]
    dicts = {c: [] for c in DICT}
    dix = {c: {} for c in DICT}

    def enc(c, x):
        if x is None or (isinstance(x, float) and np.isnan(x)) or (isinstance(x, str) and x.strip() in ("", "nan", "None")):
            return None
        if c in ("heard", "res"):
            return str(x)[:10]
        if c in ("yrb", "sf"):
            n = pd.to_numeric(x, errors="coerce")
            return int(n) if pd.notna(n) and n > 0 else None
        if c in DICT:
            x = str(x).strip()
            d = dix[c]
            if x not in d:
                d[x] = len(dicts[c])
                dicts[c].append(x)
            return d[x]
        if c == "y":
            return int(x)
        try:
            return int(round(float(x)))
        except (TypeError, ValueError):
            return x

    SH = 12
    shards = [{"a": [], "r": [], "c": {c: [] for c in COLS}} for _ in range(SH)]
    idx, seen = [], {}
    S = S.sort_values(["pid", "y"])
    for pid, g in S.groupby("pid", sort=False):
        n = nid(pid)
        s = shards[jhash(n) % SH]
        idn = ident.loc[pid] if pid in ident.index else None
        row = [n, idn.pID if idn is not None else pid, (idn.situs or None) if idn is not None else None,
               (idn.owner or None) if idn is not None else None]
        ai = len(s["a"])
        s["a"].append(row)
        idx.append(row)
        for r in g.to_dict("records"):
            s["r"].append(ai)
            for c in COLS:
                s["c"][c].append(enc(c, r.get(c)))
    base = site / "acct" / "montgomery"
    for old in base.glob("*.txt") if base.exists() else []:
        old.unlink()
    for i, s in enumerate(shards):
        dump(s, base / f"{i}.txt")
    dump(idx, base / "idx.txt")
    dump({"county": "montgomery", "shards": SH, "cols": COLS, "dicts": dicts, "rows": len(S), "accounts": len(idx),
          "hasText": True}, base / "meta.txt")
    print(f"search: {len(idx):,} properties, {len(S):,} property-seasons")


def write_lookup(R, site):
    LT = ["Under $200K", "$200K–$400K", "$400K–$600K", "$600K–$1M", "$1M+"]
    years = sorted(int(y) for y in R.Y.unique())
    res = R[(R["sub"] == "Residential") & R.nb.ne("") & (R.bM > 0) & ~((R.fM > R.bM * 1.25) & R.ok)].copy()
    special = [sd.US, sd.OWNERS]
    cnt = res[~res.A.isin(special + [sd.OTHER])].A.value_counts()
    big = cnt[cnt >= 300].index.tolist()
    res["F"] = np.where(res.A.isin(special + big), res.A, "Other agents (smaller firms)")
    firms = ["Property Tax Protest (us)", "Owners (self-filed)", "No agent · other appellant"] + big + ["Other agents (smaller firms)"]
    fi = {f: i for i, f in enumerate(firms)}
    fi[sd.US] = 0
    nice = {sd.OWN: "Ownwell"}
    city = res[res.city.ne("")].groupby("nb").city.agg(lambda s: s.mode().iat[0].title())
    nbs = sorted(res.nb.unique())
    ni = {c: i for i, c in enumerate(nbs)}
    res["t"] = res.bM.map(lambda x: 0 if x < 2e5 else 1 if x < 4e5 else 2 if x < 6e5 else 3 if x < 1e6 else 4)
    res["yi"] = res.Y.map({y: i for i, y in enumerate(years)})
    cl = res[res.ok].copy()
    cl["c0"] = (cl.bM - cl.fM).clip(lower=0)
    cl["pc"] = cl.c0 / cl.bM
    cl["w"] = (cl.c0 > 0).astype(int)
    rows = [[int(y), ni[nb], fi[f], int(t), len(g), int(g.w.sum()), int(g.bM.sum()), int(g.c0.sum()), round(float(g.pc.sum()), 5)]
            for (y, nb, f, t), g in cl.groupby(["yi", "nb", "F", "t"])]
    opn = [[int(y), ni[nb], fi[f], len(g)] for (y, nb, f), g in res[res.open].groupby(["yi", "nb", "F"])]
    ours = res[res.A == sd.US]
    ol = [[int(r.yi), r.pid, ni[r.nb], int(r.bM), None if r.open or not r.ok else int(r.fM),
           None if r.open or not r.ok else int(max(r.bM - r.fM, 0)),
           {"ARB": "ARB hearing"}.get(r.path, r.path), bool(r.ok and r.bM - r.fM > 0), bool(r.open),
           None if r.open or not r.ok else int(round(max(r.bM - r.fM, 0) * 0.01))] for r in ours.itertuples()]
    (site / "lookup").mkdir(parents=True, exist_ok=True)
    (site / "lookup" / "montgomery.json").write_text(json.dumps(
        {"years": years, "firms": [nice.get(f, f) for f in firms], "us": 0, "tiers": LT,
         "nbs": [[c, city.get(c)] for c in nbs], "rows": rows, "open": opn, "ours": ol}, separators=(",", ":"), ensure_ascii=False))
    print(f"lookup: {len(nbs):,} neighborhoods, {len(ol):,} of our property-seasons, years {years}")


# ---------------------------------------------------------------- page

def main(site):
    site = Path(site)
    R = seasons()
    D = sd.build(R, as_of=AS_OF)
    D = sd.clean(pipeline(R, D))
    T = bsp.TEXT["montgomery"]
    T["data"] = "Developers' file 2024–2025 · protax JSON Aug 4, 2026"
    T["draft"] = ("<b>Draft for review.</b> 2024 and 2025 come from the developers' Montgomery file (MCAD protest records). "
                  "2026 is the protax JSON build (Aug 4) with the certified roll for appeals still open then. <b>2023 is left out:</b> "
                  "the file has outcomes but no notice or final value for 2023, and MCAD publishes no notice (preliminary) roll before 2026. "
                  "<b>Our properties</b> = protests filed under agent 654513 (617 in 2026); about 130 more PTP clients had their 2026 "
                  "protest filed by another agent or the owner. Details under <a href=\"#method\">Method &amp; open questions</a>.")
    T["method"] = [
        "<b>Seasons.</b> 2024–2025: <span class=\"mono\">montgomery_protests_2023-2026.csv</span> (developers', Oct 26). 2026: <span class=\"mono\">montgomery_values_2026.csv</span> (protax JSON Aug 4 + certified roll Aug 4).",
        "<b>2023.</b> Left out: the file has 96,878 protested properties with outcomes for 2023 but no notice or final value. MCAD's site has certified rolls back to 2019 but only one preliminary (notice) roll, 2026, so 2023 reductions can't be rebuilt.",
        "<b>Our properties.</b> Protests filed under agent 654513: 214 (2024), 419 (2025), 617 (2026). The earlier County Scorecards page showed 747 for 2026: that counted every property with a PTP appointment and a protest, including about 130 whose protest another agent or the owner filed.",
        "<b>Status codes.</b> MCAD's own descriptions (developers' file): AC = agent cancelled and C = property owner cancelled (both Withdrawn), DP = duplicate protest (Dismissed), HD.NAA = hearing denied, no agent appointment (No-show / dismissed).",
        "<b>Open protests.</b> 20,596 protest cases were still open in the Aug 4 JSON (mostly WH, waiting for hearing; 1 ours). They're left out of results; the pipeline section lists them.",
    ]
    html = bsp.page("montgomery", D)
    html = html.replace('["pipeline", "the season files don\'t carry weekly completion dates for every filer."]', "")
    html = re.sub(r',\s*\]\};\nconst US', ']};\nconst US', html)
    html = html.replace('<span class="chip">2026 · open protests</span>', '<span class="chip">2026 · open protests as of Aug 4</span>')
    (site / "montgomery.html").write_text(html, encoding="utf-8")
    print(f"page: {(site / 'montgomery.html').stat().st_size / 1e6:.1f} MB")
    U = {y: D["yearsT"]["any"][str(y)]["us"] for y in D["seasons"]}
    print("ours:", {y: (u["props"], round(u["won"] / u["props"], 3), round(u["rM"] / u["bM"], 3)) for y, u in U.items()})
    write_search(R, site)
    write_lookup(R, site)


if __name__ == "__main__":
    main(sys.argv[1])
