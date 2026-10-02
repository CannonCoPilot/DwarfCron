#!/usr/bin/env python3
"""Build the Alpha Four walkthrough (seasonal-wildlife v7.1 @ fce7d68, DFHack 53.16-r2, test world region8).

Copied from gen_alpha3.py (1 Oct 2026); gen_alpha3.py and alpha3-walkthrough.html are left as they are. Styles and the
marking script come from Alpha Three's generated page, with their own storage key (sw-alpha-four-v1), report title, a
Load guard that accepts only Alpha Four marks, surface sub-heads and step anchors. Steps are data in this script: edit
here, never the HTML.

Order (user, 1 Oct, relayed by the lead): step 0 version and deploy checks, then six features in this order:
(1) biodiversity above the vanilla 7, (2) active ecosystems in all layers, (3) seasonal changes in food webs,
(4) ecological realism, (5) cavern mechanics, (6) other. Inside a feature, steps are grouped by surface: the window
(Panel and tabs), the console, the browser companion. Alpha Three's re-checks are filed under the feature they belong to.

Sources: every window key is from the v7.1 GUI script's HotkeyLabels and Win:onInput (scripts/gui/seasonal-wildlife.lua
at fce7d68). Every console verb is from the v7.1 dispatcher (scripts/seasonal-wildlife.lua, dispatch()) and its usage
strings. Expected results cite the stream notes (docs/v7.1/<stream>.md at fce7d68) or the user's rulings (DwarfCron
data/eco-review/part2/USER-REVIEW-PART2.md, R1-R63). Where a quoted line was seen, it was seen in the offline harnesses
(tests/gui/harness.lua, tests/web/harness.lua, and a copy of the web harness that runs console verbs) on a stubbed
world, never in DF: every step is built, untested, expected by design.
"""
import html
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / 'alpha3-walkthrough.html'
OUT = HERE / 'alpha4-walkthrough.html'
a3 = SRC.read_text(encoding='utf-8')
style = re.search(r'<style>.*?</style>', a3, re.S).group(0)
fonts = re.search(r'<link rel="stylesheet"[^>]*>', a3).group(0)
script = re.search(r'<script>.*?</script>', a3, re.S).group(0)

# ---- script: key, report title, a guard on Load ----
def sub1(old, new):
    global script
    assert old in script, old[:60]
    script = script.replace(old, new)

sub1("var KEY='sw-alpha-three-v1';", "var KEY='sw-alpha-four-v1';")
sub1("lines.push('# Seasonal Wildlife alpha trial three (window and console, v7.0 on DFHack 53.16-r2)');",
     "lines.push('# Seasonal Wildlife alpha trial four (window, console and browser, v7.1 on DFHack 53.16-r2, region8)');")
sub1("lines.push('- Page: Alpha Three (build v7.0 @ 1e65e03, unreleased; 13 decisions open)');",
     "lines.push('- Page: Alpha Four (build v7.1 @ fce7d68; every step built, untested, expected by design)');")
sub1("if((mt.page&&mt.page!=='alpha3')||(!mt.page&&/v6\\./.test(mt.tVer||''))){msg.textContent='These marks are for another page (Alpha Two or earlier): its step numbers do not match this one. Nothing loaded.';return}",
     "if(mt.page!=='alpha4'){msg.textContent='These marks are not for Alpha Four (their _meta.page is '+(mt.page?('\"'+mt.page+'\"'):'missing')+'): Alpha Three and earlier number their steps differently. Nothing loaded.';return}")
sub1("var m=state._meta||{}; var lines=[];", "var m=state._meta||{}; var lines=[]; m.page='alpha4';")
assert 'btnLoad' in script

# ---- style additions ----
extra_css = """
.tag.v71{color:var(--moss);background:var(--moss-soft)}
.surface{display:flex;align-items:baseline;gap:10px;margin:26px 0 0;font:600 0.78rem/1.2 "Source Sans 3",sans-serif;letter-spacing:0.12em;text-transform:uppercase;color:var(--ink-2)}
.surface::after{content:"";flex:1;border-bottom:1px solid var(--rule);transform:translateY(-3px)}
.surface .sn{font:600 0.72rem/1 "JetBrains Mono",ui-monospace,monospace;letter-spacing:0;text-transform:none;color:var(--ink-2);background:var(--paper-2);border-radius:3px;padding:3px 6px}
.surface+.steps{margin-top:12px}
.step .basis b{color:var(--ink);font-weight:600}
.step .body{overflow-wrap:anywhere}
.step{scroll-margin-top:16px}
a.ref{font:600 0.85em "JetBrains Mono",ui-monospace,monospace;text-decoration:none;border-bottom:1px dotted var(--moss)}
.phase-head .num.feat{font-size:2rem}
.featlist{margin:12px 0 0;padding-left:22px;max-width:72ch}
.featlist li{margin:5px 0}
</style>"""
style = style.replace('</style>', extra_css)

E = html.escape
def k(*keys):
    return '+'.join(f'<kbd>{x}</kbd>' for x in keys)
def c(cmd):
    return f'<code>{E(cmd)}</code>'
def sw(rest):
    return c('seasonal-wildlife ' + rest)
def web(rest):
    return c('seasonal-wildlife-web ' + rest)
def ctl(rest):
    return c('seasonal-wildlife-controls ' + rest)

P = []      # phases: (num, title, why, groups, pre, pid, post)
def phase(num, title, why, groups=(), pre='', pid=None, post=''):
    P.append((num, title, why, list(groups), pre, pid or f'p{num}', post))

def S(sid, title, do, expect, watch='', tags=(), src='', rul=''):
    return dict(id=sid, title=title, do=do, expect=expect, watch=watch, tags=tags, src=src, rul=rul)

GUI, CON, WEB = 'In the window', 'At the console', 'In the browser companion'
RC = lambda x: ('rc', 're-check A3 ' + x)
V71 = ('v71', 'new v7.1')
R2 = ('r2', 'r2')
UNT = '<b>Built, untested — expected by design.</b> '
def B(text):
    return UNT + text

# ===================================================================================================== tables
CHANGES = """<div class="tablewrap"><table class="recheck wide"><thead><tr><th>Stream</th><th>Merge</th><th>What a player sees</th><th>Notes (docs/v7.1/)</th></tr></thead><tbody>
<tr><td>vermin</td><td>88d6d68</td><td>Ten vermin classes (SWV_COLONY, SWV_BAT new), each with a switch; the builder's edge table beside the tool's rules; vermin eaters walk to real vermin on the map; <code>vermin census|eats|forage|edges|class</code>.</td><td>vermin.md</td></tr>
<tr><td>ecology</td><td>7446f30</td><td>Ecology every 3,000 ticks, nudge off (R37, R38). Hunter skill profiles on DF's 0-20 scale with a readback; packs recognised; raptors armed and stooping; bears fish, polar bears swim; swimmer scavengers; the cohesion table. Verb <code>hunters</code>.</td><td>ecology.md</td></tr>
<tr><td>groups</td><td>b70f6dd</td><td>Every layer its own group cap, by map size or one fixed cap (R7); the adaptive release clock (R31); caverns gated at 5 with natives counted (R44); largest adult male leads, a leaderless group panics (R32); the animal-people cap (R35).</td><td>groups.md</td></tr>
<tr><td>scav</td><td>1225054</td><td>Scavenging at a natural cadence: found after hours, walked to, eaten over visits (R16-R18); carnivorous swimmers scavenge (R42); curious thieves steal once, then stay (R30).</td><td>scav.md</td></tr>
<tr><td>roster</td><td>a48769b</td><td>Apex step off the ladder and an apex scheduler (R34); a ladder in units (R59); the flying layer with one raptor slot (R50); animal people and giants weighted down (R13, R26); curated water apexes (R43, R49); SAVAGE invasives placed on calm maps (R36); depth and lava guards (R28).</td><td>roster.md</td></tr>
<tr><td>extinct</td><td>7bdebf2</td><td>83 extinct animals corrected: apex FREQUENCY, GRAZER, four roles, three group sizes, fossil realms (R24). Verb <code>extinct</code>.</td><td>extinct.md</td></tr>
<tr><td>water</td><td>0e0771f</td><td>The column-depth survey reads every level (R22); the draw weighs what is already swimming (R62); prey pulls predators in, pelagics too (R14, R59); a stranding guard; 3-5 groups per body by design (R45).</td><td>water.md</td></tr>
<tr><td>irruption</td><td>24e8152</td><td>IRRUPT v2: per-cavern pressure, a warning, waves of the cavern's own civ races with behaviour tokens on 10% each and one unit with all, agitated cavern animals, an end and a cooldown, DF announcements (R4-R6, R10, R35).</td><td>irruption.md</td></tr>
<tr><td>fixes</td><td>c7f9400</td><td>The water layer turns itself on where the map has water, and a thin body borrows the season (the lead's water ruling, confirmed by the user); spaced raw ids work at the console; help and usage list every verb once.</td><td>fixes.md</td></tr>
<tr><td>web</td><td>09d4b0b</td><td>One control registry (<code>seasonal-wildlife-controls</code>, 356 controls) behind the browser page and the Panel; new Controls, Roster and Groups tabs; every set runs a console verb and is read back (R54).</td><td>web.md</td></tr>
<tr><td>perf</td><td>d7cc6f9</td><td>The <code>perf</code> verb (job ms and KB per pass, worst tick, DFHack perf counters, bench); memoized classification, one census per pass, staggered jobs, sliced surveys; every change has a <code>perf.legacy_*</code> switch (R48, R55).</td><td>perf.md</td></tr>
<tr><td>ui</td><td>fce7d68</td><td>The Panel renders the registry in 13 sections with readouts, sliders and read-back (R52, R5, R7); Overview and Layers show the real caps; clipped labels fixed; the tab bar scrolls instead of wrapping.</td><td>ui.md</td></tr>
</tbody></table></div>"""

A3FIX = """<div class="tablewrap"><table class="recheck"><thead><tr><th>Alpha 3</th><th>What Alpha Three found or flagged (v7.0)</th><th>v7.1</th><th>Re-check at</th></tr></thead><tbody>
<tr><td>1.6</td><td>Overview groups row read “N of 12 target” for water and “of 2” for caverns.</td><td>ui.md §3: real caps, “N, cap C each”</td><td>[[2.1]]</td></tr>
<tr><td>2.1</td><td>Three Roster key labels clipped (Ctrl+f, Ctrl+w, Ctrl+g).</td><td>ui.md §3: respaced by drawn width</td><td>[[1.1]]</td></tr>
<tr><td>3.1</td><td>Species page: “Enter: active/inacti” ran into “s: Sp”; “k:” cut at the edge.</td><td>ui.md §3</td><td>[[1.2]]</td></tr>
<tr><td>8.2</td><td>A SAVAGE invasive on a calm map: added, never drawn.</td><td>roster.md R36: the tool places it</td><td>[[1.3]]</td></tr>
<tr><td>12.1</td><td>Layers “groups at once” showed the stored 3/2/2 while the engine used auto 5.</td><td>ui.md §3: “group cap” from QUOTA.groupsFor</td><td>[[2.2]]</td></tr>
<tr><td>12.2</td><td>Layers <kbd>C</kbd> stored a number and never turned auto off.</td><td>ui.md §3: one fixed cap or auto (R7)</td><td>[[2.3]]</td></tr>
<tr><td>12.3</td><td>The table's water cell said 2 while the water line said per body.</td><td>ui.md §3</td><td>[[2.2]]</td></tr>
<tr><td>14.3</td><td>Alt+H vocabulary has none of the v6.9 or v7.0 words.</td><td>Not changed: the Panel's per-control help covers them</td><td>[[6.7]]</td></tr>
<tr><td>16 (head)</td><td>The script's help omitted 13 verbs and listed retired ones.</td><td>fixes.md §1 item 5</td><td>[[0.6]]</td></tr>
<tr><td>16.3</td><td>Raw ids with a space or comma could not be named at the console.</td><td>fixes.md §3: <code>#N</code>, SEA_OTTER form, quotes</td><td>[[3.5]]</td></tr>
<tr><td>16.5</td><td><code>seasons</code> on an inactive species: never tested.</td><td>Unchanged; still untested</td><td>[[3.6]]</td></tr>
<tr><td>16.8</td><td>The unknown-verb list offered <code>quota</code> and <code>water target</code>.</td><td>fixes.md §1 item 5, §5</td><td>[[0.6]]</td></tr>
<tr><td>18.1</td><td><code>limits water groups auto</code> printed the usage.</td><td>fixes.md §3: accepted, sets <code>limits formula</code></td><td>[[2.7]]</td></tr>
<tr><td>18.5</td><td>Scavenging status repeated the last non-empty pass and read “on” with the rotation off.</td><td>scav.md §10; fixes.md §3</td><td>[[4.14]]</td></tr>
<tr><td>fixes.md</td><td><code>groups cavern max</code> was dead, overwritten at the next load.</td><td>fixes.md §3: alias of <code>cap</code></td><td>[[5.4]]</td></tr>
<tr><td>fixes.md</td><td>Layers “AGITATED: TOKEN xN” read <code>g.armed</code>, which v7.1 never sets.</td><td>ui.md §3: IRRUPT v2 phase</td><td>[[5.1]]</td></tr>
</tbody></table></div>"""

RULINGS = """<div class="tablewrap"><table class="recheck"><thead><tr><th>A3 decision</th><th>What the user ruled (USER-REVIEW-PART2)</th><th>Steps</th></tr></thead><tbody>
<tr><td>cadence</td><td>R37: ecology every 3,000 ticks. YES.</td><td>[[6.5]], [[4.2]]</td></tr>
<tr><td>nudge</td><td>R38: nudge off by default. YES.</td><td>[[6.5]]</td></tr>
<tr><td>sneak</td><td>R8, R40, R58: keep the solo package; skills on the 0-20 scale; “assume it can work”.</td><td>[[4.4]], [[4.7]]</td></tr>
<tr><td>x3</td><td>R41: KEEP the x3 pack bonus; the null was a handling defect. Retry.</td><td>[[1.9]]</td></tr>
<tr><td>apex</td><td>R34: drop the apex step; steer apexes by placement and stock. YES.</td><td>[[1.6]], [[1.13]]</td></tr>
<tr><td>cavern cap</td><td>R44: the tool gates cavern layers; a fixed max of 5 groups each.</td><td>[[5.2]], [[5.4]]</td></tr>
<tr><td>water 2</td><td>R45: NO “2 per body”; manage water like land; 3-5 groups on its own.</td><td>[[2.14]]</td></tr>
<tr><td>swimmers</td><td>R42 (and R17): carnivorous swimmers scavenge, sharks included. YES.</td><td>[[4.15]]</td></tr>
<tr><td>AP cap</td><td>R35: a cap for animal people in caverns, lifted during an irruption. YES.</td><td>[[5.14]]</td></tr>
<tr><td>savage</td><td>R36: Add invasive places SAVAGE species on calm maps itself. YES.</td><td>[[1.3]]</td></tr>
<tr><td>push</td><td>R39: push DwarfCron and seasonal-wildlife. YES.</td><td>[[0.4]]</td></tr>
<tr><td>FPS6</td><td>R46: hold.</td><td>[[6.22]]</td></tr>
<tr><td>lake apex</td><td>R43, R49: bears fish (fixed, not switched off); a curated aquatic apex list; no sea lamprey as apex.</td><td>[[1.8]], [[4.9]], [[4.12]]</td></tr>
</tbody></table></div>"""

