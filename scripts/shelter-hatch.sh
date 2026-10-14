#!/bin/bash
# Close a shelter's surface stair with a hatch cover (X7v75, 13 Oct 2026: on the sheltered evil coast a mink raised as an
# infernal ash zombie walked down the shelter's open stair and bit the mayor; the infection took the fort). Animals cannot
# open a hatch; dwarves can. Needs DF running with the sheltered fort loaded (scripts/shelter.sh already run on it).
#   1. find the shelter's surface down stair: the stair column cx-shelter find chose (SHELTER sx sy sz ...)
#   2. createitem HATCH_COVER of the commonest stone at that tile (no workshop needed)
#   3. quickfort #build H on the stair top; buildingplan attaches the item; a dwarf builds it (step until it stands)
# Usage: scripts/shelter-hatch.sh SX SY SZ [stone=INORGANIC:GRANITE]
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/cx-config.sh >/dev/null
L=scripts/cx-lifecycle.sh
sx="$1"; sy="$2"; sz="$3"; mat="${4:-INORGANIC:GRANITE}"
bp="$DF_DIR/dfhack-config/blueprints"
mkdir -p "$bp"
printf '#build shelter hatch: a hatch cover over the stair top\nH\n' > "$bp/cx-shelter-hatch.csv"
# the item at the stair tile: dfhack.items.createItem by the first citizen, then moved onto the stair top
$L lua "local u for _, x in ipairs(df.global.world.units.active) do if dfhack.units.isCitizen(x) then u = x break end end
local mi = dfhack.matinfo.find('${mat#INORGANIC:}') or dfhack.matinfo.find('$mat')
local items = dfhack.items.createItem(u, df.item_type.HATCH_COVER, -1, mi.type, mi.index)
local it = type(items) == 'table' and items[1] or items
dfhack.items.moveToGround(it, xyz2pos($sx, $sy, $sz))
print('HATCH_ITEM ' .. it.id .. ' at $sx,$sy,$sz')" 2>&1 | tail -1
$L cmd enable buildingplan 2>&1 | tr -d '\r' | tail -1
$L cmd quickfort run cx-shelter-hatch.csv -c "$sx,$sy,$sz" 2>&1 | tr -d '\r' | tail -2
for i in 1 2 3 4 5 6; do
    $L step 500 >/dev/null 2>&1 || true
    got=$($L lua "local b = dfhack.buildings.findAtTile(xyz2pos($sx, $sy, $sz)) print((b and b:getType() == df.building_type.Hatch and b:getBuildStage() >= b:getMaxBuildStage()) and 'BUILT' or 'WAITING')" 2>&1 | tail -1)
    echo "hatch: $got after $((i * 500)) ticks"
    [ "$got" = "BUILT" ] && exit 0
done
echo "hatch: not built after 3000 ticks"; exit 1
