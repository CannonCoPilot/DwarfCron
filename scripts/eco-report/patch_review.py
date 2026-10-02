#!/usr/bin/env python3
"""Figure fixes from the user's review, Parts 1 and 2 (1 Oct 2026). Idempotent. Run after the Part 1 patch
(data/eco-review/part1/fig-diag/patch_exp.py), then build.py.

  R19   vrm2-gobble-tokens: value-first spec (fixed by patch_exp.py); arm labels shortened so they no longer clip
  11    rels-who-writes: the writer bar becomes a holder-class x target-class grid (A-mechanics s11, D s4.5), plus the
        forced-release counterfactual panel rels-grid-forced (RELS2)
  R28   raw 15a: sorted by depth (min, then max) then alphabetically, drawn min to max; new raw 15a2 = eligible species
        per layer (37 / 51 / 39 / 5 / 1), split into animals, vermin and lava-only

Inputs read: DwarfCron data/experiments/ECO/RELS*/ (the rig TSVs) and data/eco-review/part2/R28-analysis/ud.json
(the R28 raws parse, 67 species with UNDERGROUND_DEPTH)."""
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "eco-report"
MAIN = Path("/Users/nathanielcannon/Claude/Projects/DwarfCron")      # rig data and the review folders live in the main checkout
ECO = MAIN / "data/experiments/ECO"
UD = json.loads((MAIN / "data/eco-review/part2/R28-analysis/ud.json").read_text())


# ---------------------------------------------------------------- RELS grid
LAB = {"cit": "Citizens", "tame": "Livestock & pets", "other": "Placed or released", "wsurf": "Surface wild", "wcav": "Cavern wild"}
ORDER = ["cit", "tame", "other", "wsurf", "wcav"]
CAV = {x["id"] for x in UD if x["mn"] >= 1}


def cls(field):
    race, c = field.split(":")[:2]
    if c == "wild":
        return "wcav" if race in CAV else "wsurf"
    return c if c in LAB else "other"


def rels_grid(files):
    """Share of the target class's units seen that DF gave >= 1 PREDATOR_OR_PREY entry from a unit of the holder class."""
    seen, got, ent = defaultdict(set), defaultdict(set), defaultdict(int)
    for f in files:
        for ln in open(f):
            p = ln.rstrip("\n").split("\t")
            if len(p) < 5 or p[3] != "rel":
                continue
            m = re.search(r"a=(\S+) b=(\S+) ur=(\S+).* ids=(\d+)>(\d+)", p[4])
            if not m:
                continue
            a, b, ur, ia, ib = m.groups()
            ca, cb = cls(a), cls(b)
            ka, kb = (p[0], p[1], p[2], ia), (p[0], p[1], p[2], ib)
            seen[ca].add(ka)
            seen[cb].add(kb)
            if ur == "PREDATOR_OR_PREY":
                got[(ca, cb)].add(kb)
                ent[(ca, cb)] += 1
    rows = []
    for h in ORDER:
        for t in ORDER:
            n, k = len(seen[t]), len(got[(h, t)])
            rows.append({"holder": LAB[h], "target": LAB[t], "pct": round(100 * k / n) if n else 0,
                         "targets_marked": k, "targets_seen": n, "entries": ent[(h, t)]})
    return rows


