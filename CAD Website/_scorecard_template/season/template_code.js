const US='PROPERTY TAX PROTEST', OWN='Ownwell (Inc + CRE)', YEARS=D.seasons||[2023,2024,2025,2026];
(CFG.remove||[]).forEach(([sel,up])=>{const e=document.querySelector(sel);if(!e)return;const t=up?e.closest(up):e;if(t)t.remove()});
document.querySelectorAll('.grid2').forEach(g=>{if(!g.children.length)g.remove()});{const lone=[...document.querySelectorAll('.grid2')].filter(g=>g.children.length==1);for(let i=0;i+1<lone.length;i++){const a=lone[i],b=lone[i+1];if(a.parentElement===b.parentElement&&a.closest('section')===b.closest('section')){a.appendChild(b.firstElementChild);b.remove();i++}}}
(CFG.text||[]).forEach(([sel,html])=>{const e=document.querySelector(sel);if(e)e.innerHTML=html});
const LASTY=YEARS[YEARS.length-1], PREVY=YEARS.length>1?YEARS[YEARS.length-2]:null;
const HASOWN=(D.firms||[]).includes(OWN);
const FEERANGE=y=>(D.feeRangeYears||[]).includes(+y);
const feeTxt=(u,y)=>FEERANGE(y)?`${fmt.usd(u.feeLo)}–${fmt.usd(u.fee)}`:fmt.usd(u.fee);
function hideSec(id,why){const el=document.getElementById(id);if(!el)return;const lab=(el.querySelector('.eyebrow')||{}).textContent||id;el.innerHTML=`<div class="sec-head"><span class="eyebrow">${esc(lab)}</span><p class="note" style="font-size:13.5px">Hidden for ${esc(CFG.county)}: ${why}</p></div>`;el.classList.add('hiddensec');const a=document.querySelector(`nav.toc a[href="#${id}"]`);if(a)a.remove()}
const $=s=>document.querySelector(s);
const fmt={
  pct:(v,dp=1)=>v==null||isNaN(v)?'–':(v*100).toFixed(dp)+'%',
  pp:v=>(v>0?'+':'')+(v*100).toFixed(2),
  int:v=>v==null||isNaN(v)?'–':Math.round(v).toLocaleString('en-US'),
  usd:v=>{if(v==null||isNaN(v))return'–';const a=Math.abs(v),s=v<0?'−':'';return a>=1e9?s+'$'+(a/1e9).toFixed(2)+'B':a>=1e6?s+'$'+(a/1e6).toFixed(1)+'M':a>=1e3?s+'$'+(a/1e3).toFixed(0)+'K':s+'$'+a.toFixed(0)}
};
const nice=n=>{if(n==US)return 'Property Tax Protest';if(n=='Other agents'&&!CFG.firms)return 'All other agents';if(n=='Owners (self-filed)'&&CFG.ownersLabel)return CFG.ownersLabel;if(n==OWN)return 'Ownwell';if(n.startsWith('Ryan LLC'))return 'Ryan (all codes)';if(n=='Not protested'||n=='Owners (self-filed)'||n=='Other agents'||n=='All agents'||n=='All other agents')return n;
  return n.replace(/\b(INC|LLC|& ASSOCIATES|& ASSOC INC|& COMPANY LLC|& COMPANY)\b/g,'').replace('RAY TAX GROUP, THE','Ray Tax Group').replace('NORTH TEXAS PROPERTY TAX SERVICES','North Texas Property Tax').replace('RESOLUTE PROPERTY TAX SOLUTIONS','Resolute Property Tax').replace('GOODRICH REALTY CONSULTING','Goodrich Realty').replace('D ALAN BOWLBY','D. Alan Bowlby').replace('TEXAS PROPERTY TAX CONSULTANTS','Texas Property Tax Consultants').trim().toLowerCase().replace(/\b\w/g,c=>c.toUpperCase()).replace('Oconnor',"O'Connor").replace("O'connor","O'Connor").replace('Llc','LLC')};
