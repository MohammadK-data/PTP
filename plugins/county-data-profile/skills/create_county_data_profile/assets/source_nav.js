// Workspace: a sidebar of every table (grouped by the CAD download it comes from, with search and the team's review
// progress) beside the selected table, which gets a header and Columns / Sample rows / Charts / About tabs.
// Reads <script id="srcmap">. The original tabs stay in the DOM (hidden) and show(key) still drives the panels;
// show() calls navSync(key) and buildPanel() calls originEnhance(key, panel).
const SRCMAP = JSON.parse(document.getElementById('srcmap').textContent);
const WS = { ready: false, home: false, group: null, started: false, gopen: new Set(), q: '', open: new Set(), tab: 'sample', dec: {}, decReady: false };
const wsExt = url => (url.split('?')[0].match(/\.([a-z0-9]+)$/i) || [, 'link'])[1].toUpperCase();
const WS_SITE = SRCMAP.page.short || 'website';
const wsLinks = f => `<a href="${esc(f.url)}" target="_blank" rel="noopener">${esc(WS_SITE)} ↗</a>${f.drive ? `<a href="${esc(f.drive)}" target="_blank" rel="noopener">Our Drive ↗</a>` : ''}`;

// the table's name in the sidebar and breadcrumb: the source map's title, picked from the manifest when the map is built
function wsLabel(key) {
  const t = SRCMAP.tables[key];
  return (t && t.title) || SETS[key].label.replace(/^\d+ · /, '');
}
function wsFileOf(key) {
  const t = SRCMAP.tables[key];
  if (!t) return null;
  for (const g of SRCMAP.groups) for (const f of g.files) if (f.export === t.download) return { g, f };
  return null;
}
// the same file in the group's other years / downloads: the page's own year mapping
function wsTwins(key) {
  const g = groupOf[key], yr = g.years && g.years.find(y => y.datasets.includes(key));
  if (!yr) return [];
  const i = yr.datasets.indexOf(key);
  return g.years.filter(y => y !== yr && y.datasets[i]).map(y => ({ key: y.datasets[i], label: y.label }));
}
const wsFk = key => typeof rvFileKey === 'function' ? rvFileKey(key) : key;
const wsDone = key => WS.dec[wsFk(key)] || 0;

// one sidebar section per profiled download; single-table downloads of the same CAD group share a section
function wsSections() {
  if (WS.sections) return WS.sections;
  const out = [];
  SRCMAP.groups.forEach(g => g.files.filter(f => f.export).forEach(f => {
    const keys = GROUPS.flatMap(gr => gr.datasets).filter(k => SRCMAP.tables[k] && SRCMAP.tables[k].download === f.export);
    const last = out[out.length - 1];
    if (keys.length === 1 && last && last.g === g && last.single) { last.keys.push(...keys); last.files.push(f); return; }
    out.push({ id: 's' + out.length, g, files: [f], keys, single: keys.length === 1, title: keys.length === 1 ? g.name : f.name });
  }));
  return WS.sections = out;
}

function wsItem(key) {
  const d = SETS[key], t = SRCMAP.tables[key], n = d.columns.length, done = wsDone(key);
  const state = !WS.decReady ? '' : done >= n ? 'full' : done ? 'part' : 'none';
  const sel = key === current && !WS.home && !WS.doc && WS.group === null;
  return `<button type="button" class="ws-item${sel ? ' on' : ''}" data-key="${key}" aria-current="${sel}">
    <span class="ws-raw">${esc(t.raw)}</span><span class="ws-lab">${esc(wsLabel(key))}</span>
    <span class="ws-prog ${state}" title="${WS.decReady ? `${done} of ${n} columns decided` : ''}">${WS.decReady ? `${done}/${n}` : n}</span></button>`;
}

