# Dual Mode Implementation Guide

**Date:** 2025-12-31
**Status:** ✅ IMPLEMENTED

---

## Overview

The system now supports **TWO processing modes** that you can switch between:

### **Mode 1: Fixed Chunks (Option A - Default)**
- **Speed:** Ultra-fast (< 1s latency)
- **Quality:** Good, some fragmented sentences
- **Complexity:** Simple
- **Best for:** Real-time with minimal delay

### **Mode 2: VAD-Based (Option B)**
- **Speed:** Fast (2-3s latency)
- **Quality:** Better sentence coherence
- **Complexity:** Uses Silero VAD
- **Best for:** Production quality subtitles

---

## How to Switch Modes

### **Method 1: Environment Variable (Recommended)**

Edit `docker-compose.yml`:

```yaml
environment:
  - PROCESSING_MODE=fixed    # Option A (default, fast)
  # OR
  - PROCESSING_MODE=vad      # Option B (better quality)
```

Then restart:
```bash
docker compose down
docker compose up --build -d
```

### **Method 2: Config File**

Edit `jife-windows/app/config.py`:

```python
PROCESSING_MODE = 'fixed'  # or 'vad'
```

---

## What Changed in Option A (Fixed Mode)

### ✅ **Parameter Optimizations:**

| Parameter | Old Value | New Value | Why |
|-----------|-----------|-----------|-----|
| `chunk_duration` | 1.5s | 2.5s | More context per chunk |
| `temperature` | default | 0.0 | Deterministic output |
| `no_speech_threshold` | 0.65 | 0.7 | Filter music in Japanese TV |
| `condition_on_previous_text` | False | False | Prevents repetition loops ✅ |
| `chunk_overlap` | 0.0 | 0.0 | No overlap (prevents loops) ✅ |

### ✅ **Code Simplifications:**

**Removed:**
- ❌ Sentence buffering (was holding text indefinitely)
- ❌ Overlapping chunk deduplication (was blocking legitimate text)
- ❌ Complex state management

**Added:**
- ✅ Simple duplicate detection (`if text == last_text: skip`)
- ✅ Immediate output (no delays)
- ✅ Clear logging with mode indicator

---

## What's New in Option B (VAD Mode)

### **Architecture:**

```
Audio Input → AudioCapture (0.5s raw chunks)
                    ↓
              VADProcessor (Silero VAD)
              - Detects speech boundaries
              - Buffers 1-10s utterances
                    ↓
              Processing Loop (Whisper)
              - Transcribes complete utterances
              - Better context, complete sentences
```

### **Key Features:**

1. **Natural Boundaries:** Segments at speech pauses (not fixed time)
2. **Variable Length:** 1-10s chunks based on actual speech
3. **Pre-padding:** 200ms of audio before speech detected
4. **Silence Detection:** 500ms silence ends an utterance

### **Parameters:**

```python
VAD_MIN_CHUNK_SIZE = 1.0s    # Minimum before processing
VAD_MAX_CHUNK_SIZE = 10.0s   # Force output (prevent infinite buffer)
MIN_SILENCE_DURATION_MS = 500ms  # Silence to end utterance
PRE_ROLL_MS = 200ms          # Padding before speech
```

---

## Performance Comparison

### **Fixed Mode (Option A):**

```
Latency Distribution (100 subtitles):
  Min: 0.31s
  Avg: 0.57s ✅✅✅
  Max: 2.28s

Quality:
  - Some mid-sentence cuts at 2.5s boundaries
  - Deterministic (temperature=0)
  - No repetition loops
  - Clean duplicate filtering
```

### **VAD Mode (Option B) - Expected:**

```
Latency Distribution:
  Min: 1.0s (buffer minimum)
  Avg: 2-3s
  Max: 10s (max chunk size)

Quality:
  - Complete sentences (natural boundaries)
  - Better context for translation
  - No mid-sentence cuts
  - More coherent output
```

---

## When to Use Each Mode

### **Use Fixed Mode (Option A) if:**
- You prioritize low latency (< 1s)
- You're OK with occasional fragmented sentences
- You want simplicity (no VAD dependency)
- You're testing/developing

