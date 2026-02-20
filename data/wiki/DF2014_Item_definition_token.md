# DF2014:Item definition token

- Item definition tokens** are used in item definitions in the raws.

Item types:
- ITEM_AMMO - ammo token
- ITEM_ARMOR - armor-type armor token
- ITEM_FOOD - see below
- ITEM_GLOVES - gloves-type armor token
- ITEM_HELM - helm-type armor token
- ITEM_INSTRUMENT - instrument token
- ITEM_PANTS - pants-type armor token
- ITEM_SHIELD - shield-type armor token
- ITEM_SHOES - shoes-type armor token
- ITEM_SIEGEAMMO - see below
- ITEM_TOOL - tool token
- ITEM_TOY - see below
- ITEM_TRAPCOMP - trap component token
- ITEM_WEAPON - weapon token

1. Toy tokens

**Token
**Arguments
**Description

| | singular:plural
| What this item will be called in-game.

| | | Presumably prevents the item from being made from cloth, silk, or leather, present on everything but puzzleboxes and drums. Appears to work backwards for strange moods.

1. Siege ammo tokens

**Token
**Arguments
**Description

| | singular:plural
| What this item will be called in-game.

| | | Specifies what type of siege engine uses this ammunition. Currently, only BALLISTA is permitted.

1. Food tokens

**Token
**Arguments
**Description

| | singular:plural
| What this item will be called in-game.

| | | Specifies the number of ingredients that are used in this type of prepared meal - 2 for Easy, 3 for Fine, 4 for Lavish. Defaults to 2.

ru:Item definition token
