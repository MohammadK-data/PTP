"""Hays CAD state-code lookup, same layout as Denton's APPRAISAL_STATE_CODE file.

Sources
-------
1. Hays CAD "Standard Code Table Report - Code Table: State Classification, Tax Year: 2025"
   (61 codes), printed as Addendum II, pages 18-21, of the 2025 Mass Appraisal Report:
   https://hayscad.com/wp-content/uploads/2025/12/2025-MASS-APPRSL-REPORT.pdf
   (saved in Data/hayscad_reports/). Descriptions are copied verbatim, with the PDF's line wraps
   joined. Hays has not posted a 2026 code table yet (hayscad.com/reports-and-plans, Nov 2026).
2. Codes used in the 2026 roll but missing from that table (Hays moved to Orion for 2026 and the
   roll now also carries B, N and a few A*/E* sub-codes). Their wording comes from:
     - A1, A5, A7, A9, E1, E5: Hays' own land-type descriptions for the same codes in the 2026
       PropertyDataExport LAND file (Data/2026-PROPERTY-DATA-EXPORT-FILES-AS-OF-10-19-2026);
     - B: the "B-Multi-Family" category heading in Hays CAD's 2025 Annual Report
       (https://hayscad.com/wp-content/uploads/2025/12/2025-ANNUAL-REPORT.pdf, p. 7);
     - N: no Hays wording found -> inferred.
3. PTD (Comptroller) categories: Texas Comptroller, 2026 Property Classification Guide, Pub. 96-313
   (March 2026), https://comptroller.texas.gov/taxes/property-tax/docs/96-313.pdf (saved in
   Data/comptroller/); category X names from its Exhibit 7 (pp. 31-32). Where Denton's file has the
   category, its ptd_state_cd_description wording is reused so the counties line up.

Inferred (not verbatim from Hays CAD): the description of N, and the PTD mapping of L3 -> L1,
H2 -> H, N/N1 -> N, XB/XC (dropped from the 2026 guide; old Comptroller wording),
XV-11.251 and XW-11.36 -> XV (no own Comptroller category). All other local codes either equal the
PTD code or carry it as their prefix (C1A -> C1, B1..B3 -> B, S1..S7 -> S, XE-11.182 -> XE, ...).

The script also checks every state code in the 2026 roll (Orion certified PropertyExport and the
latest PropertyDataExport IMPROVEMENT/LAND files) is in the table, when those files are present.

Output: Hays/output/hays_2026_state_codes.csv
"""
import csv
import io
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/hays_2026_state_codes.csv"
YEAR = "02026"  # same 5-char format as Denton / Dallas / Tarrant files
ORION = ROOT / "Data/2026_07_18_2127-Orion-2026-Certified-Export/2026_07_18_2127_PropertyExport.txt"
PDE = ROOT / "Data/2026-PROPERTY-DATA-EXPORT-FILES-AS-OF-10-19-2026"

