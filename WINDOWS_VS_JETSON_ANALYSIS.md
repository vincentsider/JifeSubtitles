# Windows vs Jetson Implementation Analysis

**Date:** 2025-12-31
**Analysis:** Comparing what was done for Windows and impact on Jetson

---

## Question 1: Did Windows Changes Break Jetson?

### **Answer: NO ❌ - Jetson is completely isolated**

**Why:**
- **Separate directories:** `jife-windows/` vs `subtitle-product/`
- **Separate Docker configs:** Different Dockerfiles and docker-compose.yml
- **Shared code modules are COMPATIBLE:** Changes to `app/` code work for both

### **What's Platform-Specific:**

| Component | Jetson | Windows | Compatibility |
|-----------|--------|---------|---------------|
| **Docker base** | `l4t-base:r36.4.0` (Jetson-specific) | `cuda:12.1.0` (NVIDIA GPU) | ❌ Different |
| **Audio routing** | `/dev/snd` direct | PulseAudio via WSL | ❌ Different |
| **GPU runtime** | `runtime: nvidia` | `deploy.resources` | ⚠️ Different syntax |
| **Default model** | `small` | `large-v3` | ✅ Just config |
| **Compute type** | `int8` | `float16` | ✅ Just config |
| **Beam size** | `1` (Jetson) | `10` (Windows) | ✅ Just config |

### **What's Shared (app/ code):**

| File | Jetson | Windows | Status |
|------|--------|---------|--------|
| `app/config.py` | ❌ Separate copy | ❌ Separate copy | **DIVERGED** |
| `app/main.py` | ❌ Separate copy | ❌ Separate copy | **DIVERGED** |
| `app/asr/whisper_engine.py` | 354 lines | 640 lines | **DIVERGED** |
| `app/audio/capture.py` | 10,269 bytes | 10,897 bytes | **SIMILAR** |
| `app/audio/vad_processor.py` | ❌ MISSING | ✅ EXISTS | **NEW** |
| `app/web/` | ✅ Shared | ✅ Shared | **SAME** |

**Conclusion:** Jetson code is UNTOUCHED. No risk of breaking it.

---

## Question 2: What Should We Port to Jetson?

### **✅ SHOULD Port (Beneficial):**

#### **1. Hallucination Filtering Improvements**
**File:** `whisper_engine.py` - Lines 20-60 (HALLUCINATION_PATTERNS)

**Windows has:**
```python
# Added patterns
r"^i'?m? (going to|gonna) kill you[\.!?, ]*$",
r"^i'?m? (going to|gonna) die[\.!?, ]*$",
r"^i don'?t know[\.!?, ]*$",
```

**Jetson should get:** ✅ YES
- These are common Whisper hallucinations on music/silence
- Platform-independent
- Will reduce garbage output on Jetson too

---

#### **2. Whisper Parameter Tuning**
**File:** `whisper_engine.py` - Whisper transcribe() call

**Windows has:**
```python
temperature=0.0,                     # Deterministic output
no_speech_threshold=0.5,             # Balanced (was 0.7, too high)
hallucination_silence_threshold=2.0, # More aggressive
condition_on_previous_text=False,    # Prevents repetition loops
```

**Jetson currently has:** Unknown (need to check whisper_engine.py)

**Should port:** ✅ YES
- `temperature=0.0` → deterministic (good for both)
- `condition_on_previous_text=False` → prevents loops (critical!)
- `no_speech_threshold=0.5` → balanced filtering

---

#### **3. Duplicate Detection in Processing Loop**
**File:** `main.py` - Processing loop

**Windows has:**
```python
# Simple duplicate detection
with last_output_lock:
    if text == last_output_text:
        logger.debug(f"Skipping duplicate: '{text[:40]}...'")
        continue
    last_output_text = text
```

**Jetson should get:** ✅ YES
- Prevents showing same subtitle twice
- Simple, no performance cost
- Works with any chunk size

---

#### **4. Footer Status Display**
**File:** `web/templates/index.html`

**Windows has:**
```html
<div id="footer">
    <span id="count">0</span> subtitles | <span id="latency">-</span>ms |
    Mode: <span id="mode">-</span> |
    Chunk: <span id="chunkSize">-</span>s
</div>
```

**Jetson should get:** ✅ YES
- Useful for debugging
- User can see system status
- Platform-independent

---

### **⚠️ MAYBE Port (Depends on Testing):**

#### **1. Increased Chunk Size**
**Windows:** 3.5s
**Jetson:** 3.0s

**Should port:** ⚠️ MAYBE
- **Pro:** Better context, more complete sentences
- **Con:** Jetson has less memory (7GB vs 16GB)
- **Recommendation:** Test 3.5s on Jetson, watch memory usage

---

#### **2. VAD Mode (vad_processor.py)**
**Windows:** Implemented but NOT recommended (too slow for anime)
**Jetson:** Doesn't have it

**Should port:** ❌ NO
- We found VAD mode is BAD for anime (delays, missed dialogue)
- Fixed chunk mode is better for real-time
- Would add complexity for no benefit
- Silero VAD adds dependency (torch)

