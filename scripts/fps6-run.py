#!/usr/bin/env python3
"""FPS6: world size and history length on fortress speed (design: experiments/FPS6-design.md).

Worlds: SMALLER (33x33), SMALL (65x65), MEDIUM (129x129) x 5, 125, 500 years x seeds 6101, 6102, plus LARGE (257x257)
at 125 years x the same two seeds: 20 worlds. The same two seeds in every cell, so within a size the history factor is
paired: same seed, same terrain rules, only the end year differs. The MEDIUM@500 world of seed 6101 is generated first
(the pilot): if it fails to generate or embark, the run stops there.

gen   per world, on a freshly started DF: genworld (the preset by title; the params line must show the expected dims),
      survey (TEMPERATE rows), the site rule, a 3x3 embark (CX_EMBARK_SIZE=3) at offset 6,6 of the chosen tile, a
      .preverify backup of the fort, and the pristine world folder moved out of the save directory (the "existing
      world" list would otherwise grow by one per world). One row per world in worlds.tsv.
play  each world twice, in two shuffled passes (every world's first session before any second one): restore the
      fort (touched newest) before restarting DF, load (timed), `cx-load world` (the world's scale) into loads.tsv,
      `cx-load sustain`, a 4 x 8 s stopwatch baseline, then one season (100,800 ticks) in steps of 16,800 with FPS5's
      full reading and `cx-load guests` at every step, into rows.tsv (FPS5's columns plus the world's).

Site rule, level 1: GRASSLAND/SAVANNA/SHRUBLAND_TEMPERATE; savagery < 33; evilness <= 66; no river, lake, site or
volcano on the tile; no river or ocean on its ring; >= 5 of 8 neighbours the same biome. Level 2 (recorded): the same
biomes, savagery < 50, evilness <= 66, no river, lake or site on the tile, no ocean on the ring. Among the tiles that
qualify, the one nearest the world's centre.

Usage: fps6-run.py gen  [--append <dir>] [--worlds M500a,S5b,...]
       fps6-run.py play --append <dir> [--sessions 2] [--play 100800] [--every 16800] [--worlds ...]
       fps6-run.py all  [--append <dir>]
Output: data/experiments/FPS6/<run>/{worlds.tsv, loads.tsv, rows.tsv, log.txt}
"""
import argparse, csv, importlib, json, os, random, re, subprocess, sys, time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
f5: Any = importlib.import_module("fps5-run")   # FPS5's session, stopwatch and reading code, reused as is
import procstat  # noqa: E402

ROOT = f5.ROOT
SEASON = 100800
SIZES = {"SMALLER": ("SMALLER_REGION", 33), "SMALL": ("SMALL_REGION", 65), "MEDIUM": ("MEDIUM_REGION", 129), "LARGE": ("LARGE_REGION", 257)}
SEEDS = {"a": 6101, "b": 6102}
BIOMES = ("GRASSLAND_TEMPERATE", "SAVANNA_TEMPERATE", "SHRUBLAND_TEMPERATE")
WORLD_COLS = ["world", "size_name", "world_dim", "years", "seed"]
f5.COLS = f5.COLS + WORLD_COLS + ["merchants", "visitors", "invaders"]
WORLDS_COLS = WORLD_COLS + ["status", "folder", "save", "gen_wall_s", "rejection", "rx", "ry", "biome", "sav", "evil", "same8",
                            "rule_level", "qualifying", "embark_wall_s", "save_mb", "note"]
LOADS_COLS = WORLD_COLS + ["session", "load_wall_s", "save_mb", "df_footprint_mb", "df_resident_mb", "dims", "year", "hf", "hf_alive",
                           "events", "collections", "entities", "civs", "sites", "artifacts", "armies", "army_controllers",
                           "units_all", "near_civ", "near_civ_sites", "near_civ_hf", "near_civ_race"]

def cfg(var):
    return subprocess.run(["bash", "-c", f"source '{ROOT}/scripts/cx-config.sh' >/dev/null 2>&1; echo \"${var}\""],
                          capture_output=True, text=True).stdout.strip()

SAVE_DIR = Path(cfg("DF_SAVE_DIR"))
ARCHIVE = Path(cfg("CX_SNAPSHOT_DIR")) / "fps6-worlds"

