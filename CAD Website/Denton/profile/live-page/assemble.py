"""Rebuild the live Denton page (Protax JSON export + PACS export tables + correction changes) from raw values.

Takes the published page as the base (layout, labels, notes, descriptions, groups) and swaps in:
  - merged.json   Protax JSON tables from dprof.py + merge.py (raw values, 100 sample rows per table)
  - ../profile.json  PACS tables from the skill's profile_files.py (raw values, 100 sample rows per table)
  - changes.json  correction changes from cdiff.py (old -> new pairs as stored)
and patches the page script so nothing is hidden and charts include zeros and every year.

usage: assemble.py BASE_PAGE_HTML LIVE_DATA_JSON OUT_HTML
"""
import json, os, re, sys

base, live, out = sys.argv[1:4]
HERE = os.path.dirname(os.path.abspath(__file__))
h = open(base).read()
# the saved artifact carries the viewer's outer document; keep only the page itself
if h.startswith('<!doctype html><html><head><meta charset=utf8>'):
    h = h[h.index('<title>'):]
    h = h[:h.rindex('</body></html>')].rstrip() + '\n'

D = json.load(open(live)); S = D['sets']
M = json.load(open(os.path.join(HERE, 'merged.json')))['tables']
P = json.load(open(os.path.join(HERE, '..', 'profile.json')))
man = json.load(open(os.path.join(HERE, '..', 'manifest.json')))
C = json.load(open(os.path.join(HERE, 'changes.json')))['tables']


def with_desc(new_cols, old_cols):
    desc = {c['name']: c['desc'] for c in old_cols if c.get('desc')}
    for c in new_cols:
        c.pop('masked', None)
        if c['name'] in desc: c['desc'] = desc[c['name']]
    return new_cols


# Protax JSON tables: live 'json:owners-agents' <-> merged 'property.owners.agents'
mt = {('property' if n == 'property' else n[len('property.'):].replace('.', '-')): n for n in M}
pacs = {os.path.basename(d['path']).rsplit('.', 1)[0]: k for k, d in man['datasets'].items()}
for k, s in S.items():
    if k.startswith('d-'):
        t = M[mt[s['table'][5:]]]
        assert t['rows'] == s['rows'], k
        s['columns'] = with_desc(t['columns'], s['columns'])
        s['sample'] = t['sample']
    elif k.startswith('t26') and not k.endswith('CHANGES'):
        p = P[pacs[s['file'].rsplit('.', 1)[0]]]
        assert p['rows'] == s['rows'] and [c['name'] for c in p['columns']] == [c['name'] for c in s['columns']], k
        s['columns'] = with_desc(p['columns'], s['columns'])
        s['loaderLabel'] = 'Auto-detected on load'
        s['sample'] = {'rows': p['sample']['rows']}
        if 'changes' in s:
            x = C[s['table'][5:]]
            s['changes']['cols'] = x['cols']; s['changes']['summary'] = x['summary']; s['changes']['props'] = x['props']

FOOT = ("Generated November 2, 2026. Values are shown exactly as the files hold them: nothing is trimmed, hidden or left out "
        "of the charts. The Protax JSON export was streamed in full; \"JSON type\" is the type values have in the file, its "
        "percentiles and histograms come from a random sample of up to 120,000 values per field scaled to the full count, "
        "distinct counts are exact below 3,000 values and estimated (HyperLogLog) above, and for those fields the most common "
        "values are approximate. The PACS export tables were scanned in full with DuckDB; \"Auto-detected on load\" is the type "
        "DuckDB assigns when it reads the CSV. Sample rows are 100 random rows per table.")

SAMPLE_CSS = '''details.sample { min-width: 0 }
details.sample > summary { cursor: pointer; list-style: none; display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap }
details.sample > summary::-webkit-details-marker { display: none }
details.sample > summary h2::before { content: "\\25B8"; display: inline-block; width: 1.1em; color: var(--muted); transition: transform .15s }
details.sample[open] > summary h2::before { transform: rotate(90deg) }
details.sample > summary span { color: var(--muted); font-size: 12.5px }
details.sample > summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 4px }
details.sample .tablebox { max-height: 520px; overflow: auto; margin-top: 12px }
details.sample th { font: 600 11.5px var(--f-mono); letter-spacing: 0; text-transform: none; z-index: 1 }
details.sample td { font: 12px var(--f-mono); white-space: pre; max-width: 260px; overflow: hidden; text-overflow: ellipsis }
details.sample td.blank { color: var(--t-empty) }
'''

