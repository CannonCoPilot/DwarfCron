#!/usr/bin/env python3
"""FPS5 analysis. Usage: fps5-analyze.py <FPS5a run dir> [<FPS5b run dir>]

FPS5a (wild held at 30): ticks/s by map size, and a log-log fit of ms/tick on map area (tiles, x*y).
FPS5b (a year per session): for every map size --
  * the play curve: log(t/s) on ticks played, per size (slope = % speed lost per 100k ticks);
  * resources: physical-footprint growth (MB per 100k ticks), disk written (MB per 100k ticks), CPU cores used,
    system-time share and instructions per cycle, first quarter vs last quarter of play;
  * the four-way split (FPS4's design): process age = aged/original vs fresh/original; fort change = fresh/played
    vs fresh/original;
  * a pooled model of ms/tick on ticks played, map area, citizens, wild units and items (OLS, standard errors), so
    session age is separated from the load the fort carries at each sample.
"""
import csv, statistics, sys
from collections import defaultdict
from pathlib import Path
import numpy as np

def rows_of(d):
    return [r for r in csv.DictReader(open(Path(d) / "rows.tsv"), delimiter="\t") if r.get("tps")]

def f(r, k, default=np.nan):
    try:
        return float(r[k])
    except (KeyError, ValueError, TypeError):
        return default