---

### **❌ SHOULD NOT Port (Platform-Specific):**

#### **1. Beam Size = 10**
**Windows:** 10
**Jetson:** 1 (from docker-compose.yml: `WHISPER_BEAM_SIZE=1`)

**Should port:** ❌ NO
- Jetson Orin Nano has MUCH less GPU power than RTX 4080
- beam_size=10 would slow Jetson to a crawl
- beam_size=1 is correct for Jetson (speed priority)
- **Keep Jetson at beam_size=1 or MAX=3**

---

#### **2. Model = large-v3 + FP16**
**Windows:** large-v3 + float16
**Jetson:** small + int8 (or large-v3 + int8 from docker-compose)

**Should port:** ❌ NO
- Jetson has 7GB shared memory (vs 16GB dedicated on RTX 4080)
- large-v3 + float16 might not fit or be too slow
- **Jetson should use:**
  - `large-v3` + `int8` (best quality that fits)
  - OR `small` + `int8_float16` (if large-v3 is too slow)

---

#### **3. PulseAudio + WSL-specific audio routing**
**Windows:** Uses `/mnt/wslg/PulseServer`
**Jetson:** Direct ALSA `/dev/snd`

**Should port:** ❌ NO
- Completely different audio stack
- Jetson's direct ALSA is better (lower latency)

---

## Recommended Actions for Jetson:

### **High Priority (Do These):**

1. ✅ **Add hallucination patterns** to `subtitle-product/app/asr/whisper_engine.py`
   - Copy patterns from Windows (lines 58-60)

2. ✅ **Add Whisper parameter tuning** to `subtitle-product/app/asr/whisper_engine.py`
   - `temperature=0.0`
   - `condition_on_previous_text=False`
   - `no_speech_threshold=0.5`

3. ✅ **Add duplicate detection** to `subtitle-product/app/main.py`
   - Simple `if text == last_text: skip` logic

4. ✅ **Add status footer** to `subtitle-product/app/web/templates/index.html`
   - Shows mode, chunk size, subtitle count

### **Medium Priority (Test These):**

5. ⚠️ **Test chunk_size=3.5s** on Jetson
   - Monitor memory usage
   - If stable, update; if OOM, keep 3.0s

### **Low Priority (Skip These):**

6. ❌ **Skip VAD mode** - Not useful for anime
7. ❌ **Keep beam_size=1** - Jetson can't handle 10
8. ❌ **Keep int8** - Jetson needs quantization

---

## Summary Table:

| Feature | Windows | Jetson Current | Jetson Should Be | Priority |
|---------|---------|----------------|------------------|----------|
| **Hallucination filters** | Extended | Basic | Extended | ✅ HIGH |
| **temperature** | 0.0 | ? | 0.0 | ✅ HIGH |
| **condition_on_previous_text** | False | ? | False | ✅ HIGH |
| **no_speech_threshold** | 0.5 | ? | 0.5 | ✅ HIGH |
| **Duplicate detection** | Yes | No | Yes | ✅ HIGH |
| **Status footer** | Yes | ? | Yes | ✅ HIGH |
| **chunk_size** | 3.5s | 3.0s | Test 3.5s | ⚠️ MEDIUM |
| **beam_size** | 10 | 1 | Keep 1 | ❌ SKIP |
| **Model** | large-v3 FP16 | large-v3 int8 | Keep int8 | ❌ SKIP |
| **VAD mode** | Implemented | No | Skip | ❌ SKIP |

---

## Key Learnings from Windows Work:

### **What Worked:**
1. ✅ **Longer chunks (3.5s)** = more complete sentences
2. ✅ **Higher beam size** = better quality (but only on powerful GPU)
3. ✅ **Better hallucination filtering** = cleaner output
4. ✅ **temperature=0.0** = deterministic, reproducible
5. ✅ **Simple duplicate detection** = prevents repetition

### **What Didn't Work:**
1. ❌ **VAD mode** = too slow, delayed, missed fast dialogue
2. ❌ **Overlapping chunks** = caused repetition loops
3. ❌ **Sentence buffering** = held text too long
4. ❌ **condition_on_previous_text=True** = caused infinite loops

### **Platform Differences to Respect:**
1. **GPU Power:** RTX 4080 >> Jetson Orin Nano
   - Windows can use beam=10, Jetson must stay at beam=1-3
2. **Memory:** Windows 16GB dedicated vs Jetson 7GB shared
   - Windows can use FP16, Jetson needs INT8
3. **Audio:** Different stacks, don't mix them

---

## Conclusion:

**The codebases have diverged** but in a **controlled, intentional way**. Each platform has optimizations for its hardware:

- **Windows:** Optimized for RTX 4080 (high quality, high resources)
- **Jetson:** Optimized for embedded (efficiency, low latency)

**Cross-platform learnings** (hallucination filtering, parameter tuning, duplicate detection) should be shared.

**Platform-specific optimizations** (beam size, model quantization, VAD) should stay separate.

**No Jetson code was broken.** Everything is safe. ✅
