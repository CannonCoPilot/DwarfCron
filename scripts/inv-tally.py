"""INV tally: an invasive SAVAGE species (YETI, replacing the disproven CENOZOIC_SMILODON token -- see report) added
via addNewSpecies, against this embark's own read Savage-Calm axis (not assumed), over one season sampled every
5,040 t with the shared _ALIVE reader (as LONE). Usage: inv-tally.py <run>"""
import sys, re, collections, pathlib
run = pathlib.Path(sys.argv[1])
alive = collections.defaultdict(list); savagery = collections.defaultdict(dict); invadd = {}
for t in sorted(run.glob("INV*.tsv")):
    for line in open(t):
        f = line.rstrip("\n").split("\t")
        if len(f) < 5: continue
        cell, rep, kind, rest = f[1], f[2], f[3], f[4]
        k = (cell, rep)
        if kind == "alive":
            counts = dict(x.split("=", 1) for x in rest.split() if "=" in x)
            alive[k].append(counts)
        else:
            kv = dict(re.findall(r"(\w+)=(\S+)", rest))
            if kind == "savagery": savagery[k][kv.get("tag")] = kv
            elif kind == "invadd": invadd[k] = kv
print("cell rep: savagery pre/post | invadd result | YETI count over 20 samples (5,040 t each)")
for k in sorted(alive, key=lambda k: (k[0], k[1])):
    pre, post = savagery[k].get("pre", {}), savagery[k].get("post", {})
    ia = invadd.get(k, {})
    yeti_series = [int(c.get("YETI", 0)) for c in alive[k]]
    print(f"== {k[0]:8s} r{k[1]}: savagery pre tiles={pre.get('tiles')} savage={pre.get('savage_tiles')} calm={pre.get('calm_tiles')}"
          f"  post savage={post.get('savage_tiles')} calm={post.get('calm_tiles')}")
    print(f"   invadd: added={ia.get('added')} reason={ia.get('reason')}")
    print(f"   YETI alive series: {yeti_series}  (max {max(yeti_series) if yeti_series else 0}, end {yeti_series[-1] if yeti_series else 0})")
