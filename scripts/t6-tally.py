#!/usr/bin/env python3
"""T6 — the v5.8 gate, scored the same way every time.

Five criteria, and the fifth is the one that failed on 18 September's first run: an
out-of-season arrival. That run drew a carnotaurus assigned to autumn and winter into
spring fifteen times in one replicate and twenty-one in the other, every one inside a
migratory coupling window, because opening a prey's predators gave their entries ten
stock without consulting the roster. Scoring it by hand is how it stayed invisible for
four versions, so it is scored here.

    scripts/t6-tally.py [run_dir]     (default: the newest data/experiments/T6/*)

Sources, all written by cx-experiment.py:
  events.tsv  one 'arrival' row per unit, with the absolute tick and the unit's countdown
              -- preferred, because it is exact, per-unit, and written as the run goes
  waves.tsv   one row per wave, written only when the whole run ends (the fallback)
  roster.tsv  the seasons each key was assigned, per replicate
  units.tsv   every wild unit at every sample, with its layer
  events.tsv  the baseline row carries the replicate's opening tick
  log.txt     the sampler's own per-layer line, which is what the TOOL sees
  manifest.json  the sample interval, which bounds how precisely an arrival can be dated

⚠️ An arrival is dated to within ONE SAMPLE INTERVAL, so a sample that straddles a season
boundary cannot say which side of it the animal came on. The first run's fifteen and
twenty-one breaches included three such cases -- an osprey and an alligator in replicate
one, an osprey in replicate two -- and for water-layer placements the leave countdown
settles them outright: at first sight they read 21,743, 21,743 and 23,047 against a
placement value of 25,000, so all three were placed 1,953 to 3,257 ticks earlier, in
WINTER, in season. They are reported as boundary cases, not breaches. The real counts for
that run were thirteen and twenty, every one a carnotaurus deep inside spring and summer.

Two sources are read for the water layer on purpose. The sampler counts a unit as water
when its population reference carries a feature index, which is the test the water job
itself applies; the harness's units.tsv classifies independently. On 18 September's first
run they disagreed at the bottom of the range -- the sampler's floor was nine, units.tsv's
seven -- so both are printed and a disagreement is called out rather than averaged away.
"""
import csv, re, sys, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TICKS_PER_SEASON, TICKS_PER_YEAR = 100800, 403200
SEASON = ['spring', 'summer', 'autumn', 'winter']
# waves.tsv / units.tsv say 'feature' where the roster says 'water'; the roster key for a
# surface creature is the bare token (so every pre-v5 config still loads).
KEY_PREFIX = {'surface': '', 'feature': 'water:', 'cavern': 'cavern:'}


def read(run: Path, name):
    p = run / name
    if not p.is_file():
        return []
    with p.open() as fh:
        return list(csv.DictReader(fh, delimiter='\t'))


def season_of(abs_tick):
    return (abs_tick % TICKS_PER_YEAR) // TICKS_PER_SEASON


def arrivals_for(run, waves):
    """One row per arriving unit: {arm, rep, abs, species, layer, countdown, n}.

    events.tsv is preferred: it carries the absolute tick and the unit's own countdown, one
    row per unit, and it is written as the run goes -- so a replicate can be scored while the
    next one is still running. waves.tsv only lands when the whole run ends.
    """
    out = []
    for e in read(run, 'events.tsv'):
        if e['event'] != 'arrival':
            continue
        d = e['detail'].split()
        kv = dict(p.split('=', 1) for p in d[1:] if '=' in p)
        out.append(dict(arm=e['arm'], rep=e['rep'], abs=int(e['abs_tick']), species=d[0],
                        layer=kv.get('layer', 'surface'), countdown=kv.get('countdown'), n=1))
    if out:
        return out, 'events.tsv'
    base = {}
    for e in read(run, 'events.tsv'):
        if e['event'] == 'baseline':
            base[(e['arm'], e['rep'])] = int(e['abs_tick'])
    for w in waves:
        b = base.get((w['arm'], w['rep']))
        if b is None:
            continue
        out.append(dict(arm=w['arm'], rep=w['rep'], abs=b + int(w['listed_rel']), species=w['species'],
                        layer=w['layer'], countdown=w['countdown_min'], n=int(w['n'] or 1)))
    return out, 'waves.tsv'


