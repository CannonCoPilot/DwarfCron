#!/usr/bin/env python3
"""String-match census of the user's creature tokens in DF 53.16 raws (files only, no live game).

Outputs (this directory): files.tsv, string-census.tsv, occurrences.tsv, values.tsv, values-by-creature.tsv,
cooccur-matrix-{all,wild}.csv, jaccard-matrix-{all,wild}.csv, cluster-order.json, heatmap-rows.json, cluster-cuts.json.

Matching rule. A raw tag is the text between '[' and ']'. It is split on ':'. A token is present in a tag when a
field equals the token exactly: field 0 = the tag itself ([TOKEN] / [TOKEN:...]), field >= 1 = an argument
(CV_ADD_TAG:TOKEN, CE_ADD_TAG:...:TOKEN:..., IT_FORBIDDEN:TOKEN, GO_TO_TAG:TOKEN, ...). Exact field equality is the
token-boundary rule, so GRAZER never matches STANDARD_GRAZER, PET never matches PET_EXOTIC, and so on. Text outside
brackets (comments in .txt raws, Lua code) is matched separately with an identifier boundary (not [A-Za-z0-9_]
on either side) and reported as 'bare'. Substring hits that fail the boundary are counted too, as near-misses.
Resolution (COPY_TAGS_FROM, APPLY_CREATURE_VARIATION, caste walk) reuses ../../census.py unchanged.
"""
import csv, json, re, sys, statistics
from collections import Counter, defaultdict, OrderedDict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ECO = HERE.parent.parent
sys.path.insert(0, str(ECO))
import census as C  # noqa: E402

DATA = C.DF / "data"
VAN = DATA / "vanilla"
A = VAN / "vanilla_creatures/objects"
B = VAN / "vanilla_creatures_extinct/objects"

USER = """ALL_ACTIVE AMBUSHPREDATOR AMPHIBIOUS AQUATIC ARTIFICIAL_HIVEABLE AT_PEACE_WITH_WILDLIFE BEACH_FREQUENCY BENIGN
BLOODSUCKER BONECARN CAN_LEARN CAN_SPEAK CANNOT_CLIMB CANNOT_JUMP CARNIVORE CAVE_ADAPT CLUSTER_NUMBER COMMON_DOMESTIC CRAZED
CREPUSCULAR CURIOUSBEAST_EATER CURIOUSBEAST_GUZZLER CURIOUSBEAST_ITEM DIE_WHEN_VERMIN_BITE DIURNAL DIVE_HUNTS_VERMIN EXTRAVISION
FISHITEM FLEEQUICK FLIER GAIT GNAWER GOBBLE_VERMIN_CLASS GOBBLE_VERMIN_CREATURE GOOD GRASSTRAMPLE GRAZER HUNTS_VERMIN IMMOBILE
IMMOBILE_LAND LARGE_PREDATOR LARGE_ROAMING LAYS_EGGS LAYS_UNUSUAL_EGGS LOOSE_CLUSTERS LOW_LIGHT_VISION HAUL_REFUSE MATUTINAL
MEANDERER MISCHIEVIOUS MISCHIEVOUS MOUNT MULTIPART_FULL_VISION MUNDANE NATURAL NATURAL_ANIMAL NO_AUTUMN NO_DRINK NO_SPRING
NO_SUMMER NO_WINTER NOBREATHE NOCTURNAL NOMEAT ODOR_LEVEL OPPOSED_TO_LIFE PACK_ANIMAL PET PET_EXOTIC PETVALUE POPULATION_NUMBER
PRONE_TO_RAGE RETURNS_VERMIN_KILLS_TO_OWNER ROOT_AROUND SAVAGE SENSE_CREATURE_CLASS SMALL_REMAINS SMELL_TRIGGER SPECIFIC_FOOD
STANCE_CLIMBER STANDARD_GRAZER SWIMS_INNATE SWIMS_LEARNED THICKWEB TRAINABLE TRAINABLE_HUNTING TRAINABLE_WAR TRAPAVOID
TRIGGERABLE_GROUP UBIQUITOUS UNDERGROUND_DEPTH UNDERSWIM VERMIN_BITE VERMIN_EATER VERMIN_FISH VERMIN_GROUNDER VERMIN_HATEABLE
VERMIN_MICRO VERMIN_NOFISH VERMIN_NOROAM VERMIN_NOTRAP VERMIN_ROTTER VERMIN_SOIL VERMIN_SOIL_COLONY VERMINHUNTER VESPERTINE
VIEWRANGE VISION_ARC WAGON_PULLER WEBBER WEBIMMUNE FREQUENCY EVIL BIOME CURIOUSBEAST""".split()
NINE = "BLOODSUCKER CANNOT_CLIMB CRAZED GRAZER MATUTINAL NATURAL_ANIMAL OPPOSED_TO_LIFE SENSE_CREATURE_CLASS VIEWRANGE".split()
TOKSET = set(USER)
TAGRE = re.compile(r"\[([^\[\]]+)\]")
BARE = {t: re.compile(r"(?<![A-Za-z0-9_])" + t + r"(?![A-Za-z0-9_])") for t in USER}
SUB = {t: re.compile(t) for t in USER}
CV_ADD = {"CV_ADD_TAG", "CV_NEW_TAG"}
CV_ANY = ("CV_", "CVCT_")
SYN_PREFIX = ("CE_", "CE:", "IT_", "IS_", "IE_", "IC_", "IP_", "I_", "SYN_", "CDI")
SYN_EXACT = {"CE", "CAN_DO_INTERACTION", "INTERACTION", "SYNDROME", "SPECIALATTACK_INTERACTION", "SPECIALATTACK_INJECT_EXTRACT"}
TEXT_EXT = {".txt", ".lua", ".md", ""}


