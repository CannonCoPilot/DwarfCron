# Roster + food-web builder v2: guild-first design (seasonal-wildlife, DF 53.16)

**v2.1 (30 Sep 2026):** rules marked *v2.1* below follow the user's rulings and ECO CAL. Code: `roster2.py` config `v21`
(`run2.py`); numbers: `results21.md`, `tables21.md`. The v2 text is kept in `runs/v2-orig/design.md`.

Files only. The code is `roster2.py` (builder), `species2.py` (species table, guilds, apex rule) and `realms2.py` (realm table).
The numbers behind every choice are in `results.md`, `tables2.md`, `apex.md` and `realms.md`.

**Evidence rules**
- Measured rig facts come from `../../findings.md` (block IDs in brackets).
- Token effects come from `../../wiki-tokens.md`. No effect is inferred from a token's name.
- Anything geographic is external knowledge and is labelled as such.

---

## 1. Rule set, in order of precedence

A later rule never overrides an earlier one. Guilds decide first. The contrived rules (sizes, preferences, pack bonus) only
weight choices that the guild rules have already allowed.

### R0. Universe

- The tool's `natural` class, with a BIOME, and not IMMOBILE: 894 creatures.
  - 332 vanilla, 178 giants, 184 animal people, 100 extinct, 100 extinct animal people.
- **SAVAGE gate.** On a calm embark, SAVAGE-tagged species are excluded (wiki: "will only show up in savage biomes"). The gate
  is off underground (wiki: "no effect on cavern creatures").
  - All 178 giants, all animal people and 99 of 100 extinct species carry SAVAGE. CRETACEOUS_CARNOTAURUS is the exception.
  - This one rule removes v1's two largest distortions: giant seeds, and animal people as 37-44% of the pool.
- **GOOD/EVIL gate.** GOOD and EVIL species appear only on matching regions. No natural-class species carries either tag, so
  the gate changes nothing for the tool today.

### R1. Layer pool

Every layer and water type is its own ecosystem. Pool rules (`roster2.in_layer`):

| layer | admitted (non-vermin must be LARGE_ROAMING) | vermin admitted |
|---|---|---|
| land | not FLIER, not AQUATIC; a non-water BIOME on the embark. AMPHIBIOUS species count (they cross the shore) | VG ground, VC colony |
| flying | FLIER, any BIOME on the embark | VB bird/bat, VI insect |
| ocean / lake / river | AQUATIC or AMPHIBIOUS with that water BIOME; shore species (all-water BIOME); waterbirds with that BIOME; amphibious mesocarnivores | VF fish |
| cav1 / cav2 / cav3 | SUBTERRANEAN_CHASM or _WATER, not AQUATIC. **UNDERGROUND_DEPTH min..max is a hard gate** (knob `cav_mode=ceiling` allows dmin..3) | VG, VB, VI, VC |
| cavw1 / cavw2 / cavw3 (cavern pools, managed as water) | SUBTERRANEAN_WATER and AQUATIC, AMPHIBIOUS or shore; same depth gate | VF |
| deep (magma sea) | SUBTERRANEAN_LAVA, or a depth range that includes 4 | - |

- LARGE_ROAMING species never go in pools (wiki).
- The cavern layers and the deep layer are season-free: no cavern species carries a NO_<season> flag.

### R2. Season mask

- A species is absent in a season if any caste carries NO_<season>. DF honours NO_<season> set at run time [T2].
- UBIQUITOUS is not read at the fortress pick [T2]. It is never used.

### R3. Guild (one primary guild per species; tests run in this order)

