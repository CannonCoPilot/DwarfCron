#!/usr/bin/env python3
"""steam-health.py -- is Steam in the CrossOver bottle about to stop launching? (26 Oct 2026; 27 Oct)

After days of uptime Steam in the Win10 bottle "won't launch" (26 Oct): the running steam.exe had lost its
steamwebhelper.exe (the CEF interface), and a new launch -- even `wine --bottle Win10 steam.exe` -- got no answer from it
(no ExecCommandLine in console_log for 4 days). A launch only hands its command line to a running steam.exe, so a
steam.exe that stops answering hand-offs is what "won't launch" is.

    .venv/bin/python scripts/steam-health.py                    one report (read-only)
    .venv/bin/python scripts/steam-health.py --json             the same as JSON
    .venv/bin/python scripts/steam-health.py --probe            also test that steam.exe answers a launch: a silent
                                                                hand-off (steam.exe -silent; nothing shows), answered
                                                                in about 1 s when healthy
    .venv/bin/python scripts/steam-health.py --recover          end Steam and start it again (see Recovery)
    .venv/bin/python scripts/steam-health.py --watchdog         the hourly launchd job (scripts/launchd/; user 27 Oct):
                                                                with DF not running, probe; a steam.exe that misses two
                                                                probes 30 s apart is ended (--recover --no-relaunch) and
                                                                a macOS notification says so. Steam is NOT reopened: a
                                                                foreground launch at a random hour would steal focus, and
                                                                with the wedged copy gone the user's next click works

Checks
  wedged     --probe: steam.exe did not answer a hand-off within 20 s            -> exit 1
  no UI      steam.exe running with no main steamwebhelper. The main helper is found by the process holding
             logs/webhelper.txt open: launched from CrossOver's Steam.app it runs INSIDE the app's "Menu Helper"
             process (the Dock icon; 27 Oct), whose command line never names steamwebhelper, so a command-line test
             read every healthy Steam.app session as wedged. Killing the Menu Helper (Force Quit) is not a wedge:
             steam.exe restarts the helper within 5 s and a new launch still hands off (27 Oct). -> exit 2
  stalled    the bootstrapper's update check (about every 6 h) last began more than 8 h ago, or began and never
             finished, while steam.exe has been up longer than that: the first sign on 23 Oct, 3 days before the wedge
  orphans    Wine processes older than the running wineserver (or any, with no wineserver): earlier sessions whose
             wineserver died without them (28 Sep, 3 Oct, 13 Oct sessions were still alive on 26 Oct)
  fds        the wineserver's open descriptors, shown for the record only: a fresh session read 1,976, the wedged
             4-day one 773, so the count is not a leak signal
Exit: 0 healthy, 1 wedged, 2 a warning (no UI, stalled, orphans), 3 Steam not running.
Recovery (--recover; refuses while Dwarf Fortress.exe runs unless --force; --no-relaunch leaves Steam off):
  1. a steam.exe that answers the probe is asked to quit (steam.exe -shutdown; 2 s on 27 Oct)
  2. one that did not answer, or is still up after 30 s: WINEPREFIX="$CX_BOTTLE_DIR" wineserver -k (ends every program
     in the bottle; CX_BOTTLE=Win10 alone does not find the bottle: rc 1)
  3. kill -TERM the orphans (-k cannot reach them)
  4. open Steam.app in the FOREGROUND and wait for the bootstrapper's Startup line: `open -g` (background) starts the
     Menu Helper but it never launches Steam (27 Oct), which looks exactly like the "won't launch" symptom
Not a cause (27 Oct): the steam.exe crash dumps of 29 Sep - 6 Oct are all one crash on exit, Wine's sechost.dll
I_ScUnregisterDeviceNotification (+0x6243, an access violation writing through ASCII text); none since 6 Oct.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BOTTLE = Path(os.environ.get("CX_BOTTLE_DIR") or Path.home() / "Library/Application Support/CrossOver/Bottles" / os.environ.get("CX_BOTTLE", "Win10"))
STEAM_LOGS = BOTTLE / "drive_c/Program Files (x86)/Steam/logs"
STALL_H = 8.0
WINE_BIN = Path(os.environ.get("CX_SUPPORT", "/Applications/CrossOver.app/Contents/SharedSupport/CrossOver")) / "bin"
STEAM_APP = Path(os.environ.get("STEAM_APP") or Path.home() / "Applications/CrossOver/Steam/Steam.app")
STEAM_EXE = "C:\\Program Files (x86)\\Steam\\steam.exe"


def etime_s(et: str) -> int:
    """ps etime [[dd-]hh:]mm:ss -> seconds"""
    days, _, rest = et.strip().rpartition("-")
    parts = [int(p) for p in rest.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, s = parts
    return (int(days) if days else 0) * 86400 + h * 3600 + m * 60 + s


def procs() -> list[dict]:
    out = subprocess.run(["ps", "-axo", "pid=,etime=,command="], capture_output=True, text=True, timeout=10).stdout
    rows = []
    for line in out.splitlines():
        m = re.match(r"\s*(\d+)\s+(\S+)\s+(.*)", line)
        if m:
            rows.append({"pid": int(m.group(1)), "age": etime_s(m.group(2)), "cmd": m.group(3)})
    return rows


def wine_procs(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["cmd"].startswith("C:\\") or "/CrossOver/lib/wine/" in r["cmd"]]


def fd_count(pid: int) -> int | None:
    try:
        out = subprocess.run(["lsof", "-nP", "-p", str(pid)], capture_output=True, text=True, timeout=15).stdout
        return max(0, len(out.splitlines()) - 1)
    except (subprocess.TimeoutExpired, OSError):
        return None


def log_holders(name: str) -> list[int]:
    """pids holding a Steam log open -- for webhelper.txt, the main helper (and the wineserver, which the caller drops)"""
    try:
        out = subprocess.run(["lsof", "-t", str(STEAM_LOGS / name)], capture_output=True, text=True, timeout=15).stdout
        return [int(x) for x in out.split()]
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return []


def count_lines(name: str, needle: str) -> int:
    try:
        with (STEAM_LOGS / name).open("rb") as fh:
            return fh.read().count(needle.encode())
    except OSError:
        return 0


def wine(*args: str) -> None:
    subprocess.Popen([str(WINE_BIN / "wine"), "--bottle", BOTTLE.name, "--no-wait", *args],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def probe(timeout: float = 20.0) -> float | None:
    """a silent hand-off to the running steam.exe: seconds until console_log records it, None if it never does"""
    n0, t0 = count_lines("console_log.txt", "ExecCommandLine"), time.time()
    wine(STEAM_EXE, "-silent")
    while time.time() - t0 < timeout:
        time.sleep(0.5)
        if count_lines("console_log.txt", "ExecCommandLine") > n0:
            return round(time.time() - t0, 1)
    return None


def updater_state(now: datetime) -> dict:
    """the bootstrapper's last update check: when it began and whether it finished"""
    f = STEAM_LOGS / "bootstrap_log.txt"
    if not f.exists():
        return {"known": False}
    try:
        with f.open("rb") as fh:
            fh.seek(0, 2)
            fh.seek(max(0, fh.tell() - 200_000))
            tail = fh.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return {"known": False}
    began, done, startup = None, False, None
    for line in tail:
        m = re.match(r"\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\] (.*)", line)
        if not m:
            continue
        t, msg = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"), m.group(2)
        if msg.startswith("Startup - Steam Client launched"):
            startup, began, done = t, None, False
        elif msg.startswith("Background update loop checking"):
            began, done = t, False
        elif began and (msg.startswith("Nothing to do") or "Manifest download: finished" in msg or msg.startswith("Download skipped")):
            done = True
    return {"known": True, "startup": startup and startup.isoformat(sep=" "), "began": began and began.isoformat(sep=" "),
            "finished": done, "hours_since": round((now - began).total_seconds() / 3600, 1) if began else None}


