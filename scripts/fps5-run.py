#!/usr/bin/env python3
"""FPS5: map size with the wild load held constant (mode `hold`), and one in-game year of play per map size with
speed, load and the process's resources sampled throughout (mode `long`).

Forts: FPS2E1..FPS2E6, fresh 7-dwarf embarks of side 1..6 at one site (region4 29,20), restored from .preverify.
Every (size, replicate) starts on a freshly started DF, so process age starts at zero. Sizes run in a shuffled order
per replicate (seeded), so slow drift of the host spreads over all sizes.

hold  (FPS5a): tool OFF; `cx-load clearwild` (every wild unit on every layer vanishes, every pool on the site's tiles
      is closed), one tick, `cx-load constwild 30` (30 prey land animals placed, pools closed again, nobody leaves);
      2,000 ticks warm-up; six 8-s stopwatch windows. The wild load is 30 on every map; citizens are the embark's 7.
long  (FPS5b): tool ON (the user's setup); `cx-load sustain` after the load and before every step (the site has no
      water: unsustained, all 20 dwarves of the first session died of thirst by ~190,000 ticks); stopwatch baseline, then PLAY ticks in steps of EVERY, a 3 x 6 s stopwatch
      reading after each step; then the split: aged/played (A1), fresh/played (A3), fresh/original (A4) -- process age
      = A1 vs A3 on the same save, fort change = A3 vs A4 in the same process.

Each reading records ticks/s, DF's own fps, citizens, units, wild (all / cavern), items, jobs and working citizens,
and -- through proc_pid_rusage (scripts/procstat.py) -- DF's CPU cores in use, system-time share, instructions per
cycle, physical footprint, resident and peak memory, page-ins, disk bytes read and written, wineserver's CPU, and
the host's 1-minute load.

Usage: fps5-run.py hold [--reps 3]
       fps5-run.py long [--reps 3] [--play 403200] [--every 16800] [--sizes 1,2,3,4,5,6]
Output: data/experiments/FPS5<a|b>/<run>/rows.tsv, log.txt
"""
import argparse, json, os, random, re, statistics, subprocess, sys, time
from typing import Any
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import procstat  # noqa: E402  (scripts/ on sys.path above; pyright: reportMissingImports)

ROOT = Path(__file__).resolve().parent.parent
CX = str(ROOT / "scripts" / "cx-lifecycle.sh")
RUN = datetime.now().strftime("%Y%m%d-%H%M%S")
YEAR = 403200
TOOL_ON = ("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); if not cfg.initialized then sw.captureDefault(cfg) end; "
           "cfg.enabled=true; cfg.groups.enabled=true; sw.saveConfig(cfg); sw.enableSched(); print('tool on')")
TOOL_OFF = ("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); if not cfg.initialized then sw.captureDefault(cfg) end; "
            "cfg.enabled=false; cfg.groups.enabled=false; cfg.ecology.enabled=false; sw.saveConfig(cfg); sw.disableSched(); print('tool off')")
LINE = re.compile(r"citizens (\d+) units (\d+) wild (\d+) items (\d+) map (\d+)x(\d+)x(\d+) fps (\S+) gfps (\S+) working (\d+) jobs (\d+) cavwild (\d+) dead (\d+)")
COLS = ["run", "mode", "rep", "size", "phase", "sample", "ticks_played", "tps", "tps_windows", "df_fps", "gfps", "citizens", "units",
        "wild", "cavwild", "items", "jobs", "working", "dead_citizens", "map_x", "map_y", "map_z", "df_cpu_cores", "df_sys_share", "df_ipc",
        "df_footprint_mb", "df_resident_mb", "df_max_footprint_mb", "df_pageins", "df_disk_read_mb", "df_disk_written_mb",
        "wine_cpu_cores", "load1", "session_wall_s", "step_wall_s", "step_cpu_cores"]

OUT: Path; _log: Any = None; rows: Any = None

