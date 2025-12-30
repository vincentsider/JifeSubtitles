# =============================================================================
# JIFE Subtitle System - Windows/x86_64 with CUDA
# =============================================================================
# This Dockerfile is for Windows PCs with NVIDIA GPUs (RTX 20xx/30xx/40xx).
# Uses faster-whisper with float16 for best quality.
#
# Build: docker compose build
# Run:   docker compose up -d
# =============================================================================

FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

# Avoid interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    libportaudio2 \
    portaudio19-dev \
    libasound2-plugins \
    alsa-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
# Note: We use CUDA 12.x compatible versions
RUN pip install --upgrade pip && \
    pip install \
    faster-whisper>=1.0.0 \
    flask>=3.0.0 \
    flask-socketio>=5.3.0 \
    sounddevice>=0.4.6 \
    scipy>=1.11.0 \
    numpy>=1.24.0

# Set working directory
WORKDIR /app

# Copy application code
# When running with docker-compose, this is mounted as a volume instead
COPY app/ /app/app/

# Expose web port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Default command
CMD ["python3", "/app/app/main.py"]