LEGEND = [
    "LEGEND. Match rule: a tag [..] is split on ':'; a hit is a field exactly equal to the token (token boundary = ':' '[' ']').",
    "AB_* = hits in vanilla_creatures/objects (A) + vanilla_creatures_extinct/objects (B), every file.",
    "AB_creature_body = token is the tag name, inside a [CREATURE:..] before any CASTE/SELECT_CASTE.",
    "AB_caste_block = tag name after [CASTE:X] or [SELECT_CASTE:X] (X != ALL); AB_caste_all = tag name after [SELECT_CASTE:ALL]",
    "  (textual position only: creature-level tokens such as CLUSTER_NUMBER placed after SELECT_CASTE:ALL still apply to the creature).",
    "AB_cv_def_add/remove/other = argument 1 of CV_ADD_TAG|CV_NEW_TAG / CV_REMOVE_TAG / other CV_*|CVCT_* inside a [CREATURE_VARIATION:..] definition.",
    "AB_cv_inline_* = the same inside a creature body (applied by APPLY_CURRENT_CREATURE_VARIATION).",
    "AB_syn_arg = argument of a syndrome/interaction tag (CE_*, CE, IT_*, IS_*, IE_*, I_*, SYN_*, CDI...). AB_elsewhere = any other argument (e.g. GO_TO_TAG).",
    "AB_bare_comment_text = identifier-boundary match in text outside brackets (raw comments).",
    "n_creatures_direct = creatures whose own definition writes the token as a tag; n_creatures_resolved / n_wild_resolved = after census.py resolution.",
    "OUT_* = every other text file under data/ (vanilla objects, 'interaction examples', vanilla_procedural Lua, init/*, graphics): OUT_TAGNAME (token as the tag;",
    "  OUT_tagname_namespaces says which namespace: creature tag emitted by a procedural generator, plant/body/entity token, announcement type),",
    "  OUT_SYN_ARG (syndrome/interaction argument; OUT_arg_holders names the holder tags), OUT_OTHER_ARG, OUT_bare_text (Lua code/comments).",
    "near_miss_substrings = the token as a substring of a longer identifier (NOT counted as a hit), e.g. STANDARD_GRAZER for GRAZER.",
    "Every individual hit is listed in occurrences.tsv (file, line, category, enclosing definition or Lua function, full tag).",
]


def is_syn_holder(name):
    return name in SYN_EXACT or name.startswith(SYN_PREFIX)


def line_starts(txt):
    s = [0]
    for i, ch in enumerate(txt):
        if ch == "\n":
            s.append(i + 1)
    return s


def lineno(starts, off):
    lo, hi = 0, len(starts) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if starts[mid] <= off:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1


LUAFN = re.compile(r"^\s*(?:local\s+)?(?:function\s+([\w.:\[\]\"]+)|([\w.\[\]\"]+)\s*=\s*function)")


