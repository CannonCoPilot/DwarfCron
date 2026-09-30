#!/bin/sh
# ECO chain 2: the water/shore blocks after the manifests (W1L stopped on 'no shore spot'; spot/spawn now look one level down)
cd "$(dirname "$0")/../.."
until grep -q "=== chain-eco done" data/logs/chain-eco.log; do sleep 15; done
echo "=== chain-eco2 start $(date +%H:%M:%S)"
.venv/bin/python scripts/eco-run.py DEPTHL,W1L,W1O,O,OS,OD,DEPTH --run data/experiments/ECO/20260929-235553
echo "=== chain-eco2 done $?"
