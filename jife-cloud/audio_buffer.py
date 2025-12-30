"""
JIFE Cloud - Audio Capture and Buffering
Captures audio from USB device and provides chunks for API processing
"""
import logging
import threading
import queue
import time
from typing import Optional, Callable

import numpy as np

from config import get_config

logger = logging.getLogger(__name__)
config = get_config()

# Native sample rate of most USB audio devices
NATIVE_SAMPLE_RATE = 48000
# Target sample rate for Whisper
TARGET_SAMPLE_RATE = 16000


class AudioBuffer:
    """
    Captures audio from ALSA device and provides overlapping chunks for API processing.

    Unlike the Jetson version which processes each chunk independently,
    this version creates overlapping chunks to improve transcription quality
    when sentences span chunk boundaries.
    """

    def __init__(
        self,
        device: str = None,
        sample_rate: int = TARGET_SAMPLE_RATE,
        chunk_duration: float = None,
        overlap_duration: float = None,
        callback: Optional[Callable[[np.ndarray], None]] = None,
        output_queue: Optional[queue.Queue] = None,
    ):
        """
        Initialize audio buffer.

        Args:
            device: ALSA device identifier (e.g., 'plughw:1,0')
            sample_rate: Target sample rate for output (16000 for Whisper)
            chunk_duration: Duration of each chunk in seconds
            overlap_duration: Overlap between chunks in seconds
            callback: Optional callback for each chunk
            output_queue: Optional queue to put chunks
        """
        self.device = device or config.AUDIO_DEVICE
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration or config.CHUNK_DURATION_SEC
        self.overlap_duration = overlap_duration or config.OVERLAP_DURATION_SEC
        self.callback = callback
        self.output_queue = output_queue

        # Calculate sizes
        self.chunk_samples = int(sample_rate * self.chunk_duration)
        self.overlap_samples = int(sample_rate * self.overlap_duration)
        self.stride_samples = self.chunk_samples - self.overlap_samples

        # Native capture rate
        self.native_rate = NATIVE_SAMPLE_RATE
        self.resample_ratio = self.native_rate / sample_rate  # 3 for 48kHz -> 16kHz

        # Circular buffer for audio data (at target sample rate)
        # Store enough for 2x chunk duration
        self.buffer_size = self.chunk_samples * 3
        self.buffer = np.zeros(self.buffer_size, dtype=np.float32)
        self.buffer_pos = 0  # Current position in buffer
        self.samples_since_last_chunk = 0
        self.buffer_lock = threading.Lock()

        # State
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for sounddevice stream"""
        if status:
            logger.warning(f"Audio status: {status}")

        # Convert to mono float32
        audio = indata[:, 0] if indata.ndim > 1 else indata.flatten()
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # Resample from 48kHz to 16kHz (simple decimation)
        resampled = audio[::int(self.resample_ratio)]

        with self.buffer_lock:
            n_samples = len(resampled)

            # Add to circular buffer
            end_pos = self.buffer_pos + n_samples
            if end_pos <= self.buffer_size:
                self.buffer[self.buffer_pos:end_pos] = resampled
            else:
                # Wrap around
                first_part = self.buffer_size - self.buffer_pos
                self.buffer[self.buffer_pos:] = resampled[:first_part]
                self.buffer[:n_samples - first_part] = resampled[first_part:]

            self.buffer_pos = end_pos % self.buffer_size
            self.samples_since_last_chunk += n_samples

            # Check if we have enough for a new chunk
            if self.samples_since_last_chunk >= self.stride_samples:
                self._emit_chunk()
                self.samples_since_last_chunk = 0

    def _emit_chunk(self):
        """Extract and emit a chunk from the buffer"""
        # Calculate start position for the chunk
        start_pos = (self.buffer_pos - self.chunk_samples) % self.buffer_size

        # Extract chunk (handle wrap-around)
        if start_pos + self.chunk_samples <= self.buffer_size:
            chunk = self.buffer[start_pos:start_pos + self.chunk_samples].copy()
        else:
            first_part = self.buffer_size - start_pos
            chunk = np.concatenate([
                self.buffer[start_pos:],
                self.buffer[:self.chunk_samples - first_part]
            ])

        # Check for silence
        rms = np.sqrt(np.mean(chunk ** 2))
        if rms < config.SILENCE_THRESHOLD:
            logger.debug(f"Skipping silent chunk (RMS: {rms:.4f})")
            return

        # Emit chunk
        logger.debug(f"Emitting chunk: {len(chunk)} samples, RMS: {rms:.4f}")

        if self.callback:
            try:
                self.callback(chunk)
            except Exception as e:
                logger.error(f"Callback error: {e}")

        if self.output_queue:
            try:
                self.output_queue.put_nowait(chunk)
            except queue.Full:
                logger.warning("Queue full, dropping chunk")

    def start(self):
        """Start audio capture"""
        if self._running:
            logger.warning("Audio capture already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info(f"Audio capture started: device={self.device}")

    def _capture_loop(self):
        """Main capture loop"""
        try:
            import sounddevice as sd

            # Find device
            device_index = self._find_device(sd)

            with sd.InputStream(
                device=device_index,
                samplerate=self.native_rate,
                channels=1,
                dtype='float32',
                callback=self._audio_callback,
                blocksize=1024,
            ):
                logger.info(f"Audio stream opened: device={device_index}")
                while self._running:
                    time.sleep(0.1)

        except Exception as e:
            logger.error(f"Audio capture error: {e}")
            self._list_devices()

    def _find_device(self, sd) -> int:
        """Find device index from device string"""
        try:
            return int(self.device)
        except ValueError:
            pass

        # Parse ALSA device string
        if self.device.startswith('plughw:') or self.device.startswith('hw:'):
            parts = self.device.split(':')[1].split(',')
            card_num = int(parts[0])

            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    if f"hw:{card_num}" in dev['name'].lower() or 'usb' in dev['name'].lower():
                        logger.info(f"Found device: [{i}] {dev['name']}")
                        return i

        # Fallback to default
        default = sd.default.device[0]
        logger.warning(f"Using default device: {default}")
        return default

    def _list_devices(self):
        """List available audio devices"""
        try:
            import sounddevice as sd
            logger.info("Available audio devices:")
            for i, dev in enumerate(sd.query_devices()):
                if dev['max_input_channels'] > 0:
                    logger.info(f"  [{i}] {dev['name']}")
        except Exception as e:
            logger.error(f"Could not list devices: {e}")

    def stop(self):
        """Stop audio capture"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("Audio capture stopped")


def test_buffer():
    """Test audio buffer"""
    import sys

    logging.basicConfig(level=logging.DEBUG)

    chunks_received = []

    def on_chunk(chunk):
        chunks_received.append(chunk)
        rms = np.sqrt(np.mean(chunk ** 2))
        print(f"Chunk: {len(chunk)} samples, RMS: {rms:.4f}")

    device = sys.argv[1] if len(sys.argv) > 1 else 'plughw:1,0'
    buffer = AudioBuffer(device=device, callback=on_chunk)

    print(f"Testing audio capture from {device} for 30 seconds...")
    buffer.start()

    try:
        time.sleep(30)
    except KeyboardInterrupt:
        pass
    finally:
        buffer.stop()

    print(f"Received {len(chunks_received)} chunks")


if __name__ == '__main__':
    test_buffer()