def ols(X, y, names):
    X, y = np.asarray(X, float), np.asarray(y, float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    n, k = X.shape
    s2 = resid @ resid / max(1, n - k)
    cov = s2 * np.linalg.pinv(X.T @ X)
    se = np.sqrt(np.diag(cov))
    r2 = 1 - (resid @ resid) / ((y - y.mean()) @ (y - y.mean()))
    print(f"  n={n}, R2={r2:.3f}")
    for nm, b, s in zip(names, beta, se):
        print(f"    {nm:<26} {b:>12.5f}  (se {s:.5f}, t {b / s if s else float('nan'):>6.1f})")
    return beta

def part_a(d):
    rs = [r for r in rows_of(d) if r["phase"] == "hold"]
    print(f"== FPS5a {d}: {len(rs)} sessions, wild held (constwild 30), tool off")
    by = defaultdict(list)
    for r in rs:
        by[int(r["size"])].append(r)
    print(f"  {'size':<5} {'area t2':>8}  t/s per rep            mean   ms/tick  wild  cav  cit  cpu cores")
    xs, ys = [], []
    for k in sorted(by):
        g = by[k]; t = [f(r, "tps") for r in g]; area = f(g[0], "map_x") * f(g[0], "map_y")
        m = statistics.mean(t)
        print(f"  {k}x{k:<3} {area:>8.0f}  {', '.join(f'{x:.0f}' for x in t):<22} {m:>6.0f}  {1000 / m:>7.2f}  "
              f"{'/'.join(r['wild'] for r in g):>5} {'/'.join(r['cavwild'] for r in g):>4} {'/'.join(r['citizens'] for r in g):>4}  "
              f"{statistics.mean(f(r, 'df_cpu_cores') for r in g):.2f}")
        for x in t:
            xs.append(np.log(area)); ys.append(np.log(1000 / x))
    print("  log(ms/tick) = a + b*log(area):  b = the elasticity of tick cost to map area")
    ols(np.column_stack([np.ones(len(xs)), xs]), ys, ["a", "b (elasticity)"])

def part_b(d):
    rs = rows_of(d)
    print(f"\n== FPS5b {d}: {len(rs)} readings")
    sess = defaultdict(list)
    for r in rs:
        sess[(int(r["size"]), int(r["rep"]))].append(r)
    sizes = sorted({k for k, _ in sess})
    print("\n-- play curve per size: log(t/s) on ticks played; start and end t/s; resources")
    print(f"  {'size':<5} {'%/100k t':>9} {'t/s start':>10} {'t/s end':>8} {'MB/100k':>8} {'diskW MB/100k':>13} {'cores q1->q4':>13} {'sys q1->q4':>11} {'IPC q1->q4':>11} {'cit end':>8} {'wild end':>9}")
    for k in sizes:
        xs, ys, fp, dw = [], [], [], []
        start, end, q1, q4, cit, wild = [], [], [], [], [], []
        for (kk, rep), g in sess.items():
            if kk != k:
                continue
            p0 = [r for r in g if r["phase"] == "P0_fresh_original"]
            play = sorted([r for r in g if r["phase"] == "play"], key=lambda r: f(r, "ticks_played"))
            if not play:
                continue
            start += [f(r, "tps") for r in p0]
            end.append(f(play[-1], "tps")); cit.append(play[-1]["citizens"]); wild.append(play[-1]["wild"])
            for r in play:
                xs.append(f(r, "ticks_played") / 1e5); ys.append(np.log(f(r, "tps")))
            t = np.array([f(r, "ticks_played") / 1e5 for r in play])
            fp.append(np.polyfit(t, [f(r, "df_footprint_mb") for r in play], 1)[0])
            dw.append((f(play[-1], "df_disk_written_mb") - f(play[0], "df_disk_written_mb")) / max(1e-9, t[-1] - t[0]))
            n = len(play); q1 += play[: max(1, n // 4)]; q4 += play[-max(1, n // 4):]
        if not xs:
            continue
        slope = np.polyfit(xs, ys, 1)[0]
        mq = lambda g, key: statistics.mean(f(r, key) for r in g)
        print(f"  {k}x{k:<3} {(np.exp(slope) - 1) * 100:>+8.1f}% {statistics.mean(start):>10.0f} {statistics.mean(end):>8.0f} {statistics.mean(fp):>8.0f} "
              f"{statistics.mean(dw):>13.1f} {mq(q1, 'df_cpu_cores'):>5.2f}->{mq(q4, 'df_cpu_cores'):<5.2f} {mq(q1, 'df_sys_share'):>4.2f}->{mq(q4, 'df_sys_share'):<4.2f} "
              f"{mq(q1, 'df_ipc'):>4.2f}->{mq(q4, 'df_ipc'):<4.2f} {'/'.join(cit):>8} {'/'.join(wild):>9}")

    print("\n-- four-way split per size (mean over reps; % vs the mean of P0 and A4)")
    for k in sizes:
        acc = defaultdict(list)
        for (kk, rep), g in sess.items():
            if kk == k:
                for r in g:
                    acc[r["phase"]].append(f(r, "tps"))
        if not acc.get("A4_fresh_original"):
            continue
        base = statistics.mean(acc["P0_fresh_original"] + acc["A4_fresh_original"])
        pc = lambda ph: (statistics.mean(acc[ph]) / base - 1) * 100 if acc.get(ph) else float("nan")
        print(f"  {k}x{k}: base {base:.0f} t/s; process age {pc('A2_aged_original'):+.0f}%; fort change {pc('A3_fresh_played'):+.0f}%; both {pc('A1_aged_played'):+.0f}%")

    print("\n-- pooled model over play readings: ms/tick on session age, map area and the fort's load")
    play = [r for r in rs if r["phase"] == "play"]
    X = [[1, f(r, "ticks_played") / 1e5, f(r, "map_x") * f(r, "map_y") / 1e4, f(r, "citizens"), f(r, "wild"), f(r, "items") / 1000] for r in play]
    y = [1000 / f(r, "tps") for r in play]
    ols(X, y, ["intercept (ms)", "per 100k ticks played", "per 10k map tiles", "per citizen", "per wild unit", "per 1000 items"])
    print("\n-- does speed track the process's growth? ms/tick on footprint, within the same model")
    X2 = [row + [f(r, "df_footprint_mb") / 100] for row, r in zip(X, play)]
    ols(X2, y, ["intercept (ms)", "per 100k ticks played", "per 10k map tiles", "per citizen", "per wild unit", "per 1000 items", "per 100 MB footprint"])

if __name__ == "__main__":
    part_a(sys.argv[1])
    if len(sys.argv) > 2:
        part_b(sys.argv[2])
