#!/usr/bin/env python3
"""
Record audio EXACTLY as the subtitle system captures it.
This runs INSIDE the Docker container and uses the SAME AudioCapture class.
"""
import sys
import wave
import numpy as np
from pathlib import Path

sys.path.insert(0, '/app')

from app.config import get_config
from app.audio import AudioCapture

def record_audio(duration_sec=120, output_file='/tmp/recorded_audio.wav'):
    """Record audio using SAME method as subtitle system"""
    config = get_config()

    print(f"Recording {duration_sec} seconds of audio...", flush=True)
    print(f"Device: {config.AUDIO_DEVICE}", flush=True)
    print(f"Sample rate: {config.SAMPLE_RATE}Hz", flush=True)
    print(f"Channels: {config.CHANNELS}", flush=True)
    print(f"Output: {output_file}", flush=True)

    # Use EXACT same setup as subtitle system
    import queue
    audio_queue = queue.Queue(maxsize=config.MAX_QUEUE_SIZE)

    # Create audio capture with IDENTICAL settings to main.py
    capture = AudioCapture(
        device=config.AUDIO_DEVICE,
        sample_rate=config.SAMPLE_RATE,
        channels=config.CHANNELS,
        chunk_duration=config.CHUNK_DURATION_SEC,
        output_queue=audio_queue,
    )

    # Start capture
    capture.start()

    # Collect chunks
    import time
    start_time = time.time()
    chunks = []

    print("\nRecording...", flush=True)
    while time.time() - start_time < duration_sec:
        try:
            chunk = audio_queue.get(timeout=1.0)
            chunks.append(chunk)
            elapsed = int(time.time() - start_time)
            remaining = duration_sec - elapsed
            print(f"\rRecorded {elapsed}s / {duration_sec}s ({remaining}s remaining)", end='', flush=True)
        except queue.Empty:
            continue

    print("\n\nStopping capture...", flush=True)
    capture.stop()

    if not chunks:
        print("ERROR: No audio chunks captured!", flush=True)
        sys.exit(1)

    # Concatenate all chunks
    print("Concatenating audio...", flush=True)
    audio_data = np.concatenate(chunks)

    # Check audio statistics
    print(f"Audio stats: min={audio_data.min():.4f}, max={audio_data.max():.4f}, mean={audio_data.mean():.4f}, std={audio_data.std():.4f}", flush=True)

    # Convert to int16 for WAV
    audio_int16 = (audio_data * 32767).astype(np.int16)

    # Save to WAV file
    print(f"Saving to {output_file}...", flush=True)
    with wave.open(output_file, 'wb') as wf:
        wf.setnchannels(config.CHANNELS)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(config.SAMPLE_RATE)
        wf.writeframes(audio_int16.tobytes())

    file_size = Path(output_file).stat().st_size
    print(f"\n[OK] Recorded {len(audio_data)/config.SAMPLE_RATE:.1f}s of audio", flush=True)
    print(f"[OK] Saved to {output_file}", flush=True)
    print(f"[OK] File size: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)", flush=True)

if __name__ == '__main__':
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    output = sys.argv[2] if len(sys.argv) > 2 else '/tmp/recorded_audio.wav'
    record_audio(duration, output)
