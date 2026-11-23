# Tarrant data profile

Working files for the Tarrant Property Data Profile page, built with the `create_county_data_profile` skill.

- Published page: https://claude.ai/artifact/S1k5edPmQNGeGTCmE8hEP6
- `manifest.json` describes datasets, year tabs, notes and column descriptions
- `profile.json` holds file profiles (39 website files), from DuckDB full scans
- `api.json` holds Agent Portal endpoint profiles from `CAD Agent Portal/Tarrant New/Tarrant-New-Docs.yaml`
- `tarrant-data-profile.html` is the last published build

To add a file: add it to `manifest.json`, then run
`profile_files.py manifest.json profile.json <new key>`, then `build_page.py manifest.json profile.json api.json tarrant-data-profile.html`,
then republish to the same artifact link.

## Review workspace (from 2026-11-23)

- Column review: https://claude.ai/artifact/25Y86B6k8MmpK2y9gbgCRn
- `catalog.json`: tad.org/resources/data-downloads (read in Chrome; the site needs a VPN) plus an Agent Portal API section.
  `drive.json`: County Playbooks › Tarrant › Public Information. Per-dataset `raw`/`layout` are in `manifest.json`.
- True Prodigy Data-FullSet (export of 2026-11-13): `../etl/tarrant_tp_layout.py` reads the layout workbook into
  `../Data/tp_layout_<ver>.json`; `../etl/tarrant_tp_export_etl.py` converts the 20 .TXT files to
  `../output/tp_2026-11-13/*.csv.gz` (keys `tp26-*`). The 8.0.33 layout matches the files; 8.0.32 does not.
- Rebuild (S = `~/.claude/skills/create_county_data_profile/scripts`): build_page.py manifest.json profile.json api.json
  tarrant-data-profile.html → add_column_review.py → build_source_map.py catalog.json manifest.json source_map.json
  --drive drive.json --api api.json → add_source_nav.py review/tarrant-column-review.html source_map.json
  review/tarrant-column-review.html manifest.json → republish (omit capabilities).
- The converted CSVs behind the older profiles (output/PropertyData_*.csv, Supplemental, Comp, Features) are no longer
  on disk; their profiles are kept in profile.json.
