"""
Web server for subtitle display
Flask + Flask-SocketIO for real-time subtitle streaming
"""
import logging
import os
import threading
from datetime import datetime
from typing import Dict, Any, List, Callable, Optional

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO

logger = logging.getLogger(__name__)

# Available models for the frontend selector
# Optimized for Windows PC with NVIDIA GPU (RTX 20xx/30xx/40xx)
# 'id' format: model_name:compute_type:beam_size for unique identification
#
# NOTE: large-v3-turbo is NOT included because it does NOT support translation.
# Turbo was fine-tuned only on transcription data, not translation data.
# See: https://github.com/SYSTRAN/faster-whisper/issues/1237
AVAILABLE_MODELS = [
    # Option A: Whisper with direct translation (baseline)
    {
        'id': 'large-v3:float16:5',
        'model': 'large-v3',
        'name': 'Whisper Large-v3 (Option A)',
        'description': 'Whisper direct translation. Fast, good quality.',
        'compute_type': 'float16',
        'beam_size': 5,
        'backend': 'faster_whisper',
    },
    # Option B: SeamlessM4T speech-to-text translation
    {
        'id': 'seamless:float16:5',
        'model': 'seamless-m4t-v2-large',
        'name': 'SeamlessM4T v2 (Option B)',
        'description': 'Meta speech translation model. Better for messy audio.',
        'compute_type': 'float16',
        'beam_size': 5,
        'backend': 'seamless_m4t',
    },
    # Option C: Pipeline (Whisper transcribe + SeamlessM4T translate)
    {
        'id': 'pipeline:float16:5',
        'model': 'large-v3',
        'name': 'Whisper + SeamlessM4T (Option C)',
        'description': 'Two-stage: Whisper transcribes JP, SeamlessM4T translates. Highest quality, higher latency.',
        'compute_type': 'float16',
        'beam_size': 5,
        'backend': 'pipeline',
    },
    # Option D: Pipeline (Whisper transcribe + MADLAD-400 translate)
    {
        'id': 'madlad:float16:5',
        'model': 'large-v3',
        'name': 'Whisper + MADLAD-400 (Option D)',
        'description': 'Whisper transcribes JP, MADLAD-400-3B translates. Best quality/latency balance.',
        'compute_type': 'float16',
        'beam_size': 5,
        'backend': 'madlad',
    },
    # Option E: Enhanced Whisper (Audio Preprocessing + Whisper)
    {
        'id': 'enhanced:float16:5',
        'model': 'large-v3',
        'name': 'Enhanced Whisper (Option E)',
        'description': 'Audio preprocessing (normalization + noise reduction) + Whisper. Best for noisy/music content.',
        'compute_type': 'float16',
        'beam_size': 5,
        'backend': 'enhanced',
    },
    # Faster options
    {
        'id': 'medium:float16:5',
        'model': 'medium',
        'name': 'Whisper Medium (Faster)',
        'description': 'Faster than large-v3, still good quality',
        'compute_type': 'float16',
        'beam_size': 5,
        'backend': 'faster_whisper',
    },
]


