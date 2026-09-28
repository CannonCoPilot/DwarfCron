#!/usr/bin/env python3
"""FPS1 tally: ticks per wall second by arm and replicate (first 1,000-tick step discarded), with the load the
sampler saw (citizens, units, items) and the achieved frame and graphics rates. Usage: fps1-tally.py <run_dir>"""
import csv, re, statistics, sys
from pathlib import Path

run = Path(sys.argv[1])
tps: dict[tuple[str, str], list[float]] = {}
for r in csv.DictReader(open(run / "rows.tsv"), delimiter="\t"):
    if r["metric"] == "ticks_per_wall_s" and r["value"]:
        tps.setdefault((r["arm"], r["rep"]), []).append(float(r["value"]))

load: dict[tuple[str, str], list[dict]] = {}
arm = rep = None
for line in open(run / "log.txt"):
    m = re.search(r"== FPS1 arm=(\S+) rep=(\d+)", line)
    if m:
        arm, rep = m.group(1), m.group(2)
    m = re.search(r"fps1 load: citizens (\d+) units (\d+) items (\d+) map \S+ fps (\S+) gfps (\S+) caps", line)
    if m and arm:
        load.setdefault((arm, rep), []).append({"cit": int(m.group(1)), "units": int(m.group(2)), "items": int(m.group(3)),
                                                "fps": float(m.group(4)), "gfps": float(m.group(5))})

by_arm: dict[str, list[float]] = {}
print(f"{'arm':<17} rep  t/s (steps 2+)                         mean   citizens units items  achieved gfps")
for (a, r), v in sorted(tps.items()):
    keep = v[1:]
    mean = statistics.mean(keep) if keep else float("nan")
    by_arm.setdefault(a, []).append(mean)
    L = load.get((a, r), [])
    g = [x["gfps"] for x in L[1:]] or [0]
    lx = L[-1] if L else {}
    print(f"{a:<17} {r:>3}  {' '.join(f'{x:5.0f}' for x in keep):<36} {mean:6.0f}   {lx.get('cit', '?'):>8} {lx.get('units', '?'):>5} {lx.get('items', '?'):>5}  {statistics.mean(g):5.1f}")
print()
means = {a: statistics.mean(v) for a, v in by_arm.items()}
for a, v in sorted(means.items()):
    reps = by_arm[a]
    print(f"{a:<17} mean {v:6.0f} t/s  (reps {', '.join(f'{x:.0f}' for x in reps)}; spread {abs(reps[0] - reps[-1]) / v * 100 if len(reps) > 1 and v else 0:.0f}%)")
def ratio(x, y, what):
    if x in means and y in means and means[y]:
        print(f"  {what}: {means[x]:.0f} vs {means[y]:.0f} t/s = {(means[x] / means[y] - 1) * 100:+.0f}%")
print()
ratio("B_ctrl_g60", "A_ctrl_g10", "graphics cap 60 vs 10 on CTRL (7 dwarves)")
ratio("D_boats_g60", "C_boats_g10", "graphics cap 60 vs 10 on BOATS (30 dwarves)")
ratio("C_boats_g10", "A_ctrl_g10", "BOATS vs CTRL at graphics cap 10 (fort load)")
ratio("D_boats_g60", "B_ctrl_g60", "BOATS vs CTRL at graphics cap 60 (fort load)")
ratio("E_boats_g60_off", "D_boats_g60", "tool off vs on, BOATS at 60")
