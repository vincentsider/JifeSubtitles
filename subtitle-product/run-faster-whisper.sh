#!/bin/bash
# =============================================================================
# Run JIFE Subtitles with MEDIUM model (Faster-Whisper + CTranslate2 CUDA)
# =============================================================================
# - Uses custom faster-whisper container with CTranslate2 CUDA
# - Model: medium (769M params) - Best for Japanese translation
# - GPU: Yes (CTranslate2 CUDA) - Much faster than PyTorch!
# - Japanese translation: Yes (proper translation support)
# - Speed: RTF ~0.5 (FAST)
#
# NOTE: large-v3 doesn't fit in GPU memory, large-v3-turbo doesn't translate
# Medium model is the best option for translation with GPU acceleration
# =============================================================================

cd "$(dirname "$0")"

echo "=============================================="
echo "  JIFE Subtitles - MEDIUM (Faster-Whisper)"
echo "=============================================="
echo "  Model:    medium (769M params)"
echo "  Backend:  faster-whisper (CTranslate2 CUDA)"
echo "  Speed:    RTF ~0.5 (FAST)"
echo "=============================================="

# Check if container image exists
if ! docker images | grep -q "jife-faster-whisper"; then
    echo ""
    echo "ERROR: jife-faster-whisper image not found!"
    echo ""
    echo "You need to build it first. This takes ~30-60 minutes:"
    echo "  ./build-faster-whisper.sh"
    echo ""
    exit 1
fi

# Stop any running container
docker compose down 2>/dev/null
docker compose --profile faster down 2>/dev/null

# Start ONLY the faster-whisper service (not the default one)
docker compose --profile faster up -d subtitle-server-fast

echo ""
echo "Started! Access at: http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "NOTE: First run will download medium model (~1.5GB). This may take a few minutes."
echo ""
echo "View logs: docker logs subtitle-server-fast -f"
