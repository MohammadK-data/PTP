"""Add Bexar column descriptions to manifest.json (run after make_manifest.py).
PACS columns not already described (copied from Travis) take BCAD's own text from the 8.0.34 layout workbook.
Property Summary columns use BCAD's 'Export Property Summary Layout' wording. Agent Export columns are written
in plain language from the 'Agent Export File Layout for Agents' PDF, the values, and Texas property-tax context."""
import json
m = json.load(open("manifest.json")); BS = m["descriptions_by_set"]
WB = json.load(open("../etl/pacs_8034_descriptions.json"))
P = json.load(open("profile.json"))
REC = {"info": "APPRAISAL_INFO", "entinfo": "APPRAISAL_ENTITY_INFO", "enttot": "APPRAISAL_ENTITY_TOTALS"}
D = m["descriptions"]
for k, v in P.items():
    pre, _, short = k.partition("-")
    if pre in ("p26", "s26") and short in REC:
        for c in v["columns"]:
            n = c["name"]
            if not (BS.get(f"{k}:{n}") or D.get(n)):
                t = WB.get(f"{REC[short]}:{n}")
                if t: BS[f"{k}:{n}"] = t.rstrip(".") + " (BCAD layout 8.0.34)."

PS = {
 "Prop_id": "BCAD property id; the same number as PACS <code>prop_id</code> without the leading zeros.",
 "Prop_yr": "Tax year of the values.",
 "Geo_id": "BCAD geographic id (map / parcel number, e.g. 00002-000-0013). Published wrapped in an extra pair of double quotes.",
 "Owner_id": "BCAD owner id.", "Owner_name": "Owner name.",
 "Addr_line1": "Owner mailing address, line 1.", "Addr_line2": "Owner mailing address, line 2.", "Addr_line3": "Owner mailing address, line 3.",
 "Addr_city": "Owner mailing city.", "Addr_state": "Owner mailing state.", "Country_cd": "Owner mailing country code.",
 "Zip": "Owner mailing ZIP code.", "Zip+4": "Owner mailing ZIP+4 extension.",
 "Yr_blt": "Year built (main improvement).", "Sq_ft": "Building square feet.", "Land_acres": "Land size in acres.",
 "Imprv_hstd_val": "Improvement homestead value.", "Land_hstd_val": "Land homestead value.",
 "State_cd": "Texas Comptroller state (property category) code, e.g. A1 single-family, F1 commercial.",
 "Market_val": "Market value. BCAD's layout notes that 'null' values mean the market value is not set yet.",
 "School": "School district (entity) name.", "City": "City (entity) name.",
 "Exemptions": "Exemptions on the property, each with the year it started (HS-2014, OV65-2021).",
 "Situs_num": "Property (situs) street number.", "Situs_street_prefix": "Situs street prefix (N, S, E, W).",
 "Situs_street": "Situs street name.", "Situs_street_sufix": "Situs street suffix (sic: sufix).", "Situs_unit": "Situs suite / unit number.",
 "Dba_name": "Doing-business-as name.",
 "Imprv_Type": "List of improvement type codes on the property, separated by two spaces.",
 "Ext_Wall": "List of exterior wall types.", "Roof": "List of roof types.", "Foundation": "List of foundation types.",
 "Bedrooms": "List of bedroom counts, one per improvement.", "Whole_Bath": "List of full bathroom counts.", "Half_Bath": "List of half bathroom counts.",
 "Imprv_non_hstd_val": "Improvement non-homestead value.", "Land_non_hstd_val": "Land non-homestead value.",
 "AG_Use_val": "Agricultural (productivity) use value.", "AG_Market": "Market value of land under ag use.",
 "Property_use_cd": "BCAD property use code (see 2026 Metadata - Property Use Codes.xlsx).",
 "Neighboorhood_Code": "Neighborhood code (sic: Neighboorhood); see 2026 NBHD Codes.xlsx.",
 "Legal_desc": "Legal description.", "Situs_Zip": "Situs ZIP code.",
 "Num_Units": "Number of improvements or units.", "Last_Deed_Date": "Date of the last deed on record.",
 "Agent_iD": "Id of the tax agent on the property.", "Agent_name": "Tax agent name.",
 "Agent_Addr_L1": "Agent mailing address, line 1.", "Agent_Addr_L2": "Agent mailing address, line 2.", "Agent_Addr_L3": "Agent mailing address, line 3.",
 "Agent_Addr_city": "Agent mailing city.", "Agent_Addr_state": "Agent mailing state.", "Agent_CO_code": "Agent mailing country code.",
 "Agent_Zip": "Agent mailing ZIP.", "Agent_Zip+4": "Agent mailing ZIP+4.",
 "Prior_Imp_HS_val": "Prior-year improvement homestead value.", "Prior_ Imp_non_HS_val": "Prior-year improvement non-homestead value (the header has a space after Prior_).",
 "Prior LD_HS val": "Prior-year land homestead value.", "Prior LD non_HS_val": "Prior-year land non-homestead value.",
 "Prior AG_mkt": "Prior-year ag market value.", "Prior Mkt val": "Prior-year market value.",
 "BPP Late_Rend_penalty": "Business personal property late-rendition penalty.", "MAPSCO": "MAPSCO map grid.",
 "Sq_Ft_HVI": "Square feet of the highest-valued improvement on the property.",
 "Class": "Improvement class code (main improvement).", "SubClass": "Improvement sub-class code (main improvement).",
}
for k in ("ps26a", "ps26s"):
    for c in P[k]["columns"]:
        n = c["name"]; t = PS.get(n) or PS.get(n.lstrip("﻿"))
        if t: BS[f"{k}:{n}"] = t

