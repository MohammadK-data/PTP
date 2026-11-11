"""Appeal vs. final values for a list of Denton property IDs.

    from denton_values import get_values
    df = get_values([176451, 8, 9])            # ints or zero-padded strings
    df = get_values(ids, out_csv="../output/my_ids_values.csv")

    from denton_values import get_values_from_file
    df = get_values_from_file("clients.csv")    # .txt / .csv / .xlsx -> clients_values.csv

Command line:
    python3 denton_values.py clients.csv [--id-col "Account"] [-o out.csv]
    python3 denton_values.py 176451 8 9

Columns returned (one row per prop_id):
    prop_id
    appraised_value    owners[].ownerValue.ownerNetAppraisedValue, summed over owners   protax JSON (2026-07-27)
    market_value       appeals[].initialMarketValue (first 2026 appeal)                 protax JSON
    final_value        appeals[].finalMarketValue (latest finalized 2026 appeal)        protax JSON
                       -> if the appeal wasn't finalized in the JSON (SCHEDULED / FILED, finalMarketValue 0):
                          market_value of the FINAL export's APPRAISAL_INFO (default 2026-3, 2026-10-14)
                       -> if not protested: market_value = final_value = current ownerMarketValue (reduction 0)
    final_source       'appeal', '2026-3 export' or 'no protest'
    owner_count, owner_pct   owners listed in the JSON record and their total ownerPct
    basis_adjusted     True when an appeal value was converted to the record's basis: on multi-owner
                       properties an appeal value can be the whole property or one owner's share while
                       ownerValue lists each owner's share (see basis_factor)
    reduction          market_value - final_value
    reduction_pct      (final_value - market_value) / final_value
    agent_id, agent_name          current appraisal (CA) agent, from the FINAL export
    arb_agent_id, arb_agent_name  current ARB agent, from the FINAL export
    appeal_id, appeal_type, appeal_status, appeal_count   2026 appeal(s) in the protax JSON
    has_appeal, in_final          False if no 2026 appeal / prop_id not in the final export

Appeal values: a property can have several 2026 appeals (e.g. AGREEMENT + CLERICAL) carrying the
same values; market_value comes from the earliest appealID, final_value from the latest finalized
one. CLERICAL appeal records are CAD corrections, not protests, and are ignored; a property whose
only 2026 record is CLERICAL counts as not protested.

Speed: the protax JSON (~21 GB) is read by seeking to each record via
output/protax_review/protax_index.csv (built once if missing). The final export's
APPRAISAL_INFO.TXT is scanned once and its needed columns cached in output/slim/.
"""

import csv
import json
import math
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DENTON = HERE.parent
DATA = DENTON / "Data"
SLIM_DIR = DENTON / "output" / "slim"

PROTAX_JSON = DATA / "Denton-protaxExport-20260727.json"
PROTAX_INDEX = DENTON / "output" / "protax_review" / "protax_index.csv"
FINAL_EXPORT = DATA / "2026-3"
APPEAL_YEAR = 2026
NOT_PROTEST = {"CLERICAL"}   # appeal statuses that are corrections, not protests

FIELDS = [
    "prop_id", "sup_num", "appraised_val", "market_value",
    "ca_agent_id", "ca_agent_name", "arb_agent_id", "arb_agent_name",
]
MONEY = ["appraised_val", "market_value"]
AGENT_IDS = ["ca_agent_id", "arb_agent_id"]


# ---------- final values + current agent (fixed-width APPRAISAL_INFO.TXT) ----------

def _info_file(export_dir):
    files = sorted(Path(export_dir).glob("*_APPRAISAL_INFO.TXT"))
    if len(files) != 1:
        raise FileNotFoundError(f"Expected one *_APPRAISAL_INFO.TXT in {export_dir}, found {len(files)}")
    return files[0]


