# Roster + food-web builder v2: guild-first design (seasonal-wildlife, DF 53.16)

**v2.1 (30 Sep 2026):** rules marked *v2.1* below follow the user's rulings and ECO CAL. Code: `roster2.py` config `v21`
(`run2.py`); numbers: `results21.md`, `tables21.md`. The v2 text is kept in `runs/v2-orig/design.md`.

**v2.2 (30 Sep 2026, evening):** rules marked *v2.2* follow the user's second round of rulings. Code: `roster2.py` config `v22`
(+ `v22_savage`, `v22_good`, `v22_evil`, `v22_evil_savage`, `v22_floor20`, `v22_noveg`, `v22_civ`); numbers: `results22.md`,
`tables22.md`, `analyze22.out`. The v2.1 text is kept in `runs/design.v21.md.bak`.

**1 Oct 2026 review:** sections 5-8 now carry the answers the ECO night gave (block IDs from `../../findings.md`), and a new
section 9 records which v2.2 pieces seasonal-wildlife v7.0's ROSTER.build does not carry. The rules above are unchanged.

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
- *v2.2:* **the universe adds the GOOD and EVIL wildlife** (the tool's `mythic`/`unliving` classes: 8 GOOD, 23 EVIL with a
  BIOME) and the FANCIFUL-only yeti and sasquatch. GOOD species enter pools on good regions (`align='good'`), EVIL on evil ones;
  underground they enter whatever the surface alignment (the audit: the tags only limit taming there). Sentient GOOD/EVIL
  wildlife (ogre, troll, blendec, blizzard man, harpy, nightwing) hunts by its guild (a `monster` overlay).

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

- *v2.2:* colony vermin (VC: ants, bees) stay out of the flying pool (they sit on land in the VC slot); a **fisher** (BEAR_GRIZZLY,
  BEAR_BLACK, TIGER, JAGUAR) joins the ocean/lake/river pool where its land biome meets that water.
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
- *v2.2:* in the caverns **RP also eats PL, GZ, SH** (cave land prey; reach to be tested) and **LB (bugbats, floaters) eats
  VB, VI, VG** (cave vermin). This rejoins the cavern webs: 100% split in v2.1 -> 0%.
- *v2.2:* a **fisher** in a water pool also eats FF, FC, SH and WB (reach `untested`: the tool writes swim flags).
- *v2.2:* a creature with DF's own **GOBBLE_VERMIN_CLASS** (fowl, kiwi, hedgehog, pangolin: all EDIBLE_GROUND_BUG) gets stock
  edges to the vermin of that class (thrips, roach, beetle, ant) even when its guild has no diet.
- *v2.2:* **flying apex.** A surface raptor of at least 2 kg that is not a scavenger is an apex (calm: BIRD_EAGLE, the great
  horned and snowy owls, BIRD_OSPREY; savage adds Quetzalcoatlus, Sinopterus, Rhamphorhynchus to the boosted giant raptors).
  It eats RP below it (intraguild) and flying sentients (R7). BENIGN cleared (R12.5).
- **Tiers:** apex 3 > meso/raptor 2 > prey 1 > bird vermin 0.5 > other vermin 0. An edge must go strictly down a tier.
  - *v2.2 civ:* edge direction uses `etier()`: a cavern civ race counts as 2 (meso) even when the raws make it an apex.
  - This makes mutual predation and apex-on-apex impossible by construction: 0 of 36,026 main edges.
  - No size threshold is involved.
  - DF itself makes rival predators fight as STRANGERs [E11c]; the tool writes no such relation.

### R7. Humanoid rule (*v2.1*)

- A sentient target (animal person, CAN_SPEAK or CAN_LEARN) may be written only for an attacker in the **AL or AW guild**,
  including giants boosted into apex from those guilds (giant wolf, lion, crocodile). Boosted mesocarnivores and raptors stay
  out (user ruling). v2 allowed any LARGE_PREDATOR, or a giant CARNIVORE/BONECARN.
