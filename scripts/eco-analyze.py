#!/usr/bin/env python3
"""ECO analysis. Usage: eco-analyze.py <run dir> [block ...]

Per cell, from the block TSVs eco-run.py wrote:
  kills   = Death incidents whose killer AND victim were spawned in the cell (natives excluded; VANISH never counted)
  attacks = UNIT_ATTACK events between the cell's spawned species, by direction (a native of a spawned species can
            leak into this count -- CTRL carries wild DINGO/WOLF/KANGAROO -- so kills are the primary readout)
  groups  = alive/dead/gone, spread (mean tiles from the group's centroid) and units standing in water, at the end
P1 is printed as predator x prey matrices (DF only / relation written); every other block as one row per cell.
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

def kv(s):
    return dict(t.split("=", 1) for t in s.split() if "=" in t)

def load(path):
    cells = defaultdict(lambda: dict(spawn={}, attacks=defaultdict(int), kills=defaultdict(int), groups={}, other=[], failed=None))
    order = []
    for line in open(path):
        p = line.rstrip("\n").split("\t")
        if len(p) < 5:
            continue
        _, cell, rep, kind, rest = p[:5]
        key = (cell, rep)
        if key not in cells:
            order.append(key)
        c = cells[key]
        d = kv(rest)
        if kind == "FAILED":
            c["failed"] = rest
        elif kind == "spawn":
            c["spawn"][d["token"]] = c["spawn"].get(d["token"], 0) + int(d.get("placed", 0))
        elif kind == "attacks":
            # a raw id may hold a space ('RIVER OTTER'), which kv() splits on: read the pair between 'pair=' and ' n='
            m = re.search(r"pair=(.+?)>(.+?) n=(\d+)", rest)
            if not m: continue
            a, b = m.group(1), m.group(2); d["n"] = m.group(3)
            if a in c["spawn"] and b in c["spawn"]:
                c["attacks"][(a, b)] += int(d["n"])
        elif kind == "death":
            if d.get("victim_spawned") == "1" and d.get("killer_spawned") == "1":
                c["kills"][(d["killer"], d["victim"])] += 1
        elif kind == "group":
            c["groups"][d["token"]] = d
        else:
            c["other"].append((kind, d))
    return [(k, cells[k]) for k in order]

def p1(rows):
    arms = {}
    for (cell, rep), c in rows:
        pair, arm = cell.split(":")
        a, b = pair.split("x", 1)
        arms.setdefault(arm, {})[(a, b)] = c
    preds = sorted({a for m in arms.values() for a, _ in m}, key=lambda t: ["WOLF", "COYOTE", "DINGO", "HYENA", "CHEETAH", "LION", "BEAR_GRIZZLY", "FOX"].index(t) if t in ["WOLF", "COYOTE", "DINGO", "HYENA", "CHEETAH", "LION", "BEAR_GRIZZLY", "FOX"] else 99)
    preys = ["RABBIT", "GAZELLE", "DEER", "KANGAROO", "WATER_BUFFALO"]
    for arm in ("df", "w"):
        if arm not in arms:
            continue
        print(f"\n-- P1 {'DF only (no relation written)' if arm == 'df' else 'relation written (PREDATOR_OR_PREY)'}: kills of 10 prey by 6 predators in 3,000 t [attacks pred>prey / prey>pred]")
        print(f"  {'':<13}" + "".join(f"{q:>17}" for q in preys))
        for a in preds:
            cells = []
            for q in preys:
                c = arms[arm].get((a, q))
                if not c:
                    cells.append(f"{'-':>17}"); continue
                if c["failed"]:
                    cells.append(f"{'FAILED':>17}"); continue
                k = c["kills"].get((a, q), 0); kr = c["kills"].get((q, a), 0)
                at, ab = c["attacks"].get((a, q), 0), c["attacks"].get((q, a), 0)
                cells.append(f"{k:>3}{('/-' + str(kr)) if kr else '':<3} [{at:>3}/{ab:<3}]")
            print(f"  {a:<13}" + "".join(f"{x:>17}" for x in cells))

def rowwise(name, rows):
    print(f"\n-- {name}")
    for (cell, rep), c in rows:
        if c["failed"]:
            print(f"  {cell:<34} FAILED {c['failed'][:120]}"); continue
        sp = " ".join(f"{t}x{n}" for t, n in c["spawn"].items())
        ks = " ".join(f"{a}>{b}:{n}" for (a, b), n in c["kills"].items()) or "0"
        at = " ".join(f"{a}>{b}:{n}" for (a, b), n in c["attacks"].items()) or "0"
        gs = " ".join(f"{t}[alive {g['alive']} dead {g['dead']} gone {g['gone']} spread {g['spread']} wet {g['wet']}]" for t, g in c["groups"].items())
        extra = " ".join(f"{k}:{' '.join(f'{x}={y}' for x, y in d.items() if x not in ('tag',))}" for k, d in c["other"]
                         if k not in ("watch", "clear", "restore", "rel"))
        print(f"  {cell:<34} spawned {sp}; kills {ks}; attacks {at}\n  {'':<34} {gs}\n  {'':<34} {extra[:400]}")

def main():
    run = Path(sys.argv[1])
    want = sys.argv[2:] or [p.stem for p in sorted(run.glob("*.tsv"))]
    for b in want:
        f = run / f"{b}.tsv"
        if not f.exists():
            continue
        rows = load(f)
        if b == "P1":
            p1(rows)
        else:
            rowwise(b, rows)

if __name__ == "__main__":
    main()
