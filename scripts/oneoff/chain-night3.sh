#!/bin/sh
# Night 30 Sep -> 1 Oct, part 3 (after chain-night.sh / chain-night2.sh): the SWEEP design's remaining rig blocks
# (experiments/SWEEP-design.md section 3, items 4-7). SW1-3 already ran in chain-night.sh's own RUN_SW dir; SW4-7
# get a fresh shared run dir here so sweep-tally.py can read SW5/SW6/SW7 together (scripts/sweep-tally.py <run>) once
# the chain finishes -- SW4 is not covered by that script (see scripts/sweep-tally.py's own docstring: it runs
# disarmed and reads a guild census, a different metric, left as a documented follow-up). SW7 runs because D1
# (experiments/SWEEP-D1.md) found CTRL's and BOATS's rosters both change at every pack-bonus level tested against
# the current value -- the design's own trigger for it ("Goes to the rig (SW7) only if CTRL's roster changes").
# Each block gets its own log under data/logs/ and keeps going on failure (no `set -e`; exit code printed, not
# checked), same convention as chain-night.sh/chain-night2.sh.
cd "$(dirname "$0")/../.."

PY=.venv/bin/python
TS() { date +%Y%m%d-%H%M%S; }

run_block() {
    name="$1"; shift
    log="data/logs/${name}.log"
    echo "=== ${name} start $(date +%H:%M:%S)" | tee -a "$log"
    "$PY" scripts/eco-run.py "$@" >>"$log" 2>&1
    rc=$?
    echo "=== ${name} exit ${rc}" | tee -a "$log"
    return 0   # never abort the chain
}

RUN_SW4="data/experiments/ECO/SW4-$(TS)"
run_block SW4   SW4   --run "$RUN_SW4" --reps 2

RUN_SW="data/experiments/ECO/SW-rig2-$(TS)"
run_block SW5   SW5   --run "$RUN_SW"  --reps 2
run_block SW6   SW6   --run "$RUN_SW"  --reps 2
run_block SW7   SW7   --run "$RUN_SW"  --reps 2

echo "=== chain-night3 done $(date +%H:%M:%S)"
