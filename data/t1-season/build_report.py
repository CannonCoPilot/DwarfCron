#!/usr/bin/env python3
"""Build the test-item-1 report page from each fort's report.json: build_report.py OUT.html"""
import base64
import html
import io
import json
import os
import sys

import figures

HERE = os.path.dirname(os.path.abspath(__file__))
FORTS = [
    ('T1_OCEAN_RIVER', 'River + ocean', 'region tile 54,45 (+0,8), 16x16; shrubland with a major river, temperate ocean', 'T1END_OCEAN_RIVER'),
    ('T1_LAKE_RIVER', 'Lake + river', 'tiles 14-15,12-13 (+8,12), 16x16; freshwater lake, marsh with a major river', 'T1END_LAKE_RIVER'),
    ('T1_BROOK', 'Brook', 'tile 51,22, 16x16; conifer forest with a brook', 'T1END_BROOK'),
    ('T1_FALLS', 'River drop (no falls)', 'tile 38,36 (+0,8), 16x16; a major river dropping 11 region levels, in steps', 'T1END_FALLS'),
    ('FALLS_2', 'Waterfall', 'Whitepaged (Volalmorul), embarked by the user, 6x6; a river falling into a gorge', 'T1END_WATERFALL'),
]
E = html.escape


def img_uri(path, crop=None, width=760):
    from PIL import Image
    im = Image.open(path).convert('RGB')
    if crop:
        im = im.crop(crop)
    if im.width > width:
        im = im.resize((width, int(im.height * width / im.width)))
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=82)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()


