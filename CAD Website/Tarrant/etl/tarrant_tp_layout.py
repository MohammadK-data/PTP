"""Read Tarrant's True Prodigy appraisal export layout workbook (TP_Legacy<ver>-AppraisalExportLayout.xlsx) into
JSON: per record (APPRAISAL_INFO ...) the file number and title, short name, and fields [name, start, end, description].
Start/End in the workbook are formulas, so positions are computed from each field's Length, in order.

Usage: python3 -I etl/tarrant_tp_layout.py <layout.xlsx> <out.json>
"""
import json
import re
import sys

import openpyxl


def main(src, out):
    wb = openpyxl.load_workbook(src, read_only=True, data_only=False)
    layout = {}
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        title = next((str(c) for r in rows for c in r if isinstance(c, str) and re.search(r"File #\s*\d+:", c)), "")
        m = re.search(r"File #\s*(\d+):\s*(.*?)\s*\(([A-Z_]+)\.TXT\)", title)
        if not m:
            continue
        short = re.search(r"Short file name \(([A-Z_0-9]+\.TXT)\)", title)
        hdr = next((i for i, r in enumerate(rows) if r and "Field Name" in [str(c).strip() if c else "" for c in r]), None)
        fields, pos = [], 1
        if hdr is not None:
            cols = [str(c).strip() if c else "" for c in rows[hdr]]
            ci = {k: cols.index(k) for k in ("Field Name", "Length", "Description") if k in cols}
            for r in rows[hdr + 1:]:
                name = r[ci["Field Name"]] if len(r) > ci["Field Name"] else None
                ln = r[ci["Length"]] if "Length" in ci and len(r) > ci["Length"] else None
                if not name or not isinstance(ln, (int, float)):
                    continue
                desc = r[ci["Description"]] if "Description" in ci and len(r) > ci["Description"] else None
                fields.append([str(name).strip(), pos, pos + int(ln) - 1, (str(desc).strip() if desc else "")])
                pos += int(ln)
        layout[m.group(3)] = {"file_no": int(m.group(1)), "title": m.group(2).strip(), "sheet": ws.title,
                              "short": short.group(1) if short else None, "fields": fields}
    json.dump(layout, open(out, "w"), indent=1)
    for k, v in layout.items():
        print(f"{v['file_no']:>2} {k:36} {len(v['fields']):4} fields, width {v['fields'][-1][2] if v['fields'] else '-'}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
