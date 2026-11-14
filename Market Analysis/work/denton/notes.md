## Denton (Denton CAD)

Scripts: `Market Analysis/etl/denton_market.py`. Helpers:
- `denton_agent_dates.py`: one pass over the 2026 JSON for agent appointment dates.
- `denton_json_stream.py`: streams the 2025 JSON zip.
- `pacs_info_slim.py`, `par_download.py`, `market_common_dfw.py`, `firm_names_dfw.py`.

### Sources
Data page: **https://www.dentoncad.com/data-downloads**. Files are served from `https://dentoncad.net/data/_uploaded/files/datafiles/<year>/…`. That server allows about 25 KB/s per connection, so I downloaded with 16–32 parallel range requests.

| Year | Use | URL / file | File date |
|---|---|---|---|
| 2026 | roll | 2026 Certified Data – All Property → `2026-07-27_2026_APPRAISAL_INFO.TXT` (already in `CAD Website/Denton/Data/2026 CERTIFIED DATA - ALL PROPERTIES`) | 2026-07-27 |
| 2026 | agents + protests | 2026 certified protax JSON `Denton-protaxExport-20260727.json` (already local). Agents = `owners[].agents` with application/effective/expiration dates; protests = `appeals[]` with `pYear` 2026 | 2026-07-27 |
| 2025 | roll | `…/2025/CertifiedDataAllProperty/Denton_AppraisalDataExtracts_ALL(CERTIFIED).zip` → `APPRAISAL_INFO` | 2025-07-28 (zip) |
| 2025 | agents + protests | `…/2025/CertifiedDataJSON/Denton_AppraisalDataExtract_JSON_ALL(CERTIFIED).zip`, streamed without unzipping | 2025-07-28 (zip) |
| 2024 | roll + agents | `…/2024/CertifiedDataAllProperty/CertifiedDataAll.zip` → `2024-07-22_008084_APPRAISAL_INFO.TXT`, `_APPRAISAL_AGENT.TXT` | 2024-07-22 |
| 2024 | protests | `…/2024/CertifiedDataProTax/ProTax_ARBExport.txt` (pipe-delimited, header row) | 2024-07-22 |
| 2023 | history only | `…/2023/CertifiedDataProTax/ProTax_ARBExport.txt` (tab, header row) | 2023-07-24 |
| 2022 | history only | `…/2022/CertifiedDataProTax/ProTax_ARBExport.txt` (tab, no header) | 2022-09-09 |

Raw downloads are in `CAD Website/Denton/Data/denton_prior_download/`. The roll zips were deleted after slimming; slim files are in `Market Analysis/work/denton/`.

### Missing or partial sources
- **2026:** nothing missing. A JSON export that pre-dates the protest deadline (for example April) is not published, but the 2026-07-27 JSON carries dated appointments, so the deadline test can be applied.
- **2024 agents:** no dated agent file. "Has agent" = `arb_agent_id` or `ca_agent_id` in the certified `APPRAISAL_INFO`, i.e. the agent on file at certification (Jul 22), not tested against the deadline.
- **2022 protest list is partial:** only 32,059 protests (2023: 130,983; 2024: 121,845). Used only as protest history. Because history covers 2022 only partly, `seg_lapsed` is a slight undercount, mostly for 2024, whose history window is 2022–2023.

### PTP agent IDs
DCAD's agent list (`APPRAISAL_AGENT`) has two entries named exactly **PROPERTY TAX PROTEST**:
- **245** (3824 Cedar Springs Rd MB 361, Dallas): carries all of PTP's accounts.
- **718105** (Ste 361): no accounts.

Excluded as different firms: BALLARD PROPERTY TAX PROTEST (1774250), SMART VALUE PROPERTY TAX PROTEST LLC (1873387), CAMEL TEXAS PROPERTY TAX PROTEST (1873404).

### Firm mapping
`firm_names_dfw.py`: brand keyword first, otherwise the cleaned agent name. Cleaning means uppercase and removing "(Mineral)", "(MO)", " - office", "FKA …", corporate suffixes, and the " (ID)" / "-ID" that DCAD's 2024 agent list appends to names. Full ID lists per firm are in `firms.csv` → `agent_ids`.
- **Ryan LLC:** all "RYAN LLC …" and "RYAN TAX COMPLIANCE SERVICES …" IDs (about 40), plus the 2024 entry named just "RYAN" (921949). Not included: RYAN DAVENPORT, RYAN LAW. "RYAN LLC FKA MERITAX/POPP HUTCHESON/ALTUS/PARADIGM…" are counted under Ryan. The separate 2024 entry "MERITAX ADVISORS" stays its own firm, as named that year.
- **Ownwell:** 1745071.
- **O'Connor & Associates:** 175.
- **Resolute Property Tax Solutions:** 788754.
- **Texas Tax Protest:** 792777.
- **The Ray Tax Group:** 792902.
- **North Texas Property Tax Services:** 286.
- **Goodrich Realty Consulting (Jim Goodrich):** 615976 (named "GOODRICH & ASSOCIATES" in 2024).
- **K.E. Andrews**, **Merit Advisors**, **Kroll**: grouped by brand.

