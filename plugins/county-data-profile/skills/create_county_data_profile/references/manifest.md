# Manifest reference

One JSON file per county drives everything. `examples/` has a complete, working manifest from one county
(39 website files, 26 API endpoints, 3 coming-soon placeholders); copy it and edit rather than starting blank.

```jsonc
{
  "title": "<County> Property Data Profile",             // <title> and <h1>
  "eyebrow": "<County> Appraisal District · Website files and Agent Portal API",
  "intro": "Everything <County> CAD makes available to us, ...", // HTML allowed
  "store_key": "<county>-view",                           // localStorage key for the last view; unique per county
  "foot": "Generated {date}. ...",                        // optional; {date} is filled in. Default text covers DuckDB caveats
  "date": "November 2, 2026",                             // optional; default today
  "max_year": 2026,                                       // dates/years after this are reported as typos
  "root": "<absolute path to the county folder>/",       // file paths below are relative to this
  "sample": {"rows": 100},                                // optional; random rows per file for the Sample rows table

  "datasets": {
    "y2025": {                                            // key: letters/digits/dashes; used in URLs (#y2025.Column)
      "path": "output/PropertyData_2025.csv",
      "read": "csv",                                      // csv | pipe_utf16 | pipe_latin1 | pipe_utf8 | {"opts": "<duckdb read_csv options>"}
      "label": "2025",                                    // button text (years: the year; file sets: "1 · Account")
      "about": "One row per account ...",                 // one-line description shown above the facts
      "encoding": "CSV, UTF-8",                           // shown on the File size tile
      "compare": "y2024",                                 // previous year of the same file -> new/dropped columns
      "compareLabel": "the 2024 file",                    // optional wording for the compare notes
      "renames": {"Market Area": "Neighborhood"},         // new name -> old name, so renames aren't listed as new/dropped
      "force": {"ASN": "Code (numeric text)"},            // override an inferred type label (shifted rows, ids); values are untouched
      "notes": ["Plain-HTML bullet; quote exact counts"],  // "Things to know about this file"
      // for the review workspace (references/sources.md); never shown as paths
      "raw": "PROP.TXT",                                  // the file's name inside the CAD download; default: path's file name
      "layout": "File #2 · Property (layout .xlsx)",      // what documents it; default: the catalog file's "layout"
      "nav_label": "Property",                            // optional sidebar name
      "sample_rows": 25,                                  // optional; fewer sample rows for very wide rows (drawings as JSON), to stay under the 16 MB page limit
      "table": "owners.agents", "json_path": "owners.agents"  // set by add_tables.py; table name, JSON list path
    },
    "supp26": {"placeholder": true, "label": "Not available yet",
               "about": "The 2026 supplemental files are not provided on the website yet. Coming soon."},
    "api-agent-properties": {"notes": ["..."]}            // api-* keys only add notes/label/about to profiled endpoints
  },

  "descriptions": {"Account_Num": "Account number ..."},             // column tooltip, by column name
  "descriptions_by_set": {"agent-2_Building:AppraisedValue": "..."}, // "<dataset key>:<column>" wins over the above
  "descriptions_by_prefix": {"comp:Quality": "..."},                 // "<key before first dash>:<column>"
  // nested API fields ("user.email") fall back to the leaf name ("email")

  "sources": [
    {"id": "web", "label": "CAD website files", "sub": "{n} bulk files · every account in the county",
     "desc": "Bulk exports downloaded from ...", "start": "y2026",
     "groups": [
       {"id": "property", "label": "Property Data", "desc": "...",
        "years": [{"label": "2024", "datasets": ["y2024"]},
                  {"label": "2025", "datasets": ["y2025"]},
                  {"label": "2026", "datasets": ["supp26"], "pending": true}]}   // pending -> "coming soon"
     ]},
    {"id": "api", "label": "Agent Portal API", "sub": "{n} endpoints · properties we represent",
     "desc": "...", "start": "api-agent-properties", "groups": "from_api"}       // groups come from api.json
  ],

  "api": {                                                // optional
    "spec": "/path/to/Docs.yaml",
    "groups": [{"id": "props", "label": "Properties & protests", "endpoints": ["Agent Properties", "..."]}],
    "labels": {"Agent Confrence Configuration": "Conference configuration"},   // by operation summary
    "about":  {"Agent Properties": "Every property the agent represents ..."},
    "filters": {"schema": "agent_properties_with_filter", "endpoints": ["Agent Properties"]},
    "auth_overrides": {"Agent Token": "Email and password ..."},
    "token_auth_text": "Agent JWT in authorization header"
  }
}
```

## Conventions that keep the page consistent

- **Every website group uses `years`**, even with one file per year, so all tabs share the year switch.
  A year with several files (Agent Summary, Supplemental) shows file buttons under the switch; give the
  same file the same position in each year so switching years stays on that file.
- **Years the CAD hasn't published** get a placeholder dataset and `"pending": true` in the group's year list.
  Use the same wording every time: "The 2026 <name> files are not provided on the website yet. Coming soon."
- **Keys**: property years `y2024`; other files `<short>-<year>` (`comp-2025`, `exempt-2025`) or
  `<short><yy>-<file>` for per-year file sets (`agent25-1_Account`). Keys already published should not
  change, because people bookmark `#key` links.
- **compare** every year to the year before; add `renames` when headers were rewritten.
