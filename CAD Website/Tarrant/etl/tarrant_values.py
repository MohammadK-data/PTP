"""Appeal vs. final values for a list of Tarrant account numbers -- same interface as travis_values.py /
denton_values.py / montgomery_values.py.

Sources (CAD Website/Tarrant/Data):
    ORR20261019 - ... ARB Info 2026.csv     every 2026 protest case (open records request, Oct 19)
    ORR20261019 - ... ARB Info 2025.csv     only to name agent IDs that have no name on a 2026 case
    PropertyData(Delimited)_2026.txt        full 2026 roll, all property types (Oct 26)
    PropertyData(Delimited)_R_2026.txt      newer residential-only roll (Nov 11)
    000_Tarrant_All_Taxing_Units/<date>_2026_APPRAISAL_INFO.TXT
                                            PACS appraisal export (certified + supplements, Nov 13), newest file
                                            picked by name: latest roll values and agents of record (R / P / MH)
    AgentSummaryData_2025/AgentSummaryData_1_Account.txt
                                            despite the folder name, tax year 2026 (Oct 27): notice appraised value
The rolls and the export are scanned once and their needed columns cached in output/slim/ (rebuilt when the
file changes). Roll values come from the export first, then the Nov R roll, then the Oct roll.

    from tarrant_values import get_values, get_values_from_file
    df = get_values([14848347, "06396593"])         # ints or zero-padded strings
    df = get_values_from_file("clients.csv")      # .txt / .csv / .xlsx -> clients_values.csv

Command line:
    .venv/bin/python "CAD Website/Tarrant/etl/tarrant_values.py" clients.csv [--id-col "Account #"] [-o out.csv]
    .venv/bin/python "CAD Website/Tarrant/etl/tarrant_values.py" 14848347 6396593

Columns returned (one row per prop_id = Account_Num without leading zeros):
    prop_id
    appraised_value    2026 notice appraised value (after the homestead / circuit-breaker cap) = market_value
                       limited by the year's cap ceiling: Agent Summary AppraisedValue where it is below its
                       MarketValue, else the export's assessed_val where the export still shows a cap
    appraised_source   'agent summary', 'export cap' or 'notice market (no cap data)'
    final_appraised_value  current (post-protest, capped) appraised value: export assessed_val, else roll
                       Appraised_Value
    market_value       ARB NoticeMarketValue = 2026 notice market value
                       -> notice value missing/0 on a case without a result: latest roll value
                       -> not protested: market_value = final_value = latest roll value (reduction 0)
    final_value        ARB finalMarketValue (case resolved: joint motion / ARB order / 25.25)
                       -> case open, or closed without a result (FTA, withdrawn, dismissed), or resolved with
                          finalMarketValue 0: latest roll value (roll_value)
    final_source       'appeal', 'roll (case open)', 'roll (no result: FTA / withdrawn / dismissed)',
                       'roll (no final value)' or 'no protest'
    reduction          market_value - final_value
    reduction_pct      (final_value - market_value) / final_value   (same convention as the other counties)
    agent_id, agent_name   agents on the account's 2026 cases (' | ' if several): who filed
    is_ours            a case lists agentID 1487 (Property Tax Protest), or 1487 is an agent of record in the export
    appeal_id          CaseNumber of the case that decided the value (ours first, then resolved > open > no result,
                       then latest finalizedDt / filing date / CaseNumber -- see tarrant_arb_values_2026.dedup_arb)
    appeal_type        AppellantType of that case (Agent / Owner / Other)
    appeal_status      CaseStatus of that case first, then any other statuses on the account (' / ')
    appeal_count       distinct 2026 cases on the account
    path               Informal (joint motion), ARB hearing, Open, Failure to appear, Withdrawn / dismissed
    property_type      RP: R residential, C commercial, P business personal property, M mobile home
    roll_value         latest roll value: export market_value (owner rows summed), else Nov / Oct roll Total_Value
                       (should equal final_value once the case is closed, unless post_final_change)
    roll_source        'export <date>', 'Nov R roll' or 'Oct roll'
    post_final_change  final_value is the ARB final but the export has since moved the value more than $3
                       (a supplement after the case closed) -> roll_value is the newer value
    agent_of_record_id/name, arb_agent_of_record_id/name
                       appraisal (CA) and ARB agents of record in the export: who holds the appointment today
    check_values       protested and market_value missing/<=0, or final more than 25% above notice -> look by hand
    has_appeal, found  False if no 2026 case / account not in either roll or the ARB file. Mobile homes (M) are
                       in the roll with blank values, so their values come back empty unless the case has them

"Protest Setup in Error" and "Filed Untimely" cases are not protests and are ignored (like Denton's CLERICAL);
an account whose only 2026 cases are those counts as not protested.
"""