# Comptroller (PTAD) category names; Denton's wording where Denton has the category
PTD = {
    "A": "SINGLE-FAMILY RESIDENTIAL", "B": "MULTIFAMILY RESIDENTIAL", "C1": "VACANT LOTS AND TRACTS",
    "D1": "QUALIFIED OPEN-SPACE LAND", "D2": "FARM OR RANCH IMPROVEMENTS ON QUALIFIED OPEN-SPACE",
    "E": "RURAL LAND,NOT QUALIFIED FOR OPEN-SPACE LAND APPRA", "F1": "COMMERCIAL REAL PROPERTY",
    "F2": "INDUSTRIAL REAL PROPERTY", "G1": "OIL AND GAS", "G2": "MINERALS",
    "H": "TANGIBLE PERSONAL PROPERTY - PERSONAL VEHICLES, NOT USED FOR BUSINESS PURPOSES",
    "J1": "WATER SYSTEMS", "J2": "GAS DISTRIBUTION SYSTEMS", "J3": "ELECTRIC COMPANIES (INCLUDING CO-OPS)",
    "J4": "TELEPHONE COMPANIES (INCLUDING CO-OPS)", "J5": "RAILROADS", "J6": "PIPELINES",
    "J7": "CABLE COMPANIES", "J8": "OTHER TYPE OF UTILITY", "J9": "RAILROAD ROLLING STOCK",
    "L1": "COMMERCIAL PERSONAL PROPERTY", "L2": "INDUSTRIAL AND MANUFACTURING PERSONAL PROPERTY",
    "M1": "MOBILE HOMES", "N": "INTANGIBLE PERSONAL PROPERTY", "O": "RESIDENTIAL INVENTORY",
    "S": "SPECIAL INVENTORY",
    "XA": "PUBLIC PROPERTY FOR HOUSING INDIGENT PERSONS (11.111)",
    "XB": "INCOME PRODUCING TANGIBLE PERSONAL PROPERTY VALUED UNDER $2,500 (11.145)",
    "XC": "MINERAL INTEREST PROPERTY VALUED UNDER $500 (11.146)",
    "XD": "IMPROVING PROPERTY FOR HOUSING WITH VOLUNTEER LABOR (11.181)",
    "XE": "COMMUNITY HOUSING DEVELOPMENT ORGANIZATIONS (11.182)",
    "XF": "ASSISTING AMBULATORY HEALTH CARE CENTERS (11.183)",
    "XG": "PRIMARILY PERFORMING CHARITABLE FUNCTIONS (11.184)",
    "XH": "DEVELOPING MODEL COLONIA SUBDIVISIONS (11.185)",
    "XI": "YOUTH SPIRITUAL, MENTAL AND PHYSICAL DEVELOPMENT ORGANIZATIONS (11.19)",
    "XJ": "PRIVATE SCHOOLS (11.21)",
    "XL": "ORGANIZATIONS PROVIDING ECONOMIC DEVELOPMENT SERVICES TO LOCAL COMMUNITY (11.231)",
    "XM": "MARINE CARGO CONTAINERS (11.25)",
    "XN": "MOTOR VEHICLES LEASED FOR PERSONAL USE (11.252)",
    "XO": "MOTOR VEHICLES FOR INCOME PRODUCTION AND PERSONAL USE (11.254)",
    "XP": "OFFSHORE DRILLING EQUIPMENT NOT IN USE (11.271)",
    "XQ": "INTRACOASTAL WATERWAY DREDGE DISPOSAL SITE (11.29)",
    "XR": "NONPROFIT WATER OR WASTEWATER CORPORATION (11.30)",
    "XS": "RAW COCOA AND GREEN COFFEE HELD IN HARRIS COUNTY (11.33)",
    "XT": "LIMITATION ON TAXES IN CERTAIN MUNICIPALITIES (11.34)",
    "XU": "MISCELLANEOUS EXEMPTIONS (11.23)",
    "XV": "OTHER TOTALLY EXEMPT PROPERTIES (INCLUDING PUBLIC",
}

