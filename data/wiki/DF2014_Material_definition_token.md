# DF2014:Material definition token

The following tokens can be used in material definitions (whether for inorganics or those within plants and creatures) as well as in material templates.

__TOC__

1. Material properties

**Token
**Arguments
**Description

| | - <template name>
| Imports the properties of the specified preexisting material template. 

| | - <prefix> or NONE
| Applies a prefix to all items made from the material. For PLANT and CREATURE materials, this defaults to the plant/creature name. **Not permitted in material template definitions.**

| | - <name>
| Overrides the name of BOULDER items (i.e. mined-out stones) made of the material (used for native copper/silver/gold/platinum to make them be called "nuggets" instead of "boulders").

| | - <name>
- <plural>
- OVERWRITE_SOLID (optional)
| Used to indicate that said material is a gemstone - when tiles are mined out, rough gems will be yielded instead of boulders. Plural can be "STP" to automatically append an "s" to the singular form, and OVERWRITE_SOLID will override the relevant STATE_NAME and STATE_ADJ values.

| | - <type>
| Specifies what the material should be treated as when drinking water contaminated by it, for generating unhappy thoughts. Valid values are BLOOD, SLIME, VOMIT, ICHOR, PUS, GOO, GRIME, and FILTH.

| | - <color token>
| Allows the material to be used as dye, and defines color of dyed items.

| | - <tile value or character>
| Specifies the tile that will be used to represent unmined tiles made of this material. Generally only used with stones. Defaults to 219 ('█').

| | - <tile value or character>
| Specifies the tile that will be used to represent BOULDER items made of this material. Generally only used with stones. Defaults to 7 ('•').

| | - <foreground color>
- <background color>
- <foreground brightness>
| The on-screen color of the material. Uses a standard 3-digit color token. Equivalent to [TILE_COLOR:a:b:c], [BUILD_COLOR:b:a:X] (X = 1 if 'a' equals 'b', 0 otherwise), and [BASIC_COLOR:a:c]

| | - <foreground color>
- <background color>
- <foreground brightness>
| The color of objects made of this material which use both the foreground and background color: doors, floodgates, hatch covers, bins, barrels, and cages. Defaults to 7:7:1 (white).

| | - <foreground color>
- <background color>
- <foreground brightness>
| The color of unmined tiles containing this material (for stone and soil), as well as engravings in this material. Defaults to 7:7:1 (white).

| | - <foreground color>
- <foreground brightness>
| The color of objects made of this material which use only the foreground color, including workshops, floors and boulders, and smoothed walls. Defaults to 7:1 (white).

| | - <material state>
- <color token>
| Determines the color of the material at the specified state. See below for a list of valid material states. Color comes from descriptor_color_standard.txt. The nearest color value is used to display contaminants and body parts made of this material. Example:
[STATE_COLOR:ALL_SOLID:GRAY]

| | - <material state>
- <name>
| Determines the name of the material at the specified state, as displayed in-game.
[STATE_NAME:ALL_SOLID:stone]

| | - <material state>
- <adjective>
| Like STATE_NAME, but used in different situations. Equipment made from the material uses the state adjective and not the state name.

| | - <material state>
- <name>
- <adjective>
| Sets both STATE_NAME and STATE_ADJ at the same time.

| | - <value>
| The material's tendency to absorb liquids. Containers made of materials with nonzero absorption cannot hold liquids unless they have been glazed. Defaults to 0.

| | - <value>
| Specifies how hard of an impact (in kilopascals) the material can withstand before it will start deforming permanently. Used for blunt-force combat. Defaults to 10000.

| | - <value>
| Specifies how hard of an impact the material can withstand before it will fail entirely. Used for blunt-force combat. Defaults to 10000.

| or 
| - <value>
| Specifies how much the material will have given (in parts-per-100000) when the yield point is reached. Used for blunt-force combat. Defaults to 0. Apparently affects in combat whether the corresponding tissue is bruised (value >= 50000), torn (value between 25000 and 49999), or fractured (value <= 24999)

| | - <value>
| Specifies how hard the material can be compressed before it will start deforming permanently. Determines a tissue's resistance to pinching and response to strangulation. Defaults to 10000.

| | - <value>
| Specifies how hard the material can be compressed before it will fail entirely. Determines a tissue's resistance to pinching and response to strangulation. Defaults to 10000.

