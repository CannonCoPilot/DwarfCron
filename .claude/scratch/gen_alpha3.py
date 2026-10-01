#!/usr/bin/env python3
"""Build the alpha 3 walkthrough (seasonal-wildlife v7.0 @ 1e65e03, DFHack 53.16-r2) from Alpha Two's page.

Copied from gen_alpha2.py (1 Oct 2026); gen_alpha2.py is left as it is. Styles and script come from Alpha Two's
generated page (alpha2-walkthrough.html), with its own storage key, report title, a guard on Load, and the
responsive and step-row additions below. Steps are data in this script: edit here, never the HTML.

Every window key is from the v7.0 GUI's HotkeyLabels and onInput (scripts/gui/seasonal-wildlife.lua at 1e65e03,
unchanged from v6.6's f22fa30) and the screen dumps of validate-full 20261001-074833. Every console verb's syntax is
from the engine's dispatcher (scripts/seasonal-wildlife.lua, dispatch(), lines 7509-8124) and its usage strings.
"""
import html
import re
from pathlib import Path

HERE = Path('/Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch')
SRC = HERE / 'alpha2-walkthrough.html'
OUT = HERE / 'alpha3-walkthrough.html'
a2 = SRC.read_text(encoding='utf-8')
style = re.search(r'<style>.*?</style>', a2, re.S).group(0)
fonts = re.search(r'<link rel="stylesheet"[^>]*>', a2).group(0)
script = re.search(r'<script>.*?</script>', a2, re.S).group(0)

# ---- script: key, report title, every tag stripped from titles, a guard on Load ----
def sub1(old, new):
    global script
    assert old in script, old[:60]
    script = script.replace(old, new)

sub1("var KEY='sw-alpha-two-v1';", "var KEY='sw-alpha-three-v1';")
sub1("lines.push('# Seasonal Wildlife alpha trial two (UI, v6.6)');",
     "lines.push('# Seasonal Wildlife alpha trial three (window and console, v7.0 on DFHack 53.16-r2)');")
sub1("lines.push('- Date: '+(m.tDate||''));",
     "lines.push('- Date: '+(m.tDate||'')); lines.push('- Page: Alpha Three (build v7.0 @ 1e65e03, unreleased; 13 decisions open)');")
sub1("var tg=h.querySelector('.tag'); if(tg)tg.remove();",
     "h.querySelectorAll('.tag').forEach(function(x){x.remove()});")
sub1("var n=0;\n    steps.forEach",
     "var mt=m._meta||{};\n"
     "    if((mt.page&&mt.page!=='alpha3')||(!mt.page&&/v6\\./.test(mt.tVer||''))){msg.textContent='These marks are for another page (Alpha Two or earlier): its step numbers do not match this one. Nothing loaded.';return}\n"
     "    var n=0;\n    steps.forEach")
assert 'btnLoad' in script

# ---- style additions ----
extra_css = """
.recheck.wide td:first-child,.recheck.wide td:last-child{white-space:normal;font:inherit;color:inherit}
.recheck.wide td:first-child{font-weight:600;min-width:9ch}
.recheck.wide td{min-width:14ch}
.tag.new{color:var(--moss);background:var(--moss-soft)}
.tag.r2{color:var(--amber);background:var(--amber-soft)}
.step .basis,.step .pend{display:grid;grid-template-columns:64px minmax(0,1fr);gap:10px;font-size:0.86rem}
.step .basis>span:first-child,.step .pend>span:first-child{font:600 0.7rem/1.9 "Source Sans 3",sans-serif;letter-spacing:0.1em;text-transform:uppercase;color:var(--ink-2)}
.step .basis>span:last-child{color:var(--ink-2)}
.step .pend>span:last-child{background:var(--amber-soft);border-left:3px solid var(--amber);padding:4px 8px;border-radius:0 4px 4px 0}
code{overflow-wrap:anywhere}
.cmdref{border-collapse:collapse;font-size:0.88rem;margin-top:14px;width:100%}
.cmdref th,.cmdref td{text-align:left;padding:5px 8px;border-bottom:1px solid var(--rule);vertical-align:top}
.cmdref th{font-weight:600;color:var(--ink-2);font-size:0.78rem;letter-spacing:0.06em;text-transform:uppercase}
.cmdref td:first-child{font:0.82rem "JetBrains Mono",ui-monospace,monospace;min-width:16ch}
.phase .note+.note,.phase .note+.callout,.phase .callout+.note,.phase .callout+h3,.phase .note+h3{margin-top:12px}
.phase h3.sub{margin-top:22px}
ul.plain{margin:10px 0 0;padding-left:20px;max-width:72ch}
ul.plain li{margin:4px 0}
@media (max-width:560px){
  .wrap{padding:0 16px}
  .step{grid-template-columns:1fr;padding:12px}
  .step .id{padding:0 0 4px}
  .step .do,.step .expect,.step .watch,.step .basis,.step .pend{grid-template-columns:1fr;gap:2px}
  .phase-head{grid-template-columns:1fr;gap:6px}
  .phase-head .why,.phase-head .need{grid-column:1}
}
</style>"""
style = style.replace('</style>', extra_css)

E = html.escape
def k(*keys):
    return '+'.join(f'<kbd>{x}</kbd>' for x in keys)
def c(cmd):
    return f'<code>{E(cmd)}</code>'
def sw(rest):
    return c('seasonal-wildlife ' + rest)

P = []
def phase(num, title, why, steps, pre='', pid=None):
    P.append((num, title, why, steps, pre, pid or f'p{num}'))

def S(sid, title, do, expect, watch='', tags=(), src='', dec=''):
    return dict(id=sid, title=title, do=do, expect=expect, watch=watch, tags=tags, src=src, dec=dec)

RC = lambda x: ('rc', 're-check ' + x)
NEW = lambda x: ('new', 'new ' + x)
R2 = ('r2', 'r2')
RUN = 'run 074833'   # validate-full 20261001-074833 on v7.0 1e65e03 (DFHack 53.16-r1.1)

# ===================================================================================================== tables
CHANGES = """<div class="tablewrap"><table class="recheck wide"><thead><tr><th>Release</th><th>When, commit</th><th>What a player sees</th><th>Record</th></tr></thead><tbody>
<tr><td>v6.7.0</td><td>28 Sep, c3b85c7 (master)</td><td>The Roster’s ODDS column shows an out-of-season species’ in-season share in brackets, <code>(12%)</code>. Add invasive leaves the new species active with one season (or inactive) at once. Animal people take role, habitat, size, mass, group and diet from their root animal.</td><td>STATE addendum 95; validate-full 20260928-145349: 178 pass, 0 fail</td></tr>
<tr><td>v6.8.0</td><td>29 Sep, b450362, 58a667e, f82be91, 04c06aa (master)</td><td>Console verbs <code>roster [KEY [active|inactive]]</code> and <code>seasons KEY &lt;SpSuAuWi|all&gt;</code> under the one roster rule. The browser companion <code>seasonal-wildlife-web</code>: a page on 127.0.0.1 with Status, Species, Food web and Ledger &amp; settings tabs, Steam or ASCII tiles.</td><td>No STATE addendum (engine changelog only); validate-full 20260930-125813 (<code>--only v68</code>): roster and seasons verbs pass, web serve/guard/cmd/stop pass</td></tr>
<tr><td>v6.9.0</td><td>30 Sep, 1abe109 (master, released and pushed)</td><td>A predator is armed when it is not BENIGN; the relation write reaches only where the predator can go. Water draws honour NO_&lt;season&gt;; pelagic giants draw less often. Land groups at once default to auto, floor(√embark tiles)+1. Three new Panel rows: Exhaustion and replacement (on), Scavenging (opt-in), Quiet wildlife fights (on). Console verbs <code>exhaust</code>, <code>alerts</code>, <code>curious</code>, <code>scavenge</code>, <code>limits … groups auto</code>.</td><td>No STATE addendum (engine changelog, git log); validate-full 20260930-124923: 192 pass, 0 fail</td></tr>
<tr><td>v7.0.0</td><td>1 Oct, branch v7.0 @ 1e65e03; 26 commits past master</td><td>Twenty-six <code>cfg.v7</code> switches, console only (<code>seasonal-wildlife v7</code>): alignment-managed good and evil wildlife, the largest male leads, groups at once per layer, water body and cavern, the tool owns seasons, the solitary-hunter package, a pack-mass floor, map-wide scavenging and its water and flier fallbacks, fishers (off), cavern civ races hunt and are hunted, forgotten-beast safety, the relation sweep, domestic prey (off), sponges, gate drain, vermin gobble, the roster builder (<code>roster build</code>), outgun warnings, realms (off).</td><td>STATE addenda 96, 96b, 96d, 96e, 97 (their “not deployed” and “not merged” notes are stale: merged and deployed); validate-full 20261001-074833: 214 pass, 0 fail, 30 not testable on the rig fort, 13 backlog, 2 doc drift</td></tr>
</tbody></table></div>"""

ANOM = """<div class="tablewrap"><table class="recheck"><thead><tr><th>Alpha 2</th><th>What round 1 found (v6.6.0, 28 Sep)</th><th>Fix</th><th>Re-check at</th></tr></thead><tbody>
<tr><td>4.3</td><td>Alt+O stored the odds, but the ODDS column showed <code>-</code> for every species out of season, so the key looked dead.</td><td>v6.7.0 c3b85c7: the in-season share in brackets; column five wide</td><td>2.1, 4.3</td></tr>
<tr><td>8.1</td><td>Add invasive put AARDVARK_MAN on the embark with no roster state at all until a later pass.</td><td>v6.7.0 c3b85c7: the roster pass runs at once; the status line names the result</td><td>8.1</td></tr>
<tr><td>10.1</td><td>The pyramid draws no level labels (the page was corrected); animal people and odd pairs showed as prey.</td><td>v6.7.0 c3b85c7: animal people mirror their root animal (addendum 95); the otter–jaguar-man pair left as is</td><td>3.2, 10.1, 10.2</td></tr>
<tr><td>5.1</td><td>Fill to targets with no target named Shift-B, a target retired in v6.4.</td><td>e507876 (v6.6.0, during the round)</td><td>5.1</td></tr>
<tr><td>17.1</td><td>The reload’s ledger showed a reset line still saying “abundances to 50”.</td><td>f80d072 (v6.6.0, during the round)</td><td>7.2</td></tr>
</tbody></table></div>"""

DECISIONS = """<div class="tablewrap"><table class="recheck"><thead><tr><th>Decision</th><th>What is proposed (open-items.json, category decisions)</th><th>Steps whose result depends on it</th></tr></thead><tbody>
<tr><td>cadence</td><td>Ecology pass every 3,000 ticks instead of 1,500 (SW1/SW1R: no effect of 500, 1,500 or 6,000).</td><td>1.2, 1.3, 11.2</td></tr>
<tr><td>nudge</td><td>Nudge off by default (SW1/SW1R: no effect).</td><td>1.2, 11.2, 12.1</td></tr>
<tr><td>sneak</td><td>pack_sneak 0 and retire the per-unit SNEAK write (SW2/SW2R, STL/STL2).</td><td>0.4, 19.2</td></tr>
<tr><td>x3</td><td>Remove the builder’s x3 pack-hunter pick bonus (SW7; design R11).</td><td>20.2, 20.3</td></tr>
<tr><td>apex</td><td>Drop the apex step from the FREQUENCY ladder; steer apexes by placement and stock (SW4, S8Cb).</td><td>20.2</td></tr>
<tr><td>cavern cap</td><td>Relabel cavern groups at once as a soft target (SW5: caps 1 and 2 never bind on DF’s natives).</td><td>11.3, 12.1</td></tr>
<tr><td>water 2</td><td>Optional: water groups at once default 2 per body (SW6, thin evidence).</td><td>11.3, 18.1</td></tr>
<tr><td>swimmers</td><td>Should carnivorous swimmers (alligators, crocodiles, sharks) count as scavengers?</td><td>18.5, 21.8</td></tr>
<tr><td>AP cap</td><td>A group-size cap for animal people in caverns (plump helmet men: 54 and 180 a season on BOATS).</td><td>20.4, 21.4</td></tr>
<tr><td>savage</td><td>Add invasive places SAVAGE species on calm maps itself, or refuses them (INV2: DF drew none).</td><td>8.2</td></tr>
<tr><td>push</td><td>Push DwarfCron Dev and seasonal-wildlife v7.0 (nothing pushed; v7.0 unmerged).</td><td>0.4 (the build you can get)</td></tr>
<tr><td>FPS6</td><td>FPS6 (world size x history on fort speed) is on hold.</td><td>23.2</td></tr>
<tr><td>lake apex</td><td>The temperate lake has no apex about half the time again, since fishers went off.</td><td>20.4, 21.3</td></tr>
</tbody></table></div>"""

