#!/bin/bash
# after chain-vrm: SLOTV probe (1 rep). Log data/logs/slotv.log
cd "$(dirname "$0")/../.."
until grep -q "=== chain-vrm done" data/logs/chain-vrm.log 2>/dev/null; do sleep 30; done
R=data/experiments/ECO/SLOTV-$(date +%Y%m%d-%H%M%S); .venv/bin/python scripts/eco-run.py SLOTV --run $R --reps 1 > data/logs/slotv.log 2>&1; echo "=== slotv exit $?" >> data/logs/slotv.log
