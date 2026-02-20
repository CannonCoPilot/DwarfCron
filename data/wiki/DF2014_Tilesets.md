# DF2014:Tilesets

:*(For an overview of graphics in DF, see Graphics)*
:*(For a chart with the default ASCII characters, see Character table.)*
:*(For user-created creature tilesets, see Tileset repository.)*
:*(For information about Graphic sets, see Graphic set)*
:*(For information on how tilesets get colored, see Color)*
----

    - Tilesets** are images the game uses to display its graphics; each tile is used to show text and represent things. Users create custom tilesets for a number of reasons, including increased visibility, aesthetics, or small size. Tilesets come in two flavors: "**character sets**" (or simply "tilesets") and "**graphics sets**". This article is only about tilesets.

1. Overview

A character set (or 'tileset') is an image in BMP or PNG format that contains the 256 different tiles (numbered 0-255), corresponding to the IBM Code Page 437 (sometimes called Extended ASCII), which are used to display all graphics. The tiles are always arranged in a 16x16 grid, but its dimensions can be varied. You can have both square and non-square tiles, with 16x16 pixels being the most common size. 

As the tileset is limited to only 256 tiles, some objects share the same tile. Some of those can be changed in the raws and init files, and creatures can have separate graphics, but in most cases they are hardcoded. Below is a detailed list.

1. Installation and creation of custom tilesets
1. Installation
Here is the list of user-made standard tilesets. To install any of these tilesets, follow these steps:

1. Download the tileset via right-click-save-as on the tileset.  The tileset is just an image, so there's no separate download link. (The list is here)
1. Verify that the tileset is a 24-bit BMP fileV0.28.181.40d with magenta-colored background or 24-bit PNG filev0.31.06 with transparent background. In case you need to convert it, do NOT just change the extension to .bmp or .png; you must use a program like MS paint to save it properly.
1. Put it in the data/art directory of your *Dwarf Fortress* installation.
1. Open data/init/init.txt
1. There are 4 values you can change: [FULLFONT], [FONT], [GRAPHICS_FONT], and [GRAPHICS_FULLFONT]*. Usually you just set all 4 to the same filename of the tileset you just downloaded (**[FONT:mytileset.png]** for example).
1. [FULLSCREENX:800] and [FULLSCREENY:600] set your resolution, but it is recommended to let the game decide that automatically by setting it to 0; Similarly, [WINDOWEDX:800] and [WINDOWEDY:600] denote your windowed resolution in pixels (but in tiles if set below a value of 256).
1. It is also recommended you keep [BLACK_SPACE:YES] to prevent stretching of the graphics.
1. Save the .txt file, then you're ready to play!

*They're used for the tileset used in fullscreen and windowed mode and the two GRAPHICS_ values are for tilesets used together with graphic_sets when [GRAPHICS] is set to YES. You can set them to different file names, if you want to use different tilesets for each.

1. Creating a custom tileset
The default (and minimum) gameplay viewport is 80 characters wide, and 25 characters tall. Therefore, a tileset's target resolution will be TILE_X_LENGTH * 80 by TILE_Y_LENGTH * 25. Since the tileset is arranged into a 16x16 grid of tiles (256 tiles total), the tileset image size will be TILE_X_LENGTH * 16 by TILE_Y_LENGTH * 16. Here are some common tile sizes:

- A tileset with 10x12 tiles will be 160x192 pixels large, and the target resolution will be 800x300.
- A tileset with 16x16 tiles will be 256x256 pixels large, and the target resolution will be 1280x400.

When creating a custom tileset, it's often easiest to start with an existing one, and edit it to your liking. Tilesets generally fall into two categories: rectangular tilesets and square tilesets. Rectangular tilesets have tiles that are taller than they are wide. The text in these tilesets is generally easier to read, but the map appears squished horizontally. Square tilesets usually provide more attractive graphics, but are slightly less readable. The graphics in Dwarf Fortress can be enhanced through the use of creature graphics, which allow creatures to have unique graphics without using up space on the main tilesheet. Mifki created a tool to make a tileset from any font, which can be used as starting point or as is.

Many tiles are used by the game in multiple ways, and this makes customizing the graphics difficult. The same icon is used for chairs and the north end of one-tile-wide vertical bridges. Ashes and broken arrows look the same, and many game entities (such as levers, floodgates, bags, and bins) share characters that are also used in Dwarven names or other bits of text in the interface.

Some of these issues can be fixed by the third-party Text Will Be Text (TWBT) plugin for the DFHack modding API. In addition to many other features, TWBT allows many items and building tiles to be moved to separate "overrides" tilesheets, so that fewer objects need to share tiles. TWBT also allows the use of a dedicated tilesheet just for text. TWBT still might not be very stable in adventure mode, though, so be cautious when using TWBT with adventure mode.

1. Generating a custom tileset from a font in Linux

While TrueType fonts can be used directly in *Dwarf Fortress*, it may be desirable to generate a tileset image instead (for example, when using TWBT). In Linux, it is possible to do this programmatically in the terminal. The following command will open a terminal window with your desired font, rendered appropriately for *Dwarf Fortress*, and screenshots it. It requires xterm, the screenshot utility xwd, and a text file containing the code page 437 characters in the appropriate order.

```
xterm -fa "FONTFAMILY:pixelsize:SIZE:antialias=false" -bg magenta -geometry 16x16 -e "setterm -cursor off && printf '%s' \"\$(<PATH/TO/CODE437.txt)\" && sleep 0.1 && xwd -id \$WINDOWID | xwdtopnm | pnmtopng > \"FONTFAMILY-SIZE.png\""
```

This will generate an image in your current directory, so it might be a good idea to cd into your /data/art directory beforehand.

    - This works *much* better for bitmap fonts, in their native size.** For a list of such fonts on your system and their sizes, you can run 

```
fc-list :scalable=false:spacing=mono family pixelsize
```

<!--=== How colors other than white and magenta work ===

