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
#   cx-lifecycle.sh probe <args> # cx-probe: clock|units|pops|tool|provenance|release|setq|countdown
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
    # The RPC port is fixed by dfhack-config (CX_PORT, 5555 here); ask for it
    # directly first. Scanning wineserver's listeners was the old route, and on
    # 53.16 the socket is no longer owned by a process named wineserver, so the
    # scan came back empty and every wrapper call died with "connection
    # closed" while a direct --port 5555 worked. Found 2026-09-16.
    local want="${CX_PORT:-5555}"
    if lsof -nP -iTCP:"$want" -sTCP:LISTEN >/dev/null 2>&1; then echo "$want"; return 0; fi
    # NR>1 skips lsof's header row -- without it every caller gets the
    # literal string "NAME" as the port.
    lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null \
        | awk 'NR>1 && ($1 ~ /wine|Dwarf/) {print $9}' | sed 's/.*://' | head -1
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
    # DF only holds a save open while a map is loaded; at the title screen the
    # folder can be replaced in place, and the experiment runner does exactly
    # that before every replicate (a restart per replicate would cost ~40 s).
    if is_running && [ "$(ui_get map)" = "true" ]; then
        err "leave the fort first (title) -- DF holds the save open while a map is loaded"
    fi
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
    leave_site_screen
    if [ "$(ui_get screen)" = "viewscreen_choose_game_typest" ]; then
        cmd_ui click "Back to title menu" >/dev/null 2>&1; sleep 2
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

CX_TICKS_PER_YEAR=403200   # DF year length; cur_year_tick wraps here

# DF v50 puts several things behind an "Okay" button: the first-run Welcome,
# the site-screen "On your own!" notice, the arrival announcement on a new
# fort. Each one swallows the OPTIONS key until dismissed, and `dismiss_modal`
# only knows the Welcome panel. Click any Okay that is drawn; harmless when none is.
# Known dismissers, in the order they are tried. "Skip tutorial" is the
# "Quick start and short tutorial?" prompt DF shows on the site screen of a
# world that has not had a fort yet (seen 2026-09-16 on region6; region4 showed
# "On your own!" instead).
dismiss_okay() {
    local i label found
    for i in 1 2 3 4; do
        found=""
        for label in "Okay" "Skip tutorial"; do
            if cmd_ui find "$label" 2>/dev/null | tr -d "\r" | grep -q '^[0-9]*,[0-9]*'; then
                cmd_ui click "$label" >/dev/null 2>&1; sleep 1; found=1; break
            fi
        done
        [ -n "$found" ] || return 0
    done
}

