#!/usr/bin/env python3
"""Bestiary Atlas: every creature raw DF ships, read into one table, and a dashboard that charts any of it.

Reads the creature raws of the vanilla modules -- vanilla_creatures and vanilla_creatures_extinct (the
Cambrian to the Cenozoic) -- resolving what DF resolves at load: COPY_TAGS_FROM (a creature built on another),
APPLY_CREATURE_VARIATION and inline CV_* tags with APPLY_CURRENT_CREATURE_VARIATION (giants, animal people,
gaits), CV_CONVERT_TAG, CHANGE_BODY_SIZE_PERC and CHANGE_FREQUENCY_PERC. From the resolved tags it derives, per
creature: body size, group (cluster) size, population numbers, frequency, clutch size, lifespan, speeds, the
biome list expanded from DF's ANY_* groups into biome families and climates, and the seasonal-wildlife model's
readings -- habitat, role, size band, special class -- by the same rules the tool uses.

Optional columns from the alpha trial fort (Boatsbowed), when the DwarfCron data is present: its regional stock
per species (the X1 run's population dump), the tool's season roster there, and the arrivals X1 saw.

    build_bestiary.py [--df DF_DIR] [--mods] [--out OUT.html] [--json OUT.json]

--mods also reads the Steam workshop mods' creature raws (source = mod:<id>). Writes a self-contained HTML page
with the data embedded; the page draws with Plotly from cdnjs.
"""
import argparse, json, re
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DF_DEFAULT = Path.home() / "Library/Application Support/CrossOver/Bottles/Win10/drive_c/Program Files (x86)/Steam/steamapps/common/Dwarf Fortress"

# ------------------------------------------------------------------------------------------ biomes ---
CONCRETE = ["MOUNTAIN", "GLACIER", "TUNDRA",
            "SWAMP_TEMPERATE_FRESHWATER", "SWAMP_TEMPERATE_SALTWATER", "MARSH_TEMPERATE_FRESHWATER", "MARSH_TEMPERATE_SALTWATER",
            "SWAMP_TROPICAL_FRESHWATER", "SWAMP_TROPICAL_SALTWATER", "SWAMP_MANGROVE", "MARSH_TROPICAL_FRESHWATER", "MARSH_TROPICAL_SALTWATER",
            "FOREST_TAIGA", "FOREST_TEMPERATE_CONIFER", "FOREST_TEMPERATE_BROADLEAF", "FOREST_TROPICAL_CONIFER", "FOREST_TROPICAL_DRY_BROADLEAF",
            "FOREST_TROPICAL_MOIST_BROADLEAF", "GRASSLAND_TEMPERATE", "SAVANNA_TEMPERATE", "SHRUBLAND_TEMPERATE", "GRASSLAND_TROPICAL",
            "SAVANNA_TROPICAL", "SHRUBLAND_TROPICAL", "DESERT_BADLAND", "DESERT_ROCK", "DESERT_SAND",
            "OCEAN_TROPICAL", "OCEAN_TEMPERATE", "OCEAN_ARCTIC"] + \
           [f"{b}_{c}_{s}" for b in ("POOL", "LAKE", "RIVER") for c in ("TEMPERATE", "TROPICAL") for s in ("FRESHWATER", "BRACKISHWATER", "SALTWATER")] + \
           ["SUBTERRANEAN_WATER", "SUBTERRANEAN_CHASM", "SUBTERRANEAN_LAVA"]

def family(b):
    for pre, fam in (("FOREST", "forest"), ("GRASSLAND", "grassland"), ("SAVANNA", "savanna"), ("SHRUBLAND", "shrubland"),
                     ("SWAMP", "wetland"), ("MARSH", "wetland"), ("DESERT", "desert"), ("OCEAN", "ocean"), ("LAKE", "lake"),
                     ("RIVER", "river"), ("POOL", "pool"), ("SUBTERRANEAN", "underground")):
        if b.startswith(pre):
            return fam
    return {"MOUNTAIN": "mountain", "GLACIER": "glacier", "TUNDRA": "tundra"}[b]

def climate(b):
    if b.startswith("SUBTERRANEAN"): return "underground"
    if b in ("GLACIER", "TUNDRA", "OCEAN_ARCTIC", "FOREST_TAIGA", "MOUNTAIN"): return "cold"
    if "TROPICAL" in b or b == "SWAMP_MANGROVE": return "tropical"
    if b.startswith("DESERT"): return "arid"
    return "temperate"