def sh(*args, timeout=900, env=None, check=True):
    """f5.sh with other deadlines: worldgen and a 257x257 survey outlast FPS5's 45 s RPC deadline."""
    e = {**os.environ, "CX_RPC_TIMEOUT": "45", "CX_LOAD_TIMEOUT": "600", **(env or {})}   # a caller's value wins (the survey's 1200)
    p = subprocess.run([f5.CX, *map(str, args)], capture_output=True, text=True, timeout=timeout, env=e)
    out = (p.stdout + p.stderr).replace("\r", "")
    if check and p.returncode != 0:
        raise RuntimeError(f"cx-lifecycle {' '.join(map(str, args))} rc={p.returncode}: {out.strip()[-400:]}")
    return out

def design():
    """The 20 worlds, pilot first. Key: size letter + years + seed letter (M500a = MEDIUM, 500 years, seed 6101)."""
    ws = [(s, y, k) for s in ("SMALLER", "SMALL", "MEDIUM") for y in (5, 125, 500) for k in SEEDS] + [("LARGE", 125, k) for k in SEEDS]
    ws.sort(key=lambda w: (w != ("MEDIUM", 500, "a"),))
    return [{"world": f"{('X' if s == 'SMALLER' else s[0])}{y}{k}", "size_name": s, "world_dim": SIZES[s][1], "years": y,
             "seed": SEEDS[k]} for s, y, k in ws]

def table(path, cols):
    """Append-only TSV; returns (rows already there, writer)."""
    old = list(csv.DictReader(open(path), delimiter="\t")) if path.exists() else []
    fh = open(path, "a")
    if fh.tell() == 0:
        fh.write("\t".join(cols) + "\n"); fh.flush()
    def write(vals):
        fh.write("\t".join(str(vals.get(c, "")) for c in cols) + "\n"); fh.flush()
    return old, write

def du_mb(p):
    out = subprocess.run(["du", "-sk", str(p)], capture_output=True, text=True).stdout.split()
    return f"{int(out[0]) / 1024:.0f}" if out else ""

def pick_site(rows, W, H):
    def ok(r, level):
        if r["biome"] not in BIOMES or int(r["evil"]) > 66 or r["lake"] != "0" or r["site"] != "0" or r["river"] != "0":
            return False
        if level == 1:
            return int(r["sav"]) < 33 and r["volcano"] == "0" and r["nbr_river"] == "0" and r["nbr_ocean"] == "0" and int(r["same8"]) >= 5
        return int(r["sav"]) < 50 and r["nbr_ocean"] == "0"
    cx, cy = (W - 1) / 2, (H - 1) / 2
    for level in (1, 2):
        q = [r for r in rows if ok(r, level)]
        if q:
            best = min(q, key=lambda r: ((int(r["x"]) - cx) ** 2 + (int(r["y"]) - cy) ** 2, int(r["y"]), int(r["x"])))
            return best, level, len(q)
    return None, 0, 0

