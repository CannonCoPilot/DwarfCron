#!/usr/bin/env python3
"""T8f — does a standing gated group delay DF's wave after a first-light release? Per rep: the tick of summer day 1's release
('the gate opens' + 'detached' in the ledger, year tick 100800), the first SURFACE arrival after it (events.tsv), the gap in ticks/days."""
import re, sys, json
from pathlib import Path
run = Path(sys.argv[1]); log = (run / "log.txt").read_text(errors="replace")
ev = (run / "events.tsv").read_text(errors="replace").splitlines()[1:]
SUMMER = 100800
reps = {}; cur = None
for line in log.splitlines():
    m = re.search(r"== T8f arm=(\w+) rep=(\d+)", line)
    if m: cur = (m.group(1), int(m.group(2))); reps[cur] = {"acted": None, "done": None}; continue
    if cur is None: continue
    m = re.search(r"t8f (HELD|CLEAR) at day (\d+): (\d+) group\(s\): (.*)", line)
    if m: reps[cur]["acted"] = (int(m.group(2)), int(m.group(3)), m.group(4)[:60])
    m = re.search(r"done: (\{.*\})", line)
    if m:
        try: reps[cur]["done"] = json.loads(m.group(1))
        except Exception: pass
first = {}; last = {}
for l in ev:
    f = l.split("\t")
    if len(f) < 8: continue
    arm, rep, tick, kind, detail = f[1], int(f[2]), int(f[3]), f[5], f[7]
    last[(arm, rep)] = max(last.get((arm, rep), 0), tick)
    if kind == "arrival" and "layer=surface" in detail and tick >= SUMMER:
        k = (arm, rep)
        if k not in first or tick < first[k][0]: first[k] = (tick, detail.split(" ")[0])
print(f"run {run}")
print(f"{'arm':8}{'rep':>4}{'valid':>7}{'acted (day, n, what)':>44}{'first summer surface arrival':>32}{'gap ticks':>11}{'gap days':>10}")
gaps = {"held": [], "clear": []}
for (arm, rep), r in sorted(reps.items()):
    valid = bool(r["done"] and r["done"].get("valid")) and r["acted"] is not None and r["acted"][1] > 0
    fa = first.get((arm, rep)); censored = fa is None and last.get((arm, rep), 0) > SUMMER
    gap = (fa[0] - SUMMER) if fa else ((last[(arm, rep)] - SUMMER) if censored else None)   # censored: no arrival in the window seen -> lower bound
    print(f"{arm:8}{rep:>4}{str(valid):>7}{str(r['acted'])[:44]:>44}{(f'{fa[1]} @ {fa[0]}' if fa else ('none in window' if censored else 'none')):>32}{(('>' if censored else '') + str(gap)):>11}{(('>' if censored else '') + f'{gap/1200:.1f}' if gap is not None else '-'):>10}")
    if valid and gap is not None: gaps[arm].append(gap / 1200)
print()
if gaps["held"] and gaps["clear"]:
    print(f"held {gaps['held']}  clear {gaps['clear']}  ->", "HELD later by more than a day in every pairing: PASS (a standing group delays the draw)" if min(gaps["held"]) - max(gaps["clear"]) > 1 else ("REVERSED: CLEAR waited longer than HELD in every pairing — a standing group does not delay the draw; the wait sits elsewhere" if min(gaps["clear"]) - max(gaps["held"]) > 1 else "no separation: T8d's ten days is not explained by a standing group"))
    print("(a '>' gap is censored: no surface arrival before the replicate ended)")
else: print("one arm has no valid replicate")
