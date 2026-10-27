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
// a context the engine used that is not the build's (the added layer's growth, the vermin writer): its map-only species,
// apex flags and promotions, on the probe's records and layers
const ctxOf = X => {
  if (!X) return B;
  const ao = {}; for (const t in X.apexOn || {}) ao[t] = Object.assign({}, X.apexOn[t], { apexL: arr(X.apexOn[t].apexL) });
  const mo = {}; for (const t in X.mapOnly || {}) mo[t] = { sides: arr(X.mapOnly[t].sides) };
  return Object.assign({}, B, { promoted: new Set(arr(X.promoted)), mapOnly: mo, apexOn: ao });
};
sim.useBuild(B);
const prm = Object.assign({}, P.prm, { links: 'network', network: { newrules: true } });
console.log(`     build inputs: ${P.fromBuild ? 'the build\'s own (records as read at the build)' : 'read afresh at the probe (casts built in an earlier session)'}`);
if (P.salt) console.log(`     note: salt ${P.salt} (the explorer's year() has none) -- casts will differ`);
// a layer cast after the build (sw ROSTER.castAddMissing: its water found later) is grown after the year, as the engine
// grows it: the year without it, then its four seasons on the year's repeat counts with V7.NR's seeds, then the season's
// cross-layer links over every cast
const added = Object.keys(P.added || {}).filter(L => B.active.includes(L));
// v8 (user 27 Oct, flier seeds): the probe's own surroundings (sw-wt/plugin's nrprobe already writes ctx.surroundings), not
// a spec for the explorer to re-derive one from -- the probe holds no biome list, so {} always read back as 'calm' here.
const spec = { surroundings: P.surroundings };
let cs;
if (!added.length) cs = sim.year(B, spec, prm, P.site, P.year);
else {
  console.log(`     ${added.join(', ')} cast after the build: the explorer grows ${added.length > 1 ? 'them' : 'it'} after the year, as the engine does` + (P.crossAdded ? '' : ' (engine: no cross-layer relink after the add)'));
  const y0 = sim.year(Object.assign({}, B, { active: B.active.filter(L => !added.includes(L)) }), spec, prm, P.site, P.year);
  const used = {}, out = {};
  let built = 0, n = 0;
  sim.useBuild(ctxOf(P.addCtx));   // the added layer grows on the fort as the engine read it then
  for (const key in y0) { out[key] = y0[key]; built++; for (const m of y0[key].members) { const k = m.slot === 'sentient' ? 'SN|' + m.t : m.t; used[k] = (used[k] || 0) + 1; } }
  for (let s0 = 0; s0 < 4; s0++) for (const L of added) {
    n++;
    const seed = (P.site * 7919 + P.year * 104729 + s0 * 131 + sim.LAYERS.indexOf(L) * 17) % 2147483647;
    const tr = sim.cast(B.lists[L + '|' + s0], L, B.sub, used, sim.Rng(seed), prm, spec);
    tr.built = built + n;
    out[L + '|' + s0] = tr;
  }
  const on = Object.assign({}, prm.network || {}, { hunt: false, ladder: false, crossLayer: true });
  Object.defineProperty(out, 'cross', { value: [0, 1, 2, 3].map(s0 => sim.crossLinks(out, s0, on)), enumerable: false });
  cs = out;
  sim.useBuild(B);
}
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
  wsim.useBuild(Object.assign({}, ctxOf(P.writeCtx), { P: wPmap }));
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
// ---------------------------------------------------------------- helpers: season pair sets, seats, the outsider rule
const pairSet = s0 => {
  const out = new Set();
  for (const key in cs) if (key.endsWith('|' + s0)) for (const [x, y] of cs[key].edges) out.add(x + '|' + y);
  for (const x of cs.cross[s0]) out.add(x[0] + '|' + x[2]);
  return out;
};
const seatedIn = s0 => {
  const out = new Set();
  for (const key in cs) if (key.endsWith('|' + s0)) { for (const m of cs[key].members) out.add(m.t); for (const v of cs[key].vermin) out.add(v.t); }
  return out;
};
// a pair with a side outside the season's casts: New Rules on every layer both are on, with each side's slots (V7.NR.outsider)
const within = Object.assign({}, prm.network || {}), across = Object.assign({}, within, { hunt: false, ladder: false, crossLayer: true });
const outsider = (ta, tb, now = true) => {
  if (now && P.castMembers && P.castMembers[ta] && P.castMembers[tb]) return false;   // ROSTER.castOutsider: two members keep to the casts
  if (now && P.inSeason && !(P.inSeason[ta] && P.inSeason[tb])) return false;          // ... and both sides must be in season
  const A = BY[ta], Bc = BY[tb];
  if (!A || !Bc || A.v || Bc.v) return false;
  const sa = (P.slotsBy || {})[ta] || {}, sb = (P.slotsBy || {})[tb] || {};
  for (const La of (Pmap[ta] && Pmap[ta].layers) || []) for (const Lb of (Pmap[tb] && Pmap[tb].layers) || []) {
    if (La !== Lb && !(SURF.has(La) && SURF.has(Lb))) continue;
    if (sim.linkWhy({ c: A, slots: arr(sa[La]), vermin: false }, { c: Bc, slots: arr(sb[Lb]), vermin: false, vclass: Bc.vc }, La, La === Lb ? within : across).length) return true;
  }
  return false;
};
// ---------------------------------------------------------------- 4. relations
const s = P.season;
const jset = new Set();
for (const key in cs) if (key.endsWith('|' + s)) for (const [x, y] of cs[key].edges) jset.add(x + '|' + y);
for (const x of cs.cross[s]) jset.add(x[0] + '|' + x[2]);
const eset = new Set(arr(P.seasonPairs));
const onlyE = [...eset].filter(k => !jset.has(k)), onlyJ = [...jset].filter(k => !eset.has(k));
say(onlyE.length === 0 && onlyJ.length === 0, `season ${s} pairs: engine ${eset.size}, explorer ${jset.size}` + (onlyE.length + onlyJ.length ? `; engine only ${onlyE.slice(0, 5).join(' ')}; explorer only ${onlyJ.slice(0, 5).join(' ')}` : ', the same'));
const rel = arr(P.relations).map(r => r[0]);
// the written-pair record is the year's: a pair written in an earlier season is judged by that season's set; an outsider
// pair by New Rules on its own layers
const earlier = new Set(); for (let s0 = 0; s0 < s; s0++) for (const k of pairSet(s0)) earlier.add(k);
// a non-wild target (engine ecoIsTarget): a caravan's or visitor's animal is always a target (VISITOR:); the fort's own
// (DOMESTIC:) only under ecology.livestock or domestic. Probes before 21 Oct name the fort's as bare DOMESTIC.
const fortPrey = P.livestock === true || P.domestic === true;
const notWild = b => b.startsWith('VISITOR:') || ((b === 'DOMESTIC' || b.startsWith('DOMESTIC:')) && (fortPrey || P.livestock === undefined));
const outside = rel.filter(k => { if (eset.has(k) || earlier.has(k)) return false; const [a, b] = k.split('|'); if (notWild(b)) return false; return !(P.live && outsider(a, b, false)); });
const visitorN = rel.filter(k => k.split('|')[1].startsWith('VISITOR:')).length, fortN = rel.filter(k => k.split('|')[1].startsWith('DOMESTIC')).length;
say(outside.length === 0, `relations written: ${rel.length} species pairs this year (${rel.slice(0, VERBOSE ? 999 : 8).join(', ') || 'none yet'}${rel.length > 8 && !VERBOSE ? ', ...' : ''}); ${outside.length ? outside.length + ' outside New Rules: ' + outside.join(', ') : 'all New Rules pairs of their season (or outsiders New Rules allows)'}; not wild: ${visitorN} visitor/caravan pair(s), ${fortN} fort-animal pair(s) (fort animals prey: ${P.livestock === undefined ? 'not in this probe' : fortPrey ? 'on' : 'off'})`);
// ---------------------------------------------------------------- Phase E (probes from sw v8 Phase E on): holes, live cells, kills, pass times
// probes written before sw's `(not ok) and err or nil` fix carry the string 'nil' for no error
const holesErr = P.holesErr && P.holesErr !== 'nil' ? P.holesErr : null;
if (P.holes || holesErr) {
  // holes: the engine's own score of the casts it built, against the explorer's on the casts it builds
  let hDiff = 0;
  const hs = x => JSON.stringify({ m: x.members, p: x.predators, u: arr(x.unlinked).slice().sort(), f: arr(x.unfed).slice().sort() });
  const tally = [];
  for (let s0 = 0; s0 < 4; s0++) {
    const e = arr(P.holes)[s0] || {}, j = sim.seasonHoles(cs, s0, prm);
    for (const realm of new Set([...Object.keys(e), ...Object.keys(j)])) {
      if (!e[realm] || !j[realm] || hs(e[realm]) !== hs(j[realm])) { hDiff++; console.log(`     holes season ${s0} ${realm}: engine ${e[realm] ? hs(e[realm]) : 'none'} explorer ${j[realm] ? hs(j[realm]) : 'none'}`); }
      else if (arr(j[realm].unlinked).length || arr(j[realm].unfed).length) tally.push(`s${s0} ${realm}: no partner ${arr(j[realm].unlinked).join(' ') || '-'}; unfed ${arr(j[realm].unfed).join(' ') || '-'}`);
    }
  }
  say(!holesErr && hDiff === 0, `holes: the engine's score of its casts ${holesErr ? 'FAILED: ' + holesErr : hDiff ? 'differs from the explorer\'s in ' + hDiff + ' season realm(s)' : 'equals the explorer\'s in every season and realm'}` + (tally.length ? '' : ' (no holes)'));
  for (const x of tally) console.log('     ' + x);
}
if (P.live) {
  // live cells: what DF holds now between the wild units on the map, held to the season's New Rules pairs
  const set = pairSet(s), seat = seatedIn(s);
  let nPairs = 0, nCells = 0, nW = 0, extra = [], missing = [], outW = 0, outMiss = [], unslot = 0, staleD = 0;
  for (const key in P.live) {
    const L = P.live[key], [a, b] = key.split('~');
    nPairs++; nCells += L.n; nW += L.w; unslot += L.ns;
    const both = seat.has(a) && seat.has(b);
    const inAB = set.has(a + '|' + b), inBA = set.has(b + '|' + a);
    const oAB = !both && !inAB && outsider(a, b), oBA = !both && !inBA && outsider(b, a);
    if (L.w > 0) {
      if (!inAB && !inBA && !oAB && !oBA) extra.push(`${a}~${b} (${L.w} cells)`);
      else if (!inAB && !inBA) outW += L.w;
    }
    if (inAB && L.abU > 0) { missing.push(`${a}>${b} ${L.abU}/${L.abS}`); staleD += L.abD || 0; }
    if (inBA && L.baU > 0) { missing.push(`${b}>${a} ${L.baU}/${L.baS}`); staleD += L.baD || 0; }
    if (oAB && L.abU > 0) outMiss.push(`${a}>${b} ${L.abU}/${L.abS}`);
    if (oBA && L.baU > 0) outMiss.push(`${b}>${a} ${L.baU}/${L.baS}`);
  }
  say(extra.length === 0, `live cells, season ${s}: ${nCells} unit pairs over ${nPairs} species pairs on the map, ${nW} written; ${extra.length ? extra.length + ' species pair(s) written outside New Rules: ' + extra.slice(0, 8).join(', ') : 'none written outside New Rules'}` + (outW ? ` (${outW} cells are outsider pairs New Rules allows)` : ''));
  say(missing.length === 0, `live cells: New Rules pairs the ecology write covers ${missing.length ? 'left unwritten: ' + missing.slice(0, 8).join(', ') : 'are all written'}` + (unslot ? ` (${unslot} unit pairs not yet slotted, not judged)` : ''));
  if (missing.length && P.live[Object.keys(P.live)[0]].abD !== undefined) console.log(`     of the unwritten cells, ${staleD} are in the write's memo as written (DF reset them since; the memo keeps them until its refresh), the rest are newer than the last pass`);
  if (outMiss.length) console.log(`     outsider pairs New Rules allows but unwritten (ROSTER.castOutsider may withhold them; not judged): ${outMiss.slice(0, 8).join(', ')}`);
}
if (P.kills) {
  // kills: every death DF recorded this year with a wild killer and a wild victim is a New Rules pair of its season
  const yr = P.cur_year, wildWild = [], other = {};
  for (const k of arr(P.kills)) {
    if (k.y !== yr) continue;
    const kw = k.ks && k.ks.wild && !k.ks.tame, vw = k.vs && k.vs.wild && !k.vs.tame;
    if (k.killer && kw && vw) wildWild.push(k);
    else { const why = !k.killer ? 'no killer (' + (k.cause || '?') + ')' : k.ks && k.ks.cit ? 'a citizen killed' : !vw ? 'victim not wild' : 'killer gone or not wild'; other[why] = (other[why] || 0) + 1; }
  }
  const bad = [], backEx = [];
  let fwd = 0, back = 0;
  for (const k of wildWild) {
    const s0 = Math.min(3, Math.max(0, Math.floor((k.t || 0) / 100800)));
    const seat = seatedIn(s0);
    const ps = pairSet(s0), out2 = !(seat.has(k.killer) && seat.has(k.victim));
    if (ps.has(k.killer + '|' + k.victim) || (out2 && outsider(k.killer, k.victim, false))) fwd++;
    // DF's relation is mutual: on a written pair the prey may fight back and win
    else if (ps.has(k.victim + '|' + k.killer) || (out2 && outsider(k.victim, k.killer, false))) { back++; backEx.push(`${k.killer}>${k.victim}`); }
    else bad.push(`${k.killer}>${k.victim} (season ${s0}, ${k.cause})`);
  }
  say(bad.length === 0, `kills this year: ${wildWild.length} wild-on-wild: ${fwd} eater took eaten on a New Rules pair, ${back} prey killed its eater on one${back ? ' (' + backEx.slice(0, 4).join(', ') + ')' : ''}, ${bad.length} outside New Rules${bad.length ? ': ' + bad.slice(0, 8).join(', ') : ''}${wildWild.length ? '' : ' (none yet: pending, not passed)'}` + (Object.keys(other).length ? `; other deaths: ${Object.entries(other).map(([w, n]) => n + ' ' + w).join(', ')}` : ''));
  for (const k of wildWild.slice(0, VERBOSE ? 99 : 6)) console.log(`     ${k.killer} killed ${k.victim} (tick ${k.t}, ${k.cause})`);
}
if (P.perf) {
  // pass times: the FUSE laps of the tool's passes this session (job budget 250 ms; lap budget 50 ms)
  const rows = Object.entries(P.perf).filter(([, v]) => v.runs > 0).sort();
  const worst = rows.reduce((m, [, v]) => Math.max(m, v.worst), 0);
  say(worst <= 250, `pass times: ${rows.length} laps timed, worst ${worst} ms` + (worst > 250 ? ' -- over the 250 ms job budget' : ' (under 250 ms)'));
  for (const [n, v] of rows) if (n.startsWith('ecology') || v.worst > 50) console.log(`     ${n}: ${v.runs} runs, mean ${v.mean.toFixed(1)} ms, worst ${v.worst} ms, over 50 ms ${v.over}`);
}
console.log(fails === 0 ? 'nr probe: the engine follows New Rules on this fort' : `nr probe: ${fails} check(s) failed`);
process.exit(fails ? 1 : 0);
