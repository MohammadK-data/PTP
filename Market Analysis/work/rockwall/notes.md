## Rockwall (Rockwall CAD)

Script: `Market Analysis/etl/rockwall_market.py` (uses `market_common_dfw.py`, `firm_names_dfw.py`).

### Sources
All files come from the CAD's data page **https://www.rockwallcad.com/data-exports**. Each link there opens a Google Drive zip of the PACS "Appraisal Export" (layout 8.0.0.30–8.0.0.33). I used only `APPRAISAL_INFO`, `APPRAISAL_ARB`, `APPRAISAL_AGENT` and `APPRAISAL_HEADER`.

| Year | Use | Link text on the data page / Drive file id | File inside | Run date (header) |
|---|---|---|---|---|
| 2026 | roll | 2026 CERTIFIED APPRAISAL ROLL as of July 13, 2026 (`1Ekz8ijj32TIMF_g7JsAOq-Yy8A5jXey6`) | `2026-07-13_2026_APPRAISAL_INFO.TXT` (already in `CAD Website/Rockwall/Data/RCAD CERT 2026 APP ROLL 07_13_2026`) | 2026-07-13 |
| 2026 | agents | 2026 PRELIMINARY APPRAISAL ROLL as of May 26, 2026 (`1juamoCBY39eg861J86SaUoaJJrShrAlV`) | `2026-05-26_2026_APPRAISAL_INFO.TXT`, `_AGENT.TXT` | 2026-05-26 |
| 2026 | protests | Mar 16, May 26, Jul 13 and Oct 7 (file date Oct 9) 2026 exports | `*_2026_APPRAISAL_ARB.TXT` (4 files) | 2026-03-16 … 2026-10-09 |
| 2025 | roll | 2025 CERTIFIED APPRAISAL ROLL as of July 14, 2025 (`1ZDtBCh1RaMtKGxErbc_auyKwI6uqqCQz`) | `2025-07-14_2025_APPRAISAL_INFO.TXT` | 2025-07-14 |
| 2025 | agents | 2025 PRELIMINARY APPRAISAL ROLL as of June 20, 2025 (`1KM8MdLyT-6d8tGFQmgkScDAeBCkWI1fX`) | `2025-06-20_2025_APPRAISAL_INFO.TXT`, `_AGENT.TXT` | 2025-06-20 |
| 2024 | roll + agents | "2024 CERTIFIED APPRAISAL ROLL as of July 11, 2024" (`1Qynq71VAamWp-LwwEkbFiwqTYYVo5nao`) | `2024-08-23_2024_APPRAISAL_INFO.TXT`. **The zip actually holds an Aug 23, 2024 export, not the Jul 11 one.** | 2024-08-23 |
| 2023 | (history check only) | 2023 PRELIMINARY APPRAISAL ROLL as of June 5, 2023 (`1I4fuLKBqxflLOOUVK2NSCt3Ai50FfiD7`) | `2023-06-05_2023_APPRAISAL_ARB.TXT` | 2023-06-05 |

Downloads: `https://drive.usercontent.google.com/download?id=<id>&export=download&confirm=t`. Only the four record files were kept, in `CAD Website/Rockwall/Data/rockwall_prior_download/`; the zips were deleted.
The **2024 PRELIMINARY APPRAISAL ROLL as of April 20, 2024** link (`1ai1uFPmVJHbfcaDlVajprmlqSOTsqQLL`) sends you to a Google sign-in page, so it is not public and I didn't use it.

### Missing sources
- **Protest file (all years):** Rockwall publishes no protest list. The only per-account protest source is the `APPRAISAL_ARB` record in each export, and it lists only the protests on file **at that export's date**. A protest already closed before the export date (for example an early informal settlement) does not show up.
  - **2026:** filled from the union of the four 2026 exports. This is a **lower bound**. Resolute Property Tax Solutions has 748 Rockwall homes as agent of record but only 13 show a 2026 ARB record (in Denton the same firm filed on 91% of its homes), so its settled protests are missing. Compare `all_protests` with the Comptroller survey before using it.
  - **2025:** left blank. The 2025 ARB rows (Jun 20 + Jul 14 + all 2026 exports) cover only 7,393 accounts / 5,504 homes, about half the 2026 level, with 640 owner protests against 1,944 in 2026. It is clearly incomplete. Lower bound for reference: 7,393 accounts, 5,504 homes.
  - **2024:** left blank. The April 20 prelim is not public, and the Aug 23 export lists only the few protests still open then.
