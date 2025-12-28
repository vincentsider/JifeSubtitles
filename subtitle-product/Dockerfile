# =============================================================================
# Japanese -> English Real-Time Subtitle System
# Dockerfile for Jetson Orin Nano SUPER (JetPack 6.2+)
# =============================================================================

# Base image - use l4t-jetpack which includes CUDA, TensorRT, cuDNN
# For JetPack 6.2.1 (L4T r36.4.x), use r36.4.0 tag
ARG BASE_IMAGE=nvcr.io/nvidia/l4t-jetpack:r36.4.0
FROM ${BASE_IMAGE}

# Labels
LABEL maintainer="JIFE Project"
LABEL description="Japanese to English Real-Time Subtitle System"
LABEL version="1.0"

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-dev \
    alsa-utils \
    libasound2-dev \
    libportaudio2 \
    portaudio19-dev \
    ffmpeg \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Upgrade pip
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

# Install PyTorch from Jetson AI Lab (required for ARM64/Tegra)
# This matches JetPack 6.2 with CUDA 12.6
RUN pip3 install --no-cache-dir \
    torch==2.5.0 \
    torchvision==0.20.0 \
    --index-url=https://pypi.jetson-ai-lab.io/jp6/cu126

# Install numpy (specific version for compatibility)
RUN pip3 install --no-cache-dir numpy==1.26.4

# Install whisper_trt from NVIDIA-AI-IOT
WORKDIR /opt
RUN git clone --depth 1 https://github.com/NVIDIA-AI-IOT/whisper_trt.git \
    && cd whisper_trt \
    && pip3 install --no-cache-dir -e .

# Install additional Python dependencies
RUN pip3 install --no-cache-dir \
    sounddevice>=0.4.6 \
    flask>=3.0.0 \
    flask-socketio>=5.3.0 \
    gevent>=23.0.0 \
    gevent-websocket>=0.10.1 \
    eventlet>=0.35.0

# Create application directory
WORKDIR /app

# Copy application code
COPY app/ /app/

# Pre-download Whisper model during build (optional - makes first run faster)
# Uncomment the model size you want to pre-download:
# RUN python3 -c "from whisper_trt import load_trt_model; load_trt_model('tiny')"
# RUN python3 -c "from whisper_trt import load_trt_model; load_trt_model('base')"
# RUN python3 -c "from whisper_trt import load_trt_model; load_trt_model('small')"

# Create directories for logs and cache
RUN mkdir -p /var/log/subtitle-server /root/.cache/whisper_trt

# Expose web port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Default environment variables
ENV AUDIO_DEVICE=plughw:2,0
ENV WHISPER_MODEL=small
ENV WHISPER_BACKEND=whisper_trt
ENV WEB_PORT=5000
ENV LOG_LEVEL=INFO

# Entry point
CMD ["python3", "main.py"]
