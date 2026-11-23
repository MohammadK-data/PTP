# Source files: catalog.json and drive.json

The review workspace's sidebar mirrors the CAD website's public-information page, and ties every table on the
page to the website file it comes from. Both files are written per county, from what you see on the website and in
the team's Drive; nothing about them is fixed in the scripts.

## catalog.json - what the website publishes

Read the CAD's public-information / data-download page (and any pages it links for each group). Keep the website's
own words for section, group and file names, in the website's order.

```jsonc
{
  "page": {
    "label": "<CAD name> · Public Information",   // shown in "About this page"
    "url": "https://<cad site>/<page>",
    "short": "<short CAD name>",                   // link text on the page: "<short> ↗", "Open on <short> ↗"
    "checked": "YYYY-MM-DD"                        // the day you read the page
  },
  "sections": [                                    // the page's top-level headings; one if it has none
    {"name": "<section>", "groups": [
      {"name": "<group heading>",
       "desc": "<one line: what this group holds and why someone would open it>",
       "files": [
         {"name": "<link text>", "url": "<link>",
          "role": "data",                            // data | layout | doc (default doc)
          "id": "<short id>",                        // optional; default from the name. Keep it stable
          "note": "<what someone should know: which snapshot we profiled, a newer upload we don't have ...>",
          "tables": ["<dataset key or glob>", ...],  // the manifest datasets profiled from this download
          "layout": "<what documents its tables>",   // default for datasets without their own "layout"
          "contents": ["<file inside the zip>", ...] // or "local": "<folder or .zip under the manifest root>"
         }]}]}]
}
```

- **tables** is what makes a file a data file in the workspace: it expands into those tables. Use globs over keys
  (`"c26-*"`) when a download's datasets share a prefix. `build_source_map.py` fails if a profiled dataset belongs
  to no file, or to two.
- **local** lists the folder's files or the zip's members into `contents` at build time and is not written to
  the map. Use it for downloads we keep; write `contents` by hand for nested zips or files we only saw online.
- Per dataset (in the manifest): `raw` is the file's name inside the download when ours differs (a converted
  `.csv.gz`, a record type in a mixed file: `"<file> · <TYPE> rows"`, a JSON list: `"owners[].agents[]"`);
  `layout` names the document and entry that describes it (`"File #2 · Property (<layout file>)"`).
  `nav_label` overrides the sidebar name. By default it is the dataset label without its `N · ` prefix, or the
  group label when the dataset is the only one in its year and its label only repeats that year's label.
- When the website now links a newer upload than the one we profiled, keep the website link and say so in `note`.

## drive.json - the team's copies (optional)

List the county's Drive folder with the Google Drive connector (`search_files` with the folder as parent, then
each subfolder). Record ids only; the page builds the links.

```jsonc
{
  "source": "Google Drive · <folder path people know>",
  "checked": "YYYY-MM-DD",
  "folders": {"_root": "<folder id>", "<group name exactly as in catalog.json>": "<folder id>"},
  "files": {"<file name in Drive>": "<file id>"}
}
```

Files are matched to catalog files by the website file name (URL-decoded). A `-<digit>` before the extension is
ignored on either side, since websites rename duplicate uploads (`report-1.pdf`). Unmatched website files show
"Not in our Drive"; tell the user which, rather than guessing a match.
