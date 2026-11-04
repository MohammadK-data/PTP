"""Write the per-dataset notes into manifest.json (facts checked with DuckDB on 2026-11-04)."""
import json
m = json.load(open("manifest.json")); ds = m["datasets"]
PAD = "Every number is zero-padded text (<code>000000000070931</code>); the page profiles value columns as numbers, but load them as text or cast them yourself. <code>prop_id</code> is 12 digits with leading zeros."
N = {}
def put(k, *notes): N[k] = list(notes)
# property roll
info = {"p26a": (59620, 59429, 191, 20, 9784, 10794), "p26b": (59659, 59453, 206, 13376, 12399, 13754),
        "c26": (59536, 59329, 207, 84, 12508, 13823), "s26": (59549, 59333, 216, 5, 12437, 13752)}
for k, (rows, props, extra, arbT, ca, arb) in info.items():
    n = [PAD, f"{rows:,} rows for {props:,} distinct <code>prop_id</code>: properties with several owners (undivided interest) have one row per owner ({extra} extra rows), so the key is <code>prop_id</code> + <code>py_owner_id</code>."]
    if k == "s26":
        n.append("The file is the whole roll, not just changes: <code>sup_num</code> is 0 on 58,482 rows (unchanged since certification), 3 on 10, 4 on 54, 5 on 531 and 6 on 472. <code>sup_action</code> is blank on every row. <code>arb_protest_flag</code> is T on only 5 rows (84 at certification).")
    elif k == "p26b":
        n.append("<code>sup_num</code> is 0 on every row (preliminary roll). <code>arb_protest_flag</code> is T on 13,376 rows: this export was taken during protest season (20 in March, 84 at certification).")
    else:
        n.append(f"<code>sup_num</code> is 0 on every row and <code>sup_action</code>/<code>sup_cd</code> are blank ({'preliminary' if k=='p26a' else 'certified'} roll). <code>arb_protest_flag</code> is T on {arbT:,} rows.")
    n.append(f"No agent is written <code>000000000000</code>, not blank: {ca:,} rows have an appraisal agent (<code>ca_agent_id</code>) and {arb:,} an ARB agent; every one of them is in the Agents file. <code>legal_acreage</code> and <code>land_acres</code> carry 4 implied decimals.")
    tail = ("The March prelim is PACS layout 8.0.0.30, which the 8.0.30 field list covers exactly, so there is no <code>unmapped_tail</code>." if k == "p26a"
            else f"<code>unmapped_tail</code> holds the fields PACS {'8.0.32' if k=='p26b' else '8.0.33'} adds past the 8.0.30 layout (6 distinct values, mostly zeros and F flags); the {'May' if k=='p26b' else 'July and October'} file{'s are' if k!='p26b' else ' is'} wider than March's.")
    n.append(f"<code>geo_id</code> is the dashed Rockwall map number (<code>4358-000F-0037-00-0R</code>); 5 rows have none, and business personal property uses other shapes (<code>7600-000010</code>, <code>243767</code>). <code>deed_dt</code> (<code>MM-DD-YYYY</code>) runs 1962–2026. " + tail)
    put(f"{k}-info", *n)
# taxing units
ent = {"p26a": (249285, 18), "p26b": (249698, 17), "c26": (249401, 17), "s26": (249479, 17)}
for k, (rows, mx) in ent.items():
    n = [PAD, f"{rows:,} rows: one per property, owner and taxing unit, about 4.2 units per property and up to {mx}. Every <code>prop_id</code> + <code>owner_id</code> pair matches the property roll."]
    if k == "s26":
        n.append("Against the certified export on the same property, owner and unit, 4,464 rows have a new <code>sup_num</code> and 2,301 a new <code>taxable_val</code>.")
    else:
        n.append("Value columns here are the values for that unit, so they can differ from the roll (partial units, unit-specific exemptions). Most <code>*_amt</code> and <code>*_allocation_factor</code> columns are zero on almost every row.")
    put(f"{k}-entinfo", *n)
tot = {"p26a": (63, 83, 105), "p26b": (63, None, 106), "c26": (61, 81, 106), "s26": (62, 78, 111)}
import json as _j
prof = _j.load(open("profile.json"))
for k, (units, _, ids) in tot.items():
    z = sum(1 for c in prof[f"{k}-enttot"]["columns"] if c.get("stats") and c["stats"]["zeros"] == c["nonnull"] > 0)
    put(f"{k}-enttot", f"{units} taxing units, one row each. {z} total columns (timber, mineral, auto, abatements ...) are zero for every unit.")
    put(f"{k}-entity", f"{ids} unit ids, but only {units} have a row in Unit totals; the other {ids-units} have no property on the roll. Codes are letters, not numbers: <code>GRW</code> Rockwall County, <code>SRW</code> Rockwall ISD, <code>CRW</code> City of Rockwall, <code>CAD</code> the appraisal district.")