def _slim(export_dir, rebuild=False):
    """Slim per-export table (FIELDS only), cached as CSV; one row per prop_id."""
    src = _info_file(export_dir)
    cache = SLIM_DIR / f"{src.stem}_slim.csv"
    if rebuild or not cache.exists() or cache.stat().st_mtime < src.stat().st_mtime:
        layout = {n: (s - 1, e) for n, s, e in
                  json.loads((HERE / "pacs_appraisal_export_layout.json").read_text())["APPRAISAL_INFO"]}
        slices = [layout[f] for f in FIELDS]
        SLIM_DIR.mkdir(parents=True, exist_ok=True)
        tmp = cache.with_suffix(".tmp")
        print(f"building {cache.name} from {src.name} (one-time scan)...")
        with open(src, "rb") as f, open(tmp, "w", newline="", encoding="utf-8") as out:
            w = csv.writer(out)
            w.writerow(FIELDS)
            for raw in f:
                line = raw.rstrip(b"\r\n").decode("latin-1")
                w.writerow([line[s:e].strip() for s, e in slices])
        tmp.replace(cache)

    df = pd.read_csv(cache, dtype=str, keep_default_na=False)
    df["prop_id"] = df["prop_id"].astype("int64")
    for c in MONEY:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    for c in AGENT_IDS:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64").replace(0, pd.NA)
    # One row per owner, each carrying that owner's share of the values (e.g. two 50% owners of a
    # 365,000 property show 182,500 each). Keep the latest supplement, sum the values across owners.
    df = df[df["sup_num"] == df.groupby("prop_id")["sup_num"].transform("max")]
    agents = df.replace({"": pd.NA}).groupby("prop_id")[[*AGENT_IDS, "ca_agent_name", "arb_agent_name"]].first()
    money = df.groupby("prop_id")[MONEY].sum(min_count=1)
    sup = df.groupby("prop_id")["sup_num"].first()
    return pd.concat([sup, money, agents], axis=1)


# ---------- appeal values (protax JSON, via byte-offset index) ----------

def _build_protax_index():
    """One pass over the JSON: byte offset/length of each top-level record (lines ' {' ... ' }[,]')."""
    print(f"building {PROTAX_INDEX.name} from {PROTAX_JSON.name} (one-time scan of ~21 GB)...")
    PROTAX_INDEX.parent.mkdir(parents=True, exist_ok=True)
    tmp = PROTAX_INDEX.with_suffix(".tmp")
    with open(PROTAX_JSON, "rb") as f, open(tmp, "w", newline="") as out:
        w = csv.writer(out)
        w.writerow(["pID", "offset", "length"])
        pos, start, pid = 0, None, None
        for line in f:
            s = line.rstrip(b"\r\n")
            if start is None and s == b" {":
                start, pid = pos, None
            elif start is not None and pid is None and s.startswith(b'  "pID":'):
                pid = int(s.split(b":", 1)[1].strip().rstrip(b","))
            elif start is not None and s in (b" }", b" },"):
                w.writerow([pid, start, pos + len(line) - start])
                start = None
            pos += len(line)
    tmp.replace(PROTAX_INDEX)


def _protax_offsets():
    if not PROTAX_INDEX.exists():
        _build_protax_index()
    idx = pd.read_csv(PROTAX_INDEX, usecols=["pID", "offset", "length"])
    return idx.drop_duplicates("pID").set_index("pID")