def scan_file(path, group):
    """Return (occurrences, bare_hits, near_misses, defs, objtypes, ntags)."""
    raw = path.read_bytes()
    txt = raw.decode("latin-1", errors="replace")
    starts = line_starts(txt)
    lines = txt.split("\n")
    is_lua = path.suffix == ".lua"
    luafn = []
    if is_lua:
        cur = ""
        for ln in lines:
            m = LUAFN.match(ln)
            if m:
                cur = m.group(1) or m.group(2)
            luafn.append(cur)
    occ, defs, objtypes = [], [], []
    obj, defkind, defid, caste = "", "", "", "none"
    ntags = 0
    tag_spans = []
    for m in TAGRE.finditer(txt):
        ntags += 1
        tag_spans.append((m.start(), m.end()))
        f = m.group(1).split(":")
        f = [x.strip() for x in f]
        name = f[0]
        if name == "OBJECT" and len(f) > 1:
            obj = f[1]; objtypes.append(f[1]); defkind, defid, caste = "", "", "none"; continue
        # top-level definition header: the tag named like the object type (CREATURE, CREATURE_VARIATION, INTERACTION, ...)
        if obj and (name == obj or (obj == "MATERIAL_TEMPLATE" and name == "MATERIAL_TEMPLATE") or
                    (obj == "BODY" and name in ("BODY", "BODYGLOSS")) or (obj == "ITEM" and name.startswith("ITEM_"))
                    or (obj == "DESCRIPTOR_COLOR" and name == "COLOR") or (obj == "DESCRIPTOR_SHAPE" and name == "SHAPE")
                    or (obj == "DESCRIPTOR_PATTERN" and name == "COLOR_PATTERN") or (obj == "LANGUAGE" and name in ("WORD", "SYMBOL", "TRANSLATION"))
                    or (obj == "BUILDING" and name.startswith("BUILDING_")) or (obj == "TISSUE_TEMPLATE" and name == "TISSUE_TEMPLATE")
                    or (obj == "BODY_DETAIL_PLAN" and name == "BODY_DETAIL_PLAN") or (obj == "GRAPHICS" and name in ("CREATURE_GRAPHICS", "TILE_PAGE"))):
            if len(f) > 1:
                defkind, defid, caste = name, f[1], "none"
                defs.append((name, f[1]))
                continue
        if defkind == "CREATURE":
            if name == "CASTE":
                caste = "caste"; continue
            if name == "SELECT_CASTE":
                caste = "all" if len(f) > 1 and f[1] == "ALL" else "caste"; continue
            if name == "SELECT_ADDITIONAL_CASTE":
                continue
        hit = [(i, x) for i, x in enumerate(f) if x in TOKSET]
        if not hit:
            continue
        ln = lineno(starts, m.start())
        ctx = lines[ln - 1].strip()[:200]
        for i, tok in hit:
            if i == 0:
                if defkind == "CREATURE":
                    cat = "creature_body" if caste == "none" else ("caste_all" if caste == "all" else "caste_block")
                elif defkind == "CREATURE_VARIATION":
                    cat = "cv_def_other"
                elif group in ("A", "B"):
                    cat = "elsewhere"
                else:
                    cat = "out_tagname"
            else:
                if name in CV_ADD and i == 1:
                    kind = "add"
                elif name == "CV_REMOVE_TAG" and i == 1:
                    kind = "remove"
                elif name.startswith(CV_ANY):
                    kind = "other"
                else:
                    kind = None
                if kind:
                    cat = ("cv_def_" if defkind == "CREATURE_VARIATION" else "cv_inline_") + kind
                elif is_syn_holder(name):
                    cat = "syn_arg"
                else:
                    cat = "elsewhere" if group in ("A", "B") else "out_other_arg"
                if group not in ("A", "B") and cat.startswith("cv_"):
                    cat = "out_other_arg"
                if group not in ("A", "B") and cat == "syn_arg":
                    cat = "out_syn_arg"
            occ.append(dict(token=tok, group=group, file=str(path.relative_to(DATA)), line=ln, field=i, holder=name,
                            cat=cat, obj=obj, defkind=defkind, defid=defid, luafn=luafn[ln - 1] if is_lua else "",
                            tag="[" + m.group(1)[:160] + "]", ctx=ctx))
    # outside-bracket text
    mask = [True] * len(txt)
    for s, e in tag_spans:
        for k in range(s, e):
            mask[k] = False
    outside = "".join(ch if keep else " " for ch, keep in zip(txt, mask))
    bare, near = [], []
    for t in USER:
        if t not in txt:
            continue
        for mm in BARE[t].finditer(outside):
            ln = lineno(starts, mm.start())
            bare.append(dict(token=t, group=group, file=str(path.relative_to(DATA)), line=ln,
                             luafn=luafn[ln - 1] if is_lua else "", ctx=lines[ln - 1].strip()[:200]))
        nb = {mm.start() for mm in BARE[t].finditer(txt)}
        for mm in SUB[t].finditer(txt):
            if mm.start() in nb:
                continue
            s = mm.start()
            a = s
            while a > 0 and (txt[a - 1].isalnum() or txt[a - 1] == "_"):
                a -= 1
            e = mm.end()
            while e < len(txt) and (txt[e].isalnum() or txt[e] == "_"):
                e += 1
            near.append((t, txt[a:e], str(path.relative_to(DATA))))
    return occ, bare, near, defs, objtypes, ntags


def namespace(o):
    """What an outside tag-name hit is: the token namespace it belongs to."""
    fn = o["file"].split("/")[-1]
    if fn == "announcements.txt":
        return "announcement type (data/init/announcements.txt), not a creature token"
    if o["obj"] in ("BODY", "BODY_DETAIL_PLAN"):
        return f"body-part token ({fn})"
    if o["obj"] == "PLANT":
        return f"plant token ({fn})"
    if o["obj"]:
        return f"{o['obj']} object token ({fn})"
    if fn.endswith(".lua") and (fn in ("creatures.lua", "shared_info.lua", "rcp.lua")):
        return f"creature tag emitted by procedural creature generator {fn}:{o['luafn']}"
    return f"{fn}:{o['luafn']}"


def group_of(p):
    if p.parent == A:
        return "A"
    if p.parent == B:
        return "B"
    return "OUT"


def all_files():
    files = []
    for p in sorted(DATA.rglob("*")):
        if not p.is_file() or p.name == ".DS_Store":
            continue
        if p.suffix.lower() not in TEXT_EXT:
            continue
        files.append(p)
    for d in (A, B):  # every file in A and B regardless of extension
        for p in sorted(d.iterdir()):
            if p.is_file() and p not in files:
                files.append(p)
    return files


