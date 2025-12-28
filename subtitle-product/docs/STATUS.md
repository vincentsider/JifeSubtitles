# JIFE Subtitle System - Status & Troubleshooting Guide

**Last Updated:** December 26, 2025

## Current Status: ✅ FULLY OPERATIONAL

The Japanese → English real-time subtitle system is complete and configured to auto-start on boot.

---

## System Overview

| Component | Status | Details |
|-----------|--------|---------|
| **Whisper Container** | ✅ Built | `whisper_trt:r36.4.tegra-aarch64-cu126-22.04-whisper_trt` (29GB) |
| **ASR Engine** | ✅ Working | Standard Whisper `small` model (WhisperTRT doesn't support `small`) |
| **Audio Capture** | ✅ Working | USB device hw:2,0 @ 48kHz → resampled to 16kHz |
| **Web Interface** | ✅ Working | TV-style centered subtitles, large font for distance viewing |
| **Auto-start** | ✅ Enabled | systemd service `jife-subtitles` |

---

## Quick Reference

| Item | Value |
|------|-------|
| **Jetson IP** | `192.168.1.34` |
| **Subtitle URL** | `http://192.168.1.34:5000` |
| **Audio Device** | `hw:2,0` (WJK USB Audio) |
| **Whisper Model** | `small` (best for Japanese) |
| **Expected Latency** | 2-4 seconds |

---

## How It Works

```
HDMI Source → HDMI Audio Extractor → USB Audio Adapter (hw:2,0)
                                            ↓
                                      Jetson Orin NX
                                            ↓
                              Docker Container (whisper_trt)
                              - Audio capture @ 48kHz
                              - Resample to 16kHz
                              - Whisper transcribe (ja→en)
                              - Flask + WebSocket server
                                            ↓
                              iPad/Phone Browser @ port 5000
                              (TV-style centered subtitles)
```

---

## Auto-Start Configuration

The system uses a systemd service that starts automatically on boot:

**Service file:** `/etc/systemd/system/jife-subtitles.service`

```ini
[Unit]
Description=JIFE Japanese Subtitle System
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/home/vincent/JIFE/subtitle-product
Environment=AUDIO_DEVICE=plughw:2,0
ExecStart=/usr/bin/docker compose up
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Troubleshooting

### 1. Can't Access Web Page (http://192.168.1.34:5000)

**Check if service is running:**
```bash
sudo systemctl status jife-subtitles
```

**Check if container is running:**
```bash
sudo docker ps | grep subtitle
```

**View service logs:**
```bash
sudo journalctl -u jife-subtitles -f
```

**Restart the service:**
```bash
sudo systemctl restart jife-subtitles
```

**Wait 2 minutes** - the container needs to install dependencies on first start.

### 2. IP Address Changed

**Find current IP:**
```bash
ip route get 1 | awk '{print $7; exit}'
```

Or check your router's DHCP client list.

### 3. No Subtitles Appearing

**Check if audio device exists:**
```bash
arecord -l
```
Look for "WJK USB Audio" or similar. Note the card number.

**Test audio recording:**
```bash
arecord -D hw:2,0 -f S16_LE -r 48000 -c 1 -d 5 /tmp/test.wav
aplay /tmp/test.wav
```

**If card number changed**, update the service:
```bash
sudo systemctl stop jife-subtitles
# Edit /home/vincent/JIFE/subtitle-product/docker-compose.yml
# Change AUDIO_DEVICE=plughw:X,0 to correct card number
sudo systemctl start jife-subtitles
```

### 4. "Thank you for watching" Hallucinations

This happens when Whisper receives near-silence. The RMS threshold is set to 0.02 to filter most noise. If still happening:

- Check that actual audio is flowing (test with arecord)
- Increase threshold in `/home/vincent/JIFE/subtitle-product/app/audio/capture.py` line 86

### 5. Container Won't Start

**Check Docker:**
```bash
sudo systemctl status docker
sudo docker images | grep whisper_trt
```

**Manual start for debugging:**
```bash
cd /home/vincent/JIFE/subtitle-product
sudo docker compose up
```

### 6. Health Check

**Quick health check:**
```bash
curl http://localhost:5000/health
```

Expected response:
```json
{"status":"ok","uptime_seconds":123,"stats":{...}}
```

---

## Key Files

| File | Purpose |
|------|---------|
| `/home/vincent/JIFE/subtitle-product/docker-compose.yml` | Container configuration |
| `/home/vincent/JIFE/subtitle-product/app/main.py` | Main application entry |
| `/home/vincent/JIFE/subtitle-product/app/audio/capture.py` | Audio capture (48kHz→16kHz) |
| `/home/vincent/JIFE/subtitle-product/app/asr/whisper_engine.py` | Whisper integration |
| `/home/vincent/JIFE/subtitle-product/app/web/templates/index.html` | Subtitle UI (TV-style) |
| `/etc/systemd/system/jife-subtitles.service` | Auto-start service |

---

## Service Commands

```bash
# Check status
sudo systemctl status jife-subtitles

# Start
sudo systemctl start jife-subtitles

# Stop
sudo systemctl stop jife-subtitles

# Restart
sudo systemctl restart jife-subtitles

# View logs (live)
sudo journalctl -u jife-subtitles -f

# View recent logs
sudo journalctl -u jife-subtitles --since "10 minutes ago"

# Disable auto-start
sudo systemctl disable jife-subtitles

# Re-enable auto-start
sudo systemctl enable jife-subtitles
```

---

## Testing with Sample Audio

To test without HDMI source:

```bash
# Stop the live service first
sudo systemctl stop jife-subtitles

# Run demo with Japanese audio file
sudo docker run --rm --runtime=nvidia \
  --name subtitle-demo \
  -p 5000:5000 \
  --volume /home/vincent/JIFE:/data \
  --volume /home/vincent/JIFE/models/whisper:/root/.cache/whisper \
  whisper_trt:r36.4.tegra-aarch64-cu126-22.04-whisper_trt \
  bash -c "pip install flask flask-socketio scipy sounddevice -q && \
           python3 /data/subtitle-product/play_demo.py"

# Then open http://192.168.1.34:5000 on your iPad
```

---

## Build Information

The whisper_trt container was built using jetson-containers with several fixes:

1. **TensorRT 10.3** - Downloaded and installed manually (wasn't available in base image)
2. **NVIDIA libs** - Copied 129 .so files from host for TensorRT to work at build time
3. **ONNXRUNTIME** - Built with `--parallel 2` to avoid OOM on 7.4GB RAM
4. **whisper_trt** - Installed with `--no-build-isolation` to find whisper module

Build took ~20 hours total across multiple sessions.

---

## What Claude Code Should Know

If starting a new session:

1. **The system is complete and working** - no need to rebuild anything
2. **Auto-start is configured** - `jife-subtitles` systemd service
3. **IP address is 192.168.1.34** - user accesses via iPad browser
4. **Audio device is hw:2,0** - USB audio adapter at 48kHz
5. **Whisper model is `small`** - best accuracy for Japanese on this hardware
6. **WhisperTRT doesn't support `small`** - falls back to standard Whisper
7. **UI is TV-style** - large centered text, single subtitle at a time

Common tasks:
- Troubleshooting audio issues → check `arecord -l`
- Viewing logs → `sudo journalctl -u jife-subtitles -f`
- Testing → use `play_demo.py` with the Japanese MP3 file
