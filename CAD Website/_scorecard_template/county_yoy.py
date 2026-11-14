"""Year-over-year section for the county scorecards, from <county>_history.csv (one row per property per season).

Adds (or replaces) <section id="yoy"> right after the Book & totals section (or Summary), plus a "Year over year"
link in the section menu. Nothing else on the page changes.

history columns: year, pid, res, who (us/agent/owner/other), firm, path, notice, final, reduction,
                 state (closed / open / flag / no_value / count_only)

Run:
  .venv/bin/python -I "CAD Website/_scorecard_template/county_yoy.py" <county> <page.html> [<county> <page.html> ...]
"""
import html
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TOP = 8
CAD = {"tarrant": "TAD", "travis": "TCAD", "montgomery": "MCAD", "denton": "DCAD"}

NOTES = {
    "tarrant": [
        "<b>2024</b> TAD Agent Summary review-board file (every 2024 case); our agency code that year was 00795. Final value = the case's final value, else the certified 2024 roll.",
        "<b>2025</b> TAD ARB file (open records request, same layout as 2026); agent 1487. TAD left the notice value blank on about half of the 2025 cases (52% of ours, 52% of other agents'), so 2025 rates and dollars use the half that has one.",
        "<b>2026</b> the corrected file behind the rest of this page.",
        "\"Withdrawn by joint motion\" is how TAD closes a settled joint motion after the season; it counts as informal here (92% of them end below notice).",
    ],
    "denton": [
        "<b>2023 and 2024</b> DCAD ProTax ARB exports (every protest, with starting and final market value).",
        "<b>2022</b> is left out: that file holds only about 34,000 protests (a partial export), and a quarter of our settled 2022 cases end above the notice value, against almost none in any other year, so its values can't be compared.",
        "<b>2025</b> is missing: the download has no 2025 protest file.",
        "<b>2026</b> the protax JSON build behind the rest of this page.",
        "Older files often name us \"PROPERTY TAX PROTEST\" without the ID; both forms count as ours (agent 245).",
    ],
    "montgomery": [
        "<b>2024</b> comes from MCAD's appraisal export of Jul 2, 2024 (after the filing deadline). It lists who protested and the ARB agent on the property, but carries <b>no notice value and no result</b>, so 2024 shows counts and share only; win rate and reductions are 2026-only.",
        "<b>2025</b> is missing: the \"2025\" export in the download was made in Jul 2026, and its protest list holds 2026 protests, not 2025.",
        "\"Value under protest\" for 2024 is the market value in that export, not a notice value.",
        "<b>2026</b> the protax JSON build behind the rest of this page.",
    ],
}


def key(name):
    k = re.sub(r"[^A-Z0-9]", "", str(name).upper())
    k = re.sub(r"^THE", "", k)
    return k[:16]


def groups(h):
    ag = h[h.who.eq("agent") & h.firm.ne("")].copy()
    ag["k"] = ag.firm.map(key)
    ly = h.year.max()
    vol = ag.groupby("k").size()
    recent = ag[ag.year.eq(ly)].groupby("k").size().reindex(vol.index).fillna(0)
    top = (vol * 0 + recent * 3 + vol).sort_values(ascending=False).head(TOP).index.tolist()
    disp = ag[ag.k.isin(top)].groupby("k").firm.agg(lambda s: s[ag.loc[s.index, "year"].eq(ag.loc[s.index, "year"].max())].mode().iat[0])
    h = h.copy()
    h["k"] = np.where(h.who.eq("agent"), h.firm.map(key), "")
    h["g"] = np.select([h.who.eq("us"), h.k.isin(top), h.who.eq("agent")], ["Property Tax Protest (us)", h.k.map(disp).fillna(""), "Other agents"],
                       default="Owners & others")
    names = ["Property Tax Protest (us)"] + [disp[k] for k in top] + ["Other agents", "Owners & others"]
    return h, names


def agg(d):
    c = d[d.state.eq("closed")]
    pct = (c.reduction / c.notice).clip(lower=0)
    return [len(d), int(d.state.eq("open").sum()), len(c), int((c.reduction > 0).sum()), float(c.notice.sum()),
            float(c.reduction.sum()), float(pct.sum()), int(d.path.eq("Informal").sum()), int(d.path.eq("ARB").sum()),
            int(d.path.isin(["No-show", "Withdrawn"]).sum()), int(d.state.eq("count_only").any()), float(d.notice.sum())]


