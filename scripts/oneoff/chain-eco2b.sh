#!/bin/sh
# ECO2 chain (30 Sep 2026): every layer and water type, then the spawn-time manifests.
cd "$(dirname "$0")/../.."
RUN=data/experiments/ECO/ECO2-$(date +%Y%m%d-%H%M%S)
echo "=== eco2 start $(date +%H:%M:%S) run $RUN"
for B in CB,A2,TV HC1,HC2,HC3,HCP HR HO HL; do
  .venv/bin/python scripts/eco-run.py $B --run $RUN
  echo "=== eco2 blocks $B exit $?"
done
for m in ECO2-W ECO2-FC ECO2-G; do
  echo "=== manifest $m $(date +%H:%M:%S)"
  .venv/bin/python scripts/cx-experiment.py run experiments/$m.json
  echo "=== manifest $m exit $?"
done
echo "=== eco2 done $(date +%H:%M:%S)"
