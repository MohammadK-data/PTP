"""One-off: build Rockwall's manifest.json from Travis's (same PACS files). Notes and county-specific text are
filled in by hand afterwards; re-running overwrites them."""
import json, copy
T = json.load(open("../../Travis/profile/manifest.json"))
EXPORTS = [  # key prefix, run date, year-switch label, button label for single-file tabs, compare label
    ("p26a", "2026-03-16", "2026 prelim · Mar 16", "Mar 16 · prelim", None),
    ("p26b", "2026-05-26", "2026 prelim · May 26", "May 26 · prelim", "the Mar 16 prelim export"),
    ("c26", "2026-07-13", "2026 certified · Jul 13", "Jul 13 · certified", "the May 26 prelim export"),
    ("s26", "2026-10-09", "2026 supp 6 · Oct 9", "Oct 9 · supp 6", "the Jul 13 certified export"),
]
m = {k: copy.deepcopy(v) for k, v in T.items() if k not in ("datasets", "descriptions_by_set", "sources")}
m.update(
    title="Rockwall Property Data Profile",
    eyebrow="Rockwall Central Appraisal District · PACS appraisal export files",
    intro="Everything in Rockwall CAD's 2026 PACS <b>Appraisal Export</b>, downloaded from the CAD website: 20 files "
          "per export, in four snapshots — the <b>preliminary</b> rolls exported March 16 and May 26, the "
          "<b>certified</b> roll exported July 13 and <b>supplement 6</b> exported October 9. The year switch on "
          "every tab picks the snapshot. For each file you get its columns, data types, completeness and value "
          "distributions.",
    store_key="rockwall-view",
    root="/Users/user2/PTP/CAD Website/Rockwall/",
    foot="Generated {date}. Files were scanned in full with DuckDB from the gzipped CSVs that "
         "<code>etl/rockwall_appraisal_export_etl.py</code> writes from the raw PACS .TXT files, using Denton's "
         "8.0.30 layout (Rockwall publishes the same PACS export; fields added in 8.0.32 and 8.0.33 stay in "
         "<code>unmapped_tail</code>); \"Auto-detected on load\" is the type DuckDB assigns, and distinct counts "
         "there are approximate (HyperLogLog). \"Data type\" is inferred from the values: Code means digits "
         "stored as text with leading zeros.",
)
base = {k[4:]: v for k, v in T["datasets"].items() if k.startswith("c26-")}
ds, by_set = {}, {}
for i, (pre, date, ylabel, blabel, cmp_label) in enumerate(EXPORTS):
    for short, d in base.items():
        d = copy.deepcopy(d)
        d["path"] = d["path"].replace("2026-07-18", date)
        if d["label"].endswith("certified"):
            d["label"] = blabel
        d["notes"] = []
        d.pop("compare", None); d.pop("compareLabel", None)
        if i:
            d["compare"] = f"{EXPORTS[i-1][0]}-{short}"
            d["compareLabel"] = cmp_label
        ds[f"{pre}-{short}"] = d
    for k, v in T["descriptions_by_set"].items():
        if k.startswith("c26-"):
            by_set[f"{pre}-{k[4:]}"] = v
ds["c26-state"]["about"] = ds["c26-state"]["about"].replace("Denton's", "Rockwall's")
for pre, *_ in EXPORTS:
    ds[f"{pre}-state"]["about"] = ds[f"{pre}-state"]["about"].replace("Denton's", "Rockwall's")
m["datasets"], m["descriptions_by_set"] = ds, by_set
src = copy.deepcopy(T["sources"])
for s in src:
    s["start"] = "s26-info"
    s["desc"] = s["desc"].replace("Travis", "Rockwall")
    for g in s["groups"]:
        files = [k[4:] for k in g["years"][0]["datasets"]]
        g["years"] = [{"label": e[2], "datasets": [f"{e[0]}-{f}" for f in files]} for e in EXPORTS]
        g["datasets"] = [k for y in g["years"] for k in y["datasets"]]
m["sources"] = src
json.dump(m, open("manifest.json", "w"), indent=1, ensure_ascii=False)
print(len(ds), "datasets")
