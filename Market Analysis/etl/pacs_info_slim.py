"""PACS appraisal export APPRAISAL_INFO.TXT (fixed width) -> slim gzipped CSV, one row per record.
Layout: Denton etl/pacs_appraisal_export_layout.json (8.0.30; later versions only append fields).
Usage: python -I pacs_info_slim.py <APPRAISAL_INFO.TXT | export.zip> <out.csv.gz>
A .zip is streamed (the *APPRAISAL_INFO.TXT member is read without unzipping it)."""
import csv, gzip, io, json, sys, zipfile

LAYOUT = json.load(open("/Users/user2/PTP/CAD Website/Denton/etl/pacs_appraisal_export_layout.json"))["APPRAISAL_INFO"]
KEEP = ["prop_id", "prop_type_cd", "prop_val_yr", "sup_num", "hs_exempt", "imprv_state_cd", "land_state_cd",
        "personal_state_cd", "mineral_state_cd", "ca_agent_id", "arb_agent_id", "arb_protest_flag"]
POS = {f[0]: (f[1] - 1, f[2]) for f in LAYOUT if f[0] in KEEP}

src, dst = sys.argv[1], sys.argv[2]
n = 0
if src.lower().endswith(".zip"):
    z = zipfile.ZipFile(src)
    m = [i for i in z.namelist() if i.endswith("APPRAISAL_INFO.TXT") and not i.startswith("__MACOSX")][0]
    print("member", m)
    f_in = io.TextIOWrapper(z.open(m), encoding="latin-1", newline="")
else:
    f_in = open(src, "r", encoding="latin-1", newline="")
with f_in as f, gzip.open(dst, "wt", newline="") as g:
    w = csv.writer(g)
    w.writerow(KEEP)
    for line in f:
        w.writerow([line[POS[k][0]:POS[k][1]].strip() for k in KEEP])
        n += 1
print(src, n, "rows ->", dst)
