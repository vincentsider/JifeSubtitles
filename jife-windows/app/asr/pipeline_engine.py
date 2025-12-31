"""
Pipeline Engine (Option C): Whisper Transcription + SeamlessM4T Text Translation

Two-stage pipeline for highest quality Japanese→English translation:
1. Whisper (faster-whisper) transcribes Japanese audio → Japanese text
2. SeamlessM4T v2 translates Japanese text → English text

This approach offers:
- Better transcription accuracy (Whisper in native transcribe mode)
- Better translation quality (SeamlessM4T's text-to-text strength)
- Intermediate Japanese text for debugging/display

Trade-off: Higher latency (~2x) and more VRAM usage (~13-14GB total)
"""
import logging
import time
from typing import Dict, Any, Tuple

import numpy as np
import torch

logger = logging.getLogger(__name__)


class PipelineEngine:
    """
    Two-stage pipeline: Whisper ASR + SeamlessM4T Text Translation

    Stage 1: Whisper transcribes Japanese speech → Japanese text
    Stage 2: SeamlessM4T translates Japanese text → English text
    """

    def __init__(
        self,
        whisper_model: str = "large-v3",
        whisper_compute_type: str = "float16",
        whisper_beam_size: int = 5,
        seamless_model: str = "seamless-m4t-v2-large",
        device: str = "cuda",
    ):
        """
        Initialize pipeline engine.

        Args:
            whisper_model: Whisper model name (e.g., 'large-v3')
            whisper_compute_type: Compute type for Whisper ('float16', 'int8_float16')
            whisper_beam_size: Beam size for Whisper decoding
            seamless_model: SeamlessM4T model name
            device: Device to use ('cuda' or 'cpu')
        """
        self.whisper_model_name = whisper_model
        self.whisper_compute_type = whisper_compute_type
        self.whisper_beam_size = whisper_beam_size
        self.seamless_model_name = seamless_model
        self.device = device

        # Models (loaded on demand)
        self.whisper_model = None
        self.seamless_model = None
        self.seamless_processor = None

        self._loaded = False

    def load(self):
        """Load both models"""
        logger.info("Loading Pipeline Engine (Whisper + SeamlessM4T)...")
        start = time.time()

        # Stage 1: Load Whisper for transcription
        self._load_whisper()

        # Stage 2: Load SeamlessM4T for text-to-text translation
        self._load_seamless_t2t()

        self._loaded = True
        total_time = time.time() - start
        logger.info(f"Pipeline Engine loaded in {total_time:.2f}s")

        # Log GPU memory usage
        if self.device == "cuda" and torch.cuda.is_available():
            memory_gb = torch.cuda.memory_allocated() / 1024**3
            logger.info(f"Total GPU memory used: {memory_gb:.2f} GB")

    def _load_whisper(self):
        """Load Whisper model for Japanese transcription"""
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

    def _load_seamless_t2t(self):
        """Load SeamlessM4T for text-to-text translation"""
        logger.info(f"Loading SeamlessM4T T2T: {self.seamless_model_name}")
        start = time.time()

        try:
            from transformers import AutoProcessor, SeamlessM4Tv2ForTextToText

            # Load processor
            self.seamless_processor = AutoProcessor.from_pretrained(
                f"facebook/{self.seamless_model_name}",
                trust_remote_code=True,
            )

            # Load text-to-text model (NOT speech-to-text!)
            # This is smaller and faster than the speech model
            self.seamless_model = SeamlessM4Tv2ForTextToText.from_pretrained(
                f"facebook/{self.seamless_model_name}",
                torch_dtype=torch.float16,
                trust_remote_code=True,
            ).to(self.device)

            self.seamless_model.eval()

            load_time = time.time() - start
            logger.info(f"SeamlessM4T T2T loaded in {load_time:.2f}s")

        except Exception as e:
            logger.error(f"Failed to load SeamlessM4T T2T: {e}")
            raise

    def transcribe(
        self,
        audio: np.ndarray,
        task: str = "translate",  # Ignored - we always do transcribe+translate
        language: str = "ja",
        target_language: str = "eng",
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Two-stage transcription and translation.

        Args:
            audio: Audio data as float32 numpy array (16kHz mono)
            task: Ignored (kept for API compatibility)
            language: Source language code ("ja" for Japanese)
            target_language: Target language code ("eng" for English)

        Returns:
            Tuple of (english_text, metadata_dict)
        """
        if not self._loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        total_start = time.time()

        # Ensure correct dtype
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # ============================================
        # STAGE 1: Whisper Japanese Transcription
        # ============================================
        whisper_start = time.time()

        segments, info = self.whisper_model.transcribe(
            audio,
            language="ja",  # Force Japanese
            task="transcribe",  # Transcribe, NOT translate
            beam_size=self.whisper_beam_size,
            vad_filter=True,
            condition_on_previous_text=True,  # Better context continuity
        )

        # Collect Japanese text
        japanese_text = " ".join([seg.text for seg in segments]).strip()
        whisper_elapsed = time.time() - whisper_start

        # Skip if no speech detected
        if not japanese_text:
            return "", {
                "engine": "pipeline",
                "stage": "whisper",
                "reason": "no_speech",
            }

        logger.debug(f"Whisper ({whisper_elapsed:.2f}s): {japanese_text[:50]}...")

        # ============================================
        # STAGE 2: SeamlessM4T Text Translation
        # ============================================
        seamless_start = time.time()

        try:
            # Tokenize Japanese text
            inputs = self.seamless_processor(
                text=japanese_text,
                src_lang="jpn",
                return_tensors="pt",
            ).to(self.device)

            # Generate English translation
            with torch.no_grad():
                output_tokens = self.seamless_model.generate(
                    **inputs,
                    tgt_lang="eng",
                    num_beams=5,
                    max_new_tokens=256,
                )

            # Decode to English text
            english_text = self.seamless_processor.batch_decode(
                output_tokens, skip_special_tokens=True
            )[0].strip()

        except Exception as e:
            logger.error(f"SeamlessM4T translation error: {e}")
            # Fallback: return Japanese text if translation fails
            english_text = f"[Translation failed] {japanese_text}"

        seamless_elapsed = time.time() - seamless_start
        total_elapsed = time.time() - total_start

        logger.debug(f"SeamlessM4T ({seamless_elapsed:.2f}s): {english_text[:50]}...")

        # Build metadata
        metadata = {
            "engine": "pipeline",
            "whisper_model": self.whisper_model_name,
            "seamless_model": self.seamless_model_name,
            "source_text": japanese_text,  # Japanese intermediate text
            "whisper_elapsed_sec": whisper_elapsed,
            "seamless_elapsed_sec": seamless_elapsed,
            "total_elapsed_sec": total_elapsed,
            "audio_duration_sec": len(audio) / 16000,
            "rtf": total_elapsed / (len(audio) / 16000),
        }

        logger.debug(
            f"Pipeline: '{english_text[:50]}...' "
            f"(total: {total_elapsed:.2f}s, RTF: {metadata['rtf']:.2f})"
        )

        return english_text, metadata

    def is_loaded(self) -> bool:
        return self._loaded

    def unload(self):
        """Unload both models to free GPU memory"""
        if self.whisper_model is not None:
            del self.whisper_model
            self.whisper_model = None

        if self.seamless_model is not None:
            del self.seamless_model
            self.seamless_model = None

        if self.seamless_processor is not None:
            del self.seamless_processor
            self.seamless_processor = None

        self._loaded = False

        # Clear GPU cache
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("Pipeline Engine unloaded")
