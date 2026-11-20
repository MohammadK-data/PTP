"""Dallas CAD state-code lookup, same layout as Denton's APPRAISAL_STATE_CODE file.

Source: DCAD's own cross-reference (SPTD_CD_XREF.pdf, shipped in every DCAD download),
"DCAD SPTD Code / PTAD Property Class Code". DCAD's PDF lists only "J" and "C" for the
utility and vacant-land rows; those are refined here to the Comptroller's current
subcategories (J1-J9, C1) so the column lines up with Denton's ptd_state_cd.

The script also checks every SPTD_CODE in the 2026 certified ACCOUNT_APPRL_YEAR file is covered.

Output: Dallas/output/dallas_2026_state_codes.csv
"""
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROLL = ROOT / "Data/DCAD2026_CERTIFIED_07232026/ACCOUNT_APPRL_YEAR.CSV"
OUT = ROOT / "output/dallas_2026_state_codes.csv"
YEAR = "02026"  # same 5-char format as the PACS/True Prodigy files (Denton, Tarrant)

# Comptroller (PTAD) category names, worded as in Denton's file
PTD = {
    "A": "SINGLE-FAMILY RESIDENTIAL", "B": "MULTIFAMILY RESIDENTIAL", "C1": "VACANT LOTS AND TRACTS",
    "D1": "QUALIFIED OPEN-SPACE LAND", "D2": "FARM OR RANCH IMPROVEMENTS ON QUALIFIED OPEN-SPACE",
    "E": "RURAL LAND,NOT QUALIFIED FOR OPEN-SPACE LAND APPRA", "F1": "COMMERCIAL REAL PROPERTY",
    "F2": "INDUSTRIAL REAL PROPERTY", "G1": "OIL AND GAS", "G3": "OTHER SUB-SURFACE INTERESTS",
    "J1": "WATER SYSTEMS", "J2": "GAS DISTRIBUTION SYSTEMS", "J3": "ELECTRIC COMPANIES (INCLUDING CO-OPS)",
    "J4": "TELEPHONE COMPANIES (INCLUDING CO-OPS)", "J5": "RAILROADS", "J6": "PIPELINES",
    "J7": "CABLE COMPANIES", "J9": "RAILROAD ROLLING STOCK", "L1": "COMMERCIAL PERSONAL PROPERTY",
    "L2": "INDUSTRIAL AND MANUFACTURING PERSONAL PROPERTY", "M1": "MOBILE HOMES",
    "N": "INTANGIBLE PERSONAL PROPERTY", "O": "RESIDENTIAL INVENTORY", "S": "SPECIAL INVENTORY",
}

# SPTD_CD_XREF.pdf (DCAD, as of July 25, 2011): code, PTAD class, DCAD description
XREF = [
    ("A11", "A", "SINGLE FAMILY RESIDENCES"), ("A12", "A", "SFR - TOWNHOUSES"),
    ("A13", "A", "SFR - CONDOMINIUMS"), ("A20", "A", "MOBILE HOME ON OWNERS LAND"),
    ("B11", "B", "MFR - APARTMENTS"), ("B12", "B", "MFR - DUPLEXES"),
    ("C11", "C1", "SFR - VACANT LOTS/TRACTS"), ("C12", "C1", "COMMERCIAL - VACANT PLOTTED LOTS/TRACTS"),
    ("C13", "C1", "INDUSTRIAL - VACANT PLOTTED LOTS/TRACTS"), ("C14", "C1", "RURAL VACANT - LESS THAN 5 ACRES"),
    ("D10", "D1", "QUALIFIED AGRICULTURAL LAND"), ("D20", "D2", "NON-QUALIFIED LAND"),
    ("E11", "E", "RANCH IMPROVEMENTS"), ("E12", "E", "FARM IMPROVEMENTS"),
    ("F10", "F1", "COMMERCIAL IMPROVEMENTS"), ("F20", "F2", "INDUSTRIAL IMPROVEMENTS"),
    ("G10", "G1", "OIL, GAS AND MINERAL RESERVES"), ("G30", "G3", "MINERALS, NON-PRODUCING"),
    ("J10", "J1", "PRIVATE WATER SYSTEMS"), ("J20", "J2", "GAS COMPANIES"),
    ("J30", "J3", "ELECTRIC COMPANIES"), ("J40", "J4", "TELEPHONE COMPANIES"),
    ("J51", "J5", "RAILROAD CORRIDOR"), ("J52", "J9", "RAILROAD ROLLING STOCK"),
    ("J60", "J6", "PIPELINES"), ("J70", "J7", "CABLE COMPANIES"),
    ("L10", "L1", "COMMERCIAL BPP"), ("M10", "L1", "WATERCRAFT"), ("M20", "L1", "AIRCRAFT"),
    ("L20", "L2", "INDUSTRIAL BPP"), ("M31", "M1", "MOBILE HOMES ON LEASED SPACES"),
    ("M32", "M1", "MOBILE HOMES FOR SALE (ON LOTS)"), ("N10", "N", "INTANGIBLES"),
    ("O10", "O", "RESIDENTIAL - VACANT LOTS AS INVENTORY"),
    ("O11", "O", "RESIDENTIAL - IMPROVEMENTS AS INVENTORY"), ("S10", "S", "SPECIAL INVENTORY"),
]


def main():
    with open(ROLL, encoding="latin-1", newline="") as f:
        used = Counter(r["SPTD_CODE"].strip() for r in csv.DictReader(f))
    known = {c for c, _, _ in XREF}
    missing = {c: n for c, n in used.items() if c not in known}
    if missing:
        raise SystemExit(f"Codes in the 2026 roll but not in the DCAD cross-reference: {missing}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["state_cd", "state_cd_description", "ptd_state_cd", "ptd_state_cd_description", "state_cd_year"])
        for code, ptd, desc in sorted(XREF):
            w.writerow([code, desc, ptd, PTD[ptd], YEAR])
    print(f"{OUT}: {len(XREF)} codes; {sum(used.values()):,} 2026 accounts, all covered")
    for code, _, _ in sorted(XREF):
        print(f"  {code:4} {used.get(code, 0):>9,}")


if __name__ == "__main__":
    main()
