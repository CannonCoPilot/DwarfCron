#!/bin/sh
# 29 Sep 2026: FPS6 (world size x history length, 20 worlds, 2 seasons each) once FPS5b's resume2 has exited.
# The user asked for FPS6 to start after FPS5b. Deploy waits for FPS5b too (never deploy while an experiment runs).
cd "$(dirname "$0")/../.."
until grep -q "=== fps5b resume2 exit" data/logs/fps5b.log; do sleep 30; done
scripts/cx-lifecycle.sh deploy > data/logs/fps6.log 2>&1
.venv/bin/python scripts/fps6-run.py all >> data/logs/fps6.log 2>&1; echo "=== fps6 exit $?" >> data/logs/fps6.log
