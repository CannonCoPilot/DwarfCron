# Descriptor shape token

These tokens are used to describe various shapes used in the game. All vanilla shapes are found in `descriptor_shape_standard.txt`.

1. Tokens

**Token
**Arguments
**Usage
**Description

| | string
| | An adjective to be paired with the name. Can be used multiple times, allowing for variants of the same shape e.g. "thin cross", "tall cross".

| | category name
| | A category the shape belongs to, which can be used by the tool token SHAPE_CATEGORY. Vanilla categories are SIMPLE, PLATONIC, and DICE, but any arbitrary category name is allowed.

| | number
| dice
| The amount of sides of the dice.

| | | gems
| Makes gems in this shape use the syntax 'ADJ + material' e.g. "conglomerate gizzard stone". This, GEMS_USE_NOUN or GEMS_USE_ADJ_NOUN must be used for the name of a gem in this shape to show up.

| | | gems
| Makes gems in this shape use the syntax 'ADJ + material + NAME' e.g. "smooth conglomerate cabochon". This, GEMS_USE_ADJ or GEMS_USE_ADJ_NOUN must be used for the name of a gem in this shape to show up.

| | | gems
| Makes gems in this shape use the syntax 'material + NAME' e.g. "point cut conglomerate". This, GEMS_USE_ADJ or GEMS_USE_ADJ_NOUN must be used for the name of a gem in this shape to show up.

| | string:plural
| | The name of the shape. Is not always strictly used, see GEMS_USE_ADJ.

| | 'character' or tile number
| | The tile the shape uses, as an engraving or as an item (gem, die).

| | word
| | Effect unknown.

ru:Descriptor shape token
