# Fort Bend County, Texas - Fort Bend Central Appraisal District (FBCAD)

Commercial real property dataset for PTP, built from Fort Bend Central Appraisal District public data (2023-2026). Website: https://www.fbcad.org/. Same folder layout and the same main table as every other county in this package (team standard, see `../README.md`).

Scope: state codes F1 (incl. local F1H/F1M/F1X/F1V), F2, B1-B3 on the improvement or land.

## Folder contents

| Folder | Contents |
|---|---|
| `01_Documentation/` | `research_report.md` (findings, field fill, checks, open questions), `data_dictionary.md` (this county's sources for the shared columns), `source_register.csv` (every public source with URL, date, format, local path), `public_records_request.md` (ready-to-send request for what is not public) |
| `02_Source_Data/` | unchanged downloads: `<year>/` (one folder per tax year; 2025 and 2026 also hold the April preliminary exports = notice values, and 2026 holds the October 2026 Property Data Export = latest values), `gis/` (parcel map files), `derived/parcel_centroids.csv` (point inside each parcel, made from the GIS file), `download_manifest.csv` (path, bytes, sha256, source URL) |
| `03_Reference_Documents/` | `fbcad_file_layouts/` (file layouts, codebooks), `reports_and_guides/` (CAD totals, reports, plans, manuals) |
| `04_Analysis/` | `commercial_properties.csv` (**main table, same columns in every county**, one row per property per tax year, **certified values**) and `<year>/commercial_properties_<year>.csv`, `commercial_sales.csv`, `commercial_sales_unverified.csv` (+ per-year), `code_lookups.csv`, `build_summary.json`, `analysis_summary.json`; `<year>/detail/` and `detail/` = our extra, more detailed tables. **`commercial_reductions/`** = notice value vs final value per commercial property for 2025-2026, with protest reduction totals split PTP clients / everyone else. |

## Headline numbers

| Tax year | Properties | Total appraised (market) value at certification |
|---|---:|---:|
| 2023 | 8,902 | $21.4B |
| 2024 | 9,156 | $24.1B |
| 2025 | 9,353 | $25.1B |
| 2026 | 9,788 | $26.9B |

By type, 2026:

- commercial: 8,617 properties, $18.4B
- industrial: 206 properties, $2.0B
- multifamily: 965 properties, $6.5B

10,162 distinct properties across all years; 9,305 2026 rows have map coordinates. Sales file: 0 verified, 14,702 other deed/transfer records.

### Protest reductions (notice value − final value, commercial)

| Tax year | Properties | Reduced | Total reduction | of which PTP clients |
|---|---:|---:|---:|---|
| 2025 | 9,353 | 4,569 | $4.94B | 2 properties, 0 reduced |
| 2026 | 9,788 | 4,956 | $4.10B | 7 properties, 4 reduced, $284,422 |

See `04_Analysis/commercial_reductions/README.md` for method and caveats.

## Checks done

- 2023, 2025 and 2026 exact to the dollar vs FBCAD certified grand totals; 2024 market exact (assessed 0.001% off)
- 2026 values equal to FBCAD's GIS file for 9,305 of 9,305 accounts
- 3 random properties equal on the FBCAD tax-transparency site
- Notice values (April preliminary export) equal PTP's own recorded notice value for 99.5% of 2025 Fort Bend clients and all filled 2026 rows; final values equal PTP's recorded final value for 99.0% of 2025 clients

## How it was built

Scripts in `../scripts/` (Python 3; source files are never modified): fortbend_extract_commercial.py, fortbend_extract_propertydata.py, fortbend_build_property_table.py, fortbend_value_history.py -> orion_build_shared_schema.py Fort_Bend. Then `verify_shared_schema.py Fort_Bend` (same 67 columns, no duplicates, per-year files, value sums vs our detail tables). Docs: `build_county_docs.py`, manifest: `make_download_manifest.py`. Reductions: `04_Analysis/commercial_reductions/fort_bend_commercial_reductions.py`.

## Known gaps

- FBCAD property search blocks automated access (checked by hand)
- no rent, income or cap-rate data published
- years before 2023 not included
- **no agent of record per account** in any public file: PTP clients are identified from PTP's own records, not from agent code A0830173
- **no protest list or ARB outcomes** published: any notice-to-final decrease is counted as a reduction (CAD corrections and splits are flagged, <1% of dollars)

Collected and checked 2026-10-12; protest reduction data added 2026-11-16.
