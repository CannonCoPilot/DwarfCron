#!/usr/bin/env python3
"""ECO: small behaviour experiments for seasonal-wildlife (design: experiments/ECO-design.md; v7.1 harness:
experiments/HARNESS-v71.md).

A block = one fort and a set of cells (arms). v7.1 defaults (user rulings R12, R15; Part 1 plan H1-H6):
  * n = 5 replicates per arm (--reps), short reps (--tick-scale shrinks every step and cell length);
  * a FRESH load per arm (--load arm): the fort is restored from its .preverify backup and loaded on a fresh DF for
    every cell of every rep, so nothing carries from cell to cell (SW1R's cell-position confound);
  * the cell order counterbalanced across reps (--order counterbalance: even reps reversed; rotate = Latin rows);
  * every cell starts by WIPING every animal on the map (cx-eco wipe, receipt by origin, then wipecheck == 0) before
    it places its groups (R15); a block that observes natives opts out with wipe=False and a reason;
  * a MANIPULATION CHECK: every receipt that proves a dial reached its subject is checked as the cell runs (a spawn
    that placed 0, a relation written to no pair, a pack the tool did not adopt, a cfg value that did not change,
    any explicit 'check:' step). The first failure aborts the block (--manip abort) and is printed first;
  * placed units keep DF's roaming flag (--isolate roam), so DF does not aim them as fort-side units (H4), and are
    placed the way the tool's PLACE.one places (NONE enemy-status row, own entry, debited); --placement legacy
    reproduces the pre-v7.1 rig exactly (STRANGER row, first entry, no debit).
A cell = cx-eco verbs (spawn, rel, flag, lead, adopt ...), `watch`, a step of N ticks, `read`, then `clear` + `restore`.
The fort is never saved. Every `eco ...` line the game prints is written to data/experiments/ECO/RUN/BLOCK.tsv as:
block, cell, rep, kind, then the line's key=value pairs.

Placeholders in a verb: {X} {Y} {Z} = the block's spot; {X+N} / {X-N} / {Y+N} / {Y-N} offsets; {ids:TOKEN} = the ids
the last spawn of TOKEN printed (for `corpse`).
Step forms: 'spawn ...' (any cx-eco verb), 'lua:CODE', 'step:TICKS', 'read:TAG', 'check:KIND[k=v].KEY OP VALUE'.

Usage: eco-run.py BLOCK[,BLOCK...] [--run DIR] [--reps 5] [--only cell,cell] [--load arm|rep]
                  [--order counterbalance|rotate|fixed] [--no-wipe] [--manip abort|skip] [--isolate roam|none]
                  [--placement tool|legacy] [--tick-scale F] [--dry-run]
       eco-run.py list
       eco-run.py plan BLOCK[,BLOCK...] [--reps 5] [--load arm|rep] [--tick-scale F]   # wall-time estimate, no rig
"""
import argparse, os, re, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ecolib  # noqa: E402
from ecolib import ManipFail  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LC = ROOT / "scripts" / "cx-lifecycle.sh"
ENV = dict(os.environ, CX_RPC_TIMEOUT="180")

DRY = []   # --dry-run: every rig call is recorded here and answered with a canned receipt; nothing touches DF

def _dry_eco(args):
    v = args[0] if args else ""
    if v in ("spot", "cavespot", "vspot", "fortspot"):
        return [f"eco spot kind={'fort' if v == 'fortspot' else 'dry'} x=100 y=100 z=50"]
    if v == "spawn":
        n = int(args[2]) if len(args) > 2 and str(args[2]).isdigit() else 1
        return [f"eco spawn token={args[1]} asked={n} placed={n} ids=" + ",".join(str(9000 + i) for i in range(n))]
    if v == "wipe":
        return ["eco wipe marked=0 drawn=0 placed=0 released=0 livestock=0"]
    if v == "wipecheck":
        return ["eco wipecheck remaining=0 pending=0"]
    if v in ("rel", "relfort"):
        return [f"eco {v} a={args[1] if len(args) > 1 else '?'} pairs=1"]
    if v == "adopt":
        return [f"eco adopt token={t} asked=1 groups=1 members=1 adopted=1 roam=1" for t in args[1:]]
    if v == "lead":
        return [f"eco lead token={args[1]} how={args[2] if len(args) > 2 else 'lowest'} leader=1 members=1"]
    if v == "cfg":
        return [f"eco cfg path={x} value=dry" for x in args[1:]]
    return []

def sh(*args, timeout=900, check=True):
    if DRY:
        DRY.append(" ".join(map(str, args))[:200])
        return ""
    p = subprocess.run([str(LC), *map(str, args)], capture_output=True, text=True, timeout=timeout, env=ENV, cwd=ROOT)
    out = (p.stdout + p.stderr).replace("\r", "")
    if check and p.returncode != 0:
        raise RuntimeError(f"cx-lifecycle {' '.join(map(str, args))} rc={p.returncode}: {out.strip()[-400:]}")
    return out

def eco(*args):
    if DRY:
        DRY.append("cmd cx-eco " + " ".join(map(str, args))[:200])
        return _dry_eco([str(a) for a in args])
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