import csv
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))           # so tarrant_arb_values_2026 imports when used from another folder
from tarrant_arb_values_2026 import NOT_PROTEST, OPEN, RESOLVED, dedup_arb, path_of  # noqa: E402

TARRANT = HERE.parent
DATA = TARRANT / "Data"
SLIM_DIR = TARRANT / "output" / "slim"

ARB = DATA / "ORR20261019 - Avetik Ghazaryan - ARB Info 2026.csv"
ARB_2025 = DATA / "ORR20261019 - Avetik Ghazaryan - ARB Info 2025.csv"
ROLL = DATA / "PropertyData(Delimited)_2026.txt"
ROLL_R = DATA / "PropertyData(Delimited)_R_2026.txt"
EXPORT_DIR = DATA / "000_Tarrant_All_Taxing_Units"
# the folder is named 2025 but holds tax year 2026 (downloaded Oct 27); MarketValue = notice market on ~95% of
# protested accounts, AppraisedValue = notice appraised after the cap
AGENT_SUMMARY = DATA / "AgentSummaryData_2025" / "AgentSummaryData_1_Account.txt"
APPEAL_YEAR = 2026
OUR_AGENT_ID = "1487"
ROLL_FIELDS = ["Account_Num", "RP", "Total_Value", "Appraised_Value", "Instrument_No"]

# APPRAISAL_INFO.TXT, PACS appraisal export (TP_Legacy8.0.32-AppraisalExportLayout.xlsx, sheet Property):
# fixed width, 1-based inclusive positions
EXPORT_FIELDS = [
    ("prop_id", 1, 12), ("prop_type_cd", 13, 17), ("prop_val_yr", 18, 22), ("sup_num", 23, 34),
    ("appraised_val", 1916, 1930), ("ten_percent_cap", 1931, 1945), ("assessed_val", 1946, 1960),
    ("ca_agent_id", 3204, 3215), ("ca_agent_name", 3216, 3285),
    ("arb_agent_id", 3616, 3627), ("arb_agent_name", 3628, 3697),
    ("market_value", 4214, 4227),
]


def num(s):
    return pd.to_numeric(s, errors="coerce")


def latest_export():
    """Newest *_APPRAISAL_INFO.TXT in EXPORT_DIR (file names start with the export date), or None."""
    files = sorted(EXPORT_DIR.glob("*_APPRAISAL_INFO.TXT"))
    return files[-1] if files else None


# ---------- appraisal export (fixed width, cached slim) ----------