def patch_experiments():
    p = DATA / "experiments.json"
    d = json.loads(p.read_text())
    F = {f["id"]: f for f in d["figures"]}

    # R19: the gobble figure (value-first, fixed upstream); shorten the two long arm labels (clipped at the 280-px margin)
    f = F["vrm2-gobble-tokens"]
    ren = {"badger + GOBBLE_VERMIN_CLASS:EDIBLE_GROUND_BUG": "badger + CLASS:EDIBLE_GROUND_BUG",
           "badger + GOBBLE_VERMIN_CREATURE:ROACH_LARGE": "badger + CREATURE:ROACH_LARGE"}
    for r in f["rows"]:
        r["arm"] = ren.get(r["arm"], r["arm"])
    if f["x"] != "arm":
        f["x"], f["y"] = "arm", "share"
    f["yLabel"] = "share of placed vermin removed"
    f["unit"] = None
    f["notes"] = ("CLASS = GOBBLE_VERMIN_CLASS, CREATURE = GOBBLE_VERMIN_CREATURE, written on the badger castes. Read a selective arm only "
                  "where grasshoppers held (grasshoppers_held): the non-selective losses are CTRL's two pet cats (units 117, 118) wandering in. "
                  "Two vermin species only: a larger representative vermin suite is a test-stage item (R20). VRM (first run) was flawed: vermin piled up across cells.")

    # Item 11: the RELS grid (A s11, D s4.5)
    A = rels_grid([ECO / "RELS-20260930-195031/RELS.tsv", ECO / "RELS2b-20261001-013012/RELS2b.tsv"])
    B = rels_grid([ECO / "RELS2-20260930-230649/RELS2.tsv"])
    ent_a = sum(r["entries"] for r in A)
    cov = {(r["holder"], r["target"]): r for r in A}
    cit = cov[("Citizens", "Surface wild")]
    base = {k: v for k, v in F["rels-who-writes"].items() if k not in ("rows", "highlight", "x", "y", "unit")}
    grid = dict(base, form="heatmap", x="target", y="holder", value="pct", valueLabel="% of the column's units marked", unit=None,
                xOrder=[LAB[k] for k in ORDER], yOrder=[LAB[k] for k in ORDER], block="RELS/RELS2b",
                title="DF points the fort, and anything a script places, at new surface arrivals, not wild at wild",
                subtitle=("Natural arrivals (RELS + RELS2b, 18 cell-reps). Row: the class of unit holding a PREDATOR_OR_PREY entry. "
                          "Column: the class of unit it points at. Cell: % of that column's units seen that got at least one entry from the row's class"),
                caption=(f"How to read it. DF itself wrote {ent_a} PREDATOR_OR_PREY entries in these runs (tool off), read from enemy_status_cache every 3,000 ticks; "
                         "hover a cell for the entry count and the units behind the percentage. 'Wild' means DF's roaming-population flag is set: "
                         "a unit a script places or the tool releases has that flag cleared and sits in the 'Placed or released' row, although DFHack's "
                         "isWildlife still calls it wildlife. The fort's side (citizens, livestock and pets, placed or released animals) marked "
                         f"92 of 103 surface arrivals seen (89%); citizens alone {cit['pct']}%, though in RELS only 81 of 138 citizens seen ever wrote one. "
                         f"Surface wild toward surface wild: {cov[('Surface wild', 'Surface wild')]['entries']} entries. In the caverns the natives "
                         f"mark each other ({cov[('Cavern wild', 'Cavern wild')]['pct']}% of cavern units). An entry is a disposition, not an attack: "
                         "no attack followed in RELS's 14 runs. Data: RELS, RELS2b (CTRL, tool off, 2 reps per cell); "
                         "scripts/eco-report/patch_review.py re-tallies the TSVs."),
                notes=("Exposure differs by cell (RELS nat ran 100,800 t, the subject cells 30,000 t) and cells shared a load in a fixed order; "
                       "the percentages have a 'units seen in any entry' denominator, not a census."),
                rows=A)
    forced = dict(grid, id="rels-grid-forced", block="RELS2",
                  title="Clear the flag on every arrival and DF pairs the arrivals with each other",
                  subtitle="Forced release (RELS2, 6 cell-reps): every arrival's roaming flag was cleared by script, so arrivals move into the 'Placed or released' class",
                  caption=(f"The counterfactual. With the flag cleared on every arrival, 'Placed or released' toward 'Placed or released' carries "
                           f"{[r for r in B if r['holder'] == 'Placed or released' and r['target'] == 'Placed or released'][0]['entries']:,} entries, "
                           "against 9 between surface wild animals in the natural runs: the roaming flag, not the species tokens, decides who DF aims. "
                           "Data: RELS2 (CTRL, tool off, 2 reps per cell)."),
                  notes="Same encoding as the grid above.", rows=B)
    F["rels-who-writes"].clear()
    F["rels-who-writes"].update(grid)
    if "rels-grid-forced" in F:
        F["rels-grid-forced"].clear()
        F["rels-grid-forced"].update(forced)
    else:
        i = d["figures"].index(F["rels-who-writes"])
        d["figures"].insert(i + 1, forced)
    p.write_text(json.dumps(d, indent=1, ensure_ascii=False))


