#!/usr/bin/env python3
"""ECO: small behaviour experiments for seasonal-wildlife (design: experiments/ECO-design.md).

A block = one fort, restored from its .preverify backup, loaded on a fresh DF, then cells run in sequence in that one
load. A cell = cx-eco verbs (spawn, rel, flag, lead, ...), `watch`, a step of N ticks, `read`, then `clear` + `restore`
so nothing carries into the next cell. The fort is never saved. Every `eco ...` line the game prints is written to
data/experiments/ECO/<run>/<block>.tsv as: block, cell, rep, kind, then the line's key=value pairs.

Placeholders in a verb: {X} {Y} {Z} = the block's spot; {X+N} / {X-N} / {Y+N} / {Y-N} offsets; {ids:TOKEN} = the ids
the last spawn of TOKEN printed (for `corpse`).
Step forms: 'spawn ...' (any cx-eco verb), 'lua:<code>', 'step:<ticks>', 'read:<tag>'.

Usage: eco-run.py <block>[,<block>...] [--run <dir>] [--reps N] [--only cell,cell]
       eco-run.py list
"""
import argparse, os, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LC = ROOT / "scripts" / "cx-lifecycle.sh"
ENV = dict(os.environ, CX_RPC_TIMEOUT="180")

def sh(*args, timeout=900, check=True):
    p = subprocess.run([str(LC), *map(str, args)], capture_output=True, text=True, timeout=timeout, env=ENV, cwd=ROOT)
    out = (p.stdout + p.stderr).replace("\r", "")
    if check and p.returncode != 0:
        raise RuntimeError(f"cx-lifecycle {' '.join(map(str, args))} rc={p.returncode}: {out.strip()[-400:]}")
    return out

def eco(*args):
    out = sh("cmd", "cx-eco", *args, timeout=300)
    lines = [l for l in out.splitlines() if l.startswith("eco ")]
    for l in lines:
        if l.startswith("eco error"):
            raise RuntimeError(l)
    if "TimeoutError" in out:
        raise RuntimeError(f"cx-eco {' '.join(map(str, args))}: RPC timed out")
    return lines

def kv(line):
    return dict(t.split("=", 1) for t in line.split()[2:] if "=" in t)

# ------------------------------------------------------------------ blocks ----
PRED = ["WOLF", "COYOTE", "DINGO", "HYENA", "CHEETAH", "LION", "BEAR_GRIZZLY", "FOX"]
PREY = ["RABBIT", "GAZELLE", "DEER", "KANGAROO", "WATER_BUFFALO"]

def pair(a, na, b, nb, write, ticks=3000, extra=()):
    steps = [f"spawn {a} {na} {{X}} {{Y}} {{Z}} 3", f"spawn {b} {nb} {{X+10}} {{Y}} {{Z}} 3", *extra]
    if write:
        steps.append(f"rel {a} {b}")
    return dict(steps=steps, ticks=ticks)

def flipcell(flag_steps, a, na, b=None, nb=0, write=False, ticks=3000):
    steps = list(flag_steps) + [f"spawn {a} {na} {{X}} {{Y}} {{Z}} 3"]
    if b:
        steps.append(f"spawn {b} {nb} {{X+10}} {{Y}} {{Z}} 3")
        if write:
            steps.append(f"rel {a} {b}")
    return dict(steps=steps, ticks=ticks)

BLOCKS = {}

BLOCKS["P1"] = dict(fort="CTRL", spot="land", cells={
    f"{p}x{q}:{'w' if w else 'df'}": pair(p, 6, q, 10, w) for w in (False, True) for p in PRED for q in PREY})

BLOCKS["P2"] = dict(fort="CTRL", spot="land", cells={
    f"{a}x{b}": pair(a, 6, b, 6, False) for a, b in
    [("WOLF", "COYOTE"), ("WOLF", "DINGO"), ("LION", "HYENA"), ("CHEETAH", "HYENA"), ("BEAR_GRIZZLY", "WOLF"),
     ("WOLF", "WOLF"), ("DINGO", "HYENA"), ("COYOTE", "FOX")]})

BLOCKS["T1"] = dict(fort="CTRL", spot="land", cells={
    "LP_on_COYOTE": flipcell(["flag COYOTE LARGE_PREDATOR on"], "COYOTE", 6, "DEER", 10),
    "LP_ctl_COYOTE": flipcell([], "COYOTE", 6, "DEER", 10),
    "LP_off_WOLF": flipcell(["flag WOLF LARGE_PREDATOR off"], "WOLF", 6, "DEER", 10),
    "LP_ctl_WOLF": flipcell([], "WOLF", 6, "DEER", 10),
    "BENIGN_on_WOLF_w": flipcell(["flag WOLF BENIGN on"], "WOLF", 6, "DEER", 10, write=True),
    "BENIGN_ctl_WOLF_w": flipcell([], "WOLF", 6, "DEER", 10, write=True),
    "BENIGN_off_DEER": flipcell(["flag DEER BENIGN off"], "WOLF", 6, "DEER", 10, write=True),
    "AMBUSH_on_WOLF": flipcell(["flag WOLF AMBUSHPREDATOR on"], "WOLF", 6, "DEER", 10),
    "RAGE_DEER": flipcell(["lua:local c; for _,x in ipairs(df.global.world.raws.creatures.all) do if x.creature_id=='DEER' then c=x end end; "
                           "_G.CX_ECO.rage={}; for i,k in ipairs(c.caste) do _G.CX_ECO.rage[i]=k.misc.prone_to_rage; k.misc.prone_to_rage=1 end; print('eco lua rage=1')"],
                          "WOLF", 6, "DEER", 10, write=True),
    "FLEEQUICK_on_DEER": flipcell(["flag DEER FLEEQUICK on"], "WOLF", 6, "DEER", 10, write=True),
    "PEACE_on_WOLF_w": flipcell(["flag WOLF AT_PEACE_WITH_WILDLIFE on"], "WOLF", 6, "DEER", 10, write=True),
    "CRAZED_DEER": flipcell(["flag DEER CRAZED on"], "DEER", 6, "RABBIT", 10),
    "OPPOSED_DEER": flipcell(["flag DEER OPPOSED_TO_LIFE on"], "DEER", 6, "RABBIT", 10),
    "NATURAL_off_WOLF": flipcell(["flag WOLF NATURAL_ANIMAL off"], "WOLF", 6, "DEER", 10),
    "CURIOUS_EATER_WOLF": flipcell(["flag WOLF CURIOUS_BEAST_EATER on"], "WOLF", 6),
    "MEANDER_off_DEER": flipcell(["flag DEER MEANDERER off"], "DEER", 10),
    "MEANDER_ctl_DEER": flipcell([], "DEER", 10),
    "LOOSE_on_KANGAROO": flipcell(["flag KANGAROO LOOSE_CLUSTERS on"], "KANGAROO", 10),
    "LOOSE_ctl_KANGAROO": flipcell([], "KANGAROO", 10),
})

def lead_cell(tok, n, how, pred=None):
    steps = [f"spawn {tok} {n} {{X}} {{Y}} {{Z}} 3"]
    if pred:
        steps += [f"spawn {pred} 6 {{X+12}} {{Y}} {{Z}} 3", f"rel {pred} {tok}", "watch"]
    for _ in range(6):   # the tool re-applies its leader every pass; here every 500 ticks
        steps += [f"lead {tok} {how}", "step:500"]
    return dict(steps=steps, ticks=10, nowatch=bool(pred))

SCAV = ["BIRD_VULTURE", "HYENA", "BEAR_BLACK", "RACCOON", "WOLF", "DEER"]
BLOCKS["S"] = dict(fort="CTRL", spot="land", cells={
    **{f"S1_{t}": dict(steps=["spawn KANGAROO 6 {X} {Y} {Z} 2", "corpse {ids:KANGAROO}", "step:50",
                               "items {X} {Y} {Z} 6 before", f"spawn {t} 6 {{X+4}} {{Y}} {{Z}} 2"],
                        ticks=4000, post=["items {X} {Y} {Z} 6 after"]) for t in SCAV},
    # S2: the tool's way -- walk them to the corpses and delete what they reach
    "S2_seek_eat": dict(steps=["spawn KANGAROO 6 {X} {Y} {Z} 2", "corpse {ids:KANGAROO}", "step:50", "items {X} {Y} {Z} 6 before",
                               "spawn HYENA 6 {X+20} {Y} {Z} 2", "seek HYENA {X} {Y} {Z}", "step:300", "eat HYENA 1",
                               "seek HYENA {X} {Y} {Z}", "step:300", "eat HYENA 1", "seek HYENA {X} {Y} {Z}", "step:300",
                               "eat HYENA 1", "items {X} {Y} {Z} 6 after-eat"], ticks=10),
    "S2_seek_goal": dict(steps=["spawn KANGAROO 6 {X} {Y} {Z} 2", "corpse {ids:KANGAROO}", "step:50",
                                "spawn HYENA 6 {X+20} {Y} {Z} 2", "seek HYENA {X} {Y} {Z} SeekStation", "step:300", "eat HYENA 1",
                                "seek HYENA {X} {Y} {Z} SeekStation", "step:300", "eat HYENA 1", "items {X} {Y} {Z} 6 after-eat"], ticks=10),
    "S3_haul_refuse": dict(steps=["spawn KANGAROO 6 {X} {Y} {Z} 2", "corpse {ids:KANGAROO}", "step:50", "spawn WOLF 3 {X+3} {Y} {Z} 2",
                                  "lua:local n=0 for id,t in pairs(_G.CX_ECO.spawned) do local u=df.unit.find(id) if t=='WOLF' and u then u.status.labors.HAUL_REFUSE=true n=n+1 end end print('eco lua haul_refuse='..n)"],
                           ticks=4000, post=["items {X} {Y} {Z} 6 after",
                                             "lua:local j=0 for id,t in pairs(_G.CX_ECO.spawned) do local u=df.unit.find(id) if u and u.job.current_job then j=j+1 end end print('eco lua wolves_with_job='..j)"]),
})

BLOCKS["L1"] = dict(fort="CTRL", spot="land", cells={
    **{f"herd_{h}": lead_cell("DEER", 10, h) for h in ("none", "lowest", "largest-male")},
    **{f"pack_{h}": lead_cell("WOLF", 8, h) for h in ("none", "lowest", "largest-male")},
    **{f"herd_{h}_pred": lead_cell("DEER", 10, h, pred="WOLF") for h in ("none", "lowest", "largest-male")},
})

# L1's predator cells started the watch after the 3,000 t (kills unrecorded): the same cells, watch first, 2 reps
BLOCKS["L2"] = dict(fort="CTRL", spot="land", cells={f"herd_{h}_pred": lead_cell("DEER", 10, h, pred="WOLF")
                                                    for h in ("none", "lowest", "largest-male")})

