#!/bin/bash
# =============================================================================
# Run JIFE Subtitles with MEDIUM model (Standard Whisper)
# =============================================================================
# - Uses existing whisper_trt container
# - Model: medium (769M params)
# - GPU: Yes (PyTorch CUDA)
# - Japanese translation: Yes
# - Speed: RTF ~2-3 (acceptable)
# =============================================================================

cd "$(dirname "$0")"

echo "=============================================="
echo "  JIFE Subtitles - MEDIUM Model"
echo "=============================================="
echo "  Model:    medium (769M params)"
echo "  Backend:  Standard Whisper (PyTorch CUDA)"
echo "  Speed:    RTF ~2-3"
echo "=============================================="

# Stop any running container
docker compose down 2>/dev/null

# Start with default profile (medium)
docker compose up -d

echo ""
echo "Started! Access at: http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "View logs: docker logs subtitle-server -f"