- **Animal people are attackers** by their own trophic guild (`ap_attack`; user 30 Sep: "let them be predators"). Civ races
  (AMPHIBIAN_MAN, REPTILE_MAN, SERPENT_MAN, RODENT MAN, TROGLODYTE, ANT_MAN, GREMLIN, PLUMP_HELMET_MAN) are never attackers.
- Consequence (v2.1): flying-layer animal people (insect-men, bird-men) had no allowed attacker there and never made a roster.
- *v2.2:* **the flying apex may take a flying sentient**, and a prey-guild animal person gets its own slot **SNP 0-1** beside
  SN on every layer (attacker animal people keep SN). Insect and bird men: 0 -> 880 of 880 savage flying rosters, all eaten;
  prey-guild animal people on savage land rosters 148 -> 866 of 880.
- *v2.2 civ* (user 30 Sep: "both, let them hunt and also be prey of cavern apexes"): the 8 cavern civ races (TROGLODYTE,
  RODENT MAN, AMPHIBIAN_MAN, REPTILE_MAN, SERPENT_MAN, ANT_MAN, GREMLIN, PLUMP_HELMET_MAN) **attack by their guild**
  (`civ_attack`) and **rank as meso (tier 2) for edge direction** (`civ_prey`), so every cavern apex above them may take them
  (AL/AW humanoid rule and the 5% floor still apply). A sentient GOOD/EVIL apex (troll, blind cave ogre, ogre) takes the apex
  slot, not SN (`monster_slot`), so it can share a roster with them. Singletons 20 -> 0; mutual predation and apex-on-apex stay 0.
  The builder never writes an edge for a forgotten beast, megabeast or other D8 class: their targeting stays DF's.

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
- *v2.2:* **floor 5%** (user). Edges whose group mass is at least **25%** of the prey's carry a **sneak bonus** flag (`res['sneak']`):
  the tool gives those hunters unit SNEAK. 87-100% of edges carry it; the 13% without are the 5-25% stretch hunts. CAL: below 5%
  DF only lost hunters (0 kills, 4 lost in 4 cell-reps); 5-20% gave 15 kills and 6 losses in 10.
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
   *v2.2:* **vegetation link.** A herbivore (GZ/PL/SH, prey tier, no CARNIVORE) with no predator still links, to one plant node,
   when the embark's vegetation index for its biomes is at least 20 + 15 x log10(mass / 100 kg). Weight 0.05, below any animal
   edge. In-tool survey: mean `vegetation` of the embark's region tiles and the grass-tile share, read at load.
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
- *v2.2:* **ladder22** (predators 31% of land arrivals in v2.1 was too high): land apex 4, meso 2, grazer 10.5, other prey 8.75,
  shore 7; flying apex 2, raptor 2, birds 30; water apex 3 (coastal and pelagic), meso 2, fish 12, shore 6, waterbirds 9,
  pelagic 2; caverns apex 3, meso 2, grazer 12, land prey 10, shore 8, birds 12. Each roster is scaled so its commonest member is
  100 (DF's cap). Calm predator share / apex share: land 0.16 / 0.07, flying 0.19 / 0.06, ocean 0.10 / 0.07, lake 0.10, river
  0.12, caverns 0.15-0.16.
- The tool writes this FREQUENCY per roster species. Arrival share = f / Σf per layer and pool [F1].
- Section 5 gives the values.

### R14. Vermin links are stock transfers

- No unit fights a vermin. The tool debits the prey family's stock in proportion to consumer presence, with a floor and a ceiling
  (v1 roster-reasoning rule C).
- Every VG/VC/VF/VB/VI edge is `stock`.
- *v2.2:* every vermin link is labelled (`res['vlinks']`): **native** (DF's GOBBLE_VERMIN_CLASS already covers it: 0.2%),
  **write** (the tool writes GOBBLE_VERMIN_CREATURE:<vermin>:<caste> on the consumer: 92%, about 6.4 per calm roster), or
  **tool** (vermin on vermin, pure bookkeeping: 8%).

---

## 2. Per-layer slot tables (slot: min-max, in fill order)

*v2.2:* every layer gains **SNP 0-1** (prey-guild animal person) right after SN; the cavern table gains **VI 0-2** (no vanilla
cavern flying insect exists, so it stays empty). The flying APX 0-1 slot now fills on calm maps (flying apex, R6).

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
| APX | 4 | DF's own LPs sit at 2-5. **LARGE_PREDATOR is a separate DF wave pool (wiki)**, so whether this number competes with prey is untested. *1 Oct:* the apex f does not visibly steer apex presence: 0 apex units in all 4 CTRL season runs, 0-3 on BOATS/OCEAN2 at f 13-27 [S8Cb], apex present in 1 of 6 SW4 runs at x0.5/x1/x2. Whether that is a separate pool or just rarity is still open (open item lp-separate-pool); the proposal is to drop the step (open item ladder-drop-apx-step, the user's call) |
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
- *1 Oct:* BOATS (ocean coast) has 33% of its water columns 3-4 levels deep [DEPTH: d3 8,564, d4 3,481 of 36,650]; v7.0's survey
  (ENGINE.deepColumns) found 0 of 5,374 ocean columns ≥ 3 on OCEAN2 [S8O]. v7.0 keys the PE boost on ocean columns, not lakes, so
  the lake case above does not arise in v7.0.

Resulting predator share of arrivals (main): land 0.14, ocean 0.06, river 0.13, caverns 0.08-0.15. Lake (0.54) and cavern water
(0.44) are predator-heavy, because their prey is mostly vermin.

---

## 6. Water and cavern specifics

*1 Oct 2026 review:* each question below now carries its answer and the block that settled it (findings.md block IDs).

### Ocean

- Shark apex, pelagic class and coastal fish; shore species (seals, walrus, penguins) sit on the boundary.
- ORCA and SPERM_WHALE are armable only as boosted apex with BENIGN cleared. **Answered:** the BENIGN orca made 0 attacks on
  written seals; with BENIGN cleared it killed 4 of 8 [HO, 1 run].
- Aquatic attackers never target land-only species [R8]. **Confirmed:** blue sharks took seals only in water (4/8; 1 of 8 ashore,
  one that entered the water) and never attacked deer [W1O]; tiger sharks 4/12 seals in water, 0/12 on shore [REACH, 2 reps].
- BEACH_FREQUENCY species (ORCA, SPERM_WHALE) may strand (wiki). **Answered for placed orcas:** 3 of 12 in unled pods drowned out of
  water within 15,000 t, 0 of 12 in led pods [COHO, 2 reps, small n]. The tool's own pelagic draw has never fired (the PE slot came
  out empty on OCEAN2 [S8O]), so `pelagic_beached` is untested. Open items orca-stranding-n, pelagic-slot-shallow-maps.