# RELS2b (30 Sep night): RELS2 forced the surface gate open with `cx-probe release`, which clears every arrival's roaming
# flag -- so every arrival was 'other' (non-wild) to DF and was aimed at the next, and the deer and elk never arrived.
# The clean version: tool off, NO forced release (DF's own gate), FREQUENCY steered to the subject, arrivals stay wild.
# Subjects: COUGAR (arrived in RELS2) and KANGAROO (a grazer that arrives on CTRL; deer never did). 51,000 ticks.
def rels2b(subject, ticks=51000):
    st = [SUSTAIN, rel("reset"), inline("freq_steer.lua", SUBJECT=subject, LAYER="land"), "watch"]
    for i in range(ticks // 1500):
        st += ["step:1500", rel(f"t{(i + 1) * 1500}")]
        if i % 10 == 9: st.append(SUSTAIN)
    return dict(steps=st, ticks=10, nowatch=True, post=[inline("freq_restore.lua")])
BLOCKS["RELS2b"] = dict(fort="CTRL", spot="land", cells={s.lower(): rels2b(s) for s in ("COUGAR", "KANGAROO")})

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
def inv(token="YETI"):
    W = f"{token}=1"
    st = [SUSTAIN, inline("inv_savagery.lua", TAG="pre"), inline("inv_add.lua", TOKEN=token, CMIN=5, CMAX=10),
          "watch", _ALIVE.replace("{W}", W)]
    for i in range(20):
        st += ["step:5040", _ALIVE.replace("{W}", W)]
        if i == 9: st.append(SUSTAIN)
    st.append(inline("inv_savagery.lua", TAG="post"))
    return dict(steps=st, ticks=10, nowatch=True)
BLOCKS["INV"] = dict(fort="CTRL", spot="land", cells={"yeti": inv()})
# INV2 (1 Oct night): INV's YETI was refused by addNewSpecies ("28:19:biome": mountain/tundra on temperate shrubland), so
# no subject. CENOZOIC_SMILODON is SAVAGE with SHRUBLAND_TEMPERATE in its biomes (python search of the raws; grep misses it).
BLOCKS["INV2"] = dict(fort="CTRL", spot="land", cells={"smilodon": inv("CENOZOIC_SMILODON")})

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
# SCV2 (1 Oct night): the TOOL's scavenging pass (SCAV, v7.0 scav_ext: fliers land, swimmers reach water corpses, land
# scavengers wade, wanderers fall back), not the rig's own walkto/eat verbs that SCV/SCVW drove. Tool scavenging on, a pass
# every 300 ticks (`scavenge now`), 6 carcasses, 5 scavengers 8 tiles off, items counted before and after each pass.
def scavtool(scav, medium, prey, pmed=None, passes=8):
    pm = pmed or medium
    # 1 Oct: SCAV.run returns 0 unless cfg.enabled (the tool switched on) -- SCV2 rep 1-2 never enabled it on CTRL,
    # where the tool is off, so every pass was a no-op. Enable first, then the scavenge keys; print CACHE.scavLast
    # (units seen, remains seen, walking, eaten) after every pass so a no-op names itself.
    st = [SUSTAIN, "lua:dfhack.run_command('seasonal-wildlife', 'enable'); print('eco toolenable on=1')",
          "lua:local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig(); c.scavenge.enabled=true; c.v7.scav_ext=true; "
          "sw.saveConfig(c); local k=sw.loadConfig(); print('eco scavcfg on=1 enabled='..tostring(k.enabled)..' ext='..tostring(k.v7.scav_ext))",
          f"spawn {prey} 6 {{X}} {{Y}} {{Z}} 2 {pm}", f"corpse {{ids:{prey}}}", "step:50", "items {X} {Y} {Z} 6 before",
          f"spawn {scav} 5 {{X+8}} {{Y}} {{Z}} 2 {medium}"]
    for i in range(passes):
        st += ["lua:local ok,o=pcall(dfhack.run_command_silent,'seasonal-wildlife','scavenge','now'); print('eco scavpass '..tostring(o):gsub('\\n',' | '):sub(1,200))",
               "lua:local sw=reqscript('seasonal-wildlife'); local l=sw.CACHE.scavLast or {}; print(('eco scavlast units=%s remains=%s walking=%s eaten=%s t=%s'):format(tostring(l.units), tostring(l.remains), tostring(l.walking), tostring(l.eaten), tostring(l.t)))",
               "step:300", f"items {{X}} {{Y}} {{Z}} 6 p{i + 1}"]
    st.append("lua:local sw=reqscript('seasonal-wildlife'); local ok,s=pcall(sw.SCAV.status, sw.loadConfig()); print('eco scavstatus '..tostring(s):gsub('\\n',' | '):sub(1,300))")
    return dict(steps=st, ticks=10, post=["lua:dfhack.run_command('seasonal-wildlife', 'disable'); print('eco tooldisable ok=1')"])
BLOCKS["SCV2"] = dict(fort="CTRL", spot="land", cells={
    "wolf": scavtool("WOLF", "land", "KANGAROO"), "jackal": scavtool("JACKAL", "land", "KANGAROO"),
    "vulture": scavtool("BIRD_VULTURE", "land", "KANGAROO")})
BLOCKS["SCV2W"] = dict(fort="RIVER4", spot="shore", cells={
    "alligator_water": scavtool("ALLIGATOR", "water", "FISH_CARP", pmed="water"),
    "wolf_bank": scavtool("WOLF", "land", "FISH_CARP", pmed="water")})
# SCV2b/SCV2Wb (1 Oct): reruns with the tool enabled. ALLIGATOR is not a scavenger to SCAV.is (no BONECARN /
# CURIOUS_BEAST_EATER, not in SCAV.TEXT); vanilla's only aquatic scavengers are POND_GRABBER, SEA_SERPENT, SEA_MONSTER
# (python search of the raws), so the swimmer path is tested with a pond grabber in RIVER4's water.
BLOCKS["SCV2b"] = dict(fort="CTRL", spot="land", cells=dict(BLOCKS["SCV2"]["cells"]))
BLOCKS["SCV2Wb"] = dict(fort="RIVER4", spot="shore", cells={
    "pondgrabber_water": scavtool("POND_GRABBER", "water", "FISH_CARP", pmed="water"),
    "wolf_bank": scavtool("WOLF", "land", "FISH_CARP", pmed="water")})
BLOCKS["SCVC"] = dict(fort="BOATS", spot=BOATS_CAVES["1"], cells={"cavern_miasma_troll": corpses2("TROLL", "cave", "ELK_BIRD")})

# SW1/SW2/SW3 (coordinator, 30 Sep: threshold sweep, experiments/SWEEP-design.md). Shared SW1/SW2 arena: tool on, 5
# WOLF at the spot, DEER/WATER_BUFFALO/ELEPHANT herds 45-60 tiles off (beyond the 40-tile far_tiles default, so nudge
# is in play); sw.discoverGroups (exported, confirmed by grep: _ENV.discoverGroups at seasonal-wildlife.lua:6544)
# adopts the pack as one tracked group immediately rather than waiting on the schedule. _SW_STATUS is the manifest
# subject receipt every sample: WOLF group membership, cumulative ecology pairs/nudges, and the last pass's own
# counts -- reads g.ecology.last / g.ecology.nudges directly (loadGroups()), not a re-derived rel_map scan.
# 1 Oct: + land/cavern/water group counts (SW3 rep 1-2 could not see the land limit in total_groups: ~15 cavern groups)
_SW_STATUS = ("lua:local sw=reqscript('seasonal-wildlife'); local g=sw.loadGroups(); local wolfgrp,wolfn=0,0; local L={land=0,cavern=0,water=0};"
              " for _,grp in ipairs(g.groups) do if grp.token=='WOLF' then wolfgrp=wolfgrp+1; wolfn=wolfn+#grp.ids end;"
              " local k=grp.layer or 'land'; L[k]=(L[k] or 0)+1 end;"
              " local e=g.ecology or {}; local last=e.last or {};"
              " print(('eco swstatus tag={TAG} wolf_groups=%d wolf_members=%d total_groups=%d land_groups=%d cavern_groups=%d water_groups=%d eco_pairs=%d eco_nudges_total=%d last_nudged=%d last_slotted=%d')"
              ":format(wolfgrp, wolfn, #g.groups, L.land, L.cavern, L.water, last.pairs or 0, e.nudges or 0, last.nudged or 0, last.slotted or 0))")
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
            # H3 (Part 1 plan): SW1/SW2's discoverGroups found n=0 in all 40 cells -- spawn cleared the roaming flag and
            # the tool only adopts flagged units -- so the pack was never a tracked group. v7.1's `groups adopt <ids>`
            # takes them by id; cx-eco adopt reads the tool's record back and the auto check needs adopted=1.
            "adopt WOLF", "ecostate"]