def _slim_export(src, rebuild=False):
    """prop_id -> export values and agents of record. Undivided-interest accounts have one row per owner with
    the value split by ownership share: the rows are summed. Minerals (MN) are dropped. A market value of 0 is
    treated as missing (93 accounts, mostly supplement 500000) so the roll is used instead."""
    cache = SLIM_DIR / f"{src.stem}_slim.csv"
    if rebuild or not cache.exists() or cache.stat().st_mtime < src.stat().st_mtime:
        print(f"building {cache.name} from {src.name} (one-time scan)...")
        SLIM_DIR.mkdir(parents=True, exist_ok=True)
        tmp = cache.with_suffix(".tmp")
        with open(src, encoding="latin-1") as f, open(tmp, "w", newline="", encoding="utf-8") as out:
            w = csv.writer(out)
            w.writerow([k for k, _, _ in EXPORT_FIELDS])
            for line in f:
                if line[12:17].strip() == "MN":
                    continue
                w.writerow([line[s - 1:e].strip() for _, s, e in EXPORT_FIELDS])
        tmp.replace(cache)

    df = pd.read_csv(cache, dtype=str, keep_default_na=False)
    df["prop_id"] = num(df["prop_id"]).astype("Int64")
    for c in ("sup_num", "market_value", "appraised_val", "assessed_val", "ten_percent_cap"):
        df[c] = num(df[c]).astype("Int64")
    for c in ("ca_agent_id", "arb_agent_id"):
        df[c] = df[c].str.lstrip("0")
    df = df[df["sup_num"].eq(df.groupby("prop_id")["sup_num"].transform("max"))]
    g = df.groupby("prop_id")
    res = g[["market_value", "appraised_val", "assessed_val", "ten_percent_cap"]].sum(min_count=1)
    first = g[["prop_type_cd", "sup_num", "ca_agent_id", "ca_agent_name", "arb_agent_id", "arb_agent_name"]].first()
    res = res.join(first)
    res["owner_rows"] = g.size()
    res["market_value"] = res["market_value"].where(res["market_value"] > 0)
    res["appraised_val"] = res["appraised_val"].where(res["market_value"].notna())
    for c in ("ca_agent_id", "ca_agent_name", "arb_agent_id", "arb_agent_name"):
        res[c] = res[c].replace("", None)
    return res


# ---------- roll (pipe-delimited, cached slim) ----------

def _agent_summary():
    """prop_id -> 2026 Agent Summary MarketValue, AppraisedValue (UTF-16, pipe). Empty if the file is missing
    or isn't tax year 2026."""
    cols = ["MarketValue", "AppraisedValue"]
    empty = pd.DataFrame(columns=cols, index=pd.Index([], name="prop_id", dtype="int64"), dtype="Int64")
    if not AGENT_SUMMARY.exists():
        return empty
    df = pd.read_csv(AGENT_SUMMARY, sep="|", encoding="utf-16", dtype=str, keep_default_na=False,
                     usecols=["TaxYear", "AccountNumber"] + cols)
    df = df[num(df["TaxYear"]).eq(APPEAL_YEAR)]
    if df.empty:
        return empty
    df["prop_id"] = num(df["AccountNumber"].str.lstrip("0")).astype("Int64")
    df = df.dropna(subset=["prop_id"]).drop_duplicates("prop_id")
    for c in cols:
        df[c] = num(df[c]).astype("Int64")
    return df.set_index("prop_id")[cols]


def _split(line, n):
    """Same repair as tarrant_arb_values_2026.load_roll: a few rows carry ' | ' inside a text field."""
    parts = line.rstrip("\r\n").split("|")
    if len(parts) != n:
        extra = len(parts) - n
        for j in range(len(parts) - 1):
            if extra > 0 and parts[j].endswith(" ") and parts[j + 1].startswith(" "):
                parts[j:j + extra + 1] = ["|".join(parts[j:j + extra + 1])]
                break
        parts = (parts + [""] * n)[:n]
    return parts


def _slim_roll(src, rebuild=False):
    """Account_Num -> RP, Total_Value, Appraised_Value. One row per account: duplicates (one per deed
    instrument, values identical) keep the latest Instrument_No."""
    cache = SLIM_DIR / f"{src.stem}_slim.csv"
    if rebuild or not cache.exists() or cache.stat().st_mtime < src.stat().st_mtime:
        print(f"building {cache.name} from {src.name} (one-time scan)...")
        SLIM_DIR.mkdir(parents=True, exist_ok=True)
        tmp = cache.with_suffix(".tmp")
        with open(src, encoding="latin-1") as f, open(tmp, "w", newline="", encoding="utf-8") as out:
            hdr = [h.strip() for h in f.readline().rstrip("\r\n").split("|")]
            pos = [hdr.index(c) for c in ROLL_FIELDS]
            w = csv.writer(out)
            w.writerow(ROLL_FIELDS)
            for line in f:
                parts = _split(line, len(hdr))
                w.writerow([parts[i].strip() for i in pos])
        tmp.replace(cache)

    df = pd.read_csv(cache, dtype=str, keep_default_na=False)
    df["prop_id"] = num(df["Account_Num"].str.lstrip("0")).astype("Int64")
    df = df.dropna(subset=["prop_id"])
    df = df.sort_values(["prop_id", "Instrument_No"], ascending=[True, False], kind="stable").drop_duplicates("prop_id")
    for c in ("Total_Value", "Appraised_Value"):
        df[c] = num(df[c]).astype("Int64")
    return df.set_index("prop_id")[["RP", "Total_Value", "Appraised_Value"]]


