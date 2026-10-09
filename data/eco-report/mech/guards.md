# Roster and food-web guard audit: seasonal-wildlife.lua at 4e9677f (v7.2-plugin)

I read every line number below at HEAD; the file has no local edits (19,017 lines). Nothing was edited or run, and port 5555 was not touched.

Classes: **A** = safety (DF freeze or crash, save scope, or state `off` cannot undo). **B** = ecology or plausibility, safe to switch off for testing. **C** = robustness (prevents a Lua error, a nil, or an endless loop).

## 1. Pool and classify

| Guard | Line | What it does / stated reason | If removed | Class | Switch (default) |
|---|---|---|---|---|---|
| Region set from all 9 `region_offset` neighbours, plus a 3x3 ring for cave entries | 1345, 1360-1373 | Manages every tile DF draws from. "X1: twenty cavies from a missed tile"; "Alpha Four 3.8: troglodytes from 168:173" | Narrower set: the leaks come back | B | none |
| Clamp/bounds on tile coordinates | 1347, 1372 | Keeps tile reads inside the world | Out-of-range reads | C | — |
| `POP_TYPES` (creature population types only) | 1436 | Ignores plant and tree populations | A plant's `race` would be read as a creature index, so the wrong species is managed | C | — |
| Embark-region membership | 1440 | Only this site's entries | Holds would hit populations across the whole world, and they are saved with it; I did not verify an undo path | A (scope) | — |
| `INNUMERABLE` (quantity_max ≥ 10,000,001) | 1442 (also 3990, 4085) | "never touch uncountable clouds" (the deep layers are INNUMERABLE, line 1387) | Would zero DF's sentinel entries. No experiment is cited; this is precautionary | A | — |
| Layer filter | 1443 | Enabled layers only | — | B | `cfg.layers` (land only) |
| `DOES_NOT_EXIST` / `EQUIPMENT_WAGON` | 2410 | Skips non-creatures | A wagon becomes a "species" | C | — |
| `creatureEligible` biome test | 2410 / 2309 | Fills only `eligible` (the Add-new view); the roster needs `inEmbark` | Little effect | B | — |
| Class lock: `locked`, `isAllowed`, `setActive`, `sanitizeLocked` | 2369, 2429, 2696, 1749 (called at 1139) | Mythic, mega, night, unliving, generated and unclassified never activate (D8) | Megabeasts, demons and forgotten beasts reach the roster and placement. Not a crash, but it can wreck a fort | B (gameplay hazard) | `cfg.classes` (natural only) |
| `defaultAllow` mega/night | 2427 | No apex/night creature activated by default | — | B | — |
| Aligned / cave-aligned / fanciful promotion (these *widen* the pool) | 1664-1693 | v7 user rulings | — | B | `v7.aligned`, `v7.cave_aligned`, `v7.fanciful` (all true) |
| Group floor of 1 | 1818 | `group ≥ 1` | `0^0.75` makes predator take 0 and need 0 | C | — |
| Curated ORCA is not BENIGN | 1828 | "ECO HO: orca 0 attacks on written seals" | — | B | — |
| Animal-person mass (GRAVITATE) and root mirror | 1867-1880 | R25/R57: "a damselfly man weighed 10 cm3" | Old mass bug comes back | B | `roster.ap_vermin_mass` (0) |
| Vermin-root person becomes a predator | 1876 | R25 | — | B | — |
| `casteFlagExists` | 1484 | "an unknown flag name RAISES … kills the whole tool" | Lua error | C | — |
| `V7.EXTINCT.model` role/guild/cluster fixes | 14314 | R24 | Extinct species revert to raw tags | B | `extinct.fix/roles/grazer/cluster` (true) |
| `V7.isCivRaw` | 2269 | Defines the cavern civ set | — | B | — |
| `eats()` (old matrix path): mega/night, `NEVER_PREY`, locked, eco, realm, REACH, shared water, peer cut at 0.5×, take ≥ need | 2558-2571 | W3: "lions ate sharks"; sponges (user, 5 Oct) | Nonsense edges in the old matrix path | B (`mass ≤ 0` check is C) | — |
| `MODEL.reaches` | 2576 | Same rules minus the size test (ECO v6.9) | Everything links to everything | B | — |

