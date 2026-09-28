#!/usr/bin/env python3
"""FPS2 tally: ticks per wall second by arm and replicate (first 1,000-tick step discarded) against the load the
sampler saw at each step (citizens, active units, wild units, items, map area), then a pooled least-squares fit of
wall milliseconds per tick on that load, so each factor gets a cost per unit. Usage: fps2-tally.py <run_dir>"""
import csv, json, re, statistics, sys
from pathlib import Path

run = Path(sys.argv[1])
man = json.load(open(run / "manifest.json"))
order = [a["name"] for a in man["arms"]]

tps: dict[tuple[str, str], list[float]] = {}
for r in csv.DictReader(open(run / "rows.tsv"), delimiter="\t"):
    if r["metric"] == "ticks_per_wall_s" and r["value"]:
        tps.setdefault((r["arm"], r["rep"]), []).append(float(r["value"]))

LOAD = re.compile(r"load: citizens (\d+) units (\d+) wild (\d+) items (\d+) map (\d+)x(\d+)x(\d+) fps (\S+) gfps (\S+)")
load: dict[tuple[str, str], list[dict]] = {}
arm = rep = None
for line in open(run / "log.txt"):
    m = re.search(r"== FPS2 arm=(\S+) rep=(\d+)", line)
    if m:
        arm, rep = m.group(1), m.group(2)
    m = LOAD.search(line)
    if m and arm and rep:
        g = [int(x) for x in m.groups()[:7]]
        load.setdefault((arm, rep), []).append({"cit": g[0], "units": g[1], "wild": g[2], "items": g[3],
                                                "area": g[4] * g[5], "z": g[6], "gfps": float(m.group(9))})

def mean(v):
    return statistics.mean(v) if v else float("nan")

print(f"{'arm':<18} rep  t/s per step (2+)                     mean  citizens units  wild items  area(t2)  z  gfps")
by_arm: dict[str, list[float]] = {}
points = []   # (ms/tick, citizens, units, wild, items, area) per step
for a in order:
    for r in sorted({k[1] for k in tps if k[0] == a}):
        keep = tps[(a, r)][1:]
        by_arm.setdefault(a, []).append(mean(keep))
        L = load.get((a, r), [])
        # the load line printed at the start of step i describes the fort that step ran on
        for i, v in enumerate(keep, start=1):
            if i < len(L) and v > 0:
                x = L[i]
                points.append((1000.0 / v, x["cit"], x["units"], x["wild"], x["items"], x["area"]))
        lx = L[-1] if L else {}
        g = [x["gfps"] for x in L[1:]] or [0]
        print(f"{a:<18} {r:>3}  {' '.join(f'{x:5.0f}' for x in keep):<36} {mean(keep):6.0f}  {lx.get('cit', '?'):>8} {lx.get('units', '?'):>5}"
              f" {lx.get('wild', '?'):>5} {lx.get('items', '?'):>5} {lx.get('area', '?'):>8} {lx.get('z', '?'):>3} {mean(g):5.1f}")

print()
base = order[0]
means = {a: mean(v) for a, v in by_arm.items()}
for a in order:
    if a not in means:
        continue
    reps = by_arm[a]
    spread = abs(reps[0] - reps[-1]) / means[a] * 100 if len(reps) > 1 and means[a] else 0
    rel = f"{(means[a] / means[base] - 1) * 100:+4.0f}% vs {base}" if a != base and base in means else ""
    print(f"{a:<18} mean {means[a]:6.0f} t/s  (reps {', '.join(f'{x:.0f}' for x in reps)}; spread {spread:.0f}%)  {rel}")

# Pooled fit: ms per tick = b0 + b_cit*citizens + b_other*(units - citizens) + b_items*items/1000 + b_area*area.
# Plain normal equations; five columns do not need numpy.
if len(points) >= 8:
    X = [[1.0, p[1], p[2] - p[1], p[4] / 1000.0, p[5]] for p in points]
    y = [p[0] for p in points]
    k = len(X[0])
    A: list[list[float]] = [[float(sum(X[n][i] * X[n][j] for n in range(len(X)))) for j in range(k)] for i in range(k)]
    b: list[float] = [float(sum(X[n][i] * y[n] for n in range(len(X)))) for i in range(k)]
    try:
        for c in range(k):   # Gauss-Jordan with partial pivoting
            p = max(range(c, k), key=lambda r: abs(A[r][c]))
            A[c], A[p], b[c], b[p] = A[p], A[c], b[p], b[c]
            if abs(A[c][c]) < 1e-12:
                raise ZeroDivisionError(f"column {c} is collinear with the others (a factor never varied)")
            for r in range(k):
                if r != c:
                    f = A[r][c] / A[c][c]
                    A[r] = [A[r][j] - f * A[c][j] for j in range(k)]
                    b[r] -= f * b[c]
        coef = [b[i] / A[i][i] for i in range(k)]
        pred = [sum(coef[i] * row[i] for i in range(k)) for row in X]
        ybar = mean(y)
        r2 = 1 - sum((yi - pi) ** 2 for yi, pi in zip(y, pred)) / sum((yi - ybar) ** 2 for yi in y)
        print(f"\npooled fit over {len(points)} steps: ms/tick = {coef[0]:.3f}"
              f" + {coef[1]:.4f}/citizen + {coef[2]:.4f}/other unit + {coef[3]:.4f}/1000 items + {coef[4]:.5f}/map tile2   (R2 {r2:.2f})")
        print("  (map tile2 = x*y in tiles; a 4x4 embark is 192x192 = 36,864)")
    except ZeroDivisionError as e:
        print(f"\npooled fit skipped: {e}")
