#!/bin/bash
# =============================================================================
# JIFE Windows - Run Script
# =============================================================================
# Starts the subtitle server in Docker.
# Run this in WSL2 terminal after building.
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=============================================="
echo "  JIFE Windows GPU - Starting Server"
echo "=============================================="

# Check if container is already running
if docker ps --format '{{.Names}}' | grep -q "^subtitle-server$"; then
    echo "Container is already running."
    echo ""
    echo "  View logs: docker logs subtitle-server -f"
    echo "  Stop:      docker compose down"
    echo "  Restart:   docker compose restart"
    exit 0
fi

# Start the container
echo ""
echo "Starting container..."
docker compose up -d

# Wait for startup
echo ""
echo "Waiting for server to initialize..."
sleep 5

# Check if running
if docker ps --format '{{.Names}}' | grep -q "^subtitle-server$"; then
    # Get IP address
    IP=$(hostname -I | awk '{print $1}')

    echo ""
    echo "=============================================="
    echo "  Server Started Successfully!"
    echo "=============================================="
    echo ""
    echo "  Access subtitles at:"
    echo "    http://${IP:-localhost}:5000"
    echo ""
    echo "  Commands:"
    echo "    View logs:  docker logs subtitle-server -f"
    echo "    Stop:       docker compose down"
    echo "    Restart:    docker compose restart"
    echo ""
else
    echo "ERROR: Container failed to start."
    echo "Check logs: docker logs subtitle-server"
    exit 1
fi
