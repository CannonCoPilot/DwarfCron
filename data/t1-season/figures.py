"""Inline-SVG figures for the test-item-1 report page (build_report.py). Colours are CSS roles (--s1..--s6, --ink2) set in
report_template.html; every mark carries a data-tip the page's one hover script reads."""
import html
import json
import math

E = html.escape
MEASURES = [('start', 'on the map at the start'), ('arrived', 'arrived'), ('left', 'left the map'), ('died', 'died'),
            ('grouped', 'taken into the tool\'s groups'), ('end', 'on the map at the end')]


def nice_top(v):
    """the smallest 1/2/5 x 10^k at or above v, and a tick step giving 4-6 ticks"""
    v = max(v, 1)
    mag = 10 ** int(math.floor(math.log10(v)))
    top = next(m * mag for m in (1, 2, 5, 10) if m * mag >= v)
    step = max(top / 5 if top / mag in (1, 5, 10) else top / 4, 1)
    top = max(top, step)
    return top, step


def name(t):
    return t.replace('_', ' ').lower()


def legend(items):
    return '<div class="legend">' + ''.join('<span><i class="sw %s"></i>%s</span>' % (c, E(t)) for c, t in items) + '</div>'


def demo_bars(species, n=12):
    """horizontal grouped bars: the top n species by numbers seen, six measures each"""
    sp = species[:n]
    W, L, R, T = 960, 170, 40, 8
    bh, gap = 5, 10                                  # bar thickness, space between species
    band = bh * len(MEASURES) + gap
    H = T + band * len(sp) + 26
    top, step = nice_top(max(max(s[k] for k, _ in MEASURES) for s in sp))
    X = lambda v: L + v / top * (W - L - R)
    out = []
    for i in range(int(top / step) + 1):
        v = i * step
        out.append('<line class="grid" x1="%.1f" x2="%.1f" y1="%d" y2="%d"/><text class="tick" x="%.1f" y="%d" text-anchor="middle">%d</text>'
                   % (X(v), X(v), T, H - 22, X(v), H - 8, v))
    for i, s in enumerate(sp):
        y0 = T + i * band
        out.append('<text class="lab" x="%d" y="%.1f" text-anchor="end">%s</text>' % (L - 8, y0 + bh * 3 + 3, E(name(s['race']))))
        for j, (k, lab) in enumerate(MEASURES):
            v = s[k]
            w = max(X(v) - L, 0.0)
            tip = '%s (%s): %s %d' % (name(s['race']), s['layer'].replace('underground', 'caverns'), lab, v)
            out.append('<rect class="bar s%d" x="%d" y="%d" width="%.1f" height="%d" rx="1" data-tip="%s"/>' % (j + 1, L, y0 + j * bh, w, bh - 1, E(tip)))
    out.append('<line class="axis" x1="%d" x2="%d" y1="%d" y2="%d"/>' % (L, L, T, H - 22))
    svg = '<svg viewBox="0 0 %d %d" role="img" aria-label="Grouped bars: start, arrived, left, died, grouped and end for the %d most-seen species">%s</svg>' % (
        W, H, len(sp), ''.join(out))
    return legend([('s%d' % (j + 1), lab) for j, (_, lab) in enumerate(MEASURES)]) + '<figure class="fig">%s<div class="tip" hidden></div></figure>' % svg


HAB = [('land', 's1', 'land'), ('amphibious', 's4', 'amphibious'), ('water', 's3', 'water'), ('cavern', 's2', 'caverns')]


