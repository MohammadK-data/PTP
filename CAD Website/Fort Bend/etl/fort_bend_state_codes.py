"""Fort Bend CAD (FBCAD) state-code lookup, same layout as Denton's APPRAISAL_STATE_CODE file.

Sources (copies in Fort Bend/Data/):
1. FBCAD Residential Appraisal Manual, rev. 2/06/2019, Section 10.4 "State Code List" (PDF pages 30-31,
   manual pages 27-28): https://www.fbcad.org/wp-content/uploads/2020/01/Residential-Appraisal-Manual.pdf
   -> base list and wording (newest FBCAD list found).
2. FBCAD Commercial Property Manual, rev. 03/2023, Appendix F "State Classification Codes ... as of 4/13/2006"
   (PDF pages 172-174, manual pages 154-156):
   https://www.fbcad.org/wp-content/uploads/2023/05/CommercialPropertyManualRevised03.2023.pdf
   -> same codes as (1) minus C7, plus J9 "Utility Personal Other" (taken from here).
3. Codes used in the 2026 roll but on neither FBCAD list (O1, O2, XA, XE, XG, XJ, XR, XU, XV): wording is the
   Comptroller's PTAD category names (as listed at https://taxnetusa.com/research/texas/sptb.php). FBCAD's
   2022 Annual Report only shows them rolled up as "O Real, inventory" and "X Exempt".

Mapping to ptd_state_cd: the Orion export layout calls StateCodeLand/StateCodeImp the "PTD Code", so a base
code maps to its own PTAD category (J7->J7, J9->J9 ...). Suffixed codes roll up to their base code, and FBCAD's
sub-letter splits roll up to PTAD's (C* -> C1, A* -> A, B* -> B). The INFERRED set below marks every mapping
that is a judgement call, not FBCAD's own text. PTAD wording is reused from Denton's file. X* subcategory
wording (except XV, which is Denton's) is the Comptroller's.

If the local 2026 Orion certified + supplement exports are present (CAD Website/For Bend/Data), the script also
checks that every 2026 StateCodeLand/StateCodeImp is covered and prints counts.

Output: Fort Bend/output/fort_bend_2026_state_codes.csv
Run: /Users/user2/PTP/.venv/bin/python -I "CAD Website/Fort Bend/etl/fort_bend_state_codes.py"
"""
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/fort_bend_2026_state_codes.csv"
ROLL_DIR = ROOT.parent / "For Bend/Data"  # existing local Fort Bend downloads (folder name has a typo)
YEAR = "02026"  # same 5-char format as Denton, Tarrant, Dallas, Hays

# Comptroller (PTAD) category names, worded as in Denton's file (X sub-codes: Comptroller wording)
PTD = {
    "A": "SINGLE-FAMILY RESIDENTIAL", "B": "MULTIFAMILY RESIDENTIAL", "C1": "VACANT LOTS AND TRACTS",
    "D1": "QUALIFIED OPEN-SPACE LAND", "D2": "FARM OR RANCH IMPROVEMENTS ON QUALIFIED OPEN-SPACE",
    "E": "RURAL LAND,NOT QUALIFIED FOR OPEN-SPACE LAND APPRA", "F1": "COMMERCIAL REAL PROPERTY",
    "F2": "INDUSTRIAL REAL PROPERTY", "G1": "OIL AND GAS", "G2": "MINERALS", "G3": "OTHER SUB-SURFACE INTERESTS",
    "J1": "WATER SYSTEMS", "J2": "GAS DISTRIBUTION SYSTEMS", "J3": "ELECTRIC COMPANIES (INCLUDING CO-OPS)",
    "J4": "TELEPHONE COMPANIES (INCLUDING CO-OPS)", "J5": "RAILROADS", "J6": "PIPELINES",
    "J7": "CABLE COMPANIES", "J8": "OTHER TYPE OF UTILITY", "J9": "RAILROAD ROLLING STOCK",
    "L1": "COMMERCIAL PERSONAL PROPERTY", "L2": "INDUSTRIAL AND MANUFACTURING PERSONAL PROPERTY",
    "M1": "MOBILE HOMES", "M2": "OTHER TANGIBLE PERSONAL PROPERTY", "N": "INTANGIBLE PERSONAL PROPERTY",
    "O": "RESIDENTIAL INVENTORY", "S": "SPECIAL INVENTORY",
    "XA": "PUBLIC PROPERTY FOR HOUSING INDIGENT PERSONS",
    "XE": "COMMUNITY HOUSING DEVELOPMENT ORGANIZATIONS",
    "XG": "PRIMARILY PERFORMING CHARITABLE FUNCTIONS", "XJ": "PRIVATE SCHOOLS",
    "XR": "NONPROFIT WATER OR WASTEWATER CORPORATIONS", "XU": "MISCELLANEOUS EXEMPTIONS",
    "XV": "OTHER TOTALLY EXEMPT PROPERTIES (INCLUDING PUBLIC",
}