# (Hays code, Hays description, PTD code). Block 1 = 2025 State Classification code table (verbatim).
CODES = [
    ("A", "A - SINGLE-FAMILY RESIDENTIAL", "A"),
    ("B1", "B1-Multi Family (> 4-plex)", "B"),
    ("B2", "B2-Duplexes", "B"),
    ("B3", "B3-Fourplex (triplex Included)", "B"),
    ("C1", "C1-Vac Residential Platted Lots (5 Ac Or Less)", "C1"),
    ("C1A", "C1A - Vac Bus/Commercial (lots/tracts)", "C1"),
    ("C3", "C3-Vac Platted Lots (subd > 5 Ac)", "C1"),
    ("D1", "D1-Qualified Ag Land", "D1"),
    ("D2", "D2-Farm & Ranch impt on Qualified Open-space Land", "D2"),
    ("E", "E - Rural Land, not Qualified for Open-Space and Res Imps", "E"),
    ("F1", "F1-Commercial - Real Property", "F1"),
    ("F2", "F2-Industrial - Real Property", "F2"),
    ("G1", "G1-Oil & Gas", "G1"),
    ("G2", "G2-Real Property: Minerals", "G2"),
    ("H1", "H1-Tangible Personal, Nonbusiness Vehicles", "H"),
    ("H2", "H2-Tangible Personal Prop:Goods in Transit", "H"),
    ("J1", "J1-Water Systems", "J1"),
    ("J2", "J2-Gas Companies", "J2"),
    ("J3", "J3-Electric Companies", "J3"),
    ("J4", "J4-Telephone Companies", "J4"),
    ("J5", "J5-Railroads", "J5"),
    ("J6", "J6-Pipelines", "J6"),
    ("J7", "J7-Cable Tv Companies", "J7"),
    ("J8", "J8-Other", "J8"),
    ("J9", "J9-Railroad Rolling Stock", "J9"),
    ("L1", "L1-Commercial - Personal Property", "L1"),
    ("L2", "L2-Industrial - Personal Property", "L2"),
    ("L3", "L3-Comm - Pp (lease Equip & Autos)", "L1"),
    ("M1", "M1-Mobile Homes", "M1"),
    ("N1", "N1-Trans Bus Intangible Assets - Rail", "N"),
    ("O", "O-RESIDENTIAL INVENTORY", "O"),
    ("S1", "S1-Special Inventory - Auto Dealers", "S"),
    ("S2", "S2-Special Inventory - Manufactured Home Dealers", "S"),
    ("S3", "S3-Special Inventory - Heavy Equipment Dealers", "S"),
    ("S4", "S4-Special Inventory - Recreational Vehicle & Camper Dealers", "S"),
    ("S5", "S5-Special Inventory - Truck Dealers", "S"),
    ("S6", "S6-Special Inventory - Vessels", "S"),
    ("S7", "S7 - Special Inventory - Trailers 4,000+ lbs", "S"),
    ("XA-11.111", "XA-11.111 - Public property for housing indigent persons", "XA"),
    ("XB-11.145", "XB-11.145 - Income Producing Tangible Pers Prop valued <2500", "XB"),
    ("XC-11.146", "XC-11.146 - Mineral interest property valued <500", "XC"),
    ("XD-11.181", "XD-11.181 - Improving property for housing w/volunteer labor", "XD"),
    ("XE-11.182", "XE-11.182 - Community Housing Development Organizations", "XE"),
    ("XF-11.183", "XF-11.183 - Assisting ambulatory health care centers", "XF"),
    ("XG-11.184", "XG-11.184 - Primarily performing charitable functions", "XG"),
    ("XH-11.185", "XH-11.185 - Developing model colonia subdivisions", "XH"),
    ("XI-11.19", "XI-11.19 - Youth spiritual mental/physical development org", "XI"),
    ("XJ-11.21", "XJ-11.21 - Private schools", "XJ"),
    ("XL-11.231", "XJ-11.231 - Orgs Providing Econ Developmt Svcs to Local Cmty", "XL"),  # sic: "XJ" in Hays' table
    ("XM-11.25", "XM-11.25 - Marine cargo containers", "XM"),
    ("XN-11.252", "XN-11.252 - Motor Vehicles leased for personal use", "XN"),
    ("XO-11.254", "XO-11.254 - Motor Veh for income productions & personal use", "XO"),
    ("XP-11.271", "XP-11.271 - Offshore drilling equipment not in use", "XP"),
    ("XQ-11.29", "XQ-11.29 - Intracoastal waterway dredge disposal site", "XQ"),
    ("XR-11.30", "XR-11.30 - Nonprofit water or wastewater corporations", "XR"),
    ("XS-11.33", "XS-11.33 - Raw cocoa and green coffee held in Harris Co", "XS"),
    ("XT-11.34", "XT-11.34 - Limitation on taxes in certain municipalities", "XT"),
    ("XU-11.23", "XU-11.23 - Misc Exemptions", "XU"),
    ("XV", "XV - Other Exemptions,Public prop,Religious,Charitable Org", "XV"),
    ("XV-11.251", "XV-11.251 - Freeport Exemption", "XV"),
    ("XW-11.36", "XW-11.36 Child Care Facility, BPP Bio Med", "XV"),
    # Block 2: in the 2026 roll, not in the 2025 code table (see docstring for wording sources)
    ("A1", "A1-Residential", "A"),
    ("A5", "A5-Residential > 5 Ac", "A"),
    ("A7", "A7-MH Only (Split/Subds)", "A"),
    ("A9", "A9-Res (Misc Impts)", "A"),
    ("B", "B-Multi-Family", "B"),
    ("E1", "E1-Rural Land Not Qualified for Open Space Appraisal < 5 AC", "E"),
    ("E5", "E5-Rural Land Not Qualified for Open-space Appraisal > 5 AC", "E"),
    ("N", "N-Intangible Personal Property", "N"),  # inferred; used on 10 royalty-interest accounts
]


def roll_codes():
    """Counter of state codes used in the local 2026 roll files (empty if none are present)."""
    used = Counter()
    if ORION.exists():
        with open(ORION, encoding="utf-8", errors="replace", newline="") as f:
            for r in csv.DictReader(f):
                for col in ("StateCodeLand", "StateCodeImp"):
                    used[r[col].strip()] += 1
    for kind in ("IMPROVEMENT", "LAND"):
        for zp in sorted(PDE.glob(f"*-{kind}-*.zip")):
            with zipfile.ZipFile(zp) as z, z.open(z.namelist()[0]) as fh:
                for r in csv.DictReader(io.TextIOWrapper(fh, "utf-8", errors="replace")):
                    used[r["StateCode"].strip()] += 1
    used.pop("", None)
    return used


def main():
    csv.field_size_limit(1 << 30)
    codes = [c for c, _, _ in CODES]
    assert len(codes) == len(set(codes)), "duplicate state code"
    assert all(p in PTD for _, _, p in CODES), "PTD code without a description"

    used = roll_codes()
    missing = sorted(set(used) - set(codes))
    if missing:
        raise SystemExit(f"Codes in the 2026 roll but not in the table: {missing}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["state_cd", "state_cd_description", "ptd_state_cd", "ptd_state_cd_description", "state_cd_year"])
        for code, desc, ptd in sorted(CODES):
            w.writerow([code, desc, ptd, PTD[ptd], YEAR])
    note = f"all {len(used)} codes in the 2026 roll covered" if used else "2026 roll files not found, check skipped"
    print(f"{OUT}: {len(CODES)} codes; {note}")


if __name__ == "__main__":
    main()
