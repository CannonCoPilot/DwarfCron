#!/usr/bin/env python3
"""Cast coverage: of each season's land-ground cast (non-vermin), how many species arrived at least once in that season.

13 Oct 2026: 97 of 241 ground slots (40%) and 16 of 64 extinct ones across nine forts; the cause was DF drawing walkers only
from the site's own region tile while the tool created entries on a neighbour (sw bebb00d).

Usage: cast-coverage.py RUN/ARM [RUN/ARM ...]   (cells under data/season-run, rep1)
"""
import collections
import csv
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent / 'data' / 'season-run'
SEASONS = ['Spring', 'Summer', 'Autumn', 'Winter']
TPY, TPS = 403_200, 100_800
ERA = re.compile(r'(SILURIAN|DEVONIAN|CARBONIFEROUS|PERMIAN|TRIASSIC|JURASSIC|CRETACEOUS|CENOZOIC)_')


def coverage(cell: pathlib.Path):
    cast = {}
    for ln in (cell / 'casts-start.txt').read_text().splitlines():
        m = re.match(r'\s+ground\s+(\w+)\s+\S+\s+seed\s+\S+\s+(.*?)\s*\|', ln)
        if m:
            cast[m.group(1)] = m.group(2).split()
    seen = collections.defaultdict(set)
    with open(cell / 'events.tsv', encoding='cp437') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            if row['event'] == 'ARRIVE':
                seen[SEASONS[(int(row['tick']) % TPY) // TPS]].add(row['race'])
    out, tot = [], collections.Counter()
    for s in SEASONS:
        if s not in cast or not seen[s]:
            continue
        c = cast[s]
        got = [x for x in c if x in seen[s]]
        ext = [x for x in c if ERA.match(x)]
        tot['cast'] += len(c); tot['got'] += len(got)
        tot['ext'] += len(ext); tot['extgot'] += sum(1 for x in ext if x in seen[s])
        out.append(f'{s[:2]} {len(got)}/{len(c)} (missing {" ".join(x for x in c if x not in seen[s]) or "-"})')
    return out, tot


def main():
    total = collections.Counter()
    for arg in sys.argv[1:]:
        out, tot = coverage(ROOT / arg / 'rep1')
        total.update(tot)
        print(f'{arg}:'); [print('  ' + o) for o in out]
        print(f'  ground {tot["got"]}/{tot["cast"]}, extinct {tot["extgot"]}/{tot["ext"]}')
    if len(sys.argv) > 2:
        print(f'all: ground {total["got"]}/{total["cast"]}, extinct {total["extgot"]}/{total["ext"]}')


if __name__ == '__main__':
    main()
