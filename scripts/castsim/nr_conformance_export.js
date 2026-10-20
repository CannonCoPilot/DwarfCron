// New Rules conformance fixture (rebuild plan rev 7, Phase B): the explorer's verdict for every pair on the six analysis
// forts, family by family (raws, gobble, mass, hunt), within each layer and across the surface layers, with the context the
// verdicts read (layers, promoted apexes, map-only vermin, the build's flags) and the creature records. Written as a Lua
// file for the engine harness (sw-wt/plugin tests/web/harness.lua MODE nrconf, NR_FIXTURE=path), which runs V7.NR.eats
// on the same pairs and must agree on every one. Usage: node nr_conformance_export.js OUT.lua
const path = require('path');
const DATA = require(path.resolve(__dirname, '../../data/castsim/foodweb/creatures.json'));
const sim = require(path.resolve(__dirname, 'foodweb_sim.js')).make(DATA);
const W = o => Object.assign({ ocean: null, lake: null, river: null, pool: null, brook: false }, o);
const FORTS = {
  terrifying_broadleaf_river: { land: ['FOREST_TEMPERATE_BROADLEAF'], sav: 80, evil: 90, extinct: 'UNTAMED_WILDS', water: W({ river: ['TEMPERATE'] }) },
  calm_temperate_lake: { land: ['FOREST_TEMPERATE_BROADLEAF', 'GRASSLAND_TEMPERATE'], sav: 50, evil: 50, extinct: 'UNTAMED_WILDS', water: W({ lake: ['TEMPERATE'] }) },
  savage_tropical_coast: { land: ['SHRUBLAND_TROPICAL', 'SWAMP_MANGROVE', 'FOREST_TROPICAL_MOIST_BROADLEAF'], sav: 80, evil: 50, extinct: 'UNTAMED_WILDS', water: W({ ocean: ['TROPICAL'], river: ['TROPICAL'] }) },
  good_temperate_brook: { land: ['FOREST_TEMPERATE_CONIFER', 'SHRUBLAND_TEMPERATE'], sav: 50, evil: 10, extinct: 'UNTAMED_WILDS', water: W({ river: ['TEMPERATE'], pool: ['TEMPERATE'], brook: true }) },
  evil_tundra_pools: { land: ['TUNDRA', 'FOREST_TAIGA'], sav: 50, evil: 90, extinct: 'WILDERNESS', water: W({ pool: ['TEMPERATE'] }) },
  savage_good_arctic_coast: { land: ['GLACIER', 'TUNDRA'], sav: 80, evil: 10, extinct: 'WILDERNESS', water: W({ ocean: ['ARCTIC'] }), neighbours: ['TUNDRA', 'MOUNTAIN', 'FOREST_TAIGA'] },
};
const SURF = ['ground', 'flying', 'ocean', 'fresh'];
const YEARS = +(process.env.NR_YEARS || 20), SITE = 4321;
const lua = v => {
  if (v === null || v === undefined) return 'nil';
  if (v === true || v === false) return String(v);
  if (typeof v === 'number') return String(v);
  if (typeof v === 'string') return JSON.stringify(v);
  if (Array.isArray(v)) return '{' + v.map(lua).join(',') + '}';
  return '{' + Object.entries(v).filter(([, x]) => x !== undefined && x !== null).map(([k, x]) => `[${JSON.stringify(k)}]=${lua(x)}`).join(',') + '}';
};
const FAM = sim.NEW_RULES.map(r => r.id);
function verdict(a, b, L, cross) {
  if (a.vermin || a.c.t === b.c.t || a.c.g === 'GZ') return '';
  const on = cross ? { newrules: true, hunt: false, ladder: false, crossLayer: true } : { newrules: true };
  return sim.NEW_RULES.filter(r => r.test(a, b, L, on)).map(r => r.id).join(',');
}
const out = { years: YEARS, site: SITE, layers: sim.LAYERS, families: FAM, meta: { params: sim.P0, slots: DATA.meta.slots, tier: DATA.meta.tier, reach: DATA.meta.reach, vdiet: DATA.meta.vdiet, aquatic_apex: DATA.meta.aquatic_apex, pool_cap: DATA.meta.pool_cap, rules: DATA.meta.rules_version }, creatures: {}, forts: [] };
const used = new Set();
let total = 0, positive = 0;
for (const [k, f] of Object.entries(FORTS)) {
  const spec = { land: f.land, rtype: { sav: f.sav, evil: f.evil, iso: false }, extinct: f.extinct, water: f.water, caverns: [1, 2, 3], assign: true, neighbours: f.neighbours || [] };
  const B = sim.build(spec); sim.useBuild(B);
  const items = {};   // layer -> [{t, slots, vermin, vclass}], one per (token, vermin) over the four seasons
  for (const L of B.active) {
    const m = new Map();
    for (let s = 0; s < 4; s++) for (const x of B.lists[L + '|' + s] || []) m.set(x.c.t + (x.vermin ? '#v' : ''), x);
    items[L] = [...m.values()];
  }
  const pairs = {};
  const add = (a, La, b, Lb, cross) => {
    total++;
    const v = verdict(a, b, La, cross);
    if (v) { positive++; pairs[`${La}|${a.c.t}|${a.vermin ? 'v' : ''}>${Lb}|${b.c.t}|${b.vermin ? 'v' : ''}`] = v; }
  };
  for (const L of B.active) for (const a of items[L]) for (const b of items[L]) if (a !== b) add(a, L, b, L, false);
  for (const La of SURF) for (const Lb of SURF) if (La !== Lb && items[La] && items[Lb])
    for (const a of items[La]) for (const b of items[Lb]) add(a, La, b, Lb, true);
  const P = {}, apexOn = {};
  for (const t in B.P) { P[t] = { layers: B.P[t].layers }; used.add(t); }
  for (const t in B.apexOn) apexOn[t] = B.apexOn[t];
  for (const t in B.mapOnly) used.add(t);
  const mapOnly = {}; for (const t in B.mapOnly) mapOnly[t] = { sides: B.mapOnly[t].sides };
  const its = {}; for (const L in items) its[L] = items[L].map(x => ({ t: x.c.t, slots: x.slots, vermin: !!x.vermin, vclass: x.vclass || null }));
  // Phase C: what the builder reads (slots per layer for every pool species, the season lists) and what it builds (YEARS
  // years at site SITE, with the cross-layer links), and the 200-year holes
  const slotsBy = {};
  for (const t in B.P) { if (B.P[t].c.v) continue; slotsBy[t] = {}; for (const L of B.P[t].layers) slotsBy[t][L] = sim.slotsFor(B.P[t].c, L, B.sub, B.promoted); }
  const lists = {};
  for (const key in B.lists) lists[key] = B.lists[key].map(x => ({ t: x.c.t, vermin: !!x.vermin, vclass: x.vclass || null, slots: x.slots, tier: x.tier || null, vfish: !!x.vfish }));
  const prm = Object.assign({}, sim.P0, { seed: true, weird: true, guarantee: true, links: 'network', network: { newrules: true } });
  const casts = [];
  for (let y = 0; y < YEARS; y++) {
    const cs = sim.year(B, spec, prm, SITE, 250 + y), Y = {};
    for (const key in cs) {
      const tr = cs[key];
      Y[key] = { members: tr.members.map(m => [m.t, m.slot, m.how]), vermin: tr.vermin.map(v => [v.t, v.vc]), seed: tr.seed || null,
                 bonus: tr.bonus || [], guarantee: tr.guarantee, edges: tr.edges.map(e => e[0] + '>' + e[1]), built: tr.built };
    }
    casts.push({ casts: Y, cross: cs.cross.map(c => c.map(x => x.slice(0, 4).join('|'))) });
  }
  // the 200-year holes of this build, as targets.js scores them (site 1, years 250..449); the arctic coast here has
  // neighbouring tiles (map-only vermin), so its numbers are this fixture's, not targets.json's
  const T = { members: 0, unlinked: 0, seasonsUnlinked: 0, predators: 0, unfed: 0, cav: { unlinked: 0, unfed: 0 }, cross: 0 };
  for (let y = 0; y < 200; y++) {
    const cs = sim.year(B, spec, prm, 1, 250 + y);
    for (let s = 0; s < 4; s++) {
      T.cross += cs.cross[s].length;
      const H = sim.seasonHoles(cs, s, prm);
      if (H.surface) { const h = H.surface; T.members += h.members; T.unlinked += h.unlinked.length; T.predators += h.predators; T.unfed += h.unfed.length; if (h.unlinked.length) T.seasonsUnlinked++; }
      for (const L of ['cavern1', 'cavern2', 'cavern3']) if (H[L]) { T.cav.unlinked += H[L].unlinked.length; T.cav.unfed += H[L].unfed.length; }
    }
  }
  out.forts.push({ name: k, active: B.active, P, promoted: [...B.promoted], mapOnly, apexOn, items: its, pairs, slotsBy, lists, sub: B.sub, casts,
                   targets: T && { members: T.members, unlinked: T.unlinked, seasonsUnlinked: T.seasonsUnlinked, predators: T.predators, unfed: T.unfed, cavUnlinked: T.cav.unlinked, cavUnfed: T.cav.unfed, cross: T.cross } });
}
for (const t of used) out.creatures[t] = sim.BY[t];
for (const t in sim.M.link_as || {}) out.creatures[sim.M.link_as[t]] = sim.BY[sim.M.link_as[t]];   // LINK_AS models
for (const c of DATA.creatures) if (c.rt && used.has(c.t) && sim.BY[c.rt]) out.creatures[c.rt] = sim.BY[c.rt];   // roots (HUNTED_BY)
require('fs').writeFileSync(process.argv[2], '-- generated by DwarfCron scripts/castsim/nr_conformance_export.js\nreturn ' + lua(out) + '\n');
console.log(`nr fixture: ${out.forts.length} forts, ${total} pairs, ${positive} with a New Rules link, ${Object.keys(out.creatures).length} creatures -> ${process.argv[2]}`);
