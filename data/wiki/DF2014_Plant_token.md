# DF2014:Plant token

The `[OBJECT:PLANT]` token defines the properties of plants; this being a full list of all known plant tokens.

__TOC__

1. Basic tokens
These tokens are specified for all plants and define their most basic characteristics.

**width="20%" | Token
**width="20%" | Arguments
**width="60%" | Description

| | - name
| The singular form of the plant's name as seen in-game.

| | - name
| The plural form of the plant's name as seen in-game.

| | - adjective
| The word or phrase used to describe items made from this plant.

| | - name
| Sets the NAME, NAME_PLURAL, and ADJ to the specified string.

| | - reason
| What dwarves can like this object for (e.g. "Urist likes plump helmets for their rounded tops.")

| | - material_name
| Starts defining a new local plant material with the given name and **no** properties.

| | - material_name
- old_material
| Starts defining a new local plant material with the given name and using the properties of another local plant material.

| | - material_name
- template_name
| Starts defining a new local plant material with the given name and using the properties of the specified material template.

| | - material
| Sets the basic material of the plant. According to Toady, you can use other materials (for instance, iron) but the game may hiccup on plants that aren't structurally plants. For crops, said material should have [STRUCTURAL_PLANT_MAT] to permit proper stockpiling. Generally, this should be "LOCAL_PLANT_MAT:material_name", using a material defined using MATERIAL, USE_MATERIAL, or USE_MATERIAL_TEMPLATE.

1. Environment tokens
These tokens, also applicable to all plants, specify where the plants grow.

**width="20%" | Token
**width="20%" | Arguments
**width="60%" | Description

| | - minimum
- maximum
| Designates the highest and lowest cavern levels that the plant can appear in if its biome is subterranean.  Dwarven civilizations will only export (via the embark screen or caravans) things that are available at depth 1. Defaults to 0:0 (surface only).

| | | Restricts the plant to growing in Good regions. Cannot be combined with [EVIL].

| | | Restricts the plant to growing in Evil regions. Cannot be combined with [GOOD].

| | | Restricts the plant to growing in Savage regions (regardless of alignment).

| | - freq (0-100)
| How frequently this plant is generated in a particular area. Defaults to 50.  Plants with valid biome tokens and [FREQUENCY:0] will not grow in the wild, but will still be available for entity use and farm plots.

| | | Restricts the plant to grow near natural water features. A plant with [WET] may be very common or very rare in an area, depending on how many water features that area has. Note that they will not grow next to dwarf-filled channels, since it explicitly checks if the tile type is "River", "River Slope", "River Source", "Waterfall" (used back in 40d for underground rivers), "Brook", "Murky Pool", or "Murky Pool Slope".

| | | Allows the plant to grow away from water features.

| | - biome
| What biome this plant appears in.

1. Growth tokens
These tokens are used for all plants and specify growths growing on a plant.  

Edible or otherwise usable growths should have [STOCKPILE_PLANT_GROWTH] in their material definitions for proper stockpiling.  This also lets them be collected from plant gathering and farming jobs.

**width="20%" | Token
**width="20%" | Arguments
**width="60%" | Description

| | - name
| Defines a plant growth.  Takes the below tokens as arguments.  

| | - singular
- plural (STP for standard plural)
| The name of a plant growth.

| | - item token
- material token
| Specifies what item this growth is and what it is made of.  Generally, the item type should be PLANT_GROWTH:NONE.

| | - plant part
| Specifies on which part of the plant or tree the growth appears, usually for multi-tile trees.  Valid tokens are:
- TWIGS
- BRANCHES_AND_TWIGS / LIGHT_BRANCHES_AND_TWIGS
- BRANCHES / LIGHT_BRANCHES
- ALL_BRANCHES_AND_TWIGS
- HEAVY_BRANCHES / DIRECTED_BRANCHES
- HEAVY_BRANCHES_AND_TRUNK / DIRECTED_BRANCHES_AND_TRUNK
- TRUNK
- ROOTS
- CAP
- SAPLING

| | - integer:integer
| Controls the height on the trunk at which the growth begins to appear. The first integer is the percent of the trunk height where the growth begins appearing: 0 will cause growths to appear along the entire trunk above the first tile; 100 will cause growths to appear only at the topmost trunk tile.

The second integer currently *must* be -1, but might be intended to control whether it counts height starting from the bottom or top.

| | - integer
| Currently has no effect.

| | - time start:end (0-403200)
| Specifies at which part of the year the growth appears.  Default is all year round.

A single growth can only have one GROWTH_TIMING tag. If multiple are declared, the last one will be used. To make a growth appear multiple times during the year, you need to create a different growth for every GROWTH_TIMING interval. By using the same material for all of the duplicate growths, all of them will be stockpiled together and be eligible for the same reactions. Edible/brewable growths will have separate entries in the kitchen menu, though.

