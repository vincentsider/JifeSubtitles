# =============================================================================
# JIFE Subtitle System - Windows/x86_64 with CUDA
# =============================================================================
# This Dockerfile is for Windows PCs with NVIDIA GPUs (RTX 20xx/30xx/40xx).
# Uses faster-whisper with float16 for best quality.
#
# Build: docker compose build
# Run:   docker compose up -d
# =============================================================================

FROM nvidia/cuda:12.1.0-cudnn8-devel-ubuntu22.04

# Avoid interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install cuDNN 9 manually
RUN apt-get update && apt-get install -y wget && \
    wget https://developer.download.nvidia.com/compute/cudnn/9.1.0/local_installers/cudnn-local-repo-ubuntu2204-9.1.0_1.0-1_amd64.deb && \
    dpkg -i cudnn-local-repo-ubuntu2204-9.1.0_1.0-1_amd64.deb && \
    cp /var/cudnn-local-repo-ubuntu2204-9.1.0/cudnn-*-keyring.gpg /usr/share/keyrings/ && \
    apt-get update && \
    apt-get install -y cudnn-cuda-12 && \
    rm cudnn-local-repo-ubuntu2204-9.1.0_1.0-1_amd64.deb && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set library path for cuDNN 9 runtime
ENV LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

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
    numpy>=1.24.0 \
    transformers>=4.35.0 \
    sentencepiece>=0.1.99 \
    protobuf>=3.20.0 \
    torch>=2.0.0 \
    torchaudio>=2.0.0

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
