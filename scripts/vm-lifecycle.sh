#!/bin/bash
# ===========================================================================
# vm-lifecycle.sh — UTM VM Lifecycle Management for Chronicler
# ===========================================================================
# Wraps utmctl for start/stop/status/ip/snapshot/restore operations.
# Designed for Jarvis autonomous control of the DF-Windows VM.
#
# Usage:
#   vm-lifecycle.sh start       # Boot VM, wait for SSH, print IP
#   vm-lifecycle.sh stop        # Graceful shutdown
#   vm-lifecycle.sh suspend     # Suspend to memory
#   vm-lifecycle.sh status      # Print VM status
#   vm-lifecycle.sh ip          # Print VM IP address
#   vm-lifecycle.sh ssh [cmd]   # SSH into VM (optionally run command)
#   vm-lifecycle.sh snapshot <name>   # Create disk snapshot (VM must be stopped)
#   vm-lifecycle.sh restore <name>    # Restore disk snapshot (VM must be stopped)
#   vm-lifecycle.sh snapshots         # List disk snapshots
#   vm-lifecycle.sh health            # Check VM + SSH + services health
# ===========================================================================

# --- Configuration (shared) ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/vm-config.sh"

# --- Helpers ---
log() { echo "[vm-lifecycle] $*" >&2; }
err() { echo "[vm-lifecycle] ERROR: $*" >&2; exit 1; }

get_status() {
    "$UTMCTL" status "$VM_NAME" 2>/dev/null
}

get_ip() {
    "$UTMCTL" ip-address "$VM_NAME" 2>/dev/null | head -1
}

wait_for_ssh() {
    local ip="$1"
    local elapsed=0
    log "Waiting for SSH on $ip (max ${SSH_MAX_WAIT}s)..."
    while [ $elapsed -lt $SSH_MAX_WAIT ]; do
        if ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=$SSH_TIMEOUT \
               -o BatchMode=yes "$SSH_USER@$ip" "echo ok" >/dev/null 2>&1; then
            log "SSH ready after ${elapsed}s"
            return 0
        fi
        sleep 5
        elapsed=$((elapsed + 5))
    done
    log "SSH not available after ${SSH_MAX_WAIT}s"
    return 1
}

# --- Commands ---
cmd_start() {
    local status
    status=$(get_status)
    case "$status" in
        started)
            log "VM already running"
            ;;
        suspended)
            log "Resuming suspended VM..."
            "$UTMCTL" start "$VM_NAME"
            ;;
        stopped)
            log "Starting VM..."
            "$UTMCTL" start "$VM_NAME"
            ;;
        *)
            err "Unknown VM status: $status"
            ;;
    esac

    # Wait for IP to become available
    log "Waiting for VM network..."
    local ip=""
    local attempts=0
    while [ -z "$ip" ] && [ $attempts -lt 30 ]; do
        sleep 2
        ip=$(get_ip)
        attempts=$((attempts + 1))
    done

    if [ -z "$ip" ]; then
        err "Could not get VM IP after 60s. Check QEMU guest agent."
    fi

    log "VM IP: $ip"

    # Wait for SSH
    if [ -f "$SSH_KEY" ]; then
        if wait_for_ssh "$ip"; then
            echo "$ip"
            return 0
        else
            log "WARNING: SSH not ready. VM is running at $ip but SSH may not be configured yet."
            echo "$ip"
            return 1
        fi
    else
        log "No SSH key at $SSH_KEY — skipping SSH wait"
        echo "$ip"
        return 0
    fi
}

cmd_stop() {
    local status
    status=$(get_status)
    if [ "$status" = "stopped" ]; then
        log "VM already stopped"
        return 0
    fi
    log "Stopping VM..."
    "$UTMCTL" stop "$VM_NAME"
    # Wait for stop
    local attempts=0
    while [ "$(get_status)" != "stopped" ] && [ $attempts -lt 30 ]; do
        sleep 2
        attempts=$((attempts + 1))
    done
    if [ "$(get_status)" = "stopped" ]; then
        log "VM stopped"
    else
        err "VM did not stop within 60s"
    fi
}

