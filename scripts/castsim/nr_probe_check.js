// New Rules rig probe check (rebuild plan rev 7, Phase D). Holds what the engine did on a real fort -- `seasonal-wildlife
// cast nrprobe PATH` -- to the Food Web Explorer:
//   1. records: the engine's creature records (read from DF's raws) against the explorer's (the desk export), field by field;
//   2. casts: the explorer's builder run on the engine's own context and season lists at the engine's site and year must
//      build the engine's casts (members and slots, vermin, seed, bonus seats, edges) and its cross-layer links;
//   3. vermin writes: what each consumer's written class tags and names feed is exactly the explorer's gobble + mass links
//      over the vermin present, within a realm;
//   4. relations: the season's pair set is the explorer's casts' edges + cross links; every relation written is in it.
// Usage: node nr_probe_check.js PROBE.json [--verbose]
const path = require('path');
const P = require(path.resolve(process.argv[2]));
const VERBOSE = process.argv.includes('--verbose');
const DATA = require(path.resolve(__dirname, '../../data/castsim/foodweb/creatures.json'));
const SIM = require(path.resolve(__dirname, 'foodweb_sim.js'));
const EX = {}; for (const c of DATA.creatures) EX[c.t] = c;
let fails = 0;
const say = (ok, line) => { if (!ok) fails++; console.log((ok ? 'PASS ' : 'FAIL ') + line); };
const arr = x => Array.isArray(x) ? x : (x && typeof x === 'object' ? Object.values(x) : []);   // Lua's empty table -> {}
const norm = r => Object.assign({}, r, { cc: arr(r.cc), gvc: arr(r.gvc), gvt: arr(r.gvt), wb: arr(r.wb) });
const REC = {}; for (const t in P.records) REC[t] = norm(P.records[t]);

// ---------------------------------------------------------------- 1. records
const FIELDS = ['g', 'h', 'ro', 'm', 'c0', 'c1', 'v', 'vc', 'swv', 'bn', 'gi', 'ap', 'apv', 'civ', 'se', 'lp', 'rt', 'gob', 'carn', 'grz', 'lg',
  'amb', 'wb', 'ex', 'fa', 'bo', 'pet', 'war', 'wd', 'cc', 'gvc', 'gvt', 'dhv'];
const onFort = new Set(Object.keys(P.P));
const field = {}, examples = {};
let compared = 0, missing = [];
for (const t of onFort) {
  const e = REC[t], x = EX[t];
  if (!e) continue;
  if (!x) { missing.push(t); continue; }
  compared++;
  for (const f of FIELDS) {
    let a = e[f], b = x[f];
    if (a === undefined) a = null; if (b === undefined) b = null;
    if (Array.isArray(a) || Array.isArray(b)) { a = JSON.stringify([...(a || [])].sort()); b = JSON.stringify([...(b || [])].sort()); }
    if (f === 'vc' || f === 'swv') { if (!e.v && !x.v) continue; }
    if (a !== b && !(a === null && b === false) && !(a === false && b === null)) {
      field[f] = (field[f] || 0) + 1;
      (examples[f] = examples[f] || []).push(`${t}: engine ${a} explorer ${b}`);
    }
  }
}
const nf = Object.keys(field).length;
say(nf === 0, `records: ${compared} species on the fort's layers compared field by field` + (nf ? `; differing fields: ${Object.entries(field).map(([f, n]) => f + ' ' + n).join(', ')}` : ''));
if (missing.length) console.log(`     ${missing.length} on the fort not in the explorer's export (not natural there or not wild): ${missing.slice(0, 12).join(', ')}`);
for (const f in examples) console.log(`     ${f}: ${examples[f].slice(0, VERBOSE ? 50 : 5).join(' | ')}`);

