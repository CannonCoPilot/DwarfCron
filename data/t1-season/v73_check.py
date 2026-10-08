#!/usr/bin/env python3
"""Validate a v7.3 season-cast run: v73_check.py DIR
DIR holds the recorder TSVs, casts-start.txt (`cast status` at the start), ledger.txt and pairs.tsv (`ecology pairs tsv`).
Every arrival on a managed layer is set against that season's cast for its layer: in the cast, or a leak (with the
species and why it might have come). Also: the groups sent off at a season change, and the relation pairs by who set them."""
import collections, csv, re, sys
from analyze import fill_removed, norm

SEASONS = ['Spring', 'Summer', 'Autumn', 'Winter']
TPY, ST = 403200, 100800


def read(p):
    with open(p, newline='', encoding='cp437') as f:
        return norm([r for r in csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE) if None not in r.values()])


def raw_tokens():
    """every creature token in the rig's raws; some hold spaces (GIANT TORTOISE, RIVER OTTER)"""
    import glob, os
    d = os.environ.get('DF_DIR') or os.path.expanduser('~/Library/Application Support/CrossOver/Bottles/Win10/drive_c/'
                                                      'Program Files (x86)/Steam/steamapps/common/Dwarf Fortress')
    out = set()
    for f in glob.glob(d + '/data/vanilla/**/*.txt', recursive=True) + glob.glob(d + '/mods/**/*.txt', recursive=True):
        try:
            out.update(re.findall(r'\[CREATURE:([^\]]+)\]', open(f, encoding='cp437').read()))
        except OSError:
            pass
    return out


def split_tokens(text, known):
    """space-separated tokens, rejoining words where the longest run of them is a known token"""
    w, out, i = text.split(), [], 0
    while i < len(w):
        for j in range(min(len(w), i + 4), i, -1):
            if ' '.join(w[i:j]) in known or j == i + 1:
                out.append(' '.join(w[i:j])); i = j
                break
    return out


def casts(path):
    """{(layer, season): set(tokens)} from `cast status`"""
    out, known = {}, raw_tokens()
    for line in open(path, encoding='utf-8', errors='replace'):
        m = re.match(r'^\s+(land|water|cavern)\s+(\w+)\s+\d+\+\d+\s+seed\s+(.*)$', line.rstrip())
        if m:
            members, _, vermin = m.group(3).partition('|')
            toks = split_tokens(members, known)[1:]  # first token is the seed
            out[(m.group(1), m.group(2))] = set(toks) | set(split_tokens(vermin, known))
    return out


def main():
    d = sys.argv[1]
    C = casts(d + '/casts-start.txt')
    ev = fill_removed(read(d + '/events.tsv'))
    arr = collections.Counter()
    leaks = collections.Counter()
    for r in ev:
        if r['event'] != 'ARRIVE':
            continue
        L = r.get('tlayer')
        if L not in ('land', 'water', 'cavern'):
            continue
        s = SEASONS[(int(r['tick']) % TPY) // ST]
        cast = C.get((L, s), set())
        ok = r['race'] in cast
        arr[(L, s, ok)] += 1
        if not ok:
            leaks[(L, s, r['race'])] += 1
    print('# %s: arrivals against the season cast' % d)
    print('| layer | season | arrivals | in the cast | not in the cast |')
    print('|---|---|---|---|---|')
    for (L, s) in sorted({(a, b) for a, b, _ in arr}):
        t, ok = arr[(L, s, True)] + arr[(L, s, False)], arr[(L, s, True)]
        print('| %s | %s | %d | %d | %d |' % (L, s, t, ok, t - ok))
    if leaks:
        print('\nnot in the cast (layer, season, species, units):')
        for (L, s, race), n in leaks.most_common(30):
            print('  %s %s %s %d' % (L, s, race, n))
    led = open(d + '/ledger.txt', encoding='utf-8', errors='replace').read().splitlines() if __import__('os').path.exists(d + '/ledger.txt') else []
    # who brought each arrival: the ledger says it (the recorder's kind does not: every arrival is 'wild' until the
    # tool adopts it ~200 ticks later). 'drawn into the <body>' = the tool's draw; 'xN arrived' = a DF wave it found.
    # An off-cast species is marked when the ledger shows it standing in for an exhausted cast member that season.
    stand = {}
    for l in led:
        m = re.match(r'^y\d+\s+(\w+)\s+\d+\s+edit\s+(\w+)\s+(.+?) exhausted \(stock 0\): (.+?) takes its niche', l)
        if m:
            stand[(m.group(2), m.group(1), m.group(4))] = m.group(3)
    src = collections.Counter()
    for l in led:
        m = re.match(r'^y\d+\s+(\w+)\s+\d+\s+arrive\s+(\w+)\s+(.+?) x(\d+) (drawn|arrived)', l)
        if not m:
            continue
        s, L, race, n, how = m.group(1), m.group(2), m.group(3), int(m.group(4)), m.group(5)
        who = 'tool' if how == 'drawn' else 'DF'
        where = 'cast' if race in C.get((L, s), set()) else ('stand-in' if (L, s, race) in stand else 'OFF')
        src[(L, s, who, where, race)] += n
    print('\narrivals by source (ledger; OFF = neither cast nor a logged stand-in):')
    print('| layer | season | source | cast | stand-in | OFF |')
    print('|---|---|---|---|---|---|')
    for (L, s, who) in sorted({k[:3] for k in src}):
        row = {w: sum(v for k, v in src.items() if k[:3] == (L, s, who) and k[3] == w) for w in ('cast', 'stand-in', 'OFF')}
        print('| %s | %s | %s | %d | %d | %d |' % (L, s, who, row['cast'], row['stand-in'], row['OFF']))
    for k, v in sorted(src.items()):
        if k[3] != 'cast':
            print('  %s %s %s %s %s x%d%s' % (k[0], k[1], k[2], k[3], k[4], v,
                                             (' (for %s)' % stand[(k[0], k[1], k[4])]) if k[3] == 'stand-in' else ''))
    turn = [l for l in led if 'season cast:' in l]
    print('\nseason turnover (ledger): %d line(s)' % len(turn))
    for l in turn[:6]:
        print('  ' + l[:220])
    try:
        P = read(d + '/pairs.tsv')
    except FileNotFoundError:
        P = []
    src = collections.Counter(p['source'] for p in P)
    print('\nrelation pairs: tool wrote %d species pair(s); live now %d (%d of them DF\'s own)' % (
        src['tool'], src['live-tool'] + src['live-df'], src['live-df']))
    for p in [p for p in P if p['source'] == 'live-df'][:15]:
        print('  DF: %s - %s (%s unit pairs)' % (p['predator'], p['prey'], p['n']))


if __name__ == '__main__':
    main()
