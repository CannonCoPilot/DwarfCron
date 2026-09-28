#!/usr/bin/env python3
"""Build the alpha 2 walkthrough (seasonal-wildlife v6.6) from alpha 1's styles and script.
Every key below was read off the v6.6 window (validate-full 20260927-002027 screen dumps) or its HotkeyLabels."""
import re
from pathlib import Path

SRC = Path('/Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch/alpha-walkthrough.html')
OUT = Path('/Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch/alpha2-walkthrough.html')
a1 = SRC.read_text(encoding='utf-8')
style = re.search(r'<style>.*?</style>', a1, re.S).group(0)
fonts = re.search(r'<link rel="stylesheet"[^>]*>', a1).group(0)
script = re.search(r'<script>.*?</script>', a1, re.S).group(0)

# alpha 2: its own storage key and report title; Clear asks for a second press (the viewer blocks confirm())
script = script.replace("var KEY='sw-alpha-trial-v1';", "var KEY='sw-alpha-two-v1';")
script = script.replace("lines.push('# Seasonal Wildlife alpha trial — phase one (UI)');",
                        "lines.push('# Seasonal Wildlife alpha trial two (UI, v6.6)');")
old_clear = re.search(r"document\.getElementById\('btnClear'\)\.addEventListener\('click',function\(\)\{(.*?)\}\);\n", script, re.S)
assert old_clear, 'clear handler not found'
body = old_clear.group(1)
script = script.replace(old_clear.group(0),
    "var armed=false,armT=null;document.getElementById('btnClear').addEventListener('click',function(){var b=this;"
    "if(!armed){armed=true;b.textContent='Press again to clear every mark';clearTimeout(armT);armT=setTimeout(function(){armed=false;b.textContent='Clear all marks'},4000);return;}"
    "armed=false;b.textContent='Clear all marks';" + body + "});\n")
extra_css = """
.recheck{border-collapse:collapse;font-size:0.93rem;margin-top:14px;width:100%}
.recheck th,.recheck td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--rule);vertical-align:top}
.recheck th{font-weight:600;color:var(--ink-2);font-size:0.8rem;letter-spacing:0.06em;text-transform:uppercase}
.recheck td:first-child{white-space:nowrap;font:600 0.85rem "JetBrains Mono",ui-monospace,monospace;color:var(--rust)}
.recheck td:last-child{white-space:nowrap;font:600 0.85rem "JetBrains Mono",ui-monospace,monospace}
.tablewrap{overflow-x:auto}
.step .tag{display:inline-block;font:600 0.68rem/1.6 "Source Sans 3",sans-serif;letter-spacing:0.08em;text-transform:uppercase;color:var(--rust);background:var(--rust-soft);border-radius:3px;padding:0 6px;margin-left:8px;vertical-align:0.1em}
</style>"""
style = style.replace('</style>', extra_css)

def k(*keys):
    return '+'.join(f'<kbd>{x}</kbd>' for x in keys)

# (id, title, do, expect, watch, recheck-tag or '')
P = []
def phase(num, title, why, steps, need='', pre=''):
    P.append((num, title, why, steps, need, pre))

RECHECK = """<div class="tablewrap"><table class="recheck"><thead><tr><th>Alpha 1</th><th>What it found in v6.2.1</th><th>Fixed in</th><th>Re-check at</th></tr></thead><tbody>
<tr><td>R1</td><td>A blocked species kept its worldgen stock and could still arrive (63 on Boatsbowed); water and cavern species were never seasoned.</td><td>v6.3</td><td>2.3, 2.4, 16.1</td></tr>
<tr><td>R2</td><td>One raw flag decided a species' category: a giant orca read as prey, an albatross as aquatic, a dingo as large.</td><td>v6.4</td><td>3.2, 10.2</td></tr>
<tr><td>R3</td><td>Co-align and the Y/D fills cascaded through the whole roster in one pass; a lion could eat a shark.</td><td>v6.4</td><td>5.3, 5.4, 10.2</td></tr>
<tr><td>R4</td><td>Jobs ran for seconds on a big fort; the ecology write tripped its fuse unseen.</td><td>v6.3</td><td>1.3, 17.2</td></tr>
<tr><td>R5</td><td>Ctrl+R and Ctrl+L were DF's own macro keys; the window drew garbled dashes; the overlay stayed on.</td><td>v6.3</td><td>2.7, 7.1, 15.1</td></tr>
<tr><td>7.6</td><td>Whole-roster tools changed many species without asking.</td><td>v6.3</td><td>5.1</td></tr>
<tr><td>9.2</td><td>Undo went only ten steps back.</td><td>v6.5</td><td>14.2</td></tr>
</tbody></table></div>"""