const BRAND={[OWN]:'var(--own)','RESOLUTE PROPERTY TAX SOLUTIONS':'var(--b-resolute)','Ryan LLC (all codes)':'var(--b-ryan)',"O'Connor & Associates":'var(--b-oconnor)','TEXAS TAX PROTEST':'var(--b-ttp)'};
const brandColor=f=>BRAND[f]||null;
const tip=$('#tip');
function showTip(e,html){tip.innerHTML=html;tip.style.opacity=1;const x=Math.min(e.clientX+14,innerWidth-290);tip.style.left=x+'px';tip.style.top=(e.clientY+14)+'px'}
function hideTip(){tip.style.opacity=0}
function bindTips(root){root.querySelectorAll('[data-tip]').forEach(el=>{el.addEventListener('mousemove',e=>showTip(e,el.dataset.tip));el.addEventListener('mouseleave',hideTip)})}
const esc=s=>String(s).replace(/&/g,'&amp;').replace(/"/g,'&quot;');
const S={year:LASTY,cmp:PREVY,curve:'us',win:'any'};
const WIN={any:{l:'Any reduction',col:'w',short:''},k500:{l:'$500+ reduction',col:'w500',short:'wins ≥ $500'},k1000:{l:'$1,000+ reduction',col:'w1k',short:'wins ≥ $1,000'},k2500:{l:'$2,500+ reduction',col:'w2500',short:'wins ≥ $2,500'},p025:{l:'0.25%+ of value',col:'wpct',short:'wins ≥ 0.25% of value'}};
let CW='any';
const YR=y=>D.yearsT[CW][y];
const SECS=['summary','explorer','yoy','results','matched','path','wins','more'];
const SEC=Object.fromEntries(SECS.map(k=>[k,{y:LASTY,c:PREVY,w:'any',linked:true}]));
const sv=k=>{CW=SEC[k].w;return SEC[k]};
const C=D.cols, rows=D.cube.map(r=>Object.fromEntries(C.map((c,i)=>[c,r[i]])));
const tiers=['<$300K','$300-500K','$500-750K','$750K-1M','$1-2M','$2-5M','$5M+'];
const st={sub:'Residential',hs:'all',path:'all',tier:'300+',metric:'win',sort:'n',dir:'desc'};Object.assign(st,CFG.filterDefault||{});
const METRICS=[['win','Win rate',v=>fmt.pct(v)],['redPct','Mkt reduction %',v=>fmt.pct(v,2)],['avgPct','Avg % / property',v=>fmt.pct(v,2)],['asPct','Assessed reduction %',v=>fmt.pct(v,2)],['carry','Assessed carry-through',v=>fmt.pct(v,0)],
 ['rM','Mkt value cut',fmt.usd],['perWin','$ per win',fmt.usd],['cutPerProp','$ cut per property',fmt.usd],['n','Properties',fmt.int],['avgStart','Avg starting value',fmt.usd],['hsShare','Homestead share',v=>fmt.pct(v,0)],['bigShare','Share $1M+',v=>fmt.pct(v,0)],
 ['inf','Informal share',v=>fmt.pct(v,0)],['arb','ARB share',v=>fmt.pct(v,0)],['infWin','Informal win rate',v=>fmt.pct(v)],['arbWin','ARB win rate',v=>fmt.pct(v)],['othShare','Withdrawn / no-show share',v=>fmt.pct(v,1)],
 ['capShare','Wins with $0 tax impact',v=>fmt.pct(v,0)],['taxPer','Est. tax savings / property',fmt.usd],['feePer','Est. fee-equivalent / property',fmt.usd],['dupShare','Duplicate-filing share',v=>fmt.pct(v,1)]];
{const drop=[...(CFG.path===false?['inf','arb','infWin','arbWin','othShare']:[]),...(CFG.assessed?[]:['asPct','carry','capShare']),...(CFG.tax?[]:['taxPer']),...(CFG.hs?[]:['hsShare'])];for(let i=METRICS.length-1;i>=0;i--)if(drop.includes(METRICS[i][0]))METRICS.splice(i,1);const fp=METRICS.find(m=>m[0]=='feePer');if(fp&&(D.feeRangeYears||[]).length)fp[1]='Est. fee / property (1% where unknown)'}
const MF=Object.fromEntries(METRICS.map(m=>[m[0],m]));
function deltaChip(cur,prev,kind,c=S.cmp){if(c==null)return '';if(cur==null||prev==null||!isFinite(cur)||!isFinite(prev)||(kind!='pp'&&!prev))return `<span class="delta flat">no ${c} data</span>`;
  const d=kind=='pp'?cur-prev:cur/prev-1;const txt=kind=='pp'?(d>=0?'+':'−')+Math.abs(d*100).toFixed(1)+' pp':(d>=0?'+':'−')+Math.abs(d*100).toFixed(0)+'%';
  return `<span class="delta ${Math.abs(d)<0.0005?'flat':d>0?'up':'down'}">${txt} vs ${c}</span>`}

/* ---------- season controls ---------- */
const yOpts=sel=>YEARS.map(y=>`<option value="${y}"${y==sel?' selected':''}>${y}</option>`).join('');
const cOpts=(y,sel)=>`<option value=""${sel==null?' selected':''}>No comparison</option>`+YEARS.filter(x=>x!=y).map(x=>`<option value="${x}"${x==sel?' selected':''}>${x}</option>`).join('');
const defCmp=y=>y>YEARS[0]?y-1:null;
function drawGlobal(){$('#f-year').innerHTML=yOpts(S.year);$('#f-cmp').innerHTML=cOpts(S.year,S.cmp)}
$('#f-year').onchange=e=>{S.year=+e.target.value;S.cmp=defCmp(S.year);drawGlobal();SECS.forEach(k=>{if(SEC[k].linked){SEC[k].y=S.year;SEC[k].c=S.cmp}});renderAll()};
$('#f-cmp').onchange=e=>{S.cmp=e.target.value?+e.target.value:null;SECS.forEach(k=>{if(SEC[k].linked)SEC[k].c=S.cmp});renderAll()};
const RENDER={summary:()=>renderFindings(),explorer:()=>renderExplorer(),yoy:()=>renderYoY(),results:()=>{renderResults();renderResultsExtra()},matched:()=>renderMatched(),path:()=>renderPath(),wins:()=>{renderWins();renderWinsExtra()},more:()=>renderMore()};
function drawSecCtl(k){const el=document.querySelector(`.secctl[data-sec="${k}"]`);if(!el)return;const t=SEC[k],allY=k=='yoy';
  const wSel=`<label>Count as a win <select data-r="w" aria-label="Count as a win for this section">${Object.entries(WIN).map(([kk,v])=>`<option value="${kk}"${kk==t.w?' selected':''}>${v.l}</option>`).join('')}</select></label>`;
  el.innerHTML=(allY?'':`<label>Season <select data-r="y" aria-label="Season for this section">${yOpts(t.y)}</select></label><label>Compare to <select data-r="c" aria-label="Compare season for this section">${cOpts(t.y,t.c)}</select></label>`)+wSel+`<span class="chip">${allY?YEARS[0]+'–'+YEARS[YEARS.length-1]:t.y+(t.c?` vs ${t.c}`:'')}${WIN[t.w].short?` · ${WIN[t.w].short}`:''}</span>${t.linked?'<span class="small muted">Following page settings</span>':'<span class="custom">Set for this section only</span><button type="button" class="reset">Use page settings</button>'}`;
  const ys=el.querySelector('[data-r="y"]');if(ys)ys.onchange=e=>{t.y=+e.target.value;if(t.c==t.y)t.c=null;if(t.linked&&t.c==S.cmp)t.c=defCmp(t.y);t.linked=false;drawSecCtl(k);RENDER[k]()};
  const cs=el.querySelector('[data-r="c"]');if(cs)cs.onchange=e=>{t.c=e.target.value?+e.target.value:null;t.linked=false;drawSecCtl(k);RENDER[k]()};
  el.querySelector('[data-r="w"]').onchange=e=>{t.w=e.target.value;t.linked=false;drawSecCtl(k);RENDER[k]()};
  const r=el.querySelector('.reset');if(r)r.onclick=()=>{t.y=S.year;t.c=S.cmp;t.w=S.win;t.linked=true;drawSecCtl(k);RENDER[k]()}}
drawGlobal();
$('#f-win').innerHTML=Object.entries(WIN).map(([k,v])=>`<option value="${k}"${k==S.win?' selected':''}>${v.l}</option>`).join('');
$('#f-win').onchange=e=>{S.win=e.target.value;SECS.forEach(k=>{if(SEC[k].linked)SEC[k].w=S.win});renderAll()};

/* ---------- KPIs ---------- */
function renderKPIs(){
  CW=S.win;
  const Y=YR(S.year),U=Y.us,P0=S.cmp?YR(S.cmp).us:{},resiAll=Y.matched.find(r=>r.peer=='All other agents')||Y.matched[0]||{};
  $('#kpis').innerHTML=[
   [CFG.values?(CFG.firms?'Properties (agent of record)':'Our properties'):'Properties protested',fmt.int(U.props),deltaChip(U.props,P0.props),U.rank?`#${U.rank} by volume among agents · ${fmt.pct(U.share)} share · ${fmt.int(U.ourCases)} ${CFG.values?'accounts':'cases filed'}`:CFG.firms===false&&CFG.values?`${fmt.int(U.ourCases)} accounts flagged as ours`:`${fmt.pct(U.share,2)} of agent-filed properties · ${fmt.int(U.ourCases)} protests filed`],
   [CFG.values?'Value lowered':'Win rate',fmt.pct(U.won/U.props),deltaChip(U.won/U.props,P0.won/P0.props,'pp'),`${fmt.int(U.won)} properties lowered · like-for-like ${resiAll.peer?nice(resiAll.peer).toLowerCase():'peers'} ${fmt.pct(resiAll.pw)}`],
   [CFG.capped?'Capped value cut':'Market value cut',fmt.usd(U.rM),deltaChip(U.rM,P0.rM),`${fmt.pct(U.rM/U.bM,2)} of ${fmt.usd(U.bM)} · avg ${fmt.usd(U.avgW)} per win`],
   CFG.assessed?['Assessed value cut',fmt.usd(U.rAs),deltaChip(U.rAs,P0.rAs),`${fmt.pct(U.rAs/U.rM,0)} of market cut reached the tax base`]:['Avg cut per win',fmt.usd(U.avgW),deltaChip(U.avgW,P0.avgW),`Median starting value ${fmt.usd(U.med)} · no assessed values in this file`],
   ['Est. fee revenue',feeTxt(U,S.year),FEERANGE(S.year)||FEERANGE(S.cmp)?'':deltaChip(U.fee,P0.fee),FEERANGE(S.year)?`Range: every win at 0.5% up to every win at 1%. No capped values for ${S.year}.`:`1% / 0.5% terms from the ${S.year} certified roll, before collections`]
  ].map(([l,v,d,t])=>`<div class="kpi"><span class="eyebrow">${l} · ${S.year}${S.cmp?` vs ${S.cmp}`:''}</span><span class="v">${v}</span>${d}<span class="d">${t}</span></div>`).join('');
}

/* ---------- Findings (county) ---------- */
function renderFindings(){
  const {y:SY,c:SC,w:SW}=sv('summary');
  const y=SY,Y=YR(y),U=Y.us,P=Y.paths,resiAll=Y.matched.find(r=>r.peer=='All other agents')||Y.matched[0]||{},own=Y.matched.find(r=>r.peer=='Owners (self-filed)');
  const mixT=m=>(m.Informal||0)+(m.ARB||0)+(m.Other||0);
  const mu=P[US].mix,ma=P['All agents'].mix,infShare=(mu.Informal||0)/mixT(mu),infA=(ma.Informal||0)/mixT(ma),othU=(mu.Other||0)/mixT(mu),othA=(ma.Other||0)/mixT(ma);
  const arbUs=P[US].ARB,arbAll=P['All agents'].ARB,infUs=P[US].Informal,infAll=P['All agents'].Informal;
  const t0=Y.tiers.filter(t=>t.n>=20).sort((a,b)=>(a.win-a.win_m)-(b.win-b.win_m))[0], worstCity=[...Y.cities].filter(c=>c.n>=30&&c.mwin!=null).sort((a,b)=>(a.win-a.mwin)-(b.win-b.mwin))[0];
  const F=[];
  if(resiAll.n)F.push([resiAll.up>=resiAll.pp?'good':'warn',resiAll.up>=resiAll.pp?`At or above ${nice(resiAll.peer||'All other agents').toLowerCase()} on like-for-like homes`:`Behind ${nice(resiAll.peer||'All other agents').toLowerCase()} on like-for-like homes`,`Matched by ${CFG.nbLabel}, we win <b>${fmt.pct(resiAll.uw)}</b> vs. ${fmt.pct(resiAll.pw)} and cut <b>${fmt.pct(resiAll.up,2)}</b> vs. ${fmt.pct(resiAll.pp,2)}. At other agents' neighborhood rates our book would have been cut by ${resiAll.gap>0?'about <b>'+fmt.usd(resiAll.gap)+'</b> more':'<b>'+fmt.usd(-resiAll.gap)+'</b> less'} in market value${resiAll.gap>0?` (~${fmt.usd(resiAll.gap*0.01)} in fees)`:''}.${own&&!CFG.values&&own!==resiAll?` Against owners who filed themselves we win ${fmt.pct(own.uw)} vs. ${fmt.pct(own.pw)}.`:''}`]);
  if(CFG.path!==false){F.push(['info',`${fmt.pct(infShare,0)} of our residential book settled informally`,`Informal settlements${CFG.toplineNote?' (including TopLine agreements)':''} averaged <b>${fmt.pct(infUs.pct,2)}</b> for us (${fmt.pct(infUs.win)} win) vs. ${fmt.pct(infAll.pct,2)} (${fmt.pct(infAll.win)}) for other agents. At formal ARB we got ${arbUs.n?`<b>${fmt.pct(arbUs.pct,2)}</b> (${fmt.pct(arbUs.win)} win, ${fmt.int(arbUs.n)} properties)`:'no hearings'} vs. ${fmt.pct(arbAll.pct,2)} (${fmt.pct(arbAll.win)}). Other agents settled ${fmt.pct(infA,0)} of their book informally.`]);
  F.push([othU>othA+0.03?'warn':'info',`${fmt.pct(othU,0)} of our properties ended with no result`,`${fmt.int(mu.Other||0)} of our residential properties ended dismissed, no-show or withdrawn, vs. ${fmt.pct(othA,0)} for other agents. ${U.resT&&U.resT['Dismissed / no-show']?`${fmt.int(U.resT['Dismissed / no-show'])} of them were dismissed or no-shows. Each is a client with no reduction and no fee.`:''}`]);}
  else if(!CFG.values&&mixT(mu)){F.push(['info','Our own protest path',`Our ${fmt.int(mixT(mu))} residential results: <b>${fmt.int(mu.Informal||0)}</b> informal, <b>${fmt.int(mu.ARB||0)}</b> at formal ARB and ${fmt.int(mu.Other||0)} dismissed, no-show or withdrawn. The file has no outcome type for other filers, so there's no comparison.`])}
  if(t0&&t0.win_m!=null)F.push([t0.win<t0.win_m?'bad':'info',t0.win<t0.win_m?`Weakest value tier: ${t0.tier}`:'Value tiers',`In ${t0.tier} we win <b>${fmt.pct(t0.win)}</b> (${fmt.int(t0.n)} properties) vs. ${fmt.pct(t0.win_m)} for other agents and ${fmt.pct(t0.win_o)} for ${HASOWN?'Ownwell':nice('Owners (self-filed)').replace('Owners','owners')}.${worstCity&&worstCity.win<worstCity.mwin?` Our weakest city with 30+ properties is ${worstCity.c[0]+worstCity.c.slice(1).toLowerCase()} at ${fmt.pct(worstCity.win)} vs. ${fmt.pct(worstCity.mwin)} for other agents there.`:''}`]);
  const P0=SC?YR(SC).us:null;
  if(P0&&P0.props)F.push([U.won/U.props>=P0.won/P0.props?'good':'warn',`${y} vs. ${SC}`,`Properties ${fmt.int(P0.props)} → <b>${fmt.int(U.props)}</b>, win rate ${fmt.pct(P0.won/P0.props)} → <b>${fmt.pct(U.won/U.props)}</b>, market value cut ${fmt.usd(P0.rM)} → <b>${fmt.usd(U.rM)}</b>.`]);
  F.push(['info','Fee estimate',FEERANGE(y)?`${y} has no capped values, so fees are a range: <b>${feeTxt(U,y)}</b> (every win at 0.5% up to every win at 1%).`:`About <b>${fmt.usd(U.fee)}</b> in ${y}, from the capped values in the file: ${fmt.int(U.won-U.halfFee)} wins at 1% and ${fmt.int(U.halfFee)} at 0.5% where the cap held assessed value below the reduced market value.`]);
  $('#findings').innerHTML=F.map(([t,h,b])=>`<div class="finding"><span class="tag ${t}">${{good:'Strength',info:'Context',warn:'Watch',bad:'Underperforming'}[t]}</span><h3>${h}</h3><p>${b}</p></div>`).join('');
  $('#sum-h').textContent=`What the ${CFG.county} data says about our ${y} season`;
}

/* ---------- Explorer (v1) ---------- */
function seg(id,key,opts,obj=st,cb=renderExplorerAndYoY){const el=$(id);if(!el)return;el.innerHTML=opts.map(([v,l])=>`<button type="button" data-v="${v}" aria-pressed="${obj[key]==v}">${l}</button>`).join('');el.onclick=e=>{const b=e.target.closest('button');if(!b)return;obj[key]=b.dataset.v;el.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));cb()}}
seg('#f-sub','sub',[['all','All'],['Residential','Residential'],['Non-residential','Non-residential']]);
seg('#f-hs','hs',[['all','All'],['1','Homestead'],['0','Non-homestead']]);
seg('#f-path','path',[['all','All'],['Informal','Informal'],['ARB','Formal ARB'],['Other','Other']]);
$('#f-tier').innerHTML=[['all','All values'],['300+','$300K and up'],...tiers.map(t=>[t,t])].map(([v,l])=>`<option value="${esc(v)}"${st.tier==v?' selected':''}>${l}</option>`).join('');
const COLS=[['A',CFG.firms?'Agent':'Filer'],['n','Properties'],['win','Win rate'],['dwin','Δ win'],['redPct','Mkt reduction %'],['dred','Δ reduction'],['avgPct','Avg % / property'],['asPct','Assessed reduction %'],['rM','Mkt value cut'],['perWin','$ per win'],['inf','Informal share'],['arb','ARB share']];
$('#f-metric').innerHTML=METRICS.map(([k,l])=>`<option value="${k}"${st.metric==k?' selected':''}>${l}</option>`).join('');
$('#f-tier').onchange=e=>{st.tier=e.target.value;renderExplorerAndYoY()};
$('#f-metric').onchange=e=>{st.metric=e.target.value;renderExplorer()};
function passF(r,f=st){if(f.sub!='all'&&r.sub!=f.sub)return false;if(f.hs!='all'&&String(r.HS)!=f.hs)return false;if(f.tier=='300+'?r.tier=='<$300K':(f.tier!='all'&&r.tier!=f.tier))return false;return true}
const ACC=['n','w','bM','rM','bAs','rAs','sp','all','infN','arbN','othN','infW','arbW','hsN','bigN','cap','tax','fee','dup'];
function agg(year,f=st){
  const by={},wc=WIN[CW].col;
  rows.forEach(r=>{
    if(r.Y!=year||!passF(r,f))return;
    const pathOK=f.path=='all'||r.path==f.path;
    const a=by[r.A]||(by[r.A]=Object.assign({A:r.A},Object.fromEntries(ACC.map(k=>[k,0]))));
    a.all+=r.n; if(r.path=='Informal'){a.infN+=r.n;a.infW+=r[wc]} if(r.path=='ARB'){a.arbN+=r.n;a.arbW+=r[wc]} if(r.path=='Other')a.othN+=r.n;
    if(!pathOK)return;
    a.n+=r.n;a.w+=r[wc];a.bM+=r.bM;a.rM+=r.rM;a.bAs+=r.bAs;a.rAs+=r.rAs;a.sp+=r.sp;a.cap+=r.cap;a.tax+=r.tax;a.fee+=r.fee;a.dup+=r.dup;
    if(r.HS==1)a.hsN+=r.n; if(r.tier=='$1-2M'||r.tier=='$2-5M'||r.tier=='$5M+')a.bigN+=r.n;
  });
  const fin=a=>Object.assign(a,{win:a.n?a.w/a.n:null,redPct:a.bM?a.rM/a.bM:null,avgPct:a.n?a.sp/a.n:null,asPct:a.bAs?a.rAs/a.bAs:0,perWin:a.w?a.rM/a.w:0,inf:a.all?a.infN/a.all:null,arb:a.all?a.arbN/a.all:null,
    carry:a.rM?a.rAs/a.rM:null,avgStart:a.n?a.bM/a.n:null,hsShare:a.n?a.hsN/a.n:null,bigShare:a.n?a.bigN/a.n:null,arbWin:a.arbN?a.arbW/a.arbN:null,infWin:a.infN?a.infW/a.infN:null,
    othShare:a.all?a.othN/a.all:null,capShare:a.w?a.cap/a.w:null,taxPer:a.n?a.tax/a.n:null,feePer:a.n?a.fee/a.n:null,dupShare:a.n?a.dup/a.n:null,cutPerProp:a.n?a.rM/a.n:null});
  const out=Object.values(by).filter(a=>a.n>0).map(fin);
  const sum=(list,name)=>fin(list.reduce((s,a)=>{ACC.forEach(k=>s[k]+=a[k]);return s},Object.assign({A:name},Object.fromEntries(ACC.map(k=>[k,0])))));
  const ag=sum(out.filter(a=>a.A!='Owners (self-filed)'&&a.A!=US),'All other agents');ag.agg=true;
  return {list:out,all:ag,sum};
}

