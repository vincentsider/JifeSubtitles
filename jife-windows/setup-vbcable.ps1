# =============================================================================
# JIFE Windows - VB-CABLE Audio Setup Script
# =============================================================================
# Run this AFTER installing VB-CABLE and VoiceMeeter
# Right-click and "Run with PowerShell"
# =============================================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  JIFE - VB-CABLE Setup Wizard" -ForegroundColor Cyan
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

# Step 1: Install usbipd
Write-Host "[1/5] Installing usbipd..." -ForegroundColor Green
$null = winget install --id dorssel.usbipd-win --silent --accept-source-agreements --accept-package-agreements 2>&1
if ($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq -1978335189) {
    Write-Host "  ✓ usbipd installed" -ForegroundColor Green
} else {
    Write-Host "  ✓ usbipd already installed or installation skipped" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[2/5] Finding VB-CABLE device..." -ForegroundColor Green

# List USB devices and find VB-CABLE
$devices = usbipd list 2>&1 | Out-String
Write-Host $devices

# Try to find VB-CABLE or VB-Audio device
$vbcableLine = $devices -split "`n" | Where-Object {
    $_ -match "VB-Audio|CABLE|VB Audio" -and $_ -match "(\d+-\d+)"
} | Select-Object -First 1

if ($vbcableLine) {
    if ($vbcableLine -match "(\d+-\d+)") {
        $busId = $matches[1]
        Write-Host "  ✓ Found VB-CABLE device: $busId" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Could not extract Bus ID from: $vbcableLine" -ForegroundColor Yellow
        $busId = $null
    }
} else {
    Write-Host "  ⚠ VB-CABLE device not found in USB list" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "This might be normal - VB-CABLE is a virtual device." -ForegroundColor Yellow
    Write-Host "Continuing with manual configuration..." -ForegroundColor Yellow
    $busId = $null
}

# Step 3: Bind and attach VB-CABLE (if found)
if ($busId) {
    Write-Host ""
    Write-Host "[3/5] Binding VB-CABLE device..." -ForegroundColor Green
    $null = usbipd bind --busid $busId 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Device bound" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Could not bind (may already be bound)" -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "[4/5] Attaching VB-CABLE to WSL2..." -ForegroundColor Green
    $null = usbipd attach --wsl --busid $busId 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Device attached to WSL2" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Could not attach device" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "[3/5] Skipping bind (VB-CABLE not found)" -ForegroundColor Yellow
    Write-Host "[4/5] Skipping attach (VB-CABLE not found)" -ForegroundColor Yellow
}

# Step 5: Check audio devices in WSL2
Write-Host ""
Write-Host "[5/5] Checking audio devices in WSL2..." -ForegroundColor Green

# First check if alsa-utils is installed in WSL2
Write-Host "  Installing audio tools in WSL2..." -ForegroundColor Cyan
wsl bash -c 'sudo apt-get update > /dev/null 2>&1; sudo apt-get install -y alsa-utils > /dev/null 2>&1'

Write-Host ""
$audioDevices = wsl bash -c 'arecord -l' 2>&1 | Out-String
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
wsl bash -c 'cd /mnt/c/Projects/priority/JifeSubtitles/jife-windows; docker compose restart'
Write-Host "  ✓ Container restarted" -ForegroundColor Green

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Open VoiceMeeter" -ForegroundColor White
Write-Host "2. Set Windows playback device to 'VoiceMeeter Input'" -ForegroundColor White
Write-Host "   (Right-click speaker icon > Sound settings)" -ForegroundColor Gray
Write-Host "3. In VoiceMeeter:" -ForegroundColor White
Write-Host "   - A1: Select your speakers" -ForegroundColor Gray
Write-Host "   - B1: Click to enable (should show 'B1: CABLE Input')" -ForegroundColor Gray
Write-Host "4. Play Japanese content and open: http://localhost:5000" -ForegroundColor White
Write-Host ""
Write-Host "If audio card was found: Card $cardNumber" -ForegroundColor Green

if (-not $cardNumber) {
    Write-Host ""
    Write-Host "⚠ Audio device not detected!" -ForegroundColor Yellow
    Write-Host "You may need to:" -ForegroundColor Yellow
    Write-Host "  1. Make sure VB-CABLE is playing audio" -ForegroundColor Gray
    Write-Host "  2. Restart this script" -ForegroundColor Gray
    Write-Host "  3. Check VoiceMeeter is configured correctly" -ForegroundColor Gray
}

Write-Host ""
Read-Host "Press Enter to exit"
