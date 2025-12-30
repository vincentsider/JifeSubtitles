# JIFE Cloud Edition - Raspberry Pi + Groq API

A lightweight, sellable product version using Raspberry Pi for audio capture and Groq's cloud API for transcription/translation.

---

## Overview

| Aspect | Value |
|--------|-------|
| Hardware | Raspberry Pi 5 (4GB or 8GB) |
| Cloud API | Groq (whisper-large-v3) |
| Expected Latency | 1.5 - 2.5 seconds |
| Cost per hour | $0.111 (Groq API) |
| Monthly cost (3hr/day) | ~$10 |
| Internet Required | Yes |

---

## Architecture

```
HDMI Source (TV, Streaming Box)
       |
       v
  HDMI Audio Extractor
       |
       +---> HDMI OUT ---> TV (video)
       |
       +---> 3.5mm out ---> USB Audio Adapter ---> Raspberry Pi 5
                                                        |
                                              [Capture 1-2s audio chunks]
                                                        |
                                              [Send to Groq API via internet]
                                                        |
                                              [Receive English translation]
                                                        |
                                              [Serve to iPad/Phone]
                                                        |
                                                http://PI_IP:5000
```

---

## Bill of Materials (Product Cost)

| Item | Cost | Source |
|------|------|--------|
| Raspberry Pi 5 (4GB) | $60 | Official reseller |
| HDMI Audio Extractor | $15-30 | Amazon |
| USB Sound Card | $10 | Amazon |
| Power Supply (Pi) | $15 | Official |
| SD Card (32GB) | $10 | Any |
| Case (optional) | $10 | Any |
| **Total** | **~$120-135** | |

**Suggested retail price**: $199-249 + $15-25/month subscription

---

## Product Business Model

### Subscription Tiers

| Tier | Price | Included Hours | API Cost | Your Margin |
|------|-------|----------------|----------|-------------|
| Basic | $15/month | 50 hrs | $5.55 | $9.45 (63%) |
| Standard | $25/month | 100 hrs | $11.10 | $13.90 (56%) |
| Premium | $40/month | Unlimited* | ~$20 | $20 (50%) |

*Unlimited = fair use ~180 hrs/month

---

## Implementation Plan

### Phase 1: Setup Raspberry Pi (Day 1)

#### 1.1 Flash OS

1. Download Raspberry Pi OS Lite (64-bit) - no desktop needed
2. Use Raspberry Pi Imager to flash SD card
3. Enable SSH in imager settings
4. Configure WiFi in imager settings

#### 1.2 Initial Setup

```bash
# SSH into Pi
ssh pi@raspberrypi.local

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y \
    python3-pip \
    python3-venv \
    git \
    docker.io \
    docker-compose \
    alsa-utils

# Add user to docker group
sudo usermod -aG docker $USER
sudo usermod -aG audio $USER

# Reboot
sudo reboot
```

#### 1.3 Verify Audio

```bash
# List audio devices
arecord -l

# Test recording (replace X with card number)
arecord -D plughw:X,0 -f S16_LE -r 16000 -c 1 -d 5 test.wav
aplay test.wav
```

---

### Phase 2: Project Structure (Day 1-2)

```
jife-cloud/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── app/
│   ├── __init__.py
│   ├── main.py                    # Entry point
│   ├── config.py                  # Configuration
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── capture.py             # Audio capture (reuse from Jetson)
│   │   └── buffer.py              # Audio chunking for API
│   ├── transcription/
│   │   ├── __init__.py
│   │   ├── base.py                # Abstract base class
│   │   └── groq_client.py         # Groq Whisper API client
│   └── web/
│       ├── __init__.py
│       ├── server.py              # Flask server (reuse from Jetson)
│       └── templates/
│           └── index.html         # Subtitle display (reuse from Jetson)
└── README.md
```

---

### Phase 3: Core Components (Day 2-3)

#### 3.1 Groq API Client

