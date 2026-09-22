#!/usr/bin/env python3
"""T9b — real cavern pressure. ON PASS: p1 > 1.0 at some sample and >= 1 distinct 'armed' event per rep; control PASS: p1 == 0 throughout, no irruption line.
Also reports the cavern gate's 'next cavern wave may come in N days' values per arm (halved under pressure?).
Armed events are read from the sample trace (each transition into a new 'armed=<TOKEN> xN' is one event); the manifest's
ledger dump asked for kind 'wave' only, so irruption lines never reached the log — the ledger regex stays as a second source."""
import re, sys, json
from pathlib import Path
run = Path(sys.argv[1]); log = (run / "log.txt").read_text(errors="replace")
reps = {}; cur = None
for line in log.splitlines():
    m = re.search(r"== T9b arm=(\w+) rep=(\d+)", line)
    if m: cur = (m.group(1), int(m.group(2))); reps[cur] = {"S": [], "armed": set(), "gaps": [], "moved": None, "done": None}; continue
    if cur is None: continue
    m = re.search(r"(\d+) citizen\(s\) teleported", line)
    if m and reps[cur]["moved"] is None: reps[cur]["moved"] = int(m.group(1))
    m = re.search(r"t9b: cz_in_c1=(\d+) citizens=(\d+) p1=([\d.]+) p2=([\d.]+) p3=([\d.]+) armed=(\S+ ?x?\d*) cavern_units=(\d+) agitated=(\d+) next_cavern_gap_days=(\S+) day=(\d+)", line)
    if m: reps[cur]["S"].append(dict(inb=int(m.group(1)), cz=int(m.group(2)), p1=float(m.group(3)), armed=m.group(6), cav=int(m.group(7)), agit=int(m.group(8)), day=int(m.group(10)))); continue
    if "t9b ledger:" in line:
        reps[cur]["armed"].update(re.findall(r"y\d+ \w+ \d+\s+irruption\s+cavern\s+armed \S+ x\d+ from cavern \d", line))
        reps[cur]["gaps"] += [int(x) for x in re.findall(r"next cavern wave may come in (\d+) days", line)]
    m = re.search(r"done: (\{.*\})", line)
    if m:
        try: reps[cur]["done"] = json.loads(m.group(1))
        except Exception: pass
print(f"run {run}")
print(f"{'arm':12}{'rep':>4}{'valid':>7}{'moved':>7}{'in-band max':>13}{'p1 max':>8}{'first>1 day':>13}{'armed':>7}{'agit max':>10}{'citizens':>12}{'gap days (distinct)':>24}")
ok = {"pressure_on": [], "control": []}
for (arm, rep), r in sorted(reps.items()):
    S = r["S"]; valid = bool(r["done"] and r["done"].get("valid")) and (r["moved"] or 0) > 0
    prev = "none"
    for s in S:
        if s["armed"] != "none" and s["armed"] != prev: r["armed"].add(f"sample:{s['armed']}@day{s['day']}")
        prev = s["armed"]
    p1max = max((s["p1"] for s in S), default=0); first = next((s["day"] for s in S if s["p1"] > 1.0), None)
    cz = f"{S[0]['cz']}->{S[-1]['cz']}" if S else "-"
    gaps = sorted(set(r["gaps"]))
    print(f"{arm:12}{rep:>4}{str(valid):>7}{str(r['moved']):>7}{max((s['inb'] for s in S), default=0):>13}{p1max:>8.2f}{str(first):>13}{len(r['armed']):>7}{max((s['agit'] for s in S), default=0):>10}{cz:>12}{str(gaps)[:24]:>24}")
    if not valid: continue
    if arm == "pressure_on": ok[arm].append(p1max > 1.0 and len(r["armed"]) >= 1)
    else: ok[arm].append(p1max == 0 and len(r["armed"]) == 0)
print()
for arm, v in ok.items():
    print(f"{arm:12} {'PASS' if v and all(v) else ('NO VALID REPLICATE' if not v else 'FAIL')}  {v}")
