#!/usr/bin/env python3
"""E27 tally: does zeroing a vermin population ENTRY stop that vermin appearing?
The v5.9 Vermin panel's whole premise, and the only vermin lever that is safe — addendum 54
established that zeroing a vermin's FREQUENCY is what freezes DF (CREEPY_CRAWLER is the last
underground rotter), so this arm touches entries only. Counts live vermin objects
(world.event.vermin) by race against an untouched control.
Usage: e27-tally.py [run_dir]"""
import os
import csv, glob, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tallylib import drop_incomplete
from collections import defaultdict
run_dir = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob("data/experiments/E27/*"))[-1]
SAMPLE = re.compile(r"e27: vermin_objects=(\d+) citizens=(\d+) countable_vermin_pool=(\d+) day=(\d+) \| (.*)$")
ZEROED = re.compile(r"e27: (\d+) vermin entries zeroed")
obj = defaultdict(list); pool = defaultdict(list); mix = {}; zeroed = {}
race = defaultdict(lambda: defaultdict(list))   # key -> race -> [count per sample]
cover = defaultdict(list)                      # key -> per-sample alphabetical coverage boundary
samples = defaultdict(list)                    # key -> per-sample {race: count}
for r in csv.DictReader(open(f"{run_dir}/events.tsv"), delimiter="\t"):
    if r["event"] != "manipulation": continue
    k = (r["arm"], int(r["rep"]))
    m = SAMPLE.search(r["detail"])
    if m:
        obj[k].append(int(m.group(1))); pool[k].append(int(m.group(3))); mix[k] = m.group(5).strip()
        # ⚠️ the manifest prints the mix as table.concat(parts, ', '):sub(1,200) — ALPHABETICALLY
        # SORTED AND TRUNCATED AT 200 CHARS. A race missing from the string may be absent OR may
        # simply sort past the cutoff, and the cutoff moves between arms (the control carries
        # extra surface birds early in the alphabet, which pushes its boundary back to the B's
        # while the zeroed arm reaches the S's). Comparing raw means across that is meaningless.
        # So every sample records how far its coverage actually extended, and a race is only
        # compared where BOTH arms could have shown it.
        raw = m.group(5)
        parts = raw.split(",")
        truncated = len(raw.strip()) >= 200
        if truncated and parts:
            parts = parts[:-1]           # the last entry may be cut mid-token
        seen = {}
        for part in parts:
            bits = part.strip().rsplit(" x", 1)
            if len(bits) == 2 and bits[1].isdigit():
                seen[bits[0].strip()] = int(bits[1])
        boundary = max(seen) if seen else ""
        if not truncated:
            boundary = "\uffff"          # nothing was cut: coverage is complete
        cover[k].append(boundary)
        for t, n in seen.items():
            race[k][t].append(n)
        for t in seen:
            pass
        samples[k].append(seen)
    m = ZEROED.search(r["detail"])
    if m: zeroed[k] = int(m.group(1))
drop_incomplete(run_dir, obj, pool, mix, zeroed)
print(f"run {run_dir}")
print("arm\trep\tentries zeroed\tvermin objects first/min/mean/last\tpool first->last\tfinal mix")
for k in sorted(obj):
    o = obj[k]; p = pool[k] or [0]
    print(f"{k[0]}\t{k[1]}\t{zeroed.get(k,'-')}\t{o[0]}/{min(o)}/{sum(o)/len(o):.1f}/{o[-1]}"
          f"\t{p[0]}->{p[-1]}\t{mix.get(k,'')[:70]}")
arm = defaultdict(list)
for k, o in obj.items(): arm[k[0]].extend(o)
print("\narm\tsamples\tvermin objects (mean)")
for a, o in sorted(arm.items()): print(f"{a}\t{len(o)}\t{sum(o)/len(o):.1f}")
if len(arm) == 2:
    (a1, v1), (a2, v2) = sorted(arm.items())
    m1, m2 = sum(v1)/len(v1), sum(v2)/len(v2)
    print(f"\n{a1} vs {a2}: {m1:.1f} vs {m2:.1f} live vermin objects IN TOTAL"
          f" — diluted by untouched cave species, see the per-race table")

    # per race, arm against arm, COVERAGE-AWARE: a sample counts for race t only if that
    # sample's alphabetical coverage reached t, i.e. t would have been printed had it been there.
    allraces = set()
    for k, d in race.items():
        allraces |= set(d)
    def arm_mean(armname, t):
        vals = []
        for k in samples:
            if k[0] != armname:
                continue
            for seen, bound in zip(samples[k], cover[k]):
                if t <= bound:               # within this sample's coverage
                    vals.append(seen.get(t, 0))
        return (sum(vals) / len(vals), len(vals)) if vals else (None, 0)
    print(f"\nrace\t{a1}\t{a2}\tdelta\tn({a1}/{a2})\tverdict")
    rows = []
    for t in allraces:
        mx, nx = arm_mean(a1, t)
        my, ny = arm_mean(a2, t)
        # A race needs coverage in at least HALF of each arm's samples. Below that the surviving
        # samples are biased: a control sample only reaches the S's when it happens to list FEWER
        # species, so "SNAKE_FIRE 0.0 in control over 13 of 68 samples" is a property of the
        # truncation, not of the fort.
        need = max(5, min(len(samples[k]) for k in samples) // 2)
        if mx is None or my is None or nx < need or ny < need:
            rows.append((-1, t, mx, my, nx, ny, "NOT COMPARABLE — truncated out of one arm"))
            continue
        hi = max(mx, my)
        if hi < 0.5:
            continue
        verdict = ("ELIMINATED in " + a2 if my == 0 and mx >= 1 else
                   "ELIMINATED in " + a1 if mx == 0 and my >= 1 else
                   "down in " + a2 if hi and (mx - my) / hi > 0.4 else
                   "down in " + a1 if hi and (my - mx) / hi > 0.4 else "flat")
        rows.append((abs(mx - my), t, mx, my, nx, ny, verdict))
    ok = [r for r in rows if r[0] >= 0]
    bad = [r for r in rows if r[0] < 0]
    for _, t, mx, my, nx, ny, verdict in sorted(ok, reverse=True, key=lambda r: (r[0], r[1])):
        f = lambda v: "  -  " if v is None else f"{v:.1f}"
        print(f"{t}\t{f(mx)}\t{f(my)}\t{'' if mx is None or my is None else f'{my-mx:+.1f}'}\t{nx}/{ny}\t{verdict}")
    if bad:
        print("\nnot comparable — truncated out of one arm too often to trust:")
        print("  " + ", ".join(f"{t} ({nx}/{ny})" for _, t, _, _, nx, ny, _ in sorted(bad, key=lambda r: r[1])))
    print("\nKILL: races whose ENTRY was zeroed go to zero or fall sharply while untouched races stay flat")
