"""Scorecard data, neighborhood lookup and account-search shards for Travis, same formats as the Tarrant page."""
import base64, gzip, json, re
from pathlib import Path
import numpy as np, pandas as pd

TRV = Path("/Users/user2/PTP/CAD Website/Travis/output")
SCR = Path("/private/tmp/claude-502/-Users-user2-PTP/e7f251f4-b2fb-4c35-80a5-9bf9637fb1cf/scratchpad")
SITE = SCR / "trv/site"
US = "PROPERTY TAX PROTEST"

v = pd.read_csv(TRV / "travis_values_2026.csv", dtype=str, keep_default_na=False)
for c in ["notice_value", "final_value", "reduction", "cert_market", "n_appeals", "yrb", "sf", "est_fee_1pct"]:
    v[c] = pd.to_numeric(v[c], errors="coerce")
for c in ["is_ours", "protested", "check_values", "homestead"]:
    v[c] = v[c].eq("True")

# agent id -> name from every agent string on the roll
pairs = v.agents_all.str.split(r" \| ").explode().dropna()
pairs = pairs[pairs.ne("")].str.extract(r"^(.*) \((\d+)\)$").dropna()
idname = pairs.groupby(1)[0].agg(lambda s: s.mode().iloc[0])
def canon(n):
    u = n.upper()
    if "OWNWELL" in u: return "Ownwell"
    if u.startswith("TEXAS PROTAX"): return "Texas ProTax (all agents)"
    if u.startswith("RYAN"): return "Ryan (all codes)"
    if "CONNOR" in u and "O" in u[:3]: return "O'Connor & Associates"
    return re.sub(r"\s+", " ", n.strip())
p = v[v.protested].copy()
p["firm"] = np.where(p.agent.ne(""), p.agent.map(idname).fillna("Agent #" + p.agent).map(canon),
                     np.where(p.appealedByType.eq("O"), "Owners (self-filed)", "No agent · other appellant"))
p.loc[p.is_ours, "firm"] = US
p["sub"] = np.where(p.stateCd.str.startswith("A"), "Residential", "Non-residential")
p["pth"] = p.path.map({"Informal": "Informal", "ARB": "ARB", "Open": "Open"}).fillna("Other")
p["op"] = p.path.eq("Open")
TIERS = ["<$300K", "$300-500K", "$500-750K", "$750K-1M", "$1-2M", "$2-5M", "$5M+"]
p["tier"] = pd.cut(p.notice_value, [-1, 3e5, 5e5, 7.5e5, 1e6, 2e6, 5e6, np.inf], labels=TIERS).astype(str)
p["hs"] = p.homestead.astype(int)
special = {US, "Owners (self-filed)", "No agent · other appellant"}
top = p[p["sub"].eq("Residential") & ~p.firm.isin(special)].firm.value_counts().head(16).index.tolist()
p["A"] = np.where(p.firm.isin(top) | p.firm.isin(special), p.firm, "Other agents")

closed = p[~p.op & ~p.check_values].copy()
closed["red"] = closed.reduction.clip(lower=0)
closed["w"] = closed.reduction > 0
closed["pc"] = (closed.reduction / closed.notice_value).clip(lower=0)
cube = closed.groupby(["A", "sub", "tier", "pth", "hs"]).agg(
    n=("w", "size"), w=("w", "sum"), bM=("notice_value", "sum"), rM=("red", "sum"), sp=("pc", "sum"),
    w500=("red", lambda s: (s >= 500).sum()), w1k=("red", lambda s: (s >= 1000).sum()),
    w2500=("red", lambda s: (s >= 2500).sum()), wpct=("pc", lambda s: (s >= .0025).sum())).reset_index()
cols = ["A", "sub", "tier", "pth", "hs", "n", "w", "bM", "rM", "sp", "w500", "w1k", "w2500", "wpct"]
cube_rows = cube[cols].values.tolist()

# like-for-like by TCAD neighborhood (marketArea), residential $200K-$2M
lf = closed[closed["sub"].eq("Residential") & closed.notice_value.between(2e5, 2e6) & closed.nb.ne("")]
ours = lf[lf.A.eq(US)]
def peer_set(n):
    return lf[~lf.A.isin(list(special))] if n == "All other agents" else lf[lf.A.eq(n)]
