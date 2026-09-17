#!/usr/bin/env python
"""cx-mouse.py -- drive the REAL macOS pointer over the Dwarf Fortress window.

Why this exists (2026-09-16): DF v50 places the embark rectangle by a map
click, and it decides *which map tile* was clicked from the hover position it
computed during the previous rendered frame -- not from gps.mouse at the moment
of the click. Writing gps.mouse_x/y from a DFHack script and clicking in the
same call therefore lands wherever the physical pointer was, and DF overwrites
gps.mouse from SDL every frame anyway. Text buttons never showed this because
their hit-test reads gps.mouse at click time. So a map click has to be a real
pointer event: activate the window, move the pointer, let a frame render, click.

DF must be frontmost for SDL to see the motion; `activate` does that through
System Events. Coordinates are SCREEN PIXELS; the DF window sits at (0,0) on
this rig (System Events reports position {0,0} size {1920,1080}), and DF's
grid is 10x16 px per tile, so tile (tx,ty) is pixel (tx*10+5, ty*16+8).

    cx-mouse.py activate
    cx-mouse.py move  <px> <py>
    cx-mouse.py click <px> <py>          move, settle, left click
    cx-mouse.py rclick <px> <py>
    cx-mouse.py tile  <tx> <ty> [right]  click a DF tile coordinate
    cx-mouse.py key   <esc|return|space|w|a|s|d>   a real keypress
"""
import subprocess
import sys
import time

import Quartz

TILE_W, TILE_H = 10, 16
PROC = "Dwarf Fortress.exe"


def activate():
    subprocess.run(
        ["osascript", "-e",
         f'tell application "System Events" to set frontmost of process "{PROC}" to true'],
        check=False, capture_output=True)
    time.sleep(0.4)


def _post(kind, x, y, button=Quartz.kCGMouseButtonLeft):
    ev = Quartz.CGEventCreateMouseEvent(None, kind, (x, y), button)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)


def move(x, y):
    _post(Quartz.kCGEventMouseMoved, x, y)
    time.sleep(0.25)          # let DF render a frame with the pointer there
    _post(Quartz.kCGEventMouseMoved, x + 1, y)   # a second motion event; SDL
    time.sleep(0.25)          # sometimes drops the first after activation
    _post(Quartz.kCGEventMouseMoved, x, y)
    time.sleep(0.3)


def click(x, y, right=False):
    move(x, y)
    if right:
        down, up, btn = Quartz.kCGEventRightMouseDown, Quartz.kCGEventRightMouseUp, Quartz.kCGMouseButtonRight
    else:
        down, up, btn = Quartz.kCGEventLeftMouseDown, Quartz.kCGEventLeftMouseUp, Quartz.kCGMouseButtonLeft
    _post(down, x, y, btn)
    time.sleep(0.08)
    _post(up, x, y, btn)
    time.sleep(0.3)


KEYCODES = {"esc": 53, "return": 36, "enter": 36, "space": 49, "tab": 48,
            "w": 13, "a": 0, "s": 1, "d": 2}


def key(name):
    """Post a real keyboard press. Needed where DFHack's simulateInput is ignored:
    the embark site screen swallows LEAVESCREEN but answers a physical Escape
    with its 'Return to title' dialog (2026-09-16)."""
    code = KEYCODES.get(name.lower())
    if code is None:
        raise SystemExit(f"unknown key {name}; known: {' '.join(KEYCODES)}")
    down = Quartz.CGEventCreateKeyboardEvent(None, code, True)
    up = Quartz.CGEventCreateKeyboardEvent(None, code, False)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, down)
    time.sleep(0.06)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, up)
    time.sleep(0.3)


def main(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    cmd = argv[1]
    if cmd == "activate":
        activate(); return 0
    if cmd in ("move", "click", "rclick"):
        x, y = int(argv[2]), int(argv[3])
        activate()
        if cmd == "move": move(x, y)
        else: click(x, y, right=(cmd == "rclick"))
        print(f"{cmd} {x},{y}"); return 0
    if cmd == "key":
        activate(); key(argv[2]); print(f"key {argv[2]}"); return 0
    if cmd == "tile":
        tx, ty = int(argv[2]), int(argv[3])
        right = len(argv) > 4 and argv[4] == "right"
        x, y = tx * TILE_W + TILE_W // 2, ty * TILE_H + TILE_H // 2
        activate(); click(x, y, right=right)
        print(f"tile {tx},{ty} -> px {x},{y}"); return 0
    print(__doc__); return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
