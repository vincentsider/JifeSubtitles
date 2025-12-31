#!/usr/bin/env python3
"""
Japanese -> English Real-Time Subtitle System
Main application entry point

This application:
1. Captures audio from USB audio device
2. Transcribes/translates Japanese speech to English using Whisper
3. Displays subtitles in real-time via web interface
"""
import os
import sys
import time
import queue
import signal
import logging
import threading
from datetime import datetime

import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_config
from app.audio import AudioCapture, VADProcessor
from app.asr import create_engine
from app.web import create_server

# Global state
shutdown_event = threading.Event()
config = get_config()
whisper_engine = None
engine_lock = threading.Lock()

# Simple duplicate detection
last_output_text = ""  # For detecting consecutive identical outputs
last_output_lock = threading.Lock()

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger('subtitle-system')


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    shutdown_event.set()


def get_local_ip():
    """Get local IP address for display"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return 'localhost'


# Removed old buffering/deduplication functions - not needed for fixed chunk mode


def processing_loop(
    audio_queue: queue.Queue,
    web_server,
):
    """
    Main processing loop - SIMPLIFIED for Option A (fixed chunks).
    - Processes fixed-size chunks (2.5s, no overlap)
    - Simple duplicate detection (skip identical consecutive outputs)
    - Immediate output (no buffering)
    - Deterministic output (temperature=0)
    """
    global whisper_engine, last_output_text
    logger.info(f"Processing loop started (MODE: {config.PROCESSING_MODE}, CHUNK: {config.CHUNK_DURATION_SEC}s)")

    while not shutdown_event.is_set():
        try:
            # Get next audio chunk (blocking)
            try:
                audio_chunk = audio_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            # Process with engine lock
            with engine_lock:
                if whisper_engine is None:
                    time.sleep(0.1)
                    continue

                start_time = time.time()

                # Transcribe this chunk
                text, metadata = whisper_engine.transcribe(
                    audio_chunk,
                    task=config.WHISPER_TASK,
                    language=config.WHISPER_LANGUAGE,
                    target_language=config.WHISPER_TARGET_LANGUAGE,
                )

                elapsed = time.time() - start_time

                # Skip empty/hallucination results (already filtered in engine)
                if not text or len(text.strip()) < 2:
                    continue

                # Simple duplicate detection: skip if identical to last output
                with last_output_lock:
                    if text == last_output_text:
                        logger.debug(f"Skipping duplicate: '{text[:40]}...'")
                        continue
                    last_output_text = text

                # Output immediately
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


def switch_model(model_name: str, compute_type: str, beam_size: int = 5) -> bool:
    """
    Switch to a different Whisper model.
    Called from web server in a background thread.
    Returns True on success, False on failure.

    IMPORTANT: We MUST delete the old model and free GPU memory BEFORE
    loading the new model, otherwise large models cause CUDA OOM on 7.4GB Jetson.
    """
    global whisper_engine
    logger.info(f"Switching model to: {model_name} (compute_type={compute_type}, beam_size={beam_size})")

    try:
        import gc

        # Step 1: Delete old engine FIRST to free GPU memory
        with engine_lock:
            old_engine = whisper_engine
            whisper_engine = None  # Set to None so processing loop skips

        if old_engine is not None:
            logger.info("Unloading old model to free GPU memory...")
            del old_engine

        # Step 2: Force GPU memory release
        gc.collect()

        # Try to clear GPU cache if torch is available
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                logger.info("GPU memory cache cleared")
        except Exception as e:
            logger.debug(f"Could not clear torch CUDA cache: {e}")

        # Small delay to ensure memory is fully released
        time.sleep(0.5)

        # Step 3: Now load new model with GPU memory available
        logger.info(f"Loading new model: {model_name}...")
        new_engine = create_engine(
            backend='faster_whisper',
            model_name=model_name,
            beam_size=beam_size,
            compute_type=compute_type,
        )

        # Step 4: Set new engine
        with engine_lock:
            whisper_engine = new_engine

        logger.info(f"Model switched successfully to: {model_name}")
        return True

    except Exception as e:
        logger.error(f"Failed to switch model: {e}", exc_info=True)
        # Try to recover by reloading default model
        try:
            logger.warning("Attempting to recover with medium model...")
            recovery_engine = create_engine(
                backend='faster_whisper',
                model_name='medium',
                beam_size=3,
                compute_type='int8',
            )
            with engine_lock:
                whisper_engine = recovery_engine
            logger.info("Recovered with medium model")
        except Exception as recovery_error:
            logger.error(f"Recovery also failed: {recovery_error}")
        return False


def main():
    """Main entry point"""
    global whisper_engine

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Print banner
    print("\n" + "=" * 60)
    print("  JAPANESE -> ENGLISH REAL-TIME SUBTITLE SYSTEM")
    print("  Jetson Orin Nano SUPER Edition")
    print("=" * 60)
    print(f"  Audio Device:   {config.AUDIO_DEVICE}")
    print(f"  Whisper Model:  {config.WHISPER_MODEL}")
    print(f"  Whisper Backend:{config.WHISPER_BACKEND}")
    print(f"  Task:           {config.WHISPER_TASK}")
    print(f"  Web Port:       {config.WEB_PORT}")
    print("=" * 60 + "\n")

    # Create audio queue
    audio_queue = queue.Queue(maxsize=config.MAX_QUEUE_SIZE)

    # Initialize components
    logger.info("Initializing components...")

    # 1. Create web server (start first so we can see status)
    logger.info("Creating web server...")
    web_server = create_server(config)
    web_server.run_threaded()

    # 2. Load Whisper model
    logger.info(f"Loading Whisper model ({config.WHISPER_BACKEND}/{config.WHISPER_MODEL})...")
    try:
        whisper_engine = create_engine(
            backend=config.WHISPER_BACKEND,
            model_name=config.WHISPER_MODEL,
            beam_size=config.WHISPER_BEAM_SIZE,
            compute_type=config.WHISPER_COMPUTE_TYPE,
        )
        logger.info("Whisper model loaded successfully")

        # Set current model in web server and register switch callback
        # Build model ID in format: model_name:compute_type:beam_size
        compute_type = config.WHISPER_COMPUTE_TYPE or 'float16'
        model_id = f"{config.WHISPER_MODEL}:{compute_type}:{config.WHISPER_BEAM_SIZE}"
        web_server.set_current_model(model_id)
        web_server.set_model_switch_callback(switch_model)

    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")
        logger.error("Make sure you're running inside the Docker container with GPU access")
        sys.exit(1)

    # 3. Create audio capture (mode-dependent)
    logger.info(f"Setting up audio capture (mode: {config.PROCESSING_MODE})...")

    if config.PROCESSING_MODE == 'vad':
        # VAD mode: raw audio capture + VAD processor
        vad_processor = VADProcessor(
            sample_rate=config.SAMPLE_RATE,
            min_chunk_size=config.VAD_MIN_CHUNK_SIZE,
            max_chunk_size=config.VAD_MAX_CHUNK_SIZE,
            min_silence_duration_ms=config.MIN_SILENCE_DURATION_MS,
            speech_pad_ms=config.PRE_ROLL_MS,
            output_queue=audio_queue,
        )

        # Raw audio capture feeds into VAD processor
        audio_capture = AudioCapture(
            device=config.AUDIO_DEVICE,
            sample_rate=config.SAMPLE_RATE,
            channels=config.CHANNELS,
            chunk_duration=0.5,  # Small chunks for VAD processing
            chunk_overlap=0.0,
            callback=vad_processor.process_audio,  # Feed to VAD
        )
    else:
        # Fixed mode: direct chunking
        audio_capture = AudioCapture(
            device=config.AUDIO_DEVICE,
            sample_rate=config.SAMPLE_RATE,
            channels=config.CHANNELS,
            chunk_duration=config.CHUNK_DURATION_SEC,
            chunk_overlap=config.CHUNK_OVERLAP_SEC,
            output_queue=audio_queue,
        )

    # 4. Start processing thread
    processing_thread = threading.Thread(
        target=processing_loop,
        args=(audio_queue, web_server),
        daemon=True,
        name='Processing',
    )
    processing_thread.start()

    # 5. Start audio capture
    audio_capture.start()

    # Print access info
    local_ip = get_local_ip()
    print("\n" + "=" * 60)
    print("  SYSTEM READY")
    print("=" * 60)
    print(f"\n  Open in browser:\n")
    print(f"    http://{local_ip}:{config.WEB_PORT}")
    print(f"\n  Health check:")
    print(f"    curl http://localhost:{config.WEB_PORT}/health")
    print("\n" + "=" * 60)
    print("  Press Ctrl+C to stop")
    print("=" * 60 + "\n")

    # Main loop - just wait for shutdown
    try:
        while not shutdown_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    # Cleanup
    logger.info("Shutting down...")
    audio_capture.stop()
    shutdown_event.set()

    # Wait for processing thread
    processing_thread.join(timeout=5)

    logger.info("Shutdown complete")


if __name__ == '__main__':
    main()