matched = []
for pr in ["All other agents", "Owners (self-filed)"] + top[:10]:
    ps = peer_set(pr)
    st = ps.groupby("nb").agg(pn=("w", "size"), pw=("w", "mean"), pp=("pc", "mean"))
    st = st[st.pn >= 3]
    m = ours.join(st, on="nb", how="inner")
    if not len(m): continue
    matched.append({"peer": pr, "n": len(m), "grids": m.nb.nunique(), "uw": m.w.mean(), "pw": m.pw.mean(), "up": m.pc.mean(),
                    "pp": m.pp.mean(), "gap": float((m.notice_value * m.pp).sum() - m.red.sum()),
                    "inf": float(ps[ps.nb.isin(m.nb)].pth.eq("Informal").mean())})
oth = peer_set("All other agents").groupby("nb").agg(pn=("w", "size"), pw=("w", "mean"), pp=("pc", "mean"))
og = ours.groupby("nb").agg(un=("w", "size"), uw=("w", "mean"), up=("pc", "mean"), ucut=("red", "sum"), ub=("notice_value", "sum"))
gs = og.join(oth, how="left").reset_index()
grids = [[r.nb, int(r.un), r.uw, r.up, r.ucut, None if pd.isna(r.pn) else int(r.pn), None if pd.isna(r.pw) else r.pw,
          None if pd.isna(r.pp) else r.pp, None if pd.isna(r.pn) or r.pn < 3 else r.ub * r.pp - r.ucut] for r in gs.itertuples()]

o = p[p.is_ours].copy()
def others(s):
    return "; ".join(sorted({re.sub(r" \(\d+\)$", "", x) for x in s.split(" | ") if x and not re.search(r"\((1863738|1898343|1898284)\)$", x)}))
o["oth"] = o.agents_current.map(others)
o["pshort"] = o.path
acct = [[r.pID, r.situs, r.stateCd, r.nb, None, None if pd.isna(r.notice_value) else round(r.notice_value),
         None if pd.isna(r.final_value) else round(r.final_value), None if pd.isna(r.reduction) else round(r.reduction),
         r.pshort, r.appealStatus, (r.finalizedDt or "")[:10], r.oth, 0 if pd.isna(r.n_appeals) else int(r.n_appeals), None, ""]
        for r in o.itertuples()]
shared = o[o.oth.ne("")]
checks = {
    "flow": [["Protax JSON (Oct 6)", f"{len(v):,}", "properties, one record each"],
             ["2026 protests", f"{len(p):,}", f"properties with a 2026 protest · {int(v.n_appeals.gt(1).sum()):,} had 2+ appeals"],
             ["Final vs certified roll", f"{(closed.final_source.eq('appeal') & ((closed.final_value - closed.cert_market).abs() <= 2)).sum() / closed.final_source.eq('appeal').sum():.1%}", "of closed appeals match the Oct 6 certified market value"],
             ["Filled from certified roll", f"{int(p.final_source.str.startswith('certified').sum() + p.notice_source.str.startswith('certified').sum()):,}", "values the JSON did not have"]],
    "list": [f"<b>{int(v.n_appeals.gt(1).sum()):,}</b> properties had more than one 2026 appeal. One appeal per property is kept: ours first, then finalized, then the latest.",
             f"<b>{int(p.final_source.eq('certified (appeal open)').sum()):,}</b> appeals were still open on Oct 6. Their final value is the certified roll value and they are left out of every rate.",
             f"<b>{int(p.notice_source.str.startswith('certified').sum())}</b> appeals had no initial value in the JSON; the certified value is used.",
             f"<b>{int(p.check_values.sum()):,}</b> protested properties have a $0 notice or a final more than 25% above notice. None are ours. They are left out of every rate.",
             "Multi-owner properties: appeal values are put on the same basis as the owners' values (the rule from travis_values.py).",
             "Only 2026 appeals and 2026 values are used. Earlier years in the JSON are ignored."],
    "sharedTitle": "Our accounts where another agent is also on file",
    "sharedNote": "Agents TCAD lists on the account as of Oct 6, other than us. The appeal itself was filed by us.",
    "sharedWith": shared.oth.str.split("; ").explode().value_counts().head(8).to_dict(), "oursShared": int(len(shared)),
}
D = {"cols": cols, "cube": cube_rows, "tiers": TIERS, "firms": [US] + top, "open": p[p.op].groupby("A").size().to_dict(),
     "matched": matched, "grids": grids, "acct": acct, "checks": checks, "hasHS": True}
