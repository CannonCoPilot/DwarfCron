"""castsim.compare_arms: one season-run's arms side by side on the land layer (user 15 Oct: test one entry per species).

Per arm: land waves by the cast that holds the species (walkers, fliers, the water casts' birds) and the cap's pauses; how
many ground and flying cast species got a wave in their season; the mean dominance of those layer-seasons; and the odds fit:
inside each ground or flying cast, each species' share of the season's waves against its share of the cast's FREQUENCY
(mid-season raws), as a mean absolute gap. With one entry per species the waves should follow FREQUENCY alone.
Usage: python3 compare_arms.py data/season-run/RUN [ARM ...]"""
from __future__ import annotations

import collections
import glob
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ecology as E  # noqa: E402


def arm_stats(cell: Path, known: set) -> dict:
    C = E.casts(cell, known)
    where = E._where(C)
    waves = collections.defaultdict(collections.Counter)   # (layer, season) -> species -> waves
    src, caps = collections.Counter(), 0
    for line in (cell / 'ledger.tsv').read_text(encoding='cp437').splitlines()[1:]:
        x = line.split('\t')
        if len(x) < 4 or not x[0].isdigit() or x[2] != 'land':
            continue
        s = E.season_of(int(x[0]))
        if 'at its cap' in x[3]:
            caps += 1
        m = re.match(r'detached (.+?) x\d+', x[3])
        if m:
            L = where[s].get(m.group(1), 'other')
            k = 'walkers' if L == 'ground' else 'fliers' if L == 'flying' else 'water birds' if L in ('ocean', 'fresh') else 'other'
            src[k] += 1
            if L in ('ground', 'flying'):
                waves[(L, s)][m.group(1)] += 1
    snaps = collections.defaultdict(list)
    for f in sorted(glob.glob(str(cell / 'states' / '*.json'))):
        snaps[E.season_of(int(Path(f).stem))].append(f)
    cov = collections.Counter()
    gaps, doms = [], []
    for (L, s), v in C.items():
        if L not in ('ground', 'flying') or not snaps[s]:
            continue
        w = waves[(L, s)]
        n = sum(w[t] for t in v['cast'])
        cov[L + ' cast'] += len(v['cast'])
        cov[L + ' got'] += sum(1 for t in v['cast'] if w[t])
        if n >= 3:
            raws = json.loads(Path(snaps[s][len(snaps[s]) // 2]).read_text())['raws']
            fr = {t: max(1, (raws.get(t) or [1])[0]) for t in v['cast']}
            tot = sum(fr.values())
            gaps.append(sum(abs(w[t] / n - fr[t] / tot) for t in v['cast']) / len(v['cast']))
            doms.append(max(w[t] for t in v['cast']) / n)
    return {'src': dict(src), 'caps': caps, 'cov': dict(cov), 'gap': sum(gaps) / len(gaps) if gaps else None,
            'dom': sum(doms) / len(doms) if doms else None, 'nlayer': len(gaps)}


def main():
    run = Path(sys.argv[1])
    arms = sys.argv[2:] or sorted(p.name for p in run.iterdir() if (p / 'rep1' / 'ledger.tsv').exists())
    from design import Design
    known = set(Design().R.src)
    print(f"{'arm':4} {'walkers':>7} {'fliers':>6} {'water b.':>8} {'caps':>5}  {'ground cast got':>16} {'flying cast got':>16}  {'dominance':>9}  {'odds gap':>8}")
    for a in arms:
        st = arm_stats(run / a / 'rep1', known)
        s, c = st['src'], st['cov']
        print(f"{a:4} {s.get('walkers', 0):7} {s.get('fliers', 0):6} {s.get('water birds', 0):8} {st['caps']:5}  "
              f"{c.get('ground got', 0):>7} of {c.get('ground cast', 0):<6} {c.get('flying got', 0):>7} of {c.get('flying cast', 0):<6}  "
              f"{(st['dom'] or 0):9.2f}  {(st['gap'] or 0):8.3f}")


if __name__ == '__main__':
    main()
