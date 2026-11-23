---
name: create_county_data_profile
description: Build or update a data profile Artifact for a Texas county appraisal district (CAD) from whatever it publishes: export files (fixed-width, delimited, Excel, JSON special exports, multi-record state submissions, reports) and, optionally, the agent portal API. For every table: columns, types, fill rates, distributions, sample rows, quirk notes and column tooltips, with a year switch. Also builds the team column-review workspace: a sidebar mirroring the CAD website's public-information page with website and Drive links, tables under the files they come from, a breadcrumb, a data preview, and blank Need / Maybe / Drop decisions and notes per column. Use it to profile or document a county's CAD files or portal endpoints, add files, exports or years to a county page, map tables to their website files, or start the report for another county.
---

# County data profile

One HTML Artifact per county documents every table the CAD publishes, plus a **column-review workspace** copy
the team uses to decide which columns we need. Nothing in the scripts knows a county: what the CAD publishes,
how its files are shaped and how its website is organised are read from the county's own files and website,
and written into per-county JSON files (`manifest.json`, `catalog.json`, `drive.json`).

**The page shows the data exactly as published.** Nothing is trimmed, blanked, redacted or left out of a chart:
zeros, placeholder dates, typo years, padded values, names and addresses appear as they are. Conversions
(JSON → tables, one file → one table per record type, Excel → CSV) change the shape, never a value. Describe
quirks in notes.

**The published pages never show where files live on our machines.** Tables are named by the CAD's own file
(the raw name inside its download), never by our folders. `add_source_nav.py` refuses to write a page that holds
an absolute path, a script name, or the manifest's root or data folders.

## Scripts

| Step | Script | Output |
|---|---|---|
| JSON export → one table per nested list | `flatten_json.py <file.json> <out> [--keys a,b] [--root name]` | `<out>/*.csv.gz`, `_tables.json` |
| Headerless multi-record file → one table per record type | `split_record_types.py <file> <out> [--fields layout.json]` | `<out>/<TYPE>.csv.gz` |
| Excel sheet, or CSV parts with one header → one table | `to_csv_gz.py <out.csv.gz> <input...> [--sheet name]` | one `.csv.gz` |
| Add a folder of tables to the manifest | `add_tables.py manifest.json <folder> --prefix p --group id --year "label"` | manifest datasets + group year |
| Profile files with DuckDB (full scan, 100 random sample rows) | `profile_files.py manifest.json profile.json [KEY...]` | profile.json |
| Add sample rows to sets profiled before samples existed | `profile_files.py manifest.json profile.json --sample-only [KEY...]` | profile.json |
| Profile portal endpoints from the spec's examples | `profile_api.py manifest.json api.json` | api.json |
| List anomalies worth a note | `find_anomalies.py manifest.json profile.json [KEY...]` | stdout |
| Build the profile page | `build_page.py manifest.json profile.json api.json\|- out.html [--allow-missing]` | the page |
| Make the column-review copy | `add_column_review.py <county>-data-profile.html` | `review/<county>-column-review.html` |
| Map every table to the website file it comes from | `build_source_map.py catalog.json manifest.json source_map.json [--drive drive.json] [--api api.json]` | source_map.json |
| Turn the review copy into the workspace | `add_source_nav.py <review.html> source_map.json <out.html> manifest.json` | workspace page |

Each script's docstring has its full options. Assets: `template.html` (profile page), `review.css`/`review.js`
(decisions and notes), `source_nav.css`/`source_nav.js` (workspace). Change them only for layout changes the user
asks for; data, wording and structure live in the per-county JSON files.

Read `references/manifest.md` before writing a manifest, `references/sources.md` before writing catalog.json or
drive.json, and `references/lessons.md` (encodings, placeholders, joins, conversions) before converting files or
writing notes. `examples/` holds a finished manifest from one county: borrow column descriptions where the meaning
is the same; don't copy its groups, keys or file list - every county's are its own.

## Where things live
- Keep each county's working files in one lasting folder, such as `<county>/profile/`: `manifest.json`,
  `catalog.json`, `drive.json`, `profile.json`, `api.json`, `source_map.json` and the built pages. Converted
  tables go next to the county's other outputs (for example `<county>/output/<export>/`). The scratchpad is wiped
  between sessions. If the user has no such folder, ask where to keep it.
- Python: make a venv once (`python3 -m venv venv && venv/bin/pip install duckdb pyyaml openpyxl pypdf`), in the
  background. Run the scripts with `venv/bin/python -I`.
- Run independent long jobs (several conversions, profiles or downloads) in parallel, in the background.

## New county
1. **Website inventory.** Open the CAD's public-information / data-downloads page (ask the user for it if you
   can't find it). Record every section, group and file with its link, and what each group is for, in
   `catalog.json` (`references/sources.md`). Mark each file's role: data (we profile it), layout (documents the
   data files) or doc. Note the date you checked.
2. **Local inventory.** List what the user already has (`find <root> -type f`) and match it to the catalog.
   Download missing data files only when the user asks, into the county's data folder. For each candidate file
   check, from the file itself: format (`file`, `head -c 400 | xxd`), encoding, delimiter, header or not,
   record-type field, JSON shape, sheet names (look for a data dictionary sheet), and the year in the data versus
   the folder or file name.
