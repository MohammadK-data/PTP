# Commercial definition check: Dallas and Tarrant 2026 (17 Nov 2026)

Why: the teammate's commercial totals were lower than ours. They count commercial by state code
(F1, F2, commercial land) and leave out apartments. We counted the county's own commercial group
(DCAD division COM, TAD class C), which includes apartments.

Source: our CAD-based files, `CAD Website/Dallas/output/dallas_values_2026.csv` and
`CAD Website/Tarrant/output/tarrant_values_2026.csv`. Only protested 2026 accounts are included.
The teammate's own files (PTP_Commercial_Data on Drive) were NOT compared account by account.

## Files
- `dallas_commercial_accounts_2026.csv`, `tarrant_commercial_accounts_2026.csv`: every account in the
  county's commercial group, plus commercial and apartment accounts filed elsewhere. Columns `bucket`,
  `state_code` and `in_county_commercial_group` let you rebuild either definition.
  Tarrant: sum `reduction_counted` (closed cases only, 89 flagged class C accounts excluded; this
  matches our $16.0B).

## Buckets (state codes)
| Bucket | Dallas | Tarrant |
|---|---|---|
| Commercial/industrial building | F10, F20 | F1, F2 |
| Commercial/industrial land | C12, C13 | C1C, C2C |
| Apartments | B11 | BC |

## Results
**Dallas, COM = 37,318 accounts / $24.1B**
- Commercial buildings: 22,580 / $14.08B. Commercial land: 8,331 / $0.19B
- Apartments: 3,334 / $9.77B (teammate: 3,381 / $9.89B)
- Other (minerals G10 1,902, farm land D10 491, utilities, homes): 3,073 / $0.06B
- Commercial without apartments (all divisions): 31,055 / $14.34B (teammate: 31,428 / $14.67B, older 7 Oct file)

**Tarrant, class C = 28,098 accounts / $16.0B**
- Commercial buildings: 21,227 / $8.62B. Commercial land: 4,518 / $0.25B
- Apartments: 1,922 / $7.15B (teammate: 1,912 / $7.14B)
- Other (utilities, farm/ranch, homes): 431 / $0.01B
- Commercial without apartments: 25,769 / $8.87B. Teammate: 20,940 / $8.48B, so about
  4,800 accounts / $0.39B are missing from their count, probably the rows with no property code.
  That is about 4% low in dollars but about 19% low in accounts.

## Account-level match against the teammate's files (done 17 Nov)
Their files: `tarrant_protests_2026.csv` (21 Oct) and `dallas_protests_2025-2026.csv` (7 Oct), from PTP_Commercial_Data.
Both of their totals rebuild exactly from those files using F1/F2/C1C/C2C (Tarrant) and F10/F20/C12/C13 (Dallas).

**Tarrant: their count misses about 4,870 commercial accounts.** Their file has a blank `state_code` for
20,152 Real-property accounts ($0.34B). TAD's roll codes about 4,870 of them as commercial: 3,867 C1C
vacant commercial land, 928 F1, 64 F2, 15 C2C. That is about $0.2B in reductions. Their file has only 13
C1C accounts in total. Code-level detail: `tarrant_ours_vs_teammate_codes.csv`. Their "about 4%"
estimate holds in dollars, but they are about 19% low in accounts.
Their blank rows also include 5,229 Personal accounts ($1.16B) and 4,693 Mineral accounts. That doesn't affect commercial real property.

**Dallas: 37,816 vs 37,318 comes from a filtering rule, not file dates.** Their file keeps exemption-only
protests (`protest_type` = Exemption, 10,172 accounts in 2026). Our build drops them, along with 25.25
motions. With exemption-only protests removed, their COM is 37,302 accounts / $24.36B (ours: 37,318 / $24.09B),
and commercial without apartments is 31,048 / $14.53B (ours: 31,055 / $14.34B). Their apartments, 3,381,
are B11 + B12 inside COM.

## Open items
- Jason decides whether commercial includes apartments. Minerals, farm land and utilities are
  about 3,000 accounts in Dallas but near $0.
- Agree whether exemption-only protests count (Dallas). Teammate to fill the blank Tarrant state codes
  from TAD's roll (or use our class C file).
