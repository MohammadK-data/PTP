## Dallas (Dallas Central Appraisal District, DCAD)

Script: `Market Analysis/etl/dallas_market.py` (2024, 2025, 2026).
Download page: https://www.dallascad.org/DataProducts.aspx. Each file's link is
`https://www.dallascad.org/ViewPDFs.aspx?type=3&id=\\DCAD.ORG\WEB\WEBDATA\WEBFORMS\DATA PRODUCTS\<file name>`.

### Files used

| Year | Source | File (zip on the DCAD page) | File date | Local copy |
|---|---|---|---|---|
| 2026 | Roll + tax rep + HS | `DCAD2026_CURRENT.ZIP`: ACCOUNT_APPRL_YEAR.CSV, APPLIED_STD_EXEMPT.CSV | downloaded 2026-10-30 | `CAD Website/Dallas/Data/DCAD2026_CURRENT/` |
| 2026 | (gap filler) | `DCAD2026_CERTIFIED_07232026.zip` | certified 2026-07-23 | `.../DCAD2026_CERTIFIED_07232026/` |
| 2026 | (gap filler) | `DCAD2027_CURRENT.ZIP` | downloaded 2026-10-30 | `.../DCAD2027_CURRENT/` |
| 2025 | Roll + tax rep + HS | `DCAD2025_CURRENT.ZIP` | tables dated 2026-11-09; downloaded 2026-11-14 | `.../dcad_download_20261114/DCAD2025_CURRENT/` (2 tables kept, zip deleted) |
| 2024 | Roll + tax rep + HS | `DCAD2024_CURRENT.ZIP` | tables dated 2026-11-09; downloaded 2026-11-14 | `.../dcad_download_20261114/DCAD2024_CURRENT/` |
| 2022–2026 | Protests | `ARB_ARCHIVE.zip` → ARB_ARCHIVE.CSV (2022–2026 protests, dated 2026-07-20) | downloaded 2026-11-14 | `.../dcad_download_20261114/ARB_ARCHIVE/` |
| 2026 | Protests | `ARB_CURRENT.zip` → ARB_CURRENT.csv (2026-11-09: mostly 2026 protests still open after July) | downloaded 2026-11-14 | `.../dcad_download_20261114/ARB_CURRENT/` |

- **Field descriptions:** `ARB Data Descriptions 08-16-16.xlsx` inside both ARB zips.
- **Disk use:** about 1.7 GB new. The zips were deleted after the needed tables were extracted.
- **Missing sources:** none. Roll, agent (tax rep) and protest files exist for all three years, plus protest history for 2022–2023.

### PTP agent ID
- Tax rep **`306`**. The roll lists it as "306 PROPERTY TAX PROTEST", the same as the ID in the brief.

### Rules adapted
- **Roll = "CURRENT" file, not certified.**
  - DCAD's July certified file leaves out accounts still under protest at certification. 2026 certified: 806,563 accounts, vs 847,075 in the current file. Of 2026 protested accounts, 40,655 were missing from it.
  - So each year uses the DCAD "CURRENT" roll for that year. For 2024 and 2025 that is the final roll.
  - The 2026 current file (Oct 30) still leaves out accounts with protests open at export. Added for 2026:
    - 157 accounts found only in the certified file.
    - 14,476 accounts protested in 2026 that are missing from both 2026 files. Their state code, tax rep and homestead come from `DCAD2027_CURRENT`. This is an attribute from the next year's file, not an estimate of the count. Flagged here because homestead and state code are as of 2027.
  - Protested accounts in no roll file at all are left out of homes_A but counted in all_protests: 2024: 2,217; 2025: 1,863; 2026: 1,163.
