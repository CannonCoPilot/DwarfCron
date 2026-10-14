#!/usr/bin/env python3
"""castsim.design_report: the Cast Pipeline Trace page for the 9 Oct-evening design, from data/castsim/design.json
(design_run.py) -> data/castsim/cast-pipeline-v2.html. Styles and the table sort/filter enhancer are report.py's."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import report  # noqa: E402
import crowd_assets  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/castsim/design.json'
OUT = ROOT / 'data/castsim/cast-pipeline-v2.html'
SEASONS = ['Spring', 'Summer', 'Autumn', 'Winter']

ENHANCER = report.JS[report.JS.index('// every table:'):report.JS.index('\nconst SEASONS=')]

CSS_EXTRA = """
:root{--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#e87ba4;--s6:#008300;--s7:#4a3aa7;--s8:#e34948;--s0:#9aa59f}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#008300;--s7:#9085e9;--s8:#e66767;--s0:#5f6b66}}
:root[data-theme="dark"]{--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#008300;--s7:#9085e9;--s8:#e66767;--s0:#5f6b66}
.web{position:relative;background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:10px 12px}
.webscroll{overflow-x:auto}.webscroll svg{display:block;min-width:640px;width:100%;height:auto}
.web .row{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:4px 0}
.web .row>label{font:600 .7rem var(--mono);text-transform:uppercase;letter-spacing:.05em;color:var(--muted);min-width:5.5em}
.tog{font:inherit;font-size:.8rem;border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:999px;padding:2px 9px;cursor:pointer;display:inline-flex;gap:5px;align-items:center}
.tog[aria-pressed="false"]{opacity:.45;text-decoration:line-through}.tog:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.sw{width:10px;height:10px;border-radius:50%;display:inline-block}
.wtip{position:absolute;pointer-events:none;background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:7px 9px;font-size:.8rem;box-shadow:0 4px 14px rgba(0,0,0,.18);max-width:300px;display:none;z-index:5}
.wtip b{font-family:var(--mono);font-size:.78rem}

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
const PAL=['var(--s1)','var(--s2)','var(--s3)','var(--s4)','var(--s5)','var(--s6)','var(--s7)','var(--s8)'];
const webState={color:'slot',hidden:{slot:new Set(),season:new Set(),biome:new Set()}};
const pretty=b=>b.toLowerCase().replace(/_/g,' ');
function webData(ex,L){
  const sp=ex.species, nodes={}, edges={};
  const node=t=>nodes[t]||(nodes[t]={t,slot:new Set(),season:new Set(),biome:[...new Set((sp[t].b||[]))],vermin:false,eats:new Set(),eatenBy:new Set()});
  SEASONS.forEach(s=>{const c=ex.casts[L+'|'+s];if(!c)return;
    c.members.forEach(([t,sl])=>{const n=node(t);n.slot.add(sl==='swimmer'?'amphib or aquatic':sl);n.season.add(s);});
    c.vermin.forEach(([t])=>{const n=node(t);n.slot.add('vermin');n.season.add(s);n.vermin=true;});
    c.edges.forEach(([a,b])=>{const k=a+'>'+b;(edges[k]=edges[k]||{source:a,target:b,season:new Set()}).season.add(s);});});
  const ns=Object.values(nodes);
  ns.forEach(n=>{const sl=[...n.slot];n.tier=sl.includes('apex')?3:(sl.some(x=>x==='meso'||x==='sentient')?2:(n.vermin&&sl.length===1?0:(sp[n.t].r==='predator'?2:1)));});
  const es=Object.values(edges).filter(e=>nodes[e.source]&&nodes[e.target]);
  es.forEach(e=>{nodes[e.source].eats.add(e.target);nodes[e.target].eatenBy.add(e.source);});
  const sk=slotKey(ex,L), order={slot:[...Object.keys(M.slots[sk]).filter(x=>x!=='_vermin').map(x=>x==='swimmer'?'amphib or aquatic':x),'vermin'],season:SEASONS,
    biome:[...new Set(ns.flatMap(n=>n.biome))].sort()};
  return {nodes:ns,edges:es,order};
}
function colorOf(dim,order,v){const i=order[dim].indexOf(v);return i>=0&&i<8?PAL[i]:'var(--s0)';}
function renderWeb(ex,L){
  const host=document.getElementById('web');
  if(!window.d3){host.innerHTML='<p class="note">The graph needs d3 (cdn.jsdelivr.net), which did not load.</p>';return;}
  const {nodes,edges,order}=webData(ex,L);
  if(!nodes.length){host.innerHTML='<p class="note">No cast on this layer.</p>';return;}
  // layered layout: four bands (apex, meso and predators, prey, vermin); within a band species are spread evenly and ordered
  // by the mean position of their links (down, up, down), which keeps predator-prey lines short and crossings few
  const W=960,bandH=125,R=9,top=34,H=top+3*bandH+40;
  const band=[3,2,1,0].map(t=>nodes.filter(n=>n.tier===t));
  const so=order.slot;
  band.forEach(b=>b.sort((a,c)=>so.indexOf([...a.slot][0])-so.indexOf([...c.slot][0])||a.t.localeCompare(c.t)));
  const place=b=>{const n=b.length,x0=140,x1=W-50;b.forEach((d,i)=>{d.x=n===1?(x0+x1)/2:x0+i*(x1-x0)/(n-1);});};
  band.forEach(place);
  const byT0=Object.fromEntries(nodes.map(n=>[n.t,n]));
  const mean=(d,set)=>{const xs=[...set].map(t=>byT0[t]).filter(Boolean).map(o=>o.x);return xs.length?xs.reduce((a,c)=>a+c,0)/xs.length:d.x;};
  const sweep=(ix,useUp)=>{const b=band[ix];b.forEach(d=>d.k=mean(d,useUp?d.eatenBy:d.eats));b.sort((a,c)=>a.k-c.k||a.t.localeCompare(c.t));place(b);};
  [1,2,3].forEach(i=>sweep(i,true));[2,1,0].forEach(i=>sweep(i,false));[1,2,3].forEach(i=>sweep(i,true));
  band.forEach((b,i)=>b.forEach((d,j)=>{d.y=top+i*bandH+(b.length>9?(j%2?16:-16):0);}));
  const labelled=d=>d.tier===3||band[3-d.tier].length<=7;
  const byT=Object.fromEntries(nodes.map(n=>[n.t,n]));
  const dims=['slot','season','biome'], dimName={slot:'trophic slot',season:'season',biome:'biome'};
  let h=`<div class="row"><label>Color by</label><div class="seg" id="webColor" role="group">${dims.map(d=>`<button type="button" data-v="${d}" aria-pressed="${webState.color===d}">${dimName[d]}</button>`).join('')}</div></div>`;
  dims.forEach(d=>{h+=`<div class="row" role="group" aria-label="Show ${dimName[d]}"><label>${d==='slot'?'Slots':d==='season'?'Seasons':'Biomes'}</label>${order[d].filter(v=>d!=='slot'||nodes.some(n=>n.slot.has(v))).map(v=>`<button type="button" class="tog" data-d="${d}" data-v="${esc(v)}" aria-pressed="${!webState.hidden[d].has(v)}">${webState.color===d?`<span class="sw" style="background:${colorOf(d,order,v)}"></span>`:''}${esc(d==='biome'?pretty(v):v)}</button>`).join('')}</div>`;});
  const bands=['apex','predators','prey','vermin'];
  h+=`<div class="webscroll"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Food web of the ${LN[L]} casts on ${esc(ex.name)}: ${nodes.length} species, ${edges.length} links. The year's roster table below lists the same species.">
    ${bands.map((b,i)=>`<text x="4" y="${top+i*bandH+4}" font-size="11" fill="var(--muted)" font-family="var(--mono)">${b}</text>${i<3?`<line x1="0" x2="${W}" y1="${top+i*bandH+bandH/2}" y2="${top+i*bandH+bandH/2}" stroke="var(--line)" stroke-dasharray="2 4"/>`:''}`).join('')}
    <g class="edges">${edges.map((e,i)=>`<line data-i="${i}" x1="${byT[e.source].x}" y1="${byT[e.source].y}" x2="${byT[e.target].x}" y2="${byT[e.target].y}" stroke="var(--muted)" stroke-width="1.2" stroke-opacity=".3"/>`).join('')}</g>
    <g class="nodes"></g></svg></div><div class="wtip" id="wtip"></div>
    <p class="note">${nodes.length} species and ${edges.length} predator→prey links over the year; a predator sits above its prey. A node split into sectors has more than one value (several seasons, slots or biomes). Hover a node for its links; click it to keep them lit.</p>`;
  host.innerHTML=h;
  const gN=d3.select(host).select('g.nodes'), arc=d3.arc().innerRadius(0).outerRadius(R).padAngle(.06);
  const vals=n=>[...n[webState.color]].sort((a,b)=>order[webState.color].indexOf(a)-order[webState.color].indexOf(b));
  const visible=n=>dims.every(d=>[...n[d]].some(v=>!webState.hidden[d].has(v)));
  const g=gN.selectAll('g').data(nodes).join('g').attr('transform',d=>`translate(${d.x},${d.y})`).attr('tabindex',0).style('cursor','pointer');
  g.each(function(d){const el=d3.select(this),v=vals(d);
    el.append('circle').attr('r',R+2).attr('fill','var(--surface)');
    if(v.length<=1)el.append('circle').attr('r',R).attr('fill',colorOf(webState.color,order,v[0]));
    else el.selectAll('path').data(d3.pie().value(1).sort(null)(v)).join('path').attr('d',arc).attr('fill',p=>colorOf(webState.color,order,p.data));
    el.append('text').attr('y',d.tier===3?-(R+6):R+13).attr('text-anchor','middle').attr('font-size',10.5).attr('fill','var(--ink)').attr('font-family','var(--mono)')
      .attr('stroke','var(--surface)').attr('stroke-width',3).attr('paint-order','stroke')
      .attr('class','lbl').text(d.t.toLowerCase().replace(/_/g,' ')).style('display',labelled(d)?null:'none');});
  let pinned=null;
  const tip=host.querySelector('#wtip'), lines=host.querySelectorAll('g.edges line');
  function paint(focus){
    const vis=new Map(nodes.map(n=>[n.t,visible(n)]));
    g.style('display',d=>vis.get(d.t)?null:'none').style('opacity',d=>!focus||d===focus||focus.eats.has(d.t)||focus.eatenBy.has(d.t)?1:.25);
    g.select('.lbl').style('display',d=>(focus?(d===focus||focus.eats.has(d.t)||focus.eatenBy.has(d.t)):labelled(d))?null:'none');
    edges.forEach((e,i)=>{const on=vis.get(e.source)&&vis.get(e.target)&&[...e.season].some(s=>!webState.hidden.season.has(s));
      const hot=focus&&(e.source===focus.t||e.target===focus.t);
      lines[i].style.display=on?'':'none';lines[i].setAttribute('stroke',hot?'var(--ink)':'var(--muted)');lines[i].setAttribute('stroke-opacity',hot?'.85':(focus?'.08':'.3'));});
  }
  function show(d,ev){
    const box=host.getBoundingClientRect();
    tip.innerHTML=`<b>${esc(d.t)}</b><br>${[...d.slot].map(esc).join(', ')} · ${[...d.season].join(', ')}<br><span class="note">${d.biome.map(pretty).join(', ')||'-'}</span><br>eats ${d.eats.size} · eaten by ${d.eatenBy.size}`;
    tip.style.display='block';tip.style.left=Math.min(box.width-310,Math.max(0,ev.clientX-box.left+12))+'px';tip.style.top=(ev.clientY-box.top+12)+'px';
  }
  g.on('mouseenter',(ev,d)=>{if(!pinned)paint(d);show(d,ev);}).on('mousemove',(ev,d)=>show(d,ev)).on('mouseleave',()=>{tip.style.display='none';if(!pinned)paint(null);})
   .on('click',(ev,d)=>{pinned=pinned===d?null:d;paint(pinned);})
   .on('focus',function(ev,d){const r=this.getBoundingClientRect();paint(d);show(d,{clientX:r.x,clientY:r.y});}).on('blur',()=>{tip.style.display='none';paint(pinned);});
  paint(null);
  host.querySelectorAll('#webColor button').forEach(b=>b.onclick=()=>{webState.color=b.dataset.v;renderWeb(ex,L);});
  host.querySelectorAll('.tog').forEach(b=>b.onclick=()=>{const H=webState.hidden[b.dataset.d];H.has(b.dataset.v)?H.delete(b.dataset.v):H.add(b.dataset.v);b.setAttribute('aria-pressed',!H.has(b.dataset.v));paint(pinned);});
}
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
  renderWeb(ex,L);
  document.querySelectorAll('.layername').forEach(e=>e.textContent=LN[L]);
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
        'fresh:pool': 'murky pools only: small lake and river species (up to 20,000 cm³) and vermin; raws must reach fresh water; the fish slot also takes fish and amphibious vermin',
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


REG = lambda r: f"{r['sav']} {r['align']}"


def roll_summary(meta):
    import collections
    c = collections.Counter((r['sav'], r['align'], r['layer'], r['kind']) for r in meta['audit']['roll'])
    kinds = ['ordinary', 'GOOD', 'EVIL', 'giant', 'animal person', 'extinct']
    rows = []
    for sav, al in meta['audit']['conditions']:
        for L in ('ground', 'flying', 'ocean', 'fresh'):
            n = [c[(sav, al, L, k)] for k in kinds]
            rows.append(f"<tr><td>{sav}</td><td>{al}</td><td>{LN[L]}</td>" + ''.join(f"<td class='num'>{x or ''}</td>" for x in n) + f"<td class='num'><b>{sum(n)}</b></td></tr>")
    return ("<div class='tbl'><table><thead><tr><th data-t='cat'>savagery</th><th data-t='cat'>alignment</th><th data-t='cat'>layer</th>"
            + ''.join(f"<th class='num' data-t='num'>{k}</th>" for k in kinds) + "<th class='num' data-t='num'>all</th></tr></thead><tbody>" + ''.join(rows) + '</tbody></table></div>')


def roll_table(meta):
    rows = ''.join(f"<tr><td class='mono'>{esc(r['t'])}</td><td>{r['sav']}</td><td>{r['align']}</td><td>{LN[r['layer']]}</td><td>{esc(r['kind'])}</td>"
                   f"<td class='num'>{r['n']}</td><td>{''.join(f'<span class=sp>{esc(b)}</span>' for b in r['biomes'])}</td></tr>" for r in meta['audit']['roll'])
    return ("<div class='tbl' style='max-height:520px'><table><thead><tr><th>species</th><th data-t='cat'>savagery</th><th data-t='cat'>alignment</th>"
            "<th data-t='cat'>layer</th><th data-t='cat'>kind</th><th class='num' data-t='num'>biomes</th><th data-t='multi'>biome list</th></tr></thead><tbody>" + rows + '</tbody></table></div>')


def audit_table(meta):
    rows = []
    for r in meta['audit']['rows']:
        tr = sorted({t for p in r['seasons'] for t in p['true']}); lo = sorted({t for p in r['seasons'] for t in p['local']})
        flag = 'short' if r['min_true'] < 2 else 'ok'
        prop = ', '.join(f"{p['t']} ({p['kind']})" for p in r['proposal'])
        rows.append(f"<tr><td class='mono'>{esc(r['biome'])}</td><td>{LN[r['layer']]}</td><td>{r['sav']}</td><td>{r['align']}</td><td class='num'>{r['n']}</td>"
                    f"<td><span class='chip {'bad' if flag == 'short' else 'ok'}'>{flag}</span></td><td class='num'>{r['min_true']}</td>"
                    f"<td>{''.join(f'<span class=sp>{esc(t)}</span>' for t in tr) or '<span class=note>none</span>'}</td>"
                    f"<td>{''.join(f'<span class=sp>{esc(t)}</span>' for t in lo)}</td><td class='note'>{esc(prop)}</td>"
                    f"<td class='num'>{r['min_after'] if r['proposal'] else ''}</td></tr>")
    return ("<div class='tbl' style='max-height:560px'><table><thead><tr><th data-t='cat'>biome</th><th data-t='cat'>layer</th><th data-t='cat'>savagery</th>"
            "<th data-t='cat'>alignment</th><th class='num' data-t='num'>potential cast members</th><th data-t='cat'>verdict</th>"
            "<th class='num' data-t='num'>fewest true apexes in a season</th><th data-t='multi'>true apexes</th><th data-t='multi'>local apexes</th>"
            "<th>automatic proposal</th><th class='num' data-t='num'>fewest, with it</th></tr></thead><tbody>" + ''.join(rows) + '</tbody></table></div>')


def candidate_table(meta):
    rows = []
    for r in meta['audit']['rows']:
        if r['min_true'] >= 2: continue
        chosen = {p['t'] for p in r['proposal']}
        for kind, lst in (('promote', r['promote']), ('wire', r['wire'])):
            for c in lst:
                k = 'promote (local apex)' if c.get('local') else kind
                rows.append(f"<tr><td class='mono'>{esc(r['biome'])}</td><td>{LN[r['layer']]}</td><td>{r['sav']} {r['align']}</td><td class='mono'>{esc(c['t'])}</td>"
                            f"<td>{k}</td><td class='num'>{c['score']}</td><td class='num'>{c['g']:,}</td><td>{'proposed' if c['t'] in chosen else ''}</td>"
                            f"<td class='note'>{esc(', '.join(c.get('homes', [])))}</td></tr>")
    return ("<div class='tbl' style='max-height:520px'><table><thead><tr><th data-t='cat'>biome</th><th data-t='cat'>layer</th><th data-t='cat'>region</th>"
            "<th>candidate</th><th data-t='cat'>kind</th><th class='num' data-t='num'>score</th><th class='num' data-t='num'>group size cm³</th>"
            "<th data-t='cat'>in the proposal</th><th>its biomes (wire)</th></tr></thead><tbody>" + ''.join(rows) + '</tbody></table></div>')


def order_table(meta):
    ob = meta['order_bias']
    rows = ''
    for k, name in (('season', 'Spring first'), ('random', 'random order')):
        a, n = ob[k]['all']; p, pn = ob[k]['pack']
        rows += (f"<tr><td>{name}</td>" + ''.join(f"<td class='num'>{x}%</td>" for x in p) + f"<td class='num'>{pn:,}</td>"
                 + ''.join(f"<td class='num'>{x}%</td>" for x in a) + f"<td class='num'>{ob[k]['concentration']}%</td></tr>")
    return ("<div class='tbl'><table><thead><tr><th data-t='cat'>build order</th>" + ''.join(f"<th class='num' data-t='num'>pack hunters {s}</th>" for s in SEASONS)
            + "<th class='num' data-t='num'>pack places</th>" + ''.join(f"<th class='num' data-t='num'>all {s}</th>" for s in SEASONS)
            + "<th class='num' data-t='num'>concentration</th></tr></thead><tbody>" + rows + '</tbody></table></div>')


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


def stats(data, meta_roll=()):
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
                roll_wn_ground=sum(1 for r in meta_roll if (r['sav'], r['align'], r['layer']) == ('wild', 'neutral', 'ground')),
                roll_wn_temperate=sum(1 for r in meta_roll if (r['sav'], r['align'], r['layer']) == ('wild', 'neutral', 'ground')
                                      and any(('TEMPERATE' in b or b in ('FOREST_TAIGA', 'TUNDRA', 'GLACIER', 'MOUNTAIN')) for b in r['biomes'])),
                pools_cast=sorted({t for s in SEASONS for t, _ in by['pools']['casts'][f'fresh|{s}']['members']}))


RUNS = ROOT / 'data/season-run'
FORT = {'L': 'Lake fort', 'O': 'Ocean-shore fort', 'B': 'Brook fort'}
RUN_FORTS = {   # a run's arms in table order, and their names (X5v75: the region-type forts of 13 Oct)
    'X7v75': [('B', 'Brook'), ('X', 'Extinct wilds'), ('E', 'Evil coast, sheltered'), ('G', 'Good coast'), ('S', 'Small savage lake'),
              ('U', 'Untamed wilds lake'), ('J', 'Joyous wilds coast'), ('T', 'Terrifying coast')],
    'X5v75': [('G', 'Good coast'), ('E', 'Evil coast'), ('S', 'Small savage lake'), ('U', 'Untamed wilds lake'),
              ('J', 'Joyous wilds coast'), ('T', 'Terrifying coast')],
}


RERUN = {('X5v75', 'E'): 'X5v75e',
         # X7v75: the continuation (X7v75b) ran G S U J T; the reruns on the fixes found (X7v75c) ran B E G J T -- the newest cell wins
         **{('X7v75', a): ['X7v75b', 'X7v75c'] for a in 'GJ'}, **{('X7v75', a): 'X7v75b' for a in 'SU'},
         ('X7v75', 'E'): 'X7v75c', ('X7v75', 'B'): ['X7v75c', 'X7v75d'], ('X7v75', 'T'): ['X7v75b', 'X7v75c', 'X7v75d', 'X7v75e']}   # the rerun that played 45k ticks; X5v75e2 (50 dwarves) was stopped at its first loss   # an arm rerun under its own run name (the evil coast, after its first run hung)


def cell_dir(run, a):
    """the folder holding a run's arm: its rerun's, once that has a cell"""
    rs = RERUN.get((run, a)) or []
    for r in reversed([rs] if isinstance(rs, str) else rs):
        if RUNS.joinpath(r, a, 'rep1', 'cell.json').exists():
            return RUNS.joinpath(r, a, 'rep1')
    return RUNS.joinpath(run, a, 'rep1')


def run_arms(run):
    return RUN_FORTS.get(run) or [(a, FORT[a]) for a in 'LOB']


def rig_cells(run='X3v75c'):
    out = {}
    for a, _ in run_arms(run):
        f = cell_dir(run, a) / 'cell.json'
        if f.exists():
            J = json.loads(f.read_text())
            led = cell_dir(run, a) / 'ledger.tsv'
            J['keepalive'] = led.read_text(encoding='cp437').count('keep-alive') if led.exists() else None
            out[a] = J
    return out


def run_tables(run):
    """the result tables of one season-run, any arms: {'C', 'tot', 'tbl', 'ltbl', 'ytbl', 'stbl', 'arms'}"""
    C = rig_cells(run)
    arms = [a for a, _ in run_arms(run) if a in C]
    FORT = dict(run_arms(run))
    yes = "<span class='chip ok'>pass</span>"
    no = "<span class='chip bad'>fail</span>"
    rows, tot = [], {'arr': 0, 'made': 0, 'cave': 0, 'ka': 0, 'hang': 0}
    for a in arms:
        J = C[a]; A, R = J['analysis'], J['run']
        ce = A.get('created_entries') or {}
        arr = ce.get('arrived') or {}
        made = sum(arr.values()); cave = sum(v for k, v in arr.items() if '(cavern)' in k)
        crit = A.get('criteria', {})
        tot['arr'] += A['managed_arrivals']; tot['made'] += made; tot['cave'] += cave; tot['ka'] += J['keepalive'] or 0
        tot['hang'] += len(R.get('hangs', []))
        st = R.get('status', 'OK')
        ran = (A.get('ticks') or [0, 0])
        verd = ((yes if A.get('verdict') == 'PASS' else no) if st == 'OK' else
                f"<span class='chip bad'>not finished</span> <span class=small>{'passed' if A.get('verdict') == 'PASS' else 'failed'} "
                f"its {(ran[1] - ran[0]) // 1000}k ticks</span>")
        rows.append(f"<tr><td>{FORT[a]}</td><td>{verd}</td>"
                    f"<td class='num'>{A['managed_arrivals']}</td><td class='num'>{made}</td><td class='num'>{cave}</td>"
                    f"<td class='num'>{A['offcast_late']}</td><td class='num'>{len(A['in_cast_sendoffs'])}</td>"
                    f"<td class='num'>{len(A.get('depth_sendoffs', []))}</td><td class='num'>{A.get('cavern_wrong_depth_late', 0)}</td>"
                    f"<td class='num'>{len(A['sendoffs_not_left'])}</td><td>{yes if A.get('reserve', {}).get('conserved') else no}</td>"
                    f"<td class='num'>{J['keepalive']}</td><td class='num'>{len(R.get('hangs', []))}</td></tr>")
    tbl = ("<div class='tbl'><table><thead><tr><th data-t='cat'>fort</th><th data-t='cat'>verdict</th><th class='num' data-t='num'>arrivals</th>"
           "<th class='num' data-t='num'>from created entries</th><th class='num' data-t='num'>of which in caverns</th>"
           "<th class='num' data-t='num'>off-cast, later than a day</th><th class='num' data-t='num'>in-cast groups sent off</th>"
           "<th class='num' data-t='num'>sent off for depth</th><th class='num' data-t='num'>cavern arrivals at a wrong depth</th>"
           "<th class='num' data-t='num'>sent off, still here at 10 days</th><th data-t='cat'>reserve kept</th>"
           "<th class='num' data-t='num'>keep-alive writes</th><th class='num' data-t='num'>DF hangs</th></tr></thead><tbody>"
           + ''.join(rows) + '</tbody></table></div>')
    # arrivals by layer and season, all forts
    # the seasons the run reached, in calendar order (a full-year run adds Winter)
    seasons = [s for s in SEASONS if any(k.endswith(' ' + s) for a in arms for k in C[a]['analysis']['arrivals'])]
    lrows = []
    for a in arms:
        ar = C[a]['analysis']['arrivals']
        for L in ('land', 'water', 'cavern'):
            cells = []
            for s in seasons:
                c = ar.get(f'{L} {s}', {})
                n = sum(c.values()); off = n - c.get('in_cast', 0) - c.get('in_cast_other_layer', 0)
                cells.append(f"<td class='num' data-v='{n}'>{n}{f' <span class=small>({off} off-cast, early)</span>' if off else ''}</td>")
            lrows.append(f"<tr><td>{FORT[a]}</td><td><span class='chip {L}'>{L}</span></td>{''.join(cells)}</tr>")
    ltbl = ("<div class='tbl'><table><thead><tr><th data-t='cat'>fort</th><th data-t='cat'>layer</th>"
            + ''.join(f"<th class='num' data-t='num'>{s}</th>" for s in seasons) + '</tr></thead><tbody>' + ''.join(lrows) + '</tbody></table></div>')
    # a run that crosses a new year: the casts are built once, so the year turn must change nothing
    yrows = []
    for a in arms:
        Y = C[a]['analysis'].get('year_turn')
        if not Y:
            continue
        na = Y.get('new_year_arrivals') or {}
        yrows.append(f"<tr><td>{FORT[a]}</td><td>{yes if Y['casts_unchanged'] else no}</td>"
                     f"<td class='num'>{len(Y['cast_builds_after_start'])}</td><td class='num'>{na.get('in_cast', 0)}</td>"
                     f"<td class='num'>{na.get('off_cast', 0)}</td></tr>")
    ytbl = ("<h3>Across the new year</h3><p>The casts are built once at embark and kept: the year turn must rebuild nothing, and the new year's "
            "arrivals must be the casts of their season.</p><div class='tbl'><table><thead><tr><th data-t='cat'>fort</th>"
            "<th data-t='cat'>casts the same at the end</th><th class='num' data-t='num'>cast builds after the start</th>"
            "<th class='num' data-t='num'>new-year arrivals in cast</th><th class='num' data-t='num'>off cast</th></tr></thead><tbody>"
            + ''.join(yrows) + '</tbody></table></div>') if yrows else ''
    # created-entry arrivals by species
    sp = {}
    for a in arms:
        for k, v in ((C[a]['analysis'].get('created_entries') or {}).get('arrived') or {}).items():
            tok, _, lay = k.partition(' (')
            sp.setdefault((tok, lay.rstrip(')')), {})[a] = v
    srows = ''.join(f"<tr><td class='mono'>{esc(t)}</td><td><span class='chip {lay}'>{lay}</span></td>"
                    + ''.join(f"<td class='num'>{d.get(a, '')}</td>" for a in arms) + f"<td class='num'>{sum(d.values())}</td></tr>"
                    for (t, lay), d in sorted(sp.items(), key=lambda x: -sum(x[1].values())))
    stbl = ("<div class='tbl' style='max-height:420px'><table><thead><tr><th>species</th><th data-t='cat'>layer</th>"
            + ''.join(f"<th class='num' data-t='num'>{FORT[a].lower()}</th>" for a in arms)
            + "<th class='num' data-t='num'>all</th></tr></thead><tbody>" + srows + '</tbody></table></div>')
    return {'C': C, 'tot': tot, 'tbl': tbl, 'ltbl': ltbl, 'ytbl': ytbl, 'stbl': stbl, 'arms': arms}


def rig_section(run='X3v75c'):
    T = run_tables(run)
    if len(T['arms']) < 3:
        return ''
    C, tot, tbl, ltbl, ytbl, stbl = T['C'], T['tot'], T['tbl'], T['ltbl'], T['ytbl'], T['stbl']
    return f"""
<h2 id="rig">On the rig: a full year on v7.5 (12 Oct)</h2>
<p>The design on this page is the engine (seasonal-wildlife v7.5, branch v7.5-fullpool). It ran on the three region19 forts for a whole year, from early
spring through winter and 17 days into the next year, one replicate each, with DF restarted for every fort: run X4v75b, on the code after the review
fixes. Earlier runs (X3v75 to X3v75c, spring to autumn) found and fixed four bugs (below). The rules applied on 13 Oct (<a href="#applied">below</a>)
came after this run; they ran next, on the region-type forts (<a href="#regions">X5v75</a>).</p>
<div class="grid2">
<div class="card"><h4>The year turn changes nothing</h4><p><span class="big">3 / 3</span> forts ended with the casts they began with, none rebuilt at
the new year, and every arrival of the new year ({sum(C[a]['analysis']['year_turn']['new_year_arrivals'].get('in_cast', 0) for a in T['arms'])} in all) was cast for its season.</p></div>
<div class="card"><h4>Two pass, one fault found and fixed</h4><p><span class="big">2 / 3</span> pass every check. The lake fort's one fault: a cavern
group sent off at the autumn change was released again 1.1 days later at a depth its species is not cast at. The release step now skips sent-off groups.</p></div>
<div class="card"><h4>Species DF never stocked arrive</h4><p><span class="big">{tot['made']}</span> arrivals came from population entries the tool
created, {tot['cave']} of them in the caverns. {tot['arr']:,} managed arrivals in all.</p></div>
<div class="card"><h4>No DF hangs in a year</h4><p><span class="big">{tot['hang']}</span> hangs on three forts over about 1.1 million ticks. The cavern
keep-alive guard wrote {tot['ka']} times.</p></div>
</div>
{tbl}
<p class="note">Arrivals are animals entering the map in the managed layers (births included). "Off-cast, later than a day" is the fault the run looks for:
a wave DF picks just before a change may land just after it, so the first day is allowed. Sponges are left out: they are placed scenery, never cast.</p>
<h3>Arrivals by layer and season</h3>
<p>Every arrival on every layer was a species cast for that season, apart from the few marked, all inside the first day after a change.</p>
{ltbl}
{ytbl}
<h3>Arrivals from the entries the tool created</h3>
<p>Species DF had not stocked on the fort, drawn by DF itself from the entries the tool made for them (and, for the apexes, placed by the tool's scheduler).
Each entry is masked by its cast's seasons like DF's own and removed when the tool is turned off.</p>
{stbl}
<h3>What the runs found</h3>
<div class='tbl'><table><thead><tr><th data-t='cat'>run</th><th>result</th><th>cause and fix</th></tr></thead><tbody>
<tr><td>X3v75</td><td>stopped after the lake fort</td><td class='note'>Each cavern's mask was lost at every load (the saved casts dropped their version on reload), so every
depth stayed open: 10 animals came in through a cavern their species was not cast in. Fixed; and a species DF stocked in one cavern but cast in another
now gets an entry at the cast depth.</td></tr>
<tr><td>X3v75b</td><td>ocean pass; lake one fault; brook hung four times</td><td class='note'><b>The tool could freeze DF.</b> DF picks a cavern wave by raw FREQUENCY among one
region tile's stocked animals in one cave; when every one reads 0 the pick never ends and the simulation stops while the screen still draws. A guard now
keeps one species of each such group at 1. <br><b>A pike in autumn</b>, cast for spring and winter: created entries for freshwater species were filed where
no season reached them; each now follows the cast it was made for.<br><b>No sponges on the ocean fort</b>: the sponge pass looked only for water-feature
entries, which sea life does not have. Fixed.</td></tr>
<tr><td>X3v75c</td><td>all three pass, no hangs</td><td class='note'>Spring to early autumn on the final code of the build.</td></tr>
<tr><td>X4v75b</td><td>full year: ocean and brook pass; lake one fault</td><td class='note'><b>A sent-off group released again.</b> A DF wave the cavern gate holds
back is released later, oldest first; one sent off by the season change could still be picked, so a draltha, cast only in cavern 1 for autumn, was
released in cavern 2 1.1 days in (two more on the ocean fort, inside the day). The release now skips sent-off groups, as it skipped trimmed ones.
The analyser also scored two albatross groups "not left in 10 days": albatrosses are cast on the water layer in summer and gated as land, so the
cast's own birds stayed on the map; the tool's leave check found none of the sent-off ones still there. Scored now as in the cast.</td></tr>
</tbody></table></div>
<h3>Not yet seen on the rig</h3>
<ul class="find">
<li><b>The 13 Oct rules and the savage, evil and good embarks</b> ran next, in X5v75: <a href="#regions">the region-type forts</a>.</li>
<li><b><code>off</code> after a long run.</b> Removing created entries was checked once (45 entries, 45k ticks); not yet after a year of their animals
breeding on the map.</li>
</ul>
"""


CROWD_FORTS = [   # (run, arm, name) shown in the crowdedness charts, in selector order
    ('X4v75b', 'L', 'Lake'), ('X4v75b', 'O', 'Ocean shore'), ('X4v75b', 'B', 'Brook'),
    ('X5v75', 'G', 'Good coast'), ('X5v75', 'E', 'Evil coast'), ('X5v75', 'S', 'Small savage lake'),
    ('X5v75', 'U', 'Untamed wilds lake'), ('X5v75', 'J', 'Joyous wilds coast'), ('X5v75', 'T', 'Terrifying coast'),
]


ERAS = ('SILURIAN_', 'DEVONIAN_', 'CARBONIFEROUS_', 'PERMIAN_', 'TRIASSIC_', 'JURASSIC_', 'CRETACEOUS_', 'CENOZOIC_')
SPECIALS = {'HARPY', 'NIGHTWING', 'GRIMELING', 'UNICORN', 'OGRE', 'GIANT_MANTIS', 'TIGERFISH', 'ANACONDA', 'GIANT_SPONGE'}
REGION_NOTES = {   # X5v75: what each fort found, by arm (filled in as the forts are analysed)
    'G': "<b>68 river otters out of season.</b> The casts were built before the water scan had registered the fort's water, so the fort had no "
         "freshwater cast: the otter never rested and kept the old roster's summer in its murky pools. Fixed twice over: a layer with no cast now rests "
         "its species, and the engine builds a missing layer's four casts when the scan later finds that water (13 Oct, your word).",
    'E': "<b>The fort was lost, three times.</b> Infernal ash, the evil coast's weather, turns every dwarf it catches into an infernal ash zombie. "
         "A fort with no citizen left stops DF's clock while DF still answers, so the runner read it as a hang and reloaded. The first run "
         "stopped at about tick 70,000 (and its reload missed the save, a loader bug fixed since). A rerun passed every check for 45,000 ticks of play, "
         "then was lost at tick 103,400, early summer, with 4 dwarves left, all undead. The same tile embarked again with 50 dwarves was lost by about tick 100,000. "
         "The runner now reports a lost fort as LOST. Before the ash, an ogre came in from the tool's entries on both runs, and two harpies on the first "
         "(the table shows the rerun); the giant mantis was wired as the calm evil land's apex.",
    'S': "<b>Extinct species arrive on a small savage region.</b> The ISOLATED fix (a world region of five tiles or fewer) let DF's own extinct stock "
         "through: two Hibbertopterus species, Eryops and Jaekelopterus. The pygmy mammoth was cast for autumn, the seed of that land cast, but no group came.",
    'U': "<b>Passes once the analyser knows stand-ins.</b> Four animal-person populations ran out during the year; the engine's stand-in rule filled each "
         "empty slot with a species cast for another season (sparrow and grackle men). The analyser had scored their send-offs as off-cast and their "
         "species as 'not left'; it now scores them as in the cast for their stand-in season.",
    'J': "<b>Passes; no sponges on its savage ocean.</b> The ocean was frozen at the load and thawed by summer (2, then 11 bodies), so the sea casts "
         "arrived: orcas, a sea serpent, a gigantic squid, giant nautiluses. The sponge pass, though, read a tile list taken once at the load and said "
         "'no ocean on the map' all year; it now reads the water again when the scan finds it changed. Two stand-ins in the sea (a sea serpent for the "
         "megalodon man, an octopus for Psephoderma) were logged under land and first scored as off-cast; the analyser now matches a stand-in on any layer.",
    'T': "<b>78 river otters and otter men out of season,</b> the good coast's fault again: the ocean and its fresh pools were frozen at the build "
         "and registered only at the summer thaw, so there was no freshwater cast. Fixed (above), not yet on the rig for this run. Otherwise the terror "
         "casts came: Jurassic and Permian hunters on the ground (afrovenator, anteosaurus, utahraptor), giant roaches all winter. The apex fliers "
         "barely showed: spring's giant mantis came once, as one DF wave, and the land gate sent it off at once (six groups over a cap of five); the "
         "winter harpy never came. Nine send-offs first read 'not left in 10 days': every sent-off group did "
         "leave, and the species' ungrouped cavern residents stayed; the analyser now counts grouped units only.",
}


def region_section(run='X5v75', notes_by=None, sid='regions', title='On the rig: the region-type forts (13 Oct)', intro=None):
    """the region-type forts: one table of checks, one of what reached the map, and each fort's finding"""
    notes_by = REGION_NOTES if notes_by is None else notes_by
    T = run_tables(run)
    if not T['arms']:
        return ''
    names = dict(run_arms(run))
    arms = [a for a, _ in run_arms(run) if a in T['C']]

    def kind(tok):
        if tok.endswith('_MAN') or '_MAN_' in tok:
            return 'animal people'
        if tok.startswith(ERAS):
            return 'extinct'
        if tok in SPECIALS:
            return 'good, evil and bug apexes'
        if tok.startswith(('GIANT_', 'GIANT ')) or tok.endswith('_GIANT'):
            return 'giants'
        return None
    KINDS = ('animal people', 'giants', 'extinct', 'good, evil and bug apexes')
    rows = []
    for a in arms:
        ev = cell_dir(run, a) / 'events.tsv'
        if not ev.exists():
            continue
        got = {k: {} for k in KINDS}
        for ln in ev.read_text(encoding='cp437').splitlines()[1:]:
            f = ln.split('\t')
            if len(f) > 9 and f[1] == 'ARRIVE' and f[9] in ('land', 'water', 'surface'):
                k = kind(f[3])
                if k:
                    got[k][f[3]] = got[k].get(f[3], 0) + 1
        cell = lambda d: ', '.join(f"{t.lower().replace('_', ' ')} <span class=small>{n}</span>" for t, n in sorted(d.items(), key=lambda x: -x[1])) or '<span class=small>none</span>'
        rows.append(f"<tr><td>{names[a]}</td>" + ''.join(f"<td>{cell(got[k])}</td>" for k in KINDS) + '</tr>')
    mtbl = ("<div class='tbl'><table><thead><tr><th data-t='cat'>fort</th>" + ''.join(f'<th>{k}</th>' for k in KINDS)
            + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')
    notes = ''.join(f"<tr><td>{names[a]}</td><td class='note'>{notes_by[a]}</td></tr>" for a in arms if a in notes_by)
    passed = sum(1 for a in arms if T['C'][a]['analysis'].get('verdict') == 'PASS' and T['C'][a]['run'].get('status', 'OK') == 'OK')
    intro = intro or ("a full year each on {n} forts embarked for the kinds of region the 13 Oct rules are about (good, evil, savage, joyous and terrifying "
                      "wilds, and a small savage patch that DF counts as isolated), one replicate each, on the engine with the 13 Oct rules.")
    return f"""
<h2 id="{sid}">{title}</h2>
<p>Run {run}: {intro.format(n=len(arms))} <span class="big">{passed} / {len(arms)}</span> pass.
Arrivals are counted only on the surface layers below (land and water); the caverns' giant cave toads and olms are DF's ordinary stock.</p>
{T['tbl']}
<h3>What reached the map</h3>
{mtbl}
<h3>What each fort found</h3>
<div class='tbl'><table><thead><tr><th data-t='cat'>fort</th><th>finding</th></tr></thead><tbody>{notes}</tbody></table></div>
<h3>Arrivals by layer and season</h3>
{T['ltbl']}
{T['ytbl']}
<h3>Arrivals from the entries the tool created</h3>
{T['stbl']}
"""


X7_NOTES = {   # X7v75 (+ b, c, d): what each fort found, by arm (from the NOTES.md of each run)
    'B': "<b>The brook got no animals of its own</b> in its first year: every 'water' arrival was an osprey DF sent. Its fresh casts held species too "
         "large for a brook (your 6 Oct cap, 10,000 cm³), and its one small species, the platypus, had only a land entry the water draw ignored. "
         "Fixed (the brook cap on the fresh cast; the water draw takes the season's water-cast species from land entries): the rerun drew platypus "
         "23 times, and frogs, turtles and beavers, into the brook and its 16 murky pools all year. It also put giant tree frogs (200,700 cm³) into "
         "the pools, so the draw now keeps pools to small creatures too. The table shows the last run, with the casts rebuilt on those rules: "
         "Diplocaulus and platypus every season (only two species fit a brook here), drawn into the brook and pools in all four seasons; its one "
         "flag is a giant platypus that walked in after the mid-season rebuild (pending).",
    'X': "<b>The walker fix holds for a whole year:</b> 49 extinct arrivals (ankylosaurus 10, kelenken 9, triceratops 9, kosmoceratops 7, "
         "megacerops 5, nodosaurus 4, allosaurus 2, torvosaurus, glyptodon, smilodon). One population ran out (a longnose gar); no stand-in passed "
         "the checks (the closest failed the guild check) and its slot stayed empty, as designed.",
    'E': "<b>The first full evil-coast year.</b> The first sheltered run was lost in autumn: a mink drawn into a pool was raised as an ash zombie, "
         "walked down the shelter's open stair and bit the mayor, and the infection took the fort. A hatch cover over the stair (animals cannot open "
         "it) and the rerun passed every check with the fort alive.",
    'G': "<b>One season change sent a cast species off:</b> a sturgeon drawn into the ocean from the summer cast was sent off the same day, because "
         "ocean species carry two keys and the check read the one not cast. Fixed. The rerun's one miss: a weasel sent off at the autumn change "
         "stood on the map's edge and did not vanish at day 8 when told to; it left on day 14 (pending).",
    'S': "<b>Passes.</b> 220 pauses and not one group sent off over a cap.",
    'U': "<b>No false exhaustion any more.</b> Last run this fort logged four animal-people populations as exhausted and brought in off-season "
         "stand-ins; this year it logged none, because those readings were waves on their way, not dead populations.",
    'J': "<b>Passes</b> on the rerun (the first run had the same sturgeon send-off as the good coast). One stand-in under the new checks: an "
         "octopus for a Triassic Psephoderma that ran out in autumn.",
    'T': "<b>The first full terrifying year, with the shelter sealed.</b> Terrifying land raises corpses, and the fort was lost three times: "
         "with 7 dwarves a reanimated stegosaurus killed the leader in spring; with 50, risen echidnas, utahraptors and storks overran them in "
         "summer; sheltered under a hatch, at nearly the same tick, because a risen echidna and velociraptor walked 50 tiles to the stair and down "
         "past the hatch while dwarves held it open going out for corpses. The fix locks the hatch, keeps every citizen in a burrow over the room, "
         "and takes refuse and corpses off the shelter stockpile. The rerun lived the year and passed every check, and nothing came through the "
         "hatch. It still lost 23 dwarves (50, then 55 with migrants, ending at 32): the fort's own horse starved in the sealed room, its corpse "
         "rose and killed 11 within a few days, and dwarves who died inside kept rising. Next: take the animals out before sealing (pending).",
}


def changes_section():
    """13 Oct afternoon and evening: the walker fix, the pauses, pools and brooks, exhaustion and stand-ins, the shelter"""
    def tbl(head, rows):
        return ("<div class='tbl'><table><thead><tr>" + ''.join(f"<th{' data-t=cat' if i == 0 else ''}>{h}</th>" for i, h in enumerate(head))
                + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f"<td{' class=num' if isinstance(c, (int, float)) else ''}>{c}</td>" for c in r) + '</tr>' for r in rows)
                + '</tbody></table></div>')
    walk = tbl(['cast slots whose species arrived (extinct-wilds fort)', 'before', 'after'],
               [['land-ground', '3 of 21', '9 of 21'], ['extinct', '1 of 10', '6 of 10'], ['spring', '1 of 7', '5 of 7']])
    probe = tbl(['25 days, cavern cap 1, same winter save', 'the old trim', 'the pause'],
                [['cavern waves (animals)', '82 (252)', '2 (17)'], ['groups sent off for being over the cap', 93, 0],
                 ['taken off the map (sent off, never left)', 5, 4], ['DF stalls', 'none', 'none']])
    sizes = tbl(['kind of species', 'species compared', "DF's entry per tile / the tool's (median, p10-p90)"],
                [['animal people', 120, '0.80 (0.40-1.20)'], ['giants', 82, '0.87 (0.47-1.20)'], ['other surface species', 293, '0.76 (0.44-1.16)']])
    return f"""
<h2 id="changes">Changes of 13 Oct (afternoon and evening)</h2>
<h3>Walkers and extinct animals: the missing arrivals</h3>
<p>DF sends a <b>walking</b> animal's wave only from the fort's own region tile; a flier also comes from the neighbouring tiles. The tool had put the
entries it creates on the first tile of the world region, usually a neighbour, so fliers came and walkers never did. Moving one kelenken entry onto the
fort's tile brought a group of three within 20 days. Entries now go on the fort's own tiles, also for walkers DF stocked only next door (bebb00d).
Before the fix, across nine forts, 97 of 241 ground cast slots and 16 of 64 extinct slots ever saw their species.</p>
{walk}
<p class=small>Arrivals after the fix: ankylosaurus 19, triceratops 9, kelenken 5, glyptodon 5, megaceros 3, torvosaurus 1.</p>
<h3>Caps pause arrivals; nothing is sent off</h3>
<p>Your rule: a cap stops new groups arriving and lets the groups on the map leave on their own timers. At a layer's cap every open population entry
of that layer gets DF's extinct flag, which alone stops a draw; stock and frequency are never touched. Land pauses as one layer (6b74260), each cavern
depth on its own (6245358). A paused layer reopens only two groups under its cap (414d494): reopening at the first group to leave let DF send two waves
within a day. The water bodies already worked this way (the tool draws water groups itself, only under each body's cap). The cavern pause was tested
before it was switched on:</p>
{probe}
<p>On the sheltered evil coast (X5v75e4, a full year): 62 land pause and resume lines, no land group sent off. On the brook fort (X7v75): 57 pauses,
6 that began one group over the cap (a wave already on its way), none two over, no send-offs.</p>
<h3>Murky pools (plan B) and brooks</h3>
<p>A murky pool is a subset of lake and river water: a small lake or river species (adult size up to 20,000 cm³) fits a pool, and a pool cast takes only
species whose raws reach fresh water; a DF water entry no longer lets an ocean species in (0127d7c). The brook fort's first year found the same gap in
brooks: its fresh casts held species too large for a brook (your 6 Oct cap, 10,000 cm³) and drew nothing, and its one small species, the platypus, had
only a land entry the water draw did not take. Both fixed (38c2fa8); the brook fort is rerun on it.</p>
<h3>Exhaustion and stand-ins</h3>
<p>A species is exhausted only when its stock reads 0, none of it is on the map, and both hold for a day (DF debits a wave's planned size when it starts
the wave; 284 arrivals had followed 'exhausted' readings). A stand-in must share the slot's layer, guild and a biome, be within four times its adult
size, have stock DF can actually send on that layer (for a walker: on the fort's own tile), and link to the season's food web; if none passes, the
slot stays empty and the ledger names the closest candidate and the check it failed (52cdfcb). An entry is never refilled from the world region's
total any more (one bluefish entry had been given 515,871).</p>
<p>Your two questions. <b>Entry sizes:</b> per tile, the tool's entries match DF's own (DF stocks its entries a little below the raws' midpoint the tool
uses); the differences are that DF stocks a flier on up to nine tiles where the tool creates one or two, and the refill above.
<b>When a stand-in was picked:</b> per species, the moment its summed stock read 0, never for a whole trophic layer.</p>
{sizes}
<h3>The evil coast, sheltered</h3>
<p>Fifty dwarves in a 9x9 room dug four levels down, every item stockpiled inside, the wagon deconstructed, a meeting area in the room. The fort lived
the whole year past the summer ash that had zombified three earlier runs (X5v75e4: OK). Its one failed check was two sent-off emus that never left:
both had been raised undead by the evil weather, and the tool never manages the undead. The run recorder now logs undead animals as their own kind.</p>
<h3>Water art</h3>
<p>Brooks: DF's pebbles at half opacity over a mud bed so animals show through, a frozen brook drawn as ice over pebbles, and every brook-top corner
and edge sprite cleared. Murky pools: the lake's blue with a green cast, and a mud ramp at the view level. DF's depth numbers and ramp arrows are
drawn over the plugin's water when switched on.</p>
"""


