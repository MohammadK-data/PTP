"""Montgomery CAD: latest 2026 PACS export -> active accounts with address, state code, notice value and latest market value.
  roll / address / state code : Montgomery/output/2026-08-04_2026_APPRAISAL_INFO_min.csv.gz
  notice value + protest      : Montgomery/output/montgomery_values_2026.csv (earlier protest build)
  notice value, not protested : roll value from the values file
Run: /Users/user2/PTP/.venv/bin/python -I "Market Analysis/etl/active_accounts_2026/montgomery.py"
To refresh: point the paths below at the newest export and update SOURCE / DATE."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pacs  # noqa: E402
from common import CAD, add_values_file, fill_notice, main  # noqa: E402

INFO = CAD / "Montgomery/output/2026-08-04_2026_APPRAISAL_INFO_min.csv.gz"
STATE_CODES = CAD / "Montgomery/Data/Certified Appraisal Roll 2026/2026-08-04_2026_APPRAISAL_STATE_CODE.TXT"
VALUES = CAD / "Montgomery/output/montgomery_values_2026.csv"
VALUES_MAP = {"situs": "situs_address", "situs_city": "situs_city", "zip": "situs_zip", "notice_value": "notice_value", "notice_source": "notice_source", "final_value": "protest_final_value", "protested": "protested", "outcome": "protest_outcome"}
PRELIM = None
PRELIM_LABEL = ""
SOURCE = "MCAD 2026 certified appraisal roll export 2026-08-04 (APPRAISAL_INFO)"
DATE = "2026-08-04"


def load_roll():
    r = pacs.roll(INFO, STATE_CODES)
    r = add_values_file(r, VALUES, "pID", VALUES_MAP, "protest build")
    if PRELIM:
        r = fill_notice(r, pacs.market_by_id(PRELIM), PRELIM_LABEL)
    return r


if __name__ == "__main__":
    main("Montgomery", load_roll, SOURCE, DATE)
