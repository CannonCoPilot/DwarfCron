# DF2014:Position token

These tokens define positions in entity_*.txt files (see Entity token).

__TOC__

1. Position tokens
These tokens belong in an entity definition. These tokens apply to a position (such as monarch) and should follow the [POSITION:POSITION_NAME] token.

**Token
**Arguments
**Description

| | | The position holder is not subjected to the economy. Less than relevant right now.

| | token
| Only creatures with the specified class token can be appointed to this position.

| | CREATURE:CASTE
| Restricts the position to only the defined caste. Only works with a caste of the entity's current race. (If the entity had multiple CREATURE: tokens)

| | position
| This position can only be chosen for the task from the nobles screen, and is available only if there is an *argument* present. For example, the GENERAL is [APPOINTED_BY:MONARCH]. Contrast [ELECTED]. Being appointed by a MONARCH seems to handle a lot of worldgen stuff, and interferes with fort mode titles.

| | | A creature that kills a member of this position will be sure to talk about it a lot.

| | | In adventure mode, when referencing locations, an NPC may mention this position holder living there or having done some deed there, it also means that the position exists in world-gen, rather than being created only at the end of world-gen.
Before 47.05, Dark Fortress civs cannot have this tag on anybody but their Law Maker, or the game will crash without leaving an errorlog.

| | color
| Creatures of this position will have this color, instead of their profession color, e.g. [COLOR:5:0:1].

| | position:ALL
| This position will act as a commander of the specified position. E.g. GENERAL is [COMMANDER:LIEUTENANT:ALL]. Unknown if values other than ALL work.

| | | This position is a puppet ruler left behind in a conquered site.

| | number (0-100)
| How many demands the position can make of the population at one time.

| | | The site's (or civ's) minted coins, if any, will have images that reflect the personality of this position holder.

| | | The position won't be culled from Legends as "unimportant" during world generation.

| | | Members of this position will never agree to 'join' your character during adventure mode.

| | | The population will periodically select the most skill-eligible creature to fill this position for site-level positions at the player's fort. For responsibilities or positions that use more than one skill, no skill takes priority in electing a creature: an accomplished comedian is more qualified for the TRADE responsibility than a skilled appraiser. A creature may be elected to multiple positions at the same time. Contrast [APPOINTED_BY].

| | weapon skill
| A mandatory sub-tag of [RESPONSIBILITY:EXECUTIONS]. Determines the weapon chosen by the executioner for their work.

| | | The various members who have filled this role will be listed in the civilisation's history.

| | | The creature holding this position will visibly flash, like legendary citizens. Represents a properly noble station by default.

| | male/female
| The position can only be held by the specified gender. Currently bugged 

| | | The position can assign quests to adventurers.

| | importance tier (1-10)
| This is an alternative to SITE.  What it does is allow positions to be created at civ-level 'as needed' for all sites that meet the requirements to have them, which are the values set in LAND_HOLDER_TRIGGER.  The character is tied permanently to a particular site but also operates at the civ-level.

| | string
| The name the area takes on when under the control of a LAND_HOLDER. E.g. for the DUKE, [LAND_NAME:a duchy]

| | number (0-100)
| The maximum number of mandates the position can make at once.

| | | The position holder cannot be assigned labors. Currently nonfunctional.

| | | The spouse of the position holder doesn't have to work, either - see above.

| | | This position cannot be appointed from the nobles screen. Intended for militia captains and other squad leaders to reduce clutter. Currently nonfunctional

| | singular:plural
| The name of the position.

| | singular:plural
| If the creature holding the position is male, this is the position's name. E.g. for MONARCH, [NAME_MALE:king:kings]

| | singular:plural
| If the creature holding the position is female, this is the position's name. E.g. for MONARCH, [NAME_FEMALE:queen:queens]

| | - number/AS_NEEDED
| How many of the position there should be. If the [SITE] token exists, this is per site, otherwise this is per civilisation.  AS_NEEDED applies only to positions involved with the military command chain; this is used to allow armies to expand to whatever size they need to be. Non-military positions with NUMBER:AS_NEEDED will not be appointed.

| | number (0-30000)
| How important the position is in society; a lower number is more important and displayed higher in the Nobles menu. For MONARCH it's 1, for MILITIA_CAPTAIN it's 200.

| | | The position holder will not be held accountable for his or her crimes. Currently nonfunctional.

| | | The position holder can give quests in Adventure mode. Functionality in 0.31.13 and later is uncertain.

| | CREATURE_CLASS Token
| Creatures of the specified class cannot be appointed to this position.

| | CREATURE:CASTE
| Restricts position holders by CREATURE type.

