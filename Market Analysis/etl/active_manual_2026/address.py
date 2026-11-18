"""Address parsing used on BOTH sides of the match (input file and CAD situs), so both are normalized the same way.

parse(street_address, city="") -> dict(number, street, core, unit)
  number : house number ("1181B" keeps its letter)
  street : normalized street (upper case, USPS suffix and direction abbreviations)
  core   : street without direction words and suffix words (e.g. "N QUAIL HOLLOW CT" -> "QUAIL HOLLOW"),
           used for matching because people drop or change the suffix ("Way" vs "Wy", "Dr" vs "Drive")
  unit   : unit / apartment / suite, when written after #, APT, UNIT, STE...
"""
import re

SUFFIX = {
    "STREET": "ST", "STR": "ST", "STREEY": "ST", "AVENUE": "AVE", "AV": "AVE", "DRIVE": "DR", "DRV": "DR",
    "LANE": "LN", "COURT": "CT", "CRT": "CT", "CIRCLE": "CIR", "CIRC": "CIR", "TRAIL": "TRL", "TR": "TRL",
    "ROAD": "RD", "BOULEVARD": "BLVD", "BLV": "BLVD", "PARKWAY": "PKWY", "PKY": "PKWY", "PLACE": "PL",
    "WY": "WAY", "TERRACE": "TER", "TERR": "TER", "COVE": "CV", "HIGHWAY": "HWY", "FREEWAY": "FWY",
    "EXPRESSWAY": "EXPY", "POINT": "PT", "PNT": "PT", "CROSSING": "XING", "HOLLOW": "HOLW", "SQUARE": "SQ",
    "TRACE": "TRCE", "RIDGE": "RDG", "BEND": "BND", "GROVE": "GRV", "HEIGHTS": "HTS", "MEADOW": "MDW",
    "MEADOWS": "MDWS", "CREEK": "CRK", "PASS": "PASS", "PATH": "PATH", "LOOP": "LOOP", "RUN": "RUN",
    "WAY": "WAY", "ROW": "ROW", "WALK": "WALK", "GLEN": "GLN", "SPRINGS": "SPGS", "SPRING": "SPG",
    "LANDING": "LNDG", "CANYON": "CYN", "VIEW": "VW", "VISTA": "VIS", "ESTATES": "EST", "PARK": "PARK",
    "PLAZA": "PLZ", "HILL": "HL", "HILLS": "HLS", "VALLEY": "VLY", "ISLAND": "IS", "HARBOR": "HBR",
    "CENTER": "CTR", "MANOR": "MNR", "OVAL": "OVAL", "ALLEY": "ALY", "COMMONS": "CMNS", "GATEWAY": "GTWY",
    "CAUSEWAY": "CSWY", "BAYOU": "BYU", "BRANCH": "BR", "BROOK": "BRK", "FIELD": "FLD", "FIELDS": "FLDS",
    "FOREST": "FRST", "GARDENS": "GDNS", "GARDEN": "GDN", "HAVEN": "HVN", "LAKE": "LK", "LAKES": "LKS",
    "MILL": "ML", "ORCHARD": "ORCH", "RANCH": "RNCH", "SHORES": "SHRS", "SUMMIT": "SMT", "TRAILS": "TRLS",
    "VILLAGE": "VLG", "PTH": "PATH", "LP": "LOOP", "PK": "PARK", "BLUFF": "BLF", "FORGE": "FRG", "CLIFF": "CLF",
    "BVLD": "BLVD", "TRAILS": "TRLS", "WOODS": "WDS", "CRESCENT": "CRES", "PRAIRIE": "PR", "STATION": "STA",
}
# words treated as the street "type" (dropped from core). Kept short on purpose: words like CREEK, HILL, PARK are
# often part of the name itself ("Walnut Creek Dr"), so only the true type words are dropped.
TYPE_WORDS = {"ST", "AVE", "DR", "LN", "CT", "CIR", "TRL", "RD", "BLVD", "PKWY", "PL", "WAY", "TER", "CV", "HWY",
              "FWY", "EXPY", "PT", "XING", "LOOP", "PATH", "RUN", "SQ", "TRCE", "PASS", "ROW", "WALK", "ALY", "PLZ"}
ROUTE_WORDS = {"HWY", "FWY", "EXPY", "LOOP"}     # "US HWY 180", "LOOP 820": the number is the route, not a unit
DIRS = {"NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W", "NORTHEAST": "NE", "NORTHWEST": "NW",
        "SOUTHEAST": "SE", "SOUTHWEST": "SW"}
DIR_ABBR = {"N", "S", "E", "W", "NE", "NW", "SE", "SW"}
ORDINAL = {"FIRST": "1ST", "SECOND": "2ND", "THIRD": "3RD", "FOURTH": "4TH", "FIFTH": "5TH", "SIXTH": "6TH",
           "SEVENTH": "7TH", "EIGHTH": "8TH", "NINTH": "9TH", "TENTH": "10TH"}
OTHER = {"COUNTY ROAD": "CR", "CO RD": "CR", "FARM TO MARKET": "FM", "FARM ROAD": "FM", "STATE HIGHWAY": "SH", "STATE HWY": "SH",
         "US HIGHWAY": "US HWY", "INTERSTATE HIGHWAY": "IH", "INTERSTATE": "IH", "I-": "IH ", "US-": "US HWY ",
         "SAINT": "ST", "MOUNT": "MT", "FORT": "FT"}