WATER_FAMS = {"ocean", "lake", "river", "pool"}
SURFACE = [b for b in CONCRETE if not b.startswith("SUBTERRANEAN")]
LAND = [b for b in SURFACE if family(b) not in WATER_FAMS]

def expand(tok):
    if tok in CONCRETE: return [tok]
    if tok == "TAIGA": return ["FOREST_TAIGA"]
    if tok == "ALL_MAIN": return SURFACE
    if tok == "ANY_LAND": return LAND
    if tok == "NOT_FREEZING": return [b for b in SURFACE if b not in ("GLACIER", "TUNDRA", "OCEAN_ARCTIC")]
    if tok == "ANY_WETLAND": return [b for b in CONCRETE if family(b) == "wetland"]
    m = re.match(r"ANY_(TEMPERATE|TROPICAL)(?:_(\w+))?$", tok)
    if m:
        clim, rest = m.group(1), m.group(2)
        pool = [b for b in SURFACE if clim in b or (clim == "TROPICAL" and b == "SWAMP_MANGROVE")]
        if not rest: return pool
        fam = {"WETLAND": "wetland", "MARSH": "MARSH", "SWAMP": "SWAMP", "FOREST": "forest", "LAKE": "lake", "RIVER": "river", "POOL": "pool"}.get(rest, rest.lower())
        return [b for b in pool if (b.startswith(fam) if fam.isupper() else family(b) == fam)]
    m = re.match(r"ANY_(\w+)$", tok)
    if m:
        fam = m.group(1).lower()
        return [b for b in CONCRETE if family(b) == fam]
    return []

# ------------------------------------------------------------------------------------------ parsing ---
TAG = re.compile(r"\[([^\[\]]+)\]")

def read_objects(paths):
    """creature blocks {id: [tag tuples]} and variations {id: [tag tuples]}, in file order, with the source."""
    creatures, variations, source = OrderedDict(), {}, {}
    for path, src in paths:
        txt = path.read_text(encoding="latin-1", errors="replace")
        cur, kind = None, None
        for m in TAG.finditer(txt):
            parts = m.group(1).split(":")
            t = parts[0]
            if t == "CREATURE":
                cur, kind = parts[1], "c"; creatures[cur] = []; source[cur] = (src, path.name); continue
            if t == "CREATURE_VARIATION":
                cur, kind = parts[1], "v"; variations[cur] = []; continue
            if t == "OBJECT":
                continue
            if cur is None:
                continue
            (creatures if kind == "c" else variations)[cur].append(tuple(parts))
    return creatures, variations, source

def apply_variation(tags, vtags, args=()):
    """Apply a creature variation's CV_* tags (with !ARGn substitution) to a resolved tag list."""
    def sub(p):
        return tuple(re.sub(r"!ARG(\d+)", lambda m: args[int(m.group(1)) - 1] if int(m.group(1)) - 1 < len(args) else "", x) for x in p)
    out = list(tags)
    i = 0
    vt = [sub(v) for v in vtags]
    while i < len(vt):
        v = vt[i]
        if v[0] == "CV_REMOVE_TAG":
            want = v[1:]
            out = [t for t in out if not (t[0] == want[0] and tuple(t[1:1 + len(want) - 1]) == tuple(want[1:]))]
        elif v[0] in ("CV_NEW_TAG", "CV_ADD_TAG"):
            out.append(tuple(v[1:]))
        elif v[0] == "CV_CONVERT_TAG":
            master = target = repl = None
            j = i + 1
            while j < len(vt) and vt[j][0].startswith("CVCT_"):
                if vt[j][0] == "CVCT_MASTER": master = vt[j][1]
                elif vt[j][0] == "CVCT_TARGET": target = ":".join(vt[j][1:])
                elif vt[j][0] == "CVCT_REPLACEMENT": repl = ":".join(vt[j][1:])
                j += 1
            if master:
                conv = []
                for t in out:
                    if t[0] == master and target is not None:
                        s = ":".join(t[1:])
                        if target in s:
                            s = s.replace(target, repl or "")
                            t = (t[0],) + tuple(s.split(":")) if s else (t[0],)
                    conv.append(t)
                out = conv
            i = j - 1
        i += 1
    return out

