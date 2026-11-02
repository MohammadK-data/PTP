"""Summarise the certified → supplement diff (written by the Denton ETL) for the profile page.
Streams every *_changed / *_added / *_removed CSV once; memory stays bounded per column.
Old -> new value pairs are shown exactly as the files hold them (no zero stripping, nothing hidden).
usage: cdiff.py DIFF_DIR NEW_INFO_CSV LIVE_DATA_JSON OUT_JSON"""
import sys, csv, json, os, re, random, statistics
csv.field_size_limit(1 << 30)
diff, new_info, live, out = sys.argv[1:5]
# column types of the supplement tables, as the page labels them (decides which columns get numeric up/down stats)
S = json.load(open(live))['sets']
TYPES = {k.split('-', 1)[1]: {c['name']: c['type'] for c in v['columns']} for k, v in S.items() if k.startswith('t26s3-') and not k.endswith('CHANGES')}
NUM = re.compile(r'^[+-]?\d*\.?\d+$')
summary = {r['tbl']: r for r in csv.DictReader(open(os.path.join(diff, '_summary.csv')))}


def nv(v):
    return float(v) if v and NUM.match(v) else None


def keyof(row, keys):
    return tuple(row[k].lstrip('0') for k in keys)


res = {'tables': {}, 'reasons': []}
prop_change = {}      # APPRAISAL_INFO: prop_id -> net appraised value change
info_props = set()
for tbl, sm in summary.items():
    keys = [k for k in sm['key_cols'].split(',')] if sm['key_cols'] != '(whole row)' else []
    t = {'summary': {k: (int(sm[k]) if sm[k].isdigit() else sm[k]) for k in ('old_rows', 'new_rows', 'added', 'removed', 'modified', 'unchanged', 'key_cols')}, 'cols': []}
    # properties touched, and properties whose rows were reissued (removed and added again)
    pa, pr = set(), set()
    for kind, s in (('added', pa), ('removed', pr)):
        p = os.path.join(diff, f'{tbl}_{kind}.csv')
        if os.path.exists(p) and 'prop_id' in keys:
            for row in csv.DictReader(open(p, newline='', encoding='utf-8')): s.add(row['prop_id'].lstrip('0'))
    cols = {}
    pc = set()
    p = os.path.join(diff, f'{tbl}_changed.csv')
    if os.path.exists(p):
        for row in csv.DictReader(open(p, newline='', encoding='utf-8')):
            n = row['column_name']; o, w = row['old_value'], row['new_value']
            if 'prop_id' in row: pc.add(row['prop_id'].lstrip('0'))
            c = cols.get(n)
            if c is None:
                c = cols[n] = {'n': 0, 'up': 0, 'down': 0, 'net': 0.0, 'res': [], 'seen': 0, 'filled': 0, 'cleared': 0, 'tr': {}, 'pruned': False}
            c['n'] += 1
            if not o: c['filled'] += 1
            elif not w: c['cleared'] += 1
            a, b = nv(o), nv(w)
            if re.search(r'(_yr|year)$', n): a = b = None  # years: show as transitions
            if a is not None and b is not None:
                d = b - a
                c['up' if d > 0 else 'down'] += d != 0
                c['net'] += d; c['seen'] += 1
                if len(c['res']) < 20000: c['res'].append(d)
                else:
                    j = random.randrange(c['seen'])
                    if j < 20000: c['res'][j] = d
            if tbl == 'APPRAISAL_INFO' and n == 'appraised_val' and a is not None and b is not None:
                prop_change[row['prop_id'].lstrip('0')] = prop_change.get(row['prop_id'].lstrip('0'), 0) + (b - a)
            k = (o, w)
            c['tr'][k] = c['tr'].get(k, 0) + 1
            if len(c['tr']) > 4000:
                c['pruned'] = True; c['tr'] = dict(sorted(c['tr'].items(), key=lambda kv: -kv[1])[:2000])
    if tbl == 'APPRAISAL_INFO': info_props = pa | pc
    t['props'] = {'added': len(pa - pr), 'removed': len(pr - pa), 'reissued': len(pa & pr), 'changed': len(pc)} if 'prop_id' in keys else None
    for n, c in sorted(cols.items(), key=lambda kv: -kv[1]['n']):
        typ = TYPES.get(tbl, {}).get(n, 'Text')
        e = {'name': n, 'n': c['n'], 'type': typ, 'filled': c['filled'], 'cleared': c['cleared']}
        if typ in ('Integer', 'Decimal', 'Percent') and c['seen'] and not re.search(r'(_yr|year)$', n):
            nz = sorted(x for x in c['res'] if x)
            e.update(up=c['up'], down=c['down'], net=round(c['net'], 4), med=statistics.median(nz) if nz else 0)
        top = sorted(c['tr'].items(), key=lambda kv: -kv[1])
        if top and top[0][1] > 1:
            e['top'] = [[o, w, x] for (o, w), x in top[:4] if x > 1]
        e['pairs'] = len(c['tr']) if not c['pruned'] else None
        t['cols'].append(e)
    res['tables'][tbl] = t
    print(tbl, t['summary']['modified'], len(cols), flush=True)

# why properties were corrected: supplement code and reason on the new export, for the touched properties
reasons = {}
with open(new_info, newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        pid = row['prop_id'].lstrip('0')
        if pid not in info_props: continue
        r = reasons.setdefault((row['sup_cd'], row['sup_desc']), {'props': set(), 'net': 0.0, 'up': 0, 'down': 0})
        if pid in r['props']: continue
        r['props'].add(pid)
        d = prop_change.get(pid)
        if d: r['net'] += d; r['up' if d > 0 else 'down'] += 1
res['reasons'] = sorted(({'cd': cd, 'desc': desc, 'props': len(r['props']), 'net': r['net'], 'up': r['up'], 'down': r['down']}
                         for (cd, desc), r in reasons.items()), key=lambda x: -x['props'])
res['touched'] = len(info_props)
json.dump(res, open(out, 'w'))
print('reasons', len(res['reasons']), 'touched props', len(info_props))