## 2. Builder (`ROSTER.build` and helpers)

| Guard | Line | What it does / reason | Class | Switch (default) |
|---|---|---|---|---|
| `inPart`: inEmbark, locked, vermin, mega, night | 7883 | Removing `inEmbark` seats species with no population entry on the map. The build becomes vacuous (see memory *manifest-subject-receipt*) | B, but keep `inEmbark` | — |
| `inPart`: cavern `fireOnly` | 7885 | R28: "lives in magma, DF places it" | B | — |
| `inPart`: `depthOk` raw depth range | 7887-7888 | R28 | B | `roster.depth_near` (false) widens by one layer |
| `inPart`: deep is never a roster layer | 7891 | R60 user ruling; no crash evidence cited | B by evidence; keep by ruling | — |
| `slotOf`: a civ race demoted from AL/AW to ML/MW | 7851-7852 | "never holds the apex slot" | B | `v7.civ_prey` (true) |
| `slotOf`: SN/SNP slots | 7855 | — | B | `roster.sn_slots` (false) |
| `slotOf`: water predator off the curated list becomes MW | 7857-7861 | R49: "sea lamprey 590 attacks, 0 kills" | B | `roster.aquatic_apex` |
| `flyApex`: RP, not sentient, not cavern, not a scavenger, ≥ 2000 cm3 | 7841-7844 | v2.2 rule | B | `roster.fly_apex_min` (2000) |
| `boosted`: mass ≥ 1e6, or a giant | 7834-7837 | R4 | B | `roster.giant_boost` (true) |
| `SLOTS` min/max caps and the `slotTable` map | 7902-7913, 7932-7935 | Wiki: 2 large-predator groups on a savage map | B | none (code table) |
| `linkable`: strictly one tier down, reaches, shared cavern depth | 7957-7964 | ECO2-FC | B | — |
| `realmOk` | 8016 / 2213 | Item 21 | B | `v7.realms` (false) |
| `pickWeight` multipliers | 7993-7994 | R41/R13/R26 | B | `roster.pack_bonus` 3, `ap_pick` 0.1, `giant_pick` 0.2 |
| `weightedPick` returns nil when total ≤ 0 | 8007 | — | C | — |
| Seed must have an edge | 8273 | R5 | B | — |
| Link guard: drop or swap isolates | 8339-8370 | R12.1 | B | none |
| Vegetation link | 8351, 7673 | Herbivore kept if the vegetation index ≥ need (10-90) | B | — |
| Outgun group cap | 8378-8385 | Warning always runs; the cap writes `group_size`, then CLUSTER_NUMBER, which is restored on disable | B | `v7.outgun` 2.0, `v7.outgun_cap` (false) |
| Deactivate unchosen species | 8399 | Builder by design | B | — |
| Gobble: a land APX eats no vermin; per-class caps | 8160, 8182 | R51 | B | `roster.gobble_max` (3) |

## 3. Ladder (`ROSTER.ladder`, line 8044)

