"""Appeal vs. final values for a list of Bexar property IDs -- same interface as travis_values.py /
denton_values.py / tarrant_values.py.

Sources (CAD Website/Bexar/output, built by the existing ETLs):
    bexar_arb_2022_2026.csv.gz                 every protest, from the BCAD agent export ARB file (Oct 26)
                                               -> bexar_arb_extract.py
    2026-10-15_2026_APPRAISAL_INFO.csv.gz      appraisal export Sup 298 (Oct 15): current values and agents of record
                                               -> bexar_appraisal_export_etl.py
The appraisal export's needed columns are cached once in output/slim/ (rebuilt when the file changes).

    from bexar_values import get_values, get_values_from_file
    df = get_values([100012, "000000100031"])      # BCAD prop_id (not the geo_id 00002-000-0020)
    df = get_values_from_file("clients.csv")      # .txt / .csv / .xlsx -> clients_values.csv

Command line:
    .venv/bin/python "CAD Website/Bexar/etl/bexar_values.py" clients.csv [--id-col account_number] [-o out.csv]
    .venv/bin/python "CAD Website/Bexar/etl/bexar_values.py" 100012 100031

Columns returned (one row per prop_id):
    prop_id
    appraised_value    ARB begin_assessed = notice appraised (after the homestead cap)
                       -> not protested: roll assessed_val
    market_value       ARB begin_market = 2026 notice market value
                       -> not protested: market_value = final_value = roll market_value (reduction 0)
    final_value        ARB final_market (case closed: informal, ARB order, no-show, withdrawn, other)
                       -> case still open (OP, RO, MO, FO-RESCHD, ...) or no final value: roll market_value (Oct 15)
    final_source       'appeal', 'roll (case open)', 'roll (no final value)' or 'no protest'
    reduction          market_value - final_value
    reduction_pct      (final_value - market_value) / final_value   (same convention as the other counties)
    agent_id, agent_name          appraisal (CA) agent of record on the Oct 15 roll
    arb_agent_id, arb_agent_name  ARB agent of record on the Oct 15 roll
    is_ours            the deciding protest was filed by PROPERTY TAX PROTEST
    case_agent         agent_name on the deciding protest (who filed it)
    appeal_id          case_id of the protest that decided the value (ours first, then closed over open,
                       settled over no-show / withdrawn, then the lowest final value -- as bexar_values_build.py)
    appeal_type        prot_by_type of that protest (AG agent, ANR, OW owner, ...)
    appeal_status      prot_status of that protest first, then any other statuses on the account (' / ')
    appeal_count       2026 value protests on the account
    path               Informal, ARB, No-show, Withdrawn, Other, Open (bexar_values_build.path_of)
    property_type      prop_type_cd (R real, P personal, MH mobile home, MN mineral)
    roll_value         Oct 15 roll market_value (equals final_value on ~99% of closed protests)
    check_values       protested and notice missing/<=0, or final more than 25% above notice -> look by hand
    has_appeal, found  False if no 2026 value protest / prop_id not in the roll or the ARB file

Only value protests (prot_type 25PROT) count. Exemption protests (25EX46.66), 25.25 motions, ADR / arbitration
records and DELDUP (duplicate, deleted) protests are ignored.
"""

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))           # so bexar_values_build imports when used from another folder
from bexar_values_build import US_NAME, path_of  # noqa: E402

BEXAR = HERE.parent
OUT = BEXAR / "output"
SLIM_DIR = OUT / "slim"
ARB = OUT / "bexar_arb_2022_2026.csv.gz"
ROLL = OUT / "2026-10-15_2026_APPRAISAL_INFO.csv.gz"
APPEAL_YEAR = "2026"
ROLL_FIELDS = ["prop_id", "sup_num", "prop_type_cd", "market_value", "assessed_val",
               "ca_agent_id", "ca_agent_name", "arb_agent_id", "arb_agent_name"]


def num(s):
    return pd.to_numeric(s, errors="coerce")


def _pid(s):
    return num(s.astype(str).str.strip().str.lstrip("0")).astype("Int64")


# ---------- roll (Oct 15 appraisal export, cached slim) ----------

def _slim_roll(rebuild=False):
    cache = SLIM_DIR / f"{ROLL.name.removesuffix('.csv.gz')}_slim.csv"
    if rebuild or not cache.exists() or cache.stat().st_mtime < ROLL.stat().st_mtime:
        print(f"building {cache.name} from {ROLL.name} (one-time read)...")
        SLIM_DIR.mkdir(parents=True, exist_ok=True)
        r = pd.read_csv(ROLL, dtype=str, keep_default_na=False, usecols=ROLL_FIELDS)
        tmp = cache.with_suffix(".tmp")
        r.to_csv(tmp, index=False)
        tmp.replace(cache)
    r = pd.read_csv(cache, dtype=str, keep_default_na=False)
    r["prop_id"] = _pid(r.prop_id)
    r["sup"] = num(r.sup_num)
    r = r.dropna(subset=["prop_id"]).sort_values(["prop_id", "sup"]).drop_duplicates("prop_id", keep="last")
    for c in ("market_value", "assessed_val", "ca_agent_id", "arb_agent_id"):
        r[c] = num(r[c]).astype("Int64")
    for c in ("ca_agent_id", "arb_agent_id"):
        r[c] = r[c].replace(0, pd.NA)
    for c in ("ca_agent_name", "arb_agent_name"):
        r[c] = r[c].str.strip().replace("", pd.NA)
    return r.set_index("prop_id")


