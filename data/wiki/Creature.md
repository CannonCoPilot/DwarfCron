# Creature

rightIn *Dwarf Fortress*, a **creature** is defined as any animate, normally-mobile (and for the sake of this article, non-vermin) being that can interact with the world and any element inside it. The creatures in the game range from being entirely realistic to completely mythical. Although most creatures are animals, dwarves, giant cave spiders, and even megabeasts are all also considered creatures. Various creatures can and will interact with a fortress or adventurer in many different ways.

Some creatures have skills that match what type of creature they are (e.g. monkeys having legendary climbing skill). Though most creatures can be found in any mode, some are exclusive to adventure mode or fortress mode. Some creatures are randomly and procedurally generated, meaning they could have many different sprites in-game. Creatures of that type may have just one to a few sprites showcased out of many in the list below. A question-mark placeholder may also be shown instead. Also note that creatures with the  or  tokens cannot be spawned in the object testing arena, similarly to vermin (e.g. flies, worms).

Nearly all creatures in the game, including very large ones, take the space of a single tile, even if their sprites imply otherwise (wagons being the only exception). There are 670 creatures in the game. In adventure mode, creatures can have different labels to differentiate similar ones from historical figures. For example, a goblin may be labeled as a "white-haired goblin bowyer" while another would be a "high-cheekbones goblin bowyer".

1. Spawning
<!--thumb|172px|right|Many creatures packed into one area, in the object testing arena.-->thumb|right|124px|Many creatures packed into one area, but in ASCII mode.The creatures that will spawn on any given fortress map depend on the biome(s) that the fortress is in. Additionally, there are several creature tokens in the raws that deal with creature spawning:
- <tt>[FREQUENCY:X]</tt>: This tag dictates *how often* a creature will spawn. It ranges from 0-100, and is a comparative number, where the higher this number is, the more likely the creature is to spawn. 
- <tt>[CLUSTER_NUMBER:X]</tt>: This determines *how many* creatures will appear at one time on a map.
- <tt>[POPULATION_NUMBER:X]</tt>: This determines the *total number* of this type of creature that can *ever* visit your fortress - the exact number varies, depending on the map.
 
For example, deer have a <tt>[POPULATION_NUMBER:15:30]</tt>, meaning that if you kill between 15-30 deer, no more deer will ever visit your fortress.

1. Reading the Table

The above columns indicate, in order:
- **Graphic:** The sprite assigned to the creature. Seen only in the premium version.
- **Tile:** The tile assigned to the creature, how you will see it without a graphic set.
- **Name:** The name of the creature as it displays in-game.
- **Playable:** If "No", the creature is not playable in any modes. "Fort" indicates that the creature is playable in fortress mode (). "Adv" indicates that the creature is playable in adventure mode. All creatures except humans must have a population in an  civilization in order to be playable in adventure mode; goblins (and other creatures) cannot be played from a goblin civ. Humans can be played whether or not a population exists due to , but an  civ still needs to have existed at some point. Creatures with  are also playable in adventure mode.
- **Hostile:** If "Yes", then the creature will attack on sight, if "No" then the creature is either neutral, or friendly -  mindless undead creatures are always hostile to living things.
- **Food Source:** If "Yes", then the creature can be butchered into an edible substance that your dwarves will feed on.
- **Adult Body Size:** The average size of the creature when an adult. This can be anywhere from 500 for a rabbit, to 25,000,000 for a dragon. This value represents the creature's volume in cm3, which, for creatures made of flesh, more-or-less equals the creature's weight in grams.These sizes do not correspond to the sizes which trigger pressure plates. Size is modified with height and broadness (i.e. incredibly skinny and short is below the average weight, while a fat and tall one is above it).
- **Pet Value:** This is the base value that the creature and its butchering products can be bought and sold for during trading.
- **Biome:** Where the creature can be found.
- **Features:** Any special features the creature possesses, including things such as causing a syndrome, breathing fire, or spinning webs.

Note: If you wish to view alternate ways of sorting creatures, such as sorting by biomes and location, or sorting domestic creatures by features, there is a new page found here: Alternate creature sorting

1. Creatures
1. Civilized
1. Main races
These are intelligent creatures that form the dominant civilized races of the world. While most are part of society, many have turned to banditry.

:1. Whether or not you are hostile with select civilized races depends on the history of your game world, and its length. Shorter histories mean less ongoing wars and general hostility, good for a newer player to learn the basics.
:2. Snatchers try to snatch children of other civilizations. Snatched individuals become part of the Snatcher's civilization.

1. Underground Tribes
Intelligent animal people that form crude civilizations underground, but will not trade with you. They wield some weapons and can join adventurers. They can also perform ambushes once the caverns are reached, depending on which creatures are hostile.

:1. Animal person civilizations initially encountered in the caverns will never be hostile, even if the game states otherwise. Those encountered in ambushes, however, will be aggressive.
:2. Ant-men body sizes depend on their caste.

