import sys,json
sys.path.insert(0,'scripts/eco-report'); import build
e,r=build.load('experiments.json'),build.load('raws.json')
ids=[f['id'] for f in e['figures']]
for f in r['figures']: ids+= [g['id'] for g in build.normalize_raw(f)]
print(' '.join(ids))