def gen_world(w, write):
    key = w["world"]; save = f"FPS6{key}"
    vals: dict[str, Any] = dict(w, save=save, status="FAILED")
    try:
        if (SAVE_DIR / save).exists():
            sh("title", timeout=300); sh("save-delete", save)
        f5.restart()
        t0 = time.monotonic()
        out = sh("genworld", f"FPS6-{key}", w["seed"], SIZES[w["size_name"]][0], w["years"], timeout=7500,
                 env={"CX_GENWORLD_TIMEOUT": "7200"})
        vals["gen_wall_s"] = f"{time.monotonic() - t0:.0f}"
        m = re.search(r"params: slot 0 <- preset \d+ \(([^)]*)\), \d+ fields, (\d+)x(\d+), seed=(\d+), end_year=(\d+)", out)
        if not m or int(m.group(2)) != w["world_dim"] or int(m.group(5)) != w["years"]:
            raise RuntimeError(f"worldgen params not as designed (want {w['world_dim']}x{w['world_dim']}, {w['years']} y): "
                               f"{m.group(0) if m else out.strip()[-300:]}")
        rej = re.findall(r"worldgen rejection: ([A-Z ]+?) --", out)
        vals["rejection"] = rej[0] if rej else ""
        fm = re.search(r"-> folder (\S+) \(\d+s\)", out)
        if not fm:
            raise RuntimeError(f"genworld named no folder: {out.strip()[-300:]}")
        folder = fm.group(1)
        vals["folder"] = folder
        f5.log(f"    generated {folder} in {vals['gen_wall_s']} s ({m.group(1)} {m.group(2)}x{m.group(3)}, {w['years']} y"
               + (f", allowed {vals['rejection']}" if rej else "") + ")")
        sv = sh("survey", folder, "TEMPERATE", timeout=1500, env={"CX_RPC_TIMEOUT": "1200"})
        lines = [l for l in sv.splitlines() if re.match(r"^(x\t|\d+\t\d+\t)", l)]
        rows = list(csv.DictReader(lines, delimiter="\t"))
        tile, level, nq = pick_site(rows, w["world_dim"], w["world_dim"])
        vals.update(rule_level=level, qualifying=nq)
        if not tile:
            raise RuntimeError(f"no tile meets the site rule at either level ({len(rows)} TEMPERATE tiles surveyed)")
        vals.update(rx=tile["x"], ry=tile["y"], biome=tile["biome"], sav=tile["sav"], evil=tile["evil"], same8=tile["same8"])
        f5.log(f"    site {tile['x']},{tile['y']} {tile['biome']} sav {tile['sav']} evil {tile['evil']} same8 {tile['same8']} "
               f"(rule level {level}, {nq} qualifying of {len(rows)} TEMPERATE)")
        t0 = time.monotonic()
        sh("embark", folder, tile["x"], tile["y"], save, 6, 6, timeout=1200, env={"CX_EMBARK_SIZE": "3"})
        vals["embark_wall_s"] = f"{time.monotonic() - t0:.0f}"
        sh("title", timeout=300)
        stale = Path(cfg("CX_SNAPSHOT_DIR")) / "saves" / f"{save}.preverify"   # a retried world's old backup
        if stale.is_dir():
            subprocess.run(["rm", "-rf", str(stale)], check=True)
        sh("save-backup", save, "preverify")
        vals["save_mb"] = du_mb(SAVE_DIR / save)
        # the fort's save carries its own copy of the world; the pristine folder only lengthens DF's world list
        ARCHIVE.mkdir(parents=True, exist_ok=True)
        if (SAVE_DIR / folder).is_dir() and not (ARCHIVE / folder).exists():
            (SAVE_DIR / folder).rename(ARCHIVE / folder)
        vals["status"] = "ok"
        f5.log(f"    embarked 3x3 -> {save} ({vals['save_mb']} MB) in {vals['embark_wall_s']} s; world {folder} archived")
    except Exception as e:
        vals["note"] = repr(e)[:300]
        f5.log(f"  !! world {key} FAILED: {e!r}")
        try: f5.restart()
        except Exception as e2: f5.log(f"  !! restart failed too: {e2!r}")
    write(vals)
    return vals["status"] == "ok"

