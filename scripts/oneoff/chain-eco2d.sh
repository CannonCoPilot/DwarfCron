#!/bin/sh
# ECO2-W rerun: the first run (11:03) was vacuous -- setting Winter jumped the clock 302,400 ticks and the harness
# counted it against the budget (fixed in cx-experiment.py: the budget counts from after the t0 manipulations).
cd "$(dirname "$0")/../.."
until grep -q "=== eco2c done" data/logs/chain-eco2c.log 2>/dev/null; do sleep 20; done
echo "=== eco2d start $(date +%H:%M:%S)"
.venv/bin/python scripts/cx-experiment.py run experiments/ECO2-W.json --reps 2; echo "=== manifest ECO2-W rerun exit $?"
echo "=== eco2d done $(date +%H:%M:%S)"
