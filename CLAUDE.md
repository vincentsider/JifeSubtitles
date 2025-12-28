# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current Status: ✅ SYSTEM IS COMPLETE AND OPERATIONAL

**READ FIRST:** See `/home/vincent/JIFE/subtitle-product/docs/STATUS.md` for:
- Current system status and configuration
- Troubleshooting guide
- Service commands
- What was built and how it works

**Quick facts:**
- Jetson IP: `192.168.1.34`
- Subtitle URL: `http://192.168.1.34:5000`
- Auto-start service: `jife-subtitles` (systemd)
- Audio device: `hw:2,0` (WJK USB Audio)
- Container: `whisper_trt:r36.4.tegra-aarch64-cu126-22.04-whisper_trt`

---

## Project Overview

**JIFE** (Japanese In-Flight Entertainment) is a Japanese → English real-time subtitle system for Jetson Orin NX/Nano. It captures HDMI audio from Japanese TV content, transcribes and translates speech using on-device AI, and displays English subtitles via a web interface on any device (iPad/phone/browser).

Key characteristics:
- Runs 100% offline with no cloud dependencies
- Docker-based deployment using NGC L4T base images
- Commercial-grade with licensing-safe models only
- Target latency: < 3-4 seconds from speech to subtitle

## Hardware Environment

- **Device:** NVIDIA Jetson Orin NX (7.4GB shared memory)
- **JetPack:** 6.2.1 (L4T r36.4.4)
- **Power Mode:** MAXN_SUPER (up to 157 TOPS)
- **Storage:** NVMe SSD (~206GB free)
- **Audio:** USB audio adapter connected to HDMI audio extractor

## Architecture

```
HDMI Source → HDMI Splitter → HDMI Audio Extractor → USB Audio Adapter → Jetson
                          ↓
              Docker Container:
              - Audio Capture (ALSA/sounddevice)
              - WhisperTRT (Japanese ASR/translation)
              - Flask + WebSocket server
                          ↓
              iPad/Phone Browser (subtitle display)
```

## Key Technical Decisions

1. **ASR Engine:** WhisperTRT (NVIDIA TensorRT optimized) instead of faster-whisper due to CUDA compatibility issues on JetPack 6.x

2. **Translation:** Whisper direct translation (`task='translate'`) - outputs English directly from Japanese speech. This is 100% MIT licensed and avoids NLLB's CC-BY-NC restrictions.

3. **Model Size:** `small` (244M params, ~2GB VRAM) - best accuracy/memory balance for Japanese on 7.4GB shared memory

4. **PyTorch:** Must use NVIDIA's Jetson-specific wheels:
   ```bash
   pip install torch torchvision --index-url=https://pypi.jetson-ai-lab.io/jp6/cu126
   ```

5. **Docker Base Image:** `nvcr.io/nvidia/l4t-base:r36.4.0` (matches L4T r36.4.4)

## Development Commands

### System Verification
```bash
# Check power mode (should show MAXN_SUPER)
sudo nvpmodel -q

# Check L4T version
cat /etc/nv_tegra_release

# List audio capture devices
arecord -l

# Test audio recording (replace hw:X,0 with actual device)
arecord -D hw:1,0 -f S16_LE -r 16000 -c 1 -d 5 /tmp/test.wav
```

### Docker Operations
```bash
# Build container (from project root)
docker compose build

# Run with audio device (replace device number as needed)
AUDIO_DEVICE=1 docker compose up

# Test GPU access in container
docker run --rm --runtime=nvidia nvcr.io/nvidia/l4t-base:r36.4.0 cat /etc/nv_tegra_release

# View container logs
docker compose logs -f
```

### Service Management
```bash
# Start/stop/restart the systemd service
sudo systemctl start jife-subtitles
sudo systemctl stop jife-subtitles
sudo systemctl restart jife-subtitles

# View service logs
sudo journalctl -u jife-subtitles -f

# Check service status
sudo systemctl status jife-subtitles
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AUDIO_DEVICE` | (system default) | Audio device index or name |
| `WHISPER_MODEL` | `base` | Model size: tiny, base, small, medium |
| `WEB_PORT` | `5000` | Web server port |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

## Licensing Constraints

- **Must avoid:** NLLB models (CC-BY-NC, non-commercial)
- **Safe to use:** Whisper models (MIT), WhisperTRT (MIT/Apache), PyTorch (BSD)
- Models must be pre-downloaded during Docker build - no runtime downloads for end users

## MCP Integration

This project uses **in-memoria** MCP server for persistent project memory across Claude sessions (configured in `.mcp.json`).
