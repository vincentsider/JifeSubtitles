# JIFE Windows - Next Steps

## Current System Status ✅

Your JIFE subtitle system is **running and operational**!

- **Container:** `subtitle-server` (running)
- **Web Interface:** http://localhost:5000 (accessible)
- **GPU:** RTX 4080 with CUDA 12.1 (detected)
- **Model:** large-v3 with float16 (loaded)

**What's missing:** Audio input configuration

---

## Choose Your Audio Setup

The system supports **two audio input methods**. Choose the one that fits your use case:

### 🎬 Option 1: Hardware HDMI Audio
**Best for:** Game consoles, set-top boxes, Blu-ray players, external devices

**Requires:**
- HDMI splitter
- HDMI audio extractor
- 3.5mm to USB audio adapter

**Setup:** See [AUDIO_SETUP_GUIDE.md - Option 1](AUDIO_SETUP_GUIDE.md#option-1-hardware-hdmi-audio-original-design-)

---

### 🔊 Option 2: Virtual Audio Cable (NEW!)
**Best for:** YouTube, Netflix, browser content, PC applications

**Requires:**
- VB-CABLE (free software)
- VoiceMeeter (optional, but recommended)
- usbipd (for WSL2 passthrough)

**Setup:** See [AUDIO_SETUP_GUIDE.md - Option 2](AUDIO_SETUP_GUIDE.md#option-2-virtual-audio-cable-software-routing-)

**This is the recommended option for translating:**
- YouTube videos
- Streaming services (Netflix, Crunchyroll, etc.)
- Video games running on PC
- Discord/Zoom calls
- Any Windows audio source

---

## Quick Start: VB-CABLE Setup (5 minutes)

If you want to test with YouTube/browser audio right now:

1. **Install VB-CABLE:**
   ```
   Download from: https://vb-audio.com/Cable/
   Run as Administrator and install
   ```

2. **Install VoiceMeeter:**
   ```
   Download from: https://vb-audio.com/Voicemeeter/
   Run as Administrator and install
   ```

3. **Configure VoiceMeeter:**
   - Set Windows playback device to "VoiceMeeter Input"
   - In VoiceMeeter: A1 = Your speakers, B1 = CABLE Input

4. **Attach to WSL2:**
   ```powershell
   # Install usbipd
   winget install usbipd

   # Find VB-CABLE device
   usbipd list

   # Attach to WSL2
   usbipd bind --busid <BUSID>
   usbipd attach --wsl --busid <BUSID>

   # Verify in WSL2
   wsl bash -c "arecord -l"
   ```

5. **Enable audio in docker-compose.yml:**
   - Uncomment lines 45-49 (devices and group_add sections)
   - Update AUDIO_DEVICE to match your card number

6. **Restart container:**
   ```bash
   wsl bash -c "cd /mnt/c/Projects/priority/JifeSubtitles/jife-windows && docker compose restart"
   ```

7. **Test:**
   - Play Japanese content on YouTube
   - Open http://localhost:5000
   - See live subtitles!

---

## Useful Commands

```bash
# View logs (watch model loading and transcription)
wsl bash -c "docker logs subtitle-server -f"

# Restart container (after config changes)
wsl bash -c "cd /mnt/c/Projects/priority/JifeSubtitles/jife-windows && docker compose restart"

# Stop container
wsl bash -c "cd /mnt/c/Projects/priority/JifeSubtitles/jife-windows && docker compose down"

# Start container
wsl bash -c "cd /mnt/c/Projects/priority/JifeSubtitles/jife-windows && docker compose up -d"

# Check GPU usage (should show memory usage when transcribing)
wsl nvidia-smi

# Health check (verify web server is running)
wsl bash -c "curl http://localhost:5000/health"

# Check audio devices in WSL2
wsl bash -c "arecord -l"

# Test audio recording (5 seconds)
wsl bash -c "arecord -D plughw:X,0 -f S16_LE -r 16000 -c 1 -d 5 /tmp/test.wav"
```

---

## Testing the System

Once audio is configured:

1. **Test with clear Japanese speech:**
   - News broadcasts (NHK)
   - Anime with clear dialogue
   - YouTube Japanese lessons

2. **Check for subtitles:**
   - Open http://localhost:5000
   - Subtitles should appear within 1 second of speech

3. **Monitor GPU usage:**
   ```bash
   wsl nvidia-smi
   ```
   Should show increased VRAM usage during transcription

4. **Review logs:**
   ```bash
   wsl bash -c "docker logs subtitle-server -f"
   ```
   Should show "Creating audio capture" and transcription output

---

## Performance Tuning

Edit `docker-compose.yml` to adjust performance:

### For Better Quality (slower):
```yaml
- WHISPER_MODEL=large-v3        # Already set
- WHISPER_BEAM_SIZE=7           # Increase from 5
- WHISPER_COMPUTE_TYPE=float16  # Already set
```

### For Faster Speed (lower quality):
```yaml
- WHISPER_MODEL=medium          # Change from large-v3
- WHISPER_BEAM_SIZE=3           # Decrease from 5
- WHISPER_COMPUTE_TYPE=float16  # Keep this
```

After changes:
```bash
wsl bash -c "cd /mnt/c/Projects/priority/JifeSubtitles/jife-windows && docker compose restart"
```

---

## Access from Mobile Devices

Find your Windows IP address:
```powershell
ipconfig
```

On your iPad/phone, navigate to:
```
http://YOUR_WINDOWS_IP:5000
```

Make sure Windows Firewall allows port 5000 (Docker usually handles this).

---

## Recommended Next Steps

1. ✅ **Set up VB-CABLE** (Option 2) for easy testing with YouTube
2. ✅ **Test with Japanese content** to verify everything works
3. ✅ **Try different models** (medium vs large-v3) to find your preferred speed/quality balance
4. ✅ **Access from mobile** to use as a second screen for subtitles
5. ✅ **Set up hardware HDMI** (Option 1) if you have external devices
6. ✅ **Monitor GPU usage** to ensure efficient utilization

---

## Troubleshooting

### Audio not working?
- Check [AUDIO_SETUP_GUIDE.md](AUDIO_SETUP_GUIDE.md) for detailed troubleshooting
- Verify device with: `wsl bash -c "arecord -l"`
- Check docker-compose.yml has correct AUDIO_DEVICE setting

### Subtitles not appearing?
- Check logs: `docker logs subtitle-server -f`
- Verify model is loaded (should see "Model loaded" in logs)
- Ensure audio is playing (check VoiceMeeter levels)

### Poor quality translations?
- Use `large-v3` model (best quality)
- Increase `WHISPER_BEAM_SIZE` to 5 or 7
- Ensure audio quality is good (clear speech, no background noise)

### High latency?
- Try `medium` model (faster than large-v3)
- Reduce `WHISPER_BEAM_SIZE` to 1
- Check GPU isn't being used by other applications

---

## Documentation

- **[README.md](README.md)** - Quick start and overview
- **[AUDIO_SETUP_GUIDE.md](AUDIO_SETUP_GUIDE.md)** - Complete audio configuration guide
- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Full setup instructions

---

**The system is ready to use as soon as audio input is configured!** 🎌→🇬🇧
