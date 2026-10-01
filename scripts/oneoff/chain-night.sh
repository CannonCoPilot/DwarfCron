#!/bin/sh
# eco-night chain (30 Sep 2026): the 12 new ECO blocks plus the coordinator's SW1-3 threshold-sweep addition, run
# one after another. Each block gets its own timestamped run dir and its own log under data/logs/, so a failure in
# one block does not lose the others' output and does not stop the chain (no `set -e`; each step's exit code is
# captured and printed, never checked). LAKEP is the one documented exception to the two-reps default (--reps 1: one
# run, no natural replicate variance to average -- see the final report). The "LONE --reps 10" tail step from the
# original design is deliberately DROPPED here: LONE10 is already running independently on the rig (data/logs/lone10.log).
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

run_block RELS2 RELS2 --run "data/experiments/ECO/RELS2-$(TS)" --reps 2
run_block RELS3 RELS3 --run "data/experiments/ECO/RELS3-$(TS)" --reps 2
run_block VRM4  VRM4  --run "data/experiments/ECO/VRM4-$(TS)"  --reps 2
run_block LAKEP LAKEP --run "data/experiments/ECO/LAKEP-$(TS)" --reps 1   # exception: one run, see report

# HC4's four sub-blocks share one run dir (each writes its own HC4_N.tsv into it; eco-analyze.py reads them together)
RUN_HC4="data/experiments/ECO/HC4-$(TS)"
run_block HC4_1 HC4_1 --run "$RUN_HC4" --reps 2
run_block HC4_2 HC4_2 --run "$RUN_HC4" --reps 2
run_block HC4_3 HC4_3 --run "$RUN_HC4" --reps 2
run_block HC4_P HC4_P --run "$RUN_HC4" --reps 2

RUN_GPK="data/experiments/ECO/GPK-$(TS)"
run_block GPK   GPK   --run "$RUN_GPK"  --reps 2
run_block GPKW  GPKW  --run "$RUN_GPK"  --reps 2
run_block GPKR  GPKR  --run "$RUN_GPK"  --reps 2

run_block FSH2  FSH2  --run "data/experiments/ECO/FSH2-$(TS)" --reps 2
run_block FVA   FVA   --run "data/experiments/ECO/FVA-$(TS)"  --reps 2
run_block INV   INV   --run "data/experiments/ECO/INV-$(TS)"  --reps 2

RUN_COH="data/experiments/ECO/COH-$(TS)"
run_block COH   COH   --run "$RUN_COH"  --reps 2
run_block COHO  COHO  --run "$RUN_COH"  --reps 2
run_block COHR  COHR  --run "$RUN_COH"  --reps 2

RUN_SCV="data/experiments/ECO/SCV-$(TS)"
run_block SCV   SCV   --run "$RUN_SCV"  --reps 2
run_block SCVW  SCVW  --run "$RUN_SCV"  --reps 2
run_block SCVC  SCVC  --run "$RUN_SCV"  --reps 2

# coordinator addition (mid-task, 30 Sep): SWEEP design SW1-3, 2 reps each; one shared run dir so sweep-tally.py
# can read SW1.tsv/SW2.tsv/SW3.tsv together (scripts/sweep-tally.py <run>) once the chain finishes
RUN_SW="data/experiments/ECO/SW-$(TS)"
run_block SW1   SW1   --run "$RUN_SW"  --reps 2
run_block SW2   SW2   --run "$RUN_SW"  --reps 2
run_block SW3   SW3   --run "$RUN_SW"  --reps 2

echo "=== chain-night done $(date +%H:%M:%S)"
