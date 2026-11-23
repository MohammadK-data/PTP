"""Write source_map.json: where each table on the Travis review page comes from.

The catalog is what traviscad.org/publicinformation listed (all three sections) on the date in PAGE["checked"]: its groups and
files, with links. Each table on the page is tied to the website download (.zip), the raw .TXT inside it,
and the PACS layout entry that documents it. Inner file lists come from our local copies of the zips.
Each file also gets a link to our copy in Google Drive (County Playbooks › Travis › Public Information) when
drive_files.json lists one with the same file name.

Usage: python3 -I make_source_map.py   (run from this folder; writes source_map.json)
"""
import json
import pathlib
import re

HERE = pathlib.Path(__file__).parent
TRAVIS = HERE.parent
LARGE = "https://traviscad.org/wp-content/largefiles/"
UP = "https://traviscad.org/wp-content/uploads/"

PAGE = {"label": "Travis CAD · Public Information", "url": "https://traviscad.org/publicinformation", "checked": "2026-11-23"}

# raw short file -> (layout file #, layout title, long file name), from Data/Legacy8.0.33-AppraisalExportLayout.xlsx
LAYOUT = {
    "APPR_HDR.TXT": (1, "Header File", "APPRAISAL_HEADER.TXT"),
    "PROP.TXT": (2, "Property", "APPRAISAL_INFO.TXT"),
    "PROP_ENT.TXT": (3, "Property-Entity Association", "APPRAISAL_ENTITY_INFO.TXT"),
    "TOTALS.TXT": (4, "Entity Totals", "APPRAISAL_ENTITY_TOTALS.TXT"),
    "ABS_SUBD.TXT": (5, "Abstract/Subdivision List", "APPRAISAL_ABSTRACT_SUBDV.TXT"),
    "STATE_CD.TXT": (6, "Property Tax Division Codes", "APPRAISAL_STATE_CODE.TXT"),
    "IMP_INFO.TXT": (7, "Improvements", "APPRAISAL_IMPROVEMENT_INFO.TXT"),
    "IMP_DET.TXT": (8, "Improvement Detail", "APPRAISAL_IMPROVEMENT_DETAIL.TXT"),
    "IMP_ATR.TXT": (9, "Improvement Features", "APPRAISAL_IMPROVEMENT_DETAIL_ATTR.TXT"),
    "LAND_DET.TXT": (10, "Land", "APPRAISAL_LAND_DETAIL.TXT"),
    "AGENT.TXT": (11, "Agent", "APPRAISAL_AGENT.TXT"),
    "ARB.TXT": (12, "Active ARB Properties", "APPRAISAL_ARB.TXT"),
    "LAWSUIT.TXT": (13, "Active Lawsuit Properties", "APPRAISAL_LAWSUIT.TXT"),
    "ENTITY.TXT": (14, "Entity", "APPRAISAL_ENTITY.TXT"),
    "COUNTRY.TXT": (16, "Country Codes", "APPRAISAL_COUNTRY_CODE.TXT"),
    "ARBITRATION.TXT": (17, "Properties in Arbitration", "ARBITRATION_LAWSUIT.TXT"),
    "MOBILE_HOME_INFO.TXT": (18, "Mobile Home Info", "APPRAISAL_MOBILE_HOME_INFO.TXT"),
    "TAX_DEFERRAL_INFO.TXT": (19, "Tax Deferral Info", "APPRAISAL_TAX_DEFERRAL_INFO.TXT"),
    "SKETCH_INFO.TXT": (20, "Sketches", "APPRAISAL_SKETCH_INFO.TXT"),
    "SB12.TXT": (21, "SB12", "APPRAISAL_SB12.TXT"),
}

CERT = {"id": "cert", "group": "Other Exports", "label": "2026 Certified Appraisal Export (July)",
        "url": LARGE + "2026%20Certified%20Appraisal%20Export%20Supp%200_07182026.zip",
        "local": "Data/2026 Certified Appraisal Export Supp 0_07182026/"}
SUPP = {"id": "supp", "group": "Other Exports", "label": "2026 Supplemental Appraisal Roll Export",
        "url": LARGE + "travis_SUPP%20336_2026_WEBSITE%20EXPORT_Renamed.zip",
        "local": "Data/travis_SUPP 335_2026_WEBSITE EXPORT_Renamed/",
        "note": "This page was profiled from SUPP 335, downloaded earlier. The website link now points to a newer upload, SUPP 336."}