UNIT_WORDS = r"(?:#|APT\.?|APARTMENT|UNIT|STE\.?|SUITE|BLDG|BUILDING|SPC|SPACE|LOT|NO\.?)"
JUNK_UNIT = {"", "NONE", "ALL", "UNIT", "APT", "N/A", "NA"}
STATES = r"(?:TX|TEXAS)"


def _clean(s):
    s = str(s or "").upper().replace(" ", " ")
    s = s.replace("'", "")
    s = re.sub(r"[.,;]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse(street_address, city=""):
    s = _clean(street_address)
    city = _clean(city)
    unit = ""
    # "... # 209" written by the CRM: everything after the first " # " is the unit
    m = re.search(r"\s#\s*(.*)$", " " + s)
    if m:
        unit, s = m.group(1).strip(), s[: max(m.start() - 1, 0)].strip()
    s = re.sub(rf"^{STATES}\s+", "", s)                          # "TX 2206 Falcon Brook Dr"
    s = re.sub(rf"\s{STATES}(\s+\d{{5}}(-?\d{{4}})?)?$", "", s)  # "... DALLAS TX 75231"
    s = re.sub(r"\s\d{5}(-?\d{4})?$", "", s)
    if city and len(city) > 2 and s.endswith(" " + city):        # trailing city name
        s = s[: -len(city)].strip()
    for k, v in OTHER.items():
        s = re.sub(rf"(^|\s){re.escape(k)}", rf"\1{v}", s)
    s = re.sub(r"(^|\s)(\d+)(?!(?:ST|ND|RD|TH)\b)([A-Z]{2,})", r"\1\2 \3", s)        # "3814DUQUESNE"
    m = re.match(r"^(\d+[A-Z]?|\d+-\d+|\d+ \d/\d)\s+(.*)$", s)
    number, rest = (m.group(1), m.group(2)) if m else ("", s)
    number = number.replace(" ", "")
    if number.strip("0") == "":                                   # "0 ALLEN GENOA": vacant land, no real number
        number = ""
    # repeated number ("8825 8825 ROYAL OAKS DR")
    rest = re.sub(rf"^{re.escape(number)}\s+", "", rest) if number else rest
    # inline unit: "... #2225", "... APT 5", "... STE 100A"
    m = re.search(rf"\s{UNIT_WORDS}\s*([A-Z0-9-]+)\s*$", " " + rest)
    if m:
        unit, rest = unit or m.group(1), rest[: max(m.start() - 1, 0)].strip()
    rest = re.sub(r"\s#\s*$", "", rest)
    toks = [ORDINAL.get(DIRS.get(t, SUFFIX.get(t, t)), DIRS.get(t, SUFFIX.get(t, t))) for t in rest.split()]
    # address written twice ("115 JASMINE LN 115 JASMINE LN"): cut at the repeated number
    if number and number in toks:
        toks = toks[: toks.index(number)]
    # street name written twice ("REDWING LN REDWING LN", "MYSTIC STONE DR MYSTIC STONE"): cut after the type word
    for i in range(1, len(toks) - 1):
        if toks[i] in TYPE_WORDS and toks[i + 1] == toks[0]:
            toks = toks[: i + 1]
            break
    # trailing pure number after a street type word = unit ("10501 SOUTH DR 283")
    if len(toks) >= 3 and re.fullmatch(r"\d+[A-Z]?", toks[-1]) and toks[-2] in TYPE_WORDS - ROUTE_WORDS:
        unit, toks = unit or toks[-1], toks[:-1]
    while len(toks) > 2 and toks[-1] in TYPE_WORDS and toks[-2] == toks[-1]:   # "RUSHMORE ST ST"
        toks = toks[:-1]
    street = " ".join(toks)
    # core: drop direction words and the final street-type word ("N ROCKY PT CIR" -> "ROCKY PT")
    core = [t for t in toks if t not in DIR_ABBR]
    if len(core) > 1 and core[-1] in TYPE_WORDS:
        core = core[:-1]
    if not core or (len(core) == 1 and core[0] in TYPE_WORDS):                        # "SOUTH DR": the direction word is the name
        core = toks[:-1] if len(toks) > 1 and toks[-1] in TYPE_WORDS else toks
    core = " ".join(core)
    core = re.sub(r"^(STATE HWY|SH|US HWY|US|HWY|ST HWY)\s+(?=\d)", "HWY ", core)   # Hwy 66 = SH 66 = State Highway 66
    unit = _norm_unit(unit, number)
    return {"number": number, "street": street, "core": core.replace(" ", ""), "unit": unit}


def _norm_unit(u, number=""):
    u = _clean(u)
    if u in JUNK_UNIT:
        return ""
    u = re.sub(rf"^{UNIT_WORDS}\s*", "", u).strip()
    u = u.replace(" ", "").replace("-", "")
    if u in JUNK_UNIT or u == number or len(u) > 8:     # "None", the house number again, a property ID...
        return ""
    return u.lstrip("0") or u


def zip5(*vals):
    """First valid 5-digit Texas-range zip found in the values (75xxx-79xxx, 885xx)."""
    for v in vals:
        m = re.search(r"(?<!\d)(7[5-9]\d{3}|885\d{2})(?:-?\d{4})?(?!\d)", str(v or ""))
        if m:
            return m.group(1)
    return ""
