#!/bin/sh
# 29 Sep 2026: isolate the FPS6 pilot's worldgen crash (MEDIUM@500y, seed 6101, 71 s in).
# P1 MEDIUM@5y same seed (the preset-copy path at 129x129); P2 MEDIUM@500y same seed again (does it repeat?).
cd "$(dirname "$0")/../.."
L=data/logs/fps6-crash-probe.log
for spec in "P1 MEDIUM_REGION 5" "P2 MEDIUM_REGION 500"; do
  set -- $spec
  echo "== $1 $2 $3 $(date +%H:%M:%S)" >> $L
  scripts/cx-lifecycle.sh stop >> $L 2>&1; scripts/cx-lifecycle.sh start >> $L 2>&1
  t0=$(date +%s)
  CX_GENWORLD_TIMEOUT=5400 scripts/cx-lifecycle.sh genworld "PROBE-$1" 6101 "$2" "$3" >> $L 2>&1
  echo "== $1 rc=$? after $(( $(date +%s) - t0 ))s; newest crash log: $(ls -t "$HOME/Library/Application Support/CrossOver/Bottles/Win10/drive_c/Program Files (x86)/Steam/steamapps/common/Dwarf Fortress/crashlogs" | head -1)" >> $L
done
echo "=== probe exit" >> $L
