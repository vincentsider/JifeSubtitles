#!/bin/bash
# =============================================================================
# Build the faster-whisper container with CTranslate2 CUDA support
# =============================================================================
# This builds a custom container that supports:
# - large-v3, large-v3-turbo, medium, small (all multilingual)
# - GPU acceleration via CTranslate2 with CUDA
# - Japanese to English translation
#
# BUILD TIME: ~30-60 minutes (compiles CTranslate2 from source)
# DISK SPACE: ~8-10GB for the image
# =============================================================================

cd "$(dirname "$0")"

echo "=============================================="
echo "  Building faster-whisper Container"
echo "=============================================="
echo "  This will take 30-60 minutes!"
echo "  It compiles CTranslate2 from source with CUDA."
echo "=============================================="
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 1
fi

echo ""
echo "Starting build..."
echo ""

# Build the container
docker compose --profile faster build --no-cache

if [ $? -eq 0 ]; then
    echo ""
    echo "=============================================="
    echo "  BUILD SUCCESSFUL!"
    echo "=============================================="
    echo ""
    echo "  You can now run: ./run-large-v3.sh"
    echo ""
else
    echo ""
    echo "=============================================="
    echo "  BUILD FAILED"
    echo "=============================================="
    echo ""
    echo "  Check the error messages above."
    echo "  Common issues:"
    echo "    - Not enough disk space (need ~10GB)"
    echo "    - Network issues downloading packages"
    echo ""
    exit 1
fi
