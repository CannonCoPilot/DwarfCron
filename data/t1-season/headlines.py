#!/usr/bin/env python3
"""One block of headline numbers per fort for the test item 1 report: headlines.py DIR [DIR...]"""
import collections, csv, re, sys
UZ = 8
def read(p):
    with open(p, newline='', encoding='cp437') as f:
        return [r for r in csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE) if None not in r.values()]
for d in sys.argv[1:]:
    ev, s = read(d + '/events.tsv'), read(d + '/samples.tsv')
    und = lambda x: x['z'] not in ('-1', '') and int(x['z']) <= UZ and x['layer'] == 'underground'
    ev = [x for x in ev if not und(x)]
    c = collections.Counter(x['event'] for x in ev)
    die = [x for x in ev if x['event'] == 'DIE']
    k = collections.Counter()
    for x in die:
        m = re.search(r'killer (\S+)', x['detail']); k[m.group(1) if m else '?'] += 1
    arr = [x for x in ev if x['event'] == 'ARRIVE']
    top = collections.Counter(x['race'] for x in arr).most_common(8)
    pets = collections.Counter(x['race'] for x in die if x['kind'] == 'pet/livestock')
    sumtxt = open(d + '/summary.md', encoding='utf-8', errors='replace').read()
    jm = re.search(r'## Realm jumps.*?\n\n(.*?)\n', sumtxt, re.S)
    print('== %s' % d)
    print('  arrivals %d (surface %d, caverns %d), left %d, died %d (caverns %d), adopted into groups %d' % (
        c['ARRIVE'], sum(x['layer'] != 'underground' for x in arr), sum(x['layer'] == 'underground' for x in arr), c['LEAVE'],
        len(die), sum(x['layer'] == 'underground' for x in die), sum(1 for x in ev if x['event'] == 'KIND' and x['detail'] == 'wild -> wild-group')))
    print('  wild on map %s -> %s, in groups %s -> %s, fps min %s' % (s[0]['wild'], s[-1]['wild'], s[0]['wild_in_groups'], s[-1]['wild_in_groups'], min(int(x['fps']) for x in s)))
    print('  top arrivals: ' + ', '.join('%s %d' % kv for kv in top))
    print('  top killers: ' + ', '.join('%s %d' % kv for kv in k.most_common(8)))
    print('  fort animals lost: ' + (', '.join('%s %d' % kv for kv in pets.most_common()) or 'none'))
    print('  realm jumps: ' + (jm.group(1) if jm else '?'))
