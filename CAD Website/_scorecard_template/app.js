const D=JSON.parse(document.getElementById('data').textContent);
const US='PROPERTY TAX PROTEST',OWN='Ownwell',OWNERS='Owners (self-filed)',NOAG='No agent · other appellant';
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');
const fmt={pct:(v,dp=1)=>v==null||!isFinite(v)?'–':(v*100).toFixed(dp)+'%',int:v=>v==null||isNaN(v)?'–':Math.round(v).toLocaleString('en-US'),
  usd:v=>{if(v==null||isNaN(v))return'–';const a=Math.abs(v),s=v<0?'−':'';return a>=1e9?s+'$'+(a/1e9).toFixed(2)+'B':a>=1e6?s+'$'+(a/1e6).toFixed(1)+'M':a>=1e3?s+'$'+(a/1e3).toFixed(0)+'K':s+'$'+a.toFixed(0)},
  full:v=>v==null||isNaN(v)?'–':(v<0?'−$':'$')+Math.abs(Math.round(v)).toLocaleString('en-US'),
  pp:v=>v==null||!isFinite(v)?'–':(v>=0?'+':'−')+Math.abs(v*100).toFixed(1)};
const nice=n=>{if(n==US)return 'Property Tax Protest';if([OWN,OWNERS,NOAG,'Other agents','All other agents',"O'Connor & Associates",'Ryan (all codes)'].includes(n))return n;
  return n.replace(/\b(INC|LLC|LP|dba OLA TAX)\b/gi,'').replace(/^THE /,'').replace(/ SERV$/,' SERVICES').replace(/ SOLUTION$/,' SOLUTIONS').trim().toLowerCase().replace(/\b\w/g,c=>c.toUpperCase())};
const BRAND={[OWN]:'var(--own)','RESOLUTE PROPERTY TAX SOLUTION':'var(--b-resolute)','Ryan (all codes)':'var(--b-ryan)',"O'Connor & Associates":'var(--b-oconnor)','TEXAS TAX PROTEST':'var(--b-ttp)'};
const tip=$('#tip');
function bindTips(root){root.querySelectorAll('[data-tip]').forEach(el=>{el.addEventListener('mousemove',e=>{tip.innerHTML=el.dataset.tip;tip.style.opacity=1;tip.style.left=Math.min(e.clientX+14,innerWidth-290)+'px';tip.style.top=(e.clientY+14)+'px'});el.addEventListener('mouseleave',()=>tip.style.opacity=0)})}
const rows=D.cube.map(r=>Object.fromEntries(D.cols.map((c,i)=>[c,r[i]])));
const TIERS=D.tiers;
const WIN={w:'Any reduction',w500:'$500+ reduction',w1k:'$1,000+ reduction',w2500:'$2,500+ reduction',wpct:'0.25%+ of value'};
let WC='w';
$('#f-win').innerHTML=Object.entries(WIN).map(([k,l])=>`<option value="${k}">${l}</option>`).join('');
$('#f-win').onchange=e=>{WC=e.target.value;renderAll()};
const ACC=['n','w','bM','rM','sp','pn','pv','pnv','pfv','infN','arbN','othN','infW','arbW','infS','arbS','all'];
function agg(f){const by={};
  rows.forEach(r=>{if(f.sub&&f.sub!='all'&&r.sub!=f.sub)return;if(f.hs&&f.hs!='all'&&String(r.hs)!=f.hs)return;if(f.tier&&f.tier!='all'&&(f.tier=='300+'?r.tier=='<$300K':r.tier!=f.tier))return;
    const a=by[r.A]||(by[r.A]=Object.assign({A:r.A},Object.fromEntries(ACC.map(k=>[k,0]))));const w=r[WC];
    a.all+=r.n;if(r.pth=='Informal'){a.infN+=r.n;a.infW+=w;a.infS+=r.sp}else if(r.pth=='ARB'){a.arbN+=r.n;a.arbW+=w;a.arbS+=r.sp}else a.othN+=r.n;
    if(f.path&&f.path!='all'&&r.pth!=f.path)return;
    a.n+=r.n;a.w+=w;a.bM+=r.bM;a.rM+=r.rM;a.sp+=r.sp;a.pn+=r.pn;a.pv+=r.pv;a.pnv+=r.pnv;a.pfv+=r.pfv});
  const list=Object.values(by).map(fin);
  const sum=(l,name)=>fin(l.reduce((s,a)=>{ACC.forEach(k=>s[k]+=a[k]);return s},Object.assign({A:name},Object.fromEntries(ACC.map(k=>[k,0])))));
  const others=sum(list.filter(a=>![US,OWNERS,NOAG].includes(a.A)),'All other agents');others.agg=true;
  return {list:list.filter(a=>a.n>0),by:Object.fromEntries(list.map(a=>[a.A,a])),others,sum}}
