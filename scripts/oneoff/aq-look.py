#!/usr/bin/env python3
"""Aquarium look check (2 Oct late): for each preset, load the fort, install the preset, reload, run ~2,000 ticks so DF
has waves, then for each view: status + probe, captures with waves off / on, bed off / on, absorb 0.5, and an unpaused
6-frame burst (motion). Reuses aquarium-run.py's rig helpers; shots in data/aquarium-run/<run>-look/shots/.
Usage: python3 scripts/oneoff/aq-look.py FORT PRESETS X,Y,Z [X,Y,Z ...]   e.g. AQUA_SHORE16 clear,aquarium 433,606,112
"""
import importlib.util, os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("aqr", ROOT / "scripts/aquarium-run.py")
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)

class Args: tool_src = str(Path.home() / "Claude/Projects/sw-wt/rc"); view = None; dry_run = False
A.ARGS = Args(); A.MODE = "live"; A.STAGE = "look"
A.OUT = A.OUT.with_name(A.RUN + "-look"); A.SHOTS = A.OUT / "shots"; A.SHOTS.mkdir(parents=True, exist_ok=True)
A.LOG = open(A.OUT / "log.txt", "w")


def say(tag, *words):
    out = A.aq(*words)
    A.log(f"  [{tag}] aquarium {' '.join(words)} -> " + out.strip().replace("\n", "\n      "))
    return out


def main():
    fort, presets, views = sys.argv[1], sys.argv[2].split(","), [tuple(int(v) for v in s.split(",")) for s in sys.argv[3:]]
    for p in presets:
        if not A.load_fort(fort, f"(preset {p})"): return 1
        ok, out = A.set_preset(p)
        A.log(f"preset {p} installed ok={ok}")
        if not A.load_fort(fort, f"(reload so DF reads the {p} pages)"): return 1
        A.cx("step", "2000", "300"); A.cx("pause")
        if os.environ.get("AQ_BUDGET"):   # look test only: let the bed run past its 2 ms fuse so the look can be judged
            say("budget", "budget", os.environ["AQ_BUDGET"]); say("rearm", "rearm")
        say("status", "status")
        for (x, y, z) in views:
            tag = f"{p}-{x}-{y}-z{z}"
            G = A.centre(x, y, z)
            say(tag, "waves", "auto"); say(tag, "bed", "on"); A.nap(4)
            A.shot(f"{tag}-on", G)
            say(tag, "probe")
            say(tag, "waves", "off"); A.nap(1); A.shot(f"{tag}-waves-off", G); say(tag, "waves", "auto")
            say(tag, "bed", "off"); A.nap(1); A.shot(f"{tag}-bed-off", G); say(tag, "bed", "on")
            say(tag, "bed", "absorb", "0.5"); A.nap(3); A.shot(f"{tag}-absorb05", G); say(tag, "bed", "absorb", "1")
            A.nap(2)
            A.cx("unpause"); A.burst(f"{tag}-run", 6, 0.25, G); A.cx("pause")
            say(tag, "status")
            if os.environ.get("AQ_BUDGET"): say(tag, "rearm")
    A.log(f"DONE -> {A.OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
