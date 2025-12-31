#!/usr/bin/env python3
"""
MODIFIED main.py that ALSO records audio to file while processing.
This ensures we record the EXACT same audio that produces the translations.
"""
import os
import sys
import time
import queue
import signal
import logging
import threading
import wave
import numpy as np
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_config
from app.audio import AudioCapture
from app.asr import create_engine
from app.web import create_server

# Global state
shutdown_event = threading.Event()
config = get_config()
whisper_engine = None
engine_lock = threading.Lock()

# Recording state
recorded_chunks = []
recording_active = threading.Event()

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('subtitle-system')


def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, initiating shutdown...")
    shutdown_event.set()


def processing_loop(audio_queue: queue.Queue, web_server):
    """Processing loop that ALSO records audio chunks"""
    global whisper_engine, recorded_chunks
    logger.info("Processing loop started (RECORDING MODE)")

    while not shutdown_event.is_set():
        try:
            try:
                audio_chunk = audio_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            # RECORD the audio chunk if recording is active
            if recording_active.is_set():
                recorded_chunks.append(audio_chunk.copy())

            # Process normally
            with engine_lock:
                if whisper_engine is None:
                    time.sleep(0.1)
                    continue

                start_time = time.time()

                text, metadata = whisper_engine.transcribe(
                    audio_chunk,
                    task=config.WHISPER_TASK,
                    language=config.WHISPER_LANGUAGE,
                    target_language=config.WHISPER_TARGET_LANGUAGE,
                )

                elapsed = time.time() - start_time

                if text and len(text.strip()) >= 2:
                    web_server.send_subtitle(
                        text=text,
                        source_text='',
                        latency_sec=elapsed,
                        metadata=metadata,
                    )
                    logger.info(f"[{elapsed:.2f}s] {text[:80]}{'...' if len(text) > 80 else ''}")

        except Exception as e:
            logger.error(f"Processing error: {e}", exc_info=True)
            time.sleep(0.5)

    logger.info("Processing loop stopped")


def record_120_seconds():
    """Start recording for 120 seconds"""
    global recorded_chunks
    recorded_chunks = []

    logger.info("Starting 120-second recording...")
    recording_active.set()

    time.sleep(120)

    recording_active.clear()
    logger.info(f"Recording complete. Captured {len(recorded_chunks)} chunks")

    # Save to file
    if recorded_chunks:
        audio_data = np.concatenate(recorded_chunks)
        audio_int16 = (audio_data * 32767).astype(np.int16)

        output_file = '/tmp/recorded_audio.wav'
        with wave.open(output_file, 'wb') as wf:
            wf.setnchannels(config.CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(config.SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())

        logger.info(f"Saved {len(audio_data)/config.SAMPLE_RATE:.1f}s to {output_file}")


def main():
    global whisper_engine

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("\n" + "=" * 60)
    print("  RECORDING MODE - Will record for 120 seconds")
    print("=" * 60 + "\n")

    audio_queue = queue.Queue(maxsize=config.MAX_QUEUE_SIZE)

    logger.info("Creating web server...")
    web_server = create_server(config)
    web_server.run_threaded()

    logger.info(f"Loading Whisper model...")
    whisper_engine = create_engine(
        backend=config.WHISPER_BACKEND,
        model_name=config.WHISPER_MODEL,
        beam_size=config.WHISPER_BEAM_SIZE,
        compute_type=config.WHISPER_COMPUTE_TYPE,
    )

    web_server.set_current_model(config.WHISPER_MODEL)

    logger.info("Setting up audio capture...")
    audio_capture = AudioCapture(
        device=config.AUDIO_DEVICE,
        sample_rate=config.SAMPLE_RATE,
        channels=config.CHANNELS,
        chunk_duration=config.CHUNK_DURATION_SEC,
        output_queue=audio_queue,
    )

    processing_thread = threading.Thread(
        target=processing_loop,
        args=(audio_queue, web_server),
        daemon=True,
        name='Processing',
    )
    processing_thread.start()

    audio_capture.start()

    print("\n" + "=" * 60)
    print("  SYSTEM READY - Starting 120s recording in 5 seconds...")
    print("=" * 60 + "\n")

    time.sleep(5)
    record_120_seconds()

    print("\nRecording complete! Shutting down...")
    shutdown_event.set()
    audio_capture.stop()
    processing_thread.join(timeout=5)

    logger.info("Shutdown complete")


if __name__ == '__main__':
    main()