VERBS = """<div class="tablewrap"><table class="cmdref"><thead><tr><th>Verb (type after <code>seasonal-wildlife</code>)</th><th>What it does</th><th>Step</th></tr></thead><tbody>
<tr><td>status</td><td>biomes, layers, limits, patterns, ledger, cavern, water, hunting, gobble and fuse lines, the map’s counts, the embark subset</td><td>16.1</td></tr>
<tr><td>now · enable · disable</td><td>apply the season’s roster once; rotation on or off</td><td>16.1</td></tr>
<tr><td>roster [KEY [active|inactive]]</td><td>counts per layer, or one species’ state (v6.8)</td><td>16.2, 16.3</td></tr>
<tr><td>seasons KEY &lt;SpSuAuWi|all&gt;</td><td>set seasons; <code>none</code> is refused (v6.8)</td><td>16.4, 16.5</td></tr>
<tr><td>undo</td><td>undo the last roster edit, window or console</td><td>16.6</td></tr>
<tr><td>stock|odds|size KEY [N|clear] · call KEY</td><td>one species’ stock, odds, group size; call a wave</td><td>16.7</td></tr>
<tr><td>limits [land|water|cavern] [groups N|auto] [ceiling N]</td><td>groups at once and ceiling; <code>auto</code> refused on water; <code>quota</code> is the retired alias</td><td>18.1</td></tr>
<tr><td>pattern [land|water|cavern] &lt;steady|burst|trickle|dawn|follow&gt;</td><td>arrival pattern per layer</td><td>16.8</td></tr>
<tr><td>sendoff [land|cavern]</td><td>every gated group of a layer walks off</td><td>16.8</td></tr>
<tr><td>layer &lt;land|water|cavern|deep&gt; on|off</td><td>a layer on or off</td><td>16.8</td></tr>
<tr><td>ledger [N] [kind] [land|water|cavern] | clear</td><td>the tool’s writes</td><td>16.8</td></tr>
<tr><td>groups [on|off|coupling on|off|ecology on|off|now|cavern on|off|max N|livestock on|off|nudge T K R|pack N|cohesion …|hold TOKEN DAYS|dismiss TOKEN]</td><td>groups, the ecology switch and its levers</td><td>21.1</td></tr>
<tr><td>water [on|off|now|survey|countdown N]</td><td>the water draw (<code>target</code>, <code>cadence</code> retired)</td><td>16.8</td></tr>
<tr><td>caverns [survey] · cavern</td><td>cavern bands; <code>cavern</code> prints “retired in v6.5”</td><td>16.8</td></tr>
<tr><td>vermin [classes|defaults|&lt;family&gt; [on|off|seasons …|abundance N]]</td><td>vermin by family; <code>classes</code> is v7.0</td><td>21.7</td></tr>
<tr><td>hunting [on|off] · irruption [on|off|…]</td><td>vermin-hunting flags; cavern irruptions</td><td>16.8</td></tr>
<tr><td>exhaust [on|off|now] · alerts [on|off] · curious [TOKEN resident|thief] · scavenge [on|off|now|radius N]</td><td>v6.9 jobs</td><td>18.2–18.5</td></tr>
<tr><td>v7 [KEY on|off|N | fisher TOKEN on|off | apply]</td><td>the v7 switches (numbers 0 to 10)</td><td>19.1–19.4</td></tr>
<tr><td>roster build [land|water|cavern] · roster outgun [land|water|cavern]</td><td>the roster builder; the outgun survey</td><td>20.1–20.5</td></tr>
<tr><td>realm [name|auto|off]</td><td>the embark’s realm for the builder</td><td>20.6</td></tr>
<tr><td>sponges [now]</td><td>sponge ribbons on the ocean floor</td><td>21.6</td></tr>
<tr><td>classes · class TOKEN natural|auto · preset · place TOKEN [n] [layer [depth]]</td><td>class review and override; re-apply the biome preset; headless placement (a test tool)</td><td>not stepped</td></tr>
</tbody></table></div>"""

# ===================================================================================================== phase Δ
phase('Δ', 'What changed since Alpha Two',
  'Alpha Two tested v6.6.0. Four builds later the rig runs v7.0, and the user upgraded DFHack to 53.16-r2 on 1 October. Read this before you start; the tables are the map from Alpha Two to this page.',
  [],
  pid='pchanges',
  pre='<div class="note"><b>Unreleased build.</b> This page targets <code>seasonal-wildlife</code> branch <b>v7.0 @ 1e65e03</b> as deployed on the test rig. v7.0 is not merged to master and not pushed; the released version is v6.9.0 (master 1abe109). Thirteen decisions about its defaults are open. A step whose result depends on one says which, and what each choice would change.</div>'
      '<div class="note"><b>DFHack 53.16-r2.</b> The rig moved from 53.16-r1.1 to 53.16-r2 (02e77acf) at about 08:55 on 1 October. Every validation so far, v7.0’s 214 passes included, ran on r1.1; nothing has run on r2. Steps tagged <b>r2</b> rest on something r2 changed: Units::teleport occupancy (the nudge, the water draw and placement, scavenging fallbacks), the persistent site-data fix on reclaimed forts, and gui/launcher (it hides “unavailable” tools unless dev mode, Ctrl-D, is on).</div>'
      '<h3 class="sub">Four releases since v6.6</h3>' + CHANGES +
      '<h3 class="sub">Alpha Two’s round-one anomalies, and where to re-check them</h3><p class="muted" style="margin-top:6px;max-width:72ch">The rig played round 1 on BOATS (data/alpha2/round1: 59 pass, 3 anomalies). Steps here are renumbered; this table and the <b>re-check</b> tags point to the new numbers.</p>' + ANOM +
      '<h3 class="sub">The thirteen open decisions</h3>' + DECISIONS +
      '<h3 class="sub">Window keys: what changed</h3><p style="margin-top:6px;max-width:72ch">None. The GUI script’s HotkeyLabels are identical between v6.6 (f22fa30) and v7.0 (1e65e03); the window changed in four places only: the ODDS column, the Live tab’s groups line, the Fill hint, and the Add invasive status line. Two keys Alpha Two never named are stepped here: <kbd>Alt</kbd>+<kbd>P</kbd> (the Panel from any tab) and <kbd>W</kbd> on the Live tab. Three hotkey labels on the Roster and two on the species detail draw clipped (2.1, 3.1); they were clipped on v6.6 too and round 1 passed them.</p>')

# ===================================================================================================== 0
phase(0, 'Before you start',
  'Pick a fort, back it up, and check you are on the build and the DFHack this page describes.',
  [
   S('0.1', 'Choose the fort',
     'Use a copy of a fort with surface wildlife and, ideally, an ocean or river and a cavern your dwarves have opened. An ocean fort exercises sponges and the water bodies; an open cavern exercises civ races and per-cavern groups.',
     'Nothing yet. Note the biomes, the embark size in tiles (4x4 = 16), whether water touches the map, and whether a cavern is open.',
     'Write the population, year and season in the note. The rig’s forts: CTRL (4x4 temperate shrubland, 7 dwarves, no water on the surface layer), BOATS (tropical shrubland, ocean, salt river), OCEAN2 (ocean).',
     src='Fort facts: ctrl-fort-facts; ECO S8B/S8O fort list (findings.md).'),
   S('0.2', 'Back it up',
     'Copy the save folder before you open the window.',
     'A fort that never opens the window is never touched, so the copy is your control.',
     'v7.0 writes many more raws than v6.6 while it runs: All off on CTRL restored 743 v7 raw writes. Steps 7.2, 20.2 and 21.2 change a lot; do them on the copy.',
     src=f'{RUN}: mech.save.untouched PASS; screen C0c-panel-alloff.'),
   S('0.3', 'Check DFHack is 53.16-r2',
     'Open the launcher (<kbd>`</kbd>) and read its title, or type ' + c('help') + ' in the DFHack console; then type ' + sw('status') + '.',
     'The version reads <b>53.16-r2</b>. <code>status</code> prints its Biomes, Layers and limits lines with no Lua error. If the launcher does not offer <code>gui/seasonal-wildlife</code>, r2 may be hiding it as unavailable: turn on dev mode with <kbd>Ctrl</kbd>+<kbd>D</kbd> in the launcher, or type the command.',
     'Any red traceback naming seasonal-wildlife; the DF console log (stderr.log in the game folder) holds it. Nothing on this page has been seen on r2 yet.',
     tags=(R2,), src='BRIEF (1 Oct): DFHack upgraded 08:55, dfhack.dll reports 53.16-r2; cli.status PASS on r1.1 (run 074833).'),
   S('0.4', 'Check the tool is v7.0',
     'Type ' + sw('v7') + '.',
     'Twenty-seven lines, one per v7 setting with its value (aligned, builder, cave_aligned, civ_hunt, civ_prey, domestic, fanciful, fb_safe, fish_breathe, fisher_list, fishers, gate_drain, gobble, gobble_creature_fallback, layer_groups, leader_male, outgun, outgun_cap, pack_floor, pack_sneak, realms, scav_ext, scav_mapwide, seasons_own, solo, sponges, sweep), then <b>embark alignment: …</b>. Defaults: fishers, fish_breathe, domestic, outgun_cap and realms <b>false</b>; pack_floor 0.05, pack_sneak 0.25, outgun 2.0, gobble_creature_fallback 3; the rest <b>true</b>.',
     'If the tool prints its Usage line instead, you are on v6.9 or older and phases 19 to 21 do not apply. gobble_creature_fallback is wider than its column and pushes its value right.',
     tags=(NEW('v7.0'),), src=f'{RUN}: cli.v70.v7 PASS (the list as printed); engine defaultConfig line 499.',
     dec='<b>sneak</b>: if pack_sneak 0 is adopted, that line reads 0. <b>push</b>: until v7.0 is merged and pushed, only the rig has this build.'),
   S('0.5', 'Turn on the frame counter',
     'In Settings, show the frame rate. Read it unpaused for a minute at your usual speed.',
     'A baseline for phase 23. A paused game shows a meaningless high number.',
     'Two loads of the same fort differ by 10–15 % on their own, and one long session loses up to 28 % by itself.',
     src='fps-load-facts (session length dominates: 300k ticks in one process −28 %).'),
  ])

