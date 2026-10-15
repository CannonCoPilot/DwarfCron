"""castsim.ecology: what each cast layer actually brought onto the map, season by season, fort by fort (user 14 Oct 2026:
"analyze the biodiversity and patterns of creature-type arrivals from each cast-type, across various biomes and region-types").

Per (fort, layer, season), from a season-run cell:
  cast       the season's cast for the layer (casts-start.txt): its non-vermin species and how many of them arrived at all
  arrivals   ARRIVE events of wild units, assigned to the layer whose cast holds the species that season ('off-cast' when none
             does: DF's own stock of a layer the tool leaves alone, or a straggler of the last season); rate per 28 days so a
             partial season (the embark spring) compares with a whole one
  diversity  species richness S, Shannon H' (natural log), evenness J = H'/ln S, and dominance (the top species' share)
  mix        the arrivals by animal type (crowd.animal_type)
  crowd      from positions.tsv: the mean number of wild animals present per day on the layer's super-layer, and the mean
             number of species present per day (what the report's crowdedness charts draw)
Runs: CELLS below, the newest full-year cell of each fort per engine. Feeds design_report.ecology_section().
Usage: python3 ecology.py [--json OUT]"""
from __future__ import annotations

import collections
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import crowd  # noqa: E402

ROOT = HERE.parent.parent / 'data' / 'season-run'
TPD, TPY, TPS = 1200, 403200, 100800
SEASONS = ('Spring', 'Summer', 'Autumn', 'Winter')
LAYERS = ('ground', 'flying', 'ocean', 'fresh', 'cavern1', 'cavern2', 'cavern3')
SUPER = {'ground': 'land', 'flying': 'land', 'ocean': 'water', 'fresh': 'water', 'cavern1': 'cavern', 'cavern2': 'cavern',
         'cavern3': 'cavern'}
WILD = ('wild', 'wild-group')

# (engine, run, arm, fort label, biome, region type): the newest full-year cell of each fort on each engine
CELLS = [
    ('12 Oct', 'X4v75b', 'L', 'Lake', 'lake', 'calm'),
    ('12 Oct', 'X4v75b', 'O', 'Ocean shore', 'ocean', 'calm'),
    ('12 Oct', 'X4v75b', 'B', 'Brook', 'brook', 'calm'),
    ('13 Oct', 'X5v75', 'G', 'Good coast', 'ocean', 'good'),
    ('13 Oct', 'X5v75', 'S', 'Small savage lake', 'lake', 'savage, isolated'),
    ('13 Oct', 'X5v75', 'U', 'Untamed wilds lake', 'lake', 'savage'),
    ('13 Oct', 'X5v75', 'J', 'Joyous wilds coast', 'ocean', 'good, savage'),
    ('13 Oct', 'X5v75', 'T', 'Terrifying coast', 'ocean', 'evil, savage'),
    ('14 Oct', 'X7v75h', 'B', 'Brook', 'brook', 'calm'),
    ('14 Oct', 'X7v75', 'X', 'Extinct wilds', 'lake', 'savage, isolated'),
    ('14 Oct', 'X7v75c', 'E', 'Evil coast', 'ocean', 'evil'),
    ('14 Oct', 'X7v75c', 'G', 'Good coast', 'ocean', 'good'),
    ('14 Oct', 'X7v75b', 'S', 'Small savage lake', 'lake', 'savage, isolated'),
    ('14 Oct', 'X7v75b', 'U', 'Untamed wilds lake', 'lake', 'savage'),
    ('14 Oct', 'X7v75c', 'J', 'Joyous wilds coast', 'ocean', 'good, savage'),
    ('14 Oct', 'X7v75f', 'T', 'Terrifying coast', 'ocean', 'evil, savage'),
]


def split_tokens(s: str, known: set) -> list:
    """a cast line's species: DF ids can hold spaces and commas ('RIVER OTTER', 'PLATYPUS, GIANT'), so join words greedily into
    the longest id the raws know"""
    w, out, i = s.split(), [], 0
    while i < len(w):
        for n in (4, 3, 2, 1):
            cand = ' '.join(w[i:i + n])
            if n == 1 or cand in known:
                out.append(cand); i += n; break
    return out