function fin(a){return Object.assign(a,{win:a.n?a.w/a.n:null,redPct:a.bM?a.rM/a.bM:null,avgPct:a.n?a.sp/a.n:null,perWin:a.w?a.rM/a.w:null,cutPer:a.n?a.rM/a.n:null,avgStart:a.n?a.bM/a.n:null,
  inf:a.all?a.infN/a.all:null,arb:a.all?a.arbN/a.all:null,oth:a.all?a.othN/a.all:null,infWin:a.infN?a.infW/a.infN:null,arbWin:a.arbN?a.arbW/a.arbN:null,infPct:a.infN?a.infS/a.infN:null,arbPct:a.arbN?a.arbS/a.arbN:null,
  nvp:a.pv?a.pnv/a.pv-1:null,fvp:a.pv?a.pfv/a.pv-1:null})}
const METRICS=[['win','Win rate',v=>fmt.pct(v)],['redPct','Mkt reduction %',v=>fmt.pct(v,2)],['avgPct','Avg % / property',v=>fmt.pct(v,2)],['rM','Mkt value cut',fmt.usd],['perWin','$ per win',fmt.usd],['cutPer','$ cut per account',fmt.usd],['n','Accounts',fmt.int],['avgStart','Avg notice value',fmt.usd],['inf','Informal share',v=>fmt.pct(v,0)],['arb','ARB share',v=>fmt.pct(v,0)],['infWin','Informal win rate',v=>fmt.pct(v)],['arbWin','ARB win rate',v=>fmt.pct(v)],['oth','No-show / withdrawn share',v=>fmt.pct(v,1)]];
const MF=Object.fromEntries(METRICS.map(m=>[m[0],m]));

/* ---------- KPIs + findings ---------- */
function renderKPIs(){
  const g=agg({}),U=g.by[US],O=g.others,R=agg({sub:'Residential'}),UR=R.by[US],OR=R.others;
  const open=D.open[US]||0;
  $('#kpis').innerHTML=[
    ['Accounts protested',fmt.int(U.n+open),`${fmt.int(U.n)} closed · ${fmt.int(open)} still open`],
    ['Win rate',fmt.pct(U.win),`All other agents ${fmt.pct(O.win)} · ${WIN[WC].toLowerCase()}`],
    ['Market value cut',fmt.usd(U.rM),`${fmt.pct(U.redPct,1)} of notice value · others ${fmt.pct(O.redPct,1)}`],
    ['Avg cut per account',fmt.pct(U.avgPct,1),`${fmt.usd(U.cutPer)} each · others ${fmt.pct(O.avgPct,1)}`],
    ['Est. fee revenue',fmt.usd(U.rM*0.01),'1% of our market cut, before collections']
  ].map(([l,v,d])=>`<div class="kpi"><span class="eyebrow">${l} · 2026</span><span class="v">${v}</span><span class="d">${d}</span></div>`).join('');
  const m=D.matched.find(x=>x.peer=='All other agents'),own=D.matched.find(x=>x.peer==OWN),self=D.matched.find(x=>x.peer==OWNERS);
  const F=[];
  F.push([UR.win>=OR.win?'good':'warn',`We win ${fmt.pct(UR.win)} of residential protests`,`Other agents win <b>${fmt.pct(OR.win)}</b> and owners who filed themselves win ${fmt.pct(R.by[OWNERS].win)}. Only ${fmt.int(UR.n-UR.w)} of our ${fmt.int(UR.n)} closed residential properties ended with no cut.`]);
  if(m)F.push([m.up>=m.pp?'good':'bad',m.up>=m.pp?'Deeper cuts than other agents next door':'Our cuts are shallower than other agents next door',`In the same TCAD neighborhoods we win <b>${fmt.pct(m.uw)}</b> vs. ${fmt.pct(m.pw)}, but cut <b>${fmt.pct(m.up,1)}</b> vs. ${fmt.pct(m.pp,1)} on average. At their neighborhood rates our book would have been cut by about <b>${fmt.usd(m.gap)}</b> more market value (~${fmt.usd(m.gap*0.01)} in fees).${own?` Against Ownwell alone the gap is ${fmt.usd(own.gap)} (${fmt.pct(own.up,1)} vs. ${fmt.pct(own.pp,1)}).`:''}`]);
  F.push(['info',`${fmt.pct(UR.inf,0)} of our residential book settled informally`,`Informal settlements averaged <b>${fmt.pct(UR.infPct,1)}</b> for us vs. ${fmt.pct(OR.infPct,1)} for other agents. ${UR.arbN?`At formal ARB we averaged <b>${fmt.pct(UR.arbPct,1)}</b> on ${fmt.int(UR.arbN)} hearings vs. ${fmt.pct(OR.arbPct,1)}.`:''}`]);
  F.push([UR.oth>OR.oth+0.01?'warn':'info',`${fmt.int(UR.othN)} of our properties ended as a no-show, withdrawal or dismissal`,`That is ${fmt.pct(UR.oth,1)} of our residential book vs. ${fmt.pct(OR.oth,1)} for other agents. Each is a client with no reduction and no fee.`]);
  if(self)F.push(['good','Clearly ahead of owners who file themselves',`In the same neighborhoods, owners who filed themselves won ${fmt.pct(self.pw)} and cut ${fmt.pct(self.pp,1)}; we won ${fmt.pct(self.uw)} and cut ${fmt.pct(self.up,1)}.`]);
  {const sw=Object.entries(D.checks.sharedWith)[0];if(sw)F.push(['warn',`${fmt.int(D.checks.oursShared)} of our properties list another agent too`,`TCAD also lists another firm on these accounts, most often ${esc(nice(sw[0]))} (${fmt.int(sw[1])}). We filed the 2026 appeal, so they count as ours here. See Data checks.`])}
  $('#findings').innerHTML=F.map(([t,h,b])=>`<div class="finding"><span class="tag ${t}">${{good:'Strength',info:'Context',warn:'Watch',bad:'Underperforming'}[t]}</span><h3>${h}</h3><p>${b}</p></div>`).join('');
}

