#!/bin/bash
# data/pacing/hangtest.sh SAVE UNTIL_TICK [ARMS] -- is a save's repeatable hang the tool's? (17 Nov 2026: PC_EVIL froze 3 of 3
# times between ticks 81.8k and 84.3k, twice from K21_PC_EVIL.) Per arm (default "off on off on"): restart DF, load SAVE
# (`off` = `seasonal-wildlife off` after the load), step CHUNK-tick chunks until cur_year_tick >= UNTIL_TICK; record
# pass or HUNG with the tick reached. The player's dfhack-config/seasonal-wildlife.json is put back as it was.
set -uo pipefail
SAVE=$1; UNTIL=$2; ARMS=${3:-off on off on}; CHUNK=${CHUNK:-2400}
cd ~/Claude/Projects/DwarfCron || exit 1
source scripts/cx-config.sh
L=scripts/cx-lifecycle.sh; D=data/pacing/hangtest; mkdir -p "$D"; OUT="$D/$SAVE.tsv"; LOG="$D/$SAVE.log"
CFG="$DF_DIR/dfhack-config/seasonal-wildlife.json"; BAK="$D/seasonal-wildlife.json.bak"
cp -p "$CFG" "$BAK" || { echo "cannot back up $CFG" >&2; exit 1; }
restore() { cmp -s "$BAK" "$CFG" || { cp -p "$BAK" "$CFG"; echo "[hangtest] restored $CFG" | tee -a "$LOG"; }; }
trap restore EXIT
log() { echo "[hangtest $(date +%H:%M:%S)] $*" | tee -a "$LOG"; }
tick() { .venv/bin/python scripts/cx-rpc.py --port 5555 --timeout 20 --lua 'print(df.global.cur_year_tick)' 2>/dev/null | tr -d '\r' | grep -E '^[0-9]+$' | tail -1; }
[ -f "$OUT" ] || printf 'arm\trun\tresult\ttick\tseconds\n' > "$OUT"
r=0
for arm in $ARMS; do
    r=$((r + 1)); t0=$SECONDS
    $L restart >/dev/null 2>&1
    $L load "$SAVE" >> "$LOG" 2>&1 || { log "load failed ($arm)"; printf '%s\t%s\tload failed\t\t\n' "$arm" "$r" >> "$OUT"; continue; }
    if [ "$arm" = off ]; then $L cmd seasonal-wildlife off >> "$LOG" 2>&1; restore; fi
    $L fps 1000 10 >/dev/null 2>&1
    res=pass; last=$(tick)
    while [ -n "$last" ] && [ "$last" -lt "$UNTIL" ]; do
        $L cmd cx-load sustain >/dev/null 2>&1
        out=$($L step "$CHUNK" 600 2>&1); rc=$?
        if [ "$rc" -ne 0 ]; then   # 87 = DF stopped answering (hung); 88 = no tick in the cap (LOST fort or a stuck screen)
            case "$rc" in 88) grep -q 'LOST' <<< "$out" && res=LOST || res=STALLED ;; *) res=HUNG ;; esac
            log "$arm run $r: step rc $rc at ~$last: $(tail -1 <<< "$out" | cut -c1-140)"; break
        fi
        last=$(tick)
    done
    printf '%s\t%s\t%s\t%s\t%s\n' "$arm" "$r" "$res" "$last" "$((SECONDS - t0))" >> "$OUT"
    log "$arm run $r: $res (tick $last, $((SECONDS - t0)) s)"
    [ "$res" = pass ] && $L title >/dev/null 2>&1
done
log "done: $OUT"
