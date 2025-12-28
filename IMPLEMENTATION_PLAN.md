# Japanese TV Real-Time Subtitle System - Implementation Plan

## Project Understanding

### Objective
Build a **commercial-grade, offline, real-time** Japanese → English subtitle system that:
- Captures HDMI audio from Japanese TV content
- Transcribes Japanese speech using on-device AI
- Translates to English (using Whisper's direct translation)
- Displays subtitles via web interface on any device (iPad/phone/browser)
- Runs 100% offline with no cloud dependencies
- Is packageable as a commercial product

### Target Hardware
Based on `/home/vincent/JIFE/jetson-info.md`:

| Spec | Value |
|------|-------|
| Device | **Jetson Orin Nano SUPER** (on Yahboom carrier board) |
| JetPack | 6.2.1 (L4T r36.4.4) |
| Power Mode | **MAXN_SUPER** (confirmed active) |
| Memory | 7.4GB shared (CPU+GPU) |
| Storage | 233GB NVMe, 206GB free |
| CUDA | 12.6 |
| Audio Input | **WJK USB Audio** (card 2, `plughw:2,0`) |

### Key Decisions Made
1. **Translation:** Whisper direct `task='translate'` (MIT licensed, commercial-safe)
2. **Model Size:** `small` (244M params, ~2GB VRAM)
3. **ASR Engine:** WhisperTRT (3x faster than PyTorch Whisper)

---

## Implementation Progress

### ✅ Phase 1: Environment Setup & Validation (COMPLETE)
- [x] SUPER mode active and persistent (`pmode:0002` saved)
- [x] Docker 29.1.3 installed with nvidia runtime
- [x] GPU access tested via `l4t-jetpack:r36.4.0` container
- [x] USB audio device working (`WJK USB Audio`, `plughw:2,0`)
- [x] Project directory structure created
- [x] jetson-containers utilities installed

### 🔄 Phase 2: WhisperTRT Integration (IN PROGRESS)
- [x] Research completed - using dusty-nv/jetson-containers approach
- [x] jetson-containers cloned and installed
- [🔄] Building whisper_trt container (13 stages, currently on CUDA stage)
- [ ] Test with sample Japanese audio
- [ ] Benchmark latency and memory

### ✅ Phase 3: Audio Capture Pipeline (COMPLETE)
- [x] `app/audio/capture.py` - ALSA audio capture with sounddevice
- [x] Queue-based chunk delivery
- [x] Silence detection
- [x] Configurable device, sample rate, chunk duration

### ✅ Phase 4: Web Interface (COMPLETE)
- [x] `app/web/server.py` - Flask + Flask-SocketIO
- [x] `app/web/templates/index.html` - Responsive subtitle display
- [x] WebSocket real-time subtitle push
- [x] Font size controls, Japanese text toggle
- [x] Wake Lock API for mobile
- [x] Health check endpoint

### 📝 Phase 5: Integration & Optimization (PENDING)
- [x] `app/main.py` - Main entry point tying everything together
- [x] `app/config.py` - Configuration management
- [x] `app/asr/whisper_engine.py` - Multi-backend ASR wrapper
- [ ] End-to-end testing with real audio
- [ ] Latency profiling and optimization

### 📝 Phase 6: Production Hardening (PENDING)
- [x] `Dockerfile` - Production container build
- [x] `docker-compose.yml` - Orchestration
- [x] `requirements.txt` - Python dependencies
- [x] `scripts/run.sh` - Helper script
- [ ] systemd service for auto-start
- [ ] User documentation

---

## Project Structure (Created)

```
~/JIFE/subtitle-product/
├── Dockerfile                 # ✅ Container build
├── docker-compose.yml         # ✅ Orchestration
├── requirements.txt           # ✅ Python dependencies
├── app/
│   ├── __init__.py           # ✅ Package init
│   ├── main.py               # ✅ Entry point
│   ├── config.py             # ✅ Configuration
│   ├── audio/
│   │   ├── __init__.py       # ✅
│   │   └── capture.py        # ✅ ALSA audio capture
│   ├── asr/
│   │   ├── __init__.py       # ✅
│   │   └── whisper_engine.py # ✅ WhisperTRT wrapper
│   └── web/
│       ├── __init__.py       # ✅
│       ├── server.py         # ✅ Flask + SocketIO
│       └── templates/
│           └── index.html    # ✅ Subtitle display page
├── scripts/
│   └── run.sh                # ✅ Helper script
├── models/                    # (populated at build time)
├── logs/                      # (runtime logs)
└── docs/                      # (pending)
```

---

## Current Status

**Container Build:** Running in background (task b9f0752)
- Stage 3/13 (CUDA) - Installing CUDA development libraries
- Estimated remaining time: 20-40 minutes

**Next Steps:**
1. Wait for container build to complete
2. Test whisper_trt with sample Japanese audio
3. Run end-to-end test with HDMI audio source
4. Profile and optimize latency

---

## Quick Start (Once Build Complete)

```bash
cd ~/JIFE/subtitle-product

# Build the container (if not using pre-built whisper_trt)
docker-compose build

# Run the system
AUDIO_DEVICE=plughw:2,0 docker-compose up

# Or with jetson-containers whisper_trt:
jetson-containers run $(autotag whisper_trt)
```

Open `http://[JETSON_IP]:5000` on your iPad/phone to see subtitles.

---

## Sources Used

- [NVIDIA-AI-IOT/whisper_trt](https://github.com/NVIDIA-AI-IOT/whisper_trt)
- [dusty-nv/jetson-containers](https://github.com/dusty-nv/jetson-containers)
- [OpenAI Whisper](https://github.com/openai/whisper)
- [JetPack 6.2 Super Mode](https://developer.nvidia.com/blog/nvidia-jetpack-6-2-brings-super-mode-to-nvidia-jetson-orin-nano-and-jetson-orin-nx-modules/)
- [PyTorch for Jetson](https://docs.nvidia.com/deeplearning/frameworks/install-pytorch-jetson-platform/index.html)

---

*Last updated: December 23, 2025*
