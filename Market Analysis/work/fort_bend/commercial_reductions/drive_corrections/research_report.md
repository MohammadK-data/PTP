# Fort Bend County — Commercial Data Guide

> **Re-organized 2026-10-12 to the team standard (same as every county):** main clean table `04_Analysis/commercial_properties.csv` (one row per property per year, same 67 columns in all counties, per-year copies in `04_Analysis/<year>/`); the tables described below are now in `04_Analysis/<year>/detail/`; links are in `source_register.csv`; file layouts in `03_Reference_Documents/fbcad_file_layouts/`, totals and reports in `03_Reference_Documents/reports_and_guides/`, GIS in `02_Source_Data/gis/`.
>
> **Updated 2026-11-16:** notice (pre-protest) values and latest (post-protest) values added for 2025-2026 → `04_Analysis/commercial_reductions/`. See §3, §6, §8 and the new §9.

For data engineers working on PTP commercial protests. Written 2026-10-09.

## 1. Where the data comes from

FBCAD runs **Orion** (Tyler Technologies / True Prodigy). This is a different system from the PACS
"Legacy" fixed-width exports used by Denton and Travis, and from HCAD's own PDATA files. These public files are used:

| File | Format | What it gives |
|---|---|---|
| Orion certified export (zip) | CSV with header, layout in `03_Reference_Documents/Orion_Appraisal_Export_Layout.xlsx` | Property, owner (values per owner), entity (values per taxing unit), exemptions, agents |
| Orion **preliminary** export (zip) | same layout as certified | Same tables before protests. FBCAD posts several snapshots a year (Mar–Jul). The **April** snapshot holds the values on the appraisal notices. |
| Commercial Segments | xlsx (2024-2026), CSV in zip (2023) | One row per Marshall & Swift building section: area, use (occupancy code), quality, year built, effective year, stories, RCN, RCNLD, depreciation |
| Property Data Export | zip of CSV files | Land lines, improvement list, deed history (no prices), residential-style segments (area hidden for commercial). The Property file has `CurrMarketValue` (roll year) and `MarketValue` (prior year), as of the export date. |

Join key everywhere: **`QuickRefID`** (e.g. `R101338`) = `PropertyQuickRefID` in Orion = `property_id` in our tables.
`PropertyNumber` (e.g. `5920-01-000-0102-907`) is the geographic account number shown as `geo_number`.

## 2. How commercial is selected
State code (PTD) starting with **F** or **B** on `StateCodeLand` or `StateCodeImp`.
FBCAD sub-codes: `F1` commercial, `F1H` (hotel/hospitality), `F1M`, `F1X`, `F1V`, `F2` industrial, `B1`-`B3` multifamily.
(`StateCodeImp` holds the code of the FIRST improvement only, so a few rows show A1/A3 etc. when the land is F/B.)
Totally exempt commercial property (churches, schools, government) is mostly re-coded `XV` by FBCAD, so it is
NOT in this set — only 13 properties in 2026 carry an `EX` exemption. This differs from Travis/Denton.

## 3. Values
- Orion stores values **per owner** (Owner record: `ImpHSValue`, `ImpNHSValue`, `LandHSValue`, `LandNHSValue`, `AgMktValue`, `TimMktValue`).
  We add them up per property: `market_value = improvement + land + ag market + timber market`.
  35 commercial properties in 2026 have more than one owner row (`n_owner_rows`).
- `county_g01_*` = market / assessed / taxable for Fort Bend County General (entity `G01`) from the Entity file, summed over owners.
  98.4% equal `market_value`; the rest are split-jurisdiction parcels (part of the parcel outside the county unit).
- `cbl_cap_adj` = circuit-breaker (Tax Code 23.231) limit; 937 commercial properties had one in 2026.
- `arb_protest_flag` = 1 if the protest was still open at certification (215 in 2026, 135 in 2025). It does **not** mark every protest. There is **no ARB hearing result file**
  in the public export — FBCAD does not publish ARB outcomes like HCAD does.
