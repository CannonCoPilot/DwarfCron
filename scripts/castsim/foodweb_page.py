"""castsim.foodweb_page: builds the Food Web Explorer page (data/castsim/foodweb/foodweb.html) from creatures.json
(foodweb_export.py), the simulator (foodweb_sim.js) and the page logic (foodweb_app.js). Usage: python3 foodweb_page.py"""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DATA = ROOT / 'data/castsim/foodweb/creatures.json'
OUT = ROOT / 'data/castsim/foodweb/foodweb.html'

CSS = r"""
:root{color-scheme:light;--bg:#eef1ee;--surface:#ffffff;--sunk:#e3e8e4;--ink:#1b2522;--muted:#5b6963;--line:#cfd8d2;--faint:#dde4df;
--accent:#2f6b52;--accent-ink:#ffffff;--warn:#9a6a12;--warn-bg:#f6ecd3;
--c-red:#e34948;--c-purple:#4a3aa7;--c-green:#1baf7a;--c-amber:#eda100;--c-blue:#2a78d6;--seq-lo:#d3e9dc;--seq-hi:#1c5a40;
--serif:"Bitter",Georgia,serif;--sans:"Atkinson Hyperlegible",system-ui,sans-serif;--mono:"JetBrains Mono",ui-monospace,Menlo,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#121816;--surface:#1a211e;--sunk:#222b27;--ink:#e1e8e3;
--muted:#98a69f;--line:#2e3a35;--faint:#2a3430;--accent:#7fb79a;--accent-ink:#0f1512;--warn:#e2b765;--warn-bg:#382d17;
--c-red:#d8443f;--c-purple:#b45fc9;--c-green:#199e70;--c-amber:#c98500;--c-blue:#3987e5;--seq-lo:#2a3a33;--seq-hi:#a6e6c4}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#121816;--surface:#1a211e;--sunk:#222b27;--ink:#e1e8e3;
--muted:#98a69f;--line:#2e3a35;--faint:#2a3430;--accent:#7fb79a;--accent-ink:#0f1512;--warn:#e2b765;--warn-bg:#382d17;
--c-red:#d8443f;--c-purple:#b45fc9;--c-green:#199e70;--c-amber:#c98500;--c-blue:#3987e5;--seq-lo:#2a3a33;--seq-hi:#a6e6c4}
body{background:var(--bg);color:var(--ink);font:15px/1.5 var(--sans)}
.wrap{max-width:1500px;margin:0 auto;padding-inline:20px;padding-block:22px 64px}
h1,h2,h3,h4{font-family:var(--serif);margin:0;text-wrap:balance}
h1{font-size:1.9rem;letter-spacing:-.01em}h2{font-size:1.3rem}h3{font-size:1.05rem}h4{font-size:.92rem;margin:14px 0 6px}
p{margin:0 0 8px;max-width:75ch}.note{color:var(--muted);font-size:.86rem}.small{font-size:.8rem;color:var(--muted)}
.mono{font-family:var(--mono);font-size:.82em}
.eyebrow{font:600 .72rem var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
header.top{display:grid;gap:8px;margin-bottom:14px}header.top p{color:var(--muted)}
.presets{display:flex;flex-wrap:wrap;gap:6px;align-items:center}.presets>span{font:600 .7rem var(--mono);text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-right:4px}
.presets button,.btn{font:inherit;font-size:.86rem;border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:6px;padding:5px 11px;cursor:pointer}
.btn.primary{background:var(--accent);color:var(--accent-ink);border-color:var(--accent);font-weight:700}
.btn:disabled{opacity:.45;cursor:not-allowed}
button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.app{display:grid;grid-template-columns:270px minmax(0,1fr) 150px;gap:16px;align-items:start}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:12px 14px}
aside#fort{display:grid;gap:12px;max-height:calc(100vh - 40px);overflow:auto;position:sticky;top:env(safe-area-inset-top,0px)}
.lbl{font:600 .68rem var(--mono);text-transform:uppercase;letter-spacing:.07em;color:var(--muted);display:block;margin-bottom:5px}
fieldset{border:0;margin:0 0 6px;padding:0}legend{font-size:.8rem;font-weight:700;padding:0;display:flex;gap:8px;align-items:baseline}
.ck{display:flex;gap:6px;align-items:center;font-size:.82rem;line-height:1.35;padding:1px 0;cursor:pointer}.ck input{margin:0;accent-color:var(--accent)}
.seg{display:inline-flex;flex-wrap:wrap;max-width:100%;border:1px solid var(--line);border-radius:6px;overflow:hidden;background:var(--surface)}
.seg button{font:inherit;font-size:.8rem;border:0;background:none;color:var(--ink);padding:5px 9px;cursor:pointer;border-right:1px solid var(--line)}
.seg button:last-child{border-right:0}.seg button[aria-pressed="true"]{background:var(--accent);color:var(--accent-ink)}
select,input[type=number],input[type=search]{font:inherit;font-size:.84rem;color:var(--ink);background:var(--surface);border:1px solid var(--line);border-radius:5px;padding:4px 6px}
input[type=number]{width:5.2em}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.linkish{font:inherit;font-size:.75rem;color:var(--accent);background:none;border:0;padding:0;cursor:pointer;text-decoration:underline}
section#view{display:grid;gap:8px;min-width:0}
.toolbar{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:end}.toolbar>div{display:grid;gap:3px}
#netbox{position:relative;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:var(--surface)}
#net{display:block;cursor:crosshair;touch-action:none}
#tip,#ctip{position:absolute;pointer-events:none;z-index:5;background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:7px 9px;font-size:.8rem;box-shadow:0 4px 14px rgba(0,0,0,.18);max-width:260px;line-height:1.4}
#ctip{position:fixed}
details.nb summary{cursor:pointer;color:inherit;font-weight:400}details.nb{margin-top:-4px}
.viewtabs{display:inline-flex;gap:0;border-bottom:2px solid var(--line)}
.viewtabs button{font:inherit;font-size:.92rem;font-weight:700;border:0;background:none;color:var(--muted);padding:5px 14px 6px;margin-bottom:-2px;border-bottom:3px solid transparent;cursor:pointer}
.viewtabs button span{font:600 .72rem var(--mono);color:var(--muted);margin-left:3px}
.viewtabs button[aria-selected="true"]{color:var(--ink);border-bottom-color:var(--accent)}
.viewtabs button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
table.surr{border-collapse:separate;border-spacing:3px;width:100%;font-size:.72rem;table-layout:fixed}
table.surr th{background:none;font:600 .6rem var(--mono);text-transform:uppercase;letter-spacing:.05em;color:var(--muted);padding:0 2px;border:0;text-align:center}
table.surr th[scope=row]{text-align:right;width:3.6em}table.surr td{padding:0;border:0}
table.surr button{all:unset;box-sizing:border-box;display:grid;gap:1px;width:100%;min-height:42px;padding:4px 3px;border:1px solid var(--line);border-radius:5px;background:var(--surface);color:var(--ink);text-align:center;cursor:pointer}
table.surr button b{font-weight:700;font-size:.66rem;line-height:1.15}table.surr button span{font:600 .74rem var(--mono);color:var(--muted)}
table.surr button[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}table.surr button[aria-pressed="true"] span{color:var(--accent-ink)}
table.surr button:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
#edgepop{position:absolute;z-index:6;width:320px;max-width:calc(100% - 12px);background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:10px 12px;box-shadow:0 8px 24px rgba(0,0,0,.22);font-size:.8rem}
#edgepop h4{margin:0 18px 6px 0}#edgepop .arrow{font:600 .66rem var(--mono);text-transform:uppercase;color:var(--muted)}
#edgepop ul,ul.rules{list-style:none;margin:0 0 6px;padding:0;display:grid;gap:5px}#edgepop li,ul.rules li{display:block;line-height:1.35}
#edgepop li i,ul.rules li i{display:inline-block;width:10px;height:3px;border-radius:2px;vertical-align:middle;margin-right:6px}
#edgepop .x{position:absolute;top:4px;right:6px;font:inherit;font-size:1.1rem;background:none;border:0;color:var(--muted);cursor:pointer}
ul.rules li{font-size:.72rem}ul.rules em{font-style:normal;color:var(--muted)}
.fams{display:flex;flex-wrap:wrap;gap:2px 14px}.fams .ck{font-size:.8rem}
i.ln{display:inline-block;width:16px;height:0;border-top:2px solid var(--lc);vertical-align:middle;margin:0 2px}
#legend .ln{display:inline-flex;align-items:center;gap:4px}#legend .ln::before{content:"";display:inline-block;width:14px;border-top:2px solid var(--lc)}
#legend{display:grid;gap:3px;font-size:.68rem;color:var(--muted)}#legend>div{display:flex;flex-wrap:wrap;gap:4px 12px;align-items:center}
#legend b{font:600 .66rem var(--mono);text-transform:uppercase;letter-spacing:.06em;min-width:3.6em;color:var(--ink)}
#legend span{display:inline-flex;gap:5px;align-items:center}#legend svg{flex:none}
#legend .ramp i{display:inline-block;width:90px;height:9px;border-radius:2px;background:linear-gradient(90deg,var(--seq-lo),var(--seq-hi))}
#legend .dash::before{content:"";display:inline-block;width:22px;border-top:1.5px solid var(--ink)}
#inspect{min-width:0;padding:10px;font-size:.8rem}#inspect h3{margin-bottom:2px;font-size:.92rem;overflow-wrap:anywhere}#inspect p{font-size:.76rem}
#inspect dl.kv{grid-template-columns:1fr}#inspect .chip{font-size:.6rem;white-space:normal}#inspect th,#inspect td{padding:3px 4px;font-size:.7rem}
.chips{display:flex;flex-wrap:wrap;gap:4px;margin:6px 0}.chip{font:600 .68rem var(--mono);padding:2px 7px;border-radius:999px;background:var(--sunk);color:var(--ink)}
.chip.flag{background:var(--warn-bg);color:var(--warn)}
dl.kv{display:grid;grid-template-columns:1fr 1fr;gap:4px 10px;margin:8px 0}dl.kv div{display:grid}dt{font:600 .64rem var(--mono);text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}dd{margin:0;font-size:.86rem;font-variant-numeric:tabular-nums}
.splist{display:flex;flex-wrap:wrap;gap:3px;max-height:190px;overflow:auto}
button.sp{font:inherit;font-size:.76rem;display:inline-flex;gap:5px;align-items:center;border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:4px;padding:1px 6px;cursor:pointer}
button.sp i,.yeargrid li i{width:8px;height:8px;border-radius:50%;flex:none;display:inline-block}
.tbl{overflow-x:auto;border:1px solid var(--line);border-radius:6px;background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:.8rem;font-variant-numeric:tabular-nums}
th,td{padding:4px 7px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{font:600 .64rem var(--mono);text-transform:uppercase;letter-spacing:.04em;color:var(--muted);background:var(--sunk)}
td.num,th.num{text-align:right}tr:last-child td{border-bottom:0}
section#sim{margin-top:22px;display:grid;gap:12px}
.simhead{display:block}
.params{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:end}.params label{display:grid;gap:2px;font-size:.78rem;color:var(--muted)}
.params label.ck{display:flex;color:var(--ink)}
#simNote{color:var(--warn);font-size:.86rem}
.yeargrid{min-width:820px}.yeargrid td{padding:3px;width:22%}.yeargrid th[scope=row]{white-space:nowrap;font-family:var(--mono)}
button.cast{all:unset;box-sizing:border-box;display:block;width:100%;padding:5px 7px;border-radius:5px;cursor:pointer;border:1px solid transparent}
button.cast:hover{border-color:var(--line)}button.cast.on{border-color:var(--accent);background:var(--sunk)}
button.cast:focus-visible{outline:2px solid var(--accent)}
button.cast ul{list-style:none;margin:2px 0;padding:0;display:grid;gap:1px}.yeargrid li{display:flex;gap:5px;align-items:center;font-size:.78rem;line-height:1.3}
.yeargrid li.apex{font-weight:700}.yeargrid em{font-style:normal;font:600 .6rem var(--mono);text-transform:uppercase;color:var(--accent)}
.built{font:600 .6rem var(--mono);color:var(--muted);text-transform:uppercase}.verm{font-size:.72rem;color:var(--muted);margin:2px 0 0}
.warnline{font-size:.7rem;color:var(--warn);margin:2px 0 0}
.tabs{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px}.tabs button{font:inherit;font-size:.8rem;border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:999px;padding:3px 11px;cursor:pointer}
.tabs button[aria-selected="true"]{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}
.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;margin-bottom:10px}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:7px 10px;display:grid;gap:1px}
.tile span{font-size:.72rem;color:var(--muted)}.tile b{font:700 1.15rem var(--serif);font-variant-numeric:tabular-nums}.tile em{font-style:normal;font-size:.72rem;color:var(--muted)}
.chartrow{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);gap:14px}
.chart{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:10px 12px;min-width:0}
.chart h4{margin:0 0 6px}.chart h4 .note{font-family:var(--sans);font-weight:400}
svg .axis{fill:var(--muted);font:11px var(--sans)}svg .lab{fill:var(--ink);font:11.5px var(--sans)}svg .val{fill:var(--muted);font:10.5px var(--mono)}
svg .barrow{cursor:pointer}svg .barrow:hover rect:first-child{fill:var(--sunk)}
details.how{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:10px 14px}details.how summary{cursor:pointer;font-family:var(--serif);font-weight:700}
details.how ol{margin:8px 0 4px;padding-left:1.3rem;display:grid;gap:5px;max-width:95ch;font-size:.9rem}
@media (max-width:1180px){.app{grid-template-columns:250px minmax(0,1fr)}#inspect{grid-column:1/-1}}
@media (max-width:780px){.app{grid-template-columns:minmax(0,1fr)}aside#fort{position:static;max-height:none}.chartrow{grid-template-columns:minmax(0,1fr)}h1{font-size:1.5rem}}
@media (prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}
"""

