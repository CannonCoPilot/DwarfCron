"""Section 20's table: every recommendation, its evidence, its strength, and where it stands (1 Oct 2026)."""
from mdlite import inline

S69, S70, PROP, OPEN = "v6.9 (released)", "v7.0 (validated, not released)", "Proposed", "Open"
RECS = [
    ("Filter the relation write through eats(): reach, size, class", "58% of written pairs failed the tool's own rules; shark × deer and wolf × pike made 0 attacks", "40-cell matrix, 1 run each", S69, "The write keeps only pairs the predator can reach"),
    ("Arm every non-BENIGN carnivore, not only LARGE_PREDATOR", "The coyote killed deer; fox, badger and a BENIGN wolf never attacked", "1 run per cell", S69 + "; " + S70, "v7.0 clears BENIGN on every predator the roster arms (your ruling)"),
    ("Bring water-layer units into the ecology, realm by habitat", "Alligators and crocodiles took 4–5 of 8 land prey from the water; sharks took seals in water", "1 run per cell; REACH 2 reps", S69, "Water units in the surface realm, amphibious both ways"),
    ("Guard pairings where prey outguns the predator", "Capybaras killed 5 of 5 wolves; buffalo killed a lion", "1 run each", S70, "5% pack-mass floor on the group present, sneak bonus at 25%, outgun warning in the builder; the sweep saw no effect of floor or bonus"),
    ("Season gate: the tool's deal or the raw NO_<season>", "NO_SPRING kangaroo 0 of 19 spring waves; cleared NO_WINTER groundhog 40 of 57", "1 and 2 runs", S70, "v6.9 respected the flags; v7.0 clears them on managed species so the tool's deal wins, and restores them on off"),
    ("Scavenging as the tool's own walk-and-delete", "Nothing in DF eats remains; the tool's pass cleared land and water carcasses in ~2,400 ticks", "2 reps", S70, "Map-wide outside stockpiles, fliers land, swimmers reach water corpses; who ate is unmeasured"),
    ("Hold curious beasts as residents by clearing CURIOUS_BEAST*", "18 of 18 placed bears and raccoons left; 0 of 10 with the flags off", "1 run per cell", S69, "curious TOKEN resident|thief"),
    ("Drop wild-only combat alerts", "Wild-only alerts dropped, fights with dwarves kept, safe across a reload", "Prototype, one fight per case", S69, "On by default; Panel switch; humanoids always alert"),
    ("Exhaustion watcher and same-guild replacement", "An emptied entry stopped the species; the replacement arrived 2,090 ticks later", "1 run", S69, ""),
    ("Groups at once = √(embark tiles) + 1, per layer", "+1 group at 5×5 and 6×6; the land limit binds on CTRL; the cavern limit is soft", "2 reps, counterbalanced", S69 + "; " + S70, "v7.0: each water body and cavern depth its own limit"),
    ("FREQUENCY ladder as the balancing dial", "Shares proportional within a few points; ×0.5 cut predators to ~2%", "F1 1 run; SW4 2 reps", S70, "v7.0 carries the v2.1 ladder; porting v2.2 and dropping the apex step are open"),
    ("Deep-water survey; pelagics weighted by map depth", "OCEAN2 0% columns at 3+ levels, BOATS 33%", "Survey", S70, "Pelagic slot 0–1, raised to 2 at triple weight on deep maps"),
    ("Leader = largest adult male", "Leaders hold herds, packs, flocks, schools and pods; which member leads made no consistent difference", "L1/L2 1 run; COH 2 reps", S70, ""),
    ("Guild-first roster builder with the nine rule fixes", "0% isolated over 54,560 offline builds; ran on CTRL, BOATS, OCEAN2", "Offline + S8, 2 reps", S70, "ROSTER.build; v2.2 ladder and per-body water layers still to port"),
    ("Realm table as optional data", "The raws hold no geography", "Desk", S70, "Behind the realms switch, off by default; never run on the rig"),
    ("Solitary-hunter package", "Placed-prey kills 14 → 29 over 10 seasons (p = 0.07); spread out, no effect", "10 runs per arm", S70, "Skills 10, no sneak slowdown, AMBUSHPREDATOR; caste write unverified on the rig"),
    ("Manage GOOD/EVIL wildlife on matching regions", "GOODF and EVILF manage their own alignment and lock the other", "1 run each", S70, "Plus the Vermin-tab leak, cavern GOOD/EVIL and FANCIFUL fixes"),
    ("Cavern civ races hunt and are prey; never write forgotten beasts or megabeasts", "Builder: 20 singletons to 0", "Offline", S70, ""),
    ("Sweep DF's own PREDATOR_OR_PREY between managed wildlife the roster doesn't pair", "DF aims placed and released units at arrivals (RELS)", "2 reps", S70, "With a count of pairs DF writes back"),
    ("Fishing land predators", "0 attacks on fish in 6 runs (FSH2); wolves never fished (FISH)", "2 reps", S70, "Built, default off; the lake-apex gap reopens"),
    ("Empty relation slots write NONE (−1)", "SLOTV: DF's empty value is −1; STRANGER is never its default", "1 run", S70, ""),
    ("Vermin classes and gobble writes", "Written class works on the eater (VRM2) and on the vermin (VRM4)", "2 reps each", S70, "The builder's full gobble edge table is not ported"),
    ("Domestic animals as prey", "With the switch on, wolves took a cavy each run; dogs killed a wolf each run", "2 reps", S70, "Off by default: it costs the player animals"),
    ("Ecology cadence 3,000; nudge off; pack_sneak 0; drop ×3 pack bonus; drop apex ladder step; cavern limit as a soft target", "SW1–SW7 and reruns: no effect on kills (0–4 per arm)", "2–4 reps, weak power", PROP, "Your decision (section 21); SW8 would confirm them together"),
    ("Cap animal-person group size in caverns", "Plump helmet men 54 and 180 a season on BOATS, ~15 per wave", "2 reps", PROP, "Your decision"),
    ("Add invasive places SAVAGE species itself on calm maps", "DF never drew the smilodon in a season (1 species, 1 fort)", "2 runs", PROP, "Your decision"),
]


def table():
    cls = {S69: "good", PROP: "warn"}
    head = "<thead><tr><th>Change</th><th>Evidence</th><th>Strength</th><th>Status</th><th>Notes</th></tr></thead>"
    rows = []
    for ch, ev, st, status, note in RECS:
        rows.append(f"<tr><td><b>{inline(ch)}</b></td><td>{inline(ev)}</td><td>{inline(st)}</td><td><span class='chip {('low' if status.startswith('v7') else 'cat') if status != PROP else 'medium'}'>{inline(status)}</span></td><td>{inline(note)}</td></tr>")
    return f"<table>{head}<tbody>{''.join(rows)}</tbody></table>"
