# JIFE Windows - Quick Reference

## After Restart - Just Do This:

### For YouTube/Browser Audio (VB-CABLE):

1. **Make sure VoiceMeeter is set up** (only need to do once):
   - Open VoiceMeeter
   - A1 = your speakers
   - B1 = enabled (CABLE Input)
   - Windows Output = "VoiceMeeter Input"

2. **Run this script**:
   ```
   Right-click: jife-windows/setup-audio.ps1 → Run with PowerShell
   ```

3. **Test**:
   - Open: http://localhost:5000
   - Play Japanese YouTube video
   - See subtitles! 🎉

---

### For USB Audio Device (HDMI):

1. **Plug in USB device**

2. **Run this script**:
   ```
   Right-click: jife-windows/setup-audio.ps1 → Run with PowerShell
   ```

3. **Test**:
   - Open: http://localhost:5000
   - Play Japanese HDMI content
   - See subtitles! 🎉

---

## That's literally all you need to do!

**After every Windows restart**, just run that one script again.

**More details:** See [NEXT_STEPS.md](NEXT_STEPS.md)