# (code, FBCAD description, ptd_state_cd). Wording from source 1 unless noted.
CODES = [
    ("A1", "RESIDENTIAL SINGLE FAMILY HOUSES", "A"),
    ("A2", "RESIDENTIAL MOBILE (ON OWNERS LAND ONLY)", "A"),
    ("A3", "CONDOMINIUMS & TOWNHOUSES (INDIVIDUALLY OWNED)", "A"),
    ("A4", "MISCELLANEOUS BUILDINGS ON RESIDENTIAL LAND", "A"),
    ("A5", "HOUSE ONLY ON LEASED LAND", "A"),
    ("B1", "MULTI-FAMILY (9 OR MORE UNITS)", "B"),
    ("B2", "DUPLEX", "B"),
    ("B3", "TRIPLEX TO EIGHTPLEX", "B"),
    ("C1", "VACANT RESIDENTIAL LOTS / TRACTS INCORPORATED CITY", "C1"),
    ("C2", "VACANT RESIDENTIAL LOTS / TRACTS SMALL TOWNS & VILLAGE", "C1"),
    ("C3", "VACANT RESIDENTIAL LOTS / TRACTS RURAL SUBDIVISIONS", "C1"),
    ("C4", "VACANT RESIDENTIAL LOTS / TRACTS RURAL", "C1"),
    ("C7", "PRIVATE ROADS ON TRACTS LESS THAN 5 ACRES", "C1"),
    ("C9", "SPECIAL VACANT COMMERCIAL", "C1"),
    ("D1", "RANCH LAND", "D1"),
    ("D2", "TIMBERLAND", "D1"),
    ("D3", "FARMLAND", "D1"),
    ("D4", "UNDEVELOPED / NON AG QUALIFIED LAND", "E"),
    ("D5", "LAND WITH NO MARKETABLE VALUE (ROADS, CEMETERIES, DITCHES)", "E"),
    ("D6", "ORCHARDS AND / OR GROVES", "D1"),
    ("D7", "PUBLIC ROADS AND RIGHT-A-WAYS", "XV"),
    ("E1", "RESIDENTIAL FARM & RANCHLAND, IMPROVEMENTS", "E"),
    ("E2", "FARM, RANCHLAND IMPROVEMENTS", "D2"),
    ("E3", "MOBILE HOMES ON AG LAND", "E"),
    ("F1", "REAL COMMERCIAL", "F1"),
    ("F1H", "HOMEOWNER'S ASSOC. (GRANTED SPECIAL VALUATION ONLY)", "F1"),
    ("F1M", "MOBILE HOME PARKS", "F1"),
    ("F1V", "VACANT LAND USED FOR COMMERCIAL PURPOSE", "F1"),
    ("F1X", "EXEMPT BUILDINGS", "F1"),
    ("F2", "REAL INDUSTRIAL (HUGH LANDRUM & ASSOCIATES ONLY)", "F2"),
    ("G1", "OIL, GAS & MINERAL RESERVES", "G1"),
    ("G2", "NON PRODUCTION MINERAL", "G2"),
    ("G3", "MINERAL OTHER", "G3"),
    ("H", "PERSONAL VEHICLE", "M2"),
    ("J1", "REAL & PERSONAL PROPERTY WATER SYSTEMS", "J1"),
    ("J2", "REAL & PERSONAL PROPERTY GAS COMPANIES", "J2"),
    ("J3", "REAL & PERSONAL PROPERTY ELECTRIC COMPANIES", "J3"),
    ("J4", "REAL & PERSONAL PROPERTY TELEPHONE COMPANIES", "J4"),
    ("J5", "REAL & PERSONAL PROPERTY RAILROADS", "J5"),
    ("J6", "REAL & PERSONAL PROPERTY PIPELINES", "J6"),
    ("J7", "REAL & PERSONAL PROPERTY COMMUNICATIONS (HLA ONLY)", "J7"),
    ("J7C", "REAL & PERSONAL PROPERTY COMMUNICATIONS (CAD ONLY)", "J7"),
    ("J8", "REAL & PERSONAL PROPERTY CABLE COMPANIES (HLA ONLY)", "J8"),
    ("J8C", "REAL & PERSONAL PROPERTY CABLE COMPANIES (CAD ONLY)", "J8"),
    ("J9", "UTILITY PERSONAL OTHER", "J9"),  # source 2 only
    ("L1", "TANGIBLE PERSONAL COMMERCIAL", "L1"),
    ("L1A", "TANGIBLE PERSONAL COMMERCIAL AIRCRAFT", "L1"),
    ("L1B", "TANGIBLE PERSONAL COMMERCIAL BILLBOARDS", "L1"),
    ("L1L", "TANGIBLE PERSONAL COMMERCIAL LEASING", "L1"),
    ("L1V", "TANGIBLE PERSONAL COMMERCIAL VEHICLES", "L1"),
    ("L2", "TANGIBLE PERSONAL INDUSTRIAL (HLA ONLY)", "L2"),
    ("L2C", "TANGIBLE PERSONAL INDUSTRIAL (CAD ONLY)", "L2"),
    ("L5", "TANGIBLE PERSONAL POLLUTION CONTROL", "L2"),
    ("M1", "TANGIBLE PERSONAL MOBILE HOMES", "M1"),
    ("M2", "TANGIBLE PERSONAL NON-BUSINESS AIRCRAFT", "M2"),
    ("M3", "TANGIBLE PERSONAL MOBILE HOMES", "M1"),
    ("M4", "TANGIBLE PERSONAL MISCELLANEOUS", "M2"),
    ("N", "INTANGIBLE", "N"),
    ("O", "INVENTORY", "O"),
    ("O1", "INVENTORY", "O"),  # source 3
    ("O2", "INVENTORY", "O"),  # source 3
    ("S", "SPECIAL INVENTORY", "S"),
    # source 3: Comptroller exempt subcategories seen in the 2026 roll
    ("XA", "PUBLIC PROPERTY FOR HOUSING INDIGENT PERSONS", "XA"),
    ("XE", "COMMUNITY HOUSING DEVELOPMENT ORGANIZATIONS", "XE"),
    ("XG", "PRIMARILY PERFORMING CHARITABLE FUNCTIONS", "XG"),
    ("XJ", "PRIVATE SCHOOLS", "XJ"),
    ("XR", "NONPROFIT WATER OR WASTEWATER CORPORATIONS", "XR"),
    ("XU", "MISCELLANEOUS EXEMPTIONS", "XU"),
    ("XV", "OTHER EXEMPT (INCL PUBLIC, RELIGIOUS, CHARITABLE)", "XV"),
]

