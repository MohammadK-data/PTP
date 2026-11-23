"""Profile the endpoints of an OpenAPI spec (portal API docs) from the example responses saved in it.

Usage: python profile_api.py manifest.json api.json

Reads manifest["api"]:
  spec            path to the OpenAPI YAML/JSON file
  groups          optional [{id, label, endpoints: [operation summary, ...]}]; without it endpoints are
                  grouped by their first tag (or first path segment)
  labels, about   optional {operation summary: short label / one-line description}
  filters         optional {schema: <components.schemas name>, endpoints: [summary, ...]} - a body schema
                  whose fields are listed as "filters you can send"
  auth_overrides  optional {operation summary: text for the Authentication tile}

Values are written out exactly as the spec's examples hold them: nothing is hidden, redacted or shortened.
"""
import json, re, statistics, sys
from collections import Counter

import yaml

m = json.load(open(sys.argv[1]))
OUT = sys.argv[2]
A = m["api"]
spec = yaml.load(open(A["spec"]), Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader)) if A["spec"].endswith((".yaml", ".yml")) \
    else json.load(open(A["spec"]))

ISO = re.compile(r"^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?(\.\d+)?Z?)?$")
NUM = re.compile(r"^-?\d+(\.\d+)?$")
# 0/1 integers count as a Flag when both values appear, or when the name reads like a yes/no
FLAGNAME = re.compile(r"(?i)^(is|has|can|receive|notify|initialize|reset|inactive|mailings|allow)|validated$|^processed$")


def jtype(v):
    return "null" if v is None else "boolean" if isinstance(v, bool) else "integer" if isinstance(v, int) else \
        "number" if isinstance(v, float) else "string" if isinstance(v, str) else "array" if isinstance(v, list) else "object"


def find_records(ex):
    """(records, path, totalRecords) for the main list in an example response."""
    if isinstance(ex, dict):
        tot = ex.get("totalRecords")
        r = ex.get("results", ex.get("data"))
        if isinstance(r, dict):
            if isinstance(r.get("results"), list):
                return r["results"], "results.results", r.get("totalRecords", tot)
            return [r], "results", tot
        if isinstance(r, list):
            return r, "results" if "results" in ex else "data", tot
        return [ex], "(root)", tot
    if isinstance(ex, list):
        return ex, "(root list)", None
    return None, None, None


def flatten(rec):
    """One level of nesting becomes parent.child columns."""
    out, nested = {}, {}
    for k, v in rec.items():
        if isinstance(v, dict) and v:
            nested.update({f"{k}.{k2}": v2 for k2, v2 in v.items()})
        else:
            out[k] = v
    out.update(nested)  # nested fields go after the plain ones
    return out


