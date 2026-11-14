## Fort Bend (FBCAD)

Script: `Market Analysis/etl/fort_bend_hays_market.py`

### Files used
| Year | File | Where it came from | File date |
|---|---|---|---|
| 2026 | `2026_07_07_1746_PropertyExport.txt`, `_OwnerExport.txt`, `_ExemptionExport.txt`, `_AgentExport.txt` (Orion 2026 Certified Export, Redacted) | https://www.fbcad.org/wp-content/uploads/2026/08/2026_07_07_1746-Orion-2026-Certified-Export-Redacted.zip (already on disk: `CAD Website/For Bend/Data/2026_07_07_1746 Orion 2026 Certified Export-Redacted/`) | exported 2026-07-07, SupplementNumber = CERT |
| 2025 | `2026_08_17_1646_PropertyExport.txt` etc. (Orion 2025 Certified Export, Redacted) | https://www.fbcad.org/wp-content/uploads/2026/08/2026_08_17_1646-Orion-2025-Certified-Export-Redacted-1.zip (downloaded 2026-11-14 to `CAD Website/For Bend/Data/fbcad_2025_certified_download/`) | exported 2026-08-17 (a later export of the 2025 certified roll, SupplementNumber = CERT); uploaded 2026-08-21 |
| 2024 | `2026_08_19_1831_PropertyExport.txt` etc. (Orion 2024 Certified Export) | https://www.fbcad.org/wp-content/uploads/2026/08/2026_08_19_1831-Orion-2024-Certified-Export.zip (downloaded 2026-11-14 to `CAD Website/For Bend/Data/fbcad_2024_certified_download/`) | exported 2026-08-19, SupplementNumber = CERT |

Index page: https://www.fbcad.org/certified-and-supplements-reports/

### What is missing
- **Agent of record: missing for every year.** FBCAD's public Orion exports carry no agent ID column. OwnerExport has no CAAgentID/ARBAgentID, and AgentExport lists only names and addresses, with no ID and no link to accounts. This holds for the redacted 2025/2026 exports and also for the 2024 export, which is not labelled redacted. homes_A_with_agent, homes_A_ptp_agent, seg_agent, seg_ptp and the firm table are left blank. The firm table has placeholder rows only.
- **Protest data: missing for every year.** FBCAD publishes no protest file per account or per case. The pages checked were the certified/supplement reports page, 2024values/2025values/2026values, appeals and reports. All protest columns are blank, so segments are blank too, apart from homes_A.
  - The Orion PropertyExport has an `ARBProtestFlag`. It marks protests **still open at certification**, not protests filed that year, so it was **not** used. For reference, flag = 1 on 32,570 accounts in 2026 (1,247 homes), 17,975 in 2025 (938 homes) and 16,141 in 2024 (1,930 homes). These are far below FBCAD's yearly protest volume.
- Prior-year protest history (2022–2025): none, so seg_lapsed, seg_never and seg_lapsed_or_never are blank. seg_lapsed_or_never is blank too, because seg_owner_alone is also unknown.

### PTP agent ID
- The prompt gives A0830173. The ID is **not present** in any public file, because they carry no IDs. AgentExport (2026) has two entries named "Property Tax Protest", at 3824 Cedra/Cedar Springs Rd STE 361, Dallas. Matching on the name works, but it can't be linked to accounts. PTP home protests 2026 can't be checked against the known 930.

### Firm mapping
- Not possible without account-level agent links. See the Hays notes for the name-grouping rule used where links exist.

### Rules applied / adapted
- Account = unique PropertyQuickRefID in PropertyExport (one row each, no duplicates). total_accounts includes BPP (P), minerals (N) and mobile homes.
- State code = `StateCodeImp` if filled, else `StateCodeLand`. Home = starts with "A", B and M are separate, mineral = starts with "G". G accounts match PropertyTypeCode N (14,977 G vs 14,979 N in 2026).
- Homestead = ExemptionCode "HS" in ExemptionExport, keyed by OwnerQuickRefID and mapped to the property through OwnerExport. A property counts if any owner record has HS.
- 2024 and 2025 come from later re-exports of the certified roll (dated Aug 2026). FBCAD no longer lists the original July files for those years. The SupplementNumber column still reads CERT.

### Sanity checks
- Cat A share ≈ 66% of accounts in each year. HS share of homes ≈ 73–75%. Year-over-year growth ≈ 2.5–3%.