def log(msg):
    line = f"{datetime.now().strftime('%H:%M:%S')} {msg}"
    print(line, flush=True); _log.write(line + "\n"); _log.flush()

def sh(*args, timeout=600, check=True):
    env = dict(os.environ, CX_RPC_TIMEOUT="45", CX_LOAD_TIMEOUT="400")
    p = subprocess.run([CX, *map(str, args)], capture_output=True, text=True, timeout=timeout, env=env)
    out = (p.stdout + p.stderr).replace("\r", "")
    if check and p.returncode != 0:
        raise RuntimeError(f"cx-lifecycle {' '.join(map(str, args))} rc={p.returncode}: {out.strip()[-300:]}")
    return out

def tick():
    m = re.search(r"tick=(\d+)", sh("state"))
    return int(m.group(1)) if m else -1

def load_line():
    m = LINE.search(sh("cmd", "cx-load", "line"))
    return m.groups() if m else ("",) * 13

def stamp():
    a = time.monotonic(); k = tick(); b = time.monotonic()
    return k, (a + b) / 2

def stopwatch(windows, secs):
    """Ticks/s per window, the tick counter stamped unpaused at each end; the step verb's overhead stays out."""
    sh("unpause"); time.sleep(1.0)
    s0 = procstat.snapshot()
    rates = []
    k0, t0 = stamp()
    for _ in range(windows):
        time.sleep(secs)
        k, t = stamp()
        d = k - k0 + (YEAR if k < k0 else 0)
        rates.append(d / (t - t0)); k0, t0 = k, t
    s1 = procstat.snapshot()
    sh("pause")
    return rates, s0, s1

class Session:
    def __init__(self, mode, rep, size):
        self.mode, self.rep, self.size = mode, rep, size
        self.t0 = time.monotonic(); self.played = 0; self.sample = 0
        self.extra = {}   # FPS6 (fps6-run.py) adds world columns here; they land in any COLS entry it appends

    def record(self, phase, rates, s0, s1, step_wall="", step_cpu=""):
        cit, units, wild, items, mx, my, mz, fps, gfps, working, jobs, cav, dead = load_line()
        dfr = procstat.rates(s0.get("df"), s1.get("df")); wr = procstat.rates(s0.get("wine"), s1.get("wine"))
        d = s1.get("df") or {}
        vals = {"run": RUN, "mode": self.mode, "rep": self.rep, "size": self.size, "phase": phase, "sample": self.sample,
                "ticks_played": self.played, "tps": f"{statistics.mean(rates):.1f}" if rates else "",
                "tps_windows": ",".join(f"{r:.0f}" for r in rates), "df_fps": fps, "gfps": gfps, "citizens": cit, "units": units,
                "wild": wild, "cavwild": cav, "items": items, "jobs": jobs, "working": working, "dead_citizens": dead, "map_x": mx, "map_y": my, "map_z": mz,
                "df_cpu_cores": f"{dfr.get('cpu_cores', 0):.3f}", "df_sys_share": f"{dfr.get('sys_share', 0):.3f}",
                "df_ipc": f"{dfr['ipc']:.3f}" if dfr.get("ipc") else "",
                "df_footprint_mb": f"{d.get('phys_footprint_mb', 0):.0f}", "df_resident_mb": f"{d.get('resident_mb', 0):.0f}",
                "df_max_footprint_mb": f"{d.get('max_footprint_mb', 0):.0f}", "df_pageins": d.get("pageins", ""),
                "df_disk_read_mb": f"{d.get('disk_read_mb', 0):.1f}", "df_disk_written_mb": f"{d.get('disk_written_mb', 0):.1f}",
                "wine_cpu_cores": f"{wr.get('cpu_cores', 0):.3f}", "load1": f"{s1.get('load1', 0):.2f}",
                "session_wall_s": f"{time.monotonic() - self.t0:.0f}", "step_wall_s": step_wall, "step_cpu_cores": step_cpu}
        vals.update(self.extra)
        rows.write("\t".join(str(vals.get(c, "")) for c in COLS) + "\n"); rows.flush()
        self.sample += 1
        return vals

