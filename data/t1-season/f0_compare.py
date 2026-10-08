#!/usr/bin/env python3
"""Cavern rest-frequency test: f0_compare.py A_DIR B_DIR ...  (pairs: arm A = cast restfreq 1, arm B = restfreq 0)
Per season, on the cavern layer: arrivals (recorder units; births count), ledger groups by cast/off, the species that
arrived, the cavern gate's sendoffs; and per run the frame rate and the step times (a freeze shows as a stalled step)."""
import collections, re, statistics, sys
from v73_check import summarize, ledger, read, SEASONS, TPY, ST

ORDER = {s: i for i, s in enumerate(SEASONS)}


def cavern(d):
    S = summarize(d)
    ev = [r for r in read(d + '/events.tsv') if r['event'] == 'ARRIVE' and r.get('tlayer') == 'cavern']
    species = collections.defaultdict(collections.Counter)
    for r in ev:
        species[SEASONS[(int(r['tick']) % TPY) // ST]][r['race']] += 1
    led, _ = ledger(d)
    gate = collections.Counter(s for s, k, L, t in led if k == 'dismiss' and L == 'cavern' and 'over its cap' in t)
    smp = read(d + '/samples.tsv')
    fps = [float(r['fps']) for r in smp if r.get('fps') not in (None, '', '0')]
    steps = []
    for l in open(d + '/run.log'):
        m = re.search(r'stepped (\d+) ticks .* in (\d+)s', l)
        if m and int(m.group(1)) >= 5000:
            steps.append(int(m.group(2)) * 10000 / int(m.group(1)))
    return S, species, gate, fps, steps


def main():
    dirs = sys.argv[1:]
    for d in dirs:
        S, species, gate, fps, steps = cavern(d)
        print('## %s' % d)
        print('| season | cavern units (in cast / off) | ledger groups (cast / off) | species arriving | gate sendoffs |')
        print('|---|---|---|---|---|')
        for s in sorted({k[1] for k in S['arr'] if k[0] == 'cavern'} | set(species), key=ORDER.get):
            ok, off = S['arr'][('cavern', s, True)], S['arr'][('cavern', s, False)] + S['arr'][('cavern', s, 'stand-in')]
            g_ok = sum(v for k, v in S['src'].items() if k[0] == 'cavern' and k[1] == s and k[3] == 'cast')
            g_off = sum(v for k, v in S['src'].items() if k[0] == 'cavern' and k[1] == s and k[3] != 'cast')
            sp = ', '.join('%s %d' % kv for kv in species[s].most_common(8))
            print('| %s | %d / %d | %d / %d | %s | %d |' % (s, ok, off, g_ok, g_off, sp, gate[s]))
        print('fps median %.0f (lowest %.0f); s per 10k ticks: median %.0f, worst %.0f; %d steps' % (
            statistics.median(fps) if fps else 0, min(fps) if fps else 0,
            statistics.median(steps) if steps else 0, max(steps) if steps else 0, len(steps)))
        print()


if __name__ == '__main__':
    main()