# ===================================================================================================== 1
phase(1, 'First open: Overview and Panel',
  'The window opens on the Overview. The Panel lists every switch the window has and how long each job takes. v6.9 added three rows; no v7 switch is on it.',
  [
   S('1.1', 'Open the window',
     'Type ' + c('gui/seasonal-wildlife') + ' in the console, or pick it in the launcher.',
     'A window titled <b>Seasonal Wildlife</b> with nine tabs on one row: Overview, Panel, Roster, Seasons, Food web, Live, Layers, Vermin, Ledger. All text plain ASCII.',
     'On r2 the launcher may hide the tool unless dev mode is on (0.3).',
     tags=(R2,), src=f'{RUN}: gui.open, gui.layout, w0.ascii PASS; screen C0-overview.'),
   S('1.2', 'Read the Panel',
     'Click <b>Panel</b>.',
     'SWITCHES: 18 rows plus Map overlay, each <b>[ON]</b> or <b>[off]</b>. New since Alpha Two: <b>Exhaustion and replacement</b> (on), <b>Scavenging</b> (opt-in, off), <b>Quiet wildlife fights</b> (on). Then JOBS with five rows: season roster every 1200 t, groups and gate 300 t, ecology 1500 t, quiet fights 10 t, scavenging 200 t.',
     'The v7 switches are console-only (phase 19). Opt-in rows say <b>(opt-in)</b>: coupling, livestock, scavenging, vermin hunting, irruptions.',
     tags=(NEW('v6.9'),), src=f'{RUN}: gui.tab.panel PASS; screen C0b-panel; engine PANEL.SWITCHES and PANEL.jobs.',
     dec='<b>nudge</b>: if adopted, the Nudge row reads [off] on a new fort. <b>cadence</b>: if adopted, the ecology job reads every 3000 t.'),
   S('1.3', 'Read the job timings',
     'Leave the window open a game day, then press ' + k('R') + ' on the Panel.',
     'Each job shows last and worst in milliseconds against a 50 ms budget; <b>over</b> counts passes above it; every <b>fuse</b> reads intact. On CTRL the rig saw groups worst 79 ms (2 of 107 over), ecology worst 42 ms, quiet fights worst 17 ms over 2,880 runs.',
     'A tripped fuse. A large fort with many groups may push groups and ecology over 50 ms.',
     tags=(RC('R4'),), src=f'{RUN}: w0.timing.jobs PASS; screen C0b-panel.',
     dec='<b>cadence</b>: at 3,000 ticks the ecology job runs half as often; its worst pass should not change.'),
   S('1.4', 'All off, then all on',
     'Press ' + k('X') + ' (All off) and answer Yes; read the status line; then ' + k('A') + ' (All on).',
     'Each asks first. All off turns every job off and reports what it put back: <b>All off: every job stopped; restored N cavern frequencies, N curious-beast flags, N v7 raw writes.</b> (CTRL: 31, 4, 743). The layer rows and Map overlay keep their state: they are settings, not jobs. All on brings the switches back as they were.',
     'A job row still [ON] after All off. A v7 raw left written cannot be seen here; 19.3 counts them.',
     tags=(NEW('v7.0'),), src=f'{RUN}: mech.panel.alloff, mech.v70.restore_all PASS; screen C0c-panel-alloff.'),
   S('1.5', 'The Panel from any tab',
     'From the Roster, press ' + k('Alt', 'P') + '.',
     'The Panel opens. A tripped job shows a banner on the Overview: <b>JOB STOPPED: … -- Alt+P, Enter on the job re-arms it</b>.',
     'Alpha Two never named this key; it has existed since v6.3.',
     src='GUI onInput CUSTOM_ALT_P (gui line 294) and fuseBanner; no validator claim (untested by the validator).'),
   S('1.6', 'Read the Overview',
     'Click <b>Overview</b>.',
     'The date and switches line, the patterns line, a table of what each layer holds (wild animals, groups “N of M”, when the gate reopens), recent groups, the land mass ratio, what is in season, the next boundary with its arrivals and departures, and the last ledger lines.',
     'Two cells use old numbers. The water column reads “N of 12 target”: animals against the water ceiling, with a word retired in v6.5. The caverns column reads “of 2” from the old cavern count, while the Live tab’s limits line says auto per cavern. Note what yours say.',
     src=f'{RUN}: gui.tab.overview PASS; screen C0-overview (“1 of 12 target”, “6 of 2”); GUI refreshOverview line 1840.'),
  ])

# ===================================================================================================== 2
phase(2, 'The roster rule',
  'One rule since v6.3: an active species has at least one season; inactive is the only way to keep one away, on every layer.',
  [
   S('2.1', 'Read the columns',
     'Click <b>Roster</b>.',
     'Columns CREATURE, ROLE, SIZE, HAB, BIOME, SEASON, STOCK, ODDS, act, WHY. ODDS is five wide: an in-season species shows its share, <b>12%</b>; an active one out of season shows the share it would have, in brackets, <b>(12%)</b>. A <b>w</b> after a name marks an aquatic species, <b>~</b> a marsupial. The header counts active species per role and the special creatures left to DF.',
     'Three key labels under the list draw into the next one: <b>Ctrl+f: Send off + ne</b>, <b>Ctrl+w: Stock (row</b>, <b>Ctrl+g: Stock (filte</b>. They were the same on v6.6. Mark it if it misleads you.',
     tags=(RC('4.3'),), src=f'{RUN}: gui.tab.roster, gui.odds.bracket PASS; screens C0-roster, C12-roster-keys; addendum 95.'),
   S('2.2', 'Filters',
     'Cycle ' + k('V') + ' (View: Current, Default, Add invasive), ' + k('C') + ' (category and habitats), ' + k('B') + ' (biome), ' + k('N') + ' (season).',
     'Each changes the rows. Default shows the roster as the embark was first found.',
     'A filter that empties the list without saying why.',
     src=f'{RUN}: gui.k.V, gui.k.C, gui.k.B, gui.k.N PASS.'),
   S('2.3', 'Make a species inactive',
     'Select an active species and press <kbd>Enter</kbd>.',
     'act turns to <b>-</b>, SEASON clears, WHY reads <b>you</b> and today’s date.',
     'Remember the species: 22.1 checks it never arrives.',
     tags=(RC('R1'),), src=f'{RUN}: gui.k.enter, w0.roster.inactive PASS.'),
   S('2.4', 'Make it active again',
     'Press <kbd>Enter</kbd> on the same row.',
     'act turns to <b>Y</b> with <b>exactly one</b> season, from its climate.',
     'No season, or all four.',
     tags=(RC('R1'),), src=f'{RUN}: w0.roster.activate PASS.'),
   S('2.5', 'Cycle seasons',
     'Press ' + k('E') + ' (or ' + k('Shift', 'Enter') + ') on an active row several times.',
     'Single seasons and pairs in turn; never none.',
     'A row left with no season.',
     src=f'{RUN}: gui.k.shiftenter, w0.roster.cycle PASS.'),
   S('2.6', 'Try to remove the last season',
     'On a species with one season, press that season’s key (' + k('S') + ' ' + k('U') + ' ' + k('A') + ' ' + k('W') + ').',
     'Refused: <b>the last season stays: make the species inactive instead</b>.',
     'The row going to no season.',
     src=f'{RUN}: w0.roster.lastseason PASS; engine line 2253.'),
   S('2.7', 'Cycle the layer',
     'Press ' + k('Alt', 'L') + ' five times.',
     'The title reads Land, Water, Cavern (with how many are found), Deep, then All layers again; the rows follow.',
     'Nothing starts recording a macro (Ctrl+L was DF’s macro key until v6.3).',
     tags=(RC('R5'),), src=f'{RUN}: gui.k.altL, w0.keys PASS; screens C1-altL-*; GUI LAYER_CYCLE line 203.'),
  ])

# ===================================================================================================== 3
phase(3, 'One creature: the species detail',
  'One species’ controls in one place. Since v6.7 an animal person stands where its root animal stands.',
  [
   S('3.1', 'Open the detail',
     'Select an animal and press ' + k('I') + '.',
     'Rows species, habitat, role, body (adult volume in cm³ and its band), embark, allowed, stock, odds, group size, seasons, eats, eaten by, on the map, history. Keys at the foot: H habitat, R role, C call, G group size, O odds, K stock; Enter, S U A W, Q hold, X dismiss.',
     'Two foot labels overlap: <b>Enter: active/inacti</b> runs into <b>s: Sp</b>, and <b>k:</b> (stock) is cut at the right edge. Same on v6.6.',
     src=f'{RUN}: gui.species.detail PASS; screen C2b-detail.'),
   S('3.2', 'An animal person mirrors its root',
     'Open the detail of an animal person on your roster (ADDER_MAN, JAGUAR_MAN, OTTER_MAN, BADGER MAN…).',
     'The role line names the root: <b>predator (as its root animal ADDER)</b>. Habitat, size band, mass, group and eats match the root’s own detail page; the name, class and seasons are its own.',
     'An animal person whose role or size differs from its root.',
     tags=(RC('10.1'),), src=f'{RUN}: mech.animalperson PASS (ALBATROSS_MAN, JAGUAR_MAN, OTTER_MAN: 0 differences in 275 checks); screen C2b-detail; addendum 95.'),
   S('3.3', 'Habitat and role come from the raws',
     'Open an orca or giant orca, an albatross, and a dingo if your world has them.',
     'Orca: aquatic predator (armed: v6.9 clears its BENIGN while ecology runs). Albatross: waterbird, not aquatic. Dingo: land predator, small.',
     'If one reads wrong, ' + k('H') + ' cycles habitat and ' + k('R') + ' role; the row then says <b>you</b>.',
     tags=(RC('R2'),), src=f'{RUN}: mech.model.habitat, mech.model.role, mech.model.band, mech.v69.armed PASS.'),
   S('3.4', 'Set its stock',
     'Press ' + k('K') + ' and enter a number.',
     'The stock line reads <b>N in the region, M come back in season (you set it)</b>. Before you set it, an out-of-season species reads <b>N in the region, M held while out of season</b>.',
     'Stock is how many remain to arrive; it does not make a species likelier.',
     src='engine speciesDetail lines 7255–7257; mech.stock.reserve NOT-TESTABLE-HERE in run 074833 (Alpha Two round 1 3.3 passed on v6.6).'),
   S('3.5', 'Set its odds',
     'Press ' + k('O') + ' and enter a number.',
     'The odds line reads <b>weight W, P% of the land layer</b>, with <b>(if it were in season)</b> when it is out of season, and <b>(you set it)</b>.',
     'A roster build (phase 20) writes odds for every species it picks.',
     src='screen C2b-detail; mech.odds NOT-TESTABLE-HERE in run 074833; round 1 3.4 passed.'),
   S('3.6', 'Set its group size',
     'Press ' + k('G') + ' and enter a number.',
     'The group size line says <b>(you set it)</b>.',
     'DF sometimes sends one more, never two more (X4).',
     src='addendum 94 (X4); mech.groupsize NOT-TESTABLE-HERE in run 074833.'),
   S('3.7', 'Call a wave',
     'For an active land species in season, press ' + k('C') + '.',
     'The next land wave is that species; the ledger records the call.',
     'Round 1 saw a call answered by a group of 12 elephants in one window: likely two draws.',
     src='round 1 3.6 pass; mech.call NOT-TESTABLE-HERE in run 074833.'),
  ])

# ===================================================================================================== 4
phase(4, 'Stock and odds on the Roster',
  'The same two controls for one row or every row the filter shows.',
  [
   S('4.1', 'Stock for one row', 'Select a row and press ' + k('Ctrl', 'W') + '.',
     'A prompt <b>Stock for</b> the species; the STOCK column changes.', 'The label on screen reads “Stock (row” (clipped).',
     src=f'{RUN}: gui.k.ctrlW PASS.'),
   S('4.2', 'Stock for the filter', 'Filter to one category and press ' + k('Ctrl', 'G') + '.',
     'Every row shown takes the number.', 'Rows outside the filter changing.',
     src=f'{RUN}: gui.k.ctrlG PASS.'),
   S('4.3', 'Odds for one row',
     'Press ' + k('Alt', 'O') + ' on an active row that is out of season, enter a number, then on one in season.',
     'Out of season the ODDS cell changes to the new share in brackets, <b>(N%)</b>; in season, without brackets.',
     'A cell that stays <b>-</b> on an active species: that was round 1’s anomaly.',
     tags=(RC('4.3'),), src=f'{RUN}: gui.odds.bracket PASS (cells (1%), (8%), (25%) …); addendum 95; c3b85c7.'),
  ])

