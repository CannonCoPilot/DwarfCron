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
import time
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
         "calm": True, "has_ocean": False,
         # 2 Oct tally: pool roles and cavern reach (FACTS writes them; until it has, the blocks that need them are
         # NOT-TESTABLE-HERE, and the token names below are only what the dry run builds with)
         "raptor_token": "", "fisher_token": "", "polar_token": "", "has_raptor": False, "has_fisher": False,
         "has_polar": False, "fisher_river": False, "polar_lake": False, "reach_cavern": 0, "reach_civ_cavern": 0}
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
    # the script name first: without it run_script looked for a script named after the verb and every S7/T step
    # failed silently (2 Oct, S7_SKL: no 'mark' or 'skillsum' receipt; cfg checks only passed on their defaults)
    return "lua:dfhack.run_script(" + ",".join(_lq(x) for x in ("cx-sec7", verb, *a)) + ")"


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
    """Write config paths the way the verbs do (loadConfig/saveConfig); the H2 read-back is the `cfg` step after it.

    2 Oct (S7_IRRM abort, irruption.agitate read back true): cx-sec7 cfgset at a48bbd6 coerced with
    `(raw == 'false' and false) or tonumber(raw) or raw`, so 'false' fell through the and/or and was saved as the STRING
    'false'; the tool's sanitizer keeps only booleans and put the default back. Every false written that way was lost
    (true and numbers were fine). The probe is fixed, but the rig keeps its deployed copy until DEPLOY, so the write is
    inline here: it works on any deployed probe and the running sequence picks it up."""
    vals = [str(p).lower() if isinstance(p, bool) else str(p) for p in pairs]
    tbl = ",".join("{" + _lq(k) + "," + _lq(v) + "}" for k, v in zip(vals[::2], vals[1::2]))
    return ("lua:local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig(); local n=0; "
            "for _,p in ipairs({" + tbl + "}) do local raw,v=p[2]; if raw=='true' then v=true elseif raw=='false' then v=false "
            "else v=tonumber(raw); if v==nil then v=raw end end; local t,ks,ok=c,{},true; "
            "for k in p[1]:gmatch('[^.]+') do ks[#ks+1]=tonumber(k) or k end; "
            "for j=1,#ks-1 do if type(t[ks[j]])~='table' then ok=false; break end; t=t[ks[j]] end; "
            "if ok then t[ks[#ks]]=v; n=n+1 else print('eco error cfgset: no table at '..p[1]) end end; "
            "sw.saveConfig(c); pcall(function() sw.CACHE.cfg=nil end); print('eco cfgset written='..n)")


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
#
# 2 Oct (first rig run, BLOCK-FIXES.md): the subjects are kept apart and the pack-share bonus is off in every arm.
#   * Cougars 6 tiles from the wolves fought them (24 of 25 subject attack rows were COUGAR<->WOLF) and a nopkg cell
#     lost every wolf before the rust push (MANIP-FAIL rustpush.units=0). The wolves now go to a second spot
#     (cx-sec7 far<X>x<Y>: dry open land 80-160 tiles from the cougars, 30 clear of citizens).
#   * The pack-share 'sneak bonus' (hunters.skills.pack_bonus 10, a writer separate from v7.solo/hunters.pack) wrote
#     SNEAK 10 with a floor of 10 on every subject in the nopkg arm within 2,000 ticks (each species was the other's
#     prey), so nopkg was not a no-write arm; and in pkg_nofloor (rep 4) it re-wrote the floor after `nofloor`,
#     spoiling the positive control. It is set to 0 in every arm and read back.
#   * The rust push takes both species in one verb; its 'rustpushsum' row records the subjects lost so far. The cell
#     needs a subject left to rust (pkg arms: a unit holding SNEAK of either species; nopkg: a live subject, which
#     holds no SNEAK with every writer off). A species wholly lost is a censored rep for that species, not an abort.
SKL_FAR = "far{X}x{Y}"   # eco-run fills {X} {Y} with the block's land spot before the Lua runs


