#!/bin/bash
# =============================================================================
# Run the Japanese -> English Subtitle System
# =============================================================================

set -e

# Default values
AUDIO_DEVICE="${AUDIO_DEVICE:-plughw:2,0}"
WHISPER_MODEL="${WHISPER_MODEL:-small}"
WEB_PORT="${WEB_PORT:-5000}"

echo "=============================================="
echo "  Japanese -> English Subtitle System"
echo "=============================================="
echo "  Audio Device: $AUDIO_DEVICE"
echo "  Whisper Model: $WHISPER_MODEL"
echo "  Web Port: $WEB_PORT"
echo "=============================================="

# Check if running with docker-compose or standalone
if command -v docker-compose &> /dev/null; then
    echo "Starting with docker-compose..."
    cd "$(dirname "$0")/.."
    docker-compose up --build
else
    echo "Starting with docker run..."
    docker run --rm -it \
        --runtime=nvidia \
        --device /dev/snd \
        --group-add audio \
        -e AUDIO_DEVICE="$AUDIO_DEVICE" \
        -e WHISPER_MODEL="$WHISPER_MODEL" \
        -e WEB_PORT="$WEB_PORT" \
        -p "$WEB_PORT:$WEB_PORT" \
        -v whisper_cache:/root/.cache/whisper_trt \
        subtitle-server
fi
