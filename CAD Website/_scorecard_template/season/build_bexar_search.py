"""Bexar account-search shards (acct/bexar/*) and neighborhood lookup (lookup/bexar.json), same formats as the
Travis / Tarrant pages (see ../build_travis_page.py), from output/bexar_values_2026.csv.

Run:  .venv/bin/python -I "CAD Website/_scorecard_template/season/build_bexar_search.py" <site dir>
"""
import base64
import gzip
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
SITE = Path(sys.argv[1])
US = "PROPERTY TAX PROTEST"
OWN, NOAG = "Owners (self-filed)", "No agent · other appellant"

v = pd.read_csv(ROOT / "Bexar/output/bexar_values_2026.csv", dtype=str, keep_default_na=False)
p = v[v.protested.eq("True")].copy()
for c in ["notice_value", "final_value", "reduction", "est_fee_1pct", "rows_for_account"]:
    p[c] = pd.to_numeric(p[c], errors="coerce")
for c in ["is_ours", "check_values", "homestead"]:
    p[c] = p[c].eq("True")


def canon(n):
    u = n.upper().strip()
    if "OWNWELL" in u: return "Ownwell"
    if u.startswith("RYAN") and "LAW" not in u: return "Ryan (all codes)"
    if "CONNOR" in u and u.startswith("O"): return "O'Connor & Associates"
    return re.sub(r"\s+", " ", n.strip())


p["firm"] = np.select([p.is_ours, p.agent.ne("") & p.agent_name.ne(""), p.agent.ne(""), p.appealedByType.eq("Owner")],
                      [US, p.agent_name.map(canon), "Agent #" + p.agent, OWN], default=NOAG)
p["sub"] = np.where(p.stateCd.str.upper().str.startswith("A"), "Residential", "Non-residential")
p["op"] = p.path.eq("Open")
p["win"] = (~p.op & (p.reduction > 0)).astype(int)
p["nb"] = p.nb.replace("UNASSIGNED", "")
special = {US, OWN, NOAG}


def dump(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64encode(gzip.compress(json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode(), 9)))


nid = lambda s: re.sub(r"[^A-Z0-9]", "", str(s).upper()).lstrip("0")


def jhash(s):
    h = 0
    for ch in s:
        h = (h * 31 + ord(ch)) % 4294967296
    return h


# ---------- account search
COLS = ['y', 'firm', 'agents', 'by', 'bucket', 'status', 'outcome', 'htype', 's', 'f', 'cut', 'win', 'op', 'hs', 'cls', 'sc', 'nb', 'city', 'zip',
        'yrb', 'sf', 'filed', 'heard', 'res', 'nc', 'fee', 'tsav', 'sAss', 'fAss', 'cap', 'panel', 'appr', 'ours', 'extra']
DICT = ["status", "by", "htype", "panel", "city", "firm", "extra", "nb", "appr", "agents", "bucket", "sc", "outcome", "zip", "cls"]
p["cls"] = p["sub"]
p["byv"] = p.appealedByType.map({"Agent": "AG", "Owner": "OW"})
p["heard"] = p.hearing_dt.where(~p.hearing_dt.str.startswith("1900"), "")
p["resd"] = p.resolved_dt.where(~p.resolved_dt.str.startswith("1900"), p.consent_dt.where(~p.consent_dt.str.startswith("1900"), ""))
p["htype"] = p.path.map({"ARB": "Formal ARB", "Informal": "Informal"}).fillna("")
p["agents"] = p.agents_current
p["outc"] = np.where(p.check_values, p.outcome + " · values flagged", p.outcome)
p["ext"] = "BCAD agent export (Oct 26) + appraisal export (Oct 15)"
src = {"firm": "firm", "agents": "agents", "by": "byv", "bucket": "path", "status": "status", "outcome": "outc",
       "htype": "htype", "s": "notice_value", "f": "final_value", "cut": "reduction", "win": "win", "op": "op", "hs": "homestead",
       "cls": "cls", "sc": "stateCd", "nb": "nb", "city": "city", "zip": "zip", "yrb": "yrb", "sf": "sf",
       "heard": "heard", "res": "resd", "nc": "rows_for_account", "fee": "est_fee_1pct", "panel": "arb_panel",
       "ours": "is_ours", "extra": "ext"}
dicts = {c: [] for c in DICT}
dix = {c: {} for c in DICT}


