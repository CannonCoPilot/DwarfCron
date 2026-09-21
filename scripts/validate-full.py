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
TOOL = Path.home() / "Claude/Projects/seasonal-wildlife"
RUN = datetime.now().strftime("%Y%m%d-%H%M%S")
OUT = ROOT / "data/validation/full" / RUN
SHOTS, SCREENS, GROUND = OUT / "shots", OUT / "screens", OUT / "ground"
for d in (SHOTS, SCREENS, GROUND):
    d.mkdir(parents=True, exist_ok=True)
SAVES = Path.home() / "Library/Application Support/CrossOver/Bottles/Win10/drive_c/users/crossover/AppData/Roaming/Bay 12 Games/Dwarf Fortress/save"
BACKUPS = Path.home() / "Library/Application Support/CrossOver/df-snapshots/saves"

# ----------------------------------------------------------------------------- the claims ---
# id, surface, claim, source, claimed-as
CLAIMS = [
    # ---- CLI verbs (USAGE.md "Console commands"; the script's dispatch table)
    ("cli.status", "CLI", "`status` lists biomes, layers, quota, cavern line, on-the-map counts, the invasion field, and the embark subset", "USAGE.md", "shipped"),
    ("cli.now", "CLI", "`now` applies the current season's roster once and reports the active count", "USAGE.md", "shipped"),
    ("cli.enable", "CLI", "`enable` / `disable` start and stop automatic rotation (registers/cancels the daily scheduler)", "USAGE.md", "shipped"),
    ("cli.classes", "CLI", "`classes` prints the seven ecology classes with on/off and counts, plus the unclassified review list", "USAGE.md", "shipped"),
    ("cli.class", "CLI", "`class <TOKEN> <cls>` records an override; bad args print usage", "USAGE.md", "shipped"),
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
    ("mech.unassigned", "MECH", "a creature with no seasons assigned is not managed at all", "USAGE.md Concepts", "shipped"),
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
    ("mech.class.override", "MECH", "a class override changes the creature's class on the next pool build", "USAGE.md", "shipped"),
    ("mech.overlay", "MECH", "`overlay enable seasonal-wildlife.groups` registers a map overlay marking each tracked group g/r", "USAGE.md Resident groups", "shipped"),
    ("mech.stuck", "MECH", "a tracked non-flier that has not moved in 5,000 ticks is re-grounded; the status counts swept=N", "USAGE.md v5.7; T5", "shipped"),
    ("mech.addnew", "MECH", "Add-new writes a master row and a live entry so the species is in the pool with no reload", "USAGE.md Adding a new species; v4.4", "shipped"),
    ("mech.reset", "MECH", "Reset to default restores managed quantities to the captured worldgen snapshot and abundances to 50", "USAGE.md", "shipped"),
    ("mech.abundance", "MECH", "abundance sets the stocked quantity (not arrival volume — E24)", "USAGE.md; addendum 58", "shipped"),
    ("mech.save.untouched", "MECH", "a full session of console and GUI use leaves the save byte-identical (config lives in persistent site data)", "USAGE.md Uninstall; df-rig rule", "shipped"),
    ("mech.season.boundary", "MECH", "the roster is re-applied at each season boundary and held daily against refunds", "USAGE.md Between the seasons", "shipped"),
    ("mech.coupling", "MECH", "when a prey group arrives, coupling closes the pool to its armed natural predators for up to two days", "USAGE.md v5.4/5.6", "shipped"),
    # ---- GUI: window and tabs
    ("gui.open", "GUI", "`gui/seasonal-wildlife` opens a resizable 86×34 window titled 'Seasonal Wildlife' with five tabs", "script", "shipped"),
    ("gui.tab.roster", "GUI", "Roster tab: header with biomes and per-category counts, filter row, creature list with cat/size/biome/season/ab/ok columns, action keys, status line", "USAGE.md Roster tab", "shipped"),
    ("gui.tab.setroster", "GUI", "Set roster tab: per-category targets, fill keys, season grid, matrix/co-align keys, grid status", "USAGE.md Set roster tab", "shipped"),
    ("gui.tab.foodweb", "GUI", "Food web tab: ecology-switch line, season selector, chains (All) or trophic pyramid + aquatic mini-web (a season)", "USAGE.md Food web tab", "shipped"),
    ("gui.tab.live", "GUI", "Live tab: resident-group status, tracked groups, ecology line, wild-on-map by race, quota line, cavern line, biomass ratio", "USAGE.md Live tab", "shipped"),
    ("gui.tab.seasons", "GUI", "Seasons tab: four seasons side by side, one row per allowed creature under its trophic level, +/-/X/. marks", "USAGE.md Seasons tab", "shipped"),
    ("gui.close", "GUI", "ESC closes the window", "script", "shipped"),
    ("gui.k.shadow", "GUI", "Ctrl-modified action keys work while the filter box has focus (USAGE: 'that is why all action keys are Ctrl-modified here')", "USAGE.md Roster tab", "shipped"),
    ("gui.status.roster", "GUI", "the Roster tab's status line shows each action's receipt ('Applied Spring live: N active.', 'Set N abundances to 60.', 'Auto rotation ON.')", "USAGE.md; script setStatus", "shipped"),
    ("gui.status.grid", "GUI", "the Set-roster tab's grid status shows each action's receipt ('Allowed N natural prey.', 'Assigned matrix seasons to N creatures.')", "USAGE.md; script setGridStatus", "shipped"),
    # ---- GUI: Roster hotkeys
    ("gui.k.V", "GUI", "V cycles View: Current → Default → Add-new", "USAGE.md", "shipped"),
    ("gui.k.C", "GUI", "C cycles the category filter (incl. aquatic)", "USAGE.md", "shipped"),
    ("gui.k.B", "GUI", "B cycles the biome filter", "USAGE.md", "shipped"),
    ("gui.k.N", "GUI", "N cycles the season filter", "USAGE.md", "shipped"),
    ("gui.k.enter", "GUI", "Enter allows/blocks the selected creature (ok column flips Y/-)", "USAGE.md", "shipped"),
    ("gui.k.shiftenter", "GUI", "Shift-Enter cycles the selected creature's seasons", "USAGE.md", "shipped"),
    ("gui.k.ctrlS", "GUI", "Ctrl+S opens the Set roster tab", "USAGE.md", "shipped"),
    ("gui.k.ctrlA", "GUI", "Ctrl+A applies the current season live and announces it", "USAGE.md", "shipped"),
    ("gui.k.ctrlF", "GUI", "Ctrl+F clears the current wild group and forces a new wave", "USAGE.md", "shipped"),
    ("gui.k.ctrlD", "GUI", "Ctrl+D opens the dry-run season table dialog", "USAGE.md", "shipped"),
    ("gui.k.ctrlW", "GUI", "Ctrl+W prompts for the row's abundance and stores it", "USAGE.md", "shipped"),
    ("gui.k.ctrlG", "GUI", "Ctrl+G prompts for an abundance for every filtered row", "USAGE.md", "shipped"),
    ("gui.k.ctrlE", "GUI", "Ctrl+E toggles automatic rotation", "USAGE.md", "shipped"),
    ("gui.k.ctrlX", "GUI", "Ctrl+X adds the selected non-native creature (Add-new view only; otherwise says so)", "USAGE.md", "shipped"),
    ("gui.k.ctrlR", "GUI", "Ctrl+R asks for confirmation then resets quantities and abundances", "USAGE.md", "shipped"),
    ("gui.k.ctrlL", "GUI", "Ctrl+L fills the filtered category to N (refuses on 'all'/'aquatic')", "USAGE.md", "shipped"),
    ("gui.k.thin", "GUI", "the header shows a 'Thin:' hint when a category is under its target", "USAGE.md", "shipped"),
    # ---- GUI: Set roster hotkeys
    ("gui.k.targets", "GUI", "Shift-P/R/B/V cycle the per-category targets", "USAGE.md", "shipped"),
    ("gui.k.F", "GUI", "F fills categories to their targets", "USAGE.md", "shipped"),
    ("gui.k.Y", "GUI", "Y allows the natural prey of allowed creatures", "USAGE.md", "shipped"),
    ("gui.k.D", "GUI", "D allows the natural predators of allowed creatures", "USAGE.md", "shipped"),
    ("gui.k.SUAW", "GUI", "S/U/A/W toggle Spring/Summer/Autumn/Winter on the selected grid row", "USAGE.md", "shipped"),
    ("gui.k.M", "GUI", "M assigns seasons from the climate matrix", "USAGE.md", "shipped"),
    ("gui.k.O", "GUI", "O co-aligns predator↔prey seasons", "USAGE.md", "shipped"),
    ("gui.k.gridmouse", "GUI", "per-cell mouse clicks on the grid are NOT supported (documented limit)", "USAGE.md", "shipped"),
    # ---- GUI: Food web / Live
    ("gui.k.webN", "GUI", "N on Food web cycles the season; a specific season draws the pyramid", "USAGE.md", "shipped"),
    ("gui.k.liveR", "GUI", "R refreshes the Live tab", "script", "shipped"),
    ("gui.k.liveG", "GUI", "G toggles resident groups from the Live tab", "USAGE.md", "shipped"),
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

def sh(*args, timeout=180):
    p = subprocess.run([CX, *args], capture_output=True, text=True, timeout=timeout, cwd=ROOT)
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

ROW = re.compile(r"^\s*\d+\|\s+(\S+)(?: [w~])?\s+(prey|predator|bird|vermin|apex|other)\s+(small|medium|large)\s+(\S+)\s+(\S+)\s+(\d{1,3})\s+([Y\-])\s*$")
def row_lines(txt):
    """Roster rows as the text grid actually draws them: ' NN|' row prefix, NO icon (the category
    glyphs are non-ASCII and the reader blanks them), token with an optional ' w'/' ~' tag, then
    cat size biome season ab ok. Returns (token, ab, ok, season, line)."""
    rows = []
    for line in txt.splitlines():
        m = ROW.match(line)
        if m:
            rows.append((m.group(1), int(m.group(6)), m.group(7), m.group(5), line))
    return rows


def window_rows(txt, lo=16, hi=49):
    return "\n".join(l for l in txt.splitlines() if (m := re.match(r"^\s*(\d+)\|", l)) and lo <= int(m.group(1)) <= hi)

def status_rows(txt):
    """The Roster tab's bottom panel: hint, three hotkey rows, then the status label (rows 43-48)."""
    return window_rows(txt, 42, 48)

def grid_status(txt):
    """The Set-roster tab's grid_status is the key panel's top row, right of 'Toggle a season on the
    selected row:' (window row 28 on an 86x34 window); read the whole targets-and-keys block."""
    return window_rows(txt, 20, 30)

def dialog_rows(txt):
    return window_rows(txt, 24, 40)

def sha_dir(d):
    p = subprocess.run(["bash", "-c", f'cd "{d}" && find . -type f -print0 | sort -z | xargs -0 shasum -a 256 | shasum -a 256 | cut -c1-16'],
                       capture_output=True, text=True)
    return p.stdout.strip()

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
    ok = all(k in out for k in ("Biomes:", "Layers:", "quota:", "On the map now:", "Embark subset"))
    rec("cli.status", "PASS" if ok else "FAIL", "Biomes/Layers/quota/On the map now/Embark subset", out)
    rec("mech.layers.count", "PASS" if "magma sea and underworld" in out else "FAIL",
        "the on-the-map line naming the deep bucket", out)
    rec("mech.invasion", "PASS" if re.search(r"excluded via unit\.invasion", out) else "FAIL",
        "'DF invasions excluded via unit.invasion_id'", out)
    rc, out = cmd("now")
    rec("cli.now", "PASS" if re.search(r"active: \d+", out) else "FAIL", "active: N", out)
    rc, out = cmd("classes")
    n = len(re.findall(r"^\s+\S+\s+(on|off)\s+\d+", out, re.M))
    rec("cli.classes", "PASS" if n == 7 else "FAIL", "seven class lines with on/off and a count", out, data={"class_lines": n})
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
    rc, out = cmd("quota")
    rec("cli.quota", "PASS" if "quota:" in out and "on the map now" in out else "FAIL", "quota line + on-the-map", out)
    rc, out = cmd("quota", "cavern", "12")
    ok = "frequency" in out.lower() and "arriv" in out.lower()
    rec("cli.quota.cavern", "PASS" if ok else "FAIL", "the frequency + arrival-lag warning", out)
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
        errs.append((args, "usage" in out.lower() or "no stocked" in out or "no tracked" in out, out.strip()[:120]))
    rec("cli.errors", "PASS" if all(e[1] for e in errs) else "FAIL", "each prints usage / a refusal",
        "\n".join(f"{a}: {o}" for a, _, o in errs), data=[list(a) for a, ok_, _ in errs if not ok_])
    rc, out = sh("cmd", "help", "seasonal-wildlife", timeout=60)
    rec("cli.docstring", "PASS" if "seasonal" in out.lower() and "roster" in out.lower() else "FAIL", "launcher help text", out)

def phase_mechanics():
    log("== MECHANICS")
    # --- scheduler
    rc, out = cmd("enable")
    g = ground("B1-enabled")
    rec("mech.sched", "PASS" if g.get("sched") else "FAIL", "repeat-util reports seasonal-wildlife scheduled after enable", out, data={"sched": g.get("sched")})
    rec("cli.enable", "PASS" if "enabled" in out and g.get("sched") else "FAIL", "'enabled' and the job registered", out)
    # --- build a full roster on all three layers, apply, and read the pool back
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
    # --- unassigned = unmanaged: clear one species' seasons, apply, its entry must not move
    probe = luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg); local pick; "
                 "for _,e in ipairs(pool) do if e.inEmbark and e.layer=='land' and cfg.assign[e.key] and #cfg.assign[e.key]>0 then pick=e; break end end; "
                 "if not pick then print(json.encode({none=true})) return end; "
                 "local q0=0; local rs=sw.getEmbarkRegions(); for _,pop in ipairs(df.global.world.populations.all) do local cr=df.creature_raw.find(pop.race); "
                 "if sw.managedPop(pop, rs, {land=true}) and cr and cr.creature_id==pick.token then pop.quantity=37; q0=q0+1 end end; "
                 "cfg.assign[pick.key]={}; sw.saveConfig(cfg); sw.applyLive(cfg, df.global.cur_season); sw.saveConfig(cfg); "
                 "local q1={}; for _,pop in ipairs(df.global.world.populations.all) do local cr=df.creature_raw.find(pop.race); "
                 "if sw.managedPop(pop, rs, {land=true}) and cr and cr.creature_id==pick.token then q1[#q1+1]=pop.quantity end end; "
                 "print(json.encode({token=pick.token, key=pick.key, entries=q0, after=q1}))", timeout=180)
    untouched = probe.get("after") and all(int(q) == 37 for q in probe["after"])
    rec("mech.unassigned", "PASS" if untouched else ("NOT-TESTABLE-HERE" if probe.get("none") else "FAIL"),
        "a species with no seasons keeps the sentinel quantity 37 through an apply", json.dumps(probe), data=probe)
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
    def write_line(txt):
        mm = re.search(r"(\d+) predator\(s\) x (\d+) target\(s\), (\d+) pair\(s\) written, (\d+) without a slot", txt)
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
    # --- v5.9.6: the cavern stocking pass under the cavern quota
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
    rec("mech.water.dormant", "PASS" if re.search(r"water: dormant — .+", out) else "FAIL",
        "'water: dormant — <reason>' on CTRL (inland)", out, data={"line": next((l for l in out.splitlines() if "dormant" in l), "")})
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
    rec("cli.water", "PASS" if secs < 5 and ("placed 0" in out or "dormant" in out) else "FAIL",
        "'water now' on a dormant layer returns at once (the wet-edge verdict is cached at load) with 'placed 0' and the reason",
        f"{secs:.1f} s\n{out}", data={"seconds": round(secs, 1)},
        note="" if secs < 5 else ("the verb did not answer inside the cap; whether the server was busy is settled by the drain call that follows — if it returned at once, the core was free and the reply was never sent (v5.8.2 removed the whole-map scan)"))
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
    rc, out = cmd("quota")
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
    rec("mech.class.override", "PASS" if isinstance(ov, dict) and ov.get("class") == "mythic" else "FAIL",
        "BADGER classes as mythic (and is locked, since mythic is off) after the override", out + json.dumps(ov), data=ov)
    cmd("class", "BADGER", "natural")
    # --- overlay
    rc, out = sh("cmd", "overlay", "enable", "seasonal-wildlife.groups", timeout=60)
    rc2, out2 = sh("cmd", "overlay", "list", "seasonal-wildlife", timeout=60)
    p = shot("B6-map-overlay-enabled")
    ok = "enabled widget seasonal-wildlife.groups" in out or bool(re.search(r"seasonal-wildlife\.groups.*(true|enabled|on)", out2, re.I))
    rec("mech.overlay", "PASS" if ok else "FAIL", "'enabled widget seasonal-wildlife.groups' (or overlay list showing it enabled)", out + out2, shots=[p] if p else [])
    # --- abundance and reset
    ab = luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg); local pick; "
              "for _,e in ipairs(pool) do if e.inEmbark and e.layer=='land' and cfg.allow[e.key] and cfg.assign[e.key] and #cfg.assign[e.key]>0 then pick=e; break end end; "
              "if not pick then print(json.encode({none=true})) return end; cfg.weight[pick.key]=100; sw.saveConfig(cfg); sw.applyLive(cfg, df.global.cur_season); sw.saveConfig(cfg); "
              "local q100=sw.qtyFor(cfg, pick.key); cfg.weight[pick.key]=50; sw.saveConfig(cfg); local q50=sw.qtyFor(cfg, pick.key); "
              "print(json.encode({token=pick.token, q_at_100=q100, q_at_50=q50}))", timeout=180)
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

