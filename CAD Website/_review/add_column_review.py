"""Make a team-review copy of a county data profile page.

Adds a Need / Maybe / Drop decision and a notes thread to every column table. The copy is saved
next to the original as <county>/profile/review/<county>-column-review.html; the original page
is not touched. Publish the copy with capabilities {"db": {}, "user": {"scopes": ["profile"]}}.

Usage: python3 add_column_review.py <profile.html> [<profile.html> ...]
"""
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).parent
CSS = (HERE / "review.css").read_text()
JS = (HERE / "review.js").read_text()

INTRO = """  <p class="rv-intro">Team review: mark each column <b>Need</b>, <b>Maybe</b> or <b>Drop</b> and leave notes in the column table.
  A decision or note on a column applies to that file in every year tab. Everyone with access sees changes live.</p>
  <p class="rv-off" id="rv-off" hidden>Notes and decisions load when this page is opened on claude.ai.</p>
"""


def replace_once(s, old, new):
    if s.count(old) != 1:
        raise SystemExit(f"expected exactly one {old!r}, found {s.count(old)}")
    return s.replace(old, new)


def build(src: pathlib.Path) -> pathlib.Path:
    s = src.read_text()
    county = re.search(r"<title>(\w+) Property Data Profile</title>", s).group(1)
    s = replace_once(s, f"<title>{county} Property Data Profile</title>", f"<title>{county} Column Review</title>")
    s = replace_once(s, '\n<div class="wrap">', f"\n<style>\n{CSS}</style>\n\n<div class=\"wrap\">")
    s = replace_once(s, "  </header>", INTRO + "  </header>")
    s = replace_once(s, "  return built[key] = p;", "  built[key] = p;\n  reviewEnhance(key, p);\n  return p;")
    s = replace_once(s, "\n  current = key;\n", "\n  current = key;\n  reviewShow(key);\n")
    s = replace_once(s, "\n<script>\nconst DATA = ", f"\n<script>\n{JS}</script>\n\n<script>\nconst DATA = ")
    out = src.parent / "review" / f"{county.lower()}-column-review.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(s)
    return out


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        print(build(pathlib.Path(arg)))
