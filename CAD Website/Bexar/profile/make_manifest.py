"""Build Bexar's manifest.json. PACS Appraisal Export datasets are copied from Travis's manifest (same PACS
export); the Agent Export and Property Summary datasets are Bexar-only. Notes are written by notes.py;
re-running this overwrites them."""
import json, copy
T = json.load(open("../../Travis/profile/manifest.json"))
CSV = {"opts": "delim=',', quote='\"', escape='\"', max_line_size=20000000"}
EXPORTS = [  # key prefix, run date, year-switch label, button label, compare label
    ("p26", "2026-03-28", "2026 prelim · Mar 28", "Mar 28 · prelim", None),
    ("s26", "2026-10-15", "2026 supp 298 · Oct 15", "Oct 15 · supp 298", "the Mar 28 prelim export"),
]
m = {k: copy.deepcopy(v) for k, v in T.items() if k not in ("datasets", "descriptions_by_set", "sources")}
m.update(
    title="Bexar Property Data Profile",
    eyebrow="Bexar Appraisal District · Website data exports",
    intro="Everything Bexar Appraisal District gives us as bulk files, from three exports: the PACS <b>Appraisal "
          "Export</b> (18 files, two snapshots: the March 28 first-notice preliminary roll and the October 15 export "
          "as of supplement 298), the <b>Agent Export</b> (21 CSV files, October 26) and the <b>Property Summary</b> "
          "file (March 28 and October 13). The year switch on every tab picks the snapshot. For each file you get "
          "its columns, data types, completeness, value distributions and 100 sample rows.",
    store_key="bexar-view",
    root="/Users/user2/PTP/CAD Website/Bexar/",
    foot="Generated {date}. Files were scanned in full with DuckDB. The PACS files are read from the gzipped CSVs "
         "that <code>etl/bexar_appraisal_export_etl.py</code> writes from the raw fixed-width .TXT files, using "
         "BCAD's own 8.0.34 layout workbook (the March export is 8.0.0.33, the same layout without the FEED fields); "
         "the Agent Export and Property Summary CSVs are read as published. \"Auto-detected on load\" is the type "
         "DuckDB assigns, and distinct counts there are approximate (HyperLogLog). \"Data type\" is inferred from the "
         "values: Code means digits stored as text with leading zeros.",
)
DROP = {"sketch", "sb12"}  # Bexar's export has no SKETCH_INFO or SB12 file
base = {k[4:]: v for k, v in T["datasets"].items() if k.startswith("c26-") and k[4:] not in DROP}
ds, by_set = {}, {}
for i, (pre, date, ylabel, blabel, cmp_label) in enumerate(EXPORTS):
    for short, d in base.items():
        d = copy.deepcopy(d)
        d["path"] = d["path"].replace("2026-07-18", date)
        d["encoding"] = "Gzipped CSV, UTF-8 (from fixed-width PACS .TXT)"
        if d["label"].endswith("certified"):
            d["label"] = blabel
        d["notes"] = []
        d.pop("compare", None); d.pop("compareLabel", None); d.pop("force", None)
        if i:
            d["compare"] = f"{EXPORTS[i-1][0]}-{short}"; d["compareLabel"] = cmp_label
        d["about"] = d["about"].replace("Denton's", "Bexar's").replace("Travis", "Bexar")
        ds[f"{pre}-{short}"] = d
    for k, v in T["descriptions_by_set"].items():
        if k.startswith("c26-") and k.split(":")[0][4:] not in DROP:
            by_set[f"{pre}-{k[4:]}"] = v
# renumber file buttons after dropping sketch / sb12
for pre, *_ in EXPORTS:
    ds[f"{pre}-mobile"]["label"] = "4 · Mobile homes"
    ds[f"{pre}-defer"]["label"] = ds[f"{pre}-defer"]["label"].replace("2 · ", "")

src_pacs = copy.deepcopy(T["sources"][0])
src_pacs.update(id="pacs", label="PACS Appraisal Export", sub="{n} files · every property in the county", start="s26-info",
    desc="PACS Appraisal Export from the BCAD website, saved in <code>CAD Website/Bexar/Data</code> (one zip per "
         "snapshot) and converted to gzipped CSV in <code>output/</code>. Fixed-width source files; every property in "
         "the county. <code>prop_id</code> is the BCAD property id used by every other Bexar file.")
