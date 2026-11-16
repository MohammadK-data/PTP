"""Bexar notes and Bexar-specific wording. Run after make_manifest.py and descriptions.py.
Facts were checked with DuckDB on 2026-11-16 (facts.py -> facts.json, plus profile.json)."""
import json
m = json.load(open("manifest.json")); ds = m["datasets"]; D = m["descriptions"]
P = json.load(open("profile.json"))
D.update({
 "entities": "Comma-separated codes of every taxing unit on the property (Bexar uses codes such as CAD, 06, 08, 09, 10, 11, 21, 57).",
 "geo_id": "Geographic id: BCAD's map number as shown on notices and the BCAD website (e.g. 04188-000-0012).",
 "imprv_type_cd": "Improvement type code (Bexar uses R residential, C commercial, M mobile home, DC, DM, T1 ...).",
 "ref_id1": "Reference id 1: a short BCAD code (DS05, SV14 ...), filled on about 5% of properties.",
 "ref_id2": "Reference id 2: a short BCAD code (R65C, P90C ...), filled on about 6% of properties.",
 "imprv_det_type_cd": "Segment type code (Bexar codes such as LA living area, LA2 second floor, OP open porch, AG attached garage, PA patio).",
 "entity_cd": "Taxing unit short code (Bexar uses CAD and 2-digit codes such as 06, 08, 09).",
 "state_cd_description": "BCAD description of the state code.",
 "prop_id": "BCAD property id; the key that joins every file. Zero-padded to 12 digits in the PACS files; the Agent Export and Property Summary write it without the zeros.",
})
for s in ("p26", "s26"):
    ds[f"{s}-entity"]["about"] = "Lookup of taxing unit ids to their short codes (CAD, 06, 08, 21 ...)."
PAD = "Every number is zero-padded text (<code>000000000070931</code>); the page profiles value columns as numbers, but load them as text or cast them yourself. <code>prop_id</code> is 12 digits with leading zeros."
def put(k, *n): ds[k]["notes"] = list(n)

put("p26-info", PAD,
 "795,468 rows, one per <code>prop_id</code> (no property has more than one owner row): 730,947 real, 45,005 personal, 18,178 mobile home and 1,338 mineral.",
 "<code>sup_num</code> is 0 on every row (preliminary roll). <code>arb_protest_flag</code> is T on only 1 row: the export ran March 28, before protests opened.",
 "<code>market_value</code>, <code>appraised_val</code> and <code>assessed_val</code> are exactly 100 on 11,470 rows: BCAD's minimum value, not a real appraisal. 123,493 rows have an appraisal agent (<code>ca_agent_id</code>) and 132,154 an ARB agent; no agent is written <code>000000000000</code>, and every id is in the Agents file. <code>deed_dt</code> is <code>MMDDYYYY</code> with no separators (1881–2026).")
put("s26-info", PAD,
 "794,985 rows, one per <code>prop_id</code>. The file is the whole roll as of supplement 298, not just changes: <code>sup_num</code> is 0 on 572,989 rows, 297 on 168,934, 296 on 19,828, 295 on 19,688 and 298 on 13,546.",
 "Against the March 28 prelim on the same property and owner, 165,639 rows have a different <code>market_value</code>; 19,017 March properties are gone and 19,500 are new.",
 "<code>arb_protest_flag</code> is T on only 78 rows: settled protests are cleared. 144,512 rows have an appraisal agent and 153,802 an ARB agent, all in the Agents file. 11,483 rows have the 100 minimum value. <code>deed_dt</code> (<code>MMDDYYYY</code>) runs up to a typo date in 2029.",
 "Version 8.0.0.34 adds the FEED (animal feed) exemption fields at the end of the record; they are F / blank everywhere.")
for s, rows in (("p26", "6,429,129"), ("s26", "6,425,219")):
    put(f"{s}-entinfo", PAD, f"{rows} rows: one per property, owner and taxing unit, about 8 units per property and up to 62. Every property on the roll has rows here.",
        "Value columns are the values for that unit, so they can differ from the roll (partial units, unit-specific exemptions). Most <code>*_amt</code> and every <code>*_allocation_factor</code> column is zero or 1.0 on almost every row.",
        "<code>filler_134</code> is unnamed in BCAD's layout but holds a T/F flag (T on 627 rows in October, 8 in March).")
    put(f"{s}-enttot", "170 taxing units, one row each. Totals are roll-wide per unit; many exemption columns are zero for every unit.")
    put(f"{s}-entity", "170 unit ids. Codes are CAD (the appraisal district) and 2-digit numbers; the names are in Unit totals (<code>entity_name</code>).")