# ------------------------------------------------------------ worldgen ----
# genworld <title> <seed> [preset-index] [end-year]
#
# Title -> Create new world -> Detail -> params -> Create world -> Keep world.
# All four seeds are set to <seed>, so the same call makes the same world.
# Preset 7 is SMALLER REGION (33x33), which generates in ~15s with a short
# history; see cx-embark presets for the list. Prints the new world's folder.
#
# ⚠️ A rejection dialog ("MEDIUM ELEVATION REJECTION" etc.) means the preset's
# terrain parameters do not fit its own size -- this happens when slot 0 is
# edited in place without copying a matching preset first. `params` copies, so
# a rejection now is a real one; the flow allows that rejection TYPE and logs
# it, and aborts if a second different one appears. ABORT NOW drops all the way
# to the title and the presets reload, so a failed run leaves nothing behind.
cmd_genworld() {
    local title="${1:-}" seed="${2:-}" preset="${3:-7}" endyr="${4:-5}"
    [ -n "$title" ] && [ -n "$seed" ] || err "usage: genworld <title> <seed> [preset-index=7] [end-year=5]"
    # ⚠️ DF reads the seed as a NUMBER. Two runs with text seeds WILDERPOP1 and
    # WILDERPOP2 produced byte-identical worlds (both named Gomathkar); 424242
    # produced a different one. A non-numeric seed is a silent seed of zero.
    case "$seed" in (*[!0-9]*|"") err "seed must be a whole number (DF parses it as one; text seeds all collapse to zero)";; esac
    is_running || err "start the session first"
    ensure_title || err "could not reach the title screen"
    local before; before=$(cmd_cmd cx-embark worlds 2>/dev/null | tr -d "\r" | cut -f1 | sort)
    click_when_drawn "Create new world" || err "title never showed 'Create new world'"
    wait_state screen viewscreen_new_regionst 20 || err "Create new world did not open (state: $(ui_state))"
    dismiss_okay
    click_when_drawn "Detail" 10 || err "no 'Detail' button on the world screen"
    sleep 1
    cmd_cmd cx-embark params "$preset" "$title" "$seed" "$endyr" 2>&1 | tr -d "\r" | tail -1 | sed 's/^/[cx-lifecycle] /'
    click_when_drawn "Create world" 10 || err "no 'Create world' button"
    local waited=0 allowed=""
    while [ "$waited" -lt "${CX_GENWORLD_TIMEOUT:-600}" ]; do
        sleep 3; waited=$((waited + 3))
        if wait_drawn "Keep world and return to main menu" 1 >/dev/null; then
            cmd_ui click "Keep world and return to main menu" >/dev/null 2>&1
            break
        fi
        if wait_drawn "ALLOW THIS REJECTION TYPE" 1 >/dev/null; then
            local kind; kind=$(cmd_ui screen 0 6 2>/dev/null | tr -d "\r" | grep -o '[A-Z][A-Z ]*REJECTION' | head -1)
            [ -n "$allowed" ] && [ "$allowed" != "$kind" ] && err "second rejection type ($kind after $allowed); aborting worldgen"
            allowed="$kind"; log "worldgen rejection: $kind -- allowing that type"
            cmd_ui click "ALLOW THIS REJECTION TYPE" >/dev/null 2>&1
        fi
        [ "$(ui_get screen)" = "viewscreen_titlest" ] && err "dropped to the title during worldgen"
    done
    wait_state screen viewscreen_titlest 60 || err "did not return to the title after keeping the world"
    local after; after=$(cmd_cmd cx-embark worlds 2>/dev/null | tr -d "\r" | cut -f1 | sort)
    local folder; folder=$(comm -13 <(echo "$before") <(echo "$after") | head -1)
    [ -n "$folder" ] || err "no new world folder appeared (before: $(echo $before); after: $(echo $after))"
    log "world '$title' seed=$seed -> folder $folder (${waited}s)"
    echo "$folder"
}

# --------------------------------------------------------------- embark ----
# embark <world-folder> <region-x> <region-y> <save-name> [size=4]
#
# Title -> Start new game in existing world -> the world -> Fortress -> site
# screen -> centre the view on the tile -> Embark -> place by REAL pointer
# clicks until the read-back matches -> Confirm -> Play now -> map -> save.
#
# The embark square is placed with its top-left at mid-level tile
# (rx*16+6, ry*16+6), so a 4x4 sits wholly inside the region tile: one tile,
# one biome, no neighbour bleeding in. The placement loop clicks the map
# centre, reads where DF put the square, and moves the pointer by the
# difference at 16 px per mid-level tile; two iterations is the norm.
#
# ⚠️ Map clicks are physical pointer events (cx-mouse.py), because DF resolves
# a map click from the previous frame's hover. The flow refuses to click
# unless DF is the frontmost application, so a stray click cannot land in
# another window.
CX_MAP_CENTER_PX="${CX_MAP_CENTER_PX:-961}"   # pixel under zoom_cent on this rig's 1920x1072 window
CX_MAP_CENTER_PY="${CX_MAP_CENTER_PY:-552}"
CX_MM_PX=16                                      # pixels per mid-level tile in the zoomed view

df_frontmost() {
    [ "$(osascript -e 'tell application "System Events" to get name of first process whose frontmost is true' 2>/dev/null)" = "Dwarf Fortress.exe" ]
}