def crowd_section(run='X4v75b'):
    """stacked bars per day: the crowd (height), the diversity (one segment per species) and the mix (colour by animal type)"""
    import crowd
    from design import Design
    cells = [(f'{r}:{a}', n, cell_dir(r, a)) for r, a, n in CROWD_FORTS if cell_dir(r, a).joinpath('positions.tsv').exists()]
    S = crowd.series(cells, Design().E.classify)
    if not S['forts']:
        return ''
    blob = json.dumps(S, separators=(',', ':')).replace('</', '<\\/')
    return f"""
<h2 id="crowd">Crowdedness and diversity through the year</h2>
<p>Every wild animal on the map in the full-year runs ({', '.join(sorted({k.split(':')[0] for k in S['forts']}))}), one bar per day of the year: the height is how crowded the layer was, each segment one species (so the
number of segments is its diversity that day), coloured by animal type. Sponges (placed scenery, never cast) are not counted, and a fully aquatic species recorded on land is counted in the water chart (amphibians stay on land). Each
chart has its own fort selector, and the cavern chart a Caverns 1 2 3 toggle (each unit's cavern by its level). Dashed lines mark the season changes, when the casts turn over. Each chart's
y-axis fits its own data, so read the axis when comparing forts. Hover a day for its species; each chart's table lists them all.</p>
<div id="crowd-charts" class="viz-root"></div>
<script id="crowd-data" type="application/json">{blob}</script>
"""


