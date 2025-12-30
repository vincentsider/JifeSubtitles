#!/bin/bash
# =============================================================================
# JIFE Cloud - Setup Script for Raspberry Pi 5
# =============================================================================
# Run this script to install all dependencies and configure the service.
#
# Usage:
#   chmod +x setup.sh
#   ./setup.sh
#
# After setup:
#   export GROQ_API_KEY="your-key-here"
#   sudo systemctl start jife-cloud
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=============================================="
echo "  JIFE Cloud - Setup for Raspberry Pi"
echo "=============================================="
echo ""

# Check if running on Pi
if [ "$(uname -m)" != "aarch64" ] && [ "$(uname -m)" != "armv7l" ]; then
    echo "WARNING: This script is designed for Raspberry Pi (ARM)."
    echo "         Current architecture: $(uname -m)"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 1: Update system
echo "[1/5] Updating system packages..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv portaudio19-dev libasound2-dev

# Step 2: Create virtual environment
echo ""
echo "[2/5] Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# Step 3: Install Python dependencies
echo ""
echo "[3/5] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Step 4: Copy web template if not exists
echo ""
echo "[4/5] Setting up web templates..."
if [ ! -d "templates" ]; then
    mkdir -p templates
fi

# Copy template from main project if available
if [ -f "../subtitle-product/app/web/templates/index.html" ]; then
    cp ../subtitle-product/app/web/templates/index.html templates/
    echo "  Copied index.html from main project"
elif [ ! -f "templates/index.html" ]; then
    echo "  WARNING: templates/index.html not found"
    echo "  Copy it from subtitle-product/app/web/templates/index.html"
fi

# Step 5: Install systemd service
echo ""
echo "[5/5] Installing systemd service..."
sudo tee /etc/systemd/system/jife-cloud.service > /dev/null << EOF
[Unit]
Description=JIFE Cloud Subtitle Service
After=network.target sound.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$SCRIPT_DIR
Environment="PATH=$SCRIPT_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="GROQ_API_KEY="
ExecStart=$SCRIPT_DIR/venv/bin/python3 $SCRIPT_DIR/main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload

echo ""
echo "=============================================="
echo "  Setup Complete!"
echo "=============================================="
echo ""
echo "  Next steps:"
echo ""
echo "  1. Get a Groq API key:"
echo "     https://console.groq.com/keys"
echo ""
echo "  2. Set your API key:"
echo "     sudo systemctl edit jife-cloud"
echo "     Add: Environment=\"GROQ_API_KEY=your-key-here\""
echo ""
echo "     OR edit /etc/systemd/system/jife-cloud.service directly"
echo ""
echo "  3. Connect USB audio adapter and find device:"
echo "     arecord -l"
echo ""
echo "  4. Start the service:"
echo "     sudo systemctl start jife-cloud"
echo "     sudo systemctl enable jife-cloud  # Auto-start on boot"
echo ""
echo "  5. View logs:"
echo "     sudo journalctl -u jife-cloud -f"
echo ""
echo "  6. Access subtitles:"
echo "     http://$(hostname -I | awk '{print $1}'):5000"
echo ""
