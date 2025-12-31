import sounddevice as sd
import numpy as np
import wave
from scipy import signal

print("Recording 5 seconds of audio...")
# Record at native 48kHz
data_48k = sd.rec(int(5 * 48000), samplerate=48000, channels=1, dtype=np.float32, device=0)
sd.wait()

# Save native 48kHz version
with wave.open('/tmp/debug_48k.wav', 'w') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)  # 16-bit
    wf.setframerate(48000)
    # Convert float32 to int16
    audio_int16 = (data_48k * 32767).astype(np.int16)
    wf.writeframes(audio_int16.tobytes())

# Resample to 16kHz using scipy (same as the app)
data_16k = signal.resample_poly(data_48k.flatten(), 1, 3).astype(np.float32)

# Save resampled 16kHz version
with wave.open('/tmp/debug_16k.wav', 'w') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(16000)
    audio_int16 = (data_16k * 32767).astype(np.int16)
    wf.writeframes(audio_int16.tobytes())

print(f"Saved:")
print(f"  /tmp/debug_48k.wav - native 48kHz capture")
print(f"  /tmp/debug_16k.wav - resampled 16kHz (what Whisper sees)")
print(f"RMS levels:")
print(f"  48kHz: {np.sqrt(np.mean(data_48k**2)):.4f}")
print(f"  16kHz: {np.sqrt(np.mean(data_16k**2)):.4f}")
