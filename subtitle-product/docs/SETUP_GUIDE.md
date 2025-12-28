# JIFE Setup Guide - Japanese In-Flight Entertainment

Complete step-by-step guide to run real-time Japanese → English subtitles on your Jetson.

---

## Prerequisites

Before starting, ensure you have:
- Jetson Orin Nano/NX with JetPack 6.x installed
- USB audio adapter connected to HDMI audio extractor
- iPad/phone/computer on the same network as the Jetson
- The whisper_trt container built (see BUILD_STATUS.md)

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
ip route get 1 | awk '{print $7; exit}'
```

**Write down this IP** (e.g., `192.168.1.34`). You'll need it for your iPad/phone.

---

## Step 2: Test Whisper with Sample Audio

### 2.1 Download a Japanese Audio Sample

```bash
cd /home/vincent/JIFE
mkdir -p test_audio

# Download a sample Japanese audio file
wget -O test_audio/japanese_sample.mp3 "https://www2.nhk.or.jp/gogaku/assets/mp3/sample_01.mp3" 2>/dev/null || \
  echo "Download failed - you can use any Japanese audio file instead"
```

Or record your own Japanese speech:
```bash
arecord -D hw:2,0 -f S16_LE -r 16000 -c 1 -d 10 test_audio/my_recording.wav
```

### 2.2 Test Whisper Translation in Container

```bash
cd /home/vincent/jetson-containers

# Run the whisper_trt container interactively
sudo ./jetson-containers run $(./autotag whisper_trt)
```

**Inside the container**, run:
```python
import whisper

# Load the model (first time will download ~500MB)
model = whisper.load_model("small")

# Test with your audio file
result = model.transcribe("/data/test_audio/japanese_sample.mp3", task="translate")
print("Translation:", result["text"])
```

**Expected output:** English translation of the Japanese audio.

Press `Ctrl+D` to exit the container.

---

## Step 3: Run the Full Subtitle System

### 3.1 Start the Subtitle Server

```bash
cd /home/vincent/JIFE/subtitle-product

# Set your audio device (replace 2 with your card number)
export AUDIO_DEVICE="hw:2,0"

# Run with docker-compose
sudo docker-compose up
```

Or run directly with the whisper_trt container:
```bash
cd /home/vincent/jetson-containers

sudo ./jetson-containers run \
  --volume /home/vincent/JIFE/subtitle-product:/app \
  --device /dev/snd \
  -p 5000:5000 \
  $(./autotag whisper_trt) \
  python3 /app/app/main.py --audio-device hw:2,0
```

### 3.2 Verify Server is Running

You should see output like:
```
[INFO] Loading Whisper model: small
[INFO] Starting audio capture from hw:2,0
[INFO] Web server starting on http://0.0.0.0:5000
```

---

## Step 4: Access Subtitles on Your iPad/Phone

### 4.1 Open the Subtitle Page

On your iPad/iPhone/Android/Computer, open Chrome (or Safari) and go to:

```
http://192.168.1.34:5000
```

**Replace `192.168.1.34` with your Jetson's IP from Step 1.3**

### 4.2 Subtitle Display Features

The web interface provides:
- **Large, readable subtitles** optimized for viewing
- **Font size controls** (+ and - buttons)
- **Japanese text toggle** (show original + translation)
- **Auto-reconnect** if connection drops
- **Screen wake lock** (keeps your iPad screen on)

### 4.3 Position Your Device

- Place your iPad/phone next to your TV
- Adjust font size for comfortable reading
- The subtitles will appear ~3-4 seconds after speech

---

## Step 5: Connect Your HDMI Audio Source

### Physical Setup

```
Japanese TV/Source
       |
       v
  HDMI Splitter (1 in, 2 out)
       |
       +---> TV (for video)
       |
       +---> HDMI Audio Extractor
                    |
                    v
              USB Audio Adapter
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

## Step 6: Auto-Start on Boot (Optional)

### Create a systemd Service

```bash
sudo tee /etc/systemd/system/jife-subtitles.service << 'EOF'
[Unit]
Description=JIFE Japanese Subtitle System
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=/home/vincent/JIFE/subtitle-product
Environment=AUDIO_DEVICE=hw:2,0
ExecStart=/usr/bin/docker-compose up
ExecStop=/usr/bin/docker-compose down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

### Enable the Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable jife-subtitles
sudo systemctl start jife-subtitles
```

### Check Status

```bash
sudo systemctl status jife-subtitles
sudo journalctl -u jife-subtitles -f  # View logs
```

---

## Troubleshooting

### No Audio Detected

```bash
# Check if audio device exists
arecord -l

# Test recording
arecord -D hw:2,0 -f S16_LE -r 16000 -c 1 -d 5 /tmp/test.wav

# If card number changed, update AUDIO_DEVICE
```

### Can't Access Web Page from iPad

```bash
# Check Jetson IP
ip route get 1 | awk '{print $7; exit}'

# Check if server is running
curl http://localhost:5000/health

# Check firewall (should be disabled by default on Jetson)
sudo ufw status
```

### Subtitles Are Slow/Delayed

- This is normal - expect 3-4 second delay
- The Whisper `small` model balances speed vs accuracy
- For faster (less accurate): use `tiny` or `base` model
- For better accuracy (slower): use `medium` model

### Out of Memory Errors

```bash
# Check memory usage
free -h

# Reduce model size in config
export WHISPER_MODEL=base  # or tiny
```

### Container Won't Start

```bash
# Check if image exists
sudo docker images | grep whisper_trt

# Check docker logs
sudo docker logs $(sudo docker ps -lq)
```

---

## Quick Reference

| Item | Value |
|------|-------|
| Jetson IP | `192.168.1.34` (check yours) |
| Web URL | `http://[JETSON_IP]:5000` |
| Audio Device | `hw:2,0` (check yours with `arecord -l`) |
| Model | Whisper `small` (best for Japanese) |
| Expected Latency | 3-4 seconds |

### Useful Commands

```bash
# Start subtitles
cd /home/vincent/JIFE/subtitle-product && sudo docker-compose up

# Stop subtitles
sudo docker-compose down

# View logs
sudo docker-compose logs -f

# Test whisper interactively
cd /home/vincent/jetson-containers
sudo ./jetson-containers run $(./autotag whisper_trt)

# Check audio devices
arecord -l

# Test audio recording
arecord -D hw:2,0 -f S16_LE -r 16000 -c 1 -d 5 /tmp/test.wav
```

---

## Next Steps

1. **Adjust latency** - Tune chunk size in config for speed vs accuracy tradeoff
2. **Custom styling** - Edit `app/web/templates/index.html` for different subtitle appearance
3. **Multiple displays** - Connect multiple iPads to the same URL
4. **Logging** - Check `logs/` directory for transcription history

---

*Guide created: December 26, 2025*
