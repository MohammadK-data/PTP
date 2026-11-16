# Fort Bend commercial protest reductions (2025, 2026)

Built 2026-11-16 by `fort_bend_commercial_reductions.py` (repo: `Market Analysis/etl/`). The method and caveats are in the script's docstring and in `01_Documentation/research_report.md` §9.

- `fortbend_commercial_reductions_summary.csv`: counts and dollars per year and in total, split into PTP clients / everyone else / all.
- `fortbend_commercial_reductions_detail.csv`: one row per commercial property per year, with notice, certified and final values, reduction, and flags (fields in `data_dictionary.md`).
- `ptp_clients_fortbend_<year>.csv`: Fort Bend rows of the "2026 PTP Reductions" Google Sheet (tabs 2026, 2025) as of 2026-11-16. These are the accounts counted as PTP clients.

Source files (all public, https://www.fbcad.org/certified-and-supplements-reports/), as stored in `Fort_Bend/02_Source_Data/`:

| Role | 2025 | 2026 |
|---|---|---|
| Notice value | `2025/2025_04_01_1551-Orion-2025-Preliminary-Export-Updated.zip` | `2026/2026_04_21_0828-Orion-2026-Preliminary-Export-Redacted.zip` |
| Notice value, fallback | `2025/2025_05_06_0636-Orion-2025-Preliminary-Export-Redacted.zip` | `2026/2026_06_15_1742-Orion-2026-Preliminary-Export-Redacted-2.zip` |
| Commercial list, certified value | `2025/2026_08_17_1646-Orion-2025-Certified-Export-Redacted-1.zip` | `2026/2026_07_07_1746-Orion-2026-Certified-Export-Redacted.zip` |
| Final value | `2026/October2026-PropertyDataExport.zip` (MarketValue = 2025) | `2026/October2026-PropertyDataExport.zip` (CurrMarketValue) |
