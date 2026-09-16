#!/bin/bash
# ===========================================================================
# deploy-homeserver.sh — Deploy & manage Chronicler on HomeServer via SMB/HTTP
# ===========================================================================
# Usage: deploy-homeserver.sh [command]
#
# Commands:
#   bridge       — Deploy chronicler-bridge.lua + chronicler-export.lua
#   status       — Check deployment status (network, files, bridge version)
#   legends      — Download legends XML from HomeServer + run ingest
#   backup-save  — Backup current DF save to local machine
#   all          — Deploy all scripts
#
# Requires: impacket (in infrastructure/.venv)
# ===========================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$HOME/Claude/Jarvis/infrastructure/.venv/bin/python3"
CHRONICLER_VENV="$HOME/Claude/Projects/DwarfCron/.venv/bin"
BRIDGE_SRC="$HOME/Claude/Projects/DwarfCron/chronicler/dfhack/scripts/chronicler-bridge.lua"
EXPORT_SRC="$HOME/Claude/Projects/DwarfCron/chronicler/dfhack/scripts/chronicler-export.lua"
LEGENDS_DIR="$HOME/Claude/Projects/DwarfCron/data/legends"
BACKUP_DIR="$HOME/Claude/Projects/DwarfCron/data/backups"
HOMESERVER="192.168.4.194"
HTTP_PORT=8888

COMMAND="${1:-status}"

case "$COMMAND" in
    bridge)
        echo "=== Deploying DFHack scripts ==="
        $VENV_PYTHON << 'PYEOF'
from impacket.smbconnection import SMBConnection
import io, os

HOST = '192.168.4.194'
USER = 'Nathaniel'
PASS = 'DwarfF0rtress'

home = os.environ.get('HOME', os.path.expanduser('~'))
scripts = [
    (f'{home}/Claude/Projects/DwarfCron/chronicler/dfhack/scripts/chronicler-bridge.lua',
     'Nathaniel/dfhack-scripts/chronicler-bridge.lua'),
    (f'{home}/Claude/Projects/DwarfCron/chronicler/dfhack/scripts/chronicler-export.lua',
     'Nathaniel/dfhack-scripts/chronicler-export.lua'),
]

conn = SMBConnection(HOST, HOST, sess_port=445, timeout=10)
conn.login(USER, PASS, domain='')

for src, dst in scripts:
    with open(src, 'rb') as f:
        data = f.read()
    conn.putFile('Users', dst, io.BytesIO(data).read)
    name = os.path.basename(src)
    print(f'  Deployed: {name} ({len(data)} bytes)')

# Verify
print('\n  Remote dfhack-scripts/:')
files = conn.listPath('Users', 'Nathaniel/dfhack-scripts/*')
for f in files:
    name = f.get_longname()
    if not name.startswith('.'):
        print(f'    {f.get_filesize():>10}  {name}')

conn.logoff()
PYEOF
        ;;

    status)
        echo "=== HomeServer Deployment Status ==="
        $VENV_PYTHON << 'PYEOF'
from impacket.smbconnection import SMBConnection
import io, os, socket

HOST = '192.168.4.194'
SRC = os.path.join(os.environ.get('HOME', os.path.expanduser('~')), 'Claude/Projects/DwarfCron/chronicler/dfhack/scripts/chronicler-bridge.lua')

# Check connectivity
print("\n--- Network ---")
for port, name in [(445, "SMB"), (5000, "DFHack RPC"), (8888, "HTTP File Server")]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    try:
        s.connect((HOST, port))
        print(f"  {name} (:{port}): UP")
        s.close()
    except:
        print(f"  {name} (:{port}): DOWN")

# Check files via SMB
print("\n--- Deployed Files ---")
try:
    conn = SMBConnection(HOST, HOST, sess_port=445, timeout=10)
    conn.login('Nathaniel', 'DwarfF0rtress', domain='')

    local_size = os.path.getsize(SRC)
    files = conn.listPath('Users', 'Nathaniel/dfhack-scripts/*')
    for f in files:
        name = f.get_longname()
        if not name.startswith('.'):
            extra = ""
            if name == 'chronicler-bridge.lua':
                match = "CURRENT" if f.get_filesize() == local_size else f"STALE (local={local_size})"
                extra = f"  [{match}]"
            print(f"  {f.get_filesize():>10}  {name}{extra}")

    # Check for autoconfig in Startup
    print("\n--- Startup Folder ---")
    sp = 'Nathaniel/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup'
    files = conn.listPath('Users', sp + '/*')
    has_autoconfig = False
    for f in files:
        name = f.get_longname()
        if 'chronicler' in name.lower():
            print(f"  {f.get_filesize():>10}  {name}")
            has_autoconfig = True
    if not has_autoconfig:
        print("  (no chronicler scripts — already ran or not deployed)")

    # Read bridge version
    print("\n--- Bridge Version ---")
    buf = io.BytesIO()
    conn.getFile('Users', 'Nathaniel/dfhack-scripts/chronicler-bridge.lua', buf.write)
    first_line = buf.getvalue().decode('utf-8').split('\n')[0]
    print(f"  {first_line.strip()}")

    conn.logoff()
