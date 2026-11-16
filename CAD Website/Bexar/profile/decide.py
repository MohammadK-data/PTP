"""Suggested Need / Maybe / Drop decision and a one-line comment for every column of the Bexar review page.
Writes seed.json for _review/add_column_review.py --seed. File keys match review.js rvFileKey (group id + '.' +
position in the year's file list), so one decision covers the same file in both snapshots.

How the calls are made (in this order):
 1. Column blank in every snapshot, or a layout filler -> Drop.
 2. The per-file rules below (NEED / MAYBE / DROP with a reason), written for a protest firm: values, the
    property's traits, owner and situs, exemptions, agents and protest outcomes are Need; workflow and
    rarely-filled detail is Maybe; internal, duplicate or near-constant fields are Drop.
 3. Same value on every row (not a key or year) -> Drop.
 4. Family rules for the PACS exemption columns (_exempt / _qualify_yr / _prorate_* / _amt / _allocation_factor).
 5. Anything left -> Maybe, with its fill rate.
"""
import json, re, time
M = json.load(open("manifest.json")); P = json.load(open("profile.json"))

# ---------- file keys (same as review.js) ----------
FILES = {}   # fk -> {"table":..., "keys":[dataset keys], "short":...}
for s in M["sources"]:
    for g in s["groups"]:
        for y in g["years"]:
            for i, k in enumerate(y["datasets"]):
                fk = f"{g['id']}.{i}"
                lab = M["datasets"][k]["label"]
                tbl = g["label"] if len(y["datasets"]) == 1 else f"{g['label']} · {lab}"
                f = FILES.setdefault(fk, {"keys": [], "table": tbl})
                f["keys"].append(k); f["table"] = tbl  # latest snapshot's label
                f["short"] = k.split("-", 1)[1] if k.startswith(("p26-", "s26-")) else ("ps" if k.startswith("ps26") else k)

def colstats(keys):
    st = {}
    for k in keys:
        R = P[k]["rows"]
        for c in P[k]["columns"]:
            s = st.setdefault(c["name"], {"fill": 0, "distinct": 0, "vals": set(), "rows": 0, "n": 0, "top": c["top"], "desc": c.get("desc")})
            s["fill"] = max(s["fill"], c["nonnull"] / R if R else 0)
            s["distinct"] = max(s["distinct"], c["distinct"]); s["n"] += 1
            if c["distinct"] == 1 and c["top"]: s["vals"].add(c["top"][0][0])
            elif c["distinct"] > 1: s["vals"].add(object())
            s["top"] = c["top"]
    return st

def tcount(top, val="T"):
    return next((n for v, n in top if v == val), 0)

N, Y, D = "need", "maybe", "drop"
KEY = "Join key: keep whenever this file is used."
# ---------- per-file rules: short name -> {column: (status, comment)} ----------
R = {}
def rule(short, status, cols, comment):
    for c in cols.split("|"): R.setdefault(short, {})[c.strip()] = (status, comment)