def profile(records, name):
    leaf = name.split(".")[-1]
    vals = [rec.get(name) if isinstance(rec, dict) else None for rec in records]
    nn = [v for v in vals if v is not None]
    hashable = [json.dumps(v, sort_keys=True) if isinstance(v, (list, dict)) else v for v in vals]
    lens = [len(str(v)) for v in nn]
    c = dict(name=name, loader=" / ".join(sorted({jtype(v) for v in vals})), nonnull=len(nn), nulls=len(vals) - len(nn),
             distinct=len({h for h in hashable if h is not None}), minlen=min(lens) if lens else None,
             maxlen=max(lens) if lens else None)
    if len(records) == 1 and nn:
        c["example"] = str(hashable[0])
    if not nn:
        c["type"] = "Empty"
    elif all(isinstance(v, bool) for v in nn) or (all(isinstance(v, int) for v in nn) and set(nn) <= {0, 1}
                                                   and (set(nn) == {0, 1} or FLAGNAME.search(leaf))) \
            or (all(isinstance(v, str) for v in nn) and {v.lower() for v in nn} <= {"y", "n", "yes", "no", "true", "false", "t", "f"}):
        c["type"] = "Flag"
    elif all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in nn):
        c["type"] = "Integer" if all(isinstance(v, int) for v in nn) else "Decimal"
    elif all(isinstance(v, str) for v in nn) and all(ISO.match(v) for v in nn):
        c["type"] = "Date"
    elif all(isinstance(v, str) for v in nn) and all(NUM.match(v) for v in nn):
        c["type"] = "Code (numeric text)" if any(v.startswith("0") and len(v) > 1 for v in nn) else \
            ("Integer" if all("." not in v for v in nn) else "Decimal")
    elif all(isinstance(v, list) for v in nn):
        c["type"] = "Array"
    elif all(isinstance(v, dict) for v in nn):
        c["type"] = "Object"
    else:
        c["type"] = "Text"
    c["top"] = [[k if k is None else str(k), n] for k, n in Counter(hashable).most_common(12)]
    if c["type"] in ("Integer", "Decimal"):
        xs = sorted(float(v) for v in nn)
        q = lambda p: xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))]
        c["stats"] = dict(min=xs[0], max=xs[-1], mean=statistics.fmean(xs), p=[q(p) for p in (.01, .05, .25, .5, .75, .95, .99)],
                          zeros=sum(1 for x in xs if x == 0))
        if len(xs) >= 5:
            lo, hi = q(.01), q(.99)
            inr = [x for x in xs if lo <= x <= hi]
            if hi > lo:
                if c["type"] == "Integer" and hi - lo + 1 <= 30:
                    cnt = Counter(inr)
                    c["hist"] = dict(kind="discrete", bins=[[k, cnt[k]] for k in sorted(cnt)])
                else:
                    w = (hi - lo) / 20
                    cnt = Counter(min(int((x - lo) / w), 19) for x in inr)
                    c["hist"] = dict(kind="range", lo=lo, w=w, bins=[[lo + i * w, cnt.get(i, 0)] for i in range(20)])
                c["hist"]["outside"] = len(xs) - len(inr)
    elif c["type"] == "Date":
        ds = sorted(v[:10] for v in nn)
        c["stats"] = dict(min=ds[0], max=ds[-1], unparsed=0, future=0)
        years = {d[:4] for d in ds}
        key = (lambda d: d[:7]) if len(years) <= 2 else (lambda d: int(d[:4]))
        cnt = Counter(key(d) for d in ds)
        c["hist"] = dict(kind="year", bins=[[k, cnt[k]] for k in sorted(cnt)], monthly=len(years) <= 2)
    return c


def resolve(ref):
    node = spec
    for part in ref.lstrip("#/").split("/"):
        node = node.get(part, {})
    return node


def schema_fields(sch):
    if "$ref" in sch:
        sch = dict(resolve(sch["$ref"]), _name=sch["$ref"].split("/")[-1])
    ex = sch.get("example", {}) or {}
    props = sch.get("properties", {})
    return dict(schema=sch.get("title") or sch.get("_name"), fields=[dict(name=k, type=v.get("type", "?") + ("[]" if v.get("type") == "array" else "")
                             + (" · nullable" if v.get("nullable") else ""), example=json.dumps(ex.get(k)))
                        for k, v in props.items()], example=json.dumps(ex))


def body_fields(op):
    rb = op.get("requestBody")
    if not rb:
        return None
    name = rb.get("$ref", "").split("/")[-1] or None
    out = _body(rb)
    if name:
        out["schema"] = name
    return out


def _body(rb):
    if "$ref" in rb:
        name = rb["$ref"].split("/")[-1]
        rb = resolve(rb["$ref"])
        if "content" not in rb:
            rb = dict(rb, _name=name)
    if "content" in rb:
        content = next(iter(rb["content"].values()), {})
        sch = content.get("schema", {})
        out = schema_fields(sch)
        if content.get("example") is not None:
            out["example"] = json.dumps(content["example"])
        return out
    return schema_fields(rb)


FILT = A.get("filters")
FILTERS = schema_fields({"$ref": f"#/components/schemas/{FILT['schema']}"}) if FILT else None

ops = {}
for p, methods in spec["paths"].items():
    for meth, op in methods.items():
        if meth.lower() not in ("get", "post", "put", "patch", "delete"):
            continue
        ops[op.get("summary") or f"{meth.upper()} {p}"] = (p, meth, op)

