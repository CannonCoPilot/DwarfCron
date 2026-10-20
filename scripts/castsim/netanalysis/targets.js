// The rebuild's targets (plan rev 7): the explorer's own builder (G2 + G3, growth on New Rules) over N years on the six
// analysis forts; per fort, surface members with no partner (season casts joined), seasons with any, predators without
// prey, and the same for each cavern alone. Usage: node targets.js [years=200] [out.json]
const path = require('path');
const DATA = require(path.resolve(__dirname, '../../../data/castsim/foodweb/creatures.json'));
const sim = require(path.resolve(__dirname, '../foodweb_sim.js')).make(DATA);
const YEARS = +(process.argv[2] || 200);
const W = o => Object.assign({ ocean: null, lake: null, river: null, pool: null, brook: false }, o);
const FORTS = {
  terrifying_broadleaf_river: { land: ['FOREST_TEMPERATE_BROADLEAF'], sav: 80, evil: 90, extinct: 'UNTAMED_WILDS', water: W({ river: ['TEMPERATE'] }) },
  calm_temperate_lake: { land: ['FOREST_TEMPERATE_BROADLEAF', 'GRASSLAND_TEMPERATE'], sav: 50, evil: 50, extinct: 'UNTAMED_WILDS', water: W({ lake: ['TEMPERATE'] }) },
  savage_tropical_coast: { land: ['SHRUBLAND_TROPICAL', 'SWAMP_MANGROVE', 'FOREST_TROPICAL_MOIST_BROADLEAF'], sav: 80, evil: 50, extinct: 'UNTAMED_WILDS', water: W({ ocean: ['TROPICAL'], river: ['TROPICAL'] }) },
  good_temperate_brook: { land: ['FOREST_TEMPERATE_CONIFER', 'SHRUBLAND_TEMPERATE'], sav: 50, evil: 10, extinct: 'UNTAMED_WILDS', water: W({ river: ['TEMPERATE'], pool: ['TEMPERATE'], brook: true }) },
  evil_tundra_pools: { land: ['TUNDRA', 'FOREST_TAIGA'], sav: 50, evil: 90, extinct: 'WILDERNESS', water: W({ pool: ['TEMPERATE'] }) },
  savage_good_arctic_coast: { land: ['GLACIER', 'TUNDRA'], sav: 80, evil: 10, extinct: 'WILDERNESS', water: W({ ocean: ['ARCTIC'] }) },
};
const prm = Object.assign({}, sim.P0, { seed: true, weird: true, guarantee: true, links: 'network', network: { newrules: true } });
const out = {};
for (const [k, f] of Object.entries(FORTS)) {
  const spec = { land: f.land, rtype: { sav: f.sav, evil: f.evil, iso: false }, extinct: f.extinct, water: f.water, caverns: [1, 2, 3], assign: true, neighbours: [] };
  const B = sim.build(spec); sim.useBuild(B);
  const R = { seasons: 0, members: 0, unlinked: 0, seasonsUnlinked: 0, predators: 0, unfed: 0, cross: 0,
              cav: { casts: 0, members: 0, unlinked: 0, predators: 0, unfed: 0 }, names: {}, unfedNames: {} };
  for (let y = 0; y < YEARS; y++) {
    const cs = sim.year(B, spec, prm, 1, 250 + y);
    for (let s = 0; s < 4; s++) {
      R.cross += cs.cross[s].length;
      const H = sim.seasonHoles(cs, s, prm);
      if (H.surface) {
        const h = H.surface; R.seasons++; R.members += h.members; R.unlinked += h.unlinked.length; R.predators += h.predators; R.unfed += h.unfed.length;
        if (h.unlinked.length) R.seasonsUnlinked++;
        for (const t of h.unlinked) R.names[t] = (R.names[t] || 0) + 1;
        for (const t of h.unfed) R.unfedNames[t] = (R.unfedNames[t] || 0) + 1;
      }
      for (const L of ['cavern1', 'cavern2', 'cavern3']) if (H[L]) {
        const h = H[L], C = R.cav; C.casts++; C.members += h.members; C.unlinked += h.unlinked.length; C.predators += h.predators; C.unfed += h.unfed.length;
      }
    }
  }
  out[k] = R;
  const pc = (a, b) => (100 * a / b).toFixed(2) + '%';
  const top = Object.entries(R.names).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([t, n]) => `${t} ${n}`).join(', ');
  console.log(`${k.padEnd(28)} unlinked ${R.unlinked}/${R.members} (${pc(R.unlinked, R.members)}) seasons ${pc(R.seasonsUnlinked, R.seasons)} unfed ${R.unfed}/${R.predators} | caverns ${R.cav.unlinked} unlinked, ${R.cav.unfed} unfed | cross links/season ${(R.cross / R.seasons).toFixed(1)}${top ? ' | ' + top : ''}`);
}
if (process.argv[3]) require('fs').writeFileSync(process.argv[3], JSON.stringify({ years: YEARS, rules: DATA.meta.rules_version, forts: out }));
