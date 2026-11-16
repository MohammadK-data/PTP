# Bexar data profile

Working files for the Bexar Property Data Profile and Column Review pages (create_county_data_profile skill).

- Profile page: https://claude.ai/artifact/QboBF1Z4Qmn5gDfb9SHayg
- Column review: https://claude.ai/artifact/VPchNWnTYUXVcaBJiNehVq (db + user capabilities)

Sources (59 datasets): PACS Appraisal Export Mar 28 prelim (8.0.0.33, keys `p26-*`) and Oct 15 as of supp 298
(8.0.0.34, `s26-*`), converted by `../etl/bexar_appraisal_export_etl.py` with the layout built from BCAD's 8.0.34
workbook by `../etl/bexar_pacs_layout_build.py`; Agent Export CSV of Oct 26 (`ag-*`); Property Summary Mar 28 and
Oct 13 (`ps26a`, `ps26s`). The March summary ships without a header; `output/... (with header).csv` is the same file
with BCAD's header line on top.

Rebuild: `python3 make_manifest.py && python3 descriptions.py && python3 notes.py`, then
`./run_profile.sh` (profiles anything not yet in profile.json), then
`venv/bin/python -I ~/.claude/skills/create_county_data_profile/scripts/build_page.py manifest.json profile.json - bexar-data-profile.html`,
then `python3 decide.py && python3 ../../_review/add_column_review.py --seed seed.json bexar-data-profile.html`,
then republish both files to the links above. `facts.py` re-runs the DuckDB queries behind the notes.

`decide.py` holds the suggested Need/Maybe/Drop decision and comment for every column (rules documented at the top);
the review page shows them as "Claude (suggested)" until someone saves their own decision.
`venv` is a symlink to Rockwall's (duckdb).
