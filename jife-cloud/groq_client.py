"""
JIFE Cloud - Groq Whisper API Client
Handles audio translation via Groq's Whisper API
"""
import io
import time
import wave
import logging
from typing import Tuple, Dict, Any, Optional

import requests
import numpy as np

from config import get_config

logger = logging.getLogger(__name__)
config = get_config()


class GroqWhisperClient:
    """
    Client for Groq's Whisper API.
    Translates Japanese audio to English text.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.GROQ_API_KEY
        if not self.api_key:
            raise ValueError(
                "GROQ_API_KEY not set. Get one at https://console.groq.com/keys"
            )

        self.api_url = config.GROQ_API_URL
        self.model = config.GROQ_MODEL
        self.timeout = config.REQUEST_TIMEOUT_SEC

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 60.0 / config.MAX_REQUESTS_PER_MINUTE

        # Stats
        self.total_requests = 0
        self.total_audio_seconds = 0
        self.total_errors = 0

    def _audio_to_wav_bytes(self, audio: np.ndarray, sample_rate: int = 16000) -> bytes:
        """
        Convert numpy audio array to WAV file bytes.

        Args:
            audio: Audio data as float32 numpy array (-1.0 to 1.0)
            sample_rate: Sample rate in Hz

        Returns:
            WAV file as bytes
        """
        # Convert float32 to int16
        audio_int16 = (audio * 32767).astype(np.int16)

        # Write to WAV in memory
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav:
            wav.setnchannels(1)  # Mono
            wav.setsampwidth(2)  # 16-bit
            wav.setframerate(sample_rate)
            wav.writeframes(audio_int16.tobytes())

        return buffer.getvalue()

    def _rate_limit(self):
        """Enforce rate limiting between API calls"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)

    def translate(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Translate Japanese audio to English text using Groq API.

        Args:
            audio: Audio data as float32 numpy array (-1.0 to 1.0)
            sample_rate: Sample rate in Hz (should be 16000)

        Returns:
            Tuple of (translated_text, metadata_dict)
        """
        start_time = time.time()
        audio_duration = len(audio) / sample_rate

        # Rate limit
        self._rate_limit()

        # Convert audio to WAV bytes
        wav_bytes = self._audio_to_wav_bytes(audio, sample_rate)

        # Prepare request
        headers = {
            'Authorization': f'Bearer {self.api_key}',
        }

        files = {
            'file': ('audio.wav', wav_bytes, 'audio/wav'),
        }

        data = {
            'model': self.model,
            # 'language': 'ja',  # Source language (optional, auto-detected)
            # 'response_format': 'json',  # Default
        }

        # Make request
        try:
            logger.debug(f"Sending {audio_duration:.1f}s audio to Groq API...")

            response = requests.post(
                self.api_url,
                headers=headers,
                files=files,
                data=data,
                timeout=self.timeout,
            )

            self.last_request_time = time.time()
            elapsed = time.time() - start_time

            # Update stats
            self.total_requests += 1
            self.total_audio_seconds += audio_duration

            if response.status_code == 200:
                result = response.json()
                text = result.get('text', '').strip()

                metadata = {
                    'engine': 'groq',
                    'model': self.model,
                    'audio_duration_sec': audio_duration,
                    'elapsed_sec': elapsed,
                    'rtf': elapsed / audio_duration if audio_duration > 0 else 0,
                }

                logger.debug(f"Groq API: '{text[:50]}...' ({elapsed:.2f}s)")
                return text, metadata

            else:
                self.total_errors += 1
                error_msg = f"API error {response.status_code}: {response.text}"
                logger.error(error_msg)
                return '', {'error': error_msg}

        except requests.Timeout:
            self.total_errors += 1
            logger.error(f"API timeout after {self.timeout}s")
            return '', {'error': 'timeout'}

        except requests.RequestException as e:
            self.total_errors += 1
            logger.error(f"API request failed: {e}")
            return '', {'error': str(e)}

        except Exception as e:
            self.total_errors += 1
            logger.error(f"Unexpected error: {e}")
            return '', {'error': str(e)}

    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            'total_requests': self.total_requests,
            'total_audio_seconds': self.total_audio_seconds,
            'total_audio_hours': self.total_audio_seconds / 3600,
            'total_errors': self.total_errors,
            'estimated_cost_usd': self.total_audio_seconds / 3600 * 0.111,
        }


def test_client():
    """Test the Groq client with a sample audio file"""
    import sys

    logging.basicConfig(level=logging.DEBUG)

    if len(sys.argv) < 2:
        print("Usage: python groq_client.py <audio_file.wav>")
        sys.exit(1)

    # Load audio file
    import scipy.io.wavfile as wav
    sample_rate, audio = wav.read(sys.argv[1])

    # Convert to float32
    if audio.dtype == np.int16:
        audio = audio.astype(np.float32) / 32767.0

    # Create client and translate
    client = GroqWhisperClient()
    text, metadata = client.translate(audio, sample_rate)

    print(f"\nTranslation: {text}")
    print(f"Metadata: {metadata}")
    print(f"Stats: {client.get_stats()}")


if __name__ == '__main__':
    test_client()