if(!CFG.assessed)COLS.splice(COLS.findIndex(c=>c[0]=='asPct'),1);if(CFG.path===false)for(const k of ['inf','arb'])COLS.splice(COLS.findIndex(c=>c[0]==k),1);
const F2={n:fmt.int,win:v=>fmt.pct(v),dwin:v=>v==null?'–':(v>=0?'+':'−')+Math.abs(v*100).toFixed(1)+' pp',dred:v=>v==null?'–':(v>=0?'+':'−')+Math.abs(v*100).toFixed(2)+' pp',redPct:v=>fmt.pct(v,2),avgPct:v=>fmt.pct(v,2),asPct:v=>fmt.pct(v,2),rM:fmt.usd,perWin:fmt.usd,inf:v=>fmt.pct(v,0),arb:v=>fmt.pct(v,0)};
function renderExplorer(){
  const {y:SY,c:SC,w:SW}=sv('explorer');
  scopeNote($('#exp-scope'),SY,st);
  const {list,all}=agg(SY),prev=SC?agg(SC):{list:[],all:{n:0}};const pm=Object.fromEntries(prev.list.map(r=>[r.A,r]));
  list.forEach(r=>{const p=pm[r.A];r.prev=p&&p.n?p:null;r.dwin=r.prev?r.win-p.win:null;r.dred=r.prev?r.redPct-p.redPct:null});all.prev=prev.all.n?prev.all:null;all.dwin=all.prev?all.win-prev.all.win:null;all.dred=all.prev?all.redPct-prev.all.redPct:null;
  $('#exp-h').textContent=CFG.firms?`Compare us against the top ${D.firms.length-1} agents, ${SY}`:`Compare us against ${CFG.values?'every other account':'other agents and owners'}, ${SY}`;
  const cols=SC?COLS:COLS.filter(c=>c[0]!='dwin'&&c[0]!='dred');const k=st.sort;
  const sorted=[...list].sort((a,b)=>k=='A'?a.A.localeCompare(b.A):((b[k]??-1e9)-(a[k]??-1e9)));if(st.dir=='asc')sorted.reverse();
  const tb=$('#exp-tbl');
  tb.querySelector('thead').innerHTML='<tr>'+cols.map(([c,l])=>`<th><button type="button" data-k="${c}"${st.sort==c?` data-dir="${st.dir}"`:''}>${c=='dwin'?`Δ win vs ${SC}`:c=='dred'?`Δ reduction vs ${SC}`:l}</button></th>`).join('')+'</tr>';
  const mx={};cols.slice(1).forEach(([c])=>mx[c]=Math.max(...list.map(r=>r[c]||0),1e-9));
  const row=r=>`<tr class="${r.A==US?'us':''}${r.agg||r.A=='Other agents'||r.A=='Owners (self-filed)'?' agg':''}">`+cols.map(([c])=>c=='A'?`<td>${nice(r.A)}</td>`:(c=='dwin'||c=='dred')?`<td class="num ${r[c]==null?'':r[c]>=0?'pos':'neg'}">${F2[c](r[c])}</td>`:(c=='win'||c=='redPct')&&!r.agg?`<td class="num"><span class="cellbar">${F2[c](r[c])}<i style="width:${Math.max(2,48*r[c]/mx[c])}px"></i></span></td>`:`<td class="num">${F2[c](r[c])}</td>`).join('')+'</tr>';
  tb.querySelector('tbody').innerHTML=sorted.map(row).join('')+(all.n&&CFG.firms?row(all):'');
  tb.querySelectorAll('th button').forEach(b=>b.onclick=()=>{const c=b.dataset.k;if(st.sort==c)st.dir=st.dir=='desc'?'asc':'desc';else{st.sort=c;st.dir='desc'}renderExplorer()});
  const m=st.metric, lab=MF[m][1];const F2m=MF[m][2];
  const data=[...list].filter(r=>r.n>=20&&r[m]!=null).sort((a,b)=>b[m]-a[m]);
  hbar('#exp-chart',data.map(r=>({label:nice(r.A),c:brandColor(r.A),v:r[m],g:r.prev?r.prev[m]:null,us:r.A==US,tip:`<b>${nice(r.A)}</b><br>${lab} ${SY}: ${F2m(r[m])}${r.prev?`<br>${lab} ${SC}: ${F2m(r.prev[m])}`:''}<br>${fmt.int(r.n)} properties`})),{fmt:F2m,cmp:SC,ref:CFG.firms&&all.n&&all[m]!=null?{v:all[m],label:'All other agents '+F2m(all[m])}:null});
}
function hbar(sel,data,o){
  const W=900,rowH=22,L=240,R=70,top=8,H=top+data.length*rowH+24;
  const max=Math.max(...data.map(d=>Math.max(d.v,d.g||0)),o.ref?o.ref.v:0)*1.05||1, x=v=>L+(W-L-R)*v/max;
  let s=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Bar chart">`;
  for(let i=0;i<=4;i++){const gx=L+(W-L-R)*i/4;s+=`<line class="grid" x1="${gx}" x2="${gx}" y1="${top}" y2="${H-22}"/><text x="${gx}" y="${H-6}" text-anchor="middle">${o.fmt(max*i/4)}</text>`}
  data.forEach((d,i)=>{const y=top+i*rowH;const w=Math.max(1,x(d.v)-L);
    s+=`<g data-tip="${esc(d.tip)}"><rect x="0" y="${y}" width="${W}" height="${rowH}" fill="transparent"/><text x="${L-10}" y="${y+15}" text-anchor="end" class="${d.us?'lab-us':''}">${d.label}</text><rect x="${L}" y="${y+4}" width="${w}" height="${rowH-8}" rx="2" fill="${d.us?'var(--us)':(d.c||'var(--comp-2)')}"/>${d.g!=null?`<line x1="${x(d.g)}" x2="${x(d.g)}" y1="${y+1}" y2="${y+rowH-1}" stroke="var(--ink)" stroke-width="2"/>`:''}<text x="${Math.max(L+w,d.g!=null?x(d.g):0)+6}" y="${y+15}" class="${d.us?'lab-us':''}">${o.fmt(d.v)}</text></g>`});
  if(o.ref){const rx=x(o.ref.v);s+=`<line x1="${rx}" x2="${rx}" y1="${top-4}" y2="${H-22}" stroke="var(--ink)" stroke-dasharray="3 3"/>`}
  s+='</svg>';$(sel).innerHTML=s+`<p class="note">${o.ref?`Dashed line: ${o.ref.label}. `:''}${o.cmp?`Black tick: the same group's ${o.cmp} value. `:''}Groups with fewer than 20 properties under the current filter are hidden.</p>`;bindTips($(sel));
}

/* ---------- Year over year ---------- */
function lineChart(el,{title,cats,series,fmt:f,zero=false,h=170,w=320,zeroLine=false,cap1=false,dots=true}){
  const pad={l:46,r:14,t:title?26:10,b:24};const iw=w-pad.l-pad.r,ih=h-pad.t-pad.b;
  const vals=series.flatMap(s=>s.vals).filter(v=>v!=null&&isFinite(v));
  let lo=vals.length?Math.min(...vals):0,hi=vals.length?Math.max(...vals):1;if(zero)lo=Math.min(0,lo);if(zeroLine){lo=Math.min(0,lo);hi=Math.max(0,hi)}
  if(hi===lo)hi=lo+Math.abs(lo||1)*.1;const span=hi-lo;if(!zero)lo-=span*.08;hi+=span*.08;if(cap1&&hi>1)hi=1.02;
  const X=i=>pad.l+(cats.length===1?iw/2:i*iw/(cats.length-1)),Y=v=>pad.t+ih-(v-lo)/(hi-lo)*ih;
  let g='';for(let i=0;i<=4;i++){const v=lo+(hi-lo)*i/4,y=Y(v);g+=`<line class="grid" x1="${pad.l}" x2="${w-pad.r}" y1="${y}" y2="${y}"/><text class="v" x="${pad.l-6}" y="${y+3.5}" text-anchor="end">${f(v)}</text>`}
  if(zeroLine&&lo<0&&hi>0)g+=`<line x1="${pad.l}" x2="${w-pad.r}" y1="${Y(0)}" y2="${Y(0)}" stroke="var(--ink-3)" stroke-dasharray="3 3"/>`;
  cats.forEach((c,i)=>{if(c!=='')g+=`<text x="${X(i)}" y="${h-6}" text-anchor="middle">${c}</text>`});
  for(const s of series){const pts=s.vals.map((v,i)=>v==null||!isFinite(v)?null:[X(i),Y(v)]);let d='',pen=false;pts.forEach(p=>{if(!p){pen=false;return}d+=(pen?'L':'M')+p[0].toFixed(1)+','+p[1].toFixed(1);pen=true});
    g+=`<path d="${d}" fill="none" stroke="${s.color}" stroke-width="${s.bold?2.5:2}" stroke-linejoin="round" stroke-linecap="round"/>`;
    pts.forEach((p,i)=>{if(!p)return;const last=i===pts.length-1;if(!dots&&!last)return;g+=`<circle cx="${p[0]}" cy="${p[1]}" r="${last?4.5:3.2}" fill="${s.color}" stroke="var(--surface)" stroke-width="2"/>`})}
  const cw=cats.length>1?iw/(cats.length-1):iw;
  cats.forEach((c,i)=>{const html=`<b>${title?esc(title)+' · ':''}${c||''}</b><br>`+series.map(s=>`${esc(s.name)}: <b>${f(s.vals[i])}</b>`).join('<br>');g+=`<rect x="${Math.max(pad.l,X(i)-cw/2)}" y="${pad.t}" width="${cw}" height="${ih}" fill="transparent" data-tip="${esc(html)}"/>`});
  el.innerHTML=`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(title||'chart')}">${title?`<text x="0" y="14" style="font-weight:600;fill:var(--ink);font-size:12.5px">${esc(title)}</text>`:''}${g}</svg>`;bindTips(el)}
const yst={sub:'Residential',hs:'all',path:'all',tier:'300+',metric:'win',cmp:HASOWN?['All other agents',OWN]:['All other agents','Owners (self-filed)']};Object.assign(yst,CFG.filterDefault||{});
function scopeNote(el,y,f){
  if(!el)return;const n=a=>{const u=a.list.find(r=>r.A==US);return u?u.n:0};
  const tot=n(agg(y,{sub:'all',hs:'all',path:'all',tier:'all'})),cur=n(agg(y,f));
  const on=[f.sub!='all'?f.sub:'',f.hs=='1'?'Homesteads':f.hs=='0'?'Non-homestead':'',f.path!='all'?(f.path=='ARB'?'Formal ARB':f.path):'',f.tier=='300+'?'$300K and up':f.tier!='all'?f.tier:''].filter(Boolean);
  el.innerHTML=tot?`Showing <b>${fmt.int(cur)}</b> of our ${fmt.int(tot)} properties with a ${y} result${on.length?` · filters on: ${esc(on.join(' · '))}`:' · no filters on'}.`:''}
const CMP_COLORS={'All other agents':'var(--agents)','Owners (self-filed)':'#8c6d3f','Other agents':'#a0a7a3'};
const PAL=['#7a5cc9','#2a78d6','#c2185b','#00897b','#6d4c41','#5c6bc0','#f9a825','#8e24aa','#0277bd','#558b2f','#d84315','#37474f','#ad1457','#1565c0','#2e7d32','#795548'];
const cmpOptions=()=>CFG.firms?['All other agents',...(HASOWN?[OWN]:[]),'Owners (self-filed)','Other agents',...D.firms.filter(f=>f!=US&&f!=OWN)]:['All other agents','Owners (self-filed)'];
const cmpColor=f=>CMP_COLORS[f]||brandColor(f)||PAL[D.firms.indexOf(f)%PAL.length];
seg('#y-sub','sub',[['all','All'],['Residential','Residential'],['Non-residential','Non-residential']],yst,()=>renderYoY());
seg('#y-hs','hs',[['all','All'],['1','Homestead'],['0','Non-homestead']],yst,()=>renderYoY());
seg('#y-path','path',[['all','All'],['Informal','Informal'],['ARB','Formal ARB'],['Other','Other']],yst,()=>renderYoY());
$('#y-tier').innerHTML=[['all','All values'],['300+','$300K and up'],...tiers.map(t=>[t,t])].map(([v,l])=>`<option value="${esc(v)}"${yst.tier==v?' selected':''}>${l}</option>`).join('');
$('#y-tier').onchange=e=>{yst.tier=e.target.value;renderYoY()};
$('#y-metric').innerHTML=METRICS.map(([k,l])=>`<option value="${k}"${yst.metric==k?' selected':''}>${l}</option>`).join('');
$('#y-metric').onchange=e=>{yst.metric=e.target.value;renderYoY()};
function drawCmpPicks(){const el=$('#y-cmp');el.innerHTML=cmpOptions().map(f=>{const on=yst.cmp.includes(f),dis=!on&&yst.cmp.length>=4;return `<label class="${on?'on':''}${dis?' dis':''}"><input type="checkbox" value="${esc(f)}"${on?' checked':''}${dis?' disabled':''}><i style="background:${cmpColor(f)}"></i>${nice(f)}</label>`}).join('');
  el.querySelectorAll('input').forEach(i=>i.onchange=()=>{const f=i.value;if(i.checked){if(yst.cmp.length<4)yst.cmp.push(f)}else yst.cmp=yst.cmp.filter(x=>x!=f);renderYoY()})}