def inside(folder):
    return sorted(p.name for p in (TRAVIS / folder).iterdir() if p.is_file())


def f(name, url, status="not", note="", contents=None, export=None):
    d = {"name": name, "url": url, "status": status}
    if note: d["note"] = note
    if contents: d["contents"] = contents
    if export: d["export"] = export  # a download whose raw files are profiled on the page (key in "downloads")
    return d


EARS_NOTE = "Comptroller (PTD) submission: totals PDFs plus a nested data .zip."
EARS_USED = (" The nested 227EARS .csv mixes three record types (AJR, AUD, TU2); each is its own table on this page,"
             " with column names from the Comptroller's manual 96-1051.")
EARS_26 = ["2026 Tax Rates.xlsx", "2026-2 Totals_PTD.pdf", "2026_2_PTD_50_253_TOTALS.pdf", "2026_2_PTD_ACREAGE_DETAIL_TOTALS.pdf",
           "2026_2_PTD_ACREAGE_TOTALS.pdf", "2026_2_PTD_ASSUMPTION.pdf", "2026_2_PTD_CITY_50_109_TOTALS.pdf", "2026_2_PTD_COUNTY_50_105_TOTALS.pdf",
           "2026_2_PTD_SCHOOL_50_108_TOTALS.pdf", "2026_2_PTD_SCHOOL_LIMITATION_DETAIL_TOTALS.pdf", "2026_2_PTD_SPECIAL_DISTRICT_50_868_TOTALS.pdf",
           "227EARS082626.zip", "227_50_897_082626_Revised.xlsx", "227_EARS_MIF_082626_Signed.pdf",
           "Tax Office Files for Abated Lawsuits, Sales & Deferrals/ (5 files)"]
EARS_24 = ["2024 Totals supp 1 PTD.pdf", "2024_PTD_50_253_TOTALS.pdf", "2024_PTD_50_897.zip", "2024_PTD_ACREAGE_DETAIL_TOTALS.pdf",
           "2024_PTD_ACREAGE_TOTALS.pdf", "2024_PTD_ASSUMPTION.pdf", "2024_PTD_CITY_50_109_TOTALS.pdf", "2024_PTD_COUNTY_50_105_TOTALS.pdf",
           "2024_PTD_SCHOOL_50_108_TOTALS.pdf", "2024_PTD_SCHOOL_LIMITATION_DETAIL_TOTALS.pdf", "2024_PTD_SPECIAL_DISTRICT_50_868_TOTALS.pdf",
           "227_EARS_MIF_082824_Signed.pdf", "227EARS082824.zip"]
EARS_23 = ["2023 Totals supp 2 PTD.pdf", "2023_PTD_50_253_TOTALS.pdf", "2023_PTD_ACREAGE_DETAIL_TOTALS.pdf", "2023_PTD_ACREAGE_TOTALS.pdf",
           "2023_PTD_ASSUMPTION.pdf", "2023_PTD_CITY_50_109_TOTALS.pdf", "2023_PTD_COUNTY_50_105_TOTALS.pdf", "2023_PTD_SCHOOL_50_108_TOTALS.pdf",
           "2023_PTD_SCHOOL_LIMITATION_DETAIL_TOTALS.pdf", "2023_PTD_SPECIAL_DISTRICT_50_868_TOTALS.pdf", "227EARS082923.zip (holds 227EARS083023.csv)",
           "227_EARS_MIF_082923_Signed.pdf"]
EARS_22 = ["2022 Totals supp 2.pdf", "2022_PTD_50_253.pdf", "2022_PTD_ACREAGE.pdf", "2022_PTD_ACREAGE_DETAIL.pdf", "2022_PTD_ASSUMPTION.pdf",
           "2022_PTD_CITY_50_109.pdf", "2022_PTD_COUNTY_50_105.pdf", "2022_PTD_SCHOOL_50_108.pdf", "2022_PTD_SCHOOL_LIMITATION_DETAIL.pdf",
           "2022_PTD_SPECIAL_DISTRICT_50_868.pdf", "227EARS092822.zip", "227_2022 EARS Tax Rate Submission.xlsx", "227_EARS_MIF_092822_Signed.pdf"]