def render(county, h):
    cad = CAD[county]
    h["notice"] = pd.to_numeric(h.notice, errors="coerce")
    h["reduction"] = pd.to_numeric(h.reduction, errors="coerce")
    h["res"] = h.res.astype(str).eq("True")
    h, names = groups(h)
    years = sorted(int(y) for y in h.year.unique())
    cube = {}
    for seg, d0 in (("all", h), ("res", h[h.res])):
        tot = {int(y): len(d) for y, d in d0.groupby("year")}
        rows = {}
        for g in names + ["All agents except us", "Everyone"]:
            sel = d0 if g == "Everyone" else d0[d0.who.eq("agent")] if g == "All agents except us" else d0[d0.g.eq(g)]
            rows[g] = {int(y): agg(sel[sel.year.eq(y)]) for y in years}
        cube[seg] = {"tot": tot, "rows": rows}
    cov = {}
    for y, d in h.groupby("year"):
        n = len(d)
        cov[int(y)] = {"n": n, "closed": int(d.state.eq("closed").sum()), "nov": int(d.state.eq("no_value").sum()),
                       "count_only": bool(d.state.eq("count_only").any())}
    D = {"years": years, "groups": names + ["All agents except us", "Owners & others", "Everyone"], "cube": cube, "cov": cov,
         "picks": [n for n in names[1:4]]}
    D["groups"] = list(dict.fromkeys(D["groups"]))
    data = json.dumps(D).replace("</", "<\\/")
    notes = "".join(f"<li>{x}</li>" for x in NOTES.get(county, []))
    yl = f"{years[0]}–{years[-1]}" if len(years) > 1 else str(years[0])
    missing = [y for y in range(years[0], years[-1] + 1) if y not in years]
    gap = f" ({', '.join(map(str, missing))} not available)" if missing else ""
    return f"""<!--yoy-start-->
<style>
#yoy .cmp-picks{{display:flex;flex-wrap:wrap;gap:6px}}
#yoy .cmp-picks button{{font:500 12.5px "Montserrat",sans-serif;border:1px solid var(--line);background:var(--surface-2,transparent);color:var(--ink-2);border-radius:999px;padding:5px 10px;cursor:pointer}}
#yoy .cmp-picks button[aria-pressed="true"]{{border-color:var(--ink-2);color:var(--ink);font-weight:600}}
#yoy .cmp-picks button i{{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:6px;vertical-align:0}}
#yoy svg text{{font:500 11px "IBM Plex Mono",monospace;fill:var(--ink-3)}}
#yoy td:not(:first-child),#yoy th:not(:first-child){{text-align:right}}
#yoy td.up{{color:var(--us)}} #yoy td.dn{{color:var(--bad,#c0392b)}}
#yoy .cov{{font-size:12.5px;color:var(--ink-2)}}
</style>
<section id="yoy">
  <div class="sec-head"><span class="eyebrow">Year over year</span><h2>How our seasons compare, {yl}</h2>
  <p class="lede">Every {cad} protest season in the files{gap}, one property per season, with the same rules as the rest of the page. Pick a metric and up to four firms to compare with us.</p></div>
  <div class="panel">
    <div class="filters">
      <div class="fgroup"><span class="eyebrow">Property type</span><div class="seg" id="yy-seg"></div></div>
      <div class="fgroup"><label class="eyebrow" for="yy-metric">Metric</label><select id="yy-metric"></select></div>
    </div>
    <div class="fgroup"><span class="eyebrow">Compare Property Tax Protest with (up to 4)</span><div class="cmp-picks" id="yy-cmp"></div></div>
    <div class="chart" id="yy-chart"></div>
    <div class="tbl-wrap"><table id="yy-tbl"><thead></thead><tbody></tbody></table></div>
    <p class="note" id="yy-note"></p>
  </div>
  <div class="panel"><h3>Property Tax Protest by season</h3><p class="small muted">Every metric for our book, season by season, with the change from the season before. Uses the property-type switch above.</p>
    <div class="tbl-wrap"><table id="yy-score"><thead></thead><tbody></tbody></table></div></div>
  <div class="panel"><h3>Where each season comes from</h3><p class="cov" id="yy-cov"></p><ul class="plain">{notes}</ul></div>
</section>
<script type="application/json" id="yy-data">{data}</script>
<script>
(function(){{
const D=JSON.parse(document.getElementById('yy-data').textContent),$=id=>document.getElementById(id);
const COL=['var(--us)','#c9822b','#5b7fbf','#9a5bb0','#3a9a8f'];
const esc=s=>String(s).replace(/[&<>"]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]));
const pct=(v,d=1)=>v==null||!isFinite(v)?'–':(v*100).toFixed(d)+'%';
const money=v=>{{if(v==null||!isFinite(v))return'–';const a=Math.abs(v),s=a>=1e9?'$'+(a/1e9).toFixed(2)+'B':a>=1e6?'$'+(a/1e6).toFixed(1)+'M':a>=1e3?'$'+(a/1e3).toFixed(0)+'K':'$'+a.toFixed(0);return(v<0?'−':'')+s}};
const num=v=>v==null||!isFinite(v)?'–':Math.round(v).toLocaleString('en-US');
// a = [n, open, closed, won, notice, cut, pctsum, informal, arb, noshow_wd, count_only, value]
const M={{
 n:{{l:'Properties protested',f:(a)=>a[0],fmt:num,res:0}},
 share:{{l:'Share of all protests',f:(a,t)=>t?a[0]/t:null,fmt:v=>pct(v),res:0}},
 win:{{l:'Win rate (any reduction)',f:a=>a[2]?a[3]/a[2]:null,fmt:v=>pct(v),res:1}},
 avg:{{l:'Avg % cut per property',f:a=>a[2]?a[6]/a[2]:null,fmt:v=>pct(v),res:1}},
 cutp:{{l:'Cut % of notice value',f:a=>a[4]?a[5]/a[4]:null,fmt:v=>pct(v),res:1}},
 cut:{{l:'Total market value cut',f:a=>a[2]?a[5]:null,fmt:money,res:1}},
 inf:{{l:'Informal share (of settled)',f:a=>(a[7]+a[8])?a[7]/(a[7]+a[8]):null,fmt:v=>pct(v),res:1}},
 arb:{{l:'ARB hearings',f:a=>a[8],fmt:num,res:1}},
 lost:{{l:'No-show / withdrawn',f:a=>a[9],fmt:num,res:1}},
 val:{{l:'Value under protest',f:a=>a[4]||a[11],fmt:money,res:0}}
}};
const S={{seg:'all',m:'win',picks:D.picks.slice(0,3)}};
const co=y=>D.cov[y]&&D.cov[y].count_only;
function val(g,y,k){{const c=D.cube[S.seg],a=c.rows[g]&&c.rows[g][y];if(!a||!a[0])return null;if(M[k].res&&co(y))return null;return M[k].f(a,c.tot[y])}}
const segEl=$('yy-seg');segEl.innerHTML=[['all','All types'],['res','Residential']].map(([v,l])=>`<button type="button" data-v="${{v}}" aria-pressed="${{v==S.seg}}">${{l}}</button>`).join('');
segEl.onclick=e=>{{const b=e.target.closest('button');if(!b)return;S.seg=b.dataset.v;segEl.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));draw()}};
const ms=$('yy-metric');ms.innerHTML=Object.entries(M).map(([k,o])=>`<option value="${{k}}">${{o.l}}</option>`).join('');ms.value=S.m;ms.onchange=()=>{{S.m=ms.value;draw()}};
function picks(){{const el=$('yy-cmp');el.innerHTML=D.groups.slice(1).map(g=>{{const i=S.picks.indexOf(g);return `<button type="button" data-g="${{esc(g)}}" aria-pressed="${{i>=0}}">${{i>=0?`<i style="background:${{COL[i+1]}}"></i>`:''}}${{esc(g)}}</button>`}}).join('');
  el.onclick=e=>{{const b=e.target.closest('button');if(!b)return;const g=b.dataset.g,i=S.picks.indexOf(g);if(i>=0)S.picks.splice(i,1);else if(S.picks.length<4)S.picks.push(g);else return;draw()}}}}
function chart(){{const G=[D.groups[0],...S.picks],Y=D.years,W=720,H=240,L=56,B=28,T=10,gw=(W-L-10)/Y.length,bw=Math.min(28,(gw-16)/G.length);
  const vs=[];G.forEach(g=>Y.forEach(y=>{{const v=val(g,y,S.m);if(v!=null)vs.push(v)}}));const mx=Math.max(1e-9,...vs.map(Math.abs)),fmt=M[S.m].fmt;
  let s=`<svg viewBox="0 0 ${{W}} ${{H}}" width="100%" role="img" aria-label="${{esc(M[S.m].l)}} by season">`;
  for(let i=0;i<=4;i++){{const v=mx*i/4,yy=H-B-(H-B-T)*i/4;s+=`<line x1="${{L}}" x2="${{W-10}}" y1="${{yy}}" y2="${{yy}}" stroke="var(--line)"/><text x="${{L-6}}" y="${{yy+4}}" text-anchor="end">${{fmt(v)}}</text>`}}
  Y.forEach((y,yi)=>{{const x0=L+yi*gw+(gw-bw*G.length)/2;G.forEach((g,gi)=>{{const v=val(g,y,S.m);if(v==null)return;const hh=(H-B-T)*Math.max(0,v)/mx;
    s+=`<rect x="${{x0+gi*bw}}" y="${{H-B-hh}}" width="${{bw-3}}" height="${{hh}}" rx="2" fill="${{COL[gi]}}"><title>${{esc(g)}} ${{y}}: ${{fmt(v)}}</title></rect>`}});
    s+=`<text x="${{L+yi*gw+gw/2}}" y="${{H-8}}" text-anchor="middle">${{y}}${{co(y)&&M[S.m].res?' (no results)':''}}</text>`}});
  $('yy-chart').innerHTML=s+'</svg>'}}
function table(){{const G=[D.groups[0],...S.picks,'All agents except us','Everyone'].filter((g,i,a)=>a.indexOf(g)==i),Y=D.years,fmt=M[S.m].fmt;
  $('yy-tbl').tHead.innerHTML='<tr><th>'+esc(M[S.m].l)+'</th>'+Y.map(y=>`<th>${{y}}</th>`).join('')+'</tr>';
  $('yy-tbl').tBodies[0].innerHTML=G.map((g,gi)=>`<tr${{gi==0?' class="us"':''}}><td>${{gi<=S.picks.length?`<i style="display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:6px;background:${{COL[gi]}}"></i>`:''}}${{esc(g)}}</td>`+Y.map(y=>`<td class="num">${{fmt(val(g,y,S.m))}}</td>`).join('')+'</tr>').join('');
  $('yy-note').textContent=D.years.some(co)&&M[S.m].res?'Seasons marked "no results" have no notice value or protest result in the files, so this metric can only be shown for the other seasons.':''}}
function score(){{const Y=D.years,g=D.groups[0];$('yy-score').tHead.innerHTML='<tr><th>Metric</th>'+Y.map((y,i)=>`<th>${{y}}</th>`+(i?'<th>Change</th>':'')).join('')+'</tr>';
  $('yy-score').tBodies[0].innerHTML=Object.entries(M).map(([k,o])=>'<tr><td>'+o.l+'</td>'+Y.map((y,i)=>{{const v=val(g,y,k);let c='';if(i){{const p=val(g,Y[i-1],k);if(v!=null&&p!=null){{const d=v-p,isP=['share','win','avg','cutp','inf'].includes(k);c=`<td class="num ${{d>0?'up':d<0?'dn':''}}">${{(d>0?'+':'')+(isP?(d*100).toFixed(1)+' pp':o.fmt(d))}}</td>`}}else c='<td class="num">–</td>'}}return `<td class="num">${{o.fmt(v)}}</td>`+c}}).join('')+'</tr>').join('')}}
function cov(){{$('yy-cov').innerHTML=D.years.map(y=>{{const c=D.cov[y];return `<b>${{y}}</b>: ${{num(c.n)}} protested properties`+(c.count_only?' (counts only)':`, ${{num(c.closed)}} closed with usable values`+(c.nov?`, ${{num(c.nov)}} without a notice value`:''))}}).join(' · ')}}
function draw(){{picks();chart();table();score()}}
cov();draw()}})();
</script>
<!--yoy-end-->"""