def applied_section():
    """the user's decisions of 13 Oct and what they change"""
    import design as Dz
    from apex_share import compare
    raw = Dz.Design().R
    def biomes(toks):
        return ', '.join(sorted(b.lower().replace('_', ' ') for b in toks))
    rows = ''.join(f"<tr><td class='mono'>{t}</td><td class='num'>{len(raw.creature(t)['biomes'])}</td><td>{biomes(bs)}</td><td>any region</td></tr>"
                   for t, bs in sorted(Dz.EXTRA_BIOMES.items()))
    rows += ''.join(f"<tr><td class='mono'>{t}</td><td class='num'>{len(raw.creature(t)['biomes'])}</td><td>{biomes(bs)}</td><td>evil regions only</td></tr>"
                    for t, bs in sorted(Dz.EVIL_EXTRA_BIOMES.items()))
    rows += ''.join(f"<tr><td class='mono'>{t}</td><td class='num'>{len(raw.creature(t)['biomes'])}</td><td>{biomes(bs)}</td><td>evil deserts (wired evil flier)</td></tr>"
                    for t, bs in sorted(Dz.EVIL_APEX_BIOMES.items()))
    limit = ''.join(f"<tr><td class='mono'>{t}</td><td class='num'>{len(raw.creature(t)['biomes'])}</td><td>{biomes(bs)}</td><td>kept to these (narrowed)</td></tr>"
                    for t, bs in sorted(Dz.BIOME_LIMIT.items()))
    bugs = ''.join(f"<tr><td class='mono'>{t}</td><td>{'flier: land-ground or land-flying' if Dz.Design().E.classify(t)['habitat'] in ('flier', 'waterbird') else 'land-ground'}</td>"
                   f"<td class='note'>{Dz.REAL_CARNIVORE.get(t, 'already a predator in the raws (CARNIVORE)')}</td></tr>" for t in sorted(Dz.GIANT_BUGS))
    before, after, _, none_after = compare()
    top = sorted(set(before) | set(after), key=lambda t: -after.get(t, 0))
    share = ''.join(f"<tr><td class='mono'>{t}</td><td class='num' data-v='{before.get(t, 0):.4f}'>{before.get(t, 0):.1%}</td>"
                    f"<td class='num' data-v='{after.get(t, 0):.4f}'>{after.get(t, 0):.1%}</td></tr>"
                    for t in top if max(before.get(t, 0), after.get(t, 0)) >= 0.005)
    return f"""
<h2 id="applied">Applied 13 Oct: your apex decisions</h2>
<p>Your answers to the apex review, now in the simulation (every table on this page is regenerated with them) and ported to the engine. Not yet run on
the rig.</p>
<ul class="find">
<li><b>The audit bug is fixed.</b> The audit read every row's apex tiers after its last embark, so one embark's wiring stood for all: the grimeling showed
as an evil freshwater apex everywhere and the harpy nowhere. Tiers are now read with each row; the harpy and the nightwing are in the evil flying rows.</li>
<li><b>Two new freshwater apexes:</b> the tigerfish (tropical lakes and rivers) and the anaconda (into tropical lakes and rivers through the table below).</li>
<li><b>The dingo is narrowed</b> to arid, open and dry country; the temperate wetlands it held alone get the black bear, the wolf, the cougar and the jaguar.</li>
<li><b>The apex draw's pack bonus is x1.5</b> (it was the cast-wide x3; the pack is also counted in group size). Every other slot keeps x3.</li>
<li><b>Tool-side biome additions</b> for the apexes DF keeps in tropical subtypes, and a wider evil roster on evil regions (table). The savage, alignment
and extinct gates still apply per biome, and the engine creates population entries for cast species DF has not stocked, so DF sends them itself.</li>
<li><b>Giant bug apexes:</b> the giant mantis and four more giant bugs the raws leave without CARNIVORE are read as predators; they and the three giant
arachnids are true apexes in any savage or evil land biome, a calm evil one included, and the fliers can take the land-ground apex as well as land-flying.</li>
</ul>
<h3>Who takes the land-ground apex</h3>
<p>Each species' share of the land-ground apex draw on a calm, neutral region, every land biome and season weighted equally, under the rules of 12 Oct
and of 13 Oct.{(' Biomes with no apex after: ' + ', '.join(none_after) + '.') if none_after else ' Every land biome keeps an apex.'}</p>
<div class='tbl'><table><thead><tr><th>species</th><th class='num' data-t='num'>12 Oct</th><th class='num' data-t='num'>13 Oct</th></tr></thead><tbody>{share}</tbody></table></div>
<h3>Biome additions and limits</h3>
<div class='tbl'><table><thead><tr><th>species</th><th class='num' data-t='num'>raw biomes (water ones included)</th><th>added (or kept to)</th><th data-t='cat'>where</th></tr></thead><tbody>{rows}{limit}</tbody></table></div>
<h3>Giant bug apexes</h3>
<div class='tbl'><table><thead><tr><th>species</th><th data-t='cat'>apex on</th><th>why a predator</th></tr></thead><tbody>{bugs}</tbody></table></div>
"""