BLOCKS["A1"] = dict(fort="CTRL", spot="land", cells={
    "wild_filter_off": dict(steps=["spawn WOLF 6 {X} {Y} {Z} 3", "spawn DEER 10 {X+10} {Y} {Z} 3", "rel WOLF DEER"], ticks=2000),
    "wild_filter_on": dict(steps=["alerts drop-wild on", "spawn WOLF 6 {X} {Y} {Z} 3", "spawn DEER 10 {X+10} {Y} {Z} 3", "rel WOLF DEER"],
                           ticks=2000, post=["alerts drop-wild off"]),
    "fort_filter_on": dict(steps=["alerts drop-wild on", "fortspot", "spawn WOLF 3 {FX+3} {FY} {FZ} 2", "relfort WOLF"],
                           ticks=1500, post=["alerts drop-wild off"]),
    "save_reload_filter_on": dict(steps=["alerts drop-wild on", "spawn WOLF 6 {X} {Y} {Z} 3", "spawn DEER 10 {X+10} {Y} {Z} 3",
                                         "rel WOLF DEER", "step:1500", "read:before-save", "save:ECOTMP", "load:ECOTMP",
                                         "alerts drop-wild on", "step:1000"], ticks=10, post=["alerts drop-wild off"]),
})

def wcells(pairs):
    cells = {}
    for pred, pm, prey, qm in pairs:
        for w in (False, True):
            st = [f"spawn {pred} 5 {{X}} {{Y}} {{Z}} 5 {pm}", f"spawn {prey} 8 {{X}} {{Y}} {{Z}} 5 {qm}"]
            if w:
                st.append(f"rel {pred} {prey}")
            cells[f"{pred}({pm})x{prey}({qm}):{'w' if w else 'df'}"] = dict(steps=st, ticks=3000)
    return cells

BLOCKS["W1L"] = dict(fort="LAKE", spot="shore", cells=wcells([
    ("FISH_LAMPREY_SEA", "water", "DEER", "land"), ("ALLIGATOR", "water", "DEER", "land"), ("ALLIGATOR", "land", "DEER", "land"),
    ("ALLIGATOR", "water", "CAPYBARA", "land"), ("ALLIGATOR", "water", "FISH_PIKE", "water"),
    ("CROCODILE_SALTWATER", "water", "WATER_BUFFALO", "land"), ("WOLF", "land", "CAPYBARA", "water"),
    ("WOLF", "land", "FISH_PIKE", "water"), ("LION", "land", "CAPYBARA", "land")]))
BLOCKS["W1O"] = dict(fort="OCEAN2", spot="shore", cells=wcells([
    ("SHARK_BLUE", "water", "HARP_SEAL", "land"), ("SHARK_BLUE", "water", "HARP_SEAL", "water"),
    ("SHARK_GREAT_WHITE", "water", "LEOPARD_SEAL", "water"), ("SHARK_TIGER", "water", "FISH_MILKFISH", "water"),
    ("BEAR_POLAR", "land", "HARP_SEAL", "land"), ("BEAR_POLAR", "land", "BIRD_PENGUIN", "water"),
    ("SHARK_BLUE", "water", "DEER", "land")]))
BLOCKS["O"] = dict(fort="OCEAN2", spot="water", cells={
    "depth_survey": dict(steps=["depth OCEAN2"], ticks=10),
    "big_fish_here": dict(steps=["spawn SHARK_WHALE 2 {X} {Y} {Z} 4 water", "spawn SHARK_BLUE 3 {X} {Y} {Z} 4 water"], ticks=3000),
})
BLOCKS["OS"] = dict(fort="OCEAN2", spot="shallow", cells={
    "big_fish_shallow": dict(steps=["spawn SHARK_WHALE 2 {X} {Y} {Z} 4 water", "spawn SHARK_BLUE 3 {X} {Y} {Z} 4 water"], ticks=3000),
})
BLOCKS["OD"] = dict(fort="OCEAN2", spot="deepwater", cells={
    "big_fish_deep": dict(steps=["spawn SHARK_WHALE 2 {X} {Y} {Z} 4 water", "spawn SHARK_BLUE 3 {X} {Y} {Z} 4 water"], ticks=3000),
})
# grizzlies left the map in P1 (10/60) and P2 (6/6) within 3,000 t; no other species did. Alone, and with the
# curious-beast flags off (they are CURIOUSBEAST_EATER+GUZZLER, a wave type of its own in the wiki's spawning text)
BLOCKS["B"] = dict(fort="CTRL", spot="land", cells={
    "bear_alone": dict(steps=["spawn BEAR_GRIZZLY 6 {X} {Y} {Z} 3"], ticks=3000),
    "bear_no_curious": dict(steps=["flag BEAR_GRIZZLY CURIOUS_BEAST_EATER off", "flag BEAR_GRIZZLY CURIOUS_BEAST_GUZZLER off",
                                   "flag BEAR_GRIZZLY CURIOUS_BEAST off", "spawn BEAR_GRIZZLY 6 {X} {Y} {Z} 3"], ticks=3000),
    "bear_black_alone": dict(steps=["spawn BEAR_BLACK 6 {X} {Y} {Z} 3"], ticks=3000),
    "raccoon_alone": dict(steps=["spawn RACCOON 6 {X} {Y} {Z} 3"], ticks=3000),
})
BLOCKS["S2"] = dict(fort="CTRL", spot="land", cells={
    "S2_walkto": dict(steps=["spawn KANGAROO 6 {X} {Y} {Z} 2", "corpse {ids:KANGAROO}", "step:50", "spawn HYENA 6 {X+20} {Y} {Z} 2",
                             "walkto HYENA {X} {Y} {Z}", "step:100", "near HYENA {X} {Y} {Z} 3", "step:200", "near HYENA {X} {Y} {Z} 3",
                             "eat HYENA 2", "items {X} {Y} {Z} 6 after-eat"], ticks=10),
    "S2_tp_eat_reload": dict(steps=["spawn KANGAROO 6 {X+40} {Y} {Z} 2", "corpse {ids:KANGAROO}", "step:50",
                                    "items {X+40} {Y} {Z} 4 before", "spawn HYENA 6 {X+20} {Y} {Z} 2", "tp HYENA {X+40} {Y} {Z}",
                                    "eat HYENA 3", "items {X+40} {Y} {Z} 4 after-eat", "save:ECOTMP", "load:ECOTMP",
                                    "items {X+40} {Y} {Z} 4 after-reload", "step:500"], ticks=10),
})
# ---------------------------------------------------------------- ECO2 (30 Sep): every layer and water type
def pairs2(spec, ticks=3000, both=True):
    """spec: (pred, pred medium, prey, prey medium[, extra steps]) -> a DF-only and a written cell, same centre r5."""
    cells = {}
    for t in spec:
        pred, pm, prey, qm = t[:4]; extra = list(t[4]) if len(t) > 4 else []
        for w in ((False, True) if both else (True,)):
            st = extra + [f"spawn {pred} 5 {{X}} {{Y}} {{Z}} 5 {pm}", f"spawn {prey} 8 {{X}} {{Y}} {{Z}} 5 {qm}"]
            if w:
                st.append(f"rel {pred} {prey}")
            tag = "".join(e.split()[0][0] for e in extra)
            cells[f"{pred}({pm})x{prey}({qm}){':' + tag if tag else ''}:{'w' if w else 'df'}"] = dict(steps=st, ticks=ticks)
    return cells

def lead2(tok, n, how, medium, pred=None, pmedium=None):
    steps = [f"spawn {tok} {n} {{X}} {{Y}} {{Z}} 4 {medium}"]
    if pred:
        steps += [f"spawn {pred} 5 {{X}} {{Y}} {{Z}} 6 {pmedium or medium}", f"rel {pred} {tok}", "watch"]
    for _ in range(6):
        steps += [f"lead {tok} {how}", "step:500"]
    return dict(steps=steps, ticks=10, nowatch=bool(pred))

def corpses2(scav, medium, prey="KANGAROO", pmed=None):
    pm = pmed or medium
    return dict(steps=[f"spawn {prey} 6 {{X}} {{Y}} {{Z}} 2 {pm}", f"corpse {{ids:{prey}}}", "step:50", "items {X} {Y} {Z} 6 before",
                       f"spawn {scav} 5 {{X+3}} {{Y}} {{Z}} 3 {medium}"], ticks=4000, post=["items {X} {Y} {Z} 6 after"])

def walkeat(scav, medium, prey, pmed=None):
    pm = pmed or medium
    return dict(steps=[f"spawn {prey} 6 {{X}} {{Y}} {{Z}} 2 {pm}", f"corpse {{ids:{prey}}}", "step:50", "items {X} {Y} {Z} 6 before",
                       f"spawn {scav} 5 {{X+8}} {{Y}} {{Z}} 2 {medium}", f"walkto {scav} {{X}} {{Y}} {{Z}}", "step:150",
                       f"near {scav} {{X}} {{Y}} {{Z}} 3", "step:250", f"near {scav} {{X}} {{Y}} {{Z}} 3", f"eat {scav} 2",
                       "items {X} {Y} {Z} 6 after-eat"], ticks=10)