def kill_graph(kills, species, pairs=None, max_edges=45):
    """the food web on the map: species round a ring (land, amphibious, water, caverns), arrows from predator to prey.
    Edge source: 'tool' = a pair the tool wrote (ecology pairs), 'df' = a pair live in DF's relation table that the tool
    never wrote, 'kill' = a kill with no logged relation. Width: kills (DF's death records). Click a node to pick out its
    edges. With no pair log (runs before v7.3) every edge is a kill."""
    hab = {s['race']: s.get('habitat', 'land') for s in species}
    EDG = {}
    for k in kills:
        if k['killer'] in ('none', '?'):
            continue
        e = EDG.setdefault((k['killer'], k['victim']), {'kills': 0, 'src': 'kill'})
        e['kills'] += k['n']
    if pairs:
        for p in pairs:
            a, b = p['predator'], p['prey']
            if p['source'] == 'tool':
                EDG.setdefault((a, b), {'kills': 0, 'src': 'tool'})['src'] = 'tool'
        for p in pairs:
            if p['source'] == 'live-df':
                a, b = p['predator'], p['prey']
                key = (a, b) if (a, b) in EDG or (b, a) not in EDG else (b, a)
                e = EDG.setdefault(key, {'kills': 0, 'src': 'df'})
                if e['src'] != 'tool':
                    e['src'] = 'df'
    if not EDG:
        return '<p class="note">No kills with a named killer and no relation pairs.</p>'
    top = sorted(EDG.items(), key=lambda kv: (-(kv[1]['src'] == 'tool'), -kv[1]['kills']))[:max_edges]
    edges = dict(top)
    made, lost = {}, {}
    for (a, b), e in edges.items():
        made[a] = made.get(a, 0) + e['kills']; lost[b] = lost.get(b, 0) + e['kills']
    nodes = set(made) | set(lost)
    order = []
    for h, _, _ in HAB:
        grp = sorted((n for n in nodes if hab.get(n, 'land') == h), key=lambda n: (-(made.get(n, 0) + lost.get(n, 0)), n))
        order += grp
    W, H = 960, 620
    cx, cy, Rx, Ry = W / 2, H / 2, 290, 245
    N = max(len(order), 1)
    ang = {n: math.pi / 2 + (i + 0.5) * 2 * math.pi / N for i, n in enumerate(order)}
    XY = {n: (cx + Rx * math.cos(a), cy - Ry * math.sin(a)) for n, a in ang.items()}
    wmax = max([e['kills'] for e in edges.values()] + [1])
    big = max([made.get(n, 0) + lost.get(n, 0) for n in order] + [1])
    rad = {n: 4 + 8 * math.sqrt((made.get(n, 0) + lost.get(n, 0)) / big) for n in order}
    out = ['<defs>' + ''.join('<marker id="ah-%s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" '
                              'orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="arrow %s"/></marker>' % (c, c)
                              for c in ('tool', 'df', 'kill')) + '</defs>']
    for (a, b), e in sorted(edges.items(), key=lambda kv: kv[1]['kills']):
        sw = 1.0 + 6 * math.sqrt(e['kills'] / wmax) if e['kills'] else 0.9
        what = {'tool': 'a pair the tool wrote', 'df': 'a pair DF set (the tool never wrote it)', 'kill': 'a kill with no logged relation'}[e['src']]
        tip = '%s > %s: %s; %d kill(s)' % (name(a), name(b), what, e['kills'])
        if a == b:
            x, y = XY[a]
            ox, oy = (x - cx) / Rx, (y - cy) / Ry
            out.append('<circle class="edge %s" data-a="%s" data-b="%s" cx="%.1f" cy="%.1f" r="10" stroke-width="%.1f" data-tip="%s"/>' % (
                e['src'], E_(a), E_(b), x + ox * (rad[a] + 9), y + oy * (rad[a] + 9), sw, E(tip)))
            continue
        (x1, y1), (x2, y2) = XY[a], XY[b]
        mx, my = cx + ((x1 + x2) / 2 - cx) * 0.25, cy + ((y1 + y2) / 2 - cy) * 0.25
        dd = max(math.hypot(x2 - mx, y2 - my), 1)
        ex, ey = x2 - (x2 - mx) / dd * (rad[b] + 3), y2 - (y2 - my) / dd * (rad[b] + 3)
        out.append('<path class="edge %s" data-a="%s" data-b="%s" d="M%.1f %.1f Q%.1f %.1f %.1f %.1f" stroke-width="%.1f" '
                   'marker-end="url(#ah-%s)" data-tip="%s"/>' % (e['src'], E_(a), E_(b), x1, y1, mx, my, ex, ey, sw, e['src'], E(tip)))
    cls = {h: c for h, c, _ in HAB}
    for n in order:
        x, y = XY[n]
        h = hab.get(n, 'land')
        tip = '%s (%s): killed %d, killed by others %d' % (name(n), dict((k, l) for k, _, l in HAB)[h], made.get(n, 0), lost.get(n, 0))
        out.append('<g class="nd" data-n="%s" tabindex="0" role="button" aria-label="%s"><circle class="node %s" cx="%.1f" cy="%.1f" r="%.1f" data-tip="%s"/>' % (
            E_(n), E(name(n)), cls[h], x, y, rad[n], E(tip)))
        a = ang[n]
        lx, ly = cx + (Rx + rad[n] + 8) * math.cos(a), cy - (Ry + rad[n] + 8) * math.sin(a)
        anchor = 'start' if math.cos(a) > 0.15 else ('end' if math.cos(a) < -0.15 else 'middle')
        out.append('<text class="nlab" x="%.1f" y="%.1f" text-anchor="%s">%s</text></g>' % (lx, ly + 4, anchor, E(name(n))))
    svg = '<svg viewBox="0 0 %d %d" role="img" aria-label="Food web: arrows from predator to prey, thicker for more kills">%s</svg>' % (W, H, ''.join(out))
    srcs = {e['src'] for e in edges.values()}
    leg = [(c, l) for h, c, l in HAB if any(hab.get(n, 'land') == h for n in order)]
    eleg = ''.join('<span><i class="ln %s"></i>%s</span>' % (k, t) for k, t in
                   (('tool', 'pair the tool wrote'), ('df', 'pair DF set itself'), ('kill', 'kill, no logged relation')) if k in srcs)
    note = ('Arrows run from predator to prey; width is kills. ' +
            ('The tool logged its relation writes on this run, so every edge is marked by who set it. ' if pairs else
             'This run predates v7.3: the tool did not log which pairs it wrote, so every edge is a kill from DF\'s death records, '
             'and which of them followed a tool-written relation cannot be told apart. ') +
            'Click a species to pick out its edges; click it again to clear.')
    return (legend([(c, l) for c, l in leg]) + '<div class="legend">%s</div>' % eleg +
            '<p class="note">%s</p><figure class="fig web">%s<div class="tip" hidden></div></figure>' % (note, svg))