| code | guild (Q6 number) | test |
|---|---|---|
| VG / VF / VC / VB / VI | vermin (G14) | any VERMIN_* flag. Split into colony, flying bird/bat, flying insect, fish/aquatic, ground. Stock only |
| AW | water apex (G2) | LARGE_PREDATOR and (AQUATIC or AMPHIBIOUS), not FLIER |
| RP | raptor (G4) | FLIER and (CARNIVORE or BONECARN or LARGE_PREDATOR) |
| AL | apex hunter, land (G1) | LARGE_PREDATOR (remaining) |
| MW | water mesopredator (new) | AQUATIC and (CARNIVORE, BONECARN or the tool override), not LP |
| ML | ground mesocarnivore (G3) | CARNIVORE or BONECARN, not LP |
| GZ | grazer herd (G6) | STANDARD_GRAZER |
| LB / WB | land bird (G13) / waterbird (G12) | FLIER, not carnivore; WB if it has an ocean/lake/river/pool BIOME |
| PE / FC / FF | pelagic prey (G9) / coastal fish (G10) / freshwater and cave-water fish (G11) | AQUATIC, split by ocean BIOME and size (PE: >= 1,000,000 cm3 or BEACH_FREQUENCY) |
| SH | shore / semiaquatic prey (G8) | AMPHIBIOUS, or an all-water BIOME without AQUATIC |
| PL | other land prey (G7) | everything else |

Overlays (tags, not guilds):
- **TH** thief/scavenger: CURIOUSBEAST_* or the Q2 text set.
- **deep** class: AQUATIC ocean species, >= 1M cm3 or BEACH_FREQUENCY; includes predators.
- **SN** sentient: animal person, CAN_SPEAK or CAN_LEARN.
- hibernator: NO_<season>.
- giant; extinct.

In any slot table, a sentient takes the **SN** slot whatever its trophic guild.

*v2.1:* GIANT_OCTOPUS (235,100 cm3) and GIGANTIC SQUID (201,400 cm3; no diet token, so armed through the curated override;
the id has a space, so it is addressed by creature index) are **MW, not apex**: too small for a pelagic apex.

### R4. Apex boost

See section 3. An apex (native or boosted) takes the **APX** slot.

### R5. Slot table per layer

Section 2 gives the tables.

**Fill**
- Slots are filled in table order.
- Each pass first brings every slot up to its minimum, then up to its maximum.
- A candidate must have at least one allowed edge to the roster. Its pick weight is R11 × the sum of its edge preferences.

**Seed**
- The seed is the first slot, in table order, that has a candidate with at least one relation in the pool.
- The apex is normally the seed. There is no "high value" test, so giants get no seed privilege.

**Pick** (*v2.1*)
- Uniform among candidates that pass the gates, x link preference; x3 for non-BENIGN group **hunters** (tier >= 2) only. DF
  FREQUENCY is not a pick weight (user ruling), and the pelagic inverse-size weight is no longer used at pick time.

**Stops**
- The fill stops when every slot is at its maximum, or when a pass adds nothing (the no-progress guard).
- *v2.1:* on no progress, a slot whose candidates link only to species not yet on the roster is seeded as a predator-prey
  PAIR (a sub-web: the cave fliers), then passes resume. Every slot left below its maximum is reported in `unfilled` with
  its reason (no candidate in pool / pool exhausted / no edge in pool / links only to non-roster species). Nothing stops
  silently.

### R6. Diet matrix by guild (who may eat whom, same layer)

| eater | may eat |
|---|---|
| AL | GZ, PL, SH, ML (intraguild), SN* |
| AW | FC, FF, PE, SH, MW (intraguild), WB (reach untested), GZ, PL, ML, SN*, VF (stock) |
| ML | PL, GZ, SH, SN*, VG, VC, VF (stock) |
| MW | FC, FF, SH, PE, MW, SN*, VF (stock) |
| RP | LB, WB, RP (intraguild), SN*, VB, VI (stock) |
| VB | VI (stock) |
| boosted apex | its home guild's list, plus its home guild itself (giant fox > fox; giant kea > eagle) |

