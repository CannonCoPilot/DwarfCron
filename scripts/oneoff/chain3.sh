#!/bin/bash
# chain3 (26 Sep): after the X1 rerun -- X1c on v6.2.1, then v6.4 validated, then X3 and X4 (tool off). Logs in data/logs/.
cd /Users/nathanielcannon/Claude/Projects/DwarfCron
L=scripts/cx-lifecycle.sh; PY=.venv/bin/python; SP=/private/tmp/claude-501/-Users-nathanielcannon-Claude-Projects-DwarfCron/7ba146a2-d9ad-49df-aa12-85e29404421d/scratchpad
until grep -q "=== x1 exit" data/logs/x1b.log; do sleep 10; done
$PY scripts/x1-tally.py "$(ls -td data/experiments/X1/*/ | head -1)" > data/logs/x1b-tally.txt 2>&1
$L title >/dev/null 2>&1; $L deploy-tool $SP/sw-v621/scripts > data/logs/chain3.log 2>&1
echo "=== deployed v6.2.1 $(date +%T)" >> data/logs/chain3.log
$PY scripts/cx-experiment.py run experiments/X1c.json > data/logs/x1c.log 2>&1; echo "=== x1c exit $?" >> data/logs/x1c.log
$PY scripts/x1-tally.py "$(ls -td data/experiments/X1c/*/ | head -1)" > data/logs/x1c-tally.txt 2>&1
$L title >/dev/null 2>&1; $L deploy-tool $SP/sw-v6.4/scripts >> data/logs/chain3.log 2>&1
echo "=== deployed v6.4 $(date +%T)" >> data/logs/chain3.log
SW_TOOL=$SP/sw-v6.4 $PY scripts/validate-full.py > data/logs/validate-v64.log 2>&1; echo "=== validate-full exit $?" >> data/logs/validate-v64.log
$PY scripts/cx-experiment.py run experiments/X3.json > data/logs/x3.log 2>&1; echo "=== x3 exit $?" >> data/logs/x3.log
$PY scripts/x34-tally.py "$(ls -td data/experiments/X3/*/ | head -1)" > data/logs/x3-tally.txt 2>&1
$PY scripts/cx-experiment.py run experiments/X4.json > data/logs/x4.log 2>&1; echo "=== x4 exit $?" >> data/logs/x4.log
$PY scripts/x34-tally.py "$(ls -td data/experiments/X4/*/ | head -1)" > data/logs/x4-tally.txt 2>&1
echo "=== chain3 done $(date +%T)" >> data/logs/chain3.log