def _appeals(ids):
    idx = _protax_offsets()
    rows = []
    with open(PROTAX_JSON, "rb") as f:
        for pid in ids:
            if pid not in idx.index:
                continue
            off, length = idx.loc[pid, ["offset", "length"]]
            f.seek(int(off))
            rec = json.loads(f.read(int(length)).decode("utf-8").rstrip().rstrip(","))
            if rec.get("pID") != pid:
                raise ValueError(f"protax index is out of date (pID {pid}); delete {PROTAX_INDEX} to rebuild")
            # Net appraised: ownerValue holds each owner's share, so add it up across owners
            ovs = [o["ownerValue"][0] if isinstance(o.get("ownerValue"), list) and o["ownerValue"]
                   else o.get("ownerValue") or {} for o in rec.get("owners") or []]

            def owner_sum(key):
                vals = [v.get(key) for v in ovs if v.get(key) is not None]
                return sum(vals) if vals else None

            cur = owner_sum("ownerMarketValue")
            pcts = [o.get("ownerPct") or 0 for o in rec.get("owners") or []]
            pct = sum(pcts)
            row = {"prop_id": pid, "net_appraised": owner_sum("ownerNetAppraisedValue"),
                   "current_market": cur, "owner_count": len(pcts), "owner_pct": round(pct, 4) if pct else None}

            def basis_factor(v, initial=False):
                """Factor that puts an appeal value on the same basis as the current values (the total of the
                owners listed in the record). Each owner's ownerValue holds only that owner's share, while an
                appeal value can be for the listed owners, the whole property, or the one owner who appealed:
                  530958  only one 50% owner listed, final 332,146 = whole property      -> x0.5
                  6457    one 50% owner listed, initial 439,378 = whole property         -> x0.5
                  7554    two 50% owners listed, initial 122,610 = one owner's share     -> x2
                  586     two 50% owners listed, initial/final = whole = listed total    -> x1
                Picks the candidate basis that lands closest to the current market value (for the initial value,
                among those not below it)."""
                positive = [q for q in pcts if q > 0]
                if not v or not cur or not positive or (len(positive) == 1 and pct >= 99.99):
                    return 1.0
                cands = [1.0, pct / 100] + [pct / q for q in set(positive)]
                if initial:
                    # a protest doesn't raise the value: prefer bases where notice >= current (36804: 28/72% owners,
                    # initial 1,968,868 -> 28% share = 7,031,671 notice, not 72% = 2,734,539 below the 4,219,003 final)
                    cands = [f_ for f_ in cands if v * f_ >= cur - 2] or cands
                return min(cands, key=lambda f_: (abs(math.log(v * f_ / cur)), f_ != 1.0))

            def on_basis(v, f_):
                if v is None or f_ == 1.0:
                    return v
                x = v * f_
                return cur if abs(x - cur) <= 2 else round(x)

            # CLERICAL records are CAD value corrections, not protests (usually a copy of an AGREEMENT,
            # sometimes the only record, e.g. 1008022) -> ignored
            aps = sorted((a for a in rec.get("appeals") or [] if a.get("pYear") == APPEAL_YEAR
                          and (a.get("appealStatus") or "").strip() not in NOT_PROTEST),
                         key=lambda a: a["appealID"])
            if aps:
                # initial value from the first appeal; final from the latest finalized one
                # (unfinalized appeals, e.g. SCHEDULED / FILED, carry finalMarketValue = 0)
                done = [a for a in aps if a.get("finalized") and a.get("finalMarketValue")]
                fi = basis_factor(aps[0].get("initialMarketValue"), initial=True)
                ff = basis_factor(done[-1]["finalMarketValue"]) if done else 1.0
                row.update({
                    "initial_market": on_basis(aps[0].get("initialMarketValue"), fi),
                    "final_market": on_basis(done[-1]["finalMarketValue"], ff) if done else None,
                    "basis_adjusted": fi != 1.0 or ff != 1.0,
                    "appeal_id": aps[0].get("appealID"),
                    "appeal_type": aps[0].get("appealType"),
                    "appeal_status": " / ".join(dict.fromkeys((x.get("appealStatus") or "").strip() for x in aps)),
                    "appeal_count": len(aps),
                })
            rows.append(row)
    cols = ["prop_id", "net_appraised", "current_market", "owner_count", "owner_pct", "basis_adjusted",
            "initial_market", "final_market",
            "appeal_id", "appeal_type", "appeal_status", "appeal_count"]
    return pd.DataFrame(rows, columns=cols).set_index("prop_id")


# ---------- public ----------

