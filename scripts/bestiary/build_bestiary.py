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

# DF's biome groups, in biome_type order -- the same table as the ECO desk's census (data/eco-desk/v2/guilds/species2.py
# SETS). rev 2 (1 Oct 2026): until then this page built the groups from their names, which put every lake, river, pool
# and ocean into NOT_FREEZING, ANY_TEMPERATE and ANY_TROPICAL and pools and rivers into ALL_MAIN. The live tool reads
# the bat, the ant and the firefly (NOT_FREEZING) as fliers with no water body (fixtures/species-model.tsv, MODEL.audit);
# the old expansion made them waterbirds.
_B = ['MOUNTAIN', 'GLACIER', 'TUNDRA', 'SWAMP_TEMPERATE_FRESHWATER', 'SWAMP_TEMPERATE_SALTWATER', 'MARSH_TEMPERATE_FRESHWATER',
      'MARSH_TEMPERATE_SALTWATER', 'SWAMP_TROPICAL_FRESHWATER', 'SWAMP_TROPICAL_SALTWATER', 'SWAMP_MANGROVE', 'MARSH_TROPICAL_FRESHWATER',
      'MARSH_TROPICAL_SALTWATER', 'FOREST_TAIGA', 'FOREST_TEMPERATE_CONIFER', 'FOREST_TEMPERATE_BROADLEAF', 'FOREST_TROPICAL_CONIFER',
      'FOREST_TROPICAL_DRY_BROADLEAF', 'FOREST_TROPICAL_MOIST_BROADLEAF', 'GRASSLAND_TEMPERATE', 'SAVANNA_TEMPERATE', 'SHRUBLAND_TEMPERATE',
      'GRASSLAND_TROPICAL', 'SAVANNA_TROPICAL', 'SHRUBLAND_TROPICAL', 'DESERT_BADLAND', 'DESERT_ROCK', 'DESERT_SAND', 'OCEAN_TROPICAL',
      'OCEAN_TEMPERATE', 'OCEAN_ARCTIC', 'POOL_TEMPERATE_FRESHWATER', 'POOL_TEMPERATE_BRACKISHWATER', 'POOL_TEMPERATE_SALTWATER',
      'POOL_TROPICAL_FRESHWATER', 'POOL_TROPICAL_BRACKISHWATER', 'POOL_TROPICAL_SALTWATER', 'LAKE_TEMPERATE_FRESHWATER',
      'LAKE_TEMPERATE_BRACKISHWATER', 'LAKE_TEMPERATE_SALTWATER', 'LAKE_TROPICAL_FRESHWATER', 'LAKE_TROPICAL_BRACKISHWATER',
      'LAKE_TROPICAL_SALTWATER', 'RIVER_TEMPERATE_FRESHWATER', 'RIVER_TEMPERATE_BRACKISHWATER', 'RIVER_TEMPERATE_SALTWATER',
      'RIVER_TROPICAL_FRESHWATER', 'RIVER_TROPICAL_BRACKISHWATER', 'RIVER_TROPICAL_SALTWATER']
def _r(a, b): return _B[a:b + 1]
SETS = {'ALL_MAIN': _r(0, 29) + _r(36, 41), 'ANY_LAND': _r(0, 26), 'ANY_OCEAN': _r(27, 29), 'ANY_LAKE': _r(36, 41),
        'ANY_TEMPERATE_LAKE': _r(36, 38), 'ANY_TROPICAL_LAKE': _r(39, 41), 'ANY_RIVER': _r(42, 47), 'ANY_TEMPERATE_RIVER': _r(42, 44),
        'ANY_TROPICAL_RIVER': _r(45, 47), 'ANY_POOL': _r(30, 35), 'NOT_FREEZING': _r(3, 26),
        'ANY_TEMPERATE': _r(3, 6) + _r(13, 14) + _r(18, 20), 'ANY_TROPICAL': _r(7, 11) + _r(15, 17) + _r(21, 23),
        'ANY_FOREST': _r(12, 17), 'ANY_SHRUBLAND': [_B[20], _B[23]], 'ANY_GRASSLAND': [_B[18], _B[21]], 'ANY_SAVANNA': [_B[19], _B[22]],
        'ANY_TEMPERATE_FOREST': _r(13, 14), 'ANY_TROPICAL_FOREST': _r(15, 17), 'ANY_TEMPERATE_BROADLEAF': _r(3, 6) + [_B[14]] + _r(18, 20),
        'ANY_TROPICAL_BROADLEAF': _r(7, 11) + _r(16, 17) + _r(21, 23), 'ANY_WETLAND': _r(3, 11), 'ANY_TEMPERATE_WETLAND': _r(3, 6),
        'ANY_TROPICAL_WETLAND': _r(7, 11), 'ANY_TROPICAL_MARSH': _r(10, 11), 'ANY_TEMPERATE_MARSH': _r(5, 6),
        'ANY_TROPICAL_SWAMP': _r(7, 9), 'ANY_TEMPERATE_SWAMP': _r(3, 4), 'ANY_DESERT': _r(24, 26), 'TAIGA': ['FOREST_TAIGA'],
        'MOUNTAINS': ['MOUNTAIN']}
