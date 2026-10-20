// Season casts scored together: the surface realm (land-ground + land-flying + ocean + freshwater casts of one season)
// joined by the cross-layer links New Rules allows; each cavern alone; and caverns joined (hypothetical).
const SP = process.argv[2], YEARS = +(process.argv[3] || 200);
const DATA = require('/Users/nathanielcannon/Claude/Projects/DwarfCron/data/castsim/foodweb/creatures.json');
const sim = require(SP + '/graph/sim_proto.js').make(DATA);
const BY = sim.BY, NR = { newrules: true }, NRX = { newrules: true, hunt: false, ladder: false, crossLayer: true };
const W = o => Object.assign({ ocean: null, lake: null, river: null, pool: null, brook: false }, o);
const FORTS = {
  terrifying_broadleaf_river: { land: ['FOREST_TEMPERATE_BROADLEAF'], sav: 80, evil: 90, extinct: 'UNTAMED_WILDS', water: W({ river: ['TEMPERATE'] }) },
  calm_temperate_lake: { land: ['FOREST_TEMPERATE_BROADLEAF', 'GRASSLAND_TEMPERATE'], sav: 50, evil: 50, extinct: 'UNTAMED_WILDS', water: W({ lake: ['TEMPERATE'] }) },
  savage_tropical_coast: { land: ['SHRUBLAND_TROPICAL', 'SWAMP_MANGROVE', 'FOREST_TROPICAL_MOIST_BROADLEAF'], sav: 80, evil: 50, extinct: 'UNTAMED_WILDS', water: W({ ocean: ['TROPICAL'], river: ['TROPICAL'] }) },
  good_temperate_brook: { land: ['FOREST_TEMPERATE_CONIFER', 'SHRUBLAND_TEMPERATE'], sav: 50, evil: 10, extinct: 'UNTAMED_WILDS', water: W({ river: ['TEMPERATE'], pool: ['TEMPERATE'], brook: true }) },
  evil_tundra_pools: { land: ['TUNDRA', 'FOREST_TAIGA'], sav: 50, evil: 90, extinct: 'WILDERNESS', water: W({ pool: ['TEMPERATE'] }) },
  savage_good_arctic_coast: { land: ['GLACIER', 'TUNDRA'], sav: 80, evil: 10, extinct: 'WILDERNESS', water: W({ ocean: ['ARCTIC'] }) },
};
const SURF = ['ground', 'flying', 'ocean', 'fresh'];
const G2 = new Set(['GIANT_MOSQUITO', 'GIANT_DRAGONFLY']);
const ecache = new Map();
function edge(a, b) {   // a, b: {t, L, slot, vermin}; a eats b?
  if (a.vermin || a.t === b.t) return false;
  const k = a.t + a.L + a.slot + '|' + b.t + b.L + b.slot;
  if (!ecache.has(k)) {
    const ca = BY[a.t], cb = BY[b.t];
    const on = a.L === b.L ? NR : NRX;
    ecache.set(k, !!(ca && cb && sim.linkWhy({ c: ca, slots: [a.slot], vermin: false }, { c: cb, slots: [b.slot], vermin: b.vermin, vclass: cb.vc }, a.L, on).length));
  }
  return ecache.get(k);
}
const lev = m => m.vermin ? 'vermin' : m.slot === 'apex' ? 'apex' : (sim.tierOf({ c: BY[m.t], slot: m.slot, vermin: false }) >= 2 ? 'predator' : 'prey');
// score one realm: entries = seated members of several casts (a species may hold seats in two casts: one node)
function realm(entries, joinAcross) {
  const toks = [...new Set(entries.map(e => e.t))], ix = new Map(toks.map((t, i) => [t, i]));
  const seats = toks.map(() => []); entries.forEach(e => seats[ix.get(e.t)].push(e));
  const n = toks.length, out = toks.map(() => new Set()), inn = toks.map(() => new Set());
  const within = toks.map(() => new Set()), across = toks.map(() => new Set());
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
    if (i === j) continue;
    let same = false, cross = false;
    for (const a of seats[i]) for (const b of seats[j]) {
      if (a.L !== b.L && !joinAcross) continue;
      if (edge(a, b)) { if (a.L === b.L) same = true; else cross = true; }
    }
    if (same || cross) { out[i].add(j); inn[j].add(i); }
    if (same) { within[i].add(j); within[j].add(i); }
    if (cross && !same) { across[i].add(j); across[j].add(i); }
  }
  // a pair linked within a cast counts as within even if also across
  for (let i = 0; i < n; i++) for (const j of within[i]) across[i].delete(j);
  const lv = toks.map((t, i) => lev(seats[i][0]));
  const L0 = toks.map((t, i) => seats[i][0].L);
  const deg = i => new Set([...out[i], ...inn[i]]).size;
  const comps = () => { const p = toks.map((t, i) => i), f = x => p[x] === x ? x : (p[x] = f(p[x])); for (let i = 0; i < n; i++) for (const j of out[i]) p[f(i)] = f(j); return new Set(toks.map((t, i) => f(i))).size; };
  const C = comps();
  // articulation points that join layers: removing i splits the realm into more pieces and separates two layers
  const bridges = [];
  if (joinAcross) for (let i = 0; i < n; i++) {
    if (!across[i].size) continue;
    const p = toks.map((t, k) => k), f = x => p[x] === x ? x : (p[x] = f(p[x]));
    for (let a = 0; a < n; a++) if (a !== i) for (const b of out[a]) if (b !== i) p[f(a)] = f(b);
    const pieces = new Set(toks.map((t, k) => k).filter(k => k !== i).map(f)).size;
    if (pieces > C) bridges.push(toks[i]);
  }
  return { n, toks, lv, L0, out, inn, within, across, deg, C, bridges, seats };
}
const report = {};
for (const [fk, f] of Object.entries(FORTS)) {
  const spec = { land: f.land, rtype: { sav: f.sav, evil: f.evil, iso: false }, extinct: f.extinct, water: f.water, caverns: [1, 2, 3], assign: true, neighbours: [] };
  const variants = {
    'New Rules builder (today)': { prm: { links: 'network', network: NR }, g2: false },
    'G2 + G3 (flying grown, giant bugs off flying)': { prm: { links: 'network', network: NR, flyGrow: true }, g2: true },
  };
  report[fk] = {};
  for (const [vn, V] of Object.entries(variants)) {
    const B = sim.build(spec);
    if (V.g2) for (const k in B.lists) if (k.startsWith('flying|')) B.lists[k] = B.lists[k].filter(x => !G2.has(x.c.t));
    sim.useBuild(B);
    const prm = Object.assign({}, sim.P0, { seed: true, weird: true, guarantee: true }, V.prm);
    const R = { surf: { seasons: 0, members: 0, orphLayer: 0, orphRealm: 0, castsOrphLayer: 0, castsOrphRealm: 0, unfedLayer: 0, unfedRealm: 0, uneatenLayer: 0, uneatenRealm: 0, cons: 0, prey: 0, comps: 0, rescued: {}, leafAcross: {}, bridge: {}, homeElsewhere: {}, orphNames: {} },
                cav: { seasons: 0, members: 0, orphOwn: 0, orphJoined: 0, unfedOwn: 0, unfedJoined: 0, cons: 0, rescued: {} } };
    const bump = (o, k) => o[k] = (o[k] || 0) + 1;
    for (let y = 0; y < YEARS; y++) {
      const cs = sim.year(B, spec, prm, 1, 250 + y);
      for (let s = 0; s < 4; s++) {
        const ent = L => { const tr = cs[L + '|' + s]; if (!tr) return []; return tr.members.map(m => ({ t: m.t, L, slot: m.slot, vermin: false })).concat(tr.vermin.map(v => ({ t: v.t, L, slot: 'vermin', vermin: true }))); };
        // ---- surface
        const E = SURF.flatMap(ent).filter(e => BY[e.t]);
        if (E.length) {
          const per = realm(E, false), J = realm(E, true), S = R.surf;
          S.seasons++; S.members += J.n; S.comps += J.C;
          let oL = 0, oR = 0;
          for (let i = 0; i < J.n; i++) {
            const nm = BY[J.toks[i]].nm + ' (' + J.L0[i] + ')';
            const dL = per.deg(i), dR = J.deg(i);
            if (!dL) oL++; if (!dR) { oR++; bump(S.orphNames, nm); }
            if (!dL && dR) bump(S.rescued, nm);
            if (dR === 1 && J.across[i].size === 1 && !J.within[i].size) bump(S.leafAcross, nm);
            if (J.across[i].size > J.within[i].size && J.within[i].size >= 0 && J.across[i].size) bump(S.homeElsewhere, nm);
            if (J.lv[i] === 'apex' || J.lv[i] === 'predator') { S.cons++; if (!per.out[i].size) S.unfedLayer++; if (!J.out[i].size) S.unfedRealm++; }
            if (J.lv[i] === 'prey') { S.prey++; if (!per.inn[i].size) S.uneatenLayer++; if (!J.inn[i].size) S.uneatenRealm++; }
          }
          S.orphLayer += oL; S.orphRealm += oR; if (oL) S.castsOrphLayer++; if (oR) S.castsOrphRealm++;
          for (const t of J.bridges) bump(S.bridge, BY[t].nm);
        }
        // ---- caverns: each alone (New Rules: one realm per cavern) vs joined (hypothetical)
        const CE = ['cavern1', 'cavern2', 'cavern3'].flatMap(ent).filter(e => BY[e.t]);
        if (CE.length) {
          const own = realm(CE, false), J = realm(CE, true), K = R.cav;
          K.seasons++; K.members += J.n;
          for (let i = 0; i < J.n; i++) {
            if (!own.deg(i)) K.orphOwn++; if (!J.deg(i)) K.orphJoined++;
            if (!own.deg(i) && J.deg(i)) bump(K.rescued, BY[J.toks[i]].nm);
            if (J.lv[i] === 'apex' || J.lv[i] === 'predator') { K.cons++; if (!own.out[i].size) K.unfedOwn++; if (!J.out[i].size) K.unfedJoined++; }
          }
        }
      }
    }
    report[fk][vn] = R;
  }
}
require('fs').writeFileSync(SP + '/graph/realm.json', JSON.stringify(report));
const pct = (a, b) => b ? (100 * a / b).toFixed(1) + '%' : '-';
const top = (o, k = 6) => Object.entries(o).sort((a, b) => b[1] - a[1]).slice(0, k).map(([n, c]) => `${n} x${c}`).join('; ') || 'none';
for (const [fk, V] of Object.entries(report)) {
  console.log('\n######## ' + fk);
  for (const [vn, R] of Object.entries(V)) {
    const S = R.surf, K = R.cav;
    console.log(`== ${vn}`);
    console.log(`  SURFACE seasons ${S.seasons}: members with no partner  per layer ${pct(S.orphLayer, S.members)} -> joined ${pct(S.orphRealm, S.members)} | seasons with any  ${pct(S.castsOrphLayer, S.seasons)} -> ${pct(S.castsOrphRealm, S.seasons)} | predators with no prey ${pct(S.unfedLayer, S.cons)} -> ${pct(S.unfedRealm, S.cons)} | prey nothing eats ${pct(S.uneatenLayer, S.prey)} -> ${pct(S.uneatenRealm, S.prey)} | pieces per joined season ${(S.comps / S.seasons).toFixed(2)}`);
    console.log(`    still alone when joined: ${top(S.orphNames)}`);
    console.log(`    rescued only by another layer: ${top(S.rescued)}`);
    console.log(`    one-link leaves whose neighbour is in another layer: ${top(S.leafAcross)}`);
    console.log(`    more links in another layer than its own: ${top(S.homeElsewhere)}`);
    console.log(`    bridges (removing it splits layers apart): ${top(S.bridge)}`);
    console.log(`  CAVERNS seasons ${K.seasons}: no partner each cavern alone ${pct(K.orphOwn, K.members)} -> joined (hypothetical) ${pct(K.orphJoined, K.members)} | predators with no prey ${pct(K.unfedOwn, K.cons)} -> ${pct(K.unfedJoined, K.cons)} | rescued by another cavern: ${top(K.rescued, 4)}`);
  }
}
