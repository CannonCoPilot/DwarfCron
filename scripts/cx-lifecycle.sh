#!/bin/bash
# ===========================================================================
# cx-lifecycle.sh — CrossOver DF Session Management for Chronicler
# ===========================================================================
# The CrossOver counterpart to vm-lifecycle.sh. Same verbs, so the two rigs
# are interchangeable in scripts: start / stop / status / health / logs.
#
# Why this exists: the CrossOver bottle runs the SAME x86-64 Steam PE that a
# Windows player runs -- DFHack self-reports `v0.53.15 win64 STEAM` and
# `getOSType() == "windows"` -- but its RPC socket is a real macOS loopback
# socket held by `wineserver`. So there is no guest, no IP, no SCP step: the
# game's files are ordinary macOS paths and its RPC is on 127.0.0.1.
#
#   cx-lifecycle.sh start        # launch DF, wait for the RPC listener
#   cx-lifecycle.sh stop         # ask DF to quit, then reap the prefix
#   cx-lifecycle.sh status       # running? which port? which DFHack?
#   cx-lifecycle.sh health       # process + port + RPC handshake + Lua exec
#   cx-lifecycle.sh load <folder># load a save, clicking through the menus
#   cx-lifecycle.sh ui <args>    # drive the UI by on-screen text
#   cx-lifecycle.sh lua <script> # run Lua in the running game
#   cx-lifecycle.sh cmd <args>   # run a DFHack command
#   cx-lifecycle.sh logs [n]     # tail DFHack's stderr.log
#   cx-lifecycle.sh port         # print the port in use
#   cx-lifecycle.sh bottles      # list CrossOver bottles
#   cx-lifecycle.sh deploy-tool <dir>   # install a tool tree, subdirs intact
#   cx-lifecycle.sh save-backup <region> [tag]  # copy ONE save aside (cheap)
#   cx-lifecycle.sh save-restore <region.tag>
#   cx-lifecycle.sh saves        # list saves and save backups
#   cx-lifecycle.sh snapshot <n> # copy the bottle aside (CrossOver has no
#   cx-lifecycle.sh restore <n>  #   qcow2 snapshots; a bottle IS the state)
#   cx-lifecycle.sh snapshots
# ===========================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=cx-config.sh
source "$SCRIPT_DIR/cx-config.sh"

log() { echo "[cx-lifecycle] $*" >&2; }
err() { echo "[cx-lifecycle] ERROR: $*" >&2; exit 1; }

# --- state ----------------------------------------------------------------

df_pids() { pgrep -f "$DF_EXE_NAME" 2>/dev/null; }

is_running() { [ -n "$(df_pids)" ]; }

# The port DFHack is actually listening on, read from the live socket rather
# than from config -- config says what we asked for, the socket says what we
# got. They differ whenever the requested port was already taken.
live_port() {
    # NR>1 skips lsof's header row -- without it every caller gets the
    # literal string "NAME" as the port, which then fails deep inside the
    # socket layer instead of here.
    lsof -nP -iTCP -sTCP:LISTEN -a -c wineserver 2>/dev/null \
        | awk 'NR>1 {print $9}' | sed 's/.*://' | head -1
}

port_busy() { lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }

# ⚠️ macOS ControlCenter (AirPlay Receiver) listens on *:5000 -- DFHack's
# default port. On a Mac the collision is the normal case, not the exception:
# DFHack logs the bind failure to stderr.log and then simply does not start
# the server, which presents as "RPC is broken" rather than "port taken".
pick_port() {
    local p="${DFHACK_PORT:-$CX_DFHACK_PORT}"
    if port_busy "$p"; then
        local who
        who=$(lsof -nP -iTCP:"$p" -sTCP:LISTEN 2>/dev/null | awk 'NR==2{print $1}')
        log "port $p is held by ${who:-another process}; trying $CX_DFHACK_PORT_FALLBACK"
        p="$CX_DFHACK_PORT_FALLBACK"
        port_busy "$p" && err "both $CX_DFHACK_PORT and $p are in use; set DFHACK_PORT"
    fi
    echo "$p"
}

# --- commands -------------------------------------------------------------

