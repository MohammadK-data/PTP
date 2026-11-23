# Dallas data profile

Working files for the Dallas Property Data Profile and its team column review, built with the `create_county_data_profile` skill.

- Column review: https://claude.ai/artifact/CeDRYoC93Sxv8DtUdko7zn
- `manifest.json`: datasets, groups, notes, descriptions; per-dataset `raw` is the file name inside the DCAD download.
- `catalog.json`: dallascad.org/DataProducts.aspx (5 groups, 42 downloads, checked 2026-11-23); links go through DCAD's
  `ViewPDFs.aspx` with the file's server path. `drive.json`: County Playbooks › Dallas › Public Information (no data copies there).
- Added 2026-11-23: ARB current and archive (`arb-*`), and ACCOUNT_APPRL_YEAR / APPLIED_STD_EXEMPT from the 2024 and 2025
  current exports (`u24-*`, `u25-*`), all read in place from `../Data/dcad_download_20261114/`. Nothing was downloaded.
- The roll CSVs behind `r26-REAL_ROLL` / `r26-BPP_ROLL` are no longer in `../output/`; their profiles stay in profile.json.
- Rebuild (S = `~/.claude/skills/create_county_data_profile/scripts`): build_page.py manifest.json profile.json - dallas-data-profile.html
  → add_column_review.py dallas-data-profile.html → build_source_map.py catalog.json manifest.json source_map.json --drive drive.json
  → add_source_nav.py review/dallas-column-review.html source_map.json review/dallas-column-review.html manifest.json → republish.
