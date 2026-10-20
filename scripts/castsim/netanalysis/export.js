// Export per fort x layer x season: candidate nodes (with metadata) and directed edges (eater -> eaten) under
// L0 = the v7.6.1 tier ladder (explorer v3, 17 Oct 11:54, before New Rules), L1 = today's ladder, NR = New Rules today.
const SP = process.argv[2];
const CUR = { data: require('/Users/nathanielcannon/Claude/Projects/DwarfCron/data/castsim/foodweb/creatures.json'), sim: require('/Users/nathanielcannon/Claude/Projects/DwarfCron/scripts/castsim/foodweb_sim.js') };
const OLD = { data: require(SP + '/v3/creatures.json'), sim: require(SP + '/v3/foodweb_sim.js') };
const cur = CUR.sim.make(CUR.data), old = OLD.sim.make(OLD.data);
const W = o => Object.assign({ ocean: null, lake: null, river: null, pool: null, brook: false }, o);
const FORTS = {
  terrifying_broadleaf_river: { land: ['FOREST_TEMPERATE_BROADLEAF'], sav: 80, evil: 90, extinct: 'UNTAMED_WILDS', water: W({ river: ['TEMPERATE'] }) },
  calm_temperate_lake: { land: ['FOREST_TEMPERATE_BROADLEAF', 'GRASSLAND_TEMPERATE'], sav: 50, evil: 50, extinct: 'UNTAMED_WILDS', water: W({ lake: ['TEMPERATE'] }) },
  savage_tropical_coast: { land: ['SHRUBLAND_TROPICAL', 'SWAMP_MANGROVE', 'FOREST_TROPICAL_MOIST_BROADLEAF'], sav: 80, evil: 50, extinct: 'UNTAMED_WILDS', water: W({ ocean: ['TROPICAL'], river: ['TROPICAL'] }) },
  good_temperate_brook: { land: ['FOREST_TEMPERATE_CONIFER', 'SHRUBLAND_TEMPERATE'], sav: 50, evil: 10, extinct: 'UNTAMED_WILDS', water: W({ river: ['TEMPERATE'], pool: ['TEMPERATE'], brook: true }) },
  evil_tundra_pools: { land: ['TUNDRA', 'FOREST_TAIGA'], sav: 50, evil: 90, extinct: 'WILDERNESS', water: W({ pool: ['TEMPERATE'] }) },
  savage_good_arctic_coast: { land: ['GLACIER', 'TUNDRA'], sav: 80, evil: 10, extinct: 'WILDERNESS', water: W({ ocean: ['ARCTIC'] }) },
};
function levelOf(S, it) {
  if (it.vermin) return 'vermin';
  if (it.slots.includes('apex')) return 'apex';
  return S.tierOf({ c: it.c, slot: it.slots[0], vermin: false }) >= 2 ? 'predator' : 'prey';
}
function graph(S, B, L, s, fams, attribute) {
  const lst = (B.lists[L + '|' + s] || []).filter(x => !x.vfish);
  const by = new Map();
  for (const x of lst) if (!by.has(x.c.t)) by.set(x.c.t, { c: x.c, vermin: x.vermin, vclass: x.vclass, slots: x.slots.slice() });
  const items = [...by.values()];
  const nodes = items.map(it => ({ t: it.c.t, nm: it.c.nm, g: it.c.g, h: it.c.h, ro: it.c.ro, slots: it.slots, level: levelOf(S, it), m: it.c.m, swv: it.c.swv || null,
    gi: !!it.c.gi, ap: !!it.c.ap, se: !!it.c.se, ev: !!it.c.ev, ex: !!it.c.ex, c1: it.c.c1 || 1 }));
  const edges = {};
  for (const [name, on] of Object.entries(fams)) {
    const E = [];
    for (const a of items) { if (a.vermin) continue;
      for (const b of items) { if (a === b) continue;
        if (S.linkWhy(a, b, L, on).length) {
          if (attribute && name === 'NR') E.push([a.c.t, b.c.t, S.NEW_RULES.filter(r => r.test(a, b, L, on)).map(r => r.id)]);
          else E.push([a.c.t, b.c.t]);
        } } }
    edges[name] = E;
  }
  return { nodes, edges };
}
const out = {};
for (const [fk, f] of Object.entries(FORTS)) {
  const spec = { land: f.land, rtype: { sav: f.sav, evil: f.evil, iso: false }, extinct: f.extinct, water: f.water, caverns: [1, 2, 3], assign: true, neighbours: [] };
  const Bc = cur.build(spec); cur.useBuild(Bc);
  const Bo = old.build(spec);
  out[fk] = { layers: {} };
  for (const L of Bc.active) {
    out[fk].layers[L] = [];
    for (let s = 0; s < 4; s++) {
      const gc = graph(cur, Bc, L, s, { NR: { newrules: true }, L1: { ladder: true } }, true);
      const go = Bo.active.includes(L) ? graph(old, Bo, L, s, { L0: { ladder: true } }, false) : { nodes: [], edges: { L0: [] } };
      out[fk].layers[L].push({ season: s, cur: gc, old: go });
    }
  }
  console.error(fk, 'layers', Bc.active.join(','), '| old', Bo.active.join(','));
}
require('fs').writeFileSync(SP + '/graph/graphs.json', JSON.stringify(out));
console.error('wrote', require('fs').statSync(SP + '/graph/graphs.json').size);