```python
# app/transcription/groq_client.py

import io
import wave
import logging
from groq import Groq

logger = logging.getLogger(__name__)


class GroqWhisperClient:
    """
    Client for Groq's Whisper API with Japanese -> English translation.

    Pricing: $0.111/hour of audio
    Speed: ~299x real-time
    Model: whisper-large-v3 (supports translation)
    """

    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
        self.model = "whisper-large-v3"

    def transcribe_and_translate(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        source_language: str = "ja"
    ) -> str:
        """
        Send audio to Groq Whisper API and get English translation.

        Args:
            audio_data: Raw PCM audio bytes (16-bit, mono)
            sample_rate: Audio sample rate (default 16000)
            source_language: Source language code (default "ja" for Japanese)

        Returns:
            Translated English text
        """
        # Convert raw PCM to WAV format
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)          # Mono
            wav_file.setsampwidth(2)          # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data)

        wav_buffer.seek(0)
        wav_buffer.name = "audio.wav"  # Groq needs a filename

        try:
            # Use translations endpoint for Japanese -> English
            response = self.client.audio.translations.create(
                model=self.model,
                file=wav_buffer,
                response_format="text"
            )

            result = response.strip() if response else ""
            logger.debug(f"Groq translation: {result[:50]}...")
            return result

        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise
```

#### 3.2 Audio Buffer with Chunking

```python
# app/audio/buffer.py

import threading
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class AudioBuffer:
    """
    Collects audio samples and triggers API calls at optimal intervals.

    For Groq with ~0.5s API latency:
    - chunk_duration=2.0s gives ~2.5s total latency (recommended)
    - chunk_duration=1.0s gives ~1.5s total latency (more API calls)
    """

    def __init__(
        self,
        chunk_duration: float = 2.0,
        sample_rate: int = 16000,
        on_chunk_ready: Optional[Callable[[bytes], None]] = None
    ):
        self.chunk_duration = chunk_duration
        self.sample_rate = sample_rate
        self.bytes_per_sample = 2  # 16-bit audio
        self.bytes_per_chunk = int(
            chunk_duration * sample_rate * self.bytes_per_sample
        )
        self.on_chunk_ready = on_chunk_ready

        self.buffer = bytearray()
        self.lock = threading.Lock()

        logger.info(
            f"AudioBuffer initialized: {chunk_duration}s chunks, "
            f"{self.bytes_per_chunk} bytes each"
        )

    def add_audio(self, data: bytes):
        """Add audio data to buffer. Triggers callback when chunk is ready."""
        with self.lock:
            self.buffer.extend(data)

            # Process complete chunks
            while len(self.buffer) >= self.bytes_per_chunk:
                chunk = bytes(self.buffer[:self.bytes_per_chunk])
                self.buffer = self.buffer[self.bytes_per_chunk:]

                if self.on_chunk_ready:
                    # Process in separate thread to not block capture
                    threading.Thread(
                        target=self._safe_callback,
                        args=(chunk,),
                        daemon=True
                    ).start()

    def _safe_callback(self, chunk: bytes):
        """Wrapper to catch exceptions in callback."""
        try:
            self.on_chunk_ready(chunk)
        except Exception as e:
            logger.error(f"Chunk processing error: {e}")

    def flush(self) -> Optional[bytes]:
        """Return any remaining audio in buffer."""
        with self.lock:
            if len(self.buffer) > 0:
                chunk = bytes(self.buffer)
                self.buffer = bytearray()
                return chunk
        return None
```

#### 3.3 Main Application

