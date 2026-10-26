#!/usr/bin/env python3
"""steam-health.py -- is Steam in the CrossOver bottle about to stop launching? (26 Oct 2026)

After days of uptime Steam in the Win10 bottle "won't launch": the running steam.exe has lost its steamwebhelper.exe
(the CEF interface) and never restarts it, and a new launch only hands its command line to that steam.exe and exits.
Read-only: this looks, it never kills or starts anything.

    .venv/bin/python scripts/steam-health.py           one report
    .venv/bin/python scripts/steam-health.py --json    the same as JSON

Checks
  wedged     steam.exe running with no steamwebhelper.exe main process          -> exit 1
  stalled    the bootstrapper's update check (about every 6 h) last began more than 8 h ago, or began and never
             finished, while steam.exe has been up longer than that: the first sign on 23 Oct, 3 days before the wedge
  orphans    Wine processes older than the running wineserver (or any, with no wineserver): earlier sessions whose
             wineserver died without them (28 Sep, 3 Oct, 13 Oct sessions were still alive on 26 Oct)
  fds        the wineserver's open descriptors, shown for the record only: a fresh session read 1,976, the wedged
             4-day one 773, so the count is not a leak signal
Exit: 0 healthy, 1 wedged, 2 a warning (stalled, orphans), 3 Steam not running.
Recovery (by hand, it ends every program in the bottle):
  WINEPREFIX="$CX_BOTTLE_DIR" "$WINESERVER" -k        (CX_BOTTLE=Win10 alone does not find the bottle: rc 1)
  kill -TERM <orphan pids>                            (-k cannot reach them)
  wine --bottle Win10 "C:\\Program Files (x86)\\Steam\\steam.exe"
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BOTTLE = Path(os.environ.get("CX_BOTTLE_DIR") or Path.home() / "Library/Application Support/CrossOver/Bottles" / os.environ.get("CX_BOTTLE", "Win10"))
STEAM_LOGS = BOTTLE / "drive_c/Program Files (x86)/Steam/logs"
STALL_H = 8.0


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


def main() -> int:
    now = datetime.now()
    rows = procs()
    steam = [r for r in rows if r["cmd"].startswith("C:\\Program Files (x86)\\Steam\\steam.exe")]
    helpers = [r for r in rows if "steamwebhelper.exe" in r["cmd"]]
    main_helper = [r for r in helpers if "--type=" not in r["cmd"]]
    servers = [r for r in rows if r["cmd"].endswith("/bin/wineserver") or r["cmd"].endswith("bin/wineserver ")]
    server = max(servers, key=lambda r: r["age"]) if servers else None
    wine = wine_procs(rows)
    orphans = [r for r in wine if r is not server and (server is None or r["age"] > server["age"] + 5)]
    up = steam[0]["age"] if steam else 0
    upd = updater_state(now)
    stalled = bool(steam and upd.get("known") and upd.get("began") and up > STALL_H * 3600
                   and (upd["hours_since"] > STALL_H or (not upd["finished"] and upd["hours_since"] > 0.5)))
    rep = {
        "steam": {"running": bool(steam), "pid": steam[0]["pid"] if steam else None, "up_hours": round(up / 3600, 1)},
        "webhelper": {"processes": len(helpers), "main": len(main_helper)},
        "wineserver": {"pid": server["pid"] if server else None, "up_hours": round(server["age"] / 3600, 1) if server else None,
                       "fds": fd_count(server["pid"]) if server else None},
        "updater": upd, "stalled": stalled,
        "orphans": [{"pid": r["pid"], "days": round(r["age"] / 86400, 1), "cmd": r["cmd"][:90]} for r in orphans],
    }
    if not steam:
        verdict, code = "NOT RUNNING", 3
    elif not main_helper:
        verdict, code = "WEDGED: steam.exe is up with no steamwebhelper -- a new launch will hand off to it and show nothing", 1
    elif stalled or orphans:
        verdict, code = "WARNING: " + "; ".join(x for x in [
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
    print(f"  steam.exe    {'pid %d, up %.1f h' % (s['pid'], s['up_hours']) if s['running'] else 'not running'}")
    print(f"  webhelper    {w['processes']} process(es), main {'yes' if w['main'] else 'NO'}")
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
