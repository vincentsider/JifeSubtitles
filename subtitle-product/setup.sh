#!/bin/bash
#
# JIFE Subtitle System - One-Click Setup
#
# REQUIREMENTS:
#   - Jetson Orin NX or Orin Nano
#   - JetPack 6.x (6.0, 6.1, 6.2, or 6.2.1) - NOT JetPack 7.x
#   - Docker already installed (comes with JetPack)
#
# SETUP INSTRUCTIONS:
#   1. On new Jetson, open terminal and run:
#        cd /home/$USER
#        git clone https://github.com/vincentsider/JifeSubtitles.git
#
#   2. Copy jife-faster-whisper.tar.gz to /home/$USER/JifeSubtitles/
#      (use USB drive or SCP from source Jetson)
#
#   3. Run this script:
#        cd /home/$USER/JifeSubtitles/subtitle-product
#        sudo ./setup.sh
#
#   4. Done. Service auto-starts on boot.
#

set -e

echo "=============================================="
echo "  JIFE Subtitle System - Setup"
echo "=============================================="

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGE_FILE="$SCRIPT_DIR/../jife-faster-whisper.tar.gz"
IMAGE_NAME="jife-faster-whisper:latest"

# Check if running as root for systemd operations
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo: sudo ./setup.sh"
    exit 1
fi

# Step 1: Load Docker image if not already present
echo ""
echo "[1/4] Checking Docker image..."
if docker images --format '{{.Repository}}:{{.Tag}}' | grep -q "$IMAGE_NAME"; then
    echo "  Docker image already exists, skipping load."
else
    if [ -f "$IMAGE_FILE" ]; then
        echo "  Loading Docker image (this takes 5-10 minutes)..."
        gunzip -c "$IMAGE_FILE" | docker load
        echo "  Docker image loaded successfully."
    else
        echo "  ERROR: Docker image file not found: $IMAGE_FILE"
        echo "  Please copy jife-faster-whisper.tar.gz to: $(dirname $IMAGE_FILE)/"
        exit 1
    fi
fi

# Step 2: Create swap file for better performance
echo ""
echo "[2/6] Setting up 16GB swap file..."
if [ -f /swapfile ]; then
    echo "  Swap file already exists, skipping."
else
    fallocate -l 16G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "  16GB swap file created and enabled."
fi

# Step 3: Create directories
echo ""
echo "[3/6] Creating directories..."
mkdir -p /home/$(logname)/JIFE/models/whisper
chown -R $(logname):$(logname) /home/$(logname)/JIFE

# Step 4: Make power control script executable
echo ""
echo "[4/6] Setting up power control..."
chmod +x "$SCRIPT_DIR/scripts/power-control.sh"

# Step 5: Install systemd service
echo ""
echo "[5/6] Installing systemd service..."
cp "$SCRIPT_DIR/jife-subtitles.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable jife-subtitles
echo "  Service installed and enabled for auto-start."

# Step 6: Start the service
echo ""
echo "[6/6] Starting JIFE service..."
systemctl start jife-subtitles

echo ""
echo "=============================================="
echo "  SETUP COMPLETE!"
echo "=============================================="
echo ""
echo "  The service is now running."
echo "  Wait 2 minutes for initialization, then open:"
echo ""
echo "    http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "  Commands:"
echo "    sudo systemctl status jife-subtitles  - Check status"
echo "    sudo systemctl restart jife-subtitles - Restart"
echo "    docker logs subtitle-server --tail 50 - View logs"
echo ""
echo "  Hardware needed:"
echo "    - USB audio adapter with microphone INPUT (pink jack)"
echo "    - HDMI audio extractor"
echo "    - 3.5mm cable connecting extractor to USB adapter input"
echo ""
