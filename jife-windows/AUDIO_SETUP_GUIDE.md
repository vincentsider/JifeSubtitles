# JIFE Windows - Audio Input Setup Guide

This guide covers **two audio input methods** for JIFE on Windows. Choose the one that fits your use case.

---

## Option 1: Hardware HDMI Audio (Original Design) 🎬

**Best for:** External devices (game consoles, set-top boxes, Blu-ray players, streaming sticks)

### Hardware Required
- HDMI splitter (1 in → 2 out)
- HDMI audio extractor
- 3.5mm to USB audio adapter
- HDMI cables

### Setup

```
[Source Device] ──HDMI──> [HDMI Splitter] ──HDMI──> [Monitor/TV]
                                │
                                └──HDMI──> [Audio Extractor]
                                                 │
                                           3.5mm audio
                                                 │
                                                 v
                                    [USB Audio Adapter] ──USB──> [PC]
                                                                   │
                                                                WSL2
                                                                   │
                                                              [Container]
```

### Configuration Steps

1. **Connect hardware** as shown above

2. **Install usbipd on Windows:**
   ```powershell
   winget install usbipd
   ```

3. **Find your USB audio device:**
   ```powershell
   usbipd list
   ```
   Look for your audio adapter (e.g., "USB Audio Device")

4. **Attach to WSL2:**
   ```powershell
   usbipd bind --busid <BUSID>
   usbipd attach --wsl --busid <BUSID>
   ```

5. **Verify in WSL2:**
   ```bash
   wsl bash -c "arecord -l"
   ```
   Note the card number (e.g., `card 1`)

6. **Update docker-compose.yml:**
   - Uncomment the `devices` and `group_add` sections (lines 45-49)
   - Set `AUDIO_DEVICE` if needed (e.g., `plughw:1,0` for card 1)

7. **Restart container:**
   ```bash
   wsl bash -c "cd /mnt/c/Projects/priority/JifeSubtitles/jife-windows && docker compose restart"
   ```

---

## Option 2: Virtual Audio Cable (Software Routing) 🔊

**Best for:** Translating content playing on your Windows PC (YouTube, Netflix, games, video calls, etc.)

### Advantages
✅ No additional hardware needed
✅ Works with ANY Windows audio source
✅ Can still hear audio while capturing
✅ Great for testing and demos

### Software Required
- **VB-CABLE** (free virtual audio driver)
- **VoiceMeeter** (free audio mixer - optional but recommended)
- **usbipd** (to pass virtual device to WSL2)

### Setup

#### Step 1: Install VB-CABLE

1. **Download VB-CABLE:**
   - Visit: https://vb-audio.com/Cable/
   - Download "VBCABLE_Driver_Pack43.zip"

2. **Install:**
   - Extract the ZIP file
   - Right-click `VBCABLE_Setup_x64.exe` → "Run as Administrator"
   - Click "Install Driver"
   - Restart if prompted

3. **Verify installation:**
   - Open Windows Sound Settings
   - You should see "CABLE Input" and "CABLE Output" devices

#### Step 2: Install VoiceMeeter (Recommended)

VoiceMeeter allows you to route audio to BOTH your speakers AND VB-CABLE simultaneously.

1. **Download VoiceMeeter:**
   - Visit: https://vb-audio.com/Voicemeeter/
   - Download "VoiceMeeter" (basic version is fine)

2. **Install:**
   - Run installer as Administrator
   - Restart if prompted

3. **Configure VoiceMeeter:**
   ```
   HARDWARE INPUT 1: Select your microphone (if you want to keep it)
   VIRTUAL INPUT (Cable Input): This receives from applications

   A1: Your speakers/headphones
   B1: CABLE Input (this goes to JIFE)
   ```

4. **Set Windows playback device:**
   - Right-click speaker icon → "Sound settings"
   - Set "VoiceMeeter Input" as default playback device

#### Step 3: Attach VB-CABLE to WSL2

1. **Install usbipd (if not already installed):**
   ```powershell
   winget install usbipd
   ```

2. **List audio devices:**
   ```powershell
   usbipd list
   ```
   Look for "CABLE Output" or similar VB-Audio device

3. **Bind and attach:**
   ```powershell
   usbipd bind --busid <BUSID>
   usbipd attach --wsl --busid <BUSID>
   ```

4. **Verify in WSL2:**
   ```bash
   wsl bash -c "arecord -l"
   ```
   Find the card number for CABLE Output

#### Step 4: Update JIFE Configuration

