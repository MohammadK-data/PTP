// Team review: each column gets a Need / Maybe / Drop decision and a thread of notes, kept in the
// artifact's shared db. A file's decisions are shared by every year (or snapshot) tab of that file.
const REVIEW = { db: null, user: null, me: null, canWrite: true, fk: null, unsub: [], decisions: {}, notes: {}, pending: new Set() };
const RV_STATUS = [['need', 'Need'], ['maybe', 'Maybe'], ['drop', 'Drop']];
const RV_LABEL = { need: 'Need', maybe: 'Maybe', drop: 'Drop' };

const rvSeg = s => String(s).replace(/[^A-Za-z0-9_.:@-]/g, c => '+' + c.codePointAt(0).toString(16) + '+');
function rvDocId(fk, col) {
  const id = rvSeg(fk) + '~' + rvSeg(col);
  if (id.length <= 190) return id;
  let h = 0; for (const ch of id) h = (h * 31 + ch.codePointAt(0)) >>> 0;
  return id.slice(0, 170) + '~' + h.toString(36);
}
function rvFileKey(key) {
  const g = groupOf[key], yr = g.years && g.years.find(y => y.datasets.includes(key));
  return yr ? g.id + '.' + yr.datasets.indexOf(key) : key;
}
function rvTable(key) {
  const g = groupOf[key], d = SETS[key], yr = g.years && g.years.find(y => y.datasets.includes(key));
  return yr && yr.datasets.length === 1 ? g.label : g.label + ' · ' + d.label;
}
const rvWhen = t => t ? new Date(t).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }) : '';
const rvPanels = fk => Object.values(built).filter(p => p.dataset.fk === fk);

function rvMsg(fk, text) { rvPanels(fk).forEach(p => p.querySelectorAll('.rv-msg').forEach(m => m.textContent = text)); }

function reviewEnhance(key, p) {
  if (!REVIEW.db || p.dataset.fk) return;
  const tbody = p.querySelector('.crow'), d = SETS[key];
  if (!tbody || !d.columns || !d.columns.length) return;
  const fk = rvFileKey(key), table = rvTable(key);
  p.dataset.fk = fk; p.dataset.key = key;
  const headRow = tbody.parentElement.querySelector('thead tr');
  headRow.children[1].insertAdjacentHTML('afterend', '<th>Decision</th><th>Notes</th>');
  const span = headRow.children.length;
  const rows = [...tbody.children];
  rows.forEach((tr, i) => {
    const c = d.columns[i];
    tr.dataset.col = c.name; tr.dataset.status = 'open';
    tr.children[1].insertAdjacentHTML('afterend', `<td class="rv-dec"><span class="seg" role="group" aria-label="Decision for ${esc(c.name)}">${RV_STATUS.map(([v, l]) =>
      `<button type="button" class="rv-b ${v}" data-v="${v}" aria-pressed="false">${l}</button>`).join('')}</span></td>
      <td class="rv-notes"><button type="button" class="rv-nb" aria-expanded="false" aria-label="Notes for ${esc(c.name)}"><span class="rv-cnt"></span><span class="rv-last">Add note</span></button></td>`);
  });

  // status filter beside the name and type filters, and a running tally under the heading
  const q = p.querySelector('#q-' + CSS.escape(key)), t = p.querySelector('#t-' + CSS.escape(key));
  const sel = document.createElement('select');
  sel.setAttribute('aria-label', 'Filter by decision');
  sel.innerHTML = '<option value="">All decisions</option><option value="need">Need</option><option value="maybe">Maybe</option><option value="drop">Drop</option><option value="open">Not decided</option>';
  t.after(sel);
  const sum = document.createElement('div');
  sum.className = 'rv-sum'; sum.setAttribute('aria-live', 'polite');
  q.closest('.sechead').after(sum);
  const cards = [...p.querySelectorAll('.card')];
  p._rvApply = () => {
    const s = q.value.trim().toLowerCase(), ty = t.value, st = sel.value;
    rows.forEach((tr, i) => {
      const hide = !(tr.dataset.name.includes(s) && (!ty || tr.dataset.type === ty) && (!st || tr.dataset.status === st));
      tr.hidden = hide; if (cards[i]) cards[i].hidden = hide;
      const n = tr.nextElementSibling; if (n && n.classList.contains('nrow')) n.hidden = hide;
    });
  };
  q.addEventListener('input', p._rvApply); t.addEventListener('change', p._rvApply); sel.addEventListener('change', p._rvApply);

  tbody.addEventListener('click', e => {
    const b = e.target.closest('.rv-b');
    if (b) return rvDecide(fk, table, b.closest('tr').dataset.col, b.dataset.v);
    const nb = e.target.closest('.rv-nb');
    if (nb) return rvToggleNotes(nb.closest('tr'), fk, span);
    const del = e.target.closest('.rv-del');
    if (del) return rvDeleteNote(del);
  });
  tbody.addEventListener('submit', e => {
    e.preventDefault();
    const tr = e.target.closest('tr').previousElementSibling;
    rvAddNote(fk, table, tr.dataset.col, e.target);
  });
  tbody.addEventListener('keydown', e => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && e.target.matches('.rv-add textarea')) e.target.form.requestSubmit();
  });
  rvRender(fk);
}

