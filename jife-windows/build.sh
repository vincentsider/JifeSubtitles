#!/bin/bash
# =============================================================================
# JIFE Windows - Build Script
# =============================================================================
# Run this in WSL2 terminal to build the Docker image.
#
# Prerequisites:
#   - Docker Desktop running
#   - NVIDIA Container Toolkit installed
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=============================================="
echo "  JIFE Windows GPU - Building Docker Image"
echo "=============================================="

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker is not running. Start Docker Desktop first."
    exit 1
fi

# Check GPU access
echo ""
echo "[1/3] Checking GPU access..."
if docker run --rm --gpus all nvidia/cuda:12.1-base-ubuntu22.04 nvidia-smi > /dev/null 2>&1; then
    echo "  GPU access: OK"
else
    echo "  WARNING: GPU not detected. Make sure NVIDIA Container Toolkit is installed."
    echo "  Install it with:"
    echo "    distribution=\$(. /etc/os-release;echo \$ID\$VERSION_ID)"
    echo "    curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -"
    echo "    curl -s -L https://nvidia.github.io/nvidia-docker/\$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list"
    echo "    sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit"
    echo "    sudo systemctl restart docker"
fi

# Copy app code if not exists
echo ""
echo "[2/3] Setting up application code..."
if [ ! -d "app" ]; then
    # Copy from main subtitle-product
    if [ -d "../subtitle-product/app" ]; then
        echo "  Copying app code from subtitle-product..."
        cp -r ../subtitle-product/app ./app
    else
        echo "  ERROR: Cannot find app code. Make sure subtitle-product/app exists."
        exit 1
    fi
else
    echo "  App code already exists."
fi

# Build Docker image
echo ""
echo "[3/3] Building Docker image (this takes 10-20 minutes)..."
docker compose build

echo ""
echo "=============================================="
echo "  Build Complete!"
echo "=============================================="
echo ""
echo "  Next steps:"
echo "    1. Connect USB audio adapter"
echo "    2. Attach it to WSL2: usbipd attach --wsl --busid <ID>"
echo "    3. Find device: arecord -l"
echo "    4. Edit AUDIO_DEVICE in docker-compose.yml if needed"
echo "    5. Run: ./run.sh"
echo ""
