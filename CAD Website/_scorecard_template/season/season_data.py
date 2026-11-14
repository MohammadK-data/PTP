"""Build the County Scorecards season data (the `D` object the source template reads) from one row per property
per season.

Input frame R (one row per property per season, already deduped):
    Y (int), pid (str), A (firm label: US / canonical firm / 'Other agents' / 'Owners (self-filed)'),
    sub ('Residential' / 'Non-residential'), HS (0/1), path ('Informal' / 'ARB' / 'Other'), open (bool),
    resT ('Informal settlement' / 'ARB hearing' / 'Dismissed / no-show' / 'Withdrawn' / 'Other / closed'),
    bM (notice market), fM (final market), ok (bool: closed with usable values), nb, city, yrb, sf, hmon (1-12 or NaN)

Rules follow the source page: residential = state code A*, win = any cut (or the Count-as-a-win threshold),
like-for-like = residential $200K-$2M matched on neighborhood code with 3+ peer properties, fees = 1% of the cut
(0.5% low end, no capped values in these files).
"""
import math

import numpy as np
import pandas as pd

US = "PROPERTY TAX PROTEST"
OWN = "Ownwell (Inc + CRE)"
OWNERS = "Owners (self-filed)"
OTHER = "Other agents"
TIERS = ["<$300K", "$300-500K", "$500-750K", "$750K-1M", "$1-2M", "$2-5M", "$5M+"]
WINS = {"any": "w", "k500": "w500", "k1000": "w1k", "k2500": "w2500", "p025": "wpct"}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def tier(v):
    return pd.cut(v, [-np.inf, 3e5, 5e5, 7.5e5, 1e6, 2e6, 5e6, np.inf], right=False, labels=TIERS).astype(str)


