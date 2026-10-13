"""castsim.crowd: how crowded and how diverse each super-layer was through a season-run, day by day (user 13 Oct).

From a run's positions.tsv (every wild unit on the map, every 1,000 ticks): one sample per day of the year, the snapshot
nearest the day's start, counted per species on land, water and cavern. Each species is typed by its guild (engine.py's
classify) into seven animal types, so a stacked bar shows the crowd (height), the diversity (segments: one per species)
and the mix (colour by type) at once. Feeds design_report.crowd_section()."""
from __future__ import annotations

import collections
from pathlib import Path

TPD, TPY, TPS = 1200, 403200, 100800
SUPER = ('land', 'water', 'cavern')
# animal types: at most seven, so the categorical palette never cycles (the order is the stacking order, bottom first)
TYPES = ['large predators', 'predators', 'fliers', 'grazers', 'small land prey', 'water life', 'sentients']


def animal_type(e: dict) -> str:
    if e.get('sentient') or e.get('ap'): return 'sentients'
    g = e.get('guild')
    if g in ('AL', 'AW'): return 'large predators'
    if g in ('ML', 'MW'): return 'predators'
    if g in ('RP', 'LB', 'WB'): return 'fliers'
    if g == 'GZ': return 'grazers'
    if g in ('FF', 'FC', 'PE', 'SH'): return 'water life'
    return 'small land prey'


def series(rundir: Path, classify) -> dict:
    """{'forts': {arm: {'days': [yday...], 'layers': {L: {'species': [tok...], 'counts': [[[i, n], ...] per day]}}}},
        'types': {tok: type}, 'seasons': [(yday, label)]}"""
    out, types, y0 = {}, {}, None
    for arm in 'LOB':
        f = rundir / arm / 'rep1' / 'positions.tsv'
        if not f.exists(): continue
        snaps = collections.defaultdict(lambda: {L: collections.Counter() for L in SUPER})
        for line in f.read_text(encoding='cp437').splitlines()[1:]:
            x = line.split('\t')
            if len(x) < 8 or not x[0].isdigit() or x[3] not in ('wild', 'wild-group') or x[7] not in SUPER: continue
            if len(x) > 8 and x[8] == '0': continue          # dead
            snaps[int(x[0])][x[7]][x[2]] += 1
        ticks = sorted(snaps)
        if not ticks: continue
        if y0 is None: y0 = ticks[0] // TPY * TPY
        d0, d1 = -(-(ticks[0] - y0) // TPD), (ticks[-1] - y0) // TPD
        days, per = [], {L: [] for L in SUPER}
        j = 0
        for d in range(d0, d1 + 1):
            t = y0 + d * TPD
            while j + 1 < len(ticks) and abs(ticks[j + 1] - t) <= abs(ticks[j] - t): j += 1
            days.append(d)
            for L in SUPER: per[L].append(snaps[ticks[j]][L])
        layers = {}
        for L in SUPER:
            toks = sorted({tok for c in per[L] for tok in c})
            for tok in toks:
                if tok not in types:
                    try: types[tok] = animal_type(classify(tok))
                    except Exception: types[tok] = 'small land prey'
            toks.sort(key=lambda t: (TYPES.index(types[t]), t))
            idx = {t: i for i, t in enumerate(toks)}
            layers[L] = {'species': toks, 'counts': [[[idx[t], n] for t, n in sorted(c.items(), key=lambda kv: idx[kv[0]])] for c in per[L]]}
        out[arm] = {'days': days, 'layers': layers}
    seasons = [(0, 'Spring'), (84, 'Summer'), (168, 'Autumn'), (252, 'Winter'), (336, 'new year · Spring')]
    return {'forts': out, 'types': types, 'type_order': TYPES, 'seasons': seasons}
