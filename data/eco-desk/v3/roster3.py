#!/usr/bin/env python3
"""roster3: season casts for seasonal-wildlife (files only; user rulings 7 Oct 2026 evening, memory season-cast-rulings-oct7).

The pool (the embark's species) is not the roster. Each season, per layer (land, water, cavern; deep: a few), a CAST is grown:
  seed   one in-season HIGH-VALUE species (pet value, war training, or butcher parts) that has an edge in the pool;
  grow   repeatedly pick a cast member and add one of its in-season prey or predators whose trophic slot has room
         (the emptiest slot first); a member with nothing left to add is set aside and another member is tried;
  vermin then a few in-season vermin that some cast member eats (distinct classes first);
  rotate the next season's cast is grown with last season's members down-weighted, so casts change season to season.
The cast IS the season's roster: only cast species may appear. Everything else in the pool rests.

Edges, pools, guilds and slots come from the v2.2 desk (../v2/guilds/roster2.py, config V22). Layers here merge the desk's:
land = land + flying, water = ocean + lake + river (those present), cavern = cav1-3 + cavw1-3, deep = deep.

build_year(ekey, seed, cfg) -> {season: {layer: Cast}}; pure for a given seed.
"""
import collections, hashlib, json, random, sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'v2' / 'guilds'))
import roster2 as R2                                         # noqa: E402
from run2 import V22                                         # noqa: E402
from species2 import tier, SEASONS                           # noqa: E402

FEAT = json.load(open(HERE.parent / 'roster' / 'features.json'))
TOK = {r['id']: r for r in __import__('csv').DictReader(open(HERE.parent / 'tokens-by-creature.tsv'), delimiter='\t')}

SUBLAYERS = {'land': ['land', 'flying'], 'water': ['ocean', 'lake', 'river'],
             'cavern': ['cav1', 'cav2', 'cav3', 'cavw1', 'cavw2', 'cavw3'], 'deep': ['deep']}

# trophic slots per layer: (slot name, guild codes it takes, how many wanted). Non-vermin first, then vermin.
SLOTS = {
    'land': [('apex', {'APX'}, 1), ('meso', {'ML'}, 2), ('raptor', {'RP'}, 1), ('grazer', {'GZ'}, 2), ('ground prey', {'PL'}, 2),
             ('bird', {'LB', 'WB'}, 1), ('sentient', {'SN', 'SNP', 'TH'}, 1)],
    'water': [('apex', {'APX', 'APE'}, 1), ('meso', {'MW'}, 1), ('fish', {'FC', 'FF'}, 3), ('pelagic', {'PE'}, 1),
              ('shore', {'SH'}, 2), ('waterbird', {'WB'}, 1), ('sentient', {'SN', 'SNP'}, 1)],
    'cavern': [('apex', {'APX'}, 1), ('meso', {'ML', 'MW'}, 2), ('ground prey', {'PL', 'GZ'}, 3), ('flier', {'RP', 'LB'}, 1),
               ('shore', {'SH'}, 1), ('sentient', {'SN', 'SNP'}, 1)],
    'deep': [('apex', {'APX', 'ML'}, 1), ('prey', {'PL'}, 2)],
}
VERMIN_WANT = {'land': 3, 'water': 2, 'cavern': 3, 'deep': 0}
MIN_NONVERMIN = {'land': 8, 'water': 6, 'cavern': 8, 'deep': 1}


@dataclass(frozen=True)
class Cfg3:
    base: R2.Cfg = V22
    hv_giant_root: bool = True       # a giant's pet value is its root animal's (DF gives every giant PETVALUE 500)
    hv_petvalue: int = 200
    hv_mass: int = 1_000_000
    hv_mats: frozenset = frozenset({'IVORY', 'PEARL', 'SILK', 'SHELL'})
    carry: float = 0.25              # pick weight of a species that was in last season's cast (rotation)
    pack: float = 3.0                # x3 for non-BENIGN group hunters (user ruling 30 Sep)
    giant: float = 0.2               # giants picked x0.2 (ruling 30 Sep: giants pick x0.2), seed included
    emptiest_first: bool = True      # fill the emptiest slot first (v1 lesson: first-filled classes starve later ones)
    land_air: bool = True            # raptor -> ground prey and meso -> bird edges in the merged land layer
    label: str = 'v3'


def petvalue(sid, cfg):
    r = TOK.get(sid) or {}
    s = R2.species(cfg.base).get(sid)
    if cfg.hv_giant_root and s is not None and s.giant and s.root in TOK:
        r = TOK[s.root]
    v = r.get('PETVALUE', '')
    try:
        return int(str(v).split('|')[0].split('=')[-1]) if v not in ('', '0') else 0
    except ValueError:
        return 0