1. Livestock and Domestic Animals
<!--EDITORS - PLEASE READ NOTES AT TOP OF PAGE, thanks!-->

Creatures that have long been domesticated, and either play a part in the meat industry, or are simply pets to keep dwarves company. Note: Except for wagons, domestic animals can be bought at embark, or requested from dwarven caravans.  Animals of these types below that are caught in the wild with cage traps can be tamed after only one session with an animal trainer.

1. Beasts and Monsters
All kinds of monstrous creatures that roam the land and underground caverns, including: semi-megabeasts, megabeasts, and randomly generated ones that can take any form. all very powerful and can easily be game-ending.

1. Semi-Megabeasts
<!--EDITORS - PLEASE READ NOTES AT TOP OF PAGE, thanks!-->

1. Megabeasts
<!--EDITORS - PLEASE READ NOTES AT TOP OF PAGE, thanks!-->

1. Procedurally generated
These creatures are procedurally generated, and different for every savefile. Their raws may be extracted from the world.dat file in uncompressed save folders. Their sprite will appear as the closest resemblance to their randomly generated appearance, including their colors and design, such as having wings, trunks, tusks, etc. The animated sprites below are just a few possible sprites without custom colors added.

1. Wild Animals
This section includes wild animals, as well as their giant and humanoid counterparts. Wild animals are mostly found roaming the wilderness. Many of them are predators, while others are benign, and will not attack unless being attacked first. Some will be drawn to your stockpiles to steal drink, food or something shiny. Some can be easily overcome, and yet others can be significant threats, like the dreaded elephant.

1. Agitation
Disruption of the environment in a savage biome, such as woodcutting or fishing, may cause the appearance of "agitated" or "irritated" animals. Agitated animals will directly seek out and attack dwarves, instead of their normal behavior. Agitation rate and threshold can be adjusted in the difficulty settings. Agitation can be removed by taming animals captured in cage traps. With DFHack, it is possible to check current agitation status by executing the command `agitation-rebalance status`[https://docs.dfhack.org/en/stable/docs/tools/agitation-rebalance.html.

1. Above Ground
<!--EDITORS - PLEASE READ NOTES AT TOP OF PAGE, thanks!-->

 

1. Subterranean
<!--EDITORS - PLEASE READ NOTES AT TOP OF PAGE, thanks!-->

1. Aquatic
Note: This does not include subterranean sea creatures.
<!--EDITORS - PLEASE READ NOTES AT TOP OF PAGE, thanks!-->

1. Night Creatures / Other
<!--EDITORS - PLEASE READ NOTES AT TOP OF PAGE, thanks!-->

1. Night creatures
These creatures are either vicious creatures that attack in the night, or are created through certain interactions - be it a condition of the game, or intentionally by another creature.

 

:1. In some worlds, intelligent experiments escape their creators and join normal civilizations. They will then be playable in adventurer mode.
:2. The player cannot normally start out as an intelligent undead, but can unretire a former adventurer that has been resurrected. This can also be done (without unretiring) by using adventurer parties.
:3. The player cannot start out as a necromancer, but can gain necromancer powers by reading a slab or book containing the secrets of life and death.
:4. The player cannot start out as a vampire, but can become one by feeding on spilled vampire blood. Animal people with the ability to suck blood can also gain vampirism by blood-sucking a vampire during combat.

1. Hidden Fun Stuff
<!--EDITORS - PLEASE READ NOTES AT TOP OF PAGE, thanks!-->

†except in a few special cases

1. Nonexistent
<!--EDITORS - PLEASE READ NOTES AT TOP OF PAGE, IT'S VERY IMPORTANT FOR THIS CATEGORY, thanks!-->

1. Trivia
- right|thumb|The debug creature.If the game does not recognize a creature and/or cannot find the sprite associated for it, the sprite will default to a blue, round, blob-like face with stubby legs.
- Many of the original underground creatures were drawn by Tarn and Zach Adams "in a couple of notebooks in our parents' living room one day, more than a decade ago, when we were trying to populate the new-at-the-time 3D underground." (Bay 12 Games)While most of these were implemented in v0.31, some concepts were left on the cutting room floor.
    - Page 1: Bugbat and drunian.
    - Page 2: Manera and king cave worm.
    - Page 3: Molemarian and mole rat man.
    - Page 4: Magma seal, magma walrus, and jabberer.
    - Page 5: Pond grabber, blind cave bear, cave dragon, and reacher.
    - Page 6: Gorlak and cave fish man.
    - Page 7: Floating guts, drunian, and grabber.
    - Page 8: Creeping eye, voracious cave crawler, and blind cave ogre.
    - Page 9: Cap hopper, magma crab, and crundle.
    - Page 10: Hungry head, flesh ball, and elk bird.
    - Page 11: Helmet snake, green devourer, and rutherer.
    - Page 12: Creepy crawler.
    - Page 13: Draltha, giant earthworm, and blood man.
    - Page 14: Stilt plucker.

ru:Creature
