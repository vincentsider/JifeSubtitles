"""
JIFE Cloud - Configuration
Raspberry Pi + Groq API version
"""
import os


class Config:
    """Configuration for JIFE Cloud"""

    # Groq API
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
    GROQ_MODEL = 'whisper-large-v3'
    GROQ_API_URL = 'https://api.groq.com/openai/v1/audio/translations'

    # Audio settings
    AUDIO_DEVICE = os.environ.get('AUDIO_DEVICE', 'plughw:1,0')
    SAMPLE_RATE = 16000  # Whisper expects 16kHz
    CHANNELS = 1  # Mono

    # Chunking settings
    # Groq API processes audio files, so we need to chunk
    CHUNK_DURATION_SEC = float(os.environ.get('CHUNK_DURATION', '5'))
    OVERLAP_DURATION_SEC = float(os.environ.get('OVERLAP_DURATION', '2'))

    # Silence detection
    SILENCE_THRESHOLD = 0.02  # RMS below this is considered silence
    MIN_SPEECH_DURATION_SEC = 0.5  # Minimum speech to send to API

    # Web server
    WEB_HOST = '0.0.0.0'
    WEB_PORT = int(os.environ.get('WEB_PORT', 5000))
    SECRET_KEY = os.environ.get('SECRET_KEY', 'jife-cloud-dev-key')

    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'

    # Rate limiting
    MAX_REQUESTS_PER_MINUTE = 30  # Groq limit
    REQUEST_TIMEOUT_SEC = 30


def get_config():
    """Get configuration instance"""
    return Config()
