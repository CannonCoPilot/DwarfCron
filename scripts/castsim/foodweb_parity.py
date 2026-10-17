"""castsim.foodweb_parity: foodweb_sim.js (the Food Web Explorer's simulator) against the desk (design.Design) on the same forts.
Exact: the pool, each species' layers, each season list's slots. Statistical: how often each species is cast per layer over
N years (the two use different random generators, so per-species rates are compared, not casts). The desk predates three
engine changes the JS follows (CAVE.ASSIGN, the cavern web guarantee, ROSTER.FP.codeFor in the vermin diet): parity runs with
the first two off, and vermin are left out of the rate comparison. Usage: python3 foodweb_parity.py [--years 300]"""
from __future__ import annotations

import collections
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from design import Design, LAYERS  # noqa: E402
from design_run import wiring  # noqa: E402

ROOT = HERE.parent.parent
DATA = ROOT / 'data/castsim/foodweb/creatures.json'
FORTS = [
    ('temperate forest lake, calm neutral', ['FOREST_TEMPERATE_BROADLEAF', 'GRASSLAND_TEMPERATE'], 30, 50, {'lake': 'TEMPERATE'}, 'UNTAMED_WILDS'),
    ('savage tropical coast', ['SHRUBLAND_TROPICAL', 'SWAMP_MANGROVE'], 80, 50, {'ocean': 'TROPICAL', 'river': 'TROPICAL'}, 'UNTAMED_WILDS'),
    ('evil tundra pools', ['TUNDRA', 'FOREST_TAIGA'], 50, 90, {'pool': 'TEMPERATE'}, 'WILDERNESS'),
    ('good savage arctic coast', ['GLACIER', 'TUNDRA'], 80, 10, {'ocean': 'ARCTIC'}, 'WILDERNESS'),
]
JS = r"""
const S = require(process.argv[2]); const D = require(process.argv[3]); const job = require(process.argv[4]);
const sim = S.make(D); const out = [];
for (const f of job.forts) {
  const B = sim.build(f.spec);
  const lists = {}; for (const k in B.lists) lists[k] = B.lists[k].map(x => [x.c.t, x.vermin ? ['vermin'] : x.slots]);
  const layers = {}; for (const t in B.P) layers[t] = B.P[t].layers;
  const st = sim.years(B, f.spec, Object.assign({}, sim.P0, {seed: true, weird: true, guarantee: false, deskHv: job.deskHv}), job.years, 1);
  out.push({pool: Object.keys(B.P).sort(), layers, lists, active: B.active, st});
}
console.log(JSON.stringify(out));
"""


def desk_spec(land, sav, evil, water, ext):
    w = {}
    for k, z in water.items():
        nm = f'OCEAN_{z}' if k == 'ocean' else f'{k.upper()}_{z}_FRESHWATER'
        w[k] = [{'biome': nm, 'sav': sav, 'evil': evil}]
    return {'land': [{'biome': b, 'sav': sav, 'evil': evil} for b in land], 'water': w, 'caverns': [1, 2, 3], 'extinct': ext}


def js_spec(land, sav, evil, water, ext):
    w = {k: None for k in ('ocean', 'lake', 'river', 'pool')}
    w.update(water); w['brook'] = False
    return {'land': land, 'rtype': {'sav': sav, 'evil': evil, 'iso': False}, 'extinct': ext, 'water': w, 'caverns': [1, 2, 3],
            'assign': False}


def main():
    years = int(sys.argv[sys.argv.index('--years') + 1]) if '--years' in sys.argv else 300
    D = Design(wiring=wiring())
    job = {'deskHv': '--engine-hv' not in sys.argv, 'years': years, 'forts': [{'spec': js_spec(*f[1:])} for f in FORTS]}
    with tempfile.TemporaryDirectory() as td:
        jf, sf = Path(td) / 'job.json', Path(td) / 'run.js'
        jf.write_text(json.dumps(job)); sf.write_text(JS)
        res = json.loads(subprocess.run(['node', str(sf), str(HERE / 'foodweb_sim.js'), str(DATA), str(jf)],
                                        capture_output=True, text=True, check=True).stdout)
    bad = 0
    for (name, *args), J in zip(FORTS, res):
        spec = desk_spec(*args)
        r = D.run(spec)
        PL = {'SPONGE', 'GIANT_SPONGE'}   # placed plants: the engine gives them no layer (FP.layersOf), the desk a 'placed plant' slot
        verm = {t for t, e in r['pool'].items() if e['gameVermin']}
        dp = sorted(r['pool'])
        ok_pool = dp == J['pool']
        lay_bad = [t for t in dp if t not in PL and t in J['layers'] and sorted(r['pool'][t]['layers']) != sorted(J['layers'][t])]
        list_bad = []
        for (L, s), lst in r['lists'].items():
            d = sorted((c['e']['token'], tuple(c['slots'])) for c in lst if c['e']['token'] not in PL)
            j = sorted((t, tuple(sl)) for t, sl in J['lists'].get(f'{L}|{s}', []))
            if d != j: list_bad.append(f'{L}|{s}')
        # rates: share of a layer's season casts holding the species (non-vermin)
        inc = collections.defaultdict(collections.Counter); ncast = collections.Counter()
        for y in range(years):
            rr = D.run(spec, year=250 + y, site=1)
            for (L, s), tr in rr['casts'].items():
                ncast[L] += 1
                for t, _ in tr['members']: inc[L][t] += 1
        worst = []
        for L in r['active']:
            jd = J['st'].get(L)
            if not jd: worst.append((L, 'missing in JS', 1)); continue
            toks = set(inc[L]) | set(jd['seasons'])
            diffs = []
            for t in toks:
                if t in verm: continue
                a = inc[L][t] / ncast[L]; b = jd['seasons'].get(t, 0) / jd['casts']
                diffs.append((abs(a - b), t, round(a, 3), round(b, 3)))
            diffs.sort(reverse=True)
            worst.append((L, diffs[0] if diffs else None))
        print(f'== {name}: pool {len(dp)} {"OK" if ok_pool else "DIFF " + str(set(dp) ^ set(J["pool"]))}; '
              f'layers {"OK" if not lay_bad else lay_bad[:5]}; lists {"OK" if not list_bad else list_bad[:6]}; active {r["active"] == J["active"]}')
        for L, w in worst: print(f'   {L:8} worst rate gap {w}')
        bad += (not ok_pool) + bool(lay_bad) + bool(list_bad)
    print('EXACT CHECKS', 'PASS' if not bad else f'FAIL ({bad})')


if __name__ == '__main__':
    main()
