# Install OpenSSH Server from GitHub releases (bypasses Windows Update)
# Deployed + run by vm-lifecycle.sh or manually on the VM.
#
# What this does:
#   1. Downloads Win32-OpenSSH from GitHub (latest stable)
#   2. Extracts to C:\Program Files\OpenSSH
#   3. Runs install-sshd.ps1 from the package
#   4. Configures sshd service to auto-start
#   5. Opens firewall port 22
#   6. Deploys the Jarvis SSH public key
#   7. Starts sshd

$ErrorActionPreference = "Stop"
$sshDir = "C:\Program Files\OpenSSH"
$tempZip = "$env:TEMP\OpenSSH-Win64.zip"
$tempExtract = "$env:TEMP\OpenSSH-Extract"

Write-Host "=== OpenSSH Server Install ===" -ForegroundColor Cyan

# Check if already installed and running
$svc = Get-Service sshd -ErrorAction SilentlyContinue
if ($svc -and $svc.Status -eq "Running") {
    Write-Host "sshd is already installed and running" -ForegroundColor Green
    Write-Host "done" | Out-File "C:\Windows\Temp\sshd-install.done" -Encoding ASCII
    exit 0
}

# Step 1: Download
Write-Host "[1/6] Downloading OpenSSH from GitHub..." -ForegroundColor Yellow
$url = "https://github.com/PowerShell/Win32-OpenSSH/releases/download/v9.5.0.0p1-Beta/OpenSSH-Win64.zip"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri $url -OutFile $tempZip -UseBasicParsing
Write-Host "  Downloaded: $((Get-Item $tempZip).Length / 1MB) MB" -ForegroundColor Green

# Step 2: Extract
Write-Host "[2/6] Extracting..." -ForegroundColor Yellow
if (Test-Path $tempExtract) { Remove-Item $tempExtract -Recurse -Force }
Expand-Archive -Path $tempZip -DestinationPath $tempExtract -Force

# Move to final location
if (Test-Path $sshDir) { Remove-Item $sshDir -Recurse -Force }
Move-Item "$tempExtract\OpenSSH-Win64" $sshDir
Write-Host "  Installed to: $sshDir" -ForegroundColor Green

# Step 3: Run the bundled install script
Write-Host "[3/6] Installing sshd service..." -ForegroundColor Yellow
& "$sshDir\install-sshd.ps1"

# Step 4: Configure service
Write-Host "[4/6] Configuring sshd service..." -ForegroundColor Yellow
Set-Service sshd -StartupType Automatic

# Add OpenSSH to PATH if not already there
$machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($machinePath -notlike "*OpenSSH*") {
    [Environment]::SetEnvironmentVariable("Path", "$machinePath;$sshDir", "Machine")
    Write-Host "  Added to PATH" -ForegroundColor Green
}

# Step 5: Firewall
Write-Host "[5/6] Configuring firewall..." -ForegroundColor Yellow
$existing = Get-NetFirewallRule -DisplayName "OpenSSH Server (sshd)" -ErrorAction SilentlyContinue
if (-not $existing) {
    New-NetFirewallRule -DisplayName "OpenSSH Server (sshd)" -Direction Inbound -Protocol TCP -LocalPort 22 -Action Allow | Out-Null
    Write-Host "  Firewall rule created" -ForegroundColor Green
} else {
    Write-Host "  Firewall rule already exists" -ForegroundColor Green
}

# Step 6: Deploy SSH key for Jarvis user
Write-Host "[6/6] Deploying SSH key..." -ForegroundColor Yellow
$sshUserDir = "C:\Users\Jarvis\.ssh"
if (-not (Test-Path $sshUserDir)) {
    New-Item -ItemType Directory -Path $sshUserDir -Force | Out-Null
}
# The public key will be appended by the caller after this script runs
# For now, ensure the authorized_keys file exists
if (-not (Test-Path "$sshUserDir\authorized_keys")) {
    New-Item -ItemType File -Path "$sshUserDir\authorized_keys" -Force | Out-Null
}

# Fix permissions on .ssh directory (Windows OpenSSH is strict about this)
icacls $sshUserDir /inheritance:r /grant "Jarvis:(OI)(CI)F" /grant "SYSTEM:(OI)(CI)F" | Out-Null

# Start sshd
Write-Host "Starting sshd..." -ForegroundColor Yellow
Start-Service sshd
$status = (Get-Service sshd).Status
Write-Host "sshd status: $status" -ForegroundColor Green

# Done marker
Write-Host "=== Install complete ===" -ForegroundColor Cyan
"sshd status: $status" | Out-File "C:\Windows\Temp\sshd-install.done" -Encoding ASCII

# Cleanup
Remove-Item $tempZip -Force -ErrorAction SilentlyContinue
Remove-Item $tempExtract -Recurse -Force -ErrorAction SilentlyContinue
