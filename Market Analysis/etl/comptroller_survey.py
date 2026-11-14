"""Extract question 9 (protests) from the Comptroller Appraisal District Operations Survey for our counties.
Output: work/comptroller/ops_survey_protests.csv (long: county, year, question, value)"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from xlsx_lite import read_sheets  # noqa: E402

W = Path(__file__).resolve().parent.parent / "work" / "comptroller"
COUNTIES = ["Dallas", "Denton", "Fort Bend", "Hays", "Montgomery", "Rockwall", "Tarrant", "Travis"]
rows = []
for y in (2024, 2025):
    sh = read_sheets(W / f"ops_{y}.xlsx")
    name = next(n for n in sh if n.split(".")[0].strip() == "9")
    data = sh[name]
    hdr = data[0]
    for r in data[1:]:
        if len(r) > 1 and r[1].strip() in COUNTIES:
            for i, q in enumerate(hdr[2:], start=2):
                rows.append({"county": r[1].strip(), "year": y, "question": q.strip(),
                             "value": r[i] if i < len(r) else ""})
with open(W / "ops_survey_protests.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["county", "year", "question", "value"])
    w.writeheader()
    w.writerows(rows)
print(len(rows))
