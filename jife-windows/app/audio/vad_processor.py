"""
VAD-based audio processor using Silero VAD
Segments audio by natural speech boundaries instead of fixed chunks
"""
import logging
import queue
import threading
from typing import Optional, Callable
import numpy as np

logger = logging.getLogger(__name__)


class VADProcessor:
    """
    Voice Activity Detection processor using Silero VAD.
    Segments audio by natural speech pauses instead of fixed time windows.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        min_chunk_size: float = 1.0,
        max_chunk_size: float = 10.0,
        min_silence_duration_ms: int = 500,
        speech_pad_ms: int = 200,
        callback: Optional[Callable[[np.ndarray], None]] = None,
        output_queue: Optional[queue.Queue] = None,
    ):
        """
        Initialize VAD processor.

        Args:
            sample_rate: Audio sample rate (must be 16kHz for Silero VAD)
            min_chunk_size: Minimum chunk duration in seconds before processing
            max_chunk_size: Maximum chunk duration in seconds (force output)
            min_silence_duration_ms: Minimum silence to end an utterance
            speech_pad_ms: Padding to add before/after speech segments
            callback: Optional callback for each segment
            output_queue: Optional queue for segments
        """
        self.sample_rate = sample_rate
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.min_silence_duration_ms = min_silence_duration_ms
        self.speech_pad_ms = speech_pad_ms
        self.callback = callback
        self.output_queue = output_queue

        # Silero VAD model
        self.vad_model = None
        self._load_vad_model()

        # Speech buffer (accumulates during speech activity)
        self.speech_buffer = np.array([], dtype=np.float32)
        self.silence_frames = 0
        self.in_speech = False

        # Padding buffers
        self.pre_buffer = np.array([], dtype=np.float32)
        self.pre_buffer_max = int(sample_rate * speech_pad_ms / 1000)

        # Window size for VAD (Silero uses 512 samples at 16kHz = 32ms)
        self.vad_window_size = 512

    def _load_vad_model(self):
        """Load Silero VAD model"""
        try:
            import torch
            # Download and load Silero VAD
            self.vad_model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False,
            )
            self.vad_model.eval()
            (self.get_speech_timestamps,
             self.save_audio,
             self.read_audio,
             self.VADIterator,
             self.collect_chunks) = utils
            logger.info("Silero VAD model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Silero VAD: {e}")
            logger.error("VAD mode requires Silero VAD. Install with: pip install silero-vad")
            raise

    def process_audio(self, audio: np.ndarray):
        """
        Process audio chunk with VAD segmentation.
        Buffers audio until natural speech boundaries are detected.
        """
        if self.vad_model is None:
            logger.error("VAD model not loaded")
            return

        # Convert to torch tensor for VAD
        import torch
        audio_tensor = torch.from_numpy(audio).float()

        # Process in windows for VAD detection
        for i in range(0, len(audio), self.vad_window_size):
            window = audio_tensor[i:i + self.vad_window_size]
            if len(window) < self.vad_window_size:
                break  # Skip incomplete windows

            # Get speech probability
            with torch.no_grad():
                speech_prob = self.vad_model(window, self.sample_rate).item()

            is_speech = speech_prob > 0.5  # Threshold

            if is_speech:
                # Speech detected
                if not self.in_speech:
                    # Start of new utterance - add pre-buffer
                    self.in_speech = True
                    self.speech_buffer = np.concatenate([
                        self.pre_buffer,
                        window.numpy()
                    ])
                    self.pre_buffer = np.array([], dtype=np.float32)
                    self.silence_frames = 0
                else:
                    # Continue current utterance
                    self.speech_buffer = np.concatenate([
                        self.speech_buffer,
                        window.numpy()
                    ])
                    self.silence_frames = 0

                # Check if max duration reached (force output)
                if len(self.speech_buffer) / self.sample_rate >= self.max_chunk_size:
                    self._flush_speech_buffer()

            else:
                # Silence/non-speech
                if self.in_speech:
                    # Potential end of utterance
                    self.silence_frames += len(window)
                    silence_duration_ms = (self.silence_frames / self.sample_rate) * 1000

                    if silence_duration_ms >= self.min_silence_duration_ms:
                        # End of utterance confirmed
                        self._flush_speech_buffer()
                    else:
                        # Still in utterance (short pause)
                        self.speech_buffer = np.concatenate([
                            self.speech_buffer,
                            window.numpy()
                        ])
                else:
                    # Update pre-buffer (rolling window before speech)
                    self.pre_buffer = np.concatenate([
                        self.pre_buffer,
                        window.numpy()
                    ])
                    if len(self.pre_buffer) > self.pre_buffer_max:
                        # Keep only last N samples
                        self.pre_buffer = self.pre_buffer[-self.pre_buffer_max:]

    def _flush_speech_buffer(self):
        """Flush accumulated speech buffer as a complete utterance"""
        if len(self.speech_buffer) == 0:
            return

        duration = len(self.speech_buffer) / self.sample_rate

        # Only output if above minimum duration
        if duration >= self.min_chunk_size:
            logger.debug(f"VAD segment: {duration:.2f}s, RMS: {np.sqrt(np.mean(self.speech_buffer**2)):.4f}")

            # Deliver segment
            if self.callback:
                try:
                    self.callback(self.speech_buffer.copy())
                except Exception as e:
                    logger.error(f"VAD callback error: {e}")

            if self.output_queue:
                try:
                    self.output_queue.put_nowait(self.speech_buffer.copy())
                except queue.Full:
                    logger.warning("VAD queue full, dropping segment")

        # Reset state
        self.speech_buffer = np.array([], dtype=np.float32)
        self.in_speech = False
        self.silence_frames = 0

    def finish(self):
        """Flush any remaining audio in buffer"""
        if len(self.speech_buffer) > 0:
            logger.info("Flushing remaining speech buffer on finish")
            self._flush_speech_buffer()


def test_vad():
    """Test VAD processor"""
    import sys

    logging.basicConfig(level=logging.DEBUG)

    segments_received = []

    def on_segment(segment):
        segments_received.append(segment)
        print(f"Received segment: {len(segment)} samples, duration: {len(segment)/16000:.2f}s")

    vad = VADProcessor(
        min_chunk_size=1.0,
        max_chunk_size=10.0,
        callback=on_segment,
    )

    # Simulate audio stream
    print("Simulating 10 seconds of audio with speech pauses...")
    for i in range(10):
        # Generate 1 second of fake audio
        audio = np.random.randn(16000).astype(np.float32) * 0.1
        vad.process_audio(audio)

    vad.finish()
    print(f"Received {len(segments_received)} segments")


if __name__ == '__main__':
    test_vad()
