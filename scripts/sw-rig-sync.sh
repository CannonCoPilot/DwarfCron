#!/bin/bash
# sw-rig-sync.sh -- the rig only ever runs the seasonal-wildlife code under development (user 16 Nov 2026: "Make it so
# that the rig always can only run the latest updated version of seasonal-wildlife ... Force-update all code that the rig
# tries to test, at all times, any time there is ever any change made to seasonal-wildlife").
#
# One source of truth: $SW_DEV (cx-config.sh; default ~/Claude/Projects/sw-wt/plugin), its WORKING TREE as it stands,
# uncommitted edits included. Installed into DFHack's hack/ folder with the package's own layout (plugin/scripts/package.sh):
#   hack/scripts/seasonal-wildlife*.lua + seasonal-wildlife-web.html, hack/scripts/gui/seasonal-wildlife.lua,
#   hack/scripts/internal/seasonal-wildlife/*.lua, hack/lua/plugins/seasonal-wildlife.lua,
#   hack/plugins/seasonal-wildlife.plug.dll (rebuilt here when plugin/ sources change), hack/docs/docs/tools/seasonal-wildlife.txt
# Any other copy DFHack could load first (dfhack-config/scripts, a save's scripts/ folder) or a tool file the tree no longer
# ships is moved to $SW_RIG_STATE/quarantine/<stamp>/ (never deleted).
#
#   sw-rig-sync.sh ensure [strict|leaving|title|files]
#       strict   (default) sync, then require the code running in DF to be this tree; exit 86 (STALE) if it cannot be
#                made so without leaving a loaded fort
#       leaving  the command is about to leave any loaded fort (start/load/embark/title/genworld): restart DF for a plugin
#                change; a script change takes effect at the title (cx-lifecycle's ensure_title runs `ensure title`)
#       title    at the title: reload the scripts in DF now (no fort loaded, nothing of the old code keeps running)
#       files    sync files (and build the dll) only; never touches the running game (the watcher)
#   sw-rig-sync.sh status         tree id, branch/commit/dirty, installed match, what DF is running
#   sw-rig-sync.sh watch on|off   launchd agent: `ensure files` whenever the tree's tool files change
#
# Why a loaded fort is refused, not hot-swapped: the tool's jobs are closures of the script that scheduled them, and its
# map-load path re-snapshots raws it already changed (so `off` would restore the changed values). New code is only clean
# from a map load. Exit codes: 0 ok, 86 stale (the run must reload its fort or restart DF), 1 error.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/cx-config.sh"
SW_DEV="${SW_DEV:-$HOME/Claude/Projects/sw-wt/plugin}"
HACK="${DFHACK_HACK_DIR:-$CX_BOTTLE_DIR/drive_c/Program Files (x86)/Steam/steamapps/common/DFHack/hack}"
STATE="${SW_RIG_STATE:-$CX_SNAPSHOT_DIR/sw-rig}"
PORT="${CX_DFHACK_PORT:-5555}"
export CX_SW_GUARDED=1   # our own RPC calls must not re-enter the guard
mkdir -p "$STATE"
STALE=86
NOREAD=87   # DF is running but answered no state read (hung or busy): not stale, the caller decides (16 Nov 2026, B1 PC_EVIL)
say() { echo "[sw-rig] $*" >&2; }
die() { say "ERROR: $*"; exit 1; }
[ -d "$SW_DEV/scripts" ] || die "SW_DEV is not a seasonal-wildlife tree: $SW_DEV"
. "$SW_DEV/plugin/scripts/dfhack-target.sh"
BUILD="$SW_DEV/plugin/.build-win64$([ "$DFHACK_TAG" = 53.16-r2 ] || echo "-$DFHACK_TAG")"
DLL="$BUILD/plugins/external/seasonal-wildlife/seasonal-wildlife.plug.dll"

