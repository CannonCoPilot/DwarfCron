#!/usr/bin/env python3
"""E40 tally: arrivals per depth per arm. The gated subject sits at one depth (CTRL: elk birds, depth 2);
the gate question is answered by THAT depth's arrivals in hold vs detach. Other depths are DF's other
sources and are printed as context. Usage: e40-tally.py [run dir]"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
run = Path(sys.argv[1]) if len(sys.argv) > 1 else sorted((ROOT / "data/experiments/E40").glob("2*"))[-1]
rows = json.loads((run / "rows.json").read_text())
print(f"run {run.name}")
for r in rows:
    if r.get("vacuous"): print(f"rep {r['rep']} {r['arm']:6s} VACUOUS"); continue
    by = {}
    for u in r["arrivals"]: by.setdefault(u["depth"], []).append((u["token"], u["at"]))
    d2 = by.get(2, [])
    print(f"rep {r['rep']} {r['arm']:6s} gated at t0={r['gated_at_t0']}  ticks={r['ticks']}  depth-2 arrivals={len(d2)} {sorted(set(t for t,_ in d2))} first={min([a for _,a in d2], default='-')}  | other depths: " +
          ", ".join(f"d{d}:{len(v)}" for d, v in sorted(by.items()) if d != 2))
