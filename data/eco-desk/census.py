#!/usr/bin/env python3
"""Census of creature tokens in DF 53.16 vanilla raws (files only).

Resolution follows build_bestiary.py (COPY_TAGS_FROM, APPLY_CREATURE_VARIATION, inline CV_* +
APPLY_CURRENT_CREATURE_VARIATION, CV_CONVERT_TAG) and adds: GO_TO_START / GO_TO_END / GO_TO_TAG insertion
cursor, and a caste walk (CASTE / SELECT_CASTE / SELECT_ADDITIONAL_CASTE) over the resolved tag list.
"""
import json, re, sys, os, itertools
from collections import OrderedDict, Counter, defaultdict
from pathlib import Path

DF = Path(os.environ.get("DF_DIR", str(Path.home() / "Library/Application Support/CrossOver/Bottles/Win10/drive_c/Program Files (x86)/Steam/steamapps/common/Dwarf Fortress")))
VAN = DF / "data/vanilla"
OUT = Path(__file__).resolve().parent
TAG = re.compile(r"\[([^\[\]]+)\]")

INTEREST = """ALL_ACTIVE AMBUSHPREDATOR AMPHIBIOUS AQUATIC ARTIFICIAL_HIVEABLE AT_PEACE_WITH_WILDLIFE BEACH_FREQUENCY BENIGN
BLOODSUCKER BONECARN CAN_LEARN CAN_SPEAK CANNOT_CLIMB CANNOT_JUMP CARNIVORE CAVE_ADAPT CLUSTER_NUMBER COMMON_DOMESTIC CRAZED
CREPUSCULAR CURIOUSBEAST_EATER CURIOUSBEAST_GUZZLER CURIOUSBEAST_ITEM DIE_WHEN_VERMIN_BITE DIURNAL DIVE_HUNTS_VERMIN EXTRAVISION
FISHITEM FLEEQUICK FLIER GAIT GNAWER GOBBLE_VERMIN_CLASS GOBBLE_VERMIN_CREATURE GOOD EVIL GRASSTRAMPLE GRAZER HUNTS_VERMIN IMMOBILE
IMMOBILE_LAND LARGE_PREDATOR LARGE_ROAMING LAYS_EGGS LAYS_UNUSUAL_EGGS LOOSE_CLUSTERS LOW_LIGHT_VISION MATUTINAL MEANDERER
MISCHIEVIOUS MISCHIEVOUS MOUNT MOUNT_EXOTIC MULTIPART_FULL_VISION MUNDANE NATURAL NATURAL_ANIMAL NO_AUTUMN NO_DRINK NO_SPRING
NO_SUMMER NO_WINTER NOBREATHE NOCTURNAL NOMEAT ODOR_LEVEL OPPOSED_TO_LIFE PACK_ANIMAL PET PET_EXOTIC PETVALUE POPULATION_NUMBER
PRONE_TO_RAGE RETURNS_VERMIN_KILLS_TO_OWNER ROOT_AROUND SAVAGE SENSE_CREATURE_CLASS SMALL_REMAINS SMELL_TRIGGER SPECIFIC_FOOD
STANCE_CLIMBER STANDARD_GRAZER SWIMS_INNATE SWIMS_LEARNED THICKWEB TRAINABLE TRAINABLE_HUNTING TRAINABLE_WAR TRAPAVOID
TRIGGERABLE_GROUP UBIQUITOUS UNDERGROUND_DEPTH UNDERSWIM VERMIN_BITE VERMIN_EATER VERMIN_FISH VERMIN_GROUNDER VERMIN_HATEABLE
VERMIN_MICRO VERMIN_NOFISH VERMIN_NOROAM VERMIN_NOTRAP VERMIN_ROTTER VERMIN_SOIL VERMIN_SOIL_COLONY VERMINHUNTER VESPERTINE
VIEWRANGE VISION_ARC WAGON_PULLER WEBBER WEBIMMUNE FREQUENCY BIOME""".split()
# DF's creature-level (not caste) tokens among those of interest; everything else of interest is a caste token.
CREATURE_SCOPE = set("""ARTIFICIAL_HIVEABLE BIOME CLUSTER_NUMBER EVIL GOOD FREQUENCY LARGE_ROAMING LOOSE_CLUSTERS MUNDANE
POPULATION_NUMBER SAVAGE SMELL_TRIGGER TRIGGERABLE_GROUP UBIQUITOUS UNDERGROUND_DEPTH VERMIN_EATER VERMIN_FISH VERMIN_GROUNDER
VERMIN_ROTTER VERMIN_SOIL VERMIN_SOIL_COLONY CHANGE_FREQUENCY_PERC NAME DESCRIPTION FANCIFUL DOES_NOT_EXIST""".split())
VERMIN_TYPES = ["VERMIN_GROUNDER", "VERMIN_ROTTER", "VERMIN_SOIL", "VERMIN_SOIL_COLONY", "VERMIN_FISH", "VERMIN_EATER"]
PARAM = {"BEACH_FREQUENCY", "CLUSTER_NUMBER", "GAIT", "GOBBLE_VERMIN_CLASS", "GOBBLE_VERMIN_CREATURE", "GRASSTRAMPLE", "GRAZER",
         "ODOR_LEVEL", "PETVALUE", "POPULATION_NUMBER", "SENSE_CREATURE_CLASS", "SMELL_TRIGGER", "SPECIFIC_FOOD", "TRIGGERABLE_GROUP",
         "UNDERGROUND_DEPTH", "VIEWRANGE", "VISION_ARC", "FREQUENCY", "BIOME"}