| Guard | Line | What it does | Class | Switch (default) |
|---|---|---|---|---|
| Unknown guild weight = 5 | 8061 | Default weight | C | — |
| PE ×3 on deep columns | 8062 | R22 | B | — |
| Mass scale clamped to 0.25-4 | 8063 | Keeps weights in range | B | — |
| AP/giant FREQUENCY multipliers | 8068 | R26 | B | `roster.ap_freq` 0.25, `giant_freq` 0.5 |
| Level fallback when a level sum is 0 | 8074 | Avoids division by zero | C | — |
| Biomass guard | 8082-8087 | Carnivore biomass ≤ 0.5 × herbivore biomass | B | `roster.biomass_guard` 0.5 (0 = off) |
| Units ÷ group mean | 8092 | R59 | B | `roster.units` (true) |
| Floor of 1 | 8099 | Lifts any value that rounds to 0 | B. Redundant: every write already clamps to ≥ 1 (lines 3722, 3782) | — |
| Extinct apex read at its corrected FREQUENCY | 8110-8112 | — | B | `extinct.fix`, `extinct.freq` |
| `apex_raw_cap` | 8114 | Caps apex FREQUENCY ("16 extinct land apexes read 50") | B | `roster.apex_raw_cap` 5, `apex_odds` 0 |

**Trap in `apex_raw_cap`:** line 8111 treats 0 as "off", but line 8114 treats 0 as "cap at 0". With the cap set to 0, every apex with raw > 0 is written **1**. To disable the cap you must set 10,000,000, not 0.

## 4. Season casts

| Guard | Line | What it does / reason | Class | Switch (default) |
|---|---|---|---|---|
| `CAST` slot wants and vermin counts (3/2/3) | 8445-8460 | Cast size | B | none (code table) |
| Carry ×0.25, giant ×0.2, pack ×3, AP ×0.1 | 8461, 8645-8648 | Rotation and pick weights | B | `cfg.cast.carry/giant/pack`, `roster.ap_pick` |
| `highValue` seed preference | 8515-8535, 8670-8673 | Falls back to any linked species | B | `cast.hv_petvalue` 200, `hv_mass` 1e6 |
| `castSlot` FAPX remap; no slot means excluded | 8541, 8599 | — | B | — |
| `castVerminOk` | 8546-8551 | One entry per layer; V73_LAKE: "mussel filled both slots" | B | — |
| `castPool` raw `NO_<season>` | 8559, 8572 | Reads the raw's original flags (F10) | B | **none** |
| One vermin per token | 8571 | — | B | — |
| `castEats`: tier down, reaches, depth; vermin never eat | 8583-8594 | — | B | — |
| `castExcluded`: iterated removal of isolates | 8597-8615 | — | B | — |
| Sentient slot wants 0 | 8639 | — | B | `roster.sn_slots` |
| Emptiest slot first | 8697-8701 | — | B | — |
| Vermin: distinct classes first | 8723-8732 | — | B | — |
| `castManages`: rests locked species living on the layer; excludes mega/night (8753) and fireOnly (8754) | 8748-8756 | "no leaks" ruling (7 Oct) | B | — |
| Rest record for locked keys | 8793 | Survives `sanitizeLocked` | C (state integrity) | — |

**`castPool` and `seasons_own`:** the `NO_<season>` check in `castPool` ignores `seasons_own`. The other `NO_<season>` checks honour it (lines 3226, 6105).

## 5. Apply and runtime

| Guard | Line | What it does / reason | Class | Switch (default) |
|---|---|---|---|---|
| `CAVERN.write` clamps to ≥ 1 unless a floor is passed | 3722 | "NEVER WRITE 0 … CREEPY_CRAWLER froze DF" (addendum 54) | **A** | — |
| `CAVERN.apply` odds floor 1 | 3782 | Same reason | **A** | — |
| `restLevel`: any vermin tag stays at 1 | 3760-3766 | Addendum 54, 8 Oct | **A** | `cast.cavern_rest_freq` 1 (sanitised to 0..1 at 8488) |
| `holdLevel` never below 1 | 12871-12873 | Addendum 54 | **A** | — |
| `holdLevel` minimum 2, weight ÷10 | 12871-12873 | Keeps the season's mix (Alpha Four 3.8) | B | `groups.cavern_hold_mix` (true) |
| `holdFor` returns the rest level | 12884 | F9 | B | — |
| Cavern ceiling holds every cavern species | 3804 | — | B | `limits.cavern.ceiling` |
| `cavernHold`: natural only, not deep, not shared | 12915-12917 | A shared raw would also starve surface draws | B (deep: by ruling) | `groups.cavern_hold` 'any', `cavern_hold_shared` false |
| Trim acts only on natural units | 12846 | fb_safe | B | `groups.cavern_trim`, `cavern_trim_gated` (true) |
| `V7.GRP.orphans` | 12897 | Undo path: without it a hold could stay at 1 for good | C/A | — |
| `exhaustHolds` | 3099-3112 | Exhausted key not refilled until the season turns | B | `exhaust.enabled` (true) |
| `freqFloorApply` | 9135-9152 | R61: animal person at FREQUENCY 0 written 1; undone through `V7.rec` | B | `roster.ap_freq_floor` 1 |
| R60 deep: no placement or touch | 1412, 4983, 8548, 8936, 13093, 13129 | User ruling | B by evidence; keep | — |
| Lava-only placement refusals | 5003, 8957, 9217 | R28 | B | — |
| `civ_prey` ecology targets | 5591 | — | B | `v7.civ_prey` |