| | position
| This position is absorbed by another down the line. For example, expedition leader is [REPLACED_BY:MAYOR].

| | number (0-1000000)
| The position holder requires a bedroom with at least this value.

| | number (0-100)
| The position holder requires at least this many boxes.

| | number (0-100)
| The position holder requires at least this many cabinets.

| | number (0-1000000)
| The position holder requires a dining room with at least this value.

| | number (0-1000000)
| The position holder requires an office with at least this value.

| | number (0-100)
| The position holder requires at least this many weapon racks.

| | number (0-100)
| The position holder requires at least this many armour stands.

| | number (0-1000000)
| The position holder requires a tomb with at least this value.

| | | Does not have anything directly to do with markets.  It means that in minor sites (such as hillocks) the position will not appear, while in major sites (such as dwarf fortresses) it will.

| | number
| The position requires the population to be at least this number before it becomes available, or before the position holder will move in.

| | responsibility
| The position holder does a thing. See the table below for suitable arguments.

| | | If there is a special location set aside for rulers, such as a human castle/mead hall, the position holder will always be found at that particular location. Does nothing for dwarven nobles, because at present, dwarves have no such special locations. 

| | | Every site government will have the defined number of this position instead of the whole civilization; provided that other criteria (if any) are met. Unless LAND_HOLDER is present instead, the defined number of the position will be created only for the civilization as a whole. 

| | | The position holder will get upset if someone with a higher PRECEDENCE holds quarters with a greater value than their own.

| | | The civilization will inter the corpse of the position holder in a special grave, either in catacombs or in monuments. If that grave is disturbed, the position holder can return as a mummy. 

| | singular:plural
| The name of the position holder's spouse.

| | singular:plural
| If the spouse of the creature holding the position is female, this is the spouse's position name.

| | singular:plural
| If the spouse of the creature holding the position is male, this is the spouse's position name.

| | number:singular:plural
| The position holder is authorized to form a military squad, led by themselves using the leader and military tactics skills. The number denotes the maximum headcount. The noun used to describe the subordinates (e.g. royal guard) is used in adventure mode for the adventurer.  

| | - BY_HEIR / BY_POSITION:position
| How a new position holder is chosen. A single position can have multiple BY_POSITION tokens.

1. Responsibilities

**Argument
**Description

| | Found on bookkeeper. Position will use record keeper skill to keep track of stocks.

| | | | Found on elven ranger captain and human warrior. Effect unknown.

| | Found on champion. Citizens get a special thought for "talking to a pillar of society" when speaking to this noble.

| | | | Currently unused - was originally assigned to the tax collector.

| | | | Currently unused - was originally assigned to the arsenal dwarf.

| | Currently unused - was originally assigned to the Royal Guards (squad members beneath the Hammerer).

| | Found on dungeon master and princess and uses the schemer skill.

| | Found on outpost liaison. Position travels with the caravan and uses social skills to make trade agreements with any settlements that it visits, provided they are domestic, report the news and promote LAND_HOLDER positions. Also reports recent news. Presumably has no effect at site level. Crucially, it does not visit foreign settlements, but the civ-level TRADE position does the exact same thing in its position.

| | Found on hammerer. Position executes death penalty judgements with a weapon of the appropriate skill.

| | | | | | Found on chief medical dwarf. Position will use diagnostician skill to enable the -menu health screen.

| | | | Found on sheriff/captain of the guard. Position and its subordinates are in charge of punishing criminals. A [SITE] position holding this responsibility plus the SQUAD token (or allowing the entity to have a SITE_VARIABLE_POSITION with this responsibility) is required for an adventurer from a given civilization to start as a hearthperson, fortress guard, etc.

| | Found on monarch/landholders. Will be referred to as the leader of the site in adventure mode and they may be informed as to the site being the capital city for civ-level positions.

| | | | | | | | | | Position will make a 'social call' to an established foreign settlement, complimenting or insulting them depending on relations and reporting the news.  

| | Found on diplomat. Position negotiates peace treaties in order to end wars.

| | Found on diplomat. Position negotiates special agreements, such as tree cutting quotas.

| | Found on dungeon master.

| | | | | | | | Found on manager. Position enables the use of workshop profiles and uses the organizer skill to process work orders entered in the job manager after the fortress population reaches 20.

| | Found on expedition leader/mayor. Position uses the various social skills to hold meetings with unhappy citizens and try to pacify them with happy thoughts. In adventure mode, [SITE] positions with this responsibility handle petitions to make the player a performer for the local government.