# The site screen has no Back button. LEAVESCREEN opens a small dialog whose
# "Return to title" is the exit; a second LEAVESCREEN closes that dialog again,
# which is why blindly pressing it five times (ensure_title's loop) can end
# either way. Press once, click the exit, wait for the title.
leave_site_screen() {
    [ "$(ui_get screen)" = "viewscreen_choose_start_sitest" ] || return 0
    local i
    for i in 1 2 3; do
        cmd_ui key LEAVESCREEN >/dev/null 2>&1; sleep 1
        if wait_drawn "Return to title" 2 >/dev/null; then
            cmd_ui click "Return to title" >/dev/null 2>&1
            wait_state screen viewscreen_titlest 30 && return 0
        fi
        "$CX_PYTHON" "$SCRIPT_DIR/cx-mouse.py" key esc >/dev/null 2>&1; sleep 1
        if wait_drawn "Return to title" 2 >/dev/null; then
            cmd_ui click "Return to title" >/dev/null 2>&1
            wait_state screen viewscreen_titlest 30 && return 0
        fi
    done
    # ⚠️ The dialog does not reliably appear (seen 2026-09-16: it came up once
    # and never again on the same screen). Nothing on the site screen is
    # unsaved, so the honest exit is a restart: ~40s, and it always works.
    log "site screen would not exit; restarting DF to get back to the title"
    cmd_stop >/dev/null 2>&1; sleep 2
    cmd_start >/dev/null 2>&1 || return 1
    dismiss_modal >/dev/null
    [ "$(ui_get screen)" = "viewscreen_titlest" ]
}

# Title -> world -> Fortress -> site screen, with the site-screen notice dismissed.
open_site_screen() {
    local world="$1"
    ensure_title || err "could not reach the title screen"
    local wname; wname=$(cmd_cmd cx-embark worlds 2>/dev/null | tr -d "\r" | awk -F'\t' -v f="$world" '$1==f {print $2; exit}')
    [ -n "$wname" ] || err "DF lists no world in folder '$world'"
    click_when_drawn "Start new game in existing world" || err "title never showed 'Start new game in existing world'"
    click_when_drawn "World: $wname" || err "world list never showed 'World: $wname'"
    wait_state screen viewscreen_choose_game_typest 90 || err "world did not load to the game-type screen (state: $(ui_state))"
    click_when_drawn "Fortress" || err "no 'Fortress' choice"
    wait_state screen viewscreen_choose_start_sitest 60 || err "no site screen (state: $(ui_state))"
    dismiss_okay
}

# survey <world-folder> [biome-substring]
# One TSV row per region tile of the world: biome, river/lake/site flags,
# savagery, evilness, elevation, volcanism, and how many of the 8 neighbours
# share the biome, carry a river, or are ocean. Returns to the title.
cmd_rivers() {
    local world="${1:-}"
    [ -n "$world" ] || err "usage: rivers <world-folder>"
    is_running || err "start the session first"
    open_site_screen "$world"
    cmd_cmd cx-embark rivers 2>/dev/null | tr -d "\r"
    leave_site_screen || log "could not get back to the title after the river survey (state: $(ui_state))"
}

cmd_survey() {
    local world="${1:-}" filter="${2:-}"
    [ -n "$world" ] || err "usage: survey <world-folder> [biome-substring]"
    is_running || err "start the session first"
    open_site_screen "$world"
    cmd_cmd cx-embark survey $filter 2>/dev/null | tr -d "\r"
    leave_site_screen || log "could not get back to the title after the survey (state: $(ui_state))"
}

# facts [save]   load <save> if given, print the fort's site record, tiles,
# edge ownership, features, population counts per layer, and clock, then leave.
cmd_facts() {
    local save="${1:-}"
    if [ -n "$save" ]; then cmd_load "$save" >/dev/null 2>&1 || err "could not load $save"; fi
    [ "$(ui_get map)" = "true" ] || err "no map loaded"
    dismiss_okay
    "$CX_PYTHON" "$SCRIPT_DIR/cx-rpc.py" --port "$(live_port)" --timeout 120 --cmd cx-embark facts 2>&1 | tr -d "\r"
    [ -n "$save" ] && cmd_title >/dev/null 2>&1
}

