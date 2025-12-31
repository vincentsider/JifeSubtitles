# START HERE - Super Simple Setup

You said VB-CABLE and VoiceMeeter are already installed. Perfect!

## 30-Second VoiceMeeter Setup

1. **Open VoiceMeeter** (search in Windows Start)

2. **Click A1** (top right) and select your speakers/headphones

3. **Make sure B1 is enabled** (it should say "CABLE Input")

4. **Set Windows audio:**
   - Right-click speaker icon → Sound settings
   - Output device → select **"VoiceMeeter Input"**

Done! Now audio goes to both your speakers AND JIFE.

---

## Run the Setup Script

1. **Right-click** on `setup-audio.ps1`
2. **Select** "Run with PowerShell"
3. **Click "Yes"** if Windows asks for permission
4. **Follow the prompts**

The script does everything automatically!

---

## Test It

1. **Open** http://localhost:5000
2. **Play** Japanese YouTube video
3. **See** subtitles!

---

## That's literally it!

For USB audio device (HDMI hardware), just plug it in and run the setup script - it will guide you.

**Need help?**
- See logs: Open PowerShell and run:
  ```
  wsl bash -c 'docker logs subtitle-server -f'
  ```

- Check audio devices:
  ```
  wsl bash -c 'arecord -l'
  ```
