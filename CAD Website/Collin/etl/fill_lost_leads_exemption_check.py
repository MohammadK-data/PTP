"""Fill exemption / commercial-flag columns for the Collin commercial lost-leads list.

Source: Collin CAD Appraisal Data - 2026 (data.texas.gov dataset 5tkr-3759),
pulled into ../Data/2026/collin_2026_lost_leads_rows.csv and 2025 (vffy-snc6)
into ../Data/collin_2025_lost_leads_rows.csv.

Fully exempt = any exemption code starting with "EX-" (same test as the
Collin rule on the PTP Commercial Opportunity page).

Usage: python -I fill_lost_leads_exemption_check.py <lost_leads.csv>
(rewrites the file in place; only the four blank columns are filled).
"""
import csv
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "Data"
R26 = DATA / "2026" / "collin_2026_lost_leads_rows.csv"
R25 = DATA / "collin_2025_lost_leads_rows.csv"

MANUAL_NOTES = {
    "81066": (
        "EX7 is not a Collin code. 2026 roll: state code F1, exemption EX-XV (also on the "
        "2026 absolute-exemption list, 16 Nov). Same in 2025. Owner is a charity "
        "(Agape Resources & Assistance Center). The building is a 1,494 sq ft house built "
        "2006 (residential class R02, land type A1, nbhd EXEMPT). Fully exempt, so it should drop out."
    ),
    "2132829": "State code changed: E (not commercial) in 2025, F1 in 2026. EX-XV both years (Rise Fellowship Church).",
    "2659972": "Owner changed: Young Terri Lee (2025) to Numo Properties LLC (deed 29 Oct 2025).",
}


def load(path):
    with open(path, newline="") as f:
        return {r["propid"]: r for r in csv.DictReader(f)}


def main(target):
    r26, r25 = load(R26), load(R25)
    with open(target, newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)

    for row in rows:
        acct = row["cad_account"].strip()
        roll = r26.get(acct)
        notes = []
        if roll is None:
            row["notes"] = "Account not found on 2026 Collin roll."
            continue
        codes = [c.strip() for c in roll["exemptcodes"].split(",") if c.strip()]
        codes = list(dict.fromkeys(codes))
        row["exemption_codes_2026"] = ";".join(codes)
        row["fully_exempt_Y_N"] = "Y" if any(c.startswith("EX-") for c in codes) else "N"
        row["commercial_flag_2026"] = "Y" if roll["compropflag"].lower() == "true" else "N"

        if roll["propcategorycode"] != row["state_code_2026"]:
            notes.append(f"State code on roll is {roll['propcategorycode']}, not {row['state_code_2026']}.")
        if acct in MANUAL_NOTES:
            notes.append(MANUAL_NOTES[acct])
        elif row["ptp_state_code"] not in ("0", "", roll["propcategorycode"]):
            extra = (
                f" It matches the roll's land type code ({roll['landtypecode']})."
                if row["ptp_state_code"] == roll["landtypecode"] else ""
            )
            notes.append(f"PTP DB state code {row['ptp_state_code']} differs from roll state code {roll['propcategorycode']}.{extra}")
        if acct not in r25:
            notes.append("Not on 2025 roll.")
        if row["fully_exempt_Y_N"] == "Y" and not roll["noticevalmarket"]:
            owner = "" if acct in MANUAL_NOTES else f" Owner: {roll['ownername'].title()}."
            notes.append(f"No 2026 notice value (exempt). The value shown is the 2026 market value.{owner}")
        row["notes"] = " ".join(notes)

    with open(target, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main(sys.argv[1])