groups = []
for g in src_pacs["groups"]:
    files = [k[4:] for k in g["years"][0]["datasets"] if k[4:] not in DROP]
    g["years"] = [{"label": e[2], "datasets": [f"{e[0]}-{f}" for f in files]} for e in EXPORTS]
    g["datasets"] = [k for y in g["years"] for k in y["datasets"]]
    g["desc"] = g.get("desc", "").replace("Tax ceiling history (SB12) and tax deferrals. Pick an export, then a file.",
                                           "Tax deferrals (over-65 or disabled).").replace("sketches and ", "")
    if g["id"] == "exempt": g["label"] = "Tax Deferrals"
    groups.append(g)
src_pacs["groups"] = groups

# ---- Agent Export (CSV, Oct 26) ----
AG = "Data/2026 Agent Export as of 2026-10-26 CSV/"
AGENT = [  # group id, group label, group desc, [(key, file, label, about)]
 ("ag-prop", "Property", "Property-level files from the Agent Export. All join on <code>Property ID</code> (PACS <code>prop_id</code>).", [
   ("ag-propdata", "FID_PropDataExport.csv", "1 · Property data", "One row per property and year: year built, living area, land size, region, neighborhood, map id, appraisers and comments."),
   ("ag-notice", "FID_ApprNoticeExport.csv", "2 · Appraisal notices", "One row per appraisal notice: this year's and last year's appraised, assessed, market, land, improvement, ag and cap values, and exemptions."),
   ("ag-comments", "FID_CommentsExport.csv", "3 · Comments", "Free-text appraiser and property comments, one row per comment."),
   ("ag-events", "FID_EventsExport.csv", "4 · Events", "Property history events: date, event type code and description (value changes, e-file, exemption actions ...)."),
   ("ag-shared", "FID_SharedPropExport.csv", "5 · Shared properties", "Properties that sit in two counties, with the other appraisal district's code and property id."),
 ]),
 ("ag-impr", "Improvements & Income", "Buildings, their segments and features, and income-approach records. Join on <code>Property ID</code>, then <code>Improvement ID</code> / <code>Detail ID</code>.", [
   ("ag-impr", "FID_ImprovementExport.csv", "1 · Improvements", "One row per improvement segment (detail): improvement type, state code, year built, depreciation, class, method, unit price, area and values."),
   ("ag-feat", "FID_ImprovementFeaturesExport.csv", "2 · Improvement features", "One row per feature of an improvement segment: feature type (exterior wall, roof, use category ...) and its code."),
   ("ag-income", "FID_IncomeExport.csv", "3 · Income", "Income-approach records for commercial properties: economic area, property type, class, building and net rentable area, property name."),
 ]),
 ("ag-land", "Land", "Land segments from the Agent Export, joined on <code>Property ID</code>.", [
   ("ag-land", "FID_LandExport.csv", "Oct 26 · agent export", "One row per land segment: state code, land type, size in sq ft and acres, pricing method and table, unit price, market and ag values."),
 ]),
 ("ag-sales", "Sales", "Sales and the land and improvements on the property at the time of sale. Join on <code>Sale ID</code> and <code>Property ID</code>.", [
   ("ag-sales", "FID_SalesExport.csv", "1 · Sales", "One row per property and sale: buyer, seller, deed, sale price and date, adjustments, confirmation, financing and sale class."),
   ("ag-saleland", "FID_SalesLandExport.csv", "2 · Sale land", "Land segments on each sold property, as of the sale."),
   ("ag-saleimpr", "FID_SalesImprovementExport.csv", "3 · Sale improvements", "Improvements on each sold property, as of the sale."),
 ]),
 ("ag-bpp", "Business Personal Property", "Business personal property (BPP) rendition segments and the link from each BPP account to its real property.", [
   ("ag-bpp", "FID_BPPExport.csv", "1 · BPP segments", "One row per BPP segment: segment type, value, quality, density, area and late-rendition penalty."),
   ("ag-bpplink", "FID_BPPRealLinkExport.csv", "2 · BPP to real link", "Each business personal property account and the real property it sits on."),
 ]),
 ("ag-permit", "Building Permits", "Building permits and the properties they apply to. Join through <code>Permit ID</code>.", [
   ("ag-permit", "FID_BuildingPermitExport.csv", "1 · Permits", "One row per permit: issuer, number, dates, type, address, builder, value, appraiser and completion status."),
   ("ag-permitprop", "FID_BuildingPermitPropertyExport.csv", "2 · Permit to property", "Links each permit to the properties it covers."),
 ]),
 ("ag-arb", "Protests & Inquiries", "ARB protests, informal inquiries, protesters and the letters sent on them, every year on file. Join on <code>Property ID</code> + <code>Year</code> + <code>Case ID</code>.", [
   ("ag-arb", "FID_ARBExport.csv", "1 · ARB protests", "One row per protest case: owner, agent, protest type, status and reasons, hearing docket, panel, motions, values before and after, and final decision."),
   ("ag-arbletter", "FID_ARBLetterHistory.csv", "2 · ARB letters", "Letters sent on each protest case, with date and time."),
   ("ag-protester", "FID_ProtesterExport.csv", "3 · Protesters", "Who filed each protest case: name, type (owner, agent ...) and whether they are the primary protester."),
   ("ag-inq", "FID_ARBInquiryExport.csv", "4 · Inquiries", "One row per informal inquiry case: type, status, reason, comments, appraiser meeting and values before and after."),
   ("ag-inqletter", "FID_ARBInquiryLetterHistory.csv", "5 · Inquiry letters", "Letters sent on each inquiry case."),
 ]),
]
src_ag = {"id": "agent", "label": "Agent Export", "sub": "{n} CSV files · every property in the county", "start": "ag-propdata",
  "desc": "BCAD's Agent Export as of October 26, 2026, saved as CSV in <code>Data/2026 Agent Export as of 2026-10-26 CSV</code>. "
          "Despite the name it covers every property in the county, and several files reach back to the 1990s. "
          "<code>Property ID</code> is the PACS <code>prop_id</code>. The Non-Agent Export of October 21 carries the same "
          "files as headerless pipe-delimited text and is not profiled separately.", "groups": []}
