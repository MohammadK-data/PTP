# Travis data profile

Working files for the Travis Property Data Profile page, built with the `create_county_data_profile` skill.

- Published page: https://claude.ai/artifact/Qhnt4M9PBBmL16FqwDbPAs
- Travis publishes the same PACS 8.0.0.33 Appraisal Export as Denton (same record widths and field positions), so
  `../etl/travis_appraisal_export_etl.py` parses it with Denton's `etl/pacs_appraisal_export_layout.json` and writes
  gzipped CSVs to `../output/<export date>_2026_<RECORD>.csv.gz` (Denton's record names; DuckDB reads .gz directly)
- `manifest.json` describes datasets, tabs, notes and column descriptions (40 datasets: 20 PACS files × 2 exports,
  keys `c26-*` certified Jul 18 and `s26-*` supp 3 Oct 6). It started as a copy of Denton's manifest
- Every dataset reads with `quote='"'` pinned: with auto-detection DuckDB took `'` as the quote in the abstracts file
  and mangled names like `AUSTIN'S COLONY`
- `profile.json` holds the DuckDB full-scan profiles, with 100 sample rows per set
- `travis-data-profile.html` is the last published build
- `venv/` has duckdb (not committed)

To add an export: run the ETL on the new folder, add its datasets to `manifest.json` and a new entry to each group's `years`, then run
`venv/bin/python -I ~/.claude/skills/create_county_data_profile/scripts/profile_files.py manifest.json profile.json <keys>`,
then `build_page.py manifest.json profile.json - travis-data-profile.html`,
then republish to the same artifact link.

## Review workspace (generic skill pipeline, from 2026-11-23)

- `catalog.json`: the traviscad.org/publicinformation page (sections, groups, files, links) and which datasets each
  download holds. `drive_files.json`: our Drive copies. Per-dataset `raw`, `layout` and `nav_label` are in `manifest.json`.
- Rebuild (S = `~/.claude/skills/create_county_data_profile/scripts`, run with `venv/bin/python -I`):
  1. `$S/build_page.py manifest.json profile.json - travis-data-profile.html --allow-missing`
  2. `$S/add_column_review.py travis-data-profile.html`
  3. `$S/build_source_map.py catalog.json manifest.json source_map.json --drive drive_files.json`
  4. `$S/add_source_nav.py review/travis-column-review.html source_map.json review/travis-column-review.html manifest.json`
  5. republish `review/travis-column-review.html` to https://claude.ai/artifact/R5VF8TuPcywvHkqDJke9GX (omit capabilities)
- Superseded by the skill's generic scripts (kept for reference): `make_source_map.py`, `add_json_datasets.py`,
  `../etl/travis_json_flatten.py` (→ `flatten_json.py --keys pID,pYear --root property`),
  `../etl/travis_ears_split.py` (→ `split_record_types.py --fields ../Data/ears_download/ears_fields.json`),
  and `../../_review/` (→ the skill's `add_source_nav.py` and assets).
