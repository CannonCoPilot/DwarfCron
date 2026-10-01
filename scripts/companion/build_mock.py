#!/usr/bin/env python3
"""Build the seasonal-wildlife browser companion, in two forms from one template.

  build_mock.py <out.html> [--sprites sprites.json]
                                    the SAMPLE page (published as an artifact): the state is embedded, in the same
                                    shape `seasonal-wildlife-web` serves as /state.json
  build_mock.py --live <out.html>   the LIVE page the tool ships (scripts/seasonal-wildlife-web.html): no data; it
                                    reads /state.json from the game and sends /cmd

Sample data: the BOATS roster snapshot inside data/bestiary/creatures.json (boats_* fields, 26 Sep 2026): the 115
species with an active flag, plus the vanilla vermin of temperate and underground biomes (families by the engine's
VERMIN.family rule). Food-web pairs follow the engine's eats() -- the roster's pairing test that seasonal-wildlife-web
serves as `pairs`: habitat reach, shared water body, one realm, no peer of half its mass, and the pack's take (mass x
group^0.75, x1.5 for LARGE_PREDATOR/AMBUSHPREDATOR) against the prey's need (mass x 0.6 alone, 0.9 in a group); masses
and groups as the tool reads them (bestiary rev 2: tens of cm3, animal people at their root's). Vermin links follow
seasonal-wildlife-web's rule (HUNT's flag holders, by habitat and family). Guild, scavenger and gobble classes are the
v6.9/v7.0 readings (MODEL.guild, SCAV.is, VERMIN.GOBBLE_RULES without the snake rule) -- the web server does not send
them yet (web 1), so the live page shows them only once it does. Groups, limits, jobs, ledger and the 28-day history
are made up to show the layout, and the page says so.

rev 2 (1 Oct 2026): the published sample is built WITHOUT --sprites (the sprite build embeds the user's DF art and is
for the scratchpad only); ASCII glyphs come from the raws' CREATURE_TILE and COLOR instead.
"""
import json, math, re, sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BR = {"small": 0, "medium": 1, "large": 2}
NOW, DAY_OF_SEASON, YEAR = 2, 58, 253   # Autumn, 14 Sandstone
VERMIN_EATEN_BY = {"waterbird": {"fish", "fliers", "crawlers"}, "flier": {"fliers", "mammals", "crawlers"},
                   "land": {"mammals", "crawlers", "soil", "fliers"}, "semiaquatic": {"mammals", "crawlers", "fish"}}

def roster(d):
    out = []
    for x in d:
        if not x.get("boats_layers") or x.get("boats_active") is None:
            continue
        lay = x["boats_layers"]
        layer = "cavern" if "cavern" in lay else ("water" if lay == ["water"] else "land")
        s: dict[str, Any] = dict(key=(layer + ":" if layer != "land" else "") + x["id"], token=x["id"], name=x["name"], layer=layer,
                 habitat=x["habitat"], role=x["role"], band=x["band"], active=bool(x["boats_active"]),
                 seasons=sorted({int(c) for c in (x["boats_seasons"] or "")}), stock=int(x["boats_stock"] or 0),
                 freq=int(x["frequency"] or 50), gmin=x["cluster_min"] or 1, gmax=x["cluster_max"] or 1,
                 climate=round(x["climate_lean"] or 0.5, 2), animal_person=x["animal_person"], why="", diet=diet(x),
                 guild=x["guild"], scav=x["scavenger"] == "yes", gobble=gobble(x), ascii=ascii_of(x))
        s["_m"] = model(x)
        if s["active"] and not s["seasons"]:   # the one rule: an active species has a season
            s["seasons"] = [3 if s["climate"] < 0.35 else 1 if s["climate"] > 0.65 else 0]
        if not s["active"]:
            s["seasons"] = []
        s["why"] = "preset: one season" if s["active"] else "default: inactive"
        out.append(s)
    return out

def model(x):   # the engine's pool-entry fields eats() reads
    bodies = set()
    for b in x.get("biomes", []):
        if b.startswith("OCEAN"): bodies.add("ocean")
        elif b == "SUBTERRANEAN_WATER": bodies.add("cavern")
        elif b.split("_")[0] in ("LAKE", "RIVER", "POOL"): bodies.add(b.split("_")[0].lower())
    return dict(mass=x["tool_mass"], group=x.get("group") or 1, big=x["large_predator"] or x["ambushpredator"],
                aquatic=x["habitat"] in ("aquatic", "semiaquatic"), bodies=bodies)

GOBBLE_RULES = [   # VERMIN.GOBBLE_RULES (v7.0.0); the snake rule needs gait names, which the bestiary does not read
    (lambda x: x["guild"] in ("ML", "PL", "SH") and x["tool_mass"] < 10000 and (x["carnivore"] or not x["grazer"]), ["ground bugs", "soil life"]),
    (lambda x: x["guild"] in ("WB", "FF", "FC"), ["small fish"]),
    (lambda x: x["guild"] == "RP", ["small birds", "small mammals"]),
    (lambda x: x["guild"] == "LB", ["flying insects"]),
]
def gobble(x):
    out = []
    for rule, cls in GOBBLE_RULES:
        if rule(x): out += [c for c in cls if c not in out]
    return out

