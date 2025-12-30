#!/usr/bin/env python3
"""
JIFE Cloud - Main Application
Raspberry Pi + Groq API version

This application:
1. Captures audio from USB audio device
2. Sends audio chunks to Groq API for translation
3. Displays English subtitles via web interface
"""
import os
import sys
import time
import queue
import signal
import logging
import threading
import socket

from config import get_config
from groq_client import GroqWhisperClient
from audio_buffer import AudioBuffer
from web_server import create_server

# Global state
shutdown_event = threading.Event()
config = get_config()

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger('jife-cloud')


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    shutdown_event.set()


def get_local_ip():
    """Get local IP address"""
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
    groq_client: GroqWhisperClient,
    web_server,
):
    """
    Main processing loop.
    Takes audio chunks from queue, sends to Groq API, displays subtitles.
    """
    logger.info("Processing loop started")

    while not shutdown_event.is_set():
        try:
            # Get audio chunk (with timeout to check shutdown)
            try:
                audio_chunk = audio_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            # If queue is backing up, skip old chunks
            queue_size = audio_queue.qsize()
            if queue_size > 2:
                logger.warning(f"Queue backing up ({queue_size}), skipping old chunks")
                while audio_queue.qsize() > 1:
                    try:
                        audio_queue.get_nowait()
                    except queue.Empty:
                        break

            start_time = time.time()

            # Send to Groq API
            text, metadata = groq_client.translate(audio_chunk, config.SAMPLE_RATE)

            elapsed = time.time() - start_time

            # Skip empty results
            if not text or len(text.strip()) < 2:
                continue

            # Send to web clients
            web_server.send_subtitle(
                text=text,
                latency_sec=elapsed,
                metadata=metadata,
            )

            logger.info(f"[{elapsed:.2f}s] {text[:80]}{'...' if len(text) > 80 else ''}")

        except Exception as e:
            logger.error(f"Processing error: {e}", exc_info=True)
            time.sleep(1)

    logger.info("Processing loop stopped")


def main():
    """Main entry point"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Print banner
    print("\n" + "=" * 60)
    print("  JIFE CLOUD - Japanese to English Subtitles")
    print("  Raspberry Pi + Groq API Edition")
    print("=" * 60)
    print(f"  Audio Device:   {config.AUDIO_DEVICE}")
    print(f"  Chunk Duration: {config.CHUNK_DURATION_SEC}s")
    print(f"  Overlap:        {config.OVERLAP_DURATION_SEC}s")
    print(f"  Web Port:       {config.WEB_PORT}")
    print("=" * 60 + "\n")

    # Verify API key
    if not config.GROQ_API_KEY:
        logger.error("GROQ_API_KEY not set!")
        logger.error("Set it with: export GROQ_API_KEY='your-key-here'")
        logger.error("Get a key at: https://console.groq.com/keys")
        sys.exit(1)

    # Create audio queue
    audio_queue = queue.Queue(maxsize=10)

    # Initialize components
    logger.info("Initializing components...")

    # 1. Create Groq client
    logger.info("Creating Groq client...")
    try:
        groq_client = GroqWhisperClient()
        logger.info(f"Groq client ready (model: {config.GROQ_MODEL})")
    except Exception as e:
        logger.error(f"Failed to create Groq client: {e}")
        sys.exit(1)

    # 2. Create web server
    logger.info("Creating web server...")
    web_server = create_server(groq_client=groq_client)
    web_server.run_threaded()

    # 3. Create audio buffer
    logger.info("Setting up audio capture...")
    audio_buffer = AudioBuffer(
        device=config.AUDIO_DEVICE,
        sample_rate=config.SAMPLE_RATE,
        chunk_duration=config.CHUNK_DURATION_SEC,
        overlap_duration=config.OVERLAP_DURATION_SEC,
        output_queue=audio_queue,
    )

    # 4. Start processing thread
    processing_thread = threading.Thread(
        target=processing_loop,
        args=(audio_queue, groq_client, web_server),
        daemon=True,
    )
    processing_thread.start()

    # 5. Start audio capture
    audio_buffer.start()

    # Print access info
    local_ip = get_local_ip()
    print("\n" + "=" * 60)
    print("  SYSTEM READY")
    print("=" * 60)
    print(f"\n  Open in browser:")
    print(f"    http://{local_ip}:{config.WEB_PORT}")
    print(f"\n  Health check:")
    print(f"    curl http://localhost:{config.WEB_PORT}/health")
    print("\n" + "=" * 60)
    print("  Press Ctrl+C to stop")
    print("=" * 60 + "\n")

    # Main loop
    try:
        while not shutdown_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    # Cleanup
    logger.info("Shutting down...")
    audio_buffer.stop()
    shutdown_event.set()
    processing_thread.join(timeout=5)

    # Print usage stats
    stats = groq_client.get_stats()
    print("\n" + "=" * 60)
    print("  SESSION STATS")
    print("=" * 60)
    print(f"  Total requests:    {stats['total_requests']}")
    print(f"  Audio processed:   {stats['total_audio_hours']:.2f} hours")
    print(f"  Estimated cost:    ${stats['estimated_cost_usd']:.4f}")
    print(f"  Errors:            {stats['total_errors']}")
    print("=" * 60 + "\n")

    logger.info("Shutdown complete")


if __name__ == '__main__':
    main()
