#!/usr/bin/env python3
"""E37 tally: what does seasonal-wildlife cost in FPS, and does the cost scale with load?

Two factors crossed — tool fully on vs wholly off, at two load levels (the fort as it stands,
and the same fort with sixty extra land animals placed through the tool's own headless route).
The measure is DF's own achieved frame rate, which the harness already samples as
`clock/fps_achieved` in rows.tsv at every probe; `e37:` receipts in events.tsv carry fps, units
and tool state together, and are used here to prove each arm actually ran in the state it claims.

The fork is not the on/off gap alone but the COMPARISON OF THE TWO GAPS: a constant cost shows
the same deficit at both load levels, a cost that scales shows a wider gap when crowded.

Three culls, applied and reported rather than assumed (the manifest's own criteria):
  * a replicate with no `done:` line is still running and is excluded (tallylib)
  * a crowded replicate that placed fewer than 30 extra units is a trigger failure
  * a replicate running at the fps cap is vacuous — the cap, not the tool, was the constraint

Usage: e37-tally.py [run_dir]
"""
import csv, glob, re, statistics, sys
from collections import defaultdict

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import tallylib

run_dir = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob("data/experiments/E37/*"))[-1]

# e37: fps=214 cap=10000 units_active=31 alive=31 land=0 ... citizens=7 tool=false sched=false ...
RECEIPT = re.compile(
    r"e37: fps=(\d+) cap=(\d+) units_active=(\d+) alive=(\d+) land=(\d+) water=(\d+) "
    r"cavern=(\d+) deep=(\d+) citizens=(\d+) tool=(\w+) sched=(\w+) groups=(\w+) eco=(\w+) day=(\d+)")
# e37: CROWDED - placed 60 extra land units from 21 entries; units_active now 91
PLACED = re.compile(r"e37: CROWDED.*?placed (\d+)", re.I)

fps = defaultdict(list)          # (arm, rep) -> fps_achieved samples from rows.tsv
units = defaultdict(list)        # (arm, rep) -> units_active samples from rows.tsv
cap = {}                         # (arm, rep) -> fps cap in force
tps = defaultdict(list)          # (arm, rep) -> ticks_per_wall_s, an independent cross-check
state = {}                       # (arm, rep) -> (tool, sched, groups, eco) as the receipts report
r_units = defaultdict(list)      # (arm, rep) -> units_active from the e37 receipts
r_fps = defaultdict(list)        # (arm, rep) -> fps from the e37 receipts
citizens = defaultdict(list)
placed = defaultdict(int)

paired = defaultdict(dict)       # (arm, rep) -> tick -> {"fps": x, "units": y}

for r in csv.DictReader(open(f"{run_dir}/rows.tsv"), delimiter="\t"):
    if r["subject"] != "clock":
        continue
    k = (r["arm"], int(r["rep"]))
    try:
        v = float(r["value"])
    except ValueError:
        continue
    if r["metric"] == "fps_achieved":
        fps[k].append(v)
        paired[k].setdefault(r["abs_tick"], {})["fps"] = v
    elif r["metric"] == "units_active":
        units[k].append(v)
        paired[k].setdefault(r["abs_tick"], {})["units"] = v
    elif r["metric"] == "fps_cap":
        cap[k] = v
    elif r["metric"] == "ticks_per_wall_s":
        tps[k].append(v)

for r in csv.DictReader(open(f"{run_dir}/events.tsv"), delimiter="\t"):
    k = (r["arm"], int(r["rep"]))
    m = RECEIPT.search(r["detail"])
    if m:
        r_fps[k].append(int(m.group(1)))
        r_units[k].append(int(m.group(3)))
        citizens[k].append(int(m.group(9)))
        state[k] = tuple(m.group(i) for i in (10, 11, 12, 13))
        cap.setdefault(k, float(m.group(2)))
    m = PLACED.search(r["detail"])
    if m:
        placed[k] = max(placed[k], int(m.group(1)))

