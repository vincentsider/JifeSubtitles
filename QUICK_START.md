# Quick Start Guide - SIMPLIFIED

**Building now... This will take 5-10 minutes.**

---

## ✅ What You'll See in the UI

When you open `http://localhost:5000`, look at the **bottom status bar**:

```
123 subtitles | 580ms | Mode: fixed | Chunk: 2.5s
```

This tells you:
- **Mode:** `fixed` (Option A) or `vad` (Option B)
- **Chunk:** Size in seconds
- **VAD: ✓** (only shows in VAD mode when Silero loaded)

---

## 🔧 How to Switch Modes

### **Option 1: Environment Variable (Easy)**

Edit `docker-compose.yml`:

```yaml
environment:
  - PROCESSING_MODE=fixed    # Default - fast, 0.5-1s latency
  # OR
  - PROCESSING_MODE=vad      # Better quality, 2-3s latency
```

Then restart:
```bash
docker compose down
docker compose up -d
```

### **Option 2: Directly in Config File**

Edit `jife-windows/app/config.py` line 16:

```python
PROCESSING_MODE = 'vad'  # or 'fixed'
```

Then restart container.

---

## 📊 What to Look For in Logs

### **Fixed Mode** (Default):
```
✓ Look for these lines in docker logs:
Processing loop started (MODE: fixed, CHUNK: 2.5s)
[0.57s] Hello, I'm watching anime
[0.42s] This is a test subtitle
```

**Expected:**
- ✅ Latency: 0.5-1s
- ✅ Output is deterministic (same audio = same text)
- ✅ No repetition loops
- ⚠️ Some sentences may be cut at 2.5s boundaries

### **VAD Mode**:
```
✓ Look for these lines in docker logs:
✓ Silero VAD model loaded successfully
Processing loop started (MODE: vad, CHUNK: 2.5s)
VAD segment: 3.24s, RMS: 0.1234
[1.82s] Hello, I'm watching anime.
[2.14s] This is a complete sentence.
```

**Expected:**
- ✅ "Silero VAD model loaded successfully" appears
- ✅ "VAD segment:" logs show variable chunk sizes (1-10s)
- ✅ Complete sentences (natural boundaries)
- ✅ Latency: 2-3s
- ⚠️ Higher latency than fixed mode

---

## 🚨 Troubleshooting

### "Mode shows `-` in UI"
- Status not loaded yet, wait 2 seconds
- Refresh browser

### "Mode: fixed but I set PROCESSING_MODE=vad"
- Check docker-compose.yml syntax (proper YAML indentation)
- Restart: `docker compose down && docker compose up -d`
- Check logs: `docker logs subtitle-server`

### "No VAD: ✓ showing in VAD mode"
- VAD failed to load, check logs for "Failed to load VAD"
- System fell back to fixed mode automatically
- Torch dependencies missing? Rebuild: `docker compose build --no-cache`

---

## 🎯 Recommended Testing

1. **Start with Fixed Mode** (already default):
   ```bash
   docker compose up -d
   docker logs subtitle-server -f
   ```

2. **Watch for 2 minutes**, check:
   - Latency in UI (should be < 1s)
   - No repetition loops
   - Text is stable

3. **If quality is poor**, try VAD mode:
   ```bash
   # Edit docker-compose.yml: PROCESSING_MODE=vad
   docker compose down
   docker compose up -d
   docker logs subtitle-server -f
   ```

4. **Compare**:
   - Fixed: Faster, some fragmented sentences
   - VAD: Slower, complete sentences

---

## Current Build Status

**Building in background...**

Check progress:
```bash
docker images | grep jife
```

When done, you'll see:
```
jife-windows-subtitle-server   latest   ...   5 minutes ago
```

Then start:
```bash
docker compose up -d
docker logs subtitle-server -f
```

---

## Your Evidence Lines

You asked to see these in logs:

### **Fixed Mode:**
```
Processing loop started (MODE: fixed, CHUNK: 2.5s)
```

### **VAD Mode:**
```
✓ Silero VAD model loaded successfully
Processing loop started (MODE: vad, CHUNK: 2.5s)
```

**Both will appear in `docker logs subtitle-server -f`**
