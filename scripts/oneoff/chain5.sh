#!/bin/bash
# chain5 (27 Sep): the final v6.6 build deployed, X5 rerun (vermin via df.vermin.get_vector, a stocked small predator), v6.6 validated.
cd /Users/nathanielcannon/Claude/Projects/DwarfCron
L=scripts/cx-lifecycle.sh; PY=.venv/bin/python; SP=/private/tmp/claude-501/-Users-nathanielcannon-Claude-Projects-DwarfCron/7ba146a2-d9ad-49df-aa12-85e29404421d/scratchpad
$L title >/dev/null 2>&1; $L deploy-tool $SP/sw-v6.6/scripts > data/logs/chain5.log 2>&1; echo "=== deployed v6.6 $(git -C $SP/sw-v6.6 log -1 --format=%h) $(date +%T)" >> data/logs/chain5.log
$PY scripts/cx-experiment.py run experiments/X5.json > data/logs/x5b.log 2>&1; echo "=== x5b exit $?" >> data/logs/x5b.log
$PY scripts/x256-tally.py "$(ls -td data/experiments/X5/*/ | head -1)" > data/logs/x5b-tally.txt 2>&1
$L title >/dev/null 2>&1
SW_TOOL=$SP/sw-v6.6 $PY scripts/validate-full.py > data/logs/validate-v66b.log 2>&1; echo "=== validate-full exit $?" >> data/logs/validate-v66b.log
echo "=== chain5 done $(date +%T)" >> data/logs/chain5.log
