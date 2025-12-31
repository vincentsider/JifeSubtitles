# Translation Engine Options

My "ultimate" offline recommendation on an RTX 4080 (16GB)

## Option A (baseline): Whisper with direct translation
**Backend:** `faster_whisper`

Whisper large-v3 with `task=translate` (Japanese audio -> English text directly).
- Fast, single model inference
- Good quality for clear audio
- May struggle with messy TV audio

## Option B (best for messy audio): SeamlessM4T v2
**Backend:** `seamless_m4t`

Run Meta SeamlessM4T v2 directly as speech-to-text translation (Japanese audio -> English text).
It's specifically built for multimodal translation (speech<->text) rather than "ASR model + translation hack."

Why it's the best fit for Japanese TV audio:
- Designed for speech translation, not just transcription
- Generally more robust than a two-model pipeline when audio is messy (TV often is)
- Still not magic, but usually a clear step up

Latency reality: you'll still want ~2-4s buffering (sliding window) for coherent subtitles.

**Status:** Implemented in `seamless_engine.py`

## Option C (highest quality): Whisper + SeamlessM4T Pipeline
**Backend:** `pipeline`

Two-stage pipeline:
1. Whisper transcribes Japanese audio -> Japanese text (using `task=transcribe`, `language=ja`)
2. SeamlessM4T v2 translates Japanese text -> English text (text-to-text mode)

Why this might give best results:
- Whisper in native transcribe mode is more accurate than translate mode
- Uses `condition_on_previous_text=true` for better context continuity
- SeamlessM4T's text-to-text translation is its strong suit
- Can see/debug intermediate Japanese text

Trade-offs:
- Higher latency (~2x, two model inferences per chunk)
- More VRAM usage (~13-14GB for both models)
- More failure points

**Status:** Implemented in `pipeline_engine.py`

---

## Switching Between Options

### Via Frontend (recommended)
Use the model dropdown in the web interface to switch between options in real-time.

### Via Environment Variable
```bash
# Option A (default)
WHISPER_BACKEND=faster_whisper docker compose up -d

# Option B
WHISPER_BACKEND=seamless_m4t docker compose up -d

# Option C
WHISPER_BACKEND=pipeline docker compose up -d
```
