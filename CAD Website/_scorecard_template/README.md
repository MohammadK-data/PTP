# County scorecard template (copied from the Travis 2026 build)

Pieces of the Travis artifact (https://claude.ai/artifact/NqFrCut52SWBXXn51K5vYa), for reuse in other counties.

- `base.css` – scorecard CSS (same as the County Scorecards page).
- `body.html` – scorecard sections (Travis wording: header, draft note, method, open questions).
- `app.js` – scorecard script. Reads `<script id="data" type="application/json">` (D: cols, cube, tiers, firms, open, matched, grids, acct, checks, hasHS).
- `build_travis_page.py` – builds D (data.json), lookup/<county>.json and acct/<county>/* search shards from the one-row-per-property values CSV.
- `shell_index_travis.html` – the outer page (Scorecards / Account search bar, neighborhood lookup, account search). Edit `const C`, `const LK`, `const AS`, the search intro text and the default county.

Assembly (Travis): <county>.html = doctype + fonts + `<style>`base.css`</style>` + body.html + data JSON (escape `</`) + `<script>`app.js`</script>`.
Publish index.html with files: <county>.html, lookup/<county>.json, acct/<county>/*.txt.

Upstream ETL for Travis: `CAD Website/Travis/etl/travis_protax_extract_2026.py` (one pass over the protax JSON with the byte index) and `travis_values_2026_build.py` (one row per property, certified-roll fallback).
