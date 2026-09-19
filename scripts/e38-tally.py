#!/usr/bin/env python3
"""E38 tally: the tool's recurring job cost, paired WITHIN each replicate.

E37 could not resolve the cost because identical replicates disagree by 10-16% — the noise
lives between rig loads. E38 toggles the tool's jobs on and off in alternating 8,000-tick
blocks inside one replicate, so on-samples and off-samples share one load, one save, one
thermal state and one population trajectory, and that variance differences away.

Each `e38:` receipt carries `during=` — the scheduler state in force over the interval whose
fps it reports — because `calculated_fps` is a rolling average of time already elapsed.
The `toggle` arm really flips; the `sham` arm runs the same block bookkeeping and never
touches the scheduler, so its "apparent difference" is what the method finds when there is
nothing to find. The kill criterion is the manifest's: a paired difference consistent in
sign across both toggle replicates AND larger than the sham's apparent difference.

Culls, applied and reported: no `done:` line (tallylib); the first sample of every block
(fps has not settled after a toggle); a replicate whose `during=` never alternates (the
toggle did not fire); a replicate at the cap.

Usage: e38-tally.py [run_dir]
"""
import csv, glob, re, statistics, sys
from collections import defaultdict

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import tallylib

run_dir = sys.argv[1] if len(sys.argv) > 1 else sorted(
    d for d in glob.glob("data/experiments/E38/*") if "VACUOUS" not in d)[-1]

RECEIPT = re.compile(r"e38: fps=(\d+) during=(\w+) now=(\w+) blk=(\d+) posn=(\d+) units=(\d+) citizens=(\d+) day=(\d+)")
BLK = 8000

samples = defaultdict(list)     # (arm, rep) -> [(blk, posn, during, fps, units)]
cap = {}
for r in csv.DictReader(open(f"{run_dir}/events.tsv"), delimiter="\t"):
    m = RECEIPT.search(r["detail"])
    if not m:
        continue
    k = (r["arm"], int(r["rep"]))
    samples[k].append((int(m.group(4)), int(m.group(5)), m.group(2) == "true", int(m.group(1)), int(m.group(6))))
for r in csv.DictReader(open(f"{run_dir}/rows.tsv"), delimiter="\t"):
    if r["subject"] == "clock" and r["metric"] == "fps_cap":
        cap[(r["arm"], int(r["rep"]))] = float(r["value"])

tallylib.drop_incomplete(run_dir, samples)

print(f"run {run_dir}")
culled = {}
per_rep = {}
for k in sorted(samples):
    s = samples[k]
    # first sample of each block is discarded: the rolling average still holds the old phase
    first_posn = {}
    for blk, posn, *_ in s:
        first_posn[blk] = min(first_posn.get(blk, 10**9), posn)
    kept = [x for x in s if x[1] != first_posn[x[0]]]
    dropped = len(s) - len(kept)
    durings = {x[2] for x in s}
    why = []
    if k[0] == "toggle" and len(durings) < 2:
        why.append("trigger failure: `during=` never alternated — the toggle did not fire")
    c = cap.get(k, 0)
    if kept and c and statistics.mean(x[3] for x in kept) >= 0.95 * c:
        why.append(f"vacuous: ran at the cap ({statistics.mean(x[3] for x in kept):.0f} of {c:.0f})")
    if why:
        culled[k] = why
        continue
    # phase membership: the toggle arm by what was actually in force; the sham arm by the
    # same block parity the toggle arm would have used, so it is bookkept identically
    if k[0] == "toggle":
        on = [x[3] for x in kept if x[2]]
        off = [x[3] for x in kept if not x[2]]
    else:
        on = [x[3] for x in kept if x[0] % 2 == 0]
        off = [x[3] for x in kept if x[0] % 2 == 1]
    if not on or not off:
        culled[k] = ["one phase has no surviving samples"]
        continue
    mo, mf = statistics.mean(on), statistics.mean(off)
    # the E37 confound, inside one replicate: if the on-blocks carried more animals than the
    # off-blocks, part of the gap is population, not jobs. Report both unit means so that is
    # visible, and the per-unit charge the gap would imply if it were ALL population.
    if k[0] == "toggle":
        u_on = [x[4] for x in kept if x[2]]; u_off = [x[4] for x in kept if not x[2]]
    else:
        u_on = [x[4] for x in kept if x[0] % 2 == 0]; u_off = [x[4] for x in kept if x[0] % 2 == 1]
    per_rep[k] = dict(n_on=len(on), n_off=len(off), on=mo, off=mf, diff=mf - mo,
                      pct=100.0 * (mf - mo) / mf, dropped=dropped,
                      units=statistics.mean(x[4] for x in kept),
                      u_on=statistics.mean(u_on), u_off=statistics.mean(u_off),
                      blocks=sorted({x[0] for x in kept}))