tallylib.drop_incomplete(run_dir, fps, units, r_fps, r_units, citizens, state, placed, tps, paired)

# ------------------------------------------------------------------ culls ---
culled = {}
for k in sorted(set(fps) | set(r_fps)):
    why = []
    if "crowded" in k[0] and placed.get(k, 0) < 30:
        why.append(f"trigger failure: only {placed.get(k, 0)} extra units placed (<30)")
    s = fps.get(k) or r_fps.get(k) or []
    c = cap.get(k, 0)
    if s and c and statistics.mean(s) >= 0.95 * c:
        why.append(f"vacuous: ran at the cap ({statistics.mean(s):.0f} of {c:.0f})")
    if why:
        culled[k] = why

print(f"run {run_dir}")
if culled:
    print("\n!! CULLED — per the manifest's own criteria, excluded from every mean below:")
    for k, why in culled.items():
        print(f"   {k[0]} rep {k[1]}: " + "; ".join(why))

print("\nper replicate — DF's own achieved frame rate (rows.tsv clock/fps_achieved)")
print("arm\trep\tn\tfps min/mean/median/max\tcap\tunits mean\tcitizens\ttool/sched/groups/eco\tplaced")
for k in sorted(set(fps) | set(r_fps), key=lambda x: (x[0], x[1])):
    s = fps.get(k) or r_fps.get(k) or []
    if not s:
        continue
    u = units.get(k) or r_units.get(k) or [0]
    cz = citizens.get(k, [0])
    st = "/".join(state.get(k, ("?",) * 4))
    mark = "  [CULLED]" if k in culled else ""
    print(f"{k[0]}\t{k[1]}\t{len(s)}\t{min(s):.0f}/{statistics.mean(s):.1f}/{statistics.median(s):.0f}/{max(s):.0f}"
          f"\t{cap.get(k, 0):.0f}\t{statistics.mean(u):.1f}\t{cz[0]}->{cz[-1]}\t{st}\t{placed.get(k, 0)}{mark}")

# ------------------------------------------------------- THE NOISE FLOOR FIRST ---
# Read this before believing any gap below. off_baseline reps 1 and 2 are the SAME arm, the
# same config and the same fort, and they returned mean fps 250.7 and 295.8 — 18% apart for
# no experimental reason at all. Whatever moves that (host load, CrossOver, DF's own job mix)
# is larger than any plausible cost of a handful of Lua jobs. So the honest order of business
# is: establish what two identical replicates disagree by, and refuse to call anything smaller
# than that a finding. With two reps per arm this is a crude bound, and it is still the most
# important number in the file.
# --------------------------------------------- run order, because it is confounded ---
# The harness runs arms in manifest order: both off_baseline reps, then both on_baseline,
# then the crowded pair. So RUN ORDER IS CONFOUNDED WITH ARM by construction. If the host
# drifts over the hour (other processes, thermal, CrossOver state), that drift lands on
# whichever arm happened to be running, and would be read as a tool effect. The two
# off_baseline reps differing by 16.5% makes this a live worry, not a theoretical one.
# So: print every replicate in the order it actually ran, and test for a monotone trend.
order = []
seen = set()
cold = set()      # replicates excluded as warm-up, filled in by the run-order check below
ARMREP_T = re.compile(r"^(\d\d:\d\d:\d\d) == \S+ arm=(\S+) rep=(\d+)")
try:
    for line in open(f"{run_dir}/log.txt", errors="replace"):
        m = ARMREP_T.match(line)
        if m:
            k = (m.group(2), int(m.group(3)))
            if k not in seen:
                seen.add(k)
                order.append((m.group(1), k))
except FileNotFoundError:
    pass