groups_cfg = A.get("groups")
if not groups_cfg:
    auto = {}
    for nm, (p, meth, op) in ops.items():
        g = (op.get("tags") or [p.strip("/").split("/")[0] or "root"])[0]
        auto.setdefault(g, []).append(nm)
    groups_cfg = [dict(id=re.sub(r"[^a-z0-9]+", "-", g.lower()).strip("-"), label=g, endpoints=e) for g, e in auto.items()]

sets, groups, used = {}, [], set()
for g in groups_cfg:
    keys = []
    for nm in g["endpoints"]:
        p, meth, op = ops[nm]
        used.add(nm)
        key = "api-" + re.sub(r"[^a-z0-9]+", "-", nm.lower()).strip("-")
        params = op.get("parameters", [])
        params = [resolve(x["$ref"]) if "$ref" in x else x for x in params]
        auth = next((x for x in params if x.get("in") == "header" and x.get("name", "").lower() == "authorization"), None)
        authtxt = "None" if not auth else ("Header authorization: null" if str(auth.get("example")) == "null"
                                           else A.get("token_auth_text", "Token in authorization header"))
        if op.get("security") or spec.get("security"):
            authtxt = authtxt if auth else "Security scheme: " + ", ".join(k for s in (op.get("security") or spec["security"]) for k in s)
        authtxt = A.get("auth_overrides", {}).get(nm, authtxt)
        prm = [dict(name=x.get("name"), loc=x.get("in"), required=bool(x.get("required")),
                    example=str(x.get("example", x.get("schema", {}).get("example"))))
               for x in params]
        servers = op.get("servers") or spec.get("servers") or []
        status, ex = None, None
        for code, r in op.get("responses", {}).items():
            status = str(code)
            if "$ref" in r:
                r = resolve(r["$ref"])
            content = r.get("content", {})
            for ct in content.values():
                if "example" in ct:
                    ex = ct["example"]
                elif ct.get("examples"):
                    ex = next(iter(ct["examples"].values())).get("value", ex)
        recs, rpath, tot = find_records(ex)
        kind = "empty" if ex is None else "file" if isinstance(ex, str) else "error" if status and status[0] in "45" else "records"
        cols, example_obj, sample = [], None, None
        if kind == "records" and recs is not None:
            recs = [flatten(r) if isinstance(r, dict) else r for r in recs]
            names_ = []
            for rec in recs:
                if isinstance(rec, dict):
                    names_ += [k for k in rec if k not in names_]
            cols = [profile(recs, k) for k in names_]
            if len(recs) > 1:   # the example records themselves, as sample rows (up to 100)
                show = lambda v: json.dumps(v) if isinstance(v, (list, dict)) else v
                sample = dict(rows=[[show(r.get(c["name"])) if isinstance(r, dict) else None for c in cols] for r in recs[:100]])
        if kind == "error" and isinstance(ex, dict):
            example_obj = dict(ex)
        if kind == "file":
            example_obj = {"response": ex}
        sets[key] = dict(label=A.get("labels", {}).get(nm, nm), about=A.get("about", {}).get(nm, op.get("description", "") or ""),
                         api=dict(name=nm, method=meth.upper(), path=p, server=servers[0]["url"] if servers else "", auth=authtxt,
                                  params=prm, body=body_fields(op),
                                  filters=FILTERS if FILT and nm in FILT.get("endpoints", []) else None,
                                  status=status, kind=kind, recordsPath=rpath if kind == "records" else None,
                                  totalRecords=tot, example=example_obj),
                         rows=len(recs) if (kind == "records" and recs is not None) else 0, columns=cols, notes=[],
                         **({"sample": sample} if sample else {}))
        keys.append(key)
    groups.append(dict(id="api-" + g["id"], label=g["label"], datasets=keys))
left = set(ops) - used
if left:
    print("WARNING: endpoints not in any group:", sorted(left))
json.dump(dict(groups=groups, sets=sets), open(OUT, "w"), default=str)
for k, d in sets.items():
    print(k, d["api"]["method"], d["api"]["status"], d["api"]["kind"], d["rows"], len(d["columns"]))
