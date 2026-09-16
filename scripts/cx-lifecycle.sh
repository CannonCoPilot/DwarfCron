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
#   cx-lifecycle.sh load <folder># load a save (any world, any number of saves)
#   cx-lifecycle.sh state        # screen/focus/map/paused/year/tick/modal, one line
#   cx-lifecycle.sh pause|unpause
#   cx-lifecycle.sh step <ticks> # run the fort N ticks, then pause
#   cx-lifecycle.sh save [name]  # manual named save (copy), or DFHack quicksave
#   cx-lifecycle.sh title        # quit the fort WITHOUT saving, back to title
#   cx-lifecycle.sh key <KEY..>  # feed interface keys (OPTIONS, SELECT, ...)
#   cx-lifecycle.sh type <text>  # type into a text prompt
#   cx-lifecycle.sh wait <text>  # block until <text> is drawn
#   cx-lifecycle.sh screen [y0 y1]
#   cx-lifecycle.sh save-delete <folder>
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
    # The RPC listener comes up while DF is still on its splash screen
    # (viewscreen_initial_prepst); the title -- and the first-run Welcome panel
    # that returns on every cold start -- arrive several seconds later. Wait for
    # the title before clearing the panel, or the check passes vacuously.
    wait_state screen viewscreen_titlest 60 || log "WARNING: no title screen after 60s (state: $(ui_state))"
    sleep 1; log "welcome modal: $(dismiss_modal)"
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
# ---------------------------------------------------------------- flows ----
# Every in-game step is ONE atomic chronicler-ui call; the shell sequences and
# polls between them. A Lua script over RPC runs with the core suspended, so it
# can never wait for the screen to change -- see chronicler-ui.lua's header.

ui_state()  { cmd_ui state 2>/dev/null | tr -d "\r"; }
ui_get()    { ui_state | tr ' ' '\n' | sed -n "s/^$1=//p"; }   # ui_get map -> true/false

# Poll until a label is drawn. Prints "x,y" and returns 0, or returns 1.
wait_drawn() {
    local label="$1" secs="${2:-15}" out
    for _ in $(seq 1 "$secs"); do
        out=$(cmd_ui find "$label" 2>/dev/null | tr -d "\r")
        case "$out" in [0-9]*,[0-9]*) echo "$out"; return 0 ;; esac
        sleep 1
    done
    return 1
}

# Poll until a state field has a value. wait_state map true 180
wait_state() {
    local field="$1" want="$2" secs="${3:-30}" waited=0
    while [ "$waited" -lt "$secs" ]; do
        [ "$(ui_get "$field")" = "$want" ] && return 0
        sleep 2; waited=$((waited + 2))
    done
    return 1
}

click_when_drawn() {
    local label="$1" secs="${2:-15}"
    wait_drawn "$label" "$secs" >/dev/null || return 1
    cmd_ui click "$label" >/dev/null 2>&1
    sleep 1
}

# The first-run Welcome panel comes back on every cold start. Clear it before
# any title-screen work; harmless when it is not there.
dismiss_modal() { cmd_ui modal 2>/dev/null | tr -d "\r"; }

# Get to the title screen from wherever we are. A loaded fort goes through the
# Options menu and "Quit without saving" (plus its confirmation); the title
# screen with a submenu open takes LEAVESCREEN back to the main menu.
ensure_title() {
    dismiss_modal >/dev/null
    if [ "$(ui_get map)" = "true" ]; then
        cmd_title || return 1
    fi
    # The title screen's own mode says how deep we are:
    #   MAIN_MENU -> CONTINUE_ACTIVE_WORLD (world list) -> CONTINUE_ACTIVE (save list)
    # LEAVESCREEN backs out ONE level per press, so loop until MAIN_MENU.
    local i mode
    for i in 1 2 3 4 5; do
        mode=$(ui_get titlemode)
        [ -z "$mode" ] || [ "$mode" = "MAIN_MENU" ] && break
        cmd_ui key LEAVESCREEN >/dev/null 2>&1; sleep 1
    done
    [ "$(ui_get screen)" = "viewscreen_titlest" ] && [ "$(ui_get titlemode)" = "MAIN_MENU" ]
}

cmd_state() { ui_state; }
cmd_pause() { cmd_ui pause; }
cmd_unpause() { cmd_ui unpause; }

