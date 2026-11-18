"""Manual actives (no account number): dedupe the input, then find each property in the CAD roll by address.

Input : /Users/user2/PTP/temp/property_actives_manual.csv  (address, city, zip, county; mostly no account)
Output: /Users/user2/PTP/Market Analysis/output/active_manual_2026/
          manual_deduped_input_2026.csv        one row per property after dedupe (input_ids = all original ids)
          manual_duplicate_groups_2026.csv     the original rows that were folded together
          <County>/<county>_manual_2026.csv    every property of that county with the CAD match and values
          <County>/<county>_manual_not_found_2026.csv / _manual_review_2026.csv / _manual_summary_2026.csv

The CAD rolls are read with the same loaders as the account-number task (../active_accounts_2026/<county>.py),
so values, state codes, notice values and reductions are built the same way.

Match steps, per property (first one that finds something wins):
  1. account written in the input (account_number_county, e.g. "1144960010001 Harris 156")
  2. same house number + street name (ignoring Dr/Drive, N/North...) + same zip      -> "address + zip"
  3. same house number + street name, zip differs or the CAD has no zip (Tarrant)   -> "address, zip differs/none"
  4. same house number + zip (or county if no zip), street name spelled differently -> "fuzzy street name"
Then units narrow the candidates; real property wins over business personal property at the same address.
match_quality: exact / good / fuzzy / review (several CAD accounts fit; candidate_accounts lists them).
"""
import difflib
import importlib.util
import re
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ACC = HERE.parent / "active_accounts_2026"
sys.path.insert(0, str(ACC))
sys.path.insert(0, str(HERE))
from address import parse, zip5  # noqa: E402
from common import ADDR, ROOT, add_results, norm_acct, norm_county, prep_roll  # noqa: E402

INPUT = ROOT / "temp" / "property_actives_manual.csv"
OUT = ROOT / "Market Analysis" / "output" / "active_manual_2026"
SCRIPTS = {"Bexar": "bexar", "Dallas": "dallas", "Denton": "denton", "Fort Bend": "fort_bend", "Harris": "harris",
           "Hays": "hays", "Montgomery": "montgomery", "Rockwall": "rockwall", "Tarrant": "tarrant",
           "Travis": "travis"}
FUZZY_MIN = 0.85
OWNER_COLS = ["county_owner_name", "county_owner_address", "county_owner_city", "county_owner_state",
              "county_owner_zip", "owner_eightbase_id"]
TIMESTAMP_COLS = ["created_at", "updated_at", "reregistered_at"]   # used to pick the newest row, never written out


# ---- input + dedupe --------------------------------------------------------------------------------------
def _input_account(v, county):
    """account_number_county looks like '<account> <County> <unit>' -> account (first word)."""
    t = str(v or "").split()
    if len(t) == 1:
        return t[0]
    rest = "".join(t[1:]).lower()
    return t[0] if t and rest.startswith(county.replace(" ", "").lower()[:5]) else ""


def load_input():
    d = pd.read_csv(INPUT, dtype=str, keep_default_na=False)
    d["row_in_input"] = d.index + 2
    d["county_clean"] = d.county.map(norm_county)
    p = pd.DataFrame([parse(a, c) for a, c in zip(d.street_address, d.city)], index=d.index)
    d["addr_number"], d["addr_street"], d["addr_core"] = p.number, p.street, p.core
    # unit: the parsed one, else the CRM's unit_id field
    d["addr_unit"] = [u or parse(f"1 X # {x}")["unit"] for u, x in zip(p.unit, d.unit_id)]
    # zip: zipcode column, else a zip written inside the address (owner fields and names are never used)
    d["addr_zip"] = [zip5(z, a) for z, a in zip(d.zipcode, d.street_address)]
    d["input_account"] = [_input_account(v, c) for v, c in zip(d.account_number_county, d.county_clean)]
    return d


