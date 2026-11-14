"""Business view for the 2026 county scorecards: how our client list becomes protests, what those protests
returned, and the full season table (us vs. other agents vs. owners) from <county>_values_2026_summary.csv.

Adds (or replaces) a <section id="business"> right after the Summary section of each county page, plus a
"Book & totals" link in the section menu. Nothing else on the page changes.

Run:
  .venv/bin/python -I "CAD Website/_scorecard_template/county_business_2026.py" <county> <page.html> [<county> <page.html> ...]
"""
import html
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OURS = {"tarrant": {"1487"}, "travis": {"1863738", "1898343", "1898284"}, "montgomery": {"654513"}, "denton": {"245"}, "dallas": {"306"}, "rockwall": {"1044073", "1044084"}}
CAD = {"tarrant": "TAD", "travis": "TCAD", "montgomery": "MCAD", "denton": "DCAD", "dallas": "DCAD", "rockwall": "RCAD"}
EXPORT = {"travis": "Oct 6", "montgomery": "Aug 4", "denton": "Jul 27", "dallas": "Oct 30", "rockwall": "Oct 9"}


def n(x):
    return f"{int(x):,}"


def money(x):
    if x is None or pd.isna(x):
        return "–"
    a = abs(x)
    s = f"${a / 1e9:,.2f}B" if a >= 1e9 else f"${a / 1e6:,.1f}M" if a >= 1e6 else f"${a / 1e3:,.0f}K" if a >= 1e3 else f"${a:,.0f}"
    return ("−" if x < 0 else "") + s


def pct(x, d=1):
    return "–" if x is None or pd.isna(x) else f"{x * 100:.{d}f}%"


def results(v):
    """Our protests: outcomes, paths and dollars (rates leave out open and flagged, as the scorecards do)."""
    o = v[v.is_ours.eq("True")].copy()
    for c in ["notice_value", "final_value", "reduction", "est_fee_1pct"]:
        o[c] = pd.to_numeric(o[c], errors="coerce")
    flag = o.check_values.eq("True")
    op = o.path.eq("Open")
    cl = o[~op & ~flag]
    return {
        "total": len(o), "open": int(op.sum()), "flagged": int((flag & ~op).sum()), "closed": len(cl),
        "reduced": int((cl.reduction > 0).sum()), "nochange": int((cl.reduction == 0).sum()),
        "increased": int((cl.reduction < 0).sum()),
        "win": (cl.reduction > 0).mean() if len(cl) else np.nan,
        "notice": cl.notice_value.sum(), "final": cl.final_value.sum(), "cut": cl.reduction.sum(),
        "cut_pct": cl.reduction.sum() / cl.notice_value.sum() if cl.notice_value.sum() else np.nan,
        "fee": (cl.reduction.clip(lower=0) * 0.01).sum(),
        "paths": o.path.value_counts().to_dict(),
    }


def funnel_json(county, v):
    """Agent of record (protax JSON owners[].agents) -> who filed the 2026 protest."""
    ids = OURS[county]
    pat = "|".join(re.escape(i) for i in ids)
    listed = v.agent_ids_all.str.split(r" \| ").apply(lambda l: bool(ids & set(l)))
    active = v.agents_current.str.contains(rf"\((?:{pat})\)", regex=True)
    ours = v.is_ours.eq("True")
    prot = v.protested.eq("True")
    L = v[listed]
    # names for the agents that filed instead of us
    names = {}
    for s in v.loc[listed, "agents_all"]:
        for nm, k in re.findall(r"([^|]+?) \((\d+)\)", s):
            names.setdefault(k, nm.strip())
    other = L[prot[listed] & ~ours[listed]].copy()
    by = np.where(other.agent.ne(""), other.agent.map(lambda k: names.get(k, f"Agent {k}")),
                  np.where(other.appealedByType.str.upper().str.startswith("O"), "The owner", "Other appellant"))
    top = pd.Series(by).value_counts()
    lst = (L.is_ours.eq("True"))
    f = {
        "listed": int(listed.sum()), "active": int((listed & active).sum()), "expired": int((listed & ~active).sum()),
        "filed_us": int((listed & ours).sum()), "filed_other": int((listed & prot & ~ours).sum()),
        "not_protested": int((listed & ~prot).sum()), "us_not_listed": int((~listed & ours).sum()),
        "ours": int(ours.sum()),
        "active_other": int((listed & active & prot & ~ours).sum()),
        "active_none": int((listed & active & ~prot).sum()),
        "expired_other": int((listed & ~active & prot & ~ours).sum()),
        "expired_none": int((listed & ~active & ~prot).sum()),
        "top_other": [(k, int(c)) for k, c in top.head(8).items()], "other_rest": int(top.iloc[8:].sum()),
    }
    assert f["filed_us"] + f["us_not_listed"] == f["ours"] and lst.sum() == f["filed_us"]
    return f