put("p26-imprinfo", PAD, "1,131,482 improvements on 671,814 properties. <code>imprv_type_cd</code> R residential, C commercial, M mobile home are most rows.")
put("s26-imprinfo", PAD, "1,131,813 improvements on 672,003 properties.")
for s, n in (("p26", "3,246,627"), ("s26", "3,247,569")):
    put(f"{s}-imprdet", PAD, f"{n} segments. <code>imprv_det_type_cd</code> codes: LA living area, LA2 second floor, OP open porch, AG attached garage, PA patio. Decode them with <code>2026 Metadata - Improvement Detail Codes.xlsx</code>.",
        "<code>sketch_cmds</code> holds the legacy sketch drawing commands on 86% of rows (Bexar's export has no separate sketch file).")
    put(f"{s}-imprattr", PAD, "One row per attribute: <code>imprv_attr_desc</code> names it (foundation, roof, exterior wall ...) and <code>imprv_attr_cd</code> holds the code; see <code>Improvement attribute codes.xls</code>.")
put("p26-land", PAD, "772,129 land segments on 728,496 properties. <code>size_acres</code> carries 4 implied decimals (<code>00000000001377</code> = 0.1377 ac).")
put("s26-land", PAD, "772,079 land segments on 728,457 properties. <code>effective_front</code> and <code>effective_depth</code> are zero on 59% of segments.")
for s in ("p26", "s26"):
    put(f"{s}-mobile", PAD, "Mobile-home detail for improvements of type M. Title numbers are on only 3% of rows.")
    put(f"{s}-defer", "Over-65 / disabled tax deferrals: these owners are not paying tax now, so a protest saves them little today.")
put("p26-arb", "Only 400 rows, almost all older protests still open (<code>arb_status</code> OP for 2020–2025): the March export ran before 2026 protests were filed. The Agent Export's ARB file has every protest.")
put("s26-arb", "1,114 rows: 2026 protests still open or rescheduled at the October export (OP 495, CG 228, RO 67 ...) plus open prior-year cases. Use the Agent Export's ARB file for outcomes.")
put("p26-lawsuit", "Properties under a value lawsuit, tax years 2013–2025 (3,183 properties).")
put("s26-lawsuit", "Tax years 2013–2026, 3,847 properties.")
put("p26-arblaw", "18 properties in binding arbitration in March.")
put("s26-arblaw", "950 properties in binding arbitration by October (all 2026 cases).")
put("p26-agent", "11,111 agents. Every agent id on the property roll is here.")
put("s26-agent", "11,374 agents. Every agent id on the property roll is here.")
for s in ("p26", "s26"):
    put(f"{s}-abs", "Six lines break inside a description, so a few records read as two lines in the raw file (the ETL keeps them as they are).")
    put(f"{s}-header", "<code>pacs_version</code> / <code>export_version</code>: March is 8.51.2.6 / 8.0.0.33, October 8.52.0.14 / 8.0.0.34.")
    put(f"{s}-state", "The 2026 state-code table. Several codes are marked NOT IN USE.")
    put(f"{s}-country", "Country codes for mailing addresses.")