def placed_at(w, first_abs, countdown):
    """A water placement carries our own leave countdown, so its age at first sight dates
    it exactly. Returns the absolute tick it was placed, or None for a layer DF waves."""
    if w['layer'] != 'feature':
        return None
    try:
        age = countdown - int(w['countdown'])
    except (TypeError, ValueError):
        return None
    return first_abs - age if 0 < age < countdown else None


def tally(run: Path):
    import json
    man = json.loads((run / 'manifest.json').read_text()) if (run / 'manifest.json').is_file() else {}
    interval = int(man.get('sample_every') or 5000)
    countdown = 25000                                    # cfg.water.countdown's default
    for arm in man.get('arms', []):
        for cmd in arm.get('pre', []):
            if 'cfg.water.countdown=' in cmd:
                countdown = int(cmd.split('cfg.water.countdown=')[1].split(';')[0].strip())
    waves, roster = read(run, 'waves.tsv'), read(run, 'roster.tsv')
    arrivals_all, arr_src = arrivals_for(run, waves)
    units, events = read(run, 'units.tsv'), read(run, 'events.tsv')
    if not arrivals_all:
        sys.exit(f'{run}: no arrivals recorded in events.tsv or waves.tsv')

    # the tick each replicate opened at, so a relative arrival becomes an absolute one
    base = {}
    for e in events:
        if e['event'] == 'baseline':
            base[(e['arm'], e['rep'])] = int(e['abs_tick'])

    # seasons assigned per replicate and key; an unassigned key is UNRESTRICTED, not banned
    seasons = collections.defaultdict(dict)
    for r in roster:
        if r['allowed'] not in ('1', 'True', 'true'):
            continue
        s = [int(x) for x in r['seasons'].split(',') if x.strip() != '']
        if s:
            seasons[(r['arm'], r['rep'])][r['token']] = s

    # wild units present per layer at each sample
    present = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for u in units:
        if u['dead'] == '1' or u['inactive'] == '1' or u.get('wild') != '1':
            continue
        present[(u['arm'], u['rep'])][int(u['tick'])][u['layer']] += 1

    # The sampler's own line is the tool's view of the map, and the only place the citizen
    # count is written at all. Attribute each line to the replicate whose header preceded it.
    sampled, citizens = collections.defaultdict(list), collections.defaultdict(list)
    cur = None
    head = re.compile(r'== \S+ arm=(\S+) rep=(\d+)')
    line = re.compile(r't6 layers: surface=(\d+) water=(\d+) cavern=(\d+) citizens=(\d+)')
    for raw in (run / 'log.txt').read_text(errors='replace').splitlines():
        h = head.search(raw)
        if h:
            cur = (h.group(1), h.group(2))
            continue
        m = line.search(raw)
        if m and cur:
            surf, wat, cav, cz = (int(x) for x in m.groups())
            sampled[cur].append({'surface': surf, 'feature': wat, 'cavern': cav})
            citizens[cur].append(cz)

    verdicts = {}
    for key in sorted(base):
        arm, rep = key
        b, rost = base[key], seasons.get(key, {})
        # --- criterion 5: arrivals against the roster's seasons
        offenders, boundary, arrivals = collections.Counter(), collections.Counter(), 0
        for w in arrivals_all:
            if (w['arm'], w['rep']) != key:
                continue
            n = w['n']
            arrivals += n
            rk = KEY_PREFIX.get(w['layer'], '') + w['species']
            want = rost.get(rk)
            if not want:
                continue                       # unassigned: unrestricted by design
            first = w['abs']
            s = season_of(first)
            if s in want:
                continue
            label = (w['species'], w['layer'], SEASON[s], ','.join(SEASON[x] for x in want))
            # Our own placements date themselves through the countdown they carry.
            when = placed_at(w, first, countdown)
            if when is not None and season_of(when) in want:
                boundary[label + (f'placed {first - when} ticks earlier, in {SEASON[season_of(when)]}',)] += n
                continue
            # Otherwise: could the sample that found it straddle a season boundary?
            prev = season_of(first - interval)
            if prev != s and prev in want:
                boundary[label + (f'first seen {first % TICKS_PER_SEASON} ticks into the season, '
                                  f'within one {interval}-tick sample of the flip',)] += n
                continue
            offenders[label] += n

        # --- criteria 1-3: what each layer held across the run, as the tool saw it
        def band(seq):
            return (min(seq), sum(seq) / len(seq), max(seq)) if seq else (0, 0.0, 0)
        layers = {lay: band([c[lay] for c in sampled.get(key, [])])
                  for lay in ('feature', 'surface', 'cavern')}
        # independent cross-check on the water layer from the harness's own unit dump
        xcheck = band([c['feature'] for c in present[key].values()])

        cz = citizens.get(key, [])
        verdicts[key] = dict(arrivals=arrivals, offenders=offenders, boundary=boundary,
                             layers=layers, xcheck=xcheck,
                             citizens=(cz[0], cz[-1]) if cz else (None, None),
                             samples=len(sampled.get(key, [])))
    return verdicts, arr_src


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    run = Path(arg) if arg else max((ROOT / 'data/experiments/T6').glob('*'), key=lambda p: p.name)
    print(f'T6 — {run.name}')
    v, src = tally(run)
    print(f'(arrivals read from {src})\n')
    gate = True
    for (arm, rep), d in sorted(v.items()):
        water, surf, cav = d['layers']['feature'], d['layers']['surface'], d['layers']['cavern']
        c0, c1 = d['citizens']
        ok_water = water[0] > 0
        ok_arr = surf[1] > 0 and cav[1] > 0
        ok_season = not d['offenders']
        ok_fort = c1 is not None and c1 > 0
        gate = gate and ok_water and ok_arr and ok_season and ok_fort
        print(f'  {arm} rep {rep}  ({d["samples"]} samples, {d["arrivals"]} arrivals)')
        print(f'    water   min {water[0]:3d}  mean {water[1]:5.1f}  max {water[2]:3d}   '
              f'{"PASS never empty" if ok_water else "FAIL the layer emptied"}')
        xc = d['xcheck']
        if (xc[0], round(xc[1], 1), xc[2]) != (water[0], round(water[1], 1), water[2]):
            print(f'      cross-check (units.tsv): min {xc[0]} mean {xc[1]:.1f} max {xc[2]} '
                  f'— the two counts disagree; the figure above is the tool\'s own')
        print(f'    surface min {surf[0]:3d}  mean {surf[1]:5.1f}  max {surf[2]:3d}')
        print(f'    cavern  min {cav[0]:3d}  mean {cav[1]:5.1f}  max {cav[2]:3d}   '
              f'{"PASS both layers kept arriving" if ok_arr else "FAIL a layer stopped"}')
        print(f'    citizens {c0} -> {c1}   {"PASS the fort lived" if ok_fort else "FAIL the fort died"}')
        if d['boundary']:
            print(f'    at a season boundary (not breaches): {sum(d["boundary"].values())}')
            for (sp, lay, got, want, why), n in d['boundary'].most_common():
                print(f'      {n:4d}  {sp} ({lay}) first seen in {got}, assigned {want} — {why}')
        if ok_season:
            print('    out of season: 0   PASS')
        else:
            total = sum(d['offenders'].values())
            print(f'    out of season: {total}   FAIL')
            for (sp, lay, got, want), n in d['offenders'].most_common():
                print(f'      {n:4d}  {sp} ({lay}) arrived in {got}; assigned {want}')
        print()
    print('GATE: ' + ('PASS — every criterion in every replicate' if gate
                      else 'FAIL — see the criteria marked FAIL above'))
    print('(the save-identical check is the harness\'s own; read it from log.txt)')
    return 0 if gate else 1


if __name__ == '__main__':
    sys.exit(main())
