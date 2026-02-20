# DF2014:Building token

- Building tokens** control the functionality of custom buildings.

All custom buildings are defined as objects of type BUILDING_WORKSHOP or BUILDING_FURNACE; workshops show up in the - menu, while furnaces show up in the - menu.

You also must add any new custom buildings to the civilization that you want to use it.

Additionally, furnaces must be designed by an architect before being constructed (and will gain quality accordingly), though they will always use the labor(s) specified in the building definition, rather than ones based on the materials being used.

**Token
**Arguments
**Description

| | name
| The name of the custom building.

| | fg:bg:bright
| The color of the building's name when uerying it. Seemingly ignored for furnaces, which are hardcoded to 4:0:1.

| | width:height
| The size of the custom building, in number of tiles. Defaults to 3:3. Maximum possible size is 31x31.

| | x:y
| The tile (1:1 for upper-left) in which dwarves will stand when they are performing tasks. Defaults to 3:3 (bottom-right).

| | labor token
| The labor required to construct the custom building. If multiple BUILD_LABOR tokens are specified, then any of the indicated labors can be used to construct the building; if none are specified, then no labors are required.For furnaces, this labor does not come into play until after the workshop has been designed by an architect.

| | key bind
| The shortcut key used in the Build menu for selecting the custom building. For example: "CUSTOM_SHIFT_S"

| | - row
- tiles...
| Specifies whether or not each workshop tile blocks movement. The first parameter is the row (1 = top), and each subsequent parameter is a 0 (nonblocking) or 1 (blocking) for each column, left to right.

| | - stage
- row
- tiles...
| Specifies the characters used to represent the custom building. The first parameter is the building stage, varying from 0 (awaiting construction) to N (completed) where N is between 1 and 3, the 2nd parameter is the row number, and each subsequent parameter is a character number (or literal character enclosed in 'quotes').

| | - stage
- row
- colors...
| Specifies the colors in which the custom building's tiles will be displayed. The first parameter is the building stage, the 2nd parameter is the row number, and subsequent parameters are either sets of 3 numbers (foreground:background:brightness), or the token "MAT" to use the color of the primary building material, for each tile in the row. MAT may not be available on BUILDING_FURNACEs. However a color settings of 4:0:1 will translate into MAT for furnaces instead.

| | - quantity
- item token
- material token
| Specifies one of the objects necessary to construct the custom building. Each BUILD_ITEM can be followed by zero or more modifiers.

| | | Specifies that one of the building's tiles (other than the WORK_LOCATION) must be hanging over magma in order for the building to function. Buildings with this token also ignore the [FUEL] token in their reactions.

1. Item Modifiers
Building items have many of the same modifiers as reagents in custom reactions.

**Token
**Meaning

| []
| Item material must have the [BONE] token.

| []
| Item material must have the [HORN] token.

| []
| Item material must have the [LEATHER] token.

| []
| Item material must have the [PEARL] token.

| [] 
| Item material must be subordinate to a PLANT object.

| []
| Item material must have the [SHELL] token.

| [] 
| Item material must have the [SILK] token.

| []
| Item material must have the [SOAP] token.

| []
| Item is made of a tissue having [TISSUE_SHAPE:STRANDS], intended for matching hair and wool. Must be used with [USE_BODY_COMPONENT].

| []
| Item material must have the [TOOTH] token.

| [] 
| Item material must have the [YARN] token.

| []
| Item must be a bag - that is, a BOX made of plant fiber, silk, yarn, or leather.

| []
| Item must be a general building material - BAR, BLOCKS, BOULDER, or WOOD.

| []
| Item can be an Artifact.

| []
| Item must be a BARREL or TOOL which contains at least one item of type LIQUID_MISC made of LYE.

| []
| If the item is a container, it must be empty.

| []
| Item material must be stable at temperatures below 11000. Only works with items of type BAR, BLOCKS, BOULDER, WOOD, and ANVIL - all others are considered unsafe.

| [] 
| Item material must have the [IS_GLASS] token. All 3 types of glass have this token hardcoded.

| [:X]
| Item's material has a [MATERIAL_REACTION_PRODUCT] token with the appropriate ID.

| [:X]
| Item must be a tool with the specific TOOL_USE value. The item type must be TOOL:NONE for this to make any sense.

| []
| Item material must be stable at temperatures below 12000. Only works with items of type BAR, BLOCKS, BOULDER, WOOD, and ANVIL - all others are considered unsafe.

| [:X]
| Item material must be an ore of the specified metal.

| [:X]
| Item's dimension must be at least this large. The item type must be BAR, POWDER_MISC, LIQUID_MISC, DRINK, THREAD, or CLOTH for this to work.

| []
| Item must not have an edge, so must be blunt. Sharp stones (produced using knapping) and most types of weapon/ammo can not be used with this token.

| []
| If the item is a container, it must not contain lye or milk. Not necessary if specifying [EMPTY].

| []
| Item can not be engraved. For example, a memorial slab can not be engraved.

| []
| Item must be collected (to distinguish silk thread from webs). Only makes sense for items of type THREAD.

| [] (Deprecated)
| Alias for [CONTAINS_LYE].

| [:X]
| Item's material has a [REACTION_CLASS] token with the appropriate ID.

| []
| Item must not be rotten, mainly for organic materials.

| []
| Item must be a body part (CORPSE or CORPSEPIECE).

| []
| Item must be undisturbed (to distinguish silk thread from webs). Only makes sense for items of type THREAD.

| []
| Item material must be non-economic.

ru:Building token
