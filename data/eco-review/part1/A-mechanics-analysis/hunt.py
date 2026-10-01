"""Parse CAL, PK, STL, STL2, LONE, LONE10 into per cell-rep records (placed-only scoring)."""
import re, collections, json, sys
E="/Users/nathanielcannon/Claude/Projects/DwarfCron/data/experiments/ECO/"
MASS={"WOLF":40000,"HYENA":60000,"COUGAR":60000,"LION":200000,"TIGER":225000,"DEER":140000,"ELK":300000,"MOOSE":525000,
 "WATER_BUFFALO":1000000,"ELEPHANT":5000000,"GIRAFFE":1000000,"RABBIT":500,"HARE":3500,"GROUNDHOG":3000,"GOAT_MOUNTAIN":50000,"KANGAROO":90000}
SPEED={'KANGAROO':183,'HARE':146,'ELK':122,'WATER_BUFFALO':183,'RABBIT':204,'ELEPHANT':488,'LION':109,'TIGER':157,'GIRAFFE':146,
 'HYENA':183,'DEER':137,'COUGAR':195,'WOLF':149,'GROUNDHOG':548,'MOOSE':157,'GOAT_MOUNTAIN':439}
def kv(s): return dict(re.findall(r"(\w+)=(\S+)", s))
def parse(path, blk):
    R=collections.OrderedDict()
    for line in open(path):
        f=line.rstrip("\n").split("\t")
        if len(f)<5: continue
        cell,rep,kind,rest=f[1],f[2],f[3],f[4]
        r=R.setdefault((cell,rep),dict(block=blk,cell=cell,rep=rep,spawn={},att=collections.Counter(),deaths=[],ticks=None,hid=0,samp=0,alive=[]))
        d=kv(rest)
        if kind=="spawn": r["spawn"][d["token"]]=int(d["placed"])
        elif kind=="attacks": r["att"][d["pair"]]+=int(d["n"])
        elif kind=="death": r["deaths"].append(d)
        elif kind=="alerts": r["ticks"]=int(d.get("ticks",0))
        elif kind=="hidden": r["hid"]+=int(d["hidden"]); r["samp"]+=int(d["n"])
        elif kind=="alive": r["alive"].append(d)
    return R
def rec(r, pred, preys):
    out=dict(block=r["block"],cell=r["cell"],rep=r["rep"],pred=pred,npred=r["spawn"].get(pred,0),ticks=r["ticks"])
    out["prey"]=preys if len(preys)>1 else preys[0]
    out["nprey"]=sum(r["spawn"].get(p,0) for p in preys)
    out["att"]=sum(r["att"].get(f"{pred}>{p}",0) for p in preys)
    out["att_back"]=sum(r["att"].get(f"{p}>{pred}",0) for p in preys)
    out["att_native"]=sum(n for k,n in r["att"].items() if k.startswith(pred+">") and k.split(">")[1] not in preys)
    k=[d for d in r["deaths"] if d.get("killer")==pred and d.get("killer_spawned")=="1" and d.get("victim_spawned")=="1" and d.get("victim") in preys]
    out["kills"]=len(k); out["kill_dt"]=sorted(int(d.get("dt",-1)) for d in k)
    out["kills_by"]=collections.Counter(d["victim"] for d in k)
    out["native_kills"]=sum(1 for d in r["deaths"] if d.get("killer")==pred and d.get("killer_spawned")=="1" and d.get("victim_spawned")=="0")
    out["lost"]=sum(1 for d in r["deaths"] if d.get("victim")==pred and d.get("victim_spawned")=="1")
    out["lost_to_prey"]=sum(1 for d in r["deaths"] if d.get("victim")==pred and d.get("victim_spawned")=="1" and d.get("killer") in preys)
    out["died_dt"]=[int(d.get("dt",-1)) for d in r["deaths"] if d.get("victim")==pred and d.get("victim_spawned")=="1"]
    out["att_by"]={p:r["att"].get(f"{pred}>{p}",0) for p in preys}
    out["hid"],out["samp"]=r["hid"],r["samp"]
    return out
if __name__=='__main__':
    recs=[]
    for blk,path in [("CAL","CAL-20260930-142550/CAL.tsv"),("CALa1","CAL-20260930-135309/CAL.tsv"),("PK","ECO3-20260930-133945/PK.tsv")]:
        for (cell,rep),r in parse(E+path,blk).items():
            m=re.match(r"([a-z]+)(\d+)_(.+)",cell); pred,prey=m.group(1).upper(),m.group(3)
            x=rec(r,pred,[prey]); x["arm"]=None; recs.append(x)
    for blk,path in [("STL","STL-20260930-155456/STL.tsv"),("STL2","STL2-20260930-164417/STL2.tsv")]:
        for (cell,rep),r in parse(E+path,blk).items():
            p=cell.split("_"); pred=p[0].upper(); prey="_".join(p[1:-1]); arm=p[-1]
            x=rec(r,pred,[prey]); x["arm"]=arm; recs.append(x)
    LP=["RABBIT","HARE","GROUNDHOG","GOAT_MOUNTAIN","KANGAROO","DEER","ELK","WATER_BUFFALO"]
    for blk,path in [("LONE","LONE-20260930-184842/LONE.tsv"),("LONE10","LONE10-20260930-212000/LONE.tsv")]:
        for (cell,rep),r in parse(E+path,blk).items():
            x=rec(r,"COUGAR",LP); x["arm"]=cell.split("_")[-1]; recs.append(x)
    for x in recs: x["kills_by"]=dict(x["kills_by"])
    json.dump(recs,open(sys.argv[1] if len(sys.argv)>1 else "/dev/stdout","w"),indent=0)
