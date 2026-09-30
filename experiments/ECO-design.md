# ECO — a suite of small experiments on wild-animal behaviour, for seasonal-wildlife

User ask (29 Sep 2026, 23:4x): design a large set of very simple experiments (1–2 reps) to validate and discover how
animals behave in DF 53.16 as it bears on seasonal-wildlife, run them all, and turn the results into improvements to the
tool's mechanics. FPS6 is on hold meanwhile.

Baselines gathered first (no rig): the wiki's functional definition of every token asked about (scratch
`eco/wiki-tokens.md`: 375 tokens fetched as raw wikitext, ~15 linked pages); a census of the vanilla raws (967 creatures,
363 wildlife; `eco/census.json`, `token-counts.tsv`, `groupings.md`, `candidates.md`); a map of what the tool and the rig
already do (`eco/capabilities.md`); a pilot fight (`eco/pilot-P0.md`). Token effects are taken from the wiki or measured —
never inferred from a name.

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