BOATS_CAVES = {"1": "cavern:72:64", "2": "cavern:63:59", "3": "cavern:46:38"}
BLOCKS["HC1"] = dict(fort="BOATS", spot=BOATS_CAVES["1"], cells={
    **pairs2([("TROLL", "cave", "GORLAK", "cave"), ("TROLL", "cave", "ELK_BIRD", "cave"), ("TOAD_GIANT_CAVE", "cave", "ELK_BIRD", "cave"),
              ("TROLL", "cave", "GORLAK", "cave", ["flag TROLL BENIGN on"])]),
    **{f"lead_GORLAK_{h}": lead2("GORLAK", 10, h, "cave") for h in ("none", "lowest", "largest-male")},
    **{f"lead_GORLAK_{h}_pred": lead2("GORLAK", 10, h, "cave", pred="TROLL") for h in ("none", "lowest", "largest-male")},
    "corpses_TROLL": corpses2("TROLL", "cave", "ELK_BIRD"), "corpses_RAT_GIANT": corpses2("RAT_GIANT", "cave", "ELK_BIRD"),
    "walkeat_TROLL": walkeat("TROLL", "cave", "ELK_BIRD"),
    "rage50_GORLAK": dict(steps=["misc GORLAK prone_to_rage 50", "spawn TROLL 5 {X} {Y} {Z} 5 cave", "spawn GORLAK 8 {X} {Y} {Z} 5 cave", "rel TROLL GORLAK"], ticks=3000),
    "vermin_CAT_cave": dict(steps=["vermin {X} {Y} {Z} 12 before", "spawn CAT 4 {X} {Y} {Z} 3 cave"], ticks=4000, post=["vermin {X} {Y} {Z} 12 after"]),
    "vermin_ctl_cave": dict(steps=["vermin {X} {Y} {Z} 12 before"], ticks=4000, post=["vermin {X} {Y} {Z} 12 after"]),
})
BLOCKS["HC2"] = dict(fort="BOATS", spot=BOATS_CAVES["2"], cells={
    **pairs2([("TROGLODYTE", "cave", "ELK_BIRD", "cave"), ("VORACIOUS_CAVE_CRAWLER", "cave", "CRUNDLE", "cave")]),
    **{f"lead_TROGLODYTE_{h}": lead2("TROGLODYTE", 8, h, "cave") for h in ("none", "lowest", "largest-male")},
})
BLOCKS["HC3"] = dict(fort="BOATS", spot=BOATS_CAVES["3"], cells={
    **pairs2([("JABBERER", "cave", "REACHER", "cave"), ("BLIND_CAVE_OGRE", "cave", "RUTHERER", "cave")]),
})
BLOCKS["HCP"] = dict(fort="BOATS", spot="cavepool:63:38", cells={
    **pairs2([("CROCODILE_CAVE", "cavewater", "ELK_BIRD", "cave"), ("OLM_GIANT", "cavewater", "CRUNDLE", "cave"),
              ("POND_GRABBER", "cavewater", "GORLAK", "cave"), ("CROCODILE_CAVE", "cave", "GORLAK", "cave")]),
    "corpses_CROCODILE_CAVE_pool": corpses2("CROCODILE_CAVE", "cavewater", "ELK_BIRD", "cave"),
})
BLOCKS["HR"] = dict(fort="RIVER4", spot="shore", cells={
    **pairs2([("ALLIGATOR", "water", "DEER", "land"), ("FISH_LAMPREY_SEA", "water", "FISH_PIKE", "water"),
              ("WOLF", "land", "BEAVER", "water"), ("SHARK_BULL", "water", "FISH_PIKE", "water"),
              ("WOLF", "land", "FISH_PIKE", "water", ["flag WOLF CAN_BREATHE_WATER on", "flag WOLF CAN_SWIM_INNATE on"])]),
    **{f"lead_FISH_PIKE_{h}": lead2("FISH_PIKE", 10, h, "water") for h in ("none", "lowest", "largest-male")},
    "vermin_DUCK_river": dict(steps=["vermin {X} {Y} {Z} 12 before", "spawn BIRD_DUCK 6 {X} {Y} {Z} 3 land"], ticks=4000, post=["vermin {X} {Y} {Z} 12 after"]),
    "vermin_ctl_river": dict(steps=["vermin {X} {Y} {Z} 12 before"], ticks=4000, post=["vermin {X} {Y} {Z} 12 after"]),
})
BLOCKS["HO"] = dict(fort="OCEAN2", spot="shore", cells={
    **pairs2([("SHARK_BLUE", "water", "HARP_SEAL", "water", ["flag SHARK_BLUE BENIGN on"]), ("ORCA", "water", "HARP_SEAL", "water"),
              ("ORCA", "water", "HARP_SEAL", "water", ["flag ORCA BENIGN off"])], both=False),
    **{f"lead_FISH_MILKFISH_{h}": lead2("FISH_MILKFISH", 10, h, "water") for h in ("none", "lowest", "largest-male")},
    **{f"lead_FISH_MILKFISH_{h}_pred": lead2("FISH_MILKFISH", 10, h, "water", pred="SHARK_TIGER") for h in ("none", "lowest", "largest-male")},
    "corpses_SHARK_GREAT_WHITE": corpses2("SHARK_GREAT_WHITE", "water", "FISH_MILKFISH"),
    "walkeat_SHARK_BLUE": walkeat("SHARK_BLUE", "water", "FISH_MILKFISH"),
    "viewrange5_MILKFISH": dict(steps=["misc FISH_MILKFISH viewrange 5", "spawn SHARK_TIGER 5 {X} {Y} {Z} 5 water", "spawn FISH_MILKFISH 8 {X} {Y} {Z} 5 water", "rel SHARK_TIGER FISH_MILKFISH"], ticks=3000),
    "viewrange40_MILKFISH": dict(steps=["misc FISH_MILKFISH viewrange 40", "spawn SHARK_TIGER 5 {X} {Y} {Z} 5 water", "spawn FISH_MILKFISH 8 {X} {Y} {Z} 5 water", "rel SHARK_TIGER FISH_MILKFISH"], ticks=3000),
})
BLOCKS["HL"] = dict(fort="LAKE", spot="shore", cells={
    **{f"lead_FISH_CARP_{h}": lead2("FISH_CARP", 10, h, "water") for h in ("none", "lowest", "largest-male")},
    "vermin_DUCK_lake": dict(steps=["vermin {X} {Y} {Z} 12 before", "spawn BIRD_DUCK 6 {X} {Y} {Z} 3 land"], ticks=4000, post=["vermin {X} {Y} {Z} 12 after"]),
    "vermin_PEREGRINE_lake": dict(steps=["vermin {X} {Y} {Z} 12 before", "spawn BIRD_FALCON_PEREGRINE 4 {X} {Y} {Z} 3 land"], ticks=4000, post=["vermin {X} {Y} {Z} 12 after"]),
    "vermin_ctl_lake": dict(steps=["vermin {X} {Y} {Z} 12 before"], ticks=4000, post=["vermin {X} {Y} {Z} 12 after"]),
    "corpses_ALLIGATOR": corpses2("ALLIGATOR", "water", "FISH_CARP"),
    "walkeat_ALLIGATOR": walkeat("ALLIGATOR", "water", "FISH_CARP"),
})
def valcell(field, v, prey="DEER", pred="WOLF", n=10):
    return dict(steps=[f"misc {prey} {field} {v}", f"spawn {pred} 6 {{X}} {{Y}} {{Z}} 3", f"spawn {prey} {n} {{X+10}} {{Y}} {{Z}} 3", f"rel {pred} {prey}"], ticks=3000)
BLOCKS["TV"] = dict(fort="CTRL", spot="land", cells={
    "ctl": pair("WOLF", 6, "DEER", 10, True),
    **{f"rage{v}_DEER": valcell("prone_to_rage", v) for v in (25, 50, 100)},
    **{f"viewrange{v}_DEER": valcell("viewrange", v) for v in (5, 40)},
    "visionarc_narrow_DEER": dict(steps=["misc DEER vision_arc_min 10", "misc DEER vision_arc_max 10", "spawn WOLF 6 {X} {Y} {Z} 3", "spawn DEER 10 {X+10} {Y} {Z} 3", "rel WOLF DEER"], ticks=3000),
    "FLEEQUICK_on_DEER_r2": flipcell(["flag DEER FLEEQUICK on"], "WOLF", 6, "DEER", 10, write=True),
    "GIANT_FOX_w": pair("GIANT_FOX", 4, "DEER", 10, True),
    "GIANT_FOX_benignoff_w": dict(steps=["flag GIANT_FOX BENIGN off", "spawn GIANT_FOX 4 {X} {Y} {Z} 3", "spawn DEER 10 {X+10} {Y} {Z} 3", "rel GIANT_FOX DEER"], ticks=3000),
    "vermin_CAT_land": dict(steps=["vermin {X} {Y} {Z} 12 before", "spawn CAT 4 {X} {Y} {Z} 3"], ticks=4000, post=["vermin {X} {Y} {Z} 12 after"]),
    "vermin_PEREGRINE_land": dict(steps=["vermin {X} {Y} {Z} 12 before", "spawn BIRD_FALCON_PEREGRINE 4 {X} {Y} {Z} 3"], ticks=4000, post=["vermin {X} {Y} {Z} 12 after"]),
    "vermin_ctl_land": dict(steps=["vermin {X} {Y} {Z} 12 before"], ticks=4000, post=["vermin {X} {Y} {Z} 12 after"]),
})
BLOCKS["A2"] = dict(fort="CTRL", spot="land", cells={
    "wild_humanoid_mode": dict(steps=["alerts drop-wild on humanoid", "spawn WOLF 6 {X} {Y} {Z} 3", "spawn DEER 10 {X+10} {Y} {Z} 3", "rel WOLF DEER"], ticks=2000, post=["alerts drop-wild off"]),
    "animalperson_humanoid_mode": dict(steps=["alerts drop-wild on humanoid", "spawn WOLF_MAN 4 {X} {Y} {Z} 3", "spawn DEER 10 {X+10} {Y} {Z} 3", "rel WOLF_MAN DEER"], ticks=2000, post=["alerts drop-wild off"]),
    "entity_humanoid_mode": dict(steps=["alerts drop-wild on humanoid", "spawn GOBLIN 4 {X} {Y} {Z} 3", "spawn DEER 10 {X+10} {Y} {Z} 3", "rel GOBLIN DEER"], ticks=2000, post=["alerts drop-wild off"]),
})
RESET = ("lua:local n=0 for id,t in pairs(_G.CX_ECO.spawned) do local u=df.unit.find(id) if u and t=='RACCOON' and u.animal.leave_countdown==0 then "
         "u.animal.leave_countdown=200000; u.path.goal=df.unit_path_goal.None; u.path.path.x:resize(0); u.path.path.y:resize(0); u.path.path.z:resize(0); n=n+1 end end print('eco lua reset='..n)")
def raccoon(mode):
    steps = ["fortspot", "spawn RACCOON 4 {FX+12} {FY} {FZ} 3"]
    if mode == "flags_off":
        steps = ["flag RACCOON CURIOUS_BEAST_EATER off", "flag RACCOON CURIOUS_BEAST_ITEM off", "flag RACCOON CURIOUS_BEAST off"] + steps
    for _ in range(10):
        steps += ["step:300"] + ([RESET] if mode == "reset" else [])
    return dict(steps=steps + ["where RACCOON"], ticks=10)
BLOCKS["CB"] = dict(fort="CTRL", spot="land", cells={f"raccoon_{m}": raccoon(m) for m in ("default", "reset", "flags_off")})

def vcell(hunter, n, medium="land"):
    st = ["vermin {X} {Y} {Z} 10 before"] + ([f"spawn {hunter} {n} {{X}} {{Y}} {{Z}} 4 {medium}"] if hunter else [])
    return dict(steps=st, ticks=4000, post=["vermin {X} {Y} {Z} 10 after"])
VHUNT = {"ctl": None, "CAT": "CAT", "PEREGRINE": "BIRD_FALCON_PEREGRINE", "DUCK": "BIRD_DUCK"}
BLOCKS["VR"] = dict(fort="CTRL", spot="vermin:surface", cells={f"v_{k}": vcell(h, 4) for k, h in VHUNT.items()})
BLOCKS["VRL"] = dict(fort="LAKE", spot="vermin:surface", cells={f"v_{k}": vcell(h, 4) for k, h in VHUNT.items()})
BLOCKS["VRR"] = dict(fort="RIVER4", spot="vermin:surface", cells={f"v_{k}": vcell(h, 4) for k, h in VHUNT.items()})
BLOCKS["VRC"] = dict(fort="BOATS", spot="vermin:cavern", cells={f"v_{k}": vcell(h, 4, "cave") for k, h in {"ctl": None, "CAT": "CAT", "RAT_GIANT": "RAT_GIANT"}.items()})
def colo(steps_pre, pred="WOLF", prey="DEER", np=6, nq=10, write=True, pm="land", qm="land"):
    st = list(steps_pre) + [f"spawn {pred} {np} {{X}} {{Y}} {{Z}} 5 {pm}", f"spawn {prey} {nq} {{X}} {{Y}} {{Z}} 5 {qm}"]
    if write:
        st.append(f"rel {pred} {prey}")
    return dict(steps=st, ticks=3000)
# PK (user 30 Sep): does the 5x effective-mass gate match DF's own combat? n written wolves vs 4 prey at one spot.
BLOCKS["PK"] = dict(fort="CTRL", spot="land", cells={
    f"wolf{n}_{p}": dict(steps=[f"spawn {p} 4 {{X}} {{Y}} {{Z}} 3", f"spawn WOLF {n} {{X}} {{Y}} {{Z}} 4", f"rel WOLF {p}"], ticks=3000)
    for p in ("DEER", "ELK", "MOOSE", "WATER_BUFFALO") for n in (1, 3, 5, 7)})