V = lambda what: f"{what}"
AG = {
 "*": {"Property ID": "BCAD property id (PACS <code>prop_id</code>, no leading zeros).", "Prop_id": "BCAD property id (PACS <code>prop_id</code>, no leading zeros).",
       "Year": "Tax year of the record.", "Prop_val_yr": "Tax year of the record.", "Case ID": "Protest case number, unique within a property and year.",
       "Case_id": "Case number, unique within a property and year.", "Supplement #": "Supplement number the record belongs to (0 = original roll).",
       "Sup Num": "Supplement number the record belongs to (0 = original roll).", "Sup_num": "Supplement number (0 = original roll).",
       "Improvement ID": "Improvement (building) id within the property.", "Land ID": "Land segment id.", "Sale ID": "Sale id; joins the sale files.",
       "State Code": "Texas Comptroller state (property category) code, e.g. A1 single-family, F1 commercial.",
       "Homesite Flag": "Whether the segment is part of the homestead (Y/T = yes).", "Comment": "Free-text comment.",
       "Geo_id": "BCAD geographic id (map / parcel number).", "Geo ID": "BCAD geographic id (map / parcel number)."},
 "ag-arbletter": {"Letter Name": "Letter sent on the protest case (hearing notice, order, ...).", "Letter Date/Time": "Date and time the letter was produced."},
 "ag-inqletter": {"Letter_name": "Letter sent on the inquiry case.", "Create_dt": "Date and time the letter was produced."},
 "ag-bpp": {"Seg_id": "BPP segment id.", "Active_flag": "T when the segment is active.", "Segment_type": "BPP segment type code (inventory, furniture & fixtures, ...; see 2026 Metadata - BPP Segment Codes.xlsx).",
            "Segment_value": "Value of the segment.", "Segment_quality": "Quality code of the segment.", "Segment_density": "Density code of the segment.",
            "Segment_area": "Area of the segment.", "Penalty_amount": "Late-rendition penalty amount.", "Penalty_amount_override": "1 when the penalty amount was overridden by hand.",
            "Penalty_amount_dt": "Date the penalty was set."},
 "ag-bpplink": {"Personal_prop_id": "Business personal property account id.", "Linked_real_prop_id": "Real property id the BPP account sits on."},
 "ag-comments": {"Comment Type": "Comment category (APPR = appraiser, ...).", "Comment": "Comment text. Text the CAD wrote with line breaks is joined into one line."},
 "ag-events": {"Event Year": "Tax year of the event.", "Event Date": "Date of the event.", "Event Type": "Event type code (MUES e-file, MULAY last appraisal year, ...).", "Event Description": "What happened, as written by PACS."},
 "ag-feat": {"Improvement Detail ID": "Improvement segment (detail) id.", "Feature Type": "Feature name (Exterior Wall, Roof, Heating, Use Category ...).", "Feature Description": "Feature code or value (see Improvement attribute codes.xls)."},
 "ag-income": {"NBHD Economic Area": "Income neighborhood / economic area.", "Property Type": "Income property type code.", "Class": "Building class for the income model.",
               "Level Code": "Income level code.", "Gross Building Area": "Gross building area in sq ft.", "Net Rentable Area": "Net rentable area in sq ft.", "Property Name": "Property name on the income worksheet."},
 "ag-shared": {"PACS Property ID": "BCAD property id.", "Shared CAD Code": "Code of the other appraisal district that shares the property.", "Shared CAD Prop ID": "The property's id at the other district."},
 "ag-permitprop": {"Permit ID": "Building permit id."},
 "ag-protester": {"Protest by Name": "Name of the person or firm who filed the protest.", "Protest by Type": "Who filed: OW owner, AG agent, ...", "Primary Protester": "1 for the primary protester on the case."},
 "ag-saleimpr": {"Improvement Type": "Improvement type code at the time of sale.", "Improvement Value": "Improvement value at the time of sale."},
 "ag-saleland": {"Land Type": "Land type code at the time of sale.", "Size Acres": "Land size in acres.", "Market Value": "Land market value at the time of sale.",
                 "Ag Value": "Ag use value.", "Ag Loss": "Ag loss (rollback) amount.", "Ag Table": "Ag pricing table."},
 "ag-propdata": {"Year Built": "Year built (main improvement).", "Living Area": "Living area in sq ft.", "Land Sqft": "Land size in sq ft.", "Land Acres": "Land size in acres.",
                 "Region": "BCAD appraisal region.", "Neighborhood": "Neighborhood code.", "Map ID": "Map id.", "Land # of Lots": "Number of lots.",
                 "Effective Year Built": "Effective year built (age after renovations).", "Number of Improvements": "Count of improvements on the property.",
                 "Last Appraiser": "Appraiser who last worked the property.", "Next Appraiser": "Appraiser assigned for the next review.", "Land Appraiser": "Land appraiser.",
                 "Value Appraiser": "Appraiser responsible for the value.", "Neighborhood Appraiser": "Neighborhood appraiser.", "Subdivision Appraiser": "Subdivision appraiser.",
                 "Category Appraiser": "Category appraiser.", "Next Appraisal Reason": "Why the property is flagged for its next appraisal.",
                 "Property Comment": "Property comment (appraiser notes).", "Property Remarks": "Property remarks (field and review notes).",
                 "Valuation Method Code": "How the value was set: C cost, I income, A ARB, D distributed, S shared.", "Zoning": "Zoning code."},
 "ag-notice": {"Notice_yr": "Year of the notice.", "An_prev_yr": "Prior year the notice compares to.", "Notice_num": "Notice number for the property and year (1 = first).",
               "Owner_id": "Owner id on the notice.", "Sup_yr": "Supplement year.", "Exemption": "Exemptions on this year's notice.", "Prev_exemption": "Exemptions on the prior year."},
 "ag-land": {"Land Type Code": "Land type code (RES, CSS, ...; see 2026 Metadata - Land Type Codes.xlsx).", "Late Ag Apply Flag": "T when the ag application was late.",
             "Market Pricing Method": "Market pricing method (SQMTX square-foot matrix, AC acre, FF front foot, LOT ...).", "Market Pricing Table": "Land pricing table / schedule.",
             "Market Unit Price": "Market unit price.", "Width Front": "Front width in feet.", "Width Back": "Back width in feet.", "Depth Right": "Right depth in feet.", "Depth Left": "Left depth in feet.",
             "Size in Sq Ft": "Size in square feet.", "Size in Acres": "Size in acres.", "Legal Acreage": "Legal acreage.", "Number of Lots": "Number of lots.",
             "Effective Size Acres": "Effective size in acres.", "Size Useable Acres": "Useable acres.", "Size Useable Sqft": "Useable square feet.",
             "Ag Pricing Method": "Ag pricing method.", "Ag Pricing Table": "Ag pricing table.", "Ag Unit Price": "Ag unit price.", "Market Value": "Land market value.",
             "Calculated Market Value": "Market value the schedule calculates, before overrides.", "Ag Value": "Ag use value.", "Ag Apply Flag": "T when ag use valuation applies.",
             "Ag Use Code": "Ag use code.", "Ag Loss": "Ag loss amount.", "Entities and Percentages": "Taxing units below 100% for this segment (ENT: 50%).",
             "Adjustments and Percentages": "Land adjustments and their percentages (ADJ: 125%)."},
 "ag-impr": {"Improvement Type Code": "Improvement type: R residential, C commercial, M mobile home, ...", "Effective Year Built": "Effective year built of the improvement.",
             "Description": "Improvement description (building code).", "# of Improvements": "Number of identical improvements.", "# of Stories": "Number of stories.",
             "Base Depreciation %": "Base (age) depreciation, as percent good.", "Base Depr. Comment": "Comment on base depreciation.", "Physical %": "Physical condition percent good.",
             "Physical Comment": "Comment on physical depreciation.", "Functional %": "Functional obsolescence percent good.", "Functional Comment": "Comment on functional obsolescence.",
             "Economic %": "Economic obsolescence percent good.", "Economic Comment": "Comment on economic obsolescence.", "Percent Complete": "Percent complete (new construction).",
             "Percent Complete Comment": "Comment on percent complete.", "Total Detail Value": "Sum of the segment values.", "Improvement Value": "Improvement value.",
             "Improvement Value Source": "Where the value came from: A appraised (calculated), F flat, ...", "Entity and Percentages": "Taxing units below 100% (ENT: 50%).",
             "Adjustments and Percentages": "Improvement adjustments (ADJ: 125%).", "Detail ID": "Improvement segment (detail) id.", "Detail Number of Units": "Units in the segment.",
             "Detail Number of Stories": "Stories of the segment.", "Detail Class Code": "Construction class of the segment.", "Detail Method Code": "Segment pricing method / type (MA main area, ADD addition, ...).",
             "Detail Sub Class Code": "Construction sub-class of the segment.", "Detail Unit Price": "Unit price per sq ft.", "Detail Add Factor": "Add factor percent.",
             "Detail Area": "Segment area in sq ft.", "Detail Base Depreciation %": "Segment base depreciation (percent good).", "Detail Physical %": "Segment physical percent good.",
             "Detail Physical Comment": "Comment on segment physical depreciation.", "Detail Functional %": "Segment functional percent good.", "Detail Functional Comment": "Comment on segment functional obsolescence.",
             "Detail Economic %": "Segment economic percent good.", "Detail Economic Comment": "Comment on segment economic obsolescence.", "Detail Size Adjustment %": "Size adjustment percent.",
             "Detail Percent Complete": "Segment percent complete.", "Detail % Complete Comment": "Comment on segment percent complete.", "Detail Value": "Segment value.",
             "Detail Value Source": "Where the segment value came from (A appraised, F flat ...).", "Detail Use Unit Price for % Base Flag": "T when the unit price is used for the percent base.",
             "Detail Stories Multiplier Flag": "1 when the stories multiplier applies.", "Detail Calculated Value": "Segment value calculated by the schedule.",
             "Detail Condition Code": "Condition code (AV average, GD good, ...).", "Detail Actual Year Built": "Actual year built of the segment.",
             "Detail Effective Year Built": "Effective year built of the segment.", "Detail Age": "Segment age used for depreciation.", "Detail Adjustments and Percentages": "Segment adjustments (ADJ: 150%)."},
 "ag-permit": {"Permit ID": "Building permit id.", "Property Type": "Property type on the permit.", "Permit #": "Permit number from the issuer.", "Issuer": "Who issued the permit (CITY, county ...).",
               "Issued To": "Who the permit was issued to.", "Permit Status Code": "Issuer's permit status.", "Issue Date": "Date the permit was issued.", "Issue Limit Date": "Permit expiry date.",
               "Issuer Phone": "Issuer phone.", "Issuer Xref": "Issuer cross-reference number.", "Res / Com": "R residential or C commercial.", "Number": "Street number.",
               "Prefix": "Street prefix.", "Street": "Street name.", "Suffix": "Street suffix.", "Unit Type": "Unit type.", "Unit Number": "Unit number.", "Subdivision": "Subdivision.",
               "Plat": "Plat.", "Block": "Block.", "Lot": "Lot.", "City": "City.", "Building Inspection": "Building inspection done (T/F).", "Electrical Inspection": "Electrical inspection done (T/F).",
               "Mechanical Inspection": "Mechanical inspection done (T/F).", "Plumbing Inspection": "Plumbing inspection done (T/F).", "Permit Type Code": "Permit type (BP building permit, ...).",
               "Permit Sub Type Code": "Permit sub-type.", "Number of Floors": "Floors.", "Number of Units": "Units.", "CAD Permit Status": "BCAD's status for the permit.", "Dim 1": "Dimension 1.",
               "Builder": "Builder.", "Value": "Declared permit value.", "Dim 2": "Dimension 2.", "Builder's Phone": "Builder phone.", "Date Worked": "Date BCAD worked the permit.", "Dim 3": "Dimension 3.",
               "Appraiser": "BCAD appraiser on the permit.", "Date Completed": "Date the work was completed.", "Area": "Area of the work in sq ft.", "Land Use": "Land use.",
               "Percent Complete Override": "1 when percent complete was overridden.", "Percent Complete": "Percent complete.", "Comments": "Permit comments.", "Permit Source": "Source of the permit record.",
               "Last Changed": "Date the permit record last changed.", "Active": "T when the permit is active."},
 "ag-sales": {"Buyer Name": "Buyer (grantee).", "Seller Name": "Seller (grantor).", "Deed Type": "Deed type.", "Deed Volume": "Deed book volume.", "Deed Date": "Deed date.", "Deed Page": "Deed page.",
              "Deed Number": "Deed instrument number.", "Recorded Date": "Date the deed was recorded.", "Consideration": "Consideration stated on the deed.", "Buyer ID": "Buyer owner id.",
              "Seller ID": "Seller owner id.", "Sale Price": "Sale price (confidential under Tex. Gov. Code 552.149).", "Sale Date": "Sale date.", "Adjust Code": "Sale price adjustment code.",
              "Adjust Percentage": "Sale adjustment percent.", "Adjust Amount": "Sale adjustment amount.", "Adjust Reason": "Reason for the adjustment.", "Confirmed By": "Who confirmed the sale.",
              "Confirmed Date": "Date confirmed.", "Confirmed Source": "Source of the confirmation.", "Confirmed Sale Price": "Confirmed sale price.", "Buyer Confidence Level": "Confidence in the buyer's information.",
              "Seller Confidence Level": "Confidence in the seller's information.", "Confirm Comment": "Confirmation comment.", "Financing Code": "Financing type (OT other, CV conventional, ...).",
              "Amount Financed": "Amount financed.", "Interest Rate": "Interest rate.", "Finance Years": "Loan term in years.", "2nd Amount Financed": "Second loan amount.", "2nd Interest Rate": "Second loan rate.",
              "2nd Finance Years": "Second loan term.", "Amount Down": "Down payment.", "Finance Comment": "Financing comment.", "Sale Type": "Sale type (Q qualified, ...).",
              "Sale Ratio Type": "Ratio-study type code.", "Sale State Code": "State code at the time of sale.", "School Entity": "School district entity id.", "City Entity": "City entity id.",
              "Sale Class": "Improvement class at sale.", "Sale Sub Class": "Improvement sub-class at sale.", "Sale Comment": "Sale comment.", "Sale Realtor": "Realtor.",
              "Sale Year Built": "Year built at sale.", "Sale Imprv Unit Price": "Improvement value per sq ft at sale.", "Sale Living Area": "Living area at sale.", "Sale Land Acres": "Land acres at sale.",
              "Sale Land Sqft": "Land sq ft at sale.", "Sale Land Front Foot": "Front feet at sale.", "Sale Land Depth": "Land depth at sale.", "Sale Land Unit Price": "Land unit price at sale.",
              "Sale Land Type Code": "Land type at sale."},
}
for pfx, nm in [("Begin", "before"), ("Final", "after")]:
    for a, b in [("land_hstd_val", "land homestead value"), ("land_non_hstd_val", "land non-homestead value"), ("imprv_hstd_val", "improvement homestead value"),
                 ("imprv_non_hstd_val", "improvement non-homestead value"), ("ag_use_val", "ag use value"), ("ag_market", "ag market value"), ("timber_use", "timber use value"),
                 ("timber_market", "timber market value"), ("market", "market value"), ("appraised_val", "appraised value"), ("ten_percent_cap", "homestead cap loss (10% cap)"),
                 ("assessed_val", "assessed value"), ("rendered_val", "rendered value"), ("exemptions", "exemptions"), ("entities", "taxing units")]:
        AG.setdefault("ag-inq", {})[f"{pfx}_{a}"] = f"{b.capitalize()} {nm} the inquiry."