if culled:
    print("\n!! CULLED — per the manifest's own criteria:")
    for k, why in culled.items():
        print(f"   {k[0]} rep {k[1]}: " + "; ".join(why))

print("\nper replicate — paired within the replicate (off minus on; positive = the jobs cost fps)")
print("arm\trep\tblocks\tn on/off\tfps on\tfps off\toff-on\t%\tunits on/off\tdropped(1st of block)")
for k in sorted(per_rep):
    p = per_rep[k]
    print(f"{k[0]}\t{k[1]}\t{len(p['blocks'])}\t{p['n_on']}/{p['n_off']}\t{p['on']:.1f}\t{p['off']:.1f}"
          f"\t{p['diff']:+.1f}\t{p['pct']:+.1f}\t{p['u_on']:.0f}/{p['u_off']:.0f}\t{p['dropped']}")
print("\nthe load confound, inside each replicate")
for k in sorted(per_rep):
    p = per_rep[k]
    du = p['u_on'] - p['u_off']
    line = f"  {k[0]} rep {k[1]}: on-blocks {p['u_on']:.1f} units, off-blocks {p['u_off']:.1f} ({du:+.1f})"
    if k[0] == "toggle" and abs(du) >= 1:
        line += f" -> if the whole {p['diff']:+.1f} fps gap were population it would be {p['diff']/du:+.2f} fps/animal"
        line += "; E37 measured DF's own charge at about -1.6 fps/animal between arms, so " + (
            "population could account for most of it — read the gap as an UPPER bound on the jobs" if abs(p['diff']/du) <= 3 and du > 0
            else "the population difference cannot explain the gap; it is the jobs")
    print(line)

tog = [per_rep[k] for k in sorted(per_rep) if k[0] == "toggle"]
sham = [per_rep[k] for k in sorted(per_rep) if k[0] == "sham"]

print("\nthe verdict")
if len(tog) < 2 or len(sham) < 2:
    print(f"  incomplete: {len(tog)} toggle and {len(sham)} sham replicate(s) survive; need 2 and 2")
else:
    tpct = [p["pct"] for p in tog]
    spct = [p["pct"] for p in sham]
    sham_floor = max(abs(x) for x in spct)
    same_sign = (min(tpct) > 0) or (max(tpct) < 0)
    print(f"  toggle arm: off-on = {tpct[0]:+.1f}% and {tpct[1]:+.1f}%")
    print(f"  sham arm:   apparent = {spct[0]:+.1f}% and {spct[1]:+.1f}%  -> the method's own floor is {sham_floor:.1f}%")
    if same_sign and all(abs(x) > sham_floor for x in tpct):
        if min(tpct) > 0:
            print(f"  => A MEASURABLE RECURRING COST: the jobs cost {min(tpct):.1f}-{max(tpct):.1f}% of frame rate,")
            print("     same sign in both replicates and clear of the sham floor.")
        else:
            print(f"  => tool-on ran FASTER in both replicates, clear of the sham floor ({min(tpct):.1f} to {max(tpct):.1f}%).")
            print("     Not a speedup claim: check whether the jobs held the population down in the on blocks.")
    elif not same_sign:
        print("  => NO RESOLVABLE COST: the two toggle replicates disagree in sign. Whatever the jobs cost,")
        print(f"     it is smaller than the within-replicate noise (sham floor {sham_floor:.1f}%).")
    else:
        print(f"  => BELOW THE METHOD'S FLOOR: consistent sign, but |{max(abs(x) for x in tpct):.1f}%| does not clear the")
        print(f"     sham arm's {sham_floor:.1f}%. The honest bound is: recurring cost under ~{sham_floor:.0f}%.")
    print("  (E37 bounded the cost at <16% between loads; this pairs inside a load and should be tighter.)")
