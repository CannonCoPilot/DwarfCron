#!/usr/bin/env python3
"""castsim.report: the Cast Pipeline Trace page from data/castsim/castsim.json (run.py) -> data/castsim/cast-pipeline.html"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/castsim/castsim.json'
OUT = ROOT / 'data/castsim/cast-pipeline.html'

# what the engine printed on the rig on 9 Oct (cast show / cast status, v7.4-onebuilder), the simulation's check
RIG = [
    ('lake', 'Spring', 'land', 'pool', 31), ('lake', 'Spring', 'water', 'pool', 22), ('lake', 'Spring', 'cavern', 'pool', 34),
    ('ocean', 'Summer', 'land', 'pool', 22), ('ocean', 'Summer', 'water', 'pool', 46), ('ocean', 'Summer', 'cavern', 'pool', 41),
    ('ocean', 'Summer', 'water', 'apex', 'SPERM_WHALE; to meso ORCA, SHARK_GREAT_WHITE, SHARK_HAMMERHEAD, SHARK_BLUE, SHARK_MAKO_LONGFIN, SHARK_MAKO_SHORTFIN'),
    ('ocean', 'Summer', 'cavern', 'apex', 'CAVE_DRAGON; to meso BLIND_CAVE_OGRE, JABBERER, VORACIOUS_CAVE_CRAWLER, CROCODILE_CAVE, TROLL, BLIND_CAVE_BEAR, OLM_GIANT, SPIDER_CAVE_GIANT'),
    ('lake', 'Spring', 'land', 'seed high value', 'KANGAROO (pet 100, size 90,000)'),
    ('lake', 'Spring', 'cavern', 'seed high value', 'SPIDER_CAVE_GIANT (pet 2,500)'),
]


def validation(data):
    by = {d['id']: d for d in data}
    rows = []
    for ex, season, layer, what, rig in RIG:
        tr = by[ex]['casts'][f'{layer}|{season}']
        if what == 'pool':
            sim = len(tr['candidates'])
            ok = 'match' if sim == rig else ('close' if abs(sim - rig) <= 2 else 'wider')
        elif what == 'apex':
            ar = tr['apex_rank']
            meso = [t for t, m, r in ar['ranked'] if r == 'meso'][:len(rig.split('meso ')[1].split(', '))]
            sim = f"{ar['apex']}; to meso " + ', '.join(meso)
            ok = 'match' if sim == rig else 'differs'
        else:
            tok = rig.split(' ')[0]
            w = tr['high_value']['flagged'].get(tok)
            sim = f'{tok} ({w})' if w else f'{tok} not high value'
            ok = 'match' if w and w.replace(',', '') in rig.replace(',', '').replace('(', '').replace(')', '') or (w and tok in rig) else 'differs'
        rows.append({'ex': by[ex]['name'], 'season': season, 'layer': layer, 'what': what, 'rig': rig, 'sim': sim, 'ok': ok})
    return rows


def slim(data):
    """the fields the page shows"""
    out = []
    for d in data:
        casts = {}
        for k, tr in d['casts'].items():
            casts[k] = {x: tr.get(x) for x in ('candidates', 'not_in_layer', 'out_of_season', 'vermin_out_of_season', 'apex_rank', 'web_edges',
                                               'excluded', 'high_value', 'seed_pool', 'seed_blocked', 'seed', 'seed_why', 'log', 'members',
                                               'slots', 'unfilled', 'vermin', 'eligible_vermin', 'edges')}
        out.append({k: d[k] for k in ('id', 'name', 'kind', 'source', 'entries', 'n_entries', 'filter', 'biomes', 'parts', 'roster')}
                   | {'pool': d['pool'], 'casts': casts})
    return out


CSS = r"""
:root{--bg:#eef1ee;--surface:#ffffff;--sunk:#e3e8e4;--ink:#1b2522;--muted:#5b6963;--line:#cfd8d2;--accent:#2f6b52;--accent-ink:#ffffff;
--land:#8a6a2b;--land-bg:#f3ead6;--water:#2a6688;--water-bg:#deebf3;--cavern:#6a4f8a;--cavern-bg:#ebe4f3;
--ok:#2f7a4a;--ok-bg:#e0f0e5;--warn:#9a6a12;--warn-bg:#f6ecd3;--bad:#a2402e;--bad-bg:#f6e2dc;
--serif:"Bitter",Georgia,serif;--sans:"Atkinson Hyperlegible",system-ui,sans-serif;--mono:"JetBrains Mono",ui-monospace,Menlo,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#121816;--surface:#1a211e;--sunk:#222b27;--ink:#e1e8e3;--muted:#98a69f;--line:#2e3a35;--accent:#7fb79a;--accent-ink:#0f1512;
--land:#d8b46a;--land-bg:#2e2617;--water:#7fb2d4;--water-bg:#172734;--cavern:#b9a2dc;--cavern-bg:#251e31;--ok:#8fd0a6;--ok-bg:#1d3326;--warn:#e2b765;--warn-bg:#382d17;--bad:#ee9a86;--bad-bg:#3b231e}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#121816;--surface:#1a211e;--sunk:#222b27;--ink:#e1e8e3;--muted:#98a69f;--line:#2e3a35;--accent:#7fb79a;--accent-ink:#0f1512;
--land:#d8b46a;--land-bg:#2e2617;--water:#7fb2d4;--water-bg:#172734;--cavern:#b9a2dc;--cavern-bg:#251e31;--ok:#8fd0a6;--ok-bg:#1d3326;--warn:#e2b765;--warn-bg:#382d17;--bad:#ee9a86;--bad-bg:#3b231e}
body{background:var(--bg);color:var(--ink);font:15px/1.55 var(--sans)}
.wrap{max-width:1120px;margin:0 auto;padding-inline:20px;padding-block:28px 72px}
h1,h2,h3,h4{font-family:var(--serif);margin:0;text-wrap:balance}
h1{font-size:2rem;letter-spacing:-.01em}h2{font-size:1.4rem;margin-block:44px 12px;padding-top:12px;border-top:1px solid var(--line)}
h3{font-size:1.08rem;margin-block:22px 8px}h4{font-size:.95rem;margin-block:14px 6px}
p{margin:0 0 10px;max-width:72ch}.lede p{color:var(--muted)}
.eyebrow{font:600 .72rem var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
code,.mono{font-family:var(--mono);font-size:.86em}
.flow{list-style:none;padding:0;margin:14px 0 0;display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px;counter-reset:s}
.flow li{counter-increment:s;background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:10px 12px 10px 42px;position:relative;font-size:.9rem}
.flow li::before{content:counter(s);position:absolute;left:12px;top:9px;font:700 1rem var(--serif);color:var(--accent)}
.flow b{display:block;font-family:var(--serif)}.flow span{color:var(--muted);font-size:.84rem}
.tbl{overflow-x:auto;margin-block:6px 12px;border:1px solid var(--line);border-radius:6px;background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:.86rem;font-variant-numeric:tabular-nums}
th,td{padding:5px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{font:600 .7rem var(--mono);text-transform:uppercase;letter-spacing:.04em;color:var(--muted);background:var(--sunk);position:sticky;top:0}
tr:last-child td{border-bottom:0}td.num{text-align:right}
.chip{display:inline-block;font:600 .68rem var(--mono);padding:1px 7px;border-radius:999px;white-space:nowrap;margin:1px 2px 1px 0}
.chip.ok{color:var(--ok);background:var(--ok-bg)}.chip.warn{color:var(--warn);background:var(--warn-bg)}.chip.bad{color:var(--bad);background:var(--bad-bg)}
.chip.land{color:var(--land);background:var(--land-bg)}.chip.water{color:var(--water);background:var(--water-bg)}.chip.cavern{color:var(--cavern);background:var(--cavern-bg)}
.chip.flag{color:var(--muted);background:var(--sunk)}
.sp{display:inline-block;font-family:var(--mono);font-size:.78rem;background:var(--sunk);border-radius:4px;padding:1px 6px;margin:2px 3px 2px 0}
.sp.apex{background:var(--bad-bg);color:var(--bad)}.sp.meso{background:var(--warn-bg);color:var(--warn)}.sp.seed{outline:2px solid var(--accent)}
.controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-block:10px 4px}
.controls label{font:600 .72rem var(--mono);text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.seg{display:inline-flex;flex-wrap:wrap;border:1px solid var(--line);border-radius:6px;overflow:hidden;background:var(--surface)}
.seg button{font:inherit;font-size:.86rem;border:0;background:none;color:var(--ink);padding:6px 11px;cursor:pointer;border-right:1px solid var(--line)}
.seg button:last-child{border-right:0}.seg button[aria-pressed="true"]{background:var(--accent);color:var(--accent-ink)}
.seg button:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.steps{display:grid;gap:12px;margin-top:12px}
.step{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:14px 16px}
.step>header{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}.step>header .n{font:700 1.05rem var(--serif);color:var(--accent);min-width:1.6em}
.step>header h4{margin:0;flex:1 1 260px}.step .why{color:var(--muted);font-size:.86rem;margin:6px 0 8px;max-width:80ch}
.kv{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px;margin:8px 0}
.kv div{background:var(--sunk);border-radius:6px;padding:8px 10px}.kv b{display:block;font:700 1.2rem var(--serif)}.kv span{font-size:.78rem;color:var(--muted)}
details{margin-top:6px}summary{cursor:pointer;color:var(--accent);font-weight:700;font-size:.9rem}
ol.log{margin:4px 0 0;padding-left:1.4rem;font-family:var(--mono);font-size:.8rem;columns:2 320px}ol.log li{break-inside:avoid;margin-bottom:2px}
.note{font-size:.84rem;color:var(--muted)}
.bar{display:inline-block;height:8px;background:var(--accent);border-radius:2px;vertical-align:middle;margin-right:6px}
@media (max-width:560px){.flow{grid-template-columns:1fr}h1{font-size:1.6rem}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
"""

JS = r"""
const D = JSON.parse(document.getElementById('data').textContent);
const SEASONS=['Spring','Summer','Autumn','Winter'], LAYERS=['land','water','cavern'];
const state={ex:D[0].id, layer:'land', season:'Spring'};
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fmt=n=>(n==null?'-':Number(n).toLocaleString('en-US'));
const chips=(arr,cls='')=>arr.map(t=>`<span class="sp ${cls}">${esc(t)}</span>`).join('');
function seg(id,items,cur,label){return `<label for="${id}">${label}</label><div class="seg" id="${id}" role="group">`+items.map(([v,t])=>`<button type="button" data-v="${esc(v)}" aria-pressed="${v===cur}">${esc(t)}</button>`).join('')+'</div>';}
function step(n,title,why,body){return `<section class="step"><header><span class="n">${n}</span><h4>${title}</h4></header>${why?`<p class="why">${why}</p>`:''}${body}</section>`;}
function poolTable(ex){
  const rows=ex.pool.filter(p=>p.cat!=='vermin');
  const flags=p=>[p.lp&&'LARGE_PREDATOR',p.benign&&'BENIGN',p.giant&&'giant',p.ap&&'animal person',p.civ&&'civ race',p.savage&&'SAVAGE',p.extinct&&'extinct',p.locked&&('locked: '+p.eco),p.fixes.length&&('fixed: '+p.fixes.join(' '))].filter(Boolean).map(f=>`<span class="chip ${String(f).startsWith('locked')?'bad':'flag'}">${esc(f)}</span>`).join('');
  return `<div class="tbl" style="max-height:440px"><table><thead><tr><th>species (pool key)</th><th>layer</th><th>guild</th><th>habitat</th><th>role</th><th class="num">adult cm³</th><th class="num">pet</th><th>war</th><th>seasons</th><th>depth</th><th>flags</th></tr></thead><tbody>`+
   rows.map(p=>`<tr><td class="mono">${esc(p.key)}</td><td><span class="chip ${p.layer}">${p.layer}</span></td><td class="mono">${p.guild}</td><td>${p.habitat}</td><td>${p.role}</td><td class="num">${fmt(p.mass)}</td><td class="num">${fmt(p.pet)}</td><td>${p.war?'yes':''}</td><td class="mono">${p.seasons}</td><td class="mono">${p.depths.length?p.depths.join(','):''}</td><td>${flags(p)}</td></tr>`).join('')+'</tbody></table></div>';
}
function render(){
  const ex=D.find(d=>d.id===state.ex), key=state.layer+'|'+state.season, tr=ex.casts[key];
  const nv=ex.pool.filter(p=>p.cat==='vermin').length, na=ex.pool.length-nv;
  const ent=Object.entries(ex.entries).map(([k,n])=>{const [l,t]=k.split('|');return `<tr><td><span class="chip ${l==='deep'?'flag':l}">${l}</span></td><td>${t}</td><td class="num">${fmt(n)}</td></tr>`}).join('');
  const f=ex.filter;
  let h='';
  h+=step(1,'DF stocks the embark: population entries', `DF's worldgen gives every region tile its populations. ${ex.kind==='real'?'This is the real list the rig saved for this fort.':'Synthetic: stocked from the raws by the rule in the method notes.'} Region biomes from who lives here: ${ex.biomes.map(b=>b[0]).slice(0,4).map(esc).join(', ')}.`,
    `<div class="kv"><div><b>${fmt(ex.n_entries)}</b><span>population entries</span></div><div><b>${na}</b><span>species keys, non-vermin</span></div><div><b>${nv}</b><span>vermin keys</span></div></div><div class="tbl"><table><thead><tr><th>layer</th><th>type</th><th class="num">entries</th></tr></thead><tbody>${ent}</tbody></table></div><p class="note">${esc(ex.source)}</p>`);
  h+=step(2,'The tool keeps the entries it manages', 'managedPop: creature populations only, on this embark\'s region tiles, never an uncountable cloud (INNUMERABLE), never the deep layer (R60). One pool entry per species and layer (keyFor: TOKEN, water:TOKEN, cavern:TOKEN).',
    `<p><b>Left out:</b> ${f.innumerable.length} uncountable ${chips(f.innumerable.slice(0,14))}${f.innumerable.length>14?' …':''}</p><p><b>Deep layer:</b> ${f.deep.length?chips(f.deep):'none'}</p>`);
  h+=step(3,'Each species is classified from its raws', 'classify: habitat, role, guild, adult size, pet value, training, seasons (NO_<season> on every caste), raw cavern depth, giant, animal person, civ race, and the ecology class (only natural species can be managed; the rest are locked). Extinct species get the tool\'s 83 corrections.',
    `<details><summary>The ${na} non-vermin species of this pool</summary>${poolTable(ex)}</details>`);
  const partRows=['land','flying','water','cavern'].map(p=>{const P=ex.parts[p];const outs=Object.entries(P.out);return `<tr><td><b>${p}</b></td><td class="num">${P.in.length}</td><td>${chips(P.in)}</td><td>${outs.length?outs.slice(0,40).map(([t,w])=>`<span class="sp" title="${esc(w)}">${esc(t)}</span><span class="note">${esc(w)}</span> `).join(''):'<span class="note">none</span>'}</td></tr>`}).join('');
  h+=step(4,'Species are split into roster partitions', 'ROSTER.inPart: land (walks), flying (flies), water (water entries, aquatic animals from land entries, curated water apexes), cavern (cavern entries inside their raw depth range, never lava-only). The land cast merges land and flying.',
    `<div class="tbl"><table><thead><tr><th>partition</th><th class="num">in</th><th>species</th><th>left out, and why</th></tr></thead><tbody>${partRows}</tbody></table></div>`);
  h+=`<h3>One cast, step by step</h3><div class="controls">${seg('layerSeg',LAYERS.map(l=>[l,l]),state.layer,'Layer')}${seg('seasonSeg',SEASONS.map(s=>[s,s]),state.season,'Season')}</div>`;
  const notIn=Object.entries(tr.not_in_layer||{});
  h+=step(5,`Season filter: who ${state.season} allows on the ${state.layer} layer`, 'ROSTER.castPool: a species whose raws carry NO_'+state.season.toUpperCase()+' on every caste is out this season. Species with no season flags are in all four.',
    `<p><b>Out this season:</b> ${tr.out_of_season.length?chips(tr.out_of_season):'none'} ${tr.vermin_out_of_season.length?'<br><b>Vermin out:</b> '+chips(tr.vermin_out_of_season):''}</p>`);
  const bySlot={};tr.candidates.forEach(([t,code,slot,g])=>{const k=slot||(g.startsWith('vermin')?'vermin':'no slot ('+code+')');(bySlot[k]=bySlot[k]||[]).push([t,code,g])});
  h+=step(6,`Candidates and their trophic slots (${tr.candidates.length})`, 'ROSTER.castSlot: each candidate\'s guild maps to a slot code (slotOf: LARGE_PREDATOR guilds and boosted giants to APX, a flying apex to the raptor slot, curated water apexes to APX/APE, R49 demotes other water predators to MW, civ races never apex). The code picks the cast slot.',
    `<div class="tbl"><table><thead><tr><th>slot</th><th>candidates (slot code)</th></tr></thead><tbody>${Object.entries(bySlot).map(([s,l])=>`<tr><td><b>${esc(s)}</b></td><td>${l.map(([t,c])=>`<span class="sp">${esc(t)} <span class="note">${esc(c)}</span></span>`).join('')}</td></tr>`).join('')}</tbody></table></div>`);
  const ar=tr.apex_rank;
  h+=step(7,'Apex ranking (the mix)', 'v7.4: the flagged predators (APX/APE) are ranked by adult size; the largest keeps the apex slot and the rest move to meso. With none flagged, the largest non-sentient mesopredator is promoted.',
    `<p><b>Rule used:</b> ${esc(ar.rule)}. <b>Apex:</b> ${ar.apex?`<span class="sp apex">${esc(ar.apex)}</span>`:'none'}</p>${ar.ranked.length?`<div class="tbl"><table><thead><tr><th>#</th><th>species</th><th class="num">adult cm³</th><th>result</th></tr></thead><tbody>${ar.ranked.map(([t,m,r],i)=>`<tr><td>${i+1}</td><td class="mono">${esc(t)}</td><td class="num">${fmt(m)}</td><td><span class="chip ${r==='apex'?'bad':'warn'}">${r}</span></td></tr>`).join('')}</tbody></table></div>`:''}`);
  const ex2=Object.entries(tr.excluded||{});
  h+=step(8,'The food web, and who can never be cast', 'ROSTER.castEats: A eats B when A\'s tier is higher, MODEL.reaches lets it get at B (realm, habitat reach, shared water) and they share a cavern depth; vermin go to the predators whose diet takes their class. castExcluded then drops every species with no slot, or with no prey and no predator left that could be cast (repeated until stable).',
    `<div class="kv"><div><b>${fmt(tr.web_edges)}</b><span>predator→prey edges among the candidates</span></div><div><b>${ex2.length}</b><span>never castable this season</span></div></div>${ex2.length?ex2.map(([t,w])=>`<span class="sp">${esc(t)}</span><span class="note">${esc(w)}</span> `).join(''):''}`);
  const hv=tr.high_value;
  h+=step(9,'High-value species and the seed', `ROSTER.hvSet: among this layer-season's ${hv.n} non-vermin candidates, high value is war-trainable, or the top ${hv.k} (10%, by rank) by pet value (a giant reads its root animal's), or the top ${hv.k} by adult size. The seed is a weighted pick among the high-value ones that can be cast and are not sentient (pack hunters x3, x0.1 for each other cast the species is already on, giants x0.2).`,
    `<div class="tbl"><table><thead><tr><th>pet value rank</th><th>size rank</th></tr></thead><tbody><tr><td>${hv.pet_rank.map(([t,v])=>`<span class="sp">${esc(t)} <span class="note">${fmt(v)}</span></span>`).join('')}</td><td>${hv.size_rank.map(([t,v])=>`<span class="sp">${esc(t)} <span class="note">${fmt(v)}</span></span>`).join('')}</td></tr></tbody></table></div>
     <p><b>High value:</b> ${Object.entries(hv.flagged).map(([t,w])=>`<span class="sp">${esc(t)}</span><span class="note">${esc(w)}</span> `).join('')||'none'}</p>
     <p><b>Seed candidates (weight):</b> ${tr.seed_pool.length?tr.seed_pool.map(([t,w])=>`<span class="sp">${esc(t)} <span class="note">${w}</span></span>`).join(''):'none: any castable species'}${tr.seed_blocked.length?`<br><b>High value but not a seed</b> (sentient or never castable): ${chips(tr.seed_blocked)}`:''}</p>
     <p><b>Seed picked:</b> <span class="sp seed">${esc(tr.seed||'none')}</span> <span class="note">${esc(tr.seed_why||'')}</span></p>`);
  h+=step(10,`Growing the cast (${tr.log.length} additions)`, 'ROSTER.castGrow: take a random cast member, list its prey and predators whose slot still has room, keep those in the emptiest slot, make a weighted pick, add it; a member with nothing left to add is set aside. Stop when every slot is full or every member is set aside.',
    tr.log.length?`<ol class="log">${tr.log.map(([a,b,s,w])=>`<li>${esc(a)} → <b>${esc(b)}</b> <span class="note">${esc(s)}, ${esc(w)}</span></li>`).join('')}</ol>`:'<p class="note">The seed alone.</p>');
  h+=step(11,'Vermin for the cast', `The vermin the members eat (${tr.eligible_vermin} eligible), one per class first, then the most-eaten, up to the layer's count.`,
    tr.vermin.length?tr.vermin.map(([t,c,n])=>`<span class="sp">${esc(t)} <span class="note">${c}, ${n} eater(s)</span></span>`).join(''):'<p class="note">none</p>');
  const slots=Object.entries(tr.slots||{}), un=tr.unfilled||{};
  h+=step(12,`The ${state.season} ${state.layer} cast`, 'Every slot with its members; an unfilled slot says why. These species are the season\'s roster on this layer; every other managed species rests.',
    `<div class="tbl"><table><thead><tr><th>slot</th><th>members</th><th>unfilled</th></tr></thead><tbody>${slots.map(([s,l])=>`<tr><td><b>${esc(s)}</b></td><td>${l.map(t=>`<span class="sp ${t===tr.seed?'seed':''} ${t===ar.apex?'apex':''}">${esc(t)}</span>`).join('')||'<span class="note">-</span>'}</td><td class="note">${esc(un[s]||'')}</td></tr>`).join('')}</tbody></table></div>
     <details><summary>${(tr.edges||[]).length} food-web edges in this cast</summary><p class="mono" style="font-size:.78rem">${(tr.edges||[]).map(([a,b])=>esc(a)+'→'+esc(b)).join(' · ')}</p></details>`);
  const rc=Object.entries(ex.roster.cast).sort();
  h+=`<h3>The year's roster</h3>`+step(13,`${rc.length} species cast, ${ex.roster.resting.length} resting`, 'ROSTER.castYear: a species cast in any season is active in exactly those seasons; every other species the cast layers manage rests (no season, never on the map). Built once at enable and kept.',
    `<details><summary>Species by season</summary><div class="tbl" style="max-height:420px"><table><thead><tr><th>species (pool key)</th>${SEASONS.map(s=>`<th>${s}</th>`).join('')}</tr></thead><tbody>${rc.map(([k,ss])=>`<tr><td class="mono">${esc(k)}</td>${SEASONS.map(s=>`<td>${ss.includes(s)?'●':''}</td>`).join('')}</tr>`).join('')}</tbody></table></div></details>
     <details><summary>Resting species</summary><p>${chips(ex.roster.resting)}</p></details>`);
  const lad=Object.entries(ex.roster.ladder);
  h+=step(14,'The FREQUENCY ladder', 'ROSTER.castLadder: per partition, each cast member\'s raw FREQUENCY is rewritten so arrivals follow the pyramid (herbivore and carnivore unit shares), with the biomass guard (carnivore biomass at most half the herbivores\') on land and in caverns. Apexes keep their raw FREQUENCY, capped at 5; the apex scheduler places them.',
    lad.map(([p,l])=>`<h4>${esc(p)} <span class="note">target ${esc(l.target)}; herbivores ${l.herb_share}, carnivores ${l.carn_share}; binding: ${esc(l.binding)}</span></h4><div class="tbl"><table><tbody>${Object.entries(l.odds).map(([t,v])=>`<tr><td class="mono">${esc(t)}</td><td style="width:60%"><span class="bar" style="width:${v*0.6}%"></span>${v}</td></tr>`).join('')}${Object.entries(l.apex_odds).map(([t,v])=>`<tr><td class="mono">${esc(t)}</td><td><span class="chip bad">apex</span> raw FREQUENCY ${v}</td></tr>`).join('')}</tbody></table></div>`).join(''));
  document.getElementById('steps').innerHTML=h;
  document.querySelectorAll('#layerSeg button').forEach(b=>b.onclick=()=>{state.layer=b.dataset.v;render()});
  document.querySelectorAll('#seasonSeg button').forEach(b=>b.onclick=()=>{state.season=b.dataset.v;render()});
  document.querySelectorAll('#exSeg button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.v===state.ex));
}
document.getElementById('exPick').innerHTML=seg('exSeg',D.map(d=>[d.id,d.name.split(' (')[0]]),state.ex,'Embark');
document.querySelectorAll('#exSeg button').forEach(b=>b.onclick=()=>{state.ex=b.dataset.v;render()});
render();
"""


def apex_summary(data):
    rows = []
    for d in data:
        for layer in ('land', 'water', 'cavern'):
            ar = d['casts'][f'{layer}|Summer']['apex_rank']
            meso = [t for t, m, r in ar['ranked'] if r == 'meso']
            rows.append((d['name'].split(' (')[0], layer, ar['apex'], ar['rule'], meso, {t: m for t, m, r in ar['ranked']}))
    return rows


def main():
    data = json.loads(DATA.read_text())
    val = validation(data)
    s = slim(data)
    blob = json.dumps(s, separators=(',', ':')).replace('</', '<\\/')
    def vrow(r):
        cls = {'match': 'ok', 'close': 'warn'}.get(r['ok'], 'bad')
        return (f"<tr><td>{r['ex']}</td><td>{r['season']} {r['layer']}</td><td>{r['what']}</td><td class='mono'>{r['rig']}</td>"
                f"<td class='mono'>{r['sim']}</td><td><span class='chip {cls}'>{r['ok']}</span></td></tr>")
    def arow(r):
        name, layer, apex, rule, meso, mass = r
        return (f"<tr><td>{name}</td><td><span class='chip {layer}'>{layer}</span></td><td><span class='sp apex'>{apex or 'none'}</span>"
                f"<span class='note'>{mass.get(apex, 0):,} cm³</span></td><td>{''.join(f'<span class=sp>{t}</span>' for t in meso[:10]) or '<span class=note>-</span>'}"
                f"{' …' if len(meso) > 10 else ''}</td><td class='note'>{rule}</td></tr>")
    html = f"""<title>Cast Pipeline Trace</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bitter:wght@500;700&family=Atkinson+Hyperlegible:wght@400;700&family=JetBrains+Mono:wght@400;600&display=swap">
<style>{CSS}</style>
<div class="wrap">
<section class="lede">
  <span class="eyebrow">Seasonal Wildlife v7.4 · desk simulation · 9 Oct 2026</span>
  <h1>Cast Pipeline Trace</h1>
  <p>How the tool turns the creatures DF stocked on an embark into its year of season casts, shown step by step on five embarks:
  three real forts from the rig (their saved population lists) and two synthetic ones stocked from DF's raws. Nothing here ran DF.
  The rules are the engine's own (v7.4-onebuilder cd08293); the constant tables were read out of the engine.</p>
</section>

<h2>The pipeline</h2>
<ol class="flow">
<li><b>DF stocks the embark</b><span>population entries per region tile, by biome</span></li>
<li><b>Managed entries</b><span>creatures on this embark; no clouds, no deep layer</span></li>
<li><b>Classify</b><span>guild, habitat, size, pet value, seasons, locks</span></li>
<li><b>Partition</b><span>land, flying, water, cavern</span></li>
<li><b>Season filter</b><span>NO_&lt;season&gt; on every caste</span></li>
<li><b>Slot codes</b><span>guild to trophic slot</span></li>
<li><b>Apex ranking</b><span>largest flagged predator keeps apex</span></li>
<li><b>Food web</b><span>tier, reach, shared depth; never-castable dropped</span></li>
<li><b>High value and seed</b><span>war, top 10% pet value or size</span></li>
<li><b>Growth</b><span>prey and predators into the emptiest slot</span></li>
<li><b>Vermin</b><span>what the members eat</span></li>
<li><b>The cast</b><span>the season's roster on the layer</span></li>
<li><b>The year's roster</b><span>active in cast seasons, the rest resting</span></li>
<li><b>Ladder</b><span>FREQUENCY toward the pyramid</span></li>
</ol>

<h2>The apex, embark by embark</h2>
<p>Your open question. The summer cast of each layer, under the size-ranked mix now in the engine. The red name is the apex; the rest of the
flagged predators were moved to meso, largest first.</p>
<div class="tbl"><table><thead><tr><th>embark</th><th>layer</th><th>apex</th><th>moved to meso</th><th>rule</th></tr></thead><tbody>
{''.join(arow(r) for r in apex_summary(data))}
</tbody></table></div>
<h3>What the five embarks show</h3>
<ul class="note" style="max-width:80ch;display:grid;gap:6px;padding-left:1.2rem">
<li><b>Size alone puts the sperm whale over orcas and great whites</b> on both coasts (25,000,000 cm³ against 5,000,000). It is curated as a pelagic apex and it is the largest; nothing in the ranking knows that orcas hunt in pods.</li>
<li><b>A layer with no flagged predator promotes a small one.</b> The lake fort's land layer has no LARGE_PREDATOR species, so the largest mesopredator, a 7,000 cm³ rattlesnake, becomes the apex. The taiga's is a 20,000 cm³ wolverine (badger, fox and stoat below it).</li>
<li><b>The cavern apex is stable</b>: the cave dragon on every real fort, the blind cave ogre where no dragon was stocked. Everything below it, trolls included, goes to meso.</li>
<li><b>One species can sit in a cast twice.</b> On the brook fort the alligator is a water-layer entry and, through its land entry, a curated water apex; the cast keeps one candidate per pool key, not per species, so both enter the ranking (apex and meso). Vermin are already kept to one per species; the same rule should cover the rest. This is a defect in the engine, not in the simulation.</li>
<li><b>Savage embarks bring DF's extinct and animal-people predators.</b> On the savage forest the apex is an extinct theropod (Jurassic torvosaurus) with allosaurus, megalania, smilodon and two animal people ranked below it.</li>
<li><b>Small land pools seed the same species every season</b> (kangaroo on the lake fort, dingo on the brook fort): the season filter changes almost nothing there, and the top-10% cut is one species.</li>
</ul>

<h2>Does the simulation match the engine?</h2>
<p>What the engine printed on the rig for the lake and ocean forts (cast show, 9 Oct), against the simulation on the same population lists.
Steps that involve no random draw can match exactly; the seed and growth draws use another generator, so the members of a simulated cast are one
possible cast, not the rig's.</p>
<div class="tbl"><table><thead><tr><th>embark</th><th>cast</th><th>what</th><th>rig</th><th>simulation</th><th></th></tr></thead><tbody>
{''.join(vrow(r) for r in val)}
</tbody></table></div>
<p class="note">Cavern pools and both apex rankings match exactly. Surface pools differ by the region scope: the saved list holds every entry within one
world tile of the embark, while the engine reads a surface entry only on the tiles its map blocks name. Land entries are trimmed to the engine's own
list (the tool's snapshot); water-body entries (lakes, rivers) cannot be trimmed from the saved list, so the lake and brook water pools include a few
species from neighbouring tiles' water. With a larger pool the top-10% cut takes one more species, which is why the crocodile's high-value reason reads
"pet 700" here and "pet 700, size 800000" on the rig.</p>

<h2>Step through an embark</h2>
<div class="controls" id="exPick"></div>
<div class="steps" id="steps"></div>

<h2>Method notes</h2>
<p><b>Raws.</b> DF 53.16's vanilla and extinct creature files, compiled as DF compiles them: COPY_TAGS_FROM, the GIANT and ANIMAL_PERSON variations
(tags removed and added), castes, DF's derived flags (GRAZER, TRAINABLE_WAR, CANNOT_BREATHE_AIR, CAN_BREATHE_WATER) and the aggregate biome tokens
expanded. CV_CONVERT_TAG is not applied; it renames body and attack tokens the tool does not read.</p>
<p><b>Real embarks.</b> The population lists sw-state-check saved at the start of X3 on v7.4 (lake, ocean, brook forts on region19). A cave entry's cavern
is not in the list, so a cavern species' depths are its raw UNDERGROUND_DEPTH range within the three caverns.</p>
<p><b>Synthetic embarks.</b> DF's worldgen approximated: every natural creature whose BIOME admits one of the embark's biomes is a candidate (SAVAGE and
animal people only on a savage region, GOOD/EVIL only on an aligned one); it is stocked with odds that follow its FREQUENCY (50 is an even chance);
sea life rides land-layer entries, lakes and rivers stock water-feature entries, caverns stock SUBTERRANEAN species by raw depth. The savage embark
therefore carries DF's extinct species, which are SAVAGE in the raws.</p>
<p><b>Tool rules.</b> scripts/castsim/engine.py follows classify, buildPool, ROSTER.inPart, slotOf, castSlot, castPool, castRankApex, castEats,
castExcluded, hvSet, castGrow, castYear and castLadder line for line, with the engine's tables (cast slots, ladder, tiers, reach, vermin diets,
curated roles and water apexes, roster defaults, extinct corrections) read from the engine by the offline harness (MODE tables).</p>
</div>
<script id="data" type="application/json">{blob}</script>
<script>{JS}</script>
"""
    OUT.write_text(html)
    print('wrote', OUT, len(html))
    for r in val: print(r['ok'], r['ex'][:12], r['season'], r['layer'], r['what'], '|', str(r['sim'])[:90])


if __name__ == '__main__':
    main()
