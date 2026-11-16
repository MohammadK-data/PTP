"""Convert Bexar CAD's PACS Appraisal Export (zipped fixed-width .TXT, layout 8.0.0.34) to gzipped CSV.

Same approach as Rockwall/Travis: slice each line by etl/pacs_appraisal_export_layout_8034.json (built from
BCAD's own 8.0.34 workbook by bexar_pacs_layout_build.py), strip the padding, write
output/<export run date>_<year>_<RECORD>.csv.gz. Reads straight from the zip, nothing is unpacked.
Every Bexar record is one character wider than the layout (a trailing blank); it is dropped, and any
non-blank trailing character is counted and reported.

Usage (from the Bexar folder):
    python3 -I etl/bexar_appraisal_export_etl.py "Data/2026 Appraisal Data Export as of 2026-10-08_Sup 298/....zip" [RECORD ...]
"""
import csv, gzip, io, json, subprocess, sys, time, zipfile
from datetime import datetime
from pathlib import Path

BEXAR = Path(__file__).resolve().parent.parent
OUT = BEXAR / "output"
LAYOUT = json.loads((BEXAR / "etl/pacs_appraisal_export_layout_8034.json").read_text())


def rec_name(name):  # 2026-10-15_007456_APPRAISAL_INFO.TXT -> APPRAISAL_INFO
    return Path(name).stem.split("_", 2)[2]


def main():
    zpath = Path(sys.argv[1]); only = set(sys.argv[2:])
    z = zipfile.ZipFile(zpath)
    # stream members with the system unzip: the March zip uses Deflate64, which Python's zipfile can't read
    member = lambda name: subprocess.Popen(["unzip", "-p", str(zpath), name], stdout=subprocess.PIPE).stdout
    hdr = member(next(n for n in z.namelist() if n.endswith("APPRAISAL_HEADER.TXT"))).read().decode("latin-1")
    run_date = datetime.strptime(hdr[:10], "%m/%d/%Y").strftime("%Y-%m-%d"); year = hdr[56:60]
    OUT.mkdir(exist_ok=True)
    version = hdr[174:184].strip()
    print("export layout version", version, flush=True)
    if version == "8.0.0.33":
        # 8.0.0.33 = 8.0.34 without the FEED fields at the end of three records (checked against the
        # March 28 prelim widths: INFO 9659, ENTITY_INFO 2975, ENTITY_TOTALS 2356 characters).
        LAYOUT["APPRAISAL_INFO"] = [f for f in LAYOUT["APPRAISAL_INFO"] if not f[0].startswith("feed_")]
        for r in ("APPRAISAL_ENTITY_INFO", "APPRAISAL_ENTITY_TOTALS"):
            LAYOUT[r] = [f for f in LAYOUT[r] if not f[0].startswith("feed_")]
    for info in sorted(z.infolist(), key=lambda i: i.file_size):
        rec = rec_name(info.filename)
        if only and rec not in only:
            continue
        if rec not in LAYOUT:
            print(f"{info.filename}: no layout, skipped", flush=True); continue
        lay = LAYOUT[rec]; width = lay[-1][2]
        names = [n for n, _, _ in lay]; slices = [(s - 1, e) for _, s, e in lay]
        out = OUT / f"{run_date}_{year}_{rec}.csv.gz"
        t0 = time.time(); n = badlen = tail = 0
        with member(info.filename) as raw, gzip.open(out, "wt", newline="", encoding="utf-8", compresslevel=1) as dst:
            w = csv.writer(dst); w.writerow(names)
            for line in io.TextIOWrapper(raw, encoding="latin-1", newline=""):
                line = line.rstrip("\r\n")
                if len(line) != width + 1 and len(line) != width:
                    badlen += 1
                    if badlen <= 5: print(f"  {rec} line {n+1}: {len(line)} chars, layout {width}", flush=True)
                if line[width:].strip(): tail += 1
                w.writerow([line[s:e].strip() for s, e in slices]); n += 1
        print(f"{info.filename} -> {out.name}: {n:,} rows, {badlen} bad length, {tail} non-blank tail, "
              f"{out.stat().st_size/1e6:,.1f} MB, {time.time()-t0:,.0f}s", flush=True)


if __name__ == "__main__":
    main()