function wsRenderSearch() {
  const q = WS.q.toLowerCase(), tables = [], cols = [];
  wsSections().forEach(s => s.keys.forEach(k => {
    const t = SRCMAP.tables[k], d = SETS[k];
    if ((wsLabel(k) + ' ' + t.raw + ' ' + d.about).toLowerCase().includes(q)) tables.push(k);
    d.columns.forEach(c => { if (c.name.toLowerCase().includes(q) || (c.desc || '').toLowerCase().includes(q)) cols.push([k, c]); });
  }));
  const dl = k => esc(wsFileOf(k).f.name);
  return `<div class="ws-sub">Tables (${tables.length})</div>${tables.slice(0, 25).map(wsItem).join('') || '<p class="ws-empty">No tables match.</p>'}
    <div class="ws-sub">Columns (${cols.length}${cols.length > 80 ? ', first 80' : ''})</div>${cols.slice(0, 80).map(([k, c]) =>
      `<button type="button" class="ws-col" data-key="${k}" data-col="${esc(c.name)}"><code>${esc(c.name)}</code><span>${esc(wsLabel(k))} · ${dl(k)}</span></button>`).join('') || '<p class="ws-empty">No columns match.</p>'}`;
}

// the sidebar: the CAD website's page as a tree. Section › group › file; a file with tables expands into its tables
function wsFileTables(f) {
  return f.export ? GROUPS.flatMap(gr => gr.datasets).filter(k => SRCMAP.tables[k] && SRCMAP.tables[k].download === f.export) : [];
}
const WS_ICON = {
  data: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6"/><path d="M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"/></svg>',
  docs: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 7a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/></svg>',
};
function wsFileRow(g, gi, f, fi) {
  const on = WS.doc && WS.doc[0] === gi && WS.doc[1] === fi;
  const all = wsFileTables(f);
  if (!all.length) return `<li><button type="button" class="ws-docbtn${on ? ' on' : ''}" data-g="${gi}" data-f="${fi}">
    <span class="ws-ext">${wsExt(f.url)}</span><span class="ws-dname">${esc(f.name)}</span></button></li>`;
  const open = WS.open.has(f.export);
  const done = all.reduce((a, k) => a + Math.min(wsDone(k), SETS[k].columns.length), 0), cols = all.reduce((a, k) => a + SETS[k].columns.length, 0);
  let body = '', lastTab = null;
  if (open) all.forEach(k => {
    const tab = groupOf[k].label.replace(/^JSON · /, '');
    if (all.length > 6 && tab !== lastTab) body += `<div class="ws-sub">${esc(tab)}</div>`;
    lastTab = tab;
    body += wsItem(k);
  });
  return `<li class="ws-file${open ? ' open' : ''}"><button type="button" class="ws-docbtn ws-hastables${on ? ' on' : ''}" data-g="${gi}" data-f="${fi}" aria-expanded="${open}">
    <span class="ws-ext">${wsExt(f.url)}</span><span class="ws-dname">${esc(f.name)}<small>${all.length} ${all.length === 1 ? 'table' : 'tables'}${WS.decReady ? ` · ${Math.round(100 * done / (cols || 1))}% decided` : ''}</small></span><i aria-hidden="true">▸</i></button>
    ${open ? `<div class="ws-tables">${body}</div>` : ''}</li>`;
}
function wsRenderTree() {
  return SRCMAP.groups.map((g, gi) => {
    const open = WS.gopen.has(gi);
    const nTables = g.files.reduce((a, f) => a + wsFileTables(f).length, 0);
    const meta = `${g.files.length} ${g.files.length === 1 ? 'file' : 'files'}${nTables ? ` · ${nTables} ${nTables === 1 ? 'table' : 'tables'}` : ''}`;
    return `<div class="ws-doc ws-grp${open ? ' open' : ''}${nTables ? ' data' : ''}${WS.group === gi ? ' on' : ''}" data-gi="${gi}">
      <button type="button" class="ws-grph" data-gi="${gi}" aria-expanded="${open}"><span class="ws-gicon">${nTables ? WS_ICON.data : WS_ICON.docs}</span>
        <span class="ws-gtext"><b>${esc(g.name)}</b><small>${meta}</small></span><i aria-hidden="true">▸</i></button>
      ${open ? `<ul>${g.files.map((f, fi) => wsFileRow(g, gi, f, fi)).join('')}</ul>${g.drive ? `<a class="ws-gdrive" href="${esc(g.drive)}" target="_blank" rel="noopener">Drive folder ↗</a>` : ''}` : ''}</div>`;
  }).join('');
}