def clean(x):
    if isinstance(x, (np.bool_,)): return bool(x)
    if isinstance(x, (np.integer,)): return int(x)
    if isinstance(x, (float, np.floating)): return None if np.isnan(x) else round(float(x), 6)
    if isinstance(x, list): return [clean(y) for y in x]
    if isinstance(x, dict): return {k: clean(y) for k, y in x.items()}
    return x
(SCR / "trv/data.json").write_text(json.dumps(clean(D), separators=(",", ":"), ensure_ascii=False))
print("scorecard: cube", len(cube_rows), "ours", len(o), "top", top[:6])
print(pd.DataFrame(matched)[["peer", "n", "uw", "pw", "up", "pp", "gap"]].round(3).to_string())

# ---------- account search shards (same format as the County Scorecards page)
def dump(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64encode(gzip.compress(json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode(), 9)))
nid = lambda s: re.sub(r"[^A-Z0-9]", "", str(s).upper()).lstrip("0")
def jhash(s):
    h = 0
    for ch in s: h = (h * 31 + ord(ch)) % 4294967296
    return h
COLS = ['y', 'firm', 'agents', 'by', 'bucket', 'status', 'outcome', 'htype', 's', 'f', 'cut', 'win', 'op', 'hs', 'cls', 'sc', 'nb', 'city', 'zip',
        'yrb', 'sf', 'filed', 'heard', 'res', 'nc', 'fee', 'tsav', 'sAss', 'fAss', 'cap', 'panel', 'appr', 'ours', 'extra']
DICT = ["status", "by", "htype", "panel", "city", "firm", "extra", "nb", "appr", "agents", "bucket", "sc", "outcome", "zip", "cls"]
p["cls"] = p["sub"]
p["byv"] = p.appealedByType.map({"A": "AG", "O": "OW", "OTH": "OT"})
p["heard"] = np.where(p.formalStartMeeting.ne(""), p.formalStartMeeting, p.informalStartMeeting).astype(str)
p["htype"] = np.where(p.formalStartMeeting.ne(""), "Formal ARB", np.where(p.informalStartMeeting.ne(""), "Informal meeting", ""))
p["appr"] = np.where(p.formalAppraiser.ne(""), p.formalAppraiser, p.informalAppraiser)
p["appr"] = p.appr.str.replace(r"@.*$", "", regex=True)
p["win"] = (~p.op & (p.reduction > 0)).astype(int)
p["agents"] = p.agents_current.str.replace(r" \| ", "; ", regex=True)
p["outc"] = np.where(p.check_values, p.outcome + " · values flagged", p.outcome)
p["ext"] = np.where(p.final_source.str.startswith("certified"), "Final from certified roll", "")
src = {"firm": "firm", "agents": "agents", "by": "byv", "bucket": "path", "status": "appealStatus", "outcome": "outc",
       "htype": "htype", "s": "notice_value", "f": "final_value", "cut": "reduction", "win": "win", "op": "op", "hs": "homestead",
       "cls": "cls", "sc": "stateCd", "nb": "nb", "city": "city", "zip": "zip", "yrb": "yrb", "sf": "sf",
       "heard": "heard", "res": "finalizedDt", "nc": "n_appeals", "fee": "est_fee_1pct", "panel": "panelMembers",
       "appr": "appr", "ours": "is_ours", "extra": "ext"}
