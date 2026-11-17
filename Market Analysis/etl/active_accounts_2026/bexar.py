"""Bexar CAD: latest 2026 PACS export -> active accounts with address, state code, notice value and latest market value.
  roll / address / state code : Bexar/output/2026-10-15_2026_APPRAISAL_INFO.csv.gz
  notice value + protest      : Bexar/output/bexar_values_2026.csv (earlier protest build)
  notice value, not protested : Bexar/output/2026-03-28_2026_APPRAISAL_INFO.csv.gz
Run: /Users/user2/PTP/.venv/bin/python -I "Market Analysis/etl/active_accounts_2026/bexar.py"
To refresh: point the paths below at the newest export and update SOURCE / DATE."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pacs  # noqa: E402
from common import CAD, add_values_file, fill_notice, main  # noqa: E402

INFO = CAD / "Bexar/output/2026-10-15_2026_APPRAISAL_INFO.csv.gz"
STATE_CODES = CAD / "Bexar/output/2026-10-15_2026_APPRAISAL_STATE_CODE.csv.gz"
VALUES = CAD / "Bexar/output/bexar_values_2026.csv"
VALUES_MAP = {"situs": "situs_address", "city": "situs_city", "zip": "situs_zip", "notice_value": "notice_value", "final_value": "protest_final_value", "protested": "protested", "outcome": "protest_outcome"}
PRELIM = CAD / "Bexar/output/2026-03-28_2026_APPRAISAL_INFO.csv.gz"
PRELIM_LABEL = "1st notice run export 2026-03-28"
SOURCE = "BCAD 2026 PACS appraisal export 2026-10-15 (APPRAISAL_INFO)"
DATE = "2026-10-15"


def load_roll():
    r = pacs.roll(INFO, STATE_CODES)
    r = add_values_file(r, VALUES, "pID", VALUES_MAP, "protest build")
    if PRELIM:
        r = fill_notice(r, pacs.market_by_id(PRELIM), PRELIM_LABEL)
    return r


if __name__ == "__main__":
    main("Bexar", load_roll, SOURCE, DATE)
