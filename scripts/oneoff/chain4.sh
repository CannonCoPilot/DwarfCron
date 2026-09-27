#!/bin/bash
# chain4 (26 Sep): after chain3 -- X1 on the v6.4 build (extinct-flag hold), v6.5 validated + X2, v6.6 validated + X5 + X6.
cd /Users/nathanielcannon/Claude/Projects/DwarfCron
L=scripts/cx-lifecycle.sh; PY=.venv/bin/python; SP=/private/tmp/claude-501/-Users-nathanielcannon-Claude-Projects-DwarfCron/7ba146a2-d9ad-49df-aa12-85e29404421d/scratchpad
until grep -q "=== chain3 done" data/logs/chain3.log 2>/dev/null; do sleep 15; done
echo "=== chain4 start $(date +%T)" > data/logs/chain4.log
$PY scripts/cx-experiment.py run experiments/X1.json > data/logs/x1d.log 2>&1; echo "=== x1 exit $?" >> data/logs/x1d.log
$PY scripts/x1-tally.py "$(ls -td data/experiments/X1/*/ | head -1)" > data/logs/x1d-tally.txt 2>&1
$L title >/dev/null 2>&1; $L deploy-tool $SP/sw-v6.5/scripts >> data/logs/chain4.log 2>&1; echo "=== deployed v6.5 $(date +%T)" >> data/logs/chain4.log
SW_TOOL=$SP/sw-v6.5 $PY scripts/validate-full.py > data/logs/validate-v65.log 2>&1; echo "=== validate-full exit $?" >> data/logs/validate-v65.log
$PY scripts/cx-experiment.py run experiments/X2.json > data/logs/x2.log 2>&1; echo "=== x2 exit $?" >> data/logs/x2.log
$PY scripts/x256-tally.py "$(ls -td data/experiments/X2/*/ | head -1)" > data/logs/x2-tally.txt 2>&1
$L title >/dev/null 2>&1; $L deploy-tool $SP/sw-v6.6/scripts >> data/logs/chain4.log 2>&1; echo "=== deployed v6.6 $(date +%T)" >> data/logs/chain4.log
SW_TOOL=$SP/sw-v6.6 $PY scripts/validate-full.py > data/logs/validate-v66.log 2>&1; echo "=== validate-full exit $?" >> data/logs/validate-v66.log
$PY scripts/cx-experiment.py run experiments/X5.json > data/logs/x5.log 2>&1; echo "=== x5 exit $?" >> data/logs/x5.log
$PY scripts/x256-tally.py "$(ls -td data/experiments/X5/*/ | head -1)" > data/logs/x5-tally.txt 2>&1
$PY scripts/cx-experiment.py run experiments/X6.json > data/logs/x6.log 2>&1; echo "=== x6 exit $?" >> data/logs/x6.log
$PY scripts/x256-tally.py "$(ls -td data/experiments/X6/*/ | head -1)" > data/logs/x6-tally.txt 2>&1
echo "=== chain4 done $(date +%T)" >> data/logs/chain4.log
