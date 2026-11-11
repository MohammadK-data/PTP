"""Appeal vs. final values for a list of Montgomery property IDs -- from the protax JSON only.

Source: Data/Montgomery-protaxExport-20260804.json (~21 GB). Each property is read by seeking to it
via output/protax_review/protax_index_20260804.csv (built once, a few minutes, if missing;
shared with montgomery_lookup.py, which shows the full detail for one property).

    from montgomery_values import get_values, get_values_from_file
    df = get_values([1001, 1002])                 # pID, refID2, refID1 or geoID
    df = get_values_from_file("clients.csv")    # .txt / .csv / .xlsx -> clients_values.csv

Command line:
    python3 montgomery_values.py clients.csv [--id-col "Account"] [--id-type refID2] [-o out.csv]
    python3 montgomery_values.py 1001 1002

Columns returned (one row per prop_id):
    prop_id
    appraised_value    appeals[].initialAppraisedValue (first 2026 appeal) = notice appraised value
                       -> not protested: current owners[].ownerValue.ownerAppraisedValue (summed over owners)
    market_value       appeals[].initialMarketValue (first 2026 appeal) = notice market value
    final_value        appeals[].finalMarketValue (latest finalized 2026 appeal)
                       -> appeal not finalized yet (e.g. WH, EXP-NC, PROT-SCHD; finalMarketValue 0):
                          current market value (owners[].ownerValue.ownerMarketValue)
                       -> not protested: market_value = final_value = current market value (reduction 0)
    final_source       'appeal', 'current (appeal open)' or 'no protest'
    reduction          market_value - final_value
    reduction_pct      (final_value - market_value) / final_value
    agent_id, agent_name   current agent(s) on the property (owners[].agents, not expired); ' | ' if several
    appeal_id, appeal_type, appeal_status, appeal_count   2026 appeal(s)
    owner_count, owner_pct   owners listed in the record and their total ownerPct
    basis_adjusted     True when an appeal value was converted to the record's basis: Montgomery files appeals per
                       owner account, so on a multi-owner property the appeal's initial value is often one owner's
                       share while ownerValue lists every owner (see basis_factor)
    has_appeal, found  False if no 2026 appeal / prop_id not in the JSON

IDs: a client list can hold pIDs, refID2 (account numbers), refID1 (M...) or geoIDs. The ID type that matches
the most IDs is used and printed (pID and refID2 are both plain numbers); force one with --id-type.
Output has the client's columns plus prop_id (the pID) and matched_on.

Montgomery appeal types are PROT (protest) and 25.25D (motion to correct); statuses include TLCC, TLCNC,
DECISION.A, DECISION.D, SW, NS, HD.NAA, AC, EF_AC, EF_WD, ERR and, still open on 08-04, WH, EXP-NC, PROT-SCHD.
None of them is a clerical correction like Denton's CLERICAL, so every 2026 appeal counts.
"""

import json
import math
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))           # so montgomery_lookup imports when used from another folder
MONTGOMERY = HERE.parent
PROTAX_JSON = MONTGOMERY / "Data" / "Montgomery-protaxExport-20260804.json"
PROTAX_INDEX = MONTGOMERY / "output" / "protax_review" / "protax_index_20260804.csv"
APPEAL_YEAR = 2026
NOT_PROTEST = set()      # appeal statuses that are corrections, not protests (none known for Montgomery)
EXPORT_DATE = datetime(2026, 8, 4)


# ---------- byte-offset index into the JSON (shared with montgomery_lookup.py) ----------

def _offsets():
    import montgomery_lookup as lookup
    if not lookup.index_ok(str(PROTAX_JSON)):
        lookup.build_index(str(PROTAX_JSON))
    idx = pd.read_csv(PROTAX_INDEX, usecols=["pID", "offset", "length"])
    return idx.drop_duplicates("pID").set_index("pID")


# ---------- per-record extraction ----------

def _date(s):
    try:
        return datetime.fromisoformat(str(s)[:19]) if s else None
    except ValueError:
        return None


