# User review Part 2 of 2 (1 Oct 2026) — verbatim rulings, numbered for reference (R1..R63)
Top-level directive: "Focus on building everything first. Then move to the testing stage. Build all layers of the tool from commands
to DFHack UI to Web companion and GUI." and "Experiments to run or rerun: Hold on experiments to the end. Build first. Assume a fully
optimistic stance regarding all experimental outcomes, and build first with that in mind. Experiment later to confirm or invalidate."

R1 Define: "DF brought", "the tool placed", "the rig placed", "it was released". Grounded in game/tool mechanics? How do they differ?
R2 "the fort's side" — define; what is the mechanic at work?
R3 "Prey mass doesn't lower kills; it makes fights longer." Presumably prey mass correlates with increased predator death and injury.
   Confirm or invalidate.
R4 Invasions are disabled IN THE CODE of Dwarf Fortress (until a future major version, no ETA). 'Irruption' livens up cavern ecology,
   gives players something in place of the lost cavern invasion mechanic, and will eventually live alongside a re-introduced invasion.
R5 The tool UI must expose the added irruption behaviour tokens as on/off toggles or sliders so players adjust difficulty impact.
   Irruption events should add AGITATED to the NON-civ creatures of the cavern. Layer-specific. Needs an in-game end-state condition
   or a cooldown.
R6 What mechanic drives irruption occurrence? What ends it? What alerts/messages tell the player it is coming, has happened, has ended?
R7 Groups: layers get their own limit of concurrent groups (DESIGN REQUIREMENT), a function of map size. No "count per-layer y/n"
   switch. Add a toggle between a single fixed cap imposed on every layer and the map-size formula (for slower computers).
R8 SNEAK: keep the solo predator package in place, with a note for post-alpha experimentation and research.
R9 Pyramid targets accepted as first default (apex on land 20–30% of the season).
R10 Fury tier: agitate the ANIMALS, not the tribal cavern dweller creatures. For tribal cavern dwellers, each token type (CRAZED, RAGE,
    THIEF, and so on) is assigned to ~10% (minimum 1) of the irruption wave. Each wave always gets exactly ONE individual given ALL tags.
R11 Use the save region8, world Snospdastrasp "The Last Planets", at
    .../Bay 12 Games/Dwarf Fortress/save/region8 for ALL testing and experimentation moving forward.
R12 Replicates n=5 for any and all future experimental arms; keep each rep's runtime short.
R13 Roster builder: ANIMAL_MAN selection chance ~1/10 of other animals; all other biome-appropriate creatures uniform chance (filters
    still applied).
R14 "No pelagics on OCEAN2": design a fix if not already done.
R15 Cell-position confound: each cell rep must get ALL animals wiped from the map before placing the experimental groups.
R16 Rig walk-and-eat verbs fed wolves but not jackals, vultures or anything at the water (SCV, SCVW): investigate why.
R17 Swimmer scavengers: add sharks (not only pond grabbers, sea serpents, sea monsters).
R18 Scavenging speed in in-game time? It must not zip scavengers around the map and zap corpses like a clean-up sweep; natural cadence.
R19 Figure "A written gobble token made badgers take roaches" appears empty: repair.
R20 Gobble experiments need a larger suite of representative vermin.
R21 Colony "counts" (bumblebee, termite 14,000–19,000) are fake (industry size, never swarms on the map). Build a better predator-prey
    system for vermin-eating creatures to richly interact with the variety of vermin in the game.
R22 Water: "depth" of a column = count of stacked water tiles; per-tile water depth is 1–7 (flow). Different things; keep them apart.
R23 Cavern invasions (E23e): invasions are disabled in the game code.
R24 EXTINCT creatures lack the tags they ought to have; see Steam workshop mods 3753912171 and 3755752944.
R25 Vermin-root ANIMAL_MAN: give a reasonable smallish mass so they can prey on small critters.
R26 Animal people + giants = 49.3% of wildlife types unbalances vanilla: lower roster selection odds for ANIMAL_MAN and GIANT_*;
    filling a roster should still fill where it can; once on a roster, ANIMAL_MAN and GIANT_* get LOWER FREQUENCY for waves.
R27 "DF wires only one gobble class natively" — needs fixing; the tool's GOBBLE_RULES is the fix and looks good.
R28 Figure "67 species carry UNDERGROUND_DEPTH": sort by depth then alphabetically. Is layer 1 really only RAT_LARGE, MOLE_DOG_NAKED?
    Could the tool increase layer-1 diversity by picking other creatures? How does depth work with cavern layer placement
    mechanistically? Is the tool breaking anything (fiery types in a cavern layer)? Why is MAGMA_CRAB in layer 5 underworld?
