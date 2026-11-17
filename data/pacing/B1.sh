#!/bin/bash
# B1 baseline: five new 3x3 forts in PACE (region6), two seasons each, v8.0.0 behaviour (tree v8.1-pacing@987cffc = 46bfb87 + F1)
cd ~/Claude/Projects/DwarfCron
F=data/pacing/fort.sh; L=scripts/cx-lifecycle.sh
while read -r name rx ry ox oy; do
  [ -z "$name" ] && continue
  $L restart >/dev/null 2>&1
  $F B1 "$name" region6 "$rx" "$ry" "$ox" "$oy"
done <<'LIST'
PC_COAST 29 42 0 13
PC_CALM 62 18 6 6
LIST
echo "B1 ALL DONE"
