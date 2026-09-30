#!/bin/sh
# ECO2 follow-ups: vermin at vermin-dense spots on every layer; values/flags co-located x2 reps
cd "$(dirname "$0")/../.."
until grep -q "=== eco2 done" data/logs/chain-eco2b.log; do sleep 20; done
RUN=$(ls -td data/experiments/ECO/ECO2-* | head -1)
echo "=== eco2c start $(date +%H:%M:%S) run $RUN"
scripts/cx-lifecycle.sh deploy
.venv/bin/python scripts/eco-run.py VR,VRL,VRR,VRC --run $RUN; echo "=== eco2c vermin exit $?"
.venv/bin/python scripts/eco-run.py TV2 --run $RUN --reps 2; echo "=== eco2c TV2 exit $?"
echo "=== eco2c done $(date +%H:%M:%S)"