# embark <world-folder> <region-x> <region-y> <save-name> [off-x=6] [off-y=6]
# off-x/off-y place the 4x4's top-left within the region tile (0..15). The
# default 6,6 keeps the square wholly inside one tile; 14,6 straddles the
# tile to its east two-and-two, which is the even split the F2 experiment needs.
cmd_embark() {
    local world="${1:-}" rx="${2:-}" ry="${3:-}" name="${4:-}" ox="${5:-6}" oy="${6:-6}"
    [ -n "$world" ] && [ -n "$rx" ] && [ -n "$ry" ] && [ -n "$name" ] || err "usage: embark <world-folder> <region-x> <region-y> <save-name> [off-x=6] [off-y=6]"
    is_running || err "start the session first"
    [ -e "$SAVE_ROOT/$name" ] && err "save '$name' already exists"
    open_site_screen "$world"
    cmd_cmd cx-embark center "$rx" "$ry" 2>/dev/null | tr -d "\r" | tail -1 | sed 's/^/[cx-lifecycle] /'
    sleep 1
    # Enter placement mode and PROVE it before any pointer click. The site-screen
    # notice can appear after dismiss_okay ran, in which case the Embark click
    # lands on the notice and choosing_embark stays false -- seen 2026-09-16,
    # when the loop then chased a 0,0 read-back to pixel 20801,25512.
    local rd i
    for i in 1 2 3; do
        dismiss_okay
        cmd_ui clicklast "Embark" >/dev/null 2>&1
        sleep 1
        rd=$(cmd_cmd cx-embark read 2>/dev/null | tr -d "\r" | tail -1)
        case "$rd" in *choosing=true*) break;; esac
        [ "$i" = 3 ] && err "Embark did not enter placement mode: $rd"
    done
    local tx=$((rx * 16 + ox)) ty=$((ry * 16 + oy)) px="$CX_MAP_CENTER_PX" py="$CX_MAP_CENTER_PY" mx my
    for i in 1 2 3 4 5; do
        # never post a pointer event outside the DF window
        { [ "$px" -ge 0 ] && [ "$px" -lt 1920 ] && [ "$py" -ge 0 ] && [ "$py" -lt 1072 ]; } || err "placement pixel $px,$py is off the window; refusing"
        "$CX_PYTHON" "$SCRIPT_DIR/cx-mouse.py" activate >/dev/null 2>&1
        df_frontmost || err "Dwarf Fortress is not the frontmost app; refusing to send pointer clicks"
        "$CX_PYTHON" "$SCRIPT_DIR/cx-mouse.py" click "$px" "$py" >/dev/null 2>&1
        sleep 1
        rd=$(cmd_cmd cx-embark read 2>/dev/null | tr -d "\r" | tail -1)
        mx=$(echo "$rd" | sed -n 's/.*mm_min=\([0-9-]*\),.*/\1/p'); my=$(echo "$rd" | sed -n 's/.*mm_min=[0-9-]*,\([0-9-]*\) .*/\1/p')
        log "placement $i: click $px,$py -> $rd"
        [ -n "$mx" ] && [ -n "$my" ] || err "could not read the placement (state: $(ui_state))"
        case "$rd" in *choosing=true*|*confirm=true*) ;; *) err "left placement mode unexpectedly: $rd";; esac
        if [ "$mx" = "$tx" ] && [ "$my" = "$ty" ]; then
            case "$rd" in *confirm=true*) cmd_ui click "Confirm" >/dev/null 2>&1 ;; esac
            break
        fi
        case "$rd" in *confirm=true*) cmd_ui click "Abort" >/dev/null 2>&1; sleep 1 ;; esac
        px=$((px + (tx - mx) * CX_MM_PX)); py=$((py + (ty - my) * CX_MM_PX))
        [ "$i" = 5 ] && err "placement did not converge on $tx,$ty (last $mx,$my)"
    done
    wait_state screen viewscreen_setupdwarfgamest 30 || err "Confirm did not open the preparation screen (state: $(ui_state))"
    click_when_drawn "Play now!" || err "no 'Play now!' on the preparation screen"
    wait_state map true "$CX_LOAD_TIMEOUT" || err "map never loaded (state: $(ui_state))"
    sleep 2; dismiss_okay
    cmd_ui pause >/dev/null
    cmd_save "$name"
    log "embarked: world $world tile $rx,$ry -> save $name ($(ui_state))"
}