```python
# app/main.py

import os
import sys
import time
import logging
import signal
import threading

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import Config
from app.audio.capture import AudioCapture  # Reuse from Jetson
from app.audio.buffer import AudioBuffer
from app.transcription.groq_client import GroqWhisperClient
from app.web.server import SubtitleServer  # Reuse from Jetson

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger('jife-cloud')


class JIFECloud:
    """
    JIFE Cloud Edition - Raspberry Pi + Groq API

    Captures audio locally, sends to Groq for translation,
    displays subtitles on web interface.
    """

    def __init__(self):
        self.config = Config()
        self.shutdown_event = threading.Event()

        # Validate API key
        if not self.config.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY environment variable required")

        # Initialize components
        logger.info("Initializing JIFE Cloud...")

        self.groq_client = GroqWhisperClient(self.config.GROQ_API_KEY)

        self.web_server = SubtitleServer(
            host='0.0.0.0',
            port=self.config.WEB_PORT
        )

        self.audio_buffer = AudioBuffer(
            chunk_duration=self.config.CHUNK_DURATION,
            sample_rate=self.config.SAMPLE_RATE,
            on_chunk_ready=self.process_audio_chunk
        )

        self.audio_capture = AudioCapture(
            device=self.config.AUDIO_DEVICE,
            sample_rate=self.config.SAMPLE_RATE,
            channels=1,
            chunk_duration=0.1,  # Small chunks for smooth capture
            output_queue=None,  # We use callback instead
        )

        # Wire up audio capture to buffer
        self.audio_capture.set_callback(self.audio_buffer.add_audio)

        # Stats
        self.chunks_processed = 0
        self.total_audio_seconds = 0

    def process_audio_chunk(self, audio_data: bytes):
        """Called when we have enough audio to send to API."""
        chunk_duration = len(audio_data) / (self.config.SAMPLE_RATE * 2)
        self.total_audio_seconds += chunk_duration
        self.chunks_processed += 1

        logger.info(
            f"Processing chunk #{self.chunks_processed} "
            f"({chunk_duration:.1f}s, total: {self.total_audio_seconds:.0f}s)"
        )

        try:
            start_time = time.time()

            # Get translation from Groq
            translation = self.groq_client.transcribe_and_translate(
                audio_data,
                sample_rate=self.config.SAMPLE_RATE
            )

            api_time = time.time() - start_time

            if translation and len(translation.strip()) > 1:
                logger.info(f"[{api_time:.2f}s] {translation[:80]}")
                self.web_server.send_subtitle(
                    text=translation,
                    source_text='',
                    latency_sec=api_time,
                    metadata={'provider': 'groq'}
                )
            else:
                logger.debug(f"Empty translation (API time: {api_time:.2f}s)")

        except Exception as e:
            logger.error(f"Translation error: {e}")

    def start(self):
        """Start all components."""
        logger.info("Starting JIFE Cloud Edition...")

        # Start web server
        self.web_server.run_threaded()

        # Start audio capture
        self.audio_capture.start()

        # Print access info
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            s.close()
        except:
            local_ip = 'localhost'

        print("\n" + "=" * 60)
        print("  JIFE CLOUD EDITION - READY")
        print("=" * 60)
        print(f"\n  Open in browser:")
        print(f"    http://{local_ip}:{self.config.WEB_PORT}")
        print(f"\n  Audio device: {self.config.AUDIO_DEVICE}")
        print(f"  Chunk duration: {self.config.CHUNK_DURATION}s")
        print(f"  API: Groq whisper-large-v3")
        print("\n" + "=" * 60)
        print("  Press Ctrl+C to stop")
        print("=" * 60 + "\n")

        # Main loop
        try:
            while not self.shutdown_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            pass

        self.stop()

    def stop(self):
        """Stop all components."""
        logger.info("Shutting down...")
        self.shutdown_event.set()
        self.audio_capture.stop()

        # Log stats
        if self.total_audio_seconds > 0:
            cost = self.total_audio_seconds / 3600 * 0.111
            logger.info(
                f"Session stats: {self.chunks_processed} chunks, "
                f"{self.total_audio_seconds:.0f}s audio, "
                f"~${cost:.3f} API cost"
            )

        logger.info("Shutdown complete")


def main():
    signal.signal(signal.SIGINT, lambda s, f: None)
    signal.signal(signal.SIGTERM, lambda s, f: None)

    app = JIFECloud()
    app.start()


if __name__ == "__main__":
    main()
```

#### 3.4 Configuration

```python
# app/config.py

import os


class Config:
    """Configuration for JIFE Cloud Edition."""

    # Groq API
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

    # Audio capture
    AUDIO_DEVICE = os.environ.get('AUDIO_DEVICE', 'plughw:1,0')
    SAMPLE_RATE = int(os.environ.get('SAMPLE_RATE', 16000))

    # Chunking - trade-off between latency and API calls
    # 2.0s = ~2.5s latency, fewer API calls
    # 1.0s = ~1.5s latency, more API calls (2x cost)
    CHUNK_DURATION = float(os.environ.get('CHUNK_DURATION', '2.0'))

    # Web server
    WEB_PORT = int(os.environ.get('WEB_PORT', 5000))

    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
```

---

### Phase 4: Docker Setup (Day 3)

#### 4.1 Dockerfile

