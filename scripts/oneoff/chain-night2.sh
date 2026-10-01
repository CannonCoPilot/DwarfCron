#!/bin/sh
# Night 30 Sep -> 1 Oct, part 2 (after chain-night.sh): item 8 season tests (S8C/S8B/S8O, also items 15/16), T9c.
cd "$(dirname "$0")/../.."
PY=.venv/bin/python
for m in S8C S8B S8O T9c; do
    log="data/logs/${m}.log"
    echo "=== ${m} start $(date +%H:%M:%S)" | tee -a "$log"
    "$PY" scripts/cx-experiment.py run "experiments/${m}.json" >>"$log" 2>&1
    echo "=== ${m} exit $?" | tee -a "$log"
done
echo "=== chain-night2 done $(date +%H:%M:%S)"