# ===================================================================================================== Δ
phase('Δ', 'What changed since Alpha Three',
  'Alpha Three walked v7.0. The user then ruled on 63 points (R1-R63) and said to build everything first and test after. Twelve streams built v7.1; this page walks all of it. Read this before you start.',
  pid='pchanges',
  pre='<div class="note"><b>Everything here is built and untested.</b> The target is <code>seasonal-wildlife</code> branch <b>v7.1 @ fce7d68</b> (merged 1 Oct, 17:58), 64 commits past v7.0. No rig was used for any of it (“build first, optimistic stance”). Each Expect line is what the stream notes or the user\'s rulings say should happen; a line quoted from a readout was seen only in the offline harnesses on a stubbed world, where every count is zero. So every step is <b>built, untested — expected by design</b>, and a mismatch you find is the first evidence either way.</div>'
      '<div class="note"><b>Test world: region8, “The Last Planets”</b> (Snospdastrasp; R11). DFHack <b>53.16-r2</b>. The user confirmed the lead\'s water decision: <b>the water layer turns itself on where the map has water, with the season spill</b>; steps expect that.</div>'
      '<h3 class="sub">The six features, in the order the user set</h3><ol class="featlist">'
      '<li><b>Biodiversity above the vanilla 7</b>: wider rosters, the builder and its guild slots, the animal-person and giant weights, extinct fixes, Add invasive with SAVAGE, the apex scheduler.</li>'
      '<li><b>Active ecosystems in all layers</b>: land, flying, water bodies, caverns per depth; per-layer group caps, the adaptive clock, leaders and panic, aquatic leaders, the water layer auto-on with season spill.</li>'
      '<li><b>Seasonal changes in food webs</b>: the tool\'s season deal, rotation, pairs and vermin edges by season, the bears\' run season, apex presence per season.</li>'
      '<li><b>Ecological realism</b>: pyramid targets, hunter skills, packs, the raptor stoop, bears and polar bears, scavenging at a natural cadence, swimmers, vermin foraging, curious thieves, the pelagic pull, prey mass.</li>'
      '<li><b>Cavern mechanics</b>: the gate at 5, natives, civ races, irruption v2 end to end, the animal-people cap and its lift, depth and lava guards, demons untouched.</li>'
      '<li><b>Other</b>: Panel and registry mechanics, the browser companion, the console verbs, <code>perf</code>, ledger and undo, persistence and cost.</li></ol>'
      '<p class="muted" style="margin-top:8px;max-width:72ch">Inside each feature the steps are grouped by surface: the window (tabs and Panel), the console, the browser companion. Step 0 checks the build first.</p>'
      '<h3 class="sub">Twelve streams since v7.0</h3>' + CHANGES +
      '<h3 class="sub">Alpha Three\'s findings, and where to re-check them</h3><p class="muted" style="margin-top:6px;max-width:72ch">Alpha Three was never played on v7.0; these are the faults its page flagged and the notes fixed. The ui notes call 12.1 and 12.2 “11.3” and “11.4”.</p>' + A3FIX +
      '<h3 class="sub">Alpha Three\'s thirteen open decisions, as the user ruled</h3>' + RULINGS +
      '<h3 class="sub">Window keys: what changed</h3><p style="margin-top:6px;max-width:72ch">The Panel has new keys: <kbd>S</kbd> next section, <kbd>Shift</kbd>+<kbd>S</kbd> back, <kbd>Enter</kbd> set, <kbd>←</kbd> <kbd>→</kbd> or <kbd>-</kbd> <kbd>+</kbd> one step (<kbd>Shift</kbd> ten), <kbd>Shift</kbd>+<kbd>Enter</kbd> previous choice, <kbd>D</kbd> default, <kbd>Alt</kbd>+<kbd>S</kbd> find, <kbd>A</kbd> all on, <kbd>X</kbd> all off, <kbd>R</kbd> refresh. The species page has <kbd>V</kbd> (its v7 rows). Layers <kbd>C</kbd> is now “Group cap (R7)” and <kbd>I</kbd> toggles irruptions. Below 92 columns the tab bar scrolls with <kbd>Ctrl</kbd>+<kbd>T</kbd> / <kbd>Ctrl</kbd>+<kbd>Y</kbd>. DFHack draws plain letter keys in lower case (<code>s: Section</code>). Every other key is as in Alpha Three.</p>')

# ===================================================================================================== 0
phase(0, 'Before you start: version and deploy',
  'Pick a region8 fort, back it up, and check that the build, the DFHack and the new module are the ones this page describes.',
  [(None, [
   S('0.1', 'Choose the world and the fort',
     'Open the save folder <code>region8</code> (Snospdastrasp, “The Last Planets”) and embark under a new name, or load a fort already embarked from it. Aim for a <b>3x3 or larger</b> embark with an ocean shore or a lake or river, and a cavern your dwarves will open. A second, savage fort helps phases 1 and 5.',
     'A fort on region8. Note its biomes, embark size, water, open caverns and whether it is calm or savage.',
     'Never save over region8: it is the user\'s own world and the harness\'s reference (HARNESS-v71 §5). Pick the folder, not the world name: same-seed worlds share a name. The group cap is floor(√embark tiles) + 1, so a 1x1 holds 2 groups per layer, a 3x3 4, a 4x4 5. No region8 test forts exist yet (no survey has run).',
     src=B('R11 (region8 for all testing); experiments/HARNESS-v71.md §5; groups.md R7 formula.')),
   S('0.2', 'Back it up',
     'Copy the fort\'s save folder before you open the window.',
     'A copy that the tool has never touched: your control.',
     'v7.1 writes more raws than v7.0 (extinct corrections, skill profiles, raptor BENIGN, irruption caste windows); every one is put back on disable, All off and unload, but use the copy for phases 1 and 5.',
     src=B('extinct.md design 2; ecology.md; irruption.md §10.')),
   S('0.3', 'DFHack is 53.16-r2',
     'Open the launcher (<kbd>`</kbd>) and read its title, or type ' + c('help') + ' in the DFHack console.',
     'The version reads <b>53.16-r2</b>. If the launcher does not offer <code>gui/seasonal-wildlife</code>, turn on dev mode (<kbd>Ctrl</kbd>+<kbd>D</kbd> in the launcher) or type the command.',
     'Nothing of v7.1 has run on r2 or on r1.1. Read the DF console log (stderr.log in the game folder) for any traceback naming seasonal-wildlife.',
     tags=(R2,), src=B('Alpha Three 0.3; data/dfhack-r2/REPORT.md.')),
   S('0.4', 'The tool is 7.1.0',
     'Type ' + c("lua print(reqscript('seasonal-wildlife').CACHE.release)") + ', then ' + c('help seasonal-wildlife') + '.',
     'The release reads <b>7.1.0</b>. The help lists the v7.1 verbs with “v7.1” beside them: <code>water layer</code>, <code>water spill</code>, <code>vermin forage</code>, <code>scavenge natural|swimmers|defer</code>, <code>curious reform</code>, <code>hunters</code>, <code>roster apex|gobble|depth|aquatic|set</code>, <code>extinct</code>, <code>irruption</code>, <code>perf</code>.',
     'The docs stream is bumping the release; at fce7d68 the cache key still reads <b>7.0.0</b>. If you see 7.0.0 and a 13-section Panel (6.2), you have the merge before the bump: note it and go on.',
     tags=(V71,), src=B('engine CACHE.release (line 508-509 at fce7d68); help header lines 20-115.'),
     rul='R39: push seasonal-wildlife. YES. The v7.1 branch is on origin; the bump and release are the docs stream\'s.'),
   S('0.5', 'The controls module is deployed',
     'Type ' + c('seasonal-wildlife-controls') + '.',
     'Twelve lines, one per section, then a total: <b>switches 20, limits 19, caverns 10, leaders 13, roster 40, ecology 31, water 33, scavenging 38, vermin 23, extinct 9, v7 17, irruption 103</b>; <b>7 species rows, 21 actions, 27 readouts</b>.',
     'If the command is unknown, the deploy missed <code>seasonal-wildlife-controls.lua</code>. The window then says so on the Panel and keeps only the switches and jobs; the web server will not start.',
     tags=(V71,), src=B('web.md §1; ui.md §1 and merge hazards; offline registry run: 356 controls, 424 verb checks pass, 0 fail.')),
   S('0.6', 'Help and usage list every verb once',
     'Type ' + sw('help') + ' (any unknown word does the same).',
     'One line that starts <b>Usage: seasonal-wildlife [gui|status|now|enable|disable|preset|undo|layer …</b> and ends with <code>… realm …|v7 …|extinct …|irruption …|perf …]</code> and the TOKEN note (quoted, SEA_OTTER, or #N). No <code>quota</code>, no <code>cavern [on|off|now]</code>, no <code>water target</code>.',
     '', tags=(RC('16 head'), RC('16.8')),
     src=B('fixes.md §1 item 5 and §5 (validator wording); seen in the offline verb run.')),
   S('0.7', 'A v7.0 fort migrates once',
     'Only if this fort ran v7.0 before: load it with v7.1 and type ' + sw('groups ecology') + ', ' + sw('v7') + ', ' + sw('limits') + ' and ' + sw('irruption') + '.',
     'Each old default moves once: ecology every 3,000 ticks (was 1,500), nudge off, fishers on with the nine bears, water animal ceiling none (was 12), <code>layer_groups</code> true (retired), seasons_own true, and <code>irruption</code> shows its v7.0 settings carried over (“migrated v7.0” once). A value you had changed yourself is kept.',
     'A fresh region8 embark has nothing to migrate: mark Skipped.',
     tags=(V71,), src=B('ecology.md “Migration”; groups.md config (migration); irruption.md §6 Migration.')),
   S('0.8', 'Frame-rate baseline',
     'In Settings, show the frame rate. Read it unpaused for a minute at your usual speed, with the window closed.',
     'A baseline for 6.22.',
     'Two loads of the same fort differ by 10-15 % on their own; one long session loses up to 28 %.',
     src=B('fps-load-facts.')),
  ])])

