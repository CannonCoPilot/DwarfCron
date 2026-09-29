#!/bin/sh
# 28 Sep 2026: FPS2b starts when FPS4 ends, on a freshly started DF (FPS3: process age dominates timing)
cd "$(dirname "$0")/../.."
until grep -q "=== fps4 resume exit" data/logs/fps4.log; do sleep 20; done
scripts/cx-lifecycle.sh stop; scripts/cx-lifecycle.sh start
.venv/bin/python scripts/cx-experiment.py run experiments/FPS2b.json > data/logs/fps2b.log 2>&1
echo "=== fps2b exit $?" >> data/logs/fps2b.log