# improvements
imp = {"p26a": 72479, "p26b": 72472, "c26": 72472, "s26": 72476}
newimp = {"p26b": "21 <code>imprv_id</code>s are new since March", "c26": "only 4 <code>imprv_id</code>s are new since May", "s26": "1,358 <code>imprv_id</code>s are new since certification (properties re-saved in a supplement)"}
for k, n in imp.items():
    s = f"One row per <code>imprv_id</code> ({n:,}, all distinct), all on the property roll. <code>imprv_type_cd</code> is a letter: R 45,300 or so, I about 23,300, C 2,300 and M 1,500 (mobile homes). <code>omitted_imprv_val</code> is zero on every row."
    extra = [f"Unlike Travis, ids are mostly stable between Rockwall exports: {newimp[k]}. Still compare snapshots on <code>prop_id</code> to be safe."] if k in newimp else []
    put(f"{k}-imprinfo", s, *extra)
    put(f"{k}-imprdet", "Area and value carry 6 decimals (<code>00002218.000000</code>). <code>sketch_cmds</code> is blank on every row; the drawings are in the Sketches file. Every row matches an improvement on <code>prop_id</code> + <code>imprv_id</code>.",
        "<code>prop_val_yr</code> is <code>2026</code> here but <code>02026</code> on the property roll; compare it as a number.")
    put(f"{k}-imprattr", "One row per attribute; pivot <code>imprv_attr_desc</code> to get one column per attribute. The common ones are Roof Style, Exterior Wall, Heating/Cooling, Foundation, Fireplace, Plumbing and Number of Bedrooms.")
sk = {"p26a": (187045, 11469), "p26b": (186979, 11484), "c26": (186962, 11487), "s26": (188631, 11068)}
for k, (leg, enh) in sk.items():
    put(f"{k}-sketch", f"Tab-separated in the source, with ids not zero-padded: pad <code>prop_id</code> and <code>imprv_det_id</code> to 12 digits to join. All {leg:,} Legacy sketches match an improvement detail after padding.",
        f"{enh:,} Enhanced sketches have <code>sketch_json</code> (up to 6.6 MB per row) and a blank <code>imprv_det_id</code>; they attach to the improvement, not a segment. Raise your CSV reader's maximum line size to load them. The file is about 1.8 GB raw, the largest in the export.")
mh = {"p26a": (1504, 1456), "p26b": (1201, 1186), "c26": (1200, 1185), "s26": (1200, 1185)}
for k, (r, p) in mh.items():
    n = [f"{r:,} rows for {p:,} properties, all on the property roll. Serial and HUD numbers fill <code>_2</code>/<code>_3</code> only for multi-section homes (7 rows have a third)."]
    if k == "p26b": n.append("303 fewer rows than March (1,504): the 303 March rows that are gone from May on had no make, model or serial number.")
    put(f"{k}-mobile", *n)
# land
land = {"p26a": (56667, 41698), "p26b": (56677, 41709), "c26": (56677, 107), "s26": (56683, 107)}
for k, (n, z) in land.items():
    if k.startswith("p"):
        nn = [f"<code>size_acres</code> is rounded to <b>whole acres</b> in the prelim exports (<code>00000000000012</code> = 12 acres; the same segment is <code>00000000121462</code> = 12.1462 acres from July on), so {z:,} lots under half an acre show 0. Use <code>size_square_feet</code> (whole square feet) for lot size. One row per <code>land_seg_id</code> ({n:,}), all on the property roll."]
    else:
        nn = [f"<code>size_acres</code> carries 4 implied decimals (<code>00000000002290</code> = 0.229 acres); in the March and May prelims it was whole acres. <code>size_square_feet</code> is whole square feet. One row per <code>land_seg_id</code> ({n:,}), all on the property roll; {z} rows have zero acres."]
    nn.append("<code>effective_front</code>/<code>effective_depth</code> are a run of 14 zeros on about 25,800 rows. <code>ag_ls_method</code> is filled only on the ~1,600 agricultural segments.")
    if k == "s26": nn.append("1,051 <code>land_seg_id</code>s are new since certification (re-saved properties); compare snapshots on <code>prop_id</code>.")
    put(f"{k}-land", *nn)
# SB12, deferrals
sb = {"p26a": (30225, 9948, 19905, 9964, 356), "p26b": (30152, 9922, 19854, 9938, 360), "c26": (30178, 9929, 19868, 9945, 365), "s26": (30229, 9957, 19892, 9972, 365)}
for k, (r, p, a, b, c) in sb.items():
    put(f"{k}-sb12", f"Tab-separated in the source, with <code>prop_id</code> not zero-padded: all {r:,} rows match the roll once padded to 12 digits ({p:,} properties).",
        f"Three record types: {a:,} <code>SB12</code> (one per tax year 2025–2026), {b:,} <code>SUMMARY</code> and {c} <code>NEW_VALUE</code>. <code>col_16</code> is <code>0.6169</code> on every SB12 row, for both school districts (SRW and SRC). The ETL could not identify <code>col_11</code>–<code>col_18</code>; their tooltips are best guesses.")
