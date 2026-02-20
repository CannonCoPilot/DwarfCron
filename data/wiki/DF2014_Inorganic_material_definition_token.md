# DF2014:Inorganic material definition token

The following tokens can be used in inorganic material definitions, generally for stones, gems, and metals, but not with materials attached to plants or creatures.

**Token
**Arguments
**Description

| || ||Used on metals, causes the metal to be made into wafers instead of bars.

| || || Causes the stone to form hollow tubes leading to the Underworld. Used for raw adamantine. When mined, stone has a 100% yield. If no material with this token exists, hollow veins will instead be made of the first available inorganic, usually iron.

| || metal:chance || Allows the ore to be smelted into metal in the smelter. Each token with a non-zero chance causes the game to roll d100 four times, each time creating one bar of the type requested on success.

| || metal:chance ||Allows strands to be extracted from the metal at a craftsdwarf's workshop.

| || ||Causes the stone to line the landscape of the Underworld. Used for slade. When mined (if it's mineable), stone has a 100% yield. If no material with this token exists, other materials will be used in place of slade. Underworld spires will still be referred to as a "spire of slade" in the world's history.

| || ||Allows the stone to support an aquifer.

| || ||Causes the material to form metamorphic layers.

| || ||Causes the material to form sedimentary layers.

| || ||Causes the material to form soil layers, allowing it to appear in (almost) any biome. Mining is faster and produces no stones.

| || ||Causes the material to form pelagic sediment layers beneath deep oceans. Mining is faster and produces no stones.

| || ||Causes the material to form sand layers, allowing it to appear in sand deserts and shallow oceans. Mining is faster and produces no stones. Sand layers can also be used for making glass. Can be combined with [SOIL].

| || ||Permits an already [SEDIMENTARY] stone layer to appear underneath shallow ocean regions.

| || ||Permits an already [SEDIMENTARY] stone layer to appear underneath deep ocean regions.

| || || Causes the material to form igneous intrusive layers.

| || || Causes the material to form igneous extrusive layers.

| || class:type:freq ||Specifies what types of layers will contain this mineral. Multiple instances of the same token segment will cause the rock type to occur more frequently, but won't increase its abundance in the specified environment. See below.

| || stone:type:freq ||Specifies which specific minerals will contain this mineral. See below.

| || ||Specifies that the stone is created when combining water and magma, also causing it to line the edges of magma pools and volcanoes. If multiple minerals are marked as lava stones, a different one will be used in each biome or geological region.

| || ||Prevents the material from showing up in certain places. AI-controlled entities won't use the material to make items and don't bring it in caravans, though the player can use it as normal. Also, inorganic generated creatures (forgotten beasts, titans, demons) will never be composed of this material. Explicitly set by all evil weather materials and implied by [DEEP_SURFACE] and [DEEP_SPECIAL].

| || ||Indicates that this is a generated material. Cannot be specified in user-defined raws.

| || ||Found on random-generated metals and cloth.  Marks this material as usable by Deity-created generated entities.

| || sphere ||Found on divine materials.  Presumably links the material to a god of the same sphere.

1. ENVIRONMENT and ENVIRONMENT_SPEC

Format:
- [ENVIRONMENT:<class>:<inclusion type>:<frequency>]

Possible values for class:

**Environment class token
**Description

| ||Will appear in every stone.

| , , ||Will appear in igneous layers, either igneous intrusive, igneous extrusive, or both.

| , , ||Will appear in soil. SOIL_OCEAN is oceans specifically and SOIL_SAND is sand specifically.

| ||Will appear in metamorphic layers.

| ||Will appear in sedimentary layers.

| ||Will appear in alluvial layers. 

Possible values for inclusion type:

**Inclusion type token
**Description

| ||Large ovoids that occupy their entire 48x48 embark tile. Microcline is an example. When mined, stone has a 25% yield (as with layer stones).

| ||Blobs of 3-9 tiles. Will always be successfully mined. Red pyropes are an example. When mined, stone has a 100% yield.

| ||Single tiles. Will always be successfully mined. Clear diamonds are an example. When mined, stone has a 100% yield.

| ||Large streaks of stone. Native gold is an example. When mined, stone has a 33% yield instead of the usual 25%.

An inclusion may be contained within a larger inclusion.  For example, diamond small clusters are found within kimberlite veins.

The frequency number varies from 1 to 100 and determines the relative frequency at which the stone will be chosen to appear - if all frequency values are the same, then all stones will be equally likely to appear.

ENVIRONMENT_SPEC follows much the same format, but takes a specific stone material ID where ENVIRONMENT would take a class token. What you can use will depend on what inorganic raws are around.

1. See also
- Material definition token

ru:Inorganic material definition token
