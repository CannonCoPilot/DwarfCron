#!/bin/bash
# VRM full (2 reps) after SLOTV; the chain-vrm gate grepped 'vcreate race=' but the TSV has a tab there (smoke made=40: passed)
cd "$(dirname "$0")/../.."
until grep -q "=== slotv exit" data/logs/slotv.log 2>/dev/null; do sleep 30; done
R=data/experiments/ECO/VRM-$(date +%Y%m%d-%H%M%S); .venv/bin/python scripts/eco-run.py VRM --run $R --reps 2 > data/logs/vrm.log 2>&1; echo "=== vrm exit $?" >> data/logs/vrm.log
