"""Turn a county column-review page into a workspace: a sidebar listing every table, grouped by the CAD download it
comes from (with search over tables and columns, the team's review progress, and the CAD's documents with TCAD and
Drive links), beside the selected table, which gets a header and Columns / Sample rows / Charts / About tabs.
The original tabs stay in the page, hidden.

The map is a JSON file written per county, for example Travis/profile/make_source_map.py -> source_map.json.

Usage: python3 add_source_nav.py <column-review.html> <source_map.json> <out.html>
"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).parent


def replace_once(s, old, new):
    if s.count(old) != 1:
        raise SystemExit(f"expected exactly one {old!r}, found {s.count(old)}")
    return s.replace(old, new)


def build(page: pathlib.Path, srcmap: pathlib.Path, out: pathlib.Path):
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
               + '. Pick a table on the left, or search for a table or column.</p>\n')
    ws = """<div class="ws" id="ws">
    <button type="button" class="ws-toggle" id="ws-toggle">Tables and search</button>
    <aside class="ws-side" id="ws-side" aria-label="Tables">
      <div class="ws-sidetop"><button type="button" class="ws-homebtn" id="ws-home" aria-label="Home" title="Home"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 10.5 12 3l9 7.5"/><path d="M5.5 9v11h4.5v-6h4v6h4.5V9"/></svg></button><input type="search" class="ws-q" id="ws-q" placeholder="Find a table or column" aria-label="Find a table or column">
        <button type="button" class="ws-collapse" id="ws-collapse" aria-label="Hide sidebar" title="Hide sidebar" aria-expanded="true"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="3"/><path d="M9.5 4v16"/></svg></button></div>
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

    # name each table's file by its raw file in the TCAD download, never by our local path
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
    leaks = sorted(set(re.findall(r"(?<![\w.])(?:Data|output|etl|profile|venv)/[\w./ -]{0,60}|CAD Website|/Users/[\w./-]+|\b\w+\.py\b", s)))
    if leaks:
        raise SystemExit("local paths left in the page: " + "; ".join(leaks[:20]))
    out.write_text(s)


if __name__ == "__main__":
    build(*map(pathlib.Path, sys.argv[1:4]))
