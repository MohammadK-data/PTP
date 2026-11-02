# Denton live page (Protax JSON + PACS tables + correction changes)

Builds the published page https://claude.ai/artifact/J85FsXFMftJrVDht43z4sZ. This is a different page from
`../denton-data-profile.html` (PACS tables only). Values are shown exactly as the files hold them: nothing is
trimmed, hidden or left out of the charts.

- `dprof.py`, `merge.py`: stream-profile `~/Downloads/Denton/Denton-protaxExport-20260727.json` (about 2.5 min, 6 workers);
  each table gets 100 random sample rows. Output `merged.json`.
- `../profile.json`: the PACS tables, from the skill's `profile_files.py` (see `../README.md`).
- `cdiff.py`: the certified → supplement 3 changes from `output/diff_2026-07-27_vs_2026-10-14`. Output `changes.json`.
- `assemble.py`: puts all of it into the page's layout, labels, notes and descriptions.
- `base-page-2026-10-29.html`, `live_data.before-rebuild.json`: the page as published on 29 Oct, which `assemble.py`
  uses as its base.

Rebuild:
```
python3 -I dprof.py ~/Downloads/Denton/Denton-protaxExport-20260727.json parts 6 2026
python3 -I merge.py parts merged.json
python3 -I cdiff.py ../../output/diff_2026-07-27_vs_2026-10-14 ../../output/2026-10-14_2026_APPRAISAL_INFO.csv live_data.before-rebuild.json changes.json
python3 -I assemble.py base-page-2026-10-29.html live_data.before-rebuild.json denton-live-profile.html
```
then republish `denton-live-profile.html` to the link above.
