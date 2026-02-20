# DF2014:Ethic

- Ethic** tags are used in the entity raw files to determine how different civilizations feel about various issues. Relationships between civilizations are based on their ethic responses in relation to each other; similar ethics result in friendship, while conflicting ethics result in animosity. Strongly conflicting ethics often trigger wars during world generation. (In practice, this generally causes elves to declare war on everybody else over killing plants and making trophies, and everybody else to declare war on the elves over the devouring of sapient beings.)

Some ethics also affect fortress mode features, such as justice, or trading. In adventurer mode, ethics can affect the level of conflict (lethal, or no quarter). During world generation, ethics also affect how the entity treats its kills, such as devouring them or making trophies out of them.

1. Example
In the raw files for entities, ethics appear as follows:
 [ETHIC:LYING:PERSONAL_MATTER]

This means that the entity will treat lying as a personal matter. More technically, the value of its LYING ethic is set to PERSONAL_MATTER.

1. Ethic types

**Token
**Extra Information

| | The result of a tantrumming citizen attacking another in fortress mode. Other effects unknown.

| | This determines if the race will sometimes devour defeated enemy combatants.

| | This includes whether or not a race is willing to butcher other sapients. Note that, due to a bug, player forts will never butcher intelligent creatures in fortress mode (they are still willing to eat their meat though, should they have access to it). However this works as intended in adventure mode, worldgen, and offsite (caravans will deliver products made from sentients, etc.)

| | A response between MISGUIDED and UNTHINKABLE (see below) causes the entity to refuse animal products in trade &mdash; namely, materials with [IMPLIES_ANIMAL_KILL]. Animal products sold by caravans will be marked as "grown", which means kosher for their ethics, for example grown leather.

| | If REQUIRED, all lethal combat with an enemy who is an enemy of the whole entity will put the creature in no quarter mode.

| | If REQUIRED, all lethal combat with an enemy in the same entity will put the creature in no quarter mode.  Determines whether and how often entity members will be murdered. 

| | If REQUIRED, all lethal combat with an enemy who is neutral with the entity will put the creature in no quarter mode, and the creature will also demand that strangers identify themselves.

| | This includes a race's position towards wood &mdash; a response between MISGUIDED and UNTHINKABLE (see below) causes the entity to refuse wooden objects (except for "grown" wooden objects) in trade, and also prohibits them from bringing caravan wagons. Caravans will sell grown wood objects (if the civ has WOOD_PREF) and even grown non-wood objects but that elves refuse to buy (if the civ uses misc processed wood products). 

| | Giving false witness reports?

| | This determines whether animal kills will lead to characters with trophies. Historical figures can arrive at your fortress with leather, horn, ivory, tooth, hair, bone or nail jewellery from slain non-sapients, and fortress citizens may put on crafts made from their kills as well. 

| | This determines whether kills of one's own race will lead to characters with trophies. Historical figures can arrive at your fortress with leather, tooth, hair, bone or nail jewellery from their race, even INTELLIGENT. Example: goblin with -goblin tooth ring-.

| | This determines whether kills of other sapients will lead to characters with trophies. As previous, but regarding other races, including INTELLIGENT.

| | The result of a citizen violating noble mandates in fortress mode. Other effects unknown.

| | Civilization will enslave defeated enemies and bring them back to their site. Also affects whether you may trade caged sapient beings to merchants. Aside from diplomacy, higher/lower values don't seem to affect anything beyond if a civilization is willing to take slaves at all. 

| | This determines whether the civilization will try to steal goods and how it will respond when stolen from.

| | | | Civilization will sometimes execute non-combatants after defeating enemy defenders.

| | | | | | Protects position-holders from being murdered like everyone else – the reason that demon overlords of goblins manage to live for centuries, despite goblins' regard of killing each other as being a personal matter.  

| | Ignoring burrow restrictions 

| | The result of a tantruming citizen breaking furniture in fortress mode. Other effects unknown.

1. Ethic values
As used internally (see below), roughly in order of acceptability:

**Num !! Token

| 0 || 

| 1 || 

| 2 || 

| 3 || 

| 4 || 

| 5 || 

| 6 || 

| 7 || 

| 8 || 

| 9 || 

| 10 || 

| 11 || 

| 12 || 

| 13 || 

| 14 || 

| 15 || 

| 16 || 

1. Ethic value numbers in relation to each other
The following table describes how entities respond to other cultures, with the observer on the vertical axis and their target on the horizontal axis.
If an entity's accumulated animosity towards another passes a certain threshold (determined by the ruler's personality) then it will run a risk-assessment check. If passed, this will lead to a declaration of war.

In general, entities react much more strongly to actions that violate *their* taboos than to the outlawing of their customs in other civilisations.
For example, Civ A finds slavery Acceptable, but Civ B considers it a Capital Offence.
- Civ A will consider Civ B most unreasonable (&minus;5) for executing people over such a non-issue.
- Civ B will be shocked and disgusted (&minus;15) that Civ A engages in such a debased activity.
- The end result is mutual negativity. However, Civ B is 3&times; *more* offended, and much more likely to go to war over the issue &mdash; assuming, of course, they think they have a chance of winning.

**rowspan=2 colspan=2 | &nbsp;
**colspan=16  | TARGET

