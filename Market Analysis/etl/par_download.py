"""Parallel HTTP range download (the Denton CAD file server gives ~25 KB/s per connection).
Usage: python -I par_download.py URL OUTFILE [workers] [chunk_MB]"""
import os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

url, out = sys.argv[1], sys.argv[2]
workers = int(sys.argv[3]) if len(sys.argv) > 3 else 16
chunk = int(float(sys.argv[4]) * 1e6) if len(sys.argv) > 4 else 2_000_000
h = subprocess.run(["curl", "-sIL", "-m", "60", "-A", "Mozilla/5.0", url], capture_output=True, text=True).stdout
size = int([l.split(":")[1] for l in h.lower().splitlines() if l.startswith("content-length")][-1])
parts = [(i, s, min(s + chunk, size) - 1) for i, s in enumerate(range(0, size, chunk))]
tmp = out + ".parts"
os.makedirs(tmp, exist_ok=True)


def get(p):
    i, a, b = p
    f = f"{tmp}/{i:06d}"
    for _ in range(8):
        if os.path.exists(f) and os.path.getsize(f) == b - a + 1:
            return
        subprocess.run(["curl", "-s", "-m", "600", "-A", "Mozilla/5.0", "-r", f"{a}-{b}", "-o", f, url])
    raise RuntimeError(f"part {i} failed")


with ThreadPoolExecutor(workers) as ex:
    for k, _ in enumerate(ex.map(get, parts), 1):
        if k % 50 == 0:
            print(f"{k}/{len(parts)}", flush=True)
with open(out, "wb") as o:
    for i, _, _ in parts:
        with open(f"{tmp}/{i:06d}", "rb") as f:
            o.write(f.read())
        os.remove(f"{tmp}/{i:06d}")
os.rmdir(tmp)
assert os.path.getsize(out) == size
print("ok", out, size)
