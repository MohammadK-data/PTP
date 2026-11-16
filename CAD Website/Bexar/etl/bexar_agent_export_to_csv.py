"""Bexar: convert BCAD's Agent Export .txt files (pipe-delimited, no header) to CSV with header rows.

Column names come from "Data/Agent Export File Layout for Agents.pdf" (Files #1-#21).

Usage:  python3 bexar_agent_export_to_csv.py <folder with FID_*.txt> <output folder>

Cleaning (raw files are CRLF records, cp1252 text):
  - NUL bytes (BCAD writes them for empty fields) are removed.
  - Records broken by a line break inside a text field (seen in ImprovementExport) are joined back together.
  - Records with pipes typed inside a free-text field get those extra pieces merged back into that field.
    The field is chosen so the numeric columns after it still parse as numbers.
  - Line breaks inside a field become a space; leading/trailing spaces are trimmed (IncomeExport is space-padded).
  - FID_BPPRealLinkExport has 2 columns, not the 3 in the layout (Personal_area is not in the file).
"""
import csv
import re
import sys
from pathlib import Path

N, C = "n", "c"  # numeric / char

LAYOUT = {
    "FID_ARBExport": [
        ("Property ID", N), ("Geo ID", C), ("Year", N), ("Case ID", N), ("Current Appraiser", C), ("Neighborhood", C),
        ("Owner Name", C), ("State Code", C), ("Property Type", C), ("Legal Description", C), ("Entities", C),
        ("Exemptions", C), ("Situs", C), ("Agent Name", C), ("Protest Type", C), ("Protest Status", C),
        ("Reason Codes", C), ("Taxpayer Comments", C), ("Protest By Type", C), ("Protest By Name", C),
        ("Taxpayer Affidavit Received Date", C), ("Affidavit Testimony By", C), ("Testimony Received", C),
        ("Docket ID", N), ("Docket Start Date/Time", C), ("Docket End Date/Time", C), ("Hearing Rescheduled", C),
        ("Assigned Panel", C), ("Arrived Date/Time", C), ("1st Motion Decision", C), ("1st Motion Decision Date", C),
        ("2nd Motion Decision", C), ("2nd Motion Decision Date", C), ("Appraiser Meeting Appraiser", C),
        ("Appraiser Meeting Date/Time", C), ("Appraiser Meeting Arrived Date/Time", C),
        ("Appraiser Meeting Appraiser Comments", C), ("Appraiser Meeting Taxpayer Comments", C),
        ("Hearing Start Date/Time", C), ("Hearing End Date/Time", C), ("Hearing Appraiser", C),
        ("Recording Appraiser", C), ("Panel Members", C), ("District Comments", C), ("Other Motion", C),
        ("First Motion", C), ("Second Motion", C),
        ("Begin Land HS Value", N), ("Begin Land NHS Value", N), ("Begin Improvement HS Value", N),
        ("Begin Improvement NHS Value", N), ("Begin Ag Use Value", N), ("Begin Ag Market", N), ("Begin Timber Use", N),
        ("Begin Timber Market", N), ("Begin Market", N), ("Begin Appraised Value", N), ("Begin Ten Percent Cap", N),
        ("Begin Assessed Value", N), ("Begin Rendered Value", N), ("Begin Exemptions", C), ("Begin Entities", C),
        ("Final Land HS Value", N), ("Final Land NHS Value", N), ("Final Improvement HS Value", N),
        ("Final Improvement NHS Value", N), ("Final Ag Use Value", N), ("Final Ag Market", N), ("Final Timber Use", N),
        ("Final Timber Market", N), ("Final Market", N), ("Final Appraised Value", N), ("Final Ten Percent Cap", N),
        ("Final Assessed Value", N), ("Final Rendered Value", N), ("Final Exemptions", C), ("Final Entities", C),
    ],
    "FID_ARBLetterHistory": [("Property ID", N), ("Year", N), ("Case ID", N), ("Letter Name", C), ("Letter Date/Time", C)],
    "FID_BuildingPermitExport": [
        ("Permit ID", N), ("Property Type", C), ("Permit #", C), ("Issuer", C), ("Issued To", C),
        ("Permit Status Code", C), ("Issue Date", C), ("Issue Limit Date", C), ("Issuer Phone", C), ("Issuer Xref", C),
        ("Res / Com", C), ("Number", C), ("Prefix", C), ("Street", C), ("Suffix", C), ("Unit Type", C),
        ("Unit Number", C), ("Subdivision", C), ("Plat", C), ("Block", C), ("Lot", C), ("City", C),
        ("Building Inspection", C), ("Electrical Inspection", C), ("Mechanical Inspection", C),
        ("Plumbing Inspection", C), ("Permit Type Code", C), ("Permit Sub Type Code", C), ("Number of Floors", N),
        ("Number of Units", N), ("CAD Permit Status", C), ("Dim 1", C), ("Builder", C), ("Value", N), ("Dim 2", C),
        ("Builder's Phone", C), ("Date Worked", C), ("Dim 3", C), ("Appraiser", C), ("Date Completed", C),
        ("Area", N), ("Land Use", C), ("Percent Complete Override", C), ("Percent Complete", N), ("Comments", C),
        ("Permit Source", C), ("Last Changed", C), ("Active", C),
    ],
    "FID_BuildingPermitPropertyExport": [("Permit ID", N), ("Property ID", N)],
    "FID_CommentsExport": [("Property ID", N), ("Comment Type", C), ("Comment", C)],
    "FID_EventsExport": [("Property ID", N), ("Event Year", N), ("Event Date", C), ("Event Type", C), ("Event Description", C)],
    "FID_ImprovementExport": [
        ("Property ID", N), ("Year", N), ("Supplement #", N), ("Improvement ID", N), ("Improvement Type Code", C),
        ("State Code", C), ("Homesite Flag", C), ("Effective Year Built", N), ("Description", C),
        ("# of Improvements", N), ("Comment", C), ("# of Stories", C), ("Base Depreciation %", N),
        ("Base Depr. Comment", C), ("Physical %", N), ("Physical Comment", C), ("Functional %", N),
        ("Functional Comment", C), ("Economic %", N), ("Economic Comment", C), ("Percent Complete", N),
        ("Percent Complete Comment", C), ("Total Detail Value", N), ("Improvement Value", N),
        ("Improvement Value Source", C), ("Entity and Percentages", C), ("Adjustments and Percentages", C),
        ("Detail ID", N), ("Detail Number of Units", N), ("Detail Number of Stories", N), ("Detail Class Code", C),
        ("Detail Method Code", C), ("Detail Sub Class Code", C), ("Detail Unit Price", N), ("Detail Add Factor", N),
        ("Detail Area", N), ("Detail Base Depreciation %", N), ("Detail Physical %", N), ("Detail Physical Comment", C),
        ("Detail Functional %", N), ("Detail Functional Comment", C), ("Detail Economic %", N),
        ("Detail Economic Comment", C), ("Detail Size Adjustment %", N), ("Detail Percent Complete", N),
        ("Detail % Complete Comment", C), ("Detail Value", N), ("Detail Value Source", C),
        ("Detail Use Unit Price for % Base Flag", C), ("Detail Stories Multiplier Flag", C),
        ("Detail Calculated Value", N), ("Detail Condition Code", C), ("Detail Actual Year Built", N),
        ("Detail Effective Year Built", N), ("Detail Age", N), ("Detail Adjustments and Percentages", C),
    ],
    "FID_ImprovementFeaturesExport": [
        ("Property ID", N), ("Year", N), ("Sup Num", N), ("Improvement ID", N), ("Improvement Detail ID", N),
        ("Feature Type", C), ("Feature Description", C),
    ],
    "FID_LandExport": [
        ("Property ID", N), ("Year", N), ("Supplement #", N), ("Land ID", N), ("State Code", C), ("Land Type Code", C),
        ("Late Ag Apply Flag", C), ("Homesite Flag", C), ("Comment", C), ("Market Pricing Method", C),
        ("Market Pricing Table", C), ("Market Unit Price", N), ("Width Front", N), ("Width Back", N),
        ("Depth Right", N), ("Depth Left", N), ("Size in Sq Ft", N), ("Size in Acres", N), ("Legal Acreage", N),
        ("Number of Lots", N), ("Effective Size Acres", N), ("Size Useable Acres", N), ("Size Useable Sqft", N),
        ("Ag Pricing Method", C), ("Ag Pricing Table", C), ("Ag Unit Price", N), ("Market Value", N),
        ("Calculated Market Value", N), ("Ag Value", N), ("Ag Apply Flag", C), ("Ag Use Code", C), ("Ag Loss", N),
        ("Entities and Percentages", C), ("Adjustments and Percentages", C),
    ],
    "FID_PropDataExport": [
        ("Property ID", N), ("Year", N), ("Year Built", N), ("Living Area", N), ("Land Sqft", N), ("Land Acres", N),
        ("Region", C), ("Neighborhood", C), ("Map ID", C), ("Land # of Lots", N), ("Effective Year Built", N),
        ("Number of Improvements", N), ("Last Appraiser", C), ("Next Appraiser", C), ("Land Appraiser", C),
        ("Value Appraiser", C), ("Neighborhood Appraiser", C), ("Subdivision Appraiser", C),
        ("Category Appraiser", C), ("Next Appraisal Reason", C), ("Property Comment", C), ("Property Remarks", C),
        ("Valuation Method Code", C), ("Zoning", C),
    ],
    "FID_ProtesterExport": [
        ("Property ID", N), ("Year", N), ("Case ID", N), ("Protest by Name", C), ("Protest by Type", C),
        ("Primary Protester", C),
    ],
    "FID_SharedPropExport": [("PACS Property ID", N), ("Year", N), ("Shared CAD Code", C), ("Shared CAD Prop ID", C)],
    "FID_IncomeExport": [
        ("Property ID", N), ("Year", N), ("NBHD Economic Area", C), ("Property Type", C), ("Class", C),
        ("Level Code", C), ("Gross Building Area", C), ("Net Rentable Area", C), ("Property Name", C), ("Comment", C),
    ],
    "FID_SalesExport": [
        ("Property ID", N), ("Sale ID", N), ("Buyer Name", C), ("Seller Name", C), ("Deed Type", C),
        ("Deed Volume", C), ("Deed Date", C), ("Deed Page", C), ("Deed Number", C), ("Recorded Date", C),
        ("Consideration", C), ("Comment", C), ("Buyer ID", N), ("Seller ID", N), ("Sale Price", N), ("Sale Date", C),
        ("Adjust Code", C), ("Adjust Percentage", N), ("Adjust Amount", N), ("Adjust Reason", C),
        ("Confirmed By", C), ("Confirmed Date", C), ("Confirmed Source", C), ("Confirmed Sale Price", N),
        ("Buyer Confidence Level", C), ("Seller Confidence Level", C), ("Confirm Comment", C),
        ("Financing Code", C), ("Amount Financed", N), ("Interest Rate", N), ("Finance Years", N),
        ("2nd Amount Financed", N), ("2nd Interest Rate", N), ("2nd Finance Years", N), ("Amount Down", N),
        ("Finance Comment", C), ("Sale Type", C), ("Sale Ratio Type", C), ("Sale State Code", C),
        ("School Entity", C), ("City Entity", C), ("Sale Class", C), ("Sale Sub Class", C), ("Sale Comment", C),
        ("Sale Realtor", C), ("Sale Year Built", N), ("Sale Imprv Unit Price", N), ("Sale Living Area", N),
        ("Sale Land Acres", N), ("Sale Land Sqft", N), ("Sale Land Front Foot", N), ("Sale Land Depth", N),
        ("Sale Land Unit Price", N), ("Sale Land Type Code", C),
    ],
    "FID_SalesImprovementExport": [
        ("Property ID", N), ("Improvement ID", N), ("Sale ID", N), ("Year", N), ("Improvement Type", C),
        ("State Code", C), ("Homesite Flag", C), ("Improvement Value", N),
    ],
    "FID_SalesLandExport": [
        ("Property ID", N), ("Land ID", N), ("Sale ID", N), ("Year", N), ("Land Type", C), ("State Code", C),
        ("Homesite Flag", C), ("Size Acres", N), ("Market Value", N), ("Ag Value", N), ("Ag Loss", N), ("Ag Table", C),
    ],
    "FID_BPPRealLinkExport": [("Personal_prop_id", N), ("Linked_real_prop_id", N)],
    "FID_BPPExport": [
        ("Prop_id", N), ("Prop_val_yr", N), ("Sup_num", N), ("Seg_id", N), ("Active_flag", C), ("Segment_type", C),
        ("Segment_value", N), ("Segment_quality", C), ("Segment_density", C), ("Segment_area", N),
        ("Penalty_amount", N), ("Penalty_amount_override", N), ("Penalty_amount_dt", C),
    ],
    "FID_ARBInquiryExport": [
        ("Prop_id", N), ("Geo_id", C), ("Prop_val_yr", N), ("Case_id", N), ("Appraiser_nm", C), ("Hood_cd", C),
        ("File_as_name", C), ("State_cd", C), ("Prop_type_cd", C), ("Legal_desc", C), ("Entities", C),
        ("Exemptions", C), ("Situs", C), ("Agent_name", C), ("Inq_type", C), ("Inq_status", C), ("Inq_nature", C),
        ("Inq_assigned_reason_cd", C), ("Inq_taxpayer_comments", C), ("Inq_appraiser_comments", C),
        ("Inq_by_type", C), ("Inq_appraisal_staff", C), ("Appraiser_meeting_date_time", C),
        ("Appraiser_meeting_appraiser_comments", C), ("Appraiser_meeting_Taxpayer_Comments", C),
        ("Inq_operator_Comments", C),
        ("Begin_land_hstd_val", N), ("Begin_land_non_hstd_val", N), ("Begin_imprv_hstd_val", N),
        ("Begin_imprv_non_hstd_val", N), ("Begin_ag_use_val", N), ("Begin_ag_market", N), ("Begin_timber_use", N),
        ("Begin_timber_market", N), ("Begin_market", N), ("Begin_appraised_val", N), ("Begin_ten_percent_cap", N),
        ("Begin_assessed_val", N), ("Begin_rendered_val", N), ("Begin_exemptions", C), ("Begin_entities", C),
        ("Final_land_hstd_val", N), ("Final_land_non_hstd_val", N), ("Final_imprv_hstd_val", N),
        ("Final_imprv_non_hstd_val", N), ("Final_ag_use_val", N), ("Final_ag_market", N), ("Final_timber_use", N),
        ("Final_timber_market", N), ("Final_market", N), ("Final_appraised_val", N), ("Final_ten_percent_cap", N),
        ("Final_assessed_val", N), ("Final_rendered_val", N), ("Final_exemptions", C), ("Final_entities", C),
    ],
    "FID_ARBInquiryLetterHistory": [("Prop_id", N), ("Prop_val_yr", N), ("Case_id", N), ("Letter_name", C), ("Create_dt", C)],
    "FID_ApprNoticeExport": [
        ("Prop_id", N), ("Notice_yr", N), ("An_prev_yr", N), ("Notice_num", N), ("Owner_id", N), ("Sup_num", N),
        ("Sup_yr", N), ("An_appraised_val", N), ("An_prev_appraised_val", N), ("An_prev_assessed_val", N),
        ("An_assessed_val", N), ("An_prev_market_val", N), ("An_market_val", N), ("An_imprv_hstd_val", N),
        ("An_prev_imprv_hstd_val", N), ("An_land_hstd_val", N), ("An_prev_land_hstd_val", N),
        ("An_ag_land_mkt_val", N), ("An_prev_ag_land_mkt_val", N), ("An_ag_land_use_val", N),
        ("An_prev_ag_land_use_val", N), ("An_imprv_non_hstd_val", N), ("An_prev_imprv_non_hstd_val", N),
        ("An_land_non_hstd_val", N), ("An_prev_land_non_hstd_val", N), ("An_ag_market", N),
        ("An_prev_ag_market_val", N), ("An_timber_market", N), ("An_prev_timber_market_val", N),
        ("An_timber_use", N), ("An_prev_timber_use", N), ("An_ten_percent_cap", N), ("An_prev_ten_percent_cap", N),
        ("An_pers_prop_mineral_value", N), ("An_prev_pers_prop_mineral_value", N), ("Exemption", C),
        ("Prev_exemption", C),
    ],
}

