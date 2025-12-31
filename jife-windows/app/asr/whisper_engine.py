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
# Pattern explanation: [\.!?]* matches any combination of . ! ? at the end
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

    # DISABLED - These were blocking legitimate translations
    # Only keeping core non-speech hallucinations (thank you, subscribe, etc.)
]


def is_hallucination(text: str) -> bool:
    """
    Check if text is likely a hallucination (generic filler phrase).
    Returns True if text should be filtered out.
    """
    if not text or len(text.strip()) < 2:
        return True

    text_lower = text.lower().strip()

    # Check for repetitions (e.g., "I'm so hot today I don't care, I'm so hot today I don't care")
    # Split by common delimiters and check if any phrase repeats
    delimiters = [',', '.', '!', '?', ';']
    for delim in delimiters:
        if delim in text_lower:
            parts = [p.strip() for p in text_lower.split(delim) if p.strip()]
            if len(parts) >= 2:
                # Check if any part appears more than once
                for part in parts:
                    if len(part) >= 5 and parts.count(part) >= 2:
                        logger.debug(f"Filtered repetitive hallucination: '{text}'")
                        return True

    # Check against known hallucination patterns
    for pattern in HALLUCINATION_PATTERNS:
        if re.match(pattern, text_lower):
            logger.debug(f"Filtered hallucination: '{text}'")
            return True

    # Additional substring check for "thank you" variations that slip through
    # (as a fallback if regex doesn't catch it)
    if text_lower.startswith('thank you') or text_lower.startswith('thanks'):
        # Filter ALL phrases starting with "thank you" or "thanks"
        # These are ALWAYS hallucinations on music/silence
        logger.debug(f"Filtered thank-you hallucination: '{text}'")
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
        # Rolling context for better transcription across chunks
        self._context_prompt = None
        self._context_history = []  # Last N sentences for context

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
        target_language: str = 'en',
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Transcribe using faster-whisper.

        NOTE: Whisper's 'translate' task ONLY translates to English.
        For other languages (e.g., Japanese->French), we must:
        1. Transcribe to Japanese text (task='transcribe')
        2. Use a separate translation model (e.g., NLLB, M2M100)

        Args:
            audio: Audio data
            task: 'translate' (JP->EN only) or 'transcribe' (JP->JP)
            language: Source language (ja)
            target_language: Target language (en, fr, es, etc.)
        """
        if not self._loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        start = time.time()

        # Ensure correct dtype
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # Whisper translate task only works for English target
        # For other languages, transcribe to Japanese first
        if task == 'translate' and target_language != 'en':
            logger.info(f"Whisper translate only supports English. Using transcribe + translation for {target_language}")
            actual_task = 'transcribe'
        else:
            actual_task = task

        # kotoba-whisper-bilingual requires language='en' for JP->EN translation
        # Standard Whisper requires language='ja' (source language)
        actual_language = language
        if 'kotoba-whisper' in self.model_name and actual_task == 'translate':
            actual_language = 'en'  # kotoba uses target language for translation
            logger.debug(f"kotoba-whisper detected, using language='en' for translation")

        # Import config to get temperature
        from app.config import get_config
        config = get_config()

        segments, info = self.model.transcribe(
            audio,
            language=actual_language,
            task=actual_task,
            beam_size=self.beam_size,
            best_of=self.beam_size * 2,  # Search more candidates for better quality
            patience=2.0,  # More patience in beam search for better results
            temperature=config.WHISPER_TEMPERATURE,  # Deterministic output (0.0 = no randomness)
            vad_filter=False,  # DISABLED - was filtering too aggressively and blocking real speech
            max_initial_timestamp=1.0,  # Reduced from 2.0 to reduce hallucinations
            hallucination_silence_threshold=2.0,  # Higher = more filtering of silence hallucinations
            compression_ratio_threshold=2.4,  # Skip if compression is too high (repetitive text)
            log_prob_threshold=-1.0,  # Skip low confidence segments
            no_speech_threshold=0.5,  # LOWERED from 0.7 - was skipping too much dialogue
            condition_on_previous_text=False,  # DISABLE - was causing repetition loops
            initial_prompt=None,  # No context prompt
        )

        # Collect text from segments
        text = ' '.join([seg.text for seg in segments]).strip()

        # If we transcribed Japanese but need French/other, translate it
        if actual_task == 'transcribe' and target_language != 'ja':
            text = self._translate_text(text, source_lang='ja', target_lang=target_language)

        # Filter out hallucinations
        if is_hallucination(text):
            text = ''  # Return empty string for hallucinations

        # Update rolling context with new text
        if text and len(text.strip()) >= 2:
            self._update_context(text)

        elapsed = time.time() - start

        metadata = {
            'engine': 'faster_whisper',
            'model': self.model_name,
            'task': task,
            'language': language,
            'target_language': target_language,
            'elapsed_sec': elapsed,
            'audio_duration_sec': len(audio) / 16000,
            'rtf': elapsed / (len(audio) / 16000),
            'detected_language': info.language if info else None,
            'language_probability': info.language_probability if info else None,
        }

        logger.debug(f"faster-whisper: '{text}' ({elapsed:.2f}s, RTF: {metadata['rtf']:.2f})")
        return text, metadata

    def _update_context(self, text: str):
        """Update rolling context prompt with new text (keep last 3 sentences)"""
        # Add to history
        self._context_history.append(text)

        # Keep only last 3 items for context (balance: enough context, not too much)
        if len(self._context_history) > 3:
            self._context_history = self._context_history[-3:]

        # Join as prompt (Whisper uses this as context for next transcription)
        self._context_prompt = ' '.join(self._context_history)

    def _translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Translate text from source to target language using M2M100 model.
        This is used when Whisper transcribes Japanese but we need French/other output.

        NOTE: This loads the translation model on-demand (first time only).
        """
        if not text or len(text.strip()) < 2:
            return text

        try:
            # Lazy load translation model
            if not hasattr(self, '_translator'):
                logger.info(f"Loading M2M100 translation model for {source_lang}->{target_lang}...")
                from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer

                model_name = "facebook/m2m100_418M"  # Smaller model, ~1GB
                self._translator_model = M2M100ForConditionalGeneration.from_pretrained(model_name)
                self._translator_tokenizer = M2M100Tokenizer.from_pretrained(model_name)

                # Move to GPU if available
                if self.device == 'cuda':
                    self._translator_model = self._translator_model.to('cuda')

                logger.info("Translation model loaded")

            # Translate
            self._translator_tokenizer.src_lang = source_lang
            encoded = self._translator_tokenizer(text, return_tensors="pt")

            if self.device == 'cuda':
                encoded = {k: v.to('cuda') for k, v in encoded.items()}

            # Generate translation
            generated_tokens = self._translator_model.generate(
                **encoded,
                forced_bos_token_id=self._translator_tokenizer.get_lang_id(target_lang),
                max_length=512,
            )

            translated = self._translator_tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
            logger.debug(f"Translated: '{text}' -> '{translated}' ({source_lang}->{target_lang})")
            return translated

        except Exception as e:
            logger.error(f"Translation failed: {e}. Returning original text.")
            return text

    def transcribe_streaming(
        self,
        audio_iterator,
        task: str = 'translate',
        language: str = 'ja',
        target_language: str = 'en',
    ):
        """
        Stream transcription using faster-whisper's streaming API.
        Yields (text, metadata) tuples as they become available.

        Args:
            audio_iterator: Iterator that yields numpy audio chunks
            task: 'transcribe' or 'translate'
            language: Source language code
            target_language: Target language (en, fr, es, etc.)

        Yields:
            (text, metadata) tuples for each transcribed segment
        """
        if not self._loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        # Whisper translate only works for English target
        if task == 'translate' and target_language != 'en':
            logger.info(f"Streaming: Using transcribe + translation for {target_language}")
            actual_task = 'transcribe'
        else:
            actual_task = task

        actual_language = language
        if 'kotoba-whisper' in self.model_name and actual_task == 'translate':
            actual_language = 'en'

        # Accumulate audio chunks for streaming transcription
        # faster-whisper processes audio in overlapping windows internally
        for audio_chunk in audio_iterator:
            if audio_chunk.dtype != np.float32:
                audio_chunk = audio_chunk.astype(np.float32)

            start = time.time()

            # Use transcribe with streaming=True (processes incrementally)
            segments, info = self.model.transcribe(
                audio_chunk,
                language=actual_language,
                task=actual_task,
                beam_size=self.beam_size,
                best_of=self.beam_size * 2,  # Search more candidates for better quality
                patience=2.0,  # More patience in beam search
                vad_filter=False,
                max_initial_timestamp=2.0,  # More context
                hallucination_silence_threshold=0.5,  # Reduce hallucinations
                condition_on_previous_text=True,  # Use context from previous segments
            )

            # Yield each segment as it's ready
            for segment in segments:
                elapsed = time.time() - start
                text = segment.text.strip()

                # Translate if needed (Japanese -> French/other)
                if actual_task == 'transcribe' and target_language != 'ja' and text:
                    text = self._translate_text(text, source_lang='ja', target_lang=target_language)

                # Filter out hallucinations
                if text and len(text) >= 2 and not is_hallucination(text):
                    metadata = {
                        'engine': 'faster_whisper',
                        'model': self.model_name,
                        'task': task,
                        'language': language,
                        'target_language': target_language,
                        'elapsed_sec': elapsed,
                        'segment_start': segment.start,
                        'segment_end': segment.end,
                        'detected_language': info.language if info else None,
                    }

                    logger.debug(f"faster-whisper stream: '{text}' ({elapsed:.2f}s)")
                    yield text, metadata

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