/* ---------- explorer ---------- */
const st={sub:'Residential',hs:'all',path:'all',tier:'all',metric:'win',sort:'n',dir:'desc'};
function seg(id,key,opts,obj,cb){const el=$(id);el.innerHTML=opts.map(([v,l])=>`<button type="button" data-v="${v}" aria-pressed="${obj[key]==v}">${l}</button>`).join('');el.onclick=e=>{const b=e.target.closest('button');if(!b)return;obj[key]=b.dataset.v;el.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));cb()}}
seg('#f-sub','sub',[['all','All'],['Residential','Residential'],['Non-residential','Non-residential']],st,()=>renderExplorer());
if($('#f-hs'))seg('#f-hs','hs',[['all','All'],['1','Homestead'],['0','Non-homestead']],st,()=>renderExplorer());
seg('#f-path','path',[['all','All'],['Informal','Informal'],['ARB','Formal ARB'],['Other','No-show / withdrawn']],st,()=>renderExplorer());
$('#f-tier').innerHTML=[['all','All values'],['300+','$300K and up'],...TIERS.map(t=>[t,t])].map(([v,l])=>`<option value="${esc(v)}">${l}</option>`).join('');
$('#f-tier').onchange=e=>{st.tier=e.target.value;renderExplorer()};
$('#f-metric').innerHTML=METRICS.map(([k,l])=>`<option value="${k}">${l}</option>`).join('');
$('#f-metric').onchange=e=>{st.metric=e.target.value;renderExplorer()};
const COLS=[['A','Agent'],['n','Accounts'],['win','Win rate'],['redPct','Mkt reduction %'],['avgPct','Avg % / property'],['rM','Mkt value cut'],['perWin','$ per win'],['inf','Informal share'],['arb','ARB share'],['oth','No-show / withdrawn']];
const F2={n:fmt.int,win:v=>fmt.pct(v),redPct:v=>fmt.pct(v,2),avgPct:v=>fmt.pct(v,2),rM:fmt.usd,perWin:fmt.usd,inf:v=>fmt.pct(v,0),arb:v=>fmt.pct(v,0),oth:v=>fmt.pct(v,1)};
function renderExplorer(){
  const {list,others}=agg(st);const k=st.sort;
  const sorted=[...list].sort((a,b)=>k=='A'?a.A.localeCompare(b.A):((b[k]??-1e9)-(a[k]??-1e9)));if(st.dir=='asc')sorted.reverse();
  const tb=$('#exp-tbl');
  tb.querySelector('thead').innerHTML='<tr>'+COLS.map(([c,l])=>`<th><button type="button" data-k="${c}"${st.sort==c?` data-dir="${st.dir}"`:''}>${l}</button></th>`).join('')+'</tr>';
  const mx={};COLS.slice(1).forEach(([c])=>mx[c]=Math.max(...list.map(r=>r[c]||0),1e-9));
  const row=r=>`<tr class="${r.A==US?'us':''}${r.agg||[OWNERS,NOAG,'Other agents'].includes(r.A)?' agg':''}">`+COLS.map(([c])=>c=='A'?`<td>${esc(nice(r.A))}</td>`:(c=='win'||c=='redPct')&&!r.agg?`<td class="num"><span class="cellbar">${F2[c](r[c])}<i style="width:${Math.max(2,48*(r[c]||0)/mx[c])}px"></i></span></td>`:`<td class="num">${F2[c](r[c])}</td>`).join('')+'</tr>';
  tb.querySelector('tbody').innerHTML=sorted.map(row).join('')+(others.n?row(others):'');
  tb.querySelectorAll('th button').forEach(b=>b.onclick=()=>{const c=b.dataset.k;if(st.sort==c)st.dir=st.dir=='desc'?'asc':'desc';else{st.sort=c;st.dir='desc'}renderExplorer()});
  const m=st.metric,[,lab,f]=MF[m];
  const data=list.filter(r=>r.n>=20&&r[m]!=null).sort((a,b)=>b[m]-a[m]);
  hbar('#exp-chart',data.map(r=>({label:nice(r.A),c:BRAND[r.A],v:r[m],us:r.A==US,tip:`<b>${esc(nice(r.A))}</b><br>${lab}: ${f(r[m])}<br>${fmt.int(r.n)} accounts`})),{fmt:f,ref:others.n&&others[m]!=null?{v:others[m],label:'All other agents '+f(others[m])}:null});
}
function hbar(sel,data,o){
  const W=900,rowH=22,L=260,R=70,top=8,H=top+data.length*rowH+24;
  const lo=Math.min(0,...data.map(d=>d.v)),max=(Math.max(...data.map(d=>d.v),o.ref?o.ref.v:0)*1.05)||1,x=v=>L+(W-L-R)*(v-lo)/(max-lo);
  let s=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Bar chart">`;
  for(let i=0;i<=4;i++){const v=lo+(max-lo)*i/4,gx=x(v);s+=`<line class="grid" x1="${gx}" x2="${gx}" y1="${top}" y2="${H-22}"/><text x="${gx}" y="${H-6}" text-anchor="middle">${o.fmt(v)}</text>`}
  data.forEach((d,i)=>{const y=top+i*rowH,x0=x(Math.min(0,d.v)),w=Math.max(1,Math.abs(x(d.v)-x(0)));
    s+=`<g data-tip="${esc(d.tip)}"><rect x="0" y="${y}" width="${W}" height="${rowH}" fill="transparent"/><text x="${L-10}" y="${y+15}" text-anchor="end" class="${d.us?'lab-us':''}">${esc(d.label)}</text><rect x="${x0}" y="${y+4}" width="${w}" height="${rowH-8}" rx="2" fill="${d.us?'var(--us)':(d.c||'var(--comp-2)')}"/><text x="${x0+w+6}" y="${y+15}" class="${d.us?'lab-us':''}">${o.fmt(d.v)}</text></g>`});
  if(o.ref){const rx=x(o.ref.v);s+=`<line x1="${rx}" x2="${rx}" y1="${top-4}" y2="${H-22}" stroke="var(--ink)" stroke-dasharray="3 3"/>`}
  $(sel).innerHTML=s+'</svg>'+`<p class="note">${o.ref?`Dashed line: ${o.ref.label}. `:''}Groups with fewer than 20 accounts under the current filter are hidden.</p>`;bindTips($(sel));
}

