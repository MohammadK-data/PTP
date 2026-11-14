## Hays (Hays CAD)

Script: `Market Analysis/etl/fort_bend_hays_market.py`. The firm ID mapping is in `work/hays/firm_mapping_2026.csv`. It has agent names, so it is a working file and not for delivery.

### Files used
| Year | File | Where it came from | File date |
|---|---|---|---|
| 2026 | `2026_07_18_2127_PropertyExport.txt`, `_OwnerExport.txt`, `_ExemptionExport.txt`, `_AgentExport.txt` (Orion 2026 Certified Export) | https://hayscad.com/wp-content/uploads/2026/07/2026_07_18_2127-Orion-2026-Certified-Export.zip (already on disk: `CAD Website/Hays/Data/2026_07_18_2127-Orion-2026-Certified-Export/`) | exported 2026-07-18, SupplementNumber = CERT |
| 2025 | `2025-CERTIFIED-PROPERTY.zip` (PropertyDataExport1278272.txt), `-OWNER`, `-IMPROVEMENT`, `-LAND` inside `2025-Certified-Data-Export.zip` | https://hayscad.com/wp-content/uploads/2025/07/2025-Certified-Data-Export.zip (downloaded 2026-11-14 to `CAD Website/Hays/Data/hays_2025_certified_download/`) | server date 2025-07-30 |
| 2024 | `2024 Certified Export-PROPERTY.zip` (PropertyDataExport1174522.txt), `-OWNER`, `-IMPROVEMENTS`, `-LAND` inside `2024-Certified-Data-Export.zip` | https://hayscad.com/wp-content/uploads/2024/07/2024-Certified-Data-Export.zip (downloaded 2026-11-14 to `CAD Website/Hays/Data/hays_2024_certified_download/`) | server date 2024-07-26 |

Index page: https://hayscad.com/data-downloads/. The site sits behind a Cloudflare browser check, so the zips were fetched through the browser.

### What is missing
- **Protest data: missing for every year.** Hays CAD publishes no protest file. The data-downloads page has only roll and property exports, and the protest page holds forms only. All protest columns are blank, and so are homes_A_protests_filed and the Owners row.
  - `ARBProtestFlag` in the 2026 Orion export marks protests still open at certification (2,010 accounts). It was not used.
- **Agent of record for 2024/2025: missing.** Hays published those years only in the "PropertyDataExport" CSV format, which has no agent field. 2026 is the only year with an Orion export that has agents.
- **Segments:** only homes_A, seg_agent and seg_ptp are filled, for 2026. The other three groups need protest data, so they are blank, and seg_lapsed_or_never is blank too. For 2026, homes with no agent = 85,944 − 25,529 = 60,415. That number is owner_alone + lapsed + never combined, and it can't be split further.

### PTP agent ID
- **A0180641**, "PROPERTY TAX PROTEST", 3824 Cedar Springs Rd MB 361, Dallas. Confirmed in AgentExport as 0180641. OwnerExport writes IDs with an "A" prefix. No other Hays agent ID carries that name. Ballard ("WATCHTOWER PROTEST DBA BALLARD PROPERTY TAX PROTEST", 0169888) is a different firm.
- 2026 PTP homes as agent of record = **93** (102 accounts of all types). The known 2026 PTP home protest count is 98. The numbers measure different things: agent of record at certification vs. protests filed. They are within 5%.

### Has agent (2026)
- Has agent = `CAAgentID` or `ARBAgentID` is filled on any owner record of the account in the certified OwnerExport. EntityAgentID (agent for taxing units only) is not counted.
- **Rule adapted:** the export has no appointment effective or expiration dates. "Agent of record" therefore means the agent on file at certification (2026-07-18), not at the May 15 deadline. Appointments that started after the deadline are included. Appointments revoked before July 18 are missed.

### Firm mapping (2026)
- An agent ID is turned into a firm by normalizing the AgentExport name (upper case, punctuation stripped) and applying brand patterns:
  - PROPERTY TAX PROTEST (excluding Ballard/Kutner/Watchtower) = Property Tax Protest
  - OWNWELL = Ownwell
  - TEXAS PROTAX / CAPTA INC (% Texas ProTax) = Texas ProTax
  - RYAN = Ryan LLC
  - O'CONNOR = O'Connor & Associates
  - TEXAS TAX PROTEST, TURBOPROTEST, TAXPROTESTMAP, PROTEST TAX LLC, KROLL, POPP, POER = their own firms
  - otherwise, the cleaned name with legal suffixes removed
- IDs per firm with ≥100 homes:

| Firm | IDs |
|---|---|
| Ownwell | A0120363 |
| Home Tax Shield | A0108804 |
| Five Stone Property Tax | A0076668 |
| Texas ProTax | A8646 |
| O'Connor & Associates | A1069 |
| Texas Tax Protest | A0046718 |
| Gill Denson | A0107403 |
| Ryan LLC | A0108459, A0115980, A0115981, A0115984, A0115996, A0116018, A0146021, A0167074, A0168540, A0175515, A1089, A1112, A1117 |
| Resolute Property Tax Solutions | A0087805 |
| TaxProtestMap | A0138556 |
| Lone Oak Property Tax Service | A0010522 |
| Property Tax Protest | A0180641 |

- An account with agents from two firms counts once for each firm. "All other agents" = accounts whose agents all fall outside the listed firms (304 IDs).

### Rules applied / adapted
- Account = unique PropertyQuickRefID (2026) or PropertyID (2024/25). total_accounts includes BPP and mobile homes.
- State code:
  - 2026 (Orion): `StateCodeImp` if filled, else `StateCodeLand`.
  - 2024/25 (PropertyDataExport, which has no state code in the property file): StateCode of the highest-value improvement, else of the highest-value land segment.
  - Check: the 2024/25 rule run on the 2026 Oct-19 PropertyDataExport gives 85,940 cat A accounts, against 85,944 from the 2026 Orion state codes. The two rules agree.
  - About 8.6k accounts per year have no state code in the PropertyDataExport format, mostly BPP with no land or improvement rows. They are counted in total_accounts and in no category.
- Homestead:
  - 2026: ExemptionCode "HS" in ExemptionExport, mapped through OwnerExport.
  - 2024/25: "HS" in the OwnerExport `ExemptionList`.
  - A property counts if any owner has HS.
- mineral_accounts = 0 in every year. Hays has no G-coded accounts in these exports. Only 10 accounts have property type N, and none is coded G.