### Rules adapted
- **Accounts:** unique `prop_id` in the certified `APPRAISAL_INFO` (one row per owner; latest `sup_num`).
- **State code:** `imprv_state_cd`, else `land_state_cd`, else `personal_state_cd`, else `mineral_state_cd`. It matches the JSON `propertyProfile.stateCd` on 99.99% of accounts (12 of 481,983 differ in the A/non-A split).
- **Mineral:** state code G (DCAD propType MN).
- **Homestead:** `hs_exempt = T` on any owner row. JSON `exemptions` containing HS agrees (224,804 vs 224,801 accounts).
- **Has agent (2026, 2025):** an appointment whose start date is on or before that account's deadline, and whose expiration date is after it.
  - Start date = `effectiveDt`, else `applicationDt`. About 6% have no start date and are treated as active.
  - Deadline = May 15, or the JSON `noticeDt` + 30 days if later.
  - This strict rule leaves out agents appointed after the deadline. Example: 484 of PTP's 3,404 Denton appointments start in June 2026.
- **Protests (2026, 2025 JSON):**
  - Every `appeals[]` of the tax year except status CLERICAL (DCAD value corrections). Appeal types are OLA (owner/agent value protest) and PPR (property protest; also used on MN/BPP).
  - `appealedByType` A = agent, O = owner. OTH (216 in 2026) is counted in `all_protests` but not as agent- or owner-filed.
  - `all_protests` counts **appeals (cases)**, not accounts.
- **Protests (2024 and history):** `ProTax_ARBExport` rows of the tax year. Dropped: protest type 25.25 (correction motions) and status DUPE/0DUPE. `prot_by_type` AG = agent, OW = owner. The agent comes from `agent_name` ("NAME (ID)" or "NAME-ID"); 2022/2023 rows often hold just the name. `all_protests` = rows (cases).
- **Agent-filed vs owner-filed:** a home with both an agent and an owner protest counts as agent-filed.
- **Segments:**
  - `seg_agent` = agent of record OR a protest filed by an agent this year. It is therefore larger than `homes_A_with_agent`, because agents appointed after the deadline still file.
  - `seg_lapsed` = protested in any year 2022..year-1 (ARB exports 2022–2024, JSON 2025), not this year, no agent now.
- **Firm rows:**
  - `homes_A_agent_of_record`: an account counts once under each firm that is active on it.
  - `homes_A_protests_filed`: homes where an ID of that firm filed.
  - `All other agents`: accounts whose active agents are all outside the listed firms.
- **ID 43:** named "TOMMY MARSHALL & ASSOCIATES" in 2024–2025 and "C & N CONSULTING SERVICES, LLC" in 2026. Grouped by the name used in each year, so it appears under different firm names.
- **2025 JSON:** pretty-printed (indent 1, 19.5 GB inside the zip). Streamed record by record; 461,801 records, 141,842 appeals (all `pYear` 2025). Status REJECTED (10) is kept as a filed protest.

### Results and checks
| | 2026 | 2025 | 2024 |
|---|---|---|---|
| total_accounts | 481,983 | 461,801 | 456,998 |
| homes_A | 299,348 | 290,056 | 283,731 |
| homes_A_with_agent | 97,710 | 72,682 | 53,678 (cert snapshot, no dates) |
| homes_A_protested | 120,784 | 102,732 | 82,101 |
| all_protests (cases) | 163,501 | 141,842 | 121,845 |
| PTP homes protested | 2,585 | 1,956 | 1,564 |

- **Checks:** `homes_A_with_agent` ≤ `homes_A` and `homes_A_protested` ≤ `homes_A` in every year; the segments sum to `homes_A` (asserted in code).
- **PTP 2026 home protests: 2,585 vs the known portal count of 3,100 (−17%).**
  - In the CAD's 2026-07-27 JSON, ID 245 filed on 2,687 accounts of all types (2,585 category A, plus E1, B2, C1 and one MH).
  - 3,404 accounts list 245 as agent at all, including expired appointments; 2,514 homes have it active at the deadline.
  - Likely reasons for the gap: protests filed under the owner's name, accounts where DCAD has no appointment on file, and filings after Jul 27 (the export date).
- **Comptroller check:** the comparison with the 2024/2025 operations survey is done by main. Here `all_protests` counts cases (appeals) for all property types, CLERICAL / 25.25 / duplicates excluded.