# Agent Export
AGN = "Converted from BCAD's pipe-delimited .txt by <code>etl/bexar_agent_export_to_csv.py</code> (NUL bytes removed, records split by line breaks joined back, values trimmed). <code>Property ID</code> has no leading zeros: pad to 12 digits to join the PACS files."
put("ag-propdata", AGN, "807,201 rows, one per property, all <code>Year</code> 2026. 12,287 Property IDs are not in the October 15 PACS roll (properties created or deleted after that export).", "<code>Valuation Method Code</code> says how BCAD valued the property (C cost, I income, A ARB, D distributed, S shared); the PACS export does not have it. <code>Zoning</code> is only here.")
put("ag-notice", AGN, "252,587 notices for 217,343 properties, all <code>Notice_yr</code> 2026: only properties that got a notice of appraised value. A property can have several notices (<code>Notice_num</code>).", "Timber columns are zero on every row.")
put("ag-comments", AGN, "676,829 comments. Long comments were written over several lines by BCAD and are joined into one value.")
put("ag-events", AGN, "4,460,518 events, all <code>Event Year</code> 2026.")
put("ag-shared", AGN, "421 properties that also sit in a neighboring appraisal district.")
put("ag-impr", AGN, "3,271,380 segment rows for 676,597 properties, all 2026: one row per improvement <b>detail</b>, so improvement-level columns repeat on each detail.", "<code>Effective Year Built</code> has typo years up to 2077 and zeros.")
put("ag-feat", AGN, "5,618,902 rows: <code>Feature Type</code> + <code>Feature Description</code> pairs per improvement detail.")
put("ag-income", AGN, "14,133 commercial properties with an income worksheet, one row each.")
put("ag-land", AGN, "942,063 land segments for 733,429 properties, all 2026. Adds unit prices and pricing tables that the PACS land file lacks. <code>Ag Loss</code> has a few negative values (down to -430).")
SALES = "<b>Confidential:</b> BCAD releases sales under Tex. Gov. Code 552.149(b); they may be used only as evidence at a protest hearing. Do not put sale prices in shared reports."
put("ag-sales", SALES, AGN, "789,886 rows for 772,880 sales (a sale can cover several properties); 777,264 have a price. Sale dates run 1971–September 24, 2026: 22,114 priced sales in 2025 and 8,455 so far in 2026.", "<code>Deed Date</code> and <code>Recorded Date</code> have placeholder and typo dates (1782, 9999-12-31).")
put("ag-saleland", SALES, AGN, "Land on each sold property as of the sale year. <code>Year</code> has 1 zero and runs up to 2027.")
put("ag-saleimpr", SALES, AGN, "Improvements on each sold property as of the sale year. <code>Year</code> has 3 zeros and runs up to 2027.")
put("ag-bpp", AGN, "146,650 BPP segments, all 2026. Decode <code>Segment_type</code> with <code>2026 Metadata - BPP Segment Codes.xlsx</code>.")
put("ag-bpplink", AGN, "45,501 links from a business personal property account to the real property it sits on. BCAD's layout lists a third column, <code>Personal_area</code>, which is not in the file.")
put("ag-permit", AGN, "1,827,963 permits going back decades. <code>Issue Date</code> has typo years (1812, 3038, 9999).", "Address fields are blank on two-thirds of permits; join to the property through Permit to property.")
put("ag-permitprop", AGN, "1,855,326 permit-to-property links.")
put("ag-arb", AGN, "2,744,831 protest rows from 1998 to 2026 (about 185,000–207,000 a year; 186,062 for 2026), plus 2 rows dated 2027. 4,746 rows repeat a property + year + case.", "2026 <code>Protest Status</code>: VA 86,356, ORD.A 41,887, ORD.A-BULK 23,017, EVA 12,967, PFNS 9,849. This is the file behind the Bexar protest scorecard.")
put("ag-arbletter", AGN, "5,347,290 letters on protest cases, 2001–2026.")
put("ag-protester", AGN, "2,796,724 rows. For 2026, <code>Protest by Type</code> is AG (agent) on 147,856 cases and OW (owner) on 37,177.", "4 rows have <code>Year</code> 0 and 23 rows have <code>Property ID</code> -1.")
put("ag-inq", AGN, "279,861 informal inquiries, 1998–2027 (16,516 for 2026), mostly exemption questions. Owner names are <code>CONFIDENTIAL OWNER</code> where protected.")
put("ag-inqletter", AGN, "62,167 letters on informal inquiries.")
put("ps26a", "BCAD ships this file <b>without a header row</b> (the header is in <code>2025-09-04 Property Summary File With Improvements Header line.csv</code>); the profiled copy in <code>output/</code> is the file with that header line put on top, nothing else changed.",
    "802,073 rows for 800,230 distinct <code>Prop_id</code>. <code>Market_val</code> and the other current-year values are the text <code>NULL</code> on 47,265 rows (prior-year values are filled): BCAD's layout says these values were still in progress.",
    "Text fields are wrapped in an extra pair of double quotes (<code>\"00002-000-0013\"</code>), and the first row's <code>Prop_id</code> starts with a byte-order mark. 5,959 Prop_ids are not in the October PACS roll.")
put("ps26s", "801,911 rows for 799,917 distinct <code>Prop_id</code>; every row has a numeric value (no <code>NULL</code>s left). 4,932 Prop_ids are not in the October 15 PACS roll.",
    "Text fields are wrapped in an extra pair of double quotes (<code>\"00002-000-0013\"</code>). Several headers have typos or spaces (<code>Neighboorhood_Code</code>, <code>Situs_street_sufix</code>, <code>Prior_ Imp_non_HS_val</code>).",
    "Lists such as <code>Imprv_Type</code>, <code>Bedrooms</code> and <code>Whole_Bath</code> hold one entry per improvement, separated by two spaces.")
for k, d in ds.items():
    if not d.get("notes"): print("no notes:", k)
json.dump(m, open("manifest.json", "w"), indent=1, ensure_ascii=False)
