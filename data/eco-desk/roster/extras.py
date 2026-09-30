#!/usr/bin/env python3
"""Rule-level facts that do not need the roster runs -> extras.md"""
from analyze import *   # noqa
from run import CONFIGS

B = CONFIGS['baseline']; FX_ = CONFIGS['FIX3']
out = []; P = out.append
CLASSIC = ['WOLF', 'COYOTE', 'FOX', 'DINGO', 'HYENA', 'COUGAR', 'LION', 'TIGER', 'LEOPARD', 'JAGUAR', 'CHEETAH', 'BEAR_BLACK',
           'BEAR_GRIZZLY', 'BEAR_POLAR', 'CROCODILE_SALTWATER', 'ALLIGATOR', 'ANACONDA', 'SHARK_GREAT_WHITE', 'SHARK_BLUE', 'ORCA',
           'BIRD_EAGLE', 'BIRD_OWL_GREAT_HORNED', 'BLIND_CAVE_BEAR', 'CROCODILE_CAVE', 'JABBERER', 'GIANT_WOLF' if 'GIANT_WOLF' in SPECIES else 'WOLF_MAN']
NAT = [s for s in SPECIES.values()]
def can_eat(p, cfg):
    units = [x for x in NAT if not x.vermin and eats(p, x, cfg)]
    return len(units), sum(1 for x in NAT if x.vermin and eats(p, x, cfg)), sum(1 for x in units if x.sentient)
rows = []
for k in CLASSIC:
    if k not in SPECIES: continue
    s = SPECIES[k]
    ub, vb, sb = can_eat(s, B); uf, vf, sf = can_eat(s, FX_)
    rows.append([k, s.mass, s.band, 'LP' if s.lp else '', 'BENIGN' if s.benign else '', s.cmax, tclass(s, B), '%d / %d / %d' % (ub, vb, sb),
                 'yes' if eats(s, SPECIES['DEER'], B) else 'no', tclass(s, FX_), '%d / %d / %d' % (uf, vf, sf), 'yes' if eats(s, SPECIES['DEER'], FX_) else 'no'])
P('## Where the tool size bands put the classic predators (whole natural species set, ignoring layer/biome)\n')
P(md(['species', 'cm3', 'tool band', 'LP', 'BENIGN', 'cluster max', 'class (baseline)', 'may eat units / vermin / sentients (baseline)',
      'eats DEER? (baseline)', 'class (FIX3)', 'units / vermin / sentients (FIX3)', 'eats DEER? (FIX3)'], rows)); P('')

# size-band census of predators
c = Counter((s.band, s.lp, s.benign) for s in NAT if not s.vermin and s.role == 'predator' and s.kind == '' and not s.sentient)
P('## Natural non-giant, non-sentient predators by tool band x LP x BENIGN\n')
P(md(['band', 'LP', 'BENIGN', 'n'], [[b, lp, bn, n] for (b, lp, bn), n in sorted(c.items())])); P('')
big = sorted(s.id for s in NAT if not s.vermin and s.role == 'predator' and s.band == 'large' and s.kind == '')
P('Rule D eaters, baseline (LP and >=1M cm3, plus giant predators): non-giant = %s\n' % ', '.join(sorted(s.id for s in NAT if d_large(s, B))))
P('Large-band (>=1M) natural predators, any tag: %s\n' % ', '.join(big))

# absurd allowed pairs (eater much smaller than prey), baseline, both units
ab = []
for p in NAT:
    if p.vermin or tclass(p, B) not in PRED_CLASSES: continue
    for x in NAT:
        if x.vermin or not x.mass or not p.mass: continue
        if eats(p, x, B) and x.mass >= 3 * p.mass: ab.append((x.mass / p.mass, p.id, x.id))
ab.sort(reverse=True)
def absurd(cfg):
    n = 0
    for p in NAT:
        if p.vermin or tclass(p, cfg) not in PRED_CLASSES: continue
        for x in NAT:
            if not x.vermin and x.mass and p.mass and x.mass >= 3 * p.mass and eats(p, x, cfg): n += 1
    return n
