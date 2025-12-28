#!/bin/bash
#
# JIFE One-Click Installer
# Run this from the USB drive on a new Jetson
#

set -e

echo "=============================================="
echo "  JIFE Subtitle System - USB Installer"
echo "=============================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo: sudo ./install.sh"
    exit 1
fi

USB_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="/home/$(logname)/JifeSubtitles"
IMAGE_FILE="$USB_DIR/whisper_trt_image.tar.gz"
IMAGE_NAME="whisper_trt:r36.4.tegra-aarch64-cu126-22.04-whisper_trt"

echo ""
echo "Installing from: $USB_DIR"
echo "Installing to:   $INSTALL_DIR"
echo ""

# Step 1: Copy repo files
echo "[1/4] Copying files..."
mkdir -p "$INSTALL_DIR"
cp -r "$USB_DIR/subtitle-product" "$INSTALL_DIR/"
cp "$USB_DIR/CLAUDE.md" "$INSTALL_DIR/" 2>/dev/null || true
cp "$USB_DIR/NEW_JETSON_SETUP.md" "$INSTALL_DIR/" 2>/dev/null || true
chown -R $(logname):$(logname) "$INSTALL_DIR"
echo "  Files copied."

# Step 2: Load Docker image
echo ""
echo "[2/4] Loading Docker image (5-10 minutes)..."
if docker images --format '{{.Repository}}:{{.Tag}}' | grep -q "$IMAGE_NAME"; then
    echo "  Docker image already exists, skipping."
else
    if [ -f "$IMAGE_FILE" ]; then
        gunzip -c "$IMAGE_FILE" | docker load
        echo "  Docker image loaded."
    else
        echo "  ERROR: Docker image not found: $IMAGE_FILE"
        exit 1
    fi
fi

# Step 3: Install systemd service
echo ""
echo "[3/4] Installing systemd service..."
cp "$INSTALL_DIR/subtitle-product/jife-subtitles.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable jife-subtitles
echo "  Service installed."

# Step 4: Start service
echo ""
echo "[4/4] Starting service..."
systemctl start jife-subtitles

echo ""
echo "=============================================="
echo "  INSTALLATION COMPLETE!"
echo "=============================================="
echo ""
echo "  Wait 2 minutes, then open in browser:"
echo "    http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "  Commands:"
echo "    sudo systemctl status jife-subtitles"
echo "    docker logs subtitle-server --tail 50"
echo ""