# ---------- ARB cases ----------

def _agent_names():
    """agentID -> most common AppellantName on Agent-type cases (2026, then 2025 for IDs missing in 2026)."""
    names = {}
    for path in (ARB, ARB_2025):
        if not path.exists():
            continue
        x = pd.read_csv(path, dtype=str, keep_default_na=False, usecols=["agentID", "AppellantType", "AppellantName"])
        x = x[x.AppellantType.eq("Agent") & x.agentID.str.strip().ne("") & x.AppellantName.str.strip().ne("")]
        for k, v in x.groupby(x.agentID.str.strip()).AppellantName.agg(lambda s: s.value_counts().index[0]).items():
            names.setdefault(k, v.strip())
    return names


def _cases(ids):
    """One row per account with a real 2026 case: the deciding case plus account-level agent / status lists."""
    a = pd.read_csv(ARB, dtype=str).drop_duplicates()
    a = a[num(a.pYear).eq(APPEAL_YEAR)].copy()
    a["prop_id"] = num(a.pID.str.strip().str.lstrip("0")).astype("Int64")
    a = a[a.prop_id.isin(ids) & ~a.CaseStatus.isin(NOT_PROTEST)].copy()
    if a.empty:
        cols = ["CaseStatus", "CaseNumber", "AppellantType", "NoticeMarketValue", "finalMarketValue", "is_ours",
                "agent_id", "agent_name", "appeal_count", "appeal_status"]
        return pd.DataFrame(columns=cols, index=pd.Index([], name="prop_id", dtype="Int64"), dtype=object)
    a["agentID"] = a.agentID.str.strip()
    pick = dedup_arb(a).set_index("prop_id")

    names = _agent_names()
    g = a.groupby("prop_id")
    agent_ids = g.agentID.agg(lambda s: sorted(set(s.dropna()) - {""}, key=lambda x: (x != OUR_AGENT_ID, int(x) if x.isdigit() else 0)))
    pick["agent_id"] = agent_ids.map(lambda l: " | ".join(l) or None)
    pick["agent_name"] = agent_ids.map(lambda l: " | ".join(names.get(x, "") for x in l if names.get(x)) or None)
    pick["appeal_count"] = g.CaseNumber.nunique()
    others = g.CaseStatus.agg(lambda s: list(dict.fromkeys(s.dropna())))
    pick["appeal_status"] = [" / ".join(dict.fromkeys([st] + others[p])) for p, st in zip(pick.index, pick.CaseStatus)]
    return pick


# ---------- public ----------

COLS = ["prop_id", "appraised_value", "appraised_source", "market_value", "final_value", "final_appraised_value",
        "final_source", "reduction", "reduction_pct",
        "agent_id", "agent_name", "is_ours", "appeal_id", "appeal_type", "appeal_status", "appeal_count", "path",
        "property_type", "roll_value", "roll_source", "post_final_change", "agent_of_record_id",
        "agent_of_record_name", "arb_agent_of_record_id", "arb_agent_of_record_name", "check_values",
        "has_appeal", "found"]


