#!/bin/bash
# Dig an underground shelter on the loaded fort and move the fort into it (user 13 Oct 2026: on evil-weather land, infernal
# ash zombifies every dwarf caught outdoors). Needs DF running with the fort loaded (cx-lifecycle start + load).
#   1. cx-shelter find: a stair column near the wagon over a solid room (2*HALF+1 square) DEPTH levels down (aquifer cleared)
#   2. quickfort #dig: a down stair, up/down stairs, and the room with an up stair; dig-now digs it at once
#   3. quickfort #place: a stockpile taking every category over the room, so the dwarves haul everything inside
#   4. quickfort #zone: the room is the meeting area, where idle dwarves gather
#   5. cx-shelter wagon: the wagon is deconstructed (its load drops; the stockpile takes it in)
# Usage: scripts/shelter.sh [depth=4] [half=4]   (half 4 = 9x9 for 50 dwarves; half 7 = 15x15 for 100)
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/cx-config.sh >/dev/null
L=scripts/cx-lifecycle.sh
depth="${1:-4}"; half="${2:-4}"; n=$((2 * half + 1))
line=$($L cmd cx-shelter find "$depth" "$half" 2>&1 | tr -d '\r' | grep -E '^SHELTER ' || true)
[ -n "$line" ] || { echo "shelter: no site: $($L cmd cx-shelter find "$depth" "$half" 2>&1 | tail -2)"; exit 1; }
read -r _ sx sy sz zb _ <<<"$line"
echo "shelter: $line"
bp="$DF_DIR/dfhack-config/blueprints"
mkdir -p "$bp"
rep() { local s="" i; for ((i = 0; i < $2; i++)); do s+="$1,"; done; echo "${s%,}"; }   # rep CELL N: N cells
blank=$(rep '`' "$n")
row() { echo "$(rep '`' "$half"),$1,$(rep '`' "$half")"; }
full=$(rep d "$n")
{
    echo "#dig shelter: a stair down to a ${n}x$n room"
    for ((r = 0; r < half; r++)); do echo "$blank"; done; row j; for ((r = 0; r < half; r++)); do echo "$blank"; done
    for ((k = 1; k < depth; k++)); do
        echo '#>'
        for ((r = 0; r < half; r++)); do echo "$blank"; done; row i; for ((r = 0; r < half; r++)); do echo "$blank"; done
    done
    echo '#>'
    for ((r = 0; r < half; r++)); do echo "$full"; done; echo "$(rep d "$half"),u,$(rep d "$half")"; for ((r = 0; r < half; r++)); do echo "$full"; done
} > "$bp/cx-shelter-dig.csv"
printf '#place shelter: every category\nafunyrswebhlzSgpd(%dx%d)\n' "$n" "$n" > "$bp/cx-shelter-place.csv"
printf '#zone shelter: meeting area\nm(%dx%d)\n' "$n" "$n" > "$bp/cx-shelter-zone.csv"
x0=$((sx - half)); y0=$((sy - half))
$L cmd quickfort run cx-shelter-dig.csv -c "$x0,$y0,$sz" 2>&1 | tr -d '\r' | tail -2
$L cmd dig-now 2>&1 | tr -d '\r' | tail -1
$L cmd quickfort run cx-shelter-place.csv -c "$x0,$y0,$zb" 2>&1 | tr -d '\r' | tail -2
$L cmd quickfort run cx-shelter-zone.csv -c "$x0,$y0,$zb" 2>&1 | tr -d '\r' | tail -2
$L cmd cx-shelter wagon 2>&1 | tr -d '\r' | tail -1
echo "shelter: done (room ${x0}..$((x0 + n - 1)), ${y0}..$((y0 + n - 1)), z $zb; stair at $sx,$sy from z $sz)"
