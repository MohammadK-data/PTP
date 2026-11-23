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

## Review workspace (from 2026-11-23)

- Column review: https://claude.ai/artifact/TEQbUErFh3QeXAQy9c6DkZ
- `catalog.json`: rockwallcad.com/data-exports (each roll is a Google Drive link; checked 2026-11-23). `drive.json`: County Playbooks › Rockwall › Public Information.
- Added: the header, agent and ARB files of the 2023 prelim (Jun 5), 2024 certified (exported Aug 23 although the folder says Jul 11),
  2025 prelim (Jun 20) and 2025 certified (Jul 14) exports (`p23-*`, `c24-*`, `p25-*`, `c25-*`, group "Earlier Exports"), and their
  property files in Property Roll. The 2023 property file is layout 8.0.25 (9,067 chars) and is not read: no 8.0.25 layout on hand.
- Sketch tables keep 25 sample rows (`sample_rows` in the manifest) so the page stays under the 16 MB artifact limit.
- Rebuild (S = `~/.claude/skills/create_county_data_profile/scripts`): build_page.py manifest.json profile.json - rockwall-data-profile.html
  → add_column_review.py → build_source_map.py catalog.json manifest.json source_map.json --drive drive.json
  → add_source_nav.py review/rockwall-column-review.html source_map.json review/rockwall-column-review.html manifest.json → republish.