# ===================================================================================================== 1
phase(1, 'Biodiversity above the vanilla 7',
  'Rosters wider than DF\'s own seven per niche: the guild builder fills slots from the embark\'s whole pool, animal people and giants weighted down, extinct animals corrected, SAVAGE invasives placed, and an apex scheduler that keeps apexes present.',
  [(GUI, [
   S('1.1', 'Roster: the columns and the keys in full',
     'Open the window (' + c('gui/seasonal-wildlife') + ') and click <b>Roster</b>. Read the key labels under the list.',
     'Columns CREATURE, ROLE, SIZE, HAB, BIOME, SEASON, STOCK, ODDS, act, WHY. The labels read in full: <b>Ctrl+f: Send off + next</b>, <b>Ctrl+w: Stock (row)</b>, <b>Ctrl+g: Stock (filter)</b>, <b>Alt+o: Odds (row)</b>, <b>Ctrl+x: Add invasive</b>. The Biome filter shows the short code, as the BIOME column does.',
     'Any label that runs into its neighbour. WHY is narrower now (up to 17 cells); the species page keeps the full reason.',
     tags=(RC('2.1'),), src=B('ui.md §3 (clipped labels, WHY column, filter row); tests/gui/harness.lua: no two hotkey labels overlap (a mutation run of the old positions fails 23 checks).')),
   S('1.2', 'The species page and its v7 rows',
     'Select an animal and press ' + k('I') + '. Read the foot and the <code>v7:</code> line; press ' + k('V') + '.',
     'The foot reads <b>Enter: active/inactive</b>, <b>s: Sp</b> … <b>k: stock</b>, <b>v: v7</b>, none overlapping. A facts line <b>v7: skill level auto, fishes [off], cohesion &lt;auto&gt;, water apex &lt;off&gt;</b> (the rows that fit this species). <kbd>V</kbd> lists those rows (skill level, never stoops, fishes, swimmer scavenger, cohesion, water apex, extinct correction); setting one runs its console verb.',
     'A row offered for a species it does not fit (a never-stoops row on a non-raptor).',
     tags=(RC('3.1'), V71), src=B('ui.md §3 (species page); web.md §1 (SPECIES rows); seen in the offline GUI harness.')),
   S('1.3', 'Add invasive: a SAVAGE species on a calm map',
     'On a calm fort, press ' + k('V') + ' until View reads Add invasive, select a SAVAGE species that suits the biome (CENOZOIC_SMILODON on temperate land), press ' + k('Ctrl', 'X') + '. Then type ' + sw('roster apex') + '.',
     'The status line names the regions and the state; the species is on the Roster at once. On a calm map the tool now <b>places one group from the new entries\' stock</b>, and more through the apex scheduler (invasive presence 25 %). The roster status line counts <b>invasive placed: 1</b>.',
     'Alpha Three expected nothing to arrive (INV2: 0 smilodons in a season).',
     tags=(RC('8.2'), V71), src=B('roster.md R36 (ROSTER.invasiveAdded); mech.v71.invasive.'),
     rul='R36: Add invasive places SAVAGE species on calm maps itself. YES.'),
   S('1.4', 'Panel: Roster & apexes',
     'Press ' + k('Alt', 'P') + ', then ' + k('S') + ' until the section list marks <b>&gt;Roster &amp; apexes</b>.',
     'Readouts first: <b>roster v7.1: ladder units, apex step none (raw, cap 5), AP pick x0.1 freq x0.25, giants pick x0.2 freq x0.5, pack x3; apex scheduler on, calm map (cap 1) …</b>, one <b>apex LAYER present P% (target T%)</b> line per layer and one <b>pyramid PART H/C/A%, target …</b> line per part. Then groups APEX SCHEDULER, LADDER AND PYRAMID, PICKS AND FREQUENCIES, PREDATION MODEL; then actions (Build the roster, Apex decision now) and readouts.',
     'A readout that throws: the section would show an error line instead.',
     tags=(V71,), src=B('ui.md §2 (Roster & apexes readouts); offline GUI harness (section drawn, 40 controls).')),
   S('1.5', 'Panel: Extinct',
     'Press ' + k('S') + ' to <b>Extinct</b>. Select <b>Grazers</b> and press <kbd>Enter</kbd> twice; then <kbd>Enter</kbd> on the readout <b>Rows</b>.',
     'The status line <b>extinct: fix on [freq grazer roles cluster realms units stand_down]; …</b>. Each Enter flips the switch; the bottom lines read <b>ran: seasonal-wildlife extinct set grazer off</b> and <b>Grazers: [off] (read back)</b>, then on again. Rows opens a scrolling list of <code>extinct-entry …</code> lines.',
     '', tags=(V71,), src=B('extinct.md (verbs, Panel exposure); ui.md §1 (bottom lines).')),
  ]), (CON, [
   S('1.6', 'Build the land roster',
     'On the copy, type ' + sw('roster build land') + '. Read it, open the Roster, then type ' + sw('undo') + '.',
     'The v7.0 receipt (slots, UNFILLED, OUTGUNNED, ladder) plus: a <b>ladder-info target=… units=true herb=… carn=… binding=… floored=…</b> line; <b>apex TOKEN: FREQUENCY N (no ladder step; the apex scheduler places it)</b> for each apex; <b>gobble edges: N over M vermin</b>; the vegetation index. Ladder values are the unit share (FREQUENCY divided by mean group), none below 1. <code>undo</code> prints <b>undid: roster build land</b>.',
     'An apex with a ladder value above 5. Under the v2.2 port the land carnivore share should sit near the 20 % pyramid target, not v2.1\'s 31 %.',
     tags=(V71,), src=B('roster.md (R34, R59, R57; verbs; mech.v71.ladder.units).'),
     rul='R34: drop the apex step from the ladder; steer apexes by placement and stock. R59: the ladder targets units. R57: v2.2 port approved.'),
   S('1.7', 'The flying layer',
     'Type ' + sw('roster build flying') + ', read it, then ' + sw('undo') + '.',
     'Slots <b>APX 0-1, RP 1-1, LB 1-2, WB 0-2</b>. No vulture, buzzard, kea or raven in APX. Flying presence defaults to 0 %: no calm flying apex exists.',
     '', tags=(V71,), src=B('roster.md R50 (ROSTER.SLOTS.flying), decision 4; mech.v71.flying.'),
     rul='R50: flying layer raptor slots set to 1.'),
   S('1.8', 'The water roster and the curated apexes',
     'On a fort with an ocean, type ' + sw('roster build water') + ' and ' + sw('roster aquatic') + '; undo the build.',
     'APE and PE seat on any ocean map (PE 1-2 with deep columns); a slot with no candidate reads UNFILLED with its reason. FISH_LAMPREY_SEA seats as MW. <code>roster aquatic</code> prints <b>33</b> lines <code>aquatic-apex TOKEN apex|pelagic|fisher</code>: sharks, crocodiles, alligators, the extinct marine apexes; bears as <b>fisher</b>; no DIMETRODON (taken off by the fixes).',
     '', tags=(V71,), src=B('roster.md R14, R59, R43, R49 and the curated list; fixes.md §1 (DIMETRODON off); mech.v71.water.pelagic.'),
     rul='R14: no pelagics on OCEAN2, design a fix. R59: a shallow ocean should seat a pelagic slot. R49: no sea lamprey as a lake or river apex.'),
   S('1.9', 'Animal people, giants and the x3 pack bonus',
     'Type ' + sw('roster set') + '. Then build land three times, undoing each, and note how often an animal person or a GIANT_ is picked.',
     'The knobs: <b>ap_pick=0.1, ap_freq=0.25, ap_freq_floor=1, giant_pick=0.2, giant_freq=0.5, pack_bonus=3</b>. Animal people are about a tenth as likely as another animal, giants a fifth; a slot only they can fill still fills. Pack hunters (raw cluster max above 1) take x3 and can now be the seed.',
     'An animal person on most builds of a calm map. v2.2\'s SN/SNP slots (an AP on 866 of 880 savage rosters) are ported but off (<code>sn_slots</code>).',
     tags=(V71,), src=B('roster.md R13, R26, R41 (three defects fixed), decision 5.'),
     rul='R13: ANIMAL_MAN at about 1/10. R26: lower roster and FREQUENCY odds for ANIMAL_MAN and GIANT_*. R41: KEEP the x3 bonus. R61: 19 animal people at FREQUENCY 0 get a floor of 1.'),
   S('1.10', 'Outgunned pairs on every layer',
     'Type ' + sw('roster outgun land') + ', then ' + sw('roster outgun flying') + '.',
     '<b>roster outgun LAYER -- N pair(s) (factor &gt;= 2.0)</b> with <code>outgunned: PRED pack vs PREY herd 3.1x</code> lines, or <b>-- none found</b>. Nothing is written. Flying is new.',
     '', tags=(V71,), src=B('roster.md verbs (roster outgun [layer], any of the four layers).')),
   S('1.11', 'Extinct corrections',
     'Type ' + sw('extinct') + ', ' + sw('extinct list') + ', ' + sw('extinct mods') + '. Then ' + sw('extinct CRETACEOUS_TYRANNOSAURUS off') + ' and ' + sw('extinct CRETACEOUS_TYRANNOSAURUS on') + '.',
     'The status line <b>extinct: fix on [freq grazer roles cluster realms units stand_down]; N of 83 table species in this world, M in the embark; written: FREQUENCY a, GRAZER b, roles c, cluster d, unit flags e; stood down s; attack mods none</b>. <code>list</code>: one <code>extinct-entry</code> line per row, e.g. <b>CRETACEOUS_TYRANNOSAURUS freq=50-&gt;2 realm=NEA</b>, <b>CENOZOIC_TITANOBOA LARGE_PREDATOR=on freq=30-&gt;3 guild=AW</b>, then five <code>extinct-mod-only</code> lines. <code>mods</code>: <b>attack mods active: 0 …</b>. The TOKEN off/on prints the row, ending <b>| skipped</b> when off.',
     'With the rotation off: <b>raws not written: rotation is off (the model already reads the corrections)</b>.',
     tags=(V71,), src=B('extinct.md (table, verbs, status line); seen in the offline verb run.'),
     rul='R24: EXTINCT creatures lack the tags they ought to have.'),
   S('1.12', 'The realm table',
     'Type ' + sw('realm table') + ', then ' + sw('realm') + '.',
     'A head <b>realm-table entries=250 missing_from_raws=0 switch=off realm=unset …codes=NEA,PAL,IND,AFR,NEO,AUS,ARC,NZ,MAD,ANT,OCE</b>, then one <code>realm-entry TOKEN CODES raws=yes|no</code> per entry. <code>realm</code>: <b>realm: unset …</b> and the realms-switch note.',
     'missing_from_raws above 0 on a vanilla install.',
     tags=(V71,), src=B('roster.md (realm table, R57); mech.v71.realm.table.'),
     rul='R57: realm table approved.'),
   S('1.13', 'The apex scheduler',
     'After a land build that seated an apex, type ' + sw('roster apex status') + ', ' + sw('roster apex now land') + ', ' + sw('roster apex target land 30') + ', then ' + sw('roster apex target land 25') + '.',
     '<b>apex-state land groups=… units=… presence=…% placed=… last=…</b> lines. <code>now land</code> places one apex group from stock (or says why not: <b>cap 1 reached</b> on a calm map with one there). The group is a placed record, counts toward groups at once and leaves on a ~21,500-tick countdown. The target change is one ledger line and one undo step.',
     'With no build the scheduler has nothing to place: <b>apex now: nothing placed</b>.',
     tags=(V71,), src=B('roster.md (apex scheduler, decision 3-4; mech.v71.apex.place, apex.cap); seen in the offline verb run.'),
     rul='R34: steer apexes by placement and stock. R9: pyramid targets accepted (apex on land 20-30 % of the season).'),
  ]), (WEB, [
   S('1.14', 'Roster tab',
     'Start the companion (6.16) and open <b>Roster</b>.',
     'Per roster part (land, flying, water, caverns): the H/C/A pyramid now (unit share = odds x mean group, and wave share) against its target; species by builder slot and guild; the apex scheduler status; <b>Build</b> and <b>Apex now</b> buttons (Build asks first).',
     'The unit share is an approximation of what the ladder writes.',
     tags=(V71,), src=B('web.md §3 (Roster), open risks.')),
   S('1.15', 'Species chips and v7 rows',
     'Open <b>Species</b> and pick a predator, an extinct animal and an animal person.',
     'Slot, guild, part, giant and extinct chips; the scavenger and gobble reading; the per-species v7 rows that fit (skill level, never stoops, fishes, swimmer scavenger, cohesion, water apex, extinct correction); group size low to high with a <code>size KEY N</code> setter. Min and max are no longer swapped.',
     '', tags=(V71,), src=B('web.md §2 (web-cluster-order fixed), §3 (Species).')),
  ])])

# ===================================================================================================== 2
phase(2, 'Active ecosystems in all layers',
  'Land, flying, each water body and each cavern hold their own groups: a cap per layer key, an adaptive clock that fills it, leaders that are the largest adult male, and a water layer that turns itself on.',
  [(GUI, [
   S('2.1', 'Overview: the real caps',
     'Click <b>Overview</b>.',
     'The groups row reads <b>N of C</b> on land and <b>N, cap C each</b> for water and caverns (caverns 5). No “target” and no “of 2”. With irruptions on, an <code>irruptions:</code> line under the patterns.',
     'The Overview and Live still print “cavern placement: retired in v6.5 …” from the cavern status; it is wording, not a fault.',
     tags=(RC('1.6'), V71), src=B('ui.md §3 (Overview groups row); fixes.md §6; offline GUI harness (“0 of 2”, “0, cap 2 each”, “0, cap 5 each” on a stubbed 1x1).')),
   S('2.2', 'Layers: group cap and release clock',
     'Click <b>Layers</b>.',
     'Rows <b>group cap</b>: <b>C (map size)</b>, <b>C/body, map size</b>, <b>5/cavern</b>, <b>-</b>; <b>release clock</b>: <b>adapt 0.5-20d</b> on land, water and caverns. Then ceiling, pattern, coupling, cohesion, ecology switch, nudge after, pack size, irruptions, cavern pressure. 86 columns, no row cut.',
     'A cap that differs from the Live limits line (2.5).',
     tags=(RC('12.1'), RC('12.3'), V71), src=B('ui.md §3 (Layers tab: 18 + 4 x 17 = 86); offline GUI harness.')),
   S('2.3', 'Layers C: one fixed cap, or the formula',
     'On Layers press ' + k('C') + ', enter <b>3</b>; read the status line and the Live limits line. Then ' + k('C') + ' and <b>auto</b>.',
     'The prompt is titled <b>Group cap (every layer)</b>. 3 sets one fixed cap on every layer: status <b>Fixed cap: 3 (read back)</b>; Live reads <b>limits [single fixed cap 3 on every layer]</b>, caverns the smaller of 3 and their own. <code>auto</code> (or empty) goes back to the map-size formula.',
     'Alpha Three\'s fault was that C stored a number the engine ignored.',
     tags=(RC('12.2'), V71), src=B('ui.md §3 (C asks for one fixed cap or auto); groups.md R7.'),
     rul='R7: layers get their own limit, a function of map size; no per-layer switch; a toggle between one fixed cap on every layer and the formula.'),
   S('2.4', 'Panel: Limits & groups',
     'Press ' + k('Alt', 'P') + ' and ' + k('S') + ' to <b>Limits &amp; groups</b>.',
     'Readout <b>Group cap: MAP-SIZE FORMULA: sqrt(embark tiles) + 1 = N on land and each water body; caverns 5 each</b>, then a table <code>layer cap by now target W d next led panic</code> with one row per layer key: <code>land</code>, <code>water:ocean</code>, <code>water:river</code> …, <code>cavern:0</code>… Controls: Group cap &lt;map-size formula&gt;, Fixed cap, three animal ceilings, three patterns, the release clock (Adaptive [ON], Target band 1, Catch-up 1, Jitter 0.35, Shortest gap 0.5 days, Longest gap 20 days, W weight, three W priors), Drawn groups leave with their leader.',
     '', tags=(V71,), src=B('ui.md §2 (Limits & groups readout: PNL.ctl.groupMap); groups.md (Panel values); offline GUI harness.')),
   S('2.5', 'Live: limits and groups',
     'Click <b>Live</b>; read the limits line and the Groups block.',
     'The limits line from 2.4. Group rows carry their state: <b>led by #id</b>, <b>PANIC</b>, <b>unled</b>, <b>native</b>, <b>seeded</b>, <b>placed</b>, <b>adopted</b>, the water body, and <b>IRR</b> for an irruption wave.',
     'The Groups line still reads <b>Groups: ON N at once gap 5-20 days</b>: the v6 gap, while the clock is adaptive (Layers says <b>adapt 0.5-20d</b>). Mark it if it misleads you.',
     tags=(V71,), src=B('groups.md (groupsStatus rows); irruption.md §5 (IRR); offline GUI harness (Live tab).')),
   S('2.6', 'Panel: Leaders & panic',
     'Press ' + k('S') + ' to <b>Leaders &amp; panic</b>.',
     'Readouts <b>leaders (R32): largest adult male, none without one; on panic on (2 day(s), 12 tiles, scatter) re-elect after panic off lost 0 panics 0 flights 0</b> and the animal-people line. Controls: Panic, Panic days, Flight radius, Flight &lt;scatter&gt;, Flocks panic too, Re-elect after panic, Leader [male], Cohesion and the five follow distances (herd 8, pack 4, flock 12, school 5, pod 5).',
     '', tags=(V71,), src=B('groups.md R32 (Panel values); offline GUI harness.')),
  ]), (CON, [
   S('2.7', 'limits: formula, fixed, and the retired per-layer number',
     'Type ' + sw('limits') + ', ' + sw('limits fixed 4') + ', ' + sw('limits land groups 3') + ', ' + sw('limits water groups auto') + ', ' + sw('limits formula') + '.',
     '<b>limits [map-size formula per layer]: land N (map size) group(s) at once, ceiling none; water N (map size) group(s) at once per water body, ceiling none; cavern 5 (fixed, R44) …</b> and <b>on the map now: land … deep …</b>. <code>fixed 4</code>: <b>[single fixed cap 4 on every layer]</b>, caverns 4. <code>land groups 3</code>: <b>note: per-layer group numbers are retired (R7): every layer now has the single fixed cap 3 …</b>. <code>water groups auto</code> is accepted and goes back to the formula.',
     'Water\'s animal ceiling is none by default now (was 12).',
     tags=(RC('18.1'), V71), src=B('groups.md R7, R45; fixes.md §3 (water groups auto accepted); seen in the offline verb run.'),
     rul='R45: NO “2 per body” default; manage water groups like land groups; no hard caps.'),
   S('2.8', 'groups layers: one row per layer key',
     'Type ' + sw('groups layers') + '.',
     'The limits line; <b>release clock: adaptive (Little\'s law, R31) target in [cap-1.0, cap], catch-up 1.00, jitter +-35%, gap 0.5-20 days</b>; one row per key (<code>land</code>, <code>water:&lt;body&gt;</code>, <code>cavern:&lt;d&gt;</code>): <b>cap C (map size) target L now n W d (n) next release … leaders unled panic lost</b>; then the cavern gate, leaders and animal-people lines.',
     '“next release waits on DF\'s next wave” is the clock saying DF has nothing gated, not a fault.',
     tags=(V71,), src=B('groups.md (status, R31); seen in the offline verb run.'),
     rul='R31: a hidden limit held every layer at 2-3; approach the per-map-size limit with a stochastic feel.'),
   S('2.9', 'The adaptive clock fills toward the cap',
     'Type ' + sw('groups clock jitter 0.5') + ', read it, then ' + sw('groups clock jitter 0.35') + '. Over a few game days watch the land row of ' + sw('groups layers') + '.',
     '<b>… jitter +-50% …</b>, then back. Over time <b>now</b> wanders just under the cap (target in [cap-1, cap]); a departure brings the next release forward; at the cap no release (“paused at the cap”). Desk simulation: mean 4.7 groups at cap 5, 6.6 at cap 7.',
     'Supply can still bind: DF must have a wave gated.',
     tags=(V71,), src=B('groups.md R31 (controller, desk simulation; mech.v71.clock.*).')),
   S('2.10', 'Leaders and panic',
     'Watch a tracked herd or pack (Live, ' + k('F') + ' to follow). If its leader dies or leaves, read the Live row and ' + sw('ledger 10 panic') + '.',
     'The leader is the largest adult male; a group with no adult male is <b>unled</b>. When the leader is lost the group is never re-led; a herd, pack, school or pod <b>panics</b> for 2 days and scatters within 12 tiles; ledger lines of kind <code>panic</code> at the start and end.',
     'The window\'s Ledger <kbd>K</kbd> filter has no <code>panic</code> or <code>lead</code> kind: use the console, or kind “all”.',
     tags=(V71,), src=B('groups.md R32 (mech.v71.lead.male, lead.lost, panic.walk); GUI led_kind options.'),
     rul='R32: leader = largest adult male; no male, no leader; if the leader dies, no leader, and a panic-shock in herds and packs.'),
   S('2.11', 'Aquatic leaders',
     'On a water fort type ' + sw('water now ocean') + ' (or <code>lake</code>, <code>river</code>), then read the group on Live.',
     '<b>water: drew TOKEN xN into the ocean (salt) [N ms]</b>; the school or pod is led at once by a <b>wet</b> leader (on water at level 4/7 or more); cetaceans are a <b>pod</b>; sponges and IMMOBILE never led. DF\'s embark-seeded schools are adopted as <b>seeded</b> (led, never counted).',
     'A leader standing on dry land: it should step down quietly.',
     tags=(V71,), src=B('groups.md C §9.3 (aquatic leaders); water.md (water now BODY); mech.v71.lead.water, lead.seeded.')),
   S('2.12', 'Water layer auto-on with season spill',
     'On a fresh fort with water, enable the tool (open the window or ' + sw('enable') + '); type ' + sw('water') + ' and ' + sw('ledger 5 edit') + '. Then ' + sw('water layer off') + ', ' + sw('water') + ', ' + sw('water layer auto') + '.',
     'The layer turns itself on: a ledger line <b>water layer on by default</b>, and <b>water layer on (follows the map); season spill on: a body with fewer than 3 drawable in-season species borrows the season for active water species</b>. After <code>layer off</code> the line reads <b>(set by the player)</b> and stays off through disable and enable; <code>auto</code> hands it back to the map. On a dry map the layer stays off.',
     'A body with fewer than 3 drawable species in season prints <b>water: N species borrowed the season</b>; the borrowed seasons go back at the change (3.12).',
     tags=(V71,), src=B('fixes.md §2 (autoLayer, spill, verbs, mech.v71.fix.water_auto, spill); seen in the offline verb run.'),
     rul='The lead\'s water ruling under R45, confirmed by the user: the water layer auto-on, with the season spill.'),
   S('2.13', 'Column depth reads every level',
     'Type ' + sw('water depth') + ' (and ' + sw('water depth full') + ').',
     '<b>column depth = stacked water tiles (each at tile water level &gt;= 4/7); every 2nd x and y sampled</b>, then per body the columns by depth 1/2/3/4/5+, the maximum and the count at or past 3; the scan line (levels, ms, rows). A deep sea shows columns at 3 and 4; <code>full</code> gives about four times the stride-2 counts.',
     'A sea that reads every column as 1 deep: that was the v7.0 bug.',
     tags=(V71,), src=B('water.md (C §8.1 survey fix, R22; mech.v71.water.survey.*).'),
     rul='R22: column depth (stacked tiles) and tile water level (1-7) are different; keep them apart.'),
   S('2.14', 'Three to five water groups per body',
     'With the water layer on, play several days and read ' + sw('water') + ' and the Overview.',
     'One row per body: groups / cap, units and groups swimming, sources (drawn, DF wave, placed, seeded, other, untracked), H/C/A units, apex groups, species drawable, next draw, last reason. By design a body with something to draw reaches 3 groups in about 7,000 ticks and holds 3-5 on a 3x3 or larger embark; an empty draw backs off 1 day, not 5.',
     'Seasons and stock can still bind on small lakes; the row\'s “drawable” and “last reason” say so.',
     tags=(V71,), src=B('water.md R45 analysis and status rows; groups.md R45.'),
     rul='R45: a fort map must actually reach 3-5 concurrent aquatic groups on its own.'),
  ]), (WEB, [
   S('2.15', 'Groups tab',
     'Open <b>Groups</b> in the companion.',
     'One card per layer key with cap pips, target, W, next release, and each group (tile, count, panic, origin). The Status tab\'s layer cards read the per-layer caps.',
     '', tags=(V71,), src=B('web.md §3 (Groups, Status); §2 limits fixed for R7.')),
  ])])