function renderYoY(){
  if(!document.getElementById('y-chart'))return;
  sv('yoy');drawCmpPicks();
  const m=yst.metric,[,lab,f]=MF[m];
  const per=YEARS.map(y=>{const g=agg(y,yst);const by=Object.fromEntries(g.list.map(r=>[r.A,r]));by['All other agents']=g.all;return by});
  const ents=[US,...yst.cmp];
  const series=ents.map(e=>({name:nice(e),color:e==US?'var(--us)':cmpColor(e),bold:e==US,vals:per.map(b=>b[e]?b[e][m]??null:null)}));
  $('#y-legend').innerHTML=ents.map(e=>`<span><i style="background:${e==US?'var(--us)':cmpColor(e)}"></i>${nice(e)}</span>`).join('');
  lineChart($('#y-chart'),{title:lab,cats:YEARS,series,fmt:f,w:900,h:320});
  scopeNote($('#y-scope'),YEARS[YEARS.length-1],yst);
  const t=$('#y-tbl');t.querySelector('thead').innerHTML=`<tr><th>${lab}</th>${YEARS.map(y=>`<th>${y}</th>`).join('')}<th>Change ${YEARS[0]}–${YEARS[YEARS.length-1]}</th></tr>`;
  const chg=(a,b)=>a==null||b==null?'–':(['win','redPct','avgPct','asPct','carry','hsShare','bigShare','inf','arb','infWin','arbWin','othShare','capShare','dupShare'].includes(m)?`${b-a>=0?'+':'−'}${Math.abs((b-a)*100).toFixed(1)} pp`:(a?`${b/a-1>=0?'+':'−'}${Math.abs((b/a-1)*100).toFixed(0)}%`:'–'));
  t.querySelector('tbody').innerHTML=ents.map((e,i)=>{const v=series[i].vals;return `<tr class="${e==US?'us':''}"><td>${nice(e)}</td>${v.map(x=>`<td class="num">${x==null?'–':f(x)}</td>`).join('')}<td class="num">${chg(v[0],v[v.length-1])}</td></tr>`}).join('');
  // scorecard
  const us=per.map(b=>b[US]||null);
  const sc=$('#y-score');sc.querySelector('thead').innerHTML=`<tr><th>Metric</th>${YEARS.map((y,i)=>`<th>${y}</th>${i?`<th>Δ</th>`:''}`).join('')}</tr>`;
  const ppK=['win','redPct','avgPct','asPct','carry','hsShare','bigShare','inf','arb','infWin','arbWin','othShare','capShare','dupShare'];
  sc.querySelector('tbody').innerHTML=METRICS.map(([k,l,ff])=>`<tr><td>${l}</td>${us.map((u,i)=>{const v=u?u[k]:null,p=i&&us[i-1]?us[i-1][k]:null;let d='';if(i){if(v==null||p==null)d='<td class="num">–</td>';else{const dd=ppK.includes(k)?v-p:(p?v/p-1:null);d=`<td class="num ${dd==null?'':dd>=0?'pos':'neg'}">${dd==null?'–':(ppK.includes(k)?`${dd>=0?'+':'−'}${Math.abs(dd*100).toFixed(1)}`:`${dd>=0?'+':'−'}${Math.abs(dd*100).toFixed(0)}%`)}</td>`}}return `<td class="num">${v==null?'–':ff(v)}</td>${d}`}).join('')}</tr>`).join('');
}
function renderExplorerAndYoY(){renderExplorer()}

/* ---------- Results (v1) ---------- */
function renderResults(){
  if(!CFG.assessed)return;
  const {y:SY,c:SC,w:SW}=sv('results');
  const Y=YR(SY),U=Y.us,P0=SC?YR(SC).us:null,dc=(a,b,k)=>SC?deltaChip(a,b,k,SC):'';
  $('#flow').innerHTML=[
   ['Starting market value',fmt.usd(U.bM),`${fmt.int(U.props)} properties`,P0&&dc(U.bM,P0.bM)],
   ['Market value cut',fmt.usd(U.rM),`${fmt.pct(U.rM/U.bM,2)} · basis for the 1% fee`,P0&&dc(U.rM,P0.rM)],
   ['Assessed value cut',fmt.usd(U.rAs),`${fmt.pct(U.rAs/U.bAs,2)} · what lowers this year's bill`,P0&&dc(U.rAs,P0.rAs)],
   ['Est. fee revenue',fmt.usd(U.fee),`${fmt.int(D.yearsT.any[SY].us.won-U.halfFee)} at 1%, ${fmt.int(U.halfFee)} at 0.5%`,P0&&dc(U.fee,P0.fee)],
   ['Est. client tax savings',fmt.usd(U.tax),SY==2026?'Combined rates by taxing unit; 2025 rate where 2026 isn\'t adopted':'Combined rates by taxing unit; exemptions not modeled',P0&&dc(U.tax,P0.tax)]
  ].map(([l,v,d,dd])=>`<div class="step"><span class="eyebrow">${l} · ${SY}</span><span class="v">${v}</span>${dd||''}<span class="small muted">${d}</span></div>`).join('');
  const keep=[US,OWN,"O'Connor & Associates",'TEXAS TAX PROTEST','NORTH TEXAS PROPERTY TAX SERVICES','GOODRICH REALTY CONSULTING','RESOLUTE PROPERTY TAX SOLUTIONS','RAY TAX GROUP, THE','Owners (self-filed)'];
  const maBy=yr=>{const by={};rows.forEach(r=>{if(r.Y!=yr||r.sub!='Residential'||r.tier=='<$300K'||!keep.includes(r.A))return;const a=by[r.A]||(by[r.A]={A:r.A,bM:0,rM:0,bAs:0,rAs:0});a.bM+=r.bM;a.rM+=r.rM;a.bAs+=r.bAs;a.rAs+=r.rAs});return Object.fromEntries(Object.values(by).filter(a=>a.bM).map(a=>[a.A,{A:a.A,m:a.rM/a.bM,s:a.rAs/a.bAs}]))};
  const cur=maBy(SY),pv=SC?maBy(SC):{};const data=Object.values(cur).map(d=>({...d,pm:pv[d.A]?pv[d.A].m:null,ps:pv[d.A]?pv[d.A].s:null})).sort((a,b)=>b.s-a.s);
  const W=560,rowH=30,L=150,R=70,top=6,H=top+data.length*rowH+24,max=Math.max(...data.map(d=>Math.max(d.m,d.s,d.pm||0,d.ps||0)))*1.1,x=v=>L+(W-L-R)*v/max;
  let s=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Market vs assessed reduction">`;
  for(let i=0;i<=4;i++){const gx=L+(W-L-R)*i/4;s+=`<line class="grid" x1="${gx}" x2="${gx}" y1="${top}" y2="${H-22}"/><text x="${gx}" y="${H-6}" text-anchor="middle">${fmt.pct(max*i/4,1)}</text>`}
  data.forEach((d,i)=>{const y=top+i*rowH,u=d.A==US;s+=`<g data-tip="${esc(`<b>${nice(d.A)}</b><br>Market reduction ${fmt.pct(d.m,2)}<br>Assessed reduction ${fmt.pct(d.s,2)}<br>${fmt.pct(d.s/d.m,0)} carried through${d.pm!=null?`<br>${SC}: market ${fmt.pct(d.pm,2)}, assessed ${fmt.pct(d.ps,2)}`:''}`)}"><rect x="0" y="${y}" width="${W}" height="${rowH}" fill="transparent"/><text x="${L-10}" y="${y+19}" text-anchor="end" class="${u?'lab-us':''}">${nice(d.A)}</text><rect x="${L}" y="${y+4}" width="${x(d.m)-L}" height="10" rx="2" fill="var(--comp-2)"/><rect x="${L}" y="${y+16}" width="${x(d.s)-L}" height="10" rx="2" fill="${u?'var(--us)':'var(--comp)'}"/>${d.pm!=null?`<line x1="${x(d.pm)}" x2="${x(d.pm)}" y1="${y+3}" y2="${y+15}" stroke="var(--ink)" stroke-width="2"/><line x1="${x(d.ps)}" x2="${x(d.ps)}" y1="${y+15}" y2="${y+27}" stroke="var(--ink)" stroke-width="2"/>`:''}<text x="${x(Math.max(d.m,d.s,d.pm||0,d.ps||0))+6}" y="${y+19}" class="${u?'lab-us':''}">${fmt.pct(d.s,2)}</text></g>`});
  $('#ma-chart').innerHTML=s+'</svg>'+(SC?`<p class="note">Black ticks: each firm's ${SC} market and assessed reduction.</p>`:'');bindTips($('#ma-chart'));
  const loss=data.filter(d=>d.A!=US&&d.m).map(d=>1-d.s/d.m);
  $('#cap-block').innerHTML=`<div class="flow" style="grid-template-columns:repeat(auto-fit,minmax(150px,1fr))">
   <div class="step"><span class="eyebrow">Full carry-through</span><span class="v">${fmt.int(U.won-U.capleak-U.capPartial)}</span>${P0?dc(U.won-U.capleak-U.capPartial,P0.won-P0.capleak-P0.capPartial):''}<span class="small muted">Wins where the assessed cut matched the market cut</span></div>
   <div class="step"><span class="eyebrow">Partial</span><span class="v">${fmt.int(U.capPartial)}</span>${P0?dc(U.capPartial,P0.capPartial):''}<span class="small muted">Assessed value fell by less than market</span></div>
   <div class="step"><span class="eyebrow">Zero tax impact</span><span class="v" style="color:var(--bad)">${fmt.int(U.capleak)}</span>${P0?dc(U.capleak,P0.capleak):''}<span class="small muted">Market cut, assessed value unchanged (capped)</span></div></div>
   <ul class="plain"><li>${fmt.int(U.halfFee)} wins fall under the <b>0.5% fee tier</b> because the cap held assessed value below the reduced market value.</li><li>Capped homes are the easiest to "win" but deliver little to the client this year. Consider sorting them out before filing, or setting expectations up front that the benefit shows up in future years.</li><li>The competitors shown lose ${fmt.pct(Math.min(...loss),0)}–${fmt.pct(Math.max(...loss),0)} to the caps. Ours is ${fmt.pct(1-U.rAs/U.rM,0)}.</li></ul>`;
}

/* ---------- Like-for-like (v1) ---------- */
const NBI=Object.fromEntries(D.nbCols.map((c,i)=>[c,i]));
let nbSel=null;const nbt={min:5,q:'',view:'All other agents',sort:'n',dir:'desc'};
function nbData(y){ // {nb:{P:{n,w,sm,mc,inf}}}
  const wc={any:'w',k500:'w500',k1000:'w1k',k2500:'w2500',p025:'wpct'}[CW];const out={};
  for(const r of D.nb[y]){const nb=r[NBI.nb],P=r[NBI.P];(out[nb]||(out[nb]={}))[P]={n:r[NBI.n],w:r[NBI[wc]],sm:r[NBI.sm],mc:r[NBI.mc],inf:r[NBI.inf]}}
  return out}
const peerKeys=nb=>Object.keys(nb);
function peerAgg(nbObj,peer){ // combine groups for a peer label
  const keys=peer=='All other agents'?Object.keys(nbObj).filter(k=>k!=US&&k!='Owners (self-filed)'):[peer];
  const a={n:0,w:0,sm:0,mc:0,inf:0};keys.forEach(k=>{const v=nbObj[k];if(v){a.n+=v.n;a.w+=v.w;a.sm+=v.sm;a.mc+=v.mc;a.inf+=v.inf}});return a}
function matchedCalc(y,nbFilter){
  const data=nbData(y);const peers=['All other agents','Owners (self-filed)',...D.peersN.filter(p=>p!=US)];
  return peers.map(peer=>{let n=0,uw=0,usm=0,umc=0,pw=0,pinf=0,exp=0;
    for(const [nb,o] of Object.entries(data)){if(nbFilter&&nb!=nbFilter)continue;const u=o[US];if(!u||!u.n)continue;const p=peerAgg(o,peer);if(p.n<3)continue;
      n+=u.n;uw+=u.w;usm+=u.sm;umc+=u.mc;pw+=u.n*(p.w/p.n);pinf+=u.n*(p.inf/p.n);exp+=u.sm*(p.mc/p.sm)}
    return n?{peer,n,uw:uw/n,pw:pw/n,up:umc/usm,pp:exp/usm,inf:pinf/n,gap:exp-umc}:null}).filter(Boolean)}
