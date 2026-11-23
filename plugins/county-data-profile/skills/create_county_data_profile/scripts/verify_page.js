// Paste into the browser tool's javascript_exec on the locally served page.
// Opens every view (and its Sample rows table); reports views whose tooltip count is off (a column without data-tip),
// whose sample table doesn't match the data, or that overflow sideways.
const bad = [];
for (const k of Object.keys(SETS)) {
  show(k);
  const p = document.getElementById('panel-' + k);
  const tips = p.querySelectorAll('[data-tip]').length;
  const expected = SETS[k].columns.length * (SETS[k].rows < 2 ? 1 : 2);   // table + card per column
  if (tips !== expected) bad.push([k, 'tooltips', tips, expected]);
  const sm = SETS[k].sample, det = p.querySelector('details.sample');
  if (sm && sm.rows.length) {
    if (!det) bad.push([k, 'sample missing']);
    else { det.open = true; const n = det.querySelectorAll('tbody tr').length; if (n !== sm.rows.length) bad.push([k, 'sample rows', n, sm.rows.length]); }
  } else if (!SETS[k].placeholder && SETS[k].rows > 1 && !SETS[k].api) bad.push([k, 'no sample in data']);
  if (document.documentElement.scrollWidth > innerWidth) bad.push([k, 'horizontal overflow']);
}
show(SOURCES[0].start);
({ views: Object.keys(SETS).length, bad });
