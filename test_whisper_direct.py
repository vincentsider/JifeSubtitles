import wave
import numpy as np
from faster_whisper import WhisperModel

# Load the captured audio
with wave.open('/tmp/debug_16k.wav', 'r') as wf:
    frames = wf.readframes(wf.getnframes())
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0

print(f"Audio loaded: {len(audio)} samples ({len(audio)/16000:.1f} seconds)")
print(f"RMS: {np.sqrt(np.mean(audio**2)):.4f}")

# Load model and transcribe
print("\nLoading faster-whisper model...")
model = WhisperModel("base", device="cuda", compute_type="float16")

print("\nTranscribing with task='translate', language='ja' (Japanese->English):")
segments, info = model.transcribe(audio, language="ja", task="translate", beam_size=5, vad_filter=True)
text = ' '.join([seg.text for seg in segments]).strip()
print(f"  Detected language: {info.language} (probability: {info.language_probability:.2f})")
print(f"  Result: '{text}'")

print("\nTranscribing with task='transcribe', language='ja' (Japanese->Japanese):")
segments, info = model.transcribe(audio, language="ja", task="transcribe", beam_size=5, vad_filter=True)
text = ' '.join([seg.text for seg in segments]).strip()
print(f"  Detected language: {info.language} (probability: {info.language_probability:.2f})")
print(f"  Result: '{text}'")

print("\nTranscribing with language=None (auto-detect):")
segments, info = model.transcribe(audio, task="transcribe", beam_size=5, vad_filter=True)
text = ' '.join([seg.text for seg in segments]).strip()
print(f"  Detected language: {info.language} (probability: {info.language_probability:.2f})")
print(f"  Result: '{text}'")
