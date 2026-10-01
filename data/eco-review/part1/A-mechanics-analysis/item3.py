import json,numpy as np, collections
from glm import fit,report,lrt
from hunt import MASS,SPEED
from scipy import stats
R=json.load(open("recs.json"))
L2=np.log2
def design(rows, terms):
    cols={"const":lambda x:1.0,
      "log2n":lambda x:L2(x["npred"]),
      "log2prey":lambda x:L2(MASS[x["prey"]]),
      "log2packmass":lambda x:L2(x["npred"]*MASS[x["pred"]]),
      "log2predmass":lambda x:L2(MASS[x["pred"]]),
      "log2ratio":lambda x:L2(x["npred"]*MASS[x["pred"]]/MASS[x["prey"]]),
      "preyspeed100":lambda x:SPEED[x["prey"]]/100.0,
      "hyena":lambda x:1.0 if x["pred"]=="HYENA" else 0.0,
      "rep2":lambda x:1.0 if x["rep"]=="2" else 0.0,
      "elephant":lambda x:1.0 if x["prey"]=="ELEPHANT" else 0.0}
    return np.array([[cols[t](x) for t in terms] for x in rows]), terms
def run(rows,label,fam="binom",yk="kills"):
    y=[x[yk] for x in rows]; m=[x["nprey"] for x in rows]
    print(f"\n=== {label}: cell-reps {len(rows)}, total {yk} {sum(y)} of {sum(m)} prey")
    models=[["const"],["const","log2n"],["const","log2prey"],["const","log2n","log2prey"],["const","log2ratio"],
            ["const","log2packmass","log2prey"],["const","preyspeed100"],["const","log2n","preyspeed100"]]
    res={}
    for t in models:
        X,nm=design(rows,t); r=fit(X,y,fam,m=m); res[tuple(t)]=r
        print(report(" + ".join(t[1:]) or "null",r,nm,quasi=(fam=="pois")))
    r0=res[("const",)]
    for t in models[1:]:
        d,k,p=lrt(r0,res[tuple(t)]); print(f"   LRT vs null {'+'.join(t[1:]):28s} chi2={d:.2f} df={k} p={p:.3f}")
    d,k,p=lrt(res[("const","log2n")],res[("const","log2n","log2prey")]); print(f"   add log2prey to log2n: chi2={d:.2f} p={p:.3f}")
    d,k,p=lrt(res[("const","log2prey")],res[("const","log2n","log2prey")]); print(f"   add log2n to log2prey: chi2={d:.2f} p={p:.3f}")
    d,k,p=lrt(res[("const","log2ratio")],res[("const","log2packmass","log2prey")]); print(f"   ratio constraint (b_pack = -b_prey) test: chi2={d:.2f} p={p:.3f}")
    return res
cal=[x for x in R if x["block"]=="CAL"]
calw=[x for x in cal if x["pred"] in("WOLF",)]
calp=[x for x in cal if x["pred"] in("WOLF","HYENA")]
pk=[x for x in R if x["block"]=="PK"]
cala1=[x for x in R if x["block"]=="CALa1" and x["pred"]=="WOLF"]
run(calw,"CAL wolves only (n 3/5/7 x deer/moose/buffalo/elephant x 2 reps)")
run(calp,"CAL packs wolves+hyenas")
run(cal,"CAL all incl. solitary")
run(calw+[x for x in cala1 if x["ticks"]>29000],"CAL wolves + attempt-1 rep (wolf7_ELEPHANT truncated dropped)")
run(pk,"PK (3,000 t, n 1/3/5/7 x deer/elk/moose/buffalo x 2 reps)")
# attacks: Poisson (quasi)
print("\n##### ATTACKS (pred>prey), quasi-Poisson")
for rows,l in [(calw,"CAL wolves"),(calp,"CAL packs"),(pk,"PK")]:
    for t in [["const","log2n"],["const","log2prey"],["const","log2n","log2prey"],["const","preyspeed100"]]:
        X,nm=design(rows,t); r=fit(X,[x["att"] for x in rows],"pois")
        print(report(l+" attacks ~ "+"+".join(t[1:]),r,nm,quasi=True))
# engagement: any attack (binary)
print("\n##### ENGAGED (>=1 pred>prey attack), logistic")
for rows,l in [(calw,"CAL wolves"),(calp,"CAL packs"),(pk,"PK")]:
    for t in [["const","log2n"],["const","log2prey"],["const","log2n","log2prey"]]:
        X,nm=design(rows,t); r=fit(X,[1 if x["att"]>0 else 0 for x in rows],"binom",m=[1]*len(rows))
        print(report(l+" engaged ~ "+"+".join(t[1:]),r,nm))
# tables
def tab(rows,label):
    print("\n"+label)
    T=collections.defaultdict(lambda:[0,0,0,0,0])
    for x in rows:
        k=(x["pred"],x["npred"],x["prey"]); T[k][0]+=x["kills"]; T[k][1]+=x["nprey"]; T[k][2]+=x["att"]; T[k][3]+=1; T[k][4]+=1 if x["att"]>0 else 0
    for k,v in sorted(T.items(),key=lambda kv:(kv[0][0],kv[0][1],MASS[kv[0][2]])):
        ratio=k[1]*MASS[k[0]]/MASS[k[2]]
        lo,hi=stats.beta.ppf(.025,v[0],v[1]-v[0]+1) if v[0]>0 else 0.0, stats.beta.ppf(.975,v[0]+1,v[1]-v[0])
        print(f"  {k[0]:7s} n{k[1]:<2d} {k[2]:14s} ratio {ratio:6.3f} kills {v[0]}/{v[1]} ({v[0]/v[1]:.2f}, CP95 {lo:.2f}-{hi:.2f}) attacks {v[2]} engaged {v[4]}/{v[3]}")
tab(cal,"CAL by cell (2 reps pooled)"); tab(pk,"PK by cell (2 reps pooled)")
# marginal
for rows,l in [(calw,"CAL wolves"),(pk,"PK")]:
    for key in ("npred","prey"):
        T=collections.defaultdict(lambda:[0,0,0])
        for x in rows: T[x[key]][0]+=x["kills"]; T[x[key]][1]+=x["nprey"]; T[x[key]][2]+=x["att"]
        print(l,key,{k:f"{v[0]}/{v[1]} att {v[2]}" for k,v in T.items()})
# Spearman cell position vs kills (confound check): CAL order within rep
order=collections.OrderedDict()
for x in cal:
    order.setdefault(x["rep"],[]).append(x)
for rep,rows in order.items():
    pos=list(range(len(rows))); k=[x["kills"] for x in rows]
    print("CAL rep",rep,"spearman(position, kills) all cells", stats.spearmanr(pos,k))
    rw=[x for x in rows if x["pred"]=="WOLF"]; print("   wolves only", stats.spearmanr(list(range(len(rw))),[x["kills"] for x in rw]))
