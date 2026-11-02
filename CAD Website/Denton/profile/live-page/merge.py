"""Merge worker pickles from dprof.py into the Tarrant-profile column JSON shape.
Values are reported exactly as in the file: nothing masked, zeros and every year charted.
Each table gets `sample`: 100 rows drawn at random across the workers' reservoirs.
usage: merge.py PARTS_DIR OUT_JSON"""
import sys, glob, pickle, json, math, re, random

HLL_P = 11; HLL_M = 1 << HLL_P
PCTS = [1, 5, 25, 50, 75, 95, 99]


def hll_est(reg):
    z = sum(2.0 ** -r for r in reg)
    e = 0.7213 / (1 + 1.079 / HLL_M) * HLL_M * HLL_M / z
    zeros = reg.count(0)
    if e <= 2.5 * HLL_M and zeros:
        e = HLL_M * math.log(HLL_M / zeros)
    return int(round(e))


def merge_col(a, b):
    if a is None: return b
    a['nonnull'] += b['nonnull']
    for k in ('jt', 'cnt', 'years'):
        for x, n in b[k].items(): a[k][x] = a[k].get(x, 0) + n
    a['pruned'] = a['pruned'] or b['pruned']
    a['hll'] = bytearray(max(x, y) for x, y in zip(a['hll'], b['hll']))
    for k, f in (('minlen', min), ('maxlen', max), ('min', min), ('max', max), ('dmin', min), ('dmax', max)):
        if b[k] is not None: a[k] = b[k] if a[k] is None else f(a[k], b[k])
    for k in ('n', 'sum', 'zeros', 'dates', 'digits'): a[k] += b[k]
    a['samples'].extend(b['samples'])
    return a


def weighted(samples):
    pts = []
    for res, seen in samples:
        if len(res): w = seen / len(res); pts.extend((v, w) for v in res)
    pts.sort()
    return pts


def wpct(pts, qs):
    tot = sum(w for _, w in pts); out = []; acc = 0; i = 0
    for q in qs:
        target = tot * q / 100
        while i < len(pts) - 1 and acc + pts[i][1] < target:
            acc += pts[i][1]; i += 1
        out.append(pts[i][0])
    return out


def classify(name, c, rows):
    jt = c['jt']; nn = c['nonnull']
    if not nn: return 'Empty'
    main = max(jt, key=jt.get)
    distinct_vals = set(c['cnt'])
    if main == 'bool': return 'Flag'
    if main == 'array': return 'Array'
    if main in ('int', 'float'):
        if main == 'int' and not c['pruned'] and distinct_vals <= {'0', '1'}: return 'Flag'
        if main == 'int' and re.search(r'(ID|Id|Cd|Code|Num)$', name.split('.')[-1]): return 'Code (numeric ID)'
        if main == 'float' or 'float' in jt:
            return 'Percent' if re.search(r'pct|percent', name, re.I) else 'Decimal'
        return 'Integer'
    if c['dates'] >= 0.95 * nn: return 'Date'
    if c['digits'] >= 0.98 * nn: return 'Code (numeric text)'
    if not c['pruned'] and len(distinct_vals) <= 2 and (c['maxlen'] or 0) <= 1: return 'Flag'
    return 'Text'


