# =============================================================================
# JIFE Windows - Hardware HDMI Audio Setup Script
# =============================================================================
# Run this AFTER plugging in your USB audio device
# Right-click and "Run with PowerShell"
# =============================================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  JIFE - Hardware HDMI Audio Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Please run this script as Administrator!" -ForegroundColor Red
    Write-Host "Right-click the script and select 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "This script will:" -ForegroundColor Yellow
Write-Host "  1. Install usbipd (for USB passthrough)" -ForegroundColor White
Write-Host "  2. Find your USB audio device" -ForegroundColor White
Write-Host "  3. Attach it to WSL2" -ForegroundColor White
Write-Host "  4. Configure JIFE to use it" -ForegroundColor White
Write-Host "  5. Restart the container" -ForegroundColor White
Write-Host ""
Write-Host "Make sure your USB audio device is plugged in!" -ForegroundColor Yellow
Write-Host ""
Read-Host "Press Enter to continue"

# Step 1: Install usbipd
Write-Host ""
Write-Host "[1/5] Installing usbipd..." -ForegroundColor Green
try {
    winget install --id dorssel.usbipd-win --silent --accept-source-agreements --accept-package-agreements
    Write-Host "  ✓ usbipd installed" -ForegroundColor Green
} catch {
    Write-Host "  ✓ usbipd already installed or installation skipped" -ForegroundColor Yellow
}

# Step 2: List USB devices
Write-Host ""
Write-Host "[2/5] Scanning for USB audio devices..." -ForegroundColor Green
Write-Host ""
$devices = usbipd list 2>&1 | Out-String
Write-Host $devices

# Try to find USB audio device
Write-Host "Looking for USB audio devices..." -ForegroundColor Cyan
$audioLines = $devices -split "`n" | Where-Object {
    $_ -match "Audio|Sound|USB.*Audio|C-Media|Realtek|Creative" -and $_ -match "(\d+-\d+)"
}

if ($audioLines) {
    Write-Host ""
    Write-Host "Found possible audio device(s):" -ForegroundColor Green
    $audioLines | ForEach-Object { Write-Host "  $_" -ForegroundColor White }

    # Get the first audio device
    $firstAudioLine = $audioLines | Select-Object -First 1
    if ($firstAudioLine -match "(\d+-\d+)") {
        $busId = $matches[1]
        Write-Host ""
        Write-Host "Will use device: $busId" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Could not extract Bus ID" -ForegroundColor Yellow
        $busId = $null
    }
} else {
    Write-Host ""
    Write-Host "  ⚠ No USB audio device found automatically" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please look at the list above and enter the Bus ID manually." -ForegroundColor Yellow
    Write-Host "The Bus ID looks like: 1-4 or 2-3" -ForegroundColor Gray
    Write-Host ""
    $busId = Read-Host "Enter Bus ID (or press Enter to skip)"

    if ([string]::IsNullOrWhiteSpace($busId)) {
        Write-Host "Skipping automatic setup. You'll need to configure manually." -ForegroundColor Yellow
        $busId = $null
    }
}

