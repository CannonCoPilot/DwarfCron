#!/usr/bin/env python3
"""Validate a v7.3 season-cast run: v73_check.py DIR
DIR holds the recorder TSVs, casts-start.txt (`cast status` at the start), ledger.txt and pairs.tsv (`ecology pairs tsv`).
Every arrival on a managed layer is set against that season's cast for its layer: in the cast, or a leak (with the
species and why it might have come). Also: the groups sent off at a season change, and the relation pairs by who set them."""
import collections, csv, os, re, sys
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


def ledger(d):
    """[(season, kind, layer, text)] from the live capture (ledger.tsv: every entry) or else the end-of-run dump
    (ledger.txt: the tool's newest 300 only), and whether it is complete"""
    if os.path.exists(d + '/ledger.tsv'):
        out = []
        # plain csv, not read(): norm() rewrites a recorder table's layer column (surface/underground), not the ledger's
        with open(d + '/ledger.tsv', newline='', encoding='cp437') as f:
            rows = list(csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE))
        for r in rows:
            if r['kind'] == 'GAP':
                continue
            t = int(r['tick'])
            out.append((SEASONS[(t % TPY) // ST], r['kind'], r['layer'] or '-', r['text']))
        return out, True
    out = []
    for l in (open(d + '/ledger.txt', encoding='utf-8', errors='replace').read().splitlines() if os.path.exists(d + '/ledger.txt') else []):
        m = re.match(r'^y\d+\s+(\w+)\s+\d+\s+(\w+)\s+(\S+)\s+(.*)$', l)
        if m:
            out.append(m.groups())
    return out, False


def summarize(d, prev=()):
    """the run's numbers: arrivals (recorder units, by cast), arrivals by source (ledger groups), stand-ins, turnover,
    swaps logged before the season's apply, relation pairs. `prev`: earlier runs on the same fort whose ledgers hold
    stand-ins still in force (a swap made at the last boundary)"""
    C = casts(d + '/casts-start.txt')
    ev = fill_removed(read(d + '/events.tsv'))
    led, complete = ledger(d)
    stand = {}
    for x in [y for p in prev for y in ledger(p)[0]] + led:
        m = re.match(r'^(.+?) exhausted \(stock 0\): (.+?) takes its niche', x[3]) if x[1] == 'edit' else None
        if m:
            stand[(x[2], x[0], m.group(2))] = m.group(1)
    arr, leaks = collections.Counter(), collections.Counter()   # arr[(layer, season, True | 'stand-in' | False)]
    for r in ev:
        if r['event'] != 'ARRIVE' or r.get('tlayer') not in ('land', 'water', 'cavern'):
            continue
        L, s = r['tlayer'], SEASONS[(int(r['tick']) % TPY) // ST]
        ok = True if r['race'] in C.get((L, s), set()) else ('stand-in' if (L, s, r['race']) in stand else False)
        arr[(L, s, ok)] += 1
        if ok is not True:
            leaks[(L, s, r['race'])] += 1
    src = collections.Counter()
    for season, kind, L, text in led:
        m = re.match(r'^(.+?) x(\d+) (drawn|arrived)', text) if kind == 'arrive' else None
        if not m:
            continue
        race, n, who = m.group(1), int(m.group(2)), 'tool' if m.group(3) == 'drawn' else 'DF'
        where = 'cast' if race in C.get((L, season), set()) else ('stand-in' if (L, season, race) in stand else 'OFF')
        src[(L, season, who, where, race)] += n
    # a hand-over logged at a season's start before that season's apply is the 300-tick/daily race (fixed sw 6e1ffb2)
    # (counted only where the ledger holds that season's apply line after it: a ledger window opening mid-season has none)
    early, applied, at = collections.Counter(), set(), {}
    for i, (season, kind, L, text) in enumerate(led):
        if kind == 'season' and 'roster applied' in text and season not in at:
            at[season] = i
            applied.add(season)
    for i, (season, kind, L, text) in enumerate(led):
        if kind == 'edit' and 'exhausted (stock 0)' in text and season in at and i < at[season]:
            early[season] += 1
    try:
        P = read(d + '/pairs.tsv')
    except FileNotFoundError:
        P = []
    return {'dir': d, 'arr': arr, 'leaks': leaks, 'src': src, 'stand': stand, 'complete': complete, 'early': early,
            'applied': applied, 'turn': [x[3] for x in led if 'season cast:' in x[3]],
            'pairs': collections.Counter(p['source'] for p in P), 'df_pairs': [p for p in P if p['source'] == 'live-df']}


def main():
    d, prev = sys.argv[1], sys.argv[2:]
    S = summarize(d, prev)
    arr, leaks, src, stand = S['arr'], S['leaks'], S['src'], S['stand']
    print('# %s: arrivals against the season cast (recorder units; births count as arrivals)' % d)
    print('| layer | season | arrivals | in the cast | not in the cast |')
    print('|---|---|---|---|---|')
    for (L, s) in sorted({(a, b) for a, b, _ in arr}):
        ok, si, off = arr[(L, s, True)], arr[(L, s, 'stand-in')], arr[(L, s, False)]
        print('| %s | %s | %d | %d | %d (%d of them stand-ins) |' % (L, s, ok + si + off, ok, si + off, si))
    if leaks:
        print('\nnot in the cast (layer, season, species, units):')
        for (L, s, race), n in leaks.most_common(30):
            print('  %s %s %s %d' % (L, s, race, n))
    print('\narrivals by source (ledger groups%s; OFF = neither cast nor a logged stand-in):' % (
        '' if S['complete'] else ', END-OF-RUN DUMP: the newest 300 entries only'))
    print('| layer | season | source | cast | stand-in | OFF |')
    print('|---|---|---|---|---|---|')
    for (L, s, who) in sorted({k[:3] for k in src}):
        row = {w: sum(v for k, v in src.items() if k[:3] == (L, s, who) and k[3] == w) for w in ('cast', 'stand-in', 'OFF')}
        print('| %s | %s | %s | %d | %d | %d |' % (L, s, who, row['cast'], row['stand-in'], row['OFF']))
    for k, v in sorted(src.items()):
        if k[3] != 'cast':
            print('  %s %s %s %s %s x%d%s' % (k[0], k[1], k[2], k[3], k[4], v,
                                             (' (for %s)' % stand[(k[0], k[1], k[4])]) if k[3] == 'stand-in' else ''))
    print('\nhand-overs logged before their season\'s apply (the race): %s' % (dict(S['early']) or 'none'))
    print('season turnover (ledger): %d line(s)' % len(S['turn']))
    for l in S['turn'][:6]:
        print('  ' + l[:220])
    ps = S['pairs']
    print('\nrelation pairs: tool wrote %d species pair(s); live now %d (%d of them DF\'s own)' % (
        ps['tool'], ps['live-tool'] + ps['live-df'], ps['live-df']))
    for p in S['df_pairs'][:15]:
        print('  DF: %s - %s (%s unit pairs)' % (p['predator'], p['prey'], p['n']))


if __name__ == '__main__':
    main()
