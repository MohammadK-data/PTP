"""Shared helpers for the active-accounts lookup (one script per CAD in this folder).

Input : /Users/user2/PTP/temp/property_actives_full_list.csv  (account_number, county, current_year_market_value, state_code)
Output: /Users/user2/PTP/Market Analysis/output/active_accounts_2026/<County>/
          <county>_active_accounts_2026.csv   every input row of that county that has an account number, with the
                                              latest CAD roll values and state code next to the input values
          <county>_not_found_2026.csv         input accounts not found in the CAD roll
          <county>_summary_2026.csv           counts and value by res_or_com / property_category / state_code

Each county script defines load_roll() returning one row per account with these columns:
  key            normalized account (see norm_acct) used for the join
  cad_account    account exactly as the CAD writes it
  state_code     main state code on the account (local code if the CAD uses one)
  ptd_state_code Comptroller (PTD) state code, when the CAD publishes the local->PTD mapping, else = state_code
  state_code_desc description from the CAD's state-code table, when it has one
  market_value   latest market value in the roll
plus any optional extra columns (appraised_value, land/impr state codes, division, class ...).
"""
import re
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/user2/PTP")
INPUT = ROOT / "temp" / "property_actives_full_list.csv"
CAD = ROOT / "CAD Website"
OUT = ROOT / "Market Analysis" / "output" / "active_accounts_2026"

COUNTY_FIX = {"elpaso": "El Paso", "fortbend": "Fort Bend"}


def norm_county(c):
    k = re.sub(r"[^a-z]", "", str(c).lower())
    return COUNTY_FIX.get(k, str(c).strip().title())


def norm_acct(a):
    """Upper-case, strip spaces; all-digit accounts lose leading zeros (CADs pad them differently)."""
    s = re.sub(r"\s+", "", str(a)).upper()
    if s.isdigit():
        s = s.lstrip("0") or "0"
    return s


def load_input():
    d = pd.read_csv(INPUT, dtype=str, keep_default_na=False).rename(columns={"state_code": "input_state_code"})
    d["row_in_input"] = d.index + 2          # line number in the CSV (header is line 1)
    d["county_clean"] = d.county.map(norm_county)
    d["has_account"] = d.account_number.str.strip().ne("")
    return d


def num(s):
    return pd.to_numeric(pd.Series(s).astype(str).str.replace(",", "").str.strip(), errors="coerce")


# ---- property type from state code -----------------------------------------------------------------------
COMMERCIAL_LAND = {"C1C", "C2C", "C12", "C13", "C2"}   # Tarrant C1C/C2C, Dallas C12/C13, Harris C2 (commercial vacant)


def classify(code, desc="", county=""):
    """-> (property_category, res_or_com). Uses the PTD code (first letter + digit) and the description."""
    c = str(code or "").strip().upper()
    d = str(desc or "").upper()
    if not c:
        return "Unknown (no state code)", "Unknown"
    if c.startswith("A"):
        return "Single-family residential", "Residential"
    if c.startswith("B"):
        return "Multifamily (apartments, duplex+)", "Multifamily"
    if c.startswith("C"):
        commercial = (c in {"C1C", "C2C", "C12", "C13"} or (county == "Harris" and c == "C2")
                      or "COMM" in d or "INDUST" in d)
        return ("Vacant land - commercial", "Commercial") if commercial else ("Vacant land - residential", "Residential")
    if c.startswith("D"):
        return "Ag / farm & ranch land", "Ag"
    if c.startswith("E"):
        return "Rural land, non-ag (with homes)", "Residential"
    if c.startswith("F2"):
        return "Industrial real property", "Commercial"
    if c.startswith("F"):
        return "Commercial real property", "Commercial"
    if c.startswith("G"):
        return "Minerals (oil & gas)", "Other"
    if c.startswith("J"):
        return "Utilities", "Commercial"
    if c.startswith("L2"):
        return "Industrial personal property", "Commercial"
    if c.startswith("L"):
        return "Commercial personal property (BPP)", "Commercial"
    if c.startswith("M"):
        return "Mobile home", "Residential"
    if c.startswith("N"):
        return "Intangible personal property", "Other"
    if c.startswith("O"):
        return "Residential inventory", "Residential"
    if c.startswith("S"):
        return "Special inventory (dealers)", "Commercial"
    if c.startswith("X"):
        return "Exempt", "Other"
    if c.startswith("Z") and county == "Harris":      # HCAD Z0-Z5: residential condos / townhomes
        return "Residential condo / townhome", "Residential"
    if c == "TMBR" or c.endswith("D1"):              # HCAD 1D1 ag, TMBR timber
        return "Ag / farm & ranch land", "Ag"
    return f"Other ({c})", "Other"


