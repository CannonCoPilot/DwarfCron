"""castsim.cavern_picks_page: the "Every cavern species" table as a tool where the user marks the caverns each species should
be able to appear in (user 15 Oct 2026). Picks are saved in the artifact's db (collection `picks`, one document per species,
id = token with spaces as '_': {caverns: [1, 3], note: str, at: ISO time}); Claude reads them back with ArtifactData.
Never-arrive verdicts come from data/cave-arrive/<run>/summary.md when present.
Usage: python3 cavern_picks_page.py [--na RUN]   (writes data/castsim/cavern-picks.html)"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'data/castsim/cavern_weird.json'
OUT = ROOT / 'data/castsim/cavern-picks.html'
NA_SUBJECTS = {'AMPHIBIAN_MAN', 'ANT_MAN', 'BAT_MAN', 'CAVE_FISH_MAN', 'CAVE_SWALLOW_MAN', 'DRUNIAN', 'GREMLIN', 'MOLE_DOG_NAKED',
               'MOLE_GIANT', 'OLM_MAN', 'RAT_GIANT', 'RAT_LARGE', 'REPTILE_MAN', 'RODENT MAN', 'SERPENT_MAN', 'MANERA'}


def na_verdicts(run):
    """{token: (verdict, 'subject n / control n')} from a never-arrive run's summary.md"""
    f = ROOT / 'data/cave-arrive' / run / 'summary.md'
    out = {}
    if not f.exists():
        return out
    for ln in f.read_text().splitlines():
        c = [x.strip() for x in ln.strip('|').split('|')]
        if len(c) >= 9 and c[0] and c[0] not in ('subject',) and not c[0].startswith('---'):
            out[c[0].replace('_', ' ') if c[0].replace('_', ' ') in NA_SUBJECTS else c[0]] = (c[8], f'{c[2]} v {c[3]}')
    return out


def main():
    run = sys.argv[sys.argv.index('--na') + 1] if '--na' in sys.argv else None
    d = json.loads(SRC.read_text())
    na = na_verdicts(run) if run else {}
    rows = []
    for r in d['rows']:
        k = lambda x, i: x.get(str(i), x.get(i, 0))  # noqa: E731
        t = r['t']
        v = na.get(t)
        rows.append({
            't': t, 'id': t.replace(' ', '_'), 'v': r['v'], 'vc': r['vc'], 'wd': r['wd'],
            'w': [round(k(r['mult'], i), 2) if i in r['caves'] else None for i in (1, 2, 3)],
            'caves': r['caves'], 'dep': r['dep'], 'slots': r['slots'], 'g': r['g'], 'h': r['h'], 'm': r['m'],
            'cl': r['cl'], 'fq': r['fq'], 'tags': r['tags'],
            'casts': [k(r['rig']['casts'], i) for i in (1, 2, 3)], 'units': None if r['v'] else [k(r['rig']['units'], i) for i in (1, 2, 3)],
            'na': (v[0] if v else ('pending' if t in NA_SUBJECTS else None)), 'nan': v[1] if v else '',
        })
    meta = {'fy': d['fort_years'], 'na_run': run or ''}
    blob = json.dumps({'rows': rows, 'meta': meta}, separators=(',', ':')).replace('</', '<\\/')
    OUT.write_text(PAGE.replace('__DATA__', blob))
    print('wrote', OUT, OUT.stat().st_size, len(rows), 'rows;', len(na), 'verdicts')


