# Creature token

The `[OBJECT:CREATURE]` token begins the definition of a *Dwarf Fortress* creature raw file. Each creature definition that follows begins with the  token, and the creature's exact properties and behavior are then specified by the use of further creature tokens.  All known creature tokens are listed below. 

Vanilla creature definitions can be found in `<Dwarf Fortress>\data\vanilla\vanilla_creatures\`. 
Creature ID is also used with graphics tokens to make customizable graphics sets.

The caste tokens allow defining sub-species within the broader creature definition, including true biological castes and lesser variations, such as sexes. Creature tokens can either be 'Creature' or 'CASTE-only' type which can only be applied to creature or caste respectively, or 'CASTE' which can be applied to both. In the table bellow, creature type distinguishes tokens that can be applied to creature only, caste only, and both ('creature', 'CASTE-only', and 'CASTE' respectively)

__NOTOC__ 

1. A

**width="20%" | Token
**width="10%" | Type
**width="20%" | Arguments
**width="50%" | Description

| | Caste
| | Prevents the tamed creature from being made available for adoption, instead allowing it to automatically adopt whoever it wants. The basic requirements for adoption are intact, and the creature will only adopt individuals who have a preference for their species. Used by cats in the vanilla game. When iewing a tame creature with this token, the message "This animal isn't interested in your wishes" will appear instead of "This [adorable] animal can't work" or "This animal is waiting to be trained".

| | Caste
| | Makes the creature need alcohol to get through the working day; it will choose to drink booze instead of water if possible. Going sober for too long reduces speed.

| | Caste
| | When set, the creature will appear at any time of day. Overrides , , , , and .

| | Creature
| - 'character' or tile number
| If set, the creature will blink between its  and its ALTTILE. 

| | Caste
| | Makes the creature start out hidden and remain near its original location until its prey draws near. When combined with , causes them to lay gigantic webs near their spawn location, though only for creatures present during embark.

| | Caste
| | Allows a creature to breathe both in and out of water (unlike ) - does not prevent drowning in magma.

| | Appearance Modifier
| - Range (6 values, low to high)
| Based on info from Wannabehero on the forums: When used with an appearance modifier token (BP_APPEARANCE_MODIFIER or BODY_APPEARANCE_MODIFIER), tells the game what numeric ranges to map to which descriptors.

The game uses 7 descriptor levels for each modifier, with the center one generally being to omit the thing from the creature description entirely. The six values in APP_MOD_DESC_RANGE define the boundaries between each described range. If this is not specified it uses the numbers 10:50:95:105:150:190.

| | Appearance Modifier
| - Model (Accepts DOMINANT_MORE, DOMINANT_LESS, and MIX)
| Defines a genetic model for the relevant appearance modifier(s). May or may not do anything significant at present.

| | Appearance Modifier
| - number
| Determines how important the appearance modifier is, for determining whether it shows up in the creature description.

| | Appearance Modifier
| - noun
- SINGULAR or PLURAL 
| Creates a noun for the appearance, and whether it is singular or plural.

| | Appearance Modifier
| - Rate (integer)
- Scale (DAILY, YEARLY)
- min (growth)
- max (growth)
- start year
- start day
- end year
- end day 
| Setting the growth rate of the modifier. The last two tokens can be replaced by NO_END to have growth continue indefinitely.

| | Caste
| - creature variation ID
- (optional) any amount of arbitrary arguments
| Applies the specified creature variation. See Creature_variation_token#Arguments_and_conditional_tokens for how the subsequent arguments may be used.

| | Special
| | Applies the effects of all pending  and  tokens that have been defined in the current creature.

| | Caste
| | Enables the creature to breathe in water, but causes it to air-drown on dry land. 

| | Caste
| | Causes the creature to be excluded from the object testing arena's creature spawning list.  Typically applied to spoileriffic creatures.

| | Creature
| | Enables the creature to be kept in artificial hives by beekeepers.

| | Caste
| | Prevents the creature from attacking or frightening creatures with the  tag.

| | Caste
| - token
- selection criteria (it's complicated)
| Defines the attack name, and the body part used. See below for valid subtokens
    - Example:**
`[ATTACK:GORE:BODYPART:BY_CATEGORY:HORN]`
- GORE* = name of the attack
- BODYPART:BY_CATEGORY:HORN* = the horn is used to attack (presuming the creature has one)

| | Caste
| - population
- exported wealth
- created wealth
| Specifies when a megabeast or semi-megabeast will attack the fortress. The attacks will start occurring when all of the requirements are met. Setting a value to 0 disables the trigger.

1. B

**width="20%" | Token
**width="10%" | Type
**width="20%" | Arguments
**width="50%" | Description

| | Caste
| - integer 
| Age at which creature is considered a child, the default is zero. One can think of this as the duration of the baby stage.

| | Caste
| - singular
- plural 
| Defines a new name for a creature in baby state at the caste level. For non-caste-specific baby names, see .

| | Caste
| - integer
| Creature may be subject to beaching, becoming stranded on shores, where they will eventually air-drown. The number indicates the frequency of the occurrence. Presumably requires the creature to be . Used by orcas, sperm whales and sea nettle jellyfish in the vanilla game.

| | Caste
| | The creature is non-aggressive by default, and will never automatically be engaged by companions or soldiers, running away from any creatures that are not friendly to it, and will only defend itself if it becomes enraged. Can be thought of as the counterpoint of the  tag. When tamed, animals with this tag will be useless for fortress defense.

This and  are required for  to function properly, if an animal contains the aforementioned requirements without this tag: items loaded by the merchants will be dropped upon departure.

| | Creature
| - biome token
| Select a biome the creature may appear in.

| | Caste
| - <material token>
- <material state>
| Specifies what the creature's blood is made of.

| | Caste
| | Causes vampire-like behaviour; the creature will suck the blood of unconscious victims when its thirst for blood grows sufficiently large. When controlling the creature in adventure mode, this can be done at will. Seems to be required to make the creature denouncable (in-world) as a creature of the night.

| | Caste
| - body parts 
| Draws body parts from OBJECT:BODY files (such as body_default.txt)
    - Example:**
[BODY:BODY_WITH_HEAD_FLAG:HEART:GUTS:BRAIN:MOUTH] 
This is the body from a purring maggot. It creates a body with head, a heart, some guts, a brain, and a mouth. That's all a maggot needs.

The body parts need to be listed in an order such that any parent part appears before its connected children. For example [BODY:HEART:BODY_WITH_HEAD_FLAG] produces a "Body Token Recognized But Could Not Connect: HEART" error because HEART can't find any UPPERBODY(s) to connect to. Switching the order to [BODY:BODY_WITH_HEAD_FLAG:HEART] fixes the problem because now the UPPERBODY is created before the HEART tries to connect to it.

    - If the body is left undefined, the creature (or caste) will be tagged as [DOES_NOT_EXIST].** 

| | Caste
| - ATTRIBUTE
- lowest
- lower
- low
- median
- high
- higher
- highest 
| These body modifiers give individual creatures different characteristics. In the case of HEIGHT, BROADNESS and LENGTH, the modifier is also a percentage change to the BODY_SIZE of the individual creature. The seven numbers afterward give a distribution of ranges. Each interval has an equal chance of occurring.
    - Example:**
[BODY_APPEARANCE_MODIFIER:HEIGHT:90:95:98:100:102:105:110] 
- HEIGHT* : marks the height to be changed 
- 90:95:98:100:102:105:110* : sets the range from the shortest (90% of the average height) to the tallest (110% of the average height) creature variation.

| | Caste
| - PlanName
- Arguments 
| Loads a plan from listed OBJECT:BODY_DETAIL_PLAN files, such as b_detail_plan_default.txt. Mass applies USE_MATERIAL_TEMPLATE, mass alters RELSIZE, alters body part positions, and will allow tissue layers to be defined. Tissue layers are defined in order of skin to bone here.
    - Example:**
[BODY_DETAIL_PLAN:VERTEBRATE_TISSUE_LAYERS:SKIN:FAT:MUSCLE:BONE:CARTILAGE] 
This creates the detailed body of a fox, the skin, fat, muscle, bones and cartilage out of the vertebrate tissues.
A maggot would only need:
- [BODY_DETAIL_PLAN:EXOSKELETON_TISSUE_LAYERS:SKIN:FAT:MUSCLE]* 

| | Caste
| - years
- days
- size 
| Sets size at a given age. Size is in cubic centimeters, and for normal body materials, is roughly equal to the creature's average weight in grams.
    - Example:**
[BODY_SIZE:0:0:10000]
[BODY_SIZE:1:168:50000]
[BODY_SIZE:12:0:220000]
This describes the size of a minotaur. Its birth size would be 10,000 cm3 (~10 kg). At 1 year and 168 days old it would be 50,000 cm3 (~50 kg). And as an adult (at 12 years old) it would be 220,000 cm3 and weigh roughly 220 kg.

| | Caste
| - gloss 
| Substitutes body part text with replacement text. Draws gloss information from OBJECT:BODY files (such as body_default.txt)

| | Caste
| | Creature eats bones. Implies .  Currently does not work due to a bug ().

| | Caste
| | Adds a type to a body part - used with . In vanilla DF, this is used for adding the type 'GELDABLE' to the lower body of certain creatures. 

| | Caste
| - QUALITY
- lowest
- lower
- low
- median
- high
- higher
- highest 
| Sets up the breadth of possibilities for appearance qualities for a selected BP group. EG. Eyes (CLOSE_SET, DEEP_SET, ROUND_VS_NARROW, LARGE_IRIS),Lips (THICKNESS), Nose (BROADNESS, LENGTH, UPTURNED, CONVEX), Ear (SPLAYED_OUT, HANGING_LOBES, BROADNESS, HEIGHT), Tooth (GAPS), Skull (HIGH_CHEEKBONES, BROAD_CHIN, JUTTING CHIN, SQUARE_CHIN), Neck (DEEP_VOICE, RASPY_VOICE), Head (BROADNESS, HEIGHT)

| | Caste
| | Removes a type from a body part. Used with . 
 

| | Caste
| - 1 or 2 
| Allows a creature to destroy furniture and buildings. Value [1] targets mostly doors, hatches, furniture and the like. Value [2] targets anything not made with the  +  commands. 

1. C

**width="20%" | Token
**width="10%" | Type
**width="20%" | Arguments
**width="50%" | Description

| | Caste
| - interaction token
| The creature can perform an interaction. See interaction token.

| | Caste
| | The creature gains skills and can have professions. If a member of a civilization (even a pet) has this token, it'll need to eat, drink and sleep. Note that this token makes the creature unable to be eaten by an adventurer, so it is not recommended for uncivilized monsters. Adventurers lacking this token can allocate but not increase attributes and skills. Skills allocated will disappear on start. A creature with at least this token or the  token will be able to have values and goals.

| | Caste
| | Can talk. Note that this is not necessary for a creature to gain social skills but to make friends in fortress mode. A creature with at least this token or the  token will be able to have values and goals.

| | Caste
| | Creature cannot climb, even if it has free grasp parts.

| | Caste
| | Creature cannot jump.

| | Caste
| | Acts like , except that  creatures will attack them.

| | Caste
| | Defunct, as doors cannot be set as tightly closed anymore.

| | Caste
| | Creature *only* eats meat. If the creature goes on rampages in worldgen, it will often devour the people/animals it kills.

| | Creature
| - name 
| Defines a caste.

| | Caste
| - tile number or "letter"
| Caste-specific . Requires .

| | Caste
| - fg
- bg
- brightness
| Caste-specific .

| | Caste
| - fg
- bg
- brightness
| Caste-specific .

| | Caste
| - tile value or "letter"
| Caste-specific .

| | Caste
| - singular
- plural
- adjective 
| While  describes the name of the species,  names individuals of the species. Unlike other caste-specific descriptions, this token is required, even for creatures without separate castes. If left undefined, the creature will not show up in the arena and members of the species will be labeled as "nothing".

| | Caste
| - Unit type token (Profession)
- singular
- plural 
| Caste-specific .

| | Caste
| - 'character' or tile number
| Caste-specific . Requires .

| | Caste
| - 'character' or tile number
| Caste-specific .

| | Caste
| - tile number or "letter"
| Caste-specific .

| | Caste
| | Causes the creature to develop cave adaptation.

Allows for creature's race to be involved in jokes that end in "And the [race] saw the sun and vomited on the spot!" 

| | Caste
| - Varies
| Specifies interaction details following a  token. See interaction token.

| | Caste
| - integer
| Multiplies body size by a factor of (integer)%. 50 halves size, 200 doubles.

| | Creature
| - integer
| Multiplies frequency by a factor of (integer)%.

| | Caste
| - integer 
| Age at which creature is considered an adult - one can think of this as the duration of the child stage. Allows the creature's offspring to be rendered fully tame if trained during their childhood. 

| | Caste
| - singular
- plural 
| Defines a new name for a creature in the child state at the caste level. For non-caste-specific child names, see .

| | Creature
| - min
- max
| The minimum/maximum numbers of how many creatures per spawned cluster. Vermin fish with this token in combination with temperate ocean and river biome tokens will perform seasonal migrations. Defaults to 1:1 if not specified.

| | Caste
| - min
- max
| Number of eggs laid in one sitting.

| | Caste
| | Caste hovers around colony.

| | Creature
| - foreground
- background
- brightness 
| Color of the creature's tile. (See Color for usage.)

| | Caste
| | When combined with any of , ,  and/or , the creature is guaranteed to be domesticated by any civilization with , ,   and/or  respectively. Such civilizations will always have access to the creature, even in the absence of wild populations. This token is invalid on  creatures.

| | Caste
| | Creatures of this caste's species with the  and  tokens will kidnap s of an appropriate sex and convert them into castes with CONVERTED_SPOUSE.

| | Caste
| | Set this to allow the creature to be cooked in meals while it is still alive, as well as when it's dead but not yet cleaned. Used by some water-dwelling vermin such as mussels, nautiluses and oysters. Currently does not work correctly when applied to non- vermin.

| | Caste
| | Creature is 'berserk' and will attack all other creatures, except members of its own species that **also** have the CRAZED tag. It will show  in the unit list. Berserk creatures go on rampages during worldgen much more frequently than non-berserk ones.

| | Special
| - creature ID
| Copies another specified creature. This will override any definitions made before it; essentially, it makes this creature identical to the other one, which can then be modified. Often used in combination with  to import standard variations from a file. The vanilla giant animals and animal peoples are examples of this token combination.

| | Creature
| - creature ID
| A unique, arbitrary identifier that begins the definition of each new creature, and is used to reference the creature in other tokens and raws.

| | Caste
| - classname
| An arbitrary creature classification. Can be set to anything, but the only vanilla uses are GENERAL_POISON (used in syndromes), EDIBLE_GROUND_BUG (used as targets for ), MAMMAL, and POISONOUS (both used for kobold pet eligibility). A single creature can have multiple classes.

The full list of tokens that use creature classes is: 

- Creature tokens: , 
- Interaction tokens: , 
- Animal definition (Entity) tokens: , 
- Position (Entity) token: 
- Syndrome tokens: , , 

| | Creature
| - 'character' or tile number
| Creatures active in their civilization's military will use this tile instead.

| | Creature
| - 'character' or tile number 
| The symbol of the creature in ASCII mode.

| | Caste
| | When set, the creature will appear at dawn (between 4:30 AM and 6:00 AM) and in the evening (between 8:00 PM and 10:05 PM) in Adventurer mode.

| | Caste
| | Allows a creature to steal and eat edible items from a site. It will attempt to grab a food item and immediately make its way to the map's edge, where it will disappear with it. If the creature goes on rampages during worldgen, it will often steal food instead of attacking. Trained and tame instances of the creature will no longer display this behavior.

| | Caste
| | Allows a creature to (very quickly) drink your alcohol. Or spill the barrel to the ground. Also affects undead versions of the creature. Unlike food or item thieves, drink thieves will consume your alcohol on the spot rather than run away with one piece of it. Trained and tame instances of the creature will no longer display this behavior.

| | Caste
| | Allows a creature to steal things (apparently, of the highest value it can find). It will attempt to grab an item of value and immediately make its way to the map's edge, where it will disappear with it. If a creature with any of the CURIOUSBEAST tokens carries anything off the map, even if it is a caravan's pack animal, it will be reported as stealing everything it carries. If the creature goes on rampages in worldgen, it will often steal items instead of attacking - kea birds are infamous for this. Trained and tame instances of the creature will no longer display this behavior. Also, makes the creature unable to drop hauled items until it enters combat.

| | Special
| - TAG NAME 
| Adds a tag. Used in conjunction with creature variation templates.

| | Special
| - TAG NAME 
| Removes a tag. Used in conjunction with creature variation templates. 

1. D

**width="20%" | Token
**width="10%" | Type
**width="20%" | Arguments
**width="50%" | Description

| | Caste
| | Found on generated demons.

At least 1 demon generated, or custom must have the  token in order for the horrifying screams event to trigger.

| | Caste
| - text 
| A brief description of the creature type, as displayed when viewing the creature's description/thoughts & preferences screen.

| | Caste
| | Causes the creature to die upon attacking. Used by honey bees to simulate them dying after using their stingers.

| | Caste
| - integer 
| Increases experience gain during adventure mode. Creatures with a difficulty of 11 or higher are not assigned for quests in adventure mode.

| | Caste
| | When set, the creature will only appear during the day (between 6:00 AM and 8:00 PM) in Adventurer mode.

| | Caste
| | The creature hunts vermin by diving from the air. On tame creatures, it has the same effect as . Found on peregrine falcons.

| | Creature
| | Adding this token to a creature prevents it from appearing in generated worlds (unless it's marked as always present for a particular civilisation). For example, adding it to dogs will lead to worlds being generated without dogs in them. Also removes the creature from the object testing arena's spawn list. If combined with , artistic depictions of the creature will occur regardless. Used by centaurs, chimeras and griffons in the vanilla game. 

Note: a creature tagged as DOES_NOT_EXIST can still be summoned successfully, as long as it has a body defined in its raws or, another creature can transform into it.

1. E

**width="20%" | Token
**width="10%" | Type
**width="20%" | Arguments
**width="50%" | Description

| | Caste
| - item token
- material token (ANY_HARD_STONE can be used for the material)
| Defines the item that the creature drops upon being butchered. Used with .

| | Caste
| - gem shape
| The shape of the creature's extra butchering drop. Used with .

| | Caste
| - <material token>
- <material state>
| Defines the material composition of eggs laid by the creature. Egg-laying creatures in the default game define this 3 times, using LOCAL_CREATURE_MAT:EGGSHELL, LOCAL_CREATURE_MAT:EGG_WHITE, and then LOCAL_CREATURE_MAT:EGG_YOLK. Eggs will be made out of eggshell. Edibility is determined by tags on whites or yolk, but they otherwise do not exist.

| | Caste
| - size
| Determines the size of laid eggs. Doesn't affect hatching or cooking, but bigger eggs will be heavier, and may take longer to be hauled depending on the hauler's strength.

| | Creature
| | Makes the creature appear as a large 3×3 wagon responsible for carrying trade goods, pulled by two  creatures and driven by a merchant.

| | Caste
| | Allows the creature to wear or wield items.

| | Creature
| | The creature is considered evil and will only show up in evil biomes. Civilizations with  can domesticate them regardless of exotic status. Has no effect on cavern creatures except to restrict taming. A civilization with evil creatures can colonize evil areas. 

Civilizations which list evil creatures as one of their main population options will potentially emerge following an underworld mining disaster, with the added caveat that a demon will be in charge of the civ. The rules which govern which noble position the demon in charge adopts however, are unclear. It either picks one of the predefined positions, or simply makes its own. 

| | Caste
| - BY_CATEGORY or BY_TYPE or BY_TOKEN
- TYPE, CATEGORY, or TOKEN
| The creature drops an additional object when butchered, as defined by  and . Used for gizzard stones in default creatures. For some materials, needs to be defined after caste definitions with SELECT_CASTE:ALL

| | Caste
| - material token
| Defines a creature extract which can be obtained via small animal dissection.

| | Caste
| | The creature can see regardless of whether it has working eyes and has full 360 degree vision, making it impossible to strike the creature from a blind spot in combat. Invisible creatures will also be seen, namely intelligent undead using a "vanish" power.

1. F

**width="20%" | Token
**width="10%" | Type
**width="20%" | Arguments
**width="50%" | Description

| | Creature
| | The creature is a thing of legend and known to all civilizations. Its materials cannot be requested or preferred. The tag also adds some art value modifiers. Used by a number of creatures. Conflicts with .

| | Caste
| | Found on subterranean animal-man tribals. Currently defunct. In previous versions, it caused these creatures to crawl out of chasms and underground rivers.

| | Caste
| | Found on forgotten beasts. Presumably makes it act as such, initiating underground attacks on fortresses, or leads to the pop-up message upon encountering one. Displays the creature's  in its legends mode entry and hides the creature from displaying in a world_sites_and_pops file. Does not create historical figures like generated forgotten beasts do.

Requires specifying a  in which the creature will live, and both surface and subterranean biomes are allowed. Does not stack with  and if both are used the creature will not spawn. Appears to be incompatible with  even if used in separate castes.

| | Caste
| | Makes the creature biologically female, enabling her to bear young. Usually specified inside a caste.

| | Caste
| | Makes the creature immune to FIREBALL and FIREJET attacks, and allows it to path through high temperature zones, like lava or fires. Does not, by itself, make the creature immune to the damaging effects of burning in fire, and does not prevent general heat damage or melting on its own (this would require adjustments to be made to the creature's body materials - see the dragon raws for an example).

| | Caste
| | Like , but also renders the creature immune to DRAGONFIRE attacks. 

| | Caste
| | The creature's corpse is a single FISH_RAW food item that needs to be cleaned (into a FISH item) at a fishery to become edible. Before being cleaned the item is referred to as "raw". The food item is categorized under "fish" on the food and stocks screens, and when uncleaned it is sorted under "raw fish" in the stocks (but does not show up on the food screen). 
Without this or , fished vermin will turn into food the same way as non-vermin creatures, resulting in multiple units of food (meat, brain, lungs, eyes, spleen etc.) from a single fished vermin. These units of food are categorized as meat by the game.

| | Caste
| - temperature 
| The creature's body is constantly at this temperature, heating up or cooling the surrounding area. Alters the temperature of the creature's inventory and all adjacent tiles, with all the effects that this implies - may trigger wildfires at high enough values. Also makes the creature immune to extreme heat or cold, as long as the temperature set is not harmful to the materials that the creature is made from. Corpses and body parts of creatures with a fixed temperature maintain their temperature even after death.

Note that temperatures of 12000 and higher may cause pathfinding issues in fortress mode.

| | Caste
| | If engaged in combat, the creature will flee at the first sign of resistance. Used by kobolds in the vanilla game.

| | Caste
| | Allows a creature to fly, independent of it having wings or not. Fortress Mode pathfinding only partially incorporates flying - flying creatures need a land path to exist between them and an area in order to access it, but as long as one such path exists, they do not need to use it, instead being able to fly over intervening obstacles. Winged creatures with this token can lose their ability to fly if their wings are crippled or severed. Winged creatures without this token will be unable to fly. (A 'wing' in this context refers to any body part with its own FLIER token).

At least 1 Demon must have the flier token in order for the horrifying screams event to trigger.

| | Creature
| - number, max 100
| The  value plays two separate roles. The first is in determining the initial distribution of creatures across the world map. Each creature is randomly assigned a single x, y co-ordinate on the world map, which act as the epicenter for that creature's distribution. A square is drawn around that x, y co-ordinate with a Manhattan radius equal to the  value divided by 100 times the world map size. For example, in a 256 by 256 size world map, the lion might be assigned 14, 112. The lion has , and so a square is drawn by moving 13 tiles in each direction from the lion's x, y co-ordinate. This is the lion's "territory".

Each sub-region in the world will attempt to fill lists of wildlife. There are five lists - , , , , and , corresponding with the relevant tokens. The game will attempt to place seven creatures in each list for each sub-region. The game will select the seven nearest valid creatures. Creatures are valid for sub-region's list if they have the requisite token for that list, if they have the valid token for that sub-region's biome (for example, the [lion can only be selected for , , and , and if their "territory" as defined by their random epicenter and  radius overlaps with that sub-region. These lists then determine the creatures that can actually appear within that sub-region during gameplay.

There are some exceptions to the above. If the game was not capable of filling all seven entries in a list, it will drop the overlapping territory requirement, and simply pull the nearest creature which has the correct token and biome availability. Conversely, if a creature has an epicenter but has not appeared on any of the list for any of the world map's sub-regions, the creature will be assigned to the relevant list for the nearest appropriate sub-region - meaning it is occasionally possible to have lists of eight creatures or more. This is more common in smaller worlds where there are less possible sub-regions to be assigned towards. Creatures with the  and  tokens ignore the epicenter distribution system altogether. They are always capable of appearing in appropriate biomes which are  or  respectively. This is not true for , which acts more like the biome tokens. Creatures with  have a "territory" which covers the entire map, regardless of their epicenter (although they can still fail to be chosen if there are 7 creatures which are eligible and have nearer epicenters to the sub-region in question).

The second use for  is to determine how often a creature actually appears on map. In Fortress Mode, the game will try and spawn large wildlife (creatures with  or  in fairly regular waves. These waves include ,  combined with , , and  - so a lion does not compete for selection with a gazelle. When the game decides it needs to spawn in a fresh wave of e.g.  creatures, it will select one of the creatures available to it from the lists for that sub-region at random, with all creatures weighted equally. Once it has selected a creature, it then effectively rolls a d100 against the relevant creature's . If the d100 is equal to the creature's  or less, that creature is then spawned in. If the d100 is above the creature's , the game returns to the relevant list and selects again.  acts as  for these purposes - in other words, the creature cannot fail the d100 check and will always be spawned in if it is selected from the list.

1. G

**width="20%" | Token
**width="10%" | Type
**width="20%" | Arguments
**width="50%" | Description

| | Caste
| - <gait type>
- <gait name>
- <max speed>
- <build up time>
- <max turning speed>
- <start speed>
- <energy expenditure>
- <gait flag(s)>
| Defines a gait by which the creature can move. See Gait for more information. Specifically, you likely want to use one of the existing STANDARD_X_GAITS creature variations, as described in this subsection.

- <max speed> indicates the maximum speed achievable by a creature using this gait
- <start speed> indicates the creature's speed when it starts moving using this gait
- <build up time> indicates how long it will take for a creature using this gait to go from <start speed> to <max speed>. For example, a value of 10 means that it should be able to reach the maximum speed by moving 10 tiles in a straight line over even terrain.
- <max turning speed> indicates the maximum speed permissible when the creature suddenly changes its direction of motion. The creature's speed will be reduced to <max turning speed> if travelling at a higher speed than this before turning.
- <energy expenditure> indicates how energy-consuming the gait is. Higher values cause the creature to tire out faster. Persistent usage of a high-intensity gait will eventually lead to exhaustion and collapse.

    - NO_BUILD_UP** can be specified instead of a <start speed> value to make the <max speed> instantly achievable upon initiating movement (this is equivalent to a <build up time> of 0). Note that <build up time> and <max turning speed> are both ignored if specified alongside this (as NO_BUILD_UP trumps <build up time> and preserves <max speed> whilst turning, and <max turning speed> cannot exceed <max speed>) so it is permissible to omit them so long as they are **both** omitted together.

It's possible to specify a <start speed> greater than the <max speed>; the moving creature will decelerate towards its <max speed> in this case.

    - valid gait types:**
      - WALK**
Used for moving normally over ground tiles.

      - CRAWL**
Used for moving over ground tiles whilst prone.

      - SWIM**
Used for moving through tiles containing water or magma at a depth of at least 4/7. 

      - FLY**
Used for moving through open space.

      - CLIMB**
Used for moving whilst climbing.

    - valid gait flags:**
- **AGILITY**
Speeds/slows movement depending on the creature's Agility stat.

- **STRENGTH**
Speeds/slows movement depending on the creature's Strength stat.

- **LAYERS_SLOW**
Makes THICKENS_ON_ENERGY_STORAGE and THICKENS_ON_STRENGTH tissue layers slow movement depending on how thick they are. Adding the STRENGTH gait flag counteracts the impact of the latter layer.

- **STEALTH_SLOWS:**<percentage>
Slows movement by the specified percentage when the creature is sneaking.

| | Creature
| - singular
- plural 
| Like , but applied regardless of caste.

| | Creature
| - singular
- plural 
| Like , but applied regardless of caste.

| | Caste
| - value A
- value B
| Has the same function as , but applies to all attacks instead of just those involving a specific material. Appears to be overridden by MATERIAL_FORCE_MULTIPLIER (werebeasts, for example, use both tokens to provide resistance to all materials, with one exception to which they are especially vulnerable).

| | Creature
| | Found on procedurally generated creatures like forgotten beasts, titans, demons, angels, and night creatures. Cannot be specified in user-defined raws.

| | Caste
| | Makes the creature get infections from necrotic tissue.

| | Caste
| | Makes the creature's wounds become infected if left untreated for too long.

| | Creature
| - foreground
- background
- brightness 
| The colour of the creature's .

| | Creature
| - ascii character 
| If present, the being glows in the dark (generally used for Adventurer Mode). The tile is what replaces the being's current tile when it is obscured from your sight by darkness. The default setting for kobolds (a yellow quotation mark) provides a nice "glowing eyes" effect. The game is also hardcoded to automatically convert quotation mark GLOWTILES into apostrophes if the creature has lost one eye. This works at the generic creature level - for caste-specific glow tiles, use  instead.

| | Caste
| - verb
| The creature can and will gnaw its way out of animal traps and cages using the specified verb, depending on the material from which it is made (normally wood).

| | Caste
| - class
| The creature eats vermin of the specified class.

| | Caste
| - creature
- caste
| The creature eats a specified vermin.

| | Special
| | When using tags from an existing creature, inserts new tags at the end of the creature.

| | Special
| | When using tags from an existing creature, inserts new tags at the beginning of the creature.

| | Special
| | When using tags from an existing creature, inserts new tags *before* the specified tag.

| | Creature
| | Creature is considered good and will only show up in good biomes - unicorns, for example. Civilizations with  can domesticate them regardless of exotic status. Has no effect on cavern creatures except to restrict taming. A civilization that has good creatures can colonise good areas in world-gen.

| | Caste
| - value 
| The value determines how rapidly grass is trampled when a creature steps on it - a value of 0 causes the creature to never damage grass, while a value of 100 causes grass to be trampled as rapidly as possible. Defaults to 5.

| | Caste
| - target value
| Used in Creature Variants. This token changes the adult body size to the average of the old adult body size and the target value and scales all intermediate growth stages by the same factor.

| | Caste
| - number
| The creature is a grazer - if tamed in fortress mode, it needs a pasture to survive. The higher the number, the less frequently it needs to eat in order to live. Not used since 0.40.12, replaced by  to fix .

1. H

**width="20%" | Token
**width="10%" | Type
**width="20%" | Arguments
**width="50%" | Description

| | Caste
| - type
- probability
| Defines certain behaviors for the creature. The habit types are:
- COLLECT_TROPHIES
- COOK_PEOPLE
- COOK_VERMIN
- GRIND_VERMIN
- COOK_BLOOD
- GRIND_BONE_MEAL
- EAT_BONE_PORRIDGE
- USE_ANY_MELEE_WEAPON
- GIANT_NEST
- COLLECT_WEALTH.
These require the creature to have a  to work properly, and also don't seem to work on creatures who are not a , , or.

| | Caste
| - number or TEST_ALL
| "If you set HABIT_NUM to a number, it should give you that exact number of habits according to the weights.". All lists of HABITs are preceded by [HABIT_NUM:TEST_ALL]

| | Caste
| | The creature has nerves in its muscles. Cutting the muscle tissue can sever motor and sensory nerves, disabling the limb.

| | Caste
| | The creature has a shell. Seemingly no longer used - holdover from previous versions.

| | Creature
| - number
- time
- item tokens
| What product is harvested from beekeeping.

| | Caste
| - number or NONE
| Default 'NONE'. The creature's normal body temperature. Creature ceases maintaining temperature on death unlike fixed material temperatures. Provides minor protection from environmental temperature to the creature.

| | Caste
| | Creature hunts and kills nearby vermin, randomly walking between places with food laying on the ground or in stockpiles, to check for possible [VERMIN_EATER] vermin, but they'll kill any other vermin too. Do not include this creature token on an intelligent entity that you intend to play as in fortress mode because it will prevent them from feeding themselves.

1. I

**width="20%" | Token
**width="10%" | Type
**width="20%" | Arguments
**width="50%" | Description

| | Caste
| | The creature cannot move. Found on sponges. Will also stop a creature from breeding in fortress mode (MALE and FEMALE are affected, if one is IMMOBILE; no breeding will happen).

| | Caste
| | The creature is immobile while on land. Only works on  creatures which can't breathe on land.

| | Caste
| | The creature radiates fire. It will ignite, and potentially completely destroy, items the creature is standing on. Also gives the vermin a high chance of escaping from animal traps and cages made of any flammable materials (specifically ones that could be ignited by magma).

| | Caste
| | Alias for  + .

| | Caste
| - item token
- material token
| Determines if the creature leaves behind a non-standard corpse (i.e. wood, statue, bars, stone, pool of liquid, etc.). Ethics may prevent actually using the item in jobs or reactions.

| | Caste
| - number
| The quality of an item-type corpse left behind. Valid values are: 0 for ordinary, 1 for well-crafted, 2 for finely-crafted, 3 for superior, 4 for exceptional, 5 for masterpiece.

1. L

**width="20%" | Token
**width="10%" | Type
**width="20%" | Arguments
**width="50%" | Description

| | Caste
| - type
- probability
| Found on megabeasts, semimegabeasts, and night creatures. The creature will seek out sites of this type and take them as lairs. The lair types are:
- SIMPLE_BURROW
- SIMPLE_MOUND
- WILDERNESS_LOCATION
- SHRINE
- LABYRINTH

| | Caste
| - characteristic
- probability
| Defines certain features of the creature's lair. The only valid characteristic is HAS_DOORS.

| | Caste
| | This creature will actively hunt adventurers in its lair.

| | Caste
| - speech file
| What this creature says while hunting adventurers in its lair.

| | Caste
| | Will attack other creatures that are smaller than it. Tamed large predators will still attack wildlife. In fortress mode, only one group of "large predators" (possibly two groups on "savage" maps) will appear on any given map. In adventurer mode, large predators will try to ambush and attack you (and your party will attack them back). When tamed, large predators tend to be much more aggressive to enemies than non-large predators, making them a good choice for an animal army. They may go on rampages in worldgen, and adventurers may receive quests to kill them. Also, they can be mentioned in the intro paragraph when starting a fortress e.g. "ere the wolves get hungry."
A single biome supports 7 large predator species, picking randomly and rolling a d100 under its  to add it until all 7 slots are filled.

Incompatible with  on a technicality, if included: hauled items are likely to be dropped upon entering the map (even if  is present) in contrast to when the merchants depart.

| | Creature
| | This is the core requisite tag allowing the creature to spawn as a wild animal in the appropriate biomes. Requires specifying a  in which the creature will spawn. Does not require specifying a frequency, population number, or cluster number.

This tag stacks with , , or ; if used with one of these tags, the creature will spawn as both a boss and as a wild animal. This tag does not stack with  and if both are used the creature will not spawn. This tag is unaffected by .
Large roamers are not able to spawn in Pool biomes as they do not connect to the edge of the map and are too small, Lake biomes are a suitable alternative.

| | Caste
| | Creature lays eggs instead of giving birth to live young.

| | Caste
| - item token
- material token
| Creature lays the specified item instead of regular eggs.

| | Caste
| - material token
- healing rate 
| The creature has ligaments in its  tissues (bone or chitin by default). Cutting the bone/chitin tissue severs the ligaments, disabling motor function if the target is a limb.

| | Caste
| | A vermin featuring this tag will remain visible to an adventurer even at night. 

Subterranean vermin which feature this token will flicker in unexposed and unrevealed cavern layers while playing in Fortress Mode.

| | Caste
| | The creature will attack enemies rather than flee from them. This tag has the same effect on player-controlled creatures - including modded dwarves. Retired as of v0.40.14 in favor of .

| | Caste
| | Creature uses "sssssnake talk" (multiplies 'S' when talking - "My name isss Recisssiz."). Used by serpent men and reptile men in the vanilla game. C's with the same pronunciation (depending on the word) are not affected by this token.

| | Caste
| - minimum
- maximum
| Determines the number of offspring per one birth; default 1-3, not used in vanilla raws. See also .

| | Creature
| | Allows you to play as a wild animal of this species in adventurer mode. Prevents trading of (tame) instances of this creature in caravans.

| | Creature
| | Wild animals of this species may occasionally join a civilization. Prevents trading of (tame) instances of this creature in caravans.

| | Caste
| | Lets a creature open doors that are set to forbidden in fortress mode.

| | Creature
| | The creatures will scatter if they have this tag, or form tight packs if they don't. 

| | Caste
| - number
| Determines how well a creature can see in the dark - higher is better. Dwarves have 10000, which amounts to perfect nightvision.

1. M

**width="20%" | Token
**width="10%" | Type
**width="20%" | Arguments
**width="50%" | Description

| | Caste
| | According to Toady One, this is completely interchangeable with  and might have been used in very early versions of the game by wandering wizards or the ent-type tree creatures that used to be animated by elves. |-
| | Caste
| | The creature is able to see while submerged in magma. 

| | Caste
| | Makes the creature biologically male; usually declared inside a caste.

| | Caste
| - occasionally body part 
| Adds a possible mannerism to the creature's profile.  See creature mannerism token for further info.

| | Creature
| - material id
| Begins defining a new local material. Follow this with standard material definition tokens to define the material.

| | Caste
| - Material token
- value A
- value B
| When struck with a weapon made of the specified material, the force exerted will be multiplied by A/B, thus making the creature more or less susceptible to this material. For example, if A is 2 and B is 1, the force exerted by the defined material will be doubled. If A is 1 and B is 2, it will be halved instead. See also  , which can be used to make this sort of effect applicable to all materials.

| | Caste
| | When set, the creature will only appear at dawn (between 4:30 AM and 6:00 AM) in Adventurer mode.

| | Caste
| - min
- max 
| Determines the creature's natural lifespan, using the specified minimum and maximum age values (in years). Each individual creature with this token is generated with a predetermined date (calculated down to the exact tick!) between these values, at which it is destined to die of old age, should it live long enough. Note that the probability of death at any given age does not increase as the creature gets older [http://i.imgur.com/A1A4aA9.png. 
Creatures which lack this token are naturally immortal. The NO_AGING syndrome tag will prevent death by old age from occurring. Also note that, among civilized creatures, castes which lack this token will refuse to marry others with it, and vice versa.

| | Caste
| | Makes the creature slowly stroll around, unless it's in combat or performing a job. If combined with , will severely impact their pathfinding and lead the creature to move extremely slowly when not performing any task. Problematically applies to animal people based on the animal, and war trained animals.

| | Caste
| | A 'boss' creature; a small number of those are created during worldgen, their histories and descendants (if any) will be tracked in worldgen (as opposed to simply 'spawning'), and they will occasionally go on rampages, potentially leading to worship if they attack the same place multiple times. Their presence and number will also influence age names. When appearing in fortress mode, they will have a pop-up message announcing their arrival. They will remain hostile to the fortress military even after being tamed. See megabeast page for more details. 

Requires specifying a  in which the creature will live. Subterranean biomes appear to not be allowed. Does stack with  and if both are used the creature will spawn as both historical bosses and as wild animals.

| | Caste
| - ATTRIBUTE Token
- Cap %
| Default is 200.  This means you can increase your attribute to 200% of its starting value (or the average value + your starting value if that is higher).

| | Caste
| - ATTRIBUTE
- lowest
- lower
- low
- median
- high
- higher
- highest 
| Sets up a mental attribute's range of values (0-5000). All mental attribute ranges default to 200:800:900:1000:1100:1300:2000.

| | Caste
| - ATTRIBUTE Token
- cost to improve
- unused counter rate
- rust counter rate
- demotion counter rate
| Mental attribute gain/decay rates. Lower numbers in the last three slots make decay occur faster. Defaults are 500:4:5:4.

| | Caste
| - material token
- frequency
| Allows the creature to be milked in the farmer's workshop. The frequency is the amount of ticks the creature needs to "recharge" (i.e. how much time needs to pass before it can be milked again). Does not work on sentient creatures, regardless of ethics.

| | Caste
| | Alias for .

| | Caste
| | The creature spawns stealthed and will attempt to path into the fortress, pulling any levers it comes across. It will be invisible on the map and unit list until spotted by a citizen, at which point the game will pause and recenter on the creature. Used by gremlins in the vanilla game. "They go on little missions to mess with various fortress buildings, not just levers." 

| | Caste
| | Seemingly no longer used.

| | Caste
| | Creature may be used as a mount. No use for the player in fortress mode, but enemy sieging forces may arrive with cavalry. Mounts are usable in adventure mode.

| | Caste
| | Creature may be used as a mount, but civilizations cannot domesticate it in worldgen without certain exceptions.

| | Caste
| | Allows the creature to have all-around vision, as long as it has multiple heads that can see.

| | Caste
| | Makes the species usually produce a single offspring per birth, with a 1/500 chance of using the  as usual.  Requires .

| | Creature
| | Marks if the creature is an actual real-life creature. Only used for age-names at present.

1. N

**width="20%" | Token
**width="10%" | Type
**width="20%" | Arguments
**width="50%" | Description

| | Creature
| - singular
- plural
- adjective 
| The generic name for any creature of this type - will be used for referring to the species in the abstract, such as the default material prefix. For labeling individual creatures,  is necessary. If left undefined, the creature will be labeled as "nothing" by the game.

Some examples of adjective use:
- "super*dwarven* strength"
- "the *dwarven* hillocks of X"
- Deity species as in "*feline* deity"
- Megabeast attacks in worldgen. One with multiple dragons being a "*draconic* rampage"

| | Caste
| | Animal is considered to be natural. NATURAL animals will not engage creatures tagged with  in combat unless they are members of a hostile entity and vice-versa.

| | Caste
| | Alias of .

| | Caste
| - Skill token
- value
| The creature possesses the specified skill at this level inherently - that is, it begins with the skill at this level, and the skill may never rust below that. A value of 15 is legendary.

| | Caste
| | Creatures with this token can appear as experiments. Causes the creature to count as . 

Killing a creature featuring this token provides one point of "hero" reputation. Adds the creature's description as part of the initial summary of their historical figure in legends mode. People will react to creatures with this token as a night creature (natch). In adventure mode, ambushes involving these units will say "Night creature!" instead of "Ambush!" 

Prevents creature behavior enabled by .

Removes the high nature value check imposed by .

Prevents the AI from using ANIMATE interactions, unless the newly-animatedundead will not attack them. The check for this is specifically whether the unit is: 
- a ghost
- an animated unit 
- a unit with the  token added via . (This allows for the default exclusion of elves and goblins, unless raised as intelligent undead.)

| | Caste
| | Creatures with this token can appear in bogeyman ambushes in adventure mode, where they adopt classical bogeyman traits such as stalking the adventurer and vaporising when dawn breaks. Such traits do not manifest if the creature is encountered outside of a bogeyman ambush (for instance, as a megabeast or a civilised being). In addition, their corpses and severed body parts turn into smoke after a short while. Note that setting the "Number of Bogeyman Types" in advanced world generation to 0 will only remove randomly-generated bogeymen.

| | Caste
| | Found on some necromancers. Creatures with this tag may periodically "perform horrible experiments" offscreen, during which they can use creature-targeting interactions with an `[I_SOURCE:EXPERIMENT]` tag on living creatures in their area. Worlds are generated with a list of procedurally-generated experiments, allowing necromancers to turn living people and animals into ghouls and other experimental creatures, and these will automatically be available to all experimenters; it does not appear possible to prevent this. You can mod in your own custom experiment interactions, but these are used very infrequently due to the large number of generated experiments.

| | Caste
| | Found on night trolls and werebeasts. Implies that the creature is a night creature, and shows its description in legends mode entry. The creature is always hostile and will start no quarter combat with any nearby creatures, except for members of its own race. Note that this tag does not override the creature's normal behavior in fortress mode except for the aforementioned aggression, and doesn't prevent the creature from fleeing the battles it started. It also removes the creature's materials from stockpile settings list, making them be stored there regardless of settings.

Does stack with  and if both are used the creature will spawn as both historical hunters and as wild animals; this requires specifying a  in which the creature will live, and subterranean biomes are allowed.

This tag causes the usual behaviour of werebeasts in worldgen, that is, fleeing towns upon being cursed and conducting raids from a lair. If this tag is absent from a deity curse, the accursed will simply be driven out of towns in a similar manner to vampires. When paired with SPOUSE_CONVERTER, a very small population of the creature will be created during worldgen (sometimes only a single individual will be created), and their histories will be tracked (that is, they will not spawn spontaneously later, they must either have children or convert other creatures to increase their numbers). The creature will settle in a lair and go on rampages during worldgen. It will actively attempt to seek out potential conversion targets to abduct, convert, and have children with (if possible).

| | Caste
| | Found on nightmares. Corpses and severed body parts derived from creatures with this token turn into smoke after a short while.

| | Caste
| | The creature caste does not appear in autumn.

| | Caste
| | Creature doesn't require connected body parts to move; generally used on undead creatures with connections that have rotted away.

| | Caste
| | Creature cannot become dizzy.

| | Caste
| | Creature does not need to drink. 

| | Caste
| | Creature does not need to eat.

| | Caste
| | Creature cannot suffer fevers.

| | Caste
| | The creature is biologically sexless, making it unable to breed.

| | Caste
| | The creature cannot raise any physical attributes.

| | Caste
| | The creature cannot lose any physical attributes.

| | Caste
| | Creature does not need to sleep, but can still be rendered unconscious by other means.

| | Caste
| | The creature caste does not appear in spring.

| | Caste
| | The creature caste does not appear in summer.

| | Caste
| | The bodyparts of this creature don't need to be connected to an organ with the  tag in order to have motor function. Generally used on creatures that don't have brains. If a creature doesn't have a thought part and doesn't have this token, it will be unable to grasp or stand. Nautilus men experience this issue in vanilla.

| | Caste
| | Prevents creature from selecting its color based on its profession (e.g. Miner, Hunter, Wrestler).

| | Caste
| | Likely prevents the creature from leaving broken vegetation tracks.

| | Caste
| | The creature caste does not appear in winter.

| | Caste
| | Creature cannot be picked up for worldgen fell moods and cannot be made a skeleton deity.

| | Caste
| | Creature doesn't need to breathe or have parts in its body, nor can it drown or be strangled. Creatures living in magma must have this tag, otherwise they will drown.

| | Caste
| | When set, the creature will only appear at night (after 10:05 PM and before 4:30 AM) in Adventurer mode.

| | Caste
| | Creature has no emotions, thus; it is immune to the effects of stress and unable to rage, and its needs cannot be fulfilled in any way. Used on undead in the vanilla game.

| | Caste
| | Creature can't become tired or over-exerted from taking too many combat actions, or moving at full speed for extended periods of time. 

| | Caste
| | Creature doesn't feel fear and will never flee from battle, and will be immune to ghosts' attempts to 'scare it to death'. Additionally, it causes bogeymen and nightmares to become friendly towards the creature.

| | Caste
| | Creature will not be hunted or fed to wild beasts.

| | Caste
| | Creature isn't nauseated by gut hits and cannot vomit.

| | Caste
| | Creature doesn't feel pain. 

| | Caste
| | Creature will not drop a hide when butchered. 

| | Caste
| | Creature will not drop a skull on butchering, rot, or decay of severed head.

| | Caste
| | Does not produce miasma when rotting.

| | Caste
| | Weapons can't get stuck in the creature. 

| | Caste
| | Creature can't be stunned and knocked unconscious by pain or head injuries. Creatures with this tag never wake up from sleep in Fortress Mode. If this creature needs to sleep while playing, it <b>will</b> die.

| | Caste
| | Corpses from this creature cannot be butchered. Does not prevent the creature from being slaughtered while alive, however.

| | Caste
| | Cannot be raised from the dead by necromancers or evil clouds. Implies the creature is not a normal living being. Used by vampires, mummies and inorganic creatures like the amethyst man and bronze colossus. Creatures who are  (undead) will be docile towards creatures with this token.

| | Caste
| | Creature doesn't require a  body part to survive. Has the added effect of preventing speech, though directly controlling creatures that would otherwise be capable of speaking allows them to engage in conversation.

1. O

**width="20%" | Token
**width="10%" | Type
**width="20%" | Arguments
**width="50%" | Description

| | Caste
| - number
| How easy the creature is to smell. The higher the number, the easier the creature is to sniff out. Defaults to 50. Vanilla creatures have values from 0 (undetectable) to 90 (noticeable by humans and dwarves).

| | Caste
| - string
| What the creature smells like. If no odor string is defined, the creature name (not the caste name) is used.

| | Caste
| | Is hostile to all creatures except undead and other non-living ones and will show  in the unit list. Used by undead in the vanilla game. Functions without the  token, and seems to imply said token as well. Undead will not be hostile to otherwise-living creatures given this token. Living creatures given this token will attack living creatures that lack it, while ignoring other living creatures that also have this token.

| | Caste
| - MALE/FEMALE
- disinterested chance
- casual chance
- strong chance
| Determines caste's likelihood of having sexual attraction to certain sexes. Values default to 75:20:5 for the same sex and 5:20:75 for the opposite sex. The first value indicates how likely to be entirely uninterested in the sex, the second decides if the creature will be able to become lovers with that sex, the third decides whether they will be able to marry in worldgen and post-worldgen world activities (which implies being able to become lovers). Marriage seems to be able to happen in fort mode play regardless, as long as they are lovers first.

| | Caste
| | Lets you play as an outsider of this species in adventure mode.

1. P

**width="20%" | Token
**width="10%" | Type
**width="20%" | Arguments
**width="50%" | Description

| | Caste
| | Allows the creature to be used as a pack animal. Used by merchants without wagons and adventurers. Also prevents creature from dropping hauled items on its own -- do *not* use for player-controllable creatures! May lead to the creature being domesticated during worldgen, even if it doesn't have .

Creatures with this tag but without , and/or with  leads to hauled items being dropped.

| | Caste
| | The creature is immune to all paralyzing special attacks.

| | Caste
| | Used to control the bat riders with paralyze-dart blowguns that flew through the 2D chasm. Doesn't do anything now.

| | Creature
| - Layering type
| Adds a layer to the current  definition. 

| | Caste
| | Does nothing.

| | Caste
| - value 
| Controls the ability of vermin to find a way into containers when they are eating food from your stockpiles.

Objects made of most materials (e.g. metal) roll a number from 0-100, and if the resulting number is greater than the penetrate power, their contents escape for the time being. Objects made of wood, leather, amber, or coral roll 0-95, and items made of cloth roll 0-90.

| | Caste
| - ATTRIBUTE
- lowest
- median
- highest 
| Determines the range and chance of personality facets. Standard is 0:50:100. See personality facet for more info.

| | Caste
| | Allows the creature to be tamed in Fortress mode. Prerequisite for all other working animal roles. Civilizations that encounter it in worldgen will tame and domesticate it for their own use. Adding this to civilization members will classify them as pets instead of citizens, with all the problems that entails. However, you can solve these problems using the popular plugin Dwarf Therapist, which is completely unaffected by the tag.

| | Caste
| | Allows the creature to be tamed in Fortress mode. Prequisite for all other working animal roles. Civilizations cannot domesticate it in worldgen, with certain exceptions. More difficult to tame? Adding this to civilization members will classify them as pets instead of citizens, with all the problems that entails. (Example).

| | Caste
| - value 
| How valuable a tamed animal is. Actual cost in points in the embarking screen is 1+(PETVALUE/2) for an untrained animal, 1+PETVALUE for a war/hunting one. 

| | Caste
| - value
| Divides the creature's  by the specified number. Used by honey bees to prevent a single hive from being worth a fortune.

| | Caste
| - ATTRIBUTE Token
- Cap %
| Default is 200. This means you can increase your attribute to 200% of its starting value (or the average value + your starting value if that is higher).

| | Caste
| - ATTRIBUTE
- lowest
- lower
- low
- median
- high
- higher
- highest 
| Sets up a physical attribute's range of values (0-5000). All physical attribute ranges default to 200:700:900:1000:1100:1300:2000.

| | Caste
| - ATTRIBUTE Token
- cost to improve
- unused counter rate
- rust counter rate
- demotion counter rate
| Physical attribute gain/decay rates. Lower numbers in the last three slots make decay occur faster. Defaults for STRENGTH, AGILITY, TOUGHNESS, and ENDURANCE are 500:3:4:3, while RECUPERATION and DISEASE_RESISTANCE default to 500:NONE:NONE:NONE.

| | Caste
| - BY_TYPE, BY_CATEGORY, or BY_TOKEN
- body type, category, or token
| Adds a body part group to selected body part group. Presumably used immediately after .

| | Creature
| - material
| Adds a material to selected materials. Used immediately after .

| | Caste
| - number (max 100000)
| Weighted population of caste; Lower is rarer. Not to be confused with . A weight of 0 will prevent a caste from spawning naturally. Regardless of pop ratio, Positions that only allow a certain caste can force it to spawn.

| | Creature
| - min
- max 
| The minimum/maximum numbers of how many of these creatures are present in each world map tile of the appropriate region. Defaults to 1:1 if not specified. If the creature's chosen  happens to be larger, it will be used instead.

| | Caste
| | Allows the being to represent itself as a deity, allowing it to become the leader of a civilized group. Not used by any creatures in the vanilla game. Requires  to actually do anything more than settle at a location (e.g. write books, lead armies, profane temples). Doesn't appear to do anything for creatures that are already civilized. Once the creature ascends to a position of leadership, it will proceed to act as a standard ruler for their entity and fulfill the same functions (hold tournaments, tame creatures, etc.).

| | Creature
| - string
| Sets what other creatures prefer about this creature. "Urist likes dwarves for their beards." Multiple entries will be chosen from at random. Creatures lacking a PREFSTRING token will never appear under another's preferences.

| | Creature
| - Sprite type or Caste then sprite type
| Makes the creature have procedural graphics built for it, like forgotten beasts/demons/titans/experiments. Must be associated with PCG_LAYERING tokens.

| | Creature
| - Unit type token (Profession)
- singular
- plural 
| The generic name for members of this profession, at the creature level. In order to give members of specific castes different names for professions, use  instead.

| | Caste
| - Chance
| Creature has a percentage chance to flip out at visible non-friendly creatures. Enraged creatures attack anything regardless of timidity and get a strength bonus to their hits. This is what makes badgers so hardcore.

| | Caste
| - <material token>
- <material state>
| The creature has pus. Specifies the stuff secreted by infected wounds.

1. R

**width="20%" | Token
**width="10%" | Type
**width="20%" | Arguments
**width="50%" | Description

| | Caste
| - BY_CATEGORY, BY_TYPE, BY_TOKEN
- body category, type, or token
- Relsize 
| Specifies a new relative size for a part than what is stated in the body plan. For example, dwarves have larger livers.

| | Caste
| - singular
- plural
| What the creature's remains are called.

| | Caste
| | What color the creature's remains are.

| | Caste
| | Goes with  and , the vermin creature will leave remains on death when biting. Leaving this tag out will cause the creature to disappear entirely after it bites.

| | Caste
| | Nothing.

| | Creature
| - material token 
| Removes a material from the creature.

| | Creature
| - tissue token
| Removes a tissue from the creature.

| | Caste
| - BY_TYPE, BY_CATEGORY or BY_TOKEN
- body type, category, or token
- Second person ("You") retract verb text
- Third person ("The giant snail") retract verb text
- Second person cancel retract text
- Third person cancel retract text
| The creature will retract into the specified body part(s) when threatened. It will be unable to move or attack, but enemies will only be able to attack the specified body part(s). When one of the specified body part is severed off, the creature automatically unretracts and cannot retract anymore. More than one body part can be selected by using BY_TYPE or BY_CATEGORY.

Second-person descriptions are used for adventurer mode natural ability. "<pro_pos>" can be used in the descriptions, being replaced with the proper pronoun (or lack thereof) in-game.

Undead curled up creatures are buggy, specifically those that retract into their upper bodies: echidnas, hedgehogs and pangolins. The upper body is prevented from collapsing by a separate body part (the middle spine), which cannot be attacked when the creature is retracted. See . Living creatures eventually succumb to blood loss, but undead creatures do not. Giant creatures also take a very long time to bleed out.

| | Creature
| | Cat behavior. If it kills a vermin creature and has an owner, it carries the remains in its mouth and drops them at their feet. Requires .

| | Caste
| - BY_TYPE, BY_CATEGORY or BY_TOKEN
- body type, category, or token
- Second person ("You") verb text
- Third person ("The hen") verb text
| Creature will occasionally root around in the grass, looking for insects.  Used for flavor in Adventurer Mode, spawns vermin edible for this creature in Fortress Mode. Creatures missing the specified body part will be unable to perform this action. The action produces a message (visible in adventure mode) in the form:

In adventure mode, the "rooting around" ability will be included in the "natural abilities" menu, represented by its second person verb text.

1. S

**width="20%" | Token
**width="10%" | Type
**width="20%" | Arguments
**width="50%" | Description

| | Creature
| | The creature will only show up in "savage" biomes. Has no effect on cavern creatures. Cannot be combined with  or .

| | Caste
| - <material token>
- <material state>
- BY_TOKEN / BY_CATEGORY / BY_TYPE
- <body part ID> / <category> or ALL / <type (e.g. GRASP)>
- <tissue layer> or ALL
- <trigger>
| Causes the specified tissue layer(s) of the indicated body part(s) to secrete the designated material. A size 100 ('covering') contaminant is created over the affected body part(s) in its specified material state (and at the temperature appropriate to this state) when the trigger condition is met, as long as one of the secretory tissue layers is still intact. Valid triggers are:
      - CONTINUOUS**
Secretion occurs once every 40 ticks in fortress mode, and every tick in adventurer mode.
      - EXERTION**
Secretion occurs continuously (at the rate described above) whilst the creature is at minimum <span style="font-size:75%"> following physical exertion. Note that this cannot occur if the creature has .
      - EXTREME_EMOTION**
Secretion occurs continuously (as above) whilst the creature is distressed. Cannot occur in creatures with .

| | Creature
| - <caste>
| Adds an additional previously defined caste to the selection. Used after .

| | Creature
| - <caste> or ALL 
| Selects a previously defined caste

| | Creature
| - <material token>
| Selects a locally defined material. Can be ALL.

| | Creature
| - tissue token
| Selects a tissue for editing.

| | Caste
| | Essentially the same as , but more of them are created during worldgen. See the semi-megabeast page for details.

| | Caste
| - <creature class>
- <tile value or character>
- <foreground color>:<background color>:<foreground brightness>
| Gives the creature the ability to sense creatures belonging to the specified creature class even when they lie far beyond line of sight, including through walls and floors. It also appears to reduce or negate the combat penalty of blind units when fighting creatures they can sense. In adventure mode, the specified tile will be used to represent sensed creatures when they cannot be seen directly.

| | Caste
| - selection criteria BY_TYPE, BY_CATEGORY, BY_TOKEN
- category, type, or token 
| Begins a selection of body parts.

| | Caste
| - <skill_token>
- <percentage>
| The rate at which this creature learns this skill. Requires  or  to function.

| | Caste
| - <percentage>
| The rate at which this creature learns all skills. Requires  or  to function.

| | Caste
| - skill_token
- <% of improvement points gained>
- <unused counter rate>
- <rust counter rate>
- <demotion counter rate>
| Like , but applies to individual skills instead. Requires  or  to function.

| | Caste
| - <% of improvement points gained>
- <unused counter rate>
- <rust counter rate>
- <demotion counter rate>
| Affects skill gain and decay. Lower numbers in the last three slots make decay occur faster ([SKILL_RATES:100:1:1:1] would cause rapid decay). The counter rates may also be replaced with NONE.
Default is [SKILL_RATES:100:8:16:16]. Requires  or  to function.

| | Caste
| - skill_token
- value
- value
- value
| The rate at which this skill decays. Lower values cause the skill to decay faster. Requires  or  to function.

| | Caste
| - value
- value
- value
| The rate at which all skills decay. Lower values cause the skills to decay faster. Requires  or  to function.

| | Caste
| - text set
| Caste-specific .

| | Creature
| - text set
| Boasting speeches relating to killing this creature. Examples include text_dwarf.txt (`[SLAIN_SPEECH:SLAIN_DWARF]`) and text_elf.txt (`[SLAIN_SPEECH:SLAIN_ELF]`) in data\vanilla\vanilla_creatures\objects.

| | Caste
| | Shorthand for  + `[SKILL_LEARN_RATES:50]`. Used by a number of 'primitive' creatures (like ogres, giants and troglodytes) in the vanilla game. Applicable to player races. Prevents a player from recruiting nobility, even basic ones. Subterranean creatures with this token combined with  will become servants of goblins in their civilizations, in the style of trolls.

| | Caste
| | Creature leaves "remains" instead of a corpse. Used by vermin.

| | Caste
| - value
| Determines how keen a creature's sense of smell is - lower is better. At 10000, a creature cannot smell at all.

| | Creature
| - 'character' or tile number
| If this creature is active in its civilization's military, it will blink between its default tile and this one.

| | Caste
| - Sound application (currently accepts ALERT or PEACEFUL_INTERMITTENT)
- Sound range (in tiles)
- Sound delay (lower values = sound is produced more often)
- VOCALIZATION or NONE (determines whether the sound requires breathing or not)
- First-person description
- Third-person description
- Description when out of sight
| Creature makes sounds periodically, which can be heard in Adventure mode.
- First-person reads "You **bark**"
- Third-person reads "The capybara **barks**"
- Out of sight reads "You hear **a loud bark**"
with the text in bold being the description arguments of the token.

| | Creature
| - Integer
| Found on generated angels. This is the historical figure ID of the deity with which the angel is associated. Since HFIDs are not predictable before worldgen, this isn't terribly usable in mods.

| | Caste
| - PLANT or CREATURE
- Plant/creature ID
| Creature will only appear in biomes with this plant or creature available. Grazers given a specific type of grass (such as pandas and bamboo) will only eat that grass and nothing else, risking starvation if there's none available. 

| | Creature
| - sphere
| Sets what religious spheres the creature is aligned to, for purposes of being worshipped via the  token. Also affects the creature's name.

| | Caste
| | This creature can be converted by a night creature with .

| | Caste
| | If the creature has the  tag, it will kidnap s and transform them into the caste of its species with the  tag during worldgen. It may also start families this way.

| | Caste
| | If the creature rules over a site, it will cause the local landscape to be corrupted into evil surroundings associated with the creature's spheres. The creature must have at least one of the following spheres for this to take effect: BLIGHT, DEATH, DISEASE, DEFORMITY, NIGHTMARES. The first three kill vegetation, while the others sometimes do.  The last two get evil plants and evil animals sometimes. NIGHTMARES gets bogeymen. Used by demons in the vanilla game.

| | Caste
| | Caste does not require `[GRASP` body parts to climb -- it can climb with `[STANCE]` parts instead.

| | Caste
| | Acts as  but set to 20000*G*(max size)^(-3/4), where G defaults to 100 but can be set in d_init, and the whole thing is trapped between 150 and 3 million. Used for all grazers in the default creature raws.

| | Caste
| | The creature will get strange moods in fortress mode and can produce artifacts.

| | Caste
| | Gives the creature knowledge of any secrets with `[SUPERNATURAL_LEARNING_POSSIBLE]` that match its spheres and also prevents it from becoming a vampire or werebeast. Other effects are unknown.

| | Caste
| | The creature naturally knows how to swim perfectly and does not use the swimmer skill, as opposed to  below. However, Fortress mode AI never paths into water anyway, so it's less useful there. 

| | Caste
| | The creature swims only as well as their present swimming skill allows them to.

| | Caste
| <syndrome identifier>:<percentage>
| Dilutes the effects of syndromes which have the specified identifier. A percentage of 100 is equal to the regular syndrome effect severity, higher percentages reduce severity.

1. T

**width="20%" | Token
**width="10%" | Type
**width="20%" | Arguments
**width="50%" | Description

| | Caste
| - material token
- healing rate 
| The creature has tendons in its  tissues (bone or chitin by default). Cutting the bone/chitin tissue severs the tendons, disabling motor function if the target is a limb.

| | Caste
| | The creature's webs can catch larger creatures.

| | Creature
| - name 
| Begins defining a tissue in the creature file. Follow this with standard tissue definition tokens to define the tissue properties.

| | Caste
| - BY_TYPE, BY_CATEGORY, BY_TOKEN
- TYPE,CATEGORY, or TOKEN
- TISSUE
- LOCATION 
| Adds the tissue layer to wherever it is required.
Non-argument Locations can be FRONT, RIGHT, LEFT, TOP, BOTTOM. Argument locations are AROUND and CLEANS, requiring a further body part and a % of coverage/cleansing

| | Caste
| - BY_TYPE, BY_CATEGORY, BY_TOKEN
- TYPE,CATEGORY, or TOKEN
- TISSUE
- LOCATION 
| Alias for TISSUE_LAYER

| | Caste
| - BY_TYPE, BY_CATEGORY, BY_TOKEN
- TYPE,CATEGORY, or TOKEN
- TISSUE
| Adds the tissue layer under a given part.
For example, an iron man has a gaseous poison within, and this tissue (GAS is its name) has the token [TISSUE_LEAKS] and its state is GAS, so when you puncture the iron outside and damage this tissue it leaks gas (can have a syndrome by using a previous one in the creature sample.) [TISSUE_LAYER_UNDER:BY_CATEGORY:ALL:{tissue}] {tissue} is what will be under the TISSUE_LAYER; here is an example Tissue from the Iron Man: 
[TISSUE:GAS] [TISSUE_NAME:gas:NP] [TISSUE_MATERIAL:LOCAL_CREATURE_MAT:GAS] [TISSUE_MAT_STATE:GAS] [RELATIVE_THICKNESS:50] [TISSUE_LEAKS] [TISSUE_SHAPE:LAYER] 

| | Caste
| | Found on titans. Cannot be specified in user-defined raws.

| | Caste
| - number
| How much the creature can carry when used by merchants. 1000 by default. Completely ignored if the animal does not also have PACK_ANIMAL or WAGON, instead using BODY_SIZE^(2/3)/20, even if they're a pack animal due to ANIMAL_ALWAYS_PACK_ANIMAL.

| | Caste
| | Shortcut for  + .

| | Caste
| | Can be trained as a hunting beast, increasing speed.

| | Caste
| | Can be trained as a war beast, increasing strength and endurance.

| | Caste
| | Allows the creature to go into martial trances. Used by dwarves in the vanilla game.

| | Caste
| | The creature will never trigger traps it steps on. Used by a number of creatures. Doesn't make the creature immune to remotely activated traps (like retractable spikes being triggered while the creature is standing over them). TRAPAVOID creatures lose this power if they're immobilized while standing in a trap, be it by stepping on thick web, being paralyzed or being knocked unconscious.

| | Creature
| - min
- max 
| A large swarm of vermin can be disturbed, usually in adventurer mode.

| | Caste
| - noun
- SINGULAR or PLURAL 
| Noun for the , used in the description of the tissue layer's style.

1. U

**width="20%" | Token
**width="10%" | Type
**width="20%" | Arguments
**width="50%" | Description

| | Creature
| | Creature will occur in every region with the correct biome. Does not apply to / tags. Supersedes  for the purposes of distributing populations through the map, they are present in every part of the valid biome. Respects  for the frequency of unit cluster spawns being of this species.

| | Creature
| - mindepth
- maxdepth 
| Depth that the creature appears underground. Numbers can be from 0 to 5. 0 is actually 'above ground' and can be used if the creature is to appear both above and below ground. Values from 1-3 are the respective cavern levels, 4 is the magma sea and 5 is the HFS. A single argument may be used instead of min and max. Demons use only 5:5; user-defined creatures with both this depth and  will take part in the initial wave from the HFS alongside generated demons, but without  they will only spawn from the map edges. Civilizations that can use underground plants or animals will only export (via the embark screen or caravans) things that are available at depth 1.

| | Caste
| | The creature is displayed as blue when in 7/7 water. Used on fish and amphibious creatures which swim under the water.

| | Caste
| | Found on generated demons; causes the game to create a single named instance of the demon which will emerge from the underworld and take over civilizations during worldgen.

| | Creature
| - new caste token
- old caste token
| Defines a new caste derived directly from a previous caste. The new caste inherits all properties of the old one. The effect of this tag is automatic if one has not yet defined any castes: "Any caste-level tag that occurs before castes are explicitly declared is saved up and placed on any caste that is declared later, unless the caste is explicitly derived from another caste."
Roostre: "When DF detects duplicate tokens in the raws of the same object, a failsafe seems to kick in; it takes the bottom-most of the duplicates, and disregards the others. In the case of tokens added by a mod, it prioritizes the duplicate in the mod." This means that if a tag is defined in the base-caste and redefined in the derived caste, the derived tag overwrites the base tag. 

| | Creature
| - new material ID
- old material ID
| Defines a new local creature material and populates it with all properties defined in the specified local creature material.

| | Creature
| - new material token
- material template 
| Defines a new local creature material and populates it with all properties defined in the specified template. There seems to be a limit of 200 materials per creature.

| | Creature
| - new tissue token
- old tissue id
| Defines a new local creature tissue and populates it with all properties defined in the local tissue specified in the second argument.

| | Creature
| - new tissue token
- tissue template
| Loads a tissue template listed in OBJECT:TISSUE_TEMPLATE files, such as tissue_template_default.txt. 

| | Creature
| | Changes the language of the creature into unintelligible 'kobold-speak', which creatures of other species will be unable to understand. If a civilized creature has this and is not part of a  civ, it will tend to start wars with all nearby civilizations and will be unable to make peace treaties due to 'inability to communicate'.

1. V

**width="20%" | Token
**width="10%" | Type
**width="20%" | Arguments
**width="50%" | Description

| | Caste
| | Like , but also makes the creature more valued in artwork by civilisations with the PLANT sphere. Used by grimelings in the vanilla game.

| | Caste
| - chance of occurrence
- verb (bitten, stung, etc.)
- material token
- material state
| Enables vermin to bite other creatures, injecting the specified material. See  for details about injection - this token presumably works in a similar manner.

| | Creature
| | The vermin creature will attempt to eat exposed food. See . Distinct from .

| | Creature
| | The vermin appears in water and will attempt to swim around.

| | Creature
| | The creature appears in "general" surface ground locations. Note that this doesn't stop the creature from flying if it can (most vermin birds have this tag).

| | Caste
| | Some dwarves will hate the creature and get unhappy thoughts when around it. See the list of hateable vermin for details.

| | Caste
| | This makes the creature move in a swarm of creatures of the same race as it (e.g. swarm of flies, swarm of ants).

| | Caste
| | The creature cannot be caught by fishing. 

| | Caste
| | The creature will not be observed randomly roaming about the map. 

| | Caste
| | The creature cannot be caught in baited animal traps; however, a "catch live land animal" task may still be able to capture one if a dwarf finds one roaming around.

| | Creature
| | The vermin are attracted to rotting stuff and loose food left in the open and cause unhappy thoughts to dwarves who encounter them. Present on flies, knuckle worms, acorn flies, and blood gnats.

| | Creature
| | The creature randomly appears near dirt or mud, and may be uncovered by creatures that have the  interaction such as geese and chickens. Dwarves will ignore the creature when given the "Capture live land animal" task.

| | Creature
| | The vermin will appear in a single tile cluster of many vermin, such as a colony of ants.

| | Caste
| | Old shorthand for "does cat stuff". Contains  +  +  + .

| | Caste
| | When set, the creature will only appear in the evening (between 8:00 PM and 10:05 PM) in Adventurer mode.

| | Caste
| - value
| Value should determine how close you have to get to a critter before it attacks (or prevents adv mode travel etc.) Default is 20.

| | Caste
| - binocular vision arc
- non-binocular vision arc
| The width of the creature's vision arcs, in degrees (i.e. 0 to 360). The first number is binocular vision, the second is non-binocular vision.  Binocular vision has a minimum of about 10 degrees, monocular, a maximum of about 350 degrees. Values past these limits will be accepted, but will default to ~10 degrees and ~350 degrees respectively. Defaults are 60:120.

1. W

**width="20%" | Token
**width="10%" | Type
**width="20%" | Arguments
**width="50%" | Description

| | Caste
| | Allows the creature to pull caravan wagons. If a civilization doesn't have access to any, it is restricted to trading with pack animals.

| | Caste
| - material token
| Allows the creature to create webs, and defines what the webs are made of.

| | Caste
| | The creature will not get caught in thick webs. Used by creatures who can shoot thick webs (such as giant cave spiders) in order to make them immune to their own attacks.

1. Attack Tokens

Attacks can use four different part selection criteria. Except for TISSUE_LAYER, the base game makes use of all of these in its attacks.

**width="20%" | Part type token
**width="30%" | Arguments
**width="60%" | Description

| | - BY_TYPE/BY_TOKEN/BY_CATEGORY
- type/token/category
| This attack uses a particular body part; for example, ATTACK:PUNCH:BODYPART:BY_TYPE:GRASP will make it use any part that can hold onto an object.

| | - BY_TYPE/BY_TOKEN/BY_CATEGORY
- type/token/category
- tissue layer
| This attack uses a specific tissue layer on a specific body part; ATTACK:SCRATCH:TISSUE_LAYER:BY_TYPE:GRASP:BONE will make it use the bone of the hands.

| | - BY_TYPE/BY_TOKEN/BY_CATEGORY
- type/token/category
- BY_TYPE/BY_TOKEN/BY_CATEGORY
- type/token/category
| Uses a body part that is subordinate to another; ATTACK:SLAP:CHILD_BODYPART_GROUP:BY_CATEGORY:ARM_LOWER:BY_TYPE:GRASP will make it use every hand attached to each lower arm (so it will generate one attack per lower arm, each of which will use every hand on that arm, assuming there are multiple hands per arm).

| | - BY_TYPE/BY_TOKEN/BY_CATEGORY
- type/token/category
- BY_TYPE/BY_TOKEN/BY_CATEGORY
- type/token/category
- tissue layer
| As CHILD_BODYPART_GROUP, but specifying a tissue, too; ATTACK:BITE:CHILD_BODYPART_GROUP:BY_CATEGORY:HEAD:BY_CATEGORY:TOOTH

**width="20%" | Token
**width="10%" | Type
**width="20%" | Arguments
**width="50%" | Description

| | Caste
| - Skill token
| Defines the skill used by the attack.

| | Caste
| - 2nd person
- 3rd person 
| Descriptive text for the attack.

| | Caste
| - % value 
| The contact area of the attack, measured in % of the body part's volume. Note that all attack percentages can be more than 100%.

| | Caste
| - % value 
| The penetration value of the attack, measured in % of the body part's volume. Requires ATTACK_FLAG_EDGE. Maximum value: 15000.

| | Caste
| - MAIN or SECOND 
| Usage frequency. MAIN attacks are 100 times more frequently chosen than SECOND. Opportunity attacks ignore this preference.

| | Caste
| - number
| The velocity multiplier of the attack, multiplied by 1000.

| | Caste
| | Attacks that damage tissue have the chance to latch on in a wrestling hold. The grabbing bodypart can then use the "shake around" wrestling move, causing severe, armor-bypassing tensile damage according to the attacker's body volume.

| | Caste
| | Displays the name of the body part used to perform an attack while announcing it, e.g. "The weaver punches the bugbat with his right hand".

| | Caste
| | The attack is edged, with all the effects on physical resistance and contact area that it entails.

| | Caste
| - Preparation time
- Recovery time
| Determines the length of time to prepare this attack and until one can perform this attack again. Values appear to be calculated in adventure mode ticks.

| | Caste
| | Multiple strikes with this attack cannot be performed effectively.

| | Caste
| | Multiple strikes with this attack can be performed with no penalty. The creature will use all attacks with this token at once.

| | Caste
| - <material token>
- <material state>
- <min quantity>
- <max quantity>
| When added to an attack, causes the attack to inject the specified material into the victim's bloodstream. Once injected, the material will participate in thermal exchange within the creature - injecting something like molten iron (INORGANIC:IRON:LIQUID) would cause most unmodded creatures to melt (note that some of the injected material also splatters over the bodypart used to carry out the attack, so it should be protected appropriately). If the injected material has an associated syndrome with the [SYN_INJECTED token, it will be transmitted to the victim. If the attack is blunt, the injected material lacks the [ENTERS_BLOOD] token, the attacked bodypart has no [VASCULAR] tissues, or the victim is bloodless, the material will splatter over the attacked body part instead. 

| | Caste
| - interaction
| When this attack lands successfully, a specified interaction will take effect on the target creature. The attack must break the target creature's skin in order to work. This will take effect in worldgen as well. If the attack would break skin, the interaction will occur **before the attack actually lands**.

| | Caste
| - min
- max
| Successful attack draws out an amount of blood randomized between the min and max value. Beware that this **will** trigger any ingestion syndromes attached to the target creature's blood - for example, using this attack on a vampire will turn you into one too.

1. Tissue Layer Tokens
Tissue layers are added to a creature's body parts by the creature tokens TISSUE_LAYER, TISSUE_LAYER_OVER, TISSUE_LAYER_UNDER, and the body detail plan token TL_LAYERS.

These tissue layers are not the same thing as tissues, which are defined at creature level, but rather applications of the tissues. If the SKIN tissue of a creature is the more general and abstract notion of what skin is for that creature, then a tissue layer may be the "actual" skin on the creature's nose, head, or second toe. As most creatures have more than one body part, tissue layers are normally selected en masse.

Some tissue layer tokens are analogous to tissue definition tokens, e.g. TL_CONNECTS to CONNECTS.

**width="20%" | Token
**width="10%" | Type
**width="20%" | Arguments
**width="50%" | Description

| | Caste
| - TISSUE
- BY_CATEGORY, BY_TYPE, BY_TOKEN
- Location - category, type, or token | Selects a tissue at a location
- (optional) FRONT, BACK, LEFT, RIGHT, TOP, BOTTOM, AROUND.
| Begins a selection of tissue layers. 
[SELECT_TISSUE_LAYER:HEART:BY_TYPE:HEART]

| | Caste
| - TISSUE
- BY_CATEGORY, BY_TYPE, BY_TOKEN
- Location - category, type, or token 
| Adds tissue layers to those selected.

| | Caste
| - TISSUE
- BY_CATEGORY, BY_TYPE, BY_TOKEN
- Location - category, type, or token
- tissue 
| Begins a selection of tissue layers. Only usable for descriptor and cosmetic purposes. 

Research has implied it may be redundant with SELECT_TISSUE_LAYER, as the latter allows for cosmetics as well as "functional" tokens such as TL_MAJOR_ARTERIES. Vanilla raws still use SET_TL_GROUP though, for all cosmetic purposes. More research is needed on this subject.

| | Caste
| - BY_CATEGORY, BY_TYPE, BY_TOKEN
- Location - category, type, or token
- tissue 
| Adds tissue layers to those selected. Like SET_TL_GROUP, it may be redundant even if used in the vanilla raws.

| | Caste
| - TISSUE
| Sets a selected tissue layer to be made of a different tissue.

| | Caste
| - tissue modifier
- required value
| Tissue layer can be sheared for its component material. The specified modifier must be at least of the desired value for shearing to be possible (for example, a llama's wool must have a LENGTH of 300 before it is shearable).

| | Caste
| - QUALITY
- lowest
- lower
- low
- median
- high
- higher
- highest 
| Sets the range of qualities, including LENGTH, DENSE, HIGH_POSITION, CURLY, GREASY, WRINKLY

| | Caste
| - tissue style unit ID
- shaping
| Sets tissue layer to be the target of TISSUE_STYLE token specified for an entity, works only on entity members. Mostly used with tissues HAIR, BEARD, MOUSTACHE, SIDEBURNS.

| | Caste
| - COLOR
- freq
- COLOR
- freq etc. 
| Creates a list of colors/color patterns, giving each a relative frequency. If the given color or pattern does not exist, the tissue is described as being "transparent".

| | Caste
| | The way the color modifier is passed on to offspring. May or may not work right now.

| | Caste
| - number
| Presumably modifies the importance of the tissue layer color modifier, for description purposes.
HOWEVER using this appears to remove all mention of colour from creature descriptions. It does not appear in any default creatures.

| | Caste
| - name
- SINGULAR or PLURAL
| Names the tissue layer color modifier, and determines the noun. Also used by Stonesense for colouring body parts. 

| | Caste
| - ROOT
- start change window years
- days
- end change window years
- days
| Determines the point in the creature's life when the color change begins and ends.

| | Caste
| | Gives the CONNECTS attribute to selected layers.

| | Caste
| - value
| Changes the HEALING_RATE of the selected tissue layers.

| | Caste
| | Gives the "major arteries" attribute to selected layers. Used to add massive bleeding properties to the throat, made from skin.

| | Caste
| - value
| Changes the number of pain receptors for selected tissue layers.

| | Caste
| - value
| Changes the relative thickness for selected tissue layers.

| | Caste
| - value
| Sets a new VASCULAR value (which modulates bleeding) for selected tissue layers.

1. See Also
- Body detail plan token
- Body token
- Material definition token
- Syndrome
- Tissue definition token
- Creature examples

ru:Creature token
