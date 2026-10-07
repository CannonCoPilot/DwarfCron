#!/usr/bin/env python3
"""Aggregate one fort's test-item-1 record into report data (JSON): demographics, interactions, timings, roster.

    report_data.py DIR > DIR/report.json

DIR holds the recorder TSVs (events, positions, reports, samples), ledger.txt and, when dumped, roster.tsv.
Underworld residents (DF's sealed demons: any DEMON_ race, or z <= 8 underground) are counted apart from the fort's wildlife.
"""
import collections
import csv
import json
import os
import re
import sys

from analyze import fill_removed

TPY, SEASON_T, DAY_T = 403200, 100800, 1200
SEASONS = ['spring', 'summer', 'autumn', 'winter']
UZ = 8


def read(p):
    if not os.path.exists(p):
        return []
    with open(p, newline='', encoding='cp437') as f:
        return [r for r in csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE) if None not in r.values()]


def day_of(t):
    """day index from the start of spring (spring d1 = 0)"""
    return (int(t) % TPY) // DAY_T


def label(day):
    return '%s %d' % (SEASONS[day // 84], day % 84 + 1)


ATTACK = re.compile(r"^(?:The |An? )?(.+?) (bites|scratches|kicks|punches|gores|claws|stings|strikes|pecks|butts|"
                    r"headbutts|grabs|latches on|attacks|charges at|rams|slams into|shakes) (?:the |an? )?(.+?)"
                    r"(?: in the | by the |,| around| and|!|\.|$)")


def main():
    d = sys.argv[1]
    ev, smp, rep = fill_removed(read(d + '/events.tsv')), read(d + '/samples.tsv'), read(d + '/reports.tsv')
    under = lambda r: r['race'].startswith('DEMON_') or (r['z'] not in ('-1', '') and int(r['z']) <= UZ and r['layer'] == 'underground')
    world = [r for r in ev if not under(r) and r['event'] != 'SAMPLE_START']
    out: dict = {'fort': os.path.basename(d.rstrip('/'))}
    t0, t1 = int(smp[0]['tick']), int(smp[-1]['tick'])
    out['span'] = {'from': label(day_of(t0)), 'to': label(day_of(t1)), 'ticks': t1 - t0, 'samples': len(smp)}
    out['underworld'] = dict(collections.Counter(r['race'] for r in ev if under(r) and r['event'] in ('PRESENT', 'ARRIVE')))
    # demographics per species: present at start, arrived, left, died, alive at the end (from the last state)
    sp = collections.defaultdict(lambda: collections.Counter())
    state, kind_of, layer_of = {}, {}, {}
    for r in world:
        k = (r['race'])
        e = r['event']
        if e == 'PRESENT':
            sp[k]['start'] += 1; state[r['id']] = 'here'
        elif e == 'ARRIVE':
            sp[k]['arrived'] += 1; state[r['id']] = 'here'
        elif e == 'LEAVE':
            sp[k]['left'] += 1; state[r['id']] = 'gone'
        elif e == 'RETURN':
            sp[k]['returned'] += 1; state[r['id']] = 'here'
        elif e == 'DIE':
            sp[k]['died'] += 1; state[r['id']] = 'dead'
        elif e == 'KIND' and r['detail'] == 'wild -> wild-group':
            sp[k]['grouped'] += 1
        if r['race'] != '?':
            kind_of.setdefault(r['id'], r['kind'] if r['kind'] != 'wild-group' else 'wild')
            layer_of.setdefault(r['id'], r['layer'])
            race_of = r['race']
            state.setdefault('race:' + r['id'], race_of)
    for uid, st in list(state.items()):
        if uid.startswith('race:'):
            continue
        if st == 'here':
            sp[state.get('race:' + uid, '?')]['end'] += 1
    species = []
    for race, c in sp.items():
        kinds = collections.Counter(kind_of[i] for i in kind_of if state.get('race:' + i) == race)
        layers = collections.Counter(layer_of[i] for i in layer_of if state.get('race:' + i) == race)
        species.append({'race': race, 'kind': kinds.most_common(1)[0][0] if kinds else '?',
                        'layer': layers.most_common(1)[0][0] if layers else '?', **{k: c[k] for k in
                        ('start', 'arrived', 'left', 'returned', 'died', 'grouped', 'end')}})
    species.sort(key=lambda s: -(s['start'] + s['arrived']))
    out['species'] = species
    # kills: killer -> victim, and causes
    kills, causes = collections.Counter(), collections.Counter()
    for r in world:
        if r['event'] != 'DIE':
            continue
        m = re.search(r'cause (\S+); killer (.+?)(?: #\d+)?$', r['detail'])
        if m:
            causes[m.group(1)] += 1
            kills[(m.group(2), r['race'])] += 1
    out['kills'] = [{'killer': a, 'victim': b, 'n': n} for (a, b), n in kills.most_common()]
    out['death_causes'] = dict(causes)
    # attacks from the combat reports (first line of each burst; names as DF writes them)
    att, seen = collections.Counter(), set()
    for r in rep:
        txt = r.get('text') or ''
        m = ATTACK.match(txt)
        if not m:
            continue
        key = (r['tick'], m.group(1), m.group(3))
        if key in seen:
            continue
        seen.add(key)
        att[(m.group(1).lower(), m.group(3).lower())] += 1
    out['attacks'] = [{'attacker': a, 'target': b, 'n': n} for (a, b), n in att.most_common(60)]
    out['report_types'] = dict(collections.Counter(r['type'] for r in rep).most_common(20))
    # timings: per day arrivals, departures, deaths (surface / caverns)
    days = collections.defaultdict(lambda: collections.Counter())
    for r in world:
        dd = day_of(r['tick'])
        lay = 'cavern' if r['layer'] == 'underground' else 'surface'
        if r['event'] in ('ARRIVE', 'LEAVE', 'DIE'):
            days[dd][r['event'].lower() + '_' + lay] += 1
    out['days'] = [{'day': dd, 'label': label(dd), **days[dd]} for dd in sorted(days)]
    out['first_seen'] = {}
    for r in world:
        if r['event'] == 'ARRIVE' and r['race'] not in out['first_seen']:
            out['first_seen'][r['race']] = label(day_of(r['tick']))
    # population over time (every 1,000 ticks)
    out['series'] = [{'day': round(((int(s['tick']) % TPY) / DAY_T), 2), 'wild': int(s['wild']), 'grouped': int(s['wild_in_groups']),
                      'pets': int(s['pets_livestock']), 'fps': int(s['fps'])} for s in smp[::10] + ([smp[-1]] if (len(smp) - 1) % 10 else [])]
    out['fps_min'] = min(int(s['fps']) for s in smp)
    out['fps_median'] = sorted(int(s['fps']) for s in smp)[len(smp) // 2]
    # the tool's ledger: actions by kind and by day, plus the lines worth quoting
    led = []
    lp = d + '/ledger.txt'
    if os.path.exists(lp):
        for line in open(lp, encoding='utf-8', errors='replace'):
            m = re.match(r'^y(\d+) (\w+) +(\d+) +(\w+)\s+(\S+)\s+(.*)$', line.rstrip('\n'))
            if m:
                led.append({'season': m.group(2), 'day': int(m.group(3)), 'kind': m.group(4), 'layer': m.group(5), 'text': m.group(6)})
    out['ledger_kinds'] = dict(collections.Counter(l['kind'] for l in led).most_common())
    out['ledger_from'] = ('%s %d' % (led[0]['season'].lower(), led[0]['day'])) if led else None
    # teleports between a cavern and the surface: the layer changes and the unit moved > 15 levels within 1,000 ticks
    last, cross = {}, 0
    for r in read(d + '/positions.tsv'):
        k = r['id']
        if k in last and r['z'] not in ('-1', '') and last[k]['z'] not in ('-1', ''):
            if abs(int(r['z']) - int(last[k]['z'])) > 15 and int(r['tick']) - int(last[k]['tick']) <= 1000 and \
                    (last[k]['layer'] == 'underground') != (r['layer'] == 'underground'):
                cross += 1
        last[k] = r
    out['jumps_cross'] = cross
    out['ledger_quotes'] = {k: [l['season'] + ' ' + str(l['day']) + ': ' + l['text'] for l in led if l['kind'] == k][:6]
                            for k in ('wave', 'arrive', 'dismiss', 'eco', 'ecology', 'panic', 'lead', 'coupling', 'sweep', 'edit', 'season', 'cavern', 'bodies')}
    draws = collections.Counter()
    for l in led:
        m = re.match(r'drew (.+?) x(\d+) into the (\w+)', l['text'])
        if l['kind'] == 'wave' and m:
            draws[(m.group(1), m.group(3))] += int(m.group(2))
    out['water_draws'] = [{'species': a, 'body': b, 'n': n} for (a, b), n in draws.most_common()]
    # the season change: species whose summer stock was exhausted and the off-season species given their niche, and the
    # seasons lent in spring that went back (ledger lines on the day the summer roster was applied)
    sday = next(((l['season'], l['day']) for l in led if l['kind'] == 'season' and 'Summer roster applied' in l['text']), None)
    out['season_change'] = None
    if sday:
        sw_, back = [], 0
        for l in led:
            if (l['season'], l['day']) != sday or l['kind'] != 'edit':
                continue
            m = re.match(r'(.+?) exhausted \(stock 0\): (.+?) takes its niche', l['text'])
            if m:
                sw_.append({'layer': l['layer'], 'gone': m.group(1), 'taker': m.group(2)})
            m = re.search(r'exhaustion: (\d+) borrowed season', l['text'])
            if m:
                back = int(m.group(1))
        out['season_change'] = {'day': '%s %d' % (sday[0].lower(), sday[1]), 'swaps': sw_, 'given_back': back}
    # roster (when dumped): per layer, species and seasons; set against the arrivals
    rp = d + '/roster.tsv'
    sp0 = d + '/roster-start.tsv'
    if os.path.exists(rp) and os.path.exists(sp0):
        a = {(r['layer'], r['token']): r['seasons'] for r in read(sp0)}
        b = {(r['layer'], r['token']): r['seasons'] for r in read(rp)}
        out['roster_diff'] = [{'layer': k[0], 'token': k[1], 'before': a.get(k, '-'), 'after': b.get(k, '-')}
                              for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]
    if os.path.exists(rp):
        ro = read(rp)
        out['roster'] = ro
        arrived = {s['race'] for s in species if s['arrived'] > 0}
        out['roster_vs_arrivals'] = {
            'on_roster_arrived': sorted({r['token'] for r in ro} & arrived),
            'arrived_not_on_roster': sorted(arrived - {r['token'] for r in ro}),
        }
    json.dump(out, sys.stdout, indent=1)


if __name__ == '__main__':
    main()
