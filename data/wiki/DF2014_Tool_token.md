# DF2014:Tool token

1. Tokens

**Token
**Arguments
**Description

| | - singular
- plural
| Name of the tool. <font color="red">Required.</font>

| | | Permits the tool to be made from any bone.

| | | Permits the tool to be made from any ceramic material.

| | | Allows a string to describe the tool when iewed. The text box can accommodate up to 325 characters until it cuts off, but the spacing of actual sentences puts the realistic limit closer to 300.  Multiple DEFINITION tokens can be used in the same tool definition, with each appearing on a new line.

| | | Permits the tool to be made from any glass.

| | | Permits the tool to be made from anything with the [ITEMS_HARD] token, such as wood, stone or metal.

| | | Permits the tool to be made from any leather.

| | | Permits the tool to be made from anything with the [IS_METAL] token.

| | | Permits the tool to be made from any metal with the [ITEMS_WEAPON] token.

| | | Permits the tool to be made from any "sheet" material, such as papyrus, paper, and parchment. Connected to the PAPER_SLURRY/PAPER_PLANT reaction classes?

| | | Permits the tool to be made from any shell.

| | | Permits the tool to be made from any silk.

| | | Permits the tool to be made from any material with the [ITEMS_SOFT] token, such as leather or textiles.

| | | Permits the tool to be made from any stone. Presumably connected to the [IS_STONE] token.

| | | Permits the tool to be made from any plant fiber, such as pig tails.

| | | Permits the tool to be made from any wood.

| | | According to Toady, "Won't be used in world gen libraries (to differentiate scrolls from quires). Also put it on bindings, rollers, instr. pieces for completeness/future use".  Used on scroll rollers, book bindings, and quires.

| | - improvement type and subtype (latter only really applicable to SPECIFIC)
- tool material flag like HARD_MAT or SILK_MAT
| Items that appear in the wild come standard with this kind of improvement. Used on scrolls: [DEFAULT_IMPROVEMENT:SPECIFIC:ROLLERS:HARD_MAT]
Currently bugged, the effect is also applied to everything made in-game. This causes scrolls to have two sets of rollers, for example.

| | | Prevents the tool from being improved.  Used on honeycombs, (scroll rollers, book bindings, and quires.)

| | - num
| Defines the item value of the tool. <font color="red">Required.</font>

| | - num
| Defines the tile used to represent the tool. <font color="red">Required.</font>

| | | The background of the tile will be colored, instead of the foreground.

| | | According to Toady, "only custom reactions are used to make this item". Found on scrolls and quires. 

| | - tool use, see below
| Defines the task performed using the tool.

| | | Allows item to be stored in a furniture stockpile.

| | - shape category
| Category of shapes to choose from for the tool as defined by the CATEGORY token in descriptor_shape_standard.txt or a custom descriptor definition.

| | | Used on dice.

| | - adjective
| Adjective preceding the material name (e.g. "large copper dagger")

| / 
| - size
| Volume of tool in mL or cubic centimeters. <font color="red">Required.</font>

| | - amount
| How much the item can contain. Defaults to 0.

| | - value
| <font color="red">Required for weapons.</font>

| | - value
| <font color="red">Required for weapons.</font>

| | - Skill token
| The skill to determine effectiveness in melee with this tool. <font color="red">Required for weapons.</font>

| | - Skill token
- Ammo item token
| Makes this tool a ranged weapon that uses the specified ammo. The specified skill determines accuracy in ranged combat.

| | - size
| Creatures under this size (in cm^3) must use the tool two-handed. <font color="red">Required for weapons.</font>

| | - size
| Minimum body size (in cm^3) to use the tool at all (multigrasp required until TWO_HANDED value) <font color="red">Required for weapons.</font>

| | - value
| Number of bar units needed for forging, as well as the amount gained from melting. <font color="red">Required for weapons.</font>

| | - attacktype:BLUNT or EDGE
- contact_area:value
- penetration_size:value
- verb2nd:string
- verb3rd:string
- noun:string
- velocity_multiplier:value
| You can have many ATTACK tags and one will be randomly selected for each attack, with EDGE attacks 100 times more common than BLUNT attacks. <font color="red">Required for weapons.</font>

Valid tool uses (and the default tools used for these tasks) are as follows:

**ID
**Token
**Usage

| 0 || LIQUID_COOKING || cauldron || adventure mode decoration / weapon

| 1 || LIQUID_SCOOP || ladle || adventure mode decoration / weapon

| 2 || GRIND_POWDER_RECEPTACLE || mortar || adventure mode decoration / weapon

| 3 || GRIND_POWDER_GRINDER || pestle || adventure mode decoration / weapon

| 4 || MEAT_CARVING || carving knife || adventure mode decoration / weapon

| 5 || MEAT_BONING || boning knife || adventure mode decoration / weapon

| 6 || MEAT_SLICING || slicing knife || adventure mode decoration / weapon

| 7 || MEAT_CLEAVING || meat cleaver || adventure mode decoration / weapon

| 8 || HOLD_MEAT_FOR_CARVING || carving fork || adventure mode decoration / weapon

| 9 || MEAL_CONTAINER || bowl || adventure mode decoration / weapon

| 10 || LIQUID_CONTAINER || jug || can store honey or oil

| 11 || FOOD_STORAGE || large pot || can store beer

| 12 || HIVE || hive || can make honey

| 13 || NEST_BOX || nest box || for your birds to lay eggs

| 14 || SMALL_OBJECT_STORAGE || pouch || adventure mode coin purse

| 15 || TRACK_CART || minecart || item hauling / weapon

| 16 || HEAVY_OBJECT_HAULING || wheelbarrow || allows hauling items faster

| 17 || STAND_AND_WORK_ABOVE || stepladder || allows gathering fruit from trees

| 18 || ROLL_UP_SHEET || scroll rollers || 

| 19 || PROTECT_FOLDED_SHEETS || book binding ||

| 20 || CONTAIN_WRITING || scroll & quire ||

| 21 || BOOKCASE || bookcase ||

| 22 || DISPLAY_OBJECT || pedestal & display case || for museums

| 23 || PLACE_OFFERING || altar || for (eventually) offering sacrifices

| 24 || DIVINATION || dice || 

| 25 || GAMES_OF_CHANCE || dice || 

ru:Tool token
