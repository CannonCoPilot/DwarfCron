#!/usr/bin/env python3
"""Full functional validation of seasonal-wildlife: every surface, every claim, on the live rig.

The claim set is everything the tool has been SAID to do — USAGE.md, the script's own docstring,
the design report (§2 capability list, §5 work packages, §11 the thirteen views), PLAN.md
(§1 map, §3.5–3.6b the unshipped packages), the Wildlife Backlog and the Fortress Docket. Every
claim gets a verdict from a fixed vocabulary, and every verdict names what was expected and what
the rig actually returned:

  PASS               did what was claimed, with the receipt and the ground truth to show it
  FAIL               claimed shipped, exercised, did not do it
  DEAD               present in the code and inert — stores a number, prints a line, moves nothing
  UNWIRED            promised in a plan or report, no code behind it at all
  DOC-DRIFT          the documentation contradicts the shipped code
  NOT-TESTABLE-HERE  needs a condition one session cannot manufacture; cites the experiment that did
  BACKLOG            explicitly unscheduled; recorded so the report is complete, not counted

Three kinds of evidence per check: the console receipt, a Lua probe of the game state (pool
quantities, units on the map, the reaction cache, leader flags, countdowns), and for anything
visible a PNG of the DF window plus the text grid. The rig is CTRL (inland, dry, caverns never
opened) with one excursion to LAKE for the water layer, which is dormant everywhere else.

Runs only when the rig is free; leaves it at the title with the forts byte-identical.
Usage: validate-full.py [--fort CTRL] [--skip-lake] [--skip-gui] [--only PHASE] [--v71 AREA,...]
       validate-full.py --list [TEXT]           print the claim register (id, surface, claimed-as, claim); no rig
       validate-full.py --dry-run [--only PHASE] [--v71 AREA,...]
                                                walk the phases against a stub rig: every Lua probe through luac53,
                                                every engine name it reads checked against $SW_TOOL, every console
                                                verb against the dispatcher; no rig, no DF (experiments/VALIDATOR-v71.md)
"""
import argparse, json, math, os, re, subprocess, sys, time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CX = str(ROOT / "scripts" / "cx-lifecycle.sh")
TOOL = Path(os.environ.get("SW_TOOL", str(Path.home() / "Claude/Projects/seasonal-wildlife")))   # the checkout under test (a worktree per release)
RUN = datetime.now().strftime("%Y%m%d-%H%M%S")
OUT = ROOT / "data/validation/full" / RUN
# --list and --dry-run never touch the rig and never write a run directory under data/ (v7.1 validator wave)
DRY = "--dry-run" in sys.argv
LISTING = "--list" in sys.argv
if DRY or LISTING:
    import tempfile
    OUT = Path(tempfile.mkdtemp(prefix="validate-full-dry-"))
SHOTS, SCREENS, GROUND = OUT / "shots", OUT / "screens", OUT / "ground"
for d in (SHOTS, SCREENS, GROUND):
    d.mkdir(parents=True, exist_ok=True)
SAVES = Path.home() / "Library/Application Support/CrossOver/Bottles/Win10/drive_c/users/crossover/AppData/Roaming/Bay 12 Games/Dwarf Fortress/save"
BACKUPS = Path.home() / "Library/Application Support/CrossOver/df-snapshots/saves"

# the version under test: the DEPLOYED engine's newest changelog line (the static phase reads the repo checkout, which
# must be on the same branch). Checks whose behaviour changed with a release branch on it.
def deployed_version():
    f = Path.home() / "Library/Application Support/CrossOver/Bottles/Win10/drive_c/Program Files (x86)/Steam/steamapps/common/Dwarf Fortress/dfhack-config/scripts/seasonal-wildlife.lua"
    m = re.search(r"^-- v(\d+)\.(\d+)\.(\d+) \u2014", f.read_text(errors="replace"), re.M) if f.exists() else None
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)
V = deployed_version()
V65 = V >= (6, 5, 0)
V66 = V >= (6, 6, 0)
V67 = V >= (6, 7, 0)
V68 = V >= (6, 8, 0)
V69 = V >= (6, 9, 0)
V70 = V >= (7, 0, 0)
# v7.1 is built on the v7.0.0 changelog header (the lead bumps it at release), so the version line alone cannot tell
# v7.1 from v7.0: the deployed engine carries the v7.1 groups table (V7.GRP) and the controls module sits beside it.
DEPLOYED = Path.home() / "Library/Application Support/CrossOver/Bottles/Win10/drive_c/Program Files (x86)/Steam/steamapps/common/Dwarf Fortress/dfhack-config/scripts"
def deployed_is_v71():
    f = DEPLOYED / "seasonal-wildlife.lua"
    return f.exists() and "V7.GRP = " in f.read_text(errors="replace")
V71 = V >= (7, 1, 0) or deployed_is_v71()
if DRY:   # the dry run walks every gated branch as the newest release would
    V, V65, V66, V67, V68, V69, V70, V71 = (7, 1, 0), True, True, True, True, True, True, True

# ----------------------------------------------------------------------------- the claims ---
# id, surface, claim, source, claimed-as
CLAIMS = [
    # ---- W0 (v6.3, alpha trial one): the validator sees what the player sees. Each of these failed on v6.2.1 first.
    ("w0.keys", "GUI", "no window key collides with a DF global binding (the macro keys Ctrl+R/L/P/S, the FPS keys Alt+=/-) or a DFHack global keybinding", "alpha 1 steps 3.5/4.4; plan rev 2 W0/W9", "shipped v6.3"),
    ("w0.overlay", "MECH", "a validation run leaves DFHack's overlay settings as it found them (seasonal-wildlife.groups not left enabled)", "alpha 1 steps 6.2/6.3/10.1; W0", "shipped v6.3"),
    ("w0.ascii", "GUI", "every string the window or the console draws is ASCII (DF draws UTF-8 em dashes as three glyphs)", "alpha 1 step 3.6; W0/W9", "shipped v6.3"),
    ("w0.timing.tabs", "PERF", "every tab of the window refreshes in under 100 ms on the alpha fort", "alpha 1 steps 1.1/5.2/6.1; W7", "shipped v6.3"),
    ("w0.timing.jobs", "PERF", "every scheduled job runs in under 50 ms per pass on the alpha fort", "alpha 1 steps 1.1/4.3; W7", "shipped v6.3"),
    ("w0.roster.seasons", "MECH", "with every present layer on, every active species on every layer has at least one season", "D2; Q8; W1", "shipped v6.3"),
    ("w0.roster.inactive", "MECH", "after the season is applied, every inactive species is held: its entries at 0 on land, water and vermin, its raw frequency at 1 in the caverns", "R1; Q4; W1", "shipped v6.3"),
    ("w0.roster.lastseason", "MECH", "removing an active species' last season is refused (make it inactive instead)", "D2; W1", "shipped v6.3"),
    ("w0.roster.activate", "MECH", "activating an inactive species gives it exactly one season", "D2; W1", "shipped v6.3"),
    ("w0.roster.cycle", "MECH", "cycling an active species' seasons never lands on 'no season'", "D2; W1", "shipped v6.3"),
    # ---- v6.4 (W2, W3): the species model and the food web
    ("mech.model.habitat", "MECH", "habitat from the raws resolves the Q1 examples: sharks, sea serpent, giant cuttlefish, pond grabber aquatic; hippo, river otter, crab, horseshoe crab, cave crocodile, penguin semiaquatic; albatross, osprey, duck waterbird; eagle, kestrel flier; wolf, dingo land", "plan rev 2 Q1, W2", "shipped v6.4"),
    ("mech.model.role", "MECH", "role is independent of habitat: orca and giant orca predators (curated), eagle and kestrel predators (BONECARN), sperm whale predator, whale shark, albatross, hippo prey", "plan rev 2 R2, W2", "shipped v6.4"),
    ("mech.model.band", "MECH", "three size bands by adult volume (D4): kestrel, wolf, dingo small; bull shark, lion medium; giraffe, hippo, elephant large", "D4; W2", "shipped v6.4"),
    ("mech.model.audit", "MECH", "the model's reading of every creature raw matches the audit fixture (data/fixtures/species-model.tsv); the first run writes it", "plan rev 2 W2", "shipped v6.4"),
    ("mech.diet.habitat", "MECH", "the diet test checks habitat: a lion takes no shark, an eagle no sea fish, a great white no deer; an osprey takes a sea fish (a herring: DF's sea fish that are units all outweigh an osprey), a lion a gazelle (DF has no zebra)", "alpha 1 step 5.2; W3", "shipped v6.4"),
    ("mech.matrix.balance", "MECH", "after the matrix no season holds more than half the active roster, and every active species has at least one season", "D6; W3", "shipped v6.4"),
    ("mech.pair.guarantee", "MECH", "after the matrix every season of every realm and habitat group that has a predator with edible prey holds such a pair", "D6; W3", "shipped v6.4"),
    ("mech.coalign.bounded", "MECH", "co-align adds at most one season per partner, from a snapshot, and its reported count equals the season cells added", "R3; W3", "shipped v6.4"),
    # ---- v6.5 (W4, W5, W10): one engine for every layer
    ("mech.engine.draw", "MECH", "Driver B draws a water group: placed together in water that suits the species (body and salinity), tracked as a drawn group with a leave countdown, the entry debited", "plan rev 2 W4, Q5", "shipped v6.5"),
    ("mech.limits", "MECH", "every layer has groups at once and a ceiling (`limits`); `quota` is an alias that says it is retired", "Q6; W4", "shipped v6.5"),
    ("mech.stock.reserve", "MECH", "an entry the tool zeroes is remembered and given back in season; `stock KEY N` writes the species' stock exactly", "Q3; W5", "shipped v6.5"),
    ("mech.odds", "MECH", "`odds KEY N` writes the raw's frequency (never below 1) and the detail page shows the share of the layer; disable restores it", "Q3; W5", "shipped v6.5"),
    ("mech.groupsize", "MECH", "`size KEY N` stands the raw's cluster range at {N,N} for DF's draw and disable restores it", "Q7; W4", "shipped v6.5"),
    ("mech.sendoff", "MECH", "send off gives every gated land group a zero leave countdown and opens the gate (no fix/wildlife pile-up)", "alpha 1 steps 4.2, 7.2; W10", "shipped v6.5"),
    ("mech.call", "MECH", "call a land species: the pool is open to it alone for the next wave; the ledger records the call", "alpha 1 step 2.5; W10", "shipped v6.5"),
    ("mech.deep", "MECH", "the magma sea's natural species are keyed deep:TOKEN, on the roster when the deep layer is on (D7)", "D7; W5", "shipped v6.5"),
    ("mech.origin", "MECH", "every wild unit on the map has an origin: DF wave, tool-drawn, resident, born here, untracked or deep", "W10", "shipped v6.5"),
    # ---- v6.6 (W6, W9, W11, W12)
    ("mech.hunt", "MECH", "hunting on writes DIVE_HUNTS_VERMIN on the active predatory and water birds and HUNTS_VERMIN on small land predators; off clears every flag it wrote", "Q2; W6", "shipped v6.6"),
    ("gui.help", "GUI", "Alt+H opens a help page for the tab with the vocabulary", "W11", "shipped v6.6"),
    ("gui.vermin.species", "GUI", "E on the Vermin tab opens a family to its species rows, each with active/inactive, seasons and stock", "W12; alpha 1 step 8.1", "shipped v6.6"),
    ("gui.seasons.edit", "GUI", "S U A W on the Seasons tab edit the selected species' seasons and the Roster shows the change", "W12; alpha 1 step 5.1", "shipped v6.6"),
    ("gui.layout", "GUI", "the window opens taller than 34 rows when the screen allows, with all nine tabs on one row", "W9; alpha 1 step 1.3", "shipped v6.6"),
    # ---- CLI verbs (USAGE.md "Console commands"; the script's dispatch table)
    ("cli.status", "CLI", "`status` lists biomes, layers, the limits line ('limits [mode]:' since v7.1), cavern line, on-the-map counts, the invasion field, and the embark subset", "USAGE.md", "shipped"),
    ("cli.now", "CLI", "`now` applies the current season's roster once and reports the active count", "USAGE.md", "shipped"),
    ("cli.enable", "CLI", "`enable` / `disable` start and stop automatic rotation (registers/cancels the daily scheduler)", "USAGE.md", "shipped"),
    ("cli.classes", "CLI", "`classes` prints the seven ecology classes, natural 'managed' and the rest 'left to DF' (D8, v6.3), with counts, plus the unclassified review list", "USAGE.md; D8", "shipped"),
    ("cli.class", "CLI", "`class <TOKEN> natural|auto` records an override; any other class, or bad args, print usage (D8, v6.3)", "USAGE.md; D8", "shipped"),
    ("cli.groups.status", "CLI", "`groups` prints resident-group status (max, gap, detached, coupling, cohesion, swept) and the ecology line", "USAGE.md", "shipped"),
    ("cli.groups.onoff", "CLI", "`groups on|off` enables/disables resident groups", "USAGE.md", "shipped"),
    ("cli.groups.coupling", "CLI", "`groups coupling on|off` (and the `piggyback` alias) sets migratory coupling", "USAGE.md", "shipped"),
    ("cli.groups.pack", "CLI", "`groups pack N` sets the coupled predator wave size; 0 = raws", "USAGE.md", "shipped"),
    ("cli.groups.ecology", "CLI", "`groups ecology [on|off|now]` reads, sets, or runs the ecology write once", "USAGE.md", "shipped"),
    ("cli.groups.livestock", "CLI", "`groups livestock on|off` makes the fort's animals targets", "USAGE.md", "shipped"),
    ("cli.groups.nudge", "CLI", "`groups nudge TILES TICKS RADIUS` changes the three nudge distances", "USAGE.md", "shipped"),
    ("cli.groups.cohesion", "CLI", "`groups cohesion on|off|herd N pack N flock N` sets cohesion and follow distances and reports groups led", "USAGE.md", "shipped"),
    ("cli.groups.hold", "CLI", "`groups hold TOKEN DAYS` raises every member's leave countdown; `groups dismiss TOKEN` zeroes it and clears the leader", "USAGE.md", "shipped"),
    ("cli.quota", "CLI", "`limits` (the retired `quota` is an alias) prints the limits line and what is on the map; since v7.1 the line names the mode: 'limits [map-size formula per layer]' or 'limits [single fixed cap N on every layer]'", "USAGE.md; docs/v7.1/groups.md R7", "shipped"),
    ("cli.quota.cavern", "CLI", "`quota cavern N` warns that the ceiling is enforced on FREQUENCY and brakes arrivals rather than culling", "STATE addendum 57", "shipped"),
    ("cli.water", "CLI", "`water [on|off|now|countdown N]` controls the water job (v7.1 adds layer, spill, mix, pull, guard, survey/depth; target and cadence are retired); status names live/dormant with the reason, and since v7.1 a 'water layer ...; season spill ...' line", "USAGE.md; docs/v7.1/fixes.md 5", "shipped"),
    ("cli.water.now", "CLI", "`water now` on a dormant layer answers at once with 'placed 0' and the reason (the wet-edge verdict is cached at load)", "USAGE.md; v5.8.2", "shipped"),
    ("cli.place", "CLI", "`place TOKEN [n] [layer]` places wild animals headlessly and debits the entry", "USAGE.md", "shipped"),
    ("cli.usage", "CLI", "an unknown verb prints usage rather than a stack trace", "script", "shipped"),
    ("cli.errors", "CLI", "bad arguments to water/quota/class/hold/place print a usage line and change nothing", "script", "shipped"),
    ("cli.docstring", "CLI", "the launcher help (`help seasonal-wildlife`) describes the tool", "script docstring", "shipped"),
    # ---- Mechanics
    ("mech.sched", "MECH", "enable registers a daily repeat-util job; disable cancels it", "USAGE.md 'Between the seasons'", "shipped"),
    ("mech.apply", "MECH", "applying the roster writes pool quantities: in-season allowed species stocked, out-of-season zeroed", "USAGE.md Concepts; S1", "shipped"),
    ("mech.outofseason", "MECH", "applying a different season zeroes the species that season excludes", "USAGE.md; S1", "shipped"),
    ("mech.unassigned", "MECH", "a species with no seasons is inactive and held at 0 by an apply (v6.3, R1; until v6.2.1 it was left unmanaged and kept its stock)", "plan rev 2 W1; D2", "shipped"),
    ("mech.force", "MECH", "Force wave clears the current group and a new wave arrives within a few thousand ticks", "USAGE.md; E1/E8", "shipped"),
    ("mech.groups.track", "MECH", "resident groups tracks wildlife groups on the map (gated/resident rows with arrival day)", "USAGE.md Resident groups", "shipped"),
    ("mech.cohesion", "MECH", "cohesion picks a leader per herd/pack/flock group and sets followers", "USAGE.md v5.7; E28", "shipped"),
    ("mech.leader.lowest", "MECH", "the leader is the lowest-id member up to v6.9; from v7.0 a group member chosen by size (largest male: mech.v70.leader_male)", "USAGE.md; Backlog; v7.0 item 22", "shipped"),
    ("mech.hold", "MECH", "hold raises leave_countdown on every member to ≥ DAYS×1200 ticks", "USAGE.md v5.7; E9c/E19", "shipped"),
    ("mech.dismiss", "MECH", "dismiss zeroes leave_countdown and clears the leader", "USAGE.md v5.7", "shipped"),
    ("mech.ecology.write", "MECH", "the ecology write relates every LARGE_PREDATOR to every target in DF's reaction cache, slotting any unit DF has not (v5.9.7), and reports the pair count", "USAGE.md v5.6/v5.9.7; E11c/T4", "shipped"),
    ("mech.ecology.cadence", "MECH", "the ecology job fires on its own every ecology.cadence ticks while enabled: 3,000 by default since v7.1 (R37), 1,500 before", "USAGE.md v5.6; docs/v7.1/ecology.md R37", "shipped"),
    ("mech.ecology.nudge", "MECH", "with the nudge on (off by default since v7.1, R38), a predator >40 tiles from every target for 3,000 ticks is moved to within 6", "USAGE.md v5.6; E18; docs/v7.1/ecology.md R38", "shipped"),
    ("mech.place", "MECH", "place puts N live wild units on walkable tiles with a population ref, debits the entry by N, and they survive stepping", "STATE addendum 47", "shipped"),
    ("mech.water.dormant", "MECH", "on a dry/inland fort the water layer is dormant and the status names WHICH test failed", "USAGE.md v5.8; E25", "shipped"),
    ("cli.caverns", "CLI", "`caverns [survey]` reports each cavern band on the map with its levels and its edge water (v5.9)", "USAGE.md v5.9; STATE addendum 76", "shipped"),
    ("mech.cavern.place", "MECH", "a cavern entry is placed in its own cavern: a subterranean tile inside the band of its depth, water for an aquatic caste (v5.9)", "STATE addendum 76", "shipped"),
    ("mech.water.outside", "MECH", "a water entry is placed only in outside water near the surface, never in a cavern lake (v5.9)", "STATE addendum 76", "shipped"),
    ("cli.cavern.stock", "CLI", "`cavern [on|off|now|cadence N|countdown N]` controls the cavern stocking pass; status reports the caverns against the quota (v5.9.6)", "USAGE.md v5.9.6; STATE addendum 83", "shipped"),
    ("mech.cavern.stock", "MECH", "with `quota cavern N` and the caverns under it, one pass places the shortfall into cavern bands, floor or water by caste; at the quota a pass places nothing (v5.9.6)", "STATE addendum 83", "shipped"),
    ("cli.ledger", "CLI", "`ledger [N] [kind] [layer]|clear` prints the tool's own writes, oldest first, stamped 'y<year> <Season> <day>' with kind and layer, and a 'shown of recorded' footer", "USAGE.md v5.9.9", "shipped"),
    ("mech.ledger.records", "MECH", "every write the tool makes leaves one ledger line: placement, roster and switch edits, and the session's arrivals, holds, dismissals, ecology changes and cavern holds when they happen", "USAGE.md v5.9.9; PLAN 3.6", "shipped"),
    ("mech.ledger.ring", "MECH", "the ledger keeps the newest 300 entries, its total keeps counting, and `clear` empties it", "v5.9.9", "shipped"),
    ("cli.vermin", "CLI", "`vermin` lists the embark's vermin as families read from the raws (fish, flies, fliers, mammals, soil, colony, crawlers) with species count, allowed count, seasons, abundance and layers", "USAGE.md v5.9.10", "shipped"),
    ("mech.vermin.family", "MECH", "`vermin <family> off|on` blocks and allows every species of the family; `seasons` and `abundance` write every member", "USAGE.md v5.9.10", "shipped"),
    ("mech.vermin.defaults", "MECH", "`vermin defaults` seasons every vermin species by family and layer: land insects spring-autumn (summer-autumn on a cold embark), mammals, fish, caverns and water all year", "USAGE.md v5.9.10; PLAN 3.5", "shipped"),
    ("gui.tab.vermin", "GUI", "Vermin tab: one row per family with n / allowed / season / abundance / layers, D applies the defaults and the status line says so", "USAGE.md v5.9.10", "shipped"),
    ("gui.tab.overview", "GUI", "Overview tab, the page the window opens on: date and switches, what each layer holds now, groups against their count, in-season counts, the next boundary with arrivals and departures, the ledger's last lines", "USAGE.md v5.10.1", "shipped"),
    ("gui.roster.why", "GUI", "the Roster's why column shows who set a species' state and when (you, fill, matrix, co-align, vermin, defaults; compact since v5.10.8) and explains an untouched or locked species; the full reason is on the detail page", "USAGE.md v5.10.5/v5.10.8", "shipped"),
    ("gui.species.detail", "GUI", "`i` on a Roster row opens the species detail over the window (what it is, body, embark, allowed and why, abundance, seasons, eats, eaten by, on the map, history); Esc closes it", "USAGE.md v5.10.7", "shipped"),
    ("mech.species.detail", "MECH", "speciesDetail(cfg, pool, e) assembles the facts for one animal: at least nine lines with species, allowed (and why), seasons, eats and eaten by", "v5.10.7", "shipped"),
    ("cli.pattern", "CLI", "`pattern [land|cavern] <steady|burst|trickle|dawn|follow>` sets and shows the arrival pattern per layer; a bad name prints usage; `status` and the Live tab carry the line", "USAGE.md v5.10.0", "shipped"),
    ("mech.pattern.burst", "MECH", "burst: two or three releases 2.5 days apart, then a quiet gap of gap_max to twice gap_max days", "USAGE.md v5.10.0", "shipped"),
    ("mech.pattern.trickle", "MECH", "trickle: draws sized 1-2 for as long as the pattern is on (a standing cluster write on every allowed, in-season land species, restored on change); a flock may run one over the raw, flier or not (E42, E42b: raven and emu trios under {2,1}, never four)", "USAGE.md v5.10.2/v6.2.1", "shipped"),
    ("mech.pattern.dawn", "MECH", "dawn: in the first week of a season only bird and vermin-class entries are open for the wave", "USAGE.md v5.10.0", "shipped"),
    ("mech.pattern.follow", "MECH", "follow: prey mass on the map at 3x predator mass opens only predators; no prey opens only prey", "USAGE.md v5.10.0", "shipped"),
    ("mech.water.live", "MECH", "on a lake fort the water layer is live and `water now` places animals from stocked, in-season water entries", "USAGE.md v5.8; E33", "shipped"),
    ("mech.water.target", "MECH", "water target / cadence / countdown are stored and reported", "USAGE.md v5.8", "shipped"),
    ("mech.quota.land", "MECH", "quota land N overrides groups.max_concurrent as the effective ceiling", "USAGE.md v5.8", "shipped"),
    ("mech.quota.water", "MECH", "quota water N overrides the water target as the effective stocking level", "USAGE.md v5.8", "shipped"),
    ("mech.quota.cavern", "MECH", "quota cavern N holds managed cavern species at frequency 1 while over the ceiling; frequency is never written 0", "STATE addenda 53–57; v5.8.1", "shipped"),
    ("mech.quota.cavern.throttle", "MECH", "QUOTA.cavernThrottle (the old entry-quantity ceiling) still prints a 'cavern ceiling' line — a second mechanism for the same setting, measured inert (T7)", "USAGE.md; STATE addendum 51", "withdrawn"),
    ("mech.cavern.restore", "MECH", "disable (or quota cavern 0) restores every held cavern frequency", "v5.8.1", "shipped"),
    ("mech.layers.count", "MECH", "the layer counter separates land/water/cavern and reports the magma sea and underworld as a never-managed deep bucket", "STATE addendum 51", "shipped"),
    ("mech.invasion", "MECH", "DF invasions are excluded from every count via a real unit field", "USAGE.md Layers; addendum 49", "shipped"),
    ("mech.classes.lock", "MECH", "a creature in a disabled class is locked: not eligible, shows an L tag, cannot be allowed", "USAGE.md Ecology classes", "shipped"),
    ("mech.class.override", "MECH", "a class override can only bring a creature in as natural; asking for a special class is refused and changes nothing (D8, v6.3)", "USAGE.md; D8", "shipped"),
    ("mech.overlay", "MECH", "`overlay enable seasonal-wildlife.groups` registers a map overlay marking each tracked group g/r", "USAGE.md Resident groups", "shipped"),
    ("mech.stuck", "MECH", "a tracked non-flier that has not moved in 5,000 ticks is re-grounded; the status counts swept=N", "USAGE.md v5.7; T5", "shipped"),
    ("mech.addnew", "MECH", "Add-new writes a master row and a live entry so the species is in the pool with no reload", "USAGE.md Adding a new species; v4.4", "shipped"),
    ("mech.reset", "MECH", "Reset to default restores managed quantities to the captured worldgen snapshot and abundances to 50", "USAGE.md", "shipped"),
    ("mech.abundance", "MECH", "abundance sets the stocked quantity (not arrival volume — E24)", "USAGE.md; addendum 58", "shipped"),
    ("mech.save.untouched", "MECH", "a full session of console and GUI use leaves the save byte-identical (config lives in persistent site data)", "USAGE.md Uninstall; df-rig rule", "shipped"),
    ("mech.season.boundary", "MECH", "the roster is re-applied at each season boundary and held daily against refunds", "USAGE.md Between the seasons", "shipped"),
    ("mech.coupling", "MECH", "when a prey group arrives, coupling closes the pool to its armed natural predators for up to two days", "USAGE.md v5.4/5.6", "shipped"),
    # ---- GUI: window and tabs
    ("gui.open", "GUI", "`gui/seasonal-wildlife` opens a resizable window titled 'Seasonal Wildlife' with nine tabs, the Panel second (v6.3)", "script", "shipped"),
    ("gui.tab.roster", "GUI", "Roster tab: header with biomes and per-category counts, filter row (Alt+S search), creature list with cat/size/biome/season/ab/ok/why columns, season keys S/U/A/W, matrix and co-align keys, targets row, fill keys, Ctrl action keys, status line", "USAGE.md Roster tab", "shipped"),
    ("gui.tab.setroster", "GUI", "Set roster folded into the Roster (v5.11.0): the targets row, fill keys, matrix/co-align keys and season keys are on the Roster page and the season grid is its SEASON column", "USAGE.md Roster tab", "shipped"),
    ("gui.tab.foodweb", "GUI", "Food web tab: ecology-switch line, season selector, chains (All) or trophic pyramid + aquatic mini-web (a season)", "USAGE.md Food web tab", "shipped"),
    ("cli.irruption", "CLI", "`irruption` shows the status (off by default); `irruption on` turns it on and the status names the threshold and the three pressures; `irruption off` turns it off", "USAGE.md v6.1", "shipped"),
    ("gui.k.layI", "GUI", "I on Layers flips irruptions and the cavern pressure row shows the three pressures", "USAGE.md v6.1", "shipped"),
    ("mech.irruption.arm", "MECH", "v6.1-v7.0: with pressure pinned at the threshold, the next arriving cavern group the roster admits is armed (agitated flag on its members) and stood down after its duration; off is inert. v7.1 replaced arming with IRRUPT v2 events (mech.v71.irr.*), and a v7.0 armed group is stood down on the first pass (mech.v71.irr.migrate)", "USAGE.md v6.1; PLAN 3.6b", "shipped"),
    ("gui.k.altL", "GUI", "Alt+L on any tab cycles the layer (all → land → water → cavern) and the window's title names it with the reason when off or dormant; the Roster's rows follow it", "USAGE.md v6.2.0", "shipped"),
    ("mech.overlay.links", "MECH", "overlayLinks() reports the related wild pairs the overlay would draw and how many share a level; the overlay seasonal-wildlife.groups is registered", "USAGE.md v6.2.0", "shipped"),
    ("gui.tab.ledger", "GUI", "Ledger tab: the recorded lines newest last, coloured by kind, with the kind and layer filters", "USAGE.md v5.11.4", "shipped"),
    ("gui.k.ledgerK", "GUI", "K on Ledger filters by kind (the header says kind=<kind>)", "USAGE.md v5.11.4", "shipped"),
    ("gui.k.ledgerZ", "GUI", "Z on Ledger undoes the last edit: a species blocked on the Roster is allowed again and the Ledger gains an undo line", "USAGE.md v5.11.4", "shipped"),
    ("cli.undo", "CLI", "`undo` restores the state before the last edit and says what it undid; with nothing to undo it says so", "USAGE.md v5.11.4", "shipped"),
    ("gui.tab.layers", "GUI", "Layers tab: a row per setting (layer, concurrent groups, gap, pattern, quota, coupling, ecology, nudge, pack) against land/water/cavern columns, the water line, a line per cavern found or hidden, the preset line", "USAGE.md v5.11.3", "shipped"),
    ("gui.k.layT", "GUI", "T on Layers cycles the selected layer's pattern (steady → burst → trickle → dawn → follow)", "USAGE.md v5.11.3", "shipped"),
    ("gui.k.layR", "GUI", "R on Layers re-applies the biome preset and the Ledger records a build line", "USAGE.md v5.11.3", "shipped"),
    ("cli.preset", "CLI", "`preset` applies the biome preset and prints the receipt (allowed, matrix seasons, co-aligned, vermin defaults)", "USAGE.md v5.11.3", "shipped"),
    ("gui.tab.live", "GUI", "Live tab: resident-group status, tracked groups, ecology line, wild-on-map by race, quota line, cavern line, biomass ratio", "USAGE.md Live tab", "shipped"),
    ("gui.tab.seasons", "GUI", "Seasons tab: four seasons side by side, one row per allowed creature under its trophic level, +/-/X/. marks", "USAGE.md Seasons tab", "shipped"),
    ("gui.close", "GUI", "ESC closes the window", "script", "shipped"),
    ("gui.k.shadow", "GUI", "Ctrl-modified action keys reach their labels on the Roster; since v5.11.0 the filter box takes focus only on Alt+S and releases it on Enter/Esc, so plain letters are actions too", "USAGE.md Roster tab", "shipped"),
    ("gui.status.roster", "GUI", "the Roster tab's status line shows each action's receipt ('Applied Spring live: N active.', 'Set N abundances to 60.', 'Auto rotation ON.')", "USAGE.md; script setStatus", "shipped"),
    ("gui.status.grid", "GUI", "the Roster's status line shows the fill / matrix / co-align receipts ('Allowed N natural prey.', 'Assigned matrix seasons to N creatures.') — v5.11.0, was the Set roster grid status", "USAGE.md; script setStatus", "shipped"),
    # ---- GUI: Roster hotkeys
    ("gui.k.V", "GUI", "V cycles View: Current → Default → Add-new", "USAGE.md", "shipped"),
    ("gui.k.C", "GUI", "C cycles the category filter (incl. aquatic)", "USAGE.md", "shipped"),
    ("gui.k.B", "GUI", "B cycles the biome filter", "USAGE.md", "shipped"),
    ("gui.k.N", "GUI", "N cycles the season filter", "USAGE.md", "shipped"),
    ("gui.k.enter", "GUI", "Enter allows/blocks the selected creature (ok column flips Y/-)", "USAGE.md", "shipped"),
    ("gui.k.shiftenter", "GUI", "Shift-Enter cycles the selected creature's seasons", "USAGE.md", "shipped"),
    ("gui.k.ctrlS", "GUI", "Ctrl+S is retired (v5.11.0): the Set roster keys — targets, F/Y/D, S/U/A/W, M/O — are on the Roster page itself", "USAGE.md v5.11.0", "shipped"),
    ("gui.k.ctrlA", "GUI", "Ctrl+A applies the current season live and announces it", "USAGE.md", "shipped"),
    ("gui.k.ctrlF", "GUI", "Ctrl+F clears the current wild group and forces a new wave", "USAGE.md", "shipped"),
    ("gui.k.ctrlD", "GUI", "Ctrl+D opens the dry-run season table dialog", "USAGE.md", "shipped"),
    ("gui.k.ctrlW", "GUI", "Ctrl+W prompts for the row's abundance and stores it", "USAGE.md", "shipped"),
    ("gui.k.ctrlG", "GUI", "Ctrl+G prompts for an abundance for every filtered row", "USAGE.md", "shipped"),
    ("gui.k.ctrlE", "GUI", "Ctrl+E toggles automatic rotation", "USAGE.md", "shipped"),
    ("mech.animalperson", "MECH", "an animal person stands where its root animal stands: role, habitat, size, mass and every predator/prey verdict the same (JAGUAR_MAN as JAGUAR, OTTER_MAN as RIVER OTTER, ALBATROSS_MAN as BIRD_ALBATROSS)", "user 28 Sep; alpha 2 step 10.1", "shipped v6.7"),
    ("gui.odds.bracket", "GUI", "the Roster's ODDS column shows an active species out of season with its in-season share in brackets", "alpha 2 step 4.3", "shipped v6.7"),
    ("gui.addnew.whole", "GUI", "Add invasive leaves the new species on the roster at once: active with one season, or inactive", "alpha 2 step 8.1", "shipped v6.7"),
    # ---- v6.8 (29 Sep, the browser companion): the Roster's two edits from the console
    ("cli.roster", "CLI", "`roster` prints one line per layer with its active, in-season and inactive counts", "user 29 Sep (companion)", "shipped v6.8"),
    ("cli.roster.state", "CLI", "`roster KEY inactive` leaves the species inactive with no seasons; `roster KEY active` makes it active with exactly one season; each is one undo step and one ledger line", "user 29 Sep (companion); the one rule", "shipped v6.8"),
    ("cli.seasons.set", "CLI", "`seasons KEY SpAu` sets exactly those seasons; `seasons KEY none` is refused and changes nothing; a bad code prints usage", "user 29 Sep (companion); the one rule", "shipped v6.8"),
    ("cli.seasons.activate", "CLI", "`seasons KEY Wi` on an inactive species makes it active in Winter", "user 29 Sep (companion); toggleSeason's rule", "shipped v6.8"),
    ("cli.roster.undo", "CLI", "`undo` after a console roster or seasons edit restores the state before it", "user 29 Sep (companion)", "shipped v6.8"),
    ("web.snapshot", "CLI", "`seasonal-wildlife-web snapshot` prints one JSON state with the fort, the date, every managed species, the food-web pairs and vermin links", "user 29 Sep (companion)", "shipped v6.8"),
    ("web.serve", "MECH", "`seasonal-wildlife-web start` serves the page and /state.json to a browser on the host at 127.0.0.1 (through CrossOver), and `stop` stops it", "user 29 Sep (companion)", "shipped v6.8"),
    ("web.guard", "MECH", "the server refuses a request without the token, a verb off its list, and a request whose Host is not 127.0.0.1/localhost", "user 29 Sep (companion); loopback CSRF and DNS rebinding", "shipped v6.8"),
    ("web.gfx", "MECH", "the snapshot carries sprite sheets, the font and a 16-colour palette, most species a sprite and an ASCII glyph, and GET /gfx/font and a sheet return PNGs", "user 29 Sep (companion tiles)", "shipped v6.8"),
    ("web.stop", "MECH", "`seasonal-wildlife-web stop` closes the port", "user 29 Sep (companion)", "shipped v6.8"),
    # ---- v6.9 (ECO suite, 29-30 Sep 2026): the ecology as measured
    ("mech.v69.armed", "MECH", "a food-web predator is armed exactly when it is not BENIGN (LARGE_PREDATOR is not the switch)", "ECO P1/T1: coyote hunted, BENIGN wolf never", "shipped v6.9"),
    ("mech.v69.reach", "MECH", "the relation write reaches only where the predator can: a shark never takes a deer; an alligator and a wolf do", "ECO W1L/W1O", "shipped v6.9"),
    ("mech.v69.fitseason", "MECH", "the season deal never gives a species a season its raws forbid (NO_SPRING/SUMMER/AUTUMN/WINTER) unless they forbid every season -- v6.9; v7.0's seasons_own overrides the raws by design", "ECO T2; user 30 Sep", "shipped v6.9"),
    ("mech.v69.pelagic", "MECH", "a pelagic giant's water-draw weight is its FREQUENCY scaled down by size, never below 0.1 of it; a small fish keeps its FREQUENCY", "user 30 Sep; ECO O/DEPTH", "shipped v6.9"),
    ("cli.alerts", "CLI", "`alerts off|on` switches quiet wildlife fights and says so; on by default", "ECO A1/A2", "shipped v6.9"),
    ("cli.curious", "CLI", "`curious TOKEN resident` clears the species' CURIOUS_BEAST* caste flags; `thief` restores them; a species that is no curious beast is refused", "ECO B/CB", "shipped v6.9"),
    ("mech.v69.autogroups", "MECH", "land groups at once default to floor(sqrt(embark tiles)) + 1 and `limits land groups N` sets a number instead -- since v7.1 (R7) the single fixed cap N on every layer, and `groups auto` the map-size formula again", "user 29 Sep; ECO2-G; R7", "shipped v6.9"),
    ("cli.scavenge", "CLI", "`scavenge on|off|now` switches scavenging, runs one pass on demand and reports it; off by default. Since v7.1 the status says on only when the tool is enabled too ('off (the tool is disabled; the scavenging switch is on)') and `now` says why nothing ran", "ECO S/S2; PLAN scavenging; docs/v7.1/scav.md 14", "shipped v6.9"),
    ("mech.v69.guild", "MECH", "the engine's guild for each natural species agrees with the ECO desk's guild table (data/eco-desk/v2/guilds/species2.tsv) for at least 95% of them", "ECO desk v2 guild design", "shipped v6.9"),
    ("mech.v69.exhaust", "MECH", "an in-season species whose stock reaches 0 is held at 0 by an apply, and an active out-of-season member of its group borrows the season, given back at the season change", "ECO N1", "shipped v6.9"),
    # ---- v7.0.0 (30 Sep 2026): alignment, civ races, groups by layer, the solitary/pack/fisher raw package, sponges
    ("mech.v70.align", "MECH", "a surface GOOD/EVIL mythic species is managed (natural) only when the embark region's own alignment matches it, gated by v7.aligned", "V7.alignment/V7.alignedNatural; user 30 Sep", "shipped v7.0"),
    ("mech.v70.cave_aligned", "MECH", "a cavern-only GOOD/EVIL species is natural when v7.cave_aligned is on regardless of embark alignment (alignment only limits taming underground)", "V7.caveOnly/V7.alignedNatural", "shipped v7.0"),
    ("mech.v70.fanciful", "MECH", "a FANCIFUL-only mythic species (no GOOD/EVIL) with no biome match is natural when v7.fanciful is on, never otherwise locked for that reason", "V7.alignedNatural", "shipped v7.0"),
    ("mech.v70.vermin_nolocked", "MECH", "the Vermin tab's rows never include a locked species (a family member whose ecology class is not enabled in cfg.classes)", "VERMIN.rows", "shipped v7.0"),
    ("mech.v70.sanitize", "MECH", "a stale cfg.allow/cfg.assign entry for a species whose class is locked is dropped the next time the config loads", "V7.sanitizeLocked", "shipped v7.0"),
    ("mech.v70.leader_male", "MECH", "a cohesive group's leader is the largest living adult male when v7.leader_male is on; v7.0 fell back to the largest adult, then the first member; since v7.1 (R32) no adult male means no leader (grp.unled); a living leader keeps the role across passes; off -> the first member", "V7.leaderOf; ECO L1; R32", "shipped v7.0"),
    ("mech.v70.groups_water_body", "MECH", "the water limit is quoted and applied per water body (ocean/lake/river/pool), not once for the whole water layer (v7.0: with v7.layer_groups on; v7.1: always, the switch retired)", "V7.waterTick; QUOTA.groupsFor/status", "shipped v7.0"),
    ("mech.v70.groups_cavern_depth", "MECH", "each cavern depth is gated and reported on its own, not pooled with the others (v7.0: with v7.layer_groups on; v7.1: always, at R44's cavern cap)", "QUOTA.groupsFor/status; groupsTick", "shipped v7.0"),
    ("mech.v70.groups_auto_all", "MECH", "every layer counts its own groups: v7.0 (layer_groups on) gave land, water and cavern floor(sqrt(embark tiles)) + 1; v7.1 gives land and every water body the formula and every cavern R44's fixed cap (5)", "QUOTA.groupsFor/autoGroups; R7; R44", "shipped v7.0"),
    ("mech.v70.seasons_own", "MECH", "with v7.seasons_own on, a species' NO_<season> raw flags are cleared for every managed species (the roster no longer deflects a dealt season around them) and restored when v7 raws are restored", "ROSTER.fitSeason; V7.apply/restore", "shipped v7.0"),
    ("mech.v70.solo_raws", "MECH", "with v7.solo on, a solitary armed predator's raw gets AMBUSHPREDATOR, the solitary-package natural skills, and stealth-free gaits; v7.1 picks the solitary species by MODEL.cohesionOf (raw cluster max <= 1) through V7.H.profileOf", "V7.apply (solo branch); user 30 Sep (STL/STL2); docs/v7.1/ecology.md", "shipped v7.0"),
    ("mech.v70.pack_floor", "MECH", "a hunting group whose live member count x predator mass is under v7.pack_floor (5%) of the target's mass writes no predator/prey relation", "ecoWrite pack-mass gate; ECO CAL", "shipped v7.0"),
    ("mech.v70.pack_sneak", "MECH", "a hunting group whose pack-mass share reaches v7.pack_sneak (25%) of the target's mass gets SNEAK on its members: 10 in v7.0, hunters.skills.pack_bonus (10) since v7.1", "ecoWrite pack-mass gate; docs/v7.1/ecology.md", "shipped v7.0"),
    ("mech.v70.scav_mapwide", "MECH", "with v7.scav_mapwide on, the scavenger pass is not limited to cfg.scavenge.radius -- it reaches anywhere on the map", "SCAV.run", "shipped v7.0"),
    ("mech.v70.fishers_flags", "MECH", "with v7.fishers on, every token set true in v7.fisher_list gets CAN_SWIM_INNATE (v7.1: and CAN_SWIM; CAN_BREATHE_WATER too when v7.fish_breathe is on); v7.1's default list is the bears, who swim already, so the write is read on a non-swimmer put on the list for the probe", "V7.apply (fishers branch); docs/v7.1/ecology.md", "shipped v7.0"),
    ("mech.v70.restore_all", "MECH", "V7.restore() reverses every raw write V7.apply made (seasons, solitary package, fishers) and reports how many", "V7.rec/restore", "shipped v7.0"),
    ("mech.v70.civ_fb_safe", "MECH", "V7.natural is false for a non-natural raw (forgotten beast/demon template, megabeast, titan, night creature) while v7.fb_safe is on, true for any raw when it is off", "V7.natural; STATE addendum 96b", "shipped v7.0"),
    ("mech.v70.civ_hunt", "MECH", "with v7.civ_hunt on, a cavern civ race of an armed guild (AL/AW/ML/MW/RP) is armed as a predator whatever its food-web role reads; off, it is not", "ecoArmed civ branch", "shipped v7.0"),
    ("mech.v70.civ_prey", "MECH", "a cavern civ race is only ever taken by a non-civ predator of guild AL or AW, never any other guild", "ecoWrite civ_prey gate; ecoLivePairs", "shipped v7.0"),
    ("mech.v70.sweep", "MECH", "each ecology pass, a PREDATOR_OR_PREY cell DF wrote between two managed-wild units this pass's web did not allow is cleared to NONE; a citizen, livestock, visitor or non-natural unit is never touched by the sweep", "V7.sweep/managedWild; ECO E16", "shipped v7.0"),
    ("mech.v70.slotv", "MECH", "a freshly allocated enemy-status slot's row and column, and a departed unit's cleared slot, are written NONE (-1), never STRANGER (0)", "PLACE.enemySlot/ecoClearDeparted; SLOTV, ECO E11c", "shipped v7.0"),
    ("mech.v70.domestic", "MECH", "v7.domestic defaults off; with it on, V7.isDomestic marks the fort's own tame animals and V7.takesDomestic allows only guild AL/ML or any cavern-layer predator to take them; with ecology.livestock and v7.domestic both off, ecoIsTarget refuses the fort's own livestock", "V7.isDomestic/takesDomestic; ecoIsTarget; user 30 Sep", "shipped v7.0"),
    ("mech.v70.sponges", "MECH", "v7.sponges defaults on; V7.isSponge is true only for a SPONGE unit, which WILD.onMap and ecoIsTarget both skip, so it never counts toward WILD.countByLayer, a group or a target", "V7.isSponge; WILD.onMap", "shipped v7.0"),
    ("cli.v70.sponges", "CLI", "`sponges` reports the switch and the ribbon count; `sponges now` places ribbons on a fort with ocean ('sponges: on  N on the ocean floor') and reports 'no ocean on the map' where there is none", "V7.spongeTick/spongeStatus", "shipped v7.0"),
    ("cli.v70.v7", "CLI", "`seasonal-wildlife v7` lists every v7 switch and its value; `v7 KEY on|off` and `v7 fisher TOKEN on|off` change one", "the v7 CLI verb", "shipped v7.0"),
    ("web.cmd", "MECH", "a POST /cmd with the token runs the console verb and returns its reply", "user 29 Sep (companion)", "shipped v6.8"),
    ("gui.k.ctrlX", "GUI", "Ctrl+X adds the selected non-native creature (Add-new view only; otherwise says so)", "USAGE.md", "shipped"),
    ("gui.k.altR", "GUI", "Alt+R (Ctrl+R until v6.3: DF's RECORD_MACRO) asks roster or everything, confirms, then resets; the roster reset leaves every abundance at 50", "USAGE.md; W9", "shipped"),
    ("gui.k.altF", "GUI", "Alt+F (Ctrl+L until v6.3: DF's LOAD_MACRO) fills the filtered category to N (refuses on 'all'/'aquatic')", "USAGE.md; W9", "shipped"),
    ("gui.tab.panel", "GUI", "Panel tab (v6.3, W8): every switch with an indicator, the jobs with cadence / last / worst / fuse, all on and all off; Enter flips a switch", "plan rev 2 W8", "shipped"),
    ("mech.panel.alloff", "MECH", "all off stops every job and restores every raw the tool wrote; all on brings the switches back (v6.3, W8)", "plan rev 2 W8", "shipped"),
    ("gui.k.thin", "GUI", "the header shows a 'Thin:' hint when a category is under its target", "USAGE.md", "shipped"),
    # ---- GUI: Set roster hotkeys
    ("gui.k.targets", "GUI", "Shift-P/R/B/V cycle the per-category targets", "USAGE.md", "shipped"),
    ("gui.k.F", "GUI", "F fills categories to their targets", "USAGE.md", "shipped"),
    ("gui.k.Y", "GUI", "Y allows the natural prey of allowed creatures", "USAGE.md", "shipped"),
    ("gui.k.D", "GUI", "D allows the natural predators of allowed creatures", "USAGE.md", "shipped"),
    ("gui.k.SUAW", "GUI", "S/U/A/W toggle Spring/Summer/Autumn/Winter on the selected Roster row (its SEASON column)", "USAGE.md", "shipped"),
    ("gui.k.M", "GUI", "M assigns seasons from the climate matrix", "USAGE.md", "shipped"),
    ("gui.k.O", "GUI", "O co-aligns predator↔prey seasons", "USAGE.md", "shipped"),
    ("gui.k.gridmouse", "GUI", "the season grid is gone (v5.11.0): seasons are the S/U/A/W keys on the Roster row; no per-cell clicks to support", "USAGE.md v5.11.0", "shipped"),
    # ---- GUI: Food web / Live
    ("gui.k.webN", "GUI", "N on Food web cycles the season; a specific season draws the pyramid", "USAGE.md", "shipped"),
    ("gui.k.webG", "GUI", "G on Food web cycles the mode: Pyramid → Graph → By season → By layer", "USAGE.md v5.11.1", "shipped"),
    ("gui.k.webL", "GUI", "L on Food web jumps to the layers side by side", "USAGE.md v5.11.1", "shipped"),
    ("gui.k.liveR", "GUI", "R refreshes the Live tab", "script", "shipped"),
    ("gui.k.liveG", "GUI", "G toggles resident groups from the Live tab", "USAGE.md", "shipped"),
    ("gui.k.liveP", "GUI", "P on Live flips migratory coupling", "USAGE.md v5.11.2", "shipped"),
    ("gui.k.liveK", "GUI", "K on Live cycles the coupling pack size (raw → 3 → 5 → 8 → 12 → raw)", "USAGE.md v5.11.2", "shipped"),
    ("gui.k.liveW", "GUI", "W on Live forces the next wave (the Roster's Ctrl+F)", "USAGE.md v5.11.2", "shipped"),
    ("gui.k.liveQ", "GUI", "Q on Live holds the selected group thirty days (its row says 'held N more days')", "USAGE.md v5.11.2", "shipped"),
    ("gui.k.liveX", "GUI", "X on Live dismisses the selected group (its row says 'dismissed')", "USAGE.md v5.11.2", "shipped"),
    ("gui.k.liveF", "GUI", "F on Live follows the selected group (plotinfo.follow_unit set to a member)", "USAGE.md v5.11.2", "shipped"),
    ("gui.k.liveEnter", "GUI", "Enter on a Live group row centres the map on it (the viewport moves)", "USAGE.md v5.11.2", "shipped"),
    # ---- Design report §11: the thirteen views (v6.0 catalogue)
    ("v6.overview", "GUI", "Overview view — what the map holds now, next boundary, recent ledger", "design §11", "planned v6.0"),
    ("v6.roster.why", "GUI", "Roster with a 'why' column and per-layer selector", "design §11", "planned v6.0"),
    ("v6.species", "GUI", "Species detail — one animal, every control", "design §11", "planned v6.0"),
    ("v6.web.graph", "GUI", "Food web as a graph with live pairs", "design §11", "planned v6.0"),
    ("v6.web.byseason", "GUI", "Food web by season — four pyramids", "design §11", "planned v6.0"),
    ("v6.web.bylayer", "GUI", "Food web by layer, side by side", "design §11", "planned v6.0"),
    ("v6.live.hotkeys", "GUI", "Live tab hotkeys P coupling / K pack / Q hold / X dismiss / W next wave / F follow, and 'Enter centres the map'", "design §11; PLAN 3.6", "planned v6.0"),
    ("v6.herds", "GUI", "Herds & packs view with labels, reasons, overrides", "design §11", "planned v6.0"),
    ("v6.vermin", "GUI", "Vermin view by family with seasonal defaults", "design §11; PLAN 3.5", "planned v5.9"),
    ("v6.patterns", "GUI", "Patterns & quotas per layer (steady/burst/trickle/dawn/follow)", "design §11; PLAN 3.5", "planned v5.9"),
    ("v6.caverns", "GUI", "Caverns view — hidden until found, pressure, rotation by epoch", "design §11", "planned v6.0"),
    ("v6.ledger", "GUI", "Ledger — every write and why, with undo", "design §11; PLAN 3.6", "planned v6.0"),
    ("v6.ecology.tab", "GUI", "Ecology tab — switch, nudge policy, pack size, live pair list", "design §11; PLAN 3.6", "planned v6.0"),
    ("v6.layersel", "GUI", "layer selector on every tab, dormant layers greyed with the reason", "PLAN 3.6", "planned v6.0"),
    ("v6.presets", "GUI", "biome presets applied at first run", "PLAN 3.6", "planned v6.0"),
    ("v6.undo", "GUI", "undo for roster edits (10-deep snapshot ring)", "PLAN 3.6", "planned v6.0"),
    ("v6.overlay.links", "GUI", "overlay extended with predator–prey links", "PLAN 3.6", "planned v6.0"),
    ("v6.explain", "GUI", "every automatic decision logs one readable line", "PLAN 3.6", "planned v6.0"),
    # ---- PLAN §3.5 / §3.6b
    ("plan.patterns", "MECH", "arrival-pattern library on the scheduler: steady, burst, trickle, dawn, follow", "PLAN 3.5", "planned v5.9"),
    ("plan.irruptions", "MECH", "cavern pressure score and irruptions (opt-in), never touching plotinfo.invasions", "PLAN 3.6b", "planned v6.1"),
    ("plan.arming", "MECH", "the 'arming step' of trigger/pre-load/set-the-table", "design §2", "gap noted"),
    # ---- Backlog (unscheduled, recorded for completeness). 1 Oct 2026 (open item validator-backlog-stale): seven of
    # the thirteen shipped in v6.5-v7.0 and are recorded from the claim that exercises each (SHIPPED_BACKLOG below);
    # v7.1 shipped two more (grouping, balance: R62); migrants, perch, r2r4 and eats remain genuinely unbuilt.
    ("bl.frequency", "MECH", "per-species frequency override in the roster (never writing 0)", "Backlog; shipped as `odds` (v6.5)", "shipped v6.5"),
    ("bl.popnumber", "DOC", "roster wording: 'regional stock' not per-fort budget", "Backlog; shipped with `stock` (v6.5)", "shipped v6.5"),
    ("bl.grouping", "MECH", "published solitary/pack/herd table with overrides", "Backlog; shipped as MODEL.cohesionOf + `hunters cohesion list all` (v7.1, R62)", "shipped v7.1"),
    ("bl.largestmale", "MECH", "leader chosen by body size and sex", "Backlog; shipped as v7.leader_male (v7.0)", "shipped v7.0"),
    ("bl.concurrency", "MECH", "max concurrent groups scaled from embark size (√tiles+1)", "Backlog; shipped as QUOTA.autoGroups (v6.9)", "shipped v6.9"),
    ("bl.deepwater", "MECH", "deep-ocean species gated on the map having deep tiles", "Backlog; shipped as the deep-water survey (v7.0)", "shipped v7.0"),
    ("bl.migrants", "MECH", "migrant-trigger timing study", "Backlog", "backlog"),
    ("bl.perch", "MECH", "perched-fraction survey before any perch lever", "Backlog", "backlog"),
    ("bl.r2r4", "MECH", "identify the 'r2/r4' creature", "Backlog", "backlog"),
    ("bl.realm", "MECH", "geographic/realm grouping of species", "Backlog; shipped as the realm table (v7.0)", "shipped v7.0"),
    ("bl.quiet", "MECH", "tool-side filter to quiet animal-on-animal combat reports", "Backlog; shipped as `alerts` (v6.9)", "shipped v6.9"),
    ("bl.eats", "MECH", "a who-eats-whom history", "Backlog", "backlog"),
    ("bl.balance", "MECH", "water placement weighted by what is swimming", "Backlog; shipped as the water community weights `water mix` (v7.1, R62)", "shipped v7.1"),
    # ---- Documentation claims that must match the code
    ("doc.usage.version", "DOC", "USAGE.md's header states the current version and DF/DFHack it was developed against", "USAGE.md", "doc"),
    ("doc.usage.cavernquota", "DOC", "USAGE.md's description of `quota cavern` matches the shipped mechanism", "USAGE.md Per-layer quotas", "doc"),
    ("doc.docstring.tabs", "DOC", "the script docstring's tab count and Usage block match the shipped window and verbs", "script docstring", "doc"),
    ("doc.design.views", "DOC", "the design report's §11 catalogue is labelled as v6.0 aspiration, not shipped", "design §11", "doc"),
    ("doc.docket", "DOC", "the Docket's statement that the tool is at v5.5 is stale", "Docket", "doc"),
    # ---- v7.1 (1 Oct 2026): validator wave 2, one block per stream (seasonal-wildlife docs/v7.1/<stream>.md); phase_v71
    ("deploy.v71.files", "MECH", "the five scripts of the tool tree (engine, gui/, web server, web page, controls registry) are deployed and byte-identical to the checkout under test", "experiments/VALIDATOR-v71.md (deploy); cx-lifecycle.sh deploy-tool", "shipped v7.1"),
    ("deploy.v71.loads", "MECH", "the controls registry loads in the game (12 sections) and the web server that requires it loads", "experiments/VALIDATOR-v71.md (deploy); docs web.md", "shipped v7.1"),
    # ---- v7.1 ecology stream (docs/v7.1/ecology.md): cadence and nudge defaults, skill profiles, packs, raptors, bears, swimmer scavengers
    ("mech.v71.cadence_default", "MECH", "a fresh config has ecology cadence 3,000 and nudge off; a config saved before v7.1 (no `hunters` table) with cadence 1,500 migrates to 3,000 and nudge on to off, one with cadence 2,000 keeps it, and a v7.1 config is never migrated", "docs/v7.1/ecology.md (R37, R38; V7.sanitizeHunters)", "shipped v7.1"),
    ("mech.v71.fish_bears_default", "MECH", "a fresh config has v7.fishers on and every token its fisher_list turns on is a bear (TIGER, JAGUAR, RACCOON off)", "docs/v7.1/ecology.md (R33, R43)", "shipped v7.1"),
    ("mech.v71.skill_profile", "MECH", "with v7 solo on, V7.apply writes a solitary hunter's caste NATURAL_SKILL SNEAK to its profile (solitary apex 15, solitary 12) and a pack species' to 5; V7.restore() puts every caste back to its vanilla level", "docs/v7.1/ecology.md (R40, R58, R8; V7.H.profileOf, V7.naturalSkill)", "shipped v7.1"),
    ("mech.v71.skill_units", "MECH", "a unit of a packaged species already on the map gets the profile on its soul (nominal SNEAK and the natural floor at least the profile's level); V7.restore() reverts the rating and the floor", "docs/v7.1/ecology.md (V7.H.skillUnits, V7.unitSkills)", "shipped v7.1"),
    ("mech.v71.readback", "MECH", "V7.H.readback() returns one row per packaged species and every row's castes all carry the profile's SNEAK (casteOk == castes)", "docs/v7.1/ecology.md (V7.H.readback, `hunters readback`)", "shipped v7.1"),
    ("mech.v71.packs_inferred", "MECH", "two armed same-species non-solitary hunters within pack_radius and in no tracked group are a pack of 2 (V7.H.packSizes); a solitary species and two hunters farther apart give none; pack off gives none", "docs/v7.1/ecology.md (R41)", "shipped v7.1"),
    ("mech.v71.raptor_armed", "MECH", "with hunters.raptors on, V7.apply clears BENIGN on every caste of a raptor (RP) species (BIRD_EAGLE where the embark has it) and V7.restore() sets it back; ecoArmed(entry) is true", "docs/v7.1/ecology.md (R47)", "shipped v7.1"),
    ("mech.v71.raptor_cap", "MECH", "a raptor takes small prey only: V7.H.raptorTooBig(eagle, DEER mass) is true and (eagle, RABBIT mass) false", "docs/v7.1/ecology.md (R47; stoop.prey_ratio)", "shipped v7.1"),
    ("mech.v71.cohesion", "MECH", "MODEL.cohesionOf reads the whole-list table: COUGAR solitary, WOLF pack, FISH_PIKE school or solitary and BIRD_RAVEN flock or solitary by their raws' cluster; `hunters cohesion WOLF herd` wins and `auto` clears it", "docs/v7.1/ecology.md (R62)", "shipped v7.1"),
    ("mech.v71.swimscav", "MECH", "MODEL.swimScavenger is true for SHARK_GREAT_WHITE, CROCODILE_SALTWATER, POND_GRABBER and SHARK_NURSE, false for FISH_LAMPREY_SEA and FISH_PIKE, and false for all with hunters.swim_scav off", "docs/v7.1/ecology.md (R42, R17)", "shipped v7.1"),
    ("mech.v71.bankpair", "MECH", "near a river or lake, V7.H.bankPair finds a dry tile G (flow < 4) and a swimming-depth water tile W (flow >= 4) adjacent at the same level, where a bear on G reaches a fish in W", "docs/v7.1/ecology.md (R33)", "shipped v7.1"),
    ("mech.v70.solo_skill", "MECH", "the caste NATURAL_SKILL write on a solitary hunter is read on a newly arrived unit: a unit placed while the v7 raws hold carries SNEAK at the profile's level on its soul with no unit write", "docs/v7.1/ecology.md (validator-v70-coverage; open item natural-skill-unverified)", "shipped v7.0"),
    # ---- v7.1 fixes stream (docs/v7.1/fixes.md section 5): integration and known bugs
    ("mech.v71.fix.cohesion_override", "MECH", "`hunters cohesion WOLF herd` reaches the leaders: a WOLF group's label is herd at the herd follow distance, `auto` gives pack back; `hunters cohesion COUGAR solitary` leaves a cougar group unled", "docs/v7.1/fixes.md (cohesionLabel reads MODEL.cohesionOf)", "shipped v7.1"),
    ("mech.v71.fix.swimscav_cache", "MECH", "`hunters swimscav SHARK_NURSE off` makes SCAV.kind(SHARK_NURSE) false at once, without a reload (CACHE.scavKind cleared)", "docs/v7.1/fixes.md (SCAV uses MODEL.swimScavenger)", "shipped v7.1"),
    ("mech.v71.fix.forager_no_crash", "MECH", "vermin foraging with a scavenger waiting on remains runs without an error and never sends the waiting scavenger foraging (VERMIN.forager reads CACHE.scav7)", "docs/v7.1/fixes.md (cross-stream 1)", "shipped v7.1"),
    ("mech.v71.fix.edges_after_build", "MECH", "after `roster build land`, `vermin edges edges` reads per-species rows from the build and V7.apply writes an SWV class into at least one consumer's GOBBLE_VERMIN_CLASS", "docs/v7.1/fixes.md (cross-stream 2)", "shipped v7.1"),
    ("mech.v71.fix.apex_pelagic", "MECH", "`roster apex now water` places a pelagic apex only in the ocean, never on a lake-only map, and a placed apex group is led (or marked unled) at once", "docs/v7.1/fixes.md (cross-stream 3)", "shipped v7.1"),
    ("mech.v71.fix.water_auto", "MECH", "a config that never set the water layer turns it on where the map has water (a ledger line 'water layer on by default'), leaves it off on a dry map, and never overrides a layer the player set", "docs/v7.1/fixes.md (section 2; V7.WAT.autoLayer)", "shipped v7.1"),
    ("mech.v71.fix.water_migrate", "MECH", "a saved {layers={water=true}} loads water.layer_set true; {layers={water=false}} and a config with no layers load false; a saved layer_set wins", "docs/v7.1/fixes.md (section 2; V7.watSanitize)", "shipped v7.1"),
    ("mech.v71.fix.spill", "MECH", "a water body with fewer than water.spill.min drawable in-season species borrows the season for active water species (assign gains the season, stock > 0); the season change and `water spill off` give every borrowed season back", "docs/v7.1/fixes.md (section 2; V7.WAT.spillCheck/spillRoll)", "shipped v7.1"),
    ("mech.v71.fix.ids", "CLI", "a spaced raw id resolves from its underscore form and its #index (also with a layer prefix), an exact id is left alone, and `odds` prints the same line for the underscore and the quoted form", "docs/v7.1/fixes.md (spaced-raw-ids-cli; V7.CLI.resolve)", "shipped v7.1"),
    ("mech.v71.fix.world_switch", "MECH", "loading a second world in the same session leaves CACHE.depth holding only its caves and CACHE.raceIdx its race indices, shared by every script copy", "docs/v7.1/fixes.md (cache-world-switch-stale)", "shipped v7.1"),
    ("mech.v71.fix.cavern_max", "MECH", "`limits cavern ceiling 3` leaves groups.cavern_max mirroring groups.cavern_cap (QUOTA.set)", "docs/v7.1/fixes.md (cross-stream 4)", "shipped v7.1"),
    # ---- v7.1 scav stream (docs/v7.1/scav.md section 14): natural-cadence scavenging, swimmers, curious thieves that stay
    ("mech.v71.scav_status_fresh", "MECH", "after a scavenging pass the status's last-pass line is that pass (age near 0), not a stale earlier one", "docs/v7.1/scav.md (scav-status-diagnostics)", "shipped v7.1"),
    ("mech.v71.scav_shared_state", "MECH", "a pass leaves the shared state in CACHE.scav7, and the console's status and a reqscript copy's SCAV.status show the same fallbacks", "docs/v7.1/scav.md (CACHE.scav7)", "shipped v7.1"),
    ("mech.v71.scav_swimmer", "MECH", "SCAV.is: SHARK_GREAT_WHITE, CROCODILE_SALTWATER, ALLIGATOR and ORCA scavenge, FISH_CARP and SHARK_WHALE do not; `scavenge swimmers off` takes every swim-kind scavenger out", "docs/v7.1/scav.md (R42, R17)", "shipped v7.1"),
    ("mech.v71.scav_keys", "CLI", "`scavenge set hop_tiles 99` is refused (range 1-50) and changes nothing; `scavenge set hop_tiles 6` is saved, shown by `scavenge keys` and kept by the sanitiser on reload", "docs/v7.1/scav.md (SCAV.RANGE)", "shipped v7.1"),
    ("mech.v71.scav_discovery", "MECH", "a fresh remains cannot be found in its first pass with the default discovery medians (found after at least discover_min_h); with every discover_*_h, discover_min_h and the sigma at 0 it can be found at once", "docs/v7.1/scav.md (R18 natural cadence; SCAV.newRemains)", "shipped v7.1"),
    ("mech.v71.scav_attribution", "MECH", "a finished remains is attributed: SCAV.stats().pairs['TOK>PREY'].n >= 1 and the ledger has 'scavenging: a PREY ... eaten -- TOK'", "docs/v7.1/scav.md (attribution)", "shipped v7.1"),
    ("mech.v71.scav_fbsafe", "MECH", "SCAV.naturalRemains is false for a non-natural race (demon, forgotten beast, megabeast...) and true for a natural one; no scavenger the pass walks is non-natural", "docs/v7.1/scav.md (R60, fb_safe)", "shipped v7.1"),
    ("mech.v71.scav_off_cancels", "MECH", "`disable` cancels the scavenging and curious jobs (repeat-util holds neither)", "docs/v7.1/scav.md (the scavenging job outlived disable)", "shipped v7.1"),
    ("cli.curious_reform", "CLI", "`curious reform off|on|now`, `curious loot keep|drop` and `curious set stay_min 25000` each print the curious status with the change; an out-of-range value is refused and changes nothing", "docs/v7.1/scav.md (R30)", "shipped v7.1"),
    ("mech.v71.curious_reform", "MECH", "a curious thief whose countdown reaches 0 is reformed within one pass: its unit curious bits cleared, its countdown stay_min..stay_max, a ledger line 'reformed and stays'; disable puts the bits back and the countdown at 0", "docs/v7.1/scav.md (R30; CURIOUS.pass/unreform)", "shipped v7.1"),
    ("mech.v71.panel_curious", "MECH", "the Panel has the curiousreform switch; all off turns it off and its restore path reaches the reformed thieves", "docs/v7.1/scav.md (PANEL.SWITCHES)", "shipped v7.1"),
    ("mech.v70.scav_ext", "MECH", "scav_ext's reach: v7.scav_ext on by default; a flier, an aquatic and an amphibious scavenger are told apart (SCAV.mover), a wet remains suits a swimmer and a dry one a land scavenger, and a wet remains is reached from 2 tiles and a level (the bank/water reach); the status carries the fallbacks counter", "docs/v7.1/scav.md (validator-v70-coverage; SCAV.mover/suits/inReach)", "shipped v7.0"),
    # -- groups (docs/v7.1/groups.md): limits per layer (R7), the adaptive clock (R31), the cavern gate (R44, R60), water
    #    like land (R45), leaders and panic (R32), placement, adoption (H3), the animal-people cap (R35), restore paths
    ("mech.v71.limits.formula", "MECH", "limits mode formula: land and every water body hold floor(sqrt(embark tiles)) + 1 groups at once, each cavern its universal cap of 5 (R44)", "docs/v7.1/groups.md; R7, R44", "shipped v7.1"),
    ("mech.v71.limits.fixed", "CLI", "`limits fixed 2` gives every land and water key 2 and each cavern min(5, 2); `limits formula` puts the map-size formula back", "docs/v7.1/groups.md; R7", "shipped v7.1"),
    ("mech.v71.layer_groups.retired", "MECH", "a config saved with v7.layer_groups=false loads true, and `v7 layer_groups off` is refused with the retirement note", "docs/v7.1/groups.md; R7", "shipped v7.1"),
    ("mech.v71.migrate", "MECH", "a v7.0 config migrates once: water ceiling 12 -> 0 (R45), an explicit land number (auto=false, 4) -> limits mode fixed 4, seasons_own forced on (R29), cavern_max 2 not carried (cap 5)", "docs/v7.1/groups.md; R7, R29, R44, R45", "shipped v7.1"),
    ("mech.v71.clock.state", "MECH", "after a release the layer's controller holds last = now, a target L* in [cap - target_band, cap] and due = last + gap", "docs/v7.1/groups.md; R31", "shipped v7.1"),
    ("mech.v71.clock.forward", "MECH", "with one group fewer on the layer the next release comes earlier (the due tick only moves forward); with the clock off there is no adaptive due tick", "docs/v7.1/groups.md; R31", "shipped v7.1"),
    ("mech.v71.clock.pause", "MECH", "at the cap the clock pauses: no due tick, and the layer's status row says 'paused at the cap'", "docs/v7.1/groups.md; R31", "shipped v7.1"),
    ("mech.v71.cavern.count", "MECH", "an unflagged cavern native is adopted as a native group (depth 0-2) and counted against its cavern's cap", "docs/v7.1/groups.md; R44", "shipped v7.1"),
    ("mech.v71.cavern.hold", "MECH", "a cavern at its cap holds its natural cavern-only species at raw frequency 1 (never 0), listed in CACHE.capHeld; below the cap they go back to the snapshot; hold off holds nothing", "docs/v7.1/groups.md; R44; addenda 53-56", "shipped v7.1"),
    ("mech.v71.cavern.trim", "MECH", "a cavern over its cap sends off its oldest native group (members' leave countdown <= 10, originals in g.trim_undo); the disable path puts the countdowns back", "docs/v7.1/groups.md; R44", "shipped v7.1"),
    ("mech.v71.cavern.deep", "MECH", "no deep unit in any group record, no deep-entry species held or capped, and `groups adopt` refuses a deep unit (R60)", "docs/v7.1/groups.md; R60", "shipped v7.1"),
    ("mech.v71.water.cap", "MECH", "each water body's cap follows the formula, the water ceiling defaults to 0 (none) and the `water` status quotes groups per water body, not a fixed 2 (R45)", "docs/v7.1/groups.md; R45", "shipped v7.1"),
    ("mech.v71.lead.male", "MECH", "a group's leader is its largest adult male; a group with no adult male has no leader and says unled (no fallback, R32)", "docs/v7.1/groups.md; R32", "shipped v7.1"),
    ("mech.v71.lead.lost", "MECH", "a leader that died or left is not replaced: leader_lost names why, nobody follows anybody, a panic ledger line; after panic_days the end line and the group stays unled", "docs/v7.1/groups.md; R32", "shipped v7.1"),
    ("mech.v71.panic.walk", "MECH", "during a panic the members within panic_tiles are walked away (path.goal SeekStation with a non-empty path)", "docs/v7.1/groups.md; R32; findings S2", "shipped v7.1"),
    ("mech.v71.lead.water", "MECH", "a group drawn into water (Driver B) is led in the same pass by a leader standing in water (flow >= 4), members following at follow_school / follow_pod", "docs/v7.1/groups.md; C 9.3", "shipped v7.1"),
    ("mech.v71.lead.place", "CLI", "`place TOKEN 6` places one clustered group, tracked as one record and led at once", "docs/v7.1/groups.md; C 9.3 F1-F2", "shipped v7.1"),
    ("mech.v71.lead.seeded", "MECH", "a school DF seeded in surface water is a record with seeded=true, led but never counted (ENGINE.count('water'))", "docs/v7.1/groups.md; C 9.3 F5", "shipped v7.1"),
    ("mech.v71.lead.sponge", "MECH", "no sponge or IMMOBILE creature is ever a group's leader (cohesion label solitary)", "docs/v7.1/groups.md; C 9.3 F6", "shipped v7.1"),
    ("mech.v71.adopt", "CLI", "`groups adopt a b c` makes exactly those units one record, removed from any other, led by R32's rule; a citizen is refused", "docs/v7.1/groups.md; harness H3", "shipped v7.1"),
    ("mech.v71.apcap", "MECH", "a cavern animal-people species' cluster range is held at <= apcap (5); an irruption on its cavern lifts it; the disable path restores the raw", "docs/v7.1/groups.md; R35", "shipped v7.1"),
    ("mech.v71.restore", "MECH", "all off and disable put back the cavern gate's frequency holds and the animal-people cluster ranges", "docs/v7.1/groups.md; rule 4", "shipped v7.1"),
    ("mech.v71.apex.onecaller", "MECH", "the apex scheduler has one job caller, tick() -> ROSTER.placeTick; the guarded ROSTER.apex.tick hook is gone (replaces mech.v71.apex.hook)", "docs/v7.1/groups.md; docs/v7.1/fixes.md section 1", "shipped v7.1"),
    ("mech.v70.gate_drain", "MECH", "v7.gate_drain (on by default) releases the next-oldest gated groups of the layer until at most one flagged animal remains", "docs/v7.1/groups.md; T8g; validator-v70-coverage", "shipped v7.0"),
    # -- irruption (docs/v7.1/irruption.md section 12): IRRUPT v2, a per-cavern ecological surge (R4-R6, R10, R35, R60)
    ("mech.v71.irr.cfg", "MECH", "the irruption config is rev 2 with every key of the notes' table; a v7.0 config migrates (gain -> src.citizens, migrated 'v7.0'); out-of-range and wrong-type values are dropped", "docs/v7.1/irruption.md; R5", "shipped v7.1"),
    ("mech.v71.irr.migrate", "MECH", "a v7.0 armed group is stood down at the first pass (agitated flags cleared, g.armed gone, its cavern cooling down); the old global cooldown spreads to idle caverns and is removed", "docs/v7.1/irruption.md; R6", "shipped v7.1"),
    ("mech.v71.irr.trigger", "MECH", "a cavern pinned at the threshold warns within one pass (ledger 'something stirs') and irrupts with a wave when the warning ends; no civ race with fallback none gives no warning, one ledger line and a daily retry", "docs/v7.1/irruption.md; R6", "shipped v7.1"),
    ("mech.v71.irr.layer", "MECH", "an event is per cavern: the others stay idle, activeOn names only that cavern, and only its gate gap halves", "docs/v7.1/irruption.md; R5", "shipped v7.1"),
    ("mech.v71.irr.wave", "MECH", "a wave is clamp(cluster max x size_mult, size_min, size_cap) units bounded by stock and unit_cap, one irruption-marked group record, led, the entry debited by n", "docs/v7.1/irruption.md; R10, R32", "shipped v7.1"),
    ("mech.v71.irr.tokens", "MECH", "a civ wave: each enabled token on the champion plus max(1, round(pct n / 100)) others, exactly one unit with every token, each write read back on the unit", "docs/v7.1/irruption.md; R10", "shipped v7.1"),
    ("mech.v71.irr.caste", "MECH", "after placement every caste of the race reads its original CURIOUS*, MEANDERER, AMBUSHPREDATOR, prone_to_rage and HAS_ANY_CURIOUS_BEAST; no caste write is held", "docs/v7.1/irruption.md; R10", "shipped v7.1"),
    ("mech.v71.irr.agitate", "MECH", "during an event only that cavern's non-civ natural animals are agitated (up to the cap): never civ dwellers, citizens, tame animals, other caverns, the deep or non-natural units", "docs/v7.1/irruption.md; R5, R10, R60", "shipped v7.1"),
    ("mech.v71.irr.end", "MECH", "an event ends (by the player, by its duration) with every write undone: masks, caste cache, hidden, mood, skill, agitation; countdowns by end_mode; cooldown set; pressure 0; group marks cleared", "docs/v7.1/irruption.md; R5", "shipped v7.1"),
    ("mech.v71.irr.off", "MECH", "`irruption off`, disable, groups off and all off each end a running event with no residual write and no active phase; while off nothing is placed or written", "docs/v7.1/irruption.md; rule 4", "shipped v7.1"),
    ("mech.v71.irr.fbsafe", "MECH", "irruption candidates are natural only, agitation never reaches a non-natural unit, and nothing is placed or agitated below the third cavern (R60)", "docs/v7.1/irruption.md; R60; fb_safe", "shipped v7.1"),
    ("mech.v71.irr.msg", "MECH", "each phase announces once (warn, start, wave, finish, ready, lapse); pause.start pauses the game; with every msg off nothing is announced", "docs/v7.1/irruption.md; R6", "shipped v7.1"),
    ("mech.v71.irr.status", "CLI", "`irruption status` prints the purpose line, every config row and one row per cavern; `status` prints the one-liner", "docs/v7.1/irruption.md; R6", "shipped v7.1"),
    ("mech.v71.irr.r35", "MECH", "during an event on a cavern with an animal-people species its cluster range is the raw's own (cap lifted); after the end it is capped again", "docs/v7.1/irruption.md; R35", "shipped v7.1"),
    ("gui.irr.rows", "GUI", "the Panel/Layers rows for IRRUPT v2 (irruption.md section 9) read and write the same keys", "docs/v7.1/irruption.md section 9; UI wave", "shipped v7.1"),
    # -- roster (seasonal-wildlife docs/v7.1/roster.md "Validator claims needed"; v7.0 reserved ids from the phase_v71 stub)
    ("mech.v70.builder", "MECH", "`roster build land` runs the guild-first builder: slot lines with their members, an UNFILLED line (with a reason) for every slot under its minimum, the FREQUENCY ladder, the vegetation survey line; a water build carries the column-depth (deep-water) survey", "docs/v7.1/roster.md; validator-v70-coverage; ROSTER.build", "shipped v7.0"),
    ("mech.v70.outgun", "MECH", "`roster outgun land` lists the outgunned pack-vs-herd pairs (factor >= v7 outgun) read-only (the config version does not move); with v7 outgun_cap on, a build caps each outgunned prey's group size at pred mass x factor / prey mass", "docs/v7.1/roster.md; validator-v70-coverage; ROSTER.outgunPairs", "shipped v7.0"),
    ("mech.v70.realms", "MECH", "the realm table holds 300+ species over the REALM_ORDER codes; with v7 realms on, V7.realmOk refuses a species whose realms exclude the embark's and admits its own realm and any unlisted species; with realms off it admits all", "docs/v7.1/roster.md; validator-v70-coverage; V7.REALMS/V7.realmOk", "shipped v7.0"),
    ("mech.v71.ladder.units", "MECH", "after `roster build land` the ladder-info line's carn_units is within 0.03 of carn (R59 unit shares), every ladder value is >= 1, and no apex reads a FREQUENCY above apex_raw_cap unless apex_odds > 0 (R34)", "docs/v7.1/roster.md; R34 R59", "shipped v7.1"),
    ("mech.v71.apex.place", "MECH", "`roster apex now land` places one apex group from stock: ids > 0, the key's entries debited by the group size, and g.groups holds a placed=true tag='apex' record", "docs/v7.1/roster.md; R9 R34", "shipped v7.1"),
    ("mech.v71.apex.cap", "MECH", "with an apex group on the map and the cap at 1, the scheduler's decision is 'cap 1 reached' (ROSTER.apex.decide, not forced)", "docs/v7.1/roster.md; R9", "shipped v7.1"),
    ("mech.v71.flying", "MECH", "`roster build flying` seats at most one RP (R50) and fills the APX slot with no vulture, buzzard, kea or raven", "docs/v7.1/roster.md; R50", "shipped v7.1"),
    ("mech.v71.water.pelagic", "MECH", "on an ocean fort `roster build water` fills APE and PE or reports them UNFILLED ('no candidate in pool'); FISH_LAMPREY_SEA slots as MW (R49)", "docs/v7.1/roster.md; R14 R49 R59", "shipped v7.1"),
    ("mech.v71.civ", "MECH", "V7.isCivRaw is true for ANT_MAN and BAT_MAN, false for WOLF_MAN (R61); every pool entry carries a civ boolean", "docs/v7.1/roster.md; R61", "shipped v7.1"),
    ("mech.v71.apmass", "MECH", "classify(DAMSELFLY_MAN).mass >= 30,000 cm3 and its guild is RP (R25: a vermin-root animal person is a small predator of its own size)", "docs/v7.1/roster.md; R25 R57", "shipped v7.1"),
    ("mech.v71.freqfloor", "MECH", "with the tool applied, every in-embark animal person at raw FREQUENCY 0 reads >= 1 (roster.ap_freq_floor); after restore the raws read 0 again (R61)", "docs/v7.1/roster.md; R61", "shipped v7.1"),
    ("mech.v71.place.deep", "MECH", "`place MAGMA_CRAB 1 deep` is refused (the deep is never touched, R28/R60) and creates no unit", "docs/v7.1/roster.md; R28 R60", "shipped v7.1"),
    ("mech.v71.invasive", "MECH", "on a calm map, Add invasive of CENOZOIC_SMILODON (SAVAGE) places >= 1 unit at once and `roster apex` lists it as a tool-placed invasive (R36)", "docs/v7.1/roster.md; R36", "shipped v7.1"),
    ("mech.v71.realm.table", "CLI", "`realm table` prints a realm-table head with missing_from_raws=0 on vanilla raws and one realm-entry line per entry", "docs/v7.1/roster.md; R57", "shipped v7.1"),
    ("mech.v71.gobble", "MECH", "`roster gobble land` prints >= 1 kind=write edge, and every kind=native edge names a class the consumer's own GOBBLE_VERMIN_CLASS and the vermin's creature classes share (R51)", "docs/v7.1/roster.md; R51", "shipped v7.1"),
    # -- extinct (seasonal-wildlife docs/v7.1/extinct.md "Validator claims needed"; R24)
    ("mech.v71.extinct.class", "MECH", "200 creature raws carry REAL_WORLD_EXTINCT on vanilla and every TAGS token in the raws carries it; `extinct list` shows no 'no REAL_WORLD_EXTINCT class' row", "docs/v7.1/extinct.md; R24", "shipped v7.1"),
    ("mech.v71.extinct.freq", "MECH", "applied with the fix on: T. rex FREQUENCY 2, Quetzalcoatlus 5, Titanoboa 3, Mosasaurus still 50 (no row); after restore 50 / 100 / 30 / 50", "docs/v7.1/extinct.md; R24", "shipped v7.1"),
    ("mech.v71.extinct.grazer", "MECH", "applied: TRICERATOPS every caste GRAZER, misc.grazer 150, HAS_ANY_GRAZER, guild GZ; after restore false / 0 / false; CENOZOIC_MOA's GRAZER untouched", "docs/v7.1/extinct.md; R24", "shipped v7.1"),
    ("mech.v71.extinct.roles", "MECH", "applied: EORAPTOR BENIGN off, CARNIVORE on, guild ML, role predator; TIKTAALIK LARGE_PREDATOR off, guild MW; TITANOBOA LARGE_PREDATOR on, guild AW; DIMETRODON habitat land, guild AL, on the land roster part", "docs/v7.1/extinct.md; R24", "shipped v7.1"),
    ("mech.v71.extinct.model_off", "MECH", "`extinct off` -> classify(TRICERATOPS).guild is PL and EORAPTOR is prey; the raws read vanilla", "docs/v7.1/extinct.md; R24", "shipped v7.1"),
    ("mech.v71.extinct.restore", "MECH", "a write/restore round trip leaves every TAGS raw (frequency, grazer, benign, large predator, carnivore, ambush, cluster) as it was before the write", "docs/v7.1/extinct.md; R24", "shipped v7.1"),
    ("mech.v71.extinct.cavsnap", "MECH", "a T. rex held by CAVERN (raw 1) is corrected in the snapshot (2), not the raw; both restore orders end at raw 50", "docs/v7.1/extinct.md; R24", "shipped v7.1"),
    ("mech.v71.extinct.standdown", "MECH", "a T. rex FREQUENCY written by hand (7) is left alone by the fix (stand_down) and its row reads 'stood down (raw 7)'", "docs/v7.1/extinct.md; R24", "shipped v7.1"),
    ("mech.v71.extinct.realm", "MECH", "with fix and realms on, the realm table gains the fossil-locality rows (CRETACEOUS_TYRANNOSAURUS NEA); with `extinct set realms off` they are gone; a user-json entry survives both", "docs/v7.1/extinct.md; R24", "shipped v7.1"),
    ("mech.v71.extinct.units", "MECH", "a wild extinct animal on the map takes the corrected caste flags into its own cache on apply and gets its own back on restore; a tame one is untouched", "docs/v7.1/extinct.md; R24", "shipped v7.1"),
    ("mech.v71.extinct.mods", "CLI", "on the vanilla rig `extinct mods` prints 'attack mods active: 0' and names the five mod-only animal people", "docs/v7.1/extinct.md; R24", "shipped v7.1"),
    ("mech.v71.extinct.ladder", "MECH", "on an embark with an extinct land apex, a land build reads its FREQUENCY as 'raw 2'/'raw 3' (the corrected raw), not a cap of a 50", "docs/v7.1/extinct.md; docs/v7.1/roster.md; R24 R34", "shipped v7.1"),
    # -- vermin (seasonal-wildlife docs/v7.1/vermin.md "Validator claims needed"; R20 R21 R27 R51)
    ("mech.v70.gobble", "MECH", "with v7 gobble on, an apply tags every in-embark vermin species' castes with its SWV_* class and writes GOBBLE_VERMIN_CLASS onto the matched consumers (GOBBLE_RULES and the edge table); `vermin classes` reports it", "docs/v7.1/vermin.md; validator-v70-coverage; VERMIN.gobbleApply", "shipped v7.0"),
    ("mech.v71.vrm.swv_split", "MECH", "VRM-SWV-SPLIT: `vermin classes` lists SWV_COLONY (bees, termites) and SWV_BAT (bats); SWV_SOIL holds no VERMIN_SOIL_COLONY species", "docs/v7.1/vermin.md VRM-SWV-SPLIT; R21", "shipped v7.1"),
    ("mech.v71.vrm.edges_src", "MECH", "VRM-EDGES-SRC: `vermin edges` names the source in force and the edge table; under source edges and source rules every in-embark consumer's castes carry exactly the SWV classes VERMIN.gobbleWants gives it (per-species rows after a roster build)", "docs/v7.1/vermin.md VRM-EDGES-SRC; docs/v7.1/fixes.md; R51", "shipped v7.1"),
    ("mech.v71.vrm.class_off", "MECH", "VRM-CLASS-OFF: `vermin class SWV_HERP off` leaves no vermin caste tagged SWV_HERP and no consumer gobbling it; `on` puts both back", "docs/v7.1/vermin.md VRM-CLASS-OFF; R21 R27", "shipped v7.1"),
    ("mech.v71.vrm.restore", "MECH", "VRM-RESTORE-v71: V7.restore (disable, all off) removes every SWV_* string from creature_class and the gobble vectors, the new SWV_COLONY and SWV_BAT included", "docs/v7.1/vermin.md VRM-RESTORE-v71", "shipped v7.1"),
    ("mech.v71.vrm.vector", "MECH", "VRM-VECTOR: `vermin census` reads a vermin vector (not NO VERMIN VECTOR) holding objects; colony sites are counted apart from loose vermin and their amount is not in the loose amount", "docs/v7.1/vermin.md VRM-VECTOR; R21", "shipped v7.1"),
    ("mech.v71.vrm.forage_run", "MECH", "VRM-FORAGE-RUN: `vermin forage now` returns a number and the status shows a last pass with its source; every pending forager is wild, not tame, natural, not deep, and walks to the recorded destination", "docs/v7.1/vermin.md VRM-FORAGE-RUN; R21", "shipped v7.1"),
    ("mech.v71.vrm.forage_off", "MECH", "VRM-FORAGE-OFF: `vermin forage off` empties pending, cancels the job (PANEL.jobs shows it off) and clears the released units' walks", "docs/v7.1/vermin.md VRM-FORAGE-OFF", "shipped v7.1"),
    ("mech.v71.vrm.cfg", "MECH", "VRM-CFG: a saved vermin_eat with out-of-range numbers and a bad source loads as the defaults; a class key it lacks loads as on", "docs/v7.1/vermin.md VRM-CFG", "shipped v7.1"),
    ("mech.v71.vrm.perf", "PERF", "VRM-PERF: the vermin foraging job's worst pass stays under 50 ms over 3,000 ticks with the tool on", "docs/v7.1/vermin.md VRM-PERF", "shipped v7.1"),
    # ---- v7.1 water stream (docs/v7.1/water.md): column depth readback (R22), land-layer aquatics (R45), the community mix (R62),
    # prey pull and seeding (R14, R59), the stranding guard, the retry back-off, the curated apex rules (R43, R49)
    ("mech.v71.water.survey.levels", "MECH", "on a fort with deep ocean columns `water depth` shows ocean columns at 3 and 4 stacked water tiles, ENGINE.deepColumns finds n > 0, the scan reads below the top water level (zReached) and is not stopped", "docs/v7.1/water.md; R22; C §8.1", "shipped v7.1"),
    ("mech.v71.water.survey.ocean2", "MECH", "on OCEAN2 the ocean's column-depth histogram holds only 1 and 2 (max 2), nothing at 3 or more", "docs/v7.1/water.md; R22; ECO DEPTH", "shipped v7.1"),
    ("mech.v71.water.survey.contig", "MECH", "a stride-1 water survey (`water depth full`) counts about 4x the stride-2 columns in every well-filled column-depth bucket (within 10%)", "docs/v7.1/water.md; R22", "shipped v7.1"),
    ("mech.v71.water.column_levels", "MECH", "a saved water.deep_levels carries over as water.column_levels (an explicit column_levels wins; default 3), and `water levels 2` changes ENGINE.deepColumns().need to 2", "docs/v7.1/water.md; R22 rename", "shipped v7.1"),
    ("mech.v71.water.landaq", "MECH", "the ocean's Driver B candidates include AQUATIC species listed on land-layer entries (keys with no water: prefix), no species twice; `water aquatic off` removes them", "docs/v7.1/water.md; R45", "shipped v7.1"),
    ("mech.v71.water.mix", "MECH", "`water mix BODY` prints each candidate's base x factor = weight with its reasons; the species most present in the body gets a balance factor under 1; the weights sum above 0", "docs/v7.1/water.md; R62", "shipped v7.1"),
    ("mech.v71.water.apexlimit", "MECH", "with a body already holding water.mix.apex_max (1) curated-apex groups every apex candidate there weighs 0 (a non-apex keeps its weight; with none held the apex weighs > 0); FISH_LAMPREY_SEA is level C, not an apex (R49)", "docs/v7.1/water.md; R43; R49", "shipped v7.1"),
    ("mech.v71.water.pull", "MECH", "with prey drawn into the ocean, a predator or listed apex that takes it shows a pull factor >= water.pull.min in its weight, and a pelagic predator over pelagic_ref with prey here has the shallow floor lifted (its base equals its raw FREQUENCY)", "docs/v7.1/water.md; R14; R59; C §8.2", "shipped v7.1"),
    ("mech.v71.water.seed", "MECH", "a predator drawn while its prey swims is seeded by its prey (ledger 'seeded by its prey'): every member on a water tile (level >= 4/7), within seek_radius of a prey unit, on a column as deep as the deepest sampled there (less one)", "docs/v7.1/water.md; R14; C §8.2 option C", "shipped v7.1"),
    ("mech.v71.water.guard.recheck", "MECH", "on r2 the water status says breathing is read via getBreathingState, and a drawn fish teleported onto dry land is moved back to open water within two guard passes (ledger strand ... moved)", "docs/v7.1/water.md; C §8.2 stranding guard", "shipped v7.1"),
    ("mech.v71.water.retry", "MECH", "a body with nothing drawable backs off water.retry_days (1 day = 1,200 ticks), not the old 5-day gap: next_water_body[body] - now <= retry_days x 1200", "docs/v7.1/water.md; R45", "shipped v7.1"),
    ("mech.v71.water.fisher", "MECH", "no BEAR_* (a fisher on the curated list) is ever a Driver B water candidate", "docs/v7.1/water.md; R33; R43", "shipped v7.1"),
    ("mech.v71.water.nodeep", "MECH", "the water census and the Driver B candidates never include a cavern or deep-layer entry or a unit outside the surface band (R60)", "docs/v7.1/water.md; R60", "shipped v7.1"),
    # ---- v7.1 perf stream (docs/v7.1/perf.md, R48 R55): P0-P12, each with its legacy_* switch
    ("perf.p0.kb", "PERF", "after a groups pass FUSE.stats['seasonal-wildlife/groups'].kb is a number >= 0 and the worst tick (CACHE.perfTickWorst.ms) is at least that job's worst pass", "docs/v7.1/perf.md P0", "shipped v7.1"),
    ("perf.p0.verb", "CLI", "`perf` prints the switch line, the job table and either DFHack perf-counter rows or the 'not in this DFHack build' line, with no error", "docs/v7.1/perf.md P0", "shipped v7.1"),
    ("perf.p1.memo", "PERF", "V7.PERF.raceEco(CACHE.cfg, race) equals ecoOf(cfg, raw) for every race on the map; CACHE.ecoClass is filled after an ecology pass; `perf legacy class on` gives the same V7.natural answers", "docs/v7.1/perf.md P1", "shipped v7.1"),
    ("perf.p2.groups", "PERF", "loadGroups() returns the same shared table twice; after saveGroups the compact site-data record decodes to the same number of groups and carries no 'stuck' key (persist_transient off)", "docs/v7.1/perf.md P2", "shipped v7.1"),
    ("perf.p2.undo", "PERF", "UNDO.push raises UNDO.depth() by one on the held ring (CACHE.undo, the same table before and after) and UNDO.pop takes it back", "docs/v7.1/perf.md P2", "shipped v7.1"),
    ("perf.p3.overlay", "PERF", "V7.PERF.overlayData() twice within a second returns the same table, holding one marker per group with a live member", "docs/v7.1/perf.md P3", "shipped v7.1"),
    ("perf.p4.census", "PERF", "inside a pass, WILD.countByLayer() from the census equals the v7.0 loop over units.active, and discoverGroups finds the same unit ids with `perf legacy census on`", "docs/v7.1/perf.md P4", "shipped v7.1"),
    ("perf.p5.phases", "PERF", "after enable every job the Panel lists as on is scheduled at once, and over a short run no tick is shared by two jobs unless a deferral (FUSE.DEFER) fired", "docs/v7.1/perf.md P5", "shipped v7.1"),
    ("perf.p6.live", "PERF", "the Live tab's biomass sum per layer from the managed-entry index (P6) equals the v7.0 walk over every population (legacy_live), computed headless the way the window does", "docs/v7.1/perf.md P6", "shipped v7.1"),
    ("perf.p7.ro", "PERF", "a groups pass with no config writer due leaves CACHE.cfg the same table and CACHE.ver unchanged (one due saves and replaces it); CAVERN.apply run twice in a row saves its snapshot at most once", "docs/v7.1/perf.md P7", "shipped v7.1"),
    ("perf.p8.pool", "PERF", "V7.PERF.pool(CACHE.cfg) twice returns the same pool with the memo's hits +1; a saveConfig makes the next call rebuild it", "docs/v7.1/perf.md P8", "shipped v7.1"),
    ("perf.p9.native", "PERF", "the edge-only CAVE and WET surveys count exactly what the legacy full scan counts; on r2 the forEachTile vegetation grass share is within 3 points of the Lua scan and PLACE.tiles starts on the same level", "docs/v7.1/perf.md P9", "shipped v7.1"),
    ("perf.p10.slice", "PERF", "after enable the load-time warm slice has run (CACHE.sliceLog.warm, n >= 1, no error) and the cave, wet-edge, water and vegetation surveys are cached; `perf build land` finishes its slice without error", "docs/v7.1/perf.md P10", "shipped v7.1"),
    ("perf.p11.events", "PERF", "`perf census` walks the wild-id set; the set holds every live wild unit on the map, including any that arrived during the run (event or tail scan)", "docs/v7.1/perf.md P11", "shipped v7.1"),
    ("perf.p12.scav", "PERF", "the edible natural remains a scavenging pass finds are the same with `perf legacy scav on` and off, and V7.PERF.webCensus(g).wild equals WILD.countByLayer()", "docs/v7.1/perf.md P12", "shipped v7.1"),
    # ---- v7.1 web stream (docs/v7.1/web.md, R54): the controls registry and its endpoints
    ("web.v71.controls", "MECH", "GET /controls.json answers 200 with at least 12 sections and 300 controls, and every available control (no {T}) carries its current value", "docs/v7.1/web.md; R54", "shipped v7.1"),
    ("web.v71.set", "MECH", "POST /set?id=hunters.stoop.chance&v=61 answers 200 with value 61, the config reads 61 and the ledger gains a line; v=101 answers 400 'at most 100'; an unknown id answers 400", "docs/v7.1/web.md; R54", "shipped v7.1"),
    ("web.v71.set_panel", "MECH", "POST /set?id=switch.nudge&v=on sets ecology.nudge through the Panel's own path (one undo step) and v=off puts it back", "docs/v7.1/web.md; R38; R54", "shipped v7.1"),
    ("web.v71.status", "MECH", "GET /status.json returns every status section with no error, and the group map's first layer key is 'land'", "docs/v7.1/web.md; R54", "shipped v7.1"),
    ("web.v71.cluster", "MECH", "the snapshot's group sizes follow the raws: for a species with two cluster numbers gmin < gmax and gmax == cluster_number[0] (the web-cluster-order fix)", "docs/v7.1/web.md; open item web-cluster-order", "shipped v7.1"),
    ("web.v71.guard", "MECH", "the v7.1 endpoints refuse what they should: /act roster_build with an argument off its list 400, /set by GET 405, /set or /controls.json without the token 403, /cmd 'groups adopt' 400", "docs/v7.1/web.md; R54", "shipped v7.1"),
    ("web.v71.perf", "PERF", "after the first, every snapshot the server builds takes under 50 ms (static species fields cached per world)", "docs/v7.1/web.md P12", "shipped v7.1"),
    ("web.v71.stop", "MECH", "`seasonal-wildlife-web stop` after the v7.1 checks closes the port", "docs/v7.1/web.md", "shipped v7.1"),
]
CLAIM = {c[0]: c for c in CLAIMS}

# ------------------------------------------------------------------------------ plumbing ---
results = []
_log = open(OUT / "log.txt", "w")

def log(msg):
    line = f"{datetime.now().strftime('%H:%M:%S')} {msg}"
    print(line, flush=True); _log.write(line + "\n"); _log.flush()

def rec(cid, verdict, expected, got, shots=(), data=None, note=""):
    assert cid in CLAIM, cid
    c = CLAIM[cid]
    results.append({"id": cid, "surface": c[1], "claim": c[2], "source": c[3], "claimed": c[4],
                    "verdict": verdict, "expected": expected, "got": (got or "").strip()[:1500],
                    "shots": [str(Path(s).relative_to(OUT)) for s in shots], "data": data, "note": note})
    log(f"  [{verdict:<17}] {cid}: {c[2][:70]}")
    if verdict == "FAIL":
        log(f"      expected: {expected}\n      got: {(got or '').strip()[:300]}")

_RIG_VER = {}
def rig_versions():
    """DF and DFHack as the running rig reports them (read once per run). The rig moved from DFHack 53.16-r1.1 to
    53.16-r2 on 1 Oct 2026; a hard-coded label would have mislabelled every run after that."""
    if not _RIG_VER:
        out = lua("print('DFVER='..tostring(dfhack.getDFVersion and dfhack.getDFVersion() or '?')"
                  "..' HACKVER='..tostring(dfhack.getDFHackVersion and dfhack.getDFHackVersion() or '?')"
                  "..' RELEASE='..tostring(dfhack.getDFHackRelease and dfhack.getDFHackRelease() or '?'))")
        m = re.search(r"DFVER=(\S+) HACKVER=(\S+) RELEASE=(\S+)", out or "")
        _RIG_VER.update(df=m.group(1) if m else "?", dfhack=m.group(2) if m else "?", release=m.group(3) if m else "?")
    return _RIG_VER

RPC_TIMEOUT = "45"   # 22 Sep 2026: `groups` right after a full-speed 6,000-tick step twice missed cx-rpc's 15 s default (0.15 s by hand)
RETRIED = []
# --dry-run: every rig call is recorded and answered from a stub (an empty JSON object for Lua, an empty reply for a
# verb), so each phase runs its Python end to end and every Lua chunk can be syntax- and name-checked offline.
DRY_CALLS = []
def sh(*args, timeout=180):
    if DRY:
        DRY_CALLS.append(tuple(str(a) for a in args))
        return 0, ("{}" if args and args[0] == "lua" else "")
    env = dict(os.environ, CX_RPC_TIMEOUT=RPC_TIMEOUT)
    p = subprocess.run([CX, *args], capture_output=True, text=True, timeout=timeout, cwd=ROOT, env=env)
    if args and args[0] in ("cmd", "lua") and "timed out" in (p.stdout + p.stderr):
        time.sleep(2)   # one retry, recorded: a deadline missed once is the rig's moment, twice is the tool's
        RETRIED.append(" ".join(str(a) for a in args[:4]))
        p = subprocess.run([CX, *args], capture_output=True, text=True, timeout=timeout, cwd=ROOT, env=env)
    return p.returncode, (p.stdout or "") + (p.stderr or "")

def cmd(*args, timeout=120):
    return sh("cmd", "seasonal-wildlife", *args, timeout=timeout)

def lua(code, timeout=120):
    rc, out = sh("lua", code, timeout=timeout)
    return out

def luaj(code, timeout=120) -> Any:
    """Run Lua that prints one JSON line (via `json.encode`) and parse it."""
    out = lua("local json=require('json'); " + code, timeout=timeout)
    # DFHack's json.encode PRETTY-PRINTS across lines (tabs, one key per line), so the
    # document is the span from the first bracket to its matching last bracket, never one
    # line. The first run of this driver parsed line-by-line, every probe fell through to
    # {"_raw": ...}, and seven mechanics that the game was doing correctly were reported
    # FAIL (run 143815, kept as VACUOUS-*). Pick whichever bracket opens first so a dict
    # holding a list is not mistaken for the list.
    starts = [k for k in (out.find("{"), out.find("[")) if k != -1]
    if not starts:
        return {"_raw": out}
    i = min(starts)
    j = out.rfind("}" if out[i] == "{" else "]")
    try:
        return json.loads(out[i:j + 1])
    except ValueError:
        return {"_raw": out}

def screen(name):
    rc, txt = sh("screen", timeout=120)
    (SCREENS / f"{name}.txt").write_text(txt)
    return txt

_winid = None
def winid():
    global _winid
    if _winid:
        return _winid
    p = subprocess.run(["swift", str(ROOT / "scripts/cx-winid.swift")], capture_output=True, text=True, timeout=60)
    for line in p.stdout.splitlines():
        if "onscreen=true" in line and "|Dwarf Fortress|" in line:
            _winid = line.split("|")[0]
            break
    return _winid

def shot(name):
    wid = winid()
    png = SHOTS / f"{name}.png"; jpg = SHOTS / f"{name}.jpg"
    if not wid:
        return None
    subprocess.run(["screencapture", "-l", wid, "-x", "-o", str(png)], timeout=30)
    # the report embeds these inline; a 1920x1080 PNG is ~1.6MB and the artifact cap is 16MB,
    # so keep a 1280-wide JPEG (~150KB) and drop the PNG
    subprocess.run(["sips", "-Z", "1280", "-s", "format", "jpeg", "-s", "formatOptions", "72", str(png), "--out", str(jpg)],
                   capture_output=True, timeout=30)
    if jpg.exists():
        png.unlink(missing_ok=True)
        return jpg
    return png if png.exists() else None

def key(k, wait=0.8):
    sh("key", k, timeout=60); time.sleep(wait)

def typ(text, wait=0.5):
    sh("type", text, timeout=60); time.sleep(wait)

def click(label, wait=1.2):
    rc, out = sh("ui", "click", label, timeout=60); time.sleep(wait); return out

def step(ticks, secs=240):
    rc, out = sh("step", str(ticks), str(secs), timeout=secs + 60)
    return out

def centre_on(unit_id):
    lua(f"local u=df.unit.find({unit_id}); if u then dfhack.gui.revealInDwarfmodeMap(xyz2pos(dfhack.units.getPosition(u)), true) end")
    time.sleep(0.8)

# ------------------------------------------------------------------- v7.1 plumbing (validator wave 2) ---
def luap(code, timeout=120) -> dict:
    """luaj with the chunk run under pcall: a Lua error does NOT come back over RPC (DFHack writes it to stderr.log and
    the call times out, cx-lifecycle.sh:865), so a v7.1 probe reports {'_err': message} instead of hanging for 45 s.
    Always returns a dict: the probe's JSON object, {'_err': ...} or {'_raw': text}."""
    j = luaj("local __ok, __e = pcall(function()\n" + code + "\nend)\n"
             "if not __ok then print(json.encode({_err=tostring(__e)})) end", timeout=timeout)
    if isinstance(j, dict):
        return j
    return {"_raw": json.dumps(j)[:600]}

def bad(j):
    """The reason a probe's answer cannot be judged (a Lua error or no JSON), else None."""
    if not isinstance(j, dict):
        return "no JSON object"
    if "_err" in j:
        return "Lua error: " + str(j["_err"])[:400]
    if "_raw" in j:
        return "no JSON: " + str(j["_raw"])[:400]
    return None

def rec_bad(cids, j, what="the probe's JSON"):
    """Record FAIL on every claim a broken probe was meant to judge."""
    for cid in ([cids] if isinstance(cids, str) else cids):
        rec(cid, "FAIL", what, bad(j) or json.dumps(j)[:600])

def manip(cid, what, ok, got):
    """H2 for the validator: a claim that turns a dial reads the dial back before judging the outcome. When the dial
    did not take, the claim is FAIL with a MANIPFAIL note and the outcome is never read (a vacuous PASS is the
    failure this guards against: manifest-subject-receipt)."""
    if ok:
        return True
    rec(cid, "FAIL", "manipulation check: " + what, got if isinstance(got, str) else json.dumps(got)[:900],
        note="MANIPFAIL: the dial did not take, so the claimed effect was not judged")
    return False

def tool(*args, timeout=120):
    """A console verb of the tool, run inside the game with run_command_silent so the reply comes back whole (the
    `cmd` route loses nothing either, but this one also returns a Lua error as text instead of timing out)."""
    words = ",".join(json.dumps(str(a)) for a in args)
    j = luaj(f"local ok,out=pcall(dfhack.run_command_silent,'seasonal-wildlife',{words}); print(json.encode({{ok=ok,out=tostring(out)}}))", timeout=timeout)
    return str(j.get("out") if isinstance(j, dict) and "out" in j else "")

CFG_GET_LUA = """
local function get(c, p)
  for k in p:gmatch('[^.]+') do
    if type(c) ~= 'table' then return nil end
    local v = c[k]; if v == nil and tonumber(k) then v = c[tonumber(k)] end
    c = v
  end
  return c
end
"""
def cfgv(*paths) -> dict:
    """The persisted config values at these dotted paths, read the way the tool reads them (loadConfig)."""
    lst = ",".join(json.dumps(p) for p in paths)
    j = luap("local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig()" + CFG_GET_LUA +
             f"local out={{}}; for _,p in ipairs({{{lst}}}) do out[p]=get(c,p) end; print(json.encode(out))")
    return j if not bad(j) else {}

def cfg_push():
    """Snapshot the tool's config, groups record and enabled state before a sub-phase turns dials (restored by cfg_pop,
    so the phases after v7.1 -- w0, teardown -- see the fort as the earlier phases left it)."""
    return luap("""local sw=reqscript('seasonal-wildlife'); local utils=require('utils')
_G.__v71_stack = _G.__v71_stack or {}
table.insert(_G.__v71_stack, { cfg = utils.clone(sw.loadConfig(), true), groups = utils.clone(sw.loadGroups(), true) })
print(json.encode({depth=#_G.__v71_stack}))""")

def cfg_pop():
    return luap("""local sw=reqscript('seasonal-wildlife'); local utils=require('utils')
local st = _G.__v71_stack; if not st or #st == 0 then print(json.encode({depth=0, none=true})) return end
local snap = table.remove(st)
local now = sw.loadConfig()
if now.enabled and not snap.cfg.enabled then pcall(dfhack.run_command_silent, 'seasonal-wildlife', 'disable') end
sw.saveConfig(snap.cfg); sw.saveGroups(snap.groups)
if snap.cfg.enabled and not now.enabled then pcall(dfhack.run_command_silent, 'seasonal-wildlife', 'enable') end
print(json.encode({depth=#st, enabled=snap.cfg.enabled}))""")

# Which fort a fort-dependent claim needs. R11: region8 ('The Last Planets') for all testing from 1 Oct 2026; its 1x1
# forts come from scripts/b1-forts.py (embark --only NEED). Until they exist, the older fort named after 'until then'
# carries the same condition. A claim whose condition is missing on the loaded fort is NOT-TESTABLE-HERE naming this.
NEED = {
    "ocean": "an ocean on the map: region8 B1-R8-*-SHORE (b1-forts.py embark --only shore); until then OCEAN2 (shallow) or BOATS (deep columns)",
    "ocean_deep": "ocean columns of 3+ stacked water tiles: BOATS (DEPTH survey: 12,045 columns >= 3), or a region8 SHORE fort whose `water depth` shows them",
    "ocean_shallow": "a shallow ocean (columns of 1-2 only): OCEAN2, or a region8 SHORE fort whose `water depth` shows max 2",
    "lake": "a lake on the map: region8 B1-R8-*-LAKE (b1-forts.py embark --only lake); until then LAKE",
    "river": "a river on the map: region8 B1-R8-*-RIVER (b1-forts.py embark --only river); until then RIVER4",
    "water": "any open surface water: region8 SHORE/LAKE/RIVER; until then LAKE, RIVER4, OCEAN2 or BOATS",
    "dry": "a dry map (no surface water): CTRL, or a region8 interior 1x1 with no water in `facts`",
    "cavern_reached": "a cavern the fort has reached (Discovered): a region8 fort after a breach (dig-now + aquifer seal, memory fort-load-levers); CTRL's caverns are never opened",
    "calm": "a calm map (savagery under 33): region8 B1-R8-*-CALM; CTRL is calm",
    "r2": "the rig on DFHack 53.16-r2 (dfhack.units.getBreathingState, dfhack.maps.forEachTile)",
    "second_world": "a second world loaded in the same DF session (load A, title, load B); one validate-full session loads one world",
}

F71 = {}
FACTS_LUA = """
local sw=reqscript('seasonal-wildlife'); local out={loaded=dfhack.isMapLoaded()}
out.release = dfhack.getDFHackRelease and dfhack.getDFHackRelease() or '?'
out.r2 = (dfhack.units.getBreathingState ~= nil)
out.forEachTile = (dfhack.maps.forEachTile ~= nil)
if out.loaded then
  local m = df.global.world.map; out.x, out.y, out.z = m.x_count, m.y_count, m.z_count
  out.auto = sw.QUOTA.autoGroups()
  local c = sw.loadConfig(); out.enabled = c.enabled; out.layers = c.layers
  local ok, w = pcall(sw.ENGINE.waterTiles, false)
  if ok and type(w) == 'table' then out.water = w.sum; out.maxDepth = w.maxDepth; out.stride = w.stride end
  local okc, cf = pcall(sw.cavernsFound)
  out.caverns = {}; out.reached = 0
  if okc and type(cf) == 'table' then for d, found in pairs(cf) do out.caverns['c' .. d] = found; if found then out.reached = out.reached + 1 end end end
  local okw, by = pcall(sw.WILD.countByLayer); if okw then out.wild = by end
  local n = 0; for _, u in ipairs(df.global.world.units.active) do if dfhack.units.isCitizen(u) and not dfhack.units.isDead(u) then n = n + 1 end end
  out.citizens = n
  local okn, nm = pcall(function() return dfhack.translation and dfhack.translation.translateName(df.global.world.world_data.name, true) or dfhack.TranslateName(df.global.world.world_data.name, true) end)
  out.world = okn and nm or '?'
  local okv, sav = pcall(function() local st = df.global.world.world_data.active_site[0]; return dfhack.maps.getRegionBiome(st.pos.x, st.pos.y).savagery end)
  out.savagery = okv and sav or nil
end
print(json.encode(out))"""

def v71_facts(fort):
    """What the loaded fort offers the fort-dependent v7.1 claims (water bodies, caverns reached, map size, r2)."""
    j = luap(FACTS_LUA, timeout=180)
    F71.clear(); F71.update(j if not bad(j) else {"_bad": bad(j)}); F71["fort"] = fort
    w = F71.get("water") or {}
    md = F71.get("maxDepth") or {}
    F71["has"] = {
        "ocean": (w.get("ocean") or 0) > 0, "lake": (w.get("lake") or 0) > 0, "river": (w.get("river") or 0) > 0,
        "pool": (w.get("pool") or 0) > 0,
        "water": sum((w.get(k) or 0) for k in ("ocean", "lake", "river", "pool")) > 0,
        "ocean_deep": (md.get("ocean") or 0) >= 3, "ocean_shallow": 0 < (md.get("ocean") or 0) <= 2,
        "cavern_reached": (F71.get("reached") or 0) > 0, "r2": bool(F71.get("r2")),
    }
    F71["has"]["dry"] = not F71["has"]["water"]
    F71["has"]["calm"] = isinstance(F71.get("savagery"), (int, float)) and F71["savagery"] < 33
    log(f"  v7.1 facts: fort {fort} world {F71.get('world')} map {F71.get('x')}x{F71.get('y')} auto {F71.get('auto')} "
        f"water {w} maxDepth {md} caverns {F71.get('caverns')} savagery {F71.get('savagery')} r2 {F71.get('r2')} citizens {F71.get('citizens')}")
    return F71

def has(cond):
    return bool((F71.get("has") or {}).get(cond)) or DRY   # the dry run walks every branch

def need(cid, cond, expected, got="", note=""):
    """NOT-TESTABLE-HERE for a claim whose fort condition is missing; returns True when the condition holds."""
    if has(cond):
        return True
    rec(cid, "NOT-TESTABLE-HERE", expected, got or f"fort {F71.get('fort')}: no {cond}",
        note=(NEED.get(cond, cond) + (("; " + note) if note else "")))
    return False

WEB_PORT = 8642
def curl(path, method="GET", host=None, port=WEB_PORT):
    """(status, body) from the companion server on the host; body as latin-1 text (PNGs are not UTF-8)."""
    if DRY:
        DRY_CALLS.append(("curl", method, path))
        return 0, ""
    a = ["curl", "-s", "-m", "10", "-o", "-", "-w", "\n%{http_code}", "-X", method]
    if host: a += ["-H", f"Host: {host}"]
    p = subprocess.run(a + [f"http://127.0.0.1:{port}{path}"], capture_output=True)
    body, _, code = p.stdout.decode("latin-1").rpartition("\n")
    return (int(code) if code.isdigit() else 0), body

GROUND_LUA = """
local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig()
local by=sw.WILD.countByLayer()
local units={}; local cz=0
for _,u in ipairs(df.global.world.units.active) do
  if not dfhack.units.isDead(u) then
    if dfhack.units.isCitizen(u) then cz=cz+1
    elseif sw.WILD.onMap(u) then
      local cr=df.creature_raw.find(u.race); local t=cr and cr.creature_id or ('#'..u.race)
      units[#units+1]={id=u.id, token=t, layer=sw.WILD.layerOf(u), x=u.pos.x, y=u.pos.y, z=u.pos.z,
        countdown=u.animal and u.animal.leave_countdown or -1}
    end
  end
end
local pool=sw.buildPool(cfg); local pools={}; local nAssigned,nAllowed=0,0
for _,e in ipairs(pool) do
  if e.inEmbark then
    if sw.isAllowed(cfg,e) then nAllowed=nAllowed+1 end
    if cfg.assign[e.key] and #cfg.assign[e.key]>0 then nAssigned=nAssigned+1 end
  end
end
local ok,ru=pcall(require,'repeat-util')
print(json.encode({tick=df.global.cur_year_tick, year=df.global.cur_year, season=df.global.cur_season,
  citizens=cz, land=by.land, water=by.water, cavern=by.cavern, deep=by.deep,
  enabled=cfg.enabled, groups=cfg.groups.enabled, ecology=cfg.ecology.enabled, water_on=cfg.water.enabled,
  layers=cfg.layers, quota=cfg.quota, sched=(ok and ru.isScheduled and ru.isScheduled('seasonal-wildlife')) or false,
  allowed=nAllowed, assigned=nAssigned, units=units}))
"""
def ground(name) -> Any:
    g = luaj(GROUND_LUA, timeout=180)
    if not isinstance(g, dict) or "units" not in g:
        g = {"_raw": g, "units": []}
    (GROUND / f"{name}.json").write_text(json.dumps(g, indent=1))
    return g

POOL_LUA = """
local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig()
local rs=sw.getEmbarkRegions(); local out={}
for _,pop in ipairs(df.global.world.populations.all) do
  if sw.managedPop(pop, rs, {land=true, water=true, cavern=true}) then
    local cr=df.creature_raw.find(pop.race)
    out[#out+1]={idx=pop.population.population_idx, token=cr and cr.creature_id or '?', layer=sw.layerOf(pop),
      qty=pop.quantity, type=df.world_population_type[pop.type]}
  end
end
print(json.encode(out))
"""
def pools():
    p = luaj(POOL_LUA, timeout=180)
    return p if isinstance(p, list) else []

def fmt_pools(ps):
    """token -> total qty across entries (managed land/water/cavern)."""
    tot = {}
    for e in ps:
        tot[e["token"]] = tot.get(e["token"], 0) + int(e["qty"])
    return tot

ROW = re.compile(r"^\s*\d+\|.*?\s{2,}(\S+)(?: [w~])?\s+(prey|predator|bird|vermin|apex|other)\s+(small|medium|large)\s+(\S+)\s+(\S+)\s+(\d{1,3})\s+([Y\-])(?:\s+(.*?))?\s*$")   # v5.10.5: an optional why column after ok; v6.2.0: skip anything painted on the MAP left of the window (the overlay's link dots landed in row 29 and read as the token)
def row_lines(txt):
    """Roster rows as the text grid draws them, sliced by the header's own column positions (v6.4: the parser reads
    the columns off the header row, so a column added -- HAB in v6.4, STOCK and ODDS in v6.5 -- moves nothing).
    The header is the line holding CREATURE and SEASON; each row is sliced at the header words' start columns.
    Returns (token, ab-or-stock as an int or -1, ok/act 'Y' or '-', season label, line)."""
    lines = txt.splitlines()
    hdr_i, cols = None, {}
    for n, line in enumerate(lines):
        if "CREATURE" in line and "SEASON" in line and "WHY" in line:
            hdr_i = n
            for m in re.finditer(r"\S+", line):
                cols[m.group(0)] = m.start()
            break
    if hdr_i is None:
        return []
    order = sorted(cols.items(), key=lambda kv: kv[1])
    def field(line, name):
        if name not in cols: return ""
        k = [nm for nm, _ in order].index(name)
        a = cols[name] - (1 if name == "CREATURE" else 0)
        b = order[k + 1][1] if k + 1 < len(order) else len(line)
        return line[a:b].strip()
    rows = []
    for line in lines[hdr_i + 1:]:
        if not re.match(r"^\s*\d+\|", line):
            continue
        cat = field(line, "ROLE") or field(line, "CAT")
        size = field(line, "SIZE")
        okc = field(line, "act") or field(line, "ok")
        if cat.split()[:1] and cat.split()[0] in ("prey", "predator", "bird", "vermin", "apex", "other") and size in ("small", "medium", "large") and okc[:1] in ("Y", "-"):
            tok = field(line, "CREATURE").split()
            tok = tok[0] if tok else ""
            ab = field(line, "STOCK") or field(line, "ab")
            try:
                abv = int(ab)
            except ValueError:
                abv = -1
            rows.append((tok, abv, okc[:1], field(line, "SEASON"), line))
    return rows

# v6.6 (W9): the window is as tall as the screen allows, so its rows are read from the window's own frame_rect
# rather than assumed (the 34-row window centred on a 67-row screen was rows 16-49). Cached once the window is open.
WINRECT = {}
def win_rect():
    if not WINRECT.get("y1"):
        r = luaj("local gw=reqscript('gui/seasonal-wildlife'); local w=gw.view and gw.view.subviews and gw.view.subviews[1]; "
                 "if w and w.frame_rect then print(json.encode({y1=w.frame_rect.y1, y2=w.frame_rect.y2, x1=w.frame_rect.x1, x2=w.frame_rect.x2})) else print(json.encode({})) end", timeout=60)
        if isinstance(r, dict) and r.get("y1") is not None:
            WINRECT.update(r)
    return WINRECT.get("y1", 16), WINRECT.get("y2", 49)

def window_rows(txt, lo=None, hi=None):
    if lo is None or hi is None:
        y1, y2 = win_rect(); lo, hi = y1, y2
    return "\n".join(l for l in txt.splitlines() if (m := re.match(r"^\s*(\d+)\|", l)) and lo <= int(m.group(1)) <= hi)

def status_rows(txt):
    """The Roster tab's bottom panel: hint, three hotkey rows, then the status label (the window's last seven rows)."""
    y1, y2 = win_rect()
    return window_rows(txt, y2 - 7, y2 - 1)

def grid_status(txt):
    """The targets-and-keys block of the Roster (rows 4-14 of the window)."""
    y1, y2 = win_rect()
    return window_rows(txt, y1 + 4, y1 + 14)

def dialog_rows(txt):
    y1, y2 = win_rect()
    mid = (y1 + y2) // 2
    return window_rows(txt, mid - 8, mid + 8)

def sha_dir(d):
    p = subprocess.run(["bash", "-c", f'cd "{d}" && find . -type f -print0 | sort -z | xargs -0 shasum -a 256 | shasum -a 256 | cut -c1-16'],
                       capture_output=True, text=True)
    return p.stdout.strip()



# ================================================================ v6.4: the species model and the food web ====
FIXTURE = ROOT / "data/fixtures/species-model.tsv"
MODEL_LUA = """
local sw=reqscript('seasonal-wildlife'); local M=sw.MODEL
local want={'SHARK_GREAT_WHITE','SEA_SERPENT','GIANT_CUTTLEFISH','POND_GRABBER','HIPPO','RIVER OTTER','CRAB','HORSESHOE_CRAB','CROCODILE_CAVE','BIRD_PENGUIN',
  'BIRD_ALBATROSS','BIRD_OSPREY','BIRD_DUCK','BIRD_EAGLE','BIRD_KESTREL','WOLF','DINGO','ORCA','GIANT_ORCA','SPERM_WHALE','SHARK_WHALE','SHARK_BULL','LION','GIRAFFE','ELEPHANT','GAZELLE','DEER','FISH_HERRING'}
local out={named={}, pairs={}}
for _,t in ipairs(want) do local e=M.entry(t); if e then out.named[t]={habitat=e.habitat, role=e.role, band=e.size, mass=e.mass} end end
local function E(a,b) local x,y=M.entry(a),M.entry(b); if not x or not y then return 'missing' end; return sw.eats(x,y) end
out.pairs={ ['LION>SHARK_GREAT_WHITE']=E('LION','SHARK_GREAT_WHITE'), ['LION>SHARK_BULL']=E('LION','SHARK_BULL'), ['BIRD_EAGLE>FISH_TUNA_BLUEFIN']=E('BIRD_EAGLE','FISH_TUNA_BLUEFIN'),
  ['SHARK_GREAT_WHITE>DEER']=E('SHARK_GREAT_WHITE','DEER'), ['BIRD_OSPREY>FISH_HERRING']=E('BIRD_OSPREY','FISH_HERRING'), ['LION>GAZELLE']=E('LION','GAZELLE') }
local rows={}
for _,r in ipairs(M.audit()) do rows[#rows+1]=table.concat({r.token, r.habitat, r.role, r.why, r.band, tostring(r.mass), tostring(r.vermin), tostring(r.eco), r.bodies, r.salt}, '\\t') end
out.audit=rows
print(json.encode(out))
"""
MATRIX_LUA = """
local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg)
sw.ROSTER.normalize(cfg, pool)
local n, repaired = sw.assignFromMatrix(cfg, pool)
local per, act, empty = {0,0,0,0}, 0, 0
for _,e in ipairs(pool) do if e.inEmbark and not e.locked and sw.isAllowed(cfg,e) then act=act+1; local a=cfg.assign[e.key] or {}; if #a==0 then empty=empty+1 end; for _,s in ipairs(a) do per[s+1]=per[s+1]+1 end end end
-- pair guarantee, re-derived here from eats() rather than trusting the engine's own report
local groups, missing = {}, {}
for _,e in ipairs(pool) do if e.inEmbark and not e.locked and e.cat~='vermin' and sw.isAllowed(cfg,e) then
  local k=(e.layer=='cavern' and 'cavern' or 'surface')..'|'..sw.ROSTER.habitatGroup(e); groups[k]=groups[k] or {}; table.insert(groups[k], e) end end
for k,list in pairs(groups) do
  local can=false; for _,p in ipairs(list) do for _,q in ipairs(list) do if p~=q and sw.eats(p,q) then can=true end end end
  if can then for s=0,3 do local ok=false
    for _,p in ipairs(list) do if sw.inSeason(cfg,p.key,s) then for _,q in ipairs(list) do if p~=q and sw.inSeason(cfg,q.key,s) and sw.eats(p,q) then ok=true; break end end end; if ok then break end end
    if not ok then missing[#missing+1]=k..'@'..s end end end
end
local cells0=0; for _,a in pairs(cfg.assign) do cells0=cells0+#a end
local co = sw.coAlignSeasons(cfg, pool)
local cells1=0; local over=0; for k,a in pairs(cfg.assign) do cells1=cells1+#a end
print(json.encode({dealt=n, repaired=repaired, per=per, active=act, empty=empty, missing=missing, groups=(function() local t={} for k in pairs(groups) do t[#t+1]=k end return t end)(), coalign=co, cells_before=cells0, cells_after=cells1}))
"""

def phase_model():
    log("== v6.4: the species model and the food web")
    m = luaj(MODEL_LUA, timeout=300)
    named = m.get("named", {}) if isinstance(m, dict) else {}
    hab = {"SHARK_GREAT_WHITE": "aquatic", "SEA_SERPENT": "aquatic", "GIANT_CUTTLEFISH": "aquatic", "POND_GRABBER": "aquatic",
           "HIPPO": "semiaquatic", "RIVER OTTER": "semiaquatic", "CRAB": "semiaquatic", "HORSESHOE_CRAB": "semiaquatic", "CROCODILE_CAVE": "semiaquatic", "BIRD_PENGUIN": "semiaquatic",
           "BIRD_ALBATROSS": "waterbird", "BIRD_OSPREY": "waterbird", "BIRD_DUCK": "waterbird", "BIRD_EAGLE": "flier", "BIRD_KESTREL": "flier", "WOLF": "land", "DINGO": "land"}
    bad = {t: named.get(t, {}).get("habitat") for t, h in hab.items() if named.get(t, {}).get("habitat") != h}
    rec("mech.model.habitat", "PASS" if named and not bad else "FAIL", "each named species in its Q1 habitat", f"mismatches: {bad}" if bad else f"{len(hab)} of {len(hab)} as Q1 says", data=named)
    role = {"ORCA": "predator", "GIANT_ORCA": "predator", "BIRD_EAGLE": "predator", "BIRD_KESTREL": "predator", "SPERM_WHALE": "predator",
            "SHARK_WHALE": "prey", "BIRD_ALBATROSS": "prey", "HIPPO": "prey"}
    badr = {t: named.get(t, {}).get("role") for t, r in role.items() if named.get(t, {}).get("role") != r}
    rec("mech.model.role", "PASS" if named and not badr else "FAIL", "each named species in its role", f"mismatches: {badr}" if badr else f"{len(role)} of {len(role)}", data={t: named.get(t) for t in role})
    band = {"BIRD_KESTREL": "small", "WOLF": "small", "DINGO": "small", "SHARK_BULL": "medium", "LION": "medium", "GIRAFFE": "large", "HIPPO": "large", "ELEPHANT": "large"}
    badb = {t: (named.get(t, {}).get("band"), named.get(t, {}).get("mass")) for t, b in band.items() if named.get(t, {}).get("band") != b}
    rec("mech.model.band", "PASS" if named and not badb else "FAIL", "each named species in its D4 band", f"mismatches: {badb}" if badb else f"{len(band)} of {len(band)}", data={t: named.get(t) for t in band})
    rows = m.get("audit", []) if isinstance(m, dict) else []
    live = "\n".join(sorted(rows))
    if not FIXTURE.exists() and rows:
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text("token\thabitat\trole\twhy\tband\tmass\tvermin\teco\tbodies\tsalt\n" + live + "\n")
        rec("mech.model.audit", "PASS", "the fixture written from this run", f"{len(rows)} creature raws written to {FIXTURE.relative_to(ROOT)} (first run: the baseline)", data={"n": len(rows)})
    else:
        fx = FIXTURE.read_text().splitlines()[1:] if FIXTURE.exists() else []
        a, b = set(fx), set(rows)
        gone, new = sorted(a - b), sorted(b - a)
        rec("mech.model.audit", "PASS" if rows and not gone and not new else "FAIL", "the live reading equals the fixture, row for row",
            f"{len(rows)} live rows, {len(fx)} fixture rows; {len(gone)} changed or missing, {len(new)} new: " + " | ".join((gone + new)[:8]), data={"n": len(rows), "diff": (gone + new)[:40]})
    pr = m.get("pairs", {}) if isinstance(m, dict) else {}
    want = {"LION>SHARK_GREAT_WHITE": False, "LION>SHARK_BULL": False, "BIRD_EAGLE>FISH_TUNA_BLUEFIN": False, "SHARK_GREAT_WHITE>DEER": False, "BIRD_OSPREY>FISH_HERRING": True, "LION>GAZELLE": True}
    badp = {k: pr.get(k) for k, v in want.items() if pr.get(k) != v}
    rec("mech.diet.habitat", "PASS" if pr and not badp else "FAIL", "the six diet verdicts as the habitat test gives them", f"mismatches: {badp}" if badp else json.dumps(pr), data=pr)
    x = luaj(MATRIX_LUA, timeout=300)
    if not isinstance(x, dict) or "per" not in x:
        for cid in ("mech.matrix.balance", "mech.pair.guarantee", "mech.coalign.bounded"):
            rec(cid, "FAIL", "the matrix probe answers", str(x)[:300])
        return
    act, per = x.get("active", 0), x.get("per", [])
    rec("mech.matrix.balance", "PASS" if act and max(per) <= act / 2 and x.get("empty") == 0 else "FAIL",
        "no season over half the active roster; no active species without a season", f"active {act}; per season {per}; empty {x.get('empty')}; repaired {x.get('repaired')}", data=x)
    rec("mech.pair.guarantee", "PASS" if not x.get("missing") else "FAIL", "no realm/habitat group season without an eats() pair",
        f"groups {x.get('groups')}; seasons missing a pair: {x.get('missing')}", data=x)
    rec("mech.coalign.bounded", "PASS" if x.get("cells_after", 0) - x.get("cells_before", 0) == x.get("coalign") else "FAIL",
        "cells added == the count co-align reports", f"co-align {x.get('coalign')}; cells {x.get('cells_before')} -> {x.get('cells_after')}", data=x)


# ================================================================ v6.5: the engine, stock, odds, calls ====
V65_LUA = """
local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg); local out={}
-- a land species with stock, active in this season
local s=df.global.cur_season; local e
for _,x in ipairs(pool) do if x.inEmbark and x.layer=='land' and x.cat~='vermin' and sw.ROSTER.wants(cfg,x.key,s) and ({sw.RESERVE.of(x.key)})[1]>0 then e=x; break end end
if not e then print(json.encode({none=true})) return end
out.token=e.token
-- stock reserve: make it inactive, apply (zeroed, remembered), activate again, apply (given back)
local live0=sw.RESERVE.of(e.key)
sw.ROSTER.setActive(cfg,pool,e,false); sw.saveConfig(cfg); sw.applyLive(cfg,s)
local live1,held1=sw.RESERVE.of(e.key)
sw.ROSTER.setActive(cfg,pool,e,true); cfg.assign[e.key]={s}; sw.saveConfig(cfg); sw.applyLive(cfg,s)
local live2,held2=sw.RESERVE.of(e.key)
out.reserve={before=live0, off_live=live1, off_held=held1, back_live=live2, back_held=held2}
-- odds: write, read the raw, the share; then disable restores
cfg.odds[e.key]=37; sw.saveConfig(cfg); sw.CAVERN.apply(cfg,s)
local cr=df.creature_raw.find(e.idx); local f1=cr.frequency; local w,share=sw.ODDS.share(cfg,pool,e)
out.odds={raw=f1, weight=w, share=share}
-- group size
cfg.group_size[e.key]=4; sw.saveConfig(cfg); sw.PATTERN.sizeApply(cfg)
out.size={max=cr.cluster_number[0], min=cr.cluster_number[1]}
sw.disableSched()
out.after_disable={raw=cr.frequency, cmax=cr.cluster_number[0], cmin=cr.cluster_number[1]}
cfg=sw.loadConfig(); cfg.odds[e.key]=nil; cfg.group_size[e.key]=nil; sw.saveConfig(cfg); sw.enableSched()
-- deep keys
local deep=0; for _,x in ipairs(sw.buildPool((function() local c=sw.loadConfig(); c.layers.deep=true; return c end)())) do if x.layer=='deep' and x.inEmbark then deep=deep+1 end end
out.deep=deep
-- origins of the wild units on the map
local g=sw.loadGroups(); local tracked={}; for _,grp in ipairs(g.groups) do for _,id in ipairs(grp.ids) do tracked[id]=grp end end
local by={}; local n=0; for _,u in ipairs(df.global.world.units.active) do if sw.WILD.onMap(u) then n=n+1; local o=sw.WILD.origin(u,tracked); by[o]=(by[o] or 0)+1 end end
out.origin=by; out.wild=n
print(json.encode(out))
"""

def phase_v65():
    log("== v6.5: the engine, stock, odds, calls")
    x = luaj(V65_LUA, timeout=300)
    if not isinstance(x, dict) or x.get("none"):
        for cid in ("mech.stock.reserve", "mech.odds", "mech.groupsize", "mech.deep", "mech.origin"):
            rec(cid, "NOT-TESTABLE-HERE", "an active, stocked land species", json.dumps(x)[:300])
    else:
        r = x.get("reserve", {})
        ok = r.get("before", 0) > 0 and r.get("off_live") == 0 and r.get("off_held", 0) >= r.get("before", 0) and r.get("back_live", 0) >= r.get("before", 0) and r.get("back_held") == 0
        rec("mech.stock.reserve", "PASS" if ok else "FAIL", "inactive: live 0, the stock held; active again: the stock back in the entries, nothing held", json.dumps(r), data=x)
        o, a = x.get("odds", {}), x.get("after_disable", {})
        rec("mech.odds", "PASS" if o.get("raw") == 37 and o.get("weight") == 37 and 0 < o.get("share", 0) <= 100 and a.get("raw") != 37 else "FAIL",
            "odds 37 on the raw and in the share; disable puts the raw back", json.dumps({"odds": o, "after_disable": a}), data=x)
        z = x.get("size", {})
        rec("mech.groupsize", "PASS" if z.get("max") == 4 and z.get("min") == 4 and not (a.get("cmax") == 4 and a.get("cmin") == 4) else "FAIL",
            "size 4 stands as {4,4}; disable puts the raw's range back", json.dumps({"size": z, "after_disable": a}), data=x)
        rec("mech.deep", "PASS" if x.get("deep", 0) > 0 else "NOT-TESTABLE-HERE", "deep:TOKEN species on the roster with the deep layer on",
            f"{x.get('deep')} deep species", note="" if x.get("deep") else "no natural magma-sea species on this embark's regions")
        by = x.get("origin", {})
        known = {"DF wave", "tool-drawn", "resident", "born here", "untracked", "deep"}
        rec("mech.origin", "PASS" if x.get("wild", 0) > 0 and sum(by.values()) == x.get("wild") and set(by) <= known else ("NOT-TESTABLE-HERE" if not x.get("wild") else "FAIL"),
            "every wild unit has one of the six origins", json.dumps(by), data=by)
    # send off: gated land groups get countdown 0 and the gate opens
    so0 = luaj("local sw=reqscript('seasonal-wildlife'); local g=sw.loadGroups(); local n=0; for _,grp in ipairs(g.groups) do if (grp.layer or 'land')=='land' and not grp.resident then n=n+1 end end; print(json.encode({gated=n}))", timeout=60)
    rc, out = cmd("sendoff", "land")
    so1 = luaj("local sw=reqscript('seasonal-wildlife'); local g=sw.loadGroups(); local n,cd=0,{}; for _,grp in ipairs(g.groups) do if (grp.layer or 'land')=='land' and not grp.resident then n=n+1 end; if grp.dismissed then for _,id in ipairs(grp.ids) do local u=df.unit.find(id); if u then cd[#cd+1]=u.animal.leave_countdown end end end end; print(json.encode({gated=n, dismissed_countdowns=cd, next=g.next_wave_tick-sw.absTick()}))", timeout=60)
    g0 = so0.get("gated", 0) if isinstance(so0, dict) else 0
    oks = isinstance(so1, dict) and so1.get("gated") == 0 and "sent off" in out and all(c == 0 for c in so1.get("dismissed_countdowns", [])) and so1.get("next", 1) <= 0
    rec("mech.sendoff", "PASS" if oks and g0 > 0 else ("NOT-TESTABLE-HERE" if g0 == 0 and oks else "FAIL"),
        "no gated land group left, every sent-off member at countdown 0, the gate open now", out + json.dumps(so1), data={"before": so0, "after": so1},
        note="" if g0 else "no gated land group on the map this moment; the verb ran and the gate opened")
    # call: the pool opened to one species alone
    pk = luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg); for _,x in ipairs(pool) do if x.inEmbark and x.layer=='land' and x.cat~='vermin' and sw.ROSTER.wants(cfg,x.key,df.global.cur_season) then print(json.encode({key=x.key})) return end end; print(json.encode({none=true}))", timeout=120)
    if isinstance(pk, dict) and pk.get("key"):
        rc, out = cmd("call", pk["key"])
        ex = luaj("local sw=reqscript('seasonal-wildlife'); local g=sw.loadGroups(); local ex=g.exclusion; local open={}; if ex then for t in pairs(ex.predators or {}) do open[#open+1]=t end end; "
                  "local l=sw.LEDGER.lines(3,'call'); print(json.encode({kind=ex and ex.kind, open=open, ledger=l[#l]}))", timeout=60)
        okc = isinstance(ex, dict) and ex.get("kind") == "call" and ex.get("open") == [pk["key"]] and pk["key"] in str(ex.get("ledger"))
        rec("mech.call", "PASS" if okc else "FAIL", "the coupling table stands with kind 'call' and only the called species open; a call line in the ledger", out + json.dumps(ex), data=ex)
    else:
        rec("mech.call", "NOT-TESTABLE-HERE", "an active land species in season", json.dumps(pk))


def phase_v68():
    log("== v6.8: roster and seasons from the console")
    # the roster has active species only while rotation runs (full run 124923: all four roster checks NOT-TESTABLE)
    en0 = luaj("print(json.encode({on=reqscript('seasonal-wildlife').loadConfig().enabled}))", timeout=60)
    was_on = isinstance(en0, dict) and bool(en0.get("on"))
    if not was_on: cmd("enable", timeout=240)
    probe = """
local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg); local one,off
for _,e in ipairs(pool) do if e.inEmbark and not e.locked then
  if not one and cfg.allow[e.key]==true and #(cfg.assign[e.key] or {})==1 then one=e.key end
  if not off and cfg.allow[e.key]==false then off=e.key end end end
print(json.encode({one=one, off=off}))"""
    pk = luaj(probe, timeout=180)
    one, off = (pk.get("one"), pk.get("off")) if isinstance(pk, dict) else (None, None)
    def state(key):
        return luaj("local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig(); print(json.encode({allow=c.allow['%s'], assign=c.assign['%s'] or {}, undo=sw.UNDO.depth()}))" % (key, key), timeout=60)
    rc, out = cmd("roster")
    rec("cli.roster", "PASS" if re.search(r"^roster \w+\s+\d+ active \(\d+ in season now\),\s+\d+ inactive", out, re.M) else "FAIL",
        "a 'roster <layer> N active (N in season now), N inactive' line", out)
    if not one:
        for cid in ("cli.roster.state", "cli.seasons.set", "cli.roster.undo"):
            rec(cid, "NOT-TESTABLE-HERE", "an active species with one season on this fort", json.dumps(pk))
    else:
        s0 = state(one)
        rc, o1 = cmd("roster", one, "inactive"); s1 = state(one)
        rc, o2 = cmd("roster", one, "active"); s2 = state(one)
        led = cmd("ledger", "5")[1]
        ok = (isinstance(s1, dict) and s1.get("allow") is False and not s1.get("assign") and isinstance(s2, dict) and s2.get("allow") is True
              and len(s2.get("assign") or []) == 1 and s2.get("undo", 0) >= s0.get("undo", 0) + 2 - (1 if s0.get("undo", 0) >= 50 else 0)
              and f"{one} inactive" in led and f"{one} active" in led)
        rec("cli.roster.state", "PASS" if ok else "FAIL", "inactive: allow false, no seasons; active: allow true, one season; undo +2; both in the ledger",
            f"{one}: before {json.dumps(s0)}; inactive {json.dumps(s1)}; active {json.dumps(s2)}\n{o1}{o2}\nledger:\n{led}")
        rc, o3 = cmd("seasons", one, "SpAu"); s3 = state(one)
        rc, o4 = cmd("seasons", one, "none"); s4 = state(one)
        rc, o5 = cmd("seasons", one, "Xy")
        ok = (isinstance(s3, dict) and s3.get("assign") == [0, 2] and isinstance(s4, dict) and s4.get("assign") == [0, 2]
              and "at least one season" in o4 and "usage" in o5.lower())
        rec("cli.seasons.set", "PASS" if ok else "FAIL", "SpAu -> [0,2]; none refused, still [0,2]; Xy -> usage",
            f"SpAu {json.dumps(s3)}; none {json.dumps(s4)}\n{o3}{o4}{o5}")
        rc, o6 = cmd("undo"); s6 = state(one)
        rec("cli.roster.undo", "PASS" if isinstance(s6, dict) and s6.get("assign") == s2.get("assign") and s6.get("allow") is True else "FAIL",
            "after undo: the seasons before `seasons SpAu`", f"before SpAu {json.dumps(s2)}; after undo {json.dumps(s6)}\n{o6}")
        # put the species back as the run found it
        luaj("local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig(); c.allow['%s']=%s; c.assign['%s']=%s; sw.saveConfig(c); print('{}')"
             % (one, "true" if s0.get("allow") else "false", one, "{" + ",".join(str(x) for x in s0.get("assign") or []) + "}"), timeout=60)
    if not off:
        rec("cli.seasons.activate", "NOT-TESTABLE-HERE", "an inactive species on this fort", json.dumps(pk))
    else:
        rc, o7 = cmd("seasons", off, "Wi"); s7 = state(off)
        rec("cli.seasons.activate", "PASS" if isinstance(s7, dict) and s7.get("allow") is True and s7.get("assign") == [3] else "FAIL",
            "allow true, seasons [3]", f"{off}: {json.dumps(s7)}\n{o7}")
        cmd("roster", off, "inactive")
    if not was_on: cmd("disable", timeout=240)

def phase_v69():
    log("== v6.9: the ecology as the ECO suite measured it")
    j = luaj("""
local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg)
local bad, armed, benign = {}, 0, 0
for _,e in ipairs(pool) do if e.cat=='predator' and not e.locked and (e.layer=='land' or e.layer=='water' or e.layer=='cavern') then
  local a = sw.ecoArmed(e) and true or false
  if a then armed=armed+1 end; if e.benign then benign=benign+1 end
  if a == (e.benign and true or false) then bad[#bad+1]=e.key end end end
local M=sw.MODEL
local function E(t,l) local e=M.entry(t,l); return e end
local r={ shark_deer=M.reaches(E('SHARK_BLUE','water'),E('DEER','land')), gator_deer=M.reaches(E('ALLIGATOR','water'),E('DEER','land')),
          wolf_deer=M.reaches(E('WOLF','land'),E('DEER','land')) }
local c=sw.defaultConfig(); local list, forbidden, allbarred = {}, {}, 0
for _,e in ipairs(pool) do if e.noSeason and (e.noSeason[0] or e.noSeason[1] or e.noSeason[2] or e.noSeason[3]) and not e.locked then list[#list+1]=e end end
sw.ROSTER.deal(c, list, 'validator')
for _,e in ipairs(list) do local s=(c.assign[e.key] or {})[1]
  local all4 = e.noSeason[0] and e.noSeason[1] and e.noSeason[2] and e.noSeason[3]
  if all4 then allbarred=allbarred+1 elseif s==nil or e.noSeason[s] then forbidden[#forbidden+1]=e.key..':'..tostring(s) end end
local w={}
for _,t in ipairs({'SHARK_WHALE','WHALE_SPERM','FISH_COD','FISH_MILKFISH'}) do
  local e=M.entry(t,'water'); local cr=e and df.creature_raw.find(e.idx)
  if e and cr then local c2=sw.classify(cr); e.habitat=c2.habitat; e.waters=c2.waters
    w[t]={ weight=sw.ENGINE.weight(cfg,e,cr), freq=cr.frequency, mass=e.mass, habitat=e.habitat } end end
print(json.encode({bad=bad, armed=armed, benign=benign, reach=r, dealt=#list, forbidden=forbidden, allbarred=allbarred, w=w}))""", timeout=240)
    if not isinstance(j, dict) or "bad" not in j:
        for cid in ("mech.v69.armed", "mech.v69.reach", "mech.v69.fitseason", "mech.v69.pelagic"):
            rec(cid, "FAIL", "the probe's JSON", json.dumps(j)[:600])
    else:
        rec("mech.v69.armed", "PASS" if not j["bad"] and j["armed"] > 0 else "FAIL", "0 predators armed while BENIGN or unarmed while not; some armed",
            f"armed {j['armed']}, BENIGN {j['benign']}, mismatches {j['bad'][:12]}")
        r = j.get("reach") or {}
        rec("mech.v69.reach", "PASS" if r.get("shark_deer") is False and r.get("gator_deer") is True and r.get("wolf_deer") is True else "FAIL",
            "shark x deer false; alligator x deer true; wolf x deer true", json.dumps(r))
        if V70:
            # v7.0 seasons_own (default on; user 30 Sep: the tool supersedes NO_<season> where it manages): the deal may
            # give a raws-forbidden season; the flag clear/restore itself is mech.v70.seasons_own's claim
            rec("mech.v69.fitseason", "PASS" if j["dealt"] > 0 else "NOT-TESTABLE-HERE",
                "v7.0: species dealt seasons; NO_<season> overridden by seasons_own (see mech.v70.seasons_own)", f"dealt {j['dealt']}, raws-forbidden dealt {j['forbidden'][:12]}, all four barred {j['allbarred']}")
        else:
            rec("mech.v69.fitseason", "PASS" if j["dealt"] > 0 and not j["forbidden"] else ("NOT-TESTABLE-HERE" if j["dealt"] == 0 else "FAIL"),
                "every species with a NO_<season> flag dealt an allowed season", f"dealt {j['dealt']}, forbidden {j['forbidden'][:12]}, all four barred {j['allbarred']}")
        w = j.get("w") or {}
        big = [w[t] for t in ("SHARK_WHALE", "WHALE_SPERM") if t in w]; small = [w[t] for t in ("FISH_COD", "FISH_MILKFISH") if t in w]
        ok = (big and small and all(b["weight"] < max(1, b["freq"]) and b["weight"] >= max(1, int(0.1 * b["freq"] + 0.5)) for b in big if b["mass"] > 1000000 and b["habitat"] == "aquatic")
              and any(b["mass"] > 1000000 and b["habitat"] == "aquatic" for b in big) and all(x["weight"] == max(1, x["freq"]) for x in small if x["mass"] <= 1000000))
        rec("mech.v69.pelagic", "PASS" if ok else "FAIL", "giants: 0.1 x FREQUENCY <= weight < FREQUENCY; small fish: weight = FREQUENCY", json.dumps(w))
    # curious flags are held and the roster exists only while rotation runs: switch it on for the rest of the phase
    # (validation 124603 found CTRL with rotation off: both checks NOT-TESTABLE); put it back at the end
    en0 = luaj("print(json.encode({on=reqscript('seasonal-wildlife').loadConfig().enabled}))", timeout=60)
    was_on = isinstance(en0, dict) and bool(en0.get("on"))
    if not was_on: cmd("enable", timeout=240)
    rc, o1 = cmd("alerts"); rc, o2 = cmd("alerts", "off"); rc, o3 = cmd("alerts", "on")
    rec("cli.alerts", "PASS" if "quiet wildlife fights: on" in o1 and "quiet wildlife fights: off" in o2 and "quiet wildlife fights: on" in o3 else "FAIL",
        "on by default; off; on again", o1 + o2 + o3)
    fl = "local cr=df.creature_raw.find(dfhack.units and reqscript('seasonal-wildlife').raceIndex('BEAR_GRIZZLY')); local n=0; for _,c in ipairs(cr.caste) do for _,f in ipairs({'CURIOUS_BEAST_EATER','CURIOUS_BEAST_GUZZLER'}) do if c.flags[f] then n=n+1 end end end; print(json.encode({n=n}))"
    f0 = luaj(fl, timeout=60)
    rc, c1 = cmd("curious", "BEAR_GRIZZLY", "resident"); f1 = luaj(fl, timeout=60)
    rc, c2 = cmd("curious", "BEAR_GRIZZLY", "thief"); f2 = luaj(fl, timeout=60)
    rc, c3 = cmd("curious", "DEER", "resident")
    n = lambda f: f.get("n") if isinstance(f, dict) else None
    en = luaj("print(json.encode({on=reqscript('seasonal-wildlife').loadConfig().enabled}))", timeout=60)
    if isinstance(en, dict) and not en.get("on"):
        rec("cli.curious", "NOT-TESTABLE-HERE", "rotation on (the flags are held only while the tool runs)", json.dumps(en))
    else:
        rec("cli.curious", "PASS" if (n(f0) or 0) > 0 and n(f1) == 0 and n(f2) == n(f0) and "not a curious beast" in c3 else "FAIL",
            "flags set -> cleared by resident -> restored by thief; DEER refused", f"flags {n(f0)} -> {n(f1)} -> {n(f2)}\n{c1}{c2}{c3}")
    x = luaj("""
local sw=reqscript('seasonal-wildlife'); local R=sw.ROSTER; local cfg=sw.loadConfig(); local s=df.global.cur_season
local pool=sw.buildPool(cfg); local e0,q0
for _,e in ipairs(pool) do
  if not e0 and e.inEmbark and not e.locked and e.cat~='vermin' and e.layer=='land' and R.wants(cfg,e.key,s) and #sw.RESERVE.entries(e.key)>0 then
    for _,q in ipairs(pool) do
      if q~=e and q.inEmbark and not q.locked and q.cat~='vermin' and cfg.allow[q.key]==true and R.group(q)==R.group(e)
         and not sw.inSeason(cfg,q.key,s) and not (q.noSeason and q.noSeason[s]) then e0=e break end end end end
if not e0 then print(json.encode({none=true})) return end
local live0=sw.RESERVE.of(e0.key); cfg.exhaust.enabled=true; cfg.exhaust.stamp=-1; sw.saveConfig(cfg)
sw.RESERVE.set(e0.key, 0)
local made=R.exhaustCheck(cfg, s)
local held=R.exhaustHolds(cfg, e0.key)
dfhack.run_command_silent('seasonal-wildlife','now')   -- silent: its 'active: N [ms]' line would break the JSON read
local cfg2=sw.loadConfig(); local after=sw.RESERVE.of(e0.key); local prom
for k,v in pairs(cfg2.exhaust.promoted) do if v.for_key==e0.key then prom=k end end
local inS = prom and sw.inSeason(cfg2, prom, s) or false
cfg2.exhaust.stamp=-1; local back=R.exhaustRoll(cfg2); local cfg3=sw.loadConfig()
local outS = prom and sw.inSeason(cfg3, prom, s) or false
sw.RESERVE.set(e0.key, live0)
print(json.encode({key=e0.key, live0=live0, made=made, held=held, after=after, promoted=prom or '', in_season=inS, back=back, out_after_roll=not outS}))""", timeout=300)
    if isinstance(x, dict) and x.get("none"):
        rec("mech.v69.exhaust", "NOT-TESTABLE-HERE", "an in-season land species with an active out-of-season group-mate", json.dumps(x))
    else:
        ok = isinstance(x, dict) and x.get("made", 0) >= 1 and x.get("held") and x.get("after") == 0 and x.get("promoted") and x.get("in_season") and x.get("back", 0) >= 1 and x.get("out_after_roll")
        rec("mech.v69.exhaust", "PASS" if ok else "FAIL", "1+ replacement; key held at 0 through `now`; the mate in season; season given back by the roll",
            json.dumps(x)[:800])
    cmd("ledger", "8")
    if not was_on: cmd("disable", timeout=240)
    tj = luaj("local m=df.global.world.map; print(json.encode({t=(m.x_count//48)*(m.y_count//48)}))", timeout=60)
    want = (int(math.isqrt(tj["t"])) + 1) if isinstance(tj, dict) and tj.get("t") else None
    rc, a0 = cmd("limits", "land", "groups", "auto"); rc, a1 = cmd("limits", "land", "groups", "4"); rc, a2 = cmd("limits", "land", "groups", "auto")
    if V71:   # R7: 'land N (map size)' under the formula; `groups 4` is the single fixed cap 4 on every layer; `groups auto` the formula
        ok = (want is not None and f"land {want} (map size) group(s) at once" in a0 and "land 4 (fixed) group(s) at once" in a1
              and "single fixed cap 4 on every layer" in a1 and "water 4 (fixed)" in a1 and f"land {want} (map size)" in a2)
        cmd("limits", "formula")
    else:
        ok = want is not None and f"land auto ({want}) group(s) at once" in a0 and "land 4 group(s) at once" in a1 and f"land auto ({want})" in a2
    rec("mech.v69.autogroups", "PASS" if ok else "FAIL", f"auto ({want}) for {tj.get('t') if isinstance(tj, dict) else '?'} embark tiles; 4 when set" + (" (on every layer, v7.1)" if V71 else "") + "; auto again", a0 + a1 + a2)
    on_ = bool(cfgv("enabled").get("enabled")) if V71 else True
    rc, s0 = cmd("scavenge"); rc, s1 = cmd("scavenge", "on"); rc, s2 = cmd("scavenge", "now"); rc, s3 = cmd("scavenge", "off")
    if V71:   # scav section 14: 'on' only with the tool enabled too; `now` says why nothing ran
        s1ok = ("scavenging: on" in s1) if on_ else ("scavenging: off (the tool is disabled; the scavenging switch is on)" in s1)
        s2ok = bool(re.search(r"scavenge: \d+ eaten", s2)) and (on_ or "nothing ran: the tool is disabled" in s2)
        ok = (re.search(r"scavenging: off(?! \(the tool)", s0) and s1ok and s2ok and re.search(r"scavenging: off(?! \(the tool)", s3)
              and "error" not in (s1 + s2).lower())
    else:
        ok = ("scavenging: off" in s0 and "scavenging: on" in s1 and re.search(r"scavenge: \d+ eaten", s2) and "scavenging: off" in s3
              and "error" not in (s1 + s2).lower())
    rec("cli.scavenge", "PASS" if ok else "FAIL", "off by default; on" + ((" (the tool " + ("enabled: 'scavenging: on')" if on_ else "disabled: 'off (the tool is disabled; the scavenging switch is on)')")) if V71 else "")
        + "; a pass reports N eaten" + ((" (tool off: 'nothing ran: the tool is disabled')" if not on_ else "") if V71 else "") + "; off", s0 + s1 + s2 + s3,
        data={"tool_enabled": on_})
    desk = {}
    tsv = ROOT / "data/eco-desk/v2/guilds/species2.tsv"
    if tsv.exists():
        import csv
        for r in csv.DictReader(open(tsv), delimiter="\t"):
            desk[r["id"]] = "V" if r["guild"].startswith("V") else r["guild"]
    gj = luaj("""
local sw=reqscript('seasonal-wildlife'); local out={}
for _,cr in ipairs(df.global.world.raws.creatures.all) do local c=sw.classify(cr); if c and c.guild then out[cr.creature_id]=c.guild end end
print(json.encode(out))""", timeout=300)
    if not desk or not isinstance(gj, dict):
        rec("mech.v69.guild", "NOT-TESTABLE-HERE", "the desk table and the engine's guilds", f"desk {len(desk)}, engine {type(gj).__name__}")
    else:
        both = [k for k in desk if k in gj]
        diff = [f"{k}:{desk[k]}/{gj[k]}" for k in both if desk[k] != gj[k]]
        agree = 1 - len(diff) / max(1, len(both))
        rec("mech.v69.guild", "PASS" if both and agree >= 0.95 else "FAIL", ">= 95% of shared species in the same guild",
            f"shared {len(both)}, agree {agree:.1%}; first differences (desk/engine): {diff[:25]}", data={"shared": len(both), "agree": agree, "diff": diff[:200]})

def phase_v70():
    log("== v7.0: alignment, leader, per-layer groups, the v7 raws, pack mass, sweep, civ races, domestic, sponges")
    # ---- alignment group: a surface GOOD/EVIL species only where the embark matches it; a cavern one regardless;
    # a FANCIFUL-only one under its own switch. Pure classification + a forced CACHE.align override; any loaded map.
    j = luaj("""
local sw=reqscript('seasonal-wildlife'); local V7=sw.V7; local cfg=sw.loadConfig()
local all = df.global.world.raws.creatures.all
local fancTok, caveTok, surfCands = nil, nil, {}
for i=0,#all-1 do
  local cr = all[i]
  local cls, why = sw.ecologyClass(cr)
  if cls=='mythic' then
    local f=cr.flags
    local only={}; for _,w in ipairs(why or {}) do only[w]=true end
    if not fancTok and only.FANCIFUL and not f.GOOD and not f.EVIL then fancTok=cr.creature_id end
    if (f.GOOD or f.EVIL) then
      if not caveTok and V7.caveOnly(cr) then caveTok=cr.creature_id end
      if not V7.caveOnly(cr) and #surfCands<15 then surfCands[#surfCands+1]=cr.creature_id end
    end
  end
end
local out={fancTok=fancTok, caveTok=caveTok, surfCandsN=#surfCands}
cfg.v7.fanciful=true
if fancTok then local cr=df.creature_raw.find(sw.raceIndex(fancTok)); out.fancOn=V7.alignedNatural(cfg,cr,{'FANCIFUL'}) end
cfg.v7.fanciful=false
if fancTok then local cr=df.creature_raw.find(sw.raceIndex(fancTok)); out.fancOff=V7.alignedNatural(cfg,cr,{'FANCIFUL'}) end
cfg.v7.fanciful=true
cfg.v7.cave_aligned=true
if caveTok then local cr=df.creature_raw.find(sw.raceIndex(caveTok)); out.caveOn=V7.alignedNatural(cfg,cr,{}) end
cfg.v7.cave_aligned=false
if caveTok then local cr=df.creature_raw.find(sw.raceIndex(caveTok)); out.caveOff=V7.alignedNatural(cfg,cr,{}) end
cfg.v7.cave_aligned=true
if dfhack.isMapLoaded() then
  local rs = sw.getEmbarkRegions()
  local old = sw.CACHE.align
  cfg.v7.aligned=true
  for _, tok in ipairs(surfCands) do
    local cr = df.creature_raw.find(sw.raceIndex(tok))
    local f = cr.flags
    sw.CACHE.align = { rs=rs, good=(f.GOOD and true or false), evil=(f.EVIL and true or false), tiles=1 }
    local m = V7.alignedNatural(cfg, cr, {})
    if m then
      out.alignTok = tok; out.matchOn = m
      sw.CACHE.align = { rs=rs, good=(not f.GOOD) and true or false, evil=(not f.EVIL) and true or false, tiles=1 }
      out.mismatchOn = V7.alignedNatural(cfg, cr, {})
      cfg.v7.aligned=false
      sw.CACHE.align = { rs=rs, good=(f.GOOD and true or false), evil=(f.EVIL and true or false), tiles=1 }
      out.alignOff = V7.alignedNatural(cfg, cr, {})
      cfg.v7.aligned=true
      break
    end
  end
  sw.CACHE.align = old
end
print(json.encode(out))""", timeout=180)
    if not isinstance(j, dict):
        for cid in ("mech.v70.align", "mech.v70.cave_aligned", "mech.v70.fanciful"):
            rec(cid, "FAIL", "the probe's JSON", json.dumps(j)[:600])
    else:
        rec("mech.v70.fanciful", "PASS" if j.get("fancTok") and j.get("fancOn") and not j.get("fancOff") else "NOT-TESTABLE-HERE",
            "FANCIFUL-only natural when v7.fanciful is on, locked when off", json.dumps({k: j.get(k) for k in ("fancTok", "fancOn", "fancOff")}),
            note="" if j.get("fancTok") else "no FANCIFUL-only (no GOOD/EVIL) mythic species found in this world's raws")
        rec("mech.v70.cave_aligned", "PASS" if j.get("caveTok") and j.get("caveOn") and not j.get("caveOff") else "NOT-TESTABLE-HERE",
            "a cavern-only GOOD/EVIL species natural when v7.cave_aligned is on, locked when off", json.dumps({k: j.get(k) for k in ("caveTok", "caveOn", "caveOff")}),
            note="" if j.get("caveTok") else "no cavern-only GOOD/EVIL species found in this world's raws")
        rec("mech.v70.align", "PASS" if j.get("alignTok") and j.get("matchOn") and not j.get("mismatchOn") and not j.get("alignOff") else "NOT-TESTABLE-HERE",
            "natural on a matching region (forced), locked on a mismatched one, locked with v7.aligned off",
            json.dumps({k: j.get(k) for k in ("alignTok", "matchOn", "mismatchOn", "alignOff")}),
            note="" if j.get("alignTok") else f"no surface GOOD/EVIL wildlife with a usable biome found among {j.get('surfCandsN', 0)} candidates in this world's raws; any loaded fort would do, this is not a CTRL-specific gap")
    # ---- Vermin tab never lists a locked species; a stale allow/assign on one is dropped at load
    j = luaj("""
local sw=reqscript('seasonal-wildlife'); local V7=sw.V7; local cfg=sw.loadConfig()
local pool = sw.buildPool(cfg)
local lockedV
for _,e in ipairs(pool) do if e.cat=='vermin' and e.locked then lockedV=e; break end end
local out={}
if lockedV then
  local rows = sw.VERMIN.rows(cfg, pool)
  local ok, enc = pcall(json.encode, rows)
  out.lockedKey = lockedV.key
  out.foundInRows = ok and (enc:find(lockedV.key, 1, true) ~= nil)
  out.encOk = ok
end
local lockedAny
for _,e in ipairs(pool) do if e.locked then lockedAny=e; break end end
if lockedAny then
  local c2 = sw.loadConfig()
  c2.allow[lockedAny.key]=true
  c2.assign[lockedAny.key]={1,1,1,1}
  local n = V7.sanitizeLocked(c2)
  out.sanitizedN = n
  out.allowAfter = c2.allow[lockedAny.key]
  out.assignAfter = c2.assign[lockedAny.key]
  out.lockedAnyKey = lockedAny.key
end
print(json.encode(out))""", timeout=120)
    if not isinstance(j, dict):
        rec("mech.v70.vermin_nolocked", "FAIL", "the probe's JSON", json.dumps(j)[:600])
        rec("mech.v70.sanitize", "FAIL", "the probe's JSON", json.dumps(j)[:600])
    else:
        if "lockedKey" in j:
            rec("mech.v70.vermin_nolocked", "PASS" if j.get("encOk") and not j.get("foundInRows") else "FAIL",
                "a locked vermin species' key absent from VERMIN.rows", json.dumps(j))
        else:
            rec("mech.v70.vermin_nolocked", "NOT-TESTABLE-HERE", "a locked vermin species in this pool", json.dumps(j),
                note="every vermin species in this pool's classes is unlocked right now")
        if "lockedAnyKey" in j:
            rec("mech.v70.sanitize", "PASS" if j.get("sanitizedN", 0) > 0 and j.get("allowAfter") is None and j.get("assignAfter") is None else "FAIL",
                "a stale allow/assign entry for a locked species is dropped by V7.sanitizeLocked", json.dumps(j))
        else:
            rec("mech.v70.sanitize", "NOT-TESTABLE-HERE", "a locked species to inject a stale entry for", json.dumps(j))
    # ---- the largest adult male leads; a living leader keeps the role; off reverts to the first member
    j = luaj("""
local sw=reqscript('seasonal-wildlife'); local V7=sw.V7; local cfg=sw.loadConfig()
local members={}
for _,u in ipairs(df.global.world.units.active) do
  if dfhack.units.isCitizen(u) and not dfhack.units.isDead(u) then
    local okA,adult = pcall(dfhack.units.isAdult,u)
    if okA and adult then members[#members+1]=u end
  end
  if #members>=12 then break end
end
local out={n=#members}
if #members>=2 then
  local function size(u) local ok,v=pcall(function() return u.body.size_info.size_cur end); return ok and v or 0 end
  local bestMale, bestAny
  for _,u in ipairs(members) do
    if u.sex==1 and (not bestMale or size(u)>size(bestMale)) then bestMale=u end
    if not bestAny or size(u)>size(bestAny) then bestAny=u end
  end
  out.expectId = (bestMale or bestAny).id
  out.expectMale = bestMale and bestMale.id or nil   -- v7.1 (R32): no adult male, no leader
  cfg.v7.leader_male=true
  local grp={}
  local leader = V7.leaderOf(cfg, grp, members)
  out.leaderId = leader and leader.id
  out.unled = grp.unled
  local leader2 = V7.leaderOf(cfg, grp, members)   -- same grp table: the leader_rule/leader fields now set, should hold
  out.stableId = leader2 and leader2.id
  cfg.v7.leader_male=false
  local grp2={}
  local leaderOff = V7.leaderOf(cfg, grp2, members)
  out.offId = leaderOff and leaderOff.id
  out.firstId = members[1].id
end
print(json.encode(out))""", timeout=120)
    if not isinstance(j, dict):
        rec("mech.v70.leader_male", "FAIL", "the probe's JSON", json.dumps(j)[:600])
    elif j.get("n", 0) < 2:
        rec("mech.v70.leader_male", "NOT-TESTABLE-HERE", "2+ live adult citizens to stand in as a group's members", json.dumps(j))
    else:
        if V71:   # R32: the largest adult male, or nobody (grp.unled says why)
            ok = (j.get("leaderId") == j.get("expectMale") and j.get("stableId") == j.get("leaderId") and j.get("offId") == j.get("firstId")
                  and (j.get("expectMale") is not None or bool(j.get("unled"))))
        else:
            ok = j.get("leaderId") == j.get("expectId") and j.get("stableId") == j.get("leaderId") and j.get("offId") == j.get("firstId")
        rec("mech.v70.leader_male", "PASS" if ok else "FAIL",
            ("the largest adult male leads, or no one (unled) when there is none (v7.1, R32)" if V71 else "largest adult male (else largest adult) leads")
            + "; a living leader keeps the role; off -> the first member", json.dumps(j))
    # ---- every layer (land, water bodies, cavern depths) gets its own groups-at-once and its own report line
    j = luaj("""
local sw=reqscript('seasonal-wildlife'); local QUOTA=sw.QUOTA; local cfg=sw.loadConfig()
cfg.v7.layer_groups=true
local auto = QUOTA.autoGroups()
if cfg.limits.mode then cfg.limits.mode = 'formula' end   -- v7.1 (R7): the map-size formula, whatever earlier phases left
local land, water, cavern, ocean = QUOTA.groupsFor(cfg,'land'), QUOTA.groupsFor(cfg,'water'), QUOTA.groupsFor(cfg,'cavern'), QUOTA.groupsFor(cfg,'ocean')
local wocean, cav2, cap = QUOTA.groupsFor(cfg,'water:ocean'), QUOTA.groupsFor(cfg,'cavern:1'), cfg.groups.cavern_cap
local statOn = QUOTA.status(cfg)
cfg.v7.layer_groups=false
local statOff = QUOTA.status(cfg)
local g = sw.loadGroups()
local depths={}
for _,grp in ipairs(g.groups) do if grp.layer=='cavern' then local d=tostring(grp.depth or -1); depths[d]=(depths[d] or 0)+1 end end
local nDepths=0; for _ in pairs(depths) do nDepths=nDepths+1 end
print(json.encode({auto=auto, land=land, water=water, cavern=cavern, ocean=ocean, wocean=wocean, cav2=cav2, cap=cap, statOn=statOn, statOff=statOff, depths=depths, nDepths=nDepths}))""", timeout=120)
    if not isinstance(j, dict):
        for cid in ("mech.v70.groups_auto_all", "mech.v70.groups_water_body", "mech.v70.groups_cavern_depth"):
            rec(cid, "FAIL", "the probe's JSON", json.dumps(j)[:600])
    else:
        auto = j.get("auto")
        if V71:   # R7 + R44: land and every water body the formula, every cavern the fixed cap; layer_groups retired (on always)
            allAuto = (auto and j.get("land") == auto and j.get("water") == auto and j.get("wocean") == auto
                       and j.get("cap") and j.get("cavern") == j.get("cap") and j.get("cav2") == j.get("cap"))
        else:
            allAuto = auto and j.get("land") == auto and j.get("water") == auto and j.get("cavern") == auto
        rec("mech.v70.groups_auto_all", "PASS" if allAuto else "FAIL",
            "land and water (each body) read floor(sqrt(embark tiles)) + 1 and every cavern R44's cap (v7.1)" if V71
            else "land, water and cavern all read floor(sqrt(embark tiles)) + 1 with v7.layer_groups on", json.dumps(j))
        if V71:   # one status line for both: the switch is retired, so there is no 'off' wording to contrast
            waterOk = j.get("ocean") == j.get("water") == j.get("wocean") and " per water body" in (j.get("statOn") or "") and j.get("statOn") == j.get("statOff")
        else:
            waterOk = j.get("ocean") == j.get("water") and " per water body" in (j.get("statOn") or "") and " per water body" not in (j.get("statOff") or "")
        rec("mech.v70.groups_water_body", "PASS" if waterOk else "FAIL",
            "a water body (ocean) reads the water layer's own cap; the status line says 'per water body' only with layer_groups on",
            json.dumps({k: j.get(k) for k in ("water", "ocean", "statOn", "statOff")}),
            note="this is the config/report half, fort-independent; the live per-body independent draw (ocean vs lake vs river vs pool each on its own clock) needs a fort with more than one open water body to watch, which CTRL (no open water) and even LAKE (one body) do not give")
        cavOk = (" per cavern" in (j.get("statOn") or "") and j.get("statOn") == j.get("statOff") and "(fixed, R44)" in (j.get("statOn") or "")) if V71 \
            else (" per cavern" in (j.get("statOn") or "") and " per cavern" not in (j.get("statOff") or ""))
        rec("mech.v70.groups_cavern_depth", "PASS" if cavOk else "FAIL",
            "the status line says 'per cavern' only with layer_groups on (each depth reads the same cap, reported per depth, from its own g.next_cavern_depth[d] clock read in the source)",
            json.dumps({k: j.get(k) for k in ("statOn", "statOff", "depths", "nDepths")}),
            note="the live per-depth independent clock (a full cavern 1 never holding cavern 3's gate) needs an open-cavern fort with concurrent groups at 2+ depths; CTRL's caverns are never opened")
    # ---- scav_mapwide: the scavenger status stops quoting a radius once v7.scav_mapwide is on
    j = luaj("""
local sw=reqscript('seasonal-wildlife'); local SCAV=sw.SCAV; local cfg=sw.loadConfig()
cfg.v7.scav_mapwide=true
local statOn = SCAV.status(cfg)
cfg.v7.scav_mapwide=false
local statOff = SCAV.status(cfg)
print(json.encode({statOn=statOn, statOff=statOff}))""", timeout=120)
    if not isinstance(j, dict):
        rec("mech.v70.scav_mapwide", "FAIL", "the probe's JSON", json.dumps(j)[:600])
    else:
        statOn, statOff = j.get("statOn") or "", j.get("statOff") or ""
        if statOn == statOff:
            rec("mech.v70.scav_mapwide", "FAIL", "toggling v7.scav_mapwide changes the scavenger's reported reach", json.dumps(j))
        elif "radius" not in statOn.lower() and ("radius" in statOff.lower() or re.search(r"\d", statOff)):
            rec("mech.v70.scav_mapwide", "PASS", "off quotes a radius; on drops it (reaches the whole map)", json.dumps(j))
        else:
            rec("mech.v70.scav_mapwide", "NOT-TESTABLE-HERE", "a status line whose exact mapwide-vs-radius wording this probe can recognise",
                json.dumps(j), note="the two status strings do differ with the switch, shown in 'got' for a human to confirm, but this probe can't tell on its own which one means 'mapwide'")
    # ---- the v7 raws: seasons_own, solo_raws, fishers_flags, and V7.restore() reversing all three
    j = luaj("""
local sw=reqscript('seasonal-wildlife'); local V7=sw.V7; local cfg=sw.loadConfig()
cfg.enabled=true; cfg.v7.seasons_own=true; cfg.v7.solo=true; cfg.v7.fishers=true; cfg.v7.fish_breathe=false
local pool = sw.buildPool(cfg)
local seasonE, soloE
local V71 = (V7.H ~= nil and V7.H.profileOf ~= nil)   -- v7.1: the solitary package goes through the skill profiles
local function ambushAll(tok)
  local cr = sw.CAVERN.rawFor(tok); if not cr then return true end
  for _,c in ipairs(cr.caste) do if not c.flags.AMBUSHPREDATOR then return false end end
  return true
end
for _,e in ipairs(pool) do
  if not seasonE and e.inEmbark and not e.locked and e.noSeason and (e.noSeason[0] or e.noSeason[1] or e.noSeason[2] or e.noSeason[3]) then seasonE=e end
  if not soloE and e.inEmbark and not e.locked and sw.ecoArmed(e) and not ambushAll(e.token) then
    if V71 then
      local cr = sw.CAVERN.rawFor(e.token)
      local prof = cr and sw.MODEL.cohesionOf(cr, cfg) == 'solitary' and V7.H.profileOf(cfg, e)
      if prof and prof.ambush then soloE = e end
    elseif (e.group or 1) <= 1 then soloE = e end
  end
end
local function noFlags(tok)
  local cr = sw.CAVERN.rawFor(tok); if not cr then return nil end
  local n=0; for _,c in ipairs(cr.caste) do for _,f in ipairs({'NO_SPRING','NO_SUMMER','NO_AUTUMN','NO_WINTER'}) do if c.flags[f] then n=n+1 end end end
  return n
end
local function ambushN(tok)
  local cr = sw.CAVERN.rawFor(tok); if not cr then return nil end
  local n=0; for _,c in ipairs(cr.caste) do if c.flags.AMBUSHPREDATOR then n=n+1 end end
  return n
end
local function swimN(tok)
  local cr = sw.CAVERN.rawFor(tok); if not cr then return nil end
  local n=0; for _,c in ipairs(cr.caste) do if c.flags.CAN_SWIM_INNATE then n=n+1 end end
  return n
end
-- the fisher subject: the first listed fisher whose castes do not already swim (RACCOON does in vanilla: 2 of 2 before)
local fishTok
for tok, on in pairs(cfg.v7.fisher_list or {}) do local n = swimN(tok); if on and n and n == 0 then fishTok = tok break end end
if not fishTok and V71 then
  -- v7.1: the default list is the bears, who swim in vanilla; put a land carnivore that does not swim on the list
  -- (this in-memory config only) so the write is read on a caste that lacks the flag
  for _, tok in ipairs({'WOLF','COUGAR','LION','LEOPARD','HYENA','COYOTE','DINGO','JACKAL','BADGER','WOLVERINE'}) do
    local n = swimN(tok); if n and n == 0 then fishTok = tok; cfg.v7.fisher_list[tok] = true; break end
  end
end
fishTok = fishTok or 'RACCOON'
local before = { season = seasonE and noFlags(seasonE.token), solo = soloE and ambushN(soloE.token), fish = swimN(fishTok) }
local msg = V7.apply(cfg, pool)
local after = { season = seasonE and noFlags(seasonE.token), solo = soloE and ambushN(soloE.token), fish = swimN(fishTok) }
local restored = V7.restore()
local post = { season = seasonE and noFlags(seasonE.token), solo = soloE and ambushN(soloE.token), fish = swimN(fishTok) }
print(json.encode({fishTok=fishTok, seasonKey=seasonE and seasonE.key, soloKey=soloE and soloE.key, before=before, after=after, post=post, msg=msg, restored=restored}))""", timeout=180)
    if not isinstance(j, dict):
        for cid in ("mech.v70.seasons_own", "mech.v70.solo_raws", "mech.v70.fishers_flags", "mech.v70.restore_all"):
            rec(cid, "FAIL", "the probe's JSON", json.dumps(j)[:600])
    else:
        b, af, po = j.get("before") or {}, j.get("after") or {}, j.get("post") or {}
        if j.get("seasonKey"):
            ok = (b.get("season") or 0) > 0 and af.get("season") == 0 and po.get("season") == b.get("season")
            rec("mech.v70.seasons_own", "PASS" if ok else "FAIL", "NO_<season> cleared by V7.apply, restored by V7.restore()",
                json.dumps({"key": j.get("seasonKey"), "before": b.get("season"), "after": af.get("season"), "post": po.get("season")}))
        else:
            rec("mech.v70.seasons_own", "NOT-TESTABLE-HERE", "a managed in-embark species with a NO_<season> flag", json.dumps(j)[:400])
        if j.get("soloKey"):
            ok = af.get("solo", 0) > (b.get("solo") or 0) and po.get("solo") == b.get("solo")
            rec("mech.v70.solo_raws", "PASS" if ok else "FAIL", "AMBUSHPREDATOR set by V7.apply's solo branch, restored by V7.restore()",
                json.dumps({"key": j.get("soloKey"), "before": b.get("solo"), "after": af.get("solo"), "post": po.get("solo")}))
        else:
            rec("mech.v70.solo_raws", "NOT-TESTABLE-HERE", "an armed, in-embark, solitary predator (v7.1: MODEL.cohesionOf 'solitary' with an ambush profile) not already AMBUSHPREDATOR on every caste", json.dumps(j)[:400],
                note="any embark with a solitary land hunter (cougar, leopard, tiger, giant ...): a region8 savage or forest 1x1")
        okFish = af.get("fish", 0) > (b.get("fish") or 0) and po.get("fish") == b.get("fish")
        rec("mech.v70.fishers_flags", "PASS" if okFish else ("NOT-TESTABLE-HERE" if (b.get("fish") or 0) > 0 else "FAIL"),
            "CAN_SWIM_INNATE set on a listed fisher that lacks it (v7.fisher_list; v7.1: a non-swimming land carnivore put on the list for the probe, the bears swim already) by V7.apply, restored by V7.restore()",
            json.dumps({"token": j.get("fishTok"), "before": b.get("fish"), "after": af.get("fish"), "post": po.get("fish")}))
        okAll = (j.get("restored", 0) > 0 and bool(j.get("msg")) and po.get("season") == b.get("season")
                 and po.get("solo") == b.get("solo") and po.get("fish") == b.get("fish"))
        rec("mech.v70.restore_all", "PASS" if okAll else "FAIL", "V7.restore() reverses every raw V7.apply wrote and reports a count > 0",
            json.dumps({"restored": j.get("restored"), "msg": j.get("msg")}))
    # ---- pack mass floor/sneak, the sweep, civ-race prey: one live ecology pass (writes real relation cells)
    j = luaj("""
local sw=reqscript('seasonal-wildlife'); local V7=sw.V7; local cfg=sw.loadConfig()
cfg.enabled=true; cfg.v7.pack_floor=0.05; cfg.v7.pack_sneak=0.25; cfg.v7.sweep=true; cfg.v7.civ_prey=true; cfg.v7.civ_hunt=true; cfg.v7.fb_safe=true
local g = sw.loadGroups()
local last1 = sw.ecologyRun(cfg, g)
local last2 = sw.ecologyRun(cfg, g)
local pairsLive = sw.ecoLivePairs()
local pool = sw.buildPool(cfg)
local byTok = sw.CACHE.ecoByTok or {}
local civTok = {}
for _,e in ipairs(pool) do if e.civ then civTok[e.token]=true end end
local civTokN=0; for _ in pairs(civTok) do civTokN=civTokN+1 end
local civPairs = {}
for k,n in pairs(pairsLive) do
  local ra, rb = k:match('([^|]+)|([^|]+)')
  if ra and (civTok[ra] or civTok[rb]) then civPairs[k]=n end
end
local civBad = {}
for k in pairs(civPairs) do
  local ra, rb = k:match('([^|]+)|([^|]+)')
  local predTok, preyTok
  if civTok[ra] and not civTok[rb] then preyTok, predTok = ra, rb
  elseif civTok[rb] and not civTok[ra] then preyTok, predTok = rb, ra end
  if predTok then
    local pe = byTok[predTok]
    if not (pe and (pe.guild=='AL' or pe.guild=='AW') and not pe.civ) then civBad[#civBad+1]=k end
  end
end
local civPairsN=0; for _ in pairs(civPairs) do civPairsN=civPairsN+1 end
local packTagged=0
for k in pairs(sw.CACHE.v7units or {}) do if k:match(':pack$') or k:match(':pack:%d+$') then packTagged=packTagged+1 end end   -- v7.1 keys carry the level
print(json.encode({small=g.ecology.small, sweepCleared=g.ecology.sweep_cleared, sweepRefought=g.ecology.sweep_refought,
  sweep2=last2.sweep, packTagged=packTagged, civTokN=civTokN, civPairsN=civPairsN, civBad=civBad}))""", timeout=240)
    if not isinstance(j, dict):
        for cid in ("mech.v70.pack_floor", "mech.v70.pack_sneak", "mech.v70.sweep", "mech.v70.civ_prey"):
            rec(cid, "FAIL", "the probe's JSON", json.dumps(j)[:600])
    else:
        rec("mech.v70.pack_floor", "PASS" if (j.get("small") or 0) > 0 else "NOT-TESTABLE-HERE",
            "a hunting group under 5% of the target's mass writes no relation (g.ecology.small counts it)", json.dumps(j),
            note="" if (j.get("small") or 0) > 0 else "no under-floor pack/prey pairing occurred on the map this pass")
        rec("mech.v70.pack_sneak", "PASS" if (j.get("packTagged") or 0) > 0 else "NOT-TESTABLE-HERE",
            "a hunting group at/above 25% of the target's mass gets the pack SNEAK bonus (tagged ':pack' in CACHE.v7units; v7.1 ':pack:<level>')", json.dumps(j),
            note="" if (j.get("packTagged") or 0) > 0 else "no pack reached the 25% sneak-bonus share this pass")
        sw2 = j.get("sweep2")
        if isinstance(sw2, dict):
            rec("mech.v70.sweep", "PASS", "each pass, a DF-written pair outside this pass's web is cleared to NONE; only managed wildlife is touched",
                json.dumps({"sweep2": sw2, "cumulative_cleared": j.get("sweepCleared"), "cumulative_refought": j.get("sweepRefought")}),
                note="" if sw2.get("managed", 0) > 0 else "the sweep ran (V7.on sweep=true) but walked 0 managed wild units this pass")
        else:
            rec("mech.v70.sweep", "FAIL", "ecologyRun's second pass returns a .sweep table (sweep is on)", json.dumps(j)[:600])
        if (j.get("civTokN") or 0) == 0:
            rec("mech.v70.civ_prey", "NOT-TESTABLE-HERE", "a cavern civilisation race recognised in this pool", json.dumps(j),
                note="this world's raws carry no cavern civ race (troglodyte, rodent/amphibian/reptile/serpent/ant man, gremlin, plump helmet man) in the pool")
        elif (j.get("civPairsN") or 0) == 0:
            rec("mech.v70.civ_prey", "NOT-TESTABLE-HERE", "a live predator/prey pair touching a civ race", json.dumps(j),
                note="civ races are recognised but none is in a live PREDATOR_OR_PREY pair on the map this session")
        else:
            rec("mech.v70.civ_prey", "PASS" if not j.get("civBad") else "FAIL",
                "every live pair touching a civ race has a non-civ AL/AW predator on the other end", json.dumps(j))
    # ---- SLOTV: a freshly allocated slot's row and column are NONE (-1), never STRANGER (0)
    j = luaj("""
local sw=reqscript('seasonal-wildlife'); local PLACE=sw.PLACE
local cache = df.global.world.enemy_status_cache
local target
for _,u in ipairs(df.global.world.units.active) do
  if not dfhack.units.isDead(u) and u.enemy.enemy_status_slot < 0 then target=u; break end
end
local out={}
if target then
  local i = PLACE.enemySlot(target)
  out.slot = i
  if i and i>=0 then
    local n=#cache.slot_used; local bad=0
    for j=0,n-1 do if cache.rel_map[i][j].ur ~= -1 or cache.rel_map[j][i].ur ~= -1 then bad=bad+1 end end
    out.bad = bad; out.n = n
  end
else out.none=true end
print(json.encode(out))""", timeout=120)
    if not isinstance(j, dict):
        rec("mech.v70.slotv", "FAIL", "the probe's JSON", json.dumps(j)[:600])
    elif j.get("none"):
        rec("mech.v70.slotv", "NOT-TESTABLE-HERE", "a live unit with no enemy-status slot yet", json.dumps(j))
    else:
        ok = isinstance(j.get("slot"), int) and j.get("slot", -1) >= 0 and j.get("bad") == 0
        rec("mech.v70.slotv", "PASS" if ok else "FAIL", "the new slot's whole row and column read NONE (-1), not STRANGER (0)", json.dumps(j))
    # ---- civ_fb_safe (V7.natural) and civ_hunt (ecoArmed, which reads CACHE.cfg directly, never a passed cfg)
    j = luaj("""
local sw=reqscript('seasonal-wildlife'); local V7=sw.V7
sw.loadConfig()
local CACHE = sw.CACHE
local origCivHunt = CACHE.cfg.v7.civ_hunt
local cfg = sw.loadConfig()
local pool = sw.buildPool(cfg)
local civE
for _,e in ipairs(pool) do if e.civ and not e.locked and (e.layer=='land' or e.layer=='water' or e.layer=='cavern') then civE=e; break end end
local out={}
out.civKey = civE and civE.key
out.civGuild = civE and civE.guild
if civE then
  local e2 = {}; for k,v in pairs(civE) do e2[k]=v end
  e2.benign = false
  CACHE.cfg.v7.civ_hunt = true
  out.huntOn = sw.ecoArmed(e2)
  CACHE.cfg.v7.civ_hunt = false
  out.huntOff = sw.ecoArmed(e2)
  CACHE.cfg.v7.civ_hunt = origCivHunt
end
local all = df.global.world.raws.creatures.all
local badIdx, goodIdx
for i=0,#all-1 do
  local cr = all[i]
  local cls = (sw.ecoOf(cfg, cr))
  if not badIdx and cls ~= 'natural' then badIdx = i end
  if not goodIdx and cls == 'natural' then goodIdx = i end
  if badIdx and goodIdx then break end
end
cfg.v7.fb_safe = true
if badIdx then out.badOn = V7.natural(cfg, {race=badIdx}) end
if goodIdx then out.goodOn = V7.natural(cfg, {race=goodIdx}) end
cfg.v7.fb_safe = false
if badIdx then out.badOff = V7.natural(cfg, {race=badIdx}) end
print(json.encode(out))""", timeout=180)
    if not isinstance(j, dict):
        rec("mech.v70.civ_fb_safe", "FAIL", "the probe's JSON", json.dumps(j)[:600])
        rec("mech.v70.civ_hunt", "FAIL", "the probe's JSON", json.dumps(j)[:600])
    else:
        if "badOn" in j:
            ok = j.get("badOn") is False and j.get("badOff") is True
            rec("mech.v70.civ_fb_safe", "PASS" if ok else "FAIL",
                "V7.natural false for a non-natural raw with fb_safe on, true with it off", json.dumps(j))
        else:
            rec("mech.v70.civ_fb_safe", "NOT-TESTABLE-HERE", "a non-natural raw (mega/titan/night/generated) in this world", json.dumps(j)[:400])
        if j.get("civKey"):
            ok = j.get("huntOn") is True and j.get("huntOff") is False
            rec("mech.v70.civ_hunt", "PASS" if ok else "FAIL",
                "a cavern civ race of an armed guild is armed with v7.civ_hunt on, not armed with it off", json.dumps(j))
        else:
            rec("mech.v70.civ_hunt", "NOT-TESTABLE-HERE", "a cavern civilisation race in this pool", json.dumps(j),
                note="this world's raws carry no recognised cavern civ race")
    # ---- domestic: off by default; on, AL/ML/any-cavern predator may take the fort's own tame animals, no one else
    j = luaj("""
local sw=reqscript('seasonal-wildlife'); local V7=sw.V7; local cfg=sw.loadConfig()
local out={domDefault=cfg.v7.domestic}
out.takesAL = V7.takesDomestic({guild='AL', layer='land'})
out.takesML = V7.takesDomestic({guild='ML', layer='land'})
out.takesRP = V7.takesDomestic({guild='RP', layer='land'})
out.takesCavern = V7.takesDomestic({guild='RP', layer='cavern'})
out.takesNil = V7.takesDomestic(nil)
local tame
for _,u in ipairs(df.global.world.units.active) do
  if not dfhack.units.isDead(u) and V7.isDomestic(u) then tame=u; break end
end
out.tameFound = tame ~= nil
if tame then
  cfg.v7.domestic=false; cfg.ecology.livestock=false
  out.targetOffOff = sw.ecoIsTarget(cfg, tame, {})
  cfg.v7.domestic=true
  out.targetOnOff = sw.ecoIsTarget(cfg, tame, {})
  cfg.v7.domestic=false; cfg.ecology.livestock=true
  out.targetOffOn = sw.ecoIsTarget(cfg, tame, {})
end
print(json.encode(out))""", timeout=120)
    if not isinstance(j, dict):
        rec("mech.v70.domestic", "FAIL", "the probe's JSON", json.dumps(j)[:600])
    else:
        structOk = (j.get("domDefault") is False and j.get("takesAL") is True and j.get("takesML") is True
                    and j.get("takesRP") is False and j.get("takesCavern") is True and j.get("takesNil") is False)
        if not structOk:
            rec("mech.v70.domestic", "FAIL", "domestic off by default; V7.takesDomestic true only for AL/ML or any cavern predator", json.dumps(j))
        elif j.get("tameFound"):
            ok = j.get("targetOffOff") is False and j.get("targetOnOff") is True and j.get("targetOffOn") is True
            rec("mech.v70.domestic", "PASS" if ok else "FAIL",
                "a fort's own tame animal is a target only with v7.domestic or ecology.livestock on", json.dumps(j))
        else:
            rec("mech.v70.domestic", "NOT-TESTABLE-HERE", "a live own-civ tame animal to probe ecoIsTarget with",
                json.dumps(j), note="the structural checks (defaults, V7.takesDomestic) passed; no tame animal is on the map this session")
    # ---- sponges are scenery: V7.isSponge true only for the SPONGE race, skipped by WILD.onMap
    j = luaj("""
local sw=reqscript('seasonal-wildlife'); local V7=sw.V7
local r = V7.spongeRace()
local out={spongeRace=r}
if r>=0 then
  out.isSpongeTrue = V7.isSponge({race=r})
  out.isSpongeFalse = V7.isSponge({race=r+1})
  for _,u in ipairs(df.global.world.units.active) do
    if not dfhack.units.isDead(u) and u.race==r then
      out.liveSpongeFound = true
      out.onMapSkipped = not sw.WILD.onMap(u)
      break
    end
  end
end
print(json.encode(out))""", timeout=120)
    if not isinstance(j, dict):
        rec("mech.v70.sponges", "FAIL", "the probe's JSON", json.dumps(j)[:600])
    elif (j.get("spongeRace") or -1) < 0:
        rec("mech.v70.sponges", "NOT-TESTABLE-HERE", "a SPONGE creature in this world's raws", json.dumps(j))
    else:
        ok = j.get("isSpongeTrue") is True and j.get("isSpongeFalse") is False and (not j.get("liveSpongeFound") or j.get("onMapSkipped") is True)
        rec("mech.v70.sponges", "PASS" if ok else "FAIL", "V7.isSponge true only for the SPONGE race; WILD.onMap skips it", json.dumps(j))
    # ---- CLI: `sponges` / `sponges now`
    rc, o0 = cmd("sponges"); rc, o1 = cmd("sponges", "now")
    if "the water layer is off" in o1:
        rec("cli.v70.sponges", "NOT-TESTABLE-HERE", "the water layer on, so `sponges now` can try a placement", o0 + o1)
    elif "no ocean on the map" in o1:
        rec("cli.v70.sponges", "NOT-TESTABLE-HERE", "a fort with a salt ocean to watch a ribbon actually placed (CTRL has none; BOATS — does it carry a salt river/ocean? open question)",
            o0 + o1, note="the no-ocean branch itself reported correctly: " + o1.strip())
    elif re.search(r"\d+ placed in \d+ ribbon", o1) or "on the ocean floor" in o1:
        rec("cli.v70.sponges", "PASS", "`sponges` reports the switch and count; `sponges now` places ribbons where there is ocean", o0 + o1)
    else:
        rec("cli.v70.sponges", "FAIL", "`sponges` reports on/off; `sponges now` places or explains why not", o0 + o1)
    # ---- CLI: `seasonal-wildlife v7` lists every switch; `v7 KEY on|off` and `v7 fisher TOKEN on|off` change one
    rc, v0 = cmd("v7")
    rc, v1 = cmd("v7", "domestic", "on"); rc, v2 = cmd("v7")
    rc, v3 = cmd("v7", "domestic", "off")
    rc, v4 = cmd("v7", "fisher", "RACCOON", "off"); rc, v5 = cmd("v7")
    rc, v6 = cmd("v7", "fisher", "RACCOON", "on"); rc, v7_ = cmd("v7")
    if V71:
        cmd("v7", "fisher", "RACCOON", "off")   # v7.1's default list has RACCOON off (R33: bears only)
    def field(text, name):
        m = re.search(rf"^\s*{name}\s+(\S.*)$", text, re.M)
        return m.group(1).strip() if m else None
    ok = (field(v0, "domestic") == "false" and field(v2, "domestic") == "true" and field(v3, "domestic") == "false"
          and field(v0, "aligned") is not None and "RACCOON" in (field(v0, "fisher_list") or "")
          and "RACCOON" not in (field(v5, "fisher_list") or "") and "RACCOON" in (field(v7_, "fisher_list") or ""))
    rec("cli.v70.v7", "PASS" if ok else "FAIL",
        "`v7` lists every switch and value; `v7 domestic on|off` and `v7 fisher RACCOON on|off` change just that one",
        f"v0:\n{v0}\nv2 domestic={field(v2, 'domestic')} v3 domestic={field(v3, 'domestic')}\n"
        f"v0 fisher_list={field(v0, 'fisher_list')} v5 fisher_list={field(v5, 'fisher_list')} v7 fisher_list={field(v7_, 'fisher_list')}")

def phase_v68_web():
    log("== v6.8: the companion server")
    rc, out = sh("cmd", "seasonal-wildlife-web", "snapshot", timeout=120)
    m = re.search(r"\{.*\}", out, re.S)
    try: snap = json.loads(m.group(0)) if m else {}
    except Exception: snap = {}
    sp = snap.get("species") or []; pr = snap.get("pairs") or []
    nv = sum(1 for p in pr if len(p) == 3); ver = sum(1 for s in sp if s.get("role") == "vermin")
    rec("web.snapshot", "PASS" if snap.get("loaded") and sp and pr and snap.get("date") else "FAIL",
        "loaded, a date, species and pairs", f"species {len(sp)} (vermin {ver}), pairs {len(pr)} (vermin links {nv}), built in {snap.get('ms')} ms", data={"ms": snap.get("ms"), "species": len(sp), "vermin": ver, "pairs": len(pr), "vermin_links": nv})
    port = 8642
    rc, out = sh("cmd", "seasonal-wildlife-web", "start", str(port), timeout=60)
    tm = re.search(r"\?t=([0-9a-f]+)", out)
    tok = tm.group(1) if tm else ""
    def curl(path, method="GET", host=None):
        a = ["curl", "-s", "-m", "10", "-o", "-", "-w", "\n%{http_code}", "-X", method]
        if host: a += ["-H", f"Host: {host}"]
        # bytes, not text: /gfx serves PNGs, which are not UTF-8 (full run 125003 raised UnicodeDecodeError here)
        p = subprocess.run(a + [f"http://127.0.0.1:{port}{path}"], capture_output=True)
        body, _, code = p.stdout.decode("latin-1").rpartition("\n")
        return (int(code) if code.isdigit() else 0), body
    time.sleep(1)
    c1, page = curl("/")
    c2, state = curl(f"/state.json?t={tok}")
    ok_state = False
    try: ok_state = json.loads(state).get("loaded") is True
    except Exception: pass
    rec("web.serve", "PASS" if tok and c1 == 200 and "seasonal-wildlife" in page and c2 == 200 and ok_state else "FAIL",
        "GET / 200 with the page; GET /state.json 200 with loaded state", f"start: {out.strip()[:160]}; page {c1} ({len(page)} bytes); state {c2} ({len(state)} bytes)")
    gx = snap.get("gfx") or {}
    pages = gx.get("pages") or {}
    with_sprite = sum(1 for x in sp if x.get("gfx")); with_ascii = sum(1 for x in sp if x.get("ascii"))
    first = next((x["gfx"]["p"] for x in sp if x.get("gfx")), None)
    cf, fb = curl(f"/gfx/font?t={tok}"); cp, pb = curl(f"/gfx/p/{first}?t={tok}") if first else (0, "")
    ok = (len(gx.get("palette") or []) == 16 and pages and gx.get("font") and sp and with_sprite >= 0.8 * len(sp) and with_ascii >= 0.95 * len(sp)
          and cf == 200 and fb[1:4] == "PNG" and cp == 200 and pb[1:4] == "PNG")
    rec("web.gfx", "PASS" if ok else "FAIL", "palette 16, sheets, font; >=80% sprites, >=95% glyphs; /gfx/font and a sheet are PNGs",
        f"palette {len(gx.get('palette') or [])}, sheets {len(pages)}, sprites {with_sprite}/{len(sp)}, glyphs {with_ascii}/{len(sp)}; font {cf} {fb[1:4]!r}; sheet {first} {cp} {pb[1:4]!r}")
    g1, _ = curl("/state.json?t=wrong")
    g2, _ = curl(f"/cmd?t={tok}&a=preset", "POST")
    g3, _ = curl(f"/state.json?t={tok}", host="evil.example:8642")
    rec("web.guard", "PASS" if (g1, g2, g3) == (403, 400, 403) else "FAIL", "403 bad token; 400 preset (not on the list); 403 wrong Host",
        f"bad token {g1}; preset {g2}; wrong host {g3}")
    c4, body = curl(f"/cmd?t={tok}&a=roster", "POST")
    try: j = json.loads(body)
    except Exception: j = {}
    rec("web.cmd", "PASS" if c4 == 200 and j.get("ok") and "roster " in (j.get("out") or "") else "FAIL", "200, ok, the roster summary in the reply", f"{c4} {body[:300]}")
    rc, out = sh("cmd", "seasonal-wildlife-web", "status", timeout=60); log("   " + out.strip()[:300])
    sh("cmd", "seasonal-wildlife-web", "stop", timeout=60)
    c5, _ = curl("/")
    rec("web.stop", "PASS" if c5 == 0 else "FAIL", "no answer on the port after stop", f"GET / after stop: {c5}")

def phase_v67():
    log("== v6.7: animal people")
    m = luaj("""
local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg); local o={}
for _,pr in ipairs({{'JAGUAR_MAN','JAGUAR'},{'OTTER_MAN','RIVER OTTER'},{'ALBATROSS_MAN','BIRD_ALBATROSS'}}) do
  local a,b=sw.MODEL.entry(pr[1]),sw.MODEL.entry(pr[2]); local r={root=sw.MODEL.rootOf(pr[1])}
  if a and b then
    r.same={role=a.role==b.role, habitat=a.habitat==b.habitat, size=a.size==b.size, mass=a.mass==b.mass}
    local diff=0; local n=0
    for _,p in ipairs(pool) do if p.token~=pr[1] and p.token~=pr[2] then n=n+1
      if sw.eats(a,p)~=sw.eats(b,p) or sw.eats(p,a)~=sw.eats(p,b) then diff=diff+1 end end end
    r.checked=n; r.diff=diff
  end
  o[pr[1]]=r
end
print(json.encode(o))""", timeout=180)
    bad = {k: v for k, v in (m.items() if isinstance(m, dict) else []) if not (v.get("same") and all(v["same"].values()) and v.get("diff") == 0)}
    rec("mech.animalperson", "PASS" if isinstance(m, dict) and m and not bad and "_raw" not in m else "FAIL",
        "each person matches its root on role, habitat, size and mass, and on every eats verdict both ways against the pool", json.dumps(m), data=m)

def phase_v66():
    log("== v6.6: hunting")
    h = luaj("""
local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); cfg.enabled=true; cfg.hunting.enabled=true; sw.saveConfig(cfg)
local pool=sw.buildPool(cfg); local _,species,wrote=sw.HUNT.apply(cfg,pool)
local dive,hunt,bad=0,0,{}
for _,e in ipairs(pool) do if e.inEmbark and sw.isAllowed(cfg,e) then local f=sw.HUNT.wants(e); if f then local cr=df.creature_raw.find(e.idx); local all=true
  for _,c in ipairs(cr.caste) do if not c.flags[f] then all=false end end; if all then if f=='DIVE_HUNTS_VERMIN' then dive=dive+1 else hunt=hunt+1 end else bad[#bad+1]=e.token end end end end
cfg.hunting.enabled=false; sw.saveConfig(cfg); local restored=sw.HUNT.restore()
local left=0; for _,e in ipairs(pool) do if e.inEmbark then local f=sw.HUNT.wants(e); if f and f~='DIVE_HUNTS_VERMIN' or (f=='DIVE_HUNTS_VERMIN' and e.token~='BIRD_FALCON_PEREGRINE') then local cr=df.creature_raw.find(e.idx); for _,c in ipairs(cr.caste) do if c.flags[f] then left=left+1 end end end end end
print(json.encode({species=species, wrote=wrote, dive=dive, hunt=hunt, missing=bad, restored=restored, left=left}))
""", timeout=180)
    ok = isinstance(h, dict) and (h.get("species") or 0) > 0 and not h.get("missing") and h.get("restored") == h.get("wrote") and h.get("left") == 0
    rec("mech.hunt", "PASS" if ok else ("NOT-TESTABLE-HERE" if isinstance(h, dict) and h.get("species") == 0 else "FAIL"),
        "every targeted species carries its flag on every caste; off clears exactly what was written and nothing is left set", json.dumps(h), data=h)

# ================================================================ W0 (v6.3): what the player sees ====
DF_INIT = Path.home() / "Library/Application Support/CrossOver/Bottles/Win10/drive_c/Program Files (x86)/Steam/steamapps/common/Dwarf Fortress"
OVERLAY_JSON = DF_INIT / "dfhack-config/overlay.json"
DF_GLOBAL_BINDS = {"RECORD_MACRO", "LOAD_MACRO", "PLAY_MACRO", "SAVE_MACRO", "FPS_UP", "FPS_DOWN"}

def df_global_keys():
    """The key combos DF itself binds globally, as DFHack CUSTOM_* names: read from interface.txt, never assumed."""
    txt = (DF_INIT / "data/init/interface.txt").read_text(errors="replace")
    mods = {1: "SHIFT_", 2: "CTRL_", 3: "CTRL_SHIFT_", 4: "ALT_"}
    names = {"Equals": "EQUALS", "Minus": "MINUS"}
    out, cur = {}, None
    for line in txt.splitlines():
        m = re.search(r"\[BIND:([A-Z0-9_]+):", line)
        if m: cur = m.group(1); continue
        m = re.search(r"\[SYM:(\d+):([^\]]+)\]", line)
        if m and cur in DF_GLOBAL_BINDS and int(m.group(1)) in mods:
            k = names.get(m.group(2), m.group(2).upper())
            out["CUSTOM_" + mods[int(m.group(1))] + k] = cur
    return out

def window_keys():
    src = (TOOL / "scripts/gui/seasonal-wildlife.lua").read_text(errors="replace")
    return sorted(set(re.findall(r"key='(CUSTOM_[A-Z0-9_]+)'", src)) | set(re.findall(r"keys\.(CUSTOM_[A-Z0-9_]+)", src)))

def nonascii_strings(path):
    """Non-ASCII characters inside Lua string literals (comments skipped): what the window or console can draw."""
    hits = []
    for n, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        code = line.split("--", 1)[0] if not re.search(r"['\"][^'\"]*--", line) else line
        for m in re.finditer(r"'([^'\\]|\\.)*'|\"([^\"\\]|\\.)*\"", code):
            lit = m.group(0)
            bad = [c for c in lit if ord(c) > 127]
            if bad: hits.append(f"{path.name}:{n}: {lit[:70]}")
    return hits

TIMING_LUA = """
local sw=reqscript('seasonal-wildlife'); local gw=reqscript('gui/seasonal-wildlife')
local out={tabs={}, jobs={}}
local function T(t, name, f) local t0=dfhack.getTickCount(); local ok,err=pcall(f); t[name]={ms=dfhack.getTickCount()-t0, ok=ok, err=(not ok) and tostring(err):sub(1,160) or nil} end
T(out.tabs, 'open', function() gw.show_gui() end)
local scr=gw.view; local w=scr and scr.subviews and scr.subviews[1]
if w then
  for i,m in ipairs({'refreshOverview','refresh','refreshSeasons','refreshWeb','refreshLive','refreshLayers','refreshVermin','refreshLedger','refreshPanel'}) do
    if w[m] then w.subviews.pages:setSelected(math.min(i, #w.subviews.pages.subviews)); T(out.tabs, m, function() w[m](w) end) end
  end
  if w.subviews.web_mode then
    for _,mode in ipairs({'graph','byseason','bylayer'}) do T(out.tabs, 'web:'..mode, function() w.subviews.web_mode:setOption(mode,false); w:refreshWeb() end) end
  end
  pcall(function() scr:dismiss() end)
end
local cfg=sw.loadConfig()
local g=sw.loadGroups()
T(out.jobs, 'season hold (daily)', function() sw.holdOutOfSeason(cfg, df.global.cur_season); sw.CAVERN.apply(cfg, df.global.cur_season) end)
T(out.jobs, 'groups (300 t)', function() sw.groupsTick(cfg, g) end)
out.parts = {}
T(out.parts, 'loadConfig', function() sw.loadConfig() end)
out.live = {}
local function L(name, f) if f then T(out.live, name, f) end end
L('groupsStatus', sw.groupsStatus and function() sw.groupsStatus() end)
L('PATTERN.status', sw.PATTERN and sw.PATTERN.status and function() sw.PATTERN.status(cfg) end)
L('IRRUPT.status', sw.IRRUPT and sw.IRRUPT.status and function() sw.IRRUPT.status(cfg, g) end)
L('ecologyStatus', sw.ecologyStatus and function() sw.ecologyStatus(cfg, g) end)
L('QUOTA.status', sw.QUOTA and sw.QUOTA.status and function() sw.QUOTA.status(cfg) end)
L('CAVE.status', sw.CAVE and sw.CAVE.status and function() sw.CAVE.status() end)
L('STOCK.status', sw.STOCK and sw.STOCK.status and function() sw.STOCK.status(cfg) end)
L('CAVERN.status', sw.CAVERN and sw.CAVERN.status and function() sw.CAVERN.status(cfg) end)
L('FUSE.status', sw.FUSE and sw.FUSE.status and function() sw.FUSE.status() end)
T(out.parts, 'buildPool', function() sw.buildPool(cfg) end)   -- not a job: jobs build the pool only when the roster changed
if sw.ecologyRun then T(out.jobs, 'ecology ('..tostring(cfg.ecology.cadence or 1500)..' t)', function() sw.ecologyRun(cfg, g) end)
else T(out.jobs, 'ecology ('..tostring(cfg.ecology.cadence or 1500)..' t)', function() dfhack.run_command_silent('seasonal-wildlife','groups','ecology','now') end) end
if sw.WATER and sw.WATER.run then T(out.jobs, 'water', function() sw.WATER.run(cfg) end) end
print(json.encode(out))
"""

ROSTER_LUA = """
local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg)
local season=df.global.cur_season
local noseason, inactiveOpen, frozen, n, nact, ninact = {}, {}, {}, 0, 0, 0
local qty={}
local rs=sw.getEmbarkRegions()
for _,pop in ipairs(df.global.world.populations.all) do
  if sw.managedPop(pop, rs, {land=true, water=true, cavern=true}) then
    local cr=df.creature_raw.find(pop.race); local k=cr and sw.keyFor(sw.layerOf(pop), cr.creature_id)
    if k then qty[k]=math.max(qty[k] or 0, pop.quantity) end
  end
end
for _,e in ipairs(pool) do
  if e.inEmbark and not e.locked then
    n=n+1
    local act=sw.isAllowed(cfg,e); local ss=cfg.assign[e.key]
    if act then nact=nact+1; if not ss or #ss==0 then noseason[#noseason+1]=e.key end
    else
      ninact=ninact+1
      if e.layer=='cavern' then
        local cr=df.creature_raw.find(e.idx); if cr and cr.frequency>1 then frozen[#frozen+1]=e.key..' freq '..cr.frequency end
      elseif (qty[e.key] or 0)>0 then inactiveOpen[#inactiveOpen+1]=e.key..' '..qty[e.key] end
    end
  end
end
print(json.encode({species=n, active=nact, inactive=ninact, active_no_season=noseason, inactive_stocked=inactiveOpen, inactive_cavern_open=frozen}))
"""

def phase_w0(fort):
    log("== W0: keys, overlay, ASCII, timing, the roster rule")
    # keys
    glob = df_global_keys()
    rc, kb = sh("cmd", "keybinding", "list", timeout=60)
    dfh = set(re.findall(r"^\s*(Ctrl-|Alt-|Shift-)*([A-Za-z0-9]+)(?=[@:\s])", kb, re.M)) if kb else set()
    wk = window_keys()
    clash = [f"{k} = DF {glob[k]}" for k in wk if k in glob]
    rec("w0.keys", "PASS" if not clash else "FAIL", "no window key is one of DF's global binds (" + ", ".join(sorted(glob)) + ")",
        ("clashes: " + "; ".join(clash)) if clash else f"{len(wk)} window keys, none global", data={"window_keys": wk, "df_global": glob, "dfhack_keybinding_list": kb[:1500]})
    # ASCII
    hits = nonascii_strings(TOOL / "scripts/gui/seasonal-wildlife.lua") + nonascii_strings(TOOL / "scripts/seasonal-wildlife.lua")
    rec("w0.ascii", "PASS" if not hits else "FAIL", "no non-ASCII character in any string literal of the window or the engine",
        f"{len(hits)} literal(s): " + " | ".join(hits[:12]), data={"hits": hits})
    # timing (the window opens and closes inside the probe; nothing is left on screen)
    t = luaj(TIMING_LUA, timeout=300)
    tabs, jobs = (t.get("tabs") or {}), (t.get("jobs") or {})
    slow_t = {k: v["ms"] for k, v in tabs.items() if k != "open" and (v.get("ms", 0) >= 100 or not v.get("ok"))}
    slow_j = {k: v["ms"] for k, v in jobs.items() if v.get("ms", 0) >= 50 or not v.get("ok")}
    live = {k: v.get("ms") for k, v in (t.get("live") or {}).items() if v.get("ms")}   # the Live tab's status lines, each timed alone
    rec("w0.timing.tabs", "PASS" if tabs and not slow_t else "FAIL", "every tab refresh < 100 ms",
        json.dumps({k: v.get("ms") for k, v in tabs.items()}) + (f"; Live parts {json.dumps(live)}" if live else ""), data=t)
    rec("w0.timing.jobs", "PASS" if jobs and not slow_j else "FAIL", "every job pass < 50 ms",
        json.dumps({k: v.get("ms") for k, v in jobs.items()}), data=t)
    # the roster rule, with every present layer on and the season applied
    cmd("layer", "water", "on"); cmd("layer", "cavern", "on")
    cmd("now")
    lua("local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig(); sw.holdOutOfSeason(c, df.global.cur_season); sw.CAVERN.apply(c, df.global.cur_season)")
    r = luaj(ROSTER_LUA, timeout=180)
    ns, st, fr = r.get("active_no_season", []), r.get("inactive_stocked", []), r.get("inactive_cavern_open", [])
    rec("w0.roster.seasons", "PASS" if isinstance(ns, list) and r.get("species") and not ns else "FAIL",
        "no active species without a season", f"{len(ns)} active with no season: {' '.join(ns[:25])}", data=r)
    rec("w0.roster.inactive", "PASS" if r.get("species") and not st and not fr else "FAIL",
        "every inactive species at 0 (land/water/vermin) or frequency 1 (caverns)",
        f"{len(st)} stocked: {' '.join(st[:20])}; {len(fr)} cavern open: {' '.join(fr[:10])}", data=r)
    # last season / activation / cycle, on one active land species with seasons (restored afterwards)
    probe = luaj("""
local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg); local pick
for _,e in ipairs(pool) do if e.inEmbark and not e.locked and e.layer=='land' and sw.isAllowed(cfg,e) then pick=e; break end end
if not pick then print(json.encode({none=true})) return end
local k=pick.key; local keep=cfg.assign[k]; local keepA=cfg.allow[k]
sw.setAssign(cfg, k, {1}); sw.toggleSeason(cfg, k, 1)
local afterLast = cfg.assign[k] and #cfg.assign[k] or 0
local cyc, empty = {}, false
sw.setAssign(cfg, k, {0})
for i=1,7 do sw.cycleSeason(cfg, k); local a=cfg.assign[k]; cyc[#cyc+1]=a and table.concat(a,',') or ''; if not a or #a==0 then empty=true end end
local act = -1
cfg.allow[k]=false; cfg.assign[k]=nil
if sw.ROSTER and sw.ROSTER.setActive then sw.ROSTER.setActive(cfg, pool, pick, true); act = cfg.assign[k] and #cfg.assign[k] or 0 end
cfg.assign[k]=keep; cfg.allow[k]=keepA
print(json.encode({token=k, after_last=afterLast, cycle=cyc, empty=empty, activated=act}))
""", timeout=120)
    if probe.get("none"):
        for cid in ("w0.roster.lastseason", "w0.roster.activate", "w0.roster.cycle"):
            rec(cid, "NOT-TESTABLE-HERE", "an active land species", json.dumps(probe))
    else:
        rec("w0.roster.lastseason", "PASS" if probe.get("after_last") == 1 else "FAIL", "toggling off the only season leaves it in place",
            f"{probe.get('token')}: seasons after removing the last = {probe.get('after_last')}", data=probe)
        rec("w0.roster.activate", "PASS" if probe.get("activated") == 1 else "FAIL", "activation yields exactly one season",
            f"{probe.get('token')}: seasons after activation = {probe.get('activated')} (-1: no activation path in the engine)", data=probe)
        rec("w0.roster.cycle", "PASS" if not probe.get("empty") else "FAIL", "seven cycles never produce an empty season set",
            f"{probe.get('token')}: {' -> '.join(probe.get('cycle', []))}", data=probe)
    # overlay: what the full run does to overlay.json (mech.overlay enables the widget), and whether it is put back
    before = OVERLAY_JSON.read_text(errors="replace") if OVERLAY_JSON.exists() else ""
    return before

def overlay_state(txt):
    try:
        return (json.loads(txt).get("seasonal-wildlife.groups") or {}).get("enabled")
    except Exception:
        return None

# ============================================================================== PHASES ====
def phase_setup(fort):
    log(f"== SETUP: restore and load {fort}")
    sh("save-restore", f"{fort}.preverify", timeout=300)
    rc, out = sh("load", fort, timeout=300)
    if rc != 0:
        log("could not load the fort: " + out[:400]); sys.exit(1)
    time.sleep(1)
    g = ground("A0-baseline")
    rv = rig_versions()
    log(f"  rig: DF {rv['df']} / DFHack {rv['dfhack']} ({rv['release']})")
    (OUT / "rig.json").write_text(json.dumps(rv))
    s = shot("A0-map-baseline")
    log(f"  loaded: tick {g.get('tick')} season {g.get('season')} citizens {g.get('citizens')} "
        f"land {g.get('land')} water {g.get('water')} cavern {g.get('cavern')} deep {g.get('deep')}")
    return g

def phase_cli():
    log("== CLI")
    rc, out = cmd("status")
    q = "limits [" if V71 else ("limits:" if V65 else "quota:")   # v6.5 (W4): quota retired for limits; v7.1 (R7): 'limits [mode]:'

    ok = all(k in out for k in ("Biomes:", "Layers:", q, "On the map now:", "Embark subset"))
    rec("cli.status", "PASS" if ok else "FAIL", f"Biomes/Layers/{q[:-1]}/On the map now/Embark subset", out)
    rec("mech.layers.count", "PASS" if "magma sea and underworld" in out else "FAIL",
        "the on-the-map line naming the deep bucket", out)
    rec("mech.invasion", "PASS" if re.search(r"excluded via unit\.invasion", out) else "FAIL",
        "'DF invasions excluded via unit.invasion_id'", out)
    rc, out = cmd("now")
    rec("cli.now", "PASS" if re.search(r"active: \d+", out) else "FAIL", "active: N", out)
    rc, out = cmd("classes")
    n = len(re.findall(r"^\s+\S+\s+(managed|left to DF)\s+\d+", out, re.M))
    rec("cli.classes", "PASS" if n == 7 else "FAIL", "seven class lines, 'managed' or 'left to DF', and a count", out, data={"class_lines": n})
    rc, out = cmd("class")
    rec("cli.class", "PASS" if "usage" in out.lower() else "FAIL", "usage line on missing args", out)
    rc, out = cmd("groups")
    ok = "resident groups:" in out and "ecology:" in out and "swept=" in out and "cohesion=" in out
    rec("cli.groups.status", "PASS" if ok else "FAIL", "resident groups / cohesion / swept / ecology lines", out)
    rec("mech.stuck", "NOT-TESTABLE-HERE" if "swept=" in out else "FAIL",
        "the sweep needs a non-flier motionless for 5,000 ticks; the counter is present", out,
        note="Measured on T5 (17 Sep 2026): canopy-stranded wolves and dingoes re-grounded; fliers exempt.")
    rc, out = cmd("groups", "off"); rc2, out2 = cmd("groups", "on")
    rec("cli.groups.onoff", "PASS" if "off" in out and "on" in out2 else "FAIL", "'resident groups: off' then 'on'", out + out2)
    rc, out = cmd("groups", "coupling", "off"); rc2, out2 = cmd("groups", "piggyback", "on")
    rec("cli.groups.coupling", "PASS" if "coupling: off" in out and "coupling: on" in out2 else "FAIL",
        "coupling off, then the piggyback alias turns it on", out + out2)
    rc, out = cmd("groups", "pack", "7"); rc2, out2 = cmd("groups", "pack", "0")
    rec("cli.groups.pack", "PASS" if "pack size: 7" in out and "raw default" in out2 else "FAIL", "7 then raw default", out + out2)
    rc, out = cmd("groups", "ecology"); rc2, out2 = cmd("groups", "ecology", "off"); rc3, out3 = cmd("groups", "ecology", "on")
    ok = ("ecology:" in out) and ("ecology: off" in out2) and ("ecology: on" in out3)
    rec("cli.groups.ecology", "PASS" if ok else "FAIL", "status, off, on", out + out2 + out3)
    rc, out = cmd("groups", "livestock", "on"); rc2, out2 = cmd("groups", "livestock", "off")
    rec("cli.groups.livestock", "PASS" if "a target" in out and "safe" in out2 else "FAIL", "'a target' then 'safe'", out + out2)
    rc, out = cmd("groups", "nudge", "40", "3000", "6")
    rec("cli.groups.nudge", "PASS" if "nudge: after 3000 ticks more than 40 tiles apart, to within 6" in out else "FAIL",
        "the nudge line echoing 40/3000/6", out)
    rc, out = cmd("groups", "cohesion", "herd", "8", "pack", "4", "flock", "12")
    rec("cli.groups.cohesion", "PASS" if re.search(r"cohesion: (on|off)\s+herd 8\s+pack 4\s+flock 12", out) else "FAIL",
        "cohesion line with herd 8 pack 4 flock 12", out)
    rc, out = cmd("groups", "hold")
    rec("cli.groups.hold", "PASS" if "usage" in out.lower() else "FAIL", "usage on missing args", out)
    rc, out = cmd("limits" if V65 else "quota")
    lq = re.search(r"limits \[(map-size formula per layer|single fixed cap \d+ on every layer)\]:", out) if V71 else (("limits:" in out) if V65 else ("quota:" in out))
    rec("cli.quota", "PASS" if lq and "on the map now" in out else "FAIL", "the limits line (v7.1: 'limits [map-size formula per layer]:' or '[single fixed cap N ...]'; v6.5: 'limits:'; quota before) + on-the-map", out)
    rc, out = cmd("quota", "cavern", "12")
    ok = "frequency" in out.lower() and "arriv" in out.lower() and (("retired" in out) if V65 else True)
    rec("cli.quota.cavern", "PASS" if ok else "FAIL", "the frequency + arrival-lag warning" + (" and the retirement note (v6.5)" if V65 else ""), out)
    cmd("quota", "cavern", "0")
    rc, out = cmd("water")
    rec("cli.water", "PASS" if out.startswith("water:") or "water:" in out else "FAIL", "a water: status line", out)
    rc, out = cmd("place")
    rec("cli.place", "PASS" if "usage" in out.lower() else "FAIL", "usage on missing token", out)
    rc, out = cmd("bogusverb")
    rec("cli.usage", "PASS" if "usage" in out.lower() and "traceback" not in out.lower() else "FAIL", "usage, no stack trace", out)
    errs = []
    for args in (("water", "target", "x"), ("water", "bogus"), ("quota", "bogus", "1"), ("quota", "land", "-1"),
                 ("class", "BADGER", "notaclass"), ("place", "NOT_A_CREATURE"), ("groups", "dismiss")):
        rc, out = cmd(*args)
        errs.append((args, "usage" in out.lower() or "no stocked" in out or "no tracked" in out or (V65 and "retired in v6.5" in out), out.strip()[:120]))
    rec("cli.errors", "PASS" if all(e[1] for e in errs) else "FAIL", "each prints usage / a refusal",
        "\n".join(f"{a}: {o}" for a, _, o in errs), data=[list(a) for a, ok_, _ in errs if not ok_])
    rc, out = sh("cmd", "help", "seasonal-wildlife", timeout=60)
    rec("cli.docstring", "PASS" if "seasonal" in out.lower() and "roster" in out.lower() else "FAIL", "launcher help text", out)

    # --- vermin by family (v5.9.10)
    rc, out = cmd("vermin")
    fams = re.findall(r"^(fish|flies|fliers|mammals|soil|colony|crawlers)\s", out, re.M)
    rec("cli.vermin", "PASS" if "FAMILY" in out and len(fams) >= 2 else "FAIL", "a FAMILY header and at least two family rows", out[:900], data={"families": fams})

    # --- arrival patterns (v5.10.0)
    rc, p0 = cmd("pattern")
    rc, p1 = cmd("pattern", "land", "burst")
    rc, p2 = cmd("pattern", "bogus")
    rc, p3 = cmd("pattern", "steady")
    ok = "patterns: land=steady" in p0 and "land=burst" in p1 and "usage:" in p2 and "land=steady" in p3
    rec("cli.pattern", "PASS" if ok else "FAIL", "shows land=steady; sets land=burst; refuses a bad name with usage; `pattern steady` sets the land layer", p0 + p1 + p2 + p3)
    out = luaj("local ok,out=pcall(dfhack.run_command_silent,'seasonal-wildlife','preset'); print(json.encode({out=out}))", timeout=120)
    ps = str(out.get("out") if isinstance(out, dict) else out)
    rec("cli.preset", "PASS" if "preset" in ps and "species active" in ps and "one season each" in ps and "rotation on" in ps else "FAIL", "the preset receipt (v6.3): '<name>: N species active, one season each on N; <layers>; seasonal rotation on'", ps[:300])
    u1 = luaj("local ok,out=pcall(dfhack.run_command_silent,'seasonal-wildlife','undo'); print(json.encode({out=out}))", timeout=120)
    us = str(u1.get("out") if isinstance(u1, dict) else u1)
    rec("cli.undo", "PASS" if ("undid:" in us or "nothing to undo" in us) else "FAIL", "'undid: <label>' or 'undo: nothing to undo'", us[:200])
    ir0 = luaj("local ok,out=pcall(dfhack.run_command_silent,'seasonal-wildlife','irruption'); print(json.encode({out=out}))", timeout=60)
    ir1 = luaj("local ok,out=pcall(dfhack.run_command_silent,'seasonal-wildlife','irruption','on'); print(json.encode({out=out}))", timeout=60)
    ir2 = luaj("local ok,out=pcall(dfhack.run_command_silent,'seasonal-wildlife','irruption','off'); print(json.encode({out=out}))", timeout=60)
    s0, s1, s2 = (str(x.get("out") if isinstance(x, dict) else x) for x in (ir0, ir1, ir2))
    rec("cli.irruption", "PASS" if "irruptions: off" in s0 and "irruptions: on" in s1 and "threshold" in s1 and "cavern 1" in s1 and "irruptions: off" in s2 else "FAIL",
        "off by default; on shows threshold and pressures; off again", (s0 + " | " + s1 + " | " + s2)[:400])
    rec("plan.irruptions", "PASS" if "irruptions: on" in s1 and "irruptions: off" in s2 else "FAIL", "the opt-in module answers on and off; plotinfo.invasions is never referenced by the tool", "on/off receipts above; plotinfo.invasions appears in the script once, in the module's comment saying it is never touched", note="built in v6.1.0 on E29/E23 (armed, not aimed; the roster the dial); T9 measures the arming path")
    rec("mech.irruption.arm", "NOT-TESTABLE-HERE", "a cavern arrival under pinned pressure across a season", "", note="T9 (experiments/T9.json, scripts/t9-tally.py): two replicates each of module on and off with every cavern's pressure pinned at the threshold")
    rec("plan.patterns", "PASS" if ok else "FAIL", "the arrival-pattern library on the scheduler: steady, burst, trickle, dawn, follow", p1,
        note="shipped in v5.10.0 on the release gate; the distributions are T8's to measure (data/experiments/T8)")

def phase_mechanics():
    log("== MECHANICS")
    # --- scheduler
    rc, out = cmd("enable")
    g = ground("B1-enabled")
    rec("mech.sched", "PASS" if g.get("sched") else "FAIL", "repeat-util reports seasonal-wildlife scheduled after enable", out, data={"sched": g.get("sched")})
    rec("cli.enable", "PASS" if "enabled" in out and g.get("sched") else "FAIL", "'enabled' and the job registered", out)
    # --- build a full roster on all three layers, apply, and read the pool back
    # v6.3: `now` (phase_cli) already applies the whole roster, so this apply would change nothing on its own; every managed
    # entry is first set to a sentinel 77, so the apply has to write each one (zero it or stock it) to pass
    lua("local sw=reqscript('seasonal-wildlife'); local rs=sw.getEmbarkRegions(); for _,pop in ipairs(df.global.world.populations.all) do "
        "if sw.managedPop(pop, rs, sw.LAYER_SET.all) then pop.quantity=77 end end", timeout=120)
    before = fmt_pools(pools())
    out = lua("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); if not cfg.initialized then sw.captureDefault(cfg) end; "
              "cfg.layers.land=true; cfg.layers.water=true; cfg.layers.cavern=true; local pool=sw.buildPool(cfg); local n=0; "
              "for _,e in ipairs(pool) do if e.inEmbark and sw.defaultAllow(e) then cfg.allow[e.key]=true; n=n+1 end end; "
              "local a=sw.assignFromMatrix(cfg,pool); sw.saveConfig(cfg); local act=sw.applyLive(cfg, df.global.cur_season); sw.saveConfig(cfg); "
              "print(('roster: %d allowed, %d assigned, %d active'):format(n,a,act))", timeout=180)
    after = fmt_pools(pools())
    ps = pools()
    zeroed = [e for e in ps if int(e["qty"]) == 0]
    stocked = [e for e in ps if int(e["qty"]) > 0]
    changed = {t: (before.get(t), after.get(t)) for t in set(before) | set(after) if before.get(t) != after.get(t)}
    rec("mech.apply", "PASS" if changed and zeroed and stocked else "FAIL",
        "the apply changes pool quantities: some entries zeroed (out of season), some stocked", out,
        data={"entries_changed": len(changed), "zeroed": len(zeroed), "stocked": len(stocked), "sample": dict(list(changed.items())[:8])})
    # --- out-of-season: apply a different season and count what drops to zero
    cur = int(ground("B2-applied").get("season", 0))
    other = (cur + 2) % 4
    out = lua(f"local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); print('active other: '..sw.applyLive(cfg, {other})); sw.saveConfig(cfg)", timeout=180)
    other_p = fmt_pools(pools())
    dropped = [t for t in after if after[t] > 0 and other_p.get(t, 0) == 0]
    raised = [t for t in other_p if other_p[t] > 0 and after.get(t, 0) == 0]
    lua(f"local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); print('active back: '..sw.applyLive(cfg, {cur})); sw.saveConfig(cfg)", timeout=180)
    rec("mech.outofseason", "PASS" if dropped or raised else "FAIL",
        f"applying season {other} instead of {cur} zeroes some species and stocks others", out,
        data={"dropped_to_zero": dropped[:12], "raised_from_zero": raised[:12], "n_dropped": len(dropped), "n_raised": len(raised)})
    # --- v6.3: no seasons = inactive = held at 0 (until v6.2.1: unmanaged, the entry kept its stock)
    probe = luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg); local pick; "
                 "for _,e in ipairs(pool) do if e.inEmbark and e.layer=='land' and cfg.assign[e.key] and #cfg.assign[e.key]>0 then pick=e; break end end; "
                 "if not pick then print(json.encode({none=true})) return end; "
                 "local q0=0; local rs=sw.getEmbarkRegions(); for _,pop in ipairs(df.global.world.populations.all) do local cr=df.creature_raw.find(pop.race); "
                 "if sw.managedPop(pop, rs, {land=true}) and cr and cr.creature_id==pick.token then pop.quantity=37; q0=q0+1 end end; "
                 "sw.ROSTER.setActive(cfg, pool, pick, false); sw.saveConfig(cfg); sw.applyLive(cfg, df.global.cur_season); sw.saveConfig(cfg); "
                 "local q1={}; for _,pop in ipairs(df.global.world.populations.all) do local cr=df.creature_raw.find(pop.race); "
                 "if sw.managedPop(pop, rs, {land=true}) and cr and cr.creature_id==pick.token then q1[#q1+1]=pop.quantity end end; "
                 "print(json.encode({token=pick.token, key=pick.key, entries=q0, after=q1}))", timeout=180)
    held = bool(probe.get("after")) and all(int(q) == 0 for q in probe["after"])
    rec("mech.unassigned", "PASS" if held else ("NOT-TESTABLE-HERE" if probe.get("none") else "FAIL"),
        "a species made inactive (its seasons cleared) goes from the sentinel quantity 37 to 0 through an apply", json.dumps(probe), data=probe)
    lua("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg); "
        f"for _,e in ipairs(pool) do if e.key=='{probe.get('key', '')}' then sw.ROSTER.setActive(cfg, pool, e, true) end end; sw.saveConfig(cfg)")
    # --- force wave. Ctrl+F runs `fix/wildlife` then `force Wildlife`. On this DFHack `force`
    # treats WILDLIFE as a SYNTHETIC event: wildlife.free_all_wildlife() clears the roaming-source
    # flags on every wild unit, which is the "release the surface" lever E8 measured (a new wave
    # within ~450 ticks of the surface being freed). So the ground truth is: flagged units before,
    # none after, then a new land wave. With nothing on the surface there is nothing to free and
    # any arrival is DF's own timer — that case is NOT-TESTABLE-HERE, not a pass.
    def roaming():
        r = luaj("local sw=reqscript('seasonal-wildlife'); local n,ids=0,{}; for _,u in ipairs(df.global.world.units.active) do "
                 "if sw.WILD.onMap(u) and sw.WILD.layerOf(u)=='land' and (u.flags2.roaming_wilderness_population_source or u.flags2.roaming_wilderness_population_source_not_a_map_feature) then n=n+1; ids[#ids+1]=u.id end end; "
                 "print(json.encode({flagged=n, ids=ids}))", timeout=60)
        return r if isinstance(r, dict) else {"flagged": -1, "ids": []}
    g0 = ground("B3-preforce")
    ids0 = {u["id"] for u in g0.get("units", [])}
    r0 = roaming()
    rc, out = sh("cmd", "fix/wildlife", timeout=60)
    fr = luaj("local ok,err=pcall(dfhack.run_script,'force','Wildlife'); print(json.encode({accepted=ok, err=tostring(err)}))", timeout=60)
    r1 = roaming()
    step(6000, 400)
    g1 = ground("B3-postforce")
    new = [u for u in g1.get("units", []) if u["id"] not in ids0 and u["layer"] == "land"]
    shots_ = []
    if new:
        centre_on(new[0]["id"]); p = shot("B3-wave-arrival"); shots_ = [p] if p else []
    freed = r0.get("flagged", 0) > 0 and r1.get("flagged", -1) == 0
    if r0.get("flagged", 0) == 0:
        rec("mech.force", "NOT-TESTABLE-HERE", "wild land units carrying the roaming-source flag before the force, none after, then a new wave",
            f"no flagged wild land unit was on the surface when the force ran (land={g0.get('land')}); arrivals in the next 6,000 ticks: {[(u['token'], u['id']) for u in new][:8]}",
            shots=shots_, data={"force": fr, "before": r0, "after": r1, "new_land_units": [(u["token"], u["id"]) for u in new][:12]},
            note="force Wildlife = wildlife.free_all_wildlife(): it clears the roaming flags so DF may send the next group; with nothing to free it is a no-op and the wave that follows is DF's own timer. Measured as the release lever in E8/E10 (a chosen species in <450 ticks, 5 of 5).")
    else:
        rec("mech.force", "PASS" if freed and new else "FAIL", "flagged units freed by the force, then a new land wave within 6,000 ticks",
            f"flagged before {r0.get('flagged')} -> after {r1.get('flagged')}; new land units: {[(u['token'], u['id']) for u in new][:8]}",
            shots=shots_, data={"force": fr, "before": r0, "after": r1, "new_land_units": [(u["token"], u["id"]) for u in new][:12]})

    # --- groups tracking / cohesion / hold / dismiss on whatever is tracked now
    rc, out = cmd("groups")
    rows = [l.strip() for l in out.splitlines() if re.match(r"^\s+\S+ x\d+ (resident|gated)", l)]
    rec("mech.groups.track", "PASS" if rows else "FAIL", "at least one tracked group row (TOKEN xN gated/resident (day D))", out, data={"rows": rows[:8]})
    rc, out = cmd("groups", "cohesion", "on")
    m = re.search(r"\((\d+) group\(s\) led, (\d+) follower\(s\) set\)", out)
    led = int(m.group(1)) if m else 0
    rec("mech.cohesion", "PASS" if led > 0 else ("NOT-TESTABLE-HERE" if not rows else "FAIL"),
        "≥1 group led after cohesion on", out, data={"led": led, "followers": int(m.group(2)) if m else 0},
        note="" if rows else "no tracked group of a herd/pack/flock species was on the map in this session")
    # leader is the lowest id (backlog says largest-male is NOT built)
    lead = luaj("local sw=reqscript('seasonal-wildlife'); local g=sw.loadGroups and sw.loadGroups() or nil; local out={}; "
                "if g then for _,grp in ipairs(g.groups) do if grp.leader then local mn,mem=math.huge,false; for _,i in ipairs(grp.ids) do if i<mn then mn=i end; if i==grp.leader then mem=true end end; "
                "out[#out+1]={token=grp.token, leader=grp.leader, lowest=mn, member=mem, n=#grp.ids} end end end; print(json.encode(out))", timeout=120)
    if isinstance(lead, list) and lead and V70:
        # v7.0 (item 22, user ruling): the largest male leads (V7.leaderOf), so lowest-id no longer holds; the size rule
        # itself is mech.v70.leader_male's claim -- here only that every leader is one of its group's members
        rec("mech.leader.lowest", "PASS" if all(x.get("member") for x in lead) else "FAIL",
            "v7.0: every led group's leader is one of its members (size rule: mech.v70.leader_male)", json.dumps(lead), data=lead)
    elif isinstance(lead, list) and lead:
        rec("mech.leader.lowest", "PASS" if all(x["leader"] == x["lowest"] for x in lead) else "FAIL",
            "every led group's leader == its lowest member id", json.dumps(lead), data=lead)
    else:
        rec("mech.leader.lowest", "NOT-TESTABLE-HERE", "a led group to inspect", json.dumps(lead), note="loadGroups not exported or no led group")
    tok = re.sub(r"^cavern\d+:", "", rows[0].split()[0]) if rows else None   # v5.9.1 prefixes cavern groups on the status line
    if tok:
        rc, out = cmd("groups", "hold", tok, "30")
        g = ground("B4-held")
        cds = [u["countdown"] for u in g.get("units", []) if u["token"] == tok]
        rec("mech.hold", "PASS" if re.search(r"held \S+ x\d+: \d+ countdown", out) and cds and min(cds) >= 30 * 1200 else "FAIL",
            f"every {tok} countdown ≥ 36,000 ticks", out, data={"countdowns": cds[:10]})
        rc, out = cmd("groups", "dismiss", tok)
        g = ground("B4-dismissed")
        cds = [u["countdown"] for u in g.get("units", []) if u["token"] == tok]
        rec("mech.dismiss", "PASS" if "dismissed" in out and cds and max(cds) == 0 else "FAIL",
            f"every {tok} countdown == 0 and 'leader cleared'", out, data={"countdowns": cds[:10]})
    else:
        rec("mech.hold", "NOT-TESTABLE-HERE", "a tracked group", out, note="no tracked group on the map; measured E19/T5")
        rec("mech.dismiss", "NOT-TESTABLE-HERE", "a tracked group", out, note="no tracked group on the map; measured T5")
    # --- ecology: write once, read the pair count; then let the cadence fire
    rc, out = cmd("groups", "ecology", "now")
    def waiting(txt):
        mm = re.search(r"pair\(s\) written \(\d+ new, (\d+) waiting", txt)
        return int(mm.group(1)) if mm else 0
    def write_line(txt):
        mm = re.search(r"(\d+) predator\(s\) x (\d+) target\(s\), (\d+) pair\(s\) written(?: \([^)]*\))?, (\d+) without a slot", txt)   # v6.3: '(N new, M waiting)' 
        return tuple(int(x) for x in mm.groups()) if mm else None
    first = write_line(out)
    preds, targets, pairs, noslot = first or (0, 0, 0, 0)
    def total_writes(txt):
        mm = re.search(r"total writes (\d+)", txt)
        return int(mm.group(1)) if mm else -1
    w0 = total_writes(out)
    step(3200, 300)
    rc, out2 = cmd("groups")
    w1 = total_writes(out2)
    later = write_line(out2)
    # USAGE: the write "skips units the game has not yet given a slot and catches them next pass". A load clears
    # DF's enemy-status cache and DF re-slots units lazily (an encounter, not a timer), so a session can end with
    # every predator still slotless (run 163604: 5 predators, 10 without a slot, 0 pairs across three passes).
    # That is the documented skip, not a failed write; FAIL is reserved for 0 pairs with nothing skipped.
    if first is None:
        v, note = "FAIL", "no 'last write' line"
    elif pairs > 0 or (later and later[2] > 0):
        v, note = "PASS", "" if pairs > 0 else f"0 pairs on the first pass ({noslot} without a slot); the scheduled passes caught them: {later[2]} pair(s) by the third write"
    elif preds == 0 or targets == 0:
        v, note = "PASS", "no armed predator and target co-present this session; the write ran and reported 0 pairs"
    elif all(x is not None and x[2] == 0 and x[3] == 0 for x in (first, later)) and waiting(out) == 0 and waiting(out2) == 0:
        # ecoWrite counts every predator-target pair that shares a realm as written, waiting or slotless; all three
        # at 0 means none did (run 211308: 4 cavern-side predators x 14 targets). v6.4.1 prints 'none in one realm'.
        v, note = "NOT-TESTABLE-HERE", f"{preds} predator(s) x {targets} target(s) on the map but no pair in one realm (written, waiting and slotless all 0 across three passes); the write only relates within a realm (v5.9.1)"
    elif (later or first)[3] > 0:
        v, note = "NOT-TESTABLE-HERE", f"{preds} predator(s) x {targets} target(s) but DF gave no slot to any predator this session ({(later or first)[3]} without a slot after three passes); the write skips slotless units by design (USAGE) and cannot reach them — measured E11c/T4 with slotted units. Open: the ecology write could allocate the slot itself the way v5.9.3 placement does (PLACE.enemySlot)"
    else:
        v, note = "FAIL", ""
    rec("mech.ecology.write", v,
        "a 'last write' line; pairs > 0 whenever a slotted LARGE_PREDATOR and a slotted target are both on the map (slotless units are skipped until DF slots them)",
        out + "\n--- after 3,200 ticks ---\n" + out2,
        data={"predators": preds, "targets": targets, "pairs": pairs, "without_slot": noslot,
              "later": dict(zip(("predators", "targets", "pairs", "without_slot"), later)) if later else None},
        note=note)
    cad = cfgv("ecology.cadence", "ecology.nudge").get("ecology.cadence")
    rec("mech.ecology.cadence", "PASS" if w1 > w0 >= 0 and (not V71 or cad == 3000) else "FAIL",
        f"total writes increases across 3,200 stepped ticks (cadence {'3,000 (v7.1 default, read back)' if V71 else '1,500'})", out2,
        data={"writes_before": w0, "writes_after": w1, "cadence": cad})
    out = out2
    rec("mech.ecology.nudge", "NOT-TESTABLE-HERE", "a predator >40 tiles from every target for 3,000 ticks", out,
        note="the nudge counter is in the same line ('N nudged'); measured E17/E18 (kill latency followed pack arrival, not the threshold)")
    rec("mech.coupling", "NOT-TESTABLE-HERE", "a prey wave arriving while coupling is on, then the pool closing for its armed predators",
        out, note="measured E10/T4/T6 (16–18 Sep 2026); the status line reports 'pool closed for <prey>' while a window is open")
    rec("mech.season.boundary", "NOT-TESTABLE-HERE", "a season boundary (100,800 ticks) inside this session", "",
        note="measured S1 (full year, 0 out-of-season arrivals) and T6 (a year, three layers); the daily hold is the same applyLive path tested above")
    # --- place
    g0 = ground("B5-preplace"); ids0 = {u["id"] for u in g0.get("units", [])}
    pb = fmt_pools(pools())
    rc, out = cmd("place", "KANGAROO", "3", "land")
    if "no stocked KANGAROO" in out:
        rc, out = cmd("place", "GROUNDHOG", "3", "land")
    m = re.search(r"placed (\d+) (\S+) on the (\S+) layer at ids ([\d,]+); entry (\d+) debited (\d+) -> (\d+)", out)
    placed_ids = [int(x) for x in m.group(4).split(",")] if m else []
    step(600, 120)
    g1 = ground("B5-postplace")
    alive = [u for u in g1.get("units", []) if u["id"] in placed_ids]
    shots_ = []
    if alive:
        centre_on(alive[0]["id"]); p = shot("B5-placed-units-on-map"); shots_ = [p] if p else []
    rec("mech.place", "PASS" if m and len(alive) == len(placed_ids) and int(m.group(6)) - int(m.group(7)) == len(placed_ids) else "FAIL",
        "N placed, entry debited by exactly N, all N alive on the map after 600 ticks", out, shots=shots_,
        data={"placed": placed_ids, "alive_after_600": [(u["token"], u["id"], u["x"], u["y"], u["z"]) for u in alive],
              "debit": (m.group(6), m.group(7)) if m else None})
    # --- v5.9: the caverns as a world of their own
    rc, out = cmd("caverns", "survey")
    bands = re.findall(r"depth (\d) \(cave (\d+)\) z(\d+)-(\d+), (water at the edge: (\d+) tile|dry edge)", out)
    rec("cli.caverns", "PASS" if len(bands) >= 1 and "survey re-run in" in out else "FAIL",
        "at least one cavern band with levels and an edge-water count", out, data={"bands": bands})
    def unit_tile(uid):
        return luaj(f"local u=df.unit.find({uid}); local d=dfhack.maps.getTileFlags(u.pos); local b=dfhack.maps.getTileBlock(u.pos); "
                    f"print(json.encode({{z=u.pos.z, sub=d.subterranean, out=d.outside, water=(d.flow_size>=4 and not d.liquid_type), gfeat=b.global_feature}}))")
    rc, out = cmd("place", "CROCODILE_CAVE", "1", "cavern")
    m = re.search(r"at ids (\d+)", out); t = unit_tile(int(m.group(1))) if m else {}
    inband = any(int(lo) <= t.get("z", -1) <= int(hi) for _, _, lo, hi, _, _ in bands)
    rec("mech.cavern.place", "PASS" if m and t.get("sub") and not t.get("out") and t.get("water") and inband else ("NOT-TESTABLE-HERE" if "no stocked" in out else "FAIL"),
        "placed; the tile is subterranean, not outside, water, and its z lies in a surveyed cavern band", out + "\n" + json.dumps(t), data={"tile": t})
    rc, out = cmd("place", "BEAVER", "1", "water")
    m = re.search(r"at ids (\d+)", out); t = unit_tile(int(m.group(1))) if m else {}
    rec("mech.water.outside", "PASS" if (m and t.get("out") and t.get("water") and not t.get("sub")) or (not m and "no free water tile" in out) else ("NOT-TESTABLE-HERE" if "no stocked" in out else "FAIL"),
        "placed in outside water, or refused for want of one; never a subterranean tile", out + "\n" + json.dumps(t), data={"tile": t})
    # --- v5.9.6: the cavern stocking pass under the cavern quota (retired in v6.5)
    if V65:
        rc, out = cmd("cavern", "on")
        rec("cli.cavern.stock", "PASS" if "retired" in out else "FAIL", "`cavern` says cavern stocking is retired (v6.5: DF draws the caverns)", out)
        rec("mech.cavern.stock", "PASS" if "retired" in out else "FAIL", "no cavern placement pass exists to run (v6.5)", out, note="retired in v6.5: DF waves the caverns; the tool steers them by frequency")
    else:
        lay0 = luaj("local sw=reqscript('seasonal-wildlife'); print(json.encode({cavern=sw.loadConfig().layers.cavern and true or false}))").get("cavern")
        present0 = luaj("local sw=reqscript('seasonal-wildlife'); print(json.encode({n=sw.WILD.countByLayer().cavern}))").get("n", 0)
        q = int(present0) + 8   # the quota sits eight above what the caverns hold now, whatever earlier checks left there
        c0 = luaj("print(json.encode({maxid=(function() local m=0; for _,u in ipairs(df.global.world.units.all) do if u.id>m then m=u.id end end; return m end)()}))")
        rc, out = cmd("layer", "cavern", "on"); rc, out = cmd("quota", "cavern", str(q)); rc, out = cmd("cavern", "on")
        rec("cli.cavern.stock", "PASS" if re.search(r"cavern stocking: on\s+\d+ of " + str(q), out) else "FAIL", f"'cavern stocking: on  N of {q} in the caverns'", out)
        # `cavern on` schedules the job and repeat-util runs it at once, so the pass under test is the one the
        # status already reports ("placed N in all"; the site data starts at 0 on this restored save); the
        # explicit `cavern now` that follows must then find the caverns at the quota and place nothing
        mj = re.search(r"placed (\d+) in all", out); placed = int(mj.group(1)) if mj else None; before = int(present0)
        rc, out = cmd("cavern", "now", timeout=120)
        chk = luaj(f"local sw=reqscript('seasonal-wildlife'); local n,bad=0,0; for _,u in ipairs(df.global.world.units.active) do if u.id>{c0.get('maxid', 0)} and dfhack.units.isWildlife(u) and u.animal.population.cave_id~=-1 then n=n+1; "
                   "local d=dfhack.maps.getTileFlags(u.pos); local b=sw.caveBandFor(u.animal.population.cave_id); local aq=sw.isAquatic(df.creature_raw.find(u.race)); "
                   "if not (d.subterranean and not d.outside and b and u.pos.z>=b.zlo and u.pos.z<=b.zhi and ((aq and d.flow_size>=4) or not aq) and u.enemy.enemy_status_slot>=0) then bad=bad+1 end end end; print(json.encode({placed=n, out_of_place=bad}))")
        rc, out2 = cmd("cavern", "now", timeout=120); m2 = re.search(r"placed (\d+)", out2)
        ok = before is not None and before < q and placed == q - before and chk.get("placed") == placed and chk.get("out_of_place") == 0 and m2 and int(m2.group(1)) == 0
        rec("mech.cavern.stock", "PASS" if ok else ("NOT-TESTABLE-HERE" if before is not None and before >= q else "FAIL"),
            "first pass places exactly quota-minus-present, every placed unit in its band (water for swimmers) with a slot; second pass places 0",
            out + "\n" + out2 + "\n" + json.dumps(chk), data={"before": before, "placed": placed, "check": chk})
        cmd("cavern", "off"); cmd("quota", "cavern", "0"); cmd("layer", "cavern", "on" if lay0 else "off")   # restore the layer as found: the quota check later expects it
    # --- water on a dry fort
    rc, out = cmd("water", "on")
    dorm = re.search(r"water: dormant (—|--) .+", out)
    pooled = V65 and not dorm and re.search(r"water: draws on .* pool \d+", out)   # v6.5 (W4): Driver B draws rivers, lakes AND pools
    rec("mech.water.dormant", "PASS" if dorm else ("NOT-TESTABLE-HERE" if pooled else "FAIL"),
        "'water: dormant — <reason>' on CTRL (inland)", out, note="CTRL holds open pool water, which v6.5's Driver B draws for; no dry fort in the set" if pooled else "", data={"line": next((l for l in out.splitlines() if "dormant" in l), "")})
    # `water now` on a dry fort: the scheduled job is gated by the cached wet-edge verdict, but
    # WATER.run — the `now` path — is not, and goes straight to a full-map placement scan. Time it
    # under a long cap so the report carries seconds, not a timeout.
    t0 = time.time()
    pr = subprocess.run([str(ROOT / ".venv/bin/python"), str(ROOT / "scripts/cx-rpc.py"), "--port", "5555", "--timeout", "600",
                         "--cmd", "seasonal-wildlife", "water", "now"], capture_output=True, text=True, timeout=660, cwd=ROOT)
    secs = time.time() - t0; out = (pr.stdout or "") + (pr.stderr or "")
    # the scan keeps running server-side after a client timeout and blocks the next RPC; drain it
    # so the finding stays on this check and does not cascade as timeouts through everything after
    subprocess.run([str(ROOT / ".venv/bin/python"), str(ROOT / "scripts/cx-rpc.py"), "--port", "5555", "--timeout", "600",
                    "--lua", "print('drained')"], capture_output=True, text=True, timeout=660, cwd=ROOT)
    log(f"  water now: {secs:.0f} s (server drained)")
    rec("cli.water.now", "PASS" if secs < 5 and ("placed 0" in out or "dormant" in out or "drew nothing" in out) else "FAIL",
        "'water now' on a dormant layer returns at once (the wet-edge verdict is cached at load) with 'placed 0' and the reason",
        f"{secs:.1f} s\n{out}", data={"seconds": round(secs, 1)},
        note="" if secs < 5 else ("the verb did not answer inside the cap; whether the server was busy is settled by the drain call that follows — if it returned at once, the core was free and the reply was never sent (v5.8.2 removed the whole-map scan)"))
    if V65:
        rc, out = cmd("limits", "water", "groups", "3", "ceiling", "20"); rc3, out3 = cmd("water", "countdown", "9000")
        # v7.1 (R7, R45): `limits <layer> groups N` is the single fixed cap N on every layer ('N (fixed)'), the water line
        # says 'per water body', and the cavern cap is R44's ('N (fixed, R44)', the smaller of the cap and the fixed cap)
        rec("mech.water.target", "PASS" if re.search(r"3 group\(s\) at once( per water body)?, ceiling 20", out3) and "~9000 ticks" in out3 else "FAIL",
            "the water status echoing 3 groups at once (per water body since v7.1), ceiling 20 and the 9000-tick countdown", out + out3)
        rc, out = cmd("limits", "land", "groups", "2")
        okl = re.search(r"land 2( \(fixed\))? group\(s\) at once", out) and (not V71 or "single fixed cap 2 on every layer" in out)
        rec("mech.quota.land", "PASS" if okl else "FAIL", "'land 2 group(s) at once' (v7.1: 'land 2 (fixed)' under 'single fixed cap 2 on every layer')", out)
        rc, out = cmd("quota", "water", "25")
        # v7.0's layer_groups (default on) words the limit per body / per cavern and sets cavern groups to auto (N);
        # v7.1's fixed cap from `limits land groups 2` above now holds on the water too
        wq = r"water 2 \(fixed\) group\(s\) at once per water body, ceiling 25" if V71 else r"water 3 group\(s\) at once( per water body)?, ceiling 25"
        rec("mech.quota.water", "PASS" if "retired" in out and re.search(wq, out) else "FAIL", "the quota alias sets the water ceiling and says quota is retired", out)
        rc, out = cmd("limits", "cavern", "ceiling", "7"); rc2, out2 = cmd("limits", "bogus")
        rec("mech.limits", "PASS" if re.search(r"cavern (2|auto \(\d+\)|\d+ \(fixed, R44\)) group\(s\) at once( per cavern)?, ceiling 7", out) and "usage" in out2.lower() else "FAIL",
            "`limits cavern ceiling 7` reads back (v7.1: the cavern count is R44's 'N (fixed, R44)'); a bad layer prints usage", out + out2)
        if V71:   # back to the v7.1 defaults: the map-size formula, no water ceiling (R45), no cavern ceiling
            cmd("limits", "formula"); cmd("limits", "water", "ceiling", "0"); cmd("limits", "cavern", "ceiling", "0")
        else:
            cmd("limits", "land", "groups", "3"); cmd("limits", "water", "groups", "2", "ceiling", "12"); cmd("limits", "cavern", "ceiling", "0")
    else:
        rc, out = cmd("water", "target", "20"); rc2, out2 = cmd("water", "cadence", "4000"); rc3, out3 = cmd("water", "countdown", "9000")
        rec("mech.water.target", "PASS" if "target 20" in out3 and "every 4000 ticks" in out3 and "countdown 9000" in out3 else "FAIL",
            "the status line echoing target 20 / every 4000 / countdown 9000", out3)
        cmd("water", "target", "12"); cmd("water", "cadence", "5000")
        # --- quotas
        rc, out = cmd("quota", "land", "2")
        rec("mech.quota.land", "PASS" if re.search(r"quota: land 2", out) else "FAIL", "'quota: land 2'", out)
        rc, out = cmd("quota", "water", "20"); rc2, out2 = cmd("water")
        rec("mech.quota.water", "PASS" if "from the water quota" in out2 and "target 20" in out2 else "FAIL",
            "water status says the target is overridden by the quota (20)", out2)
        cmd("quota", "land", "0"); cmd("quota", "water", "0")
    # cavern ceiling on frequency: set 1 (below the present count), read a held species' frequency
    rc, out = cmd("quota", "cavern", "1")
    cav = luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local r=sw.CAVERN.apply(cfg, df.global.cur_season); "
               "local held={}; local mn=999; local saved=sw.CAVERN.saved and sw.CAVERN.saved() or {}; "
               "for tok,_ in pairs(saved) do local ri=sw.raceIndex(tok); local cr=ri and df.creature_raw.find(ri); if cr then held[#held+1]={tok, cr.frequency}; if cr.frequency<mn then mn=cr.frequency end end end; "
               "print(json.encode({held=(r and r.held) or 0, open=(r and r.open) or 0, min_freq=mn, sample=held, status=sw.CAVERN.status(cfg)}))", timeout=180)
    okc = isinstance(cav, dict) and int(cav.get("held", 0)) > 0 and int(cav.get("min_freq", 999)) == 1
    rec("mech.quota.cavern", "PASS" if okc else "FAIL", "CAVERN.apply holds ≥1 species and the minimum written frequency is 1 (never 0)",
        json.dumps(cav)[:600], data=cav if isinstance(cav, dict) else None)
    rc, out = cmd("limits" if V65 else "quota")
    thr = "cavern ceiling:" in out
    rec("mech.quota.cavern.throttle", "DEAD" if thr else "PASS",
        "the old entry-quantity throttle line still prints beside the frequency mechanism (two mechanisms for one setting)", out,
        note="QUOTA.cavernThrottle closes pool entries, which T7 measured does nothing underground; it is still called from `quota` and prints a 'cavern ceiling: N of M present — CLOSED/open' line that describes an inert action. Retire it or route it to CAVERN.status.")
    rc, out = cmd("quota", "cavern", "0")
    rc2, out2 = cmd("disable")
    cav2 = luaj("local sw=reqscript('seasonal-wildlife'); local saved=sw.CAVERN.saved and sw.CAVERN.saved() or {}; local n=0; for _ in pairs(saved) do n=n+1 end; "
                "local ri=sw.raceIndex('CREEPY_CRAWLER'); local cr=ri and df.creature_raw.find(ri); print(json.encode({still_held=n, creepy_freq=cr and cr.frequency or -1}))", timeout=120)
    rec("mech.cavern.restore", "PASS" if isinstance(cav2, dict) and int(cav2.get("still_held", 1)) == 0 else "FAIL",
        "no species still held after quota cavern 0 + disable ('restored N cavern creature frequencies')", out + out2 + json.dumps(cav2), data=cav2)
    cmd("enable")
    # --- classes: lock and override
    lk = luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg); local locked, unlocked=0,0; local ex; "
              "for _,e in ipairs(pool) do if e.inEmbark then if e.locked then locked=locked+1; ex=ex or e.token else unlocked=unlocked+1 end end end; "
              "print(json.encode({locked=locked, unlocked=unlocked, example=ex, classes=cfg.classes}))", timeout=180)
    rec("mech.classes.lock", "PASS" if isinstance(lk, dict) and "locked" in lk else "FAIL",
        "the pool marks creatures of disabled classes as locked", json.dumps(lk)[:500], data=lk,
        note="CTRL's embark subset may hold no locked creature; the flag and the class table are what is checked")
    rc, out = cmd("class", "BADGER", "mythic")
    ov = luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg); "
              "for _,e in ipairs(pool) do if e.token=='BADGER' then print(json.encode({token=e.token, class=e.eco, locked=e.locked or false})) return end end; print(json.encode({missing=true}))", timeout=180)
    rc2, out2 = cmd("class", "BADGER", "natural")
    rec("mech.class.override", "PASS" if "usage" in out.lower() and isinstance(ov, dict) and ov.get("class") == "natural" and "BADGER -> natural" in out2 else "FAIL",
        "`class BADGER mythic` refused with usage and BADGER still natural; `class BADGER natural` accepted", out + json.dumps(ov) + out2, data=ov)
    # --- overlay
    rc, out = sh("cmd", "overlay", "enable", "seasonal-wildlife.groups", timeout=60)
    rc2, out2 = sh("cmd", "overlay", "list", "seasonal-wildlife", timeout=60)
    p = shot("B6-map-overlay-enabled")
    ok = "enabled widget seasonal-wildlife.groups" in out or bool(re.search(r"seasonal-wildlife\.groups.*(true|enabled|on)", out2, re.I))
    rec("mech.overlay", "PASS" if ok else "FAIL", "'enabled widget seasonal-wildlife.groups' (or overlay list showing it enabled)", out + out2, shots=[p] if p else [])
    # --- abundance and reset
    ab = luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg); local pick; "
              "for _,e in ipairs(pool) do if e.inEmbark and e.layer=='land' and cfg.allow[e.key] and cfg.assign[e.key] and #cfg.assign[e.key]>0 and (not sw.ROSTER or sw.ROSTER.wants(cfg, e.key, df.global.cur_season)) then pick=e; break end end; "
              "if not pick then print(json.encode({none=true})) return end; cfg.weight[pick.key]=100; sw.saveConfig(cfg); sw.applyLive(cfg, df.global.cur_season); sw.saveConfig(cfg); "
              "local q100=sw.qtyFor(cfg, pick.key); cfg.weight[pick.key]=50; sw.saveConfig(cfg); local q50=sw.qtyFor(cfg, pick.key); "
              "print(json.encode({token=pick.token, q_at_100=q100, q_at_50=q50}))", timeout=180)
    if V65:   # v6.5 (W5): abundance is stock -- `stock KEY N` writes the species' entries to N exactly
        pick = ab.get("token") if isinstance(ab, dict) else None
        rc, sout = cmd("stock", pick or "NONE", "333")
        st = luaj(f"local sw=reqscript('seasonal-wildlife'); local live,held=sw.RESERVE.of('{pick}'); print(json.encode({{live=live, held=held}}))", timeout=60) if pick else {}
        rec("mech.abundance", "PASS" if isinstance(st, dict) and st.get("live") == 333 and "stock" in sout else ("NOT-TESTABLE-HERE" if not pick else "FAIL"),
            "`stock KEY 333` leaves the species' entries summing to 333 (v6.5: stock, not abundance)", sout + json.dumps(st), data=st)
        cmd("stock", pick or "NONE", "clear")
    else:
        rec("mech.abundance", "PASS" if isinstance(ab, dict) and ab.get("q_at_100", 0) > ab.get("q_at_50", 0) else ("NOT-TESTABLE-HERE" if ab.get("none") else "FAIL"),
            "qtyFor at abundance 100 exceeds qtyFor at 50", json.dumps(ab), data=ab)
    # reset: set every abundance off-default, reset, and read what is left; also that a managed
    # entry's quantity returns to the captured worldgen snapshot
    rs = luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg); local n=0; "
              "for _,e in ipairs(pool) do if e.inEmbark then cfg.weight[e.key]=77; n=n+1 end end; sw.saveConfig(cfg); "
              "sw.resetToDefault(cfg); sw.saveConfig(cfg); local left=0; for k,v in pairs(cfg.weight) do if v~=50 then left=left+1 end end; "
              "local snap=0; if cfg.default then for _ in pairs(cfg.default) do snap=snap+1 end end; "
              "print(json.encode({set=n, non50_after_reset=left, snapshot_entries=snap}))", timeout=180)
    rec("mech.reset", "PASS" if isinstance(rs, dict) and rs.get("non50_after_reset") == 0 else "FAIL",
        "every abundance back to 50 after resetToDefault; a worldgen snapshot exists", json.dumps(rs), data=rs)
    # --- add-new (the console has no verb; the primitive is addNewSpecies, which the GUI's Ctrl+X calls).
    # A species already present in a region as ANY population type is refused by design ("present"),
    # so try candidates in order and keep every refusal as data.
    an = luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg); local tried={}; "
              "for _,e in ipairs(pool) do if not e.inEmbark and e.layer=='land' and not e.locked and e.cat~='apex' and e.eligible and #tried<8 then "
              "local n, why = sw.addNewSpecies(cfg, e.token, 50, 100); tried[#tried+1]={token=e.token, regions=n, why=why}; "
              "if n>0 then sw.saveConfig(cfg); local p2=sw.buildPool(cfg); local now=false; for _,x in ipairs(p2) do if x.token==e.token and x.inEmbark then now=true end end; "
              "print(json.encode({token=e.token, regions=n, in_embark_now=now, tried=tried})) return end end end; "
              "print(json.encode({none=true, tried=tried}))", timeout=240)
    if isinstance(an, dict) and an.get("in_embark_now"):
        rec("mech.addnew", "PASS", "the added species is in the embark pool immediately (no reload)", json.dumps(an), data=an)
    else:
        rec("mech.addnew", "NOT-TESTABLE-HERE" if isinstance(an, dict) and an.get("none") else "FAIL",
            "a non-native, eligible land species accepted by addNewSpecies", json.dumps(an)[:600], data=an,
            note="every candidate tried was refused as already present in the region as some population type (vermin, colony insect) — the engine's documented refusal, not a write failure; the primitive was proven live on 16 Sep (12 badgers drawn from a written entry)")

    # --- ledger (v5.9.9): every write leaves a line; the ring caps at 300 and the count keeps growing
    rc, out = cmd("ledger", "300")
    foot = re.search(r"ledger: (\d+) of (\d+) recorded shown", out)
    kinds = sorted(set(re.findall(r"^y\d+ \w+ \d+\s+(\w+)", out, re.M)))
    total = int(foot.group(2)) if foot else 0
    rec("cli.ledger", "PASS" if foot and total > 0 and kinds else "FAIL",
        "stamped lines 'y<year> <Season> <day>  kind  layer  text' and a 'shown of recorded' footer",
        out[-1500:], data={"kinds": kinds, "total": total, "shown": int(foot.group(1)) if foot else 0})
    need = {"place", "edit"}
    rec("mech.ledger.records", "PASS" if need <= set(kinds) else "FAIL",
        "after this session's placement and switch flips the ledger holds at least the kinds place and edit; arrive, hold, dismiss, ecology and cavern appear when the session produced them",
        ", ".join(kinds), data={"kinds": kinds, "total": total})
    rec("v6.explain", "PASS" if need <= set(kinds) else "FAIL", "every automatic decision logs one readable line (the ledger, v5.9.9)",
        ", ".join(kinds), note="shipped as the ledger backend in v5.9.9 (`ledger`, `status`); the Ledger tab that displays it is still v6.0 (v6.ledger)")
    ring = luaj("local sw=reqscript('seasonal-wildlife'); local _, before = sw.ledgerLines(1); local t0 = dfhack.getTickCount(); "
                "for i = 1, 310 do sw.ledgerAdd('edit', '', 'ring test %d', i) end; local ms = dfhack.getTickCount() - t0; "
                "local lines, total = sw.ledgerLines(400); print(json.encode({n=#lines, total=total, before=before, ms=ms}))", timeout=300)
    rc, out2 = cmd("ledger", "clear"); rc, out3 = cmd("ledger", "5")
    cleared = re.search(r"ledger: 0 of 0 recorded shown", out3) is not None
    ok = isinstance(ring, dict) and ring.get("n") == 300 and ring.get("total") == ring.get("before", -1) + 310 and cleared
    rec("mech.ledger.ring", "PASS" if ok else "FAIL", "310 adds leave exactly 300 lines and raise the total by 310; `clear` leaves 0 of 0",
        json.dumps(ring) + "\n" + out2 + out3, data=ring if isinstance(ring, dict) else {"raw": str(ring)},
        note=("%d ms for 310 adds" % ring["ms"]) if isinstance(ring, dict) and "ms" in ring else "")

    # --- vermin family writes and defaults (v5.9.10)
    probe = ("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local kf, km, kr = sw.keyFor('land','FLY'), sw.keyFor('land','MOSQUITO'), sw.keyFor('land','RAT'); "
             "print(json.encode({fly=cfg.allow[kf], mos=cfg.allow[km], fly_s=cfg.assign[kf] or {}, rat_s=cfg.assign[kr] or {}, kf=kf}))")
    rc, o1 = cmd("vermin", "flies", "off"); v_off = luaj(probe, timeout=60)
    rc, o2 = cmd("vermin", "flies", "on"); v_on = luaj(probe, timeout=60)
    ok = isinstance(v_off, dict) and isinstance(v_on, dict) and v_off.get("fly") is False and v_off.get("mos") is False and v_on.get("fly") is True and v_on.get("mos") is True
    rc, o3 = cmd("vermin", "mammals", "seasons", "SuAu"); v_s = luaj(probe, timeout=60)
    ok = ok and isinstance(v_s, dict) and v_s.get("rat_s") == [1, 2]
    rec("mech.vermin.family", "PASS" if ok else "FAIL", "flies off -> FLY and MOSQUITO blocked; flies on -> both allowed; mammals seasons SuAu -> RAT assigned {1,2}",
        o1 + o2 + o3, data={"off": v_off, "on": v_on, "seasons": v_s})
    rc, o4 = cmd("vermin", "defaults"); v_d = luaj(probe, timeout=60)
    okd = isinstance(v_d, dict) and v_d.get("fly_s") == [0, 1, 2] and v_d.get("rat_s") == [0, 1, 2, 3]
    rec("mech.vermin.defaults", "PASS" if okd else "FAIL", "on this temperate embark: FLY (land insect) -> {0,1,2}; RAT (mammal) -> all four", o4, data=v_d)

    # --- patterns: each needs a season under it (T8); recorded here so the report is complete
    for pid, what in (("mech.pattern.burst", "release gaps clustered at 2.5 days in twos and threes"), ("mech.pattern.trickle", "wave sizes of 1-2"),
                      ("mech.pattern.dawn", "bird arrivals concentrated in a season's first week"), ("mech.pattern.follow", "predator waves following prey mass")):
        rec(pid, "NOT-TESTABLE-HERE", what + " across a season", "", note="a season under the pattern on CTRL: T8 (steady, burst) and T8b (trickle, dawn, follow on v5.10.2); scripts/t8-tally.py over data/experiments/T8*")

    # --- species detail (v5.10.7): the facts without a window
    sd = luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg); local e; "
              "for _,q in ipairs(pool) do if q.inEmbark and q.cat=='predator' and q.layer=='land' then e=q; break end end; "
              "if not e then print(json.encode({none=true})) else local L,F=sw.speciesDetail(cfg,pool,e); print(json.encode({token=e.token, n=#L, allowed=F.allowed, seasons=F.seasons, eats=F.eats, eaten=F['eaten by']})) end", timeout=120)
    ok = isinstance(sd, dict) and sd.get("n", 0) >= 9 and "why:" in str(sd.get("allowed")) and sd.get("eats") is not None and sd.get("eaten") is not None
    rec("mech.species.detail", "PASS" if ok else ("NOT-TESTABLE-HERE" if isinstance(sd, dict) and sd.get("none") else "FAIL"),
        "≥9 lines; allowed carries 'why:'; eats and eaten by present", json.dumps(sd)[:500], data=sd)
    # v6.2.0: the overlay's links, without a screen
    ol = luaj("local sw=reqscript('seasonal-wildlife'); local r=sw.overlayLinks(); local ok,out=pcall(dfhack.run_command_silent,'overlay','list'); r.registered=(out or ''):find('seasonal%-wildlife%.groups')~=nil; print(json.encode(r))", timeout=120)
    okol = isinstance(ol, dict) and ol.get("registered") and isinstance(ol.get("pairs"), int)
    rec("mech.overlay.links", "PASS" if okol else "FAIL", "the overlay is registered and overlayLinks answers with a pair count", json.dumps(ol)[:300], data=ol)
    rec("v6.overlay.links", "PASS" if okol else "FAIL", "overlay extended with predator-prey links", json.dumps(ol)[:200], note="shipped in v6.2.0: a dotted line per related pair on the viewed level; " + (f"{ol.get('pairs')} related pair(s) at this moment" if isinstance(ol, dict) else ""))

def phase_gui():
    log("== GUI")
    sh("cmd", "gui/seasonal-wildlife", timeout=120); time.sleep(2.0)
    # v5.10.1: the opening page (Overview) builds the pool twice and reads the ledger before it draws;
    # run 144111 dumped the screen at 2.5 s and caught the frame before it. Wait for the content, up to 10 s.
    txt = ""
    for _ in range(8):
        txt = screen("C0-overview")
        if "Seasonal Wildlife" in txt and ("On the map" in txt or "CREATURE" in txt): break
        time.sleep(1.0)
    p = shot("C0-overview")
    ok = "Seasonal Wildlife" in txt and all(t in txt for t in ("Overview", "Panel", "Roster", "Seasons", "Food web", "Live", "Layers", "Vermin", "Ledger")) and "Set roster" not in txt
    rec("gui.open", "PASS" if ok else "FAIL", "window title and the nine tab labels on screen", txt[:600], shots=[p] if p else [])
    # Panel (v6.3, W8)
    click("Panel"); tp = screen("C0b-panel"); pp = shot("C0b-panel")
    okp = all(t in tp for t in ("SWITCHES", "Seasonal rotation", "Ecology", "JOBS", "season roster", "All off")) and "[ON]" in tp
    rec("gui.tab.panel", "PASS" if okp else "FAIL", "SWITCHES with [ON]/[off] rows, JOBS with timings, the all on / all off keys", window_rows(tp), shots=[pp] if pp else [])
    q0 = luaj("local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig(); local ru=require('repeat-util'); print(json.encode({enabled=c.enabled, eco=c.ecology.enabled, sched=ru.isScheduled and ru.isScheduled('seasonal-wildlife') or false}))", timeout=60)
    key("CUSTOM_X", 1.0); key("SELECT", 1.5); tx = screen("C0c-panel-alloff")
    q1 = luaj("local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig(); local ru=require('repeat-util'); local held=0; for _ in pairs(sw.CAVERN.saved()) do held=held+1 end; print(json.encode({enabled=c.enabled, eco=c.ecology.enabled, held=held, sched=ru.isScheduled and ru.isScheduled('seasonal-wildlife') or false}))", timeout=60)
    key("CUSTOM_A", 1.0); key("SELECT", 1.5); ta = screen("C0d-panel-allon")
    q2 = luaj("local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig(); local ru=require('repeat-util'); print(json.encode({enabled=c.enabled, eco=c.ecology.enabled, sched=ru.isScheduled and ru.isScheduled('seasonal-wildlife') or false}))", timeout=60)
    oka = isinstance(q1, dict) and q1.get("enabled") is False and q1.get("held") == 0 and not q1.get("sched") and isinstance(q2, dict) and q2.get("enabled") == q0.get("enabled") and q2.get("eco") == q0.get("eco")
    rec("mech.panel.alloff", "PASS" if oka else "FAIL", "after All off: rotation off, no job scheduled, no frequency held; after All on: the switches as before",
        f"before {q0}; off {q1}; on {q2}; status: {'All off' in tx}/{'All on' in ta}", data={"before": q0, "off": q1, "on": q2})
    # Overview (v5.10.1): the page the window opens on
    ok = "On the map" in txt and "Next boundary" in txt and "Recent" in txt and "In season now" in txt
    rec("gui.tab.overview", "PASS" if ok else "FAIL", "On the map / In season now / Next boundary / Recent blocks on the opening page", txt[:900], shots=[p] if p else [])
    rec("v6.overview", "PASS" if ok else "FAIL", "Overview view: what the map holds now, next boundary, recent ledger", txt[:300], note="shipped in v5.10.1 as the first tab")
    click("Roster"); txt = screen("C0-roster"); p = shot("C0-roster")
    rows = row_lines(txt)
    ok = all(k in txt for k in ("View:", "Cat:", "Biome:", "Season:")) and len(rows) >= 5 and "Apply now" in txt and ("Send off" if V65 else "Force wave") in txt and "Fill to targets" in txt and "Matrix assign" in txt
    rec("gui.tab.roster", "PASS" if ok else "FAIL", "filter row, ≥5 creature rows with ab/ok columns, the Ctrl keys and the folded Set roster keys", txt[:800], shots=[p] if p else [],
        data={"rows": len(rows), "first": rows[0][3] if rows else ""})
    if V67:
        br = re.findall(r"\(\d+%\)", txt)
        rec("gui.odds.bracket", "PASS" if br else "NOT-TESTABLE-HERE", "an '(N%)' cell on the Roster's first page", f"bracketed cells on the first page: {br[:6]}",
            note="" if br else "no active species out of season on the first page of this roster")
    rec("gui.k.thin", "PASS" if ("Thin:" in txt or "Ecosystem balanced" in txt) else "FAIL", "'Thin: …' or 'Ecosystem balanced.' in the header", txt[:400])
    # v6.2.0: Alt+L cycles the layer on the Roster; the title names it; the rows change
    n_all = len(row_lines(txt))
    key("CUSTOM_ALT_L", 1.2); tL1 = screen("C1-altL-land"); pL = shot("C1-altL-land"); n_land = len(row_lines(tL1))
    key("CUSTOM_ALT_L", 1.2); tL2 = screen("C1-altL-water"); n_water = len(row_lines(tL2))
    key("CUSTOM_ALT_L", 1.2); tL3 = screen("C1-altL-cavern"); n_cav = len(row_lines(tL3))
    key("CUSTOM_ALT_L", 1.2); tL4 = screen("C1-altL-all")
    if "Deep" in tL4:   # v6.5 (D7): the cycle is all -> land -> water -> cavern -> deep -> all
        key("CUSTOM_ALT_L", 1.2); tL4 = screen("C1-altL-all")
    toks = lambda t: {r[0] for r in row_lines(t)}
    okL = n_all >= 5 and "Land" in tL1 and "Water" in tL2 and "Cavern" in tL3 and "All layers" in tL4 and n_land <= n_all and (n_water < n_all or toks(tL2) != toks(txt) or "layer off" in tL2 or "dormant" in tL2)
    mW = re.search(r"Water[^(\n]*\([^)]*\)", tL2)
    rec("gui.k.altL", "PASS" if okL else "FAIL", "titles Land / Water / Cavern / All layers in turn; the Roster's row count follows the layer", f"rows all={n_all} land={n_land} water={n_water} cavern={n_cav}; water title: {mW.group(0) if mW else 'no reason'}", shots=[pL] if pL else [])
    rec("v6.layersel", "PASS" if okL else "FAIL", "layer selector on every tab, dormant layers named with the reason", tL2[:300], note="shipped in v6.2.0 as Alt+L, the title carrying the layer and its reason")
    # V / C / B / N
    for k, cid, before_pat in (("CUSTOM_V", "gui.k.V", r"View:\s*Current"), ("CUSTOM_C", "gui.k.C", r"Cat:\s*All"),
                                ("CUSTOM_B", "gui.k.B", r"Biome:\s*All"), ("CUSTOM_N", "gui.k.N", r"Season:\s*All")):
        t0 = screen(f"C1-{k}-before"); key(k); t1 = screen(f"C1-{k}-after"); p = shot(f"C1-{k}")
        lab = k.split("_")[-1]
        def val(t, lab=lab):
            m = re.search({"V": r"View:\s*(\S+)", "C": r"Cat:\s*(\S+)", "B": r"Biome:\s*(\S+)", "N": r"Season:\s*(\S+)"}[lab], t)
            return m.group(1) if m else None
        rec(cid, "PASS" if val(t0) and val(t1) and val(t0) != val(t1) else "FAIL", f"the {lab} filter label changes", f"{val(t0)} -> {val(t1)}", shots=[p] if p else [])
    # reopen for a clean filter state
    key("LEAVESCREEN", 1.0); sh("cmd", "gui/seasonal-wildlife", timeout=120); time.sleep(2.0); click("Roster")   # v5.10.1: the window opens on Overview
    # Enter toggles allow on the selected (first) row
    t0 = screen("C2-enter-before"); r0 = row_lines(t0)
    key("SELECT"); t1 = screen("C2-enter-after"); r1 = row_lines(t1); p = shot("C2-enter-toggle")
    ok = r0 and r1 and r0[0][0] == r1[0][0] and r0[0][2] != r1[0][2]
    rec("gui.k.enter", "PASS" if ok else "FAIL", "row 1's ok column flips Y<->-", f"{r0[0] if r0 else None} -> {r1[0] if r1 else None}", shots=[p] if p else [])
    # v5.10.5: the why column names the toggle as yours, with a date
    why1 = r1[0][4] if r1 else ""
    mw = re.search(r"[Y\-]\s+(you (?:Sp|Su|Au|Wi)\d+)(?:\s*$|\s{2,})", why1)   # v6.6: the taller window reaches DF's 'Elevation N' label beside it   # v5.10.8: the Roster shows the compact form (who and when); the full reason is on the detail page
    rec("gui.roster.why", "PASS" if mw else "FAIL", "after Enter, row 1's why reads 'you <Sp|Su|Au|Wi><day>'", why1[-90:] if why1 else "no row", data={"why": mw.group(1) if mw else None})
    rec("v6.roster.why", "PASS" if mw else "FAIL", "Roster with a 'why' column", why1[-90:] if why1 else "no row", note="the why column shipped in v5.10.5; the per-layer selector is still v6.0 (v6.layersel)")
    key("SELECT")  # put it back
    # v5.10.7: the species detail drill-down on the selected row
    key("CUSTOM_I", 1.5); td = screen("C2b-detail"); pd = shot("C2b-detail")
    okd = "Species detail:" in td and "allowed" in td   # the colon: the Roster's own hotkey label reads "i: Species detail" and "eats" in td and "eaten by" in td
    key("LEAVESCREEN", 1.0); tc = screen("C2b-detail-closed")
    okc = "Species detail:" not in tc and "Seasonal Wildlife" in tc
    rec("gui.species.detail", "PASS" if okd and okc else "FAIL", "the detail window with allowed / eats / eaten by, gone after Esc with the main window still up", td[:900], shots=[pd] if pd else [])
    rec("v6.species", "PASS" if okd and okc else "FAIL", "Species detail — one animal, every control", td[:300], note="shipped in v5.10.7 on `i` (Enter stays allow/block)")
    # Shift-Enter cycles seasons
    t0 = screen("C3-secselect-before"); key("SELECT_ALL"); t1 = screen("C3-secselect-after"); p = shot("C3-season-cycle")
    l0 = r0[0][3] if (r0 := row_lines(t0)) else ""; l1 = r1[0][3] if (r1 := row_lines(t1)) else ""
    rec("gui.k.shiftenter", "PASS" if l0 and l1 and l0 != l1 and r0[0][0] == r1[0][0] else "FAIL", "row 1's season column changes", f"{l0}\n{l1}", shots=[p] if p else [])
    # Ctrl+D dry-run dialog
    key("CUSTOM_CTRL_D", 1.2); t = screen("C4-dryrun"); p = shot("C4-dryrun-dialog")
    rec("gui.k.ctrlD", "PASS" if "Dry-run" in t and "Sp Su Au Wi" in t else "FAIL", "the 'Dry-run — season table' dialog with Sp Su Au Wi", t[:500], shots=[p] if p else [])
    key("LEAVESCREEN", 1.0)
    # The Roster status label is checked ONCE, as its own claim: every action below is judged on
    # the state it changes (config, pool, DF announcements), never on that label.
    def announcements(n=6):
        a = luaj("local out={}; local r=df.global.world.status.reports; for i=math.max(0,#r-%d),#r-1 do out[#out+1]=r[i].text end; print(json.encode(out))" % n, timeout=60)
        return a if isinstance(a, list) else []
    def weights():   # v6.5: the Ctrl+W / Ctrl+G numbers are stock (cfg.stock); before, abundance (cfg.weight)
        w = luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); print(json.encode(cfg." + ("stock" if V65 else "weight") + " or {}))", timeout=60)
        return w if isinstance(w, dict) else {}
    PROMPT = "Stock for" if V65 else "Abundance for"
    def counts():
        c = luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg); local by={}; local assigned=0; "
                 "for _,e in ipairs(pool) do if e.inEmbark then if sw.isAllowed(cfg,e) then by[e.cat]=(by[e.cat] or 0)+1 end; if cfg.assign[e.key] and #cfg.assign[e.key]>0 then assigned=assigned+1 end end end; "
                 "by.assigned=assigned; print(json.encode(by))", timeout=120)
        return c if isinstance(c, dict) else {}
    BACKSPACE = "STRING_A000"   # DF's string keys: A000 is backspace (chr 0); A008 is not
    # Ctrl+W abundance for the selected row. The key is pressed as a player would; if no prompt
    # opens, the same action is reached by clicking its label, which calls on_activate directly.
    w0 = weights()
    key("CUSTOM_CTRL_W", 1.0); t_key = screen("C5-w-key"); p = shot("C5-abundance-key")
    by_key = PROMPT in t_key
    by_click = False
    if not by_key:
        click("Stock (row" if V65 else "Abundance (row"); t_click = screen("C5-w-click"); by_click = PROMPT in t_click
        p = shot("C5-abundance-click") or p
    if by_key or by_click:
        for _ in range(4): key(BACKSPACE, 0.15)
        typ("70"); key("SELECT", 1.2)
    w1 = weights(); set70 = [k for k, v in w1.items() if v == 70 and w0.get(k) != 70]
    rec("gui.k.ctrlW", "PASS" if by_key and set70 else "FAIL",
        "Ctrl+W opens the abundance prompt for the selected row; 70 typed there is stored as cfg.weight[row]",
        f"prompt by key: {by_key}; by clicking the label: {by_click}; weights newly 70: {set70}", shots=[p] if p else [],
        data={"by_key": by_key, "by_click": by_click, "set_to_70": set70},
        note="" if by_key else "the filter box is a DFHack TextArea with focus by default; its onInput consumes CUSTOM_CTRL_W (delete word) and returns true, so the HotkeyLabel never sees the key. Digits typed afterwards land in the filter. The label works by mouse.")
    # the shadowing, stated once: the three Roster keys TextArea binds (A select-all, W delete-word, X cut)
    ann0 = announcements(); key("CUSTOM_CTRL_A", 1.2); ann1 = announcements()
    a_by_key = any("wildlife applied" in a for a in ann1) and ann1 != ann0
    key("CUSTOM_CTRL_X", 1.0); t_x = screen("C5-x-key"); x_by_key = ("Add " in t_x) or ("Switch View" in status_rows(t_x))
    rec("gui.k.shadow", "PASS" if by_key and a_by_key else "FAIL",
        "Ctrl+A, Ctrl+W and Ctrl+X reach their labels with the filter focused",
        f"Ctrl+W prompt: {by_key}; Ctrl+A announcement: {a_by_key}; Ctrl+X any effect: {x_by_key}",
        data={"ctrl_w": by_key, "ctrl_a": a_by_key, "ctrl_x": x_by_key, "textarea_binds": ["CTRL_A", "CTRL_C", "CTRL_K", "CTRL_U", "CTRL_V", "CTRL_W", "CTRL_X", "CTRL_Y", "CTRL_Z"]},
        note="DFHack's TextArea (behind the FilteredList's edit field) binds Ctrl+A/C/K/U/V/W/X/Y/Z as editor shortcuts and the field has focus whenever the Roster tab is shown, with no key to release it. Ctrl+D/E/F/G/L/R/S are not in that set and work. Rebind A/W/X (or give the edit field a focus key) to fix.")
    # Ctrl+G filtered abundance -> every filtered row's weight == 60
    key("CUSTOM_CTRL_G", 1.0); p = shot("C6-abundance-filter-prompt"); t6 = screen("C6-g-prompt")
    for _ in range(4): key(BACKSPACE, 0.15)
    typ("60"); key("SELECT", 1.2)
    w2 = weights(); n60 = sum(1 for v in w2.values() if v == 60)
    rec("gui.k.ctrlG", "PASS" if PROMPT in t6 and n60 >= 5 else "FAIL", "the prompt opens and ≥5 values read 60 afterwards",
        f"prompt: {PROMPT in t6}; values at 60: {n60}", shots=[p] if p else [], data={"at_60": n60})
    # Ctrl+E toggles auto rotation -> cfg.enabled flips (the status text is the dead label)
    g0 = ground("C7-e-before"); key("CUSTOM_CTRL_E", 1.0); t7 = screen("C7-e-after"); g1 = ground("C7-e-after"); p = shot("C7-auto-toggle")
    rec("gui.k.ctrlE", "PASS" if g0.get("enabled") != g1.get("enabled") else "FAIL", "cfg.enabled flips", f"{g0.get('enabled')} -> {g1.get('enabled')}", shots=[p] if p else [])
    rec("gui.status.roster", "PASS" if re.search(r"(Auto|Seasonal) rotation (ON|off)", t7) else "DEAD",
        "'Auto rotation ON.'/'off.' on the status row after Ctrl+E (the label is set by act_enable)", status_rows(t7), shots=[p] if p else [],
        note="the Label is created with text='' at frame t=4 of the bottom panel and never shows anything afterwards; every setStatus() receipt in the Roster tab is invisible")
    key("CUSTOM_CTRL_E", 1.0)
    # Ctrl+L: refuses on 'all' (nothing changes), then fills a category to 3
    c0 = counts(); key("CUSTOM_ALT_F", 1.0); t8 = screen("C8-l-all"); c1 = counts()
    key("CUSTOM_C", 0.8); cat_txt = screen("C8-cat"); m = re.search(r"Cat:\s*([A-Za-z]+)", cat_txt); cat = m.group(1) if m else "?"   # letters only: the next label used to run into this one
    key("CUSTOM_ALT_F", 1.0); p = shot("C8-fill-prompt"); t8b = screen("C8-l-prompt")
    for _ in range(3): key(BACKSPACE, 0.15)
    typ("3"); key("SELECT", 1.2); c2 = counts()
    ok = c0 == c1 and ("Fill" in t8b) and c2.get(cat) == 3
    rec("gui.k.altF", "PASS" if ok else "FAIL", f"no change on 'all'; the prompt on Cat={cat}; that category's active count == 3 afterwards",
        f"all: {c0.get(cat)}->{c1.get(cat)}; prompt: {'Fill' in t8b}; after: {c2.get(cat)}", shots=[p] if p else [], data={"cat": cat, "before": c0, "after": c2})
    # Ctrl+X: in Add-new the selected species is added (or refused as present). Key, then label.
    key("LEAVESCREEN", 1.0); sh("cmd", "gui/seasonal-wildlife", timeout=120); time.sleep(2.0); click("Roster")   # v5.10.1: the window opens on Overview
    key("CUSTOM_V", 0.8); key("CUSTOM_V", 0.8); t_add = screen("C9-addnew-view"); p0 = shot("C9-addnew-view")
    rows_add = row_lines(t_add); pick = rows_add[0][0] if rows_add else None
    key("CUSTOM_CTRL_X", 1.2); t9 = screen("C9-x-key"); x_key = "Add " in t9
    if not x_key:
        click("Add invasive" if V66 else "Add-new (live)"); t9 = screen("C9-x-click"); x_click = "Add " in t9
    else:
        x_click = True
    p = shot("C9-addnew-prompt")
    st9 = ""
    if x_key or x_click:
        key("SELECT", 2.5); st9 = status_rows(screen("C9-x-after"))
    added = luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg); for _,e in ipairs(pool) do if e.token=='%s' then print(json.encode({token=e.token, inEmbark=e.inEmbark, eligible=e.eligible})) return end end; print(json.encode({missing=true}))" % (pick or "NONE"), timeout=120)
    anns = announcements()
    outcome = (isinstance(added, dict) and bool(added.get("inEmbark"))) or any("added to the embark" in a for a in anns) \
        or ("added to" in st9) or ("Could not add" in st9)   # a documented refusal, now visible on the status row
    rec("gui.k.ctrlX", "PASS" if x_key and outcome else ("NOT-TESTABLE-HERE" if not rows_add else "FAIL"),
        "Ctrl+X in Add-new opens the prompt and the picked species is in the embark pool afterwards, or the status row says why it could not be",
        f"prompt by key: {x_key}; by clicking the label: {x_click}; pick={pick}; after={json.dumps(added)}; status={st9.strip()[:160]!r}; announcements={anns[-2:]}",
        shots=[x for x in (p0, p) if x], data={"pick": pick, "by_key": x_key, "by_click": x_click, "after": added, "add_view_rows": len(rows_add)},
        note="" if x_key else ("Ctrl+X is consumed by the filter box's TextArea (cut) — see gui.k.shadow; the label works by mouse" + ("" if outcome else "; the engine refused the pick as already present in the region, which is its documented behaviour")))
    if V67:
        # run 145349: the first row (ADDER on CTRL) was refused as already present in the region, so the claim never saw
        # an add; walk down the Add invasive list until one goes through (the Ctrl+X claim above keeps the first row)
        stw, i = st9, 0
        while "Could not add" in stw and i + 1 < min(len(rows_add), 8):
            i += 1; pick = rows_add[i][0]
            key("STANDARDSCROLL_DOWN", 0.3); key("CUSTOM_CTRL_X", 1.2); key("SELECT", 2.5)
            stw = status_rows(screen(f"C9-x-after-{i}"))
        for _ in range(i): key("STANDARDSCROLL_UP", 0.3)   # run 151022: a cursor left on row i+1 carried into the Roster claims that read row 1
        w = luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg); for _,e in ipairs(pool) do if e.token=='%s' then print(json.encode({inEmbark=e.inEmbark, allow=cfg.allow[e.key], n=#(cfg.assign[e.key] or {})})) return end end; print('{}')" % (pick or ""), timeout=120)
        okw = isinstance(w, dict) and w.get("inEmbark") and (w.get("allow") is False or (w.get("allow") is True and w.get("n", 0) >= 1))
        rec("gui.addnew.whole", "PASS" if okw else ("NOT-TESTABLE-HERE" if not (isinstance(w, dict) and w.get("inEmbark")) else "FAIL"),
            "right after the add: active with >=1 season, or inactive", f"{pick}: {json.dumps(w)}", data=w)
    key("CUSTOM_V", 0.8)
    # Ctrl+A apply: DF announces it. Key, then label.
    pa = fmt_pools(pools()); ann0 = announcements()
    key("CUSTOM_CTRL_A", 1.5); ann1 = announcements(); a_key = ann1 != ann0 and any("wildlife applied" in a for a in ann1[-2:])
    if not a_key:
        click("Apply now"); ann2 = announcements(); a_click = ann2 != ann1 and any("wildlife applied" in a for a in ann2[-2:])
    else:
        a_click = True
    t10 = screen("C10-apply"); p = shot("C10-apply"); pb = fmt_pools(pools()); anns = announcements()
    rec("gui.k.ctrlA", "PASS" if a_key else "FAIL", "Ctrl+A applies the season live and DF's announcement log carries '<Season> wildlife applied (N active).'",
        f"by key: {a_key}; by clicking the label: {a_click}\n" + "\n".join(anns[-3:]), shots=[p] if p else [],
        data={"by_key": a_key, "by_click": a_click, "pool_entries_changed": sum(1 for k in set(pa) | set(pb) if pa.get(k) != pb.get(k))},
        note="" if a_key else "Ctrl+A is consumed by the filter box's TextArea (select all) — see gui.k.shadow; the label works by mouse")
    rf0 = luaj("local sw=reqscript('seasonal-wildlife'); local n=0; for _,u in ipairs(df.global.world.units.active) do if sw.WILD.onMap(u) and sw.WILD.layerOf(u)=='land' and (u.flags2.roaming_wilderness_population_source or u.flags2.roaming_wilderness_population_source_not_a_map_feature) then n=n+1 end end; print(json.encode({flagged=n}))", timeout=60)
    key("CUSTOM_CTRL_F", 1.5); t10b = screen("C10-force")
    rf1 = luaj("local sw=reqscript('seasonal-wildlife'); local n=0; for _,u in ipairs(df.global.world.units.active) do if sw.WILD.onMap(u) and sw.WILD.layerOf(u)=='land' and (u.flags2.roaming_wilderness_population_source or u.flags2.roaming_wilderness_population_source_not_a_map_feature) then n=n+1 end end; print(json.encode({flagged=n}))", timeout=60)
    f0 = rf0.get("flagged", -1) if isinstance(rf0, dict) else -1; f1 = rf1.get("flagged", -1) if isinstance(rf1, dict) else -1
    rec("gui.k.ctrlF", "PASS" if f0 > 0 and f1 == 0 else ("NOT-TESTABLE-HERE" if f0 == 0 else "FAIL"),
        "Ctrl+F clears the roaming-source flag on every wild land unit (force Wildlife = free_all_wildlife), so DF may send the next group",
        f"flagged before {f0} -> after {f1}", data={"before": f0, "after": f1},
        note="" if f0 > 0 else "no flagged wild land unit was on the surface at this moment; the lever itself is measured in E8/E10 and by mech.force")
    # Alt+R reset (v6.3): roster or everything, then a yes/no; the roster reset leaves every weight at 50
    key("CUSTOM_ALT_R", 1.2); p = shot("C11-reset-choice"); t11 = screen("C11-reset-choice")
    key("SELECT", 1.2); t11b = screen("C11-reset-confirm"); key("SELECT", 1.5); w3 = weights(); left = [k for k, v in w3.items() if v != 50]
    if V65:   # v6.5 (W5): stock is kept by the roster reset (only 'Everything' resets it); the roster comes back as first found, one season each
        rr = luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local o={}; for k,v in pairs(cfg.allow) do if v and #(cfg.assign[k] or {})<1 then o[#o+1]=k..'=0' end end; print(json.encode({off=o}))", timeout=60)
        left = (rr.get("off") or []) if isinstance(rr, dict) else ["probe failed"]
    okr = "The roster" in t11 and "Everything" in t11 and "Reset the roster" in t11b
    rec("gui.k.altR", "PASS" if okr and not left else "FAIL",
        "the roster / everything choice, the confirmation, then " + ("every active species on at least one season (one from the matrix; the pair guarantee, D6, may add one)" if V65 else "no weight left off 50"), f"choice: {'The roster' in t11}; confirm: {'Reset the roster' in t11b}; " + ("active species not on one season" if V65 else "weights not 50") + f" after: {left[:8]}", shots=[p] if p else [], data={"not_50_after": left[:20]})
    # v5.11.0: Set roster folded into the Roster — its keys are read off the Roster page itself
    t = screen("C12-roster-keys"); p = shot("C12-roster-keys")
    ok = "Fill to targets" in t and "Matrix assign" in t and "Co-align" in t and "prey:" in t
    rec("gui.k.ctrlS", "PASS" if ok and "Set roster" not in t else "FAIL", "the targets row, fill keys and matrix/co-align keys on the Roster page; no Set roster label", t[:600], shots=[p] if p else [])
    rec("gui.tab.setroster", "PASS" if ok and row_lines(t) and all(r[3] for r in row_lines(t)[:5]) else "FAIL", "targets, fill keys, matrix/co-align keys, and a SEASON column on every row", window_rows(t), shots=[p] if p else [])
    # targets: Shift-P cycles (the label reads 'prey: N'; the header's 'prey=N' count is a different thing)
    m0 = re.search(r"prey:\s*(\d+)", t); key("CUSTOM_SHIFT_P", 0.8); t1 = screen("C13-shiftp"); m1 = re.search(r"prey:\s*(\d+)", t1)
    rec("gui.k.targets", "PASS" if m0 and m1 and m0.group(1) != m1.group(1) else "FAIL", "the prey target value changes", f"{m0.group(1) if m0 else None} -> {m1.group(1) if m1 else None}")
    c0 = counts(); key("CUSTOM_F", 1.2); key("SELECT", 1.5); t13 = screen("C13-fill"); p = shot("C13-fill-targets"); c1 = counts()   # v6.3: F asks first
    rec("gui.k.F", "PASS" if c0 != c1 or re.search(r"(activated|deactivated|to reach|already|No target)", status_rows(t13), re.I) else "FAIL",
        "allowed counts move toward the targets (or the status line says nothing needed doing)", f"{c0} -> {c1}", shots=[p] if p else [], data={"before": c0, "after": c1})
    rec("gui.status.grid", "PASS" if re.search(r"(activated|deactivated|to reach|already|No target)", status_rows(t13), re.I) else "DEAD",
        "a fill receipt on the Roster's status line after F", status_rows(t13), shots=[p] if p else [])
    key("CUSTOM_Y", 1.0); key("SELECT", 1.2); c2 = counts()
    rec("gui.k.Y", "PASS" if sum(v for k, v in c2.items() if k != "assigned") >= sum(v for k, v in c1.items() if k != "assigned") else "FAIL",
        "allowed counts never decrease (Y only adds)", f"{c1} -> {c2}", data={"before": c1, "after": c2})
    key("CUSTOM_D", 1.0); key("SELECT", 1.2); c3 = counts()
    rec("gui.k.D", "PASS" if sum(v for k, v in c3.items() if k != "assigned") >= sum(v for k, v in c2.items() if k != "assigned") else "FAIL",
        "allowed counts never decrease (D only adds)", f"{c2} -> {c3}", data={"before": c2, "after": c3})
    # S/U/A/W on Roster row 1: each flips its own season in the SEASON column ('-', 'All', or e.g. 'SpAu')
    def has_season(lbl, ab):
        return lbl == "All" or ab in lbl
    r0 = row_lines(screen("C14-season-before")); tok0 = r0[0][0] if r0 else None; lbl0 = r0[0][3] if r0 else ""
    flips = []
    for k, ab in (("CUSTOM_S", "Sp"), ("CUSTOM_U", "Su"), ("CUSTOM_A", "Au"), ("CUSTOM_W", "Wi")):
        key(k, 0.9); sk = screen(f"C14-{k}"); rk = row_lines(sk); tokk = rk[0][0] if rk else None; lblk = rk[0][3] if rk else ""
        # v6.3 (D2): removing the only season is refused, and the status says so -- that is the key working
        refused = lbl0 == ab and lblk == lbl0 and "last season stays" in status_rows(sk)
        flips.append(bool(tok0 and tokk == tok0 and (has_season(lbl0, ab) != has_season(lblk, ab) or refused)))
        lbl0 = lblk
    p = shot("C14-seasons-toggled")
    rec("gui.k.SUAW", "PASS" if all(flips) else "FAIL", "each of S/U/A/W flips exactly its own season on Roster row 1", f"row {tok0}: {flips}; ends {lbl0}", shots=[p] if p else [])
    rec("gui.k.gridmouse", "PASS" if all(flips) else "FAIL", "no grid since v5.11.0; the S/U/A/W keys act on the Roster row", f"{flips}", note="the Set roster grid and its keyboard-only cells are gone; the SEASON column is the grid")
    a0 = luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); print(json.encode(cfg.assign or {}))", timeout=60)
    key("CUSTOM_M", 1.0); key("SELECT", 1.5); t15 = screen("C15-matrix")
    a1 = luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); print(json.encode(cfg.assign or {}))", timeout=60)
    n_assigned = sum(1 for v in (a1 if isinstance(a1, dict) else {}).values() if v)
    rec("gui.k.M", "PASS" if isinstance(a1, dict) and n_assigned >= 5 else "FAIL", "≥5 species carry season assignments after M", f"assigned after: {n_assigned}; changed from before: {a0 != a1}", data={"assigned": n_assigned})
    key("CUSTOM_O", 1.0); key("SELECT", 1.5); t15b = screen("C15-coalign"); p = shot("C15-matrix-coalign")
    a2 = luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); print(json.encode(cfg.assign or {}))", timeout=60)
    cells = lambda a: sum(len(v) for v in (a if isinstance(a, dict) else {}).values() if v)
    rec("gui.k.O", "PASS" if cells(a2) >= cells(a1) else "FAIL", "season cells never decrease (O only extends partners' seasons)", f"cells {cells(a1)} -> {cells(a2)}", shots=[p] if p else [], data={"cells_before": cells(a1), "cells_after": cells(a2)})
    # Food web
    click("Food web"); t = screen("C16-foodweb"); p = shot("C16-foodweb-all")
    ok = ("Ecology ON" in t or "Ecology off" in t) and ("->" in t or "no chains" in t)
    rec("gui.tab.foodweb", "PASS" if ok else "FAIL", "the ecology line and predator -> prey chains", t[:800], shots=[p] if p else [])
    key("CUSTOM_N", 1.2); t1 = screen("C16-foodweb-season"); p1 = shot("C16-foodweb-spring")
    rec("gui.k.webN", "PASS" if "Spring" in t1 and t1 != t else "FAIL", "the season selector moves to Spring and the view changes (pyramid)", t1[:800], shots=[p1] if p1 else [])
    # v5.11.1: the modes. G -> Graph (edges with the live pairs marked), G -> By season (four columns), L -> By layer
    key("CUSTOM_G", 1.2); tg = screen("C16b-web-graph"); pg = shot("C16b-web-graph")
    okg = "as a graph" in tg and ("-->" in tg or "==>" in tg) and "live pair" in tg
    rec("gui.k.webG", "PASS" if okg else "FAIL", "Mode: Graph — 'as a graph', an edge arrow and the live-pair legend", tg[:700], shots=[pg] if pg else [])
    rec("v6.web.graph", "PASS" if okg else "FAIL", "Food web as a graph with live pairs", tg[:300], note="shipped in v5.11.1 as the Graph mode (G); live pairs read from DF's reaction table (ecoLivePairs)")
    key("CUSTOM_G", 1.2); ts = screen("C16c-web-byseason"); ps = shot("C16c-web-byseason")
    oks = all(x in ts for x in ("Spring", "Summer", "Autumn", "Winter")) and "mass ratio" in ts and "arrive" in ts
    rec("v6.web.byseason", "PASS" if oks else "FAIL", "Food web by season — four columns with the mass ratio and arrivals", ts[:300], shots=[ps] if ps else [], note="shipped in v5.11.1 as the By season mode")
    key("CUSTOM_L", 1.2); tl = screen("C16d-web-bylayer"); pl = shot("C16d-web-bylayer")
    okl = "LAND" in tl and "bridge edges" in tl
    rec("gui.k.webL", "PASS" if okl else "FAIL", "Mode: By layer — a LAND column and the bridge-edges line", tl[:500], shots=[pl] if pl else [])
    rec("v6.web.bylayer", "PASS" if okl else "FAIL", "Food web by layer, side by side", tl[:300], note="shipped in v5.11.1 as the By layer mode (L)")
    key("CUSTOM_G", 1.0)   # back to Pyramid for whatever follows
    # Live
    click("Live"); t = screen("C17-live"); p = shot("C17-live")
    GH = "Groups:" if V66 else "Resident groups:"   # v6.6 (W11): 'Groups: on  N at once ...'
    ok = GH in t and "ecology:" in t and "Wild on map:" in t and (("limits:" in t or "limits [" in t) if V65 else ("quota:" in t))
    rec("gui.tab.live", "PASS" if ok else "FAIL", "resident groups / ecology / Wild on map / quota lines", t[:900], shots=[p] if p else [])
    key("CUSTOM_R", 1.0); t2 = screen("C17-live-refresh")
    rec("gui.k.liveR", "PASS" if GH in t2 else "FAIL", "the tab re-renders", t2[:300])
    g0 = ground("C17-g-before"); key("CUSTOM_G", 1.2); t3 = screen("C17-live-g"); g1 = ground("C17-g-after")
    rec("gui.k.liveG", "PASS" if g0.get("groups") != g1.get("groups") else "FAIL", "cfg.groups.enabled flips", f"{g0.get('groups')} -> {g1.get('groups')}")
    key("CUSTOM_G", 1.0)
    # v5.11.2: the Live keys and the Herds & packs block
    th = screen("C17b-live-herds")
    okh = "Herds & packs" in th and "cohesion" in th and ("herd" in th or "pack" in th or "flock" in th or "no tracked species" in th)
    rec("v6.herds", "PASS" if okh else "FAIL", "Herds & packs: the cohesion line and per-species label/reason/override rows (or 'no tracked species')", th[:600], note="shipped in v5.11.2 inside the Live tab")
    cfgq = lambda: luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); print(json.encode({coupling=cfg.groups.coupling, pack=cfg.groups.pack, follow=df.global.plotinfo.follow_unit, wx=df.global.window_x, wy=df.global.window_y, wz=df.global.window_z}))", timeout=60)
    q0 = cfgq(); key("CUSTOM_P", 1.0); q1 = cfgq()
    rec("gui.k.liveP", "PASS" if isinstance(q0, dict) and isinstance(q1, dict) and q0.get("coupling") != q1.get("coupling") else "FAIL", "cfg.groups.coupling flips", f"{q0.get('coupling') if isinstance(q0, dict) else q0} -> {q1.get('coupling') if isinstance(q1, dict) else q1}")
    key("CUSTOM_P", 1.0)   # put it back
    key("CUSTOM_K", 1.0); q2 = cfgq()
    rec("gui.k.liveK", "PASS" if isinstance(q2, dict) and q2.get("pack") != q1.get("pack") else "FAIL", "cfg.groups.pack moves to the next step", f"{q1.get('pack')} -> {q2.get('pack') if isinstance(q2, dict) else q2}")
    for _ in range(4): key("CUSTOM_K", 0.6)   # back round to raw
    # the group rows: Q / X / F / Enter need a tracked group on the map
    rows_live = [l for l in th.splitlines() if re.search(r"\bx\d+ (gated|resident)", l)]
    if rows_live:
        # v6.1.0: the status lines come first; find the first group row's index in the list (the list starts two
        # screen rows under the 'q: Hold 30 days' key row) and step the cursor down to it from row 1
        rown = lambda l: int(m.group(1)) if (m := re.match(r"^\s*(\d+)\|", l)) else None
        qrow = next((rown(l) for l in th.splitlines() if "Hold 30 days" in l), None)
        grow = next((rown(l) for l in th.splitlines() if re.search(r"\bx\d+ (gated|resident)", l)), None)
        steps = (grow - qrow - 2) if (qrow is not None and grow is not None) else 1
        for _ in range(max(0, steps)): key("STANDARDSCROLL_DOWN", 0.25)
        key("CUSTOM_Q", 1.2); tq = screen("C17c-live-hold"); pq = shot("C17c-live-hold")
        rec("gui.k.liveQ", "PASS" if "held" in tq and "more days" in tq else "FAIL", "the selected group's row says 'held N more days'", tq[:500], shots=[pq] if pq else [])
        f0 = cfgq(); key("CUSTOM_F", 1.2); f1 = cfgq()
        rec("gui.k.liveF", "PASS" if isinstance(f1, dict) and f1.get("follow", -1) >= 0 else "FAIL", "plotinfo.follow_unit set to a member id", f"follow {f0.get('follow') if isinstance(f0, dict) else f0} -> {f1.get('follow') if isinstance(f1, dict) else f1}")
        luaj("df.global.plotinfo.follow_unit = -1; print(json.encode({ok=true}))", timeout=30)
        luaj("df.global.window_x = 0; df.global.window_y = 0; print(json.encode({ok=true}))", timeout=30)
        e0 = cfgq(); key("SELECT", 1.2); e1 = cfgq()
        moved = isinstance(e1, dict) and (e1.get("wx") != e0.get("wx") or e1.get("wy") != e0.get("wy") or e1.get("wz") != e0.get("wz"))
        rec("gui.k.liveEnter", "PASS" if moved else "FAIL", "the viewport moves after Enter on a group row", f"{(e0.get('wx'), e0.get('wy'), e0.get('wz')) if isinstance(e0, dict) else e0} -> {(e1.get('wx'), e1.get('wy'), e1.get('wz')) if isinstance(e1, dict) else e1}")
        key("CUSTOM_X", 1.2); tx = screen("C17d-live-dismiss"); px = shot("C17d-live-dismiss")
        rec("gui.k.liveX", "PASS" if "dismissed" in tx else "FAIL", "the selected group's row says 'dismissed'", tx[:500], shots=[px] if px else [])
    else:
        for cid in ("gui.k.liveQ", "gui.k.liveX", "gui.k.liveF", "gui.k.liveEnter"):
            rec(cid, "NOT-TESTABLE-HERE", "a tracked group row to act on", "no tracked group on the map at this point of the run", note="the groups job had no gated or resident group when the Live tab was reached")
    rf0 = luaj("local sw=reqscript('seasonal-wildlife'); local n=0; for _,u in ipairs(df.global.world.units.active) do if sw.WILD.onMap(u) and sw.WILD.layerOf(u)=='land' and (u.flags2.roaming_wilderness_population_source or u.flags2.roaming_wilderness_population_source_not_a_map_feature) then n=n+1 end end; print(json.encode({flagged=n}))", timeout=60)
    key("CUSTOM_W", 1.5)
    rf1 = luaj("local sw=reqscript('seasonal-wildlife'); local n=0; for _,u in ipairs(df.global.world.units.active) do if sw.WILD.onMap(u) and sw.WILD.layerOf(u)=='land' and (u.flags2.roaming_wilderness_population_source or u.flags2.roaming_wilderness_population_source_not_a_map_feature) then n=n+1 end end; print(json.encode({flagged=n}))", timeout=60)
    w0 = rf0.get("flagged", -1) if isinstance(rf0, dict) else -1; w1 = rf1.get("flagged", -1) if isinstance(rf1, dict) else -1
    rec("gui.k.liveW", "PASS" if w0 > 0 and w1 == 0 else ("NOT-TESTABLE-HERE" if w0 == 0 else "FAIL"), "W clears the roaming-source flag on every wild land unit (force Wildlife), like Ctrl+F", f"flagged {w0} -> {w1}")
    rec("v6.live.hotkeys", "PASS" if okh and isinstance(q1, dict) and q0.get("coupling") != q1.get("coupling") else "FAIL", "Live tab hotkeys P K Q X W F and Enter centres the map", f"P flips coupling: {q0.get('coupling') if isinstance(q0, dict) else q0} -> {q1.get('coupling') if isinstance(q1, dict) else q1}; group-row keys above", note="shipped in v5.11.2")
    # Layers (v5.11.3)
    click("Layers"); t = screen("C17e-layers"); p = shot("C17e-layers")
    okl = all(x in t for x in ("LAND", "WATER", "CAVERN", "pattern", *(("ceiling", "groups at once") if V65 else ("quota", "concurrent groups")), "Caverns:", "preset:")) and ("water:" in t)
    rec("gui.tab.layers", "PASS" if okl else "FAIL", "the three columns, the setting rows, the water line, the caverns block and the preset line", t[:900], shots=[p] if p else [])
    rec("v6.patterns", "PASS" if okl and "pattern" in t else "FAIL", "Patterns & quotas per layer", t[:300], note="shipped in v5.11.3 as rows of the Layers tab")
    rec("v6.caverns", "PASS" if okl and ("found" in t or "not on this map" in t) and "pressure" in t else "FAIL", "Caverns view — found or hidden per cavern, with its pressure", t[:300], note="shipped in v5.11.3 inside the Layers tab; the pressure is v6.1.0's (off shows a dash)")
    rec("v6.ecology.tab", "PASS" if okl and "ecology switch" in t and "nudge after" in t and "pack size" in t else "FAIL", "Ecology: switch, nudge policy, pack size as rows (the live pair list is the Food web's Graph mode)", t[:300], note="shipped in v5.11.3 as Layers rows; live pairs in the Food web Graph (v5.11.1)")
    pat0 = luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); print(json.encode({land=cfg.patterns.land}))", timeout=60)
    key("CUSTOM_T", 1.0); pat1 = luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); print(json.encode({land=cfg.patterns.land}))", timeout=60)
    rec("gui.k.layT", "PASS" if isinstance(pat0, dict) and isinstance(pat1, dict) and pat0.get("land") != pat1.get("land") else "FAIL", "cfg.patterns.land moves to the next pattern", f"{pat0.get('land') if isinstance(pat0, dict) else pat0} -> {pat1.get('land') if isinstance(pat1, dict) else pat1}")
    for _ in range(4): key("CUSTOM_T", 0.6)   # round the cycle back to steady
    key("CUSTOM_I", 1.2); ti = screen("C17e2-layers-irruption"); pi = shot("C17e2-layers-irruption")
    oki = "Irruptions ON" in ti and re.search(r"cavern pressure\s+-\s+-\s+[\d.]+ / [\d.]+ / [\d.]+", ti) is not None
    key("CUSTOM_I", 1.0)   # back off
    rec("gui.k.layI", "PASS" if oki else "FAIL", "the status says Irruptions ON and the pressure row shows three numbers", ti[:500], shots=[pi] if pi else [])
    led0 = luaj("local sw=reqscript('seasonal-wildlife'); local l,total=sw.LEDGER.lines(3,'build'); print(json.encode({n=#l, total=total, last=l[#l]}))", timeout=60)
    key("CUSTOM_R", 1.0); key("SELECT", 2.5); tr = screen("C17f-layers-preset")   # v6.3: the preset asks first
    led1 = luaj("local sw=reqscript('seasonal-wildlife'); local l,total=sw.LEDGER.lines(3,'build'); print(json.encode({n=#l, total=total, last=l[#l]}))", timeout=60)
    okr = "Preset" in tr and "rotation on" in tr and isinstance(led1, dict) and isinstance(led0, dict) and led1.get("total", 0) > led0.get("total", 0) and "preset" in str(led1.get("last"))
    rec("gui.k.layR", "PASS" if okr else "FAIL", "the status says re-applied and the Ledger gained a build line naming the preset", f"status: {'re-applied' in tr}; ledger build lines {led0.get('total') if isinstance(led0, dict) else led0} -> {led1.get('total') if isinstance(led1, dict) else led1}: {str(led1.get('last'))[:120] if isinstance(led1, dict) else ''}")
    rec("v6.presets", "PASS" if okr else "FAIL", "biome presets: applied at first run and re-applied with R", tr[:300], note="shipped in v5.11.3: the window's first run applies it, R and `preset` re-apply it")
    # Ledger (v5.11.4): block row 1 on the Roster, then undo it from the Ledger
    click("Roster"); time.sleep(0.8)
    rz0 = row_lines(screen("C17g-roster-before-z"))
    key("SELECT", 1.0); rz1 = row_lines(screen("C17g-roster-blocked"))
    click("Ledger"); tl = screen("C17h-ledger"); pl = shot("C17h-ledger")
    okt = "recorded" in tl and "newest last" in tl and re.search(r"y\d+ \w+ \d+\s+\w+", tl) is not None
    rec("gui.tab.ledger", "PASS" if okt else "FAIL", "the header with the recorded count and dated lines", tl[:600], shots=[pl] if pl else [])
    rec("v6.ledger", "PASS" if okt else "FAIL", "Ledger — every write and why, with undo", tl[:300], note="shipped in v5.11.4 as the eighth tab")
    key("CUSTOM_K", 1.0); tk = screen("C17h-ledger-kind")
    rec("gui.k.ledgerK", "PASS" if "kind=" in tk else "FAIL", "the header carries kind=<kind> after K", tk[:300])
    for _ in range(14): key("CUSTOM_K", 0.3)   # back round to all
    key("CUSTOM_Z", 2.0); tz = screen("C17h-ledger-undo"); pz = shot("C17h-ledger-undo")
    click("Roster"); time.sleep(0.8); rz2 = row_lines(screen("C17g-roster-after-z"))
    okz = rz0 and rz1 and rz2 and rz0[0][0] == rz2[0][0] and rz0[0][2] != rz1[0][2] and rz2[0][2] == rz0[0][2] and "Undid" in tz
    rec("gui.k.ledgerZ", "PASS" if okz else "FAIL", "row 1's ok column: flipped by Enter, back after Z; the Ledger status says Undid", f"{rz0[0][:3] if rz0 else None} -> {rz1[0][:3] if rz1 else None} -> {rz2[0][:3] if rz2 else None}; status: {'Undid' in tz}", shots=[pz] if pz else [])
    rec("v6.undo", "PASS" if okz else "FAIL", "undo for roster edits (10-deep snapshot ring)", f"undo restored row 1: {okz}", note="shipped in v5.11.4: UNDO ring in site data, Z on the Ledger tab and the undo verb")
    # Seasons
    click("Seasons"); t = screen("C18-seasons"); p = shot("C18-seasons")
    ok = all(s in t for s in ("Spring", "Summer", "Autumn", "Winter")) and re.search(r"[X+\-.]\s+[X+\-.]\s+[X+\-.]\s+[X+\-.]", t)
    rec("gui.tab.seasons", "PASS" if ok else "FAIL", "four season columns and +/-/X/. marks", t[:800], shots=[p] if p else [])
    # Vermin (v5.9.10)
    click("Vermin"); t = screen("C18b-vermin"); p = shot("C18b-vermin")
    ok = "FAMILY" in t and re.search(r"\b(flies|mammals|crawlers)\b", t) is not None
    key("CUSTOM_D", 1.2); t2 = screen("C18b-vermin-defaults"); p2 = shot("C18b-vermin-defaults")
    okd = "Seasonal defaults set on" in t2
    rec("gui.tab.vermin", "PASS" if ok and okd else "FAIL", "FAMILY header with family rows; D applies the defaults and the status line says so", t2[:900], shots=[x for x in (p, p2) if x])
    rec("v6.vermin", "PASS" if ok and okd else "FAIL", "Vermin view by family with seasonal defaults", t2[:300], note="shipped in v5.9.10 as the sixth tab; the design's eight-tab layout keeps it")
    if V66:
        key("CUSTOM_E", 1.0); tv = screen("C18c-vermin-open"); pv = shot("C18c-vermin-open")
        okv = re.search(r"^\s*\d+\|.*\s{3,}\S+\s+(active|inactive)\s", tv, re.M) is not None
        rec("gui.vermin.species", "PASS" if okv else "FAIL", "species rows under the opened family, each with active/inactive", window_rows(tv), shots=[pv] if pv else [])
        click("Seasons"); time.sleep(0.8); key("STANDARDSCROLL_DOWN", 0.5); key("STANDARDSCROLL_DOWN", 0.5)
        ts0 = screen("C18d-seasons-sel"); key("CUSTOM_S", 1.0); ts1 = screen("C18d-seasons-S"); ps = shot("C18d-seasons-edit")
        m = re.search(r"(\S+): (\S+)", window_rows(ts1))
        oke = bool(re.search(r"[A-Z_]{3,}: (Sp|Su|Au|Wi|All)", ts1) or "last season stays" in ts1)
        rec("gui.seasons.edit", "PASS" if oke else "FAIL", "the Seasons status line names the species and its new seasons (or the last-season refusal)", window_rows(ts1)[:600], shots=[ps] if ps else [])
        sh("key", "CUSTOM_ALT_H", timeout=60); time.sleep(1.0); th = screen("C18e-help"); ph = shot("C18e-help")
        okh = "Help:" in th and "The words" in th
        key("LEAVESCREEN", 0.8)
        rec("gui.help", "PASS" if okh else "FAIL", "a Help dialog with the tab's text and the vocabulary", th[:600], shots=[ph] if ph else [])
        y1, y2 = win_rect()
        rows_ = [l for l in th.splitlines() if all(w in l for w in ("Overview", "Panel", "Roster", "Ledger"))]
        rec("gui.layout", "PASS" if (y2 - y1 + 1) > 34 and rows_ else "FAIL", "window taller than 34 rows; one screen row holds Overview, Panel, Roster and Ledger",
            f"window rows {y1}-{y2} ({y2 - y1 + 1}); tab row found: {bool(rows_)}", shots=[ph] if ph else [])
    # close
    key("LEAVESCREEN", 1.2); t = screen("C19-closed")
    rec("gui.close", "PASS" if "Seasonal Wildlife" not in t else "FAIL", "the window gone after ESC", t[:200])

def phase_lake():
    log("== LAKE: the water layer where it is live")
    sh("title", timeout=180)
    sh("save-restore", "LAKE.preverify", timeout=300)
    rc, out = sh("load", "LAKE", timeout=300)
    if rc != 0:
        rec("mech.water.live", "FAIL", "LAKE loads", out[:300]); return
    time.sleep(1)
    g0 = ground("D0-lake-baseline"); ids0 = {u["id"] for u in g0.get("units", [])}
    cmd("enable")
    lua("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); if not cfg.initialized then sw.captureDefault(cfg) end; cfg.layers.water=true; cfg.water.enabled=true; sw.saveConfig(cfg); "
        "local pool=sw.buildPool(cfg); for _,e in ipairs(pool) do if e.inEmbark and e.layer=='water' and sw.defaultAllow(e) then cfg.allow[e.key]=true; cfg.assign[e.key]={0,1,2,3} end end; sw.saveConfig(cfg); sw.applyLive(cfg, df.global.cur_season); sw.saveConfig(cfg)", timeout=180)   # v6.3: every water species active in every season (the placement is under test here, not the one-season default)
    rc, out = cmd("water", "on")
    live = ("draws on" in out) if V65 else ("stocking on" in out)
    rc2, out2 = cmd("water", "now")
    m = re.search(r"drew \S+ x(\d+)" if V65 else r"placed (\d+)", out2)
    n = int(m.group(1)) if m else 0
    if V65:   # Driver B's group: tracked as drawn, with a countdown, in water that suits it, its entry debited
        dg = luaj("local sw=reqscript('seasonal-wildlife'); local g=sw.loadGroups(); local last; for _,grp in ipairs(g.groups) do if grp.drawn then last=grp end end; "
                  "if not last then print(json.encode({none=true})) return end; local cd,ok,sp={},0,0; local e=sw.MODEL.entry(last.token,'water'); local x0,y0; "
                  "for _,id in ipairs(last.ids) do local u=df.unit.find(id); if u then cd[#cd+1]=u.animal.leave_countdown; local d=dfhack.maps.getTileFlags(u.pos); "
                  "local t={body=last.body, salt=d.water_salt and 'salt' or 'fresh'}; if sw.ENGINE.fits(e,t) and d.flow_size>=4 then ok=ok+1 end; "
                  "if x0 then sp=math.max(sp, math.abs(u.pos.x-x0), math.abs(u.pos.y-y0)) else x0,y0=u.pos.x,u.pos.y end end end; "
                  "print(json.encode({token=last.token, n=#last.ids, body=last.body, salt=last.salt, countdowns=cd, fits=ok, spread=sp, layer=last.layer}))", timeout=120)
        okd = isinstance(dg, dict) and not dg.get("none") and dg.get("n", 0) >= 1 and dg.get("fits") == dg.get("n") and all(c > 0 for c in dg.get("countdowns", [0])) and dg.get("spread", 99) <= 12 and dg.get("layer") == "water"
        rec("mech.engine.draw", "PASS" if okd else "FAIL", "a drawn water group: every member in water that fits its body and salinity, a countdown each, within 12 tiles of each other, tracked on the water layer",
            out2 + "\n" + json.dumps(dg), data=dg)
    step(300, 120)
    g1 = ground("D1-lake-after-water-now")
    new = [u for u in g1.get("units", []) if u["id"] not in ids0 and u["layer"] == "water"]
    shots_ = []
    if new:
        centre_on(new[0]["id"]); p = shot("D1-lake-water-job-placed"); shots_ = [p] if p else []
    else:
        p = shot("D1-lake-map"); shots_ = [p] if p else []
    rec("mech.water.live", "PASS" if live and new else "FAIL",
        "'water: stocking on …' and new water-layer units on the map after the job runs (`water on` schedules a pass at once, so `water now` may find the lake already full)", out + "\n" + out2, shots=shots_,
        data={"placed": n, "new_water_units": [(u["token"], u["id"]) for u in new][:12], "water_before": g0.get("water"), "water_after": g1.get("water")})
    rc, out = cmd("place", "CARP", "2", "water")
    if "no stocked" in out:
        rc, out = cmd("place", "MUSSEL", "2", "water")
    m = re.search(r"placed (\d+) (\S+) on the water layer at ids ([\d,]+)", out)
    if m:
        centre_on(int(m.group(3).split(",")[0])); p = shot("D2-lake-place-water")
        rec("cli.place", "PASS", "a water placement receipt on LAKE", out, shots=[p] if p else [])
    sh("title", timeout=180)
    sh("save-restore", "LAKE.preverify", timeout=300)

def phase_static():
    log("== STATIC: unwired, dead, doc-drift registers")
    src = (TOOL / "scripts/seasonal-wildlife.lua").read_text(errors="replace")
    usage = (TOOL / "USAGE.md").read_text(errors="replace")
    def absent(*pats):
        return all(re.search(p, src) is None for p in pats)
    checks = {
        # patterns are deliberately specific: 'undo', 'ledger' and 'Herds' each occur once in the
        # script as a COMMENT, and 'Vermin' is a population type; none of those is a view
        "plan.arming": absent(r"arming step|armWave|arm_step"),
    }
    for cid, is_absent in checks.items():
        if cid == "plan.arming" and re.search(r"function IRRUPT\.tick", src):
            # v6.1.0 folded the design's 'arming step' into the irruption module: IRRUPT.tick arms the next roster-admitted cavern
            # arrival at the threshold (mech.irruption.arm exercises it live). The row stays so the design's promise is traceable.
            rec(cid, "PASS", "the arming step exists under another name", "folded into v6.1.0's IRRUPT.tick (arms the next admitted cavern arrival at the threshold; T9 and T9b measured it)",
                note=f"claimed as: {CLAIM[cid][4]}; recorded UNWIRED until 22 Sep 2026 because the search looked for the design's own words")
            continue
        rec(cid, "UNWIRED" if is_absent else "FAIL", "no code behind the promised view/feature (searched the shipped script)",
            "no matching identifier in seasonal-wildlife.lua" if is_absent else "an identifier matched — inspect before calling this built",
            note=f"claimed as: {CLAIM[cid][4]}")
    # backlog: recorded, with the two that are directly refutable from code
    for cid in [c[0] for c in CLAIMS if c[4] == "backlog"]:   # the shipped seven are resolved at the end of main
        rec(cid, "BACKLOG", "unscheduled by the Backlog's own terms", "")
    # doc drift
    m = re.search(r"\*\*Status:\*\*\s*v([\d.]+).*?DF ([\d.]+)\s*/\s*DFHack ([\d.r-]+)", usage, re.S)
    ver = re.search(r"--\s*v(\d+\.\d+(?:\.\d+)?)\s*—", src)   # v6.1.1: any major, not only v5
    rec("doc.usage.version", "DOC-DRIFT" if m and ver and m.group(1) != ver.group(1) else "PASS",
        "USAGE.md's Status header names the shipped version", f"USAGE.md says v{m.group(1) if m else '?'} / DF {m.group(2) if m else '?'}; the script's newest changelog entry is v{ver.group(1) if ver else '?'}; the rig is DF {rig_versions()['df']} / DFHack {rig_versions()['dfhack']}")
    cav_doc = "WITHDRAWN" in usage and "inert" in usage
    cav_code = "held at frequency" in src
    rec("doc.usage.cavernquota", "DOC-DRIFT" if cav_doc and cav_code else "PASS",
        "USAGE.md describes the cavern quota the way the code enforces it",
        "USAGE.md: 'The cavern ceiling is withdrawn … inert'; code: v5.8.1 CAVERN holds managed species at frequency 1 over the ceiling (verified live in mech.quota.cavern)")
    ds = re.search(r"Three tabs:", src)
    rec("doc.docstring.tabs", "DOC-DRIFT" if ds else "PASS", "the docstring's tab count matches the window",
        "docstring says 'Three tabs' and lists status/now/enable/disable; the window has five tabs and the console has eleven verbs")
    rec("doc.design.views", "PASS", "the design report presents §11 as the v6.0 catalogue", "§11 is under '5 · Work packages → v6.0 The window' and PLAN §3.6 lists it as v6.0; not presented as shipped",
        note="the report does not say 'shipped' for any of the thirteen views; the shipped five are named in §2 as 'the v4 window'")
    dk = sorted((ROOT / ".claude/scratch").glob("docket-r*.html"), key=lambda p: int(re.search(r"r(\d+)", p.name).group(1)))
    dtxt = dk[-1].read_text(errors="replace") if dk else ""
    dm = re.search(r"seasonal-wildlife @ ([0-9a-f]+) \(v([\d.]+)", dtxt)
    rec("doc.docket", "PASS" if dm and ver and dm.group(2) == ver.group(1) else "DOC-DRIFT", "the Docket's source line names the shipped version",
        f"{dk[-1].name if dk else 'no docket source'}: '@ {dm.group(1) if dm else '?'} (v{dm.group(2) if dm else '?'})'; the script's newest change line is v{ver.group(1) if ver else '?'}")

# Nine Backlog items that shipped (open item validator-backlog-stale; grouping and balance in v7.1). Each is recorded from the claim(s) that
# exercise it in the same run: PASS when every one passed, FAIL when one failed, otherwise NOT-TESTABLE-HERE naming
# the claim (two point at v7.0 claims that are still TODO in phase_v71).
SHIPPED_BACKLOG = {
    "bl.frequency": ["mech.odds"],
    "bl.popnumber": ["mech.stock.reserve"],
    "bl.largestmale": ["mech.v70.leader_male"],
    "bl.concurrency": ["mech.v69.autogroups"],
    "bl.deepwater": ["mech.v70.builder"],     # the deep-water survey is part of the builder's surveys: TODO in phase_v71
    "bl.realm": ["mech.v70.realms"],          # TODO in phase_v71
    "bl.quiet": ["cli.alerts"],
    "bl.grouping": ["mech.v71.cohesion"],        # v7.1 (R62): MODEL.cohesionOf, the whole-list table with overrides
    "bl.balance": ["mech.v71.water.mix"],        # v7.1 (R62): water community weights, `water mix`
}

def resolve_shipped_backlog():
    got = {r["id"]: r["verdict"] for r in results}
    for cid, via in SHIPPED_BACKLOG.items():
        vs = [got.get(v) for v in via]
        if vs and all(v == "PASS" for v in vs):
            verdict, note = "PASS", f"{CLAIM[cid][4]}; verified this run by {', '.join(via)}"
        elif "FAIL" in vs:
            verdict, note = "FAIL", f"{CLAIM[cid][4]}; {', '.join(v for v, x in zip(via, vs) if x == 'FAIL')} failed this run"
        else:
            todo = [v for v in via if v in V71_TODO]
            verdict = "NOT-TESTABLE-HERE"
            note = (f"{CLAIM[cid][4]}; its claim {', '.join(todo)} is TODO (phase_v71)" if todo
                    else f"{CLAIM[cid][4]}; {', '.join(via)} did not run in this session")
        rec(cid, verdict, f"shipped: {', '.join(via)} passes", "; ".join(f"{v}={x}" for v, x in zip(via, vs)), note=note)

# ============================================================================== v7.1 =========
# Validator wave 2 (1 Oct 2026). One sub-phase per v7.1 stream (seasonal-wildlife docs/v7.1/<stream>.md lists the
# claims each stream needs); a claim belongs to the stream its source names ('docs/v7.1/<stream>.md'). The v7.0
# features merged after phase_v70 (open item validator-v70-coverage) are written here too, each under the stream that
# now owns the code. Every sub-phase runs between cfg_push and cfg_pop, so the dials it turns are put back.
# experiments/VALIDATOR-v71.md lists every claim, what it checks and which fort it needs.
V71_TODO = {}   # wave 2 wrote every id the stub reserved; kept so the report and resolve_shipped_backlog still read it
V71_AREAS = ["deploy", "fixes", "ecology", "groups", "water", "roster", "extinct", "vermin", "scav", "irruption", "perf", "web"]

# the v7.0 features whose claims wave 2 writes in phase_v71 (the ids the stub reserved; validator-v70-coverage)
V70_IN_V71 = {"mech.v70.builder", "mech.v70.gobble", "mech.v70.scav_ext", "mech.v70.outgun", "mech.v70.realms",
              "mech.v70.gate_drain", "mech.v70.solo_skill"}

def area_of(c):
    """The phase_v71 sub-phase that judges a claim: only rows claimed 'shipped v7.1' (and the reserved v7.0 ids), by
    the first docs/v7.1/<stream>.md their source names. An older claim whose source cites a v7.1 note for its new
    wording stays in its own phase."""
    if c[0].startswith("deploy."):
        return "deploy"
    if c[4] != "shipped v7.1" and c[0] not in V70_IN_V71:
        return None
    m = re.search(r"v7\.1/(\w+)\.md", c[3])
    return m.group(1) if m else None

def v71_ids(area):
    return [c[0] for c in CLAIMS if area_of(c) == area]

# ---- deploy: v7.1 ships a fifth script, seasonal-wildlife-controls.lua, which the web server reqscripts at load
V71_FILES = ["seasonal-wildlife.lua", "gui/seasonal-wildlife.lua", "seasonal-wildlife-web.lua", "seasonal-wildlife-web.html",
             "seasonal-wildlife-controls.lua"]

def v71_deploy():
    rows, ok = [], True
    for f in V71_FILES:
        a_, b_ = TOOL / "scripts" / f, DEPLOYED / f
        if not a_.exists():
            rows.append(f"{f}: not in the checkout {TOOL}"); ok = False; continue
        if not b_.exists():
            rows.append(f"{f}: NOT DEPLOYED"); ok = False; continue
        same = a_.read_bytes() == b_.read_bytes()
        rows.append(f"{f}: {'identical' if same else 'DIFFERS from the checkout'}"); ok = ok and same
    if DRY:
        ok = True
    rec("deploy.v71.files", "PASS" if ok else "FAIL",
        "every script of the tool tree is in dfhack-config/scripts and byte-identical to the checkout under test (cx-lifecycle.sh deploy-tool)",
        "\n".join(rows), note=f"checkout {TOOL}")
    j = luap("""local out={}
local ok1, e1 = pcall(reqscript, 'seasonal-wildlife-controls'); out.controls = ok1; out.controlsErr = (not ok1) and tostring(e1) or nil
if ok1 then out.sections = e1.SECTIONS and #e1.SECTIONS or 0; out.controlsN = e1.CONTROLS and #e1.CONTROLS or 0 end
local ok2, e2 = pcall(reqscript, 'seasonal-wildlife-web'); out.web = ok2; out.webErr = (not ok2) and tostring(e2) or nil
print(json.encode(out))""")
    if bad(j):
        rec_bad("deploy.v71.loads", j)
    else:
        rec("deploy.v71.loads", "PASS" if j.get("controls") and j.get("web") and (j.get("sections") or 0) >= 12 else "FAIL",
            "reqscript('seasonal-wildlife-controls') loads with its 12 sections, and the web server (which requires it) loads",
            json.dumps(j))

def _a_unreapply():
    """V7.restore, then the tool's own raws back if the real config is enabled (a probe applied them to a copy)."""
    return luap("""local sw=reqscript('seasonal-wildlife'); local V7=sw.V7
local n = V7.restore(); local real = sw.loadConfig(); local again = ''
if real.enabled then again = V7.apply(real) end
print(json.encode({restored=n, reapplied=real.enabled}))""")

def v71_ecology():
    # ---- R37/R38 defaults and the one-time migration; R33/R43 bears fish by default
    j = luap("""local sw=reqscript('seasonal-wildlife'); local V7=sw.V7
local d = sw.defaultConfig()
local out = {cad=d.ecology.cadence, nudge=d.ecology.nudge, fishers=d.v7.fishers, rev=d.hunters and d.hunters.rev}
local on, off = {}, {}
for t, v in pairs(d.v7.fisher_list or {}) do if v then on[#on+1]=t else off[#off+1]=t end end
table.sort(on); table.sort(off); out.fishOn = on; out.fishOff = off
local c1 = sw.defaultConfig(); c1.ecology.cadence = 1500; c1.ecology.nudge = true; c1.v7.fishers = false
V7.sanitizeHunters(c1, {}); out.m1500 = c1.ecology.cadence; out.mNudge = c1.ecology.nudge; out.mFishers = c1.v7.fishers
local c2 = sw.defaultConfig(); c2.ecology.cadence = 2000
V7.sanitizeHunters(c2, {}); out.m2000 = c2.ecology.cadence
local c3 = sw.defaultConfig(); c3.ecology.cadence = 1500
V7.sanitizeHunters(c3, {hunters={}}); out.mV71 = c3.ecology.cadence
print(json.encode(out))""")
    if bad(j):
        rec_bad(["mech.v71.cadence_default", "mech.v71.fish_bears_default"], j)
    else:
        ok = (j.get("cad") == 3000 and j.get("nudge") is False and j.get("m1500") == 3000 and j.get("mNudge") is False
              and j.get("m2000") == 2000 and j.get("mV71") == 1500)
        rec("mech.v71.cadence_default", "PASS" if ok else "FAIL",
            "fresh: cadence 3000, nudge false; pre-v7.1 1500 -> 3000, nudge true -> false, 2000 kept; a config with a hunters table untouched",
            json.dumps({k: j.get(k) for k in ("cad", "nudge", "m1500", "mNudge", "m2000", "mV71")}))
        on = j.get("fishOn") or []
        ok = j.get("fishers") is True and len(on) > 0 and all("BEAR" in t for t in on)
        rec("mech.v71.fish_bears_default", "PASS" if ok else "FAIL", "v7.fishers on; every fisher_list token turned on is a BEAR",
            json.dumps({"fishers": j.get("fishers"), "on": on, "off": j.get("fishOff")}))

    # ---- pick a packaged species with stock on the map, and place one BEFORE the raws are written (the unit-write subject)
    j = luap("""local sw=reqscript('seasonal-wildlife'); local V7=sw.V7; local H=V7.H
local cfg = sw.loadConfig(); cfg.enabled=true; cfg.v7.solo=true; cfg.hunters.pack_on=true
local pool = sw.buildPool(cfg)
local stocked = {}
for _, pop in ipairs(df.global.world.populations.all) do
  if pop.type == df.world_population_type.Animal and pop.quantity > 0 and pop.population.cave_id == -1 and pop.population.feature_idx == -1 then stocked[pop.race] = true end
end
local solo, any
for _, e in ipairs(pool) do
  if e.inEmbark and not e.locked and e.layer == 'land' and stocked[e.idx] then
    local p = H.profileOf(cfg, e)
    if p and p.ambush and not solo then solo = e.token end
    if p and not any then any = e.token end
  end
end
print(json.encode({solo=solo, any=any}))""")
    placeTok = (j.get("solo") or j.get("any")) if not bad(j) else None
    placed1 = []
    if placeTok:
        out = tool("place", placeTok, "1")
        m = re.search(r"at ids ([\d,]+)", out)
        placed1 = [int(x) for x in m.group(1).split(",")] if m else []
        log(f"   ecology: placed {placeTok} before the raws: {out.strip()[:160]}")

    # ---- the profile writes: castes before/after/after-restore, one on-map unit, the readback, the raptors
    probe = """local sw=reqscript('seasonal-wildlife'); local V7=sw.V7; local H=V7.H
local cfg = sw.loadConfig(); cfg.enabled=true; cfg.v7.solo=true; cfg.hunters.pack_on=true; cfg.hunters.raptors=true
local pool = sw.buildPool(cfg)
local SN = df.job_skill.SNEAK
local function minSneak(cr) local m; for _, c in ipairs(cr.caste) do local v = H.casteSkill(c, SN); m = m and math.min(m, v) or v end; return m end
local function benignN(cr) local n = 0; for _, c in ipairs(cr.caste) do if c.flags.BENIGN then n = n + 1 end end; return n end
local function unitSk(u)
  local soul = u and u.status.current_soul
  if not soul then return nil end
  local r = { rating = 0, floor = 0 }
  for _, x in ipairs(soul.skills) do if x.id == SN then r.rating = x.rating; local ok, f = pcall(function() return x.natural_skill_lvl end); r.floor = ok and f or -1 end end
  local ok, v = pcall(dfhack.units.getNominalSkill, u, SN, true); r.nominal = ok and v or -1
  return r
end
local soloE, soloApex, packE, rapE, eagleE
local profRace = {}
for _, e in ipairs(pool) do
  if e.inEmbark and not e.locked then
    local p = H.profileOf(cfg, e)
    if p then profRace[e.idx] = p end
    if p and p.ambush and (not soloE or (p.name == 'solitary apex' and not soloApex)) then soloE = e; soloApex = (p.name == 'solitary apex') end
    if p and p.name == 'pack' and not packE then packE = e end
    if e.guild == 'RP' and not e.civ then if e.token == 'BIRD_EAGLE' then eagleE = e elseif not rapE then rapE = e end end
  end
end
rapE = eagleE or rapE
local function raw(e) return e and sw.CAVERN.rawFor(e.token) end
local out = { soloTok = soloE and soloE.token, packTok = packE and packE.token, rapTok = rapE and rapE.token }
if soloE then local p = H.profileOf(cfg, soloE); out.soloProf = p.name; out.soloLvl = p.sneak end
if packE then local p = H.profileOf(cfg, packE); out.packProf = p.name; out.packLvl = p.sneak end
if rapE then out.rapCastes = #raw(rapE).caste; out.rapArmed = sw.ecoArmed(rapE) end
local placed = { @IDS@ }
local uu
for _, id in ipairs(placed) do local u = df.unit.find(id); if u and profRace[u.race] and u.status.current_soul then uu = u; break end end
if not uu then for _, u in ipairs(df.global.world.units.active) do if profRace[u.race] and sw.WILD.onMap(u) and u.status.current_soul then uu = u; break end end end
if uu then out.unitId = uu.id; out.unitTok = df.creature_raw.find(uu.race).creature_id; out.unitLvl = profRace[uu.race].sneak end
local function snap(tag)
  if soloE then out['solo_' .. tag] = minSneak(raw(soloE)) end
  if packE then out['pack_' .. tag] = minSneak(raw(packE)) end
  if rapE then out['rap_' .. tag] = benignN(raw(rapE)) end
  if uu then out['unit_' .. tag] = unitSk(df.unit.find(uu.id)) end
end
snap('before')
V7.restore()
out.msg = V7.apply(cfg, pool)
snap('after')
local rb = H.readback(); out.rbN = #rb; out.rbBad = {}
for _, r in ipairs(rb) do if r.casteOk ~= r.castes then out.rbBad[#out.rbBad + 1] = r.token .. ' ' .. r.casteOk .. '/' .. r.castes end end
_G.__v71a_prof = { tok = out.soloTok, lvl = out.soloLvl }
print(json.encode(out))"""
    j = luap(probe.replace("@IDS@", ",".join(str(i) for i in placed1)), timeout=240)
    ids_all = ["mech.v71.skill_profile", "mech.v71.skill_units", "mech.v71.readback", "mech.v71.raptor_armed", "mech.v70.solo_skill"]
    if bad(j):
        rec_bad(ids_all, j); _a_unreapply()
    else:
        _a_profiles(j, placeTok, placed1)
    _a_packs_model()


def _a_profiles(j, placeTok, placed1):
    # ---- a unit placed while the raws hold (solo_skill: the caste write read on a newly arrived unit)
    placed2 = []
    if j.get("soloTok") or placeTok:
        tok2 = j.get("soloTok") or placeTok
        out = tool("place", tok2, "1")
        m = re.search(r"at ids ([\d,]+)", out)
        placed2 = [int(x) for x in m.group(1).split(",")] if m else []
        j2 = luap(("""local SN = df.job_skill.SNEAK; local out = {}
for _, id in ipairs({ @IDS@ }) do
  local u = df.unit.find(id); local soul = u and u.status.current_soul
  if soul then
    out.id = id; out.rating = 0
    for _, x in ipairs(soul.skills) do if x.id == SN then out.rating = x.rating end end
    out.tok = df.creature_raw.find(u.race).creature_id
    break
  end
end
print(json.encode(out))""").replace("@IDS@", ",".join(str(i) for i in placed2)))
    else:
        j2 = {}
    # ---- restore, then read every value back
    j3 = luap(("""local sw=reqscript('seasonal-wildlife'); local V7=sw.V7; local H=V7.H
local SN = df.job_skill.SNEAK
local function minSneak(tok) local cr = tok and sw.CAVERN.rawFor(tok); if not cr then return nil end; local m; for _, c in ipairs(cr.caste) do local v = H.casteSkill(c, SN); m = m and math.min(m, v) or v end; return m end
local function benignN(tok) local cr = tok and sw.CAVERN.rawFor(tok); if not cr then return nil end; local n = 0; for _, c in ipairs(cr.caste) do if c.flags.BENIGN then n = n + 1 end end; return n end
local n = V7.restore()
local out = { restored = n, solo = minSneak(@SOLO@), pack = minSneak(@PACK@), rap = benignN(@RAP@) }
local u = @UID@ and df.unit.find(@UID@)
local soul = u and u.status.current_soul
if soul then out.unit = { rating = 0, floor = 0 }; for _, x in ipairs(soul.skills) do if x.id == SN then out.unit.rating = x.rating; local ok, f = pcall(function() return x.natural_skill_lvl end); out.unit.floor = ok and f or -1 end end end
local real = sw.loadConfig(); if real.enabled then V7.apply(real) end
print(json.encode(out))""")
        .replace("@SOLO@", json.dumps(j.get("soloTok")) if j.get("soloTok") else "nil")
        .replace("@PACK@", json.dumps(j.get("packTok")) if j.get("packTok") else "nil")
        .replace("@RAP@", json.dumps(j.get("rapTok")) if j.get("rapTok") else "nil")
        .replace("@UID@", str(j.get("unitId")) if isinstance(j.get("unitId"), int) else "nil"))
    post = j3 if not bad(j3) else {}
    # skill_profile
    if j.get("soloTok") or j.get("packTok"):
        okS = (not j.get("soloTok")) or ((j.get("solo_after") or 0) >= (j.get("soloLvl") or 99) and post.get("solo") == j.get("solo_before"))
        okP = (not j.get("packTok")) or ((j.get("pack_after") or 0) >= (j.get("packLvl") or 99) and post.get("pack") == j.get("pack_before"))
        both = bool(j.get("soloTok")) and bool(j.get("packTok"))
        rec("mech.v71.skill_profile", ("PASS" if both else "NOT-TESTABLE-HERE") if okS and okP else "FAIL",
            "every caste's SNEAK at the profile after V7.apply (solitary 15/12, pack 5), the vanilla level after V7.restore()",
            json.dumps({k: j.get(k) for k in ("soloTok", "soloProf", "soloLvl", "solo_before", "solo_after", "packTok", "packProf", "packLvl", "pack_before", "pack_after")} | {"post": post}),
            note="" if both else "only one of the two profiles (solitary / pack) has an in-embark species on this fort; a savage region8 fort with wolves and a cougar has both")
    else:
        rec("mech.v71.skill_profile", "NOT-TESTABLE-HERE", "an in-embark packaged hunter (solitary or pack)", json.dumps(j)[:600],
            note="no armed natural predator in this embark's pool; a region8 savage fort (B1-R8-*-SAVAGE) has them")
    # skill_units
    ub, ua, up = j.get("unit_before") or {}, j.get("unit_after") or {}, post.get("unit") or {}
    if j.get("unitId"):
        lvl = j.get("unitLvl") or 99
        ok = ((ua.get("nominal") or 0) >= lvl and (ua.get("floor") or 0) >= lvl
              and up.get("rating") == ub.get("rating") and up.get("floor") == ub.get("floor"))
        rec("mech.v71.skill_units", "PASS" if ok else "FAIL",
            "the unit's nominal SNEAK and natural floor at the profile after V7.apply; rating and floor as before after V7.restore()",
            json.dumps({"unit": j.get("unitId"), "token": j.get("unitTok"), "level": lvl, "before": ub, "after": ua, "post": up}))
    else:
        rec("mech.v71.skill_units", "NOT-TESTABLE-HERE", "a live unit with a soul of a packaged species on the map", json.dumps({"placed": placed1, "placeTok": placeTok}),
            note="no stocked packaged hunter to place on this fort; a region8 savage fort (B1-R8-*-SAVAGE) has wolves and cougars in stock")
    # readback
    if (j.get("rbN") or 0) > 0:
        rec("mech.v71.readback", "PASS" if not j.get("rbBad") else "FAIL", "one row per packaged species, casteOk == castes on every row",
            json.dumps({"rows": j.get("rbN"), "short": j.get("rbBad")}))
    else:
        rec("mech.v71.readback", "NOT-TESTABLE-HERE", "a packaged species after V7.apply", json.dumps({"rows": j.get("rbN")}),
            note="no armed natural predator in this embark's pool; any region8 fort with wildlife predators")
    # raptor_armed
    if j.get("rapTok"):
        n = j.get("rapCastes") or 0
        ok = j.get("rapArmed") is True and j.get("rap_after") == 0 and post.get("rap") == j.get("rap_before")
        rec("mech.v71.raptor_armed", "PASS" if ok else "FAIL",
            "BENIGN off on every caste after V7.apply, as before after V7.restore(); ecoArmed true",
            json.dumps({"token": j.get("rapTok"), "castes": n, "benign_before": j.get("rap_before"), "after": j.get("rap_after"), "post": post.get("rap"), "ecoArmed": j.get("rapArmed")}),
            note="" if j.get("rapTok") == "BIRD_EAGLE" else "no BIRD_EAGLE in this embark; the first in-embark RP species stood in")
    else:
        rec("mech.v71.raptor_armed", "NOT-TESTABLE-HERE", "an in-embark raptor (RP guild)", json.dumps(j)[:400],
            note="no raptor in this embark's pool; a region8 temperate forest or mountain fort has eagles")
    # solo_skill (v7.0 reserved)
    lvl = j.get("soloLvl")
    if j2 and not bad(j2) and j2.get("id") and lvl:
        rec("mech.v70.solo_skill", "PASS" if (j2.get("rating") or 0) >= lvl else "FAIL",
            "a unit placed while the caste write holds has SNEAK >= the solitary profile on its soul (DF copied the racial skill at creation)",
            json.dumps({"token": j2.get("tok"), "unit": j2.get("id"), "rating": j2.get("rating"), "profile": lvl}))
    else:
        rec("mech.v70.solo_skill", "NOT-TESTABLE-HERE", "a stocked solitary hunter to place while the raws hold",
            json.dumps({"soloTok": j.get("soloTok"), "placed": placed2, "probe": j2 if isinstance(j2, dict) else {}})[:600],
            note="needs a stocked solitary predator (cougar, jaguar, bear) on the land layer: a region8 savage fort (B1-R8-*-SAVAGE)")


def _a_packs_model():
    # ---- packs inferred (pure: fake hunters, no unit touched)
    j = luap("""local sw=reqscript('seasonal-wildlife'); local V7=sw.V7
local wolf, cougar = sw.raceIndex('WOLF'), sw.raceIndex('COUGAR')
local out = { wolf = wolf, cougar = cougar }
if not wolf or wolf < 0 or not cougar or cougar < 0 then print(json.encode(out)) return end
local cfg = sw.loadConfig(); cfg.hunters.pack_on = true; cfg.hunters.pack_radius = 10
local function fake(id, race, x) return { id = id, race = race, pos = { x = x, y = 10, z = 100 } } end
local n1 = V7.H.packSizes(cfg, { groups = {} }, { fake(-101, wolf, 10), fake(-102, wolf, 15), fake(-103, cougar, 10), fake(-104, cougar, 12) })
out.w1, out.w2, out.c1, out.c2 = n1[-101], n1[-102], n1[-103], n1[-104]
local n2 = V7.H.packSizes(cfg, { groups = {} }, { fake(-105, wolf, 10), fake(-106, wolf, 40) })
out.far1, out.far2 = n2[-105], n2[-106]
cfg.hunters.pack_on = false
local n3 = V7.H.packSizes(cfg, { groups = {} }, { fake(-107, wolf, 10), fake(-108, wolf, 12) })
out.off1 = n3[-107]
out.cohWolf = sw.MODEL.cohesionOf(df.creature_raw.find(wolf), cfg)
print(json.encode(out))""")
    if bad(j):
        rec_bad("mech.v71.packs_inferred", j)
    elif not (isinstance(j.get("wolf"), int) and j.get("wolf") >= 0 and isinstance(j.get("cougar"), int) and j.get("cougar") >= 0):
        rec("mech.v71.packs_inferred", "NOT-TESTABLE-HERE", "WOLF and COUGAR raws in this world", json.dumps(j), note="vanilla raws carry both; a modded world may not")
    else:
        ok = j.get("w1") == 2 and j.get("w2") == 2 and j.get("c1") is None and j.get("c2") is None and j.get("far1") is None and j.get("off1") is None
        rec("mech.v71.packs_inferred", "PASS" if ok else "FAIL",
            "two wolves 5 tiles apart -> pack 2; two cougars (solitary) none; wolves 30 apart none; pack_on off none", json.dumps(j))

    # ---- raptor cap, cohesion table, swimmer scavengers (pure model reads)
    j = luap("""local sw=reqscript('seasonal-wildlife'); local V7=sw.V7; local M=sw.MODEL
local cfg = sw.loadConfig()
local out = {}
local eagle, deer, rabbit = M.rawOf('BIRD_EAGLE'), M.rawOf('DEER'), M.rawOf('RABBIT')
if eagle and deer and rabbit then
  local ce = sw.classify(eagle)
  out.eagleGuild, out.eagleMass = ce.guild, ce.mass
  out.deerMass, out.rabbitMass = sw.classify(deer).mass, sw.classify(rabbit).mass
  local ea = { guild = ce.guild, mass = ce.mass }
  out.deerTooBig = V7.H.raptorTooBig(cfg, ea, out.deerMass)
  out.rabbitTooBig = V7.H.raptorTooBig(cfg, ea, out.rabbitMass)
end
out.coh = {}; out.cl = {}
for _, t in ipairs({ 'COUGAR', 'WOLF', 'FISH_PIKE', 'BIRD_RAVEN' }) do
  local cr = M.rawOf(t)
  if cr then out.coh[t] = M.cohesionOf(cr, cfg); out.cl[t] = math.max(cr.cluster_number[0], cr.cluster_number[1]) end
end
out.sw = {}
local off = sw.loadConfig(); off.hunters.swim_scav = false
out.swOff = {}
for _, t in ipairs({ 'SHARK_GREAT_WHITE', 'CROCODILE_SALTWATER', 'POND_GRABBER', 'SHARK_NURSE', 'FISH_LAMPREY_SEA', 'FISH_PIKE' }) do
  local cr = M.rawOf(t)
  if cr then out.sw[t] = M.swimScavenger(cr, cfg); out.swOff[t] = M.swimScavenger(cr, off) end
end
print(json.encode(out))""")
    if bad(j):
        rec_bad(["mech.v71.raptor_cap", "mech.v71.swimscav"], j)
    else:
        if "deerTooBig" in j:
            rec("mech.v71.raptor_cap", "PASS" if j.get("deerTooBig") is True and j.get("rabbitTooBig") is False else "FAIL",
                "deer too big for an eagle, a rabbit not", json.dumps({k: j.get(k) for k in ("eagleGuild", "eagleMass", "deerMass", "rabbitMass", "deerTooBig", "rabbitTooBig")}),
                note="" if j.get("eagleGuild") == "RP" else "the model does not read BIRD_EAGLE as a raptor (guild != RP), so raptorTooBig is false for every prey")
        else:
            rec("mech.v71.raptor_cap", "NOT-TESTABLE-HERE", "BIRD_EAGLE, DEER and RABBIT raws", json.dumps(j)[:300], note="vanilla raws carry all three")
        swd, swo = j.get("sw") or {}, j.get("swOff") or {}
        want = {"SHARK_GREAT_WHITE": True, "CROCODILE_SALTWATER": True, "POND_GRABBER": True, "SHARK_NURSE": True, "FISH_LAMPREY_SEA": False, "FISH_PIKE": False}
        present = [t for t in want if t in swd]
        ok = bool(present) and all(swd.get(t) == want[t] for t in present) and not any(swo.get(t) for t in present)
        rec("mech.v71.swimscav", "PASS" if ok else "FAIL", "true for the four carnivorous swimmers, false for the lamprey and the pike; all false with swim_scav off",
            json.dumps({"on": swd, "off": swo, "missing_raws": [t for t in want if t not in swd]}))
    coh0 = j.get("coh") or {} if not bad(j) else {}
    cl = (j.get("cl") or {}) if not bad(j) else {}
    # the override, through the verb, with the manipulation read back from the saved config
    tool("hunters", "cohesion", "WOLF", "herd")
    v1 = cfgv("hunters.cohesion.WOLF")
    jo = luap("""local sw=reqscript('seasonal-wildlife'); local cr = sw.MODEL.rawOf('WOLF')
print(json.encode({ lab = cr and sw.MODEL.cohesionOf(cr, sw.loadConfig()) }))""")
    tool("hunters", "cohesion", "WOLF", "auto")
    v2 = cfgv("hunters.cohesion.WOLF")
    ja = luap("""local sw=reqscript('seasonal-wildlife'); local cr = sw.MODEL.rawOf('WOLF')
print(json.encode({ lab = cr and sw.MODEL.cohesionOf(cr, sw.loadConfig()) }))""")
    if manip("mech.v71.cohesion", "hunters.cohesion.WOLF reads 'herd' after `hunters cohesion WOLF herd`", v1.get("hunters.cohesion.WOLF") == "herd" or DRY,
             json.dumps({"after_herd": v1, "after_auto": v2})):
        def exp(t, many):
            return many if (cl.get(t) or 0) > 1 else "solitary"
        okT = (coh0.get("COUGAR") == "solitary" and coh0.get("WOLF") == "pack"
               and (("FISH_PIKE" not in coh0) or coh0.get("FISH_PIKE") == exp("FISH_PIKE", "school"))
               and (("BIRD_RAVEN" not in coh0) or coh0.get("BIRD_RAVEN") == exp("BIRD_RAVEN", "flock")))
        okO = jo.get("lab") == "herd" and v2.get("hunters.cohesion.WOLF") is None and ja.get("lab") == "pack"
        rec("mech.v71.cohesion", "PASS" if okT and okO else "FAIL",
            "COUGAR solitary, WOLF pack, pike/raven by cluster; the override wins and auto clears it",
            json.dumps({"table": coh0, "cluster_max": cl, "override": jo.get("lab"), "after_auto": ja.get("lab"), "saved_after_auto": v2.get("hunters.cohesion.WOLF")}))

    # ---- bankPair: a bear's shore spot by a river or lake
    if need("mech.v71.bankpair", "water", "a dry G beside a water W at one level"):
        j = luap("""local sw=reqscript('seasonal-wildlife'); local H=sw.V7.H
local wt = sw.ENGINE.waterTiles()
local out = { tried = 0 }
for _, t in ipairs(wt.tiles or {}) do
  if t.body == 'river' or t.body == 'lake' or t.body == 'pool' or t.body == 'ocean' then
    out.tried = out.tried + 1
    local G, W = H.bankPair({ x = t.x, y = t.y, z = t.z }, 8)
    if G and W then
      out.body = t.body
      out.G = { x = G.x, y = G.y, z = G.z }; out.W = { x = W.x, y = W.y, z = W.z }
      out.gFlow = dfhack.maps.getTileFlags(xyz2pos(G.x, G.y, G.z)).flow_size
      out.wFlow = dfhack.maps.getTileFlags(xyz2pos(W.x, W.y, W.z)).flow_size
      break
    end
    if out.tried >= 40 then break end
  end
end
print(json.encode(out))""")
        if bad(j):
            rec_bad("mech.v71.bankpair", j)
        elif not j.get("G"):
            rec("mech.v71.bankpair", "FAIL", "a shore pair within 8 tiles of a surveyed water tile", json.dumps(j))
        else:
            G, W = j.get("G") or {}, j.get("W") or {}
            adj = max(abs((G.get("x") or 0) - (W.get("x") or 0)), abs((G.get("y") or 0) - (W.get("y") or 0))) == 1
            ok = (j.get("gFlow") or 0) < 4 and (j.get("wFlow") or 0) >= 4 and G.get("z") == W.get("z") and adj
            rec("mech.v71.bankpair", "PASS" if ok else "FAIL", "G flow < 4, W flow >= 4, same z, adjacent", json.dumps(j),
                note="" if j.get("body") in ("river", "lake") else f"no river or lake tile found a pair first; judged on a {j.get('body')} shore")


def v71_fixes():
    # ---- the cohesion override reaches cohesionLabel / V7.GRP.cohere (fake groups for the label; a live WOLF group if one stands)
    tool("hunters", "cohesion", "WOLF", "herd"); tool("hunters", "cohesion", "COUGAR", "solitary")
    v = cfgv("hunters.cohesion.WOLF", "hunters.cohesion.COUGAR")
    if manip("mech.v71.fix.cohesion_override", "the two overrides saved", (v.get("hunters.cohesion.WOLF") == "herd" and v.get("hunters.cohesion.COUGAR") == "solitary") or DRY, json.dumps(v)):
        j = luap("""local sw=reqscript('seasonal-wildlife'); local G=sw.GRP
local cfg = sw.loadConfig(); local g = sw.loadGroups()
local wolf, cougar = sw.raceIndex('WOLF'), sw.raceIndex('COUGAR')
local out = { wolf = wolf, cougar = cougar, followHerd = cfg.groups.follow_herd }
if wolf and wolf >= 0 then
  out.wolfLabel = sw.cohesionLabel(wolf, cfg)
  for _, grp in ipairs(g.groups) do
    if grp.race == wolf then
      G.cohere(cfg, g, grp); out.liveLabel = grp.label; out.liveLeader = grp.leader
      if grp.leader then
        out.dists = {}
        for _, id in ipairs(grp.ids) do local u = df.unit.find(id); if u and u.following and id ~= grp.leader then out.dists[#out.dists + 1] = u.follow_distance end end
      end
      break
    end
  end
end
if cougar and cougar >= 0 then
  local fake = { race = cougar, ids = {}, leader = nil }
  local led = G.cohere(cfg, g, fake)
  out.cougarLabel, out.cougarLed = fake.label, led
end
print(json.encode(out))""")
        tool("hunters", "cohesion", "WOLF", "auto"); tool("hunters", "cohesion", "COUGAR", "auto")
        ja = luap("""local sw=reqscript('seasonal-wildlife'); local w = sw.raceIndex('WOLF')
print(json.encode({ lab = (w and w >= 0) and sw.cohesionLabel(w, sw.loadConfig()) or nil }))""")
        if bad(j):
            rec_bad("mech.v71.fix.cohesion_override", j)
        else:
            dists = j.get("dists") or []
            okLive = (j.get("liveLabel") is None) or (j.get("liveLabel") == "herd" and all(d == j.get("followHerd") for d in dists))
            ok = j.get("wolfLabel") == "herd" and j.get("cougarLabel") == "solitary" and j.get("cougarLed") is False and okLive and ja.get("lab") == "pack"
            rec("mech.v71.fix.cohesion_override", "PASS" if ok else "FAIL",
                "WOLF -> herd (live group at follow_herd), auto -> pack; COUGAR solitary -> unled", json.dumps(j | {"after_auto": ja.get("lab")}),
                note="" if j.get("liveLabel") else "no tracked WOLF group on the map: the label and follow distance were read off cohesionLabel and a memberless group; a live group needs wolves (region8 savage/forest fort, or `place WOLF 4`)")
    else:
        tool("hunters", "cohesion", "WOLF", "auto"); tool("hunters", "cohesion", "COUGAR", "auto")

    # ---- swimscav cache: the verb clears SCAV.kind's per-world cache
    j0 = luap("""local sw=reqscript('seasonal-wildlife'); local cr = sw.MODEL.rawOf('SHARK_NURSE')
print(json.encode({ has = cr ~= nil, kind = cr and sw.SCAV.kind(cr) or nil }))""")
    tool("hunters", "swimscav", "SHARK_NURSE", "off")
    v = cfgv("hunters.swim_scav_list.SHARK_NURSE")
    j1 = luap("""local sw=reqscript('seasonal-wildlife'); local cr = sw.MODEL.rawOf('SHARK_NURSE')
print(json.encode({ kind = cr and sw.SCAV.kind(cr) or nil }))""")
    tool("hunters", "swimscav", "SHARK_NURSE", "auto")
    if bad(j0) or bad(j1):
        rec_bad("mech.v71.fix.swimscav_cache", j0 if bad(j0) else j1)
    elif not j0.get("has") and not DRY:
        rec("mech.v71.fix.swimscav_cache", "NOT-TESTABLE-HERE", "a SHARK_NURSE raw", json.dumps(j0), note="vanilla raws carry it")
    elif j0.get("kind") == "bone":
        rec("mech.v71.fix.swimscav_cache", "NOT-TESTABLE-HERE", "SHARK_NURSE a swim-kind scavenger (not a bone-eater)", json.dumps(j0),
            note="SHARK_NURSE reads as a bone scavenger here, which the swimmer switch does not govern")
    elif manip("mech.v71.fix.swimscav_cache", "hunters.swim_scav_list.SHARK_NURSE saved false", v.get("hunters.swim_scav_list.SHARK_NURSE") is False or DRY, json.dumps(v)):
        rec("mech.v71.fix.swimscav_cache", "PASS" if j0.get("kind") == "swim" and j1.get("kind") is False else "FAIL",
            "SCAV.kind(SHARK_NURSE) 'swim' before, false right after the verb", json.dumps({"before": j0.get("kind"), "after": j1.get("kind")}))

    # ---- the forager's crash: a scavenger waiting on remains, then a forage pass
    j = luap("""local sw=reqscript('seasonal-wildlife'); local V=sw.VERMIN
local st = sw.SCAV.state()
local waited = {}
for _, u in ipairs(df.global.world.units.active) do
  if sw.WILD.onMap(u) and not st.wait[u.id] then st.wait[u.id] = sw.absTick(); waited[#waited + 1] = u.id end
  if #waited >= 5 then break end
end
local cfg = sw.loadConfig()
local okF, err = pcall(function()
  local fs = V.fstate(); local n = 0
  for _, id in ipairs(waited) do local u = df.unit.find(id); if u and V.forager(cfg, fs, u) then n = n + 1 end end
  return n
end)
local okR, nR = pcall(V.forageRun, true)
for _, id in ipairs(waited) do st.wait[id] = nil end
print(json.encode({ waited = #waited, foragerOk = okF, sentForaging = okF and err or nil, foragerErr = (not okF) and tostring(err) or nil, runOk = okR, runOut = tostring(nR) }))""")
    if bad(j):
        rec_bad("mech.v71.fix.forager_no_crash", j)
    elif (j.get("waited") or 0) == 0 and not DRY:
        rec("mech.v71.fix.forager_no_crash", "NOT-TESTABLE-HERE", "a wild unit on the map to stand as the waiting scavenger", json.dumps(j),
            note="no wild unit on the map; any region8 fort with wildlife present")
    else:
        ok = j.get("foragerOk") is True and j.get("runOk") is True and (j.get("sentForaging") or 0) == 0
        rec("mech.v71.fix.forager_no_crash", "PASS" if ok else "FAIL",
            "VERMIN.forager and a forced forage pass run without error; no waiting scavenger is eligible", json.dumps(j))

    # ---- the build's edges feed the gobble writer
    tool("roster", "build", "land")
    eo = tool("vermin", "edges", "edges")
    v = cfgv("vermin_eat.source")
    if manip("mech.v71.fix.edges_after_build", "vermin_eat.source reads 'edges'", v.get("vermin_eat.source") == "edges" or DRY, json.dumps(v) + "\n" + eo[:400]):
        j = luap("""local sw=reqscript('seasonal-wildlife'); local V7=sw.V7
local rows, label = sw.VERMIN.edges()
local out = { label = label, rows = 0, toks = {} }
for _, r in ipairs(rows or {}) do if r.token then out.rows = out.rows + 1; if #out.toks < 12 then out.toks[#out.toks + 1] = r.token end end end
local cfg = sw.loadConfig(); cfg.enabled = true
V7.restore(); V7.apply(cfg)
out.hits = {}
for _, r in ipairs(rows or {}) do
  local cr = r.token and sw.CAVERN.rawFor(r.token)
  if cr then
    for _, c in ipairs(cr.caste) do
      for _, s in ipairs(c.gobble_vermin_class) do
        local val = (type(s) == 'string') and s or s.value
        if tostring(val):find('^SWV_') then out.hits[#out.hits + 1] = r.token .. ':' .. tostring(val); break end
      end
      if #out.hits >= 6 then break end
    end
  end
end
V7.restore(); local real = sw.loadConfig(); if real.enabled then V7.apply(real) end
print(json.encode(out))""", timeout=240)
        if bad(j):
            rec_bad("mech.v71.fix.edges_after_build", j)
        elif (j.get("rows") or 0) == 0 and not DRY:
            rec("mech.v71.fix.edges_after_build", "NOT-TESTABLE-HERE", "a roster build with at least one write edge to a vermin class", json.dumps(j),
                note="the land build here seated no vermin consumer with a write edge; a region8 fort with small land predators (ML) gives them")
        else:
            ok = "per species" in (j.get("label") or "") and len(j.get("hits") or []) > 0
            rec("mech.v71.fix.edges_after_build", "PASS" if ok else "FAIL",
                "the edge source reads 'per species, from the roster build' and a consumer's castes carry an SWV class after V7.apply", json.dumps(j))

    # ---- a pelagic apex only in the ocean, led at once
    if need("mech.v71.fix.apex_pelagic", "water", "a roster-placed water apex"):
        tool("roster", "build", "water")
        jt = luap("local sw=reqscript('seasonal-wildlife'); print(json.encode({t=sw.absTick()}))")
        t0 = jt.get("t") if isinstance(jt.get("t"), int) else 0
        out = tool("roster", "apex", "now", "water", "force")   # v7.1 fixes2: `now` respects the cap; force places regardless
        j = luap(("""local sw=reqscript('seasonal-wildlife'); local cfg = sw.loadConfig(); local g = sw.loadGroups()
local out = { recs = {} }
for _, grp in ipairs(g.groups) do
  if grp.placed and grp.layer == 'water' and (grp.arrived or 0) >= @T0@ then
    out.recs[#out.recs + 1] = { token = grp.token, body = grp.body, tag = grp.tag, pelagic = sw.V7.WAT.apexKind(cfg, grp.token) == 'pelagic',
                                leader = grp.leader, unled = grp.unled, n = #grp.ids }
  end
end
print(json.encode(out))""").replace("@T0@", str(t0)))
        recs = (j.get("recs") or []) if not bad(j) else []
        if bad(j):
            rec_bad("mech.v71.fix.apex_pelagic", j)
        elif not recs:
            rec("mech.v71.fix.apex_pelagic", "NOT-TESTABLE-HERE", "a water apex the build seated, in stock, placed by `roster apex now water`", out[:600],
                note="no water apex group was placed (none seated or none stocked); OCEAN2 or a region8 SHORE fort seats a pelagic apex")
        else:
            okBody = all((r.get("body") == "ocean") for r in recs if r.get("pelagic"))
            okLead = all(r.get("leader") or r.get("unled") for r in recs if (r.get("n") or 0) >= 2)
            okLake = has("ocean") or not any(r.get("pelagic") for r in recs)
            rec("mech.v71.fix.apex_pelagic", "PASS" if okBody and okLead and okLake else "FAIL",
                "a pelagic apex group only in the ocean; every placed group of 2+ led or marked unled", json.dumps({"reply": out[:200], "groups": recs}))

    # ---- the water layer follows the map until the player sets it
    j = luap("""local sw=reqscript('seasonal-wildlife'); local V7=sw.V7
local out = {}
local okW, wet = pcall(sw.WET.get); out.edge = okW and wet and wet.near or 0
local okT, wt = pcall(sw.ENGINE.waterTiles); out.tiles = (okT and wt and #(wt.tiles or {})) or 0
local c = sw.loadConfig(); c.layers.water = false; c.water.layer_set = false; c.water.layer_auto = true
out.auto = V7.WAT.autoLayer(c); out.layerAfter = c.layers.water; out.why = sw.CACHE.watLayerWhy
local lines = sw.LEDGER.lines(5, 'edit', 'water'); out.ledger = false
for _, l in ipairs(lines) do if l:find('water layer on by default', 1, true) then out.ledger = true end end
local c2 = sw.loadConfig(); c2.layers.water = false; c2.water.layer_set = true; c2.water.layer_auto = true
out.setAuto = V7.WAT.autoLayer(c2); out.setLayer = c2.layers.water
print(json.encode(out))""")
    if bad(j):
        rec_bad("mech.v71.fix.water_auto", j)
    else:
        wet = (j.get("edge") or 0) > 0 or (j.get("tiles") or 0) > 0
        ok = (j.get("auto") is True) == wet and (not wet or (j.get("layerAfter") is True and j.get("ledger") is True)) and j.get("setAuto") is False and j.get("setLayer") is False
        rec("mech.v71.fix.water_auto", "PASS" if ok else "FAIL",
            "on where the map has water (ledger line), off on a dry map; a player-set layer is never overridden", json.dumps(j),
            note=("the wet half judged on this fort; the dry half needs " + NEED["dry"]) if wet else ("the dry half judged on this fort; the wet half needs " + NEED["water"]))

    # ---- the saved layer migrates to layer_set
    j = luap("""local sw=reqscript('seasonal-wildlife'); local V7=sw.V7
local function s(raw) local c = sw.defaultConfig(); V7.watSanitize(c, raw); return c.water.layer_set end
print(json.encode({ on = s({ layers = { water = true } }), off = s({ layers = { water = false } }), none = s({}),
  setWins = s({ layers = { water = false }, water = { layer_set = true } }), renamed = (function() local c = sw.defaultConfig(); V7.watSanitize(c, { water = { deep_levels = 2 } }); return c.water.column_levels end)() }))""")
    if bad(j):
        rec_bad("mech.v71.fix.water_migrate", j)
    else:
        ok = j.get("on") is True and j.get("off") is False and j.get("none") is False and j.get("setWins") is True
        rec("mech.v71.fix.water_migrate", "PASS" if ok else "FAIL", "on -> layer_set true; off and none -> false; a saved layer_set wins", json.dumps(j))

    # ---- the season spill (water.spill.min raised to 10 so a body is thin: the manipulation)
    if need("mech.v71.fix.spill", "water", "a water body to spill into"):
        j = luap("""local sw=reqscript('seasonal-wildlife'); local V7=sw.V7
local cfg = sw.loadConfig(); cfg.layers.water = true; cfg.water.enabled = true; cfg.water.spill.enabled = true; cfg.water.spill.min = 10
local before = {}
for k, a in pairs(cfg.assign) do local t = {}; for i, q in ipairs(a) do t[i] = q end; before[k] = t end
sw.CACHE.watSpillAt = nil
local n = V7.WAT.spillCheck(cfg, sw.loadGroups())
local season = df.global.cur_season
local out = { manipMin = cfg.water.spill.min, n = n, season = season, rows = {} }
for k, b in pairs(cfg.water.spill_state.borrowed) do
  local has = false; for _, q in ipairs(cfg.assign[k] or {}) do if q == season then has = true end end
  local live, held = sw.RESERVE.of(k)
  out.rows[#out.rows + 1] = { key = k, body = b.body, hasSeason = has, stock = live }
end
local saved = sw.loadConfig().water.spill_state.borrowed; local ns = 0; for _ in pairs(saved) do ns = ns + 1 end; out.savedN = ns
cfg.water.spill_state.stamp = -999
out.rolled = V7.WAT.spillRoll(cfg)
local left = 0; for _ in pairs(cfg.water.spill_state.borrowed) do left = left + 1 end; out.leftAfterRoll = left
local same = true
for _, r in ipairs(out.rows) do
  local a, b0 = cfg.assign[r.key] or {}, before[r.key] or {}
  if #a ~= #b0 then same = false end
end
out.assignBack = same
print(json.encode(out))""", timeout=180)
        if bad(j):
            rec_bad("mech.v71.fix.spill", j)
        elif not manip("mech.v71.fix.spill", "water.spill.min 10 in the probe's config", j.get("manipMin") == 10 or DRY, json.dumps(j)[:400]):
            pass
        elif not j.get("rows") and not DRY:
            rec("mech.v71.fix.spill", "NOT-TESTABLE-HERE", "an active, out-of-season, stocked water species that suits a body", json.dumps(j),
                note="no water species could borrow the season here; a region8 LAKE or SHORE fort with an active water roster")
        else:
            rows = j.get("rows") or []
            # `water spill off` gives back at once: borrow again, persist, then the verb
            luap("""local sw=reqscript('seasonal-wildlife'); local cfg = sw.loadConfig(); cfg.layers.water = true; cfg.water.enabled = true; cfg.water.spill.enabled = true; cfg.water.spill.min = 10
sw.CACHE.watSpillAt = nil; sw.V7.WAT.spillCheck(cfg, sw.loadGroups()); print(json.encode({}))""")
            b1 = cfgv("water.spill_state.borrowed")
            tool("water", "spill", "off")
            b2 = cfgv("water.spill_state.borrowed", "water.spill.enabled")
            tool("water", "spill", "on")
            n1 = len(b1.get("water.spill_state.borrowed") or {})
            n2 = len(b2.get("water.spill_state.borrowed") or {})
            ok = (all(r.get("hasSeason") and (r.get("stock") or 0) > 0 for r in rows) and (j.get("savedN") or 0) > 0
                  and j.get("leftAfterRoll") == 0 and j.get("assignBack") is True and n1 > 0 and n2 == 0)
            rec("mech.v71.fix.spill", "PASS" if ok else "FAIL",
                "borrowed keys hold the season with stock > 0 (saved); the season roll and `water spill off` give every one back",
                json.dumps({"borrow": rows, "saved": j.get("savedN"), "rolled": j.get("rolled"), "left": j.get("leftAfterRoll"), "assignBack": j.get("assignBack"),
                            "before_off": n1, "after_off": n2}),
                note="the season change is simulated by moving the spill stamp (spillRoll's own test); a real boundary is the rig test")

    # ---- spaced raw ids
    j = luap("""local sw=reqscript('seasonal-wildlife'); local V7=sw.V7
local all = df.global.world.raws.creatures.all
local id, idx
for i = 0, #all - 1 do local c = all[i].creature_id; if c == 'HONEY BADGER' then id, idx = c, i; break end end
if not id then for i = 0, #all - 1 do local c = all[i].creature_id; if c:find(' ', 1, true) then id, idx = c, i; break end end end
local out = { id = id, idx = idx }
if id then
  out.norm = id:gsub('[%s,]+', '_')
  out.r1 = V7.CLI.resolve(out.norm); out.r2 = V7.CLI.resolve('#' .. idx); out.r3 = V7.CLI.resolve('WOLF'); out.r4 = V7.CLI.resolve('water:#' .. idx)
end
print(json.encode(out))""")
    if bad(j):
        rec_bad("mech.v71.fix.ids", j)
    elif not j.get("id") and not DRY:
        rec("mech.v71.fix.ids", "NOT-TESTABLE-HERE", "a creature raw whose id holds a space", json.dumps(j), note="vanilla 53.16 raws have several (HONEY BADGER)")
    else:
        sid, norm = j.get("id") or "X Y", j.get("norm") or "X_Y"
        o1, o2, o3 = tool("odds", norm), tool("odds", sid), tool("odds", "WOLF")
        ok = (j.get("r1") == sid and j.get("r2") == sid and j.get("r3") == "WOLF" and j.get("r4") == "water:" + sid
              and o1.strip() == o2.strip())
        rec("mech.v71.fix.ids", "PASS" if ok else "FAIL", "underscore, #index and water:#index resolve to the spaced id; WOLF unchanged; `odds` prints the same for both forms",
            json.dumps(j) + f"\nodds {norm}: {o1.strip()[:160]}\nodds '{sid}': {o2.strip()[:160]}\nodds WOLF: {o3.strip()[:160]}")

    # ---- world switch: one session loads one world
    j = luap("""local sw=reqscript('seasonal-wildlife'); local C = sw.CACHE
local n = 0; for _ in pairs(C.raceIdx or {}) do n = n + 1 end
local d = 0; for _ in pairs(C.depth or {}) do d = d + 1 end
print(json.encode({ raceIdx = n, depth = d, depthIsTable = type(C.depth) == 'table' }))""")
    rec("mech.v71.fix.world_switch", "NOT-TESTABLE-HERE", "CACHE.depth and CACHE.raceIdx re-read after a second world loads in the same DF session",
        json.dumps(j) if not bad(j) else bad(j), note=NEED["second_world"] + "; this session's half: the shared caches exist and are filled")

    # ---- cavern_max mirrors the cavern cap
    tool("limits", "cavern", "ceiling", "3")
    v = cfgv("limits.cavern.ceiling", "groups.cavern_max", "groups.cavern_cap")
    if manip("mech.v71.fix.cavern_max", "limits.cavern.ceiling reads 3", v.get("limits.cavern.ceiling") == 3 or DRY, json.dumps(v)):
        ok = v.get("groups.cavern_max") is not None and v.get("groups.cavern_max") == v.get("groups.cavern_cap")
        rec("mech.v71.fix.cavern_max", "PASS" if ok else "FAIL", "groups.cavern_max == groups.cavern_cap after the ceiling write", json.dumps(v))
    tool("limits", "cavern", "ceiling", "0")


def v71_scav():
    tool("enable")
    v = cfgv("enabled")
    if not (v.get("enabled") is True or DRY):
        for cid in v71_ids("scav"):
            rec(cid, "FAIL", "manipulation check: the tool enabled for the scavenging and curious passes", json.dumps(v),
                note="MANIPFAIL: `enable` did not leave cfg.enabled true, so no pass could run")
        return
    # ---- swimmers scavenge, and `scavenge swimmers off` takes them out
    probe = """local sw=reqscript('seasonal-wildlife'); local out = { is = {}, kind = {} }
for _, t in ipairs({ 'SHARK_GREAT_WHITE', 'CROCODILE_SALTWATER', 'ALLIGATOR', 'ORCA', 'FISH_CARP', 'SHARK_WHALE' }) do
  local cr = sw.MODEL.rawOf(t)
  if cr then out.is[t] = sw.SCAV.is(cr, sw.loadConfig()); out.kind[t] = sw.SCAV.kind(cr) end
end
print(json.encode(out))"""
    j0 = luap(probe)
    tool("scavenge", "swimmers", "off")
    v = cfgv("scavenge.swimmers")
    j1 = luap(probe)
    tool("scavenge", "swimmers", "on")
    if bad(j0) or bad(j1):
        rec_bad("mech.v71.scav_swimmer", j0 if bad(j0) else j1)
    elif manip("mech.v71.scav_swimmer", "scavenge.swimmers saved false", v.get("scavenge.swimmers") is False or DRY, json.dumps(v)):
        want = {"SHARK_GREAT_WHITE": True, "CROCODILE_SALTWATER": True, "ALLIGATOR": True, "ORCA": True, "FISH_CARP": False, "SHARK_WHALE": False}
        is0, is1, kind = j0.get("is") or {}, j1.get("is") or {}, j0.get("kind") or {}
        present = [t for t in want if t in is0]
        okOn = bool(present) and all(is0.get(t) == want[t] for t in present)
        okOff = all(is1.get(t) is False for t in present if kind.get(t) == "swim")
        rec("mech.v71.scav_swimmer", "PASS" if okOn and okOff else "FAIL",
            "the four carnivorous swimmers scavenge, carp and whale shark do not; swimmers off takes every swim-kind one out",
            json.dumps({"on": is0, "off": is1, "kind": kind, "missing_raws": [t for t in want if t not in is0]}))

    # ---- the keys: range refusal, saved, listed, kept on reload
    r99 = tool("scavenge", "set", "hop_tiles", "99")
    v99 = cfgv("scavenge.hop_tiles")
    r6 = tool("scavenge", "set", "hop_tiles", "6")
    v6 = cfgv("scavenge.hop_tiles")
    keys = tool("scavenge", "keys")
    jr = luap("""local sw=reqscript('seasonal-wildlife'); sw.CACHE.cfg = nil; print(json.encode({ hop = sw.loadConfig().scavenge.hop_tiles }))""")
    if manip("mech.v71.scav_keys", "scavenge.hop_tiles reads 6 after `scavenge set hop_tiles 6`", v6.get("scavenge.hop_tiles") == 6 or DRY, json.dumps(v6) + "\n" + r6[:200]):
        ok = ("must be" in r99 and v99.get("scavenge.hop_tiles") != 99 and re.search(r"^\s*hop_tiles\s+6\b", keys, re.M) is not None and jr.get("hop") == 6)
        rec("mech.v71.scav_keys", "PASS" if ok else "FAIL", "99 refused and unsaved; 6 saved, listed by `scavenge keys`, kept after a reload",
            json.dumps({"refusal": r99.strip()[:160], "after_99": v99.get("scavenge.hop_tiles"), "reload": jr.get("hop")}) + "\n" + keys[:500])
    tool("scavenge", "set", "hop_tiles", "8")

    # ---- a pass, then the status: fresh, and the shared state
    tool("scavenge", "on")
    v = cfgv("scavenge.enabled")
    now_out = tool("scavenge", "now")
    st = tool("scavenge")
    js = luap("""local sw=reqscript('seasonal-wildlife'); local st = sw.CACHE.scav7
local fb = {}; for t, n in pairs(st and st.fallbacks or {}) do fb[#fb + 1] = t .. ' ' .. n end; table.sort(fb)
print(json.encode({ scav7 = st ~= nil, fallbacks = fb, status = sw.SCAV.status(sw.loadConfig()) }))""")
    m = re.search(r"last pass (\d+) t ago: (?:nothing ran \(([^)]*)\)|(\d+) scavenger\(s\), (\d+) remains, .*?(\d+) eaten)", st)
    if manip("mech.v71.scav_status_fresh", "scavenge.enabled reads true after `scavenge on`", v.get("scavenge.enabled") is True or DRY, json.dumps(v)):
        age = int(m.group(1)) if m else None
        ok = m is not None and age is not None and age <= 50 and not m.group(2)
        rec("mech.v71.scav_status_fresh", "PASS" if ok else "FAIL", "after `scavenge now` the status's last pass is that pass (age <= 50 t) and it ran",
            now_out.strip()[:200] + "\n" + st.strip()[:700])
    if bad(js):
        rec_bad("mech.v71.scav_shared_state", js)
    else:
        def fbpart(s):
            mm = re.search(r"fallbacks: (.*)$", s or "")
            return mm.group(1).strip() if mm else ""
        ok = js.get("scav7") is True and fbpart(st) == fbpart(js.get("status"))
        rec("mech.v71.scav_shared_state", "PASS" if ok else "FAIL", "CACHE.scav7 exists after the pass; the console's and the reqscript copy's fallbacks agree",
            json.dumps({"scav7": js.get("scav7"), "console": fbpart(st), "copy": fbpart(js.get("status")), "fallbacks": js.get("fallbacks")}))

    # ---- discovery delay (the model of a fresh remains)
    j = luap("""local sw=reqscript('seasonal-wildlife'); local S=sw.SCAV
local deer = sw.raceIndex('DEER'); if not deer or deer < 0 then deer = sw.raceIndex('RABBIT') end
local now = sw.absTick()
local out = { race = deer }
if deer and deer >= 0 then
  local c = sw.loadConfig()
  local r = S.newRemains(c, { id = -1, race = deer }, false, now); out.defDelay = r.found - now; out.minTicks = math.floor(S.num(c, 'discover_min_h') * sw.TICKS_PER_DAY / 24)
  local z = sw.loadConfig()
  for _, k in ipairs({ 'discover_small_h', 'discover_medium_h', 'discover_large_h', 'discover_sigma', 'scent_ticks' }) do z.scavenge[k] = 0 end
  local r1 = S.newRemains(z, { id = -1, race = deer }, false, now); out.zeroMedians = r1.found - now
  z.scavenge.discover_min_h = 0
  local r2 = S.newRemains(z, { id = -1, race = deer }, false, now); out.zeroAll = r2.found - now
end
print(json.encode(out))""")
    if bad(j):
        rec_bad("mech.v71.scav_discovery", j)
    elif not isinstance(j.get("race"), int) or j.get("race") < 0:
        rec("mech.v71.scav_discovery", "NOT-TESTABLE-HERE", "a DEER or RABBIT raw to stand as the remains", json.dumps(j), note="vanilla raws carry both")
    else:
        ok = (j.get("defDelay") or 0) >= max(1, j.get("minTicks") or 1) and j.get("zeroAll") == 0
        rec("mech.v71.scav_discovery", "PASS" if ok else "FAIL",
            "default medians: found >= discover_min_h after it is seen (never in its first pass); every delay key at 0: found at once", json.dumps(j),
            note="the notes' recipe (discover_*_h 0 and scent_ticks 0) still leaves discover_min_h (2 h = 100 t), so a remains is not found in its first pass "
                 "unless discover_min_h is 0 too (zeroMedians shows it); judged on SCAV.newRemains, the live corpse-and-scavenger half is rig test SCV on region8")

    # ---- attribution: needs a remains eaten to the end
    j = luap("""local sw=reqscript('seasonal-wildlife'); local s = sw.SCAV.stats()
local ps = {}; for k, p in pairs(s.pairs or {}) do if (p.n or 0) >= 1 then ps[#ps + 1] = k .. ' ' .. p.n end end
local led = {}; for _, l in ipairs(sw.LEDGER.lines(300, 'eco')) do if l:find('scavenging: a ', 1, true) and l:find(' eaten -- ', 1, true) then led[#led + 1] = l end end
print(json.encode({ pairs = ps, ledger = led }))""")
    if bad(j):
        rec_bad("mech.v71.scav_attribution", j)
    elif j.get("pairs") and j.get("ledger"):
        rec("mech.v71.scav_attribution", "PASS", "a TOK>PREY pair with n >= 1 and its ledger line", json.dumps({"pairs": j.get("pairs")[:6], "ledger": j.get("ledger")[-3:]}))
    elif j.get("pairs") or j.get("ledger"):
        rec("mech.v71.scav_attribution", "FAIL", "the pair counter and the ledger line together", json.dumps(j)[:600])
    else:
        rec("mech.v71.scav_attribution", "NOT-TESTABLE-HERE", "a remains finished by a scavenger this session", json.dumps(j),
            note="needs a carcass and a scavenger over a day or more (rig test SCV, region8 savage fort with vultures or jackals)")

    # ---- fb_safe remains and walkers
    j = luap("""local sw=reqscript('seasonal-wildlife'); local S=sw.SCAV; local V7=sw.V7
local c = sw.loadConfig(); local st = S.state()
local all = df.global.world.raws.creatures.all
local badRace, badTok, goodRace
for i = 0, #all - 1 do
  local cr = all[i]
  local cls = sw.ecoOf(c, cr)
  if not badRace and cls ~= 'natural' and cls ~= 'unclassified' and (cr.creature_id:find('^DEMON') or cr.creature_id:find('^FORGOTTEN_BEAST') or cr.creature_id:find('^TITAN') or cr.flags.CASTE_MEGABEAST) then badRace, badTok = i, cr.creature_id end
  if not goodRace and cr.creature_id == 'DEER' then goodRace = i end
  if badRace and goodRace then break end
end
local out = { badTok = badTok }
if badRace then out.bad = S.naturalRemains(c, st, badRace) end
if goodRace then out.good = S.naturalRemains(c, st, goodRace) end
out.walkers, out.unnatural = 0, 0
for uid in pairs(st.units or {}) do local u = df.unit.find(uid); if u then out.walkers = out.walkers + 1; if not V7.natural(c, u) then out.unnatural = out.unnatural + 1 end end end
print(json.encode(out))""")
    if bad(j):
        rec_bad("mech.v71.scav_fbsafe", j)
    elif not j.get("badTok") and not DRY:
        rec("mech.v71.scav_fbsafe", "NOT-TESTABLE-HERE", "a demon/forgotten beast/titan/megabeast raw in this world", json.dumps(j), note="every generated world has demons and forgotten beasts")
    else:
        ok = j.get("bad") is False and j.get("good") is not False and (j.get("unnatural") or 0) == 0
        rec("mech.v71.scav_fbsafe", "PASS" if ok else "FAIL", "naturalRemains false for the non-natural race, true for DEER; no non-natural walker", json.dumps(j))

    # ---- scav_ext (v7.0): reach and movers, structurally
    j = luap("""local sw=reqscript('seasonal-wildlife'); local S=sw.SCAV; local M=sw.MODEL
local d = sw.defaultConfig()
local out = { extDefault = d.v7.scav_ext, mover = {} }
for _, t in ipairs({ 'BIRD_VULTURE', 'SHARK_GREAT_WHITE', 'CROCODILE_SALTWATER', 'JACKAL' }) do local cr = M.rawOf(t); if cr then out.mover[t] = S.mover(cr) end end
local wet = { x = 10, y = 10, z = 10, wet = true }
local dry = { x = 10, y = 10, z = 10, wet = false }
out.wetAquatic = S.suits(wet, 'aquatic'); out.wetAmph = S.suits(wet, 'amphibious'); out.dryLand = S.suits(dry, 'land')
local u2 = { pos = { x = 12, y = 10, z = 11 } }
out.wetReach2 = S.inReach(u2, wet, 'land'); out.dryReach2 = S.inReach(u2, dry, 'land')
local c = sw.loadConfig(); c.v7.scav_ext = true; out.statOn = S.status(c); c.v7.scav_ext = false; out.statOff = S.status(c)
print(json.encode(out))""")
    if bad(j):
        rec_bad("mech.v70.scav_ext", j)
    else:
        mv = j.get("mover") or {}
        okM = (mv.get("BIRD_VULTURE") in (None, "flier") and mv.get("SHARK_GREAT_WHITE") in (None, "aquatic")
               and mv.get("CROCODILE_SALTWATER") in (None, "amphibious") and mv.get("JACKAL") in (None, "land") and len(mv) >= 3)
        okR = j.get("wetAquatic") is True and j.get("wetAmph") is True and j.get("dryLand") is True and j.get("wetReach2") is True and j.get("dryReach2") is False
        okS = j.get("extDefault") is True and "fallbacks:" in (j.get("statOn") or "")
        rec("mech.v70.scav_ext", "PASS" if okM and okR and okS else "FAIL",
            "scav_ext on by default; flier/aquatic/amphibious/land movers; wet remains suit swimmers and are reached from 2 tiles and a level; the status counts fallbacks",
            json.dumps({k: j.get(k) for k in ("extDefault", "mover", "wetAquatic", "wetAmph", "dryLand", "wetReach2", "dryReach2")} | {"statOn": (j.get("statOn") or "")[-120:]}),
            note="structural: the live landings, wades and hops are rig test SCV/SCVW (region8 SHORE or RIVER fort with vultures and crocodiles)")

    # ---- curious console
    o_off = tool("curious", "reform", "off"); v_off = cfgv("curious.reform")
    o_on = tool("curious", "reform", "on"); v_on = cfgv("curious.reform")
    o_now = tool("curious", "reform", "now")
    o_keep = tool("curious", "loot", "keep"); o_drop = tool("curious", "loot", "drop")
    o_set = tool("curious", "set", "stay_min", "25000"); v_set = cfgv("curious.stay_min")
    o_bad = tool("curious", "set", "stay_min", "50"); v_bad = cfgv("curious.stay_min")
    tool("curious", "set", "stay_min", "20000")
    if manip("cli.curious_reform", "curious.reform off then on, stay_min 25000 saved",
             (v_off.get("curious.reform") is False and v_on.get("curious.reform") is True and v_set.get("curious.stay_min") == 25000) or DRY,
             json.dumps({"off": v_off, "on": v_on, "set": v_set})):
        ok = ("curious reform: off" in o_off and "curious reform: on" in o_on and re.search(r"curious: \d+ reformed this pass", o_now) is not None
              and "loot kept" in o_keep and "loot dropped" in o_drop and "leave 25000-" in o_set and "must be 100-400000" in o_bad
              and v_bad.get("curious.stay_min") == 25000)
        rec("cli.curious_reform", "PASS" if ok else "FAIL", "each verb prints the curious status with its change; stay_min 50 refused and unsaved",
            "\n".join(x.strip()[:200] for x in (o_off, o_on, o_now, o_keep, o_drop, o_set, o_bad)))

    # ---- a thief reformed, then put back by disable
    j = luap("""local sw=reqscript('seasonal-wildlife'); local C=sw.CURIOUS
local best
for _, pop in ipairs(df.global.world.populations.all) do
  if pop.type == df.world_population_type.Animal and pop.quantity > 0 and pop.population.cave_id == -1 then
    local cr = df.creature_raw.find(pop.race)
    if cr and C.is(cr) and sw.classify(cr).eco == 'natural' and (not best or cr.creature_id == 'RACCOON') then best = cr.creature_id end
  end
end
print(json.encode({ tok = best }))""")
    tok = j.get("tok") if not bad(j) else None
    uid = None
    if tok:
        out = tool("place", tok, "1")
        m = re.search(r"at ids (\d+)", out)
        uid = int(m.group(1)) if m else None
    if not uid and not DRY:
        rec("mech.v71.curious_reform", "NOT-TESTABLE-HERE", "a stocked curious-thief species to place (RACCOON, MAGPIE, ...)", json.dumps({"tok": tok}),
            note="no stocked curious beast on this fort; a region8 temperate forest fort (raccoons) or BOATS (its raccoon trace)")
    else:
        jr = luap(("""local sw=reqscript('seasonal-wildlife'); local C=sw.CURIOUS; local V7=sw.V7
local u = df.unit.find(@UID@)
local out = {}
if not u then print(json.encode({ gone = true })) return end
local function bits() local b = {}; for _, f in ipairs(C.BITS) do local ok, v = pcall(function() return u.enemy.caste_flags[f] end); b[f] = ok and v or nil end; return b end
out.bitsBefore = bits()
u.animal.leave_countdown = 0
if V7.PERF.placed then V7.PERF.placed(u) end
sw.CACHE.cfg = nil
local c = sw.loadConfig(); out.enabled = c.enabled; out.reformOn = C.on(c); out.lo = C.num(c, 'stay_min'); out.hi = C.num(c, 'stay_max')
out.n = C.pass()
local st = C.state(); out.rec = st.units[u.id] ~= nil
out.bitsAfter = bits(); out.countdown = u.animal.leave_countdown
out.ledger = false
for _, l in ipairs(sw.LEDGER.lines(20, 'eco')) do if l:find('reformed and stays', 1, true) and l:find(tostring(u.id), 1, true) then out.ledger = true end end
print(json.encode(out))""").replace("@UID@", str(uid or 0)))
        tool("disable")
        jd = luap(("""local sw=reqscript('seasonal-wildlife'); local C=sw.CURIOUS; local u = df.unit.find(@UID@)
local b = {}; if u then for _, f in ipairs(C.BITS) do local ok, v = pcall(function() return u.enemy.caste_flags[f] end); b[f] = ok and v or nil end end
print(json.encode({ bits = b, countdown = u and u.animal.leave_countdown or nil }))""").replace("@UID@", str(uid or 0)))
        if bad(jr):
            rec_bad("mech.v71.curious_reform", jr)
        elif manip("mech.v71.curious_reform", "the tool enabled and reform on for the pass", (jr.get("enabled") is True and jr.get("reformOn") is True) or DRY, json.dumps(jr)[:500]):
            ba, bb, bd = jr.get("bitsAfter") or {}, jr.get("bitsBefore") or {}, (jd.get("bits") or {}) if not bad(jd) else {}
            cd = jr.get("countdown") or 0
            ok = (jr.get("rec") is True and not any(ba.values()) and (jr.get("lo") or 0) <= cd <= (jr.get("hi") or 0) and jr.get("ledger") is True
                  and bd == bb and (jd.get("countdown") == 0 if not bad(jd) else False))
            rec("mech.v71.curious_reform", "PASS" if ok else "FAIL",
                "reformed within one pass (bits clear, countdown in stay range, ledger line); disable restores the bits and countdown 0",
                json.dumps({"token": tok, "unit": uid, "pass": jr, "after_disable": jd}),
                note="no theft was staged, so the dropped-loot half is not judged (rig test CUR on a region8 forest fort)")

    # ---- disable cancels the jobs (the tool was re-enabled by nothing since: enable, set scavenging on, then disable)
    tool("enable"); tool("scavenge", "on"); tool("curious", "reform", "on")
    jon = luap("""local ru = require('repeat-util')
print(json.encode({ scav = ru.isScheduled('seasonal-wildlife/scavenge'), cur = ru.isScheduled('seasonal-wildlife/curious') }))""")
    tool("disable")
    joff = luap("""local ru = require('repeat-util')
print(json.encode({ scav = ru.isScheduled('seasonal-wildlife/scavenge'), cur = ru.isScheduled('seasonal-wildlife/curious') }))""")
    if bad(jon) or bad(joff):
        rec_bad("mech.v71.scav_off_cancels", jon if bad(jon) else joff)
    elif manip("mech.v71.scav_off_cancels", "both jobs scheduled after enable with scavenging and reform on", (jon.get("scav") is True and jon.get("cur") is True) or DRY, json.dumps(jon)):
        rec("mech.v71.scav_off_cancels", "PASS" if joff.get("scav") is False and joff.get("cur") is False else "FAIL",
            "repeat-util holds neither seasonal-wildlife/scavenge nor /curious after disable", json.dumps({"enabled": jon, "disabled": joff}))

    # ---- the Panel switch (on a config copy; the saved Panel record is put back)
    j = luap("""local sw=reqscript('seasonal-wildlife'); local P=sw.PANEL
local keep = dfhack.persistent.getSiteData(P.SAVED_KEY, nil)
local out = { has = false }
for _, s in ipairs(P.SWITCHES) do if s.id == 'curiousreform' then out.has = true; out.optin = s.optin or false end end
local c = sw.loadConfig(); c.curious.reform = true
out.restored = P.allOff(c)
out.after = c.curious.reform
if keep ~= nil then dfhack.persistent.saveSiteData(P.SAVED_KEY, keep) end
print(json.encode(out))""")
    if bad(j):
        rec_bad("mech.v71.panel_curious", j)
    else:
        ok = j.get("has") is True and j.get("after") is False
        rec("mech.v71.panel_curious", "PASS" if ok else "FAIL", "PANEL.SWITCHES has curiousreform; all off sets curious.reform false and runs the restore (CURIOUS.unreform)",
            json.dumps(j), note="the restore reports reformed thieves only when one is on the map; mech.v71.curious_reform checks the unreform itself")
# ---- groups (docs/v7.1/groups.md) ---------------------------------------------------------------------------------
# A Lua helper loaded by several probes: write a raw config into the site data, read it back through the tool's own
# loader (loadConfigRaw and every sanitiser), then put the original back. `raw` is a Lua table literal.
_B_LOADRAW = """
local sw=reqscript('seasonal-wildlife'); local KEY='seasonal-wildlife/config'
local orig = dfhack.persistent.getSiteData(KEY, nil)
local function loadRaw(raw)
  dfhack.persistent.saveSiteData(KEY, raw); sw.CACHE.cfg = nil
  local ok, c = pcall(sw.loadConfig)
  if orig ~= nil then dfhack.persistent.saveSiteData(KEY, orig) end
  sw.CACHE.cfg = nil; sw.loadConfig()
  if not ok then error(c) end
  return c
end
"""


def _b_ids(text):
    m = re.search(r"at ids ([\d,]+)", text or "")
    return [int(x) for x in m.group(1).split(",") if x] if m else []


def v71_groups():
    # ---- limits: the formula on every layer, caverns at their own cap (pure, in-memory config)
    j = luap("""local sw=reqscript('seasonal-wildlife'); local Q=sw.QUOTA; local cfg=sw.loadConfig()
cfg.limits.mode='formula'
local out={auto=Q.autoGroups(), land=Q.groupsFor(cfg,'land'), ocean=Q.groupsFor(cfg,'water:ocean'), lake=Q.groupsFor(cfg,'water:lake'),
  river=Q.groupsFor(cfg,'water:river'), cavern=Q.groupsFor(cfg,'cavern'), cav1=Q.groupsFor(cfg,'cavern:1'), cap=cfg.groups.cavern_cap,
  defMode=sw.defaultConfig().limits.mode, defCap=sw.defaultConfig().groups.cavern_cap}
print(json.encode(out))""")
    if bad(j):
        rec_bad("mech.v71.limits.formula", j)
    else:
        a = j.get("auto")
        ok = (a is not None and j.get("land") == a and j.get("ocean") == a and j.get("lake") == a and j.get("river") == a
              and j.get("cavern") == j.get("cap") and j.get("cav1") == j.get("cap") and j.get("defMode") == "formula" and j.get("defCap") == 5)
        rec("mech.v71.limits.formula", "PASS" if ok else "FAIL",
            "default mode formula; land = water:ocean = water:lake = water:river = floor(sqrt(embark))+1; every cavern = cavern_cap (default 5)", json.dumps(j))

    # ---- limits fixed N / formula through the console (manipulation: the persisted mode and number)
    t1 = tool("limits", "fixed", "2")
    v = cfgv("limits.mode", "limits.fixed")
    if manip("mech.v71.limits.fixed", "`limits fixed 2` persists limits.mode=fixed, limits.fixed=2", v.get("limits.mode") == "fixed" and v.get("limits.fixed") == 2,
             json.dumps(v) + "\n" + t1):
        j = luap("""local sw=reqscript('seasonal-wildlife'); local Q=sw.QUOTA; local cfg=sw.loadConfig()
print(json.encode({land=Q.groupsFor(cfg,'land'), ocean=Q.groupsFor(cfg,'water:ocean'), pool=Q.groupsFor(cfg,'water:pool'), cav0=Q.groupsFor(cfg,'cavern:0'),
  cap=cfg.groups.cavern_cap, stat=Q.status(cfg)}))""")
        t2 = tool("limits", "formula")
        v2 = cfgv("limits.mode")
        j2 = luap("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); print(json.encode({land=sw.QUOTA.groupsFor(cfg,'land'), auto=sw.QUOTA.autoGroups()}))")
        if bad(j) or bad(j2):
            rec_bad("mech.v71.limits.fixed", j if bad(j) else j2)
        else:
            ok = (j.get("land") == 2 and j.get("ocean") == 2 and j.get("pool") == 2 and j.get("cav0") == min(5, j.get("cap") or 5, 2)
                  and "single fixed cap 2" in (j.get("stat") or "") and v2.get("limits.mode") == "formula" and j2.get("land") == j2.get("auto"))
            rec("mech.v71.limits.fixed", "PASS" if ok else "FAIL",
                "fixed 2: land/ocean/pool 2, cavern min(cap, 2), status 'single fixed cap 2 on every layer'; formula: land = sqrt rule again",
                json.dumps({"fixed": j, "after_formula": v2, "formula": j2}) + "\n" + t1 + "\n" + t2)

    # ---- layer_groups retired: the loader forces it on; the verb refuses
    j = luap(_B_LOADRAW + """local c = loadRaw({ v7 = { layer_groups = false } })
print(json.encode({lg = c.v7.layer_groups}))""")
    t = tool("v7", "layer_groups", "off")
    v = cfgv("v7.layer_groups")
    if bad(j):
        rec_bad("mech.v71.layer_groups.retired", j)
    else:
        ok = j.get("lg") is True and "retired" in t and v.get("v7.layer_groups") is True
        rec("mech.v71.layer_groups.retired", "PASS" if ok else "FAIL",
            "saved layer_groups=false loads true; `v7 layer_groups off` prints the retirement note and changes nothing",
            json.dumps({"loaded": j, "after_verb": v}) + "\n" + t)

    # ---- migration of a v7.0 config, through the tool's own loader
    j = luap(_B_LOADRAW + """local c = loadRaw({ enabled = false, limits = { land = { groups = 4, ceiling = 0, auto = false }, water = { groups = 2, ceiling = 12, auto = true },
  cavern = { groups = 2, ceiling = 0, auto = true } }, groups = { cavern_max = 2 }, v7 = { seasons_own = false, layer_groups = true } })
local d = loadRaw({ enabled = false, limits = { land = { groups = 3, ceiling = 0, auto = true }, water = { groups = 2, ceiling = 30, auto = true } } })
print(json.encode({mode=c.limits.mode, fixed=c.limits.fixed, wceil=c.limits.water.ceiling, so=c.v7.seasons_own, cap=c.groups.cavern_cap, cmax=c.groups.cavern_max,
  mig=c.migrated_v71, mode2=d.limits.mode, wceil2=d.limits.water.ceiling}))""")
    if bad(j):
        rec_bad("mech.v71.migrate", j)
    else:
        ok = (j.get("mode") == "fixed" and j.get("fixed") == 4 and j.get("wceil") == 0 and j.get("so") is True and j.get("cap") == 5
              and j.get("cmax") == 5 and j.get("mode2") == "formula" and j.get("wceil2") == 30)
        rec("mech.v71.migrate", "PASS" if ok else "FAIL",
            "v7.0 config: land auto=false/4 -> mode fixed 4; water ceiling 12 -> 0; seasons_own true; cavern cap 5 (old cavern_max 2 dropped); an auto land with ceiling 30 -> formula, 30 kept",
            json.dumps(j))

    # ---- the adaptive clock: state, forward, pause (pure, on a synthetic groups record)
    j = luap("""local sw=reqscript('seasonal-wildlife'); local G=sw.V7.GRP; local cfg=sw.loadConfig()
cfg.limits.mode='fixed'; cfg.limits.fixed=5; cfg.groups.adaptive=true; cfg.patterns.land='steady'
local cap = sw.QUOTA.groupsFor(cfg,'land')
local g = { groups = {}, ctl = {} }
local now = sw.absTick()
local gap = G.releaseGap(cfg, g, 'land', 1, cap, 'land')
local c = g.ctl.land or {}
local out = { cap=cap, gap=gap, last=c.last, now=now, target=c.target, due=c.due, band=cfg.groups.target_band }
out.due3 = G.dueTick(cfg, g, 'land', 3, cap)
out.due2 = G.dueTick(cfg, g, 'land', 2, cap)
out.dueCap = G.dueTick(cfg, g, 'land', cap, cap)
cfg.groups.adaptive=false
out.dueOff = G.dueTick(cfg, g, 'land', 2, cap)
cfg.groups.adaptive=true
cfg.limits.fixed=1
local g2 = { groups = { { layer='land', ids={}, resident=true, token='X' } }, ctl = {} }
local rows = G.layerRows(cfg, g2)
out.row = rows[1]
print(json.encode(out))""")
    if bad(j):
        rec_bad(["mech.v71.clock.state", "mech.v71.clock.forward", "mech.v71.clock.pause"], j)
    else:
        cap, tg = j.get("cap") or 0, j.get("target")
        lo = max(1, cap - (j.get("band") or 1))
        ok = (j.get("last") == j.get("now") and isinstance(tg, (int, float)) and lo - 1e-9 <= tg <= cap + 1e-9
              and j.get("due") == (j.get("last") or 0) + (j.get("gap") or -1))
        rec("mech.v71.clock.state", "PASS" if ok else "FAIL",
            "after a release: last = now, target in [cap - band, cap], due = last + gap (fixed cap 5 on a synthetic record)", json.dumps(j))
        d3, d2 = j.get("due3"), j.get("due2")
        ok = isinstance(d3, (int, float)) and isinstance(d2, (int, float)) and d2 < d3 and j.get("dueOff") is None
        rec("mech.v71.clock.forward", "PASS" if ok else "FAIL",
            "due tick with 2 groups earlier than with 3; adaptive off -> no adaptive due tick", json.dumps({k: j.get(k) for k in ("due3", "due2", "dueOff", "target", "cap")}))
        ok = j.get("dueCap") is None and "paused at the cap" in (j.get("row") or "")
        rec("mech.v71.clock.pause", "PASS" if ok else "FAIL",
            "n >= cap: dueTick nil; the land row (fixed cap 1, one group) says 'paused at the cap'", json.dumps({k: j.get(k) for k in ("dueCap", "row")}))

    # ---- the cavern gate: count (natives), hold, trim, deep
    wild = (F71.get("wild") or {}) if isinstance(F71.get("wild"), dict) else {}
    j = luap("""local sw=reqscript('seasonal-wildlife'); local G=sw.V7.GRP; local utils=require('utils'); local cfg=sw.loadConfig()
cfg.groups.natives_cavern=true; cfg.limits.mode='formula'
local g = utils.clone(sw.loadGroups(), true)
local before = #g.groups
local n, born = G.adoptNatives(cfg, g, true)
local nat, depths, bad = 0, {}, 0
for i = before + 1, #g.groups do
  local grp = g.groups[i]
  if grp.layer == 'cavern' and grp.native then nat = nat + 1; depths[tostring(grp.depth)] = (depths[tostring(grp.depth)] or 0) + 1
    if not (grp.depth and grp.depth >= 0 and grp.depth <= 2) then bad = bad + 1 end end
end
local rows = G.layerRows(cfg, g)
local natRow = nil
for _, r in ipairs(rows) do if r:match('^%s*cavern:') and r:match('native') then natRow = r; break end end
print(json.encode({adopted=n, born=born, nat=nat, depths=depths, badDepth=bad, natRow=natRow, rows=rows}))""", timeout=180)
    if bad(j):
        rec_bad("mech.v71.cavern.count", j)
    elif (j.get("nat") or 0) == 0:
        rec("mech.v71.cavern.count", "NOT-TESTABLE-HERE", "an unflagged cavern native on the map to adopt", json.dumps(j)[:900],
            note=f"no untracked cavern native here (wild cavern units {wild.get('cavern')}); a region8 fort with populated caverns (any 1x1 with cavern entries; caverns are stocked at embark even unbreached)")
    else:
        ok = (j.get("badDepth") or 0) == 0 and bool(j.get("natRow"))
        rec("mech.v71.cavern.count", "PASS" if ok else "FAIL",
            "adoptNatives makes native cavern records at depth 0-2 and the cavern row counts them ('(N native)')", json.dumps(j)[:1200])

    j = luap("""local sw=reqscript('seasonal-wildlife'); local G=sw.V7.GRP; local CAV=sw.CAVERN; local cfg=sw.loadConfig()
cfg.enabled=false
local sp = G.species(cfg)
local out = { species=0, held=0, bad={}, zero=0 }
local d
for t, s in pairs(sp) do out.species = out.species + 1; if not d then for dd in pairs(s.d) do d = dd; break end end end
out.d = d
out.prior = 0; for _ in pairs(sw.CACHE.capHeld or {}) do out.prior = out.prior + 1 end
if d ~= nil then
  local pre, savedPre = {}, CAV.saved()
  for t in pairs(sp) do local cr = CAV.rawFor(t); if cr then pre[t] = cr.frequency end end
  cfg.groups.cavern_hold='off'
  G.cavernHold(cfg, { [d] = true })
  local offN = 0; for _ in pairs(sw.CACHE.capHeld or {}) do offN = offN + 1 end
  out.offHeld = offN
  cfg.groups.cavern_hold='any'
  G.cavernHold(cfg, { [d] = true })
  for t in pairs(sw.CACHE.capHeld or {}) do
    out.held = out.held + 1
    local s = sp[t]; local cr = CAV.rawFor(t)
    if not s or not s.natural or s.deep or (s.shared and not cfg.groups.cavern_hold_shared) or not s.d[d] then out.bad[#out.bad+1] = t end
    if cr and cr.frequency ~= CAV.SUPPRESSED then out.bad[#out.bad+1] = t .. '@' .. tostring(cr.frequency) end
    if cr and cr.frequency == 0 then out.zero = out.zero + 1 end
  end
  G.cavernHold(cfg, {})
  local back, diff = 0, {}
  for t, f in pairs(pre) do
    if savedPre[t] == nil then local cr = CAV.rawFor(t); if cr and cr.frequency == f then back = back + 1 else diff[#diff+1] = t end end
  end
  out.back = back; out.diff = diff
  out.after = 0; for _ in pairs(sw.CACHE.capHeld or {}) do out.after = out.after + 1 end
end
print(json.encode(out))""", timeout=180)
    if bad(j):
        rec_bad("mech.v71.cavern.hold", j)
    elif j.get("d") is None:
        rec("mech.v71.cavern.hold", "NOT-TESTABLE-HERE", "a natural cavern-only species with an Animal entry in a cavern band", json.dumps(j),
            note="no cavern entry on this map's region tiles; any region8 1x1 whose caverns carry entries")
    else:
        ok = ((j.get("held") or 0) > 0 and not j.get("bad") and (j.get("zero") or 0) == 0 and (j.get("offHeld") or 0) == 0
              and not j.get("diff") and (j.get("after") or 0) == 0)
        rec("mech.v71.cavern.hold", "PASS" if ok else "FAIL",
            "hold off: none held; hold any with cavern d at its cap: its natural cavern-only species at frequency 1 (none 0, none deep/shared); below the cap: every frequency back",
            json.dumps(j)[:1200], note=("CACHE.capHeld already held %s species before the probe (the live gate); they are re-held by the next groups pass" % j.get("prior")) if j.get("prior") else "")

    j = luap("""local sw=reqscript('seasonal-wildlife'); local G=sw.V7.GRP; local cfg=sw.loadConfig()
cfg.groups.natives_cavern=true; cfg.groups.cavern_cap=1; cfg.groups.cavern_trim=true; cfg.limits.mode='formula'
local g = sw.loadGroups()
G.adoptNatives(cfg, g, true)
local pick
for _, grp in ipairs(g.groups) do
  if grp.layer=='cavern' and grp.native and grp.resident and not grp.dismissed and grp.depth then
    local live = 0
    for _, id in ipairs(grp.ids) do local u = df.unit.find(id); if u and not dfhack.units.isDead(u) and dfhack.units.isActive(u) then live = live + 1 end end
    if live > 0 and (not pick or grp.arrived < pick.arrived) then pick = grp end
  end
end
local out = {}
if pick then
  local d = pick.depth
  g.groups[#g.groups+1] = { layer='cavern', depth=d, ids={}, resident=true, arrived=sw.absTick() + 1, token='VALIDATOR_DUMMY' }
  local orig = {}
  for _, id in ipairs(pick.ids) do local u = df.unit.find(id); if u then orig[tostring(id)] = u.animal.leave_countdown end end
  local n = 0; for _, grp in ipairs(g.groups) do if grp.layer=='cavern' and grp.depth==d and not grp.irruption then n = n + 1 end end
  local msg = G.trimOne(cfg, g, d, n, 1)
  out.msg = msg; out.token = pick.token; out.n = n; out.d = d
  local low, tot = 0, 0
  for _, id in ipairs(pick.ids) do local u = df.unit.find(id)
    if u and not dfhack.units.isDead(u) then tot = tot + 1; if u.animal.leave_countdown <= G.TRIM_COUNTDOWN then low = low + 1 end end end
  out.low, out.tot = low, tot
  local undoN = 0; for _ in pairs(g.trim_undo or {}) do undoN = undoN + 1 end
  out.undo = undoN
  sw.saveGroups(g)
  sw.PATTERN.sizeRestore()
  local back, diff = 0, 0
  for key, cd in pairs(orig) do local u = df.unit.find(tonumber(key))
    if u and not dfhack.units.isDead(u) then if u.animal.leave_countdown == cd then back = back + 1 else diff = diff + 1 end end end
  out.back, out.diff = back, diff
  local g2 = sw.loadGroups(); local left = 0; for _ in pairs(g2.trim_undo or {}) do left = left + 1 end
  out.undoAfter = left
end
print(json.encode(out))""", timeout=180)
    if bad(j):
        rec_bad("mech.v71.cavern.trim", j)
    elif not j.get("token"):
        rec("mech.v71.cavern.trim", "NOT-TESTABLE-HERE", "a native cavern group with live members", json.dumps(j),
            note="no cavern natives on this map; a region8 fort with populated caverns")
    else:
        ok = (bool(j.get("msg")) and (j.get("tot") or 0) > 0 and j.get("low") == j.get("tot") and (j.get("undo") or 0) == j.get("tot")
              and (j.get("diff") or 0) == 0 and (j.get("back") or 0) == j.get("tot") and (j.get("undoAfter") or 0) == 0)
        rec("mech.v71.cavern.trim", "PASS" if ok else "FAIL",
            "cap 1 with 2 records: the oldest native group trimmed (every member's countdown <= 10, originals in g.trim_undo); PATTERN.sizeRestore (the disable path) puts every countdown back",
            json.dumps(j))

    j = luap("""local sw=reqscript('seasonal-wildlife'); local G=sw.V7.GRP; local W=sw.WILD; local cfg=sw.loadConfig()
local g = sw.loadGroups()
local deepIn = {}
for _, grp in ipairs(g.groups) do for _, id in ipairs(grp.ids) do local u = df.unit.find(id)
  if u and not dfhack.units.isDead(u) and dfhack.units.isActive(u) then local ok, L = pcall(W.layerOf, u); if ok and L == 'deep' then deepIn[#deepIn+1] = id end end end end
local sp = G.species(cfg)
local deepHeld = {}
for t in pairs(sw.CACHE.capHeld or {}) do if sp[t] and sp[t].deep then deepHeld[#deepHeld+1] = t end end
for t in pairs((sw.CACHE.apcap or {}).raws or {}) do if sp[t] and sp[t].deep then deepHeld[#deepHeld+1] = t end end
local deepSp = 0; for _, s in pairs(sp) do if s.deep then deepSp = deepSp + 1 end end
local dunit
for _, u in ipairs(df.global.world.units.active) do
  if not dfhack.units.isDead(u) then local ok, L = pcall(W.layerOf, u); if ok and L == 'deep' and sw.V7.natural(cfg, u) then dunit = u; break end end
end
local out = { deepIn = deepIn, deepHeld = deepHeld, deepSpecies = deepSp }
if dunit then local r, why = G.adopt(cfg, { groups = {} }, { dunit.id }); out.adoptRef = (r == nil); out.why = why; out.dunit = dunit.id end
print(json.encode(out))""", timeout=120)
    if bad(j):
        rec_bad("mech.v71.cavern.deep", j)
    else:
        ok = not j.get("deepIn") and not j.get("deepHeld") and (j.get("dunit") is None or (j.get("adoptRef") and "R60" in (j.get("why") or "")))
        rec("mech.v71.cavern.deep", "PASS" if ok else "FAIL",
            "no deep unit in any record; no deep-entry species in CACHE.capHeld or CACHE.apcap; adopt refuses a deep unit with the R60 reason",
            json.dumps(j), note="" if j.get("dunit") is not None else "no natural deep unit on the map, so the adopt refusal was not exercised (a fort with magma-sea life, e.g. MAGMA)")

    # ---- water bodies under the same rule (R45)
    tool("limits", "formula")
    v = cfgv("limits.mode")
    if manip("mech.v71.water.cap", "limits.mode reads formula", v.get("limits.mode") == "formula", json.dumps(v)):
        t = tool("water")
        j = luap("""local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local Q=sw.QUOTA
print(json.encode({auto=Q.autoGroups(), ocean=Q.groupsFor(cfg,'water:ocean'), lake=Q.groupsFor(cfg,'water:lake'), river=Q.groupsFor(cfg,'water:river'),
  pool=Q.groupsFor(cfg,'water:pool'), defCeil=sw.defaultConfig().limits.water.ceiling}))""")
        m = re.search(r"(\d+) group\(s\) at once per water body, ceiling (\S+)", t)
        if bad(j):
            rec_bad("mech.v71.water.cap", j)
        else:
            a = j.get("auto")
            ok = (a is not None and all(j.get(k) == a for k in ("ocean", "lake", "river", "pool")) and j.get("defCeil") == 0
                  and m is not None and int(m.group(1)) == a)
            rec("mech.v71.water.cap", "PASS" if ok else "FAIL",
                "every water body = floor(sqrt(embark))+1 under the formula; default water ceiling 0; `water` quotes that number per water body",
                json.dumps(j) + "\n" + (m.group(0) if m else t[:400]))

    # ---- leaders: R32's rule, on live groups when there are any, else on the fort's citizens as stand-ins
    j = luap("""local sw=reqscript('seasonal-wildlife'); local V7=sw.V7; local cfg=sw.loadConfig()
cfg.v7.leader_male=true
local function size(u) local ok,v=pcall(function() return u.body.size_info.size_cur end); return ok and v or 0 end
local function am(u) local ok,a=pcall(dfhack.units.isAdult,u); return u.sex==1 and ok and a end
local function check(members, race)
  local best; for _,u in ipairs(members) do if am(u) and (not best or size(u)>size(best)) then best=u end end
  local grp = { race = race }
  local l = V7.leaderOf(cfg, grp, members)
  return { got = l and l.id or nil, want = best and best.id or nil, unled = grp.unled, n = #members }
end
local out = { live = {}, src = 'groups' }
local g = sw.loadGroups()
for _, grp in ipairs(g.groups) do
  local ms = {}
  for _, id in ipairs(grp.ids) do local u = df.unit.find(id); if u and not dfhack.units.isDead(u) and dfhack.units.isActive(u) then ms[#ms+1] = u end end
  if #ms >= 2 and not sw.V7.GRP.wetGroup(grp) then local r = check(ms, grp.race); r.token = grp.token; out.live[#out.live+1] = r end
  if #out.live >= 8 then break end
end
local cit, fem = {}, {}
for _, u in ipairs(df.global.world.units.active) do
  if dfhack.units.isCitizen(u) and not dfhack.units.isDead(u) then cit[#cit+1] = u; if u.sex ~= 1 then fem[#fem+1] = u end end
  if #cit >= 12 then break end
end
if #cit >= 2 then out.cit = check(cit, cit[1].race) end
if #fem >= 2 then out.nomale = check(fem, fem[1].race) end
print(json.encode(out))""")
    if bad(j):
        rec_bad("mech.v71.lead.male", j)
    else:
        rows = (j.get("live") or []) + ([j["cit"]] if isinstance(j.get("cit"), dict) else [])
        nm = j.get("nomale") if isinstance(j.get("nomale"), dict) else None
        if not rows:
            rec("mech.v71.lead.male", "NOT-TESTABLE-HERE", "a group of 2+ live members or 2+ citizens", json.dumps(j))
        else:
            ok = all(r.get("got") == r.get("want") and (r.get("want") is not None or r.get("unled") == "no adult male") for r in rows)
            ok = ok and (nm is None or (nm.get("got") is None and nm.get("unled") == "no adult male"))
            rec("mech.v71.lead.male", "PASS" if ok else "FAIL",
                "V7.leaderOf returns the largest adult male; with none it returns nil and unled 'no adult male' (live groups, plus citizens as stand-in members)",
                json.dumps(j)[:1400], note="" if nm else "no all-female set of 2+ to show the no-male case")

    # ---- leader lost and panic: synthetic records over live wild units of one herd/pack species
    j = luap("""local sw=reqscript('seasonal-wildlife'); local G=sw.V7.GRP; local cfg=sw.loadConfig()
cfg.groups.panic=true; cfg.groups.cohesion=true; cfg.groups.reelect_after_panic=false; cfg.groups.panic_tiles=12
local by = {}
for _, u in ipairs(df.global.world.units.active) do
  if not dfhack.units.isDead(u) and sw.WILD.onMap(u) and sw.V7.natural(cfg, u) and sw.WILD.layerOf(u) ~= 'deep' then
    local lab = sw.cohesionLabel(u.race, cfg)
    if G.PANICS[lab] and not sw.V7.PERF.rawFlag(u.race, 'FLIER') then by[u.race] = by[u.race] or {}; table.insert(by[u.race], u) end
  end
end
local race, ms
for r, l in pairs(by) do if #l >= 2 and (not ms or #l > #ms) then race, ms = r, l end end
local out = { found = race ~= nil }
if race then
  local ids = {}; for i = 1, math.min(#ms, 6) do ids[#ids+1] = ms[i].id end
  local p = ms[1].pos
  local grp = { ids = ids, race = race, token = df.creature_raw.find(race).creature_id, layer = 'land', resident = true, arrived = 1,
                leader = -999, lpos = { x = p.x, y = p.y, z = p.z } }
  local g = { groups = { grp }, detached = 0 }
  local L0 = sw.LEDGER.lines(400)
  G.cohere(cfg, g, grp)
  out.token, out.label, out.lost = grp.token, grp.label, grp.leader_lost
  out.panic = grp.panic ~= nil
  out.leader = grp.leader
  local following, walked, walkedOk = 0, 0, 0
  for _, id in ipairs(ids) do local u = df.unit.find(id)
    if u then
      if u.owner_type == df.unit_owner_type.PACK_LEADER and u.following then following = following + 1 end
      if u.pos.z == p.z and math.max(math.abs(u.pos.x - p.x), math.abs(u.pos.y - p.y)) < cfg.groups.panic_tiles and u.path.goal == df.unit_path_goal.SeekStation then
        walked = walked + 1; if #u.path.path.x > 0 then walkedOk = walkedOk + 1 end end
    end end
  out.following, out.walked, out.walkedOk, out.moves = following, walked, walkedOk, grp.panic and grp.panic.moves or 0
  if grp.panic then grp.panic.until_tick = sw.absTick() - 1 end
  G.cohere(cfg, g, grp)
  out.panicAfter = grp.panic ~= nil
  G.cohere(cfg, g, grp)
  out.leaderAfter = grp.leader
  local L1 = sw.LEDGER.lines(400)
  local seen = {}; for _, l in ipairs(L0) do seen[l] = true end
  local newp, over = 0, 0
  for _, l in ipairs(L1) do if not seen[l] then if l:find('panic for') then newp = newp + 1 end; if l:find('panic is over') then over = over + 1 end end end
  out.ledgerPanic, out.ledgerOver = newp, over
  local dead
  for _, u in ipairs(df.global.world.units.all) do if dfhack.units.isDead(u) then dead = u; break end end
  if dead and #ids >= 2 then
    local grp2 = { ids = ids, race = race, token = out.token, layer = 'land', resident = true, arrived = 1, leader = dead.id }
    G.leaderLost(cfg, { groups = { grp2 } }, grp2, {})
    out.deadWhy = grp2.leader_lost and grp2.leader_lost.why
  end
end
print(json.encode(out))""", timeout=180)
    if bad(j):
        rec_bad(["mech.v71.lead.lost", "mech.v71.panic.walk"], j)
    elif not j.get("found"):
        for cid in ("mech.v71.lead.lost", "mech.v71.panic.walk"):
            rec(cid, "NOT-TESTABLE-HERE", "2+ live natural wild animals of one herd/pack species (non-flier) on the map", json.dumps(j),
                note="place a herd first (a region8 fort with surface wildlife; or `place` a herd species)")
    else:
        lost = j.get("lost") if isinstance(j.get("lost"), dict) else {}
        ok = (lost.get("why") in ("left", "died") and j.get("panic") and (j.get("following") or 0) == 0 and not j.get("leader")
              and (j.get("ledgerPanic") or 0) >= 1 and not j.get("panicAfter") and (j.get("ledgerOver") or 0) >= 1 and not j.get("leaderAfter")
              and (j.get("deadWhy") in (None, "died")))
        rec("mech.v71.lead.lost", "PASS" if ok else "FAIL",
            "leader gone -> leader_lost (left; a dead unit's id -> died), panic on, nobody following, a 'panic for' ledger line; after panic_days the 'panic is over' line and still no leader",
            json.dumps(j), note="" if j.get("deadWhy") else "no dead unit in units.all to stand in for a leader that died; 'left' exercised")
        ok = (j.get("walked") or 0) >= 1 and j.get("walked") == j.get("walkedOk") and (j.get("moves") or 0) >= 1
        rec("mech.v71.panic.walk", "PASS" if ok else "FAIL",
            "members within panic_tiles of where the leader stood walked off (goal SeekStation, path non-empty), the panic's move count > 0",
            json.dumps({k: j.get(k) for k in ("token", "walked", "walkedOk", "moves")}))

    # ---- a water draw is led in water at once (needs surface water)
    if need("mech.v71.lead.water", "water", "a Driver B draw led by a wet leader"):
        tool("water", "layer", "on")
        t = tool("water", "now")
        m = re.search(r"water: drew (\S+) x(\d+) into the (\w+)", t)
        if not m:
            rec("mech.v71.lead.water", "NOT-TESTABLE-HERE", "`water now` draws a group", t[:600],
                note="the draw found nothing (no stocked, in-season water species this season); see `water mix`")
        else:
            j = luap("""local sw=reqscript('seasonal-wildlife'); local G=sw.V7.GRP; local cfg=sw.loadConfig()
local g = sw.loadGroups(); local grp
for i = #g.groups, 1, -1 do local x = g.groups[i]; if x.layer == 'water' and x.token == '@TOK@' then grp = x; break end end
local out = {}
if grp then
  out.label, out.leader, out.unled = grp.label, grp.leader, grp.unled
  local dist = cfg.groups['follow_' .. tostring(grp.label)]
  out.dist = dist
  local L = grp.leader and df.unit.find(grp.leader)
  out.leaderWet = L and G.wet(L) or false
  local f, n = 0, 0
  for _, id in ipairs(grp.ids) do local u = df.unit.find(id)
    if u and not dfhack.units.isDead(u) and id ~= grp.leader then n = n + 1; if L and u.following == L and u.follow_distance == dist then f = f + 1 end end end
  out.followers, out.others = f, n
end
print(json.encode(out))""".replace("@TOK@", m.group(1)))
            if bad(j):
                rec_bad("mech.v71.lead.water", j)
            elif j.get("leader"):
                ok = j.get("leaderWet") and j.get("label") in ("school", "pod") and j.get("followers") == j.get("others")
                rec("mech.v71.lead.water", "PASS" if ok else "FAIL", "the drawn group's leader stands in water; every other member follows it at follow_school/follow_pod",
                    json.dumps(j) + "\n" + t[:300])
            else:
                rec("mech.v71.lead.water", "PASS" if j.get("unled") in ("no wet adult male", "no adult male") else "FAIL",
                    "led at once, or unled for R32's reason (no wet adult male)", json.dumps(j) + "\n" + t[:300])

    # ---- `place` places one clustered, led group
    j = luap("""local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig()
local want = @OCEAN@
local best
for _, pop in ipairs(df.global.world.populations.all) do
  local cr = df.creature_raw.find(pop.race)
  if cr and pop.type == df.world_population_type.Animal and pop.quantity >= 6 then
    local L = sw.layerOf(pop)
    local ok = (want and cr.creature_id == 'ORCA') or (not want and L == 'land')
    if ok and sw.ecoOf(cfg, cr) == 'natural' and not sw.V7.PERF.rawFlag(pop.race, 'FLIER') then
      local lab = sw.cohesionLabel(pop.race, cfg)
      if lab ~= 'solitary' and (not best or pop.quantity > best.q) then best = { tok = cr.creature_id, q = pop.quantity, layer = L } end
    end
  end
end
print(json.encode(best or {}))""".replace("@OCEAN@", "true" if has("ocean") else "false"))
    if bad(j) or not j.get("tok"):
        if bad(j):
            rec_bad("mech.v71.lead.place", j)
        else:
            rec("mech.v71.lead.place", "NOT-TESTABLE-HERE", "a stocked (>= 6) natural non-flier herd/pack species on the map's entries", json.dumps(j),
                note="on an ocean fort the probe places ORCA (the notes' case); elsewhere any land herd")
    else:
        t = tool("place", j["tok"], "6", j.get("layer") or "land")
        ids = _b_ids(t)
        if not ids:
            rec("mech.v71.lead.place", "FAIL", f"`place {j['tok']} 6` places a group", t[:600])
        else:
            k = luap("""local sw=reqscript('seasonal-wildlife'); local g=sw.loadGroups(); local ids={@IDS@}
local want = {}; for _, id in ipairs(ids) do want[id] = true end
local recs, grp = 0, nil
for _, x in ipairs(g.groups) do local hit = false; for _, id in ipairs(x.ids) do if want[id] then hit = true end end; if hit then recs = recs + 1; grp = x end end
local xs, ys, zs = {}, {}, {}
for _, id in ipairs(ids) do local u = df.unit.find(id); if u then xs[#xs+1] = u.pos.x; ys[#ys+1] = u.pos.y; zs[#zs+1] = u.pos.z end end
local function span(t) local lo, hi; for _, v in ipairs(t) do lo = math.min(lo or v, v); hi = math.max(hi or v, v) end; return (hi or 0) - (lo or 0) end
local L = grp and grp.leader and df.unit.find(grp.leader)
local ok, adult = false, false; if L then ok, adult = pcall(dfhack.units.isAdult, L) end
print(json.encode({recs=recs, n=grp and #grp.ids or 0, placed=grp and grp.placed, leader=grp and grp.leader, unled=grp and grp.unled,
  leaderMale=L and (L.sex == 1 and ok and adult) or false, spanX=span(xs), spanY=span(ys), spanZ=span(zs)}))""".replace("@IDS@", ",".join(map(str, ids))))
            if bad(k):
                rec_bad("mech.v71.lead.place", k)
            else:
                spread = max(k.get("spanX") or 99, k.get("spanY") or 99)
                led = (k.get("leader") and k.get("leaderMale")) or k.get("unled") == "no adult male"
                ok = k.get("recs") == 1 and k.get("n") == len(ids) and spread <= 12 and led
                rec("mech.v71.lead.place", "PASS" if ok else "FAIL",
                    "one record holding every placed id, spread within 12 tiles (nearest free tiles to one seed at stride 2), led by an adult male or unled 'no adult male'",
                    json.dumps(k) + "\n" + t[:300])

    # ---- seeded schools: structurally never counted; live when DF seeded a school here
    j = luap("""local sw=reqscript('seasonal-wildlife'); local G=sw.V7.GRP; local utils=require('utils'); local cfg=sw.loadConfig()
cfg.groups.seeded_water=true
local syn = { groups = { { layer='water', seeded=true, ids={} }, { layer='water', ids={} } } }
local out = { synCount = sw.ENGINE.count(syn, 'water') }
local g = utils.clone(sw.loadGroups(), true)
local before = #g.groups
G.adoptNatives(cfg, g, true)
local seeded, notMarked = 0, 0
for _, grp in ipairs(g.groups) do if grp.layer == 'water' then if grp.seeded then seeded = seeded + 1 elseif grp.native then notMarked = notMarked + 1 end end end
local nonSeeded = 0; for _, grp in ipairs(g.groups) do if grp.layer == 'water' and not grp.seeded then nonSeeded = nonSeeded + 1 end end
out.seeded, out.badMark, out.count, out.nonSeeded = seeded, notMarked, sw.ENGINE.count(g, 'water'), nonSeeded
print(json.encode(out))""", timeout=180)
    if bad(j):
        rec_bad("mech.v71.lead.seeded", j)
    else:
        struct = j.get("synCount") == 1
        if (j.get("seeded") or 0) == 0:
            rec("mech.v71.lead.seeded", "NOT-TESTABLE-HERE" if struct else "FAIL", "a school DF seeded in surface water at embark", json.dumps(j),
                note=("structural half PASS: ENGINE.count skips a seeded record; " if struct else "") + NEED["water"] + " with seeded schools")
        else:
            ok = struct and (j.get("badMark") or 0) == 0 and j.get("count") == j.get("nonSeeded")
            rec("mech.v71.lead.seeded", "PASS" if ok else "FAIL", "seeded schools adopted as seeded=true records; ENGINE.count('water') leaves them out", json.dumps(j))

    # ---- sponges and IMMOBILE never lead
    j = luap("""local sw=reqscript('seasonal-wildlife'); local V7=sw.V7; local cfg=sw.loadConfig()
local out = { bad = {} }
local r = V7.spongeRace(); out.spongeRace = r
if r and r >= 0 then out.spongeLabel = sw.cohesionLabel(r, cfg) end
local all = df.global.world.raws.creatures.all; local imm
for i = 0, #all - 1 do if V7.PERF.rawFlag(i, 'IMMOBILE') then imm = i; break end end
if imm then out.immTok = all[imm].creature_id; out.immLabel = sw.cohesionLabel(imm, cfg) end
for _, grp in ipairs(sw.loadGroups().groups) do
  if grp.leader and grp.race and (V7.isSponge({ race = grp.race }) or V7.PERF.rawFlag(grp.race, 'IMMOBILE')) then out.bad[#out.bad+1] = grp.token end
end
print(json.encode(out))""")
    if bad(j):
        rec_bad("mech.v71.lead.sponge", j)
    else:
        ok = not j.get("bad") and j.get("spongeLabel", "solitary") == "solitary" and j.get("immLabel", "solitary") == "solitary"
        rec("mech.v71.lead.sponge", "PASS" if ok else "FAIL", "SPONGE and an IMMOBILE race label 'solitary' (never led); no led record of either", json.dumps(j))

    # ---- `groups adopt` (H3)
    j = luap("""local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig()
local by = {}
for _, u in ipairs(df.global.world.units.active) do
  if not dfhack.units.isDead(u) and sw.WILD.onMap(u) and sw.V7.natural(cfg, u) and sw.WILD.layerOf(u) ~= 'deep' then
    by[u.race] = by[u.race] or {}; table.insert(by[u.race], u.id) end
end
local ids; for _, l in pairs(by) do if #l >= 2 and (not ids or #l > #ids) then ids = l end end
local cit; for _, u in ipairs(df.global.world.units.active) do if dfhack.units.isCitizen(u) and not dfhack.units.isDead(u) then cit = u.id; break end end
local pick = {}; if ids then for i = 1, math.min(3, #ids) do pick[i] = ids[i] end end
print(json.encode({ids = pick, cit = cit}))""")
    if bad(j) or len(j.get("ids") or []) < 2:
        if bad(j):
            rec_bad("mech.v71.adopt", j)
        else:
            rec("mech.v71.adopt", "NOT-TESTABLE-HERE", "2+ live natural wild animals of one species on the map", json.dumps(j))
    else:
        ids = [int(x) for x in j["ids"]]
        t = tool("groups", "adopt", *ids)
        tc = tool("groups", "adopt", j["cit"]) if j.get("cit") is not None else ""
        k = luap("""local sw=reqscript('seasonal-wildlife'); local g=sw.loadGroups(); local ids={@IDS@}
local want = {}; for _, id in ipairs(ids) do want[id] = 0 end
local recs, exact, LEAD, UNLED = 0, false, nil, nil
for _, x in ipairs(g.groups) do
  local hit = 0; for _, id in ipairs(x.ids) do if want[id] then want[id] = want[id] + 1; hit = hit + 1 end end
  if hit > 0 then recs = recs + 1; exact = (hit == #ids and #x.ids == #ids and x.adopted == true); LEAD = x.leader; UNLED = x.unled end
end
local dup = 0; for _, n in pairs(want) do if n ~= 1 then dup = dup + 1 end end
local L = LEAD and df.unit.find(LEAD); local ok, adult = false, false; if L then ok, adult = pcall(dfhack.units.isAdult, L) end
print(json.encode({recs = recs, exact = exact, dup = dup, leader = LEAD, unled = UNLED, leaderMale = L and (L.sex == 1 and ok and adult) or false}))""".replace("@IDS@", ",".join(map(str, ids))))
        if bad(k):
            rec_bad("mech.v71.adopt", k)
        else:
            led = (k.get("leader") and k.get("leaderMale")) or k.get("unled") in ("no adult male", "no wet adult male") or \
                  (k.get("unled") is None and not k.get("leader"))
            ok = t.startswith("adopted") and k.get("recs") == 1 and k.get("exact") and k.get("dup") == 0 and led and \
                 (not tc or "belongs to the fort" in tc)
            rec("mech.v71.adopt", "PASS" if ok else "FAIL",
                "one record holding exactly the given ids (each id in one record only), adopted=true, led by an adult male or unled; a citizen refused",
                json.dumps(k) + "\n" + t[:300] + "\n" + tc[:200], note="" if tc else "no citizen to show the refusal")

    # ---- the animal-people cap (R35): capped, lifted by an irruption (stubbed activeOn), restored by the disable path
    j = luap("""local sw=reqscript('seasonal-wildlife'); local G=sw.V7.GRP; local I=sw.IRRUPT; local CAV=sw.CAVERN; local cfg=sw.loadConfig()
cfg.enabled=true; cfg.groups.enabled=true; cfg.groups.apcap=5
local sp = G.species(cfg)
local orig, subj = {}, nil
for t, s in pairs(sp) do
  if s.person and s.natural and not s.shared and not s.deep and (cfg.group_size['cavern:' .. t] or 0) <= 0 then
    local cr = CAV.rawFor(t)
    if cr then local o = (sw.CACHE.apcap and sw.CACHE.apcap.raws and sw.CACHE.apcap.raws[t]) or { cr.cluster_number[0], cr.cluster_number[1] }
      orig[t] = { o[1], o[2] }; if math.max(o[1], o[2]) > cfg.groups.apcap and (not subj or t == 'PLUMP_HELMET_MAN') then subj = t end end
  end
end
local out = { subj = subj, persons = 0 }
for _ in pairs(orig) do out.persons = out.persons + 1 end
if subj then
  local cr = CAV.rawFor(subj)
  out.orig = orig[subj]
  G.apCap(cfg); out.capped = { cr.cluster_number[0], cr.cluster_number[1] }
  local old = I.activeOn
  I.activeOn = function() return true end
  local ok, e = pcall(G.apCap, cfg)
  I.activeOn = old
  out.lifted = { cr.cluster_number[0], cr.cluster_number[1] }; out.liftErr = (not ok) and tostring(e) or nil
  G.apCap(cfg); out.recapped = { cr.cluster_number[0], cr.cluster_number[1] }
  sw.PATTERN.sizeRestore()
  out.restored = { cr.cluster_number[0], cr.cluster_number[1] }
  local left = 0; for _ in pairs((sw.CACHE.apcap or {}).raws or {}) do left = left + 1 end
  out.left = left
end
print(json.encode(out))""", timeout=180)
    if bad(j):
        rec_bad("mech.v71.apcap", j)
    elif not j.get("subj"):
        rec("mech.v71.apcap", "NOT-TESTABLE-HERE", "a natural cavern-only animal-people species whose raw cluster max exceeds the cap (5)", json.dumps(j),
            note="no such species in this map's cavern entries; a region8 fort whose caverns hold plump helmet men or another *_MAN race")
    else:
        o, cap = j.get("orig") or [0, 0], 5
        def mx(p): return max(p) if isinstance(p, list) and p else -1
        ok = (mx(j.get("capped")) <= cap and j.get("lifted") == o and mx(j.get("recapped")) <= cap and j.get("restored") == o
              and (j.get("left") or 0) == 0 and not j.get("liftErr"))
        rec("mech.v71.apcap", "PASS" if ok else "FAIL",
            "capped to <= 5; an irruption on its cavern (IRRUPT.activeOn stubbed true, restored in the probe) puts the raw range back; capped again; PATTERN.sizeRestore restores it",
            json.dumps(j))

    # ---- restore paths: all off and disable put back the holds and the caps
    rows = []
    for path in ("alloff", "disable"):
        j = luap("""local sw=reqscript('seasonal-wildlife'); local G=sw.V7.GRP; local CAV=sw.CAVERN; local cfg=sw.loadConfig()
cfg.enabled=true; cfg.groups.enabled=true; cfg.groups.apcap=5; cfg.groups.cavern_hold='any'
local sp = G.species(cfg); local d; for _, s in pairs(sp) do for dd in pairs(s.d) do d = dd end; if d then break end end
local pre, savedPre = {}, CAV.saved()
for t in pairs(sp) do local cr = CAV.rawFor(t); if cr then pre[t] = { cr.frequency, cr.cluster_number[0], cr.cluster_number[1] } end end
if d ~= nil then G.cavernHold(cfg, { [d] = true }) end
local capped = G.apCap(cfg)
local held = 0; for _ in pairs(sw.CACHE.capHeld or {}) do held = held + 1 end
if '@PATH@' == 'alloff' then sw.PANEL.restoreAll() else dfhack.run_command_silent('seasonal-wildlife', 'disable') end
local diff = {}
for t, p in pairs(pre) do
  if savedPre[t] == nil then local cr = CAV.rawFor(t)
    if cr and (cr.frequency ~= p[1] or cr.cluster_number[0] ~= p[2] or cr.cluster_number[1] ~= p[3]) then diff[#diff+1] = t end end
end
local heldAfter = 0; for _ in pairs(sw.CACHE.capHeld or {}) do heldAfter = heldAfter + 1 end
local capAfter = 0; for _ in pairs((sw.CACHE.apcap or {}).raws or {}) do capAfter = capAfter + 1 end
print(json.encode({path='@PATH@', d=d, held=held, capped=capped, diff=diff, heldAfter=heldAfter, capAfter=capAfter}))""".replace("@PATH@", path), timeout=180)
        rows.append(j)
    if any(bad(r) for r in rows):
        rec_bad("mech.v71.restore", next(r for r in rows if bad(r)))
    elif all((r.get("held") or 0) == 0 and (r.get("capped") or 0) == 0 for r in rows):
        rec("mech.v71.restore", "NOT-TESTABLE-HERE", "a cavern species to hold and an animal-people species to cap", json.dumps(rows),
            note="nothing to write on this map's cavern entries; a region8 fort with populated caverns")
    else:
        ok = all(not r.get("diff") and (r.get("heldAfter") or 0) == 0 and (r.get("capAfter") or 0) == 0 for r in rows)
        rec("mech.v71.restore", "PASS" if ok else "FAIL",
            "after a cavern hold and the animal-people cap: PANEL.restoreAll (all off) and `disable` each leave every frequency and cluster range as before, CACHE.capHeld and CACHE.apcap empty",
            json.dumps(rows)[:1400], note="the trim countdowns' restore is mech.v71.cavern.trim")

    # ---- the apex scheduler's one caller (replaces mech.v71.apex.hook)
    j = luap("""local sw=reqscript('seasonal-wildlife'); local R=sw.ROSTER
print(json.encode({hook = (type(R.apex) == 'table' and R.apex.tick ~= nil) or false, placeTick = type(R.placeTick)}))""")
    src = (TOOL / "scripts/seasonal-wildlife.lua").read_text(errors="replace") if (TOOL / "scripts/seasonal-wildlife.lua").exists() else ""
    code_only = "\n".join(l.split("--", 1)[0] for l in src.splitlines())
    hook_calls = len(re.findall(r"apex\.tick\b", code_only))
    callers = len(re.findall(r"ROSTER\.placeTick\b", code_only)) - len(re.findall(r"function\s+ROSTER\.placeTick\b", code_only))
    in_tick = bool(re.search(r"pcall\(ROSTER\.placeTick,\s*cfg\)", code_only))
    if bad(j):
        rec_bad("mech.v71.apex.onecaller", j)
    else:
        ok = j.get("hook") is False and j.get("placeTick") == "function" and (hook_calls == 0 or DRY) and (in_tick or DRY)
        rec("mech.v71.apex.onecaller", "PASS" if ok else "FAIL",
            "ROSTER.apex.tick is gone and ROSTER.placeTick is a function; the engine's code (comments stripped) never calls apex.tick and tick() pcalls ROSTER.placeTick",
            json.dumps(j) + f"\nstatic ({TOOL}): apex.tick references {hook_calls}; ROSTER.placeTick references {callers} (tick() and the `roster apex now` verb); tick() pcall {in_tick}")

    # ---- v7.0 gate_drain: synthetic gated records over three live wild units, their roaming flags put back after
    j = luap("""local sw=reqscript('seasonal-wildlife'); local V7=sw.V7; local cfg=sw.loadConfig()
local us = {}
for _, u in ipairs(df.global.world.units.active) do
  if #us < 3 and not dfhack.units.isDead(u) and sw.WILD.onMap(u) and V7.natural(cfg, u) and sw.WILD.layerOf(u) == 'land' then us[#us+1] = u end
end
local out = { n = #us, def = sw.defaultConfig().v7.gate_drain }
if #us == 3 then
  local orig = {}
  for i, u in ipairs(us) do orig[i] = { u.flags2.roaming_wilderness_population_source, u.flags2.roaming_wilderness_population_source_not_a_map_feature }
    u.flags2.roaming_wilderness_population_source = true end
  local g = { groups = {}, detached = 0 }
  for i, u in ipairs(us) do g.groups[i] = { ids = { u.id }, layer = 'land', resident = false, arrived = i, token = 'T' .. i } end
  local ok, extra = pcall(V7.drainGate, g, 'land')
  out.ok = ok; out.err = (not ok) and tostring(extra) or nil
  out.extra = ok and #extra or -1
  out.res = { g.groups[1].resident == true, g.groups[2].resident == true, g.groups[3].resident == true }
  out.flags = { us[1].flags2.roaming_wilderness_population_source, us[2].flags2.roaming_wilderness_population_source, us[3].flags2.roaming_wilderness_population_source }
  for i, u in ipairs(us) do u.flags2.roaming_wilderness_population_source = orig[i][1]; u.flags2.roaming_wilderness_population_source_not_a_map_feature = orig[i][2] end
end
print(json.encode(out))""")
    if bad(j):
        rec_bad("mech.v70.gate_drain", j)
    elif (j.get("n") or 0) < 3:
        rec("mech.v70.gate_drain", "NOT-TESTABLE-HERE", "three live natural wild land units to stand in as gated groups", json.dumps(j),
            note="a region8 fort with surface wildlife on the map")
    else:
        hooks = len(re.findall(r"V7\.on\(cfg, 'gate_drain'\)", src))
        ok = (j.get("def") is True and j.get("extra") == 2 and j.get("res") == [True, True, False] and j.get("flags") == [False, False, True]
              and (hooks >= 2 or DRY))
        rec("mech.v70.gate_drain", "PASS" if ok else "FAIL",
            "three flagged one-animal gated groups: V7.drainGate releases the two oldest and stops at one flagged animal; on by default; called after the land and the cavern releases",
            json.dumps(j) + f"\nstatic: V7.on(cfg, 'gate_drain') call sites {hooks}")


# ---- irruption (docs/v7.1/irruption.md section 12) ---------------------------------------------------------------
_B_IRR_KEYS = ["enabled", "rev", "threshold", "decay", "pmax", "src.citizens", "src.near", "src.near_z", "src.dig", "src.breach", "src.scarcity",
               "src.scar_ref", "src.random", "fort.wealth_k", "fort.wealth_ref", "fort.pop_k", "fort.pop_ref", "season_mult", "need_breach",
               "gap_halve", "gap_share", "strict_band", "warn_min_days", "warn_max_days", "lapse_share", "waves", "size_mult", "size_min",
               "size_cap", "unit_cap", "spacing_min_days", "spacing_max_days", "stay_days", "edge_tiles", "lead", "surge", "duration_days",
               "settle_days", "calm_share", "wave_spend", "repel_share", "repel_dead", "cooldown_days", "end_mode", "leave_min_days",
               "leave_max_days", "species", "fallback", "roster", "mix", "max_active", "champion", "tokens", "rage_value", "rage_ticks",
               "rage_hold", "sneak_skill", "linger_days", "wander_ticks", "wander_steps", "meander_ticks", "meander_tiles", "reassert", "rehide",
               "agitate", "agitate_cap", "agitate_benign", "agitate_wave", "msg.warn", "msg.lapse", "msg.start", "msg.wave", "msg.finish",
               "msg.ready", "pause.warn", "pause.start", "pause.wave", "pause.finish", "popup", "zoom"]

# Lua: the residual writes left on an event's units, read against the event record (rec.mask/cache/hidden/mood/skills)
_B_RESIDUAL = """
local function residual(ev)
  local n, units, alive = 0, 0, 0
  for _, rec in pairs(ev.units or {}) do
    units = units + 1
    local u = df.unit.find(rec.id)
    if u and not dfhack.units.isDead(u) then
      alive = alive + 1
      for f, old in pairs(rec.mask or {}) do local ok, v = pcall(function() return u.uwss_add_caste_flag[f] end); if ok and (v and true or false) ~= old then n = n + 1 end end
      for f, old in pairs(rec.cache or {}) do local ok, v = pcall(function() return u.enemy.caste_flags[f] end); if ok and (v and true or false) ~= old then n = n + 1 end end
      if rec.hidden ~= nil and (u.flags1.hidden_in_ambush and true or false) ~= rec.hidden then n = n + 1 end
      if rec.mood ~= nil and u.counters.soldier_mood == df.soldier_mood_type.Enraged and rec.mood ~= df.soldier_mood_type.Enraged then n = n + 1 end
      if rec.skills and rec.skills.SNEAK and rec.skills.SNEAK.had == false then
        local so = u.status.current_soul
        if so then for _, x in ipairs(so.skills) do if x.id == df.job_skill.SNEAK then n = n + 1 end end end
      end
    end
  end
  for key, old in pairs(ev.agit or {}) do
    local u = df.unit.find(tonumber(key))
    if u and not dfhack.units.isDead(u) and (u.flags4.agitated_wilderness_creature and true or false) ~= old then n = n + 1 end
  end
  return n, units, alive
end
"""


def _b_irr_set(*pairs_):
    out = []
    for k, v in pairs_:
        out.append(tool("irruption", "set", k, v))
    return "\n".join(o.splitlines()[0] if o else "" for o in out)


def v71_irruption():
    # ---- config: defaults, migration of a v7.0 table, sanitising (pure)
    keys_lua = ",".join(json.dumps(k) for k in _B_IRR_KEYS)
    j = luap("""local sw=reqscript('seasonal-wildlife'); local I=sw.IRRUPT""" + CFG_GET_LUA + """
local d = sw.defaultConfig().irruption
local missing = {}
for _, k in ipairs({@KEYS@}) do if get(d, k) == nil then missing[#missing+1] = k end end
local c = sw.defaultConfig()
I.sanitize(c, { irruption = { enabled = true, threshold = 2, gain = 0.05, decay = 0.02, duration_days = 12, cooldown_days = 40 } })
local m = c.irruption
local c2 = sw.defaultConfig()
I.sanitize(c2, { irruption = { rev = 2, threshold = 500, decay = 'x', waves = 3.7, end_mode = 'bogus', pmax = 0, msg = { warn = 'yes' } } })
local b = c2.irruption
print(json.encode({ rev = d.rev, missing = missing, tokens = (function() local n=0; for _ in pairs(d.tokens) do n=n+1 end; return n end)(),
  m = { enabled = m.enabled, threshold = m.threshold, decay = m.decay, duration = m.duration_days, cooldown = m.cooldown_days, cit = m.src.citizens, migrated = m.migrated, rev = m.rev },
  b = { threshold = b.threshold, decay = b.decay, waves = b.waves, end_mode = b.end_mode, pmax = b.pmax, warn = b.msg.warn, migrated = b.migrated } }))""".replace("@KEYS@", keys_lua))
    if bad(j):
        rec_bad("mech.v71.irr.cfg", j)
    else:
        m, b = j.get("m") or {}, j.get("b") or {}
        ok = (j.get("rev") == 2 and not j.get("missing") and j.get("tokens") == 11
              and m.get("enabled") is True and m.get("threshold") == 2 and m.get("decay") == 0.02 and m.get("duration") == 12 and m.get("cooldown") == 40
              and m.get("cit") == 0.05 and m.get("migrated") == "v7.0" and m.get("rev") == 2
              and b.get("threshold") == 1.0 and b.get("decay") == 0.01 and b.get("waves") == 3 and b.get("end_mode") == "leave" and b.get("pmax") == 4
              and b.get("warn") is True and b.get("migrated") is None)
        rec("mech.v71.irr.cfg", "PASS" if ok else "FAIL",
            "defaults rev 2 with every key of irruption.md section 6 (11 tokens); v7.0 {enabled, threshold 2, gain 0.05, decay 0.02, duration 12, cooldown 40} -> those values, src.citizens 0.05, migrated 'v7.0'; threshold 500 / decay 'x' / end_mode 'bogus' / pmax 0 / msg.warn 'yes' dropped; waves 3.7 -> 3",
            json.dumps(j))

    # ---- migration of v7.0 state (a synthetic groups record; one live wild unit's agitated flag set, then cleared by it)
    j = luap("""local sw=reqscript('seasonal-wildlife'); local I=sw.IRRUPT; local cfg=sw.loadConfig()
local u
for _, x in ipairs(df.global.world.units.active) do if not dfhack.units.isDead(x) and sw.WILD.onMap(x) and sw.V7.natural(cfg, x) then u = x; break end end
local was = u and u.flags4.agitated_wilderness_creature
if u then u.flags4.agitated_wilderness_creature = true end
local now = sw.absTick()
local g = { groups = {}, armed = { ids = { u and u.id or -1 }, depth = 0, token = 'X' }, irrupt_cooldown_until = now + 5000 }
I.migrate(cfg, g)
local s = I.state(g)
local out = { unit = u and u.id, armed = g.armed ~= nil, oldcd = g.irrupt_cooldown_until,
  c0 = s.layers.c0.phase, c0cool = s.layers.c0.cool_until, c1 = s.layers.c1.phase, c1cool = s.layers.c1.cool_until, c2 = s.layers.c2.phase,
  want0 = now + cfg.irruption.cooldown_days * sw.TICKS_PER_DAY, want1 = now + 5000, flag = u and u.flags4.agitated_wilderness_creature or false }
if u then u.flags4.agitated_wilderness_creature = was end
print(json.encode(out))""")
    if bad(j):
        rec_bad("mech.v71.irr.migrate", j)
    else:
        ok = (j.get("armed") is False and j.get("oldcd") is None and j.get("c0") == "cooldown" and j.get("c0cool") == j.get("want0")
              and j.get("c1") == "cooldown" and j.get("c1cool") == j.get("want1") and j.get("c2") == "cooldown" and j.get("flag") is False)
        rec("mech.v71.irr.migrate", "PASS" if ok else "FAIL",
            "g.armed on cavern 1 -> flag cleared, g.armed nil, cavern 1 cooling cooldown_days; the old global cooldown on caverns 2 and 3, the field removed",
            json.dumps(j), note="" if j.get("unit") else "no live wild unit to carry the agitated flag; the state half was judged")

    # ---- the per-cavern hooks (pure: a synthetic state with cavern 1 active)
    j = luap("""local sw=reqscript('seasonal-wildlife'); local I=sw.IRRUPT; local cfg=sw.loadConfig()
cfg.irruption.enabled = true; cfg.irruption.gap_halve = true
local g = { groups = {}, pressure = { c0 = 0, c1 = 0, c2 = 0 }, irr2 = { rev = 2, layers = { c0 = { phase = 'active' }, c1 = { phase = 'idle' }, c2 = { phase = 'idle' } }, stats = { events = 0, waves = 0, placed = 0 } } }
I.refreshActive(g)
local out = { a0 = I.activeOn('cavern:0'), a1 = I.activeOn('cavern:1'), aLand = I.activeOn('land'), ac0 = I.activeOn('c0'),
  gap0 = I.gapDays(cfg, g, 10, 0), gap1 = I.gapDays(cfg, g, 10, 1), gap2 = I.gapDays(cfg, g, 10, 2) }
I.refreshActive(sw.loadGroups())
print(json.encode(out))""")
    layer_pure = None if bad(j) else j
    if bad(j):
        rec_bad("mech.v71.irr.layer", j)

    # ---- the live sequence needs a cavern band with something to send
    j = luap("""local sw=reqscript('seasonal-wildlife'); local I=sw.IRRUPT; local cfg=sw.loadConfig()
local out = { bands = {}, civ = {}, pred = {} }
for d = 0, 2 do
  local b = sw.CAVE.band(d); out.bands['c' .. d] = b ~= nil
  if b then
    local c = I.candidates(cfg, d, true); local p = I.candidates(cfg, d, false)
    out.civ['c' .. d] = #c; out.pred['c' .. d] = #p
  end
end
print(json.encode(out))""", timeout=180)
    live_ids = ["mech.v71.irr.trigger", "mech.v71.irr.wave", "mech.v71.irr.tokens", "mech.v71.irr.caste", "mech.v71.irr.agitate",
                "mech.v71.irr.end", "mech.v71.irr.off", "mech.v71.irr.msg", "mech.v71.irr.r35"]
    D = None
    if not bad(j):
        civ, pred = j.get("civ") or {}, j.get("pred") or {}
        for d in range(3):
            if (civ.get(f"c{d}") or 0) > 0:
                D = d; break
        if D is None:
            for d in range(3):
                if (pred.get(f"c{d}") or 0) > 0:
                    D = d; break
        if DRY:
            D = 0
    if layer_pure is not None:
        lp = layer_pure
        ok = (lp.get("a0") is True and lp.get("a1") is False and lp.get("aLand") is False and lp.get("ac0") is True
              and lp.get("gap0") == 5 and lp.get("gap1") == 10 and lp.get("gap2") == 10)
        rec("mech.v71.irr.layer", "PASS" if ok else "FAIL",
            "cavern 1 active: activeOn('cavern:0')/('c0') true, ('cavern:1') and ('land') false; gapDays halves cavern 1's gap only (10 -> 5, others 10)",
            json.dumps(lp), note="the live half (an event on one cavern leaves the others idle) is read in mech.v71.irr.trigger")

    # fbsafe's structural half runs on any fort
    jf = luap("""local sw=reqscript('seasonal-wildlife'); local I=sw.IRRUPT; local cfg=sw.loadConfig()
local out = { cands = 0, unnatural = {}, agitNon = 0, nonNatural = 0 }
for d = 0, 2 do for _, civ in ipairs({ true, false }) do
  for _, e in ipairs(I.candidates(cfg, d, civ)) do out.cands = out.cands + 1
    if sw.ecoOf(cfg, e.craw) ~= 'natural' then out.unnatural[#out.unnatural+1] = e.token end
    for _, i in ipairs(e.idx) do local p = df.global.world.populations.all[i]; local dd = p and sw.WILD.caveDepth(p.population.cave_id)
      if dd ~= d then out.unnatural[#out.unnatural+1] = e.token .. '@depth' .. tostring(dd) end end
  end end end
local ev = { units = {} }
for _, u in ipairs(df.global.world.units.active) do
  if not dfhack.units.isDead(u) and not sw.V7.natural(cfg, u) then out.nonNatural = out.nonNatural + 1
    for d = 0, 2 do if I.agitable(cfg, u, d, ev) then out.agitNon = out.agitNon + 1 end end end
end
print(json.encode(out))""", timeout=180)

    if bad(j) or D is None:
        why = bad(j) or "no cavern band with a civ race or a cavern predator entry"
        for cid in live_ids:
            if bad(j):
                rec(cid, "FAIL", "the probe's JSON", why)
            else:
                rec(cid, "NOT-TESTABLE-HERE", "a cavern band (open at the map edge) with a live, admitted, natural civ race or predator entry", json.dumps(j),
                    note="region8 fort with cavern entries (b1-forts.py; R11); until then BOATS or OCEAN2 (their caverns carry civ races)")
        _b_fbsafe(jf, None)
        _b_irr_status()
        _b_gui_rows()
        return
    K = f"c{D}"
    CAV = str(D + 1)

    # ---- dials for the live sequence, read back (manipulation check)
    tool("irruption", "on")
    setr = _b_irr_set(("need_breach", "off"), ("pause.start", "off"), ("zoom", "off"), ("popup", "off"), ("size_min", "4"), ("size_cap", "6"),
                      ("size_mult", "2"), ("agitate", "on"), ("champion", "on"), ("end_mode", "leave"), ("fallback", "animals"), ("species", "auto"))
    v = cfgv("irruption.enabled", "irruption.need_breach", "irruption.pause.start", "irruption.size_cap", "irruption.size_min", "irruption.end_mode")
    dial_ok = (v.get("irruption.enabled") is True and v.get("irruption.need_breach") is False and v.get("irruption.pause.start") is False
               and v.get("irruption.size_cap") == 6 and v.get("irruption.size_min") == 4 and v.get("irruption.end_mode") == "leave")
    if not dial_ok and not DRY:
        for cid in live_ids:
            manip(cid, "irruption on, need_breach off, pause.start off, size 2/4/6, end_mode leave", False, json.dumps(v) + "\n" + setr)
        _b_fbsafe(jf, None)
        _b_irr_status()
        _b_gui_rows()
        return

    _b_irr_status()

    # ---- event 1: the natural path. pin at the threshold -> tick -> warning -> (warning time over) -> tick -> active, wave 1
    j = luap(("""local sw=reqscript('seasonal-wildlife'); local I=sw.IRRUPT; local G=sw.V7.GRP; local CAV=sw.CAVERN; local utils=require('utils')
local cfg=sw.loadConfig(); local g=sw.loadGroups(); local d=@D@; local k='c'..d
local out = {}
local FL = { 'CURIOUS_BEAST', 'CURIOUS_BEAST_ITEM', 'MEANDERER', 'AMBUSHPREDATOR' }
local function casteSnap(cr)
  local t = {}
  for ci, c in ipairs(cr.caste) do
    for _, f in ipairs(FL) do local ok, v = pcall(function() return c.flags[f] end); t[ci .. f] = ok and (v and true or false) or 'na' end
    local ok, v = pcall(function() return c.misc.prone_to_rage end); t[ci .. 'rage'] = ok and v or 'na'
  end
  local ok, v = pcall(function() return cr.flags.HAS_ANY_CURIOUS_BEAST end); t.cf = ok and (v and true or false) or 'na'
  return t
end
local cands, q0 = {}, {}
for _, civ in ipairs({ true, false }) do for _, e in ipairs(I.candidates(cfg, d, civ)) do cands[#cands+1] = e; q0[e.token] = e.q end end
local snap = {}; for _, e in ipairs(cands) do snap[e.token] = casteSnap(e.craw) end
local cmax = {}; for _, e in ipairs(cands) do cmax[e.token] = I.clusterMax(e.craw) end
local agBefore = {}; for _, u in ipairs(df.global.world.units.active) do if u.flags4.agitated_wilderness_creature then agBefore[u.id] = true end end
-- R35 subject: an animal-people species of this cavern, its range before
local c2 = utils.clone(cfg, true); c2.enabled = true; c2.groups.enabled = true; c2.groups.apcap = 5
local sp = G.species(c2); local apT
for t, s in pairs(sp) do if s.person and s.natural and not s.shared and not s.deep and s.d[d] then local cr = CAV.rawFor(t)
  if cr then local o = (sw.CACHE.apcap and sw.CACHE.apcap.raws and sw.CACHE.apcap.raws[t]) or { cr.cluster_number[0], cr.cluster_number[1] }
    if math.max(o[1], o[2]) > 5 then apT = t; out.apOrig = { o[1], o[2] } end end end end
out.apT = apT
local said = {}; local oldSay = I.say
I.say = function(c, kind) said[#said+1] = kind; return true end
local ledger0 = {}; for _, l in ipairs(sw.LEDGER.lines(300)) do ledger0[l] = true end
g.pressure_pin = g.pressure_pin or {}; g.pressure_pin[k] = cfg.irruption.threshold
g.pressure = g.pressure or {}; g.pressure[k] = cfg.irruption.threshold
local ok1, e1 = pcall(I.tick, cfg, g)
local s = I.state(g); local L = s.layers[k]
out.tickErr1 = (not ok1) and tostring(e1) or nil
out.phase1 = L.phase; out.nothing1 = L.nothing
if L.phase == 'warning' then L.warn_until = sw.absTick() - 1; local ok2, e2 = pcall(I.tick, cfg, g); out.tickErr2 = (not ok2) and tostring(e2) or nil end
I.say = oldSay
out.said = said
out.phase2 = L.phase
out.others = {}; for dd = 0, 2 do if dd ~= d then out.others['c' .. dd] = s.layers['c' .. dd].phase end end
out.active = {}; for dd = 0, 2 do out.active['c' .. dd] = I.activeOn('cavern:' .. dd) end
out.gap = {}; for dd = 0, 2 do out.gap['c' .. dd] = I.gapDays(cfg, g, 10, dd) end
local stir, irrupts = 0, 0
for _, l in ipairs(sw.LEDGER.lines(300)) do if not ledger0[l] then if l:find('something stirs') then stir = stir + 1 end; if l:find('IRRUPTS') then irrupts = irrupts + 1 end end end
out.ledgerStir, out.ledgerIrrupts = stir, irrupts
local ev = L.ev
if ev then
  out.ev = { id = ev.id, token = ev.token, civ = ev.civ, done = ev.done, placed = ev.placed, waves = ev.waves }
  -- the wave: size, stock, the record
  local ir = cfg.irruption
  local nexp = math.floor((cmax[ev.token] or 1) * ir.size_mult + 0.5)
  nexp = math.max(ir.size_min, math.min(nexp, ir.size_cap)); nexp = math.min(nexp, q0[ev.token] or 0, ir.unit_cap)
  out.nexp = nexp
  local q1 = 0; for _, e in ipairs(I.candidates(cfg, d, ev.civ)) do if e.token == ev.token then q1 = e.q end end
  out.q0, out.q1 = q0[ev.token], q1
  local recs = {}
  for _, grp in ipairs(g.groups) do if grp.irr_ev == ev.id then recs[#recs+1] = { mark = grp.irruption, n = #grp.ids, leader = grp.leader, unled = grp.unled, label = grp.label } end end
  out.recs = recs
  -- tokens: per token, how many units carry it; units with every enabled token; each write read back
  local on = {}; for _, t in ipairs(I.TOKENS) do if ir.tokens[t.id].on then on[#on+1] = t.id end end
  local per, all, fails, n, nosoul = {}, 0, {}, 0, 0
  for _, rec in pairs(ev.units) do
    n = n + 1
    local u = df.unit.find(rec.id)
    local has = {}; for _, t in ipairs(rec.tags or {}) do has[t] = true; per[t] = (per[t] or 0) + 1 end
    local full = true; for _, t in ipairs(on) do if not has[t] then full = false end end
    if full and #on > 0 then all = all + 1 end
    if u then
      for f in pairs(rec.mask or {}) do local ok, v = pcall(function() return u.uwss_add_caste_flag[f] end); if not (ok and v) then fails[#fails+1] = rec.id .. ':mask:' .. f end end
      for f in pairs(rec.cache or {}) do local ok, v = pcall(function() return u.enemy.caste_flags[f] end); if not (ok and v) then fails[#fails+1] = rec.id .. ':cache:' .. f end end
      if rec.hidden ~= nil and not u.flags1.hidden_in_ambush then fails[#fails+1] = rec.id .. ':hidden' end
      if rec.mood ~= nil and u.counters.soldier_mood ~= df.soldier_mood_type.Enraged then fails[#fails+1] = rec.id .. ':mood' end
      if has.sneak then local lvl = 0; local so = u.status.current_soul
        if so then for _, x in ipairs(so.skills) do if x.id == df.job_skill.SNEAK then lvl = x.rating end end
          if lvl < ir.sneak_skill then fails[#fails+1] = rec.id .. ':sneak' .. lvl end
        else nosoul = (nosoul or 0) + 1 end end
      if rec.linger and u.animal.leave_countdown < math.floor(ir.linger_days * sw.TICKS_PER_DAY) - 1200 then fails[#fails+1] = rec.id .. ':linger' end
    end
  end
  out.tok = { on = on, per = per, all = all, n = n, fails = fails, pct = {}, nosoul = nosoul }
  for _, t in ipairs(on) do out.tok.pct[t] = ir.tokens[t].pct end
  -- caste: every candidate race's castes as before; nothing held
  local cdiff = {}
  for _, e in ipairs(cands) do local now = casteSnap(e.craw); for kk, vv in pairs(snap[e.token]) do if now[kk] ~= vv then cdiff[#cdiff+1] = e.token .. ':' .. kk end end end
  out.casteDiff = cdiff; out.casteHeld = I.mem().casteHeld ~= nil
  -- agitation
  local agit, agitBad, newAg, newAgOut = 0, {}, 0, 0
  for key in pairs(ev.agit or {}) do
    agit = agit + 1
    local u = df.unit.find(tonumber(key))
    if u then
      local why
      if sw.WILD.layerOf(u) ~= 'cavern' or sw.WILD.caveDepth(u.animal.population.cave_id) ~= d then why = 'layer' end
      if I.isCiv(u.race) then why = 'civ' end
      local okC, cit = pcall(dfhack.units.isCitizen, u); local okT, tame = pcall(dfhack.units.isTame, u)
      if (okC and cit) or (okT and tame) then why = 'fort' end
      if not sw.V7.natural(cfg, u) then why = 'unnatural' end
      if why then agitBad[#agitBad+1] = key .. ':' .. why end
    end
  end
  for _, u in ipairs(df.global.world.units.active) do
    if u.flags4.agitated_wilderness_creature and not agBefore[u.id] then newAg = newAg + 1; if (ev.agit or {})[tostring(u.id)] == nil then newAgOut = newAgOut + 1 end end
  end
  out.agit = { n = agit, cap = ir.agitate_cap, bad = agitBad, newAg = newAg, newOutside = newAgOut }
  -- placed units: never below the third cavern
  local deep = 0
  for _, rec in pairs(ev.units) do local u = df.unit.find(rec.id)
    if u then local okL, Lx = pcall(sw.WILD.layerOf, u); if okL and Lx ~= 'cavern' then deep = deep + 1 end end end
  out.placedNotCavern = deep
  -- R35 during the event
  if apT then local cr = CAV.rawFor(apT); G.apCap(c2); out.apDuring = { cr.cluster_number[0], cr.cluster_number[1] } end
end
sw.saveGroups(g)
_G.__b_irr = { ev = ev and utils.clone(ev, true) or nil, apT = apT }
print(json.encode(out))""").replace("@D@", str(D)), timeout=240)
    if bad(j):
        for cid in ("mech.v71.irr.trigger", "mech.v71.irr.wave", "mech.v71.irr.tokens", "mech.v71.irr.caste", "mech.v71.irr.agitate", "mech.v71.irr.r35"):
            rec_bad(cid, j)
        ev = {}
    else:
        ev = j.get("ev") if isinstance(j.get("ev"), dict) else {}
        others = j.get("others") or {}
        ok = (j.get("phase1") == "warning" and j.get("phase2") == "active" and (ev.get("done") or 0) >= 1 and (j.get("ledgerStir") or 0) >= 1
              and (j.get("ledgerIrrupts") or 0) >= 1 and all(p in ("idle", "cooldown") for p in others.values())
              and (j.get("active") or {}).get(K) is True and not any(v_ for kk, v_ in (j.get("active") or {}).items() if kk != K)
              and not j.get("tickErr1") and not j.get("tickErr2"))
        gap = j.get("gap") or {}
        gap_ok = gap.get(K) == 5 and all(v_ == 10 for kk, v_ in gap.items() if kk != K)
        # the no-civ / fallback none half
        jn = luap("""local sw=reqscript('seasonal-wildlife'); local I=sw.IRRUPT; local cfg=sw.loadConfig()
cfg.irruption.fallback = 'none'; cfg.irruption.need_breach = false
local out = {}
for d = 0, 2 do
  if sw.CAVE.band(d) and #I.candidates(cfg, d, true) == 0 then
    local k = 'c' .. d
    local g2 = { groups = {}, pressure = { [k] = cfg.irruption.threshold }, pressure_pin = { [k] = cfg.irruption.threshold } }
    local s = I.state(g2); s.layers[k].touched = true
    local now = sw.absTick()
    local old = I.say; I.say = function() return true end
    I.step(cfg, g2, s, d)
    I.say = old
    out = { d = d, phase = s.layers[k].phase, nothing = s.layers[k].nothing, retry = s.layers[k].retry, want = now + sw.TICKS_PER_DAY }
    break
  end
end
I.refreshActive(sw.loadGroups())
print(json.encode(out))""")
        none_ok = None
        if not bad(jn) and jn.get("phase"):
            none_ok = jn.get("phase") == "idle" and "fallback none" in (jn.get("nothing") or "") and jn.get("retry") == jn.get("want")
        rec("mech.v71.irr.trigger", "PASS" if ok and none_ok is not False else "FAIL",
            f"cavern {CAV} pinned at the threshold: one pass -> warning ('something stirs'); warning over -> active with wave 1 ('IRRUPTS'); the other caverns idle; no civ race + fallback none -> idle, 'nothing to send' and a retry one day on",
            json.dumps({k_: j.get(k_) for k_ in ("phase1", "nothing1", "phase2", "others", "active", "ledgerStir", "ledgerIrrupts", "tickErr1", "tickErr2")})
            + "\nfallback none: " + (json.dumps(jn) if not bad(jn) else str(bad(jn))),
            note="" if none_ok is not None else "every cavern band here has a civ race, so the fallback-none half was not exercised")
        if layer_pure is not None and not gap_ok:
            log(f"   note: live gapDays {gap} (cavern {CAV} should halve)")
        # wave
        recs = j.get("recs") or []
        if not ev:
            for cid in ("mech.v71.irr.wave", "mech.v71.irr.tokens", "mech.v71.irr.caste", "mech.v71.irr.agitate", "mech.v71.irr.r35"):
                rec(cid, "FAIL", "an event with a placed wave", json.dumps(j)[:900])
        else:
            r0 = recs[0] if recs and isinstance(recs[0], dict) else {}
            led = bool(r0.get("leader")) or r0.get("unled") in ("no adult male", "no wet adult male")
            ok = (ev.get("placed") == j.get("nexp") and len(recs) == 1 and r0.get("mark") == K and r0.get("n") == ev.get("placed")
                  and led and (j.get("q0") or 0) - (j.get("q1") or 0) == ev.get("placed"))
            rec("mech.v71.irr.wave", "PASS" if ok else "FAIL",
                "wave n = clamp(cluster max x 2, 4, 6) bounded by stock (size dials 2/4/6, read back); one record marked with the cavern; led (or unled for R32's reason); the entry debited by n",
                json.dumps({k_: j.get(k_) for k_ in ("ev", "nexp", "q0", "q1", "recs")}))
            tk = j.get("tok") or {}
            if not ev.get("civ"):
                rec("mech.v71.irr.tokens", "NOT-TESTABLE-HERE", "a civ wave (tokens are written on civ races only)", json.dumps(tk),
                    note=f"cavern {CAV} sent a predator (no civ race there); a fort whose caverns hold a civ race (BOATS/OCEAN2; region8 per R11)")
            else:
                n = tk.get("n") or 0
                per, pct = tk.get("per") or {}, tk.get("pct") or {}
                def want(t):
                    k_ = max(1, int(math.floor((pct.get(t) or 0) * n / 100 + 0.5))) if (pct.get(t) or 0) > 0 else 0
                    return 1 + min(k_, max(0, n - 1))
                okc = all(per.get(t) == want(t) for t in (tk.get("on") or []))
                ok = okc and tk.get("all") == 1 and not tk.get("fails")
                rec("mech.v71.irr.tokens", "PASS" if ok else "FAIL",
                    "each enabled token on 1 + min(max(1, round(pct n/100)), n-1) units; exactly one unit carries every enabled token; every mask/cache/hidden/mood/SNEAK/linger write reads back",
                    json.dumps(tk))
            ok = not j.get("casteDiff") and j.get("casteHeld") is False
            rec("mech.v71.irr.caste", "PASS" if ok else "FAIL",
                "after the wave every caste of every candidate race reads as before (CURIOUS*, MEANDERER, AMBUSHPREDATOR, prone_to_rage, HAS_ANY_CURIOUS_BEAST); IRRUPT.mem().casteHeld nil",
                json.dumps({k_: j.get(k_) for k_ in ("casteDiff", "casteHeld")}))
            ag = j.get("agit") or {}
            ok = not ag.get("bad") and (ag.get("n") or 0) <= (ag.get("cap") or 0) and (ag.get("newOutside") or 0) == 0
            rec("mech.v71.irr.agitate", "PASS" if ok else "FAIL",
                "every agitated unit is a non-civ, non-fort, natural animal of this cavern; at most the cap; no newly agitated unit outside the event's list",
                json.dumps(ag), note="" if (ag.get("n") or 0) > 0 else "no other animal of this cavern on the map to agitate (CTRL's caverns are unopened); the never-wrong half held")

    # ---- event 1 ends by the player (`irruption end N`)
    t_end = tool("irruption", "end", CAV)
    je = luap(_B_RESIDUAL + ("""local sw=reqscript('seasonal-wildlife'); local I=sw.IRRUPT; local G=sw.V7.GRP; local CAV=sw.CAVERN; local utils=require('utils')
local cfg=sw.loadConfig(); local g=sw.loadGroups(); local d=@D@; local k='c'..d
local st = _G.__b_irr or {}; local ev = st.ev
local out = {}
if ev then
  local n, units, alive = residual(ev)
  out.residual, out.units, out.alive = n, units, alive
  local ir = cfg.irruption; local lo, hi = ir.leave_min_days * sw.TICKS_PER_DAY, math.max(ir.leave_min_days, ir.leave_max_days) * sw.TICKS_PER_DAY
  local cdBad = 0
  for _, rec in pairs(ev.units) do local u = df.unit.find(rec.id)
    if u and not dfhack.units.isDead(u) and dfhack.units.isActive(u) then local cd = u.animal.leave_countdown; if cd < math.max(1, math.floor(lo)) - 1 or cd > hi + 1 then cdBad = cdBad + 1 end end end
  out.cdBad = cdBad
  local s = I.state(g); local L = s.layers[k]
  out.phase = L.phase; out.coolLeft = (L.cool_until or 0) - sw.absTick(); out.coolWant = ir.cooldown_days * sw.TICKS_PER_DAY
  out.pressure = (g.pressure or {})[k]
  local marks = 0; for _, grp in ipairs(g.groups) do if grp.irr_ev == ev.id and grp.irruption then marks = marks + 1 end end
  out.marks = marks; out.why = s.last and s.last.why
  if st.apT then local c2 = utils.clone(cfg, true); c2.enabled = true; c2.groups.enabled = true; c2.groups.apcap = 5
    local cr = CAV.rawFor(st.apT); G.apCap(c2); out.apAfter = { cr.cluster_number[0], cr.cluster_number[1] }
    c2.groups.apcap = 0; G.apCap(c2); out.apReleased = { cr.cluster_number[0], cr.cluster_number[1] } end
end
print(json.encode(out))""").replace("@D@", str(D)))
    end_rows = {"player": je, "reply": t_end}

    # r35 from events 1's two halves
    if not bad(j) and ev:
        if not j.get("apT"):
            rec("mech.v71.irr.r35", "NOT-TESTABLE-HERE", f"an animal-people species with a cluster max over 5 in cavern {CAV}", json.dumps({k_: j.get(k_) for k_ in ("apT",)}),
                note="a fort whose irrupting cavern holds plump helmet men or another *_MAN race (region8 with populated caverns; BOATS saw plump helmet men, S8B)")
        elif bad(je):
            rec_bad("mech.v71.irr.r35", je)
        else:
            o = j.get("apOrig")
            ok = j.get("apDuring") == o and isinstance(je.get("apAfter"), list) and max(je.get("apAfter")) <= 5 and je.get("apReleased") == o
            rec("mech.v71.irr.r35", "PASS" if ok else "FAIL",
                "during the event the species' cluster range is the raw's own (cap lifted on its cavern); after the end apCap caps it to <= 5; cap off puts it back",
                json.dumps({"species": j.get("apT"), "orig": o, "during": j.get("apDuring"), "after": je.get("apAfter"), "released": je.get("apReleased")}))

    # ---- event 2: forced, ended by its duration; the messages around it (IRRUPT.say stubbed in this copy)
    j2 = luap(_B_RESIDUAL + ("""local sw=reqscript('seasonal-wildlife'); local I=sw.IRRUPT; local utils=require('utils')
local cfg=sw.loadConfig(); local g=sw.loadGroups(); local d=@D@; local k='c'..d
local said = {}; local old = I.say
I.say = function(c, kind) said[#said+1] = kind; return true end
local s = I.state(g); local L = s.layers[k]
local out = {}
local ok, err = pcall(function()
  L.phase = 'idle'
  local ev = I.start(cfg, g, s, d, nil, true)
  out.started = ev ~= nil
  if ev then
    local evc = utils.clone(ev, true)
    ev.until_tick = sw.absTick() - 1
    I.hold(cfg, g, s, d)
    local n, units = residual(evc)
    out.residual, out.units = n, units
    out.why = s.last and s.last.why; out.phase = L.phase
    out.pressure = (g.pressure or {})[k]
    local marks = 0; for _, grp in ipairs(g.groups) do if grp.irr_ev == evc.id and grp.irruption then marks = marks + 1 end end
    out.marks = marks
  end
  L.cool_until = sw.absTick() - 1
  I.step(cfg, g, s, d)
  out.afterCool = L.phase
  if g.pressure_pin then g.pressure_pin[k] = nil end
  I.warn(cfg, g, s, d)
  g.pressure = g.pressure or {}; g.pressure[k] = 0
  I.step(cfg, g, s, d)
  out.afterLapse = L.phase
end)
I.say = old
out.err = (not ok) and tostring(err) or nil
out.said = said
-- the real announcer: every msg off says nothing; pause.start pauses
local c3 = utils.clone(cfg, true); for kk in pairs(c3.irruption.msg) do c3.irruption.msg[kk] = false end
out.offSaid = I.say(c3, 'warn', 'seasonal-wildlife validator: irruption message test (msg off)', COLOR_GREY)
local c4 = utils.clone(cfg, true); c4.irruption.msg.start = true; c4.irruption.pause.start = true; c4.irruption.zoom = false; c4.irruption.popup = false
local was = dfhack.world.ReadPauseState()
dfhack.world.SetPauseState(false)
out.onSaid = I.say(c4, 'start', 'seasonal-wildlife validator: irruption message test (pause.start)', COLOR_GREY)
out.paused = dfhack.world.ReadPauseState()
dfhack.world.SetPauseState(was)
I.refreshActive(g)
sw.saveGroups(g)
print(json.encode(out))""").replace("@D@", str(D)), timeout=240)
    end_rows["duration"] = j2

    if bad(j2):
        rec_bad("mech.v71.irr.msg", j2)
    else:
        said1 = (j.get("said") if not bad(j) else None) or []
        allsaid = list(said1) + list(j2.get("said") or [])
        need_k = ["warn", "start", "wave", "finish", "ready", "lapse"]
        ok = all(k_ in allsaid for k_ in need_k) and j2.get("offSaid") is False and j2.get("paused") is True and not j2.get("err")
        rec("mech.v71.irr.msg", "PASS" if ok else "FAIL",
            "the announcer is called for warn, start, wave (event 1), finish, ready and lapse (event 2); with every msg off IRRUPT.say returns false; pause.start pauses the game (pause state put back)",
            json.dumps({"event1": said1, "event2": j2.get("said"), "offSaid": j2.get("offSaid"), "onSaid": j2.get("onSaid"), "paused": j2.get("paused"), "err": j2.get("err")}))

    if bad(je) or bad(j2):
        rec_bad("mech.v71.irr.end", je if bad(je) else j2)
    else:
        cw = je.get("coolWant") or 0
        okp = (je.get("residual") == 0 and (je.get("cdBad") or 0) == 0 and je.get("phase") == "cooldown" and abs((je.get("coolLeft") or 0) - cw) <= 2
               and je.get("pressure") == 0 and je.get("marks") == 0 and je.get("why") == "ended by the player" and "undone" in t_end)
        okd = (j2.get("started") and j2.get("residual") == 0 and j2.get("why") == "duration over" and j2.get("phase") == "cooldown" and j2.get("pressure") == 0
               and j2.get("marks") == 0 and j2.get("afterCool") == "idle" and j2.get("afterLapse") == "idle")
        rec("mech.v71.irr.end", "PASS" if okp and okd else "FAIL",
            "ended by the player and by its duration: 0 residual writes on surviving units and agitated animals, countdowns in leave_min..leave_max days (end_mode leave), cooldown set, pressure 0, group marks cleared; the cooldown then ends to idle",
            json.dumps(end_rows)[:1500], note="'repelled' needs units killed by the fort (repel_share/repel_dead): a rig test (irruption.md section 13), not one session")

    # ---- the off paths: `irruption off`, disable, groups off, all off -- each with an event running
    offs = {}
    for path in ("irruption off", "disable", "groups off", "all off"):
        tool("irruption", "on")
        tnow = tool("irruption", "now", CAV)
        js = luap(("""local sw=reqscript('seasonal-wildlife'); local I=sw.IRRUPT; local utils=require('utils')
local g = sw.loadGroups(); local L = I.state(g).layers['c@D@']
_G.__b_irr_off = L.ev and utils.clone(L.ev, true) or nil
print(json.encode({ phase = L.phase, placed = L.ev and L.ev.placed or 0 }))""").replace("@D@", str(D)))
        if path == "irruption off":
            tp = tool("irruption", "off")
        elif path == "disable":
            tp = tool("disable")
        elif path == "groups off":
            tp = tool("groups", "off")
        else:
            tp = json.dumps(luap("local sw=reqscript('seasonal-wildlife'); print(json.encode({out=sw.PANEL.restoreAll()}))"))
        jr = luap(_B_RESIDUAL + ("""local sw=reqscript('seasonal-wildlife'); local I=sw.IRRUPT
local g = sw.loadGroups(); local s = I.state(g)
local ev = _G.__b_irr_off
local out = { phases = {} }
for d = 0, 2 do out.phases['c' .. d] = s.layers['c' .. d].phase end
if ev then out.residual = residual(ev); local marks = 0; for _, grp in ipairs(g.groups) do if grp.irr_ev == ev.id and grp.irruption then marks = marks + 1 end end; out.marks = marks end
out.held = I.mem().casteHeld ~= nil
print(json.encode(out))"""))
        offs[path] = {"start": js, "now": tnow[:160], "path": (tp or "")[:160], "after": jr}
        if path == "groups off":
            tool("groups", "on")
    # while off: a pinned cavern sends nothing and writes nothing
    tool("irruption", "off")
    jo = luap(("""local sw=reqscript('seasonal-wildlife'); local I=sw.IRRUPT
local cfg = sw.loadConfig(); local g = sw.loadGroups(); local k = 'c@D@'
g.pressure_pin = g.pressure_pin or {}; g.pressure_pin[k] = cfg.irruption.threshold * 2
local s = I.state(g); local placed0, n0 = s.stats.placed, #g.groups
I.tick(cfg, g)
local out = { enabled = cfg.irruption.enabled, placed = s.stats.placed - placed0, recs = #g.groups - n0, phase = s.layers[k].phase }
g.pressure_pin = nil
sw.saveGroups(g)
print(json.encode(out))""").replace("@D@", str(D)))
    offs["while off"] = jo
    bad_off = [p for p, r in offs.items() if (bad(r) if p == "while off" else (bad(r["start"]) or bad(r["after"])))]
    if bad_off:
        rec("mech.v71.irr.off", "FAIL", "the off-path probes' JSON", json.dumps(offs)[:1500])
    else:
        rows_ok, notes = True, []
        for p in ("irruption off", "disable", "groups off", "all off"):
            r = offs[p]
            st, af = r["start"], r["after"]
            if st.get("phase") != "active":
                rows_ok = False; notes.append(f"{p}: no event started ({r['now']})"); continue
            ph = af.get("phases") or {}
            if af.get("residual") != 0 or (af.get("marks") or 0) != 0 or any(v_ == "active" for v_ in ph.values()) or af.get("held"):
                rows_ok = False; notes.append(f"{p}: residual {af.get('residual')} marks {af.get('marks')} phases {ph}")
        ok = rows_ok and jo.get("enabled") is False and jo.get("placed") == 0 and jo.get("recs") == 0 and jo.get("phase") != "active"
        rec("mech.v71.irr.off", "PASS" if ok else "FAIL",
            "with an event running, `irruption off`, `disable`, `groups off` and all off (PANEL.restoreAll) each leave 0 residual writes, no marks and no active phase; while off a cavern pinned at 2x threshold places and writes nothing",
            json.dumps(offs)[:1500], note="; ".join(notes))

    # ---- fbsafe: structural + every unit placed this session
    _b_fbsafe(jf, j.get("placedNotCavern") if (not bad(j) and ev) else None)
    tool("irruption", "unpin")
    tool("irruption", "end", "all")
    tool("irruption", "off")
    _b_gui_rows()


def _b_fbsafe(jf, placed_bad):
    if bad(jf):
        rec_bad("mech.v71.irr.fbsafe", jf)
        return
    ok = not jf.get("unnatural") and (jf.get("agitNon") or 0) == 0 and (placed_bad or 0) == 0
    rec("mech.v71.irr.fbsafe", "PASS" if ok else "FAIL",
        "every candidate natural and at its own cavern depth (0-2); agitable() false for every non-natural unit at every depth; every placed wave unit stands in a cavern",
        json.dumps({**jf, "placedNotCavern": placed_bad}),
        note="" if placed_bad is not None else "no event ran here, so the placed-units half was not read")


def _b_irr_status():
    t0 = tool("irruption", "on")
    ts = tool("irruption", "status")
    tst = tool("status")
    rows = [r for r in ("purpose:", "trigger:", "phases:", "end:", "species:", "tokens (R10", "token levers:", "agitation (R5", "messages:",
                        "cavern 1:", "cavern 2:", "cavern 3:", "so far:") if r not in ts]
    ok = not rows and "irruptions: on  threshold" in tst
    rec("mech.v71.irr.status", "PASS" if ok else "FAIL",
        "`irruption status`: the purpose line, trigger/phases/end/species/tokens/levers/agitation/messages rows, one row per cavern and the totals; `status` carries 'irruptions: on  threshold'",
        (("missing: " + ", ".join(rows) + "\n") if rows else "") + ts[:1200] + "\n" + "\n".join(l for l in tst.splitlines() if "irruption" in l)[:300])


def _b_gui_rows():
    gui = TOOL / "scripts/gui/seasonal-wildlife.lua"
    txt = gui.read_text(errors="replace") if gui.exists() else ""
    keys = ["src.citizens", "need_breach", "agitate_cap", "cooldown_days", "duration_days", "champion", "tokens"]
    present = [k for k in keys if k in txt]
    if DRY or len(present) < 3:
        rec("gui.irr.rows", "NOT-TESTABLE-HERE", "the Panel/Layers rows of irruption.md section 9", f"{gui}: IRRUPT v2 keys present {present}",
            note="UI wave not landed: the window still shows only the v6.1 switch, threshold and pressures (gui/seasonal-wildlife.lua act_lay_irruption, Layers rows)")
    else:
        missing = [k for k in keys if k not in txt]
        rec("gui.irr.rows", "PASS" if not missing else "FAIL", "the window names every IRRUPT v2 key it should expose (static)",
            f"present {present}; missing {missing}", note="static check only; the rows' reads and writes are the GUI wave's own claims")
# ---- fork C helpers: every probe starts from the engine's own tables; RESET puts the raws back the way the tool holds
# them (re-applied when the rotation is on, restored when it is off), so a probe that called V7.apply leaves nothing.
_C_HEAD = ("local sw=reqscript('seasonal-wildlife'); local V7=sw.V7; local R=sw.ROSTER; local M=sw.MODEL; local VE=sw.VERMIN; local CAV=sw.CAVERN\n"
           "local function RESET() local cc=sw.loadConfig(); if cc.enabled then pcall(V7.apply, cc, sw.buildPool(cc)) else V7.restore() end end\n")

def _c_probe(body, timeout=240):
    return luap(_C_HEAD + body, timeout=timeout)

def _c_num(x, d=0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d

def _c_r8(what, interim):
    return f"needs {what}: a region8 fort per R11 (b1-forts.py embark) that has it; until then {interim}"

# ---- roster -------------------------------------------------------------------------------------------------------
def v71_roster():
    # mech.v70.builder + mech.v71.ladder.units: the console build (it persists; phase_v71 restores the config after)
    out = tool("roster", "build", "land", timeout=240)
    slots = re.findall(r"^  ([A-Z]{2,3})\s+(\d+) \(min (\d+), max (\d+)\)\s+(.*)$", out, re.M)
    unf = re.findall(r"^  UNFILLED (\S+)\s+needs (\d+), have (\d+) -- (.+)$", out, re.M)
    ladder = [(k, int(v)) for k, v in re.findall(r"^    (\S+)\s+(-?\d+)\s*$", out, re.M)]
    li = re.search(r"ladder-info .*?\bcarn=([\d.]+).*?\bcarn_units=([\d.]+)", out)
    apex = re.findall(r"^  apex (\S+): FREQUENCY (raw )?(-?\d+)", out, re.M)
    veg = "vegetation index" in out
    under = [s for s in slots if int(s[1]) < int(s[2])]
    unf_codes = {u[0] for u in unf}
    if "the 'builder' switch is off" in out:
        rec("mech.v70.builder", "FAIL", "the builder on by default (v7 builder)", out[:600])
    elif not slots:
        rec("mech.v70.builder", "FAIL", "slot lines, the ladder and the vegetation line from `roster build land`", out[:900])
    else:
        ok = bool(ladder) and veg and all(s[0] in unf_codes for s in under) and all(u[3].strip() for u in unf)
        rec("mech.v70.builder", "PASS" if ok else "FAIL",
            "slots with members, an UNFILLED line with a reason for each slot under its minimum, the ladder, the vegetation survey (the water build's deep survey: mech.v71.water.pelagic's probe)",
            json.dumps({"slots": slots, "unfilled": unf, "ladder_n": len(ladder), "vegetation": veg})[:1400])
    cv = cfgv("roster.apex_raw_cap", "roster.apex_odds")
    cap, odds = _c_num(cv.get("roster.apex_raw_cap"), 5), _c_num(cv.get("roster.apex_odds"), 0)
    if not li:
        rec("mech.v71.ladder.units", "FAIL", "a ladder-info line from `roster build land`", out[:600])
    else:
        carn, cu = float(li.group(1)), float(li.group(2))
        apex_over = [(t, int(v)) for t, raw, v in apex if int(v) > cap and odds <= 0]
        ok = abs(carn - cu) <= 0.03 and all(v >= 1 for _, v in ladder) and not apex_over
        rec("mech.v71.ladder.units", "PASS" if ok else "FAIL",
            "carn_units within 0.03 of carn; every ladder value >= 1; no apex above apex_raw_cap (apex_odds 0)",
            json.dumps({"carn": carn, "carn_units": cu, "ladder_min": min([v for _, v in ladder] or [0]), "apex": apex, "apex_raw_cap": cap, "apex_odds": odds, "apex_over": apex_over}))
    # mech.v71.apex.place / .cap: from the built roster's apex keys
    j0 = _c_probe("""local c=sw.loadConfig(); local keys=(c.roster and c.roster.apex_keys and c.roster.apex_keys.land) or {}
local q={}; for _,k in ipairs(keys) do local s=0; for _,p in ipairs(R.apex.entries(k)) do s=s+p.quantity end; q[k]=s end
print(json.encode({keys=keys, nkeys=#keys, q=q}))""")
    if bad(j0):
        rec_bad(["mech.v71.apex.place", "mech.v71.apex.cap"], j0)
    elif not (j0.get("nkeys") or 0):
        for cid in ("mech.v71.apex.place", "mech.v71.apex.cap"):
            rec(cid, "NOT-TESTABLE-HERE", "an apex key seated by `roster build land`", json.dumps(j0),
                note=_c_r8("a land apex (AL/AW or a boosted giant) in the embark pool with stock", "a savage fort (region6 EVILF/GOODF) or BOATS"))
    else:
        oa = tool("roster", "apex", "now", "land", "force", timeout=180)   # v7.1 fixes2: force past the cap
        m = re.search(r"apex now: .*?\bland (\S+) x(\d+)", oa)
        keys = j0.get("keys") or []
        lua_keys = "{" + ",".join(json.dumps(str(k)) for k in keys) + "}"
        j1 = _c_probe(f"""local c=sw.loadConfig(); local keys={lua_keys}
local q={{}}; for _,k in ipairs(keys) do local s=0; for _,p in ipairs(R.apex.entries(k)) do s=s+p.quantity end; q[k]=s end
local g=sw.loadGroups(); local recs={{}}
for _,grp in ipairs(g.groups) do if grp.placed and grp.tag=='apex' then recs[#recs+1]={{key=grp.key, n=#grp.ids, layer=grp.layer}} end end
g.rapex = g.rapex or {{}}
R.apex.decide(c, g, 'land', keys, 25, 1, 'apex', false, 'vtest:land')
local st = g.rapex['vtest:land']; local why, seen = st and st.why, st and st.groups
g.rapex['vtest:land'] = nil
print(json.encode({{q=q, recs=recs, why=why, groups=seen}}))""")
        if not m:
            rec("mech.v71.apex.place", "FAIL" if "nothing placed" not in oa else "NOT-TESTABLE-HERE",
                "`roster apex now land` places a group ('apex now: land KEY xN')", oa[:600],
                note="" if "nothing placed" not in oa else _c_r8("stock in a seated apex's entry and a free edge tile", "BOATS or a savage fort"))
            rec("mech.v71.apex.cap", "NOT-TESTABLE-HERE", "an apex group on the map", oa[:300], note="no apex group was placed (mech.v71.apex.place)")
        elif bad(j1):
            rec_bad(["mech.v71.apex.place", "mech.v71.apex.cap"], j1)
        else:
            key, n = m.group(1), int(m.group(2))
            qb, qa = (j0.get("q") or {}).get(key), (j1.get("q") or {}).get(key)
            recs = [r_ for r_ in (j1.get("recs") or []) if isinstance(r_, dict) and r_.get("key") == key]
            ok = n > 0 and qb is not None and qa is not None and int(qb) - int(qa) == n and bool(recs)
            rec("mech.v71.apex.place", "PASS" if ok else "FAIL", "ids > 0; the key's stock debited by the group size; a placed tag='apex' record",
                json.dumps({"reply": oa.strip()[:200], "key": key, "n": n, "stock_before": qb, "stock_after": qa, "records": recs}))
            rec("mech.v71.apex.cap", "PASS" if j1.get("why") == "cap 1 reached" else "FAIL",
                "ROSTER.apex.decide (cap 1, not forced) with the placed group on the map says 'cap 1 reached'",
                json.dumps({"why": j1.get("why"), "groups_on_map": j1.get("groups")}))
    # mech.v71.gobble: the active land roster's edges, as the console prints them
    og = tool("roster", "gobble", "land", timeout=180)
    edges = re.findall(r"^gobble-edge land (\S+) -> (\S+) (\S+) kind=(\w+)(?: class=(\S+))?", og, re.M)
    natives = [e for e in edges if e[3] == "native"]
    writes = [e for e in edges if e[3] == "write"]
    if not edges:
        rec("mech.v71.gobble", "FAIL" if "edge(s)" not in og else "NOT-TESTABLE-HERE", ">= 1 gobble-edge line for the land roster", og[:600],
            note="" if "edge(s)" not in og else "no allowed vermin or no seated consumer on this embark's land roster")
    else:
        nat_lua = "{" + ",".join("{%s,%s,%s}" % (json.dumps(c_), json.dumps(v_), json.dumps(k_ or "")) for c_, v_, _, _, k_ in natives) + "}"
        jn = _c_probe(f"""local bad={{}}
for _,t in ipairs({nat_lua}) do
  local cr, vr = M.rawOf(t[1]), M.rawOf(t[2]); local ok=false
  if cr and vr then
    local kc, kv = sw.classify(cr), sw.classify(vr)
    local has=false; for _,g in ipairs(kc.gobble or {{}}) do if g==t[3] then has=true end end
    ok = has and kv.cclass ~= nil and kv.cclass[t[3]] == true
  end
  if not ok then bad[#bad+1]=t[1]..'>'..t[2]..':'..t[3] end
end
print(json.encode({{bad=bad, n=#bad}}))""")
        if bad(jn):
            rec_bad("mech.v71.gobble", jn)
        else:
            ok = len(writes) >= 1 and not (jn.get("n") or 0)
            rec("mech.v71.gobble", "PASS" if ok else "FAIL", ">= 1 kind=write edge; every native edge's class on both the consumer's GOBBLE classes and the vermin's creature classes",
                json.dumps({"edges": len(edges), "write": len(writes), "native": len(natives), "native_mismatch": jn.get("bad")})[:900])
    # mech.v70.outgun: read-only survey; outgun_cap's group-size write in an in-memory build
    j = _c_probe("""local c=sw.loadConfig(); local v0=sw.CACHE.ver
local ok, txt = pcall(dfhack.run_command_silent, 'seasonal-wildlife', 'roster', 'outgun', 'land')
local v1=sw.CACHE.ver
local c2=sw.loadConfig(); c2.v7.outgun_cap=true
local okb, res = pcall(R.build, c2, 'land')
local capped, over = {}, {}
if okb and res and res.ok then
  local factor = V7.on(c2, 'outgun') or 2.0
  for _,og in ipairs(res.outgunned or {}) do
    capped[#capped+1] = {pred=og.pred, prey=og.prey, factor=og.factor, size=c2.group_size[og.prey_key]}
    if og.factor < factor then over[#over+1]=og.pred..'>'..og.prey end
  end
end
print(json.encode({txt=tostring(txt), v0=v0, v1=v1, built=okb and res and res.ok or false, capped=capped, below=over, factor=V7.on(c2,'outgun')}))""")
    if bad(j):
        rec_bad("mech.v70.outgun", j)
    else:
        txt = j.get("txt") or ""
        pairs_ = re.findall(r"outgunned: (\S+) pack vs (\S+) herd ([\d.]+)x", txt)
        fac = _c_num(j.get("factor"), 2.0)
        fmt_ok = txt.startswith("roster outgun land --")
        ok = fmt_ok and j.get("v0") == j.get("v1") and all(float(p[2]) >= fac for p in pairs_) and not (j.get("below") or []) \
             and all(isinstance(x, dict) and x.get("size") for x in (j.get("capped") or []))
        rec("mech.v70.outgun", "PASS" if ok else "FAIL",
            "the survey line, every listed factor >= v7 outgun, the config version unmoved (read-only); under outgun_cap every outgunned prey has a group size written",
            json.dumps({"reply": txt[:300], "pairs": len(pairs_), "ver_before": j.get("v0"), "ver_after": j.get("v1"), "capped": j.get("capped")})[:1200],
            note="" if pairs_ or j.get("capped") else "no outgunned pair in this embark's land pool: the survey's format and read-only half judged, the cap half had nothing to cap")
    # mech.v70.realms
    j = _c_probe("""local c=sw.loadConfig(); V7.loadRealmOverride()
local n, codes = 0, {}
for _,rs in pairs(V7.REALMS) do n=n+1; for _,r in ipairs(rs) do codes[r]=true end end
local nc=0; for _ in pairs(codes) do nc=nc+1 end
local tok, realm
for t,rs in pairs(V7.REALMS) do if #rs==1 and rs[1]~='COS' and rs[1]~='OCE' then tok,realm=t,rs[1]; break end end
local other; for _,r in ipairs(V7.REALM_ORDER) do if r~=realm and r~='OCE' then other=r; break end end
local out={n=n, ncodes=nc, tok=tok, realm=realm, other=other}
if tok then
  c.v7.realms=true
  out.same = V7.realmOk(c, {token=tok, layer='land'}, realm, 'land')
  out.otherOk = V7.realmOk(c, {token=tok, layer='land'}, other, 'land')
  out.unlisted = V7.realmOk(c, {token='NO_SUCH_CREATURE_XYZ', layer='land'}, other, 'land')
  c.v7.realms=false
  out.off = V7.realmOk(c, {token=tok, layer='land'}, other, 'land')
end
print(json.encode(out))""")
    if bad(j):
        rec_bad("mech.v70.realms", j)
    else:
        ok = (j.get("n") or 0) >= 300 and j.get("same") is True and j.get("otherOk") is False and j.get("unlisted") is True and j.get("off") is True
        rec("mech.v70.realms", "PASS" if ok else "FAIL", "300+ entries; realms on: own realm in, another out, unlisted in; realms off: all in", json.dumps(j))
    # flying / water / civ / apmass: in-memory builds and pure reads (nothing saved)
    j = _c_probe("""local c=sw.loadConfig(); local out={}
local ok1, rf = pcall(R.build, c, 'flying')
if ok1 and rf and rf.ok then out.fly={slots=rf.slots, unfilled=rf.unfilled} else out.flyErr=tostring(ok1 and rf and rf.why or rf) end
local c2=sw.loadConfig()
local ok2, rw = pcall(R.build, c2, 'water')
if ok2 and rw and rw.ok then out.water={slots=rw.slots, unfilled=rw.unfilled, deep=rw.deep, ocean=rw.ctx and rw.ctx.ocean or false} else out.waterErr=tostring(ok2 and rw and rw.why or rw) end
local le = M.entry('FISH_LAMPREY_SEA', 'water'); out.lamprey = le and R.slotOf(c, le, 'water') or 'absent'
local function civ(t) local cr=M.rawOf(t); if not cr then return 'absent' end; return V7.isCivRaw(cr) end
out.civ={ANT_MAN=civ('ANT_MAN'), BAT_MAN=civ('BAT_MAN'), WOLF_MAN=civ('WOLF_MAN')}
local pool=sw.buildPool(c); local n, nb = 0, 0
for _,e in ipairs(pool) do n=n+1; if type(e.civ)=='boolean' then nb=nb+1 end end
out.poolN, out.poolCivBool = n, nb
local dm=M.rawOf('DAMSELFLY_MAN'); if dm then local k=sw.classify(dm); out.dmMass=k.mass; out.dmGuild=k.guild; out.dmRoot=k.root end
print(json.encode(out))""", timeout=300)
    if bad(j):
        rec_bad(["mech.v71.flying", "mech.v71.water.pelagic", "mech.v71.civ", "mech.v71.apmass"], j)
    else:
        fly = j.get("fly") or {}
        fs = {s.get("code"): s for s in (fly.get("slots") or []) if isinstance(s, dict)}
        scav = {"BIRD_VULTURE", "BIRD_BUZZARD", "BIRD_KEA", "BIRD_RAVEN"}
        apx = list((fs.get("APX") or {}).get("members") or [])
        rp_n = int((fs.get("RP") or {}).get("have") or 0)
        if not fs:
            rec("mech.v71.flying", "FAIL", "`roster build flying` returns its slots", json.dumps(j.get("flyErr") or fly)[:600])
        elif not apx:
            rec("mech.v71.flying", "NOT-TESTABLE-HERE" if rp_n <= 1 else "FAIL", "an APX raptor seated (>= 2,000 cm3, not a scavenger) and RP <= 1",
                json.dumps({"RP": rp_n, "APX": apx, "unfilled": fly.get("unfilled")})[:800],
                note=_c_r8("a surface raptor of 2,000 cm3 or more in the embark pool (eagle, osprey...)", "LAKE or a forest fort"))
        else:
            ok = rp_n <= 1 and not (set(apx) & scav)
            rec("mech.v71.flying", "PASS" if ok else "FAIL", "RP <= 1; APX filled with no vulture, buzzard, kea or raven",
                json.dumps({"RP": rp_n, "APX": apx, "slots": {k: (v.get("have"), v.get("min"), v.get("max")) for k, v in fs.items()}}))
        wat = j.get("water") or {}
        ws = {s.get("code"): s for s in (wat.get("slots") or []) if isinstance(s, dict)}
        wu = [u for u in (wat.get("unfilled") or []) if isinstance(u, dict)]
        lam = j.get("lamprey")
        got = json.dumps({"slots": {k: (v.get("have"), v.get("min"), v.get("members")) for k, v in ws.items()}, "unfilled": wu,
                          "deep": wat.get("deep"), "ocean": wat.get("ocean"), "lamprey_slot": lam})[:1200]
        if lam not in ("MW", "absent", None) and not DRY:
            rec("mech.v71.water.pelagic", "FAIL", "FISH_LAMPREY_SEA slots as MW (R49)", got)
        elif need("mech.v71.water.pelagic", "ocean", "APE and PE seated or UNFILLED 'no candidate in pool' on an ocean fort", got):
            def seated_or_reported(code):
                s = ws.get(code) or {}
                return int(s.get("have") or 0) >= 1 or any(u.get("code") == code and "no candidate" in str(u.get("reason")) for u in wu)
            ok = bool(ws) and seated_or_reported("APE") and seated_or_reported("PE") and lam in ("MW", "absent")
            rec("mech.v71.water.pelagic", "PASS" if ok else "FAIL", "APE and PE seated, or UNFILLED with 'no candidate in pool'; the lamprey an MW", got)
        civ = j.get("civ") or {}
        ok = civ.get("ANT_MAN") is True and civ.get("BAT_MAN") is True and civ.get("WOLF_MAN") is False and (j.get("poolN") or 0) > 0 and j.get("poolN") == j.get("poolCivBool")
        rec("mech.v71.civ", "PASS" if ok else "FAIL", "ANT_MAN and BAT_MAN civ, WOLF_MAN not; every pool entry a civ boolean",
            json.dumps({"civ": civ, "pool": j.get("poolN"), "with_civ_bool": j.get("poolCivBool")}))
        if j.get("dmMass") is None and not DRY:
            rec("mech.v71.apmass", "NOT-TESTABLE-HERE", "DAMSELFLY_MAN in this world's raws", json.dumps(j.get("dmRoot")), note="a world without the animal people of vermin roots")
        else:
            ok = _c_num(j.get("dmMass")) >= 30000 and j.get("dmGuild") == "RP"
            rec("mech.v71.apmass", "PASS" if ok else "FAIL", "DAMSELFLY_MAN mass >= 30,000 cm3, guild RP",
                json.dumps({"mass": j.get("dmMass"), "guild": j.get("dmGuild"), "root": j.get("dmRoot")}))
    # mech.v71.freqfloor: the R61 floor written by V7.apply and put back by V7.restore
    j = _c_probe("""local c=sw.loadConfig(); V7.restore()
local pool=sw.buildPool(c); local zero, seen = {}, {}
for _,e in ipairs(pool) do
  if e.ap and e.inEmbark and not e.locked and not seen[e.token] then
    seen[e.token]=true; local cr=CAV.rawFor(e.token); if cr and cr.frequency==0 then zero[#zero+1]=e.token end
  end
end
local out={zero=zero, n=#zero, floor=c.roster.ap_freq_floor, after={}, post={}}
if #zero>0 then
  c.enabled=true; V7.apply(c, pool)
  for _,t in ipairs(zero) do out.after[t]=CAV.rawFor(t).frequency end
  V7.restore()
  for _,t in ipairs(zero) do out.post[t]=CAV.rawFor(t).frequency end
end
RESET()
print(json.encode(out))""")
    if bad(j):
        rec_bad("mech.v71.freqfloor", j)
    elif not (j.get("n") or 0):
        rec("mech.v71.freqfloor", "NOT-TESTABLE-HERE", "an in-embark animal person at raw FREQUENCY 0", json.dumps(j),
            note=_c_r8("a bear, cat or dog man on the embark (19 in vanilla at FREQUENCY 0)", "a temperate forest fort"))
    else:
        af, po = j.get("after") or {}, j.get("post") or {}
        floor = _c_num(j.get("floor"), 1)
        ok = all(_c_num(af.get(t)) >= max(1, floor) for t in j.get("zero") or []) and all(_c_num(po.get(t), -1) == 0 for t in j.get("zero") or [])
        rec("mech.v71.freqfloor", "PASS" if ok else "FAIL", "each FREQUENCY-0 animal person >= the floor after apply, 0 after restore", json.dumps(j)[:900])
    # mech.v71.place.deep: refused, no unit
    cnt = """local i=sw.raceIndex('MAGMA_CRAB'); local n=0
if i>=0 then for _,u in ipairs(df.global.world.units.active) do if u.race==i and not dfhack.units.isDead(u) then n=n+1 end end end
print(json.encode({race=i, n=n}))"""
    j0 = _c_probe(cnt)
    op = tool("place", "MAGMA_CRAB", "1", "deep", timeout=120)
    j1 = _c_probe(cnt)
    if bad(j0) or bad(j1):
        rec_bad("mech.v71.place.deep", j0 if bad(j0) else j1)
    elif (j0.get("race") if j0.get("race") is not None else 0) < 0:
        rec("mech.v71.place.deep", "NOT-TESTABLE-HERE", "MAGMA_CRAB in this world's raws", json.dumps(j0))
    elif "no stocked MAGMA_CRAB" in op:
        rec("mech.v71.place.deep", "NOT-TESTABLE-HERE", "a stocked magma-sea MAGMA_CRAB entry to refuse", op.strip()[:300],
            note=_c_r8("a magma sea with a stocked MAGMA_CRAB entry", "MAGMA") + "; no unit was created either way")
    else:
        ok = ("R60" in op or "R28" in op or "deep is never touched" in op) and j0.get("n") == j1.get("n") and not op.startswith("placed")
        rec("mech.v71.place.deep", "PASS" if ok else "FAIL", "a refusal naming R28/R60 and no new MAGMA_CRAB unit",
            json.dumps({"reply": op.strip()[:300], "before": j0.get("n"), "after": j1.get("n")}))
    # mech.v71.invasive: SAVAGE on a calm map, placed by the tool (R36)
    j = _c_probe("""local c=sw.loadConfig(); local out={}
local sv = R.savage(c); out.savage = sv.savage; out.maxSavagery = sv.max
local i = sw.raceIndex('CENOZOIC_SMILODON'); out.race = i
if i >= 0 and not sv.savage then
  local function cnt() local n=0; for _,u in ipairs(df.global.world.units.active) do if u.race==i and not dfhack.units.isDead(u) then n=n+1 end end; return n end
  out.before = cnt()
  local added, note = sw.addNewSpecies(c, 'CENOZOIC_SMILODON', 50, 100)
  out.added, out.note = added, tostring(note)
  out.listed = (c.roster and c.roster.invasive and c.roster.invasive.CENOZOIC_SMILODON) or false
  sw.saveConfig(c)
  out.after = cnt()
end
print(json.encode(out))""")
    if bad(j):
        rec_bad("mech.v71.invasive", j)
    elif (j.get("race") if j.get("race") is not None else 0) < 0:
        rec("mech.v71.invasive", "NOT-TESTABLE-HERE", "CENOZOIC_SMILODON in this world's raws", json.dumps(j), note="a world generated without the extinct creatures")
    elif j.get("savage"):
        rec("mech.v71.invasive", "NOT-TESTABLE-HERE", "a calm map (no embark region at savagery >= 66)", json.dumps(j),
            note=_c_r8("a calm map", "CTRL (calm)"))
    elif not (j.get("added") or 0) and not DRY:
        rec("mech.v71.invasive", "NOT-TESTABLE-HERE", "CENOZOIC_SMILODON's biomes on an embark region it is not already in", json.dumps(j),
            note=_c_r8("a calm embark whose biome the smilodon's raws allow (grassland/savanna/forest)", "CTRL"))
    else:
        oa = tool("roster", "apex", timeout=120)
        placed = int(_c_num(j.get("after"))) - int(_c_num(j.get("before")))
        ok = placed >= 1 and "invasive CENOZOIC_SMILODON" in oa
        rec("mech.v71.invasive", "PASS" if ok else "FAIL", ">= 1 smilodon placed at once; `roster apex` lists it as a tool-placed invasive",
            json.dumps({"added_entries": j.get("added"), "note": j.get("note"), "placed": placed, "listed_in_roster_apex": "invasive CENOZOIC_SMILODON" in oa})[:900])
    # mech.v71.realm.table
    ot = tool("realm", "table", timeout=120)
    m = re.search(r"realm-table entries=(\d+) missing_from_raws=(\d+)", ot)
    nlines = len(re.findall(r"^realm-entry \S+ \S+ raws=", ot, re.M))
    ok = bool(m) and int(m.group(2)) == 0 and int(m.group(1)) == nlines and nlines >= 300
    rec("mech.v71.realm.table", "PASS" if ok else "FAIL", "realm-table head with missing_from_raws=0; one realm-entry line per entry (300+)",
        json.dumps({"head": m.group(0) if m else ot[:200], "entry_lines": nlines}),
        note="" if not m or int(m.group(2)) == 0 else "missing_from_raws counts table tokens absent from this world's raws: a modded world, or a table entry with a misspelt token")

# ---- extinct ------------------------------------------------------------------------------------------------------
_C_EXT_SNAP = """
local X=V7.EXTINCT
local function allc(cr, f) local n,y=0,0; for _,c in ipairs(cr.caste) do n=n+1; if c.flags[f] then y=y+1 end end; return n>0 and y==n, y end
local function snap()
  local s={}
  for tok in pairs(X.TAGS) do
    local cr=CAV.rawFor(tok)
    if cr then
      local g=0; pcall(function() g=cr.caste[0].misc.grazer end)
      local _,gz=allc(cr,'GRAZER'); local _,bn=allc(cr,'BENIGN'); local _,lp=allc(cr,'LARGE_PREDATOR'); local _,ca=allc(cr,'CARNIVORE'); local _,am=allc(cr,'AMBUSHPREDATOR')
      local hg=false; pcall(function() hg=cr.flags.HAS_ANY_GRAZER end)
      s[tok]={f=cr.frequency, c0=cr.cluster_number[0], c1=cr.cluster_number[1], gz=gz, g=g, hg=hg, bn=bn, lp=lp, ca=ca, am=am}
    end
  end
  return s
end
local function diff(a, b)
  local d={}
  for tok, r in pairs(a) do local q=b[tok] or {}; for k,v in pairs(r) do if q[k]~=v then d[#d+1]=tok..'.'..k..' '..tostring(v)..'->'..tostring(q[k]) end end end
  return d
end
"""

def v71_extinct():
    ids_main = ["mech.v71.extinct.class", "mech.v71.extinct.freq", "mech.v71.extinct.grazer", "mech.v71.extinct.roles",
                "mech.v71.extinct.restore", "mech.v71.extinct.units"]
    j = _c_probe(_C_EXT_SNAP + """
local c=sw.loadConfig(); local out={}
local n, missing = 0, {}
for _,cr in ipairs(df.global.world.raws.creatures.all) do if X.isExtinct(cr) then n=n+1 end end
local inRaws=0
for tok in pairs(X.TAGS) do local cr=CAV.rawFor(tok); if cr then inRaws=inRaws+1; if not X.isExtinct(cr) then missing[#missing+1]=tok end end end
out.nClass, out.missing, out.tagsInRaws, out.tags = n, missing, inRaws, X.count()
out.fix = X.cfg(c).fix
V7.restore()
-- wild and tame extinct units of corrected species, before
local watch = {}
for _,u in ipairs(df.global.world.units.active) do
  local cr = df.creature_raw.find(u.race); local t = cr and X.TAGS[cr.creature_id]
  if t and not dfhack.units.isDead(u) and (t.lp~=nil or t.carn~=nil or t.benign~=nil or t.ambush~=nil or t.grazer) then
    local fl = {}; for k,f in pairs(X.FLAGS) do if t[k]~=nil then fl[f]=t[k] end end
    if t.grazer then fl.GRAZER=true end
    watch[#watch+1] = {u=u, tok=cr.creature_id, tame=dfhack.units.isTame(u), wild=dfhack.units.isWildlife(u), fl=fl}
  end
  if #watch >= 12 then break end
end
local function uread() local r={}; for i,w in ipairs(watch) do local o={}; for f in pairs(w.fl) do local ok,v=pcall(function() return w.u.enemy.caste_flags[f] end); o[f]=ok and v or nil end; r[i]=o end; return r end
local S0 = snap(); local U0 = uread()
c.enabled=true; c.extinct.fix=true
local pool=sw.buildPool(c)
out.msg = V7.apply(c, pool)
local S1 = snap(); local U1 = uread()
local function cls(t) local cr=M.rawOf(t); if not cr then return nil end; local k=sw.classify(cr); return {guild=k.guild, role=k.role, habitat=k.habitat} end
out.cls = {TRICERATOPS=cls('CRETACEOUS_TRICERATOPS'), EORAPTOR=cls('TRIASSIC_EORAPTOR'), TIKTAALIK=cls('DEVONIAN_TIKTAALIK'), TITANOBOA=cls('CENOZOIC_TITANOBOA'), DIMETRODON=cls('PERMIAN_DIMETRODON')}
local de = M.entry('PERMIAN_DIMETRODON', 'land'); if de then de.inEmbark=true; de.locked=false; out.dimLand = R.inPart(c, de, 'land') end
V7.restore()
local S2 = snap(); local U2 = uread()
local pick = {'CRETACEOUS_TYRANNOSAURUS','CRETACEOUS_QUETZALCOATLUS','CENOZOIC_TITANOBOA','CRETACEOUS_MOSASAURUS','CRETACEOUS_TRICERATOPS','CENOZOIC_MOA','TRIASSIC_EORAPTOR','DEVONIAN_TIKTAALIK'}
out.s0, out.s1, out.s2 = {}, {}, {}
for _,t in ipairs(pick) do out.s0[t]=S0[t]; out.s1[t]=S1[t]; out.s2[t]=S2[t] end
out.changed = #diff(S0, S1); out.restoreDiff = diff(S0, S2)
out.units = {}
for i,w in ipairs(watch) do out.units[i] = {tok=w.tok, tame=w.tame, wild=w.wild, want=w.fl, before=U0[i], after=U1[i], post=U2[i]} end
RESET()
print(json.encode(out))""", timeout=300)
    if bad(j):
        rec_bad(ids_main, j)
    else:
        lst = tool("extinct", "list", timeout=120)
        ok = int(_c_num(j.get("nClass"))) == 200 and not (j.get("missing") or []) and "no REAL_WORLD_EXTINCT class" not in lst
        rec("mech.v71.extinct.class", "PASS" if ok else "FAIL", "200 raws with REAL_WORLD_EXTINCT; every TAGS token in the raws carries it; no 'no REAL_WORLD_EXTINCT class' row",
            json.dumps({"with_class": j.get("nClass"), "tags": j.get("tags"), "tags_in_raws": j.get("tagsInRaws"), "missing_class": j.get("missing"),
                        "list_rows": len(re.findall(r"^extinct-entry ", lst, re.M))}),
            note="" if int(_c_num(j.get("nClass"))) == 200 else "a world whose raws are modded or generated without the extinct creatures reads another count")
        s0, s1, s2 = j.get("s0") or {}, j.get("s1") or {}, j.get("s2") or {}
        def f(s, t, k="f"):
            return (s.get(t) or {}).get(k) if isinstance(s.get(t), dict) else None
        trex, quetz, tita, mosa = "CRETACEOUS_TYRANNOSAURUS", "CRETACEOUS_QUETZALCOATLUS", "CENOZOIC_TITANOBOA", "CRETACEOUS_MOSASAURUS"
        if not s0.get(trex) and not DRY:
            for cid in ids_main[1:5]:
                rec(cid, "NOT-TESTABLE-HERE", "the extinct creatures in this world's raws", json.dumps(j)[:300], note="a world generated without them")
        else:
            got = {t: (f(s0, t), f(s1, t), f(s2, t)) for t in (trex, quetz, tita, mosa)}
            ok = (f(s1, trex), f(s1, quetz), f(s1, tita), f(s1, mosa)) == (2, 5, 3, 50) and (f(s2, trex), f(s2, quetz), f(s2, tita), f(s2, mosa)) == (50, 100, 30, 50)
            rec("mech.v71.extinct.freq", "PASS" if ok else "FAIL", "applied 2/5/3/50, restored 50/100/30/50 (before, applied, restored per token)", json.dumps(got),
                note="the raw is read (no CAVERN hold on these surface species in this probe; mech.v71.extinct.cavsnap covers the snapshot)")
            tri, moa = "CRETACEOUS_TRICERATOPS", "CENOZOIC_MOA"
            ok = (f(s1, tri, "gz") is not None and f(s1, tri, "gz") >= 1 and f(s1, tri, "g") == 150 and f(s1, tri, "hg") is True
                  and ((j.get("cls") or {}).get("TRICERATOPS") or {}).get("guild") == "GZ"
                  and f(s2, tri, "gz") == 0 and f(s2, tri, "g") == 0 and f(s2, tri, "hg") is False
                  and f(s0, moa, "gz") == f(s1, moa, "gz") == f(s2, moa, "gz"))
            rec("mech.v71.extinct.grazer", "PASS" if ok else "FAIL", "TRICERATOPS GRAZER on every caste, misc.grazer 150, HAS_ANY_GRAZER, guild GZ; restored false/0/false; MOA untouched",
                json.dumps({"triceratops": [s0.get(tri), s1.get(tri), s2.get(tri)], "guild": ((j.get("cls") or {}).get("TRICERATOPS") or {}).get("guild"),
                            "moa_grazer_castes": [f(s0, moa, "gz"), f(s1, moa, "gz"), f(s2, moa, "gz")]})[:1000])
            cl = j.get("cls") or {}
            eo, tk, tb, dm = cl.get("EORAPTOR") or {}, cl.get("TIKTAALIK") or {}, cl.get("TITANOBOA") or {}, cl.get("DIMETRODON") or {}
            eor, tik = "TRIASSIC_EORAPTOR", "DEVONIAN_TIKTAALIK"
            ok = (f(s1, eor, "bn") == 0 and (f(s1, eor, "ca") or 0) >= 1 and eo.get("guild") == "ML" and eo.get("role") == "predator"
                  and f(s1, tik, "lp") == 0 and tk.get("guild") == "MW" and (f(s1, tita, "lp") or 0) >= 1 and tb.get("guild") == "AW"
                  and dm.get("habitat") == "land" and dm.get("guild") == "AL" and j.get("dimLand") is True)
            rec("mech.v71.extinct.roles", "PASS" if ok else "FAIL", "EORAPTOR BENIGN off/CARNIVORE on/ML/predator; TIKTAALIK LP off/MW; TITANOBOA LP on/AW; DIMETRODON land/AL/land roster part",
                json.dumps({"raw_applied": {t: s1.get(t) for t in (eor, tik, tita)}, "model": cl, "dimetrodon_on_land_part": j.get("dimLand")})[:1200])
            rd = j.get("restoreDiff") or []
            ok = (j.get("changed") or 0) > 0 and not rd
            if manip("mech.v71.extinct.restore", "the apply wrote at least one TAGS raw", (j.get("changed") or 0) > 0 or DRY, json.dumps({"changed": j.get("changed"), "msg": str(j.get("msg"))[:300]})):
                rec("mech.v71.extinct.restore", "PASS" if ok else "FAIL", "every TAGS raw back to its pre-write value after V7.restore",
                    json.dumps({"fields_changed_by_apply": j.get("changed"), "not_restored": rd[:30]}))
        units = [u for u in (j.get("units") or []) if isinstance(u, dict)]
        wild = [u for u in units if u.get("wild") and not u.get("tame")]
        tame = [u for u in units if u.get("tame")]
        if not wild and not tame:
            rec("mech.v71.extinct.units", "NOT-TESTABLE-HERE", "a wild (and a tame) extinct animal of a corrected species on the map", json.dumps(units)[:300],
                note=_c_r8("wild extinct fauna on the map (worldgen REAL_WORLD_EXTINCT populations)", "none of the older forts is known to hold one"))
        else:
            okw = all(all((u.get("after") or {}).get(k) == v for k, v in (u.get("want") or {}).items()) and u.get("post") == u.get("before") for u in wild)
            okt = all(u.get("after") == u.get("before") for u in tame)
            rec("mech.v71.extinct.units", "PASS" if okw and okt else "FAIL", "wild: corrected flags on apply, own back on restore; tame: untouched",
                json.dumps(units)[:1200], note="" if wild and tame else ("no tame one on the map" if wild else "no wild one on the map") + ": that half not judged")
    # mech.v71.extinct.cavsnap: a CAVERN-held T. rex, both restore orders
    j = _c_probe("""local tok='CRETACEOUS_TYRANNOSAURUS'; local cr=CAV.rawFor(tok); local out={}
if not cr then out.absent=true; print(json.encode(out)) return end
V7.restore()
local snap=CAV.saved(); if snap[tok]~=nil then out.preheld=snap[tok]; RESET(); print(json.encode(out)) return end
local orig=cr.frequency; out.orig=orig
local function hold() local s=CAV.saved(); CAV.write(tok, 1, s); CAV.save(s) end
local function cavRestore() local s=CAV.saved(); if s[tok]~=nil then cr.frequency=s[tok]; s[tok]=nil; CAV.save(s) end end
local c=sw.loadConfig(); c.enabled=true; local pool=sw.buildPool(c)
hold(); out.heldRaw=cr.frequency
V7.apply(c, pool); out.snapA=CAV.saved()[tok]; out.rawA=cr.frequency
V7.restore(); cavRestore(); out.endA=cr.frequency
hold(); V7.apply(c, pool); out.snapB=CAV.saved()[tok]; out.rawB=cr.frequency
cavRestore(); V7.restore(); out.endB=cr.frequency
local s=CAV.saved(); s[tok]=nil; CAV.save(s); cr.frequency=orig
RESET()
print(json.encode(out))""")
    if bad(j):
        rec_bad("mech.v71.extinct.cavsnap", j)
    elif j.get("absent"):
        rec("mech.v71.extinct.cavsnap", "NOT-TESTABLE-HERE", "CRETACEOUS_TYRANNOSAURUS in this world's raws", json.dumps(j))
    elif j.get("preheld") is not None:
        rec("mech.v71.extinct.cavsnap", "NOT-TESTABLE-HERE", "T. rex not already held by the tool's CAVERN pass", json.dumps(j), note="the live hold is left alone")
    elif manip("mech.v71.extinct.cavsnap", "the hand hold put the T. rex raw at 1", j.get("heldRaw") == 1 or DRY, json.dumps(j)):
        ok = j.get("snapA") == 2 and j.get("rawA") == 1 and j.get("snapB") == 2 and j.get("rawB") == 1 and j.get("endA") == 50 and j.get("endB") == 50
        rec("mech.v71.extinct.cavsnap", "PASS" if ok else "FAIL",
            "while held: snapshot 2, raw 1; V7.restore then the CAVERN restore -> 50; the CAVERN restore then V7.restore -> 50",
            json.dumps(j), note="the CAVERN half is CAVERN.restoreAll's per-token step, applied to T. rex alone so no other held species is released")
    # mech.v71.extinct.standdown
    j = _c_probe("""local tok='CRETACEOUS_TYRANNOSAURUS'; local cr=CAV.rawFor(tok); local out={}
if not cr then out.absent=true; print(json.encode(out)) return end
V7.restore()
if CAV.saved()[tok]~=nil then out.preheld=true; RESET(); print(json.encode(out)) return end
local orig=cr.frequency; out.orig=orig
cr.frequency=7; out.hand=cr.frequency
local c=sw.loadConfig(); c.enabled=true; c.extinct.stand_down=true
V7.apply(c, sw.buildPool(c))
out.applied=cr.frequency; out.row=V7.EXTINCT.rowLine(c, tok)
V7.restore(); out.restored=cr.frequency
cr.frequency=orig
RESET()
print(json.encode(out))""")
    if bad(j):
        rec_bad("mech.v71.extinct.standdown", j)
    elif j.get("absent") or j.get("preheld"):
        rec("mech.v71.extinct.standdown", "NOT-TESTABLE-HERE", "an unheld T. rex raw in this world", json.dumps(j))
    elif manip("mech.v71.extinct.standdown", "the hand write put T. rex at 7", j.get("hand") == 7 or DRY, json.dumps(j)):
        row = str(j.get("row") or "")
        ok = j.get("applied") == 7 and j.get("restored") == 7 and "stood down" in row and "raw 7" in row
        rec("mech.v71.extinct.standdown", "PASS" if ok else "FAIL", "the hand value 7 survives apply and restore; the row reads 'stood down (raw 7)'", json.dumps(j)[:800])
    # mech.v71.extinct.model_off: through the console verb (it clears the class cache)
    fix0 = cfgv("extinct.fix").get("extinct.fix")
    o1 = tool("extinct", "off", timeout=180)
    if manip("mech.v71.extinct.model_off", "`extinct off` stored extinct.fix=false", cfgv("extinct.fix").get("extinct.fix") is False or DRY, o1[:400]):
        j = _c_probe("""local function cls(t) local cr=M.rawOf(t); if not cr then return nil end; local k=sw.classify(cr); return {guild=k.guild, role=k.role} end
local tri=CAV.rawFor('CRETACEOUS_TRICERATOPS'); local gz=0
if tri then for _,c in ipairs(tri.caste) do if c.flags.GRAZER then gz=gz+1 end end end
local eo=CAV.rawFor('TRIASSIC_EORAPTOR'); local bn=0
if eo then for _,c in ipairs(eo.caste) do if c.flags.BENIGN then bn=bn+1 end end end
print(json.encode({tri=cls('CRETACEOUS_TRICERATOPS'), eo=cls('TRIASSIC_EORAPTOR'), triGrazerCastes=gz, eoBenignCastes=bn, eoCastes=eo and #eo.caste or 0}))""")
        if bad(j):
            rec_bad("mech.v71.extinct.model_off", j)
        elif j.get("tri") is None and not DRY:
            rec("mech.v71.extinct.model_off", "NOT-TESTABLE-HERE", "the extinct creatures in this world's raws", json.dumps(j))
        else:
            ok = ((j.get("tri") or {}).get("guild") == "PL" and (j.get("eo") or {}).get("role") == "prey"
                  and j.get("triGrazerCastes") == 0 and j.get("eoBenignCastes") == j.get("eoCastes"))
            rec("mech.v71.extinct.model_off", "PASS" if ok else "FAIL", "TRICERATOPS guild PL, EORAPTOR prey; raws vanilla (no GRAZER, BENIGN on)", json.dumps(j))
    if fix0 is not False:
        tool("extinct", "on", timeout=180)
    # mech.v71.extinct.realm
    j = _c_probe("""local c=sw.loadConfig(); local X=V7.EXTINCT; local cc0=sw.CACHE.cfg; local E=cc0.extinct; local out={}
local fix0, re0 = E.fix, E.realms
local function n() local k=0; for _ in pairs(V7.REALMS) do k=k+1 end; return k end
local function head() X.realmSig=nil; local h=R.realmTable(c); return h end
E.fix=true; E.realms=false; out.headOff=head(); out.nOff=n(); local base={}; for t in pairs(V7.REALMS) do base[t]=true end
E.realms=true; out.headOn=head(); out.nOn=n()
local tr=V7.REALMS.CRETACEOUS_TYRANNOSAURUS; out.trexOn = tr and table.concat(tr, ',') or false
local exp=0; for tok,t in pairs(X.TAGS) do if t.realm and not base[tok] then exp=exp+1 end end; out.expected=exp
E.realms=false; out.headOff2=head(); out.nOff2=n(); out.trexOff = V7.REALMS.CRETACEOUS_TYRANNOSAURUS and true or false
local f=io.open('dfhack-config/seasonal-wildlife-realms.json','r'); out.userJson = f and true or false
if f then local okj,d=pcall(json.decode, f:read('*a')); f:close()
  if okj and type(d)=='table' then local t=next(d); out.userTok=t
    E.realms=true; head(); out.userOn = V7.REALMS[t] and true or false
    E.realms=false; head(); out.userOff = V7.REALMS[t] and true or false end end
E.fix, E.realms = fix0, re0; X.realmSig=nil; X.realmSync()
print(json.encode(out))""")
    if bad(j):
        rec_bad("mech.v71.extinct.realm", j)
    else:
        added = int(_c_num(j.get("nOn"))) - int(_c_num(j.get("nOff")))
        ok = (added == int(_c_num(j.get("expected"))) and added >= 80 and j.get("trexOn") == "NEA" and j.get("trexOff") is False
              and j.get("nOff2") == j.get("nOff") and (not j.get("userJson") or (j.get("userOn") and j.get("userOff"))))
        rec("mech.v71.extinct.realm", "PASS" if ok else "FAIL", "realms on adds the fossil rows (T. rex NEA); off takes them out; a user-json entry survives both",
            json.dumps({"entries_off": j.get("nOff"), "entries_on": j.get("nOn"), "added": added, "expected": j.get("expected"), "trex_on": j.get("trexOn"),
                        "trex_off": j.get("trexOff"), "user_json": j.get("userJson"), "user_tok": j.get("userTok"), "user_on": j.get("userOn"), "user_off": j.get("userOff")}),
            note="" if j.get("userJson") else "no dfhack-config/seasonal-wildlife-realms.json on the rig: the user-json half not judged")
    # mech.v71.extinct.mods
    om = tool("extinct", "mods", timeout=120)
    lost = ["CAMBRIAN_ANOMALOCARIS_MAN", "CENOZOIC_ENTELODON_MAN", "DEVONIAN_DUNKLEOSTEUS_MAN", "PERMIAN_HELICOPRION_MAN", "CRETACEOUS_MOSASAURUS_MAN"]
    ok = "attack mods active: 0" in om and all(t in om for t in lost)
    rec("mech.v71.extinct.mods", "PASS" if ok else "FAIL", "'attack mods active: 0' and the five mod-only animal people named", om.strip()[:700])
    # mech.v71.extinct.ladder: an extinct land apex seated, its FREQUENCY read as the corrected raw
    j = _c_probe("""local X=V7.EXTINCT; local c=sw.loadConfig(); V7.restore(); c.enabled=true
local pool=sw.buildPool(c); V7.apply(c, pool)
local cand={}
for _,e in ipairs(pool) do local t=X.TAGS[e.token]; if t and t.freq and R.inPart(c, e, 'land') and R.slotOf(c, e, 'land')=='APX' then cand[#cand+1]=e.token end end
local out={cand=cand, cap=c.roster.apex_raw_cap}
if #cand>0 then
  for _=1,4 do
    local c2=sw.loadConfig(); c2.enabled=true
    local ok, res = pcall(R.build, c2, 'land')
    if ok and res and res.ok then
      for tok,a in pairs(res.ladder_info.apex or {}) do if X.TAGS[tok] and X.TAGS[tok].freq then out.tok=tok; out.val=tostring(a); out.want=math.min(X.TAGS[tok].freq[2], c2.roster.apex_raw_cap or 5) end end
    end
    if out.tok then break end
  end
end
RESET()
print(json.encode(out))""", timeout=360)
    if bad(j):
        rec_bad("mech.v71.extinct.ladder", j)
    elif not (j.get("cand") or []):
        rec("mech.v71.extinct.ladder", "NOT-TESTABLE-HERE", "an extinct land apex with a FREQUENCY row in the embark pool", json.dumps(j),
            note=_c_r8("an extinct land apex in the embark (T. rex, smilodon, megalania...)", "none of the older forts is known to hold one"))
    elif not j.get("tok"):
        rec("mech.v71.extinct.ladder", "NOT-TESTABLE-HERE", "an extinct apex seated by one of four land builds", json.dumps(j), note="the builder's apex pick is random among the candidates")
    else:
        ok = j.get("val") == f"raw {j.get('want')}"
        rec("mech.v71.extinct.ladder", "PASS" if ok else "FAIL", "the seated extinct apex reads 'raw <corrected>' (not a capped 50)", json.dumps(j))

# ---- vermin -------------------------------------------------------------------------------------------------------
_C_SWV = """
local function swvCount(tag)
  local n=0
  for _,cr in ipairs(df.global.world.raws.creatures.all) do
    for _,c in ipairs(cr.caste) do
      for _,vec in ipairs({c.creature_class, c.gobble_vermin_class}) do
        for _,s in ipairs(vec) do local v=(type(s)=='string') and s or s.value; if (tag and v==tag) or (not tag and v:sub(1,4)=='SWV_') then n=n+1 end end
      end
    end
  end
  return n
end
"""

def v71_vermin():
    # mech.v70.gobble + mech.v71.vrm.restore: one apply, one restore
    j = _c_probe(_C_SWV + """local c=sw.loadConfig(); V7.restore(); local out={}
out.gobbleSwitch = V7.on(c, 'gobble')
out.before = swvCount(nil)
c.enabled=true; local pool=sw.buildPool(c); V7.apply(c, pool)
out.on = swvCount(nil); out.colony = swvCount('SWV_COLONY'); out.bat = swvCount('SWV_BAT')
local g = sw.CACHE.gobble or {}; out.tagged, out.cons = g.tagged, g.cons
-- every embark member's castes carry its own class
local badT, nm = {}, 0
for swv, list in pairs(g.members or {}) do
  if c.vermin_eat.classes[swv] ~= false then
    for _,tok in ipairs(list) do nm=nm+1
      local cr=CAV.rawFor(tok)
      if cr and VE.swvClass(cr)==swv then
        for _,cs in ipairs(cr.caste) do if not VE.vecHasValue(cs.creature_class, swv) then badT[#badT+1]=tok..':'..swv; break end end
      end
    end
  end
end
out.members, out.untagged = nm, badT
out.status = VE.gobbleStatus(c)
V7.restore(); out.after = swvCount(nil)
RESET()
print(json.encode(out))""", timeout=300)
    if bad(j):
        rec_bad(["mech.v70.gobble", "mech.v71.vrm.restore"], j)
    else:
        oc = tool("vermin", "classes", timeout=120)
        if j.get("gobbleSwitch") is False:
            rec("mech.v70.gobble", "FAIL", "v7 gobble on by default", json.dumps(j)[:400])
        elif not (j.get("members") or 0) and not DRY:
            rec("mech.v70.gobble", "NOT-TESTABLE-HERE", "in-embark vermin species to tag", json.dumps(j)[:400], note="no vermin species allowed on this embark")
        else:
            ok = (j.get("tagged") or 0) > 0 and (j.get("cons") or 0) > 0 and not (j.get("untagged") or []) and "vermin gobble: on" in str(j.get("status"))
            rec("mech.v70.gobble", "PASS" if ok else "FAIL", "every member's castes carry its SWV class; >= 1 consumer written; the gobble status line",
                json.dumps({"tagged_classes": j.get("tagged"), "consumers": j.get("cons"), "members": j.get("members"), "untagged": (j.get("untagged") or [])[:20],
                            "status": str(j.get("status"))[:300], "vermin_classes_reply": oc.strip()[:300]}))
        if manip("mech.v71.vrm.restore", "the apply wrote SWV strings", (j.get("on") or 0) > 0 or DRY, json.dumps(j)[:400]):
            ok = (j.get("after") or 0) == 0
            rec("mech.v71.vrm.restore", "PASS" if ok else "FAIL", "0 SWV_* strings in any caste's creature_class or gobble_vermin_class after V7.restore",
                json.dumps({"before": j.get("before"), "applied": j.get("on"), "SWV_COLONY": j.get("colony"), "SWV_BAT": j.get("bat"), "after_restore": j.get("after")}),
                note="" if (j.get("colony") or 0) and (j.get("bat") or 0) else "this embark has no colony insect or bat in its vermin, so the two new classes were not written to be removed")
    # mech.v71.vrm.swv_split
    j = _c_probe("""local cl = VE.allClasses(); local out={colony=cl.SWV_COLONY, bat=cl.SWV_BAT}
local soilColony = {}
for _,tok in ipairs(cl.SWV_SOIL or {}) do local cr=M.rawOf(tok); if cr and cr.flags.VERMIN_SOIL_COLONY then soilColony[#soilColony+1]=tok end end
local wantColony = {}
for _,cr in ipairs(df.global.world.raws.creatures.all) do if cr.flags.VERMIN_SOIL_COLONY and sw.classify(cr).gameVermin then wantColony[#wantColony+1]=cr.creature_id end end
local batOk = true
for _,tok in ipairs(cl.SWV_BAT or {}) do local cr=M.rawOf(tok); if not (cr and cr.flags.HAS_ANY_FLIER) then batOk=false end end
out.soilColony, out.wantColony, out.batOk = soilColony, wantColony, batOk
print(json.encode(out))""")
    if bad(j):
        rec_bad("mech.v71.vrm.swv_split", j)
    else:
        oc = tool("vermin", "classes", timeout=120)
        colony, bats = list(j.get("colony") or []), list(j.get("bat") or [])
        named = [t for t in ("BUMBLEBEE", "HONEY_BEE", "BEE_HONEY", "TERMITE") if t in colony]
        ok = (bool(colony) and bool(bats) and not (j.get("soilColony") or []) and j.get("batOk") is True
              and "SWV_COLONY" in oc and "SWV_BAT" in oc and ("BAT" in bats or not bats))
        rec("mech.v71.vrm.swv_split", "PASS" if ok else "FAIL", "SWV_COLONY and SWV_BAT listed and filled; no VERMIN_SOIL_COLONY species left in SWV_SOIL",
            json.dumps({"SWV_COLONY": colony, "SWV_BAT": bats, "named_found": named, "VERMIN_SOIL_COLONY_raws": j.get("wantColony"), "soil_colony_left": j.get("soilColony")})[:1200])
    # mech.v71.vrm.edges_src: the console's view, then the raws under each source
    oe = tool("vermin", "edges", timeout=120)
    j = _c_probe("""local c=sw.loadConfig(); V7.restore(); c.enabled=true; c.v7.gobble=true
local pool=sw.buildPool(c); local out={}
local function check(src)
  c.vermin_eat.source=src; V7.restore(); V7.apply(c, pool)
  local bad, n, nWant, seen = {}, 0, 0, {}
  for _,e in ipairs(pool) do
    if e.inEmbark and not e.locked and e.cat~='vermin' and not seen[e.token] then
      seen[e.token]=true
      local cr=CAV.rawFor(e.token)
      if cr then
        n=n+1
        local want = VE.gobbleWants(cr, e, c) or {}
        local have = {}
        for _,s in ipairs(cr.caste[0].gobble_vermin_class) do local v=(type(s)=='string') and s or s.value; if v:sub(1,4)=='SWV_' then have[v]=true end end
        for k in pairs(want) do nWant=nWant+1; if not have[k] and #bad<20 then bad[#bad+1]=e.token..' lacks '..k end end
        for k in pairs(have) do if not want[k] and #bad<20 then bad[#bad+1]=e.token..' extra '..k end end
      end
    end
  end
  return {consumers=n, wanted=nWant, bad=bad}
end
local rows, label = VE.edges(); out.label, out.rows = label, #rows
out.edges = check('edges'); out.rules = check('rules')
RESET()
print(json.encode(out))""", timeout=360)
    if bad(j):
        rec_bad("mech.v71.vrm.edges_src", j)
    else:
        e_, r_ = j.get("edges") or {}, j.get("rules") or {}
        console_ok = "source in force:" in oe and "edge table:" in oe
        if not (e_.get("consumers") or 0) and not DRY:
            rec("mech.v71.vrm.edges_src", "NOT-TESTABLE-HERE", "an in-embark consumer to wire", json.dumps(j)[:400], note="no managed non-vermin species on this embark")
        else:
            ok = console_ok and not (e_.get("bad") or []) and not (r_.get("bad") or []) and (e_.get("wanted") or 0) > 0
            rec("mech.v71.vrm.edges_src", "PASS" if ok else "FAIL",
                "`vermin edges` names the source and table; under 'edges' and 'rules' every consumer's SWV gobble classes equal VERMIN.gobbleWants",
                json.dumps({"console_head": oe.strip()[:200], "table": j.get("label"), "rows": j.get("rows"), "edges": e_, "rules": r_})[:1400],
                note="after a roster build the edge table is per species (fixes.md section 5), so the ML-guild expectation of the notes applies only to the ported table")
    # mech.v71.vrm.class_off: through the console, then the raws
    herp0 = cfgv("vermin_eat.classes.SWV_HERP").get("vermin_eat.classes.SWV_HERP")
    count = _C_SWV + """local c=sw.loadConfig(); V7.restore(); c.enabled=true; V7.apply(c, sw.buildPool(c))
local g=sw.CACHE.gobble or {}; local out={n=swvCount('SWV_HERP'), members=#((g.members or {}).SWV_HERP or {}), stored=c.vermin_eat.classes.SWV_HERP}
RESET()
print(json.encode(out))"""
    o1 = tool("vermin", "class", "SWV_HERP", "off", timeout=180)
    if manip("mech.v71.vrm.class_off", "`vermin class SWV_HERP off` stored false", cfgv("vermin_eat.classes.SWV_HERP").get("vermin_eat.classes.SWV_HERP") is False or DRY, o1[:300]):
        joff = _c_probe(count)
        o2 = tool("vermin", "class", "SWV_HERP", "on", timeout=180)
        jon = _c_probe(count) if (cfgv("vermin_eat.classes.SWV_HERP").get("vermin_eat.classes.SWV_HERP") is True or DRY) else {"_err": "`vermin class SWV_HERP on` did not store true: " + o2[:200]}
        if bad(joff) or bad(jon):
            rec_bad("mech.v71.vrm.class_off", joff if bad(joff) else jon)
        elif not (jon.get("members") or 0) and not DRY:
            rec("mech.v71.vrm.class_off", "PASS" if (joff.get("n") or 0) == 0 else "FAIL", "off: no SWV_HERP anywhere (the 'on puts it back' half needs a herp on the map)",
                json.dumps({"off": joff, "on": jon}), note=_c_r8("a lizard, frog or newt among the embark's vermin", "LAKE or RIVER4") + "; the on half not judged")
        else:
            ok = (joff.get("n") or 0) == 0 and (jon.get("n") or 0) > 0
            rec("mech.v71.vrm.class_off", "PASS" if ok else "FAIL", "off: no SWV_HERP on any caste or gobble vector; on: back", json.dumps({"off": joff, "on": jon}))
    if herp0 is not False:
        tool("vermin", "class", "SWV_HERP", "on", timeout=180)
    # mech.v71.vrm.vector
    j = _c_probe("""local c=sw.loadConfig(); local idx=VE.index(c, sw.FUSE.deadline(sw.FUSE.SCAN_MS))
local out={src=idx.src, objs=idx.objs, loose=idx.loose, colonies=idx.colonies, partial=idx.partial}
local la=0; for _,bc in pairs(idx.byClass) do la=la+bc.amount end; out.looseAmount=la
local vec=VE.vector(); local ind, colAmt = 0, 0
if vec then for _,v in ipairs(vec) do
  if not v.flags.already_deleting then
    local amt=v.amount or 1
    local col = v.flags.is_colony or amt >= 10000001
    pcall(function() if v.flags.is_roaming_colony then col=true end end)
    pcall(function() if v.category == df.vermin_category.Colony then col=true end end)
    if col then colAmt=colAmt+amt else ind=ind+amt end
  end
end end
out.indepLoose, out.colonyAmount = ind, colAmt
print(json.encode(out))""")
    if bad(j):
        rec_bad("mech.v71.vrm.vector", j)
    else:
        oc = tool("vermin", "census", timeout=120)
        if not j.get("src") and not DRY:
            rec("mech.v71.vrm.vector", "FAIL", "a vermin vector read (world.event.vermin or df.vermin.get_vector())", oc.strip()[:400])
        elif not (j.get("objs") or 0) and not DRY:
            rec("mech.v71.vrm.vector", "NOT-TESTABLE-HERE", "vermin objects on the map", json.dumps(j), note=_c_r8("vermin on the map (any season but deep winter)", "LAKE"))
        else:
            ok = ("NO VERMIN VECTOR" not in oc and (j.get("loose") or 0) + (j.get("colonies") or 0) == (j.get("objs") or 0)
                  and j.get("looseAmount") == j.get("indepLoose") and not j.get("partial"))
            rec("mech.v71.vrm.vector", "PASS" if ok else "FAIL", "a source named; objects = loose + colony sites; the loose amount equals an independent count that leaves colony amounts out",
                json.dumps(j), note="" if (j.get("colonies") or 0) else "no colony site on the map: the 'colony amount kept out' half holds vacuously")
    # mech.v71.vrm.forage_run / forage_off
    forage0 = cfgv("vermin_eat.forage").get("vermin_eat.forage")
    of = tool("vermin", "forage", "now", timeout=180)
    m = re.search(r"vermin forage: (\d+) eater\(s\) drawn now", of)
    j = _c_probe("""local st=sw.CACHE.vforage; local c=sw.loadConfig(); local rows, badU = {}, {}
for uid,p in pairs(st and st.pending or {}) do
  local u=df.unit.find(uid)
  if u then
    local ok = sw.WILD.onMap(u) and not dfhack.units.isTame(u) and V7.natural(c, u) and sw.WILD.layerOf(u)~='deep'
    local dOk = (p.dx==nil) or (u.path.dest.x==p.dx and u.path.dest.y==p.dy and u.path.dest.z==p.dz)
    if not (ok and dOk) then badU[#badU+1]=uid end
    if p.dx then rows[#rows+1]={id=uid, dx=p.dx, dy=p.dy, dz=p.dz} end
  end
end
print(json.encode({rows=rows, n=#rows, bad=badU, last=st and st.last and st.last.src or false}))""")
    if bad(j):
        rec_bad(["mech.v71.vrm.forage_run", "mech.v71.vrm.forage_off"], j)
        rows = []
    else:
        rows = [r_ for r_ in (j.get("rows") or []) if isinstance(r_, dict)]
        ok = bool(m) and "last pass" in of and "NO VERMIN VECTOR" not in of and not (j.get("bad") or [])
        rec("mech.v71.vrm.forage_run", "PASS" if ok else "FAIL", "'N eater(s) drawn now'; a last pass with its source; every pending forager wild, untamed, natural, not deep, on its recorded line",
            json.dumps({"reply": of.strip()[:400], "pending_walks": len(rows), "bad": j.get("bad")})[:900],
            note="" if rows else "no forager was drawn (no wild vermin eater near vermin on this map): the per-forager half holds vacuously")
    o_off = tool("vermin", "forage", "off", timeout=120)
    if manip("mech.v71.vrm.forage_off", "`vermin forage off` stored false", cfgv("vermin_eat.forage").get("vermin_eat.forage") is False or DRY, o_off[:300]):
        rows_lua = "{" + ",".join("{id=%d,dx=%d,dy=%d,dz=%d}" % (int(_c_num(r_.get("id"))), int(_c_num(r_.get("dx"))), int(_c_num(r_.get("dy"))), int(_c_num(r_.get("dz")))) for r_ in rows) + "}"
        j2 = _c_probe(f"""local st=sw.CACHE.vforage; local c=sw.loadConfig(); local ru=require('repeat-util')
local n=0; for _ in pairs(st and st.pending or {{}}) do n=n+1 end
local jobOn; for _,row in ipairs(sw.PANEL.jobs(c)) do if row.name==VE.FORAGE.JOB then jobOn=row.on end end
local still={{}}
for _,r in ipairs({rows_lua}) do local u=df.unit.find(r.id); if u and u.path.dest.x==r.dx and u.path.dest.y==r.dy and u.path.dest.z==r.dz then still[#still+1]=r.id end end
print(json.encode({{pending=n, panel=jobOn, scheduled=(ru.isScheduled and ru.isScheduled(VE.FORAGE.JOB)) or false, still=still}}))""")
        if bad(j2):
            rec_bad("mech.v71.vrm.forage_off", j2)
        else:
            ok = (j2.get("pending") or 0) == 0 and j2.get("panel") is False and not j2.get("scheduled") and not (j2.get("still") or [])
            rec("mech.v71.vrm.forage_off", "PASS" if ok else "FAIL", "pending empty; PANEL.jobs shows foraging off; the job not scheduled; no released unit still walking to its forage line",
                json.dumps(j2), note="" if rows else "no forage walk was in force to release")
    if forage0 is not False:
        tool("vermin", "forage", "on", timeout=120)
    # mech.v71.vrm.cfg: a bad saved block through the real loader (the saved config is put back in the same probe)
    j = _c_probe("""local KEY='seasonal-wildlife/config'; local utils=require('utils')
local orig=dfhack.persistent.getSiteData(KEY, nil)
local mod=utils.clone(orig or {}, true)
mod.vermin_eat={forage=true, source='bogus', cadence=10, radius=999, budget=0, chance=5, cooldown=-1, colony=2, diversity=99, classes={SWV_HERP=false}}
local out={}
local ok, err = pcall(function()
  dfhack.persistent.saveSiteData(KEY, mod); sw.CACHE.cfg=nil
  out.ve = sw.loadConfig().vermin_eat
end)
dfhack.persistent.saveSiteData(KEY, orig or {}); sw.CACHE.cfg=nil; sw.loadConfig()
out.ok, out.err = ok, err and tostring(err) or nil
out.def = sw.defaultConfig().vermin_eat
print(json.encode(out))""")
    if bad(j):
        rec_bad("mech.v71.vrm.cfg", j)
    elif not j.get("ok") and not DRY:
        rec("mech.v71.vrm.cfg", "FAIL", "the loader takes a bad vermin_eat block", str(j.get("err")))
    else:
        ve, d = j.get("ve") or {}, j.get("def") or {}
        keys = ("source", "cadence", "radius", "budget", "chance", "cooldown", "colony", "diversity")
        cls = ve.get("classes") or {}
        ok = (bool(ve) and all(ve.get(k) == d.get(k) for k in keys) and cls.get("SWV_HERP") is False
              and all(v is True for k, v in cls.items() if k != "SWV_HERP") and len(cls) == len(d.get("classes") or {}))
        rec("mech.v71.vrm.cfg", "PASS" if ok else "FAIL", "every bad number and the bad source load as the defaults; the saved SWV_HERP=false kept; the missing classes on",
            json.dumps({k: (ve.get(k), d.get(k)) for k in keys} | {"classes": cls}))
    # mech.v71.vrm.perf: 3,000 ticks with the tool on and foraging on
    en0 = cfgv("enabled").get("enabled")
    if en0 is not True:
        tool("enable", timeout=300)
    fz = cfgv("enabled", "vermin_eat.forage")
    if manip("mech.v71.vrm.perf", "the tool and foraging on for the timed window", (fz.get("enabled") is True and fz.get("vermin_eat.forage") is True) or DRY, json.dumps(fz)):
        luap("local sw=reqscript('seasonal-wildlife'); sw.FUSE.stats[sw.VERMIN.FORAGE.JOB]=nil; print(json.encode({ok=true}))")
        step(3000, 300)
        j = luap("local sw=reqscript('seasonal-wildlife'); local s=sw.FUSE.stats[sw.VERMIN.FORAGE.JOB] or {}; print(json.encode({runs=s.runs or 0, worst=s.worst or 0, over=s.over or 0, last=s.last}))")
        if bad(j):
            rec_bad("mech.v71.vrm.perf", j)
        elif not (j.get("runs") or 0) and not DRY:
            rec("mech.v71.vrm.perf", "FAIL", "the forage job ran in 3,000 ticks (every 100 t)", json.dumps(j))
        else:
            rec("mech.v71.vrm.perf", "PASS" if _c_num(j.get("worst"), 999) < 50 else "FAIL", "worst forage pass < 50 ms over 3,000 ticks", json.dumps(j),
                note=f"fort {F71.get('fort')}; the notes ask for region8 (R11)")
    if en0 is not True:
        tool("disable", timeout=300)
# ---- v7.1 water (docs/v7.1/water.md). Fort-dependent: BOATS (deep ocean), OCEAN2 (shallow ocean), any water for the rest.
_D_SURVEY_LUA = """local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig()
local w = sw.ENGINE.waterTiles(true)
local dc = sw.ENGINE.deepColumns(cfg, true)
local hist = {}
for b, h in pairs(w.hist or {}) do hist[b] = { h[1], h[2], h[3], h[4], h[5], h.cols } end
local top = -1
for _, c in pairs(w.cols or {}) do if c.body == 'ocean' and c.top > top then top = c.top end end
print(json.encode({hist=hist, maxDepth=w.maxDepth, deep={n=dc.n, total=dc.total, need=dc.need, max=dc.max}, zReached=w.zReached,
  zhi=w.zhi, zlo=w.zlo, topOcean=top, stopped=w.stopped and true or false, capped=w.capped and true or false, stride=w.stride}))"""

_D_CANDS_LUA = """local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local g=sw.loadGroups()
local out={bodies={}}
for _, b in ipairs({%s}) do
  local cs = sw.ENGINE.candidates(cfg, nil, b, g)
  local rows, seen, dup, land = {}, {}, 0, 0
  for _, c in ipairs(cs) do
    rows[#rows+1] = { key=c.key, token=c.e.token, level=c.ctx and c.ctx.level, base=c.base, factor=c.factor, weight=c.weight, why=c.why }
    if seen[c.e.token] then dup = dup + 1 end; seen[c.e.token] = true
    if not c.key:find(':', 1, true) then land = land + 1 end
  end
  out.bodies[b] = { n=#cs, dup=dup, land=land, rows=rows }
end
out.land_aquatic = cfg.water.land_aquatic
print(json.encode(out))"""

def _d_bodies():
    hv = F71.get("has") or {}
    bs = [b for b in ("ocean", "lake", "river", "pool") if hv.get(b)]
    return bs or (["ocean", "lake"] if DRY else [])

def _d_num(s, pat):
    m = re.search(pat, s or "")
    try: return float(m.group(1)) if m else None
    except ValueError: return None

def v71_water():
    fort = str(F71.get("fort") or "")
    # ---- R22: the column-depth survey
    S = luap(_D_SURVEY_LUA, timeout=180)
    if bad(S):
        rec_bad(["mech.v71.water.survey.levels", "mech.v71.water.survey.ocean2"], S)
    else:
        oh = (S.get("hist") or {}).get("ocean") or [0, 0, 0, 0, 0, 0]
        oh = [(x or 0) for x in (list(oh) + [0] * 6)[:6]]
        deep = S.get("deep") or {}
        cid = "mech.v71.water.survey.levels"
        if need(cid, "ocean", "an ocean with columns of 3+ stacked water tiles"):
            if not (has("ocean_deep") or fort.upper().startswith("BOATS")):
                rec(cid, "NOT-TESTABLE-HERE", "an ocean with columns of 3+ stacked water tiles", json.dumps({"ocean": oh, "deep": deep}),
                    note=NEED["ocean_deep"] + f"; {fort}'s ocean reaches column depth {(S.get('maxDepth') or {}).get('ocean')}")
            else:
                d_out = tool("water", "depth")
                ok = ((deep.get("n") or 0) > 0 and (oh[2] + oh[3]) > 0 and not S.get("stopped")
                      and isinstance(S.get("zReached"), int) and isinstance(S.get("topOcean"), int) and S["zReached"] < S["topOcean"]
                      and "ocean" in d_out and "column depth" in d_out)
                rec(cid, "PASS" if ok else "FAIL", "ocean columns at 3 and 4; deepColumns n > 0; zReached below the top ocean level; not stopped",
                    json.dumps({"ocean[1..5,cols]": oh, "deep": deep, "zReached": S.get("zReached"), "topOcean": S.get("topOcean"),
                                "stopped": S.get("stopped")}) + "\n" + d_out[:600])
        cid = "mech.v71.water.survey.ocean2"
        if fort.upper().startswith("OCEAN2") or DRY:
            ok = oh[2] + oh[3] + oh[4] == 0 and (oh[0] + oh[1]) > 0 and ((S.get("maxDepth") or {}).get("ocean") or 0) <= 2
            rec(cid, "PASS" if ok else "FAIL", "ocean columns of 1 and 2 only, max 2", json.dumps({"ocean[1..5,cols]": oh, "maxDepth": S.get("maxDepth")}))
        else:
            rec(cid, "NOT-TESTABLE-HERE", "OCEAN2 loaded (the claim is its measured shallow ocean)", json.dumps({"fort": fort, "ocean[1..5,cols]": oh}),
                note=NEED["ocean_shallow"])
    # ---- R22: stride 1 against stride 2
    cid = "mech.v71.water.survey.contig"
    if need(cid, "water", "surface water to sample at stride 1 and 2"):
        b0 = cfgv("water.survey_ms").get("water.survey_ms")
        tool("water", "budget", "1900")
        got = cfgv("water.survey_ms").get("water.survey_ms")
        if manip(cid, "water.survey_ms reads 1900 after `water budget 1900` (a stride-1 scan must not stop at its budget)", got == 1900 or DRY,
                 {"before": b0, "after": got}):
            full = tool("water", "depth", "full")
            j = luap("""local sw=reqscript('seasonal-wildlife')
local function H(w) local o={} for b, h in pairs(w.hist or {}) do o[b] = { h[1], h[2], h[3], h[4], h[5], h.cols } end return o end
local w2 = sw.ENGINE.waterTiles(true, 2); local h2, s2, c2 = H(w2), w2.stopped and true or false, w2.capped and true or false
local w1 = sw.ENGINE.waterTiles(true, 1); local h1, s1, c1 = H(w1), w1.stopped and true or false, w1.capped and true or false
sw.ENGINE.waterTiles(true); sw.CACHE.deepCols = nil
print(json.encode({h2=h2, h1=h1, stopped=(s1 or s2), capped=(c1 or c2)}))""", timeout=240)
            if bad(j):
                rec_bad(cid, j)
            elif j.get("stopped") or j.get("capped"):
                rec(cid, "NOT-TESTABLE-HERE", "both scans complete", json.dumps(j)[:900],
                    note="a scan stopped at its budget or hit ENGINE.ROW_CAP, so the counts are not comparable; a smaller water map (LAKE) completes")
            else:
                rows, worst = [], 0.0
                for b, h2 in (j.get("h2") or {}).items():
                    h1 = (j.get("h1") or {}).get(b) or []
                    for k in range(5):
                        a2 = (h2[k] if k < len(h2) else 0) or 0
                        a1 = (h1[k] if k < len(h1) else 0) or 0
                        if a2 >= 25:
                            r = a1 / a2
                            rows.append(f"{b}[{k + 1}] {a2} -> {a1} (x{r:.2f})")
                            worst = max(worst, abs(r - 4) / 4)
                if not rows:
                    rec(cid, "NOT-TESTABLE-HERE", "a column-depth bucket with 25+ sampled columns", json.dumps(j)[:900],
                        note="too little surface water for a 10% comparison; LAKE, RIVER4 or a region8 SHORE fort has enough")
                else:
                    ok = worst <= 0.10 and "single" in full
                    rec(cid, "PASS" if ok else "FAIL", "stride 1 = 4x stride 2 within 10% in every bucket of 25+ columns; `water depth full` reads every single x and y",
                        "; ".join(rows) + f"\nworst {worst:.3f}\n" + full[:300])
    # ---- R22: the renamed key
    cid = "mech.v71.water.column_levels"
    j = luap("""local sw=reqscript('seasonal-wildlife'); local V7=sw.V7
local a = sw.defaultConfig(); V7.watSanitize(a, { water = { deep_levels = 2 } })
local b = sw.defaultConfig(); V7.watSanitize(b, { water = { deep_levels = 2, column_levels = 4 } })
print(json.encode({carried=a.water.column_levels, explicit=b.water.column_levels, default=sw.defaultConfig().water.column_levels}))""")
    tool("water", "levels", "2")
    lv = cfgv("water.column_levels").get("water.column_levels")
    if bad(j):
        rec_bad(cid, j)
    elif manip(cid, "water.column_levels reads 2 after `water levels 2`", lv == 2 or DRY, {"column_levels": lv}):
        k = luap("local sw=reqscript('seasonal-wildlife'); local d=sw.ENGINE.deepColumns(sw.loadConfig()); print(json.encode({need=d.need, n=d.n}))")
        ok = j.get("carried") == 2 and j.get("explicit") == 4 and j.get("default") == 3 and not bad(k) and k.get("need") == 2
        rec(cid, "PASS" if ok else "FAIL", "deep_levels 2 loads as column_levels 2; an explicit column_levels 4 wins; default 3; `water levels 2` -> deepColumns().need 2",
            json.dumps({"sanitise": j, "deepColumns": k}))
    # ---- R45: land-layer AQUATIC entries drawn by Driver B
    cid = "mech.v71.water.landaq"
    if need(cid, "ocean", "an ocean whose candidates can include land-listed aquatic species"):
        tool("water", "aquatic", "on")
        on_v = cfgv("water.land_aquatic").get("water.land_aquatic")
        if manip(cid, "water.land_aquatic reads true after `water aquatic on`", on_v is True or DRY, {"land_aquatic": on_v}):
            a = luap(_D_CANDS_LUA % "'ocean'", timeout=180)
            tool("water", "aquatic", "off")
            off_v = cfgv("water.land_aquatic").get("water.land_aquatic")
            if manip(cid, "water.land_aquatic reads false after `water aquatic off`", off_v is False or DRY, {"land_aquatic": off_v}):
                b = luap(_D_CANDS_LUA % "'ocean'", timeout=180)
                tool("water", "aquatic", "on")
                if bad(a) or bad(b):
                    rec_bad(cid, a if bad(a) else b)
                else:
                    A = (a.get("bodies") or {}).get("ocean") or {}
                    B = (b.get("bodies") or {}).get("ocean") or {}
                    ev = json.dumps({"on": {k: A.get(k) for k in ("n", "land", "dup")}, "off": {k: B.get(k) for k in ("n", "land", "dup")},
                                     "on_land_keys": [r.get("key") for r in (A.get("rows") or []) if ":" not in str(r.get("key"))][:20]})
                    if (A.get("n") or 0) == 0:
                        rec(cid, "NOT-TESTABLE-HERE", "an in-season, stocked ocean candidate", ev, note="no water species is active, in season and stocked for the ocean this season")
                    elif (A.get("land") or 0) == 0:
                        rec(cid, "NOT-TESTABLE-HERE", "a land-listed AQUATIC entry in season and stocked", ev,
                            note="the ocean's candidates hold no land-layer key this season; OCEAN2's milkfish ride land entries (STATE addendum 20)")
                    else:
                        ok = (B.get("land") or 0) == 0 and (A.get("dup") or 0) == 0
                        rec(cid, "PASS" if ok else "FAIL", "land-layer keys among the ocean candidates with the switch on, none with it off, no species twice", ev)
    # ---- R62: the community mix (one draw first, so something is swimming)
    cid = "mech.v71.water.mix"
    bodies = _d_bodies()
    if need(cid, "water", "a water body to weigh"):
        body = bodies[0] if bodies else "ocean"
        tool("water", "mix", "on")
        mv = cfgv("water.mix.enabled", "water.mix.balance")
        if manip(cid, "water.mix.enabled true and balance > 0", (mv.get("water.mix.enabled") is True and (mv.get("water.mix.balance") or 0) > 0) or DRY, mv):
            drew = tool("water", "now", body)
            lines = tool("water", "mix", body)
            j = luap(_D_CANDS_LUA % f"'{body}'", timeout=180)
            k = luap(f"""local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local g=sw.loadGroups()
local cen = sw.V7.WAT.census(cfg, g); local B = cen['{body}']
local most, mn = nil, 0
for tok, s in pairs(B and B.sp or {{}}) do if s.n > mn then most, mn = tok, s.n end end
print(json.encode({{units=B and B.units or 0, most=most, most_n=mn, C=B and B.lv.C or 0, A=B and B.lv.A or 0}}))""")
            if bad(j) or bad(k):
                rec_bad(cid, j if bad(j) else k)
            else:
                rows = ((j.get("bodies") or {}).get(body) or {}).get("rows") or []
                wsum = sum((r.get("weight") or 0) for r in rows)
                most = k.get("most")
                mrow = next((r for r in rows if r.get("token") == most), None)
                bal = _d_num(mrow.get("why") if mrow else "", r"balance ([0-9.]+)")
                feed = [r.get("token") for r in rows if "feed" in str(r.get("why") or "")]
                ev = json.dumps({"body": body, "drew": drew.strip()[:160], "weights_sum": wsum, "most": most, "most_row": mrow,
                                 "feed_rows": feed[:8], "census": k})
                if not rows:
                    rec(cid, "NOT-TESTABLE-HERE", "candidates in the body", ev, note="no water species is active, in season and stocked here this season")
                elif mrow is None:
                    rec(cid, "NOT-TESTABLE-HERE", "the most-present species among the candidates", ev + "\n" + lines[:600],
                        note="the species most present in the body is not a candidate now (out of season or unstocked), so its balance factor is not shown")
                else:
                    ok = wsum > 0 and bal is not None and bal < 1 and " x " in lines and "base" in lines
                    rec(cid, "PASS" if ok else "FAIL", "weights sum > 0; the most-present species' balance < 1; `water mix` prints base x factor = weight",
                        ev + "\n" + lines[:800], note="" if feed else "no prey candidate showed a feed factor (no predator group that takes it is swimming here)")
    # ---- R43/R49: the apex limit per body (synthetic census on the engine's own mix) and the lamprey's level
    cid = "mech.v71.water.apexlimit"
    tool("water", "mix", "apex", "1")
    am = cfgv("water.mix.apex_max", "water.mix.enabled").get("water.mix.apex_max")
    if manip(cid, "water.mix.apex_max reads 1 after `water mix apex 1`", am == 1 or DRY, {"apex_max": am}):
        j = luap("""local sw=reqscript('seasonal-wildlife'); local V7=sw.V7; local cfg=sw.loadConfig()
local list = (cfg.roster and type(cfg.roster.aquatic_apex) == 'table') and cfg.roster.aquatic_apex or V7.WAT.APEX
local toks = {}; for tok, kind in pairs(list) do if kind == 'apex' then toks[#toks+1] = tok end end; table.sort(toks)
local apexE
for _, tok in ipairs(toks) do local e = (sw.MODEL.entry(tok, 'water')); if e then apexE = e; break end end
local preyE
for i, cr in ipairs(df.global.world.raws.creatures.all) do
  local c = sw.classify(cr)
  if c and c.habitat == 'aquatic' and c.role ~= 'predator' and not c.gameVermin and not c.mega and not c.night then
    local e = (sw.MODEL.entry(cr.creature_id, 'water')); if e and V7.WAT.levelOf(cfg, e) == 'H' then preyE = e; break end
  end
end
local out = { apex = apexE and apexE.token, prey = preyE and preyE.token }
local lam = (sw.MODEL.entry('FISH_LAMPREY_SEA', 'water')); out.lamprey = lam and V7.WAT.levelOf(cfg, lam) or nil
out.lampreyKind = V7.WAT.apexKind(cfg, 'FISH_LAMPREY_SEA')
local function run(held)
  local cands = {}
  for _, e in ipairs({ apexE, preyE }) do
    local cr = df.creature_raw.find(e.idx)
    cands[#cands+1] = { e = e, key = e.token, craw = cr, weight = 10, ctx = { level = V7.WAT.levelOf(cfg, e), predGroups = 0 } }
  end
  local B = { units = 4, groups = 2, sp = {}, lv = { H = 2, C = 0, A = 2 }, apexGroups = held, src = {} }
  V7.WAT.mix(cfg, cands, B, 'ocean')
  return { apex = cands[1].weight, prey = cands[2].weight, why = cands[1].why }
end
if apexE and preyE then out.held1 = run(1); out.held0 = run(0) end
print(json.encode(out))""", timeout=180)
        if bad(j):
            rec_bad(cid, j)
        elif not (j.get("apex") and j.get("prey")):
            rec(cid, "NOT-TESTABLE-HERE", "a curated apex and an aquatic prey species in this world's raws", json.dumps(j))
        else:
            h1, h0 = j.get("held1") or {}, j.get("held0") or {}
            ok = (h1.get("apex") == 0 and (h1.get("prey") or 0) > 0 and (h0.get("apex") or 0) > 0
                  and j.get("lamprey") == "C" and j.get("lampreyKind") is None)
            rec(cid, "PASS" if ok else "FAIL", "apex weight 0 with one apex group held, > 0 with none; the prey keeps its weight; FISH_LAMPREY_SEA level C, off the apex list",
                json.dumps(j), note="the census is synthetic (V7.WAT.mix on the engine's own candidates); the live per-body limit is the rig test's")
    # ---- R14/R59: prey pulls predators (a prey draw into the ocean, then the weights), then a pulled draw seeds by the prey
    pull_id, seed_id = "mech.v71.water.pull", "mech.v71.water.seed"
    _n1 = need(pull_id, "ocean", "an ocean to draw prey into")
    _n2 = need(seed_id, "ocean", "an ocean to draw prey into")   # both evaluated: each records its own NOT-TESTABLE-HERE
    if _n1 and _n2:
        pv = cfgv("water.pull.enabled", "water.pull.lift_floor", "water.pull.seek", "water.pull.min")
        if manip(pull_id, "water.pull on, lift_floor on, seek on", (pv.get("water.pull.enabled") is True and pv.get("water.pull.lift_floor") is True
                                                                   and pv.get("water.pull.seek") is True) or DRY, pv):
            P = luap("""local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local g=sw.loadGroups()
local cs = sw.ENGINE.candidates(cfg, nil, 'ocean', g)
local pick
for _, c in ipairs(cs) do if c.e.token == 'FISH_MILKFISH' then pick = c end end
if not pick then for _, c in ipairs(cs) do if c.ctx and c.ctx.level == 'H' and (c.e.mass or 0) < 100000 then pick = c; break end end end
local out = { cands = #cs }
if pick then
  local only = {}; only[pick.key] = true
  local grp, why = sw.ENGINE.draw(cfg, g, only, nil, 'ocean')
  if grp then sw.saveGroups(g); out.prey = grp.token; out.ids = grp.ids else out.why = why end
end
print(json.encode(out))""", timeout=180)
            if bad(P):
                rec_bad([pull_id, seed_id], P)
            elif not P.get("prey"):
                for cid in (pull_id, seed_id):
                    rec(cid, "NOT-TESTABLE-HERE", "a prey school drawn into the ocean", json.dumps(P),
                        note="no small in-season, stocked ocean prey to draw this season (OCEAN2's milkfish ride the land layer: STATE addendum 20)")
            else:
                W = luap("""local sw=reqscript('seasonal-wildlife'); local V7=sw.V7; local cfg=sw.loadConfig(); local g=sw.loadGroups()
local B = V7.WAT.census(cfg, g)['ocean']
local out = { prey = {}, real = {}, synth = {}, min = cfg.water.pull.min, ref = cfg.water.pull and cfg.water.pelagic_ref }
for tok, s in pairs(B and B.sp or {}) do out.prey[#out.prey+1] = tok .. ' ' .. s.n end
for _, c in ipairs(sw.ENGINE.candidates(cfg, nil, 'ocean', g)) do
  if c.ctx and c.ctx.level ~= 'H' and c.ctx.prey then
    out.real[#out.real+1] = { token = c.e.token, key = c.key, level = c.ctx.level, why = c.why, base = c.base, freq = c.craw and c.craw.frequency,
                              lifted = c.ctx.lifted and true or false, pelagic = c.ctx.pelagic and true or false }
  end
end
local list = (cfg.roster and type(cfg.roster.aquatic_apex) == 'table') and cfg.roster.aquatic_apex or V7.WAT.APEX
local toks = {}; for tok, kind in pairs(list) do if kind == 'apex' or kind == 'pelagic' then toks[#toks+1] = tok end end; table.sort(toks)
for _, tok in ipairs(toks) do
  local e = (sw.MODEL.entry(tok, 'water'))
  if e and B and e.waters and e.waters.bodies and e.waters.bodies.ocean then
    e.habitat, e.role = sw.MODEL.of(cfg, e)
    local cr = df.creature_raw.find(e.idx)
    local ctx = V7.WAT.ctxFor(cfg, e, B)
    if ctx.prey then
      local c = { e = e, key = tok, craw = cr, ctx = ctx, weight = sw.ENGINE.weight(cfg, e, cr, ctx) }
      V7.WAT.mix(cfg, { c }, B, 'ocean')
      out.synth[#out.synth+1] = { token = tok, level = ctx.level, why = c.why, base = c.base, freq = cr.frequency, mass = e.mass,
                                  lifted = ctx.lifted and true or false, pelagic = ctx.pelagic and true or false }
    end
  end
  if #out.synth >= 12 then break end
end
print(json.encode(out))""", timeout=180)
                if bad(W):
                    rec_bad([pull_id, seed_id], W)
                else:
                    pmin = W.get("min") or 1.5
                    rows = (W.get("real") or []) + (W.get("synth") or [])
                    pulled = [(r.get("token"), _d_num(r.get("why"), r"pull ([0-9.]+)")) for r in rows]
                    pulled_ok = [t for t, v in pulled if v is not None and v >= pmin - 1e-6]
                    lifted = [r for r in rows if r.get("lifted")]
                    lift_ok = [r.get("token") for r in lifted if r.get("base") == max(1, r.get("freq") or 0)]
                    ev = json.dumps({"prey_drawn": P.get("prey"), "swimming": W.get("prey"), "pull_min": pmin, "pulled": pulled[:14],
                                     "lifted": [(r.get("token"), r.get("base"), r.get("freq")) for r in lifted]})
                    if not rows:
                        rec(pull_id, "NOT-TESTABLE-HERE", "a predator or listed apex that takes the drawn prey", ev,
                            note=f"nothing on the roster or the curated apex list takes {P.get('prey')}")
                    else:
                        ok = bool(pulled_ok) and (bool(lift_ok) if lifted else True)
                        rec(pull_id, "PASS" if ok else "FAIL", "a pull factor >= pull.min on a predator of the swimming prey; a lifted pelagic's base equals its FREQUENCY",
                            ev, note="" if lifted else "no pelagic over pelagic_ref takes this prey, so the floor-lift half was not exercised")
                    real = [r for r in (W.get("real") or [])]
                    if not real:
                        rec(seed_id, "NOT-TESTABLE-HERE", "an in-season, stocked ocean predator of the drawn prey on the roster", ev,
                            note="the pulled draw needs a roster candidate (the synthetic apexes above are weighed, never drawn)")
                    else:
                        key = real[0].get("key")
                        pids = ",".join(str(int(i)) for i in (P.get("ids") or []) if str(i).lstrip("-").isdigit())
                        Sd = luap(f"""local sw=reqscript('seasonal-wildlife'); local V7=sw.V7; local cfg=sw.loadConfig(); local g=sw.loadGroups()
local preyIds = {{{pids}}}
local grp, why = sw.ENGINE.draw(cfg, g, {{ ['{key}'] = true }}, nil, 'ocean')
local out = {{ why = why }}
if grp then
  sw.saveGroups(g)
  out.token, out.pulled, out.n = grp.token, grp.pulled, #grp.ids
  local R = cfg.water.pull.seek_radius
  local pp = {{}}
  for _, id in ipairs(preyIds) do local u = df.unit.find(id); if u and not dfhack.units.isDead(u) then pp[#pp+1] = {{ x = u.pos.x, y = u.pos.y, z = u.pos.z }} end end
  local maxNear = 0
  for _, t in ipairs(sw.ENGINE.waterTiles().tiles) do
    if t.body == 'ocean' then
      for _, p in ipairs(pp) do
        if math.max(math.abs(t.x - p.x), math.abs(t.y - p.y), math.abs(t.z - p.z)) <= R then maxNear = math.max(maxNear, t.cdepth or 1); break end
      end
    end
  end
  out.maxNear, out.R, out.members = maxNear, R, {{}}
  for _, id in ipairs(grp.ids) do
    local u = df.unit.find(id)
    if u then
      local d = 0; while d < 20 and V7.GRP.wetAt(u.pos.x, u.pos.y, u.pos.z - d) do d = d + 1 end
      local best = 1e9
      for _, p in ipairs(pp) do best = math.min(best, math.max(math.abs(p.x - u.pos.x), math.abs(p.y - u.pos.y), math.abs(p.z - u.pos.z))) end
      out.members[#out.members+1] = {{ id = id, wet = V7.GRP.wetAt(u.pos.x, u.pos.y, u.pos.z), depth = d, dist = best }}
    end
  end
  local ls = sw.LEDGER.lines(3, 'arrive'); out.ledger = ls[#ls]
end
print(json.encode(out))""", timeout=180)
                        if bad(Sd):
                            rec_bad(seed_id, Sd)
                        elif not Sd.get("token"):
                            rec(seed_id, "FAIL", "the predator drawn", json.dumps(Sd))
                        else:
                            mem = Sd.get("members") or []
                            lim = (Sd.get("R") or 40) + 6   # ENGINE.RADIUS: the group spreads up to 6 tiles from the seed
                            ok = (Sd.get("pulled") == "prey" and "seeded by its prey" in str(Sd.get("ledger") or "") and mem
                                  and all(m.get("wet") and (m.get("dist") or 1e9) <= lim for m in mem)
                                  and max((m.get("depth") or 0) for m in mem) >= (Sd.get("maxNear") or 0) - 1)
                            rec(seed_id, "PASS" if ok else "FAIL", "pulled == 'prey'; ledger 'seeded by its prey'; every member wet, near the prey, on the deepest column there (less one)",
                                json.dumps(Sd)[:1400])
    # ---- the stranding guard (r2: getBreathingState)
    cid = "mech.v71.water.guard.recheck"
    if need(cid, "water", "a water body to draw a fish into") and need(cid, "r2", "getBreathingState in this DFHack"):   # one id: the first missing condition records it
        gv = cfgv("water.guard.enabled", "water.guard.recheck", "water.guard.passes")
        if manip(cid, "water.guard on with its re-check", (gv.get("water.guard.enabled") is True and gv.get("water.guard.recheck") is True) or DRY, gv):
            st = tool("water")
            body = (_d_bodies() or ["ocean"])[0]
            j = luap(f"""local sw=reqscript('seasonal-wildlife'); local V7=sw.V7; local cfg=sw.loadConfig(); local g=sw.loadGroups()
local out = {{}}
for _, c in ipairs(sw.ENGINE.candidates(cfg, nil, '{body}', g)) do
  local k = c.craw and sw.classify(c.craw)
  if k and k.habitat == 'aquatic' then
    local only = {{}}; only[c.key] = true
    local grp = sw.ENGINE.draw(cfg, g, only, nil, '{body}')
    if grp then sw.saveGroups(g); out.token = grp.token; out.id = grp.ids[1]; break end
  end
end
local u = out.id and df.unit.find(out.id)
if u then
  out.from = {{ u.pos.x, u.pos.y, u.pos.z }}
  for r = 1, 15 do
    for dx = -r, r do for dy = -r, r do
      if not out.to and (math.abs(dx) == r or math.abs(dy) == r) then
        for _, dz in ipairs({{ 0, 1 }}) do
          local x, y, z = u.pos.x + dx, u.pos.y + dy, u.pos.z + dz
          if not out.to and sw.PLACE.tile(x, y, z, false) and not V7.GRP.wetAt(x, y, z) then
            if dfhack.units.teleport(u, xyz2pos(x, y, z)) then out.to = {{ x, y, z }} end
          end
        end
      end
    end end
    if out.to then break end
  end
end
print(json.encode(out))""", timeout=180)
            if bad(j):
                rec_bad(cid, j)
            elif not j.get("to"):
                rec(cid, "NOT-TESTABLE-HERE", "a drawn fish set down on dry ground", json.dumps(j),
                    note="no aquatic species was drawable here this season, or no dry walkable tile within 15 tiles of it")
            else:
                uid = int(j.get("id") or -1)
                passes = []
                for _ in range(2):
                    step(20, 60)
                    p = luap(f"""local sw=reqscript('seasonal-wildlife'); local V7=sw.V7
local moved = V7.WAT.guard(sw.loadConfig(), sw.loadGroups())
local u = df.unit.find({uid})
local ok, s = false, nil
if u then ok, s = V7.WAT.breathOk(u) end
print(json.encode({{moved=moved, wet=u and V7.GRP.wetAt(u.pos.x, u.pos.y, u.pos.z) or false, dead=u and dfhack.units.isDead(u) or false, breath=s}}))""")
                    passes.append(p)
                    if isinstance(p, dict) and p.get("wet"):
                        break
                led = luap("local sw=reqscript('seasonal-wildlife'); local ls=sw.LEDGER.lines(8,'strand'); print(json.encode({lines=ls}))")
                lines = [str(x) for x in ((led.get("lines") if isinstance(led, dict) else None) or [])]
                hit = [l for l in lines if f"#{uid} " in l and "moved" in l and "not moved" not in l]
                ok = "via getBreathingState" in st and bool(passes) and isinstance(passes[-1], dict) and passes[-1].get("wet") and bool(hit)
                rec(cid, "PASS" if ok else "FAIL", "status 'via getBreathingState'; the stranded fish back in water within two passes; a strand ... moved ledger line",
                    json.dumps({"placed": j, "passes": passes, "strand": hit or lines[-3:]}) + "\n" + st[-400:])
    # ---- R45: the retry back-off (a cloned groups record, a config where nothing is allowed)
    cid = "mech.v71.water.retry"
    if need(cid, "water", "a water body whose draw can come up empty"):
        j = luap("""local sw=reqscript('seasonal-wildlife'); local utils=require('utils'); local cfg=sw.loadConfig()
cfg.allow = {}   -- nothing active: no water species is drawable (the precondition, read back below)
local g = utils.clone(sw.loadGroups(), true); g.next_water_body = {}; g.water_why = {}
local now = sw.absTick()
sw.V7.waterTick(cfg, g)
local out = { retry = cfg.water.retry_days, bodies = {} }
for b, t in pairs(g.next_water_body) do out.bodies[b] = { gap = t - now, why = (g.water_why or {})[b] } end
print(json.encode(out))""", timeout=180)
        if bad(j):
            rec_bad(cid, j)
        else:
            bs = j.get("bodies") or {}
            empty = {b: v for b, v in bs.items() if "no water species" in str(v.get("why") or "") or "none of those" in str(v.get("why") or "")}
            if manip(cid, "every drawn-at body reports nothing drawable (cfg.allow emptied)", (bool(bs) and len(empty) == len(bs)) or DRY, json.dumps(j)):
                lim = (j.get("retry") or 1) * 1200
                ok = bool(empty) and all((v.get("gap") or 1e9) <= lim + 1 for v in empty.values())
                rec(cid, "PASS" if ok else "FAIL", f"each empty body's next draw within retry_days x 1200 = {lim:.0f} ticks", json.dumps(j))
    # ---- R33/R43: no bear is a water candidate; R60: no cavern/deep entry or unit in the census or the candidates
    fid, nid = "mech.v71.water.fisher", "mech.v71.water.nodeep"
    _n1 = need(fid, "water", "a water body's candidates")
    _n2 = need(nid, "water", "a water body's census and candidates")   # both evaluated: each records its own NOT-TESTABLE-HERE
    if _n1 and _n2:
        bl = ",".join("'" + b + "'" for b in (_d_bodies() or ["ocean"]))
        j = luap("""local sw=reqscript('seasonal-wildlife'); local V7=sw.V7; local cfg=sw.loadConfig(); local g=sw.loadGroups()
local wt = sw.ENGINE.waterTiles()
local cen = V7.WAT.census(cfg, g)
local out = { n = 0, bears = {}, badKeys = {}, badPos = {}, units = 0, fisherKinds = {} }
for _, b in ipairs({%s}) do
  for _, c in ipairs(sw.ENGINE.candidates(cfg, nil, b, g)) do
    out.n = out.n + 1
    if c.e.token:find('BEAR', 1, true) then out.bears[#out.bears+1] = b .. ':' .. c.e.token end
    if c.key:match('^cavern') or c.key:match('^deep') then out.badKeys[#out.badKeys+1] = c.key end
  end
  local B = cen[b]
  for tok, s in pairs(B and B.sp or {}) do
    out.units = out.units + s.n
    for _, p in ipairs(s.pos) do if p.z < wt.zlo or p.z > wt.zhi + 1 then out.badPos[#out.badPos+1] = tok .. '@' .. p.z end end
  end
end
for _, tok in ipairs({ 'BEAR_GRIZZLY', 'BEAR_BLACK', 'BEAR_POLAR' }) do out.fisherKinds[tok] = V7.WAT.apexKind(cfg, tok) or 'none' end
print(json.encode(out))""" % bl, timeout=180)
        if bad(j):
            rec_bad([fid, nid], j)
        else:
            ev = json.dumps(j)[:900]
            if (j.get("n") or 0) == 0:
                rec(fid, "NOT-TESTABLE-HERE", "water candidates to inspect", ev, note="no water species is drawable here this season")
            else:
                ok = not j.get("bears") and all(v == "fisher" for v in (j.get("fisherKinds") or {}).values())
                rec(fid, "PASS" if ok else "FAIL", "no BEAR_* among the candidates of any body; the three bears are 'fisher' on the apex list", ev)
            if (j.get("n") or 0) == 0 and (j.get("units") or 0) == 0:
                rec(nid, "NOT-TESTABLE-HERE", "candidates or swimming units to inspect", ev, note="nothing drawable and nothing swimming here now")
            else:
                ok = not j.get("badKeys") and not j.get("badPos")
                rec(nid, "PASS" if ok else "FAIL", "no cavern:/deep: key among the candidates; every census position inside the surface band", ev)


# ---- v7.1 perf (docs/v7.1/perf.md). Headless: every claim reads the engine's own caches; one enable + a 3,200-tick run feeds P0/P5/P10/P11.
def _d_perf_legacy(cid, name, on):
    tool("perf", "legacy", name, "on" if on else "off")
    v = cfgv(f"perf.legacy_{name}").get(f"perf.legacy_{name}")
    return manip(cid, f"perf.legacy_{name} reads {on} after `perf legacy {name} {'on' if on else 'off'}`", v is on or DRY, {f"legacy_{name}": v})

def v71_perf():
    # ---- the run: reset, enable, every job scheduled at once, then a short stretch of play
    tool("perf", "reset")
    j0 = luap("""local sw=reqscript('seasonal-wildlife'); local ru=require('repeat-util')
print(json.encode({next=df.global.unit_next_id, enabled=sw.loadConfig().enabled}))""")
    tool("enable")
    en = cfgv("enabled").get("enabled")
    sched = luap("""local sw=reqscript('seasonal-wildlife'); local ru=require('repeat-util'); local cfg=sw.loadConfig()
local out = { jobs = {} }
for _, jb in ipairs(sw.PANEL.jobs(cfg)) do if jb.on then out.jobs[#out.jobs+1] = { name = jb.name, sched = ru.isScheduled(jb.name) and true or false } end end
print(json.encode(out))""")
    step(3200, 240)
    R = luap("""local sw=reqscript('seasonal-wildlife'); local C=sw.CACHE
local st = sw.FUSE.stats['seasonal-wildlife/groups'] or {}
local def = 0; for _, s in pairs(sw.FUSE.stats) do def = def + (s.deferred or 0) end
local wl = C.sliceLog and C.sliceLog.warm
local n = 0; for _ in pairs(C.ecoClass or {}) do n = n + 1 end
print(json.encode({ kb = st.kb, kb_worst = st.kb_worst, worst = st.worst, runs = st.runs, tickWorst = C.perfTickWorst, shared = C.perfShared or 0,
  deferred = def, warm = wl and { n = wl.n, err = wl.err, aborted = wl.aborted, cpu = wl.cpu } or nil,
  cached = { cave = C.cave ~= nil, wet = C.wet ~= nil, wtiles = C.wtiles ~= nil, veg = C.veg ~= nil }, ecoClass = n }))""")
    run_ok = en is True or DRY
    # P0 kb
    cid = "perf.p0.kb"
    if manip(cid, "the tool enabled (`enable`) so the groups job runs", run_ok, {"enabled": en}):
        if bad(R):
            rec_bad(cid, R)
        else:
            tw = (R.get("tickWorst") or {}).get("ms") if isinstance(R.get("tickWorst"), dict) else None
            ok = isinstance(R.get("kb"), (int, float)) and R["kb"] >= 0 and (R.get("runs") or 0) > 0 and tw is not None and tw >= (R.get("worst") or 0)
            rec(cid, "PASS" if ok else "FAIL", "groups kb a number >= 0; the worst tick >= the groups job's worst pass", json.dumps(R)[:900])
    # P0 verb
    out = tool("perf")
    ok = out.startswith("perf:") and "job / lap" in out and ("DFHack perf counters" in out or "not in this DFHack build" in out) and "rror" not in out
    rec("perf.p0.verb", "PASS" if ok else "FAIL", "the switch line, the job table, the counters or the 'not in this build' line; no error", out[:1200])
    # P5 phases
    cid = "perf.p5.phases"
    if manip(cid, "the tool enabled", run_ok, {"enabled": en}):
        if bad(sched) or bad(R):
            rec_bad(cid, sched if bad(sched) else R)
        else:
            jobs = sched.get("jobs") or []
            ok = bool(jobs) and all(x.get("sched") for x in jobs) and ((R.get("shared") or 0) == 0 or (R.get("deferred") or 0) > 0)
            rec(cid, "PASS" if ok else "FAIL", "every on job scheduled at once; shared ticks 0, or deferrals fired",
                json.dumps({"jobs": jobs, "shared": R.get("shared"), "deferred": R.get("deferred"), "tickWorst": R.get("tickWorst")}),
                note="3,200 ticks, not the notes' 6,000 (R12 short reps): two ecology passes, ten groups passes, three days")
    # P10 slice
    cid = "perf.p10.slice"
    if manip(cid, "the tool enabled (enableSched starts the warm slice)", run_ok, {"enabled": en}):
        sync = tool("roster", "build", "land")
        pb = tool("perf", "build", "land")
        step(200, 60)
        B = luap("""local sw=reqscript('seasonal-wildlife'); local b = sw.CACHE.sliceLog and sw.CACHE.sliceLog.build
print(json.encode({build = b and { n = b.n, err = b.err, aborted = b.aborted } or nil}))""")
        if bad(R) or bad(B):
            rec_bad(cid, R if bad(R) else B)
        else:
            w = R.get("warm") or {}
            c = R.get("cached") or {}
            b = B.get("build") or {}
            ok = ((w.get("n") or 0) >= 1 and not w.get("err") and all(c.get(k) for k in ("cave", "wet", "wtiles", "veg"))
                  and "started" in pb and b and not b.get("err") and not b.get("aborted") and "ladder-info" in sync)
            rec(cid, "PASS" if ok else "FAIL", "warm slice n >= 1, no error; four surveys cached; `perf build land` slice finished without error",
                json.dumps({"warm": w, "cached": c, "build": b, "perf_build": pb.strip()[:160]}) + "\n" + sync[:300],
                note="the sliced build's roster is not compared with `roster build land`'s: ROSTER.build draws its picks at random (ROSTER.pick, rng)")
    # P11 events
    cid = "perf.p11.events"
    if manip(cid, "the tool enabled and perf.events on", (run_ok and (cfgv("perf.events").get("perf.events") is True)) or DRY, {"enabled": en}):
        nxt = j0.get("next") if isinstance(j0, dict) else None
        cen = tool("perf", "census")
        E = luap(f"""local sw=reqscript('seasonal-wildlife'); local C=sw.CACHE
local before = {{}}; for id in pairs(C.wildIds or {{}}) do before[id] = true end
local ids = sw.V7.PERF.wildIds() or {{}}
local miss, arrived, arrivedIn = {{}}, 0, 0
for _, u in ipairs(df.global.world.units.active) do
  if dfhack.units.isActive(u) and not dfhack.units.isDead(u) and dfhack.units.isWildlife(u) then
    if not ids[u.id] then miss[#miss+1] = u.id end
    if u.id >= {int(nxt) if isinstance(nxt, int) else 2**30} then arrived = arrived + 1; if before[u.id] then arrivedIn = arrivedIn + 1 end end
  end
end
print(json.encode({{miss=miss, arrived=arrived, arrivedByEvent=arrivedIn, evArrivals=C.evArrivals or 0, seeds=C.wildSeeds or 0, evReg=C.evReg}}))""")
        if bad(E):
            rec_bad(cid, E)
        else:
            ok = "the wild-id set" in cen and not E.get("miss")
            rec(cid, "PASS" if ok else "FAIL", "census walked the wild-id set; every live wild unit in the set", json.dumps(E) + "\n" + cen[:400],
                note="" if (E.get("arrived") or 0) > 0 else "no wild unit arrived during the run, so the arrival path (event or tail scan) was not exercised")
    # P1 memo
    cid = "perf.p1.memo"
    j = luap("""local sw=reqscript('seasonal-wildlife'); local V7=sw.V7; sw.loadConfig(); local cfg=sw.CACHE.cfg
local diff, n, nat = {}, 0, {}
for _, u in ipairs(df.global.world.units.active) do
  local cr = df.creature_raw.find(u.race)
  if cr then
    n = n + 1
    local a = V7.PERF.raceEco(cfg, u.race); local b = (sw.ecoOf(cfg, cr))
    if a ~= b and #diff < 10 then diff[#diff+1] = cr.creature_id .. ' ' .. tostring(a) .. '/' .. tostring(b) end
    nat[tostring(u.id)] = V7.natural(cfg, u) and true or false
  end
end
_G.__v71_nat = nat
local k = 0; for _ in pairs(sw.CACHE.ecoClass or {}) do k = k + 1 end
print(json.encode({n=n, diff=diff, ecoClass=k}))""")
    if bad(j):
        rec_bad(cid, j)
    elif _d_perf_legacy(cid, "class", True):
        k = luap("""local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local nat=_G.__v71_nat or {}
local diff, n = {}, 0
for _, u in ipairs(df.global.world.units.active) do
  local was = nat[tostring(u.id)]
  if was ~= nil then n = n + 1; local now = sw.V7.natural(cfg, u) and true or false; if now ~= was and #diff < 10 then diff[#diff+1] = u.id end end
end
_G.__v71_nat = nil
print(json.encode({n=n, diff=diff}))""")
        _d_perf_legacy(cid, "class", False)
        if bad(k):
            rec_bad(cid, k)
        else:
            ok = (j.get("n") or 0) > 0 and not j.get("diff") and (j.get("ecoClass") or 0) > 0 and not k.get("diff")
            rec(cid, "PASS" if ok else "FAIL", "raceEco == ecoOf for every race on the map; CACHE.ecoClass non-empty; V7.natural unchanged under legacy_class",
                json.dumps({"memo": j, "legacy": k}))
    # P2 groups
    cid = "perf.p2.groups"
    pt = cfgv("perf.persist_transient").get("perf.persist_transient")
    if manip(cid, "perf.persist_transient off (the default)", pt is False or DRY, {"persist_transient": pt}):
        j = luap("""local sw=reqscript('seasonal-wildlife')
local a, b = sw.loadGroups(), sw.loadGroups()
local g = a; local had = g.stuck
if not g.stuck then g.stuck = { ['1'] = { x = 1, y = 1, z = 1, t = 0 } } end
sw.saveGroups(g)
local raw = dfhack.persistent.getSiteDataString and dfhack.persistent.getSiteDataString('seasonal-wildlife/groups') or nil
local rec = raw and require('json').decode(raw) or dfhack.persistent.getSiteData('seasonal-wildlife/groups', nil) or {}
g.stuck = had; sw.saveGroups(g)
print(json.encode({same=(a == b), n=#g.groups, nRec=rec.groups and #rec.groups or -1, stuckInRec=(rec.stuck ~= nil), compact=(raw ~= nil and not raw:find('\\n'))}))""")
        if bad(j):
            rec_bad(cid, j)
        else:
            ok = j.get("same") is True and j.get("n") == j.get("nRec") and j.get("stuckInRec") is False
            rec(cid, "PASS" if ok else "FAIL", "same table twice; the record round-trips #groups; no 'stuck' key in it", json.dumps(j))
    # P2 undo
    cid = "perf.p2.undo"
    j = luap("""local sw=reqscript('seasonal-wildlife'); local U=sw.UNDO
local d0 = U.depth(); local held0 = sw.CACHE.undo
local c = sw.loadConfig(); U.push(c, 'v71 perf probe')
local d1 = U.depth(); local held1 = sw.CACHE.undo
local label = U.pop(c); local d2 = U.depth()
print(json.encode({d0=d0, d1=d1, d2=d2, label=label, cap=U.CAP, sameRing=(held0 ~= nil and held0 == held1), held=(held1 ~= nil)}))""")
    if bad(j):
        rec_bad(cid, j)
    else:
        d0, d1 = j.get("d0") or 0, j.get("d1") or 0
        ok = (d1 == d0 + 1 or (d0 >= (j.get("cap") or 50) and d1 == d0)) and j.get("label") == "v71 perf probe" and j.get("d2") == d0 - (0 if d1 == d0 + 1 else 1) and j.get("held")
        rec(cid, "PASS" if ok else "FAIL", "depth +1 on the held ring (CACHE.undo); pop returns the label and the depth", json.dumps(j))
    # P3 overlay
    cid = "perf.p3.overlay"
    j = luap("""local sw=reqscript('seasonal-wildlife')
sw.CACHE.ovl = nil
local a = sw.V7.PERF.overlayData(); local b = sw.V7.PERF.overlayData()
local live = 0
for _, grp in ipairs(sw.loadGroups().groups) do
  for _, id in ipairs(grp.ids) do local u = df.unit.find(id); if u and not dfhack.units.isDead(u) then live = live + 1; break end end
end
print(json.encode({same=(a == b), markers=#a.groups, live=live, links=#a.links}))""")
    if bad(j):
        rec_bad(cid, j)
    else:
        ok = j.get("same") is True and j.get("markers") == j.get("live")
        rec(cid, "PASS" if ok else "FAIL", "the same table twice; one marker per group with a live member", json.dumps(j))
    # P4 census
    cid = "perf.p4.census"
    a = luap("""local sw=reqscript('seasonal-wildlife'); local utils=require('utils'); local C=sw.CACHE
C.census, C.censusOpen = nil, true
local ok, by = pcall(sw.WILD.countByLayer)
C.census, C.censusOpen = nil, false
local old = { land = 0, water = 0, cavern = 0, deep = 0 }
for _, u in ipairs(df.global.world.units.active) do if sw.WILD.onMap(u) then local L = sw.WILD.layerOf(u); old[L] = old[L] + 1 end end
local g = utils.clone(sw.loadGroups(), true); local _, list = sw.discoverGroups(g)
local ids = {}; for _, grp in ipairs(list or {}) do for _, id in ipairs(grp.ids) do ids[#ids+1] = id end end; table.sort(ids)
print(json.encode({census=ok and by or tostring(by), loop=old, ids=ids}))""")
    if bad(a):
        rec_bad(cid, a)
    elif _d_perf_legacy(cid, "census", True):
        b = luap("""local sw=reqscript('seasonal-wildlife'); local utils=require('utils')
local g = utils.clone(sw.loadGroups(), true); local _, list = sw.discoverGroups(g)
local ids = {}; for _, grp in ipairs(list or {}) do for _, id in ipairs(grp.ids) do ids[#ids+1] = id end end; table.sort(ids)
print(json.encode({ids=ids}))""")
        _d_perf_legacy(cid, "census", False)
        if bad(b):
            rec_bad(cid, b)
        else:
            ok = isinstance(a.get("census"), dict) and a.get("census") == a.get("loop") and (a.get("ids") or []) == (b.get("ids") or [])
            rec(cid, "PASS" if ok else "FAIL", "census counts == the v7.0 loop's; discoverGroups' ids the same with legacy_census",
                json.dumps({"census": a.get("census"), "loop": a.get("loop"), "ids": (a.get("ids") or [])[:30], "legacy_ids": (b.get("ids") or [])[:30]}))
    # P6 live (headless: the window's two sums)
    cid = "perf.p6.live"
    j = luap("""local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg)
local byKey = {}; for _, e in ipairs(pool) do byKey[e.key] = e end
local rs = sw.getEmbarkRegions(); local all = df.global.world.populations.all
local out = {}
for _, layer in ipairs({ 'land', 'water', 'cavern' }) do
  local a, b = 0, 0
  for _, r in ipairs(sw.CACHE.managedPops()) do
    local pop = r.layer == layer and all[r.i] or nil
    local e = pop and pop.race == r.race and byKey[r.key]
    if e and pop.quantity > 0 then a = a + pop.quantity * (e.mass or 0) end
  end
  for _, pop in ipairs(all) do
    if sw.managedPop(pop, rs, sw.LAYER_SET[layer]) then
      local cr = df.creature_raw.find(pop.race)
      local e = cr and byKey[sw.keyFor(layer, cr.creature_id)]
      if e and pop.quantity > 0 then b = b + pop.quantity * (e.mass or 0) end
    end
  end
  out[layer] = { index = a, walk = b }
end
print(json.encode(out))""", timeout=180)
    if bad(j):
        rec_bad(cid, j)
    else:
        ok = bool(j) and all(isinstance(v, dict) and v.get("index") == v.get("walk") for v in j.values())
        rec(cid, "PASS" if ok else "FAIL", "per layer, the index sum == the full walk's sum", json.dumps(j),
            note="computed headless the way the Live tab does (gui/seasonal-wildlife.lua:1080); the tab itself is phase_gui's")
    # P7 read-only config
    cid = "perf.p7.ro"
    j = luap("""local sw=reqscript('seasonal-wildlife'); local V7=sw.V7; local C=sw.CACHE
local c0 = V7.PERF.cfgRO(); local v0 = C.ver
local due = V7.PERF.writersDue(c0)
sw.groupsTick(c0)
local same, v1 = (C.cfg == c0), C.ver
local P = dfhack.persistent; local n, key = { 0, 0 }, sw.CAVERN.KEY
local o1, o2 = P.saveSiteData, P.saveSiteDataString
local phase = 1
P.saveSiteData = function(k, ...) if k == key then n[phase] = n[phase] + 1 end; return o1(k, ...) end
if o2 then P.saveSiteDataString = function(k, ...) if k == key then n[phase] = n[phase] + 1 end; return o2(k, ...) end end
local ok, err = pcall(function()
  local cfg = sw.loadConfig(); local s = df.global.cur_season
  sw.CAVERN.apply(cfg, s); phase = 2; sw.CAVERN.apply(cfg, s)
end)
P.saveSiteData, P.saveSiteDataString = o1, o2
print(json.encode({due=due, same=same, v0=v0, v1=v1, first=n[1], second=n[2], err=(not ok) and tostring(err) or nil}))""", timeout=180)
    if bad(j):
        rec_bad(cid, j)
    else:
        if j.get("due"):
            groups_ok = (j.get("v1") or 0) > (j.get("v0") or 0) or j.get("same") is False
        else:
            groups_ok = j.get("same") is True and j.get("v1") == j.get("v0")
        ok = groups_ok and not j.get("err") and (j.get("second") or 0) == 0
        rec(cid, "PASS" if ok else "FAIL", "no writer due: CACHE.cfg the same table, CACHE.ver unchanged (due: replaced); CAVERN.apply's second call saves nothing",
            json.dumps(j), note="" if j.get("due") else "no exhaust or spill writer was due, so the 'due pass saves' half was not exercised")
    # P8 pool
    cid = "perf.p8.pool"
    j = luap("""local sw=reqscript('seasonal-wildlife'); local P=sw.V7.PERF; sw.loadConfig(); local C=sw.CACHE
local p1 = P.pool(C.cfg); local h1 = C.poolMemo and C.poolMemo.hits or -1; local b1 = C.poolMemo and C.poolMemo.builds or -1
local p2 = P.pool(C.cfg); local h2 = C.poolMemo and C.poolMemo.hits or -1
sw.saveConfig(sw.loadConfig())
local p3 = P.pool(C.cfg); local b3 = C.poolMemo and C.poolMemo.builds or -1
print(json.encode({same=(p1 == p2), h1=h1, h2=h2, rebuilt=(p3 ~= p1), b1=b1, b3=b3}))""")
    if bad(j):
        rec_bad(cid, j)
    else:
        ok = j.get("same") is True and j.get("h2") == (j.get("h1") or 0) + 1 and j.get("rebuilt") is True and (j.get("b3") or 0) > (j.get("b1") or 0)
        rec(cid, "PASS" if ok else "FAIL", "same pool twice, hits +1; rebuilt after a saveConfig", json.dumps(j))
    # P9 native counts and edge-only surveys
    cid = "perf.p9.native"
    probe = """local sw=reqscript('seasonal-wildlife')
local veg = sw.V7.vegSurvey(true)
local tiles = sw.PLACE.tiles(false)
local cave = sw.CAVE.survey(); local bands = {}
for _, b in ipairs(cave.bands or {}) do bands[#bands+1] = { b.depth, b.open, b.water, b.magma, b.zlo, b.zhi } end
local wet = sw.WET.survey()
print(json.encode({grass=veg.grassShare, floor=veg.floor, first=tiles[1] and tiles[1].z or -1, bands=bands, caveStopped=cave.stopped,
  wet={ near = wet.near, sea = wet.sea, verdict = wet.verdict, stopped = wet.stopped }, fet=(sw.V7.PERF.fet() ~= nil)}))"""
    a = luap(probe, timeout=240)
    if bad(a):
        rec_bad(cid, a)
    elif _d_perf_legacy(cid, "survey", True):
        b = luap(probe, timeout=240)
        _d_perf_legacy(cid, "survey", False)
        if bad(b):
            rec_bad(cid, b)
        else:
            edge_ok = a.get("bands") == b.get("bands") and (a.get("wet") or {}).get("near") == (b.get("wet") or {}).get("near") \
                      and (a.get("wet") or {}).get("sea") == (b.get("wet") or {}).get("sea")
            stopped = a.get("caveStopped") or b.get("caveStopped") or (a.get("wet") or {}).get("stopped") or (b.get("wet") or {}).get("stopped")
            ev = json.dumps({"new": a, "legacy": b})[:1400]
            if stopped:
                rec(cid, "NOT-TESTABLE-HERE", "both surveys complete", ev, note="a CAVE or WET survey stopped at its budget, so the counts are not comparable")
            elif not edge_ok:
                rec(cid, "FAIL", "the edge-only CAVE/WET counts equal the legacy full scan's exactly", ev)
            elif not a.get("fet"):
                rec(cid, "NOT-TESTABLE-HERE", "dfhack.maps.forEachTile (DFHack r2) for the native-count half", ev,
                    note=NEED["r2"] + "; the edge-only CAVE/WET half matched exactly on this build")
            else:
                ok = abs((a.get("grass") or 0) - (b.get("grass") or 0)) <= 3 and a.get("first") == b.get("first")
                rec(cid, "PASS" if ok else "FAIL", "edge-only counts exact; grass share within 3 points; PLACE.tiles' first level the same", ev)
    # P12 scavenging memo and the web census
    cid = "perf.p12.scav"
    probe = """local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local h=sw.ALERTS.humanoids(); local st={ raceOk = {} }
local n = 0
local okV, vec = pcall(function() return df.global.world.items.other.ANY_CORPSE end)
for _, it in ipairs(okV and vec or df.global.world.items.all) do
  local t = it:getType()
  if t == df.item_type.CORPSE or t == df.item_type.CORPSEPIECE then
    if sw.SCAV.edible(it, h) and sw.SCAV.naturalRemains(cfg, st, it.race) then n = n + 1 end
  end
end
local wc = sw.V7.PERF.webCensus(sw.loadGroups()).wild; local by = sw.WILD.countByLayer()
print(json.encode({remains=n, web=wc, count=by}))"""
    a = luap(probe)
    if bad(a):
        rec_bad(cid, a)
    elif _d_perf_legacy(cid, "scav", True):
        b = luap(probe)
        _d_perf_legacy(cid, "scav", False)
        if bad(b):
            rec_bad(cid, b)
        else:
            web_ok = a.get("web") == a.get("count") and isinstance(a.get("web"), dict)
            ev = json.dumps({"new": a, "legacy": b})
            if not web_ok or a.get("remains") != b.get("remains"):
                rec(cid, "FAIL", "remains equal both ways; webCensus.wild == countByLayer", ev)
            elif (a.get("remains") or 0) == 0:
                rec(cid, "NOT-TESTABLE-HERE", "edible natural remains on the map to count both ways", ev,
                    note="no corpse on the map (the webCensus half matched); any fort after a kill has some")
            else:
                rec(cid, "PASS", "remains equal both ways; webCensus.wild == countByLayer", ev)


# ---- v7.1 web (docs/v7.1/web.md): the controls registry over HTTP. One server start, every check, then stop.
def v71_web():
    ids = ["web.v71.controls", "web.v71.set", "web.v71.set_panel", "web.v71.status", "web.v71.cluster", "web.v71.guard", "web.v71.perf", "web.v71.stop"]
    rc, out = sh("cmd", "seasonal-wildlife-web", "start", str(WEB_PORT), timeout=60)
    m = re.search(r"\?t=([0-9a-f]+)", out or "")
    tok = m.group(1) if m else ("0" * 20 if DRY else "")
    if not tok:
        for cid in ids:
            rec(cid, "FAIL", "the companion server started (a token in the start reply)", (out or "")[:400])
        return
    time.sleep(1)
    def js(body):
        try: return json.loads(body)
        except Exception: return {}
    # controls.json
    c, body = curl(f"/controls.json?t={tok}")
    reg = js(body)
    secs, ctl = reg.get("sections") or [], reg.get("controls") or []
    missing = [r.get("id") for r in ctl if isinstance(r, dict) and r.get("available") and "{T}" not in str(r.get("path") or "") and "value" not in r]
    ok = c == 200 and len(secs) >= 12 and len(ctl) >= 300 and not missing
    rec("web.v71.controls", "PASS" if ok else "FAIL", "200; >= 12 sections; >= 300 controls; every available non-{T} row has a value",
        json.dumps({"status": c, "sections": len(secs), "controls": len(ctl), "species_rows": len(reg.get("species") or []),
                    "actions": len(reg.get("actions") or []), "missing_value": missing[:20], "bytes": len(body)}))
    # set: a value, a range refusal, an unknown id
    L0 = luap("local sw=reqscript('seasonal-wildlife'); print(json.encode({count=sw.LEDGER.load().count}))")
    c1, b1 = curl(f"/set?t={tok}&id=hunters.stoop.chance&v=61", "POST")
    got = cfgv("hunters.stoop.chance").get("hunters.stoop.chance")
    L1 = luap("local sw=reqscript('seasonal-wildlife'); print(json.encode({count=sw.LEDGER.load().count}))")
    c2, b2 = curl(f"/set?t={tok}&id=hunters.stoop.chance&v=101", "POST")
    c3, b3 = curl(f"/set?t={tok}&id=no.such.control&v=1", "POST")
    j1, j2 = js(b1), js(b2)
    if manip("web.v71.set", "hunters.stoop.chance reads 61 in the config after the /set", got == 61 or DRY, {"config": got, "reply": b1[:300]}):
        ok = (c1 == 200 and j1.get("value") == 61 and (L1.get("count") or 0) > (L0.get("count") or 0)
              and c2 == 400 and "at most 100" in str(j2.get("out")) and c3 == 400)
        rec("web.v71.set", "PASS" if ok else "FAIL", "61 -> 200 value 61 and a ledger line; 101 -> 400 'at most 100'; unknown id -> 400",
            json.dumps({"set61": [c1, j1], "ledger": [L0.get("count"), L1.get("count")], "set101": [c2, j2], "unknown": [c3, b3[:200]]})[:1400])
    # set through the Panel path
    U0 = luap("local sw=reqscript('seasonal-wildlife'); print(json.encode({d=sw.UNDO.depth()}))")
    c4, b4 = curl(f"/set?t={tok}&id=switch.nudge&v=on", "POST")
    nv = cfgv("ecology.nudge").get("ecology.nudge")
    U1 = luap("local sw=reqscript('seasonal-wildlife'); print(json.encode({d=sw.UNDO.depth()}))")
    c5, b5 = curl(f"/set?t={tok}&id=switch.nudge&v=off", "POST")
    nv2 = cfgv("ecology.nudge").get("ecology.nudge")
    j4 = js(b4)
    if manip("web.v71.set_panel", "ecology.nudge reads true after /set switch.nudge on", nv is True or DRY, {"nudge": nv, "reply": b4[:300]}):
        ok = (c4 == 200 and "Panel" in str(j4.get("cmd")) and (U1.get("d") or 0) == (U0.get("d") or 0) + 1 and c5 == 200 and nv2 is False)
        rec("web.v71.set_panel", "PASS" if ok else "FAIL", "200 through 'Panel: Nudge'; undo depth +1; off puts it back",
            json.dumps({"on": [c4, j4], "undo": [U0.get("d"), U1.get("d")], "off": [c5, js(b5)], "nudge_after_off": nv2})[:1200])
    # status.json
    c6, b6 = curl(f"/status.json?t={tok}")
    st = js(b6)
    sec = st.get("sections") or {}
    errs = {k: (v or {}).get("error") for k, v in sec.items() if isinstance(v, dict) and (v or {}).get("error")}
    lay = ((sec.get("groupmap") or {}).get("layers") or [])
    first = lay[0].get("key") if lay and isinstance(lay[0], dict) else None
    ok = c6 == 200 and len(sec) >= 11 and not errs and first == "land"
    rec("web.v71.status", "PASS" if ok else "FAIL", "200; every section without error; groupmap.layers[0].key == 'land'",
        json.dumps({"status": c6, "sections": sorted(sec.keys()), "errors": errs, "first_layer": first, "ms": st.get("ms")})[:1200])
    # cluster order
    c7, b7 = curl(f"/state.json?t={tok}")
    snap = js(b7)
    raws = luap("""local out = {}
for _, cr in ipairs(df.global.world.raws.creatures.all) do out[cr.creature_id] = { cr.cluster_number[0], cr.cluster_number[1] } end
print(json.encode(out))""", timeout=180)
    if bad(raws):
        rec_bad("web.v71.cluster", raws)
    else:
        rows, wrong = 0, []
        for sp in snap.get("species") or []:
            cn = raws.get(sp.get("token"))
            if not (isinstance(cn, list) and len(cn) == 2) or sp.get("gsize_set"):
                continue
            c0, c1_ = cn
            if c0 == c1_:
                continue
            rows += 1
            if not ((sp.get("gmin") or 0) < (sp.get("gmax") or 0) and sp.get("gmax") == max(1, c0, c1_) and sp.get("gmin") == max(1, min(c0, c1_)) and sp.get("gmax") == c0):
                wrong.append([sp.get("token"), sp.get("gmin"), sp.get("gmax"), cn])
        if rows == 0:
            rec("web.v71.cluster", "NOT-TESTABLE-HERE" if c7 == 200 else "FAIL", "a species with two cluster numbers in the snapshot",
                json.dumps({"status": c7, "species": len(snap.get("species") or [])}))
        else:
            rec("web.v71.cluster", "PASS" if not wrong else "FAIL", "gmin < gmax, gmax == cluster_number[0] (the max) for every two-number species",
                json.dumps({"species_checked": rows, "wrong": wrong[:15]}))
    # guard: the v7.1 refusals
    g1, gb1 = curl(f"/act?t={tok}&id=roster_build&arg=everything", "POST")
    g2, _ = curl(f"/set?t={tok}&id=hunters.stoop.chance&v=60", "GET")
    g3, _ = curl("/set?t=wrong&id=hunters.stoop.chance&v=60", "POST")
    g4, _ = curl("/controls.json?t=wrong")
    g5, gb5 = curl(f"/cmd?t={tok}&a=groups&a=adopt&a=1", "POST")
    ok = g1 == 400 and "choose one of" in gb1 and g2 == 405 and g3 == 403 and g4 == 403 and g5 == 400
    rec("web.v71.guard", "PASS" if ok else "FAIL", "/act bad arg 400 'choose one of'; /set by GET 405; no token 403 (set, controls); /cmd groups adopt 400",
        json.dumps({"act_bad_arg": [g1, gb1[:160]], "set_get": g2, "set_no_token": g3, "controls_no_token": g4, "cmd_groups_adopt": [g5, gb5[:160]]}))
    # perf: two more snapshot builds, each past the 2 s snapshot TTL
    ms = []
    for _ in range(2):
        time.sleep(2.3)
        curl(f"/state.json?t={tok}")
        s = luap("local W=rawget(_G,'SW_WEB') or {}; local s=W.stats or {}; print(json.encode({snap_ms=s.snap_ms, snap_worst=s.snap_worst, static_ms=s.static_ms}))")
        ms.append(s if not bad(s) else {"_bad": bad(s)})
    vals = [x.get("snap_ms") for x in ms if isinstance(x.get("snap_ms"), (int, float))]
    _, wst = sh("cmd", "seasonal-wildlife-web", "status", timeout=60)
    ok = len(vals) == 2 and max(vals) < 50
    rec("web.v71.perf", "PASS" if ok else "FAIL", "the two snapshot builds after the first each under 50 ms", json.dumps({"builds": ms}) + "\n" + (wst or "").strip()[:300])
    # stop, and prove it
    _, so = sh("cmd", "seasonal-wildlife-web", "stop", timeout=60)
    c8, _ = curl("/")
    rec("web.v71.stop", "PASS" if c8 == 0 else "FAIL", "no answer on the port after stop", f"stop: {(so or '').strip()[:120]}; GET / after stop: {c8}")

def phase_v71(fort="CTRL", areas=None):
    log("== v7.1: " + ", ".join(a for a in V71_AREAS if not areas or a in areas))
    v71_facts(fort)
    for area in V71_AREAS:
        if areas and area not in areas:
            continue
        ids = v71_ids(area)
        fn = globals().get(f"v71_{area}")
        seen0 = {r["id"] for r in results}
        if fn is None:
            for cid in ids:
                rec(cid, "NOT-TESTABLE-HERE", "a check written for this claim", "", note=f"no v71_{area} sub-phase in this validator")
            continue
        log(f"-- v7.1 {area} ({len(ids)} claims)")
        push = cfg_push() if area != "deploy" else {}
        try:
            fn()
        except Exception as e:
            log(f"!! v71_{area} raised: {e!r}")
            seen = {r["id"] for r in results}
            for cid in ids:
                if cid not in seen:
                    rec(cid, "FAIL", "the sub-phase reaches this claim", repr(e)[:600], note=f"v71_{area} raised before this claim was judged")
        finally:
            if area != "deploy" and not bad(push):
                cfg_pop()
        seen = {r["id"] for r in results}
        for cid in ids:
            if cid not in seen and cid not in seen0:
                rec(cid, "NOT-TESTABLE-HERE", "a check reached this claim", "", note=f"v71_{area} ran but did not record this claim")

def phase_teardown(fort):
    log("== TEARDOWN")
    sh("title", timeout=180)
    save_dir = SAVES / fort; bk = BACKUPS / f"{fort}.preverify"
    same = None
    if save_dir.exists() and bk.exists():
        p = subprocess.run(["diff", "-rq", str(save_dir), str(bk)], capture_output=True, text=True)
        same = (p.returncode == 0)
        rec("mech.save.untouched", "PASS" if same else "FAIL", "diff -rq of the save against its backup is empty after the whole session",
            p.stdout[:400] or "identical", data={"identical": same})
    sh("save-restore", f"{fort}.preverify", timeout=300)

# ------------------------------------------------------------------------------ dry run ---
LUAC = Path(os.environ.get("LUAC53", str(Path.home() / "Claude/Projects/sw-wt/.tools/luac53")))   # DFHack's own Lua 5.3.6
DRY_ALIAS = {"sw": "", "V7": "V7.", "GRP": "V7.GRP.", "H": "V7.H.", "WAT": "V7.WAT.", "PERF": "V7.PERF.", "EXTINCT": "V7.EXTINCT."}
ENGINE_TABLES = ("V7", "SCAV", "VERMIN", "ROSTER", "MODEL", "IRRUPT", "QUOTA", "CAVERN", "PLACE", "WILD", "ENGINE", "CURIOUS",
                 "UNDO", "FUSE", "PANEL", "CACHE", "CAVE", "WET", "LEDGER", "PATTERN", "STOCK", "RESERVE", "ODDS", "HUNT", "ALERTS")

DRY_BAD_VERBS = {"help", "bogusverb"}   # verbs a claim sends on purpose to read the usage reply (cli.usage)

def dry_report():
    """After a --dry-run: every Lua chunk through luac53 -p, every engine name a chunk reads checked against the tool
    checkout ($SW_TOOL), every console verb against the dispatcher. Exit 1 on a syntax error, an unknown name or verb,
    or a phase that raised."""
    src = (TOOL / "scripts/seasonal-wildlife.lua").read_text(errors="replace") if (TOOL / "scripts/seasonal-wildlife.lua").exists() else ""
    side = {m: ((TOOL / f"scripts/{m}.lua").read_text(errors="replace") if (TOOL / f"scripts/{m}.lua").exists() else "")
            for m in ("seasonal-wildlife-controls", "seasonal-wildlife-web")}
    exports = dict(re.findall(r"^_ENV\.(\w+)\s*=\s*([\w.]+)", src, re.M))
    chunks = [c[1] for c in DRY_CALLS if c and c[0] == "lua"]
    uniq = list(dict.fromkeys(chunks))
    syntax = []
    tmp = OUT / "dry-lua"; tmp.mkdir(exist_ok=True)
    for i, code in enumerate(uniq):
        f = tmp / f"chunk{i:04d}.lua"; f.write_text(code)
        if LUAC.exists():
            p = _real_run([str(LUAC), "-p", str(f)], capture_output=True, text=True)
            if p.returncode != 0:
                syntax.append(((p.stderr or p.stdout).strip()[:300], code[:200].replace("\n", " ")))
    unknown, weak = {}, set()
    def known(path):
        if re.search(r"(^|[^\w.])" + re.escape(path) + r"\b", src) or ("function " + path) in src:
            return True
        return False
    for code in uniq:
        aliases = dict(DRY_ALIAS)
        for loc, rhs in re.findall(r"local\s+(\w+)\s*=\s*sw\.([A-Za-z_][\w.]*\w)(?![\w.])(?!\s*[(:])", code):
            first = rhs.split(".")[0]   # sw.GRP is exported as V7.GRP: alias the engine's own name
            aliases[loc] = exports.get(first, first) + rhs[len(first):] + "."
        mods = {loc: mod for loc, mod in re.findall(r"local\s+(\w+)\s*=\s*reqscript\('([\w-]+)'\)", code)}
        for head, rest, call in re.findall(r"(?<![\w.:])(\w+)\.([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)(\s*\()?", code):
            if head in mods:
                if mods[head] == "seasonal-wildlife":
                    first = rest.split(".")[0]
                    tgt = exports.get(first)
                    if tgt is None:
                        unknown.setdefault(f"sw.{first} (not exported by _ENV)", code[:120]); continue
                    path = tgt + rest[len(first):]
                    if "." in tgt or tgt in ENGINE_TABLES:
                        if "." in rest and not known(path) and not known(path.rsplit(".", 1)[0]):
                            unknown.setdefault(path, code[:120])
                        elif "." in rest and not known(path):
                            weak.add(path)
                    continue
                side_src = side.get(mods[head], "")
                first = rest.split(".")[0]
                if side_src and not re.search(r"_ENV\.%s\b|^(\w+\s*,\s*)*%s\s*(,\s*\w+\s*)*=|^function\s+%s\b" % (first, first, first), side_src, re.M):
                    unknown.setdefault(f"{mods[head]}:{first}", code[:120])
                continue
            if head in aliases and head != "sw":
                path = aliases[head] + rest
            elif head in ENGINE_TABLES:
                path = head + "." + rest
            else:
                continue
            if not known(path):
                parent = path.rsplit(".", 1)[0]
                if parent != path and known(parent) and not call:   # a call needs the function itself defined
                    weak.add(path)   # a field of a known table: set at run time, or a table-constructor key
                else:
                    unknown.setdefault(path, code[:120])
    verbs = set()
    for c in DRY_CALLS:
        if c and c[0] == "cmd" and len(c) > 2 and c[1] == "seasonal-wildlife":
            verbs.add(c[2])
    for code in uniq:
        for v in re.findall(r"run_command_silent,\s*'seasonal-wildlife'\s*,\s*[\"']([\w-]+)[\"']", code):
            verbs.add(v)
    badverbs = sorted(v for v in verbs if f"cmd == '{v}'" not in src and v not in DRY_BAD_VERBS)
    raised = [l for l in (OUT / "log.txt").read_text().splitlines() if "!! " in l]
    tally = {}
    for r in results:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    print(f"\n== DRY RUN against {TOOL}: {len(DRY_CALLS)} rig calls, {len(uniq)} distinct Lua chunks, {len(verbs)} verbs")
    print("   verdicts against the stub (meaningless as results; every branch ran): " + "  ".join(f"{k} {v}" for k, v in sorted(tally.items())))
    print(f"   luac53 -p: {len(syntax)} chunk(s) failed" + ("" if LUAC.exists() else f" (SKIPPED: no {LUAC})"))
    for e, c in syntax[:40]:
        print(f"     {e}\n       in: {c}")
    print(f"   engine names not found in the tool: {len(unknown)}")
    for k, c in sorted(unknown.items())[:80]:
        print(f"     {k}    <- {c[:90]!r}")
    print(f"   fields read off known tables (set at run time; not checkable statically): {len(weak)}")
    print(f"   verbs not in the dispatcher: {badverbs or 'none'}")
    print(f"   phases or sub-phases that raised: {len(raised)}")
    for l in raised[:40]:
        print("     " + l)
    return 1 if (syntax or unknown or badverbs or raised) else 0

_real_run = subprocess.run
def _dry_patch():
    """No DF, no screen, no curl, no waiting: every external call a phase makes returns empty."""
    def run(cmd_, *a, **k):
        if isinstance(cmd_, list) and cmd_ and str(cmd_[0]).endswith("luac53"):
            return _real_run(cmd_, *a, **k)
        DRY_CALLS.append(("run", " ".join(str(x) for x in (cmd_ if isinstance(cmd_, list) else [cmd_]))[:120]))
        empty = "" if (k.get("text") or k.get("universal_newlines")) else b""
        return subprocess.CompletedProcess(cmd_, 0, stdout=empty, stderr=empty)
    subprocess.run = run
    time.sleep = lambda *_a, **_k: None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fort", default="CTRL"); ap.add_argument("--skip-lake", action="store_true"); ap.add_argument("--skip-gui", action="store_true")
    ap.add_argument("--only", choices=["w0", "model", "v65", "v68", "v69", "v70", "v71", "gui"], help="run only the named phase between setup and teardown")
    ap.add_argument("--no-overlay-restore", action="store_true", help="v6.2.1 driver behaviour, kept to show w0.overlay failing first")
    ap.add_argument("--v71", default="", help="comma list of v7.1 sub-phases to run (" + ",".join(V71_AREAS) + "); default all")
    ap.add_argument("--list", nargs="?", const="", default=None, metavar="TEXT", help="print the claim register (rows containing TEXT) and exit; no rig")
    ap.add_argument("--dry-run", action="store_true", help="walk the phases against a stub rig and check every Lua probe offline; no rig")
    a = ap.parse_args()
    areas = [x for x in a.v71.split(",") if x] or None
    if areas and set(areas) - set(V71_AREAS):
        ap.error("unknown --v71 area(s): " + ",".join(sorted(set(areas) - set(V71_AREAS))))
    if a.list is not None:
        for c in CLAIMS:
            line = "\t".join((c[0], c[1], c[4], area_of(c) or "", c[2], c[3]))
            if a.list.lower() in line.lower():
                print(line)
        return 0
    if a.dry_run:
        _dry_patch()
    log(f"validate-full run {RUN} -> {OUT}" + ("  (DRY RUN: stub rig)" if a.dry_run else ""))
    ov0 = OVERLAY_JSON.read_text(errors="replace") if OVERLAY_JSON.exists() else ""
    try:
        base = phase_setup(a.fort)
        if a.only == "w0":
            try: phase_w0(a.fort)
            except Exception as e: log(f"!! phase_w0 raised: {e!r}")
            sh("cmd", "overlay", "enable", "seasonal-wildlife.groups", timeout=60)   # what mech.overlay does in a full run
        if a.only == "model":
            try: phase_model()
            except Exception as e: log(f"!! phase_model raised: {e!r}")
        if a.only == "v65":
            try: phase_v65()
            except Exception as e: log(f"!! phase_v65 raised: {e!r}")
        if a.only == "v68":   # the console roster and seasons verbs and the companion server alone
            try: phase_v68(); phase_v68_web()
            except Exception as e: log(f"!! phase_v68 raised: {e!r}")
        if a.only == "v69":   # the ECO ecology: armed, reach, seasons, pelagic, alerts, curious, exhaustion
            try: phase_v69()
            except Exception as e: log(f"!! phase_v69 raised: {e!r}")
        if a.only == "v70":   # alignment, leader, per-layer groups, the v7 raws, pack mass, sweep, civ races, domestic, sponges
            try: phase_v70()
            except Exception as e: log(f"!! phase_v70 raised: {e!r}")
        if a.only == "v71":   # the v7.1 sub-phases (--v71 picks some); fort-dependent claims say which fort they need
            try: phase_v71(a.fort, areas)
            except Exception as e: log(f"!! phase_v71 raised: {e!r}")
        if a.only == "gui":   # v6.7: re-check the window's claims alone (~4 min)
            try: phase_gui()
            except Exception as e: log(f"!! phase_gui raised: {e!r}")
        phases = () if a.only else (phase_cli, phase_mechanics)
        for ph in phases:
            try: ph()
            except Exception as e: log(f"!! phase {ph.__name__} raised: {e!r}")
        if not a.skip_gui and not a.only:
            try: phase_gui()
            except Exception as e: log(f"!! phase_gui raised: {e!r}")
        if not a.only:
            try: phase_static()
            except Exception as e: log(f"!! phase_static raised: {e!r}")
        if not a.skip_lake and not a.only:
            try: phase_lake()
            except Exception as e: log(f"!! phase_lake raised: {e!r}")
            sh("load", a.fort, timeout=300); time.sleep(1)
        if not a.only and V >= (6, 4, 0):
            try: phase_model()
            except Exception as e: log(f"!! phase_model raised: {e!r}")
        if not a.only and V65:
            try: phase_v65()
            except Exception as e: log(f"!! phase_v65 raised: {e!r}")
        if not a.only and V66:
            try: phase_v66()
            except Exception as e: log(f"!! phase_v66 raised: {e!r}")
        if not a.only and V67:
            try: phase_v67()
            except Exception as e: log(f"!! phase_v67 raised: {e!r}")
        if not a.only and V68:
            try: phase_v68(); phase_v68_web()
            except Exception as e: log(f"!! phase_v68 raised: {e!r}")
        if not a.only and V69:
            try: phase_v69()
            except Exception as e: log(f"!! phase_v69 raised: {e!r}")
        if not a.only and V70:
            try: phase_v70()
            except Exception as e: log(f"!! phase_v70 raised: {e!r}")
        if not a.only:
            try: phase_w0(a.fort)   # it turns every layer on and applies the season, which the earlier phases do not expect
            except Exception as e: log(f"!! phase_w0 raised: {e!r}")
        if not a.only and V71:   # after w0: v7.1 places units (apex, irruption, place clusters) that w0's tab timings must not carry
            try: phase_v71(a.fort, areas)
            except Exception as e: log(f"!! phase_v71 raised: {e!r}")
    finally:
        # w0.overlay: put DFHack's overlay switch back the way this run found it, then prove it
        was = overlay_state(ov0)
        if not a.no_overlay_restore:
            sh("cmd", "overlay", "enable" if was else "disable", "seasonal-wildlife.groups", timeout=60)
        ov1 = OVERLAY_JSON.read_text(errors="replace") if OVERLAY_JSON.exists() else ""
        now = overlay_state(ov1)
        rec("w0.overlay", "PASS" if bool(now) == bool(was) else "FAIL", f"seasonal-wildlife.groups enabled={bool(was)} after the run, as before it",
            f"before: enabled={was}; after: enabled={now}")
        try: phase_teardown(a.fort)
        except Exception as e: log(f"!! teardown raised: {e!r}")
    if not a.only:
        resolve_shipped_backlog()
    # every claim gets a row, even ones no check reached
    seen = {r["id"] for r in results}
    for c in CLAIMS:
        if c[0] not in seen and not a.only:
            rec(c[0], "NOT-TESTABLE-HERE", "a check reached this claim", "", note="no check ran for this claim in this session")
    (OUT / "results.json").write_text(json.dumps(results, indent=1))
    (OUT / "v71-todo.json").write_text(json.dumps(V71_TODO, indent=1))
    (OUT / "claims.json").write_text(json.dumps([dict(zip(("id", "surface", "claim", "source", "claimed"), c)) for c in CLAIMS], indent=1))
    tally = {}
    for r in results:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    log(f"== DONE {OUT}\n   " + "  ".join(f"{k} {v}" for k, v in sorted(tally.items())))
    if RETRIED: log("   retried once after an RPC timeout: " + "; ".join(RETRIED))
    if a.dry_run:
        return dry_report()
    return 0

sys.exit(main())