# WB (user 30 Sep): do sharks take swimming waterbirds? (ducks/penguins carry SWIMS_INNATE, no water breathing)
BLOCKS["WB"] = dict(fort="OCEAN2", spot="shore", cells={
    **{f"{s}_{b}_{'w' if w else 'df'}": dict(steps=[f"spawn {b} 6 {{X}} {{Y}} {{Z}} 4 water", f"spawn {s} 4 {{X}} {{Y}} {{Z}} 5 water"] + ([f"rel {s} {b}"] if w else []), ticks=3000)
       for s in ("SHARK_TIGER",) for b in ("BIRD_DUCK", "BIRD_PENGUIN") for w in (False, True)},
})
# CAL (user 30 Sep: "run a longer calibration first"): kill rates over 30,000 ticks by pack size, prey size, and for
# solitary hunters; 6 prey, written relation, one spot per fort. Feeds the size gate and the FREQUENCY ladder.
def cal(pred, n, prey):
    # every cell waters and feeds the citizens first: 22 cells x 30k ticks is over a year in one session, and CTRL's
    # dwarves died of thirst in the first attempt (14:08-14:12, 'settlement withered'), which ended the fort
    return dict(steps=["lua:dfhack.run_command('cx-load','sustain'); print('eco sustain ok=1')",
                       f"spawn {prey} 6 {{X}} {{Y}} {{Z}} 4", f"spawn {pred} {n} {{X}} {{Y}} {{Z}} 5", f"rel {pred} {prey}"], ticks=30000)
BLOCKS["CAL"] = dict(fort="CTRL", spot="land", cells={
    **{f"wolf{n}_{p}": cal("WOLF", n, p) for p in ("DEER", "MOOSE", "WATER_BUFFALO", "ELEPHANT") for n in (3, 5, 7)},
    **{f"hyena{n}_{p}": cal("HYENA", n, p) for p in ("WATER_BUFFALO", "ELEPHANT") for n in (5, 10)},
    **{f"cougar1_{p}": cal("COUGAR", 1, p) for p in ("DEER", "ELK", "MOOSE")},
    **{f"lion1_{p}": cal("LION", 1, p) for p in ("GIRAFFE", "WATER_BUFFALO")},
    "tiger1_WATER_BUFFALO": cal("TIGER", 1, "WATER_BUFFALO"),
})
# STL (user 30 Sep): can stealth lift solitary hunting? cougar/lion vs deer (fast) and water buffalo (slow), 30k t.
# Arms: ctl; sneak = unit SNEAK skill 10 on the placed hunters (what NATURAL_SKILL:SNEAK:10 gives a new unit); nslow =
# sneak + every gait's stealth_slows 0 (sneaking costs no speed); ambush = AMBUSHPREDATOR on. Every 5,000 ticks the
# hunters are sampled for hidden_in_ambush / hidden_ambusher (do wild animals sneak at all?).
_STL_SAMPLE = ("lua:local n,h=0,0; for _,u in ipairs(df.global.world.units.active) do local c=df.creature_raw.find(u.race)"
               " if c and c.creature_id=='{P}' and not dfhack.units.isDead(u) then n=n+1; if u.flags1.hidden_in_ambush or u.flags1.hidden_ambusher then h=h+1 end end end;"
               " print(('eco hidden token={P} n=%d hidden=%d'):format(n,h))")
_STL_SNEAK = ("lua:local utils=require('utils'); local k=0; for _,u in ipairs(df.global.world.units.active) do local c=df.creature_raw.find(u.race)"
              " if c and c.creature_id=='{P}' and u.status.current_soul then utils.insert_or_update(u.status.current_soul.skills,"
              " {new=true, id=df.job_skill.SNEAK, rating=10}, 'id'); k=k+1 end end; print(('eco sneak token={P} units=%d'):format(k))")
_STL_SLOW = ("lua:for _,c in ipairs(df.global.world.raws.creatures.all) do if c.creature_id=='{P}' then for _,ca in ipairs(c.caste) do"
             " for g=0,#ca.body_info.gait_info-1 do local l=ca.body_info.gait_info[g]; for k=0,#l-1 do l[k].stealth_slows={V} end end end end end;"
             " print('eco stealthslows token={P} value={V}')")
_STL_RESTORE = ("lua:local T={[0]=50,[1]=20,[2]=10}; for _,c in ipairs(df.global.world.raws.creatures.all) do if c.creature_id=='{P}' then for _,ca in ipairs(c.caste) do"
                " for g=0,#ca.body_info.gait_info-1 do local l=ca.body_info.gait_info[g]; for k=0,#l-1 do l[k].stealth_slows=T[k] or 0 end end end end end;"
                " print('eco stealthslows token={P} restored=1')")
def stl(pred, prey, arm):
    P = pred
    st = ["lua:dfhack.run_command('cx-load','sustain'); print('eco sustain ok=1')"]
    if arm == "ambush": st.append(f"flag {P} AMBUSHPREDATOR on")
    if arm == "nslow": st.append(_STL_SLOW.replace("{P}", P).replace("{V}", "0"))
    st += [f"spawn {prey} 6 {{X}} {{Y}} {{Z}} 4", f"spawn {P} 1 {{X}} {{Y}} {{Z}} 5", f"rel {P} {prey}"]
    if arm in ("sneak", "nslow"): st.append(_STL_SNEAK.replace("{P}", P))
    st.append("watch")
    for _ in range(6):
        st += ["step:5000", _STL_SAMPLE.replace("{P}", P)]
    post = [_STL_RESTORE.replace("{P}", P)] if arm == "nslow" else []
    return dict(steps=st, ticks=10, nowatch=True, post=post)
BLOCKS["STL"] = dict(fort="CTRL", spot="land", cells={
    f"{p.lower()}_{q}_{a}": stl(p, q, a) for p in ("COUGAR", "LION") for q in ("DEER", "WATER_BUFFALO") for a in ("ctl", "sneak", "nslow", "ambush")})
# STL2 (user 30 Sep: "two kills in a row ... use skills"): STL's 2 solitary kills came in the sneak and ambush arms,
# never in ctl. Same pairs, 30k t, skills written on the placed hunter at rating 10 (what NATURAL_SKILL:<skill>:10 gives
# a new unit). Arms: ctl; norel = ctl with NO relation written (STL/CAL hunters attacked and killed natives they were never
# related to over 30k t: DF's own, or the write?); sneak (STL replicate); fight = the attack skills; all = sneak + fight +
# observer + AMBUSHPREDATOR.
_STL2_SKILLS = ("lua:local utils=require('utils'); local k=0; local S={{S}}; for _,u in ipairs(df.global.world.units.active) do"
                " local c=df.creature_raw.find(u.race) if c and c.creature_id=='{P}' and not dfhack.units.isDead(u) and u.status.current_soul then"
                " for _,s in ipairs(S) do utils.insert_or_update(u.status.current_soul.skills, {new=true, id=df.job_skill[s], rating=10}, 'id') end;"
                " k=k+1 end end; print(('eco skills token={P} units=%d set=%s'):format(k, table.concat(S,'+')))")
_STL2_ARMS = {"ctl": [], "norel": [], "sneak": ["SNEAK"],
              "fight": ["MELEE_COMBAT", "BITE", "GRASP_STRIKE", "WRESTLING", "DODGING"],
              "all": ["SNEAK", "MELEE_COMBAT", "BITE", "GRASP_STRIKE", "WRESTLING", "DODGING", "SITUATIONAL_AWARENESS"]}
def stl2(pred, prey, arm):
    P, S = pred, _STL2_ARMS[arm]
    st = ["lua:dfhack.run_command('cx-load','sustain'); print('eco sustain ok=1')"]
    if arm == "all": st.append(f"flag {P} AMBUSHPREDATOR on")
    st += [f"spawn {prey} 6 {{X}} {{Y}} {{Z}} 4", f"spawn {P} 1 {{X}} {{Y}} {{Z}} 5"] + ([] if arm == "norel" else [f"rel {P} {prey}"])
    if S: st.append(_STL2_SKILLS.replace("{P}", P).replace("{S}", ",".join(f"'{s}'" for s in S)))
    st.append("watch")
    for _ in range(6):
        st += ["step:5000", _STL_SAMPLE.replace("{P}", P)]
    return dict(steps=st, ticks=10, nowatch=True)
BLOCKS["STL2"] = dict(fort="CTRL", spot="land", cells={
    f"{p.lower()}_{q}_{a}": stl2(p, q, a) for p in ("COUGAR", "LION") for q in ("DEER", "WATER_BUFFALO") for a in _STL2_ARMS})
# LONE (user 30 Sep: "scale up the map full of prey and then a single solitary hunter and let it run ... until he dies or
# for max one season, then repeat x5"). One COUGAR among 8 prey species x 6 (r 20), relation written to each, 100,800 t
# (one season), sustain at 0 and 50k. Arms: ctl; pkg = the solitary package the user chose (unit SNEAK + fight +
# SITUATIONAL_AWARENESS 10, every gait stealth_slows 0, AMBUSHPREDATOR). Alive counts sampled every 5,040 t.
LONE_PREY = ("RABBIT", "HARE", "GROUNDHOG", "GOAT_MOUNTAIN", "KANGAROO", "DEER", "ELK", "WATER_BUFFALO")
_ALIVE = ("lua:local W={{W}}; local C={}; for _,u in ipairs(df.global.world.units.active) do if not dfhack.units.isDead(u) then"
          " local r=df.creature_raw.find(u.race); if r and W[r.creature_id] then C[r.creature_id]=(C[r.creature_id] or 0)+1 end end end;"
          " local t={}; for k in pairs(W) do t[#t+1]=k..'='..(C[k] or 0) end; table.sort(t); print('eco alive '..table.concat(t,' '))")
def lone(pred, arm):
    W = ",".join(f"{t}=1" for t in (pred,) + LONE_PREY)
    sus = "lua:dfhack.run_command('cx-load','sustain'); print('eco sustain ok=1')"
    st = [sus]
    if arm == "pkg":
        st += [f"flag {pred} AMBUSHPREDATOR on", _STL_SLOW.replace("{P}", pred).replace("{V}", "0")]
    st += [f"spawn {q} 6 {{X}} {{Y}} {{Z}} 20" for q in LONE_PREY] + [f"spawn {pred} 1 {{X}} {{Y}} {{Z}} 3"]
    st += [f"rel {pred} {q}" for q in LONE_PREY]
    if arm == "pkg":
        st.append(_STL2_SKILLS.replace("{P}", pred).replace("{S}", ",".join(f"'{s}'" for s in _STL2_ARMS["all"])))
    st += ["watch", _ALIVE.replace("{W}", W)]
    for i in range(20):
        st += ["step:5040", _ALIVE.replace("{W}", W)] + ([sus] if i == 9 else [])
    return dict(steps=st, ticks=10, nowatch=True, post=[_STL_RESTORE.replace("{P}", pred)] if arm == "pkg" else [])
BLOCKS["LONE"] = dict(fort="CTRL", spot="land", cells={f"cougar_{a}": lone("COUGAR", a) for a in ("ctl", "pkg")})
# REACH* (user 30 Sep: "Test all"): the untested reach cells. 2 reps, relation written in every cell.
_ONLAND = ("lua:local n,l=0,0; for _,u in ipairs(df.global.world.units.active) do local r=df.creature_raw.find(u.race)"
           " if r and r.creature_id=='{P}' and not dfhack.units.isDead(u) then n=n+1; local f=dfhack.maps.getTileFlags(u.pos)"
           " if f and f.flow_size==0 then l=l+1 end end end; print(('eco onland token={P} n=%d dry=%d'):format(n,l))")