// ---------------------------------------------------------------- 2. casts, on the engine's own context and lists
const creatures = Object.values(REC).map(r => Object.assign({ nm: (EX[r.t] && EX[r.t].nm) || r.t.toLowerCase(), b: (EX[r.t] && EX[r.t].b) || [] }, r));
const sim = SIM.make({ meta: DATA.meta, creatures });
const BY = sim.BY;
const Pmap = {}; for (const t in P.P) Pmap[t] = { c: BY[t], layers: arr(P.P[t].layers) };
const lists = {};
for (const k in P.lists) lists[k] = arr(P.lists[k]).map(x => ({ c: BY[x.t], vermin: !!x.vermin, vclass: x.vclass || null, slots: arr(x.slots), tier: x.tier || null, vfish: !!x.vfish }));
const apexOn = {}; for (const t in P.apexOn) apexOn[t] = Object.assign({}, P.apexOn[t], { apexL: arr(P.apexOn[t].apexL) });
const mapOnly = {}; for (const t in P.mapOnly) mapOnly[t] = { sides: arr(P.mapOnly[t].sides) };
const B = { P: Pmap, promoted: new Set(arr(P.promoted)), mapOnly, apexOn, lists, active: arr(P.active), sub: P.sub || null };
sim.useBuild(B);
const prm = Object.assign({}, P.prm, { links: 'network', network: { newrules: true } });
console.log(`     build inputs: ${P.fromBuild ? 'the build\'s own (records as read at the build)' : 'read afresh at the probe (casts built in an earlier session)'}`);
if (P.salt) console.log(`     note: salt ${P.salt} (the explorer's year() has none) -- casts will differ`);
const cs = sim.year(B, {}, prm, P.site, P.year);
let castDiff = 0;
for (const key in P.casts) {
  const e = P.casts[key], j = cs[key];
  if (!j) { castDiff++; console.log(`     ${key}: explorer built no cast`); continue; }
  const em = arr(e.members).map(m => m[0] + ':' + m[1]).sort().join(','), jm = j.members.map(m => m.t + ':' + m.slot).sort().join(',');
  const ev = arr(e.vermin).slice().sort().join(','), jv = j.vermin.map(v => v.t).sort().join(',');
  const ee = arr(e.edges).slice().sort().join(','), je = j.edges.map(x => x[0] + '>' + x[1]).sort().join(',');
  const eb = arr(e.bonus).slice().sort().join(','), jb = (j.bonus || []).slice().sort().join(',');
  const ok = em === jm && ev === jv && (e.seed || null) === (j.seed || null) && eb === jb && ee === je && e.built === j.built;
  if (!ok) {
    castDiff++;
    if (castDiff <= 6) console.log(`     ${key}: members ${em === jm ? 'same' : `engine [${em}] explorer [${jm}]`}; vermin ${ev === jv ? 'same' : `engine [${ev}] explorer [${jv}]`}; seed ${e.seed}/${j.seed}; bonus ${eb}/${jb}; edges ${ee === je ? 'same' : 'differ'}; built ${e.built}/${j.built}`);
  }
}
say(castDiff === 0, `casts: ${Object.keys(P.casts).length} casts at site ${P.site}, year ${P.year}: the explorer's builder on the engine's context ${castDiff ? 'differs on ' + castDiff : 'builds the same casts (members, slots, vermin, seed, bonus seats, edges, order)'}`);
let crossDiff = 0;
for (let s = 0; s < 4; s++) {
  const e = arr(P.cross[s]).slice().sort().join(','), j = cs.cross[s].map(x => x.slice(0, 4).join('|')).sort().join(',');
  if (e !== j) { crossDiff++; console.log(`     cross season ${s}: engine ${arr(P.cross[s]).length} explorer ${cs.cross[s].length}`); }
}
say(crossDiff === 0, `cross-layer links: ${arr(P.cross).reduce((a, x) => a + arr(x).length, 0)} over four seasons ${crossDiff ? 'differ in ' + crossDiff + ' season(s)' : 'equal the explorer\'s'}`);

