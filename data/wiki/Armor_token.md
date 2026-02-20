# Armor token

The tokens for all types of armor on all slots, including shields. Usage column gives information on what types of **armor** the token might be restricted to.

These tokens can only be placed within an ITEM_ARMOR, ITEM_GLOVES, ITEM_SHOES, ITEM_SHIELD, ITEM_HELM, or ITEM_PANTS object definition, most do not function in weapon objects.

1. Tokens

**Token
**Arguments
**Usage
**Description

| | singular:plural
| | What this item will be called in-game.

| | adjective
| All garments and shields
| Appears before the name of the garment's material. E.g. "long cow leather skirt" 

| | value
| | How much material is needed to make the item. Most important with bars. The number of bars required to make the item is the value divided by three.

| | 0 - clothing
1 - ranged
2 - melee
3 - uniform only
| All garments and shields
| Determines the garment's general purpose. Defaults to 1 for shields, 0 for everything else.

 items are claimed and used by civilians as ordinary clothing and are subject to wear.

Ranged fighters will spawn with a set of  gear, while melee fighters use .  helmets and body armor only spawn as part of a civilization's uniform.

Each instance of a civilization chooses a helmet and armor at random, from among non-clothing items they have access to, as their uniform. All soldiers that generate as part of that civilization will use those pieces, and if possible, will layer it with a second piece suitable for their unit type.

In previous versions, the armor levels were known as leather, chain, and plate, respectively.

| | | All garments
| Metal versions of this item count as one  higher, typically used to exclude it from civilians. This tag will not work unless  is explicitly declared: if you leave out , even metal armor will default to level 0.

| | | All garments
| Metal versions of this item will have "chain" added between the material and item name.

| | <phrase> of
| ITEM_ARMORITEM_PANTS
| Changes the plural form of this item to "<phrase of> item". Primarily pertains to the stock screens. Example, "suits of" platemail, "pairs of" trousers, etc. 

| | adjective
| ITEM_ARMORITEM_PANTS
| If the item has no material associated with it (e.g. stockpile menus and trade negotiations), this will be displayed in its place. Used for leather armor.

| | value
| | Defines the item value of the armor. Defaults to 10.

| | value, MAX
| ITEM_GLOVESITEM_SHOESITEM_SHIELD
| Length of gloves or footwear, counted in [LIMB] body parts towards the torso. A value of 1 lets gloves cover the lower arms, a value of 2 stretches a boot all the way over the upper leg and so on. Regardless of the value, none of these items can ever extend to cover the upper or lower body. Shields also have this token, but it only seems to affect weight.

| | value, MAX
| ITEM_ARMOR
| Length of the sleeves, counted in [LIMB] body parts towards the hands. A value of 0 only protects both halves of the torso, 1 extends over the upper arms and so on. Regardless of the value, body armor can never extend to cover the hands or head.

Currently bugged, high values of UBSTEP will result in the item protecting facial features, fingers, and toes, while leaving those parts that it cannot protect unprotected (but still counting them as steps).

| | value or MAX
| ITEM_ARMORITEM_PANTS
| Length of the legs/hem, counted in [LIMB] body parts towards the feet. A value of 0 only covers the lower body, 1 extends over the upper legs and so on. Regardless of the value, body armor or pants can never extend to cover the feet. 

| | value
| ITEM_SHIELD
| Affects the block chance of the shield. Defaults to 10.

| | | All garments
| Clothiers can make this item from all kinds of cloth. If paired with [LEATHER], the item has an equal chance of being either in randomly generated outfits. Further uses of this tag are unknown.

| | | All garments
| Default state in the absence of a [SOFT] token. Actual effects unknown.

| | | All garments
| Item can be made from metal. Overrides [SOFT] and [LEATHER] in randomly generated outfits, if the ARMORLEVEL permits. Civilizations with [WOOD_ARMOR] will make this item out of wood instead.

| | | All garments
| Craftsmen can make this item from bones. Randomly generated outfits don't include bone armor.

| | | All garments
| Craftsmen can make this item from shells. Randomly generated outfits don't include shell armor.

| | | All garments
| Leatherworkers can make this item from leather. If paired with [SOFT], this item has an equal chance of being either in randomly generated outfits.

| | | All garments
| Only one shaped piece of clothing can be worn on a single body slot at a time.

| | | All garments
| Increases the *_STRAIN_AT_YIELD properties of the armor's material to 50000, if lower. This makes the garment flex and give way instead of shattering under force. Strong materials that resist cutting will blunt edged attacks into bone-crushing hits instead.

| | | All garments
| Increases the *_STRAIN_AT_YIELD properties of the armor's material to 50000, but only if the garment is made from metal.

| | | All garments
| Reduces the armor material's SHEAR_YIELD to 20000, SHEAR_FRACTURE to 30000 and increases the *_STRAIN_AT_YIELD properties to 50000, but only if the garment is made from cloth. This makes the item very weak against edged attacks, even if the thread material is normally very strong.

| | value
| All garments
| The item's bulkiness when worn. Aside from the layer limitations, it's a big contributor to the thickness and weight (and therefore price) of the garment. See Armor for more on item sizes and layering. Defaults to 10. 

| | value
| All garments
| The maximum amount of crap that can fit underneath the garment. See Armor for more on item sizes and layering. Defaults to 10.

| | UNDEROVERARMORCOVER
| All garments
| Where the item goes in relation to other clothes. Socks cannot be worn on top of boots! 
The LAYER_PERMIT of the highest layer is used on a given section of the body - you can fit a lot of shirts and other undergarments underneath a robe, but not if you wear a leather jerkin on top of it, and you can still wear a cloak over the whole ensemble. Defaults to UNDER.

| | % value
| All garments
| How often the garment gets in the way of a contaminant or an attack. Armor with a 5% coverage value, for example, will be near useless because 95% of attacks will bypass it completely. Temperature effects and armor thickness are also influenced. Defaults to 100.

ru:Armor token