def chart(fid, series):
    """inline SVG: wild on the map and in the tool's groups, by game day; hover reads the nearest sample"""
    W, H, L, R, T, B = 560, 200, 44, 12, 14, 30
    xs = [p['day'] for p in series]
    ymax = max(max(p['wild'] for p in series), 1)
    step = 100 if ymax > 300 else 50
    top = ((ymax // step) + 1) * step
    x0, x1 = min(xs), max(xs)
    X = lambda d: L + (d - x0) / max(1e-9, x1 - x0) * (W - L - R)
    Y = lambda v: T + (1 - v / top) * (H - T - B)
    def path(key):
        return ' '.join(('M' if i == 0 else 'L') + '%.1f %.1f' % (X(p['day']), Y(p[key])) for i, p in enumerate(series))
    grid = ''.join('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="grid"/><text x="%d" y="%.1f" class="tick" text-anchor="end">%d</text>'
                   % (L, W - R, Y(v), Y(v), L - 6, Y(v) + 4, v) for v in range(0, top + 1, step))
    # x ticks at whole season days: spring 40, 60, 80, summer 1
    xt = ''
    for d in range(int(x0) // 10 * 10 + 10, int(x1) + 1, 10):
        lab = ('Sp %d' % (d + 1)) if d < 84 else ('Su %d' % (d - 83))
        xt += '<text x="%.1f" y="%d" class="tick" text-anchor="middle">%s</text>' % (X(d), H - 10, lab)
    if x0 < 84 <= x1:
        right = X(84) > W - R - 60   # near the right edge the label goes on the line's left
        xt += '<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" class="season"/><text x="%.1f" y="%d" class="tick season-lab" text-anchor="%s">summer</text>' % (
            X(84), X(84), T, H - B, X(84) + (-4 if right else 4), T + 10, 'end' if right else 'start')
    last = series[-1]
    ends = ''.join('<circle cx="%.1f" cy="%.1f" r="4" class="end s%d"/>' % (X(last['day']), Y(last[k]), i + 1) for i, k in enumerate(('wild', 'grouped')))
    data = json.dumps([[round(p['day'], 1), p['wild'], p['grouped'], p['fps']] for p in series])
    return ('<figure class="chart" data-series=\'%s\' data-x0="%s" data-x1="%s" data-top="%d">'
            '<svg viewBox="0 0 %d %d" role="img" aria-label="Wild animals on the map and in the tool\'s groups over the run">%s%s'
            '<path d="%s" class="line s1"/><path d="%s" class="line s2"/>%s'
            '<line class="cross" y1="%d" y2="%d" x1="-10" x2="-10"/><rect class="hit" x="%d" y="%d" width="%d" height="%d"/></svg>'
            '<div class="tip" hidden></div></figure>') % (
        data, x0, x1, top, W, H, grid, xt, path('wild'), path('grouped'), ends, T, H - B, L, T, W - L - R, H - T - B)


def table(head, rows, cls=''):
    h = ''.join('<th%s>%s</th>' % (' class="n"' if i > 0 and n else '', E(c)) for i, (c, n) in enumerate(head))
    b = ''.join('<tr>' + ''.join('<td%s>%s</td>' % (' class="n"' if i > 0 and head[i][1] else '', c) for i, c in enumerate(r)) + '</tr>' for r in rows)
    return '<div class="tw"><table class="%s"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (cls, h, b)


GAP_WHY = {
    'demons': 'DF\'s sealed underworld residents: they count as wild in the recorder, but the tool never manages the underworld',
    'magma': 'magma-sea life (magma crabs, fire imps, magma and fire men): the deep layer is never grouped',
    'sponge': 'sponges: placed like plants in clusters on the sea floor, never counted as groups (by design)',
    'native': 'animals already in the river when the tool loaded: DF stocked them from the region\'s population, not a water feature, so the tool files them as land natives, and land-native adoption is off by default',
    'other': 'other wild units outside a group',
}


def gap_note(d):
    g, gs = d['gap'], d['gap_species']
    total = sum(g.values())
    parts = []
    for k in ('demons', 'magma', 'sponge', 'native', 'other'):
        if g.get(k):
            sp = ', '.join('%s %d' % (r.replace('_', ' ').lower(), n) for r, n in gs[k].items()) if k != 'demons' else ''
            parts.append('<li><b>%d</b> %s%s</li>' % (g[k], E(GAP_WHY[k]), (' (%s)' % E(sp)) if sp else ''))
    return ('<h3>The gap</h3><p class="note">At the last position snapshot %d wild units were on the map and %d of them were in the '
            'tool\'s groups. The other %d:</p><ul class="gap">%s</ul>' % (total, g.get('grouped', 0), total - g.get('grouped', 0), ''.join(parts)))


def fort_section(fid, name, where, save, d):
    sp = d['species']
    tot = lambda k: sum(s[k] for s in sp)
    out = ['<section class="fort" id="%s"><h2>%s</h2><p class="where">%s &middot; %s &rarr; %s (%s ticks) &middot; saved as <code>%s</code></p>'
           % (fid.lower(), E(name), E(where), E(d['span']['from']), E(d['span']['to']), format(d['span']['ticks'], ','), E(save))]
    s0, s1 = d['series'][0], d['series'][-1]
    out.append('<div class="kpis">' + ''.join('<div><b>%s</b><span>%s</span></div>' % (E(str(v)), E(k)) for k, v in [
        ('arrived', tot('arrived')), ('left the map', tot('left')), ('died', tot('died')),
        ('wild on the map', '%d &rarr; %d' % (s0['wild'], s1['wild'])), ('in the tool\'s groups', '%d &rarr; %d' % (s0['grouped'], s1['grouped'])),
        ('frame rate, median (lowest)', '%d (%d)' % (d['fps_median'], d['fps_min']))]).replace('&amp;rarr;', '&rarr;') + '</div>')
    out.append('<div class="legend"><span><i class="sw s1"></i>wild animals on the map</span><span><i class="sw s2"></i>of them in the tool\'s groups</span></div>')
    out.append(chart(fid, d['series']))
    out.append(gap_note(d))
    # demographics
    rows = []
    for s in sp[:40]:
        rows.append([E(s['race'].replace('_', ' ').lower()), E(s['layer'].replace('underground', 'caverns')), E(s['kind']),
                     str(s['start']), str(s['arrived']), str(s['left']), str(s['died']), str(s['grouped']), str(s['end'])])
    out.append('<h3>Demographics</h3><p class="note">Every creature that is not a citizen, by species: on the map at the start, arrived, '
               'left the map, died, taken into the tool\'s groups, and still on the map at the end. Top 40 by numbers seen; '
               'DF\'s sealed underworld demons are left out%s.</p>' % (
                   (' (%s)' % E(', '.join('%s %d' % kv for kv in d['underworld'].items()))) if d['underworld'] else ''))
    out.append(figures.demo_bars(sp))
    out.append('<details><summary>The table (top 40)</summary>%s</details>' % table(
        [('species', 0), ('layer', 0), ('kind', 0), ('start', 1), ('arrived', 1), ('left', 1), ('died', 1), ('grouped', 1), ('end', 1)], rows, 'demo'))
    # interactions
    k = [[E(x['killer'].replace('_', ' ').lower()), E(x['victim'].replace('_', ' ').lower()), str(x['n'])] for x in d['kills'][:25]]
    a = [[E(x['attacker']), E(x['target']), str(x['n'])] for x in d['attacks'][:25]]
    causes = ', '.join('%s %d' % (c.replace('_', ' ').lower(), n) for c, n in sorted(d['death_causes'].items(), key=lambda kv: -kv[1]))
    out.append('<h3>Interactions</h3><p class="note">Deaths by cause: %s. Kills are DF\'s death records (the killer it names); '
               'attacks are the opening line of each fight in DF\'s combat reports.</p>%s<details><summary>Kills and fights as tables</summary>'
               '<div class="pair">%s%s</div></details>' % (
                   E(causes), figures.kill_graph(d['kills'], sp), table([('killer', 0), ('victim', 0), ('kills', 1)], k),
                   table([('attacker', 0), ('target', 0), ('fights', 1)], a)))
    # timings
    days = d['days']
    trows = []
    for x in days:
        trows.append([E(x['label']), str(x.get('arrive_surface', 0)), str(x.get('arrive_cavern', 0)), str(x.get('leave_surface', 0) + x.get('leave_cavern', 0)),
                      str(x.get('die_surface', 0)), str(x.get('die_cavern', 0))])
    first = sorted(d['first_seen'].items(), key=lambda kv: (kv[1].split()[0] != 'spring', int(kv[1].split()[1])))
    d0, d1 = int(d['series'][0]['day']), int(d['series'][-1]['day'])
    out.append('<h3>Timings</h3><p class="note">Each day of the run: arrivals stack above the line (surface, caverns), departures and '
               'deaths hang below it; the panel beneath runs the totals on one scale. Hover for the day\'s numbers.</p>')
    out.append(figures.timeline(days, d0, d1))
    out.append('<details><summary>Arrivals, departures and deaths by day (%d days)</summary>%s</details>' % (
        len(days), table([('day', 0), ('arrived, surface', 1), ('arrived, caverns', 1), ('left', 1), ('died, surface', 1), ('died, caverns', 1)], trows)))
    out.append('<details><summary>First arrival of each species (%d)</summary><p class="flow">%s</p></details>' % (
        len(first), ' &middot; '.join('<b>%s</b> %s' % (E(r.replace('_', ' ').lower()), E(t)) for r, t in first)))
    # roster
    if 'roster' in d:
        ro = d['roster']
        by = {}
        for r in ro:
            by.setdefault(r['layer'], []).append(r)
        lines = []
        for layer in ('land', 'water', 'cavern', 'deep'):
            rs = by.get(layer, [])
            if not rs:
                continue
            cnt = {sname: sum(sname in r['seasons'] for r in rs) for sname in ('Sp', 'Su', 'Au', 'Wi')}
            lines.append('<tr><td>%s</td><td class="n">%d</td><td class="n">%d</td><td class="n">%d</td><td class="n">%d</td><td class="n">%d</td></tr>'
                         % (layer, len(rs), cnt['Sp'], cnt['Su'], cnt['Au'], cnt['Wi']))
        rv = d.get('roster_vs_arrivals', {})
        full = table([('layer', 0), ('species', 0), ('seasons', 0)], [[E(r['layer']), E(r['token'].replace('_', ' ').lower()), E(r['seasons'])]
                                                                       for r in sorted(ro, key=lambda r: (r['layer'], r['token']))])
        out.append('<h3>Roster assignments</h3><p class="note">The tool\'s roster on this fort: every managed species active, dealt '
                   'seasons by its climate (the preset). Species per layer and per season:</p><div class="tw"><table><thead><tr><th>layer</th>'
                   '<th class="n">species</th><th class="n">spring</th><th class="n">summer</th><th class="n">autumn</th><th class="n">winter</th>'
                   '</tr></thead><tbody>%s</tbody></table></div><p class="note">%d roster species arrived during the run; %d species that arrived are not on it (%s): '
                   'the roster gives them no season, and DF spawns them itself.</p>'
                   '<details><summary>Every species and its seasons (%d)</summary>%s</details>' % (
                       ''.join(lines), len(rv.get('on_roster_arrived', [])), len(rv.get('arrived_not_on_roster', [])),
                       E(', '.join(t.replace('_', ' ').lower() for t in rv.get('arrived_not_on_roster', []))) or 'none', len(ro), full))
    # the season change
    sc = d.get('season_change')
    if sc:
        lab = lambda t: E(t.replace('_', ' ').lower())
        srows = [[E(x['layer']), lab(x['gone']), lab(x['taker'])] for x in sorted(sc['swaps'], key=lambda x: (x['layer'], x['gone']))]
        diff = d.get('roster_diff') or []
        dtab = ('<details><summary>Roster before and after the change (%d species changed)</summary>%s</details>' % (
            len(diff), table([('layer', 0), ('species', 0), ('spring', 0), ('summer', 0)],
                             [[E(x['layer']), lab(x['token']), E(x['before']), E(x['after'])] for x in diff]))) if diff else ''
        out.append('<h3>The season change</h3><p class="note">On %s the tool applied the summer roster. %d species due in summer had '
                   'no stock left in the world (DF\'s regional populations exhausted), so each handed its niche to an off-season '
                   'species of the same layer and role for the rest of summer; %d seasons lent in spring went back.</p>'
                   '<details><summary>Niche hand-overs (%d)</summary>%s</details>%s' % (
                       E(sc['day']), len(sc['swaps']), sc['given_back'], len(sc['swaps']),
                       table([('layer', 0), ('exhausted', 0), ('takes its niche', 0)], srows), dtab))
    # the tool's own actions
    lk = ', '.join('%s %d' % kv for kv in d['ledger_kinds'].items())
    q = ''.join('<li><b>%s</b> %s</li>' % (E(kind), E(lines_[0])) for kind, lines_ in d['ledger_quotes'].items() if lines_)
    wd = ', '.join('%s into the %s %d' % (x['species'].replace('_', ' ').lower(), x['body'], x['n']) for x in d['water_draws'][:12])
    out.append('<h3>What the tool did</h3><p class="note">The tool\'s ledger keeps its last 300 entries, so it covers the end of the run '
               '(%s). By kind: %s.</p>%s<details><summary>One example of each kind</summary><ul class="quotes">%s</ul></details>' % (
                   'from %s' % E(d['ledger_from']) if d.get('ledger_from') else 'its last stretch', E(lk),
                   ('<p class="note">Water draws: %s.</p>' % E(wd)) if wd else '', q))
    out.append('</section>')
    return '\n'.join(out)


def questions(data):
    """the user's questions of 7 Oct evening: the gap, species per season, DF's own waves (text in report_template.html)"""
    rows = [{'name': name, 'gap': data[fid]['gap']} for fid, name, _, _ in FORTS if fid in data]
    gap = figures.gap_bars(rows)
    head = '<tr><th>fort</th><th>layer</th>' + ''.join('<th class="n">%s</th>' % s for s in ('spring', 'summer', 'autumn', 'winter')) + '</tr>'
    body = ''
    for fid, name, _, _ in FORTS:
        sc = data.get(fid, {}).get('season_counts')
        if not sc:
            continue
        for i, L in enumerate(('land', 'water', 'cavern', 'deep')):
            v = sc.get(L, {})
            cells = ''.join('<td class="n">%d <span class="dim">(%d)</span></td>' % tuple(v.get(s, [0, 0])) for s in ('Sp', 'Su', 'Au', 'Wi'))
            body += '<tr%s><td>%s</td><td>%s</td>%s</tr>' % (' class="first"' if i == 0 else '', E(name) if i == 0 else '', L, cells)
    counts = '<div class="tw"><table class="seasons"><thead>%s</thead><tbody>%s</tbody></table></div>' % (head, body)
    return gap, counts


def main():
    data = {}
    for fid, *_ in FORTS:
        p = os.path.join(HERE, fid, 'report.json')
        if os.path.exists(p):
            data[fid] = json.load(open(p))
    rows = []
    for fid, name, where, save in FORTS:
        if fid not in data:
            continue
        d = data[fid]
        sp = d['species']
        s0, s1 = d['series'][0], d['series'][-1]
        rows.append(['<a href="#%s">%s</a>' % (fid.lower(), E(name)), '30 of 30', str(sum(s['arrived'] for s in sp)), str(sum(s['left'] for s in sp)),
                     str(sum(s['died'] for s in sp)), '%d &rarr; %d' % (s0['wild'], s1['wild']), '%d (%d)' % (d['fps_median'], d['fps_min']),
                     E(str(d.get('jumps_cross', 0)))])
    shots = ''
    rec = os.path.join(HERE, '..', 'recordings')
    before = os.path.join(rec, '20261007-150353-falls2-initial', 'frames', '0004.png')
    after = os.path.join(rec, '20261007-151408-falls2-curtain2', 'frames', '0004.png')
    if os.path.exists(before) and os.path.exists(after):
        crop = (700, 140, 980, 620)
        shots = ('<div class="shots"><figure><img alt="The falls before: vertical and horizontal streaks on one tile, and a dry-looking row" src="%s">'
                 '<figcaption>Before: the lip had straight streaks beside diagonal ones and the river\'s sideways dashes over both; the '
                 'falling row (bottom) read as dry sand.</figcaption></figure><figure><img alt="The falls after: one diagonal heading, a white-water curtain" src="%s">'
                 '<figcaption>After: one heading for the whole edge, on the diagonal the river takes into it; the falling row is a white-water '
                 'curtain streaming the same way.</figcaption></figure></div>') % (img_uri(before, crop, 420), img_uri(after, crop, 420))
    page = open(os.path.join(HERE, 'report_template.html')).read()
    page = page.replace('{{SUMMARY}}', table([('fort', 0), ('dwarves at the end', 0), ('arrived', 1), ('left', 1), ('died', 1),
                                              ('wild on the map', 1), ('fps, median (lowest)', 1), ('cavern-surface teleports', 1)], rows, 'sum'))
    gap, counts = questions(data)
    page = page.replace('{{GAP_FIG}}', gap).replace('{{SEASON_COUNTS}}', counts)
    page = page.replace('{{SHOTS}}', shots)
    page = page.replace('{{FORTS}}', '\n'.join(fort_section(fid, name, where, save, data[fid]) for fid, name, where, save in FORTS if fid in data))
    open(sys.argv[1], 'w').write(page)
    print('wrote', sys.argv[1], len(page) // 1024, 'KB')


if __name__ == '__main__':
    main()