phase(0, 'Before you open the window',
  'Alpha two tests v6.6, the release that answers alpha one. Most steps re-test something alpha one found; the tag on a step names it.',
  [
   ('0.1', 'Choose the fort', 'Use a copy of the alpha one fort if you still have it, or embark a fort with wildlife on the surface and, ideally, a river or lake and a breached cavern.',
    'Nothing yet. Note the biomes, whether water touches the map edge, and whether a cavern is open.', 'Write the fort’s population, year and season in the note, so later steps have a baseline.', ''),
   ('0.2', 'Back it up', 'Copy the save folder before you open the window.',
    'A fort that never opens the window is never touched, so the copy is your control.', 'The tool writes to the map’s wildlife populations, to creature raws while it runs, and to persistent site data.', ''),
   ('0.3', 'Turn on the frame counter', 'In Settings, show the frame rate. Read it unpaused for a minute at your usual speed.',
    'A baseline for phase 17. A paused game shows a meaningless high number.', 'Two loads of the same fort can differ by ten to fifteen percent on their own.', ''),
  ],
  pre='<div class="note"><b>Use a backup.</b> The plugin under test is <code>seasonal-wildlife v6.6.0</code>. It passed 177 of its claims on the test rig with none failing (run 002027), but the rig forts are small and seven dwarves strong; yours is the real test.</div>'
      '<table class="sev"><thead><tr><th>Mark</th><th>Use it when</th></tr></thead><tbody>'
      '<tr><td><b>Pass</b></td><td>What the step promises is what you saw.</td></tr>'
      '<tr><td><b>Anomaly</b></td><td>Anything else: a wrong value, a key that did nothing, a clipped column, a word you did not understand, a frame-rate dip. Write what you pressed, what you saw and what you expected.</td></tr>'
      '<tr><td><b>Skipped</b></td><td>The fort cannot show it (no water, no cavern found, no boundary reached). Say why.</td></tr></tbody></table>'
      '<h3 style="margin-top:22px">What alpha one found, and where to re-check it</h3>' + RECHECK)

phase(1, 'First open: Overview and Panel',
  'The window opens on the Overview. The Panel tab is new in v6.3: every switch the tool has, and how long each job takes.',
  [
   ('1.1', 'Open the window', f'In DFHack’s console type <code>gui/seasonal-wildlife</code>, or use your launcher.',
    'A window titled <b>Seasonal Wildlife</b> with nine tabs: Overview, Panel, Roster, Seasons, Food web, Live, Layers, Vermin, Ledger. The Overview shows the date, what is on the map per layer, what is in season, and the next boundary.',
    'All text should be plain ASCII. Alpha one saw dashes drawn as <code>ΓÇö</code>.', 'R5'),
   ('1.2', 'Read the Panel', 'Click <b>Panel</b>.',
    'A SWITCHES list with <b>[ON]</b> or <b>[off]</b> on every row (rotation, each layer, groups, cohesion, ecology, nudge, water draws, deep layer, coupling, livestock, vermin hunting, irruptions, overlay), then a JOBS table: every, last, worst, runs, over, fuse. A frame-rate line reads the game’s rate; it is information only.',
    'Enter on a switch row flips it. Note any switch whose description you could not follow.', ''),
   ('1.3', 'Read the job timings', 'Leave the window open a game day, then press <kbd>R</kbd> on the Panel.',
    'Each job shows its last and worst pass in milliseconds against a 50 ms budget; <b>over</b> counts passes above it; <b>fuse</b> reads intact.',
    'Record the worst figures. The rig saw the groups job reach 149 to 196 ms on some passes, so a nonzero <b>over</b> on groups is known; a tripped fuse is not.', 'R4'),
   ('1.4', 'All off, then all on', f'Press {k("X")} (All off) and answer the question; then {k("A")} (All on).',
    'Each asks first. All off stops every job and restores every creature raw the tool changed; all on puts the switches back as they were.',
    'Anything left on after All off, or a switch that came back different.', ''),
  ])