P('Allowed unit pairs with prey >=3x eater mass, by config: ' + ', '.join('%s %d' % (lb, absurd(CONFIGS[lb])) for lb in ('baseline', 'cls_lp+1', 'FIX', 'FIX_ratio', 'FIX3', 'FIX3_ratio')) + '\n')
P('## Allowed (baseline) unit pairs where the prey is >=3x the eater: %d pairs; examples (ratio, eater, prey)\n' % len(ab))
P('\nNon-giant, non-AP examples only: ' + ', '.join('%s>%s (%.0fx)' % (a, b, r) for r, a, b in [t for t in ab if SPECIES[t[1]].kind == '' and SPECIES[t[2]].kind == '' and not SPECIES[t[1]].sentient][:15]))
P('')

# pools: AP / giant share of non-vermin LR
rows = []
for b in EMBARKS:
    for L in ('land', 'flying'):
        Pl = [s for s in pool(b, L, 'SPRING', B) if not s.vermin]
        rows.append([b, L, len(Pl), pct(sum(1 for s in Pl if s.kind == 'animal_person'), len(Pl)), pct(sum(1 for s in Pl if s.kind == 'giant'), len(Pl)),
                     pct(sum(1 for s in Pl if s.hv), len(Pl)), pct(sum(1 for s in Pl if s.hv and s.kind == 'giant'), sum(1 for s in Pl if s.hv))])
P('## Non-vermin pool make-up (spring)\n')
P(md(['embark', 'layer', 'non-vermin pool', 'animal people', 'giants', 'high-value', 'giants among high-value'], rows)); P('')

# sentients with no allowed eater in their pool (structural D)
rows = []
for lb in ('baseline', 'D_tag', 'FIX', 'FIX3', 'FIX3_ratio'):
    cfg = CONFIGS[lb]; tot = nob = 0; ex = Counter()
    for b in list(EMBARKS) + ['UNDER']:
        for L in (SURFACE_LAYERS if b != 'UNDER' else UNDER_LAYERS):
            Pl, prey_of, eaters_of = relations(b, L, 'SPRING', cfg)
            for s in Pl:
                if s.sentient:
                    tot += 1
                    if not eaters_of[s.id]: nob += 1; ex[s.id] += 1
    rows.append([lb, tot, nob, pct(nob, tot), ', '.join(k for k, _ in ex.most_common(8))])
P('## Sentient pool entries with no allowed eater anywhere in their pool (spring; per embark x layer)\n')
P(md(['config', 'sentient entries', 'no eater', 'share', 'examples'], rows)); P('')

# flying layer non-BENIGN predators
for b in EMBARKS:
    Pl = pool(b, 'flying', 'SPRING', B)
    nb = [s.id for s in Pl if not s.vermin and s.role == 'predator' and not s.benign]
    P('- %s flying: %d predators, non-BENIGN: %s' % (b, sum(1 for s in Pl if not s.vermin and s.role == 'predator'), ', '.join(nb) or 'none'))
P('')

# caverns: bizarre ceiling exclusions
rows = []
for L in (1, 2, 3):
    dep = [s for s in SPECIES.values() if s.biomes & {'SUBTERRANEAN_CHASM', 'SUBTERRANEAN_WATER'} and s.depth[0] <= L <= s.depth[1]]
    kept = {s.id for s in pool('UNDER', 'cav%d' % L, 'SPRING', B)}
    rows.append(['cav%d' % L, len(dep), len(kept), ', '.join(sorted(s.id + '(%d)' % s.bizarre for s in dep if s.id not in kept)) or '-'])
P('## Cavern candidates: DF depth vs depth+ceiling (natural, spring)\n')
P(md(['layer', 'DF depth range', 'after score ceiling', 'removed by the ceiling (score)'], rows)); P('')
for L in ('cav1', 'cav2', 'cav3', 'deep'):
    P('- %s pool (baseline): %s' % (L, ', '.join('%s[%s,%d]' % (s.id, tclass(s, B), s.bizarre) for s in pool('UNDER', L, 'SPRING', B))))
(HERE / 'extras.md').write_text('\n'.join(out) + '\n')
print('\n'.join(out))
