#!/usr/bin/env python3
"""Build the seasonal-wildlife browser companion, in two forms from one template.

  build_mock.py <out.html>          the SAMPLE page (published as an artifact): the state is embedded, in the same
                                    shape `seasonal-wildlife-web` serves as /state.json
  build_mock.py --live <out.html>   the LIVE page the tool ships (scripts/seasonal-wildlife-web.html): no data; it
                                    reads /state.json from the game and sends /cmd

Sample data: the BOATS roster snapshot inside data/bestiary/creatures.json (boats_* fields, 26 Sep 2026): the 115
species with an active flag, plus the vanilla vermin of temperate and underground biomes (families by the engine's
VERMIN.family rule, as far as the bestiary's flags allow). Food-web pairs follow the tool's habitat rule (USAGE.md
'The species model') with the size bands standing in for its prey-size test; vermin links follow
seasonal-wildlife-web's rule (HUNT's flag holders, by habitat and family). Groups, limits, jobs, ledger and the
28-day history are made up to show the layout, and the page says so.
"""
import json, math, re, sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BR = {"small": 0, "medium": 1, "large": 2}
NOW, DAY_OF_SEASON, YEAR = 2, 58, 253   # Autumn, 14 Sandstone
SMALL_MAMMAL = re.compile(r"\b(rat|mouse|squirrel|hedgehog|chipmunk|shrew|mole|vole|rabbit|hare|bat|weasel|stoat|dormouse|gerbil|hamster|lemming)\b")
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
                 climate=round(x["climate_lean"] or 0.5, 2), animal_person=x["animal_person"], why="")
        if s["active"] and not s["seasons"]:   # the one rule: an active species has a season
            s["seasons"] = [3 if s["climate"] < 0.35 else 1 if s["climate"] > 0.65 else 0]
        if not s["active"]:
            s["seasons"] = []
        s["why"] = "preset: one season" if s["active"] else "default: inactive"
        out.append(s)
    return out

def family(x):   # the engine's VERMIN.family order; the bestiary has no creature classes, so mammals go by name
    if x.get("vermin_fish"): return "fish"
    if x.get("vermin_micro") or x.get("vermin_rotter"): return "flies"
    if x.get("vermin_soil_colony"): return "colony"
    if x.get("vermin_soil"): return "soil"
    if SMALL_MAMMAL.search(x["name"]): return "mammals"
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
                        why=f"vermin {fam}: seasonal defaults"))
    return out

def hunts(p):   # HUNT.wants
    if p["role"] != "predator": return None
    if p["habitat"] == "waterbird" or p["habitat"] == "flier": return "dive"
    if p["band"] == "small" and p["habitat"] in ("land", "semiaquatic"): return "hunt"
    return None

def eats(p, q):
    if p["role"] != "predator" or q["role"] != "prey" or p is q or (p["layer"] == "cavern") != (q["layer"] == "cavern"):
        return False
    if BR[q["band"]] > BR[p["band"]]:
        return False
    ph, qh = p["habitat"], q["habitat"]
    return {"land": qh in ("land", "flier", "waterbird", "semiaquatic"),
            "flier": qh in ("land", "flier", "waterbird") and BR[q["band"]] == 0,
            "waterbird": qh == "aquatic" or (qh in ("flier", "waterbird") and BR[q["band"]] == 0),
            "semiaquatic": qh in ("aquatic", "semiaquatic", "land", "waterbird"),
            "aquatic": qh in ("aquatic", "semiaquatic", "waterbird")}.get(ph, False)

def eats_vermin(p, v):
    return bool(hunts(p)) and (p["layer"] == "cavern") == (v["layer"] == "cavern") and v["family"] in VERMIN_EATEN_BY.get(p["habitat"], ())

def state():
    d = json.load(open(ROOT / "data/bestiary/creatures.json"))
    sp = roster(d) + vermin(d)
    pairs = [[p["key"], q["key"]] for p in sp for q in sp if eats(p, q)]
    pairs += [[p["key"], v["key"], "v"] for p in sp if p["role"] == "predator" for v in sp if v["role"] == "vermin" and eats_vermin(p, v)]
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

if __name__ == "__main__":
    tpl = (Path(__file__).parent / "wildlife-companion.tpl.html").read_text()
    if sys.argv[1] == "--live":
        Path(sys.argv[2]).write_text(tpl.replace("__DATA__", "null"))
    else:
        data = json.dumps(state())
        assert "</script" not in data
        Path(sys.argv[1]).write_text(tpl.replace("__DATA__", data))
