#!/usr/bin/env python3
"""T9 tally — v6.1 irruptions. Reads each replicate's log.txt: the 't9:' samples and the 't9 ledger:' lines.
PASS ON: >=1 'armed' ledger line and agitated>0 at some sample, each rep. PASS OFF: no irruption line, agitated==0 every sample."""
import re, sys, json
from pathlib import Path
run = Path(sys.argv[1]); log = (run / "log.txt").read_text(errors="replace")
reps = {}; cur = None
for line in log.splitlines():
    m = re.search(r"== T9 arm=(\w+) rep=(\d+)", line)
    if m: cur = (m.group(1), int(m.group(2))); reps[cur] = {"samples": [], "armed": 0, "stood": 0, "blocked": 0, "done": None}; continue
    if cur is None: continue
    m = re.search(r"t9: cavern_units=(\d+) agitated=(\d+) citizens=(\d+) armed=(\S+ ?x?\d*) p1=([\d.]+) p2=([\d.]+) p3=([\d.]+) day=(\d+)", line)
    if m: reps[cur]["samples"].append(dict(cav=int(m.group(1)), agit=int(m.group(2)), cz=int(m.group(3)), armed=m.group(4), p1=float(m.group(5)), day=int(m.group(8)))); continue
    if "t9 ledger:" in line:   # the query shows the last four lines; count DISTINCT dated events across every sample
        for kind, pat in (("armed", r"y\d+ \w+ \d+\s+irruption\s+cavern\s+armed \S+ x\d+ from cavern \d"), ("stood", r"y\d+ \w+ \d+\s+irruption\s+cavern\s+\S+ x\d+ stood down"), ("blocked", r"y\d+ \w+ \d+\s+irruption\s+cavern\s+\S+ x\d+ arrived at pressure [\d.]+ but the roster blocks it")):
            reps[cur].setdefault("_" + kind, set()).update(re.findall(pat, line))
            reps[cur][kind] = len(reps[cur]["_" + kind])
    m = re.search(r"done: (\{.*\})", line)
    if m:
        try: reps[cur]["done"] = json.loads(m.group(1))
        except Exception: pass
print(f"run {run}")
print(f"{'arm':10}{'rep':>4}{'valid':>7}{'samples':>9}{'cav max':>9}{'agit max':>9}{'agit>0 n':>10}{'citizens':>12}{'armed':>7}{'stood':>7}{'blocked':>9}{'p1 max':>8}")
ok = {"irruption": [], "control": []}
for (arm, rep), r in sorted(reps.items()):
    S = r["samples"]; valid = bool(r["done"] and r["done"].get("valid"))
    agmax = max((s["agit"] for s in S), default=0); npos = sum(1 for s in S if s["agit"] > 0)
    cz = f"{S[0]['cz']}->{S[-1]['cz']}" if S else "-"
    print(f"{arm:10}{rep:>4}{str(valid):>7}{len(S):>9}{max((s['cav'] for s in S), default=0):>9}{agmax:>9}{npos:>10}{cz:>12}{r['armed']:>7}{r['stood']:>7}{r['blocked']:>9}{max((s['p1'] for s in S), default=0):>8.2f}")
    if not valid: continue
    if arm == "irruption": ok[arm].append(r["armed"] >= 1 and agmax > 0)
    else: ok[arm].append(r["armed"] == 0 and agmax == 0)
print()
for arm, v in ok.items():
    if not v: print(f"{arm:10} NO VALID REPLICATE"); continue
    print(f"{arm:10} {'PASS' if all(v) else 'FAIL'}  {v}  " + ("armed >= 1 and agitated > 0 in each replicate" if arm == "irruption" else "no armed line and agitated == 0 at every sample"))
