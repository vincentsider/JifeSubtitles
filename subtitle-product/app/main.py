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
from app.audio import AudioCapture
from app.asr import create_engine
from app.web import create_server

# Global state
shutdown_event = threading.Event()
config = get_config()

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


def processing_loop(
    audio_queue: queue.Queue,
    whisper_engine,
    web_server,
):
    """
    Main processing loop.
    Takes audio chunks from queue, transcribes/translates, sends to web clients.
    """
    logger.info("Processing loop started")

    # Track processing times to estimate latency
    last_chunk_time = time.time()

    while not shutdown_event.is_set():
        try:
            # AGGRESSIVE latency management:
            # If queue has more than 1 chunk, we're falling behind - discard all but newest
            queue_size = audio_queue.qsize()
            if queue_size > 1:
                discarded = 0
                # Keep only the newest chunk
                newest_chunk = None
                while not audio_queue.empty():
                    try:
                        newest_chunk = audio_queue.get_nowait()
                        discarded += 1
                    except queue.Empty:
                        break
                if discarded > 1:
                    logger.warning(f"Discarded {discarded - 1} old chunks to stay real-time")
                # Put the newest back if we have it
                if newest_chunk is not None:
                    audio_queue.put(newest_chunk)

            # Get audio chunk from queue
            audio_chunk = audio_queue.get(timeout=1.0)
            chunk_receive_time = time.time()

            # Track time since last chunk for latency estimation
            time_since_last = chunk_receive_time - last_chunk_time
            last_chunk_time = chunk_receive_time

            start_time = time.time()

            # Transcribe/translate
            text, metadata = whisper_engine.transcribe(
                audio_chunk,
                task=config.WHISPER_TASK,
                language=config.WHISPER_LANGUAGE,
            )

            elapsed = time.time() - start_time

            # Skip empty results
            if not text or len(text.strip()) < 2:
                continue

            # For translate task, text is already English
            # For transcribe task, source_text would be Japanese
            source_text = ''
            if config.WHISPER_TASK == 'transcribe':
                source_text = text
                # Would need separate translation here
                # For now, we're using translate task so this isn't needed

            # Send to web clients
            web_server.send_subtitle(
                text=text,
                source_text=source_text,
                latency_sec=elapsed,
                metadata=metadata,
            )

            logger.info(f"[{elapsed:.2f}s] {text[:80]}{'...' if len(text) > 80 else ''}")

        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Processing error: {e}", exc_info=True)
            time.sleep(0.5)

    logger.info("Processing loop stopped")


def main():
    """Main entry point"""
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
        )
        logger.info("Whisper model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")
        logger.error("Make sure you're running inside the Docker container with GPU access")
        sys.exit(1)

    # 3. Create audio capture
    logger.info("Setting up audio capture...")
    audio_capture = AudioCapture(
        device=config.AUDIO_DEVICE,
        sample_rate=config.SAMPLE_RATE,
        channels=config.CHANNELS,
        chunk_duration=config.CHUNK_DURATION_SEC,
        output_queue=audio_queue,
    )

    # 4. Start processing thread
    processing_thread = threading.Thread(
        target=processing_loop,
        args=(audio_queue, whisper_engine, web_server),
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