def funnel_tarrant(v):
    arb = pd.read_csv(ROOT / "Tarrant/Data/ORR20261019 - Avetik Ghazaryan - ARB Info 2026.csv", dtype=str,
                      keep_default_na=False, usecols=["pID", "agentID", "CaseNumber"])
    o = arb[arb.agentID.str.strip().eq("1487")]
    ours = v[v.is_ours.eq("True")]
    return {"cases": int(o.CaseNumber.nunique()), "accounts": int(o.pID.nunique()), "ours": len(ours),
            "shared": int(ours.shared_with_other_agent.eq("True").sum()),
            "multi": int((o.groupby("pID").size() > 1).sum())}


def season_table(county):
    s = pd.read_csv(ROOT / county.capitalize() / "output" / f"{county}_values_2026_summary.csv", keep_default_na=False)
    s["RP"] = s.RP.replace("", "Not in roll").astype(str)
    order = {"Property Tax Protest (us)": 0, "Other agents": 1, "Owners": 2}
    s["o"] = s.who.map(order).fillna(3)
    s = s.sort_values(["RP", "o"])
    rps = ["ALL"] + (["Residential"] if "Residential" in set(s.RP) else []) + \
          sorted(r for r in s.RP.unique() if r not in ("ALL", "Residential"))
    rows = []
    for _, r in s.iterrows():
        g = lambda c: pd.to_numeric(r[c], errors="coerce")
        rows.append([r.RP, r.who, n(r.accounts), n(r.open), n(r.flagged_values), n(r.closed_with_result), n(r.reduced),
                     pct(g("win_rate")), n(r.informal), n(r.arb_hearing), n(r.fta), n(r.withdrawn),
                     money(g("notice_total")), money(g("final_total")), money(g("reduction_total")),
                     pct(g("reduction_pct_of_notice")), pct(g("avg_reduction_pct")), pct(g("median_reduction_pct"))])
    return rps, rows


RP_LABEL = {"ALL": "All types", "Residential": "Residential (A*)", "R": "Real (R)", "P": "Personal (P)",
            "MH": "Mobile home (MH)", "MN": "Mineral (MN)", "C": "Commercial (C)", "M": "Mixed / other (M)",
            "A": "Auto (A)", "Not in roll": "Not in roll"}


def step(label, v, s, us=False):
    return f'<div class="step{" us" if us else ""}"><span class="eyebrow">{label}</span><span class="v">{v}</span><span class="s">{s}</span></div>'


