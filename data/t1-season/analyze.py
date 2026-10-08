#!/usr/bin/env python3
"""Summarize one fort's animal activity from sw-t1-recorder output (test item 1, 7 Oct 2026).

    analyze.py DIR [--underworld-z N]   DIR holds events.tsv, positions.tsv, reports.tsv, samples.tsv, ledger.txt

Writes DIR/summary.md and prints it. Units at z <= the underworld top (default: the lowest 9 levels, where DF keeps
its sealed demon population) are counted apart as underworld residents, not as fort wildlife.
"""
import collections
import csv
import os
import re
import sys

TPY = 403200
SEASONS = ['spring', 'summer', 'autumn', 'winter']


def read(path):
    with open(path, newline='', encoding='cp437') as f:
        # a file copied while the recorder writes can end in a half line: drop rows with a missing field
        return norm([r for r in csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE) if None not in r.values()])


def norm(rows):
    """recorders from 7 Oct evening write the tool's layer for wild animals (land, water, cavern, deep): keep it as 'tlayer' and
    map 'layer' back to the old surface/underground, with deep at z 0 so every underworld test catches it"""
    for r in rows:
        L = r.get('layer')
        if L in ('land', 'water', 'cavern', 'deep'):
            r['tlayer'] = L
            r['layer'] = 'surface' if L in ('land', 'water') else 'underground'
            if L == 'deep':
                r['z'] = '0'
    return rows


def fill_removed(ev):
    """A unit DF drops from its unit vector is logged LEAVE with race '?' (it is gone when the recorder looks): name it, and
    place it, from the unit's last earlier event. A dead unit's removal is DF clearing the body, not a departure: drop it."""
    last, dead, out = {}, set(), []
    for r in ev:
        if r['event'] == 'LEAVE' and r['race'] == '?':
            if r['id'] in dead:
                continue
            k = last.get(r['id'])
            if k:
                r = dict(r, **{f: k[f] for f in ('race', 'caste', 'kind', 'x', 'y', 'z', 'layer')})
        elif r['race'] not in ('?', ''):
            last[r['id']] = r
        if r['event'] == 'DIE':
            dead.add(r['id'])
        out.append(r)
    return out