cmd_start() {
    if is_running; then
        log "DF already running (pid $(df_pids | head -1)), port $(live_port)"
        return 0
    fi
    [ -d "$CX_BOTTLE_DIR" ] || err "no bottle at $CX_BOTTLE_DIR"
    [ -f "$DF_DIR/$DF_EXE_NAME" ] || err "no DF at $DF_DIR"

    local port; port=$(pick_port)
    log "starting DF in bottle '$CX_BOTTLE' on port $port"

    # DFHACK_DISABLE_CONSOLE: DFHack's external console deadlocks DF's event
    #   loop under some Wine builds. In-game `gui/launcher` is unaffected, and
    #   this tool drives the game over RPC anyway.
    # WINEESYNC=0: esync deadlocks DF's event loop.
    DFHACK_PORT="$port" \
    DFHACK_DISABLE_CONSOLE="${CX_DISABLE_CONSOLE:-1}" \
    WINEESYNC=0 \
    "$CXSTART" --bottle "$CX_BOTTLE" --no-wait \
               --workdir "$DF_WIN_DIR" "$DF_WIN_DIR\\$DF_EXE_NAME" \
               >>"$CX_LOG" 2>&1 &

    local waited=0
    while [ "$waited" -lt "$CX_START_TIMEOUT" ]; do
        if port_busy "$port" && [ "$(live_port)" = "$port" ]; then
            log "RPC listening on 127.0.0.1:$port after ${waited}s"
            echo "$port"
            return 0
        fi
        sleep 1; waited=$((waited + 1))
    done
    log "no RPC listener after ${CX_START_TIMEOUT}s — last lines of stderr.log:"
    tail -5 "$DF_DIR/stderr.log" >&2 2>/dev/null
    return 1
}

cmd_stop() {
    if ! is_running; then log "DF not running"; return 0; fi
    local port; port=$(live_port)

    # Ask the game to quit itself first: DFHack flushes its config and DF
    # closes the save cleanly. Killing the process loses both.
    if [ -n "$port" ]; then
        log "asking DF to quit via RPC (port $port)"
        "$CX_PYTHON" "$SCRIPT_DIR/cx-rpc.py" --port "$port" --lua \
            'dfhack.run_command("die")' >/dev/null 2>&1
    fi
    local waited=0
    while is_running && [ "$waited" -lt "$CX_STOP_TIMEOUT" ]; do
        sleep 1; waited=$((waited + 1))
    done
    if is_running; then
        log "still running after ${waited}s; terminating the prefix"
        "$WINESERVER" -k 2>/dev/null
        sleep 2
    fi
    is_running && err "could not stop DF" || log "stopped after ${waited}s"
}

cmd_status() {
    if is_running; then
        local port; port=$(live_port)
        echo "running   pid $(df_pids | tr '\n' ' ')"
        echo "port      ${port:-none}"
        echo "bottle    $CX_BOTTLE"
        echo "df        $DF_DIR"
    else
        echo "stopped"
        echo "bottle    $CX_BOTTLE"
    fi
}

cmd_health() {
    local fail=0
    if is_running; then echo "process   OK   pid $(df_pids | head -1)"
    else echo "process   DOWN"; return 1; fi

    local port; port=$(live_port)
    if [ -n "$port" ]; then echo "port      OK   127.0.0.1:$port"
    else echo "port      DOWN  (no wineserver listener)"; fail=1; fi

    if [ -n "$port" ]; then
        local ver; ver=$("$CX_PYTHON" "$SCRIPT_DIR/cx-rpc.py" --port "$port" --version 2>/dev/null)
        if [ -n "$ver" ]; then echo "rpc       OK   DFHack $ver"
        else echo "rpc       DOWN  (handshake failed)"; fail=1; fi

        local who; who=$("$CX_PYTHON" "$SCRIPT_DIR/cx-rpc.py" --port "$port" \
            --lua 'print(dfhack.getDFVersion(), dfhack.getOSType())' 2>/dev/null)
        if [ -n "$who" ]; then echo "lua       OK   $who"
        else echo "lua       DOWN  (core did not execute)"; fail=1; fi
    fi
    return $fail
}

