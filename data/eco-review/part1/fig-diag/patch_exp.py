"""Apply the figure-data fixes to experiments.json (scratch copy). Idempotent."""
import json, sys
from pathlib import Path
P = Path(sys.argv[1] if len(sys.argv) > 1 else "data/eco-report/experiments.json")
TOK = Path("/Users/nathanielcannon/Claude/Projects/DwarfCron/data/eco-desk/v2/tokens")
d = json.loads(P.read_text())
F = {f["id"]: f for f in d["figures"]}
# (a) eight specs written value-first: the renderer wants x = category, y = value
for fid in ["hc4-species-or-spot", "leader-spread", "coh-flock-school-pod", "builder-predator-share-desk",
            "size-gate-model", "rels-who-writes", "vrm2-gobble-tokens", "sw2-elephant-choice"]:
    f = F[fid]
    if all(isinstance(r.get(f["x"]), (int, float)) for r in f["rows"]):
        f["x"], f["y"] = f["y"], f["x"]
# (b) N1: the kangaroo reference is a tick (x), not a wave count (y)
f = F["n1-exhaustion-replacement"]
f["reference"] = [{"value": 2400, "axis": "x", "label": "kangaroo wave of 3 (entry 3 -> 0)"}]
f["yLabel"] = "waves so far"; f["xLabel"] = "ticks"; f["unit"] = None; f["curve"] = "step-after"
f["notes"] = f["notes"].replace(" reference is on the x axis.", "")
# (c) builder: one aim band, not two lines both labelled 'land'
f = F["builder-predator-share-desk"]
f["reference"] = [{"value": 0.14, "label": "land aim 14-18%"}, {"value": 0.18, "label": ""}]
f["yLabel"] = "predator share of arrivals"; f["unit"] = None
# (d) RELS: the bar label must carry the target class too (the chart showed writers only)
f = F["rels-who-writes"]
SHORT = {"Dwarves": "Dwarves → new arrival", "Livestock and pets": "Livestock, pets → new arrival",
         "Placed animals (not flagged wild)": "Placed animals → new arrival", "Cavern wildlife": "Cavern → cavern wildlife",
         "Surface wildlife": "Surface → surface wildlife", "Cavern and surface wildlife": "Cavern ↔ surface wildlife"}
for r in f["rows"]:
    r["entry"] = SHORT[r["writer"]]
f["x"] = "entry"; f["highlight"] = "Placed animals → new arrival"
# (e) token heatmap: full width, block outlines from the 0.5 cut, caption that explains the grouping and order
f = F["token-cooccurrence"]
order = json.loads((TOK / "cluster-order.json").read_text())["wild"]["order"]
cuts = json.loads((TOK / "cluster-cuts.json").read_text())["wild"]["0.5"]
names = {"CANNOT_JUMP": "aquatic core", "SMALL_REMAINS": "vermin body", "FISHITEM": "vermin fish", "PETVALUE": "backbone (prevalence)",
         "LOW_LIGHT_VISION": "cavern", "ODOR_LEVEL": "cavern senses", "STANDARD_GRAZER": "grazers", "GOBBLE_VERMIN_CLASS": "ground foragers",
         "WEBBER": "spiders", "CURIOUSBEAST_ITEM": "thieves", "PACK_ANIMAL": "beasts of burden", "GNAWER": "rat-like vermin"}
blocks = []
for c in cuts:
    idx = sorted(order.index(t) for t in c["tokens"])
    first = order[idx[0]]
    blocks.append({"from": first, "to": order[idx[-1]], "i": idx[0],
                   "label": f'{names.get(first, first)}: {", ".join(order[i] for i in idx)} (all {c["n_all"]} / any {c["n_any"]} species, mean J {c["mean_pair_jaccard"]})'})
blocks.sort(key=lambda b: b["i"])
for k, b in enumerate(blocks):
    b["tag"] = str(k + 1); b["label"] = f'{k+1} {b["label"]}'; del b["i"]
f["blocks"] = blocks
f["layout"] = "full"; f["cellText"] = False
f["xOrder"] = f["yOrder"] = order
f["subtitle"] = ("Jaccard overlap of the 75 tokens carried by 3+ of the 363 wildlife species: species with both / species with either. "
                 "Same tokens, same order on both axes; blank = under 0.05; outlined = the 12 blocks that hold at mean J >= 0.5")
key = "; ".join(f'{b["tag"]} {b["label"].split(":")[0][len(b["tag"])+1:]}' for b in blocks)
f["caption"] = (
    "How to read it. The order is the leaf order of an average-linkage tree on 1 - Jaccard, so tokens that ride on the same species sit side by side "
    "and a dark square on the diagonal is a block of tokens that travel together. The numbered outlines are the blocks that survive a cut at 0.5: "
    + key + ". Only adjacency carries meaning, and loosely: tokens side by side share a branch of the tree; a block's place along the diagonal is not a rank, and the tree could be flipped at any branch without changing it. "
    "Dark rows outside any block are prevalence, not meaning: the backbone (BIOME and POPULATION_NUMBER on 363 of 363, GAIT 360, NATURAL 331) "
    "overlaps everything common. From the top left the order runs: rare tokens and the vermin set, thieves, domestic and burden tokens, grazers, the aquatic core, "
    "the vermin body and fish, the backbone, fliers, activity and diet, the two cavern blocks, and LARGE_PREDATOR last, because no token "
    "travels with it (best partner UNDERGROUND_DEPTH, J 0.26; it never co-occurs with BENIGN). What it means for the tool: writing one token of a block "
    "without its partners builds a combination no vanilla species carries (AQUATIC without IMMOBILE_LAND and NO_DRINK, for example), while LARGE_PREDATOR "
    "can be written alone without breaking a pattern. Desk survey of the 53.16 raws (eco/T0-triage.tsv; data/eco-desk/v2/tokens/clusters.md, cluster-order.json, cluster-cuts.json).")
f["valueLabel"] = "Jaccard overlap"; f["unit"] = None
f["notes"] = "Not a rig experiment. Hover a cell for the pair and the number of species carrying the row token; hover an outline for the block's members and counts."
P.write_text(json.dumps(d, indent=1, ensure_ascii=False))
print("patched", P)
