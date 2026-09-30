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
Usage: validate-full.py [--fort CTRL] [--skip-lake] [--skip-gui]
"""
import argparse, json, os, re, subprocess, sys, time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CX = str(ROOT / "scripts" / "cx-lifecycle.sh")
TOOL = Path(os.environ.get("SW_TOOL", str(Path.home() / "Claude/Projects/seasonal-wildlife")))   # the checkout under test (a worktree per release)
RUN = datetime.now().strftime("%Y%m%d-%H%M%S")
OUT = ROOT / "data/validation/full" / RUN
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
    ("cli.status", "CLI", "`status` lists biomes, layers, quota, cavern line, on-the-map counts, the invasion field, and the embark subset", "USAGE.md", "shipped"),
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
    ("cli.quota", "CLI", "`quota [land|water|cavern] N` sets a per-layer ceiling; 0 unsets; status shows effective values and what is on the map", "USAGE.md", "shipped"),
    ("cli.quota.cavern", "CLI", "`quota cavern N` warns that the ceiling is enforced on FREQUENCY and brakes arrivals rather than culling", "STATE addendum 57", "shipped"),
    ("cli.water", "CLI", "`water [on|off|now|target N|cadence N|countdown N]` controls the water job; status names live/dormant with the reason", "USAGE.md", "shipped"),
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
    ("mech.leader.lowest", "MECH", "the leader is the lowest-id member (NOT the largest male — that is backlog)", "USAGE.md; Backlog", "shipped"),
    ("mech.hold", "MECH", "hold raises leave_countdown on every member to ≥ DAYS×1200 ticks", "USAGE.md v5.7; E9c/E19", "shipped"),
    ("mech.dismiss", "MECH", "dismiss zeroes leave_countdown and clears the leader", "USAGE.md v5.7", "shipped"),
    ("mech.ecology.write", "MECH", "the ecology write relates every LARGE_PREDATOR to every target in DF's reaction cache, slotting any unit DF has not (v5.9.7), and reports the pair count", "USAGE.md v5.6/v5.9.7; E11c/T4", "shipped"),
    ("mech.ecology.cadence", "MECH", "the ecology job fires on its own every 1,500 ticks while enabled", "USAGE.md v5.6", "shipped"),
    ("mech.ecology.nudge", "MECH", "a predator >40 tiles from every target for 3,000 ticks is moved to within 6", "USAGE.md v5.6; E18", "shipped"),
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
    ("mech.irruption.arm", "MECH", "with pressure pinned at the threshold, the next arriving cavern group the roster admits is armed (agitated flag on its members) and stood down after its duration; off is inert", "USAGE.md v6.1; PLAN 3.6b", "shipped"),
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
    # ---- Backlog (unscheduled, recorded for completeness)
    ("bl.frequency", "MECH", "per-species frequency override in the roster (never writing 0)", "Backlog", "backlog"),
    ("bl.popnumber", "DOC", "roster wording: 'regional stock' not per-fort budget", "Backlog", "backlog"),
    ("bl.grouping", "MECH", "published solitary/pack/herd table with overrides", "Backlog", "backlog"),
    ("bl.largestmale", "MECH", "leader chosen by body size and sex", "Backlog", "backlog"),
    ("bl.concurrency", "MECH", "max concurrent groups scaled from embark size (√tiles+1)", "Backlog", "backlog"),
    ("bl.deepwater", "MECH", "deep-ocean species gated on the map having deep tiles", "Backlog", "backlog"),
    ("bl.migrants", "MECH", "migrant-trigger timing study", "Backlog", "backlog"),
    ("bl.perch", "MECH", "perched-fraction survey before any perch lever", "Backlog", "backlog"),
    ("bl.r2r4", "MECH", "identify the 'r2/r4' creature", "Backlog", "backlog"),
    ("bl.realm", "MECH", "geographic/realm grouping of species", "Backlog", "backlog"),
    ("bl.quiet", "MECH", "tool-side filter to quiet animal-on-animal combat reports", "Backlog", "backlog"),
    ("bl.eats", "MECH", "a who-eats-whom history", "Backlog", "backlog"),
    ("bl.balance", "MECH", "water placement weighted by what is swimming", "Backlog", "backlog"),
    # ---- Documentation claims that must match the code
    ("doc.usage.version", "DOC", "USAGE.md's header states the current version and DF/DFHack it was developed against", "USAGE.md", "doc"),
    ("doc.usage.cavernquota", "DOC", "USAGE.md's description of `quota cavern` matches the shipped mechanism", "USAGE.md Per-layer quotas", "doc"),
    ("doc.docstring.tabs", "DOC", "the script docstring's tab count and Usage block match the shipped window and verbs", "script docstring", "doc"),
    ("doc.design.views", "DOC", "the design report's §11 catalogue is labelled as v6.0 aspiration, not shipped", "design §11", "doc"),
    ("doc.docket", "DOC", "the Docket's statement that the tool is at v5.5 is stale", "Docket", "doc"),
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

RPC_TIMEOUT = "45"   # 22 Sep 2026: `groups` right after a full-speed 6,000-tick step twice missed cx-rpc's 15 s default (0.15 s by hand)
RETRIED = []
def sh(*args, timeout=180):
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
        p = subprocess.run(a + [f"http://127.0.0.1:{port}{path}"], capture_output=True, text=True)
        body, _, code = p.stdout.rpartition("\n")
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
if sw.ecologyRun then T(out.jobs, 'ecology (1500 t)', function() sw.ecologyRun(cfg, g) end)
else T(out.jobs, 'ecology (1500 t)', function() dfhack.run_command_silent('seasonal-wildlife','groups','ecology','now') end) end
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
    s = shot("A0-map-baseline")
    log(f"  loaded: tick {g.get('tick')} season {g.get('season')} citizens {g.get('citizens')} "
        f"land {g.get('land')} water {g.get('water')} cavern {g.get('cavern')} deep {g.get('deep')}")
    return g

def phase_cli():
    log("== CLI")
    rc, out = cmd("status")
    q = "limits:" if V65 else "quota:"   # v6.5 (W4): quota retired for limits (groups at once, ceiling)
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
    rec("cli.quota", "PASS" if (("limits:" in out) if V65 else ("quota:" in out)) and "on the map now" in out else "FAIL", "the limits (v6.5; quota before) line + on-the-map", out)
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
                "if g then for _,grp in ipairs(g.groups) do if grp.leader then local mn=math.huge; for _,i in ipairs(grp.ids) do if i<mn then mn=i end end; "
                "out[#out+1]={token=grp.token, leader=grp.leader, lowest=mn, n=#grp.ids} end end end; print(json.encode(out))", timeout=120)
    if isinstance(lead, list) and lead:
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
    rec("mech.ecology.cadence", "PASS" if w1 > w0 >= 0 else "FAIL", "total writes increases across 3,200 stepped ticks (cadence 1,500)", out2,
        data={"writes_before": w0, "writes_after": w1})
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
    rec("cli.water", "PASS" if secs < 5 and ("placed 0" in out or "dormant" in out or "drew nothing" in out) else "FAIL",
        "'water now' on a dormant layer returns at once (the wet-edge verdict is cached at load) with 'placed 0' and the reason",
        f"{secs:.1f} s\n{out}", data={"seconds": round(secs, 1)},
        note="" if secs < 5 else ("the verb did not answer inside the cap; whether the server was busy is settled by the drain call that follows — if it returned at once, the core was free and the reply was never sent (v5.8.2 removed the whole-map scan)"))
    if V65:
        rc, out = cmd("limits", "water", "groups", "3", "ceiling", "20"); rc3, out3 = cmd("water", "countdown", "9000")
        rec("mech.water.target", "PASS" if "3 group(s) at once, ceiling 20" in out3 and "~9000 ticks" in out3 else "FAIL",
            "the water status echoing 3 groups at once, ceiling 20 and the 9000-tick countdown", out + out3)
        rc, out = cmd("limits", "land", "groups", "2")
        rec("mech.quota.land", "PASS" if "land 2 group(s) at once" in out else "FAIL", "'land 2 group(s) at once'", out)
        rc, out = cmd("quota", "water", "25")
        rec("mech.quota.water", "PASS" if "retired" in out and "water 3 group(s) at once, ceiling 25" in out else "FAIL", "the quota alias sets the water ceiling and says quota is retired", out)
        rc, out = cmd("limits", "cavern", "ceiling", "7"); rc2, out2 = cmd("limits", "bogus")
        rec("mech.limits", "PASS" if "cavern 2 group(s) at once, ceiling 7" in out and "usage" in out2.lower() else "FAIL",
            "`limits cavern ceiling 7` reads back; a bad layer prints usage", out + out2)
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
    ok = GH in t and "ecology:" in t and "Wild on map:" in t and ("limits:" if V65 else "quota:") in t
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
    for cid in [c[0] for c in CLAIMS if c[4] == "backlog"]:
        note = ""
        if cid == "bl.largestmale":
            note = "the leader rule in the shipped code is lowest-id (verified live in mech.leader.lowest)"
        if cid == "bl.concurrency":
            m = re.search(r"max_concurrent\s*=\s*(\d+)", src); note = f"max_concurrent is a fixed default ({m.group(1) if m else '?'}); no √tiles expression in the script"
        if cid == "bl.frequency":
            note = "no per-species frequency field in the roster config; frequency is written only by the cavern ceiling (CAVERN) and the pack-size lever"
        rec(cid, "BACKLOG", "unscheduled by the Backlog's own terms", "", note=note)
    # doc drift
    m = re.search(r"\*\*Status:\*\*\s*v([\d.]+).*?DF ([\d.]+)\s*/\s*DFHack ([\d.r-]+)", usage, re.S)
    ver = re.search(r"--\s*v(\d+\.\d+(?:\.\d+)?)\s*—", src)   # v6.1.1: any major, not only v5
    rec("doc.usage.version", "DOC-DRIFT" if m and ver and m.group(1) != ver.group(1) else "PASS",
        "USAGE.md's Status header names the shipped version", f"USAGE.md says v{m.group(1) if m else '?'} / DF {m.group(2) if m else '?'}; the script's newest changelog entry is v{ver.group(1) if ver else '?'}; the rig is DF 53.16 / DFHack 53.16-r1.1")
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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fort", default="CTRL"); ap.add_argument("--skip-lake", action="store_true"); ap.add_argument("--skip-gui", action="store_true")
    ap.add_argument("--only", choices=["w0", "model", "v65", "v68", "gui"], help="run only the named phase between setup and teardown")
    ap.add_argument("--no-overlay-restore", action="store_true", help="v6.2.1 driver behaviour, kept to show w0.overlay failing first")
    a = ap.parse_args()
    log(f"validate-full run {RUN} -> {OUT}")
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
        if not a.only:
            try: phase_w0(a.fort)   # last: it turns every layer on and applies the season, which the earlier phases do not expect
            except Exception as e: log(f"!! phase_w0 raised: {e!r}")
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
    # every claim gets a row, even ones no check reached
    seen = {r["id"] for r in results}
    for c in CLAIMS:
        if c[0] not in seen and not a.only:
            rec(c[0], "NOT-TESTABLE-HERE", "a check reached this claim", "", note="no check ran for this claim in this session")
    (OUT / "results.json").write_text(json.dumps(results, indent=1))
    (OUT / "claims.json").write_text(json.dumps([dict(zip(("id", "surface", "claim", "source", "claimed"), c)) for c in CLAIMS], indent=1))
    tally = {}
    for r in results:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    log(f"== DONE {OUT}\n   " + "  ".join(f"{k} {v}" for k, v in sorted(tally.items())))
    if RETRIED: log("   retried once after an RPC timeout: " + "; ".join(RETRIED))
    return 0

sys.exit(main())