# ---- address / notice helpers ----------------------------------------------------------------------------
ADDR = ["situs_address", "situs_city", "situs_zip"]
NOTICE = ["notice_value", "notice_source", "protested", "protest_outcome", "protest_final_value"]


def join_addr(*parts):
    """Join address pieces (Series), skipping blanks."""
    df = pd.concat([p.fillna("").astype(str).str.strip() for p in parts], axis=1)
    return df.apply(lambda r: " ".join(x for x in r if x), axis=1)


def add_values_file(roll, path, key, rename, label):
    """Attach the earlier protest/values build (CAD Website/<County>/output/<county>_values_2026.csv).
    rename maps that file's columns to: situs_address, situs_city, situs_zip, notice_value, notice_source,
    protested, protest_outcome, protest_final_value. Address columns only fill blanks in the roll."""
    v = pd.read_csv(path, dtype=str, keep_default_na=False, usecols=[key, *rename]).rename(columns=rename)
    v["key"] = v.pop(key).map(norm_acct)
    v = v.drop_duplicates("key", keep="last")
    if "notice_value" in v:
        v["notice_value"] = num(v.notice_value).values
        if "notice_source" not in v:
            v["notice_source"] = label
        else:
            v["notice_source"] = label + ": " + v.notice_source
        v.loc[v.notice_value.isna(), "notice_source"] = ""
    if "protest_final_value" in v:
        v["protest_final_value"] = num(v.protest_final_value).values
    if "protested" in v:
        v["protested"] = v.protested.map({"True": "Y", "False": "N"}).fillna(v.protested)
    roll = roll.copy()
    roll["key"] = roll.key.map(norm_acct)
    out = roll.merge(v, on="key", how="left", suffixes=("", "_v"))
    for c in [c for c in v.columns if c != "key" and f"{c}_v" in out]:
        a = out[c]
        out[c] = a.where(a.notna() & a.astype(str).str.strip().ne(""), out.pop(f"{c}_v"))
    return out


def fill_notice(df, values, label, only_not_protested=True):
    """Fill blank notice_value from another source (the CAD's first 2026 notice-run export, or for accounts that
    were not protested the roll value). values: {normalized account: value}."""
    df = df.copy()
    if "notice_value" not in df:
        df["notice_value"], df["notice_source"] = float("nan"), ""
    if "protested" not in df:
        df["protested"] = ""
    blank = df.notice_value.isna()
    if only_not_protested:
        blank &= df.protested.fillna("").ne("Y")
    v = df.key.map(norm_acct).map(values)
    df.loc[blank, "notice_value"] = v[blank]
    df.loc[blank & v.notna(), "notice_source"] = label
    return df