cmd_state() { ui_state; }
cmd_pause() { cmd_ui pause; }
cmd_unpause() { cmd_ui unpause; }

# Drain queued popup messages. A popup sitting in world.status.popups HALTS the
# simulation: DF keeps rendering at full fps, pause_state stays false, the focus
# stays dwarfmode -- and cur_year_tick does not move. An unattended run therefore
# reports "stepped 0 ticks" forever with every other signal saying healthy.
# Seen 2026-09-16 at tick 216440, an outpost liaison and caravan arriving during
# S1; clearing the queue resumed the fort instantly (326 ticks in 2s). Announcements
# are lost, which is the right trade for an automated rig.
# Prints the number drained, or nothing.
drain_popups() {
    cmd_lua 'local p = df.global.world.status.popups; local n = #p; while #p > 0 do p:erase(0) end; if n > 0 then print(n) end' 2>/dev/null | tr -d "\r"
}
cmd_popups() { local n; n=$(drain_popups); log "drained ${n:-0} queued popup(s)"; }

# Simulation speed. In fortress mode a frame IS a tick, so enabler.fps is the tick rate
# cap and raising it is the honest way to run a long trial -- the game logic is unchanged,
# only how fast DF is allowed to iterate it. gfps is dropped alongside, because rendering
# frames the rig never looks at just steals CPU from the simulation.
#
# ⚠️ NEVER set fps (or calculated_fps) to 0. It does not mean "uncapped" -- it freezes the
# game permanently and the only way out is killing DF. The floor below is deliberate; use
# the timestream plugin if you ever want sub-normal pacing.
#
#   cx-lifecycle.sh fps            # report caps and achieved rates
#   cx-lifecycle.sh fps 1000 [10]  # set tick cap, and optionally the graphics cap
cmd_fps() {
    local want="${1:-}" g="${2:-}"
    if [ -z "$want" ]; then
        cmd_lua 'local e = df.global.enabler
            print(("fps cap=%s achieved=%s | gfps cap=%s achieved=%s"):format(e.fps, e.calculated_fps, e.gfps, e.calculated_gfps))'
        return 0
    fi
    case "$want" in (*[!0-9]*|"") err "fps must be a whole number (got '$want')";; esac
    [ "$want" -lt 10 ] && err "refusing fps=$want: 0 freezes DF permanently and anything under 10 is indistinguishable from a hang"
    if [ -n "$g" ]; then
        case "$g" in (*[!0-9]*) err "gfps must be a whole number (got '$g')";; esac
        [ "$g" -lt 1 ] && err "refusing gfps=$g"
    fi
    cmd_lua "local e = df.global.enabler
        e.fps = $want
        $( [ -n "$g" ] && echo "e.gfps = $g" )
        print(('fps cap now %s, gfps cap now %s'):format(e.fps, e.gfps))"
}