# ---------------------------------------------------------------- R28: UNDERGROUND_DEPTH
LAYERS = [(1, "cavern 1"), (2, "cavern 2"), (3, "cavern 3"), (4, "magma sea"), (5, "underworld")]


def kind(x):
    if x["biomes"] == ["SUBTERRANEAN_LAVA"]:
        return "lava-only"
    if any(fl.startswith("VERMIN_") for fl in x["flags"]):
        return "vermin"
    return "animal"


def patch_raws():
    p = DATA / "raws.json"
    d = json.loads(p.read_text())
    F = {str(f["id"]): f for f in d["figures"]}
    f = F["15a"]
    guild = {r["id"]: r.get("guild") for r in f["rows"]}
    rows = sorted(({"id": x["id"], "depth_min": x["mn"], "depth_max": x["mx"], "kind": kind(x), "guild": guild.get(x["id"])} for x in UD),
                  key=lambda r: (r["depth_min"], r["depth_max"], r["id"]))
    elig = {d_: [r for r in rows if r["depth_min"] <= d_ <= r["depth_max"]] for d_, _ in LAYERS}
    only1 = [r["id"] for r in rows if r["depth_max"] == 1]
    f.update(rows=rows, form="range", x="id", y=None, lo="depth_min", hi="depth_max", series="kind", unit=None,
             categoryOrder=[r["id"] for r in rows], yLabel="UNDERGROUND_DEPTH, min to max", seriesOrder=["animal", "vermin", "lava-only"],
             title=(f"{len(elig[1])} species can live in cavern 1, {len(elig[2])} in cavern 2, {len(elig[3])} in cavern 3; "
                    f"{len(only1)} live only in cavern 1"),
             subtitle=("UNDERGROUND_DEPTH min to max per species, sorted by min, then max, then name. 0 = also on the surface, "
                       "1-3 = cavern layers, 4 = magma sea, 5 = underworld"),
             caption=("Raw depth = DF's layer_depth + 1, so cavern 1 is layer_depth 0. A species can be drawn for every layer its bar covers, "
                      "if its BIOME matches that layer's SUBTERRANEAN_* type (CHASM land, WATER pools, LAVA magma). "
                      + ", ".join(only1) + " are the only species confined to cavern 1 (1:1). MAGMA_CRAB is 3:5 with a lava-only biome: it is "
                      "eligible for cavern 3, the magma sea and the underworld, and was seen in CTRL's magma sea. No extinct creature carries the token. "
                      "v7.0 never read the raw (it layers DF's waves by the entry's cave); v7.1 seats a roster species only inside its raw depth and "
                      "puts lava-only species beside magma or not at all."),
             notes="Python parse of the 53.16 vanilla raws with COPY_TAGS_FROM and variations applied (data/eco-review/part2/R28-analysis/ud.py).")
    lay = []
    for d_, name in LAYERS:
        for k in ("animal", "vermin", "lava-only"):
            lay.append({"layer": name, "kind": k, "count": sum(1 for r in elig[d_] if r["kind"] == k)})
    new = {"id": "15a2", "title": f"Eligible species per layer: {', '.join(f'{n} {len(elig[d_])}' for d_, n in LAYERS)}",
           "subtitle": "Species whose UNDERGROUND_DEPTH range covers the layer, split into animals, vermin and lava-only species",
           "caption": ("Cavern 1's 29 animals: MOLE_DOG_NAKED, RAT_LARGE, BAT_GIANT, BAT_MAN, BIRD_SWALLOW_CAVE_GIANT, BLIND_CAVE_BEAR, CAVE_FISH_MAN, "
                       "CAVE_SWALLOW_MAN, CROCODILE_CAVE, DRALTHA, DRUNIAN, GIANT_EARTHWORM, HELMET_SNAKE, MOLE_GIANT, OLM_GIANT, OLM_MAN, POND_GRABBER, "
                       "RAT_GIANT, TOAD_GIANT_CAVE, TROGLODYTE, AMPHIBIAN_MAN, ANT_MAN, ELK_BIRD, GORLAK, GREMLIN, REPTILE_MAN, RODENT MAN, SERPENT_MAN, "
                       "TROLL. Lava-only species (IMP_FIRE, SNAKE_FIRE, the fire and magma men, MAGMA_CRAB) live only where magma is. "
                       "Generated demons (5:5) are not in the raws and are not counted."),
           "form": "stackedBar", "x": "layer", "y": "count", "series": "kind", "facet": None, "unit": "species", "log": False,
           "categoryOrder": [n for _, n in LAYERS], "seriesOrder": ["animal", "vermin", "lava-only"], "notes": "", "rows": lay}
    if "15a2" in F:
        F["15a2"].clear()
        F["15a2"].update(new)
    else:
        d["figures"].insert(d["figures"].index(f) + 1, new)
    p.write_text(json.dumps(d, indent=1))     # raws.json keeps its escaped non-ASCII (smaller diffs)