def restart():
    sh("stop", timeout=200); sh("start", timeout=300)

def prune_autosaves(save):
    """DF's seasonal autosaves join the save list of the world being played; after a few year-long sessions region4's
    list outgrew its panel and the load verb could not see FPS2E3/E4 (FPS5b run 103823). Delete the autosave folders
    that belong to THIS save's world -- the experiment's own throwaway worlds -- and never any other world's."""
    rows_ = [l.split("\t") for l in sh("ui", "saves").splitlines() if l.startswith("SAVE\t")]
    world = next((r[2] for r in rows_ if len(r) > 2 and r[1] == save), None)
    gone = []
    for r in rows_:
        if len(r) > 2 and r[1].startswith("autosave") and world and r[2] == world:
            sh("save-delete", r[1], check=False); gone.append(r[1])
    if gone:
        log(f"    pruned {len(gone)} autosave(s) of world {world}: {', '.join(gone)}")

def load_fort(save, restore=True, tool=TOOL_ON, fresh=False):
    """fresh=True: restore (touched newest) BEFORE restarting DF -- DF reads its Continue list once at start, newest
    first, ~8 rows visible, no scroll key -- then load in the new process. fresh=False: load in the process as it is."""
    sh("title", timeout=300)
    prune_autosaves(save)
    if restore:
        sh("save-restore", f"{save}.preverify")
    if fresh:
        restart()
    sh("load", save, timeout=700)
    sh("fps", 1000, 60)
    sh("lua", tool)

def measure(sess, phase, windows=4, secs=8.0):
    rates, s0, s1 = stopwatch(windows, secs)
    v = sess.record(phase, rates, s0, s1)
    log(f"    {phase}: {v['tps']} t/s [{v['tps_windows']}]; cit {v['citizens']} wild {v['wild']} (cav {v['cavwild']}) items {v['items']}; "
        f"cpu {v['df_cpu_cores']} footprint {v['df_footprint_mb']} MB")
    return float(v["tps"])

def run_hold(sess):
    save = f"FPS2E{sess.size}"
    load_fort(save, tool=TOOL_OFF, fresh=True)
    log(f"    {sh('cmd', 'cx-load', 'clearwild').strip().splitlines()[-1]}")
    sh("step", 20)
    log(f"    {sh('cmd', 'cx-load', 'constwild', 30).strip().splitlines()[-1]}")
    sh("step", 2000)
    measure(sess, "hold", windows=6, secs=8.0)

