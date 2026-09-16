#!/bin/bash
# ===========================================================================
# vm-bootstrap.sh — Automated Phase 0 Bootstrap for DF-Windows VM
# ===========================================================================
# Runs after user has completed:
#   1. Fresh Windows 11 ARM install in UTM
#   2. SPICE Guest Tools + QEMU Guest Agent installed
#
# This script autonomously:
#   1. Verifies guest agent connectivity
#   2. Installs OpenSSH Server
#   3. Generates and deploys SSH key pair
#   4. Verifies SSH key-based auth
#   5. Installs PowerShell 7 (optional, best-effort)
#
# Usage:
#   vm-bootstrap.sh              # Run full bootstrap
#   vm-bootstrap.sh --check      # Check current bootstrap status
#   vm-bootstrap.sh --ssh-only   # Only do SSH key setup (if OpenSSH already installed)
# ===========================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/vm-config.sh"
LIFECYCLE="$SCRIPT_DIR/vm-lifecycle.sh"

# --- Helpers ---
log() { echo "[vm-bootstrap] $*" >&2; }
err() { echo "[vm-bootstrap] ERROR: $*" >&2; exit 1; }
warn() { echo "[vm-bootstrap] WARNING: $*" >&2; }

check_pass() { echo "  [PASS] $*"; }
check_fail() { echo "  [FAIL] $*"; }
check_skip() { echo "  [SKIP] $*"; }

# --- Prerequisite Checks ---
preflight() {
    log "Running preflight checks..."

    # VM must be running
    local status
    status=$("$LIFECYCLE" status 2>/dev/null)
    if [ "$status" != "started" ]; then
        err "VM is $status. Start it first: vm-lifecycle.sh start"
    fi
    log "VM is running"

    # Guest agent must respond
    log "Testing guest agent..."
    local hostname
    hostname=$("$UTMCTL" exec "$VM_NAME" --cmd cmd.exe /c hostname 2>/dev/null)
    if [ -z "$hostname" ]; then
        err "Guest agent not responding. Ensure SPICE Guest Tools + QEMU Guest Agent are installed in the VM."
    fi
    log "Guest agent OK — hostname: $hostname"
}

# --- Step 1: Install OpenSSH Server ---
install_openssh() {
    log "Step 1: Installing OpenSSH Server..."

    # Check if already installed
    local sshd_check
    sshd_check=$("$UTMCTL" exec "$VM_NAME" --cmd powershell.exe -Command \
        "Get-Service sshd -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status" 2>/dev/null)

    if [ "$sshd_check" = "Running" ]; then
        log "OpenSSH Server already running"
        return 0
    fi

    # Install OpenSSH capability
    log "Adding OpenSSH Server capability..."
    "$UTMCTL" exec "$VM_NAME" --cmd powershell.exe -Command \
        "Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0" 2>&1
    local rc=$?
    if [ $rc -ne 0 ]; then
        warn "Add-WindowsCapability returned $rc — may already be installed"
    fi

    # Start and enable sshd
    log "Starting sshd service..."
    "$UTMCTL" exec "$VM_NAME" --cmd powershell.exe -Command \
        "Start-Service sshd; Set-Service -Name sshd -StartupType Automatic" 2>&1

    # Open firewall
    log "Opening firewall port 22..."
    "$UTMCTL" exec "$VM_NAME" --cmd powershell.exe -Command \
        "New-NetFirewallRule -Name OpenSSH-Server -DisplayName 'OpenSSH Server' -Direction Inbound -Protocol TCP -LocalPort 22 -Action Allow -ErrorAction SilentlyContinue" 2>&1

    # Verify
    sshd_check=$("$UTMCTL" exec "$VM_NAME" --cmd powershell.exe -Command \
        "Get-Service sshd | Select-Object -ExpandProperty Status" 2>/dev/null)
    if [ "$sshd_check" = "Running" ]; then
        log "OpenSSH Server installed and running"
        return 0
    else
        err "OpenSSH Server install failed — sshd status: $sshd_check"
    fi
}

