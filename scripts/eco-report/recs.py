"""Section 20's table: every recommendation, its evidence, its strength, and where it stands (1 Oct 2026; revised after the
user's review Parts 1 and 2: rulings applied, v7.1 build state from the stream notes on seasonal-wildlife v7.1 fce7d68)."""
from mdlite import inline

S69, S70, S70P, S71, RULED = ("v6.9 (released)", "v7.0 (validated, pushed, not released)", "v7.0 (validator covers part)",
                              "v7.1 (built, untested)", "Ruled; v7.1 (built, untested)")
RECS = [
    ("Filter the relation write through eats(): reach, size, class", "58% of written pairs failed the tool's own rules; shark × deer and wolf × pike made 0 attacks", "40-cell matrix, 1 run each", S69, "The write keeps only pairs the predator can reach"),
    ("Arm every non-BENIGN carnivore; LARGE_PREDATOR decides nothing measured", "The coyote (not LARGE_PREDATOR) killed deer; fox, badger and a BENIGN wolf never attacked", "1 run per cell", S69 + "; " + S70, "LARGE_PREDATOR stays a guild and cohesion label; its pack-take ×1.5 has no measured basis"),
    ("Bring water-layer units into the ecology, realm by habitat", "Alligators and crocodiles took 4–5 of 8 land prey from the water; sharks took seals in water", "1 run per cell; REACH 2 reps", S69, "Water units in the surface realm, amphibious both ways"),
    ("Guard pairings where prey outguns the predator", "Elephants killed 28% of wolves; capybaras (non-BENIGN, wolf-sized) killed 5 of 5; prey mass from deer to buffalo did not raise wolf deaths", "R3 re-analysis, 667 pairings, 1–4 reps per block", S70, "5% pack-mass floor on the group present, outgun warning in the builder. A harm screen would key on ~50–100× mass and non-BENIGN prey; PMH1 tests it"),
    ("Season gate: the tool's deal, not the raw NO_<season>", "NO_SPRING kangaroo 0 of 19 spring waves; cleared NO_WINTER groundhog 40 of 57", "1 and 2 runs", S70 + "; ruled (R29)", "v7.0 clears the flags on managed species and restores them on off; v7.1 forces seasons_own on"),
    ("Scavenging as the tool's own walk-and-eat, at a natural pace", "Nothing in DF eats remains; v7.0's pass cleared land and water carcasses in ~2,400 ticks, far faster than nature", "2 reps", RULED, "R18 natural cadence, R17/R42 swimmers incl. sharks, R16 rig causes, attribution"),
    ("Keep curious beasts as thieves, then let the thief stay", "18 of 18 placed bears and raccoons left; DF zeroes the countdown at the theft; flags off kept 0 of 10 leaving", "1 run per cell", RULED, "R30: after the theft the tool clears that unit's curious flags and resets its countdown"),
    ("Drop wild-only combat alerts", "Wild-only alerts dropped, fights with dwarves kept, safe across a reload", "Prototype, one fight per case", S69, "On by default; Panel switch; humanoids always alert"),
    ("Exhaustion watcher and same-guild replacement", "An emptied entry stopped the species; the replacement arrived 2,090 ticks later", "1 run", S69, ""),
    ("Groups at once per layer, by map size or one fixed cap", "+1 group at 5×5 and 6×6; Little's law held the rest near 2–3", "2 reps, counterbalanced", RULED, "R7 per-layer caps always, formula|fixed toggle; R31 adaptive release clock; R44 caverns 5; R45 water like land"),
    ("FREQUENCY ladder targets units and the trophic pyramid; no apex step", "Shares proportional within a few points; ×0.5 cut predators to ~2%; the apex step was too low a target", "F1 1 run; SW4 2 reps", RULED, "R9 pyramid targets, R34 apex by placement and stock, R57 v2.2 port, R59 units"),
    ("Pelagic slot on every ocean map; prey pulls predators in", "OCEAN2's slot came out empty: ocean life rides land-layer entries the water roster never read; the survey stopped at the top level", "Survey, code", RULED, "R14, R59; stranding guard; R22 column depth"),
    ("Leader = largest adult male; no male, no leader; panic on loss", "Leaders hold herds, packs, flocks, schools and pods; which member leads made no consistent difference", "L1/L2 1 run; COH 2 reps", RULED, "R32; wet leaders for schools and pods"),
    ("Guild-first roster builder, v2.2", "0% isolated over 54,560 offline builds; ran on CTRL, BOATS, OCEAN2", "Offline + S8, 2 reps", RULED, "R57 port; R13/R26 animal-person and giant odds; R41 ×3 bonus kept and fixed; R50 flying layer"),
    ("Realm table as optional data", "The raws hold no geography", "Desk", RULED, "R57; realm table verb; never run on the rig"),
    ("Solitary-hunter package, kept", "Placed-prey kills 14 → 29 over 10 seasons (p = 0.07), order-confounded; no SNEAK level but 10 ever tried", "10 runs per arm", RULED, "R8, R58: keep; v7.1 profiles 0–20 on caste and unit with readback; post-alpha SNK tests"),
    ("Manage GOOD/EVIL wildlife on matching regions", "GOODF and EVILF manage their own alignment and lock the other", "1 run each", S70, "Plus the Vermin-tab leak, cavern GOOD/EVIL and FANCIFUL fixes"),
    ("Cavern civ races hunt and are prey; never write forgotten beasts or megabeasts", "Builder: 20 singletons to 0", "Offline", S70 + "; " + S71, "v7.0's civ_hunt and civ_prey never fired (pool entries lacked the civ flag); v7.1 fixes it; ANT_MAN and cavern vermin-men in the civ set (R61)"),
    ("Sweep DF's own PREDATOR_OR_PREY between managed wildlife the roster doesn't pair", "DF aims placed and released units at arrivals (RELS)", "2 reps", S70, "With a count of pairs DF writes back"),
    ("Fishing: bears only, made to work", "Grizzlies and tigers 0 attacks on pike in 4 runs, wolves 0 (FSH2, FISH)", "2 reps", RULED, "R33, R43: bears fish by default (lure, run season); polar bears swim"),
    ("Empty relation slots write NONE (−1)", "SLOTV: DF's empty value is −1; STRANGER is never its default", "1 run", S70, "The rig's own spawn wrote STRANGER; the v7.1 harness writes −1"),
    ("Vermin classes, gobble writes and foraging", "Written class works on the eater (VRM2) and on the vermin (VRM4)", "2 reps each, two vermin species", RULED, "R27 GOBBLE_RULES kept, R51 edge table, R21 foraging; R20 a wider vermin suite at test"),
    ("Domestic animals as prey", "With the switch on, wolves took a cavy each run; dogs killed a wolf each run", "2 reps", S70, "Off by default: it costs the player animals"),
    ("Ecology cadence 3,000; nudge off", "SW1: no effect visible; the nudge never fired", "4 reps, vacuous for the nudge", RULED, "R37, R38"),
    ("pack_sneak 0 and the ×3 removal", "SW2 and SW7 could not test them", "Vacuous / weak", "Rejected by your rulings", "R8, R40, R41: SNEAK and the ×3 bonus stay"),
    ("Cap animal-person group size in caverns", "Plump helmet men 54 and 180 a season on BOATS, ~15 per wave", "2 reps", RULED, "R35: cap 5, lifted during an irruption"),
    ("Add invasive places SAVAGE species itself on calm maps", "DF never drew the smilodon in a season (1 species, 1 fort)", "2 runs", RULED, "R36"),
    ("Irruption replaces the disabled cavern invasion", "DF's invasions are off in its code; no flag raised one (E23b–e)", "Code, 2 reps", RULED, "R4, R5, R6, R10: IRRUPT v2"),
]


def table():
    chip = {S71: "medium", RULED: "medium", S70P: "medium"}
    head = "<thead><tr><th>Change</th><th>Evidence</th><th>Strength</th><th>Status</th><th>Notes</th></tr></thead>"
    rows = []
    for ch, ev, st, status, note in RECS:
        rows.append(f"<tr><td><b>{inline(ch)}</b></td><td>{inline(ev)}</td><td>{inline(st)}</td><td><span class='chip {chip.get(status) or ('low' if status.startswith('v7') else 'cat')}'>{inline(status)}</span></td><td>{inline(note)}</td></tr>")
    return f"<table>{head}<tbody>{''.join(rows)}</tbody></table>"