def main():
    d = json.loads(DATA.read_text())
    data, meta = d['embarks'], d['meta']
    st = stats(data, meta['audit']['roll'])
    st['ob_years'] = meta['order_bias']['years']
    blob = json.dumps(d, separators=(',', ':')).replace('</', '<\\/')
    html = f"""<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cast Pipeline Trace</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bitter:wght@500;700&family=Atkinson+Hyperlegible:wght@400;700&family=JetBrains+Mono:wght@400;600&display=swap">
<style>{report.CSS}{CSS_EXTRA}{crowd_assets.CSS}</style>
<div class="wrap">
<section class="lede">
  <span class="eyebrow">Seasonal Wildlife · the full-pool design · simulated 9 Oct · built and run on the rig 12 Oct 2026</span>
  <h1>Cast Pipeline Trace</h1>
  <p>Your design of 9 Oct (evening), simulated on DF's own raws for six embarks. The pool is no longer the short list DF stocked on the
  region: every creature in the raws is a candidate, filtered first by wild and natural, then BIOME, SAVAGE, GOOD/EVIL and the world's
  real-world-extinct rule, then split into seven layers (land-ground, land-flying, ocean, freshwater, cavern 1, 2, 3) and four seasons.
  Each of those lists feeds one season cast with the slot table you set for its layer. The design is now built into the engine (v7.5) and has run on
  the rig: the results come first, in <a href="#rig">On the rig</a>. Newest: <a href="#changes">the changes of 13 Oct</a> (walkers, pauses,
  pools and brooks, stand-ins) and <a href="#validate">the validation year</a> on eight forts. The sections after them are the desk simulation the build followed.
  Every table sorts by a click on its header; categorical columns filter.</p>
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
{rig_section('X4v75b')}
{region_section('X5v75')}
{changes_section()}
{region_section('X7v75', X7_NOTES, 'validate', 'On the rig: the validation year (13-14 Oct)', "a full year each on {n} forts on the engine with the 13 Oct changes (walkers, both pauses, pools and brooks, exhaustion and stand-ins); one replicate each; a fort whose run found a fault shows its rerun on the fix (X7v75b to X7v75e).")}
{crowd_section('X4v75b')}
{applied_section()}

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

<h2>Two odds: being cast, and arriving</h2>
<p>The tool weighs a species twice, at two different times, by two different mechanisms.</p>
<div class='tbl'><table><thead><tr><th data-t='cat'>stage</th><th>when</th><th>who decides</th><th>what sets the odds</th></tr></thead><tbody>
<tr><td><b>1. Inclusion</b>: is the species in a season's cast?</td><td>once, at embark (or first enable, or a redraw); all 28 casts at once,
in a random order</td><td>the tool (castYear, castGrow)</td><td>the seed's high-value test, food-web links into the emptiest slot, and the pick weights:
x3 pack hunters, x0.2 giants, x0.1 animal people, x0.01 per cast already built that holds the species; the apex draw (size, the same weights)</td></tr>
<tr><td><b>2. Appearance</b>: which cast species comes in the next wave?</td><td>every wave, all season, every year</td><td>DF, drawing from the region's
population entries</td><td>DF picks in proportion to each creature's raw FREQUENCY. The tool rewrites FREQUENCY to the cast's ladder (the pyramid: grazers
and prey common, predators rarer, apexes at most 5; castLadder writes one number per species, CAVERN.apply copies it into the raw) and holds every
out-of-season species' entry at zero, so only cast species can be drawn. Apexes are placed by the tool's scheduler.</td></tr>
</tbody></table></div>
<p><b>Where the x0.01 belongs: at inclusion.</b> That is where it is now, and where it does what you want: across the year it makes a species unlikely to
be cast in a second season while others are free, so the four casts of a layer differ, and a species that is cast twice is cast because nothing else fits
(a thin pool, or the only apex). Applied to appearance instead (a grizzly cast all year arriving at x1, x0.01, x0.01², x0.01³), three things break:</p>
<ul class="find">
<li><b>Hollow casts.</b> The grizzly keeps its summer, autumn and winter slots but almost never arrives in them, so those casts show one apex short
and the food web the cast was built on does not appear on the map.</li>
<li><b>DF cannot hold the numbers.</b> FREQUENCY is a whole number per creature, 1 to 100 in practice; 50 x 0.01 = 0.5 and 50 x 0.0001 both round to 0 or
the floor of 1. Only one step of the decay is representable.</li>
<li><b>It needs seasonal FREQUENCY.</b> Today's ladder writes one number per species for the year; a decaying odds would have to be rewritten at every
season change (the season timer can, at the cost of one more write pass).</li>
</ul>
<p>So x0.01 stays at inclusion (confirmed 12 Oct): each cast built before this one that holds the species multiplies its weight by 0.01. Arrival
odds are then the ladder's, the same every year, so nothing needs a yearly reset. Population entries are never reset: each wave debits its entry, and a
species whose entry runs out is gone from the fort's region (local extinction).</p>
<h3>How the region's population list is made to match the casts</h3>
<p>The tool does not overwrite DF's entries; it masks them. DF draws a wave only from entries with animals left, so for each managed species the tool
sets the entry's count to zero (and marks it extinct) whenever the species is out of season or not cast, parking that count in its reserve, and puts the
same count back when the species' cast season comes (applyLive, holdOutOfSeason). DF's own stocking is untouched underneath and comes back whole when the
tool is turned off. A cast species DF never stocked gets a new entry beside DF's (phase 5), masked the same way and removed at <code>off</code>. The reserve
only ever holds an entry's own animals; it creates none.</p>
<p>In the caverns the mask works per cavern: each has its own cast, so a species cast in cavern 1 alone keeps its cavern 2 and 3 entries at zero, and a
species DF stocked in one cavern but cast in another gets an entry where it is cast. One limit comes from DF itself (found on the rig, 12 Oct): when every
stocked animal of one region tile in one cave has FREQUENCY 0, DF's wave pick never ends and the game stops. The tool's cap gate can do exactly that, so
after every FREQUENCY write a guard puts one species of each such group back at 1.</p>
<h3>Build order</h3>
<p>Because the repeat weight counts casts already built, the cast built first gets the unpenalised pick of every species eligible all year. Built Spring
first, the high-weight species (pack hunters x3, high-value seeds) gathered in Spring; built in a random order (seeded by site and year), each season
gets its fair share. Measured over {st['ob_years']} simulated years on each of the six embarks, counting every non-apex cast place of a species eligible on its
layer in all four seasons:</p>
{order_table(meta)}
<p><b>The rule this produces</b> (confirmed 12 Oct): a species goes, at random, into whichever season × layer casts it is eligible for, and every
further appearance is penalised x0.01 cumulatively, in whatever order the casts happen to be built. It is discouraged from a second season and from a
second layer in the same season alike.</p>
<p class="note">The total per season is the same either way, because each cast has fixed slot counts; what the order changes is <i>which</i> species
fill them. "Concentration" is the mean share of a species' casts that fall in its most common season (25% would be perfectly even).</p>

<h2>Who can hold the apex</h2>
<p>Rebuilt 10 Oct. A species can be drawn for the apex slot of a layer when it is:</p>
<ul class="find">
<li>a LARGE_PREDATOR species (land, flying and caverns; caverns keep their sentients in the sentient slot);</li>
<li>a giant of any predator, mesopredators included (giant fox, giant badger, giant kestrel);</li>
<li>an animal person whose root animal is eligible (bear man, cougar man, quetzalcoatlus man), drawn at x0.1 as all animal people;</li>
<li>on water layers, one of the engine's curated water apexes (orca, sperm whale, great white, crocodiles, the large sharks) or a giant or animal
person of one; DF's other LARGE_PREDATOR water species (sea lamprey, frill shark, blacktip) take meso, as before;</li>
<li>a raptor of 2,000 cm³ or more on land-flying (eagle, the large owls, osprey; never a scavenger);</li>
<li>a real-life apex that DF does not tag, below;</li>
<li>a species the biomes × region audit promotes or wires in for a biome that had too few apexes (approved 12 Oct, applied);</li>
<li>on an evil region, the harpy on land-flying (an EVIL LARGE_PREDATOR raptor, kept out before only by its sentience) and the grimeling on freshwater
(the only EVIL water hunter besides the sea monster; DF tags it NO_EAT and NO_DRINK, so it is let through as a hand-wired apex). A lake is the only
freshwater layer with an apex slot; on a river or murky pools the grimeling can take meso (it is too large for the murky-pool roster).</li>
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

<h2>Biomes × region × apex audit</h2>
<p>Built programmatically over the whole creature list (scripts/castsim/apex_audit.py): every surface biome (27 land, 3 oceans, temperate and
tropical lakes) under six region types (not savage or savage, × good, neutral or evil; extinct species under UNTAMED_WILDS, so only on savage
regions), through the same filters and layer split as the casts. For each it counts the layer's potential cast members and, per season, the species
that can hold the apex. A row is short when some season has fewer than two true apexes. Rivers and murky pools have no apex slot; caverns do not
depend on the region.</p>
<h3>Every true apex in DF's raws, by region type</h3>
<p>The species that can hold a layer's apex in at least one biome. On a region that is not savage, the whole raws give {st['roll_wn_ground']} land apexes
({st['roll_wn_temperate']} of them temperate or cold); evil regions add their EVIL predators; savage regions add giants, animal people and extinct species.</p>
{roll_summary(meta)}
<details><summary>Every apex species, with its biomes</summary>{roll_table(meta)}</details>
<h3>Every biome, layer and region type</h3>
{audit_table(meta)}
<h3>Candidates for the short rows</h3>
<p>Generated, not hand-picked. <b>Promote</b>: every resident predator that cannot hold the apex today, the resident local apexes (lynx, coyote,
wolverine) first, then by group size against the largest resident. <b>Wire</b>: every species that is a true apex of the same layer in another biome
of the same region type and climate band, scored by fauna overlap (the share of this biome's residents that also live in the candidate's biomes).
The automatic proposal takes local promotions, then wires with overlap 0.5 or more, then other promotions, then other wires, until every season has
two true apexes. The scores say how well a candidate fits DF's own fauna, not real-life range: a wired dingo in the taiga scores well because DF's
dingo shares most of the taiga's animals. <b>Approved 12 Oct and applied to the casts on this page</b> (the automatic proposal of each short row).</p>
{candidate_table(meta)}

<h2>Step through an embark</h2>
<div class="controls" id="exPick"></div>
<div class="steps" id="steps"></div>

<h3>The year's food web: <span class="exname"></span>, <span class="layername"></span></h3>
<div class="web" id="web"></div>

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
<p><b>Built 12 Oct</b>, every phase below, and run on the rig (<a href="#rig">results</a>). The table is the plan as it stood before the build, with
its line numbers in v7.4; phase 5's freshwater entries were solved without a water-feature creator, as surface entries filed under the species'
water key, which DF draws waves from. The original text follows.</p>
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
<h3>Decided (12 Oct)</h3>
<ul class="find">
<li><b>Casts are built once</b>, at embark, at first enable, or when the player asks for a redraw; all 28 at once, in a random order seeded by site and
year. They are not redrawn at a new year.</li>
<li><b>The x0.01 repeat weight is an inclusion weight</b> (section above): x0.01 per cast already built that holds the species. Arrival odds are the ladder's,
the same each year; population entries run down naturally, and a species whose entry is spent is locally extinct. The reserve is unchanged.</li>
<li><b>Created entries are removed when the tool is turned off.</b> The tool records every entry it creates (region tile, race, master and live row) in
its saved config; <code>off</code> zeroes them, lets or sends their units off the map, clears any unit's population reference to them, and then deletes
both rows, next to the reserve give-back (RESERVE.giveBack 3071). A unit still pointing at a deleted entry is the risk to test first. Phase 5.</li>
<li><b>The audit's proposals are approved</b>, with the harpy and grimeling for evil regions: a wiring table the engine reads beside MODEL.ROLE.</li>
</ul>
<h3>Settled by the build</h3>
<ul class="find">
<li><b>Freshwater entries.</b> No water-feature creator was needed: a surface entry for the species, masked by its freshwater cast, is enough for DF to
send it (the longnose gar, pike and sturgeon arrived this way).</li>
<li><b>Wired species on the map</b> remain untested: the three rig forts wire none (see <a href="#rig">Not yet seen on the rig</a>).</li>
</ul>
<h2>Method notes</h2>
<p><b>Raws.</b> DF 53.16's vanilla and extinct creature files compiled as DF compiles them (COPY_TAGS_FROM, the GIANT and ANIMAL_PERSON variations,
castes, derived flags, aggregate biome tokens expanded), as in the earlier trace. <b>Classification</b> (guild, habitat, size, pet value, the 83 extinct
corrections) is the engine's classify, mirrored in scripts/castsim/engine.py. <b>The design</b> is scripts/castsim/design.py; the runner is
design_run.py. Random draws are seeded per embark, layer and season, so one run is one possible year.</p>
</div>
<script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"></script>
<script id="data" type="application/json">{blob}</script>
<script>{JS}</script>
<script>{crowd_assets.JS}</script>
"""
    OUT.write_text(html)
    print('wrote', OUT, len(html))


if __name__ == '__main__':
    main()