# ===================================================================================================== 5
phase(5, 'Whole-roster tools',
  'Each rewrites many species, so each asks first.',
  [
   S('5.1', 'Every tool asks',
     'Press ' + k('M') + ' (Matrix assign), ' + k('O') + ' (Co-align), ' + k('F') + ' (Fill to targets), ' + k('Y') + ' and ' + k('D') + ', answering No each time.',
     'A yes/no question every time; No changes nothing. With no target set, F does not ask and says so: <b>No target set on the land layer: Shift-P/R/V set one; F leaves unset categories alone.</b>',
     'A hint that names Shift-B (retired in v6.4).',
     tags=(RC('5.1'),), src=f'{RUN}: gui.k.M, gui.k.O, gui.k.F, gui.k.Y, gui.k.D PASS; e507876.'),
   S('5.2', 'Matrix assign', 'Press ' + k('M') + ' and answer Yes.',
     'Every active species gets one season by climate; each season of each habitat group keeps a predator with prey it eats. WHY reads <b>matrix</b> or <b>pair</b>. The ledger: <b>matrix: N active species dealt one season each by climate rank within realm, habitat and role</b>.',
     'One season holding more than half the roster.',
     src=f'{RUN}: mech.matrix.balance, mech.pair.guarantee PASS; screen C17h-ledger.'),
   S('5.3', 'Co-align', 'Press ' + k('O') + ' and answer Yes.',
     'Partners within one adjacent season; seasons only added. Ledger: <b>co-align: N partner(s) given one adjacent season (read from a snapshot)</b>.',
     'Most species ending on all four seasons.',
     tags=(RC('R3'),), src=f'{RUN}: mech.coalign.bounded PASS; screen C17h-ledger.'),
   S('5.4', 'Fill natural prey and predators', 'Press ' + k('Y') + ', then ' + k('D') + '.',
     'Each adds only direct partners where a pairing is missing; the ledger says how many.', 'A fill that activates species with no partner.',
     tags=(RC('R3'),), src=f'{RUN}: gui.k.Y, gui.k.D PASS.'),
   S('5.5', 'Category targets',
     'Press ' + k('Shift', 'P') + ', ' + k('Shift', 'R') + ' or ' + k('Shift', 'V') + ' to set a target, then ' + k('Alt', 'F') + ' to fill a category to a number.',
     'The P / R / V line shows the targets; the header says Thin when a category is under target.', '',
     src=f'{RUN}: gui.k.targets, gui.k.thin, gui.k.altF PASS.'),
  ])

# ===================================================================================================== 6
phase(6, 'Apply, send off, rotation',
  'The roster reaches DF at each season boundary or by hand.',
  [
   S('6.1', 'Dry run', 'Press ' + k('Ctrl', 'D') + '.', 'The Dry-run season table opens; nothing changes.', '',
     src=f'{RUN}: gui.k.ctrlD PASS; screen C4-dryrun.'),
   S('6.2', 'Apply now', 'Press ' + k('Ctrl', 'A') + '.', 'The announcement reads <b>&lt;Season&gt; wildlife applied (N active).</b>',
     'If the filter box has focus, Ctrl+A may select its text.', src=f'{RUN}: gui.k.ctrlA PASS; GUI line 1464.'),
   S('6.3', 'Send off and next', 'With wild animals on the surface, press ' + k('Ctrl', 'F') + '.',
     'The groups on the map are told to leave; DF may send the next wave.', 'Its label reads “Send off + ne” (clipped).',
     src=f'{RUN}: gui.k.ctrlF PASS; round 1 6.3 (8 tied units → 0).'),
   S('6.4', 'Rotation off and on', 'Press ' + k('Ctrl', 'E') + ' twice.', 'The header reads rotation off, then ON.', '',
     src=f'{RUN}: gui.k.ctrlE PASS.'),
  ])

# ===================================================================================================== 7
phase(7, 'Reset',
  'Two levels: the roster, or everything.',
  [
   S('7.1', 'Reset the roster', 'Press ' + k('Alt', 'R') + ', choose <b>The roster</b>, answer Yes.',
     'Every species as first found: active natural species, one season each (a predator may keep a second for a pair). Stock and settings kept. Ledger: <b>reset the roster to the embark as first found: N species active, one season each</b>.',
     'Odds a roster build wrote are settings, so they survive this reset.',
     tags=(RC('R5'),), src=f'{RUN}: gui.k.altR PASS; screens C11-reset-choice, C17h-ledger.'),
   S('7.2', 'Reset everything', 'On the copy, press ' + k('Alt', 'R') + ', choose <b>Everything</b>, answer Yes. Then type ' + sw('v7') + ' and read the Ledger’s last line.',
     'Stock back to the worldgen snapshot and every setting to its default, the v7 switches and the realm included. The ledger line talks of stock, not abundances.',
     'That the v7 switches return to their defaults is read from the code (resetToDefault copies defaultConfig whole); no test has looked.',
     tags=(RC('17.1'),), src='round 1 17.1 and f80d072; engine resetToDefault line 3214 (untested for cfg.v7).'),
  ])

# ===================================================================================================== 8
phase(8, 'Add an invasive species',
  'A species not native to the embark can be brought in live. v6.7 puts it on the roster at once.',
  [
   S('8.1', 'Add invasive',
     'Press ' + k('V') + ' until View reads Add invasive, select a species, press ' + k('Ctrl', 'X') + '.',
     'The status line reads <b>TOKEN added to N region(s) (a-b), live: active, Sp. Enter makes it inactive.</b> (or <b>inactive</b>). The species is on the Roster at once, active with exactly one season or inactive; the ledger records the add.',
     'An added species with no state until you reopen the window: that was round 1’s anomaly.',
     tags=(RC('8.1'),), src=f'{RUN}: gui.addnew.whole, gui.k.ctrlX PASS; GUI act_addnew; addendum 95.'),
   S('8.2', 'A savage species on a calm map',
     'If your map is calm (no savage region), add a SAVAGE species that matches its biome (on temperate shrubland, CENOZOIC_SMILODON) and play a season.',
     'Today: the add succeeds and DF never draws the species. On CTRL, with the entry added, 0 smilodons in a full season, both replicates.',
     'Mark it Pass if the page’s description holds; the gap is a design question.',
     src='ECO INV2 (findings.md).',
     dec='<b>savage</b>: if the tool is to place SAVAGE species itself, the species should appear as a placed group; if it is to refuse them, the add should be refused with a reason. Until decided, nothing arrives.'),
  ])

# ===================================================================================================== 9
phase(9, 'Seasons tab',
  'Every active species under its level across the four seasons, editable.',
  [
   S('9.1', 'Read it', 'Click <b>Seasons</b>.',
     'Columns Spring to Winter; <b>+</b> arrives that season, <b>-</b> leaves after it, <b>X</b> stays, <b>.</b> not present.',
     'Names over 20 letters run into the Spring column with no gap (BIRD_SWALLOW_CAVE_GI.).',
     src=f'{RUN}: gui.tab.seasons PASS; screens C18-seasons, C18e-help.'),
   S('9.2', 'Edit from the grid', 'Select a row and press ' + k('S') + ', ' + k('U') + ', ' + k('A') + ' or ' + k('W') + '.',
     'That season flips; the header names the species with its seasons.', 'Removing the last season should be refused here too.',
     src=f'{RUN}: gui.seasons.edit PASS; screen C18d-seasons-S.'),
  ])

# ===================================================================================================== 10
phase(10, 'Food web',
  'Who eats whom, from role, habitat and size; animal people now as their root animal.',
  [
   S('10.1', 'The pyramid', 'Click <b>Food web</b> and press ' + k('N') + ' to pick a season.',
     'A trophic pyramid of unlabelled tiers with <b>^</b> between them, apex at the top, vermin at the base; an aquatic chain below it, each line a predator <b>----&gt;</b> what it eats.',
     'A tier missing on a fort that has its animals.',
     tags=(RC('10.1'),), src=f'{RUN}: gui.tab.foodweb, gui.k.webN PASS; screen C16-foodweb; round 1 10.1 (page corrected).'),
   S('10.2', 'Animal people as prey and predator',
     'Find an animal person in the pyramid or chain, and its root animal.',
     'Each sits where its root sits: what eats JAGUAR eats JAGUAR_MAN; what the root eats, the person eats. A giant otter still eats a jaguar man, because it eats the jaguar (left as is by the user).',
     'An animal person placed differently from its root.',
     tags=(RC('10.1'),), src=f'{RUN}: mech.animalperson PASS; addendum 95 (“Left as is”).'),
   S('10.3', 'Diet follows habitat', 'Look for a land predator eating a sea creature, or a bird eating a large fish.',
     'None. A lion takes no shark, an eagle no tuna, a great white no deer; an osprey takes small sea fish.', '',
     tags=(RC('R3'),), src=f'{RUN}: mech.diet.habitat, mech.v69.reach PASS.'),
   S('10.4', 'The four modes', 'Press ' + k('G') + ' to step Pyramid, Graph, By season; ' + k('L') + ' for Layers side by side.',
     'Graph shows arrows and live pairs; By season four columns; By layer the layers side by side.', '',
     src=f'{RUN}: gui.k.webG, gui.k.webL PASS; screens C16b–C16d.'),
  ])

# ===================================================================================================== 11
phase(11, 'Live',
  'What is on the map, where it came from, and the ecology line, which in v7.0 carries the relation sweep.',
  [
   S('11.1', 'Origins', 'Click <b>Live</b>.',
     'A <b>Wild on map</b> line, then each animal by origin: DF wave, tool-drawn, resident, born here, untracked, deep.',
     'An animal counted twice or in no origin. Sponges are never listed: they are scenery.',
     src=f'{RUN}: gui.tab.live, mech.v70.sponges PASS; screen C17-live; mech.origin NOT-TESTABLE-HERE.'),
   S('11.2', 'The ecology line and the sweep',
     'Read the line that starts <code>ecology:</code>.',
     '<b>ecology: on  last write day D: P predator(s) x T target(s), N pair(s) written …; livestock safe; nudge on; sweep: last N cleared (N refought) of N managed, N ms; total N cleared, N refought</b>. The sweep clears DF’s own predator-prey cells between two managed wild animals that the roster’s web does not pair.',
     'A sweep that never clears anything is normal on a quiet surface (RELS2b: wild-wild surface relations almost never arise); caverns give it work. <b>nudged</b> counts teleports, which rest on r2’s changed teleport.',
     tags=(NEW('v7.0'), R2), src=f'{RUN}: mech.v70.sweep PASS (0 cleared on CTRL), gui.tab.live; screen C17-live; ECO RELS2b, HC4.',
     dec='<b>cadence</b>: at 3,000 ticks the “last write day” moves half as often. <b>nudge</b>: if off, the line reads “nudge off” and nudged stays 0.'),
   S('11.3', 'The limits line',
     'Read the line that starts <code>limits:</code>.',
     '<b>limits: land auto (N) group(s) at once, ceiling none; water auto (N) group(s) at once per water body, ceiling 12; cavern auto (N) group(s) at once per cavern, ceiling none</b>, with N = floor(√embark tiles) + 1: 5 on a 4x4, 7 on a 6x6.',
     'A number instead of auto means someone set it (18.1).',
     tags=(NEW('v7.0'),), src=f'{RUN}: mech.v70.groups_auto_all, groups_water_body, groups_cavern_depth, mech.v69.autogroups PASS; screen C17-live.',
     dec='<b>water 2</b>: if adopted, water reads “2 group(s) at once per water body”. <b>cavern cap</b>: if adopted, the cavern part is relabelled as a soft target; the number stays.'),
   S('11.4', 'Groups and their leaders',
     'Scroll to <b>Groups:</b>.',
     'The line <b>Groups: ON   N at once   gap 5-20 days   released N   departed N</b>, then one row per group: species, size, how it came, its day, and <b>led by #id</b> for a herd, pack, flock or school.',
     'v7.0 picks the largest adult male as leader. You can spot-check: ' + k('F') + ' (11.6) follows a member; DF’s unit sheet shows sex and size.',
     tags=(NEW('v7.0'),), src=f'{RUN}: mech.v70.leader_male PASS; mech.leader.lowest (v7.0-aware) PASS; ECO COH.'),
   S('11.5', 'Hold and send off',
     'Select a group; press ' + k('Q') + ' (hold 30 days), then ' + k('X') + ' (send off).',
     'The row reads <b>held N more days</b>, then <b>dismissed</b>; the ledger has both.', '',
     src=f'{RUN}: gui.k.liveQ, gui.k.liveX PASS; screens C17c, C17d.'),
   S('11.6', 'Follow and centre', 'Press ' + k('F') + ' on a group, then <kbd>Enter</kbd>.',
     'The camera follows a member; Enter centres the map on the group.', '',
     src=f'{RUN}: gui.k.liveF, gui.k.liveEnter PASS.'),
   S('11.7', 'Send off and next from Live',
     'With a gated land group on the map, press ' + k('W') + ' on the Live tab.',
     'Every gated land group is sent off and the gate opens, as the Roster’s Ctrl+F does.',
     'Alpha Two never stepped this key. The validator could not test it on CTRL (no gated group at the time).',
     src=f'{RUN}: gui.k.liveW NOT-TESTABLE-HERE; v6.live.hotkeys PASS; GUI line 456.'),
   S('11.8', 'Herds and packs', 'Read the Herds &amp; packs block.',
     'Each tracked species is herd, pack, flock or school, with the reason from its raws.', '',
     src=f'{RUN}: v6.herds PASS; screen C17-live.'),
  ])