def sw1(arm):
    st = sw_arena()
    if arm == "cad500": st.append("lua:local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig(); c.ecology.cadence=500; sw.saveConfig(c);"
                                   " dfhack.run_command('seasonal-wildlife', 'groups', 'ecology', 'on'); print('eco swcfg cadence=500 ok=1')")
    elif arm == "cad6000": st.append("lua:local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig(); c.ecology.cadence=6000; sw.saveConfig(c);"
                                      " dfhack.run_command('seasonal-wildlife', 'groups', 'ecology', 'on'); print('eco swcfg cadence=6000 ok=1')")
    elif arm == "nudge_off": st.append("lua:local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig(); c.ecology.nudge=false; sw.saveConfig(c);"
                                        " dfhack.run_command('seasonal-wildlife', 'groups', 'ecology', 'on'); print('eco swcfg nudge_bool=false ok=1')")
    elif arm == "nudge_tight": st.append("lua:dfhack.run_command('seasonal-wildlife', 'groups', 'nudge', '20', '1500', '6'); print('eco swnudge set=20,1500,6')")
    st.append("cfg ecology.cadence ecology.nudge ecology.far_tiles")   # H2: the dial as the tool now holds it
    st += {"cad500": ["check:cfg[path=ecology.cadence].value==500"], "cad6000": ["check:cfg[path=ecology.cadence].value==6000"],
           "nudge_off": ["check:cfg[path=ecology.nudge].value==false"],
           "nudge_tight": ["check:cfg[path=ecology.far_tiles].value==20"]}.get(arm, [])
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
                       "cfg v7.pack_floor v7.pack_sneak",   # H2: the dial as the tool holds it, not the echo
                       f"check:cfg[path=v7.pack_floor].value=={floor}", f"check:cfg[path=v7.pack_sneak].value=={sneak}",
                       "watch"]
    for i in range(20):
        st += ["step:1500", _SW_STATUS.replace("{TAG}", f"t{(i + 1) * 1500}")]
        if i == 0:   # H2: no SW2 arm ever wrote SNEAK (one wolf weighed 22% of a deer); after one pass it must show
            st.append("skill WOLF SNEAK")
            if arm == "sneak0": st.append("check:skill.with==0")
            if arm == "sneak100": st.append("check:skill.with>0")
        if i == 9: st.append(SUSTAIN)
    return dict(steps=st, ticks=10, nowatch=True, post=[_SW_CFG_RESTORE])
BLOCKS["SW2"] = dict(fort="CTRL", spot="land", cells={a: sw2(a) for a in SW2_ARMS})
# SW1R/SW2R (1 Oct): the same arms in REVERSED cell order. Cells of a rep share one load, so natives arriving over the
# rep (badgers, kangaroos, cavern troglodytes) pile into the later cells; SW1 showed the last two arms' attacks were
# mostly on natives. An effect that holds in both orders is the lever; one that flips is the cell position.
BLOCKS["SW1R"] = dict(fort="CTRL", spot="land", cells={a: sw1(a) for a in ("nudge_tight", "nudge_off", "cad6000", "cad500", "ctl")})
BLOCKS["SW2R"] = dict(fort="CTRL", spot="land", cells={a: sw2(a) for a in reversed(list(SW2_ARMS))})

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
    st.append("cfg limits.land.groups limits.land.auto")
    st += (["check:cfg[path=limits.land.auto].value==true"] if arm == "auto" else
           [f"check:cfg[path=limits.land.groups].value=={ {'g1': 1, 'g3': 3}[arm] }", "check:cfg[path=limits.land.auto].value==false"])
    st += ["groups3 base", "watch"]
    for i in range(1, 11):
        st += ["step:5040", _SW_STATUS.replace("{TAG}", f"t{i * 5040}"), f"groups3 t{i * 5040}"]   # H5: three-source groups
        if i == 5: st.append(SUSTAIN)
    return dict(steps=st, ticks=10, nowatch=True,
                post=["lua:dfhack.run_command('seasonal-wildlife', 'limits', 'land', 'groups', 'auto'); print('eco swlimits restored=auto')",
                      "lua:dfhack.run_command('seasonal-wildlife', 'disable'); print('eco tooldisable ok=1')"])
BLOCKS["SW3"] = dict(fort="CTRL", spot="land", cells={a: sw3(a) for a in ("g1", "g3", "auto")})
BLOCKS["SW3B"] = dict(fort="CTRL", spot="land", cells={a: sw3(a) for a in ("g1", "g3", "auto")})   # rerun with land_groups

# SW4 LADDER (coordinator, 30 Sep: SWEEP-design.md row f). Follows the F1 design (experiments/ECO-F1.json) exactly:
# tool disarmed by cfg (cfg.enabled/groups.enabled/ecology.enabled=false + disableSched -- NOT `seasonal-wildlife
# disable`, since F1 reads raw FREQUENCY while the scheduler is off, not cfg.enabled), land FREQUENCY written by
# guild from design.md section 5's table (the FREQUENCY the tool writes: AL=4, ML=12, GZ=50, PL=40, SH=30, LB=40),
# the predator multiplier (0.5/1/2) on AL/ML only, prey guilds fixed, surface released every 1,500 t to 60,000 t.
# Built as an eco-run.py block, not a cx-experiment.py manifest: cx-experiment.py has no "post" hook at all (grepped;
# only `arm.get("pre", [])`), so it cannot literally satisfy "restoring config/raws in post" -- its implicit reset is
# a full save-restore+load every replicate instead. An eco-run.py block keeps the raws-restore explicit (post always
# re-writes the x1 ladder) and keeps SW4 on the same CLI, TSV shape and coordinator as SW1-3/SW5/SW6.
# Every arm writes an ABSOLUTE frequency (X3.json's own convention, not a relative multiply of whatever is already in
# the raws) because this DF process is never restarted between cells of one rep -- a relative write would let x0.5
# leak into x2's baseline.
# Receipt: the tool's own group engine is inert while disarmed (sw.loadGroups() cannot be used, unlike SW1-3), so
# the subject receipt here is a guild census read straight off the map (sw.WILD.onMap/layerOf, both cfg-independent)
# every 1,500 t -- present count by guild, which is also the raw series the predator-share readout comes from.
SW4_MULT = {"ctl": 1.0, "half": 0.5, "double": 2.0}
SW4_BASE = {"AL": 4, "ML": 12, "GZ": 50, "PL": 40, "SH": 30, "LB": 40}   # design.md S5, LADDER22 scale
SW4_PRED_GUILDS = ("AL", "ML")
def _sw4_freq_lua(mult, phase):
    base = ", ".join(f"{g}={v}" for g, v in SW4_BASE.items())
    pred = ", ".join(f"{g}=true" for g in SW4_PRED_GUILDS)
    return ("lua:local sw=reqscript('seasonal-wildlife'); local rs=sw.getEmbarkRegions();"
            f" local mult={mult}; local BASE={{{base}}}; local PREDG={{{pred}}}; local n={{}};"
            " for _,pop in ipairs(df.global.world.populations.all) do"
            " if df.world_population_type[pop.type]=='Animal' and sw.managedPop(pop, rs, sw.LAYER_SET.land) then"
            " local cr=df.creature_raw.find(pop.race);"
            " if cr then local g=sw.classify(cr).guild; local f=BASE[g];"
            " if f then if PREDG[g] then f=math.max(1, math.floor(f*mult+0.5)) end; cr.frequency=f; n[g]=(n[g] or 0)+1 end end"
            " end end;"
            f" print(('eco swladder phase={phase} mult=%.2f al_f=%d ml_f=%d al_n=%d ml_n=%d gz_n=%d pl_n=%d sh_n=%d lb_n=%d')"
            ":format(mult, math.floor(BASE.AL*mult+0.5), math.floor(BASE.ML*mult+0.5),"
            " n.AL or 0, n.ML or 0, n.GZ or 0, n.PL or 0, n.SH or 0, n.LB or 0))")
_SW4_DISARM = ("lua:local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig();"
               " if not cfg.initialized then sw.captureDefault(cfg) end;"
               " cfg.enabled=false; cfg.groups.enabled=false; cfg.ecology.enabled=false; sw.saveConfig(cfg); sw.disableSched();"
               " print('eco swladder phase=disarmed armed=0')")