| | Found on monarch/landholder/leaders. Character is in charge of going to war and making peace for the government they work for. Without a position with this responsibility at civ level the civilization will not be able to make peace and its sites will wage war on each other constantly, and as a result, all viable civilizations must have one leader with this tag at civ level. This appears not to be a problem for kobolds, presumably due to either the SKULKING or the UTTERANCES tokens. If no position has this responsibility in fortress mode, players are unable to start missions.

| | Found on general/militia commander. During worldgen, position will go on expeditions to tame exotic creatures. Means that they will command the armies of their site or civilization. Issues the orders for the teams conducting raids or other operations away from the fortress.

| | | | Found on elven ranger captain. Effect unknown.

| | | | Found on monarch/landholder/leaders. Position uses the various social skills to hold meetings with incoming diplomats and liaisons.

| | Found on elven druid and uses social skills. Position informs you about worship cults

| | Currently unused - was originally assigned to the arsenal dwarf.

| | Position will tame animals with the  token. Currently unused - was originally assigned to the dungeon master.

| | Found on broker. Position will use Appraisal skill to display value estimates and the various Social skills to trade at the depot. When applied to other civilizations, this position will arrive with the caravan to make trade agreements (like the Human Guild Representative from older versions) and behaves otherwise like the civ's own ESTABLISH_COLONY_TRADE_AGREEMENTS position holder.

| | Currently unused - was originally assigned to the arsenal dwarf.

1. Related tokens
The following two ENTITY tokens are not actually position tokens, but bear mentioning on this page because they can modify the way that a civilization's positions behave:

**Token
**Arguments
**Description

| | - landholder tier
- population
- wealth exported
- created wealth
| Defines the requirements for the noble ruler promotions. The tier numbers determine which position is used.

| | Position responsibility or ALL
| Allows a responsibility to be taken up by a dynamically generated position (such as Law-maker).

1. Why won't my positions appear?
The way DF determines what positions will actually *appear* in your fortress is somewhat counter-intuitive and fairly limiting. This guide should help you understand what you can do to actually get your positions working properly.

There are five tokens governing which positions appear in your fortress - LAND_HOLDER, REQUIRES_POPULATION, APPOINTED_BY, ELECTED, and REPLACED_BY. The first two determine when your fortress is eligible for a new position, the next two determine how a new position for which your fortress is eligible can be added, and the fifth allows you to clear up obsolete positions. Unfortunately, they also interact in some strange ways that makes creating interesting position structures difficult.

When you start a new fortress, DF compiles a list of your initial positions. To do this, it looks at the requirements for each position - any position whose only requirement is less than seven dwarves (either because they have no requirement tokens, or because their only requirement tokens are [REQUIRES_POPULATION: =< 7] or [LAND_HOLDER:some trigger whose only requirement is some number of dwarves equal to or less than 7]). Most importantly, *any* position whose only requirement is a LAND_HOLDER requirement, regardless of what the trigger for that requirement is, will be added if another eligible starting position is REPLACED_BY it. **A non-LAND_HOLDER position that is REPLACED_BY a LAND_HOLDER position will never appear.** With this list compiled, the game culls all positions that are REPLACED_BY another eligible position, and then culls all positions that have the APPOINTED_BY token. **You may not embark with any appointed positions.** Any remaining positions are then filled by a dwarf chosen at random.

    - Positions do not automatically appear when you reach their requirements.** For example, if you remove the ELECTED token from the Mayor, then the Mayor will never appear, even once you reach their required number of dwarves. **For a position that does not appear at embark to appear in your fortress, it must be APPOINTED_BY another position or ELECTED.**

Naturally, this is more complicated than it looks. **APPOINTED_BY positions must be appointed by another position already in your fortress, or a civ-level position. Only LAND_HOLDER positions may be appointed by civ-level positions.** LAND_HOLDER positions that are APPOINTED_BY civ-level positions are inherently tied to civ-level tokens with the ESTABLISH_COLONY_TRADE_AGREEMENTS responsibility. If a fortress meets the LAND_HOLDER_TRIGGER for a new LAND_HOLDER tier when a caravan leaves, then the next time the outpost liaison or equivalent arrives, they will offer to make you an official colony, which will allow you to select all positions for that LAND_HOLDER level. **Each time they appear, the outpost liaison will only promote your fortress one tier up the LAND_HOLDER track.** The biggest problem with this system is that you may set your LAND_HOLDER_TRIGGERS such that you are eligible for the first tier of LAND_HOLDER positions at embark. **If you are eligible for the first tier of LAND_HOLDER positions at embark, then all first-tier positions will appear twice - once at embark, and again when the outpost liaison comes to appoint you to the first tier.**

ru:Position token
