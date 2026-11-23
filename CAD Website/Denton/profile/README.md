# Denton data profile

Working files for the Denton Property Data Profile page, built with the `create_county_data_profile` skill.

- Published page: https://claude.ai/artifact/KA1GfZdYjdbxMWVRx6HWSt
- `live-page/` builds the other Denton page (Protax JSON + PACS tables + correction changes), https://claude.ai/artifact/J85FsXFMftJrVDht43z4sZ; see its README
- `manifest.json` describes datasets, tabs, notes and column descriptions (40 datasets: 20 PACS files × 2 exports)
- `profile.json` holds the DuckDB full-scan profiles of `output/2026-07-27_*.csv` (certified) and `output/2026-10-14_*.csv` (supp 3)
- `mask_sensitive.py` is no longer used: the page shows values exactly as published (no masking)
- Each set in `profile.json` has a `sample` (100 random rows). Personal columns are blanked by the skill's default rule plus the manifest's `sample.hide`; `sample.show` keeps owner IDs and flags visible. Refill with `profile_files.py manifest.json profile.json --sample-only` after a new profile
- `denton-data-profile.html` is the last published build
- `venv/` has duckdb (not committed)

To add an export: add its datasets to `manifest.json` and a new entry to each group's `years`, then run
`venv/bin/python -I ~/.claude/skills/create_county_data_profile/scripts/profile_files.py manifest.json profile.json <keys>`,
then `build_page.py manifest.json profile.json - denton-data-profile.html`,
then republish to the same artifact link.

## Review workspace (from 2026-11-23)

- Column review: https://claude.ai/artifact/KCSSzQr7oppt95FVQQahhu
- `catalog.json`: dentoncad.com/data-downloads (year sections, Roll Corrections, GIS). `drive.json`: County Playbooks › Denton › CAD Reports.
- New tables: the 2026 certified JSON (`jc-*`, flattened with the skill's `flatten_json.py --keys pID,pYear --root property`
  to `../output/json_2026-07-27/`; tooltips from `PublicJSON_FileLayout_20250124.xlsx`), ProTax ARB exports 2022–2024
  (`pt22`–`pt24`, read in place from `Data/denton_prior_download/`), and the 2024/2025 agent and header files (`c24-*`, `c25-*`,
  converted to `../output/cert_<year>/`). Nothing was downloaded.
- Rebuild (S = `~/.claude/skills/create_county_data_profile/scripts`): build_page.py manifest.json profile.json - denton-data-profile.html
  → add_column_review.py denton-data-profile.html → build_source_map.py catalog.json manifest.json source_map.json --drive drive.json
  → add_source_nav.py review/denton-column-review.html source_map.json review/denton-column-review.html manifest.json → republish.
