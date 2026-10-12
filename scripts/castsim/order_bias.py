#!/usr/bin/env python3
"""castsim.order_bias: does the cast build order favour a season? For every species eligible on a layer in all four seasons,
the share of its cast appearances that fall in each season, over many simulated years (site seeds) on the six embarks,
built Spring-first and in a random order. -> data/castsim/order_bias.json"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from design import Design  # noqa: E402
from design_run import examples, wiring  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/castsim/order_bias.json'
SEASONS = ['Spring', 'Summer', 'Autumn', 'Winter']
YEARS = int(sys.argv[1]) if len(sys.argv) > 1 else 40


def main():
    w = wiring()
    out = {}
    t0 = time.time()
    for order in ('season', 'random'):
        D = Design(wiring=w, order=order)
        exs = examples(D.R)
        per = {}          # (embark, layer, species) -> appearances by season
        pack = set()
        for ex in exs:
            for site in range(1, YEARS + 1):
                r = D.run(ex['spec'], site=site)
                for L in r['active']:
                    allyear = None
                    for s in range(4):
                        ts = {c['e']['token'] for c in r['lists'][(L, s)] if not c['vermin'] and 'placed plant' not in c['slots']}
                        allyear = ts if allyear is None else allyear & ts
                    for s in range(4):
                        for t, sl in r['casts'][(L, s)]['members']:
                            if t not in allyear or sl == 'apex': continue      # the apex draw is its own; slots only
                            k = (ex['id'], L, t)
                            per.setdefault(k, [0, 0, 0, 0])[s] += 1
                            e = r['pool'][t]
                            if D.predator(e) and not e['benign'] and e['cmax'] > 1: pack.add(k)
        def share(keys):
            tot = [0, 0, 0, 0]
            for k in keys:
                for s in range(4): tot[s] += per[k][s]
            n = sum(tot) or 1
            return [round(100 * x / n, 1) for x in tot], sum(tot)
        common = [k for k, v in per.items() if sum(v) >= 10]
        conc = round(sum(max(per[k]) / sum(per[k]) for k in common) / len(common) * 100, 1) if common else 0
        skew = sorted(common, key=lambda k: -(per[k][0] / sum(per[k])))[:12]
        out[order] = {'all': share(per), 'pack': share([k for k in per if k in pack]), 'concentration': conc, 'n_species': len(common),
                      'top_spring': [{'embark': k[0], 'layer': k[1], 't': k[2], 'by_season': per[k]} for k in skew]}
        print(order, 'all', out[order]['all'], 'pack', out[order]['pack'], 'mean top-season share', conc, f'{time.time() - t0:.0f}s')
        for k in skew[:5]: print('   ', k, per[k])
    out['years'] = YEARS; out['embarks'] = 6
    OUT.write_text(json.dumps(out))


if __name__ == '__main__':
    main()