if order:
    print("\nrun order — arm is confounded with time by construction, so check for drift")
    print("started\tarm\trep\tfps mean")
    seq = []
    for t, k in order:
        if k in culled or not fps.get(k):
            continue
        m = statistics.mean(fps[k])
        seq.append(m)
        print(f"{t}\t{k[0]}\t{k[1]}\t{m:.1f}")
    # Two shapes look alike early and mean opposite things. CONTINUOUS DRIFT (each replicate
    # faster than the last, by similar steps) contaminates every arm comparison and can only
    # be fixed by interleaving. A COLD START (replicate 1 slow, the rest in a tight band) is
    # just a warm-up cost: drop replicate 1 and the remaining comparison is sound. The step
    # sizes discriminate them, so measure the steps rather than eyeballing the direction.
    if len(seq) >= 3:
        steps = [b - a for a, b in zip(seq, seq[1:])]
        rises = sum(1 for s in steps if s > 0)
        tail = seq[1:]
        tail_spread = (max(tail) - min(tail)) / statistics.mean(tail) * 100 if len(tail) >= 2 else None
        first_gap = abs(seq[0] - statistics.mean(tail)) / statistics.mean(tail) * 100
        if tail_spread is not None and first_gap > 3 * max(tail_spread, 1e-9):
            cold_key = order[0][1]
            cold.add(cold_key)
            print(f"  => COLD START, not drift: replicate 1 ({cold_key[0]} rep {cold_key[1]}) sits")
            print(f"     {first_gap:.1f}% off the rest, while replicates 2..{len(seq)} hold within "
                  f"{tail_spread:.1f}% of each other.")
            print("     Excluded below as warm-up. NOTE this spends a replicate: the arm it came")
            print("     from now has one fewer, and an arm left with a single warm replicate has")
            print("     no internal estimate of its own variability.")
            print(f"     ({tail_spread:.1f}% is measured across MIXED arms, so it also absorbs any")
            print("      real tool effect — it is an upper bound on the floor, not the floor.)")
        elif rises == len(steps) or rises == 0:
            print("  !! MONOTONE across every replicate in run order, with no plateau — the rig")
            print("     is drifting and arm order rides that drift. Any on/off gap here is UNSAFE")
            print("     to attribute to the tool. Re-run INTERLEAVED (off,on,off,on) to fix it.")
        else:
            print(f"  no monotone trend ({rises} of {len(steps)} steps rise) — drift is not")
            print("  obviously driving the ordering, though the noise floor above still applies.")

print("\nthe noise floor — how far apart IDENTICAL replicates land")
print("(same arm, same config, same fort: whatever separates these is the rig, not the tool)")
floors = []
singles = []
for arm in ("off_baseline", "on_baseline", "off_crowded", "on_crowded"):
    means = []
    for k in sorted(fps):
        if k[0] == arm and k not in culled and k not in cold and fps[k]:
            means.append((k[1], statistics.mean(fps[k])))
    if len(means) == 1:
        singles.append((arm, means[0]))
    if len(means) < 2:
        continue
    vals = [m for _, m in means]
    spread = max(vals) - min(vals)
    pct = 100.0 * spread / statistics.mean(vals)
    floors.append(pct)
    print(f"  {arm}: " + ", ".join(f"rep {r} {m:.1f}" for r, m in means)
          + f"  -> spread {spread:.1f} fps ({pct:.1f}%)")
    # Identical replicates can still carry different LOADS — DF's own arrivals vary run to run,
    # and the crowded arms' placed animals decay at different rates. So part of a same-arm
    # spread may be real load, not rig noise. Show the loads and the slope they imply: if that
    # slope is wildly steeper than the between-arm charge per animal, the residual is noise.
    lo = [(statistics.mean(units[k]), statistics.mean(fps[k]))
          for k in sorted(fps) if k[0] == arm and k not in culled and k not in cold and units.get(k)]
    if len(lo) == 2:
        du = abs(lo[0][0] - lo[1][0]) / statistics.mean([lo[0][0], lo[1][0]]) * 100
        if du > 3.0:
            implied = (lo[1][1] - lo[0][1]) / (lo[1][0] - lo[0][0])
            print(f"     loads differed by {du:.1f}% too ({lo[0][0]:.1f} vs {lo[1][0]:.1f} units) "
                  f"-> implies {implied:+.2f} fps/animal; NOT usable as a noise estimate")
            floors.pop()          # this pair mixes load with noise; it cannot define the floor
        else:
            print(f"     at effectively the SAME load ({lo[0][0]:.1f} vs {lo[1][0]:.1f} units, "
                  f"{du:.1f}% apart) — this spread is pure rig noise")