except Exception as e:
    print(f"  SMB error: {e}")
PYEOF
        ;;

    legends)
        echo "=== Legends Export: Download + Ingest ==="
        echo ""
        echo "Step 1: Checking for export manifest..."

        # Try to download the manifest first
        MANIFEST_URL="http://${HOMESERVER}:${HTTP_PORT}/chronicler-export-manifest.json"
        MANIFEST_FILE="/tmp/chronicler-export-manifest.json"

        if curl -sf --connect-timeout 5 "$MANIFEST_URL" -o "$MANIFEST_FILE" 2>/dev/null; then
            echo "  Manifest found!"
            $VENV_PYTHON << PYEOF
import json, os

with open('$MANIFEST_FILE') as f:
    m = json.load(f)

print(f"  World: {m.get('world_name', '?')}")
print(f"  Save: {m.get('save_dir', '?')}")
print(f"  Year: {m.get('cur_year', '?')}")
print(f"  Base: {m.get('base_name', '?')}")
files = m.get('files', {})
print(f"  legends: {files.get('legends', '?')}")
print(f"  legends_plus: {files.get('legends_plus', '?')}")

# Write file names for shell to use
with open('/tmp/chronicler-legends-files.txt', 'w') as f:
    f.write(files.get('legends', '') + '\n')
    f.write(files.get('legends_plus', '') + '\n')
    f.write(m.get('save_dir', 'unknown') + '\n')
PYEOF
        else
            echo "  No manifest found. Trying to detect from bridge data..."
            BRIDGE_URL="http://${HOMESERVER}:${HTTP_PORT}/chronicler-state.json"
            BRIDGE_FILE="/tmp/chronicler-bridge-state.json"

            if curl -sf --connect-timeout 5 "$BRIDGE_URL" -o "$BRIDGE_FILE" 2>/dev/null; then
                $VENV_PYTHON << PYEOF
import json

with open('$BRIDGE_FILE') as f:
    data = json.load(f)

wi = data.get('world_info', {})
year = data.get('cur_year', 0)
tick = data.get('cur_year_tick', 0)
save_dir = wi.get('save_dir', 'unknown')

# Construct expected filenames
year_str = f'{year:05d}'
month = tick // 33600 + 1
day = (tick % 33600) // 1200 + 1

base = f'{save_dir}-{year_str}-{month:02d}-{day:02d}'
legends = f'{base}-legends.xml'
legends_plus = f'{base}-legends_plus.xml'

print(f"  Detected from bridge: {wi.get('world_name_english', '?')}")
print(f"  Constructed: {legends}")
print(f"  NOTE: Filenames are estimated from current game time.")
print(f"  If export was done at a different time, filenames may differ.")

with open('/tmp/chronicler-legends-files.txt', 'w') as f:
    f.write(legends + '\n')
    f.write(legends_plus + '\n')
    f.write(save_dir + '\n')
PYEOF
            else
                echo "  ERROR: HTTP server not reachable. Cannot determine file names."
                echo "  Start the HTTP server on the HomeServer first."
                exit 1
            fi
        fi

        echo ""
        echo "Step 2: Downloading legends XML files..."

        # Read file names
        if [ ! -f /tmp/chronicler-legends-files.txt ]; then
            echo "  ERROR: Could not determine file names."
            exit 1
        fi

        LEGENDS_FILE=$(sed -n '1p' /tmp/chronicler-legends-files.txt)
        LEGENDS_PLUS_FILE=$(sed -n '2p' /tmp/chronicler-legends-files.txt)
        SAVE_DIR=$(sed -n '3p' /tmp/chronicler-legends-files.txt)

        # Create output directory
        OUTPUT_DIR="${LEGENDS_DIR}/${SAVE_DIR}"
        mkdir -p "$OUTPUT_DIR"

        LEGENDS_LOCAL="${OUTPUT_DIR}/${LEGENDS_FILE}"
        LEGENDS_PLUS_LOCAL="${OUTPUT_DIR}/${LEGENDS_PLUS_FILE}"

        # URL-encode the filenames (spaces in save names)
        LEGENDS_URL="http://${HOMESERVER}:${HTTP_PORT}/$(python3 -c "import urllib.parse; print(urllib.parse.quote('${LEGENDS_FILE}'))")"
        LEGENDS_PLUS_URL="http://${HOMESERVER}:${HTTP_PORT}/$(python3 -c "import urllib.parse; print(urllib.parse.quote('${LEGENDS_PLUS_FILE}'))")"

        echo "  Downloading ${LEGENDS_FILE}..."
        if curl -sf --connect-timeout 10 "$LEGENDS_URL" -o "$LEGENDS_LOCAL"; then
            LSIZE=$(wc -c < "$LEGENDS_LOCAL" | tr -d ' ')
            echo "    OK (${LSIZE} bytes)"
        else
            echo "    FAILED — file may not exist yet. Run 'chronicler-export' in DFHack Legends mode first."
            exit 1
        fi

        echo "  Downloading ${LEGENDS_PLUS_FILE}..."
        if curl -sf --connect-timeout 10 "$LEGENDS_PLUS_URL" -o "$LEGENDS_PLUS_LOCAL"; then
            LPSIZE=$(wc -c < "$LEGENDS_PLUS_LOCAL" | tr -d ' ')
            echo "    OK (${LPSIZE} bytes)"
        else
            echo "    WARNING: legends_plus.xml not found (DFHack exportlegends may not have run)"
            LEGENDS_PLUS_LOCAL=""
        fi

        echo ""
        echo "Step 3: Running chronicler ingest..."

        INGEST_CMD="${CHRONICLER_VENV}/chronicler ingest --legends ${LEGENDS_LOCAL}"
        if [ -n "$LEGENDS_PLUS_LOCAL" ]; then
            INGEST_CMD="${INGEST_CMD} --legends-plus ${LEGENDS_PLUS_LOCAL}"
        fi

        echo "  ${INGEST_CMD}"
        $INGEST_CMD

        echo ""
        echo "=== Legends pipeline complete ==="
        ;;

    backup-save)
        echo "=== DF Save Backup ==="
        echo ""

        # Get save info from bridge data
        $VENV_PYTHON << 'PYEOF'