/* ---------- journey ---------- */
const js={sub:'Residential'};
if($('#j-sub'))seg('#j-sub','sub',[['all','All'],['Residential','Residential'],['Non-residential','Non-residential']],js,()=>renderJourney());
function renderJourney(){if(!$('#flow'))return;
  const g=agg(js),U=g.by[US]||fin(Object.fromEntries(ACC.map(k=>[k,0]))),ents=[[US,U],['All other agents',g.others],...(g.by[OWN]?[[OWN,g.by[OWN]]]:[]),[OWNERS,g.by[OWNERS]],[NOAG,g.by[NOAG]]].filter(e=>e[1]);
  $('#flow').innerHTML=[['2025 roll value',U.pv,`${fmt.int(U.pn)} of our closed accounts with a 2025 value`],['2026 notice',U.pnv,`${fmt.pct(U.nvp,1)} vs 2025`],['Final 2026 value',U.pfv,`${fmt.pct(U.fvp,1)} vs 2025 · ${fmt.usd(U.pnv-U.pfv)} cut`],['Cut from notice',U.pnv?(U.pnv-U.pfv)/U.pnv:null,'share of notice value removed']]
    .map(([l,v,s],i)=>`<div class="step${i==3?' us':''}"><span class="eyebrow">${l}</span><span class="v">${i==3?fmt.pct(v,1):fmt.usd(v)}</span><span class="s">${s}</span></div>`).join('');
  $('#j-tbl tbody').innerHTML=ents.map(([n,a])=>`<tr class="${n==US?'us':''}${n=='All other agents'?' agg':''}"><td>${esc(nice(n))}</td><td class="num">${fmt.int(a.pn)}</td><td class="num">${fmt.usd(a.pv)}</td><td class="num">${fmt.usd(a.pnv)}</td><td class="num">${fmt.usd(a.pfv)}</td><td class="num">${fmt.pct(a.nvp,1)}</td><td class="num ${a.fvp<0?'pos':''}">${fmt.pct(a.fvp,1)}</td><td class="num">${fmt.pct(a.pnv?(a.pnv-a.pfv)/a.pnv:null,1)}</td></tr>`).join('');
}