for a, b in [("appraised_val", "appraised value"), ("assessed_val", "assessed value"), ("market_val", "market value"), ("imprv_hstd_val", "improvement homestead value"),
             ("land_hstd_val", "land homestead value"), ("ag_land_mkt_val", "ag land market value"), ("ag_land_use_val", "ag land use value"), ("imprv_non_hstd_val", "improvement non-homestead value"),
             ("land_non_hstd_val", "land non-homestead value"), ("ag_market", "ag market value"), ("ag_market_val", "ag market value"), ("timber_market", "timber market value"),
             ("timber_market_val", "timber market value"), ("timber_use", "timber use value"), ("ten_percent_cap", "homestead cap loss (10% cap)"), ("pers_prop_mineral_value", "personal property / mineral value")]:
    AG["ag-notice"][f"An_{a}"] = f"Notice: this year's {b}."; AG["ag-notice"][f"An_prev_{a}"] = f"Notice: prior year's {b}."
AG["ag-inq"].update({"Appraiser_nm": "Appraiser on the property.", "Hood_cd": "Neighborhood code.", "File_as_name": "Owner name (CONFIDENTIAL OWNER where protected).",
    "State_cd": "State code.", "Prop_type_cd": "Property type: R real, P personal, MH mobile home, MN mineral.", "Legal_desc": "Legal description.", "Entities": "Taxing units.",
    "Exemptions": "Exemptions.", "Situs": "Property address.", "Agent_name": "Agent on the inquiry.", "Inq_type": "Inquiry type (EX exemption, VAL value, ...).",
    "Inq_status": "Inquiry status code (CI closed, ...).", "Inq_nature": "How the inquiry came in (E-INQ online, ...).", "Inq_assigned_reason_cd": "Reason code assigned.",
    "Inq_taxpayer_comments": "Taxpayer comments.", "Inq_appraiser_comments": "Appraiser comments.", "Inq_by_type": "Who made the inquiry (OW owner, AG agent).",
    "Inq_appraisal_staff": "Staff member on the inquiry.", "Appraiser_meeting_date_time": "Informal meeting date and time.",
    "Appraiser_meeting_appraiser_comments": "Appraiser's comments from the meeting.", "Appraiser_meeting_Taxpayer_Comments": "Taxpayer's comments from the meeting.",
    "Inq_operator_Comments": "Operator comments (often the settlement note)."})
