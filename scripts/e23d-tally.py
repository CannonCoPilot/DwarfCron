#!/usr/bin/env python3
"""E23d — a real cavern invasion? Per rep: max invaders at any sample, the cavern count at those samples, citizens, irritation."""
import re, sys, json
from pathlib import Path
run = Path(sys.argv[1]); log = (run / "log.txt").read_text(errors="replace")
reps = {}; cur = None
for line in log.splitlines():
    m = re.search(r"== E23d arm=(\w+) rep=(\d+)", line)
    if m: cur = (m.group(1), int(m.group(2))); reps[cur] = {"S": [], "done": None, "disc": None, "moved": None}; continue
    if cur is None: continue
    m = re.search(r"e23d: (\d+) cavern features marked Discovered; did_first_cavern_announcement set: (\w+) \(reads (\w+)\)", line)
    if m: reps[cur]["disc"] = (int(m.group(1)), m.group(3))
    m = re.search(r"(\d+) citizen\(s\) teleported", line)
    if m: reps[cur]["moved"] = int(m.group(1))
    m = re.search(r"invaders=(\d+)", line)
    if m:
        cav = re.search(r"cavern=(\d+)", line); cz = re.search(r"citizens=(\d+)", line); irr = re.search(r"irritation(?:_sum)?[= ]+(\d+)", line)
        reps[cur]["S"].append(dict(inv=int(m.group(1)), cav=int(cav.group(1)) if cav else -1, cz=int(cz.group(1)) if cz else -1, irr=int(irr.group(1)) if irr else -1))
    m = re.search(r"done: (\{.*\})", line)
    if m:
        try: reps[cur]["done"] = json.loads(m.group(1))
        except Exception: pass
print(f"run {run}")
print(f"{'arm':9}{'rep':>4}{'valid':>7}{'discovered':>12}{'moved':>7}{'samples':>9}{'inv max':>9}{'cav at inv max':>16}{'cav max':>9}{'citizens':>12}{'irr max':>9}")
for (arm, rep), r in sorted(reps.items()):
    S = r["S"]; valid = bool(r["done"] and r["done"].get("valid"))
    invmax = max((s["inv"] for s in S), default=0); at = next((s["cav"] for s in S if s["inv"] == invmax), -1) if invmax else -1
    cz = f"{S[0]['cz']}->{S[-1]['cz']}" if S else "-"
    print(f"{arm:9}{rep:>4}{str(valid):>7}{str(r['disc']):>12}{str(r['moved']):>7}{len(S):>9}{invmax:>9}{at:>16}{max((s['cav'] for s in S), default=0):>9}{cz:>12}{max((s['irr'] for s in S), default=-1):>9}")
print()
inv = [max((s["inv"] for s in r["S"]), default=0) for (a, _), r in reps.items() if a == "invaded" and r["done"] and r["done"].get("valid")]
print("invaded arm invaders max per rep:", inv, "->", "an invasion came: read the cavern count against the control's level" if inv and any(x > 0 for x in inv) else "no invader in two seasons: the trigger still needs something the flags do not give (E23d stays a fort-construction item)")
