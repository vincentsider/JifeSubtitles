import sounddevice as sd
import numpy as np

print("=== AVAILABLE AUDIO DEVICES ===")
devices = sd.query_devices()
for i, d in enumerate(devices):
    print(f"{i}: {d['name']} (in:{d['max_input_channels']} out:{d['max_output_channels']}) @ {d['default_samplerate']}Hz")

print("\n=== RECORDING 3 SECONDS FROM DEVICE 0 ===")
data = sd.rec(int(3 * 16000), samplerate=16000, channels=1, dtype=np.float32, device=0)
sd.wait()

rms = np.sqrt(np.mean(data**2))
print(f"RMS level: {rms:.4f}")
print(f"Min: {data.min():.4f}, Max: {data.max():.4f}")
print(f"Peak amplitude: {np.abs(data).max():.4f}")

# Check if it's actual audio or just noise
if rms < 0.001:
    print("\n⚠️  VERY LOW AUDIO - likely no input connected")
elif rms > 0.1:
    print("\n✓ GOOD AUDIO LEVELS - input is working")
else:
    print("\n⚠️  WEAK AUDIO - check input levels")
