#!/usr/bin/env python3
"""Read a v7.1-harness ECO run: manipulation receipts first, then outcomes scored the v7.1 way.

  python3 scripts/eco-v71-tally.py data/experiments/ECO/RUN [BLOCK ...]

Per block, cell and rep:
  manip     the receipts (wipe marked, spawn placed, adopt, cfg values, checks) and any MANIPFAIL -- read these first;
            a cell whose manipulation failed has no outcome to read (H2)
  attacks   split by origin (H4): placed>placed (DF's aiming isolated when the block ran with --isolate roam),
            drawn>* (DF-drawn subjects), and any pair that involves a released or fort-side unit, kept apart
  bouts     engagements per hunter-day from the timestamped attacks (H6: gaps < the watch's bout_gap)
  hidden    share of 10-t samples with the hunter hidden, overall and just after its attacks (H6)
  groups3   the last groups3 summary per layer: live groups vs the tool's, with untracked / split / merged / stale /
            no-population counts (H5: one definition, three sources)
Means are over reps; n is printed next to every mean (R12: 5 reps per arm by default).
"""
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ecolib import kv as _kv  # noqa: E402


def kv(rest):
    return _kv("eco x " + rest)


def load(path):
    rows = defaultdict(list)   # (block, cell, rep) -> [(kind, dict, raw)]
    for line in open(path, errors="replace"):
        p = line.rstrip("\n").split("\t")
        if len(p) < 5:
            continue
        b, c, r, kind, rest = p[0], p[1], p[2], p[3], p[4]
        rows[(b, c, r)].append((kind, kv(rest) if kind not in ("MANIPFAIL", "FAILED") else {"msg": rest}, rest))
    return rows


def fmt(xs):
    return f"{mean(xs):.2f} (n={len(xs)})" if xs else "-"


def tally(path):
    rows = load(path)
    cells = defaultdict(dict)
    for (b, c, r), recs in rows.items():
        cells[(b, c)][r] = recs
    for (b, c), reps in sorted(cells.items()):
        print(f"\n== {b} / {c}: {len(reps)} rep(s)")
        fails = [(r, d["msg"]) for r, recs in reps.items() for k, d, _ in recs if k in ("MANIPFAIL", "FAILED")]
        for r, m in fails:
            print(f"   rep {r}: {m[:160]}")
        ok_reps = {r: recs for r, recs in reps.items() if not any(k in ("MANIPFAIL", "FAILED") for k, _, _ in recs)}
        wiped = [int(d.get("marked", 0)) for recs in ok_reps.values() for k, d, _ in recs if k == "wipe"]
        checks = [d.get("check", "") for recs in ok_reps.values() for k, d, _ in recs if k == "manip"]
        adopt = [d.get("adopted") for recs in ok_reps.values() for k, d, _ in recs if k == "adopt"]
        print(f"   manip: {len(ok_reps)} clean rep(s); wiped per rep {wiped or '-'}; adopt {adopt or '-'}; "
              f"{len(checks)} explicit check(s) passed")
        per_rep = []
        bph = defaultdict(list)
        hid = defaultdict(lambda: [0, 0, 0, 0])
        for recs in ok_reps.values():
            per = defaultdict(int)
            for k, d, _ in recs:
                if k == "attacks_o":
                    a, _, t = d["pair"].partition(">")
                    ao, to = a[a.find("(") + 1:-1], t[t.find("(") + 1:-1]
                    cls = ("placed>placed" if ao == to == "placed" else "drawn>drawn" if ao == to == "drawn"
                           else f"{ao}>{to}")
                    per[cls] += int(d.get("n", 0))
                elif k == "bouts":
                    bph[d.get("atok", "?")].append(float(d.get("per_hunter_day", 0)))
                elif k == "hidden":
                    h = hid[d.get("token", "?")]
                    h[0] += int(d.get("samples", 0)); h[1] += int(d.get("hidden", 0))
                    h[2] += int(d.get("near", 0)); h[3] += int(d.get("near_hidden", 0))
            per_rep.append(per)
        classes = sorted(set().union(*per_rep)) if per_rep else []
        split = {cls: [p.get(cls, 0) for p in per_rep] for cls in classes}   # a rep without the class counts 0
        for cls, xs in sorted(split.items()):
            print(f"   attacks {cls:<22} {fmt(xs)}")
        for tok, xs in sorted(bph.items()):
            print(f"   bouts/hunter-day {tok:<18} {fmt(xs)}")
        for tok, (n, h, nn, nh) in sorted(hid.items()):
            print(f"   hidden {tok:<18} {h}/{n} samples ({100 * h / n if n else 0:.2f}%); after attacks {nh}/{nn}")
        last = {}
        for recs in ok_reps.values():
            for k, d, _ in recs:
                if k == "g3sum":
                    last[d.get("layer")] = d
        for layer, d in sorted(last.items()):
            print(f"   groups3 {layer:<12} live {d.get('live_groups')} tool {d.get('tool_groups')} match {d.get('match')} "
                  f"untracked {d.get('untracked')} split {d.get('split')} merged {d.get('merged')} stale {d.get('stale')} "
                  f"nopop {d.get('nopop')}")


def main(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    run = Path(argv[1])
    blocks = argv[2:] or sorted(p.stem for p in run.glob("*.tsv"))
    for b in blocks:
        f = run / f"{b}.tsv"
        if f.exists():
            tally(f)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
