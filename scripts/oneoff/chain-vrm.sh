#!/bin/bash
# after REACH: VRM smoke (1 cell) -> gate on created vermin -> VRM 2 reps -> RELS 2 reps. Logs data/logs/chain-vrm.log
cd "$(dirname "$0")/../.."
L=data/logs/chain-vrm.log
until grep -q "=== reach exit" data/logs/reach.log 2>/dev/null; do sleep 20; done
R=data/experiments/ECO/VRMSMOKE-$(date +%Y%m%d-%H%M%S)
.venv/bin/python scripts/eco-run.py VRM --run $R --reps 1 --only none >> $L 2>&1
MADE=$(grep -h "vcreate race=ROACH_LARGE" $R/VRM.tsv 2>/dev/null | grep -oE "made=[0-9]+" | head -1 | cut -d= -f2)
echo "=== vrm smoke made=${MADE:-none}" >> $L
grep -h "vcount" $R/VRM.tsv 2>/dev/null | head -4 >> $L
if [ "${MADE:-0}" -ge 30 ]; then
  R=data/experiments/ECO/VRM-$(date +%Y%m%d-%H%M%S); .venv/bin/python scripts/eco-run.py VRM --run $R --reps 2 >> $L 2>&1; echo "=== vrm exit $?" >> $L
else
  echo "=== vrm SKIPPED (smoke made ${MADE:-0} < 30)" >> $L
fi
R=data/experiments/ECO/RELS-$(date +%Y%m%d-%H%M%S); .venv/bin/python scripts/eco-run.py RELS --run $R --reps 2 >> $L 2>&1; echo "=== rels exit $?" >> $L
echo "=== chain-vrm done" >> $L