# ===================================================================================================== 3
phase(3, 'Seasonal changes in food webs',
  'The tool deals the seasons: each active species arrives in its season, and the predator–prey pairs, vermin edges, the bears\' run and the apex presence move with them.',
  [(GUI, [
   S('3.1', 'The season deal on the Roster',
     'On the Roster, press <kbd>Enter</kbd> on an active species (inactive), <kbd>Enter</kbd> again, then ' + k('E') + ' a few times, then a season key on a one-season species.',
     'Inactive: act <b>-</b>, WHY <b>you</b>. Active again with <b>exactly one</b> season from its climate. ' + k('E') + ' steps singles and pairs, never none. Removing the last season is refused: <b>the last season stays: make the species inactive instead</b>.',
     'Remember the inactive species for 3.8.',
     src=B('Alpha Three 2.3-2.6 (unchanged code paths); R29.'),
     rul='R29: the season gate is the TOOL\'s deal, not the raw NO_&lt;season&gt;.'),
   S('3.2', 'Seasons tab and Food web by season',
     'Click <b>Seasons</b>; then <b>Food web</b>, ' + k('G') + ' to <b>By season</b>, and ' + k('N') + ' through the seasons.',
     'Seasons: <b>+</b> arrives, <b>-</b> leaves after, <b>X</b> stays, <b>.</b> absent. Food web by season: four columns; pairs appear and vanish as their species come into season. Animal people sit where their root sits.',
     'A pair shown in a season when one of its species is out of season.',
     src=B('Alpha Three 9.1, 10.1-10.4; addendum 95.')),
   S('3.3', 'Rotation and apply',
     'Press ' + k('Ctrl', 'D') + ' (dry run), ' + k('Ctrl', 'A') + ' (apply now), ' + k('Ctrl', 'E') + ' twice.',
     'The dry-run season table; <b>&lt;Season&gt; wildlife applied (N active).</b>; the header reads rotation off, then ON.',
     '', src=B('Alpha Three 6.1, 6.2, 6.4; GUI HotkeyLabels.')),
  ]), (CON, [
   S('3.4', 'seasons and roster at the console',
     'Type ' + sw('seasons BADGER SpAu') + ', ' + sw('seasons BADGER none') + ', ' + sw('seasons BADGER Xy') + ', ' + sw('undo') + '.',
     '<b>BADGER active, seasons SpAu [guild: …]</b>. <code>none</code> refused: <b>seasons: an active species keeps at least one season; to keep BADGER away: seasonal-wildlife roster BADGER inactive</b>. A bad code prints the usage. <code>undo</code>: <b>undid: seasons (N more to undo)</b>.',
     'No “NO_SPRING in its raws” note: seasons_own is on.',
     src=B('Alpha Three 16.4, 16.6; dispatcher (seasons); groups.md R29 (seasons_own forced on).')),
   S('3.5', 'Spaced raw ids by #N, underscore or quotes',
     'Pick a species whose raw id has a space (HONEY BADGER, RIVER OTTER) and type ' + sw('roster HONEY_BADGER') + ', ' + sw('odds HONEY_BADGER') + ', ' + c('seasonal-wildlife odds "HONEY BADGER"') + '. Find its index with the window or the web and try ' + sw('odds #N') + '.',
     'All three name the same species and print the same <code>odds …</code> line. <code>water:#N</code> and <code>cavern:#N</code> work too. An id that matches nothing passes through unchanged and prints the usage.',
     'Needs a world loaded: before one, arguments pass through.',
     tags=(RC('16.3'), V71), src=B('fixes.md §3 (spaced-raw-ids-cli; id forms; mech.v71.fix.ids).')),
   S('3.6', 'seasons on an inactive species',
     'Make a species inactive (' + sw('roster KEY inactive') + '), then type ' + sw('seasons KEY Wi') + '.',
     'It becomes active, in Winter only, one ledger line and one undo step.',
     'Never tested on any build.',
     tags=(RC('16.5'),), src=B('dispatcher (seasons: an inactive species given seasons becomes active); help header.')),
   S('3.7', 'Vermin edges and families by season',
     'Type ' + sw('vermin') + ', ' + sw('vermin edges') + ', ' + sw('roster gobble land') + '.',
     '<code>vermin</code>: one row per family with its seasons (land insects spring-autumn by default; cold embarks summer-autumn). <code>edges</code>: <b>who eats which vermin -- source in force: both</b>, the five GOBBLE_RULES and the edge table. <code>roster gobble land</code>: <b>gobble-edge LAYER CONSUMER -&gt; VERMIN VCLASS kind=…</b> lines for the active roster. As the season turns, the active consumers change and so do the edges in force.',
     'A consumer out of season still listed as in force.',
     tags=(V71,), src=B('vermin.md (verbs, R51); roster.md (roster gobble); seen in the offline verb run.')),
   S('3.8', 'A season boundary',
     'Play through a boundary. Watch for the inactive species from 3.1, then read the announcements and ' + sw('ledger 20 season') + '.',
     'The inactive species never arrives on any layer. An announcement <b>&lt;Season&gt; wildlife roster applied.</b> and a season line; exhaustion replacements end; borrowed water seasons are given back.',
     'Any inactive or out-of-season arrival: species, layer, date.',
     src=B('Alpha Three 22.1-22.2; fixes.md §2 (spillRoll at the change).')),
   S('3.9', 'The bears\' run season',
     'Type ' + sw('hunters') + ' and read the fishers line; then ' + sw('hunters fish run SpSu') + ' and back with ' + sw('hunters fish run SuAu') + '.',
     '<b>fishers: on [BEAR_BLACK BEAR_GRIZZLY BEAR_POLAR BEAR_SLOTH BLIND_CAVE_BEAR GIANT_…]; run SuAu (now) …</b> in Summer and Autumn: the fish cooldown is halved and one more fish is lured per action. Changing the run is one ledger line.',
     'With the rotation off the setter prints <b>hunters: rotation is off, so no raw is written</b>; the value is still stored.',
     tags=(V71,), src=B('ecology.md R33 (the run), verbs; seen in the offline verb run.'),
     rul='R33: bears hunting salmon; polar bears swim. R43: don\'t turn fishing off for bears, fix them.'),
   S('3.10', 'Apex presence per season',
     'Through one season with a land apex built, read ' + sw('roster apex status') + ' and the Panel\'s Roster &amp; apexes readout now and then.',
     'Presence climbs toward the target (land 25 %, water 20 %, cavern 70 %, flying 0 %); once a layer has reached its target for the season (after 7 days of watching) nothing more is placed until the next season.',
     'Natives count toward the cavern presence, so caverns may place little.',
     tags=(V71,), src=B('roster.md decision 3 (scheduler maths) and 4.'),
     rul='R9: apex on land 20-30 % of the season.'),
   S('3.11', 'Exhaustion fills a niche for the season',
     'Pick an active species in season, ' + sw('stock KEY 0') + ', then ' + sw('exhaust now') + '.',
     '<b>exhaust: 1 replacement(s) made</b> and a ledger line naming who fills the niche for the rest of the season.',
     'A replacement across habitats (Alpha Three saw an osprey replaced by a dingo).',
     src=B('Alpha Three 18.2; dispatcher (exhaust).')),
   S('3.12', 'The spill gives the season back',
     'On a thin lake or river body, after 2.12 borrowed seasons, cross a season boundary and type ' + sw('water') + '.',
     'The spill line reads <b>(nothing borrowed)</b> after the change; every borrowed species is back on its own seasons; none left seasonless.',
     '', tags=(V71,), src=B('fixes.md §2 (spillRoll at the season change, disable, spill off).')),
  ]), (WEB, [
   S('3.13', 'Seasons from the page',
     'In the companion, open <b>Species</b>; change one species\' seasons with its season buttons; then reopen the window\'s Roster.',
     'The page sends one <code>seasons KEY …</code> verb; the Roster and the Ledger show it (WHY “you”); an attempt to clear the last season is refused with the console\'s message.',
     '', src=B('web.md §3 (Species); Alpha Three 17.3.')),
  ])])