// ---------------------------------------------------------------- 3. vermin writes (on the writer's own records, read when it ran)
let wsim = sim, wPmap = Pmap;
if (P.writeRecords) {
  const WR = {}; for (const t in P.writeRecords) WR[t] = norm(P.writeRecords[t]);
  wsim = SIM.make({ meta: DATA.meta, creatures: Object.values(WR).map(r => Object.assign({ nm: r.t.toLowerCase(), b: (EX[r.t] && EX[r.t].b) || [] }, r)) });
  wPmap = {}; for (const t in (P.writeP || {})) wPmap[t] = { c: wsim.BY[t], layers: arr(P.writeP[t].layers) };
  wsim.useBuild(Object.assign({}, B, { P: wPmap }));
}
const SURF = new Set(['ground', 'flying', 'ocean', 'fresh']);
const realmOf = L => SURF.has(L) ? 'surface' : L;
const present = new Set(); for (const cls in P.gobbleMembers || {}) for (const t of arr(P.gobbleMembers[cls])) present.add(t);
const layersOf = t => (wPmap[t] && wPmap[t].layers) || [];
let wN = 0, wBad = 0;
const wEx = [];
for (const a of arr(P.consumersPresent)) {
  const A = wsim.BY[a];
  if (!A || A.v) continue;
  const g = P.gobble[a] || { tags: [], names: [] };
  const tags = new Set(arr(g.tags)), names = new Set(arr(g.names));
  const la = layersOf(a);
  for (const v of present) {
    const V = wsim.BY[v];
    if (!V) continue;
    const lb = layersOf(v), off = lb.length === 0 && mapOnly[v];
    const pairs = [];
    for (const La of la) {
      if (off) { if (SURF.has(La)) pairs.push([La, false]); continue; }
      for (const Lb of lb) { if (La === Lb) pairs.push([La, false]); else if (SURF.has(La) && SURF.has(Lb)) pairs.push([La, true]); }
    }
    if (!pairs.length) continue;
    wN++;
    let want = false;
    for (const [L, cross] of pairs) {
      const on = cross ? { newrules: true, hunt: false, ladder: false, crossLayer: true } : { newrules: true };
      const ok = wsim.NEW_RULES.filter(r => r.id === 'gobble' || r.id === 'mass').some(r => r.test({ c: A, slots: [], vermin: false }, { c: V, slots: ['vermin'], vermin: true, vclass: V.vc }, L, on));
      if (ok) want = true;
    }
    let fed = names.has(v);
    for (const sd of wsim.sidesOf(v)) if (tags.has((V.swv || '') + '@' + sd)) fed = true;
    if (fed !== want) { wBad++; if (wEx.length < 8) wEx.push(`${a} -> ${v}: written feeds ${fed}, New Rules ${want}`); }
  }
}
say(wBad === 0, `vermin writes: ${wN} consumer x vermin pairs present within a realm; what the written tags and names feed ${wBad ? 'differs on ' + wBad : 'is exactly New Rules\''}`);
for (const x of wEx) console.log('     ' + x);

sim.useBuild(B);
// ---------------------------------------------------------------- 4. relations
const s = P.season;
const jset = new Set();
for (const key in cs) if (key.endsWith('|' + s)) for (const [x, y] of cs[key].edges) jset.add(x + '|' + y);
for (const x of cs.cross[s]) jset.add(x[0] + '|' + x[2]);
const eset = new Set(arr(P.seasonPairs));
const onlyE = [...eset].filter(k => !jset.has(k)), onlyJ = [...jset].filter(k => !eset.has(k));
say(onlyE.length === 0 && onlyJ.length === 0, `season ${s} pairs: engine ${eset.size}, explorer ${jset.size}` + (onlyE.length + onlyJ.length ? `; engine only ${onlyE.slice(0, 5).join(' ')}; explorer only ${onlyJ.slice(0, 5).join(' ')}` : ', the same'));
const rel = arr(P.relations).map(r => r[0]);
const outside = rel.filter(k => !eset.has(k) && !k.endsWith('|DOMESTIC'));
say(outside.length === 0, `relations written: ${rel.length} species pairs (${rel.join(', ') || 'none yet'}); ${outside.length ? outside.length + ' outside the season set: ' + outside.join(', ') : 'all in the season set (or a fort animal)'}`);
console.log(fails === 0 ? 'nr probe: the engine follows New Rules on this fort' : `nr probe: ${fails} check(s) failed`);
process.exit(fails ? 1 : 0);