UNKNOWN_BIOME = set()

def expand(tok):
    if tok in CONCRETE: return [tok]
    if tok in SETS: return SETS[tok]
    UNKNOWN_BIOME.add(tok)
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
            # DF applies the variation at once; inline CV_* tags that follow collect into the CURRENT variation, which
            # APPLY_CURRENT_CREATURE_VARIATION applies. rev 2 (1 Oct 2026): this used to seed CURRENT with the variation
            # too, so a giant's CHANGE_FREQUENCY_PERC:50 was applied twice (GIANT_EAGLE 12 instead of 25; the ECO
            # census, data/eco-desk/census.py, reads 25).
            tags = apply_variation(tags, variations.get(t[1], []), t[2:])
            current = []
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
               "VERMIN_SOIL_COLONY", "VERMIN_ROTTER", "VERMIN_EATER", "VERMIN_MICRO", "EQUIPMENT_WAGON", "DOES_NOT_EXIST",
               # rev 2: the tokens the ECO study and the v6.9/v7.0 tool turn on
               "GOOD", "EVIL", "FANCIFUL", "CAN_SPEAK", "CAN_LEARN", "CURIOUSBEAST_EATER", "CURIOUSBEAST_GUZZLER",
               "CURIOUSBEAST_ITEM", "NOBONES", "MEGABEAST", "SEMIMEGABEAST", "STANDARD_GRAZER"]
# SCAV.TEXT (v6.9.0): species whose raws describe carrion-eating but carry no BONECARN or CURIOUS_BEAST_EATER
SCAV_TEXT = {"BIRD_VULTURE", "BIRD_BUZZARD", "BEAR_BLACK", "JACKAL", "HYENA", "BIRD_RAVEN", "FLESH_BALL"}

SWV_LABEL = {"SWV_GROUND_BUG": "ground bugs", "SWV_SOIL": "soil life", "SWV_FLYING_INSECT": "flying insects", "SWV_SMALL_BIRD": "small birds",
             "SWV_SMALL_MAMMAL": "small mammals", "SWV_HERP": "herps", "SWV_SMALL_FISH": "small fish", "SWV_OTHER": "other vermin"}

def swv_class(names, classes):   # VERMIN.swvClass (v7.0.0), in the engine's order
    flier = "FLIER" in names
    if "EDIBLE_GROUND_BUG" in classes: c = "SWV_GROUND_BUG"
    elif "VERMIN_FISH" in names or "AQUATIC" in names or "IMMOBILE_LAND" in names: c = "SWV_SMALL_FISH"
    elif "VERMIN_MICRO" in names or "VERMIN_ROTTER" in names: c = "SWV_FLYING_INSECT"
    elif "VERMIN_SOIL_COLONY" in names or "VERMIN_SOIL" in names: c = "SWV_SOIL"
    elif "MAMMAL" in classes: c = "SWV_SMALL_MAMMAL"
    elif flier and "LAYS_EGGS" in names: c = "SWV_SMALL_BIRD"
    elif flier: c = "SWV_FLYING_INSECT"
    elif "AMPHIBIOUS" in names or "NOBONES" not in names: c = "SWV_HERP"
    elif "VERMIN_GROUNDER" in names: c = "SWV_GROUND_BUG"
    else: c = "SWV_OTHER"
    return SWV_LABEL[c]