- **Notice (pre-protest) value IS available:** the April Orion preliminary export (2025-04-01, 2026-04-21) holds every account's value as noticed. It matched PTP's own recorded notice value for 99.5% of 2025 Fort Bend clients and for every filled 2026 row. `commercial_properties.csv` does not carry it (shared schema has no such column); it is in `04_Analysis/commercial_reductions/`.
- **Final (post-protest) value:** the certified roll is not final for protests open at certification. The October 2026 Property Data Export gives the latest 2026 value and the latest 2025 value (prior-year column). It matched PTP's recorded 2025 final value for 99.0% of clients.

## 4. Buildings (Commercial Segments file)
- `fMSSecType = 1` = a building section; `2` = site improvements / units (paving, fencing, mobile home park pads, etc.).
- Area = `vMVPSeg_CalcArea` (equals `fOvrArea` when the appraiser overrode the sketch, otherwise `fApexArea`).
- `building_sqft` = sum of section areas of all building sections. `primary_*` fields come from the largest section.
- `vMVPSeg_TitleForMS` = Marshall & Swift occupancy (e.g. `344: Office Building`, `406: Storage Warehouse`, `412: Neighborhood Shopping Ctr`).
- `fQuality` 0.5-5.0 = M&S quality class (2.0 average). `vMVPSeg_MSRCN` / `MSRCNLD` = replacement cost new / less depreciation.
- Properties with no building section (1,906 in 2026): vacant land (~560), small multifamily B2 (valued with
  residential segments — not in this file), and industrial F2 (power plants, solar, battery storage valued without M&S).

## 5. Checks done
| Check | Result |
|---|---|
| 2026 entity G01 rows vs Grand Totals PDF (ARB approved 414,252 + under review 32,720) | **446,972 = 446,972 exact** |
| 2026 G01 assessed and taxable vs PDF | **$165,398,669,693 and $133,532,246,624 — exact** |
| 2026 G01 market vs PDF | $185,034,293,556 vs $185,034,734,324 — difference $440,768 = the PDF's "Exempt Ag/Timber Market" line |
| **2023-2025 entity G01 vs FBCAD certified grand totals PDFs (approved + under review)** | 2023: 409,248 properties, market $160,092,726,644, assessed $135,909,710,038 — all exact. 2024: count and market exact, assessed off by $1.85M (0.001%). 2025: count, market and assessed exact. So the 2023-2025 exports (re-posted Aug 2026) are exactly the certified rolls. |
| 2026 market value vs FBCAD 2026 certified GIS parcel file (CamaSummary Total_Value) | equal for 9,305 of 9,305 commercial properties found in the GIS file |
| Website check 2026-10-12 (Truth-in-Taxation site) | R277329 $2,740,228 ✓ (plus R101338, R103428 earlier) |
| Table audit 2026-10-12 | row counts = summary.json, no duplicate IDs, no blank/negative market values, market = improvement + land + ag/timber market for 100% of rows, flags valid |
| Owner-summed value vs G01 value (commercial) | 9,628 / 9,787 equal; rest split jurisdiction |
| Website (Truth-in-Taxation site) 2026 market value | R101338 $5,243,569 ✓, R103428 $812,000 ✓ |
| M&S segment value vs improvement value | equal for ~42%; others valued by income approach, so cost value differs (expected) |
| Commercial parcel count vs FBCAD 2024 annual report (8,512 F parcels) | 9,156 in 2024 incl. B multifamily — consistent |
| **2026-11-16: commercial totals re-computed from certified exports** | 2025 $25,130,621,026 and 2026 $26,853,769,275 = `analysis_summary.json`, exact |
| **2026-11-16: April preliminary value vs PTP recorded notice value** | 2025: 99.5% of 618 FB clients exact; 2026: all filled rows exact |
| **2026-11-16: Oct 2026 roll vs PTP recorded final value** | 2025: 99.0% of 618 FB clients exact |

Not yet checked: building sq ft against the esearch website (it refuses automated access — check a few by hand). The GIS parcel file has living area for houses only, so it cannot confirm commercial sq ft.

## 6. Things to know
- The 2023-2025 "certified" exports on the website were **re-generated in Aug 2026** (file names start with 2026_08_..).
  They are labeled `CERT` and match the certified grand totals exactly (see §5), i.e. they do **not** include later supplement changes.
  2024 and 2023 commercial segments are post-certification (Aug 2024 / Nov 2023).
