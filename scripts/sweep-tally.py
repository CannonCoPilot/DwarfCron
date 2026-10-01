"""sweep-tally: the SWEEP design's busy-ness index B (experiments/SWEEP-design.md section 1) for SW1/SW2/SW3.

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

WINDOW_TICKS = {"SW1": 30000, "SW2": 30000, "SW3": 50400}
CONTROL_ARM = {"SW1": "ctl", "SW2": "ctl", "SW3": "auto"}


def kv(s):
    return dict(t.split("=", 1) for t in s.split() if "=" in t)


def load(path):
    """-> {(cell, rep): {"series": [(tag, total_groups)...], "attacks": n, "deaths": n, "failed": str|None}}"""
    cells = defaultdict(lambda: dict(series=[], attacks=0, deaths=0, failed=None))
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
        elif kind == "death":
            c["deaths"] += 1
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


def main():
    run = Path(sys.argv[1])
    blocks = sys.argv[2:] or [b for b in ("SW1", "SW2", "SW3") if (run / f"{b}.tsv").exists()]
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
            if arm != ctl_name and outside and all(outside) and len(outside) >= 2:
                tag = "  ** differs from control (2-of-2 outside control range) **"
            print(f"   {arm:14s} " + " | ".join(parts) + tag)


if __name__ == "__main__":
    main()