phase(2, 'The roster rule',
  'Alpha one’s biggest finding: a species you blocked could still arrive. v6.3 has one rule. An active species has at least one season; the only way to keep one away is to make it inactive, and an inactive species is held on every layer.',
  [
   ('2.1', 'Read the new columns', 'Click <b>Roster</b>.',
    'Columns CREATURE, ROLE (predator, prey, vermin), SIZE (small, medium, large), HAB (land, fly, wbird, semi, aqua), BIOME, SEASON, STOCK, ODDS, act, WHY. The header counts active species per role and says how many <b>special</b> creatures are left to DF.',
    'Special means DF’s own classes: demons, megabeasts, titans, forgotten beasts, night creatures and the like. They are not on the roster by design.', ''),
   ('2.2', 'Filters', f'Cycle {k("V")} (View: Current, Default, Add invasive), {k("C")} (category, including habitats), {k("B")} (biome), {k("N")} (season).',
    'Each changes the rows. Default shows the roster as the embark was first found.', 'A filter that empties the list without saying why.', ''),
   ('2.3', 'Make a species inactive', 'Select an active species and press <kbd>Enter</kbd>.',
    'act turns to <b>-</b>, its SEASON clears, WHY reads <b>you</b> and today’s date.', 'Remember the species; step 16.1 checks it never arrives.', 'R1'),
   ('2.4', 'Make it active again', 'Press <kbd>Enter</kbd> on the same row.',
    'act turns to <b>Y</b> with <b>exactly one</b> season, chosen from its climate.', 'No season, or all four.', 'R1'),
   ('2.5', 'Cycle seasons', f'Press {k("E")} (or {k("Shift","Enter")}) on an active row several times.',
    'The season steps through single seasons and pairs and never lands on none.', 'A row left with no season.', ''),
   ('2.6', 'Try to remove the last season', f'On a species with one season, press that season’s key ({k("S")} {k("U")} {k("A")} {k("W")}).',
    'Refused: <b>the last season stays: make the species inactive instead</b>.', 'The row going to no season.', ''),
   ('2.7', 'Cycle the layer', f'Press {k("Alt","L")} five times.',
    'The title reads All layers, Land, Water, Cavern (with how many are found), Deep (magma sea), then All layers again; the rows follow the layer.',
    'The layer key used to be Ctrl+L, DF’s macro key. Nothing should start recording a macro.', 'R5'),
  ])

phase(3, 'One creature: the species detail',
  'The detail page is where one species’ controls live: its habitat and role, its stock and odds, its group size, and a call.',
  [
   ('3.1', 'Open the detail', f'Select a large animal and press {k("I")}.',
    'Rows for species, habitat, role, body (<b>adult volume in cm³</b> and its band), embark, allowed, stock, odds, group size, seasons, eats, eaten by, on the map, history.',
    'Bands are small under 150,000 cm³, medium to 1,000,000, large above. A lion reads about 200,000 (medium), an elephant 5,000,000 (large). Until v6.4.1 every size read ten times too small.', 'R2'),
   ('3.2', 'Habitat and role come from the raws', 'Open the detail for an orca or giant orca, an albatross, and a dingo if your world has them.',
    'Orca: aquatic predator. Albatross: waterbird (flies, lives by water), not aquatic. Dingo: land predator, small.',
    f'If one reads wrong, {k("H")} cycles its habitat and {k("R")} its role; the row then says <b>you</b> and what the raws said.', 'R2'),
   ('3.3', 'Set its stock', f'Press {k("K")} and enter a number.',
    'The stock line reads the number you set. For a species out of season it says how many <b>come back in season</b>.',
    'Stock is how many remain in the region to arrive. It does not make a species more likely; that is odds.', ''),
   ('3.4', 'Set its odds', f'Press {k("O")} and enter a number.',
    'The odds line shows the weight and its share of the layer.',
    'On the rig, raising two species’ odds took them from about a quarter of surface waves to about three quarters.', ''),
   ('3.5', 'Set its group size', f'Press {k("G")} and enter a number.',
    'The group size line says <b>you set it</b>.', 'DF sometimes sends one more than the size you set, never two more. That is DF, not the tool.', ''),
   ('3.6', 'Call a wave', f'For an active land species in season, press {k("C")}.',
    'The next land wave is that species. The ledger records the call.', 'A call that brings another species.', ''),
  ])

