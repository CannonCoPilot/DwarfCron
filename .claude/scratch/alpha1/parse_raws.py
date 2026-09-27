import re, sys, json, glob, os
raws = sys.argv[1]
out = {}
for fn in sorted(glob.glob(os.path.join(raws, 'creature_*.txt'))):
    txt = open(fn, encoding='latin-1').read()
    cur = None; incaste = False
    for m in re.finditer(r'\[([^\]]+)\]', txt):
        parts = m.group(1).split(':'); tag = parts[0]
        if tag == 'CREATURE':
            cur = {'file': os.path.basename(fn), 'tags': set(), 'biomes': [], 'classes': set(), 'body': [], 'cluster': None, 'popnum': None, 'freq': None, 'name': None}
            out[parts[1]] = cur; continue
        if cur is None: continue
        if tag == 'BIOME': cur['biomes'].append(parts[1])
        elif tag == 'CREATURE_CLASS': cur['classes'].add(parts[1])
        elif tag == 'BODY_SIZE': cur['body'].append(int(parts[3]) if len(parts) > 3 and parts[3].lstrip('-').isdigit() else 0)
        elif tag == 'CLUSTER_NUMBER': cur['cluster'] = parts[1:]
        elif tag == 'POPULATION_NUMBER': cur['popnum'] = parts[1:]
        elif tag == 'FREQUENCY': cur['freq'] = parts[1]
        elif tag == 'NAME' and cur['name'] is None: cur['name'] = parts[1]
        else: cur['tags'].add(tag)
for k, v in out.items():
    v['tags'] = sorted(v['tags']); v['classes'] = sorted(v['classes']); v['adult'] = max(v['body']) if v['body'] else 0; del v['body']
json.dump(out, open(sys.argv[2], 'w'), indent=0)
print(len(out), 'creatures parsed')