# PACS property roll
rule("info", N, "prop_id", "Primary key of every Bexar file (12 digits, leading zeros; strip them to match the Agent Export and Property Summary).")
rule("info", N, "prop_val_yr", "Tax year; needed to stack snapshots and years.")
rule("info", N, "sup_num", "Supplement number: tells which rows changed after the preliminary roll.")
rule("info", Y, "sup_action|sup_cd|sup_desc", "Why a supplement changed the value; useful to explain post-notice changes, not needed day to day.")
rule("info", N, "prop_type_cd", "Real, personal, mobile home or mineral: decides which protest workflow applies.")
rule("info", N, "geo_id", "BCAD map/parcel number shown on notices and the BCAD website; clients quote it.")
rule("info", N, "py_owner_id|py_owner_name", "Current owner: client matching and outreach.")
rule("info", N, "py_addr_line1|py_addr_line2|py_addr_city|py_addr_state|py_addr_zip", "Owner mailing address for outreach and client matching.")
rule("info", Y, "py_addr_line3|py_addr_country|py_addr_zip_cass", "Extra mailing-address detail; rarely needed beyond line 1-2, city, state, ZIP.")
rule("info", Y, "py_confidential_flag|py_address_suppress_flag|py_addr_ml_deliverable", "Mailing flags: confidential / suppressed / undeliverable addresses should be skipped in mail campaigns.")
rule("info", Y, "partial_owner", "Undivided-interest owner flag; explains why a prop_id has several rows.")
rule("info", N, "situs_num|situs_street_prefx|situs_street|situs_street_suffix|situs_unit|situs_city|situs_zip", "Property address: search, client matching and comps.")
rule("info", N, "legal_desc", "Legal description; needed on protest forms and to confirm the parcel.")
rule("info", Y, "legal_desc2", "Overflow of the legal description; only on a third of rows.")
rule("info", Y, "legal_acreage", "Legal acreage (4 implied decimals); land_acres is the appraised size we use.")
rule("info", N, "abs_subdv_cd|hood_cd", "Subdivision and neighborhood: the basis for equity and sales comps.")
rule("info", Y, "block|tract_or_lot", "Block and lot; already inside legal_desc.")
rule("info", N, "land_hstd_val|land_non_hstd_val|imprv_hstd_val|imprv_non_hstd_val", "Land / improvement value split: needed to argue land vs building value.")
rule("info", N, "ag_use_val|ag_market", "Ag (productivity) value and its market value: matter for every ag-valued tract.")
rule("info", N, "market_value|appraised_val|assessed_val", "The values we protest and report on.")
rule("info", N, "ten_percent_cap|nhs_cap_loss", "Homestead (10%) and non-homestead (20%) cap loss: needed to estimate the tax impact of a reduction.")
rule("info", N, "arb_protest_flag", "Protest on file at export time; shows which accounts were protested.")
rule("info", N, "deed_dt", "Last deed date: recent buyers and sale timing.")
rule("info", Y, "deed_book_id|deed_book_page|deed_num", "Deed reference; useful to pull the deed, not for analysis.")
rule("info", D, "mortgage_co_id|mortage_co_name|mortgage_acct_id", "Mortgage company fields are not used by Bexar (blank or zero).")
rule("info", Y, "jan1_owner_id|jan1_owner_name", "January 1 owner when it differs from the current owner (about 2% of rows): who could protest.")
rule("info", D, "jan1_addr_line1|jan1_addr_line2|jan1_addr_line3|jan1_addr_city|jan1_addr_state|jan1_addr_country|jan1_addr_zip|jan1_addr_zip_cass|jan1_addr_zip_rt|jan1_confidential_flag|jan1_address_suppress_flag|jan1_ml_deliverable", "January 1 owner's address; we mail the current owner.")
rule("info", N, "hs_exempt|ov65_exempt|dp_exempt|dvhs_exempt", "Main homestead exemptions: drive the cap and the tax saving of a reduction.")
rule("info", Y, "ov65s_exempt|dps_exempt|dv1_exempt|dv1s_exempt|dv2_exempt|dv2s_exempt|dv3_exempt|dv3s_exempt|dv4_exempt|dv4s_exempt|dvhss_exempt", "Surviving-spouse and disabled-veteran exemptions; matter only for the tax estimate.")
rule("info", Y, "hs_qualify_yr|ov65_qualify_yr|dp_qualify_yr|dvhs_qualify_yr", "Year the exemption started; useful to check cap history.")
rule("info", N, "imprv_state_cd|land_state_cd", "State (property category) code: residential vs commercial routing and reporting.")
rule("info", Y, "personal_state_cd", "State code for business personal property (6% of rows).")
rule("info", N, "land_acres", "Appraised land size (4 implied decimals).")
rule("info", D, "entity_agent_id|entity_agent_name|entity_agent_addr_line1|entity_agent_addr_line2|entity_agent_addr_line3|entity_agent_city|entity_agent_state|entity_agent_country|entity_agent_zip|entity_agent_cass|entity_agent_rt", "Taxing-unit (tax bill) agent; not the protest agent we track.")
rule("info", N, "ca_agent_id|ca_agent_name|arb_agent_id|arb_agent_name", "Appraisal and ARB agent of record: our coded accounts and competitor share.")
rule("info", Y, "ca_agent_addr_line1|ca_agent_addr_line2|ca_agent_city|ca_agent_state|ca_agent_zip|arb_agent_addr_line1|arb_agent_addr_line2|arb_agent_city|arb_agent_state|arb_agent_zip", "Agent mailing address; the Agents file has the same.")
rule("info", D, "ca_agent_addr_line3|ca_agent_country|ca_agent_zip_cass|ca_agent_zip_rt|arb_agent_addr_line3|arb_agent_country|arb_agent_zip_cass|arb_agent_zip_rt", "Agent address detail; not needed.")
rule("info", D, "mineral_type_of_int|mineral_int_pct|mineral_state_cd", "Mineral interest fields; Bexar has almost no mineral accounts and we don't protest them.")
rule("info", Y, "productivity_use_code|ag_late_loss", "Ag detail; only for ag accounts.")
rule("info", Y, "dba", "Business name (9% of rows): helps match commercial clients.")
rule("info", D, "ref_id1|ref_id2", "BCAD internal reference ids.")
rule("info", D, "appr_owner_id|appr_owner_name|appr_addr_line1|appr_addr_line2|appr_addr_line3|appr_addr_city|appr_addr_state|appr_addr_country|appr_addr_zip|appr_addr_zip_cass|appr_addr_zip_cass_route|appr_ml_deliverable|appr_confidential_flag|appr_address_suppress_flag", "Appraisal-year owner block; duplicates the py_owner block for the current year.")
rule("info", Y, "rendition_filed|rendition_date|rendition_penalty", "BPP rendition status and penalty: relevant for business personal property clients.")
rule("info", N, "entities", "Taxing units on the account: needed to apply tax rates.")
rule("info", D, "dataset_id|udi_group|personal_property_group", "Export / grouping ids with no protest use.")
rule("info", Y, "exemption_percentage|apply_percent_exemption_flag", "Partial (percentage) exemption; only matters for the tax estimate.")
rule("info", Y, "appraised_val_reflecting_productivity_loss|assessed_val_reflecting_productivity_loss", "Values after the ag productivity loss; useful for ag tracts only.")
rule("info", Y, "late_correction_val|sic_code", "Rarely used detail; kept available.")
rule("info", D, "pp_late_interstate_allocation_val|pp_late_freeport_val|omitted_property_flag|omitted_imprv_hstd_val|omitted_imprv_non_hstd_val", "Late-filing and omitted-property detail; zero or blank on nearly every row.")

