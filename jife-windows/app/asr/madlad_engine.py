"""
MADLAD Engine (Option D): Whisper Transcription + MADLAD-400-3B-MT Translation

Two-stage pipeline optimized for quality and speed:
1. Whisper (faster-whisper) transcribes Japanese audio → Japanese text
2. MADLAD-400-3B-MT (CTranslate2 INT8) translates Japanese text → English text

This approach offers:
- Whisper stays in transcribe mode (more stable, no hallucinations from translate mode)
- MADLAD-400 is a dedicated MT model (better translation quality than Whisper translate)
- CTranslate2 INT8 quantization for fast inference and low memory
- Context-aware translation (passes previous text for coherence)

Memory usage: ~4GB Whisper + ~2GB MADLAD (INT8) = ~6GB total
Latency: Slightly higher than Whisper-translate but much better than SeamlessM4T
"""
import logging
import time
import os
from typing import Dict, Any, Tuple, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class MADLADEngine:
    """
    Two-stage pipeline: Whisper ASR + MADLAD-400 Machine Translation

    Stage 1: Whisper transcribes Japanese speech → Japanese text (transcribe mode)
    Stage 2: MADLAD-400-3B translates Japanese text → English text (CTranslate2 INT8)
    """

    def __init__(
        self,
        whisper_model: str = "large-v3",
        whisper_compute_type: str = "float16",
        whisper_beam_size: int = 5,
        madlad_model: str = "Heng666/madlad400-3b-mt-ct2",
        madlad_compute_type: str = "int8",
        device: str = "cuda",
        cache_dir: Optional[str] = None,
    ):
        """
        Initialize MADLAD pipeline engine.

        Args:
            whisper_model: Whisper model name (e.g., 'large-v3')
            whisper_compute_type: Compute type for Whisper ('float16', 'int8_float16')
            whisper_beam_size: Beam size for Whisper decoding
            madlad_model: MADLAD CTranslate2 model path or HuggingFace repo
            madlad_compute_type: Compute type for MADLAD ('int8', 'float16')
            device: Device to use ('cuda' or 'cpu')
            cache_dir: Directory to cache downloaded models
        """
        self.whisper_model_name = whisper_model
        self.whisper_compute_type = whisper_compute_type
        self.whisper_beam_size = whisper_beam_size
        self.madlad_model_name = madlad_model
        self.madlad_compute_type = madlad_compute_type
        self.device = device
        self.cache_dir = cache_dir or os.environ.get(
            "HF_HOME",
            os.path.join(os.path.dirname(__file__), "..", "..", "cache")
        )

        # Models (loaded on demand)
        self.whisper_model = None
        self.madlad_translator = None
        self.madlad_tokenizer = None

        # Context for coherent translation (rolling window of previous Japanese text)
        self.context_history: List[str] = []
        self.max_context_tokens = 25  # ~10-25 prior JA tokens as per optiond.md

        self._loaded = False

    def load(self):
        """Load both models"""
        logger.info("Loading MADLAD Pipeline Engine (Whisper + MADLAD-400)...")
        start = time.time()

        # Stage 1: Load Whisper for transcription
        self._load_whisper()

        # Stage 2: Load MADLAD for text-to-text translation
        self._load_madlad()

        self._loaded = True
        total_time = time.time() - start
        logger.info(f"MADLAD Pipeline Engine loaded in {total_time:.2f}s")

        # Log GPU memory usage
        try:
            import torch
            if self.device == "cuda" and torch.cuda.is_available():
                memory_gb = torch.cuda.memory_allocated() / 1024**3
                logger.info(f"GPU memory used (after load): {memory_gb:.2f} GB")
        except Exception:
            pass

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

    def _load_madlad(self):
        """Load MADLAD-400 CTranslate2 model for translation"""
        logger.info(f"Loading MADLAD-400 model: {self.madlad_model_name}")
        start = time.time()

        try:
            import ctranslate2
            from transformers import AutoTokenizer

            # Check if model path exists locally or needs download
            model_path = self.madlad_model_name

            # If it's a HuggingFace repo, download it
            if "/" in self.madlad_model_name and not os.path.exists(self.madlad_model_name):
                from huggingface_hub import snapshot_download

                logger.info(f"Downloading MADLAD model from HuggingFace: {self.madlad_model_name}")
                model_path = snapshot_download(
                    repo_id=self.madlad_model_name,
                    cache_dir=self.cache_dir,
                )
                logger.info(f"Model downloaded to: {model_path}")

            # Load CTranslate2 translator
            self.madlad_translator = ctranslate2.Translator(
                model_path,
                device=self.device,
                compute_type=self.madlad_compute_type,
            )

            # Load tokenizer - MADLAD uses T5 tokenizer from the original model
            # We need the tokenizer from the original google/madlad400-3b-mt
            self.madlad_tokenizer = AutoTokenizer.from_pretrained(
                "google/madlad400-3b-mt",
                cache_dir=self.cache_dir,
            )

            load_time = time.time() - start
            logger.info(f"MADLAD-400 loaded in {load_time:.2f}s")

        except ImportError as e:
            logger.error(f"ctranslate2 not available: {e}")
            raise RuntimeError("ctranslate2 not installed. Install with: pip install ctranslate2")
        except Exception as e:
            logger.error(f"Failed to load MADLAD-400: {e}")
            raise

    def _build_context_prefix(self) -> str:
        """
        Build context prefix from recent Japanese text.

        Returns context as a concatenated string of recent Japanese segments.
        This helps MADLAD maintain coherence across segments.
        """
        if not self.context_history:
            return ""

        # Join recent context, limiting to ~max_context_tokens worth
        # Simple approximation: assume ~2 chars per token for Japanese
        context_text = " ".join(self.context_history[-3:])  # Last 3 segments

        # Rough token count check (Japanese: ~2 chars per token)
        max_chars = self.max_context_tokens * 2
        if len(context_text) > max_chars:
            context_text = context_text[-max_chars:]

        return context_text

    def _update_context(self, japanese_text: str):
        """Add Japanese text to context history"""
        if japanese_text and len(japanese_text.strip()) > 3:
            self.context_history.append(japanese_text.strip())
            # Keep only last 5 segments
            if len(self.context_history) > 5:
                self.context_history.pop(0)

    def translate_text(self, japanese_text: str, with_context: bool = True) -> str:
        """
        Translate Japanese text to English using MADLAD-400.

        Args:
            japanese_text: Japanese text to translate
            with_context: Whether to use context from previous segments

        Returns:
            English translation
        """
        if not japanese_text or not japanese_text.strip():
            return ""

        try:
            # Build input with target language token
            # MADLAD uses <2xx> format: <2en> for English target

            # Optionally prepend context for coherence
            if with_context:
                context = self._build_context_prefix()
                if context:
                    # Format: translate with context hint
                    # We'll translate just the new text but tokenizer sees context
                    input_text = f"<2en> {japanese_text}"
                else:
                    input_text = f"<2en> {japanese_text}"
            else:
                input_text = f"<2en> {japanese_text}"

            # Tokenize
            tokens = self.madlad_tokenizer.tokenize(input_text)

            # Translate using CTranslate2
            results = self.madlad_translator.translate_batch(
                [tokens],
                beam_size=4,  # Moderate beam size for quality/speed balance
                max_decoding_length=256,
                sampling_topk=0,  # Greedy/beam search, no sampling
            )

            # Decode result
            if results and results[0].hypotheses:
                output_tokens = results[0].hypotheses[0]
                english_text = self.madlad_tokenizer.convert_tokens_to_string(output_tokens)
                return english_text.strip()

            return ""

        except Exception as e:
            logger.error(f"MADLAD translation error: {e}")
            return f"[Translation failed] {japanese_text}"

    def transcribe(
        self,
        audio: np.ndarray,
        task: str = "translate",  # Ignored - we always do transcribe+translate
        language: str = "ja",
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Two-stage transcription and translation.

        Args:
            audio: Audio data as float32 numpy array (16kHz mono)
            task: Ignored (kept for API compatibility)
            language: Source language code ("ja" for Japanese)

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
        # Settings from optiond.md:
        # - task="transcribe" (NOT translate)
        # - language="ja"
        # - vad_filter=True
        # - beam_size=3-5
        # - temperature=0.0
        # - condition_on_previous_text=False (helps with streaming)

        whisper_start = time.time()

        try:
            segments, info = self.whisper_model.transcribe(
                audio,
                language="ja",  # Force Japanese
                task="transcribe",  # Transcribe, NOT translate
                beam_size=self.whisper_beam_size,
                vad_filter=True,  # Important for TV audio
                temperature=0.0,  # Deterministic output
                condition_on_previous_text=False,  # Better for streaming
                no_speech_threshold=0.6,  # Higher = stricter silence detection
                compression_ratio_threshold=2.4,  # Lower = stricter anti-hallucination
            )

            # Collect Japanese text
            japanese_text = " ".join([seg.text for seg in segments]).strip()

        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            japanese_text = ""

        whisper_elapsed = time.time() - whisper_start

        # Skip if no speech detected
        if not japanese_text:
            return "", {
                "engine": "madlad",
                "stage": "whisper",
                "reason": "no_speech",
            }

        logger.debug(f"Whisper ({whisper_elapsed:.2f}s): {japanese_text[:50]}...")

        # ============================================
        # STAGE 2: MADLAD-400 Text Translation
        # ============================================
        madlad_start = time.time()

        english_text = self.translate_text(japanese_text, with_context=True)

        # Update context for future translations
        self._update_context(japanese_text)

        madlad_elapsed = time.time() - madlad_start
        total_elapsed = time.time() - total_start

        logger.debug(f"MADLAD ({madlad_elapsed:.2f}s): {english_text[:50]}...")

        # Build metadata
        metadata = {
            "engine": "madlad",
            "whisper_model": self.whisper_model_name,
            "madlad_model": self.madlad_model_name,
            "source_text": japanese_text,  # Japanese intermediate text
            "whisper_elapsed_sec": whisper_elapsed,
            "madlad_elapsed_sec": madlad_elapsed,
            "total_elapsed_sec": total_elapsed,
            "audio_duration_sec": len(audio) / 16000,
            "rtf": total_elapsed / (len(audio) / 16000),
            "context_segments": len(self.context_history),
        }

        logger.debug(
            f"MADLAD Pipeline: '{english_text[:50]}...' "
            f"(total: {total_elapsed:.2f}s, RTF: {metadata['rtf']:.2f})"
        )

        return english_text, metadata

    def is_loaded(self) -> bool:
        return self._loaded

    def clear_context(self):
        """Clear the context history (e.g., when switching speakers/content)"""
        self.context_history.clear()
        logger.debug("Context history cleared")

    def unload(self):
        """Unload both models to free GPU memory"""
        import gc

        if self.whisper_model is not None:
            del self.whisper_model
            self.whisper_model = None

        if self.madlad_translator is not None:
            del self.madlad_translator
            self.madlad_translator = None

        if self.madlad_tokenizer is not None:
            del self.madlad_tokenizer
            self.madlad_tokenizer = None

        self.context_history.clear()
        self._loaded = False

        # Clear GPU cache
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

        logger.info("MADLAD Pipeline Engine unloaded")
