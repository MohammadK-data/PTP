## Tarrant (Tarrant Appraisal District, TAD)

Script: `Market Analysis/etl/tarrant_market.py` (2024, 2025, 2026). All inputs were already on disk in
`CAD Website/Tarrant/Data/` (downloaded 2026-10-21 to 2026-11-13); nothing new was downloaded.

### Files used

| Year | Source | File | Where it came from / date |
|---|---|---|---|
| 2026 | Roll | `PropertyData(Delimited)_2026.txt` (2,294,819 rows → 2,288,134 accounts after removing duplicate rows per deed; dedupe done by `CAD Website/Tarrant/etl/tarrant_arb_values_2026.py` → `output/tarrant_property_2026_dedup.csv`) | TAD data downloads, https://www.tad.org/resources/data-downloads (file dated 2026-10-26) |
| 2026 | Homestead | `AgentSummaryData_2025/AgentSummaryData_8_Exemption.txt`. **The folder name says 2025, but every row is TaxYear 2026.** | TAD Agent Summary data (agent portal download, 2026-10-27) |
| 2026 | Protests + agents | `ORR20261019 - Avetik Ghazaryan - ARB Info 2026.csv`: every 2026 protest case from an open-records request, dated 2026-10-19. 326,909 rows / 310,995 cases / 307,478 accounts. Filing dates run from 2026-02-03 to 2026-10-20. | TAD open-records response (received 2026-10-21) |
| 2025 | Roll | `PropertyData_2025.txt` (1,996,478 accounts) | TAD data downloads |
| 2025 | Homestead | `PropertyData_Exemptions_2025.txt` | TAD data downloads |
| 2025 | Protests + agents | `ORR20261019 - Avetik Ghazaryan - ARB Info 2025.csv`: 660,456 rows / 660,452 cases / 268,648 accounts. Its ProtestFilingDate values are all in 2026 (2026-01-20 and later), which looks like a migration date, not a real filing date. | same open-records response |
| 2024 | Roll | `PropertyData_2024.txt` (1,930,923 accounts) | TAD data downloads |
| 2024 | Homestead | `PropertyData_Exemptions_2024.txt` | TAD data downloads |
| 2024 | Protests + agents | `AgentSummaryData_2024/AgentSummaryData_9_ReviewBoard.txt`: 340,602 rows / 164,051 accounts, all 2024 cases county-wide | TAD Agent Summary data |

- **Roll version:** all three rolls are the TAD downloads as of 2026-10-26, so each is the latest roll for its year, not the July certified snapshot. TAD's public site does not offer a separate July certified export.
- **Missing source:**
  - TAD publishes no agent-of-record (appointment) list in any of these files, for any year.
  - 2022 and 2023 protest data are not on disk.

### PTP agent IDs
- **2025 and 2026: agentID `1487`.** In the ARB files, every Agent-type case with agentID 1487 has the appellant name "PROPERTY TAX PROTEST". No other ID carries that name. These IDs have similar names but are different firms: 2655 TEXAS TAX PROTEST, 3749390 TX TAX PROTEST, 3935282 TAX PROTEST CONSULTANTS.
- **2024: agency code `00795`.** The 2024 ReviewBoard file uses TAD's older agency codes, not agentIDs. On 861 accounts shared between the two files, code 00795 lines up with agentID 1487. Cases where the appellant is "PROPERTY TAX PROTEST" and the agency is blank (about 196 rows) were also counted as PTP.

### Rules adapted
- **Has agent (biggest caveat).** There is no appointment list, so "has agent" means an agent ID or agent name appears on at least one of the account's valid protest cases that year. The ARB file lists each case once per agent on the account.
  - So `homes_A_with_agent` = `homes_A_protested_by_agent`, and `homes_A_ptp_agent` = `homes_A_ptp_protested`.
  - Accounts where an agent is appointed but filed no protest are not visible. These counts are a lower bound on "agent of record".
  - In firms.csv, `homes_A_agent_of_record` = `homes_A_protests_filed` for the same reason.
- **Valid protest.** Every case except these statuses: Protest Setup in Error, Filed Untimely, Protest Filed Untimely, 25.25(b) Correction, JOINT MOTION 25.25(h) RESOLVED, Reference Only Account, Incomplete Account.
  - The ARB files give no reason for each case ("nature"), so exemption, ag-use and circuit-breaker protests are included.
  - In 2024, about 1% of cases have a nature other than market or unequal value. They were not removed, to keep the years consistent.
