# DF2014:Item token

Item tokens are the first part in defining the target item in reactions, containing the item type and subtype. They determine the most basic form of the item, made more specific by material tokens.  Most item tokens do not have a subtype; for these, either NO_SUBTYPE or NONE **must** be specified.

Nearly all items are made of a material, though several types expect a creature ID and caste ID (e.g. ANT:SOLDIER) instead.

Actually defining an item in the item raws is done with item definition tokens.

__TOC__

1. Standard item tokens

**# !! Token !! Subtype !! Description

| 0 ||  || NONE || Bars, such as metal, fuel, or soap. Standard dimension = 150.

| 1 ||  || NONE || Cut gemstones usable in the jeweler's workshop

| 2 ||  || NONE || Blocks of any kind.

| 3 ||  || NONE || Rough gemstones or raw glass.

| 4 ||  /  || NONE || Raw mined stone.

| 5 ||  || NONE || Wooden logs.

| 6 ||  || NONE || Doors and glass portals.

| 7 ||  || NONE || Floodgates.

| 8 ||  || NONE || Beds.

| 9 ||  || NONE || Chairs and thrones.

| 10 ||  || NONE || Chains and ropes.

| 11 ||  || NONE || Flasks, vials, and waterskins.

| 12 ||  || NONE || Goblets, mugs, and cups.

| 13 ||  || item_instrument.txt || Musical instruments.

| 14 ||  || item_toy.txt || Toys.

| 15 ||  || NONE || Glass windows.

| 16 ||  || NONE || Cages and terrariums.

| 17 ||  || NONE || Barrels.

| 18 ||  || NONE || Buckets.

| 19 ||  || NONE || Animal traps.

| 20 ||  || NONE || Tables.

| 21 ||  || NONE || Coffins, caskets, and sarcophagi.

| 22 ||  || NONE || Statues.

| 23 ||  || NONE || Corpses. Does not have a material that can be specified for reactions, but GET_MATERIAL_FROM_REAGENT will return the "dominant" material (normally flesh).

| 24 ||  || item_weapon.txt || Weapons.

| 25 ||  || item_armor.txt || Armor and clothing worn on the upper body.

| 26 ||  || item_shoes.txt || Armor and clothing worn on the feet.

| 27 ||  || item_shield.txt || Shields and bucklers.

| 28 ||  || item_helm.txt || Armor and clothing worn on the head.

| 29 ||  || item_gloves.txt || Armor and clothing worn on the hands.

| 30 ||  || NONE || Chests (wood), coffers (stone), boxes (glass, default), and bags (cloth or leather).

| 31 ||  || NONE || Bins.

| 32 ||  || NONE || Armor stands.

| 33 ||  || NONE || Weapon racks.

| 34 ||  || NONE || Cabinets.

| 35 ||  || NONE || Figurines.

| 36 ||  || NONE || Amulets.

| 37 ||  || NONE || Scepters.

| 38 ||  || item_ammo.txt || Ammunition for hand-held weapons.

| 39 ||  || NONE || Crowns.

| 40 ||  || NONE || Rings.

| 41 ||  || NONE || Earrings.

| 42 ||  || NONE || Bracelets.

| 43 ||  || NONE || Large gems.

| 44 ||  || NONE || Anvils.

| 45 ||  || NONE || Body parts. Does not have a material that can be specified for reactions, but GET_MATERIAL_FROM_REAGENT will return the "dominant" material.

| 46 ||  || NONE || Dead vermin bodies. Material is CREATURE_ID:CASTE.

| 47 ||  || NONE || Butchered meat.

| 48 ||  || NONE || Prepared fish. Material is CREATURE_ID:CASTE.

| 49 ||  || NONE || Freshly-caught fish. Material is CREATURE_ID:CASTE.

| 50 ||  || NONE || Live vermin. Material is CREATURE_ID:CASTE.

| 51 ||  || NONE || Tame vermin. Material is CREATURE_ID:CASTE.

