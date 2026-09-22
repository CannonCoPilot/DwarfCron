#!/usr/bin/env python3
"""E42b — wave sizes under a standing {2,1} write: ravens (flier) vs emu (flightless). Waves = surface arrivals within 500 ticks.
Only waves after the write stood are sized: the setup receipt read 'standing on 0' because the pre called trickleApply with its own
stale cfg (enabled unset) and the tool restored instead; the tool then wrote the range itself at the first release (ledger 'trickle:
draws sized 1-2 standing on N species'). The first sample tick at which the ledger dump shows that line is the cut; arrivals before it are listed but not scored."""
import re, sys, json
from pathlib import Path
run = Path(sys.argv[1]); log = (run / "log.txt").read_text(errors="replace")
ev = (run / "events.tsv").read_text(errors="replace").splitlines()[1:]
valid = {}; stood = {}; tick = 0
cur = None
for line in log.splitlines():
    m = re.search(r"== E42b arm=(\w+) rep=(\d+)", line)
    if m: cur = (m.group(1), int(m.group(2))); tick = 0; continue
    m = re.search(r"\+\s*(\d+) ticks \|", line)
    if m: tick = int(m.group(1))
    if cur and cur not in stood and "standing on" in line and "e42b ledger" in line: stood[cur] = tick
    m = re.search(r"done: (\{.*\})", line)
    if m and cur:
        try: valid[cur] = json.loads(m.group(1)).get("valid", False)
        except Exception: pass
arr = {}; allarr = {}   # allarr: every arrival's id -> token, any layer, per rep (to let a wave's id run skip another layer's draw)
for l in ev:
    f = l.split("\t")
    if len(f) < 8 or f[5] != "arrival": continue
    k = (f[1], int(f[2])); tok = f[7].split(" ")[0]; m = re.search(r"ref6=(\S+)", f[7]); ref6 = m.group(1) if m else "?"
    allarr.setdefault(k, {})[int(f[6])] = tok
    if "layer=surface" in f[7]: arr.setdefault(k, []).append((int(f[3]), tok, int(f[6]), ref6))   # (listed tick, token, unit id, population)
print(f"run {run}")
print(f"{'arm':7}{'rep':>4}{'valid':>7}{'write by':>9}{'waves':>7}{'sizes (after the write stood)':>40}{'>2':>5}{'first sample (unscored)':>24}")
over = {}
for k in sorted(arr):
    cut = stood.get(k); ts = sorted(arr[k]); before = sum(1 for t, _, _, _ in ts if cut is None or t < cut)
    # the first sample's arrivals (ids from 139 in every replicate) land inside the load-to-first-sample race with the write and cannot be placed
    # against it (emu rep 1: nine emus at +1118 t with the raw read {10,2} at the end of the pre and the ledger showing the write by +14 t) -> listed, not scored
    firstt = ts[0][0] if ts else None
    first_sizes = []
    if cut is None: ts = []
    else:
        head = [x for x in ts if x[0] == firstt]; ts = [x for x in ts if x[0] > firstt and x[0] >= cut]
        w = []
        for t, tok, uid, ref6 in head:
            if w and uid == w[-1][1] + 1 and ref6 == w[-1][2]: w[-1][0] += 1; w[-1][1] = uid
            else: w.append([1, uid, ref6])
        first_sizes = [x[0] for x in w]
    ids = allarr.get(k, {})
    def joins(w, t, tok, uid, ref6):   # same species and population entry, within 500 listed ticks, CONSECUTIVE unit ids (DF creates a draw's cluster in one go;
        return t - w[0] <= 500 and tok == w[2] and ref6 == w[4] and uid == w[3] + 1   # ids 139-140 then 141-154 of other layers then 155-157 are two draws, not one of five)
    waves = []   # arrivals are LISTED at the sample tick, so one sample can hold two draws (E42b raven rep 1: ids 139-140 and 155-157 in one sample; 195 and 204-205 from two population entries with troglodytes 196-200 between)
    for t, tok, uid, ref6 in ts:
        if waves and joins(waves[-1], t, tok, uid, ref6): waves[-1][1] += 1; waves[-1][3] = uid
        else: waves.append([t, 1, tok, uid, ref6])
    sizes = [w[1] for w in waves]; n_over = sum(1 for s in sizes if s > 2); n_over2 = sum(1 for s in sizes if s > 3)
    over.setdefault(k[0], []).append(n_over); over.setdefault(k[0] + "+2", []).append(n_over2)
    print(f"{k[0]:7}{k[1]:>4}{str(valid.get(k)):>7}{str(cut):>9}{len(waves):>7}{str(sizes)[:40]:>40}{n_over:>5}{str(first_sizes):>24}")
print()
r, e = over.get("raven", []), over.get("emu", []); r2, e2 = over.get("raven+2", []), over.get("emu+2", [])
print(f"raven waves over 2 per rep: {r} (over 3: {r2}); emu: {e} (over 3: {e2}) ->", end=" ")
if r and e and all(x > 0 for x in r) and all(x == 0 for x in e): print("fliers run over, emu holds: the raw is a SOFT ceiling for fliers")
elif r and e and all(x == 0 for x in r + e): print("neither runs over: E42 stands as a single anomaly")
elif r and e and any(x > 0 for x in e) and all(x == 0 for x in r2 + e2): print("BOTH species run over by exactly one and never by two: the extra is not flight; a fixed +1 to the written range (a juvenile in the draw?) is the candidate")
else: print("mixed: read the sizes")
