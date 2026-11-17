#!/bin/bash
# B2: the B1 tiles re-embarked with v8.1 (sw ec63e66+: land/flying draw, cavern draw P9, ladder order P5, cavern open
# stock P10, one wave = one group P12 + tail join, swimscav P8) -- 3x3 forts in PACE (region6), 50 dwarves, breach, two seasons each; probe casts once per season.
# Compare with B1 (data/pacing/B1): per-wave dominance, days at 0, off-cast, bursts. PC_LAKE tries a shore offset.
cd ~/Claude/Projects/DwarfCron
F=data/pacing/fort.sh; L=scripts/cx-lifecycle.sh
# 17 Nov 2026 resume (user paused B2 at 10:58 for the ladder examples): SAVR, COAST done; EVIL LOST (chunk 5). CALM
# crashed DF twice at 62,18 in the Workshop overlay evil_check (cx-lifecycle embark now switches it off). LAKE moved off
# 13,6 1,1 (overlaps site 101 Swordwhip; a 13,6 square found no lake, only river) to the 16,17 lake shore: 7x7 at 1,3
# (lake + river + land; frozen until ~45k ticks, then lake 1, river 4, pond 5). B2_ONLY="P2_LAKE P2_CALM" runs a subset.
ONLY="${B2_ONLY:-}"
while read -r name rx ry ox oy size; do
  [ -z "$name" ] && continue
  [ -n "$ONLY" ] && case " $ONLY " in *" $name "*) ;; *) continue;; esac
  $L restart >/dev/null 2>&1
  SIZE="${size:-3}" $F B2 "$name" region6 "$rx" "$ry" "$ox" "$oy"
done <<'LIST'
P2_SAVR 24 11 6 6
P2_COAST 29 42 0 13
P2_EVIL 7 2 6 6
P2_LAKE 16 17 1 3 7
P2_CALM 62 18 6 6
LIST
echo "B2 ALL DONE"