cmd_suspend() {
    log "Suspending VM..."
    "$UTMCTL" suspend "$VM_NAME"
}

cmd_status() {
    get_status
}

cmd_ip() {
    local ip
    ip=$(get_ip)
    if [ -n "$ip" ]; then
        echo "$ip"
    else
        err "No IP available. Is the VM running with guest agent?"
    fi
}

cmd_ssh() {
    local ip
    ip=$(get_ip)
    if [ -z "$ip" ]; then
        err "No VM IP. Is the VM running?"
    fi
    if [ $# -gt 0 ]; then
        ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=$SSH_TIMEOUT \
            "$SSH_USER@$ip" "$@"
    else
        ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$ip"
    fi
}

require_qemu_img() {
    if [ -z "$QEMU_IMG" ]; then
        err "qemu-img not found. Install with: brew install qemu"
    fi
}

cmd_snapshot() {
    require_qemu_img
    local name="$1"
    if [ -z "$name" ]; then
        err "Usage: vm-lifecycle.sh snapshot <name>"
    fi
    local status
    status=$(get_status)
    if [ "$status" != "stopped" ]; then
        err "VM must be stopped for snapshot. Current status: $status"
    fi
    if [ ! -f "$VM_DISK" ]; then
        err "Disk image not found: $VM_DISK"
    fi
    log "Creating snapshot '$name'..."
    "$QEMU_IMG" snapshot -c "$name" "$VM_DISK"
    log "Snapshot '$name' created"
}

cmd_restore() {
    require_qemu_img
    local name="$1"
    if [ -z "$name" ]; then
        err "Usage: vm-lifecycle.sh restore <name>"
    fi
    local status
    status=$(get_status)
    if [ "$status" != "stopped" ]; then
        err "VM must be stopped for restore. Current status: $status"
    fi
    if [ ! -f "$VM_DISK" ]; then
        err "Disk image not found: $VM_DISK"
    fi
    log "Restoring snapshot '$name'..."
    "$QEMU_IMG" snapshot -a "$name" "$VM_DISK"
    log "Snapshot '$name' restored"
}

cmd_snapshots() {
    require_qemu_img
    if [ ! -f "$VM_DISK" ]; then
        err "Disk image not found: $VM_DISK"
    fi
    "$QEMU_IMG" snapshot -l "$VM_DISK"
}

cmd_clone() {
    local name="$1"
    if [ -z "$name" ]; then
        err "Usage: vm-lifecycle.sh clone <name>"
    fi
    local status
    status=$(get_status)
    if [ "$status" != "stopped" ]; then
        err "VM must be stopped for clone. Current status: $status"
    fi
    log "Cloning VM as '$name'..."
    "$UTMCTL" clone "$VM_NAME" --name "$name"
    log "Clone '$name' created"
}

cmd_health() {
    echo "=== VM Health Check ==="
    local status
    status=$(get_status)
    echo "VM Status: $status"

    if [ "$status" != "started" ]; then
        echo "VM not running — skipping network checks"
        return 1
    fi

    local ip
    ip=$(get_ip)
    echo "VM IP: ${ip:-UNAVAILABLE}"

    if [ -z "$ip" ]; then
        echo "Guest agent: NOT RESPONDING"
        return 1
    fi
    echo "Guest agent: OK"

    # SSH check
    if [ -f "$SSH_KEY" ]; then
        if ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=$SSH_TIMEOUT \
               -o BatchMode=yes "$SSH_USER@$ip" "echo ok" >/dev/null 2>&1; then
            echo "SSH: OK"
        else
            echo "SSH: FAILED"
        fi
    else
        echo "SSH: NO KEY ($SSH_KEY not found)"
    fi

    # DFHack RPC check (port 5000)
    if nc -z -w 2 "$ip" 5000 2>/dev/null; then
        echo "DFHack RPC (5000): LISTENING"
    else
        echo "DFHack RPC (5000): NOT AVAILABLE"
    fi

    # Bridge HTTP check (port 8888)
    if curl -sf --max-time 2 "http://$ip:8888/" >/dev/null 2>&1; then
        echo "Bridge HTTP (8888): OK"
    else
        echo "Bridge HTTP (8888): NOT AVAILABLE"
    fi

    # File server HTTP check
    if curl -sf --max-time 2 "http://$ip:$FILE_SERVE_PORT/" >/dev/null 2>&1; then
        echo "File Server ($FILE_SERVE_PORT): OK"
    else
        echo "File Server ($FILE_SERVE_PORT): NOT AVAILABLE"
    fi
}

cmd_push() {
    local local_file="$1"
    local guest_path="$2"
    if [ -z "$local_file" ] || [ -z "$guest_path" ]; then
        err "Usage: vm-lifecycle.sh push <local-file> <guest-path>"
    fi
    if [ ! -f "$local_file" ]; then
        err "Local file not found: $local_file"
    fi
    log "Pushing $local_file → $guest_path"
    "$UTMCTL" file push "$VM_NAME" "$guest_path" < "$local_file"
    log "Push complete"
}

cmd_pull_ga() {
    # Legacy pull via QEMU Guest Agent (1-5 MB/s). Use scp-pull for large files.
    local guest_path="$1"
    if [ -z "$guest_path" ]; then
        err "Usage: vm-lifecycle.sh pull-ga <guest-path>"
    fi
    "$UTMCTL" file pull "$VM_NAME" "$guest_path"
}

cmd_scp_pull() {
    # Fast file download via SCP (40-80 MB/s vs 1-5 MB/s for GA).
    # Requires SSH to be bootstrapped on the VM.
    local guest_path="$1"
    local local_path="${2:-.}"
    if [ -z "$guest_path" ]; then
        err "Usage: vm-lifecycle.sh scp-pull <guest-path> [local-path]"
    fi
    local ip
    ip=$(get_ip)
    if [ -z "$ip" ]; then
        err "No VM IP. Is the VM running?"
    fi
    if [ ! -f "$SSH_KEY" ]; then
        err "SSH key not found at $SSH_KEY. Run vm-bootstrap.sh first."
    fi
    log "SCP pull: $guest_path → $local_path"
    local start_time
    start_time=$(date +%s)
    # -O forces legacy SCP protocol (OpenSSH 8.0+ defaults to SFTP mode,
    # which breaks on Windows absolute paths like C:/path).
    # -T disables strict filename checking (needed for paths with parens/spaces).
    # The remote path must be quoted for the remote shell (spaces in paths).
    scp -O -T -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout="$SSH_TIMEOUT" \
        "$SSH_USER@$ip:\"$guest_path\"" "$local_path"
    local rc=$?
    local end_time
    end_time=$(date +%s)
    local elapsed=$((end_time - start_time))
    if [ $rc -eq 0 ]; then
        log "SCP pull complete in ${elapsed}s"
    else
        err "SCP pull failed (rc=$rc) after ${elapsed}s"
    fi
}

cmd_scp_pull_multi() {
    # Parallel SCP download of multiple files.
    local local_dir="$1"
    shift
    if [ -z "$local_dir" ] || [ $# -eq 0 ]; then
        err "Usage: vm-lifecycle.sh scp-pull-multi <local-dir> <guest-path1> [guest-path2] ..."
    fi
    if [ ! -d "$local_dir" ]; then
        err "Local directory does not exist: $local_dir"
    fi
    local ip
    ip=$(get_ip)
    if [ -z "$ip" ]; then
        err "No VM IP. Is the VM running?"
    fi
    if [ ! -f "$SSH_KEY" ]; then
        err "SSH key not found at $SSH_KEY. Run vm-bootstrap.sh first."
    fi

    local start_time
    start_time=$(date +%s)
    local pids=""
    local count=0

    for guest_path in "$@"; do
        count=$((count + 1))
        log "Starting SCP #$count: $(basename "$guest_path")"
        scp -O -T -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout="$SSH_TIMEOUT" \
            "$SSH_USER@$ip:\"$guest_path\"" "$local_dir/" &
        pids="$pids $!"
    done

    log "Waiting for $count parallel SCP transfers..."
    local failed=0
    for pid in $pids; do
        if ! wait "$pid"; then
            failed=$((failed + 1))
        fi
    done

    local end_time
    end_time=$(date +%s)
    local elapsed=$((end_time - start_time))

    if [ $failed -eq 0 ]; then
        log "All $count transfers complete in ${elapsed}s"
    else
        log "WARNING: $failed of $count transfers failed (${elapsed}s total)"
        return 1
    fi
}

cmd_http_serve() {
    # Start/stop/status for PowerShell HTTP file server on VM (port FILE_SERVE_PORT).
    local action="${1:-start}"
    local ip
    ip=$(get_ip)
    if [ -z "$ip" ]; then
        err "No VM IP. Is the VM running?"
    fi

    case "$action" in
        start)
            # Check if already running
            if curl -sf --max-time 2 "http://$ip:$FILE_SERVE_PORT/" >/dev/null 2>&1; then
                log "HTTP file server already running on port $FILE_SERVE_PORT"
                return 0
            fi

            log "Starting HTTP file server on port $FILE_SERVE_PORT..."
            local template="$VM_SCRIPTS_DIR/file-server.ps1"
            if [ ! -f "$template" ]; then
                err "file-server.ps1 template not found at $template"
            fi

            local ssh_ok=false
            if [ -f "$SSH_KEY" ] && nc -z -w 2 "$ip" 22 2>/dev/null; then
                ssh_ok=true
            fi

            if [ "$ssh_ok" = true ]; then
                # Fast path: deploy + start via SSH
                local ps1_path="C:/Users/$SSH_USER/file-server.ps1"
                scp -i "$SSH_KEY" -o StrictHostKeyChecking=no \
                    "$template" "$SSH_USER@$ip:\"$ps1_path\"" 2>/dev/null
                ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout="$SSH_TIMEOUT" \
                    "$SSH_USER@$ip" \
                    "powershell.exe -ExecutionPolicy Bypass -File \"$ps1_path\"" &
                local ssh_pid=$!
                disown "$ssh_pid" 2>/dev/null
            else
                # Slow path: exec-ps (no SSH or SSH unreachable)
                log "SSH not available — using Guest Agent (slower, ~10s PowerShell startup)"

                # Ensure URL ACL + firewall rule exist (idempotent, requires GA SYSTEM privileges)
                cmd_exec_ps "netsh http show urlacl url=http://+:${FILE_SERVE_PORT}/ | Select-String 'Reserved URL' | Out-Null; if (-not \$?) { netsh http add urlacl url=http://+:${FILE_SERVE_PORT}/ user=Everyone }" 2>/dev/null
                cmd_exec_ps "if (-not (Get-NetFirewallRule -DisplayName 'Chronicler File Server ${FILE_SERVE_PORT}' -ErrorAction SilentlyContinue)) { New-NetFirewallRule -DisplayName 'Chronicler File Server ${FILE_SERVE_PORT}' -Direction Inbound -Protocol TCP -LocalPort ${FILE_SERVE_PORT} -Action Allow | Out-Null }" 2>/dev/null

                "$UTMCTL" file push "$VM_NAME" "C:\\Users\\$SSH_USER\\file-server.ps1" < "$template"
                cmd_exec_ps "Start-Process powershell.exe -ArgumentList '-ExecutionPolicy','Bypass','-File','C:\\Users\\$SSH_USER\\file-server.ps1' -WindowStyle Hidden"
                sleep 5
            fi

            # Wait for server to be ready
            local elapsed=0
            local max_wait=20
            while [ $elapsed -lt $max_wait ]; do
                sleep 2
                elapsed=$((elapsed + 2))
                if curl -sf --max-time 2 "http://$ip:$FILE_SERVE_PORT/" >/dev/null 2>&1; then
                    log "HTTP file server running on http://$ip:$FILE_SERVE_PORT/"
                    return 0
                fi
            done
            log "WARNING: HTTP file server may not have started after ${max_wait}s"
            return 1
            ;;
        stop)
            log "Stopping HTTP file server..."
            if [ -f "$SSH_KEY" ] && nc -z -w 2 "$ip" 22 2>/dev/null; then
                ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout="$SSH_TIMEOUT" \
                    "$SSH_USER@$ip" \
                    'powershell.exe -Command "Get-Process powershell | Where-Object { $_.MainWindowTitle -like \"*File Server*\" } | Stop-Process -Force"' 2>/dev/null
            else
                cmd_exec_ps 'Get-Process powershell | Where-Object { $_.MainWindowTitle -like "*File Server*" } | Stop-Process -Force'
            fi
            log "Stop signal sent"
            ;;
        status)
            if curl -sf --max-time 2 "http://$ip:$FILE_SERVE_PORT/" >/dev/null 2>&1; then
                echo "running (http://$ip:$FILE_SERVE_PORT/)"
            else
                echo "not running"
            fi
            ;;
        *)
            err "Usage: vm-lifecycle.sh http-serve {start|stop|status}"
            ;;
    esac
}