R29 Season gate: the TOOL's deal (not the raw NO_<season>).
R30 Curious beasts: let them steal first; after the counter is set to 0, clear THAT individual's CURIOUS tag and reset the counter to a
    normal value, so thieves keep meddling but stay as part of the ecosystem longer.
R31 Groups at once per layer: a hidden limit is hit (draw/placement rate vs mean leave countdown). Fix so the per-map-size limit is
    approached while keeping a semi-random stochastic feel to concurrent group counts.
R32 Leader = largest adult male. If no male, no leader. If the leader dies, no leader — this causes a panic-shock behaviour in herding
    and pack animals.
R33 Fishing land predators: implement only on BEAR-type creatures for now; explore, test, think creatively — bears hunting salmon.
    Polar bears get full swimming tokens and hunt in water like sharks and on land like crocodiles.
R34 Drop the apex step from the FREQUENCY ladder; steer apexes by placement and stock: YES.
R35 Group-size cap for animal people (plump helmet men) in caverns: YES, lifted during an irruption event.
R36 Add invasive places SAVAGE species on calm maps itself: YES.
R37 Ecology cadence 1,500 -> 3,000: YES.  R38 Nudge off by default: YES.  R39 Push DwarfCron Dev and seasonal-wildlife v7.0: YES.
R40 pack_sneak: what is it and how does it work? Was NATURAL_SKILL:SNEAK tested across its full range (legendary = 20; same for all
    skills)? Good solo predators (sharks, jaguars) should be mid to legendary; GREMLIN has NATURAL_SKILL:SNEAK:3.
R41 x3 pack-hunter pick bonus: KEEP; the lack of effect is probably a failure in handling tokens/mechanics. Retry.
R42 Carnivorous swimmers count as scavengers: YES.
R43 Temperate lake apex: don't turn fishing off for BEAR types — fix them so it works; allow a curated aquatic apex list (may include
    amphibious apex).
R44 Cavern groups: why are DF's native cavern populations "not the tool's to gate"? Fix: the tool gates cavern layers; cavern layers
    get a universally fixed max of 5 concurrent groups, under the tool's control.
R45 Water groups: NO "2 per body" default. Manage in-water aquatic concurrent groups like land groups; no hard caps; a fort map must
    actually reach 3–5 concurrent aquatic groups on its own.
R46 FPS6: hold.
R47 Raptor-on-land edges: make them REAL and make them actually occur (not rare).
R48 Performance v7.1 (instrument, memoize classification, groups/undo in CACHE, overlay from cache, one census, stagger jobs): YES.
R49 Don't seat the sea lamprey as a lake/river apex; research which lake/river apex creatures to include and how to handle them.
R50 Flying layer: raptor slots set to 1.
R51 Port the builder's GOBBLE_VERMIN edge table into v7.0: YES.  R52 Expose v7 switches in the GUI Panel: YES.
R53 PRED cfg key: do what is best for performance and data structure handling.
R54 Web companion: add a dev phase to overhaul it for controlling all v7.0+ functionality.
R55 Performance v7.2 (forEachTile surveys, coroutine slicing, eventful arrivals, shared pool memo): YES.
R56 Known bugs and diagnostics: resolve all.
R57 Builder port (v2.2 ladder etc.): approved. Realm table: approved. Validator backlog cleanup: approved. Animal-person mass: approved.
R58 Solitary package: assume it can work; fix rig and tool so the natural-skill write works as hoped.
R59 Shallow ocean SHOULD seat a pelagic (PE) slot. Ladder targets units (divide FREQUENCY by mean cluster size): approved; test later.
R60 Demons on deep layers: no limit, no management, unseen until breached; the tool has NO impact on them.
R61 ANT_MAN belongs to the civ set; VERMIN_MAN creatures in the caverns belong to the civ set. 19 animal people at FREQUENCY 0: floor 1.
R62 Release/housekeeping: do all. Harness/validator/method: fix all. Water placement weighted by what is swimming: unpark, prioritise.
    Whole-list solitary/pack/herd table with overrides: build. Upstream DFHack: port modtools/create-unit onto dfhack.units.create:
    implement. Alpha phase two + playtest republish: hold to the end, then overhaul for testing after all new stuff is in.
R63 Lower priority / held: gobble feeding & debit (low); cavern traffic limit (more testing later); LP own pool (N/A).
