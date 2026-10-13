#!/bin/bash
# Dig an underground shelter on the loaded fort and move the fort into it (user 13 Oct 2026: on evil-weather land, infernal
# ash zombifies every dwarf caught outdoors). Needs DF running with the fort loaded (cx-lifecycle start + load).
#   1. cx-shelter find: a stair column near the wagon over a solid 9x9 room DEPTH levels down (aquifer cleared there)
#   2. quickfort #dig: a down stair, up/down stairs, and the room with an up stair; dig-now digs it at once
#   3. quickfort #place: a stockpile taking every category over the room, so the dwarves haul everything inside
#   4. quickfort #zone: the room is the meeting area, where idle dwarves gather
#   5. cx-shelter wagon: the wagon is deconstructed (its load drops; the stockpile takes it in)
# Usage: scripts/shelter.sh [depth=4]
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/cx-config.sh >/dev/null
L=scripts/cx-lifecycle.sh
depth="${1:-4}"
line=$($L cmd cx-shelter find "$depth" 2>&1 | tr -d '\r' | grep -E '^SHELTER ' || true)
[ -n "$line" ] || { echo "shelter: no site: $($L cmd cx-shelter find "$depth" 2>&1 | tail -2)"; exit 1; }
read -r _ sx sy sz zb _ <<<"$line"
echo "shelter: $line"
bp="$DF_DIR/dfhack-config/blueprints"
mkdir -p "$bp"
blank='`,`,`,`,`,`,`,`,`'
row() { local c="$1"; echo "\`,\`,\`,\`,$c,\`,\`,\`,\`"; }
{
    echo '#dig shelter: a stair down to a 9x9 room'
    for r in 1 2 3 4; do echo "$blank"; done; row j; for r in 1 2 3 4; do echo "$blank"; done
    for ((k = 1; k < depth; k++)); do
        echo '#>'
        for r in 1 2 3 4; do echo "$blank"; done; row i; for r in 1 2 3 4; do echo "$blank"; done
    done
    echo '#>'
    for r in 1 2 3 4; do echo 'd,d,d,d,d,d,d,d,d'; done; echo 'd,d,d,d,u,d,d,d,d'; for r in 1 2 3 4; do echo 'd,d,d,d,d,d,d,d,d'; done
} > "$bp/cx-shelter-dig.csv"
printf '#place shelter: every category\nafunyrswebhlzSgpd(9x9)\n' > "$bp/cx-shelter-place.csv"
printf '#zone shelter: meeting area\nm(9x9)\n' > "$bp/cx-shelter-zone.csv"
x0=$((sx - 4)); y0=$((sy - 4))
$L cmd quickfort run cx-shelter-dig.csv -c "$x0,$y0,$sz" 2>&1 | tr -d '\r' | tail -2
$L cmd dig-now 2>&1 | tr -d '\r' | tail -1
$L cmd quickfort run cx-shelter-place.csv -c "$x0,$y0,$zb" 2>&1 | tr -d '\r' | tail -2
$L cmd quickfort run cx-shelter-zone.csv -c "$x0,$y0,$zb" 2>&1 | tr -d '\r' | tail -2
$L cmd cx-shelter wagon 2>&1 | tr -d '\r' | tail -1
echo "shelter: done (room ${x0}..$((x0 + 8)), ${y0}..$((y0 + 8)), z $zb; stair at $sx,$sy from z $sz)"