def high_value(s, cfg):
    """the reasons a species is high value (empty = not): pet value, war training, butcher parts"""
    why = []
    if petvalue(s.id, cfg) >= cfg.hv_petvalue: why.append('pet')
    r = TOK.get(s.id) or {}
    if r.get('TRAINABLE_WAR', '') not in ('', '0') or r.get('TRAINABLE', '') not in ('', '0'): why.append('war')
    mats = set((FEAT.get(s.id) or {}).get('valuable_mats', ()))
    if s.mass >= cfg.hv_mass or mats & cfg.hv_mats: why.append('parts')
    return why


def slot_name(s, layer, sub, cfg):
    code = R2.slot_of(s, sub, cfg.base)
    if s.vermin:
        return 'vermin'
    for name, codes, _ in SLOTS[layer]:
        if code in codes:
            return name
    return None


@dataclass
class Pool:
    species: dict                    # id -> Sp
    sub: dict                        # id -> the sublayers it is in
    slot: dict                       # id -> slot name (None: no slot on this layer)
    edges: dict                      # (eater, eaten) -> weight
    nb: dict                         # id -> neighbours (either direction)


def season_pool(ekey, layer, season, cfg):
    sp, sub, E = {}, collections.defaultdict(list), {}
    for L in SUBLAYERS[layer]:
        P = R2.pool(ekey, L, season, cfg.base)
        if not P:
            continue
        E1, _ = R2.relations(ekey, L, season, cfg.base)
        for s in P:
            sp[s.id] = s; sub[s.id].append(L)
        for (a, b), (w, kind) in E1.items():
            E[(a, b)] = max(E.get((a, b), 0), w)
    if layer == 'land' and cfg.land_air:
        # the merged land layer: raptors take small ground prey and ground vermin (the tool's stoop: prey up to 2x the raptor's
        # mass), and ground mesopredators take birds no heavier than themselves (the desk kept these in separate layers)
        for p in sp.values():
            for x in sp.values():
                if p.id == x.id or (p.id, x.id) in E or x.vermin and x.vclass != 'VG':
                    continue
                if p.guild == 'RP' and not p.vermin and (x.vermin or (x.guild in ('PL', 'SH') and x.mass <= 2 * p.mass)):
                    E[(p.id, x.id)] = 0.5
                elif p.guild == 'ML' and not p.vermin and not x.vermin and x.guild in ('LB', 'WB') and x.mass <= p.mass:
                    E[(p.id, x.id)] = 0.5
    slot = {i: slot_name(s, layer, sub[i][0], cfg) for i, s in sp.items()}
    nb = collections.defaultdict(set)
    for (a, b) in E:
        nb[a].add(b); nb[b].add(a)
    return Pool(sp, dict(sub), slot, E, nb)


def never_castable(P):
    """species the growth can never reach this season, with the reason; iterated, since removing one can strand another"""
    out = {}
    for i, s in P.species.items():
        if P.slot[i] is None:
            out[i] = 'no slot on this layer'
    changed = True
    while changed:
        changed = False
        for i in P.species:
            if i in out:
                continue
            live = [j for j in P.nb.get(i, ()) if j not in out]
            if not live:
                out[i] = 'no prey and no predator in the pool' if not P.nb.get(i) else 'linked only to species that cannot be cast'
                changed = True
    return out


@dataclass
class Cast:
    layer: str
    season: str
    seed: str = ''
    seed_why: tuple = ()
    members: list = field(default_factory=list)      # non-vermin, in order of addition
    vermin: list = field(default_factory=list)
    slots: dict = field(default_factory=dict)        # slot -> members
    unfilled: dict = field(default_factory=dict)     # slot -> reason
    excluded: dict = field(default_factory=dict)     # never castable this season -> reason
    edges: list = field(default_factory=list)        # (eater, eaten) inside the cast
    log: list = field(default_factory=list)

    @property
    def all(self): return self.members + self.vermin


