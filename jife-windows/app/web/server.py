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
    {
        'id': 'large-v3:float16:5',
        'model': 'large-v3',
        'name': 'Large-v3 FP16 (Best Quality)',
        'description': 'Highest accuracy, best for Japanese→English translation. Uses float16 for optimal GPU performance.',
        'compute_type': 'float16',
        'beam_size': 5,
    },
    {
        'id': 'large-v3:int8_float16:5',
        'model': 'large-v3',
        'name': 'Large-v3 INT8 (Faster)',
        'description': 'Best accuracy with 50% less VRAM, slightly faster than FP16',
        'compute_type': 'int8_float16',
        'beam_size': 5,
    },
    {
        'id': 'medium:float16:5',
        'model': 'medium',
        'name': 'Medium FP16 (Balanced)',
        'description': 'Good balance of speed and accuracy, faster than large-v3',
        'compute_type': 'float16',
        'beam_size': 5,
    },
    {
        'id': 'small:float16:5',
        'model': 'small',
        'name': 'Small FP16 (Fast)',
        'description': 'Fastest option with acceptable quality for real-time use',
        'compute_type': 'float16',
        'beam_size': 5,
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

        # Model switching support
        self.current_model: str = ''
        self.model_switching: bool = False
        self.model_switch_callback: Optional[Callable] = None

        # Language support
        self.current_target_language: str = 'en'  # Default to English

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
                        # Pass model name (not id), compute_type, and beam_size
                        success = self.model_switch_callback(
                            model_config['model'],
                            model_config['compute_type'],
                            model_config.get('beam_size', 5)
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

        @self.app.route('/language/switch', methods=['POST'])
        def switch_language():
            """Switch target language"""
            data = request.get_json() or {}
            language = data.get('language')

            if not language:
                return jsonify({'success': False, 'message': 'No language specified'}), 400

            # Validate language code
            valid_languages = ['en', 'fr', 'es', 'de', 'pt', 'it', 'ru', 'zh', 'ja', 'ko']
            if language not in valid_languages:
                return jsonify({'success': False, 'message': f'Unsupported language: {language}'}), 400

            # Update target language in config
            try:
                from app.config import get_config
                config = get_config()
                config.WHISPER_TARGET_LANGUAGE = language
                self.current_target_language = language

                logger.info(f"Target language switched to: {language}")
                return jsonify({'success': True, 'language': language})

            except Exception as e:
                logger.error(f"Language switch error: {e}")
                return jsonify({'success': False, 'message': str(e)}), 500

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

        # Hallucination filtering is now done in whisper_engine.py

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
