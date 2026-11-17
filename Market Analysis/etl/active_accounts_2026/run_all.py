"""Run every county script in parallel (one process per CAD, so a slow or failing county does not block the
others), then write the combined files in Market Analysis/output/active_accounts_2026/.

Run all:          /Users/user2/PTP/.venv/bin/python -I "Market Analysis/etl/active_accounts_2026/run_all.py"
Run some:         ... run_all.py dallas tarrant
Run one county:   /Users/user2/PTP/.venv/bin/python -I "Market Analysis/etl/active_accounts_2026/dallas.py"
Rebuild combined files only (no county runs):  ... run_all.py --combine
"""
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import OUT, load_input  # noqa: E402

SCRIPTS = {"Bexar": "bexar", "Dallas": "dallas", "Denton": "denton", "Fort Bend": "fort_bend", "Harris": "harris",
           "Hays": "hays", "Montgomery": "montgomery", "Rockwall": "rockwall", "Tarrant": "tarrant",
           "Travis": "travis"}


def run(names):
    logs = OUT / "_logs"
    logs.mkdir(parents=True, exist_ok=True)
    procs = {}
    for county, script in SCRIPTS.items():
        if names and script not in names:
            continue
        log = open(logs / f"{script}.log", "w")
        procs[county] = (subprocess.Popen([sys.executable, "-I", str(HERE / f"{script}.py")], stdout=log,
                                          stderr=subprocess.STDOUT), log, time.time())
        print(f"started {county}", flush=True)
    status = {}
    while procs:
        for county, (p, log, t0) in list(procs.items()):
            if p.poll() is not None:
                log.close()
                status[county] = "ok" if p.returncode == 0 else f"FAILED (see _logs/{SCRIPTS[county]}.log)"
                print(f"{county}: {status[county]} in {time.time() - t0:.0f}s", flush=True)
                del procs[county]
        time.sleep(2)
    return status


def combine():
    inp = load_input()
    with_acct = inp[inp.has_account]
    no_data = with_acct[~with_acct.county_clean.isin(SCRIPTS)]
    no_data[["row_in_input", "account_number", "county", "county_clean", "current_year_market_value",
             "input_state_code"]].to_csv(OUT / "no_cad_data_counties_2026.csv", index=False)
    blank = inp[~inp.has_account]
    blank.groupby("county_clean").size().rename("rows_blank_account").reset_index() \
        .to_csv(OUT / "blank_account_rows_by_county.csv", index=False)

    rows, parts = [], []
    for county, script in SCRIPTS.items():
        f = OUT / county / f"{script}_active_accounts_2026.csv"
        n_in = int(with_acct.county_clean.eq(county).sum())
        if not f.exists():
            rows.append(dict(county=county, input_rows_with_account=n_in, status="not run / failed"))
            continue
        d = pd.read_csv(f, dtype={"account_number": str, "cad_account": str}, low_memory=False)
        found = d[d.found_in_cad.eq("Y")]
        r = dict(county=county, input_rows_with_account=n_in, found_in_cad=len(found),
                 not_found=int(d.found_in_cad.eq("N").sum()), roll_date=d.roll_date.iloc[0] if len(d) else "",
                 with_address=int(found.situs_address.fillna("").ne("").sum()),
                 with_zip=int(found.situs_zip.fillna("").astype(str).ne("").sum()),
                 with_notice_value=int(found.notice_value.notna().sum()),
                 notice_value_total=found.notice_value.sum(), market_value_total=found.market_value.sum(),
                 accounts_reduced=int(found.value_result.eq("Reduced").sum()),
                 total_reduction=found.reduction[found.reduction > 0].sum(), status="ok")
        for g, n in found.res_or_com.value_counts().items():
            r[f"accounts_{g.lower()}"] = n
        rows.append(r)
        parts.append(found.groupby(["res_or_com", "property_category"]).agg(
            accounts=("account_number", "size"), notice_value=("notice_value", "sum"),
            market_value=("market_value", "sum"), reduction=("reduction", "sum"),
            accounts_reduced=("value_result", lambda x: int(x.eq("Reduced").sum()))).reset_index()
            .assign(county=county))
    for county, n in no_data.county_clean.value_counts().items():
        rows.append(dict(county=county, input_rows_with_account=n, status="no CAD data downloaded"))
    pd.DataFrame(rows).to_csv(OUT / "all_counties_summary_2026.csv", index=False)
    combine_rows(no_data)
    if parts:
        p = pd.concat(parts)[["county", "res_or_com", "property_category", "accounts", "accounts_reduced",
                              "notice_value", "market_value", "reduction"]]
        p.to_csv(OUT / "all_counties_by_category_2026.csv", index=False)
    print(pd.DataFrame(rows).to_string(index=False))


def combine_rows(no_data):
    """all_counties_found_2026.csv / all_counties_not_found_2026.csv: every county's rows stacked. Shared columns
    first (same order as the county files), county-specific extras after them (blank for other counties)."""
    frames = []
    for county, script in SCRIPTS.items():
        f = OUT / county / f"{script}_active_accounts_2026.csv"
        if f.exists():
            frames.append(pd.read_csv(f, dtype=str, keep_default_na=False))
    if not frames:
        return
    shared = [c for c in frames[0].columns if all(c in x.columns for x in frames)]
    shared = [c for c in shared if c not in ("roll_source", "roll_date")]
    extra = list(dict.fromkeys(c for x in frames for c in x.columns if c not in shared + ["roll_source", "roll_date"]))
    cols = shared + extra + ["roll_source", "roll_date"]
    allrows = pd.concat(frames, ignore_index=True).reindex(columns=cols).fillna("")

    found = allrows[allrows.found_in_cad.eq("Y")]
    found.to_csv(OUT / "all_counties_found_2026.csv", index=False)

    nf = allrows[allrows.found_in_cad.eq("N")].copy()
    nf.insert(4, "not_found_reason", "account not in the CAD's latest roll")
    nd = pd.DataFrame({"row_in_input": no_data.row_in_input.astype(str), "account_number": no_data.account_number,
                       "county": no_data.county_clean, "found_in_cad": "N",
                       "not_found_reason": "no CAD data downloaded for this county",
                       "input_market_value": no_data.current_year_market_value,
                       "input_state_code": no_data.input_state_code})
    nf = pd.concat([nf, nd], ignore_index=True).reindex(columns=nf.columns).fillna("")
    keep = [c for c in nf.columns if nf[c].ne("").any() or c in ("row_in_input", "account_number", "county")]
    nf[keep].to_csv(OUT / "all_counties_not_found_2026.csv", index=False)
    print(f"all_counties_found_2026.csv: {len(found):,} rows; all_counties_not_found_2026.csv: {len(nf):,} rows "
          f"({len(nf) - len(nd):,} not in roll, {len(nd):,} no CAD data)")


if __name__ == "__main__":
    args = [a.lower() for a in sys.argv[1:]]
    if "--combine" not in args:
        OUT.mkdir(parents=True, exist_ok=True)
        run(set(args))
    combine()
