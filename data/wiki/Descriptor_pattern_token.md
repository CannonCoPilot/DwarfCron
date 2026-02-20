# Descriptor pattern token

Tokens used to define descriptor patterns, that may be used instead of descriptor colors. As an example, the descriptor pattern STRIPES_ORANGE_BLACK is what gives tigers their stripes.

1. Tokens

**Token
**Arguments
**Usage
**Description

| | SPOTS, STRIPES, MOTTLED, IRIS_EYE or PUPIL_EYE
| | The type of pattern, deciding the description.
- SPOTS: Causes a crash if no CP_COLOR is given, otherwise takes any amount.
- STRIPES: Takes any amount of CP_COLOR tokens.
- MOTTLED: Takes any amount of CP_COLOR tokens.
- IRIS_EYE: Only shows the third CP_COLOR given; technically takes any amount. Causes a crash if no CP_COLOR is given. If only one or two CP_COLORs is given, the tissue is described as being "transparent".
- PUPIL_EYE: Only shows the second CP_COLOR given; technically takes any amount. Causes a crash if no CP_COLOR is given. If only one CP_COLORs is given, the tissue is described as being "transparent".
An undefined pattern type causes the description to simply not show up. 

| | color token
| | A color to be used in the pattern. See PATTERN for how many CP_COLOR tokens are needed, and how they are used. Modded color tokens may be used.

ru:Descriptor pattern token
