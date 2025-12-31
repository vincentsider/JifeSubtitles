"""
SeamlessM4T v2 Speech Translation Engine
Meta's multimodal translation model for direct speech-to-text translation
"""
import logging
import time
from typing import Dict, Any, Tuple

import numpy as np
import torch

logger = logging.getLogger(__name__)


class SeamlessM4TEngine:
    """
    SeamlessM4T v2 engine for direct speech-to-text translation.

    This is fundamentally different from Whisper:
    - Whisper: ASR model with translation "hack"
    - SeamlessM4T: Purpose-built for speech translation

    Should handle messy TV audio better than Whisper.
    """

    def __init__(
        self,
        model_name: str = "seamless-m4t-v2-large",
        device: str = "cuda",
        dtype: torch.dtype = torch.float16,
    ):
        """
        Initialize SeamlessM4T engine.

        Args:
            model_name: Model variant - "seamlessM4T_v2_large" (~9GB) recommended
            device: "cuda" or "cpu"
            dtype: torch.float16 for GPU, torch.float32 for CPU
        """
        self.model_name = model_name
        self.device = device
        self.dtype = dtype
        self.model = None
        self.processor = None
        self._loaded = False

    def load(self):
        """Load the SeamlessM4T model"""
        logger.info(f"Loading SeamlessM4T model: {self.model_name}")
        start = time.time()

        try:
            from transformers import AutoProcessor, SeamlessM4Tv2ForSpeechToText

            # Load processor and model
            logger.info("Loading processor...")
            self.processor = AutoProcessor.from_pretrained(
                f"facebook/{self.model_name}",
                trust_remote_code=True,
            )

            logger.info(f"Loading model to {self.device} with {self.dtype}...")
            self.model = SeamlessM4Tv2ForSpeechToText.from_pretrained(
                f"facebook/{self.model_name}",
                torch_dtype=self.dtype,
                trust_remote_code=True,
            ).to(self.device)

            # Set to eval mode
            self.model.eval()

            self._loaded = True
            load_time = time.time() - start
            logger.info(f"SeamlessM4T model loaded in {load_time:.2f}s")

            # Log GPU memory usage
            if self.device == "cuda" and torch.cuda.is_available():
                memory_gb = torch.cuda.memory_allocated() / 1024**3
                logger.info(f"GPU memory used: {memory_gb:.2f} GB")

        except ImportError as e:
            logger.error(f"transformers not available: {e}")
            raise RuntimeError(
                "transformers not installed. Run: pip install transformers"
            )
        except Exception as e:
            logger.error(f"Failed to load SeamlessM4T model: {e}")
            raise

    def transcribe(
        self,
        audio: np.ndarray,
        task: str = "translate",  # Ignored - SeamlessM4T always translates
        language: str = "ja",  # Source language
        target_language: str = "eng",  # Target language (English)
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Translate speech to text using SeamlessM4T.

        Args:
            audio: Audio data as float32 numpy array (16kHz mono)
            task: Ignored (kept for API compatibility with Whisper)
            language: Source language code ("ja" for Japanese)
            target_language: Target language code ("eng" for English)

        Returns:
            Tuple of (translated_text, metadata_dict)
        """
        if not self._loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        start = time.time()

        # Ensure correct dtype
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # Map language codes (Whisper uses 2-letter, SeamlessM4T uses 3-letter)
        lang_map = {
            "ja": "jpn",  # Japanese
            "en": "eng",  # English
            "zh": "cmn",  # Chinese (Mandarin)
            "ko": "kor",  # Korean
        }
        src_lang = lang_map.get(language, language)

        try:
            # Process audio
            # SeamlessM4T expects 16kHz audio
            inputs = self.processor(
                audio=audio,
                sampling_rate=16000,
                return_tensors="pt",
            )

            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Generate translation
            with torch.no_grad():
                output_tokens = self.model.generate(
                    **inputs,
                    tgt_lang=target_language,
                    num_beams=5,
                    max_new_tokens=256,
                )

            # Decode output
            text = self.processor.batch_decode(
                output_tokens, skip_special_tokens=True
            )[0]

            # Clean up text
            text = text.strip()

        except Exception as e:
            logger.error(f"SeamlessM4T transcription error: {e}")
            text = ""

        elapsed = time.time() - start

        metadata = {
            "engine": "seamless_m4t",
            "model": self.model_name,
            "task": "translate",
            "source_language": src_lang,
            "target_language": target_language,
            "elapsed_sec": elapsed,
            "audio_duration_sec": len(audio) / 16000,
            "rtf": elapsed / (len(audio) / 16000),
        }

        logger.debug(
            f"SeamlessM4T: '{text}' ({elapsed:.2f}s, RTF: {metadata['rtf']:.2f})"
        )
        return text, metadata

    def is_loaded(self) -> bool:
        return self._loaded

    def unload(self):
        """Unload model to free GPU memory"""
        if self.model is not None:
            del self.model
            self.model = None
        if self.processor is not None:
            del self.processor
            self.processor = None
        self._loaded = False

        # Clear GPU cache
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("SeamlessM4T model unloaded")
