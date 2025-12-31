import sounddevice as sd
import numpy as np
import wave
from scipy import signal
from faster_whisper import WhisperModel

print("=" * 60)
print("MAKE SURE JAPANESE DIALOGUE IS SPEAKING NOW!")
print("Recording in 3 seconds...")
print("=" * 60)
import time
time.sleep(3)

print("\nRecording 5 seconds...")
data_48k = sd.rec(int(5 * 48000), samplerate=48000, channels=1, dtype=np.float32, device=0)
sd.wait()

# Resample
data_16k = signal.resample_poly(data_48k.flatten(), 1, 3).astype(np.float32)
rms = np.sqrt(np.mean(data_16k**2))
print(f"Captured: RMS={rms:.4f}")

# Transcribe immediately
print("\nLoading Whisper...")
model = WhisperModel("base", device="cuda", compute_type="float16")

print("Transcribing WITHOUT VAD...")
segments, info = model.transcribe(data_16k, language="ja", task="translate", beam_size=5, vad_filter=False)
text = ' '.join([seg.text for seg in segments]).strip()
print(f"\nDetected language: {info.language} (confidence: {info.language_probability:.2f})")
print(f"Translation: '{text}'")

if not text or len(text) < 5:
    print("\n⚠️  NO SPEECH DETECTED - audio might be music/effects only")
else:
    print("\n✓ Speech transcribed successfully!")
