"""
Whisper ASR engine wrapper
Supports both whisper_trt (TensorRT optimized) and standard whisper backends
"""
import logging
import time
import re
from typing import Optional, Dict, Any, Tuple
from abc import ABC, abstractmethod

import numpy as np

logger = logging.getLogger(__name__)


# Hallucination patterns to filter out (case-insensitive)
# These are common Whisper hallucinations on silence/music/background noise
HALLUCINATION_PATTERNS = [
    # Thank you variations
    r'^thank you[\.!?]*$',
    r'^thank you for watching[\.!?]*$',
    r'^thank you for your [\.!?\w\s]*[\.!?]*$',
    r'^thank you for [\.!?\w\s]*[\.!?]*$',
    r'^thank you very much[\.!?]*$',
    r'^thank you so much[\.!?]*$',
    r'^thanks for watching[\.!?]*$',
    r'^thanks for [\.!?\w\s]*[\.!?]*$',
    r'^thanks[\.!?]*$',

    # Generic filler phrases
    r"^let's go[,\.!? ]*$",
    r"^what[?!,\. ]*$",
    r"^i think[\.!?, ]*$",
    r"^i'm sorry[\.!?, ]*$",
    r"^sorry[\.!?, ]*$",
    r"^that's it[\.!?, ]*$",
    r"^i can't believe it[\.!?, ]*$",
    r"^i don't believe it[\.!?, ]*$",
    r'^oh my god[\.!?, ]*$',
    r'^oh my[\.!?, ]*$',
    r'^wow[\.!?, ]*$',
    r'^bye[\.!?, ]*$',
    r'^see you[\.!?, ]*$',
    r'^goodbye[\.!?, ]*$',
    r'^okay[\.!?, ]*$',
    r'^alright[\.!?, ]*$',
    r'^yeah[\.!?, ]*$',
    r'^yes[\.!?, ]*$',
    r'^no[\.!?, ]*$',
    r'^uh[\.!?, ]*$',
    r'^um[\.!?, ]*$',
    r'^huh[\.!?, ]*$',
    r'^please subscribe[\.!?, ]*$',
    r'^subscribe[\.!?, ]*$',

    # Common hallucinations on music/noise
    r"^i'?m? (going to|gonna) kill you[\.!?, ]*$",
    r"^i'?m? (going to|gonna) die[\.!?, ]*$",
    r"^i don'?t know[\.!?, ]*$",
]


def is_hallucination(text: str) -> bool:
    """
    Check if text is likely a hallucination (generic filler phrase).
    Returns True if text should be filtered out.
    """
    if not text or len(text.strip()) < 2:
        return True

    text_lower = text.lower().strip()

    # Check for repetitions (e.g., "phrase, phrase" or "phrase. phrase")
    delimiters = [',', '.', '!', '?', ';']
    for delim in delimiters:
        if delim in text_lower:
            parts = [p.strip() for p in text_lower.split(delim) if p.strip()]
            if len(parts) >= 2:
                for part in parts:
                    if len(part) >= 5 and parts.count(part) >= 2:
                        logger.debug(f"Filtered repetitive hallucination: '{text}'")
                        return True

    # Check against known hallucination patterns
    for pattern in HALLUCINATION_PATTERNS:
        if re.match(pattern, text_lower):
            logger.debug(f"Filtered hallucination: '{text}'")
            return True

    return False