| 52 ||  || NONE || Seeds from plants.

| 53 ||  || NONE || Plants.

| 54 ||  || NONE || Leather.

| 55 ||  || growth ID || Plant growths.  Subtype is the GROWTH's identifier within the plant raws (e.g. "LEAVES" or "FLOWERS" for most trees)

| 56 ||  || NONE || Thread (made at the farmer's workshop), webs (collected or undisturbed), and strands extracted from suitable stones. Standard dimension = 15000.

| 57 ||  || NONE || Cloth made at the loom. Standard dimension = 10000.

| 58 ||  || NONE || Skull totems.

| 59 ||  || item_pants.txt || Armor and clothing worn on the legs.

| 60 ||  || NONE || Backpacks.

| 61 ||  || NONE || Quivers.

| 62 ||  || NONE || Catapult parts.

| 63 ||  || NONE || Ballista parts.

| 64 ||  || item_siegeammo.txt || Siege engine ammunition.

| 65 ||  || NONE || Ballista arrow heads.

| 66 ||  || NONE || Mechanisms.

| 67 ||  || item_trapcomp.txt || Trap components.

| 68 ||  || NONE || Alcoholic drinks. Standard dimension = 150.

| 69 ||  || NONE || Powders such as flour, dye, sand, or gypsum plaster. Standard dimension = 150.

| 70 ||  || NONE || Pieces of cheese.

| 71 ||  || item_food.txt || Prepared meals.

| 72 ||  || NONE || Liquids such as water, lye, and extracts. Standard dimension = 150.

| 73 ||  || NONE || Coins.

| 74 ||  || NONE || Fat, tallow, pastes/pressed objects, and small bits of molten rock/metal. Standard dimension = 150.

| 75 ||  || NONE || Small rocks (usually sharpened and/or thrown in adventurer mode).

| 76 ||  || NONE || Pipe sections and glass tubes.

| 77 ||  || NONE || Hatch covers.

| 78 ||  || NONE || Grates.

| 79 ||  || NONE || Querns.

| 80 ||  || NONE || Millstones.

| 81 ||  || NONE || Splints.

| 82 ||  || NONE || Crutches.

| 83 ||  || NONE || Traction benches.

| 84 ||  || NONE || Casts.

| 85 ||  || item_tool.txt || Tools.

| 86 ||  || NONE || Slabs, memorials, and shop signs.

| 87 ||  || NONE || Eggs. Material is CREATURE_ID:CASTE.

| 88 ||  || NONE || Books.

| 89 ||  || NONE || Sheets. Paper, papyrus, or parchment. Used for making quires and scrolls.

| 90 ||  || NONE || Branches plucked from trees, used for making stone axes in adventurer mode.

1. Special use item tokens

In several specific locations, the values below can be substituted for the item type and subtype (and be followed directly by the material token).

**Token
**Subtype
**Valid Uses
**Description

| | NONE
| Reaction [REAGENT]
| Matches FIGURINE, AMULET, SCEPTER, CROWN, RING, EARRING, or BRACELET.

| | NONE
| Reaction [REAGENT]
| Matches POWDER_MISC, BAR, BOULDER, or GLOB.

| | NONE
| Reaction [PRODUCT]
| Produces 1-3 items of any type possible to make with the specified material, normally the types FIGURINE, AMULET, SCEPTER, CROWN, RING, EARRING, or BRACELET, however GEM is also possible for some materials and there may be other possible results. The output depends entirely on the material used, and incredibly unusual materials may produce nothing at all, although most vanilla materials will produce GEMs at the very least.

1. Related tokens

These tokens are not Item Tokens at all, but can take the place of them in some circumstances.

**Token
**Subtype
**Valid Uses
**Description

| | Metal   
| Reaction [REAGENT]   
| Matches a BOULDER item made of a material having [METAL_ORE:<Metal>:###].

1. See also
- Material token
- Reactions

ru:Item token
