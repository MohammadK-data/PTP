"""Write source_map.json: where each table on a county's review page comes from, for add_source_nav.py.

Inputs, all per county (nothing here knows any county):
  catalog.json   What the CAD's public-information page lists, read from the website when you build it:
                 {"page": {"label", "url", "short", "checked"},
                  "sections": [{"name", "groups": [{"name", "desc", "files": [
                      {"name", "url", "role": "data" | "layout" | "doc", "note",
                       "contents": [...] | "local": "<folder or .zip, relative to the manifest root>",
                       "tables": ["<dataset key or glob>", ...], "layout": "<default layout text for its tables>"}]}]}]}
                 "tables" ties a download to the datasets profiled from it. "local" is listed here (folder files or
                 zip members) to fill "contents" and is never written out.
  manifest.json  The page's manifest. Optional per-dataset fields: "raw" (the file's name inside the download;
                 default: the dataset path's file name), "layout" (what documents it; default: the catalog file's
                 "layout"), "nav_label" (the table's name in the sidebar).
  drive.json     Optional (--drive): the team's Drive copies, listed with the Google Drive connector:
                 {"source": "<folder path for people>", "checked", "folders": {"_root": id, "<group name>": id},
                  "files": {"<file name>": id}}. Files match by the website file name, ignoring a "-<digit>"
                 suffix (duplicate uploads) on either side.

Usage: python3 -I build_source_map.py catalog.json manifest.json source_map.json [--drive drive.json]
"""
import fnmatch
import json
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "file"


def list_local(root, rel):
    p = Path(root) / rel
    if p.is_dir():
        return sorted(x.name + ("/" if x.is_dir() else "") for x in p.iterdir() if not x.name.startswith("."))
    if p.suffix.lower() == ".zip" and p.exists():
        with zipfile.ZipFile(p) as z:
            return sorted(n for n in z.namelist() if not n.endswith("/") and "/." not in "/" + n)
    raise SystemExit(f"catalog 'local' not found: {rel}")


def words(s):
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def titles(manifest):
    """Sidebar name per dataset: nav_label; else the group's label when the dataset is alone in its year and its
    label only repeats words of that year's label (a year or snapshot, not a table name); else the label without "N · "."""
    alone = {}
    for src in manifest.get("sources", []):
        groups = src.get("groups")
        if not isinstance(groups, list):
            continue
        for g in groups:
            for y in g.get("years") or []:
                if len(y["datasets"]) == 1:
                    alone[y["datasets"][0]] = (y["label"], g["label"])
    out = {}
    for k, d in manifest["datasets"].items():
        label = d.get("label", k)
        yl, gl = alone.get(k, (None, None))
        out[k] = d.get("nav_label") or (gl if yl and words(label) <= words(yl) else None) or re.sub(r"^\d+ · ", "", label)
    return out


def add_drive(groups, drive):
    norm = lambda n: re.sub(r"-\d(\.[a-z0-9]+)$", r"\1", n.lower())
    exact = {n.lower(): i for n, i in drive.get("files", {}).items()}
    loose = {norm(n): i for n, i in drive.get("files", {}).items()}
    folders = drive.get("folders", {})
    for g in groups:
        if g["name"] in folders:
            g["drive"] = "https://drive.google.com/drive/folders/" + folders[g["name"]]
        for f in g["files"]:
            name = f["url"].split("?")[0].rstrip("/").rsplit("/", 1)[-1]
            name = unquote(name).lower()
            i = exact.get(name) or loose.get(norm(name))
            if i:
                f["drive"] = f"https://drive.google.com/file/d/{i}/view"
    out = {"label": drive.get("source", "Google Drive"), "checked": drive.get("checked", "")}
    if "_root" in folders:
        out["url"] = "https://drive.google.com/drive/folders/" + folders["_root"]
    return out if "url" in out else None


def main(catalog_path, manifest_path, out_path, drive_path=None):
    cat = json.loads(Path(catalog_path).read_text())
    man = json.loads(Path(manifest_path).read_text())
    root = man.get("root", str(Path(manifest_path).parent))
    sets = {k: d for k, d in man["datasets"].items() if not d.get("placeholder")}
    name = titles(man)
    groups, tables, ids, claimed = [], {}, set(), {}
    for sec in cat["sections"]:
        for g in sec["groups"]:
            files = []
            for f in g["files"]:
                row = {"name": f["name"], "url": f["url"], "status": "used" if f.get("tables") else f.get("role", "doc")}
                if row["status"] == "doc":
                    row["status"] = "not"
                if f.get("note"):
                    row["note"] = f["note"]
                contents = f.get("contents") or (list_local(root, f["local"]) if f.get("local") else None)
                if contents:
                    row["contents"] = contents
                if f.get("tables"):
                    eid = slug(f.get("id") or f["name"])
                    while eid in ids:
                        eid += "-x"
                    ids.add(eid)
                    row["export"] = eid
                    keys = [k for pat in f["tables"] for k in sets if fnmatch.fnmatchcase(k, pat)]
                    if not keys:
                        raise SystemExit(f"catalog file {f['name']!r}: no dataset matches {f['tables']}")
                    for k in keys:
                        if k in claimed:
                            raise SystemExit(f"dataset {k} matched by both {claimed[k]!r} and {f['name']!r}")
                        claimed[k] = f["name"]
                        d = sets[k]
                        tables[k] = {"download": eid, "raw": d.get("raw") or PurePosixPath(d["path"]).name,
                                     "layout": d.get("layout") or f.get("layout", ""), "title": name[k]}
                files.append(row)
            groups.append({"name": g["name"], "files": files, "section": sec["name"], "desc": g.get("desc", "")})
    missing = sorted(set(sets) - set(tables))
    if missing:
        raise SystemExit(f"{len(missing)} datasets are in no catalog file's 'tables': {' '.join(missing[:30])}")
    m = {"page": cat["page"], "groups": groups, "tables": tables}
    if drive_path:
        d = add_drive(groups, json.loads(Path(drive_path).read_text()))
        if d:
            m["drive"] = d
    Path(out_path).write_text(json.dumps(m, indent=1, ensure_ascii=False))
    used = sum(1 for g in groups for f in g["files"] if f.get("export"))
    print(f"{len(tables)} tables from {used} downloads; {sum(len(g['files']) for g in groups)} files in {len(groups)} groups"
          + (f"; {sum(1 for g in groups for f in g['files'] if f.get('drive'))} with a Drive copy" if drive_path else ""))


if __name__ == "__main__":
    a = sys.argv[1:]
    drive = None
    if "--drive" in a:
        i = a.index("--drive")
        drive = a[i + 1]
        del a[i:i + 2]
    if len(a) != 3:
        raise SystemExit(__doc__)
    main(*a, drive_path=drive)