for gid, glabel, gdesc, files in AGENT:
    for key, f, label, about in files:
        ds[key] = {"path": AG + f, "read": CSV, "label": label, "about": about, "encoding": "CSV, UTF-8", "notes": []}
    keys = [f[0] for f in files]
    src_ag["groups"].append({"id": gid, "label": glabel, "desc": gdesc, "datasets": keys,
                             "years": [{"label": "2026 · Oct 26", "datasets": keys}]})

# ---- Property Summary ----
PS = [("ps26a", "output/2026 Property Summary Export as of 2026-03-28__1st Notice Run Preliminary (with header).csv",
       "2026 prelim · Mar 28", None),
      ("ps26s", "Data/2026 Property Summary Export as of 2026-10-08_Sup 298/2026 Property Summary Export as of 2026-10-13_Sup 298.csv",
       "2026 supp 298 · Oct 13", "ps26a")]
for key, path, label, cmp in PS:
    ds[key] = {"path": path, "read": CSV, "label": label, "encoding": "CSV, UTF-8 with BOM",
               "about": "One row per property: owner and mailing address, situs, values (homestead and non-homestead, prior year), "
                        "school and city, exemptions, main building traits (type, wall, roof, foundation, beds, baths), class, agent.",
               "notes": []}
    if cmp: ds[key].update(compare=cmp, compareLabel="the Mar 28 prelim file")
src_ps = {"id": "summary", "label": "Property Summary", "sub": "{n} files · one row per property", "start": "ps26s",
  "desc": "BCAD's Property Summary Export, a flat one-row-per-property CSV (layout of 2025-09-04), in two snapshots.",
  "groups": [{"id": "summary", "label": "Property Summary", "desc": "The flat Property Summary file. Joins to the PACS roll on <code>Prop_id</code>.",
              "datasets": ["ps26a", "ps26s"], "years": [{"label": "2026 prelim · Mar 28", "datasets": ["ps26a"]},
                                                        {"label": "2026 supp 298 · Oct 13", "datasets": ["ps26s"]}]}]}
m["datasets"], m["descriptions_by_set"] = ds, by_set
m["sources"] = [src_pacs, src_ag, src_ps]
json.dump(m, open("manifest.json", "w"), indent=1, ensure_ascii=False)
print(len(ds), "datasets")