# ---------- protests (agent export ARB file) ----------

def _protests(ids):
    a = pd.read_csv(ARB, dtype=str, keep_default_na=False)
    a = a[a.year.eq(APPEAL_YEAR) & a.prot_type.eq("25PROT")].copy()
    a["prop_id"] = _pid(a.prop_id)
    a = a[a.prop_id.isin(ids)].copy()
    a["path"] = a.prot_status.map(path_of)
    a = a[a.path.ne("Not a protest")].copy()
    if a.empty:
        return pd.DataFrame(columns=["case_id", "prot_status", "prot_by_type", "agent_name", "path", "ours",
                                     "bM", "bA", "fM", "appeal_count", "appeal_status"],
                            index=pd.Index([], name="prop_id", dtype="Int64"))
    a["ours"] = a.agent_name.eq(US_NAME)
    a["bM"], a["bA"], a["fM"] = num(a.begin_market), num(a.begin_assessed), num(a.final_market)
    a["open"] = a.path.eq("Open")
    a["rk"] = a.path.map({"Informal": 0, "ARB": 0, "Other": 1, "Open": 2}).fillna(1)

    # same pick as bexar_values_build.py: ours first, then closed over open, settled over no-show / withdrawn,
    # then the lowest final value
    ours_p = set(a.loc[a.ours, "prop_id"])
    cand = a[~a.prop_id.isin(ours_p) | a.ours]
    pick = cand.sort_values(["prop_id", "open", "rk", "fM"]).drop_duplicates("prop_id").set_index("prop_id")
    g = a.groupby("prop_id")
    pick["appeal_count"] = g.case_id.nunique()
    others = g.prot_status.agg(lambda s: list(dict.fromkeys(s)))
    pick["appeal_status"] = [" / ".join(dict.fromkeys([st] + others[p])) for p, st in zip(pick.index, pick.prot_status)]
    return pick


# ---------- public ----------

COLS = ["prop_id", "appraised_value", "market_value", "final_value", "final_source", "reduction", "reduction_pct",
        "agent_id", "agent_name", "arb_agent_id", "arb_agent_name", "is_ours", "case_agent", "appeal_id",
        "appeal_type", "appeal_status", "appeal_count", "path", "property_type", "roll_value", "check_values",
        "has_appeal", "found"]


def get_values(ids, out_csv=None):
    ids = pd.Index(pd.unique(_pid(pd.Series(list(ids))).dropna().astype("int64")), name="prop_id")
    roll = _slim_roll().reindex(ids)
    case = _protests(ids).reindex(ids)

    res = pd.DataFrame(index=ids)
    cur = roll["market_value"]
    has = case["prot_status"].notna()
    is_open = case["path"].eq("Open").fillna(False).astype(bool)
    notice = num(case["bM"]).astype("Int64")
    final = num(case["fM"]).astype("Int64")
    final = final.where(~is_open & (final > 0))

    res["appraised_value"] = num(case["bA"]).astype("Int64").where(has, roll["assessed_val"])
    res["market_value"] = notice.where(has, cur)
    res["final_value"] = final.where(final.notna(), cur)
    res["final_source"] = pd.Series(pd.NA, index=ids, dtype="string")
    res.loc[final.notna(), "final_source"] = "appeal"
    fb = has & final.isna() & cur.notna()
    res.loc[fb & is_open, "final_source"] = "roll (case open)"
    res.loc[fb & ~is_open, "final_source"] = "roll (no final value)"
    res.loc[~has & cur.notna(), "final_source"] = "no protest"

    res["reduction"] = res["market_value"] - res["final_value"]
    fv = res["final_value"].astype("Float64")
    mv = res["market_value"].astype("Float64")
    res["reduction_pct"] = ((fv - mv) / fv.where(fv != 0)).round(4)
    res["agent_id"] = roll["ca_agent_id"]
    res["agent_name"] = roll["ca_agent_name"]
    res["arb_agent_id"] = roll["arb_agent_id"]
    res["arb_agent_name"] = roll["arb_agent_name"]
    res["is_ours"] = case["ours"].fillna(False).astype(bool)
    res["case_agent"] = case["agent_name"].replace("", pd.NA)
    res["appeal_id"] = num(case["case_id"]).astype("Int64")
    res["appeal_type"] = case["prot_by_type"]
    res["appeal_status"] = case["appeal_status"]
    res["appeal_count"] = num(case["appeal_count"]).astype("Int64")
    res["path"] = case["path"]
    res["property_type"] = roll["prop_type_cd"]
    res["roll_value"] = cur
    res["check_values"] = has & (mv.isna() | (mv <= 0).fillna(False) | (fv > mv * 1.25).fillna(False))
    res["has_appeal"] = has
    res["found"] = has | roll["sup_num"].notna()
    res = res.reset_index()[COLS]

    if out_csv:
        res.to_csv(out_csv, index=False)
    return res


