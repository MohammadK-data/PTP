"""Travis 2024/2025 roll counts from the EARS submission the CAD sent the Comptroller (traviscad.org largefiles).

AJR records (one per account x taxing unit x category; 96-1051 manual): AJR005 taxing unit type,
AJR008 short account (= prop_id), AJR031 category code, AJR039 homestead indicator (Y/N).
Output per account: prop_id, cats (sorted unique categories), hs (Y if any AJR039=Y).
Run: python -I travis_ears_slim.py <EARS.csv> <out.csv.gz>
"""
import csv
import gzip
import sys
from collections import Counter, defaultdict


def main(src, dst):
    cats = defaultdict(set)
    hs = set()
    nf = Counter()
    with open(src, "r", encoding="latin-1", newline="") as f:
        for row in csv.reader(f):
            if not row or row[0] != "AJR":
                continue
            nf[len(row)] += 1
            pid = row[7].strip().lstrip("0")
            cats[pid].add(row[30].strip())
            if row[38].strip() == "Y":
                hs.add(pid)
    print("AJR field counts:", nf.most_common(5))
    with gzip.open(dst, "wt", newline="") as g:
        w = csv.writer(g)
        w.writerow(["prop_id", "cats", "hs"])
        for pid, c in cats.items():
            w.writerow([pid, "|".join(sorted(c)), "Y" if pid in hs else "N"])
    print(len(cats), "accounts ->", dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
