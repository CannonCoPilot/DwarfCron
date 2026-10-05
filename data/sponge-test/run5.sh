#!/bin/zsh
# resumable: start DF, load $1, disable tool+plugin, step 20k chunks saving each as SPB_<tick>; stop at the first birth
cd /Users/nathanielcannon/Claude/Projects/DwarfCron
S=$1
timeout 120 scripts/cx-lifecycle.sh stop >/dev/null 2>&1
scripts/cx-lifecycle.sh start 2>&1 | tail -1
scripts/cx-lifecycle.sh cmd disable aquarium >/dev/null 2>&1
scripts/cx-lifecycle.sh load "$S" 2>&1 | tail -1
scripts/cx-lifecycle.sh cmd disable aquarium >/dev/null 2>&1
scripts/cx-lifecycle.sh cmd seasonal-wildlife disable >/dev/null 2>&1
scripts/cx-lifecycle.sh fps 1000 10 >/dev/null
for i in $(seq 1 12); do
  timeout 240 scripts/cx-lifecycle.sh step 20000 500 2>&1 | tail -1 || { echo "=== STEP FAILED (freeze?)"; exit 3; }
  s=$(timeout 60 .venv/bin/python scripts/cx-rpc.py --port 5555 --timeout 50 --lua "$(cat data/sponge-test/sample.lua)") || { echo "=== SAMPLE FAILED (freeze?)"; exit 3; }
  echo "$s"
  t=$(echo "$s" | head -1 | cut -f2)
  timeout 120 scripts/cx-lifecycle.sh save "SPB_$t" 2>&1 | tail -1
  if echo "$s" | grep -q "newborn sponge/crab units [1-9]"; then echo "=== birth seen"; break; fi
done
echo "=== sponge run done"
