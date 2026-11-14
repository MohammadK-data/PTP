## Travis (Travis CAD)

Scripts: `Market Analysis/etl/travis_agents_2026.py` (agent appointments from the JSON), `travis_montgomery_pacs_slim.py`
(certified roll slim), `travis_ears_slim.py` (2024/2025 EARS), `travis_montgomery_market.py` (all counts).

### Files used
| Year | Source | File | Date | Where from |
|---|---|---|---|---|
| 2026 | Roll | `2026 Certified Appraisal Export Supp 0_07182026.zip` → `PROP.TXT` (PACS legacy 8.0.33) | 07/18/2026 (certified, Supp 0) | https://traviscad.org/wp-content/largefiles/2026%20Certified%20Appraisal%20Export%20Supp%200_07182026.zip (already on disk in `CAD Website/Travis/Data/`) |
| 2026 | Agents | `Travis-protaxExport-20261006.json` → `owners[].agents[]` (agentID, companyName, effectiveDt, expirationDt) | 10/06/2026 | TCAD agent-portal JSON export (on disk); the certified `AGENT.TXT` was used only to check the PTP name |
| 2026 | Protests | same JSON → `appeals[]` (2026 appeals; appealType, appealedByType, appealedByAgentID), flattened in `CAD Website/Travis/output/travis_appeals_2026.csv.gz` | 10/06/2026 | same |
| 2025 | Roll only | `227EARS090425.zip` → inner `227EARS090425.zip` → `227EARS090425.csv` (EARS roll submission to the Comptroller, 2025 Supp 3) | 09/04/2025 | https://traviscad.org/wp-content/largefiles/227EARS090425.zip |
| 2024 | Roll only | `227EARS082824 (2).zip` → `227EARS082824.zip` → `227EARS082824.csv` (2024 Supp 1) | 08/28/2024 | https://traviscad.org/wp-content/largefiles/227EARS082824%20%282%29.zip |

Downloads are in `CAD Website/Travis/Data/ears_download/`. The extracted 1 GB CSVs were deleted after the slim
extract (work/travis/ears_<y>.csv.gz); re-extract from the zips to rerun.

### Missing
- TCAD's public information page (https://traviscad.org/publicinformation) only offers 2026 exports (certified, supplements,
  JSON). It has no 2024 or 2025 certified appraisal export, agent list or protest file. The only prior-year bulk files are the
  EARS submissions, which have account, category and homestead flags but no agents or protests.
- 2024, 2025: agent and protest columns are blank, there are no firm rows, and the segment columns are blank (only homes_A is filled).
- 2026: protests before 2026 aren't published (the JSON only holds 2026 appeals), so seg_lapsed and seg_never are blank.
  The combined count goes in seg_lapsed_or_never.

### PTP agent IDs
- **1863738** "PROPERTY TAX PROTEST", 3824 Cedar Springs Rd MB 361 (in AGENT.TXT and the JSON; 2,957 property appointments). Used.
- 1328537 "PROPERTY TAX PROTEST" (AGENT.TXT, no address). Included in the ID set, but it has no appointments and no 2026 filings.
- Not counted: 1898343 "CAMEL TEXAS PROPERTY TAX PROTEST" (39 appointments) and 1898284 "Q-SOLUTIONS PROPERTY TAX PROTEST" (2).
  Their names are different firms. Note that `CAD Website/Travis/etl/travis_values_2026_build.py` counts them as ours.
  If the team confirms they are PTP, add them; they change the counts by fewer than 45 accounts.
- Not counted: 1611620 "PROPERTY TAX PROTEST PROFESSIONALS" and 1897915 "BALLARD PROPERTY TAX PROTEST AKA WATCHTOWER PROTEST".

### PTP 2026 check against our portal (2,890)
- homes_A_ptp_protested = **1,130**: home protests the CAD records as filed by agent 1863738. All property types: 1,199.
- homes_A_ptp_agent = 2,162 (2,036 by the appointment-date rule alone).
- The JSON lists PTP on 2,957 properties at some point (2,556 of them homes). That is close to the portal's 2,890.
  Of those 2,556 homes, 2,410 were protested in 2026, but only 1,104 by PTP's ID. 792 were filed by another agent
  (mostly Ownwell, 1887270) and 513 by the owner. About 350 PTP appointments carry a 2026 expiration date, which suggests
  clients moved to another firm. **Big difference: the CAD records PTP as filer on about 39% of the portal count.** Check whether
  PTP sometimes files as the owner (appealedByType O) on its clients' accounts.

### Rules adapted
- Universe: unique prop_id in the 07/18 certified PROP.TXT (493,324 rows, 493,246 unique). Agents and protests are joined to it
  by prop_id. 13 protest cases sit on accounts not in the certified roll; they are counted in all_protests but not in the home columns.
- Category: an account is A if any of imprv/land/personal/mineral_state_cd starts with A, else B, else M. Mineral = any
  code starting with G (Travis has 5). EARS years: the same rule over every AJR031 category the account has.
- Homestead: 2026 hs_exempt = T. 2024/2025 EARS AJR039 = Y ("an exemption restricted to homesteads"). That flag is slightly
  broader than HS alone, so the years are close but not identical.
- Has agent (2026): an appointment effective on or before the deadline (later of May 15 and noticeDt + 30 days) and not expired
  before it, **or** a 2026 protest filed by an agent. The rule alone gives 149,622 homes; 7,523 more homes had an agent-filed
  protest with an appointment dated after the deadline. homes_A_with_agent, seg_agent, homes_A_ptp_agent, seg_ptp and the firm
  rows all use this combined flag.
- Protest = 2026 appeal of type P. Left out: PY (32+29+9) and T (21), which are not value protests. Filer: appealedByType A = agent,
  O = owner, OTH = other (141 home accounts filed only by OTH are in homes_A_protested but in neither split).
  An account with both an agent and an owner filing counts as agent-filed.
- all_protests = 226,989 protest cases (226,664 accounts); all_agent_protests = 198,273 cases.
- Firm grouping: by agent name (`firm_of()` in travis_montgomery_market.py). The text after " - ", AKA, DBA, FKA and C/O is cut,
  legal suffixes are dropped, and these brand rules apply: OWNWELL → Ownwell (1887270, 1898217); TEXAS PROTAX → Texas ProTax
  (14 IDs, one per staff agent); names starting RYAN → Ryan LLC (about 140 office IDs, including "RYAN LLC FKA ALTUS…" and
  "RYAN TAX COMPLIANCE…"); O'CONNOR & ASSOC → O'Connor & Associates (2556; O'Connor-Braman is kept separate); FIVE STONE →
  Five Stone Property Tax (1564573). The full name→ID list is in work/travis/firm_mapping.txt.
  homes_A_agent_of_record counts each home once per firm (a home with two firms counts in both). "All other agents" = unique
  homes with an agent from a firm under 100 homes. homes_A_protests_filed = homes where that firm's ID filed a 2026 protest.

### Checks
- homes_A_with_agent 157,145 ≤ homes_A 353,498; homes_A_protested 175,680 ≤ homes_A.
- Segments: 157,145 + 20,889 + 175,464 = 353,498 ✓.
