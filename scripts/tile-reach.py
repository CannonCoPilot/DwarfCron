#!/usr/bin/env python3
"""The tile-reach test (user 15 Oct 2026): does a flier with population entries on more region tiles get drawn more often?

Two solitary fliers at the same FREQUENCY and stock, every other surface Animal entry on the fort's draw tiles closed: one
flier open on the site tile only, the other on every draw tile (cx-tilereach setup). DF's waves are collected as they land
(source tile recorded) and vanished so the next wave can come. Replicates alternate which species has the one tile, so a
species effect cancels. If DF picks per entry, the many-tile species takes about k/(k+1) of the waves (k = its tiles); if
it picks per species, about half.

    tile-reach.py FORT A B [--reps 4] [--waves 40] [--step 600] [--max-ticks 90000] [--name RUN]
Writes data/tile-reach/RUN/: waves.tsv (rep, one, tick, race, n, rx, ry, site|neighbour), setup.txt, summary.md.
Runs on the loaded rig; every replicate loads FORT fresh and leaves it unsaved (quit to title)."""
from __future__ import annotations

import argparse
import datetime as dt
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
L = str(ROOT / 'scripts' / 'cx-lifecycle.sh')


def sh(*a, timeout=600) -> str:
    r = subprocess.run([L, *a], capture_output=True, text=True, timeout=timeout)
    return (r.stdout + r.stderr).replace('\r', '')


def binom_p(k: int, n: int) -> float:
    """two-sided exact binomial p for k of n at 0.5"""
    if n == 0:
        return 1.0
    pk = [math.comb(n, i) / 2 ** n for i in range(n + 1)]
    return min(1.0, sum(p for p in pk if p <= pk[k] + 1e-12))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('fort'); ap.add_argument('a'); ap.add_argument('b')
    ap.add_argument('--reps', type=int, default=4); ap.add_argument('--waves', type=int, default=40)
    ap.add_argument('--step', type=int, default=600); ap.add_argument('--max-ticks', type=int, default=90000)
    ap.add_argument('--name', default=dt.datetime.now().strftime('%Y%m%d-%H%M%S'))
    o = ap.parse_args()
    out = ROOT / 'data' / 'tile-reach' / o.name
    out.mkdir(parents=True, exist_ok=True)
    W = open(out / 'waves.tsv', 'w')
    W.write('rep\tone_tile\ttick\trace\tn\trx\try\tsource\n')
    log = open(out / 'setup.txt', 'w')
    reps = []
    for rep in range(1, o.reps + 1):
        one = o.a if rep % 2 else o.b
        st = sh('state')
        if 'map=true' in st:
            sh('title')
        print(f'rep {rep}: load {o.fort}', flush=True)
        r = sh('load', o.fort, timeout=900)
        if 'loaded after' not in r:
            raise SystemExit(f'load failed: {r[-400:]}')
        log.write(f'== rep {rep} (one tile: {one})\n')
        log.write(sh('cmd', 'seasonal-wildlife', 'disable'))
        if rep == 1:
            log.write(sh('cmd', 'cx-tilereach', 'info'))
        s = sh('cmd', 'cx-tilereach', 'setup', o.a, o.b, one)
        log.write(s); log.write(sh('cmd', 'cx-tilereach', 'state')); log.flush()
        print('  ' + next((x for x in s.splitlines() if x.startswith('SETUP')), s[-300:]), flush=True)
        if 'SETUP' not in s:
            raise SystemExit('setup failed')
        sh('cmd', 'cx-tilereach', 'collect')   # anything already arriving
        got, ticks, leaks = {o.a: 0, o.b: 0}, 0, 0
        src = {o.a: {}, o.b: {}}
        while sum(got.values()) < o.waves and ticks < o.max_ticks:
            r = sh('step', str(o.step))
            ticks += o.step
            for line in sh('cmd', 'cx-tilereach', 'collect').splitlines():
                if not line.startswith('WAVE '):
                    continue
                _, tick, race, n, rx, ry, where = line.split()
                W.write(f'{rep}\t{one}\t{tick}\t{race}\t{n}\t{rx}\t{ry}\t{where}\n')
                if race in got:
                    got[race] += 1
                    src[race][f'{rx}:{ry}'] = src[race].get(f'{rx}:{ry}', 0) + 1
                else:
                    leaks += 1
            W.flush()
        many = o.b if one == o.a else o.a
        reps.append({'rep': rep, 'one': one, 'many': many, 'one_n': got[one], 'many_n': got[many], 'ticks': ticks, 'leaks': leaks,
                     'src_many': src[many]})
        print(f'  rep {rep}: {one} (1 tile) {got[one]}, {many} (all tiles) {got[many]} in {ticks} ticks; {leaks} other', flush=True)
        sh('title')
    k1 = sum(r['one_n'] for r in reps); kn = sum(r['many_n'] for r in reps)
    p = binom_p(kn, k1 + kn)
    with open(out / 'summary.md', 'w') as f:
        f.write(f'# tile-reach {o.name}: {o.fort}, {o.a} v {o.b}\n\n| rep | one tile | waves | all tiles | waves | ticks | other |\n|---|---|---|---|---|---|---|\n')
        for r in reps:
            f.write(f"| {r['rep']} | {r['one']} | {r['one_n']} | {r['many']} | {r['many_n']} | {r['ticks']} | {r['leaks']} |\n")
        f.write(f'\nAll replicates: one-tile species {k1}, all-tile species {kn}; share {kn / max(1, k1 + kn):.2f}; '
                f'two-sided binomial p against 0.5 = {p:.3g}.\n\nSources of the all-tile species\' waves, per replicate:\n')
        for r in reps:
            f.write(f"- rep {r['rep']}: {r['src_many']}\n")
    print((out / 'summary.md').read_text())


if __name__ == '__main__':
    main()
