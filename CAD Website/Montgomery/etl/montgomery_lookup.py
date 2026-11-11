"""Look up one or more Montgomery properties in the Protax JSON export and show their notice values.

Source: Data/Montgomery-protaxExport-20260804.json (~21 GB).

An "account id" can be any of:
    pID       property ID                                e.g. 1001
    refID1    reference number                           e.g. M00001
    refID2    account number                             e.g. 462789
    geoID     geographic ID                              e.g. 8580-01-02832
pID and refID2 are both plain numbers, so a number can match two different properties (e.g. 1001 as a pID and
1001 as someone's refID2); every match is shown, with the ID type it matched on.

Usage (from the Montgomery folder):
    python3 etl/montgomery_lookup.py 1001
    python3 etl/montgomery_lookup.py 1001 M00002 462789 8580-01-02832
    python3 etl/montgomery_lookup.py --build-index      # one-time pass over the 21 GB file (a few minutes)

The index (output/protax_review/protax_index_20260804.csv) is shared with montgomery_values.py and is
built automatically on first use. With it, a lookup seeks straight to the record (under a second).

For each property it prints a summary and writes the full record to output/protax_review/pid_<pID>.json.

Notice values:
- Protested properties: the appeal's initial* values (the value before the protest). The appeal's notice*
  columns are 0 in Montgomery's export, so they are not used.
- Not protested: the current ownerValue values. They match the notice unless a correction changed the
  value after the notice was mailed.
- Appeals still open on 2026-08-04 (e.g. WH, EXP-NC, PROT-SCHD) have finalMarketValue 0.
"""

import argparse
import csv
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MONTGOMERY = os.path.dirname(HERE)
DEFAULT_SRC = os.path.join(MONTGOMERY, "Data", "Montgomery-protaxExport-20260804.json")
OUT_DIR = os.path.join(MONTGOMERY, "output", "protax_review")
INDEX = os.path.join(OUT_DIR, "protax_index_20260804.csv")
ID_KEYS = ("pID", "geoID", "refID1", "refID2")

RE_PID = re.compile(rb'^  "pID": (\d+),', re.M)
RE_IDS = {k: re.compile(rb'"%s": "([^"]*)"' % k.encode()) for k in ("geoID", "refID1", "refID2")}


def iter_raw(path, progress_every=50_000):
    """Yield (offset, raw_bytes) for each top-level record. Records start with b' {' and end with b' }'."""
    start, n = time.time(), 0
    with open(path, "rb") as f:
        offset, buf, rec_start = 0, None, 0
        for line in f:
            s = line.rstrip(b"\r\n")
            if buf is None:
                if s == b" {":
                    buf, rec_start = [line], offset
            elif s in (b" }", b" },"):
                buf.append(b" }")
                yield rec_start, b"".join(buf)
                buf = None
                n += 1
                if progress_every and n % progress_every == 0:
                    print(f"  {n:,} records, {time.time() - start:,.0f}s", file=sys.stderr, flush=True)
            else:
                buf.append(line)
            offset += len(line)


def ids_of(raw):
    out = {"pID": RE_PID.search(raw).group(1).decode()}
    for k, rx in RE_IDS.items():
        m = rx.search(raw)
        out[k] = m.group(1).decode() if m else ""
    return out