BODY = r"""
<div class="wrap">
<header class="top">
  <span class="eyebrow">Seasonal Wildlife · the cast builder of engine v7.6.1 · DF 53.16 raws</span>
  <h1>Food Web Explorer</h1>
  <p>Every wild creature in the raws, the feeding links seasonal-wildlife imposes on them (each rule switchable, each link clickable for the rule and numbers behind it), and the cast builder, running in the page.
  Choose a fort on the left; the network shows what passes its gates, layer by layer. Then build casts below and change the rules
  (rarity multipliers, pack bonus, the seed, the repeat weight) to see how often each species would be cast.</p>
  <div class="presets" id="presets"><span>Forts</span>
    <button type="button" data-p="coast">Savage tropical coast</button><button type="button" data-p="lake">Calm temperate forest lake</button>
    <button type="button" data-p="brook">Good temperate brook</button><button type="button" data-p="tundra">Evil tundra, murky pools</button>
    <button type="button" data-p="arctic">Savage good arctic coast</button><button type="button" data-p="all">Every creature</button></div>
  <p class="small" id="fortline"></p>
</header>
<div class="app">
<aside id="fort" class="panel" aria-label="Fort">
  <div><span class="lbl">Land biomes</span><div id="biomes"></div></div>
  <details class="nb"><summary><span class="lbl" style="display:inline">Neighbouring tiles</span> <span class="small" id="nbCount"></span></summary>
    <p class="small">The biomes of the region tiles around the embark. DF stocks vermin from them too; one that lives there and is on none of the fort's layers is on the map only (drawn hollow): never cast, but eaten, by the sides its raws give it.</p>
    <div id="nbiomes"></div></details>
  <div><span class="lbl">Surroundings <button type="button" class="linkish" id="surrAll">all</button> <button type="button" class="linkish" id="surrNone">none</button></span><div id="surr"></div>
    <p class="small">Each cell switches on or off by itself; the network shows creatures that fit any cell that is on. Building casts needs exactly one cell on.</p>
    <p class="small" id="tagline"></p></div>
  <div class="row"><label class="ck" for="extinct"><span class="lbl" style="margin:0">Extinct rule</span></label>
    <select id="extinct"><option value="UNTAMED_WILDS">untamed wilds (savage only)</option><option value="WILDERNESS">wilderness (any wild)</option>
    <option value="ISOLATED">isolated regions</option><option value="NONE">none</option></select>
    <label class="ck"><input type="checkbox" id="iso">isolated region</label></div>
  <div><span class="lbl">Water</span>
    <div class="row"><label class="ck"><input type="checkbox" id="w_ocean">ocean</label>
      <select id="oz" aria-label="Ocean zone"><option value="ARCTIC">arctic</option><option value="TEMPERATE">temperate</option><option value="TROPICAL">tropical</option><option value="ALL">every zone</option></select></div>
    <div class="row"><label class="ck"><input type="checkbox" id="w_lake">lake</label><label class="ck"><input type="checkbox" id="w_river">river</label>
      <label class="ck"><input type="checkbox" id="w_brook">brook</label><label class="ck"><input type="checkbox" id="w_pool">murky pool</label></div>
    <div class="row"><span class="small">freshwater zone</span><select id="fz" aria-label="Freshwater zone"><option value="TEMPERATE">temperate</option><option value="TROPICAL">tropical</option><option value="ALL">both</option></select></div>
    <p class="small" id="subNote"></p></div>
  <div><span class="lbl">Caverns</span><div class="row"><label class="ck"><input type="checkbox" id="cv1">1</label><label class="ck"><input type="checkbox" id="cv2">2</label><label class="ck"><input type="checkbox" id="cv3">3</label></div>
    <label class="ck"><input type="checkbox" id="assign">your cavern picks (off: DF's raw depth)</label></div>
</aside>
<section id="view" aria-label="Network">
  <div class="toolbar">
    <div><span class="lbl">View</span><div class="viewtabs" id="tabs" role="tablist"></div></div>
    <div><span class="lbl">Layer</span><div class="seg" id="layer"></div></div>
    <div><span class="lbl">Season</span><div class="seg" id="season"></div></div>
  </div>
  <div class="toolbar">
    <div><span class="lbl">Colour</span><div class="seg" id="color"></div></div>
    <div><span class="lbl">Shape</span><div class="seg" id="shape"></div></div>
    <div><span class="lbl">Layout</span><div class="seg" id="lay"></div></div>
    <div><span class="lbl">Show links</span><div class="seg" id="edges"></div></div>
    <div><label class="ck"><input type="checkbox" id="verm">vermin</label></div>
    <div><label class="lbl" for="search">Find</label><input type="search" id="search" list="names" placeholder="type to light matches" autocomplete="off"><datalist id="names"></datalist></div>
  </div>
  <div><span class="lbl">Feeding links: the rules seasonal-wildlife applies (engine default in brackets)</span><div id="fams" class="fams"></div></div>
  <p class="small" id="searchNote"></p>
  <div id="netbox"><canvas id="net" aria-label="Food web network: scroll to zoom, drag to pan, click a creature or a link"></canvas><div id="tip" hidden></div><div id="edgepop" hidden></div></div>
  <div id="legend"></div>
</section>
<aside id="inspect" class="panel" aria-live="polite"></aside>
</div>

<section id="sim" aria-label="Cast simulator">
  <h2>Build casts</h2>
  <p class="note">The engine's cast builder on the fort above: all 28 season casts of a year, built at once in a random order, as at embark.
  One year shows the casts; many years show how often each species is cast. Pin a run as the baseline, change a rule, and run again to compare.</p>
  <p id="simNote" hidden>Switch exactly one surrounding on (one cell of the matrix) to build casts; several cells are for browsing the network.</p>
  <div class="simhead">
    <div class="params">
      <label>animal people ×<input type="number" id="p_ap" step="0.05" min="0"></label>
      <label>giants ×<input type="number" id="p_gi" step="0.05" min="0"></label>
      <label>pack bonus ×<input type="number" id="p_pack" step="0.5" min="0"></label>
      <label>apex pack ×<input type="number" id="p_apack" step="0.5" min="0"></label>
      <label>repeat weight ×<input type="number" id="p_reuse" step="0.01" min="0"></label>
      <label>high value, top share<input type="number" id="p_hv" step="0.05" min="0" max="1"></label>
      <label>growth links<span class="seg" id="p_links"></span></label>
      <label class="ck"><input type="checkbox" id="p_seed">seed each cast</label>
      <label class="ck"><input type="checkbox" id="p_weird">cavern weirdness tilt</label>
      <label class="ck"><input type="checkbox" id="p_guar">cavern web guarantee</label>
      <button type="button" class="linkish" id="p_reset">engine defaults</button>
    </div>
  </div>
  <div class="row">
    <button type="button" class="btn" id="run1">Build one year</button>
    <label class="small">years <select id="p_years"><option>50</option><option>100</option><option>200</option><option>500</option><option>1000</option></select></label>
    <button type="button" class="btn primary" id="runN">Run many years</button>
    <button type="button" class="btn" id="pin">Pin as baseline</button>
    <span class="small" id="runState"></span><span class="small" id="pinState"></span>
  </div>
  <h3>One year <span class="note">click a cast to light it in the network</span></h3>
  <div id="year"></div>
  <h3>Across the years</h3>
  <div id="stats"></div>
  <details class="how"><summary>How the cast builder decides</summary>
  <ol>
    <li><b>Gates.</b> A creature is a candidate when it is wild and natural, its BIOME (with the tool's own additions and limits) names one of the fort's biomes, and it passes that biome's savagery, good/evil and extinct rules.</li>
    <li><b>Layers.</b> Land-ground, land-flying, ocean, freshwater (one cast: lake, else river or brook, else murky pool) and caverns 1 to 3 (your cavern picks, or DF's raw depth).</li>
    <li><b>Slots.</b> Each layer has a slot table (apex, meso, grazer, ground prey, flier, fish, pelagic, shore, waterbird, swimmer, sentient, vermin); a creature's habitat, guild and apex eligibility say which slots it can take.</li>
    <li><b>Apex.</b> A weighted draw among the eligible apexes in season: the square root of group size (body × mean pack) against the largest, times the pick weight.</li>
    <li><b>Seed.</b> One high-value species (war-trainable, or the top share by pet value or by body size; never sentient), not on land-flying.</li>
    <li><b>Growth.</b> Candidates linked to any member (it eats a member or a member eats it) fill the emptiest slot, by pick weight; a slot nothing links to is filled anyway. Pick weight: pack hunters ×pack bonus, animal people ×, giants ×, ×repeat weight per cast already holding the species this year (a sentient seat counts only against its later sentient seats), and in caverns the weirdness tilt.</li>
    <li><b>Sentients.</b> Every layer has one sentient slot; a sentient fills only that slot (the harpy and nightwing also keep their evil flying apex seat).</li>
    <li><b>Cavern web guarantee.</b> A cavern cast with no prey or no predator takes one.</li>
    <li><b>Vermin.</b> What the members eat first, one per vermin class, then any.</li>
  </ol>
  <p class="small"><b>New Rules</b> is the rule set we are building together, one rule at a time; its current rules are listed in the switch's tooltip and in every link's popup. It holds DF's own diet tokens, the vermin the tool feeds, and mass and numbers trimmed by the vermin side rules.</p>
  <p class="small"><b>The network's links are the rules seasonal-wildlife applies to creatures</b> (engine v7.6.1; switch each on or off above the network):
  <b>hunting pairs written in play</b> (the ecology relation write, on: an armed predator (not wholly BENIGN, a raptor, a cast predator slot, or a cavern civ race) and a target unit whose habitat it reaches, two water animals sharing a water body, never a raptor's prey over twice its mass, never a civ race unless the hunter is a non-civ apex guild, the hunting group at least 5% of the prey's mass (mean group size stands in for the live pack), and, under casts, only a pair the season's cast links);
  <b>vermin the tool feeds</b> (GOBBLE_VERMIN_CLASS written onto consumers, on: small land insectivores take ground bugs, soil life and colony insects; waterbirds and fish-eaters small fish; raptors small birds, bats and small mammals; land birds flying insects; snakes small mammals and herps; plus the guild rows ML, AW, MW, RP and cavern LB, over the tool's own SWV vermin classes; since 17 Oct by side too, as composite classes SWV_type@SIDE: a giant, a land-ground apex and an ocean apex eat no vermin, a land-flying apex flying vermin only, an ocean or freshwater creature no ground vermin, a freshwater-only creature no ocean vermin and an ocean-only creature no freshwater vermin (one on both waters eats both), a land-ground predator no flying, ocean or freshwater vermin, the duck, goose and swan every freshwater vermin, every land-ground prey animal (not a predator, not an apex there, not a giant, not a grazer) every land-ground vermin, every shore prey every ocean and freshwater vermin, every non-giant flying prey every flying insect, and every giant flying prey but the giant moth and giant monarch every non-insect flying vermin);
  <b>DF's own diet tokens</b> (always); <b>hunting flags</b> (DIVE_HUNTS_VERMIN and HUNTS_VERMIN written by the tool, off by default); <b>the cast-growth ladder</b> (ROSTER.FP.eats, which the hunting pairs pass through); <b>mass and numbers</b> (MODEL eats, used only by coupling, off by default; since 17 Oct a vermin only from a side the consumer may eat from, by the same rules as the vermin the tool feeds without the land-ground predator rule).
  No apex (a species eligible for the apex seat on any layer it is on) is ever prey (user 17 Oct).
  No grazer eats anything, under any rule (user 17 Oct).
  No ocean-shore predator (an ocean shore seat, and a predator or an ocean apex) eats a land-ground creature, and no land-ground apex eats one (user 19 Oct).
  The osprey and the eagle eat every ocean and freshwater fish prey, every ocean and freshwater fish vermin, every land mammal and herp vermin, and every ground snake that is not an apex; the great horned owl every land mammal and herp vermin and the hare; whatever the other bars, reach or size rules say (user 19 Oct).
  No ocean or freshwater apex or predator links either way with a land-ground or land-flying creature unless either can take a shore seat (a vermin that also lives in water counts as water vermin; such a hunter takes no cavern vermin unless it is in the caverns). The gigantic squid is read as the giant octopus, and the giant leopard seal as the leopard seal, for every link and the slots that steer them; the leopard seal is no apex and every ocean apex takes it; the giant leopard seal is an ocean apex (user 17 Oct).
  No rule the tool applies links a land-ground apex or predator to anything on land-flying, vermin included (a flying hunter preying on the ground is kept; user 17 Oct); only the hunting flags, off by default, still do: DF's HUNTS_VERMIN takes any vermin.
  In the Levels layout an apex or predator that eats nothing under the links switched on is drawn in the prey tier.
  Vermin links reach anything in the same realm (the surface, or one cavern); hunting pairs and the ladder need a shared layer. A snake is read from its BODY tokens (no legs, feet or toes), as the engine reads no STANCE part.</p>
  <p class="small"><b>Raws links</b> are the only creature-to-creature diet tokens in DF 53.16's vanilla raws: GOBBLE_VERMIN_CLASS (kiwi, hedgehog, pangolin, duck, goose, peafowl and turkey eat the EDIBLE_GROUND_BUG vermin: ant, beetle, large roach, thrips), GOBBLE_VERMIN_CREATURE (unused in vanilla) and the peregrine's DIVE_HUNTS_VERMIN (any vermin). CARNIVORE, LARGE_PREDATOR and BONECARN name no prey; SPECIFIC_FOOD names plants. <b>Engine ladder links</b> are the v7.6.1 engine's feeding test, kept for comparison: a higher trophic tier eats a lower one when its habitat reaches the other's; shore animals and waterbirds take aquatic creatures up to their own size; vermin by diet class. Growth in the simulator follows the links you choose under Build casts.
  Not modelled: DF's own stocking on a real fort (stocked water entries, the zone read from stocked species), exhaustion stand-ins, placed thieves and apexes, and everything after the cast (FREQUENCY, caps, pauses).
  Source: castsim foodweb_export.py and foodweb_sim.js, checked against the desk simulator (exact pools, layers and slots; cast rates within sampling noise).</p>
  </details>
</section>
</div>
<div id="ctip" hidden></div>
"""


def main():
    data = DATA.read_text()
    simjs = (HERE / 'foodweb_sim.js').read_text()
    appjs = (HERE / 'foodweb_app.js').read_text()
    html = f"""<title>Food Web Explorer</title>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bitter:wght@500;700&family=Atkinson+Hyperlegible:wght@400;700&family=JetBrains+Mono:wght@400;600&display=swap">
<style>{CSS}</style>
{BODY}
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<script>window.FWDATA = {data.replace('</', '<\\/')};</script>
<script>{simjs}</script>
<script>{appjs}</script>
"""
    OUT.write_text(html)
    print('wrote', OUT, len(html))


if __name__ == '__main__':
    main()