- Tiger sharks take swimming waterbirds: ducks 5 of 6 in both reps, penguins 2 and 3 of 6 [WB].

### Lake and river

- The apex is FISH_LAMPREY_SEA (temperate), ALLIGATOR, or CROCODILE_SALTWATER (tropical river). The temperate lake has no apex
  50% of the time.
  - **The lamprey is not a real apex:** 590 attacks on pike, 0 kills in 3,000 t [HR] (open item lamprey-not-apex).
  - **v2.2's fishers do not fill the gap:** grizzlies and tigers given CAN_SWIM_INNATE made 0 attacks on river pike in 4 runs, and
    wolves with swim and water-breathing flags never killed a pike [FSH2, FISH, HR]. v7.0 ships `fishers` off, so the temperate lake
    is apex-less about half the time again (open item lake-apex-gap, the user's call).
- Unit fish are few (4 FF species). Vermin fish carry most of the base, as stock.
- ~~Open question: are lake species feature entries or surface entries?~~ **Answered [LAKEP, 1 run]:** lake wild units are feature
  entries (layer 'water') that the tool puts in the surface realm ('land', since v6.9); 24 alligator x carp pairs were written and
  21 of 21 (with 7 carp alive) still held at every 500-t read to 3,000 t. Lake species are writable.
- Amphibious predators cross the shore both ways: alligators killed 5 of 8 deer and 5 of 8 capybaras from the water [W1L];
  saltwater crocodiles went ashore for 10 of 12 capybaras and took 12 of 12 swimming beavers [REACH]. Bull sharks took 8 of 8 pike
  in a river [HR]. Flow effects are untested.

### Cavern land

- Depth range is a hard gate; the bizarre score is a preference. FREQUENCY steers each cavern layer's own pool in proportion
  [ECO2-FC, 1 run: cavern 3 55/26/18% vs 57/29/14% predicted].
- `cav_ceiling` (dmin..3) makes cavw3 non-empty (80 more rosters) and grows cav3 from 8.1 to 10.0 species, but lowers DF-actable
  edges from 69% to 60%.
- cav1 has no non-sentient group hunter. With `sentient_attack` on, the civ races become the packs (v2.2 civ: `civ_attack`).
- **Measured:** cavern natives fight without a written relation for some pairs only: troll x gorlak and troglodyte x elk bird fought at
  two spots; jabberers, blind cave ogres and giant olms never fought unwritten but hunted when written (7/8 reachers, 3 rutherers);
  cave toads, crawlers and cave crocodiles moved with the spot [HC1-HC3 1 run, HC4 2 reps]. Keep the cavern relation write.
- Plump helmet men arrive as cavern herds of ~15 per wave (54 and 180 units a season on BOATS [S8B]): open item
  cavern-animal-person-group-cap (the user's call).

### Cavern water

- Four amphibious or aquatic LPs; sentients and vermin fish are the only in-pool prey.
- ~~The cross-edge reach is untested underground.~~ **Answered [HCP, 1 run; HC4 2 reps]:** cavern pools behave like surface water.
  CROCODILE_CAVE left the pool to kill 5 of 8 elk birds (and 5 and 4 at a second spot [HC4]); OLM_GIANT killed 7 crundles with a
  placed killer on record (8 died) when written; POND_GRABBER stayed wet 5/5 and made 1 attack: aquatic predators never leave
  cavern water. MODEL.reaches' habitat rules hold underground unchanged.

### Deep

- Degenerate (IMP_FIRE → MAGMA_CRAB). Only 2 natural species exist.
- **Seen on CTRL:** a deep layer delivered DEMON_* groups (15 and 16 units in 4-5 waves) in both S8C runs; the tool leaves them
  unmanaged by design (D8; open item deep-layer-demons). IMP_FIRE vs MAGMA_CRAB is still unmeasured.

---

## 7. What must be tested on the rig, per layer

Legend: ✔ measured (block); ○ open; the arm design follows the two-replicates-per-arm rule. *1 Oct review:* cells measured on
30 Sep – 1 Oct are marked ✔ with their block; "1 run" marks a cell with one replicate. Cells still ○ are collected in open item
design-s7-unmeasured-cells.

| item | land | flying | ocean | lake | river | cav1-3 | cavern water | deep |
|---|---|---|---|---|---|---|---|---|
| **Hunting on a written relation** | ✔ P1/T1: non-BENIGN acts, LP not needed. ✔ boosted BENIGN-cleared giant: GIANT_FOX 0/0 attacks as in raws, 2/10 with BENIGN off [TV2]. ✔ giant packs take megafauna [GPK]. ○ intraguild apex→meso (WOLF vs COYOTE; P2 placed them side by side unwritten: 0 attacks) | ✔ REACH: kea x parrot 5/12; eagle (BENIGN off) x raven 2/12, x rabbit 0/12 (0 attacks); owl x stork 1/12. ○ boosted giant raptor with BENIGN cleared | ✔ W1O shark x seal (water only) / x milkfish. ✔ ORCA cleared 4/8 seals [HO, 1 run]. ✔ shark x duck 5/6, x penguin 2-3/6 [WB]. ○ SPERM_WHALE cleared; ○ OCTOPUS (MW) as attacker | ✔ W1L alligator. ✔ lake species writable [LAKEP]. ○ FISH_LAMPREY_SEA vs BEAVER in water | ✔ bull shark x pike 8/8, lamprey 590 attacks 0 kills [HR, 1 run]. ✔ giant crocodiles x hippo 2/2 in all reps [GPKR]. ○ flow effect | ✔ E41e. ✔ written cavern pairs hunt; some natives fight unwritten [HC1-3, HC4]. ✔ giant bat x crundle 5/12 [REACH]. ○ LP vs a sentient civ-race group without the fort joining | ✔ cave croc crosses out 5/8; pond grabber never leaves water [HCP, HC4] | ○ IMP_FIRE vs MAGMA_CRAB (MAGMA fort) |
| **Groups, leaders, packs, herds** | ✔ L1/L2: a leader gives cohesion; a led herd was barely attacked (L2 1 run). ○ a led **pack** vs a led herd | ✔ flock cohesion with a leader: ducks 5-30 tiles vs 113-140 unled [COH] | ✔ school 6-7 vs 97-114 [COHO]; ✔ orca pod about half as wide (44-49 vs 87-100) [COHO]. In water a led school was not protected: sharks took 10 and 1 of led schools vs 5 unled [HO, 1 run] | ✔ carp school 1.8-2.3 vs 34 [HL, 1 run] | ✔ pike school 9-23 vs 142-149 [COHR] | ✔ gorlak/troglodyte cohesion [HC1/HC2, 1 run]. ✔ cavern groups-at-once: cap 1-2 trims the tool's groups ~40%, natives stay [SW5]. ○ civ-race groups 5:10 | ○ | ○ IMP_FIRE 3:4 |
| **Vermin eating (stock transfer)** | ✔ X5: HUNTS_VERMIN has no effect. ✔ GOBBLE class is specific; a written class or creature token works on the eater [VRM2] and a runtime class on the vermin [VRM4]. ○ the tool's stock debit shows in df.vermin counts | ○ bird vermin → insect debit; DIVE_HUNTS_VERMIN | ○ VF debit vs fishing yield | ○ VF debit (aquatic vermin do not restock: wiki bug 2780) | ○ same | ○ cave spider stock (caverns hold ≤ 2 vermin near any spot [VRC]) | ○ cave fish / olm stock | n/a |
| **Eating remains (walk + delete)** | ✔ S2: hyenas walk, eat, reload-safe. ✔ wolves ate 6 and 2 after a kill; ✔ JACKAL (borrowed ref) and vulture never got near [SCV]. ✔ tool pass clears land carcasses in ~2,400 t [SCV2b] | ✔ vulture walk fails [SCV]; ○ scav_ext's fliers-land path (never fired) | ○ corpses in water persist? (none removed by DF) | ✔ alligator walkto moves no swimmer; wolf on the bank cannot reach water corpses [SCVW] | ✔ tool pass clears river carcasses (pond grabber cell 6 → 0) [SCV2Wb] | ✔ DF removes no cavern corpse in 4,000 t [SCVC]; the troll walk failed underground [HC1]. ○ miasma | ○ | ○ remains in magma burn? |
| **Relative frequencies** | ✔ F1: land/surface non-bird pick ∝ FREQUENCY (1 run). ✔ predator multiplier x0.5 cuts predators to ~2% [SW4]. ✔ the apex step does not visibly steer apexes [S8, SW4] (LP pool mechanism still open) | ○ the flier pool ∝ FREQUENCY? Ravens dominate CTRL whatever the builder writes [S8C, S8Cb] (open item flier-pool-steering) | ○ water waves ∝ FREQUENCY? ✔ deep survey: OCEAN2 0 columns ≥ 3, PE slot empty [S8O] | ○ lake waves ∝ FREQUENCY | ○ | ✔ ∝ FREQUENCY per cavern layer [ECO2-FC, 1 run]. ○ does the bizarre preference show in waves? | ○ | ✔ deep waves on CTRL are demons [S8C]; ○ IMP/CRAB |
| **Group counts by embark size** | ✔ G1 + ECO2-G: √+1 adds ~1 group on 5x5/6x6 only. ✔ CTRL 4x4: cap 1 < 3 ≤ auto [SW3B]. ○ savage map: 2 LP groups? | ○ | ✔ water cap 2 = auto on BOATS (supply 2-5 groups) [SW6] | ○ | ○ | ✔ cavern limit soft: cap trims tool groups only [SW5] | ○ | ○ |
| **Token and value effects** | ✔ NO_<season> honoured, UBIQUITOUS not (T2, ECO2-W); quantity 0 stops (N1); BENIGN clear (T1); LP flip (E32b); CURIOUS_BEAST flags off keep bears (B, CB); AT_PEACE overridden by a write (T1). ✔ PRONE_TO_RAGE dose 25-100 [TV2]. ✔ LOOSE_CLUSTERS no effect [TV2]. ✔ FLEEQUICK, VISION_ARC no reliable effect [FVA]. ✔ SAVAGE smilodon not drawn on a calm map with its entry added [INV2]. ○ CLUSTER_NUMBER written at run time | ○ FLIER-specific: none tested | ✔ BEACH_FREQUENCY: placed unled orcas strand [COHO]. ○ IMMOBILE_LAND | ○ | ○ | ○ UNDERGROUND_DEPTH: a species placed deeper than dmax stays? (`cav_ceiling`) | ○ | ○ NOBREATHE / FIREIMMUNE (placement only) |

**Never used:** CRAZED and OPPOSED_TO_LIFE. Both aim at the fort, never at wildlife [T1].

**Prerequisites before any water or cavern-water arm**
- ~~The tool must write water-layer units (R12.8).~~ Done in v6.9 (water units join the ecology in the surface realm; LAKEP shows
  the write sticks).
- The run must carry a manifest subject receipt, so no arm runs vacuously (memory: three did; SCV2, S8C and INV run 1 were vacuous
  again on 30 Sep – 1 Oct and were rerun).

**A trap that applies to every land cell above.** A placed or tool-released unit loses DF's wild flag, so DF aims it at later wild
arrivals itself [RELS, RELS3]. Long cells with placed hunters (CAL, STL, LONE) killed natives this way. Score placed-only pairs.

---

## 8. Known limits

*1 Oct review:* each limit as it stands now.

- Realm tables are external knowledge. DF has no realms (see realms.md). v7.0 carries the realm table behind `realms` (off by
  default, `realm` sets the embark's realm; seasonal-wildlife e8cbda7, 466baec). It has never run on the rig and has no validator
  claim (open item realms-built-untested).
- ~~The flying layer's DF actability is unknown until the raptor block runs.~~ **Answered [REACH, 2 reps]:** fliers take fliers
  (kea x parrot 5/12; BENIGN-cleared eagle x raven 2/12; owl x stork 1/12) and cavern fliers take cavern prey (giant bat x crundle
  5/12), but a BENIGN-cleared eagle made 0 attacks on rabbits: raptor-on-land-prey edges are `df?` at best and should stay rare
  (open item builder-reach-table-refresh).
- ~~The ladder's apex f may be moot if DF draws LPs from their own pool.~~ **Answered in effect [S8Cb, SW4]:** apex arrivals were 0
  in all 4 CTRL season runs and 0-3 units elsewhere at f 13-27; in SW4 an apex was present in 1 run of 6 at any multiplier. The
  apex f does not visibly steer apex presence, whatever the mechanism (separate pool or rarity: open item lp-separate-pool).
  Proposal: drop the APX step and steer apexes by placement and stock (open item ladder-drop-apx-step, the user's call). Steering
  by placement or stock is itself untested (open item apex-placement-stock-test).
- ~~Whether Add invasive can put a SAVAGE species on a calm embark is untested.~~ **Answered for one species [INV2, 2 reps]:** with
  CENOZOIC_SMILODON's population entry added on calm CTRL, DF drew none in a full season (0 at 21 of 21 samples, both reps). Add
  invasive must place SAVAGE species itself on calm maps (open item add-invasive-savage-placement, the user's call). One species on
  one fort; INV run 1 (YETI) was vacuous (refused on biome).
- **New limits found 30 Sep – 1 Oct:**
  - The v2.1 ladder overshoots predators on land by pack size, not wave count (BOATS rep 1: giant jackals 27 units, 42% of surface
    units) [S8B]; a unit-share ladder is open (open item ladder-units-vs-waves).
  - On CTRL the roster barely moves the surface: ravens are most arrivals with or without the builder [S8C, S8Cb].
  - The sweep found no effect of cadence, nudge, floor, sneak or the x3 pack bonus [SW1/SW1R, SW2/SW2R, SW7], in an arena of placed
    wolves that DF aims itself; untested on natural arrivals (SW8).

---

## 9. What v7.0 carries of v2.2 (1 Oct review)

v7.0's ROSTER.build (seasonal-wildlife branch v7.0 @ 1e65e03, merged from roster-port 0d030b2) is a partial port. Read from the code
(seasonal-wildlife.lua ~5052-5100 ROSTER.SLOTS and the port's comments, ~5413 ROSTER.LADDER):

| v2.2 piece | in v7.0? | note |
|---|---|---|
| Guild-first slots, uniform pick, link guard, no-progress stop, unfilled report | yes | three layers only |
| Separate ocean / lake / river tables | **no** | one `water` table (AW, FC, FF, SH, MW, PE, WB) |
| Separate cav1-3 and cavw1-3 tables | **no** | one `cavern` table; per-depth groups-at-once exist (`layer_groups`) |
| Flying layer and flying apex (R6, v2.2) | **no** | RP 0-2 and LB 0-2 sit in the land table |
| SNP slot for prey-guild animal people (v2.2) | **no** | no SN/SNP slot; v7.0's `civ_hunt`/`civ_prey` switches cover cavern civ races |
| Apex boost for GIANT_* by flag (R4) | **no** | boost by mass ≥ 1,000,000 cm³ only (documented gap) |
| ladder22 (R13 v2.2) | **no** | ROSTER.LADDER is v2.1 (land AL 3, ML 3, GZ 6, PL 5, SH 4), rescaled so the roster max is 100; predicted ~31% land predators vs 16% (open item builder-port-vs-v22) |
| PE slot 0-1, 1-2 with ×3 weight on maps with ≥ 3-level ocean columns | yes | ENGINE.deepColumns; came out empty on OCEAN2 [S8O] |
| Vegetation link (R12.1 v2.2) | yes | V7.vegSupports, same formula |
| x3 pack bonus (R11 v2.1) | yes | SW7: no measurable effect; removal proposed (open item builder-drop-x3-pack-bonus) |
| 5% pack-mass floor, 25% sneak bonus | yes (tool switches `pack_floor`, `pack_sneak`) | SW2/SW2R: no measurable effect |
| v2.2 civ rules (civ races hunt and are prey; never write FB/megabeasts) | yes | `civ_hunt`, `civ_prey`, `fb_safe` |
| BENIGN clear on every armed predator (R12.5) | yes | |
| GOBBLE_VERMIN edge table (R14 v2.2 'write' links) and vermin stock links | **no** | v7.0 `gobble` writes runtime SWV_* classes by VERMIN.GOBBLE_RULES, not the builder's per-roster table (open item port-gobble-edge-table); stock transfers unbuilt (vermin-stock-bookkeeping) |
| Outgun warning (item 23) | yes (`outgun`, `roster outgun`) | no validator claim |
| Realm table | yes, off by default | never rig-tested |
| Season guard (R12.4) | partly | v7.0 `seasons_own` clears NO_<season> on managed species so the tool's season deal wins; the per-predator guard as written is not separately validated |

The validator (run 20261001-074833, 214 PASS) has no claim for ROSTER.build, the ladder, the unfilled report, the vegetation or
deep-water surveys, outgun or realms (open item validator-v70-coverage).
