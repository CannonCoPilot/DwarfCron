/* foodweb_sim.js -- the seasonal-wildlife cast pipeline (engine v7.6.1, ROSTER.FP; desk mirror castsim/design.py) in the
   browser and in node. Data: foodweb_export.py's creatures.json ({meta, creatures}). Where the engine has moved past the
   desk, this follows the engine: CAVE.ASSIGN (the user's cavern picks), the cavern food-web guarantee, the brook roster,
   ROSTER.FP.codeFor slot codes for the vermin diet, hvSet's giant pet value and tie-break, FLY_NOT_RAPTOR.
   Not modelled (they need a live fort): DF's own stocking (a DF water entry counts as freshwater whatever its raws say;
   the stocked entry preferred among duplicates), the water-zone inference from stocked species, exhaustion stand-ins,
   the tool's thief and apex placement, and everything after the cast (FREQUENCY ladder, caps, pauses). */
(function (root) {
  'use strict';
  const LAYERS = ['ground', 'flying', 'ocean', 'fresh', 'cavern1', 'cavern2', 'cavern3'];
  const SUBTER = ['SUBTERRANEAN_WATER', 'SUBTERRANEAN_CHASM'];
  const SLOT_ORDER = ['apex', 'meso', 'grazer', 'ground prey', 'flier', 'fish', 'pelagic', 'shore', 'waterbird', 'swimmer', 'sentient'];

  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function Rng(seed) {
    const f = mulberry32(seed);
    return { random: f, int: (lo, hi) => lo + Math.floor(f() * (hi - lo + 1)), below: n => Math.floor(f() * n) };
  }

  function make(DATA) {
    const M = DATA.meta;
    const BY = {};
    for (const c of DATA.creatures) BY[c.t] = c;
    const setOf = o => { const r = {}; for (const k in o) r[k] = new Set(o[k]); return r; };
    const EXTRA = setOf(M.extra_biomes), EVIL_EXTRA = setOf(M.evil_extra_biomes), LIMIT = setOf(M.biome_limit);
    const EVIL_APEX_B = setOf(M.evil_apex_biomes);
    const GIANT_BUGS = new Set(M.giant_bugs), SALT_WET = new Set(M.salt_wet), NOT_RAPTOR = new Set(M.fly_not_raptor);
    const VDIET = {};
    for (const k in M.vdiet) VDIET[k] = M.vdiet[k];
    const P0 = Object.assign({}, M.params);

    // ------------------------------------------------------------ the fort
    // spec: { land: [biome], rtype: {sav, evil, iso}, extinct, water: {ocean, lake, river, pool: zone|null, brook: bool},
    //         caverns: [1,2,3], assign: bool, guarantee: bool }
    function fortBiomes(spec) {
      const out = {}, rt = spec.rtype;
      for (const b of spec.land) out[b] = { sav: rt.sav, evil: rt.evil, iso: !!rt.iso, kind: 'land' };
      const W = spec.water || {};
      // a zone may be one name or a list (the explorer's 'every zone', for browsing)
      for (const z of [].concat(W.ocean || [])) out['OCEAN_' + z] = { sav: rt.sav, evil: rt.evil, iso: !!rt.iso, kind: 'ocean' };
      for (const k of ['lake', 'river', 'pool']) {
        for (const z of [].concat(W[k] || [])) out[k.toUpperCase() + '_' + z + '_FRESHWATER'] = { sav: rt.sav, evil: rt.evil, iso: !!rt.iso, kind: k };
      }
      if ((spec.caverns || []).length) for (const b of SUBTER) out[b] = { sav: 0, evil: 50, kind: 'cavern' };
      return out;
    }
    function freshSub(spec) {
      const W = spec.water || {};
      return W.lake ? 'lake' : (W.river ? 'river' : (W.pool ? 'pool' : null));
    }
    function regionType(fb) {
      return [fb.sav >= M.savage_at ? 'savage' : 'wild', fb.evil >= M.evil_at ? 'evil' : (fb.evil <= M.good_at ? 'good' : 'neutral')];
    }
    function wiresFor(fbs) {
      const out = [];
      for (const b in fbs) {
        const fb = fbs[b];
        if (fb.kind === 'cavern') continue;
        const [sav, al] = regionType(fb);
        const layers = fb.kind === 'land' ? ['ground', 'flying'] : (fb.kind === 'ocean' ? ['ocean'] : ['fresh']);
        for (const L of layers) {
          for (const [t, kind] of (M.wiring[`${sav}|${al}|${L}|${b}`] || [])) out.push([L, t, kind, b]);
          if (al === 'evil') for (const t in M.evil_apex) {
            if (M.evil_apex[t] === L && (!EVIL_APEX_B[t] || EVIL_APEX_B[t].has(b))) out.push([L, t, 'wire', b]);
          }
        }
      }
      return out;
    }

    // ------------------------------------------------------------ step 1: the gates
    function gate(c, b, fb, spec) {
      if (SUBTER.includes(b)) return null;
      if (GIANT_BUGS.has(c.t) && fb.kind === 'land' && (fb.sav >= M.savage_at || fb.evil >= M.evil_at)) return null;
      if (c.ex && !c.ap) {
        const rule = spec.extinct || 'UNTAMED_WILDS';
        if (rule === 'NONE') return 'extinct: absent from this world';
        if (rule === 'UNTAMED_WILDS' && fb.sav < M.savage_at) return 'extinct (UNTAMED_WILDS): biome not savage';
        if (rule === 'ISOLATED' && !fb.iso) return 'extinct (ISOLATED): no small region';
      } else if (c.sav && fb.sav < M.savage_at) return 'savage: biome not savage';
      if (c.gd && fb.evil > M.good_at) return 'good: biome not good';
      if (c.ev && fb.evil < M.evil_at) return 'evil: biome not evil';
      return null;
    }
    function biomesOf(c, fbs) {
      let bs = new Set(c.b);
      if (LIMIT[c.t]) bs = new Set([...bs].filter(b => LIMIT[c.t].has(b)));
      if (EXTRA[c.t]) for (const b of EXTRA[c.t]) bs.add(b);
      if (EVIL_EXTRA[c.t]) for (const b of EVIL_EXTRA[c.t]) if (fbs[b] && fbs[b].evil >= M.evil_at) bs.add(b);
      if (GIANT_BUGS.has(c.t)) for (const b in fbs) if (fbs[b].kind === 'land' && (fbs[b].sav >= M.savage_at || fbs[b].evil >= M.evil_at)) bs.add(b);
      return bs;
    }
    function pool(spec) {
      const fbs = fortBiomes(spec);
      const P = {}, rejected = [];
      for (const c of DATA.creatures) {
        if (!c.nat) continue;
        const hit = [...biomesOf(c, fbs)].filter(b => fbs[b]).sort();
        if (!hit.length) continue;
        const ok = [], why = [];
        for (const b of hit) { const r = gate(c, b, fbs[b], spec); (r ? why : ok).push(r || b); }
        if (!ok.length) { rejected.push({ t: c.t, why: why.sort()[0] }); continue; }
        const raw = new Set(c.b);
        P[c.t] = { c, matched: ok, extra: ok.filter(b => !raw.has(b)) };
      }
      const promoted = new Set();
      for (const [L, t, kind, b] of wiresFor(fbs)) {
        promoted.add(L + '|' + t);
        if (kind !== 'wire') continue;
        if (P[t]) { if (!P[t].matched.includes(b)) { P[t].matched.push(b); P[t].matched.sort(); P[t].wired = true; } continue; }
        if (BY[t]) P[t] = { c: BY[t], matched: [b], extra: [b], wired: true };
      }
      return { P, fbs, promoted, rejected };
    }

    // ------------------------------------------------------------ step 2: the layers
    function layersOf(p, spec, fbs) {
      const c = p.c, m = new Set(p.matched), out = [];
      const land = p.matched.filter(b => fbs[b].kind === 'land');
      const hab = c.h, verm = c.v, vc = c.vc;
      if (c.pl) return out;
      if (land.length) {
        if (verm) { if (vc === 'VB' || vc === 'VI') out.push('flying'); else if (vc !== 'VF') out.push('ground'); }
        else if (hab === 'land') out.push('ground');
        else if (hab === 'flier' || hab === 'waterbird') { out.push('flying'); if (GIANT_BUGS.has(c.t)) out.push('ground'); }
      }
      const wet = hab === 'aquatic' || hab === 'semiaquatic';
      const waterHere = p.matched.filter(b => fbs[b].kind !== 'land' && fbs[b].kind !== 'cavern');
      const named = new Set(c.wn.filter(b => m.has(b)));
      for (const b of p.extra) if (waterHere.includes(b)) named.add(b);
      const seas = p.matched.filter(b => fbs[b].kind === 'ocean');
      const anySea = Object.keys(fbs).some(b => fbs[b].kind === 'ocean');
      if (anySea) {
        if ((seas.length && (wet || seas.some(b => named.has(b)))) || (!verm && (hab === 'semiaquatic' || hab === 'waterbird') && land.some(b => SALT_WET.has(b)))) out.push('ocean');
      }
      const sub = freshSub(spec);
      if (sub) {
        const hit = p.matched.filter(b => ['lake', 'river', 'pool'].includes(fbs[b].kind));
        const via = (hit.length && (wet || hit.some(b => named.has(b)))) || (!verm && hab === 'semiaquatic' && land.length && !land.every(b => SALT_WET.has(b)));
        if (via) {
          const brook = sub === 'river' && spec.water.brook;
          if (sub === 'pool' && !verm && c.m > M.pool_cap) { /* too large for the murky-pool roster */ }
          else if (sub === 'pool' && !verm && !wet) { /* not aquatic or amphibious */ }
          else if (sub === 'pool' && !verm && !c.fr) { /* no lake, river or pool in its raws */ }
          else if (brook && !verm && c.m > M.brook_max_mass) { /* too large for the brook */ }
          else if (brook && !verm && !wet) { /* not aquatic or amphibious (brook roster) */ }
          else out.push('fresh');
        }
      }
      if (p.matched.some(b => SUBTER.includes(b))) {
        const a = spec.assign !== false ? M.cave_assign[c.t] : null;
        for (const k of spec.caverns || []) {
          if (a) { if (a.includes(k)) out.push('cavern' + k); }
          else if (!c.d || c.d[0] <= k && k <= c.d[1]) out.push('cavern' + k);
        }
      }
      return out;
    }

    // ------------------------------------------------------------ slots
    function predator(c) { return ['ML', 'MW', 'RP', 'AL', 'AW'].includes(c.g) || c.ro === 'predator'; }
    function flagged(c, L) {
      if (c.civ || c.v) return false;
      if (L === 'flying') {
        if (c.ap && c.lp && (c.h === 'flier' || c.h === 'waterbird')) return true;
        if (NOT_RAPTOR.has(c.t)) return false;
        return c.fa;
      }
      if (L === 'ocean' || L === 'fresh') {
        for (const t of [c.t, c.rt, c.gi ? c.t.slice(6) : null]) {
          const k = t && M.aquatic_apex[t];
          if (k === 'apex' || k === 'pelagic') return true;
        }
        return false;
      }
      return c.g === 'AL' || c.g === 'AW' || c.bo;
    }
    function apexTier(c, L, promoted) {
      if (c.civ || c.v) return null;
      if (promoted.has(L + '|' + c.t)) return 'apex';
      if (GIANT_BUGS.has(c.t) && (L === 'ground' || L === 'flying')) return 'apex';
      if (flagged(c, L)) return 'apex';
      for (const t of [c.t, c.rt]) { const r = t && M.real_apex[t]; if (r && r[0] === L) return r[1]; }
      if (c.gi) { const r = M.real_apex[c.t.slice(6)]; if (r && r[0] === L) return 'apex'; }
      return null;
    }
    function slotKey(L, sub) { return L === 'fresh' ? 'fresh:' + sub : (L.startsWith('cavern') ? 'cavern' : L); }
    function slotsFor(c, L, sub, promoted) {
      const hab = c.h, pred = predator(c), g = c.g, s = [];
      const tier = apexTier(c, L, promoted);
      if (L.startsWith('cavern')) {
        if (c.se) return ['sentient'];
        if (tier) s.push('apex');
        if (pred) s.push('meso');
        if (hab === 'land' && !pred) s.push('ground prey');
        if (hab === 'flier' || hab === 'waterbird') s.push('flier');
        if (hab === 'aquatic' || hab === 'semiaquatic') s.push('swimmer');
        return s;
      }
      if (L === 'ground') { if (tier) s.push('apex'); s.push(pred ? 'meso' : (g === 'GZ' ? 'grazer' : 'ground prey')); return s; }
      if (L === 'flying') return (tier ? ['apex'] : []).concat(['flier']);
      if (hab === 'flier' || hab === 'waterbird') return (L === 'fresh' && sub === 'pool') ? [] : ['waterbird'];
      const wet = hab === 'aquatic' || hab === 'semiaquatic';
      if (L === 'fresh' && sub === 'pool') { if (pred) s.push('meso'); else if (wet) s.push('fish'); return s; }
      if (c.pl) return ['placed plant'];
      if (tier && !(L === 'fresh' && sub === 'river')) s.push('apex');
      if (pred && (wet || hab === 'land')) s.push('meso');
      if (hab === 'aquatic' && !pred) s.push(g === 'PE' && L === 'ocean' ? 'pelagic' : 'fish');
      if (hab === 'semiaquatic' || hab === 'land') s.push('shore');
      const tbl = M.slots[slotKey(L, sub)];
      return s.filter(x => x in tbl);
    }

    // ------------------------------------------------------------ the food web test (ROSTER.FP.eats)
    function codeFor(slot, c, L) {
      switch (slot) {
        case 'apex': return 'APX';
        case 'meso': return c.h === 'aquatic' ? 'MW' : 'ML';
        case 'sentient': return 'SN';
        case 'grazer': return 'GZ';
        case 'ground prey': return 'PL';
        case 'pelagic': return 'PE';
        case 'shore': return 'SH';
        case 'waterbird': return predator(c) ? 'RP' : 'WB';
        case 'flier': return predator(c) ? 'RP' : 'LB';
        case 'fish': return L === 'ocean' ? 'FC' : 'FF';
        case 'swimmer': return predator(c) ? 'MW' : 'FF';
      }
      return 'PL';
    }
    function vdiet(c, code, L) {
      let base = VDIET[code];
      if (code === 'APX' && c.h !== 'aquatic' && c.h !== 'semiaquatic') base = null;
      if (code === 'SN' || code === 'SNP') base = VDIET[c.g];
      const d = new Set(base || []);
      if (L.startsWith('cavern') && code === 'LB') { d.add('VB'); d.add('VI'); d.add('VG'); }
      if (c.apv) { d.add('VG'); d.add('VI'); d.add('VF'); }
      if (c.gob) { d.add('VG'); d.add('VC'); }
      return d;
    }
    function tierOf(x) {
      if (x.vermin) return 0;
      const t = M.tier[x.slot];
      if (t !== undefined) return t;
      return predator(x.c) ? 2 : 1;
    }
    // VANILLA (user 17 Oct): the raws' own 'this eats that' -- GOBBLE_VERMIN_CLASS (a vermin of that CREATURE_CLASS),
    // GOBBLE_VERMIN_CREATURE (that vermin), DIVE_HUNTS_VERMIN / HUNTS_VERMIN (any vermin). Nothing else in the raws names prey.
    function vanillaEats(ca, cb) {
      if (!cb.v) return null;
      if (ca.gvt.includes(cb.t)) return 'GOBBLE_VERMIN_CREATURE';
      for (const k of ca.gvc) if (cb.cc.includes(k)) return 'GOBBLE_VERMIN_CLASS:' + k;
      if (ca.dhv) return 'hunts vermin';
      return null;
    }
    let LINKS = 'engine';   // set per cast from prm.links: 'engine' (the v7.6.1 tier ladder) or 'vanilla'
    // a and b: {c, slot, vermin, vclass}; on layer L
    function eats(a, b, L) {
      if (LINKS === 'vanilla') return !!vanillaEats(a.c, b.c);
      return engineEats(a, b, L);
    }
    function engineEats(a, b, L) {
      if (a.vermin) return false;
      const ea = a.c, eb = b.c;
      const shore = a.slot === 'shore' || a.slot === 'waterbird' || ((a.slot === 'flier' || a.slot === 'swimmer') && (ea.h === 'semiaquatic' || ea.h === 'waterbird'));
      if (b.vermin) {
        const d = vdiet(ea, codeFor(a.slot, ea, L), L);
        if (shore && predator(ea)) d.add('VF');
        return d.has(b.vclass);
      }
      if (tierOf(a) <= tierOf(b)) return false;
      if (shore && eb.h === 'aquatic') return (eb.m || 0) <= Math.max(ea.m || 0, M.pool_cap);
      const reach = M.reach[ea.h || 'land'] || M.reach.land;
      return reach[eb.h || 'land'] === true;
    }
    function weirdWeight(k, s) {
      if (k === 1) return (1 - s) ** 2 + 0.05;
      if (k === 2) return Math.max(0.05, 1 - Math.abs(s - 0.5) * 1.8);
      return s ** 2 + 0.05;
    }

    // ------------------------------------------------------------ the lists: 7 layers x 4 seasons
    function build(spec) {
      const { P, fbs, promoted, rejected } = pool(spec);
      const sub = freshSub(spec);
      const layerSets = {};
      for (const L of LAYERS) layerSets[L] = [];
      for (const t of Object.keys(P).sort()) {
        const p = P[t];
        p.layers = layersOf(p, spec, fbs);
        for (const L of p.layers) layerSets[L].push(t);
      }
      const W = spec.water || {};
      const active = LAYERS.filter(L => layerSets[L].length && (L !== 'ocean' || W.ocean) && (L !== 'fresh' || sub) &&
        (!L.startsWith('cavern') || (spec.caverns || []).includes(+L.slice(-1))));
      const lists = {};
      for (let s = 0; s < 4; s++) for (const L of active) {
        const lst = [];
        for (const t of layerSets[L]) {
          const c = P[t].c;
          if (c.ns[s]) continue;
          if (c.v) {
            lst.push({ c, vermin: true, vclass: c.vc, slots: ['vermin'] });
            if (L === 'fresh' && sub === 'pool' && (c.vc === 'VF' || c.h === 'semiaquatic')) lst.push({ c, vermin: false, slots: ['fish'], vfish: true, tier: null });
          } else {
            const sl = slotsFor(c, L, sub, promoted);
            if (sl.length) lst.push({ c, vermin: false, slots: sl, tier: sl.includes('apex') ? apexTier(c, L, promoted) : null });
          }
        }
        lists[L + '|' + s] = lst;
      }
      return { P, fbs, promoted, rejected, sub, layerSets, active, lists };
    }

    // ------------------------------------------------------------ one season cast (ROSTER.FP.grow)
    function cast(lst, L, sub, used, rng, prm, spec) {
      LINKS = prm.links || 'engine';
      const tbl = M.slots[slotKey(L, sub)];
      const order = Object.keys(tbl).filter(s => s !== '_vermin');
      const want = {}, have = {};
      for (const s of order) { const [lo, hi] = tbl[s]; want[s] = rng.int(lo, hi); have[s] = 0; }
      const wantFixed = Object.assign({}, want);
      const vwant = rng.int(tbl._vermin[0], tbl._vermin[1]);
      const cands = lst.filter(x => !x.vermin && !x.slots.includes('placed plant'));
      const verm = lst.filter(x => x.vermin);
      const weirdK = L.startsWith('cavern') ? +L.slice(-1) : null;
      const out = { L, members: [], vermin: [], log: [], seed: null, apexRank: [], hv: {}, guarantee: [], unfilled: {}, pool: cands.length, want: wantFixed };
      const taken = new Set(), members = [];
      function weight(x, pack) {
        const c = x.c;
        let w = 1;
        if (predator(c) && !c.bn && (c.c1 || 1) > 1) w *= (pack === undefined ? prm.pack : pack);
        w *= Math.pow(prm.reuse, used[c.t] || 0);
        if (c.gi) w *= prm.giant;
        if (c.ap && !c.civ) w *= prm.ap_pick;
        if (weirdK && c.wd != null && prm.weird) w *= weirdWeight(weirdK, c.wd);
        return w;
      }
      function pick(arr) {
        let tot = 0;
        for (const x of arr) tot += weight(x);
        if (tot <= 0) return null;
        let r = rng.random() * tot;
        for (const x of arr) { r -= weight(x); if (r <= 0) return x; }
        return arr[arr.length - 1];
      }
      function put(x, slot, how) {
        const m = { c: x.c, slot, vermin: false };
        members.push(m); have[slot] = (have[slot] || 0) + 1; taken.add(x.c.t);
        out.members.push({ t: x.c.t, slot, how });
        return m;
      }
      const room = x => x.slots.filter(s => want[s] !== undefined && have[s] < want[s] && s !== 'apex');
      const frac = s => (want[s] - have[s]) / want[s];
      // apex
      if (want.apex) {
        const elig = cands.filter(x => x.tier && x.slots[0] === 'apex');
        const tierUse = elig.some(x => x.tier === 'apex') ? 'apex' : 'local';
        const el = elig.filter(x => x.tier === tierUse);
        if (el.length) {
          const gsize = x => { const c = x.c; const pk = predator(c) && !c.bn && (c.c1 || 1) > 1; return (c.m || 0) * (pk ? ((c.c0 || 1) + (c.c1 || 1)) / 2 : 1); };
          let mx = 1;
          for (const x of el) mx = Math.max(mx, gsize(x));
          const ws = el.map(x => Math.sqrt(gsize(x) / mx) * weight(x, prm.apex_pack));
          const tot = ws.reduce((a, b) => a + b, 0);
          let r = rng.random() * tot, chosen = null;
          for (let i = 0; i < el.length; i++) { r -= ws[i]; if (r <= 0) { chosen = el[i]; break; } }
          chosen = chosen || el[el.length - 1];
          out.apexRank = el.map((x, i) => ({ t: x.c.t, p: tot > 0 ? ws[i] / tot : 0 })).sort((a, b) => b.p - a.p);
          out.apexTier = tierUse;
          put(chosen, 'apex', 'apex drawn (' + tierUse + ')');
        } else {
          let best = null;
          for (const x of cands) if (x.slots.includes('meso') && !x.c.se && (!best || (x.c.m || 0) > (best.c.m || 0))) best = x;
          if (best) { put(best, 'apex', 'largest predator promoted'); out.apexTier = 'promoted'; }
        }
      }
      // the seed
      let free = cands.filter(x => !taken.has(x.c.t) && room(x).length);
      const hv = hvSet(free, prm);
      out.hv = hv;
      const direct = L === 'flying';
      if (!direct && prm.seed) {
        const seeds = free.filter(x => hv[x.c.t] && !x.c.se && !x.c.ap);
        const s = pick(seeds);
        if (s) {
          let best = null;
          for (const x of room(s)) if (best === null || frac(x) > frac(best)) best = x;
          out.seed = s.c.t; out.seedWhy = hv[s.c.t];
          put(s, best, 'seed (' + hv[s.c.t] + ')');
        }
      }
      // growth
      let guard = 0;
      while (guard++ < 200) {
        const open = order.filter(s => have[s] < want[s]);
        if (!open.length) break;
        free = cands.filter(x => !taken.has(x.c.t) && room(x).length);
        if (!free.length) break;
        const linked = [];
        if (!direct && members.length) {
          const ord = members.slice();
          for (let i = ord.length - 1; i >= 1; i--) { const j = rng.below(i + 1); [ord[i], ord[j]] = [ord[j], ord[i]]; }
          for (const x of free) {
            const cc = { c: x.c, slot: room(x)[0], vermin: false };
            for (const m of ord) if (eats(cc, m, L) || eats(m, cc, L)) { linked.push([x, m]); break; }
          }
        }
        out.linkStats = out.linkStats || [];
        if (!direct && members.length) out.linkStats.push([linked.length, free.length]);
        if (linked.length) {
          let best = -1;
          for (const [x] of linked) for (const s of room(x)) best = Math.max(best, frac(s));
          const top = [], fromOf = new Map();
          for (const [x, m] of linked) if (room(x).some(s => frac(s) === best)) { top.push(x); fromOf.set(x, m); }
          const x = pick(top);
          if (!x) break;
          const slot = room(x).find(s => frac(s) === best);
          put(x, slot, 'linked to ' + fromOf.get(x).c.t);
        } else {
          let s = null, bf = -1;
          for (const x of open) { const f = frac(x); if (f > bf) { s = x; bf = f; } }
          const el = free.filter(x => room(x).includes(s));
          if (!el.length) { want[s] = have[s]; continue; }
          const x = pick(el);
          if (!x) break;
          put(x, s, direct ? 'drawn (slot fill)' : 'no link: filled anyway');
        }
      }
      for (const s of order) if (have[s] < wantFixed[s]) {
        const n = cands.filter(x => x.slots.includes(s)).length;
        out.unfilled[s] = `${have[s]} of ${wantFixed[s]}: ` + (n ? 'all candidates used in other slots' : 'none in season');
      }
      // the cavern food-web guarantee (v7.6)
      if (L.startsWith('cavern') && prm.guarantee) {
        const isPrey = m => m.slot === 'ground prey' || ((m.slot === 'flier' || m.slot === 'swimmer') && !predator(m.c));
        const isPred = m => m.slot === 'apex' || m.slot === 'meso' || ((m.slot === 'flier' || m.slot === 'swimmer') && predator(m.c));
        if (!members.some(isPrey)) {
          const el = [];
          for (const x of cands) if (!taken.has(x.c.t) && !predator(x.c)) {
            const s = x.slots.find(s => s === 'ground prey' || s === 'flier' || s === 'swimmer');
            if (s) el.push([x, s]);
          }
          if (el.length) { const [x, s] = el[rng.below(el.length)]; put(x, s, 'web guarantee: prey'); out.guarantee.push(x.c.t); }
        }
        if (!members.some(isPred)) {
          let best = null;
          for (const x of cands) if (!taken.has(x.c.t) && predator(x.c) && !x.c.se && (!best || (x.c.m || 0) > (best.c.m || 0))) best = x;
          if (best) { const s = best.slots.find(s => s === 'apex' || s === 'meso') || 'meso'; put(best, s, 'web guarantee: predator'); out.guarantee.push(best.c.t); }
        }
      }
      // vermin
      const vl = verm.filter(v => !taken.has(v.c.t));
      const eaten = new Map();
      for (const v of vl) eaten.set(v, members.filter(m => eats(m, v, L)).length);
      for (let i = vl.length - 1; i >= 1; i--) { const j = rng.below(i + 1); [vl[i], vl[j]] = [vl[j], vl[i]]; }
      vl.sort((a, b) => eaten.get(b) - eaten.get(a));
      const vsel = [], seen = new Set();
      for (const v of vl) { if (vsel.length >= vwant) break; if (eaten.get(v) > 0 && !seen.has(v.vclass)) { seen.add(v.vclass); vsel.push(v); } }
      for (const v of vl) { if (vsel.length >= vwant) break; if (!vsel.includes(v)) vsel.push(v); }
      out.vermin = vsel.map(v => ({ t: v.c.t, vc: v.vclass, eaten: eaten.get(v) }));
      // the web, after the draw
      const all = members.concat(vsel.map(v => ({ c: v.c, slot: 'vermin', vermin: true, vclass: v.vclass })));
      out.edges = [];
      for (const a of all) for (const b of all) if (a !== b && eats(a, b, L)) out.edges.push([a.c.t, b.c.t]);
      const linkedSet = new Set(out.edges.flat());
      out.isolated = members.filter(m => !linkedSet.has(m.c.t)).map(m => m.c.t);
      for (const m of members) used[m.c.t] = (used[m.c.t] || 0) + 1;
      return out;
    }
    function hvSet(free, prm) {
      const k = Math.ceil(free.length * prm.hv_top);
      const why = {};
      const note = (t, w) => { why[t] = why[t] ? why[t] + ', ' + w : w; };
      for (const x of free) if (x.c.war) note(x.c.t, 'war');
      const top = (val, tie, label) => {
        const list = free.filter(x => val(x) > 0);
        list.sort((a, b) => val(b) - val(a) || tie(b) - tie(a) || (a.c.t < b.c.t ? -1 : 1));
        for (const x of list.slice(0, k)) note(x.c.t, label(x));
      };
      if (prm.deskHv) {   // the desk's rule (design.high_value): the creature's own pet value, ties by token
        const k2 = Math.ceil(free.length * prm.hv_top);
        for (const [fld, lab] of [['pet0', 'pet'], ['m', 'size']]) {
          const list = free.filter(x => x.c[fld] > 0).sort((a, b) => b.c[fld] - a.c[fld] || (a.c.t < b.c.t ? -1 : 1));
          for (const x of list.slice(0, k2)) note(x.c.t, lab + ' ' + x.c[fld]);
        }
        return why;
      }
      top(x => x.c.pet, x => x.c.m, x => 'pet ' + x.c.pet);
      top(x => x.c.m, x => x.c.pet, x => 'size ' + Math.round(x.c.m).toLocaleString('en'));
      return why;
    }

    // ------------------------------------------------------------ a year: all 28 casts at once, in a random order
    function year(B, spec, prm, site, yr) {
      const order = [];
      for (let s = 0; s < 4; s++) for (const L of B.active) order.push([L, s]);
      const sh = Rng((site * 7919 + yr * 104729 + 7) % 2147483647);
      for (let i = order.length - 1; i >= 1; i--) { const j = sh.below(i + 1); [order[i], order[j]] = [order[j], order[i]]; }
      const casts = {}, used = {};
      order.forEach(([L, s], n) => {
        const seed = (site * 7919 + yr * 104729 + s * 131 + LAYERS.indexOf(L) * 17) % 2147483647;
        const tr = cast(B.lists[L + '|' + s], L, B.sub, used, Rng(seed), prm, spec);
        tr.built = n + 1;
        casts[L + '|' + s] = tr;
      });
      return casts;
    }
    // N years: per layer, how often each species is cast, seeded, apex
    function years(B, spec, prm, n, site) {
      const st = {};
      for (const L of B.active) st[L] = { casts: 0, inc: {}, seasons: {}, seed: {}, apex: {}, slot: {}, guarantee: 0, unfilled: 0, hvSeen: {} };
      for (let i = 0; i < n; i++) {
        const cs = year(B, spec, prm, site || 1, 250 + i);
        for (const key in cs) {
          const tr = cs[key], L = tr.L, S = st[L];
          S.casts++;
          const once = new Set();
          for (const m of tr.members) {
            S.seasons[m.t] = (S.seasons[m.t] || 0) + 1;
            once.add(m.t);
            S.slot[m.t + '|' + m.slot] = (S.slot[m.t + '|' + m.slot] || 0) + 1;
            if (m.slot === 'apex') S.apex[m.t] = (S.apex[m.t] || 0) + 1;
          }
          for (const v of tr.vermin) S.seasons[v.t] = (S.seasons[v.t] || 0) + 1;
          if (tr.seed) S.seed[tr.seed] = (S.seed[tr.seed] || 0) + 1;
          for (const t in tr.hv) S.hvSeen[t] = (S.hvSeen[t] || 0) + 1;
          S.guarantee += tr.guarantee.length;
          if (Object.keys(tr.unfilled).length) S.unfilled++;
        }
      }
      return st;
    }
    // the potential web of a layer: every pair that eats under some slot either can hold, among one list (or the union of
    // the four seasons' lists)
    // the view's vanilla edges: [a, b, why] among the items (any layer)
    function vanillaEdges(items) {
      const out = [];
      for (const a of items) {
        if (a.vermin || !(a.c.gvc.length || a.c.gvt.length || a.c.dhv)) continue;
        for (const b of items) { const why = a !== b && vanillaEats(a.c, b.c); if (why) out.push([a.c.t, b.c.t, why]); }
      }
      return out;
    }
    function potentialEdges(items, L) {
      const keep = LINKS; LINKS = 'engine';
      const edges = [];
      for (const a of items) {
        if (a.vermin) continue;
        for (const b of items) {
          if (a === b || a.c.t === b.c.t) continue;
          let hit = false;
          for (const sa of a.slots) {
            const A = { c: a.c, slot: sa, vermin: false };
            for (const sb of (b.vermin ? ['vermin'] : b.slots)) {
              if (eats(A, { c: b.c, slot: sb, vermin: b.vermin, vclass: b.vclass }, L)) { hit = true; break; }
            }
            if (hit) break;
          }
          if (hit) edges.push([a.c.t, b.c.t]);
        }
      }
      LINKS = keep;
      return edges;
    }
    return { M, BY, P0, LAYERS, SLOT_ORDER, tierOf, build, year, years, cast, potentialEdges, vanillaEdges, vanillaEats, slotsFor, apexTier, predator, eats, layersOf, pool, Rng, hvSet, codeFor };
  }

  const api = { make, LAYERS };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.FWSim = api;
})(typeof self !== 'undefined' ? self : this);