# Taxing units
rule("entinfo", N, "prop_id|owner_id|entity_id", "Join key (property, owner, taxing unit).")
rule("entinfo", N, "prop_val_yr", "Tax year.")
rule("entinfo", Y, "sup_num", "Supplement of the row.")
rule("entinfo", N, "entity_cd|entity_name", "Which taxing unit the row is for.")
rule("entinfo", N, "taxable_val", "Taxable value per unit: what the tax bill is computed from, so it is the basis of the tax-savings estimate.")
rule("entinfo", Y, "assessed_val|market_value|appraised_value", "Value per unit; equals the roll value except for partial units.")
rule("entinfo", N, "hs_amt|ov65_amt|dp_amt|dvhs_amt|hs_cap|freeze_ceiling|freeze_yr|nhs_cap_loss", "Exemption amounts, cap and over-65/disabled tax ceiling per unit: needed for an accurate tax-savings estimate.")
rule("entinfo", Y, "hs_state_amt|hs_local_amt|dv_amt|ex366_amt|lve_amt|145b_amt|145d_amt|145d1_amt|145f_amt|ex_xv_amt|dvhss_amt|qvss_amt|masss_amt|ccf_amt|chodo_amt|lih_amt|mcr_freeze_ceiling_reduction_amount|freeze_previous_tax|freeze_previous_tax_unfrozen|freeze_transfer_flag|freeze_transfer_percentage|freeze_transfer_date|freeze_exmpt_type_cd|homestead_group_exemption_factor|new_val_hs|new_val_nhs|new_val_p|new_val_taxable|partial_entity", "Detail behind the taxable value; useful for tax-bill reconciliation, not for valuation.")
rule("entinfo", Y, "land_hstd_val|land_non_hstd_val|imprv_hstd_val|imprv_non_hstd_val|ag_use_val|ag_market_val|ag_use_val_ne|ag_market_ne", "Value split per unit; the roll already has it.")
rule("entinfo", D, "ent_pct_land_hs|ent_pct_land_nonhs|ent_pct_imprv_hs|ent_pct_imprv_nonhs|ent_pct_ag_use|ent_pct_ag_mkt|ent_pct_tim_use|ent_pct_tim_mkt|ent_pct_pers|ent_pct_min|ent_pct_auto", "Share of each value in the unit; 100% except on split parcels.")
rule("entinfo", D, "entity_xref_id|filler_134|dataset_id", "Internal ids / filler.")

# Unit totals
rule("enttot", N, "entity_id|entity_cd|entity_name", "Identifies the taxing unit.")
rule("enttot", Y, "market_value|taxable_val|num_records|land_hstd_val|land_non_hstd_val|imprv_hstd_val|imprv_non_hstd_val|personal_val|real_mobile_val", "Roll-wide totals per unit: market context, not per-property data.")
rule("enttot", Y, "year|sup_num", "Year and supplement of the totals.")