# ===================================================================================================== 12
phase(12, 'Layers',
  'One column per layer with the same words on each. This tab has not caught up with v6.9’s auto and v7.0’s per-body and per-cavern counts.',
  [
   S('12.1', 'Read the table', 'Click <b>Layers</b>.',
     'Columns LAND, WATER, CAVERN, DEEP; rows layer, drawn by, groups at once, ceiling, gap, pattern, coupling, cohesion, ecology switch, nudge after, pack size, irruptions, cavern pressure.',
     'The groups-at-once row shows the stored number, not auto: on CTRL it read 3, 2, 2 while the Live tab said auto (5) per cavern. Compare with 11.3 and mark a mismatch.',
     src=f'{RUN}: gui.tab.layers PASS; screen C17e-layers vs C17-live; GUI refreshLayers line 1217.',
     dec='<b>cavern cap</b>: the decision is to relabel this cavern cell as a soft target. <b>nudge</b>: the nudge row reads its distances either way.'),
   S('12.2', 'Change a limit',
     'Press ' + k('L') + ' to pick the land column, then ' + k('C') + ' and enter 3. Then read the Live tab’s limits line.',
     'The cell reads 3, the ledger records <b>land groups at once 3</b>, and Live’s limits line reads <b>land 3 group(s) at once</b>.',
     'Read from the code: this key stores the number but does not turn auto off, so Live most likely still reads auto (N), and the engine keeps using auto. If so, mark an anomaly; ' + sw('limits land groups 3') + ' does turn it off (18.1).',
     src='GUI act_lay_concurrent line 1283 (QUOTA.set, auto untouched); engine QUOTA.groupsFor; round 1 12.2 passed on v6.6 (no auto then). Untested on v7.0.'),
   S('12.3', 'The water line', 'Read the line under the table that starts <code>water:</code>.',
     '<b>water: draws on  N of M per body group(s) at once, N of 12 animals; water ocean … river … (salt N / fresh N); next draw in D days</b>.',
     'A fort with water that reads dormant. The table’s water cell says 2 while this line says per body.',
     tags=(NEW('v7.0'),), src=f'{RUN}: screen C17e-layers; mech.water.live PASS.'),
   S('12.4', 'Caverns', 'Read the Caverns block.',
     'Each cavern <b>not yet found</b> until your dwarves reach it, then its species and groups.', '',
     src=f'{RUN}: v6.caverns PASS; screen C17e-layers.'),
  ])

# ===================================================================================================== 13
phase(13, 'Vermin, and vermin hunting',
  'Vermin by family. In v7.0 the Vermin tab lists no locked species.',
  [
   S('13.1', 'Families', 'Click <b>Vermin</b>.',
     'One row per family present (fish, flies, fliers, mammals, soil, colony, crawlers) with n, active, season, stock and layers.',
     'A good or evil species your map does not match listed here (v7.0 dropped them).',
     src=f'{RUN}: gui.tab.vermin, mech.v70.vermin_nolocked PASS; screen C18b-vermin.'),
   S('13.2', 'Open a family', 'Select a family and press ' + k('E') + '.',
     'Its species appear under it, each with active, seasons, stock and layer.', '',
     src=f'{RUN}: gui.vermin.species PASS; screen C18c-vermin-open.'),
   S('13.3', 'Edit one vermin species', 'On a species row press <kbd>Enter</kbd>, a season key, or ' + k('Shift', 'W') + ' (stock).',
     'That species alone changes.', '', src='round 1 13.3 pass.'),
   S('13.4', 'Vermin hunting on', 'On the Panel, turn on <b>Vermin hunting</b>.',
     'Predatory and water birds get DIVE_HUNTS_VERMIN, small land predators HUNTS_VERMIN, while the switch is on.',
     'X5 saw no effect of these flags on wild animals. The v7.0 gobble (21.7) is the mechanism that worked.',
     src=f'{RUN}: mech.hunt PASS; addendum 94 (X5).'),
  ])

# ===================================================================================================== 14
phase(14, 'Ledger, undo, help', 'Every write the tool makes is in the ledger; edits can be undone.',
  [
   S('14.1', 'Filter the ledger', 'Click <b>Ledger</b>; press ' + k('K') + ' (kind) and ' + k('L') + ' (layer).',
     'The list narrows; the count line reads <b>N of M recorded</b> with the filter.', '',
     src=f'{RUN}: gui.k.ledgerK PASS; screen C17h-ledger.'),
   S('14.2', 'Undo', 'Make three roster edits, then press ' + k('Z') + ' three times.',
     'Each undone in reverse order; the label shows how many remain, <b>Undo last edit (N)</b>; fifty deep.', '',
     tags=(RC('9.2'),), src=f'{RUN}: gui.k.ledgerZ PASS; screen C17h-ledger-undo.'),
   S('14.3', 'Help on every tab', 'On each tab press ' + k('Alt', 'H') + '.',
     'A help page for the tab, then the vocabulary: active, seasons, stock, odds, group size, groups at once, ceiling, gap, cohesion, coupling, ecology, nudge, hold, send off, call, seasonal rotation, Add invasive, agitated, special creatures.',
     'A word in the window the help does not explain. None of the v6.9 or v7.0 words (exhaustion, scavenging, sweep, builder) is in the help.',
     src=f'{RUN}: gui.help PASS; screen C18e-help; GUI HELP table.'),
  ])

# ===================================================================================================== 15
phase(15, 'The map overlay', 'Group markers and predator-prey links on the map.',
  [
   S('15.1', 'Turn it on',
     'Open ' + c('gui/control-panel') + ' (or the Panel’s Map overlay row) and enable <code>seasonal-wildlife.groups</code>.',
     'Markers on tracked groups on the level you view, and lines between related predators and prey.',
     'All off does not turn the overlay off (1.4); turn it off yourself at the end.',
     tags=(RC('R5'),), src=f'{RUN}: mech.overlay, mech.overlay.links, w0.overlay PASS; screen C0c-panel-alloff.'),
  ])

# ===================================================================================================== 16
phase(16, 'Console, part one: the roster from the console',
  'Phase two of the alpha, promised since alpha one: the console verbs. v6.8 added the Roster’s two edits as verbs, for the browser companion. Type each line in the DFHack console with the window closed, then reopen the window to see the effect.',
  [
   S('16.1', 'Status and apply',
     'Type ' + sw('status') + ', then ' + sw('now') + '.',
     '<code>status</code>: Biomes, Layers, the limits line, patterns, ledger, caverns, cavern map, water, vermin hunting, <b>vermin gobble</b>, fuse, <b>On the map now</b>, the invasion field, then the embark subset. <code>now</code>: <b>active: N  [N ms]</b>.',
     'Before the rotation runs this session, the gobble line reads <b>vermin gobble: on, not yet applied this session (`v7 apply` or enable the rotation)</b>.',
     tags=(NEW('v7.0'),), src=f'{RUN}: cli.status, cli.now PASS (output quoted in results.json).'),
   S('16.2', 'Roster counts',
     'Type ' + sw('roster') + '.',
     'One line per layer: <b>roster land     24 active (0 in season now),   0 inactive</b>.', '',
     tags=(NEW('v6.8'),), src=f'{RUN}: cli.roster PASS.'),
   S('16.3', 'Inactive and active from the console',
     'Pick an active species with a one-word key (BADGER, or cavern:CRUNDLE) and type ' + sw('roster BADGER inactive') + ', then ' + sw('roster BADGER active') + '.',
     '<b>BADGER inactive, seasons -  [guild: ground mesocarnivore]</b>, then <b>BADGER active, seasons Au  [guild: …]</b>: one season. Each is one ledger line and one undo step; the Roster shows it when reopened.',
     'Raw ids with a space or comma (HONEY BADGER, RIVER OTTER, “BADGER, GIANT”) cannot be named: the console splits them. Quoting is untested.',
     tags=(NEW('v6.8'),), src='validate-full 20260930-125813 (v6.9): cli.roster.state PASS; NOT-TESTABLE-HERE on run 074833 (no fit species on CTRL); open-items bug spaced-raw-ids-cli.'),
   S('16.4', 'Set seasons',
     'Type ' + sw('seasons BADGER SpAu') + ', then ' + sw('seasons BADGER none') + ', then ' + sw('seasons BADGER Xy') + '.',
     '<b>BADGER active, seasons SpAu</b>. <code>none</code> is refused: <b>seasons: an active species keeps at least one season; to keep BADGER away: seasonal-wildlife roster BADGER inactive</b>. A bad code prints <b>usage: seasonal-wildlife seasons BADGER &lt;SpSuAuWi|all&gt;   e.g. SpAu, Wi, all</b>.',
     'On v6.9 a species whose raws forbid a season printed “note: … has NO_SPRING in its raws”. With v7.0’s seasons_own on, no note: the tool clears NO_&lt;season&gt; (19.4).',
     tags=(NEW('v6.8'),), src='20260930-125813: cli.seasons.set PASS; engine dispatcher (seasons branch).'),
   S('16.5', 'Seasons on an inactive species',
     'Make a species inactive (16.3), then type ' + sw('seasons KEY Wi') + '.',
     'It becomes active, in Winter only.',
     'No validator run has tested this: mark what you see.',
     tags=(NEW('v6.8'),), src='cli.seasons.activate NOT-TESTABLE-HERE in every run (125813, 124923, 074833). Untested.'),
   S('16.6', 'Undo from the console',
     'After 16.4, type ' + sw('undo') + '.',
     '<b>undid: seasons  (N more to undo)</b>; the species is back as before. With nothing left: <b>undo: nothing to undo</b>.', '',
     src='20260930-125813: cli.roster.undo PASS; ' + RUN + ': cli.undo PASS.'),
   S('16.7', 'Stock, odds, size and call',
     'Type ' + sw('stock BADGER 40') + ', ' + sw('odds BADGER 20') + ', ' + sw('size BADGER 2') + ', ' + sw('call BADGER') + ', then ' + sw('stock BADGER clear') + '.',
     'Each prints its line from the species detail (<b>stock …</b>, <b>odds …</b>, <b>group size …</b>) and writes one ledger line. <code>call</code> prints <b>called BADGER: …</b> or <b>cannot call BADGER: …</b> with the reason. <code>clear</code> hands it back to the raws.',
     'An unknown key prints the usage with the key forms: TOKEN, water:TOKEN, cavern:TOKEN, deep:TOKEN.',
     src='engine dispatcher (stock/odds/size/call); mech.stock.reserve, mech.odds, mech.groupsize, mech.call NOT-TESTABLE-HERE in run 074833.'),
   S('16.8', 'The other settings verbs',
     'Try ' + sw('pattern land burst') + ' and ' + sw('pattern land steady') + '; ' + sw('ledger 10 edit') + '; ' + sw('layer water on') + '; ' + sw('water') + '; ' + sw('caverns') + '; ' + sw('hunting') + '; ' + sw('irruption') + '; ' + sw('sendoff land') + '.',
     '<b>patterns: land=burst  water=steady  cavern=steady</b>; ten ledger lines then <b>ledger: 10 of N recorded shown  kind=edit</b>; <b>layers: land=on water=on …</b>; the water status and its groups line; one line per cavern band; <b>vermin hunting: off</b>; the irruption status (off); <b>sent off N gated land group(s); the gate is open</b>.',
     'Retired words still answer: <code>water target</code> and <code>cavern</code> print that they were retired in v6.5. The verb list printed for an unknown verb is stale (it offers quota and water target).',
     src=f'{RUN}: cli.pattern, cli.ledger, cli.water, cli.caverns, cli.irruption, cli.usage PASS; mech.sendoff NOT-TESTABLE-HERE; engine dispatcher.'),
  ],
  pre='<h3 class="sub" style="margin-top:0">Every console verb, from the engine’s dispatcher</h3><p class="muted" style="margin-top:6px;max-width:72ch">The script’s own help (<code>help seasonal-wildlife</code>) omits <code>limits</code>, <code>stock</code>, <code>odds</code>, <code>size</code>, <code>call</code>, <code>sendoff</code>, <code>undo</code>, <code>preset</code>, <code>irruption</code>, <code>hunting</code>, <code>sponges</code>, <code>roster KEY</code> and <code>seasons</code>, and still lists retired forms. This table is read from the code instead.</p>' + VERBS)

