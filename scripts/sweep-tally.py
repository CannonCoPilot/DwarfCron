"""sweep-tally: the SWEEP design's busy-ness index B (experiments/SWEEP-design.md section 1) for
SW1/SW2/SW3/SW5/SW6/SW7.

SW5 (cavern) and SW6 (water) are natural-arrival blocks shaped exactly like SW3 (same eco-run.py cell pattern,
`nowatch=True` + a terminal `read`), so they land in the same <BLOCK>.tsv shape. Their per-sample status lines
(_SW_CAVERN_STATUS / _SW_WATER_STATUS in eco-run.py) carry a `total_groups` key alongside their own per-depth /
per-body breakdown, so the `swstatus` loader below needs no change for G; only WINDOW_TICKS/CONTROL_ARM below are
extended. SW7 (the roster-builder push, D1-triggered) reuses SW3's own `_SW_STATUS` reader unchanged (arms p1/p3/p5,
control p3 -- the current pack-bonus level), so it needs the same no-op treatment: just an entry in WINDOW_TICKS/
CONTROL_ARM. SW4 (the ladder) is not covered here: it runs disarmed (no `swstatus`/groups engine at all) and reads a
guild census instead (`swladder` lines) -- a different metric (predator share of guild counts, not busy-ness B) and,
per the task, left as a documented follow-up rather than bent into this script's B.

B = (G/G0 . (W+1/2)/(W0+1/2) . (A+2)/(A0+2) . (K+1/2)/(K0+1/2)) ^ (1/4), a geometric mean of each arm's ratio to its
run's own control arm (SW1/SW2: "ctl"; SW3: "auto", the current default). Decision rule: an arm differs from control
only if BOTH its replicates land outside the control's own 2-replicate range on B (the 2-of-2 rule, T8/DOM2).

Components, as read from eco-run.py's <BLOCK>.tsv (block, cell, rep, kind, k=v...):
  G (groups present)  = mean of swstatus's total_groups over that replicate's samples (first sample dropped, T8g)
  W (arrival waves)   = count of upward steps in total_groups between consecutive samples (a new group first listed)
                        -- 0 by design in SW1/SW2's arena (the subjects are placed, not arrived); real only in SW3
  A (fights)          = total `attacks` n, summed over the single terminal `read` eco-run.py always appends to a cell
  K (kills)           = count of `death` rows from that same terminal read
  all scaled to a rate per 10,000 ticks using the block's own window length (SW1/SW2: 30,000 t; SW3: 50,400 t)

Deviation from the design doc, noted for the report: the doc's A is "attack-intervals" (distinct attacker>defender,
sample-interval cells with >=1 attack), which needs a periodic counter *reset* that cx-eco's `read` verb does not do
(S.attacks is cumulative from `watch` and is never cleared by `read` -- confirmed by reading cx-eco.lua). Every other
block in this harness also reads only once per cell for this reason. A here is therefore total attacks over the whole
window, not interval count; likewise K counts all death rows (the arena holds only placed wild actors, so the design's
"killer is wild" filter is unconditionally true here -- there are no citizens or tame units in these cells).

Usage: sweep-tally.py <run> [SW1 SW2 SW3 ...]
"""
import re
import sys
import statistics
from collections import defaultdict
from pathlib import Path

WINDOW_TICKS = {"SW1": 30000, "SW2": 30000, "SW1R": 30000, "SW2R": 30000, "SW3": 50400, "SW5": 50400, "SW6": 50400, "SW7": 50400}
CONTROL_ARM = {"SW1": "ctl", "SW2": "ctl", "SW1R": "ctl", "SW2R": "ctl", "SW3": "auto", "SW5": "auto", "SW6": "auto", "SW7": "p3"}


def kv(s):
    return dict(t.split("=", 1) for t in s.split() if "=" in t)


def load(path):
    """-> {(cell, rep): {"series": [(tag, total_groups)...], "attacks": n, "deaths": n, "failed": str|None}}"""
    cells = defaultdict(lambda: dict(series=[], attacks=0, deaths=0, failed=None, pairs=[], dead=[]))
    for line in open(path):
        p = line.rstrip("\n").split("\t")
        if len(p) < 5:
            continue
        _, cell, rep, kind, rest = p[:5]
        c = cells[(cell, rep)]
        if kind == "FAILED":
            c["failed"] = rest
            continue
        d = kv(rest)
        if kind == "swstatus":
            c["series"].append((d.get("tag", "?"), int(d.get("total_groups", 0))))
        elif kind == "attacks":
            m = re.search(r"n=(\d+)", rest)
            if m:
                c["attacks"] += int(m.group(1))
                c["pairs"].append((d.get("pair", "?"), int(m.group(1))))
        elif kind == "death":
            c["deaths"] += 1
            c["dead"].append((d.get("victim", "?"), d.get("victim_spawned") == "1"))
    return cells


def components(c, ticks):
    """G, W, A, K for one (cell, rep), first sample dropped."""
    series = c["series"][1:] if len(c["series"]) > 1 else c["series"]
    g = statistics.mean(n for _, n in series) if series else 0.0
    w = sum(1 for (_, a), (_, b) in zip(series, series[1:]) if b > a)
    scale = 10000 / ticks
    return g, w * scale, c["attacks"] * scale, c["deaths"] * scale