dicts = {c: [] for c in DICT}; dix = {c: {} for c in DICT}
def enc(c, x):
    if x is None or (isinstance(x, float) and np.isnan(x)) or (isinstance(x, str) and x.strip() in ("", "nan", "None")): return None
    if c in ("heard", "res"): return str(x)[:10]
    if c in ("yrb", "sf"):
        n = float(x); return int(n) if n > 0 else None
    if c in DICT:
        x = str(x).strip(); d = dix[c]
        if x not in d: d[x] = len(dicts[c]); dicts[c].append(x)
        return d[x]
    if isinstance(x, (bool, np.bool_)): return int(x)
    if isinstance(x, (np.integer, int)): return int(x)
    if isinstance(x, (float, np.floating)): return int(round(float(x)))
    return x
SH = 10
shards = [{"a": [], "r": [], "c": {c: [] for c in COLS}} for _ in range(SH)]
idx = []
for r in p.to_dict("records"):
    n = nid(r["pID"]); s = shards[jhash(n) % SH]
    row = [n, r["pID"], r["situs"] or None, r["owner"] or None]
    s["r"].append(len(s["a"])); s["a"].append(row); idx.append(row)
    for c in COLS:
        f = src.get(c)
        s["c"][c].append(2026 if c == "y" else enc(c, r.get(f)) if f else None)
for i, s in enumerate(shards): dump(s, SITE / f"acct/travis/{i}.txt")
dump(idx, SITE / "acct/travis/idx.txt")
dump({"county": "travis", "shards": SH, "cols": COLS, "dicts": dicts, "rows": len(p), "accounts": len(p), "hasText": True},
     SITE / "acct/travis/meta.txt")
print("search accounts", len(p))

# ---------- neighborhood lookup
LT = ["Under $200K", "$200K–$400K", "$400K–$600K", "$600K–$1M", "$1M+"]
tierOf = lambda x: 0 if x < 2e5 else 1 if x < 4e5 else 2 if x < 6e5 else 3 if x < 1e6 else 4
res = p[p["sub"].eq("Residential") & p.nb.ne("") & ~p.check_values & (p.notice_value > 0)].copy()
cnt = res[~res.firm.isin(special)].firm.value_counts(); big = cnt[cnt >= 200].index.tolist()
res["F"] = np.where(res.firm.isin(list(special) + big), res.firm, "Other agents (smaller firms)")
firms = ["Property Tax Protest (us)", "Owners (self-filed)", "No agent · other appellant"] + big + ["Other agents (smaller firms)"]
fi = {f: i for i, f in enumerate(firms)}; fi[US] = 0
city = res.groupby("nb").city.agg(lambda s: s[s.ne("")].mode().iloc[0].replace("CITY OF ", "").title() if s.ne("").any() else None)
nbs = sorted(res.nb.unique()); ni = {c: i for i, c in enumerate(nbs)}
res["t"] = res.notice_value.map(tierOf)
cl = res[~res.op].copy(); cl["c0"] = cl.reduction.clip(lower=0); cl["pc"] = cl.c0 / cl.notice_value
rows = [[0, ni[nb], fi[f], int(t), len(g), int(g.win.sum()), int(g.notice_value.sum()), int(g.c0.sum()), round(float(g.pc.sum()), 5)]
        for (nb, f, t), g in cl.groupby(["nb", "F", "t"])]
opn = [[0, ni[nb], fi[f], len(g)] for (nb, f), g in res[res.op].groupby(["nb", "F"])]
ol = [[0, r.pID, ni[r.nb], int(r.notice_value), None if r.op else int(r.final_value), None if r.op else int(max(r.reduction, 0)),
       {"ARB": "ARB hearing"}.get(r.path, r.path), bool(r.win), bool(r.op), None if r.op else int(round(max(r.reduction, 0) * 0.01))]
      for r in res[res.is_ours].itertuples()]
(SITE / "lookup").mkdir(parents=True, exist_ok=True)
(SITE / "lookup/travis.json").write_text(json.dumps({"years": [2026], "firms": firms, "us": 0, "tiers": LT,
    "nbs": [[c, city.get(c) if isinstance(city.get(c), str) else None] for c in nbs], "rows": rows, "open": opn, "ours": ol}, separators=(",", ":"), ensure_ascii=False))
print("lookup nbs", len(nbs), "ours", len(ol))