cmd_http_pull() {
    # Download a file from the VM's HTTP file server.
    # The path is relative to the DF install directory.
    local remote_file="$1"
    local local_path="${2:-.}"
    if [ -z "$remote_file" ]; then
        err "Usage: vm-lifecycle.sh http-pull <filename> [local-path]"
    fi
    local ip
    ip=$(get_ip)
    if [ -z "$ip" ]; then
        err "No VM IP. Is the VM running?"
    fi

    # URL-encode spaces in filename
    local encoded
    encoded=$(printf '%s' "$remote_file" | sed 's/ /%20/g')

    local url="http://$ip:$FILE_SERVE_PORT/$encoded"
    log "HTTP pull: $url"

    local start_time
    start_time=$(date +%s)

    if [ -d "$local_path" ]; then
        local basename
        basename=$(basename "$remote_file")
        curl -sfL --max-time 600 -o "$local_path/$basename" "$url"
    else
        curl -sfL --max-time 600 -o "$local_path" "$url"
    fi
    local rc=$?
    local end_time
    end_time=$(date +%s)
    local elapsed=$((end_time - start_time))

    if [ $rc -eq 0 ]; then
        log "HTTP pull complete in ${elapsed}s"
    else
        err "HTTP pull failed (rc=$rc) after ${elapsed}s. Is http-serve running?"
    fi
}

