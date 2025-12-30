# JIFE Setup Guide - Japanese In-Flight Entertainment

Complete step-by-step guide to run real-time Japanese -> English subtitles on your Jetson.

---

## Prerequisites

Before starting, ensure you have:
- Jetson Orin Nano/NX with JetPack 6.x installed (NOT JetPack 7.x)
- USB audio adapter with microphone INPUT (pink jack) - NOT output-only adapters
- HDMI audio extractor
- 3.5mm audio cable
- iPad/phone/computer on the same network as the Jetson

---

## Quick Start (New Jetson)

If setting up a new Jetson from scratch, see [NEW_JETSON_SETUP.md](../../NEW_JETSON_SETUP.md) for the fastest path.

---

## Step 1: Verify Hardware Setup

### 1.1 Check Audio Device

```bash
arecord -l
```

Look for your USB audio adapter. Example output:
```
card 2: Audio [WJK USB Audio], device 0: USB Audio [USB Audio]
```

**Note your card number** (e.g., `2` in this example).

### 1.2 Test Audio Recording

```bash
# Replace hw:2,0 with your card number
arecord -D hw:2,0 -f S16_LE -r 16000 -c 1 -d 5 /tmp/test.wav

# Play it back (optional, if you have speakers)
aplay /tmp/test.wav
```

If you hear/see audio recorded, your hardware is working.

### 1.3 Find Your Jetson's IP Address

```bash
hostname -I
```

**Write down this IP** (e.g., `192.168.1.34`). You'll need it for your iPad/phone.

---

## Step 2: Start the Subtitle System

### 2.1 Start the Service

```bash
cd /home/vincent/JIFE/subtitle-product

# Start the service
docker compose up -d

# View logs
docker logs subtitle-server -f
```

### 2.2 Verify Server is Running

You should see output like:
```
JAPANESE -> ENGLISH REAL-TIME SUBTITLE SYSTEM
Whisper Model:  large-v3
Whisper Backend:faster_whisper
Loading Whisper model (faster_whisper/large-v3)...
Whisper model loaded successfully
SYSTEM READY
```

---

## Step 3: Access Subtitles on Your iPad/Phone

### 3.1 Open the Subtitle Page

On your iPad/iPhone/Android/Computer, open Chrome (or Safari) and go to:

```
http://192.168.1.34:5000
```

**Replace `192.168.1.34` with your Jetson's IP from Step 1.3**

### 3.2 Subtitle Display Features

The web interface provides:
- **Large, readable subtitles** optimized for viewing
- **Font size controls** (+ and - buttons)
- **Model switching** - change Whisper model without restart
- **Auto-reconnect** if connection drops
- **Screen wake lock** (keeps your iPad screen on)

### 3.3 Available Models

You can switch models from the web interface:
- **Small INT8** - Fastest, lowest memory, lower accuracy
- **Medium INT8** - Good balance (recommended for slower Jetsons)
- **Large-v3 Turbo INT8** - Fast large model, good accuracy
- **Large-v3 INT8** - Best accuracy, highest memory (default)

### 3.4 Position Your Device

- Place your iPad/phone next to your TV
- Adjust font size for comfortable reading
- The subtitles will appear ~3-4 seconds after speech

---

## Step 4: Connect Your HDMI Audio Source

### Physical Setup

```
Japanese TV/Source
       |
       v
  HDMI Audio Extractor
       |
       +---> HDMI OUT ---> TV (for video)
       |
       +---> 3.5mm headphone out
                    |
                    v
            USB Audio Adapter (pink/mic input)
                    |
                    v
                 Jetson
```

### Verify Audio is Flowing

1. Start playing Japanese content on your TV
2. On the Jetson, test recording:
   ```bash
   arecord -D hw:2,0 -f S16_LE -r 16000 -c 1 -d 5 /tmp/hdmi_test.wav
   aplay /tmp/hdmi_test.wav  # Should hear your TV audio
   ```

---

## Step 5: Auto-Start on Boot

The setup script automatically installs a systemd service. To manage it:

### Check Status

```bash
sudo systemctl status jife-subtitles
```

### Start/Stop/Restart

```bash
sudo systemctl start jife-subtitles
sudo systemctl stop jife-subtitles
sudo systemctl restart jife-subtitles
```

### View Logs

```bash
# Service logs
sudo journalctl -u jife-subtitles -f

# Container logs
docker logs subtitle-server --tail 50
```

---

## Troubleshooting

### No Audio Detected

```bash
# Check if audio device exists
arecord -l

# Test recording
arecord -D hw:2,0 -f S16_LE -r 16000 -c 1 -d 5 /tmp/test.wav

# If card number changed, update docker-compose.yml AUDIO_DEVICE
```

### Can't Access Web Page from iPad

```bash
# Check Jetson IP
hostname -I

# Check if server is running
curl http://localhost:5000/health

# Check if container is running
docker ps
```

### Subtitles Are Slow/Delayed

- This is normal - expect 3-4 second delay with large-v3
- Switch to a smaller model from the web interface for faster (less accurate) results
- Medium INT8 is a good balance

### Out of Memory Errors / Low Memory Alerts

```bash
# Check memory usage
free -h

# Check swap
swapon --show

# Switch to a smaller model from the web interface
```

### Model Switch Fails

- The system will automatically recover with medium model if a switch fails
- Large models need more memory - make sure swap is configured (16GB recommended)
- Try switching to medium first, then to larger models

### Container Won't Start

```bash
# Check if image exists
docker images | grep jife-faster-whisper

# Check container logs
docker logs subtitle-server

# Restart the service
sudo systemctl restart jife-subtitles
```

---

## Quick Reference

| Item | Value |
|------|-------|
| Jetson IP | `192.168.1.34` (check yours with `hostname -I`) |
| Web URL | `http://[JETSON_IP]:5000` |
| Audio Device | `plughw:2,0` (check yours with `arecord -l`) |
| Default Model | Large-v3 INT8 (best accuracy) |
| Expected Latency | 3-4 seconds |
| Docker Image | `jife-faster-whisper:latest` |

### Useful Commands

```bash
# Start subtitles
cd /home/vincent/JIFE/subtitle-product && docker compose up -d

# Stop subtitles
docker compose down

# View logs
docker logs subtitle-server -f

# Restart service
sudo systemctl restart jife-subtitles

# Check service status
sudo systemctl status jife-subtitles

# Check audio devices
arecord -l

# Test audio recording
arecord -D hw:2,0 -f S16_LE -r 16000 -c 1 -d 5 /tmp/test.wav
```

---

## Configuration

### Environment Variables

Set in `docker-compose.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `AUDIO_DEVICE` | `plughw:2,0` | Audio device name |
| `WHISPER_MODEL` | `large-v3` | Default model on startup |
| `WHISPER_BACKEND` | `faster_whisper` | ASR backend |
| `WHISPER_COMPUTE_TYPE` | `int8` | Model precision (int8, float16) |
| `WHISPER_BEAM_SIZE` | `1` | Beam search size |
| `WEB_PORT` | `5000` | Web server port |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## Next Steps

1. **Switch models** - Try different models from the web interface to find the best balance for your use case
2. **Custom styling** - Edit `app/web/templates/index.html` for different subtitle appearance
3. **Multiple displays** - Connect multiple iPads to the same URL

---

*Guide updated: December 30, 2025*