def grow(ekey, layer, season, rng, cfg, prev=()):
    P = season_pool(ekey, layer, season, cfg)
    c = Cast(layer, season)
    c.excluded = never_castable(P)
    ok = {i for i in P.species if i not in c.excluded}
    want = {name: n for name, _, n in SLOTS[layer]}
    have = collections.Counter()
    prev = set(prev)

    def weight(i):
        s = P.species[i]
        w = 1.0
        if tier(s) >= 2 and not s.benign and s.cmax > 1:
            w *= cfg.pack
        if i in prev:
            w *= cfg.carry
        if s.giant:
            w *= cfg.giant
        return w

    def pick(cands):
        ws = [weight(i) for i in cands]
        return rng.choices(cands, ws)[0]

    nonv = sorted(i for i in ok if not P.species[i].vermin)
    hv = [i for i in nonv if high_value(P.species[i], cfg)]
    if not nonv:
        c.unfilled = {name: 'empty pool' for name in want}
        return c, P
    c.seed = pick(hv) if hv else pick(nonv)
    c.seed_why = tuple(high_value(P.species[c.seed], cfg)) or ('no high-value species: any linked one',)
    c.members.append(c.seed); have[P.slot[c.seed]] += 1
    tried = set()
    while True:
        room = {n for n in want if have[n] < want[n]}
        if not room:
            break
        # candidates: in-season, castable, non-vermin neighbours of a cast member whose slot has room
        open_members = [m for m in c.members if m not in tried]
        if not open_members:
            break
        m = rng.choice(open_members)
        cand = [j for j in P.nb.get(m, ()) if j in ok and j not in c.members and not P.species[j].vermin and P.slot[j] in room]
        if not cand:
            tried.add(m)                     # nothing left to add from this member: go back and try another
            continue
        if cfg.emptiest_first:
            gap = {n: (want[n] - have[n]) / want[n] for n in room}
            best = max(gap[P.slot[j]] for j in cand)
            cand = [j for j in cand if gap[P.slot[j]] == best]
        j = pick(sorted(cand))
        c.members.append(j); have[P.slot[j]] += 1
        c.log.append('%s -> %s (%s, %s of %s)' % (m, j, P.slot[j], 'prey' if (m, j) in P.edges else 'predator', m))
    for n in want:
        if have[n] < want[n]:
            pool_n = [i for i in ok if P.slot[i] == n]
            c.unfilled[n] = ('%d of %d: ' % (have[n], want[n])) + ('none in season in the pool' if not pool_n else
                                                                     'no link to the cast from the %d in the pool' % len(pool_n))
    # vermin: in-season vermin eaten by a cast member; distinct classes first, then the most-eaten
    eaten = collections.Counter()
    for m in c.members:
        for j in P.nb.get(m, ()):
            if (m, j) in P.edges and P.species[j].vermin and j in ok:
                eaten[j] += 1
    vlist = sorted(eaten, key=lambda j: (-eaten[j], j))
    seen_cls = set()
    for j in sorted(vlist, key=lambda j: rng.random()):
        if len(c.vermin) >= VERMIN_WANT[layer]:
            break
        cl = P.species[j].vclass
        if cl in seen_cls:
            continue
        c.vermin.append(j); seen_cls.add(cl)
    for j in vlist:
        if len(c.vermin) >= VERMIN_WANT[layer]:
            break
        if j not in c.vermin:
            c.vermin.append(j)
    S = set(c.all)
    c.edges = sorted((a, b) for (a, b) in P.edges if a in S and b in S)
    for n in want:
        c.slots[n] = [i for i in c.members if P.slot[i] == n]
    return c, P


def build_year(ekey, seed, cfg=Cfg3(), layers=('land', 'water', 'cavern', 'deep')):
    out = {s: {} for s in SEASONS}
    for layer in layers:
        prev = ()
        for s in SEASONS:
            rng = random.Random(int(hashlib.sha256(('%s|%s|%s|%s|%s' % (ekey, layer, s, seed, cfg.label)).encode()).hexdigest()[:12], 16))
            c, P = grow(ekey, layer, s, rng, cfg, prev)
            out[s][layer] = (c, P)
            prev = c.all
    return out


def components(c):
    par = {i: i for i in c.all}
    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]; i = par[i]
        return i
    for a, b in c.edges:
        par[f(a)] = f(b)
    return len({f(i) for i in c.all}) if c.all else 0


if __name__ == '__main__':
    yr = build_year(sys.argv[1] if len(sys.argv) > 1 else 'TEMP_GRASS_FOREST', int(sys.argv[2]) if len(sys.argv) > 2 else 1)
    for s, layers in yr.items():
        for L, (c, P) in layers.items():
            print('%s %-6s seed %-22s %-12s %2d+%d  parts %d  %s' % (s, L, c.seed, ','.join(c.seed_why), len(c.members), len(c.vermin),
                                                                   components(c), ' '.join(c.members + ['|'] + c.vermin)))
            if c.unfilled:
                print('            unfilled:', c.unfilled)