import json, urllib.request, os, sys
from datetime import datetime

HOST = '192.168.4.194'
HTTP_PORT = 8888
BACKUP_DIR = os.path.join(os.environ.get('HOME', os.path.expanduser('~')), 'Claude/Projects/DwarfCron/data/backups')

# Get current save info from bridge
try:
    url = f'http://{HOST}:{HTTP_PORT}/chronicler-state.json'
    with urllib.request.urlopen(url, timeout=15) as resp:
        data = json.loads(resp.read().decode('utf-8'))
except Exception as e:
    print(f"  ERROR: Cannot reach HTTP server: {e}")
    print(f"  Start the HTTP server on the HomeServer first.")
    sys.exit(1)

wi = data.get('world_info', {})
world = wi.get('world_name_english', 'unknown')
fortress = wi.get('fortress_name_english', 'unknown')
year = data.get('cur_year', 0)

print(f"  World: {world}")
print(f"  Fortress: {fortress}")
print(f"  Year: {year}")
print("")

# We can't access the save directory via SMB (C$ denied) or HTTP (server only serves DF root files)
# But we CAN backup the bridge state and any legends XMLs we have locally
# For actual save files, we need the HTTP server to serve from the save directory
# or use a different transfer method

# Backup the bridge state snapshot
os.makedirs(BACKUP_DIR, exist_ok=True)
timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
backup_name = f'bridge-snapshot-{timestamp}-y{year}.json'
backup_path = os.path.join(BACKUP_DIR, backup_name)

with open(backup_path, 'w') as f:
    json.dump(data, f, indent=2)

size = os.path.getsize(backup_path)
print(f"  Bridge snapshot saved: {backup_path} ({size:,} bytes)")
print("")

# For full save backup, explain the limitation
print("  NOTE: Full save backup requires access to the DF save directory.")
print("  The HTTP server only serves files from the DF root directory.")
print("  To enable full save backup, either:")
print("    1. Run chronicler-setup.ps1 (adds admin share access)")
print("    2. Configure the HTTP server to also serve the save directory")
print("    3. Use 'exportlegends all' in Legends mode to export world state")
print("")
print("  The bridge snapshot above captures the current live game state")
print(f"  including all {len([k for k in data.keys() if k not in ('cur_year','cur_year_tick','cur_season','creature_raws','creature_count','timestamp','bridge_version')])} data sections.")

# Also try to list what legends we have locally
legends_dir = os.path.join(os.environ.get('HOME', os.path.expanduser('~')), 'Claude/Projects/DwarfCron/data/legends')
if os.path.exists(legends_dir):
    print(f"\n  Local legends backups in {legends_dir}:")
    for entry in sorted(os.listdir(legends_dir)):
        full = os.path.join(legends_dir, entry)
        if os.path.isdir(full):
            files = os.listdir(full)
            xml_count = sum(1 for f in files if f.endswith('.xml'))
            total_size = sum(os.path.getsize(os.path.join(full, f)) for f in files)
            print(f"    {entry}/  ({xml_count} XMLs, {total_size:,} bytes)")
        elif entry.endswith('.xml'):
            print(f"    {entry}  ({os.path.getsize(full):,} bytes)")
PYEOF
        ;;

    all)
        "$0" bridge
        echo ""
        "$0" status
        ;;

    *)
        echo "Usage: deploy-homeserver.sh [bridge|status|legends|backup-save|all]"
        echo ""
        echo "Commands:"
        echo "  bridge       Deploy chronicler-bridge.lua + chronicler-export.lua"
        echo "  status       Check deployment status (network, files, versions)"
        echo "  legends      Download legends XML + run ingest pipeline"
        echo "  backup-save  Backup bridge state + list local legends"
        echo "  all          Deploy all scripts + show status"
        exit 1
        ;;
esac
