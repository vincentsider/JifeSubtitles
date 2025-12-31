"""Test OpenAI with a small 10-second sample"""
import wave
import numpy as np
import os
from pathlib import Path

# Load .env
env_file = Path('.env')
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

api_key = os.environ.get('OPENAI_API_KEY')

# Load first 10 seconds of audio
print("Loading test_audio.wav...")
with wave.open('test_audio.wav', 'rb') as w:
    frames = w.readframes(16000 * 10)  # 10 seconds
    audio = np.frombuffer(frames, dtype=np.int16)

print(f"Sample: 10 seconds, {len(audio)} samples")
print(f"Stats: min={audio.min()}, max={audio.max()}, mean={audio.mean():.1f}, std={audio.std():.1f}")

# Save small sample
print("Saving 10-second sample...")
with wave.open('test_10sec.wav', 'wb') as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(16000)
    w.writeframes(audio.tobytes())

print(f"Saved to test_10sec.wav ({Path('test_10sec.wav').stat().st_size} bytes)")

# Test with OpenAI
print("\nTesting with OpenAI...")
try:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    with open('test_10sec.wav', 'rb') as f:
        response = client.audio.translations.create(
            model="whisper-1",
            file=f,
        )

    print(f"\nOpenAI response: '{response.text}'")
    print(f"Length: {len(response.text)}")

    if response.text:
        print("\nSUCCESS! OpenAI transcribed the audio.")
    else:
        print("\nFAILURE: OpenAI returned empty text.")
        print("The audio file contains only silence or music.")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
