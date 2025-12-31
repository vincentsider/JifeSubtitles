"""
Configuration for Japanese -> English Real-Time Subtitle System
"""
import os


class Config:
    """Application configuration - can be overridden by environment variables"""

    # Audio settings
    AUDIO_DEVICE = os.environ.get('AUDIO_DEVICE', 'plughw:2,0')
    SAMPLE_RATE = 16000  # Whisper expects 16kHz
    CHANNELS = 1  # Mono

    # Processing mode: 'fixed' or 'vad'
    PROCESSING_MODE = os.environ.get('PROCESSING_MODE', 'fixed')  # 'fixed' = Option A, 'vad' = Option B

    # Fixed chunk mode settings (Option A - fast, simple)
    CHUNK_DURATION_SEC = 3.5  # Increased to 3.5s - more context for better translation quality
    CHUNK_OVERLAP_SEC = 0.0  # NO OVERLAP - prevents repetition with short chunks
    SILENCE_THRESHOLD = 0.02  # RMS threshold for silence detection (raised from 0.01)

    # VAD-based mode settings (Option B - better quality, higher latency)
    VAD_ENABLED = (PROCESSING_MODE == 'vad')
    VAD_AGGRESSIVENESS = 2  # 0-3, higher = more aggressive filtering
    MIN_SPEECH_DURATION_MS = 250  # Minimum speech segment
    MIN_SILENCE_DURATION_MS = 500  # Silence needed to end utterance
    PRE_ROLL_MS = 200  # Audio to keep before speech detection
    VAD_MIN_CHUNK_SIZE = 1.0  # Minimum seconds before processing (VAD mode)
    VAD_MAX_CHUNK_SIZE = 10.0  # Maximum chunk size (VAD mode)

    # Whisper settings
    WHISPER_MODEL = os.environ.get('WHISPER_MODEL', 'large-v3')
    WHISPER_BACKEND = os.environ.get('WHISPER_BACKEND', 'faster_whisper')  # faster_whisper for Windows
    WHISPER_COMPUTE_TYPE = os.environ.get('WHISPER_COMPUTE_TYPE', 'float16')  # FP16 for best quality
    WHISPER_TASK = 'translate'  # 'translate' for JP->target, 'transcribe' for JP->JP
    WHISPER_LANGUAGE = 'ja'  # Source language (Japanese)
    WHISPER_TARGET_LANGUAGE = os.environ.get('WHISPER_TARGET_LANGUAGE', 'en')  # Target: en, fr, es, de, etc.
    WHISPER_BEAM_SIZE = int(os.environ.get('WHISPER_BEAM_SIZE', 5))  # 5 for large-v3 (better quality)
    WHISPER_TEMPERATURE = 0.0  # Deterministic output (no randomness)

    # Translation (if using separate translation model)
    USE_SEPARATE_TRANSLATION = False  # Set to True to use NLLB/other
    TRANSLATION_MODEL = 'facebook/nllb-200-distilled-600M'

    # Web server
    WEB_HOST = '0.0.0.0'
    WEB_PORT = int(os.environ.get('WEB_PORT', 5000))
    SECRET_KEY = os.environ.get('SECRET_KEY', 'subtitle-dev-key-change-in-prod')

    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'

    # Performance
    MAX_QUEUE_SIZE = 5  # Max audio chunks in queue (aggressive discard keeps it at ~1)
    SUBTITLE_HISTORY_SIZE = 50  # Max subtitles to keep in browser


class ProductionConfig(Config):
    """Production overrides"""
    LOG_LEVEL = 'WARNING'
    SECRET_KEY = os.environ.get('SECRET_KEY')  # Must be set in production


class DevelopmentConfig(Config):
    """Development overrides"""
    LOG_LEVEL = 'DEBUG'


def get_config():
    """Get configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'development')
    if env == 'production':
        return ProductionConfig()
    return DevelopmentConfig()