def resolve(cid, creatures, variations, cache, depth=0):
    if cid in cache: return cache[cid]
    raw = creatures.get(cid, [])
    tags, current = [], []
    for t in raw:
        if t[0] == "COPY_TAGS_FROM" and depth < 8:
            tags = list(resolve(t[1], creatures, variations, cache, depth + 1))
        elif t[0] == "APPLY_CREATURE_VARIATION":
            tags = apply_variation(tags, variations.get(t[1], []), t[2:])
            current = list(variations.get(t[1], []))
        elif t[0].startswith("CV_") or t[0].startswith("CVCT_"):
            current.append(t)
        elif t[0] == "APPLY_CURRENT_CREATURE_VARIATION":
            tags = apply_variation(tags, current, ()); current = []
        elif t[0] in ("GO_TO_END", "GO_TO_START", "GO_TO_TAG"):
            pass
        else:
            tags.append(t)
    cache[cid] = tags
    return tags

# ------------------------------------------------------------------------------------------ fields ---
def num(t, i, default=None):
    try: return int(t[i])
    except (IndexError, ValueError): return default

SPECIAL = {"MEGABEAST": "megabeast", "SEMIMEGABEAST": "semi-megabeast", "TITAN": "titan", "NIGHT_CREATURE_HUNTER": "night creature",
           "NIGHT_CREATURE_BOGEYMAN": "night creature", "NIGHT_CREATURE_NIGHTMARE": "night creature", "NIGHT_CREATURE_EXPERIMENTER": "night creature",
           "DEMON": "demon", "UNIQUE_DEMON": "demon", "FEATURE_BEAST": "forgotten beast", "NOT_LIVING": "unliving",
           "FANCIFUL": "mythic", "EVIL": "mythic", "GOOD": "mythic"}
DIET = ("CARNIVORE", "BONECARN", "LARGE_PREDATOR", "AMBUSHPREDATOR")
CURATED_ROLE = {"ORCA": "predator", "GIANT_ORCA": "predator", "GIANT_CUTTLEFISH": "predator", "SHARK_WHALE": "prey"}
FLAG_FIELDS = ["LAYS_EGGS", "FLIER", "AMPHIBIOUS", "AQUATIC", "IMMOBILE_LAND", "UNDERSWIM", "SWIMS_INNATE", "CARNIVORE", "BONECARN",
               "LARGE_PREDATOR", "AMBUSHPREDATOR", "GRAZER", "BENIGN", "SAVAGE", "NOCTURNAL", "CREPUSCULAR", "DIURNAL", "LARGE_ROAMING",
               "PET", "PET_EXOTIC", "TRAINABLE", "MOUNT", "COMMON_DOMESTIC", "INTELLIGENT", "UBIQUITOUS", "NO_WINTER", "NO_SUMMER",
               "NO_SPRING", "NO_AUTUMN", "HUNTS_VERMIN", "DIVE_HUNTS_VERMIN", "VERMIN_GROUNDER", "VERMIN_FISH", "VERMIN_SOIL",
               "VERMIN_SOIL_COLONY", "VERMIN_ROTTER", "VERMIN_EATER", "VERMIN_MICRO", "EQUIPMENT_WAGON", "DOES_NOT_EXIST"]

def kph(v):
    return round(8800 / v, 1) if v and v > 0 else None

