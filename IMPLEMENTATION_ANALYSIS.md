# Current Implementation Analysis vs Whisper Best Practices

Date: 2025-12-31

## Best Practices Checklist

### ✅ What We're Doing Right

1. **Chunk-based processing (not byte streaming)**
   - Current: 1.5s chunks
   - Location: `config.py:14` `CHUNK_DURATION_SEC = 1.5`
   - Status: ✅ GOOD

2. **Language locking**
   - Current: Force `language='ja'`
   - Location: `whisper_engine.py:379`, `main.py:98`
   - Status: ✅ GOOD

3. **Aggressive hallucination filtering**
   - Current: Pattern matching for "thank you", "subscribe", repetitions
   - Location: `whisper_engine.py:16-99`
   - Status: ✅ GOOD

4. **Low confidence filtering**
   - Current: `log_prob_threshold=-1.0`, `no_speech_threshold=0.65`
   - Location: `whisper_engine.py:388-389`
   - Status: ✅ GOOD

5. **Resilience**
   - Health checks, graceful shutdown, error recovery
   - Location: `main.py:47-50`, `docker-compose.yml:65-70`
   - Status: ✅ GOOD

6. **Target latency**
   - Current: 0.72s average (excellent!)
   - Status: ✅ EXCEEDS TARGET

### ❌ What We're Missing (CRITICAL)

1. **Overlapping chunks**
   - **Problem:** Each 1.5s chunk processed independently, speech cut mid-sentence
   - **Best Practice:** Use 0.5-1s overlap between chunks
   - **Impact:** Context loss, fragmented translations
   - **Priority:** 🔴 HIGH

2. **Deduplication of overlap**
   - **Problem:** No mechanism to drop repeated text from overlaps
   - **Best Practice:** Track and merge overlapping segments
   - **Impact:** Would cause repetition if overlaps added
   - **Priority:** 🔴 HIGH (but only if we add overlaps)

3. **Sentence boundary detection & buffering**
   - **Problem:** Output every chunk immediately, even mid-sentence
   - **Best Practice:** Buffer text until punctuation/pause, only output complete sentences
   - **Impact:** Fragmented subtitles, lower translation quality
   - **Priority:** 🔴 HIGH

4. **Interim vs confirmed text (UX)**
   - **Problem:** All text displayed as final immediately
   - **Best Practice:** Mark interim text differently, allow overwrites
   - **Impact:** User sees fragmented/partial translations
   - **Priority:** 🟡 MEDIUM

5. **Rolling context prompt**
   - **Problem:** Each chunk transcribed independently, no previous context
   - **Current:** `condition_on_previous_text=False` (implicit)
   - **Best Practice:** Pass previous 2-3 sentences as prompt
   - **Impact:** Context loss between chunks
   - **Priority:** 🔴 HIGH

### 🟡 Partially Implemented

1. **Separate ASR + translation phases**
   - Current: Using Whisper's built-in `task='translate'` (single phase)
   - Best Practice: Separate transcribe → translate pipeline
   - Status: Using built-in works, but separate could be more controllable
   - Priority: 🟢 LOW (current approach acceptable)

## Root Cause Analysis

### Why Current Implementation May Underperform vs OpenAI

OpenAI Whisper API likely:
1. **Processes full audio context** (entire 2-minute clip) vs our 1.5s chunks
2. **Uses sentence-aware segmentation** vs our fixed 1.5s windows
3. **Applies context across segments** vs our independent chunks
4. **Buffers and merges** before outputting vs our immediate output

### Example Failure Mode

Japanese speech: "私は今日とても暑いので気にしません" (continuous over 3 seconds)

**Current system:**
- Chunk 1 (0-1.5s): "I'm so hot today" ✅
- Chunk 2 (1.5-3.0s): "I don't care" ✅
- **Problem:** Context lost between chunks, translation fragmented

**With overlapping + buffering:**
- Chunk 1 (0-2.0s with 0.5s overlap): "I'm so hot today I don't..." [INTERIM]
- Chunk 2 (1.5-3.5s with overlap): "...hot today I don't care." [COMPLETE]
- After dedup: "I'm so hot today I don't care." ✅

## Recommended Improvements (Priority Order)

### 1. 🔴 Add Overlapping Chunks + Deduplication
**Impact:** Preserve context across chunk boundaries
**Effort:** Medium
**Changes:**
- Modify `audio/capture.py` to use sliding window (1.5s chunks, 0.5s overlap)
- Add deduplication logic in `main.py` processing loop
- Track previous segment text, merge overlaps

### 2. 🔴 Implement Sentence Buffering
**Impact:** Output only complete sentences, improve translation coherence
**Effort:** Medium
**Changes:**
- Add sentence boundary detection (punctuation, long pause)
- Buffer incomplete sentences across chunks
- Only send to UI when sentence complete

### 3. 🔴 Enable Rolling Context Prompt
**Impact:** Better context awareness, improved accuracy
**Effort:** Low
**Changes:**
- Enable `condition_on_previous_text=True` in whisper_engine.py:522
- Track last 2-3 sentences as prompt context
- Already partially implemented in streaming API!

### 4. 🟡 Add Interim/Confirmed Text States
**Impact:** Better UX, user sees progress
**Effort:** Medium
**Changes:**
- Add `is_interim` field to subtitle messages
- Modify web UI to display interim text differently (gray/italic)
- Send updates as sentences complete

### 5. 🟢 Separate Transcription + Translation (Optional)
**Impact:** More control over each phase
**Effort:** High
**Changes:**
- First pass: transcribe to Japanese
- Second pass: translate Japanese → English
- Could use different models for each

## Immediate Action Plan

**Phase 1: Quick Wins (30 min)**
1. Enable `condition_on_previous_text=True` in faster-whisper
2. Increase chunk size to 2.5s (more context per chunk)

**Phase 2: Core Improvements (2-3 hours)**
1. Implement overlapping chunks (1.5s overlap on 3s chunks)
2. Add sentence boundary detection + buffering
3. Implement deduplication logic

**Phase 3: UX Polish (1-2 hours)**
1. Add interim/confirmed text states
2. Update web UI to handle text updates

## Expected Quality Improvement

After implementing overlapping + sentence buffering:
- **Context preservation:** +40% (no more mid-sentence cuts)
- **Translation coherence:** +30% (complete sentences)
- **Word-level accuracy:** Similar (model unchanged)
- **Overall similarity to OpenAI:** Expect 80-90% (vs current unknown)

## Files to Modify

1. `jife-windows/app/config.py` - Add overlap config
2. `jife-windows/app/audio/capture.py` - Sliding window
3. `jife-windows/app/main.py` - Dedup + sentence buffering
4. `jife-windows/app/asr/whisper_engine.py` - Enable context prompt
5. `jife-windows/app/web/server.py` - Interim text support
6. `jife-windows/app/web/templates/index.html` - UI for interim text