# ---------------------------------------------------------------- captions the reviews corrected
CAPTIONS = {
    "stl-skills": dict(
        title="STL could only see effects of 5x or more: no skill or ambush arm clearly beat the unchanged lone hunter (kills in 10 of 48 treated runs vs 2 of 16)",
        notes=("STL arms: ctl 17/0/0, sneak 112/3/0, nslow 21/1/1, ambush 29/1/0 (attacks/killed/lost over 8 cell-reps). STL2: ctl 53/4, norel 0/0, sneak 85/4, "
               "fight 315/3, all 18/1. SNEAK alone vs control: kill ratio 1.75 (CI 0.44-8.2), all of it lion kills. The hidden flag was set in 0 of 426 "
               "single-tick snapshots: that caps hidden time near 0.7%, it does not show that wild animals never sneak (A s13). Cells ran in one load "
               "in a fixed order (ctl first). All STL kills by LION; COUGAR is slower than both prey. Only the relation itself mattered (norel 0 in 8).")),
    "water-depth": dict(
        title="Fortress-map water columns are 1-2 levels deep (column depth): the lake is 91% one level and the ocean never deeper than 2",
        subtitle="Water columns by column depth (stacked water tiles at level 4/7 or more) on each embark's map",
        notes=("Column depth = stacked water tiles; a tile's own water level is 1-7 (flow_size), a different thing (R22). OCEAN2: 21,328 columns, "
               "d1 9,116, d2 12,212. Placed SHARK_WHALE x2 + SHARK_BLUE x3 all alive, wet, spread 13/43 after 3,000 t. BOATS (DEPTH block): "
               "36,650 columns, d1 14,846, d2 9,759, d3 8,564, d4 3,481. v7.0's own survey stopped after the top level, so it saw every column "
               "as one level deep; v7.1 reads every level.")),
    "orca-stranding": dict(
        title="Unled orcas the harness placed stranded: unled pods lost 1 and 2 of 6 to drowning in 15,000 ticks; led pods lost none",
        notes=("ORCA is AQUATIC + IMMOBILE_LAND + BEACH_FREQUENCY:10, so a drowned orca was out of water. Survivors all wet. The unled pods were "
               "the harness's control, not something the tool placed. n small. v7.1 leads every school and pod with a wet leader and re-checks "
               "breathing one tick after a water placement (built, untested).")),
    "apex-arrivals": dict(
        title="The apex FREQUENCY step did what it was set to (about 4.8 apex waves predicted over the six S8 runs, 6 seen); the target was too low",
        notes=("FREQUENCY is a relative weight: the ladder gave apexes 6-8% of land weight. Your ruling (R34, R9): the apex step is off the ladder; "
               "v7.1 steers apexes by placement from stock toward a presence target of 20-30% of the season on land. SW4 values are means over "
               "samples (units present), S8 values are arrivals. S8O counts AL + AW units on the surface (3, 2).")),
    "sw1-cadence-nudge": dict(
        notes=("Pooled over 4 reps: attacks ctl 174, cad500 243, cad6000 145, nudge_off 179, nudge_tight 198; placed prey killed 1, 2, 0, 3, 1. "
               "The nudge fired 0 times in all 8 control reps, so the nudge arms compared two arms in which it did nothing. Cells shared a load. "
               "Ruled anyway (R37, R38): cadence 3,000 and nudge off, built in v7.1.")),
    "sw2-floor-sneak": dict(
        title="This sweep could not test its dials: the placed pack was never a tracked group, so the floor and the sneak bonus weighed one wolf, and no arm wrote SNEAK",
        notes=("Placed prey killed over 4 reps: ctl 3, floor0 1, floor20 3, sneak0 4, sneak100 0. swdiscover n = 0 in all 40 cells; one wolf is "
               "22% of a deer, below the 25% sneak bar. The harness now adopts a placed pack as one tool group and aborts a block whose "
               "manipulation check fails. Your ruling keeps pack_sneak at 0.25 and the floor at 0.05 (R8, R40).")),
    "sw2-elephant-choice": dict(
        notes=("SW2 rep 1 floor20: ELEPHANT 4, WATER_BUFFALO 33 attacks vs ctl 52, 6 -- not repeated. The floor arms weighed one wolf (the pack "
               "was never tracked), so ctl (0.05) and floor20 (0.20) refused the same pairs. Placed units are non-wild to DF, which aims them itself (RELS).")),
    "sw7-pack-bonus": dict(
        title="The x3 pack bonus showed no effect on CTRL (land groups 3.1 / 1.6, 2.2 / 2.2, 3.3 / 2.8 at 1 / 3 / 5), but the test was weak",
        notes=("Only 7-8 of 27-29 wanted species are in CTRL's pool (sw7apply missing 20-21). Attacks 0 in all six cells; deaths 4-13 cavern natives. "
               "Your ruling (R41): keep the bonus; v7.1 fixed three defects in it (cluster read floored, a fixed seed, animal people carrying "
               "their root's cluster).")),
    "e23e-cavern-invasion": dict(
        notes=("invaders_max = 0 in all four runs. Cavern units peak 61-72 in both arms alike. DF's invasions are disabled in its code (R4, R23), "
               "so no flag or setting could raise one. Irruption is the tool's replacement (section 16).")),
    "curious-beasts-leave": dict(
        notes=("P1: BEAR_GRIZZLY 10/60 gone; no other P1 species lost any. They leave because they stole: DF zeroes leave_countdown at the theft "
               "and zeroed it again within 300 t of CB's reset (4/4 gone); clearing the flags species-wide kept them (4/4 stay). BOATS trace: a raccoon "
               "walked ~35 tiles to the wagon pile, took a rope, left. Also W1O polar bears 5/5, FSH2 grizzlies 2,1 of 3. v7.1 (R30): after the theft "
               "the tool clears that one unit's curious flags and resets its countdown (built, untested).")),
    "sw5-cavern-cap": dict(
        notes=("Per cavern layer ~8 under auto, ~4-7 capped; v7.0 left DF's native populations (4-5 groups per layer) outside the cap. Cap 1 = cap 2. "
               "Your ruling (R44): the tool gates every cavern layer at a fixed 5 groups, natives counted; built in v7.1.")),
    "size-gate-model": dict(
        subtitle="Hunters a kill needs under the builder's 5x mass gate, per predator x prey pair; log scale",
        notes=("needed = 1 if mass ratio <= 5 else ceil((ratio/5)^(4/3)). Builder counts floor((cmin+cmax)/2). Not a rig experiment. On the rig, "
               "pack size predicted kills (OR 3.8 per doubling) and the pack/prey mass ratio did not (OR 0.96); A-mechanics s3.")),
}


def patch_captions():
    p = DATA / "experiments.json"
    d = json.loads(p.read_text())
    F = {f["id"]: f for f in d["figures"]}
    for fid, kv in CAPTIONS.items():
        F[fid].update(kv)
    p.write_text(json.dumps(d, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    patch_experiments()
    patch_raws()
    patch_captions()
    print("patched experiments.json (vrm2, RELS grid + forced panel) and raws.json (15a sorted, 15a2 per layer)")