// home: nothing selected, so the right side stays empty
function wsRenderHomeView() {
  document.getElementById('ws-bc').innerHTML = '';
  document.getElementById('ws-head').innerHTML = '<p class="ws-hint-home">Choose a category on the left to begin.</p>';
}

// a category (website group) opened in the sidebar: its summary, with a card per file
function wsFileCard(g, gi, f, fi) {
  const t = wsFileTables(f);
  if (!t.length) return `<button type="button" class="ws-hcard doc" data-g="${gi}" data-f="${fi}"><small><span class="ws-ext">${wsExt(f.url)}</span></small><b>${esc(f.name)}</b>
    <span class="ws-hmeta">${f.status === 'layout' ? 'Layout document' : 'Document'} · ${f.drive ? 'in our Drive' : 'not in our Drive'}</span></button>`;
  const cols = t.reduce((a, k) => a + SETS[k].columns.length, 0), done = t.reduce((a, k) => a + Math.min(wsDone(k), SETS[k].columns.length), 0);
  const pct = Math.round(100 * done / (cols || 1));
  return `<button type="button" class="ws-hcard" data-g="${gi}" data-f="${fi}"><small><span class="ws-ext">${wsExt(f.url)}</span></small><b>${esc(f.name)}</b>
    <span class="ws-hmeta">${t.length} ${t.length === 1 ? 'table' : 'tables'}${WS.decReady ? ` · ${pct}% decided` : ''}</span>
    ${WS.decReady ? `<span class="ws-track"><i style="width:${pct}%"></i></span>` : ''}</button>`;
}
function wsRenderGroupView() {
  const gi = WS.group, g = SRCMAP.groups[gi];
  wsRenderBc([['Home', 'home'], [g.name, 'group', gi]]);
  const keys = g.files.flatMap(wsFileTables), cols = keys.reduce((a, k) => a + SETS[k].columns.length, 0);
  const done = keys.reduce((a, k) => a + Math.min(wsDone(k), SETS[k].columns.length), 0);
  const data = g.files.map((f, fi) => ({ f, fi })).filter(x => wsFileTables(x.f).length), docs = g.files.map((f, fi) => ({ f, fi })).filter(x => !wsFileTables(x.f).length);
  document.getElementById('ws-head').innerHTML = `<div class="ws-home">
    <div class="ws-title"><span class="ws-gicon${keys.length ? ' data' : ''}">${keys.length ? WS_ICON.data : WS_ICON.docs}</span><h2>${esc(g.name)}</h2></div>
    ${g.desc ? `<p class="ws-about">${esc(g.desc)}</p>` : ''}
    <div class="ws-chips"><span>${g.files.length} ${g.files.length === 1 ? 'file' : 'files'}</span>
      ${keys.length ? `<span>${keys.length} ${keys.length === 1 ? 'table' : 'tables'}</span>` : ''}
      ${keys.length && WS.decReady ? `<span class="${done >= cols ? 'ok' : ''}">${Math.round(100 * done / (cols || 1))}% of columns decided</span>` : ''}
      ${g.drive ? `<a class="ws-chip-link" href="${esc(g.drive)}" target="_blank" rel="noopener">Drive folder ↗</a>` : ''}</div>
    ${data.length ? `<section class="ws-dsec"><h3>Data files</h3><div class="ws-hcards">${data.map(x => wsFileCard(g, gi, x.f, x.fi)).join('')}</div></section>` : ''}
    ${docs.length ? `<section class="ws-dsec"><h3>${data.length ? 'Documents' : 'Files'}</h3><div class="ws-hcards">${docs.map(x => wsFileCard(g, gi, x.f, x.fi)).join('')}</div></section>` : ''}</div>`;
}
function wsOpenGroup(gi, scroll = true) {
  WS.group = +gi; WS.home = false; WS.doc = null;
  WS.gopen.add(+gi);
  document.getElementById('panels').hidden = true;
  wsRenderSide(); wsRenderGroupView();
  if (scroll) document.getElementById('ws-main').scrollIntoView({ block: 'start' });
}