There is no known way to declare a growth timing that lasts from winter into spring. Including numbers below 0 or above 403200 in the range will make the growth available at all times, as though you hadn't defined a growth timing at all. So will including a range for which the start time is later than the end time.

This has no effect on farmed growths; all eligible growths that have [STOCKPILE_PLANT_GROWTH] in their materials will be harvested, regardless of if they are currently within their growth timing or not.

| | - overworld tile
- item tile
- color
- time (0-403200) start:end, ALL, or NONE
- priority
| Specifies the appearance of the growth.  Can be specified more than once, for example for autumn leaves. Transitions between different timing periods will happen gradually over the course of 2000 ticks. Priority seems to control what to display when there would be multiple symbols on a tile.

The GROWTH_PRINT tile will only be displayed when the growth in question is actually present, even if its timing parameter is ALL.

| | | The growth drops a seed if eaten raw.

| | | Growths drop from the plant, producing a cloud of items which fall on the ground, which herbalists can collect.

| | | Growths drop collectable items from the plant without producing item clouds.

1. Tree tokens
These tokens are used only for trees.

**width="20%" | Token
**width="20%" | Arguments
**width="60%" | Description

| | - material or NONE
| Makes the plant into a tree. Cutting down the tree will yield logs made of this material.  Setting the material to NONE will give no wood from this tree.

| | - name
| What the trunk of the tree is named.

| | - 1-8
| The maximum z-level height of a mature tree's trunk, starting from about two z-levels above ground and going up.

| | - 1-3
| Upper limit of trunk thickness, in tiles. Counted separately for all branching trunks. Has a geometric effect on log yield.

| | - integer
| The number of years the trunk takes to grow one Z-level upward.

| | - integer
| The number of years the trunk takes to grow another tile wider.

| | - name
| What thin branches of the tree are named.

| / 
| - integer
| How dense the branches grow on this tree. 

| /  
| - integer
| The radius to which branches can reach.  Appears to never reach further than seven tiles from the centre.  Does not depend on the trunk branching amount or where trunks are. The values used in the game go from 0-3. Higher values than that can cause crashes. 

| / 
| - name
| What thick branches of the tree are named.

| / 
| - integer
| Similar to BRANCH_DENSITY for thick branches. Values outside 0-3 can cause crashes. 

| / 
| - integer
| Similar as BRANCH_DENSITY for thick branches.

| | - integer
| How much the trunk branches out.  0 makes the trunk straight.

| / 
| - name
| What the roots of the tree are named.

| | - integer
| Density of the root growth.

| | - integer
| How wide the roots reach out.

| | - name
| What the twigs of the tree are named.

| | - boolean (0 or 1)
| Twigs appear on the side of branches.  Defaults to 1.

| | - boolean (0 or 1)
| Twigs appear above branches.  Defaults to 1.

| | - boolean (0 or 1)
| Twigs appear below branches.  Defaults to 0.

| | - boolean (0 or 1)
| Twigs appear on the side of heavy branches.  Defaults to 0.

| | - boolean (0 or 1)
| Twigs appear above heavy branches.  Defaults to 0.

| | - boolean (0 or 1)
| Twigs appear below heavy branches.  Defaults to 0.

| | - boolean (0 or 1)
| Twigs appear on the side of the trunk.  Defaults to 0.

| | - boolean (0 or 1)
| Twigs appear above the trunk.  Defaults to 0.

| | - boolean (0 or 1)
| Twigs appear below the trunk.  Defaults to 0.

| | | The tree has a rounded cap-hood like a giant mushroom. This severely stunts a tree's maximum height - see the bug report. 

| | - name
| What this mushroom-cap is called.  Only makes sense with TREE_HAS_MUSHROOM_CAP.

| | - integer
| Similar to the other PERIOD tags, influences the rate of the mushroom cap growth.  Only makes sense with TREE_HAS_MUSHROOM_CAP.

| | - integer
| The radius of a mushroom cap.  Only makes sense with TREE_HAS_MUSHROOM_CAP.

| | | Uses the standard names for the tree components (roots, trunk, branches, etc.)

| | - tile
| The tile used for trees of this type on the world map. Defaults to 24 (↑).

| | - tile
| The tile used for (un)dead trees and deciduous trees (generally in winter) of this type.  Defaults to 198 (╞).

| | - tile
| The tile used for saplings of this tree. Defaults to 231 (τ).

| | - tile
| The tile used for dead saplings of this tree. Defaults to 231 (τ).

| | - foreground
- background
- bright
| The color of the tree on the map. Defaults to 2:0:0 (dark green).

| | - foreground
- background
- bright
| The color of the tree on the map when (un)dead. Defaults to 0:0:1 (dark gray).

| | - foreground
- background
- bright
| The color of saplings of this tree. Defaults to 2:0:0 (dark green).

| | - foreground
- background
- bright
| The color of dead saplings of this tree. Defaults to 0:0:1 (dark gray).

