#!/bin/sh
# Item 6: a good and an evil fort on region6 (seed 424242). Survey, pick, embark GOODF/EVILF, probe, 30,000 ticks tool on.
cd "$(dirname "$0")/../.."
L=data/logs/align.log; echo "=== align start $(date +%H:%M:%S)" | tee -a $L
C=scripts/cx-lifecycle.sh
$C state >/dev/null 2>&1 || $C start >> $L 2>&1
$C title >> $L 2>&1
$C survey region6 > data/forts/region6-survey.tsv 2>> $L
.venv/bin/python scripts/oneoff/align-pick.py data/forts/region6-survey.tsv | tee data/forts/region6-align-pick.txt | tee -a $L
for kind in good evil; do
  set -- $(grep "^$kind " data/forts/region6-align-pick.txt)
  rx=$2; ry=$3; save=$(echo $kind | tr a-z A-Z)F
  [ "$rx" = none ] && { echo "=== align $kind: no tile" | tee -a $L; continue; }
  $C save-delete $save >> $L 2>&1
  $C embark region6 $rx $ry $save >> $L 2>&1 || { echo "=== align $kind embark FAILED" | tee -a $L; continue; }
  $C save-backup $save preverify >> $L 2>&1
  $C load $save >> $L 2>&1
  PRE=$(grep -v '^--' data/eco-desk/v2/research/lua/align_probe.lua | tr '\n' ' ')
  $C lua "$(echo "$PRE" | sed 's/{TAG}/pre/g')" >> $L 2>&1
  $C cmd seasonal-wildlife enable >> $L 2>&1
  $C step 30000 >> $L 2>&1
  $C lua "$(echo "$PRE" | sed 's/{TAG}/t30000/g')" >> $L 2>&1
  $C title >> $L 2>&1
  echo "=== align $kind done $save $rx,$ry" | tee -a $L
done
echo "=== align exit 0" | tee -a $L