function wsHome(scroll = true) {
  WS.home = true; WS.doc = null; WS.group = null;
  document.getElementById('panels').hidden = true;
  wsRenderSide(); wsRenderHomeView();
  if (scroll) document.getElementById('ws-main').scrollIntoView({ block: 'start' });
}
function wsGoGroup(gi) {
  const side = document.getElementById('ws-side'), list = document.getElementById('ws-list');
  WS.q = ''; document.getElementById('ws-q').value = '';
  wsOpenGroup(gi, false);
  side.classList.add('show');
  if (document.getElementById('ws').classList.contains('collapsed')) document.getElementById('ws-collapse').click();
  const target = list.querySelector(`.ws-grp[data-gi="${gi}"]`);
  if (target) { list.scrollTop = target.offsetTop - 4; target.classList.add('ws-flash-doc'); setTimeout(() => target.classList.remove('ws-flash-doc'), 1600); }
  if (innerWidth <= 900) side.scrollIntoView({ block: 'start' });
}

// breadcrumb: each part is [label, action, ...args]. Every part opens a menu of what is inside it (the categories,
// a category's files, a file's tables, a table's tabs), so you can jump sideways at any level.
const WS_TABS = [['sample', 'Data preview'], ['cols', 'Columns'], ['about', 'About']];
function wsBcKids(part) {
  const [, a, x, y] = part;
  if (a === 'home') return SRCMAP.groups.map((g, gi) => [g.name, 'group', gi]);
  if (a === 'group') return SRCMAP.groups[x].files.map((f, fi) => [f.name, 'doc', x, fi]);
  if (a === 'doc') return wsFileTables(SRCMAP.groups[x].files[y]).map(k => [`${wsLabel(k)} · ${SRCMAP.tables[k].raw}`, 'table', k]);
  if (a === 'table') { const p = built[x]; return WS_TABS.filter(([id]) => p && p.querySelector(`[data-wst="${id}"]`)).map(([id, l]) => [l, 'tab', id]); }
  return [];
}
function wsRenderBc(parts) {
  WS.bc = parts.filter(x => x[0]);
  const same = (a, b) => b && a[1] === b[1] && String(a.slice(2)) === String(b.slice(2));
  document.getElementById('ws-bc').innerHTML = WS.bc.map((x, i, all) => {
    const last = i === all.length - 1, kids = wsBcKids(x);
    if (!kids.length) return last ? `<span class="ws-bc-here" aria-current="page">${esc(x[0])}</span>`
      : `<button type="button" class="ws-bc-link" data-i="${i}">${esc(x[0])}</button>`;
    const menu = (last ? '' : `<button type="button" class="ws-bcm ws-bcm-open" role="menuitem" data-i="${i}">Open ${esc(x[0])}</button><div class="ws-bcm-sep"></div>`) +
      kids.map((k, j) => `<button type="button" class="ws-bcm${same(k, all[i + 1]) ? ' on' : ''}" role="menuitem" data-i="${i}" data-k="${j}">${esc(k[0])}</button>`).join('');
    return `<span class="ws-bcw"><button type="button" class="ws-bc-item${last ? ' here' : ''}" data-i="${i}" aria-haspopup="menu" aria-expanded="false"${last ? ' aria-current="page"' : ''}>${esc(x[0])}<i class="ws-caret" aria-hidden="true">▾</i></button>
      <div class="ws-bcmenu" role="menu" hidden>${menu}</div></span>`;
  }).join('<i class="ws-bc-sep" aria-hidden="true">›</i>');
}
function wsBcClose() {
  document.querySelectorAll('.ws-bcmenu:not([hidden])').forEach(m => { m.hidden = true; m.previousElementSibling.setAttribute('aria-expanded', 'false'); });
}
function wsBcGo(a, args) {
  if (a === 'table') return show(args[0]);
  if (a === 'doc') return wsOpenDoc(args[0], args[1]);
  if (a === 'group') return wsGoGroup(args[0]);
  if (a === 'tab') return wsTab(built[current], args[0]);
  return wsHome();
}