# Run the fort for N ticks, then pause. Pausing is via df.global.pause_state,
# which is honoured on the next frame; the loop reads the tick back rather
# than trusting elapsed time, because DF's tick rate varies with load.
cmd_step() {
    local ticks="${1:-100}" secs="${2:-120}" t0 t1 waited=0
    t0=$(ui_get tick); [ -n "$t0" ] || err "no map loaded"
    cmd_ui unpause >/dev/null
    # DF runs ~100 ticks/s here, so a 1s poll overshoots small steps by ~100.
    # A quarter-second poll keeps the overshoot to a few dozen ticks; each poll
    # is one RPC round trip (~20 ms).
    local i=0
    while [ "$i" -lt $((secs * 4)) ]; do
        t1=$(ui_get tick)
        [ $((t1 - t0)) -ge "$ticks" ] && break
        sleep 0.25; i=$((i + 1))
    done
    waited=$((i / 4))
    cmd_ui pause >/dev/null
    t1=$(ui_get tick)
    log "stepped $((t1 - t0)) ticks ($t0 -> $t1) in ${waited}s"
}

# Load a save by folder name. The world list groups saves BY WORLD and shows
# only "Three saves" on the world row until it is clicked; each save then draws
# as two rows -- "<fort>, Fortress" above "Folder: <name>". So: read which world
# owns the folder from the title screen's own save headers, expand that world,
# wait for the folder label, and click the row ABOVE it.
cmd_load() {
    local folder="${1:-region1}"
    is_running || err "start the session first"
    ensure_title || err "could not reach the title screen (state: $(ui_state))"
    click_when_drawn "Continue active game" || err "title screen never showed 'Continue active game'"
    wait_state titlemode CONTINUE_ACTIVE_WORLD 15 || err "clicking 'Continue active game' did not open the world list (state: $(ui_state))"
    # which world owns this folder? (tab-separated: SAVE folder world fort year)
    local world; world=$(cmd_ui saves 2>/dev/null | tr -d "\r" | awk -F'\t' -v f="$folder" '$1=="SAVE" && $2==f {print $3; exit}')
    [ -n "$world" ] || err "DF lists no save in folder '$folder' -- known: $(cmd_ui saves 2>/dev/null | awk -F'\t' '$1=="SAVE"{printf "%s ",$2}')"
    click_when_drawn "World: $world" || err "world list never showed 'World: $world'"
    wait_state titlemode CONTINUE_ACTIVE 15 || err "clicking the world row did not open its save list (state: $(ui_state))"
    wait_drawn "Folder: $folder" >/dev/null || err "save list never showed 'Folder: $folder'"
    cmd_ui clickrel "Folder: $folder" -1 "Fortress" >/dev/null 2>&1 || err "could not click the fortress row for $folder"
    log "clicked through to $folder (world: $world); waiting for the map"
    local waited=0
    while [ "$waited" -lt "$CX_LOAD_TIMEOUT" ]; do
        [ "$(ui_get map)" = "true" ] && { log "loaded after ${waited}s ($(ui_state))"; return 0; }
        sleep 3; waited=$((waited + 3))
    done
    err "no map after ${CX_LOAD_TIMEOUT}s (state: $(ui_state))"
}

# Save the loaded fort.
#   save <name>   a MANUAL save via the Options menu -> new folder <name>. This
#                 is a COPY; the folder you loaded from is untouched.
#   save          DFHack `quicksave` -> an "autosave N" folder (DF keeps 3).
# ⚠️ quicksave only completes while the game is UNPAUSED -- it sets
# plotinfo.main.autosave_request and DF services that on the game loop.
cmd_save() {
    local name="${1:-}"
    [ "$(ui_get map)" = "true" ] || err "no map loaded"
    if [ -z "$name" ]; then
        local was; was=$(ui_get paused)
        local newest_before; newest_before=$(ls -t "$SAVE_ROOT" | grep '^autosave' | head -1)
        local m0; m0=$(stat -f %m "$SAVE_ROOT/$newest_before/world.sav" 2>/dev/null || echo 0)
        cmd_ui unpause >/dev/null
        cmd_cmd quicksave >/dev/null 2>&1
        local waited=0
        while [ "$waited" -lt 60 ]; do
            sleep 2; waited=$((waited + 2))
            local newest; newest=$(ls -t "$SAVE_ROOT" | grep '^autosave' | head -1)
            local m1; m1=$(stat -f %m "$SAVE_ROOT/$newest/world.sav" 2>/dev/null || echo 0)
            [ "$m1" -gt "$m0" ] && { [ "$was" = "true" ] && cmd_ui pause >/dev/null; log "quicksaved -> $newest (${waited}s)"; return 0; }
        done
        [ "$was" = "true" ] && cmd_ui pause >/dev/null
        err "quicksave did not write an autosave within 60s"
    fi
    [ -e "$SAVE_ROOT/$name" ] && err "save '$name' already exists -- DF would refuse the name"
    cmd_ui key OPTIONS >/dev/null 2>&1
    click_when_drawn "Save and continue playing" || err "Options menu never showed 'Save and continue playing'"
    wait_drawn "name this manual" >/dev/null || err "no save-name prompt appeared"
    cmd_ui type "$name" >/dev/null 2>&1
    cmd_ui key SELECT >/dev/null 2>&1
    local waited=0
    while [ "$waited" -lt 90 ]; do
        sleep 3; waited=$((waited + 3))
        if [ -f "$SAVE_ROOT/$name/world.sav" ] && [ "$(ui_get focus)" = "dwarfmode/Default" ]; then
            log "saved -> $name ($(du -sh "$SAVE_ROOT/$name" | cut -f1), ${waited}s)"; return 0
        fi
    done
    err "manual save '$name' did not complete within 90s (state: $(ui_state))"
}

