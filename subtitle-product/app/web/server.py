"""
Web server for subtitle display
Flask + Flask-SocketIO for real-time subtitle streaming
"""
import logging
import os
from datetime import datetime
from typing import Dict, Any, List

from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO

logger = logging.getLogger(__name__)


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
        self.max_history = 20

        # Pause state
        self.paused = False

        # Hallucination filter - common Whisper hallucinations on silence/noise
        self.hallucination_phrases = [
            'thank you for watching',
            'thank you for your viewing',
            'thanks for watching',
            'thank you very much',
            'please subscribe',
            'like and subscribe',
            'see you next time',
            'bye bye',
            'goodbye',
            'the end',
            'to be continued',
        ]

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
            """Safely shutdown the Jetson"""
            import subprocess
            logger.info("Shutdown requested from web interface")
            # Run shutdown in background so we can return response
            subprocess.Popen(['sudo', 'shutdown', '-h', 'now'])
            return jsonify({'status': 'shutting down'})

        @self.app.route('/reboot', methods=['POST'])
        def reboot():
            """Safely reboot the Jetson"""
            import subprocess
            logger.info("Reboot requested from web interface")
            subprocess.Popen(['sudo', 'reboot'])
            return jsonify({'status': 'rebooting'})

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
        """Check if text is a common Whisper hallucination"""
        text_lower = text.lower().strip()
        for phrase in self.hallucination_phrases:
            if phrase in text_lower:
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

        subtitle = {
            'text': text.strip(),
            'source': source_text.strip() if source_text else '',
            'latency': round(latency_sec, 2),
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {},
        }

        # Update stats
        self.stats['subtitles_sent'] += 1
        self.stats['last_subtitle_time'] = subtitle['timestamp']

        # Track latency
        if latency_sec > 0:
            self.latencies.append(latency_sec * 1000)  # ms
            if len(self.latencies) > 50:
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