_SW4_RELEASE = "lua:dfhack.run_command('cx-probe', 'release', 'surface'); print('eco release ok=1')"
_SW4_CENSUS = ("lua:local sw=reqscript('seasonal-wildlife'); local C={AL=0,ML=0,GZ=0,PL=0,SH=0,LB=0,other=0}; local total=0;"
               " for _,u in ipairs(df.global.world.units.active) do"
               " if sw.WILD.onMap(u) and sw.WILD.layerOf(u)=='land' then"
               " local r=df.creature_raw.find(u.race); local g=(r and sw.classify(r).guild) or 'other'; if C[g]==nil then g='other' end;"
               " C[g]=C[g]+1; total=total+1 end end;"
               " print(('eco swladder tag={TAG} total=%d al=%d ml=%d gz=%d pl=%d sh=%d lb=%d other=%d')"
               ":format(total, C.AL, C.ML, C.GZ, C.PL, C.SH, C.LB, C.other))")
def sw4(arm):
    mult = SW4_MULT[arm]
    st = [SUSTAIN, _SW4_DISARM, _sw4_freq_lua(mult, "set"), "cfg enabled", "check:cfg[path=enabled].value==false",
          "check:swladder[phase=set].al_n>0", "watch", _SW4_CENSUS.replace("{TAG}", "t0")]
    for i in range(40):   # 40 x 1,500 t = 60,000 t (design row f)
        st += ["step:1500", _SW4_RELEASE, _SW4_CENSUS.replace("{TAG}", f"t{(i + 1) * 1500}")]
        if i == 19: st.append(SUSTAIN)
    return dict(steps=st, ticks=10, nowatch=True, post=[_sw4_freq_lua(1.0, "restore")])
BLOCKS["SW4"] = dict(fort="CTRL", spot="land", cells={a: sw4(a) for a in ("ctl", "half", "double")})

# SW5 GROUPS-CAVERN / SW6 GROUPS-WATER (coordinator, 30 Sep: SWEEP-design.md rows g/h). Natural arrivals on BOATS,
# tool on, same shape as SW3 (no placed subject) but with `v7 layer_groups on` first, since that flag is what makes
# each cavern depth / water body its own limit (section 0's table; confirmed in seasonal-wildlife.lua: QUOTA.groupsFor
# keys off cfg.limits[parent] per layer only when V7.on(cfg,'layer_groups')). `limits cavern groups N|auto` is valid
# CLI for every N and for auto (grepped: the 7095-7134 handler only special-cases water). `limits water groups auto`
# is REJECTED by that same handler (lay ~= 'water' guard on the auto branch) -- SW6's auto arm instead writes
# cfg.limits.water.auto=true directly (the handler's own numeric branch, QUOTA.set, is what a CLI `groups N` call
# runs; auto has no verb for water so the cfg field is set the same way SW1/SW2 set levers with no CLI verb).
# Subject receipt (manifest-subject-receipt; design row h names this explicitly after 3 prior vacuous runs):
# sw.WILD.countByLayer() at t0, cfg-independent, must show >0 cavern (SW5) / water (SW6) units before the status
# series is read as meaningful. Per-sample status breaks groups down by depth (SW5) or body (SW6) but keeps the
# `total_groups` key _SW_STATUS also uses, so sweep-tally.py's existing swstatus loader (G component) needs no change.
def _sw_layer_receipt(layer):
    return (f"lua:local sw=reqscript('seasonal-wildlife'); local by=sw.WILD.countByLayer();"
            f" print(('eco swreceipt layer={layer} present=%d land=%d water=%d cavern=%d deep=%d')"
            f":format(by.{layer}, by.land, by.water, by.cavern, by.deep))")
_SW_CAVERN_STATUS = ("lua:local sw=reqscript('seasonal-wildlife'); local g=sw.loadGroups(); local byd={}; local n=0;"
                     " for _,grp in ipairs(g.groups) do if grp.layer=='cavern' then n=n+1; local d=grp.depth or -1; byd[d]=(byd[d] or 0)+1 end end;"
                     " local e=g.ecology or {}; local last=e.last or {};"
                     " print(('eco swstatus tag={TAG} cavern_groups=%d d0=%d d1=%d d2=%d total_groups=%d eco_pairs=%d eco_nudges_total=%d')"
                     ":format(n, byd[0] or 0, byd[1] or 0, byd[2] or 0, #g.groups, last.pairs or 0, e.nudges or 0))")
_SW_WATER_STATUS = ("lua:local sw=reqscript('seasonal-wildlife'); local g=sw.loadGroups(); local byb={}; local n=0;"
                    " for _,grp in ipairs(g.groups) do if grp.layer=='water' then n=n+1; local b=grp.body or 'none'; byb[b]=(byb[b] or 0)+1 end end;"
                    " local e=g.ecology or {}; local last=e.last or {};"
                    " print(('eco swstatus tag={TAG} water_groups=%d ocean=%d lake=%d river=%d pool=%d total_groups=%d eco_pairs=%d eco_nudges_total=%d')"
                    ":format(n, byb.ocean or 0, byb.lake or 0, byb.river or 0, byb.pool or 0, #g.groups, last.pairs or 0, e.nudges or 0))")
def sw5(arm):
    st = ["lua:dfhack.run_command('seasonal-wildlife', 'enable'); print('eco toolenable on=1')",
          "lua:dfhack.run_command('seasonal-wildlife', 'groups', 'on'); print('eco groupson ok=1')",
          "lua:dfhack.run_command('seasonal-wildlife', 'v7', 'layer_groups', 'on'); print('eco swv7 key=layer_groups value=on')"]
    if arm == "auto":
        st.append("lua:dfhack.run_command('seasonal-wildlife', 'limits', 'cavern', 'groups', 'auto'); print('eco swlimits cavern=auto')")
    else:
        n = {"c1": "1", "c2": "2"}[arm]
        st.append(f"lua:dfhack.run_command('seasonal-wildlife', 'limits', 'cavern', 'groups', '{n}'); print('eco swlimits cavern={n}')")
    st += ["cfg v7.layer_groups limits.cavern.groups limits.cavern.auto", "check:cfg[path=v7.layer_groups].value==true"]
    st += (["check:cfg[path=limits.cavern.auto].value==true"] if arm == "auto" else
           [f"check:cfg[path=limits.cavern.groups].value=={ {'c1': 1, 'c2': 2}[arm] }"])
    st += ["groups3 base", "watch", _sw_layer_receipt("cavern")]
    for i in range(1, 11):
        st += ["step:5040", _SW_CAVERN_STATUS.replace("{TAG}", f"t{i * 5040}"), f"groups3 t{i * 5040}"]
        if i == 5: st.append(SUSTAIN)
    return dict(steps=st, ticks=10, nowatch=True,
                post=["lua:dfhack.run_command('seasonal-wildlife', 'limits', 'cavern', 'groups', 'auto'); print('eco swlimits restored=auto')",
                      "lua:dfhack.run_command('seasonal-wildlife', 'disable'); print('eco tooldisable ok=1')"])
BLOCKS["SW5"] = dict(fort="BOATS", spot=BOATS_CAVES["1"], cells={a: sw5(a) for a in ("c1", "c2", "auto")})