def tool_guild(r):   # MODEL.guild (v6.9.0), on the readings after the animal-person mirror
    if r["vermin"]: return "V"
    aquatic = r["habitat"] == "aquatic"
    amphib = not aquatic and r["_amphib"]
    lp, flier = r["_lp"], r["_flier"]
    diet = r["_diet"]
    if lp and not flier and (aquatic or amphib): return "AW"
    if flier and (diet or lp): return "RP"
    if lp: return "AL"
    if diet: return "MW" if aquatic else "ML"
    if r["grazer"]: return "GZ"
    if flier: return "WB" if r["_water"] else "LB"
    if aquatic:
        if r["_ocean"]: return "PE" if r["tool_mass"] >= 1_000_000 else "FC"
        return "FF"
    if amphib or (r["_water"] and not r["_land"]): return "SH"
    return "PL"

GUILD_NAME = {"V": "vermin", "AW": "water apex", "RP": "raptor", "AL": "land apex", "MW": "water mesopredator", "ML": "ground mesocarnivore",
              "GZ": "grazer herd", "WB": "waterbird", "LB": "land bird", "PE": "pelagic", "FC": "coastal fish", "FF": "freshwater fish",
              "SH": "shore", "PL": "land prey"}

def band_of(mass):   # MODEL.band (D4): small < 150,000 cm3, medium < 1,000,000, large from 1,000,000
    return "large" if mass >= 1_000_000 else ("medium" if mass >= 150_000 else "small")

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
    # rev 2: the CP437 code and the DF colour (fg, bg, bright) -- text from the raws, for an ASCII glyph without the font
    d["tile_code"] = (ord(tv[1]) if tv.startswith("'") and len(tv) >= 3 else (int(tv) if tv.isdigit() else None))
    col = next((t for t in tags if t[0] == "COLOR"), None)
    d["color"] = [num(col, 1, 7), num(col, 2, 0), num(col, 3, 0)] if col else None
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
    # rev 2: the size as the tool reads it. DF stores caste body sizes in units of 10 cm3 (at least 1), then applies
    # CHANGE_BODY_SIZE_PERC; the tool multiplies back by 10 (adultSize, v6.4.1). Matches the live MODEL.audit
    # (fixtures/species-model.tsv) on every creature that is not an animal person. Tiny roots floor at 10 cm3, so their
    # giants read ten times the raw (GIANT_DAMSELFLY 2,000,070, large, not 200,007, medium).
    tm = max(1, max(sizes) // 10) if sizes and max(sizes) > 0 else 0
    for t in tags:
        if t[0] == "CHANGE_BODY_SIZE_PERC" and num(t, 1):
            tm = tm * num(t, 1) // 100
    d["tool_mass"] = tm * 10
    d["band"] = band_of(d["tool_mass"])
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
    # rev 2: VERMIN_SOIL_COLONY counts (DF sets the soil flag for a colony; the live tool reads ANT, BUMBLEBEE,
    # HONEY_BEE and TERMITE as vermin -- fixtures/species-model.tsv)
    d["vermin"] = any(f in names for f in ("VERMIN_GROUNDER", "VERMIN_ROTTER", "VERMIN_SOIL", "VERMIN_SOIL_COLONY", "VERMIN_FISH",
                                           "VERMIN_EATER", "SMALL_RACE"))
    d["classes"] = classes
    d["beach_frequency"] = next((num(t, 1) for t in tags if t[0] == "BEACH_FREQUENCY"), None)
    ud = next((t for t in tags if t[0] == "UNDERGROUND_DEPTH"), None)
    d["depth_min"], d["depth_max"] = (num(ud, 1), num(ud, 2)) if ud else (None, None)
    d["seasons_raw"] = [s for s, f in (("Spring", "NO_SPRING"), ("Summer", "NO_SUMMER"), ("Autumn", "NO_AUTUMN"), ("Winter", "NO_WINTER"))
                        if f not in names]
    d["alignment"] = "good" if "GOOD" in names else ("evil" if "EVIL" in names else "neither")
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
    # rev 2: inputs for the v6.9/v7.0 readings that main() finishes after the animal-person mirror
    d["grazer"] = "GRAZER" in names or "STANDARD_GRAZER" in names   # STANDARD_GRAZER sets DF's GRAZER flag
    d["_water"], d["_land"] = water, land
    d["_lp"], d["_flier"], d["_amphib"] = "LARGE_PREDATOR" in names, "FLIER" in names, "AMPHIBIOUS" in names
    d["_ocean"] = any(b.startswith("OCEAN") for b in concrete)
    d["_subterranean"] = any(b.startswith("SUBTERRANEAN") for b in concrete)
    d["_diet"] = "CARNIVORE" in names or "BONECARN" in names or CURATED_ROLE.get(cid) == "predator"
    d["_scav"] = cid in SCAV_TEXT or "BONECARN" in names or "CURIOUSBEAST_EATER" in names
    # BENIGN as the v6.9 model reads it: a curated predator (the orca) counts as armed (CURIOUS.apply clears its BENIGN)
    d["armed"] = "no (BENIGN)" if ("BENIGN" in names and CURATED_ROLE.get(cid) != "predator") else "yes"
    d["swv"] = swv_class(names, classes) if d["vermin"] else ""
    spec = next((SPECIAL[f] for f in SPECIAL if f in names), None)
    if "DOES_NOT_EXIST" in names or "EQUIPMENT_WAGON" in names: spec = "not a creature"
    d["special"] = spec or ""
    d["class"] = "natural" if not spec and concrete and size > 0 else ("special" if spec else "unclassified")
    d["tags"] = sorted(names)
    return d

# ----------------------------------------------------------------------------------- trial fort ---
def tool_readings(rows, creatures, df):
    """rev 2 (1 Oct 2026): the seasonal-wildlife readings as v7.0 makes them, after derive()'s own reading.
    Animal people (v6.7.0, MODEL.rootOf): a creature whose raw block has COPY_TAGS_FROM and
    APPLY_CREATURE_VARIATION:ANIMAL_PERSON(_LEGLESS) stands where its root stands -- role, habitat, size, group, diet and
    flight -- unless it is vermin itself; its guild is read after the mirror (MODEL.guild). Scavenger: SCAV.is (v6.9.0).
    Civilisation race: V7.isCivRaw (v7.0.0). The humanoid list is DF's entity races plus the animal people."""
    by = {r["id"]: r for r in rows}
    root = {}
    for cid, raw in creatures.items():
        frm = next((t[1] for t in raw if t[0] == "COPY_TAGS_FROM" and len(t) > 1), None)
        if frm and any(t[0] == "APPLY_CREATURE_VARIATION" and len(t) > 1 and t[1].startswith("ANIMAL_PERSON") for t in raw):
            root[cid] = frm
    for cid in creatures:   # MODEL.rootOf's fallback: a person the files do not name -> its token less _MAN (or BIRD_ + that)
        stem = cid[:-4] if cid.endswith("_MAN") else None
        if stem and cid not in root:
            for t in (stem, "BIRD_" + stem):
                if t in creatures: root[cid] = t; break
    entity = set()
    for p in (df / "data/vanilla/vanilla_entities/objects").glob("entity*.txt"):
        entity |= set(re.findall(r"\[CREATURE:([^\]]+)\]", p.read_bytes().decode("latin-1")))
    for r in rows:
        r["root"] = root.get(r["id"], "")
        r["group"] = max(1, (r["cluster_min"] + r["cluster_max"]) // 2) if r["cluster_min"] is not None and r["cluster_max"] is not None else 1
    for r in rows:
        src = by.get(r["root"])
        if src and not r["vermin"]:
            # MODEL.guild then reads the person's OWN diet tokens, breathing and biome list, the root's LP, flight, water and mass
            for k in ("category", "role", "habitat", "tool_mass", "group", "_lp", "_flier", "_ocean"):
                r[k] = src[k]
            if r["category"] == "vermin": r["category"] = r["role"]   # a person of a vermin root is a unit (validation 124603)
    for r in rows:
        r["band"] = band_of(r["tool_mass"])
        r["guild"] = tool_guild(r)
        r["guild_name"] = f'{r["guild"]} {GUILD_NAME[r["guild"]]}'
        humanoid = r["id"] in entity or bool(r["root"]) or r["id"].endswith("MAN")
        r["scavenger"] = "yes" if (r["_scav"] and not humanoid) else "no"
        r["civ_race"] = bool(("CAN_SPEAK" in r["tags"] or "CAN_LEARN" in r["tags"]) and not ("GOOD" in r["tags"] or "EVIL" in r["tags"])
                             and not r["root"] and r["_subterranean"])
        r["pelagic"] = r["guild"] == "PE"

def eco_columns(rows):
    """rev 2: the ECO desk's columns, joined by token so the two pages answer the same question the same way --
    data/eco-report/raws.json (the 736-species 'wildlife' set, the desk's own v2 guild and layer family) and
    data/eco-desk/v2/guilds/species2.tsv (apex, realms)."""
    eco = {}
    p = ROOT / "data/eco-report/raws.json"
    if p.exists():
        eco = {s["id"]: s for s in json.loads(p.read_text())["species"]}
    s2 = {}
    p2 = ROOT / "data/eco-desk/v2/guilds/species2.tsv"
    if p2.exists():
        lines = p2.read_text().splitlines()
        head = lines[0].split("\t")
        for line in lines[1:]:
            f = dict(zip(head, line.split("\t")))
            s2[f["id"]] = f
    for r in rows:
        e, f = eco.get(r["id"]), s2.get(r["id"])
        r["eco_wildlife"] = e is not None
        r["desk_guild"] = e["guild"] if e else ""
        r["layer_family"] = e["layer"] if e else ""
        r["apex"] = (f.get("apex") == "1") if f else None
        r["realms"] = [x for x in (f.get("realms") or "").split(",") if x] if f else []

def trial_fort(_rows, run_id=None):
    """Boatsbowed columns from the DwarfCron X1 runs: stock per species key, the tool's roster, X1 arrivals."""
    runs = sorted((ROOT / "data/experiments/X1").glob("*/")) if (ROOT / "data/experiments/X1").exists() else []
    if not runs: return {}
    run = next((r for r in runs if r.name == run_id), runs[-1])
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
    # rev 2: the trial-fort columns come from one named X1 run (the page was built from 202637 on 26 Sep; a later
    # run, 220001, would silently replace them if the newest were taken)
    ap.add_argument("--x1-run", default="20260926-202637")
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
    if UNKNOWN_BIOME: print("warning: biome tokens with no expansion:", sorted(UNKNOWN_BIOME))
    tool_readings(rows, creatures, df)
    eco_columns(rows)
    fort = trial_fort(rows, a.x1_run)
    for r in rows:
        f = fort.get(r["id"], {})
        r["boats_stock"] = f.get("boats_stock")
        r["boats_layers"] = f.get("boats_layers", [])
        r["boats_active"] = f.get("boats_active")
        r["boats_seasons"] = f.get("boats_seasons", "")
        r["x1_arrivals"] = f.get("x1_arrivals", 0) if f else None
    for r in rows:
        for k in [k for k in r if k.startswith("_")]: del r[k]
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(rows))
    tpl = (Path(__file__).parent / "atlas.html").read_text()
    slim = [{k: v for k, v in r.items() if k not in ("tags", "biomes", "classes")} for r in rows]   # the page needs the families, not every tag
    Path(a.out).write_text(tpl.replace("/*__DATA__*/[]", json.dumps(slim, separators=(",", ":"))))
    by = {}
    for r in rows: by[r["source"]] = by.get(r["source"], 0) + 1
    print(f"{len(rows)} creatures ({by}); natural {sum(r['class'] == 'natural' for r in rows)}; with trial-fort columns {sum(r['boats_stock'] is not None for r in rows)}")
    print(f"wrote {a.json} and {a.out}")

if __name__ == "__main__":
    main()
