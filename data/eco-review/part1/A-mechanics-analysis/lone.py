import json,numpy as np,collections
from glm import fit,report,lrt
from hunt import MASS,SPEED
from scipy import stats
R=json.load(open("recs.json"))
LP=["RABBIT","HARE","GROUNDHOG","GOAT_MOUNTAIN","KANGAROO","DEER","ELK","WATER_BUFFALO"]
for blks in (["LONE"],["LONE10"],["LONE","LONE10"]):
    rows=[x for x in R if x["block"] in blks]
    print("\n===",blks,"runs",len(rows), collections.Counter(x["arm"] for x in rows))
    K=collections.Counter(); A=collections.Counter(); E=collections.Counter()
    for x in rows:
        for p in LP: K[p]+=x["kills_by"].get(p,0); A[p]+=x["att_by"].get(p,0); E[p]+=1 if x["att_by"].get(p,0)>0 else 0
    n=len(rows)
    for p in LP: print(f"  {p:14s} mass {MASS[p]:>8d} ratio {60000/MASS[p]:7.2f} speed {SPEED[p]:3d}  kills {K[p]:2d}/{6*n}  attacks {A[p]:4d}  runs-attacked {E[p]}/{n}")
    # Poisson per prey-run with run fixed effect absorbed: use per-species totals with offset (multinomial-equivalent)
    y=[K[p] for p in LP]; off=np.log([6*n]*8)
    for terms in (["log2mass"],["speed"],["log2mass","speed"]):
        X=np.array([[1]+[np.log2(MASS[p]) if t=="log2mass" else SPEED[p]/100 for t in terms] for p in LP])
        r=fit(X,y,"pois",off=off); print(report(" kills ~ "+"+".join(terms),r,["const"]+terms,quasi=True))
    y=[A[p] for p in LP]
    for terms in (["log2mass"],["speed"],["log2mass","speed"]):
        X=np.array([[1]+[np.log2(MASS[p]) if t=="log2mass" else SPEED[p]/100 for t in terms] for p in LP])
        r=fit(X,y,"pois",off=off); print(report(" attacks ~ "+"+".join(terms),r,["const"]+terms,quasi=True))
    print("  spearman kills~mass",stats.spearmanr([MASS[p] for p in LP],[K[p] for p in LP]))
    print("  spearman kills~speed(ticks; higher slower)",stats.spearmanr([SPEED[p] for p in LP],[K[p] for p in LP]))
    print("  spearman mass~speed",stats.spearmanr([MASS[p] for p in LP],[SPEED[p] for p in LP]))
