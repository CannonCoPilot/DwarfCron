#!/bin/bash
# package-year.sh -- the release test (rebuild plan rev 7, Phase G): install the packaged zip as a player would, with the dev
# copy removed, embark a new fort, play one year through the next year's cast build, then `off`.
#
#   scripts/package-year.sh install ZIP          DF stopped: dev copy (dfhack-config/scripts) set aside, the zip's hack/ copied
#                                                into DFHack's hack/ (old files backed up), cmp-checked
#   scripts/package-year.sh embark NAME          start DF, embark NAME on the Phase D-E tile (region16 135,23 off 11,7, 50
#                                                dwarves, size 4), breach
#   scripts/package-year.sh year NAME [TICKS]    step the loaded fort NAME TICKS (default to the next year's tick 60000) in
#                                                20,000 chunks, a named copy NAME-tNNN every 100,000 (never DF's quicksave:
#                                                it can land in an autosave slot); stops on a step that does not advance
#   scripts/package-year.sh check OUTDIR         the year's receipts: casts year, probe + nr_probe_check, errors in stderr.log,
#                                                fuse trips, then `off` and what it left
#   scripts/package-year.sh restore-dev DIR      put a set-aside dev copy back (developer use only)
set -uo pipefail
here="$(cd "$(dirname "$0")" && pwd)"; root="$(cd "$here/.." && pwd)"
C="$here/cx-lifecycle.sh"
. "$here/cx-config.sh" >/dev/null 2>&1
STEAM="$(dirname "$DF_DIR")"
HACK="$STEAM/DFHack/hack"
DEV="$DF_DIR/dfhack-config/scripts"
log() { echo "[package-year] $*"; }
die() { echo "[package-year] FATAL: $*" >&2; exit 1; }
# the rig's state word (stopped / running ...); the whole reply is read, so `head` never cuts the pipe under pipefail
rig() { "$C" status 2>/dev/null | awk 'NR==1{print $1}'; }
tick_abs() { "$C" state 2>/dev/null | tr ' ' '\n' | awk -F= '$1=="year"{y=$2} $1=="tick"{t=$2} END{print y*403200+t}'; }

case "${1:-}" in
install)
    zip="${2:-}"; [ -f "$zip" ] || die "no zip: $zip"
    [ "$(rig)" = stopped ] || die "stop DF first"
    ts=$(date +%Y%m%d-%H%M%S); bk="$root/data/package-install/$ts-v8"; mkdir -p "$bk/devcopy/gui" "$bk/hack"
    # the dev copy: every seasonal-wildlife script in dfhack-config/scripts shadows the package's (DFHack reads it first)
    n=0
    for f in "$DEV"/seasonal-wildlife*.lua "$DEV"/seasonal-wildlife-web.html "$DEV"/gui/seasonal-wildlife.lua; do
        [ -f "$f" ] || continue
        rel="${f#$DEV/}"; mkdir -p "$bk/devcopy/$(dirname "$rel")"; mv "$f" "$bk/devcopy/$rel"; n=$((n+1))
    done
    log "dev copy set aside: $n file(s) -> $bk/devcopy"
    tmp="$(mktemp -d)"; unzip -q "$zip" -d "$tmp"; pkg="$(ls -d "$tmp"/seasonal-wildlife-*)"
    (cd "$pkg" && shasum -a 256 -c SHA256SUMS >/dev/null) || die "the zip's SHA256SUMS do not match its files"
    (cd "$pkg/hack" && find . -type f) | while read -r rel; do
        [ -f "$HACK/$rel" ] && { mkdir -p "$bk/hack/$(dirname "$rel")"; cp "$HACK/$rel" "$bk/hack/$rel"; }
        mkdir -p "$HACK/$(dirname "$rel")"; cp "$pkg/hack/$rel" "$HACK/$rel"
        cmp -s "$pkg/hack/$rel" "$HACK/$rel" || die "cmp failed: $rel"
    done
    log "installed $(basename "$pkg") into $HACK ($(cd "$pkg/hack" && find . -type f | wc -l | tr -d ' ') files, cmp ok); old files -> $bk/hack"
    echo "$bk"
    ;;
