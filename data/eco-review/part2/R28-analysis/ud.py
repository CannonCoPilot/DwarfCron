import sys, json
from pathlib import Path
ROOT=Path('/Users/nathanielcannon/Claude/Projects/DwarfCron')
sys.path.insert(0,str(ROOT/'data/eco-desk'))
import census as C
paths=[(p,'vanilla') for p in sorted((C.VAN/'vanilla_creatures/objects').glob('*.txt'))]
paths+=[(p,'extinct') for p in sorted((C.VAN/'vanilla_creatures_extinct/objects').glob('*.txt'))]
CR,VA,SRC=C.read_objects(paths)
cache,info={},{}
rows=[]
for cid in CR:
    tags=C.resolve(cid,CR,VA,cache,info)
    castes,occ=C.caste_walk(tags)
    names=set(occ)
    ud=occ.get('UNDERGROUND_DEPTH')
    if not ud: continue
    t=ud[-1][1]
    mn=int(t[1]); mx=int(t[2]) if len(t)>2 else mn
    biomes=sorted({o[1][1] for o in occ.get('BIOME',[]) if len(o[1])>1})
    fl=[f for f in ('FIREIMMUNE','FIREIMMUNE_SUPER','MAGMA_SAFE' ,'LARGE_PREDATOR','ANIMAL_PERSON','EVIL','GOOD','FLIER','AQUATIC','AMPHIBIOUS','MEGABEAST','SEMIMEGABEAST','DEMON','VERMIN_GROUNDER','VERMIN_SOIL','VERMIN_EATER','VERMIN_FISH','IMMOBILE','INTELLIGENT','LOCAL_POPS_PRODUCE_HEROES','UNIQUE_DEMON','NOT_LIVING','FISHITEM') if f in names]
    cls=sorted({o[1][1] for o in occ.get('CREATURE_CLASS',[]) if len(o[1])>1})
    # fire/magma tissue hints
    raw=' '.join(':'.join(o[1]) for k in occ for o in occ[k])
    fiery = 'FIREIMMUNE' in names or 'FIREIMMUNE_SUPER' in names or 'MAGMA' in raw or 'SPECIAL_ATTACK_FIRE' in raw or 'FIRE' in ' '.join(o[1][0] for k in occ for o in occ[k] if 'FIRE' in k)
    hf=[k for k in names if 'FIRE' in k or 'MAGMA' in k or 'HOT' in k or 'HEAT' in k]
    freq=occ.get('FREQUENCY'); freq=freq[-1][1][1] if freq else None
    rows.append(dict(id=cid,src=SRC[cid][0],file=Path(SRC[cid][1]).name if len(SRC[cid])>1 else '',mn=mn,mx=mx,biomes=biomes,flags=fl,firehints=sorted(hf),cls=cls,freq=freq,ap=cid.endswith('_MAN') or 'ANIMAL_PERSON' in cls))
rows.sort(key=lambda r:(r['mn'],r['mx'],r['id']))
json.dump(rows,open('ud.json','w'),indent=0)
for r in rows:
    print(f"{r['mn']}:{r['mx']}\t{r['id']}\t{r['src']}\t{r['file']}\tF{r['freq']}\t{','.join(r['biomes'])}\t{','.join(r['flags'])}\t{','.join(r['firehints'])}")
print(len(rows), sum(r['src']=='vanilla' for r in rows))