**width=6%| Accept. ||width=6%| Personal ||width=6%| Reperc. ||width=6%| Good ||width=6%| Extreme ||width=6%| Self-Def. ||width=6%| Sanct. ||width=6%| Misguid. ||width=6%| Shun ||width=6%| Appall. ||width=6%| Reprim. ||width=6%| Serious ||width=6%| Exile ||width=6%| Capital ||width=6%| Unthink. ||width=6%| Req.

**rowspan=16 |  &nbsp;&nbsp;&nbsp;&nbsp;
**Acceptable ||  ||  ||  || 0 || 0 || 0 || 0 ||  ||  ||  ||  ||  ||  ||  ||  || 

**Personal ||  ||  ||  || 0 || 0 || 0 || 0 ||  ||  ||  ||  ||  ||  ||  ||  || 

**No Reperc. ||  ||  ||  || 0 || 0 || 0 || 0 ||  ||  ||  ||  ||  ||  ||  ||  || 

**Good Reas. || 0 || 0 || 0 ||  ||  || 0 || 0 || 0 ||  ||  ||  ||  ||  ||  ||  || 0

**Extreme Rs. ||  ||  || 0 ||  ||  || 0 || 0 || 0 ||  ||  ||  ||  ||  ||  ||  || 

**Self-Defence ||  ||  ||  || 0 ||  ||  || 0 || 0 || 0 ||  ||  ||  ||  ||  ||  || 

**Sanctioned ||  ||  ||  || 0 ||  || 0 ||  || 0 || 0 ||  ||  ||  ||  ||  ||  || 

**Misguided ||  ||  || 0 || 0 || 0 || 0 || 0 ||  ||  ||  ||  || 0 || 0 ||  ||  || 

**Shun ||  ||  || 0 || 0 || 0 || 0 || 0 ||  ||  ||  ||  || 0 || 0 ||  ||  || 

**Appalling ||  ||  ||  ||  ||  ||  ||  ||  ||  ||  ||  ||  ||  || 0 ||  || 

**Reprimand ||  ||  ||  ||  ||  ||  ||  ||  ||  ||  ||  ||  ||  || 0 ||  || 

**Serious ||  ||  ||  ||  ||  ||  ||  || 0 ||  ||  || 0 ||  ||  ||  ||  || 

**Exile ||  ||  ||  ||  ||  ||  ||  || 0 ||  ||  || 0 ||  ||  ||  ||  || 

**Capital ||  ||  ||  ||  ||  ||  ||  || 0 || 0 ||  || 0 ||  ||  ||  ||  || 

**Unthinkable ||  ||  ||  ||  ||  ||  ||  || 0 ||  ||  || 0 ||  ||  ||  ||  || 

**Required ||  ||  ||  || 0 || 0 || 0 || 0 ||  ||  ||  ||  ||  ||  ||  ||  || 

All above info was collected and interpreted from the data given by Toady himself at .

1. Ethics of vanilla civilizations
Animal people currently have the same ethics as kobolds.

**Issue
**Mountain(dwarf)
**Forest(elf)
**Plains(human)
**Evil(goblin)
**Skulking(kobold)

| Killing member of the same entity
| Capital punishment
| Justified with extreme reason
| Justified with good reason
| Personal matter
| Exile

| Killing neutral sapient
| Only if sanctioned
| Acceptable
| Justified if no repercussions
| Required
| Required

| Killing enemy
| Acceptable
| Acceptable
| Acceptable
| Required
| Required

| Killing animal
| Acceptable
| Justified in self-defence
| Acceptable
| Acceptable
| Acceptable

| Killing plant
| Acceptable
| Unthinkable
| Acceptable
| Acceptable
| Acceptable

| Torture as example
| Unthinkable
| Acceptable
| Acceptable
| Acceptable
| Unthinkable

| Torture for information
| Unthinkable
| Misguided
| Acceptable
| Acceptable
| N/A

| Torture for fun
| Unthinkable
| Unthinkable
| Appalling
| Acceptable
| Acceptable

| Torture of animals
| Unthinkable
| Unthinkable
| Shunned
| Acceptable
| Unthinkable

| Treason
| Capital punishment
| Exile
| Capital punishment
| Capital punishment
| Unthinkable

| Oathbreaking
| Capital punishment
| Exile
| Capital punishment
| Personal matter
| N/A

| Lying
| Personal matter
| Exile
| Personal matter
| Personal matter
| N/A

| Vandalism
| Serious punishment
| Reprimand
| Serious punishment
| Personal matter
| N/A

| Trespassing
| Serious punishment
| Reprimand
| Serious punishment
| Personal matter
| N/A

| Theft
| Serious punishment
| Reprimand
| Serious punishment
| Personal matter
| N/A

| Assault
| Serious punishment
| Exile
| Serious punishment
| Personal matter
| Personal matter

| Slavery
| Capital punishment
| Exile
| Acceptable
| Personal matter
| Unthinkable

| Eating sapients
| Unthinkable
| Unthinkable
| Unthinkable
| Personal matter
| Unthinkable

| Eating sapients (that have been killed in battle)
| Unthinkable
| Acceptable
| Unthinkable
| Personal matter
| Unthinkable

| Making a trophy from a corpse of the same race
| Appalling
| Unthinkable
| Acceptable
| Acceptable
| Unthinkable

| Making a trophy from a corpse of another sapient race
| Shunned
| Unthinkable
| Acceptable
| Acceptable
| Unthinkable

| Making a trophy from the corpse of an animal
| Acceptable
| Unthinkable
| Acceptable
| Acceptable
| Unthinkable

ru:Ethic