phase(4, 'Stock and odds on the Roster',
  'The same two controls, for one row or for every row the filter shows.',
  [
   ('4.1', 'Stock for one row', f'Select a row and press {k("Ctrl","W")}.', 'A prompt <b>Stock for</b> the species; the STOCK column changes.', '', ''),
   ('4.2', 'Stock for the filter', f'Filter to one category and press {k("Ctrl","G")}.', 'Every row shown takes the number.', 'Rows outside the filter changing.', ''),
   ('4.3', 'Odds for one row', f'Press {k("Alt","O")} on a row.', 'The ODDS column shows its share of its layer.', '', ''),
  ])

phase(5, 'Whole-roster tools',
  'Each of these rewrites many species, so since v6.3 each asks first.',
  [
   ('5.1', 'Every tool asks', f'Press {k("M")} (Matrix assign), {k("O")} (Co-align), {k("F")} (Fill to targets), {k("Y")} and {k("D")} (fill natural prey or predators), and answer No each time.',
    'A yes/no question every time, and No changes nothing.', 'A tool that acts without asking.', '7.6'),
   ('5.2', 'Matrix assign', f'Press {k("M")} and answer Yes.',
    'Every active species gets one season by climate, spread across the year, and every season of every habitat group keeps at least one predator with prey it eats. WHY reads <b>matrix</b>, or <b>pair</b> where a season was added for a pair.',
    'One season holding more than half the roster.', ''),
   ('5.3', 'Co-align', f'Press {k("O")} and answer Yes.',
    'Partners are aligned to within one adjacent season of each other. Seasons are only ever added, and never spread through the whole roster.',
    'Alpha one saw co-align give most species all four seasons in one press.', 'R3'),
   ('5.4', 'Fill natural prey and predators', f'Press {k("Y")}, then {k("D")}.',
    'Each adds only direct partners where a pairing is missing, and the ledger says how many.', 'A fill that activates species with no partner.', 'R3'),
   ('5.5', 'Category targets', f'Press {k("Shift","P")} (prey), {k("Shift","R")} (predator) or {k("Shift","V")} (vermin) to set a target, then {k("Alt","F")} to fill a category to a number.',
    'The P / R / V line shows the targets; the header says Thin when a category is under its target.', '', ''),
  ])

phase(6, 'Apply, send off, rotation',
  'The roster only reaches DF when it is applied, at each season boundary or by hand.',
  [
   ('6.1', 'Dry run', f'Press {k("Ctrl","D")}.', 'A list of what an apply would change, with nothing changed.', '', ''),
   ('6.2', 'Apply now', f'Press {k("Ctrl","A")}.', 'DF’s announcement log reads <b>&lt;Season&gt; wildlife applied (N active).</b>', 'If the filter box has focus, Ctrl+A may select its text instead; the label works by mouse.', ''),
   ('6.3', 'Send off and next', f'With wild animals on the surface, press {k("Ctrl","F")}.', 'The groups on the map are told to leave, and DF may send the next wave.', 'This replaces force-wildlife, which piled a new wave on the old one.', ''),
   ('6.4', 'Rotation off and on', f'Press {k("Ctrl","E")} twice.', 'The header reads rotation off, then on.', '', ''),
  ])