function renderMatched(){
  const {y:SY,c:SC,w:SW}=sv('matched');
  const cur=matchedCalc(SY,nbSel),PM=SC?Object.fromEntries(matchedCalc(SC,nbSel).map(r=>[r.peer,r])):{};
  $('#nb-note').innerHTML=nbSel?`Showing <b>${esc(nbSel)} · ${esc(D.nbNames[nbSel]||'')}</b>${D.nbCity[nbSel]?` (${esc(D.nbCity[nbSel])})`:''}. Peers need at least 3 properties in this neighborhood.`:'All neighborhoods where we had a residential property ($200K–$2M).';
  $('#m-tbl thead').innerHTML=`<tr><th>Compared against</th><th>Matched props</th><th>Our win rate</th><th>Their win rate</th><th>Our avg reduction</th><th>Their avg reduction</th><th>Our edge (pp)</th>${SC?`<th>Edge Δ vs ${SC}</th>`:''}<th>Their informal share</th><th>$ gap on our book</th></tr>`;
  $('#m-tbl tbody').innerHTML=cur.length?cur.map(r=>{const g=r.pp-r.up,p=PM[r.peer],de=p?(r.up-r.pp)-(p.up-p.pp):null;return `<tr${r.peer==OWN?' style="font-weight:600"':''}><td>${nice(r.peer)}</td><td class="num">${fmt.int(r.n)}</td><td class="num">${fmt.pct(r.uw)}</td><td class="num">${fmt.pct(r.pw)}</td><td class="num">${fmt.pct(r.up,2)}</td><td class="num">${fmt.pct(r.pp,2)}</td><td class="num ${g>0?'neg':'pos'}">${fmt.pp(-g)}</td>${SC?`<td class="num ${de==null?'':de>=0?'pos':'neg'}">${de==null?'–':fmt.pp(de)}</td>`:''}<td class="num">${fmt.pct(r.inf,0)}</td><td class="num ${r.gap>0?'neg':'pos'}">${fmt.usd(r.gap)}</td></tr>`}).join(''):`<tr><td colspan="10">No peer had 3+ properties in this neighborhood.</td></tr>`;
  renderNbTable(SY);
}
function renderNbTable(y){
  const data=nbData(y),peer=nbt.view,q=nbt.q.trim().toLowerCase();
  const rowsN=[];for(const [nb,o] of Object.entries(data)){const u=o[US];if(!u||u.n<nbt.min)continue;const p=peerAgg(o,peer);const name=D.nbNames[nb]||'',city=D.nbCity[nb]||'';
    if(q&&!(nb.toLowerCase().includes(q)||name.toLowerCase().includes(q)||city.toLowerCase().includes(q)))continue;
    const r={nb,name,city,n:u.n,uw:u.w/u.n,up:u.sm?u.mc/u.sm:null,umc:u.mc,pn:p.n,pw:p.n?p.w/p.n:null,pp:p.sm?p.mc/p.sm:null};r.edge=r.pp!=null&&p.n>=3?r.up-r.pp:null;r.gap=r.pp!=null&&p.n>=3?u.sm*r.pp-u.mc:null;r.dw=r.pw!=null&&p.n>=3?r.uw-r.pw:null;rowsN.push(r)}
  const k=nbt.sort;rowsN.sort((a,b)=>(k=='nb'||k=='name'||k=='city')?String(a[k]).localeCompare(String(b[k])):((b[k]??-1e18)-(a[k]??-1e18)));if(nbt.dir=='asc')rowsN.reverse();
  const cols=[['nb','Code'],['name','Neighborhood'],['city','City'],['n','Our props'],['uw','Our win'],['pw','Their win'],['dw','Win Δ (pp)'],['up','Our reduction'],['pp','Their reduction'],['edge','Our edge (pp)'],['pn','Their props'],['umc','Our $ cut'],['gap','$ gap']];
  const th=$('#nbt-tbl thead');th.innerHTML='<tr>'+cols.map(([c,l])=>`<th><button type="button" data-k="${c}"${nbt.sort==c?` data-dir="${nbt.dir}"`:''}>${l}</button></th>`).join('')+'</tr>';
  const pp2=v=>v==null?'–':fmt.pp(v);const pw1=v=>v==null?'–':(v>=0?'+':'−')+Math.abs(v*100).toFixed(1);
  $('#nbt-tbl tbody').innerHTML=rowsN.map(r=>`<tr class="click${nbSel==r.nb?' sel':''}" data-nb="${esc(r.nb)}"><td class="mono l">${esc(r.nb)}</td><td class="l" style="white-space:normal;min-width:180px">${esc(r.name)}</td><td class="l">${esc(r.city)}</td><td class="num">${fmt.int(r.n)}</td><td class="num">${fmt.pct(r.uw)}</td><td class="num">${r.pn>=3?fmt.pct(r.pw):'–'}</td><td class="num ${r.dw==null?'':r.dw>=0?'pos':'neg'}">${pw1(r.dw)}</td><td class="num">${fmt.pct(r.up,2)}</td><td class="num">${r.pn>=3?fmt.pct(r.pp,2):'–'}</td><td class="num ${r.edge==null?'':r.edge>=0?'pos':'neg'}">${pp2(r.edge)}</td><td class="num">${fmt.int(r.pn)}</td><td class="num">${fmt.usd(r.umc)}</td><td class="num ${r.gap==null?'':r.gap>0?'neg':'pos'}">${r.gap==null?'–':fmt.usd(r.gap)}</td></tr>`).join('');
  th.querySelectorAll('button').forEach(b=>b.onclick=()=>{const c=b.dataset.k;if(nbt.sort==c)nbt.dir=nbt.dir=='desc'?'asc':'desc';else{nbt.sort=c;nbt.dir='desc'}renderNbTable(y)});
  $('#nbt-tbl tbody').querySelectorAll('tr.click').forEach(tr=>tr.onclick=()=>{nbSel=tr.dataset.nb;$('#nb-find').value=nbSel+' · '+(D.nbNames[nbSel]||'');renderMatched();$('#matched').scrollIntoView({behavior:'smooth',block:'start'})});
  const wins=rowsN.filter(r=>r.edge!=null);const beat=wins.filter(r=>r.edge>0).length;
  $('#nbt-note').innerHTML=`${fmt.int(rowsN.length)} neighborhoods shown. We out-cut ${nice(peer)} in <b>${fmt.int(beat)}</b> of the ${fmt.int(wins.length)} where they had 3+ properties.`;
}
(function(){
  const all=new Set();Object.values(D.nb).forEach(rs=>rs.forEach(r=>{if(r[NBI.P]==US)all.add(r[NBI.nb])}));
  $('#nb-list').innerHTML=[...all].sort().map(nb=>`<option value="${esc(nb)} · ${esc(D.nbNames[nb]||'')}${D.nbCity[nb]?' ('+esc(D.nbCity[nb])+')':''}"></option>`).join('');
  $('#nb-find').onchange=e=>{const v=e.target.value.split(' · ')[0].trim();nbSel=v&&all.has(v)?v:null;if(!nbSel)e.target.value='';renderMatched()};
  $('#nb-clear').onclick=()=>{nbSel=null;$('#nb-find').value='';renderMatched()};
  $('#nbt-min').onchange=e=>{nbt.min=+e.target.value;renderMatched()};
  $('#nbt-q').oninput=e=>{nbt.q=e.target.value;sv('matched');renderNbTable(SEC.matched.y)};
  {const opts=[['All other agents','All other agents (combined)'],['Owners (self-filed)','Owners (self-filed)'],...(D.nbPeers||D.peersN).filter(p=>p!=US).map(p=>[p,nice(p)])];
   const el=$('#nbt-view');el.innerHTML='<optgroup label="Groups">'+opts.slice(0,2).map(([v,l])=>`<option value="${esc(v)}"${v==nbt.view?' selected':''}>${esc(l)}</option>`).join('')+'</optgroup>'+(opts.length>2?'<optgroup label="Individual agents">'+opts.slice(2).map(([v,l])=>`<option value="${esc(v)}"${v==nbt.view?' selected':''}>${esc(l)}</option>`).join('')+'</optgroup>':'');
   el.onchange=e=>{nbt.view=e.target.value;renderMatched()}}
})();

/* ---------- Path (v1) ---------- */
function renderPath(){
  if(!document.getElementById('mix-chart'))return;
  const {y:SY,c:SC,w:SW}=sv('path');
  const Y=YR(SY),P=Y.paths,cf=Y.cf,nc=Y.nochange;
  const firms=(CFG.firms?[US,...D.firms.filter(f=>f!=US).slice(0,7)]:[US,'Owners (self-filed)']).filter(f=>P[f]);
  const mixOf=f=>{const m=P[f].mix;return {Informal:m.Informal||0,ARB:m.ARB||0,Other:m.Other||0,t:(m.Informal||0)+(m.ARB||0)+(m.Other||0)}};
  const PP=SC?YR(SC).paths:null;const mixP=f=>{if(!PP||!PP[f])return null;const m=PP[f].mix;const t=(m.Informal||0)+(m.ARB||0)+(m.Other||0);return t?{i:(m.Informal||0)/t,a:(m.ARB||0)/t}:null};
  const us=mixOf(US),al=mixOf('All agents');
  $('#path-lede').textContent=`In ${SY} we sent ${fmt.pct(us.ARB/us.t,0)} of our residential properties to formal ARB hearings. All other agents sent ${fmt.pct(al.ARB/al.t,0)}. ${CFG.pathNote} Mix covers all residential properties. The average-reduction chart covers residential $200K–$2M.`;
  $('#path-h').textContent=`${SY}: ${fmt.pct(us.Informal/us.t,0)} of our book settled informally, ${fmt.pct(us.ARB/us.t,0)} at formal ARB`;
  const W=560,rowH=26,L=150,R=10,top=4,H=top+firms.length*rowH+22,x=v=>(W-L-R)*v;
  let s=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Resolution mix">`;
  firms.forEach((f,i)=>{const a=mixOf(f),y=top+i*rowH,u=f==US;let cx=L;s+=`<text x="${L-10}" y="${y+16}" text-anchor="end" class="${u?'lab-us':''}">${nice(f)}</text>`;if(!a.t)return;
    [['Informal','var(--inf)'],['ARB','var(--arb)'],['Other','var(--oth)']].forEach(([k,c])=>{const w=x(a[k]/a.t);if(w<=0)return;s+=`<rect data-tip="${esc(`<b>${nice(f)}</b><br>${k=='ARB'?'Formal ARB':k=='Informal'?'Informal / TopLine':'Withdrawn / no-show / closed'}: ${fmt.pct(a[k]/a.t)} (${fmt.int(a[k])})`)}" x="${cx}" y="${y+3}" width="${Math.max(0,w-2)}" height="${rowH-8}" fill="${c}"/>`;if(w>34)s+=`<text x="${cx+w/2-1}" y="${y+16}" text-anchor="middle" style="fill:#fff;font-weight:600" pointer-events="none">${fmt.pct(a[k]/a.t,0)}</text>`;cx+=w})});
  firms.forEach((f,i)=>{const p=mixP(f);if(!p)return;const y=top+i*rowH;[p.i,p.i+p.a].forEach(v=>{s+=`<line x1="${L+x(v)}" x2="${L+x(v)}" y1="${y}" y2="${y+rowH-2}" stroke="var(--ink)" stroke-width="2" pointer-events="none"/>`})});
  [0,.5,1].forEach(v=>s+=`<text x="${L+x(v)}" y="${H-5}" text-anchor="middle">${v*100}%</text>`);
  $('#mix-chart').innerHTML=s+'</svg>'+(SC?`<p class="note">Black ticks: where each firm's informal and ARB shares ended in ${SC}.</p>`:'');bindTips($('#mix-chart'));
  const ks=['All agents',...firms];const PL=k=>k=='All agents'&&!CFG.firms?'All other agents':nice(k);
  const pv=ks.flatMap(k=>[P[k].Informal.n>=40?P[k].Informal.pct:0,P[k].ARB.n?P[k].ARB.pct:0,PP&&PP[k]?PP[k].ARB.pct||0:0,PP&&PP[k]?PP[k].Informal.pct||0:0]);const W2=560,rh=26,L2=150,R2=60,H2=6+ks.length*rh+22,mx=Math.max(.04,Math.ceil(Math.max(...pv)*1.1*100)/100),x2=v=>L2+(W2-L2-R2)*Math.min(v||0,mx)/mx;
  let t=`<svg viewBox="0 0 ${W2} ${H2}" role="img" aria-label="Average reduction by path">`;
  for(let i=0;i<=4;i++){const gx=L2+(W2-L2-R2)*i/4;t+=`<line class="grid" x1="${gx}" x2="${gx}" y1="6" y2="${H2-22}"/><text x="${gx}" y="${H2-6}" text-anchor="middle">${fmt.pct(mx*i/4,0)}</text>`}
  const hidden=[];
  ks.forEach((k,i)=>{const p=P[k],y=6+i*rh+rh/2,u=k==US;const a=p.Informal,b=p.ARB;if(a.n<40&&a.n>0)hidden.push(`${PL(k)}: ${a.n}`);
    t+=`<g data-tip="${esc(`<b>${PL(k)}</b><br>Informal: ${fmt.pct(a.pct,2)} avg, ${fmt.pct(a.win)} win (${fmt.int(a.n)})<br>Formal ARB: ${fmt.pct(b.pct,2)} avg, ${fmt.pct(b.win)} win (${fmt.int(b.n)})`)}"><rect x="0" y="${y-rh/2}" width="${W2}" height="${rh}" fill="transparent"/><text x="${L2-10}" y="${y+4}" text-anchor="end" class="${u?'lab-us':''}" style="${k=='All agents'?'font-style:italic':''}">${PL(k)}</text>
    ${a.n>=40&&b.n?`<line x1="${x2(a.pct)}" x2="${x2(b.pct)}" y1="${y}" y2="${y}" stroke="var(--line)" stroke-width="2"/>`:''}
    ${a.n>=40?`<circle cx="${x2(a.pct)}" cy="${y}" r="6" fill="var(--inf)" stroke="var(--surface)" stroke-width="2"/>`:''}
    ${b.n?`<circle cx="${x2(b.pct)}" cy="${y}" r="${u?8:6}" fill="var(--arb)" stroke="${u?'var(--us)':'var(--surface)'}" stroke-width="2"/>`:''}${PP&&PP[k]&&PP[k].ARB.n?`<circle cx="${x2(PP[k].ARB.pct)}" cy="${y}" r="5" fill="none" stroke="var(--arb)" stroke-width="1.5" stroke-dasharray="2 2"/>`:''}${PP&&PP[k]&&PP[k].Informal.n>=40?`<circle cx="${x2(PP[k].Informal.pct)}" cy="${y}" r="5" fill="none" stroke="var(--inf)" stroke-width="1.5" stroke-dasharray="2 2"/>`:''}</g>`});
  $('#db-chart').innerHTML=t+`</svg><p class="note">${SC?`Dashed rings: the same firm's ${SC} averages. `:''}Informal dots are hidden for firms with fewer than 40 informal properties${hidden.length?` (${hidden.join('; ')})`:''}.</p>`;bindTips($('#db-chart'));
  if(!CFG.cfCallout){const e=$('#cf-callout');e.innerHTML='';e.style.display='none';return}
  $('#cf-callout').innerHTML=cf.n?`<b>Did the path choice help or hurt in ${SY}?</b> Across all agents, informal cases average ${fmt.pct(P['All agents'].Informal.pct,2)} and ARB cases average ${fmt.pct(P['All agents'].ARB.pct,2)}. That comparison is biased, though: informals settle when the CAD's offer is good, and the hard cases go to ARB. The fairer test uses our ${fmt.int(cf.n)} ARB properties that have informal and ARB comparables in the same neighborhood. There, other agents' <b>informal</b> results averaged ${fmt.pct(cf.inf,2)} (${fmt.pct(cf.infw)} win) and their <b>ARB</b> results averaged ${fmt.pct(cf.arb,2)} (${fmt.pct(cf.arbw)} win). Ours were <b>${fmt.pct(cf.our,2)}</b> (${fmt.pct(cf.ourw)} win). Against informal settlements, our ARB results ${cf.gapInf>0?`land about <b>${fmt.usd(cf.gapInf)}</b> in market value (~${fmt.usd(cf.gapInf*0.01)} in fees) short`:`come out <b>${fmt.usd(-cf.gapInf)}</b> ahead`}. Our ${fmt.int(nc.n)} <b>No Change</b> results carry ${fmt.usd(nc.base)} of value. In those neighborhoods, ${fmt.pct(nc.infw)} of informal settlements got a reduction, averaging ${fmt.pct(nc.infp,2)}. Even a middling offer on those properties would have been worth about ${fmt.usd(nc.est*0.5)}–${fmt.usd(nc.est)}.`:'Not enough matched ARB properties this season for the path comparison.';
}