def derive(cid, tags, src):
    names = {t[0] for t in tags}
    d = OrderedDict(id=cid)
    nm = next((t for t in tags if t[0] == "NAME"), None)
    d["name"] = nm[1] if nm and len(nm) > 1 else cid.lower().replace("_", " ")
    tile = next((t for t in tags if t[0] == "CREATURE_TILE"), None)
    tv = tile[1] if tile and len(tile) > 1 else ""
    d["tile"] = tv.strip("'") if tv.startswith("'") else (chr(int(tv)) if tv.isdigit() and 32 <= int(tv) < 127 else "")
    d["source"] = src[0]
    d["file"] = src[1]
    classes = sorted({t[1] for t in tags if t[0] == "CREATURE_CLASS" and len(t) > 1})
    d["period"] = next((c.title() for c in classes if c in ("CAMBRIAN", "ORDOVICIAN", "SILURIAN", "DEVONIAN", "CARBONIFEROUS", "PERMIAN",
                                                            "TRIASSIC", "JURASSIC", "CRETACEOUS", "CENOZOIC")), "Holocene" if src[0] == "vanilla" else "")
    d["animal_person"] = cid.endswith("_MAN") or " MAN" in cid
    d["giant"] = cid.startswith("GIANT_")
    # body size: the largest final BODY_SIZE of any caste, then every CHANGE_BODY_SIZE_PERC
    sizes = [num(t, 3, 0) for t in tags if t[0] == "BODY_SIZE"]
    size = max(sizes) if sizes else 0
    for t in tags:
        if t[0] == "CHANGE_BODY_SIZE_PERC" and num(t, 1):
            size = size * num(t, 1) // 100
    d["adult_size"] = size
    d["band"] = "large" if size >= 1_000_000 else ("medium" if size >= 150_000 else "small")
    cl = next((t for t in tags if t[0] == "CLUSTER_NUMBER"), None)
    d["cluster_min"], d["cluster_max"] = (num(cl, 1), num(cl, 2)) if cl else (None, None)
    pn = next((t for t in tags if t[0] == "POPULATION_NUMBER"), None)
    d["pop_min"], d["pop_max"] = (num(pn, 1), num(pn, 2)) if pn else (None, None)
    fr = [num(t, 1) for t in tags if t[0] == "FREQUENCY" and num(t, 1) is not None]
    freq = fr[-1] if fr else 50
    for t in tags:
        if t[0] == "CHANGE_FREQUENCY_PERC" and num(t, 1):
            freq = freq * num(t, 1) // 100
    d["frequency"] = freq
    cz = next((t for t in tags if t[0] == "CLUTCH_SIZE"), None)
    d["clutch_min"], d["clutch_max"] = (num(cz, 1), num(cz, 2)) if cz else (None, None)
    ma = next((t for t in tags if t[0] == "MAXAGE"), None)
    d["maxage_min"], d["maxage_max"] = (num(ma, 1), num(ma, 2)) if ma else (None, None)
    ch = next((t for t in tags if t[0] == "CHILD"), None)
    d["child_age"] = num(ch, 1) if ch else None
    pv = next((t for t in tags if t[0] == "PETVALUE"), None)
    d["pet_value"] = num(pv, 1) if pv else None
    diff = next((t for t in tags if t[0] == "DIFFICULTY"), None)
    d["difficulty"] = num(diff, 1) if diff else None
    # speeds: the gait variations' sprint argument (ARG4), or GAIT tags' full speed; kph ~ 8800 / value
    sp: dict = {"walk": None, "swim": None, "fly": None, "climb": None}
    for t in tags:
        if t[0] == "GAIT" and len(t) > 3:
            kind = {"WALK": "walk", "SWIM": "swim", "FLY": "fly", "CLIMB": "climb"}.get(t[1])
            v = num(t, 3)
            if kind and v and (sp[kind] is None or v < sp[kind]): sp[kind] = v
    for k in sp: d[f"{k}_kph"] = kph(sp[k])
    # biomes
    concrete = set()
    for t in tags:
        if t[0] == "BIOME" and len(t) > 1: concrete.update(expand(t[1]))
    d["biomes"] = sorted(concrete)
    d["n_biomes"] = len(concrete)
    d["biome_families"] = sorted({family(b) for b in concrete})
    d["climates"] = sorted({climate(b) for b in concrete})
    cold = sum(1 for b in concrete if climate(b) == "cold"); hot = sum(1 for b in concrete if climate(b) in ("tropical", "arid"))
    mild = sum(1 for b in concrete if climate(b) == "temperate")
    d["climate_lean"] = round((hot - cold) / (hot + cold + mild), 3) if (hot + cold + mild) else None
    for f in FLAG_FIELDS:
        d[f.lower()] = f in names
    d["vermin"] = any(f in names for f in ("VERMIN_GROUNDER", "VERMIN_ROTTER", "VERMIN_SOIL", "VERMIN_FISH", "VERMIN_EATER", "SMALL_RACE"))
    # the tool's model (v6.4): habitat, role, special class
    water = any(family(b) in WATER_FAMS or b == "SUBTERRANEAN_WATER" for b in concrete)
    land = any(not (family(b) in WATER_FAMS or b == "SUBTERRANEAN_WATER") for b in concrete)
    if "IMMOBILE_LAND" in names or "AQUATIC" in names: hab = "aquatic"
    elif "FLIER" in names: hab = "waterbird" if water else "flier"
    elif "AMPHIBIOUS" in names: hab = "semiaquatic"
    elif water and not land: hab = "semiaquatic"
    else: hab = "land"
    d["habitat"] = hab
    role = CURATED_ROLE.get(cid) or ("predator" if any(f in names for f in DIET) else "prey")
    d["role"] = role
    d["category"] = "vermin" if d["vermin"] else role
    spec = next((SPECIAL[f] for f in SPECIAL if f in names), None)
    if "DOES_NOT_EXIST" in names or "EQUIPMENT_WAGON" in names: spec = "not a creature"
    d["special"] = spec or ""
    d["class"] = "natural" if not spec and concrete and size > 0 else ("special" if spec else "unclassified")
    d["tags"] = sorted(names)
    return d