# ------------------------------------------------------------------------------------------ resolution ---
def resolve_all():
    paths = [(p, "vanilla") for p in sorted(A.glob("*.txt"))] + [(p, "extinct") for p in sorted(B.glob("*.txt"))]
    creatures, variations, source = C.read_objects(paths)
    cache, info, rows = {}, {}, {}
    for cid in creatures:
        tags = C.resolve(cid, creatures, variations, cache, info)
        castes, occ = C.caste_walk(tags)
        names = set(occ)
        var = info[cid]["variations"]
        kind = "animal_person" if ("ANIMAL_PERSON" in var or "ANIMAL_PERSON_LEGLESS" in var) else ("giant" if "GIANT" in var else "")
        biomes = list(dict.fromkeys(o[1][1] for o in occ.get("BIOME", []) if len(o[1]) > 1))
        r = dict(id=cid, source=source[cid][0], file=source[cid][1], kind=kind, castes=castes, occ=occ, _names=names,
                 biomes=",".join(biomes), biome_list=biomes)
        r["wild"] = C.is_wild(r)
        rows[cid] = r
    return creatures, variations, source, rows


def direct_tokens(creatures):
    """Tokens written as a tag (field 0) in each creature's own definition, unresolved."""
    d = {}
    for cid, tags in creatures.items():
        d[cid] = {t[0] for t in tags if t[0] in TOKSET}
    return d


WATER = re.compile(r"OCEAN|LAKE|RIVER|POOL")


def guild(r):
    """Primary Q6 guild (Q6-setgroups.md table, reimplemented; precedence G15 > G14 > water guilds > land guilds)."""
    n = r["_names"]; b = r["biome_list"]
    sub = bool(b) and all(x.startswith("SUBTERRANEAN") for x in b)
    surface = not sub
    water_all = bool(b) and all(WATER.search(x) for x in b)
    water_any = any(WATER.search(x) for x in b)
    ocean = any("OCEAN" in x for x in b)
    lr = "LARGE_ROAMING" in n
    size = body_size(r)
    if sub:
        return "G15 cavern"
    if any(v in n for v in C.VERMIN_TYPES):
        return "G14 vermin"
    lp = "LARGE_PREDATOR" in n
    aq = "AQUATIC" in n; amph = "AMPHIBIOUS" in n; fl = "FLIER" in n
    carn = "CARNIVORE" in n or "BONECARN" in n
    if lp and (aq or amph) and surface:
        return "G2 water apex"
    if aq and lr and ocean and (size >= 1_000_000 or "BEACH_FREQUENCY" in n):
        return "G9 pelagic"
    if aq and lr and ocean:
        return "G10 coastal fish"
    if aq and lr and water_any and not ocean:
        return "G11 freshwater fish"
    if fl and water_any and lr and "BONECARN" not in n:
        return "G12 waterbird"
    if amph or (water_all and not aq and not fl):
        return "G8 shore"
    if lp and not aq and not amph and surface:
        return "G1 land apex"
    if fl and "BONECARN" in n:
        return "G4 raptor"
    if fl and lr and "BONECARN" not in n and not water_any:
        return "G13 land bird"
    if "STANDARD_GRAZER" in n:
        return "G6 grazer"
    if carn and not lp and not fl and not aq and lr:
        return "G3 mesocarnivore"
    if lr and "BENIGN" in n and not carn and not fl and not aq and not amph:
        return "G7 land prey"
    return "other"


def body_size(r):
    occ = r["occ"]
    bs = [C.num(o[1][3], 0) for o in occ.get("BODY_SIZE", []) if len(o[1]) > 3]
    size = bs[-1] if bs else 0
    for o in occ.get("CHANGE_BODY_SIZE_PERC", []):
        if C.num(o[1][1]):
            size = size * C.num(o[1][1]) // 100
    return size


# ------------------------------------------------------------------------------------------ values ---
VALUED = ["FREQUENCY", "POPULATION_NUMBER", "CLUSTER_NUMBER", "BEACH_FREQUENCY", "PETVALUE", "PRONE_TO_RAGE", "ODOR_LEVEL",
          "SMELL_TRIGGER", "VIEWRANGE", "VISION_ARC", "GRASSTRAMPLE", "GRAZER", "LOW_LIGHT_VISION", "UNDERGROUND_DEPTH",
          "TRIGGERABLE_GROUP", "GAIT", "SPECIFIC_FOOD", "SENSE_CREATURE_CLASS", "GOBBLE_VERMIN_CLASS", "GOBBLE_VERMIN_CREATURE",
          "SMALL_REMAINS", "STANDARD_GRAZER", "BIOME"]
# Defaults: only where wiki-tokens.md states one (row cited). Never invented.
DEFAULTS = {
    "FREQUENCY": ("50", "wiki-tokens.md row FREQUENCY: 'Creature (0-100; default 50)' (CT#FREQUENCY)"),
    "CLUSTER_NUMBER": ("1:1", "wiki-tokens.md row CLUSTER_NUMBER: 'Default 1:1' (CT#CLUSTER_NUMBER)"),
    "POPULATION_NUMBER": ("1:1", "wiki-tokens.md row POPULATION_NUMBER: 'Default 1:1' (CT#POPULATION_NUMBER)"),
    "ODOR_LEVEL": ("50", "wiki-tokens.md row ODOR_LEVEL: 'Default 50' (CT#ODOR_LEVEL)"),
    "GRASSTRAMPLE": ("5", "wiki-tokens.md row GRASSTRAMPLE: 'Default 5' (CT#GRASSTRAMPLE)"),
    "VIEWRANGE": ("20", "wiki-tokens.md row VIEWRANGE: 'Default 20' (CT#VIEWRANGE)"),
    "VISION_ARC": ("60:120", "wiki-tokens.md row VISION_ARC: 'default 60:120' (CT#VISION_ARC)"),
}
MULTI = {"GAIT", "SPECIFIC_FOOD", "SENSE_CREATURE_CLASS", "GOBBLE_VERMIN_CLASS", "GOBBLE_VERMIN_CREATURE", "BIOME"}
LASTWINS_CREATURE = {"FREQUENCY", "POPULATION_NUMBER", "CLUSTER_NUMBER", "UNDERGROUND_DEPTH", "TRIGGERABLE_GROUP"}


