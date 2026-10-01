#!/bin/sh
# Inserted between chain-night and chain-night2: RELS2b (the clean cougar-vs-grazer arrival test).
cd "$(dirname "$0")/../.."
log=data/logs/RELS2b.log; echo "=== RELS2b start $(date +%H:%M:%S)" | tee -a $log
.venv/bin/python scripts/eco-run.py RELS2b --run data/experiments/ECO/RELS2b-$(date +%Y%m%d-%H%M%S) --reps 2 >> $log 2>&1
echo "=== RELS2b exit $?" | tee -a $log