/* ---------- like-for-like ---------- */
function renderMatched(){
  $('#m-tbl tbody').innerHTML=D.matched.map(m=>{const edge=m.up-m.pp;return `<tr${m.peer=='All other agents'?' class="agg"':''}><td>${esc(nice(m.peer))}</td><td class="num">${fmt.int(m.n)}</td><td class="num">${fmt.int(m.grids)}</td><td class="num">${fmt.pct(m.uw)}</td><td class="num">${fmt.pct(m.pw)}</td><td class="num">${fmt.pct(m.up,2)}</td><td class="num">${fmt.pct(m.pp,2)}</td><td class="num ${edge>=0?'pos':'neg'}">${fmt.pp(edge)}</td><td class="num">${fmt.pct(m.inf,0)}</td><td class="num ${m.gap>0?'neg':'pos'}">${fmt.usd(m.gap)}</td></tr>`}).join('');
}
const gs={min:3,q:'',sort:'gap',dir:'desc'};
const GC=[['code','Neighborhood',r=>esc(r[0])],['un','Our accts',r=>fmt.int(r[1])],['uw','Our win',r=>fmt.pct(r[2])],['up','Our avg',r=>fmt.pct(r[3],1)],['ucut','Our $ cut',r=>fmt.usd(r[4])],['pn','Their accts',r=>fmt.int(r[5])],['pw','Their win',r=>fmt.pct(r[6])],['pp','Their avg',r=>fmt.pct(r[7],1)],['gap','$ gap',r=>r[8]==null?'–':fmt.usd(r[8])]];
const GI={code:0,un:1,uw:2,up:3,ucut:4,pn:5,pw:6,pp:7,gap:8};
$('#g-min').onchange=e=>{gs.min=+e.target.value;renderGrids()};$('#g-q').oninput=e=>{gs.q=e.target.value.trim().toUpperCase();renderGrids()};
function renderGrids(){
  let r=D.grids.filter(g=>g[1]>=gs.min&&(!gs.q||g[0].toUpperCase().includes(gs.q)));const i=GI[gs.sort];
  r.sort((a,b)=>i==0?String(a[0]).localeCompare(b[0]):((b[i]??-1e15)-(a[i]??-1e15)));if(gs.dir=='asc')r.reverse();
  $('#g-tbl thead').innerHTML='<tr>'+GC.map(([k,l])=>`<th><button type="button" data-k="${k}"${gs.sort==k?` data-dir="${gs.dir}"`:''}>${l}</button></th>`).join('')+'</tr>';
  $('#g-tbl tbody').innerHTML=r.slice(0,400).map(g=>'<tr>'+GC.map(([k,,f])=>`<td class="${k=='code'?'mono':'num'}${k=='gap'&&g[8]!=null?(g[8]>0?' neg':' pos'):''}">${f(g)}</td>`).join('')+'</tr>').join('')||'<tr><td colspan="9" class="l">No neighborhoods match.</td></tr>';
  $('#g-tbl').querySelectorAll('th button').forEach(b=>b.onclick=()=>{const k=b.dataset.k;if(gs.sort==k)gs.dir=gs.dir=='desc'?'asc':'desc';else{gs.sort=k;gs.dir=k=='code'?'asc':'desc'}renderGrids()});
  $('#g-note').textContent=`${fmt.int(r.length)} neighborhoods${r.length>400?' · showing the first 400':''}. "$ gap" = what we would have cut at other agents' average rate in that neighborhood, minus what we cut (needs 3+ of their accounts). Positive means they did better.`;
}

