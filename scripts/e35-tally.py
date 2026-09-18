#!/usr/bin/env python3
"""E35 — is FREQUENCY a comparative weight or an independent probability?

Both arms hold the SAME 4:1 ratio (TROGLODYTE:ELK_BIRD) at very different absolute levels,
100+25 against 4+1, with every other cavern-capable creature zeroed. The mix cannot separate
the models -- a ratio of independent probabilities tracks the frequency ratio too -- so the
discriminator is the TOTAL:

  comparative (shared spawn budget) -> both arms give the same total; only shares move
  independent probability           -> the low arm gives ~25x fewer arrivals, same mix

E34's untouched control on the same fort at the same length is the outside baseline: 67 and
91 total cavern arrivals with every species at its natural frequency.

    scripts/e35-tally.py [run_dir]
"""
import csv, sys, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAIR = ("TROGLODYTE", "ELK_BIRD")
E34_CONTROL_TOTALS = (67, 91)   # cavern arrivals per replicate, all species at natural frequency


def main():
    run = Path(sys.argv[1]) if len(sys.argv) > 1 else max(
        (ROOT / "data/experiments/E35").glob("*"), key=lambda p: p.name)
    arr = collections.defaultdict(collections.Counter)
    for e in csv.DictReader((run / "events.tsv").open(), delimiter="\t"):
        if e["event"] != "arrival":
            continue
        d = e["detail"].split()
        kv = dict(p.split("=", 1) for p in d[1:] if "=" in p)
        if kv.get("layer") != "cavern":
            continue
        arr[(e["arm"], e["rep"])][d[0]] += 1

    print(f"E35 — {run.name}\n")
    totals = collections.defaultdict(list)
    for key in sorted(arr):
        c = arr[key]
        a, b = c[PAIR[0]], c[PAIR[1]]
        other = sum(v for k, v in c.items() if k not in PAIR)
        tot = a + b
        ratio = (f"{a/b:.1f}:1" if b else ("all A" if a else "none"))
        print(f"  {key[0]:<10} rep{key[1]}   {PAIR[0]} {a:3d}   {PAIR[1]} {b:3d}   "
              f"total {tot:3d}   mix {ratio:>7}   leaked from zeroed species: {other}")
        totals[key[0]].append(tot)

    print()
    hi = totals.get("high_4to1", [])
    lo = totals.get("low_4to1", [])
    if not (hi and lo):
        print("  (both arms not finished yet)")
        return 0
    mh, ml = sum(hi) / len(hi), sum(lo) / len(lo)
    print(f"  mean total   high (sum 125): {mh:.1f}      low (sum 5): {ml:.1f}")
    print(f"  E34 control, every species at its natural frequency: {E34_CONTROL_TOTALS} "
          f"(mean {sum(E34_CONTROL_TOTALS)/2:.1f})")
    print()
    if ml == 0 and mh > 0:
        print("  READS AS: independent probability — the low arm produced nothing at all.")
    elif mh and ml / mh > 0.6:
        print("  READS AS: COMPARATIVE WEIGHT — a 25-fold cut in absolute frequency barely moved the")
        print("            total, so the arms share a spawn budget and frequency sets shares.")
        print("            Frequency is an ecosystem-composition lever.")
    elif mh and ml / mh < 0.25:
        print("  READS AS: INDEPENDENT PROBABILITY — the total scaled with the absolute level, so")
        print("            frequency sets each species' own spawn rate, not its share.")
        print("            Balancing means managing absolute levels against each other.")
    else:
        print(f"  READS AS: neither cleanly — low/high = {ml/mh:.2f}. Report the numbers, not a model.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
