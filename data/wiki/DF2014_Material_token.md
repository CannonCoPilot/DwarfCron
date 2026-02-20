# DF2014:Material token

:*For the tokens that define an individual material's properties, see Material definition token.*

Material tokens are used to refer to various types of materials in a wide variety of places. They can take the following forms below.

1. Tokens

**width="20%" | Token
**width="30%" | Arguments
**width="50%" | Description

| | MATERIAL_NAME
| Specifies a standalone inorganic material defined in the raws, generally a stone or metal. For example, INORGANIC:IRON refers to iron, and INORGANIC:CERAMIC_PORCELAIN refers to porcelain. The material name can be substituted with USE_LAVA_STONE to automatically select the local lava stone, which is normally obsidian.

| | MATERIAL_NAME
| Alias for INORGANIC:MATERIAL_NAME, intended for backwards compatibility.

| | MATERIAL_NAME
| Alias for INORGANIC:MATERIAL_NAME, intended for backwards compatibility.

| | CHARCOAL, COKE, or NO_MATGLOSS
| Specifies a material that can be used as fuel - charcoal or coke. Specifying NO_MATGLOSS (**not** NONE) will make it accept "refined coal" in general, which matches charcoal, coke, and generic refined coal.

| | CREATURE_ID:MATERIAL_NAME or CREATURE_ID:INDEX###
| Specifies a material associated with a specific creature. Examples: CREATURE_MAT:DWARF:SKIN refers to dwarf skin. Can also specify "INDEX" followed by a 3-digit number to select a material by index instead of by name, where 000 is the first material in that creature.

| | MATERIAL_NAME or INDEX###
| Alias for CREATURE_MAT:**CREATURE_ID**:MATERIAL_NAME (or CREATURE_MAT:**CREATURE_ID**:INDEX###), where CREATURE_ID is the creature currently being defined; as such, it can only be used in creature definitions.

| | PLANT_ID:MATERIAL_NAME
| Specifies a material associated with a specific plant. Example: PLANT_MAT:BUSH_QUARRY:LEAF refers to quarry bush leaves.

| | MATERIAL_NAME
| Alias for PLANT_MAT:**PLANT_ID**:MATERIAL_NAME, where PLANT_ID is the plant currently being defined; as such, it can only be used in plant definitions.

| | REAGENT_ID:REACTION_PRODUCT_ID
| Specifies a material related to a reagent's material within a reaction. REAGENT_ID must match a [REAGENT], and REACTION_PRODUCT_ID must either match a [MATERIAL_REACTION_PRODUCT] belonging to the reagent's material or be equal to "NONE" to use the reagent's material itself.

| | NONE
| Specifies one of the hardcoded materials listed below. Note that this goes in the token itself, not arguments (i.e GLASS_GREEN:NONE, not MATERIAL_NAME:GLASS_GREEN).

Several types of items expect a creature ID and caste ID (e.g. ANT:SOLDIER) in place of the material token.

1. Hardcoded Materials

It should be noted when using the table below, that you do not place (MATERIAL_NAME:(Your material here)). For example, green glass will be (GLASS_GREEN:NONE).

**# !! Token !! Information

| -1 ||  || Unknown material (light gray, solid), acts as a placeholder for any material.

| 0 ||  || Magma when specified with subtype NONE or NO_MATGLOSS, otherwise a user-defined inorganic material.

| 1 ||  || Amber

| 2 ||  || Coral

| 3 ||  || Green glass

| 4 ||  || Clear glass

| 5 ||  || Crystal glass

| 6 ||  || Water, when placed in buckets or when mining out ice.

| 7 ||  || Coal - subtype is either COKE or CHARCOAL (or NO_MATGLOSS to match either).

| 8 ||  || Potash

| 9 ||  || Ash

| 10 ||  || Pearlash

| 11 ||  || Lye

| 12 ||  || Mud

| 13 ||  || Vomit

| 14 ||  || Salt

| 15 ||  || Filth (brown, solid)

| 16 ||  || Filth (yellow, liquid)

| 17 ||  || Unknown substance (light gray, liquid)

| 18 ||  || Grime

ru:Material token