def creature_values(r, tok):
    """-> (values list per caste-effective, varies flag). Multi tokens -> sorted set of value strings."""
    os_ = r["occ"].get(tok, [])
    if not os_:
        return None, False
    if tok in MULTI:
        if tok == "GAIT":
            return sorted({o[1][1] for o in os_ if len(o[1]) > 1}), False
        return sorted({":".join(o[1][1:]) for o in os_}), False
    if tok in LASTWINS_CREATURE:
        return [":".join(os_[-1][1][1:])], False
    castes = r["castes"]
    eff = {}
    for sel, t, _ in os_:
        targets = castes if sel == "ALL" else [c for c in castes if c in sel] or list(sel)
        for c in targets:
            eff[c] = ":".join(t[1:])
    vals = [eff[c] for c in castes if c in eff] or list(eff.values())
    return vals, len(set(vals)) > 1


def numparts(v):
    out = []
    for x in v.split(":"):
        try:
            out.append(int(x))
        except ValueError:
            out.append(None)
    return out


def summarize(nums):
    nums = sorted(nums)
    if not nums:
        return {}
    q = lambda p: nums[min(len(nums) - 1, int(round(p * (len(nums) - 1))))]
    return dict(n=len(nums), min=nums[0], p25=q(.25), median=statistics.median(nums), p75=q(.75), max=nums[-1],
                mean=round(sum(nums) / len(nums), 2))


def hist(nums):
    if not nums:
        return ""
    lo, hi = min(nums), max(nums)
    if hi - lo <= 12 and all(isinstance(x, int) for x in nums):
        c = Counter(nums)
        return "; ".join(f"{k}:{c[k]}" for k in sorted(c))
    edges = sorted({0, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000, 10 ** 6, 10 ** 7})
    edges = [e for e in edges if e >= min(lo, 0)]
    c = Counter()
    for x in nums:
        k = max([e for e in edges if e <= x], default=lo)
        c[k] += 1
    ks = sorted(c)
    lab = lambda k: f">={k}" if k == edges[-1] else f"{k}-{edges[edges.index(k) + 1] - 1}" if k in edges else str(k)
    return "; ".join(f"{lab(k)}:{c[k]}" for k in ks)


def behav3(r):
    n = r["_names"]; lp = "LARGE_PREDATOR" in n; be = "BENIGN" in n
    return "LP+BENIGN" if lp and be else "LARGE_PREDATOR" if lp else "BENIGN" if be else "neither"


GROUPINGS = {
    "behaviour": behav3,
    "flier": lambda r: "FLIER" if "FLIER" in r["_names"] else "no FLIER",
    "vermin": lambda r: "vermin" if any(v in r["_names"] for v in C.VERMIN_TYPES) else "not vermin",
    "guild": guild,
    "kind": lambda r: r["kind"] or r["source"],
}


# ------------------------------------------------------------------------------------------ clustering ---
def average_linkage(D, labels):
    n = len(labels)
    clusters = {i: [i] for i in range(n)}
    dist = {}
    for i in range(n):
        for j in range(i + 1, n):
            dist[(i, j)] = D[i][j]
    merges, nxt = [], n
    active = set(range(n))
    while len(active) > 1:
        (a, b), d = min(((k, v) for k, v in dist.items() if k[0] in active and k[1] in active), key=lambda kv: (round(kv[1], 12), kv[0]))
        active -= {a, b}
        clusters[nxt] = clusters[a] + clusters[b]
        merges.append(dict(id=nxt, a=a, b=b, distance=round(d, 6), size=len(clusters[nxt]),
                           a_members=[labels[x] for x in clusters[a]], b_members=[labels[x] for x in clusters[b]]))
        for c in active:
            na, nb = len(clusters[a]), len(clusters[b])
            da = dist[(min(a, c), max(a, c))]; db = dist[(min(b, c), max(b, c))]
            dist[(c, nxt)] = (na * da + nb * db) / (na + nb)
        active.add(nxt)
        nxt += 1
    root = nxt - 1
    order = clusters[root] if n > 1 else [0]
    return merges, [labels[i] for i in order], clusters


def cut(merges, labels, thr):
    """Flat clusters: merges with distance <= thr."""
    parent = {i: i for i in range(len(labels) + len(merges))}
    groups = {i: [labels[i]] for i in range(len(labels))}
    for m in merges:
        if m["distance"] <= thr:
            groups[m["id"]] = groups.pop(m["a"]) + groups.pop(m["b"])
    return [g for g in groups.values()]


def cooccur(rows, toks):
    pres = {t: {r["id"] for r in rows if t in r["_names"]} for t in toks}
    return pres