# ------------------------------------------------------------------------------- reading ---
def read_objects(paths):
    creatures, variations, source, lines = OrderedDict(), {}, {}, {}
    for path, src in paths:
        txt = path.read_text(encoding="latin-1", errors="replace")
        cur, kind = None, None
        for m in TAG.finditer(txt):
            parts = tuple(m.group(1).split(":"))
            t = parts[0]
            if t == "CREATURE":
                cur, kind = parts[1], "c"; creatures[cur] = []; source[cur] = (src, path.name); continue
            if t == "CREATURE_VARIATION":
                cur, kind = parts[1], "v"; variations[cur] = []; continue
            if t == "OBJECT" or cur is None:
                continue
            (creatures if kind == "c" else variations)[cur].append(parts)
    return creatures, variations, source

class TagList:
    """A tag list with an insertion cursor (None = append at end)."""
    def __init__(self, tags=None):
        self.t = list(tags or []); self.pos = None
    def add(self, tag):
        if self.pos is None: self.t.append(tag)
        else: self.t.insert(self.pos, tag); self.pos += 1

def matches(t, want):
    return t[0] == want[0] and tuple(t[1:len(want)]) == tuple(want[1:])

def apply_variation(tl, vtags, args=()):
    def sub(p):
        return tuple(re.sub(r"!ARG(\d+)", lambda m: args[int(m.group(1)) - 1] if int(m.group(1)) - 1 < len(args) else "", x) for x in p)
    vt = [sub(v) for v in vtags]
    i = 0
    while i < len(vt):
        v = vt[i]
        if v[0] == "CV_REMOVE_TAG":
            want = v[1:]
            keep = []
            for k, t in enumerate(tl.t):
                if matches(t, want):
                    if tl.pos is not None and k < tl.pos: tl.pos -= 1
                else: keep.append(t)
            tl.t = keep
        elif v[0] in ("CV_NEW_TAG", "CV_ADD_TAG"):
            tl.add(tuple(v[1:]))
        elif v[0] == "CV_CONVERT_TAG":
            master = target = repl = None
            j = i + 1
            while j < len(vt) and vt[j][0].startswith("CVCT_"):
                if vt[j][0] == "CVCT_MASTER": master = vt[j][1]
                elif vt[j][0] == "CVCT_TARGET": target = ":".join(vt[j][1:])
                elif vt[j][0] == "CVCT_REPLACEMENT": repl = ":".join(vt[j][1:])
                j += 1
            if master and target is not None:
                for k, t in enumerate(tl.t):
                    if t[0] == master:
                        s = ":".join(t[1:])
                        if target in s:
                            s = s.replace(target, repl or "")
                            tl.t[k] = (t[0],) + tuple(s.split(":")) if s else (t[0],)
            i = j - 1
        i += 1

def resolve(cid, creatures, variations, cache, info, depth=0):
    if cid in cache: return cache[cid]
    tl = TagList(); current = []
    inf = info.setdefault(cid, {"copy_from": "", "variations": []})
    for t in creatures.get(cid, []):
        if t[0] == "COPY_TAGS_FROM" and depth < 8:
            tl = TagList(resolve(t[1], creatures, variations, cache, info, depth + 1)); inf["copy_from"] = t[1]
        elif t[0] == "APPLY_CREATURE_VARIATION":
            apply_variation(tl, variations.get(t[1], []), t[2:]); current = []
            if not t[1].startswith("STANDARD_") and not t[1].endswith("_ATTACK"): inf["variations"].append(t[1])
        elif t[0].startswith("CV_") or t[0].startswith("CVCT_"):
            current.append(t)
        elif t[0] == "APPLY_CURRENT_CREATURE_VARIATION":
            apply_variation(tl, current, ()); current = []
        elif t[0] == "GO_TO_START": tl.pos = 0
        elif t[0] == "GO_TO_END": tl.pos = None
        elif t[0] == "GO_TO_TAG":
            want = t[1:]
            idx = next((k for k, x in enumerate(tl.t) if matches(x, want)), None)
            tl.pos = None if idx is None else idx + 1
        else:
            tl.add(t)
    cache[cid] = tl.t
    return tl.t