cmd_pull() {
    # Smart pull dispatcher: SCP if SSH available, else Guest Agent fallback.
    local guest_path="$1"
    local local_path="${2:-.}"
    if [ -z "$guest_path" ]; then
        err "Usage: vm-lifecycle.sh pull <guest-path> [local-path]"
    fi

    # Try SCP first (fast path)
    if [ -f "$SSH_KEY" ]; then
        local ip
        ip=$(get_ip)
        if [ -n "$ip" ] && ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no \
               -o ConnectTimeout=2 -o BatchMode=yes "$SSH_USER@$ip" "echo ok" >/dev/null 2>&1; then
            cmd_scp_pull "$guest_path" "$local_path"
            return $?
        fi
    fi

    # Fallback to Guest Agent
    log "SSH unavailable — falling back to Guest Agent pull (slow)"
    cmd_pull_ga "$guest_path"
}

cmd_exec() {
    if [ $# -eq 0 ]; then
        err "Usage: vm-lifecycle.sh exec <command> [args...]"
    fi
    "$UTMCTL" exec "$VM_NAME" --cmd "$@"
}

cmd_exec_capture() {
    # Reliable exec with output capture via temp file on guest.
    # QEMU Guest Agent's exec doesn't relay stdout back to the host.
    # This redirects output to a temp file, polls for completion, then pulls it.
    #
    # Uses a done-marker file pattern: command writes output, then creates .done file.
    # We poll for .done, which guarantees the output file is complete.
    #
    # LIMITATION: Commands pass through cmd.exe, so | " & are interpreted by cmd.exe.
    # For complex PowerShell with pipes/quotes, use exec-ps or SSH once available.
    if [ $# -eq 0 ]; then
        err "Usage: vm-lifecycle.sh exec-capture <command>"
        err "  Example: vm-lifecycle.sh exec-capture hostname"
        err "  Example: vm-lifecycle.sh exec-capture 'powershell.exe -Command Get-Date'"
    fi
    local cmd_str="$*"
    local tmp_name="utmctl-output-$$"
    local guest_out="C:\\Windows\\Temp\\${tmp_name}.txt"
    local guest_done="C:\\Windows\\Temp\\${tmp_name}.done"
    local pull_out="C:\\\\Windows\\\\Temp\\\\${tmp_name}.txt"
    local pull_done="C:\\\\Windows\\\\Temp\\\\${tmp_name}.done"
    local max_wait=30
    local elapsed=0

    # Run command with output redirect, then create done marker
    "$UTMCTL" exec "$VM_NAME" --cmd cmd.exe /c \
        "$cmd_str > $guest_out 2>&1 & echo done > $guest_done" 2>/dev/null

    # Poll for done marker (utmctl file pull returns exit 0 even on failure,
    # so we must check actual output content, not exit code)
    while [ $elapsed -lt $max_wait ]; do
        sleep 2
        elapsed=$((elapsed + 2))
        local marker
        marker=$("$UTMCTL" file pull "$VM_NAME" "$pull_done" 2>/dev/null)
        if [ -n "$marker" ]; then
            break
        fi
    done

    if [ $elapsed -ge $max_wait ]; then
        log "WARNING: exec-capture timed out after ${max_wait}s"
    fi

    # Pull the output file
    local output
    output=$("$UTMCTL" file pull "$VM_NAME" "$pull_out" 2>/dev/null)

    # Clean up both temp files
    "$UTMCTL" exec "$VM_NAME" --cmd cmd.exe /c "del $guest_out $guest_done" 2>/dev/null

    echo "$output"
}

cmd_exec_ps() {
    # Execute complex PowerShell commands via -EncodedCommand (base64 UTF-16LE).
    # Avoids all quoting issues with pipes, quotes, and special characters.
    # Output captured via temp file + done marker (same as exec-capture).
    if [ $# -eq 0 ]; then
        err "Usage: vm-lifecycle.sh exec-ps <powershell-command>"
        err "  Example: vm-lifecycle.sh exec-ps 'Get-Service sshd | Select-Object Status'"
    fi
    local ps_cmd="$*"
    local tmp_name="utmctl-ps-$$"
    local guest_out="C:\\Windows\\Temp\\${tmp_name}.txt"
    local guest_done="C:\\Windows\\Temp\\${tmp_name}.done"
    local pull_out="C:\\\\Windows\\\\Temp\\\\${tmp_name}.txt"
    local pull_done="C:\\\\Windows\\\\Temp\\\\${tmp_name}.done"
    local max_wait=30
    local elapsed=0

    # Wrap: execute PS, redirect to file, then create done marker
    local full_cmd="${ps_cmd} | Out-File -FilePath '${guest_out}' -Encoding ASCII; 'done' | Out-File -FilePath '${guest_done}' -Encoding ASCII"

    # Encode as UTF-16LE base64 for -EncodedCommand
    local encoded
    encoded=$(printf '%s' "$full_cmd" | iconv -f UTF-8 -t UTF-16LE | base64 | tr -d '\n')

    "$UTMCTL" exec "$VM_NAME" --cmd powershell.exe -EncodedCommand "$encoded" 2>/dev/null

    # Poll for done marker
    while [ $elapsed -lt $max_wait ]; do
        sleep 2
        elapsed=$((elapsed + 2))
        local marker
        marker=$("$UTMCTL" file pull "$VM_NAME" "$pull_done" 2>/dev/null)
        if [ -n "$marker" ]; then
            break
        fi
    done

    if [ $elapsed -ge $max_wait ]; then
        log "WARNING: exec-ps timed out after ${max_wait}s"
    fi

    local output
    output=$("$UTMCTL" file pull "$VM_NAME" "$pull_out" 2>/dev/null)

    # Clean up
    "$UTMCTL" exec "$VM_NAME" --cmd cmd.exe /c "del $guest_out $guest_done" 2>/dev/null

    echo "$output"
}

# --- Main dispatch ---
case "${1:-}" in
    start)     cmd_start ;;
    stop)      cmd_stop ;;
    suspend)   cmd_suspend ;;
    status)    cmd_status ;;
    ip)        cmd_ip ;;
    ssh)       shift; cmd_ssh "$@" ;;
    snapshot)  cmd_snapshot "$2" ;;
    restore)   cmd_restore "$2" ;;
    snapshots) cmd_snapshots ;;
    clone)     cmd_clone "$2" ;;
    health)    cmd_health ;;
    push)           shift; cmd_push "$@" ;;
    pull)           shift; cmd_pull "$@" ;;
    pull-ga)        shift; cmd_pull_ga "$@" ;;
    scp-pull)       shift; cmd_scp_pull "$@" ;;
    scp-pull-multi) shift; cmd_scp_pull_multi "$@" ;;
    http-serve)     shift; cmd_http_serve "$@" ;;
    http-pull)      shift; cmd_http_pull "$@" ;;
    exec)           shift; cmd_exec "$@" ;;
    exec-capture)   shift; cmd_exec_capture "$@" ;;
    exec-ps)        shift; cmd_exec_ps "$@" ;;
    *)
        echo "Usage: vm-lifecycle.sh <command> [args...]"
        echo ""
        echo "Lifecycle:"
        echo "  start              Boot VM, wait for SSH, print IP"
        echo "  stop               Graceful shutdown"
        echo "  suspend            Suspend to memory"
        echo "  status             Print VM status"
        echo "  ip                 Print VM IP address"
        echo "  ssh [cmd]          SSH into VM (or run command)"
        echo "  health             Check VM + SSH + services health"
        echo ""
        echo "File transfer (fastest first):"
        echo "  scp-pull <guest> [local]     Fast download via SCP (40-80 MB/s)"
        echo "  scp-pull-multi <dir> <g1>... Parallel SCP downloads"
        echo "  http-serve {start|stop|status}  Manage HTTP file server on VM"
        echo "  http-pull <file> [local]     Download via HTTP file server"
        echo "  pull <guest> [local]         Smart pull (SCP if available, else GA)"
        echo "  pull-ga <guest-path>         Legacy pull via Guest Agent (1-5 MB/s)"
        echo "  push <local> <guest-path>    Upload file to VM via guest agent"
        echo ""
        echo "Execution:"
        echo "  exec <cmd...>      Execute command via QEMU guest agent"
        echo "  exec-capture <cmd> Execute via GA with reliable output capture"
        echo "  exec-ps <ps-cmd>   Execute complex PowerShell via base64 encoding"
        echo ""
        echo "Snapshots:"
        echo "  snapshot <name>    Create disk snapshot (requires: brew install qemu)"
        echo "  restore <name>     Restore disk snapshot (requires: brew install qemu)"
        echo "  snapshots          List disk snapshots (requires: brew install qemu)"
        echo "  clone <name>       Clone entire VM (no qemu-img needed)"
        exit 1
        ;;
esac