# ----------------------------------------------------------------------------------- trial fort ---
def trial_fort(_rows):
    """Boatsbowed columns from the DwarfCron X1 runs: stock per species key, the tool's roster, X1 arrivals."""
    runs = sorted((ROOT / "data/experiments/X1").glob("*/")) if (ROOT / "data/experiments/X1").exists() else []
    if not runs: return {}
    run = runs[-1]
    out = {}
    pa = run / "pops_all.tsv"
    if pa.exists():
        head = None
        for line in pa.read_text().splitlines():
            f = line.split("\t")
            if head is None: head = {h: i for i, h in enumerate(f)}; continue
            if f[head["phase"]] != "start" or f[head["rep"]] != "1": continue
            ref = f[head["ref6"]].split(",")
            layer = "cavern" if ref[3] != "-1" else ("water" if ref[2] != "-1" else "land")
            sp = f[head["species"]]
            o = out.setdefault(sp, {"boats_stock": 0, "boats_layers": set()})
            try: o["boats_stock"] += int(f[head["quantity"]])
            except ValueError: pass
            o["boats_layers"].add(layer)
    ev = run / "events.tsv"
    if ev.exists():
        for line in ev.read_text().splitlines()[1:]:
            f = line.split("\t")
            if len(f) < 8: continue
            if f[5] == "manipulation" and "x1 roster" in "\t".join(f[6:]) and f[2] == "1":
                m = re.search(r"x1 roster \d+: (.*)", "\t".join(f[6:]))
                for item in (m.group(1).split() if m else []):
                    if "=" in item and "/" in item:
                        k, v = item.split("=", 1); allow, seasons = v.split("/", 1)
                        tok = k.split(":")[-1]
                        o = out.setdefault(tok, {"boats_stock": 0, "boats_layers": set()})
                        o["boats_active"] = allow == "true"
                        o["boats_seasons"] = "".join(sorted(set(o.get("boats_seasons", "") + seasons)))
            elif f[5] == "arrival":
                tok = f[7].split(" ")[0]
                o = out.setdefault(tok, {"boats_stock": 0, "boats_layers": set()})
                o["x1_arrivals"] = o.get("x1_arrivals", 0) + 1
    for o in out.values():
        o["boats_layers"] = sorted(o["boats_layers"])
    return out

# ------------------------------------------------------------------------------------------ main ---
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--df", default=str(DF_DEFAULT))
    ap.add_argument("--mods", action="store_true")
    ap.add_argument("--out", default=str(ROOT / ".claude/scratch/bestiary-atlas.html"))
    ap.add_argument("--json", default=str(ROOT / "data/bestiary/creatures.json"))
    a = ap.parse_args()
    df = Path(a.df)
    van = df / "data/vanilla"
    paths = [(p, "vanilla") for p in sorted((van / "vanilla_creatures/objects").glob("*.txt"))]
    paths += [(p, "extinct") for p in sorted((van / "vanilla_creatures_extinct/objects").glob("*.txt"))]
    if a.mods:
        ws = df.parent.parent / "workshop/content/975370"
        for p in sorted(ws.glob("*/objects/*.txt")):
            paths.append((p, "mod:" + p.parent.parent.name))
    creatures, variations, source = read_objects(paths)
    cache, rows = {}, []
    for cid in creatures:
        tags = resolve(cid, creatures, variations, cache)
        rows.append(derive(cid, tags, source[cid]))
    fort = trial_fort(rows)
    for r in rows:
        f = fort.get(r["id"], {})
        r["boats_stock"] = f.get("boats_stock")
        r["boats_layers"] = f.get("boats_layers", [])
        r["boats_active"] = f.get("boats_active")
        r["boats_seasons"] = f.get("boats_seasons", "")
        r["x1_arrivals"] = f.get("x1_arrivals", 0) if f else None
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(rows))
    tpl = (Path(__file__).parent / "atlas.html").read_text()
    slim = [{k: v for k, v in r.items() if k not in ("tags", "biomes")} for r in rows]   # the page needs the families, not every tag
    Path(a.out).write_text(tpl.replace("/*__DATA__*/[]", json.dumps(slim, separators=(",", ":"))))
    by = {}
    for r in rows: by[r["source"]] = by.get(r["source"], 0) + 1
    print(f"{len(rows)} creatures ({by}); natural {sum(r['class'] == 'natural' for r in rows)}; with trial-fort columns {sum(r['boats_stock'] is not None for r in rows)}")
    print(f"wrote {a.json} and {a.out}")

if __name__ == "__main__":
    main()