class WhisperEngine(ABC):
    """Abstract base class for Whisper engines"""

    @abstractmethod
    def transcribe(
        self,
        audio: np.ndarray,
        task: str = 'translate',
        language: str = 'ja',
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Transcribe/translate audio to text.

        Args:
            audio: Audio data as float32 numpy array (16kHz mono)
            task: 'transcribe' or 'translate'
            language: Source language code

        Returns:
            Tuple of (text, metadata_dict)
        """
        pass

    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if model is loaded and ready"""
        pass


class WhisperTRTEngine(WhisperEngine):
    """TensorRT-optimized Whisper engine for Jetson"""

    def __init__(self, model_name: str = 'small', beam_size: int = 5):
        self.model_name = model_name
        self.beam_size = beam_size
        self.model = None
        self._loaded = False

    def load(self):
        """Load the WhisperTRT model"""
        logger.info(f"Loading WhisperTRT model: {self.model_name}")
        start = time.time()

        try:
            from whisper_trt import load_trt_model

            # First load builds TensorRT engine, cached after that
            self.model = load_trt_model(self.model_name)
            self._loaded = True

            load_time = time.time() - start
            logger.info(f"WhisperTRT model loaded in {load_time:.2f}s")

        except ImportError as e:
            logger.error(f"whisper_trt not available: {e}")
            raise RuntimeError("whisper_trt not installed. Use standard Whisper backend.")
        except Exception as e:
            logger.error(f"Failed to load WhisperTRT model: {e}")
            raise

    def transcribe(
        self,
        audio: np.ndarray,
        task: str = 'translate',
        language: str = 'ja',
    ) -> Tuple[str, Dict[str, Any]]:
        """Transcribe using WhisperTRT"""
        if not self._loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        start = time.time()

        # Ensure correct dtype and shape
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # WhisperTRT transcribe
        result = self.model.transcribe(
            audio,
            language=language,
            task=task,
            beam_size=self.beam_size,
        )

        elapsed = time.time() - start

        text = result.get('text', '').strip()
        metadata = {
            'engine': 'whisper_trt',
            'model': self.model_name,
            'task': task,
            'language': language,
            'elapsed_sec': elapsed,
            'audio_duration_sec': len(audio) / 16000,
            'rtf': elapsed / (len(audio) / 16000),  # Real-time factor
        }

        logger.debug(f"WhisperTRT: '{text}' ({elapsed:.2f}s, RTF: {metadata['rtf']:.2f})")
        return text, metadata

    def is_loaded(self) -> bool:
        return self._loaded


class StandardWhisperEngine(WhisperEngine):
    """Standard Whisper engine (fallback when TRT not available)"""

    def __init__(self, model_name: str = 'small', beam_size: int = 5):
        self.model_name = model_name
        self.beam_size = beam_size
        self.model = None
        self._loaded = False

    def load(self):
        """Load the standard Whisper model"""
        logger.info(f"Loading standard Whisper model: {self.model_name}")
        start = time.time()

        try:
            import whisper

            self.model = whisper.load_model(self.model_name)
            self._loaded = True

            load_time = time.time() - start
            logger.info(f"Whisper model loaded in {load_time:.2f}s")

        except ImportError as e:
            logger.error(f"whisper not available: {e}")
            raise RuntimeError("whisper not installed.")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise

    def transcribe(
        self,
        audio: np.ndarray,
        task: str = 'translate',
        language: str = 'ja',
    ) -> Tuple[str, Dict[str, Any]]:
        """Transcribe using standard Whisper"""
        if not self._loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        start = time.time()

        # Ensure correct dtype
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        result = self.model.transcribe(
            audio,
            language=language,
            task=task,
            beam_size=self.beam_size,
        )

        elapsed = time.time() - start

        text = result.get('text', '').strip()
        metadata = {
            'engine': 'whisper',
            'model': self.model_name,
            'task': task,
            'language': language,
            'elapsed_sec': elapsed,
            'audio_duration_sec': len(audio) / 16000,
            'rtf': elapsed / (len(audio) / 16000),
        }

        logger.debug(f"Whisper: '{text}' ({elapsed:.2f}s, RTF: {metadata['rtf']:.2f})")
        return text, metadata

    def is_loaded(self) -> bool:
        return self._loaded


class FasterWhisperEngine(WhisperEngine):
    """faster-whisper engine using CTranslate2 (if available)"""

    def __init__(self, model_name: str = 'small', beam_size: int = 5, device: str = 'cuda', compute_type: str = None):
        self.model_name = model_name
        self.beam_size = beam_size
        self.device = device
        # compute_type options for GPU: float16, int8_float16, int8
        # int8_float16 uses ~50% less VRAM than float16
        self.compute_type = compute_type
        self.model = None
        self._loaded = False

    def load(self):
        """Load the faster-whisper model"""
        logger.info(f"Loading faster-whisper model: {self.model_name}")
        start = time.time()

        try:
            from faster_whisper import WhisperModel

            # Determine compute type
            if self.compute_type:
                ct = self.compute_type
            elif self.device == 'cuda':
                ct = 'float16'
            else:
                ct = 'int8'

            # Try CUDA first, fall back to CPU
            try:
                logger.info(f"Loading with device={self.device}, compute_type={ct}")
                self.model = WhisperModel(
                    self.model_name,
                    device=self.device,
                    compute_type=ct,
                )
            except Exception as e:
                logger.warning(f"CUDA failed ({e}), falling back to CPU")
                self.model = WhisperModel(self.model_name, device='cpu', compute_type='int8')

            self._loaded = True

            load_time = time.time() - start
            logger.info(f"faster-whisper model loaded in {load_time:.2f}s")

        except ImportError as e:
            logger.error(f"faster-whisper not available: {e}")
            raise RuntimeError("faster-whisper not installed.")
        except Exception as e:
            logger.error(f"Failed to load faster-whisper model: {e}")
            raise

    def transcribe(
        self,
        audio: np.ndarray,
        task: str = 'translate',
        language: str = 'ja',
    ) -> Tuple[str, Dict[str, Any]]:
        """Transcribe using faster-whisper"""
        if not self._loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        start = time.time()

        # Ensure correct dtype
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # kotoba-whisper-bilingual requires language='en' for JP->EN translation
        # Standard Whisper requires language='ja' (source language)
        actual_language = language
        if 'kotoba-whisper' in self.model_name and task == 'translate':
            actual_language = 'en'  # kotoba uses target language for translation
            logger.debug(f"kotoba-whisper detected, using language='en' for translation")

        segments, info = self.model.transcribe(
            audio,
            language=actual_language,
            task=task,
            beam_size=self.beam_size,
            vad_filter=True,
            temperature=0.0,  # Deterministic output (no randomness)
            condition_on_previous_text=False,  # Prevents repetition loops with short chunks
            no_speech_threshold=0.5,  # Balanced (higher = skip more silence)
        )

        # Collect text from segments
        text = ' '.join([seg.text for seg in segments]).strip()

        # Filter hallucinations
        if is_hallucination(text):
            text = ''  # Return empty string for hallucinations

        elapsed = time.time() - start

        metadata = {
            'engine': 'faster_whisper',
            'model': self.model_name,
            'task': task,
            'language': language,
            'elapsed_sec': elapsed,
            'audio_duration_sec': len(audio) / 16000,
            'rtf': elapsed / (len(audio) / 16000),
            'detected_language': info.language if info else None,
            'language_probability': info.language_probability if info else None,
        }

        logger.debug(f"faster-whisper: '{text}' ({elapsed:.2f}s, RTF: {metadata['rtf']:.2f})")
        return text, metadata

    def is_loaded(self) -> bool:
        return self._loaded


def create_engine(
    backend: str = 'whisper_trt',
    model_name: str = 'small',
    beam_size: int = 5,
    compute_type: str = None,
) -> WhisperEngine:
    """
    Factory function to create the appropriate Whisper engine.

    Args:
        backend: 'whisper_trt', 'faster_whisper', or 'whisper'
        model_name: Model size ('tiny', 'base', 'small', 'medium', 'large', 'large-v3')
                    or HuggingFace model ID (e.g., 'kotoba-tech/kotoba-whisper-bilingual-v1.0-faster')
        beam_size: Beam size for decoding
        compute_type: For faster_whisper: 'float16', 'int8_float16', 'int8' (GPU)
                      int8_float16 uses ~50% less VRAM than float16

    Returns:
        WhisperEngine instance
    """
    engines = {
        'whisper_trt': WhisperTRTEngine,
        'faster_whisper': FasterWhisperEngine,
        'whisper': StandardWhisperEngine,
    }

    if backend not in engines:
        raise ValueError(f"Unknown backend: {backend}. Available: {list(engines.keys())}")

    # Pass compute_type only to faster_whisper
    if backend == 'faster_whisper':
        engine = engines[backend](model_name=model_name, beam_size=beam_size, compute_type=compute_type)
    else:
        engine = engines[backend](model_name=model_name, beam_size=beam_size)

    # Try to load, with fallback
    try:
        engine.load()
        return engine
    except Exception as e:
        logger.warning(f"Failed to load {backend}: {e}")

        # Try fallbacks
        fallback_order = ['whisper_trt', 'faster_whisper', 'whisper']
        for fallback in fallback_order:
            if fallback != backend:
                try:
                    logger.info(f"Trying fallback engine: {fallback}")
                    engine = engines[fallback](model_name=model_name, beam_size=beam_size)
                    engine.load()
                    return engine
                except Exception:
                    continue

        raise RuntimeError("No Whisper backend available")