ID_COLUMN_NAMES = ["prop_id", "propid", "pid", "property_id", "propertyid", "account_number", "account_#",
                   "account", "account_id", "accountid", "id"]


def _clean_id(v):
    """'100012', '000000100012', '100,012', 100012.0 -> 100012; anything else (geo_id, blank) -> None."""
    s = str(v).strip().replace(",", "")
    if s.endswith(".0"):
        s = s[:-2]
    s = s.lstrip("0")
    return int(s) if s.isdigit() else None


def read_client_ids(path, id_col=None, county="Bexar"):
    """Client list -> DataFrame with the original columns plus 'prop_id' (blank where the ID isn't valid).
    A list with a 'county' column is filtered to Bexar rows.

    .txt  : IDs separated by whitespace/newlines/commas
    .csv  : column named id_col, or the first column matching ID_COLUMN_NAMES, or the first column
    .xlsx : same as .csv, first sheet (needs openpyxl)
    """
    path = Path(path)
    ext = path.suffix.lower()
    if ext in (".txt", ""):
        df = pd.DataFrame({"client_id": path.read_text().replace(",", " ").split()})
        col = "client_id"
    else:
        if ext == ".csv":
            df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(path, dtype=str).fillna("")
        else:
            raise ValueError(f"Unsupported file type {ext!r}; use .txt, .csv or .xlsx")
        norm = {c.strip().lower().replace(" ", "_"): c for c in df.columns}
        if county and "county" in norm:
            keep = df[norm["county"]].str.strip().str.lower().eq(county.lower())
            print(f"{path.name}: kept {keep.sum()} {county} rows of {len(df)}")
            df = df[keep]
        if id_col is None:
            id_col = next((norm[n] for n in ID_COLUMN_NAMES if n in norm), df.columns[0])
        elif id_col not in df.columns:
            raise KeyError(f"Column {id_col!r} not in {path.name}; columns are {list(df.columns)}")
        col = id_col
    df = df.copy()
    df["prop_id"] = df[col].map(_clean_id).astype("Int64")
    bad = df.loc[df["prop_id"].isna(), col].tolist()
    print(f"{path.name}: {len(df)} rows, ID column {col!r}, {len(bad)} not a valid ID"
          + (f" (e.g. {bad[:5]})" if bad else ""))
    return df


def get_values_from_file(path, id_col=None, out_csv=None):
    """Client rows (same order, duplicates kept) with the values appended; saved to out_csv,
    default '<input name>_values.csv' next to the input."""
    path = Path(path)
    clients = read_client_ids(path, id_col)
    values = get_values(clients["prop_id"].dropna())
    clients = clients.drop(columns=[c for c in values.columns if c in clients.columns and c != "prop_id"])
    res = clients.merge(values, on="prop_id", how="left")
    res["valid_id"] = res["prop_id"].notna()
    for c in ("has_appeal", "found", "is_ours", "check_values"):
        res[c] = res[c].fillna(False).astype(bool)

    out_csv = Path(out_csv) if out_csv else path.with_name(f"{path.stem}_values.csv")
    res.to_csv(out_csv, index=False)
    print(f"{res['valid_id'].sum()} valid IDs | {res['found'].sum()} found | {res['has_appeal'].sum()} with a "
          f"{APPEAL_YEAR} value protest ({res['is_ours'].sum()} ours) | {res['check_values'].sum()} to check | "
          f"total reduction {res['reduction'].sum():,}\nsaved {out_csv}")
    return res


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Appeal vs. final values for Bexar property IDs.")
    p.add_argument("ids", nargs="+", help="a client file (.txt/.csv/.xlsx) or one or more prop_ids")
    p.add_argument("--id-col", help="ID column name in a .csv/.xlsx (default: auto-detect)")
    p.add_argument("-o", "--out", help="output CSV (default: <input>_values.csv next to the input file)")
    a = p.parse_args()
    if len(a.ids) == 1 and Path(a.ids[0]).is_file():
        get_values_from_file(a.ids[0], id_col=a.id_col, out_csv=a.out)
    else:
        pd.set_option("display.width", 250)
        pd.set_option("display.max_columns", 30)
        print(get_values(a.ids, out_csv=a.out).to_string(index=False))