def wcell(pred, pm, prey, qm, n=3, nq=6, rq=5, ticks=5000, extra=(), dry=False):
    st = list(extra) + [f"spawn {prey} {nq} {{X}} {{Y}} {{Z}} {rq} {qm}", f"spawn {pred} {n} {{X}} {{Y}} {{Z}} 4 {pm}", f"rel {pred} {prey}"]
    if not dry:
        return dict(steps=st, ticks=ticks)
    st.append("watch")
    for _ in range(ticks // 1000):
        st += ["step:1000", _ONLAND.replace("{P}", pred)]
    return dict(steps=st, ticks=10, nowatch=True)
BLOCKS["REACHW"] = dict(fort="OCEAN2", spot="shore", cells={
    "croc_beaver_swim": wcell("CROCODILE_SALTWATER", "water", "BEAVER", "water", dry=True),
    "croc_capybara_inland": wcell("CROCODILE_SALTWATER", "water", "CAPYBARA", "land", rq=15, dry=True),
    "shark_seal_swim": wcell("SHARK_TIGER", "water", "HARP_SEAL", "water"),
    "shark_seal_shore": wcell("SHARK_TIGER", "water", "HARP_SEAL", "land"),
})
BLOCKS["REACHF"] = dict(fort="CTRL", spot="land", cells={
    "kea_parrot": wcell("BIRD_KEA", "land", "BIRD_PARROT_GREY", "land", n=6, ticks=3000),
    "eagle_raven": wcell("BIRD_EAGLE", "land", "BIRD_RAVEN", "land", n=2, ticks=3000, extra=["flag BIRD_EAGLE BENIGN off"]),
    "eagle_rabbit": wcell("BIRD_EAGLE", "land", "RABBIT", "land", n=2, ticks=3000, extra=["flag BIRD_EAGLE BENIGN off"]),
    "owl_stork": wcell("BIRD_OWL_GREAT_HORNED", "land", "BIRD_STORK_WHITE", "land", n=2, ticks=3000),
})
BLOCKS["REACHC"] = dict(fort="BOATS", spot=BOATS_CAVES["1"], cells={
    "gbat_bugbat": wcell("BAT_GIANT", "cave", "BUGBAT", "cave", n=2, ticks=3000),
    "gbat_crundle": wcell("BAT_GIANT", "cave", "CRUNDLE", "cave", n=2, ticks=3000),
    "gswallow_bugbat": wcell("BIRD_SWALLOW_CAVE_GIANT", "cave", "BUGBAT", "cave", n=2, ticks=3000, extra=["flag BIRD_SWALLOW_CAVE_GIANT BENIGN off"]),
})
BLOCKS["FISH"] = dict(fort="RIVER4", spot="shore", cells={
    "wolf_swim_pike": wcell("WOLF", "land", "FISH_PIKE", "water", n=5, nq=8, ticks=3000, extra=["flag WOLF CAN_SWIM_INNATE on"]),
    "wolf_swimbreathe_pike": wcell("WOLF", "land", "FISH_PIKE", "water", n=5, nq=8, ticks=3000,
                                   extra=["flag WOLF CAN_SWIM_INNATE on", "flag WOLF CAN_BREATHE_WATER on"]),
    "wolf_ctl_pike": wcell("WOLF", "land", "FISH_PIKE", "water", n=5, nq=8, ticks=3000),
})
# VRM + RELS (user 30 Sep: vermin predation "a huge hole ... high priority", GOBBLE_VERMIN "use it"; "DF also writes some
# relations on its own ... Explore further"). Designs and Lua: data/eco-desk/v2/research/{vermin,relations}.md, lua/.
import pathlib

VRM = pathlib.Path(__file__).resolve().parents[1] / "data/eco-desk/v2/research/lua"
def inline(name, **kw):
    s = " ".join(l.strip() for l in (VRM / name).read_text().splitlines() if l.strip() and not l.strip().startswith("--"))
    for k, v in kw.items(): s = s.replace("{" + k + "}", str(v))
    return "lua:" + s
def vrm(consumer=None, gob=None, n=4):
    st = ["lua:dfhack.run_command('cx-load','sustain'); print('eco sustain ok=1')",
          inline("vermin_create.lua", RACE="ROACH_LARGE", N=40, R=6), inline("vermin_create.lua", RACE="GRASSHOPPER", N=20, R=6)]
    if gob: st.append(inline("gobble_write.lua", P=consumer, KIND=gob[0], CLS=gob[1]))
    if consumer: st.append(f"spawn {consumer} {n} {{X}} {{Y}} {{Z}} 3")
    for i in range(13):
        st += [inline("vermin_count.lua", RACE="ROACH_LARGE", R=8, TAG=f"t{i*500}"),
               inline("vermin_count.lua", RACE="GRASSHOPPER", R=8, TAG=f"t{i*500}")]
        if consumer: st.append(inline("hunger.lua", P=consumer, TAG=f"t{i*500}"))
        if i < 12: st.append("step:500")
    post = [inline("gobble_restore.lua", P=consumer)] if gob else []
    return dict(steps=st, ticks=10, nowatch=True, post=post)
BLOCKS["VRM"] = dict(fort="CTRL", spot="land", cells={
    "none": vrm(), "duck": vrm("BIRD_DUCK"), "hedgehog": vrm("HEDGEHOG"), "badger": vrm("BADGER"),
    "badger_cls": vrm("BADGER", ("class", "EDIBLE_GROUND_BUG")), "badger_cre": vrm("BADGER", ("creature", "ROACH_LARGE")),
    "cat": vrm("CAT")})

def rel(tag): return inline("rel_sample.lua", TAG=tag)      # inline() as in vermin.md
def rels(subject=None, n=1, flags=(), ticks=30000):
    st = ["lua:dfhack.run_command('cx-load','sustain'); print('eco sustain ok=1')", rel("reset")]
    st += [f"flag {subject} {f}" for f in flags]
    if subject: st.append(f"spawn {subject} {n} {{X}} {{Y}} {{Z}} 5")
    st.append("watch")
    for i in range(ticks // 3000):
        st += ["step:3000", rel(f"t{(i+1)*3000}")]
        if i % 10 == 9: st.append("lua:dfhack.run_command('cx-load','sustain'); print('eco sustain ok=1')")
    return dict(steps=st, ticks=10)        # watch kept: read gives attacks/deaths by pair
BLOCKS["RELS"] = dict(fort="CTRL", spot="land", cells={
    "nat": rels(ticks=100800), "lion": rels("LION"), "lion_benign": rels("LION", flags=("BENIGN on",)),
    "lion_nolp": rels("LION", flags=("LARGE_PREDATOR off",)), "lion_ambush": rels("LION", flags=("AMBUSHPREDATOR on",)),
    "deer": rels("DEER"), "badger": rels("BADGER", 4)})
# SLOTV (user 30 Sep: "verify on the rig then fix both paths"): what value does DF itself leave in rel_map? The tool's
# PLACE.enemySlot and ecoClearDeparted write 0 (STRANGER) across a slot's row and column; the sweep writes -1 (NONE).
# Histograms of ur: pairs among slotted units, rows of unused slots, and rows of slots DF allocated since the last read.
_SLOTV = ("lua:local c=df.global.world.enemy_status_cache; local n=#c.slot_used; _G.__slotv_prev=_G.__slotv_prev or {};"
          " local P=_G.__slotv_prev; local S={}; for _,u in ipairs(df.global.world.units.active) do local sl=u.enemy.enemy_status_slot"
          " if sl>=0 and not dfhack.units.isDead(u) then S[#S+1]=sl end end; local function h(tag,cells) local H={} for _,v in ipairs(cells) do"
          " H[v]=(H[v] or 0)+1 end; for v,k in pairs(H) do print(('eco slotv tag={T} scope=%s ur=%s n=%d'):format(tag,tostring(df.unit_reaction_type[v] or v),k)) end end;"
          " local pc={}; for i=1,#S do for j=1,#S do if i~=j then pc[#pc+1]=c.rel_map[S[i]][S[j]].ur end end end; h('pairs',pc);"
          " local uc={}; local nu=0; for i=0,n-1 do if not c.slot_used[i] and nu<20 then nu=nu+1; for j=0,n-1 do uc[#uc+1]=c.rel_map[i][j].ur end end end; h('unused',uc);"
          " local nc={}; local nn=0; for _,sl in ipairs(S) do if not P[sl] then nn=nn+1; for _,o in ipairs(S) do if o~=sl then nc[#nc+1]=c.rel_map[sl][o].ur end end end end; h('new',nc);"
          " for _,sl in ipairs(S) do P[sl]=true end; print(('eco slotv tag={T} slotted=%d unused_rows=%d new_slots=%d next=%d'):format(#S,nu,nn,c.next_slot))")
BLOCKS["SLOTV"] = dict(fort="CTRL", spot="land", cells={"probe": dict(steps=[
    "lua:_G.__slotv_prev=nil; print('eco slotv reset=1')", _SLOTV.replace("{T}", "t0"), "step:100", _SLOTV.replace("{T}", "t100"),
    "step:2900", _SLOTV.replace("{T}", "t3000"), "step:6000", _SLOTV.replace("{T}", "t9000")], ticks=10, nowatch=True)})
# VRM2 (30 Sep): VRM let placed vermin pile up across cells (vermin aren't cleared with the units: 40 roaches at the first
# cell, 225 by the last) and ran its only control first, so later cells mix time with consumer. One block per arm here:
# every block reloads CTRL fresh, so each arm starts from the same 40 roaches + 20 grasshoppers at the same session age.
for _k, _c in BLOCKS["VRM"]["cells"].items():
    BLOCKS[f"VRM2_{_k}"] = dict(fort="CTRL", spot="land", cells={_k: _c})
# VRM3 (30 Sep): VRM2's control lost 14 roaches and 18 grasshoppers in rep 1 (from t3,000) and none in rep 2, with no
# consumer placed. Same control, plus every unit within 3 tiles of a placed vermin each 500 ticks, to name the eater.
def _vrm3():
    c, out = vrm(), []
    for x in c["steps"]:
        out.append(x)
        if x.startswith("lua:") and "GRASSHOPPER" in x and "vcount" in x:
            tag = x.split("tag=")[1].split(" ")[0]
            out.append(inline("vermin_near_units.lua", R=3, TAG=tag))
    c["steps"] = out
    return c
BLOCKS["VRM3_none"] = dict(fort="CTRL", spot="land", cells={"none": _vrm3()})
# VRM3b (30 Sep): VRM3's 2 reps had no event (the eater hit 3 of 14 VRM2 reps). Same control, 6 reps, every 250 ticks,
# units within 6 tiles of any placed vermin.
def _vrm3b():
    st = ["lua:dfhack.run_command('cx-load','sustain'); print('eco sustain ok=1')",
          inline("vermin_create.lua", RACE="ROACH_LARGE", N=40, R=6), inline("vermin_create.lua", RACE="GRASSHOPPER", N=20, R=6)]
    for i in range(25):
        tag = f"t{i*250}"
        st += [inline("vermin_count.lua", RACE="ROACH_LARGE", R=8, TAG=tag), inline("vermin_count.lua", RACE="GRASSHOPPER", R=8, TAG=tag),
               inline("vermin_near_units.lua", R=6, TAG=tag)]
        if i < 24: st.append("step:250")
    return dict(steps=st, ticks=10, nowatch=True)
BLOCKS["VRM3b_none"] = dict(fort="CTRL", spot="land", cells={"none": _vrm3b()})
# DOM (30 Sep, v7.0 802a82e): domestic prey. The tool on CTRL with ecology on and livestock-as-prey off; v7.domestic on vs
# off. 3 WOLF (AL) placed and moved onto the fort animal nearest the spot; an ecology pass every 1,500 ticks, 12,000 ticks.
# On: the pass writes wolf -> each fort animal; off: none. Attacks and deaths from the watch.
def dom(on):
    st = ["lua:dfhack.run_command('cx-load','sustain'); print('eco sustain ok=1')",
          inline("dom_setup.lua", ON="true" if on else "false"), "spawn WOLF 3 {X} {Y} {Z} 3",
          inline("dom_bring.lua", IDS="{ids:WOLF}"), "watch"]
    for i in range(9):
        st.append(inline("dom_sample.lua", IDS="{ids:WOLF}", TAG=f"t{i*1500}"))
        if i < 8: st.append("step:1500")
    return dict(steps=st, ticks=10, nowatch=True)   # nowatch: the harness's own watch at the cell end reset this one's log (DOM run 1)
BLOCKS["DOM"] = dict(fort="CTRL", spot="land", cells={"off": dom(False), "on": dom(True)})
# RELP (30 Sep): STL/STL2/CAL hunters attacked natives they were never related to (STL2 norel lion killed 8 badgers).
# Does DF itself hold relations for its own arrivals? Reads enemy_status_cache.rel_map between live units with a slot:
# natives only, then with one placed LION (no rel written) at +100 and +3,000 ticks.
_RELP = ("lua:local c=df.global.world.enemy_status_cache; local L={}; for _,u in ipairs(df.global.world.units.active) do"
         " if not dfhack.units.isDead(u) and u.enemy.enemy_status_slot>=0 then local r=df.creature_raw.find(u.race);"
         " L[#L+1]={u.enemy.enemy_status_slot, r and r.creature_id or '?', dfhack.units.isCitizen(u) and 'cit' or"
         " (u.flags2.roaming_wilderness_population_source and 'wild' or 'other')} end end; local C={}; for i=1,#L do for j=1,#L do"
         " if i~=j then local ok,v=pcall(function() return c.rel_map[L[i][1]][L[j][1]].ur end); if ok and v and v>=0 then"
         " local k=L[i][2]..'('..L[i][3]..')>'..L[j][2]..'('..L[j][3]..')='..tostring(df.unit_reaction_type[v] or v); C[k]=(C[k] or 0)+1 end end end end;"
         " print(('eco relp tag={T} slotted=%d'):format(#L)); for k,v in pairs(C) do print(('eco relp tag={T} pair=%s n=%d'):format(k:gsub(' ','_'),v)) end")
BLOCKS["RELP"] = dict(fort="CTRL", spot="land", cells={"lion_norel": dict(steps=[
    _RELP.replace("{T}", "natives"), "spawn LION 1 {X} {Y} {Z} 5", "step:100", _RELP.replace("{T}", "t100"),
    "step:2900", _RELP.replace("{T}", "t3000")], ticks=10, nowatch=True)})
BLOCKS["TV2"] = dict(fort="CTRL", spot="land", cells={
    "ctl": colo([]),
    **{f"rage{v}": colo([f"misc DEER prone_to_rage {v}"]) for v in (25, 100)},
    **{f"viewrange{v}": colo([f"misc DEER viewrange {v}"]) for v in (5, 40)},
    "visionarc_narrow": colo(["misc DEER vision_arc_min 10", "misc DEER vision_arc_max 10"]),
    "fleequick": colo(["flag DEER FLEEQUICK on"]),
    "meander_off": colo(["flag DEER MEANDERER off"], write=False, np=0) if False else dict(steps=["flag DEER MEANDERER off", "spawn DEER 10 {X} {Y} {Z} 3"], ticks=3000),
    "meander_ctl": dict(steps=["spawn DEER 10 {X} {Y} {Z} 3"], ticks=3000),
    "loose_on": dict(steps=["flag KANGAROO LOOSE_CLUSTERS on", "spawn KANGAROO 10 {X} {Y} {Z} 3"], ticks=3000),
    "loose_ctl": dict(steps=["spawn KANGAROO 10 {X} {Y} {Z} 3"], ticks=3000),
    "giantfox": colo([], pred="GIANT_FOX", np=4),
    "giantfox_benignoff": colo(["flag GIANT_FOX BENIGN off"], pred="GIANT_FOX", np=4),
    "giantwolf": colo([], pred="GIANT_WOLF", np=4),
    "ambush": colo(["flag WOLF AMBUSHPREDATOR on"], write=False),
    "ambush_ctl": colo([], write=False),
})

BLOCKS["DEPTH"] = dict(fort="BOATS", spot="water", cells={"depth_survey": dict(steps=["depth BOATS"], ticks=10)})
BLOCKS["DEPTHL"] = dict(fort="LAKE", spot="water", cells={"depth_survey": dict(steps=["depth LAKE"], ticks=10)})

# ================================================================== eco-night (30 Sep): 12 new blocks + SW1-3 =====
SUSTAIN = "lua:dfhack.run_command('cx-load','sustain'); print('eco sustain ok=1')"

# RELS2 (genuine DF arrivals, not spawn): steer the raw FREQUENCY ladder toward one subject per cell (freq_steer.lua,
# the ECO-F1 pattern already used by nothing else in this file yet) so DF's own wave pick draws it; the tool is OFF,
# so a gated arrival never releases on its own -- cx-probe release surface forces the clear every sample window (the
# same roaming-flag clear a `spawn`-based cell gets automatically). rel_sample.lua as in RELS; frequencies restored.
def rels2(subject, layer="land", ticks=30000):
    st = [SUSTAIN, rel("reset"), inline("freq_steer.lua", SUBJECT=subject, LAYER=layer), "watch"]
    for i in range(ticks // 1500):
        st += ["step:1500", "lua:dfhack.run_command('cx-probe', 'release', 'surface'); print('eco release ok=1')", rel(f"t{(i + 1) * 1500}")]
        if i == 9: st.append(SUSTAIN)
    return dict(steps=st, ticks=10, post=[inline("freq_restore.lua")])   # watch kept: read gives attacks/deaths by pair, as RELS
BLOCKS["RELS2"] = dict(fort="CTRL", spot="land", cells={s.lower(): rels2(s) for s in ("COUGAR", "DEER", "ELK")})

# RELS3: are groups the TOOL releases (seasonal-wildlife enable, groups on) treated as non-wild the same way? Ecology
# OFF isolates the release/gate mechanism from the ecology writer, so any PREDATOR_OR_PREY rel_sample catches here is
# DF's own engine reacting to "non-wild" status, not an ecology-pass write. tool_off is the untouched control.
def rels3(tool_on):
    st = [SUSTAIN, rel("reset")]
    if tool_on:
        st += ["lua:dfhack.run_command('seasonal-wildlife', 'enable'); print('eco toolenable on=1')",
               "lua:dfhack.run_command('seasonal-wildlife', 'groups', 'on'); print('eco groupson ok=1')",
               "lua:dfhack.run_command('seasonal-wildlife', 'groups', 'ecology', 'off'); print('eco ecologyoff ok=1')"]
    st.append("watch")
    for i in range(20):
        st += ["step:1500", rel(f"t{(i + 1) * 1500}")]
        if i == 9: st.append(SUSTAIN)
    post = ["lua:dfhack.run_command('seasonal-wildlife', 'groups', 'ecology', 'on'); print('eco ecologyon ok=1')",
            "lua:dfhack.run_command('seasonal-wildlife', 'disable'); print('eco tooldisable ok=1')"] if tool_on else []
    return dict(steps=st, ticks=10, post=post)
BLOCKS["RELS3"] = dict(fort="CTRL", spot="land", cells={"tool_on": rels3(True), "tool_off": rels3(False)})

# VRM4: a runtime CREATURE_CLASS matched by GOBBLE_VERMIN_CLASS. class_write.lua puts CREATURE_CLASS:SWV_TEST on every
# GRASSHOPPER caste; gobble_write.lua(KIND=class) puts GOBBLE_VERMIN_CLASS:SWV_TEST on BADGER in the "gobble" arm only
# ("ctl" = the class alone, no matching gobble tag -- ordinary BADGER never gobbles this class). Placed 30 tiles off
# the block's land spot (CTRL's two pet cats eat placed vermin at the usual spot -- the eco-night task's own trap
# note); vermin_near_units.lua already names ANY unit near ROACH_LARGE/GRASSHOPPER, so no edit needed there.
def _at(name, dx, dy, **kw):
    ox = ("{X%+d}" % dx) if dx else "{X}"
    oy = ("{Y%+d}" % dy) if dy else "{Y}"
    return inline(name, X=ox, Y=oy, **kw)
def vrm4(arm):
    st = [SUSTAIN, inline("class_write.lua", P="GRASSHOPPER", CLS="SWV_TEST"),
          _at("vermin_create.lua", 30, 30, RACE="GRASSHOPPER", N=20, R=6)]
    if arm == "gobble":
        st.append(inline("gobble_write.lua", P="BADGER", KIND="class", CLS="SWV_TEST"))
    st.append("spawn BADGER 4 {X+30} {Y+30} {Z} 3")
    for i in range(13):
        tag = f"t{i * 250}"
        st += [_at("vermin_count.lua", 30, 30, RACE="GRASSHOPPER", R=8, TAG=tag), inline("vermin_near_units.lua", R=6, TAG=tag)]
        if i < 12: st.append("step:250")
    post = [inline("class_restore.lua", P="GRASSHOPPER")]
    if arm == "gobble": post.append(inline("gobble_restore.lua", P="BADGER"))
    return dict(steps=st, ticks=10, nowatch=True, post=post)
BLOCKS["VRM4"] = dict(fort="CTRL", spot="land", cells={"ctl": vrm4("ctl"), "gobble": vrm4("gobble")})

# LAKEP: lake-layer wild unit survey (lake_wild.lua: feature_idx/cave_id, WILD.layerOf, hand-computed ecoRealm) either
# side of a written predator-prey relation, plus does the write itself persist in enemy_status_cache over 3,000 ticks
# at the lake's own shore/water spot (lake_persist.lua). ONE run (no natural replicate variance to average here --
# documented exception to the two-reps default; invoke with --reps 1).
def lakep():
    st = [SUSTAIN, inline("lake_wild.lua", TAG="pre"),
          "spawn ALLIGATOR 3 {X} {Y} {Z} 5 water", "spawn FISH_CARP 8 {X} {Y} {Z} 5 water", "rel ALLIGATOR FISH_CARP", "watch"]
    for i in range(6):
        st += ["step:500", inline("lake_persist.lua", A="ALLIGATOR", B="FISH_CARP", AIDS="{ids:ALLIGATOR}", BIDS="{ids:FISH_CARP}", TAG=f"t{(i + 1) * 500}")]
    st.append(inline("lake_wild.lua", TAG="t3000"))
    return dict(steps=st, ticks=10)
BLOCKS["LAKEP"] = dict(fort="LAKE", spot="shore", cells={"survey_and_persist": lakep()})

# HC4: the HC1-3/HCP "fighting with no relation" pairs again, at the SECOND cavespot of each cavern/pool (the 4th
# colon-segment of `spot` now selects the skip index main() passes to cx-eco's cavespot verb -- see main()'s fix).
def nowrite_pair(a, na, b, nb, am="cave", bm="cave", ticks=3000):
    return dict(steps=[f"spawn {a} {na} {{X}} {{Y}} {{Z}} 5 {am}", f"spawn {b} {nb} {{X}} {{Y}} {{Z}} 5 {bm}"], ticks=ticks)
BLOCKS["HC4_1"] = dict(fort="BOATS", spot=BOATS_CAVES["1"] + ":1", cells={
    "TROLLxGORLAK_df": nowrite_pair("TROLL", 5, "GORLAK", 8), "TOAD_GIANT_CAVExELK_BIRD_df": nowrite_pair("TOAD_GIANT_CAVE", 5, "ELK_BIRD", 8)})
BLOCKS["HC4_2"] = dict(fort="BOATS", spot=BOATS_CAVES["2"] + ":1", cells={
    "TROGLODYTExELK_BIRD_df": nowrite_pair("TROGLODYTE", 5, "ELK_BIRD", 8), "CRAWLERxCRUNDLE_df": nowrite_pair("VORACIOUS_CAVE_CRAWLER", 5, "CRUNDLE", 8)})
BLOCKS["HC4_3"] = dict(fort="BOATS", spot=BOATS_CAVES["3"] + ":1", cells={
    "JABBERERxREACHER_df": nowrite_pair("JABBERER", 5, "REACHER", 8), "OGRExRUTHERER_df": nowrite_pair("BLIND_CAVE_OGRE", 5, "RUTHERER", 8)})
BLOCKS["HC4_P"] = dict(fort="BOATS", spot="cavepool:63:38:1", cells={
    "CROC_CAVExELK_BIRD_df": nowrite_pair("CROCODILE_CAVE", 5, "ELK_BIRD", 8, am="cavewater"),
    "OLM_GIANTxCRUNDLE_df": nowrite_pair("OLM_GIANT", 5, "CRUNDLE", 8, am="cavewater")})

# GPK: giant packs, written relation, 30,000 ticks (CAL's calibration pattern). All three tokens on each side verified
# present in vanilla DF raws (creature_large_tropical.txt/creature_large_riverlake.txt/creature_temperate_new.txt) --
# no substitution needed, unlike the task's own hedge. The crocodilian pair at shore on both saltwater-biome forts.
def gpk(pred, n, prey, nq, pm="land", qm="land"):
    return dict(steps=[SUSTAIN, f"spawn {prey} {nq} {{X}} {{Y}} {{Z}} 5 {qm}", f"spawn {pred} {n} {{X}} {{Y}} {{Z}} 6 {pm}", f"rel {pred} {prey}"], ticks=30000)
BLOCKS["GPK"] = dict(fort="CTRL", spot="land", cells={
    "giant_hyena_pack_x_elephant": gpk("GIANT_HYENA", 10, "ELEPHANT", 2), "giant_dingo_pack_x_rhinoceros": gpk("GIANT_DINGO", 10, "RHINOCEROS", 2)})
BLOCKS["GPKW"] = dict(fort="OCEAN2", spot="shore", cells={"giant_crocodile_saltwater_x_hippo": gpk("GIANT_CROCODILE_SALTWATER", 4, "HIPPO", 2, pm="water", qm="water")})
BLOCKS["GPKR"] = dict(fort="RIVER4", spot="shore", cells={"giant_crocodile_saltwater_x_hippo": gpk("GIANT_CROCODILE_SALTWATER", 4, "HIPPO", 2, pm="water", qm="water")})

# FSH2: CAN_SWIM_INNATE written onto two land apex predators vs FISH_PIKE, same bank as FISH; wolf_ctl_pike repeats
# FISH's own unflagged control exactly (same name) so the three can be read side by side.
BLOCKS["FSH2"] = dict(fort="RIVER4", spot="shore", cells={
    "grizzly_swim_pike": wcell("BEAR_GRIZZLY", "land", "FISH_PIKE", "water", n=3, nq=8, ticks=3000, extra=["flag BEAR_GRIZZLY CAN_SWIM_INNATE on"]),
    "tiger_swim_pike": wcell("TIGER", "land", "FISH_PIKE", "water", n=3, nq=8, ticks=3000, extra=["flag TIGER CAN_SWIM_INNATE on"]),
    "wolf_ctl_pike": wcell("WOLF", "land", "FISH_PIKE", "water", n=5, nq=8, ticks=3000),
})

# INV: add an invasive SAVAGE species via the live addNewSpecies path (inv_add.lua, opts.force=true), on CTRL -- whose
# savagery is read live, not assumed (inv_savagery.lua; V7.alignment() never reads it). YETI (vanilla [SAVAGE]
# [LARGE_PREDATOR], biomes MOUNTAIN/GLACIER/TUNDRA -- confirmed against the vanilla raws) is the chosen token: it is
# the vanilla [SAVAGE]+[LARGE_PREDATOR] creature whose biomes are the ones most certainly absent from CTRL's own
# (temperate) embark, unlike SASQUATCH's ANY_TEMPERATE_FOREST which CTRL may already have. 100,800 ticks (one season),
# 20 samples every 5,040 ticks via the existing _ALIVE reader.
def inv():
    W = "YETI=1"
    st = [SUSTAIN, inline("inv_savagery.lua", TAG="pre"), inline("inv_add.lua", TOKEN="YETI", CMIN=5, CMAX=10),
          "watch", _ALIVE.replace("{W}", W)]
    for i in range(20):
        st += ["step:5040", _ALIVE.replace("{W}", W)]
        if i == 9: st.append(SUSTAIN)
    st.append(inline("inv_savagery.lua", TAG="post"))
    return dict(steps=st, ticks=10, nowatch=True)
BLOCKS["INV"] = dict(fort="CTRL", spot="land", cells={"yeti": inv()})

# COH: schools/flocks/pods with a leader. "Cohesion on/off" is implemented, as everywhere else in this file, via the
# established cx-eco `lead` verb (largest-male vs none) -- the task's own documented substitution for a dedicated
# tool-side cohesion toggle, which exists in spirit (`seasonal-wildlife groups cohesion`) but re-applies on the
# TOOL's schedule, not a cx-eco cell's own step loop, so `lead` is the only way this harness can drive and SAMPLE it
# deterministically every 1,500 ticks. leader_dist.lua (existing) + group_spread.lua (new) sample both ends: member
# distance to the chosen leader, and the group's own bounding-box spread. No dolphin token exists anywhere in vanilla
# DF raws (grepped, zero matches) -- the pod arm uses ORCA only; this gap is in the vanilla raws, not the harness.
def coh(tok, n, medium, how, ticks=15000):
    st = [f"spawn {tok} {n} {{X}} {{Y}} {{Z}} 4 {medium}", "watch"]
    for i in range(ticks // 1500):
        st += [f"lead {tok} {how}", "step:1500", inline("leader_dist.lua", TOKEN=tok, HOW=how, TAG=f"t{(i + 1) * 1500}"),
               inline("group_spread.lua", TOKEN=tok, TAG=f"t{(i + 1) * 1500}")]
    return dict(steps=st, ticks=10, nowatch=True)
BLOCKS["COH"] = dict(fort="CTRL", spot="land", cells={f"flock_duck_{h}": coh("BIRD_DUCK", 12, "land", h) for h in ("largest-male", "none")})
BLOCKS["COHO"] = dict(fort="OCEAN2", spot="shore", cells={
    **{f"school_milkfish_{h}": coh("FISH_MILKFISH", 12, "water", h) for h in ("largest-male", "none")},
    **{f"pod_orca_{h}": coh("ORCA", 6, "water", h) for h in ("largest-male", "none")},
})
BLOCKS["COHR"] = dict(fort="RIVER4", spot="shore", cells={f"school_pike_{h}": coh("FISH_PIKE", 12, "water", h) for h in ("largest-male", "none")})

# FVA: TV2's two cells whose 2 replicates disagreed (visionarc_narrow, fleequick), plus TV2's own ctl, rerun for 2
# MORE replicates (run this block with --reps 2; TV2's original reps are untouched).
BLOCKS["FVA"] = dict(fort="CTRL", spot="land", cells={
    "ctl": colo([]),
    "visionarc_narrow": colo(["misc DEER vision_arc_min 10", "misc DEER vision_arc_max 10"]),
    "fleequick": colo(["flag DEER FLEEQUICK on"]),
})

# SCV: scavenging extensions on the S/S2/S3 "walk + delete" recipe (walkeat/corpses2, already proven working -- S2:
# "'eating remains' = walk + delete, works"). Wolf pack, jackals, a flier (BIRD_VULTURE -- vanilla has it, confirmed;
# no raven substitution needed), a water-fort corpse, and a cavern corpse. No miasma-tile-count verb exists anywhere
# in cx-eco/cx-probe, so the cavern cell reuses the same before/after items proxy as S1/corpses2 -- true miasma-tile
# detection is NOT doable with the current tooling (documented, not invented).
BLOCKS["SCV"] = dict(fort="CTRL", spot="land", cells={
    "wolfpack_kill": walkeat("WOLF", "land", "KANGAROO"),
    "jackal_kill": walkeat("JACKAL", "land", "KANGAROO"),
    "vulture_kill": walkeat("BIRD_VULTURE", "land", "KANGAROO"),
})
BLOCKS["SCVW"] = dict(fort="RIVER4", spot="shore", cells={
    "corpse_in_water_alligator": walkeat("ALLIGATOR", "water", "FISH_CARP", pmed="water"),
    "corpse_in_water_wolf_bank": walkeat("WOLF", "land", "FISH_CARP", pmed="water"),
})
BLOCKS["SCVC"] = dict(fort="BOATS", spot=BOATS_CAVES["1"], cells={"cavern_miasma_troll": corpses2("TROLL", "cave", "ELK_BIRD")})

# SW1/SW2/SW3 (coordinator, 30 Sep: threshold sweep, experiments/SWEEP-design.md). Shared SW1/SW2 arena: tool on, 5
# WOLF at the spot, DEER/WATER_BUFFALO/ELEPHANT herds 45-60 tiles off (beyond the 40-tile far_tiles default, so nudge
# is in play); sw.discoverGroups (exported, confirmed by grep: _ENV.discoverGroups at seasonal-wildlife.lua:6544)
# adopts the pack as one tracked group immediately rather than waiting on the schedule. _SW_STATUS is the manifest
# subject receipt every sample: WOLF group membership, cumulative ecology pairs/nudges, and the last pass's own
# counts -- reads g.ecology.last / g.ecology.nudges directly (loadGroups()), not a re-derived rel_map scan.
_SW_STATUS = ("lua:local sw=reqscript('seasonal-wildlife'); local g=sw.loadGroups(); local wolfgrp,wolfn=0,0;"
              " for _,grp in ipairs(g.groups) do if grp.token=='WOLF' then wolfgrp=wolfgrp+1; wolfn=wolfn+#grp.ids end end;"
              " local e=g.ecology or {}; local last=e.last or {};"
              " print(('eco swstatus tag={TAG} wolf_groups=%d wolf_members=%d total_groups=%d eco_pairs=%d eco_nudges_total=%d last_nudged=%d last_slotted=%d')"
              ":format(wolfgrp, wolfn, #g.groups, last.pairs or 0, e.nudges or 0, last.nudged or 0, last.slotted or 0))")
_SW_CFG_RESTORE = ("lua:local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig();"
                   " c.ecology.cadence=1500; c.ecology.nudge=true; c.ecology.far_tiles=40; c.ecology.far_ticks=3000; c.ecology.radius=6;"
                   " c.v7.pack_floor=0.05; c.v7.pack_sneak=0.25; sw.saveConfig(c);"
                   " dfhack.run_command('seasonal-wildlife', 'groups', 'ecology', 'on'); dfhack.run_command('seasonal-wildlife', 'disable');"
                   " print('eco swcfg restored=1')")
def sw_arena():
    return ["lua:dfhack.run_command('seasonal-wildlife', 'enable'); print('eco toolenable on=1')",
            "lua:dfhack.run_command('seasonal-wildlife', 'groups', 'on'); print('eco groupson ok=1')",
            "spawn WOLF 5 {X} {Y} {Z} 3", "spawn DEER 6 {X+50} {Y} {Z} 5", "spawn WATER_BUFFALO 6 {X-50} {Y} {Z} 5",
            "spawn ELEPHANT 4 {X} {Y+55} {Z} 5",
            "lua:local sw=reqscript('seasonal-wildlife'); local g=sw.loadGroups(); local n=sw.discoverGroups(g); sw.saveGroups(g);"
            " print(('eco swdiscover n=%d'):format(n))"]
def sw1(arm):
    st = sw_arena()
    if arm == "cad500": st.append("lua:local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig(); c.ecology.cadence=500; sw.saveConfig(c);"
                                   " dfhack.run_command('seasonal-wildlife', 'groups', 'ecology', 'on'); print('eco swcfg cadence=500 ok=1')")
    elif arm == "cad6000": st.append("lua:local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig(); c.ecology.cadence=6000; sw.saveConfig(c);"
                                      " dfhack.run_command('seasonal-wildlife', 'groups', 'ecology', 'on'); print('eco swcfg cadence=6000 ok=1')")
    elif arm == "nudge_off": st.append("lua:local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig(); c.ecology.nudge=false; sw.saveConfig(c);"
                                        " dfhack.run_command('seasonal-wildlife', 'groups', 'ecology', 'on'); print('eco swcfg nudge_bool=false ok=1')")
    elif arm == "nudge_tight": st.append("lua:dfhack.run_command('seasonal-wildlife', 'groups', 'nudge', '20', '1500', '6'); print('eco swnudge set=20,1500,6')")
    st.append("watch")
    for i in range(20):
        st += ["step:1500", _SW_STATUS.replace("{TAG}", f"t{(i + 1) * 1500}")]
        if i == 9: st.append(SUSTAIN)
    return dict(steps=st, ticks=10, nowatch=True, post=[_SW_CFG_RESTORE])
BLOCKS["SW1"] = dict(fort="CTRL", spot="land", cells={a: sw1(a) for a in ("ctl", "cad500", "cad6000", "nudge_off", "nudge_tight")})

SW2_ARMS = {"ctl": (0.05, 0.25), "floor0": (0.0, 0.25), "floor20": (0.20, 0.25), "sneak0": (0.05, 0.0), "sneak100": (0.05, 1.0)}
def sw2(arm):
    floor, sneak = SW2_ARMS[arm]
    st = sw_arena() + [f"lua:dfhack.run_command('seasonal-wildlife', 'v7', 'pack_floor', '{floor}'); print('eco swv7 key=pack_floor value={floor}')",
                       f"lua:dfhack.run_command('seasonal-wildlife', 'v7', 'pack_sneak', '{sneak}'); print('eco swv7 key=pack_sneak value={sneak}')",
                       "watch"]
    for i in range(20):
        st += ["step:1500", _SW_STATUS.replace("{TAG}", f"t{(i + 1) * 1500}")]
        if i == 9: st.append(SUSTAIN)
    return dict(steps=st, ticks=10, nowatch=True, post=[_SW_CFG_RESTORE])
BLOCKS["SW2"] = dict(fort="CTRL", spot="land", cells={a: sw2(a) for a in SW2_ARMS})

# SW3: natural arrivals (no placed subject), v7.gate_drain now fixes the surface gate stalls T8g found, so this is no
# longer confounded (coordinator's note). `limits land groups N|auto` via CLI, 50,400 ticks (half a season).
def sw3(arm):
    st = ["lua:dfhack.run_command('seasonal-wildlife', 'enable'); print('eco toolenable on=1')",
          "lua:dfhack.run_command('seasonal-wildlife', 'groups', 'on'); print('eco groupson ok=1')"]
    if arm == "auto":
        st.append("lua:dfhack.run_command('seasonal-wildlife', 'limits', 'land', 'groups', 'auto'); print('eco swlimits land=auto')")
    else:
        n = {"g1": "1", "g3": "3"}[arm]
        st.append(f"lua:dfhack.run_command('seasonal-wildlife', 'limits', 'land', 'groups', '{n}'); print('eco swlimits land={n}')")
    st.append("watch")
    for i in range(1, 11):
        st += ["step:5040", _SW_STATUS.replace("{TAG}", f"t{i * 5040}")]
        if i == 5: st.append(SUSTAIN)
    return dict(steps=st, ticks=10, nowatch=True,
                post=["lua:dfhack.run_command('seasonal-wildlife', 'limits', 'land', 'groups', 'auto'); print('eco swlimits restored=auto')",
                      "lua:dfhack.run_command('seasonal-wildlife', 'disable'); print('eco tooldisable ok=1')"])
BLOCKS["SW3"] = dict(fort="CTRL", spot="land", cells={a: sw3(a) for a in ("g1", "g3", "auto")})

def prune_autosaves(save, say):
    """DF autosaves at season changes, and an autosave of the fort hides the fort in the Continue list (ECO P2, 30 Sep:
    'save list never showed Folder: CTRL' after P1's 240k ticks). Delete the autosaves of THIS save's world only."""
    rows_ = [l.split("\t") for l in sh("ui", "saves").splitlines() if l.startswith("SAVE\t")]
    world = next((r[2] for r in rows_ if len(r) > 2 and r[1] == save), None)
    for r in rows_:
        if len(r) > 2 and r[1].startswith("autosave") and world and r[2] == world:
            sh("save-delete", r[1], check=False); say(f"  pruned {r[1]} (world {world})")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blocks")
    ap.add_argument("--run"); ap.add_argument("--reps", type=int, default=1); ap.add_argument("--only")
    a = ap.parse_args()
    if a.blocks == "list":
        for k, b in BLOCKS.items():
            print(f"{k}: {b['fort']} {len(b['cells'])} cells")
        return 0
    run = Path(a.run) if a.run else ROOT / "data/experiments/ECO" / time.strftime("%Y%m%d-%H%M%S")
    run.mkdir(parents=True, exist_ok=True)
    log = open(run / "log.txt", "a")
    def say(m):
        line = f"{time.strftime('%H:%M:%S')} {m}"; print(line, flush=True); log.write(line + "\n"); log.flush()
    only = set(a.only.split(",")) if a.only else None
    for bname in a.blocks.split(","):
        b = BLOCKS[bname]
        out = open(run / f"{bname}.tsv", "a")
        say(f"== block {bname} on {b['fort']}: {len(b['cells'])} cells x {a.reps} rep(s)")
        for rep in range(1, a.reps + 1):
            sh("title", timeout=300)
            prune_autosaves(b["fort"], say)
            sh("save-restore", f"{b['fort']}.preverify", timeout=600)
            sh("stop", timeout=120, check=False); sh("start", timeout=300)
            sh("load", b["fort"], timeout=1200)
            sh("fps", 1000, 10)
            sp = b["spot"].split(":")
            if sp[0] in ("cavern", "cavepool"):
                skip = int(sp[3]) if len(sp) > 3 else 0   # HC4: a 4th colon-segment picks the Nth match, not just the top
                spot = kv(eco("cavespot", sp[0], skip, *sp[1:3])[-1])
            elif sp[0] == "vermin":
                spot = kv(eco("vspot", *sp[1:])[-1])
            else:
                spot = kv(eco("spot", sp[0])[-1])
            X, Y, Z = int(spot["x"]), int(spot["y"]), int(spot["z"])
            say(f"  rep {rep}: spot {b['spot']} {X},{Y},{Z}")
            ids, temps = {}, []
            V = {"X": X, "Y": Y, "Z": Z, "FX": X, "FY": Y, "FZ": Z}
            def fill(s):
                s = re.sub(r"\{ids:(\w+)\}", lambda m: ids.get(m.group(1), ""), s)
                s = re.sub(r"\{(F?[XYZ])([+-]\d+)?\}", lambda m: str(V[m.group(1)] + int(m.group(2) or 0)), s)
                return s
            for cname, c in b["cells"].items():
                if only and cname not in only:
                    continue
                t0 = time.monotonic()
                try:
                    eco("clear"); eco("restore")
                    rows = []
                    for st in c["steps"]:
                        st = fill(st)
                        if st.startswith("lua:"):
                            rows += [l for l in sh("lua", st[4:], timeout=300).splitlines() if l.startswith("eco ")]
                        elif st.startswith("step:"):
                            sh("step", st[5:], timeout=900)
                        elif st.startswith("read:"):
                            rows += eco("read", st[5:])
                        elif st.startswith("save:"):
                            sh("save", st[5:], timeout=900)
                        elif st.startswith("load:"):
                            # the loaded save cannot be deleted (save-delete refuses with a map loaded), and left behind
                            # it hides the fort in DF's Continue list (ECO S2, 30 Sep): delete it at the block's end
                            sh("load", st[5:], timeout=1200); temps.append(st[5:])
                            rows.append(f"eco reload save={st[5:]} ok=1")
                        else:
                            got = eco(*st.split())
                            rows += got
                            for l in got:
                                d = kv(l)
                                if l.startswith("eco spawn") and d.get("ids"):
                                    ids[d["token"]] = d["ids"]
                                if l.startswith("eco spot") and d.get("kind") == "fort":
                                    V.update(FX=int(d["x"]), FY=int(d["y"]), FZ=int(d["z"]))
                    if not c.get("nowatch"):
                        rows += eco("watch")
                    sh("step", c["ticks"], timeout=900)
                    rows += eco("read", cname)
                    for st in c.get("post", []):
                        st = fill(st)
                        if st.startswith("lua:"):
                            rows += [l for l in sh("lua", st[4:], timeout=300).splitlines() if l.startswith("eco ")]
                        else:
                            rows += eco(*st.split())
                    eco("clear"); eco("restore")
                    for l in rows:
                        p = l.split()
                        out.write("\t".join([bname, cname, str(rep), p[1], " ".join(p[2:])]) + "\n")
                    out.flush()
                    k = [kv(l) for l in rows]
                    deaths = sum(1 for l in rows if l.startswith("eco death"))
                    att = sum(int(d.get("n", 0)) for l, d in zip(rows, k) if l.startswith("eco attacks"))
                    placed = "/".join(d["placed"] for l, d in zip(rows, k) if l.startswith("eco spawn"))
                    say(f"    {cname}: placed {placed}, attacks {att}, deaths {deaths} ({time.monotonic() - t0:.0f} s)")
                except Exception as e:
                    say(f"    !! {cname} FAILED: {e!r}"[:600])
                    out.write("\t".join([bname, cname, str(rep), "FAILED", repr(e)[:300]]) + "\n"); out.flush()
                    try:
                        eco("clear"); eco("restore")
                    except Exception:
                        say("    !! clear failed too; stopping the block")
                        break
            sh("title", timeout=300, check=False)
            for t in temps:
                say("  " + sh("save-delete", t, timeout=300, check=False).strip()[-120:])
        say(f"== block {bname} done")
    say("=== eco exit")
    return 0

if __name__ == "__main__":
    sys.exit(main())