def sw6(arm):
    st = ["lua:dfhack.run_command('seasonal-wildlife', 'enable'); print('eco toolenable on=1')",
          "lua:dfhack.run_command('seasonal-wildlife', 'groups', 'on'); print('eco groupson ok=1')",
          "lua:dfhack.run_command('seasonal-wildlife', 'v7', 'layer_groups', 'on'); print('eco swv7 key=layer_groups value=on')"]
    if arm == "auto":
        # no CLI verb takes `groups auto` for water (seasonal-wildlife.lua ~7112 rejects it); write the cfg field
        # QUOTA.set's own numeric branch flips (cfg.limits.water.auto) directly instead.
        st.append("lua:local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig(); c.limits.water.auto=true; sw.saveConfig(c);"
                   " print('eco swlimits water=auto')")
    else:
        n = {"w1": "1", "w2": "2"}[arm]
        st.append(f"lua:dfhack.run_command('seasonal-wildlife', 'limits', 'water', 'groups', '{n}'); print('eco swlimits water={n}')")
    st += ["cfg v7.layer_groups limits.water.groups limits.water.auto", "check:cfg[path=v7.layer_groups].value==true"]
    st += (["check:cfg[path=limits.water.auto].value==true"] if arm == "auto" else
           [f"check:cfg[path=limits.water.groups].value=={ {'w1': 1, 'w2': 2}[arm] }"])
    st += ["groups3 base", "watch", _sw_layer_receipt("water")]
    for i in range(1, 11):
        st += ["step:5040", _SW_WATER_STATUS.replace("{TAG}", f"t{i * 5040}"), f"groups3 t{i * 5040}"]
        if i == 5: st.append(SUSTAIN)
    return dict(steps=st, ticks=10, nowatch=True,
                post=["lua:local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig(); c.limits.water.auto=true; sw.saveConfig(c);"
                      " print('eco swlimits restored=auto')",
                      "lua:dfhack.run_command('seasonal-wildlife', 'disable'); print('eco tooldisable ok=1')"])
BLOCKS["SW6"] = dict(fort="BOATS", spot="water", cells={a: sw6(a) for a in ("w1", "w2", "auto")})

# SW7 BUILDER (coordinator, 30 Sep: SWEEP-design.md row i / section 3 item 7). D1 (experiments/SWEEP-D1.md) found
# CTRL's and BOATS's rosters change at every level tested against the current value (3) -- 100% of 80 CTRL
# embark/season/seed keys differ at levels 1, 2 and 5, and pack-hunt presence moves monotonically (56.8% to
# 76.7%), so per the design's rule ("Goes to the rig (SW7) only if CTRL's roster changes") this block is required.
#
# The pack bonus itself has NO live lever: v7.0.0's own roster port (ROSTER.build / ROSTER.packBonus, ~line 5090)
# hard-codes the x3 multiplier (`ROSTER.packBonus(e) and 3 or 1`) with no cfg field, V7 switch or CLI verb -- grepped,
# confirmed absent. This matches design.md section 0's own row for this value ("lives in: builder only (pick
# weight)... set it with: desk config. A roster reaches the fort via `roster`/`seasons` verbs (cfg `allow`,
# `assign`)"): the sweep does not vary a tool setting here, it pushes three different DESK-computed rosters onto the
# live fort through the same roster/seasons mechanism DF already uses for any manual roster edit.
#
# Rosters were precomputed once, offline (python3 -c import only, no DF contact), at CTRL's own identity
# (TEMP_GRASS_FOREST/land, seed 1 -- roster2.py's own __main__ default, established in D1), one roster2.build() call
# per season per level, unioned into an active-species -> seasons-selected set. This is the same convention SW4's
# FREQUENCY ladder already established: a desk artifact embedded as literal data, not computed in Lua. All three
# arms (including p3, the current/control value) go through the identical push mechanism, so the comparison is
# push-vs-push, not push-vs-untouched -- "rosters applied" per the design's own phrasing for this row.
#
# Known data quirk, not introduced here: the census `tokens-by-creature.tsv` (data/eco-desk/) spells the red panda's
# id with a literal space ("RED PANDA"), unlike every other token sampled (WOLF, DEER, PANDA, BIRD_EMU, ...). DF raw
# CREATURE_IDs never contain a space, so this is normalized to RED_PANDA below; if the live KEY still does not
# match, the apply step's own miss= count in its printed line catches it (a missed species is silently not pushed,
# never a crash -- the CLI's own `roster KEY ...` path no-ops with a usage line on an unknown key).
#
# Window: 50,400 t, same as the groups-at-once blocks (this is also a natural-arrival read, not an encounter
# lever). CTRL natural (tool on, groups on, no forced placement -- SW3's own shape). _SW_STATUS is reused unchanged
# (SW3 already reuses this wolf-group-counting reader for a non-wolf natural scenario; wolf_groups/wolf_members read
# 0 here and total_groups/eco_pairs/eco_nudges_total -- the keys sweep-tally.py actually parses -- stay meaningful).
# Receipt: sw.WILD.countByLayer().land > 0 after the push (manifest-subject-receipt). Post: ROSTER.resetRoster
# (exported, "reset the roster to the embark as first found") across every layer, not just land, so a later block
# never inherits this one's push.
SW7_ROSTER = {
    1: [("BEAR_BLACK", "Su"), ("BIRD_EMU", "SpSu"), ("BIRD_KAKAPO", "AuWi"), ("BIRD_KIWI", "Wi"),
        ("BOBCAT", "SpAuWi"), ("COUGAR", "Au"), ("COYOTE", "SpSuAu"), ("DINGO", "SpWi"),
        ("FOX", "Wi"), ("KANGAROO", "SuAu"), ("KOALA", "Au"), ("LIZARD", "Sp"),
        ("LOUSE", "Sp"), ("MACAQUE_RHESUS", "SpSu"), ("MOOSE", "Sp"), ("PANDA", "SpWi"),
        ("RAT", "SuAu"), ("RATTLESNAKE", "Su"), ("RED_PANDA", "AuWi"), ("SKINK", "AuWi"),
        ("SPIDER_BROWN_RECLUSE", "AuWi"), ("SPIDER_JUMPING", "Sp"), ("SQUIRREL_FLYING", "Su"), ("SQUIRREL_RED", "Su"),
        ("TERMITE", "SpSuAuWi"), ("WOMBAT", "Su"), ("WORM", "Wi")],
    3: [("ADDER", "Su"), ("BADGER", "SpAu"), ("BEETLE", "Sp"), ("BIRD_EMU", "AuWi"),
        ("BOBCAT", "Wi"), ("CHIPMUNK", "Sp"), ("COYOTE", "SpSuAuWi"), ("DEER", "Au"),
        ("DINGO", "SpAuWi"), ("GRASSHOPPER", "Su"), ("GRAY_LANGUR", "SuAuWi"), ("HAMSTER", "AuWi"),
        ("HARE", "Wi"), ("IBEX", "Wi"), ("MUSKOX", "Su"), ("OPOSSUM", "Sp"),
        ("PANDA", "Sp"), ("RAT", "SpAu"), ("RED_PANDA", "Su"), ("SKINK", "Su"),
        ("SKUNK", "Su"), ("SLUG", "Au"), ("SNAIL", "Wi"), ("SQUIRREL_FLYING", "Su"),
        ("TERMITE", "SpSuAuWi"), ("WILD_BOAR", "Sp"), ("WOLF", "Su"), ("WOMBAT", "SpAu"),
        ("WORM", "Wi")],
    5: [("ADDER", "Wi"), ("BADGER", "SpSuAu"), ("BEAR_GRIZZLY", "Au"), ("BEETLE", "Wi"),
        ("BIRD_EMU", "SuAu"), ("BOBCAT", "Su"), ("CHIPMUNK", "Su"), ("COYOTE", "SpAuWi"),
        ("DINGO", "SpWi"), ("ECHIDNA", "Au"), ("ELK", "SpWi"), ("GRASSHOPPER", "Sp"),
        ("HAMSTER", "Au"), ("KANGAROO", "SuAu"), ("KOALA", "Wi"), ("LOUSE", "SpSuAu"),
        ("MACAQUE_RHESUS", "Su"), ("MUSKOX", "Au"), ("PANDA", "Sp"), ("SKINK", "Wi"),
        ("SKUNK", "Sp"), ("SQUIRREL_FLYING", "Wi"), ("SQUIRREL_GRAY", "Au"), ("SQUIRREL_RED", "Su"),
        ("TERMITE", "SpSuAuWi"), ("TICK", "Sp"), ("WILD_BOAR", "SpWi"), ("WOLF", "Su"),
        ("WOMBAT", "SuWi")],
}
def _sw7_apply_lua(lvl):
    rows = ", ".join(f"{{t='{t}',s='{s}'}}" for t, s in SW7_ROSTER[lvl])
    return ("lua:local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig(); local pool=sw.buildPool(c);"
            f" local WANT={{{rows}}}; local want={{}}; for _,r in ipairs(WANT) do want[r.t]=r.s end;"
            " local applied,found=0,{};"
            " for _,e in ipairs(pool) do"
            " if e.inEmbark and not e.locked and e.layer=='land' then"
            " found[e.key]=true;"
            " local s=want[e.key];"
            " if s then sw.ROSTER.setActive(c, pool, e, true, 'sw7: desk roster pack');"
            f" local arr=sw.VERMIN.parseSeasons(s); if arr then sw.setAssign(c, e.key, arr); sw.whySet(c, e.key, 'sw7: desk roster pack') end;"
            " applied=applied+1"
            " else sw.ROSTER.setActive(c, pool, e, false, 'sw7: desk roster pack (not selected)') end"
            " end end;"
            " local miss={}; for t,_ in pairs(want) do if not found[t] then miss[#miss+1]=t end end;"
            " sw.saveConfig(c);"
            f" print(('eco sw7apply level={lvl} applied=%d wanted=%d missing=%d miss=%s')"
            ":format(applied, #WANT, #miss, table.concat(miss, ',')))")
