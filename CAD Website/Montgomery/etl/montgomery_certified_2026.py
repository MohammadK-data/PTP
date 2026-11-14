"""Montgomery certified roll 2026 (PACS 8.0.0.33 appraisal export, run 2026-08-03) -> a small CSV of the
fields the 2026 scorecard uses as fallback: prop_id, prop_val_yr, sup_num, geo_id, hood_cd, situs_city,
arb_protest_flag, appraised_val, market_value, state codes.

Field positions come from Denton/etl/pacs_appraisal_export_layout.json (same PACS layout; Montgomery's
lines are wider, 9,923 chars, the extra tail is ignored).

Run:  .venv/bin/python -I "CAD Website/Montgomery/etl/montgomery_certified_2026.py"
Out:  output/2026-08-04_2026_APPRAISAL_INFO_min.csv.gz
"""
import csv
import gzip
import json
from pathlib import Path

MONT = Path(__file__).resolve().parent.parent
SRC = MONT / "Data" / "Certified Appraisal Roll 2026" / "2026-08-04_2026_APPRAISAL_INFO.TXT"
OUT = MONT / "output" / "2026-08-04_2026_APPRAISAL_INFO_min.csv.gz"
LAYOUT = json.loads((MONT.parent / "Denton" / "etl" / "pacs_appraisal_export_layout.json").read_text())
KEEP = ["prop_id", "prop_type_cd", "prop_val_yr", "sup_num", "geo_id", "situs_city", "hood_cd",
        "appraised_val", "arb_protest_flag", "imprv_state_cd", "land_state_cd", "market_value"]


def main():
    pos = {n: (s - 1, e) for n, s, e in LAYOUT["APPRAISAL_INFO"]}
    sl = [pos[k] for k in KEEP]
    n = 0
    with open(SRC, "rb") as f, gzip.open(OUT, "wt", newline="") as g:
        w = csv.writer(g)
        w.writerow(KEEP)
        for line in f:
            s = line.decode("latin-1")
            w.writerow([s[a:b].strip() for a, b in sl])
            n += 1
    print(f"{n:,} rows -> {OUT}")


if __name__ == "__main__":
    main()