/* ---------- Wins, gaps & misses (v1) ---------- */
function renderWins(){
  const {y:SY,c:SC,w:SW}=sv('wins');
  const Y=YR(SY),U=Y.us,nc=Y.nochange;
  const YC=SC?YR(SC):null,TC=YC?Object.fromEntries(YC.tiers.map(t=>[t.tier,t])):{};
  const O3=HASOWN?'Ownwell':'Owners (self-filed)';
  const T=Y.tiers.filter(t=>t.n>=10);const W=560,gh=46,L=80,R=60,H=8+T.length*gh+22,x=v=>L+(W-L-R)*(v||0);
  let s=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Win rate by tier">`;
  for(let i=0;i<=4;i++){const gx=L+(W-L-R)*i/4;s+=`<line class="grid" x1="${gx}" x2="${gx}" y1="8" y2="${H-22}"/><text x="${gx}" y="${H-6}" text-anchor="middle">${i*25}%</text>`}
  T.forEach((t,i)=>{const y=8+i*gh;s+=`<g data-tip="${esc(`<b>${t.tier}</b><br>Property Tax Protest: ${fmt.pct(t.win)} win, ${fmt.pct(t.pct,2)} avg (${t.n} props)<br>All other agents: ${fmt.pct(t.win_m)} win<br>${O3}: ${fmt.pct(t.win_o)} win, ${fmt.pct(t.pct_o,2)} avg${TC[t.tier]?`<br>${SC}: us ${fmt.pct(TC[t.tier].win)}, agents ${fmt.pct(TC[t.tier].win_m)}, ${O3.toLowerCase()} ${fmt.pct(TC[t.tier].win_o)}`:''}`)}"><rect x="0" y="${y}" width="${W}" height="${gh}" fill="transparent"/><text x="${L-10}" y="${y+26}" text-anchor="end">${t.tier}</text>
   <rect x="${L}" y="${y+4}" width="${x(t.win)-L}" height="11" rx="2" fill="var(--us)"/><text x="${x(t.win)+6}" y="${y+14}" class="lab-us">${fmt.pct(t.win,0)}</text>
   <rect x="${L}" y="${y+17}" width="${x(t.win_m)-L}" height="11" rx="2" fill="var(--agents)"/>
   <rect x="${L}" y="${y+30}" width="${x(t.win_o)-L}" height="11" rx="2" fill="var(--own)"/>${(()=>{const p=TC[t.tier];if(!p)return '';return [[p.n?p.win:null,y+2],[p.win_m,y+15],[p.win_o,y+28]].map(([v,yy])=>v==null?'':`<line x1="${x(v)}" x2="${x(v)}" y1="${yy}" y2="${yy+15}" stroke="var(--ink)" stroke-width="2"/>`).join('')})()}</g>`});
  $('#tier-chart').innerHTML=s+'</svg>'+(SC?`<p class="note">Black ticks: ${SC} win rates.</p>`:'');bindTips($('#tier-chart'));
  const CC=YC?Object.fromEntries(YC.cities.map(c=>[c.c,c])):{};
  if($('#city-tbl')){$('#city-tbl thead').innerHTML=`<tr><th>City</th><th>Props</th><th>Win rate</th>${SC?`<th>Δ win vs ${SC}</th>`:''}<th>Market win</th><th>Avg reduction</th><th>Market avg</th><th>$ cut</th></tr>`;
  $('#city-tbl tbody').innerHTML=Y.cities.map(c=>`<tr><td>${c.c[0]+c.c.slice(1).toLowerCase()}</td><td class="num">${fmt.int(c.n)}</td><td class="num ${c.mwin!=null&&c.win<c.mwin-0.05?'neg':''}">${fmt.pct(c.win)}</td>${SC?(()=>{const p=CC[c.c];const d=p?c.win-p.win:null;return `<td class="num ${d==null?'':d>=0?'pos':'neg'}">${d==null?'–':(d>=0?'+':'−')+Math.abs(d*100).toFixed(1)+' pp'}</td>`})():''}<td class="num">${fmt.pct(c.mwin)}</td><td class="num">${fmt.pct(c.pct,2)}</td><td class="num">${fmt.pct(c.mpct,2)}</td><td class="num">${fmt.usd(c.red)}</td></tr>`).join('');
}
  if($('#mo-tbl')){const MC=YC?Object.fromEntries(YC.month.map(m=>[m.m,m])):{};
  $('#mo-tbl thead').innerHTML=`<tr><th>Month</th><th>Our hearings</th><th>Our win</th>${SC?`<th>Our win ${SC}</th>`:''}<th>Market win</th><th>Our avg</th><th>Market avg</th></tr>`;
  $('#mo-tbl tbody').innerHTML=Y.month.map(m=>`<tr><td>${m.m}</td><td class="num">${fmt.int(m.n)}</td><td class="num">${fmt.pct(m.win)}</td>${SC?`<td class="num">${MC[m.m]&&MC[m.m].n?fmt.pct(MC[m.m].win):'–'}</td>`:''}<td class="num">${fmt.pct(m.mwin)}</td><td class="num">${fmt.pct(m.pct,2)}</td><td class="num">${fmt.pct(m.mpct,2)}</td></tr>`).join('');
  }
  if(CFG.appraiser){
  // appraiser chart (v1)
  $('#appr-sub').textContent=`Formal ARB hearings, residential, appraisers with ${Y.apprMin}+ of our cases in ${SY}. Each dot is the market's win rate with that appraiser, and each bar is ours.`;
  const AC=YC?Object.fromEntries(YC.appr.map(a=>[a.name,a])):{};
  const A=[...Y.appr].sort((a,b)=>(a.win-a.mwin)-(b.win-b.mwin));
  if(!A.length){$('#appr-chart').innerHTML='<p class="note">No appraiser had enough of our ARB cases this season.</p>'}else{
  const Wa=560,rh=22,La=130,Ra=70,Ha=6+A.length*rh+22,lo=.2,xa=v=>La+(Wa-La-Ra)*(Math.max(v,lo)-lo)/(1-lo);
  let a=`<svg viewBox="0 0 ${Wa} ${Ha}" role="img" aria-label="Win rate by appraiser">`;
  [.2,.4,.6,.8,1].forEach(v=>{a+=`<line class="grid" x1="${xa(v)}" x2="${xa(v)}" y1="6" y2="${Ha-22}"/><text x="${xa(v)}" y="${Ha-6}" text-anchor="middle">${Math.round(v*100)}%</text>`});
  A.forEach((p,i)=>{const y=6+i*rh,d=p.win-p.mwin;a+=`<g data-tip="${esc(`<b>${p.name}</b><br>Property Tax Protest: ${fmt.pct(p.win)} win, ${fmt.pct(p.pct,2)} avg (${p.n})<br>Market: ${fmt.pct(p.mwin)} win, ${fmt.pct(p.mpct,2)} avg (${fmt.int(p.mn)})${AC[p.name]?`<br>Our ${SC}: ${fmt.pct(AC[p.name].win)} win (${AC[p.name].n})`:''}`)}"><rect x="0" y="${y}" width="${Wa}" height="${rh}" fill="transparent"/><text x="${La-10}" y="${y+15}" text-anchor="end">${p.name}</text><rect x="${xa(lo)}" y="${y+5}" width="${Math.max(0,xa(p.win)-xa(lo))}" height="${rh-10}" rx="2" fill="var(--us)" opacity=".85"/>${AC[p.name]?`<line x1="${xa(AC[p.name].win)}" x2="${xa(AC[p.name].win)}" y1="${y+2}" y2="${y+rh-2}" stroke="var(--us-ink)" stroke-width="2"/>`:''}<circle cx="${xa(p.mwin)}" cy="${y+rh/2}" r="5" fill="var(--ink)" stroke="var(--surface)" stroke-width="2"/><text x="${Math.max(xa(p.win),xa(p.mwin))+10}" y="${y+15}" class="${d<0?'':'lab-us'}" style="${d<0?'fill:var(--bad)':''}">${(d>0?'+':'')+(d*100).toFixed(0)} pts</text></g>`});
  $('#appr-chart').innerHTML=a+'</svg>'+(SC?`<p class="note">Dark green tick: our ${SC} win rate with that appraiser, where they had ${YC.apprMin}+ of our cases that season.</p>`:'');bindTips($('#appr-chart'))}
  // ARB panel members (v8)
  {const P=Y.pm||[],PC=YC&&YC.pm?Object.fromEntries(YC.pm.map(a=>[a.name,a])):{};
  $('#pm-sub').textContent=`Formal ARB hearings, residential, ${SY}. Panel members who sat on ${Y.pmMin}+ of our hearings. A hearing counts once for each member on the panel. Each dot is the market's win rate with that member, and each bar is ours.`;
  if(!P.length){$('#pm-chart').innerHTML='<p class="note">No panel member heard enough of our ARB cases this season.</p>'}else{
  const A=[...P].filter(p=>p.mwin!=null).sort((a,b)=>(a.win-a.mwin)-(b.win-b.mwin));
  const Wa=560,rh=22,La=150,Ra=70,Ha=6+A.length*rh+22,lo=.2,xa=v=>La+(Wa-La-Ra)*(Math.max(v,lo)-lo)/(1-lo);
  let a=`<svg viewBox="0 0 ${Wa} ${Ha}" role="img" aria-label="Win rate by ARB panel member">`;
  [.2,.4,.6,.8,1].forEach(v=>{a+=`<line class="grid" x1="${xa(v)}" x2="${xa(v)}" y1="6" y2="${Ha-22}"/><text x="${xa(v)}" y="${Ha-6}" text-anchor="middle">${Math.round(v*100)}%</text>`});
  A.forEach((p,i)=>{const y=6+i*rh,d=p.win-p.mwin,c=PC[p.name];a+=`<g data-tip="${esc(`<b>${p.name}</b><br>Property Tax Protest: ${fmt.pct(p.win)} win, ${fmt.pct(p.pct,2)} avg (${p.n} hearings)<br>Market: ${fmt.pct(p.mwin)} win, ${fmt.pct(p.mpct,2)} avg (${fmt.int(p.mn)})${c?`<br>Our ${SC}: ${fmt.pct(c.win)} win (${c.n})`:''}`)}"><rect x="0" y="${y}" width="${Wa}" height="${rh}" fill="transparent"/><text x="${La-10}" y="${y+15}" text-anchor="end">${p.name}</text><rect x="${xa(lo)}" y="${y+5}" width="${Math.max(0,xa(p.win)-xa(lo))}" height="${rh-10}" rx="2" fill="var(--us)" opacity=".85"/>${c?`<line x1="${xa(c.win)}" x2="${xa(c.win)}" y1="${y+2}" y2="${y+rh-2}" stroke="var(--us-ink)" stroke-width="2"/>`:''}<circle cx="${xa(p.mwin)}" cy="${y+rh/2}" r="5" fill="var(--ink)" stroke="var(--surface)" stroke-width="2"/><text x="${Math.max(xa(p.win),xa(p.mwin))+10}" y="${y+15}" class="${d<0?'':'lab-us'}" style="${d<0?'fill:var(--bad)':''}">${(d>0?'+':'')+(d*100).toFixed(0)} pts</text></g>`});
  $('#pm-chart').innerHTML=a+'</svg>'+(SC?`<p class="note">Dark green tick: our ${SC} win rate with that member, where they sat on ${YC.pmMin}+ of our hearings that season.</p>`:'');bindTips($('#pm-chart'))}
  const L=Y.pnl||[],cov=Y.pnlCov||[0,0],LC=YC&&YC.pnl?Object.fromEntries(YC.pnl.map(a=>[a.name,a])):{};
  $('#pnl-sub').textContent=`Exact panel line-ups, formal ARB, residential, ${SY}. ${fmt.int(cov[0])} of our ${fmt.int(cov[1])} ARB hearings list their panel.`;
  $('#pnl-tbl thead').innerHTML=`<tr><th>Panel</th><th>Our hearings</th><th>Our win</th>${SC?`<th>Our win ${SC}</th>`:''}<th>Our avg</th><th>Market hearings</th><th>Market win</th><th>Market avg</th></tr>`;
  $('#pnl-tbl tbody').innerHTML=L.length?L.map(p=>{const c=LC[p.name];return `<tr><td class="l" style="white-space:normal;min-width:200px">${esc(p.name)}</td><td class="num">${fmt.int(p.n)}</td><td class="num">${fmt.pct(p.win)}</td>${SC?`<td class="num">${c?fmt.pct(c.win):'–'}</td>`:''}<td class="num">${fmt.pct(p.pct,2)}</td><td class="num">${fmt.int(p.mn)}</td><td class="num">${p.mn>=5?fmt.pct(p.mwin):'–'}</td><td class="num">${p.mn>=5?fmt.pct(p.mpct,2):'–'}</td></tr>`}).join(''):`<tr><td colspan="8">No panel heard 10+ of our cases this season.</td></tr>`;
  const solo=L.filter(p=>p.mn<5).length;
  $('#pnl-note').innerHTML=`Collin often seats a panel for one agent's docket, so ${fmt.int(solo)} of these ${fmt.int(L.length)} line-ups heard fewer than 5 other cases and have no market comparison. The member chart is the fairer comparison.`}
  }
  // ledger (county)
  const t0=Y.tiers.filter(t=>t.n>=20).sort((a,b)=>(a.win-a.win_m)-(b.win-b.win_m))[0],worst=[...Y.cities].filter(c=>c.n>=30&&c.mwin!=null).sort((a,b)=>(a.win-a.mwin)-(b.win-b.mwin))[0],rt=U.resT||{};
  const U0=YC?YC.us:null,was=(v,f=fmt.int)=>YC&&v!=null?` <span class="note">(${SC}: ${f(v)})</span>`:'';
  $('#miss').innerHTML=[
   nc.n?`<b>${fmt.int(nc.n)} ARB "no change" results (${fmt.usd(nc.base)} of value).</b>${was(YC&&YC.nochange.n)} ${nc.matched?`Informal settlements in the same neighborhoods won ${fmt.pct(nc.infw)} of the time at ${fmt.pct(nc.infp,2)}.`:''} Look back at the evidence packets for these.`:null,
   `<b>${fmt.int(Y.lostNbrN)} properties we lost where neighbors won</b> (other agents won 70%+ in the neighborhood): about ${fmt.usd(Y.lostNbrEst)} of market value at the neighborhood's average cut. See the table above.`,
   rt['Dismissed / no-show']?`<b>${fmt.int(rt['Dismissed / no-show'])} dismissed or no-show results.</b>${was(U0&&U0.resT?U0.resT['Dismissed / no-show']||0:null)} Each one is a client with no hearing outcome. Worth checking against our hearing calendar.`:null,
   t0?`<b>${t0.tier} homes (${fmt.int(t0.n)} properties): ${fmt.pct(t0.win)} win rate</b> vs. ${fmt.pct(t0.win_m)} for other agents. Our biggest gap by value tier.`:null,
   worst&&worst.win<worst.mwin?`<b>${worst.c[0]+worst.c.slice(1).toLowerCase()} (${fmt.int(worst.n)} properties): ${fmt.pct(worst.win)} win rate</b> vs. ${fmt.pct(worst.mwin)} for other agents there. Our weakest city with 30+ properties.`:null,
   rt['Withdrawn']?`<b>${fmt.int(rt['Withdrawn'])} withdrawn.</b>`:null
  ].filter(Boolean).map(t=>`<li>${t}</li>`).join('');
}