NUM = re.compile(r"^-?\d*\.?\d*$")
LONG_TEXT = re.compile(r"comment|remark|description|reason|motion|legal|name|situs|issued to|panel|desc|lot|street", re.I)


def decode(b):
    try:
        return b.decode("cp1252")
    except UnicodeDecodeError:
        return b.decode("latin-1")


def valid(fields, types):
    return all(t != N or NUM.match(v.strip()) for v, t in zip(fields, types))


def fix_extra(fields, cols, types):
    """Merge surplus fields (pipes typed inside text) back into one text column."""
    extra = len(fields) - len(cols)
    cands = [i for i, (n, t) in enumerate(cols) if t == C and LONG_TEXT.search(n)] + \
            [i for i, (n, t) in enumerate(cols) if t == C and not LONG_TEXT.search(n)]
    for i in cands:
        trial = fields[:i] + ["|".join(fields[i:i + extra + 1])] + fields[i + extra + 1:]
        if valid(trial, types):
            return trial, True
    i = cands[0]
    return fields[:i] + ["|".join(fields[i:i + extra + 1])] + fields[i + extra + 1:], False


def iter_records(fh):
    """Yield CRLF-terminated records (bare LF/CR inside a record stays in it), NULs removed."""
    buf = b""
    for line in fh:
        buf += line
        if buf.endswith(b"\r\n"):
            yield buf[:-2].replace(b"\x00", b"")
            buf = b""
    if buf.strip(b"\r\n\x00"):
        yield buf.rstrip(b"\r\n").replace(b"\x00", b"")


