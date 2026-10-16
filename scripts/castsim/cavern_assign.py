"""castsim.cavern_assign: the user's cavern layer picks (16 Oct 2026, Cavern Layer Picks tool) run through the desk cast builder.

The user's goals: more diversity, the weirdest in cavern 3 only, most sentients (all the civ-like ones) in caverns 2-3, the mundane
in all three, cavern 1 less hostile; and (the ask) every cavern-season with at least a minimally complete food web, species allowed
in more than one season where that is what it takes.

Minimal food web of a cavern-season, counting only species DF will actually send (the NA1 thief-tagged six never come):
  prey      at least one non-predator animal member (ground prey, a benign flier or swimmer)
  predator  at least one predator member (apex or meso slot) with a food-web edge to a member or a cast vermin
  vermin    at least two vermin, at least one of them eaten by a member
Arms: the picks as entered; the picks with the review's changes; each with and without the web guarantee (after a cast is built, a
missing prey or predator is filled from the cavern's candidates ignoring the x0.01 repeat weight, so the same species may serve
several seasons). Usage: python3 cavern_assign.py PICKS.json [--sites 30]   (writes data/castsim/cavern_assign.json)"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from design import Design  # noqa: E402

ROOT = HERE.parent.parent
OUT = ROOT / 'data/castsim/cavern_assign.json'
THIEF = {'DRUNIAN', 'GREMLIN', 'MOLE_DOG_NAKED', 'MOLE_GIANT', 'RAT_GIANT', 'RAT_LARGE'}   # NA1: never drawn for a cavern wave
DEAD = {1: set(), 2: set(), 3: set()}   # per cavern: species that will not arrive there (out-of-range picks, when that arm says so)
SPEC = {'land': [{'biome': 'FOREST_TEMPERATE_BROADLEAF', 'sav': 50, 'evil': 50, 'src': 'given'}], 'water': {},
        'caverns': [1, 2, 3], 'extinct': 'WILDERNESS'}
SEASONS = ('Spring', 'Summer', 'Autumn', 'Winter')


class Assigned(Design):
    """Design with the cavern layers taken from an assignment {token: [caverns]} (default: the raw depth range)"""
    def __init__(self, assign, drop=(), guarantee=False, **kw):
        super().__init__(**kw)
        self.assign, self.drop, self.guarantee = assign, set(drop), guarantee
        self.k = None

    def layers_of(self, e, spec, fbs):
        out, notes = super().layers_of(e, spec, fbs)
        t = e['token']
        if not any(L.startswith('cavern') for L in out) and t not in self.assign:
            return out, notes
        out = [L for L in out if not L.startswith('cavern')]
        if t in self.drop:
            return out, notes
        cav = self.assign.get(t)
        if cav is None:
            lo, hi = e['depthLo'], e['depthHi']
            cav = [k for k in (1, 2, 3) if not lo or not hi or lo <= k <= hi]
        out += [f'cavern{k}' for k in sorted(cav)]
        return out, notes

    def cast(self, lst, layer, sub, season, used, rng, drawn=None):
        tr = super().cast(lst, layer, sub, season, used, rng, drawn)
        if self.guarantee and layer.startswith('cavern'):
            self.k = int(layer[-1])
            self.ensure_web(tr, lst, layer, rng)
        return tr

    def ensure_web(self, tr, lst, layer, rng):
        """fill a missing prey or predator from the list, ignoring the repeat weight (the species may then serve several seasons)"""
        have = {t for t, _ in tr['members']}
        k = int(layer[-1])
        ok = lambda c: c['e']['token'] not in THIEF and c['e']['token'] not in DEAD[k] and c['e']['token'] not in have  # noqa: E731
        st = web_state(tr, k)
        tr.setdefault('guarantee', [])
        if not st['prey']:
            c = [x for x in lst if not x['vermin'] and ok(x) and not self.predator(x['e']) and set(x['slots']) & {'ground prey', 'flier', 'swimmer'}]
            if c:
                pick = rng.choice(c)
                slot = next((s for s in pick['slots'] if s in ('ground prey', 'flier', 'swimmer')), pick['slots'][0])
                tr['members'].append((pick['e']['token'], slot)); have.add(pick['e']['token']); tr['guarantee'].append(('prey', pick['e']['token']))
        st = web_state(tr, k)
        if not st['pred']:
            c = [x for x in lst if not x['vermin'] and ok(x) and self.predator(x['e'])]
            if c:
                pick = max(c, key=lambda x: (x['e']['mass'], x['e']['token']))   # the largest predator in season: the old apex fallback
                tr['members'].append((pick['e']['token'], 'meso')); tr['guarantee'].append(('predator', pick['e']['token']))


PRED = {}


def web_state(tr, k):
    """prey / predator / vermin of a cast, counting arriving species only; edges recomputed by habitat and tier (Design.eats)"""
    mem = [(t, s) for t, s in tr['members'] if t not in THIEF and t not in DEAD[k]]
    prey = [t for t, s in mem if s in ('ground prey',) or (s in ('flier', 'swimmer') and not PRED.get(t))]
    preds = [t for t, s in mem if s in ('apex', 'meso') or (s in ('flier', 'swimmer') and PRED.get(t))]
    return {'prey': prey, 'pred': preds, 'verm': list(tr.get('vermin') or [])}


def run_arm(name, assign, drop, guarantee, sites, D0, oor_dead=False):
    for k in DEAD: DEAD[k] = set()
    if oor_dead:
        for t, cav in assign.items():
            e = D0.E.classify(t)
            lo, hi = e['depthLo'], e['depthHi']
            for k in cav:
                if lo and hi and not lo <= k <= hi: DEAD[k].add(t)
    per = collections.defaultdict(lambda: collections.Counter())
    distinct = collections.defaultdict(list)
    members = collections.defaultdict(collections.Counter)
    for site in range(1, sites + 1):
        D = Assigned(assign, drop=drop, guarantee=guarantee, wiring=D0.wiring)
        r = D.run(SPEC, year=250, site=site)
        for k in (1, 2, 3):
            L = f'cavern{k}'
            seen = set()
            for s in range(4):
                tr = r['casts'].get((L, s))
                if not tr:
                    continue
                for t, sl in tr['members']:
                    PRED.setdefault(t, D.predator(r['pool'][t]))
                st = web_state(tr, k)
                c = per[(k, s)]
                c['n'] += 1
                c['prey'] += bool(st['prey']); c['pred'] += bool(st['pred']); c['verm2'] += len(st['verm']) >= 2
                c['web'] += bool(st['prey'] and st['pred'] and len(st['verm']) >= 2)
                c['thief'] += sum(1 for t, _ in tr['members'] if t in THIEF or t in DEAD[k])
                c['size'] += sum(1 for t, _ in tr['members'] if t not in THIEF and t not in DEAD[k])
                c['lp'] += sum(1 for t, _ in tr['members'] if r['pool'][t]['largePred'])
                c['guar'] += len(tr.get('guarantee', []))
                for t, _ in tr['members']:
                    seen.add(t); members[k][t] += 1
            distinct[k].append(len(seen - THIEF - DEAD[k]))
    out = {'arm': name, 'cells': {}, 'distinct': {k: round(sum(v) / len(v), 1) for k, v in distinct.items()},
           'members': {k: dict(v.most_common()) for k, v in members.items()}}
    for (k, s), c in sorted(per.items()):
        n = c['n']
        out['cells'][f'{k}|{SEASONS[s]}'] = {x: round(c[x] / n, 2) for x in ('prey', 'pred', 'verm2', 'web', 'thief', 'size', 'lp', 'guar')}
    return out


def main():
    picks = {k.replace('_', ' ') if k == 'RODENT_MAN' else k: v for k, v in json.loads(Path(sys.argv[1]).read_text()).items()}
    sites = int(sys.argv[sys.argv.index('--sites') + 1]) if '--sites' in sys.argv else 30
    review = json.loads(Path(sys.argv[2]).read_text()) if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else None
    D0 = Design()
    arms = [('raw depth (today)', {}, (), False), ('your picks', picks, (), False)]
    if review:
        rv = dict(picks); rv.update(review['assign'])
        arms += [('review', rv, review.get('drop', ()), False), ('review + web guarantee', rv, review.get('drop', ()), True)]
    arms6 = [('your picks, out-of-range never drawn', picks, (), False, True)]
    if review:
        arms6 += [('review, out-of-range never drawn', rv, review.get('drop', ()), False, True),
                  ('review + guarantee, out-of-range never drawn', rv, review.get('drop', ()), True, True)]
    res = [run_arm(n, a, d, g, sites, D0) for n, a, d, g in arms] + [run_arm(n, a, d, g, sites, D0, o) for n, a, d, g, o in arms6]
    OUT.write_text(json.dumps(res, indent=1))
    for a in res:
        print(f"\n== {a['arm']}  distinct arriving species per cavern-year: {a['distinct']}")
        for key, c in a['cells'].items():
            print(f"  cavern {key:10} web {c['web']:.2f}  prey {c['prey']:.2f} pred {c['pred']:.2f} verm2 {c['verm2']:.2f}  "
                  f"arriving members {c['size']:.1f} dead slots {c['thief']:.2f}  LARGE_PREDATOR {c['lp']:.1f}  guaranteed {c['guar']:.2f}")


if __name__ == '__main__':
    main()
