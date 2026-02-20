# Color

: 
: 
: 
180px|right*Dwarf Fortress* can use roughly 8424 **colors** to give many tiles such as foregrounds, backgrounds and sprites different colors. These colors make up the color scheme. Which of these colors are assigned to a given tile is often decided by values in its raw file. Whether a pixel shows foreground, background, black or anything in between is influenced by its brightness and opacity. These colors are shown at the right:

The original game used a simplistic 16-color palette, with 8 of those colors: black, blue, green, cyan, red, purple, yellow, grey, and a lighter version of those colors creating a total of 16. The game also has an option to use the classic ASCII visuals, mimicking the classic version of the game by using 16 colors. Even with the updated graphics turned on, the text in the GUI still references the color scheme. Color is also used to express various information, from a dwarf's profession, to the natural color of a terrain feature, to the material an item is made of.

Some sprite sheets contain their own dedicated color palettes.
1. Overview
1. The tileset influences color display
<div style="margin-bottom:-26px;"> <!-- This undoes the weird space creation that the modding template causes. -->

right
300px|thumb|right
In the simplest case, a pixel on a tileset is either white (foreground) or transparent* (background). However, black, and anything in between is possible as well (even color):
- a white pixel will show the foreground color
- a transparent* pixel will show the background color
- a black pixel will stay black	
The darker a white pixel is (i.e. a shade of gray), the darker the foreground color will be displayed. Similarly, a black pixel with lower opacity will result in a darker background color. 
A partially transparent, non-black pixel shows both the background and foreground color.

*magenta for .bmp files.

1. Colors are assigned based on material and other raw values
To decide which colors to use for a tile in ASCII mode, DF looks at raw values for that object (color value or color token) and selects a foreground and background color from the 16 colors in the color scheme. When a color value is defined, it directly picks it from the 16. When instead a color token is defined, the game compares the color token definition to all 16 colors in the color scheme and picks the closest match.

For tiles in graphics mode, it instead uses a raw-defined palette. The default palette image is shown above. It checks for each color in the row defined by the PALETTE_DEFAULT token--in this case, the first row--and then maps it to the corresponding color in the same column, based on the STATE_COLOR of the object that the tile being printed corresponds to. For the vanilla raws, this is all in alphabetical order. New palettes and colors can be defined in the same way.

<!-- TODO
clearly define somewhere when and how the article refers to background/foreground one one hand and pixels on the tileset on the other hand.
1. How the tileset influences color display
TODO: look through commented out section of tileset page, correct it, update it, etc.
adapt as section here.

go into more detail about color in tilesets.