# Improvements / land / others
rule("imprinfo", N, "prop_id|imprv_id", KEY)
rule("imprinfo", N, "prop_val_yr", "Tax year.")
rule("imprinfo", N, "imprv_type_cd|imprv_state_cd|imprv_val", "Building type, category and value: the improvement side of every protest.")
rule("imprinfo", Y, "imprv_type_desc", "Text of imprv_type_cd; can be looked up.")
rule("imprinfo", Y, "imprv_homesite|imprv_homesite_pct", "Homesite share of the building; matters for the cap split.")
rule("imprinfo", D, "omitted|omitted_imprv_val", "Omitted-property flag; almost always F / zero.")
rule("imprdet", N, "prop_id|imprv_id|imprv_det_id", KEY)
rule("imprdet", N, "prop_val_yr", "Tax year.")
rule("imprdet", N, "imprv_det_type_cd|imprv_det_class_cd|yr_built|depreciation_yr|imprv_det_area|imprv_det_val", "Segment type, class, age, area and value: the core of cost-approach and equity arguments.")
rule("imprdet", Y, "imprv_det_type_desc", "Text of the segment type code.")
rule("imprdet", Y, "sketch_cmds", "Sketch drawing commands; large text, only for rebuilding sketches.")
rule("imprattr", N, "prop_id|imprv_id|imprv_det_id", KEY)
rule("imprattr", N, "prop_val_yr", "Tax year.")
rule("imprattr", N, "imprv_attr_desc|imprv_attr_cd", "Building attributes (foundation, roof, HVAC, pool, quality ...): comps and condition evidence.")
rule("imprattr", D, "imprv_attr_id", "Row id of the attribute; no meaning.")
rule("land", N, "prop_id|land_seg_id", KEY)
rule("land", N, "prop_val_yr", "Tax year.")
rule("land", N, "land_type_cd|state_cd|size_acres|size_square_feet|mkt_ls_method|mkt_ls_class|land_seg_mkt_val", "Land type, size, pricing method/schedule and value: the land side of every protest.")
rule("land", Y, "land_type_desc", "Text of land_type_cd.")
rule("land", Y, "land_seg_homesite|land_homesite_pct|effective_front|effective_depth", "Homesite share and front/depth: occasional land arguments.")
rule("land", Y, "ag_apply|ag_ls_method|ag_ls_class|ag_value", "Ag valuation of the segment; ag tracts only.")
rule("mobile", N, "prop_id|imprv_id", KEY)
rule("mobile", Y, "prop_val_yr|mbl_hm_make|mbl_hm_model", "Mobile-home make and model; rarely protested.")
rule("mobile", D, "mbl_hm_title_num|mbl_hm_sn|mbl_hm_hud_num|mbl_hm_sn_2|mbl_hm_hud_num_2|mbl_hm_sn_3|mbl_hm_hud_num_3", "Title, serial and HUD numbers; no protest use.")
rule("defer", N, "prop_id", KEY)
rule("defer", Y, "owner_id|owner_name|geo_id|exmpt_type_cd|deferral_start_date|deferral_end_date", "Tax deferral: the owner is not paying now, so a protest is worth less; good to flag.")
rule("defer", D, "last_change_date", "Record maintenance date.")
for f in ("arb", "lawsuit", "arblaw"):
    rule(f, N, "prop_id|prop_val_yr", "Property and tax year in protest / litigation / arbitration: flags accounts we cannot simply protest again.")
    rule(f, Y, "geo_id", "Map number; prop_id is enough.")
    rule(f, D, "ref_id1|ref_id2", "BCAD reference ids, mostly blank.")
rule("arb", N, "arb_status", "Status of the ARB protest.")
rule("agent", N, "agent_id|agent_name", "Every agent firm: competitor tracking and decoding agent ids on the roll.")
rule("agent", Y, "agent_addr_line1|agent_addr_line2|agent_city|agent_state|agent_zip|agent_country", "Agent address.")
rule("agent", D, "agent_addr_line3|agent_zip_cass|agent_zip_rt", "Address detail; not needed.")
rule("abs", N, "abs_subdv_cd|abs_subdv_desc", "Subdivision / abstract names for abs_subdv_cd: needed to label comps.")
rule("state", N, "state_cd|state_cd_description", "Decodes the state codes used everywhere.")
rule("state", Y, "ptd_state_cd|ptd_state_cd_description", "Comptroller (PTD) category the BCAD code rolls up to.")
rule("country", Y, "country_cd|country_name", "Decodes mailing country codes; nearly all accounts are US.")
rule("header", N, "run_date_time|appraisal_year", "When the export was run and for which year: provenance of every number.")
rule("header", Y, "file_description|supplement_number|pacs_version|export_version", "Export description and versions; useful when the layout changes.")
rule("header", D, "office_name|operator|office_use_only|entity_code", "Who ran the export; no analytical use.")
rule("entity", N, "entity_id|entity_cd", "Decodes taxing-unit ids.")