def play_session(w, session, play, every, write_load):
    save = f"FPS6{w['world']}"
    sess = f5.Session("fps6", session, 3)
    sess.extra = {k: w[k] for k in WORLD_COLS}
    sh("title", timeout=300); f5.prune_autosaves(save); sh("save-restore", f"{save}.preverify")
    f5.restart()
    t0 = time.monotonic(); sh("load", save, timeout=1200); load_wall = time.monotonic() - t0
    sh("fps", 1000, 60); sh("lua", f5.TOOL_ON)
    snap = procstat.snapshot().get("df") or {}
    m = re.search(r"world: (.*)", sh("cmd", "cx-load", "world"))
    probe = dict(zip(*[iter(m.group(1).split())] * 2)) if m else {}
    write_load(dict(sess.extra, session=session, load_wall_s=f"{load_wall:.1f}", save_mb=du_mb(SAVE_DIR / save),
                    df_footprint_mb=f"{snap.get('phys_footprint_mb', 0):.0f}", df_resident_mb=f"{snap.get('resident_mb', 0):.0f}", **probe))
    f5.log(f"    loaded in {load_wall:.0f} s; world {probe.get('dims')} year {probe.get('year')}: hf {probe.get('hf')} (alive {probe.get('hf_alive')}), "
           f"events {probe.get('events')}, sites {probe.get('sites')}, armies {probe.get('armies')}, near civ {probe.get('near_civ')} tiles")
    sh("cmd", "cx-load", "sustain")
    f5.measure(sess, "P0_fresh_original")
    while sess.played < play:
        sh("cmd", "cx-load", "sustain")
        s0 = procstat.snapshot(); t0 = time.monotonic()
        out = sh("step", every, max(300, every // 20 + 120), timeout=every // 5 + 900)
        wall = time.monotonic() - t0; s1 = procstat.snapshot()
        m = re.search(r"stepped (\d+) ticks", out)
        sess.played += int(m.group(1)) if m else every
        cpu = procstat.rates(s0.get("df"), s1.get("df")).get("cpu_cores", 0)
        rates, a, b = f5.stopwatch(3, 6.0)
        g = re.search(r"guests: merchants (\d+) visitors (\d+) invaders (\d+)", sh("cmd", "cx-load", "guests"))
        sess.extra.update(dict(zip(("merchants", "visitors", "invaders"), g.groups())) if g else {})
        v = sess.record("play", rates, a, b, f"{wall:.1f}", f"{cpu:.3f}")
        if v["citizens"] in ("", "0"):
            raise RuntimeError(f"the settlement is gone at {sess.played} ticks (citizens {v['citizens']!r}, dead {v['dead_citizens']})")
        f5.log(f"    play {sess.played:>6}: {v['tps']} t/s; cit {v['citizens']} wild {v['wild']} items {v['items']} guests "
               f"{v.get('merchants')}/{v.get('visitors')}/{v.get('invaders')}; cpu {v['df_cpu_cores']} footprint {v['df_footprint_mb']} MB load {v['load1']}")
    sh("title", timeout=300)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["gen", "play", "all"])
    ap.add_argument("--append", help="an existing FPS6 run directory (gen skips worlds already ok there)")
    ap.add_argument("--worlds", help="only these world keys, e.g. M500a,X5b")
    ap.add_argument("--sessions", type=int, default=2); ap.add_argument("--play", type=int, default=SEASON)
    ap.add_argument("--every", type=int, default=16800); ap.add_argument("--seed", type=int, default=6)
    a = ap.parse_args()
    out = Path(a.append) if a.append else ROOT / "data/experiments/FPS6" / f5.RUN
    f5.RUN = out.name; f5.OUT = out
    out.mkdir(parents=True, exist_ok=True)
    f5._log = open(out / "log.txt", "a"); f5.rows = open(out / "rows.tsv", "a")
    if f5.rows.tell() == 0:
        f5.rows.write("\t".join(f5.COLS) + "\n"); f5.rows.flush()
    (out / f"design-{a.mode}-{time.strftime('%H%M%S')}.json").write_text(json.dumps(vars(a), indent=1))
    want = set(a.worlds.split(",")) if a.worlds else None
    worlds = [w for w in design() if not want or w["world"] in want]
    f5.log(f"== FPS6 {a.mode} run {f5.RUN}: {len(worlds)} world(s)")
    done, write_world = table(out / "worlds.tsv", WORLDS_COLS)
    ok = {r["world"] for r in done if r["status"] == "ok"}
    if a.mode in ("gen", "all"):
        for i, w in enumerate(worlds):
            if w["world"] in ok:
                continue
            f5.log(f"  -- gen {w['world']}: {w['size_name']} {w['world_dim']}x{w['world_dim']}, {w['years']} years, seed {w['seed']}")
            if gen_world(w, write_world):
                ok.add(w["world"])
            elif i == 0 and w["world"] == "M500a":
                f5.log("== FPS6 stopped: the pilot world (MEDIUM, 500 years) failed; fix before generating the rest")
                return 2
        f5.log(f"== FPS6 gen done: {len(ok)} world(s) ok")
    if a.mode in ("play", "all"):
        _, write_load = table(out / "loads.tsv", LOADS_COLS)
        playable = [w for w in worlds if w["world"] in ok]
        rng = random.Random(a.seed)
        for s in range(1, a.sessions + 1):
            order = playable[:]; rng.shuffle(order)
            f5.log(f"== session pass {s}: {[w['world'] for w in order]}")
            for w in order:
                f5.log(f"  -- {w['world']} session {s}")
                try:
                    play_session(w, s, a.play, a.every, write_load)
                except Exception as e:
                    f5.log(f"  !! {w['world']} session {s} FAILED: {e!r}")
                    try: f5.restart()
                    except Exception as e2: f5.log(f"  !! restart failed too: {e2!r}")
        f5.log("== FPS6 done")
    return 0

if __name__ == "__main__":
    sys.exit(main())
