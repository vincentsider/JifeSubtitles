# Whisper Real-Time Japanese Translation: Research Findings & Implementation Plan

**Date:** 2025-12-31
**Research Goal:** Find proven best practices for Japanese→English real-time subtitles with Whisper

---

## Executive Summary

After researching academic papers, production implementations, and community discussions, I've identified **WHY my previous implementation failed** and **what actually works** for real-time Whisper streaming.

**Key Finding:** The issue wasn't that best practices don't work—it's that I implemented them incorrectly by mixing incompatible approaches.

---

## What I Did Wrong

### ❌ **Fatal Mistake #1: Used `condition_on_previous_text=True` with short chunks**

**The Problem:**
- When `condition_on_previous_text=True`, Whisper uses previous output as context
- With 1.5s chunks, if a chunk has silence/noise, Whisper can't decode anything
- Instead of outputting nothing, it REPEATS the previous output (gets stuck in a loop)
- This is why we saw "I don't know what to do." repeated 20+ times

**Evidence:**
- [OpenAI Whisper Discussion #679](https://github.com/openai/whisper/discussions/679): "When `condition_on_previous_text` is true, Whisper remembers what it output previously and if the current output cannot produce anything, it will just use the last output."
- [OpenAI Whisper Discussion #112](https://github.com/openai/whisper/discussions/112): "The repetition appears systematic—The repeated sentences also have the same duration, as if it was the same tokens/data over and over."

**The Fix:**
- `condition_on_previous_text=False` for short chunks (< 5 seconds)
- Only use `condition_on_previous_text=True` with VAD-based segmentation (natural speech boundaries)

### ❌ **Fatal Mistake #2: Overlapping chunks WITHOUT proper deduplication**

**The Problem:**
- My deduplication compared word-by-word overlap at chunk boundaries
- But when Whisper gets stuck in repetition loop, it outputs IDENTICAL text (not overlapping text)
- My deduplication didn't detect "text A" followed by "text A" (identical)
- It only detected "...end of A" at start of next chunk (overlapping)

**The Fix:**
- Need BOTH deduplication strategies:
  1. Remove overlapping words at boundaries (what I had)
  2. Skip completely identical consecutive outputs (what I was missing)

### ❌ **Fatal Mistake #3: Sentence buffering with incompatible chunking**

**The Problem:**
- 1.5s chunks are too short to contain complete sentences
- Buffering logic held text waiting for punctuation that never came
- Text accumulated indefinitely, never displayed

**The Fix:**
- Use VAD-based segmentation (natural speech pauses) instead of fixed 1.5s chunks
- OR don't buffer at all—output immediately and let user read partial sentences

---

## What Actually Works: Production Systems

### 🏆 **Best Approach: VAD-Based Segmentation (Recommended)**

**Implementation:** [ufal/whisper_streaming](https://github.com/ufal/whisper_streaming) (Academic, proven)

**How It Works:**
1. Use Silero VAD to detect speech boundaries (where people pause)
2. Process natural utterances (2-10 seconds typically) instead of fixed chunks
3. Use LocalAgreement policy: output text only when consecutive chunks agree
4. Latency: **3.3 seconds** on European Parliament corpus

**Key Parameters:**
```python
--min-chunk-size 1          # Wait at least 1s before processing
--vad-chunk-size 0.5        # VAD sample size (500ms)
--buffer_trimming_sec 15    # Trim buffer after 15s to prevent memory issues
```

**Why It Works:**
- Natural speech segments have complete thoughts (fewer mid-sentence cuts)
- Pauses between sentences provide natural boundaries for buffering
- Chunks are longer (2-10s) so `condition_on_previous_text` doesn't cause loops
- Agreement policy prevents outputting unstable transcriptions

**Architecture:**
```python
from whisper_streaming import OnlineASRProcessor

online = OnlineASRProcessor(asr)
while audio_continues:
    online.insert_audio_chunk(audio)
    output = online.process_iter()  # Only outputs confirmed text
online.finish()
```

### 🥈 **Alternative: Fixed Chunks with NO Context (What We Should Use)**

**Implementation:** Our current system, but with correct parameters

**How It Works:**
1. Process fixed 1.5-3s chunks (what we already do)
2. **Disable context completely** (`condition_on_previous_text=False`)
3. Output immediately, no buffering
4. Accept that some sentences will be fragmented

**Key Parameters:**
```python
# Whisper settings
condition_on_previous_text = False  # ✅ CRITICAL - prevents repetition loops
initial_prompt = None               # ✅ No context
compression_ratio_threshold = 2.4   # ✅ Detect repetitive output
no_speech_threshold = 0.6           # ✅ Skip silence/music
logprob_threshold = -1.0            # ✅ Skip low confidence
temperature = 0                     # ✅ Deterministic (no randomness)

# Audio settings
chunk_duration = 2.5                # ✅ Longer chunks = more context per chunk
chunk_overlap = 0.0                 # ✅ NO overlap (we already have this)
```

**Why It Works:**
- Each chunk is independent—no risk of repetition loops
- Longer chunks (2.5s instead of 1.5s) give Whisper more context per chunk
- Whisper's built-in hallucination filtering prevents garbage output
- Simple, predictable, low latency

**Trade-offs:**
- ❌ May fragment sentences at chunk boundaries
- ❌ Less coherent than VAD approach
- ✅ Ultra-low latency (< 1 second)
- ✅ Simple implementation (no VAD dependency)

---

## Japanese-Specific Findings

### Model Selection

**Best Models for Japanese:**
- **Medium** (244M params): Best balance for real-time (what we use ✅)
- **Large-v2**: Better than large-v3 for Japanese (less hallucination)
- **Kotoba-Whisper**: Japanese-optimized, 6.3x faster than large-v3 ([Hugging Face model](https://huggingface.co/kotoba-tech/kotoba-whisper-bilingual-v1.0))

**Translation Task:**
- `task='translate'` (Japanese→English) is correct ✅
- Direct translation is better than transcribe→translate pipeline for real-time

### Japanese Hallucination Patterns

**Common Issues:**
- Music and non-speech audio trigger repetition ([Discussion #112](https://github.com/openai/whisper/discussions/112))
- Anime/TV often has background music mixed with dialogue
- Solution: Increase `no_speech_threshold` to 0.65-0.7 for Japanese TV

**Parameters Tuned for Japanese:**
```python
language = 'ja'                     # ✅ Lock source language
task = 'translate'                  # ✅ Direct JP→EN
no_speech_threshold = 0.65          # ✅ Higher for TV/anime (music filtering)
compression_ratio_threshold = 2.4   # ✅ Detect repetition
beam_size = 3                       # ✅ Balance speed/quality
temperature = 0                     # ✅ Deterministic output
```

---

## Recommended Implementation Plan

### **Option A: Quick Fix (30 minutes)**

Keep our current architecture, just fix the parameters:

**Changes Needed:**
1. ✅ `condition_on_previous_text = False` (already done)
2. ✅ `chunk_overlap = 0.0` (already done)
3. ❌ Change `chunk_duration = 2.5` (currently 1.5s—too short)
4. ❌ Add `temperature = 0` (for deterministic output)
5. ❌ Increase `no_speech_threshold = 0.7` (for Japanese TV with music)
6. ❌ Remove all sentence buffering logic (output immediately)
7. ❌ Add simple duplicate detection: `if text == last_text: skip`

**Expected Results:**
- ✅ No more repetition loops
- ✅ Stable, predictable output
- ✅ Low latency (0.5-1s)
- ❌ Some sentences fragmented at 2.5s boundaries
- ❌ Less coherent than VAD approach

**Risk:** Low (mostly parameter changes)

### **Option B: Production-Quality VAD (4-6 hours)**

Implement proper VAD-based segmentation:

**Changes Needed:**
1. Add Silero VAD dependency
2. Replace fixed chunking with VAD-based segmentation
3. Implement LocalAgreement confirmation policy
4. Enable context with proper safeguards
5. Add sentence-based buffering (now safe because chunks are natural utterances)

**Expected Results:**
- ✅ Complete sentences (natural boundaries)
- ✅ Better coherence across segments
- ✅ Context-aware translation
- ❌ Slightly higher latency (2-3s instead of 0.5-1s)
- ❌ More complex implementation

**Risk:** Medium (significant refactoring)

---

## My Recommendation

**Start with Option A (Quick Fix).**

**Reasoning:**
1. We're already at 0.57s average latency—this is EXCELLENT
2. The main issue is repetition and random output, not latency
3. Option A fixes repetition with minimal changes
4. We can test Option A in 30 minutes vs 4-6 hours for Option B
5. If Option A quality is good enough, we're done
6. If not, we have the research for Option B

**Immediate Next Steps:**
1. Update config parameters (5 minutes)
2. Simplify processing loop (remove all buffering/dedup logic) (10 minutes)
3. Add simple duplicate detection (5 minutes)
4. Test for 2 minutes with Japanese TV
5. Compare quality with your expectations

---

## Sources

### Academic Papers
- [Turning Whisper into Real-Time Transcription System](https://arxiv.org/html/2307.14743) - Academic research on streaming Whisper

### Production Implementations
- [ufal/whisper_streaming](https://github.com/ufal/whisper_streaming) - VAD-based streaming (recommended)
- [JonathanFly/faster-whisper-livestream-translator](https://github.com/JonathanFly/faster-whisper-livestream-translator) - Livestream translation
- [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) - Our current backend

### Community Discussions
- [OpenAI Whisper Discussion #679](https://github.com/openai/whisper/discussions/679) - Hallucination solutions
- [OpenAI Whisper Discussion #112](https://github.com/openai/whisper/discussions/112) - Repetition issues
- [Transformers Issue #21467](https://github.com/huggingface/transformers/issues/21467) - condition_on_previous_text problems
- [Best prompt for Japanese](https://github.com/openai/whisper/discussions/2151) - Japanese-specific tips

### Models
- [kotoba-whisper-bilingual](https://huggingface.co/kotoba-tech/kotoba-whisper-bilingual-v1.0) - Japanese-optimized model

---

## Conclusion

**The root cause of our issues:**
- Using `condition_on_previous_text=True` with short chunks caused repetition loops
- Sentence buffering with fixed chunks (no natural boundaries) held text indefinitely
- Deduplication didn't detect identical consecutive outputs

**The solution:**
- Disable context completely for short chunks
- Increase chunk size to 2.5s for more context per chunk
- Remove sentence buffering (output immediately)
- Add simple duplicate detection

**This is a parameter fix, not an architecture overhaul.**

We had the right infrastructure (overlapping chunk support, deduplication functions, buffering logic). We just used them with the wrong parameters for our use case.