EARS_25 = [n.replace("2024", "2025").replace("082824", "090425").replace("2025 Totals supp 1 PTD.pdf", "2025-3 Totals PTD.pdf") for n in EARS_24]

PUBLIC = [
    {"name": "Export Layout File Explanation", "files": [
        f("Export Layouts", LARGE + "Website_Legacy8.0.33-AppraisalExportLayout_06182026.zip", "layout",
          "Field-by-field layout of every .TXT in the appraisal exports.",
          ["Legacy8.0.33-AppraisalExportLayout.xlsx", "Legacy8.0.33-AppraisalExportLayout.pdf"])]},
    {"name": "Other Exports", "files": [
        f(CERT["label"], CERT["url"], "used", "The certified roll, exported July 18.", inside(CERT["local"]), "cert"),
        f("2026 Certified Special Export (JSON) (July)", LARGE + "2026%20Certified%20JSON%20SUPP%200%2007182026.zip", "used",
          "One JSON object per property. Each nested list in it is its own table on this page.",
          ["Travis-protaxExport-20260719.json"], "json-cert"),
        f(SUPP["label"], SUPP["url"], "used", "Supplement 3, exported October 6. " + SUPP["note"], inside(SUPP["local"]), "supp"),
        f("2026 Supplemental Special Export (JSON)", LARGE + "2026%20Special%20export%20Supp%204%2011062026.zip", "used",
          "Profiled from our earlier download of this export (Oct 6). The website link now points to a newer upload, Supp 4 of Nov 6, which is not on this page.",
          ["Travis-protaxExport-20261006.json"], "json-oct"),
    ]},
    {"name": "Protest Information", "files": [
        f("Agent Formal Hearing Check In Instructions", UP + "Agent-ARB-Hearing-Instructions.pdf"),
        f("Agent Portal Tutorial", UP + "Agent-Portal-Tutorial-Updated-1.pdf"),
        f("TCAD Updates for Tax Agents 2026 Presentation", UP + "Agent-Meeting_2026.pdf"),
        f("ARB Agent Policy", UP + "Revised-Agent-Policy-April-16-2025-1.pdf"),
        f("2026 ARB Letter to Agents", UP + "2026-TARB-Agent-Letter.pdf"),
        f("Single Family Residence Class and Conditions Guidelines", UP + "Single-Family-Construction.pdf"),
    ]},
    {"name": "Certified Totals Reports", "files": [
        f("2026 Certified Totals Report", UP + "totals_2026_AsOfRollCorr_0_RunID_6885_20260718_171007.pdf"),
        f("2025 Certified Totals Report", UP + "totals_2025_AsOfRollCorr_15_RunID_6881_20260717_195104.pdf"),
        f("2024 Certified Totals Report", UP + "totals_2024_AsOfRollCorr_29_RunID_6880_20260717_192846.pdf"),
        f("2023 Certified Totals Report", UP + "totals_2023_AsOfRollCorr_42_RunID_6879_20260717_191041.pdf"),
        f("2022 Certified Totals Report", UP + "totals_2022_AsOfRollCorr_53_RunID_6878_20260717_184951.pdf"),
    ]},
    {"name": "Electronic Appraisal Roll Submission (EARS) to Comptroller", "files": [
        f("Electronic Records Submission Manual", UP + "96-1051-Electronic-Appraisal-Roll-Submission-Manual.pdf"),
        f("2026 EARS Submission", LARGE + "227EARS082626.zip", "used", EARS_NOTE + EARS_USED, EARS_26, "ears-2026"),
        f("2025 EARS Submission", LARGE + "227EARS090425.zip", "used", EARS_NOTE + EARS_USED, EARS_25, "ears-2025"),
        f("2024 EARS Submission", LARGE + "227EARS082824%20%282%29.zip", "used", EARS_NOTE + EARS_USED, EARS_24, "ears-2024"),
        f("2023 EARS Submission", LARGE + "227EARS082923%20%282%29.zip", "used", EARS_NOTE + EARS_USED, EARS_23, "ears-2023"),
        f("2022 EARS Submission", LARGE + "227EARS092822%20%282%29.zip", "used", EARS_NOTE + EARS_USED, EARS_22, "ears-2022"),
    ]},
    {"name": "Property Reports", "files": [
        f("Subdivision and Condominium Report 2026", UP + "2026-NewSubdivisionListReport.pdf"),
        f("AG Activities Report 2026", UP + "ag_activities_2026.csv", "used", None, None, "rpt-ag"),
        f("Land Comment Report 2026", UP + "land_comments_2026.csv", "used", None, None, "rpt-land"),
        f("Improvement Details Report 2026", LARGE + "improvement_detail_2026.zip", "used",
          "Four CSVs with the same columns, shown as one table.",
          [f"improvement_detail_2026_{i}.csv" for i in range(1, 5)], "rpt-impdet"),
        f("Waterfront Effective Front Foot 2026", UP + "waterfront_effective_front_foot_report_2026.csv", "used",
          None, None, "rpt-water"),
    ]},
]


