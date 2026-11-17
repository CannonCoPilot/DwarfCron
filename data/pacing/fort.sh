#!/bin/bash
# data/pacing/fort.sh RUN NAME WORLD RX RY [OX OY] -- one pacing fort (v8.1 pacing plan, 16 Nov 2026): embark a NEW 3x3 fort
# (50 dwarves; the tool builds its casts at embark), breach caverns 1-3, then step SEASONS seasons in CHUNK-tick chunks with
# `cx-load sustain` and the pacing probe at every checkpoint. Ends at the title, never saving. The rig runs the tree under
# development (sw-rig-sync.sh); a STALE refusal (86) stops the fort and is recorded.
#   env: SEASONS (2), CHUNK (2400), SIZE (3)
set -uo pipefail
RUN=$1; NAME=$2; WORLD=$3; RX=$4; RY=$5; OX=${6:-6}; OY=${7:-6}
cd ~/Claude/Projects/DwarfCron || exit 1
source scripts/cx-config.sh   # DF_SAVE_DIR
L=scripts/cx-lifecycle.sh; D=data/pacing/$RUN/$NAME; mkdir -p "$D"
SEASONS=${SEASONS:-2}; CHUNK=${CHUNK:-2400}; N=$(( SEASONS * 100800 / CHUNK ))
log() { echo "[$NAME $(date +%H:%M:%S)] $*" | tee -a "$D/run.log"; }
probe() { .venv/bin/python scripts/cx-rpc.py --port 5555 --timeout 120 --lua "$(cat data/pacing/probe.lua)" 2>>"$D/probe.err" | python3 -c 'import json,sys; t=sys.stdin.read(); i=t.find("{"); print(json.dumps(json.loads(t[i:]),separators=(",",":")))' 2>>"$D/probe.err"; }
probe_t() { .venv/bin/python scripts/cx-rpc.py --port 5555 --timeout 30 --lua 'print(df.global.cur_year * 403200 + df.global.cur_year_tick)' 2>/dev/null | tr -d '\r' | grep -E '^[0-9]+$' | tail -1; }
scripts/sw-rig-sync.sh status > "$D/code.txt" 2>&1
# Embark: pointer-free first (CX_EMBARK_PLACE=1; never takes the Mac); when its square does not take (16 Nov 2026, B1 PC_LAKE:
# the hover went back two region tiles), restart DF and use the aim path (moves the map under DF's pointer; takes the pointer
# only after CX_IDLE_S of no Mac input). Each attempt's log is kept (embark.log, embark-aim.log).
embark_try() { CX_EMBARK_SIZE=${SIZE:-3} $L embark "$WORLD" "$RX" "$RY" "$NAME" "$OX" "$OY"; }
if ! CX_EMBARK_PLACE=1 embark_try > "$D/embark.log" 2>&1; then
    log "pointer-free embark failed: $(grep -m1 ERROR "$D/embark.log" | cut -c1-160); retrying with the aim path"
    $L restart >/dev/null 2>&1
    CX_EMBARK_PLACE=0 embark_try > "$D/embark-aim.log" 2>&1 || { log "FAIL embark"; tail -5 "$D/embark-aim.log"; exit 1; }
fi
log "embarked $NAME at $RX,$RY ($WORLD)"
$L cmd cx-load breach auto > "$D/breach.log" 2>&1; log "$(grep -m1 -E 'breach' "$D/breach.log" || echo 'breach: none')"
$L state 2>/dev/null | tail -1 | grep -q "map=true" || { log "FAIL no map after embark"; exit 1; }
$L fps 1000 10 >/dev/null 2>&1
$L cmd seasonal-wildlife status > "$D/status-start.txt" 2>&1
probe > "$D/probe.jsonl"
# Hang recovery (16 Nov 2026, B1 PC_SAVR froze at ~29k ticks with no save to return to): save after the breach (K00_) and
# every SAVE_EVERY chunks; when a step fails, restart DF, reload the last save, drop the probe lines past it and go on.
# The same chunk hanging twice from the same save is DETERMINISTIC (a tool or DF bug, not the random fast-step hang):
# the save is kept (named in hangs.txt) and the fort stops there.
# a chunk save counts only when its world.sav is at least 70% of the save before it (17 Nov 2026: K21_PC_COAST 655 KB of 5.6 MB)
save_ok() { local a b; a=$(stat -f %z "$DF_SAVE_DIR/$1/world.sav" 2>/dev/null || echo 0); b=$(stat -f %z "$DF_SAVE_DIR/$2/world.sav" 2>/dev/null || echo 0)
            [ "$a" -gt 0 ] && [ $((a * 10)) -ge $((b * 7)) ]; }
