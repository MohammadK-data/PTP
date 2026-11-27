# Bexar data profile

Working files for the Bexar Property Data Profile and its team column-review workspace (create_county_data_profile skill).

- Profile page: https://claude.ai/artifact/QboBF1Z4Qmn5gDfb9SHayg
- Column review workspace: https://claude.ai/artifact/VPchNWnTYUXVcaBJiNehVq (db + user capabilities)

Sources (59 datasets): PACS Appraisal Export Mar 28 prelim (8.0.0.33, keys `p26-*`) and as of supp 298 (files dated
Oct 15, 8.0.0.34, `s26-*`), converted by `../etl/bexar_appraisal_export_etl.py` with the layout built from BCAD's 8.0.34
workbook by `../etl/bexar_pacs_layout_build.py`; Agent Export of Oct 26 (`ag-*`; BCAD's zip holds headerless
pipe-delimited .txt, converted to the CSV folder by `../etl/bexar_agent_export_to_csv.py`); Property Summary Mar 28 and
Oct 13 (`ps26a`, `ps26s`). The March summary ships without a header; `output/... (with header).csv` is the same file
with BCAD's header line on top.

- `catalog.json`: BCAD has no data-downloads page on bcad.org (checked 2026-11-27). The exports come on request
  through BCAD's FTP server, so the catalog lists the exports we received under BCAD's own names, grouped by export.
  Every link opens BCAD's Public Information Act help page, with `#/<file name>` appended so the workspace shows the
  file's name and type. The Non-Agent Export (Oct 21) is listed but not profiled.
- `drive.json`: Google Drive › Bexar › Public Information. Only documents are there; none of the export zips are.
- `source_fields.py`: adds each dataset's `raw` (zip member name) and `layout`, and rewrites page texts so they name
  no local folder or script (`add_source_nav.py` refuses a page that does).

Rebuild (S = the skill's `scripts` folder):
`python3 make_manifest.py && python3 descriptions.py && python3 notes.py && venv/bin/python -I source_fields.py`,
then `./run_profile.sh` (profiles anything not yet in profile.json), then
`venv/bin/python -I $S/build_page.py manifest.json profile.json - bexar-data-profile.html`
→ `$S/add_column_review.py bexar-data-profile.html`
→ `$S/build_source_map.py catalog.json manifest.json source_map.json --drive drive.json`
→ `$S/add_source_nav.py review/bexar-column-review.html source_map.json review/bexar-column-review.html manifest.json`
→ republish both files to the links above (omit `capabilities` so saved decisions and notes stay).
Note: `make_manifest.py` copies the PACS datasets from Travis's manifest, which has changed since; re-running it may
pull in Travis edits. To change only Bexar texts, patch manifest.json (as `source_fields.py` does) instead.
`facts.py` re-runs the DuckDB queries behind the notes.

`venv` is a symlink to Rockwall's (duckdb).