# ===================================================================================================== 17
phase(17, 'The browser companion',
  'v6.8’s web page: the tool’s state in a browser on the same machine, refreshed every two seconds; every change is sent as one console verb.',
  [
   S('17.1', 'Start it',
     'Type ' + c('seasonal-wildlife-web start') + '.',
     '<b>start: serving the companion at http://127.0.0.1:8642/?t=&lt;token&gt;  (copied to the clipboard)  [tiles: N creatures, N sheets, read in N ms]</b>.',
     'It needs DFHack’s luasocket. Only 127.0.0.1 is served. Under CrossOver, open the address in a browser on the Mac.',
     tags=(NEW('v6.8'), R2), src=f'{RUN}: web.serve PASS on r1.1 (page 200, 75,201 bytes; state 200).'),
   S('17.2', 'Read the page',
     'Open the address.',
     'The fort’s name and date, a layer selector, Steam or ASCII tiles, and four tabs: Status, Species, Food web, Ledger &amp; settings. It updates every two seconds.',
     'A blank page or a stale date.',
     tags=(NEW('v6.8'),), src=f'{RUN}: web.snapshot (24 species, 87 pairs, built in 26 ms), web.gfx PASS; seasonal-wildlife-web.html TABS.'),
   S('17.3', 'Change something from the page',
     'On Species, switch one species’ <b>Active</b> off. Then reopen the window’s Roster and the Ledger.',
     'The page says the species is inactive; the window shows it inactive with WHY <b>you</b>; the ledger has the edit. Switch it back on.',
     'The page’s Hold is 3 days; the window’s Q holds 30.',
     tags=(NEW('v6.8'),), src=f'{RUN}: web.cmd PASS (POST /cmd ran “seasonal-wildlife roster”).'),
   S('17.4', 'The token guard',
     'Open the same address with the <code>?t=…</code> part removed.',
     'The page or its data is refused.', '',
     tags=(NEW('v6.8'),), src=f'{RUN}: web.guard PASS.'),
   S('17.5', 'Its cost, then stop it',
     'Type ' + c('seasonal-wildlife-web status') + ', then ' + c('seasonal-wildlife-web stop') + '.',
     '<b>serving http://… requests N (commands N, refused N, errors N); poll last N ms, worst N ms; snapshot last N ms, worst N ms</b>; then the port closes and the page stops updating.',
     'A worst poll or snapshot near a frame (20 ms at 50 fps) would show as stutter.',
     tags=(NEW('v6.8'),), src=f'{RUN}: web.stop PASS; seasonal-wildlife-web.lua status().'),
  ])

# ===================================================================================================== 18
phase(18, 'Console, part two: the v6.9 jobs',
  'v6.9 turned five ECO findings into features. Two have Panel rows; all five have verbs.',
  [
   S('18.1', 'Groups at once: auto and a number',
     'Type ' + sw('limits') + '; ' + sw('limits land groups 3') + '; ' + sw('limits land groups auto') + '.',
     'The limits line (11.3) and <b>on the map now: land N  water N  cavern N  deep N</b>; then <b>land 3 group(s) at once</b>; then <b>land auto (N)</b> again.',
     'Water cannot go back to auto: ' + sw('limits water groups auto') + ' prints the usage. Once water is set to a number, only Reset everything restores auto (read from the code).',
     tags=(NEW('v6.9'),), src=f'{RUN}: mech.v69.autogroups PASS; ECO2-G, SW3B (1 < 3 ≤ auto); engine limits branch.',
     dec='<b>water 2</b>: if adopted, water reads 2 per body by default and this gap matters less.'),
   S('18.2', 'Exhaustion and replacement',
     'Type ' + sw('exhaust') + '. Then pick an active species in season, type ' + sw('stock KEY 0') + ' and ' + sw('exhaust now') + '.',
     '<b>exhaustion watch: on; exhausted this season: none; replacements: none</b>; then <b>exhaust: 1 replacement(s) made</b> and a ledger line <b>KEY exhausted (stock 0): OTHER takes its niche for the rest of &lt;Season&gt;</b>. In N1 the replacement’s waves began about 2,000 ticks later.',
     'Look at what replaces what. On CTRL the validator’s run logged BIRD_OSPREY → DINGO and FISH_LAMPREY_SEA → RIVER OTTER: a niche crossing habitat.',
     tags=(NEW('v6.9'),), src='validate-full 20260930-124844: mech.v69.exhaust PASS; NOT-TESTABLE-HERE in run 074833; screen C17h-ledger (074833); ECO N1.'),
   S('18.3', 'Quiet wildlife fights',
     'Type ' + sw('alerts') + '. Watch a fight between two wild animals, and one involving a dwarf or an animal person.',
     '<b>quiet wildlife fights: on (combat alerts with no humanoid in them are dropped)</b>. The wild-only fight raises no combat alert; the other still does. The fight stays in each animal’s own log.',
     'A dwarf fight that raises no alert. r2 changed isCitizen to exclude the dead; the filter’s humanoid test reads it.',
     tags=(NEW('v6.9'), R2), src=f'{RUN}: cli.alerts PASS; ECO A1, A2 (wolves x deer: 3 dropped, 0 left; wolf men kept).'),
   S('18.4', 'Curious beasts as residents',
     'If a curious beast lives near you (raccoon, grizzly), type ' + sw('curious RACCOON resident') + '; then ' + sw('curious DEER resident') + '.',
     '<b>curious beasts kept as residents (flags cleared while the tool runs): RACCOON</b>; the raccoons wander and stay instead of stealing and leaving. DEER is refused: <b>curious: DEER is not a curious beast (no CURIOUSBEAST_EATER/ITEM/GUZZLER)</b>. ' + sw('curious RACCOON thief') + ' puts DF’s way back.',
     '', tags=(NEW('v6.9'),), src=f'{RUN}: cli.curious PASS (flags 4 → 0 → 4); ECO CB (4 of 4 stayed with the flags off).'),
   S('18.5', 'Scavenging',
     'With remains of a wild kill on the map, type ' + sw('scavenge on') + ', then ' + sw('scavenge now') + ', then ' + sw('scavenge') + '.',
     '<b>scavenge: N eaten</b>; status <b>scavenging: on  map-wide, off stockpiles and buildings  last pass: N scavenger(s), N remains, N walking, N eaten  fallbacks: 0</b>. On CTRL and RIVER4 the pass cleared every carcass on land and in water within about 2,400 ticks.',
     'Two known lies in the status line: “last pass” repeats the last non-empty pass, and “on” shows even when the rotation is off, when nothing runs. The walk uses setPathGoal, which r2 fixed.',
     tags=(NEW('v6.9'), R2), src=f'{RUN}: cli.scavenge PASS; ECO SCV, SCV2b/SCV2Wb; open-items bug scav-status-diagnostics.',
     dec='<b>swimmers</b>: if carnivorous swimmers count as scavengers, alligators, crocodiles and sharks join the pass; today only pond grabbers and sea serpents do among swimmers.'),
  ])

# ===================================================================================================== 19
phase(19, 'Console, part three: the v7 switches',
  'Every v7.0 item is a switch in <code>cfg.v7</code>, set only from the console. Raw writes happen while the rotation is on and are put back on off, All off and unload.',
  [
   S('19.1', 'The embark’s alignment',
     'Type ' + sw('v7') + ' and read its last line.',
     '<b>embark alignment: good</b>, <b>evil</b> or <b>neutral (N region tiles read)</b>. On a good map, good natural species (fluffy wamblers, pixies) are on the Roster and evil ones locked; an evil map the mirror. Cavern good or evil species (trolls, gorlaks, blind cave ogres) are ordinary cavern life everywhere.',
     'A good or evil species on the Roster of a map whose alignment does not match.',
     tags=(NEW('v7.0'),), src=f'{RUN}: mech.v70.align, mech.v70.cave_aligned, mech.v70.fanciful PASS; ECO item 6 (GOODF, EVILF).'),
   S('19.2', 'Change one switch',
     'With the rotation on, type ' + sw('v7 domestic on') + ', then ' + sw('v7 domestic maybe') + ', then ' + sw('v7 domestic off') + '.',
     'The switch flips and the tool rewrites its raws: <b>v7 raws: NO_&lt;season&gt; cleared N; solitary package on N species (natural skills N of N, gaits N, units N); fishers N; gobble N class(es) tagged, N consumer write(s), N fallback write(s)</b>, then the list. A bad value prints <b>usage: seasonal-wildlife v7 domestic on|off</b>. Numbers take 0 to 10 (' + sw('v7 outgun 3') + ').',
     'With the rotation off it prints <b>v7: rotation is off, so no raw is written</b>.',
     tags=(NEW('v7.0'),), src=f'{RUN}: cli.v70.v7, mech.v70.restore_all PASS (CTRL: cleared 8; package on 2 species, skills 28 of 28, gaits 54; gobble 4, 6, 6).',
     dec='<b>sneak</b>: if adopted, ' + sw('v7 pack_sneak 0') + ' becomes the default.'),
   S('19.3', 'Apply and count the raws',
     'Type ' + sw('v7 apply') + ', then ' + sw('status') + '.',
     'The same <b>v7 raws: …</b> line; the ledger records it. <code>status</code> now reads <b>vermin gobble: on  N species class-tagged  consumers by class (written/members): …</b>.',
     'All off (1.4) should report the same raw writes restored.',
     tags=(NEW('v7.0'),), src=f'{RUN}: mech.v70.restore_all PASS; engine VERMIN.gobbleStatus.'),
   S('19.4', 'The tool owns seasons',
     'Read the <b>NO_&lt;season&gt; cleared N</b> count in 19.3. Then type ' + sw('v7 seasons_own off') + ' and repeat 16.4 on a species whose raws forbid a season; then ' + sw('v7 seasons_own on') + '.',
     'With seasons_own on, NO_&lt;season&gt; is cleared on every managed species and the roster’s seasons stand. Off, the raw flags return and <code>seasons</code> prints its NO_ note again.',
     'Whether DF then brings a species in a season its raws forbid has not been measured since the change.',
     tags=(NEW('v7.0'),), src=f'{RUN}: mech.v70.seasons_own PASS (BADGER flags 2 → 0 → 2); ECO T2 (DF honours NO_ at the pick).'),
   S('19.5', 'The solitary package',
     'Read <b>solitary package on N species</b> in 19.3.',
     'Each armed hunter that travels alone (raw group 1) gets natural skill 10 in sneak, melee, bite, grasp, wrestling, dodging and awareness, silent gaits and AMBUSHPREDATOR. You cannot see the skills in the window.',
     'LONE10 measured it: a cougar with the package killed 29 placed prey in 10 runs against 14 without (p = 0.07).',
     tags=(NEW('v7.0'),), src=f'{RUN}: mech.v70.solo_raws PASS; ECO LONE10.'),
   S('19.6', 'Switch everything off',
     'Press All off on the Panel (1.4), then All on.',
     'All off reports the v7 raw writes restored; All on writes them again.', '',
     tags=(NEW('v7.0'),), src=f'{RUN}: mech.panel.alloff PASS; screen C0c-panel-alloff (743 v7 raw writes).'),
  ])

