"""
Enhanced Whisper Engine (Option E): Audio Preprocessing + Whisper Large-v3

This engine wraps FasterWhisperEngine with comprehensive audio preprocessing:
1. Audio Normalization/Leveling - Prevents Whisper from dropping quiet speakers
2. Light Noise Suppression - Reduces background noise without distorting speech
3. Better Resampling - High-quality polyphase resampling instead of decimation
4. Vocal Isolation - Optional Demucs-based source separation for TV content

Key features:
- Reuses existing Whisper large-v3 model (no new downloads)
- All preprocessing done in numpy/scipy (fast, CPU-based)
- Vocal isolation uses pre-trained Demucs (optional, adds latency)
- Designed for Japanese TV content with music/effects

Memory: ~4GB (same as Option A, Demucs adds ~1GB if enabled)
Latency: Slightly higher due to preprocessing, much lower hallucination rate
"""
import logging
import time
import os
from typing import Dict, Any, Tuple, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Audio preprocessing constants
TARGET_RMS = 0.1  # Target RMS level for normalization
NOISE_REDUCE_PROP = 0.5  # Noise reduction strength (0.0-1.0)
NOISE_REDUCE_STATIONARY = True  # Assume stationary noise (faster)


class EnhancedWhisperEngine:
    """
    Option E: Enhanced Whisper with comprehensive audio preprocessing.

    Wraps FasterWhisperEngine with:
    1. Audio normalization (RMS-based)
    2. Noise reduction (noisereduce library)
    3. High-quality resampling (scipy polyphase)
    4. Optional vocal isolation (Demucs)
    """

    def __init__(
        self,
        whisper_model: str = "large-v3",
        whisper_compute_type: str = "float16",
        whisper_beam_size: int = 5,
        device: str = "cuda",
        enable_vocal_isolation: bool = False,  # Off by default (adds latency)
        enable_noise_reduction: bool = True,
        enable_normalization: bool = True,
    ):
        """
        Initialize Enhanced Whisper Engine.

        Args:
            whisper_model: Whisper model name (reuses existing model)
            whisper_compute_type: Compute type for Whisper
            whisper_beam_size: Beam size for decoding
            device: Device to use ('cuda' or 'cpu')
            enable_vocal_isolation: Enable Demucs vocal separation (slow but effective)
            enable_noise_reduction: Enable noise reduction preprocessing
            enable_normalization: Enable audio normalization
        """
        self.whisper_model_name = whisper_model
        self.whisper_compute_type = whisper_compute_type
        self.whisper_beam_size = whisper_beam_size
        self.device = device

        # Preprocessing flags
        self.enable_vocal_isolation = enable_vocal_isolation
        self.enable_noise_reduction = enable_noise_reduction
        self.enable_normalization = enable_normalization

        # Models
        self.whisper_model = None
        self.demucs_model = None

        self._loaded = False

    def load(self):
        """Load Whisper model and optional Demucs"""
        logger.info("Loading Enhanced Whisper Engine (Option E)...")
        start = time.time()

        # Load Whisper (same as Option A)
        self._load_whisper()

        # Optionally load Demucs for vocal isolation
        if self.enable_vocal_isolation:
            self._load_demucs()

        # Verify preprocessing libraries
        self._check_preprocessing_libs()

        self._loaded = True
        total_time = time.time() - start
        logger.info(f"Enhanced Whisper Engine loaded in {total_time:.2f}s")

        # Log configuration
        logger.info(f"  Vocal isolation: {'ON' if self.enable_vocal_isolation else 'OFF'}")
        logger.info(f"  Noise reduction: {'ON' if self.enable_noise_reduction else 'OFF'}")
        logger.info(f"  Normalization: {'ON' if self.enable_normalization else 'OFF'}")

    def _load_whisper(self):
        """Load Whisper model (reuses existing large-v3)"""
        logger.info(f"Loading Whisper model: {self.whisper_model_name}")
        start = time.time()

        try:
            from faster_whisper import WhisperModel

            self.whisper_model = WhisperModel(
                self.whisper_model_name,
                device=self.device,
                compute_type=self.whisper_compute_type,
            )

            load_time = time.time() - start
            logger.info(f"Whisper loaded in {load_time:.2f}s")

        except Exception as e:
            logger.error(f"Failed to load Whisper: {e}")
            raise

    def _load_demucs(self):
        """Load Demucs model for vocal isolation"""
        logger.info("Loading Demucs for vocal isolation...")
        start = time.time()

        try:
            import torch
            from demucs.pretrained import get_model
            from demucs.apply import apply_model

            # Use htdemucs_ft (fine-tuned, good quality)
            # Or htdemucs (faster, slightly lower quality)
            self.demucs_model = get_model('htdemucs')
            self.demucs_model.to(self.device if self.device == 'cuda' else 'cpu')
            self.demucs_model.eval()

            load_time = time.time() - start
            logger.info(f"Demucs loaded in {load_time:.2f}s")

        except ImportError:
            logger.warning("Demucs not installed. Vocal isolation disabled.")
            logger.warning("Install with: pip install demucs")
            self.enable_vocal_isolation = False
        except Exception as e:
            logger.error(f"Failed to load Demucs: {e}")
            self.enable_vocal_isolation = False

    def _check_preprocessing_libs(self):
        """Check that preprocessing libraries are available"""
        # Check noisereduce
        if self.enable_noise_reduction:
            try:
                import noisereduce
                logger.info("noisereduce library available")
            except ImportError:
                logger.warning("noisereduce not installed. Noise reduction disabled.")
                logger.warning("Install with: pip install noisereduce")
                self.enable_noise_reduction = False

        # Check scipy for resampling
        try:
            from scipy import signal
            logger.info("scipy.signal available for resampling")
        except ImportError:
            logger.warning("scipy not installed. Using basic resampling.")
            logger.warning("Install with: pip install scipy")

    def _normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """
        Normalize audio to target RMS level.

        This prevents Whisper from dropping quiet speakers and ensures
        consistent input levels regardless of source volume.
        """
        if not self.enable_normalization:
            return audio

        # Calculate current RMS
        rms = np.sqrt(np.mean(audio ** 2))

        if rms < 1e-6:  # Silence
            return audio

        # Scale to target RMS
        gain = TARGET_RMS / rms

        # Limit gain to prevent amplifying noise too much
        gain = min(gain, 10.0)  # Max 20dB boost

        normalized = audio * gain

        # Soft clip to prevent clipping (tanh-based)
        normalized = np.tanh(normalized)

        logger.debug(f"Audio normalized: RMS {rms:.4f} -> {TARGET_RMS:.4f} (gain: {gain:.2f}x)")

        return normalized.astype(np.float32)

    def _reduce_noise(self, audio: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
        """
        Apply light noise reduction to reduce background noise.

        Uses noisereduce library with conservative settings to avoid
        distorting consonants (important for Japanese).
        """
        if not self.enable_noise_reduction:
            return audio

        try:
            import noisereduce as nr

            # Light noise reduction - prop_decrease controls strength
            # Lower values = less aggressive (preserves more speech detail)
            reduced = nr.reduce_noise(
                y=audio,
                sr=sample_rate,
                prop_decrease=NOISE_REDUCE_PROP,
                stationary=NOISE_REDUCE_STATIONARY,
                n_fft=512,  # Smaller FFT for faster processing
                hop_length=128,
            )

            logger.debug("Noise reduction applied")
            return reduced.astype(np.float32)

        except Exception as e:
            logger.warning(f"Noise reduction failed: {e}")
            return audio

    def _resample_audio(
        self,
        audio: np.ndarray,
        orig_sr: int,
        target_sr: int = 16000
    ) -> np.ndarray:
        """
        High-quality resampling using scipy polyphase filter.

        Much better than simple decimation (Option A uses 3:1 decimation).
        Properly handles anti-aliasing to prevent artifacts.
        """
        if orig_sr == target_sr:
            return audio

        try:
            from scipy import signal

            # Calculate resampling ratio
            gcd = np.gcd(orig_sr, target_sr)
            up = target_sr // gcd
            down = orig_sr // gcd

            # Polyphase resampling (high quality, efficient)
            resampled = signal.resample_poly(audio, up, down)

            logger.debug(f"Resampled {orig_sr}Hz -> {target_sr}Hz (ratio: {up}/{down})")
            return resampled.astype(np.float32)

        except ImportError:
            # Fallback to simple decimation
            logger.warning("scipy not available, using simple decimation")
            ratio = orig_sr // target_sr
            return audio[::ratio].astype(np.float32)

    def _isolate_vocals(self, audio: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
        """
        Isolate vocals from music/effects using Demucs.

        This is the most effective preprocessing for TV content with
        background music, but adds significant latency (~0.5-1s per chunk).
        """
        if not self.enable_vocal_isolation or self.demucs_model is None:
            return audio

        try:
            import torch
            from demucs.apply import apply_model

            # Demucs expects stereo at 44.1kHz
            # We have mono at 16kHz, so need to upsample and duplicate channels

            # Upsample to 44.1kHz
            audio_44k = self._resample_audio(audio, sample_rate, 44100)

            # Convert to stereo (duplicate mono channel)
            audio_stereo = np.stack([audio_44k, audio_44k], axis=0)

            # Convert to torch tensor [batch, channels, samples]
            audio_tensor = torch.from_numpy(audio_stereo).unsqueeze(0).float()

            if self.device == 'cuda':
                audio_tensor = audio_tensor.cuda()

            # Apply Demucs separation
            with torch.no_grad():
                sources = apply_model(
                    self.demucs_model,
                    audio_tensor,
                    device=self.device if self.device == 'cuda' else 'cpu',
                    shifts=0,  # Faster (no time-shift augmentation)
                    overlap=0.25,
                )

            # Sources are: [drums, bass, other, vocals]
            # We want vocals (index 3)
            vocals = sources[0, 3].cpu().numpy()

            # Convert back to mono
            vocals_mono = vocals.mean(axis=0)

            # Resample back to 16kHz
            vocals_16k = self._resample_audio(vocals_mono, 44100, 16000)

            logger.debug("Vocal isolation applied")
            return vocals_16k.astype(np.float32)

        except Exception as e:
            logger.warning(f"Vocal isolation failed: {e}")
            return audio

    def preprocess_audio(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000
    ) -> np.ndarray:
        """
        Full preprocessing pipeline.

        Order matters:
        1. Vocal isolation (if enabled) - isolate speech from music/effects
        2. Noise reduction - clean up remaining background noise
        3. Normalization - ensure consistent levels

        Resampling is done by capture.py, but we can improve it if needed.
        """
        start = time.time()
        processed = audio.copy()

        # Step 1: Vocal isolation (most impactful but slowest)
        if self.enable_vocal_isolation:
            processed = self._isolate_vocals(processed, sample_rate)

        # Step 2: Noise reduction
        if self.enable_noise_reduction:
            processed = self._reduce_noise(processed, sample_rate)

        # Step 3: Normalization (always last)
        if self.enable_normalization:
            processed = self._normalize_audio(processed)

        elapsed = time.time() - start
        logger.debug(f"Audio preprocessing took {elapsed:.3f}s")

        return processed

    def transcribe(
        self,
        audio: np.ndarray,
        task: str = "translate",
        language: str = "ja",
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Transcribe/translate audio with preprocessing.

        Args:
            audio: Audio data as float32 numpy array (16kHz mono)
            task: 'transcribe' or 'translate'
            language: Source language code

        Returns:
            Tuple of (text, metadata_dict)
        """
        if not self._loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        total_start = time.time()

        # Ensure correct dtype
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # ============================================
        # PREPROCESSING PIPELINE
        # ============================================
        preprocess_start = time.time()
        processed_audio = self.preprocess_audio(audio, sample_rate=16000)
        preprocess_elapsed = time.time() - preprocess_start

        # ============================================
        # WHISPER TRANSCRIPTION/TRANSLATION
        # ============================================
        whisper_start = time.time()

        try:
            segments, info = self.whisper_model.transcribe(
                processed_audio,
                language=language,
                task=task,
                beam_size=self.whisper_beam_size,
                vad_filter=True,
                temperature=0.0,
                condition_on_previous_text=False,
                no_speech_threshold=0.6,
                compression_ratio_threshold=2.4,
            )

            # Collect text from segments
            text = " ".join([seg.text for seg in segments]).strip()

        except Exception as e:
            logger.error(f"Whisper error: {e}")
            text = ""

        whisper_elapsed = time.time() - whisper_start
        total_elapsed = time.time() - total_start

        # Build metadata
        metadata = {
            "engine": "enhanced",
            "whisper_model": self.whisper_model_name,
            "task": task,
            "language": language,
            "preprocess_elapsed_sec": preprocess_elapsed,
            "whisper_elapsed_sec": whisper_elapsed,
            "total_elapsed_sec": total_elapsed,
            "audio_duration_sec": len(audio) / 16000,
            "rtf": total_elapsed / (len(audio) / 16000),
            "vocal_isolation": self.enable_vocal_isolation,
            "noise_reduction": self.enable_noise_reduction,
            "normalization": self.enable_normalization,
        }

        logger.debug(
            f"Enhanced Whisper: '{text[:50]}...' "
            f"(preprocess: {preprocess_elapsed:.2f}s, whisper: {whisper_elapsed:.2f}s, "
            f"total: {total_elapsed:.2f}s, RTF: {metadata['rtf']:.2f})"
        )

        return text, metadata

    def is_loaded(self) -> bool:
        return self._loaded

    def unload(self):
        """Unload models to free memory"""
        import gc

        if self.whisper_model is not None:
            del self.whisper_model
            self.whisper_model = None

        if self.demucs_model is not None:
            del self.demucs_model
            self.demucs_model = None

        self._loaded = False

        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

        logger.info("Enhanced Whisper Engine unloaded")

    def set_preprocessing(
        self,
        vocal_isolation: Optional[bool] = None,
        noise_reduction: Optional[bool] = None,
        normalization: Optional[bool] = None,
    ):
        """
        Dynamically enable/disable preprocessing steps.

        Useful for testing or adapting to different content types.
        """
        if vocal_isolation is not None:
            if vocal_isolation and self.demucs_model is None:
                logger.warning("Cannot enable vocal isolation - Demucs not loaded")
            else:
                self.enable_vocal_isolation = vocal_isolation
                logger.info(f"Vocal isolation: {'ON' if vocal_isolation else 'OFF'}")

        if noise_reduction is not None:
            self.enable_noise_reduction = noise_reduction
            logger.info(f"Noise reduction: {'ON' if noise_reduction else 'OFF'}")

        if normalization is not None:
            self.enable_normalization = normalization
            logger.info(f"Normalization: {'ON' if normalization else 'OFF'}")
