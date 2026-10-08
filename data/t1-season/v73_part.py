#!/usr/bin/env python3
"""The report's v7.3 section (v73.part.html) from the v7.3 runs: v73_part.py > v73.part.html
Every number comes from v73_check.summarize, the same code as the console check."""
import os

from build_report import E, table
from v73_check import summarize

HERE = os.path.dirname(os.path.abspath(__file__))
# (dir, title, earlier runs on the same fort whose stand-ins are still in force, what the run is)
RUNS = [
    ('V73_WATERFALL', 'Waterfall fort, summer &rarr; autumn', (),
     'The waterfall fort from test item 1, its casts rebuilt in summer (<code>cast rebuild</code>), run into autumn on the first v7.3 engine.'),
    ('V73_WINTER', 'Waterfall fort, autumn &rarr; winter', ('V73_WATERFALL',),
     'The same fort run on into winter after the exhaustion fix (seasonal-wildlife 6e1ffb2). Its autumn ran on the stand-ins the '
     'bug had put in at autumn 1.'),
    ('V73_BROOK', 'New 2x2 brook fort, spring &rarr; summer', (),
     'A fresh 2x2 embark on region19 (21,22, marsh and brook): casts built at enable, the fixed engine and the live ledger from the start.'),
    ('V73_WREN', 'Waterfall fort replayed, summer &rarr; autumn, giant wren held', (),
     'The waterfall fort\'s summer save run again on the engine with both boundary fixes, casts rebuilt so the giant wren is out of '
     'summer (autumn only), to see whether the summer wrens of the first run come back. Recorder detail on every arrival: age, edge or '
     'inside, mother.'),
    ('V73_LAKE2', 'New 2x2 lake fort, spring &rarr; summer', (),
     'A fresh 2x2 on region19 (10,42) placed on the lake tile\'s own lake cell: a 1,062-tile freshwater lake, two river runs, a pool. '
     'A first try on the seam with the savanna tile (10,41) had no water at all: the lake tile\'s edge rows take their neighbours\' biomes.'),
    ('V73_OCEAN2', 'New 2x2 ocean fort, spring &rarr; summer', (),
     'A fresh 2x2 on region19 (63,46, no river) placed on the ocean tile\'s own cells: one column ocean, one shrubland; a 6,191-tile '
     'salt ocean up to 4 levels deep. A first try on the seam with the shrubland tile (63,45) had only freshwater pools. Its casts '
     'were built by the engine with the vermin fixes (29a8a91). Its <i>units</i> column lists 17 orcas, sharks and a halibut under '
     'land: the recorder took the layer from the population source, and ocean life has none, so it filed the water layer\'s own draws '
     '(the ledger\'s 17 water groups) as land. The recorder now takes a group member\'s layer from its group. The same mix-up hid '
     'these groups from the season turnover: 3 orcas, cast spring and winter, stayed into summer. Fixed (8817eb4) and checked on '
     'this fort: the next pass sent off the orcas, the dogfish and the halibut.'),
    ('V73_OCEAN3', 'Ocean fort again, spring &rarr; summer &rarr; autumn', (),
     'The ocean fort\'s embark save run through two season changes on the engine with every fix of these runs. The first attempt '
     'at its autumn (V73_OCEAN2_AU) was lost to thirst: the rig\'s embarks carry no drink and this site has only salt water, so all '
     '30 dwarves died of dehydration by mid-summer and DF ended the fort. Not the tool; the season runner now waters and feeds the '
     'dwarves each chunk. Reloading that save then showed a tool bug: the casts were saved but never read back, so the reloaded fort '
     'had none. Fixed (b0895b9): the save now loads with its casts, identical to the first run\'s.'),
    ('V73_LAKE3', 'Lake fort again, spring &rarr; summer &rarr; autumn', (),
     'The lake fort\'s embark save through two season changes on the final engine, its casts reloaded from the save.'),
]
LAYERS = ('land', 'water', 'cavern')
# what an off-cast group was, where the run's data show it (read by hand from ledger and recorder; 8 Oct)
WHY = {
    ('V73_WATERFALL', 'Summer', 'land', 'GIANT_WREN'): 'from the held entry #3634 (54,25), cast only in winter. Not reproduced: the '
        'replay with the wren held (V73_WREN, below) had no wren arrive in 100 days, and a departure refund was measured not to reopen '
        'the entry (extinct stays set, the hold pins it back within 100-300 ticks). The first run\'s casts came from an earlier build in '
        'a session whose steps before the recorder are not logged',
    ('V73_LAKE3', 'Spring', 'cavern', 'RUTHERER'): 'DF\'s embark-time cavern residents, found on the first pass after the load and '
        'sent off at once as not cast this season (not a wave)',
    ('V73_WREN', 'Autumn', 'cavern', 'REACHER'): 'a summer species walking in 28 ticks after the change: the season now applies at its '
        'own tick, so this is DF\'s own lead time between choosing a wave and placing it',
    ('V73_BROOK', 'Spring', 'cavern', 'HUNGRY_HEAD'): 'DF\'s embark-time cavern residents, found on the first pass and sent off at once '
        'as not cast this season (not a wave)',
    ('V73_BROOK', 'Summer', 'cavern', 'TROLL'): 'a spring species arriving 291 ticks into summer: the caverns\' hold is set by the daily '
        'tick, so a boundary leaves up to a day at the old odds',
}
ORDER = {'Spring': 0, 'Summer': 1, 'Autumn': 2, 'Winter': 3}


