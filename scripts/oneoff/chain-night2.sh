#!/bin/sh
# Night 30 Sep -> 1 Oct, part 2 (after chain-night.sh): item 8 season tests (S8C/S8B/S8O, also items 15/16), T9c.
cd "$(dirname "$0")/../.."
PY=.venv/bin/python
# deploy the merged v7.0 (realm table, outgun, vermin classes) between chains, never mid-block
scripts/cx-lifecycle.sh deploy-tool ~/Claude/Projects/seasonal-wildlife/scripts > data/logs/deploy-night2.log 2>&1
echo "=== deploy $(cd ~/Claude/Projects/seasonal-wildlife && git log --oneline -1 | cut -c1-8) $(date +%H:%M:%S)"
sh scripts/oneoff/chain-night1b.sh
for m in S8C S8B S8O T9c; do
    log="data/logs/${m}.log"
    echo "=== ${m} start $(date +%H:%M:%S)" | tee -a "$log"
    "$PY" scripts/cx-experiment.py run "experiments/${m}.json" >>"$log" 2>&1
    echo "=== ${m} exit $?" | tee -a "$log"
done
echo "=== chain-night2 done $(date +%H:%M:%S)"
