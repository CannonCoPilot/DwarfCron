#!/usr/bin/env python3
"""FPS4: does DF slow with play in one process, and does a save + reload or only a restart recover it?

FPS3 (28 Sep 2026) found a two-day-old DF running BOATS ~6x slower than a fresh one, and ~11% lost inside one run after
~200k simulated ticks. Playing a fort also grows it (migrants, items, corpses), so the curve alone mixes two causes. Per
replicate, on BOATS at tick cap 1000 / graphics 60 with seasonal-wildlife on:

  P0  fresh process, original fort      restart DF, restore BOATS.preverify, load, measure
  --  play PLAY_TICKS in chunks of 10,000, recording t/s, DF's fps, load and the process's resident memory
  A1  aged process,  played fort        save the played fort to a NEW folder, measure
  A2  aged process,  original fort      quit to title (no save), restore BOATS, load, measure
  A3  fresh process, played fort        restart DF, load the played save, measure
  A4  fresh process, original fort      quit, restore BOATS, load, measure (P0 again)

A2 vs P0/A4 is process age alone; A3 vs P0/A4 is fort growth alone; A1 is both. A measure is four 8-second stopwatch windows (tick
counter read unpaused at each end), after a 2-second warm-up. The played saves are deleted at the end.

Usage: fps4-run.py [--reps N] [--play TICKS]
Output: data/experiments/FPS4/<run>/rows.tsv, log.txt, summary.txt
"""
import argparse, os, re, statistics, subprocess, time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CX = str(ROOT / "scripts" / "cx-lifecycle.sh")
RUN = datetime.now().strftime("%Y%m%d-%H%M%S")
OUT = ROOT / "data/experiments/FPS4" / RUN
FORT, BACKUP = "BOATS", "BOATS.preverify"
PLAY_CHUNK = 10000
TOOL_ON = ("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); if not cfg.initialized then sw.captureDefault(cfg) end; "
           "cfg.enabled=true; cfg.groups.enabled=true; sw.saveConfig(cfg); sw.enableSched(); print('tool on')")
LINE = re.compile(r"citizens (\d+) units (\d+) wild (\d+) items (\d+) map \S+ fps (\S+) gfps (\S+) working (\d+) jobs (\d+)")

OUT.mkdir(parents=True, exist_ok=True)
_log = open(OUT / "log.txt", "a")
rows = open(OUT / "rows.tsv", "a")
if rows.tell() == 0:
    rows.write("run\trep\tphase\tchunk\tticks\twall_s\tticks_per_s\tdf_fps\tgfps\tcitizens\tunits\twild\titems\trss_mb\tabs_tick\n")

def log(msg):
    line = f"{datetime.now().strftime('%H:%M:%S')} {msg}"
    print(line, flush=True); _log.write(line + "\n"); _log.flush()

def sh(*args, timeout=600, check=True):
    env = dict(os.environ, CX_RPC_TIMEOUT="45")
    p = subprocess.run([CX, *map(str, args)], capture_output=True, text=True, timeout=timeout, env=env)
    out = (p.stdout + p.stderr).replace("\r", "")
    if check and p.returncode != 0:
        raise RuntimeError(f"cx-lifecycle {' '.join(map(str, args))} rc={p.returncode}: {out.strip()[-300:]}")
    return out

def df_rss_mb():
    p = subprocess.run(["pgrep", "-f", "Dwarf Fortress.exe"], capture_output=True, text=True)
    pid = (p.stdout.split() or [""])[0]
    if not pid:
        return 0
    r = subprocess.run(["ps", "-o", "rss=", "-p", pid], capture_output=True, text=True)
    return int(r.stdout.strip() or 0) // 1024

def tick():
    m = re.search(r"tick=(\d+)", sh("state"))
    return int(m.group(1)) if m else -1

def load_line():
    m = LINE.search(sh("cmd", "cx-load", "line"))
    return m.groups() if m else ("",) * 8

