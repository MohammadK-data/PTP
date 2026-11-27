"""Bexar: per-dataset fields the column-review workspace needs, and page texts without our local folders.
Run after make_manifest.py, descriptions.py and notes.py (it patches manifest.json in place).

- raw: the file's name inside BCAD's download (the zip member), since our tables are converted or renamed.
- layout: the BCAD document that describes the file.
"""
import json, re
from pathlib import PurePosixPath

m = json.load(open("manifest.json"))
ds = m["datasets"]

PACS_RUN = {"p26": ("2026-03-28", "007264", "Appraisal Export Layout - 8.0.31.xlsx (shipped with this export; the header says 8.0.0.33)"),
            "s26": ("2026-10-15", "007456", "Appraisal Export Layout - 8.0.34.xlsx")}
for k, d in ds.items():
    pre = k.split("-")[0]
    name = PurePosixPath(d["path"]).name
    if pre in PACS_RUN:
        date, run, layout = PACS_RUN[pre]
        table = re.sub(r"^\d{4}-\d\d-\d\d_\d{4}_", "", name).replace(".csv.gz", "")
        d["raw"] = f"{date}_{run}_{table}.TXT"
        d["layout"] = f"{layout} · {table}"
    elif pre == "ag":
        d["raw"] = name.replace(".csv", ".txt")
        d["layout"] = "Agent Export File Layout for Agents.pdf"
    elif k == "ps26a":
        d["raw"] = "2026 Property Summary Export as of 2026-03-28__1st Notice Run Preliminary.csv"
        d["layout"] = "2025-09-04 Export Property Summary Layout.pdf (header from 2025-09-04 Property Summary File With Improvements Header line.csv)"
    elif k == "ps26s":
        d["raw"] = "2026 Property Summary Export as of 2026-10-13_Sup 298.csv"
        d["layout"] = "2025-09-04 Export Property Summary Layout.pdf"

# texts on the page name BCAD's files, never our folders or scripts
src = {s["id"]: s for s in m["sources"]}
src["pacs"]["desc"] = ("BCAD's PACS Appraisal Export, provided on request through BCAD's FTP server (one zip per snapshot). "
    "Fixed-width .TXT files, converted to CSV for profiling with BCAD's own layout workbook; every property in the county. "
    "<code>prop_id</code> is the BCAD property id used by every other Bexar file.")
src["agent"]["desc"] = ("BCAD's Agent Export as of October 26, 2026 (<code>2026 Agent Export as of 2026-10-26.zip</code>, "
    "headerless pipe-delimited .txt files, converted to CSV with the column names from BCAD's layout PDF; values are "
    "unchanged). Despite the name it covers every property in the county, and several files reach back to the 1990s. "
    "<code>Property ID</code> is the PACS <code>prop_id</code>. The Non-Agent Export of October 21 carries the same "
    "files minus the three sales files and is not profiled separately.")
m["eyebrow"] = "Bexar Appraisal District · Data exports (on request)"
m["foot"] = ("Generated {date}. Files were scanned in full with DuckDB. The PACS files are converted from the raw "
    "fixed-width .TXT files to CSV using BCAD's own 8.0.34 layout workbook (the March export is 8.0.0.33, the same "
    "layout without the FEED fields); the Agent Export and Property Summary files are read as published. "
    "\"Auto-detected on load\" is the type DuckDB assigns, and distinct counts there are approximate (HyperLogLog). "
    "\"Data type\" is inferred from the values: Code means digits stored as text with leading zeros.")
NOTE_FIX = [
    ("by <code>etl/bexar_agent_export_to_csv.py</code> (", "to CSV ("),
    ("the profiled copy in <code>output/</code> is the file", "the profiled copy is the file"),
]
for d in ds.values():
    for old, new in NOTE_FIX:
        d["notes"] = [n.replace(old, new) for n in d.get("notes", [])]
json.dump(m, open("manifest.json", "w"), indent=1, ensure_ascii=False)
print(sum(1 for d in ds.values() if d.get("raw")), "datasets with raw names")