def get_values(ids, final_export=FINAL_EXPORT, out_csv=None):
    ids = pd.Index(pd.unique(pd.Series(list(ids)).astype(str).str.strip().astype("int64")), name="prop_id")
    appeal = _appeals(ids).reindex(ids)
    final = _slim(final_export).reindex(ids)

    res = pd.DataFrame(index=ids)
    res["appraised_value"] = appeal["net_appraised"].astype("Int64")
    res["market_value"] = appeal["initial_market"].astype("Int64")
    appeal_final = appeal["final_market"].astype("Int64")
    use_export = appeal["appeal_id"].notna() & appeal_final.isna()   # appeal not finalized in the JSON
    res["final_value"] = appeal_final.where(~use_export, final["market_value"])
    res["final_source"] = pd.Series(pd.NA, index=ids, dtype="string")
    res.loc[appeal_final.notna(), "final_source"] = "appeal"
    res.loc[use_export & final["market_value"].notna(), "final_source"] = "2026-3 export"
    # Not protested: market and final are both the current market value -> reduction 0
    no_protest = appeal["appeal_id"].isna() & appeal["current_market"].notna()
    cur = appeal["current_market"].astype("Int64")
    res.loc[no_protest, "market_value"] = cur[no_protest]
    res.loc[no_protest, "final_value"] = cur[no_protest]
    res.loc[no_protest, "final_source"] = "no protest"
    res["reduction"] = res["market_value"] - res["final_value"]
    fv = res["final_value"].astype("Float64")
    res["reduction_pct"] = ((fv - res["market_value"]) / fv.where(fv != 0)).round(4)
    res["agent_id"] = final["ca_agent_id"]
    res["agent_name"] = final["ca_agent_name"].replace("", pd.NA)
    res["arb_agent_id"] = final["arb_agent_id"]
    res["arb_agent_name"] = final["arb_agent_name"].replace("", pd.NA)
    res["appeal_id"] = appeal["appeal_id"].astype("Int64")
    res["appeal_type"] = appeal["appeal_type"]
    res["appeal_status"] = appeal["appeal_status"]
    res["appeal_count"] = appeal["appeal_count"].astype("Int64")
    res["owner_count"] = appeal["owner_count"].astype("Int64")
    res["owner_pct"] = appeal["owner_pct"]
    res["basis_adjusted"] = appeal["basis_adjusted"].fillna(False).astype(bool)
    res["has_appeal"] = appeal["appeal_id"].notna()
    res["in_final"] = final["sup_num"].notna()
    res = res.reset_index()

    if out_csv:
        res.to_csv(out_csv, index=False)
    return res


ID_COLUMN_NAMES = ["prop_id", "propid", "pid", "property_id", "propertyid", "account", "account_id",
                   "accountid", "account_number", "id"]


def _clean_id(v):
    """'176451', '000000176451', '176,451', 176451.0 -> 176451; anything else -> None."""
    s = str(v).strip().replace(",", "")
    if s.endswith(".0"):
        s = s[:-2]
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
        raw = path.read_text().replace(",", " ").split()
        df = pd.DataFrame({"client_id": raw})
        col = "client_id"
    else:
        if ext == ".csv":
            df = pd.read_csv(path, dtype=str, keep_default_na=False)
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


def get_values_from_file(path, id_col=None, out_csv=None, final_export=FINAL_EXPORT):
    """Read a client ID list, look up every ID, and return the client rows with the values appended
    (same row order, duplicates kept). Saves to out_csv, default '<input name>_values.csv' next to the input."""
    path = Path(path)
    clients = read_client_ids(path, id_col)
    values = get_values(clients["prop_id"].dropna(), final_export=final_export)
    clients = clients.drop(columns=[c for c in values.columns if c in clients.columns and c != "prop_id"])
    res = clients.merge(values, on="prop_id", how="left")
    res["valid_id"] = res["prop_id"].notna()
    for c in ("has_appeal", "in_final"):
        res[c] = res[c].fillna(False).astype(bool)

    out_csv = Path(out_csv) if out_csv else path.with_name(f"{path.stem}_values.csv")
    res.to_csv(out_csv, index=False)
    print(f"{res['valid_id'].sum()} valid IDs | {res['in_final'].sum()} found in final export | "
          f"{res['has_appeal'].sum()} with a {APPEAL_YEAR} appeal | total reduction "
          f"{res['reduction'].sum():,}\nsaved {out_csv}")
    return res


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Appeal vs. final values for Denton property IDs.")
    p.add_argument("ids", nargs="+", help="a client file (.txt/.csv/.xlsx) or one or more IDs")
    p.add_argument("--id-col", help="ID column name in a .csv/.xlsx (default: auto-detect)")
    p.add_argument("-o", "--out", help="output CSV (default: <input>_values.csv next to the input file)")
    a = p.parse_args()
    if len(a.ids) == 1 and Path(a.ids[0]).is_file():
        get_values_from_file(a.ids[0], id_col=a.id_col, out_csv=a.out)
    else:
        res = get_values(a.ids, out_csv=a.out)
        print(res.to_string(index=False))