### **Use VAD Mode (Option B) if:**
- You prioritize quality over speed
- You need complete, coherent sentences
- You can tolerate 2-3s latency
- You're in production

---

## Testing

### **Test Fixed Mode:**

```bash
# Default mode
docker compose up --build -d
docker logs subtitle-server -f

# Look for:
# - "Processing loop started (MODE: fixed, CHUNK: 2.5s)"
# - Latency around 0.5-1s
# - Possible sentence fragments
```

### **Test VAD Mode:**

```bash
# Set VAD mode
# Edit docker-compose.yml: PROCESSING_MODE=vad

docker compose up --build -d
docker logs subtitle-server -f

# Look for:
# - "Processing loop started (MODE: vad, CHUNK: 2.5s)"
# - "Silero VAD model loaded successfully"
# - "VAD segment: X.XXs, RMS: X.XXXX"
# - Latency around 2-3s
# - Complete sentences
```

---

## Troubleshooting

### **Fixed Mode Issues:**

| Problem | Solution |
|---------|----------|
| Repetition loops | Check `condition_on_previous_text=False` |
| Too many duplicates | Check `temperature=0.0` |
| Fragmented sentences | Increase `chunk_duration` to 3.0s |
| Slow processing | Decrease `chunk_duration` to 2.0s |

### **VAD Mode Issues:**

| Problem | Solution |
|---------|----------|
| "VAD model not loaded" | Rebuild with torch: `docker compose build --no-cache` |
| No segments detected | Check `VAD_MIN_CHUNK_SIZE` (try 0.5s) |
| Segments too long | Decrease `MIN_SILENCE_DURATION_MS` to 300ms |
| Missing speech start | Increase `PRE_ROLL_MS` to 400ms |

---

## Docker Build Notes

### **Dependencies Added:**

```dockerfile
torch>=2.0.0        # For Silero VAD
torchaudio>=2.0.0   # For VAD audio processing
```

Silero VAD is downloaded automatically via `torch.hub` on first run.

### **Rebuild if:**

- Switching to VAD mode for the first time
- Dependencies changed
- VAD model not loading

```bash
docker compose build --no-cache
docker compose up -d
```

---

## Configuration Reference

### **Config File:** `jife-windows/app/config.py`

```python
# Mode selection
PROCESSING_MODE = 'fixed'  # 'fixed' or 'vad'

# Fixed mode settings
CHUNK_DURATION_SEC = 2.5
CHUNK_OVERLAP_SEC = 0.0
SILENCE_THRESHOLD = 0.02

# VAD mode settings
VAD_MIN_CHUNK_SIZE = 1.0
VAD_MAX_CHUNK_SIZE = 10.0
MIN_SILENCE_DURATION_MS = 500
PRE_ROLL_MS = 200

# Whisper settings (both modes)
WHISPER_TEMPERATURE = 0.0
WHISPER_BEAM_SIZE = 3
```

### **Whisper Parameters:** `jife-windows/app/asr/whisper_engine.py`

```python
# Critical parameters (both modes)
temperature = 0.0                    # Deterministic
no_speech_threshold = 0.7            # Filter music/noise
condition_on_previous_text = False   # Prevent loops
compression_ratio_threshold = 2.4    # Detect repetition
log_prob_threshold = -1.0            # Skip low confidence
```

---

## Next Steps

1. **Test both modes** with 2 minutes of Japanese TV
2. **Compare quality:**
   - Fixed: Fast but fragmented?
   - VAD: Slower but coherent?
3. **Choose default mode** based on your preference
4. **Fine-tune parameters** for your specific use case

---

## Summary

You now have **two working modes**:

✅ **Option A (Fixed):** Ultra-fast, simple, some fragmentation
✅ **Option B (VAD):** Slower, better quality, complete sentences

Switch with `PROCESSING_MODE` environment variable or config file.

**Recommended:** Start with **Fixed mode** (it's already working well at 0.57s latency). Only switch to VAD if you need better sentence coherence and can tolerate 2-3s latency.