- **Prior-year protest history (2022–2025):** incomplete (no 2022 list, no 2024 list, 2025 partial). So `seg_lapsed` and `seg_never` are blank, and the combined count is in `seg_lapsed_or_never`.
- **Agent appointment dates:** the PACS export has none. So "has agent" = the agent ID on the account in the export closest after the deadline (see rules below).

### PTP agent IDs
RCAD's agent list (`APPRAISAL_AGENT`) has two entries named exactly **PROPERTY TAX PROTEST**:
- **1044073** (3824 Cedar Springs Rd PMB 361, Dallas): the active one.
- **1044084**: its address field reads "DO NOT USE - SEE 549409"; 549409 is PTP's Collin ID. Kept in the ID list, but it has no accounts.

Excluded: BALLARD PROPERTY TAX PROTEST (1114733), a different firm.
- **2026:** 40 homes with PTP as agent (May 26), 39 of them with a 2026 ARB record. The known portal count is 49. The CAD data never shows more than 41 PTP accounts in any 2026 export (Mar 0, May 40, Jul 41, Oct 38). So about 8–10 of our accounts are not linked to 1044073 in RCAD's data, either because the appointment was not entered or because the protest was filed under the owner.
- **2025 and 2024:** no accounts on PTP IDs.

### Firm mapping
Rule (`firm_names_dfw.py`): brand keyword first, otherwise the cleaned agent name. Cleaning means uppercase and removing "(Mineral)", "(MO)", " - office", "FKA …" and corporate suffixes. IDs for each firm are listed in `firms.csv` → `agent_ids`.
- **Ryan LLC:** every "RYAN LLC …" and "RYAN TAX COMPLIANCE …" ID (28 IDs in 2026). Individuals named Ryan are not included.
- **Ownwell:** 1112849, 1113504.
- **O'Connor & Associates:** 97643, 1042350.
- **Texas Tax Protest:** 1058309.
- **Resolute Property Tax Solutions:** 97580.
- **Jim Goodrich:** 1044152.
- **Gill Denson:** 1106236.
- **Home Tax Shield:** 1103469.
- **Texas Property Tax Consultants:** 97673 (2024 only ≥100).

### Rules adapted
- **Accounts:** unique `prop_id` in the certified `APPRAISAL_INFO`. It has one row per owner; I kept the latest `sup_num`.
- **State code:** `imprv_state_cd`, else `land_state_cd`, else `personal_state_cd`, else `mineral_state_cd`. Rockwall has no G (mineral) accounts, so `mineral_accounts` = 0.
- **Homestead:** `hs_exempt = T` on any owner row.
- **Has agent:** a non-blank `arb_agent_id` or `ca_agent_id` in the export closest after the May 15 deadline:
  - 2026: May 26 prelim.
  - 2025: Jun 20 prelim.
  - 2024: Aug 23 export (the only one available).

  There are no dates in the export, so the deadline test can't be applied exactly.
- **Protests:**
  - **Protested:** a 2026 `APPRAISAL_ARB` row in any 2026 export. Statuses starting `25.25` are excluded (correction motions, not value protests). PACS keys ARB records by property and year, so `all_protests` counts **accounts with a protest** (one per account-year).
  - **Agent-filed vs owner-filed:** there is no filer field. Agent-filed = the account had an `arb_agent_id` in the May 26 export, or the ARB status starts `O-AGT`. Owner-filed = everything else.
- **Segments:** `seg_agent` = agent of record OR a protest filed by an agent this year. That makes it slightly larger than `homes_A_with_agent` (9,387 vs 9,343).
- **Firm rows:** `homes_A_protests_filed` uses the ARB agent on the account (May 26), not a filer field.

### Checks
- `homes_A_with_agent` ≤ `homes_A`, `homes_A_protested` ≤ `homes_A`, and the segments sum to `homes_A` (asserted in code).
- Rockwall `all_protests` 2026 = 13,509 accounts. No Comptroller survey exists yet for 2026; 2025 is blank here.