# ===================================================================================================== 4
phase(4, 'Ecological realism',
  'Pyramid shares, hunters with real skills, packs that count as packs, raptors that stoop, bears that fish, scavengers that take their time, vermin that get eaten, thieves that stay, and predators drawn by their prey.',
  [(GUI, [
   S('4.1', 'Pyramid against target',
     'On the Panel\'s Roster &amp; apexes, read the <code>pyramid</code> lines.',
     'One line per part: <b>pyramid land H/C/A%, target 73/20/7, N species</b>; flying 80/20/0, ocean 82/13/5, lake 87/13/3, cavern 60/27/13. The share is units (odds x mean group).',
     '', tags=(V71,), src=B('ui.md §2; roster.md config (pyramid defaults).'),
     rul='R9: pyramid targets accepted as the first default. R59: the ladder targets units.'),
   S('4.2', 'Panel: Ecology, hunters',
     'Press ' + k('S') + ' to <b>Ecology, hunters</b>. Select <b>Stoop chance</b> and press ' + k('→') + '; then ' + k('D') + '.',
     'Readouts: the ecology line, then a skill table <code>hunter profile SNEAK castes on map skill now</code> (10 rows; the rest in <code>hunters readback</code>). Controls: Ecology cadence <b>3000 t</b>, Solitary package, the skill rows (Skill: solitary apex 15 …), Raptors armed, Stoop and its numbers, Fishers and theirs, Swimmer scavengers. → gives <b>ran: seasonal-wildlife hunters stoop chance 61</b> and <b>Stoop chance: 61% (read back)</b>; the row gets a <b>*</b>. D puts 60 % back.',
     '', tags=(V71,), src=B('ui.md §2 (Ecology readout), validator claim gui.panel.set; ecology.md (Panel controls).')),
   S('4.3', 'Panel: Scavenging, Water, Vermin eating',
     'Press ' + k('S') + ' through <b>Water</b>, <b>Scavenging</b> and <b>Vermin eating</b>.',
     'Water: the layer/spill line, per body groups vs cap and H/C/A vs the body\'s pyramid; groups DRAWS, MIX (R62), PULL (R14), STRANDING GUARD. Scavenging: <b>scavenging off (natural cadence); curious thieves stay after a theft</b> and a per-scavenger table; groups SCAVENGING, DISCOVERY, FEEDING, MOVEMENT BUDGET, CURIOUS BEASTS. Vermin eating: gobble, forage and hunting lines; WIRING, ten CLASSES, FORAGING.',
     '', tags=(V71,), src=B('ui.md §2; offline GUI harness (sections drawn).')),
  ]), (CON, [
   S('4.4', 'Hunter skill profiles and the readback',
     'With the rotation on, type ' + sw('hunters') + ' and ' + sw('hunters readback') + '.',
     '<b>hunters: skill profiles on N species (pack a, solitary b, solitary apex c); SNEAK readback castes x/y, units u/v at level …; levels solo apex 15, solo 12, pack 10 (SNEAK 5, bonus 10)</b>. The readback heads <b>skill profiles (0-20; 15 Legendary, 20 Legendary+5) …</b> and lists each packaged species: profile, SNEAK, combat, castes ok, units ok/n, souls, SNEAK range on the map.',
     'Units at level should equal units on the map: the write now sets the rust floor. “without a soul” counts units retried each pass.',
     tags=(V71,), src=B('ecology.md (R40 / R8 / R58; status lines; verbs).'),
     rul='R40: good solo predators mid to legendary. R58: assume the solitary package can work; make the natural-skill write work. R8: keep the package.'),
   S('4.5', 'Change a skill level',
     'Type ' + sw('hunters skills solo_apex 16') + ', ' + sw('hunters readback') + ', then ' + sw('hunters skills solo_apex 15') + '. For one species: ' + sw('hunters skills COUGAR 18') + ' and ' + sw('hunters skills COUGAR auto') + '.',
     'Each setter writes a ledger line and re-applies the raws (restore first), so a lowered level really lowers. The readback\'s SNEAK column follows.',
     '', tags=(V71,), src=B('ecology.md (verbs: every hunters setter saves, ledgers and re-runs V7.apply).')),
   S('4.6', 'Packs recognised',
     'Watch a wolf pack (or any armed pack species) and read the <code>packs:</code> line of ' + sw('hunters') + ' after an ecology pass (' + sw('groups ecology now') + ').',
     '<b>packs: on, radius 10; last pass T tracked, I inferred, largest L, H hunter(s) in packs</b>. Five wolves standing together, in no tracked group, still count as one pack of 5. A solitary species is never inferred into a pack.',
     'Two waves of one species that happen to stand together are merged: accepted by design.',
     tags=(V71,), src=B('ecology.md R41 (V7.H.packSizes; mech.v71.packs_inferred).'),
     rul='R41: the lack of effect was a handling failure; retry.'),
   S('4.7', 'Prey mass: the pack floor',
     'Find a lone hunter and a pack of the same species near large prey (one wolf, a wolf pack, an elephant or buffalo herd). Run ' + sw('groups ecology now') + ' and read the Food web graph or the ecology line.',
     'The relation is written only when the hunting group weighs at least 5 % of the prey (<code>pack_floor</code>): seven wolves are 0.056 of an elephant and pass, one wolf fails. At a share of 25 % (<code>pack_sneak</code>) the hunters get the SNEAK bonus 10.',
     'The window shows pairs, not shares; mark Skipped if your map has no such pair.',
     tags=(V71,), src=B('ecology.md R40 (pack_sneak, the floor) and R41 (the floor).'),
     rul='R3: prey mass makes fights longer; presumably more predator death and injury. Confirm or invalidate.'),
   S('4.8', 'Raptors armed, and the stoop',
     'With a raptor (eagle, falcon, owl) and small land prey (rabbit, hare, groundhog) on the map, read the <code>raptors:</code> line of ' + sw('hunters') + ' after a few ecology passes.',
     '<b>raptors: armed (BENIGN cleared on RP species); stoop on (cooldown 2400 t, range 40, max 3/pass, chance 60%, prey &lt;= 2x own mass); last pass R raptor(s), S stooped; total N</b>. A stooping raptor appears on the ground 1-2 tiles from its prey, at most once per 2 days. An eagle is never related to a deer. Vultures never stoop.',
     'The stoop rides the ecology pass (every 3,000 ticks), so it is rare.',
     tags=(V71,), src=B('ecology.md R47 (arming, size cap, stoop, rate limits).'),
     rul='R47: raptor-on-land edges: make them REAL and make them actually occur.'),
   S('4.9', 'Bears fish; polar bears swim',
     'On a river or lake fort with a bear, type ' + sw('curious BEAR_GRIZZLY resident') + ' first (bears are curious beasts and leave after a theft). Watch the bear, and read the fishers line of ' + sw('hunters') + '.',
     'The bear walks to a shore tile beside water <b>at its own level</b>; up to 2 fish (3 in the run) are drawn to the edge; counters for walks, paths, hops, fish lured and swims rise. A polar bear away from any shore swims to the fish. No drowning (water-breathing stays off).',
     'A bear lost in water or drowned: try ' + sw('v7 fish_breathe on') + ' and say so. Undo the resident setting after.',
     tags=(V71,), src=B('ecology.md R33 + R43 (FSH2 analysis, the lever, polar bears).'),
     rul='R33: fishing on BEAR types only; polar bears get full swimming. R43: fix the bears so fishing works.'),
   S('4.10', 'The cohesion table',
     'Type ' + sw('hunters cohesion list') + ', then ' + sw('hunters cohesion WOLF herd') + '; watch a wolf group a pass; then ' + sw('hunters cohesion WOLF auto') + '.',
     'The table for this embark: each species solitary, pack, herd, flock or school, with its source. The override reaches the group: its label becomes <b>herd</b> and its follow distance 8; <code>auto</code> restores <b>pack</b>. <code>cohesion COUGAR solitary</code> would leave a cougar group unled.',
     '', tags=(V71,), src=B('ecology.md R62 (MODEL.cohesionOf); fixes.md §1 (overrides reach leaders; mech.v71.fix.cohesion_override).'),
     rul='R62: whole-list solitary/pack/herd table with overrides: build.'),
   S('4.11', 'Pelagic pull and the stranding guard',
     'On an ocean fort with a school present, type ' + sw('water mix ocean') + ', then ' + sw('water now ocean') + ' a few times, and read ' + sw('water') + '.',
     '<code>water mix</code> is a dry run: each species <b>base x factor = weight (share %)</b> with its reasons (balance, feed, pyramid, pull). A listed apex with prey present shows <b>pull</b> of at least 1.5, and a pelagic over the size line <b>shallow floor lifted</b>. A pulled draw is seeded in the deepest water near its prey with a wet path to it; the ledger <code>arrive</code> line says so. The guard line reads <b>breathing via getBreathingState</b> on r2; a stranded swimmer is moved (ledger <code>strand</code>).',
     'Any stranding death the guard did not catch.',
     tags=(V71, R2), src=B('water.md (R14, R59, C §8.2; mix factors; guard; mech.v71.water.pull, seed, guard.recheck).'),
     rul='R14: no pelagics on OCEAN2, fix it. R62: water placement weighted by what is swimming: unpark, prioritise.'),
   S('4.12', 'Curated water apexes in the draw',
     'Type ' + sw('roster aquatic') + ', then (if you want to try) ' + sw('roster aquatic FISH_LAMPREY_SEA apex') + ', ' + sw('water mix') + ' and ' + sw('roster aquatic FISH_LAMPREY_SEA off') + '.',
     'Only listed species are apexes on the draw side: the lamprey is a mesopredator until listed. A pelagic apex is drawn into the ocean only; a bear (fisher) is never water-drawn; at most one apex group per body (<code>water mix apex 1</code>).',
     '', tags=(V71,), src=B('water.md R43, R49 (curated apexes); roster.md (roster aquatic).'),
     rul='R49: don\'t seat the sea lamprey as a lake/river apex.'),
   S('4.13', 'Scavenging at a natural cadence',
     'With wild remains on the map, type ' + sw('scavenge on') + '; watch a day or two; then ' + sw('scavenge stats') + ' and ' + sw('ledger 10 eco') + '.',
     'Remains are found after hours, not at once (about 18 h small, 10 h medium, 6 h large, plus 10 ticks per tile), and only by scavengers within 20 tiles (fliers 40, swimmers 16). They walk; a short hop only after 600 ticks without progress. Eating takes visits; a carcass goes when its mass is gone. A ledger line per remains: <b>scavenging: a KANGAROO corpse (70 kg) eaten -- WOLF 52 kg, JACKAL 18 kg; found 9 h after the tool saw it, gone after 2.1 days</b>.',
     'Anything that looks like a sweep: remains vanishing within hours of a death. ' + sw('scavenge natural off') + ' brings the v7.0 sweep back for comparison.',
     tags=(V71,), src=B('scav.md §3 (natural cadence), §5 (attribution), verbs.'),
     rul='R18: natural cadence; it must not zip scavengers around the map and zap corpses. R16: investigate why jackals, vultures and water did not eat.'),
   S('4.14', 'Scavenging status tells the truth',
     'Type ' + sw('disable') + ', ' + sw('scavenge') + ', ' + sw('scavenge now') + '; then ' + sw('enable') + '.',
     'With the tool disabled: <b>scavenging: off (the tool is disabled; the scavenging switch is on)</b>; <code>now</code> prints <b>scavenge: 0 eaten (nothing ran: …)</b> with the reason. The last-pass part shows its age in ticks and why nothing ran.',
     'Alpha Three\'s two lies: a stale “last pass”, and “on” while nothing runs.',
     tags=(RC('18.5'), V71), src=B('scav.md §10 (status lines); fixes.md §3 (scav-status-diagnostics).')),
   S('4.15', 'Carnivorous swimmers scavenge',
     'Type ' + sw('hunters swimscav list') + '. With remains in water and a shark, crocodile or pond grabber nearby, watch a day.',
     'The list includes the LP sharks, nurse, whitetip, dogfish, wobbegong and angel sharks, crocodiles, alligators, pond grabbers, sea serpents, the otters; not the sea lamprey. A swimmer takes wet remains from the water; a land scavenger takes them from the bank.',
     '', tags=(V71,), src=B('ecology.md R42 + R17 (MODEL.swimScavenger); scav.md §4.'),
     rul='R42: carnivorous swimmers count as scavengers. YES. R17: add sharks.'),
   S('4.16', 'Vermin foraging on real vermin',
     'Type ' + sw('vermin census') + ', ' + sw('vermin forage now') + ', then a day later ' + sw('vermin eats') + '.',
     '<code>census</code>: <b>vermin objects: N (N loose, N colony sites, N hidden) from world.event.vermin</b>, a class table, and the wild vermin eaters present. <code>forage now</code>: <b>vermin forage: N eater(s) drawn now</b>. <code>eats</code>: per eater&gt;vermin pair, drawn, arrived, eaten, missed, gone; and the loose amount per class over the last passes. Eaters walk, never jump.',
     '<b>NO VERMIN VECTOR</b> in census means the read failed, not an empty map. Pet cats eat placed vermin.',
     tags=(V71,), src=B('vermin.md (R21; verbs; design 7, 5); seen in the offline verb run.'),
     rul='R21: colony counts are fake; build a better predator-prey system for vermin eaters. R27: GOBBLE_RULES are the fix.'),
   S('4.17', 'Ten vermin classes',
     'Type ' + sw('vermin classes') + ', ' + sw('vermin class SWV_BAT off') + ', ' + sw('vermin class SWV_BAT on') + ', ' + sw('vermin edges rules') + ', ' + sw('vermin edges both') + '.',
     'Ten classes, <b>SWV_COLONY</b> and <b>SWV_BAT</b> new. A class off is untagged and uneaten at once (the raws are re-applied); the source switch prints the rules and the edge table it now uses.',
     '', tags=(V71,), src=B('vermin.md (SWV taxonomy, verbs); seen in the offline verb run.'),
     rul='R51: port the builder\'s GOBBLE_VERMIN edge table. YES. R20: a larger suite of representative vermin.'),
   S('4.18', 'Curious thieves steal once, then stay',
     'With a curious beast near the fort (raccoon, grizzly), type ' + sw('curious status') + '. Let it steal; then read ' + sw('curious status') + ' and ' + sw('ledger 10') + '.',
     'After its theft DF zeroes its countdown; the tool clears that one animal\'s curious habit, gives it a 20,000-30,000-tick stay and drops its loot where it stands; a ledger line names the item. The status counts stole, reformed, re-zeroed, dropped. New arrivals of the species still come to steal.',
     ' ' + sw('curious loot keep') + ' leaves the item carried; ' + sw('curious reform off') + ' puts the habit and the exit back.',
     tags=(V71,), src=B('scav.md §6 (R30), §10.'),
     rul='R30: let them steal first; then clear THAT individual\'s CURIOUS tag and reset its counter, so thieves stay in the ecosystem longer.'),
  ]), (WEB, [
   S('4.19', 'Ecology controls from the page',
     'In the companion, open <b>Controls</b> &gt; <b>Ecology and hunters</b>; move <b>Stoop chance</b> to 61.',
     'A toast <b>Stoop chance: 61%</b>; the row shows the verb it ran and a reset button; the section nav shows a changed dot; the console\'s raptors line reads chance 61%. Reset puts 60 back.',
     '', tags=(V71,), src=B('web.md §3 (Controls), validator claim web.set.')),
  ])])