// a document opened from the Documents list: what it is, where to open it, what's inside, and our tables from it
function wsRenderDoc() {
  const [gi, fi] = WS.doc, g = SRCMAP.groups[gi], f = g.files[fi];
  const file = decodeURIComponent(f.url.split('/').pop());
  const tables = f.export ? GROUPS.flatMap(gr => gr.datasets).filter(k => SRCMAP.tables[k] && SRCMAP.tables[k].download === f.export) : [];
  const status = f.export ? `${tables.length} ${tables.length === 1 ? 'table' : 'tables'} on this page` : f.status === 'layout' ? 'Layout document for the exports' : 'A document; no tables on this page';
  document.getElementById('panels').hidden = true;
  wsRenderBc([['Home', 'home'], [g.name, 'group', gi], [f.name, 'doc', gi, fi]]);
  document.getElementById('ws-head').innerHTML = `    <div class="ws-title"><span class="ws-ext ws-ext-lg">${wsExt(f.url)}</span><h2>${esc(f.name)}</h2></div>
    ${g.desc ? `<p class="ws-about">${esc(g.desc)}</p>` : ''}
    <div class="ws-docact"><a class="ws-btn primary" href="${esc(f.url)}" target="_blank" rel="noopener">Open on ${esc(WS_SITE)} ↗</a>
      ${f.drive ? `<a class="ws-btn" href="${esc(f.drive)}" target="_blank" rel="noopener">Open our Drive copy ↗</a>` : '<span class="ws-nodrive">Not in our Drive</span>'}</div>
    <dl class="ws-dfacts"><div><dt>File</dt><dd><code>${esc(file)}</code></dd></div><div><dt>On this page</dt><dd>${esc(status)}</dd></div>
      ${g.drive ? `<div><dt>Drive folder</dt><dd><a href="${esc(g.drive)}" target="_blank" rel="noopener">${esc(g.name)} ↗</a></dd></div>` : ''}</dl>
    ${f.note ? `<p class="ws-dnote">${esc(f.note)}</p>` : ''}
    ${tables.length ? `<section class="ws-dsec"><h3>Tables from this file</h3><div class="ws-dtables">${tables.map(wsItem).join('')}</div></section>` : ''}
    ${f.contents ? `<section class="ws-dsec"><h3>Inside the .zip (${f.contents.length} files)</h3><ul class="ws-dlist">${f.contents.map(c => `<li><code>${esc(c)}</code></li>`).join('')}</ul></section>` : ''}
    <section class="ws-dsec"><h3>Other files in ${esc(g.name)}</h3><div class="ws-dsib">${g.files.map((x, i) => i === fi ? '' :
      `<button type="button" class="ws-docbtn" data-g="${gi}" data-f="${i}"><span class="ws-ext">${wsExt(x.url)}</span><span class="ws-dname">${esc(x.name)}</span></button>`).join('')}</div></section>`;
}
function wsOpenDoc(gi, fi) {
  WS.doc = [+gi, +fi]; WS.home = false; WS.group = null;
  WS.gopen.add(+gi);
  const f = SRCMAP.groups[gi].files[fi];
  if (f.export) WS.open.add(f.export);
  wsRenderSide(); wsRenderDoc();
  document.getElementById('ws-main').scrollIntoView({ block: 'start' });
}

function wsRenderSide() {
  const list = document.getElementById('ws-list');
  list.innerHTML = WS.q.length >= 2 ? wsRenderSearch() : wsRenderTree();
}

function wsRenderHead() {
  if (WS.home) return wsRenderHomeView();
  if (WS.group !== null) return wsRenderGroupView();
  if (WS.doc) return wsRenderDoc();
  const el = document.getElementById('ws-head'), key = current;
  if (!key || !SRCMAP.tables[key]) { el.innerHTML = ''; return; }
  const d = SETS[key], t = SRCMAP.tables[key], at = wsFileOf(key), n = d.columns.length, done = wsDone(key);
  const twins = wsTwins(key);
  const gi = SRCMAP.groups.indexOf(at.g), fi = at.g.files.indexOf(at.f);
  const tabName = { sample: 'Data preview', cols: 'Columns', about: 'About' }[WS.tab] || '';
  wsRenderBc([['Home', 'home'], [at.g.name, 'group', gi], [at.f.name, 'doc', gi, fi], [`${wsLabel(key)} · ${t.raw}`, 'table', key], [tabName, 'tab', WS.tab]]);
  el.innerHTML = `<div class="ws-title"><h2>${esc(wsLabel(key))}</h2><code>${esc(t.raw)}</code><span class="ws-dl">${wsLinks(at.f)}</span></div>
    ${d.about ? `<p class="ws-about">${esc(d.about)}</p>` : ''}
    <div class="ws-chips"><span>${fmt(d.rows)} rows</span><span>${n} columns</span>
      ${WS.decReady ? `<span class="${done >= n ? 'ok' : ''}">${done} of ${n} decided</span>` : ''}
      ${twins.length ? `<span class="ws-twins">Same file in: ${twins.map(x => `<button type="button" class="ws-twin" data-key="${x.key}">${esc(x.label)}</button>`).join('')}</span>` : ''}</div>`;
}