_SW7_RECEIPT = ("lua:local sw=reqscript('seasonal-wildlife'); local by=sw.WILD.countByLayer();"
                " print(('eco swreceipt layer=land present=%d land=%d water=%d cavern=%d deep=%d')"
                ":format(by.land, by.land, by.water, by.cavern, by.deep))")
_SW7_RESET = ("lua:local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig();"
              " local n=sw.ROSTER.resetRoster(c, sw.buildPool(c)); sw.saveConfig(c);"
              " print(('eco sw7reset active=%d'):format(n))")
def sw7(arm):
    lvl = {"p1": 1, "p3": 3, "p5": 5}[arm]
    st = ["lua:dfhack.run_command('seasonal-wildlife', 'enable'); print('eco toolenable on=1')",
          "lua:dfhack.run_command('seasonal-wildlife', 'groups', 'on'); print('eco groupson ok=1')",
          _sw7_apply_lua(lvl), "watch", _SW7_RECEIPT]
    for i in range(1, 11):
        st += ["step:5040", _SW_STATUS.replace("{TAG}", f"t{i * 5040}")]
        if i == 5: st.append(SUSTAIN)
    return dict(steps=st, ticks=10, nowatch=True,
                post=[_SW7_RESET, "lua:dfhack.run_command('seasonal-wildlife', 'disable'); print('eco tooldisable ok=1')"])
BLOCKS["SW7"] = dict(fort="CTRL", spot="land", cells={a: sw7(a) for a in ("p1", "p3", "p5")})

def prune_autosaves(save, say):
    """DF autosaves at season changes, and an autosave of the fort hides the fort in the Continue list (ECO P2, 30 Sep:
    'save list never showed Folder: CTRL' after P1's 240k ticks). Delete the autosaves of THIS save's world only."""
    rows_ = [l.split("\t") for l in sh("ui", "saves").splitlines() if l.startswith("SAVE\t")]
    world = next((r[2] for r in rows_ if len(r) > 2 and r[1] == save), None)
    for r in rows_:
        if len(r) > 2 and r[1].startswith("autosave") and world and r[2] == world:
            sh("save-delete", r[1], check=False); say(f"  pruned {r[1]} (world {world})")

def fresh_load(fort, say):
    """H1: restore the fort's .preverify backup and load it on a fresh DF. Nothing from an earlier cell survives."""
    sh("title", timeout=300)
    prune_autosaves(fort, say)
    sh("save-restore", f"{fort}.preverify", timeout=600)
    sh("stop", timeout=120, check=False); sh("start", timeout=300)
    sh("load", fort, timeout=1200)
    sh("fps", 1000, 10)


def locate(b):
    sp = b["spot"].split(":")
    if sp[0] in ("cavern", "cavepool"):
        skip = int(sp[3]) if len(sp) > 3 else 0   # HC4: a 4th colon-segment picks the Nth match, not just the top
        spot = kv(eco("cavespot", sp[0], skip, *sp[1:3])[-1])
    elif sp[0] == "vermin":
        spot = kv(eco("vspot", *sp[1:])[-1])
    else:
        spot = kv(eco("spot", sp[0])[-1])
    return int(spot["x"]), int(spot["y"]), int(spot["z"])


def wipe_map(b, say):
    """R15: every animal off the map before the cell places anything; proven by wipecheck == 0 (ManipFail if not)."""
    extra = ["livestock"] if b.get("wipe_livestock") else []
    rows = eco("wipe", *extra)
    sh("step", 5, timeout=300)
    chk = eco("wipecheck", *extra)
    d = kv(chk[-1]) if chk else {}
    if d and (int(d.get("remaining", 0)) or int(d.get("pending", 0))):   # an arrival in those 5 ticks: once more
        rows += chk + eco("wipe", *extra)
        sh("step", 5, timeout=300)
        chk = eco("wipecheck", *extra)
    rows += chk
    bad = ecolib.auto_failures([l for l in chk if l.startswith("eco wipecheck")])
    if bad:
        raise ManipFail("wipe left animals on the map: " + "; ".join(bad))
    return rows


