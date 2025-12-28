#!/usr/bin/env python3
"""
Play a demo audio file through the subtitle system.
This feeds the audio file directly into the processing queue.
"""
import sys
import time
import subprocess
import numpy as np
from scipy.io import wavfile
from scipy import signal as scipy_signal

# Add app to path
sys.path.insert(0, '/app')

from app.config import get_config
from app.asr import create_engine
from app.web import create_server

def main():
    audio_file = sys.argv[1] if len(sys.argv) > 1 else '/data/subtitle-product/docs/japanese.mp3'

    print(f"Playing demo: {audio_file}")

    # Convert to wav if needed
    if audio_file.endswith('.mp3'):
        wav_file = '/tmp/demo.wav'
        subprocess.run(['ffmpeg', '-y', '-i', audio_file, '-ar', '16000', '-ac', '1', wav_file],
                      capture_output=True)
    else:
        wav_file = audio_file

    # Load audio
    print("Loading audio...")
    sample_rate, audio_data = wavfile.read(wav_file)

    # Normalize to float32
    if audio_data.dtype == np.int16:
        audio_data = audio_data.astype(np.float32) / 32768.0
    elif audio_data.dtype == np.int32:
        audio_data = audio_data.astype(np.float32) / 2147483648.0

    # Resample if needed
    if sample_rate != 16000:
        num_samples = int(len(audio_data) * 16000 / sample_rate)
        audio_data = scipy_signal.resample(audio_data, num_samples).astype(np.float32)

    print(f"Audio loaded: {len(audio_data)} samples ({len(audio_data)/16000:.1f} seconds)")

    # Load Whisper
    config = get_config()
    print("Loading Whisper model...")
    engine = create_engine(backend='whisper', model_name=config.WHISPER_MODEL)

    # Create web server
    print("Starting web server...")
    server = create_server(config)
    server.run_threaded()

    print("\n" + "="*60)
    print("  DEMO READY - Open http://192.168.1.34:5000 on your iPad")
    print("="*60 + "\n")

    # Process in chunks
    chunk_duration = 3.0  # seconds
    chunk_samples = int(16000 * chunk_duration)

    for i in range(0, len(audio_data), chunk_samples):
        chunk = audio_data[i:i+chunk_samples]

        if len(chunk) < chunk_samples // 2:
            break

        # Pad if needed
        if len(chunk) < chunk_samples:
            chunk = np.pad(chunk, (0, chunk_samples - len(chunk)))

        start_time = time.time()
        text, metadata = engine.transcribe(chunk, task='translate', language='ja')
        elapsed = time.time() - start_time

        if text and len(text.strip()) > 2:
            server.send_subtitle(text=text, latency_sec=elapsed)
            print(f"[{elapsed:.2f}s] {text}")

        # Small delay between chunks
        time.sleep(0.5)

    print("\nDemo complete! Server will stay running for 30 more seconds...")
    time.sleep(30)

if __name__ == '__main__':
    main()