/* ---------- Other insights (county) ---------- */
function renderMore(){
  const {y:SY,c:SC,w:SW}=sv('more');
  const Y=YR(SY),U=Y.us,pr=Y.prospects,M=Y.month;
  const mf=M.filter(m=>m.n>=20);const first=mf[0],last=mf[mf.length-1];
  const F=[
   ['info','A prospect list is sitting in this file',`<b>${fmt.int(pr.zero)}</b> owners who protested their own home got <b>no reduction</b> in ${SY}. ${fmt.int(pr.zero300)} of them have homes worth $300K+. Another ${fmt.int(pr.noshow)} owner-filed protests were dismissed or no-shows.${CFG.prospectNote?' '+CFG.prospectNote:''}`],
   ['info','Market share: plenty of room to grow',`Our ${fmt.int(U.props)} properties are ${fmt.pct(U.share,2)} of the ${CFG.county} properties protested by an agent in ${SY}. Our median starting value is ${fmt.usd(U.med)}.`],
   first&&last&&first!==last?['info',last.win>=first.win?'ARB results improved as the season went on':'ARB results slipped later in the season',`Our ARB win rate went from ${fmt.pct(first.win)} in ${first.m} to ${fmt.pct(last.win)} in ${last.m}, and our average cut from ${fmt.pct(first.pct,2)} to ${fmt.pct(last.pct,2)}. Other filers' ${last.m} ARB win rate was ${fmt.pct(last.mwin)}.`]:null
  ].filter(Boolean);
  $('#more-f').innerHTML=F.map(([t,h,b])=>`<div class="finding"><span class="tag ${t}">${t=='warn'?'Action':'Insight'}</span><h3>${h}</h3><p>${b}</p></div>`).join('');
}

/* ---------- Pipeline, book, context (new) ---------- */
function renderPipeline(){
  if(!document.getElementById('open-kpis'))return;
  const o=D.open,tot=o.byStatus.reduce((t,r)=>t+r[2],0),dt=d=>new Date(d+'T12:00').toLocaleDateString('en-US',{month:'short',day:'numeric'});
  $('#open-kpis').innerHTML=[[`Open protests, ${LASTY}`,fmt.int(tot),`All filers, as of ${dt(D.asOf)}`],['Property Tax Protest open',fmt.int(o.ours),o.ours?'Left out of results until they close':'Our book is fully closed'],...o.byWeek.map(r=>[`Hearings, week of ${dt(r[0])}`,fmt.int(+r[1]),'Open cases on the docket']),['Open, no future hearing date',fmt.int(o.noDocket),'Not scheduled, or the date has passed'],['Properties held out',fmt.int(o.closedPropsWithOpenCase),'Closed protest plus another still open']].map(t=>`<div class="kpi"><span class="eyebrow">${t[0]}</span><span class="v">${t[1]}</span><span class="d">${t[2]}</span></div>`).join('');
  $('#open-tbl tbody').innerHTML=o.byStatus.map(r=>`<tr><td>${esc(r[1])} <span class="note mono">${esc(r[0])}</span></td><td class="num">${fmt.int(r[2])}</td></tr>`).join('');
  const src={};for(const [us,b,s2,n] of D.compsrc){src[s2]=src[s2]||[0,0];if(us)src[s2][0]+=n;src[s2][1]+=n}
  $('#src-tbl tbody').innerHTML=Object.keys(src).map(k=>`<tr><td>${k}</td><td class="num">${fmt.int(src[k][0])}</td><td class="num">${fmt.int(src[k][1])}</td></tr>`).join('');
  const byY={};for(const [y,us,w,n] of D.wk){if(S.curve=='us'&&!us)continue;byY[y]=byY[y]||{};byY[y][w]=(byY[y][w]||0)+n}
  const wks=[];for(let w=14;w<=44;w++)wks.push(w);
  const shades=['#dde6e0','#bfcdc4','#93b39e','#5f9571','var(--us)'],colY=Object.fromEntries(YEARS.map((y,i)=>[y,shades[shades.length-YEARS.length+i]]));
  const ser=YEARS.map(y=>{const m=byY[y]||{},t=Object.values(m).reduce((a,b)=>a+b,0);let c=Object.entries(m).filter(([w])=>+w<14).reduce((a,[,v])=>a+v,0);return {name:String(y),color:colY[y],bold:y==LASTY,vals:wks.map(w=>{c+=m[w]||0;return t?c/t:null})}});
  const cats=wks.map(w=>{const d=new Date(LASTY,0,1+w*7);return d.getDate()<=7?d.toLocaleDateString('en-US',{month:'short'}):''});
  if($('#curve-chart')){lineChart($('#curve-chart'),{cats,fmt:v=>fmt.pct(v,0),w:560,h:220,series:ser,zero:true,cap1:true,dots:false});
  $('#curve-legend').innerHTML=YEARS.map(y=>`<span><i style="background:${colY[y]}"></i>${y}</span>`).join('');}
}
seg('#f-curve','curve',[['us','Property Tax Protest'],['all','All filers']],S,renderPipeline);
function renderBook(){
  if(!D.bookflow||!document.getElementById('book-chart'))return;
  const bf=D.bookflow;const w=760,lab=60,mid=230,sc=(w-lab-mid-190)/Math.max(...bf.map(b=>b.props));let g='';
  bf.forEach((b,i)=>{const y=i*34,hl=false;g+=`<text x="${lab-8}" y="${y+20}" text-anchor="end" class="${hl?'lab-us':''}">${b.year}</text>`;
    const lw=b.lost*sc;g+=`<rect x="${lab+mid-lw}" y="${y+6}" width="${lw}" height="20" rx="3" fill="var(--oth)" data-tip="${esc(`<b>${b.year}</b><br>Lost: ${fmt.int(b.lost)}`)}"/><text x="${lab+mid-lw-6}" y="${y+20}" text-anchor="end">${fmt.int(b.lost)} lost</text>`;
    const rw=b.retained*sc,nw=b.new*sc;g+=`<rect x="${lab+mid+2}" y="${y+6}" width="${rw-2}" height="20" rx="3" fill="var(--us)" data-tip="${esc(`<b>${b.year}</b><br>Retained: ${fmt.int(b.retained)}`)}"/><rect x="${lab+mid+rw+2}" y="${y+6}" width="${Math.max(nw-2,1)}" height="20" rx="3" fill="color-mix(in srgb,var(--us) 45%,var(--surface))" data-tip="${esc(`<b>${b.year}</b><br>New: ${fmt.int(b.new)}`)}"/><text x="${lab+mid+rw+nw+8}" y="${y+20}">${fmt.int(b.retained)} kept + ${fmt.int(b.new)} new</text>`});
  g+=`<line x1="${lab+mid+1}" x2="${lab+mid+1}" y1="0" y2="${bf.length*34}" stroke="var(--ink-3)"/>`;
  $('#book-chart').innerHTML=`<svg viewBox="0 0 ${w} ${bf.length*34+6}" role="img" aria-label="Retained, new and lost properties">${g}</svg>`;bindTips($('#book-chart'));
  $('#book-tbl tbody').innerHTML=bf.map(b=>`<tr><td>${b.year}</td><td class="num">${fmt.int(b.props)}</td><td class="num">${fmt.int(b.retained)}</td><td class="num">${fmt.int(b.new)}</td><td class="num">${fmt.int(b.lost)}</td><td style="text-align:left;white-space:normal;min-width:280px">${b.lostTo.map(x=>`${x[0]=='Property Tax Protest (us)'?'Property Tax Protest':nice(x[0])} ${fmt.int(x[1])}`).join(' · ')}</td></tr>`).join('');
}
function renderContext(){
  if(!D.context)return;
  const pr=Object.fromEntries(D.protestRate.map(r=>[r[0],r]));
  $('#ctx-tbl tbody').innerHTML=D.context.map(r=>{const p=pr[r[0]];return `<tr><td>${r[0]}</td><td class="num">${fmt.int(r[1])}</td><td class="num ${r[2]<0?'neg':''}">${fmt.pct(r[2],1)}</td><td class="num">${fmt.pct(r[3],0)}</td><td class="num">${fmt.pct(r[4],0)}</td><td class="num">${fmt.pct(r[5],1)}</td><td class="num">${p?fmt.int(p[2]):'–'}</td><td class="num">${p?fmt.pct(p[2]/p[1],1):'–'}</td><td class="num">${p?fmt.pct(D.yearsT.any[r[0]].us.props/p[2],2):'–'}</td></tr>`}).join('');
  renderContextNotes();
}
function renderMethod(){ /* county method text is static in the page body */ }