| or 
| - <value>
| Specifies how much the material will have given when it has been compressed to its yield point. Determines a tissue's resistance to pinching and response to strangulation. Defaults to 0.

| | - <value>
| Specifies how hard the material can be stretched before it will start deforming permanently. Determines a tissue's resistance to a latching and tearing bite. Defaults to 10000.

| | - <value>
| Specifies how hard the material can be stretched before it will fail entirely. Determines a tissue's resistance to a latching and tearing bite. Defaults to 10000.

| or 
| - <value>
| Specifies how much the material will have given when it is stretched to its yield point. Determines a tissue's resistance to a latching and tearing bite. Defaults to 0.

| | - <value>
| Specifies how hard the material can be twisted before it will start deforming permanently. Used for latching and shaking with a blunt attack (no default creature has such an attack, but they can be modded in).  Defaults to 10000.

| | - <value>
| Specifies how hard the material can be twisted before it will fail entirely. Used for latching and shaking with a blunt attack (no default creature has such an attack, but they can be modded in).  Defaults to 10000.

| or 
| - <value>
| Specifies how much the material will have given when it is twisted to its yield point. Used for latching and shaking with a blunt attack (no default creature has such an attack, but they can be modded in).  Defaults to 0.

| | - <value>
| Specifies how hard the material can be sheared before it will start deforming permanently. Used for cutting calculations. Defaults to 10000.

| | - <value>
| Specifies how hard the material can be sheared before it will fail entirely. Used for cutting calculations. Defaults to 10000.

| or 
| - <value>
| Specifies how much the material will have given when sheared to its yield point. Used for cutting calculations. Defaults to 0.

| | - <value>
| Specifies how hard the material can be bent before it will start deforming permanently. Determines a tissue's resistance to being mangled with a joint lock. Defaults to 10000.

| | - <value>
| Specifies how hard the material can be bent before it will fail entirely. Determines a tissue's resistance to being mangled with a joint lock. Defaults to 10000.

| or 
| - <value>
| Specifies how much the material will have given when bent to its yield point. Determines a tissue's resistance to being mangled with a joint lock. Defaults to 0.

| | - <value>
| How sharp the material is. Used in cutting calculations. Does not allow an inferior metal to penetrate superior armor. Applying a value of at least 10000 to a stone will allow weapons to be made from that stone. Defaults to 10000.

| | - <value>
| Value modifier for the material. Defaults to 1. This number can be made negative by placing a "-" in front, resulting in things that you are paid to buy and must pay to sell.

| | - <value>
| Multiplies the value of the material. **Not permitted in material template definitions.**

| | - <specific heat capacity>
| Rate at which the material heats up or cools down (in joules/kilogram-kelvin). If set to NONE, the temperature will be fixed at its initial value. See Temperature for more information. Defaults to NONE.

| | - <temperature>
| Temperature above which the material takes damage from heat. May be set to NONE. If the material has an ignite point but no heatdam point, it will burn for a very long time (9 months and 16.8 days). Defaults to NONE.

| | - <temperature>
| Temperature below which the material takes damage from cold. Defaults to NONE.

| | - <temperature>
| Temperature at which the material will catch fire. Defaults to NONE.

| | - <temperature>
| Temperature at which the material melts. Defaults to NONE.

| | - <temperature>
| Temperature at which the material boils. Defaults to NONE.

| | - <temperature>
| Items composed of this material will initially have this temperature. Used in conjunction with `[SPEC_HEAT:NONE]` to make material's temperature fixed at the specified value. Defaults to NONE.

| | - <temperature>
| Changes a material's HEATDAM_POINT, but only if it was not set to NONE. **Not permitted in material template definitions.**

| | - <temperature>
| Changes a material's COLDDAM_POINT, but only if it was not set to NONE. **Not permitted in material template definitions.**

| | - <temperature>
| Changes a material's IGNITE_POINT, but only if it was not set to NONE. **Not permitted in material template definitions.**

| | - <temperature>
| Changes a material's MELTING_POINT, but only if it was not set to NONE. **Not permitted in material template definitions.**

| | - <temperature>
| Changes a material's BOILING_POINT, but only if it was not set to NONE. **Not permitted in material template definitions.**

| | - <temperature>
| Changes a material's MAT_FIXED_TEMP, but only if it was not set to NONE. **Not permitted in material template definitions.**

| | - <density>
| Specifies the density (in kilograms per cubic meter) of the material when in solid form. Also affects combat calculations; affects blunt-force damage and ability of edged weapons to pierce tissue layers. Defaults to NONE.

