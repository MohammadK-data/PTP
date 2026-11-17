"""Denton CAD: latest 2026 PACS export -> active accounts with address, state code, notice value and latest market value.
  roll / address / state code : Denton/output/2026-10-14_2026_APPRAISAL_INFO.csv
  notice value + protest      : Denton/output/denton_values_2026.csv (earlier protest build)
  notice value, not protested : roll value from the values file
Run: /Users/user2/PTP/.venv/bin/python -I "Market Analysis/etl/active_accounts_2026/denton.py"
To refresh: point the paths below at the newest export and update SOURCE / DATE."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pacs  # noqa: E402
from common import CAD, add_values_file, fill_notice, main  # noqa: E402

INFO = CAD / "Denton/output/2026-10-14_2026_APPRAISAL_INFO.csv"
STATE_CODES = CAD / "Denton/output/2026-10-14_2026_APPRAISAL_STATE_CODE.csv"
VALUES = CAD / "Denton/output/denton_values_2026.csv"
VALUES_MAP = {"situs": "situs_address", "situs_city": "situs_city", "zip": "situs_zip", "notice_value": "notice_value", "notice_source": "notice_source", "final_value": "protest_final_value", "protested": "protested", "outcome": "protest_outcome"}
PRELIM = None
PRELIM_LABEL = ""
SOURCE = "DCAD (Denton) 2026 PACS appraisal export 2026-10-14 (APPRAISAL_INFO)"
DATE = "2026-10-14"


def load_roll():
    r = pacs.roll(INFO, STATE_CODES)
    r = add_values_file(r, VALUES, "pID", VALUES_MAP, "protest build")
    if PRELIM:
        r = fill_notice(r, pacs.market_by_id(PRELIM), PRELIM_LABEL)
    return r


if __name__ == "__main__":
    main("Denton", load_roll, SOURCE, DATE)
