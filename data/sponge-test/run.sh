#!/bin/zsh
cd /Users/nathanielcannon/Claude/Projects/DwarfCron
for i in $(seq 1 20); do
  scripts/cx-lifecycle.sh step 10000 200 2>&1 | tail -1
  .venv/bin/python scripts/cx-rpc.py --port 5555 --timeout 60 --lua "$(cat data/sponge-test/sample.lua)"
done
echo "=== sponge run done"