| | - <density>
| Specifies the density of the material when in liquid form. Defaults to NONE.

| | - <value>
| Supposedly not used. Theoretically, should determine density (at given pressure) in gas state, on which in turn would depend (together with weight of vaporized material) on the volume covered by spreading vapors. Defaults to NONE.

| | * BARREL or FLASK
| Specifies the type of container used to store the material. Used in conjunction with the [EXTRACT_BARREL], [EXTRACT_VIAL], or [EXTRACT_STILL_VIAL] plant tokens. Defaults to BARREL.

| | - <item token>
| Specifies the item type used for butchering results made of this material. Stock raws use GLOB:NONE for fat and MEAT:NONE for other meat materials.

| | - <prefix>
- <name>
- <adjective>
| When a creature is butchered, meat yielded from organs made from this material will be named via this token. If this token is not specified, meat objects will be called "chops" instead.

| | - <singular>
- <plural>
| Specifies the name of blocks made from this material.

| | | The material forms "wafers" instead of "bars".

| | - <reaction reference>
- <material token>
| Used with reaction raws to associate a reagent material with a product material. The first argument is used by HAS_MATERIAL_REACTION_PRODUCT and GET_MATERIAL_FROM_REAGENT in reaction raws. The remainder is a material reference, generally LOCAL_CREATURE_MAT:SUBTYPE or LOCAL_PLANT_MAT:SUBTYPE or INORGANIC:STONETYPE.
[MATERIAL_REACTION_PRODUCT:TAN_MAT:LOCAL_CREATURE_MAT:LEATHER]

| | - <item reference>
- <item token>
- <material token>
| Used with reaction raws to associate a reagent material with a complete item.  The first argument is used by HAS_ITEM_REACTION_PRODUCT and GET_ITEM_DATA_FROM_REAGENT in reaction raws.  The rest refers to the type of item, then its material.
[ITEM_REACTION_PRODUCT:BAG_ITEM:PLANT_GROWTH:LEAVES:LOCAL_PLANT_MAT:LEAF]

| | - <reaction class name>
| Used to classify all items made of the material, so that reactions can use them as generic reagents.
In default raws, the following are used:
- FAT, TALLOW, SOAP, PARCHMENT, PAPER_PLANT, PAPER_SLURRY, MILK, CHEESE, WAX
- CAN_GLAZE - items made from this material can be glazed.
- FLUX - can be used as flux in pig iron and steel making.
- GYPSUM - can be processed into gypsum plaster.
- CALCIUM_CARBONATE - can be used in production of quicklime.

| | - <inorganic material name e.g. LEAD>
- <value>
| Makes BOULDER acceptable as a reagent in reactions that require "METAL_ORE:MATERIAL_NAME", as well as smelting directly into metal bars. Places the material under "Metal Ores" in Stone stockpiles. The specified value determines the probability for this product (see Tetrahedrite or Galena for details).

| | - <inorganic material name e.g. RAW_ADAMANTINE>
- <value>
| Makes BOULDER items made of the material acceptable for strand extraction into threads; see also STOCKPILE_THREAD_METAL. Value presumably determines the probability of this product extracted.

| | - <material token>
| Allows the material to be used to make casts.

| | - <value>
| Soap has [SOAP_LEVEL:2]. Effects unknown. Defaults to 0.

| | | Begins defining a syndrome applied by the material. Multiple syndromes can be specified. See Syndrome token.

1. Material states

The following is a list of valid material states:

| **SOLID**

| **LIQUID**

| **GAS**

| **POWDER** (or **SOLID_POWDER**)

| **PASTE** (or **SOLID_PASTE**)

| **PRESSED** (or **SOLID_PRESSED**)

The following can be specified within tokens such as STATE_NAME, STATE_NAME_ADJ and STATE_ADJ to make them apply to several of the above material states simultaneously:

**Value
**Description

| **ALL**
| Denotes all possible material states.

| **ALL_SOLID**
| Denotes 'SOLID', 'POWDER', 'PASTE' and 'PRESSED'.

1. Material usage tokens

**Token
**Arguments
**Description

| | | Lets the game know that an animal was likely killed in the production of this item. Entities opposed to killing animals (which currently does **not** include Elves) will refuse to accept these items in trade.

| | | Classifies the material as plant-based alcohol, allowing its storage in food stockpiles under "Drink (Plant)".

