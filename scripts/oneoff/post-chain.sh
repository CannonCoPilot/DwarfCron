#!/bin/bash
# After chain2 exits: probe the world for layer-linked civs (E23d follow-up), deploy v6.2.1 (wording only), validate-full.
cd ~/Claude/Projects/DwarfCron || exit 1
source scripts/cx-config.sh
until grep -q "=== chain2 exit" data/logs/chain2.log; do sleep 20; done
echo "=== post-chain start $(date +%T) ==="
sleep 20
R=$(ls -d data/experiments/E23d/*/ | tail -1)
echo "--- load CTRL for the probe"
scripts/cx-lifecycle.sh load CTRL; echo "load rc=$?"
sleep 15
echo "--- probe"
scripts/cx-lifecycle.sh lua "$(cat /private/tmp/claude-501/-Users-nathanielcannon-Claude-Projects-DwarfCron/df1a7cb4-013e-4d18-8473-d9d9b71f62cc/scratchpad/probe-layer-linked.oneline.lua)" 2>&1 | tee "$R/probe-layer-linked.txt"
echo "probe rc=${PIPESTATUS[0]}"
echo "--- title"
scripts/cx-lifecycle.sh title; echo "title rc=$?"
sleep 5
echo "--- deploy v6.2.1"
scripts/cx-lifecycle.sh deploy-tool ~/Claude/Projects/seasonal-wildlife/scripts; echo "deploy rc=$?"
cmp ~/Claude/Projects/seasonal-wildlife/scripts/seasonal-wildlife.lua "$DF_DIR/dfhack-config/scripts/seasonal-wildlife.lua" && cmp ~/Claude/Projects/seasonal-wildlife/scripts/gui/seasonal-wildlife.lua "$DF_DIR/dfhack-config/scripts/gui/seasonal-wildlife.lua" && echo "cmp OK both" || echo "cmp MISMATCH"
echo "--- validate-full"
: > data/logs/validate-full.log
.venv/bin/python scripts/validate-full.py > data/logs/validate-full.log 2>&1; echo "=== validate-full exit $? $(date +%T) ===" | tee -a data/logs/validate-full.log
grep -E "PASS|FAIL|DEAD|DRIFT" data/logs/validate-full.log | tail -3
echo "=== post-chain exit $(date +%T) ==="
