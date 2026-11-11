"""Appeal vs. final values for a list of Denton property IDs.

    from denton_values import get_values
    df = get_values([176451, 8, 9])            # ints or zero-padded strings
    df = get_values(ids, out_csv="../output/my_ids_values.csv")

Columns returned (one row per prop_id):
    prop_id
    appeal_appraised   appeals[].initialAppraisedValue   protax JSON export (2026-07-27)
    appeal_market      appeals[].initialMarketValue      protax JSON export
    final_value        market_value                      APPRAISAL_INFO of the FINAL export (default 2026-3, 2026-10-14)
    reduction          appeal_market - final_value
    reduction_pct      (final_value - appeal_market) / final_value
    agent_id, agent_name          current appraisal (CA) agent, from the FINAL export
    arb_agent_id, arb_agent_name  current ARB agent, from the FINAL export
    appeal_id, appeal_type, appeal_status, appeal_count   2026 appeal(s) in the protax JSON
    has_appeal, in_final          False if no 2026 appeal / prop_id not in the final export

Appeal values: a property can have several 2026 appeals (e.g. AGREEMENT + CLERICAL) carrying the
same initial values; the earliest appealID is used. Properties with no 2026 appeal get blank
appeal values, so reduction and reduction_pct are blank too.

Speed: the protax JSON (~21 GB) is read by seeking to each record via
output/protax_review/protax_index.csv (built once if missing). The final export's
APPRAISAL_INFO.TXT is scanned once and its needed columns cached in output/slim/.
"""

import csv
import json
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
    # Rows repeat once per owner with identical values; keep the highest supplement per property
    df = df.sort_values(["prop_id", "sup_num"]).drop_duplicates("prop_id", keep="last")
    return df.set_index("prop_id")


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
            aps = sorted((a for a in rec.get("appeals") or [] if a.get("pYear") == APPEAL_YEAR),
                         key=lambda a: a["appealID"])
            if not aps:
                continue
            a = aps[0]
            rows.append({
                "prop_id": pid,
                "appeal_appraised": a.get("initialAppraisedValue"),
                "appeal_market": a.get("initialMarketValue"),
                "appeal_id": a.get("appealID"),
                "appeal_type": a.get("appealType"),
                "appeal_status": " / ".join(dict.fromkeys(x.get("appealStatus") or "" for x in aps)),
                "appeal_count": len(aps),
            })
    cols = ["prop_id", "appeal_appraised", "appeal_market", "appeal_id", "appeal_type", "appeal_status", "appeal_count"]
    return pd.DataFrame(rows, columns=cols).set_index("prop_id")


# ---------- public ----------

def get_values(ids, final_export=FINAL_EXPORT, out_csv=None):
    ids = pd.Index(pd.unique(pd.Series(list(ids)).astype(str).str.strip().astype("int64")), name="prop_id")
    appeal = _appeals(ids).reindex(ids)
    final = _slim(final_export).reindex(ids)

    res = pd.DataFrame(index=ids)
    res["appeal_appraised"] = appeal["appeal_appraised"].astype("Int64")
    res["appeal_market"] = appeal["appeal_market"].astype("Int64")
    res["final_value"] = final["market_value"]
    res["reduction"] = res["appeal_market"] - res["final_value"]
    fv = res["final_value"].astype("Float64")
    res["reduction_pct"] = ((fv - res["appeal_market"]) / fv.where(fv != 0)).round(4)
    res["agent_id"] = final["ca_agent_id"]
    res["agent_name"] = final["ca_agent_name"].replace("", pd.NA)
    res["arb_agent_id"] = final["arb_agent_id"]
    res["arb_agent_name"] = final["arb_agent_name"].replace("", pd.NA)
    res["appeal_id"] = appeal["appeal_id"].astype("Int64")
    res["appeal_type"] = appeal["appeal_type"]
    res["appeal_status"] = appeal["appeal_status"]
    res["appeal_count"] = appeal["appeal_count"].astype("Int64")
    res["has_appeal"] = appeal["appeal_id"].notna()
    res["in_final"] = final["sup_num"].notna()
    res = res.reset_index()

    if out_csv:
        res.to_csv(out_csv, index=False)
    return res


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        sys.exit("usage: python3 denton_values.py ID [ID ...]   or   python3 denton_values.py ids.txt")
    arg = sys.argv[1:]
    ids = Path(arg[0]).read_text().split() if len(arg) == 1 and Path(arg[0]).is_file() else arg
    print(get_values(ids).to_string(index=False))