| | | Classifies the material as animal-based alcohol, allowing its storage in food stockpiles under "Drink (Animal)".

| | | Classifies the material as generic alcohol. Implied by both ALCOHOL_PLANT and ALCOHOL_CREATURE. Exact behavior unknown, possibly vestigial.

| | | Classifies the material as plant-based cheese,  allowing its storage in food stockpiles under "Cheese (Plant)".

| | | Classifies the material as animal-based cheese, allowing its storage in food stockpiles under "Cheese (Animal)".

| | | Classifies the material as generic cheese. Implied by both CHEESE_PLANT and CHEESE_CREATURE. Exact behavior unknown, possibly vestigial.

| | | Classifies the material as plant powder, allowing its storage in food stockpiles under "Milled Plant".

| | | Classifies the material as creature powder, allowing its storage in food stockpiles under "Bone Meal". Unlike milled plants, such as sugar and flour, "Bone Meal" barrels or pots may not contain bags. Custom reactions using this product better use buckets or jugs instead.

| | | Classifies the material as generic powder. Implied by both POWDER_MISC_PLANT and POWDER_MISC_CREATURE. Exact behavior unknown, possibly vestigial.

| or 
| | Permits globs of the material in solid form to be stored in food stockpiles under "Fat" - without it, dwarves will come by and "clean" the items, destroying them (unless [DO_NOT_CLEAN_GLOB] is also included).

| | | Classifies the material as milled paste, allowing its storage in food stockpiles under "Paste".

| | | Classifies the material as pressed goods, allowing its storage in food stockpiles under "Pressed Material".

| | | Classifies the material as a plant growth (e.g. fruits, leaves), allowing its storage in food stockpiles under Plant Growth/Fruit.

| | | Classifies the material as a plant extract, allowing its storage in food stockpiles under "Extract (Plant)".

| | | Classifies the material as a creature extract, allowing its storage in food stockpiles under "Extract (Animal)".

| | | Classifies the material as a miscellaneous liquid, allowing its storage in food stockpiles under "Misc. Liquid" along with lye.

| | | Classifies the material as a generic liquid. Implied by LIQUID_MISC_PLANT, LIQUID_MISC_CREATURE, and LIQUID_MISC_OTHER. Exact behavior unknown, possibly vestigial.

| | | Classifies the material as a plant, allowing its storage in food stockpiles under "Plants".

| | | Classifies the material as a plant seed, allowing its storage in food stockpiles under "Seeds".

| | | Classifies the material as bone, allowing its use for bone carvers and restriction from stockpiles by material.

| | | Classifies the material as wood, allowing its use for carpenters and storage in wood stockpiles. Entities opposed to killing plants (i.e. Elves) will refuse to accept these items in trade.

| | | Classifies the material as plant fiber, allowing its use for clothiers and storage in cloth stockpiles under "Thread (Plant)" and "Cloth (Plant)".

| | | Classifies the material as tooth, allowing its use for bone carvers and restriction from stockpiles by material.

| | | Classifies the material as horn, allowing its use for bone carvers and restriction from stockpiles by material.

| | | Classifies the material as pearl, allowing its use for bone carvers and restriction from stockpiles by material.

| | | Classifies the material as shell, allowing its use for bone carvers and restriction from stockpiles by material.

| | | Classifies the material as leather, allowing its use for leatherworkers and storage in leather stockpiles.

| | | Classifies the material as silk, allowing its use for clothiers and storage in cloth stockpiles under "Thread (Silk)" and "Cloth (Silk)".

| | | Classifies the material as soap, allowing it to be used as a bath detergent and stored in bar/block stockpiles under "Bars: Other Materials".

| | | Material generates miasma when it rots.

| | | Classifies the material as edible meat.

| | | Material will rot if not stockpiled appropriately. Currently only affects food and refuse, other items made of this material will not rot.

| | | Tells the game to classify contaminants of this material as being "blood" in Adventurer mode tile descriptions ("Here we have a Dwarf in a slurry of blood.").

| | | Tells the game to classify contaminants of this material as being "ichor".

| | | Tells the game to classify contaminants of this material as being "goo".

| | | Tells the game to classify contaminants of this material as being "slime".

| | | Tells the game to classify contaminants of this material as being "pus".

| | | Tells the game to classify contaminants of this material as being "sweat".

| | | Tells the game to classify contaminants of this material as being "tears".

| | | Tells the game to classify contaminants of this material as being "spit".