def main():
    files = all_files()
    creatures, variations, source, rows = resolve_all()
    direct = direct_tokens(creatures)
    earlier = set()
    with open(ECO / "tokens-by-creature.tsv") as f:
        rd = csv.DictReader(f, delimiter="\t")
        for r in rd:
            earlier.add(r["id"])

    # ---------------------------------------------------------------- scan every file
    occ_all, bare_all, near_all = [], [], []
    frows = []
    per_file_creatures = {}
    for p in files:
        g = group_of(p)
        occ, bare, near, defs, objtypes, ntags = scan_file(p, g)
        occ_all += occ; bare_all += bare; near_all += near
        if g in ("A", "B"):
            cr = [d[1] for d in defs if d[0] == "CREATURE"]
            cv = [d[1] for d in defs if d[0] == "CREATURE_VARIATION"]
            other = Counter(d[0] for d in defs if d[0] not in ("CREATURE", "CREATURE_VARIATION"))
            per_file_creatures[p.name] = cr
            miss = [c for c in cr if c not in earlier]
            frows.append(dict(folder=g, file=p.name, bytes=p.stat().st_size, object_types=",".join(objtypes), n_tags=ntags,
                              n_CREATURE=len(cr), n_CREATURE_VARIATION=len(cv),
                              other_definitions="; ".join(f"{k}:{v}" for k, v in other.items()),
                              n_in_earlier_census=sum(c in earlier for c in cr), missing_from_earlier_census=",".join(miss),
                              read_by_census_py=int(p.suffix == ".txt"), variation_ids=",".join(cv)))
    with open(HERE / "files.tsv", "w") as f:
        cols = list(frows[0])
        f.write("\t".join(cols) + "\n")
        for r in frows:
            f.write("\t".join(str(r[c]) for c in cols) + "\n")
        allc = [c for v in per_file_creatures.values() for c in v]
        dup = [c for c, n in Counter(allc).items() if n > 1]
        extra = sorted(earlier - set(allc))
        f.write(f"# TOTAL\tfiles={len(frows)}\tcreature_defs={len(allc)}\tdistinct={len(set(allc))}\tduplicates={','.join(dup) or 'none'}"
                f"\tin_earlier_census={len(set(allc) & earlier)}/{len(set(allc))}\tearlier_census_rows={len(earlier)}"
                f"\tin_census_not_in_files={','.join(extra) or 'none'}\n")

    # ---------------------------------------------------------------- occurrences.tsv (every hit, for audit)
    with open(HERE / "occurrences.tsv", "w") as f:
        cols = ["token", "group", "file", "line", "cat", "field", "holder", "obj", "defkind", "defid", "luafn", "tag", "ctx"]
        f.write("\t".join(cols) + "\n")
        for o in sorted(occ_all, key=lambda o: (o["token"], o["group"], o["file"], o["line"])):
            f.write("\t".join(str(o[c]).replace("\t", " ") for c in cols) + "\n")
        for b in bare_all:
            f.write("\t".join(str(x).replace("\t", " ") for x in [b["token"], b["group"], b["file"], b["line"], "bare_text", "", "", "", "", "", b["luafn"], "", b["ctx"]]) + "\n")

    # ---------------------------------------------------------------- string-census.tsv
    ids = list(rows)
    wild = [rows[c] for c in ids if rows[c]["wild"]]
    by_tok = defaultdict(list)
    for o in occ_all:
        by_tok[o["token"]].append(o)
    bare_by = defaultdict(list)
    for b in bare_all:
        bare_by[b["token"]].append(b)
    near_by = defaultdict(Counter)
    for t, word, fn in near_all:
        near_by[t][word] += 1
    AB_CATS = ["creature_body", "caste_block", "caste_all", "cv_def_add", "cv_def_remove", "cv_def_other", "cv_inline_add",
               "cv_inline_remove", "cv_inline_other", "syn_arg", "elsewhere"]
    OUT_CATS = ["out_tagname", "out_syn_arg", "out_other_arg"]
    census_rows = []
    for t in USER:
        os_ = by_tok[t]
        ab = [o for o in os_ if o["group"] in ("A", "B")]
        out = [o for o in os_ if o["group"] == "OUT"]
        cat = Counter(o["cat"] for o in os_)
        n_direct = sum(t in direct[c] for c in ids)
        n_res = sum(t in rows[c]["_names"] for c in ids)
        n_res_w = sum(t in r["_names"] for r in wild)
        abfiles = Counter(o["file"].split("/")[-1] for o in ab)
        outfiles = Counter(o["file"] for o in out)
        bare_ab = [b for b in bare_by[t] if b["group"] in ("A", "B")]
        bare_out = [b for b in bare_by[t] if b["group"] == "OUT"]
        hold_ab = Counter(o["holder"] for o in ab if o["field"] > 0)
        hold_out = Counter(o["holder"] for o in out if o["field"] > 0)
        # verdict
        if ab and n_res:
            verdict = "creature token in vanilla creature raws"
        elif ab:
            verdict = "in creature raws only as argument/variation (no creature carries it after resolution)"
        elif out:
            kinds = []
            if cat["out_tagname"]:
                where = sorted({namespace(o) for o in out if o["cat"] == "out_tagname"})
                kinds.append("as a tag: " + " | ".join(where))
            if cat["out_syn_arg"]:
                kinds.append("syndrome/interaction argument (" + ", ".join(f"{k}x{v}" for k, v in hold_out.most_common()) + ")")
            if cat["out_other_arg"]:
                kinds.append("other argument")
            verdict = "absent from creature folders; outside: " + "; ".join(kinds)
        elif bare_by[t]:
            verdict = "only in comment/code text outside tags"
        else:
            verdict = "absent from every file under data/ (exact-field match)"
        ex_ab = ab[0] if ab else None
        ex_out = next((o for o in out if o["cat"] == "out_tagname"), out[0] if out else None)
        census_rows.append(OrderedDict([
            ("token", t), ("in_the_nine", "YES" if t in NINE else ""), ("verdict", verdict),
            ("AB_hits", len(ab)), *[("AB_" + c, cat[c]) for c in AB_CATS],
            ("AB_bare_comment_text", len(bare_ab)),
            ("n_creatures_direct", n_direct), ("n_creatures_resolved", n_res), ("n_wild_resolved", n_res_w),
            ("AB_n_files", len(abfiles)), ("AB_files", ",".join(f"{k}:{v}" for k, v in sorted(abfiles.items()))),
            ("AB_arg_holders", ",".join(f"{k}:{v}" for k, v in hold_ab.most_common())),
            ("AB_example", f"{ex_ab['file'].split('/')[-1]}:{ex_ab['line']} {ex_ab['tag']} ({ex_ab['defkind']} {ex_ab['defid']}, {ex_ab['cat']})" if ex_ab else ""),
            ("OUT_hits", len(out)), *[(c.upper(), cat[c]) for c in OUT_CATS], ("OUT_bare_text", len(bare_out)),
            ("OUT_files", ",".join(f"{k}:{v}" for k, v in sorted(outfiles.items()))),
            ("OUT_tagname_namespaces", " | ".join(f"{k} x{v}" for k, v in Counter(namespace(o) for o in out if o["cat"] == "out_tagname").most_common())),
            ("OUT_arg_holders", ",".join(f"{k}:{v}" for k, v in hold_out.most_common())),
            ("OUT_example", f"{ex_out['file']}:{ex_out['line']}{(' fn ' + ex_out['luafn']) if ex_out['luafn'] else ''} {ex_out['tag']}" if ex_out else ""),
            ("near_miss_substrings", ",".join(f"{k}:{v}" for k, v in near_by[t].most_common(8))),
        ]))
    with open(HERE / "string-census.tsv", "w") as f:
        cols = list(census_rows[0])
        f.write("\t".join(cols) + "\n")
        for r in census_rows:
            f.write("\t".join(str(r[c]).replace("\t", " ") for c in cols) + "\n")
        for line in LEGEND:
            f.write("# " + line + "\n")

    # ---------------------------------------------------------------- values
    allrows = [rows[c] for c in ids]
    vrows = []
    percre = []
    for t in VALUED:
        for popname, pop in (("all", allrows), ("wild", wild)):
            groupings = [("all", lambda r: "all")] + list(GROUPINGS.items())
            if popname == "all":
                groupings = [g for g in groupings if g[0] != "guild"]
            for gname, gf in groupings:
                grp = defaultdict(list)
                for r in pop:
                    grp[gf(r)].append(r)
                for gv in sorted(grp):
                    members = grp[gv]
                    have, vals, varies = [], [], 0
                    for r in members:
                        v, var = creature_values(r, t)
                        if v is None:
                            continue
                        have.append(r); vals.append((r, v)); varies += var
                    if gname != "all" and not have:
                        continue
                    comps = defaultdict(list)
                    topc = Counter()
                    for r, vs in vals:
                        if t in MULTI:
                            for x in vs:
                                topc[x.split(":")[0] if t in ("GAIT",) else x] += 1
                            continue
                        v = max(vs, key=lambda s: numparts(s)[0] if numparts(s) and numparts(s)[0] is not None else -1)
                        topc[v] += 1
                        for k, x in enumerate(numparts(v)):
                            if x is not None:
                                comps[k].append(x)
                    base = OrderedDict(token=t, population=popname, grouping=gname, group=gv, n_group=len(members),
                                       n_with_token=len(have), n_absent=len(members) - len(have),
                                       n_caste_varying=varies,
                                       default_if_absent=DEFAULTS.get(t, ("", ""))[0],
                                       top_values="; ".join(f"{k}={v}" for k, v in topc.most_common(12)))
                    if not comps:
                        vrows.append(base | dict(component="", min="", p25="", median="", p75="", max="", mean="", histogram="",
                                                 median_with_default="", mean_with_default=""))
                    for k, nums in sorted(comps.items()):
                        s = summarize(nums)
                        dflt = DEFAULTS.get(t)
                        md = mn = ""
                        if dflt and gname in ("all", "behaviour", "flier", "vermin", "guild", "kind"):
                            dv = numparts(dflt[0])
                            if k < len(dv) and dv[k] is not None:
                                imp = nums + [dv[k]] * (len(members) - len(have))
                                md = statistics.median(imp); mn = round(sum(imp) / len(imp), 2)
                        vrows.append(base | dict(component=k + 1, **{x: s.get(x, "") for x in ("min", "p25", "median", "p75", "max", "mean")},
                                                 histogram=hist(nums), median_with_default=md, mean_with_default=mn))
    with open(HERE / "values.tsv", "w") as f:
        cols = list(vrows[0])
        f.write("\t".join(cols) + "\n")
        for r in vrows:
            f.write("\t".join(str(r.get(c, "")) for c in cols) + "\n")
    # per-creature values (wide) for audit
    with open(HERE / "values-by-creature.tsv", "w") as f:
        cols = ["id", "wild", "source", "kind", "guild", "behaviour", "castes"] + VALUED
        f.write("\t".join(cols) + "\n")
        for r in allrows:
            cells = [r["id"], int(r["wild"]), r["source"], r["kind"], guild(r) if r["wild"] else "", behav3(r), ",".join(r["castes"])]
            for t in VALUED:
                v, var = creature_values(r, t)
                cells.append("" if v is None else ("|".join(v) if (t in MULTI or var) else v[0]) if v else "1")
            f.write("\t".join(map(str, cells)) + "\n")

    # ---------------------------------------------------------------- co-occurrence + clustering
    clus = {}
    cuts = {}
    for popname, pop in (("all", allrows), ("wild", wild)):
        pres = cooccur(pop, USER)
        freq = {t: len(pres[t]) for t in USER}
        keep = [t for t in USER if freq[t] >= 3]
        J = lambda a, b: (len(pres[a] & pres[b]) / len(pres[a] | pres[b])) if (pres[a] | pres[b]) else 0.0
        D = [[1 - J(a, b) for b in keep] for a in keep]
        merges, order, _ = average_linkage(D, keep)
        rest = sorted([t for t in USER if t not in keep], key=lambda t: (-freq[t], t))
        full = order + rest
        with open(HERE / f"cooccur-matrix-{popname}.csv", "w", newline="") as f:
            w = csv.writer(f); w.writerow(["token"] + full)
            for a in full:
                w.writerow([a] + [len(pres[a] & pres[b]) for b in full])
        with open(HERE / f"jaccard-matrix-{popname}.csv", "w", newline="") as f:
            w = csv.writer(f); w.writerow(["token"] + full)
            for a in full:
                w.writerow([a] + [f"{J(a, b):.4f}" for b in full])
        clus[popname] = dict(n_creatures=len(pop), rule="presence = token is a tag name anywhere in the resolved tag list (any caste); "
                             "tokens with >=3 creatures clustered; distance = 1 - Jaccard; average linkage (UPGMA), implemented in token_census.py",
                             order=order, not_clustered_lt3=rest, freq={t: freq[t] for t in full},
                             merges=merges)
        cuts[popname] = {str(th): [dict(tokens=g, n_all=len(set.intersection(*[pres[x] for x in g])), n_any=len(set.union(*[pres[x] for x in g])),
                                         mean_pair_jaccard=round(statistics.mean([J(a, b) for i, a in enumerate(g) for b in g[i + 1:]]), 3) if len(g) > 1 else 1.0)
                                    for g in cut(merges, keep, th) if len(g) > 1] for th in (0.3, 0.5, 0.6, 0.7, 0.8)}
        if popname == "wild":
            cells = []
            for i, a in enumerate(order):
                for b in order[i:]:
                    cells.append(dict(a=a, b=b, count=len(pres[a] & pres[b]), jaccard=round(J(a, b), 4)))
            (HERE / "heatmap-rows.json").write_text(json.dumps(dict(
                population="wildlife (census.py is_wild)", n_creatures=len(pop), order=order,
                freq=[dict(token=t, n=freq[t]) for t in order], cells=cells,
                note="cells are the upper triangle including the diagonal (a==b gives the token's count); mirror for the lower triangle"), indent=0))
        # notable pairs
        pairs = []
        for i, a in enumerate(keep):
            for b in keep[i + 1:]:
                pairs.append((a, b, len(pres[a] & pres[b]), J(a, b), freq[a], freq[b]))
        cuts[popname + "_top_pairs"] = [dict(a=a, b=b, both=n, jaccard=round(j, 3), n_a=fa, n_b=fb) for a, b, n, j, fa, fb in sorted(pairs, key=lambda x: -x[3])[:60]]
        cuts[popname + "_never_together"] = [dict(a=a, b=b, n_a=fa, n_b=fb) for a, b, n, j, fa, fb in sorted(pairs, key=lambda x: -(x[4] * x[5])) if n == 0][:60]
        cuts[popname + "_subset"] = [dict(small=(a if fa <= fb else b), large=(b if fa <= fb else a), n_small=min(fa, fb), n_large=max(fa, fb))
                                      for a, b, n, j, fa, fb in pairs if n == min(fa, fb) and min(fa, fb) >= 5 and fa != fb and max(fa, fb) < 0.9 * len(pop)]
    (HERE / "cluster-order.json").write_text(json.dumps(clus, indent=1))
    (HERE / "cluster-cuts.json").write_text(json.dumps(cuts, indent=1))
    print("creatures", len(allrows), "wild", len(wild), "files", len(files), "AB files", len(frows), "occurrences", len(occ_all), "bare", len(bare_all))


if __name__ == "__main__":
    main()