/* ---------- path ---------- */
function renderPath(){
  const g=agg({sub:'Residential'}),ents=[[US,g.by[US]],['All other agents',g.others],...D.firms.filter(f=>f!=US&&g.by[f]).map(f=>[f,g.by[f]]),[OWNERS,g.by[OWNERS]]];
  const U=g.by[US],O=g.others;
  $('#path-h').textContent=U.inf>=O.inf-0.02?'Almost everything settles informally, for us and for everyone else':'We take more cases to the ARB than other agents';
  $('#path-lede').textContent=`Residential. ${fmt.pct(U.inf,0)} of our closed accounts settled by joint motion, ${fmt.pct(U.arb,1)} went to a formal ARB hearing and ${fmt.pct(U.oth,1)} ended as a no-show or withdrawal. Other agents: ${fmt.pct(O.inf,0)}, ${fmt.pct(O.arb,1)} and ${fmt.pct(O.oth,1)}.`;
  const W=900,rowH=22,L=260,R=20,H=ents.length*rowH+10;let s=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Resolution mix">`;
  ents.forEach(([n,a],i)=>{const y=4+i*rowH;let x=L;const segs=[['inf','var(--inf)','Informal'],['arb','var(--arb)','ARB'],['oth','var(--oth)','No-show / withdrawn']];
    s+=`<text x="${L-10}" y="${y+15}" text-anchor="end" class="${n==US?'lab-us':''}">${esc(nice(n))}</text>`;
    segs.forEach(([k,c,l])=>{const w=(W-L-R)*(a[k]||0);if(w>0)s+=`<rect x="${x}" y="${y+4}" width="${w}" height="${rowH-8}" fill="${c}" data-tip="<b>${esc(nice(n))}</b><br>${l}: ${fmt.pct(a[k],1)} (${fmt.int(a[k+'N']||a.othN)})"/>`;x+=w})});
  $('#mix-chart').innerHTML=s+'</svg>';bindTips($('#mix-chart'));
  const d=ents.filter(([,a])=>a.infN>=20);const mx=Math.max(...d.flatMap(([,a])=>[a.infPct||0,a.arbN>=20?a.arbPct:0]))*1.1;const H2=d.length*rowH+30;
  let t=`<svg viewBox="0 0 ${W} ${H2}" role="img" aria-label="Average reduction by path">`;const xx=v=>L+(W-L-60)*v/mx;
  for(let i=0;i<=4;i++){const v=mx*i/4;t+=`<line class="grid" x1="${xx(v)}" x2="${xx(v)}" y1="4" y2="${H2-22}"/><text x="${xx(v)}" y="${H2-6}" text-anchor="middle">${fmt.pct(v,0)}</text>`}
  d.forEach(([n,a],i)=>{const y=4+i*rowH+11;t+=`<text x="${L-10}" y="${y+4}" text-anchor="end" class="${n==US?'lab-us':''}">${esc(nice(n))}</text>`;
    const pts=[[a.infPct,'var(--inf)','Informal',a.infN]];if(a.arbN>=20)pts.push([a.arbPct,'var(--arb)','ARB',a.arbN]);
    if(pts.length==2)t+=`<line x1="${xx(pts[0][0])}" x2="${xx(pts[1][0])}" y1="${y}" y2="${y}" stroke="var(--line)" stroke-width="3"/>`;
    pts.forEach(([v,c,l,nn])=>t+=`<circle cx="${xx(v)}" cy="${y}" r="6" fill="${c}" stroke="var(--surface)" stroke-width="1.5" data-tip="<b>${esc(nice(n))}</b><br>${l}: ${fmt.pct(v,1)} avg on ${fmt.int(nn)} cases"/>`)});
  $('#db-chart').innerHTML=t+'</svg>';bindTips($('#db-chart'));
}

