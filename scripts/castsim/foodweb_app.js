/* foodweb_app.js -- the Food Web Explorer's page logic: fort filters, the network (canvas + d3-force), the cast simulator
   panels. Needs window.FWSim (foodweb_sim.js), window.FWDATA (creatures.json) and d3 v7. */
(function () {
  'use strict';
  const sim = FWSim.make(FWDATA);
  const M = sim.M, BY = sim.BY, LAYERS = sim.LAYERS;
  const $ = s => document.querySelector(s);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const SEASONS = ['Spring', 'Summer', 'Autumn', 'Winter'];
  // VIEWER TABS (user 17 Oct): the surface layers as columns; the caverns in their own tab, sorted left to right by the set
  // of caverns a creature can be cast in (staggered by mean depth), since most cavern creatures live in more than one
  const SURF = ['ground', 'flying', 'ocean', 'fresh'], CAVS = ['cavern1', 'cavern2', 'cavern3'];
  const CAVGROUPS = ['1', '1,2', '2', '1,2,3', '1,3', '2,3', '3'];
  const CAVGROUP_LABEL = { '1': 'Cav 1', '1,2': '1 + 2', '2': 'Cav 2', '1,2,3': 'all three', '1,3': '1 + 3', '2,3': '2 + 3', '3': 'Cav 3' };
  const CAV_COL = { 1: 'c-green', 2: 'c-blue', 3: 'c-purple' };
  const SHORT = { ground: 'Ground', flying: 'Flying', ocean: 'Ocean', fresh: 'Fresh', cavern1: 'Cav 1', cavern2: 'Cav 2', cavern3: 'Cav 3' };
  const LNAME = { ground: 'Land-ground', flying: 'Land-flying', ocean: 'Ocean', fresh: 'Freshwater', cavern1: 'Cavern 1', cavern2: 'Cavern 2', cavern3: 'Cavern 3' };
  const BIOME_GROUPS = [
    ['Forest', ['FOREST_TAIGA', 'FOREST_TEMPERATE_CONIFER', 'FOREST_TEMPERATE_BROADLEAF', 'FOREST_TROPICAL_CONIFER', 'FOREST_TROPICAL_DRY_BROADLEAF', 'FOREST_TROPICAL_MOIST_BROADLEAF']],
    ['Grass, savanna, shrub', ['GRASSLAND_TEMPERATE', 'SAVANNA_TEMPERATE', 'SHRUBLAND_TEMPERATE', 'GRASSLAND_TROPICAL', 'SAVANNA_TROPICAL', 'SHRUBLAND_TROPICAL']],
    ['Marsh and swamp', ['MARSH_TEMPERATE_FRESHWATER', 'MARSH_TEMPERATE_SALTWATER', 'MARSH_TROPICAL_FRESHWATER', 'MARSH_TROPICAL_SALTWATER', 'SWAMP_TEMPERATE_FRESHWATER', 'SWAMP_TEMPERATE_SALTWATER', 'SWAMP_TROPICAL_FRESHWATER', 'SWAMP_TROPICAL_SALTWATER', 'SWAMP_MANGROVE']],
    ['Desert', ['DESERT_BADLAND', 'DESERT_ROCK', 'DESERT_SAND']],
    ['Cold and high', ['MOUNTAIN', 'GLACIER', 'TUNDRA']],
  ];
  const bname = b => b.toLowerCase().replace(/_/g, ' ').replace('freshwater', 'fresh').replace('saltwater', 'salt').replace('temperate', 'temp.').replace('tropical', 'trop.');
  // slot -> colour token (validated: five hues, both themes; shape carries the trophic level as the second encoding)
  const SLOT_COL = { apex: 'c-red', meso: 'c-purple', sentient: 'ink', grazer: 'c-green', 'ground prey': 'c-amber', flier: 'c-blue',
    waterbird: 'c-blue', fish: 'c-green', pelagic: 'c-green', shore: 'c-amber', swimmer: 'c-green', vermin: 'muted' };
  const SLOT_LEGEND = [['apex', 'apex'], ['meso', 'meso predator'], ['sentient', 'sentient'], ['grazer', 'grazer · fish · pelagic · swimmer'],
    ['ground prey', 'ground prey · shore'], ['flier', 'flier · waterbird'], ['vermin', 'vermin']];
  const HAB_COL = { land: 'c-amber', flier: 'c-blue', waterbird: 'c-purple', aquatic: 'c-green', semiaquatic: 'c-red' };
  const LEVEL_NAME = ['vermin', 'prey', 'predator', 'apex'];
  const FAM = {
    newrules: { lab: 'New Rules', col: 'c-green', def: sim.NEW_RULES.map(r => r.label).join(' + '), note: 'the rule set we are building: ' + sim.NEW_RULES.map(r => r.label).join(' + ') },
    hunt: { lab: 'Hunting pairs written in play', col: 'ink', def: 'on', note: 'ecology relation write: armed predator x target, on the season cast\'s own edges' },
    gobble: { lab: 'Vermin the tool feeds', col: 'c-blue', def: 'on', note: 'GOBBLE_VERMIN_CLASS written onto consumers (guild rules) over the tool\'s SWV vermin classes' },
    raws: { lab: "DF's own diet tokens", col: 'c-amber', def: 'always', note: 'GOBBLE_VERMIN_CLASS/_CREATURE, DIVE_HUNTS_VERMIN, HUNTS_VERMIN in the vanilla raws' },
    flags: { lab: 'Hunting flags', col: 'c-purple', def: 'off', note: 'DIVE_HUNTS_VERMIN / HUNTS_VERMIN written by the tool (hunting off by default)' },
    ladder: { lab: 'Cast-growth ladder', col: 'muted', def: 'build only', note: 'ROSTER.FP.eats: tiers + habitat; the hunting pairs are filtered through it' },
    mass: { lab: 'Mass and numbers', col: 'c-red', def: 'off', note: 'MODEL eats (pack mass v prey mass), vermin only from the sides the user\'s rules allow; used only by coupling, off by default' },
  };
  const FAM_ORDER = ['newrules', 'hunt', 'raws', 'gobble', 'flags', 'mass', 'ladder'];
  const realmOf = L => L.startsWith('cavern') ? L : 'surface';
  const GUILD_FAM = g => ({ AL: 'predator', AW: 'predator', ML: 'predator', MW: 'predator', RP: 'raptor', GZ: 'grazer', PL: 'small prey',
    LB: 'bird', WB: 'bird', FF: 'fish', FC: 'fish', PE: 'fish', SH: 'shore', V: 'vermin' }[g] || 'other');
  const FAM_SHAPE = { predator: 'tri', raptor: 'star', grazer: 'circle', 'small prey': 'square', bird: 'diamond', fish: 'cross', shore: 'square', vermin: 'dot', other: 'circle' };
  // the Levels layout's sub-columns: a guild type for creatures, a vermin type for vermin (left to right in this order)
  const VERMIN_GROUP = { SWV_GROUND_BUG: 'bug', SWV_SOIL: 'soil', SWV_COLONY: 'colony', SWV_SMALL_MAMMAL: 'mammal', SWV_HERP: 'herp',
    SWV_SMALL_FISH: 'small fish', SWV_SMALL_BIRD: 'small bird', SWV_BAT: 'bat', SWV_FLYING_INSECT: 'insect', SWV_OTHER: 'other vermin' };
  const GROUP_ORDER = ['land hunter', 'raptor', 'grazer', 'small prey', 'land bird', 'waterbird', 'shore', 'water hunter', 'fish', 'pelagic', 'other', 'sentient',
    'mammal', 'herp', 'bug', 'soil', 'colony', 'insect', 'small bird', 'bat', 'small fish', 'other vermin'];
  const GUILD_GROUP = { AL: 'land hunter', ML: 'land hunter', AW: 'water hunter', MW: 'water hunter', RP: 'raptor', GZ: 'grazer',
    PL: 'small prey', LB: 'land bird', WB: 'waterbird', SH: 'shore', FF: 'fish', FC: 'fish', PE: 'pelagic' };
  // a sentient-slot member gets its own sub-column (user 17 Oct: a sentient slot on every layer), at the right of its tier
  const groupOf = n => n.vermin ? (VERMIN_GROUP[n.c.swv] || 'other vermin') : n.slot === 'sentient' ? 'sentient' : (GUILD_GROUP[n.c.g] || 'other');
  const HAB_SHAPE = { land: 'circle', flier: 'tri', waterbird: 'diamond', aquatic: 'cross', semiaquatic: 'square' };
  const LEVEL_SHAPE = ['dot', 'circle', 'diamond', 'tri'];

  // ------------------------------------------------------------------ state
  // user 17 Oct: the page opens on everything -- every land biome, all nine surroundings, every neighbouring tile, every water
  // body in every zone, all three caverns
  const ALL_LAND = BIOME_GROUPS.flatMap(([, bs]) => bs);
  const state = {
    land: new Set(ALL_LAND), cells: new Set(['benign', 'neutral', 'savage'].flatMap(v => ['good', 'neutral', 'evil'].map(a => v + '|' + a))), neighbours: new Set(ALL_LAND), iso: false,
    extinct: 'UNTAMED_WILDS', ocean: true, oz: 'ALL', lake: true, river: true, brook: true, pool: true, fz: 'ALL',
    caverns: new Set([1, 2, 3]), assign: true, season: 'all', layer: 'all', color: 'slot', shape: 'level', layout: 'levels',
    tab: 'surface', seasonBy: 'raws', edges: 'all', fam: { newrules: true, hunt: false, gobble: false, raws: false, flags: false, ladder: false, mass: false }, selEdge: null, vermin: true, years: 200, sel: null, hover: null, castSel: null, statsLayer: null, search: '',
    prm: Object.assign({}, sim.P0, { seed: true, weird: true, guarantee: true, links: 'engine' }),
  };
  // SURROUNDINGS (user 17 Oct): DF's nine, savagery (benign, neutral, savage) x alignment (good, neutral, evil)
  const SAVK = ['benign', 'neutral', 'savage'], ALK = ['good', 'neutral', 'evil'];
  const ALLCELLS = ALK.flatMap(a => SAVK.map(v => v + '|' + a));
  const CELLNAME = { 'benign|good': 'Serene', 'neutral|good': 'Mirthful', 'savage|good': 'Joyous Wilds', 'benign|neutral': 'Calm',
    'neutral|neutral': 'Wilderness', 'savage|neutral': 'Untamed Wilds', 'benign|evil': 'Sinister', 'neutral|evil': 'Haunted', 'savage|evil': 'Terrifying' };
  const PRESETS = {
    coast: { label: 'Savage tropical coast', land: ['SHRUBLAND_TROPICAL', 'SWAMP_MANGROVE', 'FOREST_TROPICAL_MOIST_BROADLEAF'], cells: ['savage|neutral'], extinct: 'UNTAMED_WILDS', iso: false, ocean: true, oz: 'TROPICAL', lake: false, river: true, brook: false, pool: false, fz: 'TROPICAL' },
    lake: { label: 'Calm temperate forest lake', land: ['FOREST_TEMPERATE_BROADLEAF', 'GRASSLAND_TEMPERATE'], cells: ['neutral|neutral'], extinct: 'UNTAMED_WILDS', iso: false, ocean: false, oz: 'TEMPERATE', lake: true, river: false, brook: false, pool: false, fz: 'TEMPERATE' },
    brook: { label: 'Good temperate brook', land: ['FOREST_TEMPERATE_CONIFER', 'SHRUBLAND_TEMPERATE'], cells: ['neutral|good'], extinct: 'UNTAMED_WILDS', iso: false, ocean: false, oz: 'TEMPERATE', lake: false, river: false, brook: true, pool: true, fz: 'TEMPERATE' },
    tundra: { label: 'Evil tundra with murky pools', land: ['TUNDRA', 'FOREST_TAIGA'], cells: ['neutral|evil'], extinct: 'WILDERNESS', iso: false, ocean: false, oz: 'ARCTIC', lake: false, river: false, brook: false, pool: true, fz: 'TEMPERATE' },
    arctic: { label: 'Savage good arctic coast', land: ['GLACIER', 'TUNDRA'], cells: ['savage|good'], extinct: 'WILDERNESS', iso: false, ocean: true, oz: 'ARCTIC', lake: false, river: false, brook: false, pool: false, fz: 'TEMPERATE' },
    all: { label: 'Every creature', land: M.land.slice(), cells: ALLCELLS, extinct: 'WILDERNESS', iso: true, ocean: true, oz: 'ALL', lake: true, river: true, brook: false, pool: true, fz: 'ALL' },
  };
  function applyPreset(k) {
    const p = PRESETS[k];
    Object.assign(state, { land: new Set(p.land), cells: new Set(p.cells), extinct: p.extinct, iso: p.iso, ocean: p.ocean, oz: p.oz, lake: p.lake,
      river: p.river, brook: p.brook, pool: p.pool, fz: p.fz, caverns: new Set([1, 2, 3]), sel: null, castSel: null });
    syncControls(); rebuild(true);
  }

  // ------------------------------------------------------------------ the fort -> builds
  const SAVS = { benign: 10, neutral: 50, savage: 80 }, ALS = { good: 10, neutral: 50, evil: 90 };
  const zones = (z, kind) => z === 'ALL' ? (kind === 'ocean' ? ['ARCTIC', 'TEMPERATE', 'TROPICAL'] : ['TEMPERATE', 'TROPICAL']) : z;
  function specFor(sav, al) {
    const fz = zones(state.fz, 'fresh');
    return {
      land: [...state.land], rtype: { sav, evil: al, iso: state.iso }, extinct: state.extinct,
      water: { ocean: state.ocean ? zones(state.oz, 'ocean') : null, lake: state.lake ? fz : null,
        river: (state.river || state.brook) ? fz : null, pool: state.pool ? fz : null, brook: state.brook && !state.river },
      caverns: [...state.caverns].sort(), assign: state.assign, neighbours: [...state.neighbours],
    };
  }
  function fortKey() {
    return JSON.stringify([...state.land].sort()) + '|nb:' + [...state.neighbours].sort().join(',') + '|' + state.iso + state.extinct + state.ocean + state.oz + state.lake + state.river + state.brook + state.pool + state.fz + [...state.caverns].sort() + state.assign;
  }
  function concrete() { return state.cells.size === 1; }
  let BUILD = null;   // { B (merged or single), spec (single or null), key }
  function buildAll() {
    const bs = [];
    for (const cell of ALLCELLS) if (state.cells.has(cell)) { const [v, a] = cell.split('|'); const sp = specFor(SAVS[v], ALS[a]); bs.push([sp, sim.build(sp)]); }
    if (bs.length === 1) return { B: bs[0][1], spec: bs[0][0] };
    if (!bs.length) {   // every cell off: an empty view
      const L0 = {}; for (const L of LAYERS) L0[L] = [];
      return { B: { P: {}, layerSets: L0, active: [], lists: {}, sub: null, rejected: [] }, spec: null };
    }
    // browse union: a species is in when any region type admits it; its slots from the first that does
    const B = { P: {}, layerSets: {}, active: [], lists: {}, sub: bs[0][1].sub, rejected: [], promoted: new Set(), mapOnly: {}, apexOn: {} };
    for (const L of LAYERS) B.layerSets[L] = [];
    for (const [, b] of bs) {
      // a species' layers can differ by surroundings (the bat man reaches land-flying and the ocean only where savage): union them
      for (const t in b.P) {
        if (!B.P[t]) B.P[t] = b.P[t];
        else if (b.P[t].layers.some(L => !B.P[t].layers.includes(L))) B.P[t] = Object.assign({}, B.P[t], { layers: [...new Set(B.P[t].layers.concat(b.P[t].layers))] });
      }
      for (const t in b.mapOnly || {}) if (!B.mapOnly[t]) B.mapOnly[t] = b.mapOnly[t];
      for (const t in b.apexOn || {}) { const x = B.apexOn[t] || {}, y = b.apexOn[t]; B.apexOn[t] = Object.fromEntries(Object.keys(y).map(k => [k, Array.isArray(y[k]) ? [...new Set((x[k] || []).concat(y[k]))] : !!(x[k] || y[k])])); }
      for (const x of b.promoted || []) B.promoted.add(x);
      for (const L of LAYERS) for (const t of b.layerSets[L]) if (!B.layerSets[L].includes(t)) B.layerSets[L].push(t);
      for (const L of b.active) if (!B.active.includes(L)) B.active.push(L);
      for (const k in b.lists) {
        const cur = B.lists[k] || (B.lists[k] = []);
        const have = new Set(cur.map(x => x.c.t + (x.vermin ? '|v' : '')));
        for (const x of b.lists[k]) if (!have.has(x.c.t + (x.vermin ? '|v' : ''))) cur.push(x);
      }
    }
    B.active.sort((a, b) => LAYERS.indexOf(a) - LAYERS.indexOf(b));
    return { B, spec: null };
  }

  let CELLPOOLS = null;
  function cellPools() {
    const key = fortKey();
    if (CELLPOOLS && CELLPOOLS.key === key) return CELLPOOLS;
    const by = {}, union = {};
    for (const cell of ALLCELLS) {
      const [v, a] = cell.split('|');
      const P = sim.build(specFor(SAVS[v], ALS[a])).P;
      by[cell] = new Set(Object.keys(P).filter(t => !P[t].c.pl && P[t].layers.length));
      for (const t of by[cell]) union[t] = P[t].c;
    }
    CELLPOOLS = { key, by, union };
    return CELLPOOLS;
  }
  function renderSurroundings() {
    const C = cellPools();
    const ok = t => state.vermin || !BY[t].v;
    const n = cell => [...C.by[cell]].filter(ok).length;
    $('#surr').innerHTML = `<table class="surr"><thead><tr><th></th>${SAVK.map(v => `<th scope="col">${v}</th>`).join('')}</tr></thead><tbody>` +
      ALK.map(a => `<tr><th scope="row">${a}</th>${SAVK.map(v => { const cell = v + '|' + a, on = state.cells.has(cell);
        return `<td><button type="button" data-cell="${cell}" aria-pressed="${on}"><b>${CELLNAME[cell]}</b><span>${n(cell)}</span></button></td>`; }).join('')}</tr>`).join('') +
      '</tbody></table>';
    const all = Object.values(C.union).filter(c => state.vermin || !c.v);
    const tag = (k, lab) => { const xs = all.filter(c => c[k]); const v = xs.filter(c => c.v).length; return `${lab} ${xs.length}${v ? ` (${v} vermin)` : ''}`; };
    $('#tagline').textContent = `Creatures that can live here in any surroundings: ${all.length}. Tagged ${tag('sav', 'SAVAGE')}, ${tag('gd', 'GOOD')}, ${tag('ev', 'EVIL')}. ` +
      'Each cell counts the creatures that fit it: a SAVAGE tag needs savage surroundings, GOOD good, EVIL evil; an untagged creature fits all nine. ' +
      'No raw tag asks for benign surroundings, so the benign and neutral columns hold the same creatures. Real-world-extinct species follow the extinct rule in place of their SAVAGE tag.';
  }
  $('#surr').addEventListener('click', ev => {
    const b = ev.target.closest('button[data-cell]'); if (!b) return;
    const cell = b.dataset.cell;
    // each cell toggles on its own (user 17 Oct)
    if (state.cells.has(cell)) state.cells.delete(cell); else state.cells.add(cell);
    state.sel = null; rebuild();
  });
  $('#surrAll').onclick = () => { state.cells = new Set(ALLCELLS); rebuild(); };
  $('#surrNone').onclick = () => { state.cells = new Set(); rebuild(); };

  // ------------------------------------------------------------------ nodes and edges for the view
  let VIEW = null;   // { nodes, byT, edges (array of {a,b,L}), adj }
  const edgeCache = new Map();
  function seasonsIn() { return state.season === 'all' ? [0, 1, 2, 3] : [+state.season]; }
  // the season buttons read DF's raws (NO_SPRING..NO_WINTER: who can be on the map that season) or, once a year is built,
  // that year's casts (who the tool puts in the season's cast); user 19 Oct: the raws alone barely change by season
  function castMembers(L) {
    if (state.seasonBy !== 'casts' || !YEAR) return null;
    const set = new Set();
    for (const s of seasonsIn()) { const tr = YEAR[L + '|' + s]; if (tr) { tr.members.forEach(m => set.add(m.t)); tr.vermin.forEach(v => set.add(v.t)); } }
    return set;
  }
  function layerItems(L) {
    const map = new Map(), cm = castMembers(L);
    for (const s of seasonsIn()) for (const x of (BUILD.B.lists[L + '|' + s] || [])) {
      if (x.vfish) continue;
      if (cm && !cm.has(x.c.t)) continue;
      const k = x.c.t;
      if (!map.has(k)) map.set(k, { c: x.c, vermin: x.vermin, vclass: x.vclass, slots: x.slots.slice(), tier: x.tier });
    }
    return [...map.values()];
  }
  function levelOf(it, L) {
    if (it.vermin) return 0;
    const s = it.slots[0];
    if (s === 'apex') return 3;
    return sim.tierOf({ c: it.c, slot: s, vermin: false }) >= 2 ? 2 : 1;
  }
  function tabLayers() { return BUILD.B.active.filter(L => (state.tab === 'cavern' ? CAVS : SURF).includes(L)); }
  function viewLayers() { const t = tabLayers(); return state.layer === 'all' ? t : (t.includes(state.layer) ? [state.layer] : []); }
  // the caverns a species can be cast in on this fort, whatever the tab shows
  const cavsOf = t => ((BUILD.B.P[t] && BUILD.B.P[t].layers) || []).filter(L => CAVS.includes(L) && BUILD.B.active.includes(L)).map(L => +L.slice(-1));
  const surfOf = t => ((BUILD.B.P[t] && BUILD.B.P[t].layers) || []).filter(L => SURF.includes(L) && BUILD.B.active.includes(L));
  function makeView() {
    sim.useBuild(BUILD.B);   // the side rules read this fort's layers (the matrix's nine builds must not leak in)
    const nodes = [], byT = {};
    const ls = viewLayers();
    const items = {};
    for (const L of ls) {
      items[L] = layerItems(L).filter(it => state.vermin || !it.vermin);
      for (const it of items[L]) {
        if (byT[it.c.t]) { byT[it.c.t].layers.push(L); byT[it.c.t].slotsBy[L] = it.slots; continue; }
        const n = { t: it.c.t, c: it.c, L, layers: [L], slotsBy: { [L]: it.slots }, slot: it.vermin ? 'vermin' : it.slots[0], vermin: it.vermin,
          level: levelOf(it, L), r: radius(it.c), cavs: cavsOf(it.c.t), surf: surfOf(it.c.t) };
        byT[n.t] = n; nodes.push(n);
      }
    }
    // map-only vermin (stocked from a neighbouring region tile, on none of the fort's layers): placed by the sides their raws
    // give them, drawn hollow, never cast
    const SIDE_LAYERS = { GROUND: ['ground'], FLYING: ['flying'], OCEAN: ['ocean'], FRESH: ['fresh'], CAVERN: CAVS };
    if (state.vermin && !(state.seasonBy === 'casts' && YEAR)) for (const t in (BUILD.B.mapOnly || {})) {   // map-only vermin are never cast
      const mo = BUILD.B.mapOnly[t];
      if (byT[t]) continue;
      if (state.season !== 'all' && mo.c.ns[+state.season]) continue;
      const lays = mo.sides.flatMap(x => SIDE_LAYERS[x]).filter(L => ls.includes(L));
      if (!lays.length) continue;
      const n = { t, c: mo.c, L: lays[0], layers: lays, slotsBy: Object.fromEntries(lays.map(L => [L, ['vermin']])), slot: 'vermin', vermin: true,
        level: 0, r: radius(mo.c), cavs: lays.filter(L => CAVS.includes(L)).map(L => +L.slice(-1)), surf: lays.filter(L => SURF.includes(L)), mapOnly: mo };
      byT[t] = n; nodes.push(n);
    }
    const edges = [];
    const fkey = BUILD.key + '|' + state.season + '|' + (state.seasonBy === 'casts' && YEAR ? 'casts' + YEAR._site : 'raws') + '|' + state.vermin + '|' + ls.join(',') + '|' + FAM_ORDER.map(f => state.fam[f] ? 1 : 0).join('');
    let E = edgeCache.get(fkey);
    if (!E) { E = computeEdges(nodes); edgeCache.set(fkey, E); }
    for (const [x, y, fams] of E) edges.push({ a: byT[x], b: byT[y], fams, f: FAM_ORDER.find(f => fams.some(z => z.f === f)) });
    const adj = new Map();
    for (const n of nodes) adj.set(n.t, { prey: new Set(), pred: new Set() });
    const why = new Map();
    for (const e of edges) { if (!e.a || !e.b) continue; adj.get(e.a.t).prey.add(e.b.t); adj.get(e.b.t).pred.add(e.a.t); why.set(e.a.t + '>' + e.b.t, e); }
    // user 17 Oct: an apex or predator that eats nothing under the links switched on drops to the prey tier
    for (const n of nodes) { n.demoted = !n.vermin && n.level >= 2 && adj.get(n.t).prey.size === 0; if (n.demoted) n.level = 1; }
    // value: within the view, the higher of the pet-value and body-size percentiles; war animals at the top
    const pct = (arr, f) => { const v = arr.map(f).filter(x => x > 0).sort((a, b) => a - b); return x => x <= 0 ? 0 : (d3.bisectRight(v, x) / v.length); };
    const nv = nodes.filter(n => !n.vermin);
    const pp = pct(nv, n => n.c.pet), mp = pct(nv, n => n.c.m);
    for (const n of nodes) n.value = n.vermin ? 0 : (n.c.war ? 1 : Math.max(pp(n.c.pet), mp(n.c.m)));
    // the high-value (seed) set of each layer over the view's lists, the cast builder's own rule
    for (const L of ls) {
      const free = items[L].filter(it => !it.vermin && !it.slots.includes('placed plant'));
      const hv = sim.hvSet(free.map(it => ({ c: it.c })), state.prm);
      for (const t in hv) if (byT[t] && byT[t].L === L) byT[t].hv = hv[t];
    }
    VIEW = { nodes, byT, edges, adj, why, layers: ls };
  }
  // every pair in one realm (the surface, or one cavern) that a switched-on rule links; the cast-bound rules (hunting pairs,
  // the ladder) need a layer both are on, the others only the realm (a raptor's vermin, the tool's gobble, the raws' tokens)
  function computeEdges(nodes) {
    const out = [], on = state.fam;
    for (const a of nodes) {
      if (a.vermin) continue;
      const ra = new Set(a.layers.map(realmOf));
      for (const b of nodes) {
        if (a === b) continue;
        const common = a.layers.filter(L => b.layers.includes(L));
        let fams = [];
        if (common.length) {
          for (const L of common) for (const x of sim.linkWhy({ c: a.c, slots: a.slotsBy[L], vermin: false }, { c: b.c, slots: b.slotsBy[L], vermin: b.vermin, vclass: b.c.vc }, L, on))
            if (!fams.some(y => y.f === x.f)) fams.push(Object.assign({ L }, x));
        } else if (b.layers.some(L => ra.has(realmOf(L)))) {
          const L = a.L, off = Object.assign({}, on, { hunt: false, ladder: false });
          fams = sim.linkWhy({ c: a.c, slots: a.slotsBy[L], vermin: false }, { c: b.c, slots: b.slotsBy[b.L], vermin: b.vermin, vclass: b.c.vc }, L, off).map(x => Object.assign({ L }, x));
        }
        if (fams.length) out.push([a.t, b.t, fams]);
      }
    }
    return out;
  }
  function radius(c) { return 2.6 + 1.9 * Math.sqrt(Math.min(40, Math.max(1, c.c1 || 1))); }

  // ------------------------------------------------------------------ layout
  let W = 800, H = 560, transform = d3.zoomIdentity;
  const canvas = $('#net'), ctx = canvas.getContext('2d');
  function layout() {
    const nodes = VIEW.nodes, ls = VIEW.layers;
    const pad = 28, padL = state.layout === 'levels' ? 64 : 28;
    const cols = {};
    if (state.layout === 'levels') {
      // one column per layer (surface) or per set of caverns (caverns: 1, 1+2, 2, all three, 1+3, 2+3, 3, by mean depth),
      // width by the square root of its node count; four bands top to bottom (apex .. vermin)
      const keyOf = n => state.tab === 'cavern' ? n.layers.map(L => L.slice(-1)).sort().join(',') : n.L;
      for (const n of nodes) n.col = keyOf(n);
      const keys = state.tab === 'cavern' ? CAVGROUPS.filter(k => nodes.some(n => n.col === k)) : ls;
      const wts = keys.map(k => Math.sqrt(nodes.filter(n => n.col === k).length + 4));
      const tot = wts.reduce((a, b) => a + b, 0);
      let x = padL;
      keys.forEach((k, i) => { const w = (W - pad - padL) * wts[i] / tot; cols[k] = { x0: x, x1: x + w, cx: x + w / 2, label: state.tab === 'cavern' ? CAVGROUP_LABEL[k] : SHORT[k] }; x += w; });
      const bandH = (H - 2 * pad - 18) / 4;
      const band = l => pad + 18 + (3 - l) * bandH + bandH / 2;
      // within each column and tier, one sub-column per guild type (vermin: per vermin type), width by its node count
      const sub = [], cell = {};
      for (const n of nodes) { n.grp = groupOf(n); const k = n.col + '|' + n.level; (cell[k] = cell[k] || {}); (cell[k][n.grp] = cell[k][n.grp] || []).push(n); }
      for (const k in cell) {
        const [ck, lv] = [k.slice(0, k.lastIndexOf('|')), +k.slice(k.lastIndexOf('|') + 1)], col = cols[ck];
        const gs = Object.keys(cell[k]).sort((a, b) => GROUP_ORDER.indexOf(a) - GROUP_ORDER.indexOf(b));
        const wt = g => cell[k][g].length + 1.5, tot = gs.reduce((a, g) => a + wt(g), 0);
        let x0 = col.x0 + 2;
        for (const g of gs) {
          const w = (col.x1 - col.x0 - 4) * wt(g) / tot, sc = { x0, x1: x0 + w, cx: x0 + w / 2, last: g === gs[gs.length - 1], l: lv, label: g, n: cell[k][g].length, many: gs.length > 1 };
          for (const n of cell[k][g]) n.sc = sc;
          sub.push(sc); x0 += w;
        }
      }
      for (const n of nodes) {
        const sc = n.sc;
        n.x = n.x != null && n._lay === 'levels' && n._grp === n.grp ? n.x : sc.cx + (Math.random() - 0.5) * (sc.x1 - sc.x0) * 0.8;
        n.y = n.y != null && n._lay === 'levels' ? n.y : band(n.level) + (Math.random() - 0.5) * 30;
        n.tx = sc.cx; n.ty = band(n.level); n._lay = 'levels'; n._grp = n.grp;
      }
      const s = d3.forceSimulation(nodes).stop()
        .force('x', d3.forceX(n => n.tx).strength(n => 0.05 + 0.6 / Math.max(1, (n.sc.x1 - n.sc.x0) / 40)))
        .force('y', d3.forceY(n => n.ty).strength(0.22))
        .force('c', d3.forceCollide(n => n.r + 1.4).iterations(2));
      for (let i = 0; i < 220; i++) {
        s.tick();
        if (i % 20 === 19 || i === 219) for (const n of nodes) { const c = n.sc; n.x = c.x1 - c.x0 > 2 * n.r ? Math.max(c.x0 + n.r, Math.min(c.x1 - n.r, n.x)) : c.cx; }
      }
      VIEW.cols = cols; VIEW.band = band; VIEW.bandH = bandH; VIEW.sub = sub;
    } else {
      for (const n of nodes) { if (n._lay !== 'force') { n.x = W / 2 + (Math.random() - 0.5) * W * 0.6; n.y = H / 2 + (Math.random() - 0.5) * H * 0.6; } n._lay = 'force'; }
      // a dense lattice draws as a hairball, so the layout uses a sample of the links: at most 6 per node
      const deg = new Map(), links = [];
      const shuffled = d3.shuffle(VIEW.edges.slice());
      for (const e of shuffled) {
        if (!e.a || !e.b) continue;
        const da = deg.get(e.a) || 0, db = deg.get(e.b) || 0;
        if (da < 6 && db < 6) { links.push({ source: e.a, target: e.b }); deg.set(e.a, da + 1); deg.set(e.b, db + 1); }
      }
      const s = d3.forceSimulation(nodes).stop()
        .force('l', d3.forceLink(links).distance(38).strength(0.25))
        .force('q', d3.forceManyBody().strength(-26).distanceMax(240))
        .force('x', d3.forceX(W / 2).strength(0.04)).force('y', d3.forceY(H / 2).strength(0.06))
        .force('c', d3.forceCollide(n => n.r + 1.2));
      for (let i = 0; i < 260; i++) s.tick();
      VIEW.cols = null;
    }
  }

  // ------------------------------------------------------------------ drawing
  let TOK = {};
  function readTokens() {
    const cs = getComputedStyle(document.documentElement);
    for (const k of ['ink', 'muted', 'line', 'surface', 'bg', 'accent', 'c-red', 'c-purple', 'c-green', 'c-amber', 'c-blue', 'seq-lo', 'seq-hi', 'faint'])
      TOK[k] = cs.getPropertyValue('--' + k).trim();
  }
  const seq = t => d3.interpolateLab(TOK['seq-lo'], TOK['seq-hi'])(Math.max(0, Math.min(1, t)));
  function colorOf(n) {
    if (state.color === 'cavern') return n.cavs.length ? TOK[CAV_COL[n.cavs[0]]] : TOK.faint;
    if (state.color === 'slot') return TOK[SLOT_COL[n.slot] || 'muted'];
    if (state.color === 'habitat') return n.vermin ? TOK.muted : TOK[HAB_COL[n.c.h] || 'muted'];
    if (state.color === 'value') return n.vermin ? TOK.muted : seq(n.value);
    if (state.color === 'inclusion') {
      const st = STATS && STATS.by[n.L];
      if (!st) return TOK.faint;
      const v = (st.seasons[n.t] || 0) / st.casts;
      return v > 0 ? seq(Math.sqrt(v)) : TOK.faint;
    }
    return TOK.muted;
  }
  function shapeOf(n) {
    if (state.shape === 'habitat') return n.vermin ? 'dot' : (HAB_SHAPE[n.c.h] || 'circle');
    if (state.shape === 'guild') return FAM_SHAPE[GUILD_FAM(n.c.g)] || 'circle';
    return LEVEL_SHAPE[n.level];
  }
  function drawShape(sh, x, y, r) {
    ctx.beginPath();
    if (sh === 'circle') ctx.arc(x, y, r, 0, 2 * Math.PI);
    else if (sh === 'dot') ctx.arc(x, y, Math.max(1.6, r * 0.6), 0, 2 * Math.PI);
    else if (sh === 'square') { const s = r * 0.9; ctx.rect(x - s, y - s, 2 * s, 2 * s); }
    else if (sh === 'diamond') { const s = r * 1.25; ctx.moveTo(x, y - s); ctx.lineTo(x + s, y); ctx.lineTo(x, y + s); ctx.lineTo(x - s, y); ctx.closePath(); }
    else if (sh === 'tri') { const s = r * 1.35; ctx.moveTo(x, y - s); ctx.lineTo(x + s * 0.92, y + s * 0.62); ctx.lineTo(x - s * 0.92, y + s * 0.62); ctx.closePath(); }
    else if (sh === 'star') { const s = r * 1.4; for (let i = 0; i < 10; i++) { const a = -Math.PI / 2 + i * Math.PI / 5, rr = i % 2 ? s * 0.45 : s; ctx.lineTo(x + rr * Math.cos(a), y + rr * Math.sin(a)); } ctx.closePath(); }
    else if (sh === 'cross') { const s = r * 1.1, w = r * 0.42; ctx.rect(x - s, y - w, 2 * s, 2 * w); ctx.rect(x - w, y - s, 2 * w, 2 * s); }
  }
  function castSet() {
    if (!state.castSel || !YEAR) return null;
    const tr = YEAR[state.castSel];
    if (!tr) return null;
    return { tr, set: new Set(tr.members.map(m => m.t).concat(tr.vermin.map(v => v.t))) };
  }
  function draw() {
    if (!VIEW) return;
    const dpr = window.devicePixelRatio || 1;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = TOK.surface; ctx.fillRect(0, 0, W, H);
    ctx.save();
    ctx.translate(transform.x, transform.y); ctx.scale(transform.k, transform.k);
    const k = transform.k;
    // bands and columns
    if (VIEW.cols) {
      ctx.font = `600 ${11 / k}px "JetBrains Mono", ui-monospace, monospace`;
      ctx.fillStyle = TOK.muted; ctx.strokeStyle = TOK.line; ctx.lineWidth = 1 / k;
      for (const L in VIEW.cols) {
        const c = VIEW.cols[L];
        ctx.fillText(c.label.toUpperCase(), c.x0 + 4, 20);
        ctx.beginPath(); ctx.moveTo(c.x1, 8); ctx.lineTo(c.x1, H - 8); ctx.stroke();
      }
      for (let l = 3; l >= 0; l--) ctx.fillText(LEVEL_NAME[l], 6, VIEW.band(l) + 4);
      // guild sub-columns: a faint divider between neighbours and the guild's name where it fits
      ctx.font = `${9 / k}px "JetBrains Mono", ui-monospace, monospace`;
      ctx.setLineDash([2 / k, 3 / k]);
      for (const sc of VIEW.sub || []) {
        if (!sc.many) continue;
        const top = VIEW.band(sc.l) - VIEW.bandH / 2 + 4;
        if (!sc.last) {
          ctx.beginPath(); ctx.moveTo(sc.x1, top); ctx.lineTo(sc.x1, top + VIEW.bandH - 8); ctx.stroke();
        }
        if (ctx.measureText(sc.label).width < sc.x1 - sc.x0 - 4 / k) ctx.fillText(sc.label, sc.x0 + 3 / k, top + 8 / k);
      }
      ctx.setLineDash([]);
    }
    const cs = castSet();
    const sel = state.sel && VIEW.byT[state.sel] ? VIEW.byT[state.sel] : null;
    const A = sel ? VIEW.adj.get(sel.t) : null;
    const Q = searchHits();   // live search: matches light up over everything else
    const lit = n => Q ? Q.has(n.t) : (cs ? cs.set.has(n.t) : (sel ? (n === sel || A.prey.has(n.t) || A.pred.has(n.t)) : true));
    // edges
    let edges = [];
    if (cs) edges = cs.tr.edges.map(([x, y]) => VIEW.why.get(x + '>' + y) || { a: VIEW.byT[x], b: VIEW.byT[y], f: 'ladder', fams: [{ f: 'ladder', d: 'the cast\'s own growth link' }] }).filter(e => e.a && e.b);
    else if (sel) edges = VIEW.edges.filter(e => e.a === sel || e.b === sel);
    else if (state.edges === 'all') edges = VIEW.edges;
    ctx.lineWidth = (edges.length > 3000 ? 0.6 : 1.1) / k;
    const alpha = edges.length > 3000 ? 0.09 : (edges.length > 600 ? 0.22 : 0.6);
    for (const f of FAM_ORDER.concat([undefined])) {
      ctx.strokeStyle = f ? TOK[FAM[f].col] : TOK.ink; ctx.globalAlpha = alpha;
      for (const dash of [false, true]) {   // dashed: the selection's predators
        if (dash && !sel) continue;
        ctx.setLineDash(dash ? [4 / k, 3 / k] : []); ctx.beginPath();
        for (const e of edges) { if (!e.a || !e.b || e.f !== f || (sel && (e.b === sel) !== dash)) continue; ctx.moveTo(e.a.x, e.a.y); ctx.lineTo(e.b.x, e.b.y); }
        ctx.stroke();
      }
    }
    ctx.setLineDash([]);
    const se = state.selEdge;
    if (se && se.a && se.b) { ctx.globalAlpha = 1; ctx.lineWidth = 3 / k; ctx.strokeStyle = TOK.accent; ctx.beginPath(); ctx.moveTo(se.a.x, se.a.y); ctx.lineTo(se.b.x, se.b.y); ctx.stroke(); }
    VIEW.drawn = edges;
    ctx.globalAlpha = 1;
    // nodes, dim first
    const order = VIEW.nodes.slice().sort((a, b) => (lit(a) - lit(b)) || (b.r - a.r));
    for (const n of order) {
      const on = lit(n);
      ctx.globalAlpha = on ? 1 : 0.16;
      drawShape(shapeOf(n), n.x, n.y, n.r);
      if (state.color === 'cavern' && n.cavs.length) {
        ctx.save(); ctx.clip();
        const w = 2.8 * n.r / n.cavs.length;
        n.cavs.forEach((k, i) => { ctx.fillStyle = TOK[CAV_COL[k]]; ctx.fillRect(n.x - 1.4 * n.r + i * w, n.y - 1.5 * n.r, w + 0.3, 3 * n.r); });
        ctx.restore();
        drawShape(shapeOf(n), n.x, n.y, n.r);
      } else if (n.mapOnly) { ctx.fillStyle = TOK.surface; ctx.fill(); ctx.lineWidth = 1.6 / k; ctx.strokeStyle = colorOf(n); ctx.stroke(); }
      else { ctx.fillStyle = colorOf(n); ctx.fill(); }
      ctx.lineWidth = 1.2 / k; ctx.strokeStyle = TOK.surface; ctx.stroke();
      if (n.hv && on && !n.vermin && state.color !== 'inclusion') { ctx.lineWidth = 1.4 / k; ctx.strokeStyle = TOK.ink; drawShape('circle', n.x, n.y, n.r + 3); ctx.stroke(); }
    }
    ctx.globalAlpha = 1;
    // labels: the selection and its links, a highlighted cast, the hover; everything when zoomed in
    const lab = new Set();
    const hov = state.hover && VIEW.byT[state.hover];
    if (sel) {   // a selection shows only its own label and those of what it eats and what eats it
      lab.add(sel); for (const t of [...A.prey, ...A.pred]) lab.add(VIEW.byT[t]);
      if (hov && (A.prey.has(hov.t) || A.pred.has(hov.t))) lab.add(hov);
    } else {
      if (cs) for (const t of cs.set) if (VIEW.byT[t]) lab.add(VIEW.byT[t]);
      if (k >= 2.4) for (const n of VIEW.nodes) lab.add(n);
      if (hov) lab.add(hov);
    }
    if (Q && Q.size <= 60) for (const t of Q) lab.add(VIEW.byT[t]);
    ctx.font = `${11.5 / k}px "Atkinson Hyperlegible", system-ui, sans-serif`;
    ctx.lineJoin = 'round';
    for (const n of lab) {
      if (!n) continue;
      const s = n.c.nm;
      ctx.lineWidth = 3 / k; ctx.strokeStyle = TOK.surface; ctx.strokeText(s, n.x + n.r + 3 / k, n.y + 4 / k);
      ctx.fillStyle = TOK.ink; ctx.fillText(s, n.x + n.r + 3 / k, n.y + 4 / k);
    }
    if (Q) {   // ring every match; label them while there are few enough to read
      ctx.lineWidth = 2 / k; ctx.strokeStyle = TOK.accent;
      for (const t of Q) { const n = VIEW.byT[t]; drawShape('circle', n.x, n.y, n.r + 4); ctx.stroke(); }
    }
    if (sel) { ctx.lineWidth = 2 / k; ctx.strokeStyle = TOK.accent; drawShape('circle', sel.x, sel.y, sel.r + 5); ctx.stroke(); }
    ctx.restore();
  }
  function resize() {
    const box = $('#netbox');
    W = Math.max(300, box.clientWidth); H = Math.max(430, Math.min(864, Math.round(W * 0.744)));
    const dpr = window.devicePixelRatio || 1;
    canvas.width = W * dpr; canvas.height = H * dpr; canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
  }
  // the view never leaves the figure (user 17 Oct): no zooming out past the whole figure, no panning beyond its edges
  const zoom = d3.zoom().scaleExtent([1, 8]).on('zoom', ev => { transform = ev.transform; draw(); });
  function bindZoom() {
    zoom.extent([[0, 0], [W, H]]).translateExtent([[0, 0], [W, H]]);
    d3.select(canvas).call(zoom.transform, d3.zoomTransform(canvas));   // re-clamp the current view to the new bounds
  }
  d3.select(canvas).call(zoom).on('dblclick.zoom', null);
  function nodeAt(px, py) {
    const [x, y] = transform.invert([px, py]);
    let best = null, bd = Infinity;
    for (const n of VIEW.nodes) { const d = Math.hypot(n.x - x, n.y - y); if (d < n.r + 5 / transform.k && d < bd) { bd = d; best = n; } }
    return best;
  }
  const tip = $('#tip');
  canvas.addEventListener('mousemove', ev => {
    const r = canvas.getBoundingClientRect();
    const n = nodeAt(ev.clientX - r.left, ev.clientY - r.top);
    const t = n ? n.t : null;
    canvas.style.cursor = n ? 'pointer' : (edgeAt(ev.clientX - r.left, ev.clientY - r.top) ? 'pointer' : 'crosshair');
    if (t !== state.hover) { state.hover = t; draw(); }
    if (n) {
      const A = VIEW.adj.get(n.t);
      tip.innerHTML = `<b>${esc(n.c.nm)}</b> <span class="mono">${esc(n.t)}</span>${n.mapOnly ? '<br><i>on the map only: from a neighbouring tile (' + esc(n.mapOnly.from.map(b => bname(b)).join(', ')) + '), never cast</i>' : ''}<br>${esc(LNAME[n.L])} · ${esc(n.vermin ? 'vermin ' + (n.c.vc || '') : n.slotsBy[n.L].join(' / '))}` +
        `<br>${fmtMass(n.c.m)} · groups of ${n.c.c0}-${n.c.c1}${n.c.pet ? ' · pet value ' + n.c.pet : ''}` +
        `<br>eats ${A.prey.size} · eaten by ${A.pred.size}${n.hv ? '<br>high value: ' + esc(n.hv) : ''}` + statLine(n);
      tip.hidden = false;
      const bx = $('#netbox').getBoundingClientRect();
      let x = ev.clientX - bx.left + 14, y = ev.clientY - bx.top + 12;
      if (x + 240 > bx.width) x -= 260;
      tip.style.left = x + 'px'; tip.style.top = y + 'px';
    } else tip.hidden = true;
  });
  canvas.addEventListener('mouseleave', () => { tip.hidden = true; state.hover = null; draw(); });
  function edgeAt(px, py) {
    const [x, y] = transform.invert([px, py]);
    let best = null, bd = 5 / transform.k;
    for (const e of (VIEW.drawn || [])) {
      if (!e.a || !e.b) continue;
      const dx = e.b.x - e.a.x, dy = e.b.y - e.a.y, L2 = dx * dx + dy * dy || 1;
      const t = Math.max(0, Math.min(1, ((x - e.a.x) * dx + (y - e.a.y) * dy) / L2));
      const d = Math.hypot(e.a.x + t * dx - x, e.a.y + t * dy - y);
      if (d < bd) { bd = d; best = e; }
    }
    return best;
  }
  const pop = $('#edgepop');
  function showEdge(e, px, py) {
    state.selEdge = e;
    const back = VIEW.why.get(e.b.t + '>' + e.a.t);
    pop.innerHTML = `<button type="button" class="x" aria-label="Close">×</button><h4>${esc(e.a.c.nm)} <span class="arrow">eats</span> ${esc(e.b.c.nm)}</h4>` +
      `<ul>${(e.fams || []).map(x => `<li><i style="background:var(--${FAM[x.f].col})"></i><b>${esc(FAM[x.f].lab)}</b>${x.L ? ` <span class="small">${esc(LNAME[x.L])}</span>` : ''}<br>${esc(x.d)}</li>`).join('')}</ul>` +
      `<p class="small">${esc(e.a.c.nm)}: ${fmtMass(e.a.c.m)}, groups ${e.a.c.c0}-${e.a.c.c1}, ${esc(e.a.c.h)}, ${esc(e.a.c.g)}. ${esc(e.b.c.nm)}: ${fmtMass(e.b.c.m)}, groups ${e.b.c.c0}-${e.b.c.c1}, ${esc(e.b.vermin ? 'vermin ' + (e.b.c.swv || '') : e.b.c.h + ', ' + e.b.c.g)}.</p>` +
      (back ? `<p class="small">Also the other way: ${esc(e.b.c.nm)} eats ${esc(e.a.c.nm)} (${esc(back.fams.map(x => FAM[x.f].lab).join(', '))}).</p>` : '') +
      `<p class="row"><button type="button" class="sp" data-t="${esc(e.a.t)}">select ${esc(e.a.c.nm)}</button><button type="button" class="sp" data-t="${esc(e.b.t)}">select ${esc(e.b.c.nm)}</button></p>`;
    pop.hidden = false;
    const bw = $('#netbox').clientWidth;
    pop.style.left = Math.max(6, Math.min(bw - 330, px + 12)) + 'px'; pop.style.top = Math.max(6, py - 20) + 'px';
    draw();
  }
  pop.addEventListener('click', ev => { if (ev.target.closest('.x')) { pop.hidden = true; state.selEdge = null; draw(); } });
  canvas.addEventListener('click', ev => {
    const r = canvas.getBoundingClientRect(), px = ev.clientX - r.left, py = ev.clientY - r.top;
    const n = nodeAt(px, py);
    if (!n) { const e = edgeAt(px, py); if (e) { showEdge(e, px, py); return; } }
    pop.hidden = true; state.selEdge = null;
    state.sel = n ? n.t : null; state.castSel = null;
    renderInspector(); renderYear(); draw();
  });
  function statLine(n) {
    const st = STATS && STATS.by[n.L];
    if (!st) return '';
    const v = (st.seasons[n.t] || 0) / st.casts;
    return `<br>cast in ${pct(v)} of ${LNAME[n.L].toLowerCase()} season casts`;
  }
  const pct = v => (v * 100 >= 10 || v === 0 ? Math.round(v * 100) : (v * 100).toFixed(1)) + '%';
  const fmtMass = m => m >= 1e6 ? (m / 1e6).toFixed(m >= 1e7 ? 0 : 1) + ' m³ body' : m >= 1000 ? Math.round(m / 1000) + ' L body' : (m || 0) + ' cm³ body';

  // ------------------------------------------------------------------ legend
  function renderLegend() {
    const sw = (col, sh) => `<svg width="16" height="16" viewBox="-8 -8 16 16" aria-hidden="true">${shapeSvg(sh, col)}</svg>`;
    let colorPart = '';
    if (state.color === 'slot') colorPart = SLOT_LEGEND.map(([s, lab]) => `<span>${sw(`var(--${SLOT_COL[s]})`, 'circle')}${esc(lab)}</span>`).join('');
    else if (state.color === 'habitat') colorPart = Object.entries(HAB_COL).map(([h, c]) => `<span>${sw(`var(--${c})`, 'circle')}${h}</span>`).join('') + `<span>${sw('var(--muted)', 'circle')}vermin</span>`;
    else if (state.color === 'cavern') colorPart = [1, 2, 3].map(k => `<span>${sw(`var(--${CAV_COL[k]})`, 'circle')}cavern ${k}</span>`).join('') + '<span>one stripe per cavern it can be cast in (left to right 1, 2, 3); grey: never in the caverns</span>';
    else colorPart = `<span class="ramp"><i></i>${state.color === 'value' ? 'low → high value (pet value or body size percentile; war animals top)' : (STATS ? 'never → most often cast (√ share of season casts)' : 'run the simulator to colour by how often cast')}</span>`;
    let shapePart = '';
    if (state.shape === 'level') shapePart = [[3, 'apex'], [2, 'predator'], [1, 'prey'], [0, 'vermin']].map(([l, lab]) => `<span>${sw('var(--muted)', LEVEL_SHAPE[l])}${lab}</span>`).join('');
    else if (state.shape === 'habitat') shapePart = Object.entries(HAB_SHAPE).map(([h, s]) => `<span>${sw('var(--muted)', s)}${h}</span>`).join('');
    else shapePart = Object.entries(FAM_SHAPE).filter(([f]) => f !== 'other').map(([f, s]) => `<span>${sw('var(--muted)', s)}${f}</span>`).join('');
    $('#legend').innerHTML = `<div><b>Colour</b>${colorPart}</div><div><b>Shape</b>${shapePart}</div><div><b>Size</b><span>largest group the raws allow (cluster max)</span>` +
      `<span>${sw('none', 'ring')}high-value: a possible seed</span>${Object.keys(BUILD.B.mapOnly || {}).length ? '<span>hollow: map-only vermin from a neighbouring tile</span>' : ''}<span>${FAM_ORDER.filter(f => state.fam[f]).map(f => `<span class="ln" style="--lc:var(--${FAM[f].col})">${esc(FAM[f].lab.toLowerCase())}</span>`).join(' ')}; dashed: the selection's predators; click a link for details</span></div>`;
  }
  function shapeSvg(sh, col) {
    const f = `fill="${col}"`;
    switch (sh) {
      case 'ring': return '<circle r="6" fill="none" stroke="var(--ink)" stroke-width="1.4"/><circle r="3" fill="var(--muted)"/>';
      case 'dot': return `<circle r="3" ${f}/>`;
      case 'square': return `<rect x="-5" y="-5" width="10" height="10" ${f}/>`;
      case 'diamond': return `<path d="M0 -6.5L6.5 0L0 6.5L-6.5 0Z" ${f}/>`;
      case 'tri': return `<path d="M0 -6.8L6.3 4.3L-6.3 4.3Z" ${f}/>`;
      case 'star': return `<path d="${d3.range(10).map(i => { const a = -Math.PI / 2 + i * Math.PI / 5, r = i % 2 ? 3 : 7; return (i ? 'L' : 'M') + (r * Math.cos(a)).toFixed(1) + ' ' + (r * Math.sin(a)).toFixed(1); }).join('')}Z" ${f}/>`;
      case 'cross': return `<path d="M-6 -2.2H-2.2V-6H2.2V-2.2H6V2.2H2.2V6H-2.2V2.2H-6Z" ${f}/>`;
      default: return `<circle r="5.5" ${f}/>`;
    }
  }

  // ------------------------------------------------------------------ inspector
  function renderInspector() {
    const box = $('#inspect');
    const n = state.sel && VIEW.byT[state.sel];
    if (!n) {
      const nv = VIEW.nodes.filter(x => !x.vermin).length;
      box.innerHTML = `<h3>${VIEW.nodes.length} creatures in view</h3><p class="note">${nv} animals and ${VIEW.nodes.length - nv} vermin on ${VIEW.layers.length} layer${VIEW.layers.length === 1 ? '' : 's'}, ${VIEW.edges.length.toLocaleString('en')} feeding link${VIEW.edges.length === 1 ? '' : 's'} from the rules switched on. Click a link for its rule.` +
        ` Click a creature to see what it eats, what eats it, and how often the cast builder picks it.</p>` + rejectedNote();
      return;
    }
    const c = n.c, A = VIEW.adj.get(n.t);
    const flags = [c.gi && 'giant', c.ap && 'animal person', c.se && 'sentient', c.sav && 'savage', c.gd && 'good', c.ev && 'evil', c.ex && 'real-world extinct',
      c.war && 'war-trainable', c.lp && 'large predator', c.bn && 'benign', c.th.length && ('thief: ' + c.th.join(', ').toLowerCase()), n.demoted && 'eats nothing: drawn as prey'].filter(Boolean);
    const ns = c.ns.map((x, i) => x ? SEASONS[i] : null).filter(Boolean);
    const list = (set) => [...set].map(t => VIEW.byT[t]).filter(Boolean).sort((a, b) => b.level - a.level || (a.c.nm < b.c.nm ? -1 : 1))
      .map(x => `<button type="button" class="sp" data-t="${esc(x.t)}"><i style="background:var(--${SLOT_COL[x.slot] || 'muted'})"></i>${esc(x.c.nm)}</button>`).join('');
    let st = '';
    for (const L of n.layers) {
      const S = STATS && STATS.by[L];
      if (!S) continue;
      const share = (S.seasons[n.t] || 0) / S.casts, seed = (S.seed[n.t] || 0) / S.casts, apex = (S.apex[n.t] || 0) / S.casts;
      const slots = Object.entries(S.slot).filter(([k]) => k.startsWith(n.t + '|')).map(([k, v]) => `${k.split('|')[1]} ${pct(v / S.casts)}`).join(', ');
      st += `<tr><td>${esc(LNAME[L])}</td><td class="num">${pct(share)}</td><td class="num">${pct(seed)}</td><td class="num">${pct(apex)}</td><td>${esc(slots || '-')}</td></tr>`;
    }
    box.innerHTML = `<h3>${esc(c.nm)}</h3><p class="mono small">${esc(n.t)}${c.rt ? ' · root ' + esc(c.rt) : ''}</p>
      ${n.mapOnly ? `<p class="note">On the map only: DF stocks it from a neighbouring tile (${esc(n.mapOnly.from.map(b => bname(b)).join(', '))}). It is on none of the fort's layers, so it is never cast, but consumers still eat it; its sides come from its raws: ${esc(n.mapOnly.sides.join(', ').toLowerCase())}.</p>` : ''}${n.cavs.length && state.tab === 'surface' ? `<p class="note">Also cast in cavern ${n.cavs.join(', ')} (Caverns tab).</p>` : ''}${n.surf.length && state.tab === 'cavern' ? `<p class="note">Also on the surface: ${n.surf.map(L => LNAME[L].toLowerCase()).join(', ')} (Surface tab).</p>` : ''}
      <div class="chips">${n.layers.map(L => `<span class="chip">${esc(LNAME[L])}: ${esc(n.vermin ? 'vermin ' + (c.vc || '') : n.slotsBy[L].join(' / '))}</span>`).join('')}</div>
      <dl class="kv"><div><dt>body</dt><dd>${fmtMass(c.m)}</dd></div><div><dt>group</dt><dd>${c.c0}-${c.c1}</dd></div>
      <div><dt>habitat</dt><dd>${esc(c.h)}</dd></div><div><dt>guild</dt><dd>${esc(c.g)} · ${esc(GUILD_FAM(c.g))}</dd></div>
      <div><dt>pet value</dt><dd>${c.pet || '-'}</dd></div><div><dt>raw FREQUENCY</dt><dd>${c.fq ?? '-'}</dd></div>
      ${c.wd != null ? `<div><dt>weirdness</dt><dd>${c.wd}</dd></div>` : ''}${c.d ? `<div><dt>raw depth</dt><dd>${c.d[0]}-${c.d[1]}</dd></div>` : ''}</dl>
      ${flags.length ? `<p class="chips">${flags.map(f => `<span class="chip flag">${esc(f)}</span>`).join('')}</p>` : ''}
      ${ns.length ? `<p class="note">Absent in ${ns.join(', ')} (NO_ season tags).</p>` : ''}
      ${n.hv ? `<p class="note"><b>High value</b> on ${esc(LNAME[n.L].toLowerCase())}: ${esc(n.hv)}. It can seed a cast.</p>` : ''}
      ${st ? `<h4>In the simulated years</h4><div class="tbl"><table><thead><tr><th>layer</th><th class="num">cast</th><th class="num">seed</th><th class="num">apex</th><th>by slot</th></tr></thead><tbody>${st}</tbody></table></div>` : ''}
      ${whyList(n, A)}
      <h4>Eats (${A.prey.size})</h4><div class="splist">${list(A.prey) || '<span class="note">nothing in view</span>'}</div>
      <h4>Eaten by (${A.pred.size})</h4><div class="splist">${list(A.pred) || '<span class="note">nothing in view</span>'}</div>`;
  }
  function whyList(n, A) {
    const c = n.c, L = n.L, rows = [];
    const arm = sim.armedWhy(c, n.slotsBy[L], L);
    if (arm) rows.push(['hunt', 'armed: ' + arm]);
    const g = sim.gobbleSet(c, L);
    const al = sim.allowedSides(c);
    if (g && !al.sides.length) rows.push(['gobble', 'no vermin: ' + al.why]);
    else if (g) rows.push(['gobble', 'GOBBLE_VERMIN_CLASS written: ' + [...g.keys()].map(k => k.replace('SWV_', '').toLowerCase().replace('_', ' ')).join(', ') + ' from ' + al.sides.join(', ').toLowerCase() + (al.why ? ' (' + al.why + ')' : '')]);
    if (!c.v && c.ro === 'predator') { const am = sim.allowedSides(c, 'mass'); rows.push(['mass', 'vermin by mass and numbers from ' + (am.sides.length ? am.sides.join(', ').toLowerCase() : 'no side') + (am.why ? ' (' + am.why + ')' : '')]); }
    if (c.gvc.length || c.gvt.length || c.dhv) rows.push(['raws', [c.gvc.length && 'GOBBLE_VERMIN_CLASS:' + c.gvc.join(','), c.dhv && 'hunts vermin'].filter(Boolean).join('; ')]);
    const hf = sim.huntFlag(c);
    if (hf) rows.push(['flags', hf]);
    if (n.vermin) rows.push(['gobble', 'vermin class ' + (c.swv || '?').replace('SWV_', '').toLowerCase().replace('_', ' ') + ' on ' + sim.sidesOf(c.t).join(', ').toLowerCase()]);
    return rows.length ? `<ul class="rules">${rows.map(([f, t]) => `<li><i style="background:var(--${FAM[f].col})"></i>${esc(t)}${state.fam[f] ? '' : ' <em>(rule off)</em>'}</li>`).join('')}</ul>` : '<p class="note">No rule the tool applies gives it prey.</p>';
  }
  function rejectedNote() {
    const r = BUILD.B.rejected || [];
    if (!r.length) return '';
    const by = d3.rollup(r, v => v.length, x => x.why);
    return `<h4>Kept out by the gates (${r.length})</h4><ul class="small">${[...by].sort((a, b) => b[1] - a[1]).map(([w, k]) => `<li>${esc(w)}: ${k}</li>`).join('')}</ul>`;
  }
  document.addEventListener('click', ev => {
    const b = ev.target.closest('button.sp[data-t]');
    if (!b) return;
    const t = b.dataset.t;
    if (!VIEW.byT[t]) { const p = BUILD.B.P[t]; if (p && (p.layers || []).some(L => (state.tab === 'cavern' ? SURF : CAVS).includes(L))) setTab(state.tab === 'cavern' ? 'surface' : 'cavern'); state.layer = 'all'; syncControls(); refreshView(); }
    state.sel = t; state.castSel = null; renderInspector(); renderYear(); draw();
    $('#netbox').scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  });

  // ------------------------------------------------------------------ simulation
  let STATS = null, BASE = null, YEAR = null, running = 0;
  function prmNow() { return Object.assign({}, state.prm, { network: Object.assign({}, state.fam) }); }
  function runYear() {
    if (!BUILD.spec) return;
    sim.useBuild(BUILD.B);
    const site = 1 + Math.floor(Math.random() * 9999);
    YEAR = sim.year(BUILD.B, BUILD.spec, prmNow(), site, 250);
    YEAR._site = site;
    state.castSel = null;
    state.seasonBy = 'casts';   // a built year: the season buttons show its casts
    syncControls(); refreshView(); renderYear();
  }
  function runYears() {
    if (!BUILD.spec) return;
    const myRun = ++running, n = state.years, prm = prmNow(), B = BUILD.B, spec = BUILD.spec;
    sim.useBuild(B);
    const acc = { n: 0, by: {}, prm, key: BUILD.key };
    for (const L of B.active) acc.by[L] = { casts: 0, seasons: {}, seed: {}, apex: {}, slot: {}, guarantee: 0, unfilled: 0, links: [0, 0] };
    const btn = $('#runN'); btn.disabled = true;
    function chunk() {
      if (myRun !== running) return;
      const t0 = performance.now();
      while (acc.n < n && performance.now() - t0 < 30) {
        const cs = sim.year(B, spec, prm, 1, 250 + acc.n);
        for (const key in cs) {
          const tr = cs[key], S = acc.by[tr.L];
          S.casts++;
          for (const m of tr.members) {
            S.seasons[m.t] = (S.seasons[m.t] || 0) + 1;
            S.slot[m.t + '|' + m.slot] = (S.slot[m.t + '|' + m.slot] || 0) + 1;
            if (m.slot === 'apex') S.apex[m.t] = (S.apex[m.t] || 0) + 1;
          }
          for (const v of tr.vermin) S.seasons[v.t] = (S.seasons[v.t] || 0) + 1;
          if (tr.seed) S.seed[tr.seed] = (S.seed[tr.seed] || 0) + 1;
          S.guarantee += tr.guarantee.length;
          if (Object.keys(tr.unfilled).length) S.unfilled++;
          for (const [l, f] of (tr.linkStats || [])) { S.links[0] += l; S.links[1] += f; }
        }
        acc.n++;
      }
      $('#runState').textContent = acc.n < n ? `${acc.n} of ${n} years…` : `${n} years, ${prmText(prm)}`;
      if (acc.n < n) return setTimeout(chunk, 0);
      btn.disabled = false;
      STATS = acc;
      if (!state.statsLayer || !B.active.includes(state.statsLayer)) state.statsLayer = state.layer !== 'all' && B.active.includes(state.layer) ? state.layer : B.active[0];
      renderStats(); renderInspector(); renderLegend(); draw();
    }
    chunk();
  }
  function prmText(p) {
    const d = sim.P0, out = [];
    if (p.ap_pick !== d.ap_pick) out.push(`animal people ×${p.ap_pick}`);
    if (p.giant !== d.giant) out.push(`giants ×${p.giant}`);
    if (p.pack !== d.pack) out.push(`pack ×${p.pack}`);
    if (p.apex_pack !== d.apex_pack) out.push(`apex pack ×${p.apex_pack}`);
    if (p.reuse !== d.reuse) out.push(`repeat ×${p.reuse}`);
    if (p.hv_top !== d.hv_top) out.push(`high value top ${Math.round(p.hv_top * 100)}%`);
    if (!p.seed) out.push('no seed');
    if (!p.weird) out.push('no weirdness tilt');
    if (!p.guarantee) out.push('no web guarantee');
    out.push(p.links === 'network' ? 'growth on ' + FAM_ORDER.filter(f => p.network[f]).join('+') : 'ladder growth');
    return out.join(', ');
  }
  function eff(o) { const v = Object.values(o); const t = v.reduce((a, b) => a + b, 0); return t ? 1 / v.reduce((a, b) => a + (b / t) ** 2, 0) : 0; }
  function renderStats() {
    const box = $('#stats');
    if (!STATS || STATS.key !== BUILD.key) { box.innerHTML = `<p class="note">${BUILD.spec ? 'Run the simulator to see how often each species is cast.' : ''}</p>`; return; }
    const L = state.statsLayer, S = STATS.by[L];
    if (!S) { box.innerHTML = ''; return; }
    const Bs = BASE && BASE.key === BUILD.key ? BASE.by[L] : null;
    const memb = o => Object.fromEntries(Object.entries(o).filter(([t]) => !BY[t].v));
    const m = memb(S.seasons), places = Object.values(m).reduce((a, b) => a + b, 0) || 1;
    const share = f => Object.entries(m).reduce((a, [t, v]) => a + (f(BY[t]) ? v : 0), 0) / places;
    const elig = new Set(); for (let s = 0; s < 4; s++) for (const x of (BUILD.B.lists[L + '|' + s] || [])) if (!x.vermin) elig.add(x.c.t);
    const seeds = Object.entries(S.seed).sort((a, b) => b[1] - a[1]);
    const tiles = [
      ['eligible species', elig.size, null],
      ['effective species', eff(m).toFixed(1), Bs ? eff(memb(Bs.seasons)).toFixed(1) : null],
      ['animal people, share of places', pct(share(c => c.ap && !c.civ)), Bs ? pctOf(Bs, c => c.ap && !c.civ) : null],
      ['giants, share of places', pct(share(c => c.gi)), Bs ? pctOf(Bs, c => c.gi) : null],
      ['top seed', seeds.length ? `${BY[seeds[0][0]].nm} ${pct(seeds[0][1] / S.casts)}` : 'none', null],
      ['growth: linked candidates', S.links[1] ? pct(S.links[0] / S.links[1]) : 'n/a', null],
    ];
    if (L.startsWith('cavern')) tiles.push(['web guarantee fills per cast', (S.guarantee / S.casts).toFixed(2), null]);
    tiles.push(['casts with an unfilled slot', pct(S.unfilled / S.casts), null]);
    const rows = Object.entries(S.seasons).map(([t, v]) => ({ t, v: v / S.casts, seed: (S.seed[t] || 0) / S.casts, apex: (S.apex[t] || 0) / S.casts,
      b: Bs ? (Bs.seasons[t] || 0) / Bs.casts : null, n: VIEW.byT[t] }));
    for (const t of elig) if (!S.seasons[t]) rows.push({ t, v: 0, seed: 0, apex: 0, b: Bs ? (Bs.seasons[t] || 0) / Bs.casts : null, n: VIEW.byT[t] });
    rows.sort((a, b) => b.v - a.v || (a.t < b.t ? -1 : 1));
    STATS.rows = rows;
    box.innerHTML = `<div class="tabs" role="tablist">${BUILD.B.active.map(x => `<button type="button" role="tab" aria-selected="${x === L}" data-sl="${x}">${esc(LNAME[x])}</button>`).join('')}</div>
      <div class="tiles">${tiles.map(([k, v, b]) => `<div class="tile"><span>${esc(k)}</span><b>${esc(v)}</b>${b != null ? `<em>baseline ${esc(b)}</em>` : ''}</div>`).join('')}</div>
      <div class="chartrow"><div class="chart"><h4>How often each species is cast <span class="note">share of ${S.casts / 4 | 0} years × 4 season casts${Bs ? '; tick = baseline' : ''}</span></h4><div id="bars"></div>
      <p class="small"><button type="button" class="linkish" id="moreBars">${state.allBars ? 'Show the top 40' : `Show all ${rows.length}`}</button> · <button type="button" class="linkish" id="tblToggle">${state.tbl ? 'Hide' : 'Show'} as a table</button></p>
      ${state.tbl ? statsTable(rows) : ''}</div>
      <div class="chart"><h4>Feeding links against how often cast <span class="note">one dot per species; links in this layer's potential web</span></h4><div id="scatter"></div></div></div>`;
    drawBars(rows, S, L); drawScatter(rows, L);
  }
  function pctOf(S, f) {
    const m = Object.entries(S.seasons).filter(([t]) => !BY[t].v);
    const tot = m.reduce((a, [, v]) => a + v, 0) || 1;
    return pct(m.reduce((a, [t, v]) => a + (f(BY[t]) ? v : 0), 0) / tot);
  }
  function statsTable(rows) {
    return `<div class="tbl"><table><thead><tr><th>species</th><th>slot</th><th class="num">cast</th><th class="num">seed</th><th class="num">apex</th>${BASE ? '<th class="num">baseline</th>' : ''}</tr></thead><tbody>` +
      rows.map(r => `<tr><td>${esc(BY[r.t].nm)}</td><td>${esc(r.n ? r.n.slot : '')}</td><td class="num">${pct(r.v)}</td><td class="num">${pct(r.seed)}</td><td class="num">${pct(r.apex)}</td>${BASE ? `<td class="num">${r.b == null ? '' : pct(r.b)}</td>` : ''}</tr>`).join('') + '</tbody></table></div>';
  }
  function drawBars(rows, S, L) {
    const host = $('#bars');
    const show = state.allBars ? rows : rows.slice(0, 40);
    const w = Math.max(280, host.clientWidth), lw = Math.min(170, w * 0.36), rh = 17, h = show.length * rh + 26;
    const mx = Math.max(0.05, d3.max(show, r => Math.max(r.v, r.b || 0)));
    const x = d3.scaleLinear([0, mx], [lw, w - 40]);
    const svg = d3.select(host).html('').append('svg').attr('width', w).attr('height', h).attr('role', 'img').attr('aria-label', 'species by share of season casts');
    const ticks = x.ticks(4);
    svg.append('g').selectAll('line').data(ticks).join('line').attr('x1', d => x(d)).attr('x2', d => x(d)).attr('y1', 4).attr('y2', h - 18).attr('stroke', 'var(--line)');
    svg.append('g').selectAll('text').data(ticks).join('text').attr('x', d => x(d)).attr('y', h - 4).attr('text-anchor', 'middle').attr('class', 'axis').text(d => Math.round(d * 100) + '%');
    const g = svg.append('g').selectAll('g').data(show).join('g').attr('transform', (d, i) => `translate(0,${6 + i * rh})`).attr('class', 'barrow');
    g.append('rect').attr('x', 0).attr('y', -2).attr('width', w).attr('height', rh).attr('fill', 'transparent');
    g.append('text').attr('x', lw - 6).attr('y', 10).attr('text-anchor', 'end').attr('class', 'lab').text(d => trunc(BY[d.t].nm, 24));
    g.append('rect').attr('x', lw).attr('y', 2).attr('height', 10).attr('rx', 2).attr('width', d => Math.max(0, x(d.v) - lw))
      .attr('fill', d => `var(--${SLOT_COL[d.n ? d.n.slot : 'vermin'] || 'muted'})`);
    g.append('rect').attr('x', lw).attr('y', 5).attr('height', 4).attr('width', d => Math.max(0, x(d.seed) - lw)).attr('fill', 'var(--ink)').attr('opacity', 0.55);
    g.filter(d => d.b != null).append('line').attr('x1', d => x(d.b)).attr('x2', d => x(d.b)).attr('y1', 0).attr('y2', 14).attr('stroke', 'var(--ink)').attr('stroke-width', 2);
    g.append('text').attr('x', d => x(d.v) + 4).attr('y', 11).attr('class', 'val').text(d => pct(d.v));
    g.on('mousemove', (ev, d) => showTip(ev, `<b>${esc(BY[d.t].nm)}</b><br>cast ${pct(d.v)} · seed ${pct(d.seed)} · apex ${pct(d.apex)}${d.b != null ? '<br>baseline ' + pct(d.b) : ''}`))
      .on('mouseleave', hideTip).on('click', (ev, d) => { state.sel = d.t; state.castSel = null; renderInspector(); draw(); });
    svg.append('text').attr('x', lw).attr('y', h - 4).attr('class', 'axis').attr('text-anchor', 'start').text('');
  }
  const trunc = (s, n) => s.length > n ? s.slice(0, n - 1) + '…' : s;
  function drawScatter(rows, L) {
    const host = $('#scatter');
    const w = Math.max(260, host.clientWidth), h = 260, m = { l: 44, r: 12, t: 10, b: 34 };
    const pts = rows.filter(r => r.n && !r.n.vermin).map(r => { const A = VIEW.adj.get(r.t); return { r, d: A ? A.prey.size + A.pred.size : 0 }; });
    const x = d3.scaleLinear([0, d3.max(pts, p => p.d) || 1], [m.l, w - m.r]).nice();
    const y = d3.scaleLinear([0, d3.max(pts, p => p.r.v) || 0.05], [h - m.b, m.t]).nice();
    const svg = d3.select(host).html('').append('svg').attr('width', w).attr('height', h).attr('role', 'img').attr('aria-label', 'feeding links against share of casts');
    svg.append('g').selectAll('line').data(y.ticks(4)).join('line').attr('x1', m.l).attr('x2', w - m.r).attr('y1', d => y(d)).attr('y2', d => y(d)).attr('stroke', 'var(--line)');
    svg.append('g').selectAll('text').data(y.ticks(4)).join('text').attr('x', m.l - 6).attr('y', d => y(d) + 4).attr('text-anchor', 'end').attr('class', 'axis').text(d => Math.round(d * 100) + '%');
    svg.append('g').selectAll('text').data(x.ticks(5)).join('text').attr('x', d => x(d)).attr('y', h - m.b + 16).attr('text-anchor', 'middle').attr('class', 'axis').text(d => d);
    svg.append('text').attr('x', w - m.r).attr('y', h - 4).attr('text-anchor', 'end').attr('class', 'axis').text('feeding links (eats + eaten by)');
    svg.append('g').selectAll('circle').data(pts).join('circle').attr('cx', p => x(p.d)).attr('cy', p => y(p.r.v)).attr('r', 4.5)
      .attr('fill', p => `var(--${SLOT_COL[p.r.n.slot] || 'muted'})`).attr('stroke', 'var(--surface)').attr('stroke-width', 1.5)
      .on('mousemove', (ev, p) => showTip(ev, `<b>${esc(BY[p.r.t].nm)}</b><br>${p.d} links · cast ${pct(p.r.v)}`)).on('mouseleave', hideTip)
      .on('click', (ev, p) => { state.sel = p.r.t; state.castSel = null; renderInspector(); draw(); });
  }
  const ctip = $('#ctip');
  function showTip(ev, html) { ctip.innerHTML = html; ctip.hidden = false; ctip.style.left = (ev.clientX + 14) + 'px'; ctip.style.top = (ev.clientY + 12) + 'px'; }
  function hideTip() { ctip.hidden = true; }
  function renderYear() {
    const box = $('#year');
    if (!YEAR || !BUILD.spec) { box.innerHTML = ''; return; }
    const act = BUILD.B.active;
    const cell = (L, s) => {
      const tr = YEAR[L + '|' + s];
      if (!tr) return '<td></td>';
      const k = L + '|' + s;
      const mem = SLOTSORT(tr.members).map(m => `<li class="${m.slot === 'apex' ? 'apex' : ''}" title="${esc(m.how)}"><i style="background:var(--${SLOT_COL[m.slot] || 'muted'})"></i>${esc(BY[m.t].nm)}${tr.seed === m.t ? ' <em>seed</em>' : ''}${tr.guarantee.includes(m.t) ? ' <em>added</em>' : ''}${state.sel === m.t ? ' ◆' : ''}</li>`).join('');
      const vm = tr.vermin.map(v => esc(BY[v.t].nm)).join(', ');
      const un = Object.keys(tr.unfilled).length ? `<p class="warnline">unfilled: ${esc(Object.entries(tr.unfilled).map(([s, w]) => s + ' ' + w.split(':')[0]).join('; '))}</p>` : '';
      return `<td><button type="button" class="cast${state.castSel === k ? ' on' : ''}" data-cast="${k}" aria-pressed="${state.castSel === k}"><span class="built">built ${tr.built} of ${Object.keys(YEAR).length - 1}</span><ul>${mem}</ul><p class="verm">${vm}</p>${un}</button></td>`;
    };
    box.innerHTML = `<div class="tbl"><table class="yeargrid"><thead><tr><th>layer</th>${SEASONS.map(s => `<th>${s}</th>`).join('')}</tr></thead><tbody>` +
      act.map(L => `<tr><th scope="row">${esc(LNAME[L])}</th>${[0, 1, 2, 3].map(s => cell(L, s)).join('')}</tr>`).join('') + '</tbody></table></div>';
  }
  const SLOTSORT = ms => ms.slice().sort((a, b) => sim.SLOT_ORDER.indexOf(a.slot) - sim.SLOT_ORDER.indexOf(b.slot));
  document.addEventListener('click', ev => {
    const b = ev.target.closest('button.cast[data-cast]');
    if (b) {
      const k = b.dataset.cast;
      state.castSel = state.castSel === k ? null : k; state.sel = null;
      const L = k.split('|')[0];
      const want = CAVS.includes(L) ? 'cavern' : 'surface';
      if (state.castSel && state.tab !== want) { const keep = state.castSel; setTab(want); state.castSel = keep; }
      if (state.castSel && state.layer !== 'all' && state.layer !== L) { state.layer = L; syncControls(); refreshView(); }
      renderYear(); renderInspector(); draw();
      return;
    }
    const t = ev.target.closest('[data-sl]');
    if (t) { state.statsLayer = t.dataset.sl; renderStats(); return; }
    if (ev.target.id === 'moreBars') { state.allBars = !state.allBars; renderStats(); }
    if (ev.target.id === 'tblToggle') { state.tbl = !state.tbl; renderStats(); }
  });

  // ------------------------------------------------------------------ controls
  function seg(id, opts, cur, cb) {
    const el = $(id);
    el.innerHTML = opts.map(([v, lab]) => `<button type="button" aria-pressed="${String(v) === String(cur)}" data-v="${v}">${esc(lab)}</button>`).join('');
    el.onclick = ev => { const b = ev.target.closest('button[data-v]'); if (b) cb(b.dataset.v); };
  }
  function syncControls() {
    $('#nbiomes').innerHTML = BIOME_GROUPS.map(([g, bs]) => `<fieldset><legend>${esc(g)}</legend>` +
      bs.map(b => `<label class="ck"><input type="checkbox" id="nb_${b}" data-nb="${b}" ${state.neighbours.has(b) ? 'checked' : ''}><span>${esc(bname(b))}</span></label>`).join('') + '</fieldset>').join('');
    $('#nbCount').textContent = state.neighbours.size ? `(${state.neighbours.size} ticked; ${Object.keys(BUILD ? BUILD.B.mapOnly || {} : {}).length} map-only vermin)` : '(none ticked)';
    $('#biomes').innerHTML = BIOME_GROUPS.map(([g, bs]) => `<fieldset><legend>${esc(g)} <button type="button" class="linkish" data-grp="${esc(g)}">${bs.every(b => state.land.has(b)) ? 'none' : 'all'}</button></legend>` +
      bs.map(b => `<label class="ck"><input type="checkbox" id="b_${b}" data-b="${b}" ${state.land.has(b) ? 'checked' : ''}><span>${esc(bname(b))}</span></label>`).join('') + '</fieldset>').join('');
    renderSurroundings();
    $('#extinct').value = state.extinct; $('#iso').checked = state.iso;
    for (const k of ['ocean', 'lake', 'river', 'brook', 'pool']) $('#w_' + k).checked = state[k];
    $('#oz').value = state.oz; $('#fz').value = state.fz;
    for (const k of [1, 2, 3]) $('#cv' + k).checked = state.caverns.has(k);
    $('#assign').checked = state.assign;
    seg('#season', [['all', 'All'], [0, 'Spring'], [1, 'Summer'], [2, 'Autumn'], [3, 'Winter']], state.season, v => { state.season = v; syncControls(); refreshView(); });
    seg('#seasonBy', [['raws', "DF's raws"], ['casts', 'Built year']], state.seasonBy, v => { state.seasonBy = v; syncControls(); refreshView(); });
    $('#seasonNote').textContent = state.seasonBy === 'casts'
      ? (YEAR ? ' the built year\'s casts' + (state.season === 'all' ? ' (all four seasons)' : '') : ' build one year below first (one surroundings cell on)')
      : ' who can be on the map that season (DF\'s season tags: few species have one)';
    $('#tabs').innerHTML = [['surface', 'Surface'], ['cavern', 'Caverns']].map(([t, lab]) => {
      const n = !BUILD ? '' : Object.values(BUILD.B.P).filter(p => (p.layers || []).some(L => (t === 'cavern' ? CAVS : SURF).includes(L) && BUILD.B.active.includes(L)) && (state.vermin || !p.c.v)).length;
      return `<button type="button" role="tab" aria-selected="${state.tab === t}" data-tab="${t}">${lab} <span>${n}</span></button>`; }).join('');
    seg('#layer', [['all', state.tab === 'cavern' ? 'All caverns' : 'All surface layers']].concat((state.tab === 'cavern' ? CAVS : SURF).map(L => [L, LNAME[L]])), state.layer, v => { state.layer = v; state.sel = null; refreshView(); });
    seg('#color', [['slot', 'Trophic slot'], ['cavern', 'Cavern layer'], ['value', 'Value'], ['habitat', 'Habitat'], ['inclusion', 'How often cast']], state.color, v => { state.color = v; syncControls(); renderLegend(); draw(); });
    seg('#shape', [['level', 'Trophic level'], ['habitat', 'Habitat'], ['guild', 'Guild']], state.shape, v => { state.shape = v; syncControls(); renderLegend(); draw(); });
    seg('#lay', [['levels', 'Levels'], ['force', 'Force']], state.layout, v => { state.layout = v; syncControls(); layout(); draw(); });
    seg('#edges', [['focus', 'Selected only'], ['all', 'All']], state.edges, v => { state.edges = v; syncControls(); draw(); });
    $('#fams').innerHTML = FAM_ORDER.map(f => `<label class="ck" title="${esc(FAM[f].note)}"><input type="checkbox" id="f_${f}" data-f="${f}" ${state.fam[f] ? 'checked' : ''}><i class="ln" style="--lc:var(--${FAM[f].col})"></i>${esc(FAM[f].lab)} <span class="small">(${esc(FAM[f].def)})</span></label>`).join('');
    seg('#p_links', [['engine', 'Cast ladder (engine)'], ['network', 'Rules switched on above']], state.prm.links, v => { state.prm.links = v; syncControls(); });
    $('#verm').checked = state.vermin;
    for (const [k, id] of [['ap_pick', 'p_ap'], ['giant', 'p_gi'], ['pack', 'p_pack'], ['apex_pack', 'p_apack'], ['reuse', 'p_reuse'], ['hv_top', 'p_hv']]) $('#' + id).value = state.prm[k];
    $('#p_seed').checked = state.prm.seed; $('#p_weird').checked = state.prm.weird; $('#p_guar').checked = state.prm.guarantee;
    $('#p_years').value = state.years;
    const cap = concrete();
    $('#simNote').hidden = cap; $('#runN').disabled = !cap; $('#run1').disabled = !cap;
    const sub = (state.lake && 'lake') || ((state.river || state.brook) && (state.brook && !state.river ? 'brook (river table, small aquatic species only)' : 'river')) || (state.pool && 'murky pool') || null;
    $('#subNote').textContent = sub ? `Freshwater cast uses the ${sub} slot table (the engine builds one: lake, then river or brook, then pool).` : 'No freshwater cast.';
  }
  $('#nbiomes').addEventListener('change', ev => { const b = ev.target.dataset.nb; if (!b) return; ev.target.checked ? state.neighbours.add(b) : state.neighbours.delete(b); rebuild(); });
  $('#biomes').addEventListener('change', ev => { const b = ev.target.dataset.b; if (!b) return; ev.target.checked ? state.land.add(b) : state.land.delete(b); rebuild(); });
  $('#biomes').addEventListener('click', ev => {
    const g = ev.target.dataset.grp; if (!g) return;
    const bs = BIOME_GROUPS.find(x => x[0] === g)[1], all = bs.every(b => state.land.has(b));
    for (const b of bs) all ? state.land.delete(b) : state.land.add(b);
    syncControls(); rebuild();
  });
  $('#extinct').onchange = e => { state.extinct = e.target.value; rebuild(); };
  $('#iso').onchange = e => { state.iso = e.target.checked; rebuild(); };
  for (const k of ['ocean', 'lake', 'river', 'brook', 'pool']) $('#w_' + k).onchange = e => { state[k] = e.target.checked; rebuild(); };
  $('#oz').onchange = e => { state.oz = e.target.value; rebuild(); };
  $('#fz').onchange = e => { state.fz = e.target.value; rebuild(); };
  for (const k of [1, 2, 3]) $('#cv' + k).onchange = e => { e.target.checked ? state.caverns.add(k) : state.caverns.delete(k); rebuild(); };
  $('#assign').onchange = e => { state.assign = e.target.checked; rebuild(); };
  function setTab(t) {
    if (state.tab === t) return;
    state.tab = t; state.layer = 'all'; state.sel = null; state.castSel = null;
    state.color = t === 'cavern' ? 'cavern' : (state.color === 'cavern' ? 'slot' : state.color);
    for (const n of (VIEW ? VIEW.nodes : [])) n._lay = null;
    syncControls(); refreshView();
  }
  $('#tabs').addEventListener('click', ev => { const b = ev.target.closest('button[data-tab]'); if (b) setTab(b.dataset.tab); });
  $('#verm').onchange = e => { state.vermin = e.target.checked; renderSurroundings(); refreshView(); };
  $('#fams').addEventListener('change', ev => { const f = ev.target.dataset.f; if (!f) return; state.fam[f] = ev.target.checked; refreshView(); });
  $('#presets').onclick = ev => { const b = ev.target.closest('button[data-p]'); if (b) applyPreset(b.dataset.p); };
  const num = (id, k) => { $('#' + id).onchange = e => { const v = parseFloat(e.target.value); if (!isNaN(v) && v >= 0) state.prm[k] = v; else e.target.value = state.prm[k]; }; };
  num('p_ap', 'ap_pick'); num('p_gi', 'giant'); num('p_pack', 'pack'); num('p_apack', 'apex_pack'); num('p_reuse', 'reuse'); num('p_hv', 'hv_top');
  $('#p_seed').onchange = e => { state.prm.seed = e.target.checked; };
  $('#p_weird').onchange = e => { state.prm.weird = e.target.checked; };
  $('#p_guar').onchange = e => { state.prm.guarantee = e.target.checked; };
  $('#p_years').onchange = e => { state.years = +e.target.value; };
  $('#p_reset').onclick = () => { state.prm = Object.assign({}, sim.P0, { seed: true, weird: true, guarantee: true, links: state.prm.links }); syncControls(); };
  $('#run1').onclick = runYear;
  $('#runN').onclick = runYears;
  $('#pin').onclick = () => { if (STATS) { BASE = STATS; $('#pinState').textContent = `Baseline: ${STATS.n} years, ${prmText(STATS.prm)}`; renderStats(); } };
  // live search (user 17 Oct): every keystroke lights the creatures whose name or token holds the text; Enter selects the
  // best match; Escape clears
  function searchHits() {
    const q = state.search;
    if (!q || !VIEW) return null;
    const hits = new Set();
    for (const n of VIEW.nodes) if (n.c.nm.toLowerCase().includes(q) || n.t.toLowerCase().includes(q)) hits.add(n.t);
    return hits;
  }
  function searchNote() {
    const Q = searchHits();
    $('#searchNote').textContent = !Q ? '' : (Q.size ? `${Q.size} match${Q.size === 1 ? '' : 'es'} lit${Q.size > 60 ? ' (labels shown for 60 or fewer)' : ''}; Enter selects the first, Esc clears.`
      : 'No creature in this view matches: widen the fort or pick All layers.');
  }
  $('#search').addEventListener('input', e => { state.search = e.target.value.trim().toLowerCase(); searchNote(); draw(); });
  $('#search').addEventListener('keydown', e => {
    if (e.key === 'Escape') { e.target.value = ''; state.search = ''; searchNote(); draw(); return; }
    if (e.key !== 'Enter') return;
    const q = state.search; if (!q) return;
    const n = VIEW.nodes.find(n => n.c.nm.toLowerCase() === q || n.t.toLowerCase() === q) || VIEW.nodes.find(n => n.c.nm.toLowerCase().includes(q) || n.t.toLowerCase().includes(q));
    if (n) { state.sel = n.t; state.castSel = null; e.target.value = ''; state.search = ''; searchNote(); renderInspector(); renderYear(); draw(); }
  });
  const dl = $('#names');

  // ------------------------------------------------------------------ rebuild chain
  function rebuild(keepView) {
    BUILD = buildAll();
    BUILD.key = fortKey() + [...state.cells].sort().join(',');
    YEAR = null; state.castSel = null;
    syncControls();
    refreshView();
    renderYear();
    const nP = Object.keys(BUILD.B.P).length;
    const PV = Object.values(BUILD.B.P), onS = p => p.layers.some(L => SURF.includes(L)), onC = p => p.layers.some(L => CAVS.includes(L));
    const nS = PV.filter(onS).length, nC = PV.filter(onC).length, nB = PV.filter(p => onS(p) && onC(p)).length, nN = PV.filter(p => !p.layers.length).length;
    const split = ` (${nS} on the surface layers, ${nC} in the caverns${nB ? `, ${nB} of them on both` : ''}${nN ? `, ${nN} placed plant${nN === 1 ? '' : 's'} with no layer` : ''})`;
    $('#fortline').textContent = `${nP} species and vermin${nP ? split : ''} pass the gates on ${state.land.size} land biome${state.land.size === 1 ? '' : 's'} in ${state.cells.size === 9 ? 'all nine surroundings' : (state.cells.size ? [...state.cells].map(c => CELLNAME[c]).join(', ') : 'no surroundings (switch a cell on)')}; active layers: ${BUILD.B.active.map(L => LNAME[L]).join(', ') || 'none'}.`;
    if (concrete() && !keepView) { /* stats stay until the next run */ }
    renderStats();
  }
  function refreshView() {
    makeView(); layout(); transform = d3.zoomIdentity; d3.select(canvas).call(zoom.transform, transform);
    dl.innerHTML = VIEW.nodes.map(n => `<option value="${esc(n.c.nm)}">`).join('');
    if (state.sel && !VIEW.byT[state.sel]) state.sel = null;
    state.selEdge = null; $('#edgepop').hidden = true;
    searchNote();
    renderLegend(); renderInspector(); draw();
  }
  function boot() {
    readTokens(); resize(); bindZoom();
    syncControls(); rebuild(true);
    runYear(); runYears();
  }
  const mq = window.matchMedia('(prefers-color-scheme: dark)');
  mq.addEventListener('change', () => { readTokens(); draw(); });
  new MutationObserver(() => { readTokens(); draw(); }).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  let rz; window.addEventListener('resize', () => { clearTimeout(rz); rz = setTimeout(() => { const w0 = W; resize(); bindZoom(); if (Math.abs(W - w0) > 20) { layout(); } draw(); if (STATS) renderStats(); }, 150); });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => draw());
  boot();
})();
