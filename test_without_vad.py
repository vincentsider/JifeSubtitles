import wave
import numpy as np
from faster_whisper import WhisperModel

# Load the captured audio
with wave.open('/tmp/debug_16k.wav', 'r') as wf:
    frames = wf.readframes(wf.getnframes())
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0

print(f"Audio: {len(audio)/16000:.1f}s, RMS: {np.sqrt(np.mean(audio**2)):.4f}")

model = WhisperModel("base", device="cuda", compute_type="float16")

print("\n1. WITH VAD (current setup):")
segments, info = model.transcribe(audio, language="ja", task="translate", beam_size=5, vad_filter=True)
text = ' '.join([seg.text for seg in segments]).strip()
print(f"   Language: {info.language} ({info.language_probability:.2f})")
print(f"   Result: '{text}'")

print("\n2. WITHOUT VAD (force process all audio):")
segments, info = model.transcribe(audio, language="ja", task="translate", beam_size=5, vad_filter=False)
text = ' '.join([seg.text for seg in segments]).strip()
print(f"   Language: {info.language} ({info.language_probability:.2f})")
print(f"   Result: '{text}'")

print("\n3. WITHOUT VAD + initial_prompt hint:")
segments, info = model.transcribe(
    audio,
    language="ja",
    task="translate",
    beam_size=5,
    vad_filter=False,
    initial_prompt="Japanese television broadcast dialogue."
)
text = ' '.join([seg.text for seg in segments]).strip()
print(f"   Language: {info.language} ({info.language_probability:.2f})")
print(f"   Result: '{text}'")