# ===================================================================================================== 5
phase(5, 'Cavern mechanics',
  'The tool gates each cavern at five groups, counts its natives, treats the civ races as their own set, and stirs an irruption when the fort works there. The deep below the caverns is never touched.',
  [(GUI, [
   S('5.1', 'Layers: each cavern\'s phase',
     'Click <b>Layers</b>; press ' + k('I') + ' to turn irruptions on; read the Caverns block; press ' + k('I') + ' again.',
     'Rows <b>irruptions</b> (<b>on, at 1.00</b>) and <b>cavern pressure</b> (three numbers). Per cavern: <b>Cavern N found managed N group(s) on the map pressure P quiet</b>, <b>STIRRING (irrupts in x d)</b>, <b>IRRUPTING TOKEN wave k/n</b> or <b>cooldown x d</b>; <b>not yet found</b> before your dwarves reach it. I off undoes every irruption write at once.',
     'Any “AGITATED: TOKEN xN” suffix: that was v7.0\'s readout.',
     tags=(V71,), src=B('ui.md §3 (Layers cavern rows read IRRUPT.phaseText; I runs irruption on|off, off = IRRUPT.restoreAll); fixes.md §6.')),
   S('5.2', 'Panel: Cavern gate',
     'Press ' + k('Alt', 'P') + ', ' + k('S') + ' to <b>Cavern gate</b>.',
     '<b>cavern gate (R44): on cap 5 per cavern hold any (N species at frequency 1) trim on (N animal(s) on their way) natives counted</b>. Controls: Cavern gate, Cavern cap 5, Frequency hold &lt;any&gt;, Hold shared species too, Trim over the cap, Trim every 1 days, Count cavern natives, Count surface natives, Lead seeded schools, Animal-people cap 5; action Adopt natives now.',
     '', tags=(V71,), src=B('groups.md R44, R35 (Panel values); offline GUI harness.'),
     rul='R44: the tool gates cavern layers; a universally fixed max of 5 concurrent groups.'),
   S('5.3', 'Panel: Irruptions',
     'Press ' + k('S') + ' to <b>Irruptions</b>. Select <b>Token: Thief share</b> and press ' + k('→') + ' five times; then <kbd>Enter</kbd> on the action <b>Stir</b> and pick cavern 1.',
     'A header <b>Irruptions ON threshold 1.00 at most 3 cavern(s) at once 3 wave(s) of up to 20</b>; per cavern <b>Cavern N found pressure 0.42 of 1.00 [####------]</b> with its phase and this pass\'s sources (citizens, near, dig, scarcity, season x, fort x, gain); while an event runs, waves, placed, alive, dead, left, agitated and tokens on living units with the champion; <b>So far: …</b>. Then 103 controls: TRIGGER, EVENT, END AND COOLDOWN, BEHAVIOUR TOKENS (R10), AGITATION (R5), MESSAGES (R6). The share reads <b>15%</b> (read back). Stir asks for a cavern and forces a warning there.',
     'Set the share back to 10 (' + k('D') + ').',
     tags=(V71,), src=B('ui.md §2 (Irruptions readout); irruption.md §9 (controls); offline GUI harness (sample event drawn).'),
     rul='R5: the UI must expose the irruption tokens as toggles or sliders so players adjust difficulty.'),
  ]), (CON, [
   S('5.4', 'The cavern gate at the console',
     'Type ' + sw('groups cavern') + ', ' + sw('groups cavern max 4') + ', ' + sw('groups cavern') + ', ' + sw('limits cavern groups 5') + '.',
     '<b>groups: cavern gate on, cap 5 groups per cavern (R44); hold any; trim on every 1 day(s); natives counted</b>. <code>max 4</code> is an alias of <code>cap</code> and sticks: <b>cap 4</b> (and survives a reload). <code>limits cavern groups 5</code> sets the cavern cap back.',
     'Alpha Three: <code>groups cavern max</code> was dead, overwritten at the next load.',
     tags=(RC('cavern max'), V71), src=B('fixes.md §3 (groups cavern max reconciled; mech.v71.fix.cavern_max); groups.md verbs; seen in the offline verb run.')),
   S('5.5', 'Natives counted, held and trimmed',
     'With a cavern open and busy, read ' + sw('groups layers') + ' (the <code>cavern:&lt;d&gt;</code> rows) and ' + sw('groups natives') + ' over a few days.',
     'Unflagged cavern animals become <b>native</b> groups within 1,200 ticks and count. At the cap, the cavern\'s natural species are held at frequency 1 (never 0); over the cap, the oldest native group is sent off once a day (countdown 10, “on their way”). Below the cap the frequencies come back.',
     'Whether DF walks a trimmed native off when its countdown ends is unmeasured.',
     tags=(V71,), src=B('groups.md R44 (count, release, hold, trim; mech.v71.cavern.*), open risks.')),
   S('5.6', 'Civ races and the civ set',
     'With a civ race on your cavern roster, type ' + sw('roster cavern:TROGLODYTE') + ' (or ANT_MAN, RODENT_MAN, PLUMP_HELMET_MAN).',
     'A managed cavern species with its guild. The civ set now holds ANT_MAN and the vermin-root cave persons (BAT_MAN, CAVE_FISH_MAN, CAVE_SWALLOW_MAN, OLM_MAN). Civ races hunt by their guild and are prey of cavern apexes only: in v7.0 both rules were dead (the pool never carried <code>civ</code>); now they act.',
     'This is new behaviour on the rig: civ races may fight more.',
     tags=(V71,), src=B('roster.md R61, “Bug found on the way”; fixes.md §4.'),
     rul='R61: ANT_MAN and cavern VERMIN_MAN creatures belong to the civ set.'),
   S('5.7', 'Irruptions on, and the breach',
     'Type ' + sw('irruption on') + '. Then send dwarves to dig into a cavern and read ' + sw('irruption') + ' and ' + sw('ledger 10 irruption') + '.',
     'The full readout: purpose, trigger, phases, end, species, tokens, levers, agitation, messages, one row per cavern. Before the fort reaches a cavern its row reads <b>quiet (not reached by the fort: no event)</b>. The first time the fort reaches one, a breach pulse (+0.5) is added once, with a ledger line.',
     'With the cavern roster layer off it says so: irruptions run on their own switch.',
     tags=(V71,), src=B('irruption.md §4 (reached, breach), §8; seen in the offline verb run.'),
     rul='R4: irruption livens up cavern ecology in place of the disabled invasions. R6: what drives it, what ends it, what tells the player.'),
   S('5.8', 'Pressure and the warning',
     'Keep about three dwarves working in the cavern (mining, felling). Read the cavern\'s row of ' + sw('irruption') + ' each day.',
     'Pressure rises from citizens in the band, citizens just above it, dig jobs, the season and a weak fort factor (about +0.09 a pass with 3 citizens in winter: the threshold in about 3 days). At the threshold: a yellow announcement <b>Something stirs in the first cavern...</b> and the row reads <b>STIRRING (irrupts in x d)</b> for 1-3 days. If pressure falls below 60 % it lapses: <b>The stirring in the first cavern has quieted.</b>',
     'A cavern with nothing to send logs that once and never warns.',
     tags=(V71,), src=B('irruption.md §4 (formula, numbers at the defaults, phases), §5.4 (messages).')),
   S('5.9', 'Waves of its own civ races',
     'Let the warning run out, or type ' + sw('irruption now 1') + ' (add a token, e.g. ' + sw('irruption now 1 TROGLODYTE') + ').',
     'A light-red announcement <b>The first cavern is irrupting! Troglodytes surge out of the dark.</b> and the game pauses (pause.start is on). Three waves, 1-3 days apart, each clamp(cluster max x 2, 4, 20) units placed from the cavern\'s own entries at the map edge farthest from your access: <b>A wave of 12 troglodytes surges through the first cavern.</b> Each wave is one led group (IRR on Live), outside the cavern cap. With no civ race there, the cavern\'s predators come instead.',
     'If nothing can be sent: <b>cavern 1: nothing to send: …</b> with the reason. Offline, a <code>now</code> that sent nothing moved a pinned pressure from 1.00 to 0.50: see whether a pin holds in game.',
     tags=(V71,), src=B('irruption.md §5 (species, waves, entry, group), §5.4; seen in the offline verb run.'),
     rul='R10: tribal cavern dwellers carry the tokens; R6: announcements.'),
   S('5.10', 'Tokens on 10 %, and one unit with all',
     'During an event type ' + sw('irruption tokens') + ' and ' + sw('irruption') + '; watch a wave.',
     '<code>tokens</code>: crazed, rage, thief, sneak, wander, meander, linger, mischief, nofear, ambush <b>on 10%</b>, trance <b>off</b>, and <b>champion … on</b>. The cavern row counts <b>tokens on living units: crazed 1, rage 2, …; champion 1</b>: each token on at least one unit, about 10 % of the wave, and <b>exactly one</b> unit per wave carrying all of them. Raws are never left changed: each caste write lives only across one unit\'s making.',
     '', tags=(V71,), src=B('irruption.md §5.1 (tokens, champion, caste window; mech.v71.irr.tokens, caste); seen in the offline verb run.'),
     rul='R10: each token on about 10 % (minimum 1) of the wave; exactly ONE individual per wave with ALL tags.'),
   S('5.11', 'The cavern\'s animals agitated',
     'During an event, watch the cavern\'s animals (not the civ dwellers) and read the cavern row\'s <b>agitated</b> count.',
     'Up to 30 of the cavern\'s non-civ natural animals are agitated and attack what they meet. Never a civ dweller, citizen, tame animal, forgotten beast or other non-natural unit, another cavern or the deep. The flags go back at the end.',
     'Agitated animals are lethal (E29: 7 citizens to 4 in one run). Use the copy.',
     tags=(V71,), src=B('irruption.md §5.2 (agitation, fb_safe), §14 (lethality).'),
     rul='R5: irruption events add AGITATED to the NON-civ creatures of the cavern; layer-specific. R10: agitate the ANIMALS.'),
   S('5.12', 'The end and the cooldown',
     'Let an event end on its own, or kill half the wave, or type ' + sw('irruption end all') + '; then ' + sw('irruption cool all') + '.',
     'It ends at 10 days, when the fort kills half the units placed (repelled), when every wave is gone, or 3 days after the last wave. A light-green announcement <b>The irruption in the first cavern has run its course.</b> (repelled: <b>The fortress has driven the troglodytes back into the depths of the first cavern.</b>). Survivors leave within 1-3 days; every write is undone; pressure 0; 30 days of cooldown, then <b>The first cavern has settled.</b> <code>cool all</code> clears the cooldown.',
     ' ' + sw('irruption off') + ', ' + sw('disable') + ', All off and ' + sw('groups off') + ' end it with no cooldown and no announcement.',
     tags=(V71,), src=B('irruption.md §5.3, §5.4, §10 (restore paths).'),
     rul='R5: an in-game end-state condition or a cooldown.'),
   S('5.13', 'Difficulty: shares, waves, messages',
     'Type ' + sw('irruption token thief 25') + ', ' + sw('irruption token all off') + ', ' + sw('irruption champion off') + ', ' + sw('irruption waves 2') + ', ' + sw('irruption msg wave off') + ', ' + sw('irruption keys') + '; then set them back.',
     'Each prints the readout with the new value (<b>thief 25%</b>, all tokens off, champion off, waves 2, wave messages off); <code>keys</code> lists every key with its value and range (e.g. <b>tokens.thief.pct 25 0..100</b>). Every change is a ledger line.',
     '', tags=(V71,), src=B('irruption.md §6, §7 (verbs); seen in the offline verb run.')),
   S('5.14', 'The animal-people cap and its lift',
     'With plump helmet men (or another cavern animal person) on the roster, type ' + sw('groups apcap') + '; watch their waves; then trigger an irruption in their cavern (5.9).',
     '<b>animal-people cap: 5 a group; N species capped now</b>. Their groups arrive at most 5 strong (S8B saw about 15 a wave). While an irruption runs on their cavern the cap is lifted there and DF\'s own draws come at full size; after the end it is capped again.',
     '', tags=(V71,), src=B('groups.md R35; irruption.md §5 (R35); mech.v71.apcap, irr.r35.'),
     rul='R35: a group-size cap for animal people in caverns: YES, lifted during an irruption event.'),
   S('5.15', 'Depth and lava guards',
     'Type ' + sw('roster depth') + '; then ' + sw('place MAGMA_CRAB 1 deep') + '.',
     '<code>depth-layer cavern=N cave=ID stocked=N eligible_unstocked=N</code> lines, then the two lists. The MAGMA_CRAB placement is refused with the R28 message and makes no unit. A lava-only species is never seated in a cavern roster; a cavern species must be inside its raw UNDERGROUND_DEPTH.',
     '<code>place</code> is a test tool: run it only on the copy.',
     tags=(V71,), src=B('roster.md R28 (depthOk, PLACE.fromEntry guards; mech.v71.place.deep).'),
     rul='R28: is the tool breaking anything (fiery types in a cavern layer)? Why is MAGMA_CRAB in layer 5?'),
   S('5.16', 'Demons and the deep untouched',
     'Type ' + sw('status') + ' and ' + sw('groups layers') + ' on a fort with something in the magma sea or underworld.',
     '<b>On the map now: land N water N cavern N (+N in the magma sea and underworld, never managed)</b>. No <code>deep</code> key in the group rows; nothing below cavern 3 is counted, held, agitated, trimmed or placed.',
     '', tags=(V71,), src=B('groups.md R44/R60; irruption.md §5.2; mech.v71.cavern.deep, irr.fbsafe.'),
     rul='R60: demons on deep layers: no limit, no management; the tool has NO impact on them.'),
  ]), (WEB, [
   S('5.17', 'Irruption controls from the page',
     'In the companion, open <b>Controls</b> &gt; <b>Cavern irruptions</b>. Move a token share; run <b>Stir</b> for cavern 1.',
     'Live status lines for the section (refreshed every five seconds); 103 rows grouped as on the Panel; actions Start now (asks; cavern and species), Stir, End every event (asks), Clear every cooldown, Unpin, each with its choice list. A toast with the console\'s first line.',
     '', tags=(V71,), src=B('web.md §4 (IRRUPT v2 rows, actions, readouts), §3 (Controls).')),
  ])])