def _current_agents(rec):
    """Agents not expired at the export date, across owners (deduplicated by agentID)."""
    found = {}
    for o in rec.get("owners") or []:
        for a in o.get("agents") or []:
            exp = _date(a.get("expirationDt"))
            if exp is not None and exp < EXPORT_DATE:
                continue
            name = a.get("companyName") or a.get("contactName") or \
                " ".join(x for x in (a.get("firstName"), a.get("lastName")) if x) or None
            found.setdefault(a.get("agentID"), (name or "").strip())
    return found


def _extract(rec):
    ovs = [o["ownerValue"][0] if isinstance(o.get("ownerValue"), list) and o["ownerValue"]
           else o.get("ownerValue") or {} for o in rec.get("owners") or []]

    def owner_sum(key):
        vals = [v.get(key) for v in ovs if v.get(key) is not None]
        return sum(vals) if vals else None

    cur = owner_sum("ownerMarketValue")
    pcts = [o.get("ownerPct") or 0 for o in rec.get("owners") or []]
    pct = sum(pcts)

    def basis_factor(v, initial=False):
        """Factor that puts an appeal value on the same basis as the current values (the total of the owners
        listed in the record). Each owner's ownerValue holds only that owner's share, while an appeal value
        can be for the listed owners, for the whole property, or for the one owner who appealed:
          532143  two 50% owners, appeal initial 148,780 = one owner's share       -> x2
          335041  owners 34/33/33%, initial 90,636 = the 34% owner's share          -> x(100/34)
          21952   two 50% owners, final 78,948 = whole property = listed total      -> x1
          Denton 530958  only one 50% owner listed, final 332,146 = whole property  -> x0.5
        Picks the candidate basis that lands closest to the current market value (for the initial value,
        among those not below it)."""
        positive = [p for p in pcts if p > 0]
        if not v or not cur or not positive or (len(positive) == 1 and pct >= 99.99):
            return 1.0
        cands = [1.0, pct / 100] + [pct / q for q in set(positive)]
        if initial:
            # a protest doesn't raise the value: prefer bases where notice >= current (36804: 28/72% owners,
            # initial 1,968,868 -> 28% share = 7,031,671 notice, not 72% = 2,734,539 below the 4,219,003 final)
            cands = [f_ for f_ in cands if v * f_ >= cur - 2] or cands
        return min(cands, key=lambda f_: (abs(math.log(v * f_ / cur)), f_ != 1.0))

    def on_basis(v, f):
        if v is None or f == 1.0:
            return v
        x = v * f
        return cur if abs(x - cur) <= 2 else round(x)

    agents = _current_agents(rec)
    row = {
        "prop_id": rec["pID"],
        "current_appraised": owner_sum("ownerAppraisedValue"),
        "current_market": cur,
        "agent_id": " | ".join(str(k) for k in agents if k is not None) or None,
        "agent_name": " | ".join(v for v in agents.values() if v) or None,
        "owner_count": len(pcts),
        "owner_pct": round(pct, 4) if pct else None,
    }
    aps = sorted((a for a in rec.get("appeals") or [] if a.get("pYear") == APPEAL_YEAR
                  and (a.get("appealStatus") or "").strip() not in NOT_PROTEST),
                 key=lambda a: a["appealID"])
    if aps:
        done = [a for a in aps if a.get("finalized") and a.get("finalMarketValue")]
        fi = basis_factor(aps[0].get("initialMarketValue"), initial=True)       # same factor for initial appraised
        ff = basis_factor(done[-1]["finalMarketValue"]) if done else 1.0
        row.update({
            "initial_market": on_basis(aps[0].get("initialMarketValue"), fi),
            "initial_appraised": on_basis(aps[0].get("initialAppraisedValue"), fi),
            "final_market": on_basis(done[-1]["finalMarketValue"], ff) if done else None,
            "basis_adjusted": fi != 1.0 or ff != 1.0,
            "appeal_id": aps[0].get("appealID"),
            "appeal_type": aps[0].get("appealType"),
            "appeal_status": " / ".join(dict.fromkeys((a.get("appealStatus") or "").strip() for a in aps)),
            "appeal_count": len(aps),
        })
    return row


# ---------- public ----------

COLS = ["prop_id", "appraised_value", "market_value", "final_value", "final_source", "reduction",
        "reduction_pct", "agent_id", "agent_name", "appeal_id", "appeal_type", "appeal_status",
        "appeal_count", "owner_count", "owner_pct", "basis_adjusted", "has_appeal", "found"]