| | - depth
| The sapling of this tree will drown once the water on its tile reaches this level. Defaults to 4.

| | - depth
| The water depth at which this tree will drown. Exact behavior is unknown. Defaults to 7.

| | | Makes young versions of the tree be called "[tree name] sapling"; otherwise, they are called "young [tree name]".

1. Shrub tokens
These tokens are used for non-grass, non-tree plants.

**width="20%" | Token
**width="20%" | Arguments
**width="60%" | Description

| , , , 
| | Allows the plant to grow in farm plots during the given season.

If the plant is a surface plant, allows it to grow in the wild during this season; wild surface plants without this token will disappear at the beginning of the season. Underground plants grow wild in all seasons, regardless of their season tokens.

| | - time
| How long the plant takes to grow to harvest in a farm plot. Unit hundreds of ticks, See Time. There are 1008 GROWDUR units in a season. Defaults to 300.

| | - value
| Has no known effect. Previously set the value of the harvested plant.

| | - tile
| The tile used when the plant is harvested whole, or is ready to be picked from a farm plot. May either be a cp437 tile number, or a character between single quotes. See character table. Defaults to 231 (τ).

| | - tile
| The tile used when a plant harvested whole has wilted. Defaults to 169 (⌐).

| | - tile
| The tile used to represent this plant when it is wild, alive, and has no growths. Defaults to 34 (").

| | - tile
| The tile used to represent this plant when it is dead in the wild. Defaults to 34 (").

| | - size
| The maximum stack size collected when gathered via herbalism (but *not* farm plots). Defaults to 5.

| | - foreground
- background
- bright
| The color of the plant when it has been picked whole, or when it is ready for harvest in a farm plot. Defaults to 2:0:0 (dark green).

| | - foreground
- background
- bright
| The color of the plant when it has been picked whole, but has wilted. Defaults to 0:0:1 (dark gray).

| | - foreground
- background
- bright
| The color of the plant when it is alive, wild, and has no growths. Defaults to 2:0:0 (dark green).

| | - foreground
- background
- bright
| The color of the plant when it is dead in the wild. Defaults to 6:0:0 (brown).

| | - depth
| The shrub will drown once the water on its tile reaches this level. Defaults to 4.

| | - material
| Names a drink made from the plant, allowing it to be used in entity resources.  Previously also permitted brewing the plant into alcohol made of this material.  Now, a MATERIAL_REACTION_PRODUCT of type DRINK_MAT should be used on the proper plant material.

| | - material
| Permits milling the plant at a quern or millstone into a powder made of this material and allows its use in entity resources. Said material should have [POWDER_MISC_PLANT] to permit proper stockpiling.

| | - material
| Permits processing the plant at a farmer's workshop to yield threads made of this material and allows its use in entity resources. Said material should have [THREAD_PLANT] to permit proper stockpiling.

| | - name
- name_plural
- foreground
- background
- bright
- material
| Causes the plant to yield plantable seeds made of this material and having these properties. Said material should have [SEED_MAT] to permit proper stockpiling.

| | - material
| Permits processing the plant into a vial at a still to yield extract made of this material. Said material should have [EXTRACT_STORAGE:FLASK].

| | - material
| Permits processing the plant into a vial at a farmer's workshop to yield extract made of this material. Said material should have [EXTRACT_STORAGE:FLASK].

| | - material
| Permits processing the plant into a barrel at a farmer's workshop to yield extract made of this material. Said material should have [EXTRACT_STORAGE:BARREL].

1. Grass tokens
These tokens are used only for grasses.

**width="20%" | Token
**width="20%" | Arguments
**width="60%" | Description

| | | Makes the plant behave as a type of grass. This allows animals to graze on it, and prevents it and its growths from being picked by herbalists. (Grass growths can still be picked in adventure mode, however.)

| | - tile
- tile
- tile
- tile
| Specifies the 4 tiles used to represent grass of this type. If VARIED_GROUND_TILES is disabled in d_init.txt, these are seemingly ignored. Defaults to 46:44:96:39 (.,`').

| | - period
- offset
| How often the grass switches between its main tiles and alternate tiles. The "period" value determines how quickly (in frames) the grass animates, and the "offset" value specifies how much of that time is spent displaying the alternate tiles.  If the "offset" value is greater than or equal to the "period" value, the grass will only display using the alternate tiles. Defaults to 0:0.

| | - tile
- tile
- tile
- tile
| When used with ALT_PERIOD, specifies the 4 alternate tiles used to represent grass of this type. Defaults to 46:44:96:39 (.,`'). Dead grass does not animate.

| | - color 1 (fore:back:bright)
- color 2 (fore:back:bright)
- dry color (fore:back:bright)
- dead color (fore:back:bright)
| Specifies the color of this grass. Defaults to 2:0:1:2:0:0:6:0:1:6:0:0 (light green, dark green, yellow, brown).

ru:Plant token