# --- the manifest: "dest<TAB>src" lines (dest relative to hack/) -------------------------------------------------------
manifest_scripts() {
    local f
    for f in "$SW_DEV"/scripts/seasonal-wildlife*.lua "$SW_DEV/scripts/seasonal-wildlife-web.html"; do
        [ -f "$f" ] && printf 'scripts/%s\t%s\n' "$(basename "$f")" "$f"
    done
    printf 'scripts/gui/seasonal-wildlife.lua\t%s\n' "$SW_DEV/scripts/gui/seasonal-wildlife.lua"
    for f in "$SW_DEV"/scripts/internal/seasonal-wildlife/*.lua; do
        [ -f "$f" ] && printf 'scripts/internal/seasonal-wildlife/%s\t%s\n' "$(basename "$f")" "$f"
    done
}
manifest_plugin() {
    printf 'lua/plugins/seasonal-wildlife.lua\t%s\n' "$SW_DEV/plugin/lua/seasonal-wildlife.lua"
    printf 'plugins/seasonal-wildlife.plug.dll\t%s\n' "$DLL"
}
help_txt() {   # the help file package.sh renders from the engine's help block
    awk 'f && index($0, "]====]") == 1 { exit } f { print } index($0, "--[====[") == 1 { f = 1 }' "$SW_DEV/scripts/seasonal-wildlife.lua"
}
# a content id over a manifest's sources (order fixed)
ids_of() { while IFS=$'\t' read -r d s; do printf '%s %s\n' "$d" "$(shasum "$s" 2>/dev/null | cut -c1-40)"; done | shasum | cut -c1-12; }

# --- the plugin build: when any source the dll is built from changed since the last build ------------------------------
plugin_src_id() {
    (cd "$SW_DEV/plugin" && find src CMakeLists.txt scripts/dfhack-target.sh -type f 2>/dev/null | sort | xargs shasum) | shasum | cut -c1-12
}
build_dll() {
    local want; want=$(plugin_src_id)
    if [ -f "$DLL" ] && [ "$(cat "$BUILD/.sw-src-id" 2>/dev/null)" = "$want" ]; then return 0; fi
    say "plugin sources changed (src $want): building the dll (plugin/scripts/build-win64.sh)"
    docker info >/dev/null 2>&1 || die "the plugin sources changed but Docker is not running: the dll cannot be rebuilt, so the rig would test an old plugin"
    if ! "$SW_DEV/plugin/scripts/build-win64.sh" > "$STATE/build.log" 2>&1; then
        tail -15 "$STATE/build.log" >&2; die "plugin build failed ($STATE/build.log)"
    fi
    [ -f "$DLL" ] || die "the build left no dll at $DLL"
    echo "$want" > "$BUILD/.sw-src-id"
    say "dll built: $(shasum -a 256 "$DLL" | cut -c1-16)"
}

# --- quarantine: copies DFHack might load instead of hack/'s, and tool files the tree no longer ships -------------------
quarantine() {   # quarantine <file> <why>
    local q="$STATE/quarantine/$(date +%Y%m%d-%H%M%S)"; mkdir -p "$q"
    mv "$1" "$q/$(echo "$1" | sed 's|/|__|g' | tail -c 200)" && say "moved aside ($2): $1 -> $q/"
}
clear_shadows() {
    local f
    # dfhack-config/scripts is searched before hack/scripts: any seasonal-wildlife file there shadows the tree's
    while IFS= read -r f; do quarantine "$f" "shadows hack/scripts"; done < <(find "$DF_DIR/dfhack-config/scripts" -type f \( -name 'seasonal-wildlife*' -o -path '*/internal/seasonal-wildlife/*' \) 2>/dev/null)
    # a world's own scripts/ folder is searched before hack/scripts too
    while IFS= read -r f; do quarantine "$f" "a save's scripts/ shadows hack/scripts"; done < <(find "$DF_SAVE_DIR" -maxdepth 4 -path '*/scripts/*' \( -name 'seasonal-wildlife*' -o -path '*/internal/seasonal-wildlife/*' \) -type f 2>/dev/null)
    # tool files in hack/ that the tree no longer ships (a renamed or removed helper)
    local keep; keep=$( { manifest_scripts; manifest_plugin; } | cut -f1)
    while IFS= read -r f; do
        local rel="${f#"$HACK"/}"
        # a here-string, not `echo | grep -q`: under pipefail grep -q's early exit can SIGPIPE the echo and the pipeline
        # reads as "not found" -- tool files the tree DOES ship were moved aside under a running DF (16-17 Nov 2026: 3 times,
        # B1 PC_COAST step failed "not installed after the copy: .../install.lua")
        grep -qxF "$rel" <<< "$keep" || quarantine "$f" "no longer in the tree"
    done < <(find "$HACK/scripts" -type f \( -name 'seasonal-wildlife*' -o -path '*/internal/seasonal-wildlife/*' \) 2>/dev/null)
}

# --- copy what differs; prints the classes that changed (scripts, plugin) ------------------------------------------------
sync_files() {
    local changed_s=0 changed_p=0 d s
    while IFS=$'\t' read -r d s; do
        if ! cmp -s "$s" "$HACK/$d"; then mkdir -p "$(dirname "$HACK/$d")"; cp "$s" "$HACK/$d" || die "copy failed: $d"; changed_s=1; fi
    done < <(manifest_scripts)
    local h; h=$(mktemp); help_txt > "$h"
    if ! cmp -s "$h" "$HACK/docs/docs/tools/seasonal-wildlife.txt"; then mkdir -p "$HACK/docs/docs/tools"; cp "$h" "$HACK/docs/docs/tools/seasonal-wildlife.txt"; fi
    rm -f "$h"
    while IFS=$'\t' read -r d s; do
        if ! cmp -s "$s" "$HACK/$d"; then
            if [ "$d" = plugins/seasonal-wildlife.plug.dll ] && df_running; then
                changed_p=2   # the running DF holds the dll: it is installed once DF stops (ensure restarts DF for it)
            else
                cp "$s" "$HACK/$d" || die "copy failed: $d"; changed_p=1
            fi
        fi
    done < <(manifest_plugin)
    clear_shadows
    # verify, byte for byte (the dll may wait for DF to stop)
    while IFS=$'\t' read -r d s; do cmp -s "$s" "$HACK/$d" || die "not installed after the copy: $d"; done < <(manifest_scripts)
    echo "$changed_s $changed_p"
}

df_running() { pgrep -f "Dwarf Fortress.exe" >/dev/null 2>&1; }
rpc() { "$CX_PYTHON" "$HERE/cx-rpc.py" --port "$PORT" --timeout "${2:-30}" --lua "$1" 2>/dev/null | tr -d '\r' | tail -1; }
# what the running DF is using: script tree id, plugin id, map loaded
live() { rpc "print(tostring(_G.SW_RIG_TREE), tostring(_G.SW_RIG_PLUGIN), tostring(dfhack.isMapLoaded()))"; }
# reload the scripts in a DF with no fort loaded: re-require the engine (DFHack re-reads a changed file), then stamp
reload_scripts() {   # reload_scripts <tree-id> <plugin-id>
    local out; out=$(rpc "if dfhack.isMapLoaded() then print('MAPLOADED') return end
local ok, err = pcall(function() local env = dfhack.script_environment('seasonal-wildlife', true) end)
if not ok then print('ERR ' .. tostring(err)) return end
_G.SW_RIG_TREE = '$1'; _G.SW_RIG_PLUGIN = _G.SW_RIG_PLUGIN or '$2'; print('OK')" 60)
    case "$out" in OK) return 0 ;; MAPLOADED) return $STALE ;; *) say "reload failed: $out"; return 1 ;; esac
}

tree_desc() {
    local br c dirty; br=$(git -C "$SW_DEV" rev-parse --abbrev-ref HEAD 2>/dev/null); c=$(git -C "$SW_DEV" rev-parse --short HEAD 2>/dev/null)
    dirty=$(git -C "$SW_DEV" status --porcelain -- scripts plugin/lua plugin/src 2>/dev/null | wc -l | tr -d ' ')
    echo "$SW_DEV  $br@$c$([ "$dirty" -gt 0 ] && echo " +$dirty uncommitted")"
}

ensure() {
    local mode="${1:-strict}"
    build_dll
    local tree plug; tree=$(manifest_scripts | ids_of); plug=$(manifest_plugin | ids_of)
    local ch; ch=$(sync_files) || exit 1
    echo "{\"tree\":\"$tree\",\"plugin\":\"$plug\",\"src\":\"$(tree_desc)\",\"at\":\"$(date +%FT%T)\"}" > "$STATE/installed.json"
    [ "$mode" = files ] && { [ "$ch" != "0 0" ] && say "synced $(tree_desc) (scripts $tree, plugin $plug)"; return 0; }
    df_running || return 0
    local lv; lv=$(live); local ltree lplug lmap; read -r ltree lplug lmap <<< "$lv"
    [ -n "$lmap" ] || { say "could not read the running DF's state ($lv): DF is not answering"; [ "$mode" = strict ] && return $NOREAD || return 0; }
    # a plugin change needs a fresh DF (the dll and its Lua module load once per process)
    # nil = a DF the rig did not start (or started before this guard): which plugin it loaded is unknown, so it is stale
    if [ "$lplug" != "$plug" ]; then
        if [ "$mode" = leaving ] || [ "$lmap" = false ]; then
            say "the plugin changed ($lplug -> $plug): restarting DF so it loads the new one"
            "$HERE/cx-lifecycle.sh" stop >&2 || die "could not stop DF for the plugin update"
            sync_files >/dev/null || exit 1
            "$HERE/cx-lifecycle.sh" start >/dev/null || die "DF did not restart after the plugin update"
            return 0   # start stamps the fresh process
        fi
        say "STALE: the seasonal-wildlife plugin changed ($lplug -> $plug) while a fort is loaded; restart DF (cx-lifecycle restart) and reload the fort"
        return $STALE
    fi
    [ "$ltree" = "$tree" ] && return 0
    if [ "$lmap" = false ]; then
        reload_scripts "$tree" "$plug"; local rc=$?
        [ $rc -eq 0 ] && say "DF now runs $(tree_desc) (scripts $tree)"
        return $rc
    fi
    [ "$mode" = leaving ] && return 0   # cx-lifecycle reloads them at the title (ensure title)
    say "STALE: DF has a fort loaded that runs seasonal-wildlife scripts ${ltree} but the tree is now ${tree} ($(tree_desc)); reload the fort (cx-lifecycle load <folder>) so it runs the new code"
    return $STALE
}

# stamp a freshly started DF: it loaded the dll and Lua module installed before it started, and will read the scripts now
stamp_start() {
    local tree plug; tree=$(manifest_scripts | ids_of); plug=$(manifest_plugin | ids_of)
    cmp -s "$DLL" "$HACK/plugins/seasonal-wildlife.plug.dll" || say "WARNING: the installed dll differs from the build"
    rpc "_G.SW_RIG_TREE = '$tree'; _G.SW_RIG_PLUGIN = '$plug'; print('OK')" >/dev/null
    say "DF started on $(tree_desc) (scripts $tree, plugin $plug)"
}

status() {
    local tree plug; tree=$(manifest_scripts | ids_of); plug=$(manifest_plugin | ids_of)
    echo "tree      $(tree_desc)"
    echo "ids       scripts $tree  plugin $plug  (plugin sources $(plugin_src_id), last build $(cat "$BUILD/.sw-src-id" 2>/dev/null || echo none))"
    local d s bad=0; while IFS=$'\t' read -r d s; do cmp -s "$s" "$HACK/$d" || { echo "differs   $d"; bad=1; }; done < <(manifest_scripts; manifest_plugin)
    [ $bad -eq 0 ] && echo "installed matches the tree ($HACK)"
    if df_running; then echo "DF        running: $(live) (scripts plugin map)"; else echo "DF        not running"; fi
    launchctl list 2>/dev/null | grep -q com.urist.sw-rig-sync && echo "watcher   on" || echo "watcher   off"
}

watch() {
    local plist="$HOME/Library/LaunchAgents/com.urist.sw-rig-sync.plist"
    if [ "${1:-on}" = off ]; then launchctl unload "$plist" 2>/dev/null; rm -f "$plist"; say "watcher off"; return 0; fi
    local paths="" f
    for f in "$SW_DEV/scripts" "$SW_DEV/scripts/gui" "$SW_DEV/scripts/internal/seasonal-wildlife" "$SW_DEV/plugin/src" "$SW_DEV/plugin/lua" $(manifest_scripts | cut -f2) "$SW_DEV/plugin/lua/seasonal-wildlife.lua" "$SW_DEV/.git/HEAD"; do
        paths="$paths<string>$f</string>"
    done
    # a worktree's HEAD lives in the main repo's .git/worktrees/<name>/HEAD (a branch switch)
    local gd; gd=$(git -C "$SW_DEV" rev-parse --git-dir 2>/dev/null); [ -n "$gd" ] && paths="$paths<string>$(cd "$SW_DEV" && cd "$gd" && pwd)/HEAD</string>"
    cat > "$plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>com.urist.sw-rig-sync</string>
<key>ProgramArguments</key><array><string>/bin/bash</string><string>$HERE/sw-rig-sync.sh</string><string>ensure</string><string>files</string></array>
<key>EnvironmentVariables</key><dict><key>SW_DEV</key><string>$SW_DEV</string><key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string></dict>
<key>WatchPaths</key><array>$paths</array>
<key>ThrottleInterval</key><integer>2</integer>
<key>StandardErrorPath</key><string>$STATE/watcher.log</string>
<key>StandardOutPath</key><string>$STATE/watcher.log</string>
</dict></plist>
EOF
    launchctl unload "$plist" 2>/dev/null; launchctl load "$plist" && say "watcher on ($SW_DEV; log $STATE/watcher.log)"
}

case "${1:-status}" in
    ensure) ensure "${2:-strict}" ;;
    stamp-start) stamp_start ;;
    status) status ;;
    watch) watch "${2:-on}" ;;
    *) sed -n '2,28p' "$0"; exit 1 ;;
esac
