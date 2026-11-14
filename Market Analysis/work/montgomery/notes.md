## Montgomery (Montgomery CAD)

Scripts: `Market Analysis/etl/travis_montgomery_pacs_slim.py` (certified roll slim) and `travis_montgomery_market.py` (all counts).

### Files used
| Year | Source | File | Date | Where from |
|---|---|---|---|---|
| 2026 | Roll | `Certified Appraisal Roll 2026` → `2026-08-04_2026_APPRAISAL_INFO.TXT` (PACS legacy 8.0.33; header 08/03/2026) | 08/03/2026 (certified) | https://www.mcad-tx.org/appraisal-data-exports → "Certified Appraisal Roll 2026" (Google Drive file 1pQvjZX9rnM-vUOwhGuLfiWpZ3S9Ms2mr). Already on disk |
| 2026 | Agents | `Montgomery-protaxExport-20260804.json` → `owners[].agents[]` with effective/expiration dates (flattened: `CAD Website/Montgomery/output/protax_csv/20260804_owner_agents.csv.gz`) | 08/04/2026 | MCAD agent-portal JSON export (on disk) |
| 2026 | Protests | same JSON → `appeals[]` (all 2026), flattened in `CAD Website/Montgomery/output/montgomery_appeals_2026.csv.gz` | 08/04/2026 | same |
| 2025 | Roll + agent of record | `MCAD_Certified_2025_071626.zip` → `2026-07-16_2025_APPRAISAL_INFO.TXT` | 07/16/2026 export of the **2025** roll (header sup 19, so it includes supplements through July 2026) | https://www.mcad-tx.org/appraisal-data-exports → "Certified Appraisal Roll 2025" → https://drive.google.com/file/d/1enYuMq1MzGopV5ycIEIEyUUjEH_efqhd |
| 2024 | Roll + agent of record | `Full Appraisal Export - 2024.zip` → `2024-07-02_2024_APPRAISAL_INFO.TXT` (layout 8.0.30) | 07/02/2024 (certified) | https://www.mcad-tx.org/appraisal-data-exports → "Certified Appraisal Roll 2024" → https://drive.google.com/file/d/1UkrxgueKDhC4kO6-Uy16vAOB4tcAevx3 |

Downloads are in `CAD Website/Montgomery/Data/cert_2024_2025_download/`. The zips are kept (657 MB); INFO was streamed
straight from the zip into work/montgomery/info_<y>_cert.csv.gz.

### Missing
- 2024, 2025 protests: no published protest file. The certified exports include `APPRAISAL_ARB.TXT`, but it only lists
  cases still open when the roll was exported (2026: 20,803 rows against 121,278 protests in the JSON), so it can't be
  used as a protest count. The protest columns, homes_A_protests_filed and the Owners row are blank for 2024/2025.
- 2024, 2025 agents: only `ca_agent_id` (agent of record when the roll was exported). No appointment dates, so the deadline
  test can't be applied. homes_A_with_agent and firm rows for those years are agent-of-record at certification.
- 2026: protests before 2026 aren't published (the JSON only holds 2026 appeals), so seg_lapsed and seg_never are blank and
  seg_lapsed_or_never is filled. 2024/2025 segment rows only have homes_A and seg_ptp.

### PTP agent IDs
- **654513** "PROPERTY TAX PROTEST" (AGENT.TXT 2024, 2025 and 2026; 772 appointments in the JSON). Used.
- **412** "\*\*\*PROPERTY TAX PROTEST\*\*\*", Ste #101-502, 3818 Cedar Springs Rd. Included in the ID set (Cedar Springs
  address). It is agent of record on a few accounts in the 2024 roll, and on none in 2025 or 2026.
- Not counted: 393159 "A1 PROPERTY TAX PROTEST" and 498496 "PROPERTY TAX PROTEST PROFESSIONALS" (other firms).

### PTP 2026 check against our portal (783)
- homes_A_ptp_protested = **588**: home protests the CAD records as filed by 654513. All property types: 617.
- homes_A_ptp_agent = 657 (593 by the appointment-date rule alone).
- The JSON lists PTP on 769 properties at some point (732 of them homes). That is close to 783. Of those 732 homes,
  683 were protested in 2026: 567 by PTP, 112 by another agent, 4 by the owner. Part of the gap (588 vs 783) is clients
  whose protest another agent filed. The JSON is from 08/04, so appointments added later are not in it.

### Rules adapted
- Universe: unique prop_id in the certified INFO file. MCAD repeats a prop_id once per geo_id (2026: 405,533 rows,
  400,131 unique), and the first row is kept.
- Category: an account is A if any of imprv/land/personal/mineral_state_cd starts with A, else B, else M. Mineral = any
  code starting with G (MCAD mineral accounts are prop type MN with G1 codes). Montgomery codes many mobile homes (prop type MH) as
  A2, which are counted as A (the rule follows the state code, not the prop type).
- Homestead = hs_exempt T.
- Has agent (2026): an appointment effective on or before the deadline (later of May 15 and noticeDt + 30 days; 147k accounts
  have no noticeDt and use May 15) and not expired before it, **or** a 2026 protest filed by an agent. The rule alone gives
  72,863 homes; 2,400 more homes had an agent-filed protest with no appointment active at the deadline.
- Protest = appealType PROT, PROTPH or P. Left out: 25.25C (2), 25.25D (54) and 26.09D1 (12), which are correction motions,
  not value protests. Filer A = agent, O = owner, OTH = other (41 homes filed only by OTH are in neither split). An account
  with both an agent and an owner filing counts as agent-filed.
- all_protests = 121,278 protest cases (120,897 accounts); all_agent_protests = 107,782 cases.
- Firm grouping: by agent name, using the 2026 JSON name for each ID in every year so an ID keeps one firm. The text after
  " - ", AKA, DBA, FKA, FKN and C/O is cut, legal suffixes are dropped, and these brand rules apply: OWNWELL → Ownwell (627223);
  O'CONNOR & ASSOC → O'Connor & Associates (113); names starting RYAN → Ryan LLC (about 65 IDs); QUATRO → Quatro Tax (13, 514700,
  361114 "QUATRO FKN DLC ENTERPRISES", 700772); TEXAS PROTAX → Texas ProTax (132). The full list is in
  work/montgomery/firm_mapping.txt. Counting is the same as Travis.

### Checks
- 2026: homes_A_with_agent 75,263 ≤ homes_A 250,354; homes_A_protested 82,916 ≤ homes_A.
- Segments: 75,263 + 10,878 + 164,213 = 250,354 ✓.
- Roll growth 2024 → 2026: 370,926 → 387,780 → 400,131 accounts. Homes: 225,536 → 240,294 → 250,354.