| | | Contaminants composed of this material evaporate over time, slowly disappearing from the map. Used internally by water.

| | | Used for materials which cause syndromes, causes it to enter the creature's blood instead of simply spattering on the surface.

| | | Can be eaten by vermin.

| | | Can be eaten raw.

| | | Can be cooked and then eaten.

| | | Prevents globs made of this material from being cleaned up and destroyed.

| | | Prevents the material from showing up in Stone stockpile settings.

| | | Allows the creation of metal furniture at the metalsmith's forge.

| | | Equivalent to ITEMS_HARD. Given to bone.

| | | Equivalent to ITEMS_HARD. Given to shell.

| | | Equivalent to ITEMS_SOFT. Given to leather.

| | | Random crafts made from this material cannot be made into rings, crowns, scepters or figurines. Given to plant fiber, silk and wool.

| | | Random crafts made from this material include all seven items. Given to stone, wood, bone, shell, chitin, claws, teeth, horns, hooves and beeswax. Hair, pearls and eggshells also have the tag.

| | | Used to define that the material is a stone. Allows its usage in masonry and stonecrafting and storage in stone stockpiles, among other effects.

| | | Used for a stone that cannot be dug into.

| | | Causes containers made of this material to be prefixed with "unglazed" if they have not yet been glazed.

| | | Classifies the material as yarn, allowing its use for clothiers and its storage in cloth stockpiles under "Thread (Yarn)" and "Cloth (Yarn)".

| | | Classifies the material as metal thread, permitting thread and cloth to be stored in cloth stockpiles under "Thread (Metal)" and "Cloth (Metal)".

| | | Defines the material as being metal, allowing it to be used at forges.

| | | Used internally by green glass, clear glass, and crystal glass.

| | | Can be used in the production of crystal glass.

| | | Melee weapons can be made out of this material.

| | | Ranged weapons can be made out of this material.

| | | Anvils can be made out of this material.

| | | Ammunition can be made out of this material.

| | | Picks can be made out of this material.

| | | Armor can be made out of this material.

| | | Used internally by amber and coral. Functionally equivalent to ITEMS_HARD.

| | | Siege engine parts can be made out of this material. Does not appear to work.

| | | Querns and millstones can be made out of this material.

1. Syndrome tokens
Below is a table with some of the tokens you can use when declaring a [SYNDROME] token. For all the tokens you can use, see the Syndrome token page.

**Token
**Arguments
**Description

| {{text_anchor|SYN_NAME 
| - text 
| Defines the name of the syndrome

| | | Syndrome can be contracted by injection (by a creature)

| | | Syndrome can be contracted on contact (e.g. poison dust or liquid)

| | | Syndrome can be contracted by inhalation (e.g. poison vapor or gas)

| | | Syndrome can be contracted by ingestion (when the material is eaten in solid or liquid form)

| | - creature class name
| Adds a class of creatures to those affected, such as CREATURE_CLASS:GENERAL_POISON

| | - creature class name
| Makes the class of creatures immune to the syndrome

| | - creature name
- caste name or ALL
| Adds a specific creature to those affected.

| | - creature name
- caste name or ALL
| Makes the creature immune to the syndrome

| CE_PAINCE_SWELLINGCE_OOZINGCE_BRUISINGCE_BLISTERSCE_NUMBNESSCE_PARALYSISCE_FEVERCE_BLEEDINGCE_COUGH_BLOODCE_VOMIT_BLOODCE_NAUSEACE_UNCONSCIOUSNESSCE_NECROSISCE_IMPAIR_FUNCTIONCE_DROWSINESSCE_DIZZINESS
| - SEV:<value>  (severity, higher is worse)
- PROB:<value(1-100)> (probability)
- RESISTABLE (optional) allows resistance
- SIZE_DILUTES (optional) lessens effect based on size 
Place affected:
- LOCALIZED (optional)
- VASCULAR_ONLY (optional)
- MUSCULAR_ONLY (optional)
- BP:BY_CATEGORY:category:tissue (optional)
- BP:BY_TYPE:type:tissue (optional)
- BP:BY_TOKEN:token:tissue (optional)
Timeline:
- Start:effect start time
- Peak:effect peak time
- End:effect end time
| Specifies the way that a syndrome affects a creature -- more detail can be found on the Syndromes page

1. See also
- Inorganic material definition token
- Syndrome
- Hardcoded material

ru:Material definition token
