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
