# JIFE Cloud (Raspberry Pi + Groq API) - AI Implementation Guide

**PURPOSE**: This document tells an AI coding assistant EXACTLY how to set up JIFE on a Raspberry Pi 5 using the Groq cloud API for inference. Follow these instructions precisely.

---

## OVERVIEW

This is a **product version** of JIFE designed for commercial deployment. It uses:
- **Raspberry Pi 5** ($80) for audio capture and web serving
- **Groq Cloud API** for Whisper large-v3 inference (fastest cloud API)
- No GPU required - all AI runs in the cloud

**Expected Result**: 1-2 second latency, excellent quality, low hardware cost.

---

## ARCHITECTURE

```
HDMI Audio Source
       |
       v
HDMI Audio Extractor
       |
       +---> HDMI OUT ---> TV (video)
       |
       +---> 3.5mm out ---> USB Audio Adapter ---> Raspberry Pi 5
                                                        |
                                         [Audio Capture + Web Server]
                                                        |
                                         HTTPS --> Groq Cloud API
                                                   (whisper-large-v3)
                                                        |
                                                   http://PI_IP:5000
                                                        |
                                                   iPad/Phone (subtitles)
```

---

## COST ANALYSIS

### Groq API Pricing (as of Dec 2025)
- Whisper large-v3: **$0.111 per audio hour**
- Translation included (no separate charge)

### Usage Scenarios
| Scenario | Monthly Hours | Monthly Cost |
|----------|---------------|--------------|
| Light (1hr/day) | 30 hours | $3.33 |
| Medium (3hr/day) | 90 hours | $9.99 |
| Heavy (8hr/day) | 240 hours | $26.64 |

### Business Model (Subscription)
| Tier | Price | Included Hours | Overage |
|------|-------|----------------|---------|
| Basic | $9.99/mo | 60 hours | $0.15/hr |
| Standard | $19.99/mo | 150 hours | $0.12/hr |
| Unlimited | $29.99/mo | Unlimited | - |

---

## PREREQUISITES (User must do manually)

1. **Raspberry Pi 5** (4GB or 8GB RAM)
   - Raspberry Pi OS (64-bit) installed
   - Connected to WiFi/Ethernet

2. **USB Audio Adapter** with microphone input (pink jack)

3. **Groq API Key**
   - Sign up at https://console.groq.com/
   - Create API key at https://console.groq.com/keys
   - Free tier: 14,400 requests/day (enough for ~40 hours continuous)

---

## FILES IN THIS FOLDER

| File | Purpose |
|------|---------|
| `main.py` | Main application entry point |
| `groq_client.py` | Groq Whisper API wrapper |
| `audio_buffer.py` | Audio capture and buffering |
| `web_server.py` | Flask + SocketIO web interface |
| `config.py` | Configuration settings |
| `templates/index.html` | Web UI (copied from main project) |
| `requirements.txt` | Python dependencies |
| `setup.sh` | One-click setup script |
| `jife-cloud.service` | Systemd service file |

---

## STEP-BY-STEP IMPLEMENTATION

### Step 1: Clone repository on Pi

```bash
cd ~
git clone https://github.com/vincentsider/JifeSubtitles.git
cd JifeSubtitles/jife-cloud
```

### Step 2: Run setup script

```bash
chmod +x setup.sh
./setup.sh
```

This installs dependencies and configures the service.

### Step 3: Set API key

```bash
# Edit the service file or set environment variable
export GROQ_API_KEY="your-api-key-here"

# Or add to ~/.bashrc for persistence
echo 'export GROQ_API_KEY="your-api-key-here"' >> ~/.bashrc
```

### Step 4: Start the service

```bash
sudo systemctl start jife-cloud
sudo systemctl enable jife-cloud  # Auto-start on boot
```

### Step 5: Access subtitles

Find Pi's IP:
```bash
hostname -I
```

Open on iPad: `http://PI_IP:5000`

---

## KEY DIFFERENCES FROM JETSON/WINDOWS

| Aspect | Jetson | Windows | Pi Cloud |
|--------|--------|---------|----------|
| Hardware | $200-500 | Existing PC | $80 |
| GPU | Required | Required | Not needed |
| Internet | Not needed | Not needed | **Required** |
| Latency | 3-4s | <0.5s | 1-2s |
| Running cost | $0 | $0 | ~$10-30/mo |
| Model | INT8 (limited) | float16 (best) | large-v3 (best) |
| Power | 10-25W | 300W | 5W |

---

## HOW THE AUDIO CHUNKING WORKS

The Groq API processes audio files, not streams. We need to:

1. **Capture audio** continuously at 16kHz mono
2. **Buffer 5 seconds** of audio
3. **Send to Groq** via HTTPS POST (WAV file)
4. **Receive translation** (English text)
5. **Display on web** via WebSocket
6. **Repeat**

```
Timeline:
[===== 5 sec =====][===== 5 sec =====][===== 5 sec =====]
        |                  |                  |
        v                  v                  v
    [API call]         [API call]         [API call]
        |                  |                  |
        v                  v                  v
   [Subtitle 1]       [Subtitle 2]       [Subtitle 3]
```

**Latency breakdown:**
- Audio buffer: 5 seconds
- API call: 0.5-1 second
- **Total: ~5.5-6 seconds**

**Optimization (overlap):**
We can reduce perceived latency by overlapping chunks:
- Send 5-second chunks every 3 seconds
- Overlap of 2 seconds catches mid-sentence splits
- **Effective latency: ~3-4 seconds**

---

## CONFIGURATION OPTIONS

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | (required) | Your Groq API key |
| `AUDIO_DEVICE` | `plughw:1,0` | ALSA device name |
| `CHUNK_DURATION` | `5` | Seconds per API call |
| `OVERLAP_DURATION` | `2` | Overlap between chunks |
| `WEB_PORT` | `5000` | Web server port |

---

## TESTING

1. Setup completes without error
2. `curl http://localhost:5000/health` returns OK
3. Speaking Japanese produces English subtitles
4. Latency is under 6 seconds
5. Service auto-starts after reboot

---

## TROUBLESHOOTING

### No subtitles appearing

```bash
# Check service status
sudo systemctl status jife-cloud

# Check logs
sudo journalctl -u jife-cloud -f

# Verify API key is set
echo $GROQ_API_KEY
```

### API errors

```bash
# Test API directly
curl -X POST "https://api.groq.com/openai/v1/audio/translations" \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test.wav" \
  -F "model=whisper-large-v3"
```

### Audio device not found

```bash
# List devices
arecord -l

# Test recording
arecord -D plughw:1,0 -f S16_LE -r 16000 -c 1 -d 5 test.wav
aplay test.wav
```

---

## SECURITY NOTES

- **API key**: Never commit to git. Use environment variables.
- **HTTPS**: All API calls use HTTPS (encrypted).
- **Local network**: Web server only accessible on local network by default.

---

## RATE LIMITS

Groq free tier limits:
- 14,400 requests per day
- 30 requests per minute

For continuous use at 5-second chunks:
- 12 requests/minute (well under limit)
- 720 requests/hour
- 17,280 requests/day (slightly over free limit)

**Recommendation**: Use 6-second chunks for free tier (10 req/min = 14,400/day exactly).

---

*This guide assumes the AI assistant has full access to create/edit files and run commands.*