def docs(*rows):
    return [f(name, UP + file) for name, file in rows]


APPRAISAL = [
    {"name": "Reappraisal Plans", "files": docs(
        ("2027/2028 Proposed Reappraisal Plan Summary", "2027-2028-Reappraisal-Plan-Summary_Adopted.pdf"),
        ("2027/2028 Reappraisal Plan", "2027-2028-Reappraisal-Plan_Adopted-20260903-1.pdf"),
        ("2025/2026 Reappraisal Plan", "2025-2026-Reappraisal-Plan.pdf"),
        ("2025/2026 Reappraisal Plan Summary", "2025-2026-Reappraisal-Plan-Summary.pdf"),
        ("2023/2024 Reappraisal Plan", "2023-2024-Reappraisal-Plan_20220824.pdf"),
        ("2023/2024 Reappraisal Plan Summary", "2023-2024-Reappraisal-Plan-Summary_20220824.pdf"),
        ("2021/2022 Reappraisal Plan", "2021_2022-Reappraisal-Plan.pdf"),
        ("2019/2020 Reappraisal Plan", "8b_Reappraisal-Plan_20180808.pdf"))},
    {"name": "Annual Reports", "files": docs(
        ("2025 Annual Report", "2025-Annual-Report.pdf"), ("2024 Annual Report", "2024-Annual-Report.pdf"),
        ("2023 Annual Report", "2023-Annual-Report.pdf"), ("2022 Annual Report", "2022-Annual-Report_20230414.pdf"),
        ("2021 Annual Report", "2021-Annual-Report.pdf"))},
    {"name": "Mass Appraisal Reports", "files": docs(
        ("2026 Mass Appraisal Report", "2026_Mass-Appraisal-Report.pdf"), ("2025 Mass Appraisal Report", "2025_Mass-Appraisal-Report.pdf"),
        ("2024 Mass Appraisal Report", "2024_Mass-Appraisal-Report20240424.pdf"), ("2023 Mass Appraisal Report", "2023_Mass-Appraisal-Report_20230414.pdf"),
        ("2022 Mass Appraisal Report", "2022_Mass-Appraisal-Report_20220421.pdf"))},
    {"name": "Utility Usage Reports", "files": docs(
        ("SEC. 2265.001 Energy Usage Report – 2025", "Utility-Usage-Report-2025-1.pdf"),
        ("SEC. 2265.001 Energy Usage Report – 2024", "HB-3693-Utility-Usage-Report-2024.pdf"),
        ("SEC. 2265.001 Energy Usage Report – 2023", "HB-3693-Utility-Usage-Report-2023.pdf"),
        ("SEC. 2265.001 Energy Usage Report – 2022", "HB-3693-Utility-Usage-Report-2022.pdf"),
        ("SEC. 2265.001 Energy Usage Report – 2021", "HB-3693-Utility-Usage-Report-2021.pdf"))},
]
FINANCIAL = [
    {"name": "Adopted Budgets", "files": docs(
        ("2027 Adopted Budget", "FY-2027-Adopted-Budget.pdf"), ("2026 Adopted Budget", "FY-2026-Adopted-Budget.pdf"),
        ("2025 Adopted Budget", "FY-2025-Adopted-Budget.pdf"), ("2024 Adopted Budget", "FY-2024-Proposed-Budget-1.pdf"),
        ("2023 Adopted Budget", "FY-2023-Adopted-Budget.pdf"), ("2022 Adopted Budget", "FY-2022-Adopted-Budget.pdf"))},
    {"name": "Popular Annual Financial Reports", "files": docs(
        ("2025 Popular Annual Financial Report", "FY-2025-Popular-Annual-Financial-Report-1.pdf"),
        ("2024 Popular Annual Financial Report", "FY-2024-Popular-Annual-Financial-Report.pdf"),
        ("2023 Popular Annual Financial Report", "FY-2023-Popular-Annual-Financial-Report.pdf"),
        ("2022 Popular Annual Financial Report", "FY-2022-Popular-Annual-Financial-Report.pdf"),
        ("2021 Popular Annual Financial Report", "FY-2021-Popular-Annual-Financial-Report.pdf"))},
    {"name": "Annual Comprehensive Financial Reports", "files": docs(
        ("2025 Annual Comprehensive Financial Report", "2025-ACFR_Final.pdf"),
        ("2024 Annual Comprehensive Financial Report", "2024-ACFR_FINAL-1.pdf"),
        ("2023 Annual Comprehensive Financial Report", "2023-Annual-Comprehensive-Financial-Report_FINAL-1.pdf"),
        ("2022 Annual Comprehensive Financial Report", "2022-Annual-Comprehensive-Financial-Report.pdf"),
        ("2021 Annual Comprehensive Financial Report", "2021-Annual-Comprehensive-Financial-Report-ACFR.pdf"))},
    {"name": "Open Bid Requests / Requests for Proposals", "files": docs(
        ("RFQ 2026-01 Professional Audit Services (Revised 10.22.2026)", "RFQ-2026-01-Professional-Audit-Services-Revised-10.22.2026.pdf"),
        ("RFQ 2026-01 – Addendum No. 1 (10.22.2026)", "RFQ-2026-01-Addendum-No.-1-10.22.2026.pdf"),
        ("RFQ 2026-01 – Addendum No. 2", "RFQ-2026-01-Addendum-No.-2-QA-11.12.2026.pdf"))},
]
SECTIONS = [("Publicly Available Data", PUBLIC), ("Appraisal Reports", APPRAISAL), ("Financial Reports", FINANCIAL)]
# one line per group, shown when someone opens a document on the page
GROUP_DESC = {
    "Export Layout File Explanation": "The field-by-field layout of every file in the PACS appraisal exports: positions, lengths and meanings.",
    "Other Exports": "The bulk data exports: the certified and supplemental appraisal roll (fixed-width .TXT files) and the JSON special exports.",
    "Protest Information": "Guides and policies for tax agents: hearing check-in, the agent portal, ARB policy and letters, and residential class guidelines.",
    "Certified Totals Reports": "Roll totals by taxing unit as certified each July: market, exempt and taxable values. Useful to check our totals against the CAD's.",
    "Electronic Appraisal Roll Submission (EARS) to Comptroller": "The appraisal roll the CAD sends the Comptroller each August, with totals PDFs; the data files are profiled on this page.",
    "Property Reports": "Property-level reports: new subdivisions and condos, ag activity, land comments, improvement details and waterfront front footage.",
    "Reappraisal Plans": "The CAD's two-year plan for which areas and property types it reappraises, and how.",
    "Annual Reports": "The CAD's yearly summary of the appraisal season: values, protests, staffing and performance.",
    "Mass Appraisal Reports": "How the CAD values property: models, schedules and methods by property type, under USPAP Standard 6.",
    "Utility Usage Reports": "The CAD's own energy and water use, a report state law requires.",
    "Adopted Budgets": "The CAD's operating budget for each fiscal year.",
    "Popular Annual Financial Reports": "A short, plain-language version of the CAD's annual financial report.",
    "Annual Comprehensive Financial Reports": "The CAD's audited annual financial statements.",
    "Open Bid Requests / Requests for Proposals": "Open requests for bids and proposals from the CAD, with their addenda.",
}