- **Agent-filed vs owner-filed (2025/2026).**
  - Agent-filed: an agent ID is on the case, or the AppellantType is "Agent".
  - Owner-filed: AppellantType "Owner", or "Other" with no agent ID.
  - In 2026, 51,909 "Other" cases name the appellant "TARRANT APPRAISAL DISTRICT" (owner online filings). In 2025 the same kind of filing is coded "Owner".
  - A home with both an agent case and an owner case counts as agent-filed.
- **Agent-filed (2024).** The ReviewBoard Agency code is filled, or the Appellant is a known agent name.
- **all_protests / all_agent_protests:** these count unique **accounts** with at least one valid protest (all property types), not cases. Case counts:

  | Year | Valid cases | Accounts |
  |---|---|---|
  | 2024 | 340,080 | 163,867 |
  | 2025 | 660,119 | 268,587 |
  | 2026 | 307,813 | 307,093 |

  2024 and 2025 usually have two cases per account (market + unequal value). In 2026, TAD records one case per account.
- **State code** = roll `State_Use_Code`.
  - Home = starts with A (includes "AC", ~200 accounts coded A on commercial records).
  - Mineral = starts with G.
  - The 2026 roll has 286,368 rows with a blank RP column (283,114 of them are G, mineral). These are new mineral account numbers (73,220,822 and up), none present in 2025. They make 2026 mineral_accounts / total_accounts jump. They were kept as published.
- **Homestead** = exemption row "HOMESTEAD GENERAL 11.13(b)".
- **Segments.**
  - 2026: lapsed = protested in 2024 or 2025 (not 2022–2023, which are missing).
  - 2025: lapsed = protested in 2024 only.
  - 2024: no history, so only `seg_lapsed_or_never` is filled.
  - Because "has agent" can only be seen through protests, `seg_agent` = homes protested with an agent. Lapsed and never are the homes with no 2026 protest.
- **Firm grouping.**
  - Agent name for each agentID = the most common AppellantName on its Agent-type cases (2025 + 2026 ARB files). For 2024, the Appellant name, or the most common name for that agency code.
  - Names are put into firms by brand regex:
    - OWNWELL → Ownwell
    - any "RYAN" → Ryan LLC
    - O'CONNOR / OCONNOR → O'Connor & Associates
    - CHANDLER CROUCH, RESOLUTE, RAY TAX GROUP, SOUTHLAND, TEXAS TAX PROTEST, PEYCO, PROPERTY TAX LOCK, INTEGRATAX, NORTH TEXAS PROPERTY TAX, TEXAS PROTAX, TEXAS PROPERTY TAX REDUCTIONS, POPP HUTCHESON, KROLL, POER, DUCHARME, FIVE STONE → their own firm
    - anything else → its name without LLC/INC/LP.
  - Agent-type cases with no ID and no name (2025: 15,129 homes; 2026: 5,947) are grouped as "Unknown agent" and folded into "All other agents".
  - The full firm → IDs list per year is in `work/tarrant/firm_map.txt`.
  - Ryan LLC IDs (2026): 224;248;670;672;673;675;687;691;697;698;1292;1296;2256;3598587;3598670;3609556;3687527;3957596;4119693.
  - Ownwell 4021420; Chandler Crouch 3662597; Resolute 1792; O'Connor 918; Texas Tax Protest 2655.
  - A home on cases from two firms is counted under each firm.

### Checks
- `homes_A_with_agent` ≤ homes_A and `homes_A_protested` ≤ homes_A in every year. Segments add up to homes_A, checked in the script.
- **PTP 2026 homes vs the portal:**
  - 3,943 homes (all property types: 4,064 accounts; 4,074 counting 10 "Protest Setup in Error" cases) vs the 4,185 in PTP's portal.
  - That is 242 fewer homes (−5.8%), or 121 fewer accounts of all types.
  - Likely causes: cases filed after the 2026-10-19 open-records cut, and portal accounts where PTP is appointed but not listed on the case.
- **PTP by year:** 2024: 618 homes; 2025: 2,169; 2026: 3,943.