class SubtitleServer:
    """Web server for real-time subtitle display"""

    def __init__(
        self,
        host: str = '0.0.0.0',
        port: int = 5000,
        secret_key: str = 'dev-key',
    ):
        self.host = host
        self.port = port

        # Create Flask app
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        self.app = Flask(__name__, template_folder=template_dir)
        self.app.config['SECRET_KEY'] = secret_key

        # Create SocketIO
        self.socketio = SocketIO(
            self.app,
            cors_allowed_origins="*",
            async_mode='threading',
        )

        # Stats
        self.stats: Dict[str, Any] = {
            'start_time': datetime.now().isoformat(),
            'subtitles_sent': 0,
            'clients_connected': 0,
            'last_subtitle_time': None,
            'avg_latency_ms': 0,
        }
        self.latencies: List[float] = []

        # Subtitle history (for clients joining mid-stream)
        self.subtitle_history: List[Dict[str, Any]] = []
        self.max_history = 10  # Only need last few for new clients

        # Pause state
        self.paused = False

        # Speaker tracking - alternate colors on silence gaps
        self.current_speaker = 0
        self.last_subtitle_time = None
        self.speaker_colors = ['#ffffff', '#00ffff', '#ffff00', '#ff88ff']  # white, cyan, yellow, pink

        # Hallucination filter - common hallucinations on silence/noise
        # Includes patterns from both Whisper and SeamlessM4T
        self.hallucination_phrases = [
            # Common Whisper hallucinations
            'thank you for watching',
            'thank you for your viewing',
            'thanks for watching',
            'thank you very much',
            'please subscribe',
            'like and subscribe',
            'see you next time',
            'see you in the next video',
            'see you in the next',
            'bye bye',
            'goodbye',
            'the end',
            'to be continued',
            'subtitles by',
            'captions by',
            'translated by',
            "i'll come back to you",
            "and i'll come back to you",
            "i'll be back",
            "i will come back",
            # Violent hallucinations on music/noise
            "i'll die",
            "i will die",
            "i'll kill you",
            "i will kill you",
            "kill you",
            "die",
            "i'm going to die",
            "you're going to die",
            "i'm dead",
            "death",
            # Music/singing hallucinations
            "what's that",
            "what is that",
            "wow",
            "what?",
            "i'm going to sleep",
            "i'm going to bed",
            "going to sleep",
            # SeamlessM4T repetitive hallucinations
            "i'm going to be able to",
            "i'm going to be",
            "going to be able to do it",
            "i'm not going to be able",
            "i don't know what to do",
            "i don't know what to say",
            "i don't know",
        ]

        # Short phrases that are almost always hallucinations (exact match only)
        self.short_hallucinations = [
            "die",
            "no",
            "yes",
            "oh",
            "ah",
            "uh",
            "um",
            "hmm",
        ]

        # Model switching support
        self.current_model: str = ''
        self.model_switching: bool = False
        self.model_switch_callback: Optional[Callable] = None

        # Register routes and events
        self._register_routes()
        self._register_socket_events()

    def _register_routes(self):
        """Register HTTP routes"""

        @self.app.route('/')
        def index():
            return render_template('index.html')

        @self.app.route('/health')
        def health():
            return jsonify({
                'status': 'ok',
                'uptime_seconds': (
                    datetime.now() - datetime.fromisoformat(self.stats['start_time'])
                ).total_seconds(),
                'stats': self.stats,
            })

        @self.app.route('/stats')
        def stats():
            return jsonify(self.stats)

        @self.app.route('/history')
        def history():
            return jsonify(self.subtitle_history)

        @self.app.route('/pause', methods=['POST'])
        def pause():
            self.paused = True
            logger.info("Subtitles paused")
            return jsonify({'paused': True})

        @self.app.route('/resume', methods=['POST'])
        def resume():
            self.paused = False
            logger.info("Subtitles resumed")
            return jsonify({'paused': False})

        @self.app.route('/toggle_pause', methods=['POST'])
        def toggle_pause():
            self.paused = not self.paused
            logger.info(f"Subtitles {'paused' if self.paused else 'resumed'}")
            return jsonify({'paused': self.paused})

        @self.app.route('/status')
        def status():
            return jsonify({'paused': self.paused})

        @self.app.route('/shutdown', methods=['POST'])
        def shutdown():
            """Safely shutdown the Jetson via FIFO to host"""
            logger.info("Shutdown requested from web interface")
            try:
                with open('/tmp/jife-power-control', 'w') as f:
                    f.write('shutdown\n')
                return jsonify({'status': 'shutting down'})
            except Exception as e:
                logger.error(f"Shutdown failed: {e}")
                return jsonify({'status': 'error', 'message': str(e)}), 500

        @self.app.route('/reboot', methods=['POST'])
        def reboot():
            """Safely reboot the Jetson via FIFO to host"""
            logger.info("Reboot requested from web interface")
            try:
                with open('/tmp/jife-power-control', 'w') as f:
                    f.write('reboot\n')
                return jsonify({'status': 'rebooting'})
            except Exception as e:
                logger.error(f"Reboot failed: {e}")
                return jsonify({'status': 'error', 'message': str(e)}), 500

        @self.app.route('/models')
        def get_models():
            """Get available models and current model"""
            return jsonify({
                'models': AVAILABLE_MODELS,
                'current': self.current_model,
                'switching': self.model_switching,
            })

        @self.app.route('/models/switch', methods=['POST'])
        def switch_model():
            """Switch to a different model"""
            data = request.get_json() or {}
            model_id = data.get('model')

            if not model_id:
                return jsonify({'error': 'No model specified'}), 400

            # Find model config
            model_config = None
            for m in AVAILABLE_MODELS:
                if m['id'] == model_id:
                    model_config = m
                    break

            if not model_config:
                return jsonify({'error': f'Unknown model: {model_id}'}), 400

            if self.model_switching:
                return jsonify({'error': 'Model switch already in progress'}), 409

            if model_id == self.current_model:
                return jsonify({'status': 'already_loaded', 'model': model_id})

            # Trigger model switch via callback
            if self.model_switch_callback:
                self.model_switching = True
                # Notify clients that model is switching
                self.socketio.emit('model_switching', {'model': model_id, 'name': model_config['name']})

                # Start switch in background thread
                def do_switch():
                    try:
                        # Pass model name (not id), compute_type, beam_size, and backend
                        success = self.model_switch_callback(
                            model_config['model'],
                            model_config['compute_type'],
                            model_config.get('beam_size', 5),
                            model_config.get('backend', 'faster_whisper')
                        )
                        if success:
                            self.current_model = model_id
                            self.socketio.emit('model_switched', {'model': model_id, 'name': model_config['name']})
                            logger.info(f"Model switched to: {model_id}")
                        else:
                            self.socketio.emit('model_switch_failed', {'model': model_id, 'error': 'Switch failed'})
                            logger.error(f"Model switch failed: {model_id}")
                    except Exception as e:
                        self.socketio.emit('model_switch_failed', {'model': model_id, 'error': str(e)})
                        logger.error(f"Model switch error: {e}")
                    finally:
                        self.model_switching = False

                threading.Thread(target=do_switch, daemon=True).start()
                return jsonify({'status': 'switching', 'model': model_id})
            else:
                return jsonify({'error': 'Model switching not configured'}), 500

    def set_model_switch_callback(self, callback: Callable[[str, str], bool]):
        """Set callback function for model switching"""
        self.model_switch_callback = callback

    def set_current_model(self, model_id: str):
        """Set the current model ID"""
        self.current_model = model_id

    def _register_socket_events(self):
        """Register WebSocket events"""

        @self.socketio.on('connect')
        def on_connect():
            self.stats['clients_connected'] += 1
            logger.info(f"Client connected. Total: {self.stats['clients_connected']}")

            # Send recent history to new client
            if self.subtitle_history:
                self.socketio.emit('history', self.subtitle_history, room=None)

        @self.socketio.on('disconnect')
        def on_disconnect():
            self.stats['clients_connected'] = max(0, self.stats['clients_connected'] - 1)
            logger.info(f"Client disconnected. Total: {self.stats['clients_connected']}")

    def _is_hallucination(self, text: str) -> bool:
        """Check if text is a common hallucination or repetitive garbage"""
        text_lower = text.lower().strip()

        # Very short text (1-2 words) is almost always hallucination
        words = text_lower.split()
        if len(words) <= 2:
            # Check exact match for short hallucinations
            if text_lower in self.short_hallucinations:
                logger.debug(f"Short hallucination filtered: '{text}'")
                return True
            # Single words under 4 chars are suspicious
            if len(words) == 1 and len(text_lower) < 4:
                logger.debug(f"Very short word filtered: '{text}'")
                return True

        # Check for known hallucination phrases
        for phrase in self.hallucination_phrases:
            if phrase in text_lower:
                logger.debug(f"Hallucination phrase filtered: '{phrase}' in '{text}'")
                return True

        # Check for repetitive patterns - more aggressive detection
        words = text_lower.split()

        # Pattern 1: Any 3+ word phrase that repeats 2+ times is suspicious
        if len(words) >= 6:
            for phrase_len in [3, 4, 5]:  # Check 3, 4, and 5 word phrases
                if len(words) >= phrase_len * 2:
                    for i in range(len(words) - phrase_len + 1):
                        phrase = ' '.join(words[i:i+phrase_len])
                        # Count non-overlapping occurrences
                        count = 0
                        pos = 0
                        temp = text_lower
                        while phrase in temp[pos:]:
                            count += 1
                            pos = temp.find(phrase, pos) + len(phrase)
                        if count >= 2:
                            logger.debug(f"Repetition detected: '{phrase}' x{count}")
                            return True

        # Pattern 2: Same sentence repeated (with punctuation variations)
        import re
        # Remove punctuation for comparison
        clean_text = re.sub(r'[^\w\s]', '', text_lower)
        clean_words = clean_text.split()

        # Check if first half roughly equals second half (repeated sentence)
        if len(clean_words) >= 4:
            mid = len(clean_words) // 2
            first_half = ' '.join(clean_words[:mid])
            second_half = ' '.join(clean_words[mid:mid+len(clean_words[:mid])])
            if first_half == second_half:
                logger.debug(f"Repeated sentence detected: '{first_half}'")
                return True

        # Pattern 3: Very short repeated phrases like "No! No! No!"
        if len(words) >= 3:
            # Check for 1-2 word repetitions
            for word_count in [1, 2]:
                if len(words) >= word_count * 3:
                    first_phrase = ' '.join(words[:word_count])
                    all_same = True
                    for i in range(0, min(len(words), word_count * 4), word_count):
                        if i + word_count <= len(words):
                            if ' '.join(words[i:i+word_count]) != first_phrase:
                                all_same = False
                                break
                    if all_same and len(words) >= word_count * 3:
                        logger.debug(f"Short repetition detected: '{first_phrase}' repeated")
                        return True

        return False

    def send_subtitle(
        self,
        text: str,
        source_text: str = '',
        latency_sec: float = 0,
        metadata: Dict[str, Any] = None,
    ):
        """
        Send a subtitle to all connected clients.

        Args:
            text: The translated/transcribed text (English)
            source_text: Original source text (Japanese)
            latency_sec: Processing latency in seconds
            metadata: Additional metadata
        """
        if not text or not text.strip():
            return

        # Skip if paused
        if self.paused:
            logger.debug(f"Skipping subtitle (paused): {text[:30]}...")
            return

        # Filter out hallucinations
        if self._is_hallucination(text):
            logger.debug(f"Filtered hallucination: {text}")
            return

        # Speaker detection: if gap > 2 seconds, likely new speaker
        now = datetime.now()
        if self.last_subtitle_time:
            gap = (now - self.last_subtitle_time).total_seconds()
            if gap > 2.0:  # 2 second gap suggests speaker change
                self.current_speaker = (self.current_speaker + 1) % len(self.speaker_colors)
        self.last_subtitle_time = now

        subtitle = {
            'text': text.strip(),
            'source': source_text.strip() if source_text else '',
            'latency': round(latency_sec, 2),
            'timestamp': now.isoformat(),
            'metadata': metadata or {},
            'speaker': self.current_speaker,
            'color': self.speaker_colors[self.current_speaker],
        }

        # Update stats
        self.stats['subtitles_sent'] += 1
        self.stats['last_subtitle_time'] = subtitle['timestamp']

        # Track latency
        if latency_sec > 0:
            self.latencies.append(latency_sec * 1000)  # ms
            if len(self.latencies) > 20:  # 20 samples enough for average
                self.latencies.pop(0)
            self.stats['avg_latency_ms'] = round(
                sum(self.latencies) / len(self.latencies), 1
            )

        # Add to history
        self.subtitle_history.append(subtitle)
        if len(self.subtitle_history) > self.max_history:
            self.subtitle_history.pop(0)

        # Emit to all clients
        self.socketio.emit('subtitle', subtitle)
        logger.debug(f"Sent subtitle: {text[:50]}...")

    def run(self, debug: bool = False):
        """Run the web server (blocking)"""
        logger.info(f"Starting web server on http://{self.host}:{self.port}")
        self.socketio.run(
            self.app,
            host=self.host,
            port=self.port,
            debug=debug,
            allow_unsafe_werkzeug=True,
        )

    def run_threaded(self):
        """Run the web server in a background thread"""
        import threading

        thread = threading.Thread(
            target=self.run,
            daemon=True,
            name='WebServer',
        )
        thread.start()
        logger.info(f"Web server started in background on http://{self.host}:{self.port}")
        return thread


def create_server(config=None) -> SubtitleServer:
    """Factory function to create server with configuration"""
    if config is None:
        from ..config import get_config
        config = get_config()

    return SubtitleServer(
        host=config.WEB_HOST,
        port=config.WEB_PORT,
        secret_key=config.SECRET_KEY,
    )
