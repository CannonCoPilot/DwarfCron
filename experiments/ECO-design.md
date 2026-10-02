# ECO — a suite of small experiments on wild-animal behaviour, for seasonal-wildlife

User ask (29 Sep 2026, 23:4x): design a large set of very simple experiments (1–2 reps) to validate and discover how
animals behave in DF 53.16 as it bears on seasonal-wildlife, run them all, and turn the results into improvements to the
tool's mechanics. FPS6 is on hold meanwhile.

Baselines gathered first (no rig): the wiki's functional definition of every token asked about (scratch
`eco/wiki-tokens.md`: 375 tokens fetched as raw wikitext, ~15 linked pages); a census of the vanilla raws (967 creatures,
363 wildlife; `eco/census.json`, `token-counts.tsv`, `groupings.md`, `candidates.md`); a map of what the tool and the rig
already do (`eco/capabilities.md`); a pilot fight (`eco/pilot-P0.md`). Token effects are taken from the wiki or measured —
never inferred from a name.

**Status (1 Oct 2026 review).** Every block below ran, 29 Sep night – 1 Oct morning, and many more were added (ECO2, ECO3,
the 30 Sep night queue, the SWEEP blocks). Results: `data/eco-desk/findings.md` (authority) and the ECO Wildlife Study page
(https://claude.ai/artifact/UY2KevMooCW4mRr5F19M26, built by `scripts/eco-report/`). Section "Results by question" at the end maps
each question to its blocks and verdict; "Next experiments" holds the designs the open questions call for. All of it ran on DFHack
53.16-r1.1; the rig moved to 53.16-r2 on 1 Oct (~08:55), so a re-validation comes before any new block (open item
revalidate-dfhack-r2). The "1–2 reps" of the original ask became 2 reps per arm from 30 Sep (memory two-reps-per-arm); the
first-day matrices (P1, P2, T1, W1L, W1O, the HC/HR/HO/HL probes, F1) ran once.

## Instrument (new)

`chronicler/dfhack/scripts/cx-eco.lua` — one atomic verb per RPC call, state in `_G.CX_ECO`:
`spot land|shore|water`, `spawn TOKEN N X Y Z [r] [land|water] [male|female|any]` (headless placement: the six writes +
an enemy slot; the species' own population ref, else a borrowed one), `rel A B` (PREDATOR_OR_PREY both ways), `watch`
(eventful UNIT_ATTACK counts per attacker>defender race; incident baseline), `read` (per group alive/dead/gone, spread,
share in water; attacks per pair; Death incidents with killer and victim race and cause; COMBAT alerts), `clear` (vanish,
no corpse), `flag TOKEN FLAG on|off` / `restore` (caste or creature flag in memory, species-wide, snapshotted), `lead TOKEN
lowest|largest-male|none`, `alerts drop-wild on|off` (prototype filter).
`scripts/eco-run.py` — runs a block: one fort load, then cells in sequence (setup verbs, step, read, clear, restore);
every `eco ...` line goes to `data/experiments/ECO/<run>/<block>.tsv` tagged block/cell/rep. The fort is never saved.

**Placement rule.** Species are placed regardless of their biome: the question is how two units behave once together,
not whether DF would bring them. Groups start 10 tiles apart (centre to centre, radius 3) on a spot chosen as the open
ground (or shore, or water) nearest the map centre and at least 30 tiles from any citizen.

**What counts.** A kill = a Death incident whose killer and victim are both spawned. An attack = one UNIT_ATTACK event.
Conflict = attacks in both directions. A cell with no attacks and no kills is a result (a zero), not a failure; the readout
traps in memory apply (a zero with the subjects gone is censored, not zero).

## Questions → experiments

Rig blocks are marked ▶ (with forts, cells, ticks); desk work ◇.

### Q1 Scavenging — "eating" remains
◇ Wiki: no creature eats corpses/remains in any mode; BONECARN is "does not work" (adventurer bug 11069); VERMIN_ROTTER
vermin gather at rot; GOBBLE_VERMIN eats vermin of a class. Census: no carrion token; vulture/buzzard descriptions say
carrion; CURIOUSBEAST_EATER/GUZZLER/ITEM steal food/drink/items.
▶ **S1 corpse exposure** (CTRL): make 6 KANGAROO corpses at the spot (spawn, drain blood → death, corpse stays); place
6 of each candidate beside them for 4,000 t: BIRD_VULTURE, HYENA, BEAR_BLACK (CURIOUSBEAST_EATER, "steals carcasses"),
RACCOON (CURIOUSBEAST_EATER+ITEM), WOLF (BONECARN), control DEER. Read: corpse items moved / held / gone.
▶ **S2 tool-driven "eating"** (CTRL): scavenger group + corpses 20 tiles away; the tool's way: set each scavenger's
path goal to a corpse tile; on arrival (≤1 tile) delete the corpse item; count arrivals and deletions, time to arrive;
then save to a scratch save, reload, check the fort loads and the items are gone. Arm B: a real job (StoreItemInStockpile)
assigned to a wild unit — does it act on it?
▶ **S3 HAUL_REFUSE on a wild animal** (CTRL): set the labor on 3 placed wolves beside corpses; any job taken in 4,000 t?

### Q2 Tags that set scavengers apart
◇ Census partitions: BONECARN (41 wildlife) and CARNIVORE (46) never co-occur and never with STANDARD_GRAZER; candidate
set-groups for scavenging built from BONECARN ∪ CURIOUSBEAST_EATER ∪ description words; scored against S1/S2.

### Q3 Predator–prey sweep with large groups
▶ **P1 matrix** (CTRL, 3,000 t per cell): predators WOLF, COYOTE, DINGO, HYENA, CHEETAH, LION, BEAR_GRIZZLY, FOX (6 each)
× prey RABBIT, GAZELLE, DEER, KANGAROO, WATER_BUFFALO (10 each); two arms: DF only (no write) and relation written
(80 cells, 1 rep). WOLF/COYOTE is the LARGE_PREDATOR minimal pair; FOX is BENIGN+BONECARN.
▶ **P2 conflict** (CTRL, 3,000 t): predator vs predator, no write: WOLF×COYOTE, WOLF×DINGO, LION×HYENA, CHEETAH×HYENA,
BEAR_GRIZZLY×WOLF, and same-species WOLF×WOLF (two groups).

### Q4 Across the land/water boundary; does the tool sort and pair correctly
▶ **W1 boundary** (LAKE shore; OCEAN2 shore for sea species; 3,000 t; relation written and not): aquatic predator in the
water vs land prey on the shore (FISH_LAMPREY_SEA×DEER; SHARK_BLUE×HARP_SEAL on the ice/shore); amphibious predator
(ALLIGATOR, CROCODILE_SALTWATER) vs land prey (DEER), vs amphibious prey (CAPYBARA), vs water prey (FISH_PIKE); land
predator (WOLF, LION) vs amphibious prey (CAPYBARA, SEA OTTER) and vs water prey (FISH_PIKE). Read kills, attacks, and
where each side stood (share in water).
◇ **W2 tool audit**: the tool's model (fixture `data/fixtures/species-model.tsv`, written by the tool) against the raws:
habitat, water bodies, role, realm, and the pair rules (`eats`, REACH, realm, `ecoArmed`) — which species land in the
wrong group, which pairs the tool writes that DF cannot act on (and the reverse), checked against W1.

### Q5 Token effects, and whether the tool respects them
◇ **T0 triage** of all ~95 tokens: wiki effect, vanilla count, level (caste/creature/value), fortress-mode relevance, does
the tool read it, test route: behaviour (flip at run time), spawn (wave pick), worldgen-only (not testable at run time),
or none (no wildlife effect in the wiki: CAN_SPEAK, PETVALUE, TRAINABLE_*, MOUNT, WAGON_PULLER...).
▶ **T1 behaviour flips** (CTRL, 3,000 t, 1 rep, flip species-wide in memory, restore after). Pairs are chosen so one
token changes:
- LARGE_PREDATOR on COYOTE (vs DEER); off on WOLF (vs DEER) — no relation write.
- BENIGN on WOLF (vs DEER, relation written); off on DEER (with WOLF).
- AMBUSHPREDATOR on WOLF (vs DEER): attacks, and whether the wolves start hidden.
- PRONE_TO_RAGE (misc value) on DEER attacked by WOLF: attacks by deer.
- FLEEQUICK on DEER near WOLF: prey–predator distance.
- AT_PEACE_WITH_WILDLIFE on WOLF (relation written).
- CRAZED and OPPOSED_TO_LIFE on DEER beside RABBIT (no predator).
- NATURAL_ANIMAL off on WOLF.
- MEANDERER off on DEER, alone: distance moved.
- LOOSE_CLUSTERS on KANGAROO, alone: spread.
- FLIER off on BIRD_CROW-sized land birds is not feasible (body); skipped with reason.
- Activity: DIURNAL vs NOCTURNAL (DEER vs DEER flipped NOCTURNAL): movement per 100 t over one full day (1,200 t).
- Swimming at a shore (LAKE): CAN_SWIM_INNATE off on DEER; CAN_BREATHE_WATER (=AMPHIBIOUS) on DEER; AQUATIC_UNDERSWIM on
  CAPYBARA: share of time in water with prey across the water.
- CURIOUS_BEAST_EATER on WOLF near the fort's food (CTRL wagon): items taken.
▶ **T2 spawn-time flips** (CTRL, tool disarmed, X3-style manifests, 30–60k t): NO_SPRING on a dominant KANGAROO in
spring (arrivals on vs off); UBIQUITOUS on DINGO (freq 5) — share of land waves vs a plain freq-5 species.

### Q6 Tags as set-groups for the tool's behaviours
◇ From the census: the clean partitions (LARGE_ROAMING/vermin; LARGE_PREDATOR/BENIGN/neither; CARNIVORE/BONECARN/
STANDARD_GRAZER; activity time; AQUATIC/AMPHIBIOUS/SWIMS_INNATE/none) and how their products cover wildlife; proposed
guild sets (e.g. apex hunter = LP; mesocarnivore = BONECARN∖LP; grazer; bird of prey = FLIER∩BONECARN; shore = AMPHIBIOUS
∪ ocean biome; …) with counts, each tied to a behaviour the tool would map onto it; validated by P1/T1/W1 where measured.

### Q7 Suppress animal-on-animal combat alerts
▶ **A1** (CTRL): a wild fight (WOLF×DEER written) and a fort fight (a WOLF beside dwarves); filter off vs on; read
COMBAT alerts kept/dropped; the dwarf fight's alert must survive; then save to a scratch save, reload, run 1,000 t.

### Q8 Deep vs shallow ocean
▶ **O1 depth survey** (OCEAN2, BOATS, LAKE): water column depth per tile (levels of water ≥ 4), share of tiles by depth.
▶ **O2 big fish in shallow water** (OCEAN2): SHARK_WHALE (20M) and SHARK_BLUE in deep vs shallow water, 3,000 t: moved,
stuck, died. ◇ Tool design: a deep class (open-ocean species: size, ANY_OCEAN, not AMPHIBIOUS) drawn rarer unless the
map has deep columns (from O1).

### Q9 Geographic eco-groups
◇ The raws hold no geography (census e); DF places any species on any landmass with its biome; penguins are
OCEAN_ARCTIC. A curated realm table (Australasia / Africa / Americas / Asia / Arctic / Antarctic) as tool data, applied as a
roster filter across biomes; Antarctic ≠ Arctic only by the table. Feasibility: species absent from the region pool enter
by Add invasive (exists). No rig run needed beyond what X1 showed (the roster gates arrivals).

### Q10 POPULATION_NUMBER exhaustion and niche replacement
◇ Wiki: once that many die or are kept, the species stops visiting (per biome); leaving alive does not count.
▶ **N1** (CTRL, tool disarmed): a dominant species with its entry at 3; each arrival is killed; waves until the entry is 0
and the species stops; then the replacement prototype: raise the nearest-niche species (same role, habitat, size band) —
the next waves are it.

### Q11 FREQUENCY for balancing
▶ **F1** (CTRL, tool disarmed, 60k t): four species at FREQUENCY 100/50/25/12, all others 1; wave shares vs the wiki's
model (uniform pick, accept on d100 ≤ f → share ∝ f).

### Q12 max_concurrent = √(embark size) + 1
▶ **G1** (FPS2E4 4x4 and FPS2E6 6x6, tool on, 40k t): land groups at once 3 (default) vs formula (√16+1 = 5, √36+1 = 7):
concurrent groups, wild units, t/s.

### Q13 Leader = the largest male
▶ **L1** (CTRL, 3,000 t): herd (DEER 10), pack (WOLF 8): no leader / lowest id (the tool's rule today) / largest male;
spread and cohesion; with a predator for the herd in a second pass.

### Q14 Fight log and interaction plots
The instrument is the logger (attacks per pair, deaths with killer/victim). ▶ run through P1/P2/W1; ◇ plot species ×
species over time from the TSVs.

## Order and budget
A1 → P1/P2 → T1 → S1–S3 → L1 (CTRL, one load each block) → W1 (LAKE, OCEAN2) → O1/O2 → T2, F1, N1 (manifests) → G1.
About four hours of rig time. Each block writes its TSV; analysis `scripts/eco-analyze.py`; results and the changes they
suggest for seasonal-wildlife go into a report.

---

## Results by question (1 Oct 2026 review)

Block IDs are findings.md's. "1 run" = one replicate. Where a later block overturned an earlier reading, the later one is given.

| Q | ran | answer | still open |
|---|---|---|---|
| Q1 scavenging | S1, S2, S3; SCV, SCVW, SCVC; SCV2 (vacuous), SCV2b/SCV2Wb | Nothing in DF eats or moves remains on any layer (S1, HC1, HCP, SCVC 4,000 t). Walk + delete works and survives reload (S2). The rig's walk works for wolves only (SCV). v7.0's own pass clears land and water carcasses in ~2,400 t (SCV2b, 2 reps). HAUL_REFUSE gives no job (S3). | Who ate (ledger not captured); scav_ext's flier, swimmer and wanderer fallbacks never fired; underground walk fails (HC1). Open item scav-attribution-and-fallbacks; SCV3 below |
| Q2 scavenger tags | desk Q2-scavenger-sets.md | SCAV.is = BONECARN, CURIOUSBEAST_EATER or a named list: 90 species, 3 aquatic (raws figure 9) | Count carnivorous swimmers? (decision scav-carnivorous-swimmers) |
| Q3 predator–prey | P1, P2; ECO3 PK; CAL; GPK/GPKW/GPKR | No relation, no hunting within 3,000 t (P1 0/40, P2 0/8, 1 run). Any non-BENIGN attacker acts on a written relation. Kills follow group size, not prey mass (PK, CAL); savage giant packs take megafauna (GPK). Over long cells DF itself aims placed units at natives (RELP, RELS) | Intraguild WOLF vs COYOTE written (design-s7-unmeasured-cells) |
| Q4 land/water boundary, tool audit | W1L, W1O (1 run); HR, HO, HL (1 run); HCP; REACH; WB; FISH, FSH2; LAKEP; W2 audit | Amphibious predators cross the shore both ways; aquatic ones never leave the water; land predators never fish, even with swim and breathe flags (FISH, FSH2: v7.0 fishers off). W2: 58% of written pairs failed eats() → v6.9 filters the write and brings water units in | OCTOPUS as attacker; flow effects |
| Q5 token effects | T0 desk; T1 (1 run); TV (1 run); TV2; FVA; B; CB; T2 (1 run); ECO2-W | BENIGN is the switch (T1, HO, TV2); AT_PEACE does not stop a write; CRAZED/OPPOSED aim at the fort; PRONE_TO_RAGE by dose (TV2); MEANDERER off scatters (TV2); LOOSE_CLUSTERS, FLEEQUICK, VISION_ARC, AMBUSHPREDATOR: no reliable effect; CURIOUS_BEAST flags make placed bears and raccoons leave (B, CB); NO_<season> honoured at the pick (T2, ECO2-W); UBIQUITOUS not read at run time (T2) | DIURNAL/NOCTURNAL and the swim-flag shore cells of the T1 list have no result in findings.md (CURIOUS_BEAST_EATER on WOLF ran: nothing in 3,000 t); CLUSTER_NUMBER at run time |
| Q6 tag set-groups | desk Q6-setgroups.md → guild builder v2–v2.2 | 15 set-groups became the 13 guilds of `v2/guilds/design.md` | – |
| Q7 combat alerts | A1, A2 (1 run each) | The filter drops wild-only alerts, keeps fort, animal-person and goblin fights, survives reload → v6.9 ships it on | Natural fights over a season (A3 below; open item single-run-defaults) |
| Q8 deep vs shallow ocean | O, DEPTHL, DEPTH (BOATS); OS; COHO; S8O | Fortress water is 1–4 levels: OCEAN2 never ≥ 3, LAKE 91% one level, BOATS 33% at 3–4. Big fish live in 1–2-level water for 3,000 t; placed unled orcas strand (3 of 12 in 15,000 t). v7.0 widens the PE slot only where ≥ 3-level ocean columns exist; on OCEAN2 it came out empty | Why the PE slot is empty (pelagic-slot-shallow-maps); PEL1 below |
| Q9 geographic groups | desk Q9-realms.md | Realm table built into v7.0 behind `realms` (off) | Never run on the rig, no validator claim (realms-built-untested); REALM1 below |
| Q10 exhaustion and replacement | N1 (1 run) | Entry quantity 0 stops a species; the extinct flag stays false; a replacement's first wave came 2,090 t after the hook (25 of the next 26 non-bird waves) → v6.9 EXHAUST | Second replicate (single-run-defaults) |
| Q11 FREQUENCY | F1 (1 run); ECO2-FC (1 run); SW4; S8C/S8Cb/S8B/S8O | Shares ∝ FREQUENCY on land and per cavern layer; ×0.5 predator ladder cuts predators to ~2%. The apex step does not visibly steer apexes | Does FREQUENCY steer the flier pool (flier-pool-steering)? Is LP a separate pool (lp-separate-pool)? Apex by placement/stock (APX1 below) |
| Q12 groups at once | G1 (1 run); ECO2-G; SW3B; SW5; SW6 | √(embark)+1 adds ~1 group on 5×5 and 6×6 only (v6.9 default); on CTRL 1 < 3 ≤ auto; the cavern cap trims only the tool's groups; water cap 2 = auto on BOATS | Savage map with 2 LP groups |
| Q13 leader | L1, L2 (1 run); HC1–HL (1 run); COH/COHO/COHR | A leader holds herds, packs, flocks, schools and pods on every layer; which member leads made no consistent difference → v7.0 largest adult male | Does a leader protect prey? Land 1 run says yes, water 1 run says no (L3 below) |
| Q14 fight log | all blocks | UNIT_ATTACK + incident log gave every count; blind in unopened caverns (deaths still appear) | – |

Blocks added beyond the original list and where they are reported: RELS, RELS2, RELS2b, RELS3, RELP, SLOTV (who DF aims at whom);
STL, STL2, LONE, LONE10 (solitary hunters); VRM, VRM2, VRM3, VRM3b, VRM4 (vermin); DOM, DOM2 (domestic prey); INV, INV2 (SAVAGE
invasives); T9c, E23e, item 6 GOODF/EVILF (caverns, alignment); S8C, S8Cb, S8B, S8O (a v7.0 season with the builder); SW1–SW7,
SW1R, SW2R, SW3B (experiments/SWEEP-design.md).

Vacuous or flawed runs, kept as lessons: TV/HL/HO/VR* vermin cells (no vermin at the spot or colonies only), VRM (vermin piled up
across cells), INV run 1 (yeti refused on biome), SCV2 (tool off), S8C (loop over a string; kept as the builder-off control), SW3
(status line counted cavern groups). Each was rerun with a receipt.

Untested assumptions the results carry (labelled on the page):
- Placed and tool-released units are non-wild to DF, which aims them at arrivals itself (RELS). Long cells with placed hunters and
  the SW1/SW2 arena cannot separate the tool's written pair from DF's aiming.
- Cells sharing one load run in order and natives pile into later cells (SW1); only the SWEEP blocks from SW3 on and the reruns
  were counterbalanced. Earlier multi-cell blocks (P1, T1, TV2, HC*, REACH, FSH2, COH) ran in a fixed order: their later cells may
  carry more natives. Their readouts count placed pairs only, which limits but does not remove the bias.
- LONE10's skill package was written by the harness; v7.0's own caste NATURAL_SKILL write is unverified (natural-skill-unverified).
- One species, one fort: INV2 (smilodon on CTRL); one fort: CB, A1/A2, N1.

## Next experiments (1 Oct 2026 review)

Every design: **2 replicates per arm**, as few arms as the question needs; **counterbalanced order** (rep 2 runs the arms in reverse;
a fresh fort load per arm where cells would otherwise share a load); a **manifest subject receipt** in the pre and every pass
(the subject's own count, the forced state, the tool's job counters), and a replicate that fails it is reported vacuous, not zero
(memory manifest-subject-receipt, experiment-readout-traps 20–21). Score placed-only pairs where anything is placed. First: the DFHack
53.16-r2 re-validation (open item revalidate-dfhack-r2), because teleport, setPathGoal and breathing changed under every block below.

| id | question (open item) | fort, window | arms | receipt | readout | priority |
|---|---|---|---|---|---|---|
| **R2V** | Do the harness and v7.0 behave the same on r2? (revalidate-dfhack-r2) | validate-full forts; then CTRL/OCEAN2 | validate-full once; COHO (unled pods) and SCV2b re-run as in ECO, 2 reps | dfhack version string in every log; cx-eco spawn/tp receipts | claim-by-claim diff vs 20261001-074833; orca drowning and corpse clearance vs the r1.1 numbers | high |
| **APX1** | Can placement or stock steer apexes, if the ladder's apex step goes? (apex-placement-stock-test, ladder-drop-apx-step) | CTRL, builder on, 100,800 t | control; stock (apex entry ×5, FREQUENCY as built); placed (tool places one COUGAR group at t0) | apex entry quantity before/after the pre; placed arm: apex units on map at +300 t; tool enabled and ecology counters per pass | apex units present per sample; kills by apex (placed prey excluded); departures; fort harm | high |
| **S8L** | Does the v2.2 ladder hit 14–18% predators once ported? (builder-port-vs-v22) | BOATS and CTRL, 100,800 t | ladder v2.1 (current) vs v2.2 | `roster build` lines with the ladder values printed; same seed both arms | predator share of surface units and waves; apex units; giant-pack overshoot | high, after the port |
| **E23f** | What starts a cavern invasion; does the invasion exclusion hold? (invasion-exclusion-unvalidated) | BOATS copy, 201,600 t | dig-now into cavern 1 + aquifer seal + citizens on the floor vs control | the cavern connection exists (path probe); irritation re-pinned and read before each re-pin | invaders; WILD.onMap counts with and without invaders | medium |
| **SOLO1** | Does v7.0's own solitary package work at natural density? (natural-skill-unverified, solo-package-natural-density) | CTRL, 100,800 t | v7.solo on vs off | a newly arrived solitary hunter's caste NATURAL_SKILL fields read on arrival | kills by armed solitary hunters; native-only (no placed units) | medium |
| **L3** | Does a leader protect prey? Land said yes, water no (single-run-defaults) | CTRL (10 DEER vs 6 WOLF written), OCEAN2 (12 MILKFISH vs 5 SHARK_TIGER), 6,000 t, fresh load per arm | none vs largest-male | lead receipt (leader id); relation rows > 0 at +100 t | attacks and kills on the herd/school; spread | medium |
| **SCV3** | Which species scavenge, and do scav_ext's fallbacks fire? (scav-attribution-and-fallbacks) | CTRL land, RIVER4 water, 8 × 300 t passes | vulture-only (natives culled), jackal on a fort with a real jackal entry, POND_GRABBER in water | `ledger` dump with the scavenging kind; SCAV last-run counters per pass | eaten per species; fallbacks fired | medium |
| **FLY1** | Does FREQUENCY or the stop list steer DF's flier pool? (flier-pool-steering) | CTRL, F1 design, 60,000 t | ravens native vs FREQUENCY 1 vs entry 0 | raven entry and FREQUENCY printed after the pre | raven share of bird waves | medium |
| **A3** | Does the alert filter keep every fort fight over natural fights? (single-run-defaults) | BOATS, 50,400 t | filter on vs off | COMBAT report count read each pass | alerts kept/dropped; any fight with a citizen (incidents) whose alert was dropped | low |
| **PEL1** | Why is the PE slot empty on OCEAN2; does a pelagic fill on a deep map? (pelagic-slot-shallow-maps, orca-stranding-n) | desk first (buildPool PE candidates for OCEAN2 and BOATS); rig BOATS, 100,800 t | builder on, 1 arm | deep-column count; PE candidates printed | PE slot fill; pelagic_beached | low |
| **REALM1** | Does `realm` co-seat only same-realm species? (realms-built-untested) | CTRL and OCEAN2, roster build only (no stepping) | realms off vs `realm auto` vs one forced realm | `roster build` output | species per realm; then add mech.v70.realms | low |