# Agent Export
A = "ag-"
rule("ag-propdata", N, "Property ID|Year", KEY)
rule("ag-propdata", N, "Year Built|Living Area|Effective Year Built|Neighborhood", "Age, size and neighborhood: core comp fields.")
rule("ag-propdata", N, "Valuation Method Code", "Cost, income, ARB, distributed or shared: tells how BCAD valued the property, which shapes the protest argument.")
rule("ag-propdata", Y, "Land Sqft|Land Acres|Land # of Lots|Number of Improvements|Region|Zoning", "Already in the PACS roll and land file; Zoning is only here (useful for commercial).")
rule("ag-propdata", Y, "Property Remarks|Property Comment|Next Appraisal Reason", "Appraiser field notes (condition, permits, reviews): good protest evidence, free text.")
rule("ag-propdata", Y, "Last Appraiser|Value Appraiser|Neighborhood Appraiser", "Which appraiser handles the property; useful for hearing prep.")
rule("ag-propdata", D, "Map ID|Next Appraiser|Land Appraiser|Subdivision Appraiser|Category Appraiser", "Mostly blank workflow fields.")
rule("ag-notice", N, "Prop_id|Notice_yr", KEY)
rule("ag-notice", N, "An_market_val|An_prev_market_val|An_appraised_val|An_prev_appraised_val|An_assessed_val|An_prev_assessed_val", "Notice values this year and last: the year-over-year change clients ask about.")
rule("ag-notice", N, "Exemption|An_ten_percent_cap", "Exemptions and cap on the notice.")
rule("ag-notice", Y, "An_prev_yr|Notice_num|Owner_id|Sup_num|Prev_exemption|An_prev_ten_percent_cap", "Notice detail.")
rule("ag-notice", Y, "An_imprv_hstd_val|An_prev_imprv_hstd_val|An_land_hstd_val|An_prev_land_hstd_val|An_imprv_non_hstd_val|An_prev_imprv_non_hstd_val|An_land_non_hstd_val|An_prev_land_non_hstd_val|An_ag_land_mkt_val|An_prev_ag_land_mkt_val|An_ag_land_use_val|An_prev_ag_land_use_val|An_ag_market|An_prev_ag_market_val|An_pers_prop_mineral_value|An_prev_pers_prop_mineral_value", "Value split on the notice; the PACS roll has the current split.")
rule("ag-notice", D, "Sup_yr", "Same as Notice_yr.")
rule("ag-comments", N, "Property ID", KEY)
rule("ag-comments", Y, "Comment Type|Comment", "Appraiser comments on the property: free-text evidence, read case by case.")
rule("ag-events", N, "Property ID", KEY)
rule("ag-events", Y, "Event Year|Event Date|Event Type|Event Description", "Property history (value changes, exemption actions, e-file); useful for audits, 4.5M rows.")
rule("ag-shared", Y, "PACS Property ID|Year|Shared CAD Code|Shared CAD Prop ID", "Only 421 properties shared with a neighboring CAD; keep to flag cross-county parcels.")
rule("ag-impr", N, "Property ID|Year|Improvement ID|Detail ID", KEY)
rule("ag-impr", N, "Improvement Type Code|State Code|Effective Year Built|Improvement Value|Physical %|Functional %|Economic %|Percent Complete", "Building type, age, depreciation and value: condition and obsolescence arguments.")
rule("ag-impr", N, "Detail Class Code|Detail Sub Class Code|Detail Method Code|Detail Unit Price|Detail Area|Detail Value|Detail Condition Code|Detail Actual Year Built|Detail Effective Year Built|Detail Physical %|Detail Functional %|Detail Economic %|Detail Base Depreciation %", "Segment class, unit price, area, condition and depreciation: the full cost approach, not in the PACS export.")
rule("ag-impr", Y, "Supplement #|Homesite Flag|Description|# of Improvements|# of Stories|Base Depreciation %|Total Detail Value|Improvement Value Source|Adjustments and Percentages|Detail Number of Units|Detail Number of Stories|Detail Add Factor|Detail Size Adjustment %|Detail Percent Complete|Detail Value Source|Detail Calculated Value|Detail Age|Detail Adjustments and Percentages|Entity and Percentages", "Supporting cost-approach detail.")
rule("ag-impr", Y, "Comment|Physical Comment|Functional Comment|Economic Comment|Detail Physical Comment|Detail Functional Comment|Detail Economic Comment|Percent Complete Comment|Detail % Complete Comment|Base Depr. Comment", "Appraiser's reason for a depreciation; rare but strong evidence when present.")
rule("ag-impr", D, "Detail Use Unit Price for % Base Flag|Detail Stories Multiplier Flag", "Pricing switches with no protest use.")
rule("ag-feat", N, "Property ID|Year|Improvement ID|Improvement Detail ID", KEY)
rule("ag-feat", N, "Feature Type|Feature Description", "Building features (wall, roof, heating, quality ...): comps and condition.")
rule("ag-feat", Y, "Sup Num", "Supplement of the row.")
rule("ag-income", N, "Property ID|Year", KEY)
rule("ag-income", N, "Property Type|Class|Gross Building Area|Net Rentable Area|NBHD Economic Area", "Income-model inputs BCAD used for commercial properties: needed for income-approach protests.")
rule("ag-income", Y, "Level Code|Property Name|Comment", "Income worksheet detail (comments mark confidential worksheets).")
rule("ag-land", N, "Property ID|Year|Land ID", KEY)
rule("ag-land", N, "State Code|Land Type Code|Market Pricing Method|Market Pricing Table|Market Unit Price|Size in Sq Ft|Size in Acres|Market Value", "Land pricing: method, schedule, unit price, size and value; unit price is not in the PACS land file.")
rule("ag-land", Y, "Supplement #|Homesite Flag|Comment|Width Front|Width Back|Depth Right|Depth Left|Legal Acreage|Number of Lots|Effective Size Acres|Size Useable Acres|Size Useable Sqft|Calculated Market Value|Adjustments and Percentages|Entities and Percentages", "Land size detail and adjustments (topography, shape ...): occasional land arguments.")
rule("ag-land", Y, "Ag Pricing Method|Ag Pricing Table|Ag Unit Price|Ag Value|Ag Apply Flag|Ag Use Code|Ag Loss", "Ag valuation; ag tracts only.")
rule("ag-land", D, "Late Ag Apply Flag", "Late ag application flag; almost always F.")
CONF = " Confidential under Tex. Gov. Code 552.149(b): use only as protest evidence, never in shared outputs."
rule("ag-sales", N, "Property ID|Sale ID", KEY)
rule("ag-sales", N, "Sale Price|Sale Date|Sale Type|Sale State Code|Sale Class|Sale Sub Class|Sale Year Built|Sale Living Area|Sale Land Acres|Sale Land Sqft|Sale Imprv Unit Price", "Sale price, date and the property's traits at sale: the sales comps for protests." + CONF)
rule("ag-sales", Y, "Deed Date|Recorded Date|Deed Type|Deed Volume|Deed Page|Deed Number|Consideration|Buyer Name|Seller Name|Buyer ID|Seller ID", "Deed and parties; helps qualify a sale.")
rule("ag-sales", Y, "Adjust Code|Adjust Percentage|Adjust Amount|Adjust Reason|Confirmed By|Confirmed Date|Confirmed Source|Confirmed Sale Price|Buyer Confidence Level|Confirm Comment|Sale Ratio Type|Sale Comment|Comment|Financing Code|School Entity|City Entity|Sale Land Front Foot|Sale Land Depth|Sale Land Unit Price|Sale Land Type Code", "How BCAD adjusted, confirmed and used the sale.")
rule("ag-sales", D, "Amount Financed|Interest Rate|Finance Years|2nd Amount Financed|2nd Interest Rate|2nd Finance Years|Amount Down|Finance Comment|Sale Realtor|Seller Confidence Level", "Financing and realtor detail; mostly zero or blank.")
rule("ag-saleland", N, "Property ID|Land ID|Sale ID|Year", KEY)
rule("ag-saleland", Y, "Land Type|State Code|Homesite Flag|Size Acres|Market Value|Ag Value|Ag Loss|Ag Table", "Land on the sold property at the time of sale; adds detail to a comp.")
rule("ag-saleimpr", N, "Property ID|Improvement ID|Sale ID|Year", KEY)
rule("ag-saleimpr", Y, "Improvement Type|State Code|Homesite Flag|Improvement Value", "Improvements on the sold property at the time of sale.")
rule("ag-bpp", N, "Prop_id|Prop_val_yr", KEY)
rule("ag-bpp", N, "Segment_type|Segment_value", "BPP value by segment (inventory, furniture & fixtures ...): what a BPP protest argues.")
rule("ag-bpp", Y, "Sup_num|Seg_id|Active_flag|Segment_quality|Segment_density|Segment_area|Penalty_amount", "Segment detail and late-rendition penalty.")
rule("ag-bpp", D, "Penalty_amount_override|Penalty_amount_dt", "Penalty bookkeeping.")
rule("ag-bpplink", N, "Personal_prop_id|Linked_real_prop_id", "Links a business's BPP account to the building it sits in: lets us offer both protests to one client.")
rule("ag-permit", N, "Permit ID", KEY)
rule("ag-permit", N, "Issue Date|Permit Type Code|Value|CAD Permit Status", "Recent permits explain value jumps (new construction, remodel).")
rule("ag-permit", Y, "Permit #|Issuer|Res / Com|Permit Sub Type Code|Number of Floors|Number of Units|Builder|Date Worked|Appraiser|Date Completed|Area|Percent Complete|Percent Complete Override|Comments|Active|Last Changed|Permit Status Code", "Permit detail; useful when a permit is in dispute.")
rule("ag-permit", D, "Property Type|Issued To|Issue Limit Date|Issuer Phone|Issuer Xref|Number|Prefix|Street|Suffix|Unit Type|Unit Number|Subdivision|Plat|Block|Lot|City|Building Inspection|Electrical Inspection|Mechanical Inspection|Plumbing Inspection|Dim 1|Dim 2|Dim 3|Builder's Phone|Land Use|Permit Source", "Address and inspection fields; the property link gives the address, the rest is blank or constant.")
rule("ag-permitprop", N, "Permit ID|Property ID", "Links permits to properties.")
rule("ag-arb", N, "Property ID|Year|Case ID", KEY)
rule("ag-arb", N, "Protest Type|Protest Status|Reason Codes|Protest By Type|Agent Name|Arrived Date/Time|Docket Start Date/Time|Begin Market|Begin Assessed Value|Final Market|Final Assessed Value|Exemptions|Geo ID|Neighborhood|State Code|Property Type|Situs", "Protest outcome fields used by the Bexar scorecard (etl/bexar_arb_extract.py): who protested, how, and the value before and after.")
rule("ag-arb", N, "Begin Appraised Value|Final Appraised Value", "Appraised value before and after the protest: the reduction we report.")
rule("ag-arb", Y, "Owner Name|Current Appraiser|Legal Description|Entities|Protest By Name|Assigned Panel|Hearing Start Date/Time|Hearing End Date/Time|Hearing Rescheduled|Docket ID|Docket End Date/Time|Hearing Appraiser|Panel Members|Appraiser Meeting Appraiser|Appraiser Meeting Date/Time|Appraiser Meeting Arrived Date/Time", "Hearing logistics: panel, appraiser and timing; useful for hearing-prep analysis.")
rule("ag-arb", Y, "Taxpayer Comments|Appraiser Meeting Appraiser Comments|Appraiser Meeting Taxpayer Comments|District Comments|Other Motion|First Motion|Second Motion|1st Motion Decision|1st Motion Decision Date|2nd Motion Decision|2nd Motion Decision Date", "Motions and comments from the case: what argument won; free text.")
rule("ag-arb", Y, "Begin Land HS Value|Begin Land NHS Value|Begin Improvement HS Value|Begin Improvement NHS Value|Final Land HS Value|Final Land NHS Value|Final Improvement HS Value|Final Improvement NHS Value|Begin Ten Percent Cap|Final Ten Percent Cap|Begin Ag Use Value|Begin Ag Market|Final Ag Use Value|Final Ag Market", "Value split before and after; shows whether land or building was cut.")
rule("ag-arb", Y, "Begin Exemptions|Final Exemptions|Begin Entities|Final Entities", "Exemptions and taxing units before and after; changes only on exemption protests.")
rule("ag-arb", D, "Begin Timber Use|Begin Timber Market|Final Timber Use|Final Timber Market|Begin Rendered Value|Final Rendered Value|Taxpayer Affidavit Received Date|Affidavit Testimony By|Testimony Received|Recording Appraiser", "Timber, rendered value and affidavit fields; zero or blank on most cases.")
rule("ag-arbletter", N, "Property ID|Year|Case ID", KEY)
rule("ag-arbletter", Y, "Letter Name|Letter Date/Time", "Letters on the case (hearing notice, order): dates of notices, 5.3M rows.")
rule("ag-protester", N, "Property ID|Year|Case ID", KEY)
rule("ag-protester", N, "Protest by Name|Protest by Type", "Who filed each protest: agent market share by year.")
rule("ag-protester", Y, "Primary Protester", "Primary filer flag when a case has several.")
rule("ag-inq", N, "Prop_id|Prop_val_yr|Case_id", KEY)
rule("ag-inq", Y, "Inq_type|Inq_status|Inq_nature|Inq_by_type|Agent_name|Begin_market|Final_market|Begin_appraised_val|Final_appraised_val|Begin_assessed_val|Final_assessed_val", "Informal inquiries (mostly exemption questions): outcome and values; secondary to formal protests.")
rule("ag-inq", Y, "Appraiser_nm|Hood_cd|State_cd|Legal_desc|Exemptions|Situs|Inq_assigned_reason_cd|Inq_appraisal_staff|Begin_exemptions|Final_exemptions|Begin_entities|Final_entities", "Property and staff context of the inquiry; the roll has the same.")
rule("ag-inq", Y, "Inq_taxpayer_comments|Inq_appraiser_comments|Appraiser_meeting_appraiser_comments|Appraiser_meeting_Taxpayer_Comments|Inq_operator_Comments", "Free-text notes on the inquiry; read case by case.")
rule("ag-inq", Y, "Begin_land_hstd_val|Begin_land_non_hstd_val|Begin_imprv_hstd_val|Begin_imprv_non_hstd_val|Final_land_hstd_val|Final_land_non_hstd_val|Final_imprv_hstd_val|Final_imprv_non_hstd_val|Begin_ag_use_val|Begin_ag_market|Final_ag_use_val|Final_ag_market|Begin_ten_percent_cap|Final_ten_percent_cap", "Value split before and after the inquiry.")
rule("ag-inq", D, "Begin_timber_use|Begin_timber_market|Final_timber_use|Final_timber_market|Begin_rendered_val|Final_rendered_val", "Timber and rendered values; zero or blank on nearly all inquiries.")
for c in ["ag_use_val","ag_market_val","mineral_val","num_real_mobile","num_personal","num_mineral","hs_cap","hs_local_amount","hs_state_amount","ag_late_loss","ag_use_val_ne","ag_market_ne","nhs_cap_loss","late_correction_val"]:
    R.setdefault("enttot", {})[c] = (Y, "Roll-wide total per taxing unit; market context only, not per-property data.")