1. tricks (<- keep short, focus on tools/facts, not applications; those go into future "custom tileset" page)
-tiles that are used for several things, one of which uses a black background others that don't can display different things:
-mention walls/engravings as example.: smoothed walls use foreground color of material and black background. Engraved walls use foreground color and dark foreground color as background (actually, verify that. Isn't info on that in the old section right below?). So all black pixels (on the tileset) will be "invisible" on smooth walls (because the background is also black), but with engraved walls having a background color, you can see a pattern.
-Other ("advanced") example with transparency: 50%opacity white pixels next to 100%opacity 50% gray pixels
-other tricks I'm forgetting? check through old tileset threads on bay12
insert images showing the examples

-->
1. How colors are assigned
Colors of Status icons, professions, text and the interface in general are hardcoded. Items, furniture, constructions, and geographic features get the color of their material. Dyes and material contaminants use color tokens.
1. Wall and floor color
thumb|400px|[[Phyllite (to the left) has  and .  The white sand present has  and so the actual floor color is ``7:1`` (white).]]

While the foreground, background and brightness shown in the RAW files will be applied to walls, the mineral's "secondary" color will end up different.  Here is how it works:
- If the  tag is specified, it will use that color.  Note that the  tag only has foreground and brightness as arguments.
- If  is left out:
    - The background color is forced to 0 (effectively stripping it).
    - If the foreground color is 0, the game will display it as dark gray, color 8 (in other words, color 0 with brightness 1).
This is effective for stairs, floors, ramps, and constructions (in the case of stone).  When stone is engraved, it uses the material's  (which is the same as the  unless overridden).

1. Color values

Colors are primarily defined using the  or  tokens. The three arguments are:

1. Foreground color [0-7]
1. Background color [0-7]
1. Brightness of the foreground color [0 or 1]

The brightness of the background color is always 0.

By default*, the following 8 pairs of colors are displayed.  These are bright and dark shades of the primary colors, as well as black, white, and two grays:

| style="vertical-align: top; padding: 0" | 

**style="padding: 0.15em 0.4em; width: 3em" | Col.
**style="padding: 0.15em 0.4em; width: 3em" | Bri.
**style="padding: 0.15em 0.4em; width: 9em; text-align: left" | Name

| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em; text-align: left" | BLACK

| style="padding: 0.15em 0.4em" | 1
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em; text-align: left" | BLUE

| style="padding: 0.15em 0.4em" | 2
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em; text-align: left" | GREEN

| style="padding: 0.15em 0.4em" | 3
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em; text-align: left" | CYAN

| style="padding: 0.15em 0.4em" | 4
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em; text-align: left" | RED

| style="padding: 0.15em 0.4em" | 5
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em; text-align: left" | MAGENTA

| style="padding: 0.15em 0.4em" | 6
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em; text-align: left" | BROWN

| style="padding: 0.15em 0.4em" | 7
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em; text-align: left" | LGRAY

| style="vertical-align: top; padding: 0" | 

**style="padding: 0.15em 0.4em; width: 3em" | Col.
**style="padding: 0.15em 0.4em; width: 3em" | Bri.
**style="padding: 0.15em 0.4em; width: 9em; text-align: left" | Name
**style="padding: 0.15em 0.4em; width: 3em" | Alt.

| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 1
| style="padding: 0.15em 0.4em; text-align: left" | DGRAY
| style="padding: 0.15em 0.4em" | 8

| style="padding: 0.15em 0.4em" | 1
| style="padding: 0.15em 0.4em" | 1
| style="padding: 0.15em 0.4em; text-align: left" | LBLUE
| style="padding: 0.15em 0.4em" | 9

| style="padding: 0.15em 0.4em" | 2
| style="padding: 0.15em 0.4em" | 1
| style="padding: 0.15em 0.4em; text-align: left" | LGREEN
| style="padding: 0.15em 0.4em" | 10

| style="padding: 0.15em 0.4em" | 3
| style="padding: 0.15em 0.4em" | 1
| style="padding: 0.15em 0.4em; text-align: left" | LCYAN
| style="padding: 0.15em 0.4em" | 11

| style="padding: 0.15em 0.4em" | 4
| style="padding: 0.15em 0.4em" | 1
| style="padding: 0.15em 0.4em; text-align: left" | LRED
| style="padding: 0.15em 0.4em" | 12

| style="padding: 0.15em 0.4em" | 5
| style="padding: 0.15em 0.4em" | 1
| style="padding: 0.15em 0.4em; text-align: left" | LMAGENTA
| style="padding: 0.15em 0.4em" | 13

| style="padding: 0.15em 0.4em" | 6
| style="padding: 0.15em 0.4em" | 1
| style="padding: 0.15em 0.4em; text-align: left" | YELLOW
| style="padding: 0.15em 0.4em" | 14

| style="padding: 0.15em 0.4em" | 7
| style="padding: 0.15em 0.4em" | 1
| style="padding: 0.15em 0.4em; text-align: left" | WHITE
| style="padding: 0.15em 0.4em" | 15

::::*(* See color scheme for information about how to change the actual various colors as displayed.)*

Sometimes the color numbers are part of another token, e.g.  specifies the colors ``7:0:0`` for quarry bush leaves and ``0:0:1`` for wilted quarry bush leaves.

1. Values 8-15

If the brightness value is 1 or another nonzero number, it adds 8 to the foreground color. If the final value of the foreground or background is 8-15, it appears as a "bright" color. 

As these values can be manually typed in instead of using the brightness value, you can also give the background a bright color with this method. For example, for a white background color, add 8 to 7 = 15. For a light green background color, you add 8 to 2 = 10.

1. Color tokens

When in graphics mode, most things do not use color flags. Instead, they reference color tokens defined in ``descriptor_color_standard.txt``. Color tokens are referenced by their token name, e.g.  or . The defined RGB values are not displayed in-game; instead, it assigns colors in the sprite from the top row of the palette file (see Graphics#Palettes) to the row defined in ``data/vanilla/vanilla_descriptors_graphics/graphics/palette_default.txt``, or any user-defined palette objects.

The following colors are grouped according to their corresponding display color in ASCII mode. Hexadecimal color values are not used in the raws, but correspond to the RGB values that are. For further information, see the Wikipedia article on web colors.

| | + **DGRAY colors**

**style="text-align: center; padding: 0.15em 0.4em" | Token
**style="text-align: center; padding: 0.15em 0.4em" colspan="3" | RGB
**style="text-align: center; padding: 0.15em 0.4em" | Hex
**style="text-align: center; padding: 0.15em 0.4em" | Palette

| style="padding: 0.15em 0.4em; text-align: left" | BLACK
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | #000000
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | CLEAR
| style="padding: 0.15em 0.4em" | 128
| style="padding: 0.15em 0.4em" | 128
| style="padding: 0.15em 0.4em" | 128
| style="padding: 0.15em 0.4em" | #808080
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | GRAY
| style="padding: 0.15em 0.4em" | 128
| style="padding: 0.15em 0.4em" | 128
| style="padding: 0.15em 0.4em" | 128
| style="padding: 0.15em 0.4em" | #808080
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | TAUPE_GRAY
| style="padding: 0.15em 0.4em" | 139
| style="padding: 0.15em 0.4em" | 133
| style="padding: 0.15em 0.4em" | 137
| style="padding: 0.15em 0.4em" | #8B8589
| style="padding: 0.15em 0.4em" |

| | + **LGRAY colors**

**style="text-align: center; padding: 0.15em 0.4em" | Token
**style="text-align: center; padding: 0.15em 0.4em" colspan="3" | RGB
**style="text-align: center; padding: 0.15em 0.4em" | Hex
**style="text-align: center; padding: 0.15em 0.4em" | Palette

| style="padding: 0.15em 0.4em; text-align: left" | SILVER
| style="padding: 0.15em 0.4em" | 192
| style="padding: 0.15em 0.4em" | 192
| style="padding: 0.15em 0.4em" | 192
| style="padding: 0.15em 0.4em" | #C0C0C0
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | ASH_GRAY
| style="padding: 0.15em 0.4em" | 178
| style="padding: 0.15em 0.4em" | 190
| style="padding: 0.15em 0.4em" | 181
| style="padding: 0.15em 0.4em" | #B2BEB5
| style="padding: 0.15em 0.4em" |

| | + **WHITE colors**

**style="text-align: center; padding: 0.15em 0.4em" | Token
**style="text-align: center; padding: 0.15em 0.4em" colspan="3" | RGB
**style="text-align: center; padding: 0.15em 0.4em" | Hex
**style="text-align: center; padding: 0.15em 0.4em" | Palette

| style="padding: 0.15em 0.4em; text-align: left" | WHITE
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | #FFFFFF
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | BEIGE
| style="padding: 0.15em 0.4em" | 245
| style="padding: 0.15em 0.4em" | 245
| style="padding: 0.15em 0.4em" | 220
| style="padding: 0.15em 0.4em" | #F5F5DC
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | IVORY
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 240
| style="padding: 0.15em 0.4em" | #FFFFF0
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | LAVENDER
| style="padding: 0.15em 0.4em" | 230
| style="padding: 0.15em 0.4em" | 230
| style="padding: 0.15em 0.4em" | 250
| style="padding: 0.15em 0.4em" | #E6E6FA
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | LAVENDER_BLUSH
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 240
| style="padding: 0.15em 0.4em" | 245
| style="padding: 0.15em 0.4em" | #FFF0F5
| style="padding: 0.15em 0.4em" |

| | + **RED colors**

**style="text-align: center; padding: 0.15em 0.4em" | Token
**style="text-align: center; padding: 0.15em 0.4em" colspan="3" | RGB
**style="text-align: center; padding: 0.15em 0.4em" | Hex
**style="text-align: center; padding: 0.15em 0.4em" | Palette

| style="padding: 0.15em 0.4em; text-align: left" | MAROON
| style="padding: 0.15em 0.4em" | 128
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | #800000
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | CHESTNUT
| style="padding: 0.15em 0.4em" | 205
| style="padding: 0.15em 0.4em" | 92
| style="padding: 0.15em 0.4em" | 92
| style="padding: 0.15em 0.4em" | #CD5C5C
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | ROSE
| style="padding: 0.15em 0.4em" | 244
| style="padding: 0.15em 0.4em" | 194
| style="padding: 0.15em 0.4em" | 194
| style="padding: 0.15em 0.4em" | #F4C2C2
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | RED
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | #FF0000
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | VERMILION
| style="padding: 0.15em 0.4em" | 227
| style="padding: 0.15em 0.4em" | 66
| style="padding: 0.15em 0.4em" | 52
| style="padding: 0.15em 0.4em" | #E34234
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | DARK_CHESTNUT
| style="padding: 0.15em 0.4em" | 152
| style="padding: 0.15em 0.4em" | 105
| style="padding: 0.15em 0.4em" | 96
| style="padding: 0.15em 0.4em" | #986960
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | BURNT_SIENNA
| style="padding: 0.15em 0.4em" | 233
| style="padding: 0.15em 0.4em" | 116
| style="padding: 0.15em 0.4em" | 81
| style="padding: 0.15em 0.4em" | #E97451
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | MAHOGANY
| style="padding: 0.15em 0.4em" | 192
| style="padding: 0.15em 0.4em" | 64
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | #C04000
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | PALE_BROWN
| style="padding: 0.15em 0.4em" | 152
| style="padding: 0.15em 0.4em" | 118
| style="padding: 0.15em 0.4em" | 84
| style="padding: 0.15em 0.4em" | #987654
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | RASPBERRY_PINK
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 25
| style="padding: 0.15em 0.4em" | 128
| style="padding: 0.15em 0.4em" | #FF1980
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | RED_PURPLE
| style="padding: 0.15em 0.4em" | 178
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 75
| style="padding: 0.15em 0.4em" | #B2004B
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | DARK_PINK
| style="padding: 0.15em 0.4em" | 231
| style="padding: 0.15em 0.4em" | 84
| style="padding: 0.15em 0.4em" | 128
| style="padding: 0.15em 0.4em" | #E75480
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | DARK_SCARLET
| style="padding: 0.15em 0.4em" | 86
| style="padding: 0.15em 0.4em" | 3
| style="padding: 0.15em 0.4em" | 25
| style="padding: 0.15em 0.4em" | #560319
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | CRIMSON
| style="padding: 0.15em 0.4em" | 220
| style="padding: 0.15em 0.4em" | 20
| style="padding: 0.15em 0.4em" | 60
| style="padding: 0.15em 0.4em" | #DC143C
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | CARMINE
| style="padding: 0.15em 0.4em" | 150
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 24
| style="padding: 0.15em 0.4em" | #960018
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | CARDINAL
| style="padding: 0.15em 0.4em" | 196
| style="padding: 0.15em 0.4em" | 30
| style="padding: 0.15em 0.4em" | 58
| style="padding: 0.15em 0.4em" | #C41E3A
| style="padding: 0.15em 0.4em" |

| | + **LRED colors**

**style="text-align: center; padding: 0.15em 0.4em" | Token
**style="text-align: center; padding: 0.15em 0.4em" colspan="3" | RGB
**style="text-align: center; padding: 0.15em 0.4em" | Hex
**style="text-align: center; padding: 0.15em 0.4em" | Palette

| style="padding: 0.15em 0.4em; text-align: left" | RUST
| style="padding: 0.15em 0.4em" | 183
| style="padding: 0.15em 0.4em" | 65
| style="padding: 0.15em 0.4em" | 14
| style="padding: 0.15em 0.4em" | #B7410E
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | PUMPKIN
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 117
| style="padding: 0.15em 0.4em" | 24
| style="padding: 0.15em 0.4em" | #FF7518
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | SEPIA
| style="padding: 0.15em 0.4em" | 112
| style="padding: 0.15em 0.4em" | 66
| style="padding: 0.15em 0.4em" | 20
| style="padding: 0.15em 0.4em" | #704214
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | BROWN
| style="padding: 0.15em 0.4em" | 150
| style="padding: 0.15em 0.4em" | 75
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | #964B00
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | CINNAMON
| style="padding: 0.15em 0.4em" | 123
| style="padding: 0.15em 0.4em" | 63
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | #7B3F00
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | TAN
| style="padding: 0.15em 0.4em" | 210
| style="padding: 0.15em 0.4em" | 180
| style="padding: 0.15em 0.4em" | 140
| style="padding: 0.15em 0.4em" | #D2B48C
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | RAW_UMBER
| style="padding: 0.15em 0.4em" | 115
| style="padding: 0.15em 0.4em" | 74
| style="padding: 0.15em 0.4em" | 18
| style="padding: 0.15em 0.4em" | #734A12
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | TAUPE_SANDY
| style="padding: 0.15em 0.4em" | 150
| style="padding: 0.15em 0.4em" | 113
| style="padding: 0.15em 0.4em" | 23
| style="padding: 0.15em 0.4em" | #967117
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | ECRU
| style="padding: 0.15em 0.4em" | 194
| style="padding: 0.15em 0.4em" | 178
| style="padding: 0.15em 0.4em" | 128
| style="padding: 0.15em 0.4em" | #C2B280
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | SCARLET
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 36
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | #FF2400
| style="padding: 0.15em 0.4em" |

| | + **BROWN colors**

**style="text-align: center; padding: 0.15em 0.4em" | Token
**style="text-align: center; padding: 0.15em 0.4em" colspan="3" | RGB
**style="text-align: center; padding: 0.15em 0.4em" | Hex
**style="text-align: center; padding: 0.15em 0.4em" | Palette

| style="padding: 0.15em 0.4em; text-align: left" | BURNT_UMBER
| style="padding: 0.15em 0.4em" | 138
| style="padding: 0.15em 0.4em" | 51
| style="padding: 0.15em 0.4em" | 36
| style="padding: 0.15em 0.4em" | #8A3324
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | AUBURN
| style="padding: 0.15em 0.4em" | 111
| style="padding: 0.15em 0.4em" | 53
| style="padding: 0.15em 0.4em" | 26
| style="padding: 0.15em 0.4em" | #6F351A
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | CHOCOLATE
| style="padding: 0.15em 0.4em" | 210
| style="padding: 0.15em 0.4em" | 105
| style="padding: 0.15em 0.4em" | 30
| style="padding: 0.15em 0.4em" | #DC691E
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | TAUPE_PALE
| style="padding: 0.15em 0.4em" | 188
| style="padding: 0.15em 0.4em" | 152
| style="padding: 0.15em 0.4em" | 126
| style="padding: 0.15em 0.4em" | #BC987E
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | COPPER
| style="padding: 0.15em 0.4em" | 184
| style="padding: 0.15em 0.4em" | 115
| style="padding: 0.15em 0.4em" | 51
| style="padding: 0.15em 0.4em" | #B87333
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | DARK_BROWN
| style="padding: 0.15em 0.4em" | 101
| style="padding: 0.15em 0.4em" | 67
| style="padding: 0.15em 0.4em" | 33
| style="padding: 0.15em 0.4em" | #654321
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | LIGHT_BROWN
| style="padding: 0.15em 0.4em" | 205
| style="padding: 0.15em 0.4em" | 133
| style="padding: 0.15em 0.4em" | 63
| style="padding: 0.15em 0.4em" | #CD853F
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | BRONZE
| style="padding: 0.15em 0.4em" | 205
| style="padding: 0.15em 0.4em" | 127
| style="padding: 0.15em 0.4em" | 50
| style="padding: 0.15em 0.4em" | #CD7F32
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | OCHRE
| style="padding: 0.15em 0.4em" | 204
| style="padding: 0.15em 0.4em" | 119
| style="padding: 0.15em 0.4em" | 34
| style="padding: 0.15em 0.4em" | #CC7722
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | GOLDENROD
| style="padding: 0.15em 0.4em" | 218
| style="padding: 0.15em 0.4em" | 165
| style="padding: 0.15em 0.4em" | 32
| style="padding: 0.15em 0.4em" | #DAA520
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | GOLD
| style="padding: 0.15em 0.4em" | 212
| style="padding: 0.15em 0.4em" | 175
| style="padding: 0.15em 0.4em" | 55
| style="padding: 0.15em 0.4em" | #D4AF37
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | BRASS
| style="padding: 0.15em 0.4em" | 181
| style="padding: 0.15em 0.4em" | 166
| style="padding: 0.15em 0.4em" | 66
| style="padding: 0.15em 0.4em" | #B5A642
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | OLIVE
| style="padding: 0.15em 0.4em" | 128
| style="padding: 0.15em 0.4em" | 128
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | #808000
| style="padding: 0.15em 0.4em" |

| | + **YELLOW colors**

**style="text-align: center; padding: 0.15em 0.4em" | Token
**style="text-align: center; padding: 0.15em 0.4em" colspan="3" | RGB
**style="text-align: center; padding: 0.15em 0.4em" | Hex
**style="text-align: center; padding: 0.15em 0.4em" | Palette

| style="padding: 0.15em 0.4em; text-align: left" | DARK_PEACH
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 218
| style="padding: 0.15em 0.4em" | 185
| style="padding: 0.15em 0.4em" | #FFDAB9
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | ORANGE
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 165
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | #FFA500
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | PEACH
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 229
| style="padding: 0.15em 0.4em" | 180
| style="padding: 0.15em 0.4em" | #FFE5B4
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | SAFFRON
| style="padding: 0.15em 0.4em" | 244
| style="padding: 0.15em 0.4em" | 196
| style="padding: 0.15em 0.4em" | 48
| style="padding: 0.15em 0.4em" | #F4C430
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | AMBER
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 191
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | #FFBF00
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | PEARL
| style="padding: 0.15em 0.4em" | 240
| style="padding: 0.15em 0.4em" | 234
| style="padding: 0.15em 0.4em" | 214
| style="padding: 0.15em 0.4em" | #F0EBD6
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | BUFF
| style="padding: 0.15em 0.4em" | 240
| style="padding: 0.15em 0.4em" | 220
| style="padding: 0.15em 0.4em" | 130
| style="padding: 0.15em 0.4em" | #F0DC82
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | FLAX
| style="padding: 0.15em 0.4em" | 238
| style="padding: 0.15em 0.4em" | 220
| style="padding: 0.15em 0.4em" | 130
| style="padding: 0.15em 0.4em" | #EEDC82
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | GOLDEN_YELLOW
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 223
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | #FFDF00
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | LEMON
| style="padding: 0.15em 0.4em" | 253
| style="padding: 0.15em 0.4em" | 233
| style="padding: 0.15em 0.4em" | 16
| style="padding: 0.15em 0.4em" | #FDE910
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | CREAM
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 253
| style="padding: 0.15em 0.4em" | 208
| style="padding: 0.15em 0.4em" | #FFFDD0
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | YELLOW
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | #FFFF00
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | LIME
| style="padding: 0.15em 0.4em" | 204
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | #CCFF00
| style="padding: 0.15em 0.4em" |

| | + **GREEN colors**

**style="text-align: center; padding: 0.15em 0.4em" | Token
**style="text-align: center; padding: 0.15em 0.4em" colspan="3" | RGB
**style="text-align: center; padding: 0.15em 0.4em" | Hex
**style="text-align: center; padding: 0.15em 0.4em" | Palette

| style="padding: 0.15em 0.4em; text-align: left" | TAUPE_DARK
| style="padding: 0.15em 0.4em" | 72
| style="padding: 0.15em 0.4em" | 60
| style="padding: 0.15em 0.4em" | 50
| style="padding: 0.15em 0.4em" | #483C32
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | DARK_TAN
| style="padding: 0.15em 0.4em" | 145
| style="padding: 0.15em 0.4em" | 129
| style="padding: 0.15em 0.4em" | 81
| style="padding: 0.15em 0.4em" | #918151
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | YELLOW_GREEN
| style="padding: 0.15em 0.4em" | 154
| style="padding: 0.15em 0.4em" | 205
| style="padding: 0.15em 0.4em" | 50
| style="padding: 0.15em 0.4em" | #9ACD32
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | DARK_OLIVE
| style="padding: 0.15em 0.4em" | 85
| style="padding: 0.15em 0.4em" | 104
| style="padding: 0.15em 0.4em" | 50
| style="padding: 0.15em 0.4em" | #556832
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | GREEN-YELLOW
| style="padding: 0.15em 0.4em" | 173
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 47
| style="padding: 0.15em 0.4em" | #ADFF2F
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | APPLE_GREEN
| style="padding: 0.15em 0.4em" | 97
| style="padding: 0.15em 0.4em" | 178
| style="padding: 0.15em 0.4em" | 53
| style="padding: 0.15em 0.4em" | #61B235
| style="padding: 0.15em 0.4em" |

| | + **LGREEN colors**

**style="text-align: center; padding: 0.15em 0.4em" | Token
**style="text-align: center; padding: 0.15em 0.4em" colspan="3" | RGB
**style="text-align: center; padding: 0.15em 0.4em" | Hex
**style="text-align: center; padding: 0.15em 0.4em" | Palette

| style="padding: 0.15em 0.4em; text-align: left" | CHARTREUSE
| style="padding: 0.15em 0.4em" | 127
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | #7BFF00
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | BRIGHT_GREEN
| style="padding: 0.15em 0.4em" | 80
| style="padding: 0.15em 0.4em" | 229
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | #50E500
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | LEAF_GREEN
| style="padding: 0.15em 0.4em" | 25
| style="padding: 0.15em 0.4em" | 178
| style="padding: 0.15em 0.4em" | 17
| style="padding: 0.15em 0.4em" | #19B211
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | ZESTY_GREEN
| style="padding: 0.15em 0.4em" | 55
| style="padding: 0.15em 0.4em" | 229
| style="padding: 0.15em 0.4em" | 45
| style="padding: 0.15em 0.4em" | #37E52D
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | GREEN
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | #00FF00
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | WOODLAND_GREEN
| style="padding: 0.15em 0.4em" | 15
| style="padding: 0.15em 0.4em" | 153
| style="padding: 0.15em 0.4em" | 49
| style="padding: 0.15em 0.4em" | #0F9931
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | GRASS_GREEN
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 204
| style="padding: 0.15em 0.4em" | 51
| style="padding: 0.15em 0.4em" | #00CC33
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | VIBRANT_GREEN
| style="padding: 0.15em 0.4em" | 25
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 82
| style="padding: 0.15em 0.4em" | #19FF52
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | EMERALD
| style="padding: 0.15em 0.4em" | 80
| style="padding: 0.15em 0.4em" | 200
| style="padding: 0.15em 0.4em" | 120
| style="padding: 0.15em 0.4em" | #50C878
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | DARK_GREEN
| style="padding: 0.15em 0.4em" | 1
| style="padding: 0.15em 0.4em" | 50
| style="padding: 0.15em 0.4em" | 32
| style="padding: 0.15em 0.4em" | #013220
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | JADE
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 168
| style="padding: 0.15em 0.4em" | 107
| style="padding: 0.15em 0.4em" | #00A86B
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | MIDNIGHT_BLUE
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 51
| style="padding: 0.15em 0.4em" | 102
| style="padding: 0.15em 0.4em" | #003366
| style="padding: 0.15em 0.4em" |

| | + **CYAN colors**

**style="text-align: center; padding: 0.15em 0.4em" | Token
**style="text-align: center; padding: 0.15em 0.4em" colspan="3" | RGB
**style="text-align: center; padding: 0.15em 0.4em" | Hex
**style="text-align: center; padding: 0.15em 0.4em" | Palette

| style="padding: 0.15em 0.4em; text-align: left" | RUSSET
| style="padding: 0.15em 0.4em" | 117
| style="padding: 0.15em 0.4em" | 90
| style="padding: 0.15em 0.4em" | 87
| style="padding: 0.15em 0.4em" | #755A57
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | TAUPE_MEDIUM
| style="padding: 0.15em 0.4em" | 103
| style="padding: 0.15em 0.4em" | 76
| style="padding: 0.15em 0.4em" | 71
| style="padding: 0.15em 0.4em" | #674C47
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | FERN_GREEN
| style="padding: 0.15em 0.4em" | 79
| style="padding: 0.15em 0.4em" | 121
| style="padding: 0.15em 0.4em" | 66
| style="padding: 0.15em 0.4em" | #4F7942
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | MOSS_GREEN
| style="padding: 0.15em 0.4em" | 173
| style="padding: 0.15em 0.4em" | 223
| style="padding: 0.15em 0.4em" | 173
| style="padding: 0.15em 0.4em" | #ADDFAD
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | MINT_GREEN
| style="padding: 0.15em 0.4em" | 152
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 152
| style="padding: 0.15em 0.4em" | #98FF98
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | EUCALYPTUS
| style="padding: 0.15em 0.4em" | 76
| style="padding: 0.15em 0.4em" | 153
| style="padding: 0.15em 0.4em" | 141
| style="padding: 0.15em 0.4em" | #4C998D
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | LIGHT_BLUE
| style="padding: 0.15em 0.4em" | 173
| style="padding: 0.15em 0.4em" | 216
| style="padding: 0.15em 0.4em" | 230
| style="padding: 0.15em 0.4em" | #ADD8E6
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | SLATE_GRAY
| style="padding: 0.15em 0.4em" | 112
| style="padding: 0.15em 0.4em" | 128
| style="padding: 0.15em 0.4em" | 144
| style="padding: 0.15em 0.4em" | #708090
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | BLUE-GRAY
| style="padding: 0.15em 0.4em" | 186
| style="padding: 0.15em 0.4em" | 202
| style="padding: 0.15em 0.4em" | 226
| style="padding: 0.15em 0.4em" | #BACAE2
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | PALE_CHESTNUT
| style="padding: 0.15em 0.4em" | 221
| style="padding: 0.15em 0.4em" | 173
| style="padding: 0.15em 0.4em" | 175
| style="padding: 0.15em 0.4em" | #DDADAF
| style="padding: 0.15em 0.4em" |

| | + **LCYAN colors**

**style="text-align: center; padding: 0.15em 0.4em" | Token
**style="text-align: center; padding: 0.15em 0.4em" colspan="3" | RGB
**style="text-align: center; padding: 0.15em 0.4em" | Hex
**style="text-align: center; padding: 0.15em 0.4em" | Palette

| style="padding: 0.15em 0.4em; text-align: left" | SPRING_GREEN
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 127
| style="padding: 0.15em 0.4em" | #00FF7F
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | AQUAMARINE
| style="padding: 0.15em 0.4em" | 127
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 212
| style="padding: 0.15em 0.4em" | #7FFFD4
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | SEA_FOAM
| style="padding: 0.15em 0.4em" | 25
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 220
| style="padding: 0.15em 0.4em" | #19FFDC
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | TURQUOISE
| style="padding: 0.15em 0.4em" | 48
| style="padding: 0.15em 0.4em" | 213
| style="padding: 0.15em 0.4em" | 200
| style="padding: 0.15em 0.4em" | #30D5C8
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | AQUA
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | #00FFFF
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | GLACIER_BLUE
| style="padding: 0.15em 0.4em" | 25
| style="padding: 0.15em 0.4em" | 220
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | #19DCFF
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | SKY_BLUE
| style="padding: 0.15em 0.4em" | 135
| style="padding: 0.15em 0.4em" | 206
| style="padding: 0.15em 0.4em" | 235
| style="padding: 0.15em 0.4em" | #87CEEB
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | LILAC
| style="padding: 0.15em 0.4em" | 200
| style="padding: 0.15em 0.4em" | 162
| style="padding: 0.15em 0.4em" | 200
| style="padding: 0.15em 0.4em" | #C8A2C8
| style="padding: 0.15em 0.4em" |

| | + **BLUE colors**

**style="text-align: center; padding: 0.15em 0.4em" | Token
**style="text-align: center; padding: 0.15em 0.4em" colspan="3" | RGB
**style="text-align: center; padding: 0.15em 0.4em" | Hex
**style="text-align: center; padding: 0.15em 0.4em" | Palette

| style="padding: 0.15em 0.4em; text-align: left" | SEA_GREEN
| style="padding: 0.15em 0.4em" | 46
| style="padding: 0.15em 0.4em" | 139
| style="padding: 0.15em 0.4em" | 87
| style="padding: 0.15em 0.4em" | #2E8B57
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | PINE_GREEN
| style="padding: 0.15em 0.4em" | 1
| style="padding: 0.15em 0.4em" | 121
| style="padding: 0.15em 0.4em" | 111
| style="padding: 0.15em 0.4em" | #01796F
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | TEAL
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 128
| style="padding: 0.15em 0.4em" | 128
| style="padding: 0.15em 0.4em" | #008080
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | CERULEAN
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 123
| style="padding: 0.15em 0.4em" | 167
| style="padding: 0.15em 0.4em" | #007BA7
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | RIVER_BLUE
| style="padding: 0.15em 0.4em" | 61
| style="padding: 0.15em 0.4em" | 139
| style="padding: 0.15em 0.4em" | 204
| style="padding: 0.15em 0.4em" | #3D8BCC
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | CORNFLOWER
| style="padding: 0.15em 0.4em" | 76
| style="padding: 0.15em 0.4em" | 174
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | #4CAEFF
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | AZURE
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 127
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | #007FFF
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | ULTRAMARINE
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 63
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | #003FFF
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | COBALT
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 71
| style="padding: 0.15em 0.4em" | 171
| style="padding: 0.15em 0.4em" | #0047AB
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | DEEP_SEA_BLUE
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 38
| style="padding: 0.15em 0.4em" | 153
| style="padding: 0.15em 0.4em" | #002699
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | DARK_AZURE
| style="padding: 0.15em 0.4em" | 45
| style="padding: 0.15em 0.4em" | 91
| style="padding: 0.15em 0.4em" | 229
| style="padding: 0.15em 0.4em" | #2D5BE5
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | DARK_BLUE
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 139
| style="padding: 0.15em 0.4em" | #00008B
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | BLUE
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | #0000FF
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | PERIWINKLE
| style="padding: 0.15em 0.4em" | 204
| style="padding: 0.15em 0.4em" | 204
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | #CCCCFF
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | SAPPHIRE
| style="padding: 0.15em 0.4em" | 55
| style="padding: 0.15em 0.4em" | 45
| style="padding: 0.15em 0.4em" | 229
| style="padding: 0.15em 0.4em" | #372DE5
| style="padding: 0.15em 0.4em" |

| | + **LBLUE colors**

**style="text-align: center; padding: 0.15em 0.4em" | Token
**style="text-align: center; padding: 0.15em 0.4em" colspan="3" | RGB
**style="text-align: center; padding: 0.15em 0.4em" | Hex
**style="text-align: center; padding: 0.15em 0.4em" | Palette

| style="padding: 0.15em 0.4em; text-align: left" | TAUPE_ROSE
| style="padding: 0.15em 0.4em" | 144
| style="padding: 0.15em 0.4em" | 93
| style="padding: 0.15em 0.4em" | 93
| style="padding: 0.15em 0.4em" | #905D5D
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | PALE_BLUE
| style="padding: 0.15em 0.4em" | 175
| style="padding: 0.15em 0.4em" | 238
| style="padding: 0.15em 0.4em" | 238
| style="padding: 0.15em 0.4em" | #AFEEEE
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | CROCUS_PURPLE
| style="padding: 0.15em 0.4em" | 110
| style="padding: 0.15em 0.4em" | 45
| style="padding: 0.15em 0.4em" | 229
| style="padding: 0.15em 0.4em" | #6E2DE5
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | AMETHYST
| style="padding: 0.15em 0.4em" | 153
| style="padding: 0.15em 0.4em" | 102
| style="padding: 0.15em 0.4em" | 204
| style="padding: 0.15em 0.4em" | #9966CC
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | VIOLET
| style="padding: 0.15em 0.4em" | 139
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | #8B00FF
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | MAUVE_TAUPE
| style="padding: 0.15em 0.4em" | 145
| style="padding: 0.15em 0.4em" | 95
| style="padding: 0.15em 0.4em" | 109
| style="padding: 0.15em 0.4em" | #915F6D
| style="padding: 0.15em 0.4em" |

| | + **MAGENTA colors**

**style="text-align: center; padding: 0.15em 0.4em" | Token
**style="text-align: center; padding: 0.15em 0.4em" colspan="3" | RGB
**style="text-align: center; padding: 0.15em 0.4em" | Hex
**style="text-align: center; padding: 0.15em 0.4em" | Palette

| style="padding: 0.15em 0.4em; text-align: left" | CHARCOAL
| style="padding: 0.15em 0.4em" | 54
| style="padding: 0.15em 0.4em" | 69
| style="padding: 0.15em 0.4em" | 79
| style="padding: 0.15em 0.4em" | #36454F
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | DARK_VIOLET
| style="padding: 0.15em 0.4em" | 66
| style="padding: 0.15em 0.4em" | 49
| style="padding: 0.15em 0.4em" | 137
| style="padding: 0.15em 0.4em" | #423189
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | DARK_INDIGO
| style="padding: 0.15em 0.4em" | 49
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 98
| style="padding: 0.15em 0.4em" | #310062
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | INDIGO
| style="padding: 0.15em 0.4em" | 75
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 130
| style="padding: 0.15em 0.4em" | #4B0082
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | FOXGLOVE
| style="padding: 0.15em 0.4em" | 165
| style="padding: 0.15em 0.4em" | 45
| style="padding: 0.15em 0.4em" | 229
| style="padding: 0.15em 0.4em" | #A52DE5
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | PURPLE
| style="padding: 0.15em 0.4em" | 102
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 153
| style="padding: 0.15em 0.4em" | #660099
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | PLUM
| style="padding: 0.15em 0.4em" | 102
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 102
| style="padding: 0.15em 0.4em" | #660066
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | TAUPE_PURPLE
| style="padding: 0.15em 0.4em" | 80
| style="padding: 0.15em 0.4em" | 64
| style="padding: 0.15em 0.4em" | 77
| style="padding: 0.15em 0.4em" | #50404D
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | EGGPLANT
| style="padding: 0.15em 0.4em" | 97
| style="padding: 0.15em 0.4em" | 64
| style="padding: 0.15em 0.4em" | 81
| style="padding: 0.15em 0.4em" | #614051
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | MAUVE
| style="padding: 0.15em 0.4em" | 153
| style="padding: 0.15em 0.4em" | 51
| style="padding: 0.15em 0.4em" | 102
| style="padding: 0.15em 0.4em" | #993366
| style="padding: 0.15em 0.4em" |

| | + **LMAGENTA colors**

**style="text-align: center; padding: 0.15em 0.4em" | Token
**style="text-align: center; padding: 0.15em 0.4em" colspan="3" | RGB
**style="text-align: center; padding: 0.15em 0.4em" | Hex
**style="text-align: center; padding: 0.15em 0.4em" | Palette

| style="padding: 0.15em 0.4em; text-align: left" | HELIOTROPE
| style="padding: 0.15em 0.4em" | 223
| style="padding: 0.15em 0.4em" | 115
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | #DF73FF
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | ORCHID_PINK
| style="padding: 0.15em 0.4em" | 229
| style="padding: 0.15em 0.4em" | 91
| style="padding: 0.15em 0.4em" | 195
| style="padding: 0.15em 0.4em" | #E55BC3
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | FUCHSIA
| style="padding: 0.15em 0.4em" | 244
| style="padding: 0.15em 0.4em" | 0
| style="padding: 0.15em 0.4em" | 161
| style="padding: 0.15em 0.4em" | #F400A1
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | PUCE
| style="padding: 0.15em 0.4em" | 204
| style="padding: 0.15em 0.4em" | 136
| style="padding: 0.15em 0.4em" | 153
| style="padding: 0.15em 0.4em" | #CC8899
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | PINK
| style="padding: 0.15em 0.4em" | 255
| style="padding: 0.15em 0.4em" | 192
| style="padding: 0.15em 0.4em" | 203
| style="padding: 0.15em 0.4em" | #FFC0CB
| style="padding: 0.15em 0.4em" |

| style="padding: 0.15em 0.4em; text-align: left" | PALE_PINK
| style="padding: 0.15em 0.4em" | 250
| style="padding: 0.15em 0.4em" | 218
| style="padding: 0.15em 0.4em" | 221
| style="padding: 0.15em 0.4em" | #FADADD
| style="padding: 0.15em 0.4em" |

1. Color lists
:*For the different colors used to represent different professions, see Skill categories.*
:*For a list of the colors of items listed in the -stocks menu, see Stocks.*
:*For the colors of the various creatures, see creature*
:*For the colors of status icons, see status icon*

1. Material by color

For those who want to know which materials display as which color, for levers, aesthetic concerns, etc.

1. ASCII Mode
Color names listed and the colors shown below match the colors from default init/color.txt. To change these from the default tones, see Color scheme. 

**width="90"| Color
**Stones
**Ores
**Metals
**Other

| WHITE
| Alabaster, Alunite, Borax, Calcite, Chalk, Cryolite, Dolomite, Limestone, Marble, Marcasite, Periclase, Quartzite, Rock salt, Satinspar, Selenite, Talc
| Galena, Horn silver, Native aluminum, Native platinum, Native silver
| Silver, Platinum, Aluminum, Fine pewter, Nickel silver, Sterling silver
| Crystal glass, Feather tree, Tower-cap

| LGRAY
| Anhydrite, Dacite, Gneiss, Granite, Phyllite, Stibnite
| Bismuthinite
| Nickel, Tin, Zinc, Billon, Trifle pewter
| | DGRAY
| Andesite, Basalt, Claystone, Chromite, Diorite, Gabbro, Graphite, Hornblende, Ilmenite, Jet, Mica, Pyrolusite, Rhyolite, Shale, Slate, Obsidian
| Bituminous coal, Lignite, Magnetite, Sphalerite, Tetrahedrite
| Iron, Steel, Lead, Pig iron
| Black-cap

| BROWN
| Chert, Conglomerate, Mudstone, Puddingstone, Sandstone, Schist, Siltstone
| Cassiterite, Native copper
| Copper, Bronze
| All other aboveground trees

| YELLOW
| Brimstone, Orpiment, Orthoclase, Saltpeter, Sylvite, Gypsum
| Limonite, Native gold
| Gold, Bismuth bronze, Brass, Electrum
| Fungiwood

| RED
| Bauxite, Kaolinite
| Hematite
| | Blood thorn

| LRED
| Cinnabar, Petrified wood, Realgar
| | | Goblin-cap

| GREEN
| Olivine, Serpentine
| Malachite
| | Green glass

| LGREEN
| | Garnierite
| | | CYAN
| | | Lay pewter
| Clear glass, Spore tree

| LCYAN
| Microcline
| Raw adamantine
| Adamantine
| Ice

| BLUE
| Kimberlite
| | | Nether-cap

| LBLUE
| Cobaltite
| | | | MAGENTA
| Pitchblende, Rutile
| | Black bronze
| Glumprong

| LMAGENTA
| | | Bismuth, Rose gold
| Tunnel tube