def convert(src, dst):
    cols = LAYOUT[src.stem]
    names, types = [c[0] for c in cols], [c[1] for c in cols]
    n = len(cols)
    stats = dict(rows=0, joined_breaks=0, pipe_fixed=0, pipe_guess=0, short=0)
    with open(src, "rb") as fin, open(dst, "w", newline="", encoding="utf-8") as out:
        w = csv.writer(out)
        w.writerow(names)
        recs = iter_records(fin)
        pending = next(recs, None)
        while pending is not None:
            rec = pending
            pending = next(recs, None)
            # a line break inside a field split this record: glue following pieces on
            while (rec.count(b"|") + 1 < n and pending is not None
                   and rec.count(b"|") + pending.count(b"|") + 1 <= n):
                rec += b" " + pending
                pending = next(recs, None)
                stats["joined_breaks"] += 1
            fields = [re.sub(r"[\r\n]+", " ", f).strip() for f in decode(rec).split("|")]
            if len(fields) > n:
                fields, ok = fix_extra(fields, cols, types)
                stats["pipe_fixed" if ok else "pipe_guess"] += 1
            elif len(fields) < n:
                stats["short"] += 1
                fields += [""] * (n - len(fields))
            w.writerow(fields)
            stats["rows"] += 1
    return stats


def job(args):
    f, out_dir = args
    return f.stem, convert(f, out_dir / (f.stem + ".csv"))


if __name__ == "__main__":
    from concurrent.futures import ProcessPoolExecutor, as_completed
    import os

    src_dir, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(src_dir.glob("FID_*.txt"), key=lambda p: -p.stat().st_size)  # biggest first
    with ProcessPoolExecutor(max_workers=min(len(files), os.cpu_count() or 4)) as ex:
        futs = [ex.submit(job, (f, out_dir)) for f in files]
        for fu in as_completed(futs):
            stem, s = fu.result()
            print(f"{stem:36s} " + " ".join(f"{k}={v:,}" for k, v in s.items()), flush=True)
