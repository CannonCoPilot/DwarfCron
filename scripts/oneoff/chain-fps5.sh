#!/bin/sh
# 29 Sep 2026: FPS5a (map size, wild held at 30) then FPS5b (a year of play per map size), 3 reps each, fresh DF per session
cd "$(dirname "$0")/../.."
.venv/bin/python scripts/fps5-run.py hold --reps 3 > data/logs/fps5a.log 2>&1; echo "=== fps5a exit $?" >> data/logs/fps5a.log
.venv/bin/python scripts/fps5-run.py long --reps 3 > data/logs/fps5b.log 2>&1; echo "=== fps5b exit $?" >> data/logs/fps5b.log