for arm, (rep, m) in singles:
    print(f"  {arm}: only rep {rep} ({m:.1f}) survives — no within-arm spread available here.")
if floors:
    worst = max(floors)
    print(f"  => RESOLUTION FLOOR: {worst:.1f}%, from the {len(floors)} pair(s) that ran at matched")
    print("     load. An on/off gap smaller than this is NOT a cost;")
    print("     it is the rig. Report it as 'below the noise floor', never as a measured cost.")
else:
    print("  => no arm has two warm replicates yet; the floor is not yet estimable.")


# --------------------------------------------------------------- the fork ---
def arm_mean(arm, source):
    vals = [v for k, s in source.items()
            if k[0] == arm and k not in culled and k not in cold for v in s]
    return statistics.mean(vals) if vals else None

def arm_reps(arm, source):
    return sorted(k[1] for k in source if k[0] == arm and k not in culled and k not in cold)

print("\nper arm")
print("arm\treps\tfps mean\tunits mean\tsamples")
for arm in ("off_baseline", "on_baseline", "off_crowded", "on_crowded"):
    m = arm_mean(arm, fps) or arm_mean(arm, r_fps)
    if m is None:
        print(f"{arm}\t—\t(no completed replicates)")
        continue
    u = arm_mean(arm, units) or arm_mean(arm, r_units) or 0
    n = sum(len(s) for k, s in (fps if arm_mean(arm, fps) else r_fps).items()
            if k[0] == arm and k not in culled and k not in cold)
    print(f"{arm}\t{arm_reps(arm, fps) or arm_reps(arm, r_fps)}\t{m:.1f}\t{u:.1f}\t{n}")

print("\nthe fork — the tool's cost at each load level, and whether it grows")
gaps = {}
for level in ("baseline", "crowded"):
    off = arm_mean(f"off_{level}", fps) or arm_mean(f"off_{level}", r_fps)
    on = arm_mean(f"on_{level}", fps) or arm_mean(f"on_{level}", r_fps)
    if off is None or on is None:
        print(f"  {level}: incomplete — need both arms")
        continue
    gaps[level] = (off - on, 100.0 * (off - on) / off)
    verdict = "on is SLOWER" if on < off else ("on is FASTER" if on > off else "no difference")
    print(f"  {level}: off {off:.1f} fps, on {on:.1f} fps — {verdict} by {abs(off - on):.1f} fps "
          f"({abs(gaps[level][1]):.1f}%)")