embark)
    name="${2:-}"; [ -n "$name" ] || die "usage: embark NAME"
    [ "$(rig)" = running ] || "$C" start
    CX_EMBARK_SIZE=4 "$C" embark region16 135 23 "$name" 11 7 || die "embark failed"
    b=$("$C" cmd cx-load breach auto); echo "$b" | tail -1
    # the year's fort lives through it (V8PKG, 20 Oct: 63 dead by tick 291k -- cave dragons, giant cave spiders and blind
    # cave bears up the shaft, which walks both ways; BUILDINGDESTROYER 2 and 1 break a hatch): the caves stay discovered,
    # the shaft is walled in stone on the two levels under the fort floor
    col=$(echo "$b" | sed -n 's/.*breach: column \([0-9]*\),\([0-9]*\) z\([0-9]*\)\.\..*/\1 \2 \3/p' | head -1)
    if [ -n "$col" ]; then
        set -- $col
        # through Lua: `cx-lifecycle cmd` splits the quoted paint spec into words and the paint never takes
        "$C" lua "dfhack.run_command_silent('tiletypes-command p any ; p s wall ; p m stone ; p sp normal'); for _,z in ipairs({$(( $3 - 1 )),$(( $3 - 2 ))}) do dfhack.run_command_silent('tiletypes-here-point --cursor $1,$2,'..z) end; local T=df.tiletype; print('seal:', T[dfhack.maps.getTileType($1,$2,$(( $3 - 1 )))], T[dfhack.maps.getTileType($1,$2,$(( $3 - 2 )))])" | tail -1
        log "shaft sealed at $1,$2 z$(( $3 - 1 )) and z$(( $3 - 2 ))"
    else
        log "WARNING: no shaft column in the breach reply; the shaft stays open"
    fi
    "$C" cmd seasonal-wildlife cast status | head -2
    ;;
year)
    name="${2:-}"; [ -n "$name" ] || die "usage: year NAME [TICKS]"
    t0=$(tick_abs); want=${3:-$(( (t0 / 403200 + 1) * 403200 + 60000 - t0 ))}
    end=$((t0 + want)); nextsave=$((t0 + 100000))
    log "from $t0 to $end ($want ticks)"
    while :; do
        now=$(tick_abs); [ "$now" -ge "$end" ] && break
        left=$((end - now)); n=$((left < 20000 ? left : 20000))
        "$C" cmd cx-load sustain | tail -1   # rig embarks carry no drink (V8PKG: 9 died of thirst)
        "$C" step "$n" 300 | tail -1
        after=$(tick_abs)
        if "$C" screen 2>/dev/null | grep -q "settlement has crumbled"; then die "LOST: the settlement crumbled at $after; read the deaths before the engine"; fi
        [ "$after" -gt "$now" ] || die "the step did not advance ($now): a hang or a lost fort; the last named save is the restore point"
        if [ "$after" -ge "$nextsave" ]; then "$C" save "$name-t$((after / 1000))k" | tail -1; nextsave=$((nextsave + 100000)); fi
    done
    log "year done at $(tick_abs)"
    ;;
check)
    out="${2:-$root/data/package-year/$(date +%Y%m%d-%H%M%S)}"; mkdir -p "$out"
    "$C" state | tail -1 | tee "$out/state.txt"
    "$C" cmd seasonal-wildlife cast status | tee "$out/cast-status.txt" | head -2
    "$C" cmd seasonal-wildlife ledger | grep -i "cast\|build\|year" | tail -12 > "$out/ledger-casts.txt"
    "$C" cmd seasonal-wildlife groups ecology now | tail -1
    "$C" cmd seasonal-wildlife cast nrprobe nrprobe-package-year.json | tail -1
    cp "$DF_DIR/nrprobe-package-year.json" "$out/" && node "$here/castsim/nr_probe_check.js" "$out/nrprobe-package-year.json" | tee "$out/probe-check.txt" | grep -E "^(PASS|FAIL)|nr probe"
    "$C" cmd seasonal-wildlife perf | tee "$out/perf.txt" | tail -4
    grep -n "seasonal-wildlife" "$DF_DIR/stderr.log" | grep -iv "loaded plugin\|loading" | tail -40 > "$out/stderr-sw.txt"; log "stderr lines naming the tool: $(wc -l < "$out/stderr-sw.txt" | tr -d ' ')"
    "$C" lua "local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig(); print('fp_created before off: '..#(c.fp_created or {}))" | tail -1 | tee -a "$out/off.txt"
    "$C" cmd seasonal-wildlife off | tee -a "$out/off.txt" | tail -3
    "$C" lua "local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig(); print('fp_created after off: '..#(c.fp_created or {})..'; enabled '..tostring(c.enabled))" | tail -1 | tee -a "$out/off.txt"
    log "receipts in $out"
    ;;
restore-dev)
    d="${2:-}"; [ -d "$d/devcopy" ] || die "no devcopy in $d"
    [ "$(rig)" = stopped ] || die "stop DF first"
    (cd "$d/devcopy" && find . -type f) | while read -r rel; do mkdir -p "$DEV/$(dirname "$rel")"; cp "$d/devcopy/$rel" "$DEV/$rel"; done
    log "dev copy restored into $DEV"
    ;;
*) sed -n '2,15p' "$0"; exit 2 ;;
esac
