"""
JIFE Cloud - Web Server
Flask + SocketIO for real-time subtitle display
"""
import logging
import os
from datetime import datetime
from typing import Dict, Any, List

from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO

from config import get_config

logger = logging.getLogger(__name__)
config = get_config()


class SubtitleServer:
    """Web server for real-time subtitle display"""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        groq_client=None,
    ):
        self.host = host or config.WEB_HOST
        self.port = port or config.WEB_PORT
        self.groq_client = groq_client

        # Create Flask app
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        self.app = Flask(__name__, template_folder=template_dir)
        self.app.config['SECRET_KEY'] = config.SECRET_KEY

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
            'avg_latency_ms': 0,
        }
        self.latencies: List[float] = []

        # Subtitle history
        self.subtitle_history: List[Dict[str, Any]] = []
        self.max_history = 10

        # Speaker tracking
        self.current_speaker = 0
        self.last_subtitle_time = None
        self.speaker_colors = ['#ffffff', '#00ffff', '#ffff00', '#ff88ff']

        # Hallucination filter
        self.hallucination_phrases = [
            'thank you for watching',
            'thanks for watching',
            'please subscribe',
            'like and subscribe',
            'see you next time',
            'bye bye',
            'goodbye',
            'the end',
            'subtitles by',
        ]

        # Register routes
        self._register_routes()
        self._register_socket_events()

    def _register_routes(self):
        """Register HTTP routes"""

        @self.app.route('/')
        def index():
            return render_template('index.html')

        @self.app.route('/health')
        def health():
            stats = {}
            if self.groq_client:
                stats = self.groq_client.get_stats()
            return jsonify({
                'status': 'ok',
                'uptime_seconds': (
                    datetime.now() - datetime.fromisoformat(self.stats['start_time'])
                ).total_seconds(),
                'stats': self.stats,
                'groq_stats': stats,
            })

        @self.app.route('/stats')
        def stats():
            result = dict(self.stats)
            if self.groq_client:
                result['groq'] = self.groq_client.get_stats()
            return jsonify(result)

    def _register_socket_events(self):
        """Register WebSocket events"""

        @self.socketio.on('connect')
        def on_connect():
            self.stats['clients_connected'] += 1
            logger.info(f"Client connected. Total: {self.stats['clients_connected']}")
            if self.subtitle_history:
                self.socketio.emit('history', self.subtitle_history)

        @self.socketio.on('disconnect')
        def on_disconnect():
            self.stats['clients_connected'] = max(0, self.stats['clients_connected'] - 1)
            logger.info(f"Client disconnected. Total: {self.stats['clients_connected']}")

    def _is_hallucination(self, text: str) -> bool:
        """Check if text is a common hallucination"""
        text_lower = text.lower().strip()
        for phrase in self.hallucination_phrases:
            if phrase in text_lower:
                return True
        return False

    def send_subtitle(
        self,
        text: str,
        latency_sec: float = 0,
        metadata: Dict[str, Any] = None,
    ):
        """Send a subtitle to all connected clients"""
        if not text or not text.strip():
            return

        if self._is_hallucination(text):
            logger.debug(f"Filtered hallucination: {text}")
            return

        # Speaker detection
        now = datetime.now()
        if self.last_subtitle_time:
            gap = (now - self.last_subtitle_time).total_seconds()
            if gap > 2.0:
                self.current_speaker = (self.current_speaker + 1) % len(self.speaker_colors)
        self.last_subtitle_time = now

        subtitle = {
            'text': text.strip(),
            'source': '',  # Cloud version doesn't have source text
            'latency': round(latency_sec, 2),
            'timestamp': now.isoformat(),
            'metadata': metadata or {},
            'speaker': self.current_speaker,
            'color': self.speaker_colors[self.current_speaker],
        }

        # Update stats
        self.stats['subtitles_sent'] += 1

        if latency_sec > 0:
            self.latencies.append(latency_sec * 1000)
            if len(self.latencies) > 20:
                self.latencies.pop(0)
            self.stats['avg_latency_ms'] = round(
                sum(self.latencies) / len(self.latencies), 1
            )

        # Add to history
        self.subtitle_history.append(subtitle)
        if len(self.subtitle_history) > self.max_history:
            self.subtitle_history.pop(0)

        # Emit to clients
        self.socketio.emit('subtitle', subtitle)
        logger.debug(f"Sent: {text[:50]}...")

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
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        logger.info(f"Web server started on http://{self.host}:{self.port}")
        return thread


def create_server(groq_client=None) -> SubtitleServer:
    """Factory function"""
    return SubtitleServer(groq_client=groq_client)
