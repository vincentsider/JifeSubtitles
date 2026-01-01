What I’d run on your RTX 4080 (16GB VRAM): “ultimate” offline pipeline


A) Best “quality per latency” local stack (what I’d actually do)
ASR: faster-whisper (Japanese transcription, NOT Whisper translate)

Use large-v3 / large-v3-turbo if you can, but tune for stability (below).

Punctuation restoration (lightweight): optional but very helpful for MT.

MT: MADLAD-400-3B-MT

Run INT8 (or FP16 if VRAM allows comfortably).

Streaming policy: translate only committed text + short rolling context.



This usually beats “Whisper translate” on hard audio once the streaming policy is correct.



Bottom line (for 
your
 constraints: offline, near-real-time, excellent JA→EN)
Keep Whisper as ASR only (transcribe JA), fix streaming stability/commit logic.

Use MADLAD-400-3B-MT (INT8) as your MT first choice on the RTX 4080. 

Don’t translate raw 3-second fragments; translate committed text + short context



Known-good faster-whisper streaming settings (a solid baseline)


These are good starting points for TV audio chaos:



ASR

task="transcribe" and language="ja" (avoid auto language switching)

vad_filter=True (very important for TV)

beam_size=3 to 5 (10 is usually too slow + can destabilize streaming)

temperature=0.0 (start here; raise only if it gets stuck)

If you see repeats/hallucination-like ASR:

condition_on_previous_text=False (often helps for streaming TV)

set stricter thresholds if supported:

no_speech_threshold higher

log_prob_threshold higher

compression_ratio_threshold lower



Chunking

Use overlap/hops:

audio window ~2–4s

hop ~0.2–0.5s

Commit text when stable across 2–3 updates.



MT

Translate committed segments (sentence-ish), not raw live fragments.

Pass ~10–25 prior JA tokens as context (not the entire history).