"""Hide values of personal columns in profile.json before building. Run after every profile_files.py run."""
import json, re, sys
p = sys.argv[1] if len(sys.argv) > 1 else "profile.json"
prof = json.load(open(p))
SENS = re.compile(r"^(py_owner_name|appr_owner_name|jan1_owner_name|owner_name|.*confidential_name|"
                  r"(py|appr|jan1|mortgage)_addr_line\d|mortgage_acct_id|legal_desc2?|situs_num|"
                  r"mbl_hm_(sn|hud_num|title_num).*|operator)$")
n = 0
for k, d in prof.items():
    for c in d["columns"]:
        if SENS.match(c["name"]):
            c["masked"] = True; c["top"] = []; c.pop("stats", None); c.pop("hist", None); n += 1
        else:  # long JSON sketches: keep the top values short
            c["top"] = [[v[:120] + "…" if isinstance(v, str) and len(v) > 120 else v, cnt] for v, cnt in c["top"]]
json.dump(prof, open(p, "w"), default=str)
print(n, "columns masked")