function wsTab(p, tab) {
  const changed = WS.tab !== tab;
  WS.tab = tab;
  if (changed && !WS.doc && p === built[current]) wsRenderHead();
  p.querySelectorAll('.ws-tab').forEach(b => b.setAttribute('aria-selected', b.dataset.t === tab));
  p.querySelectorAll('[data-wst]').forEach(el => el.hidden = el.dataset.wst !== tab);
}

// one card per column: the column-table row (name, type, fill, decision, notes) beside that column's chart card
const WS_CELL = { '#': 'idx', 'Column': 'name', 'Field': 'name', 'Data type': 'type', 'Most common value': 'top', 'Example value': 'top' };
function wsMergeColumns(key, p) {
  const sec = p.querySelector('[data-wst="cols"]'), charts = p.querySelector('[data-wst="charts"]');
  const table = sec && sec.querySelector('table');
  if (!table) return;
  table.classList.add('ws-ctable');
  sec.querySelector('.tablebox').classList.add('ws-cbox');
  const h = sec.querySelector('.sechead h2'); if (h) h.textContent = 'Columns';
  const labels = [...table.querySelectorAll('thead th')].map(th => th.textContent.trim().replace('Auto-detected on load', 'Loaded as'));
  const cards = charts ? [...charts.querySelectorAll('.card')] : [];
  [...table.querySelectorAll('tbody.crow > tr')].forEach((tr, i) => {
    [...tr.children].forEach((td, j) => { td.dataset.label = labels[j] || ''; td.classList.add('ws-' + (WS_CELL[labels[j]] || 'stat')); });
    const a = tr.querySelector('td.name a'); if (a) a.removeAttribute('href');
    if (cards[i]) { const td = document.createElement('td'); td.className = 'ws-chart'; td.append(cards[i]); tr.append(td); }
  });
  if (charts) charts.remove();
}

// Data preview: the sample rows always shown (no collapsible), each column name linking to its column card
function wsPreview(key, p) {
  const det = p.querySelector('details.sample');
  if (!det) return;
  const box = document.createElement('div');
  box.className = 'ws-sample';
  const what = det.querySelector('summary span');
  box.innerHTML = `<p class="ws-cap">${what ? esc(what.textContent) : ''}. Click a column name to see its details, decision and notes.</p>`;
  [...det.children].filter(el => el.tagName !== 'SUMMARY').forEach(el => box.append(el));
  det.replaceWith(box);
  const cols = SETS[key].columns;
  box.querySelectorAll('thead th').forEach((th, i) => {
    const c = cols[i - 1];
    if (!c) return;
    th.removeAttribute('title');
    th.innerHTML = `<button type="button" class="ws-th" data-col="${esc(c.name)}"${c.desc ? ` data-tip="${esc(c.desc)}"` : ''}>${esc(c.name)}</button>`;
  });
  box.addEventListener('click', e => { const b = e.target.closest('.ws-th'); if (b) wsGoColumn(key, b.dataset.col); });
}

