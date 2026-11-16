# Fort Bend — corrections, 2026-11-16

These are full replacement copies of files in `Fort_Bend/` on the shared drive. The originals can only be replaced by someone with edit rights on them. Until then, this folder is the current version.

| Replace this file | With this copy | What was wrong / missing |
|---|---|---|
| `README.md` | `README.md` | It did not mention the protest reduction table or the new source files. "Known gaps" did not list the agent and protest gaps. |
| `01_Documentation/research_report.md` | `research_report.md` | §3 implied no pre-protest value exists, but FBCAD's **preliminary exports** hold the notice value for every account. §6 left out the post-certification changes (2025 commercial: −$1.21B on 1,296 accounts through the Oct 2026 roll). §8 is now out of date. §9 is new and describes the protest reduction work. |
| `01_Documentation/source_register.csv` | `source_register.csv` | Preliminary exports, supplements and the October 2026 Property Data Export were not listed. |
| `01_Documentation/data_dictionary.md` | `data_dictionary.md` | No entry for the reduction tables. |
| `01_Documentation/public_records_request.md` | `public_records_request.md` | It did not ask for agent of record or protest/ARB outcomes, which are the two items that can't be filled from public files. |
| `02_Source_Data/download_manifest.csv` | `download_manifest.csv` | The 5 newly uploaded source files were not listed. |

New files (uploaded directly to their place):
- `02_Source_Data/2025/2025_04_01_1551-Orion-2025-Preliminary-Export-Updated.zip`: 2025 notice values
- `02_Source_Data/2025/2025_05_06_0636-Orion-2025-Preliminary-Export-Redacted.zip`: 2025 notice values, fallback
- `02_Source_Data/2026/2026_04_21_0828-Orion-2026-Preliminary-Export-Redacted.zip`: 2026 notice values
- `02_Source_Data/2026/2026_06_15_1742-Orion-2026-Preliminary-Export-Redacted-2.zip`: 2026 notice values, fallback
- `02_Source_Data/2026/October2026-PropertyDataExport.zip`: final values for 2025 and 2026
- `04_Analysis/commercial_reductions/`: summary, detail, client lists used, script, README

The existing `commercial_properties*.csv` values were checked against the certified rolls and are correct (2025 $25,130,621,026; 2026 $26,853,769,275, both exact). They are certified values only. Use `04_Analysis/commercial_reductions/` for notice and final values.