def state() -> dict:
    rows = procs()
    steam = [r for r in rows if r["cmd"].startswith(STEAM_EXE)]
    helpers = [r for r in rows if "steamwebhelper.exe" in r["cmd"]]
    servers = [r for r in rows if r["cmd"].endswith("/bin/wineserver") or r["cmd"].endswith("bin/wineserver ")]
    server = max(servers, key=lambda r: r["age"]) if servers else None
    by_pid = {r["pid"]: r for r in rows}
    holders = [by_pid[p] for p in log_holders("webhelper.txt") if p in by_pid and not (server and p == server["pid"])]
    main_helper = holders or [r for r in helpers if "--type=" not in r["cmd"]]
    return {"rows": rows, "steam": steam, "helpers": helpers, "main": main_helper, "server": server}


def orphans_of(rows: list[dict], server: dict | None) -> list[dict]:
    """Wine processes older than the running wineserver (or any, with none): sessions whose wineserver died without them"""
    return [r for r in wine_procs(rows) if r is not server and (server is None or r["age"] > server["age"] + 5)]


def df_running(rows: list[dict]) -> bool:
    return any("Dwarf Fortress.exe" in r["cmd"] for r in rows)


def recover(force: bool, relaunch: bool) -> int:
    st = state()
    if df_running(st["rows"]) and not force:
        print("recover: Dwarf Fortress is running in the bottle -- not touching Steam (--force to override)")
        return 4
    if st["steam"]:
        answered = probe()
        print(f"recover: steam.exe pid {st['steam'][0]['pid']} {'answered in %s s' % answered if answered is not None else 'did NOT answer a hand-off'}")
        if answered is not None:
            wine(STEAM_EXE, "-shutdown")
            t0 = time.time()
            while time.time() - t0 < 30 and state()["steam"]:
                time.sleep(1)
        if state()["steam"]:
            print("recover: steam.exe still up -- wineserver -k (ends every program in the bottle)")
            subprocess.run([str(WINE_BIN / "wineserver"), "-k"], env={**os.environ, "WINEPREFIX": str(BOTTLE)}, timeout=60)
            time.sleep(2)
        else:
            print(f"recover: steam.exe quit on request")
    st = state()
    left = orphans_of(st["rows"], st["server"])
    for r in left:
        try:
            os.kill(r["pid"], 15)
        except OSError:
            pass
    if left:
        print(f"recover: TERM to {len(left)} orphaned Wine process(es)")
    if not relaunch:
        print("recover: Steam left off (--no-relaunch)")
        return 0
    n0 = count_lines("bootstrap_log.txt", "Startup - Steam Client launched")
    subprocess.run(["open", str(STEAM_APP)], timeout=30)   # foreground: `open -g` starts the helper but not Steam
    t0 = time.time()
    while time.time() - t0 < 45:
        time.sleep(1)
        if count_lines("bootstrap_log.txt", "Startup - Steam Client launched") > n0 and state()["main"]:
            print(f"recover: Steam started in {time.time() - t0:.0f} s")
            return 0
    print("recover: Steam did not start within 45 s")
    return 1