def ascii_of(x):   # CREATURE_TILE and COLOR from the raws, the shape the live snapshot sends (ch, fg, bg, br)
    if x.get("tile_code") is None: return None
    fg, bg, br = x.get("color") or [7, 0, 0]
    return {"ch": x["tile_code"], "fg": fg, "bg": bg, "br": br}

def diet(x):   # the caste flags scavenging suggestions read (the live snapshot reads the same from the raws in memory)
    return {"carnivore": bool(x.get("carnivore")), "bonecarn": bool(x.get("bonecarn")), "grazer": bool(x.get("grazer"))}

def family(x):   # the engine's VERMIN.family order (rev 2: MAMMAL from the creature classes, not the name)
    if x.get("vermin_fish"): return "fish"
    if x.get("vermin_micro") or x.get("vermin_rotter"): return "flies"
    if x.get("vermin_soil_colony"): return "colony"
    if x.get("vermin_soil"): return "soil"
    if "MAMMAL" in (x.get("classes") or []): return "mammals"
    if x.get("flier"): return "fliers"
    return "crawlers"

def vermin(d):
    out = []
    for x in d:
        if not x.get("vermin") or x["source"] != "vanilla" or x.get("animal_person"):
            continue
        bs = x["biomes"]
        under = [b for b in bs if b.startswith("SUBTERRANEAN")]
        temperate = [b for b in bs if "TEMPERATE" in b or b.startswith("ANY_")]
        if not (temperate or under):
            continue
        fam = family(x)
        layer = "cavern" if under and not temperate else ("water" if fam == "fish" and not any(b.startswith("OCEAN") for b in temperate) else "land")
        seasons = [0, 1, 2, 3] if (layer != "land" or fam in ("mammals", "fish")) else [0, 1, 2]
        out.append(dict(key=(layer + ":" if layer != "land" else "") + x["id"], token=x["id"], name=x["name"],
                        layer=layer, habitat=x["habitat"] or "land", role="vermin", band="small", active=True, seasons=seasons,
                        stock=int(x.get("pop_max") or 200), freq=0, gmin=1, gmax=1, family=fam, animal_person=False,
                        why=f"vermin {fam}: seasonal defaults", diet=diet(x), swv=x["swv"], ascii=ascii_of(x)))
    return out

def hunts(p):   # HUNT.wants
    if p["role"] != "predator": return None
    if p["habitat"] == "waterbird" or p["habitat"] == "flier": return "dive"
    if p["band"] == "small" and p["habitat"] in ("land", "semiaquatic"): return "hunt"
    return None

REACH = {"land": {"land", "flier", "waterbird", "semiaquatic"}, "flier": {"land", "flier", "waterbird", "semiaquatic"},
         "waterbird": {"land", "flier", "waterbird", "semiaquatic", "aquatic"}, "semiaquatic": {"land", "waterbird", "semiaquatic", "aquatic"},
         "aquatic": {"waterbird", "semiaquatic", "aquatic"}}   # MODEL.REACH
def eats(p, q):   # the engine's eats() (seasonal-wildlife.lua v7.0, line ~1940)
    if p["role"] != "predator" or q["role"] == "vermin" or p is q or (p["layer"] == "cavern") != (q["layer"] == "cavern"):
        return False
    a, b = p["_m"], q["_m"]
    if a["mass"] <= 0 or b["mass"] <= 0 or q["habitat"] not in REACH.get(p["habitat"], REACH["land"]):
        return False
    if a["aquatic"] and b["aquatic"] and a["bodies"] and b["bodies"] and not (a["bodies"] & b["bodies"]):
        return False
    if q["role"] == "predator" and b["mass"] >= a["mass"] * 0.5:
        return False
    take = a["mass"] * a["group"] ** 0.75 * (1.5 if a["big"] else 1.0)
    need = b["mass"] * (0.9 if b["group"] > 1 else 0.6)
    return take >= need

def eats_vermin(p, v):
    return bool(hunts(p)) and (p["layer"] == "cavern") == (v["layer"] == "cavern") and v["family"] in VERMIN_EATEN_BY.get(p["habitat"], ())

