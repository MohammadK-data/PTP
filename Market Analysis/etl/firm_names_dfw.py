"""Agent name -> firm (used by the Denton and Rockwall market scripts).

Rule: brand keywords first (one firm per brand, whatever the office/suffix), else the cleaned agent name
(uppercase, '(Mineral)', '(MO)', ' - <office>', 'FKA ...' and corporate suffixes dropped)."""
import re

BRANDS = [  # (regex on upper-case name, firm)
    (r"^PROPERTY TAX PROTEST$", "Property Tax Protest"),
    (r"\bOWNWELL\b", "Ownwell"),
    (r"\bTEXAS PROTAX\b|\bTX PROTAX\b", "Texas ProTax"),
    (r"^RYAN (LLC|TAX COMPLIANCE)\b|\bRYAN LLC\b", "Ryan LLC"),
    (r"O'?\s*CONNOR\s*&\s*ASSOC", "O'Connor & Associates"),
    (r"\bGOODRICH\b", "Goodrich Realty Consulting (Jim Goodrich)"),
    (r"\bK\.?\s?E\.? ANDREWS\b", "K.E. Andrews & Company"),
    (r"\bMERIT ADVISORS\b", "Merit Advisors"),
    (r"\bRESOLUTE PROPERTY TAX\b", "Resolute Property Tax Solutions"),
    (r"\bNORTH TEXAS PROPERTY TAX SERV", "North Texas Property Tax Services"),
    (r"\bTEXAS TAX PROTEST\b", "Texas Tax Protest"),
    (r"\bRAY TAX GROUP\b", "The Ray Tax Group"),
    (r"\bAD VALOREM ADVISORS\b", "Ad Valorem Advisors"),
    (r"\bKROLL\b|\bDUFF & PHELPS\b", "Kroll"),
    (r"\bMARVIN F\.? POER\b", "Marvin F. Poer & Company"),
    (r"\bPOPP HUTCHESON\b", "Ryan LLC"),
]


def strip_id(name):
    """'NAME (245)', 'NAME-793132', 'NAME -131' -> 'NAME' (Denton's 2024 agent list carries the ID in the name)."""
    return re.sub(r"\s*(\(\d+\)|-\s*\d+)\s*$", "", (name or "").strip())


def clean(name):
    n = strip_id(name).upper().strip()
    n = re.sub(r"\((MINERAL|MO|BPP|COMMERCIAL|RESIDENTIAL)\)", "", n)
    n = re.sub(r"\bF/?K/?A\b.*$", "", n)
    n = re.sub(r"\s+-\s+.*$", "", n)
    n = re.sub(r"[.,]", " ", n)
    n = re.sub(r"\b(LLC|L L C|INC|INCORPORATED|LP|LLP|PLLC|CORP|CORPORATION|CO|COMPANY|LTD)\b", "", n)
    return re.sub(r"\s+", " ", n).strip(" &-")


def firm_of(name, agent_id=None, ptp_ids=()):
    if agent_id is not None and str(agent_id) in {str(x) for x in ptp_ids}:
        return "Property Tax Protest"
    up = strip_id(name).upper().strip()
    if up == "RYAN":
        return "Ryan LLC"
    for rx, firm in BRANDS:
        if re.search(rx, up):
            return firm
    return clean(up).title() or f"Agent {agent_id}"