- **roll_version_date:** 2024 and 2025 tables are dated 2026-11-09 inside the zip; 2026 is the 2026-10-30 download.
- **Agent of record.**
  - `ACCOUNT_APPRL_YEAR.TAXPAYER_REP` (format "<rep id> <rep name>"; "UNASSIGNED" treated as none), plus any rep ID (`AUTH_TAX_REP_ID`) on that year's protest.
  - The roll field has **no appointment dates**, so the effective-before-deadline rule cannot be checked. It is the rep on the roll as of each file's date.
  - For agent-filed protests, the 2024 file's rep matches the 2024 protest's rep on 69% of accounts (2025: 85%). So old-year files mostly carry that year's rep, not today's.
  - Flag: 2024 Ownwell agent-of-record (60,655 homes) is much larger than its 2024 protests (17,431). Treat agent-of-record for earlier years with caution.
- **Protest file and validity.**
  - 2026 = ARB_ARCHIVE 2026 rows (closed by July 20) plus ARB_CURRENT 2026 rows (open after July). Only 5% of accounts appear in both.
  - A protest = an ARB row for that year except:
    - exemption-only protests (PROTEST_RCVD_CDX = "X"), and
    - 25.25 correction motions (any P2525*_IND = "Y").
  - Withdrawn, dismissed, no-show and late protests are kept.
  - Protests per year (rows, then accounts):

    | Year | Valid rows | Accounts (all property types) |
    |---|---|---|
    | 2022 | 191,491 | – |
    | 2023 | 193,845 | – |
    | 2024 | 200,768 | 193,831 |
    | 2025 | 222,986 | 216,844 |
    | 2026 | 237,508 | 234,586 |

  - `all_protests` / `all_agent_protests` = unique **accounts**.
- **Agent-filed vs owner-filed.** OWNER_PROTEST_IND = "N" (DCAD: "Owner did not protest but Tax Agent did") is agent-filed; "Y" is owner-filed.
  - An owner-filed home whose roll lists a rep (2026: 1,051 homes) counts in `homes_A_protested_by_owner` but sits in `seg_agent`, because it has an agent of record.
- **State code** = `ACCOUNT_APPRL_YEAR.SPTD_CODE`.
  - Home = A* (A1, A2).
  - Mobile homes: M3 (RES division) plus M1/M2 (BPP division).
  - Mineral = G* (G1/G3, under COM).
- **Homestead** = an APPLIED_STD_EXEMPT row with HOMESTEAD_EFF_DT filled (DCAD's general residence homestead).
- **PTP protested** = 2026 agent-filed protest with rep 306. **PTP agent** = rep 306 on the roll or on a protest.
- **Segments:** full 2022-to-prior-year history exists for every year (2024 uses 2022–2023). `seg_lapsed` and `seg_never` are filled.
- **Firm grouping.**
  - Rep names come from the roll's TAXPAYER_REP text. The full ID → name list is in `work/dallas/tax_rep_names.csv`.
  - Brand regex (same as Tarrant, plus Dallas names):
    - R50 OWNWELL INC + C50 OWNWELL CRE → Ownwell
    - every "RYAN" rep → Ryan LLC (35 IDs: 114;116;194;359;377;380;382;399;417;423;425;460;483;803;823;832;884;887;903;908;921;922;935;943;960;967;A33;M80;P08;R11;R26;R80;X88;Z27;Z29)
    - N98 → O'Connor & Associates
    - 930 → Resolute
    - 558 → Texas Tax Protest
    - 381 → North Texas Property Tax
    - G37 → Goodrich
    - 458 → Ray Tax Group
    - G99 → Gill Denson
    - 466 → Cantrell McCulloch
    - 959 → Candace Rubin / Overtaxed
    - 254 → Hegwood
    - 060 → K.E. Andrews
  - Any other rep = its own name. A home with reps from two firms counts under each.

### Checks
- Every year: `homes_A_with_agent` ≤ homes_A, `homes_A_protested` ≤ homes_A, and segments add up to homes_A (checked in the script).
- **PTP homes:**

  | Year | Agent of record | Protested |
  |---|---|---|
  | 2024 | 4,385 | 2,190 |
  | 2025 | 4,064 | 2,504 |
  | 2026 | 3,891 | 3,584 |

  The brief gives no portal count for Dallas.