1. **Enable audio device in docker-compose.yml:**

   Uncomment lines 45-49:
   ```yaml
   devices:
     - /dev/snd:/dev/snd

   group_add:
     - audio
   ```

2. **Set the correct audio device:**

   Update line 54 to match your VB-CABLE card number:
   ```yaml
   - AUDIO_DEVICE=plughw:X,0  # Replace X with card number from arecord -l
   ```

3. **Restart container:**
   ```bash
   wsl bash -c "cd /mnt/c/Projects/priority/JifeSubtitles/jife-windows && docker compose restart"
   ```

#### Step 5: Test

1. **Play Japanese content** (YouTube, Netflix, etc.)
2. **Open subtitle interface:** http://localhost:5000
3. **You should see live subtitles** appear as the audio plays
4. **Audio should still play** through your speakers (via VoiceMeeter)

### VoiceMeeter Audio Routing Diagram

```
┌─────────────────┐
│  Windows Apps   │
│ (YouTube, etc.) │
└────────┬────────┘
         │
         v
┌─────────────────────┐
│   VoiceMeeter Input │
└─────┬───────────┬───┘
      │           │
      │           └──────> A1: Your Speakers (you hear it)
      │
      └──────> B1: CABLE Input
                    │
                    v
              CABLE Output
                    │
                    v
              USB Passthrough
                    │
                    v
                  WSL2
                    │
                    v
            Docker Container
                    │
                    v
           [JIFE Subtitles]
```

---

## Troubleshooting

### Virtual Audio Cable Not Showing in WSL2

**Problem:** `arecord -l` doesn't show VB-CABLE device

**Solutions:**
1. Make sure VB-CABLE is playing audio (play something in Windows)
2. Try detaching and reattaching with usbipd:
   ```powershell
   usbipd detach --busid <BUSID>
   usbipd attach --wsl --busid <BUSID>
   ```
3. Restart WSL2:
   ```powershell
   wsl --shutdown
   wsl
   ```

### Audio Capturing But No Subtitles

**Problem:** Container receives audio but doesn't generate subtitles

**Solutions:**
1. Check logs:
   ```bash
   wsl bash -c "docker logs subtitle-server -f"
   ```
2. Verify model is loaded (should see "Model loaded" in logs)
3. Check audio levels - might be too quiet
4. Test with loud, clear Japanese speech first

### Can't Hear Audio Anymore

**Problem:** After setting up VoiceMeeter, no audio from speakers

**Solutions:**
1. Open VoiceMeeter and ensure A1 is set to your speakers
2. Check that channels are not muted (red = muted, should be green)
3. Adjust volume sliders in VoiceMeeter

### USB Device Detaches After Sleep/Restart

**Problem:** Need to reattach usbipd after Windows restarts

**Solution:** Create a startup script:
1. Create `attach-audio.bat`:
   ```batch
   @echo off
   usbipd attach --wsl --busid <YOUR_BUSID>
   ```
2. Place in `shell:startup` folder
3. Or manually reattach after each restart

---

## Recommended Setup by Use Case

| Use Case | Recommended Option | Why |
|----------|-------------------|-----|
| Anime streaming on PC | Option 2 (VB-CABLE) | Direct software routing, no hardware |
| YouTube videos | Option 2 (VB-CABLE) | Easy setup, no hardware needed |
| Gaming console (PS5, Switch) | Option 1 (HDMI) | Clean audio signal, zero latency |
| Video conferencing | Option 2 (VB-CABLE) | Can capture meeting audio |
| Blu-ray player | Option 1 (HDMI) | Best audio quality |
| Testing/Demo | Option 2 (VB-CABLE) | Quick setup, repeatable |

---

## Performance Notes

- **VB-CABLE adds ~5-10ms latency** (negligible for subtitles)
- **VoiceMeeter adds ~10-15ms** (still imperceptible)
- **Total system latency:** ~500ms-1s from speech to subtitle (mostly Whisper processing)
- **GPU usage:** ~2-4GB VRAM for large-v3 model

---

## Next Steps After Audio Setup

Once audio is working:

1. **Test with clear Japanese speech** (news, anime with clear dialogue)
2. **Adjust beam size** in docker-compose.yml if needed (higher = more accurate, slower)
3. **Try different models** (medium, small) if large-v3 is too slow
4. **Access from mobile devices** at http://YOUR_PC_IP:5000
5. **Monitor GPU usage** with `wsl nvidia-smi` during transcription

---

**Questions?** Check the main IMPLEMENTATION_GUIDE.md or container logs for more details.
