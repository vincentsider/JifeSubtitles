"""Verify the recorded audio has actual speech using faster-whisper"""
import wave
import numpy as np

# Load audio
print("Loading test_audio.wav...")
with wave.open('test_audio.wav', 'rb') as w:
    frames = w.readframes(w.getnframes())
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

print(f"Audio shape: {audio.shape}")
print(f"Duration: {len(audio)/16000:.1f}s")
print(f"Min: {audio.min():.4f}, Max: {audio.max():.4f}")
print(f"Mean: {audio.mean():.4f}, Std: {audio.std():.4f}")

# Test with faster-whisper
print("\nTesting with faster-whisper...")
try:
    from faster_whisper import WhisperModel

    model = WhisperModel("small", device="cpu", compute_type="int8")

    print("Transcribing first 30 seconds...")
    segments, info = model.transcribe(
        audio[:16000*30],  # First 30s
        language="ja",
        task="translate"
    )

    print(f"\nDetected language: {info.language} (prob: {info.language_probability:.2f})")

    print("\nTranscription:")
    for segment in segments:
        print(f"[{segment.start:.1f}s -> {segment.end:.1f}s] {segment.text}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