PAGE = r"""<title>Cavern Layer Picks</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bitter:wght@600;700&family=Atkinson+Hyperlegible:wght@400;700&family=JetBrains+Mono:wght@400;600&display=swap">
<style>
:root{--bg:#edf0ee;--surface:#ffffff;--sunk:#e2e7e4;--ink:#1c2321;--muted:#5a6661;--line:#cdd6d1;--accent:#4e3f7d;--accent-ink:#ffffff;
--c1:#2f7184;--c1-bg:#dcedf1;--c2:#5d4ea0;--c2-bg:#e6e2f4;--c3:#94365a;--c3-bg:#f4e0e8;
--ok:#2f7a4a;--ok-bg:#e0f0e5;--warn:#8d6210;--warn-bg:#f6ecd3;--bad:#a2402e;--bad-bg:#f6e2dc;
--serif:"Bitter",Georgia,serif;--sans:"Atkinson Hyperlegible",system-ui,sans-serif;--mono:"JetBrains Mono",ui-monospace,Menlo,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#121614;--surface:#1a201d;--sunk:#232b27;--ink:#e0e7e3;--muted:#9aa8a1;--line:#2f3a35;--accent:#b6a6e6;--accent-ink:#141019;
--c1:#7fc3d4;--c1-bg:#173039;--c2:#b0a3ea;--c2-bg:#272240;--c3:#e594b3;--c3-bg:#3a1f2b;--ok:#8fd0a6;--ok-bg:#1d3326;--warn:#e2b765;--warn-bg:#382d17;--bad:#ee9a86;--bad-bg:#3b231e}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#121614;--surface:#1a201d;--sunk:#232b27;--ink:#e0e7e3;--muted:#9aa8a1;--line:#2f3a35;--accent:#b6a6e6;--accent-ink:#141019;
--c1:#7fc3d4;--c1-bg:#173039;--c2:#b0a3ea;--c2-bg:#272240;--c3:#e594b3;--c3-bg:#3a1f2b;--ok:#8fd0a6;--ok-bg:#1d3326;--warn:#e2b765;--warn-bg:#382d17;--bad:#ee9a86;--bad-bg:#3b231e}
body{background:var(--bg);color:var(--ink);font:15px/1.5 var(--sans)}
.wrap{max-width:1400px;margin:0 auto;padding-inline:20px;padding-block:24px 64px}
h1{font:700 1.75rem/1.2 var(--serif);margin:2px 0 8px;text-wrap:balance}
.eyebrow{font:600 .7rem var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
.lede{color:var(--muted);max-width:78ch;margin:0 0 14px}
.strip{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px;margin:14px 0}
.cv{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:10px 12px;display:grid;gap:2px}
.cv h3{margin:0;font:700 .95rem var(--serif);display:flex;gap:8px;align-items:center}
.cv .n{font:700 1.4rem var(--serif);font-variant-numeric:tabular-nums}.cv .s{font-size:.8rem;color:var(--muted)}
.dot{width:10px;height:10px;border-radius:3px;display:inline-block}.d1{background:var(--c1)}.d2{background:var(--c2)}.d3{background:var(--c3)}
.save{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:10px 12px;font-size:.85rem;color:var(--muted);display:grid;gap:4px}
.save b{color:var(--ink)}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0 10px}
.bar input[type=search]{font:inherit;font-size:.9rem;padding:6px 10px;border:1px solid var(--line);border-radius:6px;background:var(--surface);color:var(--ink);min-width:0;flex:1 1 200px;max-width:320px}
.bar select,.bar button,.bar label{font:inherit;font-size:.85rem}
.bar select{padding:5px 8px;border:1px solid var(--line);border-radius:6px;background:var(--surface);color:var(--ink)}
.bar label{display:inline-flex;gap:5px;align-items:center;color:var(--muted)}
.btn{border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:999px;padding:5px 12px;cursor:pointer}
.btn:hover{border-color:var(--accent)}
.count{font-size:.8rem;color:var(--muted);margin-left:auto}
.tbl{overflow:auto;max-height:72vh;border:1px solid var(--line);border-radius:8px;background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:.84rem;font-variant-numeric:tabular-nums}
th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top;white-space:nowrap}
td.wrapc{white-space:normal;min-width:12em}
th{font:600 .68rem var(--mono);text-transform:uppercase;letter-spacing:.04em;color:var(--muted);background:var(--sunk);position:sticky;top:0;z-index:2}
th button{all:unset;cursor:pointer}th button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
th[aria-sort] button::after{content:' ▾';color:var(--accent)}th[aria-sort="ascending"] button::after{content:' ▴'}
td.num,th.num{text-align:right}
td.tok{font-family:var(--mono);font-size:.8rem;position:sticky;left:0;background:var(--surface);z-index:1}
th.tok{left:0;z-index:3}
tr.changed td.tok{box-shadow:inset 3px 0 0 var(--accent)}
.pick{display:inline-flex;gap:4px}
.pick button{font:600 .74rem var(--mono);width:2.3em;height:1.9em;border-radius:5px;border:1px solid var(--line);background:var(--surface);color:var(--muted);cursor:pointer}
.pick button[aria-pressed="true"].p1{background:var(--c1);border-color:var(--c1);color:var(--surface)}
.pick button[aria-pressed="true"].p2{background:var(--c2);border-color:var(--c2);color:var(--surface)}
.pick button[aria-pressed="true"].p3{background:var(--c3);border-color:var(--c3);color:var(--surface)}
.pick button:focus-visible,.btn:focus-visible,.reset:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.pick button:disabled{cursor:not-allowed;opacity:.6}
.reset{all:unset;cursor:pointer;color:var(--accent);font-size:.75rem;margin-left:6px}
.reset[hidden]{display:none}
.lay{display:inline-flex;gap:3px}.lay span{font:600 .7rem var(--mono);padding:0 5px;border-radius:4px}
.l1{color:var(--c1);background:var(--c1-bg)}.l2{color:var(--c2);background:var(--c2-bg)}.l3{color:var(--c3);background:var(--c3-bg)}
.chip{display:inline-block;font:600 .66rem var(--mono);padding:1px 6px;border-radius:999px;margin:1px 2px 1px 0;background:var(--sunk);color:var(--muted)}
.chip.warn{background:var(--warn-bg);color:var(--warn)}.chip.bad{background:var(--bad-bg);color:var(--bad)}.chip.ok{background:var(--ok-bg);color:var(--ok)}
.note{font:inherit;font-size:.8rem;width:14em;padding:3px 6px;border:1px solid var(--line);border-radius:5px;background:var(--surface);color:var(--ink)}
.w0{color:var(--muted)}.zero{color:var(--bad);font-weight:700}
.legend{font-size:.8rem;color:var(--muted);max-width:110ch;margin-top:10px}
@media (max-width:560px){h1{font-size:1.4rem}.count{margin-left:0;width:100%}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
<div class="wrap">
<span class="eyebrow">Seasonal Wildlife · cavern casts</span>
<h1>Cavern Layer Picks</h1>
<p class="lede">Every species the full pool can put in a cavern, with its weirdness score, the slots it can fill and what the rig cast and saw
arrive. Mark the caverns you want each species to be able to appear in. Your picks are saved as you make them, and Claude reads them back
to change the casts. A pick outside DF's raw depth range is allowed, and it is flagged, because DF itself stocks a species only inside that range.</p>
<div class="strip" id="strip"></div>
<div class="bar">
  <input type="search" id="q" placeholder="Search species or tag" aria-label="Search species or tag">
  <select id="fslot" aria-label="Slot"><option value="">All slots</option></select>
  <select id="fkind" aria-label="Kind"><option value="">Animals and vermin</option><option value="a">Animals</option><option value="v">Vermin</option></select>
  <label><input type="checkbox" id="fchg"> Changed only</label>
  <label><input type="checkbox" id="fna"> No-shows only</label>
  <button type="button" class="btn" id="copy">Copy picks</button>
  <span class="count" id="count"></span>
</div>
<div class="tbl"><table id="t"><thead><tr></tr></thead><tbody></tbody></table></div>
<p class="legend" id="legend"></p>
</div>
<script id="data" type="application/json">__DATA__</script>
<script>
(function(){
const D=JSON.parse(document.getElementById('data').textContent), R=D.rows, M=D.meta;
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fmt=n=>n==null?'−':Number(n).toLocaleString('en-US');
const def=r=>r.caves.slice();                       // today's caverns: DF's raw depth range
const picks={};                                     // id -> {caverns:[...], note}
let canWrite=true, dbRef=null, status='connecting';
const pending={}, timers={};
function cur(r){return picks[r.id]&&Array.isArray(picks[r.id].caverns)?picks[r.id].caverns:def(r)}
function changed(r){const a=cur(r).slice().sort().join(),b=def(r).slice().sort().join();return a!==b||!!(picks[r.id]&&picks[r.id].note)}
const COLS=[
 ['tok','species',r=>r.t,'tok'],['pick','your caverns',null,''],['def','raw depth (today)',r=>r.dep?r.dep[0]*10+r.dep[1]:0,''],
 ['wd','weird',r=>r.wd??-1,'num'],['w1','weight c1',r=>r.w[0]??-1,'num'],['w2','weight c2',r=>r.w[1]??-1,'num'],['w3','weight c3',r=>r.w[2]??-1,'num'],
 ['slots','slots',r=>r.v?'vermin':r.slots.join(','),''],['g','guild',r=>r.g,''],['h','habitat',r=>r.h,''],['m','adult cm³',r=>r.m,'num'],
 ['cl','group',r=>r.cl&&r.cl.length?r.cl[1]:0,'num'],['fq','FREQUENCY',r=>r.fq??-1,'num'],
 ['c1','casts c1',r=>r.casts[0],'num'],['c2','casts c2',r=>r.casts[1],'num'],['c3','casts c3',r=>r.casts[2],'num'],
 ['u','units seen',r=>r.units?r.units[0]+r.units[1]+r.units[2]:-1,'num'],['na','never-arrive test',r=>r.na||'',''],
 ['note','your note',null,''],['tags','raw tags',r=>r.tags.join(' '),'']];
let sortKey='wd', sortDir=1;
const thead=document.querySelector('#t thead tr');
thead.innerHTML=COLS.map(([k,l,f,c])=>`<th class="${c==='num'?'num':''} ${k==='tok'?'tok':''}" data-k="${k}">${f?`<button type="button">${esc(l)}</button>`:esc(l)}</th>`).join('');
thead.querySelectorAll('th button').forEach(b=>b.addEventListener('click',()=>{const k=b.parentElement.dataset.k;sortDir=sortKey===k?-sortDir:1;sortKey=k;render()}));
const slots=[...new Set(R.flatMap(r=>r.v?['vermin']:r.slots))].sort();
document.getElementById('fslot').insertAdjacentHTML('beforeend',slots.map(s=>`<option value="${esc(s)}">${esc(s)}</option>`).join(''));
['q','fslot','fkind','fchg','fna'].forEach(id=>document.getElementById(id).addEventListener('input',render));
function naChip(r){if(!r.na)return '<span class="w0">−</span>';const v=r.na;const cls=v==='pending'?'':(v.startsWith('arrives')?'ok':(v.startsWith('never')?'bad':'warn'));
  return `<span class="chip ${cls}">${esc(v.split(' (')[0])}</span>${r.nan?` <span class="w0">${esc(r.nan)}</span>`:''}`}
function row(r){
  const c=cur(r), out=c.filter(k=>!r.caves.includes(k));
  const pick=`<span class="pick" role="group" aria-label="Caverns for ${esc(r.t)}">${[1,2,3].map(k=>`<button type="button" class="p${k}" data-id="${esc(r.id)}" data-k="${k}" aria-pressed="${c.includes(k)}" ${canWrite?'':'disabled'} title="Cavern ${k}">C${k}</button>`).join('')}</span>`
    +`<button type="button" class="reset" data-reset="${esc(r.id)}" ${changed(r)&&canWrite?'':'hidden'}>reset</button>`
    +(out.length?` <span class="chip warn">outside raw depth: C${out.join(', C')}</span>`:'')+(c.length?'':' <span class="chip bad">no cavern</span>');
  const lay=`<span class="lay">${r.caves.map(k=>`<span class="l${k}">C${k}</span>`).join('')}</span> <span class="w0">${r.dep?r.dep[0]+'-'+r.dep[1]:''}</span>`;
  const units=r.units?r.units.reduce((a,b)=>a+b,0):null;
  const uc=units===0&&r.casts.some(x=>x>0)?'zero':'';
  const cells={tok:esc(r.t),pick,def:lay,wd:r.wd==null?'−':r.wd.toFixed(2),w1:r.w[0]??'−',w2:r.w[1]??'−',w3:r.w[2]??'−',
    slots:r.v?`<span class="chip">vermin ${esc(r.vc)}</span>`:r.slots.map(s=>`<span class="chip">${esc(s)}</span>`).join(''),g:esc(r.g),h:esc(r.h),m:fmt(r.m),
    cl:r.cl&&r.cl.length?(r.cl[0]===r.cl[1]?r.cl[0]:r.cl[0]+'-'+r.cl[1]):'−',fq:fmt(r.fq),c1:r.casts[0],c2:r.casts[1],c3:r.casts[2],
    u:units==null?'<span class="w0">−</span>':`<span class="${uc}">${fmt(units)}</span>`,na:naChip(r),
    note:`<input class="note" id="note-${esc(r.id)}" data-note="${esc(r.id)}" value="${esc((picks[r.id]&&picks[r.id].note)||'')}" ${canWrite?'':'disabled'} aria-label="Note for ${esc(r.t)}">`,
    tags:r.tags.map(t=>`<span class="chip">${esc(t)}</span>`).join('')};
  return `<tr class="${changed(r)?'changed':''}">`+COLS.map(([k,,,c])=>`<td class="${c==='num'?'num':''} ${k==='tok'?'tok':''} ${k==='tags'?'wrapc':''}">${cells[k]}</td>`).join('')+'</tr>';
}
function render(){
  const q=document.getElementById('q').value.trim().toLowerCase(), fs=document.getElementById('fslot').value, fk=document.getElementById('fkind').value;
  const fc=document.getElementById('fchg').checked, fn=document.getElementById('fna').checked;
  const col=COLS.find(c=>c[0]===sortKey);
  let L=R.filter(r=>(!q||r.t.toLowerCase().includes(q)||r.tags.join(' ').toLowerCase().includes(q))&&(!fs||(fs==='vermin'?r.v:r.slots.includes(fs)))
    &&(!fk||(fk==='v')===r.v)&&(!fc||changed(r))&&(!fn||r.na));
  if(col&&col[2])L.sort((a,b)=>{const x=col[2](a),y=col[2](b);return (x<y?-1:x>y?1:0)*sortDir||a.t.localeCompare(b.t)});
  const active=document.activeElement&&document.activeElement.id;
  document.querySelector('#t tbody').innerHTML=L.map(row).join('');
  if(active&&active.startsWith('note-')){const el=document.getElementById(active);if(el){el.focus();const n=el.value.length;el.setSelectionRange(n,n)}}
  thead.querySelectorAll('th').forEach(th=>{th.removeAttribute('aria-sort');if(th.dataset.k===sortKey)th.setAttribute('aria-sort',sortDir>0?'ascending':'descending')});
  document.getElementById('count').textContent=`${L.length} of ${R.length} species · ${R.filter(changed).length} changed`;
  strip();
}
function strip(){
  const an=R.filter(r=>!r.v);
  const cards=[1,2,3].map(k=>{const today=an.filter(r=>r.caves.includes(k)).length, mine=an.filter(r=>cur(r).includes(k)).length;
    const d=mine-today;return `<div class="cv"><h3><span class="dot d${k}"></span>Cavern ${k}</h3><span class="n">${mine}</span><span class="s">animal species with your picks · ${today} today${d?` (${d>0?'+':''}${d})`:''}</span></div>`}).join('');
  const st={connecting:'Connecting to saved picks…',live:'Picks save as you make them.',saving:'Saving…',readonly:'You can view this table; saving picks needs edit access.',
    off:'Saving is off in this view, so picks stay on this screen only. Open the page on claude.ai to save them.',error:'A save failed. Your last change may not be stored; try it again.'}[status];
  document.getElementById('strip').innerHTML=cards+`<div class="save"><b>${R.filter(changed).length} species changed</b><span>${esc(st)}</span></div>`;
}
function save(id){
  clearTimeout(timers[id]);
  timers[id]=setTimeout(async()=>{
    delete timers[id];
    if(!dbRef||!canWrite)return;
    if(pending[id]){save(id);return}
    pending[id]=true;status='saving';strip();
    const p=picks[id]||{};
    try{await dbRef.doc(id).set({caverns:(p.caverns||[]).slice().sort(),note:p.note||'',at:new Date().toISOString()});status='live'}
    catch(e){status=e&&e.code==='invalid_argument'?'readonly':'error';if(status==='readonly'){canWrite=false;render()}}
    pending[id]=false;strip();
  },500);
}
document.querySelector('#t tbody').addEventListener('click',e=>{
  const b=e.target.closest('button[data-k]'), rs=e.target.closest('button[data-reset]');
  if(b&&canWrite){const r=R.find(x=>x.id===b.dataset.id),k=+b.dataset.k;const c=new Set(cur(r));c.has(k)?c.delete(k):c.add(k);
    picks[r.id]=Object.assign({},picks[r.id],{caverns:[...c].sort()});render();save(r.id)}
  if(rs&&canWrite){const r=R.find(x=>x.id===rs.dataset.reset);picks[r.id]={caverns:def(r),note:''};render();save(r.id)}
});
document.querySelector('#t tbody').addEventListener('input',e=>{const id=e.target.dataset&&e.target.dataset.note;if(!id||!canWrite)return;
  const r=R.find(x=>x.id===id);picks[id]=Object.assign({caverns:cur(r)},picks[id],{note:e.target.value});save(id);
  const tr=e.target.closest('tr');tr.classList.toggle('changed',changed(r));document.getElementById('count').textContent=`${R.length} species · ${R.filter(changed).length} changed`});
document.getElementById('copy').addEventListener('click',async()=>{
  const lines=R.filter(changed).map(r=>`${r.t}: caverns ${cur(r).join(',')||'none'} (today ${def(r).join(',')})${picks[r.id]&&picks[r.id].note?' -- '+picks[r.id].note:''}`);
  const txt=lines.length?lines.join('\n'):'No changes yet.';const b=document.getElementById('copy');
  try{await navigator.clipboard.writeText(txt);b.textContent='Copied'}catch(_){b.textContent='Copy failed'}setTimeout(()=>b.textContent='Copy picks',1600)});
document.getElementById('legend').innerHTML=`Raw depth is DF's UNDERGROUND_DEPTH: the caverns DF stocks the species in, and today the only caverns the tool casts it in.
Weights are the weirdness score's pick multiplier in each cavern (cavern 1 favours the plain, 2 the middle, 3 the strange). Casts and units
seen are from ${M.fy} full-year rig forts (13-14 Oct); a red units count marks a species cast and never seen. Vermin are not units on DF's list, so they show −.
The never-arrive test puts each no-show beside a species that arrives, on the same footing${M.na_run?` (run ${esc(M.na_run)})`:' (running now)'}.`;
render();
(async()=>{
  const db=await window.claude?.use?.('db').catch(()=>null);
  const user=await window.claude?.use?.('user').catch(()=>null);
  if(!db){status='off';strip();return}
  if(user){const cw=await user.can('data.write');if(cw===false){canWrite=false;status='readonly'}}
  dbRef=db.collection('picks');
  dbRef.onSnapshot(s=>{
    for(const d of s.docs){if(!pending[d.id]&&!timers[d.id]){const x=d.data();picks[d.id]={caverns:Array.isArray(x.caverns)?x.caverns:[],note:x.note||''}}}
    if(status==='connecting')status=canWrite?'live':'readonly';render();
  },()=>{status='error';strip()});
})();
})();
</script>
"""

if __name__ == '__main__':
    main()