3. **Convert what DuckDB can't read as one table** (keep the original; write converted tables to a new folder):
   - JSON special export → `flatten_json.py`. It detects the shape and the record key; check the printed key
     against the data (it was unique in the first 5,000 records only) or pass `--keys`.
   - Headerless file with several record types → `split_record_types.py`, with a `--fields` JSON built from the
     layout document (the manual's field tables, read with `pypdf`, or the layout sheet). Field counts can differ
     by year: check each year's row width against the layout release it came with.
   - Fixed-width exports → an ETL driven by the CAD's layout file (positions and lengths) to CSV, kept in the
     county's etl folder. Layouts differ by CAD software and version: read the county's own, never assume one.
   - Excel sheets, or a report split into parts with one header → `to_csv_gz.py`.
   - Plain delimited files need no conversion; set `read` in the manifest.
4. **Manifest.** Set title, eyebrow, intro, store_key and root (`references/manifest.md`). Add datasets with
   `add_tables.py` (one call per folder and year/snapshot; it keeps table order across years) or by hand. Every
   group uses `years`, even with one entry. Set `compare` to the year before, `raw` (the file's name inside the
   CAD download, when it differs from ours) and `layout` (what documents it). Placeholders with `"pending": true`
   for years the CAD hasn't published.
5. **Profile.** Run `profile_files.py` in the background; it handles each file in its own process, smallest first,
   and resumes if interrupted. Check the `done ...` lines and rejected counts; compare row counts with `wc -l`.
6. **API (if there's a portal spec).** Add the `api` section and run `profile_api.py`. Its statistics come from the
   docs' example responses, so they describe a sample; say so in the source description.
7. **Notes.** Run `find_anomalies.py`, confirm each fact with an exact DuckDB query, and write 1–4 notes per
   dataset: what someone loading or joining the file must know, with exact counts and `<code>` column names.
   Check the join keys between files (and to portal ids) and state the result.
8. **Descriptions.** `build_page.py` lists every column without a tooltip. Use the CAD's data dictionary or layout
   text first, borrow from `examples/` where the meaning is the same, and write the rest in plain language. Use
   `--allow-missing` only when the user accepts a page with gaps; tell them how many.
9. **Build and check the profile page.**
   - Run `build_page.py`.
   - Serve the folder locally (a `python3 -m http.server --directory <folder>` entry in `.claude/launch.json`,
     then `preview_start`) and run `scripts/verify_page.js` in the browser tool: expect `bad: []` and no console
     errors. Hover one column name. Delete the launch.json entry afterwards.
   - Grep the HTML for `eyJ` (JWTs), `X-Amz-` (pre-signed links), `password` and email addresses. The page keeps
     them as published; tell the user what and where before publishing.
10. **Publish the profile page.** Load `artifact-design` if this session hasn't. Publish with icon `chart`.
11. **Column-review workspace.**
    - `add_column_review.py <county>-data-profile.html` → `review/<county>-column-review.html`.
    - `build_source_map.py catalog.json manifest.json source_map.json --drive drive.json`. It fails until every
      profiled dataset belongs to exactly one catalog file (`tables` patterns): that is the check that every table
      is traced to a website file. The Drive listing comes from the Google Drive connector (`references/sources.md`);
      leave out `--drive` if the team keeps no copies. With a portal API, pass `--api api.json` and give the portal its
      own catalog section (one file per endpoint group, `link_label` for the docs link), so endpoints appear too.
    - `add_source_nav.py review/<county>-column-review.html source_map.json review/<county>-column-review.html manifest.json`
      (in place; it refuses a page that already has a map, so always start from a fresh `add_column_review.py` copy).
    - Check it in the browser: Home shows only the hint; a group shows its summary; a data file expands into its
      tables; breadcrumb menus list each level's children; the Data preview / Columns / About tabs work; no
      console errors.
    - **Every decision and every comment starts blank.** Never pick Need / Maybe / Drop and never write comments,
      not in the page and not in its database.
    - Publish as its own artifact with icon `checklist` and `capabilities: {"db": {}, "user": {"scopes": ["profile"]}}`
      (load `artifact-capabilities` first). Decisions and notes live in `decisions` and `notes`, keyed by group id
      and file position, so a decision applies to the same file in every year. A new page's collections list empty.

## Updating an existing county
Typical requests: a new year or export, a new kind of file, a website change, layout changes.
1. Find the manifest, profile.json and catalog.json. If they're lost, rebuild them from the published pages: the
   `<script id="data">` block holds every set's profile and texts, and `<script id="srcmap">` the source map.
2. Convert and add the new tables (steps 3–4 above), profiling only the new keys:
   `profile_files.py manifest.json profile.json KEY1 KEY2`. Keep the same file order in each year.
3. Re-check the website page; update catalog.json (new files, changed links, the checked date) and drive.json.
4. Notes and descriptions for the new keys, then rebuild the profile page, the review copy, the source map and the
   workspace, and republish both to their existing artifacts (omit `capabilities` so saved decisions and notes
   stay). Don't change existing keys, group ids or file order: bookmarks and saved decisions depend on them.
5. Pages built before sample rows existed: `profile_files.py --sample-only` (background) fills only missing samples.
6. Never change the values of existing data unless the user asks.

## Reporting back
Give both links (profile and workspace) and what changed, then the findings that matter: a folder whose year
doesn't match its data, a file much smaller than the year before, renamed columns, a join that partly fails,
website files we don't have, encodings that garble text. List which tooltips are best guesses. Don't paste the
notes back word for word.