def busyness(g, w, a, k, g0, w0, a0, k0):
    terms = [
        (g / g0) if g0 else 1.0,
        (w + 0.5) / (w0 + 0.5),
        (a + 2) / (a0 + 2),
        (k + 0.5) / (k0 + 0.5),
    ]
    p = 1.0
    for t in terms:
        p *= t
    return p ** 0.25


ARENA_HUNTER = "WOLF"
ARENA_PREY = {"DEER", "WATER_BUFFALO", "ELEPHANT"}


def arena_panel(by_arm, order):
    """SW1/SW2 placed-only readout (1 Oct): A and K above count every attack and death the watch saw, and natives
    that arrive during a rep (badgers, kangaroos, cavern troglodytes) dominate the later cells of the fixed cell
    order. Here: the placed wolves' attacks on the placed herds, placed prey killed, placed wolves lost."""
    print("   placed-only (wolf attacks on placed herds | placed prey killed | wolves lost | share of all attacks):")
    for arm in order:
        if arm not in by_arm:
            continue
        parts = []
        for rep, c in sorted(by_arm[arm], key=lambda x: x[0]):
            ap = sum(n for pr, n in c["pairs"] if pr.split(">")[0] == ARENA_HUNTER and pr.split(">")[-1] in ARENA_PREY)
            kp = sum(1 for v, sp in c["dead"] if sp and v in ARENA_PREY)
            wl = sum(1 for v, sp in c["dead"] if sp and v == ARENA_HUNTER)
            share = ap / c["attacks"] if c["attacks"] else 0.0
            parts.append(f"r{rep} {ap:4d} | {kp} | {wl} | {share:.0%}")
        print(f"     {arm:<13} " + "   ".join(parts))


def main():
    run = Path(sys.argv[1])
    blocks = sys.argv[2:] or [b for b in ("SW1", "SW2", "SW3", "SW5", "SW6", "SW7") if (run / f"{b}.tsv").exists()]
    for b in blocks:
        f = run / f"{b}.tsv"
        if not f.exists():
            print(f"-- {b}: no {f.name} in {run}")
            continue
        ticks = WINDOW_TICKS.get(b, 30000)
        ctl_name = CONTROL_ARM.get(b, "ctl")
        cells = load(f)
        by_arm = defaultdict(list)
        for (cell, rep), c in cells.items():
            by_arm[cell].append((rep, c))
        if ctl_name not in by_arm:
            print(f"-- {b}: control arm '{ctl_name}' missing, cannot compute B")
            continue
        ctl_comp = [components(c, ticks) for rep, c in by_arm[ctl_name] if not c["failed"]]
        if not ctl_comp:
            print(f"-- {b}: control arm '{ctl_name}' has no completed reps")
            continue
        g0, w0, a0, k0 = (statistics.mean(x) for x in zip(*ctl_comp))
        ctl_b = [busyness(g, w, a, k, g0, w0, a0, k0) for g, w, a, k in ctl_comp]
        ctl_lo, ctl_hi = (min(ctl_b), max(ctl_b)) if ctl_b else (1.0, 1.0)
        print(f"\n== {b}  (window {ticks} t, control={ctl_name}, G0={g0:.2f} W0={w0:.2f} A0={a0:.2f} K0={k0:.2f})")
        print(f"   control B per rep: {[f'{x:.2f}' for x in ctl_b]}  range [{ctl_lo:.2f}, {ctl_hi:.2f}]")
        order = list(dict.fromkeys(cell for (cell, _rep) in cells))   # first-seen = the block's cell order
        for arm in sorted(by_arm):
            rows = []
            for rep, c in sorted(by_arm[arm], key=lambda x: x[0]):
                if c["failed"]:
                    rows.append((rep, None, c["failed"]))
                    continue
                g, w, a, k = components(c, ticks)
                b_i = busyness(g, w, a, k, g0, w0, a0, k0)
                rows.append((rep, (g, w, a, k, b_i), None))
            parts = []
            outside = []
            for rep, comp, err in rows:
                if err:
                    parts.append(f"r{rep} FAILED {err[:80]}")
                    continue
                g, w, a, k, b_i = comp
                parts.append(f"r{rep} G={g:.2f} W={w:.2f} A={a:.2f} K={k:.2f} B={b_i:.2f}")
                outside.append(b_i < ctl_lo or b_i > ctl_hi)
            tag = ""
            # 2-of-2 AND the same side of the control range (SW1, 1 Oct: an arm with one rep above and one below
            # the range was flagged as "differs", which is noise, not an effect)
            sides = [comp[4] > ctl_hi for _, comp, err in rows if not err]
            if arm != ctl_name and outside and all(outside) and len(outside) >= 2 and len(set(sides)) == 1:
                tag = "  ** differs from control (2-of-2 outside control range) **"
            print(f"   {arm:14s} " + " | ".join(parts) + tag)
        if b.rstrip("R") in ("SW1", "SW2"):
            arena_panel(by_arm, order)


if __name__ == "__main__":
    main()