dfr = {"p26a": 109, "p26b": 112, "c26": 112, "s26": 111}
for k, n in dfr.items():
    put(f"{k}-defer", f"{n} deferrals. Dates are <code>MM-DD-YYYY</code>; <code>deferral_end_date</code> is blank on every row{' and so is <code>last_change_date</code>' if k=='p26a' else ''}.")
# protests
put("p26a-arb", "Only 22 rows, all 2026 protests filed by mid-March. Rockwall status codes are spelled out (<code>EF</code> 9, <code>WS</code> 4, <code>O-LAND</code> 3 ...). <code>ref_id1</code> is blank on every row.")
put("p26b-arb", "13,441 rows, 13,436 of them 2026 protests and 5 from 2022–2025: protest season was under way at this export. Top statuses: <code>EF-OFF</code> 7,778, <code>EF</code> 2,507, <code>O-AGT</code> 869, <code>2NAOA</code> 655.",
    "Every <code>prop_id</code> is on the property roll; <code>ref_id1</code> is filled on only 10 rows.")
put("c26-arb", "Only 97 rows (13,441 in May): the file lists protests still open at export time, so settled ones drop out. 84 are 2026 protests and 13 from 2022–2025.",
    "Top statuses: <code>O-RESCH-WO</code> 28, <code>LP</code> 22, <code>O-AGT</code> 14, <code>O-BPP</code> 9, plus 25.25(c) correction motions (<code>25.25C-O</code>/<code>-S</code>). 5 rows have a <code>prop_id</code> not on the property roll.")
put("s26-arb", "30 rows still open: 20 for 2026 and 10 from 2022–2025, mostly 25.25 correction motions (<code>25.25C-O</code> 8, <code>25.25C-S</code> 4) and agent hearings (<code>O-AGT</code> 8). 4 rows have a <code>prop_id</code> not on the current roll.")
for k in ("p26a", "p26b", "c26", "s26"):
    put(f"{k}-lawsuit", "396 rows for tax years 2016–2023 only, and the file is byte-for-byte the same in all four 2026 exports: no 2024–2026 suits are listed, so this file does not reflect current litigation.")
    put(f"{k}-arblaw", "Empty: the source <code>ARBITRATION_LAWSUIT.TXT</code> is 0 bytes in every Rockwall export (Denton and Travis fill it). The columns come from the layout.")
agents = {"p26a": 3104, "p26b": 3135, "c26": 3694, "s26": 3695}
for k, n in agents.items():
    put(f"{k}-agent", f"{n:,} agents. <code>agent_id</code> is 12-digit zero-padded and joins to <code>ca_agent_id</code>, <code>arb_agent_id</code> and <code>entity_agent_id</code> on the property roll; ids run from <code>000000097557</code> up. <code>agent_zip_rt</code> is blank on every row.")
N["c26-agent"].append("559 more agents than in May (3,135): agents appointed during protest season.")
# lookups
for k in ("p26a", "p26b", "c26", "s26"):
    nabs = 2095 if k == "s26" else 2056
    put(f"{k}-abs", f"{nabs:,} abstract and subdivision codes{' (39 more than at certification)' if k=='s26' else ''}. 48 names contain commas or apostrophes, so read the CSV with <code>\"</code> as the quote character.")
    put(f"{k}-state", "288 Rockwall state codes (much finer than Travis's 45, e.g. <code>10A</code> cell site and tower); <code>ptd_state_cd</code> maps them to 28 Comptroller categories. Same file in all four exports.")
    put(f"{k}-country", "246 country codes; the same file in all four exports.")
hdr = {"p26a": ("0000", "03/16/2026 10:24", "8.0.0.30", "preliminary roll"), "p26b": ("0000", "05/26/2026 15:39", "8.0.0.32", "preliminary roll"),
       "c26": ("0000", "07/13/2026 14:43", "8.0.0.33", "certified roll"), "s26": ("0006", "10/09/2026 14:56", "8.0.0.33", "supplement 6")}
for k, (s, r, v, w) in hdr.items():
    n = f"Identifies the export: <code>supplement_number</code> is <code>{s}</code> ({w}), run {r}, PACS 8.1.33.23, export version {v}."
    if k == "s26": n += " The source folder is named <i>RCAD ADJ 2026 (RC6) APP ROLL 100726</i>; the header run date is October 9."
    if k in ("c26", "s26"): n += " The folder ships <code>Legacy8.0.32-AppraisalExportLayout.pdf</code>, one version behind the data."
    put(f"{k}-header", n)
for k, v in N.items(): ds[k]["notes"] = v
missing = [k for k in ds if k not in N]
assert not missing, missing
json.dump(m, open("manifest.json", "w"), indent=1, ensure_ascii=False)
print(len(N), "datasets noted")
