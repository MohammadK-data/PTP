"""Build etl/pacs_appraisal_export_layout_8034.json from BCAD's 'Appraisal Export Layout - 8.0.34.xlsx'.

Field positions come from the workbook's lengths (cumulative). Names reuse Denton's 8.0.30 layout
(etl/pacs_appraisal_export_layout.json) where a field starts at the same position with the same length, so
Bexar columns match Denton/Travis/Rockwall; fields new in 8.0.34 get a snake_case name from the workbook.
Also writes the workbook's descriptions to etl/pacs_8034_descriptions.json (by record and column).
"""
import json, re, sys
from pathlib import Path
import openpyxl

BEXAR = Path(__file__).resolve().parent.parent
XLSX = BEXAR / "Data/2025 Appraisal Data Export as of 2026-10-08_Sup 298/Appraisal Export Layout - 8.0.34.xlsx"
DENTON = json.loads((BEXAR.parent / "Denton/etl/pacs_appraisal_export_layout.json").read_text())

def snake(s):
    s = re.sub(r"[^0-9a-zA-Z]+", "_", str(s).strip()).strip("_").lower()
    return s or "field"

ws = openpyxl.load_workbook(XLSX, read_only=True).worksheets[0]
records, cur, in_table = {}, None, False
for r in ws.iter_rows(values_only=True, max_col=6):
    a = r[0]
    if isinstance(a, str) and a.startswith("File #"):
        m = re.search(r"\((\w+)\.TXT\)", a)
        cur = m.group(1) if m else None
        in_table = False
        if cur: records[cur] = []
        continue
    if a == "Field Name":
        in_table = True; continue
    if cur and in_table and a and isinstance(r[4], (int, float)):
        ln = int(r[4])
        m = re.fullmatch(r"char\((\d+)\)", str(r[1] or "").strip())
        if m and int(m.group(1)) != ln:  # workbook typo: freeze_ceiling_override is char(1) with length 15
            print(f"{cur}.{a}: length {ln} -> {m.group(1)} (datatype {r[1]})", file=sys.stderr)
            ln = int(m.group(1))
        records[cur].append((str(a).strip(), ln, str(r[1] or ""), str(r[5] or "").strip()))

layout, descs = {}, {}
for rec, fields in records.items():
    den = {(s, e): n for n, s, e in DENTON.get(rec, [])}
    pos, out, used = 1, [], set()
    for name, ln, typ, desc in fields:
        s, e = pos, pos + ln - 1
        n = den.get((s, e)) or snake(name)
        base, k = n, 2
        while n in used:
            n = f"{base}_{k}"; k += 1
        used.add(n)
        out.append([n, s, e])
        descs[f"{rec}:{n}"] = desc
        pos = e + 1
    layout[rec] = out
    print(rec, len(out), "fields, width", pos - 1, "| reused Denton names:", sum(1 for f in out if (f[1], f[2]) in den), file=sys.stderr)

(BEXAR / "etl/pacs_appraisal_export_layout_8034.json").write_text(json.dumps(layout, indent=0))
(BEXAR / "etl/pacs_8034_descriptions.json").write_text(json.dumps(descs, indent=0))