def add_drive(groups):
    """Attach our Google Drive copy of each file, matched by file name (a trailing -1 on either side is ignored)."""
    drive = json.loads((HERE / "drive_files.json").read_text())
    norm = lambda n: re.sub(r"-1(\.[a-z]+)$", r"\1", n.lower())
    by_name = {norm(n): i for n, i in drive["files"].items()}
    for g in groups:
        if g["name"] in drive["folders"]:
            g["drive"] = "https://drive.google.com/drive/folders/" + drive["folders"][g["name"]]
        for fl in g["files"]:
            i = by_name.get(norm(fl["url"].rsplit("/", 1)[1]))
            if i: fl["drive"] = f"https://drive.google.com/file/d/{i}/view"
    return {"label": drive["source"], "url": "https://drive.google.com/drive/folders/" + drive["folders"]["_root"], "checked": drive["checked"]}


EARS_RAW = {"2022": ("092822", None), "2023": ("083023", None), "2024": ("082824", "227_50_897_082924.csv"), "2025": ("090425", "227_50_897_090425.xlsx"),
            "2026": ("082626", "227_50_897_082626_Revised.xlsx")}
EARS_APX = {"ajr": ("AJR", "Appendix 1"), "aud": ("AUD", "Appendix 3"), "tu2": ("TU2", "Appendix 5")}
JSON_FILE = {"jc": ("json-cert", "Travis-protaxExport-20260719.json"), "jo": ("json-oct", "Travis-protaxExport-20261006.json")}


