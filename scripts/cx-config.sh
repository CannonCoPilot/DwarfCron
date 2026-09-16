#!/bin/bash
# ===========================================================================
# cx-config.sh — shared configuration for the CrossOver DF rig
# ===========================================================================
# Sourced by cx-lifecycle.sh. The VM counterpart is vm-config.sh.
# ===========================================================================

# --- CrossOver ------------------------------------------------------------
CX_APP="${CX_APP:-/Applications/CrossOver.app}"
CX_SUPPORT="$CX_APP/Contents/SharedSupport/CrossOver"
CXSTART="$CX_SUPPORT/bin/cxstart"
CXBOTTLE="$CX_SUPPORT/bin/cxbottle"
WINESERVER="$CX_SUPPORT/bin/wineserver"

CX_BOTTLES_ROOT="${CX_BOTTLES_ROOT:-$HOME/Library/Application Support/CrossOver/Bottles}"
CX_BOTTLE="${CX_BOTTLE:-Win10}"
CX_BOTTLE_DIR="$CX_BOTTLES_ROOT/$CX_BOTTLE"

# --- Dwarf Fortress -------------------------------------------------------
# Both spellings of the same directory: the macOS path for reading files and
# logs, and the Windows path cxstart needs for --workdir and the exe. They
# must be kept in step; that they describe ONE directory is the whole point
# of this rig -- editing a Lua script here is editing it "on Windows".
DF_STEAM_REL="Program Files (x86)/Steam/steamapps/common/Dwarf Fortress"
DF_DIR="${DF_DIR:-$CX_BOTTLE_DIR/drive_c/$DF_STEAM_REL}"
DF_WIN_DIR="${DF_WIN_DIR:-C:\\Program Files (x86)\\Steam\\steamapps\\common\\Dwarf Fortress}"
DF_EXE_NAME="${DF_EXE_NAME:-Dwarf Fortress.exe}"

# ⚠️ SAVES ARE NOT IN THE INSTALL DIRECTORY. The Steam build writes them to the
# Windows user profile -- %APPDATA%\Bay 12 Games\Dwarf Fortress\save -- so
# `$DF_DIR/save` does not exist and never will. This cost a session: an empty
# `$DF_DIR/save` reads exactly like "the fortress is gone" when in fact every
# save was present the whole time. `load` never caught it because it drives the
# menus by on-screen text and never touches a path.
DF_USER_DIR="${DF_USER_DIR:-$CX_BOTTLE_DIR/drive_c/users/crossover/AppData/Roaming/Bay 12 Games/Dwarf Fortress}"
DF_SAVE_DIR="${DF_SAVE_DIR:-$DF_USER_DIR/save}"

# --- DFHack RPC -----------------------------------------------------------
# ⚠️ 5000 is DFHack's default and is ALSO macOS ControlCenter's AirPlay
# Receiver port. On this machine 5000 is taken, so the default here is not
# DFHack's default. DFHACK_PORT overrides both.
CX_DFHACK_PORT="${CX_DFHACK_PORT:-5555}"
CX_DFHACK_PORT_FALLBACK="${CX_DFHACK_PORT_FALLBACK:-5100}"

# ⚠️ Leave DFHack's `allow_remote` FALSE. The socket is a real macOS loopback
# socket, so a local client reaches it without opening the server to the
# network -- the VM rig has to set allow_remote:true to cross its guest
# boundary, which DFHack's own docs call insecure.
CX_DISABLE_CONSOLE="${CX_DISABLE_CONSOLE:-1}"

# --- timings --------------------------------------------------------------
# Measured 2026-09-15 on an M4 Max: the RPC listener was up ~10s after launch.
CX_START_TIMEOUT="${CX_START_TIMEOUT:-120}"
CX_STOP_TIMEOUT="${CX_STOP_TIMEOUT:-60}"
# Measured: a year-50 fortress reached dwarfmode ~15s after the final click.
CX_LOAD_TIMEOUT="${CX_LOAD_TIMEOUT:-180}"

# --- python ---------------------------------------------------------------
# ⚠️ cx-rpc.py imports `chronicler`, so it needs THIS project's interpreter.
# Its shebang resolves to the system python3, which has none of the deps --
# invoking the script directly fails at the import, not at the RPC.
CX_PYTHON="${CX_PYTHON:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.venv/bin/python}"
[ -x "$CX_PYTHON" ] || CX_PYTHON=python3

# --- paths ----------------------------------------------------------------
CX_SNAPSHOT_DIR="${CX_SNAPSHOT_DIR:-$HOME/Library/Application Support/CrossOver/df-snapshots}"
CX_LOG="${CX_LOG:-${TMPDIR:-/tmp}/cx-lifecycle.log}"
