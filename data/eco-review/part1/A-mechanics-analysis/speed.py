import json,numpy as np
from glm import fit,report,lrt
from hunt import MASS,SPEED
R=json.load(open("recs.json"))
def faster(x): return 1.0 if SPEED[x["prey"]]<SPEED[x["pred"]] else 0.0
for lab,rows in [("CAL all",[x for x in R if x["block"]=="CAL"]),("CAL wolves",[x for x in R if x["block"]=="CAL" and x["pred"]=="WOLF"]),("PK",[x for x in R if x["block"]=="PK"]),
                 ("STL+STL2 ctl+sneak+fight+nslow+ambush+all",[x for x in R if x["block"] in("STL","STL2") and x["arm"]!="norel"])]:
    y=[x["kills"] for x in rows]; m=[x["nprey"] for x in rows]
    fk=sum(x["kills"] for x in rows if faster(x)); fm=sum(x["nprey"] for x in rows if faster(x))
    sk=sum(x["kills"] for x in rows if not faster(x)); sm=sum(x["nprey"] for x in rows if not faster(x))
    print(f"== {lab}: prey faster than hunter {fk}/{fm}; prey slower {sk}/{sm}")
    for terms in (["log2n","faster"],["log2n","faster","log2prey"]):
        X=np.array([[1]+[np.log2(x["npred"]) if t=="log2n" else faster(x) if t=="faster" else np.log2(MASS[x["prey"]]) for t in terms] for x in rows])
        if lab.startswith("STL"): X=np.array([[1]+[faster(x)]+([np.log2(MASS[x["prey"]])] if "log2prey" in terms else []) for x in rows]); nm=["const","faster"]+(["log2prey"] if "log2prey" in terms else [])
        else: nm=["const"]+terms
        print(report(" ~ "+"+".join(nm[1:]),fit(X,y,"binom",m=m),nm))
