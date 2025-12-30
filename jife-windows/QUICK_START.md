# JIFE Windows - Quick Start Guide

**Choose your setup based on what you want to translate:**

---

## 🔊 Option A: YouTube/Netflix/Browser Content (VB-CABLE)

**You said you installed VB-CABLE and VoiceMeeter - great! Here's the simple version:**

### Step 1: Quick VoiceMeeter Setup (30 seconds)

1. **Open VoiceMeeter** (search for it in Windows Start menu)

2. **Configure it like this:**
   - In the top-right corner, find **A1**
   - Click **A1** and select your speakers/headphones
   - Find **B1** (should already say "CABLE Input")
   - Make sure **B1** is highlighted/enabled

3. **Set Windows audio:**
   - Right-click the speaker icon in Windows taskbar
   - Click "Sound settings"
   - Under "Output device", select **"VoiceMeeter Input"**

That's it for VoiceMeeter! Now audio from YouTube/etc. will go to both your speakers AND to JIFE.

### Step 2: Run the Setup Script

1. **Open PowerShell as Administrator:**
   - Press Windows key
   - Type "PowerShell"
   - Right-click "Windows PowerShell"
   - Click "Run as Administrator"

2. **Navigate to the folder:**
   ```powershell
   cd C:\Projects\priority\JifeSubtitles\jife-windows
   ```

3. **Run the setup script:**
   ```powershell
   .\setup-vbcable.ps1
   ```

4. **Follow the prompts** - the script does everything automatically!

### Step 3: Test It!

1. **Open http://localhost:5000** in your browser
2. **Play Japanese content** (YouTube, Netflix, etc.)
3. **See subtitles appear!** 🎉

---

## 🎬 Option B: Hardware HDMI Audio (USB Audio Device)

**For game consoles, set-top boxes, or external HDMI devices:**

### Step 1: Plug In Your USB Audio Device

Make sure your USB audio adapter is connected to your PC.

### Step 2: Run the Setup Script

1. **Open PowerShell as Administrator:**
   - Press Windows key
   - Type "PowerShell"
   - Right-click "Windows PowerShell"
   - Click "Run as Administrator"

2. **Navigate to the folder:**
   ```powershell
   cd C:\Projects\priority\JifeSubtitles\jife-windows
   ```

3. **Run the setup script:**
   ```powershell
   .\setup-hdmi.ps1
   ```

4. **Follow the prompts** - the script will:
   - Find your USB audio device
   - Attach it to WSL2
   - Configure JIFE
   - Restart the container

### Step 3: Test It!

1. **Make sure audio is playing** through your USB device
2. **Open http://localhost:5000** in your browser
3. **Play Japanese content** through HDMI
4. **See subtitles appear!** 🎉

### Important Note

**After Windows restarts**, you'll need to re-run the script OR manually run:
```powershell
usbipd attach --wsl --busid <YOUR_BUSID>
```

The script will tell you your Bus ID at the end.

---

## 🚨 Troubleshooting

### No subtitles appearing?

**Check the logs:**
```powershell
wsl bash -c "docker logs subtitle-server -f"
```

Look for:
- "Model loaded" ✓ (means AI is ready)
- "Creating audio capture" ✓ (means it's listening)
- Transcription output ✓ (means it's working)

### VB-CABLE: Audio but no subtitles?

1. **Check VoiceMeeter:**
   - Is audio showing on the meters?
   - Is B1 enabled (highlighted)?

2. **Re-run the setup script:**
   ```powershell
   .\setup-vbcable.ps1
   ```

### Hardware HDMI: Device not found?

1. **Make sure USB device is plugged in**

2. **Run this to see all devices:**
   ```powershell
   usbipd list
   ```

3. **Look for your audio device** in the list

4. **Re-run the setup script** and manually enter the Bus ID when prompted

---

## 📱 Access from Phone/Tablet

1. **Find your Windows IP address:**
   ```powershell
   ipconfig
   ```
   Look for "IPv4 Address" (e.g., 192.168.1.100)

2. **On your phone/tablet:**
   - Open browser
   - Go to: `http://YOUR_IP:5000`
   - Example: `http://192.168.1.100:5000`

---

## ⚙️ Advanced: Change Settings

To use a different model or adjust quality:

1. **Edit this file:**
   ```
   C:\Projects\priority\JifeSubtitles\jife-windows\docker-compose.yml
   ```

2. **Find these lines (around line 54-58):**
   ```yaml
   - WHISPER_MODEL=large-v3
   - WHISPER_BEAM_SIZE=5
   ```

3. **Change to:**
   - **Faster (lower quality):** `WHISPER_MODEL=medium` and `WHISPER_BEAM_SIZE=3`
   - **Best quality (slower):** Keep `large-v3` and change `WHISPER_BEAM_SIZE=7`

4. **Restart container:**
   ```powershell
   wsl bash -c "cd /mnt/c/Projects/priority/JifeSubtitles/jife-windows && docker compose restart"
   ```

---

## 🎯 That's It!

You now have a working Japanese→English subtitle system!

**Questions?** Check the detailed guides:
- [AUDIO_SETUP_GUIDE.md](AUDIO_SETUP_GUIDE.md) - Detailed audio setup
- [next_steps.md](next_steps.md) - Advanced configuration
- Container logs: `wsl bash -c "docker logs subtitle-server -f"`