for c in ["ag_use_val_ex","ag_market_ex","dataset_id","pp_late_interstate_allocation_val","pp_late_freeport_val"]:
    R.setdefault("enttot", {})[c] = (D, "Roll-wide total that is zero or constant for nearly every unit.")
rule("entinfo", Y, "ag_late_loss|late_correction_val|freeze_ceiling_override|freeze_transfer_exmpt_type_cd", "Rare tax-bill adjustments per unit.")
rule("entinfo", D, "ag_use_val_ex|ag_market_ex|pp_late_interstate_allocation_val|pp_late_freeport_val", "Zero on nearly every row.")
rule("info", D, "py_addr_zip_rt|vit_flag|freeze_only_flag_dps", "Rarely set flag / route code; no protest use.")
rule("ag-inqletter", Y, "Prop_id|Prop_val_yr|Case_id|Letter_name|Create_dt", "Letters on informal inquiries; low value (62k rows).")

# Property Summary
rule("ps", N, "Prop_id|Prop_yr", KEY + " Prop_id is prop_id without leading zeros.")
rule("ps", N, "Geo_id|Owner_name|Addr_line1|Addr_line2|Addr_city|Addr_state|Zip|Situs_num|Situs_street_prefix|Situs_street|Situs_street_sufix|Situs_unit|Situs_Zip|Legal_desc", "Owner, mailing and property address in one row: the simplest source for client matching.")
rule("ps", N, "Yr_blt|Sq_ft|Land_acres|Sq_Ft_HVI|Class|SubClass|Num_Units|Bedrooms|Whole_Bath|Half_Bath|Imprv_Type|Ext_Wall|Roof|Foundation", "Main building traits flattened to one row: quick comps without joining the improvement files.")
rule("ps", N, "Market_val|Imprv_hstd_val|Land_hstd_val|Imprv_non_hstd_val|Land_non_hstd_val|AG_Use_val|AG_Market", "Current values.")
rule("ps", N, "Prior_Imp_HS_val|Prior_ Imp_non_HS_val|Prior LD_HS val|Prior LD non_HS_val|Prior AG_mkt|Prior Mkt val", "Prior-year values: the year-over-year change without a second file.")
rule("ps", N, "State_cd|Property_use_cd|Neighboorhood_Code|School|City|Exemptions|Last_Deed_Date|Agent_iD|Agent_name", "Category, use, neighborhood, units, exemptions and agent.")
rule("ps", Y, "Owner_id|Addr_line3|Country_cd|Zip+4|Dba_name|MAPSCO|Agent_Addr_L1|Agent_Addr_L2|Agent_Addr_city|Agent_Addr_state|Agent_Zip", "Secondary detail.")
rule("ps", D, "Agent_Addr_L3|Agent_CO_code|Agent_Zip+4|BPP Late_Rend_penalty", "Blank or constant.")