def build(name, c, rows):
    t = classify(name, c, rows)
    nulls = rows - c['nonnull']
    distinct = len(c['cnt']) if not c['pruned'] else max(hll_est(c['hll']), len(c['cnt']))
    jt = '/'.join(k for k in ('int', 'float', 'string', 'bool', 'array') if k in c['jt']) or 'null'
    top = sorted(c['cnt'].items(), key=lambda kv: -kv[1])[:12]
    top = [[k, n] for k, n in top]
    if nulls: top.append([None, nulls]); top.sort(key=lambda kv: -kv[1]); top = top[:12]
    col = {'name': name, 'loader': jt, 'type': t, 'nonnull': c['nonnull'], 'nulls': nulls, 'distinct': distinct,
           'minlen': c['minlen'], 'maxlen': c['maxlen'], 'top': top}
    if t in ('Integer', 'Decimal', 'Percent') and c['n']:
        pts = weighted(c['samples'])
        p = wpct(pts, PCTS)
        stats = {'min': c['min'], 'max': c['max'], 'mean': c['sum'] / c['n'], 'p': p, 'zeros': c['zeros']}
        if c['n'] < c['nonnull']: stats['unparsed'] = c['nonnull'] - c['n']
        col['stats'] = stats
        vals = {float(k) for k in c['cnt']} if not c['pruned'] else None
        if pts and vals is not None and len(vals) <= 30:
            bins = sorted((float(k), n) for k, n in c['cnt'].items())
            col['hist'] = {'kind': 'discrete', 'bins': [[k, n] for k, n in bins]}
        elif pts:
            lo, hi = wpct(pts, [1, 99])
            if hi > lo:
                w = (hi - lo) / 20; tot = sum(x for _, x in pts); scale = c['n'] / tot
                bins = [0.0] * 20; out = 0.0
                for v, x in pts:
                    if v < lo or v > hi: out += x; continue
                    bins[min(int((v - lo) / w), 19)] += x
                col['hist'] = {'kind': 'range', 'lo': lo, 'w': w,
                               'bins': [[lo + i * w, round(b * scale)] for i, b in enumerate(bins)], 'outside': round(out * scale)}
    elif t == 'Date':
        future = sum(n for y, n in c['years'].items() if y > 2026)
        col['stats'] = {'min': c['dmin'], 'max': c['dmax'], 'future': future}
        if c['nonnull'] > c['dates']: col['stats']['unparsed'] = c['nonnull'] - c['dates']
        col['hist'] = {'kind': 'year', 'bins': [[y, n] for y, n in sorted(c['years'].items())]}
    return col


def show(v):
    # the same text the value counters use, so sample cells match the top values
    if v is None: return None
    t = type(v)
    if t is list: return json.dumps(v, separators=(',', ':'))
    if t is bool: return 'true' if v else 'false'
    if t is float: return repr(v)
    return str(v)


def pick_sample(parts, names, n=100):
    # weighted reservoir merge: each worker's rows stand for rows/len(sample) rows of the file
    rng = random.Random(42); keyed = []
    for rows, sample in parts:
        if not sample: continue
        w = rows / len(sample)
        keyed += [(rng.random() ** (1 / w), r) for r in sample]
    keyed.sort(key=lambda kr: -kr[0])
    return {'rows': [[show(r.get(c)) for c in names] for _, r in keyed[:n]]}


def main(parts, out):
    meta = {'records': 0, 'years': {}, 'bytes': 0}; tables = {}
    for f in sorted(glob.glob(parts + '/part*.pkl')):
        m, T = pickle.load(open(f, 'rb'))
        meta['records'] += m['records']; meta['bytes'] += m['bytes']
        for y, n in m['years'].items(): meta['years'][y] = meta['years'].get(y, 0) + n
        for tn, t in T.items():
            a = tables.setdefault(tn, {'rows': 0, 'parents': 0, 'maxper': 0, 'cols': {}, 'samples': []})
            a['samples'].append((t['rows'], t.get('sample', [])))
            a['rows'] += t['rows']; a['parents'] += t['parents']; a['maxper'] = max(a['maxper'], t['maxper'])
            for cn, c in t['cols'].items():
                c['samples'] = [(c.pop('res'), c.pop('seen'))]
                a['cols'][cn] = merge_col(a['cols'].get(cn), c)
        del T
    res = {'meta': meta, 'tables': {}}
    for tn, t in tables.items():
        cols = [build(cn, c, t['rows']) for cn, c in t['cols'].items()]
        res['tables'][tn] = {'rows': t['rows'], 'parents': t['parents'], 'maxper': t['maxper'], 'columns': cols,
                             'sample': pick_sample(t['samples'], [x['name'] for x in cols])}
    json.dump(res, open(out, 'w'), default=str)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