- **Values keep changing after certification** (late ARB orders, corrections). Through the October 2026 roll: 2025 commercial −$1.21B on 1,296 accounts; 2026: 58 of the 215 protests open at certification changed (−$59.8M). `commercial_properties.csv` holds certified values only.
- Sale prices: not published (Texas non-disclosure). The deed history gives dates, instrument numbers and previous owners only.
- Income data (rents, NOI, cap rates): not in any public file. FBCAD's Commercial Property Manual describes the method.
- FBCAD publishes the **low-income housing cap rate** each year (2026: 6.75-8.0%, Tax Code 11.1825(r)) on the home page.
- 31 commercial properties exceed the $62.9M special-panel threshold; 1,049 are ≥ $5M (outside binding-arbitration range).
- **Agent of record:** AgentExport lists agent names/addresses only (PTP appears as "Property Tax Protest", 3824 Cedar Springs Rd STE 361, Dallas). No public file links an agent ID (e.g. PTP A0830173) to an account.

## 7. Extra public files (added 2026-10-12, 2026-11-16)
- `03_Reference_Documents/`: certified grand totals 2023-2025, Commercial Property Manual (Oct 2024).
- `02_Source_Data/gis/FBCAD2026CertifiedGISData-ParcelsShapefiles.zip` — 2026 certified parcels with owner, values, situs, year built, state code (CamaSummary layer). Earlier years (2021-2025) are on https://www.fbcad.org/gis-data/.
- `02_Source_Data/2025/`: Orion 2025 preliminary exports 2025-04-01 and 2025-05-06 (notice values).
- `02_Source_Data/2026/`: Orion 2026 preliminary exports 2026-04-21 and 2026-06-15 (notice values); October 2026 Property Data Export (latest values for 2026 and 2025).

## 8. Open items
- Download the Residential Segments file to get areas for B2 small multifamily, if PTP wants those.
- Run `fortbend_extract_propertydata.py` for 2023-2025 (zips are nested one level deeper — script needs a small change).
- Verify building sq ft by hand on esearch.fbcad.org for 3-5 properties.
- ~~2026 supplements (Sup 1-3) exist for post-certification changes; not loaded.~~ Done 2026-11-16 via the October 2026 Property Data Export (covers Sup 1-4).
- Send `public_records_request.md` items 4-5 (agent of record by account; protest/ARB outcomes) — the only way to confirm PTP accounts by agent code and separate protest wins from CAD corrections.
- Hand-check the largest 2026 reductions on the FBCAD site (e.g. R454449 $58.7M → $1.8M).

## 9. Protest reductions 2025-2026 (added 2026-11-16)
Folder `04_Analysis/commercial_reductions/`; script `fort_bend_commercial_reductions.py`.

- reduction = notice value − final value, counted when > 0. Notice = April preliminary export (fallback: next preliminary snapshot holding the account). Final = October 2026 Property Data Export. A version against the certified value is included too (`reduction_vs_cert`).
- Commercial = certified-roll state codes above. Counts 9,353 (2025) and 9,788 (2026), same as `commercial_properties.csv`.
- PTP clients = Fort Bend accounts in PTP's "2026 PTP Reductions" sheet (copies saved alongside).

| Tax year | Group | Properties | Reduced | Total reduction |
|---|---|---:|---:|---:|
| 2025 | PTP clients | 2 | 0 | $0 |
| 2025 | Everyone else | 9,351 | 4,569 | $4,938,252,468 |
| 2026 | PTP clients | 7 | 4 | $284,422 |
| 2026 | Everyone else | 9,781 | 4,952 | $4,098,683,171 |
| 2025+2026 | PTP clients | 9 | 4 | $284,422 |
| 2025+2026 | Everyone else | 19,132 | 9,521 | $9,036,935,639 |

Caveats: FBCAD publishes no protest list, so every notice-to-final decrease is counted. Accounts whose acreage shrank, whose final value is 0 or whose legal description changed are flagged. Excluding them gives 2025 $4.91B and 2026 $4.08B. Against the certified value instead of the latest roll: 2025 $3.75B, 2026 $3.95B. Year-over-year change is not used.