# ------------------------------------------------------------------------------- caste walk ---
def caste_walk(tags):
    """-> (castes list, occurrences {token: [(selection or 'ALL', tagtuple, in_caste_block)]})"""
    castes, sel, occ = [], "ALL", defaultdict(list)
    in_block = False
    for t in tags:
        k = t[0]
        if k == "CASTE":
            if t[1] not in castes: castes.append(t[1])
            sel, in_block = {t[1]}, True; continue
        if k == "SELECT_CASTE":
            sel = "ALL" if t[1] == "ALL" else {t[1]}; in_block = t[1] != "ALL" or True; continue
        if k == "SELECT_ADDITIONAL_CASTE":
            if sel != "ALL": sel = set(sel) | {t[1]}
            continue
        occ[k].append((sel if sel == "ALL" else frozenset(sel), t, in_block))
    return castes or ["(single)"], occ

def castes_for(occs, castes):
    s = set()
    for sel, _, _ in occs:
        if sel == "ALL": return set(castes)
        s |= set(sel)
    return s & set(castes) if castes != ["(single)"] else set(castes)

def num(x, default=None):
    try: return int(x)
    except (ValueError, TypeError): return default

# ------------------------------------------------------------------------------- main ---
def main():
    paths = [(p, "vanilla") for p in sorted((VAN / "vanilla_creatures/objects").glob("*.txt"))]
    paths += [(p, "extinct") for p in sorted((VAN / "vanilla_creatures_extinct/objects").glob("*.txt"))]
    creatures, variations, source = read_objects(paths)
    cache, info, rows = {}, {}, []
    all_token_creatures = defaultdict(set)   # every token string -> creatures (for the extra-token scan)
    for cid in creatures:
        tags = resolve(cid, creatures, variations, cache, info)
        castes, occ = caste_walk(tags)
        names = set(occ)
        for k in names: all_token_creatures[k].add(cid)
        r = OrderedDict()
        r["id"] = cid
        nm = occ.get("NAME")
        r["name"] = nm[0][1][1] if nm and len(nm[0][1]) > 1 else cid.lower()
        r["source"] = source[cid][0]; r["file"] = source[cid][1]
        r["copy_from"] = info[cid]["copy_from"]; r["variations"] = ",".join(info[cid]["variations"])
        r["kind"] = ("animal_person" if "ANIMAL_PERSON" in info[cid]["variations"] or "ANIMAL_PERSON_LEGLESS" in info[cid]["variations"]
                     else "giant" if "GIANT" in info[cid]["variations"] else "")
        r["castes"] = ",".join(castes)
        r["is_vermin"] = int(any(v in names for v in VERMIN_TYPES))
        r["biomes"] = ",".join(dict.fromkeys(o[1][1] for o in occ.get("BIOME", []) if len(o[1]) > 1))
        fr = [num(o[1][1]) for o in occ.get("FREQUENCY", []) if len(o[1]) > 1]
        freq = fr[-1] if fr else None
        eff = freq if freq is not None else 50
        for o in occ.get("CHANGE_FREQUENCY_PERC", []):
            if num(o[1][1]): eff = eff * num(o[1][1]) // 100
        r["frequency"] = "" if freq is None else freq
        r["frequency_eff"] = eff if r["biomes"] else ""
        pn = occ.get("POPULATION_NUMBER"); r["population_number"] = ":".join(pn[-1][1][1:3]) if pn else ""
        cl = occ.get("CLUSTER_NUMBER"); r["cluster_number"] = ":".join(cl[-1][1][1:3]) if cl else ""
        # adult body size: last BODY_SIZE value, times every CHANGE_BODY_SIZE_PERC
        bs = [num(o[1][3], 0) for o in occ.get("BODY_SIZE", []) if len(o[1]) > 3]
        size = bs[-1] if bs else 0
        for o in occ.get("CHANGE_BODY_SIZE_PERC", []):
            if num(o[1][1]): size = size * num(o[1][1]) // 100
        r["adult_body_size"] = size
        r["creature_classes"] = ",".join(sorted({o[1][1] for o in occ.get("CREATURE_CLASS", []) if len(o[1]) > 1}))
        desc = occ.get("DESCRIPTION"); r["_desc"] = ":".join(desc[-1][1][1:]) if desc else ""
        r["_caste_detail"] = {}
        for tok in INTEREST:
            if tok in ("BIOME", "FREQUENCY", "POPULATION_NUMBER", "CLUSTER_NUMBER"):
                r[tok] = 1 if tok in names else 0
                if tok in names: r["_caste_detail"][tok] = ("creature", True, any(o[2] for o in occ[tok]))
                continue
            if tok not in names:
                r[tok] = 0; continue
            os_ = occ[tok]
            cs = castes_for(os_, castes)
            allc = cs >= set(castes)
            placed_in_caste = any(o[0] != "ALL" for o in os_)
            if tok in PARAM:
                if tok == "GAIT": vals = sorted({o[1][1] for o in os_ if len(o[1]) > 1})
                elif tok in ("TRIGGERABLE_GROUP", "UNDERGROUND_DEPTH", "SMELL_TRIGGER"): vals = sorted({":".join(o[1][1:]) for o in os_})
                else: vals = list(dict.fromkeys(":".join(o[1][1:]) for o in os_))
                v = "|".join(vals) if vals else "1"
            else:
                v = None
            if tok in CREATURE_SCOPE:
                r[tok] = v if v is not None else 1
            else:
                prefix = "all" if allc else "some:" + ",".join(c for c in castes if c in cs)
                r[tok] = (v if allc else prefix + "=" + v) if v is not None else prefix
            r["_caste_detail"][tok] = ("creature" if tok in CREATURE_SCOPE else "caste", allc, placed_in_caste)
        cb = [t for t in ("CURIOUSBEAST_EATER", "CURIOUSBEAST_GUZZLER", "CURIOUSBEAST_ITEM") if t in names]
        r["CURIOUSBEAST_ANY"] = ",".join(x.split("_")[1] for x in cb) if cb else 0
        r["_names"] = names
        r["_occ"] = occ
        rows.append(r)

    # ---------------- tokens-by-creature.tsv
    cols = ["id", "name", "source", "kind", "copy_from", "variations", "castes", "is_vermin", "biomes", "frequency", "frequency_eff",
            "population_number", "cluster_number", "adult_body_size", "creature_classes"] + INTEREST + ["CURIOUSBEAST_ANY"]
    with open(OUT / "tokens-by-creature.tsv", "w") as f:
        f.write("\t".join(cols) + "\n")
        for r in rows:
            f.write("\t".join(str(r[c]) for c in cols) + "\n")

    # ---------------- token-counts.tsv
    COMMON = """DOG CAT HORSE COW PIG SHEEP GOAT DONKEY CHICKEN DUCK GOOSE RABBIT DEER ELK MOOSE WOLF FOX BEAR_GRIZZLY BEAR_BLACK BEAR_POLAR
    BEAVER BADGER RACCOON SKUNK OTTER_RIVER OTTER_SEA BOBCAT COUGAR LYNX LION TIGER LEOPARD JAGUAR CHEETAH HYENA ELEPHANT HIPPO RHINOCEROS
    GIRAFFE ZEBRA GAZELLE CAMEL_1_HUMP CROCODILE_SALTWATER ALLIGATOR SHARK_GREAT_WHITE WHALE_BLUE DOLPHIN SEAL PENGUIN EAGLE HAWK OWL CROW
    MAGPIE SPARROW RAT MOUSE SQUIRREL HEDGEHOG MOLE BAT FLY MOSQUITO ANT BEETLE HONEY_BEE FROG TOAD SNAKE LIZARD TURTLE SALMON TROUT CARP
    COD TUNA KANGAROO KOALA WOMBAT TASMANIAN_DEVIL PLATYPUS WALRUS REINDEER MUSK_OX BISON BOAR BUFFALO WARTHOG MONKEY GORILLA CHIMPANZEE""".split()
    rank = {c: i for i, c in enumerate(COMMON)}
    def pick(ids, n=5):
        ids = sorted(ids, key=lambda c: (rank.get(c, 10_000), 1 if byid[c]["kind"] else 0, 1 if byid[c]["source"] == "extinct" else 0, c))
        return ids[:n]
    byid = {r["id"]: r for r in rows}
    wild = [r for r in rows if is_wild(r)]
    wild_ids = {r["id"] for r in wild}
    with open(OUT / "token-counts.tsv", "w") as f:
        f.write("token\tdf_scope\tn_creatures\tn_wildlife\tn_all_castes\tn_some_castes\tn_declared_in_caste_block\tn_vanilla\tn_extinct\tn_animal_person\tn_giant\tvalue_distribution\texamples\n")
        for tok in INTEREST + ["CURIOUSBEAST_ANY"]:
            have = [r for r in rows if r[tok] not in (0, "0")]
            if tok == "CURIOUSBEAST_ANY":
                scope, n_all, n_some, n_block = "caste", "", "", ""
            else:
                det = [r["_caste_detail"].get(tok) for r in have]
                scope = "creature" if tok in CREATURE_SCOPE else "caste"
                n_all = sum(1 for d in det if d and d[1]); n_some = sum(1 for d in det if d and not d[1]); n_block = sum(1 for d in det if d and d[2])
                if scope == "creature": n_all, n_some = "", ""
            dist = ""
            if tok in PARAM or tok == "CURIOUSBEAST_ANY":
                c = Counter()
                for r in have:
                    v = str(r[tok]).split("=", 1)[-1]
                    for x in (v.split("|") if tok in ("GAIT", "BIOME") else [v]): c[x] += 1
                if tok == "BIOME":
                    c = Counter(); [c.update(r["biomes"].split(",")) for r in have]
                dist = "; ".join(f"{k}:{n}" for k, n in c.most_common(25))
            f.write("\t".join(map(str, [tok, scope, len(have), sum(r["id"] in wild_ids for r in have), n_all, n_some, n_block,
                                        sum(r["source"] == "vanilla" for r in have), sum(r["source"] == "extinct" for r in have),
                                        sum(r["kind"] == "animal_person" for r in have), sum(r["kind"] == "giant" for r in have),
                                        dist, ",".join(pick([r["id"] for r in have]))])) + "\n")
        # CREATURE_CLASS values and BODY_SIZE distribution
        cc = Counter(); [cc.update(r["creature_classes"].split(",")) for r in rows if r["creature_classes"]]
        f.write("\t".join(["CREATURE_CLASS", "caste", str(sum(1 for r in rows if r["creature_classes"])), str(sum(1 for r in wild if r["creature_classes"])),
                           "", "", "", "", "", "", "", "; ".join(f"{k}:{n}" for k, n in cc.most_common()), ""]) + "\n")
        bands = [(0, "0/none"), (1, "1-99"), (100, "100-999"), (1000, "1k-9.9k"), (10000, "10k-99k"), (100000, "100k-999k"), (1000000, "1M-9.9M"), (10000000, ">=10M")]
        bc = Counter()
        for r in rows:
            s = r["adult_body_size"]; lab = [l for lo, l in bands if s >= lo][-1] if s else "0/none"; bc[lab] += 1
        f.write("\t".join(["BODY_SIZE(adult,last,x CHANGE_BODY_SIZE_PERC)", "caste", str(sum(1 for r in rows if r["adult_body_size"])), "", "", "", "", "", "", "", "",
                           "; ".join(f"{l}:{bc[l]}" for _, l in bands), ""]) + "\n")

    # ---------------- extra tokens (>=5 creatures, not in list)
    known = set(INTEREST) | {"CREATURE_CLASS", "BODY_SIZE", "CURIOUSBEAST"}
    with open(OUT / "extra-tokens.tsv", "w") as f:
        f.write("token\tn_creatures\tn_wildlife\texamples\n")
        for k, s in sorted(all_token_creatures.items(), key=lambda kv: -len(kv[1])):
            if k in known or len(s) < 5: continue
            f.write(f"{k}\t{len(s)}\t{len(s & wild_ids)}\t{','.join(pick(list(s)))}\n")

    # ---------------- dump json for later analysis
    slim = [{k: v for k, v in r.items() if k not in ("_occ", "_caste_detail")} | {"_names": sorted(r["_names"]), "_wild": r["id"] in wild_ids} for r in rows]
    (OUT / "census.json").write_text(json.dumps(slim))
    print(len(rows), "creatures;", len(wild), "wildlife")

def is_wild(r):
    """Natural surface/underground wildlife: has a BIOME, vanilla (not extinct), not animal person/giant, not a civ race."""
    n = r["_names"]
    return bool(r["biomes"]) and r["source"] == "vanilla" and not r["kind"] and "DOES_NOT_EXIST" not in n \
        and "EQUIPMENT_WAGON" not in n and not ("CAN_SPEAK" in n and "CAN_LEARN" in n) and "MEGABEAST" not in n \
        and "SEMIMEGABEAST" not in n and "FEATURE_BEAST" not in n and "TITAN" not in n and not any(x.startswith("NIGHT_CREATURE") for x in n) \
        and "DEMON" not in n and "UNIQUE_DEMON" not in n

if __name__ == "__main__":
    main()