def E_(t):
    return html.escape(t, quote=True)


def timeline(days, d0, d1):
    """per day: arrivals (surface, caverns) above the baseline, departures and deaths below; under it the running totals"""
    by = {x['day']: x for x in days}
    rng = list(range(d0, d1 + 1))
    g = lambda dd, k: by.get(dd, {}).get(k, 0)
    rows = [{'d': dd, 'as': g(dd, 'arrive_surface'), 'ac': g(dd, 'arrive_cavern'),
             'lv': g(dd, 'leave_surface') + g(dd, 'leave_cavern'), 'di': g(dd, 'die_surface') + g(dd, 'die_cavern')} for dd in rng]
    cum = {'as': 0, 'ac': 0, 'lv': 0, 'di': 0}
    for r in rows:
        for k in cum:
            cum[k] += r[k]; r['c' + k] = cum[k]
    W, L, R = 960, 44, 130
    up = max(max(r['as'] + r['ac'] for r in rows), 1)
    dn = max(max(r['lv'] + r['di'] for r in rows), 1)
    tu, su = nice_top(up); td, sd = nice_top(dn)
    T1, H1 = 14, 190                                 # bars panel: baseline at T1 + H1 * tu / (tu + td)
    base = T1 + H1 * tu / (tu + td)
    Yb = lambda v: base - v / (tu + td) * H1
    T2, H2 = T1 + H1 + 34, 130                        # running-total panel
    ct, cs = nice_top(max(cum.values()))
    Yc = lambda v: T2 + H2 - v / ct * H2
    n = len(rng)
    bw = (W - L - R) / n
    X = lambda i: L + i * bw
    out = []
    for v in [i * su for i in range(1, int(tu / su) + 1)] + [-i * sd for i in range(1, int(td / sd) + 1)] + [0]:
        lab_ = '<text class="tick" x="%d" y="%.1f" text-anchor="end">%d</text>' % (L - 6, Yb(v) + 4, abs(v)) if v in (0, tu, -td) else ''
        out.append('<line class="%s" x1="%d" x2="%d" y1="%.1f" y2="%.1f"/>%s' % ('axis' if v == 0 else 'grid', L, W - R, Yb(v), Yb(v), lab_))
    out.append('<text class="tick" x="%d" y="%d">per day: in above the line, out below</text>' % (L, T1 - 1))
    for i in range(int(ct / cs) + 1):
        v = i * cs
        out.append('<line class="%s" x1="%d" x2="%d" y1="%.1f" y2="%.1f"/><text class="tick" x="%d" y="%.1f" text-anchor="end">%d</text>'
                   % ('axis' if v == 0 else 'grid', L, W - R, Yc(v), Yc(v), L - 6, Yc(v) + 4, v))
    out.append('<text class="tick" x="%d" y="%d">running total since the start of the record</text>' % (L, T2 - 6))
    w = max(bw - 1.2, 1.0)
    for i, r in enumerate(rows):
        x = X(i) + (bw - w) / 2
        y = base
        for k, c in (('as', 's1'), ('ac', 's2')):
            if r[k]:
                h = base - Yb(r[k])
                out.append('<rect class="bar %s" x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>' % (c, x, y - h, w, h)); y -= h
        y = base
        for k, c in (('lv', 's3'), ('di', 'ink')):
            if r[k]:
                h = Yb(-r[k]) - base
                out.append('<rect class="bar %s" x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>' % (c, x, y, w, h)); y += h
    ends = []
    for k, c, lab in (('as', 's1', 'surface in'), ('ac', 's2', 'caverns in'), ('lv', 's3', 'left'), ('di', 'ink', 'died')):
        pts = ' '.join('%s%.1f %.1f' % ('M' if i == 0 else 'L', X(i) + bw / 2, Yc(r['c' + k])) for i, r in enumerate(rows))
        out.append('<path class="line %s%s" d="%s"/>' % (c, ' dash' if c == 'ink' else '', pts))
        ends.append([Yc(rows[-1]['c' + k]), c, '%s %d' % (lab, rows[-1]['c' + k])])
    ends.sort()
    for i in range(1, len(ends)):                    # keep end labels 11 px apart
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + 11)
    for y, c, lab in ends:
        out.append('<text class="elab %s" x="%d" y="%.1f">%s</text>' % (c, W - R + 6, y + 4, E(lab)))
    lab = lambda dd: ('Sp %d' % (dd + 1)) if dd < 84 else ('Su %d' % (dd - 83))
    for i, dd in enumerate(rng):
        if (dd + 1) % 10 == 0 or dd == 84:
            for yy in (T1 + H1 + 14, T2 + H2 + 14):
                out.append('<text class="tick" x="%.1f" y="%d" text-anchor="middle">%s</text>' % (X(i) + bw / 2, yy, lab(dd)))
    if d0 <= 84 <= d1:
        x = X(84 - d0)
        out.append('<line class="season" x1="%.1f" x2="%.1f" y1="%d" y2="%d"/>' % (x, x, T1, T2 + H2))
    H = T2 + H2 + 22
    data = json.dumps([[lab(r['d']), r['as'], r['ac'], r['lv'], r['di'], r['cas'], r['cac'], r['clv'], r['cdi']] for r in rows])
    svg = ('<svg viewBox="0 0 %d %d" role="img" aria-label="Arrivals, departures and deaths per day, and their running totals">%s'
           '<line class="cross" x1="-10" x2="-10" y1="%d" y2="%d"/><rect class="hit" x="%d" y="%d" width="%.1f" height="%d"/></svg>') % (
        W, H, ''.join(out), T1, T2 + H2, L, T1, W - L - R, T2 + H2 - T1)
    return (legend([('s1', 'arrived, surface'), ('s2', 'arrived, caverns'), ('s3', 'left the map'), ('ink', 'died (dashed in the totals)')]) +
            '<figure class="fig tl" data-rows=\'%s\' data-l="%d" data-w="%d" data-bw="%.4f">%s<div class="tip" hidden></div></figure>' % (data, L, W, bw, svg))