def get_values(ids, id_type="auto", out_csv=None):
    """Values for a list of IDs (pID, refID2, refID1 or geoID; see resolve_ids). One row per property."""
    ids = list(ids)
    pids, _ = resolve_ids(ids, id_type)
    missing = [i for i, p in zip(ids, pids) if pd.isna(p)]
    if missing:
        print(f"not found: {', '.join(map(str, missing))}")
    return _values_for_pids(pids.dropna().unique(), out_csv)


def _values_for_pids(ids, out_csv=None):
    ids = [int(i) for i in ids]
    idx = _offsets()
    rows = []
    with open(PROTAX_JSON, "rb") as f:
        for pid in ids:
            if pid not in idx.index:
                rows.append({"prop_id": pid, "found": False})
                continue
            off, length = idx.loc[pid, ["offset", "length"]]
            f.seek(int(off))
            rec = json.loads(f.read(int(length)).decode("utf-8").rstrip().rstrip(","))
            if rec.get("pID") != pid:
                raise ValueError(f"protax index is out of date (pID {pid}); delete {PROTAX_INDEX} to rebuild")
            r = _extract(rec)
            r["found"] = True
            rows.append(r)

    res = pd.DataFrame(rows)
    for c in ["current_appraised", "current_market", "initial_appraised", "initial_market", "final_market",
              "appeal_id", "appeal_count"]:
        # a column is missing when none of the IDs has it (e.g. only unprotested properties)
        res[c] = pd.to_numeric(res[c], errors="coerce").astype("Int64") if c in res else pd.Series(pd.NA, index=res.index, dtype="Int64")
    res["has_appeal"] = res["appeal_id"].notna()
    res["basis_adjusted"] = res.get("basis_adjusted", pd.Series(False, index=res.index)).fillna(False).astype(bool)
    cur = res["current_market"]

    # Notice values: from the appeal when protested, otherwise the current values
    res["appraised_value"] = res["initial_appraised"].where(res["has_appeal"], res["current_appraised"])
    res["market_value"] = res["initial_market"].where(res["has_appeal"], cur)
    res["final_value"] = res["final_market"]
    res["final_source"] = pd.Series(pd.NA, index=res.index, dtype="string")
    res.loc[res["final_market"].notna(), "final_source"] = "appeal"
    open_ = res["has_appeal"] & res["final_market"].isna()
    res.loc[open_, "final_value"] = cur[open_]
    res.loc[open_ & cur.notna(), "final_source"] = "current (appeal open)"
    no_protest = ~res["has_appeal"] & cur.notna()
    res.loc[no_protest, "final_value"] = cur[no_protest]
    res.loc[no_protest, "final_source"] = "no protest"

    res["reduction"] = res["market_value"] - res["final_value"]
    fv = res["final_value"].astype("Float64")
    res["reduction_pct"] = ((fv - res["market_value"]) / fv.where(fv != 0)).round(4)
    for c in COLS:
        if c not in res:
            res[c] = pd.NA
    res = res[COLS]

    if out_csv:
        res.to_csv(out_csv, index=False)
    return res


ID_COLUMN_NAMES = ["prop_id", "propid", "pid", "property_id", "propertyid", "account", "account_id",
                   "accountid", "account_number", "id"]
ID_TYPES = ["pID", "refID2", "refID1", "geoID"]


def _norm_id(v):
    """Comparable form: '462,789' / '462789.0' / ' 0462789 ' -> '462789'; 'm00001' -> 'M00001'."""
    s = str(v).strip().upper().replace(",", "")
    if s.endswith(".0") and s[:-2].isdigit():
        s = s[:-2]
    return str(int(s)) if s.isdigit() else s


