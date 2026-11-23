"""Build the single-page data profile from a manifest and the profiler outputs.

Usage: python build_page.py manifest.json profile.json [api.json|-] out.html [--allow-missing]

- Every file dataset in the manifest must be in profile.json (run profile_files.py first).
- Each dataset's `sample` (100 random rows from profile_files.py) is shown as a "Sample rows" table.
- Placeholder datasets ({"placeholder": true}) render a "Not provided on the website yet / coming soon" card.
- API sets come from api.json (profile_api.py); manifest datasets with the same api-* key add notes/labels.
- Every column must have a description (manifest descriptions / descriptions_by_set / descriptions_by_prefix);
  missing ones are listed and the build fails unless --allow-missing.
"""
import datetime, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
args = [a for a in sys.argv[1:] if not a.startswith("--")]
allow_missing = "--allow-missing" in sys.argv
mpath, ppath, apath, out = args
M = json.load(open(mpath))
P = json.load(open(ppath))
API = json.load(open(apath)) if apath != "-" and os.path.exists(apath) else None
max_year = M.get("max_year", 2026)

META = ("label", "about", "encoding", "compare", "compareLabel", "renames", "notes")


def prep(v):
    v = dict(v)
    for c in v["columns"]:
        c["distinct"] = min(c["distinct"], c["nonnull"])
        if c["type"] == "Date" and c.get("hist") and "future" not in c.get("stats", {}):
            c["stats"]["future"] = sum(n for yr, n in c["hist"]["bins"] if isinstance(yr, int) and yr > max_year)
    v.pop("rej_sample", None)
    return v


SETS, missing_profiles = {}, []
for k, d in M["datasets"].items():
    if k.startswith("api-"):
        continue
    if d.get("placeholder"):
        SETS[k] = dict(label=d.get("label", "Not available yet"), placeholder=True, rows=0, columns=[], size=0, file="",
                       about=d.get("about", "Not provided on the website yet. Coming soon."))
        continue
    if k not in P:
        missing_profiles.append(k)
        continue
    SETS[k] = dict(prep(P[k]), **{f: d[f] for f in META if f in d})
    SETS[k].setdefault("label", k)
    SETS[k].setdefault("compare", None)
if missing_profiles:
    sys.exit(f"Not profiled yet: {missing_profiles}. Run profile_files.py first.")
no_sample = [k for k, v in SETS.items() if not v.get("placeholder") and v["rows"] and "sample" not in v]
if no_sample:
    print(f"No sample rows yet (page shows none for these): {no_sample}. Run profile_files.py --sample-only.")

if API:
    SETS.update(API["sets"])
    for k, d in M["datasets"].items():
        if k.startswith("api-") and k in SETS:
            for f in META:
                if f in d:
                    SETS[k][f] = d[f]

# descriptions
D, BYSET, BYPRE = M.get("descriptions", {}), M.get("descriptions_by_set", {}), M.get("descriptions_by_prefix", {})
missing = []
for k, v in SETS.items():
    for c in v["columns"]:
        n, leaf = c["name"], c["name"].split(".")[-1]
        pre = k.split("-")[0]
        c["desc"] = BYSET.get(f"{k}:{n}") or BYPRE.get(f"{pre}:{n}") or D.get(n) or BYSET.get(f"{k}:{leaf}") or D.get(leaf)
        if not c["desc"]:
            missing.append(f"{k}:{n}")
if missing:
    print(f"{len(missing)} columns have no description:\n  " + "\n  ".join(missing))
    if not allow_missing:
        sys.exit("Add them to the manifest (descriptions / descriptions_by_set / descriptions_by_prefix), or pass --allow-missing.")

# sources and groups
sources = []
for s in M["sources"]:
    s = dict(s)
    if s.get("groups") == "from_api":
        if not API:
            continue
        s["groups"] = API["groups"]
    for g in s["groups"]:
        if g.get("years") and not g.get("datasets"):
            g["datasets"] = [k for y in g["years"] for k in y["datasets"]]
        for k in g["datasets"]:
            assert k in SETS, f"group {g['id']} lists unknown dataset {k}"
    n = sum(1 for g in s["groups"] for k in g["datasets"] if not SETS[k].get("placeholder"))
    s["sub"] = s.get("sub", "").replace("{n}", str(n))
    s.setdefault("start", next(k for g in s["groups"] for k in g["datasets"] if not SETS[k].get("placeholder")))
    sources.append(s)

date = M.get("date") or datetime.date.today().strftime("%B %-d, %Y")
foot = M.get("foot", "Generated {date}. Files were scanned in full with DuckDB; \"Auto-detected on load\" is the type DuckDB "
             "assigns when it reads the raw file, and distinct counts there are approximate (HyperLogLog). \"Data type\" is "
             "inferred from the values: Code means digits stored as text with leading zeros, so it should stay text.").replace("{date}", date)
data = json.dumps(dict(sources=sources, sets=SETS), default=str, ensure_ascii=False).replace("</", "<\\/")
tpl = open(os.path.join(HERE, "..", "assets", "template.html")).read()
html = (tpl.replace("__DATA__", data).replace("__TITLE__", M["title"]).replace("__EYEBROW__", M.get("eyebrow", ""))
        .replace("__INTRO__", M.get("intro", "")).replace("__STORE_KEY__", M.get("store_key", "county-profile-view"))
        .replace("__FOOT__", json.dumps(foot)))
open(out, "w").write(html)
views = sum(len(g["datasets"]) for s in sources for g in s["groups"])
print(f"wrote {out}: {len(html) / 1e6:.2f} MB, {views} views, {len(SETS)} datasets")
