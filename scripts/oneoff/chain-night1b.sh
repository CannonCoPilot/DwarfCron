#!/bin/sh
# Inserted between chain-night and chain-night2: RELS2b (the clean cougar-vs-grazer arrival test).
cd "$(dirname "$0")/../.."
log=data/logs/RELS2b.log; echo "=== RELS2b start $(date +%H:%M:%S)" | tee -a $log
.venv/bin/python scripts/eco-run.py RELS2b --run data/experiments/ECO/RELS2b-$(date +%Y%m%d-%H%M%S) --reps 2 >> $log 2>&1
echo "=== RELS2b exit $?" | tee -a $log
log=data/logs/INV2.log; echo "=== INV2 start $(date +%H:%M:%S)" | tee -a $log
.venv/bin/python scripts/eco-run.py INV2 --run data/experiments/ECO/INV2-$(date +%Y%m%d-%H%M%S) --reps 2 >> $log 2>&1
echo "=== INV2 exit $?" | tee -a $log
R=data/experiments/ECO/SCV2-$(date +%Y%m%d-%H%M%S)
for b in SCV2 SCV2W; do log=data/logs/$b.log; echo "=== $b start $(date +%H:%M:%S)" | tee -a $log
.venv/bin/python scripts/eco-run.py $b --run $R --reps 2 >> $log 2>&1; echo "=== $b exit $?" | tee -a $log; done