phase(7, 'Reset',
  'Two levels since v6.3: the roster, or everything.',
  [
   ('7.1', 'Reset the roster', f'Press {k("Alt","R")}, choose <b>The roster</b>, answer Yes.',
    'The roster returns to the embark as first found: every active species on one season (a predator may keep a second one for a pair). Stock and odds you set are kept.',
    'Reset used to be Ctrl+R, DF’s record-macro key.', 'R5'),
   ('7.2', 'Reset everything', f'Press {k("Alt","R")}, choose <b>Everything</b>, answer Yes.',
    'Stock returns to the worldgen snapshot and every setting to its default; the roster as first found.', 'Do this last in a session, or on the copy.', ''),
  ])

phase(8, 'Add an invasive species',
  'A species that is not native to the embark can be brought in live.',
  [
   ('8.1', 'Add invasive', f'Press {k("V")} until View reads Add invasive, select a species, press {k("Ctrl","X")}.',
    'The species joins the roster for this map, and the ledger records the add.', 'Note whether it arrived active and with which seasons; an added species that never shows on the Roster is an anomaly.', ''),
  ])

phase(9, 'Seasons tab',
  'Every active species under its level across the four seasons. New in v6.6: you can edit here.',
  [
   ('9.1', 'Read it', 'Click <b>Seasons</b>.', 'Columns Spring to Winter; <b>+</b> arrives that season, <b>-</b> leaves after it, <b>.</b> not present.', '', ''),
   ('9.2', 'Edit from the grid', f'Select a row and press {k("S")}, {k("U")}, {k("A")} or {k("W")}.', 'That season flips for the species, as on the Roster, and the header names the species with its new seasons.', 'Removing its last season should be refused here too.', ''),
  ])

phase(10, 'Food web',
  'Who eats whom, from the species model: role, habitat and body size.',
  [
   ('10.1', 'The pyramid', 'Click <b>Food web</b>.', 'Levels large predators, small predators, prey, vermin. Large predators now include every medium or large predator.', 'A level that is empty on a fort that has its animals.', ''),
   ('10.2', 'Diet follows habitat', 'Look for any land predator shown eating a sea creature, or a bird eating a large fish.',
    'None. A lion takes no shark, an eagle no tuna, a great white no deer. An osprey takes small sea fish (vermin).', 'Alpha one saw lions eating sharks.', 'R3'),
   ('10.3', 'The four modes', f'Press {k("G")} to step Pyramid, Graph, By season; {k("L")} for By layer; {k("N")} for the season.',
    'Graph shows arrows and marks live pairs; By season shows four columns with the mass ratio; By layer puts layers side by side.', '', ''),
  ])

phase(11, 'Live',
  'What is on the map this instant, and where each animal came from.',
  [
   ('11.1', 'Origins', 'Click <b>Live</b>.',
    'A <b>Wild on map</b> line, then each animal by origin: DF wave, tool-drawn, resident, born here, untracked, deep. Then the ecology, limits, cavern and fuse lines.', 'An animal counted twice or in no origin.', ''),
   ('11.2', 'Groups', 'Scroll to <b>Groups:</b>.', 'One row per tracked group: species, size, how it came, its day.', '', ''),
   ('11.3', 'Hold and send off', f'Select a group; press {k("Q")} (hold 30 days), then {k("X")} (send off).', 'The row reads <b>held N more days</b>, then <b>dismissed</b>, and the group leaves.', '', ''),
   ('11.4', 'Follow and centre', f'Press {k("F")} on a group, then <kbd>Enter</kbd>.', 'The camera follows a member; Enter centres the map on the group.', '', ''),
   ('11.5', 'Herds and packs', 'Read the Herds &amp; packs block.', 'Each tracked species is herd, pack, flock or <b>school</b>, with the reason from its raws.', '', ''),
  ])

phase(12, 'Layers',
  'One column per layer, with the same words on every layer.',
  [
   ('12.1', 'Read the table', 'Click <b>Layers</b>.',
    'Columns LAND, WATER, CAVERN, DEEP; rows layer, drawn by, groups at once, ceiling, gap between waves, pattern, coupling, cohesion, ecology switch, nudge after, pack size, irruptions, cavern pressure.',
    'Water is drawn by the tool (DF sends no river or lake waves in play); land and caverns by DF; deep by frequency.', ''),
   ('12.2', 'Change a limit', f'Press {k("L")} to pick a column, then {k("C")} (groups at once) or {k("Q")} (ceiling).', 'The cell changes and the ledger records it.', '', ''),
   ('12.3', 'The water line', 'Read the line under the table that starts <code>water:</code>.', 'Groups at once, animals against the ceiling, the water on the map (ocean, lake, river, pool; salt and fresh), and the next draw.', 'A fort with water that reads dormant.', ''),
   ('12.4', 'Caverns', 'Read the Caverns block.', 'Each cavern is <b>not yet found</b> until your dwarves reach it, then its species.', '', ''),
  ])