def dedupe(d):
    """One row per property: same county + house number + street name + unit. Rows with different (non-blank)
    zips stay apart; a blank zip joins its group. Kept row: not archived, then most filled-in, then newest."""
    base = d.county_clean + "|" + d.addr_number + "|" + d.addr_core + "|" + d.addr_unit
    base = base.where(d.addr_number.ne(""), d.county_clean + "|" + d.street_address.str.upper().str.replace(
        r"[^A-Z0-9]", "", regex=True) + "|" + d.addr_unit)
    zips = d.assign(base=base).groupby("base").addr_zip.agg(lambda z: set(z) - {""})
    d["property_key"] = [b + ("|" + z if len(zips[b]) > 1 and z else "") for b, z in zip(base, d.addr_zip)]
    d["_filled"] = d.drop(columns=[c for c in OWNER_COLS if c in d]).ne("").sum(axis=1)
    d = d.sort_values(["property_key", "is_archived", "_filled", "updated_at"], ascending=[True, True, False, False])
    g = d.groupby("property_key", sort=False)
    rep = g.head(1).copy()
    agg = g.agg(input_ids=("id", lambda s: ";".join(s)), input_rows=("id", "size"),
                rows_not_archived=("is_archived", lambda s: int(s.eq("0").sum())),
                all_rows_in_input=("row_in_input", lambda s: ";".join(map(str, sorted(s)))),
                salesforce_ids=("salesforce_id", lambda s: ";".join(sorted(set(s) - {""}))),
                zip_any=("addr_zip", lambda s: next((z for z in s if z), "")),
                account_any=("input_account", lambda s: next((a for a in s if a), "")))
    rep = rep.merge(agg, left_on="property_key", right_index=True)
    rep["addr_zip"] = rep.addr_zip.where(rep.addr_zip.ne(""), rep.zip_any)
    rep["input_account"] = rep.input_account.where(rep.input_account.ne(""), rep.account_any)
    rep = rep.drop(columns=["zip_any", "account_any", "_filled"]).rename(columns={"id": "property_id"})
    dups = d[d.property_key.isin(agg.index[agg.input_rows > 1])].drop(columns="_filled")
    return rep.sort_values("row_in_input").reset_index(drop=True), dups