When the game draws a tile, it will select a foreground color, a background color, and a tile based on the item being drawn.  The background color will be used in place of magenta (Hex code #FF00FF or RGB 255 0 255).  All other colors in the tile will be treated as a mask against the foreground color.  Pure white (#FFFFFF) will always show the foreground color, while light grey (#CCCCCC) will be a slightly darker version of the foreground color, and dark grey (#888888) will be a dark version of the foreground color.  Black (#000000) will always be black.  It is impossible to use different shades of the background color.

As of the current version of the game (v0.43.04), alpha values are supported in png fonts, allowing for better transparency, and partial transparency, enabling anti-aliased tilesets and other interesting tricks.

In general, just remember these rules:

- Bright magenta (#FF00FF) is the background.
- Bright white (#FFFFFF) is the foreground.
- Darker shades of white and grey (#C0C0C0, #808080, etc) will display darker shades of the foreground color.  It is possible to use any shade of grey, including ones like #333333 and #C2C2C2.
- Black (#000000) will always be black.
- It's probably best to avoid color in normal tilesets.

For an example, the game is drawing an exposed turquoise cluster with color <span style="color:#00F;">bright blue (#0000FF).  While loading the tile image, it encounters the color <span style="color:#CCC;">light grey (#CCCCCC).  The color used in its place will be:

**Color component || Foreground color || Color mask from tile || Calculation in hex || Calculation in decimal

| Red   || #<span style="color:#F00;">0000FF || #<span style="color:#F00;">CCCCCC || <span style="color:#F00;">0016 * <span style="color:#F00;">CC16 / 10016 = <span style="color:#900;">0016 || <span style="color:#F00;">0 * <span style="color:#F00;">204 / 256 = <span style="color:#900;">0

| Green || #00<span style="color:#0F0;">00FF || #CC<span style="color:#0F0;">CCCC ||<span style="color:#0F0;">0016 * <span style="color:#0F0;">CC16 / 10016 = <span style="color:#090;">0016 || <span style="color:#0F0;">0 * <span style="color:#0F0;">204 / 256 = <span style="color:#090;">0

| Blue  || #0000<span style="color:#00F">FF  || #CCCC<span style="color:#00F;">CC || <span style="color:#00F;">FF16 * <span style="color:#00F;">CC16 / 10016 = <span style="color:#009;">CB16 || <span style="color:#00F;">255 * <span style="color:#00F;">204 / 256 = <span style="color:#009;">203

| <span style="color:#0000CB">Final Color || || || #<span style="color:#900;">00<span style="color:#090;">00<span style="color:#009;">CB || <span style="color:#900;">0 <span style="color:#090;">0 <span style="color:#009;">203

Color masks with unequal amounts of R, G and B are calculated in the same fashion.  The game is now drawing a speardwarf with color <span style="color:#C0C000;">brown (#C0C000).  It encounters the color <span style="color:#008080;">cyan while loading the tile (#008080).  The color used instead of cyan will be:

**Color component || Foreground color || Color mask from tile || Calculation in hex || Calculation in decimal

| Red   || #<span style="color:#F00;">C0C000 || #<span style="color:#F00;">008080 || <span style="color:#F00;">C016 * <span style="color:#F00;">0016 / 10016 = <span style="color:#900;">0016 || <span style="color:#F00;">192 * <span style="color:#F00;">0 / 256 = <span style="color:#900;">0

| Green || #C0<span style="color:#0F0;">C000 || #00<span style="color:#0F0;">8080 ||<span style="color:#0F0;">C016 * <span style="color:#0F0;">8016 / 10016 = <span style="color:#090;">6016 || <span style="color:#0F0;">192 * <span style="color:#0F0;">128 / 256 = <span style="color:#090;">96

| Blue  || #C0C0<span style="color:#00F">00  || #0080<span style="color:#00F;">80 || <span style="color:#00F;">0016 * <span style="color:#00F;">8016 / 10016 = <span style="color:#009;">0016 || <span style="color:#00F;">0 * <span style="color:#00F;">128 / 256 = <span style="color:#009;">0

| <span style="color:#006000">Final Color || || || #<span style="color:#900;">00<span style="color:#090;">60<span style="color:#009;">00 || <span style="color:#900;">0 <span style="color:#090;">96 <span style="color:#009;">0

As illustrated by this example, colors in the tileset can result in colors that aren't in the foreground color or the tile graphic.  In this case, a brown foreground color with a cyan pixel color in the tileset results in a final color of green.

Theoretically, the way the game handles color masks could be used to display different graphics for items that use the same tile (but whose respective colors use different color component channels).  For example, if a bright red object and a bright blue object use the same tile, the tile can use bright red for all pixels that only the red object uses, bright blue for all pixels only the blue object uses, and bright magenta (but NOT #FF00FF, it would have to be #FE00FE or something similar) for all pixels both objects use.  In this fashion the two objects that share a tile would look completely different.  In practice however, this is probably impossible because so many objects share the same tile, the chances of the potential foreground colors sharing a red, green, or blue color component are too great.-->

1. What tiles are used for what

- Items marked with * can have their tile changed in the raw data files.
- Items marked with # can have their tile replaced by a graphic set image, in addition to having their tile changed in the raw data.
- Items marked with $ can be changed in the d_init.txt file.
- Items marked with ¢ use dual colors.
- Items marked with ÷ use inverted tile

For a graphical table, go to the Character Table.

1. Row 01 (000-015)

| 000&nbsp;
| Used for background tiles in the intro CMV and background tiles of interface screens

| 001 
| Civilian dwarves#, various status indicators

| 002 
| Military dwarves#

| 003 
| Dimple cups*

| 004 
| Cut gems, large gems

| 005 
| Quarry bush leaves*, blossoms*, various forest trees*

| 006 
| Broadleaf forest, various forest trees*, various leaf items*, Plump helmets*

| 007 
| Mined-out stone*, solid workshop tile for several workshops like the magma smelter, filled nest box building, river sources on world map, caves on world map, lairs on world map, moon on travel map, flower buds*

| 008 
| Solid workshop tile for several other workshops like the magma forge, tanner's shop, catapult cup, nest box tool*, empty nest box building, codices, dice

| 009 
| Well, vermin colony, millstone, quern, vertical axle, fortress walls on travel map, sun behind clouds on travel map, castles on world map, monasteries on world map, creeping eye out of view (adventure mode)*, staring eyeball*, bubble bulb*

| 010 
| trunk interior$, forts on world map

| 011 
| Male sign, bags, various cephalopods#

| 012 
| Female sign, amulet

| 013 
| Ladles*, dancers dancing

| 014 
| Armor stands, playing instruments

| 015 
| Masterpiece quality tags, unmined gem cluster*, Rough gems and Raw glass, unmined bituminous coal*, mined bituminous coal*, currency symbol, spider webs, pond turtle*, sun, gear assemblies, paralyzed indicator, fireballs, bandit camps on travel map, towns on world map, night creature senses, artifact gem doors¢

1. Row 02 (016-031)

| 016 
| Head of Ballista arrow facing east, manta ray#

| 017 
| Head of Ballista arrow facing west

| 018 
| | 019 
| Cages¢, on-fire tags, vertical bars

| 020 
| Mugs, drinking in-progress, largest forest retreats, cumulonimbus clouds on travel map, Highwood forests*

| 021 
| Restraints, whip vine*

| 022 
| Logs, hive tool*, hive building

| 023 
| Cedar forest*

| 024 
| Interface text (bridge direction), conifer forests, various forest trees*

| 025 
| Interface text (bridge direction), Various status indicators

| 026 
| Interface text (bridge direction)

| 027 
| Interface text (bridge direction)

| 028 
| | 029 
| | 030 
| Head of Ballista arrow facing north, ramp, track ramp up$, mountain on world map

| 031 
| Head of Ballista arrow facing south, ramp on level below, trackramp on level below$

1. Row 03 (032-047)

| 032&nbsp;
| Spaces in text messages, Unexplored underground, black background on the title screen and interface menu

| 033 
| Text, various status icons, sound indicator in sneaking mode, tracks (footprints) in sneaking mode

| 034 
| Text, shrub*, various status icons, quotation marks, Carpenter's workshop tile, kobold out of view*, goblin out of view*, blizzard man out of view*, tracks (bent vegetation) in sneaking mode, various stones*, savanna, swamp, shrubland, marsh

| 035 
| Text, floor grates, various stones*, smoothed branches in elven forest retreats, labyrinths on travel map, towns on world map

| 036 
| Coins

| 037 
| Prepared meal, unexplored underground, screw pump in action, footprints in sneaking mode, various fruits*,  various buds*, various stones*, Bismuthinite*, Floating guts#

| 038 
| Demons#

| 039 
| Text, rough floors, unexplored underground, various stones, one eyed creatures with GLOWTILE " (kobold, goblins, and blizzard in vanilla), various grasses*

| style="white-space:nowrap"|040 
| Text, foreign object opening tag, tile in bowyer's workshop, waning moon on travel map

| 041 
| Text, foreign object closing tag, waxing moon on travel map

| 042 
| Interface text, superior quality tags, Unmined ore*, glowing pits, key reference, working gear assembly, gem floodgate, various stones*, chestnut fruit*, other fruits and flowers*, moving armies on quick travel map, towns on world map

| 043 
| Text, finely-crafted quality tags, Smooth/constructed floors, block/bar bridge or road, Bauxite*, injury indicator, towns on world map, mining designation

| 044 
| Text, rough floors, Claystone*, unexplored underground, various grasses*

| 045 
| Text, well-crafted quality tags, Scepters, keyboard reference, various stones*, overlapping creatures animation

| 046 
| Text, rough floors, various stones*, unexplored underground, various grasses*

| 047 
| Text, weapons, bolts, Ballista tile, Pestle, overlapping creatures animation, stone axe, active windmill blade

1. Row 04 (048-063)

| 048 
| Text, coffins, tombs on world map

| 049 
| Text, designation priorities, adventurer mode conversation targets, fluids if SHOW_FLOW_AMOUNTS is YES in d_init.txt

| 050 
| Text, designation priorities, adventurer mode conversation targets, fluids if SHOW_FLOW_AMOUNTS is YES in d_init.txt

| 051 
| Text, designation priorities, adventurer mode conversation targets, fluids if SHOW_FLOW_AMOUNTS is YES in d_init.txt

| 052 
| Text, designation priorities, adventurer mode conversation targets, fluids if SHOW_FLOW_AMOUNTS is YES in d_init.txt

| 053 
| Text, designation priorities, adventurer mode conversation targets, fluids if SHOW_FLOW_AMOUNTS is YES in d_init.txt

| 054 
| Text, designation priorities, adventurer mode conversation targets, fluids if SHOW_FLOW_AMOUNTS is YES in d_init.txt

| 055 
| Text, designation priorities, adventurer mode conversation targets, fluids if SHOW_FLOW_AMOUNTS is YES in d_init.txt

| 056 
| Text, Fortress gates on travel map

| 057 
| Text

| 058 
| Interface text, strawberry*, prickle berry*, fisher berry*, sun berry*, snowstorms, underground shrubs*

| 059 
| Interface text (command menu Movies key), Mason's workshop, Kitchen, Selenite*, twigs$

| 060 
| Interface text (trading screen "Less than 1 unit weight"), brackets around squad names, Stairs up, west move indicator (adventure mode)

| 061 
| Empty Stockpiles, hamlets on world map, various stones*, middle-left tile of Furnaces, up-right tile of Carpenter's workshop

| 062 
| Brackets around squad names, Stairs down, east move indicator (adventure mode)

| 063 
| Text, various status icons

1. Row 05 (064-079)

| 064&nbsp;
| berserk dwarf#, adventurer#, dwarven merchants#, dwarven caravan guards#, dwarven diplomat#, adventurer's location on map

| 065&nbsp;
| Text, various creatures#, Tile in Farm Workshop

| 066&nbsp;
| Text, various creatures#

| 067&nbsp;
| Text, various creatures#, construction designations

| 068&nbsp;
| Text, various creatures#, Depot Access Display

| 069&nbsp;
| Text, various creatures#

| 070&nbsp;
| Text, various creatures#

| 071&nbsp;
| Text, various creatures#

| 072&nbsp;
| Text, various creatures#, high traffic designation

| 073&nbsp;
| Text, various creatures#, support, Necromancer's tower on world map

| 074&nbsp;
| Text, various creatures#

| 075&nbsp;
| Text, various creatures#

| 076&nbsp;
| Text, various creatures#, low traffic designation

| 077&nbsp;
| Text, various creatures#

| 078&nbsp;
| Text, various creatures#

| 079&nbsp;
| Text, various creatures#, trade depot post, glass portal, Tile in Farm Workshop, column$, wall construction, full moon on travel map and dwarf mode, trunk$, staring eyeball*, bubble bulb*, windmill hub

1. Row 06 (080-095)

| 080&nbsp;
| Text, various creatures#

| 081&nbsp;
| Text

| 082&nbsp;
| Text, various creatures#, restricted traffic designation

| 083&nbsp;
| Text, various creatures#

| 084&nbsp;
| Text, various creatures#

| 085&nbsp;
| Text, various creatures#

| 086&nbsp;
| Text, Badlands on map

| 087&nbsp;
| Text, various creatures#, Depot Access Display

| 088&nbsp;
| Text, wear tags, keyboard cursor, Bin¢, floodgate¢, shop post, building footprint, Depot Access Display, up/down stairs, Tile in Ashery, Archery target, various status indicators

| 089&nbsp;
| Text, Yak#, Yeti#

| 090&nbsp;
| Text, Sleep indicator

| 091&nbsp;
| Text, Floor tile in workshops, Clothing, armor, item stack opening tag, moon on travel map, tracks (bootprints) in sneaking mode

| 092&nbsp;
| Overlapping creatures animation, Ballista tile, helves*, active windmill blade

| 093&nbsp;
| Text, Floor tile in workshops and furnaces, item stack closing tag

| 094&nbsp;
| Trap, Alabaster*, Aluminum*, Volcano on world map, north move indicator (adventure mode), Mechanic Workshop center-south tile (in light cyan)

| 095&nbsp;
| Text, Channel designation

1. Row 07 (096-111)

| 096&nbsp;
| Rough floors, unexplored underground*, various stones*, various grasses*

| 097&nbsp;
| Text, various creatures#

| 098&nbsp;
| Text, various creatures#

| 099&nbsp;
| Text, various creatures#

| 100&nbsp;
| Text, various creatures#

| 101&nbsp;
| Text, various creatures#

| 102&nbsp;
| Text, various creatures#

| 103&nbsp;
| Text, various creatures#

| 104&nbsp;
| Text, various creatures#

| 105&nbsp;
| Text, various creatures#

| 106&nbsp;
| Text, various creatures#

| 107&nbsp;
| Text, various creatures#

| 108&nbsp;
| Text, various creatures#

| 109&nbsp;
| Text, various creatures#

| 110&nbsp;
| Text, various creatures#, Hills on map

| 111&nbsp;
| Text, various creatures#, Graphite*, well construction, bridge construction, millstone in action, vertical axle in action, floor tile in magma furnaces, staring eyeball*, bubble bulb*, winter melon*, watermelon*

1. Row 08 (112-127)

| 112 
| Text, various creatures#

| 113 
| Text

| 114 
| Text, various creatures#

| 115 
| Text, various creatures#

| 116 
| Text, various creatures#

| 117 
| Text

| 118 
| Text, various creatures#, various stones*, south move indicator (adventure mode)

| 119 
| Text, various creatures#

| 120 
| Text, wear tags, Saltpeter*

| 121 
| Text

| 122 
| Text

| 123 
| Forbidden opening tag, tile in Jeweler's workshop, vermin, purring maggot#

| 124 
| Talc*, pipe sections, overlapping creatures animation

| 125 
| Forbidden closing tag, vermin, purring maggot alternate*

| 126 
| Unfinished rough stone road, flowing water, dirt road, farm plot under construction, sand, furrowed soil, blood smear, guts, Various creatures#, Magnetite*

| 127 
| Animal trap, low mountains on world map, part of mechanic's workshop, trunk$

1. Row 09 (128-143)

| 128 
| Text, Mechanisms

| 129 
| Text

| 130 
| Text

| 131 
| Text

| 132 
| Text, Angels

| 133 
| Text

| 134 
| Text

| 135 
| Text, Totems

| 136 
| Text

| 137 
| Text, military elves

| 138 
| Text

| 139 
| Text, Pedestal*

| 140 
| Text, Elven forest retreat

| 141 
| Text

| 142 
| Text, Angels

| 143 
| Text, Figurines, shrines on travel map

1. Row 10 (144-159)

| 144 
| Text, altars

| 145 
| Toys, hamlets on world map

| 146 
| Coffers, quivers, backpacks, hamlets on world map

| 147 
| Text, Cauldrons*

| 148 
| Text, Rings

| 149 
| Text, Unactivated levers, Various creatures#

| 150 
| Text, Buckets

| 151 
| Text

| 152 
| Text, Valley herb*

| 153 
| Bracelets, wheelbarrows*

| 154 
| Military Humans

| 155 
| Hatch covers¢, musical instrument pieces

| 156 
| Various stones*, most unmined ores*,

| 157 
| Cave lobster*

| 158 
| Stepladder*, largest forest retreat ruins

| 159 
| Rope reed*, splints, arrow bamboo*, golden bamboo*, hedge bamboo*
| 1. Row 11 (160-175)

| 160 
| Text

| 161 
| Text

| 162 
| Text, Activated levers

| 163 
| Text

| 164 
| Text, Bogeyman

| 165 
| Night creatures

| 166 
| dark pit ruins

| 167 
| Cloth, dark pit

| 168 
| Musical Instruments

| 169 
| Withered plants*, wormy tendril*

| 170 
| wormy tendril*

| 171 
| | 172 
| Roc nests, roots$, branches$

| 173 
| Flask, waterskin, Pouch

| 174 
| Tail of Ballista arrow facing west, item with decoration tags

| 175 
| Tail of Ballista arrow facing east, item with decoration tags

1. Row 12 (176-191)

| 176&nbsp;
| Partially dug rock, various flows (miasma, cave-in dust, steam, smoke, etc.), Fishery, fog on travel map, Semi-molten Rock, various stones*, various soils*,  Workshop wall tiles (craftdwarf's, bowyer's, mason's, mechanic's, jeweler's, clothier's, kitchen, and leather works), fallen leaves, vermin swarm

| 177&nbsp;
| Partially dug rock, various flows (miasma, cave-in dust, steam, smoke, etc.), side tiles for catapult, window, fog on travel map, various stones*, various kinds of soil*, fallen leaves, vermin swarm

| 178&nbsp;
| Partially dug rock, various flows (miasma, cave-in dust, steam, smoke, etc.), floor tile for ice, tanner's shop, butcher's shop, Wagon body, fog on travel map, various kinds of stones*, various kinds of soil*, sky$, fallen leaves

| 179&nbsp;
| Overworld rivers, well chain/rope, bolts in flight, rotating horizontal axles, branches$, active EW water wheel, active windmill blade, upright weapon trap

| 180&nbsp;
| Overworld rivers, top-right tile for Loom, branches$, Glumprong forests*

| 181&nbsp;
| Blood thorn trees*, bridges, catapult tile, tracks$

| 182&nbsp;
| Branches$, east roller

| 183&nbsp;
| Ends of smooth walls

| 184&nbsp;
| Ends of smooth walls

| 185&nbsp;
| Smooth/constructed walls, tracks$, trunk$

| 186&nbsp;
| Smooth/constructed walls, bridges, wooden doors¢, center catapult tile, center Ballista tile, axles, tracks$, fortress walls on travel map, trunk$, NS water wheel, windmill blade

| 187&nbsp;
| Smooth/constructed walls, bridges, tracks$, trunk$

| 188&nbsp;
| Smooth/constructed walls, bridges, tracks$, trunk$

| 189&nbsp;
| Ends of smooth walls

| 190&nbsp;
| Ends of smooth walls

| 191&nbsp;
| Overworld rivers, branches$, northeast move indicator (adventure mode)

1. Row 13 (192-207)

| 192&nbsp;
| Overworld rivers/Roads, branches$, southwest move indicator (adventure mode)

| 193&nbsp;
| Overworld rivers/Roads, branches$

| 194&nbsp;
| Overworld rivers/Roads, crutches, branches$

| 195&nbsp;
| Overworld rivers/Roads, top-left tile for Loom, branches$

| 196&nbsp;
| Overworld rivers/Roads, bolts in flight, rotating axles, branches$, active NS water wheel, active windmill blade

| 197&nbsp;
| Doors¢, overworld rivers/Roads, floor detailing/engraving in progress, branches$

| 198&nbsp;
| Bridges, trees in winter, (un)dead trees*, Saguaro*, catapult tile, tracks$, branches$

| 199&nbsp;
| branches$, west roller

| 200&nbsp;
| Smooth/constructed walls, bridges, tracks$, fortress walls on travel map, trunk$

| 201&nbsp;
| Smooth/constructed walls, bridges, tracks$, fortress walls on travel map, trunk$

| 202&nbsp;
| Smooth/constructed walls, tracks$, trunk$

| 203&nbsp;
| Smooth/constructed walls, tracks$, fortress walls on travel map, trunk$

| 204&nbsp;
| Smooth/constructed walls, tracks$, trunk$

| 205&nbsp;
| Smooth/constructed walls, bridges, planted crops, center catapult tile, center Ballista tile, axles, tracks$, fortress walls on travel map, trunk$, EW water wheel, windmill blade

| 206&nbsp;
| Smooth/constructed walls, bridges, fortifications, (flashing) wall detailing/engraving/fortifying in progress, tracks$, trunk$

| 207&nbsp;
| Tail of Ballista arrow facing north, screw press building, branches$, south roller

1. Row 14 (208-223)

| 208 
| Bridges, catapult tile, tracks$

| 209 
| Table, tail of Ballista arrow facing south, branches$, north roller

| 210 
| Chairs, bridges, catapult tile, farmer's workshop bottom-middle tile, tracks$

| 211 
| Ends of smooth walls

| 212 
| Ends of smooth walls

| 213 
| Ends of smooth walls

| 214 
| Ends of smooth walls

| 215 
| Wooden floodgates, bone floodgates, wall grates

| 216 
| Door designation

| 217 
| Overworld rivers, branches$, southeast move indicator (adventure mode)

| 218 
| Overworld rivers, branches$, northwest move indicator (adventure mode)

| 219 
| Interface window border, trade depot tile, ice wall and dig-designated tiles, Mist

| 220 
| Ballista tile, Siege engine parts

| 221 
| Ballista tile

| 222 
| Ballista tile

| 223 
| Ballista tile

1. Row 15 (224-239)

| 224&nbsp;
| Various fish#, top-center fishery tile, meat, altocumulus clouds on travel map

| 225&nbsp;
| Leather, cumulus clouds on travel map

| 226&nbsp;
| Weight symbol, various forest trees, tropical forests

| 227&nbsp;
| Cabinet, Display cases÷*, dark fortresses

| 228&nbsp;
| Trap component

| 229&nbsp;
| Anvil, metalsmith's and magma forge bottom-middle tile, jugs*

| 230&nbsp;
| Crown, ruins on world map, shop signs (adventure mode)

| 231&nbsp;
| Tree sapling*, pig tail*, cave wheat*, Longland grass*, rat weed*, hide root*, muck root*, blade weed*, sliver barb*, shrubland, arrow bamboo*, golden bamboo*, hedge bamboo*

| 232&nbsp;
| Sweet pod*, bloated tuber*, kobold bulb*, traction benches, (Large) pots*

| 233&nbsp;
| Beds, Puddingstone*

| 234&nbsp;
| Statues, dwarven cities on map, sea nettle jellyfish*

| 235&nbsp;
| Earrings, kennel tile

| 236&nbsp;
| Boulder, dry brook, middle-right butcher's shop tile, various stones*, sea foam, images of clouds, fortress gates on travel map, honeycomb*, scrolls*

| 237&nbsp;
| Thread, loom bottom left tile, farmer's workshop bottom right tile

| 238&nbsp;
| Bowyer's workshop middle-right tile

| 239&nbsp;
| Hills on world map, slab building

1. Row 16 (240-255)

| 240&nbsp;
| Bars, exceptional quality tags, activity zones, metal doors¢, floor bars, track stops, cirrus clouds on travel map, hamlets on world map, quire*, bookcase*÷

| 241&nbsp;
| Unfinished road

| 242&nbsp;
| Debris (spent ammo, ballista bolts, and catapult stones), ashes, wormy tendril*

| 243&nbsp;
| Debris (spent ammo, ballista bolts, and catapult stones), ashes, wormy tendril*

| 244&nbsp;
| swamps on world map, Willow forest/swamp*

| 245&nbsp;
| sheets

| 246&nbsp;
| Barrel¢, screw pump, upper left tile of still, center tile of ashery, upper left tile of kitchen, scroll rollers*, book binding*

| 247&nbsp;
| Rough stone road or bridge, water, magma, snow, glob (fat/tallow), farm plot, furrowed soil, vomit, blood pools, sea foam, sand, various stones*

| 248&nbsp;
| Sea foam, eggs, staring eyeball*, bubble bulb*, Bowl, Mortar, dark pits on world map

| 249&nbsp;
| Vermin*, Boulders at lower elevation, trees at lower elevation, tundra on world map, move indicator frame 2 (adventure mode)

| 250&nbsp;
| Seeds, micro-vermin, open space, terrain at lower elevation, plants at lower elevation, tundra on world map, move indicator frame 1 (adventure mode)

| 251&nbsp;
| Weapon racks, badlands in main map, check mark (selecting production materials, confirmed items on manager window)

| 252&nbsp;
| Savanna, marsh, grassland, badlands

| 253&nbsp;
| Body parts, vermin remains

| 254&nbsp;
| Blocks, minecarts*÷, vaults on world map, human houses/shops on travel map, progress bars, move indicator frame 3 (adventure mode)

| 255&nbsp;
| 1. Detailed use list by type
1. Creatures
1. Main creature tiles
This is a list of tiles used by creatures. In all cases the tile can be changed in the raws, and a graphic can be assigned.

001 
(Civilian) dwarves

011 
Cuttlefish Nautilus, Squid

015 
Pond turtle

016 
manta ray

037 
Floating guts

042 
Creepy crawler

064 
berserk dwarf, adventurer, dwarven merchants, dwarven caravan guards, dwarven diplomat

065 
Alligator, Alligator man, Anaconda, Anaconda man, Giant aardvark, Giant adder, Giant albatross, Giant alligator, Giant anaconda, Giant anole, Giant armadillo, Giant axolotl, Giant aye-aye

066 
Beak dog, Black bear, Black bear man, Blind cave bear, Giant badger, Giant barn owl, Giant bat, Giant beaver, Giant beetle, Giant black bear, Giant bluejay, Giant bobcat, Giant bushtit, Giant buzzard, Giant grizzly bear, Giant honey badger, Giant monarch butterfly, Giant polar bear, Giant sloth bear, Giant wild boar, Grizzly bear, Grizzly bear man, Polar bear, Polar bear man, Sloth bear, Sloth bear man, Wild boar, Wild boar man

067 
Bronze colossus, Cave crocodile, Centaur, Chimera, Coelacanth, Cow, Cyclops, Giant capuchin, Giant capybara, Giant cardinal, Giant cassowary, Giant cave swallow, Giant chameleon, Giant cheetah, Giant chinchilla, Giant chipmunk, Giant coati, Giant cockatiel, Giant cougar, Giant coyote, Giant crab, Giant crow, Giant cuttlefish, Giant horseshoe crab, Giant one-humped camel, Giant saltwater crocodile, Giant two-humped camel, Magma crab, One-humped camel, One-humped camel man, Saltwater crocodile, Saltwater crocodile man, Two-humped camel, Two-humped camel man, Voracious cave crawler

068 
Cave dragon, Deer, Donkey, Dragon, Draltha, Giant deer, Giant dingo, Giant dragonfly

069 
Elephant, Elephant man, Elk, Elk bird, Elk man, Emu, Emu man, Ettin, Giant eagle, Giant echidna, Giant elephant, Giant elk, Giant emu

070 
Giant firefly, Giant fly, Giant fox, Giant green tree frog

071 
Giant, Giant gazelle, Giant gila monster, Giant giraffe, Giant grackle, Giant grasshopper, Giant groundhog, Giant grouper, Giant leopard gecko, Giant mountain goat, Giraffe, Giraffe man, Gorilla, Green devourer, Griffon

072 
Giant hamster, Giant hare, Giant harp seal, Giant hedgehog, Giant hippo, Giant hornbill, Giant hyena, Harp seal, Hippo, Hippo man, Horse, Hydra

073 
Giant ibex, Giant iguana, Giant impala

074 
Giant jackal, Giant jaguar, Giant jumping spider, Jabberer, Jaguar, Jaguar man

075 
Giant kakapo, Giant kangaroo, Giant kea, Giant kestrel, Giant king cobra, Giant kingsnake, Giant kiwi, Giant koala, Kangaroo, Kangaroo man

076 
Giant gray langur, Giant leech, Giant leopard, Giant leopard seal, Giant lion, Giant lion tamarin, Giant lizard, Giant loon, Giant lorikeet, Giant louse, Giant lynx, Giant masked lovebird, Giant peach-faced lovebird, Leopard seal, Leopard seal man, Lion, Lion man, Llama

077 
Amethyst man, Blizzard man, Blood man, Fire man, Gabbro man, Giant hoary marmot, Giant magpie, Giant mandrill, Giant mantis, Giant mink, Giant mongoose, Giant monitor lizard, Giant moose, Giant mosquito, Giant moth, Giant muskox, Giant rhesus macaque, Giant spider monkey, Iron man, Magma man, Merperson, Minotaur, Molemarian, Monitor lizard, Monitor lizard man, Moose, Moose man, Mud man, Mule, Muskox, Muskox man, Sea monster

078 
Giant narwhal, Giant nautilus, Narwhal, Narwhal man, Nightwing

079 
Blind cave ogre, Giant great horned owl, Giant ocelot, Giant octopus, Giant olm, Giant opossum, Giant orca, Giant oriole, Giant osprey, Giant ostrich, Giant otter, Giant snowy owl, Ogre, Orangutan, Orca, Orca man, Ostrich, Ostrich man

080 
Giant grey parrot, Giant pangolin, Giant parakeet, Giant penguin, Giant peregrine falcon, Giant platypus, Giant porcupine, Giant puffin, Giant red panda, Gigantic panda, Panda, Panda man

082 
Giant raccoon, Giant rat, Giant raven, Giant red-winged blackbird, Giant rhinoceros, Giant roach, Reacher, Reindeer, Rhinoceros, Rhinoceros man, Roc, Rutherer

083 
Basking shark, Blue shark, Bull shark, Elephant seal, Elephant seal man, Giant bark scorpion, Giant black mamba, Giant brown recluse spider, Giant bushmaster, Giant cave spider, Giant copperhead snake, Giant elephant seal, Giant flying squirrel, Giant gray squirrel, Giant moon snail, Giant python, Giant rattlesnake, Giant red squirrel, Giant skink, Giant skunk, Giant sloth, Giant slug, Giant snail, Giant sparrow, Giant sponge, Giant stoat, Giant swan, Giant white stork, Gigantic squid, Great white shark, Hammerhead shark, Longfin mako shark, Nurse shark, Python, Python man, Sasquatch, Sea serpent, Shortfin mako shark, Spotted wobbegong, Tiger shark

084 
Alligator snapping turtle, Giant cave toad, Giant desert tortoise, Giant pond turtle, Giant snapping turtle, Giant tapir, Giant thrips, Giant tick, Giant tiger, Giant toad, Giant tortoise, Giant tortoise man, Gigantic tortoise, Tapir, Tapir man, Tiger, Tiger man, Troll

085 
Human, Unicorn

086 
Giant vulture

087 
Giant earthworm, Giant sperm whale, Giant walrus, Giant warthog, Giant weasel, Giant wolf, Giant wolverine, Giant wombat, Giant wren, Sperm whale, Sperm whale man, Wagon, Walrus, Walrus man, Warthog, Warthog man, Water buffalo, Whale shark

089 
Yak, Yeti

097 
Aardvark, Aardvark man, Adder, Adder man, Albatross, Albatross man, Alpaca, Amphibian man, Anole man, Antman, Armadillo, Armadillo man, Axolotl man, Aye-aye, Aye-aye man

098 
Badger, Badger man, Barn owl, Barn owl man, Bat man, Beaver, Beaver man, Beetle man, Bluejay man, Bobcat, Bobcat man, Bonobo, Bugbat, Bushtit man, Buzzard, Buzzard man, Foul blendec, Great barracuda, Honey badger, Honey badger man, Monarch butterfly man

099 
Capuchin, Capuchin man, Capybara, Capybara man, Cardinal man, Cassowary, Cassowary man, Cat, Cavy, Chameleon man, Cheetah, Cheetah man, Chicken, Chimpanzee, Chinchilla, Chinchilla man, Chipmunk man, Coati, Coati man, Cockatiel man, Cougar, Cougar man, Coyote, Coyote man, Crab, Crab man, Crow man, Crundle, Cuttlefish man, Horseshoe crab, Horseshoe crab man

100 
Damselfly man, Deer man, Dingo, Dingo man, Dog, Dragonfly man, Drunian, Duck

101 
Creeping eye, Eagle, Eagle man, Echidna, Echidna man, Elf

102 
Cave fish man, Cave floater, Firefly man, Fly man, Fox, Fox man, Green tree frog man

103 
Bilou, Black-crested gibbon, Black-handed gibbon, Dark gnome, Gazelle, Gazelle man, Gila monster, Gila monster man, Goat, Goblin, Goose, Gorlak, Grackle man, Grasshopper man, Gray gibbon, Gremlin, Grimeling, Groundhog, Groundhog man, Guineafowl, Leopard gecko man, Longnose gar, Mountain gnome, Mountain goat, Mountain goat man, Pileated gibbon, Silvery gibbon, White-browed gibbon, White-handed gibbon

104 
Hamster man, Hare, Hare man, Harp seal man, Harpy, Hedgehog man, Hornbill, Hornbill man, Hungry head, Hyena, Hyena man

105 
Fire imp, Ibex, Ibex man, Iguana, Iguana man, Impala, Impala man

106 
Jackal, Jackal man, Jumping spider man

107 
Kakapo, Kakapo man, Kea, Kea man, Kestrel, Kestrel man, King cobra, King cobra man, Kingsnake, Kingsnake man, Kiwi, Kiwi man, Koala, Koala man, Kobold

108 
Gray langur, Gray langur man, Leech man, Leopard, Leopard man, Lion tamarin man, Lizard man, Loon, Loon man, Lorikeet man, Louse man, Lynx, Lynx man, Masked lovebird man, Peach-faced lovebird man

109 
Giant mole, Hoary marmot, Hoary marmot man, Magpie man, Mandrill, Mandrill man, Manera, Mantis man, Mink, Mink man, Mongoose, Mongoose man, Mosquito man, Moth man, Mussel, Plump helmet man, Rhesus macaque, Rhesus macaque man, Spider monkey, Spider monkey man

110 
Naked mole dog, Nautilus man

111 
Cave blob, Flesh ball, Great horned owl, Great horned owl man, Ocelot, Ocelot man, Octopus, Octopus man, Olm man, Opossum, Opossum man, Oriole man, Osprey, Osprey man, Otter man, Oyster, River otter, Sea otter, Snowy owl, Snowy owl man

112 
Blue peafowl, Emperor penguin, Grey parrot, Grey parrot man, Little penguin, Pangolin, Pangolin man, Parakeet man, Penguin, Penguin man, Peregrine falcon, Peregrine falcon man, Pig, Platypus, Platypus man, Pond grabber, Porcupine, Porcupine man, Puffin, Puffin man, Red panda, Red panda man

114 
Large rat, Rabbit, Raccoon, Raccoon man, Rat man, Raven, Raven man, Red-winged blackbird man, Reptile man, Roach man, Rodent man

115 
Angelshark, Bark scorpion man, Black mamba, Black mamba man, Blacktip reef shark, Brown recluse spider man, Bushmaster, Bushmaster man, Cave swallow man, Copperhead snake, Copperhead snake man, Flying squirrel man, Frill shark, Gray squirrel man, Helmet snake, Moon snail man, Rattlesnake, Rattlesnake man, Red squirrel man, Satyr, Serpent man, Sheep, Siamang, Skink man, Skunk, Skunk man, Sloth, Sloth man, Slug man, Snail man, Sparrow man, Spiny dogfish, Sponge, Sponge man, Squid man, Stoat, Stoat man, Strangler, Swan, Swan man, White stork, White stork man, Whitetip reef shark

116 
Common snapping turtle, Desert tortoise, Desert tortoise man, Pond turtle man, Snapping turtle man, Thrips man, Tick man, Toad man, Troglodyte, Turkey

118 
Vulture, Vulture man

119 
Ice wolf, Weasel, Weasel man, Wolf, Wolf man, Wolverine, Wolverine man, Wombat, Wombat man, Worm man, Wren man

123 
Purring maggot

126 
Brook lamprey, Conger eel, Hagfish, Knuckle worm, Leech, Sea lamprey, Slug, Worm

149 
Bat ray, Common skate, Stingray, Thornback ray

157 
Cave lobster

224 
Anchovy, Banded knifefish, Black bullhead, Bluefin tuna, Bluefish, Brown bullhead, Carp, Cave fish, Char, Clown loach, Clownfish, Cod, Flounder, Glasseye, Guppy, Hake, Halibut, Herring, Lungfish, Mackerel, Marlin, Milkfish, Ocean sunfish, Opah, Perch, Pike, Rainbow trout, Sailfin molly, Salmon, Seahorse, Shad, Sole, Spotted ratfish, Steelhead trout, Sturgeon, Swordfish, Tigerfish, White-spotted puffer, Yellow bullhead

234 
Sea nettle jellyfish
1. Vermin
These creatures are classified as "vermin" and cannot have their tiles changed.

249 
Anole, Ant, Axolotl, Bark scorpion, Bat, Blue jay, Brown recluse spider, Bushtit, Cap hopper, Cardinal, Cave spider, Cave swallow, Chameleon, Chipmunk, Cockatiel, Crow, Damselfly, Demon rat, Dragonfly, Fairy, Fire snake, Firefly, Fluffy wambler, Flying squirrel, Fox squirrel, Giant damselfly, Grackle, Gray squirrel, Green tree frog, Hamster, Hedgehog, Large roach, Leopard gecko, Lion tamarin, Lizard, Lorikeet, Magpie, Masked lovebird, Moghopper, Moon snail, Olm, Oriole, Parakeet, Peach-faced lovebird, Phantom spider, Rat, Red squirrel, Red-winged blackbird, Skink, Snail, Sparrow, Toad, Two-legged rhino lizard, Wren

250 
Acorn fly, Beetle, Blood gnat, Bumblebee, Fly, Grasshopper, Honey bee, Jumping spider, Louse, Mantis, Mosquito, Pixie, Termite, Thrips, Tick

1. Additional Tiles Used by Creatures
Some creature raw specify secondary tiles. They are listed here

**Tile !! Usage !! Change Properties

| 002 
| Military dwarves
| can be removed, reassigned, or overridden by graphics

| 009 
| creeping eye glowing eye
| can be reassigned

| 034 
| kobold, goblin, and blizzard man glowing eyes
| cannot be removed or reassigned without changing behavior

| 039 
| one eyed creatures with GLOWTILE " (kobold, goblins, and blizzard men)
| tile cannot be changed

| 125 
| purring maggot alternate
| can be removed or reassigned

| 137 
| military elves
| can be removed, reassigned, or overridden by graphics

| 154 
| Military Humans
| can be removed, reassigned, or overridden by graphics

1. Plants
1. Trees on map
The tiles can all be changed in the raws.

005&nbsp;
Acacia, Alder, Apple, Apricot, Birch, Cherry, Feather tree, Mangrove, Maple, Peach, Pear, Tea, Sand pear, Plum

006&nbsp;
Almond, Hazel, Oak, Mahogany, Chestnut, Ash, Kumquat, Custard-apple, Orange, Desert lime, Finger lime, Round lime, Walnut, Pomelo, Citron, Olive , Macadamia, Coffee, Bayberry, Bitter orange, Lime, Lychee, Pecan, Persimmon

020&nbsp;
Highwood

023&nbsp;
Cedar

024&nbsp;
Pine, Ginkgo, Larch

180&nbsp;
Glumprong

181&nbsp;
Blood thorn

198&nbsp;
Saguaro

226&nbsp;
abaca, candlenut, mango tree, rubber tree, cacao tree, Coconut palm, kapok, Avocado, Banana, Carambola, Cashew, Date palm, Durian, Guava, Papaya, Paradise nut, Pomegranate, Rambutan

244&nbsp;
Willow

1. Trees in game

| 035 
| smoothed branches in elven forest retreats

| 037&nbsp;
| various fruits,  various buds

| 042&nbsp;
| chestnut fruit, catkins

| 059 
| twigs

| 127&nbsp;
| trunk cap

| 172&nbsp;
| roots, branches with leaves

| 231&nbsp;
| Tree sapling

| trunk
| 010&nbsp;
| 079&nbsp;
| 185&nbsp;
| 186&nbsp;
| 187&nbsp;
| 188&nbsp;
| 200&nbsp;
| 201&nbsp;
| 202&nbsp;
| 203&nbsp;
| 204&nbsp;
| 205&nbsp;
| 206&nbsp;

| branches
| 179&nbsp;
| 180&nbsp;
| 182&nbsp;
| 191&nbsp;
| 192&nbsp;
| 193&nbsp;
| 194&nbsp;
| 195&nbsp;
| 196&nbsp;
| 197&nbsp;
| 198&nbsp;
| 199&nbsp;
| 207&nbsp;
| 209&nbsp;
| 217&nbsp;
| 218&nbsp;

1. Crops

| 003&nbsp;
| Dimple cups

| 005&nbsp;
| Quarry bushes

| 006&nbsp;
| Plump helmets,

| 058&nbsp;
| strawberry, prickle berry, fisher berry, sun berry

| 152&nbsp;
| Valley herb

| 159&nbsp;
| Rope reed

| 231&nbsp;
| pig tail, cave wheat, Longland grass, rat weed, hide root, muck root, blade weed, sliver barb

| 232&nbsp;
| Sweet pod, bloated tuber, kobold bulb

1. Garden plants

| 005&nbsp;
| blossoms

| 006&nbsp;
| leaves

| 037&nbsp;
| all kinds of berries

| 058&nbsp;
| all kinds of berries

| 111&nbsp;
| winter melon, watermelon

1. Grasses
Grass tiles can be changed in the plant raws. Most grasses have 4 tiles that are alternatively used.

| 005 
| flowers on baby toes succulent, cloudberry, cottongrass, marsh thistle, meadowsweet. mountain avens, pebble plant, and rush.

| 009 
| staring eyeball, bubble bulb

| 039 
| all other grasses

| 044 
| all other grasses

| 046 
| all other grasses

| 079&nbsp;
| bubble bulb, staring eyeball

| 096&nbsp;
| all other grasses

| 111&nbsp;
| bubble bulb, staring eyeball

| 159&nbsp;
| arrow bamboo, golden bamboo, hedge bamboo

| 169 
| wormy tendril

| 170 
| wormy tendril

| 231&nbsp;
| arrow bamboo, golden bamboo, hedge bamboo

| 242&nbsp;
| wormy tendril

| 243&nbsp;
| wormy tendril

| 248&nbsp;
| staring eyeball, bubble bulb

1. Unmined inorganic material
The tiles can all be changed in the raws.
1. Stones

| 015 
| Bituminous coal

| 034 
| Calcite, Hornblende

| 035 
| Sandstone, Rock salt, Basalt, Gypsum

| 037 
| Siltstone, Slate, Brimstone, Kimberlite, Bismuthinite, Realgar, Stibnite, Marcasite, Olivine, Orthoclase, Microcline, Petrified wood, Brimstone, Pyrolusite

| 039 
| Claystone, Rhyolite, Periclase

| 042 
| Lignite, Pitchblende

| 043 
| Bauxite

| 045 
| Cryolite, Orpiment, Satinspar, Phyllite, Quartzite

| 046 
| Dacite, Ilmenite, Shale

| 059 
| Selenite

| 061 
| Chert, Gneiss, Sylvite, Chromite, Kaolinite

| 094 
| Alabaster

| 096 
| Dolomite, Schist, Alunite, Rutile, Borax

| 111 
| Graphite

| 118 
| Anhydrite, Mica

| 120 
| Saltpeter

| 124 
| Talc

| 156 
| Cinnabar, Cobaltite

| 176&nbsp;
| Jet, Chalk, Diorite

| 177&nbsp;
| Gabbro, Obsidian

| 178&nbsp;
| Marble, Limestone, Granite

| 233&nbsp;
| Puddingstone

| 236&nbsp;
| Andesite, Conglomerate

| 247 
| Mudstone, Serpentine

1. Ores

| 037 
| Bismuthinite

| 094 
| Native aluminum

| 126 
| Magnetite

| 156 
| Adamantine, Cassiterite, Galena, Garnierite, Hematite, Horn silver, Limonite, Malachite, Native copper, Native gold, Native platinum, Native silver, Sphalerite, Tetrahedrite

1. Gems
015  is used by all gems

1. Soil

| 176&nbsp;
| Loam, Peat, Sandy clay loam, Sandy loam, Silty clay loam, Pelagic clay, Red sand, Sand (tan)

| 177&nbsp;
| Loamy sand, Silt loam, Siliceous ooze, Calcareous ooze, Clay loam, Sandy clay

| 178&nbsp;
| Silt, Black sand, White sand, Yellow sand, Clay, Silty clay, Fire clay

1. Characters used in text and interface
Changes to these may make text look strange or be difficult to understand, unless you are using the TrueType font feature.

- " ! _ + , - . 0 1 2 3 4 5 6 7 8 9 /
- A B C D E F G H I J K L M N O P Q R S T U V W X Y Z
- a b c d e f g h i j k l m n o p q r s t u v w x y z
- 32 (Space); 219█; 254■; ↑ ↓ → ← (Bridge direction indicators); ♂ ♀ ☼ Γ √;
- Quality: - + ≡ * ☼ « »
- Brackets: ( ) < > { } [ ]

1. Alphabets
Accented characters are used for names.

Dwarven: aáàâäåbcdeéèêëfghiíìîïklmnoóòôörstuúùûvz

Elven: abcçdeéèfghiíìklmnoóòpqrstuúùvwyz

Human: aábcdefghijklmnñopqrstuvwxyz

Goblin: aâäåbdeêëghklmnoôöprstuûxz

In total, the accented characters used are: áàâäåçéèêëíìîïñóòôöúùûÿ

1. No known use
These are ideal for using to change tiles in the raw data or init.txt.

↕ ∟ ↔ ½ 255

<!-- ☺ ☻ ♥ ♦ ♣ ♠ • ◘ ○ ◙ ♂ ♀ ♪ ♫ ☼ ► ◄ ↕ ‼ ¶ § ▬ ↨ ↑ ↓ → ← ∟ ↔ ▲ ▼ ! " # $ % & ' ( ) * + , - . / 0 1 2 3 4 5 6 7 8 9 : ; < = > ? @ A B C D E F G H I J K L M N O P Q R S T U V W X Y Z [ \ ] ^ _ ` a b c d e f g h i j k l m n o p q r s t u v w x y z { | } ~ ⌂ Ç ü é â ä à å ç ê ë è ï î ì Ä Å É æ Æ ô ö ò û ù ÿ Ö Ü ¢ £ ¥ ₧ ƒ á í ó ú ñ Ñ ª º ¿ ⌐ ¬ ½ ¼ ¡ « » ░ ▒ ▓ │ ┤ ╡ ╢ ╖ ╕ ╣ ║ ╗ ╝ ╜ ╛ ┐ └ ┴ ┬ ├ ─ ┼ ╞ ╟ ╚ ╔ ╩ ╦ ╠ ═ ╬ ╧ ╨ ╤ ╥ ╙ ╘ ╒ ╓ ╫ ╪ ┘ ┌ █ ▄ ▌ ▐ ▀ α ß Γ π Σ σ µ τ Φ Θ Ω δ ∞ φ ε ∩ ≡ ± ≥ ≤ ⌠ ⌡ ÷ ≈ ° ∙ · √ ⁿ ² ■ -->

ru:Tilesets