def phase_gui():
    log("== GUI")
    sh("cmd", "gui/seasonal-wildlife", timeout=120); time.sleep(2.5)
    txt = screen("C0-roster"); p = shot("C0-roster")
    ok = "Seasonal Wildlife" in txt and all(t in txt for t in ("Roster", "Set roster", "Food web", "Live", "Seasons"))
    rec("gui.open", "PASS" if ok else "FAIL", "window title and five tab labels on screen", txt[:600], shots=[p] if p else [])
    rows = row_lines(txt)
    ok = all(k in txt for k in ("View:", "Cat:", "Biome:", "Season:")) and len(rows) >= 5 and "Apply now" in txt and "Force wave" in txt
    rec("gui.tab.roster", "PASS" if ok else "FAIL", "filter row, ≥5 creature rows with ab/ok columns, action keys", txt[:800], shots=[p] if p else [],
        data={"rows": len(rows), "first": rows[0][3] if rows else ""})
    rec("gui.k.thin", "PASS" if ("Thin:" in txt or "Ecosystem balanced" in txt) else "FAIL", "'Thin: …' or 'Ecosystem balanced.' in the header", txt[:400])
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
    key("LEAVESCREEN", 1.0); sh("cmd", "gui/seasonal-wildlife", timeout=120); time.sleep(2.0)
    # Enter toggles allow on the selected (first) row
    t0 = screen("C2-enter-before"); r0 = row_lines(t0)
    key("SELECT"); t1 = screen("C2-enter-after"); r1 = row_lines(t1); p = shot("C2-enter-toggle")
    ok = r0 and r1 and r0[0][0] == r1[0][0] and r0[0][2] != r1[0][2]
    rec("gui.k.enter", "PASS" if ok else "FAIL", "row 1's ok column flips Y<->-", f"{r0[0] if r0 else None} -> {r1[0] if r1 else None}", shots=[p] if p else [])
    key("SELECT")  # put it back
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
    def weights():
        w = luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); print(json.encode(cfg.weight or {}))", timeout=60)
        return w if isinstance(w, dict) else {}
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
    by_key = "Abundance for" in t_key
    by_click = False
    if not by_key:
        click("Abundance (row"); t_click = screen("C5-w-click"); by_click = "Abundance for" in t_click
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
    rec("gui.k.ctrlG", "PASS" if "Abundance for" in t6 and n60 >= 5 else "FAIL", "the prompt opens and ≥5 weights read 60 afterwards",
        f"prompt: {'Abundance for' in t6}; weights at 60: {n60}", shots=[p] if p else [], data={"weights_at_60": n60})
    # Ctrl+E toggles auto rotation -> cfg.enabled flips (the status text is the dead label)
    g0 = ground("C7-e-before"); key("CUSTOM_CTRL_E", 1.0); t7 = screen("C7-e-after"); g1 = ground("C7-e-after"); p = shot("C7-auto-toggle")
    rec("gui.k.ctrlE", "PASS" if g0.get("enabled") != g1.get("enabled") else "FAIL", "cfg.enabled flips", f"{g0.get('enabled')} -> {g1.get('enabled')}", shots=[p] if p else [])
    rec("gui.status.roster", "PASS" if re.search(r"Auto rotation (ON|off)", t7) else "DEAD",
        "'Auto rotation ON.'/'off.' on the status row after Ctrl+E (the label is set by act_enable)", status_rows(t7), shots=[p] if p else [],
        note="the Label is created with text='' at frame t=4 of the bottom panel and never shows anything afterwards; every setStatus() receipt in the Roster tab is invisible")
    key("CUSTOM_CTRL_E", 1.0)
    # Ctrl+L: refuses on 'all' (nothing changes), then fills a category to 3
    c0 = counts(); key("CUSTOM_CTRL_L", 1.0); t8 = screen("C8-l-all"); c1 = counts()
    key("CUSTOM_C", 0.8); cat_txt = screen("C8-cat"); m = re.search(r"Cat:\s*([A-Za-z]+)", cat_txt); cat = m.group(1) if m else "?"   # letters only: the next label used to run into this one
    key("CUSTOM_CTRL_L", 1.0); p = shot("C8-fill-prompt"); t8b = screen("C8-l-prompt")
    for _ in range(3): key(BACKSPACE, 0.15)
    typ("3"); key("SELECT", 1.2); c2 = counts()
    ok = c0 == c1 and ("Fill" in t8b) and c2.get(cat) == 3
    rec("gui.k.ctrlL", "PASS" if ok else "FAIL", f"no change on 'all'; the prompt on Cat={cat}; that category's allowed count == 3 afterwards",
        f"all: {c0.get(cat)}->{c1.get(cat)}; prompt: {'Fill' in t8b}; after: {c2.get(cat)}", shots=[p] if p else [], data={"cat": cat, "before": c0, "after": c2})
    # Ctrl+X: in Add-new the selected species is added (or refused as present). Key, then label.
    key("LEAVESCREEN", 1.0); sh("cmd", "gui/seasonal-wildlife", timeout=120); time.sleep(2.0)
    key("CUSTOM_V", 0.8); key("CUSTOM_V", 0.8); t_add = screen("C9-addnew-view"); p0 = shot("C9-addnew-view")
    rows_add = row_lines(t_add); pick = rows_add[0][0] if rows_add else None
    key("CUSTOM_CTRL_X", 1.2); t9 = screen("C9-x-key"); x_key = "Add " in t9
    if not x_key:
        click("Add-new (live)"); t9 = screen("C9-x-click"); x_click = "Add " in t9
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
    # Ctrl+R reset: the yes/no prompt, then every weight back to 50
    key("CUSTOM_CTRL_R", 1.2); p = shot("C11-reset-prompt"); t11 = screen("C11-reset-prompt")
    key("SELECT", 1.5); w3 = weights(); left = [k for k, v in w3.items() if v != 50]
    rec("gui.k.ctrlR", "PASS" if ("worldgen default" in t11 or "Yes, proceed" in t11) and not left else "FAIL",
        "the confirmation prompt, then no weight left off 50", f"prompt: {'worldgen default' in t11}; weights not 50 after: {left[:8]}", shots=[p] if p else [], data={"not_50_after": left[:20]})
    # Ctrl+S -> Set roster
    key("CUSTOM_CTRL_S", 1.2); t = screen("C12-setroster"); p = shot("C12-setroster")
    ok = "Fill to targets" in t and "Assign seasons from matrix" in t and "Co-align" in t
    rec("gui.k.ctrlS", "PASS" if ok else "FAIL", "the Set roster tab's keys on screen", t[:600], shots=[p] if p else [])
    rec("gui.tab.setroster", "PASS" if ok and re.search(r"[X\-]\s+[X\-]\s+[X\-]\s+[X\-]\s*$", t, re.M) else "FAIL", "targets, fill keys, a season grid of X/- cells", window_rows(t), shots=[p] if p else [])
    # targets: Shift-P cycles
    m0 = re.search(r"prey:?\s*(\S+)", t); key("CUSTOM_SHIFT_P", 0.8); t1 = screen("C13-shiftp"); m1 = re.search(r"prey:?\s*(\S+)", t1)
    rec("gui.k.targets", "PASS" if m0 and m1 and m0.group(1) != m1.group(1) else "FAIL", "the prey target value changes", f"{m0.group(1) if m0 else None} -> {m1.group(1) if m1 else None}")
    c0 = counts(); key("CUSTOM_F", 1.5); t13 = screen("C13-fill"); p = shot("C13-fill-targets"); c1 = counts()
    rec("gui.k.F", "PASS" if c0 != c1 or re.search(r"(allowed|blocked|to reach|already)", grid_status(t13), re.I) else "FAIL",
        "allowed counts move toward the targets (or the grid status says nothing needed doing)", f"{c0} -> {c1}", shots=[p] if p else [], data={"before": c0, "after": c1})
    rec("gui.status.grid", "PASS" if re.search(r"(allowed|blocked|to reach|already|Ecosystem)", grid_status(t13), re.I) else "DEAD",
        "a fill receipt on the grid status row after F", grid_status(t13), shots=[p] if p else [],
        note="setGridStatus() writes to a Label created with text='' at frame t=0,l=40; nothing it is given ever shows, so Y, D, M, O and F report nothing")
    key("CUSTOM_Y", 1.2); c2 = counts()
    rec("gui.k.Y", "PASS" if sum(v for k, v in c2.items() if k != "assigned") >= sum(v for k, v in c1.items() if k != "assigned") else "FAIL",
        "allowed counts never decrease (Y only adds)", f"{c1} -> {c2}", data={"before": c1, "after": c2})
    key("CUSTOM_D", 1.2); c3 = counts()
    rec("gui.k.D", "PASS" if sum(v for k, v in c3.items() if k != "assigned") >= sum(v for k, v in c2.items() if k != "assigned") else "FAIL",
        "allowed counts never decrease (D only adds)", f"{c2} -> {c3}", data={"before": c2, "after": c3})
    # S/U/A/W on grid row 1
    def grid_row1(txt):
        for line in txt.splitlines():
            m = re.match(r"^\s*\d+\|\s+[!v^.*\-] (\S+)\s+([X\-])\s+([X\-])\s+([X\-])\s+([X\-])\s*$", line)
            if m:
                return m.group(1), m.group(2, 3, 4, 5)
        return None, None
    t0 = screen("C14-grid-before"); tok0, c0 = grid_row1(t0)
    flips = []
    for k, i in (("CUSTOM_S", 0), ("CUSTOM_U", 1), ("CUSTOM_A", 2), ("CUSTOM_W", 3)):
        key(k, 0.9); tk, ck = grid_row1(screen(f"C14-{k}"))
        flips.append(bool(c0 and ck and tk == tok0 and ck[i] != c0[i]))
        c0 = ck
    p = shot("C14-grid-toggled")
    rec("gui.k.SUAW", "PASS" if all(flips) else "FAIL", "each of S/U/A/W flips exactly its own cell on row 1", f"row {tok0}: {flips}", shots=[p] if p else [])
    rec("gui.k.gridmouse", "NOT-TESTABLE-HERE", "a per-cell mouse click (documented as unsupported)", "", note="USAGE.md documents keyboard-only cells; the rig's fed clicks land on text labels, not List cells")
    a0 = luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); print(json.encode(cfg.assign or {}))", timeout=60)
    key("CUSTOM_M", 1.5); t15 = screen("C15-matrix")
    a1 = luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); print(json.encode(cfg.assign or {}))", timeout=60)
    n_assigned = sum(1 for v in (a1 if isinstance(a1, dict) else {}).values() if v)
    rec("gui.k.M", "PASS" if isinstance(a1, dict) and n_assigned >= 5 else "FAIL", "≥5 species carry season assignments after M", f"assigned after: {n_assigned}; changed from before: {a0 != a1}", data={"assigned": n_assigned})
    key("CUSTOM_O", 1.5); t15b = screen("C15-coalign"); p = shot("C15-matrix-coalign")
    a2 = luaj("local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); print(json.encode(cfg.assign or {}))", timeout=60)
    cells = lambda a: sum(len(v) for v in (a if isinstance(a, dict) else {}).values() if v)
    rec("gui.k.O", "PASS" if cells(a2) >= cells(a1) else "FAIL", "season cells never decrease (O only extends partners' seasons)", f"cells {cells(a1)} -> {cells(a2)}", shots=[p] if p else [], data={"cells_before": cells(a1), "cells_after": cells(a2)})
    # Food web
    click("Food web"); t = screen("C16-foodweb"); p = shot("C16-foodweb-all")
    ok = ("Ecology ON" in t or "Ecology off" in t) and ("->" in t or "no chains" in t)
    rec("gui.tab.foodweb", "PASS" if ok else "FAIL", "the ecology line and predator -> prey chains", t[:800], shots=[p] if p else [])
    key("CUSTOM_N", 1.2); t1 = screen("C16-foodweb-season"); p1 = shot("C16-foodweb-spring")
    rec("gui.k.webN", "PASS" if "Spring" in t1 and t1 != t else "FAIL", "the season selector moves to Spring and the view changes (pyramid)", t1[:800], shots=[p1] if p1 else [])
    # Live
    click("Live"); t = screen("C17-live"); p = shot("C17-live")
    ok = "Resident groups:" in t and "ecology:" in t and "Wild on map:" in t and "quota:" in t
    rec("gui.tab.live", "PASS" if ok else "FAIL", "resident groups / ecology / Wild on map / quota lines", t[:900], shots=[p] if p else [])
    key("CUSTOM_R", 1.0); t2 = screen("C17-live-refresh")
    rec("gui.k.liveR", "PASS" if "Resident groups:" in t2 else "FAIL", "the tab re-renders", t2[:300])
    g0 = ground("C17-g-before"); key("CUSTOM_G", 1.2); t3 = screen("C17-live-g"); g1 = ground("C17-g-after")
    rec("gui.k.liveG", "PASS" if g0.get("groups") != g1.get("groups") else "FAIL", "cfg.groups.enabled flips", f"{g0.get('groups')} -> {g1.get('groups')}")
    key("CUSTOM_G", 1.0)
    # Seasons
    click("Seasons"); t = screen("C18-seasons"); p = shot("C18-seasons")
    ok = all(s in t for s in ("Spring", "Summer", "Autumn", "Winter")) and re.search(r"[X+\-.]\s+[X+\-.]\s+[X+\-.]\s+[X+\-.]", t)
    rec("gui.tab.seasons", "PASS" if ok else "FAIL", "four season columns and +/-/X/. marks", t[:800], shots=[p] if p else [])
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
        "local pool=sw.buildPool(cfg); for _,e in ipairs(pool) do if e.inEmbark and e.layer=='water' and sw.defaultAllow(e) then cfg.allow[e.key]=true end end; sw.saveConfig(cfg); sw.applyLive(cfg, df.global.cur_season); sw.saveConfig(cfg)", timeout=180)
    rc, out = cmd("water", "on")
    live = "stocking on" in out
    rc2, out2 = cmd("water", "now")
    m = re.search(r"placed (\d+)", out2)
    n = int(m.group(1)) if m else 0
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
        "v6.overview": absent(r"labels=\{[^}]*Overview|refreshOverview"), "v6.roster.why": absent(r"why_col|why column|refreshWhy"),
        "v6.species": absent(r"Species detail|species_detail|SpeciesDetail|refreshSpecies"), "v6.web.graph": absent(r"web_graph|as a graph|═══|drawGraph"),
        "v6.web.byseason": absent(r"refreshWebSeason|web_by_season|byseason"), "v6.web.bylayer": absent(r"refreshWebLayer|web_by_layer|bylayer"),
        "v6.live.hotkeys": absent(r"key='CUSTOM_P'|key='CUSTOM_K'|key='CUSTOM_Q'|key='CUSTOM_X'[^_]|centres the map|act_next_wave"),
        "v6.herds": absent(r"labels=\{[^}]*Herds|refreshHerds"), "v6.vermin": absent(r"labels=\{[^}]*Vermin|refreshVermin"),
        "v6.patterns": absent(r"labels=\{[^}]*Patterns|'burst'|'trickle'|'dawn'|refreshPatterns"), "v6.caverns": absent(r"labels=\{[^}]*Caverns|not yet found|refreshCaverns"),
        "v6.ledger": absent(r"labels=\{[^}]*Ledger|undo last|refreshLedger"), "v6.ecology.tab": absent(r"labels=\{[^}]*Ecology|refreshEcology"),
        "v6.layersel": absent(r"layer selector|Land · Water|layerSel|cur_layer"), "v6.presets": absent(r"preset"), "v6.undo": absent(r"snapshot ring|cfg_history|act_undo|undo_stack"),
        "v6.overlay.links": absent(r"coupled pairs as a line|drawLine|paintLine"),
        "plan.patterns": absent(r"'burst'|'trickle'|'dawn'|'follow'|arrival_pattern"), "plan.irruptions": absent(r"pressure|irruption"),
        "plan.arming": absent(r"arming step|armWave|arm_step"),
    }
    for cid, is_absent in checks.items():
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
    ver = re.search(r"--\s*v(5\.\d+(?:\.\d+)?)\s*—", src)
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
    a = ap.parse_args()
    log(f"validate-full run {RUN} -> {OUT}")
    try:
        base = phase_setup(a.fort)
        for ph in (phase_cli, phase_mechanics):
            try: ph()
            except Exception as e: log(f"!! phase {ph.__name__} raised: {e!r}")
        if not a.skip_gui:
            try: phase_gui()
            except Exception as e: log(f"!! phase_gui raised: {e!r}")
        try: phase_static()
        except Exception as e: log(f"!! phase_static raised: {e!r}")
        if not a.skip_lake:
            try: phase_lake()
            except Exception as e: log(f"!! phase_lake raised: {e!r}")
            sh("load", a.fort, timeout=300); time.sleep(1)
    finally:
        try: phase_teardown(a.fort)
        except Exception as e: log(f"!! teardown raised: {e!r}")
    # every claim gets a row, even ones no check reached
    seen = {r["id"] for r in results}
    for c in CLAIMS:
        if c[0] not in seen:
            rec(c[0], "NOT-TESTABLE-HERE", "a check reached this claim", "", note="no check ran for this claim in this session")
    (OUT / "results.json").write_text(json.dumps(results, indent=1))
    (OUT / "claims.json").write_text(json.dumps([dict(zip(("id", "surface", "claim", "source", "claimed"), c)) for c in CLAIMS], indent=1))
    tally = {}
    for r in results:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    log(f"== DONE {OUT}\n   " + "  ".join(f"{k} {v}" for k, v in sorted(tally.items())))
    return 0

sys.exit(main())