// panel: put its parts under tabs
function originEnhance(key, p) {
  const t = SRCMAP.tables[key];
  if (!t || p.dataset.wsTabs) return;
  p.dataset.wsTabs = '1';
  const kids = [...p.children], notes = p.querySelector('.note');
  kids.forEach(el => {
    if (el.classList.contains('about')) el.remove();   // shown in the header
    else if (el.classList.contains('facts') || el.classList.contains('note')) el.dataset.wst = 'about';
    else if (el.querySelector('.crow')) el.dataset.wst = 'cols';
    else if (el.querySelector('details.sample, .ws-sample')) el.dataset.wst = 'sample';
    else if (el.querySelector('.cards')) el.dataset.wst = 'charts';
  });
  wsMergeColumns(key, p);
  wsPreview(key, p);
  const nNotes = notes ? notes.querySelectorAll('li').length : 0;
  const bar = document.createElement('div');
  bar.className = 'ws-tabs'; bar.setAttribute('role', 'tablist');
  bar.innerHTML = [['sample', 'Data preview'], ['cols', 'Columns'], ['about', nNotes ? `About · ${nNotes} ${nNotes === 1 ? 'note' : 'notes'}` : 'About']]
    .filter(([id]) => p.querySelector(`[data-wst="${id}"]`))
    .map(([id, label]) => `<button type="button" class="ws-tab" role="tab" data-t="${id}">${label}</button>`).join('');
  p.prepend(bar);
  bar.addEventListener('click', e => { const b = e.target.closest('.ws-tab'); if (b) wsTab(p, b.dataset.t); });
  p.querySelectorAll('.fact.file > span').forEach(s => { if (s.textContent === 'Source file') s.textContent = `Raw file in the ${WS_SITE} download`; });
  wsTab(p, p.querySelector(`[data-wst="${WS.tab}"]`) ? WS.tab : 'sample');
}

function wsGoColumn(key, col) {
  show(key);
  const p = built[key];
  wsTab(p, 'cols');
  const tr = [...p.querySelectorAll('.crow tr')].find(r => r.dataset.col === col || r.dataset.name === col.toLowerCase());
  if (tr) { tr.hidden = false; tr.scrollIntoView({ block: 'center' }); tr.classList.add('ws-flash'); setTimeout(() => tr.classList.remove('ws-flash'), 2200); }
}

async function wsWatchDecisions() {
  if (!window.claude || typeof window.claude.use !== 'function') return;
  const db = await window.claude.use('db');
  if (!db) return;
  db.collection('decisions').onSnapshot(s => {
    const m = {};
    s.docs.forEach(x => { const v = x.data(); if (v && v.file && ['need', 'maybe', 'drop'].includes(v.status)) m[v.file] = (m[v.file] || 0) + 1; });
    WS.dec = m; WS.decReady = true;
    wsRenderSide(); wsRenderHead();
  }, () => {});
}