def skl(arm):
    pkg = arm != "nopkg"
    st = [SUSTAIN, "spawn COUGAR 2 {X} {Y} {Z} 3",
          AT(SKL_FAR, "spawn", "WOLF", "3", "<X>", "<Y>", "<Z>", "3", "land", "any", "200000", "roam"), S7("mark", "pre"),
          T("v7", "solo", "on" if pkg else "off"), T("hunters", "pack", "on" if pkg else "off"),
          T("hunters", "skills", "pack_bonus", "0"),
          *ENABLE, T("groups", "ecology", "now"),
          readback("v7.solo", "hunters.pack_on", "hunters.skills.pack_bonus"),
          chk(f"cfg[path=v7.solo].value=={'true' if pkg else 'false'}"),
          chk(f"cfg[path=hunters.pack_on].value=={'true' if pkg else 'false'}"),
          chk("cfg[path=hunters.skills.pack_bonus].value==0"),
          "spawn COUGAR 2 {X+20} {Y} {Z} 3",
          AT(SKL_FAR, "spawn", "WOLF", "3", "<X>", "<Y>", "<Z>", "3", "land", "any", "200000", "roam"),
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
        st += [S7("nofloor", "COUGAR,WOLF", "SNEAK"), chk("nofloorsum.tokens_hit>=1")]
    st += [S7("rustpush", "COUGAR,WOLF", "SNEAK", "200000"),
           chk("rustpushsum.tokens_hit>=1" if pkg else "rustpushsum.alive>=1"),
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


# 2 Oct tally (SECTION7-RESULTS "vacuous blocks"): STP1, FSH3 and FSH4 never reached their subject, for two reasons.
#   1. The tool manages only POOL species: ecoPredatorSet builds CACHE.ecoByTok from V7.PERF.pool, and V7.H.stoop /
#      V7.H.fish skip a unit whose token has no entry. BIRD_EAGLE, BEAR_GRIZZLY and BEAR_POLAR were not in
#      RinghatchetsReady's pool (FACTS factpool), so no stoop or fishing could act on the placed ones. FACTS now reads
#      the roles from the pool (factroles: the best-stocked raptor, fisher and polar fisher) and the blocks use them;
#      a fort without one makes the block NOT-TESTABLE-HERE instead of vacuous.
#   2. Placement: the eagles were placed 20 tiles from the rabbits and flew 30-220 tiles off; the bears went to the
#      body's shore spot and the pike to its water spot, picked apart (closest approach 15-17 tiles, adjacency 0/200).
#      Now the raptors are placed beside the prey and adopted as one group (the tool's cohesion holds them), and the
#      fishers go on the tool's own shore pair (cx-sec7 BODY:bank, V7.H.bankPair) with the pike in the water beside it.
# Each block receipts the encounter: adj (closest approach) every sample, and the tool's own per-pass counters
# (CACHE.stoopStat / CACHE.fishStat). The ON arm checks that the tool saw a managed raptor / fisher by its first pass.
RAPTOR = F.get("raptor_token") or "BIRD_EAGLE"
FISHER = F.get("fisher_token") or "BEAR_GRIZZLY"
POLAR = F.get("polar_token") or "BEAR_POLAR"


def _hstat(kind, tag):
    """CACHE.stoopStat / CACHE.fishStat: the last ecology pass's own counters for the stoop or the fishing."""
    key = {"stoop": "stoopStat", "fish": "fishStat"}[kind]
    return ("lua:local sw=reqscript('seasonal-wildlife'); local st=sw.CACHE." + key + " or {}; local t={}; "
            "for k,v in pairs(st) do if type(v)=='number' then t[#t+1]=k..'='..v end end; table.sort(t); "
            f"print('eco {kind}st tag={tag} '..(#t>0 and table.concat(t,' ') or 'none=1'))")


def stp1(arm):
    on = arm == "stoop_on"
    st = [SUSTAIN, T("hunters", "raptors", "on"), T("hunters", "stoop", "on" if on else "off"),
          T("groups", "ecology", "cadence", "1000"), *ENABLE,
          readback("hunters.stoop.enabled", "hunters.raptors", "ecology.cadence"),
          chk(f"cfg[path=hunters.stoop.enabled].value=={'true' if on else 'false'}"),
          chk("cfg[path=ecology.cadence].value==1000"),
          "spawn RABBIT 6 {X} {Y} {Z} 4", "spawn DEER 3 {X+12} {Y+6} {Z} 3",
          f"spawn {RAPTOR} 2 {{X+3}} {{Y}} {{Z}} 2", f"adopt {RAPTOR}",
          S7("mark", "pre"), S7("adj", RAPTOR, "RABBIT", "t0"), "watch"]
    for s, t in steps_of(6000, 1000):
        st += [s, S7("ledger", "ecology", f"t{t}"), S7("adj", RAPTOR, "RABBIT", f"t{t}"), _hstat("stoop", f"t{t}")]
        if on and t == 2000:   # an ecology pass (cadence 1,000, rescheduled at the verb) saw a managed raptor
            st.append(chk("stoopst[tag=t2000].raptors>0"))
    st += [f"relcount {RAPTOR} RABBIT", f"relcount {RAPTOR} DEER", TA("hunters", "status")]
    return dict(steps=st, ticks=10, nowatch=True)


def fsh3(arm):
    on = arm == "fish_on"
    st = [SUSTAIN, T("v7", "fishers", "on" if on else "off"), T("hunters", "fish", "run", "SpSuAuWi"),
          T("curious", FISHER, "resident"), *ENABLE,
          readback("v7.fishers", "hunters.fish.run"), chk(f"cfg[path=v7.fishers].value=={'true' if on else 'false'}"),
          S7("spot", "river:bank"), S7("spot", "river:bankwater"),
          AT("river:bank", "spawn", FISHER, "2", "<X>", "<Y>", "<Z>", "2", "land", "any", "200000", "roam"),
          AT("river:bankwater", "spawn", "FISH_PIKE", "8", "<X>", "<Y>", "<Z>", "3", "water", "any", "200000", "roam"),
          S7("adj", FISHER, "FISH_PIKE", "t0"), chk("adj[tag=t0].dmin<=6"), "watch"]
    for s, t in steps_of(6000, 300):
        st += [s, S7("adj", FISHER, "FISH_PIKE", f"t{t}"), _hstat("fish", f"t{t}")]
        if on and t == 3600:   # an ecology pass (cadence 3,000, from enable) saw a managed fisher
            st.append(chk("fishst[tag=t3600].fishers>0"))
    st += [S7("ledger", "ecology", "end"), TA("hunters", "status")]
    return dict(steps=st, ticks=10, nowatch=True)


def fsh4(arm):
    st = [SUSTAIN, T("v7", "fishers", "on"), T("v7", "fish_breathe", "off"), T("hunters", "fish", "polar", "on"),
          T("hunters", "fish", "run", "SpSuAuWi"), T("curious", POLAR, "resident"), *ENABLE,
          readback("v7.fishers", "v7.fish_breathe", "hunters.fish.polar"),
          chk("cfg[path=v7.fish_breathe].value==false"), chk("cfg[path=hunters.fish.polar].value==true"),
          S7("spot", "lake:bank"), S7("spot", "lake:bankwater"),
          AT("lake:bank", "spawn", POLAR, "2", "<X>", "<Y>", "<Z>", "2", "land", "any", "200000", "roam"),
          AT("lake:bankwater", "spawn", "FISH_PIKE", "8", "<X>", "<Y>", "<Z>", "3", "water", "any", "200000", "roam"),
          S7("adj", POLAR, "FISH_PIKE", "t0"), chk("adj[tag=t0].dmin<=6"), "watch"]
    for s, t in steps_of(6000, 600):
        st += [s, S7("swim", POLAR, f"t{t}"), S7("adj", POLAR, "FISH_PIKE", f"t{t}"), _hstat("fish", f"t{t}")]
        if t == 3600:
            st.append(chk("fishst[tag=t3600].fishers>0"))
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
           readback("enabled", "groups.adaptive", "groups.cavern", "groups.cavern_hold_mix", "water.spill.enabled",
                    "water.mix.enabled", "roster.apex.enabled", "roster.units", "extinct.fix"),
           chk("cfg[path=enabled].value==true")]
    want = dict(zip(levers[::2], levers[1::2]))
    for p in ("groups.adaptive", "groups.cavern", "water.spill.enabled", "roster.apex.enabled", "roster.units"):
        st.append(chk(f"cfg[path={p}].value=={want.get(p, 'true')}"))
    if arm == "def":   # the gate as shipped at 9e5aabe: the season's mix kept under the hold (the hold check reads it)
        st.append(chk("cfg[path=groups.cavern_hold_mix].value==true"))
    st += [S7("mark", "pre"), S7("nat", "t0"), chk("nat[tag=t0].land_cap>0"), "groups3 base"]
    for s, t in steps_of(NAT_TICKS):
        st += [s, S7("nat", f"t{t}")]
        if arm == "def":
            # R44's manipulation check: no species the gate holds reads above its hold level. Since 9e5aabe
            # (`groups cavern mix`, default on) an in-season held species keeps max(2, weight // 10) and only the
            # out-of-season ones sit at 1, so v7.1's "held_not_1 == 0" aborted a correct gate (2 Oct, S7_NAT rep 1
            # t3000: held_not_1=1). held_not_1 is still printed beside it.
            st.append(chk(f"hold[tag=t{t}].held_open==0"))
        if t % 6000 == 0:
            st.append(f"groups3 t{t}")
        if t % 15000 == 0:
            st.append(SUSTAIN)
    st += [S7("ledger", "season", "end"), S7("ledger", "wave", "end"), S7("ledger", "build", "end"),
           TA("water"), TA("roster", "apex"), TA("groups", "layers")]
    return dict(steps=st, ticks=10, nowatch=True, post=[T("disable")])


# S7_TRIM (R44 TRIM): cap 1, so a cavern holding two groups is over it, and the trim sends one resident group off per
# cavern_trim_days. History (BLOCK-FIXES.md):
#   * core3: the check fired at t1200, before the trim's pacing allowed it, and read only g.trim_undo (forgets);
#   * rerun 1 (a4fix): cav_max=0 at t0 -- flagged DF waves become groups only in a groups pass (discoverGroups);
#   * rerun 2 (a4fix): cav_max=5 but dismissed=0 at t2400. V7.GRP.trimOne (a4fix ~11124-11160) picks only RESIDENT
#     groups (natives first, else the oldest resident); groups discovered from DF waves are resident=false (gated,
#     discoverGroups ~4168), and every cavern group on RinghatchetsReady is a DF wave -- nothing was trimmable, by
#     design (the gate holds them; DF walks them off on its own leave clock). A design question for the user.
# So the subject is now placed: three resident groups (one species each, cx-eco spawn on the cavern floor WITHOUT
# the roaming flag, then `groups adopt` -> V7.GRP.record resident = not flagged) in cavern TRIM_CAV, cap 1, beside the
# DF-wave groups already there. Arms: cap1 (trim on) and trim_off (trim off, the same placement). Expected in cap1: a
# trim within trim_days (1 day = 1,200 t) plus the 300 t pass -- natives first, else the oldest resident (the first
# adopted: CRUNDLE, chosen first because it is surely natural; trimOne writes countdowns only to natural members and
# returns nothing for a group without one). `trimgrp` (inline) reads the cavern's groups by kind every 300 t: resident,
# gated, native, and which of them carry the trim mark -- trimmed_gated must stay 0 (the waves left alone).
TRIM_CAV = int(os.environ.get("SEC7_TRIM_CAV", "3"))   # FACTS: cavern 3 had the fewest wild units (10)
TRIM_TOKENS = tuple(os.environ.get("SEC7_TRIM_TOKENS", "CRUNDLE,TOAD_GIANT_CAVE,CREEPING_EYE").split(","))


def _trimgrp(d, tag):
    return ("lua:local sw=reqscript('seasonal-wildlife'); local g=sw.loadGroups(); "
            "local r,ga,nat,tr,trg,trn,live,toks=0,0,0,0,0,0,0,{}; "
            "for _,grp in ipairs(g.groups or {}) do if grp.layer=='cavern' and grp.depth==" + str(d) + " and not grp.irruption then "
            "local n=0; for _,id in ipairs(grp.ids or {}) do local u=df.unit.find(id); if u and not dfhack.units.isDead(u) and u.pos.x>=0 then n=n+1 end end; "
            "live=live+n; if grp.resident then r=r+1 else ga=ga+1 end; if grp.native then nat=nat+1 end; "
            "if grp.trimmed then tr=tr+1; toks[#toks+1]=tostring(grp.token)..(grp.native and '(n)' or (grp.resident and '(r)' or '(g)'))..'x'..n; "
            "if not grp.resident then trg=trg+1 end; if grp.native then trn=trn+1 end end end end; "
            f"print('eco trimgrp tag={tag} cavern={d + 1} resident='..r..' gated='..ga..' native='..nat..' live='..live.."
            "' trimmed='..tr..' trimmed_gated='..trg..' trimmed_native='..trn..' tokens='..(#toks>0 and table.concat(toks,',') or '-'))")


def trim(arm):
    on = arm == "cap1"
    d = TRIM_CAV - 1
    cav = f"cav{TRIM_CAV}"
    st = [SUSTAIN, T("preset"), *ENABLE, T("groups", "cavern", "on"), T("groups", "cavern", "cap", "1"),
          T("groups", "cavern", "trim", "on" if on else "off"), T("groups", "cavern", "trim_days", "1"),
          readback("groups.cavern_cap", "groups.cavern_trim", "groups.cavern_trim_days"),
          chk("cfg[path=groups.cavern_cap].value==1"), chk(f"cfg[path=groups.cavern_trim].value=={'true' if on else 'false'}"),
          S7("mark", "pre"), S7("spot", cav)]
    for tok in TRIM_TOKENS:   # no 'roam': the flag cleared, so the adopted group is resident (the trim's subject)
        st.append(AT(cav, "spawn", tok, "3", "<X>", "<Y>", "<Z>", "3", "cave", "any", "200000"))
    st += [f"adopt {' '.join(TRIM_TOKENS)}", "step:300", _trimgrp(d, "t0"), chk("trimgrp[tag=t0].resident>=3"),
           S7("trim", "t0")]
    for s, t in steps_of(3000, 300):
        st += [s, S7("trim", f"t{t}"), _trimgrp(d, f"t{t}")]
        if t in (1500, 2700):
            st.append(S7("ledger", "dismiss", f"t{t}"))
        if on and t == 2700:   # trim_days (1,200 t) + passes, from a t0 already one pass in: the arm is vacuous without one
            st.append(chk(f"trim[tag=t{t}].dismissed>0"))
    for tok in TRIM_TOKENS:
        st.append(S7("swim", tok, "end"))   # per placed species: alive / dead / gone (walked off)
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


# 2 Oct (S7_IRRR35 abort, irrupting arm: gsize groups=0 at t1200, no wave): `preset` turns the cavern layer on, so the
# R29 season deal holds every OUT-OF-SEASON cavern species by zeroing its population entry every groups pass
# (holdOutOfSeason, seasonal-wildlife.lua:2927-2939; the stock goes to the reserve). IRRUPT.candidates reads live
# quantity (`pop.quantity > 0`, :9621), so an out-of-season civ race cannot be sent even under irruption.roster
# 'allowed' (:9610): `irruption now 2 PLUMP_HELMET_MAN` found "no live, admitted, natural entry" and nothing was placed.
# With no token (IRRM, IRRP2, IRRTSEQ), pick falls back to a cavern PREDATOR when the civ race is out of season, and the
# token arms run on a species that carries no tokens -- vacuous while `alive>0` passes. FACTS read the candidates before
# any preset, so it saw the civ race. CIV_PREP gives every civ race with an entry in the cavern all seasons
# (`seasons cavern:TOKEN all`: in season, so applyLive restocks it from the reserve) in every arm alike, then proves the
# event can send a civ race: civcand.n>0 (and, for a named species, irrpick.ok==1 with the tool's reason on failure).
# SEC7_CIV_SEASONS=0 drops the seasons write and keeps the receipts and checks: for a build whose irruption admits an
# out-of-season civ race itself (a4fix 69e97a1), so the arm tests the tool's own admission and the roster is untouched.
CIV_SEASONS = os.environ.get("SEC7_CIV_SEASONS", "1") != "0"


def CIV_PREP(cav, token=""):
    d = int(cav) - 1
    st = [] if not CIV_SEASONS else [
          "lua:local sw=reqscript('seasonal-wildlife'); local all=df.global.world.populations.all; local seen,n={},0; "
          "for _,r in ipairs(sw.CACHE.managedPops()) do local p=all[r.i]; if r.layer=='cavern' and p and not seen[r.key] "
          f"and sw.WILD.caveDepth(p.population.cave_id)=={d} and sw.IRRUPT.isCiv(p.race) then seen[r.key]=true; "
          "dfhack.run_command_silent('seasonal-wildlife','seasons',r.key,'all'); n=n+1 end end; "
          f"print('eco civseason cavern={d + 1} keys='..n)"]
    st += ["lua:local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig(); local t={}; "
          f"for _,e in ipairs(sw.IRRUPT.candidates(c,{d},true)) do t[#t+1]=e.token..':'..e.q end; "
          f"print('eco civcand cavern={d + 1} n='..#t..' tokens='..(#t>0 and table.concat(t,',') or '-'))",
          chk("civcand.n>0")]
    if token:
        st += ["lua:local sw=reqscript('seasonal-wildlife'); local e,why=sw.IRRUPT.pick(sw.loadConfig()," + str(d) + "," + _lq(token) + "); "
               f"print('eco irrpick cavern={d + 1} ok='..(e and 1 or 0)..' why='..tostring(why or (e and e.token) or '-'):gsub('[%s=]+','_'))",
               chk("irrpick.ok==1")]
    return st


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
        # 2 Oct tally: the event had ended (cooldown, t500-t2900: the crazed subjects died and the event read as
        # repelled) before the end-of-cell save, so the reload read no subject. No repel end, a long settle: the event
        # stays active through the save, which now comes at t300.
        extra += ["irruption.repel_share", "0", "irruption.repel_dead", "0", "irruption.settle_days", "10"]
    if arm == "sneak_rehide":
        extra = ["irruption.rehide", "true"]
    if arm == "wander_surge":
        extra = ["irruption.surge", "true"]
    st = [SUSTAIN, T("preset"), *ENABLE, *CIV_PREP(CIV), CFG(*IRR_BASE, *_tokens_only(tok), *extra),
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
    # M6 (goalonly), 2 Oct tally: one harness write of the steal goal did not persist (0 steal-goal samples; DF re-plans
    # a unit's path goal on its own). The write is now repeated after every sample, 100 t apart, so each `irr` read
    # measures whether the goal survived 100 t; and the arm's verdict is the persistence of a bare goal write, while
    # theft-by-goal is read from the thief token's own goal (the tool's write, M4), not from this arm.
    every = 100 if arm in ("crazed", "goalonly") else 300
    for s, t in steps_of(3000, every):
        st += [s, S7("irr", str(CIV), f"t{t}")]
        if arm == "goalonly":
            st.append(S7("subjects", str(CIV), "goal"))
        if arm == "thief" and t in (100, 3000):
            st.append(S7("native", str(CIV), "*", f"t{t}"))
        if arm == "crazed" and t == 300:   # M1: the mask after a save and reload, with the event still active
            st += [chk("irr[tag=t300].alive>0"), "read:pre_reload", "save:S7_M1_TMP", "load:S7_M1_TMP",
                   S7("irr", str(CIV), "reload"), chk("irr[tag=reload].alive>0")]
    st += [S7("civs", str(CIV), "end"), S7("resid", "end")]
    return dict(steps=st, ticks=10, nowatch=True)


# Phase 2: A rotation only (irruption off), B irruption with every token off, C the R10 package (defaults). The
# pressure is pinned at the threshold, the warning is 0.1 day, waves 0.5 day apart, 5 days long. Every civ unit in
# the band is sampled every 600 ticks (the notes ask 300; 600 halves the RPC time) for 7,200 ticks.
# 2 Oct tally: dacc was -1 everywhere (the event had no access point) and no subject came within 124 tiles of a
# citizen, so P2's approach was untested. The tool's access (IRRUPT pressurePass: L.access) is where citizens stand
# in the band (or dig beside it), and RinghatchetsReady's fort reaches no cavern. So P2 runs in a cavern a citizen can
# walk to when FACTS finds one with a civ race (reach_civ_cavern), else the civ cavern, and in EVERY arm three citizens
# are put in that band, knocked out so they stay (the notes' "3 citizens working in the band", the shortcut the first
# design left out): they give the event its access and the approach its target. The tool still places and walks the
# subjects itself; dacc and dcit are the outcome.
P2CAV = int(F.get("reach_civ_cavern") or 0) or CIV


def irr_p2(arm):
    cav = str(P2CAV)
    st = [SUSTAIN, T("preset"), *ENABLE, *CIV_PREP(P2CAV), S7("citizens", cav, "3", "in", "knock"), chk("citizens.moved>0")]
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
               chk("cfg[path=irruption.duration_days].value==5"), S7("pin", cav), chk("pin.ok==1")]
    st += [S7("civs", cav, "t0"), "watch"]
    for s, t in steps_of(7200, 600):
        st += [s, S7("irr", cav, f"t{t}"), S7("civs", cav, f"t{t}")]
        if arm != "A" and t == 1200:
            st.append(chk(f"irr[tag=t{t}].alive>0"))
        if t == 3600:
            st.append(SUSTAIN)
    st.append(S7("resid", "end"))
    return dict(steps=st, ticks=10, nowatch=True)


# Phase 3 (T-*): an event, then its end by each route, then the residual-write scan (0 masks, 0 cache bits beyond the
# caste's own). T-SAVE: save and reload mid-event, then the record and the writes again.
def irr_t(arm):
    st = [SUSTAIN, T("preset"), *ENABLE, *CIV_PREP(CIV), CFG(*IRR_BASE, *_tokens_only(("crazed", "thief", "sneak", "mischief")),
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
    st = [SUSTAIN, T("preset"), *ENABLE, *CIV_PREP(CIV), CFG(*IRR_BASE, *_tokens_only(("crazed", "thief", "sneak", "mischief")),
                                             "irruption.duration_days", "1", "irruption.cooldown_days", "0"),
          readback("irruption.enabled"), chk("cfg[path=irruption.enabled].value==true")]

    # 2 Oct (desk review): each event starts with `irruption end` -- a no-op when the route before ended its event, but
    # if a route left it active, `now` would answer "already irrupting" and the next route's alive>0 check would pass on
    # the old event's subjects (its residue then misattributed). The route's own resid row, taken before, still shows
    # what that route left (active_events).
    def event(tag):
        return [T("irruption", "end", cav), T("irruption", "cool", cav), CFG("irruption.enabled", "true"),
                T("irruption", "now", cav), "step:20",
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


# R35 (USER-REVIEW-PART2: "Group-size cap for animal people (plump helmet men) in caverns: YES, lifted during an
# irruption event"). The lever is the raw's CLUSTER_NUMBER, held at groups.apcap (5) by V7.GRP.apCap every groups pass
# and put back while the species' cavern irrupts (V7.GRP.irruptOn); DF reads it when it draws a natural wave.
# 2 Oct (rerun 20261002-075328, a4fix): the irrupting arm worked (one PLUMP_HELMET_MAN wave of 10, 'i'); the quiet arm
# aborted on gsize[t1200].groups=0. Its subject was a NATURAL group, which cannot exist in a cell: in Spring the season
# roster holds the species out of season (stock 0), and a cavern `call` places nothing -- it only opens the frequency
# for DF's next draw (ENGINE.call), whose timing is DF's. So:
#   * both arms give the species all seasons (`seasons cavern:TOKEN all`), whatever SEC7_CIV_SEASONS says, so a
#     natural wave CAN come in either arm and the arms differ only by the event;
#   * the quiet arm's subject is the cap itself: `apraw` reads the raw's cluster range every sample, and the check is
#     apraw[t600].max <= 5 (after two groups passes); natural groups that DF does send are recorded by gsize as an
#     outcome, not required;
#   * the irrupting arm records apraw too (the cap lifted during the event is the contrast) and keeps its start check;
#   * both arms run 2,400 t (DF gets more time to send a natural wave).
R35_CAP = int(os.environ.get("SEC7_R35_CAP", "2"))


def _apraw(token, cav, tag):
    return ("lua:local sw=reqscript('seasonal-wildlife'); local cr=sw.CAVERN.rawFor(" + _lq(token) + "); "
            "local o=((sw.CACHE.apcap or {}).raws or {})[" + _lq(token) + "]; "
            f"local on=sw.V7.GRP.irruptOn({int(cav) - 1}) and 1 or 0; "
            # the tool's convention: cluster_number[0] is the MAX, [1] the min (seasonal-wildlife.lua:1744 at rc), and
            # apCap's held original is { [0], [1] } -- so orig_max is o[1] (2 Oct tally: the labels were swapped)
            f"print(('eco apraw tag={tag} token=%s max=%d min=%d orig_max=%s capped=%d irrupting=%d')"
            ":format(cr.creature_id, cr.cluster_number[0], cr.cluster_number[1], o and tostring(o[1]) or '-', o and 1 or 0, on))")


def irr_r35(arm):
    cav = AP_CAV or CIV
    tok = AP_TOKEN or "PLUMP_HELMET_MAN"
    # 2 Oct tally: at apcap 5 R35 was vacuous here -- PLUMP_HELMET_MAN's raw range is 3-5, so apCap never capped
    # anything (capped=0, "0 species capped now"). apcap R35_CAP (2, below the raw's max) makes the cap bite.
    st = [SUSTAIN, T("preset"), *ENABLE, T("groups", "apcap", str(R35_CAP)), readback("groups.apcap"),
          chk(f"cfg[path=groups.apcap].value=={R35_CAP}"),
          T("seasons", f"cavern:{tok}", "all"), *CIV_PREP(cav, tok)]
    if arm == "irrupting":
        # the event's start is proven at once (phase active, a wave alive after 20 t), not first at the end
        st += [CFG(*IRR_BASE, "irruption.species", tok, "irruption.size_cap", "20"),
               T("irruption", "now", str(cav), tok), "step:20", S7("irr", str(cav), "t0"), chk("irr[tag=t0].alive>0")]
    else:
        st += [T("call", f"cavern:{tok}")]
    for s, t in steps_of(2400, 300):
        st += [s, S7("gsize", tok, f"t{t}"), _apraw(tok, cav, f"t{t}")]
        if arm == "quiet" and t == 600:   # the cap reached the raw (two groups passes after enable): held, and biting
            st += [chk(f"apraw[tag=t600].max<={R35_CAP}"), chk("apraw[tag=t600].capped==1")]
    if arm == "irrupting":
        st.append(chk("gsize[tag=t2400].groups>0"))
    return dict(steps=st, ticks=10, nowatch=True)


# T-PR (FULL): pressure from real sources, threshold lowered to 0.3 (shortcut: the order of the sources, not their
# absolute days); days to warning read off the phase every 600 ticks.
def irr_pr(arm):
    st = [SUSTAIN, T("preset"), *ENABLE, *CIV_PREP(CIV), CFG("irruption.enabled", "true", "irruption.threshold", "0.3",
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
          # 2 Oct (desk review): at the water spot itself, radius 3. <X+10> radius 2 asked for deep water 10 tiles off
          # a spot that only guarantees 30 wet of the 49 within 3 tiles -- placed=0 there aborts the block (auto spawn)
          AT("lake:water", "spawn", "POND_GRABBER", "2", "<X>", "<Y>", "<Z>", "3", "water", "any", "200000", "roam"),
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


VFEAT = ("lua:local sw=reqscript('seasonal-wildlife'); local S=(_G.CX_ECO or {}).spawned or {}; "
         "local race=-1; for i,c in ipairs(df.global.world.raws.creatures.all) do if c.creature_id=='GRASSHOPPER' then race=i end end; "
         "local st={race={},eater={},match={}}; local n,eaters,eats,cls=0,0,0,{}; "
         "for id,tok in pairs(S) do if tok=='BADGER' then local u=df.unit.find(id); if u and not dfhack.units.isDead(u) then n=n+1; "
         "local okE,set=pcall(sw.VERMIN.eaterSet,st,u); if okE and set then eaters=eaters+1; for k in pairs(set.cls) do cls[k]=true end end; "
         "local okA,yes=pcall(sw.VERMIN.eats,st,u,race); if okA and yes then eats=eats+1 end end end end; "
         "local c={}; for k in pairs(cls) do c[#c+1]=k end; table.sort(c); "
         "print('eco vfeat badgers='..n..' eaters='..eaters..' eats='..eats..' classes='..(#c>0 and table.concat(c,',') or '-'))")


def vf1(arm):
    on = arm == "forage_on"
    st = [SUSTAIN, *ENABLE, *_forage(on),
          _vrm_inline("vermin_create.lua", RACE="GRASSHOPPER", N=20, R=5, X="{X+15}", Y="{Y}", Z="{Z}"),
          chk("vcreate.made>=10"), "spawn BADGER 4 {X} {Y} {Z} 2",
          # 2 Oct tally: no badger appeared as an eater. `vfeat` reads what the tool's forage reads: each placed badger's
          # caste gobble set (VERMIN.eaterSet: GOBBLE_VERMIN_CLASS / _CREATURE, as the gobble wiring left it) and
          # whether it eats GRASSHOPPER (VERMIN.eats). With no eater the arm has no subject, so both arms check it.
          VFEAT, chk("vfeat.eats>0")]
    if on:
        st.append(T("vermin", "forage", "now"))
    for s, t in steps_of(3000, 500):
        st += [s, _vrm_inline("vermin_count.lua", RACE="GRASSHOPPER", R=8, TAG=f"t{t}", X="{X+15}", Y="{Y}", Z="{Z}")]
    st.append(TA("vermin", "eats"))
    return dict(steps=st, ticks=10, nowatch=True, post=[T("disable")])


# S7_VF4's bank, found by the fish (VSHORE).
# 2 Oct (core3: MANIP-FAIL vermin[t0].total=0): the river's survey shore spot had no fish vermin within 12 tiles.
# 2 Oct (rerun 20261002-075328): the first arm found a fish bank, the second (a fresh load) found none -- DF places and
# hides vermin at random per load. So VSHORE now
#   * scans every vermin that is a fish (VERMIN_FISH) or stands in water, at any level open to the sky (not
#     subterranean), visible or not; bins them 10x10 per level, preferring bins with visible vermin; takes the nearest
#     open outside floor within 8 tiles of the densest bin's centroid, 0-3 levels up (the bank over deep water);
#   * fixes that bank for the whole block: the first arm that finds one writes `TOKEN x y z` to
#     dfhack-config/sec7-vshore.txt (DF's directory; TOKEN is this eco-run invocation's, so a stale file from another
#     run is ignored), and every later arm and rep reads it back -- every arm compares the same bank;
#   * calls the bank found once a visible vermin stands within the counter's reach of it (cx-eco `vermin`: 12 tiles,
#     levels z-1..z+1, visible) -- the same thing the outcome counts;
#   * is tried five times, 300 t apart (up to 1,200 t of waiting, always stepped so every arm has the same timeline);
#     `found` is sticky (first_try records the wait) and the check reads the last try. A fort with no fish vermin near a
#     bank after the wait aborts the block, as before.
# The spot is cached as cx-sec7 spot 'vshore' (_G.CX_SEC7.spots under cx-sec7's own map key), so `at vshore` works on
# the deployed probe. The ducks go on the spot itself (radius 3). VF4 needs no river: any surface water serves.
VSHORE_TOKEN = os.environ.get("SEC7_VSHORE_TOKEN") or time.strftime("%Y%m%d%H%M%S")


def VSHORE(k):
    return ("lua:local TOKEN=" + _lq(VSHORE_TOKEN) + "; local TRY=" + str(k) + "; "
            "local S=_G.CX_SEC7 or {spots={},marks={}}; _G.CX_SEC7=S; "
            "local key=df.global.plotinfo.site_id..':'..df.global.world.map.x_count..'x'..df.global.world.map.y_count; "
            "if S.map~=key then S.map,S.spots,S.marks,S.perf=key,{},{},nil end; "
            "local V=_G.SEC7_VSHORE or {}; _G.SEC7_VSHORE=V; local FILE='dfhack-config/sec7-vshore.txt'; "
            "local function amt(v) local a=v.amount; if not a or a<1 then a=1 end; return a end; "
            "local function near(x,y,z) local nv,na=0,0; for _,v in ipairs(df.vermin.get_vector()) do "
            "if math.abs(v.pos.x-x)<=12 and math.abs(v.pos.y-y)<=12 and math.abs(v.pos.z-z)<=1 then "
            "na=na+amt(v); if v.visible~=false then nv=nv+amt(v) end end end; return nv,na end; "
            "if not V.tile then local ok,fh=pcall(io.open,FILE,'r'); if ok and fh then local l=fh:read('*l') or ''; fh:close(); "
            "local t,x,y,z=l:match('^(%S+) (%d+) (%d+) (%d+)$'); if t==TOKEN then V.tile={tonumber(x),tonumber(y),tonumber(z)}; V.src='file' end end end; "
            "local tot,vis,nb=0,0,0; "
            "if not V.tile then local bins={}; "
            "for _,v in ipairs(df.vermin.get_vector()) do local f=dfhack.maps.getTileFlags(v.pos); "
            "if f and not f.subterranean then local cr=df.creature_raw.find(v.race); local fish=false; "
            "pcall(function() fish=cr.flags.VERMIN_FISH and true or false end); "
            "if fish or (f.flow_size>=4 and not f.liquid_type) then local a=amt(v); tot=tot+a; "
            "local k=(v.pos.x//10)..','..(v.pos.y//10)..','..v.pos.z; local b=bins[k]; "
            "if not b then b={n=0,nv=0,x=0,y=0,c=0,z=v.pos.z}; bins[k]=b; nb=nb+1 end; "
            "b.n=b.n+a; b.x=b.x+v.pos.x; b.y=b.y+v.pos.y; b.c=b.c+1; if v.visible~=false then b.nv=b.nv+a; vis=vis+a end end end end; "
            "local best; for _,b in pairs(bins) do if not best or b.nv>best.nv or (b.nv==best.nv and b.n>best.n) then best=b end end; "
            "local res,bd; if best then local cx,cy=best.x//best.c,best.y//best.c; "
            "for dz=0,3 do for dy=-8,8 do for dx=-8,8 do local x,y,z=cx+dx,cy+dy,best.z+dz; "
            "local t=dfhack.maps.getTileType(x,y,z); local f=dfhack.maps.getTileFlags(x,y,z); "
            "if t and f and f.outside and f.flow_size<4 then local sa=df.tiletype_shape.attrs[df.tiletype.attrs[t].shape]; "
            "if sa.walkable and (sa.basic_shape==df.tiletype_shape_basic.Floor or sa.basic_shape==df.tiletype_shape_basic.Ramp) then "
            "local d=math.max(math.abs(dx),math.abs(dy))+2*dz; if not bd or d<bd then res,bd={x,y,z},d end end end end end end end; "
            "if res then V.tile=res; V.src='scan'; local ok,fh=pcall(io.open,FILE,'w'); "
            "if ok and fh then fh:write(TOKEN..' '..res[1]..' '..res[2]..' '..res[3]..'\\n'); fh:close() end end end; "
            "local nv,na=-1,-1; if V.tile then S.spots['vshore']=V.tile; nv,na=near(V.tile[1],V.tile[2],V.tile[3]) end; "
            "if nv>0 and not V.found then V.found=TRY end; "
            "print(('eco vshore try=%d src=%s aquatic=%d visible=%d bins=%d found=%d first_try=%d near_vis=%d near_all=%d x=%d y=%d z=%d')"
            ":format(TRY,V.src or '-',tot,vis,nb,V.found and 1 or 0,V.found or -1,nv,na,"
            "V.tile and V.tile[1] or -1,V.tile and V.tile[2] or -1,V.tile and V.tile[3] or -1))")


def vf4(arm):
    on = arm == "forage_on"
    st = [SUSTAIN, *ENABLE, *_forage(on), VSHORE(1)]
    for k in range(2, 6):
        st += ["step:300", VSHORE(k)]
    st += [chk("vshore.found==1"),
           AT("vshore", "vermin", "<X>", "<Y>", "<Z>", "12", "t0"),
           AT("vshore", "spawn", "BIRD_DUCK", "4", "<X>", "<Y>", "<Z>", "3", "land", "any", "200000", "roam")]
    if on:
        st.append(T("vermin", "forage", "now"))
    for s, t in steps_of(3000, 500):
        st += [s, AT("vshore", "vermin", "<X>", "<Y>", "<Z>", "12", f"t{t}")]
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
          "adopt FISH_PIKE", "step:50", AT("lake:shore", "tp", "FISH_PIKE", "<X>", "<Y>", "<Z>"), chk("tp.units>0"),
          # 2 Oct tally: no dry receipt -- at t200 every pike was wet in BOTH arms (DF or the guard had them back
          # already). The stranding is receipted at once, before any tick passes, and the first 200 t are sampled densely
          S7("swim", "FISH_PIKE", "tp0"), S7("wat", "tp0"), chk("swim[tag=tp0].alive>0"), chk("swim[tag=tp0].wet==0")]
    t = 0
    for d in (10, 10, 30, 50, 100):
        t += d
        st += [f"step:{d}", S7("swim", "FISH_PIKE", f"t{t}"), S7("wat", f"t{t}")]
    for s, t2 in steps_of(1000, 200):
        st += [s, S7("swim", "FISH_PIKE", f"t{t2 + 200}"), S7("wat", f"t{t2 + 200}")]
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
          # 2 Oct (desk review): found==1 never proved the dial. The fix (V7.EXTINCT.apply at enable, roles: TAGS
          # benign=false) writes BENIGN off on every caste, so fix_on must read 0 BENIGN castes; fix_off is the raw's own
          *([chk("benign.castes_benign==0")] if on else []),
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
    # 2 Oct tally: EXU1 had no receipt that the extinct change reached the animals (no attack, no per-unit BENIGN or
    # relation). `exunit` reads every placed eoraptor's per-unit caste cache (enemy.caste_flags.BENIGN) and its
    # caste's raw flag: the fix clears BENIGN on the castes (V7.EXTINCT.apply, roles) and E.units writes the change
    # into units already on the map -- so both arms must read cache_benign 0 (before: by the unit pass; after: born
    # from the changed caste). relcount (PREDATOR_OR_PREY between the placed eoraptors and hares) every sample.
    st += [readback("extinct.fix", "extinct.units"), chk("cfg[path=extinct.units].value==true"),
           "spawn HARE 6 {X+8} {Y} {Z} 3", EXUNIT("t0"), chk("exunit[tag=t0].alive>0"), chk("exunit[tag=t0].cache_benign==0"),
           "watch"]
    for s, t in steps_of(6000):
        st += [s, "relcount TRIASSIC_EORAPTOR HARE", EXUNIT(f"t{t}")]
    return dict(steps=st, ticks=10)


def EXUNIT(tag):
    return ("lua:local S=(_G.CX_ECO or {}).spawned or {}; local n,cb,rb=0,0,0; "
            "for id,tok in pairs(S) do if tok=='TRIASSIC_EORAPTOR' then local u=df.unit.find(id); "
            "if u and not dfhack.units.isDead(u) and u.pos.x>=0 then n=n+1; "
            "local ok,v=pcall(function() return u.enemy.caste_flags.BENIGN end); if ok and v then cb=cb+1 end; "
            "local cr=df.creature_raw.find(u.race); local ok2,v2=pcall(function() return cr.caste[u.caste].flags.BENIGN end); "
            "if ok2 and v2 then rb=rb+1 end end end end; "
            f"print('eco exunit tag={tag} alive='..n..' cache_benign='..cb..' caste_benign='..rb)")


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
    # 2 Oct (desk review): sixty makeown citizens in ONE lua: step outlast cx-rpc --lua's 15 s deadline (fort-load-levers:
    # the 6x6 build did the same), which fails the cell; six calls of ten each stay well inside it
    st = [SUSTAIN, *[f"lua:dfhack.run_command('cx-load','citizens','10'); print('eco citizens10 batch={i}')" for i in range(1, 7)],
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
    B["S7_STP1"] = _blk({a: stp1(a) for a in ("stoop_on", "stoop_off")}, "CORE", 2, requires="has_raptor")
    B["S7_FSH3"] = _blk({a: fsh3(a) for a in ("fish_on", "fish_off")}, "CORE", 2, requires="fisher_river")
    B["S7_FSH4"] = _blk({"polar": fsh4("polar")}, "CORE", 2, requires="polar_lake")
    nw = "natural arrivals are the subject (G2r, CAVG, WAT5, APX1, LAD1, MIX1, F2)"
    B["S7_NAT"] = _blk({a: nat(a) for a in ("def", "v70")}, "CORE", 3, wipe=False, why=nw)
    B["S7_NATLEV"] = _blk({a: nat(a) for a in LEVER_ARMS}, "FULL", 3, wipe=False, why=nw)
    B["S7_TRIM"] = _blk({a: trim(a) for a in ("cap1", "trim_off")}, "CORE", 4, wipe=False,
                        why="placed resident groups beside the cavern's own DF-wave groups (which must be left alone)",
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
    B["S7_VF4"] = _blk({a: vf4(a) for a in ("forage_on", "forage_off")}, "CORE", 8, livestock=True)   # any water body (VSHORE)
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