# --- Step 2: Generate and Deploy SSH Key ---
setup_ssh_key() {
    log "Step 2: Setting up SSH key..."

    # Generate key if it doesn't exist
    if [ ! -f "$SSH_KEY" ]; then
        log "Generating SSH key pair at $SSH_KEY"
        ssh-keygen -t ed25519 -f "$SSH_KEY" -N "" -C "jarvis-vm-control"
    else
        log "SSH key already exists at $SSH_KEY"
    fi

    # Get VM IP
    local ip
    ip=$("$LIFECYCLE" ip 2>/dev/null)
    if [ -z "$ip" ]; then
        err "Could not get VM IP"
    fi
    log "VM IP: $ip"

    # Read public key
    local pubkey
    pubkey=$(cat "${SSH_KEY}.pub")

    # Deploy via guest agent — create .ssh directory and authorized_keys
    log "Deploying public key to VM..."

    # Create .ssh directory
    "$UTMCTL" exec "$VM_NAME" --cmd powershell.exe -Command \
        "New-Item -ItemType Directory -Force -Path \"C:\\Users\\$SSH_USER\\.ssh\" | Out-Null" 2>&1

    # Write authorized_keys via guest agent file push
    echo "$pubkey" | "$UTMCTL" file push "$VM_NAME" "C:\\Users\\$SSH_USER\\.ssh\\authorized_keys" 2>&1
    local rc=$?

    if [ $rc -ne 0 ]; then
        # Fallback: write via exec + powershell
        log "File push failed (rc=$rc), trying PowerShell fallback..."
        "$UTMCTL" exec "$VM_NAME" --cmd powershell.exe -Command \
            "Set-Content -Path \"C:\\Users\\$SSH_USER\\.ssh\\authorized_keys\" -Value '$pubkey'" 2>&1
    fi

    # Fix permissions (Windows OpenSSH requires specific ACLs for admin users)
    "$UTMCTL" exec "$VM_NAME" --cmd powershell.exe -Command \
        "icacls \"C:\\Users\\$SSH_USER\\.ssh\\authorized_keys\" /inheritance:r /grant \"$SSH_USER:F\" /grant \"SYSTEM:F\"" 2>&1

    # For admin users, OpenSSH on Windows uses administrators_authorized_keys
    "$UTMCTL" exec "$VM_NAME" --cmd powershell.exe -Command \
        "if ((Get-LocalGroupMember Administrators -Member $SSH_USER -ErrorAction SilentlyContinue)) { Copy-Item \"C:\\Users\\$SSH_USER\\.ssh\\authorized_keys\" \"C:\\ProgramData\\ssh\\administrators_authorized_keys\" -Force; icacls \"C:\\ProgramData\\ssh\\administrators_authorized_keys\" /inheritance:r /grant 'SYSTEM:F' /grant 'Administrators:F' }" 2>&1

    # Test SSH connection
    log "Testing SSH connection..."
    sleep 2
    local test_result
    test_result=$(ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
                      -o BatchMode=yes "$SSH_USER@$ip" "hostname" 2>/dev/null)
    if [ -n "$test_result" ]; then
        log "SSH key auth verified — hostname: $test_result"
        return 0
    else
        warn "SSH key auth test failed. May need manual sshd_config adjustment."
        warn "Try: ssh -i $SSH_KEY -o StrictHostKeyChecking=no $SSH_USER@$ip"
        return 1
    fi
}

# --- Step 3: Configure SSH Config Entry ---
setup_ssh_config() {
    log "Step 3: Configuring SSH config entry..."

    local ssh_config="$HOME/.ssh/config"
    local ip
    ip=$("$LIFECYCLE" ip 2>/dev/null)

    # Check if entry already exists
    if [ -f "$ssh_config" ] && grep -q "Host df-vm" "$ssh_config" 2>/dev/null; then
        log "SSH config entry 'df-vm' already exists"
        # Update HostName if IP changed
        if [ -n "$ip" ]; then
            local current_host
            current_host=$(awk '/Host df-vm/{found=1} found && /HostName/{print $2; exit}' "$ssh_config")
            if [ "$current_host" != "$ip" ]; then
                log "Updating HostName from $current_host to $ip"
                sed -i '' "s/HostName $current_host/HostName $ip/" "$ssh_config"
            fi
        fi
        return 0
    fi

    if [ -z "$ip" ]; then
        warn "Cannot determine VM IP — SSH config entry will use placeholder. Update after VM starts."
        ip="VM_IP_PLACEHOLDER"
    fi

    # Append config block
    log "Adding 'df-vm' host entry to $ssh_config"
    {
        echo ""
        echo "# DF-Windows UTM VM (managed by vm-bootstrap.sh)"
        echo "Host df-vm"
        echo "    HostName $ip"
        echo "    User $SSH_USER"
        echo "    IdentityFile $SSH_KEY"
        echo "    StrictHostKeyChecking no"
        echo "    UserKnownHostsFile /dev/null"
        echo "    LogLevel ERROR"
        echo "    ConnectTimeout $SSH_TIMEOUT"
    } >> "$ssh_config"

    chmod 600 "$ssh_config"
    log "SSH config entry added. Use: ssh df-vm"
}

