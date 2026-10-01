import json,numpy as np
from scipy import stats
R=json.load(open("recs.json"))
rng=np.random.default_rng(7)
def nb(mu,k,size):  # NB with mean mu, shape k (var=mu+mu^2/k)
    if k is None: return rng.poisson(mu,size)
    p=k/(k+mu); return rng.negative_binomial(k,p,size)
def ptest(a,b):  # one-sided exact conditional Poisson test (b vs a higher)
    ka,kb=a.sum(),b.sum()
    if ka+kb==0: return 1.0
    return stats.binomtest(int(kb),int(ka+kb),0.5,alternative="greater").pvalue
def permtest(a,b,N=400):
    obs=b.mean()-a.mean(); z=np.concatenate([a,b]); c=0
    for _ in range(N):
        rng.shuffle(z); c+=(z[len(a):].mean()-z[:len(a)].mean())>=obs-1e-12
    return c/N
def power(mu0,rr,n,k=None,sims=1000,test="pois"):
    hit=0
    for _ in range(sims):
        a=nb(mu0,k,n); b=nb(mu0*rr,k,n)
        p=ptest(a,b) if test=="pois" else permtest(a,b,200)
        hit+=p<0.05
    return hit/sims
def mdrr(mu0,n,k=None,test="pois",target=.8):
    for rr in [1.25,1.5,1.75,2,2.5,3,4,5,6,8,10,15,20]:
        if power(mu0,rr,n,k,sims=600 if test=="pois" else 200,test=test)>=target: return rr
    return ">20"
# estimate NB k from ctl kills (method of moments)
def mom_k(x):
    x=np.array(x,float); m,v=x.mean(),x.var(ddof=1)
    return None if v<=m else m*m/(v-m)
S=[x for x in R if x["block"] in("STL","STL2")]
ctlk=[x["kills"] for x in S if x["arm"]=="ctl"]; ctla=[x["att"] for x in S if x["arm"]=="ctl"]
L=[x for x in R if x["block"]=="LONE10"]; lk=[x["kills"] for x in L if x["arm"]=="ctl"]
print("STL ctl kills mean",np.mean(ctlk),"var",np.var(ctlk,ddof=1),"k",mom_k(ctlk))
print("STL ctl attacks mean",np.mean(ctla),"var",np.var(ctla,ddof=1),"k",mom_k(ctla))
print("LONE10 ctl placed kills mean",np.mean(lk),"var",np.var(lk,ddof=1),"k",mom_k(lk))
allk=[x["kills"] for x in S if x["arm"]!="norel"]; print("STL all-arm kills k",mom_k(allk), np.mean(allk))
for lab,mu0,k in [("STL kills/run (30k t), mu0=0.25, Poisson",0.25,None),("STL kills, NB k=1",0.25,1.0),
                  ("LONE10 placed kills/run (100.8k t), mu0=1.4, NB k=%s"%(round(mom_k(lk),2) if mom_k(lk) else None),1.4,mom_k(lk)),
                  ("LONE10 Poisson",1.4,None)]:
    print(lab, {n:mdrr(mu0,n,k) for n in (2,8,16,32,64)})
ka=mom_k(ctla) or 0.2
print("STL attacks/run mu0=%.1f NB k=%.2f (perm test)"%(np.mean(ctla),ka), {n:mdrr(np.mean(ctla),n,ka,test="perm") for n in (8,16,32,64)})
# runs-with-kill binary: p0=2/16
def bpow(p0,p1,n,sims=2000):
    h=0
    for _ in range(sims):
        a=rng.binomial(n,p0); b=rng.binomial(n,p1)
        h+=stats.fisher_exact([[b,n-b],[a,n-a]],alternative="greater").pvalue<0.05
    return h/sims
for n in (8,16,32,64,128):
    for p1 in (.25,.375,.5,.75):
        pw=bpow(.125,p1,n,800)
        if pw>=.8: print(f"runs-with-kill p0=0.125: n/arm {n} detects p1={p1} (power {pw:.2f})"); break
    else: print(f"runs-with-kill n/arm {n}: none of .25-.75 reaches 80%")
print("STL kills NB k=0.5", {n:mdrr(0.25,n,0.5) for n in (8,16,32,64)})
print("Engagement-rate design: hunter-prey contact bouts per run mu0=3 NB k=1", {n:mdrr(3,n,1.0) for n in (2,4,8,16)})