# Deploy the in-game helpers into the bottle. No SCP: the DF directory is an
# ordinary macOS path, which is the whole point of this rig.
cmd_deploy() {
    local dest="$DF_DIR/dfhack-config/scripts"
    mkdir -p "$dest"
    cp "$SCRIPT_DIR/../chronicler/dfhack/scripts/"*.lua "$dest/" || err "deploy failed"
    log "deployed $(ls -1 "$dest"/*.lua | wc -l | tr -d ' ') script(s) to the bottle"
}

# Deploy an ARBITRARY tool tree, preserving subdirectories.
#
# ⚠️ `deploy` above is a flat `cp *.lua` from Chronicler's own directory. It
# cannot install any tool that ships a `gui/` subfolder -- which is every
# DFHack tool with a GUI entry point, including seasonal-wildlife, whose
# launcher MUST live at `gui/seasonal-wildlife.lua` for `gui/<name>` to
# resolve. Deploying that by hand is how it was done before, and a hand copy
# is not reproducible and drifts silently.
#
#   deploy-tool <src-scripts-dir> [subpath ...]
#   deploy-tool ~/Claude/Projects/seasonal-wildlife/scripts
cmd_deploy_tool() {
    local src="${1:-}"
    [ -n "$src" ] || err "usage: deploy-tool <src-scripts-dir>"
    [ -d "$src" ] || err "not a directory: $src"
    local dest="$DF_DIR/dfhack-config/scripts"
    mkdir -p "$dest"
    # -R keeps the tree; the trailing /. copies CONTENTS, not the dir itself.
    cp -R "$src/." "$dest/" || err "deploy-tool failed"
    local n
    n=$(cd "$src" && find . -name '*.lua' | wc -l | tr -d ' ')
    log "deployed $n lua file(s) from $src (tree preserved)"
    (cd "$src" && find . -name '*.lua' | sed 's|^\./|  |')
}

# Save-scoped backup. `snapshot` copies the whole 5.4 GB bottle and needs the
# session stopped; that is right for "the rig broke" but far too heavy to run
# before each destructive test. A DF save is a self-contained folder, so back
# up just that -- and it can be taken with DF running, as long as DF is not
# mid-write (i.e. not during its own save).
SAVE_ROOT="$DF_SAVE_DIR"
CX_SAVE_BACKUPS="${CX_SAVE_BACKUPS:-$CX_SNAPSHOT_DIR/saves}"

cmd_save_backup() {
    local region="${1:-}" tag="${2:-$(date +%Y%m%d-%H%M%S)}"
    [ -n "$region" ] || err "usage: save-backup <region-folder> [tag]"
    [ -d "$SAVE_ROOT/$region" ] || err "no such save: $SAVE_ROOT/$region"
    mkdir -p "$CX_SAVE_BACKUPS"
    local dest="$CX_SAVE_BACKUPS/$region.$tag"
    [ -e "$dest" ] && err "backup already exists: $dest"
    ditto "$SAVE_ROOT/$region" "$dest" || err "backup failed"
    log "backed up $region -> $dest ($(du -sh "$dest" | cut -f1))"
}

cmd_save_restore() {
    local name="${1:-}"
    [ -n "$name" ] || err "usage: save-restore <region.tag>"
    local src="$CX_SAVE_BACKUPS/$name"
    [ -d "$src" ] || err "no such backup: $src"
    is_running && err "stop the session first -- DF holds the save open"
    local region="${name%%.*}"
    rm -rf "$SAVE_ROOT/$region"
    ditto "$src" "$SAVE_ROOT/$region" || err "restore failed"
    log "restored $name -> $SAVE_ROOT/$region"
}

cmd_saves() {
    echo "-- saves in the bottle --"
    ls -1 "$SAVE_ROOT" 2>/dev/null || echo "(none)"
    echo "-- save backups --"
    ls -1 "$CX_SAVE_BACKUPS" 2>/dev/null || echo "(none)"
}

cmd_ui() { cmd_cmd chronicler-ui "$@"; }