# --- Step 4: Install PowerShell 7 (best-effort) ---
install_pwsh7() {
    log "Step 3: Installing PowerShell 7 (best-effort)..."

    local pwsh_check
    pwsh_check=$("$UTMCTL" exec "$VM_NAME" --cmd cmd.exe /c "where pwsh" 2>/dev/null)

    if [ -n "$pwsh_check" ]; then
        log "PowerShell 7 already installed: $pwsh_check"
        return 0
    fi

    # Try winget
    "$UTMCTL" exec "$VM_NAME" --cmd cmd.exe /c \
        "winget install --id Microsoft.PowerShell --accept-source-agreements --accept-package-agreements" 2>&1
    local rc=$?

    if [ $rc -eq 0 ]; then
        log "PowerShell 7 installed via winget"
    else
        warn "winget install failed (rc=$rc). PowerShell 7 can be installed manually later."
    fi
}

# --- Status Check ---
check_status() {
    echo "=== VM Bootstrap Status ==="

    local status
    status=$("$LIFECYCLE" status 2>/dev/null)
    echo "VM Status: $status"

    if [ "$status" != "started" ]; then
        echo "VM not running — start it to check full status"
        return 1
    fi

    # Guest agent
    local hostname
    hostname=$("$UTMCTL" exec "$VM_NAME" --cmd cmd.exe /c hostname 2>/dev/null)
    if [ -n "$hostname" ]; then
        check_pass "Guest agent (hostname: $hostname)"
    else
        check_fail "Guest agent not responding"
    fi

    # OpenSSH
    local sshd_status
    sshd_status=$("$UTMCTL" exec "$VM_NAME" --cmd powershell.exe -Command \
        "Get-Service sshd -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status" 2>/dev/null)
    if [ "$sshd_status" = "Running" ]; then
        check_pass "OpenSSH Server (Running)"
    elif [ -n "$sshd_status" ]; then
        check_fail "OpenSSH Server ($sshd_status)"
    else
        check_fail "OpenSSH Server (not installed)"
    fi

    # SSH key
    if [ -f "$SSH_KEY" ]; then
        check_pass "SSH key exists ($SSH_KEY)"
    else
        check_fail "SSH key missing ($SSH_KEY)"
    fi

    # SSH connectivity
    local ip
    ip=$("$LIFECYCLE" ip 2>/dev/null)
    if [ -n "$ip" ]; then
        check_pass "VM IP: $ip"
        if [ -f "$SSH_KEY" ]; then
            local ssh_test
            ssh_test=$(ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
                           -o BatchMode=yes "$SSH_USER@$ip" "echo ok" 2>/dev/null)
            if [ "$ssh_test" = "ok" ]; then
                check_pass "SSH key auth"
            else
                check_fail "SSH key auth"
            fi
        fi
    else
        check_fail "VM IP not available"
    fi

    # SSH config
    if [ -f "$HOME/.ssh/config" ] && grep -q "Host df-vm" "$HOME/.ssh/config" 2>/dev/null; then
        check_pass "SSH config entry (df-vm)"
    else
        check_fail "SSH config entry (df-vm not in ~/.ssh/config)"
    fi

    # PowerShell 7
    local pwsh_check
    pwsh_check=$("$UTMCTL" exec "$VM_NAME" --cmd cmd.exe /c "where pwsh" 2>/dev/null)
    if [ -n "$pwsh_check" ]; then
        check_pass "PowerShell 7"
    else
        check_skip "PowerShell 7 (not installed)"
    fi
}

# --- Main ---
case "${1:-}" in
    --check)
        check_status
        ;;
    --ssh-only)
        preflight
        setup_ssh_key
        ;;
    "")
        log "Starting full bootstrap..."
        preflight
        install_openssh
        setup_ssh_key
        setup_ssh_config
        install_pwsh7
        log ""
        log "=== Bootstrap Complete ==="
        check_status
        ;;
    *)
        echo "Usage: vm-bootstrap.sh [--check|--ssh-only]"
        echo ""
        echo "  (no args)    Run full bootstrap (OpenSSH + SSH key + PowerShell 7)"
        echo "  --check      Check current bootstrap status"
        echo "  --ssh-only   Only set up SSH key (if OpenSSH already installed)"
        exit 1
        ;;
esac