def render(county, v):
    cad = CAD[county]
    r = results(v)
    p = r["paths"]
    if county == "tarrant":
        f = funnel_tarrant(v)
        flow = "".join([
            step("ARB cases filed by us", n(f["cases"]), f"Rows in {cad}'s 2026 ARB file with agent 1487"),
            step("Accounts", n(f["accounts"]), f"{n(f['multi'])} accounts had a second case (refiled or set up twice)"),
            step("Shared with another agent", n(f["shared"]), "The same case also lists another firm. It still counts as ours"),
            step("Our 2026 protests", n(f["ours"]), "One row per account on this page", us=True),
        ])
        expl = (f"<p class=\"small muted\">{cad} doesn't publish an agent-of-record list, so this starts from the ARB file. "
                "Clients who signed with us but had no 2026 case filed under agent 1487 can't be seen here; the agent portal is the place to count them.</p>")
        lost = ""
    else:
        f = funnel_json(county, v)
        flow = "".join([
            step("Properties listing us as agent", n(f["listed"]), f"{cad} owner records, any time ({n(f['active'])} active on {EXPORT[county]}, {n(f['expired'])} expired)"),
            step("We filed the 2026 protest", n(f["filed_us"]), "Counted as ours on this page"),
            step("Someone else filed", n(f["filed_other"]), "Counted for the firm or owner who filed"),
            step("Nobody protested", n(f["not_protested"]), "No 2026 protest on the property"),
            step("Plus: filed by us, not listed", n(f["us_not_listed"]), f"Our protest, but {cad}'s agent list doesn't show us"),
            step("Our 2026 protests", n(f["ours"]), "One row per property on this page", us=True),
        ])
        expl = ""
        if county == "denton":
            expl = ('<p class="small muted">denton_agents_2026.csv shows 3,413 for us because it counts agent listings, not properties: '
                    "9 properties list us under two owners. It also includes expired authorizations.</p>")
        top = "".join(f"<tr><td>{html.escape(k)}</td><td class=\"num\">{n(c)}</td></tr>" for k, c in f["top_other"])
        if f["other_rest"]:
            top += f"<tr><td>Everyone else</td><td class=\"num\">{n(f['other_rest'])}</td></tr>"
        lost = f"""
  <div class="grid2">
    <div class="panel"><h3>Listed with us, but we didn't file</h3>
      <p class="small muted">{n(f['filed_other'] + f['not_protested'])} properties. An expired authorization most likely means the client moved on;
      an active one with no protest from us is worth checking in the agent portal.</p>
      <div class="tbl-wrap"><table><thead><tr><th>Authorization</th><th>Someone else filed</th><th>Nobody protested</th><th>Total</th></tr></thead><tbody>
        <tr><td>Active on {EXPORT[county]}</td><td class="num">{n(f['active_other'])}</td><td class="num">{n(f['active_none'])}</td><td class="num"><b>{n(f['active_other'] + f['active_none'])}</b></td></tr>
        <tr><td>Expired</td><td class="num">{n(f['expired_other'])}</td><td class="num">{n(f['expired_none'])}</td><td class="num">{n(f['expired_other'] + f['expired_none'])}</td></tr>
      </tbody></table></div></div>
    <div class="panel"><h3>Who filed instead of us</h3><p class="small muted">The filer of the deciding 2026 protest on the {n(f['filed_other'])} properties above.</p>
      <div class="tbl-wrap"><table><thead><tr><th>Filed by</th><th>Properties</th></tr></thead><tbody>{top}</tbody></table></div></div>
  </div>"""

    pth = " · ".join(f"{k} {n(c)}" for k, c in sorted(p.items(), key=lambda x: -x[1]))
    res = "".join([
        step("Our protests", n(r["total"]), pth),
        step("Still open", n(r["open"]), "No final value yet; left out of rates and dollars"),
        step("Values flagged", n(r["flagged"]), "Notice missing or final far above notice; left out"),
        step("Closed with a result", n(r["closed"]), f"{n(r['reduced'])} reduced · {n(r['nochange'])} no change · {n(r['increased'])} increased"),
        step("Win rate", pct(r["win"]), "Share of closed protests with any reduction", us=True),
    ])
    kp = "".join(f'<div class="kpi"><span class="eyebrow">{a}</span><span class="v">{b}</span><span class="d">{c}</span></div>' for a, b, c in [
        ("Notice value, closed", money(r["notice"]), f"{n(r['closed'])} closed protests"),
        ("Final value", money(r["final"]), "After informal settlement or ARB"),
        ("Market value cut", money(r["cut"]), f"{pct(r['cut_pct'])} of notice"),
        ("Fee estimate (1%)", money(r["fee"]), "1% of the cut, before caps and collections"),
    ])
    rps, rows = season_table(county)
    data = json.dumps({"rps": [[x, RP_LABEL.get(x, x)] for x in rps], "rows": rows}).replace("</", "<\\/")
    return f"""<!--biz-start-->
<style>
#business .flow{{margin-bottom:16px}}
#business .flow .step.us{{border-color:var(--us);background:var(--us-soft)}}
#business .flow .step.us .v{{color:var(--us-ink)}}
#business .kpis{{margin:0 0 16px}}
#biz-tbl td:nth-child(n+2){{text-align:right}}
#biz-tbl td:first-child{{white-space:nowrap}}
#biz-tbl th{{white-space:nowrap}}
</style>
<section id="business">
  <div class="sec-head"><span class="eyebrow">Book &amp; totals</span><h2>From client list to results, and the whole season in one table</h2>
  <p class="lede">How many properties list us as their agent, how many of those we actually protested in 2026, what those protests returned,
  and the complete {cad} season split by who filed: us, other agents and owners.</p></div>
  <div class="panel"><h3>Our client list → our 2026 protests</h3>{expl}<div class="flow">{flow}</div></div>
  {lost}
  <div class="panel"><h3>What our protests returned</h3><div class="flow">{res}</div><div class="kpis">{kp}</div>
  <p class="note">Dollars are market value on closed protests with clean values: notice minus final. The fee estimate is not invoiced revenue.</p></div>
  <div class="panel"><h3>The full season: us vs. other agents vs. owners</h3>
    <p class="small muted">Every 2026 protest in {cad}, one row per property, grouped by who filed the deciding protest. Rates and dollars use closed protests and leave out flagged values. Same numbers as {county}_values_2026_summary.csv.</p>
    <div class="filters"><div class="fgroup"><span class="eyebrow">Property type</span><div class="seg" id="biz-rp"></div></div></div>
    <div class="tbl-wrap"><table id="biz-tbl"><thead><tr><th>Filed by</th><th>Properties</th><th>Open</th><th>Flagged</th><th>Closed</th><th>Reduced</th><th>Win rate</th><th>Informal</th><th>ARB hearing</th><th>No-show</th><th>Withdrawn / dismissed</th><th>Notice $</th><th>Final $</th><th>Cut $</th><th>Cut % of notice</th><th>Avg % / property</th><th>Median %</th></tr></thead><tbody></tbody></table></div>
    <p class="note">Win rate = closed protests with any reduction. Cut % of notice = total cut ÷ total notice. Avg % / property averages each property's own cut (no change counts as 0%).</p>
  </div>
</section>
<script type="application/json" id="biz-data">{data}</script>
<script>
(function(){{const B=JSON.parse(document.getElementById('biz-data').textContent);let cur='ALL';
const el=document.getElementById('biz-rp'),tb=document.querySelector('#biz-tbl tbody');
const esc=s=>String(s).replace(/[&<>"]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]));
function draw(){{tb.innerHTML=B.rows.filter(r=>r[0]===cur).map(r=>`<tr${{r[1].startsWith('Property Tax Protest')?' class="us"':''}}>`+r.slice(1).map((c,i)=>`<td${{i?' class="num"':''}}>${{esc(c)}}</td>`).join('')+'</tr>').join('')}}
el.innerHTML=B.rps.map(([v,l])=>`<button type="button" data-v="${{esc(v)}}" aria-pressed="${{v===cur}}">${{esc(l)}}</button>`).join('');
el.onclick=e=>{{const b=e.target.closest('button');if(!b)return;cur=b.dataset.v;el.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));draw()}};draw()}})();
</script>
<!--biz-end-->"""


def inject(page, section):
    h = Path(page).read_text(encoding="utf-8")
    h = re.sub(r"<!--biz-start-->.*?<!--biz-end-->\n?", "", h, flags=re.S)
    h = h.replace('<a href="#business">Book &amp; totals</a>', "")
    h = h.replace('<a href="#summary">Summary</a>', '<a href="#summary">Summary</a><a href="#business">Book &amp; totals</a>', 1)
    i = h.index('<section id="summary">')
    j = h.index("</section>", i) + len("</section>")
    h = h[:j] + "\n" + section + h[j:]
    Path(page).write_text(h, encoding="utf-8")


def main(args):
    for county, page in zip(args[::2], args[1::2]):
        county = county.lower()
        src = ROOT / county.capitalize() / "output" / f"{county}_values_2026.csv"
        v = pd.read_csv(src, dtype=str, keep_default_na=False)
        inject(page, render(county, v))
        print(f"{county}: section added to {page}")


if __name__ == "__main__":
    main(sys.argv[1:])