# Rows whose description and/or PTD mapping is inferred rather than FBCAD's own text
INFERRED = {
    "O1": "description (FBCAD lists only 'O Inventory')", "O2": "description (FBCAD lists only 'O Inventory')",
    "XA": "description (Comptroller)", "XE": "description (Comptroller)", "XG": "description (Comptroller)",
    "XJ": "description (Comptroller)", "XR": "description (Comptroller)", "XU": "description (Comptroller)",
    "XV": "description (Comptroller)",
    "D2": "PTD D1: FBCAD D2 is timberland, not PTAD D2 improvements",
    "D4": "PTD E", "D5": "PTD E", "D7": "PTD XV", "E2": "PTD D2", "E3": "PTD E",
    "F1X": "PTD F1 (exempt buildings; could be reported as X)", "H": "PTD M2",
    "J7": "PTD J7 by code (FBCAD calls it communications)", "J7C": "PTD J7 by code",
    "J8": "PTD J8 by code (FBCAD calls it cable)", "J8C": "PTD J8 by code",
    "J9": "PTD J9 by code (FBCAD calls it utility personal other)", "L5": "PTD L2",
    "M4": "PTD M2", "C7": "PTD C1", "C9": "PTD C1",
}


def roll_counts():
    """Counter of 2026 StateCodeLand/StateCodeImp values in the local Orion exports, or None."""
    files = [*ROLL_DIR.glob("*Orion 2026 Certified Export*/*_PropertyExport.txt"),
             *ROLL_DIR.glob("*Orion 2026 Supplement*/*_PropertyExport.txt")]
    if not files:
        return None
    used = Counter()
    for f in files:
        with open(f, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                for col in ("StateCodeLand", "StateCodeImp"):
                    if (v := (r.get(col) or "").strip().upper()):
                        used[v] += 1
    return used


def main():
    codes = {c for c, _, _ in CODES}
    assert len(codes) == len(CODES), "duplicate code"
    assert all(p in PTD for _, _, p in CODES), "PTD code without wording"

    used = roll_counts()
    if used is not None:
        missing = {c: n for c, n in used.items() if c not in codes}
        if missing:
            raise SystemExit(f"Codes in the 2026 roll but not in the table: {missing}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["state_cd", "state_cd_description", "ptd_state_cd", "ptd_state_cd_description", "state_cd_year"])
        for code, desc, ptd in CODES:
            w.writerow([code, desc, ptd, PTD[ptd], YEAR])

    print(f"{OUT}: {len(CODES)} codes")
    if used is not None:
        print(f"2026 roll: {sum(used.values()):,} land/imp state-code entries, all covered; "
              f"{len(used)} codes in use")
    for code, _, ptd in CODES:
        n = f"{used.get(code, 0):>9,}" if used is not None else ""
        print(f"  {code:4} -> {ptd:3} {n}  {INFERRED.get(code, '')}")


if __name__ == "__main__":
    main()
