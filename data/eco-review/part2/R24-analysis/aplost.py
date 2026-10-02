import glob,re,collections
var={}
for f in glob.glob('*/objects/c_variation*.txt'):
    s=open(f,encoding='latin-1').read()
    for part in s.split('[CREATURE_VARIATION:')[1:]:
        n=part.split(']')[0]; var[n]=set(re.findall(r'ATTACK:[A-Z_0-9]+:(?:BODYPART|CHILD_BODYPART_GROUP|CHILD_TISSUE_LAYER_GROUP):(?:BY_CATEGORY|BY_TYPE|BY_TOKEN):([A-Z_0-9]+)',part))
cre={}; src={}
for f in sorted(glob.glob('vanilla_creatures/objects/creature_*.txt'))+sorted(glob.glob('vanilla_creatures_extinct/objects/creature_*.txt')):
    s=open(f,encoding='latin-1').read()
    for part in s.split('[CREATURE:')[1:]:
        cid=part.split(']')[0]; cre[cid]=part; src[cid]='extinct' if 'extinct' in f else 'vanilla'
RX=r'\[ATTACK:[A-Z_0-9]+:(?:BODYPART|CHILD_BODYPART_GROUP|CHILD_TISSUE_LAYER_GROUP):(?:BY_CATEGORY|BY_TYPE|BY_TOKEN):([A-Z_0-9]+)'
def cats(p):
    c=set(re.findall(RX,p))
    for v in re.findall(r'\[APPLY_CREATURE_VARIATION:([A-Z_0-9]+)',p):
        if v.endswith('_ATTACK'): c|=var.get(v,set())
    return c
IGN={'HAND','FOOT','STANCE','GRASP','FINGER','TOE','UPPERBODY','LOWERBODY','FOOT_FRONT','FOOT_REAR'}
out=collections.defaultdict(list)
for cid,p in cre.items():
    if 'APPLY_CREATURE_VARIATION:ANIMAL_PERSON' not in p: continue
    m=re.search(r'\[COPY_TAGS_FROM:([A-Z_0-9]+)\]',p)
    if not m or m.group(1) not in cre: continue
    rc=cats(cre[m.group(1)])-IGN; ac=cats(p)
    out[src[cid]].append((cid,sorted(rc),sorted(rc-ac)))
for k,v in out.items():
    l=[x for x in v if x[2]]
    print(k,'APs',len(v),'APs missing >=1 root natural-weapon part (feet ignored):',len(l))
    for x in (l if k=='extinct' else l[:30]): print('  ',x[0],'lost',x[2])
