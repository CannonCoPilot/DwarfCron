#!/usr/bin/env python3
"""castsim.design_report: the Cast Pipeline Trace page for the 9 Oct-evening design, from data/castsim/design.json
(design_run.py) -> data/castsim/cast-pipeline-v2.html. Styles and the table sort/filter enhancer are report.py's."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import report  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/castsim/design.json'
OUT = ROOT / 'data/castsim/cast-pipeline-v2.html'
SEASONS = ['Spring', 'Summer', 'Autumn', 'Winter']

ENHANCER = report.JS[report.JS.index('// every table:'):report.JS.index('\nconst SEASONS=')]

CSS_EXTRA = """
.lede h1{margin-top:4px}.lede p{max-width:78ch}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:12px 14px}
.card h4{margin:0 0 6px}.card p{font-size:.9rem;margin:0 0 6px}
.big{font:700 1.5rem var(--serif)}.small{font-size:.8rem;color:var(--muted)}
ul.find{max-width:84ch;display:grid;gap:8px;padding-left:1.2rem;font-size:.92rem}
.sp.vm{background:var(--sunk);color:var(--muted)}.sp.no{opacity:.55}
td .sp{margin:1px 2px 1px 0}
"""

JS = r"""
const ALL = JSON.parse(document.getElementById('data').textContent);
const M = ALL.meta, D = ALL.embarks;
const SEASONS=['Spring','Summer','Autumn','Winter'];
const LN={ground:'land-ground',flying:'land-flying',ocean:'ocean',fresh:'freshwater',cavern1:'cavern 1',cavern2:'cavern 2',cavern3:'cavern 3'};
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fmt=n=>(n==null||n===''?'':Number(n).toLocaleString('en-US'));
const chips=(arr,cls='')=>arr.map(t=>`<span class="sp ${cls}">${esc(t)}</span>`).join('');
const state={ex:D[0].id, layer:'ground', season:'Summer'};
function seg(id,items,cur,label){return `<label>${label}</label><div class="seg" id="${id}" role="group">`+items.map(([v,t])=>`<button type="button" data-v="${esc(v)}" aria-pressed="${v===cur}">${esc(t)}</button>`).join('')+'</div>';}
function step(n,title,why,body){return `<section class="step"><header><span class="n">${n}</span><h4>${title}</h4></header>${why?`<p class="why">${why}</p>`:''}${body}</section>`;}
function slotKey(ex,L){return L==='fresh'?'fresh:'+ex.sub:(L.startsWith('cavern')?'cavern':L);}
function dfCell(sp){return sp.st==null?'':(sp.st.length?'yes':'no');}
""" + ENHANCER + r"""
function render(){
  const ex=D.find(d=>d.id===state.ex);
  if(!ex.active.includes(state.layer)) state.layer=ex.active[0];
  const L=state.layer, key=L+'|'+state.season, lst=ex.lists[key]||[], tr=ex.casts[key], sp=ex.species;
  const sk=slotKey(ex,L), table=M.slots[sk];
  let h=`<div class="controls">${seg('layerSeg',ex.active.map(l=>[l,LN[l]]),L,'Layer')}${seg('seasonSeg',SEASONS.map(s=>[s,s]),state.season,'Season')}</div>`;
  // 1 the list
  const rows=lst.map(c=>{const s=sp[c.t];return `<tr><td class="mono">${esc(c.t)}</td><td>${c.sl.map(x=>`<span class="chip ${x==='apex'?'bad':x==='vermin'?'flag':'ok'}">${esc(x)}</span>`).join('')}</td><td class="mono">${esc(s.g)}${c.vc?' '+esc(c.vc):''}</td><td>${esc(s.h)}</td><td class="num">${fmt(s.m)}</td><td class="num">${fmt(s.p)}</td><td class="mono">${esc(s.s)}</td><td>${dfCell(s)}</td>${L.startsWith('cavern')?`<td class="num">${s.wd??''}</td>`:''}<td>${s.f.map(f=>`<span class="chip flag">${esc(f)}</span>`).join('')}</td></tr>`}).join('');
  const nv=lst.filter(c=>!c.sl.includes('vermin')).length;
  h+=step(1,`The ${LN[L]} list for ${state.season}: ${nv} species + ${lst.length-nv} vermin`,
    `Every pool species that belongs to this layer and is not NO_${state.season.toUpperCase()} on every caste, with the slots it can fill here. ${ex.kind==='real'?'"DF stocked" says whether DF\'s own population list for this fort had the species.':''}`,
    `<div class="tbl" style="max-height:460px"><table><thead><tr><th>species</th><th data-t="multi">can fill</th><th data-t="cat">guild</th><th data-t="cat">habitat</th><th class="num" data-t="num">adult cm³</th><th class="num" data-t="num">pet</th><th data-t="cat">seasons</th><th data-t="cat">DF stocked</th>${L.startsWith('cavern')?'<th class="num" data-t="num">weird</th>':''}<th data-t="multi">flags</th></tr></thead><tbody>${rows}</tbody></table></div>`);
  // 2 kept out
  const inLayer=Object.values(sp).filter(s=>s.L.includes(L)).map(s=>s.t), inList=new Set(lst.map(c=>c.t));
  const outSeason=inLayer.filter(t=>!inList.has(t));
  const notes=ex.notes.filter(n=>n.layer===L);
  h+=step(2,`Kept out of this list (${outSeason.length+notes.length})`,'Species of the pool that do not enter this layer, and why: out of season, outside their raw cavern depth, an amphibian on land-ground, too large for the murky-pool roster, or a land animal whose raws name no water body (only a broad biome group such as ALL_MAIN).',
    `<div class="tbl" style="max-height:300px"><table><thead><tr><th>species</th><th data-t="cat">why</th></tr></thead><tbody>${outSeason.map(t=>`<tr><td class="mono">${esc(t)}</td><td>NO_${state.season.toUpperCase()}</td></tr>`).join('')}${notes.map(n=>`<tr><td class="mono">${esc(n.token)}</td><td>${esc(n.why)}</td></tr>`).join('')}</tbody></table></div>`);
  // 3 slots drawn
  const filled={};tr.members.forEach(([t,s])=>filled[s]=(filled[s]||0)+1);
  const srows=Object.entries(table).filter(([s])=>s!=='_vermin').map(([s,[lo,hi]])=>`<tr><td><b>${esc(s==='swimmer'?'amphib or aquatic':s)}</b></td><td class="num" data-v="${hi}">${lo===hi?lo:lo+'-'+hi}</td><td class="num">${tr.want[s]}</td><td class="num">${filled[s]||0}</td><td class="note">${esc((tr.unfilled||{})[s]||'')}</td></tr>`).join('')
    +`<tr><td><b>vermin</b></td><td class="num" data-v="${table._vermin[1]}">${table._vermin[0]===table._vermin[1]?table._vermin[0]:table._vermin.join('-')}</td><td class="num">${tr.vermin_want}</td><td class="num">${tr.vermin.length}</td><td class="note">${tr.vermin_eligible} eligible</td></tr>`;
  h+=step(3,`Slots for ${ex.sub&&L==='fresh'?'freshwater ('+ex.sub+')':LN[L]}`,'The layer\'s slot table; a range draws its count for this cast.',
    `<div class="tbl"><table><thead><tr><th data-t="cat">slot</th><th class="num" data-t="num">range</th><th class="num" data-t="num">drawn</th><th class="num" data-t="num">filled</th><th>note</th></tr></thead><tbody>${srows}</tbody></table></div>`);
  // 4 apex
  h+=step(4,'Apex','As built (v7.4 "the mix"): the largest flagged predator in season keeps the apex slot; the rest can take meso. None flagged: the largest non-sentient predator is promoted.',
    'apex' in tr.want?`<p><b>Rule used:</b> ${esc(tr.apex_rule||'no candidate')}</p>${tr.apex_rank.length?`<div class="tbl" style="max-height:260px"><table><thead><tr><th class="num" data-t="num">#</th><th>species</th><th class="num" data-t="num">adult cm³</th><th data-t="cat">result</th></tr></thead><tbody>${tr.apex_rank.map(([t,m],i)=>`<tr><td class="num">${i+1}</td><td class="mono">${esc(t)}</td><td class="num">${fmt(m)}</td><td>${i===0?'<span class="chip bad">apex</span>':'<span class="chip warn">can take meso</span>'}</td></tr>`).join('')}</tbody></table></div>`:''}`:'<p class="note">This layer has no apex slot.</p>');
  // 5 fill log
  const hv=Object.entries(tr.hv||{});
  h+=step(5,`Seed and fill (${tr.log.length} picks)`,
    L==='flying'?'Land-flying: each slot is drawn directly from its eligible fliers (weighted: x3 pack hunters, x0.1 per earlier cast this year, x0.2 giants); the food web is assigned after.':
    'The seed is a weighted pick among the high-value species (war-trainable, top 10% by pet value, top 10% by size; never a sentient). Then each pick takes a species linked to the cast (its prey or predator) into the emptiest slot; a slot nothing links to is filled from its eligible species anyway ("no link"). Weights: x3 pack hunters, x0.1 per earlier cast this year, x0.2 giants'+(L.startsWith('cavern')?', and the cavern\'s weirdness weight.':'.'),
    `${hv.length?`<p class="note"><b>High value here:</b> ${hv.map(([t,w])=>`${esc(t)} (${esc(w)})`).join(', ')}</p>`:''}<div class="tbl"><table><thead><tr><th class="num" data-t="num">#</th><th>species</th><th data-t="cat">slot</th><th data-t="cat">how</th><th>detail</th></tr></thead><tbody>${tr.log.map((l,i)=>{const how=l.how.split(' (')[0];return `<tr><td class="num">${i+1}</td><td class="mono">${esc(l.species)}</td><td>${esc(l.slot==='swimmer'?'amphib or aquatic':l.slot)}</td><td>${esc(how.startsWith('apex')?'apex':how)}</td><td class="note">${esc(l.how)}</td></tr>`}).join('')}</tbody></table></div>`);
  // 6 vermin
  h+=step(6,`Vermin (${tr.vermin.length} of ${tr.vermin_eligible} eligible)`,'The vermin the members eat, one per class first, then the rest of the count from any eligible vermin.',
    `<div class="tbl"><table><thead><tr><th>species</th><th data-t="cat">class</th><th class="num" data-t="num">eaten by</th></tr></thead><tbody>${tr.vermin.map(([t,c,n])=>`<tr><td class="mono">${esc(t)}</td><td>${esc(c)}</td><td class="num">${n}</td></tr>`).join('')}</tbody></table></div>`);
  // 7 the cast
  const deg={};tr.edges.forEach(([a,b])=>{deg[a]=(deg[a]||0)+1;deg[b]=(deg[b]||0)+1;});
  const crow=tr.members.map(([t,s])=>`<tr><td><b>${esc(s==='swimmer'?'amphib or aquatic':s)}</b></td><td class="mono">${esc(t)}</td><td class="num">${fmt(sp[t].m)}</td><td>${esc(sp[t].h)}</td><td class="num">${deg[t]||0}</td><td>${dfCell(sp[t])}</td></tr>`).join('')+tr.vermin.map(([t,c])=>`<tr><td><b>vermin</b></td><td class="mono">${esc(t)}</td><td class="num">${fmt(sp[t].m)}</td><td>${esc(sp[t].h)}</td><td class="num">${deg[t]||0}</td><td>${dfCell(sp[t])}</td></tr>`).join('');
  h+=step(7,`The ${state.season} ${LN[L]} cast: ${tr.members.length} species + ${tr.vermin.length} vermin`,`${tr.weird!=null?'Mean weirdness of the cast: <b>'+tr.weird+'</b>. ':''}${Object.keys(tr.unfilled).length?'Unfilled: '+Object.entries(tr.unfilled).map(([s,w])=>esc(s)+' '+esc(w)).join('; ')+'.':'Every slot filled.'}`,
    `<div class="tbl"><table><thead><tr><th data-t="cat">slot</th><th>species</th><th class="num" data-t="num">adult cm³</th><th data-t="cat">habitat</th><th class="num" data-t="num">web links</th><th data-t="cat">DF stocked</th></tr></thead><tbody>${crow}</tbody></table></div>`);
  // 8 web
  h+=step(8,`The food web, after the draw (${tr.edges.length} edges)`,'Who eats whom among the cast: the slot tiers (apex over meso over the rest; vermin last), habitat reach, and the new shore rule: a shore creature or waterbird takes aquatic creatures no larger than itself (or 20,000 cm³) and aquatic vermin.',
    `<div class="tbl" style="max-height:300px"><table><thead><tr><th data-t="cat">predator</th><th data-t="cat">prey</th></tr></thead><tbody>${tr.edges.map(([a,b])=>`<tr><td class="mono">${esc(a)}</td><td class="mono">${esc(b)}</td></tr>`).join('')}</tbody></table></div>${tr.isolated.length?`<p><b>No link to the rest of the cast:</b> ${chips(tr.isolated)}</p>`:''}`);
  document.getElementById('steps').innerHTML=h;
  enhance(document.getElementById('steps'));
  // the year's roster and the gates for this embark
  const yr={};
  ex.active.forEach(l=>SEASONS.forEach(s=>{const c=ex.casts[l+'|'+s];c.members.forEach(([t,sl])=>{const k=l+'|'+t;(yr[k]=yr[k]||{l,t,sl:new Set(),s:new Set()});yr[k].s.add(s);yr[k].sl.add(sl)});c.vermin.forEach(([t])=>{const k=l+'|'+t;(yr[k]=yr[k]||{l,t,sl:new Set(),s:new Set()});yr[k].s.add(s);yr[k].sl.add('vermin')});}));
  const yrows=Object.values(yr).sort((a,b)=>ex.active.indexOf(a.l)-ex.active.indexOf(b.l)||a.t.localeCompare(b.t)).map(r=>`<tr><td>${LN[r.l]}</td><td class="mono">${esc(r.t)}</td><td>${[...r.sl].map(x=>`<span class="chip ${x==='apex'?'bad':x==='vermin'?'flag':'ok'}">${esc(x==='swimmer'?'amphib or aquatic':x)}</span>`).join('')}</td>${SEASONS.map(s=>`<td>${r.s.has(s)?'cast':''}</td>`).join('')}<td class="num">${r.s.size}</td><td>${dfCell(sp[r.t])}</td></tr>`).join('');
  document.getElementById('year').innerHTML=`<p class="note">Every species cast on ${esc(ex.name)} this year, by layer. A species not listed rests all year.</p><div class="tbl" style="max-height:520px"><table><thead><tr><th data-t="cat">layer</th><th>species</th><th data-t="multi">slot</th>${SEASONS.map(s=>`<th data-t="cat">${s}</th>`).join('')}<th class="num" data-t="num">seasons</th><th data-t="cat">DF stocked</th></tr></thead><tbody>${yrows}</tbody></table></div>`;
  enhance(document.getElementById('year'));
  document.getElementById('gates').innerHTML=`<p class="note">Species whose BIOME names one of this embark's biomes but which the savage, alignment or extinct gates keep out (${ex.rejected.length}).</p><div class="tbl" style="max-height:420px"><table><thead><tr><th>species</th><th data-t="cat">why</th><th data-t="multi">biomes it matched</th></tr></thead><tbody>${ex.rejected.map(r=>`<tr><td class="mono">${esc(r.token)}</td><td>${esc(r.why)}</td><td>${r.biomes.map(b=>`<span class="sp">${esc(b)}</span>`).join('')}</td></tr>`).join('')}</tbody></table></div>`;
  enhance(document.getElementById('gates'));
  document.querySelectorAll('#layerSeg button').forEach(b=>b.onclick=()=>{state.layer=b.dataset.v;render()});
  document.querySelectorAll('#seasonSeg button').forEach(b=>b.onclick=()=>{state.season=b.dataset.v;render()});
  document.querySelectorAll('#exSeg button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.v===state.ex));
  document.querySelectorAll('.exname').forEach(e=>e.textContent=ex.name);
}
document.getElementById('exPick').innerHTML=seg('exSeg',D.map(d=>[d.id,d.name.split(' (')[0]]),state.ex,'Embark');
document.querySelectorAll('#exSeg button').forEach(b=>b.onclick=()=>{state.ex=b.dataset.v;render()});
enhance(document);
render();
"""

LN = {'ground': 'land-ground', 'flying': 'land-flying', 'ocean': 'ocean', 'fresh': 'freshwater', 'cavern1': 'cavern 1', 'cavern2': 'cavern 2', 'cavern3': 'cavern 3'}


def esc(s): return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def slot_key(ex, L): return 'fresh:' + ex['sub'] if L == 'fresh' else ('cavern' if L.startswith('cavern') else L)


def rng(t): return f'{t[0]}' if t[0] == t[1] else f'{t[0]}-{t[1]}'


def layer_table(meta):
    what = {
        'ground': 'walkers matching a fort land biome; never amphibious, aquatic or flying',
        'flying': 'fliers matching a fort land biome; flying vermin (birds, insects)',
        'ocean': 'species whose raws name the fort\'s sea (aquatic and amphibious on any match), shore creatures and waterbirds of a saltwater marsh, swamp or mangrove; sea vermin',
        'fresh:lake': 'a lake (or lake + river): species naming the fort\'s lake, river or pool; amphibians matching a fort land biome',
        'fresh:river': 'river or brook, no lake: as the lake, smaller',
        'fresh:pool': 'murky pools only: small aquatic or amphibious species (up to 20,000 cm³); the fish slot also takes fish and amphibious vermin',
        'cavern': 'each cavern its own layer: species of the caverns whose raw depth range includes it; weighted by weirdness (1 plain, 3 strange)',
    }
    rows = []
    for k, t in meta['slots'].items():
        name = {'fresh:lake': 'freshwater: lake', 'fresh:river': 'freshwater: river/brook', 'fresh:pool': 'freshwater: murky pools', 'cavern': 'cavern 1, 2, 3'}.get(k, LN.get(k, k))
        slots = ', '.join(f'{("amphib or aquatic" if s == "swimmer" else s)} {rng(v)}' for s, v in t.items() if s != '_vermin')
        mx = sum(v[1] for s, v in t.items() if s != '_vermin')
        rows.append(f"<tr><td><b>{esc(name)}</b></td><td class='note'>{esc(what[k])}</td><td>{esc(slots)}</td><td class='num' data-v='{t['_vermin'][1]}'>{rng(t['_vermin'])}</td><td class='num'>{mx}</td></tr>")
    return ("<div class='tbl'><table><thead><tr><th data-t='cat'>layer</th><th>what goes in</th><th>slots per cast</th><th class='num' data-t='num'>vermin</th>"
            "<th class='num' data-t='num'>species max</th></tr></thead><tbody>" + ''.join(rows) + '</tbody></table></div>')


def embark_table(data):
    rows = []
    for e in data:
        s = e['spec']
        land = ', '.join(f"{b['biome']} (sav {b['sav']}, evil {b['evil']}{', ' + b['src'] if e['kind'] == 'real' else ''})" for b in s['land'])
        water = '; '.join(f"{k}: " + ', '.join(w['biome'] for w in ws) for k, ws in s['water'].items() if ws)
        sub = {'lake': 'lake', 'river': 'river/brook only', 'pool': 'murky pools only', None: 'none'}[e['sub']]
        rows.append(f"<tr><td>{esc(e['name'].split(' (')[0])}</td><td>{e['kind']}</td><td class='note'>{esc(land)}</td><td class='note'>{esc(water)}</td>"
                    f"<td>{sub}</td><td>{s.get('extinct')}</td><td class='num'>{len(e['active'])}</td><td class='num'>{len(e['active']) * 4}</td></tr>")
    return ("<div class='tbl'><table><thead><tr><th data-t='cat'>embark</th><th data-t='cat'>kind</th><th>land biomes</th><th>water biomes</th>"
            "<th data-t='cat'>freshwater</th><th data-t='cat'>extinct rule</th><th class='num' data-t='num'>layers</th><th class='num' data-t='num'>casts</th></tr></thead><tbody>"
            + ''.join(rows) + '</tbody></table></div>')


def funnel_table(data):
    rows = []
    for e in data:
        f = list(e['funnel'].values())
        rej = {}
        for r in e['rejected']:
            k = 'savage' if r['why'].startswith('SAVAGE') else ('extinct' if r['why'].startswith('extinct') else 'alignment')
            rej[k] = rej.get(k, 0) + 1
        rows.append(f"<tr><td>{esc(e['name'].split(' (')[0])}</td>" + ''.join(f"<td class='num'>{n:,}</td>" for n in f)
                    + ''.join(f"<td class='num'>{rej.get(k, 0)}</td>" for k in ('savage', 'alignment', 'extinct')) + '</tr>')
    hd = ['all creatures', 'wild', 'natural', 'BIOME matches', 'in the pool', 'out: savage', 'out: GOOD/EVIL', 'out: extinct rule']
    return ("<div class='tbl'><table><thead><tr><th data-t='cat'>embark</th>" + ''.join(f"<th class='num' data-t='num'>{h}</th>" for h in hd)
            + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')


def lists_table(data):
    rows = []
    for e in data:
        for L in e['active']:
            sizes = [sum(1 for c in e['lists'][f'{L}|{s}'] if 'vermin' not in c['sl']) for s in SEASONS]
            vs = [sum(1 for c in e['lists'][f'{L}|{s}'] if 'vermin' in c['sl']) for s in SEASONS]
            pool = [t for t, sp in e['species'].items() if L in sp['L'] and not sp['v']]
            dfn = sum(1 for t in pool if e['species'][t]['st']) if e['kind'] == 'real' else None
            casts = [e['casts'][f'{L}|{s}'] for s in SEASONS]
            uniq = {t for c in casts for t, _ in c['members']}
            per = sum(len(c['members']) for c in casts) / 4
            apex = [next((t for t, sl in c['members'] if sl == 'apex'), None) for c in casts]
            ap = sorted({a for a in apex if a})
            wd = [c['weird'] for c in casts if c['weird'] is not None]
            rows.append(f"<tr><td>{esc(e['name'].split(' (')[0])}</td><td>{LN[L]}</td><td class='num'>{len(pool)}</td>"
                        f"<td class='num'>{'' if dfn is None else dfn}</td>" + ''.join(f"<td class='num'>{n}</td>" for n in sizes)
                        + f"<td class='num'>{sum(vs) // 4}</td><td class='num'>{per:.1f}</td><td class='num'>{len(uniq)}</td>"
                        f"<td class='mono' style='font-size:.78rem'>{esc(', '.join(ap)) or '<span class=note>no apex slot</span>'}</td>"
                        f"<td class='num'>{'' if not wd else round(sum(wd) / len(wd), 2)}</td></tr>")
    hd = ("<th data-t='cat'>embark</th><th data-t='cat'>layer</th><th class='num' data-t='num'>pool</th><th class='num' data-t='num'>of which DF stocked</th>"
          + ''.join(f"<th class='num' data-t='num'>{s} list</th>" for s in SEASONS)
          + "<th class='num' data-t='num'>vermin per list</th><th class='num' data-t='num'>cast size</th><th class='num' data-t='num'>distinct cast in the year</th>"
          "<th data-t='cat'>apex (all seasons)</th><th class='num' data-t='num'>mean weirdness</th>")
    return f"<div class='tbl' style='max-height:560px'><table><thead><tr>{hd}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"


def judgement_table(meta):
    rows = ''.join(f"<tr><td><b>{esc(k)}</b></td><td>{esc(v)}</td></tr>" for k, v in meta['judgement'])
    return f"<div class='tbl'><table><thead><tr><th data-t='cat'>decision</th><th>what the simulation does</th></tr></thead><tbody>{rows}</tbody></table></div>"


def weird_table(meta):
    rows = ''.join(f"<tr><td class='mono'>{esc(k)}</td><td class='num'>{v}</td><td class='num'>{round((1 - v) ** 2 + .05, 2)}</td>"
                   f"<td class='num'>{round(max(.05, 1 - abs(v - .5) * 1.8), 2)}</td><td class='num'>{round(v * v + .05, 2)}</td></tr>"
                   for k, v in sorted(meta['weird'].items(), key=lambda kv: kv[1]))
    return ("<div class='tbl' style='max-height:380px'><table><thead><tr><th>species</th><th class='num' data-t='num'>weirdness</th>"
            "<th class='num' data-t='num'>weight in cavern 1</th><th class='num' data-t='num'>cavern 2</th><th class='num' data-t='num'>cavern 3</th></tr></thead><tbody>"
            + rows + '</tbody></table></div>')


def stats(data):
    by = {e['id']: e for e in data}
    def pool_n(e, L): return sum(1 for sp in e['species'].values() if L in sp['L'] and not sp['v'])
    def df_n(e, L): return sum(1 for sp in e['species'].values() if L in sp['L'] and not sp['v'] and sp['st'])
    def uniq(e, L): return len({t for s in SEASONS for t, _ in e['casts'][f'{L}|{s}']['members']})
    def wd(L): return round(sum(e['casts'][f'{L}|{s}']['weird'] for e in data for s in SEASONS) / (4 * len(data)), 2)
    return dict(lake_g=pool_n(by['lake'], 'ground'), lake_g_df=df_n(by['lake'], 'ground'), ocean_g=pool_n(by['ocean'], 'ground'),
                ocean_g_df=df_n(by['ocean'], 'ground'), lake_gu=uniq(by['lake'], 'ground'), ocean_ou=uniq(by['ocean'], 'ocean'),
                savage_g=pool_n(by['savage'], 'ground'), brook_g=pool_n(by['brook'], 'ground'), brook_f=pool_n(by['brook'], 'fresh'), w1=wd('cavern1'), w2=wd('cavern2'), w3=wd('cavern3'),
                taiga_ext=sum(1 for sp in by['taiga']['species'].values() if 'extinct' in sp['f']),
                pools_cast=sorted({t for s in SEASONS for t, _ in by['pools']['casts'][f'fresh|{s}']['members']}))


def main():
    d = json.loads(DATA.read_text())
    data, meta = d['embarks'], d['meta']
    st = stats(data)
    blob = json.dumps(d, separators=(',', ':')).replace('</', '<\\/')
    html = f"""<title>Cast Pipeline Trace</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bitter:wght@500;700&family=Atkinson+Hyperlegible:wght@400;700&family=JetBrains+Mono:wght@400;600&display=swap">
<style>{report.CSS}{CSS_EXTRA}</style>
<div class="wrap">
<section class="lede">
  <span class="eyebrow">Seasonal Wildlife · the full-pool design · desk simulation · 9 Oct 2026</span>
  <h1>Cast Pipeline Trace</h1>
  <p>Your design of 9 Oct (evening), simulated on DF's own raws for six embarks. The pool is no longer the short list DF stocked on the
  region: every creature in the raws is a candidate, filtered first by wild and natural, then BIOME, SAVAGE, GOOD/EVIL and the world's
  real-world-extinct rule, then split into seven layers (land-ground, land-flying, ocean, freshwater, cavern 1, 2, 3) and four seasons.
  Each of those lists feeds one season cast with the slot table you set for its layer. Nothing here ran DF and the engine is unchanged; this is
  the design, ahead of building it. Every table sorts by a click on its header; categorical columns filter.</p>
</section>

<h2>What changes, in numbers</h2>
<div class="grid2">
<div class="card"><h4>Land-ground pools grow several-fold</h4><p><span class="big">{st['lake_g_df']} → {st['lake_g']}</span> species on the lake fort,
<span class="big">{st['ocean_g_df']} → {st['ocean_g']}</span> on the ocean fort: what DF stocked against everything the biome allows.</p></div>
<div class="card"><h4>Every species DF stocked is still in</h4><p>On all three real forts the new pool contains every species in DF's population list,
except the locked unliving cave species, the lava-only magma crab, demons, and one damselfly. The biome reading matches DF's own stocking.</p></div>
<div class="card"><h4>Variety across the year</h4><p>{st['lake_gu']} different species cast on the lake fort's land-ground over four seasons,
{st['ocean_ou']} in the ocean fort's sea. The x0.1-per-earlier-cast weight spreads the picks.</p></div>
<div class="card"><h4>Caverns get stranger with depth</h4><p>Mean weirdness of the casts: cavern 1 <b>{st['w1']}</b>, cavern 2 <b>{st['w2']}</b>,
cavern 3 <b>{st['w3']}</b> (0 = a real animal's cave form, 1 = wholly alien).</p></div>
</div>

<h2>The layers and their slots</h2>
<p>As you set them, with land-ground (not specified) kept from v7.4 without its bird, raptor and sentient slots. A range draws its count per cast.</p>
{layer_table(meta)}

<h2>Six embarks</h2>
<p>Three real forts on region19: their land biomes are the 3×3 world tiles around the fort (from the world survey), their water bodies come from the
tool's own map scan, and the temperature zone of their rivers and pools is read from the water species DF stocked there. Three synthetic embarks
cover the other cases: an arctic coast with a river and extinct creatures in any wild region; a savage lake; an evil savanna with murky pools only.</p>
{embark_table(data)}

<h2>The top-level filters</h2>
<p>All {data[0]['funnel']['all creatures']:,} creatures in the raws (vanilla and extinct files, giants and animal people included) through the gates.
"Wild" is DF's own test for region populations: a BIOME, and LARGE_ROAMING or a vermin tag (colony insects included). It drops the 30 creatures with
no BIOME or no roaming tag: domestic animals and civilised races (no BIOME), the three DOES_NOT_EXIST entries and the wagon, and the megabeasts and
titans (dragon, hydra, roc, colossus, cyclops, ettin, giant, minotaur) and the sponge. "Natural" drops the 14 unliving: the elemental men and blood man,
fire imp and fire snake, grimeling, nightwing, purring maggot, and the giant sponge and sponge man. The 28 GOOD and EVIL species stay in until the
alignment gate, which checks each biome.</p>
{funnel_table(data)}

<h2>The 28 lists and their casts</h2>
<p>One row per embark and layer: the pool, how much of it DF had stocked, each season's list (species, not vermin), the cast drawn from it, and how many
different species the year's four casts used. Filter the embark or layer columns to compare.</p>
{lists_table(data)}

<h3>What the six embarks show</h3>
<ul class="find">
<li><b>The diversity is there.</b> The lake fort's land-ground pool is {st['lake_g']} species where DF stocked {st['lake_g_df']}; the savage forest's is {st['savage_g']}
(its extinct species, giants and animal people all qualify). The casts stay the size you set; the variety shows across the year.</li>
<li><b>A marsh has few walkers.</b> The brook fort's land-ground pool is {st['brook_g']} species: most marsh animals are amphibious and now belong to the
water layer, as you ruled. Its freshwater pool is {st['brook_f']}.</li>
<li><b>The apex never changes within a layer.</b> Under the built rule (largest flagged predator keeps apex) the land apex is the same species in all four
seasons on every embark (dingo, cougar, polar bear, tyrannosaurus, ogre); the flying apex is the eagle everywhere; the sea apex is still the sperm whale.
With pools this large, a weighted apex pick (by size, x0.1 per earlier cast) would rotate it. Your call, together with the open orca question.</li>
<li><b>Murky pools work as a mini roster</b> once the pool's fish slot can draw DF's pool fish and amphibians, which are all vermin: on the
evil savanna the year casts {', '.join(st['pools_cast'])}.</li>
<li><b>River-only freshwater has no apex</b>, as you listed; the alligator and similar predators take its one meso slot.</li>
<li><b>Extinct species follow the world setting.</b> With "any wild region" the arctic coast gains {st['taiga_ext']} extinct species (woolly mammoth and
woolly rhinoceros among them); with "savage regions only" the calm real forts get none and the savage forest gets all that fit.</li>
<li><b>Odd fits come from DF's own raws</b>, not the filter: an alligator on a cold river (its raws allow any temperate river), a capybara on a temperate
saltwater marsh, penguins on an arctic coast.</li>
<li><b>Caverns are the same three pools on every fort</b> (DF's cave species are not biome-bound), so only the draw differs between forts.</li>
</ul>

<h2>Step through an embark</h2>
<div class="controls" id="exPick"></div>
<div class="steps" id="steps"></div>

<h3>The year's roster: <span class="exname"></span></h3>
<div id="year"></div>

<h3>Kept out by the savage, alignment and extinct gates: <span class="exname"></span></h3>
<div id="gates"></div>

<h2>Cavern weirdness, first cut</h2>
<p>No cave species carries DF's MUNDANE tag, so the raws give no ready measure. This is a hand score for you to adjust; DF's raw depth range still
decides which caverns a species can live in, and the weight only tilts the draw.</p>
{weird_table(meta)}

<h2>Judgement calls in this simulation</h2>
<p>Everything the design left open and the simulation had to decide. Each is a single rule you can change.</p>
{judgement_table(meta)}

<h2>What building it means for the engine</h2>
<ul class="find">
<li><b>Species DF never stocked need a population.</b> DF only sends wildlife from the region's population list; a cast species with no entry there
(most of a full pool) needs an entry created for this site, or the tool places the units itself. Units placed with a population off the site never
breed (rig finding), so created entries should belong to the site.</li>
<li><b>The FREQUENCY ladder then applies to those entries</b> as it does now.</li>
<li><b>Each biome's savagery and alignment</b> come from the region data the engine already reads; the extinct rule from
<code>world.raws.param_real_world_extinct</code> (its value for region19 is not yet read).</li>
<li><b>Caverns become three layers</b> with their own casts, and freshwater picks its subtype from the water-body scan the tool already runs at load.</li>
</ul>

<h2>Method notes</h2>
<p><b>Raws.</b> DF 53.16's vanilla and extinct creature files compiled as DF compiles them (COPY_TAGS_FROM, the GIANT and ANIMAL_PERSON variations,
castes, derived flags, aggregate biome tokens expanded), as in the earlier trace. <b>Classification</b> (guild, habitat, size, pet value, the 83 extinct
corrections) is the engine's classify, mirrored in scripts/castsim/engine.py. <b>The design</b> is scripts/castsim/design.py; the runner is
design_run.py. Random draws are seeded per embark, layer and season, so one run is one possible year.</p>
</div>
<script id="data" type="application/json">{blob}</script>
<script>{JS}</script>
"""
    OUT.write_text(html)
    print('wrote', OUT, len(html))


if __name__ == '__main__':
    main()