def enc(c, x):
    if x is None or (isinstance(x, float) and np.isnan(x)) or (isinstance(x, str) and x.strip() in ("", "nan", "None")): return None
    if c in ("heard", "res"): return str(x)[:10]
    if c in ("yrb", "sf"):
        try:
            n = float(x)
        except ValueError:
            return None
        return int(n) if n > 0 else None
    if c in DICT:
        x = str(x).strip(); d = dix[c]
        if x not in d: d[x] = len(dicts[c]); dicts[c].append(x)
        return d[x]
    if isinstance(x, (bool, np.bool_)): return int(x)
    if isinstance(x, (np.integer, int)): return int(x)
    if isinstance(x, (float, np.floating)): return int(round(float(x)))
    return x


SH = 14
shards = [{"a": [], "r": [], "c": {c: [] for c in COLS}} for _ in range(SH)]
idx = []
for r in p.to_dict("records"):
    n = nid(r["account"]); s = shards[jhash(n) % SH]
    row = [n, r["account"], r["situs"] or None, r["owner"] or None]
    s["r"].append(len(s["a"])); s["a"].append(row); idx.append(row)
    for c in COLS:
        f = src.get(c)
        s["c"][c].append(2026 if c == "y" else enc(c, r.get(f)) if f else None)
for i, s in enumerate(shards): dump(s, SITE / f"acct/bexar/{i}.txt")
dump(idx, SITE / "acct/bexar/idx.txt")
dump({"county": "bexar", "shards": SH, "cols": COLS, "dicts": dicts, "rows": len(p), "accounts": len(p), "hasText": True},
     SITE / "acct/bexar/meta.txt")
print("search accounts", len(p))

# ---------- neighborhood lookup (residential)
LT = ["Under $200K", "$200K–$400K", "$400K–$600K", "$600K–$1M", "$1M+"]
tierOf = lambda x: 0 if x < 2e5 else 1 if x < 4e5 else 2 if x < 6e5 else 3 if x < 1e6 else 4
res = p[p["sub"].eq("Residential") & p.nb.ne("") & ~p.check_values & (p.notice_value > 0)].copy()
cnt = res[~res.firm.isin(special)].firm.value_counts(); big = cnt[cnt >= 200].index.tolist()
res["F"] = np.where(res.firm.isin(list(special) + big), res.firm, "Other agents (smaller firms)")
firms = ["Property Tax Protest (us)", OWN, NOAG] + big + ["Other agents (smaller firms)"]
fi = {f: i for i, f in enumerate(firms)}; fi[US] = 0
city = res.groupby("nb").city.agg(lambda s: s[s.ne("")].mode().iloc[0].title() if s.ne("").any() else None)
nbs = sorted(res.nb.unique()); ni = {c: i for i, c in enumerate(nbs)}
res["t"] = res.notice_value.map(tierOf)
cl = res[~res.op].copy(); cl["c0"] = cl.reduction.clip(lower=0); cl["pc"] = cl.c0 / cl.notice_value
rows = [[0, ni[nb], fi[f], int(t), len(g), int(g.win.sum()), int(g.notice_value.sum()), int(g.c0.sum()), round(float(g.pc.sum()), 5)]
        for (nb, f, t), g in cl.groupby(["nb", "F", "t"])]
opn = [[0, ni[nb], fi[f], len(g)] for (nb, f), g in res[res.op].groupby(["nb", "F"])]
ol = [[0, r.account, ni[r.nb], int(r.notice_value), None if r.op else int(r.final_value), None if r.op else int(max(r.reduction, 0)),
       {"ARB": "ARB hearing"}.get(r.path, r.path), bool(r.win), bool(r.op), None if r.op else int(round(max(r.reduction, 0) * 0.01))]
      for r in res[res.is_ours].itertuples()]
(SITE / "lookup").mkdir(parents=True, exist_ok=True)
(SITE / "lookup/bexar.json").write_text(json.dumps({"years": [2026], "firms": firms, "us": 0, "tiers": LT,
    "nbs": [[c, city.get(c) if isinstance(city.get(c), str) else None] for c in nbs], "rows": rows, "open": opn, "ours": ol},
    separators=(",", ":"), ensure_ascii=False))
print("lookup nbs", len(nbs), "ours", len(ol), "firms", len(firms))
