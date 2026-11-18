"""Travis: find the manual actives (address only, no account) in the Travis CAD roll.
The roll, notice value and protest data come from ../active_accounts_2026/travis.py (change paths there).
Run: /Users/user2/PTP/.venv/bin/python -I "Market Analysis/etl/active_manual_2026/travis.py"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from match import main  # noqa: E402

if __name__ == "__main__":
    main("Travis")
