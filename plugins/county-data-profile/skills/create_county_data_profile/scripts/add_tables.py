"""Add a folder of converted tables (<table>.csv.gz, from flatten_json.py, split_record_types.py, to_csv_gz.py or
an ETL) to manifest.json as datasets, one year (or snapshot) entry of a group. Prints the new keys, for
profile_files.py.

  - Keys are "<prefix>-<table slug>". Existing keys are kept, with their notes, labels and about text.
  - If the folder has _tables.json (flatten_json.py), each table gets its JSON path, an "about" line saying what
    one row is and what it joins back on, and descriptions for the key and <list>_i columns. Otherwise "about"
    is left for you to write; the script lists those keys.
  - If the group already has years, tables keep the same position as in those years (matched by table name), so
    switching years stays on the same table; new tables go at the end. --compare sets each table's "compare" to
    the same table under that prefix, when it exists.
  - --groups splits the folder's tables over several groups: a JSON file
    [{"id", "label", "desc", "match": ["<top-level path or table name>", ...]}, ...]; tables matching none go to
    --group. Without it, all tables go to --group.

Usage: python3 -I add_tables.py manifest.json <folder> --prefix p --group id --year "label"
                 [--group-label "Label"] [--group-desc "..."] [--compare prefix] [--groups groups.json] [--source id]
"""
import json
import re
import sys
from pathlib import Path

CSV = {"opts": "delim=',', quote='\"', escape='\"', max_line_size=200000000"}


def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def arg(a, flag, default=None):
    if flag in a:
        i = a.index(flag)
        v = a[i + 1]
        del a[i:i + 2]
        return v
    return default


def main(a):
    prefix, gid, year = arg(a, "--prefix"), arg(a, "--group"), arg(a, "--year")
    glabel, gdesc, cmp_prefix = arg(a, "--group-label"), arg(a, "--group-desc", ""), arg(a, "--compare")
    gmap_path, source_id = arg(a, "--groups"), arg(a, "--source")
    if len(a) != 2 or not (prefix and gid and year):
        raise SystemExit(__doc__)
    mpath, folder = Path(a[0]), Path(a[1])
    m = json.loads(mpath.read_text())
    root = Path(m.get("root", mpath.parent))
    meta = json.loads((folder / "_tables.json").read_text()) if (folder / "_tables.json").exists() else None
    tables = sorted(meta["tables"]) if meta else sorted(p.name[:-7] for p in folder.glob("*.csv.gz"))
    if not tables:
        raise SystemExit(f"no .csv.gz tables in {folder}")
    try:
        rel = folder.resolve().relative_to(root.resolve())
    except ValueError:
        raise SystemExit(f"{folder} is not under the manifest root {root}")
    gmap = json.loads(Path(gmap_path).read_text()) if gmap_path else []
    top_of = lambda t: t.split(".")[0]

    def group_for(t):
        for g in gmap:
            if t in g["match"] or top_of(t) in g["match"]:
                return g["id"]
        return gid

    ds, desc = m["datasets"], m.setdefault("descriptions", {})
    src = next((s for s in m["sources"] if s["id"] == source_id), None) if source_id else m["sources"][0]
    if src is None or not isinstance(src.get("groups"), list):
        raise SystemExit("no website source with a groups list in the manifest (see --source)")
    labels = {g["id"]: g for g in gmap}
    labels.setdefault(gid, {"id": gid, "label": glabel or gid, "desc": gdesc})
    new, need_about = [], []
    for g_id in dict.fromkeys(group_for(t) for t in tables):
        mine = [t for t in tables if group_for(t) == g_id]
        g = next((x for x in src["groups"] if x["id"] == g_id), None)
        if g is None:
            info = labels[g_id]
            g = {"id": g_id, "label": info.get("label") or g_id, "desc": info.get("desc", ""), "datasets": [], "years": []}
            src["groups"].append(g)
        # order: the position each table has in the group's other years, then new tables by name
        order = []
        for y in g.get("years", []):
            for k in y["datasets"]:
                t = ds.get(k, {}).get("table")
                if t and t not in order:
                    order.append(t)
        mine.sort(key=lambda t: (order.index(t) if t in order else len(order), t))
        keys = []
        for i, t in enumerate(mine, 1):
            k = f"{prefix}-{slug(t)}"
            keys.append(k)
            if k in ds:
                continue
            d = {"path": str(rel / f"{t}.csv.gz"), "read": CSV, "table": t,
                 "label": (f"{i} · " if len(mine) > 1 else "") + t.replace(".", " › "),
                 "encoding": "Gzipped CSV, UTF-8" + (f" (from {meta['source']})" if meta else "")}
            if meta:
                kc = meta.get("keys", [])
                if t == meta.get("root"):
                    d["about"] = "One row per record: its top-level fields."
                else:
                    parents = [p + "_i" for p in t.split(".")[:-1]]
                    d["about"] = (f"One row per item in the {t.replace('.', ' › ')} list of each record. Joins back on "
                                  + ", ".join(kc + parents) + ".")
                d["json_path"] = t
                for c in kc:
                    desc.setdefault(c, f"Key of the record this row belongs to ({', '.join(kc)} together identify it).")
                leaf = t.rsplit(".", 1)[-1]
                desc.setdefault(f"{leaf}_i", f"Position of the row in its {leaf} list (0 = first); with the record key it links child rows to this row.")
            else:
                d["about"] = ""
                need_about.append(k)
            if cmp_prefix and f"{cmp_prefix}-{slug(t)}" in ds:
                d["compare"] = f"{cmp_prefix}-{slug(t)}"
            ds[k] = d
            new.append(k)
        years = g.setdefault("years", [])
        yr = next((y for y in years if y["label"] == year), None)
        if yr:
            yr["datasets"] = keys
        else:
            years.append({"label": year, "datasets": keys})
        g["datasets"] = [k for y in years for k in y["datasets"]]
    mpath.write_text(json.dumps(m, indent=1, ensure_ascii=False))
    if need_about:
        print("write 'about' for:", " ".join(need_about), file=sys.stderr)
    print(" ".join(new))


if __name__ == "__main__":
    main(sys.argv[1:])