```dockerfile
# Dockerfile for JIFE Cloud (Raspberry Pi / ARM64)

FROM python:3.11-slim-bookworm

# Install audio dependencies
RUN apt-get update && apt-get install -y \
    alsa-utils \
    libasound2-dev \
    libportaudio2 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "app.main"]
```

#### 4.2 requirements.txt

```
groq>=0.4.0
flask>=3.0.0
flask-socketio>=5.3.0
pyaudio>=0.2.14
numpy>=1.24.0
```

#### 4.3 docker-compose.yml

```yaml
# JIFE Cloud Edition - Raspberry Pi + Groq API

services:
  jife-cloud:
    build: .
    container_name: jife-cloud
    restart: unless-stopped

    ports:
      - "5000:5000"

    devices:
      - /dev/snd:/dev/snd

    group_add:
      - audio

    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
      - AUDIO_DEVICE=${AUDIO_DEVICE:-plughw:1,0}
      - CHUNK_DURATION=${CHUNK_DURATION:-2.0}
      - WEB_PORT=5000
      - LOG_LEVEL=INFO

    # Health check
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

#### 4.4 .env.example

```bash
# Groq API key (required)
# Get from: https://console.groq.com/keys
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx

# Audio device (find with: arecord -l)
AUDIO_DEVICE=plughw:1,0

# Chunk duration in seconds
# Lower = less latency, more API calls
# Higher = more latency, fewer API calls
CHUNK_DURATION=2.0
```

---

### Phase 5: Deploy and Test (Day 4)

#### 5.1 Get Groq API Key

1. Go to https://console.groq.com/
2. Sign up / Log in
3. Go to API Keys
4. Create new key
5. Copy to `.env` file

#### 5.2 Deploy

```bash
# Clone repo on Pi
git clone https://github.com/vincentsider/JifeSubtitles.git
cd JifeSubtitles/jife-cloud

# Create .env
cp .env.example .env
nano .env  # Add your GROQ_API_KEY

# Build and run
docker compose up --build -d

# Check logs
docker logs jife-cloud -f
```

#### 5.3 Test

1. Connect HDMI audio extractor + USB audio adapter
2. Play Japanese content
3. Open http://PI_IP:5000 on iPad/phone
4. Watch subtitles appear!

---

## Latency Tuning

| CHUNK_DURATION | Total Latency | API Calls/min | Monthly Cost (3hr/day) |
|----------------|---------------|---------------|------------------------|
| 1.0s | ~1.5s | 60 | $10 |
| 2.0s | ~2.5s | 30 | $10 |
| 3.0s | ~3.5s | 20 | $10 |
| 5.0s | ~5.5s | 12 | $10 |

**Note**: Cost is the same regardless of chunk size (billed by audio duration, not API calls).

Recommended: Start with `CHUNK_DURATION=2.0`, reduce to 1.0 if latency is critical.

---

## Files to Reuse from Jetson Version

| File | Reuse? | Notes |
|------|--------|-------|
| `app/audio/capture.py` | Yes | Audio capture code works the same |
| `app/web/server.py` | Yes | Flask server unchanged |
| `app/web/templates/index.html` | Yes | Subtitle UI unchanged |
| `app/asr/whisper_engine.py` | No | Replace with Groq client |

---

## Comparison: Jetson vs Pi Cloud

| Aspect | Jetson Orin Nano | Pi 5 + Groq |
|--------|------------------|-------------|
| Hardware cost | ~$250 | ~$120 |
| Monthly cost | $0 | ~$10 |
| Latency | 3-5s (large-v3) | 1.5-2.5s |
| Internet required | No | Yes |
| Privacy | Full (local) | Audio sent to Groq |
| Quality | Good (int8) | Best (large-v3 fp16) |
| Complexity | High (CUDA/JetPack) | Low |

**Use Jetson when**: Offline operation required, privacy critical
**Use Pi Cloud when**: Best quality needed, internet available, selling as product

---

## Product Packaging Checklist

- [ ] Raspberry Pi 5 (4GB)
- [ ] Official power supply
- [ ] 32GB SD card with OS pre-installed
- [ ] HDMI audio extractor
- [ ] USB sound card (if needed)
- [ ] 3.5mm audio cable
- [ ] Quick start guide (printed)
- [ ] Subscription activation card

---

*Document created: December 30, 2025*