# Leave the fort WITHOUT saving and return to the title screen.
# State-aware: it may be called with the Options menu already open, or with
# the "Really quit?" confirmation already up (a previous attempt that stalled),
# and must not assume it starts from the map.
cmd_title() {
    [ "$(ui_get map)" = "true" ] || { log "no map loaded; already out of the fort"; return 0; }
    local i
    for i in 1 2 3 4 5 6; do
        if wait_drawn "Really quit" 1 >/dev/null; then
            cmd_ui clicklast "Quit" >/dev/null 2>&1
            break
        elif wait_drawn "Quit without saving" 1 >/dev/null; then
            cmd_ui click "Quit without saving" >/dev/null 2>&1
        elif [ "$(ui_get focus)" = "dwarfmode/Default" ]; then
            cmd_ui key OPTIONS >/dev/null 2>&1
        else
            # some other dwarfmode sub-screen: back out one level and retry
            cmd_ui key LEAVESCREEN >/dev/null 2>&1
        fi
        sleep 1
    done
    wait_state map false 60 || err "still in the fort after quitting (state: $(ui_state))"
    wait_state screen viewscreen_titlest 60 || err "map unloaded but not on the title screen (state: $(ui_state))"
    log "back at the title screen"
}

cmd_save_delete() {
    local name="${1:-}"; [ -n "$name" ] || err "usage: save-delete <folder>"
    [ -d "$SAVE_ROOT/$name" ] || err "no such save: $name"
    is_running && [ "$(ui_get map)" = "true" ] && err "leave the fort first (title) -- DF may hold the save open"
    rm -rf "$SAVE_ROOT/$name" && log "deleted save $name"
}

cmd_key()    { cmd_ui key "$@"; }
cmd_type()   { cmd_ui type "$@"; }
cmd_wait()   { wait_drawn "$1" "${2:-15}" || err "'$1' not drawn within ${2:-15}s"; }
cmd_screen() { cmd_ui screen "$@"; }


cmd_lua() { "$CX_PYTHON" "$SCRIPT_DIR/cx-rpc.py" --port "$(live_port)" --lua "$*"; }
# ⚠️ A script's Lua error does NOT come back over RPC -- DFHack writes it to
# stderr.log and the call simply times out, so a crashing script is
# indistinguishable from a slow one. Note the log's size before the call and
# surface any traceback that lands after it.
cmd_cmd() {
    local logf="$DF_DIR/stderr.log" before=0
    [ -f "$logf" ] && before=$(stat -f %z "$logf")
    "$CX_PYTHON" "$SCRIPT_DIR/cx-rpc.py" --port "$(live_port)" --cmd "$@"
    local rc=$?
    if [ -f "$logf" ]; then
        tail -c +$((before + 1)) "$logf" | grep -B1 -A8 -iE "error|traceback" | grep -v "Client connection" | head -20 >&2
    fi
    return $rc
}
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
    state)     cmd_state ;;
    pause)     cmd_pause ;;
    unpause)   cmd_unpause ;;
    step)      shift; cmd_step "$@" ;;
    save)      shift; cmd_save "$@" ;;
    title)     cmd_title ;;
    key)       shift; cmd_key "$@" ;;
    type)      shift; cmd_type "$@" ;;
    wait)      shift; cmd_wait "$@" ;;
    screen)    shift; cmd_screen "$@" ;;
    save-delete) shift; cmd_save_delete "$@" ;;
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
