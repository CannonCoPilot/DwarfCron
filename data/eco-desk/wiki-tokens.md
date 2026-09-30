# DF creature tokens: what the wiki documents (baseline for experiment design)

Fetched 2026-09-29 from the raw wikitext of https://dwarffortresswiki.org/index.php?title=Creature_token&action=raw (375 token anchors parsed) plus linked pages (URLs per row/answer). Definitions are quotes or close paraphrases of the wiki only. Nothing is inferred from token names. Where the wiki gives no functional effect, the row says so.

Level = the wiki's "Type" column. The page defines: "Creature" = creature-level only; "Caste" = may be applied to creature or caste; "CASTE-only" = caste only (none of the listed tokens are CASTE-only).

"Behaviour?" = does the wiki state an in-game effect on what the creature does, where and when it appears, or whether it survives (yes); only cosmetic, naming, economic or UI effects (no); or effect hedged with {{verify}}, "presumably", or a bug note (unclear).

Short URL form: CT#X = https://dwarffortresswiki.org/index.php/Creature_token#X

Local cross-check (not the wiki; noted where used): DF 53.16 vanilla raws at `.../Dwarf Fortress/data/vanilla/vanilla_creatures/objects/`, and `data/init/announcements.txt`.

## Token table: the user's list

| token | level | wiki functional definition | source URL | behaviour? |
|---|---|---|---|---|
| ALL_ACTIVE | Caste | "The creature will appear at any time of day." Overrides DIURNAL, NOCTURNAL, CREPUSCULAR, MATUTINAL, VESPERTINE. | CT#ALL_ACTIVE | yes (appearance timing; the sibling tokens are documented for Adventurer mode only) |
| AMBUSHPREDATOR | Caste | "Start out hidden and remain near its original location until its prey draws near." With WEBBER, lays gigantic webs near its spawn location, "only for creatures present during embark." Vanilla user: giant cave spider only (local raws). | CT#AMBUSHPREDATOR | yes |
| AMPHIBIOUS | Caste | Can breathe both in and out of water (unlike AQUATIC). Does not prevent drowning in magma. | CT#AMPHIBIOUS | yes |
| AQUATIC | Caste | "Enables the creature to breathe in water, but causes it to air-drown on dry land." | CT#AQUATIC | yes |
| ARTIFICIAL_HIVEABLE | Creature | Can be kept in artificial hives by beekeepers. | CT#ARTIFICIAL_HIVEABLE | no (husbandry only) |
| AT_PEACE_WITH_WILDLIFE | Caste | "Prevents the creature from attacking or frightening creatures with the NATURAL tag." Cat page: cats "will not perturb natural creatures" but can still be killed by cavern monsters. Vanilla user: CAT only (local raws). | CT#AT_PEACE_WITH_WILDLIFE ; https://dwarffortresswiki.org/index.php/Cat | yes |
| BEACH_FREQUENCY | Caste (int) | May strand on shores and "eventually air-drown"; the number is the frequency. "Presumably requires" AQUATIC. Used by orca, sperm whale, sea nettle jellyfish. The Beaching page says beached animals are "immobile and unable to breathe." | CT#BEACH_FREQUENCY ; https://dwarffortresswiki.org/index.php/Beaching | yes (the AQUATIC requirement is unverified) |
| BENIGN | Caste | "Non-aggressive by default, and will never automatically be engaged by companions or soldiers, running away from any creatures that are not friendly to it, and will only defend itself if it becomes enraged." The counterpoint of LARGE_PREDATOR. Also needed, with TRADE_CAPACITY, for PACK_ANIMAL to work. | CT#BENIGN | yes |
| BLOODSUCKER | Caste | Sucks the blood of unconscious victims when its thirst for blood grows large (vampire-like). Also seems to be needed for denunciation as a creature of the night. | CT#BLOODSUCKER | yes |
| BONECARN | Caste | "Creature eats bones. Implies CARNIVORE. Currently does not work due to a bug (11069)." The bug is adventure-mode only: a BONECARN adventurer cannot eat bones (https://dwarffortressbugtracker.com/view.php?id=11069). Bone meal page: BONECARN creatures "have never yet been observed consuming" bone meal. | CT#BONECARN ; https://dwarffortresswiki.org/index.php/Bone_meal | unclear |
| CAN_LEARN | Caste | Gains skills and can have professions. A civ member with it needs to eat, drink and sleep. Cannot be eaten by an adventurer. Enables values and goals (as does CAN_SPEAK). With MEANDERER, pathing becomes very slow. | CT#CAN_LEARN | yes |
| CAN_SPEAK | Caste | Can talk. Not needed to gain social skills, but needed to make friends in fortress mode. Enables values and goals. | CT#CAN_SPEAK | yes |
| CANNOT_CLIMB | Caste | "Cannot climb, even if it has free grasp parts." | CT#CANNOT_CLIMB | yes |
| CANNOT_JUMP | Caste | "Creature cannot jump." | CT#CANNOT_JUMP | yes |
| CARNIVORE | Caste | "Creature *only* eats meat. If the creature goes on rampages in worldgen, it will often devour the people/animals it kills." | CT#CARNIVORE | yes (diet restriction; devouring kills is stated for worldgen only) |
| CAVE_ADAPT | Caste | Develops cave adaptation. Also enables the "saw the sun and vomited" joke. | CT#CAVE_ADAPT | yes |
| CLUSTER_NUMBER | Creature (min:max) | "How many creatures per spawned cluster." Default 1:1. Vermin fish with it plus temperate ocean and river biomes "will perform seasonal migrations" (forum cite). The Creature page says it sets "how many creatures will appear at one time on a map." | CT#CLUSTER_NUMBER ; https://dwarffortresswiki.org/index.php/Creature | yes (group size) |
| COMMON_DOMESTIC | Caste | With PET, PACK_ANIMAL, WAGON_PULLER or MOUNT, it is always domesticated by civs with the matching COMMON_DOMESTIC_* entity token, even without wild populations. Invalid on FANCIFUL. | CT#COMMON_DOMESTIC | no (civ availability) |
| CRAZED | Caste | "Berserk", and "will attack all other creatures, except members of its own species that also have the CRAZED tag." Shows Berserk in the unit list. Rampages in worldgen much more often. No vanilla creature uses it (local raws: 0). | CT#CRAZED | yes |
| CREPUSCULAR | Caste | Appears at dawn (4:30-6:00) and evening (20:00-22:05) "in Adventurer mode." | CT#CREPUSCULAR | yes (adventure mode only; wiki gives no fortress effect) |
| CURIOUSBEAST_EATER | Caste | Steals and eats edible items from a site: grabs a food item and heads for the map edge, where it disappears with it. Steals food instead of attacking in worldgen rampages. Trained or tame instances stop doing this. | CT#CURIOUSBEAST_EATER ; https://dwarffortresswiki.org/index.php/Steals_food | yes |
| CURIOUSBEAST_GUZZLER | Caste | "(Very quickly) drink your alcohol. Or spill the barrel." Drinks on the spot rather than running off. Also affects undead versions. Tame instances stop. | CT#CURIOUSBEAST_GUZZLER | yes |
| CURIOUSBEAST_ITEM | Caste | Steals things, "apparently, of the highest value it can find," and heads for the map edge. Anything a CURIOUSBEAST carries off the map is reported as stolen. It "cannot drop hauled items until it enters combat." Tame instances stop. | CT#CURIOUSBEAST_ITEM | yes |
| DIE_WHEN_VERMIN_BITE | Caste | "Causes the creature to die upon attacking." Used by honey bees. | CT#DIE_WHEN_VERMIN_BITE | yes |
| DIURNAL | Caste | Only appears during the day (6:00-20:00) "in Adventurer mode." | CT#DIURNAL | yes (adventure mode only) |
| DIVE_HUNTS_VERMIN | Caste | Hunts vermin by diving from the air. On tame creatures it acts as HUNTS_VERMIN. Peregrine falcon. | CT#DIVE_HUNTS_VERMIN | yes |
| EXTRAVISION | Caste | Sees without working eyes, has 360-degree vision (cannot be hit from a blind spot), and sees invisible creatures. | CT#EXTRAVISION | yes |
| FISHITEM | Caste | The corpse is a single FISH_RAW item that must be cleaned at a fishery. Without it (or COOKABLE_LIVE), fished vermin butcher into multiple food units. | CT#FISHITEM | no (item form) |
| FLEEQUICK | Caste | "If engaged in combat, the creature will flee at the first sign of resistance." Kobolds (the only vanilla user, local raws). | CT#FLEEQUICK | yes |
| FLIER | Caste | Can fly, wings or not. Fortress pathfinding needs a land path to exist to an area, but the flier need not use it. Wings can be crippled. Winged creatures without FLIER cannot fly. | CT#FLIER | yes |
| GAIT | Caste (type, name, max speed, build-up, turn speed, start speed, energy, flags) | Defines a movement gait: WALK, CRAWL, SWIM (water or magma depth at least 4/7), FLY, CLIMB. Flags: AGILITY, STRENGTH, LAYERS_SLOW, STEALTH_SLOWS. Energy use tires the creature; persistent high intensity leads to exhaustion. | CT#GAIT ; https://dwarffortresswiki.org/index.php/Gait | yes |
| GNAWER | Caste (verb) | "Can and will gnaw its way out of animal traps and cages" depending on material (normally wood). | CT#GNAWER | yes |
| GOBBLE_VERMIN_CLASS | Caste (class) | "The creature eats vermin of the specified class." (That is all the page says.) Vanilla: 9 fowl and hedgehog, all `EDIBLE_GROUND_BUG` (local raws). | CT#GOBBLE_VERMIN_CLASS | unclear (one sentence, no mechanics) |
| GOBBLE_VERMIN_CREATURE | Caste (creature, caste) | "The creature eats a specified vermin." No vanilla user (local raws: 0). | CT#GOBBLE_VERMIN_CREATURE | unclear |
| GOOD | Creature | "Will only show up in good biomes." Lets USE_GOOD_ANIMALS civs domesticate it. No effect on cavern creatures except taming. The FREQUENCY entry says GOOD and EVIL creatures ignore the epicenter distribution system. | CT#GOOD ; CT#FREQUENCY | yes (spawn placement) |
| GRASSTRAMPLE | Caste (0-100) | How fast grass is trampled when stepped on. 0 = never, 100 = fastest. Default 5. | CT#GRASSTRAMPLE | yes (environment effect) |
| GRAZER | Caste (number) | Grazer: if tamed in fortress mode it needs a pasture to survive. Higher = eats less often. "Not used since 0.40.12, replaced by STANDARD_GRAZER." Grazer page: the value is the hunger reduction per grass unit; hunger rises every tick and death comes at 100,000. | CT#GRAZER ; https://dwarffortresswiki.org/index.php/Grazer | yes (documented for tame animals) |
| HUNTS_VERMIN | Caste | Hunts and kills nearby vermin, "randomly walking between places with food laying on the ground or in stockpiles, to check for possible [VERMIN_EATER] vermin, but they'll kill any other vermin too." Prevents an intelligent playable race from feeding itself. Vanilla: CAT only. | CT#HUNTS_VERMIN ; https://dwarffortresswiki.org/index.php/Remains | yes |
| IMMOBILE | Caste | "The creature cannot move." Also stops breeding in fortress mode. Sponges. | CT#IMMOBILE | yes |
| IMMOBILE_LAND | Caste | Immobile on land. Only works on AQUATIC creatures that can't breathe on land. | CT#IMMOBILE_LAND | yes |
| LARGE_PREDATOR | Caste | "Will attack other creatures that are smaller than it. Tamed large predators will still attack wildlife." Fortress: "only one group of 'large predators' (possibly two groups on 'savage' maps) will appear on any given map." A biome supports 7 large-predator species, each added by a d100 roll under its FREQUENCY. Worldgen rampages; embark intro text. | CT#LARGE_PREDATOR | yes |
| LARGE_ROAMING | Creature | "The core requisite tag allowing the creature to spawn as a wild animal in the appropriate biomes." Needs BIOME; frequency, population and cluster numbers are optional. Stacks with MEGABEAST, SEMIMEGABEAST and NIGHT_CREATURE_HUNTER, but not with FEATURE_BEAST (then it will not spawn). Cannot spawn in Pool biomes. | CT#LARGE_ROAMING | yes (spawning) |
| LAYS_EGGS | Caste | Lays eggs instead of live birth. | CT#LAYS_EGGS | yes (reproduction) |
| LAYS_UNUSUAL_EGGS | Caste (item, material) | Lays the specified item instead of regular eggs. | CT#LAYS_UNUSUAL_EGGS | yes (reproduction output) |
| LOOSE_CLUSTERS | Creature | "The creatures will scatter if they have this tag, or form tight packs if they don't." | CT#LOOSE_CLUSTERS | yes (group spacing; that is the whole definition) |
| LOW_LIGHT_VISION | Caste (number) | How well it sees in the dark. Higher is better; 10000 is perfect night vision (dwarves). | CT#LOW_LIGHT_VISION | yes |
| HAUL_REFUSE | **not a creature token**: labor token #5 | Labor token 5 = "Refuse hauling". Dwarves with this labor "haul rotting food, and non-dwarf bodyparts to refuse stockpiles" and dump marked items. Outdoor refuse collection is a standing-orders toggle. Creature-side link: RETURNS_VERMIN_KILLS_TO_OWNER cats drop remains "for a dwarf with refuse hauling enabled to clean up." No creature token maps to it. `HAUL_REFUSE` and "Refuse Hauling" both appear as strings in the DF 53.16 exe (local check). | https://dwarffortresswiki.org/index.php/Labor_token ; https://dwarffortresswiki.org/index.php/Hauling ; https://dwarffortresswiki.org/index.php/Refuse ; https://dwarffortresswiki.org/index.php/Cat | n/a (dwarf labor) |
| MATUTINAL | Caste | Appears only at dawn (4:30-6:00) "in Adventurer mode." | CT#MATUTINAL | yes (adventure mode only) |
| MEANDERER | Caste | "Slowly stroll around, unless it's in combat or performing a job." With CAN_LEARN, pathing is severely slowed. Since 52.05 it no longer applies to animal people or war- or hunting-trained animals. | CT#MEANDERER | yes (wiki does not say whether "slowly" means speed or wander pattern) |
| MISCHIEVOUS / MISCHIEVIOUS | Caste | **MISCHIEVOUS** is the spelling in the vanilla raws (1 use: GREMLIN, local raws; MISCHIEVIOUS: 0 uses). The wiki lists MISCHIEVIOUS as an "Alias for MISCHIEVOUS." Effect: spawns stealthed, paths into the fortress pulling any levers it finds, and stays invisible until spotted (then the game pauses). Trained gremlins stop (Gremlin page). | CT#MISCHIEVOUS ; https://dwarffortresswiki.org/index.php/Gremlin | yes |
| MOUNT | Caste | Can be a mount. No fortress use; sieging cavalry and adventure mode can use it. | CT#MOUNT | no (for wildlife behaviour) |
| MULTIPART_FULL_VISION | Caste | All-around vision if it has multiple heads that can see. | CT#MULTIPART_FULL_VISION | yes |
| MUNDANE | Creature | "Marks if the creature is an actual real-life creature. Only used for age-names at present." | CT#MUNDANE | no |
| NATURAL | Caste | "NATURAL animals will not engage creatures tagged with AT_PEACE_WITH_WILDLIFE in combat unless they are members of a hostile entity and vice-versa." 329 vanilla uses (local raws). | CT#NATURAL | yes (only relative to AT_PEACE_WITH_WILDLIFE) |
| NATURAL_ANIMAL | Caste | "Alias of NATURAL." 0 vanilla uses (local raws). | CT#NATURAL_ANIMAL | yes (same as NATURAL) |
| NO_AUTUMN | Caste | "The creature caste does not appear in autumn." | CT#NO_AUTUMN | yes (seasonal presence; no mode restriction stated) |
| NO_DRINK | Caste | "Creature does not need to drink." | CT#NO_DRINK | yes |
| NO_SPRING | Caste | Does not appear in spring. | CT#NO_SPRING | yes |
| NO_SUMMER | Caste | Does not appear in summer. | CT#NO_SUMMER | yes |
| NO_WINTER | Caste | Does not appear in winter. | CT#NO_WINTER | yes |
| NOBREATHE | Caste | Doesn't need to breathe; cannot drown or be strangled. Required for magma dwellers. | CT#NOBREATHE | yes |
| NOCTURNAL | Caste | Appears only at night (22:05-4:30) "in Adventurer mode." | CT#NOCTURNAL | yes (adventure mode only) |
| NOMEAT | Caste | "Creature will not be hunted or fed to wild beasts." (Wiki does not explain "fed to wild beasts".) | CT#NOMEAT | yes (hunting target selection); "fed to wild beasts" undocumented |
| ODOR_LEVEL | Caste (number) | How easy the creature is to smell. Higher = easier. Default 50; vanilla ranges 0 (undetectable) to 90 (noticeable by humans and dwarves). | CT#ODOR_LEVEL ; https://dwarffortresswiki.org/index.php/Smell | yes (detectability) |
| OPPOSED_TO_LIFE | Caste | "Hostile to all creatures except undead and other non-living ones." Used by undead. Living creatures given it attack living creatures that lack it. | CT#OPPOSED_TO_LIFE | yes |
| PACK_ANIMAL | Caste | Usable as a pack animal by merchants and adventurers. Prevents the creature dropping hauled items on its own. May lead to worldgen domestication. Without BENIGN, or with LARGE_PREDATOR, hauled items get dropped. | CT#PACK_ANIMAL | no (for wildlife) |
| PET | Caste | Tameable in Fortress mode; prerequisite for other working-animal roles. Civs encountering it in worldgen will domesticate it. | CT#PET | no (for wild behaviour) |
| PET_EXOTIC | Caste | Tameable, but civs cannot domesticate it in worldgen (with exceptions). "More difficult to tame?{{verify}}" | CT#PET_EXOTIC | unclear |
| PETVALUE | Caste (value) | Value of a tamed animal. Embark cost 1+(PETVALUE/2) untrained, 1+PETVALUE war or hunting trained. | CT#PETVALUE | no |
| POPULATION_NUMBER | Creature (min:max) | "How many of these creatures are present in each world map tile of the appropriate region." Default 1:1; a larger CLUSTER_NUMBER is used instead. Extinction page: when that many wild members die or are captured-and-kept at the fort, the species is "locally extinct" and removed from visitor rotation. | CT#POPULATION_NUMBER ; https://dwarffortresswiki.org/index.php/Extinction | yes (spawn cap / depletion) |
| PRONE_TO_RAGE | Caste (chance %) | "Percentage chance to flip out at visible non-friendly creatures. Enraged creatures attack anything regardless of timidity and get a strength bonus to their hits." Badgers. Vanilla: badger, black mamba, giant giraffe, wolverine (local raws). | CT#PRONE_TO_RAGE | yes |
| RETURNS_VERMIN_KILLS_TO_OWNER | Creature | If it kills a vermin and has an owner, "carries the remains in its mouth and drops them at their feet." Requires HUNTS_VERMIN. | CT#RETURNS_VERMIN_KILLS_TO_OWNER | yes |
| ROOT_AROUND | Caste (BY_TYPE/CATEGORY/TOKEN, part, verbs) | Occasionally roots in grass for insects. Adventure-mode flavour; in Fortress mode it "spawns vermin edible for this creature." Needs the named body part. | CT#ROOT_AROUND | yes (wiki does not say whether the spawned vermin are then eaten) |
| SAVAGE | Creature | "Will only show up in 'savage' biomes." No effect on cavern creatures. Cannot combine with GOOD or EVIL. FREQUENCY entry: SAVAGE "acts more like the biome tokens" (does not bypass epicenters). | CT#SAVAGE ; CT#FREQUENCY | yes (spawn placement) |
| SENSE_CREATURE_CLASS | Caste (class, tile, colour) | Senses creatures of that class beyond line of sight, through walls and floors. "Appears to reduce or negate" the blind combat penalty against sensed creatures. | CT#SENSE_CREATURE_CLASS | yes |
| SMALL_REMAINS | Caste | Leaves "remains" instead of a corpse. Used by vermin. Remains page: remains cause no miasma and leave no bones; "they simply disappear" as they rot. | CT#SMALL_REMAINS ; https://dwarffortresswiki.org/index.php/Remains | no (death product) |
| SMELL_TRIGGER | Caste (value) | How keen its sense of smell is; lower is better. At 10000 it cannot smell. | CT#SMELL_TRIGGER | yes (wiki does not say what smell is used for) |
| SPECIFIC_FOOD | Caste (PLANT/CREATURE, id) | "Will only appear in biomes with this plant or creature available." Grazers given a specific grass eat only that grass and can starve (pandas/bamboo). | CT#SPECIFIC_FOOD | yes |
| STANCE_CLIMBER | Caste | Can climb with STANCE parts instead of GRASP parts. | CT#STANCE_CLIMBER | yes |
| STANDARD_GRAZER | Caste | Acts as GRAZER with value 20000*G*(max size)^(-3/4), G default 100 (d_init), clamped to 150 to 3,000,000. Used for all vanilla grazers. | CT#STANDARD_GRAZER | yes (hunger rate) |
| SWIMS_INNATE | Caste | Swims perfectly without the swimmer skill. "However, Fortress mode AI never paths into water anyway." | CT#SWIMS_INNATE | yes (but fortress AI does not path into water) |
| SWIMS_LEARNED | Caste | Swims only as well as its swimming skill allows. | CT#SWIMS_LEARNED | yes |
| THICKWEB | Caste | Its webs "can catch larger creatures." | CT#THICKWEB | yes |
| TRAINABLE | Caste | Shortcut for TRAINABLE_HUNTING + TRAINABLE_WAR. | CT#TRAINABLE | no (for wildlife) |
| TRAINABLE_HUNTING | Caste | Can be trained as a hunting beast, "increasing speed." | CT#TRAINABLE_HUNTING | no (for wildlife) |
| TRAINABLE_WAR | Caste | Can be trained as a war beast, "increasing strength and endurance." | CT#TRAINABLE_WAR | no (for wildlife) |
| TRAPAVOID | Caste | Never triggers traps it steps on; still vulnerable to remotely triggered traps. Loses the ability when immobilized in a trap (web, paralysis, unconsciousness). | CT#TRAPAVOID ; https://dwarffortresswiki.org/index.php/Trapavoid | yes |
| TRIGGERABLE_GROUP | Creature (min:max) | "A large swarm of vermin can be disturbed, usually in adventurer mode." Vanilla: bat, rat, demon rat, large roach (5:50), fluffy wambler (50:100) (local raws). The VERMIN_DISTURBED announcement exists (Announcements.txt page). | CT#TRIGGERABLE_GROUP | unclear (the fortress effect is not described) |
| UBIQUITOUS | Creature | "Will occur in every region with the correct biome." Territory covers the whole map; acts as FREQUENCY:100 for the spawn roll, but can still be crowded out of a region's 7-slot list. Does not apply to EVIL/GOOD tags. | CT#UBIQUITOUS ; CT#FREQUENCY | yes (spawn) |
| UNDERGROUND_DEPTH | Creature (min:max, 0-5) | Depth the creature appears at: 0 above ground, 1-3 cavern layers, 4 magma sea, 5 HFS. Depth-5 FLIERs join the HFS initial wave; without FLIER they spawn from map edges. Civs export only depth-1 things. | CT#UNDERGROUND_DEPTH | yes (spawn layer) |
| UNDERSWIM | Caste | "Displayed as blue when in 7/7 water." Used on fish and amphibious creatures that swim under water. | CT#UNDERSWIM | no (display only per wiki) |
| VERMIN_BITE | Caste (chance{{verify}}, verb, material, state) | Lets vermin bite other creatures, injecting the specified material. "Presumably" works like SPECIALATTACK_INJECT_EXTRACT {{verify}}. | CT#VERMIN_BITE | yes (the mechanics are unverified) |
| VERMIN_EATER | Creature | "The vermin creature will attempt to eat exposed food." See PENETRATEPOWER (getting into containers). "Distinct from VERMIN_ROTTER." Vanilla: hamster, lizard(s), rat, demon rat, large roach, fluffy wambler (local raws). | CT#VERMIN_EATER ; CT#PENETRATEPOWER | yes |
| VERMIN_FISH | Creature | Appears in water and swims around. Required for fishing or live-fish capture. | CT#VERMIN_FISH | yes |
| VERMIN_GROUNDER | Creature | Appears in "general" surface ground locations; still flies if it can. Also one of the 5 per-region wildlife lists (FREQUENCY entry). | CT#VERMIN_GROUNDER | yes (spawn location) |
| VERMIN_HATEABLE | Caste | Some dwarves hate it and get unhappy thoughts near it. | CT#VERMIN_HATEABLE ; https://dwarffortresswiki.org/index.php/Hateable | no (dwarf thoughts only) |
| VERMIN_MICRO | Caste | "Move in a swarm of creatures of the same race" (flies, ants). | CT#VERMIN_MICRO | yes |
| VERMIN_NOFISH | Caste | Cannot be caught by fishing. | CT#VERMIN_NOFISH | no (capture only) |
| VERMIN_NOROAM | Caste | "Will not be observed randomly roaming about the map." | CT#VERMIN_NOROAM | yes |
| VERMIN_NOTRAP | Caste | Cannot be caught in baited animal traps; a "catch live land animal" task may still catch one. | CT#VERMIN_NOTRAP | no (capture only) |
| VERMIN_ROTTER | Creature | "Attracted to rotting stuff and loose food left in the open and cause unhappy thoughts to dwarves who encounter them." Flies, knuckle worms, acorn flies, blood gnats (vanilla also creepy crawler, local raws). Wiki does not say rotters consume anything. | CT#VERMIN_ROTTER | yes (attraction; no consumption documented) |
| VERMIN_SOIL | Creature | Appears near dirt or mud; can be uncovered by ROOT_AROUND creatures; ignored by "Capture live land animal." | CT#VERMIN_SOIL | yes (spawn location) |
| VERMIN_SOIL_COLONY | Creature | Appears as "a single tile cluster of many vermin, such as a colony of ants." | CT#VERMIN_SOIL_COLONY | yes (spawn form) |
| VERMINHUNTER | Caste | "Old shorthand for 'does cat stuff'": AT_PEACE_WITH_WILDLIFE + RETURNS_VERMIN_KILLS_TO_OWNER + HUNTS_VERMIN + ADOPTS_OWNER. 0 vanilla uses (local raws). | CT#VERMINHUNTER | yes (via its components) |
| VESPERTINE | Caste | Appears only in the evening (20:00-22:05) "in Adventurer mode." | CT#VESPERTINE | yes (adventure mode only) |
| VIEWRANGE | Caste (value) | "Value should determine how close you have to get to a critter before it attacks (or prevents adv mode travel etc.)" Default 20. | CT#VIEWRANGE | unclear (hedged "should") |
| VISION_ARC | Caste (binocular, non-binocular) | Vision arc widths in degrees; default 60:120; limits about 10 and 350. | CT#VISION_ARC | yes |
| WAGON_PULLER | Caste | Can pull caravan wagons. | CT#WAGON_PULLER | no (for wildlife) |
| WEBBER | Caste (material) | Can create webs; defines the web material. With AMBUSHPREDATOR, lays giant webs near its spawn location (embark-present creatures only). | CT#WEBBER | yes |
| WEBIMMUNE | Caste | Not caught in thick webs. | CT#WEBIMMUNE | yes |

## Token table: also requested

| token | level | wiki functional definition | source URL | behaviour? |
|---|---|---|---|---|
| FREQUENCY | Creature (0-100; default 50) | Two roles. **(1) Placement:** each creature gets a random world epicenter and a square "territory" of Manhattan radius FREQUENCY/100 x world size. Each sub-region fills 5 lists (VERMIN_GROUNDER, VERMIN_SOIL, VERMIN_SOIL_COLONY, LARGE_ROAMING, LARGE_PREDATOR) with the 7 nearest valid creatures (right token + biome + territory overlap). The overlap rule is dropped if a list can't fill; orphans attach to the nearest sub-region (lists of 8+ possible). GOOD and EVIL ignore epicenters; SAVAGE does not. **(2) On-map spawning:** fortress mode spawns large wildlife in "fairly regular waves" in separate pools: LARGE_ROAMING, LARGE_ROAMING+FLIER, LARGE_PREDATOR, CURIOUS_BEAST. It picks a creature uniformly from the region list, then rolls d100 against FREQUENCY and reselects on failure. UBIQUITOUS = always passes. (The wiki page files this entry under "Attack Tokens"; that is a page-layout artifact.) | CT#FREQUENCY | yes |
| BIOME | Creature (biome token) | "Select a biome the creature may appear in." Ocean biome tokens are only OCEAN_TROPICAL, OCEAN_TEMPERATE, OCEAN_ARCTIC and ANY_OCEAN (Biome token page). No depth variants. | CT#BIOME ; https://dwarffortresswiki.org/index.php/Biome_token | yes (spawn eligibility) |
| CURIOUSBEAST (bare) | not a token | No `CURIOUSBEAST` anchor exists on the page. The variants are the three CURIOUSBEAST_* tokens above. The FREQUENCY entry names a "CURIOUS_BEAST" spawn-wave pool as if it were a token, but there is no CURIOUS_BEAST token entry and 0 uses in the vanilla raws (local check). How a creature joins that pool is **not documented**. | CT#FREQUENCY | n/a |

## Token table: extras the page describes as affecting spawning, diet, hunting, aggression, fleeing, grouping, remains, or movement

| token | level | wiki functional definition | source URL | behaviour? |
|---|---|---|---|---|
| NOFEAR (extra) | Caste | "Doesn't feel fear and will never flee from battle." Immune to ghost scaring; bogeymen and nightmares are friendly to it. | CT#NOFEAR | yes |
| NO_EAT (extra) | Caste | "Creature does not need to eat." | CT#NO_EAT | yes |
| NO_SLEEP (extra) | Caste | Does not need to sleep; can still be knocked unconscious. | CT#NO_SLEEP | yes |
| MAGICAL (extra) | Caste | Per Toady (forum cite), "completely interchangeable with AT_PEACE_WITH_WILDLIFE." | CT#MAGICAL | yes |
| VEGETATION (extra) | Caste | "Like AT_PEACE_WITH_WILDLIFE," plus art value to PLANT-sphere civs. Grimelings. | CT#VEGETATION | yes |
| EVIL (extra) | Creature | "Will only show up in evil biomes." Ignores the epicenter system (FREQUENCY entry). No effect on cavern creatures except taming. | CT#EVIL | yes (spawn) |
| NOT_LIVING (extra) | Caste | Cannot be raised; OPPOSED_TO_LIFE undead are docile toward it. | CT#NOT_LIVING | yes |
| NIGHT_CREATURE_HUNTER (extra) | Caste | Always hostile; starts no-quarter combat with nearby creatures except its own race {{verify}}; can still flee battles it started. Stacks with LARGE_ROAMING (spawns as wild animal too). | CT#NIGHT_CREATURE_HUNTER | yes |
| BUILDINGDESTROYER (extra) | Caste (1 or 2) | Destroys furniture and buildings. 1 = doors, hatches, furniture; 2 = anything not built with b+C. | CT#BUILDINGDESTROYER | yes |
| MEGABEAST / SEMIMEGABEAST (extra) | Caste | Worldgen "boss" with tracked history and rampages; arrival popup in fortress. Stacks with LARGE_ROAMING. | CT#MEGABEAST | yes |
| FEATURE_BEAST (extra) | Caste | Forgotten-beast behaviour "presumably" {{verify}}. Does not stack with LARGE_ROAMING (then it will not spawn). | CT#FEATURE_BEAST | unclear |
| POP_RATIO (extra) | Caste (max 100000) | Weighted population of a caste; lower is rarer. "Not to be confused with FREQUENCY." 0 prevents natural spawning of that caste (51.06+). | CT#POP_RATIO | yes (caste mix) |
| CHANGE_FREQUENCY_PERC (extra) | Creature (int) | "Multiplies frequency by a factor of (integer)%." (Creature-variation use.) | CT#CHANGE_FREQUENCY_PERC | yes (spawn weight) |
| DOES_NOT_EXIST (extra) | Creature | Prevents the creature from appearing in generated worlds (unless ANIMAL_ALWAYS_PRESENT). | CT#DOES_NOT_EXIST | yes (spawn) |
| LITTERSIZE / CLUTCH_SIZE / MULTIPLE_LITTER_RARE (extra) | Caste | Offspring per birth (default 1-3); eggs per clutch; 1/500 chance of a multiple litter. | CT#LITTERSIZE ; CT#CLUTCH_SIZE ; CT#MULTIPLE_LITTER_RARE | yes (reproduction) |
| MAXAGE (extra) | Caste (min:max years) | A predetermined death date between the bounds, fixed per individual; without MAXAGE the creature is immortal. Death probability does not rise with age. | CT#MAXAGE | yes (lifespan) |
| PENETRATEPOWER (extra) | Caste | Vermin ability to get into containers when eating stockpiled food. Container rolls 0-100 (wood/leather/amber/coral 0-95, cloth 0-90); if the roll > power, contents "escape for the time being." | CT#PENETRATEPOWER | yes (feeding) |
| ITEMCORPSE (extra) | Caste (item, material) | Leaves a non-standard corpse item (wood, statue, bars, liquid...). | CT#ITEMCORPSE | no (death product) |
| REMAINS (extra) | Caste (sing, plural) | Name of the creature's remains. | CT#REMAINS | no |
| REMAINS_ON_VERMIN_BITE_DEATH (extra) | Caste | With VERMIN_BITE + DIE_WHEN_VERMIN_BITE, leaves remains on biting death; otherwise it "disappear[s] entirely." | CT#REMAINS_ON_VERMIN_BITE_DEATH | no (death product) |
| NOT_BUTCHERABLE (extra) | Caste | Corpse cannot be butchered. | CT#NOT_BUTCHERABLE | no |
| NOSMELLYROT (extra) | Caste | Produces no miasma when rotting. | CT#NOSMELLYROT | no (corpse environment effect) |
| GETS_INFECTIONS_FROM_ROT (extra) | Caste | Gets infections from necrotic tissue. | CT#GETS_INFECTIONS_FROM_ROT | yes (health) |
| COLONY_EXTERNAL (extra) | Caste | "Caste hovers around colony." | CT#COLONY_EXTERNAL | unclear (one line) |
| HABIT / HABIT_NUM (extra) | Caste | Lair habits: COLLECT_TROPHIES, COOK_PEOPLE, COOK_VERMIN, GRIND_VERMIN, COOK_BLOOD, GRIND_BONE_MEAL, EAT_BONE_PORRIDGE, ... Require LAIR and apparently megabeast, semimegabeast or night-creature status. | CT#HABIT | yes (lair creatures only) |
| LAIR / LAIR_HUNTER (extra) | Caste | Seeks sites of the given type as lairs; hunts adventurers in its lair. | CT#LAIR | yes (not ordinary wildlife) |
| NO_VEGETATION_PERTURB (extra) | Caste{{verify}} | "Likely prevents the creature from leaving broken vegetation tracks.{{verify}}" | CT#NO_VEGETATION_PERTURB | unclear |
| NO_CONNECTIONS_FOR_MOVEMENT / NO_THOUGHT_CENTER_FOR_MOVEMENT (extra) | Caste | Moves without connected parts {{verify}}; motor function without a THOUGHT organ. | CT#NO_THOUGHT_CENTER_FOR_MOVEMENT | yes/unclear |
| LOCAL_POPS_CONTROLLABLE (extra) | Creature | Playable as a wild animal in adventure mode. | CT#LOCAL_POPS_CONTROLLABLE | no |
| BODY_SIZE (extra) | Caste | Size by age (cm^3, about grams). Used by STANDARD_GRAZER and LARGE_PREDATOR ("smaller than it"). | CT#BODY_SIZE | yes (indirectly, via those tokens) |

---

## Answers

### 1. Scavenging; what BONECARN, CARNIVORE, VERMIN_EATER, VERMIN_ROTTER and GOBBLE_VERMIN_* do

- **Scavenging of corpses, remains or refuse by any creature: not documented** in any mode. A full-text wiki search for "scavenge", "carrion", "eat corpses" and "eats corpses" found no mechanic.
  - The Vulture page describes food theft (CURIOUSBEAST_EATER), not carrion eating: https://dwarffortresswiki.org/index.php/Vulture
  - Corpses and remains only rot (miasma underground), get hauled as refuse, or reanimate in evil biomes: https://dwarffortresswiki.org/index.php/Corpse , https://dwarffortresswiki.org/index.php/Remains , https://dwarffortresswiki.org/index.php/Refuse
  - The only corpse-consumption text is CARNIVORE: "If the creature goes on rampages in **worldgen**, it will often devour the people/animals it kills." That is worldgen only (CT#CARNIVORE).
  - The only other "eating" of remains-type things is night-troll lair HABITs (COOK_VERMIN, GRIND_BONE_MEAL, EAT_BONE_PORRIDGE). These require LAIR and are "apparently" limited to megabeasts, semimegabeasts and night creatures (CT#HABIT).
- **BONECARN:** "Creature eats bones. Implies CARNIVORE. Currently does not work due to a bug (11069)."
  - Bug 11069 is about a BONECARN *adventurer* being unable to eat bones: https://dwarffortresswiki.org/index.php/Creature_token#BONECARN , https://dwarffortressbugtracker.com/view.php?id=11069
  - No wild-animal bone-eating is documented.
- **CARNIVORE:** "only eats meat". Worldgen devouring as above. The wiki does not describe wild carnivores feeding on the fortress map.
- **VERMIN_EATER:** vermin that "attempt to eat exposed food". PENETRATEPOWER governs getting into containers. HUNTS_VERMIN cats patrol food piles "to check for possible [VERMIN_EATER] vermin" (CT#VERMIN_EATER, CT#PENETRATEPOWER, CT#HUNTS_VERMIN).
- **VERMIN_ROTTER:** "attracted to rotting stuff and loose food left in the open", and causes unhappy thoughts. No consumption or removal of rot is stated (CT#VERMIN_ROTTER).
- **GOBBLE_VERMIN_CLASS / _CREATURE:** "eats vermin of the specified class" / "eats a specified vermin". Nothing more is documented: no frequency, no hunger effect, no mode.
  - Related: ROOT_AROUND "spawns vermin edible for this creature in Fortress Mode" (CT#ROOT_AROUND).
  - Vanilla pairs the two tokens only on fowl and hedgehog, with class `EDIBLE_GROUND_BUG` (local raws).

### 2. Animal-vs-animal combat and announcements (DF 50+)

- The wiki does not specifically address wildlife-vs-wildlife fights. What it documents:
  - Combat goes to **Reports**, not Announcements. "Reports are messages detailing either combat (both practiced and real) between creatures ... every battle will give at least two reports, one from either side." The red report is "<creature> is fighting!", and "a hunted animal will be considered fighting." https://dwarffortresswiki.org/index.php/Reports
  - Wild animals "are automatically detected as they enter the map, but have no special announcement associated with them." https://dwarffortresswiki.org/index.php/Thief
- **Config:** there are per-type toggles, both in the in-game Settings > Announcements tab and in `announcements.txt`. Defaults live in `data/init/announcements.txt`, current settings in `prefs/announcements.txt`. https://dwarffortresswiki.org/index.php/Announcement , https://dwarffortresswiki.org/index.php/Announcements.txt
  - Options per type: BOX/DO_MEGA (Popup), P (Pause), R (Recenter), A_D (adventure display), D_D (fort display), UCR / UNIT_COMBAT_REPORT (goes into reports; creates a new report if none is active), UCR_A (only adds to an active report), ALERT.
  - Bug note: removing an option in prefs does not disable it if the init file enables it (bug 13034).
- **Types covering fights** (Announcements.txt page): 43 COMBAT_* types, "used in combat, most often in adventure mode (also in the arena)":
  - COMBAT_STRIKE_DETAILS ("Strike"), COMBAT_STRIKE_DETAILS_2 ("Wounds"), COMBAT_DODGE, COMBAT_BLOCK, COMBAT_PARRY, COMBAT_COUNTERSTRIKE, COMBAT_CHARGE_*, COMBAT_WRESTLE_*
  - COMBAT_EVENT_ENRAGED (example "The Wolf has become enraged!"), COMBAT_EVENT_KNOCKED_OUT, COMBAT_EVENT_STUNNED
  - Other relevant types: ADV_CREATURE_DEATH ("The Wolf has been struck down."), PET_DEATH, CITIZEN_DEATH, BEAST_AMBUSH, BIRTH_WILD_ANIMAL, VERMIN_BITE, VERMIN_DISTURBED, ANIMAL_TRAP_CATCH.
- The wiki does not say whether fights between two wild animals, with no citizen involved, generate reports in fortress mode: **not documented**.
- Local rig defaults (53.16, data/init and prefs agree):
  - Fort display (D_D) is off for all combat detail: `COMBAT_STRIKE_DETAILS:A_D:UCR`, `COMBAT_STRIKE_DETAILS_2:A_D:UCR`, `COMBAT_DODGE:A_D:UCR`, `COMBAT_EVENT_ENRAGED:A_D:UCR`.
  - Death types: `ADV_CREATURE_DEATH:A_D:D_D:UCR_A`, `PET_DEATH:A_D:D_D:UCR_A`, `CITIZEN_DEATH:A_D:D_D:UCR_A:ALERT`, `BIRTH_WILD_ANIMAL:A_D:D_D`.

### 3. Wildlife groups: leaders, herds, packs, group size, population depletion

- **Leaders: not documented.** No wiki page or token describes a wildlife group leader. The page's only "leader" mention is SPHERE/deity leadership of civilized groups.
- **Group size:**
  - CLUSTER_NUMBER min:max = "how many creatures per spawned cluster" (default 1:1) (CT#CLUSTER_NUMBER). The Creature page: "how many creatures will appear at one time on a map" (https://dwarffortresswiki.org/index.php/Creature). Vulture page example: "flocks of 5-10."
  - The Extinction page adds that group size also "depends on the number of biomes you abridge," and that clusters can't exceed the remaining cap.
- **Spacing:** LOOSE_CLUSTERS: "will scatter if they have this tag, or form tight packs if they don't" (CT#LOOSE_CLUSTERS). No other herding or cohesion behaviour is documented.
- **One group at a time:**
  - LARGE_PREDATOR: "only one group of 'large predators' (possibly two groups on 'savage' maps) will appear on any given map" (CT#LARGE_PREDATOR).
  - Ambusher (hunting) page: "Only one group of animals will appear at any given time, and as soon as one group leaves another will take its place" per layer (surface and each cavern) (https://dwarffortresswiki.org/index.php/Ambusher).
  - Surroundings: savage biomes may get two groups (https://dwarffortresswiki.org/index.php/Surroundings). Cavern: "subterranean groups of creatures are limited to one group at a time" (https://dwarffortresswiki.org/index.php/Cavern).
  - Separately, FREQUENCY describes waves in separate pools: LARGE_ROAMING, LARGE_ROAMING+FLIER, LARGE_PREDATOR, CURIOUS_BEAST (CT#FREQUENCY).
- **POPULATION_NUMBER depletion** (https://dwarffortresswiki.org/index.php/Extinction , https://dwarffortresswiki.org/index.php/Creature):
  - Per world-map tile of the region (CT#POPULATION_NUMBER); a larger CLUSTER_NUMBER overrides it. Deer example: 15:30, "if you kill between 15-30 deer, no more deer will ever visit your fortress."
  - Wild non-siege-mount animals that **die or are captured and kept** count toward the cap. At the cap the species is "locally extinct" and "taken out of the wildlife visitation rotation."
  - The cap is **biome-specific** (multi-biome sites get more). Mass hunting "can eventually prevent any wildlife from spawning at all."
  - "As long as at least one animal in that cluster is allowed to leave, the species will not have been considered depleted" (forum-sourced nuance). The Ambusher page repeats this.
  - Aquatic vermin do not restock when fished (bug 2780).
  - "Supposedly" populations slowly regenerate via world activities (mantis 2780 note); whether locally extinct ones do is "unknown".
  - Cavern populations "are usually far more than their raws imply" (Cavern page).
  - Vermin "do not breed, but 'spawn'"; "some types of vermin are inexhaustible" (https://dwarffortresswiki.org/index.php/Vermin). The wiki does not say which ones.
  - DFHack `region-pops` can restore or remove populations.

### 4. Deep vs shallow ocean placement; real-world geography

- **Deep vs shallow ocean placement: not documented.**
  - Ocean biome tokens are only OCEAN_TROPICAL, OCEAN_TEMPERATE, OCEAN_ARCTIC and ANY_OCEAN, split by temperature, not depth (https://dwarffortresswiki.org/index.php/Biome_token). The vanilla raws use exactly these four (local check).
  - The Ocean page's wildlife section only notes that frozen arctic oceans lack aquatic creatures while frozen (https://dwarffortresswiki.org/index.php/Ocean).
  - Water-depth mentions concern display (UNDERSWIM: blue in 7/7 water) and SWIM gait (used at depth of at least 4/7), not placement.
  - BEACH_FREQUENCY is the only shore-related creature token.
- **Real-world geography: none documented.**
  - Placement is by biome token plus a *random* world epicenter per creature with a FREQUENCY-sized territory (CT#FREQUENCY). No continent, realm or real-world range concept appears.
  - MUNDANE marks real-life creatures but is "only used for age-names at present."
  - The 53.15 extinct creatures are "classified by the prehistoric era they existed in, but this currently has no effect on how or where they appear" (https://dwarffortresswiki.org/index.php/Extinction).
