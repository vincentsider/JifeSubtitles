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
    CHUNK_DURATION_SEC = 3.0  # Seconds of audio per chunk
    SILENCE_THRESHOLD = 0.01  # RMS threshold for silence detection

    # VAD settings
    VAD_AGGRESSIVENESS = 2  # 0-3, higher = more aggressive filtering
    MIN_SPEECH_DURATION_MS = 250  # Minimum speech segment
    MIN_SILENCE_DURATION_MS = 500  # Silence needed to end utterance
    PRE_ROLL_MS = 200  # Audio to keep before speech detection

    # Whisper settings
    WHISPER_MODEL = os.environ.get('WHISPER_MODEL', 'small')
    WHISPER_BACKEND = os.environ.get('WHISPER_BACKEND', 'whisper_trt')  # whisper_trt or whisper
    WHISPER_TASK = 'translate'  # 'translate' for JP->EN, 'transcribe' for JP->JP
    WHISPER_LANGUAGE = 'ja'
    WHISPER_BEAM_SIZE = 5

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
    MAX_QUEUE_SIZE = 20  # Max audio chunks in queue
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