def inject(page, section):
    h = Path(page).read_text(encoding="utf-8")
    h = re.sub(r"<!--yoy-start-->.*?<!--yoy-end-->\n?", "", h, flags=re.S)
    h = h.replace('<a href="#yoy">Year over year</a>', "")
    anchor = '<a href="#business">Book &amp; totals</a>' if "#business" in h else '<a href="#summary">Summary</a>'
    h = h.replace(anchor, anchor + '<a href="#yoy">Year over year</a>', 1)
    if "<!--biz-end-->" in h:
        j = h.index("<!--biz-end-->") + len("<!--biz-end-->")
    else:
        i = h.index('<section id="summary">')
        j = h.index("</section>", i) + len("</section>")
    h = h[:j] + "\n" + section + h[j:]
    Path(page).write_text(h, encoding="utf-8")


def main(args):
    for county, page in zip(args[::2], args[1::2]):
        county = county.lower()
        h = pd.read_csv(ROOT / county.capitalize() / "output" / f"{county}_history.csv", dtype={"pid": str, "firm": str},
                        keep_default_na=False, na_values=[""])
        h["firm"] = h.firm.fillna("")
        h["path"] = h.path.fillna("")
        inject(page, render(county, h))
        print(f"{county}: year-over-year section added to {page}")


if __name__ == "__main__":
    main(sys.argv[1:])