def run_long(sess, play, every):
    save = f"FPS2E{sess.size}"
    played_save = f"FPS5P{RUN[-6:]}{sess.rep}{sess.size}"
    load_fort(save, fresh=True)
    sh("cmd", "cx-load", "sustain")   # 29 Sep: the first year-long session's 20 dwarves all died of THIRST (no water here)
    r = {"P0": measure(sess, "P0_fresh_original")}
    while sess.played < play:
        sh("cmd", "cx-load", "sustain")
        s0 = procstat.snapshot(); t0 = time.monotonic()
        out = sh("step", every, max(300, every // 20 + 120), timeout=every // 5 + 900)
        wall = time.monotonic() - t0; s1 = procstat.snapshot()
        m = re.search(r"stepped (\d+) ticks", out)
        sess.played += int(m.group(1)) if m else every
        cpu = procstat.rates(s0.get("df"), s1.get("df")).get("cpu_cores", 0)
        rates, a, b = stopwatch(3, 6.0)
        v = sess.record("play", rates, a, b, f"{wall:.1f}", f"{cpu:.3f}")
        if v["citizens"] in ("", "0"):
            raise RuntimeError(f"the settlement is gone at {sess.played} ticks (citizens {v['citizens']!r}, dead {v['dead_citizens']})")
        if sess.sample % 4 == 0:
            log(f"    play {sess.played:>7}: {v['tps']} t/s; cit {v['citizens']} wild {v['wild']} items {v['items']}; cpu {v['df_cpu_cores']} "
                f"dead {v['dead_citizens']} footprint {v['df_footprint_mb']} MB disk w {v['df_disk_written_mb']} MB load {v['load1']}")
    sh("save", played_save, timeout=400)
    r["A1"] = measure(sess, "A1_aged_played")
    # FPS5b 103823: DF reads its Continue list once at start, so the aged process cannot find a save restored after it
    # started -- the old A2 (aged process, original save) failed in 3 of 3 attempts. The split is now measured on ONE
    # save across the restart: process age = A1 (aged) vs A3 (fresh), both the played save; fort change = A3 vs A4,
    # both in the fresh process. The original is restored and touched BEFORE that restart, so the new list shows it.
    sh("title", timeout=300); prune_autosaves(save); sh("save-restore", f"{save}.preverify")
    restart(); sh("load", played_save, timeout=700); sh("fps", 1000, 60); sh("lua", TOOL_ON); sh("cmd", "cx-load", "sustain")
    r["A3"] = measure(sess, "A3_fresh_played")
    sh("title", timeout=300); sh("load", save, timeout=700); sh("fps", 1000, 60); sh("lua", TOOL_ON)
    r["A4"] = measure(sess, "A4_fresh_original")
    sh("title", timeout=300); sh("save-delete", played_save, check=False)
    log(f"  size {sess.size} rep {sess.rep}: process age {(r['A1'] / r['A3'] - 1) * 100:+.0f}% (played save, aged {r['A1']:.0f} vs fresh {r['A3']:.0f}); "
        f"fort change {(r['A3'] / r['A4'] - 1) * 100:+.0f}% (fresh process, played {r['A3']:.0f} vs original {r['A4']:.0f}); original at start {r['P0']:.0f}")

def main():
    global OUT, _log, rows
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["hold", "long"]); ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--play", type=int, default=YEAR); ap.add_argument("--every", type=int, default=16800)
    ap.add_argument("--sizes", default="1,2,3,4,5,6"); ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--only", help="re-run just these sessions, 'size:rep,size:rep' (a FAILED one), into --append's run")
    ap.add_argument("--append", help="an existing run directory to append rows to (its RUN id is kept)")
    a = ap.parse_args()
    global RUN
    if a.append:
        OUT = Path(a.append); RUN = OUT.name
    else:
        OUT = ROOT / "data/experiments" / ("FPS5a" if a.mode == "hold" else "FPS5b") / RUN
    OUT.mkdir(parents=True, exist_ok=True)
    _log = open(OUT / "log.txt", "a"); rows = open(OUT / "rows.tsv", "a")
    if rows.tell() == 0:
        rows.write("\t".join(COLS) + "\n")
    sizes = [int(x) for x in a.sizes.split(",")]
    (OUT / ("design-rerun.json" if a.append else "design.json")).write_text(json.dumps(vars(a), indent=1))
    log(f"== FPS5 {a.mode} run {RUN}: sizes {sizes}, {a.reps} reps" + (f", play {a.play} every {a.every}" if a.mode == "long" else ""))
    rng = random.Random(a.seed)
    only = {tuple(int(x) for x in p.split(":")) for p in a.only.split(",")} if a.only else None
    for rep in range(1, a.reps + 1):
        order = sizes[:]; rng.shuffle(order)
        if only:
            order = [k for k in order if (k, rep) in only]
        if not order:
            continue
        log(f"== rep {rep}: order {order}")
        for size in order:
            log(f"  -- size {size}x{size} rep {rep}")
            sess = Session(a.mode, rep, size)
            try:
                run_hold(sess) if a.mode == "hold" else run_long(sess, a.play, a.every)
            except Exception as e:   # one failed session is logged and the design goes on; a restart clears the rig
                log(f"  !! size {size} rep {rep} FAILED: {e!r}")
                try: restart()
                except Exception as e2: log(f"  !! restart failed too: {e2!r}")
    log("== FPS5 done")

if __name__ == "__main__":
    main()
