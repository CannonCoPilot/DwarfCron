#!/bin/sh
# E23e (BOATS cavern invasion with animal people), then the full validate-full on the night's final v7.0.
cd "$(dirname "$0")/../.."
L=data/logs/E23e.log; echo "=== E23e start $(date +%H:%M:%S)" | tee -a $L
.venv/bin/python scripts/cx-experiment.py run experiments/E23e.json >> $L 2>&1; echo "=== E23e exit $?" | tee -a $L
scripts/cx-lifecycle.sh title > /dev/null 2>&1
L=data/logs/validate-night.log; echo "=== validate-full start $(date +%H:%M:%S)" | tee -a $L
.venv/bin/python scripts/validate-full.py >> $L 2>&1; echo "=== validate-full exit $?" | tee -a $L
