# Rockwall data profile

Working files for the Rockwall Property Data Profile page, built with the `create_county_data_profile` skill.

- Published page: https://claude.ai/artifact/HxBagVNeeWmR1coTBoYH7f

- Rockwall publishes the same PACS Appraisal Export as Denton and Travis, with Denton's file names. The four 2026 exports
  are layout 8.0.0.30 (Mar 16 prelim), 8.0.0.32 (May 26 prelim) and 8.0.0.33 (Jul 13 certified, Oct 9 supp 6).
  Denton's `etl/pacs_appraisal_export_layout.json` is the 8.0.30 layout, so `../etl/rockwall_appraisal_export_etl.py`
  parses all four with it; fields added in 8.0.32/8.0.33 land in `unmapped_tail`. Output: `../output/<export date>_2026_<RECORD>.csv.gz`
- `manifest.json` describes datasets, tabs, notes and column descriptions (80 datasets: 20 PACS files × 4 exports, keys
  `p26a-*` Mar 16, `p26b-*` May 26, `c26-*` Jul 13, `s26-*` Oct 9). `make_manifest.py` built it from Travis's manifest
  (re-running overwrites notes and the Rockwall tooltips); `notes.py` writes the notes, with facts checked in DuckDB
- `profile.json` holds the DuckDB full-scan profiles, with 100 sample rows per set
- `rockwall-data-profile.html` is the last published build (about 14.5 MB, mostly sketch JSON in the sample rows)
- `venv/` has duckdb (not committed)

To add an export: run the ETL on the new folder, add its datasets to `manifest.json` and a new entry to each group's `years`, then run
`venv/bin/python -I ~/.claude/skills/create_county_data_profile/scripts/profile_files.py manifest.json profile.json <keys>`,
then `build_page.py manifest.json profile.json - rockwall-data-profile.html`,
then republish to the same artifact link.