/* ---------- tiers ---------- */
function renderTiers(){
  const per=TIERS.map(t=>{const g=agg({sub:'Residential',tier:t});return {t,u:g.by[US],o:g.others,w:g.by[OWN]}}).filter(x=>x.u&&x.u.n>=5);
  const W=900,H=280,L=50,B=40,T=14,gw=(W-L-10)/per.length,bw=Math.min(28,gw/4),y=v=>T+(H-T-B)*(1-v);
  let s=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Win rate by tier">`;
  const lo=0.6;const yy=v=>T+(H-T-B)*(1-(Math.max(v,lo)-lo)/(1-lo));
  for(let i=0;i<=4;i++){const v=lo+(1-lo)*i/4;s+=`<line class="grid" x1="${L}" x2="${W-10}" y1="${yy(v)}" y2="${yy(v)}"/><text x="${L-6}" y="${yy(v)+4}" text-anchor="end">${fmt.pct(v,0)}</text>`}
  per.forEach((p,i)=>{const cx=L+gw*i+gw/2;[[p.u,'var(--us)',US],[p.o,'var(--agents)','All other agents'],[p.w,'var(--own)',OWN]].forEach(([a,c,n],j)=>{if(!a||!a.n)return;const x=cx+(j-1.5)*bw+2;s+=`<rect x="${x}" y="${yy(a.win)}" width="${bw-4}" height="${H-B-yy(a.win)}" fill="${c}" rx="2" data-tip="<b>${esc(nice(n))} · ${p.t}</b><br>Win rate ${fmt.pct(a.win)}<br>${fmt.int(a.n)} accounts"/>`});
    s+=`<text x="${cx}" y="${H-B+18}" text-anchor="middle">${p.t}</text><text x="${cx}" y="${H-B+32}" text-anchor="middle" class="v">${fmt.int(p.u.n)} ours</text>`});
  $('#tier-chart').innerHTML=s+'</svg><p class="note">Axis starts at 60%.</p>';bindTips($('#tier-chart'));
  $('#tier-tbl tbody').innerHTML=per.map(p=>`<tr><td>${p.t}</td><td class="num">${fmt.int(p.u.n)}</td><td class="num">${fmt.pct(p.u.win)}</td><td class="num">${fmt.pct(p.u.avgPct,1)}</td><td class="num">${fmt.pct(p.o.avgPct,1)}</td><td class="num">${p.w?fmt.pct(p.w.avgPct,1):'–'}</td><td class="num">${fmt.usd(p.u.rM)}</td></tr>`).join('');
}

