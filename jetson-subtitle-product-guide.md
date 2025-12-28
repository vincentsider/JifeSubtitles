# Japanese TV Real-Time Subtitle System
## Product-Ready Guide for Jetson Orin Nano SUPER
### December 2025

---

## Overview

This guide builds a **commercial-grade** Japanese → English real-time subtitle system that:

- Works for personal use immediately
- Is structured for commercial product deployment
- Uses Docker for reproducibility and easy updates
- Runs 100% offline (no cloud, no subscriptions)

---

## Table of Contents

1. [Architecture Decision](#1-architecture-decision)
2. [Hardware Setup](#2-hardware-setup)
3. [JetPack 6.1+ Installation](#3-jetpack-61-installation)
4. [Enable SUPER Mode](#4-enable-super-mode)
5. [Verify Audio Input](#5-verify-audio-input)
6. [Docker Setup with NGC L4T](#6-docker-setup-with-ngc-l4t)
7. [Build Product Container](#7-build-product-container)
8. [Run and Test](#8-run-and-test)
9. [Production Deployment](#9-production-deployment)
10. [Commercial Packaging](#10-commercial-packaging)

---

## 1. Architecture Decision

### Why This Approach?

| Decision | Reason |
|----------|--------|
| **Docker** | Reproducible, easy updates, clean licensing, multi-customer support |
| **faster-whisper** | More stable than WhisperTRT, better streaming support, widely tested |
| **NGC L4T base** | Official NVIDIA, guaranteed compatibility, commercial-safe |
| **Local only** | No cloud costs, no latency, privacy-friendly, works offline |

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     COMMERCIAL PRODUCT                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   HARDWARE (What you sell)                                      │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  Jetson Orin Nano SUPER + SSD + Enclosure               │   │
│   │  + HDMI Audio Extractor + USB Audio Adapter + Cables    │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│   SOFTWARE STACK                                                │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  JetPack 6.x (L4T) ─────── Installed by you (setup)     │   │
│   │       │                                                 │   │
│   │       ▼                                                 │   │
│   │  Docker Runtime ────────── Included in JetPack          │   │
│   │       │                                                 │   │
│   │       ▼                                                 │   │
│   │  ┌─────────────────────────────────────────────────┐    │   │
│   │  │  YOUR CONTAINER (your IP, your value)           │    │   │
│   │  │                                                 │    │   │
│   │  │  Base: NGC L4T (nvcr.io/nvidia/l4t-base)       │    │   │
│   │  │       │                                         │    │   │
│   │  │       ├── faster-whisper (ASR)                  │    │   │
│   │  │       ├── NLLB (translation)                    │    │   │
│   │  │       ├── Audio capture (ALSA)                  │    │   │
│   │  │       ├── Web UI (Flask + WebSocket)            │    │   │
│   │  │       └── Service manager + watchdog            │    │   │
│   │  │                                                 │    │   │
│   │  └─────────────────────────────────────────────────┘    │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│   WHAT CUSTOMER SEES                                            │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  "Plug HDMI in → English subtitles on iPad"             │   │
│   │  (They never see Docker, JetPack, Whisper, etc.)        │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Hardware Setup

### Bill of Materials

| Component | Purpose | Est. Price (EUR) |
|-----------|---------|------------------|
| Jetson Orin Nano Developer Kit | AI processing | €249-300 |
| MicroSD Card 128GB+ (A2/V30) | Initial boot | €15-25 |
| NVMe SSD 256GB+ | Production storage | €30-50 |
| HDMI Splitter (1-in, 2-out) | Split video signal | €15-25 |
| HDMI Audio Extractor | Extract audio | €20-40 |
| USB Audio Adapter | Connect to Jetson | €10-20 |
| 3.5mm Audio Cable | Audio connection | €5-10 |
| Enclosure (for product) | Professional look | €20-50 |
| **Total BOM** | | **€365-520** |

### Connection Diagram

```
┌──────────────┐      ┌───────────────┐      ┌──────────────┐
│  Source      │ HDMI │    HDMI       │ HDMI │   TV         │
│  (Android TV)│─────▶│   Splitter    │─────▶│  (Display)   │
│  (ForJoyTV)  │      │   1-in 2-out  │      │              │
└──────────────┘      └───────┬───────┘      └──────────────┘
                              │
                              │ HDMI (copy)
                              ▼
                      ┌───────────────┐
                      │  HDMI Audio   │
                      │  Extractor    │
                      └───────┬───────┘
                              │ 3.5mm audio
                              ▼
                      ┌───────────────┐
                      │  USB Audio    │
                      │  Adapter      │
                      └───────┬───────┘
                              │ USB
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  JETSON ORIN NANO SUPER                     │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  Docker Container                                   │   │
│   │  ┌───────────┐  ┌───────────┐  ┌───────────┐       │   │
│   │  │ Audio     │  │ faster-   │  │ NLLB      │       │   │
│   │  │ Capture   │─▶│ whisper   │─▶│ Translate │       │   │
│   │  │ (ALSA)    │  │ (JP ASR)  │  │ (JP→EN)   │       │   │
│   │  └───────────┘  └───────────┘  └─────┬─────┘       │   │
│   │                                      │              │   │
│   │                                      ▼              │   │
│   │                              ┌───────────────┐      │   │
│   │                              │  Web Server   │      │   │
│   │                              │  (Flask+WS)   │      │   │
│   │                              └───────┬───────┘      │   │
│   └──────────────────────────────────────┼──────────────┘   │
│                                          │                  │
└──────────────────────────────────────────┼──────────────────┘
                                           │ WiFi/LAN
                                           ▼
                                   ┌───────────────┐
                                   │  iPad/Phone   │
                                   │  Browser      │
                                   │               │
                                   │  ┌─────────┐  │
                                   │  │ English │  │
                                   │  │ Subs    │  │
                                   │  └─────────┘  │
                                   └───────────────┘
```

---

## 3. JetPack 6.1+ Installation

### Why Fresh Install (Not Upgrade)?

> ⚠️ **Important**: Upgrading via `apt` from older JetPack may NOT activate Super Mode properly.
> A fresh flash of JetPack 6.1+ ensures Super Mode works correctly.

### Option A: SD Card Method (Simpler)

#### Step 1: Download Image

1. Go to: https://developer.nvidia.com/embedded/jetpack
2. Download **"Jetson Orin Nano Developer Kit"** SD card image
3. Make sure it's **JetPack 6.1 (rev. 1)** or later

#### Step 2: Flash SD Card

**On any OS (Windows/Mac/Linux):**

1. Download [balenaEtcher](https://www.balena.io/etcher/)
2. Insert SD card (128GB+, A2/V30 recommended)
3. Open balenaEtcher:
   - Select the downloaded image
   - Select your SD card
   - Click Flash
4. Wait 15-30 minutes

#### Step 3: First Boot

1. Insert SD card into Jetson (bottom of carrier board)
2. Connect: monitor, keyboard, mouse, ethernet (recommended)
3. Connect power (last)
4. Complete Ubuntu setup wizard
5. Create user account (remember credentials!)

### Option B: SDK Manager Method (More Control)

Use this for SSD installation or if you need more control.

#### Requirements
- Ubuntu 20.04 or 22.04 host PC
- USB-C cable
- Target: NVMe SSD in Jetson

#### Steps

```bash
# On Ubuntu host PC

# 1. Install SDK Manager
# Download from: https://developer.nvidia.com/sdk-manager
sudo apt install ./sdkmanager_*_amd64.deb

# 2. Put Jetson in Recovery Mode:
#    - Power off Jetson
#    - Hold Recovery button
#    - Connect power while holding Recovery
#    - Release after 2 seconds
#    - Connect USB-C to host PC

# 3. Verify connection
lsusb | grep -i nvidia
# Should show: "NVIDIA Corp. APX"

# 4. Run SDK Manager
sdkmanager

# 5. In SDK Manager:
#    - Select: Jetson Orin Nano Developer Kit
#    - Select: JetPack 6.1 or later
#    - Select: NVMe as storage target
#    - Flash and install all components
```

---

## 4. Enable SUPER Mode

### This is Critical!

Without SUPER mode, you're running at **40 TOPS instead of 67 TOPS** — a 40% performance loss.

### Step 1: Verify JetPack/L4T Version

```bash
# Check L4T version
cat /etc/nv_tegra_release

# Expected output (example):
# R36 (release), REVISION: 2.0, ...
# This means L4T r36.2 (JetPack 6.1)

# Also check JetPack version
apt show nvidia-jetpack 2>/dev/null | grep Version
```

**Record your L4T version** — you'll need it for Docker!

| JetPack | L4T Version | NGC Tag |
|---------|-------------|---------|
| 6.0 | r36.1 | r36.1.0 |
| 6.1 | r36.2 | r36.2.0 |
| 6.2 | r36.3 | r36.3.0 |

### Step 2: Enable MAXN (SUPER) Mode

```bash
# Check current power mode
sudo nvpmodel -q
# Probably shows: "NV Power Mode: 15W"

# Enable SUPER mode (25W MAXN)
sudo nvpmodel -m 2

# Verify
sudo nvpmodel -q
# Should show: "NV Power Mode: MAXN"

# Maximize clocks
sudo jetson_clocks

# Verify GPU clock (should be 1020 MHz, not 635 MHz)
sudo jetson_clocks --show | grep GPU
```

### Step 3: Make SUPER Mode Persistent

```bash
# Create startup script
sudo tee /etc/rc.local << 'EOF'
#!/bin/bash
# Enable SUPER mode on boot
nvpmodel -m 2
jetson_clocks
exit 0
EOF

sudo chmod +x /etc/rc.local

# Enable rc-local service
sudo systemctl enable rc-local
```

---

## 5. Verify Audio Input

### Find Your Audio Device

```bash
# List capture devices
arecord -l

# Expected output:
# **** List of CAPTURE Hardware Devices ****
# card 1: Device [USB Audio Device], device 0: USB Audio [USB Audio]
#     Subdevices: 1/1
#     Subdevice #0: subdevice #0
```

**Note the card number** (e.g., card 1 = `hw:1,0`)

### Test Audio Capture

```bash
# Record 5 seconds (replace hw:1,0 with your device)
arecord -D hw:1,0 -f S16_LE -r 16000 -c 1 -d 5 /tmp/test.wav

# Play back
aplay /tmp/test.wav
```

✅ If you hear the audio from your HDMI source, the hardware is working!

### Adjust Levels if Needed

```bash
alsamixer
# Press F6 to select USB Audio Device
# Adjust capture levels
# Press Esc to exit
```

---

## 6. Docker Setup with NGC L4T

### Why NGC L4T Base?

| Question | Answer |
|----------|--------|
| Why not regular Ubuntu image? | Won't have GPU access, CUDA broken |
| Why not install directly? | Docker = reproducible, updatable, commercial-ready |
| Why NGC specifically? | Official NVIDIA, guaranteed compatible, safe licensing |

### Install Docker (if not already)

```bash
# Docker should be included with JetPack, but verify:
docker --version

# If not installed:
sudo apt update
sudo apt install -y docker.io nvidia-container-toolkit

# Add yourself to docker group
sudo usermod -aG docker $USER

# Logout and login again, then verify:
docker run --rm hello-world
```

### Configure NVIDIA Container Runtime

```bash
# Verify nvidia runtime is available
docker info | grep -i nvidia

# If not showing, configure it:
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### Test GPU Access in Docker

```bash
# Replace r36.2.0 with YOUR L4T version from Step 4
docker run --rm --runtime=nvidia \
    nvcr.io/nvidia/l4t-base:r36.2.0 \
    nvidia-smi

# If nvidia-smi not available, try:
docker run --rm --runtime=nvidia \
    nvcr.io/nvidia/l4t-base:r36.2.0 \
    cat /etc/nv_tegra_release
```

---

## 7. Build Product Container

### Create Project Directory

```bash
mkdir -p ~/subtitle-product
cd ~/subtitle-product
```

### Create Dockerfile

```bash
cat > Dockerfile << 'DOCKERFILE'
# =============================================================================
# Japanese → English Real-Time Subtitle System
# Product Container for Jetson Orin Nano SUPER
# =============================================================================

# Base image - MUST match your L4T version!
# Check with: cat /etc/nv_tegra_release
# JetPack 6.1 = r36.2.0, JetPack 6.2 = r36.3.0
ARG L4T_VERSION=r36.2.0
FROM nvcr.io/nvidia/l4t-base:${L4T_VERSION}

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    ffmpeg \
    alsa-utils \
    libasound2-dev \
    libsndfile1 \
    portaudio19-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

# Install PyTorch for Jetson (L4T compatible)
# Note: For JetPack 6.x, PyTorch wheels are available from NVIDIA
RUN pip3 install --no-cache-dir \
    numpy \
    scipy

# Install faster-whisper (primary ASR engine)
# CTranslate2 backend, much faster than original Whisper
RUN pip3 install --no-cache-dir \
    faster-whisper \
    webrtcvad

# Install translation model dependencies
RUN pip3 install --no-cache-dir \
    transformers \
    sentencepiece \
    accelerate

# Install audio processing
RUN pip3 install --no-cache-dir \
    sounddevice \
    soundfile \
    pyaudio

# Install web server
RUN pip3 install --no-cache-dir \
    flask \
    flask-socketio \
    gevent \
    gevent-websocket \
    eventlet

# Create app directory
WORKDIR /app

# Copy application code
COPY app/ /app/

# Download models on first run (or pre-download in build)
# Uncomment below to pre-download (larger image, faster startup):
# RUN python3 -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu')"
# RUN python3 -c "from transformers import AutoModelForSeq2SeqLM, AutoTokenizer; AutoTokenizer.from_pretrained('facebook/nllb-200-distilled-600M'); AutoModelForSeq2SeqLM.from_pretrained('facebook/nllb-200-distilled-600M')"

# Expose web port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run the application
CMD ["python3", "main.py"]
DOCKERFILE
```

### Create Application Directory

```bash
mkdir -p ~/subtitle-product/app
```

### Create Main Application

```bash
cat > ~/subtitle-product/app/main.py << 'PYTHON'
#!/usr/bin/env python3
"""
Japanese → English Real-Time Subtitle System
Commercial-Grade Implementation

Features:
- faster-whisper for reliable ASR
- NLLB for offline translation
- Streaming audio processing
- Web-based subtitle display
- Robust error handling
- Logging for diagnostics
"""

import os
import sys
import time
import queue
import logging
import threading
import signal
from datetime import datetime

import numpy as np

# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    # Audio settings
    AUDIO_DEVICE = os.environ.get('AUDIO_DEVICE', None)  # None = default
    SAMPLE_RATE = 16000
    CHUNK_DURATION = 2.5  # seconds per chunk
    
    # Model settings
    WHISPER_MODEL = os.environ.get('WHISPER_MODEL', 'base')  # tiny, base, small, medium
    WHISPER_DEVICE = 'cuda'  # or 'cpu'
    WHISPER_COMPUTE_TYPE = 'float16'  # float16, int8, int8_float16
    
    # Translation
    TRANSLATION_MODEL = 'facebook/nllb-200-distilled-600M'
    USE_GPU_TRANSLATION = True
    
    # Server
    WEB_PORT = int(os.environ.get('WEB_PORT', 5000))
    WEB_HOST = '0.0.0.0'
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = '/var/log/subtitle-server.log'

# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logging():
    """Configure logging for production use"""
    log_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # File handler (if writable)
    handlers = [console_handler]
    try:
        os.makedirs(os.path.dirname(Config.LOG_FILE), exist_ok=True)
        file_handler = logging.FileHandler(Config.LOG_FILE)
        file_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(file_handler)
    except (PermissionError, OSError):
        pass  # Can't write to log file, use console only
    
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL.upper()),
        handlers=handlers
    )
    
    return logging.getLogger('subtitle-server')

logger = setup_logging()

# =============================================================================
# IMPORTS (after logging setup)
# =============================================================================

try:
    import sounddevice as sd
    logger.info("sounddevice loaded")
except ImportError as e:
    logger.error(f"Failed to import sounddevice: {e}")
    sys.exit(1)

try:
    from faster_whisper import WhisperModel
    logger.info("faster-whisper loaded")
except ImportError as e:
    logger.error(f"Failed to import faster-whisper: {e}")
    sys.exit(1)

try:
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    import torch
    logger.info(f"transformers loaded, CUDA available: {torch.cuda.is_available()}")
except ImportError as e:
    logger.error(f"Failed to import transformers: {e}")
    sys.exit(1)

try:
    from flask import Flask, render_template_string, jsonify
    from flask_socketio import SocketIO
    logger.info("Flask loaded")
except ImportError as e:
    logger.error(f"Failed to import Flask: {e}")
    sys.exit(1)

# =============================================================================
# GLOBAL STATE
# =============================================================================

# Processing queues
audio_queue = queue.Queue(maxsize=20)
text_queue = queue.Queue(maxsize=100)

# Models (loaded lazily)
whisper_model = None
nllb_model = None
nllb_tokenizer = None

# Statistics
stats = {
    'start_time': datetime.now().isoformat(),
    'transcriptions': 0,
    'translations': 0,
    'errors': 0,
    'avg_latency_ms': 0,
    'last_activity': None
}

# Shutdown flag
shutdown_event = threading.Event()

# =============================================================================
# MODEL LOADING
# =============================================================================

def load_whisper_model():
    """Load faster-whisper model"""
    global whisper_model
    
    logger.info(f"Loading Whisper model: {Config.WHISPER_MODEL}")
    logger.info(f"  Device: {Config.WHISPER_DEVICE}")
    logger.info(f"  Compute type: {Config.WHISPER_COMPUTE_TYPE}")
    
    try:
        whisper_model = WhisperModel(
            Config.WHISPER_MODEL,
            device=Config.WHISPER_DEVICE,
            compute_type=Config.WHISPER_COMPUTE_TYPE
        )
        logger.info("✓ Whisper model loaded successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to load Whisper: {e}")
        return False


def load_translation_model():
    """Load NLLB translation model"""
    global nllb_model, nllb_tokenizer
    
    logger.info(f"Loading translation model: {Config.TRANSLATION_MODEL}")
    
    try:
        nllb_tokenizer = AutoTokenizer.from_pretrained(Config.TRANSLATION_MODEL)
        nllb_model = AutoModelForSeq2SeqLM.from_pretrained(Config.TRANSLATION_MODEL)
        
        if Config.USE_GPU_TRANSLATION and torch.cuda.is_available():
            nllb_model = nllb_model.to('cuda')
            logger.info("✓ Translation model loaded (GPU)")
        else:
            logger.info("✓ Translation model loaded (CPU)")
        
        return True
    except Exception as e:
        logger.error(f"✗ Failed to load translation model: {e}")
        return False

# =============================================================================
# AUDIO PROCESSING
# =============================================================================

def get_audio_device():
    """Find and validate audio device"""
    device = Config.AUDIO_DEVICE
    
    if device is None:
        # Use default
        default = sd.default.device[0]
        logger.info(f"Using default audio device: {default}")
        return default
    
    # Try to parse as integer
    try:
        device = int(device)
        logger.info(f"Using audio device index: {device}")
        return device
    except ValueError:
        # Use as string name
        logger.info(f"Using audio device name: {device}")
        return device


def audio_capture_thread():
    """Continuously capture audio and send to processing queue"""
    logger.info("Starting audio capture thread")
    
    device = get_audio_device()
    samples_per_chunk = int(Config.SAMPLE_RATE * Config.CHUNK_DURATION)
    buffer = []
    
    def audio_callback(indata, frames, time_info, status):
        if status:
            logger.warning(f"Audio status: {status}")
        
        # Accumulate samples
        buffer.extend(indata[:, 0].tolist())
        
        # Process when we have enough
        while len(buffer) >= samples_per_chunk:
            chunk = np.array(buffer[:samples_per_chunk], dtype=np.float32)
            del buffer[:samples_per_chunk]
            
            # Check for actual audio (not silence)
            audio_level = np.abs(chunk).max()
            if audio_level > 0.01:  # Silence threshold
                try:
                    audio_queue.put_nowait(chunk)
                except queue.Full:
                    logger.warning("Audio queue full, dropping chunk")
    
    try:
        with sd.InputStream(
            device=device,
            samplerate=Config.SAMPLE_RATE,
            channels=1,
            dtype='float32',
            callback=audio_callback,
            blocksize=1024
        ):
            logger.info(f"✓ Audio capture started (device: {device})")
            while not shutdown_event.is_set():
                time.sleep(0.1)
    except Exception as e:
        logger.error(f"Audio capture error: {e}")
        logger.info("Available audio devices:")
        for i, dev in enumerate(sd.query_devices()):
            if dev['max_input_channels'] > 0:
                logger.info(f"  [{i}] {dev['name']}")

# =============================================================================
# TRANSCRIPTION
# =============================================================================

def transcription_thread():
    """Process audio chunks and transcribe to Japanese text"""
    logger.info("Starting transcription thread")
    
    while not shutdown_event.is_set():
        try:
            audio_chunk = audio_queue.get(timeout=1)
            start_time = time.time()
            
            # Transcribe with faster-whisper
            segments, info = whisper_model.transcribe(
                audio_chunk,
                language='ja',
                task='transcribe',  # Get Japanese text first
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200
                )
            )
            
            # Collect text from segments
            japanese_text = ' '.join([seg.text for seg in segments]).strip()
            
            transcription_time = time.time() - start_time
            
            if japanese_text and len(japanese_text) > 1:
                stats['transcriptions'] += 1
                stats['last_activity'] = datetime.now().isoformat()
                
                logger.debug(f"[ASR {transcription_time:.2f}s] {japanese_text}")
                
                text_queue.put({
                    'japanese': japanese_text,
                    'asr_time': transcription_time
                })
                
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            stats['errors'] += 1

# =============================================================================
# TRANSLATION
# =============================================================================

def translate_japanese_to_english(text):
    """Translate Japanese text to English using NLLB"""
    if not text or not text.strip():
        return ""
    
    try:
        device = 'cuda' if Config.USE_GPU_TRANSLATION and torch.cuda.is_available() else 'cpu'
        
        inputs = nllb_tokenizer(
            text,
            return_tensors='pt',
            padding=True,
            truncation=True,
            max_length=256
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        translated = nllb_model.generate(
            **inputs,
            forced_bos_token_id=nllb_tokenizer.lang_code_to_id['eng_Latn'],
            max_length=256,
            num_beams=4,
            early_stopping=True
        )
        
        english_text = nllb_tokenizer.decode(translated[0], skip_special_tokens=True)
        return english_text
        
    except Exception as e:
        logger.error(f"Translation error: {e}")
        stats['errors'] += 1
        return f"[Translation error]"


def translation_thread():
    """Translate Japanese text and send to web clients"""
    logger.info("Starting translation thread")
    
    latencies = []
    
    while not shutdown_event.is_set():
        try:
            item = text_queue.get(timeout=1)
            japanese_text = item['japanese']
            asr_time = item['asr_time']
            
            start_time = time.time()
            english_text = translate_japanese_to_english(japanese_text)
            translation_time = time.time() - start_time
            
            total_latency = asr_time + translation_time
            
            # Update stats
            stats['translations'] += 1
            latencies.append(total_latency * 1000)  # ms
            if len(latencies) > 50:
                latencies.pop(0)
            stats['avg_latency_ms'] = sum(latencies) / len(latencies)
            
            logger.info(f"[{total_latency:.2f}s] {japanese_text} → {english_text}")
            
            # Send to web clients
            if english_text:
                socketio.emit('subtitle', {
                    'japanese': japanese_text,
                    'english': english_text,
                    'latency': round(total_latency, 2),
                    'timestamp': time.time()
                })
                
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Translation thread error: {e}")
            stats['errors'] += 1

# =============================================================================
# WEB SERVER
# =============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'subtitle-secret-key-change-in-production')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# HTML Template (embedded for single-file deployment)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <title>🎌 Live Subtitles</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0f0f1a 100%);
            color: #fff;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            padding: 12px;
            padding-top: max(12px, env(safe-area-inset-top));
            padding-bottom: max(12px, env(safe-area-inset-bottom));
        }
        
        #header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 16px;
            background: rgba(0,0,0,0.4);
            border-radius: 12px;
            margin-bottom: 12px;
            backdrop-filter: blur(10px);
        }
        
        .status {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
        }
        
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #ff4444;
        }
        
        .status-dot.connected {
            background: #00ff88;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .controls {
            display: flex;
            gap: 8px;
        }
        
        button, select {
            padding: 8px 14px;
            border: none;
            border-radius: 8px;
            background: rgba(255,255,255,0.15);
            color: #fff;
            font-size: 14px;
            cursor: pointer;
            transition: background 0.2s;
        }
        
        button:hover, select:hover {
            background: rgba(255,255,255,0.25);
        }
        
        #subtitles {
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
            -webkit-overflow-scrolling: touch;
        }
        
        .subtitle {
            background: rgba(0,0,0,0.7);
            backdrop-filter: blur(10px);
            padding: 16px 20px;
            margin: 6px 0;
            border-radius: 12px;
            border-left: 4px solid #e74c3c;
            animation: slideIn 0.3s ease-out;
        }
        
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .japanese {
            font-size: 0.9em;
            color: #888;
            margin-bottom: 8px;
            font-family: 'Hiragino Sans', 'Yu Gothic', 'Noto Sans JP', sans-serif;
        }
        
        .english {
            font-size: 1.4em;
            font-weight: 600;
            line-height: 1.4;
        }
        
        .meta {
            font-size: 0.7em;
            color: #555;
            margin-top: 6px;
        }
        
        .size-small .english { font-size: 1.1em; }
        .size-medium .english { font-size: 1.4em; }
        .size-large .english { font-size: 1.8em; }
        .size-xlarge .english { font-size: 2.2em; }
        
        #empty {
            text-align: center;
            color: #444;
            padding: 60px 20px;
        }
        
        #empty .icon { font-size: 64px; margin-bottom: 20px; }
        
        #footer {
            text-align: center;
            font-size: 11px;
            color: #444;
            padding: 10px;
        }
    </style>
</head>
<body class="size-medium">
    <div id="header">
        <div class="status">
            <span class="status-dot" id="statusDot"></span>
            <span id="statusText">Connecting...</span>
        </div>
        <div class="controls">
            <select id="fontSize" onchange="setFontSize(this.value)">
                <option value="small">A</option>
                <option value="medium" selected>A+</option>
                <option value="large">A++</option>
                <option value="xlarge">A+++</option>
            </select>
            <button onclick="toggleJapanese()">日</button>
            <button onclick="clearAll()">✕</button>
        </div>
    </div>
    
    <div id="subtitles">
        <div id="empty">
            <div class="icon">🎌</div>
            <p><strong>Waiting for audio...</strong></p>
            <p style="font-size: 0.85em; margin-top: 8px;">Subtitles will appear when Japanese speech is detected</p>
        </div>
    </div>
    
    <div id="footer">
        Subtitles: <span id="count">0</span> | 
        Latency: <span id="latency">-</span>ms
    </div>

    <script>
        const socket = io();
        const subtitles = document.getElementById('subtitles');
        const empty = document.getElementById('empty');
        let count = 0;
        let showJapanese = true;
        let latencies = [];
        
        socket.on('connect', () => {
            document.getElementById('statusDot').classList.add('connected');
            document.getElementById('statusText').textContent = 'Connected';
        });
        
        socket.on('disconnect', () => {
            document.getElementById('statusDot').classList.remove('connected');
            document.getElementById('statusText').textContent = 'Disconnected';
        });
        
        socket.on('subtitle', (data) => {
            if (empty) empty.style.display = 'none';
            
            const div = document.createElement('div');
            div.className = 'subtitle';
            
            let html = '';
            if (showJapanese) {
                html += `<div class="japanese">${esc(data.japanese)}</div>`;
            }
            html += `<div class="english">${esc(data.english)}</div>`;
            html += `<div class="meta">${data.latency}s</div>`;
            
            div.innerHTML = html;
            subtitles.appendChild(div);
            
            count++;
            document.getElementById('count').textContent = count;
            
            latencies.push(data.latency * 1000);
            if (latencies.length > 20) latencies.shift();
            const avg = Math.round(latencies.reduce((a,b) => a+b, 0) / latencies.length);
            document.getElementById('latency').textContent = avg;
            
            subtitles.scrollTop = subtitles.scrollHeight;
            
            // Keep last 50
            while (subtitles.querySelectorAll('.subtitle').length > 50) {
                subtitles.querySelector('.subtitle').remove();
            }
        });
        
        function esc(s) {
            const d = document.createElement('div');
            d.textContent = s;
            return d.innerHTML;
        }
        
        function setFontSize(size) {
            document.body.className = 'size-' + size;
            localStorage.setItem('fontSize', size);
        }
        
        function toggleJapanese() {
            showJapanese = !showJapanese;
            document.querySelectorAll('.japanese').forEach(el => {
                el.style.display = showJapanese ? 'block' : 'none';
            });
        }
        
        function clearAll() {
            subtitles.querySelectorAll('.subtitle').forEach(el => el.remove());
            count = 0;
            latencies = [];
            document.getElementById('count').textContent = '0';
            document.getElementById('latency').textContent = '-';
            if (empty) empty.style.display = 'block';
        }
        
        // Restore preferences
        const saved = localStorage.getItem('fontSize');
        if (saved) {
            document.body.className = 'size-' + saved;
            document.getElementById('fontSize').value = saved;
        }
        
        // Keep screen awake
        if ('wakeLock' in navigator) {
            navigator.wakeLock.request('screen').catch(() => {});
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'uptime': str(datetime.now() - datetime.fromisoformat(stats['start_time'])),
        'stats': stats
    })

@app.route('/stats')
def get_stats():
    return jsonify(stats)

# =============================================================================
# MAIN
# =============================================================================

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, shutting down...")
    shutdown_event.set()


def get_local_ip():
    """Get local IP address for display"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return 'localhost'


def main():
    """Main entry point"""
    # Handle signals
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Print banner
    print("\n" + "=" * 60)
    print("  🎌 JAPANESE → ENGLISH REAL-TIME SUBTITLE SYSTEM")
    print("  Product Edition | Jetson Orin Nano SUPER")
    print("=" * 60)
    print(f"  Whisper Model:  {Config.WHISPER_MODEL}")
    print(f"  Audio Device:   {Config.AUDIO_DEVICE or 'default'}")
    print(f"  Web Port:       {Config.WEB_PORT}")
    print("=" * 60 + "\n")
    
    # Load models
    logger.info("Loading AI models...")
    
    if not load_whisper_model():
        logger.error("Failed to load Whisper model, exiting")
        sys.exit(1)
    
    if not load_translation_model():
        logger.error("Failed to load translation model, exiting")
        sys.exit(1)
    
    logger.info("All models loaded successfully")
    
    # Start processing threads
    threads = [
        threading.Thread(target=audio_capture_thread, name='AudioCapture', daemon=True),
        threading.Thread(target=transcription_thread, name='Transcription', daemon=True),
        threading.Thread(target=translation_thread, name='Translation', daemon=True),
    ]
    
    for t in threads:
        t.start()
        logger.info(f"Started thread: {t.name}")
    
    # Print access info
    local_ip = get_local_ip()
    print("\n" + "=" * 60)
    print("  ✓ SYSTEM READY")
    print("=" * 60)
    print(f"\n  Open in browser:\n")
    print(f"    👉  http://{local_ip}:{Config.WEB_PORT}")
    print(f"\n  Health check:")
    print(f"    curl http://localhost:{Config.WEB_PORT}/health")
    print("\n" + "=" * 60)
    print("  Press Ctrl+C to stop")
    print("=" * 60 + "\n")
    
    # Run web server
    try:
        socketio.run(
            app,
            host=Config.WEB_HOST,
            port=Config.WEB_PORT,
            debug=False,
            allow_unsafe_werkzeug=True
        )
    except Exception as e:
        logger.error(f"Web server error: {e}")
    finally:
        shutdown_event.set()
        logger.info("Shutdown complete")


if __name__ == '__main__':
    main()
PYTHON
```

### Create Docker Compose (Optional but Recommended)

```bash
cat > ~/subtitle-product/docker-compose.yml << 'YAML'
version: '3.8'

services:
  subtitle-server:
    build:
      context: .
      args:
        L4T_VERSION: r36.2.0  # CHANGE THIS to match your L4T version!
    container_name: subtitle-server
    runtime: nvidia
    restart: unless-stopped
    
    # Audio device access
    devices:
      - /dev/snd:/dev/snd
    
    # Required for ALSA
    group_add:
      - audio
    
    # Environment variables
    environment:
      - AUDIO_DEVICE=${AUDIO_DEVICE:-}
      - WHISPER_MODEL=${WHISPER_MODEL:-base}
      - WEB_PORT=5000
      - LOG_LEVEL=INFO
    
    # Port mapping
    ports:
      - "5000:5000"
    
    # Volume for logs (optional)
    volumes:
      - ./logs:/var/log
    
    # Health check
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s
YAML
```

---

## 8. Run and Test

### Step 1: Determine Your L4T Version

```bash
cat /etc/nv_tegra_release
# Note the version (e.g., R36 REVISION: 2.0 = r36.2)
```

### Step 2: Update Dockerfile/Compose with Your Version

Edit `~/subtitle-product/docker-compose.yml`:
```yaml
args:
  L4T_VERSION: r36.2.0  # Change to match your version
```

### Step 3: Find Audio Device

```bash
arecord -l
# Note the card number (e.g., card 1)
```

### Step 4: Build Container

```bash
cd ~/subtitle-product

# Build (first time takes 10-20 minutes)
docker compose build

# Or without compose:
# docker build --build-arg L4T_VERSION=r36.2.0 -t subtitle-server .
```

### Step 5: Run Container

```bash
# With docker compose (recommended)
AUDIO_DEVICE=1 docker compose up

# Or directly:
docker run --rm -it \
    --runtime=nvidia \
    --device /dev/snd \
    --group-add audio \
    -e AUDIO_DEVICE=1 \
    -p 5000:5000 \
    subtitle-server
```

### Step 6: Test

1. Open `http://[JETSON_IP]:5000` on your iPad/phone
2. Play Japanese audio through your HDMI source
3. Watch subtitles appear!

---

## 9. Production Deployment

### Auto-Start on Boot

```bash
# Create systemd service for docker compose
sudo tee /etc/systemd/system/subtitle-server.service << 'EOF'
[Unit]
Description=Japanese Subtitle Server
After=docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/home/YOUR_USERNAME/subtitle-product
Environment="AUDIO_DEVICE=1"
ExecStart=/usr/bin/docker compose up
ExecStop=/usr/bin/docker compose down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Replace YOUR_USERNAME
sudo sed -i "s/YOUR_USERNAME/$USER/g" /etc/systemd/system/subtitle-server.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable subtitle-server
sudo systemctl start subtitle-server

# Check status
sudo systemctl status subtitle-server
```

### View Logs

```bash
# Live logs
sudo journalctl -u subtitle-server -f

# Container logs
docker compose logs -f
```

### Update Container

```bash
cd ~/subtitle-product

# Pull new changes (if using git)
git pull

# Rebuild
docker compose build

# Restart
sudo systemctl restart subtitle-server
```

---

## 10. Commercial Packaging

### What You Sell

| Component | Source | Your Responsibility |
|-----------|--------|---------------------|
| Jetson Orin Nano | Buy from NVIDIA/distributor | Flash JetPack |
| Your Container | Your code | Build & install |
| Enclosure | Design/buy | Professional look |
| Cables & accessories | Source | Bundle together |
| Documentation | Write | User guide |
| Support | Provide | Email/phone |

### Licensing Considerations

| Component | License | Commercial Use |
|-----------|---------|----------------|
| JetPack/L4T | NVIDIA EULA | ✅ OK (don't redistribute OS image directly) |
| Docker | Apache 2.0 | ✅ OK |
| faster-whisper | MIT | ✅ OK (include license notice) |
| Whisper models | MIT | ✅ OK |
| NLLB | CC-BY-NC 4.0 | ⚠️ Check: May need commercial license |
| Your code | Your choice | You own it |

> ⚠️ **NLLB License**: The `nllb-200-distilled-600M` model is CC-BY-NC (non-commercial).
> For commercial use, consider:
> 1. Using **DeepL API** (pay per use)
> 2. Using **Whisper's translate mode** directly (skip separate translation)
> 3. Contacting Meta for commercial NLLB license

### Alternative: Whisper Direct Translation

For commercial safety, you can skip NLLB and use Whisper's built-in translation:

```python
# In transcription, use task='translate' instead of 'transcribe'
segments, info = whisper_model.transcribe(
    audio_chunk,
    language='ja',
    task='translate',  # Direct to English!
    beam_size=5
)
# Output is already English, no separate translation needed
```

This uses only MIT-licensed code.

### Suggested Retail Pricing

| Edition | Contents | Price |
|---------|----------|-------|
| **DIY License** | Software only (Docker image) | €99-149 |
| **Complete Device** | Jetson + software + cables + case | €599-799 |
| **Pro Bundle** | Complete + 1 year support + updates | €999 |

### Product Checklist

Before shipping to customers:

- [ ] Flash JetPack 6.1+ on Jetson
- [ ] Enable SUPER mode (nvpmodel -m 2)
- [ ] Install Docker + your container
- [ ] Configure auto-start service
- [ ] Test with actual HDMI audio
- [ ] Verify latency < 3 seconds
- [ ] Label enclosure with logo/brand
- [ ] Include quick start guide
- [ ] Package securely

---

## Quick Reference

### Essential Commands

```bash
# Check L4T version
cat /etc/nv_tegra_release

# Enable SUPER mode
sudo nvpmodel -m 2

# List audio devices
arecord -l

# Build container
cd ~/subtitle-product && docker compose build

# Run container
AUDIO_DEVICE=1 docker compose up

# View service logs
sudo journalctl -u subtitle-server -f

# Restart service
sudo systemctl restart subtitle-server
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AUDIO_DEVICE` | (default) | Audio device index or name |
| `WHISPER_MODEL` | `base` | tiny, base, small, medium |
| `WEB_PORT` | `5000` | Web server port |
| `LOG_LEVEL` | `INFO` | DEBUG, INFO, WARNING, ERROR |

### Troubleshooting

| Problem | Solution |
|---------|----------|
| "No GPU access in Docker" | Verify `--runtime=nvidia` and nvidia-container-toolkit |
| "Audio device not found" | Check `arecord -l`, verify device number |
| "High latency (>4s)" | Use smaller model, check SUPER mode |
| "Container won't start" | Check `docker logs subtitle-server` |
| "Web page not loading" | Check firewall, verify port 5000 |

---

## Summary

You now have a **commercial-grade** Japanese subtitle system that:

✅ Works for personal testing immediately  
✅ Is structured for commercial deployment  
✅ Uses Docker for reproducibility  
✅ Runs 100% offline  
✅ Auto-starts on boot  
✅ Has proper logging and health checks  
✅ Can be packaged and sold  

**Next steps:**
1. Flash JetPack and enable SUPER mode
2. Build and test the Docker container
3. Refine based on real-world testing
4. Design enclosure and packaging
5. Start selling!

---

*Last updated: December 2025*
*For Jetson Orin Nano SUPER with JetPack 6.1+*
