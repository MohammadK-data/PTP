# Denton data profile

Working files for the Denton Property Data Profile page, built with the `create_county_data_profile` skill.

- Published page: https://claude.ai/artifact/KA1GfZdYjdbxMWVRx6HWSt
- `manifest.json` describes datasets, tabs, notes and column descriptions (40 datasets: 20 PACS files × 2 exports)
- `profile.json` holds the DuckDB full-scan profiles of `output/2026-07-27_*.csv` (certified) and `output/2026-10-14_*.csv` (supp 3)
- `mask_sensitive.py` hides owner names, addresses, serial numbers and the export operator. Run it after every profiling run
- `denton-data-profile.html` is the last published build
- `venv/` has duckdb (not committed)

To add an export: add its datasets to `manifest.json` and a new entry to each group's `years`, then run
`venv/bin/python -I ~/.claude/skills/create_county_data_profile/scripts/profile_files.py manifest.json profile.json <keys>`,
then `python3 mask_sensitive.py`, then `build_page.py manifest.json profile.json - denton-data-profile.html`,
then republish to the same artifact link.
