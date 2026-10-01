import json,numpy as np
from scipy import stats
R=json.load(open("recs.json"))
rng=np.random.default_rng(3)
def perm(a,b,N=50000):
    a=np.array(a,float);b=np.array(b,float);obs=b.mean()-a.mean();z=np.concatenate([a,b]);c=0
    for _ in range(N):
        rng.shuffle(z); c+=(z[len(a):].mean()-z[:len(a)].mean())>=obs-1e-12
    return obs,c/N
for blks in (["LONE"],["LONE10"],["LONE","LONE10"]):
    rows=[x for x in R if x["block"] in blks]
    c=[x for x in rows if x["arm"]=="ctl"]; p=[x for x in rows if x["arm"]=="pkg"]
    print("==",blks,len(c),len(p))
    for key in ("kills","native_kills","att","att_native","lost"):
        a=[x[key] for x in c]; b=[x[key] for x in p]
        obs,pp=perm(a,b)
        ka,kb=sum(a),sum(b)
        rr=(kb/len(b))/(ka/len(a)) if ka else float('inf')
        line=f"  {key:12s} ctl {ka} pkg {kb} (per run {np.mean(a):.2f} vs {np.mean(b):.2f}) RR {rr:.2f} one-sided perm p={pp:.3f}"
        if key=="kills":
            bt=stats.binomtest(kb,ka+kb,len(b)/(len(a)+len(b))); ci=bt.proportion_ci(.95,"exact"); f=lambda q:q/(1-q)*len(a)/len(b)
            line+=f" exact RR95 [{f(ci.low):.2f},{f(ci.high):.2f}]"
            # bootstrap CI for difference in means
            bs=[np.mean(rng.choice(b,len(b)))-np.mean(rng.choice(a,len(a))) for _ in range(20000)]
            line+=f" boot diff95 [{np.percentile(bs,2.5):+.2f},{np.percentile(bs,97.5):+.2f}]"
        print(line)
    eng=lambda rs:sum(1 for x in rs if x["att"]>0)
    print("  engaged runs (>=1 attack on placed prey)",eng(c),"/",len(c),"vs",eng(p),"/",len(p))
    print("  first-kill dt ctl",sorted(min(x["kill_dt"]) for x in c if x["kill_dt"]),"pkg",sorted(min(x["kill_dt"]) for x in p if x["kill_dt"]))
    print("  hunter died dt ctl",[x["died_dt"] for x in c if x["died_dt"]],"pkg",[x["died_dt"] for x in p if x["died_dt"]])