def step(n, rep, phase, i):
    t0 = time.monotonic()
    out = sh("step", n, max(120, n // 20 + 60))
    wall = time.monotonic() - t0
    m = re.search(r"stepped (\d+) ticks", out)
    got = int(m.group(1)) if m else 0
    cit, units, wild, items, fps, gfps, _work, _jobs = load_line()
    tps = got / wall if wall > 0 else 0
    rows.write(f"{RUN}\t{rep}\t{phase}\t{i}\t{got}\t{wall:.2f}\t{tps:.1f}\t{fps}\t{gfps}\t{cit}\t{units}\t{wild}\t{items}\t{df_rss_mb()}\t{tick()}\n")
    rows.flush()
    return tps, fps, units, items

YEAR = 403200

def window_rate(rep, phase, windows=4, secs=8.0):
    """Ticks per wall second read the way a stopwatch would: unpaused, the tick counter read at the start and end of
    each window. The step verb's fixed ~5 s per call (polling, pause handling) stays out of the figure -- it had
    squeezed a fresh DF's ~500 t/s into ~220 (smoke run 232951)."""
    sh("unpause"); time.sleep(2.0)
    rates = []
    def stamp():   # the tick read takes ~0.3-0.5 s over RPC: time it at the read's midpoint
        a = time.monotonic(); k = tick(); b = time.monotonic()
        return k, (a + b) / 2
    k_prev, t_prev = stamp()
    for i in range(windows):
        time.sleep(secs)
        k, t = stamp()
        d = k - k_prev
        if d < 0:
            d += YEAR
        rates.append(d / (t - t_prev))
        t_prev, k_prev = t, k
    sh("pause")
    cit, units, wild, items, fps, gfps, _w, _j = load_line()
    rss = df_rss_mb()
    for i, r in enumerate(rates):
        rows.write(f"{RUN}\t{rep}\t{phase}\t{i}\t\t{secs}\t{r:.1f}\t{fps}\t{gfps}\t{cit}\t{units}\t{wild}\t{items}\t{rss}\t{k_prev}\n")
    rows.flush()
    return rates, fps, units, items, rss

def measure(rep, phase):
    rates, fps, units, items, rss = window_rate(rep, phase)
    tps = statistics.mean(rates)
    log(f"  {phase}: {tps:.0f} t/s (windows {', '.join(f'{r:.0f}' for r in rates)}); DF fps {fps}; units {units} items {items}; rss {rss} MB")
    return tps

def restart():
    sh("stop", timeout=200); sh("start", timeout=300)

def fresh_load(save, restore=True):
    sh("title", timeout=300)
    if restore:
        sh("save-restore", BACKUP)
    sh("load", save, timeout=600)
    sh("fps", 1000, 60)
    sh("lua", TOOL_ON)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--reps", type=int, default=2); ap.add_argument("--play", type=int, default=300000)
    ap.add_argument("--resume", help="finish rep 1 of an existing run from A2 in the process as it stands: RUN,PLAYED_SAVE,P0,A1")
    a = ap.parse_args()
    global RUN, OUT, _log, rows
    summary = []
    first = 1
    if a.resume:
        # run 20260928-234451 crashed after A1 when a queued popup blocked the quit; the process was never restarted,
        # so A2 is still 'aged, original' (300,000 ticks played in it)
        RUN, played, p0, a1 = a.resume.split(",")
        OUT = ROOT / "data/experiments/FPS4" / RUN
        _log = open(OUT / "log.txt", "a"); rows = open(OUT / "rows.tsv", "a")
        log(f"== FPS4 run {RUN}: resuming rep 1 at A2 in the same aged process")
        r = {"P0": float(p0), "A1": float(a1)}
        summary.append(finish(1, played, r))
        first = 2
    else:
        log(f"== FPS4 run {RUN}: {a.reps} reps, play {a.play} ticks per rep, BOATS, cap 1000 / graphics 60, tool on")
    for rep in range(first, a.reps + 1):
        played = f"FPS4P{RUN[-6:]}{rep}"
        log(f"== rep {rep}")
        restart(); fresh_load(FORT)
        r = {"P0": measure(rep, "P0_fresh_original")}
        for i in range(a.play // PLAY_CHUNK):
            step(PLAY_CHUNK, rep, "play", i)
            if i % 5 == 4:   # the curve: a stopwatch reading every 50,000 ticks of play
                rates, fps, units, items, rss = window_rate(rep, f"curve{(i + 1) * PLAY_CHUNK}", windows=3, secs=6.0)
                log(f"  play {(i + 1) * PLAY_CHUNK:>7} t: {statistics.mean(rates):.0f} t/s, DF fps {fps}, units {units}, items {items}, rss {rss} MB")
        sh("save", played, timeout=300)
        log(f"  saved the played fort as {played}")
        r["A1"] = measure(rep, "A1_aged_played")
        summary.append(finish(rep, played, r))
    with open(OUT / "summary.txt", "a") as f:
        f.write("\n".join(summary) + "\n")
    log("== FPS4 done")

def finish(rep, played, r):
    fresh_load(FORT); r["A2"] = measure(rep, "A2_aged_original")
    restart(); fresh_load(played, restore=False); r["A3"] = measure(rep, "A3_fresh_played")
    fresh_load(FORT); r["A4"] = measure(rep, "A4_fresh_original")
    sh("title", timeout=300); sh("save-delete", played, check=False)
    base = statistics.mean([r["P0"], r["A4"]])
    line = (f"rep {rep}: fresh/original {r['P0']:.0f} & {r['A4']:.0f}; aged/original {r['A2']:.0f} ({(r['A2'] / base - 1) * 100:+.0f}%, process age); "
            f"fresh/played {r['A3']:.0f} ({(r['A3'] / base - 1) * 100:+.0f}%, fort change); aged/played {r['A1']:.0f} ({(r['A1'] / base - 1) * 100:+.0f}%, both)")
    log(line)
    return line

if __name__ == "__main__":
    main()