# ===================================================================================================== 6
VERBS = """<div class="tablewrap"><table class="cmdref"><thead><tr><th>Verb (after <code>seasonal-wildlife</code>)</th><th>What it does; v7.1 in bold</th><th>Step</th></tr></thead><tbody>
<tr><td>status · now · enable · disable · preset · undo</td><td>the whole state (<b>hunters, scavenging, curious, roster v7.1, extinct, perf, irruptions lines</b>); apply once; rotation; the biome preset; undo the last edit</td><td>[[6.12]]</td></tr>
<tr><td>layer &lt;land|water|cavern|deep&gt; on|off</td><td>a layer; <b>water sets “set by the player”</b></td><td>[[2.12]]</td></tr>
<tr><td>limits [formula | fixed N | LAYER [groups N|auto] [ceiling N]]</td><td><b>one cap per layer by map size, or one fixed cap (R7)</b>; <code>quota</code> is the retired alias</td><td>[[2.7]]</td></tr>
<tr><td>groups [on|off|layers|adopt IDS|clock …|cavern …|panic …|natives …|apcap N|coupling …|pack N|cohesion …|ecology [on|off|now|cadence N]|livestock …|nudge …|hold TOKEN DAYS|dismiss TOKEN]</td><td>groups; <b>layers, clock, cavern, panic, natives, apcap, adopt, ecology cadence</b></td><td>[[2.8]]-[[2.10]], [[5.4]], [[5.5]], [[5.14]]</td></tr>
<tr><td>water [on|off|now [BODY]|survey|depth [full]|mix …|pull …|guard …|layer auto|on|off|spill [on|off] [min N]|levels N|aquatic on|off|budget MS|retry D|countdown N|status]</td><td>the water draws; <b>per-body draw, depth, mix, pull, guard, layer, spill</b></td><td>[[2.11]]-[[2.14]], [[4.11]]</td></tr>
<tr><td>caverns [survey] · cavern</td><td>cavern bands; <code>cavern</code> prints its retirement (now pointing at <code>groups cavern cap N</code>)</td><td>[[6.15]]</td></tr>
<tr><td>place TOKEN [n] [LAYER [depth]]</td><td>headless placement, <b>one clustered led group; deep refused</b> (a test tool)</td><td>[[5.15]]</td></tr>
<tr><td>stock|odds|size KEY [N|clear] · call KEY · sendoff [land|cavern]</td><td>one species' stock, odds, group size; a wave; send off gated groups</td><td>[[3.11]]</td></tr>
<tr><td>roster [KEY [active|inactive]|build [LAYER]|outgun [LAYER]|apex …|gobble [LAYER]|depth …|aquatic …|set …] · seasons KEY &lt;SpSuAuWi|all&gt;</td><td>the roster; <b>flying layer, apex scheduler, gobble edges, depth, curated water apexes, knobs</b></td><td>[[1.6]]-[[1.13]], [[3.4]]</td></tr>
<tr><td>pattern [LAYER] NAME · ledger [N] [kind] [layer] | clear · classes · class TOKEN natural|auto</td><td>arrival pattern; the ledger; ecology classes</td><td>[[6.13]]</td></tr>
<tr><td>vermin [classes|class SWV_X on|off|edges …|census|eats|forage …|defaults|&lt;family&gt; …]</td><td>vermin; <b>class switches, edges, census, eats, forage</b></td><td>[[3.7]], [[4.16]], [[4.17]]</td></tr>
<tr><td>scavenge [on|off|now|radius N|natural|swimmers|defer on|off|set KEY N|keys|stats [reset]]</td><td>scavenging; <b>natural cadence, swimmers, every timing, who ate what</b></td><td>[[4.13]]-[[4.15]]</td></tr>
<tr><td>curious [TOKEN resident|thief | reform [on|off|now] | loot drop|keep | set KEY N | status]</td><td>curious beasts; <b>reform</b></td><td>[[4.18]]</td></tr>
<tr><td>exhaust [on|off|now] · alerts [on|off] · hunting [on|off] · sponges [now]</td><td>v6.9-v7.0 jobs, unchanged</td><td>[[3.11]]</td></tr>
<tr><td>hunters [status|readback|skills …|pack|packradius|raptors|stoop …|fish …|swimscav …|cohesion …]</td><td><b>skill profiles, packs, raptors, fishing, swimmer scavengers, cohesion</b></td><td>[[4.4]]-[[4.10]], [[4.15]]</td></tr>
<tr><td>v7 [KEY on|off|N | fisher TOKEN on|off | apply]</td><td>the v7 switches; <b><code>layer_groups</code> retired</b></td><td>[[6.15]]</td></tr>
<tr><td>extinct [status|list|on|off|TOKEN [on|off]|set KEY on|off|mods]</td><td><b>extinct corrections (R24)</b></td><td>[[1.11]]</td></tr>
<tr><td>realm &lt;name|auto|off|table&gt;</td><td>the embark's realm; <b><code>table</code></b></td><td>[[1.12]]</td></tr>
<tr><td>irruption [status|on|off|keys|set KEY VALUE|tokens|token ID on|off|PCT|now|stir|end|cool CAVERN …|pin|unpin|…]</td><td><b>IRRUPT v2</b></td><td>[[5.7]]-[[5.13]]</td></tr>
<tr><td>perf [status|reset|keys|set KEY VALUE|legacy NAME on|off|bench [N]|census|build [LAYER]]</td><td><b>job cost, worst tick, perf counters, switches</b></td><td>[[6.11]]</td></tr>
</tbody></table></div><p class="muted" style="margin-top:8px;max-width:72ch">Two more scripts: <code>seasonal-wildlife-controls [list [SECTION] | get ID [TOKEN] | set ID VALUE [TOKEN] | json]</code> ([[6.10]]) and <code>seasonal-wildlife-web start [port] | stop | status | snapshot</code> ([[6.16]]). Read from the v7.1 dispatcher and usage strings, not from memory.</p>"""

phase(6, 'Other: Panel, companion, console, cost',
  'How every control is reached and checked: the Panel and its registry, the browser companion, the console verbs and the registry script, the perf verb, the ledger and undo, persistence and frame cost.',
  [(GUI, [
   S('6.1', 'Open the window; the tab bar',
     'Type ' + c('gui/seasonal-wildlife') + '. If you can, narrow the DF window below 92 columns and press ' + k('Ctrl', 'T') + ' / ' + k('Ctrl', 'Y') + '.',
     'Nine tabs: Overview, Panel, Roster, Seasons, Food web, Live, Layers, Vermin, Ledger; ASCII only, nothing wider than 86 columns. Narrow, the bar scrolls (edge arrows) and still reaches Ledger; it never wraps under the pages.',
     'On r2 the launcher may hide the tool unless dev mode is on (0.3).',
     tags=(V71, R2), src=B('ui.md §1 (no tenth tab; TabBar wrap=false), §3 (Win:wrap at 86); screen-check trap 4.')),
   S('6.2', 'Panel: sections and moving between them',
     'Press ' + k('Alt', 'P') + '. Press ' + k('S') + ' through every section and ' + k('Shift', 'S') + ' back; click a section name.',
     'The help line <b>Every control, by section. Enter sets; Left/Right steps (Shift: x10); * = not default.</b>; keys <b>a: All on, x: All off, r: Refresh, s: Section, S: back, d: Default, Alt+s: Find</b>; thirteen sections: Switches &amp; jobs, Limits &amp; groups, Cavern gate, Leaders &amp; panic, Roster &amp; apexes, Ecology, hunters, Water, Scavenging, Vermin eating, Extinct, v7 switches, Irruptions, All controls. A <b>&gt;</b> marks the open one; each opens with its readouts.',
     'A blank section or one that shows an error line: read stderr.log for the script\'s name (screen-check trap 3).',
     tags=(V71,), src=B('ui.md §1 (layout, keys), validator claim gui.panel.sections; offline GUI harness (13 sections, 712 control rows, 0 fail).'),
     rul='R52: expose the v7 switches in the GUI Panel. YES.'),
   S('6.3', 'Setting: Enter, steps, default, refusals',
     'In <b>Limits &amp; groups</b>: <kbd>Enter</kbd> on <b>Adaptive release clock</b> twice; ' + k('→') + ' and ' + k('Shift', '→') + ' on <b>Fixed cap</b>; <kbd>Enter</kbd> on <b>Fixed cap</b> and type 99; ' + k('D') + '; <kbd>Enter</kbd> and ' + k('Shift', 'Enter') + ' on <b>Land pattern</b>.',
     'A switch flips ([ON]/[off]). → adds one, Shift+→ ten (clamped to the range 1-20). Enter on a number asks with the range in the prompt; 99 is refused: <b>Refused: Fixed cap: at most 20</b>. Each set shows <b>ran: seasonal-wildlife …</b> and <b>&lt;label&gt;: value (read back)</b>; a non-default row carries <b>*</b>; D puts the default back. Enter moves a choice on, Shift+Enter back. Setting Fixed cap switches the cap to fixed: set Group cap back to the formula after.',
     'A set that reports success while the value did not change: the registry should report <b>… did not change (it reads …)</b>.',
     tags=(V71,), src=B('ui.md §1 (rows, keys), §4; web.md §1 (set, validate, read-back); controls.lua set().')),
   S('6.4', 'Find a control',
     'Press ' + k('Alt', 'S') + ', type <b>stoop</b>; then ' + k('Alt', 'S') + ' with nothing to close it.',
     'A section <b>Find: stoop</b> with every control whose label, id, help, group or verb holds the words (Stoop, Stoop cooldown, Stoop range, Stoops per pass, Stoop chance, Prey size ratio …).',
     '', tags=(V71,), src=B('ui.md §1 (Find).')),
   S('6.5', 'Switches & jobs; All off and All on',
     'In <b>Switches &amp; jobs</b> read the rows; press ' + k('X') + ' and answer Yes; then ' + k('A') + '.',
     'Twenty switches and Map overlay; new: <b>Curious thieves stay</b> [ON], <b>Cavern irruptions</b> (opt-in), <b>Vermin foraging</b> [ON]; <b>Nudge [off]</b> and opt-in. JOBS: season roster 1200 t, groups and gate 300 t, <b>ecology 3000 t</b>, quiet fights 10 t, scavenging 200 t, <b>vermin foraging 100 t</b>, <b>curious thieves 50 t</b>, with last, worst, runs, over and fuse. All off asks, stops every job and reports what it put back (cavern frequencies, cluster sizes, hunting flags, v7 raws, irruption writes, reformed thieves, forage walks); All on restores the switches as they were.',
     'Any raw left written after All off: ' + sw('extinct') + ' and ' + sw('hunters') + ' should read zero writes.',
     tags=(RC('1.2'), V71), src=B('engine PANEL.SWITCHES, PANEL.jobs, PANEL.restoreAll; ui.md §1; offline GUI harness (Switches & jobs drawn).'),
     rul='R37: ecology cadence 3,000. R38: nudge off by default.'),
   S('6.6', 'Actions and readouts on the Panel',
     'In <b>Water</b>, <kbd>Enter</kbd> on the readout <b>Column depths</b>; then <kbd>Enter</kbd> on the action <b>Draw now</b> and pick <b>any</b>.',
     'A readout opens the console\'s own output in a scrolling list. An action with an argument offers its choices; one that changes a lot asks first; the result is the bottom line.',
     '', tags=(V71,), src=B('ui.md §1 (actions and readouts).')),
   S('6.7', 'Help on every tab',
     'On each tab press ' + k('Alt', 'H') + '.',
     'A page per tab; the Panel\'s explains sections, keys, read-back and All off. The vocabulary under it is unchanged from v7.0: none of exhaustion, scavenging, sweep, builder, irruption tokens, cap or release clock. The Panel\'s per-control help (the lines under the rows) covers them instead.',
     'Mark Anomaly if a word in the window is explained nowhere.',
     tags=(RC('14.3'),), src=B('GUI HELP table at fce7d68 (Words unchanged; Panel and Layers entries rewritten); ui.md merge hazards.')),
   S('6.8', 'Ledger and undo in the window',
     'Click <b>Ledger</b>; press ' + k('K') + ' through the kinds; make three Panel sets; press ' + k('Z') + ' three times.',
     'Kinds: all, edit, season, wave, arrive, coupling, ecology, hold, dismiss, sweep, place, cavern, fuse, build, undo, irruption. Each Panel set is one ledger line and one undo step; Z undoes them in reverse; the label reads <b>Undo last edit (N)</b>.',
     'v7.1 writes kinds the filter cannot pick: <code>panic</code>, <code>lead</code>, <code>adopt</code>, <code>size</code>, <code>strand</code>, <code>eco</code>, <code>extinct</code>, and roster builds as <code>roster</code> (the filter has <code>build</code>). They show under <b>all</b>; the console filters them (6.13).',
     tags=(V71,), src=B('GUI led_kind options; groups.md (new ledger kinds), water.md (strand), scav.md §5 (eco), extinct.md (extinct); offline verb run (roster kind).')),
  ]), (CON, [
   S('6.9', 'Every console verb',
     'Use the table under this phase as the map; each verb\'s own step tests it.',
     'Every verb answers with its status line, its usage on a bad argument, and one ledger line per change.',
     'A verb that raises a Lua error rather than printing its usage.',
     src=B('the v7.1 dispatcher (dispatch(), lines 15031-15943) and usage strings.')),
   S('6.10', 'The registry from the console',
     'Type ' + ctl('list water') + ', ' + ctl('get hunters.stoop.chance') + ', ' + ctl('set hunters.stoop.chance 61') + ', ' + ctl('set hunters.stoop.chance 101') + ', ' + ctl('set hunters.stoop.chance 60') + '.',
     '<code>list</code>: one line per control: id, value, type, default, range, verb. <code>get</code>: <b>60</b>. <code>set … 61</code> prints the verb it ran, <b>seasonal-wildlife hunters stoop chance 61</b>, then the game\'s reply. <code>101</code>: <b>refused: Stoop chance: at most 100</b>. A row the engine lacks shows <b>[not in this version]</b>.',
     '', tags=(V71,), src=B('web.md §1 (registry, set, console); controls.lua console block.')),
   S('6.11', 'perf: what each job costs',
     'After a few game days type ' + sw('perf') + ', ' + sw('perf keys') + ', ' + sw('perf census') + ', ' + sw('perf bench 50') + '; then ' + sw('perf set overlay_ms 2000') + ', ' + sw('perf legacy census on') + ', ' + sw('perf legacy census off') + ', ' + sw('perf set overlay_ms 1000') + '.',
     '<code>perf</code>: a table <code>job / lap runs last worst over ms/run KB last KB worst defer</code>, the worst single tick (ms, tick, which jobs), then DFHack\'s perf counters for the tool\'s repeats and overlay. <code>keys</code>: 21 keys with defaults (stagger, events, slice, forEachTile on; ten <code>legacy_*</code> off). <code>census</code>: <b>census: N wild on the map (land, water, cavern, deep), N gated; walked the wild-id set</b>. Setters echo <b>perf overlay_ms = 2000</b>, <b>perf legacy_census = true</b>.',
     'Offline, <code>perf</code> raised on the stubbed perf counters; in DF they are numbers. If it raises in game, copy the error.',
     tags=(V71,), src=B('perf.md §1-§2 (P0, verbs, keys); seen in the offline verb run.'),
     rul='R48, R55: performance v7.1 and v7.2. YES.'),
   S('6.12', 'status reads it all',
     'Type ' + sw('status') + '.',
     'After the v7.0 lines, new ones: the groups block (limits, release clock, per-key rows, cavern gate, leaders, animal-people), <b>vermin forage</b>, the five <b>hunters</b> lines, the water layer/spill line, <b>scavenging</b>, <b>curious reform</b>, <b>roster v7.1</b>, <b>extinct</b>, <b>perf</b>, <b>irruptions</b>, then the map counts and the embark subset.',
     '', tags=(V71,), src=B('cmdStatus additions in each stream\'s merge hazards; seen in the offline verb run.')),
   S('6.13', 'Ledger and undo at the console',
     'Type ' + sw('ledger 20 irruption') + ', ' + sw('ledger 20 extinct') + ', ' + sw('ledger 20 panic') + ', then make a Panel set and type ' + sw('undo') + '.',
     'Each kind filters: <b>ledger: N of M recorded shown kind=…</b>. <code>undo</code> after a Panel or web set undoes it: <b>undid: … (N more to undo)</b>.',
     '', tags=(V71,), src=B('dispatcher (ledger, undo); web.md §1 (each set an undo step).')),
   S('6.14', 'Save, quit, reload',
     'Note a fixed cap, an irruption token share, a hunters skill level, an inactive species and the ledger\'s last line. Save, go to the title, load, then type ' + sw('limits') + ', ' + sw('irruption tokens') + ', ' + sw('hunters') + ' and open the Ledger.',
     'All as you left them; undo still works (the newest 50 steps persist); reformed thieves are re-asserted after the load. Mid-irruption, the record and its writes agree after a reload.',
     'v7.1 settings across a reload are untested.',
     tags=(V71,), src=B('perf.md P2 (undo_persist 50); scav.md §6 (hold after reload); irruption.md §10 (world unload), T-SAVE.')),
   S('6.15', 'Retired words point at v7.1',
     'Type ' + sw('v7 layer_groups off') + ', ' + sw('water target 5') + ', ' + sw('cavern') + '.',
     '<b>v7 layer_groups: retired in v7.1 -- every layer always has its own limit (R7); the one toggle is `limits formula` / `limits fixed N`</b>. <code>water target</code>: <b>water: retired in v6.5 -- each water body is drawn in groups under its cap (`limits formula|fixed N`; …), on the adaptive clock (`groups clock`)</b>. <code>cavern</code>: names <code>groups cavern cap N</code>.',
     '', tags=(V71,), src=B('groups.md (v7 layer_groups retired); fixes.md §5 (retired-verb messages); seen in the offline verb run.')),
  ]), (WEB, [
   S('6.16', 'Start the companion',
     'Type ' + web('start') + '.',
     '<b>serving the companion at http://127.0.0.1:8642/?t=&lt;token&gt; (copied to the clipboard) [tiles: N creatures, N sheets, read in N ms]</b>.',
     'It needs DFHack\'s luasocket; it was written against r1.1. If it cannot listen, copy the message (<b>could not listen on 127.0.0.1:8642: …</b>). Under CrossOver, open the address in a browser on the Mac.',
     tags=(V71, R2), src=B('web.md §2, rig tests (re-check luasocket on r2); seasonal-wildlife-web.lua start().')),
   S('6.17', 'The page and its tabs',
     'Open the address.',
     'Seven tabs: <b>Status, Species, Food web, Roster, Groups, Controls, Ledger</b>; only the open tab renders. Status carries the Panel\'s switches with <b>All on</b>, <b>All off</b>, <b>Re-arm</b>. Light and dark follow the system. Deep links <code>#controls/water</code>, <code>#roster</code>, <code>#groups</code> open those tabs.',
     'A blank page or a stale date.',
     tags=(V71,), src=B('web.md §3.')),
   S('6.18', 'Controls: sections, search, defaults',
     'Open <b>Controls</b>. Click through the sections; type <b>panic</b> in the search; find a changed row and press its <b>reset</b>.',
     'The section nav shows each section\'s count and a dot with the number changed from default; the section\'s live status lines; rows by group with a widget (switch, slider and number, choice, season buttons), unit, default, a reset when changed, and the exact console verb. Search spans every control. Rows a feature lacks show <b>not in this version</b>, disabled.',
     '', tags=(V71,), src=B('web.md §3 (Controls).')),
   S('6.19', 'A set and its readback',
     'On Controls &gt; <b>Limits and release clock</b>, set <b>Fixed cap</b> to 4. Then type ' + sw('limits') + ', look at the window\'s Panel, and read the Ledger. Then try 25 in the same field; then set <b>Group cap</b> back to the map-size formula.',
     'A toast <b>Fixed cap: 4</b>; <code>limits</code> reads <b>[single fixed cap 4 on every layer]</b>; the Panel shows <b>*Fixed cap 4</b> after a refresh; one ledger line and one undo step. 25 is refused before it runs: <b>Fixed cap: at most 20</b>. The page reflects the value the game read back, not the one typed.',
     '', tags=(V71,), src=B('web.md §1 (set: validate, run the verb, read back), validator claims web.set, web.set.panel; groups.md (limits.fixed implies fixed).')),
   S('6.20', 'Token guard and the whitelist',
     'Open the address without <code>?t=…</code>. Then, with the token, try the page\'s console box with <code>preset</code> if it offers one.',
     'Without the token the data is refused; the page says the token is not the one the game gave and to run <code>seasonal-wildlife-web status</code>. <code>preset</code>, <code>gui</code>, <code>place</code>, <code>class</code> and <code>groups adopt|nudge|pack</code> are refused from the page.',
     '', src=B('web.md §2 (endpoints, whitelist), validator claim web.guard; Alpha Three 17.4.')),
   S('6.21', 'Its cost, then stop it',
     'Leave the page open five minutes, paused and unpaused; type ' + web('status') + ', then ' + web('stop') + '.',
     '<b>serving http://… requests N (commands N, sets N, refused N, errors N); poll last N ms, worst N ms; snapshot last N ms, worst N ms; status last N ms, worst N ms; static species fields N ms in all</b>. Snapshot worst under 50 ms after the first (static fields cached). Then <b>stopped</b>.',
     'A worst poll or snapshot near 20 ms shows as stutter at 50 fps.',
     tags=(V71,), src=B('web.md §2 (P12 static/dynamic), validator claim web.perf; seasonal-wildlife-web.lua status().')),
   S('6.22', 'Frame rate on and off',
     'Unpaused, read the frame rate for a minute with the tool on; then All off and read it again, in the same session. Compare with 0.8.',
     'Within the load noise. Wild animal count matters more than the tool: 500 more wild animals cost 38 %. v7.1\'s perf work (one census, staggered jobs, cached overlay) should not cost more than v7.0.',
     'Ignore the first seconds after a switch.',
     src=B('fps-load-facts; perf.md (rig tests PERF0-PERF4 still to run).'),
     rul='R46: FPS6 on hold.'),
  ])],
  post='<h3 class="sub">Every console verb, from the v7.1 dispatcher</h3>' + VERBS)