def plan(names, a):
    print(f"{'block':<16} {'fort':<10} {'cells':>5} {'reps':>4} {'loads':>5} {'ticks/rep':>10} {'minutes':>8}  wipe")
    tot = 0.0
    for bname in names:
        b = BLOCKS[bname]
        e = ecolib.estimate(b, a.reps, a.load, tps=a.tps, scale=a.tick_scale, wipe=b.get("wipe", True) and not a.no_wipe)
        tot += e["minutes"]
        print(f"{bname:<16} {b['fort']:<10} {e['cells']:>5} {e['reps']:>4} {e['loads']:>5} {e['ticks_per_rep']:>10,} {e['minutes']:>8}  "
              f"{'yes' if b.get('wipe', True) and not a.no_wipe else 'no (' + b.get('wipe_why', '--no-wipe') + ')'}")
    print(f"total about {tot / 60:.1f} h at {a.tps:.0f} t/s, {a.load}-level loads, tick scale {a.tick_scale}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blocks", help="BLOCK[,BLOCK...], or list, or plan")
    ap.add_argument("more", nargs="?", help="with plan: the blocks")
    ap.add_argument("--run")
    ap.add_argument("--reps", type=int, default=5, help="replicates per arm (R12: 5)")
    ap.add_argument("--only")
    ap.add_argument("--load", choices=["arm", "rep"], default="arm", help="H1: a fresh load per arm (default) or per rep (pre-v7.1)")
    ap.add_argument("--order", choices=list(ecolib.ORDERS), default="counterbalance", help="H1: cell order across reps")
    ap.add_argument("--no-wipe", action="store_true", help="R15 off: do not wipe the map's animals before each cell")
    ap.add_argument("--manip", choices=["abort", "skip"], default="abort", help="H2: on a failed check abort the block, or skip the cell")
    ap.add_argument("--isolate", choices=["roam", "none"], default="roam", help="H4: placed units keep DF's roaming flag (roam)")
    ap.add_argument("--placement", choices=["tool", "legacy"], default="tool",
                    help="tool: NONE slot row, own entry, debited (PLACE.one); legacy: the pre-v7.1 rig (STRANGER, first entry, no debit)")
    ap.add_argument("--tick-scale", type=float, default=1.0, help="R12: multiply every step and cell length (short reps)")
    ap.add_argument("--tps", type=float, default=450.0, help="plan: assumed ticks per second")
    ap.add_argument("--dry-run", action="store_true", help="walk every step with canned receipts; no rig call is made")
    a = ap.parse_args()
    if a.blocks == "list":
        for k, b in BLOCKS.items():
            print(f"{k}: {b['fort']} {len(b['cells'])} cells{'' if b.get('wipe', True) else ' (no wipe: ' + b.get('wipe_why', '') + ')'}")
        return 0
    if a.blocks == "plan":
        names = (a.more or "").split(",") if a.more else list(BLOCKS)
        unknown = [n for n in names if n not in BLOCKS]
        if unknown:
            sys.exit(f"no block {', '.join(unknown)}")
        return plan(names, a)
    names = a.blocks.split(",")
    unknown = [n for n in names if n not in BLOCKS]
    if unknown:
        sys.exit(f"no block {', '.join(unknown)} (eco-run.py list)")
    if a.dry_run:
        DRY.append("dry-run")
    run = Path(a.run) if a.run else ROOT / "data/experiments/ECO" / (("dry-" if a.dry_run else "") + time.strftime("%Y%m%d-%H%M%S"))
    run.mkdir(parents=True, exist_ok=True)
    log = open(run / "log.txt", "a")

    def say(m):
        line = f"{time.strftime('%H:%M:%S')} {m}"; print(line, flush=True); log.write(line + "\n"); log.flush()
    only = set(a.only.split(",")) if a.only else None
    say(f"eco-run v7.1 harness: reps {a.reps}, load per {a.load}, order {a.order}, wipe {'off' if a.no_wipe else 'on'}, "
        f"manip {a.manip}, isolate {a.isolate}, placement {a.placement}, tick scale {a.tick_scale}{', DRY RUN' if a.dry_run else ''}")
    for bname in names:
        b = BLOCKS[bname]
        out = open(run / f"{bname}.tsv", "a")
        wipe = b.get("wipe", True) and not a.no_wipe
        cells = {k: v for k, v in b["cells"].items() if not only or k in only}
        say(f"== block {bname} on {b['fort']}: {len(cells)} cells x {a.reps} rep(s); wipe "
            f"{'on' if wipe else 'off (' + b.get('wipe_why', '--no-wipe') + ')'}")
        # H2, printed first: what each cell must prove before its outcome counts
        for cname, c in cells.items():
            explicit = [st[6:] for st in c["steps"] if st.startswith("check:")]
            auto = sorted({st.split()[0] for st in c["steps"] if st.split() and st.split()[0] in ecolib.AUTO})
            say(f"  manip {cname}: " + ("; ".join(explicit) or "-") + f" | auto: {', '.join(auto + (['wipecheck'] if wipe else [])) or '-'}")
            for chk in explicit:
                ecolib.parse_check(chk)   # a malformed check fails here, before any rig time is spent
        aborted = False
        for rep in range(1, a.reps + 1):
            order = ecolib.arm_order(list(cells), rep, a.order)
            say(f"  rep {rep}: order {', '.join(order)}")
            temps = []
            X = Y = Z = None
            if a.load == "rep":
                fresh_load(b["fort"], say)
                X, Y, Z = locate(b)
                say(f"  rep {rep}: spot {b['spot']} {X},{Y},{Z}")
            for cname in order:
                c = cells[cname]
                t0 = time.monotonic()
                manip_rows, rows = [], []
                try:
                    if a.load == "arm":
                        fresh_load(b["fort"], say)
                        X, Y, Z = locate(b)
                    ids = {}
                    V = {"X": X, "Y": Y, "Z": Z, "FX": X, "FY": Y, "FZ": Z}

                    def fill(st):
                        st = re.sub(r"\{ids:(\w+)\}", lambda m: ids.get(m.group(1), ""), st)
                        st = re.sub(r"\{(F?[XYZ])([+-]\d+)?\}", lambda m: str(V[m.group(1)] + int(m.group(2) or 0)), st)
                        return st
                    eco("clear"); eco("restore")
                    if wipe:
                        manip_rows += wipe_map(b, say)
                    for st in c["steps"]:
                        st = ecolib.scale_step(fill(st), a.tick_scale)
                        if st.startswith("check:"):
                            ok, msg = ecolib.eval_check(ecolib.parse_check(st[6:]), manip_rows + rows)
                            if not ok and DRY:   # canned receipts cannot carry the dial's value: record, do not judge
                                manip_rows.append(f"eco manip ok=dry check={msg.replace(' ', '_')}")
                                continue
                            manip_rows.append(f"eco manip ok={int(ok)} check={msg.replace(' ', '_')}")
                            if not ok:
                                raise ManipFail(msg)
                            continue
                        if st.startswith("lua:"):
                            got = [l for l in sh("lua", st[4:], timeout=300).splitlines() if l.startswith("eco ")]
                        elif st.startswith("step:"):
                            sh("step", st[5:], timeout=900); continue
                        elif st.startswith("read:"):
                            rows += eco("read", st[5:]); continue
                        elif st.startswith("save:"):
                            sh("save", st[5:], timeout=900); continue
                        elif st.startswith("load:"):
                            # the loaded save cannot be deleted (save-delete refuses with a map loaded), and left behind
                            # it hides the fort in DF's Continue list (ECO S2, 30 Sep): delete it at the block's end
                            sh("load", st[5:], timeout=1200); temps.append(st[5:])
                            rows.append(f"eco reload save={st[5:]} ok=1"); continue
                        else:
                            if st.startswith("spawn "):
                                opts = (["roam"] if a.isolate == "roam" else []) + (["legacy"] if a.placement == "legacy" else [])
                                if opts:
                                    st = ecolib.spawn_opts(st, *opts)
                            got = eco(*st.split())
                            for l in got:
                                d = kv(l)
                                if l.startswith("eco spawn") and d.get("ids"):
                                    ids[d["token"]] = d["ids"]
                                if l.startswith("eco spot") and d.get("kind") == "fort":
                                    V.update(FX=int(d["x"]), FY=int(d["y"]), FZ=int(d["z"]))
                        # H2: every receipt that proves a manipulation reached its subject, checked as it prints
                        bad = ecolib.auto_failures(got)
                        recs = [l for l in got if l.split()[1:2] and l.split()[1] in ecolib.RECEIPTS]
                        manip_rows += recs
                        rows += [l for l in got if l not in recs]
                        if bad:
                            raise ManipFail("; ".join(bad))
                    if not c.get("nowatch"):
                        rows += eco("watch")
                    sh("step", max(1, int(round(c["ticks"] * a.tick_scale))), timeout=900)
                    rows += eco("read", cname)
                    for st in c.get("post", []):
                        st = fill(st)
                        if st.startswith("lua:"):
                            rows += [l for l in sh("lua", st[4:], timeout=300).splitlines() if l.startswith("eco ")]
                        else:
                            rows += eco(*st.split())
                    eco("clear"); eco("restore")
                    for l in manip_rows + rows:   # the manipulation receipts first (H2)
                        p_ = l.split()
                        out.write("\t".join([bname, cname, str(rep), p_[1], " ".join(p_[2:])]) + "\n")
                    out.flush()
                    k = [kv(l) for l in rows]
                    deaths = sum(1 for l in rows if l.startswith("eco death"))
                    att = sum(int(d.get("n", 0)) for l, d in zip(rows, k) if l.startswith("eco attacks "))
                    placed = "/".join(kv(l)["placed"] for l in manip_rows if l.startswith("eco spawn"))
                    wiped = next((kv(l).get("marked") for l in manip_rows if l.startswith("eco wipe ")), "-")
                    say(f"    {cname}: manip ok ({len(manip_rows)} receipts, wiped {wiped}), placed {placed or '-'}, "
                        f"attacks {att}, deaths {deaths} ({time.monotonic() - t0:.0f} s)")
                except ManipFail as e:
                    say(f"    !! MANIP-FAIL {cname}: {e}"[:600])
                    for l in manip_rows:
                        p_ = l.split()
                        out.write("\t".join([bname, cname, str(rep), p_[1], " ".join(p_[2:])]) + "\n")
                    out.write("\t".join([bname, cname, str(rep), "MANIPFAIL", str(e)[:300]]) + "\n"); out.flush()
                    try:
                        eco("clear"); eco("restore")
                    except Exception:
                        pass
                    if a.manip == "abort":
                        say(f"  !! block {bname} aborted: a dial did not reach its subject (H2); its outcomes would be vacuous")
                        aborted = True
                        break
                except Exception as e:
                    say(f"    !! {cname} FAILED: {e!r}"[:600])
                    out.write("\t".join([bname, cname, str(rep), "FAILED", repr(e)[:300]]) + "\n"); out.flush()
                    try:
                        eco("clear"); eco("restore")
                    except Exception:
                        say("    !! clear failed too; stopping the block")
                        aborted = True
                        break
            sh("title", timeout=300, check=False)
            for t in temps:
                say("  " + sh("save-delete", t, timeout=300, check=False).strip()[-120:])
            if aborted:
                break
        say(f"== block {bname} {'ABORTED' if aborted else 'done'}")
    if a.dry_run:
        (run / "dry-calls.txt").write_text("\n".join(DRY[1:]) + "\n")
        say(f"dry run: {len(DRY) - 1} rig calls recorded in {run / 'dry-calls.txt'}")
    say("=== eco exit")
    return 0