# ===================================================================================================== 20
phase(20, 'Console, part four: the roster builder',
  'v7.0’s builder fills a fixed table of guild slots per layer from the embark’s own candidates and writes a FREQUENCY ladder as odds. It replaces the whole roster of a layer. Use the copy.',
  [
   S('20.1', 'The builder switch',
     'Type ' + sw('v7 builder off') + ', ' + sw('roster build') + ', then ' + sw('v7 builder on') + '.',
     '<b>roster build: the \'builder\' switch is off (v7 builder=false)</b>; on again, the matrix and manual roster are untouched.', '',
     tags=(NEW('v7.0'),), src='engine dispatcher (roster build); no validator claim.'),
   S('20.2', 'Build the land roster',
     'Type ' + sw('roster build land') + '. Read the receipt; open the Roster; then type ' + sw('undo') + '.',
     '<b>roster build land -- seed TOKEN</b>; one line per slot, <b>AL  1 (min 1, max 1)  COUGAR</b>, then RP, GZ, PL, ML, LB, WB, SH; any <b>UNFILLED</b> slot with its reason; <b>OUTGUNNED</b> pairs; <b>ladder:</b> one weight per pick, the largest 100; <b>vegetation index N (region N, grass N% of N surface tiles, N shrub, N tree)</b>; and <b>N previously-active land species deactivated</b> if it dropped any. The Roster shows the picks active and the rest inactive, ODDS from the ladder. <code>undo</code> prints <b>undid: roster build land</b>.',
     'On CTRL the builder barely changed what arrived: its surface supply is ravens whatever the roster says (S8Cb vs S8C). The ladder is the v2.1 table, predicted ~31 % predators on land; the 14–18 % target is v2.2’s, not ported.',
     tags=(NEW('v7.0'),), src='ECO S8Cb receipts (data/experiments/S8C/20261001-062036/log.txt); S8C, S8B, S8O; findings “Corrections” (ladder v2.1). No validator claim.',
     dec='<b>x3</b>: removing the pack-hunter bonus makes pack hunters less likely in RP/ML picks. <b>apex</b>: dropping the apex step changes the AL line’s ladder weight; apexes would then be steered by placement and stock.'),
   S('20.3', 'Build again',
     'Type ' + sw('roster build land') + ' a second time and compare.',
     'The picks can differ: the builder picks uniformly within a slot. On CTRL two builds gave GROUNDHOG, KANGAROO / PORCUPINE, BIRD_KAKAPO and KANGAROO, GROUNDHOG / BIRD_EMU, PORCUPINE.',
     'Undo both builds before going on.',
     tags=(NEW('v7.0'),), src='ECO S8Cb rep 1 vs rep 2 receipts; roster-builder-decisions (uniform selection).',
     dec='<b>x3</b>: see 20.2.'),
   S('20.4', 'Build the cavern and water rosters',
     'With a cavern open, type ' + sw('roster build cavern') + '; on a water fort, ' + sw('roster build water') + '. Undo each.',
     'Cavern slots AL, AW, PL, ML, RP, LB, SH, MW, FF. Water prints <b>deep water: N/T ocean column(s) at or past 3 levels</b>; with none, the pelagic slot stays empty (OCEAN2: 0/5374). Slots with no candidate read UNFILLED (BOATS: AW, FC, FF).',
     'With no cavern open the cavern pool is empty and the build has nothing to pick.',
     tags=(NEW('v7.0'),), src='ECO S8Cb, S8B, S8O; findings “Corrections” (PE slot min 0, max 1).',
     dec='<b>AP cap</b>: with the builder, plump helmet men filled the cavern SH slot and came about 15 a wave; a cap would shrink their groups. <b>lake apex</b>: on a temperate lake the water apex slot is unfilled about half the time.'),
   S('20.5', 'Outgunned pairs',
     'Type ' + sw('roster outgun land') + ' (and cavern). Then ' + sw('v7 outgun_cap on') + ', build again, read the OUTGUNNED lines, undo, and ' + sw('v7 outgun_cap off') + '.',
     '<b>roster outgun land -- N pair(s) (factor &gt;= 2.0)</b> with lines <b>outgunned: WOLF pack vs CAPYBARA herd 3.1x</b>, or <b>-- none found</b>. Nothing is written. With outgun_cap on, a build’s OUTGUNNED lines end <b>-- capped to N</b> and the prey’s group size is set.',
     'CTRL’s cavern build found REACHER vs CREEPING_EYE 4.3x and REACHER vs FLESH_BALL 3.0x.',
     tags=(NEW('v7.0'),), src='ECO S8Cb rep 2 receipt; CAL and P1 (capybaras killed 5 of 5 wolves). No validator claim; the cap’s effect on fights is unmeasured.'),
   S('20.6', 'Realms',
     'Type ' + sw('realm') + '; ' + sw('realm XYZ') + '; ' + sw('realm auto') + '; ' + sw('realm') + '; then ' + sw('v7 realms on') + ', build land, undo, ' + sw('v7 realms off') + ' and ' + sw('realm off') + '.',
     '<b>realm: unset (`seasonal-wildlife realm &lt;name|auto|off&gt;`)</b> and <b>(the \'realms\' switch is off -- `seasonal-wildlife v7 realms on`)</b>. XYZ prints the usage with the eleven codes NEA, PAL, IND, AFR, NEO, AUS, ARC, NZ, MAD, ANT, OCE. <code>realm auto</code> then <code>realm</code>: <b>realm: auto -&gt; NEA</b> (or another). With realms on, the build’s first line ends <b>, realm NEA</b> and species of other realms are not seated together.',
     'Realms have never run on the rig.',
     tags=(NEW('v7.0'),), src='engine dispatcher (realm), V7.REALM_ORDER line 1640; bl.realm BACKLOG in run 074833. Untested.'),
  ])

# ===================================================================================================== 21
phase(21, 'v7.0 in play',
  'The rest of v7.0 acts on animals, not on a screen. Each step names what you can see and where; 24 lists what you cannot.',
  [
   S('21.1', 'Run the ecology pass by hand',
     'Type ' + sw('groups ecology now') + '.',
     'The ecology line of 11.2, with the sweep’s numbers, written at once.', '',
     tags=(NEW('v7.0'),), src=f'{RUN}: cli.groups.ecology, mech.v70.sweep PASS.'),
   S('21.2', 'Domestic prey (on the copy)',
     'With a land apex or a cavern predator on the map, type ' + sw('v7 domestic on') + ' and play a few days; then ' + sw('v7 domestic off') + '.',
     'The ecology line reads <b>livestock prey of AL/ML/cavern hunters</b> instead of <b>safe</b>. Your dogs, cats, pigs and chickens become targets of land apexes, ground mesocarnivores and cavern predators only. In DOM2 wolves killed a cavy and a chicken, and the fort’s dogs killed one wolf each run.',
     'It costs animals. Off, nothing of yours is targeted (0 relations in DOM2).',
     tags=(NEW('v7.0'),), src=f'{RUN}: mech.v70.domestic PASS; ECO DOM, DOM2 (fb_safe fix 6c79f32); engine ecologyStatus line 5623.'),
   S('21.3', 'Fishers stay off',
     'Read <b>fishers false</b> in ' + sw('v7') + '. Optionally ' + sw('v7 fishers on') + ' and ' + sw('v7 apply') + ', then off.',
     'Off by default. Turned on, the raws line reads <b>fishers 0</b> on vanilla: every listed fisher (grizzly, black and polar bear, tiger, jaguar, raccoon) already swims.',
     'Fishing bears and tigers made 0 attacks on river pike in FSH2.',
     tags=(NEW('v7.0'),), src=f'{RUN}: mech.v70.fishers_flags NOT-TESTABLE-HERE (RACCOON already swims: 2 → 2); ECO FSH2; 3ca528c.',
     dec='<b>lake apex</b>: fishers off is what reopened the temperate lake’s apex gap.'),
   S('21.4', 'Cavern civ races',
     'With a cavern open, type ' + sw('roster cavern:TROGLODYTE') + ' (or another civ race on your roster).',
     'It is a managed cavern species, active or inactive like any other, with its guild: <b>[guild: …]</b>. Troglodytes, rodent, amphibian, reptile, serpent and ant men, gremlins and plump helmet men hunt by their guild and are prey of cavern apexes only.',
     'Who hunts whom is not shown in the window; the validator found no civ race on CTRL’s roster.',
     tags=(NEW('v7.0'),), src=f'{RUN}: mech.v70.civ_hunt, mech.v70.civ_prey NOT-TESTABLE-HERE; addendum 96b.',
     dec='<b>AP cap</b>: plump helmet man groups would shrink.'),
   S('21.5', 'Gate drain',
     'Play a few days with land arrivals. On the Ledger press ' + k('K') + ' to kind <b>wave</b>.',
     'Now and then <b>also detached TOKEN xN so the gate can open (gate_drain)</b> (or <b>… in cavern N …</b>): after a release, older gated groups go too until at most one flagged animal remains, which is when DF opens its gate.',
     'Long waits between waves (10 days or more) were what T8g found before this.',
     tags=(NEW('v7.0'),), src='engine lines 6188–6218 and V7.drainGate (T8g: 27 of 36 slow releases had freed a one-animal group, p = 5e-6). No validator claim.'),
   S('21.6', 'Sponges',
     'On an ocean fort with the water layer on, type ' + sw('sponges now') + ', then ' + sw('sponges') + '.',
     '<b>sponges: on  N on the ocean floor of T  -- last: …</b>: ribbons of 8–16 sponges along the floor, 2–8 ribbons by the ocean’s size, topped up daily below half. They never appear on the Live tab or in any count.',
     'Without an ocean: <b>sponges: on  0 on the ocean floor</b>. With the water layer off: <b>the water layer is off</b>. Placement uses teleport (r2).',
     tags=(NEW('v7.0'), R2), src=f'{RUN}: mech.v70.sponges PASS; cli.v70.sponges NOT-TESTABLE-HERE (no ocean on CTRL); ECO S8B/S8O (sponges persisted); engine V7.spongeStatus.'),
   S('21.7', 'Vermin classes and gobble',
     'Type ' + sw('vermin classes') + '.',
     'A table <b>CLASS  n  LABEL</b> for the eight tool classes (SWV_GROUND_BUG, SWV_SOIL, SWV_FLYING_INSECT, SWV_SMALL_BIRD, SWV_SMALL_MAMMAL, SWV_HERP, SWV_SMALL_FISH, SWV_OTHER) with their members, then the gobble status line. Consumers (small land insectivores, waterbirds, raptors, bats and land birds, snakes) get GOBBLE_VERMIN_CLASS for their classes.',
     'You cannot watch vermin being eaten in the window; pet cats eat placed vermin, which hides it.',
     tags=(NEW('v7.0'),), src='ECO VRM2, VRM3b, VRM4 (a runtime-written class is honoured); addendum 96e. No validator claim for the verb.'),
   S('21.8', 'Scavenging past the walk',
     'With scavenging on (18.5) and remains in water or a flier scavenger on the map, run ' + sw('scavenge now') + ' a few times and read ' + sw('scavenge') + '.',
     'Remains in water are eaten from the bank or by a swimmer; a flier that cannot close in is landed beside the remains. The status ends <b>fallbacks: VULTURE 1, …</b> when a fallback fired, <b>fallbacks: 0</b> when none did; the ledger logs <b>scavenging: TOKEN landed beside a corpse (fallback)</b>.',
     'In SCV2b the remains were gone before any fallback was needed. Fallbacks teleport (r2) and walks use setPathGoal (r2).',
     tags=(NEW('v7.0'), R2), src='addendum 97; ECO SCV2b/SCV2Wb (6 → 0 in every water cell); scav_ext 1e65e03. No validator claim.',
     dec='<b>swimmers</b>: see 18.5.'),
  ])

# ===================================================================================================== 22
phase(22, 'A season boundary', 'Let the game run into the next season. This is where the roster meets DF.',
  [
   S('22.1', 'Inactive stays away',
     'Play through at least one boundary; watch for the species you made inactive in 2.3.',
     'It never arrives on any layer. X1 on v6.4 let no inactive animal in across two runs where v6.2.1 let in 32 and 12; round 1 saw none in 91,581 ticks.',
     'Any inactive or out-of-season arrival: species, layer, date.',
     tags=(RC('R1'),), src='addendum 94 (X1); round 1 16.1; mech.season.boundary NOT-TESTABLE-HERE in run 074833.'),
   S('22.2', 'The boundary itself', 'At the change of season read the announcements and the Ledger.',
     'An announcement <b>&lt;Season&gt; wildlife roster applied.</b> and a season line in the ledger.', '',
     src='round 1 16.2; engine line 3378.'),
   S('22.3', 'Water groups per body',
     'If your map has an ocean and a river or lake, watch the water line and the Live tab over a few days.',
     'Each water body draws its own groups to its own count; groups swim together and leave on their countdown.',
     'An animal placed on dry land. Placement teleports (r2).',
     tags=(NEW('v7.0'), R2), src=f'{RUN}: mech.v70.groups_water_body, mech.engine.draw PASS; ECO SW6.'),
  ])

