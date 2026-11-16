"""Make a team-review copy of a county data profile page.

Adds a Need / Maybe / Drop decision and a notes thread to every column table. The copy is saved
next to the original as <county>/profile/review/<county>-column-review.html; the original page
is not touched. Publish the copy with capabilities {"db": {}, "user": {"scopes": ["profile"]}}.

Usage: python3 add_column_review.py [--seed seed.json] <profile.html> [<profile.html> ...]

--seed bakes suggested decisions into the copy: {"at": <ms>, "files": {<file key>: {<column>: [status, comment]}}}.
Each column then shows the suggestion and its comment (as a note by Claude) until the team saves its own decision.
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


def build(src: pathlib.Path, seed: str = "") -> pathlib.Path:
    s = src.read_text()
    county = re.search(r"<title>(\w+) Property Data Profile</title>", s).group(1)
    s = replace_once(s, f"<title>{county} Property Data Profile</title>", f"<title>{county} Column Review</title>")
    s = replace_once(s, '\n<div class="wrap">', f"\n<style>\n{CSS}</style>\n\n<div class=\"wrap\">")
    s = replace_once(s, "  </header>", INTRO + "  </header>")
    s = replace_once(s, "  return built[key] = p;", "  built[key] = p;\n  reviewEnhance(key, p);\n  return p;")
    s = replace_once(s, "\n  current = key;\n", "\n  current = key;\n  reviewShow(key);\n")
    s = replace_once(s, "\n<script>\nconst DATA = ", f"\n<script>\n{seed}{JS}</script>\n\n<script>\nconst DATA = ")
    out = src.parent / "review" / f"{county.lower()}-column-review.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(s)
    return out


if __name__ == "__main__":
    args, seed = sys.argv[1:], ""
    if "--seed" in args:
        i = args.index("--seed")
        seed = "const REVIEW_SEED = " + pathlib.Path(args[i + 1]).read_text().replace("</", "<\\/") + ";\n"
        del args[i:i + 2]
    for arg in args:
        print(build(pathlib.Path(arg), seed))
