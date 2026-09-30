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
            spot = kv(eco("cavespot", sp[0], 0, *sp[1:])[-1] if sp[0] in ("cavern", "cavepool")
                      else eco("vspot", *sp[1:])[-1] if sp[0] == "vermin" else eco("spot", sp[0])[-1])
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
