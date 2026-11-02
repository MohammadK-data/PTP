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
