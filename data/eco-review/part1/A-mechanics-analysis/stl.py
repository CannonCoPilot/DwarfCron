import json,numpy as np,collections,itertools
from glm import fit,report,lrt
from scipy import stats
R=json.load(open("recs.json"))
S=[x for x in R if x["block"] in("STL","STL2")]
def ctype(x): return x["pred"]+"_"+x["prey"]
print("per block x arm: runs | attacks (hunter>prey) | kills | runs with kill | engaged runs (>=1 att) | hunters lost | native kills | att on natives | hidden/samples")
for blk in ("STL","STL2"):
    A=collections.OrderedDict()
    for x in S:
        if x["block"]!=blk: continue
        a=A.setdefault(x["arm"],collections.Counter()); a["runs"]+=1; a["att"]+=x["att"]; a["kills"]+=x["kills"]; a["krun"]+=x["kills"]>0
        a["eng"]+=x["att"]>0; a["lost"]+=x["lost"]; a["natk"]+=x["native_kills"]; a["attn"]+=x["att_native"]; a["hid"]+=x["hid"]; a["samp"]+=x["samp"]
    for arm,a in A.items(): print(f" {blk:5s} {arm:7s} {a['runs']:2d} | {a['att']:4d} | {a['kills']} | {a['krun']} | {a['eng']} | {a['lost']} | {a['natk']} | {a['attn']} | {a['hid']}/{a['samp']}")
print("\nper cell type x arm (STL+STL2 pooled; kills / attacks per rep)")
T=collections.defaultdict(list)
for x in S: T[(ctype(x),x["arm"])].append((x["block"],x["rep"],x["att"],x["kills"],x["lost"]))
for k in sorted(T): print(" ",k,T[k])
# pooled arm sums
print("\nPOOLED STL+STL2 by arm")
P=collections.OrderedDict()
for arm in ["ctl","sneak","nslow","ambush","fight","all","norel"]:
    rows=[x for x in S if x["arm"]==arm]
    if not rows: continue
    k=sum(x["kills"] for x in rows); a=sum(x["att"] for x in rows); n=len(rows); kr=sum(x["kills"]>0 for x in rows); eng=sum(x["att"]>0 for x in rows)
    lo,hi=stats.chi2.ppf(.025,2*k)/2 if k else 0, stats.chi2.ppf(.975,2*k+2)/2
    P[arm]=rows
    print(f" {arm:7s} runs {n:2d} kills {k:2d} ({k/n:.2f}/run, exact95 {lo/n:.2f}-{hi/n:.2f}) runs-with-kill {kr}/{n} engaged {eng}/{n} attacks {a} (mean {a/n:.1f}, median {np.median([x['att'] for x in rows]):.0f})")
# comparisons vs ctl: kills conditional binomial (Poisson rate ratio exact), Fisher on runs with kill, attacks permutation (mean)
ctl=P["ctl"]
def perm(a,b,stat=np.mean,N=20000,rng=np.random.default_rng(1)):
    a=np.array(a,float);b=np.array(b,float);obs=stat(a)-stat(b);z=np.concatenate([a,b]);c=0
    for _ in range(N):
        rng.shuffle(z); c+= (stat(z[:len(a)])-stat(z[len(a):]))>=obs-1e-12
    return obs,c/N
print("\nvs ctl (pooled STL+STL2, ctl 16 runs)")
for arm,rows in P.items():
    if arm=="ctl": continue
    k1,n1=sum(x["kills"] for x in rows),len(rows); k0,n0=sum(x["kills"] for x in ctl),len(ctl)
    # exact conditional test for rate ratio: k1 ~ Binom(k1+k0, n1/(n1+n0)) under H0
    bt=stats.binomtest(k1,k1+k0,n1/(n1+n0)) if k1+k0>0 else None
    rr=(k1/n1)/(k0/n0) if k0 else float('inf')
    # CI for rate ratio via exact binomial CI on p
    if bt:
        ci=bt.proportion_ci(0.95,method="exact"); f=lambda p:(p/(1-p))*(n0/n1) if p<1 else float('inf'); rrci=(f(ci.low),f(ci.high))
    kr1=sum(x["kills"]>0 for x in rows); kr0=sum(x["kills"]>0 for x in ctl)
    fe=stats.fisher_exact([[kr1,n1-kr1],[kr0,n0-kr0]])
    e1=sum(x["att"]>0 for x in rows); e0=sum(x["att"]>0 for x in ctl)
    fe2=stats.fisher_exact([[e1,n1-e1],[e0,n0-e0]])
    obs,pp=perm([x["att"] for x in rows],[x["att"] for x in ctl])
    print(f" {arm:7s} kills {k1}/{n1} vs {k0}/{n0}: RR {rr:.2f} exact95 [{rrci[0]:.2f},{rrci[1]:.2f}] p={bt.pvalue:.3f} | runs-with-kill {kr1}/{n1} vs {kr0}/{n0} Fisher p={fe.pvalue:.3f} | engaged {e1}/{n1} vs {e0}/{n0} p={fe2.pvalue:.3f} | mean attacks diff {obs:+.1f} one-sided perm p={pp:.3f}")
# GLM: kills ~ celltype + arm (Poisson), STL+STL2 excluding norel
rows=[x for x in S if x["arm"]!="norel"]
cts=sorted({ctype(x) for x in rows}); arms=["sneak","nslow","ambush","fight","all"]
X=np.array([[1]+[1.0*(ctype(x)==c) for c in cts[1:]]+[1.0*(x["arm"]==a) for a in arms]+[1.0*(x["block"]=="STL2")] for x in rows])
names=["const"]+cts[1:]+arms+["STL2"]
r=fit(X,[x["kills"] for x in rows],"pois")
print("\n"+report("kills ~ celltype + arm + block (Poisson)",r,names))
r=fit(X,[x["att"] for x in rows],"pois")
print(report("attacks ~ celltype + arm + block (quasi-Poisson)",r,names,quasi=True))
r=fit(X,[1 if x["att"]>0 else 0 for x in rows],"binom",m=[1]*len(rows))
print(report("engaged ~ celltype + arm + block (logistic)",r,names))
# Speed: lion vs cougar
for p in ("LION","COUGAR"):
    rr=[x for x in S if x["pred"]==p and x["arm"]!="norel"]
    print(p,"kills",sum(x["kills"] for x in rr),"of runs",len(rr),"attacks",sum(x["att"] for x in rr),"lost",sum(x["lost"] for x in rr))