# ---- run one county --------------------------------------------------------------------------------------
def run(county, load_roll, source, roll_date):
    t0 = time.time()
    folder = OUT / county
    folder.mkdir(parents=True, exist_ok=True)
    slug = county.lower().replace(" ", "_")

    inp = load_input()
    mine = inp[inp.county_clean.eq(county) & inp.has_account].copy()
    print(f"[{county}] {len(mine):,} input rows with an account; loading roll: {source}", flush=True)
    mine["key"] = mine.account_number.map(norm_acct)

    roll = load_roll()
    roll["key"] = roll.key.map(norm_acct)
    roll = roll.drop_duplicates("key", keep="last")
    for c, default in {"ptd_state_code": None, "state_code_desc": "", **{a: "" for a in ADDR},
                       "notice_value": float("nan"), "notice_source": "", "protested": "", "protest_outcome": "",
                       "protest_final_value": float("nan")}.items():
        if c not in roll:
            roll[c] = roll.state_code if default is None else default
    roll = roll.fillna({"state_code": "", "ptd_state_code": "", "state_code_desc": ""})
    for a in ADDR:
        roll[a] = roll[a].fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    print(f"[{county}] roll has {len(roll):,} accounts ({time.time() - t0:.0f}s)", flush=True)

    m = mine.merge(roll, on="key", how="left", indicator=True)
    m["found_in_cad"] = m.pop("_merge").eq("both").map({True: "Y", False: "N"})
    cls = [classify(p or s, d, county) if f == "Y" else ("", "")
           for p, s, d, f in zip(m.ptd_state_code, m.state_code, m.state_code_desc, m.found_in_cad)]
    m["property_category"] = [c[0] for c in cls]
    m["res_or_com"] = [c[1] for c in cls]
    m["input_market_value"] = num(m.current_year_market_value).values
    m["market_value_diff"] = m.market_value - m.input_market_value
    m["state_code_changed"] = ["" if f != "Y" or not i.strip() else
                               "N" if i.strip().upper() in {str(s).upper(), str(p).upper()} else "Y"
                               for f, i, s, p in zip(m.found_in_cad, m.input_state_code, m.state_code, m.ptd_state_code)]
    # reduction = notice value - latest CAD market value (positive = value went down after notice)
    m["reduction"] = m.notice_value - m.market_value
    m["reduction_pct"] = (m.reduction / m.notice_value).where(m.notice_value > 0).round(4)
    m["value_result"] = pd.Series(pd.NA, index=m.index, dtype=object)
    m.loc[m.reduction > 0, "value_result"] = "Reduced"
    m.loc[m.reduction == 0, "value_result"] = "No change"
    m.loc[m.reduction < 0, "value_result"] = "Increased"
    m["value_result"] = m.value_result.fillna("")
    m["roll_source"] = source
    m["roll_date"] = roll_date

    front = ["row_in_input", "account_number", "county_clean", "found_in_cad", "cad_account",
             "situs_address", "situs_city", "situs_zip",
             "res_or_com", "property_category", "state_code", "ptd_state_code", "state_code_desc",
             "notice_value", "market_value", "reduction", "reduction_pct", "value_result", "notice_source",
             "protested", "protest_outcome", "protest_final_value",
             "input_market_value", "market_value_diff", "input_state_code", "state_code_changed"]
    extra = [c for c in roll.columns if c not in front + ["key"]]
    cols = front + extra + ["roll_source", "roll_date"]
    m = m[cols].rename(columns={"county_clean": "county"})

    m.to_csv(folder / f"{slug}_active_accounts_2026.csv", index=False)
    m[m.found_in_cad.eq("N")].to_csv(folder / f"{slug}_not_found_2026.csv", index=False)

    f = m[m.found_in_cad.eq("Y")]
    s = (f.groupby(["res_or_com", "property_category", "ptd_state_code", "state_code"], dropna=False)
         .agg(accounts=("account_number", "size"), notice_value=("notice_value", "sum"),
              market_value=("market_value", "sum"), reduction=("reduction", "sum"),
              reduced_accounts=("value_result", lambda x: int(x.eq("Reduced").sum()))).reset_index()
         .sort_values(["res_or_com", "accounts"], ascending=[True, False]))
    s.insert(0, "county", county)
    s.to_csv(folder / f"{slug}_summary_2026.csv", index=False)

    print(f"[{county}] done in {time.time() - t0:.0f}s: {len(f):,} found, {len(m) - len(f):,} not found -> {folder}",
          flush=True)
    return m


def main(county, load_roll, source, roll_date):
    """Entry point used by each county script; exits non-zero on error so run_all.py reports it."""
    try:
        run(county, load_roll, source, roll_date)
    except Exception as e:
        print(f"[{county}] FAILED: {e!r}", file=sys.stderr, flush=True)
        raise