# ===================================================================================================== 7 (no steps)
CANNOT = """<div class="tablewrap"><table class="recheck wide"><thead><tr><th>What</th><th>Why a walkthrough cannot show it</th><th>The rig test the notes ask for (region8, n = 5)</th></tr></thead><tbody>
<tr><td>Skill writes act on new arrivals and do not rust</td><td>Caste skills and souls</td><td>SKL1, SKL2 (ecology.md)</td></tr>
<tr><td>Packs, stoops and fishing change kills</td><td>No attack log in the window</td><td>PK2, STP1, FSH3, FSH4 (ecology.md)</td></tr>
<tr><td>The clock holds groups near the cap</td><td>Counts over 30,000 ticks</td><td>G2r, WAT5 (groups.md, water.md)</td></tr>
<tr><td>The cavern gate holds five; natives trimmed walk off</td><td>Counts per cavern over time</td><td>CAVG (groups.md)</td></tr>
<tr><td>A lost leader makes the group scatter</td><td>Spread over time</td><td>PAN1, COHT (groups.md)</td></tr>
<tr><td>Tokens act (CRAZED sticks and acts, the caste window reaches one unit, theft, MISCHIEVOUS, hidden, waypoints)</td><td>Unit internals</td><td>M1-M9 first, then the three-arm main experiment and T-PR, T-END, T-OFF, T-SAVE, T-R35 (irruption.md §13)</td></tr>
<tr><td>Scavenging takes days, swimmers eat from the water</td><td>Per-species kg over days</td><td>scav.md §15</td></tr>
<tr><td>Vermin eaters eat what they walk to</td><td>Vermin are not units</td><td>vermin.md rig tests (3,000-tick reps)</td></tr>
<tr><td>The apex scheduler meets its presence target; the ladder meets 20 % carnivores</td><td>Season-long shares</td><td>APX1, LAD1, AP1, PEL1, INV3, R28P (roster.md)</td></tr>
<tr><td>Pull, mix and guard shape the water</td><td>Arrivals, distances, strandings</td><td>SURV, PELA, MIX1, GRD1 (water.md)</td></tr>
<tr><td>Extinct corrections change arrivals</td><td>Needs the extinct setting of region8 read first</td><td>extinct.md rig tests</td></tr>
<tr><td>Water auto-on and spill reach 3-5 groups</td><td>Counts over two seasons</td><td>F1, F2 (fixes.md)</td></tr>
<tr><td>Cost of every v7.1 change</td><td>One fort, one session</td><td>PERF0-PERF4 (perf.md)</td></tr>
<tr><td>Panel and page round trips on a real screen</td><td>A DFHack screen cannot render headless</td><td>ui.md and web.md rig tests; gui.* and web.* validator claims</td></tr>
<tr><td>Anything at all on DFHack 53.16-r2</td><td>No v7.1 run yet, on r2 or r1.1</td><td><b>revalidate-dfhack-r2 and validate-full on v7.1: needed first</b> (HARNESS-v71)</td></tr>
</tbody></table></div>"""
phase(7, 'What this page cannot check', 'A walkthrough sees the window, the console and the page. These parts act inside DF over time; only the rig tests in the stream notes measure them.', pre=CANNOT)

REPORT = """
    <section class="phase" id="p8">
      <div class="phase-head"><span class="num">8</span><h2>Compile the report</h2>
        <p class="why">Everything you marked and wrote becomes one report. Copy it out and send it; nothing leaves this page on its own.</p></div>
      <div class="report">
        <div class="tester">
          <label>Tester<input id="tName" placeholder="name or handle"></label>
          <label>Fort<input id="tFort" placeholder="region8 fort name, biomes, embark size"></label>
          <label>Game &amp; DFHack<input id="tVer" placeholder="53.16 · 53.16-r2 · seasonal-wildlife 7.1.0 @ fce7d68"></label>
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
          <p class="muted" style="margin:10px 0 6px">Paste the contents of a round's <code>marks.json</code>. Its marks and notes replace what is on this page for the steps it covers. A file for this page carries <code>"_meta": {"page": "alpha4"}</code>; any other file is refused, because Alpha Three and earlier number their steps differently.</p>
          <textarea id="marksIn" placeholder='{"0.1": {"v": "p", "n": "note"}, "_meta": {"page": "alpha4", "tName": "..."}}'></textarea>
          <div class="bar" style="margin-top:8px"><button class="ghost" id="btnLoad">Load marks</button><span class="muted" id="loadMsg"></span></div>
        </details>
      </div>
    </section>"""

# ===================================================================================================== render
ALL_IDS = [s['id'] for ph in P for _, steps in ph[3] for s in steps]
assert len(ALL_IDS) == len(set(ALL_IDS)), 'duplicate step id'
for ph in P:
    n = 0
    for _, steps in ph[3]:
        for s in steps:
            n += 1
            assert s['id'] == f'{ph[0]}.{n}', (s['id'], ph[0], n)

def anchor(sid):
    return 's' + sid.replace('.', '-')

def refs(text):
    def rep(m):
        sid = m.group(1)
        assert sid in ALL_IDS, 'reference to a missing step: ' + sid
        return f'<a class="ref" href="#{anchor(sid)}">{sid}</a>'
    return re.sub(r'\[\[([0-9]+\.[0-9]+)\]\]', rep, text)

def step_html(s):
    tags = ''.join(f'<span class="tag{"" if kind == "rc" else " " + kind}">{E(txt)}</span>' for kind, txt in s['tags'])
    rows = [f'<div class="do"><span>Do</span><span>{s["do"]}</span></div>',
            f'<div class="expect"><span>Expect</span><span>{s["expect"]}</span></div>']
    if s['watch']:
        rows.append(f'<div class="watch"><span>Watch</span><span>{s["watch"]}</span></div>')
    if s['rul']:
        rows.append(f'<div class="pend"><span>Ruling</span><span>{s["rul"]}</span></div>')
    if s['src']:
        rows.append(f'<div class="basis"><span>Basis</span><span>{s["src"]}</span></div>')
    inner = '\n          '.join(rows)
    return (f'        <div class="step" id="{anchor(s["id"])}" data-id="{s["id"]}"><div class="id">{s["id"]}</div><div class="body"><h3>{s["title"]}{tags}</h3>\n'
            f'          {inner}\n'
            f'          <div class="verdict"></div></div></div>')

sections = []
for num, title, why, groups, pre, pid, post in P:
    body = ''
    for surf, steps in groups:
        if surf:
            body += f'      <h3 class="surface">{surf}<span class="sn">{steps[0]["id"]}–{steps[-1]["id"]}</span></h3>\n'
        body += '      <div class="steps">\n' + '\n'.join(step_html(s) for s in steps) + '\n      </div>\n'
    sections.append(f'    <section class="phase" id="{pid}">\n      <div class="phase-head"><span class="num">{num}</span><h2>{title}</h2>\n'
                    f'        <p class="why">{why}</p></div>\n      {refs(pre)}\n{body}      {refs(post)}\n    </section>\n')

nsteps = len(ALL_IDS)
page = f"""<title>Seasonal Wildlife Alpha Four</title>
{fonts}
{style}

<header class="masthead">
  <div class="wrap">
    <div class="eyebrow">Alpha trial four · window, console and browser · v7.1</div>
    <h1>Seasonal Wildlife Alpha Four</h1>
    <p class="lede">A walkthrough of everything <em>Seasonal Wildlife</em> v7.1 added, on the region8 test world and DFHack 53.16-r2, organised around the six features the user named: biodiversity, active layers, seasonal food webs, realism, caverns, and the rest. Each feature is tested in the window, at the console and in the browser companion. Work on a copy of a region8 fort, mark each step, and compile the report at the end.</p>
    <div class="facts">
      <span>Plugin <b>seasonal-wildlife 7.1.0</b> (branch v7.1 @ fce7d68)</span>
      <span>Game <b>Dwarf Fortress 53.16</b> · <b>DFHack 53.16-r2</b></span>
      <span>World <b>region8, “The Last Planets”</b></span>
      <span>Status <b>built, untested — expected by design</b></span>
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

    <div class="note" style="margin-bottom:26px"><b>How to read a step.</b> <b>Do</b> is what to press or type; <b>Expect</b> is what the design says you should see; <b>Watch</b> is what tends to go wrong, or a quirk already seen offline. <b>Ruling</b> quotes the user's ruling the step tests (R1-R63, USER-REVIEW-PART2). <b>Basis</b> starts “Built, untested — expected by design” on every step, then names the source: a stream's notes (docs/v7.1/&lt;stream&gt;.md in the seasonal-wildlife repo, at fce7d68), the code, or the offline harnesses that ran the real engine on a stubbed world. Tags: <b>re-check A3</b> tests a fault Alpha Three flagged; <b>new v7.1</b> marks what v7.1 added; <b>r2</b> rests on something DFHack r2 changed. Mark <b>Pass</b> when what you see matches, <b>Anomaly</b> for anything else (say what you pressed, saw and expected), <b>Skipped</b> when your fort cannot show it.</div>

{''.join(sections)}{REPORT}

  </main>
</div>

{script}
"""
OUT.write_text(page, encoding='utf-8')
n = page.count('class="step" id=')
print(f'wrote {OUT} ({len(page):,} bytes); {len(P)+1} sections, {n} steps; '
      f're-check tags {page.count(">re-check ")}, new tags {page.count(">new v7.1<")}, r2 tags {page.count(">r2<")}; '
      f'steps per phase: ' + ', '.join(f'{ph[0]}:{sum(len(s) for _, s in ph[3])}' for ph in P))