# ---- CAD side --------------------------------------------------------------------------------------------
def load_county_roll(county):
    """Run that county's loader from the account-number task."""
    script = SCRIPTS[county]
    spec = importlib.util.spec_from_file_location(f"acc_{script}", ACC / f"{script}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, prep_roll(mod.load_roll())


def index_roll(roll, numbers):
    """Parse situs addresses, only for accounts whose house number appears in the input (keeps it fast)."""
    first = roll.situs_address.str.extract(r"^\s*(\d+)", expand=False).fillna("")
    sub = roll[first.isin({re.match(r"\d+", n).group(0) for n in numbers if re.match(r"\d+", n)})].copy()
    p = pd.DataFrame([parse(a, c) for a, c in zip(sub.situs_address, sub.situs_city)], index=sub.index)
    sub["c_number"], sub["c_core"], sub["c_unit"] = p.number, p.core, p.unit
    sub["c_zip"] = sub.situs_zip.str[:5]
    cat = sub.state_code.fillna("").str.upper()
    sub["c_rank"] = 0
    sub.loc[cat.str.match(r"^(L|G|J|N)") | sub.get("prop_type", pd.Series("", index=sub.index)).isin(["P", "MN"])
            | sub.get("division", pd.Series("", index=sub.index)).eq("BPP"), "c_rank"] = 1   # personal property last
    by_num = {n: g for n, g in sub.groupby("c_number")}
    return by_num


def pick(cands, prop, method):
    """Narrow candidates by unit, then real property first. -> (row or None, method, quality, n, accounts)."""
    c = cands
    unit_note = ""
    if prop.addr_unit:
        same = c[c.c_unit.eq(prop.addr_unit)]
        if len(same):
            c = same
        else:
            unit_note = ", unit not matched"
    elif c.c_unit.ne("").any() and c.c_unit.eq("").any():
        c = c[c.c_unit.eq("")]
    c = c.sort_values(["c_rank", "market_value"], ascending=[True, False])
    real = c[c.c_rank.eq(0)]
    if len(real):
        c = real
    n = len(c)
    accts = ";".join(c.cad_account.astype(str).head(10))
    quality = {"address + zip": "exact", "address (CAD has no zip)": "exact", "account in input file": "exact", "fuzzy street name": "fuzzy"}.get(method, "good")
    if n > 1:
        quality = "review"
    elif unit_note and quality == "exact":
        quality = "good"
    return c.iloc[0], method + unit_note, quality, n, accts


def match_one(prop, roll, by_num):
    if prop.input_account:
        k = norm_acct(prop.input_account)
        if k in roll.index:
            r = roll.loc[k]
            return r, "account in input file", "exact", 1, str(r.cad_account)
    if not prop.addr_number:
        return None, "no house number in the address", "", 0, ""
    cands = by_num.get(prop.addr_number)
    if cands is None:
        return None, "house number not anywhere in CAD roll", "", 0, ""
    same = cands[cands.c_core.eq(prop.addr_core)]
    if len(same) and prop.addr_zip:
        for rows, how in [(same[same.c_zip.eq(prop.addr_zip)], "address + zip"),
                          (same[same.c_zip.eq("")], "address (CAD has no zip)"),
                          (same, "address, zip differs")]:
            if len(rows):
                return pick(rows, prop, how)
    if len(same):
        return pick(same, prop, "address (input has no zip)")
    pool = cands[cands.c_zip.isin([prop.addr_zip, ""])] if prop.addr_zip else cands
    if len(pool) and prop.addr_core:
        score = pool.c_core.map(lambda x: difflib.SequenceMatcher(None, x, prop.addr_core).ratio())
        # one name inside the other ("ISLANDVIEW" in "ISLANDVIEWSLANDVIEW"), only when lengths are close
        contains = pool.c_core.map(lambda x: len(x) >= 5 and len(prop.addr_core) >= 5
                                   and (x in prop.addr_core or prop.addr_core in x)
                                   and min(len(x), len(prop.addr_core)) / max(len(x), len(prop.addr_core)) >= 0.7)
        ok = pool[(score >= FUZZY_MIN) | contains]
        if len(ok):
            best = score[ok.index].max()
            return pick(ok[score[ok.index] >= best - 0.02], prop, "fuzzy street name")
    return None, "address not found in CAD roll", "", 0, ""


# ---- run one county --------------------------------------------------------------------------------------
FRONT = ["property_id", "input_ids", "input_rows", "rows_not_archived", "county", "input_street_address",
         "input_city", "input_zip", "input_unit", "found_in_cad", "match_method",
         "match_quality", "candidates", "candidate_accounts", "cad_account", "situs_address", "situs_city",
         "situs_zip", "res_or_com", "property_category", "state_code", "ptd_state_code", "state_code_desc",
         "notice_value", "market_value", "reduction", "reduction_pct", "value_result", "notice_source",
         "protested", "protest_outcome", "protest_final_value", "input_market_value", "market_value_diff",
         "input_state_code", "state_code_changed"]


def run(county):
    t0 = time.time()
    folder = OUT / county
    folder.mkdir(parents=True, exist_ok=True)
    slug = county.lower().replace(" ", "_")
    props, _ = dedupe(load_input())
    mine = props[props.county_clean.eq(county)].copy()
    print(f"[{county}] {len(mine):,} properties after dedupe; loading roll", flush=True)
    mod, roll = load_county_roll(county)
    roll = roll.set_index("key", drop=False)
    by_num = index_roll(roll, set(mine.addr_number))
    print(f"[{county}] roll {len(roll):,} accounts, {sum(map(len, by_num.values())):,} share a house number with "
          f"the input ({time.time() - t0:.0f}s)", flush=True)

    hits, info = [], []
    for prop in mine.itertuples():
        r, method, quality, n, accts = match_one(prop, roll, by_num)
        hits.append(r.key if r is not None else None)
        info.append((method, quality, n, accts))
    mine["key"] = hits
    mine["match_method"], mine["match_quality"], mine["candidates"], mine["candidate_accounts"] = zip(*info) \
        if info else ([], [], [], [])
    mine["found_in_cad"] = mine.key.notna().map({True: "Y", False: "N"})

    # two input properties that land on the same CAD account are the same property -> fold them together
    found = mine[mine.found_in_cad.eq("Y")]
    dup = found.key.duplicated(keep="first")
    if dup.any():
        keep = found[~dup]
        extra = found[dup].groupby("key").agg(ids=("input_ids", ";".join), n=("input_rows", "sum"),
                                              na=("rows_not_archived", "sum"))
        mine = mine.drop(found[dup].index)
        k = mine.key.isin(extra.index)
        mine.loc[k, "input_ids"] = mine.loc[k, "input_ids"] + ";" + mine.loc[k, "key"].map(extra.ids)
        mine.loc[k, "input_rows"] = mine.loc[k, "input_rows"] + mine.loc[k, "key"].map(extra.n)
        mine.loc[k, "rows_not_archived"] = mine.loc[k, "rows_not_archived"] + mine.loc[k, "key"].map(extra.na)
        print(f"[{county}] {int(dup.sum())} more input properties folded: same CAD account as another row", flush=True)

    keep = {"property_id": "property_id", "input_ids": "input_ids", "input_rows": "input_rows",
            "rows_not_archived": "rows_not_archived", "street_address": "input_street_address",
            "city": "input_city", "addr_zip": "input_zip", "addr_unit": "input_unit",
            "current_year_market_value": "current_year_market_value",
            "state_code": "input_state_code", "all_rows_in_input": "all_rows_in_input",
            "salesforce_ids": "salesforce_ids", "key": "key", "found_in_cad": "found_in_cad",
            "match_method": "match_method", "match_quality": "match_quality", "candidates": "candidates",
            "candidate_accounts": "candidate_accounts"}
    roll = roll.rename(columns={c: f"cad_{c}" for c in roll.columns if c in keep.values() and c != "key"})
    roll_cols = [c for c in roll.columns if c != "key"]
    m = mine[list(keep)].rename(columns=keep).merge(roll[roll_cols].reset_index(), on="key", how="left")
    m["county"] = county
    m = add_results(m, county)
    m["roll_source"], m["roll_date"] = mod.SOURCE, mod.DATE
    extra_cols = [c for c in roll_cols if c not in FRONT + ADDR + ["cad_account", "c_number", "c_core", "c_unit",
                                                                  "c_zip", "c_rank"]]
    m = m[FRONT + extra_cols + ["all_rows_in_input", "salesforce_ids", "roll_source", "roll_date"]]

    m.to_csv(folder / f"{slug}_manual_2026.csv", index=False)
    m[m.found_in_cad.eq("N")].to_csv(folder / f"{slug}_manual_not_found_2026.csv", index=False)
    m[m.match_quality.isin(["review", "fuzzy"])].to_csv(folder / f"{slug}_manual_review_2026.csv", index=False)
    s = m.groupby(["found_in_cad", "match_quality", "match_method"]).size().rename("properties").reset_index()
    s.insert(0, "county", county)
    s.to_csv(folder / f"{slug}_manual_summary_2026.csv", index=False)
    print(f"[{county}] done in {time.time() - t0:.0f}s: {int(m.found_in_cad.eq('Y').sum()):,} found, "
          f"{int(m.found_in_cad.eq('N').sum()):,} not found\n{s.to_string(index=False)}", flush=True)
    return m


def main(county):
    try:
        run(county)
    except Exception as e:
        print(f"[{county}] FAILED: {e!r}", file=sys.stderr, flush=True)
        raise