function rvToggleNotes(tr, fk, span) {
  const nb = tr.querySelector('.rv-nb'), next = tr.nextElementSibling;
  if (next && next.classList.contains('nrow')) {
    next.remove(); nb.setAttribute('aria-expanded', 'false'); return;
  }
  const n = document.createElement('tr');
  n.className = 'nrow';
  n.innerHTML = `<td colspan="${span}"><div class="rv-thread"><div class="rv-list"></div></div></td>`;
  tr.after(n);
  nb.setAttribute('aria-expanded', 'true');
  rvRender(fk);
  const ta = n.querySelector('textarea'); if (ta) ta.focus();
}

function rvThread(n, col, list, who) {
  const box = n.querySelector('.rv-thread');
  const listEl = box.querySelector('.rv-list');
  listEl.replaceChildren();
  if (!list.length) {
    const e = document.createElement('div'); e.className = 'rv-empty'; e.textContent = 'No notes on this column yet.'; listEl.append(e);
  }
  list.forEach(x => {
    const item = document.createElement('div'); item.className = 'rv-n';
    const meta = document.createElement('div'); meta.className = 'rv-meta';
    const b = document.createElement('b'); b.textContent = who(x.by);
    const s = document.createElement('span'); s.textContent = rvWhen(x.at);
    meta.append(b, s);
    if (REVIEW.canWrite && x.by && x.by === REVIEW.me) {
      const del = document.createElement('button'); del.type = 'button'; del.className = 'rv-del'; del.dataset.id = x.id; del.textContent = 'Delete';
      meta.append(del);
    }
    const txt = document.createElement('div'); txt.className = 'rv-text'; txt.textContent = x.text;
    item.append(meta, txt); listEl.append(item);
  });
  let form = box.querySelector('.rv-add');
  if (REVIEW.canWrite && !form) {
    form = document.createElement('form'); form.className = 'rv-add';
    form.innerHTML = `<textarea maxlength="2000" placeholder="Add a note on ${esc(col)} for the team" aria-label="New note on ${esc(col)}"></textarea><div><button type="submit">Add note</button><small>⌘/Ctrl + Enter to add</small></div>`;
    box.append(form);
  } else if (!REVIEW.canWrite && form) form.remove();
}

async function rvRender(fk) {
  const panels = rvPanels(fk);
  if (!panels.length) return;
  const dec = REVIEW.decisions[fk] || {}, notes = REVIEW.notes[fk] || {};
  const ids = new Set();
  Object.values(dec).forEach(x => x.by && ids.add(x.by));
  Object.values(notes).forEach(l => l.forEach(x => x.by && ids.add(x.by)));
  const ps = REVIEW.user && ids.size ? await REVIEW.user.profiles([...ids]) : {};
  const who = id => (ps[id] && ps[id].name) || (id && id === REVIEW.me ? 'You' : 'Someone');
  panels.forEach(p => {
    const counts = { need: 0, maybe: 0, drop: 0, open: 0 };
    let noted = 0;
    p.querySelectorAll('.crow tr[data-col]').forEach(tr => {
      const col = tr.dataset.col, d = dec[col], st = d && RV_LABEL[d.status] ? d.status : '';
      counts[st || 'open']++;
      tr.dataset.status = st || 'open';
      tr.querySelectorAll('.rv-b').forEach(b => { b.setAttribute('aria-pressed', String(b.dataset.v === st)); b.disabled = !REVIEW.canWrite; });
      tr.querySelector('.rv-dec').title = st ? `${RV_LABEL[st]}, set by ${who(d.by)} · ${rvWhen(d.at)}` : '';
      const list = notes[col] || [];
      if (list.length) noted++;
      const nb = tr.querySelector('.rv-nb');
      nb.classList.toggle('has', list.length > 0);
      nb.querySelector('.rv-cnt').textContent = list.length || '';
      nb.querySelector('.rv-last').textContent = list.length ? list[list.length - 1].text : REVIEW.canWrite ? 'Add note' : '—';
      nb.title = list.length ? `${list.length} note${list.length > 1 ? 's' : ''} · latest by ${who(list[list.length - 1].by)}` : '';
      const n = tr.nextElementSibling;
      if (n && n.classList.contains('nrow')) rvThread(n, col, list, who);
      const card = document.getElementById(p.dataset.key + '.' + col);
      if (card) {
        const h = card.querySelector('h3 > span');
        let chip = h.querySelector('.rv-chip');
        if (st) {
          if (!chip) { chip = document.createElement('span'); h.append(chip); }
          chip.className = 'rv-chip ' + st; chip.textContent = RV_LABEL[st];
        } else if (chip) chip.remove();
      }
    });
    const sum = p.querySelector('.rv-sum');
    if (sum) {
      const msg = sum.querySelector('.rv-msg') ? sum.querySelector('.rv-msg').textContent : '';
      sum.innerHTML = `<span><i class="need"></i>Need <b>${counts.need}</b></span><span><i class="maybe"></i>Maybe <b>${counts.maybe}</b></span>
        <span><i class="drop"></i>Drop <b>${counts.drop}</b></span><span><i></i>Not decided <b>${counts.open}</b></span>
        <span>Columns with notes <b>${noted}</b></span>${REVIEW.canWrite ? '' : '<span>View only</span>'}<span class="rv-msg"></span>`;
      sum.querySelector('.rv-msg').textContent = msg;
    }
    if (p._rvApply) p._rvApply();
  });
}

