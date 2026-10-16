#!/usr/bin/env python3
"""The never-arrive test (user 15 Oct 2026): can DF send a cavern wave of these species at all?

15 cast cavern species never arrived in 16 full-year forts (the cave animal people, the gremlin, the plain prey). For each
SUBJECT: load FORT fresh (DF restarted first), the tool disabled, then `cx-cavearrive setup` puts SUBJECT and CONTROL on the
same footing in one cavern (one open entry each on every draw tile x cave of that depth, same quantity and FREQUENCY,
every other Animal entry there closed). Waves are collected as they land and every wild cavern animal vanished so the
gate stays clear. Equal footing gives the subject about half the waves; a bar gives it none.

    cave-arrive.py FORT CONTROL SUBJ [SUBJ ...] [--depth 1] [--waves 20] [--step 1000] [--max-ticks 50000] [--name RUN]
Writes data/cave-arrive/RUN/: waves.tsv (subject, tick, race, n, rx, ry, depth), setup.txt, summary.md.
Every subject's fort is left unsaved (quit to title)."""
from __future__ import annotations

import argparse
import datetime as dt
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
L = str(ROOT / 'scripts' / 'cx-lifecycle.sh')


class Hung(Exception):
    pass


def sh(*a, timeout=600) -> str:
    try:
        r = subprocess.run([L, *a], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise Hung(' '.join(a)) from e
    return (r.stdout + r.stderr).replace('\r', '')


def binom_p(k: int, n: int) -> float:
    """two-sided exact binomial p for k of n at 0.5"""
    if n == 0:
        return 1.0
    pk = [math.comb(n, i) / 2 ** n for i in range(n + 1)]
    return min(1.0, sum(p for p in pk if p <= pk[k] + 1e-12))


def one(o, subj, W, log):
    print(f'{subj}: restart DF, load {o.fort}', flush=True)
    sh('restart', timeout=300)
    r = sh('load', o.fort, timeout=900)
    if 'loaded after' not in r:
        raise SystemExit(f'load failed: {r[-400:]}')
    log.write(f'== {subj} v {o.control}, cavern {o.depth}\n')
    log.write(sh('cmd', 'seasonal-wildlife', 'disable'))
    s = sh('cmd', 'cx-cavearrive', 'setup', str(o.depth), subj, o.control, str(o.freq), str(o.qty))
    log.write(s); log.write(sh('cmd', 'cx-cavearrive', 'state', str(o.depth))); log.flush()
    line = next((x for x in s.splitlines() if x.startswith('SETUP')), '')
    print('  ' + (line or s[-300:]), flush=True)
    for x in s.splitlines():
        if x.startswith('WARN'):
            print('  ' + x, flush=True)
    if not line:
        raise SystemExit('setup failed')
    sh('cmd', 'cx-cavearrive', 'collect')
    got, other, ticks = {subj: 0, o.control: 0}, {}, 0
    while sum(got.values()) < o.waves and ticks < o.max_ticks:
        sh('step', str(o.step), timeout=180)
        ticks += o.step
        for x in sh('cmd', 'cx-cavearrive', 'collect', timeout=120).splitlines():
            if not x.startswith('WAVE '):
                continue
            _, tick, race, n, rx, ry, d = x.split()
            race = race.replace('_', ' ') if race.replace('_', ' ') in got else race
            W.write(f'{subj}\t{tick}\t{race}\t{n}\t{rx}\t{ry}\t{d}\n')
            if race in got and d == str(o.depth):
                got[race] += 1
            else:
                other[f'{race}@{d}'] = other.get(f'{race}@{d}', 0) + 1
        W.flush()
    sh('title')
    return {'subj': subj, 'n_subj': got[subj], 'n_ctrl': got[o.control], 'ticks': ticks, 'other': other, 'setup': line}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('fort'); ap.add_argument('control'); ap.add_argument('subjects', nargs='+')
    ap.add_argument('--depth', type=int, default=1); ap.add_argument('--waves', type=int, default=20)
    ap.add_argument('--step', type=int, default=1000); ap.add_argument('--max-ticks', type=int, default=50000)
    ap.add_argument('--freq', type=int, default=50); ap.add_argument('--qty', type=int, default=100)
    ap.add_argument('--name', default=dt.datetime.now().strftime('%Y%m%d-%H%M%S'))
    o = ap.parse_args()
    out = ROOT / 'data' / 'cave-arrive' / o.name
    out.mkdir(parents=True, exist_ok=True)
    W = open(out / 'waves.tsv', 'w')
    W.write('subject\ttick\trace\tn\trx\try\tdepth\n')
    log = open(out / 'setup.txt', 'w')
    res = []
    for subj in o.subjects:
        for attempt in (1, 2):
            try:
                res.append(one(o, subj, W, log)); break
            except Hung as e:
                print(f'  {subj}: DF hung ({e}); attempt {attempt}', flush=True)
                log.write(f'HUNG {subj} attempt {attempt}: {e}\n'); log.flush()
                if attempt == 2:
                    res.append({'subj': subj, 'n_subj': None, 'n_ctrl': None, 'ticks': 0, 'other': {}, 'setup': 'hung twice'})
        r = res[-1]
        print(f"  {subj}: {r['n_subj']} v {o.control} {r['n_ctrl']} in {r['ticks']} ticks; other {r['other']}", flush=True)
    sh('stop', timeout=120)
    with open(out / 'summary.md', 'w') as f:
        f.write(f'# never-arrive {o.name}: {o.fort}, cavern {o.depth}, control {o.control}, FREQUENCY {o.freq}, quantity {o.qty}\n\n'
                '| subject | subject waves | control waves | share | p (v 0.5) | ticks | other waves |\n|---|---|---|---|---|---|---|\n')
        for r in res:
            if r['n_subj'] is None:
                f.write(f"| {r['subj']} | - | - | - | - | - | hung twice |\n"); continue
            n = r['n_subj'] + r['n_ctrl']
            f.write(f"| {r['subj']} | {r['n_subj']} | {r['n_ctrl']} | {r['n_subj'] / n if n else 0:.2f} | {binom_p(r['n_subj'], n):.3g} | "
                    f"{r['ticks']} | {r['other'] or ''} |\n")
        f.write('\nSetup lines:\n' + ''.join(f"- {r['subj']}: {r['setup']}\n" for r in res))
    print((out / 'summary.md').read_text())


if __name__ == '__main__':
    main()