GAP = [('grouped', 's1', 'in the tool\'s groups'), ('native', 's2', 'here before the tool loaded, not adopted'),
       ('sponge', 's3', 'sponges (placed like plants)'), ('other', 's4', 'other ungrouped')]


def gap_bars(rows):
    """one stacked bar per fort: what the wild units on the map at the end are"""
    W, L, R, T, bh, gp = 960, 170, 50, 6, 22, 12
    H = T + len(rows) * (bh + gp) + 20
    top, step = nice_top(max(sum(r['gap'].values()) for r in rows))
    X = lambda v: L + v / top * (W - L - R)
    out = []
    for i in range(int(top / step) + 1):
        v = i * step
        out.append('<line class="grid" x1="%.1f" x2="%.1f" y1="%d" y2="%d"/><text class="tick" x="%.1f" y="%d" text-anchor="middle">%d</text>'
                   % (X(v), X(v), T, H - 20, X(v), H - 6, v))
    for i, r in enumerate(rows):
        y = T + i * (bh + gp)
        out.append('<text class="lab" x="%d" y="%d" text-anchor="end">%s</text>' % (L - 8, y + bh / 2 + 4, E(r['name'])))
        x = 0
        for k, c, lab in GAP:
            v = r['gap'].get(k, 0)
            if not v:
                continue
            out.append('<rect class="bar %s" x="%.1f" y="%d" width="%.1f" height="%d" data-tip="%s"/>' % (
                c, X(x), y, X(x + v) - X(x) - 0.8, bh, E('%s: %s %d of %d' % (r['name'], lab, v, sum(r['gap'].values())))))
            x += v
        out.append('<text class="tick" x="%.1f" y="%d">%d</text>' % (X(x) + 5, y + bh / 2 + 4, x))
    svg = '<svg viewBox="0 0 %d %d" role="img" aria-label="What the wild units on each map are at the end of the run">%s</svg>' % (W, H, ''.join(out))
    return legend([(c, lab) for _, c, lab in GAP]) + '<figure class="fig">%s<div class="tip" hidden></div></figure>' % svg