function rvFail(fk, e) {
  if (e && (e.code === 'invalid_argument' || e.code === 'not_granted')) {
    REVIEW.canWrite = false;
    rvMsg(fk, 'You can read the team’s notes but your access does not allow changes.');
  } else {
    rvMsg(fk, `Couldn’t save (${e && e.code || 'error'}). Try again in a moment.`);
  }
  rvRender(fk);
}

async function rvDecide(fk, table, col, v) {
  if (!REVIEW.canWrite) return;
  const id = rvDocId(fk, col);
  if (REVIEW.pending.has(id)) return;
  REVIEW.pending.add(id);
  const cur = (REVIEW.decisions[fk] || {})[col];
  const ref = REVIEW.db.collection('decisions').doc(id);
  try {
    if (cur && cur.status === v) await ref.delete();
    else await ref.set({ file: fk, table, col, status: v, by: REVIEW.me, at: Date.now() });
    rvMsg(fk, '');
  } catch (e) { rvFail(fk, e); }
  REVIEW.pending.delete(id);
}

async function rvAddNote(fk, table, col, form) {
  const ta = form.querySelector('textarea'), btn = form.querySelector('button');
  const text = ta.value.trim();
  if (!text || btn.disabled) return;
  btn.disabled = true;
  try {
    await REVIEW.db.collection('notes').add({ file: fk, table, col, text: text.slice(0, 2000), by: REVIEW.me, at: Date.now() });
    ta.value = ''; rvMsg(fk, '');
  } catch (e) {
    if (e && e.code === 'quota_exceeded') rvMsg(fk, 'The notes store is full. Delete old notes before adding more.');
    else rvFail(fk, e);
  }
  btn.disabled = false;
}

async function rvDeleteNote(btn) {
  if (!btn.classList.contains('sure')) {
    btn.classList.add('sure'); btn.textContent = 'Click again to delete';
    setTimeout(() => { btn.classList.remove('sure'); btn.textContent = 'Delete'; }, 3000);
    return;
  }
  btn.disabled = true;
  try { await REVIEW.db.collection('notes').doc(btn.dataset.id).delete(); }
  catch (e) { rvFail(REVIEW.fk, e); }
}

function reviewShow(key) {
  if (!REVIEW.db) return;
  const fk = rvFileKey(key);
  if (REVIEW.fk === fk) return;
  REVIEW.unsub.forEach(u => u()); REVIEW.unsub = []; REVIEW.fk = fk;
  if (!SETS[key].columns || !SETS[key].columns.length) return;
  let gotD = false, gotN = false;
  const timer = setTimeout(() => rvMsg(fk, 'Team notes can’t be reached yet; what you see may be out of date.'), 10000);
  const settle = () => { if (gotD && gotN) { clearTimeout(timer); rvMsg(fk, ''); } };
  const onErr = e => { clearTimeout(timer); rvMsg(fk, e.code === 'revoked' ? '' : `Team notes couldn’t load (${e.code}).`); };
  REVIEW.unsub.push(REVIEW.db.collection('decisions').where('file', '==', fk).onSnapshot(s => {
    const m = {};
    s.docs.forEach(x => { const v = x.data(); if (v && typeof v.col === 'string') m[v.col] = v; });
    REVIEW.decisions[fk] = m;
    if (!s.metadata.fromCache) { gotD = true; settle(); }
    rvRender(fk);
  }, onErr));
  REVIEW.unsub.push(REVIEW.db.collection('notes').where('file', '==', fk).onSnapshot(s => {
    const m = {};
    s.docs.forEach(x => {
      const v = x.data();
      if (v && typeof v.col === 'string' && typeof v.text === 'string') (m[v.col] = m[v.col] || []).push({ ...v, id: x.id });
    });
    Object.values(m).forEach(l => l.sort((a, b) => (a.at || 0) - (b.at || 0)));
    REVIEW.notes[fk] = m;
    if (!s.metadata.fromCache) { gotN = true; settle(); }
    rvRender(fk);
  }, onErr));
}

(async () => {
  const off = () => { const el = document.getElementById('rv-off'); if (el) el.hidden = false; };
  if (!window.claude || typeof window.claude.use !== 'function') return off();
  const [db, user] = await Promise.all([window.claude.use('db'), window.claude.use('user')]);
  if (!db) return off();
  REVIEW.db = db; REVIEW.user = user;
  if (user) {
    REVIEW.me = await user.id();
    if (await user.can('data.write') === false) REVIEW.canWrite = false;
  }
  Object.entries(built).forEach(([k, p]) => reviewEnhance(k, p));
  if (current) reviewShow(current);
})();
