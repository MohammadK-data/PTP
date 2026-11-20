"""Tarrant CAD state-code lookup, same layout and source type as Denton's APPRAISAL_STATE_CODE file.

Source: TAD's True Prodigy appraisal export ("True Prodigy Data-FullSet" on tad.org Data Downloads),
file *_APPRAISAL_STATE_CODE.TXT in Data/000_Tarrant_All_Taxing_Units/. Fixed width per the export
layout (TP_Legacy8.0.32-AppraisalExportLayout.xlsx, sheet StateCode):
    state_cd 1-10, state_cd_description 11-60, ptd_state_cd 61-70,
    ptd_state_cd_description 71-120, state_cd_year 121-125

Values are copied verbatim. The script also checks that every Property_Class used in the 2026
PropertyData roll is in the table.

Output: Tarrant/output/tarrant_2026_state_codes.csv
"""
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / "Data/000_Tarrant_All_Taxing_Units"
ROLL = ROOT / "Data/PropertyData(Delimited)_2026.txt"
OUT = ROOT / "output/tarrant_2026_state_codes.csv"
COLS = ["state_cd", "state_cd_description", "ptd_state_cd", "ptd_state_cd_description", "state_cd_year"]
SLICES = [(0, 10), (10, 60), (60, 70), (70, 120), (120, 125)]


def main():
    src = sorted(EXPORT.glob("*_APPRAISAL_STATE_CODE.TXT"))[-1]
    with open(src, encoding="latin-1") as f:
        rows = [[line.rstrip("\r\n")[a:b].strip() for a, b in SLICES] for line in f if line.strip()]

    with open(ROLL, encoding="latin-1", newline="") as f:
        used = Counter(r["Property_Class"].strip() for r in csv.DictReader(f, delimiter="|"))
    used.pop("", None)
    missing = set(used) - {r[0] for r in rows}
    if missing:
        raise SystemExit(f"Roll codes missing from {src.name}: {sorted(missing)}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLS)
        w.writerows(rows)
    print(f"{OUT}: {len(rows)} codes from {src.name}; all {len(used)} codes used in the 2026 roll are covered")


if __name__ == "__main__":
    main()
