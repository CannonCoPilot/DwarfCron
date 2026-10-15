#!/bin/bash
# Seal a shelter on terrifying land (X7v75d, 14 Oct 2026: on V75_TERROR50S a risen echidna and velociraptor walked from where
# they died, 50 tiles off, down the hatched stair at 93,94 and into the room; dwarves going out to haul corpses to the
# all-category stockpile held the hatch open). Run after scripts/shelter.sh and scripts/shelter-hatch.sh on the loaded fort.
#   1. the hatch over the stair top is locked (forbidden): nobody opens it, dwarves included
#   2. quickfort #burrow: a burrow `Shelter` over the shaft below the hatch and the room; every citizen is assigned to it
#   3. the room's stockpile takes no refuse and no corpses, so no job sends a dwarf after a corpse
#   4. the fort's animals (pets, livestock, strays) vanish, as exterminate's vaporize does: no corpse. X7v75e: sealed in with nothing
#      to graze, a stray horse starved, rose in the room and killed 11 dwarves; the dead then kept rising there.
# The rig's sustain (season-run --sustain) waters and feeds the citizens; the room has no water or food of its own.
# Usage: scripts/shelter-lock.sh SX SY SZ ZB [half=4]   (SHELTER sx sy sz zb from cx-shelter find; the hatch stands at SX,SY,SZ;
#        half as given to shelter.sh)
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/cx-config.sh >/dev/null
L=scripts/cx-lifecycle.sh
sx="$1"; sy="$2"; sz="$3"; zb="$4"; half="${5:-4}"; n=$((2 * half + 1))
bp="$DF_DIR/dfhack-config/blueprints"
mkdir -p "$bp"
rep() { local s="" i; for ((i = 0; i < $2; i++)); do s+="$1,"; done; echo "${s%,}"; }   # rep CELL N: N cells
blank=$(rep '`' "$n")
cell='a{name=Shelter create=true}'
{
    echo '#burrow shelter: the shaft under the hatch and the room'
    for ((z = sz - 1; z > zb; z--)); do
        for ((r = 0; r < half; r++)); do echo "$blank"; done; echo "$(rep '`' "$half"),$cell,$(rep '`' "$half")"
        for ((r = 0; r < half; r++)); do echo "$blank"; done
        echo '#>'
    done
    echo "$cell(${n}x$n)"
} > "$bp/cx-shelter-burrow.csv"
$L lua "local b = dfhack.buildings.findAtTile(xyz2pos($sx, $sy, $sz))
if not b or b:getType() ~= df.building_type.Hatch then qerror('no hatch at $sx,$sy,$sz') end
b.door_flags.forbidden = true
b.door_flags.closed = true
print('HATCH ' .. b.id .. ' locked: forbidden=' .. tostring(b.door_flags.forbidden) .. ' closed=' .. tostring(b.door_flags.closed))" 2>&1 | tr -d '\r' | tail -1
$L cmd quickfort run cx-shelter-burrow.csv -c "$((sx - half)),$((sy - half)),$((sz - 1))" 2>&1 | tr -d '\r' | tail -2
$L lua "local b = dfhack.burrows.findByName('Shelter')
if not b then qerror('no Shelter burrow') end
local n, tiles = 0, 0
for _, u in ipairs(df.global.world.units.active) do
    if dfhack.units.isCitizen(u) then dfhack.burrows.setAssignedUnit(b, u, true); n = n + 1 end
end
for z = $zb, $((sz - 1)) do for x = $((sx - half)), $((sx + half)) do for y = $((sy - half)), $((sy + half)) do
    if dfhack.burrows.isAssignedTile(b, xyz2pos(x, y, z)) then tiles = tiles + 1 end
end end end
print(('BURROW Shelter id %d: %d tile(s), %d citizen(s) assigned'):format(b.id, tiles, n))" 2>&1 | tr -d '\r' | tail -1
$L lua "local sp
for x = $((sx - half)), $((sx + half)) do for y = $((sy - half)), $((sy + half)) do
    local b = dfhack.buildings.findAtTile(xyz2pos(x, y, $zb))
    if not sp and b and b:getType() == df.building_type.Stockpile then sp = b end
end end
if not sp then qerror('no stockpile in the room at z $zb') end
sp.settings.flags.refuse = false
sp.settings.flags.corpses = false
print(('STOCKPILE %d: refuse=%s corpses=%s'):format(sp.id, tostring(sp.settings.flags.refuse), tostring(sp.settings.flags.corpses)))" 2>&1 | tr -d '\r' | tail -1
$L lua "local n, kinds = 0, {}
for _, u in ipairs(df.global.world.units.active) do
    if not dfhack.units.isDead(u) and u.civ_id == df.global.plotinfo.civ_id and u.race ~= df.global.plotinfo.race_id then
        u.animal.vanish_countdown = 1; n = n + 1
        local r = df.creature_raw.find(u.race).creature_id; kinds[r] = (kinds[r] or 0) + 1
    end
end
local s = {} for k, v in pairs(kinds) do s[#s + 1] = k .. ' ' .. v end
print(('ANIMALS %d of the fort vanish: %s'):format(n, table.concat(s, ', ')))" 2>&1 | tr -d '\r' | tail -1