if len(gaps) == 2:
    b, c = gaps["baseline"][0], gaps["crowded"][0]
    bp, cp = gaps["baseline"][1], gaps["crowded"][1]
    print(f"\n  baseline gap {b:+.1f} fps ({bp:+.1f}%) vs crowded gap {c:+.1f} fps ({cp:+.1f}%)")
    # SIGN FIRST. A gap is only a COST when tool-on runs slower (positive here, off minus on).
    # Both gaps came out negative on this run — tool-on was faster at both load levels — and an
    # earlier version of this block called that "THE COST SCALES WITH UNITS" purely on magnitude.
    # It would have put a measured cost into a report when the data shows the opposite sign.
    floor_pct = max(floors) if floors else None
    resolvable = floor_pct is not None and abs(bp) > floor_pct and abs(cp) > floor_pct
    direction = ("slower" if b > 0 else "faster", "slower" if c > 0 else "faster")
    if not resolvable:
        print(f"  => NOT RESOLVABLE: both gaps sit under the {floor_pct:.1f}% noise floor"
              if floor_pct is not None else "  => NOT RESOLVABLE: no noise floor estimable.")
        print(f"     (tool-on ran {direction[0]} at baseline and {direction[1]} when crowded).")
        print("     The defensible claim is an UPPER BOUND on the tool's cost, not a measurement,")
        print(f"     and the bound is the floor: below ~{floor_pct:.0f}%." if floor_pct else "")
        if b <= 0 and c <= 0:
            print("     Note the direction is consistent: tool-on was never the slower arm in any")
            print("     cell. That is evidence against a cost, not evidence of a benefit.")
    elif b > 0 and c > 0 and abs(c) > 1.5 * abs(b):
        print("  => THE COST SCALES WITH UNITS — on is slower at both levels and the crowded")
        print("     deficit is materially wider, which is what a job that walks units.active does.")
    elif b > 0 and c > 0:
        print("  => A CONSTANT COST — on is slower by a similar amount at both load levels.")
    else:
        print(f"  => tool-on ran {direction[0]} at baseline and {direction[1]} when crowded, both")
        print("     beyond the noise floor. A faster tool-on arm is not a speedup: check whether")
        print("     the roster held the population down (fewer units is fewer frames of work).")

# ------------------------------------------------- the load confound, measured ---
# off_baseline rep 1 started at 31 units and averaged 53.5 — DF's own churn moves the load
# around inside an arm, so raw arm means mix "the jobs cost cycles" with "the arms carried
# different populations" (prediction 4's mechanism). Fitting fps ~ units per arm is meant to
# separate them. CAVEAT, measured on this run: the within-replicate slopes are not stable
# (off_baseline gave -1.15 and +1.80 fps/unit across two identical reps), so at the baseline
# load range this fit is dominated by noise and its slope must NOT be quoted as DF's per-unit
# cost. The crowded arms swing units by ~60 against ~35 of natural churn, so the crowded-vs-
# baseline contrast is the better lever on per-unit cost; the fit is kept for that comparison
# and printed per replicate so instability is visible rather than averaged away.
def samples(arm):
    out = []
    for k, ticks in paired.items():
        if k[0] != arm or k in culled or k in cold:
            continue
        for d in ticks.values():
            if "fps" in d and "units" in d:
                out.append((d["units"], d["fps"]))
    return out

def fit(pts):
    """Least-squares slope/intercept of fps on units; None if the units never varied."""
    n = len(pts)
    if n < 3:
        return None
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    if sxx < 1e-9:
        return None
    b = sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx
    return (my - b * mx, b, mx)

all_pts = [p for arm in ("off_baseline", "on_baseline", "off_crowded", "on_crowded")
           for p in samples(arm)]