# ===================================================================================================== 23
phase(23, 'Persistence and cost', 'Does everything survive a reload, and what does the tool cost.',
  [
   S('23.1', 'Save, quit, reload',
     'Note an inactive species, a stock you set, a v7 switch you changed and the ledger’s last line. Save, return to the title, load, open the window and type ' + sw('v7') + '.',
     'All four as you left them; undo still works; the v7 list shows your change.',
     'Settings back at defaults, or a ledger that restarted. r2 fixed persistent site data on reclaimed forts; a normal save should not be affected. The v7 switches across a reload are untested.',
     tags=(R2,), src='round 1 17.1; mech.save.untouched PASS (config in persistent site data). v7 persistence untested.'),
   S('23.2', 'Frame rate on and off',
     'Unpaused, read the frame rate for a minute with the tool on; then All off and read it again, in the same session.',
     'Within the load noise: round 1 read 189 t/s on and 203 off (one reading each).',
     'Ignore the first seconds after a switch. Wild animal count matters more than the tool: 500 more wild animals cost 38 %.',
     src='round 1 17.2; fps-load-facts.',
     dec='<b>cadence</b>: halves the ecology passes. <b>FPS6</b>: the world-size study that would say what a lived-in fort costs is on hold.'),
  ])

# ===================================================================================================== 24 (no steps)
CANNOT = """<div class="tablewrap"><table class="recheck wide"><thead><tr><th>What</th><th>Why the window cannot show it</th><th>What covers it</th></tr></thead><tbody>
<tr><td>Predators hunt because of the written relation</td><td>Relations live in DF’s tables</td><td>RELS, RELS2, RELS2b, RELS3; CAL; LONE10; SW1/SW1R; mech.ecology.write</td></tr>
<tr><td>Pack-mass floor and sneak bonus</td><td>No readout; placed units are non-wild to DF</td><td>SW2/SW2R, STL/STL2; mech.v70.pack_floor and pack_sneak not testable on CTRL</td></tr>
<tr><td>Solitary package</td><td>Caste skills and gaits</td><td>LONE10 (29 vs 14 placed-prey kills, p = 0.07); mech.v70.solo_raws</td></tr>
<tr><td>The leader is the largest male; how tight groups stay</td><td>Sex and size per unit</td><td>mech.v70.leader_male; COH, COHO, COHR; L1</td></tr>
<tr><td>Gate drain shortens waits</td><td>Days between waves over many releases</td><td>T8g analysis before the change; <b>no run since: needed</b></td></tr>
<tr><td>A species arrives in a season its raws forbid</td><td>Rare; needs whole seasons</td><td>T2 (DF honours NO_ at the pick); mech.v70.seasons_own; <b>arrival test since the change: needed</b></td></tr>
<tr><td>Which vermin each consumer eats</td><td>Vermin are not units</td><td>VRM2, VRM3b, VRM4</td></tr>
<tr><td>The relation sweep changes fights</td><td>Cells cleared are counted, fights are not</td><td>mech.v70.sweep (0 cleared on CTRL); RELS2b; HC4</td></tr>
<tr><td>Civ races hunt and are hunted; forgotten beasts untouched</td><td>Needs a civ race and a beast on the map</td><td>mech.v70.civ_hunt, civ_prey not testable; mech.v70.civ_fb_safe (static); E23e</td></tr>
<tr><td>Fishers fish</td><td>No attack log in the window</td><td>FSH2 (0 attacks)</td></tr>
<tr><td>The builder changes what arrives over a season</td><td>Needs whole seasons</td><td>S8C, S8Cb, S8B, S8O; SW4 (apex FREQUENCY does not steer apexes)</td></tr>
<tr><td>Outgun cap changes fights</td><td>No fight measure</td><td>CAL, P1 (the reason for it); <b>no run of the cap: needed</b></td></tr>
<tr><td>Realms</td><td>Nothing to see but the build’s picks</td><td><b>No rig run: needed</b>; bl.realm backlog</td></tr>
<tr><td>Groups at once shape the map</td><td>Counts over a season</td><td>ECO2-G, SW3B, SW5, SW6</td></tr>
<tr><td>Who scavenged</td><td>Only in the ledger’s per-species count</td><td>SCV, SCV2b/SCV2Wb (species not captured)</td></tr>
<tr><td>Exhaustion timing</td><td>Waves after a niche change</td><td>N1</td></tr>
<tr><td>A savage invasive on a calm map</td><td>DF’s draw</td><td>INV2</td></tr>
<tr><td>Quiet fights and curious residents in long play</td><td>Partly visible</td><td>A1, A2; CB</td></tr>
<tr><td>Cavern traffic under pressure; cavern invasions</td><td>Needs whole seasons</td><td>T9c; E23e (negative)</td></tr>
<tr><td>Cost on a lived-in fort</td><td>One fort, one session</td><td>fps-load-facts; FPS1 sketched; FPS6 on hold</td></tr>
<tr><td>Anything on DFHack 53.16-r2</td><td>All runs so far were r1.1</td><td><b>validate-full on v7.0 under r2: needed first</b></td></tr>
</tbody></table></div>"""
phase(24, 'What this page cannot check', 'A walkthrough sees the window and the console. These parts of v7.0 act inside DF, and only experiments measure them.',
  [], pre=CANNOT)

REPORT = """
    <section class="phase" id="p25">
      <div class="phase-head"><span class="num">25</span><h2>Compile the report</h2>
        <p class="why">Everything you marked and wrote becomes one report. Copy it out and send it; nothing leaves this page on its own.</p></div>
      <div class="report">
        <div class="tester">
          <label>Tester<input id="tName" placeholder="name or handle"></label>
          <label>Fort<input id="tFort" placeholder="fort name, biomes, embark size"></label>
          <label>Game &amp; DFHack<input id="tVer" placeholder="53.16 · 53.16-r2 · plugin v7.0 @ 1e65e03"></label>
          <label>Date<input id="tDate" placeholder="YYYY-MM-DD"></label>
        </div>
        <div class="bar" style="margin-top:14px">
          <button id="btnCompile">Compile report</button>
          <button class="ghost" id="btnCopy">Copy to clipboard</button>
          <button class="ghost" id="btnClear">Clear all marks</button>
          <span class="muted" id="copyMsg"></span>
        </div>
        <textarea id="reportOut" readonly placeholder="Press Compile report. The text is Markdown: the tally, then every anomaly with its note, then skipped steps, then passes."></textarea>
        <details class="load" style="margin-top:16px"><summary>Load a round from its marks file</summary>
          <p class="muted" style="margin:10px 0 6px">Paste the contents of a round’s <code>marks.json</code>. Its marks and notes replace what is on this page for the steps it covers. A file for this page carries <code>"_meta": {"page": "alpha3"}</code>; Alpha Two’s files are refused, because the step numbers differ.</p>
          <textarea id="marksIn" placeholder='{"0.1": {"v": "p", "n": "note"}, "_meta": {"page": "alpha3", "tName": "..."}}'></textarea>
          <div class="bar" style="margin-top:8px"><button class="ghost" id="btnLoad">Load marks</button><span class="muted" id="loadMsg"></span></div>
        </details>
      </div>
    </section>"""

def step_html(s):
    tags = ''.join(f'<span class="tag{"" if kind == "rc" else " " + kind}">{E(txt)}</span>' for kind, txt in s['tags'])
    rows = [f'<div class="do"><span>Do</span><span>{s["do"]}</span></div>',
            f'<div class="expect"><span>Expect</span><span>{s["expect"]}</span></div>']
    if s['watch']:
        rows.append(f'<div class="watch"><span>Watch</span><span>{s["watch"]}</span></div>')
    if s['dec']:
        rows.append(f'<div class="pend"><span>Pending</span><span>{s["dec"]}</span></div>')
    if s['src']:
        rows.append(f'<div class="basis"><span>Basis</span><span>{s["src"]}</span></div>')
    inner = '\n          '.join(rows)
    return (f'        <div class="step" data-id="{s["id"]}"><div class="id">{s["id"]}</div><div class="body"><h3>{s["title"]}{tags}</h3>\n'
            f'          {inner}\n'
            f'          <div class="verdict"></div></div></div>')

sections = []
for num, title, why, steps, pre, pid in P:
    body = ('      <div class="steps">\n' + '\n'.join(step_html(s) for s in steps) + '\n      </div>\n') if steps else ''
    sections.append(f'    <section class="phase" id="{pid}">\n      <div class="phase-head"><span class="num">{num}</span><h2>{title}</h2>\n'
                    f'        <p class="why">{why}</p></div>\n      {pre}\n{body}    </section>\n')

nsteps = sum(len(p[3]) for p in P)
page = f"""<title>Seasonal Wildlife Alpha Three</title>
{fonts}
{style}

<header class="masthead">
  <div class="wrap">
    <div class="eyebrow">Alpha trial three · window and console · v7.0 build</div>
    <h1>Seasonal Wildlife Alpha Three</h1>
    <p class="lede">A play-order walkthrough of the <em>Seasonal Wildlife</em> window and, for the first time, its console verbs, as of the unreleased v7.0 build on the test rig, running on DFHack 53.16-r2. Work through it on a copy of a live fort, mark each step, and compile the report at the end. <b>re-check</b> tags test Alpha Two’s round-one anomalies; <b>new</b> tags mark what v6.8 to v7.0 added; <b>r2</b> tags rest on something DFHack 53.16-r2 changed.</p>
    <div class="facts">
      <span>Plugin <b>seasonal-wildlife v7.0.0</b> (branch v7.0 @ 1e65e03, unreleased)</span>
      <span>Game <b>Dwarf Fortress 53.16</b> · <b>DFHack 53.16-r2</b></span>
      <span>Validated <b>214 pass, 0 fail</b> on 53.16-r1.1 (run 074833); <b>none yet on r2</b></span>
      <span>Open decisions <b>13</b></span>
      <span>Steps <b id="stepcount">{nsteps}</b></span>
    </div>
  </div>
</header>

<div class="wrap layout">
  <nav class="rail" aria-label="Phases">
    <ol id="railList"></ol>
    <div class="tally" aria-live="polite">
      <div><span>Pass</span><span class="n" id="tPass">0</span></div>
      <div><span>Anomaly</span><span class="n" id="tAnom">0</span></div>
      <div><span>Skipped</span><span class="n" id="tSkip">0</span></div>
      <div><span>Unmarked</span><span class="n" id="tOpen">0</span></div>
    </div>
  </nav>

  <main id="main">

    <div class="note" style="margin-bottom:26px"><b>How to read a step.</b> <b>Do</b> is what to press or type; <b>Expect</b> is what you should see; <b>Watch</b> is what tends to go wrong. <b>Pending</b> names an open decision that would change the result. <b>Basis</b> is where the expectation comes from: “run 074833” is validate-full 20261001-074833 on v7.0 (DwarfCron data/validation/full), with its claim ids and screen dumps; ECO names are entries in data/eco-desk/findings.md; addenda are in the tool’s STATE.md. Mark <b>Pass</b> when what you saw matches, <b>Anomaly</b> for anything else (say what you pressed, saw and expected), <b>Skipped</b> when your fort cannot show it.</div>

{''.join(sections)}{REPORT}

  </main>
</div>

{script}
"""
OUT.write_text(page, encoding='utf-8')
n = page.count('class="step" data-id=')
print(f'wrote {OUT} ({len(page):,} bytes); {len(P)+1} sections, {n} steps; '
      f're-check tags {page.count(">re-check ")}, new tags {page.count(">new v")}, r2 tags {page.count(">r2<")}')