def table_of(key, d):
    """Where one dataset on the page comes from: the download, the raw file inside it, and what documents it."""
    pre, _, short = key.partition("-")
    if pre in ("c26", "s26"):
        etl = (TRAVIS / "etl" / "travis_appraisal_export_etl.py").read_text()
        record_to_txt = {rec: sh + ".TXT" for sh, rec in re.findall(r'"([A-Z_0-9]+)": "([A-Z_0-9]+)"', etl.split("}")[0])}
        raw = record_to_txt[re.search(r"_\d{4}_([A-Z_0-9]+)\.csv\.gz$", d["path"]).group(1)]
        n, title, long = LAYOUT[raw]
        return {"download": "cert" if pre == "c26" else "supp", "raw": raw, "layout": f"File #{n} · {title} ({long})"}
    if pre.startswith("ears"):
        year = "20" + pre[4:]
        dt, tax = EARS_RAW[year]
        if short == "897":
            return {"download": f"ears-{year}", "raw": tax, "layout": "Form 50-897 tax office file, sent with the EARS submission"}
        kind, apx = EARS_APX[short]
        return {"download": f"ears-{year}", "raw": f"227EARS{dt}.csv · {kind} rows",
                "layout": f"{kind} record layout, EARS manual 96-1051 {apx}"}
    if pre == "rpt":
        raw = {"impdet": "improvement_detail_2026_1-4.csv"}.get(short, d["path"].rsplit("/", 1)[-1])
        return {"download": key, "raw": raw, "layout": "TCAD property report (CSV, header row)"}
    if pre in JSON_FILE:
        dl, fn = JSON_FILE[pre]
        path = d["json_path"]
        return {"download": dl, "raw": path if path == "property" else path.replace(".", "[].") + "[]",
                "layout": f"JSON {'top-level fields of each property' if path == 'property' else 'list ' + path.replace('.', ' › ')} in {fn}"}
    raise SystemExit(f"no source rule for {key}")


def tables():
    manifest = json.loads((HERE / "manifest.json").read_text())
    out = {}
    for key, d in manifest["datasets"].items():
        if d.get("placeholder"):
            continue
        out[key] = {**table_of(key, d), "converted": d["path"]}
    return out


if __name__ == "__main__":
    groups = [dict(g, section=sec, desc=GROUP_DESC.get(g["name"], "")) for sec, gs in SECTIONS for g in gs]
    m = {"page": PAGE, "downloads": {"cert": CERT, "supp": SUPP}, "groups": groups, "drive": add_drive(groups), "tables": tables()}
    # the published page names files only by their TCAD download and raw file: never our local folders
    for t in m["tables"].values():
        t.pop("converted", None)
    m["downloads"] = {k: {x: v for x, v in d.items() if x != "local"} for k, d in m["downloads"].items()}
    (HERE / "source_map.json").write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print(len(m["tables"]), "tables mapped")
