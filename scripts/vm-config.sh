#!/bin/bash
# ===========================================================================
# vm-config.sh — Shared configuration for VM automation scripts
# ===========================================================================
# Sourced by vm-lifecycle.sh, vm-bootstrap.sh, and future vm-*.sh scripts.
# Single source of truth for VM identity, paths, and SSH settings.
# ===========================================================================

# --- VM Identity ---
VM_NAME="DF-Windows"
UTMCTL="/Applications/UTM.app/Contents/MacOS/utmctl"
QEMU_IMG="$(which qemu-img 2>/dev/null)"

# --- Disk (auto-detect qcow2 — UUID changes on re-create) ---
VM_DATA_DIR="$HOME/Library/Containers/com.utmapp.UTM/Data/Documents/${VM_NAME}.utm/Data"
VM_DISK=""
if [ -d "$VM_DATA_DIR" ]; then
    VM_DISK=$(ls "$VM_DATA_DIR"/*.qcow2 2>/dev/null | head -1)
fi

# --- SSH ---
SSH_KEY="$HOME/.ssh/df-vm"
SSH_USER="Jarvis"
SSH_TIMEOUT=5
SSH_MAX_WAIT=120  # seconds to wait for SSH after boot

# --- Network Ports ---
DFHACK_RPC_PORT=5000
BRIDGE_HTTP_PORT=8888
FILE_SERVE_PORT=8889

# --- Script Directory ---
VM_SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
