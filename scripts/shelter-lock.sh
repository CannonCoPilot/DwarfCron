#!/bin/bash
# Seal a shelter on terrifying land (X7v75d, 14 Oct 2026: on V75_TERROR50S a risen echidna and velociraptor walked from where
# they died, 50 tiles off, down the hatched stair at 93,94 and into the room; dwarves going out to haul corpses to the
# all-category stockpile held the hatch open). Run after scripts/shelter.sh and scripts/shelter-hatch.sh on the loaded fort.
#   1. the hatch over the stair top is locked (forbidden): nobody opens it, dwarves included
#   2. quickfort #burrow: a burrow `Shelter` over the shaft below the hatch and the 9x9 room; every citizen is assigned to it
#   3. the room's stockpile takes no refuse and no corpses, so no job sends a dwarf after a corpse
# The rig's sustain (season-run --sustain) waters and feeds the citizens; the room has no water or food of its own.
# Usage: scripts/shelter-lock.sh SX SY SZ ZB   (SHELTER sx sy sz zb from cx-shelter find; the hatch stands at SX,SY,SZ)
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/cx-config.sh >/dev/null
L=scripts/cx-lifecycle.sh
sx="$1"; sy="$2"; sz="$3"; zb="$4"
bp="$DF_DIR/dfhack-config/blueprints"
mkdir -p "$bp"
blank='`,`,`,`,`,`,`,`,`'
cell='a{name=Shelter create=true}'
{
    echo '#burrow shelter: the shaft under the hatch and the room'
    for ((z = sz - 1; z > zb; z--)); do
        for r in 1 2 3 4; do echo "$blank"; done; echo "\`,\`,\`,\`,$cell,\`,\`,\`,\`"; for r in 1 2 3 4; do echo "$blank"; done
        echo '#>'
    done
    echo "$cell(9x9)"
} > "$bp/cx-shelter-burrow.csv"
$L lua "local b = dfhack.buildings.findAtTile(xyz2pos($sx, $sy, $sz))
if not b or b:getType() ~= df.building_type.Hatch then qerror('no hatch at $sx,$sy,$sz') end
b.door_flags.forbidden = true
b.door_flags.closed = true
print('HATCH ' .. b.id .. ' locked: forbidden=' .. tostring(b.door_flags.forbidden) .. ' closed=' .. tostring(b.door_flags.closed))" 2>&1 | tr -d '\r' | tail -1
$L cmd quickfort run cx-shelter-burrow.csv -c "$((sx - 4)),$((sy - 4)),$((sz - 1))" 2>&1 | tr -d '\r' | tail -2
$L lua "local b = dfhack.burrows.findByName('Shelter')
if not b then qerror('no Shelter burrow') end
local n, tiles = 0, 0
for _, u in ipairs(df.global.world.units.active) do
    if dfhack.units.isCitizen(u) then dfhack.burrows.setAssignedUnit(b, u, true); n = n + 1 end
end
for z = $zb, $((sz - 1)) do for x = $((sx - 4)), $((sx + 4)) do for y = $((sy - 4)), $((sy + 4)) do
    if dfhack.burrows.isAssignedTile(b, xyz2pos(x, y, z)) then tiles = tiles + 1 end
end end end
print(('BURROW Shelter id %d: %d tile(s), %d citizen(s) assigned'):format(b.id, tiles, n))" 2>&1 | tr -d '\r' | tail -1
$L lua "local sp
for x = $((sx - 4)), $((sx + 4)) do for y = $((sy - 4)), $((sy + 4)) do
    local b = dfhack.buildings.findAtTile(xyz2pos(x, y, $zb))
    if not sp and b and b:getType() == df.building_type.Stockpile then sp = b end
end end
if not sp then qerror('no stockpile in the room at z $zb') end
sp.settings.flags.refuse = false
sp.settings.flags.corpses = false
print(('STOCKPILE %d: refuse=%s corpses=%s'):format(sp.id, tostring(sp.settings.flags.refuse), tostring(sp.settings.flags.corpses)))" 2>&1 | tr -d '\r' | tail -1