prev=""
SAVE_EVERY=${SAVE_EVERY:-7}; ksave=0; tsave=$(probe_t); sname="K00_$NAME"; saves="$sname"
$L save "$sname" >> "$D/saves.log" 2>&1 || log "save $sname failed"
hung_at=""; tries=0; k=1
while [ "$k" -le "$N" ]; do
    $L cmd cx-load sustain >/dev/null 2>&1
    out=$($L step "$CHUNK" 600 2>&1); rc=$?
    if [ $rc -ne 0 ]; then
        log "step $k failed (rc $rc): $(echo "$out" | tail -1)"
        echo "$(date +%H:%M:%S) chunk $k rc $rc from $sname: $(echo "$out" | tail -1)" >> "$D/hangs.txt"
        if [ "$hung_at" = "$k@$sname" ]; then log "DETERMINISTIC HANG: chunk $k hung twice from $sname (kept)"; echo "DETERMINISTIC $k $sname" >> "$D/hangs.txt"; break; fi
        tries=$((tries + 1)); [ "$tries" -gt 5 ] && { log "giving up after 5 recoveries"; break; }
        hung_at="$k@$sname"
        $L restart >/dev/null 2>&1
        until $L load "$sname" >> "$D/saves.log" 2>&1; do   # a save that will not load: fall back to the one before it
            log "reload $sname failed"
            [ -n "${prev// /}" ] || { sname=""; break; }
            last=${prev##* }; prev=${prev% *}; sname=${last%%:*}; r=${last#*:}; ksave=${r%%:*}; tsave=${r#*:}
            log "falling back to $sname (chunk $ksave)"; $L restart >/dev/null 2>&1
        done
        [ -n "$sname" ] || { log "no save left to reload"; break; }
        $L fps 1000 10 >/dev/null 2>&1
        python3 - "$D/probe.jsonl" "$tsave" <<'PY'
import json, sys
p, t = sys.argv[1], int(sys.argv[2])
rows = [x for x in open(p) if x.strip().startswith('{') and json.loads(x)['t'] <= t]
open(p, 'w').writelines(rows)
PY
        log "reloaded $sname (chunk $ksave); replaying from chunk $((ksave + 1))"
        k=$((ksave + 1)); continue
    fi
    p=$(probe); [ -n "$p" ] && echo "$p" >> "$D/probe.jsonl" || log "probe $k empty"
    [ $((k % 7)) -eq 0 ] && log "checkpoint $k/$N: $(echo "$p" | python3 -c "import json,sys; d=json.load(sys.stdin); print(' '.join(f\"{l['lk']}={l['n']}/{l['cap']}\" for l in d['layers']))" 2>/dev/null)"
    if [ $((k % SAVE_EVERY)) -eq 0 ] && [ "$k" -lt "$N" ]; then
        n2=$(printf 'K%02d_%s' "$k" "$NAME")
        if $L save "$n2" >> "$D/saves.log" 2>&1 && save_ok "$n2" "$sname"; then
            prev="$prev $sname:$ksave:$tsave"; ksave=$k; sname=$n2; tsave=$(probe_t); saves="$saves $n2"
        else log "save $n2 failed or short; keeping $sname"; fi
    fi
    k=$((k + 1))
done
.venv/bin/python scripts/cx-rpc.py --port 5555 --timeout 60 --cmd seasonal-wildlife ledger 300 > "$D/ledger.txt" 2>&1
$L cmd seasonal-wildlife status > "$D/status-end.txt" 2>&1
$L cmd seasonal-wildlife groups status > "$D/groups-end.txt" 2>&1
$L title >> "$D/run.log" 2>&1 || log "FAIL title"
echo "$saves" > "$D/saves.txt"
log "DONE ($(wc -l < "$D/probe.jsonl") checkpoints; saves: $saves)"
