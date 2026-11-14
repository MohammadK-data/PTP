"""Stream a Denton CAD certified protax JSON zip (one property record per line) without unzipping it.
Usage: python -I denton_json_stream.py <zip> <year> <outdir>
Writes <outdir>/denton_<year>_json_props.csv.gz   (pID, pYear, propType, stateCd, exemptions, noticeDt)
       <outdir>/denton_<year>_json_agents.csv.gz  (pID, agentID, name, applicationDt, effectiveDt, expirationDt)
       <outdir>/denton_<year>_json_appeals.csv.gz (pID, appealID, pYear, appealType, appealStatus, appealedByType, appealedByAgentID)
No owner names/addresses are written."""
import csv, gzip, io, json, sys, time, zipfile

src, year, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
z = zipfile.ZipFile(src)
member = max(z.infolist(), key=lambda i: i.file_size)
print("member", member.filename, member.file_size, flush=True)


def name(a):
    return (a.get("companyName") or a.get("contactName") or
            " ".join(x for x in (a.get("firstName"), a.get("lastName")) if x) or "").strip()


def first(x):
    return x[0] if isinstance(x, list) and x else (x if isinstance(x, dict) else {})


FH = [gzip.open(f"{out}/denton_{year}_json_{k}.csv.gz", "wt", newline="") for k in ("props", "agents", "appeals")]
P, A, AP = (csv.writer(h) for h in FH)
P.writerow(["pID", "pYear", "propType", "stateCd", "exemptions", "noticeDt"])
A.writerow(["pID", "agentID", "name", "applicationDt", "effectiveDt", "expirationDt"])
AP.writerow(["pID", "appealID", "pYear", "appealType", "appealStatus", "appealedByType", "appealedByAgentID"])
t, n, buf = time.time(), 0, None
# Two layouts: one record per line, or pretty-printed with indent 1 (record opens with " {" and closes with " }," / " }").
with z.open(member) as fb:
    for line in io.TextIOWrapper(fb, encoding="utf-8", errors="replace"):
        s = line.rstrip("\r\n")
        if buf is None:
            if s in (" {", "{"):
                buf = [s]
                continue
            st = s.strip()
            if not st.startswith("{"):
                continue
            rec = json.loads(st.rstrip(","))
        else:
            buf.append(s)
            if s not in (" },", " }", "},", "}"):
                continue
            rec = json.loads("\n".join(buf).rstrip(","))
            buf = None
        n += 1
        prof = first(rec.get("propertyProfile"))
        P.writerow([rec.get("pID"), rec.get("pYear"), rec.get("propType"), prof.get("stateCd"), prof.get("exemptions"), rec.get("noticeDt")])
        seen = set()
        for o in rec.get("owners") or []:
            for a in o.get("agents") or []:
                k = (a.get("agentID"), a.get("effectiveDt"), a.get("expirationDt"))
                if a.get("agentID") is None or k in seen:
                    continue
                seen.add(k)
                A.writerow([rec.get("pID"), a.get("agentID"), name(a), a.get("applicationDt"), a.get("effectiveDt"), a.get("expirationDt")])
        for a in rec.get("appeals") or []:
            AP.writerow([rec.get("pID"), a.get("appealID"), a.get("pYear"), a.get("appealType"), a.get("appealStatus"),
                         a.get("appealedByType"), a.get("appealedByAgentID")])
        if n % 50000 == 0:
            print(f"{n:,} records {time.time()-t:,.0f}s", flush=True)
for h in FH:
    h.close()
print("done", n, "records; unfinished record:", buf is not None, flush=True)