SAMPLE_JS = '''function sampleHTML(d) {
  const sm = d.sample;
  if (!sm || !sm.rows.length) return '';
  const what = `${fmt(sm.rows.length)} random rows of ${fmt(d.rows)}`;
  return `<section><details class="sample"><summary><h2>Sample rows</h2><span>${what}</span></summary>
    <div class="tablebox"><table><thead><tr><th>#</th>${d.columns.map(c => `<th title="${esc(c.desc || '')}">${esc(c.name)}</th>`).join('')}</tr></thead>
    <tbody>${sm.rows.map((r, i) => `<tr><td class="idx">${i + 1}</td>${r.map(v => v == null ? '<td class="blank">·</td>' : `<td title="${esc(v)}">${esc(v)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
  </details></section>`;
}

'''

PATCHES = [
    ('footer { color: var(--muted)', SAMPLE_CSS + 'footer { color: var(--muted)'),
    ('''  if (c.masked) {
    body += `<p class="empty">Values hidden: this field holds personal, contact or credential data. Only counts are shown.</p>`;
  } else if (c.type === 'Integer' ''', '''  if (c.type === 'Integer' '''),
    ("Distribution of non-zero values${", "Distribution of values${"),
    ('''      const notes = [];
      if (s.zeros) notes.push(`${fmt(s.zeros)} zeros (${fmtPct(pct(s.zeros, rows))})`);
''', '''      if (s.zeros) body += `<div class="foot">${fmt(s.zeros)} values are zero (${fmtPct(pct(s.zeros, rows))}), included in the chart.</div>`;
      const notes = [];
'''),
    ('''    const bins = c.hist.bins.filter(b => b[0] != null);''', '''    const bins = c.hist.bins;'''),
    ('''    const dn = [];
    if (s.future) dn.push(`${fmt(s.future)} dates after 2026`);
    if (s.unparsed) dn.push(`${fmt(s.unparsed)} values that are not dates`);
    if (dn.length) body += `<div class="foot">Not charted: ${dn.join(', ')}.</div>`;''',
     '''    if (s.future) body += `<div class="foot">${fmt(s.future)} dates are after 2026, included in the chart.</div>`;
    if (s.unparsed) body += `<div class="foot">Not charted: ${fmt(s.unparsed)} values that are not dates.</div>`;'''),
    ('''${c.masked ? '<span class="hid">hidden</span>' : c.example != null ? esc(c.example) : '<span class="hid">blank</span>'}''',
     '''${c.example != null ? esc(c.example) : '<span class="hid">blank</span>'}'''),
    ('''${c.masked ? '<span class="hid">hidden</span>' : topv ? esc(topv[0])''', '''${topv ? esc(topv[0])'''),
    ('''      }).join('')}</tbody></table></div>
  </section>` + (single ? '' : `<section>''', '''      }).join('')}</tbody></table></div>
  </section>` + sampleHTML(d) + (single ? '' : `<section>'''),
    ('function notesHTML(d, prev) {', SAMPLE_JS + 'function notesHTML(d, prev) {'),
    # correction changes: show stored values as they are (no zero collapsing); long ones keep the full value on hover
    ('''  v = /^0+$/.test(v) ? '0' : String(v);
  return esc(v.length > 34 ? v.slice(0, 33) + '…' : v);''', '''  v = String(v);
  return v.length > 34 ? `<span title="${esc(v)}">${esc(v.slice(0, 33))}…</span>` : esc(v);'''),
    ('''  if (c.masked) return '<span class="hid">values hidden</span>';
''', ''),
]
for a, b in PATCHES:
    assert h.count(a) == 1, (h.count(a), a[:80])
    h = h.replace(a, b)
foot = re.search(r"document.getElementById\('foot'\).textContent = (.*?);\n", h, re.S)
h = h[:foot.start(1)] + json.dumps(FOOT) + h[foot.end(1):]
assert 'masked' not in h.split('<script id="data"')[1].split('</script>', 1)[1], 'masked still referenced in the script'

tag = '<script id="data" type="application/json">'
a = h.index(tag) + len(tag); b = h.index('</script>', a)
h = h[:a] + json.dumps(D, ensure_ascii=False, default=str).replace('</', '<\\/') + h[b:]
open(out, 'w').write(h)
print(f'wrote {out}: {len(h) / 1e6:.2f} MB, {len(S)} sets, '
      f'{sum(1 for s in S.values() if s.get("sample"))} with sample rows')
