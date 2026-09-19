#!/usr/bin/env python3
"""E31a tally: what draws a feature (water) population entry when nothing is fishing it?

E26 left this loose end with a SPECIFIC entry: mussels fell 5005 -> 4701 across a year on a fort
with no fishing labour. So the total is the wrong statistic — it pools ~70,000 across a dozen
entries and a 300-unit move in one of them is 0.4% of it. The sampler lists the first ten entries
by name every pass (a fixed cap in stable iteration order, so the same ten throughout), which is
enough to follow each one individually. That per-entry trajectory is the finding: a steady slope
means a continuous background drain the water job must budget for; discrete steps mean an event,
and the step size names the consumer; flat means E26's fall came from something the tool did.

Day is NOT used for the span: cur_year_tick/1200 wraps at the year boundary, so a full-year run
reads "day 14-15" and hides that it covered 336 days. abs_tick is authoritative.
Usage: e31-tally.py [run_dir]"""
import csv, glob, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tallylib import drop_incomplete
from collections import defaultdict

run_dir = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob("data/experiments/E31/*"))[-1]
SAMPLE = re.compile(r"e31: feature_pool_total=(\d+) citizens=(\d+) day=(\d+) \| (.*)$")
ENTRY = re.compile(r"([A-Z0-9_ ]+)\[(\w+)\]=(\d+)")

tot = defaultdict(list)                                  # key -> [(abs_tick, total, citizens)]
ent = defaultdict(lambda: defaultdict(list))             # key -> "NAME[type]" -> [(abs_tick, qty)]
for r in csv.DictReader(open(f"{run_dir}/events.tsv"), delimiter="\t"):
    if r["event"] != "manipulation":
        continue
    m = SAMPLE.search(r["detail"])
    if not m:
        continue
    k = (r["arm"], int(r["rep"])); at = int(r["abs_tick"])
    tot[k].append((at, int(m.group(1)), int(m.group(2))))
    for name, ty, q in ENTRY.findall(m.group(4)):
        ent[k][f"{name.strip()}[{ty}]"].append((at, int(q)))
drop_incomplete(run_dir, tot, ent)

print(f"run {run_dir}")
for k in sorted(tot):
    t = tot[k]
    span_t = (t[-1][0] - t[0][0]) / 1200.0
    print(f"\n=== {k[0]} rep {k[1]}: {len(t)} samples over {span_t:.0f} days "
          f"({t[0][0]} -> {t[-1][0]} abs_tick), citizens {t[0][2]} -> {t[-1][2]}")
    print(f"    pool total {t[0][1]} -> {t[-1][1]} ({t[-1][1]-t[0][1]:+d}, "
          f"{100.0*(t[-1][1]-t[0][1])/t[0][1]:+.2f}%)  — the total pools every entry and hides them")
    print(f"    {'entry':28} {'start':>7} {'end':>7} {'net':>7} {'%':>7}  {'moves':>5}  shape / largest steps")
    for name, series in sorted(ent[k].items(), key=lambda kv: kv[1][0][1], reverse=True):
        a, b = series[0][1], series[-1][1]
        deltas = [(t1, q1 - q0) for (_, q0), (t1, q1) in zip(series, series[1:]) if q1 != q0]
        moves = len(deltas)
        downs = [d for _, d in deltas if d < 0]
        pct = (100.0 * (b - a) / a) if a else 0.0
        if moves == 0:
            shape = "FLAT — never moved"
        elif moves <= max(3, len(series) // 20):
            shape = "discrete steps"
        else:
            shape = "steady slope" if abs(pct) > 0.5 else "jitter, no net drift"
        big = sorted(deltas, key=lambda d: d[1])[:3]
        detail = ", ".join(f"{d:+d}@t{t1}" for t1, d in big) if big else ""
        print(f"    {name:28} {a:>7} {b:>7} {b-a:>+7} {pct:>6.2f}%  {moves:>5}  {shape}"
              + (f"   worst: {detail}" if detail else ""))
    # ⚠️ The sampler lists only the first TEN managed entries, and on LAKE the entry that actually
    # drains is not among them — so the per-sample table above can read "everything is flat" while
    # the pool total falls. pops_all carries all 472 feature entries at start and end, which finds
    # the movers; what it cannot give is their SHAPE, because it is only two snapshots. A rerun
    # that wants the shape must sample every feature entry, or at least every Vermin one.
    import os as _os
    pa = _os.path.join(run_dir, "pops_all.tsv")
    if _os.path.exists(pa):
        st, en = {}, {}
        for r in csv.DictReader(open(pa), delimiter="\t"):
            if (r["arm"], int(r["rep"])) != k or r["layer"] != "feature":
                continue
            (st if r["phase"] == "start" else en)[r["idx"]] = r
        moved = [(i, int(st[i]["quantity"]), int(en[i]["quantity"]), st[i]["species"], st[i]["type"])
                 for i in st if i in en and st[i]["quantity"] != en[i]["quantity"]]
        print(f"\n    every feature entry at start/end: {len(st)} entries, {len(moved)} moved over the year")
        for i, a, b, sp, ty in sorted(moved, key=lambda x: -abs(x[2] - x[1])):
            pct = (100.0 * (b - a) / a) if a else 0.0
            note = ("DRAIN" if b < a and abs(pct) > 1 else
                    "departure refund (addendum 30)" if b > a and ty == "Animal" else "noise")
            print(f"      idx {i:>5} {sp:22} {ty:8} {a:>7} -> {b:>7} ({b-a:+d}, {pct:+.2f}%)  {note}")

    # the E26 entry specifically
    for name, series in ent[k].items():
        if name.startswith("MUSSEL"):
            a, b = series[0][1], series[-1][1]
            print(f"\n    E26's entry: MUSSEL {a} -> {b} ({b-a:+d}, {100.0*(b-a)/a:+.2f}%) across {span_t:.0f} days")
            print(f"      E26 measured 5005 -> 4701 (-6.07%) over a year with no fishing labour.")
