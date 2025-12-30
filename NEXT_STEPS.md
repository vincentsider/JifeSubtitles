# JIFE Subtitles - What to Do Next

## After You Restart Your Computer

You have two options. Pick one based on what you want to translate:

---

## Option A: YouTube/Netflix/Browser Audio (VB-CABLE)

### One-Time VoiceMeeter Setup (only need to do this once)

1. **Open VoiceMeeter**
   - Press Windows key
   - Type "VoiceMeeter"
   - Open it

2. **Configure it:**
   - Find **A1** (top-right corner)
   - Click it and select your speakers/headphones
   - Check that **B1** shows "CABLE Input" and is highlighted/enabled

3. **Set Windows audio:**
   - Right-click speaker icon in taskbar
   - Click "Sound settings"
   - Under "Output device", select **"VoiceMeeter Input"**

### Run the Setup Script (after restart)

1. **Open File Explorer** → Navigate to:
   ```
   C:\Projects\priority\JifeSubtitles\jife-windows
   ```

2. **Right-click** `setup-audio.ps1`

3. **Select** "Run with PowerShell"

4. **Click "Yes"** when Windows asks for permission

5. **Follow the prompts** - the script does everything!

### Test It

1. **Open browser** → http://localhost:5000

2. **Play Japanese YouTube video**

3. **See subtitles appear!** 🎉

---

## Option B: Hardware USB Audio Device (HDMI)

### Setup (after restart, with USB device plugged in)

1. **Plug in your USB audio device**

2. **Open File Explorer** → Navigate to:
   ```
   C:\Projects\priority\JifeSubtitles\jife-windows
   ```

3. **Right-click** `setup-audio.ps1`

4. **Select** "Run with PowerShell"

5. **Click "Yes"** when Windows asks for permission

6. **Follow the prompts** - the script will find your device automatically!

### Test It

1. **Make sure audio is playing** through your USB device

2. **Open browser** → http://localhost:5000

3. **Play Japanese content** through HDMI

4. **See subtitles appear!** 🎉

---

## Important Notes

### For VB-CABLE Users:
- VoiceMeeter stays configured after restart
- Just run `setup-audio.ps1` after each restart to reconnect the audio

### For USB Audio Users:
- After **every Windows restart**, you need to run `setup-audio.ps1` again
- This re-attaches the USB device to WSL2
- It only takes 10 seconds!

---

## Quick Commands

### Check if it's working:
```powershell
wsl bash -c 'docker logs subtitle-server -f'
```
Look for "Creating audio capture" and transcription output

### Check audio devices:
```powershell
wsl bash -c 'arecord -l'
```
Should show your audio card

### Restart container manually:
```powershell
wsl bash -c 'cd /mnt/c/Projects/priority/JifeSubtitles/jife-windows; docker compose restart'
```

---

## Troubleshooting

### No subtitles appearing?

1. **Check VoiceMeeter** (if using VB-CABLE):
   - Is audio showing on the meters?
   - Is B1 enabled?

2. **Check logs**:
   ```powershell
   wsl bash -c 'docker logs subtitle-server -f'
   ```

3. **Re-run the setup script**

### Can't access http://localhost:5000?

Make sure Docker Desktop is running!

---

## That's It!

The setup script handles everything automatically. You just need to run it after restarting Windows.

**For detailed help:** See `jife-windows/START_HERE.md` or `jife-windows/QUICK_START.md`