def run_table(S):
    keys = sorted({k[:2] for k in S['src']} | {k[:2] for k in S['arr']},
                  key=lambda k: (ORDER[k[1]], LAYERS.index(k[0])))
    rows = []
    for L, s in keys:
        g = {w: sum(v for k, v in S['src'].items() if k[0] == L and k[1] == s and k[3] == w) for w in ('cast', 'stand-in', 'OFF')}
        who = sorted({k[2] for k in S['src'] if k[0] == L and k[1] == s})
        u_ok, u_si, u_off = S['arr'][(L, s, True)], S['arr'][(L, s, 'stand-in')], S['arr'][(L, s, False)]
        rows.append([E(s), E(L), E(' + '.join(who) or '-'), str(g['cast']), str(g['stand-in']),
                     ('<b>%d</b>' % g['OFF']) if g['OFF'] else '0', '%d + %d of %d' % (u_ok, u_si, u_ok + u_si + u_off)])
    return table([('season', 0), ('layer', 0), ('brought by', 0), ('groups: in the cast', 1), ('stand-in', 1), ('off the cast', 1),
                  ('units: cast + stand-in', 1)], rows)


def off_list(S, d):
    items = []
    for k, v in sorted(S['src'].items(), key=lambda kv: (ORDER[kv[0][1]], kv[0][0], -kv[1])):
        L, s, who, where, race = k
        if where == 'cast':
            continue
        why = ('stand-in for %s' % S['stand'][(L, s, race)]) if where == 'stand-in' else WHY.get((d, s, L, race), 'neither cast nor a logged stand-in')
        items.append('<li>%s %s: %s x%d (%s); %s</li>' % (E(s), E(L), E(race), v, 'the tool\'s draw' if who == 'tool' else 'DF', E(why)))
    return ('<ul class="gap">%s</ul>' % ''.join(items)) if items else ''


def main():
    out = ['<section id="v73">', '  <h2>v7.3 season casts: first runs</h2>',
           '  <p class="note">v7.3 makes the cast the season\'s roster: per layer and season a small set grown from a high-value seed '
           '(your ruling of 7 October: the pool is not the roster), every other species resting. These runs check that arrivals follow the cast. '
           '<i>Groups</i> come from the tool\'s ledger: a tool draw (water) or a DF wave the tool found (land, caverns). <i>Units</i> '
           'come from the recorder and include births. A <i>stand-in</i> is a species the exhaustion check handed a cast member\'s niche.</p>',
           '  <p class="note"><b>Result.</b> Arrivals follow the cast. On the final engine the ocean fort (V73_OCEAN3) and the lake fort '
           '(V73_LAKE3) ran through two season changes each: every arrival on land, in the water and in the caverns belonged to its '
           'season\'s cast, each season applied at its own tick, and each change sent off the groups whose species left the cast, '
           'ocean groups included. The runs found and fixed five things in the tool, and settled one question:</p>',
           '  <ul class="gap">',
           '    <li><b>The exhaustion check ran before the season\'s apply</b> (6e1ffb2): at autumn 1 it handed 17 of the 22 cast species\' '
           'niches to stand-ins. The same bug made test item 1\'s summer-1 hand-overs (corrected under Findings).</li>',
           '    <li><b>A season change waited for the daily job</b> (34a3a4b): up to a day at the old season\'s odds; a spring troll '
           'came in 291 ticks into summer. The change now applies at its own tick.</li>',
           '    <li><b>Aquatic vermin were cast on land, and one species could fill two vermin slots</b> (29a8a91).</li>',
           '    <li><b>Ocean and river groups escaped the turnover</b> (8817eb4): their species are filed under a land key; 3 orcas, '
           'cast spring and winter, stayed into summer.</li>',
           '    <li><b>The casts were saved but never loaded</b> (b0895b9): after any save and load a fort ran with no casts. This would '
           'have hit every fort you save.</li>',
           '    <li>The giant wrens of the first run were not reproduced with the wren held; the hold was measured to work.</li>',
           '  </ul>',
           '  <p class="note">Two rig lessons, not tool faults: a small fort on a lake or ocean seam can miss the water (the water tile\'s '
           'edge rows take their neighbours\' biomes; forts are now placed on the water tile\'s own cells), and the rig\'s embarks carry no '
           'drink, so a salt-water fort died of thirst (the runner now waters the dwarves).</p>']
    for d, title, prev, what in RUNS:
        if not os.path.exists(os.path.join(HERE, d, 'casts-start.txt')) or not os.path.exists(os.path.join(HERE, d, 'events.tsv')):
            continue
        S = summarize(os.path.join(HERE, d), tuple(os.path.join(HERE, p) for p in prev))
        out.append('  <h3>%s</h3>' % title)
        out.append('  <p class="note">%s%s</p>' % (what, '' if S['complete'] else
                   ' Ledger groups are from the end-of-run dump, which holds only the tool\'s newest 300 entries: the run\'s first '
                   'weeks are missing from that column.'))
        out.append(run_table(S))
        out.append(off_list(S, d))
        early = sum(S['early'].values())
        out.append('  <p class="note">Hand-overs logged before their season\'s apply: <b>%s</b>. Groups sent off at a season change '
                   'because their species left the cast: %s. Relation pairs the tool wrote: %d species pairs; DF\'s own at the end: %d.</p>'
                   % (('%d (%s)' % (early, ', '.join('%s %d' % kv for kv in S['early'].items()))) if early else 'none',
                      E('; '.join(t.split(': ', 1)[-1][:160] for t in S['turn'])) or 'none in the window',
                      S['pairs']['tool'], S['pairs']['live-df']))
    out.append('</section>')
    print('\n'.join(out))


if __name__ == '__main__':
    main()