for k in P:
    if not k.startswith("ag-"): continue
    for c in P[k]["columns"]:
        n = c["name"]; t = AG.get(k, {}).get(n) or AG["*"].get(n)
        if t and not BS.get(f"{k}:{n}"): BS[f"{k}:{n}"] = t
json.dump(m, open("manifest.json", "w"), indent=1, ensure_ascii=False)

# ---- ARB protests (ag-arb) ----
m = json.load(open("manifest.json")); BS = m["descriptions_by_set"]
ARB = {"Current Appraiser": "Appraiser currently on the property.", "Neighborhood": "Neighborhood code.", "Owner Name": "Owner name.",
 "Property Type": "Property type: R real, P personal, MH mobile home, MN mineral.", "Legal Description": "Legal description.", "Entities": "Taxing units.",
 "Exemptions": "Exemptions.", "Situs": "Property address.", "Agent Name": "Agent on the protest.", "Protest Type": "Protest type (PROT protest, ...).",
 "Protest Status": "Protest status code (closed, settled, scheduled ...).", "Reason Codes": "Protest reasons checked on the notice of protest (VOM value over market, UE unequal, ...).",
 "Taxpayer Comments": "Taxpayer comments on the protest.", "Protest By Type": "Who filed: OW owner, AG agent.", "Protest By Name": "Name of who filed.",
 "Taxpayer Affidavit Received Date": "Date a taxpayer affidavit was received.", "Affidavit Testimony By": "Who gave affidavit testimony.", "Testimony Received": "Whether testimony was received.",
 "Docket ID": "ARB hearing docket id.", "Docket Start Date/Time": "Scheduled hearing start.", "Docket End Date/Time": "Scheduled hearing end.", "Hearing Rescheduled": "T when the hearing was rescheduled.",
 "Assigned Panel": "ARB panel assigned.", "Arrived Date/Time": "When the protester checked in.", "1st Motion Decision": "Decision on the first motion.", "1st Motion Decision Date": "Date of the first motion decision.",
 "2nd Motion Decision": "Decision on the second motion.", "2nd Motion Decision Date": "Date of the second motion decision.", "Appraiser Meeting Appraiser": "Appraiser at the informal meeting.",
 "Appraiser Meeting Date/Time": "Informal meeting date and time.", "Appraiser Meeting Arrived Date/Time": "When the protester arrived for the informal meeting.",
 "Appraiser Meeting Appraiser Comments": "Appraiser's comments from the informal meeting.", "Appraiser Meeting Taxpayer Comments": "Taxpayer's comments from the informal meeting.",
 "Hearing Start Date/Time": "Actual ARB hearing start.", "Hearing End Date/Time": "Actual ARB hearing end.", "Hearing Appraiser": "District appraiser at the hearing.",
 "Recording Appraiser": "Appraiser who recorded the hearing.", "Panel Members": "ARB panel members.", "District Comments": "District comments on the case.",
 "Other Motion": "Other motion text.", "First Motion": "First motion text.", "Second Motion": "Second motion text."}
for pfx, nm in [("Begin", "before"), ("Final", "after")]:
    for a, b in [("Land HS Value", "land homestead value"), ("Land NHS Value", "land non-homestead value"), ("Improvement HS Value", "improvement homestead value"),
                 ("Improvement NHS Value", "improvement non-homestead value"), ("Ag Use Value", "ag use value"), ("Ag Market", "ag market value"), ("Timber Use", "timber use value"),
                 ("Timber Market", "timber market value"), ("Market", "market value"), ("Appraised Value", "appraised value"), ("Ten Percent Cap", "homestead cap loss (10% cap)"),
                 ("Assessed Value", "assessed value"), ("Rendered Value", "rendered value"), ("Exemptions", "exemptions"), ("Entities", "taxing units")]:
        ARB[f"{pfx} {a}"] = f"{b.capitalize()} {nm} the protest."
for c in P["ag-arb"]["columns"]:
    n = c["name"]; t = ARB.get(n) or AG["*"].get(n)
    if t and not BS.get(f"ag-arb:{n}"): BS[f"ag-arb:{n}"] = t
json.dump(m, open("manifest.json", "w"), indent=1, ensure_ascii=False)