phase(13, 'Vermin, and vermin hunting',
  'Vermin by family, now editable per species. Vermin hunting is an opt-in switch new in v6.6.',
  [
   ('13.1', 'Families', 'Click <b>Vermin</b>.', 'One row per family (fish, flies, fliers, mammals, crawlers) with active count, seasons, stock and layers.', '', ''),
   ('13.2', 'Open a family', f'Select a family and press {k("E")}.', 'Its species appear under it, each with active, seasons, stock and layer.', '', ''),
   ('13.3', 'Edit one vermin species', f'On a species row press <kbd>Enter</kbd>, a season key, or {k("Shift","W")} (stock).', 'That species alone changes.', '', ''),
   ('13.4', 'Vermin hunting on', 'On the Panel, turn on <b>Vermin hunting</b>.',
    'Predatory and water birds get the dive-hunting flag and small land predators the hunting flag, for as long as the switch is on.',
    'On the rig, wild kestrels and badgers with the flags behaved no differently from those without. Tell us if yours do anything visible.', ''),
  ])

phase(14, 'Ledger, undo, help',
  'Every write the tool makes is in the ledger, and the edits can be undone.',
  [
   ('14.1', 'Filter the ledger', f'Click <b>Ledger</b>; press {k("K")} (kind) and {k("L")} (layer).', 'The list narrows; the count line shows how many of how many.', '', ''),
   ('14.2', 'Undo', f'Make three roster edits, then press {k("Z")} three times.', 'Each edit is undone in reverse order. Undo now goes fifty edits deep.', '', '9.2'),
   ('14.3', 'Help on every tab', f'On each tab press {k("Alt","H")}.', 'A help page for that tab, with the vocabulary: active, stock, odds, group size, groups at once, ceiling, send off, call.', 'A word used in the window that the help does not explain.', ''),
  ])

phase(15, 'The map overlay',
  'Group markers and predator-prey links drawn on the map.',
  [
   ('15.1', 'Turn it on', 'Open <code>gui/control-panel</code>, find the overlay <code>seasonal-wildlife.groups</code>, enable it.', 'Markers on tracked groups, only on the level you are viewing, and lines between related predators and prey.', 'Alpha one’s run left the overlay on; turn it off again at the end if you do not want it.', 'R5'),
  ])

phase(16, 'A season boundary',
  'Let the game run into the next season. This is where the roster meets DF.',
  [
   ('16.1', 'Inactive stays away', 'Play through at least one boundary; watch for the species you made inactive in 2.3.',
    'It never arrives, on any layer. On the rig’s copy of the alpha one fort, v6.4 let no inactive animal in across two test runs, where v6.2.1 let in 32 and 12.', 'Any inactive or out-of-season arrival: note species, layer and date.', 'R1'),
   ('16.2', 'The boundary itself', 'At the change of season, read the announcements and the Ledger.', 'A <b>&lt;Season&gt; wildlife roster applied</b> announcement and a season line in the ledger.', '', ''),
   ('16.3', 'Water groups', 'If your map has river or lake water, watch the water line and the Live tab over a few days.', 'Groups drawn into water that suits them, swimming together, leaving on their countdown.', 'An animal placed on dry land.', ''),
  ])

phase(17, 'Persistence and cost',
  'Does everything survive a reload, and what does the tool cost while its jobs run.',
  [
   ('17.1', 'Save, quit, reload', 'Note an inactive species, a stock you set, and the ledger’s last line. Save, return to the title, load again, open the window.', 'All three as you left them; undo still works.', 'Settings back at defaults, or a ledger that restarted.', ''),
   ('17.2', 'Frame rate on and off', 'Unpaused, read the frame rate for a minute with the tool on; then All off on the Panel and read it again.',
    'On the test fort the jobs cost about ten to twelve percent of frame rate while they run.', 'Compare within one session and ignore the first seconds after a switch. Note the Panel’s worst times too.', 'R4'),
  ])

