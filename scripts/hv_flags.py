#!/usr/bin/env python3
"""hv_flags: which species in a fort's pool are "high value" seed candidates, per layer and season (user, 9 Oct 2026).

Quick and dirty desk version of the proposed rule, run on a fort's pool before it goes into the engine:

    for each layer (land incl. fliers, water, cavern) and each season:
        candidates = non-vermin pool species of that layer that DF allows in that season (no NO_<season> on every caste;
                     a species with no season flags is a candidate in all four)
        high value = war-trainable (TRAINABLE or TRAINABLE_WAR)
                     OR pet value in the top 10% of the candidates (by rank: ceil(n/10), ties by size)
                     OR adult size in the top 10% of the candidates (by rank, ties by pet value)

The percentiles are taken over that layer-season's candidates only. A giant's pet value is its base animal's (DF's GIANT
variation removes PETVALUE, so DF reports 500 for every giant).

Inputs: a sw-state-check JSON dump (pops; the run kit writes them under <cell>/states/), the desk
species table data/eco-desk/v2/guilds/species2.tsv (guild, mass, habitat), and DF's vanilla creature raws (pet value,
trainability). Approximations against the engine: a cave entry is taken as cavern (the deep split needs the tool's depth
table; species whose desk depth starts at 3 or below are dropped), fishers stay on land, locked GOOD/EVIL
species are not removed.

    hv_flags.py STATE.json [STATE.json ...] [--md OUT.md]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECIES = ROOT / 'data/eco-desk/v2/guilds/species2.tsv'
DF = Path.home() / ('Library/Application Support/CrossOver/Bottles/Win10/drive_c/Program Files (x86)/Steam/steamapps/'
                    'common/Dwarf Fortress/data/vanilla')
SEASONS = ['Spring', 'Summer', 'Autumn', 'Winter']
LAYERS = ['land', 'water', 'cavern']


def read_raws() -> dict:
    """token -> {'pet': int|None, 'war': bool, 'copy': root token|None} from every vanilla creature raw file"""
    out = {}
    for f in sorted(DF.glob('vanilla_creatures*/objects/creature_*.txt')):
        text = f.read_text(encoding='latin-1')
        for block in re.split(r'(?=\[CREATURE:)', text)[1:]:
            tok = re.match(r'\[CREATURE:([^\]]+)\]', block).group(1)
            pet = [int(x) for x in re.findall(r'\[PETVALUE:(\d+)\]', block)]
            out[tok] = {'pet': max(pet) if pet else None,
                        'war': bool(re.search(r'\[(TRAINABLE|TRAINABLE_WAR)\]', block)),
                        'copy': (re.search(r'\[COPY_TAGS_FROM:([^\]]+)\]', block) or [None, None])[1]}
    return out


def pet_of(tok: str, raws: dict) -> int:
    r = raws.get(tok, {})
    if r.get('copy') and tok.startswith('GIANT'):
        return pet_of(r['copy'], raws)
    return r.get('pet') or 0


def war_of(tok: str, raws: dict) -> bool:
    r = raws.get(tok, {})
    return r.get('war', False) or (bool(r.get('copy')) and war_of(r['copy'], raws))


def top_k(rows: list, key, tie) -> set:
    """the top 10% of the pool by rank: ceil(n/10) species, ties at the cut broken by `tie` (pet values are coarse --
    50, 100, 650 -- so a value cut of 50 flagged a third of the ocean fort's land pool)"""
    k = math.ceil(len(rows) / 10)
    ranked = sorted((r for r in rows if key(r) > 0), key=lambda r: (key(r), tie(r)), reverse=True)
    return {r['tok'] for r in ranked[:k]}


def layer_of(key: str, sp: dict) -> str | None:
    if key.startswith('cave:'):
        lo = (sp.get('depth') or '0:0').split(':')[0]
        return None if lo.isdigit() and int(lo) >= 3 else 'cavern'   # desk depth lo:hi; 3+ is the magma sea / underworld
    if key.startswith('water:'):
        return 'water'
    return 'water' if sp.get('aquatic') == '1' else 'land'


def pools(state: dict, species: dict) -> dict:
    """(layer, season) -> {token: info} of non-vermin candidates"""
    out = {(L, s): {} for L in LAYERS for s in range(4)}
    for _idx, tok, key, _qty, _ext, typ in state['pops']:
        if typ != 'Animal':
            continue
        sp = species.get(tok, {})
        if sp.get('vermin') == '1':
            continue
        L = layer_of(key, sp)
        if L is None:
            continue
        # the desk's seasons column is read from the raw files: the live raws' NO_<season> flags are cleared by the tool
        # (seasons_own), so the dump's own mask reads '----' on a fort the tool has run on
        live = (state['raws'].get(tok) or [None] * 6)[5] or '----'
        have = set((sp.get('seasons') or 'SP,SU,AU,WI').split(','))
        for s, code in enumerate(('SP', 'SU', 'AU', 'WI')):
            if code in have and live[s] == '-':
                out[(L, s)][tok] = sp
    return out


def flag(pool: dict, raws: dict) -> tuple[list, float, float]:
    rows = []
    for tok, sp in pool.items():
        rows.append({'tok': tok, 'guild': sp.get('guild', '?'), 'mass': float(sp.get('mass') or 0),
                     'pet': pet_of(tok, raws), 'war': war_of(tok, raws)})
    pets = top_k(rows, lambda r: r['pet'], lambda r: r['mass'])
    bigs = top_k(rows, lambda r: r['mass'], lambda r: r['pet'])
    pcut = min((r['pet'] for r in rows if r['tok'] in pets), default=0)
    mcut = min((r['mass'] for r in rows if r['tok'] in bigs), default=0)
    for r in rows:
        why = []
        if r['war']:
            why.append('war')
        if r['tok'] in pets:
            why.append(f'pet {r["pet"]}')
        if r['tok'] in bigs:
            why.append(f'size {r["mass"] / 1e6:.2f}M')
        r['why'] = why
    rows.sort(key=lambda r: (not r['why'], r['tok']))
    return rows, pcut, mcut


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('states', nargs='+', type=Path)
    ap.add_argument('--md', type=Path)
    a = ap.parse_args()
    species = {r['id']: r for r in csv.DictReader(SPECIES.open(), delimiter='\t')}
    raws = read_raws()
    md = ['# High-value seed candidates per layer and season', '',
          'High value = war-trainable, or pet value in the top 10% of that layer-season pool, or adult size in its top 10%. '
          'Pools are the non-vermin species DF allows in that season. Source: `scripts/hv_flags.py`.', '']
    for f in a.states:
        st = json.loads(f.read_text())
        fort = st.get('site') or f.parent.parent.name
        md += [f'## {fort}', '', '| layer | season | pool | high value (why) | pet cut | size cut |', '|---|---|---|---|---|---|']
        for (L, s), pool in pools(st, species).items():
            rows, pcut, mcut = flag(pool, raws)
            hv = [f'{r["tok"]} ({", ".join(r["why"])})' for r in rows if r['why']]
            md.append(f'| {L} | {SEASONS[s]} | {len(rows)} | {"; ".join(hv) or "none"} | '
                      f'{pcut if rows else "-"} | {f"{mcut / 1e6:.2f}M" if rows else "-"} |')
            print(f'{fort:14} {L:6} {SEASONS[s]:6} pool {len(rows):3}  HV {len(hv):2}: {", ".join(r["tok"] for r in rows if r["why"])}')
        md.append('')
    if a.md:
        a.md.write_text('\n'.join(md) + '\n')
        print('wrote', a.md)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