/* ---------- accounts ---------- */
const A=D.acct.map(r=>({id:r[0],addr:r[1],cls:r[2],grid:r[3],prior:r[4],notice:r[5],fin:r[6],cut:r[7],path:r[8],status:r[9],dt:r[10],oth:r[11],cases:r[12],nov:r[13]}));
A.forEach(a=>{a.pct=a.notice>0&&a.cut!=null?a.cut/a.notice:null;a.out=a.path=='Open'?'Open':a.cut>0?'Reduced':'No change';a.vs25=a.prior>0&&a.fin!=null?a.fin/a.prior-1:null;a.q=(a.id+' '+a.addr).toUpperCase()});
const GR=Object.fromEntries(D.grids.map(g=>[g[0],g]));
function renderBig(){
  const big=[...A].filter(a=>a.cut>0).sort((a,b)=>b.cut-a.cut).slice(0,15);
  $('#big-tbl tbody').innerHTML=big.map(a=>`<tr><td class="mono">${esc(a.id)}</td><td class="l">${esc(a.addr)}</td><td class="num">${fmt.usd(a.notice)}</td><td class="num">${fmt.usd(a.fin)}</td><td class="num">${fmt.usd(a.cut)}</td><td class="num">${fmt.pct(a.pct,1)}</td><td class="l">${pill(a.path)}</td></tr>`).join('');
  const nr=A.filter(a=>a.out=='No change').sort((a,b)=>b.notice-a.notice);
  $('#nr-sub').textContent=`${fmt.int(nr.length)} of our closed accounts ended with no cut. The last two columns show how other agents did in the same neighborhood.`;
  $('#nr-tbl tbody').innerHTML=nr.map(a=>{const g=GR[a.grid];return `<tr><td class="mono">${esc(a.id)}</td><td class="l">${esc(a.addr)}</td><td class="num">${fmt.usd(a.notice)}</td><td class="l">${pill(a.path,a.status)}</td><td class="mono">${esc(a.grid||'')}</td><td class="num">${g&&g[5]?fmt.pct(g[6]):'–'}</td><td class="num">${g&&g[5]?fmt.pct(g[7],1):'–'}</td></tr>`}).join('');
}
function pill(p,title){const c={Informal:'inf',ARB:'arb','No-show':'bad','Failure to appear':'bad',Withdrawn:'warn',Dismissed:'bad',Open:'warn'}[p]||'';return `<span class="pill ${c}"${title?` title="${esc(title)}"`:''}>${esc(p)}</span>`}
const as={q:'',out:'all',path:'all',sh:'all',sort:'cut',dir:'desc',page:0};
seg('#a-out','out',[['all','All'],['Reduced','Reduced'],['No change','No change'],['Open','Open']],as,()=>{as.page=0;renderAccts()});
seg('#a-path','path',[['all','All'],['Informal','Informal'],['ARB','ARB'],['No-show','No-show'],['Withdrawn','Withdrawn'],['Dismissed','Dismissed']],as,()=>{as.page=0;renderAccts()});
seg('#a-sh','sh',[['all','All'],['no','Only us'],['yes','Shared']],as,()=>{as.page=0;renderAccts()});
$('#a-q').oninput=e=>{as.q=e.target.value.trim().toUpperCase();as.page=0;renderAccts()};
const AC=[['id','Account',a=>`<span class="mono">${esc(a.id)}</span>`],['addr','Address',a=>esc(a.addr)],['notice','2026 notice',a=>fmt.full(a.notice)],['fin','Final',a=>fmt.full(a.fin)],['cut','Cut',a=>fmt.full(a.cut)],['pct','Cut %',a=>fmt.pct(a.pct,1)],['path','Path',a=>pill(a.path,a.status)],['dt','Finalized',a=>esc(a.dt||'')],['oth','Also on file',a=>esc(a.oth)]];
const PG=100;
function renderAccts(){
  let r=A.filter(a=>(!as.q||a.q.includes(as.q))&&(as.out=='all'||a.out==as.out)&&(as.path=='all'||a.path==as.path)&&(as.sh=='all'||(as.sh=='yes')==!!a.oth));
  const k=as.sort;r.sort((a,b)=>{const x=a[k],y=b[k];if(typeof x=='string'||typeof y=='string')return String(x??'').localeCompare(String(y??''));return (y??-1e15)-(x??-1e15)});if(as.dir=='asc')r.reverse();
  const pages=Math.max(1,Math.ceil(r.length/PG));as.page=Math.min(as.page,pages-1);
  $('#a-tbl thead').innerHTML='<tr>'+AC.map(([c,l])=>`<th><button type="button" data-k="${c}"${as.sort==c?` data-dir="${as.dir}"`:''}>${l}</button></th>`).join('')+'</tr>';
  $('#a-tbl tbody').innerHTML=r.slice(as.page*PG,as.page*PG+PG).map(a=>'<tr>'+AC.map(([c,,f])=>`<td class="${['addr','path','oth','dt'].includes(c)?'l':c=='id'?'':'num'}${c=='vs25'&&a.vs25<0?' pos':''}">${f(a)}</td>`).join('')+'</tr>').join('')||'<tr><td colspan="11">No accounts match.</td></tr>';
  $('#a-tbl').querySelectorAll('th button').forEach(b=>b.onclick=()=>{const c=b.dataset.k;if(as.sort==c)as.dir=as.dir=='desc'?'asc':'desc';else{as.sort=c;as.dir=['id','addr','path','oth'].includes(c)?'asc':'desc'}renderAccts()});
  const tot=r.reduce((s,a)=>s+(a.out=='Reduced'?a.cut:0),0);
  $('#a-pager').innerHTML=`<span>${fmt.int(r.length)} accounts · ${fmt.usd(tot)} cut</span><button type="button" class="btn" id="a-prev"${as.page?'':' disabled'}>Previous</button><span>Page ${as.page+1} of ${pages}</span><button type="button" class="btn" id="a-next"${as.page<pages-1?'':' disabled'}>Next</button>`;
  $('#a-prev').onclick=()=>{as.page--;renderAccts()};$('#a-next').onclick=()=>{as.page++;renderAccts()};
}

/* ---------- checks ---------- */
function renderChecks(){const c=D.checks;
  $('#chk-flow').innerHTML=c.flow.map(([l,v,s])=>`<div class="step"><span class="eyebrow">${l}</span><span class="v">${v}</span><span class="s">${s}</span></div>`).join('');
  $('#chk-list').innerHTML=c.list.map(x=>`<li>${x}</li>`).join('');
  $('#sh-h').textContent=c.sharedTitle;$('#sh-note').textContent=c.sharedNote;
  $('#sh-tbl tbody').innerHTML=Object.entries(c.sharedWith).map(([n,v])=>`<tr><td>${esc(nice(n))}</td><td class="num">${fmt.int(v)}</td></tr>`).join('')+`<tr class="agg"><td>All our properties with another agent on file</td><td class="num">${fmt.int(c.oursShared)}</td></tr>`;
}
function renderAll(){renderKPIs();renderExplorer();renderJourney();renderPath();renderTiers()}
renderAll();renderMatched();renderGrids();renderBig();renderAccts();renderChecks();