function wsInit() {
  if (WS.ready) return;
  WS.ready = true;
  const side = document.getElementById('ws-side');
  side.addEventListener('click', e => {
    const it = e.target.closest('.ws-item');
    if (it) { show(it.dataset.key); document.getElementById('ws-main').scrollIntoView({ block: 'start' }); side.classList.remove('show'); return; }
    const col = e.target.closest('.ws-col');
    if (col) { wsGoColumn(col.dataset.key, col.dataset.col); side.classList.remove('show'); return; }
    const gh = e.target.closest('.ws-grph');
    if (gh) {   // opening a category shows its summary; closing it only folds the list
      const gi = +gh.dataset.gi;
      if (WS.gopen.has(gi)) { WS.gopen.delete(gi); wsRenderSide(); } else { wsOpenGroup(gi); side.classList.remove('show'); }
      return;
    }
    const d = e.target.closest('.ws-docbtn');
    if (!d) return;
    const f = SRCMAP.groups[d.dataset.g].files[d.dataset.f];
    if (f.export && WS.open.has(f.export)) { WS.open.delete(f.export); wsRenderSide(); return; }   // collapse its tables
    wsOpenDoc(d.dataset.g, d.dataset.f);   // open the document (a file with tables also expands them)
    if (!f.export) side.classList.remove('show');
  });
  const q = document.getElementById('ws-q');
  q.addEventListener('input', () => { WS.q = q.value.trim(); wsRenderSide(); });
  document.getElementById('ws-toggle').addEventListener('click', () => side.classList.toggle('show'));
  // collapse the sidebar to a slim strip on wide screens; remembered per viewer in this browser
  const ws = document.getElementById('ws'), col = document.getElementById('ws-collapse');
  const setCollapsed = c => {
    ws.classList.toggle('collapsed', c);
    col.setAttribute('aria-expanded', String(!c));
    col.setAttribute('aria-label', c ? 'Show sidebar' : 'Hide sidebar'); col.title = col.getAttribute('aria-label');
    try { localStorage.setItem('ws-side-collapsed', c ? '1' : '') } catch (e) {}
  };
  col.addEventListener('click', () => setCollapsed(!ws.classList.contains('collapsed')));
  try { if (localStorage.getItem('ws-side-collapsed')) setCollapsed(true) } catch (e) {}
  document.addEventListener('click', e => {   // the "About this page" popover closes on any click outside it
    const info = document.querySelector('.ws-info[open]');
    if (info && !info.contains(e.target)) info.open = false;
  });
  const bcEl = document.getElementById('ws-bc');
  bcEl.addEventListener('click', e => {
    const item = e.target.closest('.ws-bc-item');
    if (item) {   // open this level's menu (and close any other)
      const menu = item.nextElementSibling, was = !menu.hidden;
      wsBcClose();
      if (!was) { menu.hidden = false; item.setAttribute('aria-expanded', 'true'); (menu.querySelector('.on') || menu.querySelector('.ws-bcm')).focus(); }
      return;
    }
    const m = e.target.closest('.ws-bcm, .ws-bc-link');
    if (!m) return;
    const part = WS.bc[m.dataset.i], go = m.dataset.k !== undefined ? wsBcKids(part)[m.dataset.k] : part;
    wsBcClose();
    wsBcGo(go[1], go.slice(2));
  });
  bcEl.addEventListener('keydown', e => {
    if (e.key === 'Escape') { const open = bcEl.querySelector('.ws-bcmenu:not([hidden])'); if (open) { wsBcClose(); open.previousElementSibling.focus(); } }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      const items = [...(e.target.closest('.ws-bcmenu') || { querySelectorAll: () => [] }).querySelectorAll('.ws-bcm')];
      const i = items.indexOf(e.target);
      if (i >= 0) { e.preventDefault(); items[(i + (e.key === 'ArrowDown' ? 1 : items.length - 1)) % items.length].focus(); }
    }
  });
  document.addEventListener('click', e => { if (!e.target.closest('.ws-bcw')) wsBcClose(); });
  document.getElementById('ws-head').addEventListener('click', e => {
    const b = e.target.closest('.ws-twin, .ws-item');
    if (b) { show(b.dataset.key); return; }
    const d = e.target.closest('.ws-docbtn, .ws-hcard');
    if (d) { wsOpenDoc(d.dataset.g, d.dataset.f); return; }
    const hg = e.target.closest('.ws-hgrp');
    if (hg) wsGoGroup(hg.dataset.gi);
  });
  document.getElementById('ws-home').addEventListener('click', () => { wsHome(); side.classList.remove('show'); });
  addEventListener('hashchange', () => {   // an old #key.column link points at that column's card
    const h = decodeURIComponent(location.hash.slice(1)), el = document.getElementById(h);
    if (el && el.classList.contains('card')) { wsTab(built[current], 'cols'); (el.closest('tr') || el).scrollIntoView({ block: 'start' }); }
  });
  wsWatchDecisions();
}

// called from show(key)
function navSync(key) {
  wsInit();
  if (!WS.started) {   // a fresh visit with no #table link starts on the home view, nothing selected
    WS.started = true;
    if (!location.hash) return wsHome(false);
  }
  WS.doc = null; WS.home = false; WS.group = null;
  document.getElementById('panels').hidden = false;
  const t = SRCMAP.tables[key], at = wsFileOf(key);
  if (t) WS.open.add(t.download);
  if (at) WS.gopen.add(SRCMAP.groups.indexOf(at.g));
  wsRenderSide(); wsRenderHead();
  const p = built[key];
  if (p && p.dataset.wsTabs) wsTab(p, p.querySelector(`[data-wst="${WS.tab}"]`) ? WS.tab : 'sample');
  const on = document.querySelector('.ws-item.on'), box = document.getElementById('ws-list');
  if (on && !WS.q && (on.offsetTop < box.scrollTop || on.offsetTop > box.scrollTop + box.clientHeight - 40)) box.scrollTop = on.offsetTop - 80;
}