def casts(cell: Path, known: set) -> dict:
    """{(layer, season): {'cast': [non-vermin], 'vermin': [...], 'seed': tok}} from casts-start.txt"""
    out = {}
    f = cell / 'casts-start.txt'
    if not f.exists():
        return out
    for ln in f.read_text(errors='replace').splitlines():
        m = re.match(r'\s+(ground|flying|ocean|fresh|cavern[123])\s+(Spring|Summer|Autumn|Winter)\s+\S+\s+seed\s+(\S+)\s+(.*)$', ln)
        if not m:
            continue
        main, _, ver = m.group(4).partition('|')
        out[(m.group(1), m.group(2))] = {'cast': split_tokens(main, known), 'vermin': split_tokens(ver, known), 'seed': m.group(3)}
    return out


def shannon(c: collections.Counter) -> tuple:
    n = sum(c.values())
    if not n:
        return 0.0, 0.0
    h = -sum(v / n * math.log(v / n) for v in c.values() if v)
    return h, (h / math.log(len(c)) if len(c) > 1 else 0.0)


def season_of(t: int) -> str:
    return SEASONS[(t % TPY) // TPS]


def analyse(cell: Path, classify, known: set) -> dict:
    C = casts(cell, known)
    where = collections.defaultdict(dict)        # season -> species -> layer (first cast holding it)
    anywhen = {t for v in C.values() for t in v['cast'] + v['vermin']}   # cast in some season
    for (L, s), v in sorted(C.items(), key=lambda kv: LAYERS.index(kv[0][0])):
        for t in v['cast'] + v['vermin']:
            where[s].setdefault(t, L)
    ev = (cell / 'events.tsv').read_text(encoding='cp437').splitlines()[1:]
    bands = crowd.cavern_bands(cell)
    arr = collections.defaultdict(collections.Counter)    # (layer, season) -> species -> units
    births = collections.Counter()
    ticks = []
    for line in ev:
        x = line.split('\t')
        if len(x) < 10 or not x[0].isdigit():
            continue
        ticks.append(int(x[0]))
        if x[1] != 'ARRIVE' or x[5] not in WILD or x[3] in crowd.PLACED:
            continue
        t, s, sp = int(x[0]), season_of(int(x[0])), x[3]
        L = where[s].get(sp)
        if x[9] == 'cavern' and bands and x[8].lstrip('-').isdigit():   # a cavern arrival is filed by the cavern it came into
            L = 'cavern%d' % crowd.depth_of(bands, int(x[8]))
        if L is None:   # another season's cast (a stand-in, a straggler) or never cast (DF's own stock); 'deep' is the magma sea
            L = ('other season ' if sp in anywhen else 'never cast ') + x[9]
        arr[(L, s)][sp] += 1
        m = re.search(r'age (\d+)', x[10] if len(x) > 10 else '')
        if m and int(m.group(1)) < TPY // 4:
            births[(L, s)] += 1
    # the days of each season the run covered (the embark spring is partial; the new year's spring days count as spring)
    days = collections.Counter()
    if ticks:
        for d in range(min(ticks) // TPD, max(ticks) // TPD + 1):
            days[season_of(d * TPD)] += 1
    # standing crowd per super-layer and season, from the crowdedness series
    S = crowd.series([('c', 'c', cell)], classify)
    stand = {}
    if S['forts']:
        F = S['forts']['c']
        for sup, D in F['layers'].items():
            per = collections.defaultdict(list)
            for d, c in zip(F['days'], D['counts']):
                s = SEASONS[(d % 336) // 84]
                per[s].append((sum(p[1] for p in c), len({p[0] for p in c})))
            for s, v in per.items():
                stand[(sup, s)] = (sum(a for a, _ in v) / len(v), sum(b for _, b in v) / len(v))
    # vermin on the map (recorder vermin.tsv, from 15 Oct): per season, the species seen in any sample and their mean swarms
    vseen = collections.defaultdict(lambda: collections.defaultdict(list))
    vf = cell / 'vermin.tsv'
    if vf.exists():
        for line in vf.read_text(encoding='cp437').splitlines()[1:]:
            x = line.split('\t')
            if len(x) > 3 and x[0].isdigit():
                vseen[season_of(int(x[0]))][x[1]].append(int(x[2]))
    rows = []
    keys = sorted({k for k in arr} | set(C), key=lambda k: (LAYERS.index(k[0]) if k[0] in LAYERS else 9, k[0], SEASONS.index(k[1])))
    for L, s in keys:
        c = arr.get((L, s), collections.Counter())
        cast = C.get((L, s), {})
        n = sum(c.values())
        h, j = shannon(c)
        types = collections.Counter()
        for sp, k in c.items():
            try:
                info = classify(sp)
            except Exception:
                info = {}
            types[crowd.animal_type(info) if info else 'small land prey'] += k
        top = c.most_common(3)
        rows.append({
            'layer': L, 'season': s, 'days': days[s],
            'cast': cast.get('cast', []), 'vermin': cast.get('vermin', []), 'seed': cast.get('seed'),
            'vermin_seen': sorted(v for v in cast.get('vermin', []) if vseen[s].get(v)) if vf.exists() else None,
            'cast_arrived': sorted(t for t in cast.get('cast', []) if c.get(t)),
            'units': n, 'per28': round(n * 28 / days[s], 1) if days[s] else None, 'births': births[(L, s)],
            'S': len(c), 'H': round(h, 2), 'J': round(j, 2),
            'dominance': round(top[0][1] / n, 2) if n else None, 'top': top,
            'types': dict(types.most_common()),
            'crowd': stand.get((SUPER.get(L, L.split()[-1]), s)),
        })
    return {'rows': rows, 'days': dict(days),
            'vermin_map': {s: {k: round(sum(v) / len(v), 1) for k, v in d.items()} for s, d in vseen.items()} if vf.exists() else None}


def run(cells=CELLS) -> list:
    from design import Design
    D = Design()
    classify, known = D.E.classify, set(D.R.src)
    out = []
    for eng, r, a, name, biome, region in cells:
        cell = ROOT / r / a / 'rep1'
        if not (cell / 'events.tsv').exists():
            continue
        out.append({'engine': eng, 'run': r, 'arm': a, 'fort': name, 'biome': biome, 'region': region, **analyse(cell, classify, known)})
    return out


if __name__ == '__main__':
    res = run()
    if '--json' in sys.argv:
        Path(sys.argv[sys.argv.index('--json') + 1]).write_text(json.dumps(res, indent=1, default=list))
    for f in res:
        print(f"\n## {f['fort']} ({f['engine']} engine, {f['run']}/{f['arm']}; {f['biome']}, {f['region']}) days {f['days']}")
        for r in f['rows']:
            cr = r['crowd']
            print(f"  {r['layer']:16} {r['season']:6} cast {len(r['cast']):2} got {len(r['cast_arrived']):2}  units {r['units']:4} "
                  f"/28d {r['per28'] if r['per28'] is not None else '-':>6}  S {r['S']:2} H {r['H']:.2f} J {r['J']:.2f} "
                  f"dom {r['dominance'] if r['dominance'] is not None else '-':>4}  crowd {'%.1f/%.1f' % cr if cr else '-':>10}  "
                  f"top {', '.join(f'{t} {k}' for t, k in r['top'])}")


# --- evidence for the report's diagnosis (14 Oct engine cells) ---------------------------------------------------------

def _where(C):
    w = collections.defaultdict(dict)
    for (L, s), v in C.items():
        for t in v['cast'] + v['vermin']:
            w[s].setdefault(t, L)
    return w


def land_sources(cells, known):
    """land waves (the tool's 'detached X' lines) by the cast that holds the species -- ground, flying or a water cast's bird --
    and how often the land cap paused the layer, per fort and season"""
    out = []
    for eng, r, a, name, *_ in cells:
        cell = ROOT / r / a / 'rep1'
        if not (cell / 'ledger.tsv').exists():
            continue
        where = _where(casts(cell, known))
        c, caps = collections.Counter(), collections.Counter()
        for line in (cell / 'ledger.tsv').read_text(encoding='cp437').splitlines()[1:]:
            x = line.split('\t')
            if len(x) < 4 or not x[0].isdigit() or x[2] != 'land':
                continue
            s = season_of(int(x[0]))
            if 'at its cap' in x[3]:
                caps[s] += 1
            m = re.match(r'detached (.+?) x\d+', x[3])
            if m:
                L = where[s].get(m.group(1), 'other')
                c[(s, 'ground' if L == 'ground' else 'flying' if L == 'flying' else 'water' if L in ('ocean', 'fresh') else 'other')] += 1
        for s in SEASONS:
            out.append({'fort': name, 'season': s, 'ground': c[(s, 'ground')], 'flying': c[(s, 'flying')], 'water': c[(s, 'water')],
                        'caps': caps[s]})
    return out


def freq_bands(cells, known):
    """each surface cast species (ground, flying, ocean, fresh) by the FREQUENCY it had mid-season, and whether it arrived"""
    import glob
    bands = (('1-2', 0, 2), ('3-5', 3, 5), ('6-20', 6, 20), ('21 and up', 21, 10 ** 9))
    tot, got = collections.Counter(), collections.Counter()
    for eng, r, a, name, *_ in cells:
        cell = ROOT / r / a / 'rep1'
        C = casts(cell, known)
        snaps = collections.defaultdict(list)
        for f in sorted(glob.glob(str(cell / 'states' / '*.json'))):
            snaps[season_of(int(Path(f).stem))].append(f)
        seen = collections.defaultdict(set)
        for line in (cell / 'events.tsv').read_text(encoding='cp437').splitlines()[1:]:
            x = line.split('\t')
            if len(x) > 9 and x[1] == 'ARRIVE' and x[5] in WILD:
                seen[season_of(int(x[0]))].add(x[3])
        for (L, s), v in C.items():
            if L.startswith('cavern') or not snaps[s]:
                continue
            raws = json.loads(Path(snaps[s][len(snaps[s]) // 2]).read_text())['raws']
            for t in v['cast']:
                f = (raws.get(t) or [0])[0]
                b = next(n for n, lo, hi in bands if lo <= f <= hi)
                tot[b] += 1
                got[b] += t in seen[s]
    return [(n, got[n], tot[n]) for n, *_ in bands]


def freezes(cells):
    """wild animals killed by ice (DF's ENCASE_ICE) per fort: when, which, and how long they had been on the map"""
    out = []
    for eng, r, a, name, *_ in cells:
        ev = (ROOT / r / a / 'rep1' / 'events.tsv').read_text(encoding='cp437').splitlines()[1:]
        arr, sp, days, age = {}, collections.Counter(), set(), []
        for line in ev:
            x = line.split('\t')
            if len(x) > 3 and x[1] == 'ARRIVE':
                arr[x[2]] = int(x[0])
        for line in ev:
            x = line.split('\t')
            if len(x) > 10 and x[1] == 'DIE' and 'ENCASE_ICE' in x[10]:
                t = int(x[0]); sp[x[3]] += 1; days.add((t % TPY) // TPD + 1)
                if x[2] in arr:
                    age.append((t - arr[x[2]]) // TPD)
        if sp:
            placed = sum(v for k, v in sp.items() if k in crowd.PLACED)
            out.append({'fort': name, 'n': sum(sp.values()), 'placed': placed, 'days': sorted(days),
                        'animals': [(k, v) for k, v in sp.most_common() if k not in crowd.PLACED][:4],
                        'age': sorted(age)[len(age) // 2] if age else None})
    return out


def kills(cells, n=5):
    """who killed whom among the wild animals, per fort (the run's DIE lines with a killer)"""
    out = []
    for eng, r, a, name, *_ in cells:
        k, deaths = collections.Counter(), 0
        for line in (ROOT / r / a / 'rep1' / 'events.tsv').read_text(encoding='cp437').splitlines()[1:]:
            x = line.split('\t')
            if len(x) > 10 and x[1] == 'DIE' and x[5] in WILD:
                deaths += 1
                m = re.search(r'killer (.+?) #', x[10])
                if m and m.group(1) not in ('DWARF',):
                    k[(m.group(1), x[3])] += 1
        out.append({'fort': name, 'deaths': deaths, 'top': k.most_common(n)})
    return out


CATEGORIES = crowd.TYPES + ['vermin']


def categories(res, classify) -> list:
    """per fort: the distinct species its casts held over the year by animal type, vermin as a category of its own (user 15 Oct:
    'include vermin categorically'), and how many of each type arrived. Vermin never arrive as units (DF spawns them as swarms
    and the engine's holds rewrite their stock), so for them only the casts are known."""
    out = []
    for f in res:
        cast, got, names = collections.defaultdict(set), collections.defaultdict(set), collections.defaultdict(set)
        for r in f['rows']:
            if r['layer'] not in LAYERS:
                continue
            for t in r['cast']:
                try:
                    k = crowd.animal_type(classify(t))
                except Exception:
                    k = 'small land prey'
                cast[k].add(t)
                if t in r['cast_arrived']:
                    got[k].add(t)
            for t in r['vermin']:
                cast['vermin'].add(t); names[SUPER[r['layer']]].add(t)
                if r.get('vermin_seen') and t in r['vermin_seen']:
                    got['vermin'].add(t)
        out.append({'fort': f['fort'], 'engine': f['engine'], 'cast': {k: len(v) for k, v in cast.items()},
                    'got': {k: len(v) for k, v in got.items()}, 'vermin_by': {k: sorted(v) for k, v in names.items()},
                    'vermin_sampled': f.get('vermin_map') is not None})
    return out