def clean(x):
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating, float)):
        return None if (x is None or math.isnan(x) or math.isinf(x)) else float(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    return x


def prep(R, firms_top=16):
    R = R.copy()
    R["Y"] = R.Y.astype(int)
    R["cut"] = (R.bM - R.fM).where(R.ok)
    R["cutp"] = R.cut.clip(lower=0)
    R["pct"] = (R.cutp / R.bM).where(R.ok & (R.bM > 0))
    R["w"] = (R.cut > 0).astype(int)
    R["w500"] = (R.cut >= 500).astype(int)
    R["w1k"] = (R.cut >= 1000).astype(int)
    R["w2500"] = (R.cut >= 2500).astype(int)
    R["wpct"] = (R.pct >= 0.0025).astype(int)
    R["tier"] = tier(R.bM.fillna(0))
    R["mid"] = (R["sub"] == "Residential") & R.bM.between(2e5, 2e6)
    # top firms: volume across seasons, the latest season counts double
    ag = R[~R.A.isin([US, OWNERS, OTHER])]
    ly = R.Y.max()
    vol = ag.groupby("A").size() + ag[ag.Y == ly].groupby("A").size().reindex(ag.A.unique()).fillna(0)
    top = vol.sort_values(ascending=False).head(firms_top).index.tolist()
    R.loc[~R.A.isin([US, OWNERS] + top), "A"] = OTHER
    return R, [US] + top


def rate(d, wc):
    return d[wc].mean() if len(d) else None


def avgp(d):
    return d.pct.mean() if len(d) else None


def season(R, Y, firms, wc):
    A = R[R.Y == Y]
    C = A[A.ok]
    res = C[C["sub"] == "Residential"]
    us, oth = C[C.A == US], C[(C.A != US) & (C.A != OWNERS)]
    hasown = OWN in firms
    o3 = OWN if hasown else OWNERS

    # ---- like-for-like by neighborhood (residential $200K-$2M)
    mid = res[res.mid & res.nb.ne("")]
    g = mid.groupby(["nb", "A"]).agg(n=("pid", "size"), w=(wc, "sum"), sm=("bM", "sum"), mc=("cutp", "sum"),
                                     inf=("path", lambda s: (s == "Informal").sum()))
    matched = []
    for peer in ["All other agents", OWNERS] + [f for f in firms[1:9]]:
        n = uw = usm = umc = pw = pinf = exp = 0
        for nb, gg in g.groupby(level=0):
            gg = gg.droplevel(0)
            if US not in gg.index:
                continue
            u = gg.loc[US]
            p = gg.drop(index=[US, OWNERS], errors="ignore").sum() if peer == "All other agents" else \
                (gg.loc[peer] if peer in gg.index else None)
            if p is None or p.n < 3:
                continue
            n += u.n; uw += u.w; usm += u.sm; umc += u.mc
            pw += u.n * p.w / p.n; pinf += u.n * p.inf / p.n; exp += u.sm * (p.mc / p.sm if p.sm else 0)
        if n:
            matched.append({"peer": peer, "n": n, "uw": uw / n, "up": umc / usm, "pw": pw / n, "pp": exp / usm,
                            "inf": pinf / n, "gap": exp - umc})

    # ---- paths (residential; averages on $200K-$2M)
    def pstat(d):
        out = {}
        for k in ("Informal", "ARB"):
            x = d[d.path == k]
            xm = x[x.mid]
            out[k] = {"n": len(x), "win": rate(x, wc), "pct": avgp(xm) if len(xm) else avgp(x),
                      "agg": (xm.cutp.sum() / xm.bM.sum()) if len(xm) and xm.bM.sum() else None}
        out["mix"] = {k: int((d.path == k).sum()) for k in ("Informal", "ARB", "Other")}
        return out
    paths = {"All agents": pstat(res[(res.A != US) & (res.A != OWNERS)]), US: pstat(res[res.A == US]),
             OWNERS: pstat(res[res.A == OWNERS])}
    for f in firms[1:]:
        paths[f] = pstat(res[res.A == f])

    # ---- our numbers
    usA = A[A.A == US]
    rM = us.cutp.sum()
    won = int(us[wc].sum())
    agent_props = A[(A.A != OWNERS)]
    vol = agent_props.groupby("A").size().sort_values(ascending=False)
    U = {"props": len(us), "won": won, "bM": us.bM.sum(), "fM": us.fM.sum(), "rM": rM, "bAs": None, "rAs": None,
         "capleak": 0, "capPartial": 0, "halfFee": 0, "fee": rM * 0.01, "feeLo": rM * 0.005, "tax": None,
         "dupProps": 0, "med": us.bM.median() if len(us) else None, "avgW": rM / won if won else None,
         "cases": len(usA), "ourCases": len(usA), "res": us.resT.value_counts().to_dict(),
         "resT": us.resT.value_counts().to_dict(),
         "rank": int(list(vol.index).index(US) + 1) if US in vol.index and vol.index[0] != OTHER else
         (int(list(vol.drop(OTHER, errors="ignore").index).index(US) + 1) if US in vol.index else None),
         "share": len(usA) / len(agent_props) if len(agent_props) else None,
         "ownN": int((C.A == OWN).sum()), "ownMed": C[C.A == OWN].bM.median() if hasown else None}

    # ---- tiers
    tiers = []
    for t in TIERS:
        a, m, o = res[(res.tier == t) & (res.A == US)], res[(res.tier == t) & ~res.A.isin([US, OWNERS])], res[(res.tier == t) & (res.A == o3)]
        tiers.append({"tier": t, "n": len(a), "win": rate(a, wc), "pct": avgp(a), "n_m": len(m), "win_m": rate(m, wc),
                      "pct_m": avgp(m), "n_o": len(o), "win_o": rate(o, wc), "pct_o": avgp(o)})
    ru = res[res.A == US]
    hs = {"non": {"n": int((ru.HS == 0).sum()), "win": rate(ru[ru.HS == 0], wc)},
          "hs": {"n": int((ru.HS == 1).sum()), "win": rate(ru[ru.HS == 1], wc)}}

    # ---- ARB by hearing month
    month = []
    arb = res[(res.path == "ARB") & res.hmon.notna()]
    for mnum, d in arb.groupby("hmon"):
        a, m = d[d.A == US], d[d.A != US]
        if len(a):
            month.append({"mnum": int(mnum), "m": MONTHS[int(mnum) - 1], "n": len(a), "win": rate(a, wc), "pct": avgp(a),
                          "mn": len(m), "mwin": rate(m, wc), "mpct": avgp(m)})

    # ---- prospects: owners who protested their own home
    ow = A[(A.A == OWNERS) & (A["sub"] == "Residential") & ~A.open]
    owc = ow[ow.ok]
    zero = owc[owc.cut <= 0]
    prospects = {"total": len(ow), "zero": len(zero), "zero300": int((zero.bM >= 3e5).sum()),
                 "zero300hs": int(((zero.bM >= 3e5) & (zero.HS == 1)).sum()),
                 "noshow": int((ow.resT == "Dismissed / no-show").sum()), "wd": int((ow.resT == "Withdrawn").sum()),
                 "win": rate(owc, wc), "pct": avgp(owc)}

    # ---- cities
    cities = []
    rc = res[res.city.ne("")]
    for c, n in rc[rc.A == US].city.value_counts().head(10).items():
        a, m = rc[(rc.city == c) & (rc.A == US)], rc[(rc.city == c) & ~rc.A.isin([US, OWNERS])]
        cities.append({"c": c, "n": len(a), "win": rate(a, wc), "pct": avgp(a), "red": a.cutp.sum(),
                       "mwin": rate(m, wc), "mpct": avgp(m)})

    # ---- age / size bands, residential $200K+
    r2 = res[res.bM >= 2e5]
    grp = np.select([r2.A == US, r2.A == o3, r2.A != OWNERS], ["us", "own", "ag"], default="")
    r2 = r2.assign(g=grp)
    r2 = r2[r2.g != ""]
    yb = pd.to_numeric(r2.yrb, errors="coerce")
    sf = pd.to_numeric(r2.sf, errors="coerce")
    age_b = pd.cut(yb, [0, 1950, 1980, 2000, 2010, 2020, 2100], right=False,
                   labels=["0: Before 1950", "1: 1950–79", "2: 1980–99", "3: 2000–09", "4: 2010–19", "5: 2020+"])
    size_b = pd.cut(sf, [0, 1500, 2000, 3000, 4000, 1e9], right=False,
                    labels=["0: Under 1,500", "1: 1,500–1,999", "2: 2,000–2,999", "3: 3,000–3,999", "4: 4,000+"])

    def bands(b):
        out = []
        for (bb, gg), d in r2.assign(b=b).dropna(subset=["b"]).groupby(["b", "g"], observed=True):
            if len(d) >= 10:
                out.append({"b": str(bb), "g": gg, "n": len(d), "win": rate(d, wc), "pct": avgp(d)})
        return out

    # ---- biggest wins, lost-where-neighbors-won, no-change ARB
    big = us.sort_values("cutp", ascending=False).head(15)
    bigWins = [[r.pid, r.nb, r.city, r.bM, r.cutp, r.pct, r.resT, None, None] for r in big.itertuples()]
    nbo = res[~res.A.isin([US, OWNERS]) & res.nb.ne("")].groupby("nb").agg(n=("pid", "size"), w=(wc, "mean"), p=("pct", "mean"))
    lostc = ru[(ru[wc] == 0) & ru.nb.isin(nbo[(nbo.n >= 5) & (nbo.w >= 0.7)].index)].copy()
    lostc = lostc.join(nbo, on="nb", rsuffix="_nb")
    lostc["est"] = lostc.bM * lostc.p
    lostc = lostc.sort_values("est", ascending=False)
    lostNbr = [[r.pid, r.nb, r.city, r.bM, r.resT, int(r.n), r.w_nb, r.p, r.est] for r in lostc.head(60).itertuples()]
    ncs = ru[(ru.path == "ARB") & (ru.cut <= 0)]
    inf_nb = res[(res.path == "Informal") & (res.A != US) & res.nb.ne("")].groupby("nb").agg(w=(wc, "mean"), p=("pct", "mean"), n=("pid", "size"))
    ncm = ncs[ncs.nb.isin(inf_nb[inf_nb.n >= 3].index)].join(inf_nb, on="nb", rsuffix="_i")
    nochange = {"n": len(ncs), "matched": len(ncm), "base": ncs.bM.sum() if len(ncs) else None,
                "infw": ncm.w_i.mean() if len(ncm) else None, "infp": ncm.p.mean() if len(ncm) else None,
                "est": (ncm.bM * ncm.p).sum() if len(ncm) else None}

    return {"matched": matched, "paths": paths, "cf": {"n": 0}, "nochange": nochange, "us": U, "tiers": tiers, "hs": hs,
            "appr": [], "apprMin": 30, "pm": [], "pmMin": 30, "pnl": [], "pnlCov": [0, 0], "month": month,
            "prospects": prospects, "cities": cities, "impact": [], "cushion": [], "taxBands": [], "taxCity": [],
            "taxIsd": [], "isdWin": [], "age": bands(age_b), "size": bands(size_b), "bigWins": bigWins,
            "lostNbr": lostNbr, "lostNbrN": len(lostc), "lostNbrEst": lostc.est.sum()}


def build(R, as_of):
    R, firms = prep(R)
    years = sorted(R.Y.unique().tolist())
    C = R[R.ok]
    cols = ["Y", "A", "sub", "tier", "HS", "path", "n", "w", "bM", "rM", "bAs", "rAs", "wAs", "sp", "fee", "tax", "cap",
            "w500", "w1k", "w2500", "wpct", "dup", "feeLo"]
    g = C.groupby(["Y", "A", "sub", "tier", "HS", "path"]).agg(
        n=("pid", "size"), w=("w", "sum"), bM=("bM", "sum"), rM=("cutp", "sum"), sp=("pct", "sum"),
        w500=("w500", "sum"), w1k=("w1k", "sum"), w2500=("w2500", "sum"), wpct=("wpct", "sum")).reset_index()
    cube = [[r.Y, r.A, r.sub, r.tier, int(r.HS), r.path, r.n, r.w, r.bM, r.rM, 0, 0.0, None, r.sp, r.rM * 0.01, 0, 0,
             r.w500, r.w1k, r.w2500, r.wpct, 0, r.rM * 0.005] for r in g.itertuples()]
    yearsT = {k: {y: season(R, y, firms, wc) for y in years} for k, wc in WINS.items()}

    # neighborhood rows (residential $200K-$2M)
    nb = {}
    for y in years:
        m = C[(C.Y == y) & C.mid & C.nb.ne("")]
        gg = m.groupby(["nb", "A"]).agg(n=("pid", "size"), w=("w", "sum"), w500=("w500", "sum"), w1k=("w1k", "sum"),
                                        w2500=("w2500", "sum"), wpct=("wpct", "sum"), sm=("bM", "sum"), mc=("cutp", "sum"),
                                        inf=("path", lambda s: (s == "Informal").sum())).reset_index()
        nb[y] = gg[["nb", "A", "n", "w", "w500", "w1k", "w2500", "wpct", "sm", "mc", "inf"]].values.tolist()
    nbCity = C[C.nb.ne("") & C.city.ne("")].groupby("nb").city.agg(lambda s: s.mode().iat[0]).to_dict()

    # book of business: every property we filed on (open or closed)
    own = {y: set(R[(R.Y == y) & (R.A == US)].pid) for y in years}
    by = {y: R[R.Y == y].set_index("pid") for y in years}
    bookflow, lost = [], {}
    for i, y in enumerate(years[1:], 1):
        p, cur = years[i - 1], own[y]
        prev = own[p]
        gone = sorted(prev - cur)
        now = by[y]
        to = pd.Series([now.A.get(x, "Not protested") if x in now.index else "Not protested" for x in gone]).value_counts()
        bookflow.append({"year": y, "props": len(cur), "retained": len(cur & prev), "new": len(cur - prev),
                         "lost": len(gone), "lostTo": [[k, int(v)] for k, v in to.items()]})
        pv = by[p]
        rows = []
        for x in gone:
            a = pv.loc[x]
            n = now.loc[x] if x in now.index else None
            rows.append([x, a.nb, a.city, a.bM, a.resT, a.cutp if pd.notna(a.cutp) else 0.0,
                         n.A if n is not None else "Not protested", n.resT if n is not None else None])
        lost[y] = sorted(rows, key=lambda r: -(r[3] or 0))
    D = {"cols": cols, "firms": firms, "cube": cube, "yearsT": yearsT, "nb": nb,
         "nbCols": ["nb", "P", "n", "w", "w500", "w1k", "w2500", "wpct", "sm", "mc", "inf"], "nbNames": {}, "nbCity": nbCity,
         "peersN": firms[:9], "nbPeers": firms, "asOf": as_of, "seasons": years,
         "openAgents": [], "openShare": {}, "excludedOpen": 0, "ourHeld": 0,
         "open": {"byStatus": [], "byWeek": [], "noDocket": 0, "ours": 0, "closedPropsWithOpenCase": 0},
         "wk": [], "compsrc": [], "bookflow": bookflow if bookflow else None, "lost": lost if lost else None,
         "context": None, "protestRate": None, "share": None, "ratesFallback": None, "prospectsYoY": None,
         "baseline": None, "counts": {}, "feeRangeYears": years}
    return clean(D)