def state():
    d = json.load(open(ROOT / "data/bestiary/creatures.json"))
    sp = roster(d) + vermin(d)
    pairs = [[p["key"], q["key"]] for p in sp for q in sp if eats(p, q)]
    pairs += [[p["key"], v["key"], "v"] for p in sp if p["role"] == "predator" for v in sp if v["role"] == "vermin" and eats_vermin(p, v)]
    for s in sp: s.pop("_m", None)
    live = [
        {"key": "cavern:CRUNDLE", "n": 17, "origin": "DF wave", "leaves": 6.5, "tracked": True},
        {"key": "cavern:ELK_BIRD", "n": 7, "origin": "DF wave", "leaves": 3.2, "tracked": True},
        {"key": "cavern:FLESH_BALL", "n": 3, "origin": "DF wave", "leaves": 9.0, "tracked": True},
        {"key": "FISH_MILKFISH", "n": 6, "origin": "DF wave", "leaves": 4.4, "tracked": True},
        {"key": "SHARK_MAKO_LONGFIN", "n": 1, "origin": "DF wave", "leaves": 2.1, "tracked": True},
        {"key": "GIANT_EAGLE", "n": 1, "origin": "DF wave", "leaves": 7.8, "tracked": True},
        {"key": "BIRD_OSPREY", "n": 1, "origin": "untracked", "tracked": False},
    ]
    by = {s["key"]: s for s in sp}
    for g in live:
        by[g["key"]]["on_map"] = g["n"]
    limits = {"land": {"groups": 4, "ceiling": 60, "wild": 38, "groups_now": 3, "pattern": "steady", "on": True, "gate_days": 1.8},
              "water": {"groups": 2, "ceiling": 40, "wild": 0, "groups_now": 0, "pattern": "steady", "on": True},
              "cavern": {"groups": 3, "ceiling": 80, "wild": 41, "groups_now": 3, "pattern": "burst", "on": True}}
    abs_day = YEAR * 336 + NOW * 84 + DAY_OF_SEASON
    land, cav, series = 30, 22, []
    for i in range(29):
        land = max(8, min(58, land + round(math.sin(i * 0.9) * 5 + (9 if i % 7 == 3 else -2))))
        cav = max(10, min(70, cav + round(math.cos(i * 0.6) * 4 + (14 if i % 9 == 5 else -1))))
        series.append({"t": abs_day - 28 + i, "land": land, "water": max(0, 6 - i), "cavern": cav})
    series[-1].update(land=38, cavern=41)
    ledger = [("Au 14 09:12", "groups", "GIANT_EAGLE held 3 more days (you)"),
              ("Au 13 22:40", "arrive", "SHARK_MAKO_LONGFIN x1 arrived at the east sea edge; stock 421 -> 420"),
              ("Au 12 06:05", "arrive", "FISH_MILKFISH x6 arrived (school); stock 7436 -> 7430"),
              ("Au 11 17:31", "arrive", "cavern:CRUNDLE x17 arrived in cavern 1 (herd)"),
              ("Au 10 03:14", "depart", "GIANT_PARAKEET x5 left; stock 340 -> 345 (given back)"),
              ("Au 08 12:00", "ecology", "24 predator-prey pairs written, 0 waiting"),
              ("Au 01 00:00", "season", "Autumn roster took effect: 23 species in season, 34 held out of season"),
              ("Au 01 00:00", "season", "water layer: no active water species in Autumn"),
              ("Su 71 15:20", "edit", "cavern:ELK_BIRD odds 50 -> 80 (you)"),
              ("Su 66 08:47", "edit", "GIANT_COUGAR stock 40 -> 16 (you)")]
    return {"tool": "seasonal-wildlife", "web": 1, "loaded": True, "fort": "Boatsbowed",
            "date": {"year": YEAR, "season": NOW, "season_name": "Autumn", "day_of_season": DAY_OF_SEASON, "days_to_next": 84 - DAY_OF_SEASON,
                     "day_of_month": 14, "month": "Sandstone", "abs_day": abs_day},
            "enabled": True, "hunting": False, "fuse": "fuse: intact -- no job has been cancelled", "budget": 50, "undo_depth": 7,
            "limits": limits, "wild": {"land": 38, "water": 0, "cavern": 41, "deep": 0}, "species": sp, "pairs": pairs, "live": live,
            "jobs": [{"name": n, "last": a, "worst": b, "runs": 400, "over": 0} for n, a, b in
                     (("cavern", 18, 44), ("ecology", 9, 71), ("groups", 12, 149), ("hold", 2, 6), ("water", 3, 66))],
            "ledger": [{"t": t, "k": k, "l": "", "s": s} for t, k, s in ledger], "series": series, "ms": 0}

def with_sprites(st, path):
    """Merge build_sprites.py's output: gfx pages, font and palette at the top; gfx/ascii per species."""
    g = json.load(open(path))
    st["gfx"] = {"pages": g["pages"], "font": g["font"], "palette": g["palette"]}
    for s in st["species"]:
        s.update(g["tiles"].get(s["token"], {}))
    return st

if __name__ == "__main__":
    tpl = (Path(__file__).parent / "wildlife-companion.tpl.html").read_text()
    if sys.argv[1] == "--tokens":   # the creature tokens the sample uses, for build_sprites.py
        json.dump(sorted({x["token"] for x in state()["species"]}), open(sys.argv[2], "w")); sys.exit(0)
    if sys.argv[1] == "--live":
        Path(sys.argv[2]).write_text(tpl.replace("__DATA__", "null"))
    else:
        st = state()
        if len(sys.argv) > 3 and sys.argv[2] == "--sprites":
            st = with_sprites(st, sys.argv[3])
        data = json.dumps(st)
        assert "</script" not in data
        Path(sys.argv[1]).write_text(tpl.replace("__DATA__", data))
