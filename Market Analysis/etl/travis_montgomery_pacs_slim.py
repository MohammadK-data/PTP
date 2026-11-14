"""(Travis/Montgomery fork) Slim extract of a PACS legacy 8.0.x APPRAISAL_INFO / PROP.TXT fixed-width file.

Keeps: prop_id, prop_type_cd, prop_val_yr, sup_num, arb_protest_flag, hs_exempt, imprv_state_cd,
land_state_cd, personal_state_cd, mineral_state_cd, ca_agent_id, ca_agent_name, arb_agent_id.
Positions: CAD Website/Denton/etl/pacs_appraisal_export_layout.json (1-based, inclusive).
Run: python -I travis_montgomery_pacs_slim.py <INFO.TXT> <out.csv.gz>
"""
import csv
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAYOUT = json.load(open(ROOT / "CAD Website/Denton/etl/pacs_appraisal_export_layout.json"))["APPRAISAL_INFO"]
KEEP = ["prop_id", "prop_type_cd", "prop_val_yr", "sup_num", "arb_protest_flag", "hs_exempt", "imprv_state_cd",
        "land_state_cd", "personal_state_cd", "mineral_state_cd", "ca_agent_id", "ca_agent_name", "arb_agent_id"]
STRIP0 = {"prop_id", "ca_agent_id", "arb_agent_id"}


def main(src, dst):
    flds = LAYOUT if isinstance(LAYOUT, list) else LAYOUT.get("fields", LAYOUT)
    pos = {f[0]: (int(f[1]) - 1, int(f[2])) for f in flds}
    spec = [(k, *pos[k]) for k in KEEP]
    n = 0
    with open(src, "r", encoding="latin-1", newline="") as f, gzip.open(dst, "wt", newline="") as g:
        w = csv.writer(g)
        w.writerow(KEEP)
        for line in f:
            w.writerow([line[a:b].strip().lstrip("0") if k in STRIP0 else line[a:b].strip() for k, a, b in spec])
            n += 1
    print(n, "rows ->", dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
