"""
Audio capture module using ALSA/sounddevice
Captures audio from USB audio device and streams to processing queue
"""
import logging
import threading
import queue
import time
from typing import Optional, Callable

import numpy as np
from scipy import signal as scipy_signal

logger = logging.getLogger(__name__)

# Native sample rate of USB audio device (most USB devices support 48kHz)
NATIVE_SAMPLE_RATE = 48000
# Target sample rate for Whisper
TARGET_SAMPLE_RATE = 16000


class AudioCapture:
    """
    Captures audio from ALSA device and delivers chunks to a callback or queue.

    Uses sounddevice for cross-platform compatibility with ALSA backend on Jetson.
    """

    def __init__(
        self,
        device: str = 'plughw:2,0',
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_duration: float = 3.0,
        callback: Optional[Callable[[np.ndarray], None]] = None,
        output_queue: Optional[queue.Queue] = None,
    ):
        """
        Initialize audio capture.

        Args:
            device: ALSA device identifier (e.g., 'plughw:2,0')
            sample_rate: Sample rate in Hz (16000 for Whisper)
            channels: Number of audio channels (1 for mono)
            chunk_duration: Duration of each audio chunk in seconds
            callback: Optional callback function for each audio chunk
            output_queue: Optional queue to put audio chunks
        """
        self.device = device
        self.sample_rate = sample_rate  # Target rate for Whisper (16kHz)
        self.channels = channels
        self.chunk_duration = chunk_duration
        self.callback = callback
        self.output_queue = output_queue

        # Use native rate for capture, resample to target rate
        self.native_rate = NATIVE_SAMPLE_RATE
        self.resample_ratio = self.native_rate / self.sample_rate  # 48000/16000 = 3

        # Buffer sizes at native rate
        self.native_samples_per_chunk = int(self.native_rate * chunk_duration)
        self.samples_per_chunk = int(sample_rate * chunk_duration)
        self.buffer = []
        self.buffer_lock = threading.Lock()

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stream = None

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for sounddevice stream"""
        if status:
            logger.warning(f"Audio status: {status}")

        # Convert to mono float32 if needed
        audio = indata[:, 0] if indata.ndim > 1 else indata.flatten()
        audio = audio.astype(np.float32)

        with self.buffer_lock:
            self.buffer.extend(audio.tolist())

            # Process complete chunks (at native sample rate)
            while len(self.buffer) >= self.native_samples_per_chunk:
                chunk = np.array(self.buffer[:self.native_samples_per_chunk], dtype=np.float32)
                del self.buffer[:self.native_samples_per_chunk]

                # Resample from 48kHz to 16kHz
                resampled = scipy_signal.resample(chunk, self.samples_per_chunk)

                # Deliver chunk
                self._deliver_chunk(resampled.astype(np.float32))

    def _deliver_chunk(self, chunk: np.ndarray):
        """Deliver audio chunk to callback or queue"""
        # Check for silence (skip if too quiet)
        # RMS threshold increased to 0.02 to avoid Whisper hallucinations on noise
        rms = np.sqrt(np.mean(chunk**2))
        if rms < 0.02:  # Skip low-level noise that causes hallucinations
            logger.debug(f"Skipping silent chunk (RMS: {rms:.6f})")
            return

        logger.debug(f"Delivering audio chunk: {len(chunk)} samples, RMS: {rms:.4f}")

        if self.callback:
            try:
                self.callback(chunk)
            except Exception as e:
                logger.error(f"Audio callback error: {e}")

        if self.output_queue:
            try:
                self.output_queue.put_nowait(chunk)
            except queue.Full:
                logger.warning("Audio queue full, dropping chunk")

    def start(self):
        """Start audio capture in background thread"""
        if self._running:
            logger.warning("Audio capture already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info(f"Audio capture started: device={self.device}, rate={self.sample_rate}")

    def _capture_loop(self):
        """Main capture loop - runs in background thread"""
        try:
            import sounddevice as sd

            # Find device index
            device_index = self._find_device(sd)

            with sd.InputStream(
                device=device_index,
                samplerate=self.native_rate,  # Capture at native 48kHz
                channels=self.channels,
                dtype='float32',
                callback=self._audio_callback,
                blocksize=1024,
            ):
                logger.info(f"Audio stream opened: device_index={device_index}, native_rate={self.native_rate}, target_rate={self.sample_rate}")
                while self._running:
                    time.sleep(0.1)

        except Exception as e:
            logger.error(f"Audio capture error: {e}")
            self._list_devices()

    def _find_device(self, sd) -> int:
        """Find device index from device string"""
        # If it's already an integer, use it directly
        try:
            return int(self.device)
        except ValueError:
            pass

        # For ALSA device strings like 'plughw:2,0', we need to find by name
        # sounddevice lists devices by name, so we look for matching pattern
        devices = sd.query_devices()

        # Extract card number from plughw:X,Y format
        if self.device.startswith('plughw:') or self.device.startswith('hw:'):
            parts = self.device.split(':')[1].split(',')
            card_num = int(parts[0])

            # Look for device with matching card number
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    # Check if device name contains card info
                    if f"hw:{card_num}" in dev['name'].lower() or \
                       'usb' in dev['name'].lower():
                        logger.info(f"Found device: [{i}] {dev['name']}")
                        return i

        # Fallback: return default input device
        default = sd.default.device[0]
        logger.warning(f"Could not find device '{self.device}', using default: {default}")
        return default

    def _list_devices(self):
        """List available audio devices for debugging"""
        try:
            import sounddevice as sd
            logger.info("Available audio devices:")
            for i, dev in enumerate(sd.query_devices()):
                if dev['max_input_channels'] > 0:
                    logger.info(f"  [{i}] {dev['name']} (inputs: {dev['max_input_channels']})")
        except Exception as e:
            logger.error(f"Could not list devices: {e}")

    def stop(self):
        """Stop audio capture"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("Audio capture stopped")

    def is_running(self) -> bool:
        """Check if capture is running"""
        return self._running


def test_capture():
    """Test audio capture functionality"""
    import sys

    logging.basicConfig(level=logging.DEBUG)

    chunks_received = []

    def on_chunk(chunk):
        chunks_received.append(chunk)
        print(f"Received chunk: {len(chunk)} samples, RMS: {np.sqrt(np.mean(chunk**2)):.4f}")

    device = sys.argv[1] if len(sys.argv) > 1 else 'plughw:2,0'
    capture = AudioCapture(device=device, chunk_duration=2.0, callback=on_chunk)

    print(f"Testing audio capture from {device} for 10 seconds...")
    capture.start()

    try:
        time.sleep(10)
    except KeyboardInterrupt:
        pass
    finally:
        capture.stop()

    print(f"Received {len(chunks_received)} chunks")


if __name__ == '__main__':
    test_capture()