REPORT = """
    <section class="phase" id="p18">
      <div class="phase-head"><span class="num">18</span><h2>Compile the report</h2>
        <p class="why">Everything you marked and wrote becomes one report. Copy it out and send it; nothing leaves this page on its own.</p></div>
      <div class="report">
        <div class="tester">
          <label>Tester<input id="tName" placeholder="name or handle"></label>
          <label>Fort<input id="tFort" placeholder="fort name, biomes"></label>
          <label>Game &amp; DFHack<input id="tVer" placeholder="53.16 · 53.16-r1.1 · plugin v6.6.0"></label>
          <label>Date<input id="tDate" placeholder="YYYY-MM-DD"></label>
        </div>
        <div class="bar" style="margin-top:14px">
          <button id="btnCompile">Compile report</button>
          <button class="ghost" id="btnCopy">Copy to clipboard</button>
          <button class="ghost" id="btnClear">Clear all marks</button>
          <span class="muted" id="copyMsg"></span>
        </div>
        <textarea id="reportOut" readonly placeholder="Press Compile report. The text is Markdown: the tally, then every anomaly with its note, then skipped steps, then passes."></textarea>
      </div>
    </section>"""

def step_html(s):
    sid, title, do, expect, watch, tag = s
    t = f'<span class="tag">re-check {tag}</span>' if tag else ''
    w = f'\n          <div class="watch"><span>Watch</span><span>{watch}</span></div>' if watch else ''
    return (f'        <div class="step" data-id="{sid}"><div class="id">{sid}</div><div class="body"><h3>{title}{t}</h3>\n'
            f'          <div class="do"><span>Do</span><span>{do}</span></div>\n'
            f'          <div class="expect"><span>Expect</span><span>{expect}</span></div>{w}\n'
            f'          <div class="verdict"></div></div></div>')

# the report compiler reads h3 text for titles; keep the tag out of it
script = script.replace("var t=st.querySelector('h3').textContent;", "var h=st.querySelector('h3').cloneNode(true); var tg=h.querySelector('.tag'); if(tg)tg.remove(); var t=h.textContent;")

sections = []
for num, title, why, steps, need, pre in P:
    sections.append(f'    <section class="phase" id="p{num}">\n      <div class="phase-head"><span class="num">{num}</span><h2>{title}</h2>\n'
                    f'        <p class="why">{why}</p></div>\n      {pre}\n      <div class="steps">\n' +
                    '\n'.join(step_html(s) for s in steps) + '\n      </div>\n    </section>\n')

page = f"""<title>Seasonal Wildlife Alpha Two</title>
{fonts}
{style}

<header class="masthead">
  <div class="wrap">
    <div class="eyebrow">Alpha trial two · UI · re-tests alpha one</div>
    <h1>Seasonal Wildlife Alpha Two</h1>
    <p class="lede">A play-order walkthrough of the <em>Seasonal Wildlife</em> window as of v6.6, the release built from what alpha one found. Work through it on a live fort, mark each step, and compile the report at the end. Steps tagged <b>re-check</b> test a specific alpha one finding. Console commands are left for a later round.</p>
    <div class="facts">
      <span>Plugin <b>seasonal-wildlife v6.6.0</b> (f22fa30)</span>
      <span>Game <b>Dwarf Fortress 53.16</b> · <b>DFHack 53.16-r1.1</b></span>
      <span>Validated <b>177 claims pass on the rig, 0 fail</b> (run 002027)</span>
      <span>Steps <b id="stepcount">–</b></span>
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

{''.join(sections)}{REPORT}

  </main>
</div>

{script}
"""
OUT.write_text(page, encoding='utf-8')
n = page.count('class="step" data-id=')
print(f'wrote {OUT} ({len(page):,} bytes); {len(P)+1} phases, {n} steps; re-check tags {page.count("re-check ")}')