def when(t):
    t = int(t)
    yt = t % TPY
    return '%s d%d' % (SEASONS[yt // 100800], (yt % 100800) // 1200 + 1)


def main():
    d = sys.argv[1]
    uz = 8
    if '--underworld-z' in sys.argv:
        uz = int(sys.argv[sys.argv.index('--underworld-z') + 1])
    ev = fill_removed(read(os.path.join(d, 'events.tsv')))
    smp = read(os.path.join(d, 'samples.tsv'))
    rep = read(os.path.join(d, 'reports.tsv'))
    out = []
    W = out.append
    name = os.path.basename(d.rstrip('/'))
    t0, t1 = int(smp[0]['tick']), int(smp[-1]['tick'])
    W('# %s: animal activity, %s to %s (%d ticks, %d samples every 100 ticks)' % (name, when(t0), when(t1), t1 - t0, len(smp)))
    W('')
    under = lambda r: r['race'].startswith('DEMON_') or (r['z'] not in ('-1', '') and int(r['z']) <= uz and r['layer'] == 'underground')
    pres = [r for r in ev if r['event'] == 'PRESENT']
    W('## On the map at the start')
    W('')
    c = collections.Counter((r['kind'], r['race']) for r in pres if not under(r))
    for kind in ('wild', 'wild-group', 'pet/livestock', 'visitor', 'merchant', 'invader', 'other'):
        rows = sorted(((n, race) for (k, race), n in c.items() if k == kind), reverse=True)
        if rows:
            W('- **%s** (%d): %s' % (kind, sum(n for n, _ in rows), ', '.join('%s %d' % (race, n) for n, race in rows)))
    u0 = collections.Counter(r['race'] for r in pres if under(r))
    if u0:
        W('- underworld residents (sealed: DEMON_ races, or z <= %d): %s' % (uz, ', '.join('%s %d' % kv for kv in u0.most_common())))
    W('')
    W('## Arrivals during the run')
    W('')
    arr = [r for r in ev if r['event'] == 'ARRIVE']
    ca = collections.Counter((r['race'], r['kind'], r['layer']) for r in arr if not under(r))
    W('| species | kind | layer | arrived | first |')
    W('|---|---|---|---|---|')
    first = {}
    for r in arr:
        first.setdefault((r['race'], r['kind'], r['layer']), r['tick'])
    for (race, kind, layer), n in sorted(ca.items(), key=lambda kv: (-kv[1], kv[0])):
        W('| %s | %s | %s | %d | %s |' % (race, kind, layer, n, when(first[(race, kind, layer)])))
    ua = collections.Counter(r['race'] for r in arr if under(r))
    if ua:
        W('')
        W('Underworld residents that appeared (DF\'s own, below the seal): ' + ', '.join('%s %d' % kv for kv in ua.most_common()))
    W('')
    W('## Departures')
    W('')
    lv = [r for r in ev if r['event'] == 'LEAVE' and not under(r)]
    rt = [r for r in ev if r['event'] == 'RETURN' and not under(r)]
    cl = collections.Counter((r['race'], r['kind']) for r in lv)
    W('%d left the map (%d came back later).' % (len(lv), len(rt)) + (' ' + ', '.join('%s (%s) %d' % (k[0], k[1], n) for k, n in cl.most_common()) if cl else ''))
    W('')
    W('## Deaths')
    W('')
    die = [r for r in ev if r['event'] == 'DIE']
    W('| when | species | kind | layer | cause and killer |')
    W('|---|---|---|---|---|')
    for r in die:
        W('| %s | %s | %s | %s | %s |' % (when(r['tick']), r['race'], r['kind'], r['layer'] + (' (underworld)' if under(r) else ''), r['detail']))
    kills = collections.Counter()
    for r in die:
        m = re.search(r'killer (.+?)(?: #\d+)?$', r['detail'])
        if m and m.group(1) != 'none':
            kills[(m.group(1), r['race'])] += 1
    if kills:
        W('')
        W('Predation and kills (killer -> victim): ' + ', '.join('%s -> %s %d' % (k[0], k[1], n) for k, n in kills.most_common()))
    W('')
    W('## Realm jumps (a unit more than 15 levels from where it was 1,000 ticks before)')
    W('')
    pos = read(os.path.join(d, 'positions.tsv'))
    last, jumps = {}, []
    for r in pos:
        k = r['id']
        if not r.get('z') or not r.get('tick'):
            continue
        if k in last and r['z'] not in ('-1', '') and last[k]['z'] not in ('-1', ''):
            dz = int(r['z']) - int(last[k]['z'])
            if abs(dz) > 15 and int(r['tick']) - int(last[k]['tick']) <= 1000:
                # across realms: the recorded layer changes between underground (a cavern) and the surface or its water
                cross = (last[k]['layer'] == 'underground') != (r['layer'] == 'underground')
                jumps.append('- %s%s #%s %s: %s,%s,%s (%s) -> %s,%s,%s (%s)' % ('**CAVERN<->SURFACE** ' if cross else '', when(r['tick']), k, r['race'],
                             last[k]['x'], last[k]['y'], last[k]['z'], last[k]['layer'], r['x'], r['y'], r['z'], r['layer']))
        last[k] = r
    nx = sum('CAVERN<->SURFACE' in j for j in jumps)
    W(('%d jump(s); %d between a cavern and the surface.' % (len(jumps), nx)) if jumps else 'None.')
    out.extend(jumps[:60])
    W('')
    W('## The tool\'s groups')
    W('')
    kd = [r for r in ev if r['event'] == 'KIND' and r['detail'] == 'wild -> wild-group']
    W('%d wild units were taken into the tool\'s groups: ' % len(kd) + ', '.join('%s %d' % kv for kv in collections.Counter(r['race'] for r in kd).most_common()))
    W('')
    W('## Wild numbers over time')
    W('')
    W('| when | wild on the map | in the tool\'s groups | pets/livestock | fps |')
    W('|---|---|---|---|---|')
    step = max(1, len(smp) // 12)
    for s in smp[::step] + ([smp[-1]] if (len(smp) - 1) % step else []):
        W('| %s | %s | %s | %s | %s |' % (when(s['tick']), s['wild'], s['wild_in_groups'], s['pets_livestock'], s['fps']))
    W('')
    W('## Reports about animals')
    W('')
    tc = collections.Counter(r['type'] for r in rep)
    W('%d reports in all; by type: %s' % (len(rep), ', '.join('%s %d' % kv for kv in tc.most_common(12))))
    animalish = re.compile(r'(bites|scratches|kicks|gores|charges|attacks|hunt|struck down|has been killed|slain|dies|devoured|'
                           r'ambush|flees|eats|catch|caught|grabs|latches|pounces|sinks|collides)', re.I)
    keep = [r for r in rep if animalish.search(r.get('text') or '')]
    # combat reports come in bursts of identical lines; keep the first of each text per burst
    seen, lines = set(), []
    for r in keep:
        k = r['text']
        if k in seen:
            continue
        seen.add(k)
        lines.append('- %s: %s' % (when(r['tick']), k))
    W('%d reports name a hunt, fight or death; the distinct ones (%d):' % (len(keep), len(lines)))
    W('')
    out.extend(lines[:400])
    if len(lines) > 400:
        W('- ... %d more in reports.tsv' % (len(lines) - 400))
    led = os.path.join(d, 'ledger.txt')
    if os.path.exists(led):
        W('')
        W('## The tool\'s ledger for the run')
        W('')
        W('```')
        out.extend(l.rstrip('\n') for l in open(led) if l.strip())
        W('```')
    text = '\n'.join(out) + '\n'
    with open(os.path.join(d, 'summary.md'), 'w') as f:
        f.write(text)
    print(text)


if __name__ == '__main__':
    main()
