#!/bin/zsh
cd /Users/nathanielcannon/Claude/Projects/DwarfCron
saved_preg=1
for i in $(seq 1 24); do
  scripts/cx-lifecycle.sh step 20000 500 2>&1 | tail -1
  s=$(.venv/bin/python scripts/cx-rpc.py --port 5555 --timeout 60 --lua "$(cat data/sponge-test/sample.lua)")
  echo "$s"
  if [ $saved_preg -eq 0 ] && echo "$s" | grep -q "preg=[1-9]"; then scripts/cx-lifecycle.sh save SPONGE2preg 2>&1 | tail -1; saved_preg=1; fi
  if echo "$s" | grep -q "newborn sponge/crab units [1-9]"; then scripts/cx-lifecycle.sh save SPONGE2born4 2>&1 | tail -1; echo "=== birth seen"; break; fi
done
echo "=== sponge run done"
