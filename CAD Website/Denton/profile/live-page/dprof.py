"""Stream-profile the Denton protax JSON export (one top-level array of property records,
pretty-printed with each record starting at a line ' {'). Every nested list of objects
becomes its own table; nested dicts are flattened into dotted column names.
Memory is bounded per column: value counters are pruned, numeric values are reservoir-sampled.
Values are counted exactly as they are in the file. Each table also keeps SAMPLE random rows (reservoir).

usage: profile.py FILE OUTDIR WORKERS [YEAR]
"""
import sys, os, json, re, random, pickle, math
from array import array
from multiprocessing import Process

CAP, KEEP, RES, SAMPLE = 3000, 1500, 20000, 100
HLL_P = 11; HLL_M = 1 << HLL_P; MASK = (1 << 64) - 1
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}')


class Col:
    __slots__ = ('nonnull', 'jt', 'cnt', 'pruned', 'hll', 'minlen', 'maxlen', 'n', 'sum', 'min', 'max',
                 'zeros', 'res', 'seen', 'dmin', 'dmax', 'years', 'dates', 'digits')

    def __init__(self):
        self.nonnull = 0; self.jt = {}; self.cnt = {}; self.pruned = False
        self.hll = bytearray(HLL_M); self.minlen = None; self.maxlen = None
        self.n = 0; self.sum = 0.0; self.min = None; self.max = None; self.zeros = 0
        self.res = array('d'); self.seen = 0
        self.dmin = None; self.dmax = None; self.years = {}; self.dates = 0; self.digits = 0


def add(c, v):
    if v is None:
        return
    c.nonnull += 1
    t = type(v)
    if t is list:
        key = json.dumps(v, separators=(',', ':'))
        tn = 'array'
    elif t is bool:
        key = 'true' if v else 'false'; tn = 'bool'
    elif t is str:
        key = v; tn = 'string'
        if DATE_RE.match(v):
            c.dates += 1
            d = v[:10]
            if c.dmin is None or d < c.dmin: c.dmin = d
            if c.dmax is None or d > c.dmax: c.dmax = d
            y = int(v[:4]); c.years[y] = c.years.get(y, 0) + 1
        elif v.isdigit():
            c.digits += 1
    else:
        tn = 'int' if t is int else 'float'
        key = repr(v) if t is float else str(v)
        x = float(v)
        c.n += 1; c.sum += x
        if c.min is None or x < c.min: c.min = x
        if c.max is None or x > c.max: c.max = x
        if x == 0: c.zeros += 1
        c.seen += 1
        if len(c.res) < RES: c.res.append(x)
        else:
            j = random.randrange(c.seen)
            if j < RES: c.res[j] = x
    c.jt[tn] = c.jt.get(tn, 0) + 1
    L = len(key)
    if c.minlen is None or L < c.minlen: c.minlen = L
    if c.maxlen is None or L > c.maxlen: c.maxlen = L
    cnt = c.cnt
    cnt[key] = cnt.get(key, 0) + 1
    if len(cnt) > CAP:
        c.pruned = True
        c.cnt = dict(sorted(cnt.items(), key=lambda kv: -kv[1])[:KEEP])
    h = hash(key) & MASK
    i = h & (HLL_M - 1); w = h >> HLL_P
    r = (64 - HLL_P) - w.bit_length() + 1
    if r > c.hll[i]: c.hll[i] = r


class Table:
    def __init__(self):
        self.rows = 0; self.parents = 0; self.maxper = 0; self.cols = {}; self.sample = []


def run(path, start, end, out, year):
    random.seed(start)
    tables = {}; meta = {'records': 0, 'years': {}, 'bytes': 0}

    def tab(name):
        t = tables.get(name)
        if t is None: t = tables[name] = Table()
        return t

    def obj(o, tname):
        t = tab(tname); t.rows += 1
        row = {}
        flat(o, '', t, tname, row)
        if len(t.sample) < SAMPLE: t.sample.append(row)
        else:
            j = random.randrange(t.rows)
            if j < SAMPLE: t.sample[j] = row

    def flat(o, pre, t, tname, row):
        for k, v in o.items():
            name = pre + k
            if type(v) is dict:
                flat(v, name + '.', t, tname, row)
            elif type(v) is list and v and all(type(x) is dict for x in v):
                child = tname + '.' + name
                ct = tab(child); ct.parents += 1
                if len(v) > ct.maxper: ct.maxper = len(v)
                for x in v: obj(x, child)
            elif type(v) is list and not v:
                tab(tname + '.' + name)  # register the (possibly always empty) list
            else:
                c = t.cols.get(name)
                if c is None:
                    c = t.cols[name] = Col()
                add(c, v); row[name] = v

    with open(path, 'rb') as f:
        pos = max(start - 1, 0)
        f.seek(pos)
        if start:
            line = f.readline(); pos += len(line)  # finish the line that straddles start
        buf = None
        while True:
            line = f.readline()
            if not line: break
            if buf is None:
                if line.startswith(b' {'):
                    if pos >= end: break
                    buf = [line]
            elif line.startswith(b' }'):
                buf.append(line)
                rec = json.loads(b''.join(buf).rstrip().rstrip(b','))
                buf = None
                y = rec.get('pYear'); meta['years'][y] = meta['years'].get(y, 0) + 1
                if year is None or y == year:
                    meta['records'] += 1
                    obj(rec, 'property')
            else:
                buf.append(line)
            pos += len(line)
    meta['bytes'] = pos - start
    with open(out, 'wb') as g:
        plain = {n: {'rows': t.rows, 'parents': t.parents, 'maxper': t.maxper, 'sample': t.sample,
                     'cols': {k: {a: getattr(c, a) for a in Col.__slots__} for k, c in t.cols.items()}}
                 for n, t in tables.items()}
        pickle.dump((meta, plain), g, protocol=pickle.HIGHEST_PROTOCOL)



if __name__ == '__main__':
    path, outdir, W = sys.argv[1], sys.argv[2], int(sys.argv[3])
    year = int(sys.argv[4]) if len(sys.argv) > 4 else None
    size = os.path.getsize(path)
    bounds = [size * i // W for i in range(W + 1)]
    ps = [Process(target=run, args=(path, bounds[i], bounds[i + 1], f'{outdir}/part{i}.pkl', year)) for i in range(W)]
    for p in ps: p.start()
    for p in ps: p.join()
    print('done', [p.exitcode for p in ps])