- \* SN targets only under R7.
- *v2.1:* ocean adds the APE slot (pelagic apex: tier 3, eats with its own guild's list: AW or MW).
- **Tiers:** apex 3 > meso/raptor 2 > prey 1 > bird vermin 0.5 > other vermin 0. An edge must go strictly down a tier.
  - This makes mutual predation and apex-on-apex impossible by construction: 0 of 36,026 main edges.
  - No size threshold is involved.
  - DF itself makes rival predators fight as STRANGERs [E11c]; the tool writes no such relation.

### R7. Humanoid rule (*v2.1*)

- A sentient target (animal person, CAN_SPEAK or CAN_LEARN) may be written only for an attacker in the **AL or AW guild**,
  including giants boosted into apex from those guilds (giant wolf, lion, crocodile). Boosted mesocarnivores and raptors stay
  out (user ruling). v2 allowed any LARGE_PREDATOR, or a giant CARNIVORE/BONECARN.
- **Animal people are attackers** by their own trophic guild (`ap_attack`; user 30 Sep: "let them be predators"). Civ races
  (AMPHIBIAN_MAN, REPTILE_MAN, SERPENT_MAN, RODENT MAN, TROGLODYTE, ANT_MAN, GREMLIN, PLUMP_HELMET_MAN) are never attackers.
- Consequence: flying-layer animal people (insect-men, bird-men) have no allowed attacker there and never make a roster.

### R8. DF reach (measured) decides whether an edge can exist at all

| attacker \ target | land-only | amphibious | aquatic | penguin / waterbird in water | flier |
|---|---|---|---|---|---|
| land (not AQ/AMPH) | yes [P1] | yes, on land [W1L: lion x capybara] | **no edge** [W1L: wolf x pike 0] | - | untested |
| amphibious | yes [W1L: alligator(water) x deer 5/8] | yes | yes | untested | untested |
| aquatic | **no edge** [W1L: lamprey x deer 0; W1O: shark x deer 0] | yes, only in water [W1O: shark x seal] | yes [W1O: tiger shark x milkfish] | **untested** [W1O: polar bear x penguin in water 0] | - |
| flier (raptor) | untested | untested | - | untested | **untested** (no raptor hunt has been run) |

Edge classes:
- `df`: measured pattern, non-BENIGN attacker. DF carries it out [P1, T1].
- `df?`: written, but the reach is untested.
- `stock`: vermin, handled by the tool.
- `no`: BENIGN attacker. DF never acts [P1 fox 0; T1].

### R9. The only hard size rules: physical meaningfulness (*v2.1*)

- *v2.1:* **no 5x upper bound.** ECO CAL showed kills follow group size, not prey mass: 7 wolves (5.6% of an elephant's mass)
  and 10 hyenas killed elephants, and deer escaped. It is replaced by a **pack-mass floor**: the hunting group's total mass
  (mass x mid cluster size, non-BENIGN) must be at least `mass_floor` x prey mass. Default 20% (the earlier proposal); 5% is
  the lowest measured kill, and results21.md shows 20% forbids kills DF makes. **User to choose.** No floor at all admits
  inert solitary edges (river otter -> hippo).
- v2 (kept for reference): prey heavier than 5x the attacker's effective mass was not an edge. Effective mass = mass x
  (group mid-size)^0.75 for a non-BENIGN group hunter.
- **Lower bound:** a unit 10,000x lighter is not a unit hunt; a vermin stock link covers it.
- Everything between is soft (R10).
  - This keeps a wolf pack on moose (3.9x effective) and a lion on giraffe (3x).
  - It drops a hyena pack on rhinoceros (8.9x), a coyote pack on moose (9x) and a kea flock on a cave floater.

### R10. Soft size preference

- Weight = floor + (1 - floor) × exp(-(ln(r / r*))² / 2σ²), with r = prey mass / effective attacker mass.
  - σ = 1.0 (ln), floor = 0.02.
  - Preferred ratio r*: AL 0.8, AW 0.5, ML 0.3, RP 0.3, MW 0.2.
- The weight is **never zero** inside R9. It ranks prey at pick time and orders the relation writes.
- Test without it (`nosizepref`): seasonal breaks fall from 4% to 2%, everything else is within 2 points. The preference shapes
  which prey is chosen, not whether a web closes.

### R11. Pick weight

- *v2.1:* uniform (see R5). The v2 text below is superseded for picks. FREQUENCY is written as a finalizing step (R13).
- v2: the base was DF FREQUENCY, because DF's own pick is proportional to it [F1]. That was multiplied by:
  - **pelagic (deep class, non-apex):** the inverse-size frequency (section 5) instead of DF FREQUENCY;
  - **caverns:** a bizarre preference exp(-((score - target)/3)²) + 0.05, with targets cav1 2, cav2 4, cav3 7 (the v1 tertile
    medians). It is a preference, never a cut;
  - **optional secondary rule `pack_pref`:** × pack_pref for non-BENIGN group species. Off in `main`; 3 in `pack_pref3`
    (section 7 of results.md).

### R12. Guards (tool actions attached to every roster)

1. **Link guard.** Every member must have an edge. An isolated member is swapped for a same-slot candidate that links, or dropped.
2. **No-progress stop.** The fill ends when a pass adds nothing.
3. **Stop list.** Every pool species not on the roster has its population entry set to quantity 0. That stops the species [N1];
   exhaustion is detected by entry quantity, not the extinct flag [N1].
4. **Season guard (predator seasons within prey seasons).** For each roster predator and each season it is present in, if none of
   its roster prey is present then, the tool writes NO_<season> on the predator [T2: honoured].
5. **BENIGN clear** (*v2.1*). BENIGN is cleared on every predator-guild member the roster arms: the 20 boosted BENIGN apex
   (incl. ORCA, SPERM_WHALE) and the BENIGN mesocarnivores and raptors (fox, badger, otters, eagle, osprey, owls...). This
   takes surface edges DF will not act on from 19% of unit edges to 0 [T1: GIANT_FOX with BENIGN off attacked]. v2 cleared
   boosted apex only.
6. **Curious beasts.** A curious beast placed by the tool leaves within 3,000 ticks [B]. A resident curious beast (the three bears,
   8 boosted giants, the TH set) needs its CURIOUS_BEAST_* flags off (species-wide) or re-placement.
7. **One LP group per map.** APX max is 1 on land, 2 on a savage embark (wiki). A second apex is placed by the tool.
8. **Water realm.** ecoWrite gives water-layer units no realm today, so it never writes them [W2]. The ocean, lake, river and
   cavern-water webs need that fix before any edge is writable.
9. **Id safety.** 36 raw ids contain a space or comma (SEA OTTER, HONEY BADGER, "BADGER, GIANT"). Verbs cannot name them
   [W1O trap], so the tool must address them by creature index.

### R13. Frequency ladder

- *v2.1:* the ladder is apex 3, meso 3, grazer 6, other land prey 5, shore 4; raptor 2, other birds 6; water apex 2, water
  meso 3, fish 8, pelagic 2; caverns the same tiers. Within a slot it is scaled by (mass / slot geometric mean)^-0.75,
  clamped 0.25-4, and written x10 (shares unchanged). Section 5's table is the v2 ladder.
- The tool writes this FREQUENCY per roster species. Arrival share = f / Σf per layer and pool [F1].
- Section 5 gives the values.

### R14. Vermin links are stock transfers

- No unit fights a vermin. The tool debits the prey family's stock in proportion to consumer presence, with a floor and a ceiling
  (v1 roster-reasoning rule C).
- Every VG/VC/VF/VB/VI edge is `stock`.

---

## 2. Per-layer slot tables (slot: min-max, in fill order)

| layer | APX | then |
|---|---|---|
| land | 1-1 (2 on savage) | GZ 1-2, PL 1-2, ML 1-2, SH 0-1, TH 0-1, SN 0-1, VG 1-3, VC 0-1 |
| flying | 0-1 | RP 1-2, LB 1-2, WB 0-2, TH 0-1, SN 0-1, VB 1-1, VI 1-2 |
| ocean | 1-1 | *v2.1:* APE 1-1 (pelagic apex: SHARK_GREAT_WHITE, ORCA, SPERM_WHALE; + GIANT_ORCA, GIANT_SPERM_WHALE, SEA_SERPENT on savage), then FC 1-3, SH 1-2, MW 0-1, PE 0-1 (1-2 when water columns are >= 3 levels), WB 0-1, SN 0-1, VF 1-3 |
| lake | 0-1 | FF 1-2, SH 1-2, MW 0-1, WB 0-1, SN 0-1, VF 1-3 |
| river | 0-1 | FF 1-2, SH 1-2, MW 0-1, WB 0-1, SN 0-1, VF 1-3 |
| cav1-3 | 1-1 | PL 1-3, ML 0-1, RP 0-1, LB 0-1, SH 0-1, TH 0-1, SN 0-1, VG 0-2, VB 0-1 |
| cavw1-3 | 1-1 | FF 0-2, SH 0-2, MW 0-1, SN 0-1, VF 1-3 |
| deep | 0-1 | PL 0-2, ML 0-1 |

What the pools can fill (main config; `tables2.md` gives each slot):
- **Flying** has no apex on a calm map. Giant raptors are SAVAGE.
- **cav1** has no non-sentient group hunter. Its group hunters are the sentient civ races.
- **cavw1-2** contain only four amphibious LPs plus sentients and vermin. POND_GRABBER, CROCODILE_CAVE, TOAD_GIANT_CAVE and
  OLM_GIANT therefore reach into the cavern land layer for unit prey.
- **cavw3** holds only FLESH_BALL and sentients, and is empty.
- **deep** is IMP_FIRE and MAGMA_CRAB, always.

---

## 3. The apex rule

IF (guild ∈ {AL, AW, ML, RP} OR CARNIVORE) AND (giant OR adult ≥ 1,000,000 cm3) THEN apex. This holds with or without
LARGE_PREDATOR, and with or without BENIGN.

**Readings**
- CARNIVORE is read as CARNIVORE or BONECARN. Wiki: BONECARN "implies CARNIVORE".
- ORCA, GIANT_ORCA and GIANT_CUTTLEFISH enter through the tool's curated predator override. The literal rule misses ORCA
  (BENIGN, no diet token).

**What it admits**
- **89 boosted species:**
  - 63 giants;
  - 5 vanilla: SHARK_GREAT_WHITE, SEA_SERPENT, ORCA, SPERM_WHALE, JABBERER;
  - 10 extinct: T. rex, Allosaurus, Torvosaurus, Carnotaurus, two Spinosaurus, Megalodon, Mosasaurus, Dunkleosteus, Archelon;
  - 11 animal people.
- **90 native apex** (LARGE_PREDATOR, below the bar).

**BENIGN apex**
- 20 boosted species need BENIGN cleared to act: giant fox, badger, otter, stoat, wolverine, mongoose, pond turtle, six giant
  raptors, ORCA, SPERM_WHALE, the giant orca and giant sperm whale, Archelon, and two animal people.
- The boost is how a BENIGN species becomes armable at all.

**Sentient apex**
- 11 boosted and 38 native apex are sentient. They are held out of attacker roles by R7.

`apex.md` lists every species with its flags.

---

## 4. The humanoid rule

- **Allowed attackers of sentients:** LARGE_PREDATOR, or giant AND CARNIVORE/BONECARN.
- **Effect:** 0 violations in any run. Without it (`no_humanoid_rule`), 3,023 of 56,151 edges would target sentients from
  non-LP, non-giant attackers: eagles, octopus, rattlesnakes, CRUNDLE.
- **What the rule admits in practice:** on savage maps, most attackers of animal people are giant raptors and giant lizards
  (GIANT_EAGLE, GIANT_SKINK). Tightening would need a guild restriction (e.g. AL/AW only), not a size bar.
- **Fort safety:** the rule does not by itself keep a civ out of it. A written relation against a civ-member group is a separate
  risk [E22: gathered dingoes killed a caravan animal]. Keep livestock and visitors out of the write, as the tool does by opt-in.

---

## 5. Frequency ladder per guild (the FREQUENCY the tool writes)

| slot | f | note |
|---|---|---|
| APX | 4 | DF's own LPs sit at 2-5. **LARGE_PREDATOR is a separate DF wave pool (wiki)**, so whether this number competes with prey is untested |
| ML / RP / MW | 12 | |
| GZ / FC / FF | 50 | |
| PL / LB | 40 | |
| SH / WB | 30 | |
| SN | 5 | |
| TH | 10 | a tag: a TH member keeps its trophic slot's f |
| PE and deep-class non-apex | clamp(100 × 200,000 / mass, floor 2, cap 50); ×3 (cap 100) when the map has water columns ≥ 3 levels | 1M → 20 (60 deep), 2M → 10 (30), 5M → 4 (12), 20M+ → 2 (6) |

Measured depths:
- Ocean embarks are 1-2 levels deep [O: 0 columns ≥ 3].
- A lake reaches 3 [DEPTHL: 1,334 columns].
- So the deep boost fires on lakes, and on an ocean only when a deeper map is found. The wiki documents no depth placement.

Resulting predator share of arrivals (main): land 0.14, ocean 0.06, river 0.13, caverns 0.08-0.15. Lake (0.54) and cavern water
(0.44) are predator-heavy, because their prey is mostly vermin.

---

## 6. Water and cavern specifics

### Ocean

- Shark apex, pelagic class and coastal fish; shore species (seals, walrus, penguins) sit on the boundary.
- ORCA and SPERM_WHALE are armable only as boosted apex with BENIGN cleared.
- Aquatic attackers never target land-only species [R8].
- BEACH_FREQUENCY species (ORCA, SPERM_WHALE) may strand (wiki). This is untested for tool placement.

### Lake and river

- The apex is FISH_LAMPREY_SEA (temperate), ALLIGATOR, or CROCODILE_SALTWATER (tropical river). The temperate lake has no apex
  50% of the time.
- Unit fish are few (4 FF species). Vermin fish carry most of the base, as stock.
- **Open question:** are lake species feature entries (no realm, so unwritable) or surface entries (realm land)? W2 found the
  tool's own notes contradict each other. This decides writability.

### Cavern land

- Depth range is a hard gate; the bizarre score is a preference.
- `cav_ceiling` (dmin..3) makes cavw3 non-empty (80 more rosters) and grows cav3 from 8.1 to 10.0 species, but lowers DF-actable
  edges from 69% to 60%.
- cav1 has no non-sentient group hunter. With `sentient_attack` on, the civ races become the packs.

### Cavern water

- Four amphibious or aquatic LPs; sentients and vermin fish are the only in-pool prey.
- The amphibious ones hunt the cavern land layer's prey across the edge. This is the same reach as the surface shore, and it is
  untested underground: E41 found a croc was not pulled from water, and E41f found a croc killing toads in the same water.

### Deep

- Degenerate (IMP_FIRE → MAGMA_CRAB). Only 2 natural species exist.

---

## 7. What must be tested on the rig, per layer

Legend: ✔ measured (block); ○ open; the arm design follows the two-replicates-per-arm rule.

| item | land | flying | ocean | lake | river | cav1-3 | cavern water | deep |
|---|---|---|---|---|---|---|---|---|
| **Hunting on a written relation** | ✔ P1/T1: non-BENIGN acts, LP not needed. ○ boosted BENIGN-cleared giant (GIANT_FOX vs RABBIT/DEER). ○ intraguild apex→meso (WOLF vs COYOTE) | ○ **everything**: non-BENIGN raptor (BIRD_BUZZARD/KEA) vs land bird; boosted giant raptor with BENIGN cleared; raptor vs a land prey across layers | ✔ W1O shark x seal (water only) / x milkfish. ○ ORCA and SPERM_WHALE cleared; ○ shark vs penguin / waterbird in water; ○ OCTOPUS (MW) as attacker | ✔ W1L alligator. ○ FISH_LAMPREY_SEA vs BEAVER in water; ○ **are lake species writable at all** (feature vs surface entry) | ○ CROCODILE_SALTWATER vs HIPPO in a flowing river (RIVER3/4); ○ flow effect | ✔ E41e (kills via incidents). ○ per level: cavern LP vs cavern prey; ○ LP vs a sentient civ-race group without the fort joining | ○ cave croc/olm/toad across the pool edge vs cavern land prey; ○ POND_GRABBER never leaves water | ○ IMP_FIRE vs MAGMA_CRAB (MAGMA fort) |
| **Groups, leaders, packs, herds** | ✔ L1/L2: a leader gives cohesion; a led herd was barely attacked. ○ a led **pack** vs a led herd | ○ flock cohesion with a leader (follow 12) | ○ school cohesion (follow 5); ○ ORCA pod 3:9 | ○ school | ○ school in flow | ○ one group at a time (wiki) vs tool limit 2; ○ civ-race groups 5:10 | ○ | ○ IMP_FIRE 3:4 |
| **Vermin eating (stock transfer)** | ✔ X5: HUNTS_VERMIN has no effect. ○ the tool's stock debit shows in df.vermin counts and sightings | ○ bird vermin → insect debit; DIVE_HUNTS_VERMIN | ○ VF debit vs fishing yield | ○ VF debit (aquatic vermin do not restock: wiki bug 2780) | ○ same | ○ cave spider stock | ○ cave fish / olm stock | n/a |
| **Eating remains (walk + delete)** | ✔ S2: hyenas walk, eat, reload-safe. ○ with a pack after a kill; ○ JACKAL (not LP) | ○ vulture/buzzard (fliers: a path to the ground) | ○ corpses in water: persist, sink? ○ aquatic walk-to in water | ○ | ○ corpses carried by flow | ○ underground remains make miasma: priority; ○ path in caverns | ○ | ○ remains in magma burn? |
| **Relative frequencies** | ✔ F1: land/surface non-bird pick ∝ FREQUENCY. ○ **the LP pool is separate**: does APX f matter? ○ the ladder reproduces predicted shares with 5+ species | ○ the flier pool (13 bird waves in F1) ∝ FREQUENCY? | ○ water waves ∝ FREQUENCY? (ocean species come from surface entries, W2); ○ deep boost on a ≥3-level map | ○ lake waves ∝ FREQUENCY | ○ | ○ CAVERN.apply clamp ≥ 1; does the bizarre preference show in waves? | ○ | ○ 3 deep waves in F1 only |
| **Group counts by embark size** | ✔ G1 (4x4 vs 6x6, surface): +1 concurrent group from the limit; supply-limited. ○ savage map: 2 LP groups? | ○ | ○ water limit 2/12: DF's own cap unknown | ○ | ○ | ✔ CTRL: cavern gate saturates at 2 groups. ○ by cavern size | ○ | ○ |
| **Token and value effects** | ✔ NO_<season> honoured, UBIQUITOUS not (T2); quantity 0 stops (N1); BENIGN clear (T1); LP flip (E32b); CURIOUS_BEAST flags off keep bears (B); AT_PEACE overridden by a write (T1). ○ PRONE_TO_RAGE above 1; ○ LOOSE_CLUSTERS (weak at n=1); ○ CLUSTER_NUMBER written at run time; ○ SAVAGE/GIANT admission on a calm map via Add invasive | ○ FLIER-specific: none tested | ○ BEACH_FREQUENCY stranding of placed ORCA/SPERM_WHALE; ○ IMMOBILE_LAND | ○ | ○ | ○ UNDERGROUND_DEPTH: a species placed deeper than dmax stays? (`cav_ceiling`) | ○ | ○ NOBREATHE / FIREIMMUNE (placement only) |

**Never used:** CRAZED and OPPOSED_TO_LIFE. Both aim at the fort, never at wildlife [T1].

**Prerequisites before any water or cavern-water arm**
- The tool must write water-layer units (R12.8).
- The run must carry a manifest subject receipt, so no arm runs vacuously (memory: three did).

---

## 8. Known limits

- Realm tables are external knowledge. DF has no realms (see realms.md).
- The flying layer's DF actability is unknown until the raptor block runs. Every raptor edge is `df?` or `no`.
- The ladder's apex f may be moot if DF draws LPs from their own pool (wiki). If so, the tool controls apex presence by placement
  and quantity, not by FREQUENCY.
- Whether Add invasive can put a SAVAGE species (giant, extinct) on a calm embark, and whether DF keeps waving it, is untested
  (Q9 cross-biome question, same mechanism).