def get_values(ids, out_csv=None):
    ids = pd.Index(pd.unique(pd.Series(list(ids)).astype(str).str.strip().str.lstrip("0").astype("int64")),
                   name="prop_id")
    oct_ = _slim_roll(ROLL).reindex(ids)
    nov = _slim_roll(ROLL_R).reindex(ids)
    src = latest_export()
    exp_cols = ["market_value", "appraised_val", "prop_type_cd", "ca_agent_id", "ca_agent_name", "arb_agent_id",
                "arb_agent_name"]
    exp = (_slim_export(src) if src else pd.DataFrame(columns=exp_cols)).reindex(ids)
    case = _cases(ids).reindex(ids)

    # latest roll value: appraisal export -> Nov R roll -> Oct roll
    res = pd.DataFrame(index=ids)
    in_exp = exp["market_value"].notna()
    in_nov = ~in_exp & nov["Total_Value"].notna()
    in_oct = ~in_exp & ~in_nov & oct_["Total_Value"].notna()
    roll = (exp["market_value"].where(in_exp, nov["Total_Value"].where(in_nov, oct_["Total_Value"]))).astype("Int64")
    # current (post-protest) appraised value after the homestead / circuit-breaker cap = export assessed_val
    res["final_appraised_value"] = (exp["assessed_val"].where(
        in_exp, nov["Appraised_Value"].where(in_nov, oct_["Appraised_Value"]))).astype("Int64")
    # roll RP keeps the commercial (C) split the export doesn't have; export-only accounts use its type (MH -> M)
    rp = nov["RP"].where(nov["RP"].notna() & nov["RP"].ne(""), oct_["RP"]).replace("", None)
    res["property_type"] = rp.where(rp.notna(), exp["prop_type_cd"].replace({"MH": "M"}))
    res["roll_value"] = roll
    res["roll_source"] = pd.Series(pd.NA, index=ids, dtype="string")
    res.loc[in_exp, "roll_source"] = f"export {src.name[:10]}" if src else pd.NA
    res.loc[in_nov, "roll_source"] = "Nov R roll"
    res.loc[in_oct, "roll_source"] = "Oct roll"

    status = case["CaseStatus"]
    has = status.notna()
    resolved = status.isin(RESOLVED)
    notice = num(case["NoticeMarketValue"]).astype("Int64")
    notice = notice.where(notice > 0)
    final = num(case["finalMarketValue"]).astype("Int64")
    final = final.where(resolved & (final > 0))

    # notice: from the case; missing on a case with no result -> the roll (value didn't change)
    res["market_value"] = notice.where(notice.notna() | resolved, roll).where(has, roll)
    res["final_value"] = final.where(final.notna(), roll)
    # notice appraised value = notice market limited by the year's cap ceiling. The ceiling doesn't move with a
    # protest: Agent Summary AppraisedValue when it is below its MarketValue (cap or ag binding), else the export's
    # assessed_val when the export still shows a cap; no ceiling -> appraised = notice market.
    ag = _agent_summary().reindex(ids)
    in_ag = ag["MarketValue"].notna()
    ag_cap = ag["AppraisedValue"].where(ag["AppraisedValue"] < ag["MarketValue"])
    exp_cap = exp["assessed_val"].where(exp["ten_percent_cap"] > 0)
    ceiling = ag_cap.where(in_ag, exp_cap).astype("Int64")
    mv0 = res["market_value"]
    res["appraised_value"] = mv0.where(ceiling.isna() | (mv0 <= ceiling).fillna(True), ceiling).astype("Int64")
    res["appraised_source"] = pd.Series(pd.NA, index=ids, dtype="string")
    res.loc[mv0.notna() & in_ag, "appraised_source"] = "agent summary"
    res.loc[mv0.notna() & ~in_ag & exp_cap.notna(), "appraised_source"] = "export cap"
    res.loc[mv0.notna() & ~in_ag & exp_cap.isna(), "appraised_source"] = "notice market (no cap data)"

    res["final_source"] = pd.Series(pd.NA, index=ids, dtype="string")
    res.loc[final.notna(), "final_source"] = "appeal"
    fb = has & final.isna() & roll.notna()
    res.loc[fb & status.isin(OPEN), "final_source"] = "roll (case open)"
    res.loc[fb & ~status.isin(OPEN) & ~resolved, "final_source"] = "roll (no result: FTA / withdrawn / dismissed)"
    res.loc[fb & resolved, "final_source"] = "roll (no final value)"
    res.loc[~has & roll.notna(), "final_source"] = "no protest"

    res["reduction"] = res["market_value"] - res["final_value"]
    fv = res["final_value"].astype("Float64")
    res["reduction_pct"] = ((fv - res["market_value"]) / fv.where(fv != 0)).round(4)
    # a supplement after the case closed moved the roll away from the ARB final value (final_value is kept)
    res["post_final_change"] = (res["final_source"].eq("appeal") & in_exp
                                & ((roll - final).abs() > 3).fillna(False)).astype(bool)
    res["agent_id"] = case["agent_id"]
    res["agent_name"] = case["agent_name"]
    res["agent_of_record_id"] = exp["ca_agent_id"]
    res["agent_of_record_name"] = exp["ca_agent_name"]
    res["arb_agent_of_record_id"] = exp["arb_agent_id"]
    res["arb_agent_of_record_name"] = exp["arb_agent_name"]
    res["is_ours"] = (case["is_ours"].fillna(False).astype(bool) | exp["ca_agent_id"].eq(OUR_AGENT_ID).fillna(False)
                      | exp["arb_agent_id"].eq(OUR_AGENT_ID).fillna(False))
    res["appeal_id"] = num(case["CaseNumber"]).astype("Int64")
    res["appeal_type"] = case["AppellantType"]
    res["appeal_status"] = case["appeal_status"]
    res["appeal_count"] = case["appeal_count"].astype("Int64")
    res["path"] = status.map(path_of, na_action="ignore")
    mv = res["market_value"].astype("Float64")
    res["check_values"] = has & (mv.isna() | (mv <= 0).fillna(False) | (fv > mv * 1.25).fillna(False))
    res["has_appeal"] = has
    res["found"] = has | res["property_type"].notna()     # mobile homes (M) can be in the roll with blank values
    res = res.reset_index()[COLS]

    if out_csv:
        res.to_csv(out_csv, index=False)
    return res


