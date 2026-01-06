@echo off
echo ============================================
echo  JIFE Subtitle System - Windows Startup
echo ============================================
echo.

REM Start the container from WSL (required for audio to work)
echo Starting subtitle server...
wsl -e bash -c "cd /mnt/c/Projects/priority/JifeSubtitles/jife-windows && docker compose up -d"

echo.
echo ============================================
echo  READY! Open http://localhost:5000
echo ============================================
echo.
echo Press any key to view logs (Ctrl+C to exit)...
pause >nul
docker logs subtitle-server -f
