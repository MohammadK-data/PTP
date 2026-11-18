"""Manual actives: dedupe the input, then find every property in its county's CAD roll, one process per county
in parallel (a slow or failing county does not block the others). Output: Market Analysis/output/active_manual_2026/

Run all:        /Users/user2/PTP/.venv/bin/python -I "Market Analysis/etl/active_manual_2026/run_all.py"
Run some:       ... run_all.py dallas tarrant
Run one county: /Users/user2/PTP/.venv/bin/python -I "Market Analysis/etl/active_manual_2026/dallas.py"
Summary only:   ... run_all.py --summary
"""
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from match import OUT, SCRIPTS, TIMESTAMP_COLS, dedupe, load_input  # noqa: E402


def write_dedupe():
    d = load_input()
    rep, dups = dedupe(d)
    drop = lambda x: x.drop(columns=[c for c in TIMESTAMP_COLS if c in x])  # noqa: E731
    cols = ["property_id", "input_ids", "input_rows", "rows_not_archived", "county_clean", "street_address", "city",
            "addr_zip", "addr_unit", "addr_number", "addr_street", "input_account", "all_rows_in_input",
            "has_cad_data"]
    rep["has_cad_data"] = rep.county_clean.isin(SCRIPTS).map({True: "Y", False: "N"})
    drop(rep[cols].rename(columns={"county_clean": "county", "addr_zip": "zip", "addr_unit": "unit",
                                   "addr_number": "house_number", "addr_street": "street_normalized"})) \
        .to_csv(OUT / "manual_deduped_input_2026.csv", index=False)
    dcols = ["property_key", "id", "row_in_input", "county", "street_address", "city", "zipcode", "unit_id",
             "addr_number", "addr_street", "addr_unit", "addr_zip", "account_number_county", "is_archived",
             "salesforce_id"]
    dups[dcols].to_csv(OUT / "manual_duplicate_groups_2026.csv", index=False)
    rep[~rep.county_clean.isin(SCRIPTS)][["property_id", "input_ids", "county_clean", "street_address", "city",
                                          "addr_zip"]].rename(columns={"county_clean": "county"}) \
        .to_csv(OUT / "manual_no_cad_data_counties_2026.csv", index=False)
    print(f"input {len(d):,} rows -> {len(rep):,} properties ({len(d) - len(rep):,} duplicate rows folded)")
    return d, rep


def run(names):
    logs = OUT / "_logs"
    logs.mkdir(parents=True, exist_ok=True)
    procs, status = {}, {}
    for county, script in SCRIPTS.items():
        if names and script not in names:
            continue
        log = open(logs / f"{script}.log", "w")
        procs[county] = (subprocess.Popen([sys.executable, "-I", str(HERE / f"{script}.py")], stdout=log,
                                          stderr=subprocess.STDOUT), log, time.time())
        print(f"started {county}", flush=True)
    while procs:
        for county, (p, log, t0) in list(procs.items()):
            if p.poll() is not None:
                log.close()
                status[county] = "ok" if p.returncode == 0 else f"FAILED (see _logs/{SCRIPTS[county]}.log)"
                print(f"{county}: {status[county]} in {time.time() - t0:.0f}s", flush=True)
                del procs[county]
        time.sleep(2)
    return status


def summary(d, rep):
    rows = []
    for county, script in SCRIPTS.items():
        f = OUT / county / f"{script}_manual_2026.csv"
        r = dict(county=county, input_rows=int(d.county_clean.eq(county).sum()),
                 properties_after_dedupe=int(rep.county_clean.eq(county).sum()))
        if not f.exists():
            rows.append({**r, "status": "not run / failed"})
            continue
        m = pd.read_csv(f, dtype=str, keep_default_na=False)
        q = m.match_quality.value_counts()
        rows.append({**r, "properties_in_output": len(m), "found": int(m.found_in_cad.eq("Y").sum()),
                     "not_found": int(m.found_in_cad.eq("N").sum()), "exact": int(q.get("exact", 0)),
                     "good": int(q.get("good", 0)), "fuzzy": int(q.get("fuzzy", 0)),
                     "review": int(q.get("review", 0)), "status": "ok"})
    for county, n in rep[~rep.county_clean.isin(SCRIPTS)].county_clean.value_counts().items():
        rows.append(dict(county=county, input_rows=int(d.county_clean.eq(county).sum()),
                         properties_after_dedupe=n, status="no CAD data downloaded"))
    s = pd.DataFrame(rows)
    s.to_csv(OUT / "manual_summary_by_county_2026.csv", index=False)
    print(s.to_string(index=False))


if __name__ == "__main__":
    args = [a.lower() for a in sys.argv[1:]]
    OUT.mkdir(parents=True, exist_ok=True)
    d, rep = write_dedupe()
    if "--summary" not in args:
        run(set(args))
    summary(d, rep)
