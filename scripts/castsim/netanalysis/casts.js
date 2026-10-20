// Cast-level comparison: builders x forts, every cast scored on the New Rules web among its own members (actual seats).
const SP = process.argv[2], YEARS = +(process.argv[3] || 200);
const cur = require('/Users/nathanielcannon/Claude/Projects/DwarfCron/scripts/castsim/foodweb_sim.js').make(require('/Users/nathanielcannon/Claude/Projects/DwarfCron/data/castsim/foodweb/creatures.json'));
const old = require(SP + '/v3/foodweb_sim.js').make(require(SP + '/v3/creatures.json'));
const W = o => Object.assign({ ocean: null, lake: null, river: null, pool: null, brook: false }, o);
const FORTS = {
  terrifying_broadleaf_river: { land: ['FOREST_TEMPERATE_BROADLEAF'], sav: 80, evil: 90, extinct: 'UNTAMED_WILDS', water: W({ river: ['TEMPERATE'] }) },
  calm_temperate_lake: { land: ['FOREST_TEMPERATE_BROADLEAF', 'GRASSLAND_TEMPERATE'], sav: 50, evil: 50, extinct: 'UNTAMED_WILDS', water: W({ lake: ['TEMPERATE'] }) },
  savage_tropical_coast: { land: ['SHRUBLAND_TROPICAL', 'SWAMP_MANGROVE', 'FOREST_TROPICAL_MOIST_BROADLEAF'], sav: 80, evil: 50, extinct: 'UNTAMED_WILDS', water: W({ ocean: ['TROPICAL'], river: ['TROPICAL'] }) },
};
const NR = { newrules: true };
function rngOf(seed) { let a = seed | 0; return () => { a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const pickOf = r => arr => arr[Math.floor(r() * arr.length)];
function shuffle(r, a) { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }

const HOLES_ALL = {};
let HOLES;
for (const [fk, f] of Object.entries(FORTS)) {
  const spec = { land: f.land, rtype: { sav: f.sav, evil: f.evil, iso: false }, extinct: f.extinct, water: f.water, caverns: [1, 2, 3], assign: true, neighbours: [] };
  const B = cur.build(spec); cur.useBuild(B);
  const Bo = old.build(spec);
  const BY = cur.BY;
  // candidate New Rules graph per layer|season (any seat), for walks and degrees
  const cand = {};
  for (const key in B.lists) {
    const items = []; const seen = new Set();
    for (const x of B.lists[key]) { if (x.vfish || seen.has(x.c.t)) continue; seen.add(x.c.t); items.push(x); }
    const eaters = new Map(), prey = new Map(); items.forEach(x => { eaters.set(x.c.t, []); prey.set(x.c.t, []); });
    for (const a of items) if (!a.vermin) for (const b of items) if (a !== b && cur.linkWhy(a, b, key.split('|')[0], NR).length) { prey.get(a.c.t).push(b.c.t); eaters.get(b.c.t).push(a.c.t); }
    cand[key] = { items, by: new Map(items.map(x => [x.c.t, x])), eaters, prey };
  }
  // the New Rules edge between two seated members
  const ecache = new Map();
  function eats(L, a, b) {
    const k = L + '|' + a.t + '|' + a.slot + '|' + b.t + '|' + b.slot;
    if (!ecache.has(k)) {
      const ca = BY[a.t], cb = BY[b.t];
      ecache.set(k, !!(ca && cb && !a.vermin && cur.linkWhy({ c: ca, slots: [a.slot], vermin: false }, { c: cb, slots: [b.slot], vermin: b.vermin, vclass: cb.vc }, L, NR).length));
    }
    return ecache.get(k);
  }
  const lev = m => m.vermin ? 'vermin' : m.slot === 'apex' ? 'apex' : (cur.tierOf({ c: BY[m.t], slot: m.slot, vermin: false }) >= 2 ? 'predator' : 'prey');
  function score(L, members) {
    const ms = members.filter(m => BY[m.t]);
    const n = ms.length, out = ms.map(() => []), inn = ms.map(() => []);
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) if (i !== j && eats(L, ms[i], ms[j])) { out[i].push(j); inn[j].push(i); }
    const lv = ms.map(lev);
    const anim = ms.map((m, i) => i).filter(i => lv[i] !== 'vermin');
    const cons = anim.filter(i => lv[i] === 'apex' || lv[i] === 'predator'), pry = anim.filter(i => lv[i] === 'prey'), ver = ms.map((m, i) => i).filter(i => lv[i] === 'vermin');
    const reach = s => { const seen = new Set([s]), st = [s]; while (st.length) { const x = st.pop(); for (const y of out[x]) if (!seen.has(y)) { seen.add(y); st.push(y); } } return seen; };
    const apx = anim.filter(i => lv[i] === 'apex'); const fromApex = new Set(); apx.forEach(a => reach(a).forEach(x => fromApex.add(x)));
    // weak components
    const par = ms.map((m, i) => i); const fnd = x => par[x] === x ? x : (par[x] = fnd(par[x]));
    for (let i = 0; i < n; i++) for (const j of out[i]) par[fnd(i)] = fnd(j);
    const comps = new Set(ms.map((m, i) => fnd(i))).size;
    for (const i of cons) if (!out[i].length) HOLES.unfed[L + ' ' + BY[ms[i].t].nm + ' (' + ms[i].slot + ')'] = (HOLES.unfed[L + ' ' + BY[ms[i].t].nm + ' (' + ms[i].slot + ')'] || 0) + 1;
    for (const i of anim) if (!out[i].length && !inn[i].length) HOLES.orphan[L + ' ' + BY[ms[i].t].nm + ' (' + ms[i].slot + ')'] = (HOLES.orphan[L + ' ' + BY[ms[i].t].nm + ' (' + ms[i].slot + ')'] || 0) + 1;
    return { n: anim.length, v: ver.length, partner: anim.filter(i => out[i].length || inn[i].length).length, cons: cons.length, consFed: cons.filter(i => out[i].length).length,
      prey: pry.length, preyEaten: pry.filter(i => inn[i].length).length, verm: ver.length, vermEaten: ver.filter(i => inn[i].length).length,
      apex: apx.length, vermToApex: ver.filter(i => fromApex.has(i)).length, comps, mutual: 0 };
  }
  // ---- the walk prototype (user 20 Oct): per layer x season: non-apex seed and apex (both without replacement over the
  // year), N/4 of the layer's vermin dealt to each season, then a random walk from each vermin and the seed up its eaters
  // to the apex, keeping only steps that can still reach the apex
  function walkYear(r) {
    const pick = pickOf(r), casts = {};
    const layers = [...new Set(Object.keys(cand).map(k => k.split('|')[0]))];
    for (const L of layers) {
      const usedSeed = new Set(), usedApex = new Set();
      const allV = [...new Set([0, 1, 2, 3].flatMap(s => (cand[L + '|' + s] || { items: [] }).items.filter(x => x.vermin).map(x => x.c.t)))];
      const dealt = shuffle(r, allV), per = Math.max(1, Math.round(allV.length / 4));
      for (let s = 0; s < 4; s++) {
        const C = cand[L + '|' + s]; if (!C) continue;
        const apexes = C.items.filter(x => !x.vermin && x.slots.includes('apex'));
        let apex = pick(apexes.filter(x => !usedApex.has(x.c.t))) || pick(apexes);
        const res = { L, members: [], fail: { verm: 0, seed: 0, noApex: !apex } };
        if (!apex) { casts[L + '|' + s] = res; continue; }
        usedApex.add(apex.c.t);
        // descendants of the apex (it can reach them by eating down)
        const D = new Set([apex.c.t]), st = [apex.c.t];
        while (st.length) { const x = st.pop(); for (const y of C.prey.get(x)) if (!D.has(y)) { D.add(y); st.push(y); } }
        const chosen = new Map([[apex.c.t, 'apex']]);
        const walk = t => { let x = t; let guard = 0; while (x !== apex.c.t && guard++ < 50) { const up = C.eaters.get(x).filter(e => D.has(e)); if (!up.length) return false; x = pick(up); if (!chosen.has(x)) chosen.set(x, null); } return true; };
        const seeds = shuffle(r, C.items.filter(x => !x.vermin && !x.slots.includes('apex') && !usedSeed.has(x.c.t)));
        let seed = seeds.find(x => D.has(x.c.t));
        if (!seed) res.fail.seed = 1; else { usedSeed.add(seed.c.t); chosen.set(seed.c.t, null); walk(seed.c.t); }
        const vs = dealt.slice(s * per, (s + 1) * per).filter(t => C.by.has(t));
        for (const t of vs) { if (!D.has(t)) { res.fail.verm++; continue; } chosen.set(t, null); walk(t); }
        for (const [t, seat] of chosen) { const x = C.by.get(t); res.members.push({ t, vermin: x.vermin, slot: seat || (x.vermin ? 'vermin' : (x.slots.find(z => z !== 'apex') || x.slots[0])) }); }
        casts[L + '|' + s] = res;
      }
    }
    return casts;
  }
  const builders = {
    'old builder (ladder v7.6.1)': y => old.year(Bo, spec, Object.assign({}, old.P0, { seed: true, weird: true, guarantee: true, links: 'engine' }), 1, 250 + y),
    'builder today (ladder)': y => cur.year(B, spec, Object.assign({}, cur.P0, { seed: true, weird: true, guarantee: true, links: 'engine' }), 1, 250 + y),
    'builder on New Rules': y => cur.year(B, spec, Object.assign({}, cur.P0, { seed: true, weird: true, guarantee: true, links: 'network', network: NR }), 1, 250 + y),
    'walk prototype': y => walkYear(rngOf(7919 * y + 13)),
  };
  const report = {};
  for (const [bn, fn] of Object.entries(builders)) {
    HOLES = HOLES_ALL[fk + ' | ' + bn] = { unfed: {}, orphan: {} };
    const agg = {}, inc = {}, castsPer = {}, fails = { verm: 0, seed: 0 };
    for (let y = 0; y < YEARS; y++) {
      const cs = fn(y);
      for (const key in cs) {
        const tr = cs[key], L = tr.L.startsWith('cavern') ? 'caverns' : tr.L;
        const mem = tr.members ? (tr.members[0] && 'slot' in tr.members[0] && tr.vermin === undefined ? tr.members : tr.members.map(m => ({ t: m.t, slot: m.slot, vermin: false })).concat((tr.vermin || []).map(v => ({ t: v.t, slot: 'vermin', vermin: true })))) : [];
        if (tr.fail) { fails.verm += tr.fail.verm; fails.seed += tr.fail.seed; }
        const sc = score(tr.L, mem), A = (agg[L] = agg[L] || {});
        for (const k in sc) A[k] = (A[k] || 0) + sc[k]; A.casts = (A.casts || 0) + 1; A.isolatedCasts = (A.isolatedCasts || 0) + (sc.partner < sc.n ? 1 : 0); A.unfedCasts = (A.unfedCasts || 0) + (sc.consFed < sc.cons ? 1 : 0); A.uneatenCasts = (A.uneatenCasts || 0) + (sc.preyEaten < sc.prey ? 1 : 0);
        castsPer[tr.L] = (castsPer[tr.L] || 0) + 1;
        for (const m of mem) if (!m.vermin) { const id = tr.L + '|' + m.t; inc[id] = (inc[id] || 0) + 1; }
      }
    }
    // evenness of selection per layer over eligible non-vermin species, and hub inflation (inclusion vs candidate degree)
    const even = {};
    for (const key of Object.keys(cand).filter(k => k.endsWith('|0'))) {
      const L = key.split('|')[0], Lg = L.startsWith('cavern') ? 'caverns' : L;
      const elig = new Map();
      for (let s = 0; s < 4; s++) { const C = cand[L + '|' + s]; if (!C) continue; for (const x of C.items) if (!x.vermin) { const d = C.eaters.get(x.c.t).length + C.prey.get(x.c.t).length; elig.set(x.c.t, (elig.get(x.c.t) || 0) + d / 4); } }
      const ts = [...elig.keys()], rate = ts.map(t => (inc[L + '|' + t] || 0) / (castsPer[L] || 1)), deg = ts.map(t => elig.get(t));
      const rank = a => { const o = a.map((v, i) => [v, i]).sort((p, q) => p[0] - q[0]); const r = new Array(a.length); o.forEach(([, i], k) => r[i] = k); return r; };
      const r1 = rank(rate), r2 = rank(deg), mean = r1.reduce((p, q) => p + q, 0) / r1.length;
      let num = 0, d1 = 0, d2 = 0; for (let i = 0; i < r1.length; i++) { num += (r1[i] - mean) * (r2[i] - mean); d1 += (r1[i] - mean) ** 2; d2 += (r2[i] - mean) ** 2; }
      const srt = rate.slice().sort((p, q) => p - q), tot = srt.reduce((p, q) => p + q, 0);
      const gini = tot ? srt.reduce((p, x, i) => p + (2 * (i + 1) - srt.length - 1) * x, 0) / (srt.length * tot) : 0;
      const E = (even[Lg] = even[Lg] || { elig: 0, ever: 0, gini: [], rho: [] });
      E.elig += ts.length; E.ever += rate.filter(x => x > 0).length; E.gini.push(gini); E.rho.push(d1 && d2 ? num / Math.sqrt(d1 * d2) : 0);
      if (L === 'ground') E.top = ts.map((t, i) => [BY[t].nm, rate[i], deg[i]]).sort((p, q) => q[1] - p[1]).slice(0, 5).map(([nm, r, d]) => `${nm} ${(100 * r).toFixed(0)}% (deg ${d.toFixed(0)})`);
    }
    report[bn] = { agg, even, fails };
  }
  console.log('\n######## ' + fk + ` (${YEARS} years)`);
  for (const [bn, R] of Object.entries(report)) {
    console.log(`\n== ${bn}` + (bn === 'walk prototype' ? `  (vermin with no path to the season's apex: ${R.fails.verm}; seasons with no reachable seed: ${R.fails.seed})` : ''));
    for (const [L, A] of Object.entries(R.agg)) {
      const E = R.even[L] || {}; const pct = (a, b) => b ? (100 * a / b).toFixed(0) + '%' : '-';
      console.log(`  ${L.padEnd(8)} CASTS WITH: a member with no partner ${pct(A.isolatedCasts, A.casts)}, a predator with no prey ${pct(A.unfedCasts, A.casts)}, a prey nothing eats ${pct(A.uneatenCasts, A.casts)}`);
      console.log(`  ${L.padEnd(8)} animals/cast ${(A.n / A.casts).toFixed(1)} vermin/cast ${(A.v / A.casts).toFixed(1)} | with an in-cast partner ${pct(A.partner, A.n)} | eaters fed ${pct(A.consFed, A.cons)} | prey eaten ${pct(A.preyEaten, A.prey)} | vermin eaten ${pct(A.vermEaten, A.verm)} | vermin under an apex ${pct(A.vermToApex, A.verm)} | web pieces/cast ${(A.comps / A.casts).toFixed(1)} | species ever cast ${E.ever}/${E.elig} | gini ${E.gini ? (E.gini.reduce((p, q) => p + q, 0) / E.gini.length).toFixed(2) : '-'} | rho(rate,degree) ${E.rho ? (E.rho.reduce((p, q) => p + q, 0) / E.rho.length).toFixed(2) : '-'}`);
      if (E.top) console.log('           most cast on land-ground: ' + E.top.join('; '));
    }
  }
}

require('fs').writeFileSync(SP + '/graph/holes.json', JSON.stringify(HOLES_ALL));