def notify(msg: str) -> None:
    subprocess.run(["osascript", "-e", f'display notification "{msg}" with title "Steam watchdog"'],
                   capture_output=True, timeout=10)


def watchdog() -> int:
    """one launchd tick: one log line, and a recovery only for a steam.exe that misses two probes"""
    st = state()
    stamp = f"{datetime.now():%Y-%m-%d %H:%M:%S}"
    if not st["steam"]:
        print(f"{stamp} steam not running")
        return 0
    if df_running(st["rows"]):
        print(f"{stamp} skipped: Dwarf Fortress is running")
        return 0
    answered = probe()
    if answered is None:
        time.sleep(30)
        answered = probe()
    if answered is not None:
        print(f"{stamp} ok: steam.exe pid {st['steam'][0]['pid']} answered in {answered} s")
        return 0
    print(f"{stamp} WEDGED: steam.exe pid {st['steam'][0]['pid']} missed two hand-offs 30 s apart; recovering", flush=True)
    rc = recover(force=False, relaunch=False)
    notify("Steam had stopped answering and was shut down. Open Steam again to use it." if rc == 0
           else f"Steam had stopped answering; recovery returned {rc}. See DwarfCron data/logs/steam-watchdog.log")
    return rc


def main() -> int:
    if "--watchdog" in sys.argv:
        return watchdog()
    if "--recover" in sys.argv:
        return recover("--force" in sys.argv, "--no-relaunch" not in sys.argv)
    now = datetime.now()
    st = state()
    rows, steam, helpers, main_helper, server = st["rows"], st["steam"], st["helpers"], st["main"], st["server"]
    orphans = orphans_of(rows, server)
    up = steam[0]["age"] if steam else 0
    upd = updater_state(now)
    stalled = bool(steam and upd.get("known") and upd.get("began") and up > STALL_H * 3600
                   and (upd["hours_since"] > STALL_H or (not upd["finished"] and upd["hours_since"] > 0.5)))
    answered = probe() if steam and "--probe" in sys.argv else None
    rep = {
        "steam": {"running": bool(steam), "pid": steam[0]["pid"] if steam else None, "up_hours": round(up / 3600, 1),
                  "probe_s": answered, "probed": bool(steam and "--probe" in sys.argv)},
        "webhelper": {"processes": len(helpers), "main": len(main_helper),
                      "main_in": (main_helper[0]["cmd"] if main_helper else None) and
                      ("Steam.app's Menu Helper" if "Menu Helper" in main_helper[0]["cmd"] else "steamwebhelper.exe")},
        "wineserver": {"pid": server["pid"] if server else None, "up_hours": round(server["age"] / 3600, 1) if server else None,
                       "fds": fd_count(server["pid"]) if server else None},
        "updater": upd, "stalled": stalled,
        "orphans": [{"pid": r["pid"], "days": round(r["age"] / 86400, 1), "cmd": r["cmd"][:90]} for r in orphans],
    }
    if not steam:
        verdict, code = "NOT RUNNING", 3
    elif rep["steam"]["probed"] and answered is None:
        verdict, code = "WEDGED: steam.exe did not answer a launch hand-off in 20 s -- a new launch will show nothing (--recover)", 1
    elif not main_helper or stalled or orphans:
        verdict, code = "WARNING: " + "; ".join(x for x in [
            not main_helper and "steam.exe has no main steamwebhelper (no interface; --probe tests whether a launch still gets through)",
            stalled and f"the update check began {upd['hours_since']} h ago and {'never finished' if not upd['finished'] else 'has not run since'} (the first sign before a wedge)",
            orphans and f"{len(orphans)} orphaned Wine process(es) from earlier sessions"] if x), 2
    else:
        verdict, code = "HEALTHY", 0
    rep["verdict"], rep["exit"] = verdict, code
    if "--json" in sys.argv:
        print(json.dumps(rep, indent=2))
        return code
    s, w, ws = rep["steam"], rep["webhelper"], rep["wineserver"]
    print(f"steam-health  {now:%Y-%m-%d %H:%M}  bottle {BOTTLE.name}")
    print(f"  steam.exe    {'pid %d, up %.1f h' % (s['pid'], s['up_hours']) if s['running'] else 'not running'}"
          + (f", answered a launch in {s['probe_s']} s" if s["probe_s"] is not None else ", did NOT answer a launch" if s["probed"] else ""))
    print(f"  webhelper    {w['processes']} process(es), main {'yes (in %s)' % w['main_in'] if w['main'] else 'NO'}")
    print(f"  wineserver   {'pid %s, up %s h, %s fds' % (ws['pid'], ws['up_hours'], ws['fds']) if ws['pid'] else 'none'}")
    if upd.get("known") and upd.get("began"):
        print(f"  updater      last check began {upd['began']} ({upd['hours_since']} h ago), {'finished' if upd['finished'] else 'NOT finished'}")
    elif upd.get("known"):
        print("  updater      no check since the last launch")
    for o in rep["orphans"]:
        print(f"  orphan       pid {o['pid']}, {o['days']} d: {o['cmd']}")
    print(f"  => {verdict}")
    return code


if __name__ == "__main__":
    sys.exit(main())