# 1 Oct 01:20: counterbalance the not-yet-run sweep blocks (see the cell loop in main). v7.1: every block is
# counterbalanced by default (--order); the flag is kept so old run logs still read.
for _b in ("SW3", "SW3B", "SW4", "SW5", "SW6", "SW7"):
    BLOCKS[_b]["counterbalance"] = True

# R15 (user, 1 Oct): every cell rep wipes ALL animals before it places its groups. Blocks whose SUBJECT is the natives
# themselves -- what DF draws, writes or holds -- opt out; each says why. Everything else wipes (cx-eco wipe).
WIPE_OPT_OUT = {
    "RELS": "the subject is DF's own relations among natives",
    "RELS2": "the subject is DF's own arrivals", "RELS2b": "the subject is DF's own arrivals",
    "RELS3": "the subject is DF's reaction to released natives", "RELP": "the subject is natives' relations",
    "SLOTV": "the subject is DF's slots on natives", "LAKEP": "the first read surveys the lake's natives",
    "SW3": "natural arrivals are the subject", "SW3B": "natural arrivals are the subject",
    "SW4": "natural arrivals are the subject", "SW5": "natural arrivals are the subject",
    "SW6": "natural arrivals are the subject", "SW7": "natural arrivals are the subject",
    "DEPTH": "a survey; nothing placed", "DEPTHL": "a survey; nothing placed", "O": "a survey cell; nothing placed",
}
for _b, _why in WIPE_OPT_OUT.items():
    if _b in BLOCKS:
        BLOCKS[_b]["wipe"] = False; BLOCKS[_b]["wipe_why"] = _why

# R11 + B-dials section 10: the 1x1-per-biome test forts embarked from region8 (scripts/b1-forts.py). One baseline
# block per registered fort: tool on with per-layer groups, natural arrivals for 50,400 t (half a season), groups
# counted three ways (H5) every 5,040 t. Read from data/forts/b1-forts.tsv when it exists; absent, no B1 blocks.
def b1base():
    st = [SUSTAIN, "lua:dfhack.run_command('seasonal-wildlife', 'enable'); print('eco toolenable on=1')",
          "lua:dfhack.run_command('seasonal-wildlife', 'groups', 'on'); print('eco groupson ok=1')",
          "lua:dfhack.run_command('seasonal-wildlife', 'v7', 'layer_groups', 'on'); print('eco swv7 key=layer_groups value=on')",
          "cfg enabled v7.layer_groups", "check:cfg[path=enabled].value==true", "check:cfg[path=v7.layer_groups].value==true",
          "groups3 base", "ecostate", "watch"]
    for i in range(1, 11):
        st += ["step:5040", f"groups3 t{i * 5040}", "ecostate"]
        if i == 5: st.append(SUSTAIN)
    return dict(steps=st, ticks=10, post=["lua:dfhack.run_command('seasonal-wildlife', 'disable'); print('eco tooldisable ok=1')"])

def _b1_blocks(path=ROOT / "data/forts/b1-forts.tsv"):
    if not path.exists():
        return
    rows = [l.rstrip("\n").split("\t") for l in path.read_text().splitlines() if l.strip()]
    if not rows:
        return
    head = rows[0]
    for r in rows[1:]:
        d = dict(zip(head, r))
        if d.get("save") and d.get("status", "ok") == "ok":
            BLOCKS[f"B1BASE_{d['save']}"] = dict(fort=d["save"], spot=d.get("spot") or "land",
                                                  cells={"baseline": b1base()}, wipe=False,
                                                  wipe_why="natural arrivals on a fresh test fort are the subject")
_b1_blocks()

# Alpha Four section 7 (experiments/ALPHA4-SECTION7.md): the S7_ blocks live in their own module; this only adds them.
import alpha4_sec7_blocks  # noqa: E402
alpha4_sec7_blocks.register(BLOCKS)

if __name__ == "__main__":
    sys.exit(main())
