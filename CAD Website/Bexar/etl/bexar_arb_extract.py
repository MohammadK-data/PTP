"""Bexar: every protest from 2022 on, from BCAD's agent export ARB file (FID_ARBExport.txt, Oct 26 2026).

The file is the PACS ProTax ARB layout (77 pipe fields, same as DCAD's ProTax_ARBExport): prop_id, geo_id,
prop_val_yr, case_id, ..., agent_name (14), prot_type (15), prot_status (16), prot_by_type (19), begin_* (48-62,
begin_market = 56), final_* (63-77, final_market = 71). Free-text comments break some rows over several lines;
pieces are joined until the row has 77 fields.

Output: output/bexar_arb_2022_2026.csv.gz
Run:    .venv/bin/python -I "CAD Website/Bexar/etl/bexar_arb_extract.py"
"""
import io
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
Z = ROOT / "Data" / "2026 Agent Export as of 2026-10-26.zip"
N = 77
KEEP = {0: "prop_id", 1: "geo_id", 2: "year", 3: "case_id", 5: "hood_cd", 7: "state_cd", 8: "prop_type_cd",
        11: "exemptions", 12: "situs", 13: "agent_name", 14: "prot_type", 15: "prot_status", 16: "reasons",
        18: "prot_by_type", 24: "docket_start", 28: "arrived_dt", 55: "begin_market", 58: "begin_assessed",
        70: "final_market", 73: "final_assessed"}

rows, buf, bad = [], None, 0
p = subprocess.Popen(["unzip", "-p", str(Z), "FID_ARBExport.txt"], stdout=subprocess.PIPE)
for line in io.TextIOWrapper(p.stdout, encoding="latin-1"):
    line = line.rstrip("\r\n")
    buf = line if buf is None else buf + " " + line
    parts = buf.split("|")
    if len(parts) < N:
        continue
    if len(parts) > N:
        bad += 1
    buf = None
    y = parts[2].strip()
    if y.isdigit() and int(y) >= 2022:
        rows.append([parts[i].strip() for i in KEEP])
d = pd.DataFrame(rows, columns=list(KEEP.values()))
d.to_csv(ROOT / "output" / "bexar_arb_2022_2026.csv.gz", index=False)
print(f"{len(d):,} protests 2022+ | rows with extra fields: {bad}")
print(d.groupby("year").agg(rows=("prop_id", "size"), props=("prop_id", "nunique")).to_string())