def build_index(src=DEFAULT_SRC):
    print(f"building {os.path.basename(INDEX)} from {os.path.basename(src)} (one-time scan of ~21 GB)...",
          file=sys.stderr, flush=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = f"{INDEX}.{os.getpid()}.tmp"      # own temp file, so two builds at once can't corrupt each other
    n = 0
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([*ID_KEYS, "offset", "length"])
        for off, raw in iter_raw(src):
            i = ids_of(raw)
            w.writerow([*(i[k] for k in ID_KEYS), off, len(raw)])
            n += 1
    # sanity check before replacing the old index
    with open(tmp, newline="") as f:
        rows = list(csv.reader(f))[1:]
    if len(rows) != n or any(len(r) != 6 or not r[0].isdigit() or not r[4].isdigit() for r in rows):
        os.remove(tmp)
        raise RuntimeError("index build produced a damaged file (another build running at the same time?); try again")
    os.replace(tmp, INDEX)
    print(f"indexed {n:,} records -> {INDEX}", file=sys.stderr)


def index_ok(src=DEFAULT_SRC):
    """Index exists, is newer than the JSON and has the ID columns (an older pID-only index is rebuilt)."""
    if not os.path.exists(INDEX) or os.path.getmtime(INDEX) < os.path.getmtime(src):
        return False
    with open(INDEX, newline="") as f:
        header = next(csv.reader(f), [])
    return all(k in header for k in ID_KEYS)


def norm(x):
    return str(x).strip().upper()


def find_with_index(src, wanted):
    """{wanted id: [(id type, record), ...]} -- a number can be one property's pID and another's refID2."""
    hits = {}
    with open(INDEX, newline="") as f:
        for row in csv.DictReader(f):
            for k in ID_KEYS:
                if row[k] and norm(row[k]) in wanted:
                    hits.setdefault(norm(row[k]), []).append((k, int(row["offset"]), int(row["length"])))
    found = {}
    with open(src, "rb") as f:
        for key, matches in hits.items():
            for k, off, ln in matches:
                f.seek(off)
                found.setdefault(key, []).append((k, json.loads(f.read(ln))))
    return found


def find_by_scan(src, wanted):
    found = {}
    for _, raw in iter_raw(src):
        # cheap text check before parsing JSON
        if not any(w.encode() in raw.upper() for w in wanted):
            continue
        i = ids_of(raw)
        rec = None
        for k in ID_KEYS:
            if i[k] and norm(i[k]) in wanted:
                rec = rec or json.loads(raw)
                found.setdefault(norm(i[k]), []).append((k, rec))
    return found


def money(v):
    try:
        return f"${float(v):,.0f}"
    except (TypeError, ValueError):
        return "-"


def first(lst):
    return lst[0] if lst else {}


def summarize(rec):
    ident = first(rec.get("propertyIdentification"))
    sit = next((s for s in rec.get("situses") or [] if s.get("primarySitus")), first(rec.get("situses")))
    legal = first(rec.get("propertyLegalDescription"))
    prof = first(rec.get("propertyProfile"))
    owners = rec.get("owners") or []
    appeals = sorted(rec.get("appeals") or [], key=lambda a: a.get("appealID") or 0)
    p = print

    p("=" * 78)
    p(f"pID {rec['pID']}   account {ident.get('refID2')}   refID1 {ident.get('refID1')}   geoID {ident.get('geoID')}   year {rec.get('pYear')}")
    addr = " ".join(str(sit.get(k)) for k in ("streetNum", "streetPrefix", "streetName", "streetSuffix", "streetSecondary") if sit.get(k))
    p(f"Situs:      {addr}, {sit.get('city') or ''} {sit.get('zip') or ''}")
    p(f"Legal:      {legal.get('legalDescription')}")
    p(f"State cd:   {prof.get('stateCd')}   exemptions: {prof.get('exemptions') or '-'}   taxing units: {prof.get('taxingUnits')}")
    p(f"Notice dt:  {rec.get('noticeDt') or '(none - no notice mailed)'}")

    for o in owners:
        v = first(o.get("ownerValue")) if isinstance(o.get("ownerValue"), list) else (o.get("ownerValue") or {})
        p("-" * 78)
        p(f"Owner:      {o.get('name')}  ({o.get('ownerPct')}%)   ownerID {o.get('ownerID')}  pAccountID {o.get('pAccountID')}")
        for a in o.get("agents") or []:
            name = a.get("companyName") or a.get("contactName") or \
                " ".join(x for x in (a.get("firstName"), a.get("lastName")) if x)
            exp = a.get("expirationDt")
            p(f"Agent:      {name}  (agentID {a.get('agentID')}, effective {str(a.get('effectiveDt') or '-')[:10]}"
              f"{', expires ' + str(exp)[:10] if exp else ''})")
        ex = [e.get("exemptionCode") for e in o.get("exemptions") or []]
        p(f"Exemptions: {', '.join(map(str, ex)) or '-'}")
        p("Current values (after protest / corrections):")
        p(f"  land {money(v.get('ownerLandValue'))}   improvement {money(v.get('ownerImprovementValue'))}   "
          f"market {money(v.get('ownerMarketValue'))}")
        p(f"  appraised {money(v.get('ownerAppraisedValue'))}   HS cap loss {money(v.get('ownerTaxLimitationValue'))}   "
          f"net appraised {money(v.get('ownerNetAppraisedValue'))}")
        tx = o.get("ownerTaxable") or []
        units = {u.get("taxingUnitID"): f"{u.get('taxingUnitCode')} {u.get('taxingUnitName')}"
                 for u in rec.get("taxingunits") or []}
        if tx:
            p("  taxable by unit:")
            for t in tx:
                exs = ", ".join(f"{e.get('exemptionCode')} {money(e.get('totalExemptionAmount'))}"
                                for e in t.get("exemptions") or [] if float(e.get("totalExemptionAmount") or 0))
                p(f"    {units.get(t.get('taxingUnitID'), t.get('taxingUnitID'))}: taxable {money(t.get('taxableValue'))}"
                  f"  (appraised {money(t.get('appraisedValue'))}{'; ' + exs if exs else ''})")

    p("-" * 78)
    if appeals:
        a = appeals[0]
        p(f"NOTICE VALUES (from appeal {a.get('appealID')}, initial* = value before protest):")
        p(f"  land {money(a.get('initialLandValue'))}   improvement {money(a.get('initialImprovementValue'))}   "
          f"market {money(a.get('initialMarketValue'))}   appraised {money(a.get('initialAppraisedValue'))}")
        for a in appeals:
            open_note = "" if a.get("finalized") else "   (not finalized - final value is 0 or provisional)"
            p(f"  appeal {a.get('appealID')} {a.get('pYear')} {a.get('appealType')} {str(a.get('appealStatus')).strip()}: "
              f"market {money(a.get('initialMarketValue'))} -> {money(a.get('finalMarketValue'))}, "
              f"appraised {money(a.get('initialAppraisedValue'))} -> {money(a.get('finalAppraisedValue'))}{open_note}")
    else:
        p("NOTICE VALUES: not protested -> use the current values above "
          "(same as notice unless corrected after mailing).")
    p("=" * 78)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", help="pID, refID2 (account), refID1 (M...) or geoID")
    ap.add_argument("--src", default=DEFAULT_SRC)
    ap.add_argument("--build-index", action="store_true", help="(re)build the index now")
    ap.add_argument("--no-index", action="store_true", help="scan the file even if an index exists")
    args = ap.parse_args()

    if args.build_index:
        build_index(args.src)
        if not args.ids:
            return
    if not args.ids:
        ap.error("give at least one id")

    wanted = {norm(i) for i in args.ids}
    if args.no_index or args.src != DEFAULT_SRC:
        found = find_by_scan(args.src, wanted)
    else:
        if not index_ok(args.src):
            build_index(args.src)
        found = find_with_index(args.src, wanted)

    os.makedirs(OUT_DIR, exist_ok=True)
    for key in args.ids:
        matches = found.get(norm(key))
        if not matches:
            print(f"not found: {key}")
            continue
        if len(matches) > 1:
            print(f"*** {key} matches {len(matches)} properties: "
                  + ", ".join(f"{k} of pID {r['pID']}" for k, r in matches) + " ***")
        for k, rec in matches:
            print(f"[{key} matched as {k}]")
            summarize(rec)
            path = os.path.join(OUT_DIR, f"pid_{rec['pID']}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(rec, f, indent=1)
            print(f"full record -> {path}\n")


if __name__ == "__main__":
    main()