# Load a save by clicking through DF's menus.
#
# ⚠️ Three screens, not one, and each is reached by clicking the text of the
# LAST one: "Continue active game" -> the world row -> the fortress row. The
# labels carry the world and fort names, so they are matched on the folder and
# on "Fortress" rather than on fixed strings.
cmd_load() {
    local folder="${1:-region1}"
    is_running || err "start the session first"
    cmd_ui click "Continue active game" >/dev/null 2>&1
    sleep 2
    cmd_ui click "Folder: $folder" >/dev/null 2>&1
    sleep 2
    # The third screen names the fortress; click whatever row says "Fortress".
    cmd_ui click "Fortress" >/dev/null 2>&1
    log "clicked through to $folder; waiting for the map"
    local waited=0
    while [ "$waited" -lt "$CX_LOAD_TIMEOUT" ]; do
        local focus; focus=$(cmd_ui focus 2>/dev/null | tr -d "\r")
        case "$focus" in
            dwarfmode*) log "loaded after ${waited}s ($focus)"; return 0 ;;
        esac
        sleep 3; waited=$((waited + 3))
    done
    err "no map after ${CX_LOAD_TIMEOUT}s (last screen: $(cmd_ui focus 2>/dev/null))"
}

cmd_lua() { "$CX_PYTHON" "$SCRIPT_DIR/cx-rpc.py" --port "$(live_port)" --lua "$*"; }
cmd_cmd() { "$CX_PYTHON" "$SCRIPT_DIR/cx-rpc.py" --port "$(live_port)" --cmd "$@"; }
cmd_logs() { tail -"${1:-40}" "$DF_DIR/stderr.log"; }
cmd_port() { live_port; }
cmd_bottles() { ls -1 "$CX_BOTTLES_ROOT"; }

# A CrossOver bottle is a plain directory, so "snapshot" is a copy. Unlike the
# VM's qcow2 snapshots this needs the session stopped for a consistent copy --
# same constraint, different reason.
cmd_snapshot() {
    [ -n "${1:-}" ] || err "usage: snapshot <name>"
    is_running && err "stop the session first — a copy taken mid-write is not restorable"
    mkdir -p "$CX_SNAPSHOT_DIR"
    local dest="$CX_SNAPSHOT_DIR/$1"
    [ -e "$dest" ] && err "snapshot '$1' already exists"
    log "copying bottle '$CX_BOTTLE' -> $dest (this is not small)"
    ditto "$CX_BOTTLE_DIR" "$dest" || err "copy failed"
    log "snapshot '$1' created"
}

cmd_restore() {
    [ -n "${1:-}" ] || err "usage: restore <name>"
    is_running && err "stop the session first"
    local src="$CX_SNAPSHOT_DIR/$1"
    [ -d "$src" ] || err "no snapshot '$1'"
    log "restoring '$1' over bottle '$CX_BOTTLE'"
    rm -rf "$CX_BOTTLE_DIR" && ditto "$src" "$CX_BOTTLE_DIR" || err "restore failed"
    log "restored"
}

cmd_snapshots() { ls -1 "$CX_SNAPSHOT_DIR" 2>/dev/null || echo "(none)"; }

# --- dispatch -------------------------------------------------------------

case "${1:-status}" in
    start)     shift; cmd_start "$@" ;;
    stop)      shift; cmd_stop "$@" ;;
    restart)   cmd_stop; cmd_start ;;
    status)    cmd_status ;;
    health)    cmd_health ;;
    load)      shift; cmd_load "$@" ;;
    ui)        shift; cmd_ui "$@" ;;
    deploy)    cmd_deploy ;;
    deploy-tool) shift; cmd_deploy_tool "$@" ;;
    save-backup) shift; cmd_save_backup "$@" ;;
    save-restore) shift; cmd_save_restore "$@" ;;
    saves)     cmd_saves ;;
    lua)       shift; cmd_lua "$@" ;;
    cmd)       shift; cmd_cmd "$@" ;;
    logs)      shift; cmd_logs "$@" ;;
    port)      cmd_port ;;
    bottles)   cmd_bottles ;;
    snapshot)  shift; cmd_snapshot "$@" ;;
    restore)   shift; cmd_restore "$@" ;;
    snapshots) cmd_snapshots ;;
    *)         sed -n '2,30p' "$0"; exit 1 ;;
esac
