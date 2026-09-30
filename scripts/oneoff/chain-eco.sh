#!/bin/sh
# ECO chain (30 Sep 2026): after the CTRL run, the remaining eco-run blocks, then the spawn-time manifests.
cd "$(dirname "$0")/../.."
RUN=data/experiments/ECO/20260929-235553
until grep -q "=== eco-ctrl exit" data/logs/eco-ctrl.log; do sleep 10; done
echo "=== chain-eco start $(date +%H:%M:%S)"
.venv/bin/python scripts/eco-run.py S2,B,L2,W1L,DEPTHL,W1O,O,OS,OD,DEPTH --run $RUN
echo "=== eco blocks exit $?"
for m in ECO-F1 ECO-T2 ECO-N1 ECO-G1; do
  echo "=== manifest $m $(date +%H:%M:%S)"
  .venv/bin/python scripts/cx-experiment.py run experiments/$m.json
  echo "=== manifest $m exit $?"
done
echo "=== chain-eco done $(date +%H:%M:%S)"
