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
  h+=step(4,'Apex','Rebuilt 10 Oct: a weighted draw among the predators eligible in season (true apexes; the local ones only when there is no true apex). Weight: square root of group size against the largest, x3 pack hunters, x0.01 per cast the species is already on this year, x0.2 giants, x0.1 animal people. The others can still take meso.',
    'apex' in tr.want?`<p><b>Rule used:</b> ${esc(tr.apex_rule||'no candidate')}</p>${tr.apex_rank.length?`<div class="tbl" style="max-height:300px"><table><thead><tr><th>species</th><th data-t="cat">tier</th><th class="num" data-t="num">adult cm³</th><th class="num" data-t="num">group size cm³</th><th class="num" data-t="num">chance</th><th data-t="cat">result</th></tr></thead><tbody>${tr.apex_rank.map(([t,m,g,w,tier,res])=>`<tr><td class="mono">${esc(t)}</td><td>${esc(tier)}</td><td class="num">${fmt(m)}</td><td class="num">${fmt(g)}</td><td class="num" data-v="${w}">${w?(w*100).toFixed(1)+'%':''}</td><td>${res==='apex'?'<span class="chip bad">apex</span>':`<span class="chip warn">${esc(res)}</span>`}</td></tr>`).join('')}</tbody></table></div>`:''}`:'<p class="note">This layer has no apex slot.</p>');
  // 5 fill log
  const hv=Object.entries(tr.hv||{});
  h+=step(5,`Seed and fill (${tr.log.length} picks)`,
    L==='flying'?'Land-flying: each slot is drawn directly from its eligible fliers (weighted: x3 pack hunters, x0.01 per earlier cast this year, x0.2 giants); the food web is assigned after.':
    'The seed is a weighted pick among the high-value species (war-trainable, top 10% by pet value, top 10% by size; never a sentient). Then each pick takes a species linked to the cast (its prey or predator) into the emptiest slot; a slot nothing links to is filled from its eligible species anyway ("no link"). Weights: x3 pack hunters, x0.01 per earlier cast this year, x0.2 giants'+(L.startsWith('cavern')?', and the cavern\'s weirdness weight.':'.'),
    `${hv.length?`<p class="note"><b>High value here:</b> ${hv.map(([t,w])=>`${esc(t)} (${esc(w)})`).join(', ')}</p>`:''}<div class="tbl"><table><thead><tr><th class="num" data-t="num">#</th><th>species</th><th data-t="cat">slot</th><th data-t="cat">how</th><th>detail</th></tr></thead><tbody>${tr.log.map((l,i)=>{const how=l.how.split(' (')[0];return `<tr><td class="num">${i+1}</td><td class="mono">${esc(l.species)}</td><td>${esc(l.slot==='swimmer'?'amphib or aquatic':l.slot)}</td><td>${esc(how.startsWith('apex')?'apex':how)}</td><td class="note">${esc(l.how)}</td></tr>`}).join('')}</tbody></table></div>`);
  // 6 vermin
  h+=step(6,`Vermin (${tr.vermin.length} of ${tr.vermin_eligible} eligible)`,'The vermin the members eat, one per class first, then the rest of the count from any eligible vermin.',
    `<div class="tbl"><table><thead><tr><th>species</th><th data-t="cat">class</th><th class="num" data-t="num">eaten by</th></tr></thead><tbody>${tr.vermin.map(([t,c,n])=>`<tr><td class="mono">${esc(t)}</td><td>${esc(c)}</td><td class="num">${n}</td></tr>`).join('')}</tbody></table></div>`);
  // 7 the cast
  const deg={};tr.edges.forEach(([a,b])=>{deg[a]=(deg[a]||0)+1;deg[b]=(deg[b]||0)+1;});
  const crow=tr.members.map(([t,s])=>`<tr><td><b>${esc(s==='swimmer'?'amphib or aquatic':s)}</b></td><td class="mono">${esc(t)}</td><td class="num">${fmt(sp[t].m)}</td><td>${esc(sp[t].h)}</td><td class="num">${deg[t]||0}</td><td>${dfCell(sp[t])}</td></tr>`).join('')+tr.vermin.map(([t,c])=>`<tr><td><b>vermin</b></td><td class="mono">${esc(t)}</td><td class="num">${fmt(sp[t].m)}</td><td>${esc(sp[t].h)}</td><td class="num">${deg[t]||0}</td><td>${dfCell(sp[t])}</td></tr>`).join('');
  h+=step(7,`The ${state.season} ${LN[L]} cast: ${tr.members.length} species + ${tr.vermin.length} vermin`,`${(tr.placed||[]).length?'Placed like plants on the bed (no slot): <b>'+tr.placed.map(esc).join(', ')+'</b>. ':''}${tr.weird!=null?'Mean weirdness of the cast: <b>'+tr.weird+'</b>. ':''}${Object.keys(tr.unfilled).length?'Unfilled: '+Object.entries(tr.unfilled).map(([s,w])=>esc(s)+' '+esc(w)).join('; ')+'.':'Every slot filled.'}`,
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


def real_apex_table(meta):
    rows = ''.join(f"<tr><td class='mono'>{esc(r['t'])}</td><td>{LN.get(r['layer'], r['layer'])}</td><td><span class='chip {'bad' if r['tier'] == 'apex' else 'warn'}'>{r['tier']}</span></td>"
                   f"<td class='num'>{r['m']:,}</td><td>{'yes' if r['carn'] else 'no'}</td><td>{esc(r['role'])} ({esc(r['g'])})</td><td class='note'>{esc(r['why'])}</td></tr>"
                   for r in meta['real_apex'])
    return ("<div class='tbl'><table><thead><tr><th>species</th><th data-t='cat'>layer</th><th data-t='cat'>tier</th><th class='num' data-t='num'>adult cm³</th>"
            "<th data-t='cat'>CARNIVORE in DF</th><th data-t='cat'>tool reads it as</th><th>why</th></tr></thead><tbody>" + rows + '</tbody></table></div>')


def carnivore_table(meta):
    rows = ''.join(f"<tr><td class='mono'>{esc(r['t'])}</td><td>{esc(r['h'])}</td><td class='num'>{r['m']:,}</td><td class='mono'>{esc(r['g'])}</td><td class='note'>{esc(r['why'])}</td></tr>"
                   for r in meta['carnivore'])
    return ("<div class='tbl' style='max-height:420px'><table><thead><tr><th>species</th><th data-t='cat'>habitat</th><th class='num' data-t='num'>adult cm³</th>"
            "<th data-t='cat'>guild now</th><th>hunts</th></tr></thead><tbody>" + rows + '</tbody></table></div>')


def audit_table(meta):
    rows = []
    for r in meta['audit']['rows']:
        tr = sorted({t for p in r['seasons'] for t in p['true']}); lo = sorted({t for p in r['seasons'] for t in p['local']})
        flag = 'too few' if r['min_true'] < 2 else 'ok'
        rows.append(f"<tr><td class='mono'>{esc(r['biome'])}</td><td>{LN.get(r['layer'], r['layer'])}</td><td><span class='chip {'bad' if flag != 'ok' else 'ok'}'>{flag}</span></td>"
                    f"<td class='num'>{r['min_true']}</td><td>{''.join(f'<span class=sp>{esc(t)}</span>' for t in tr) or '<span class=note>none</span>'}</td>"
                    f"<td>{''.join(f'<span class=sp>{esc(t)}</span>' for t in lo)}</td><td class='note'>{esc(', '.join(r['proposals']))}</td>"
                    f"<td class='num'>{r['min_after'] if r['proposals'] else ''}</td></tr>")
    return ("<div class='tbl' style='max-height:560px'><table><thead><tr><th data-t='cat'>biome</th><th data-t='cat'>layer</th><th data-t='cat'>verdict</th>"
            "<th class='num' data-t='num'>fewest true apexes in a season</th><th data-t='multi'>true apexes</th><th data-t='multi'>local apexes</th>"
            "<th>proposed</th><th class='num' data-t='num'>fewest, with the proposals</th></tr></thead><tbody>" + ''.join(rows) + '</tbody></table></div>')


def proposal_table(meta):
    rows = ''.join(f"<tr><td class='mono'>{esc(p['t'])}</td><td>{p['kind']}</td><td>{LN.get(p['layer'], p['layer'])}</td>"
                   f"<td>{''.join(f'<span class=sp>{esc(b)}</span>' for b in p['biomes'])}</td><td class='note'>{esc(p['why'])}</td></tr>"
                   for p in meta['audit']['proposals'])
    return ("<div class='tbl'><table><thead><tr><th>species</th><th data-t='cat'>kind</th><th data-t='cat'>layer</th><th data-t='multi'>biomes</th>"
            "<th>real-life basis</th></tr></thead><tbody>" + rows + '</tbody></table></div>')


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
                rot=sum(1 for e in data for L in e['active'] if len({next((t for t, sl in e['casts'][f'{L}|{s}']['members'] if sl == 'apex'), None) for s in SEASONS} - {None}) > 1),
                nl=sum(1 for e in data for L in e['active'] if any(sl == 'apex' for s in SEASONS for _, sl in e['casts'][f'{L}|{s}']['members'])),
                oc_apex=' → '.join(next((t.lower().replace('_', ' ') for t, sl in by['ocean']['casts'][f'ocean|{s}']['members'] if sl == 'apex'), '-') for s in SEASONS),
                tg_apex=' → '.join(next((t.lower().replace('_', ' ') for t, sl in by['taiga']['casts'][f'ground|{s}']['members'] if sl == 'apex'), '-') for s in SEASONS),
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
{st['ocean_ou']} in the ocean fort's sea. The x0.01-per-earlier-cast weight spreads the picks.</p></div>
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
"Wild" is DF's own test for region populations: a BIOME, and LARGE_ROAMING or a vermin tag (colony insects included). It drops 29 creatures:
domestic animals and civilised races (no BIOME), the three DOES_NOT_EXIST entries and the wagon, and the megabeasts and titans (dragon, hydra, roc,
colossus, cyclops, ettin, giant, minotaur). The sponge passes as a placed plant. "Natural" drops 12 unliving: the elemental men and blood man,
fire imp and fire snake, grimeling, nightwing and purring maggot. Kept (12 Oct): the sponge and giant sponge as plants placed on the bed (no cast slot),
the sponge man as a filter-feeding creature. The 28 GOOD and EVIL species stay in until the alignment gate, which checks each biome.</p>
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
<li><b>The apex rotates.</b> Under the rebuilt rule the apex differs between seasons on {st['rot']} of the {st['nl']} layers with an apex slot.
The ocean fort's sea goes {st['oc_apex']}; the arctic coast's land {st['tg_apex']}. Where it stays put, only one predator is eligible: the dingo is the
only flagged hunter of a temperate savanna or marsh in DF's raws (lake and brook forts).</li>
<li><b>Murky pools work as a mini roster</b> once the pool's fish slot can draw DF's pool fish and amphibians, which are all vermin: on the
evil savanna the year casts {', '.join(st['pools_cast'])}.</li>
<li><b>River-only freshwater has no apex</b>, as you listed; the alligator and similar predators take its one meso slot.</li>
<li><b>Extinct species follow the world setting.</b> With "any wild region" the arctic coast gains {st['taiga_ext']} extinct species (woolly mammoth and
woolly rhinoceros among them); with "savage regions only" the calm real forts get none and the savage forest gets all that fit.</li>
<li><b>Odd fits come from DF's own raws</b>, not the filter: an alligator on a cold river (its raws allow any temperate river), a capybara on a temperate
saltwater marsh, penguins on an arctic coast.</li>
<li><b>Caverns are the same three pools on every fort</b> (DF's cave species are not biome-bound), so only the draw differs between forts.</li>
</ul>

<h2>Who can hold the apex</h2>
<p>Rebuilt 10 Oct. A species can be drawn for the apex slot of a layer when it is:</p>
<ul class="find">
<li>a LARGE_PREDATOR species (land, flying and caverns; caverns keep their sentients in the sentient slot);</li>
<li>a giant of any predator, mesopredators included (giant fox, giant badger, giant kestrel);</li>
<li>an animal person whose root animal is eligible (bear man, cougar man, quetzalcoatlus man), drawn at x0.1 as all animal people;</li>
<li>on water layers, one of the engine's curated water apexes (orca, sperm whale, great white, crocodiles, the large sharks) or a giant or animal
person of one; DF's other LARGE_PREDATOR water species (sea lamprey, frill shark, blacktip) take meso, as before;</li>
<li>a raptor of 2,000 cm³ or more on land-flying (eagle, the large owls, osprey; never a scavenger);</li>
<li>a real-life apex that DF does not tag, below.</li>
</ul>
<p>The draw then weights each by the square root of its group size against the largest (a pack's mean size times the adult size), x3 for pack hunters,
x0.01 for each cast it is already on this year (counted only once drawn: the year's 28 casts are built together at its start), x0.2 giants and x0.1 animal people. That is what puts the orca beside the sperm whale: a pod of six
orcas outweighs one whale.</p>
<h3>Real-life apexes DF does not tag LARGE_PREDATOR</h3>
<p>Every carnivore in the raws without the flag (56) and the large predators DF does not even mark CARNIVORE were checked against their real ecology.
"Apex" joins the draw; "local" holds the apex only where no true apex is in season (the top of a small or depleted community). Several are not
CARNIVORE in DF's raws; the CARNIVORE fix below now reads them as predators.</p>
{real_apex_table(meta)}
<p class="note">Considered and left as mesopredators: honey badger, ocelot, bobcat, jackal, king cobra, the otters, octopus, walrus and narwhal
(predators, but not at the top of their webs), the vulture (a scavenger), and the elephant seal (hunted by orcas and great whites).</p>

<h2>The CARNIVORE fix</h2>
<p>Real-life hunters DF does not tag CARNIVORE (or BONECARN), which the tool used to read as prey (12 Oct: applied). Upper-level predators only:
mid-level fish (cod, carp, bluefish, skate) stay in the fish slot and penguins stay shore birds. A fish-eating bird gains the predator role but is
not a raptor, so it never holds the flying apex. In the engine this is a set of 'predator' entries in MODEL.ROLE.</p>
{carnivore_table(meta)}

<h2>Biomes × apex audit</h2>
<p>For every surface biome on a calm-to-wild, neutral region (no savage species, no GOOD or EVIL species, no extinct species), the species that can hold
each layer's apex in each season under the rule above. A biome is flagged when some season has fewer than two true apexes: one species then holds the
slot all season with nothing to rotate with. Rivers and murky pools have no apex slot; caverns are the same in every fort.</p>
{audit_table(meta)}
<h3>Proposed hand-wiring</h3>
<p>For your review; not applied to the casts on this page. "Promote" makes a species that already lives in the biome a true apex there; "wire" treats
an existing apex species as living in the biome (the tool's pool, not a raw edit). With all of them the flagged biomes reach two or more true apexes
in every season, except the glacier's winter.</p>
{proposal_table(meta)}

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

<h2>Building it into seasonal-wildlife</h2>
<p>A pass through the engine (scripts/seasonal-wildlife.lua on v7.4-onebuilder 834f92e, 19,102 lines; line numbers below) for the shortest path from
today's code to the patterns on this page. Most of the machinery exists: the engine already scans every raw creature against the embark's biomes,
already creates population entries on land and in caverns, and already places units with an on-site population reference. Order matters:
each phase can ship and be checked on the rig before the next.</p>
<div class='tbl'><table><thead><tr><th class='num' data-t='num'>phase</th><th>change</th><th>where (line)</th><th data-t='cat'>size</th><th>notes</th></tr></thead><tbody>
<tr><td class='num'>0</td><td>The desk simulation becomes the oracle: export its pools, 28 lists, slot and apex eligibility for a few embarks as fixtures, and check the engine against them offline</td><td>tests/web/harness.lua, MODE fixes and sim (fakeworld.lua)</td><td>small</td><td>every phase below adds checks here first</td></tr>
<tr><td class='num'>1</td><td>CARNIVORE fix: the 27 species as 'predator' in the curated role table; the four fish-eating birds kept out of the flying apex</td><td>MODEL.ROLE 1733; MODEL.guild 1962 already reads it (1968); fly apex test</td><td>small</td><td>guild follows the role table, so no other change</td></tr>
<tr><td class='num'>1</td><td>Reuse x0.01 per cast already drawn this year</td><td>ROSTER.CAST_DEF 8259 (reuse); castGrow 8534; castYear 8678 counts after each cast</td><td>trivial</td><td>castYear already builds all of a year's casts at once and counts only casts drawn</td></tr>
<tr><td class='num'>1</td><td>Sponges: the sponge man natural (filter feeder); the giant sponge placed like the sponge, savage regions only</td><td>ecoOf 1698 (exception); V7.SPONGE 9517-9635 (ribbons, SPONGE only today)</td><td>small</td><td>both sponges already sit in MODEL.NEVER_PREY (2570)</td></tr>
<tr><td class='num'>2</td><td>The full pool: drop the stocked-only rule; gate each species by the savagery, alignment and extinct rule of the biome it matches; water layers only where the raws name the water body; colony insects as vermin</td><td>buildPool 2351 (already walks all raws via creatureEligible 2322, tagging them inEmbark=false); ROSTER.savage 7827; V7.alignment 1640; ROSTER.inPart 7907 and castPartOk 8384 (drop inEmbark)</td><td>medium</td><td>DF compiles the raws itself, so the TAIGA alias and COPY_TAGS_FROM need nothing in the engine</td></tr>
<tr><td class='num'>2</td><td>Read the world's REAL_WORLD_EXTINCT</td><td>new, beside V7.alignment 1640: <code>df.global.world.worldgen.worldgen_parms.real_world_extinct</code></td><td>small</td><td>nothing reads it today; the number for each setting to be confirmed on the rig (region2's file says UNTAMED_WILDS)</td></tr>
<tr><td class='num'>3</td><td>Seven layers with the slot tables on this page; freshwater subtype from the water-body registry; caverns 1-3 by raw depth range, weighted by weirdness</td><td>ROSTER.CAST 8243; castPool 8390; castYear 8662 (layer loop, seeds); castSanitize 8286 and castManages 8649 (hard-code three layers); V7.WB.build 6763 and typeOf 6740; CAVE.survey 4736</td><td>large</td><td>saved casts change shape: a load of an older save must migrate them</td></tr>
<tr><td class='num'>3</td><td>The year's roster, the ladder and turnover keyed by the seven layers</td><td>castLadder 8712; V7.GRP.castTurnover 13006; applyLive 3100; holdOutOfSeason 3152</td><td>medium</td><td></td></tr>
<tr><td class='num'>4</td><td>Apex: the weighted draw, the real-life apex set, giants and animal people of eligible roots, the promote-largest fallback</td><td>castRankApex 8430 (rewrite); castEats 8464 reads the drawn codes</td><td>small</td><td>the draw uses castGrow's own generator so a rebuild reproduces it</td></tr>
<tr><td class='num'>5</td><td>Make unstocked cast species arrive: at castYear, create a population entry for each cast species the region lacks; DF then sends waves from it, and the FREQUENCY ladder and hold logic apply as for DF's own entries</td><td>land and sea: addNewSpecies 4106 (live-tested: DF drew a wave from a created entry); caverns: ROSTER.caveEntryFor 9169; lakes, rivers, pools: new (no water-feature entry creator exists)</td><td>large</td><td>created entries belong to the site, so placed units can breed (they carry its population reference, PLACE.one 4929)</td></tr>
<tr><td class='num'>5</td><td>Where DF will not send a species from an entry (a savage species on a calm tile today; perhaps the hand-wired biome additions), the tool places it</td><td>ROSTER.invasiveAdded 9093; ROSTER.placeGroup 8913; apex scheduler 9009/9057</td><td>medium</td><td>to measure on the rig before relying on either path</td></tr>
<tr><td class='num'>6</td><td>Rig validation: the three region19 forts and a savage embark; unstocked species arrive in their season, breed, leave at the change; no leaks; FPS</td><td>season-run kit (DwarfCron scripts/season-run.py)</td><td>runs</td><td>save each chunk (the fast-step hang)</td></tr>
</tbody></table></div>
<h3>Questions the build needs answered</h3>
<ul class="find">
<li><b>A new draw every year, or the same year repeated?</b> castYear runs at enable and on a rebuild, not at the new year (your 9 Oct ruling: no
year-to-year variety). Building the 28 casts at each new year is a one-line hook at the year change, and the x0.01 reuse count restarts with it.</li>
<li><b>What happens to created entries when the tool is turned off?</b> Removing them returns the save to DF's own stocking; keeping them leaves the
new species in the world.</li>
<li><b>Freshwater feature entries.</b> Lake, river and pool species live on water-feature entries, which the engine cannot create yet. The ocean is
easier: DF keeps sea life on land entries, which addNewSpecies already makes.</li>
<li><b>The hand-wired biome additions</b> (audit above): whether DF sends a wave from a created entry for a species whose raws do not name the biome
decides between an entry and placement.</li>
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
