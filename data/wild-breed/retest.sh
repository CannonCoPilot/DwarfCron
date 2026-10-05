#!/bin/zsh
cd /Users/nathanielcannon/Claude/Projects/DwarfCron
for i in $(seq 1 3); do
  timeout 240 scripts/cx-lifecycle.sh step 20000 500 2>&1 | tail -1 || { echo "=== STEP FAILED (freeze?)"; exit 3; }
  s=$(timeout 60 .venv/bin/python scripts/cx-rpc.py --port 5555 --timeout 50 --lua "$(cat data/wild-breed/retest-sample.lua)") || { echo "=== SAMPLE FAILED (freeze?)"; exit 3; }
  echo "$s"
  t=$(echo "$s" | cut -f2)
  timeout 120 scripts/cx-lifecycle.sh save "RT_$t" 2>&1 | tail -1
done
echo "=== retest done"
