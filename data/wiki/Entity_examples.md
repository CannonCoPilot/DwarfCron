# Entity examples

This page was created to aid those looking to create new civilizations. Those familiar with entity design should feel free to add helpful/obscure information to the lists below to help less-experienced members of the community with their entities.

1. Example Animal Person Civilization
The various Animal People (with the exception of those based on creatures with the [AQUATIC] token) already have all the parts they need to join civilized society. They just need to be given an ENTITY that will allow them to create civilizations of their own. The following example creates water-themed otter people civilizations based on the vanilla human civilizations.

Now after this example you might be thinking "*Why not make a generic animal person civilization and stuff all 175+ existing [CREATURE:ANIMAL_MAN] tokens into it?*". This works, but the trick is it works far too well. The number of [CREATURE:X] tags changes the civ's spawn rate, so adding every [CREATURE:ANIMAL_MAN] to one entity will likely cause their civ to spawn so often that it blocks all the elves, humans, goblins, kobolds, and dwarves from spawning and will lead to world gen rejections. To balance the spawn rates for the vanilla civs you would need to add [SELECT_ENTITY:VANILLA_ENTITY_X] followed by the same number (175+) of duplicate [CREATURE:VANILLA_CREATURE_X] tokens for each vanilla civ. See entity placement for more info on this.

1. General Tips
