#!/usr/bin/env python3
"""data/pacing/analyse.py RUN -- per fort and layer: arrivals per season by source, occupancy against the cap, days the layer
sat at zero while under its cap and not paused, and cast coverage (share of the season's cast members seen on the map that
season). Reads data/pacing/RUN/*/probe.jsonl (probe.lua); writes RUN/summary.json + summary.md. v8.1 pacing plan, 16 Nov 2026."""
import collections
import json
import sys
from pathlib import Path

RUN = Path(__file__).resolve().parent / sys.argv[1]
TPD = 1200
SEASON = ['Spring', 'Summer', 'Autumn', 'Winter']
# the castsView layer names -> the tool's layer keys (water:<body> and cavern:<depth> fold by prefix)
CAST2LK = {'ground': 'land', 'flying': 'flying', 'ocean': 'water', 'fresh': 'water', 'cavern1': 'cavern:0', 'cavern2': 'cavern:1',
           'cavern3': 'cavern:2'}


def fold(lk):
    return 'water' if lk.startswith('water') else lk


def fort(d: Path):
    rows = [json.loads(x) for x in d.joinpath('probe.jsonl').read_text().splitlines() if x.strip().startswith('{')]
    if len(rows) < 2:
        return None
    first = {}            # group id -> group (first sighting)
    seen_season = collections.defaultdict(set)   # (season, layer) -> tokens seen on the map
    occ = collections.defaultdict(list)          # layer -> [(n, cap, pause)]
    zero_days = collections.Counter()
    casts = {}
    for i, r in enumerate(rows):
        for g in r['groups']:
            key = (g['id'], g['tok'])
            if key not in first:
                first[key] = dict(g, season=r['season'], seen=r['t'], new=i > 0)
            seen_season[(r['season'], fold(g['lk']))].add(g['tok'])
        lay = {}
        for l in r['layers']:
            lay[fold(l['lk'])] = lay.get(fold(l['lk']), (0, 0, False))
            n, cap, p = lay[fold(l['lk'])]
            lay[fold(l['lk'])] = (n + (l['n'] or 0), cap + (l['cap'] or 0), p or bool(l['pause']))
        for lk, (n, cap, p) in lay.items():
            occ[lk].append((n, cap, p))
            if i > 0 and n == 0 and cap > 0 and not p:
                zero_days[lk] += (r['t'] - rows[i - 1]['t']) / TPD
        for c, members in (r.get('casts') or {}).items():
            casts[(r['season'], CAST2LK.get(c, c))] = members
    arr = collections.defaultdict(collections.Counter)    # (season, layer) -> source -> arrivals
    for g in first.values():
        if g['new']:
            arr[(g['season'], fold(g['lk']))][g['src']] += 1
    days = (rows[-1]['t'] - rows[0]['t']) / TPD
    out = {'fort': d.name, 'days': round(days, 1), 'checkpoints': len(rows), 'layers': {}}
    layers = sorted(set(occ) | {k[1] for k in arr})
    for lk in layers:
        o = occ.get(lk, [])
        rec = {'mean_n': round(sum(x[0] for x in o) / max(1, len(o)), 2), 'cap': max((x[1] for x in o), default=0),
               'paused_share': round(sum(1 for x in o if x[2]) / max(1, len(o)), 2), 'zero_days': round(zero_days[lk], 1),
               'seasons': {}}
        for s in sorted({k[0] for k in arr if k[1] == lk} | {k[0] for k in casts if k[1] == lk}):
            members = casts.get((s, lk), [])
            seen = seen_season.get((s, lk), set())
            rec['seasons'][SEASON[s]] = {'arrivals': dict(arr.get((s, lk), {})), 'cast': len(members),
                                         'covered': len([m for m in members if m in seen])}
        out['layers'][lk] = rec
    # balance per raw layer key (water bodies and caverns apart): arrivals, species, the top species' share, effective
    # species count (exp Shannon), arrivals of species in no cast that season, same-tick bursts (16 Nov 2026, B1 PC_SAVR:
    # caverns 1/3 were 56%/54% bugbats/flesh balls, the pool 19 of 19 ospreys, up to 3 groups on one tick over the cap)
    import math
    allcast = collections.defaultdict(set)
    for (se, _), m in casts.items():
        allcast[se].update(m)
    bal = {}
    per = collections.defaultdict(list)
    for g in first.values():
        if g['new']:
            per[g['lk']].append(g)
    for lk, gs in sorted(per.items()):
        sp = collections.Counter(g['tok'] for g in gs)
        n = len(gs)
        H = -sum(c / n * math.log(c / n) for c in sp.values())
        top, topn = sp.most_common(1)[0]
        ticks = collections.Counter(g['arr'] for g in gs if g['arr'] and g['arr'] > 0)
        off = [g['tok'] for g in gs if allcast[g['season']] and g['tok'] not in allcast[g['season']]]
        bal[lk] = {'arrivals': n, 'species': len(sp), 'top': top, 'top_share': round(topn / n, 2), 'eff_species': round(math.exp(H), 1),
                   'off_cast': len(off), 'off_cast_species': sorted(set(off)), 'bursts': sum(1 for c in ticks.values() if c > 1),
                   'burst_max': max(ticks.values(), default=0), 'by_src': dict(collections.Counter(g['src'] for g in gs))}
    out['balance'] = bal
    return out


def main():
    forts = [f for f in (fort(d) for d in sorted(RUN.iterdir()) if d.joinpath('probe.jsonl').exists()) if f]
    RUN.joinpath('summary.json').write_text(json.dumps(forts, indent=1))
    lines = [f'# {RUN.name}: pacing per layer', '',
             '| fort | layer | cap | mean on map | paused | days at 0 (under cap) | season | arrivals by source | cast covered |',
             '|---|---|---|---|---|---|---|---|---|']
    for f in forts:
        for lk, r in f['layers'].items():
            for s, x in (r['seasons'] or {'-': {'arrivals': {}, 'cast': 0, 'covered': 0}}).items():
                a = ', '.join(f'{k} {v}' for k, v in sorted(x['arrivals'].items())) or '0'
                lines.append(f"| {f['fort']} ({f['days']} d) | {lk} | {r['cap']} | {r['mean_n']} | {r['paused_share']:.0%} | "
                             f"{r['zero_days']} | {s} | {a} | {x['covered']}/{x['cast']} |")
    lines += ['', f'# {RUN.name}: balance per layer (new arrivals over the run)', '',
              '| fort | layer | arrivals | species | effective species | top species (share) | off-cast arrivals | same-tick bursts (max) | by source |',
              '|---|---|---|---|---|---|---|---|---|']
    for f in forts:
        for lk, b in f.get('balance', {}).items():
            src = ', '.join(f'{k} {v}' for k, v in sorted(b['by_src'].items()))
            offs = f"{b['off_cast']}" + (f" ({', '.join(b['off_cast_species'][:4])}{'...' if len(b['off_cast_species']) > 4 else ''})" if b['off_cast'] else '')
            lines.append(f"| {f['fort']} | {lk} | {b['arrivals']} | {b['species']} | {b['eff_species']} | {b['top']} ({b['top_share']:.0%}) | "
                         f"{offs} | {b['bursts']} ({b['burst_max']}) | {src} |")
    RUN.joinpath('summary.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