## Loop limits (not guards)

- Fill loop ≤ 200: line 8297.
- Link-guard loop ≤ 200: line 8342.
- Cast growth ≤ 400: line 8681.
- `castExcluded` stops when nothing changes: line 8603.

## Keep even in dev (A/C)

- **Never write a frequency below 1 where vermin or the default path is involved:** 3722, 3782, 3760-3766, 12871-12873.
- **Population scope:** `INNUMERABLE` (1442), `POP_TYPES` (1436), region membership (1440).
- **Robustness:** `DOES_NOT_EXIST`/wagon (2410), `casteFlagExists` (1484), group ≥ 1 (1818), ladder fallback and default weight (8061, 8074), `weightedPick` nil (8007), all loop limits.
- **Undo paths:** `orphans` (12897), the cast rest record (8793).
- **Keep on rulings, though not class A:** R60 deep exclusion (no crash evidence, but it is a user ruling), and the `inEmbark` test in `inPart` (without it the build has no subject on the map).

## Safe to remove for dev (B)

Everything else in sections 1-5, notably:

- the biomass guard, scale clamp, AP/giant multipliers and `apex_raw_cap`;
- slot and cast caps, link guard, seed-edge rule and `castExcluded`;
- tier, reach and depth rules in `linkable` and `castEats`;
- realms, flyApex/boosted thresholds, R49, the civ demotion;
- the `castPool` `NO_<season>` check, highValue, carry/pack weights;
- exhaustion holds and the outgun cap.

Class locks are also B, but they are dangerous for gameplay and already have their own switch, `cfg.classes`.

## Recommendation

Add one switch, `cfg.dev.no_guards`, default false, and reset it to false at load so it can never ship persisted. One predicate, `V7.dev(cfg)`, would gate the B sites:

- **Ladder:** skip the biomass guard, clamp, multipliers and `apex_raw_cap`; the floor of 1 can stay because it is harmless.
- **Builder:** set slot and cast caps to pool size; replace `linkable`/`castEats` with "any two distinct non-vermin species"; skip the link guard, the seed-edge rule and `castExcluded`; set pick and cast weights uniform; bypass `castPool`'s `NO_<season>`, `depthOk`, the roster-side `fireOnly`, the civ demotion, the flyApex/boosted thresholds, R49 and realms.
- **Logging:** add a LEDGER line on every build saying "dev: no guards".

The switch must **not** bypass:

- any write of a frequency below 1 (CREEPY_CRAWLER at frequency 0 froze DF, addendum 54);
- `INNUMERABLE`, `POP_TYPES` or region scope;
- R60 deep, the placement-side lava and deep refusals, and `inEmbark`;
- the undo paths;
- the Lua and loop guards;
- class locks (leave those to `cfg.classes`) and `fb_safe`.

Fix the `apex_raw_cap = 0` trap at the same time.
