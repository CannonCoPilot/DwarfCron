#!/bin/bash
# data/pacing/savetest.sh SAVE [ROUNDS] -- does seasonal-wildlife make DF's saves come out truncated? (17 Nov 2026: in B1
# PC_COAST 3 of 7 chunk saves stopped short -- world.sav 655 KB / 663 KB / 0 B of ~5.7 MB -- while the map came back and
# the game ran on; savage and evil forts' saves were whole.) For each arm (on, off): restart DF, load SAVE, then ROUNDS x
# (step CHUNK ticks, manual save ST_<arm>_<i>, wait 60 s, record world.sav size). Off = `seasonal-wildlife off` after the
# load; norender = jobs on, water renderer off. ARMS="on off norender" picks arms (default on off); ST_PREFIX names a series. The player's dfhack-config/seasonal-wildlife.json is put back as it was, whatever happens. Results: savetest/<SAVE>.tsv
set -uo pipefail
SAVE=$1; ROUNDS=${2:-8}; CHUNK=${CHUNK:-2400}
cd ~/Claude/Projects/DwarfCron || exit 1
source scripts/cx-config.sh
L=scripts/cx-lifecycle.sh; D=data/pacing/savetest; mkdir -p "$D"; OUT="$D/$SAVE.tsv"; LOG="$D/$SAVE.log"
CFG="$DF_DIR/dfhack-config/seasonal-wildlife.json"; BAK="$D/seasonal-wildlife.json.bak"
cp -p "$CFG" "$BAK" || { echo "cannot back up $CFG" >&2; exit 1; }
restore() { cmp -s "$BAK" "$CFG" || { cp -p "$BAK" "$CFG"; echo "[savetest] restored $CFG" | tee -a "$LOG"; }; }
trap restore EXIT
log() { echo "[savetest $(date +%H:%M:%S)] $*" | tee -a "$LOG"; }
[ -f "$OUT" ] || printf 'arm\tround\tworld_sav\tfiles\tsave_rc\tnote\n' > "$OUT"
for arm in ${ARMS:-on off}; do
    $L restart >/dev/null 2>&1
    $L load "$SAVE" >> "$LOG" 2>&1 || { log "load $SAVE failed ($arm)"; continue; }
    if [ "$arm" = norender ]; then   # the tool's jobs on, the plugin's water renderer (per-frame work) off
        $L cmd aquarium depth off >> "$LOG" 2>&1 || $L cmd seasonal-wildlife water renderer off >> "$LOG" 2>&1
        log "norender: $($L cmd seasonal-wildlife status 2>&1 | head -1 | cut -c1-120)"
        restore
    fi
    if [ "$arm" = off ]; then
        $L cmd seasonal-wildlife off >> "$LOG" 2>&1
        log "off: $($L cmd seasonal-wildlife status 2>&1 | head -3 | tr '\n' ' ' | cut -c1-200)"
        restore   # `off` may have cleared the global autostart in the player's config: put it back now (the fort keeps its own off)
    fi
    $L fps 1000 10 >/dev/null 2>&1
    for i in $(seq 1 "$ROUNDS"); do
        $L cmd cx-load sustain >/dev/null 2>&1
        out=$($L step "$CHUNK" 600 2>&1) || { log "$arm $i: step failed: $(echo "$out" | tail -1)"; printf '%s\t%s\t\t\t\tstep failed\n' "$arm" "$i" >> "$OUT"; break; }
        name=$(printf '%s%s_%02d_%s' "${ST_PREFIX:-ST_}" "$arm" "$i" "$SAVE")
        $L save "$name" >> "$LOG" 2>&1; rc=$?
        sleep 60
        sz=$(stat -f %z "$DF_SAVE_DIR/$name/world.sav" 2>/dev/null || echo -1)
        nf=$(ls "$DF_SAVE_DIR/$name" 2>/dev/null | wc -l | tr -d ' ')
        # DF's resident memory (17 Nov 2026: two crashes were uncaught C++ throws in kernelbase after a few saves; watch for growth)
        rss=$(ps -o rss= -p "$(pgrep -f 'Dwarf Fortress.exe' | head -1)" 2>/dev/null | tr -d ' '); rss=$(( ${rss:-0} / 1024 ))
        printf '%s\t%s\t%s\t%s\t%s\trss %s MB\n' "$arm" "$i" "$sz" "$nf" "$rc" "$rss" >> "$OUT"
        log "$arm $i: world.sav $sz bytes, $nf files, save rc $rc, DF rss $rss MB"
        [ "$rc" -eq 87 ] && break
    done
    $L title >/dev/null 2>&1 || true
done
log "done: $OUT"
