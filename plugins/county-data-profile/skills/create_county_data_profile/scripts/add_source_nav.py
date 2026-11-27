"""Turn a column-review page into a workspace: a sidebar that mirrors the CAD website's public-information page
(sections › groups › files, each data file expanding into the tables profiled from it, with search over tables and
columns and the team's review progress), beside the selected table, which gets a breadcrumb, a header with links to
the website and the team's Drive copy, and Data preview / Columns / About tabs. The original tabs stay in the page, hidden.

The map comes from build_source_map.py (source_map.json). Before writing, the page is checked for local paths:
absolute paths, script names, and the manifest's root and dataset paths (pass the manifest to check those).

Usage: python3 add_source_nav.py <column-review.html> <source_map.json> <out.html> [manifest.json]
"""
import json
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent / "assets"  # source_nav.css and source_nav.js


def replace_once(s, old, new):
    if s.count(old) != 1:
        raise SystemExit(f"expected exactly one {old!r}, found {s.count(old)}")
    return s.replace(old, new)


def build(page: pathlib.Path, srcmap: pathlib.Path, out: pathlib.Path, manifest: pathlib.Path | None = None):
    s = page.read_text()
    if 'id="srcmap"' in s:
        raise SystemExit(f"{page} already has a source map")
    m = json.loads(srcmap.read_text())
    data = json.dumps(m, ensure_ascii=False).replace("</", "<\\/")
    css = (HERE / "source_nav.css").read_text()
    js = (HERE / "source_nav.js").read_text()
    pg = m["page"]
    drive = m.get("drive")
    sources = (f'<p class="rv-intro">Sources: <a href="{pg['url']}" target="_blank" rel="noopener">{pg['url'].split('//')[1]}</a>'
               f' (checked {pg['checked']})'
               + (f' · our copies in <a href="{drive['url']}" target="_blank" rel="noopener">{drive['label']}</a>' if drive else '')
               + '. Pick a file below, or search for a table or column at the top.</p>\n')
    ws = """<div class="ws-topbar"><button type="button" class="ws-homebtn" id="ws-home" aria-label="Home" title="Home"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 10.5 12 3l9 7.5"/><path d="M5.5 9v11h4.5v-6h4v6h4.5V9"/></svg></button>
  <div class="ws-search" id="ws-search" role="search">
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
    <input type="search" class="ws-q" id="ws-q" placeholder="Search tables and columns" aria-label="Search tables and columns" autocomplete="off">
    <div class="ws-results" id="ws-results" hidden></div>
  </div>
  </div>
  <div class="ws" id="ws">
    <button type="button" class="ws-toggle" id="ws-toggle">Contents</button>
    <aside class="ws-side" id="ws-side" aria-label="Tables">
      <div class="ws-sidetop"><span class="ws-toc-title">Contents</span></div>
      <div class="ws-list" id="ws-list"></div>
    </aside>
    <div class="ws-main" id="ws-main">
      <nav class="ws-bc" id="ws-bc" aria-label="Breadcrumb"></nav>
      <div class="ws-head" id="ws-head"></div>
      <main id="panels"></main>
    </div>
  </div>"""
    # the year/snapshot tabs are replaced by picking a download, so drop wording that points at them
    s = s.replace(" The year switch on every tab picks the snapshot.", "")
    s = s.replace("applies to that file in every year tab.", "applies to the same raw file in every download that has it.")
    s = replace_once(s, '\n<div class="wrap">', f"\n<style>\n{css}</style>\n\n<div class=\"wrap\">")
    # header: eyebrow and title stay; the intro, the review note and the sources fold into "About this page"
    head = re.search(r"  <header>\n(.*?)  </header>\n", s, re.S)
    body = head.group(1)
    keep = "".join(re.findall(r"    <div class=\"eyebrow\">.*?</div>\n|    <h1>.*?</h1>\n", body))
    off = re.search(r"  <p class=\"rv-off\".*?</p>\n", body).group(0)
    info = "".join(re.findall(r"    <p class=\"sub\">.*?</p>\n|  <p class=\"rv-intro\">.*?</p>\n", body, re.S))
    header = ('  <header class="ws-top">\n' + keep +
              '    <details class="ws-info"><summary>About this page</summary><div class="ws-info-body">\n' + info + "  " + sources +
              "    </div></details>\n" + off + "  </header>\n")
    s = s[:head.start()] + header + s[head.end():]

    # name each table's file by its raw file in the website download, never by our local path
    dm = re.search(r'(<script id="data" type="application/json">)(.*?)(</script>)', s, re.S)
    data_obj = json.loads(dm.group(2))
    for k, d in data_obj["sets"].items():
        t = m["tables"].get(k)
        if t and "file" in d:
            d["file"] = t["raw"]
    s = s[:dm.start(2)] + json.dumps(data_obj, ensure_ascii=False).replace("</", "<\\/") + s[dm.end(2):]
    s = replace_once(s, '<main id="panels"></main>', ws)
    s = replace_once(s, "  reviewEnhance(key, p);\n", "  originEnhance(key, p);\n  reviewEnhance(key, p);\n")
    s = replace_once(s, "  reviewShow(key);\n", "  reviewShow(key);\n  navSync(key);\n")
    s = replace_once(s, "\n<script>\nconst DATA = ",
                     f'\n<script id="srcmap" type="application/json">{data}</script>\n<script>\n{js}</script>\n\n<script>\nconst DATA = ')
    leaks = find_leaks(s, manifest)
    if leaks:
        raise SystemExit("local paths left in the page: " + "; ".join(leaks[:20]))
    out.write_text(s)


def find_leaks(s, manifest=None):
    """Local file locations in the page: absolute paths, our script names, and (with the manifest) its root and the
    folders of every dataset path. Names of the CAD's own files (PROP.TXT, x.csv) are fine; our folders are not."""
    # this machine's own locations; a Windows-style path in the CAD's data (Q:\\...) is the CAD's, not ours
    pats = [r"(?<![\w.])/(?:Users|home|private|tmp|var/folders|mnt|Volumes)/[\w./ -]+", r"\bvenv/",
            re.escape(str(pathlib.Path.home()))]
    # our own scripts by name (the skill's, and the county folder's when the manifest is given); a script name
    # inside the CAD's data or API examples is theirs, not ours
    scripts = {x.name for x in pathlib.Path(__file__).resolve().parent.glob("*.py")}
    if os.name == "nt":
        pats.append(r"\b[A-Za-z]:\\(?:Users|Documents and Settings)\\[\w\\. -]+")
    if manifest:
        m = json.loads(pathlib.Path(manifest).read_text())
        root = m.get("root", "").rstrip("/")
        if root:
            pats += [re.escape(root), re.escape(pathlib.Path(root).name) + "/"]
        if root and pathlib.Path(root).is_dir():
            scripts |= {x.name for x in pathlib.Path(root).rglob("*.py") if "venv" not in x.parts and "site-packages" not in x.parts}
        dirs = {str(pathlib.PurePosixPath(d["path"]).parent) for d in m.get("datasets", {}).values() if d.get("path")}
        pats += [r"(?<![\w.])" + re.escape(x) + "/" for x in sorted(dirs) if x not in (".", "")]
    pats += [r"\b" + re.escape(n) + r"\b" for n in sorted(scripts)]
    return sorted(set(re.findall("|".join(pats), s)))


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) not in (3, 4):
        raise SystemExit(__doc__)
    build(*map(pathlib.Path, a))
