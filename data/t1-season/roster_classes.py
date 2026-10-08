#!/usr/bin/env python3
"""Class each roster species from DF's raws (vermin: any VERMIN_ tag; predator: LARGE_PREDATOR or a CARNIVORE without BENIGN;
else prey) and count active species per layer per season, all and without vermin: roster_classes.py DIR [DIR...]"""
import csv, glob, os, re, sys, collections
DF = os.path.expanduser('~/Library/Application Support/CrossOver/Bottles/Win10/drive_c/Program Files (x86)/Steam/steamapps/common/Dwarf Fortress/data/vanilla')


def raws():
    tags = {}
    for p in glob.glob(DF + '/*/objects/creature_*.txt'):
        cur = None
        for line in open(p, encoding='cp437', errors='replace'):
            for t in re.findall(r'\[([^\]]+)\]', line):
                if t.startswith('CREATURE:'):
                    cur = t.split(':', 1)[1]; tags[cur] = set()
                elif cur:
                    tags[cur].add(t.split(':')[0])
    return tags


def klass(t):
    if any(x.startswith('VERMIN_') for x in t):
        return 'vermin'
    if 'LARGE_PREDATOR' in t or ('CARNIVORE' in t and 'BENIGN' not in t):
        return 'predator'
    return 'prey'


def read(p):
    with open(p, newline='', encoding='cp437') as f:
        return list(csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE))


if __name__ == '__main__':
    T = raws()
    for d in sys.argv[1:]:
        ro = read(d + '/roster.tsv')
        c = collections.Counter()
        for r in ro:
            k = klass(T.get(r['token'], set()))
            for s in ('Sp', 'Su', 'Au', 'Wi'):
                if s in r['seasons']:
                    c[(r['layer'], s, 'all')] += 1
                    if k != 'vermin':
                        c[(r['layer'], s, 'nonvermin')] += 1
                    c[(r['layer'], s, k)] += 1
        print('==', d, 'roster', len(ro), 'unknown tokens', [r['token'] for r in ro if r['token'] not in T][:5])
        for L in ('land', 'water', 'cavern', 'deep'):
            print('  %-6s ' % L + '  '.join('%s %2d (%2d non-vermin: %2d pred %2d prey)' % (s, c[(L, s, 'all')], c[(L, s, 'nonvermin')], c[(L, s, 'predator')], c[(L, s, 'prey')]) for s in ('Sp', 'Su', 'Au', 'Wi')))
