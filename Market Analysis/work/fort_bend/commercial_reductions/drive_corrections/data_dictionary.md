# Data dictionary - Fort Bend commercial property dataset

Applies to `04_Analysis/commercial_properties.csv`, `04_Analysis/<year>/commercial_properties_<year>.csv`, `commercial_sales.csv` and `commercial_sales_unverified.csv`. **Same 67 columns, in the same order, as every county in the package** (team standard = Montgomery / Tarrant / Williamson schema; full definitions in `../../Wiliamson/01_Documentation/data_dictionary.md`). This file lists the Fort Bend sources and rules. Blank = not available in the source. Money in whole US dollars, areas in square feet unless the name says acres, dates `YYYY-MM-DD`.

**Source.** FBCAD Orion (True Prodigy / Tyler) certified exports per year (PropertyExport, OwnerExport, EntityExport - values per owner summed per property; county unit G01 for assessed/taxable), FBCAD commercial segments files, Property Data Export (deed history). Coordinates: FBCAD 2026 certified GIS (CamaSummary, key CAD_Reference_Number).

**Scope.** state codes F1 (incl. local F1H/F1M/F1X/F1V), F2, B1-B3 on the improvement or land.

## commercial_properties*.csv

| field | Fort Bend source | meaning / rule | limitations |
|---|---|---|---|
| property_id / parcel_id | QuickRef account (R######) / geo number | | |
| property_address / city / postal_code | situs | | |
| latitude / longitude | 2026 certified GIS CamaSummary | point inside parcel | 2026 layer used for all years |
| property_type / property_use_code | improvement state code, else land state code | | |
| land_area_acres / land_area_sqft | legal acres, land sq ft | | |
| building_area_sqft / year_built / effective_year_built / building_quality / construction_style | FBCAD commercial segments: sum of building segment areas; primary segment year, effective year, quality, occupancy | = FBCAD website building sq ft | no second public source to check area |
| land_value | land + ag market + timber market | land + improvement = market value | |
| total_appraised_value / value_at_certification | Orion market value; entity G01 market | **certified** value | not the notice value and not the post-certification final value — see `commercial_reductions` below |
| assessed_value / taxable_value / exemption_amount | entity G01 (Fort Bend County) assessed and taxable; difference | county unit | taxable differs by taxing unit |
| appraised_value_after_special | market - ag/timber market + ag use | | |
| taxing_units | entity codes | | |
| deed_date / deed_book / deed_page | Property Data Export deed history (latest deed up to the year's end) | | deed history file is the 2026 one |
| county / state / appraisal_date / tax_year | constant / Jan 1 of tax year | | |
| property_type | derived from the Comptroller category of the primary code | `commercial_real`, `industrial_real`, `multifamily`, `vacant_commercial_land`, `other_with_commercial_line` | multifamily included because CRE practice treats apartments as commercial - filter with this column |
| prior_year_tax_year / prior_year_total_appraised_value / yoy_appraised_change_pct | derived: nearest earlier tax year in this table for the same property_id | | gap years noted in data_quality_notes. **YoY change is not a protest reduction.** |
| source_dataset / source_url / source_record_id / source_publication_date / collection_date / verification_status | provenance | `official_appraisal_record` = values copied from the CAD file, no edits | |
| data_quality_notes | derived flags | e.g. no building area, total exemption, ag value in land, protest, value not published | "protest" = still open at certification only |
| columns not listed | - | not published by this CAD | blank |

## commercial_sales.csv and commercial_sales_unverified.csv

FBCAD publishes no sale prices. `commercial_sales_unverified.csv` = every deed in the 2026 Property Data Export deed history for the commercial accounts (instrument number, deed type, previous owner).

`commercial_sales.csv` holds only transfers with a price the CAD marks as verified; everything else is in `commercial_sales_unverified.csv` with the reason in `transaction_verification_status` (`ownership_transfer_no_disclosed_price`, `price_reported_but_not_validated_by_cad`). Texas is a non-disclosure state: deeds do not show a price.

## commercial_reductions/fortbend_commercial_reductions_detail.csv (added 2026-11-16)

One row per commercial property per tax year (2025, 2026).

| field | source | meaning / rule |
|---|---|---|
| property_id | QuickRefID | |
| tax_year | | 2025 or 2026 |
| StateCodeLand / StateCodeImp | certified Orion PropertyExport | commercial selection (F1, F1H, F1M, F1X, F1V, F2, B1-B3) |
| ARBProtestFlag | certified Orion PropertyExport | 1 = protest still open at certification |
| Acres | certified Orion PropertyExport | |
| cert_value | certified Orion OwnerExport | market value at certification |
| notice_value | Orion preliminary export (2025-04-01 / 2026-04-21; fallback 2025-05-06 / 2026-06-15) | value on the notice, before protest |
| notice_src | | which snapshot gave notice_value |
| final_value | October 2026 Property Data Export (`CurrMarketValue` for 2026, `MarketValue` for 2025) | latest value incl. post-certification ARB results; falls back to cert_value |
| reduced / reduction | derived | reduced = notice_value > final_value; reduction = notice_value − final_value (else 0) |
| reduction_vs_cert | derived | max(notice_value − cert_value, 0) |
| geom_change | derived | acreage shrank > 5% from notice to certification, or final value = 0 (likely split/merge/deletion) |
| legal_changed | derived | legal description differs between notice and certification |
| flagged | derived | geom_change, or legal_changed on a reduced account; excluded in the `_excl_flagged` totals |
| ptp_client | PTP "2026 PTP Reductions" sheet | account listed for Fort Bend in that year's tab |

`fortbend_commercial_reductions_summary.csv`: per tax year (2025, 2026, 2025+2026) and group (PTP clients, Everyone else, All): commercial_properties, with_notice_value, properties_reduced, total_reduction, the same two excluding flagged rows, and the same two against certified value.
