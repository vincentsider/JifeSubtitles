# Start PulseAudio TCP server for Docker audio access
# Run this ONCE after Windows reboot, before starting subtitle-server

Write-Host "Starting PulseAudio TCP server for Docker..." -ForegroundColor Green

# Start PulseAudio with TCP module in WSL
wsl -e bash -c @"
# Kill any existing pulseaudio
pulseaudio --kill 2>/dev/null

# Start pulseaudio with TCP module
pulseaudio --start --exit-idle-time=-1

# Load TCP module (anonymous auth for Docker)
pactl load-module module-native-protocol-tcp auth-anonymous=1 port=4713 2>/dev/null || echo 'TCP module may already be loaded'

# Verify it's working
echo ''
echo 'PulseAudio status:'
pactl info 2>/dev/null | grep -E 'Server Name|Default Sink|Default Source' || echo 'PulseAudio not responding'
echo ''
echo 'Audio sources available:'
pactl list sources short 2>/dev/null || echo 'No sources found'
"@

Write-Host ""
Write-Host "Done. Now you can start the subtitle server:" -ForegroundColor Green
Write-Host "  docker start subtitle-server" -ForegroundColor Yellow
Write-Host ""
Write-Host "Or if container doesn't exist:" -ForegroundColor Green
Write-Host "  cd jife-windows && docker compose up -d" -ForegroundColor Yellow
