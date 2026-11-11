"""Look up one or more Denton properties in the Protax JSON export and show their notice values.

An "account id" can be any of:
    pID       property ID on the Denton CAD website      e.g. 8
    refID2    account number                              e.g. R00008
    refID1    legacy reference number                     e.g. 174650
    geoID     geographic ID                               e.g. SL0100A-00000A-0000-0004-0000

Usage (from the Denton folder):
    python3 -I etl/denton_lookup.py 8
    python3 -I etl/denton_lookup.py 8 R00012 SL0100A-00000A-0000-0004-0000
    python3 -I etl/denton_lookup.py --build-index      # one-time pass over the 21 GB file (several minutes)

Without the index, each run reads through the whole file. With the index, a lookup seeks straight to the
record and finishes in under a second.

For each property it prints a summary and writes the full record to output/protax_review/pid_<pID>.json.

Notice values:
- Protested properties: the appeal's initial* values (the value before the protest). The appeal's notice*
  columns are 0 in Denton's export, so they are not used.
- Not protested: the current ownerValue values. They match the notice unless a correction changed the
  value after the notice was mailed.
"""

import argparse
import csv
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DENTON = os.path.dirname(HERE)
DEFAULT_SRC = os.path.join(DENTON, "Data", "Denton-protaxExport-20260727.json")
OUT_DIR = os.path.join(DENTON, "output", "protax_review")
INDEX = os.path.join(OUT_DIR, "protax_index.csv")

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
                    print(f"  {n:,} records, {time.time() - start:,.0f}s", file=sys.stderr)
            else:
                buf.append(line)
            offset += len(line)


def ids_of(raw):
    out = {"pID": RE_PID.search(raw).group(1).decode()}
    for k, rx in RE_IDS.items():
        m = rx.search(raw)
        out[k] = m.group(1).decode() if m else ""
    return out


def build_index(src):
    os.makedirs(OUT_DIR, exist_ok=True)
    n = 0
    with open(INDEX, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pID", "geoID", "refID1", "refID2", "offset", "length"])
        for off, raw in iter_raw(src):
            i = ids_of(raw)
            w.writerow([i["pID"], i["geoID"], i["refID1"], i["refID2"], off, len(raw)])
            n += 1
    print(f"indexed {n:,} records -> {INDEX}")


def norm(x):
    return str(x).strip().upper()


def find_with_index(src, wanted):
    hits = {}
    with open(INDEX, newline="") as f:
        for row in csv.DictReader(f):
            for k in ("pID", "geoID", "refID1", "refID2"):
                if row[k] and norm(row[k]) in wanted:
                    hits[norm(row[k])] = (int(row["offset"]), int(row["length"]))
    found = {}
    with open(src, "rb") as f:
        for key, (off, ln) in hits.items():
            f.seek(off)
            found[key] = json.loads(f.read(ln))
    return found


def find_by_scan(src, wanted):
    found, left = {}, set(wanted)
    for _, raw in iter_raw(src):
        # cheap text check before parsing JSON
        if not any(w.encode() in raw.upper() for w in left):
            continue
        i = ids_of(raw)
        for k in ("pID", "geoID", "refID1", "refID2"):
            if i[k] and norm(i[k]) in left:
                found[norm(i[k])] = json.loads(raw)
                left.discard(norm(i[k]))
        if not left:
            break
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
    p(f"pID {rec['pID']}   account {ident.get('refID2')}   geoID {ident.get('geoID')}   year {rec.get('pYear')}")
    addr = " ".join(str(sit.get(k)) for k in ("streetNum", "streetPrefix", "streetName", "streetSuffix", "streetSecondary") if sit.get(k))
    p(f"Situs:      {addr}, {sit.get('city') or ''} {sit.get('zip') or ''}")
    p(f"Legal:      {legal.get('legalDescription')}")
    p(f"State cd:   {prof.get('stateCd')}   exemptions: {prof.get('exemptions') or '-'}   taxing units: {prof.get('taxingUnits')}")
    p(f"Notice dt:  {rec.get('noticeDt') or '(none - no notice mailed)'}")

    for o in owners:
        v = first(o.get("ownerValue")) if isinstance(o.get("ownerValue"), list) else (o.get("ownerValue") or {})
        p("-" * 78)
        p(f"Owner:      {o.get('name')}  ({o.get('ownerPct')}%)   ownerID {o.get('ownerID')}  pAccountID {o.get('pAccountID')}")
        agents = [a.get("companyName") or a.get("contactName") for a in o.get("agents") or []]
        if agents:
            p(f"Agent:      {', '.join(map(str, agents))}")
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
            p(f"  appeal {a.get('appealID')} {a.get('appealType')} {str(a.get('appealStatus')).strip()}: "
              f"market {money(a.get('initialMarketValue'))} -> {money(a.get('finalMarketValue'))}, "
              f"appraised {money(a.get('initialAppraisedValue'))} -> {money(a.get('finalAppraisedValue'))}")
    else:
        p("NOTICE VALUES: not protested -> use the current values above "
          "(same as notice unless corrected after mailing).")
    p("=" * 78)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", help="pID, account (R...), refID1 or geoID")
    ap.add_argument("--src", default=DEFAULT_SRC)
    ap.add_argument("--build-index", action="store_true", help="index the file once for instant lookups")
    ap.add_argument("--no-index", action="store_true", help="scan the file even if an index exists")
    args = ap.parse_args()

    if args.build_index:
        build_index(args.src)
        if not args.ids:
            return
    if not args.ids:
        ap.error("give at least one id")

    wanted = {norm(i) for i in args.ids}
    if os.path.exists(INDEX) and not args.no_index:
        found = find_with_index(args.src, wanted)
    else:
        print("No index yet: scanning the whole file (run --build-index once to make lookups instant).",
              file=sys.stderr)
        found = find_by_scan(args.src, wanted)

    os.makedirs(OUT_DIR, exist_ok=True)
    for key in args.ids:
        rec = found.get(norm(key))
        if rec is None:
            print(f"not found: {key}")
            continue
        summarize(rec)
        path = os.path.join(OUT_DIR, f"pid_{rec['pID']}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rec, f, indent=1)
        print(f"full record -> {path}\n")


if __name__ == "__main__":
    main()
