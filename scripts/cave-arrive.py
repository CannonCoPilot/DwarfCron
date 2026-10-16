#!/usr/bin/env python3
"""The never-arrive test (user 15 Oct 2026): can DF send a cavern wave of these species at all?

15 cast cavern species never arrived in 16 full-year forts (the cave animal people, the gremlin, the plain prey). For each
SUBJECT: load FORT fresh (DF restarted first), the tool disabled, then `cx-cavearrive setup` puts SUBJECT and CONTROL on the
same footing in one cavern (one open entry each on every draw tile x cave of that depth, same quantity and FREQUENCY,
every other Animal entry there closed). Waves are collected as they land and every wild cavern animal vanished so the
gate stays clear. Equal footing gives the subject about half the waves; a bar gives it none.

    cave-arrive.py FORT CONTROL SUBJ[@DEPTH] [SUBJ ...] [--depth 1] [--waves 20] [--step 1000] [--max-ticks 50000] [--name RUN]
Writes data/cave-arrive/RUN/: waves.tsv (subject, tick, race, n, rx, ry, depth), qty.tsv (the pair's stock after each step: DF debits a
wave's planned size, so a debit with no unit is a drawn wave that could not be placed), setup.txt, summary.md.
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


def one(o, spec, W, Q, log):
    subj, _, d = spec.partition('@')
    depth = int(d) if d else o.depth
    print(f'{subj}: restart DF, load {o.fort} (cavern {depth})', flush=True)
    sh('restart', timeout=300)
    r = sh('load', o.fort, timeout=900)
    if 'loaded after' not in r:
        raise SystemExit(f'load failed: {r[-400:]}')
    log.write(f'== {subj} v {o.control}, cavern {depth}\n')
    log.write(sh('cmd', 'seasonal-wildlife', 'disable'))
    s = sh('cmd', 'cx-cavearrive', 'setup', str(depth), subj, o.control, str(o.freq), str(o.qty))
    log.write(s); log.write(sh('cmd', 'cx-cavearrive', 'state', str(depth))); log.flush()
    line = next((x for x in s.splitlines() if x.startswith('SETUP')), '')
    print('  ' + (line or s[-300:]), flush=True)
    for x in s.splitlines():
        if x.startswith('WARN') or x.startswith('RAW'):
            print('  ' + x, flush=True)
    if not line:
        raise SystemExit('setup failed')
    q0 = qty(sh('cmd', 'cx-cavearrive', 'collect'))
    got, other, ticks = {subj: 0, o.control: 0}, {}, 0
    debit, last = [0, 0], q0
    while sum(got.values()) < o.waves and ticks < o.max_ticks:
        sh('step', str(o.step), timeout=180)
        ticks += o.step
        out = sh('cmd', 'cx-cavearrive', 'collect', timeout=120)
        q = qty(out)
        if q and last:
            for i in (0, 1):
                debit[i] += max(0, last[i] - q[i])
            Q.write(f'{subj}\t{ticks}\t{q[0]}\t{q[1]}\n')
        last = q or last
        for x in out.splitlines():
            if not x.startswith('WAVE '):
                continue
            _, tick, race, n, rx, ry, d = x.split()
            W.write(f'{subj}\t{tick}\t{race}\t{n}\t{rx}\t{ry}\t{d}\n')
            if race in got and d == str(depth):
                got[race] += 1
            else:
                other[f'{race}@{d}'] = other.get(f'{race}@{d}', 0) + 1
        W.flush()
    sh('title')
    raws = [x for x in s.splitlines() if x.startswith(('RAW', 'WARN'))]
    return {'subj': subj, 'depth': depth, 'n_subj': got[subj], 'n_ctrl': got[o.control], 'ticks': ticks, 'other': other, 'setup': line,
            'debit': debit, 'q0': q0, 'raws': raws}


def qty(out):
    for x in out.splitlines():
        if x.startswith('QTY '):
            a, b = x.split()[1:3]
            return [int(a), int(b)]
    return None


def verdict(r):
    if r['n_subj'] is None:
        return 'not tested (DF hung twice)'
    if not r['n_ctrl']:
        return 'void: the control did not arrive either'
    if r['n_subj']:
        return 'arrives on equal footing (no bar: absence was odds)'
    if r['n_ctrl'] < 8:
        return f"inconclusive (the control came only {r['n_ctrl']} times)"
    if r['debit'][0]:
        return f"drawn but never placed (stock debited {r['debit'][0]}, no unit)"
    return 'never drawn (a bar: no stock debited, no unit)'


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
    Q = open(out / 'qty.tsv', 'w')
    Q.write('subject\tticks\tsubject_qty\tcontrol_qty\n')
    log = open(out / 'setup.txt', 'w')
    res = []
    for subj in o.subjects:
        for attempt in (1, 2):
            try:
                res.append(one(o, subj, W, Q, log)); break
            except Hung as e:
                print(f'  {subj}: DF hung ({e}); attempt {attempt}', flush=True)
                log.write(f'HUNG {subj} attempt {attempt}: {e}\n'); log.flush()
                if attempt == 2:
                    res.append({'subj': subj, 'depth': None, 'n_subj': None, 'n_ctrl': None, 'ticks': 0, 'other': {}, 'setup': 'hung twice',
                                'debit': [0, 0], 'q0': None, 'raws': []})
        r = res[-1]
        print(f"  {r['subj']}: {r['n_subj']} v {o.control} {r['n_ctrl']} in {r['ticks']} ticks; debits {r['debit']}; {verdict(r)}; other {r['other']}", flush=True)
    sh('stop', timeout=120)
    with open(out / 'summary.md', 'w') as f:
        f.write(f'# never-arrive {o.name}: {o.fort}, control {o.control}, FREQUENCY {o.freq}, quantity {o.qty}\n\n'
                '| subject | cavern | subject waves | control waves | share | p (v 0.5) | stock debited (subject / control) | ticks | verdict | other waves |\n'
                '|---|---|---|---|---|---|---|---|---|---|\n')
        for r in res:
            if r['n_subj'] is None:
                f.write(f"| {r['subj']} | - | - | - | - | - | - | - | {verdict(r)} | |\n"); continue
            n = r['n_subj'] + r['n_ctrl']
            f.write(f"| {r['subj']} | {r['depth']} | {r['n_subj']} | {r['n_ctrl']} | {r['n_subj'] / n if n else 0:.2f} | {binom_p(r['n_subj'], n):.3g} | "
                    f"{r['debit'][0]} / {r['debit'][1]} | {r['ticks']} | {verdict(r)} | {r['other'] or ''} |\n")
        f.write('\nSetup and raws:\n' + ''.join(f"- {r['subj']}: {r['setup']}\n" + ''.join(f"  - {x}\n" for x in r['raws']) for r in res))
    print((out / 'summary.md').read_text())


if __name__ == '__main__':
    main()