if all_pts:
    ref = statistics.median([p[0] for p in all_pts])
    print(f"\nfps against units — fitted WITHIN each replicate, read off at a common {ref:.0f} units")
    print("(pooling replicates corrupts this: two reps with different intercepts produce a slope")
    print(" that is an artifact of the gap between them. Per-replicate slopes shown so you can see")
    print(" whether the relationship is stable at all before trusting any adjusted figure.)")
    print("arm\trep\tn\tslope (fps per unit)\tfps @ ref\tunits range")
    adj, arm_slopes = {}, defaultdict(list)
    for arm in ("off_baseline", "on_baseline", "off_crowded", "on_crowded"):
        per_rep_adj = []
        for k in sorted(paired):
            if k[0] != arm or k in culled or k in cold:
                continue
            pts = [(d["units"], d["fps"]) for d in paired[k].values() if "fps" in d and "units" in d]
            f = fit(pts)
            if not f:
                continue
            a, b, _ = f
            per_rep_adj.append(a + b * ref)
            arm_slopes[arm].append(b)
            us = [p[0] for p in pts]
            print(f"{arm}\t{k[1]}\t{len(pts)}\t{b:+.2f}\t{a + b * ref:.1f}\t{min(us):.0f}-{max(us):.0f}")
        if per_rep_adj:
            adj[arm] = statistics.mean(per_rep_adj)
        if len(arm_slopes[arm]) >= 2:
            s = arm_slopes[arm]
            if min(s) < 0 < max(s):
                print(f"   !! {arm}: slopes disagree in SIGN ({min(s):+.2f} to {max(s):+.2f}) — "
                      "the units/fps relationship is not resolvable here; do not quote a per-unit cost.")
    # The slope is also the yardstick: DF itself charges this much per animal on the map, so
    # the tool's cost is most honestly quoted as "worth N extra animals" rather than as a
    # bare fps figure that means nothing without knowing the fort.
    # A per-unit cost is only worth quoting if every replicate agrees on its SIGN. Otherwise
    # the honest statement is that this design cannot resolve it — which is itself a result.
    # PHYSICAL PLAUSIBILITY. A positive slope says the fort ran FASTER as animals accumulated,
    # which DF does not do — more units is more work. So a positive fit is not a load effect at
    # all: inside one replicate, units climb monotonically through the season while the rig is
    # still settling, so the fit happily attributes warm-up (and any seasonal easing of the job
    # mix) to the unit count. Quoting it as "DF's charge per animal" would invert the sign of a
    # real cost. The honest per-unit lever is the BETWEEN-ARM contrast — crowded (~91 units)
    # against baseline (~53), both measured after warm-up — not this within-replicate slope.
    withheld = None
    all_slopes = [b for s in arm_slopes.values() for b in s]
    stable = bool(all_slopes) and (min(all_slopes) > 0 or max(all_slopes) < 0)
    per_unit = statistics.mean(all_slopes) if stable else None
    if per_unit is not None and per_unit > 0:
        print(f"  !! the within-replicate slope is POSITIVE ({per_unit:+.2f} fps/unit): the fort")
        print("     appears to speed up as animals accumulate, which DF does not do. This fit is")
        print("     tracking warm-up within the replicate, not load. Per-unit cost withheld; use")
        print("     the crowded-vs-baseline contrast instead.")
        per_unit, withheld = None, "positive — warm-up, not load"


    floor = max(floors) if floors else None
    for level in ("baseline", "crowded"):
        o, n = adj.get(f"off_{level}"), adj.get(f"on_{level}")
        if o is None or n is None:
            continue
        pct = 100.0 * (o - n) / o
        line = (f"  {level}, load held equal: off {o:.1f} vs on {n:.1f} — "
                f"{o - n:+.1f} fps ({pct:+.1f}%)")
        if per_unit:
            line += f" = the cost of {abs((o - n) / per_unit):.1f} extra animals"
        print(line)
        if floor is not None and abs(pct) < floor:
            print(f"     ^ BELOW THE {floor:.1f}% NOISE FLOOR — not a measured cost.")
    if per_unit:
        print(f"  DF's own charge for one more animal on this map: {per_unit:.2f} fps "
              f"(consistent in sign across {len(all_slopes)} replicates).")
    elif all_slopes:
        why = withheld or "they disagree in sign"
        print(f"  per-unit cost NOT quotable ({why}): replicate slopes run "
              f"{min(all_slopes):+.2f} to {max(all_slopes):+.2f} fps/unit.")
    print("  (a gap that survives this is the jobs; a gap that vanishes was the population.)")

