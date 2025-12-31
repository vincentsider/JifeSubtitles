# =============================================================================
# JIFE Windows - Simple Audio Setup Script
# =============================================================================
# This script sets up audio for JIFE (both VB-CABLE and Hardware options)
# Right-click and "Run as Administrator"
# =============================================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  JIFE - Audio Setup Wizard" -ForegroundColor Cyan
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

# Step 1: Install usbipd if not already installed
Write-Host "[Step 1/4] Installing usbipd..." -ForegroundColor Green
winget install --id dorssel.usbipd-win --silent --accept-source-agreements --accept-package-agreements 2>&1 | Out-Null
Write-Host "  Done (installed or already present)" -ForegroundColor Green

# Step 2: Install audio tools in WSL2
Write-Host ""
Write-Host "[Step 2/4] Installing audio tools in WSL2..." -ForegroundColor Green
wsl bash -c 'sudo apt-get update > /dev/null 2>&1; sudo apt-get install -y alsa-utils > /dev/null 2>&1'
Write-Host "  Done" -ForegroundColor Green

# Step 3: Enable audio in docker-compose.yml
Write-Host ""
Write-Host "[Step 3/4] Updating docker-compose.yml..." -ForegroundColor Green

$composeFile = "C:\Projects\priority\JifeSubtitles\jife-windows\docker-compose.yml"
if (Test-Path $composeFile) {
    $content = Get-Content $composeFile -Raw

    # Uncomment devices section
    $content = $content -replace '#\s*devices:', 'devices:'
    $content = $content -replace '#\s*-\s*/dev/snd:/dev/snd', '      - /dev/snd:/dev/snd'

    # Uncomment group_add section
    $content = $content -replace '#\s*group_add:', 'group_add:'
    $content = $content -replace '#\s*-\s*audio', '      - audio'

    Set-Content $composeFile $content
    Write-Host "  Done" -ForegroundColor Green
} else {
    Write-Host "  ERROR: docker-compose.yml not found!" -ForegroundColor Red
}

# Step 4: Instructions for user
Write-Host ""
Write-Host "[Step 4/4] Final setup..." -ForegroundColor Green
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Almost Done!" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Choose which audio method you want to use:" -ForegroundColor Yellow
Write-Host ""
Write-Host "Option A: VB-CABLE (for YouTube/browser audio)" -ForegroundColor Cyan
Write-Host "  1. Make sure VoiceMeeter is running" -ForegroundColor White
Write-Host "  2. Set Windows playback to 'VoiceMeeter Input'" -ForegroundColor White
Write-Host "  3. In VoiceMeeter: A1 = your speakers, B1 = enabled" -ForegroundColor White
Write-Host "  4. Play some audio to activate VB-CABLE" -ForegroundColor White
Write-Host ""
Write-Host "Option B: USB Audio Device (for HDMI hardware)" -ForegroundColor Cyan
Write-Host "  1. Plug in your USB audio device" -ForegroundColor White
Write-Host "  2. Run: usbipd list" -ForegroundColor White
Write-Host "  3. Find the Bus ID (like 1-4)" -ForegroundColor White
Write-Host "  4. Run: usbipd bind --busid <BUSID>" -ForegroundColor White
Write-Host "  5. Run: usbipd attach --wsl --busid <BUSID>" -ForegroundColor White
Write-Host ""
Read-Host "Press Enter when ready to restart the container"

# Restart container
Write-Host ""
Write-Host "Restarting Docker container..." -ForegroundColor Green
wsl bash -c 'cd /mnt/c/Projects/priority/JifeSubtitles/jife-windows; docker compose restart' 2>&1 | Out-Null
Write-Host "  Done" -ForegroundColor Green

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Open http://localhost:5000" -ForegroundColor White
Write-Host "2. Play Japanese content" -ForegroundColor White
Write-Host "3. See subtitles appear!" -ForegroundColor White
Write-Host ""
Write-Host "To check if audio is working:" -ForegroundColor Yellow
Write-Host "  wsl bash -c 'arecord -l'" -ForegroundColor Gray
Write-Host ""
Write-Host "To view logs:" -ForegroundColor Yellow
Write-Host "  wsl bash -c 'docker logs subtitle-server -f'" -ForegroundColor Gray
Write-Host ""
Read-Host "Press Enter to exit"
