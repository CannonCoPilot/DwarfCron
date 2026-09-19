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
    elif r["metric"] == "units_active":
        units[k].append(v)
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

tallylib.drop_incomplete(run_dir, fps, units, r_fps, r_units, citizens, state, placed, tps)

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

# --------------------------------------------------------------- the fork ---
def arm_mean(arm, source):
    vals = [v for k, s in source.items() if k[0] == arm and k not in culled for v in s]
    return statistics.mean(vals) if vals else None

def arm_reps(arm, source):
    return sorted(k[1] for k in source if k[0] == arm and k not in culled)

print("\nper arm")
print("arm\treps\tfps mean\tunits mean\tsamples")
for arm in ("off_baseline", "on_baseline", "off_crowded", "on_crowded"):
    m = arm_mean(arm, fps) or arm_mean(arm, r_fps)
    if m is None:
        print(f"{arm}\t—\t(no completed replicates)")
        continue
    u = arm_mean(arm, units) or arm_mean(arm, r_units) or 0
    n = sum(len(s) for k, s in (fps if arm_mean(arm, fps) else r_fps).items()
            if k[0] == arm and k not in culled)
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
    if abs(bp) < 3 and abs(cp) < 3:
        print("  => THE COST IS NEGLIGIBLE at both load levels — under 3% either way.")
    elif abs(c) > 1.5 * abs(b):
        print("  => THE COST SCALES WITH UNITS — the crowded gap is materially wider than the baseline one.")
    elif abs(b) > 1.5 * abs(c):
        print("  => the gap NARROWS under load — not a per-unit cost; read the receipts before claiming why.")
    else:
        print("  => A CONSTANT COST — the same deficit at both load levels, not a per-unit walk.")
    if c < 0:
        print("  => note: `on` ran FASTER when crowded — check whether the roster held the population down.")

# an independent cross-check: wall-clock stepping rate should tell the same story
print("\ncross-check — harness stepping rate (ticks_per_wall_s), which includes RPC overhead")
for arm in ("off_baseline", "on_baseline", "off_crowded", "on_crowded"):
    m = arm_mean(arm, tps)
    if m is not None:
        print(f"  {arm}: {m:.1f} t/s")
