"""Add the flattened JSON special-export tables (output/json_<date>/<table>.csv.gz) to manifest.json.

Each JSON list becomes one dataset per export: jc-* for the certified export (Jul 19 file), jo-* for the Oct 6 file.
Tables are grouped into tabs by their top-level path, with the same file order in both exports so the
review's decisions line up. Prints the new keys, for profile_files.py.

Usage: python3 -I add_json_datasets.py
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE.parent / "output"
EXPORTS = [("jc", "json_2026-07-19", "Certified JSON · Jul 19"), ("jo", "json_2026-10-06", "Supplemental JSON · Oct 6")]
GROUPS = [
    ("json-prop", "JSON · Property", "Top-level property fields and the one-to-few lists that describe the property.",
     ("property", "propertyIdentification", "propertyLegalDescription", "propertyCharacteristics", "propertyProfile",
      "situses", "tags", "smartgroups", "links")),
    ("json-own", "JSON · Owners & Taxing Units", "Owners, their agents, exemptions, values and taxable values per taxing unit.",
     ("owners", "taxingunits")),
    ("json-val", "JSON · Valuations", "Valuations and the cost-approach detail behind them: improvements, segments, features and land.",
     ("valuations",)),
    ("json-hist", "JSON · History", "Deeds, sales, permits, inspections, notes and events recorded on the property.",
     ("deeds", "sales", "permits", "inspections", "notes", "events")),
    ("json-appeal", "JSON · Appeals", "Protests (appeals) with hearing, decision and value details.", ("appeals",)),
]
CSV = {"opts": "delim=',', quote='\"', escape='\"', max_line_size=200000000"}


def short(table):
    s = table.replace("valuations.details.cost-local", "val-cost").replace("valuations", "val")
    return re.sub(r"[^a-z0-9-]+", "-", s.replace(".", "-").lower()).strip("-")


def group_of(table):
    top = table.split(".")[0]
    for gid, *_, tops in GROUPS:
        if top in tops:
            return gid
    return "json-other"


def main():
    m = json.loads((HERE / "manifest.json").read_text())
    meta = {pre: json.loads((OUT / d / "_tables.json").read_text()) for pre, d, _ in EXPORTS}
    names = sorted(set().union(*(x["tables"] for x in meta.values())))
    ds, desc = m["datasets"], m.setdefault("descriptions", {})
    desc.setdefault("pID", "Travis CAD property id; the same number as prop_id in the appraisal export (unpadded).")
    desc.setdefault("pYear", "Appraisal (tax) year.")
    order = {g[0]: i for i, g in enumerate(GROUPS)}
    tops = {top: i for g in GROUPS for i, top in enumerate(g[3])}
    names.sort(key=lambda t: (order.get(group_of(t), 99), tops.get(t.split(".")[0], 99), t))
    new = []
    for pre, folder, _ in EXPORTS:
        for t in names:
            k = f"{pre}-{short(t)}"
            leaf = t.rsplit(".", 1)[-1]
            parents = [p + "_i" for p in t.split(".")[:-1] if p not in ("details", "cost-local")]
            ds[k] = {"path": f"output/{folder}/{t}.csv.gz", "read": CSV, "json_path": t,
                     "label": " › ".join(x for x in t.split(".") if x not in ("details", "cost-local")) if t != "property" else "property (top level)",
                     "about": ("One row per property: its top-level fields." if t == "property" else
                               f"One row per item in the {t.replace('.', ' › ')} list of each property. Joins back on pID"
                               + (f" and {', '.join(parents)}" if parents else "") + "."),
                     "encoding": f"Gzipped CSV, UTF-8 (flattened from {meta[pre]['source']})"}
            if pre == "jo":
                ds[k]["compare"] = f"jc-{short(t)}"
            new.append(k)
            desc.setdefault(f"{leaf}_i", f"Position of the row in its {leaf} list (0 = first); with pID it links child rows to this row.")
    src = m["sources"][0]
    src["groups"] = [g for g in src["groups"] if not g["id"].startswith("json-")]
    for gid, label, gdesc, _ in GROUPS + [("json-other", "JSON · Other", "Other lists in the JSON export.", ())]:
        tabs = [t for t in names if group_of(t) == gid]
        if not tabs:
            continue
        years = [{"label": ylabel, "datasets": [f"{pre}-{short(t)}" for t in tabs]} for pre, _, ylabel in EXPORTS]
        src["groups"].append({"id": gid, "label": label, "desc": gdesc,
                              "datasets": [k for y in years for k in y["datasets"]], "years": years})
    (HERE / "manifest.json").write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print(" ".join(new))


if __name__ == "__main__":
    main()