/* ---------- Results extras ---------- */
const rx={hs:'all',by:'city'};
seg('#imp-hs','hs',[['all','All homes'],['1','Homesteads'],['0','Non-homestead']],rx,()=>renderResultsExtra());
seg('#tax-by','by',[['city','By city'],['isd','By school district']],rx,()=>renderResultsExtra());
function renderResultsExtra(){
  if(!CFG.assessed)return;
  const {y:SY,c:SC,w:SW}=sv('results');const Y=YR(SY),U=Y.us;
  // impact by tier
  const T={};for(const r of Y.impact){if(rx.hs!='all'&&String(r.hs)!=rx.hs)continue;const t=T[r.tier]||(T[r.tier]={wins:0,f:0,p:0,z:0,mc:0,ac:0});t.wins+=r.wins;t.f+=r.full_;t.p+=r.part_;t.z+=r.zero;t.mc+=r.mc||0;t.ac+=r.ac||0}
  const trs=tiers.filter(t=>T[t]&&T[t].wins);
  const W=560,rh=30,L=90,R2=70,H=6+trs.length*rh+22,iw=W-L-R2;let g=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Tax impact of wins by tier">`;
  [0,.5,1].forEach(v=>g+=`<text x="${L+iw*v}" y="${H-6}" text-anchor="middle">${v*100}%</text>`);
  trs.forEach((t,i)=>{const a=T[t],y=6+i*rh;let x=L;g+=`<text x="${L-8}" y="${y+18}" text-anchor="end">${t}</text>`;
    [['f','var(--us)','Full'],['p','color-mix(in srgb,var(--us) 45%,var(--surface))','Partial'],['z','var(--bad)','None']].forEach(([k,c,nm])=>{const w=iw*a[k]/a.wins;if(w<=0)return;g+=`<rect x="${x}" y="${y+5}" width="${Math.max(w-2,0.5)}" height="${rh-12}" rx="2" fill="${c}" data-tip="${esc(`<b>${t}</b><br>${nm}: ${fmt.int(a[k])} of ${fmt.int(a.wins)} wins (${fmt.pct(a[k]/a.wins,0)})`)}"/>`;if(w>30)g+=`<text x="${x+w/2}" y="${y+18}" text-anchor="middle" style="fill:#fff;font-weight:600" pointer-events="none">${fmt.pct(a[k]/a.wins,0)}</text>`;x+=w});
    g+=`<text x="${L+iw+6}" y="${y+18}">${fmt.int(a.wins)}</text>`});
  $('#imp-chart').innerHTML=g+'</svg><p class="note">Number at right = wins in the tier.</p>';bindTips($('#imp-chart'));
  // cushion
  const cu=Y.cushion,lab=b=>b.split(': ')[1];
  $('#cush-tbl tbody').innerHTML=cu.map(r=>`<tr><td>${lab(r.band)}</td><td class="num">${fmt.int(r.n)}</td><td class="num">${fmt.pct(r.wins/r.n)}</td><td class="num ${r.zero/Math.max(r.wins,1)>0.3?'neg':''}">${fmt.int(r.zero)} (${fmt.pct(r.wins?r.zero/r.wins:0,0)})</td><td class="num">${fmt.usd(r.mc)}</td><td class="num">${fmt.usd(r.ac)}</td><td class="num">${fmt.pct(r.mc?r.ac/r.mc:null,0)}</td></tr>`).join('');
  // tax bands
  const tb=Y.taxBands,mx=Math.max(...tb.map(r=>r.n),1),W2=560,rh2=26,L2=110,iw2=W2-L2-90,H2=6+tb.length*rh2+6;let b=`<svg viewBox="0 0 ${W2} ${H2}" role="img" aria-label="Tax savings per win">`;
  tb.forEach((r,i)=>{const y=6+i*rh2,w=iw2*r.n/mx;b+=`<text x="${L2-8}" y="${y+16}" text-anchor="end">${lab(r.band)}</text><rect x="${L2}" y="${y+4}" width="${Math.max(w,1)}" height="${rh2-9}" rx="2" fill="${r.band.startsWith('0')?'var(--bad)':'var(--us)'}" data-tip="${esc(`<b>${lab(r.band)}</b><br>${fmt.int(r.n)} wins · ${fmt.usd(r.tax)} total`)}"/><text x="${L2+w+6}" y="${y+16}">${fmt.int(r.n)} · ${fmt.usd(r.tax)}</text>`});
  $('#band-chart').innerHTML=b+'</svg>';bindTips($('#band-chart'));
  // tax by
  const tt=$('#tax-tbl');
  if(rx.by=='city'){tt.querySelector('thead').innerHTML='<tr><th>City</th><th>Wins</th><th>Est. tax savings</th><th>Per win</th><th>Est. fees</th></tr>';tt.querySelector('tbody').innerHTML=Y.taxCity.map(r=>`<tr><td>${r.c[0]+r.c.slice(1).toLowerCase()}</td><td class="num">${fmt.int(r.wins)}</td><td class="num">${fmt.usd(r.tax)}</td><td class="num">${fmt.usd(r.wins?r.tax/r.wins:null)}</td><td class="num">${fmt.usd(r.fee)}</td></tr>`).join('')}
  else{tt.querySelector('thead').innerHTML='<tr><th>School district</th><th>Props</th><th>Wins</th><th>Est. tax savings</th><th>Per win</th></tr>';tt.querySelector('tbody').innerHTML=Y.taxIsd.map(r=>`<tr><td>${esc(r.isd)}</td><td class="num">${fmt.int(r.n)}</td><td class="num">${fmt.int(r.wins)}</td><td class="num">${fmt.usd(r.tax)}</td><td class="num">${fmt.usd(r.wins?r.tax/r.wins:null)}</td></tr>`).join('')}
  // callout
  const big=cu.filter(r=>r.band>='3').reduce((a,r)=>({n:a.n+r.n,w:a.w+r.wins,z:a.z+r.zero,mc:a.mc+r.mc}),{n:0,w:0,z:0,mc:0});
  const tot=tb.reduce((a,r)=>a+r.n,0),under100=tb.filter(r=>r.band<'2').reduce((a,r)=>a+r.n,0);
  $('#res-callout').innerHTML=`<b>What this means for ${SY}.</b> Of our ${fmt.int(U.won)} wins, ${fmt.int(U.capleak)} took $0 off this year's bill and ${fmt.int(U.capPartial)} took off only part. ${big.n?`Homes that started with a cap cushion of 10% or more (${fmt.int(big.n)} properties) produced ${fmt.int(big.z)} of those zero-impact wins. That makes the cushion a useful pre-filing screen for setting client expectations.`:''} ${fmt.int(under100)} of ${fmt.int(tot)} wins (${fmt.pct(tot?under100/tot:0,0)}) saved the client under $100 this year. Estimated client savings total <b>${fmt.usd(U.tax)}</b>, vs. <b>${fmt.usd(U.fee)}</b> in estimated fees.`;
}

/* ---------- Wins extras ---------- */
const wx={by:'age'};
seg('#ws-by','by',[['age','Home age'],['size','Home size']],wx,()=>renderWinsExtra());
function renderWinsExtra(){
  const {y:SY,c:SC,w:SW}=sv('wins');const Y=YR(SY);const src=Y[wx.by];
  const bands=[...new Set(src.map(r=>r.b))].sort();const get=(b,g)=>src.find(r=>r.b==b&&r.g==g);
  if($('#ws-chart')){
  const W=560,gh=48,L=120,R2=80,H=8+bands.length*gh+22,x=v=>L+(W-L-R2)*(v||0);let s=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Win rate by ${wx.by}">`;
  for(let i=0;i<=4;i++){const gx=L+(W-L-R2)*i/4;s+=`<line class="grid" x1="${gx}" x2="${gx}" y1="8" y2="${H-22}"/><text x="${gx}" y="${H-6}" text-anchor="middle">${i*25}%</text>`}
  bands.forEach((b,i)=>{const y=8+i*gh;s+=`<text x="${L-8}" y="${y+26}" text-anchor="end">${b.split(': ')[1]}</text>`;
    [['us','var(--us)',4],['ag','var(--agents)',17],['own','var(--own)',30]].forEach(([g,c,dy])=>{const r=get(b,g);if(!r)return;s+=`<rect x="${L}" y="${y+dy}" width="${Math.max(x(r.win)-L,1)}" height="11" rx="2" fill="${c}" data-tip="${esc(`<b>${b.split(': ')[1]}</b><br>${g=='us'?'Property Tax Protest':g=='ag'?'All other agents':'Ownwell'}: ${fmt.pct(r.win)} win, ${fmt.pct(r.pct,2)} reduction (${fmt.int(r.n)} props)`)}"/>${g=='us'?`<text x="${x(r.win)+6}" y="${y+14}" class="lab-us">${fmt.pct(r.win,0)} <tspan style="fill:var(--ink-3);font-weight:400">n=${fmt.int(r.n)}</tspan></text>`:''}`})});
  $('#ws-chart').innerHTML=s+'</svg>';bindTips($('#ws-chart'));}
  if($('#isd-tbl'))$('#isd-tbl tbody').innerHTML=Y.isdWin.map(r=>`<tr><td>${esc(r.isd)}</td><td class="num">${fmt.int(r.n)}</td><td class="num ${r.mwin!=null&&r.win<r.mwin-0.05?'neg':''}">${fmt.pct(r.win)}</td><td class="num">${fmt.pct(r.mwin)}</td><td class="num">${fmt.pct(r.pct,2)}</td><td class="num">${fmt.pct(r.mpct,2)}</td></tr>`).join('');
  const nbn=nb=>`<span class="mono">${esc(nb||'')}</span> ${esc((D.nbNames[nb]||'').slice(0,28))}`,cap=c=>c?c[0]+c.slice(1).toLowerCase():'';
  $('#big-tbl tbody').innerHTML=Y.bigWins.map(r=>`<tr><td class="mono">${r[0]}</td><td class="l" style="white-space:normal;min-width:160px">${nbn(r[1])}</td><td class="l">${cap(r[2])}</td><td class="num">${fmt.usd(r[3])}</td><td class="num">${fmt.usd(r[4])}</td><td class="num">${fmt.pct(r[5],1)}</td>${CFG.tax?`<td class="num">${fmt.usd(r[8])}</td>`:''}<td class="l" style="white-space:normal;min-width:140px">${esc(r[6])}</td></tr>`).join('');
  $('#ln-sub').innerHTML=`Our residential properties with no win (by the current "Count as a win" rule) in neighborhoods where other agents won at least 70% of the time (5+ of their properties). <b>${fmt.int(Y.lostNbrN)}</b> properties, about <b>${fmt.usd(Y.lostNbrEst)}</b> of market value at the neighborhood's average cut. Top 60 shown, largest first.`;
  $('#ln-tbl tbody').innerHTML=Y.lostNbr.map(r=>`<tr><td class="mono">${r[0]}</td><td class="l" style="white-space:normal;min-width:160px">${nbn(r[1])}</td><td class="l">${cap(r[2])}</td><td class="num">${fmt.usd(r[3])}</td><td class="l" style="white-space:normal;min-width:140px">${esc(r[4])}</td><td class="num">${fmt.pct(r[6],0)} of ${fmt.int(r[5])}</td><td class="num">${fmt.pct(r[7],2)}</td><td class="num">${fmt.usd(r[8])}</td></tr>`).join('');
}

/* ---------- Open by agent, lost list, context notes ---------- */
function renderOpenAgents(){
  if(!document.getElementById('oa-tbl'))return;
  const sh=D.openShare;
  $('#oa-tbl tbody').innerHTML=D.openAgents.slice(0,12).map(r=>`<tr class="${r[0]==US?'us':''}"><td>${nice(r[0])}</td><td class="num">${fmt.int(r[1])}</td><td class="num">${fmt.pct(sh[r[0]]?r[1]/sh[r[0]]:null,0)}</td><td class="num">${fmt.int(r[6])}</td><td class="num">${r[3]?`${new Date(r[3]+'T12:00').toLocaleDateString('en-US',{month:'short',day:'numeric'})}${r[4]&&r[4]!=r[3]?'–'+new Date(r[4]+'T12:00').toLocaleDateString('en-US',{month:'short',day:'numeric'}):''}`:'–'}</td><td class="num">${fmt.int(r[5])}</td></tr>`).join('');
  const own=D.openAgents.find(r=>r[0]==OWN),tot=D.openAgents.reduce((a,r)=>a+r[1],0);
  $('#oa-note').innerHTML=`${D.ourHeld?`${fmt.int(D.ourHeld)} of our properties have an open protest and are held out. `:''}${fmt.int(D.excludedOpen)} properties with a closed protest but another still open are left out of results.`;
}
const lx={y:LASTY,f:'all'};
function renderLost(){
  if(!D.lost||!document.getElementById('lost-tbl'))return;
  $('#lost-y').innerHTML=YEARS.slice(1).reverse().map(y=>`<option${y==lx.y?' selected':''}>${y}</option>`).join('');
  const rs=D.lost[lx.y].filter(r=>lx.f=='all'||(lx.f=='agent'?(r[6]!='Not protested'&&r[6]!='Owners (self-filed)'):lx.f=='none'?r[6]=='Not protested':r[6]=='Owners (self-filed)'));
  const cap=c=>c?c[0]+c.slice(1).toLowerCase():'';
  $('#lost-tbl tbody').innerHTML=rs.map(r=>`<tr><td class="mono">${r[0]}</td><td class="l" style="white-space:normal;min-width:160px"><span class="mono">${esc(r[1]||'')}</span> ${esc((D.nbNames[r[1]]||'').slice(0,26))}</td><td class="l">${cap(r[2])}</td><td class="num">${fmt.usd(r[3])}</td><td class="l" style="white-space:normal;min-width:130px">${esc(r[4]||'')}</td><td class="num">${fmt.usd(r[5])}</td><td class="l">${r[6]=='Not protested'?'Not protested':nice(r[6])}</td><td class="l" style="white-space:normal;min-width:130px">${esc(r[7]||'–')}</td></tr>`).join('')||'<tr><td colspan="8">None.</td></tr>';
}
$('#lost-y').onchange=e=>{lx.y=+e.target.value;renderLost()};
seg('#lost-f','f',[['agent','Went to another agent'],['own','Owner filed'],['none','Not protested'],['all','All']],lx,()=>renderLost());
function renderContextNotes(){
  const C=Object.fromEntries(D.context.map(r=>[r[0],r])),PR=Object.fromEntries(D.protestRate.map(r=>[r[0],r]));
  const note=y=>{const c=C[y],p=PR[y];if(!c)return '';const up=c[2]>0.05?'rose sharply':c[2]>0?'rose slightly':'fell';return `<li><b>${y}:</b> notices ${up} (median ${fmt.pct(c[2],1)}), ${fmt.pct(c[4],0)} of homesteads were held below market by the 10% cap, and ${p?fmt.pct(p[2]/p[1],0):'–'} of residential accounts were protested. ${c[4]>0.6?'Market wins often didn\'t reach the tax bill this year.':c[4]<0.3?'Most market wins reached the tax bill this year.':''}</li>`};
  $('#ctx-notes').innerHTML=YEARS.map(note).join('');
}

function renderAll(){$('#h-year').textContent=S.year;SECS.forEach(drawSecCtl);renderKPIs();renderFindings();renderExplorerAndYoY();renderResults();renderResultsExtra();renderMatched();renderPath();renderWins();renderWinsExtra();renderMore();renderPipeline();renderOpenAgents();renderBook();renderLost();renderContext();renderYoY()}
(CFG.hide||[]).forEach(([id,why])=>hideSec(id,why));
renderMethod();renderAll();

