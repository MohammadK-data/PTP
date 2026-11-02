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