# Run the fort for N ticks, then pause. Pausing is via df.global.pause_state,
# which is honoured on the next frame; the loop reads the tick back rather
# than trusting elapsed time, because DF's tick rate varies with load.
cmd_step() {
    local ticks="${1:-100}" secs="${2:-120}" t0 t1 waited=0 drained
    t0=$(ui_get tick); [ -n "$t0" ] || err "no map loaded"
    drained=$(drain_popups); [ -n "$drained" ] && log "drained $drained queued popup(s) before stepping"
    cmd_ui unpause >/dev/null
    # DF runs ~100 ticks/s here, so a 1s poll overshoots small steps by ~100.
    # A quarter-second poll keeps the overshoot to a few dozen ticks; each poll
    # is one RPC round trip (~20 ms).
    # cur_year_tick RESETS to 0 at the new year (403,200 ticks), so a naive t1-t0 goes
    # hugely negative and the loop waits out its whole timeout on a fort that is running
    # perfectly. Seen 2026-09-16: "stepped -307819 ticks (401790 -> 93971) in 200s".
    local i=0 last="$t0" stalled=0 delta=0
    while [ "$i" -lt $((secs * 4)) ]; do
        t1=$(ui_get tick)
        delta=$((t1 - t0)); [ "$delta" -lt 0 ] && delta=$((delta + CX_TICKS_PER_YEAR))
        [ "$delta" -ge "$ticks" ] && break
        # a popup can be queued mid-step; notice a stall and clear it rather than
        # burning the whole timeout on a fort that has stopped moving
        if [ "$t1" = "$last" ]; then
            stalled=$((stalled + 1))
            if [ "$stalled" -ge 20 ]; then
                drained=$(drain_popups)
                [ -n "$drained" ] && log "drained $drained queued popup(s) mid-step (fort had stalled at $t1)"
                # A screen other than the map freezes the simulation whatever pause_state says.
                # Seen 2026-09-18 on OCEAN2: both E20 replicates died with the focus on
                # dwarfmode/Options and the tick frozen, burning the whole 400 s timeout.
                # LEAVESCREEN backs out one level per press; three is enough for any menu
                # the rig can land in, and it is a no-op on the map itself.
                local foc; foc=$(cmd_ui focus 2>/dev/null | tr -d '\r')
                case "$foc" in
                    dwarfmode/Default|"") : ;;
                    *)  log "focus was $foc mid-step; backing out to the map"
                        for _ in 1 2 3; do
                            cmd_ui key LEAVESCREEN >/dev/null 2>&1; sleep 0.5
                            foc=$(cmd_ui focus 2>/dev/null | tr -d '\r')
                            [ "$foc" = "dwarfmode/Default" ] && break
                        done ;;
                esac
                cmd_ui unpause >/dev/null
                stalled=0
            fi
        else
            stalled=0; last="$t1"
        fi
        sleep 0.25; i=$((i + 1))
    done
    waited=$((i / 4))
    cmd_ui pause >/dev/null
    t1=$(ui_get tick)
    delta=$((t1 - t0)); [ "$delta" -lt 0 ] && delta=$((delta + CX_TICKS_PER_YEAR))
    log "stepped $delta ticks ($t0 -> $t1) in ${waited}s"
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
    # a previous load can leave the title in its Continue submenu (titlemode CONTINUE_ACTIVE*); back out to the main menu first
    local tries=0
    while [ "$(ui_get titlemode)" != "MAIN_MENU" ] && [ "$tries" -lt 4 ]; do
        cmd_ui key LEAVESCREEN >/dev/null 2>&1; sleep 1; tries=$((tries + 1))
    done
    [ "$(ui_get titlemode)" = "MAIN_MENU" ] || err "title is stuck in $(ui_get titlemode); could not back out to the main menu"
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
    dismiss_okay
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
    popups)    shift; cmd_popups "$@" ;;
    genworld)  shift; cmd_genworld "$@" ;;
    survey)    shift; cmd_survey "$@" ;;
    rivers)    shift; cmd_rivers "$@" ;;
    facts)     shift; cmd_facts "$@" ;;
    embark)    shift; cmd_embark "$@" ;;
    fps)       shift; cmd_fps "$@" ;;
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
    probe)     shift; cmd_cmd cx-probe "$@" ;;
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