ID_COLUMN_NAMES = ["prop_id", "account_#", "account_num", "account", "account_id", "accountid", "account_number",
                   "propid", "pid", "property_id", "propertyid", "id"]


def _clean_id(v):
    """'06396593', '6,396,593', 6396593.0 -> 6396593; anything else -> None."""
    s = str(v).strip().replace(",", "")
    if s.endswith(".0"):
        s = s[:-2]
    s = s.lstrip("0")
    return int(s) if s.isdigit() else None


def read_client_ids(path, id_col=None):
    """Client list -> DataFrame with the original columns plus 'prop_id' (blank where the ID isn't valid).

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
        if id_col is None:
            norm = {c.strip().lower().replace(" ", "_"): c for c in df.columns}
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
    for c in ("has_appeal", "found", "is_ours", "check_values", "post_final_change"):
        res[c] = res[c].fillna(False).astype(bool)

    out_csv = Path(out_csv) if out_csv else path.with_name(f"{path.stem}_values.csv")
    res.to_csv(out_csv, index=False)
    print(f"{res['valid_id'].sum()} valid IDs | {res['found'].sum()} found | {res['has_appeal'].sum()} with a "
          f"{APPEAL_YEAR} case ({res['is_ours'].sum()} ours) | {res['check_values'].sum()} to check | total reduction "
          f"{res['reduction'].sum():,}\nsaved {out_csv}")
    return res


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Appeal vs. final values for Tarrant account numbers.")
    p.add_argument("ids", nargs="+", help="a client file (.txt/.csv/.xlsx) or one or more account numbers")
    p.add_argument("--id-col", help="ID column name in a .csv/.xlsx (default: auto-detect)")
    p.add_argument("-o", "--out", help="output CSV (default: <input>_values.csv next to the input file)")
    a = p.parse_args()
    if len(a.ids) == 1 and Path(a.ids[0]).is_file():
        get_values_from_file(a.ids[0], id_col=a.id_col, out_csv=a.out)
    else:
        pd.set_option("display.width", 250)
        pd.set_option("display.max_columns", 30)
        print(get_values(a.ids, out_csv=a.out).to_string(index=False))
