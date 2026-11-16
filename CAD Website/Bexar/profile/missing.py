import json,sys
M=json.load(open('manifest.json'));P=json.load(open('profile.json'))
D,BS,BP=M.get('descriptions',{}),M.get('descriptions_by_set',{}),M.get('descriptions_by_prefix',{})
miss={}
for k,v in P.items():
    pre=k.split('-')[0]
    for c in v['columns']:
        n=c['name']
        if not (BS.get(f'{k}:{n}') or BP.get(f'{pre}:{n}') or D.get(n)):
            miss.setdefault(n,[]).append(k)
for n,ks in miss.items(): print(n,'|',' '.join(sorted(set(k.split('-',1)[-1] if not k.startswith(('ag','ps')) else k for k in ks))))
print(len(miss),file=sys.stderr)