def resolve_ids(ids, id_type="auto"):
    """Map client IDs to pIDs through the index. Returns (Series of pID aligned with ids, id_type used).

    id_type 'auto' picks the ID type that matches the most IDs (pID wins a tie). pID and refID2 are both plain
    numbers in Montgomery, so check the printed choice; force it with id_type='refID2' etc. if needed."""
    raw = pd.Series(list(ids), dtype="object")
    keys = raw.map(_norm_id)
    _offsets()                               # make sure the index exists
    idx = pd.read_csv(PROTAX_INDEX, usecols=ID_TYPES, dtype=str, keep_default_na=False)
    maps = {}
    for t in ID_TYPES:
        m = pd.DataFrame({"key": idx[t].map(_norm_id), "pID": idx["pID"]})[idx[t] != ""]
        maps[t] = m.drop_duplicates("key").set_index("key")["pID"]
    hits = {t: int(keys.isin(maps[t].index).sum()) for t in ID_TYPES}
    if id_type == "auto":
        id_type = max(ID_TYPES, key=lambda t: (hits[t], t == "pID"))
    elif id_type not in ID_TYPES:
        raise ValueError(f"id_type must be 'auto' or one of {ID_TYPES}")
    print(f"IDs matched as: " + ", ".join(f"{t} {n}" for t, n in hits.items()) + f"  -> using {id_type}")
    return keys.map(maps[id_type]).astype("Int64"), id_type


def read_client_ids(path, id_col=None):
    """Client list -> (DataFrame with the original columns, name of the ID column)."""
    path = Path(path)
    ext = path.suffix.lower()
    if ext in (".txt", ""):
        df = pd.DataFrame({"client_id": path.read_text().replace(",", " ").split()})
        return df, "client_id"
    if ext == ".csv":
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(path, dtype=str).fillna("")
    else:
        raise ValueError(f"Unsupported file type {ext!r}; use .txt, .csv or .xlsx")
    if id_col is None:
        norm = {c.strip().lower().replace(" ", "_").rstrip("#").strip("_"): c for c in df.columns}
        id_col = next((norm[n] for n in ID_COLUMN_NAMES if n in norm), df.columns[0])
    elif id_col not in df.columns:
        raise KeyError(f"Column {id_col!r} not in {path.name}; columns are {list(df.columns)}")
    return df, id_col


def get_values_from_file(path, id_col=None, id_type="auto", out_csv=None):
    """Client rows (same order, duplicates kept) with the values appended; saved to out_csv,
    default '<input name>_values.csv' next to the input."""
    path = Path(path)
    clients, col = read_client_ids(path, id_col)
    print(f"{path.name}: {len(clients)} rows, ID column {col!r}")
    clients = clients.copy()
    clients["prop_id"], used = resolve_ids(clients[col], id_type)
    values = _values_for_pids(clients["prop_id"].dropna().unique())
    clients = clients.drop(columns=[c for c in values.columns if c in clients.columns and c != "prop_id"])
    res = clients.merge(values, on="prop_id", how="left")
    res.insert(res.columns.get_loc("prop_id") + 1, "matched_on", used)
    res.loc[res["prop_id"].isna(), "matched_on"] = pd.NA
    for c in ("has_appeal", "found"):
        res[c] = res[c].fillna(False).astype(bool)

    out_csv = Path(out_csv) if out_csv else path.with_name(f"{path.stem}_values.csv")
    res.to_csv(out_csv, index=False)
    missing = clients.loc[clients["prop_id"].isna(), col].tolist()
    print(f"{res['found'].sum()} of {len(res)} found in {PROTAX_JSON.name}"
          + (f" (not found e.g. {missing[:5]})" if missing else "")
          + f" | {res['has_appeal'].sum()} with a {APPEAL_YEAR} appeal | total reduction "
          f"{res['reduction'].sum():,}\nsaved {out_csv}")
    return res


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Appeal vs. final values for Montgomery property IDs (protax JSON).")
    p.add_argument("ids", nargs="+", help="a client file (.txt/.csv/.xlsx) or one or more IDs")
    p.add_argument("--id-col", help="ID column name in a .csv/.xlsx (default: auto-detect)")
    p.add_argument("--id-type", default="auto", choices=["auto", *ID_TYPES],
                   help="what the IDs are (default: whichever type matches the most)")
    p.add_argument("-o", "--out", help="output CSV (default: <input>_values.csv next to the input file)")
    a = p.parse_args()
    if len(a.ids) == 1 and Path(a.ids[0]).is_file():
        get_values_from_file(a.ids[0], id_col=a.id_col, id_type=a.id_type, out_csv=a.out)
    else:
        print(get_values(a.ids, id_type=a.id_type, out_csv=a.out).to_string(index=False))
