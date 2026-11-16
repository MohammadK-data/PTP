#!/bin/zsh
# profile every dataset except the ones named as args, one process each, smallest file first
cd "${0:a:h}"
S=~/.claude/skills/create_county_data_profile/scripts/profile_files.py
keys=$(venv/bin/python -I -c "
import json,os,sys
m=json.load(open('manifest.json')); skip=set(sys.argv[1:])
done=set(json.load(open('profile.json'))) if os.path.exists('profile.json') else set()
ks=[k for k,d in m['datasets'].items() if d.get('path') and k not in skip and k not in done]
ks.sort(key=lambda k: os.path.getsize(os.path.join(m['root'],m['datasets'][k]['path'])))
print(' '.join(ks))" "$@")
for k in ${=keys}; do venv/bin/python -I $S manifest.json profile.json $k > logs/prof_$k.log 2>&1 || echo "FAILED $k"; grep "^done" logs/prof_$k.log || echo "NODONE $k"; done
