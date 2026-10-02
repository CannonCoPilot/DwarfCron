"""Alpha Four section 7: the eco-run blocks that check what the walkthrough cannot (experiments/ALPHA4-SECTION7.md).

Registered into eco-run.py's BLOCKS by the hook at the end of eco-run.py (`register`), so every block runs under the
v7.1 harness defaults (HARNESS-v71.md): n = 5 reps per arm, a fresh load per arm (restore .preverify, restart DF,
load), counterbalanced order, every animal wiped before a cell places anything (R15), manipulation checks that abort
the block (H2), placed units keep DF's roaming flag (H4). scripts/alpha4-sec7.py runs them in sequence.

The fort is RinghatchetsReady in world region9 (memory test-world-region9: 8x8, several biomes, a lake and a river,
caverns dug and revealed, a trade depot). SEC7_FORT overrides it. Facts the blocks depend on -- which cavern holds a
civ race, how many ticks to the next season, the region's savagery, extinct rows in the embark -- are read once by
`alpha4-sec7.py --only FACTS` into data/alpha4-sec7/facts.json; without that file the defaults below stand (the dry run
uses them).

Block names start with S7_. Tiers: CORE (answers each section 7 row at its shortest), FULL (the stream notes' other
rig tests), OCEAN (needs a region9 shore embark: b1-forts.py embark --only shore).

Conventions:
  * cx-sec7 verbs run through `lua:dfhack.run_script('cx-sec7', ...)` (S7 below); every one prints 'eco ...' rows.
  * placement at a water body or a cavern goes through `cx-sec7 at SPOT ...`, which resolves the spot in game and
    fills <X> <Y> <Z>; eco-run's own {X} {Y} {Z} is the block's land spot.
  * no single step is longer than 3,000 ticks: cx-lifecycle `step` stops at 120 s whatever was asked (eco-run passes no
    seconds), so a 36,000-tick step at 200 t/s would silently end at 24,000 (a trap found while building this).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORT = os.environ.get("SEC7_FORT", "RinghatchetsReady")
OCEAN_FORT = os.environ.get("SEC7_OCEAN_FORT", "")          # a region9 shore 1x1, when one exists
FACTS = ROOT / "data/alpha4-sec7/facts.json"
CHUNK = 3000

SUSTAIN = "lua:dfhack.run_command('cx-load','sustain'); print('eco sustain ok=1')"


def facts() -> dict:
    d = {"to_season": 33600, "civ_cavern": 1, "pred_cavern": 1, "ap_cavern": 0, "ap_token": "", "savagery": 50,
         "extinct_in_embark": 0, "extinct_apex": 0, "bodies": ["lake", "river"],
         # what the fort offers (the runner skips a block whose condition is false); the defaults are the
         # RinghatchetsReady description in memory test-world-region9, until FACTS has read the fort itself
         "has_lake": True, "has_river": True, "has_civ": True, "has_ap": False, "has_cavern_natives": True,
         "calm": True, "has_ocean": False}
    try:
        d.update(json.loads(FACTS.read_text()).get("derived", {}))
    except (OSError, ValueError):
        pass
    return d


F = facts()


# ------------------------------------------------------------------------------------------------ step helpers --
def _lq(x) -> str:
    return "'" + str(x).replace("\\", "\\\\").replace("'", "\\'") + "'"


def S7(verb, *a) -> str:
    """A cx-sec7 verb as an eco-run lua: step (its 'eco ...' rows are kept and checked)."""
    return "lua:dfhack.run_script(" + ",".join(_lq(x) for x in (verb, *a)) + ")"


def T(*words) -> str:
    """A seasonal-wildlife verb, its first reply line as an 'eco tool' receipt."""
    return S7("tool", *words)


def TA(*words) -> str:
    """A seasonal-wildlife verb, every reply line as 'eco toolline' rows (status tables)."""
    return S7("toolall", *words)


def AT(spot, *cxeco) -> str:
    """A cx-eco verb at a spot cx-sec7 resolves in game (lake:shore, river:water, cav2, ...); <X> <Y> <Z> filled there."""
    return S7("at", spot, *cxeco)


def CFG(*pairs) -> str:
    """Write config paths the way the verbs do (loadConfig/saveConfig); the H2 read-back is the `cfg` step after it."""
    return S7("cfgset", *[str(p).lower() if isinstance(p, bool) else p for p in pairs])


def readback(*paths) -> str:
    return "cfg " + " ".join(paths)


def chk(spec) -> str:
    return "check:" + spec


def steps_of(total, chunk=CHUNK):
    """Split `total` ticks into step: rows no longer than `chunk`, yielding (step row, elapsed after it)."""
    t = 0
    while t < total:
        n = min(chunk, total - t)
        t += n
        yield f"step:{n}", t


ENABLE = [T("enable"), T("groups", "on")]


def wipe_off(block, why):
    block["wipe"] = False
    block["wipe_why"] = why
    return block


# ======================================================================= 1. skill writes act and do not rust ==
# SKL1/SKL2 (ecology.md): the package writes NATURAL_SKILL on the caste (new arrivals) and the soul (units already on
# the map), with the rust floor (natural_skill_lvl). Pre units are placed BEFORE the write, post units after it and
# read before any ecology pass reaches them, so a post unit at level got it from the caste alone. Rust: DF's own rust
# clock is ~30,000 ticks of disuse; the shortcut pushes the skill's disuse counters by 200,000 and reads 1,200 and
# 6,000 ticks later. The positive control (pkg_nofloor) zeroes the floor first: if no SNEAK drops there either, the
# shortcut did not make DF rust and the floor result is vacuous.
def skl(arm):
    pkg = arm != "nopkg"
    st = [SUSTAIN, "spawn COUGAR 2 {X} {Y} {Z} 3", "spawn WOLF 3 {X+6} {Y} {Z} 3", S7("mark", "pre"),
          T("v7", "solo", "on" if pkg else "off"), T("hunters", "pack", "on" if pkg else "off"),
          *ENABLE, T("groups", "ecology", "now"),
          readback("v7.solo", "hunters.pack_on"),
          chk(f"cfg[path=v7.solo].value=={'true' if pkg else 'false'}"),
          chk(f"cfg[path=hunters.pack_on].value=={'true' if pkg else 'false'}"),
          "spawn COUGAR 2 {X+20} {Y} {Z} 3", "spawn WOLF 3 {X+26} {Y} {Z} 3",
          S7("skills", "COUGAR", "SNEAK", "t0"), S7("skills", "WOLF", "SNEAK", "t0"),
          chk("skillsum[tag=t0,token=COUGAR].units>0"), chk("skillsum[tag=t0,token=WOLF].pre>0"),
          "step:2000", S7("skills", "COUGAR", "SNEAK", "t2000"), S7("skills", "WOLF", "SNEAK", "t2000")]
    if arm == "pkg_30k":   # FULL: DF's own rust clock, no shortcut
        for s, t in steps_of(30000):
            st += [s, S7("skills", "COUGAR", "SNEAK", f"r{t}"), S7("skills", "WOLF", "SNEAK", f"r{t}")]
            if t % 15000 == 0:
                st.append(SUSTAIN)
        return dict(steps=st, ticks=10)
    if arm == "pkg_nofloor":
        st += [S7("nofloor", "COUGAR", "SNEAK"), S7("nofloor", "WOLF", "SNEAK"), chk("nofloor.units>0")]
    st += [S7("rustpush", "COUGAR", "SNEAK", "200000"), S7("rustpush", "WOLF", "SNEAK", "200000"), chk("rustpush.units>0"),
           "step:1200", S7("skills", "COUGAR", "SNEAK", "r1200"), S7("skills", "WOLF", "SNEAK", "r1200"),
           "step:4800", S7("skills", "COUGAR", "SNEAK", "r6000"), S7("skills", "WOLF", "SNEAK", "r6000")]
    return dict(steps=st, ticks=10)


# ======================================================================= 2. packs, stoops and fishing change kills ==
def pk2(arm):
    on = arm == "pack_on"
    st = [SUSTAIN, T("hunters", "pack", "on" if on else "off"), *ENABLE,
          readback("hunters.pack_on"), chk(f"cfg[path=hunters.pack_on].value=={'true' if on else 'false'}"),
          "spawn WOLF 5 {X} {Y} {Z} 3", "spawn WATER_BUFFALO 6 {X+12} {Y} {Z} 4",
          T("groups", "ecology", "now"), S7("packs", "WOLF", "t0"), "relcount WOLF WATER_BUFFALO"]
    if on:   # R41's recognition and the floor relation are the manipulation: without them the arm is the off arm
        st += [chk("packs[tag=t0].largest>=5"), chk("relcount.pairs>0")]
    st.append("watch")
    for s, t in steps_of(6000):
        st += [s, "relcount WOLF WATER_BUFFALO"]
    return dict(steps=st, ticks=10, nowatch=True)


def stp1(arm):
    on = arm == "stoop_on"
    st = [SUSTAIN, T("hunters", "raptors", "on"), T("hunters", "stoop", "on" if on else "off"),
          T("groups", "ecology", "cadence", "1000"), *ENABLE,
          readback("hunters.stoop.enabled", "hunters.raptors", "ecology.cadence"),
          chk(f"cfg[path=hunters.stoop.enabled].value=={'true' if on else 'false'}"),
          chk("cfg[path=ecology.cadence].value==1000"),
          "spawn BIRD_EAGLE 2 {X} {Y} {Z} 2", "spawn RABBIT 6 {X+20} {Y} {Z} 4", "spawn DEER 3 {X+25} {Y+6} {Z} 3",
          S7("mark", "pre"), "watch"]
    for s, t in steps_of(6000, 1000):
        st += [s, S7("ledger", "eco", f"t{t}")]
    st += ["relcount BIRD_EAGLE RABBIT", "relcount BIRD_EAGLE DEER", TA("hunters", "status")]
    return dict(steps=st, ticks=10, nowatch=True)


def fsh3(arm):
    on = arm == "fish_on"
    st = [SUSTAIN, T("v7", "fishers", "on" if on else "off"), T("hunters", "fish", "run", "SpSuAuWi"),
          T("curious", "BEAR_GRIZZLY", "resident"), *ENABLE,
          readback("v7.fishers", "hunters.fish.run"), chk(f"cfg[path=v7.fishers].value=={'true' if on else 'false'}"),
          AT("river:shore", "spawn", "BEAR_GRIZZLY", "2", "<X>", "<Y>", "<Z>", "2", "land", "any", "200000", "roam"),
          AT("river:water", "spawn", "FISH_PIKE", "8", "<X>", "<Y>", "<Z>", "4", "water", "any", "200000", "roam"),
          "watch"]
    for s, t in steps_of(6000, 300):
        st += [s, S7("adj", "BEAR_GRIZZLY", "FISH_PIKE", f"t{t}")]
    st += [S7("ledger", "eco", "end"), TA("hunters", "status")]
    return dict(steps=st, ticks=10, nowatch=True)


def fsh4(arm):
    st = [SUSTAIN, T("v7", "fishers", "on"), T("v7", "fish_breathe", "off"), T("hunters", "fish", "polar", "on"),
          T("hunters", "fish", "run", "SpSuAuWi"), T("curious", "BEAR_POLAR", "resident"), *ENABLE,
          readback("v7.fishers", "v7.fish_breathe", "hunters.fish.polar"),
          chk("cfg[path=v7.fish_breathe].value==false"), chk("cfg[path=hunters.fish.polar].value==true"),
          AT("lake:shore", "spawn", "BEAR_POLAR", "2", "<X>", "<Y>", "<Z>", "2", "land", "any", "200000", "roam"),
          AT("lake:water", "spawn", "FISH_PIKE", "8", "<X>", "<Y>", "<Z>", "4", "water", "any", "200000", "roam"),
          "watch"]
    for s, t in steps_of(6000, 600):
        st += [s, S7("swim", "BEAR_POLAR", f"t{t}"), S7("adj", "BEAR_POLAR", "FISH_PIKE", f"t{t}")]
    return dict(steps=st, ticks=10, nowatch=True)


# ======================================= 3/4/9/10/11/12. natural arrivals: clock, cavern gate, water, apex, ladder ==
# One block, two arms, natives as the subject (no wipe). The v7.1 targets are absolute, so the def arm alone judges
# them: land groups mean in [cap-1.5, cap] (G2r); per-cavern mean <= 5.5, max <= 6 (CAVG); water groups per body mean
# >= 3 (WAT5, F2); apex presence near 25% (APX1); carnivore share of land units near 20% (LAD1); per-species water
# shares (MIX1). The v70 arm turns every one of those levers back to its v7.0 path AT ONCE: one contrast for the lot
# (the per-lever arms are FULL tier). Length: 36,000 ticks, or to the next season change + 3,000 when that is longer
# (F2's borrowed seasons given back at the change), sampled every 3,000.
V70_LEVERS = ("groups.adaptive", "false", "groups.cavern", "false", "water.land_aquatic", "false", "water.retry_days", "5",
              "water.mix.enabled", "false", "water.pull.enabled", "false", "water.spill.enabled", "false",
              "roster.apex.enabled", "false", "roster.units", "false", "extinct.fix", "false")
LEVER_ARMS = {"clock_legacy": ("groups.adaptive", "false"), "gate_off": ("groups.cavern", "false"),
              "water_v70": ("water.land_aquatic", "false", "water.retry_days", "5"), "spill_off": ("water.spill.enabled", "false"),
              "mix_off": ("water.mix.enabled", "false"), "apex_off": ("roster.apex.enabled", "false"),
              "units_off": ("roster.units", "false"), "extinct_off": ("extinct.fix", "false")}
NAT_TICKS = max(36000, min(60000, int(F["to_season"]) + 3000))


def nat(arm):
    levers = () if arm == "def" else (V70_LEVERS if arm == "v70" else LEVER_ARMS[arm])
    st = [SUSTAIN, T("preset")]
    if levers:
        st.append(CFG(*levers))
    st += [T("roster", "build", "land"), T("roster", "build", "water"), T("roster", "build", "cavern"), *ENABLE,
           readback("enabled", "groups.adaptive", "groups.cavern", "water.spill.enabled", "water.mix.enabled",
                    "roster.apex.enabled", "roster.units", "extinct.fix"),
           chk("cfg[path=enabled].value==true")]
    want = dict(zip(levers[::2], levers[1::2]))
    for p in ("groups.adaptive", "groups.cavern", "water.spill.enabled", "roster.apex.enabled", "roster.units"):
        st.append(chk(f"cfg[path={p}].value=={want.get(p, 'true')}"))
    st += [S7("mark", "pre"), S7("nat", "t0"), chk("nat[tag=t0].land_cap>0"), "groups3 base"]
    for s, t in steps_of(NAT_TICKS):
        st += [s, S7("nat", f"t{t}")]
        if arm == "def":   # R44's manipulation check: a held species reads FREQUENCY 1 while its cavern is full
            st.append(chk(f"hold[tag=t{t}].held_not_1==0"))
        if t % 6000 == 0:
            st.append(f"groups3 t{t}")
        if t % 15000 == 0:
            st.append(SUSTAIN)
    st += [S7("ledger", "season", "end"), S7("ledger", "wave", "end"), S7("ledger", "build", "end"),
           TA("water"), TA("roster", "apex"), TA("groups", "layers")]
    return dict(steps=st, ticks=10, nowatch=True, post=[T("disable")])


def trim(arm):
    st = [SUSTAIN, T("preset"), *ENABLE, T("groups", "cavern", "on"), T("groups", "cavern", "cap", "1"),
          T("groups", "cavern", "trim", "on"), readback("groups.cavern_cap", "groups.cavern_trim"),
          chk("cfg[path=groups.cavern_cap].value==1"), chk("cfg[path=groups.cavern_trim].value==true"), S7("nat", "t0")]
    for s, t in steps_of(3600, 300):
        st += [s, S7("trim", f"t{t}")]
        if t == 1200:   # a trim must have happened by the second groups pass, or the arm is vacuous
            st.append(chk(f"trim[tag=t{t}].trimmed>0"))
    return dict(steps=st, ticks=10, nowatch=True, post=[T("disable")])


# ======================================================================= 5. a lost leader makes the group scatter ==
def pan1(arm):
    on = arm == "panic_on"
    st = [SUSTAIN, T("groups", "panic", "on" if on else "off"), T("groups", "cohesion", "on"), *ENABLE,
          readback("groups.panic", "groups.cohesion"), chk(f"cfg[path=groups.panic].value=={'true' if on else 'false'}"),
          "spawn DEER 1 {X} {Y} {Z} 2 land male", "spawn DEER 5 {X} {Y} {Z} 4 land female", "adopt DEER",
          "step:300", S7("grp", "DEER", "t0"), chk("grp[tag=t0].leader_male==1"), chk("grp[tag=t0].members>=6"),
          S7("mark", "pre"), S7("killleader", "DEER"), chk("kill.killed==1"), "step:100", S7("grp", "DEER", "t100")]
    for d, t in ((200, 300), (900, 1200), (1200, 2400)):
        st += [f"step:{d}", S7("grp", "DEER", f"t{t}"), S7("ledger", "panic", f"t{t}")]
    return dict(steps=st, ticks=10, nowatch=True)


def coht(arm):
    on = arm == "led"
    st = [SUSTAIN, T("groups", "cohesion", "on" if on else "off"), *ENABLE,
          readback("groups.cohesion"), chk(f"cfg[path=groups.cohesion].value=={'true' if on else 'false'}"),
          AT("lake:water", "spawn", "FISH_PIKE", "8", "<X>", "<Y>", "<Z>", "3", "water", "any", "200000", "roam"),
          "adopt FISH_PIKE", "step:200", S7("grp", "FISH_PIKE", "t0")]
    if on:
        st.append(chk("grp[tag=t0].leader>=0"))
    for s, t in steps_of(3000, 300):
        st += [s, S7("grp", "FISH_PIKE", f"t{t}"), S7("swim", "FISH_PIKE", f"t{t}")]
    st.append(S7("wat", "end"))
    return dict(steps=st, ticks=10, nowatch=True)


# ======================================================================= 6. irruption tokens act ==
# M1-M8 (irruption.md section 13 phase 1): the probed token alone at 100% against a wave with every token off, same
# draw. One civ wave of 4-6 in cavern CIV (facts), agitation off (the tokens are the subject), pauses and zoom off so
# the rig keeps stepping, `irruption now`. Receipt: subjects on the map at t0 with their written fields read back.
CIV = int(F.get("civ_cavern") or F.get("pred_cavern") or 1)
IRR_BASE = ("irruption.enabled", "true", "irruption.need_breach", "false", "irruption.agitate", "false",
            "irruption.champion", "false", "irruption.pause.start", "false", "irruption.pause.wave", "false",
            "irruption.pause.warn", "false", "irruption.zoom", "false", "irruption.popup", "false",
            "irruption.waves", "1", "irruption.size_min", "4", "irruption.size_cap", "6")
TOKENS = ("crazed", "rage", "thief", "sneak", "wander", "meander", "linger", "mischief", "nofear", "ambush", "trance")


def _tokens_only(on):
    pairs = []
    for t in TOKENS:
        pairs += [f"irruption.tokens.{t}.on", "true" if t in on else "false", f"irruption.tokens.{t}.pct", "100" if t in on else "10"]
    return pairs


def irr_m(arm):
    tok = {"none": (), "crazed": ("crazed",), "thief": ("thief", "meander"), "goalonly": (), "mischief": ("mischief",),
           "sneak": ("sneak",), "sneak_rehide": ("sneak",), "wander": ("wander",), "wander_surge": ("wander",)}[arm]
    extra = []
    if arm == "crazed":
        extra = ["irruption.reassert", "false"]   # M1 decides whether reassert is needed: off, so DF's own hold shows
    if arm == "sneak_rehide":
        extra = ["irruption.rehide", "true"]
    if arm == "wander_surge":
        extra = ["irruption.surge", "true"]
    st = [SUSTAIN, T("preset"), *ENABLE, CFG(*IRR_BASE, *_tokens_only(tok), *extra),
          readback("irruption.enabled", "irruption.need_breach", "irruption.agitate", "irruption.size_cap"),
          chk("cfg[path=irruption.enabled].value==true"), chk("cfg[path=irruption.agitate].value==false")]
    for t in tok:
        st += [readback(f"irruption.tokens.{t}.pct"), chk(f"cfg[path=irruption.tokens.{t}.pct].value==100")]
    if arm == "thief":
        st.append(S7("native", str(CIV), "*", "pre"))
    st += [T("irruption", "now", str(CIV)), "step:20", S7("irr", str(CIV), "t0"), chk("irr[tag=t0].alive>0")]
    if arm == "goalonly":
        st += [S7("subjects", str(CIV), "goal"), chk("subjects.units>0")]
    st += ["watch"]
    every = 100 if arm == "crazed" else 300
    for s, t in steps_of(3000, every):
        st += [s, S7("irr", str(CIV), f"t{t}")]
        if arm == "thief" and t in (100, 3000):
            st.append(S7("native", str(CIV), "*", f"t{t}"))
    if arm == "crazed":   # M1: the mask after a save and reload
        st += ["read:pre_reload", "save:S7_M1_TMP", "load:S7_M1_TMP", S7("irr", str(CIV), "reload"), "step:300",
               S7("irr", str(CIV), "reload300")]
    st += [S7("civs", str(CIV), "end"), S7("resid", "end")]
    return dict(steps=st, ticks=10, nowatch=True)


# Phase 2: A rotation only (irruption off), B irruption with every token off, C the R10 package (defaults). The
# pressure is pinned at the threshold, the warning is 0.1 day, waves 0.5 day apart, 5 days long. Every civ unit in
# the band is sampled every 600 ticks (the notes ask 300; 600 halves the RPC time) for 7,200 ticks.
def irr_p2(arm):
    st = [SUSTAIN, T("preset"), *ENABLE]
    if arm == "A":
        st += [CFG("irruption.enabled", "false"), readback("irruption.enabled"), chk("cfg[path=irruption.enabled].value==false")]
    else:   # B: every token off; C and D: the R10 package as shipped (each token on at 10%, a champion)
        pairs = _tokens_only(()) if arm == "B" else []
        st += [CFG("irruption.enabled", "true", "irruption.need_breach", "false", "irruption.pause.start", "false",
                   "irruption.pause.wave", "false", "irruption.pause.warn", "false", "irruption.zoom", "false",
                   "irruption.popup", "false", "irruption.warn_min_days", "0.1", "irruption.warn_max_days", "0.1",
                   "irruption.spacing_min_days", "0.5", "irruption.spacing_max_days", "0.5", "irruption.duration_days", "5",
                   *(["irruption.agitate", "false"] if arm == "D" else []), *pairs),
               readback("irruption.enabled", "irruption.duration_days"), chk("cfg[path=irruption.enabled].value==true"),
               chk("cfg[path=irruption.duration_days].value==5"), S7("pin", str(CIV)), chk("pin.ok==1")]
    st += [S7("civs", str(CIV), "t0"), "watch"]
    for s, t in steps_of(7200, 600):
        st += [s, S7("irr", str(CIV), f"t{t}"), S7("civs", str(CIV), f"t{t}")]
        if arm != "A" and t == 1200:
            st.append(chk(f"irr[tag=t{t}].alive>0"))
        if t == 3600:
            st.append(SUSTAIN)
    st.append(S7("resid", "end"))
    return dict(steps=st, ticks=10, nowatch=True)


# Phase 3 (T-*): an event, then its end by each route, then the residual-write scan (0 masks, 0 cache bits beyond the
# caste's own). T-SAVE: save and reload mid-event, then the record and the writes again.
def irr_t(arm):
    st = [SUSTAIN, T("preset"), *ENABLE, CFG(*IRR_BASE, *_tokens_only(("crazed", "thief", "sneak", "mischief")),
                                             "irruption.duration_days", "1" if arm == "end_duration" else "5"),
          readback("irruption.enabled"), chk("cfg[path=irruption.enabled].value==true"),
          T("irruption", "now", str(CIV)), "step:20", S7("irr", str(CIV), "t0"), chk("irr[tag=t0].alive>0"), "step:280"]
    route = {"end_duration": ["step:1200"],
             "end_repel": [S7("subjects", str(CIV), "kill"), chk("subjects.units>0"), "step:600"],
             "end_verb": [T("irruption", "end", str(CIV)), "step:100"],
             "off_irruption": [T("irruption", "off"), "step:100"],
             "off_disable": [T("disable"), "step:100"],
             "off_alloff": ["lua:local sw=reqscript('seasonal-wildlife'); local ok=pcall(sw.PANEL.restoreAll, 'sec7'); print('eco alloff ok='..(ok and 1 or 0))", "step:100"],
             "off_groups": [T("groups", "off"), "step:100"],
             "save": ["save:S7_TSAVE_TMP", "load:S7_TSAVE_TMP", S7("irr", str(CIV), "reload"), "step:600",
                      S7("irr", str(CIV), "reload600")]}[arm]
    st += route + [S7("irr", str(CIV), "end"), S7("resid", "end")]
    return dict(steps=st, ticks=10, nowatch=True)


# CORE shortcut for the routes above: one load, the routes in sequence, a residual scan after each. A route that
# leaves writes shows at once (the scan before it read 0), so the sequence attributes each residue to its route; the
# cost is that a later route starts on a fort that already held an event (cooled with `irruption cool`).
def irr_tseq(arm):
    cav = str(CIV)
    st = [SUSTAIN, T("preset"), *ENABLE, CFG(*IRR_BASE, *_tokens_only(("crazed", "thief", "sneak", "mischief")),
                                             "irruption.duration_days", "1", "irruption.cooldown_days", "0"),
          readback("irruption.enabled"), chk("cfg[path=irruption.enabled].value==true")]

    def event(tag):
        return [T("irruption", "cool", cav), CFG("irruption.enabled", "true"), T("irruption", "now", cav), "step:20",
                S7("irr", cav, f"{tag}_t0"), chk(f"irr[tag={tag}_t0].alive>0"), "step:280"]
    routes = [("end_duration", ["step:1200"]),
              ("end_repel", [S7("subjects", cav, "kill"), "step:600"]),
              ("end_verb", [T("irruption", "end", cav), "step:100"]),
              ("off_irruption", [T("irruption", "off"), "step:100"]),
              ("off_disable", [T("disable"), "step:100", *ENABLE]),
              ("off_groups", [T("groups", "off"), "step:100", T("groups", "on")]),
              ("off_alloff", ["lua:local sw=reqscript('seasonal-wildlife'); local ok=pcall(sw.PANEL.restoreAll, 'sec7'); print('eco alloff ok='..(ok and 1 or 0))",
                              "step:100", *ENABLE]),
              ("save", ["save:S7_TSEQ_TMP", "load:S7_TSEQ_TMP", S7("irr", cav, "save_reload"), "step:600", S7("irr", cav, "save_reload600"),
                        T("irruption", "end", cav), "step:100"])]
    for name, steps in routes:
        st += event(name) + steps + [S7("irr", cav, f"{name}_end"), S7("resid", name)]
    return dict(steps=st, ticks=10, nowatch=True)


# T-R35: an animal-people species' wave size in an irrupting cavern vs a quiet one (apcap 5 lifted during the event)
AP_CAV, AP_TOKEN = int(F.get("ap_cavern") or 0), F.get("ap_token") or ""


def irr_r35(arm):
    cav = AP_CAV or CIV
    st = [SUSTAIN, T("preset"), *ENABLE, T("groups", "apcap", "5"), readback("groups.apcap"), chk("cfg[path=groups.apcap].value==5")]
    if arm == "irrupting":
        st += [CFG(*IRR_BASE, "irruption.species", AP_TOKEN or "auto", "irruption.size_cap", "20"),
               T("irruption", "now", str(cav), AP_TOKEN) if AP_TOKEN else T("irruption", "now", str(cav))]
    else:
        st += [T("call", f"cavern:{AP_TOKEN}") if AP_TOKEN else T("call", "cavern")]
    for s, t in steps_of(1200, 300):
        st += [s, S7("gsize", AP_TOKEN or "-", f"t{t}")]
    st.append(chk(f"gsize[tag=t1200].groups>0"))
    return dict(steps=st, ticks=10, nowatch=True)


# T-PR (FULL): pressure from real sources, threshold lowered to 0.3 (shortcut: the order of the sources, not their
# absolute days); days to warning read off the phase every 600 ticks.
def irr_pr(arm):
    st = [SUSTAIN, T("preset"), *ENABLE, CFG("irruption.enabled", "true", "irruption.threshold", "0.3",
                                            "irruption.need_breach", "false", "irruption.pause.warn", "false",
                                            "irruption.pause.start", "false", "irruption.zoom", "false"),
          readback("irruption.threshold"), chk("cfg[path=irruption.threshold].value==0.3")]
    st += {"cit_in": [S7("citizens", str(CIV), "3", "in", "knock"), chk("citizens.moved>0")],
           "cit_above": [S7("citizens", str(CIV), "3", "above", "knock"), chk("citizens.moved>0")],
           "dig": [S7("dig", str(CIV), "20"), chk("dig.marked>0")], "none": []}[arm]
    for s, t in steps_of(7200, 600):
        st += [s, S7("irr", str(CIV), f"t{t}")]
    return dict(steps=st, ticks=10, nowatch=True)


# ======================================================================= 7. scavenging takes days; swimmers eat ==
def scv3(arm):
    nat_on = arm == "natural"
    st = [SUSTAIN, *ENABLE, T("scavenge", "on"), T("scavenge", "natural", "on" if nat_on else "off"),
          readback("scavenge.enabled", "scavenge.natural"), chk("cfg[path=scavenge.enabled].value==true"),
          chk(f"cfg[path=scavenge.natural].value=={'true' if nat_on else 'false'}"),
          "spawn KANGAROO 6 {X} {Y} {Z} 2", "corpse {ids:KANGAROO}", "step:50", "items {X} {Y} {Z} 6 t0",
          chk("items[tag=t0].corpses>0"),
          "spawn JACKAL 2 {X+12} {Y} {Z} 2", "spawn BIRD_VULTURE 2 {X+12} {Y+3} {Z} 2", "spawn HYENA 1 {X+12} {Y-3} {Z} 2",
          S7("scav", "t0")]
    for s, t in steps_of(7200, 600):
        st += [s, S7("scav", f"t{t}"), f"items {{X}} {{Y}} {{Z}} 6 t{t}"]
    st.append(TA("scavenge", "stats"))
    return dict(steps=st, ticks=10, nowatch=True, post=[T("disable")])


def scv3w(arm):
    swim = arm == "swimmer"
    st = [SUSTAIN, *ENABLE, T("scavenge", "on"), T("scavenge", "swimmers", "on" if swim else "off"),
          T("hunters", "swimscav", "on"),
          readback("scavenge.swimmers"), chk(f"cfg[path=scavenge.swimmers].value=={'true' if swim else 'false'}"),
          AT("lake:water", "spawn", "FISH_CARP", "6", "<X>", "<Y>", "<Z>", "2", "water", "any", "200000", "roam"),
          S7("corpses", "FISH_CARP"), chk("corpse.drained>0"),
          AT("lake:water", "spawn", "POND_GRABBER", "2", "<X+10>", "<Y>", "<Z>", "2", "water", "any", "200000", "roam"),
          S7("scav", "t0")]
    for s, t in steps_of(7200, 600):
        st += [s, S7("scav", f"t{t}"), S7("swim", "POND_GRABBER", f"t{t}")]
    st.append(TA("scavenge", "stats"))
    return dict(steps=st, ticks=10, nowatch=True, post=[T("disable")])


# FULL: SCV3J (own vs borrowed entry, walk only), SCV3F (vulture walk only vs default), CBX2 (curious reform)
def scv3j(arm):
    ref = "ref=site" if arm == "own" else "ref=first"
    st = [SUSTAIN, *ENABLE, T("scavenge", "on"), T("scavenge", "set", "hop_max", "0"), readback("scavenge.hop_max"),
          chk("cfg[path=scavenge.hop_max].value==0"), "spawn KANGAROO 6 {X} {Y} {Z} 2", "corpse {ids:KANGAROO}",
          f"spawn JACKAL 4 {{X+12}} {{Y}} {{Z}} 2 land any 200000 {ref}"]
    for s, t in steps_of(7200, 600):
        st += [s, S7("scav", f"t{t}")]
    return dict(steps=st, ticks=10, nowatch=True, post=[T("disable")])


def scv3f(arm):
    st = [SUSTAIN, *ENABLE, T("scavenge", "on")]
    if arm == "walk_only":
        st += [T("scavenge", "set", "hop_max", "0"), readback("scavenge.hop_max"), chk("cfg[path=scavenge.hop_max].value==0")]
    st += ["spawn KANGAROO 6 {X} {Y} {Z} 2", "corpse {ids:KANGAROO}", "spawn BIRD_VULTURE 4 {X+20} {Y} {Z} 2"]
    for s, t in steps_of(7200, 600):
        st += [s, S7("scav", f"t{t}")]
    return dict(steps=st, ticks=10, nowatch=True, post=[T("disable")])


def cbx2(arm):
    st = [SUSTAIN, *ENABLE, S7("spot", "fort")]
    if arm == "reform_off":
        st += [T("curious", "reform", "off"), readback("curious.reform"), chk("cfg[path=curious.reform].value==false")]
    elif arm == "resident":
        st += [T("curious", "RACCOON", "resident")]
    else:
        st += [readback("curious.reform"), chk("cfg[path=curious.reform].value==true")]
    st += [AT("fort", "spawn", "RACCOON", "4", "<X+12>", "<Y>", "<Z>", "2", "land", "any", "200000", "roam")]
    for s, t in steps_of(12000, 600):
        st += [s, S7("swim", "RACCOON", f"t{t}"), TA("curious", "status")]
    return dict(steps=st, ticks=10, nowatch=True, post=[T("disable")])


# ======================================================================= 8. vermin eaters eat what they walk to ==
# VF1 (vermin.md): BADGER x4 and GRASSHOPPER x20 (SWV_GROUND_BUG) 15 tiles apart; forage off vs on (budget 8, chance 1,
# cooldown 600). The fort's pets are wiped too (VRM3b: cats ate placed vermin). VF4: BIRD_DUCK at the river bank
# against the river's own fish vermin.
def _vrm_inline(name, **kw):
    lua = ROOT / "data/eco-desk/v2/research/lua" / name
    s = " ".join(l.strip() for l in lua.read_text().splitlines() if l.strip() and not l.strip().startswith("--"))
    for k, v in kw.items():
        s = s.replace("{" + k + "}", str(v))
    return "lua:" + s


def _forage(on):
    if not on:
        return [T("vermin", "forage", "off"), readback("vermin_eat.forage"), chk("cfg[path=vermin_eat.forage].value==false")]
    return [T("vermin", "forage", "on"), T("vermin", "forage", "budget", "8"), T("vermin", "forage", "chance", "1"),
            T("vermin", "forage", "cooldown", "600"), readback("vermin_eat.forage", "vermin_eat.chance"),
            chk("cfg[path=vermin_eat.forage].value==true"), chk("cfg[path=vermin_eat.chance].value==1")]


def vf1(arm):
    on = arm == "forage_on"
    st = [SUSTAIN, *ENABLE, *_forage(on),
          _vrm_inline("vermin_create.lua", RACE="GRASSHOPPER", N=20, R=5, X="{X+15}", Y="{Y}", Z="{Z}"),
          chk("vcreate.made>=10"), "spawn BADGER 4 {X} {Y} {Z} 2"]
    if on:
        st.append(T("vermin", "forage", "now"))
    for s, t in steps_of(3000, 500):
        st += [s, _vrm_inline("vermin_count.lua", RACE="GRASSHOPPER", R=8, TAG=f"t{t}", X="{X+15}", Y="{Y}", Z="{Z}")]
    st.append(TA("vermin", "eats"))
    return dict(steps=st, ticks=10, nowatch=True, post=[T("disable")])


def vf4(arm):
    on = arm == "forage_on"
    st = [SUSTAIN, *ENABLE, *_forage(on), AT("river:shore", "vermin", "<X>", "<Y>", "<Z>", "12", "t0"), chk("vermin[tag=t0].total>0"),
          AT("river:shore", "spawn", "BIRD_DUCK", "4", "<X+10>", "<Y>", "<Z>", "2", "land", "any", "200000", "roam")]
    if on:
        st.append(T("vermin", "forage", "now"))
    for s, t in steps_of(3000, 500):
        st += [s, AT("river:shore", "vermin", "<X>", "<Y>", "<Z>", "12", f"t{t}")]
    st.append(TA("vermin", "eats"))
    return dict(steps=st, ticks=10, nowatch=True, post=[T("disable")])


# ======================================================================= 9. apex scheduler (INV3) ==
# INV3 (roster.md): INV2 again with the tool placing (R36): Add invasive (addNewSpecies, the GUI's Ctrl+X; the console
# has no verb) of a SAVAGE species on a calm map places it at once. Units present, staying, refunded on departure.
def inv3(arm):
    st = [SUSTAIN, T("preset"), *ENABLE,
          "lua:local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig(); local n, why = sw.addNewSpecies(c, 'CENOZOIC_SMILODON', 50, 100);"
          " sw.saveConfig(c); print(('eco inv added=%s why=%s'):format(tostring(n or 0), (tostring(why):gsub('[%s=]+','_'))))",
          S7("gsize", "CENOZOIC_SMILODON", "t0"), chk("gsize[tag=t0].groups>0")]
    for s, t in steps_of(9000):
        st += [s, S7("gsize", "CENOZOIC_SMILODON", f"t{t}")]
    st.append(TA("roster", "apex"))
    return dict(steps=st, ticks=10, nowatch=True, post=[T("disable")])


# ======================================================================= 10. guard (GRD1) ==
def grd1(arm):
    on = arm == "guard_on"
    st = [SUSTAIN, T("water", "guard", "on" if on else "off"), *ENABLE,
          readback("water.guard.enabled"), chk(f"cfg[path=water.guard.enabled].value=={'true' if on else 'false'}"),
          AT("lake:water", "spawn", "FISH_PIKE", "3", "<X>", "<Y>", "<Z>", "2", "water", "any", "200000", "roam"),
          "adopt FISH_PIKE", "step:50", AT("lake:shore", "tp", "FISH_PIKE", "<X>", "<Y>", "<Z>"), chk("tp.units>0")]
    for s, t in steps_of(1200, 200):
        st += [s, S7("swim", "FISH_PIKE", f"t{t}"), S7("wat", f"t{t}")]
    st.append(S7("ledger", "strand", "end"))
    return dict(steps=st, ticks=10, nowatch=True)


# ======================================================================= 11. extinct corrections ==
def exr1(arm):
    on = arm == "fix_on"
    st = [SUSTAIN, T("extinct", "on" if on else "off"), *ENABLE, readback("extinct.fix"),
          chk(f"cfg[path=extinct.fix].value=={'true' if on else 'false'}"),
          "lua:local c; for _,r in ipairs(df.global.world.raws.creatures.all) do if r.creature_id=='TRIASSIC_EORAPTOR' then c=r end end;"
          " local b=0; if c then for _,cs in ipairs(c.caste) do if cs.flags.BENIGN then b=b+1 end end end;"
          " print('eco benign token=TRIASSIC_EORAPTOR found='..(c and 1 or 0)..' castes_benign='..b)",
          chk("benign.found==1"),
          "spawn TRIASSIC_EORAPTOR 5 {X} {Y} {Z} 3", "spawn HARE 6 {X+8} {Y} {Z} 3", "watch"]
    for s, t in steps_of(6000):
        st += [s, "relcount TRIASSIC_EORAPTOR HARE"]
    return dict(steps=st, ticks=10, nowatch=True)


def exu1(arm):
    before = arm == "placed_before"
    st = [SUSTAIN]
    if before:
        st += ["spawn TRIASSIC_EORAPTOR 5 {X} {Y} {Z} 3", *ENABLE]
    else:
        st += [*ENABLE, "spawn TRIASSIC_EORAPTOR 5 {X} {Y} {Z} 3"]
    st += [readback("extinct.fix", "extinct.units"), chk("cfg[path=extinct.units].value==true"),
           "spawn HARE 6 {X+8} {Y} {Z} 3", "watch"]
    for s, t in steps_of(6000):
        st.append(s)
    return dict(steps=st, ticks=10)


def exf1(arm):
    on = arm == "freq_on"
    st = [SUSTAIN, T("preset"), T("extinct", "set", "freq", "on" if on else "off"), *ENABLE,
          readback("extinct.freq"), chk(f"cfg[path=extinct.freq].value=={'true' if on else 'false'}"), S7("nat", "t0")]
    for s, t in steps_of(30000, 1500):   # shortcut: DF's surface gate released every 1,500 t (SW4's lever)
        st += [s, "lua:dfhack.run_command('cx-probe','release','surface'); print('eco release ok=1')", S7("nat", f"t{t}")]
        if t % 15000 == 0:
            st.append(SUSTAIN)
    return dict(steps=st, ticks=10, nowatch=True, post=[T("disable")])


# ======================================================================= 12. water auto-on (F1) ==
def f1(arm):
    st = [SUSTAIN, CFG("layers.water", "false", "water.layer_set", "false", "water.layer_auto", "true")]
    if arm == "layer_off":
        st.append(T("water", "layer", "off"))
    st += [*ENABLE, readback("layers.water", "water.layer_set"),
           chk(f"cfg[path=layers.water].value=={'false' if arm == 'layer_off' else 'true'}"), S7("mark", "pre"), S7("nat", "t0")]
    for s, t in steps_of(2400, 600):
        st += [s, S7("nat", f"t{t}"), S7("ledger", "*", f"t{t}")]
    return dict(steps=st, ticks=10, nowatch=True, post=[T("disable")])


# ======================================================================= 13. cost of every v7.1 change ==
LEGACY_ALL = ("perf.stagger", "false", *[x for k in ("class", "groups", "undo", "cfg", "overlay", "census", "live", "pool", "survey", "scav")
                                          for x in (f"perf.legacy_{k}", "true")])


def perf1(arm):
    """PERF0 (bench, no time passes) + PERF1 (12,000 t, the shortcut of a 33,600-t month): new paths vs all legacy."""
    st = [SUSTAIN, T("preset")]
    if arm == "legacy":
        st.append(CFG(*LEGACY_ALL))
    st += [*ENABLE, readback("perf.legacy_census", "perf.stagger"),
           chk(f"cfg[path=perf.legacy_census].value=={'true' if arm == 'legacy' else 'false'}"),
           T("perf", "reset"), S7("bench", "20"), chk("bench.failed==0"), S7("perf", "t0")]
    for s, t in steps_of(12000):
        st += [s, S7("perf", f"t{t}")]
    st += [chk("perf[tag=t12000].tps>0"), TA("perf")]
    return dict(steps=st, ticks=10, nowatch=True, post=[T("disable")])


_OVL = ("lua:local ok,pc=pcall(function() return dfhack.internal.getPerfCounters() end); local n=0;"
        " if ok and type(pc)=='table' then for k,v in pairs(pc) do if tostring(k):find('overlay') then"
        " if type(v)=='table' then for k2,v2 in pairs(v) do if tostring(k2):find('seasonal') then n=n+1;"
        " print(('eco ovl key=%s ms=%s'):format(tostring(k2):gsub('[%s=]','_'), tostring(type(v2)=='table' and (v2.ms or v2.total) or v2))) end end end end end end;"
        " print('eco ovlsum ok='..(ok and 1 or 0)..' rows='..n)")


def perf2(arm):
    st = [SUSTAIN, T("preset"), *ENABLE]
    if arm != "overlay_off":
        st.append("lua:dfhack.run_command('overlay','enable','seasonal-wildlife.groups'); print('eco overlay on=1')")
    if arm == "legacy_overlay":
        st.append(CFG("perf.legacy_overlay", "true"))
    st += [readback("perf.legacy_overlay"), chk(f"cfg[path=perf.legacy_overlay].value=={'true' if arm == 'legacy_overlay' else 'false'}"),
           S7("perf", "t0")]
    for s, t in steps_of(6000):
        st += [s, S7("perf", f"t{t}"), _OVL]
    return dict(steps=st, ticks=10, nowatch=True, post=[T("disable")])


def perf4(arm):
    on = arm == "events_on"
    st = [SUSTAIN, "lua:dfhack.run_command('cx-load','citizens','60'); print('eco citizens60 ok=1')",
          "lua:local n=0; for _,u in ipairs(df.global.world.units.active) do if dfhack.units.isCitizen(u) then n=n+1 end end; print('eco cit n='..n)",
          chk("cit.n>=60"), T("preset"), CFG("perf.events", "true" if on else "false"), *ENABLE,
          readback("perf.events"), chk(f"cfg[path=perf.events].value=={'true' if on else 'false'}"), S7("perf", "t0")]
    for s, t in steps_of(10000, 2500):
        st += [s, S7("perf", f"t{t}"), SUSTAIN]
    st.append(TA("perf", "census"))
    return dict(steps=st, ticks=10, nowatch=True, post=[T("disable")])


# PERF3 (OCEAN): A v7 defaults vs B sponges off (layer_groups is retired in v7.1, so B is sponges alone)
def perf3(arm):
    st = [SUSTAIN, T("preset")]
    if arm == "sponges_off":
        st.append(T("v7", "sponges", "off"))
    st += [*ENABLE, readback("v7.sponges"), chk(f"cfg[path=v7.sponges].value=={'false' if arm == 'sponges_off' else 'true'}"), S7("perf", "t0")]
    for s, t in steps_of(12000):
        st += [s, S7("perf", f"t{t}")]
    return dict(steps=st, ticks=10, nowatch=True, post=[T("disable")])


# ======================================================================= OCEAN tier: PELA, PEL1, COHT (orca) ==
def pela(arm):
    on = arm == "pull_on"
    st = [SUSTAIN, T("preset"), T("water", "pull", "on" if on else "off"), T("roster", "build", "water"), *ENABLE,
          readback("water.pull.enabled"), chk(f"cfg[path=water.pull.enabled].value=={'true' if on else 'false'}"),
          T("water", "now", "ocean"), S7("nat", "t0")]
    for s, t in steps_of(20000, 2000):
        st += [s, S7("nat", f"t{t}"), S7("wat", f"t{t}")]
    st += [S7("ledger", "strand", "end"), TA("water", "mix", "ocean")]
    return dict(steps=st, ticks=10, nowatch=True, post=[T("disable")])


def coht_orca(arm):
    on = arm == "led"
    st = [SUSTAIN, T("groups", "cohesion", "on" if on else "off"), *ENABLE, readback("groups.cohesion"),
          chk(f"cfg[path=groups.cohesion].value=={'true' if on else 'false'}"), T("place", "ORCA", "6", "water"),
          S7("gsize", "ORCA", "t0"), chk("gsize[tag=t0].groups>0")]
    for s, t in steps_of(6000, 600):
        st += [s, S7("wat", f"t{t}"), S7("gsize", "ORCA", f"t{t}")]
    return dict(steps=st, ticks=10, nowatch=True, post=[T("disable")])


# ================================================================================================ registration ==
def _blk(cells, tier, item, spot="land", fort=None, wipe=True, why="", livestock=False, requires=None):
    """requires: a facts.json 'derived' key that must be true for the block to say anything on this fort; the runner
    skips the block (and reports the item NOT-TESTABLE-HERE with the reason) when it is false."""
    b = dict(fort=fort or FORT, spot=spot, cells=cells, sec7_tier=tier, sec7_item=item, sec7_requires=requires)
    if livestock:
        b["wipe_livestock"] = True
    return b if wipe else wipe_off(b, why)


def blocks() -> dict:
    B = {}
    B["S7_SKL"] = _blk({a: skl(a) for a in ("pkg", "nopkg", "pkg_nofloor")}, "CORE", 1)
    B["S7_SKL30K"] = _blk({"pkg_30k": skl("pkg_30k")}, "FULL", 1)
    B["S7_PK2"] = _blk({a: pk2(a) for a in ("pack_on", "pack_off")}, "CORE", 2)
    B["S7_STP1"] = _blk({a: stp1(a) for a in ("stoop_on", "stoop_off")}, "CORE", 2)
    B["S7_FSH3"] = _blk({a: fsh3(a) for a in ("fish_on", "fish_off")}, "CORE", 2, requires="has_river")
    B["S7_FSH4"] = _blk({"polar": fsh4("polar")}, "CORE", 2, requires="has_lake")
    nw = "natural arrivals are the subject (G2r, CAVG, WAT5, APX1, LAD1, MIX1, F2)"
    B["S7_NAT"] = _blk({a: nat(a) for a in ("def", "v70")}, "CORE", 3, wipe=False, why=nw)
    B["S7_NATLEV"] = _blk({a: nat(a) for a in LEVER_ARMS}, "FULL", 3, wipe=False, why=nw)
    B["S7_TRIM"] = _blk({"cap1": trim("cap1")}, "CORE", 4, wipe=False, why="the cavern's natives are the subject (trim)",
                        requires="has_cavern_natives")
    B["S7_PAN1"] = _blk({a: pan1(a) for a in ("panic_on", "panic_off")}, "CORE", 5)
    B["S7_COHT"] = _blk({a: coht(a) for a in ("led", "cohesion_off")}, "CORE", 5, requires="has_lake")
    B["S7_IRRM"] = _blk({a: irr_m(a) for a in ("none", "crazed", "thief", "goalonly", "mischief", "sneak", "wander")}, "CORE", 6,
                        requires="has_civ")
    B["S7_IRRM2"] = _blk({a: irr_m(a) for a in ("sneak_rehide", "wander_surge")}, "FULL", 6)
    B["S7_IRRP2"] = _blk({a: irr_p2(a) for a in ("A", "B", "C")}, "CORE", 6, wipe=False,
                         why="the cavern's own civ dwellers are the comparison in arm A", requires="has_civ")
    B["S7_IRRP2D"] = _blk({"D": irr_p2("D")}, "FULL", 6, wipe=False, why="as S7_IRRP2")
    B["S7_IRRTSEQ"] = _blk({"routes": irr_tseq("routes")}, "CORE", 6, requires="has_civ")
    B["S7_IRRT"] = _blk({a: irr_t(a) for a in ("end_duration", "end_repel", "end_verb", "off_irruption", "off_disable",
                                               "off_alloff", "off_groups", "save")}, "FULL", 6,
                     requires="has_civ")
    B["S7_IRRR35"] = _blk({a: irr_r35(a) for a in ("irrupting", "quiet")}, "CORE", 6, wipe=False,
                          why="the cavern's animal-people entries are the subject", requires="has_ap")
    B["S7_IRRPR"] = _blk({a: irr_pr(a) for a in ("cit_in", "cit_above", "dig", "none")}, "FULL", 6)
    B["S7_SCV3"] = _blk({a: scv3(a) for a in ("natural", "sweep")}, "CORE", 7)
    B["S7_SCV3W"] = _blk({a: scv3w(a) for a in ("swimmer", "swimmers_off")}, "CORE", 7, requires="has_lake")
    B["S7_SCV3J"] = _blk({a: scv3j(a) for a in ("own", "borrowed")}, "FULL", 7)
    B["S7_SCV3F"] = _blk({a: scv3f(a) for a in ("walk_only", "default")}, "FULL", 7)
    B["S7_CBX2"] = _blk({a: cbx2(a) for a in ("reform_on", "reform_off", "resident")}, "FULL", 7)
    B["S7_VF1"] = _blk({a: vf1(a) for a in ("forage_on", "forage_off")}, "CORE", 8, livestock=True)
    B["S7_VF4"] = _blk({a: vf4(a) for a in ("forage_on", "forage_off")}, "CORE", 8, livestock=True, requires="has_river")
    B["S7_INV3"] = _blk({"smilodon": inv3("smilodon")}, "CORE", 9, requires="calm")
    B["S7_GRD1"] = _blk({a: grd1(a) for a in ("guard_on", "guard_off")}, "CORE", 10, requires="has_lake")
    B["S7_EXR1"] = _blk({a: exr1(a) for a in ("fix_on", "fix_off")}, "CORE", 11)
    B["S7_EXU1"] = _blk({a: exu1(a) for a in ("placed_before", "placed_after")}, "CORE", 11)
    B["S7_EXF1"] = _blk({a: exf1(a) for a in ("freq_on", "freq_off")}, "CORE", 11,
                        wipe=False, why="DF-drawn arrivals are the subject", requires="extinct_apex")
    B["S7_F1"] = _blk({a: f1(a) for a in ("auto", "layer_off")}, "CORE", 12, wipe=False, why="the water draw itself is the subject")
    B["S7_PERF1"] = _blk({a: perf1(a) for a in ("new", "legacy")}, "CORE", 13, wipe=False, why="the fort as loaded is the load")
    B["S7_PERF2"] = _blk({a: perf2(a) for a in ("new", "legacy_overlay", "overlay_off")}, "CORE", 13, wipe=False,
                         why="the fort as loaded is the load")
    B["S7_PERF4"] = _blk({a: perf4(a) for a in ("events_on", "events_off")}, "CORE", 13, wipe=False,
                         why="the fort as loaded is the load")
    if OCEAN_FORT:
        B["S7_PERF3"] = _blk({a: perf3(a) for a in ("defaults", "sponges_off")}, "OCEAN", 13, fort=OCEAN_FORT, wipe=False,
                             why="the fort as loaded is the load")
        B["S7_PELA"] = _blk({a: pela(a) for a in ("pull_on", "pull_off")}, "OCEAN", 10, fort=OCEAN_FORT, wipe=False,
                            why="the ocean's drawn prey and predators are the subject")
        B["S7_COHTO"] = _blk({a: coht_orca(a) for a in ("led", "cohesion_off")}, "OCEAN", 5, fort=OCEAN_FORT)
    return B


def register(BLOCKS: dict) -> dict:
    """eco-run.py's hook: add the S7_ blocks to its registry (no existing block is touched)."""
    new = blocks()
    clash = [k for k in new if k in BLOCKS and not k.startswith("S7_")]
    if clash:
        raise RuntimeError(f"alpha4_sec7_blocks: names already taken: {clash}")
    BLOCKS.update(new)
    return new
