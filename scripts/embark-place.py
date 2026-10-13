"""Place a small embark square where the water really is (12 Oct 2026, the V75 region-type forts).

A 4x4 over a land/water corner missed the water on five of six forts: a mid-level cell takes its biome from the tile
its region_details direction names, but cells borrowing an ocean or lake biome at land height are dry. A cell holds
water only if its source tile is water AND it lies low: ocean below 100 (the shore level), lake within 1 of the lake
tile's survey elevation (lakes cover few cells). Ranks squares by wet cells (closest to WANT), then land biomes, and
keeps those whose land source tiles fit the region type (savagery >= 66; good/evil by the world region flags).

usage: embark-place.py SURVEY.tsv CELLS.txt CATEGORY [WANT=6]
  SURVEY.tsv  `cx-lifecycle.sh survey <world>` (with rgood/revil)
  CELLS.txt   `cx-lifecycle.sh cmd cx-embark cells` on a fort embarked nearby (region_details exist only around a fort)
  CATEGORY    good evil untamed joyous terror smallsav
Prints: embark tile rx,ry and offset ox,oy for `CX_EMBARK_SIZE=4 cx-lifecycle.sh embark <world> rx ry <save> ox oy`."""
import csv, sys
surv = {(int(r['x']), int(r['y'])): r for r in csv.DictReader(open(sys.argv[1]), delimiter='\t')}
D = {1: (-1, 1), 2: (0, 1), 3: (1, 1), 4: (-1, 0), 5: (0, 0), 6: (1, 0), 7: (-1, -1), 8: (0, -1), 9: (1, -1)}
cell = {}
for line in open(sys.argv[2]):
    if not line.startswith('RD '): continue
    _, x, y, g = line.split(None, 3); x, y = int(x), int(y)
    for j, row in enumerate(g.strip().split('/')):
        for i, p in enumerate(row.split(',')):
            b, e = map(int, p.split(":")); d = b - 48 if b >= 48 else b   # inside an embarked square: ASCII digits (cx-embark cells normalises)
            if d in D: cell[(x * 16 + i, y * 16 + j)] = ((x + D[d][0], y + D[d][1]), e)
cat, want = sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 6
def wet(c):
    s, e = cell[c]; b = surv[s]['biome']
    if b.startswith('OCEAN'): return e < 100
    if b.startswith('LAKE'): return e <= int(surv[s]['elev']) + 1
    return False
out = []
for (mx, my) in cell:
    cs = [(mx + i, my + j) for i in range(4) for j in range(4)]
    if not all(c in cell and cell[c][0] in surv for c in cs): continue
    w = [c for c in cs if wet(c)]
    land = [c for c in cs if not surv[cell[c][0]]['biome'].startswith(('LAKE', 'OCEAN'))]
    lb = {surv[cell[c][0]]['biome'] for c in land}
    if len(w) < 1 or len(lb) < 2: continue
    srcs = {cell[c][0] for c in land}
    sav = [int(surv[s]['sav']) >= 66 for s in srcs]
    g = [surv[s].get('rgood') == '1' for s in srcs]; e = [surv[s].get('revil') == '1' for s in srcs]
    ok = {'good': any(g) and not any(e) and not any(sav), 'evil': any(e) and not any(g) and not any(sav),
          'untamed': all(sav) and not any(g) and not any(e), 'joyous': all(sav) and any(g) and not any(e),
          'terror': any(sav) and any(e), 'smallsav': any(sav) and not all(sav) and not any(g) and not any(e)}[cat]
    if ok:
        out.append((len(w), len(lb), mx // 16, my // 16, mx % 16, my % 16, sorted(lb), sorted(srcs)))
out.sort(key=lambda r: (abs(r[0] - want), -r[1]))
for r in out[:5]:
    print(f"wet cells {r[0]:2d}, land biomes {r[1]} -> embark tile {r[2]},{r[3]} off {r[4]},{r[5]} | {', '.join(r[6])} | land sources {r[7]}")
if not out: print('no square qualifies in the loaded region_details')