# ---------- apply ----------
KEYS = re.compile(r"(?i)^(prop_?id|property id|pacs property id|year|prop_val_yr|prop_yr|notice_yr|event year|case.?id|sale id|permit id)$")
def family(col, st):
    m = re.match(r"^(.*)_(exempt|qualify_yr|prorate_begin|prorate_end|amt|count|allocation_factor)$", col)
    if not m: return None
    code, kind = m.groups()
    if kind == "exempt":
        t = tcount(st["top"])
        return (Y, f"Rare exemption flag ({t:,} rows T in the latest snapshot); matters only for the tax estimate.") if t else (D, "Exemption flag that is F on every row.")
    if kind == "qualify_yr": return (D, "Year a rare exemption started; not needed.")
    if kind.startswith("prorate"): return (D, "Proration date for a mid-year exemption change; blank on almost every row.")
    if kind == "allocation_factor": return (D, "Exemption allocation factor; 1.0 / zero on nearly every row.")
    return (Y, "Exemption amount / count for a less common exemption; tax-bill detail only.")

SEED = {"at": int(time.time() * 1000), "files": {}}
tally = {N: 0, Y: 0, D: 0}
for fk, f in FILES.items():
    st = colstats(f["keys"]); rules = R.get(f["short"], {})
    out = SEED["files"].setdefault(fk, {})
    snaps = len(f["keys"])
    for col, s in st.items():
        empty = s["fill"] == 0
        const = len(s["vals"]) == 1 and s["fill"] == 1.0
        val = next(iter(s["vals"])) if const else None
        where = "in both snapshots" if snaps > 1 else "in this file"
        if empty or col.startswith("filler_") and col != "filler_134":
            dec = (D, f"Blank on every row {where}." if empty else "Layout filler.")
            if col in rules and rules[col][0] != D: dec = (D, f"Blank on every row {where}, so nothing to keep (would be {rules[col][0].capitalize()}: {rules[col][1]})")
        elif col in rules:
            dec = rules[col]
            if const and not KEYS.match(col) and dec[0] != D:
                dec = (D, f"Same value ({val!r}) on every row {where}. {dec[1]}")
        elif const and not KEYS.match(col):
            dec = (D, f"Same value ({val!r}) on every row {where}; carries no information.")
        else:
            dec = family(col, s) or (Y, f"Filled on {round(100*s['fill'])}% of rows; no current use in our protest or valuation work, keep available.")
        if KEYS.match(col) and dec[0] == Y and f["short"] not in ("ag-shared", "ag-inqletter"):
            dec = (N, KEY)
        out[col] = [dec[0], dec[1]]
        tally[dec[0]] += 1
json.dump(SEED, open("seed.json", "w"), ensure_ascii=False)
print(len(FILES), "files", sum(len(v) for v in SEED["files"].values()), "columns", tally)
# columns that fell through to the generic Maybe, for review
for fk, cols in SEED["files"].items():
    gen = [c for c, (s_, t) in cols.items() if t.startswith("Filled on")]
    if gen: print(fk, FILES[fk]["short"], gen)