# Step 3: Bind the device
if ($busId) {
    Write-Host ""
    Write-Host "[3/5] Binding USB device $busId..." -ForegroundColor Green
    try {
        usbipd bind --busid $busId
        Write-Host "  ✓ Device bound" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠ Could not bind (may already be bound)" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "[3/5] Skipping bind (no device selected)" -ForegroundColor Yellow
}

# Step 4: Attach to WSL2
if ($busId) {
    Write-Host ""
    Write-Host "[4/5] Attaching device to WSL2..." -ForegroundColor Green
    try {
        usbipd attach --wsl --busid $busId
        Write-Host "  ✓ Device attached to WSL2" -ForegroundColor Green
        Write-Host ""
        Write-Host "  NOTE: After Windows restarts, you'll need to run:" -ForegroundColor Yellow
        Write-Host "    usbipd attach --wsl --busid $busId" -ForegroundColor Gray
        Write-Host "  Or just run this script again!" -ForegroundColor Gray
    } catch {
        Write-Host "  ⚠ Could not attach device" -ForegroundColor Yellow
        Write-Host "  Error: $_" -ForegroundColor Red
    }

    # Wait a moment for device to settle
    Start-Sleep -Seconds 2
} else {
    Write-Host ""
    Write-Host "[4/5] Skipping attach (no device selected)" -ForegroundColor Yellow
}

# Step 5: Check audio in WSL2
Write-Host ""
Write-Host "[5/5] Checking audio devices in WSL2..." -ForegroundColor Green

# Install alsa-utils if needed
Write-Host "  Installing audio tools in WSL2..." -ForegroundColor Cyan
wsl bash -c "sudo apt-get update > /dev/null 2>&1 && sudo apt-get install -y alsa-utils > /dev/null 2>&1"

Write-Host ""
$audioDevices = wsl bash -c "arecord -l 2>&1"
Write-Host $audioDevices

# Parse audio device info
$cardNumber = $null
if ($audioDevices -match "card (\d+)") {
    $cardNumber = $matches[1]
    Write-Host ""
    Write-Host "  ✓ Found audio card: $cardNumber" -ForegroundColor Green
}

# Step 6: Update docker-compose.yml
Write-Host ""
Write-Host "Updating docker-compose.yml..." -ForegroundColor Green

$composeFile = "C:\Projects\priority\JifeSubtitles\jife-windows\docker-compose.yml"
if (Test-Path $composeFile) {
    $content = Get-Content $composeFile -Raw

    # Uncomment devices section
    $content = $content -replace '#\s*devices:', 'devices:'
    $content = $content -replace '#\s*-\s*/dev/snd:/dev/snd', '      - /dev/snd:/dev/snd'

    # Uncomment group_add section
    $content = $content -replace '#\s*group_add:', 'group_add:'
    $content = $content -replace '#\s*-\s*audio', '      - audio'

    # Update AUDIO_DEVICE if we found a card
    if ($cardNumber) {
        $content = $content -replace 'AUDIO_DEVICE=\$\{AUDIO_DEVICE:-plughw:\d+,0\}', "AUDIO_DEVICE=`${AUDIO_DEVICE:-plughw:$cardNumber,0}"
    }

    Set-Content $composeFile $content
    Write-Host "  ✓ docker-compose.yml updated" -ForegroundColor Green
} else {
    Write-Host "  ⚠ docker-compose.yml not found at: $composeFile" -ForegroundColor Yellow
}

# Step 7: Restart container
Write-Host ""
Write-Host "Restarting Docker container..." -ForegroundColor Green
wsl bash -c "cd /mnt/c/Projects/priority/JifeSubtitles/jife-windows && docker compose restart"
Write-Host "  ✓ Container restarted" -ForegroundColor Green

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

if ($busId -and $cardNumber) {
    Write-Host "✓ USB audio device configured successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Bus ID: $busId" -ForegroundColor White
    Write-Host "  Audio Card: $cardNumber" -ForegroundColor White
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Make sure audio is playing through your USB device" -ForegroundColor White
    Write-Host "2. Play some Japanese content" -ForegroundColor White
    Write-Host "3. Open http://localhost:5000 to see subtitles" -ForegroundColor White
    Write-Host ""
    Write-Host "IMPORTANT: After Windows restarts, run this script again!" -ForegroundColor Yellow
    Write-Host "Or manually run: usbipd attach --wsl --busid $busId" -ForegroundColor Gray
} else {
    Write-Host "⚠ Could not fully configure audio device!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Manual steps needed:" -ForegroundColor Yellow
    Write-Host "1. Run: usbipd list" -ForegroundColor White
    Write-Host "2. Find your USB audio device Bus ID" -ForegroundColor White
    Write-Host "3. Run: usbipd bind --busid <BUSID>" -ForegroundColor White
    Write-Host "4. Run: usbipd attach --wsl --busid <BUSID>" -ForegroundColor White
    Write-Host "5. Run this script again" -ForegroundColor White
}

Write-Host ""
Read-Host "Press Enter to exit"
