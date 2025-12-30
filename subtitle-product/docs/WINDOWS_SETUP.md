# JIFE on Windows - Local GPU Setup

Run JIFE locally on your Windows machine with NVIDIA GPU for the best quality and lowest latency.

---

## Overview

| Aspect | Value |
|--------|-------|
| Hardware | Windows PC with NVIDIA GPU (RTX 4080 recommended) |
| VRAM Required | 4GB+ (large-v3 uses ~3GB) |
| RAM Required | 16GB+ |
| Expected Latency | < 0.5 seconds |
| Cost | $0 (local inference) |
| Internet Required | No |

---

## Architecture

```
HDMI Source (ForJoyTV, etc.)
       |
       v
  HDMI Audio Extractor
       |
       +---> HDMI OUT ---> TV (video)
       |
       +---> 3.5mm out ---> USB Audio Adapter ---> Windows PC
                                                        |
                                                   Docker + faster-whisper
                                                        |
                                                   http://PC_IP:5000
                                                        |
                                                   iPad/Phone (subtitles)
```

---

## Prerequisites

1. **Windows 10/11** with WSL2 enabled
2. **NVIDIA GPU** with CUDA support (RTX 20xx, 30xx, 40xx series)
3. **Docker Desktop** with WSL2 backend
4. **NVIDIA Container Toolkit**
5. **USB Audio Adapter** (same as Jetson setup)
6. **HDMI Audio Extractor** (same as Jetson setup)

---

## Step 1: Install Docker Desktop with NVIDIA GPU Support

### 1.1 Enable WSL2

Open PowerShell as Administrator:
```powershell
wsl --install
```

Restart your computer.

### 1.2 Install Docker Desktop

1. Download from https://www.docker.com/products/docker-desktop/
2. Install with WSL2 backend (default)
3. Enable "Use WSL 2 based engine" in Docker Desktop settings

### 1.3 Install NVIDIA Container Toolkit

In WSL2 Ubuntu terminal:
```bash
# Add NVIDIA repository
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# Install
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Restart Docker
sudo systemctl restart docker
```

### 1.4 Verify GPU Access

```bash
docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu22.04 nvidia-smi
```

You should see your GPU listed.

---

## Step 2: Clone Repository

In WSL2 terminal:
```bash
cd ~
git clone https://github.com/vincentsider/JifeSubtitles.git
cd JifeSubtitles
```

---

## Step 3: Build Docker Image for Windows

The Jetson image won't work on Windows (ARM64 vs x86_64). You need to build a new image.

### 3.1 Create Windows Dockerfile

Create `subtitle-product/Dockerfile.windows`:

```dockerfile
# JIFE Subtitle System - Windows/x86_64 with CUDA
FROM nvidia/cuda:12.1-cudnn8-runtime-ubuntu22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    libportaudio2 \
    libasound2-plugins \
    alsa-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install \
    faster-whisper \
    flask \
    flask-socketio \
    sounddevice \
    scipy \
    numpy

# Set working directory
WORKDIR /app

# Default command
CMD ["python3", "/app/app/main.py"]
```

### 3.2 Create Windows docker-compose

Create `subtitle-product/docker-compose.windows.yml`:

```yaml
# JIFE for Windows with NVIDIA GPU
services:
  subtitle-server:
    build:
      context: .
      dockerfile: Dockerfile.windows

    container_name: subtitle-server

    working_dir: /app
    command: ["python3", "/app/app/main.py"]

    # NVIDIA GPU support for Windows/WSL2
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

    restart: unless-stopped

    # Audio device (may need adjustment for Windows)
    devices:
      - /dev/snd:/dev/snd

    group_add:
      - audio

    environment:
      - AUDIO_DEVICE=${AUDIO_DEVICE:-plughw:1,0}
      - WHISPER_MODEL=${WHISPER_MODEL:-large-v3}
      - WHISPER_BACKEND=${WHISPER_BACKEND:-faster_whisper}
      - WHISPER_COMPUTE_TYPE=${WHISPER_COMPUTE_TYPE:-float16}
      - WHISPER_BEAM_SIZE=${WHISPER_BEAM_SIZE:-5}
      - WEB_PORT=5000
      - LOG_LEVEL=${LOG_LEVEL:-INFO}

    ports:
      - "5000:5000"

    volumes:
      - .:/app
      - faster_whisper_cache:/root/.cache/huggingface

volumes:
  faster_whisper_cache:
    driver: local
```

**Note**: On Windows with 16GB VRAM, you can use:
- `compute_type=float16` (best quality)
- `beam_size=5` (better accuracy)
- No memory pressure!

---

## Step 4: Connect Audio Hardware

### Option A: USB Audio in WSL2 (Recommended)

1. Plug USB audio adapter into Windows PC
2. Install usbipd-win to pass USB to WSL2:

```powershell
# In PowerShell (Admin)
winget install usbipd
```

3. Attach USB audio to WSL2:

```powershell
# List USB devices
usbipd list

# Attach audio device (replace BUSID with actual)
usbipd bind --busid <BUSID>
usbipd attach --wsl --busid <BUSID>
```

4. Verify in WSL2:
```bash
arecord -l
```

### Option B: PulseAudio Bridge

If USB passthrough doesn't work, use PulseAudio to bridge Windows audio to WSL2.

---

## Step 5: Build and Run

```bash
cd ~/JifeSubtitles/subtitle-product

# Build the Windows image
docker compose -f docker-compose.windows.yml build

# Run
docker compose -f docker-compose.windows.yml up -d

# Check logs
docker logs subtitle-server -f
```

---

## Step 6: Access Subtitles

1. Find your Windows PC's IP address:
   ```powershell
   ipconfig
   ```

2. On iPad/phone, open: `http://YOUR_PC_IP:5000`

---

## Expected Performance

| Metric | Value |
|--------|-------|
| Model | large-v3 float16 |
| VRAM Usage | ~3GB |
| RTF | 0.1 - 0.2 |
| Latency | < 0.5 seconds |
| Quality | Best |

---

## Troubleshooting

### GPU not detected

```bash
# Check NVIDIA driver in WSL2
nvidia-smi

# Reinstall container toolkit
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### Audio device not found

```bash
# List devices in WSL2
arecord -l

# Try different device
AUDIO_DEVICE=plughw:0,0 docker compose -f docker-compose.windows.yml up
```

### Permission denied for /dev/snd

```bash
# Add user to audio group
sudo usermod -aG audio $USER
```

---

## Comparison with Jetson

| Aspect | Windows 4080 | Jetson Orin Nano |
|--------|--------------|------------------|
| Latency | < 0.5s | 3-5s (large-v3) |
| Quality | Best (float16) | Good (int8) |
| Power | 300W | 10W |
| Portable | No | Yes |
| Cost | $0 (own it) | $0 (own it) |
| Always-on | No (desktop) | Yes |

**Use Windows when**: You want best quality and are at your desk.
**Use Jetson when**: You want always-on, portable, or low power.

---

*Document created: December 30, 2025*