# ------------------------------------- per-unit cost, the way the data supports it ---
# The within-replicate slope is unusable at baseline (units climb monotonically through the
# season, so it absorbs warm-up and comes out positive — the fort cannot speed up as animals
# accumulate). The BETWEEN-ARM contrast does not have that problem: crowded against baseline
# at the SAME tool state is two independent populations measured the same way, and the whole
# unit difference is deliberate rather than time-correlated. That is DF's own charge per
# animal, and it is the only honest yardstick for quoting what the tool costs.
print("\ncost per animal — crowded against baseline, within each tool state")
per_unit_between = {}
for st in ("off", "on"):
    b_f = arm_mean(f"{st}_baseline", fps)
    c_f = arm_mean(f"{st}_crowded", fps)
    b_u = arm_mean(f"{st}_baseline", units)
    c_u = arm_mean(f"{st}_crowded", units)
    if None in (b_f, c_f, b_u, c_u) or abs(c_u - b_u) < 1:
        print(f"  {st}: incomplete — need both load levels")
        continue
    slope = (c_f - b_f) / (c_u - b_u)
    per_unit_between[st] = slope
    print(f"  tool {st}: {b_u:.1f} units at {b_f:.1f} fps -> {c_u:.1f} units at {c_f:.1f} fps "
          f"= {slope:+.2f} fps per animal")
if len(per_unit_between) == 2:
    o, n = per_unit_between["off"], per_unit_between["on"]
    print(f"  DF charges {o:+.2f} fps/animal with the tool off, {n:+.2f} with it on.")
    # GATE. Each of these two slopes is a ratio of arm means, so it inherits BOTH arms' noise.
    # Quoting a percentage change between them when the arms themselves are 10-35% apart on
    # repeat is how a noise artifact becomes a headline. Only state it if every contributing
    # arm has two warm replicates AND both on/off gaps clear the measured floor.
    floor = max(floors) if floors else None
    reps_ok = all(len(arm_reps(f"{s}_{l}", fps)) >= 2
                  for s in ("off", "on") for l in ("baseline", "crowded"))
    gaps_ok = floor is not None and all(
        abs(100.0 * (arm_mean(f"off_{l}", fps) - arm_mean(f"on_{l}", fps))
            / arm_mean(f"off_{l}", fps)) > floor
        for l in ("baseline", "crowded")
        if arm_mean(f"off_{l}", fps) and arm_mean(f"on_{l}", fps))
    if o < 0 and n < 0 and reps_ok and gaps_ok:
        print(f"  The tool changes DF's per-animal charge by {100.0 * (n - o) / abs(o):+.1f}%.")
        print("  (That is the scaling question answered directly: a tool whose jobs walk the unit")
        print("   list makes each animal more expensive; one with a fixed cost leaves this alone.)")
    else:
        reasons = []
        if not reps_ok:
            reasons.append("an arm has fewer than two warm replicates")
        if not gaps_ok:
            reasons.append(f"the on/off gaps do not clear the {floor:.1f}% noise floor"
                           if floor is not None else "no floor is estimable yet")
        print(f"  NOT quoting a change in per-animal charge: {'; '.join(reasons)}.")
        print("  These two slopes are ratios of arm means and carry both arms' noise; comparing")
        print("  them here would report the rig's variance as a property of the tool.")
    # The "worth N animals" framing is the most quotable line in this file, which is exactly
    # why it must not run on an unreliable slope. It divides by the mean of the two charges,
    # so if those are noise the framing launders noise into a concrete-sounding claim.
    if reps_ok and gaps_ok:
        for level in ("baseline", "crowded"):
            off_f, on_f = arm_mean(f"off_{level}", fps), arm_mean(f"on_{level}", fps)
            if off_f is None or on_f is None:
                continue
            ref = (o + n) / 2
            if abs(ref) > 1e-6:
                print(f"  {level}: the on/off gap of {off_f - on_f:+.1f} fps is worth "
                      f"{abs((off_f - on_f) / ref):.1f} animals on the map.")
    else:
        print("  ('worth N animals' withheld for the same reason — it divides by these slopes.)")

# an independent cross-check: wall-clock stepping rate should tell the same story
print("\ncross-check — harness stepping rate (ticks_per_wall_s), which includes RPC overhead")
for arm in ("off_baseline", "on_baseline", "off_crowded", "on_crowded"):
    m = arm_mean(arm, tps)
    if m is not None:
        print(f"  {arm}: {m:.1f} t/s")
