"""
Monitor subtitle system for 2 minutes, capture audio, and compare with reference transcription.
This helps identify quality issues and optimize the system.
"""
import re
import time
import wave
import json
import numpy as np
from datetime import datetime
from pathlib import Path

# Configuration
MONITOR_DURATION = 120  # 2 minutes
AUDIO_OUTPUT_FILE = "captured_audio.wav"
LOGS_OUTPUT_FILE = "system_logs.txt"
RESULTS_FILE = "comparison_results.json"

def monitor_system():
    """Monitor Docker logs and extract subtitles + metrics"""
    import subprocess

    print(f"=== MONITORING SYSTEM FOR {MONITOR_DURATION} SECONDS ===\n")

    # Start timestamp
    start_time = time.time()
    end_time = start_time + MONITOR_DURATION

    subtitles = []
    gpu_metrics = []

    print("Starting monitoring... (Press Ctrl+C to stop early)\n")

    try:
        while time.time() < end_time:
            remaining = int(end_time - time.time())
            print(f"\rMonitoring... {remaining}s remaining", end="", flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped early by user")

    print("\n\n=== COLLECTING LOGS ===")

    # Collect all logs from monitoring period
    result = subprocess.run(
        ["wsl", "bash", "-c", f"docker logs subtitle-server 2>&1 | tail -500"],
        capture_output=True,
        text=True,
        timeout=30
    )

    logs = result.stdout

    # Save raw logs
    with open(LOGS_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(logs)

    print(f"Logs saved to {LOGS_OUTPUT_FILE}")

    # Extract subtitles
    for line in logs.split('\n'):
        # Match: [0.42s] Subtitle text here
        match = re.search(r'\[(\d+\.\d+)s\] (.+)$', line)
        if match and 'subtitle-system:' in line:
            latency = float(match.group(1))
            text = match.group(2).strip()
            subtitles.append({
                'latency': latency,
                'text': text,
                'timestamp': time.time()
            })

    # Extract GPU metrics (if available)
    gpu_lines = [l for l in logs.split('\n') if 'GPU' in l or 'VRAM' in l or 'CUDA' in l]

    # Calculate statistics
    if subtitles:
        latencies = [s['latency'] for s in subtitles]
        stats = {
            'total_subtitles': len(subtitles),
            'latency_min': min(latencies),
            'latency_max': max(latencies),
            'latency_avg': sum(latencies) / len(latencies),
            'latency_median': sorted(latencies)[len(latencies) // 2],
            'subtitles_per_minute': len(subtitles) / (MONITOR_DURATION / 60),
        }

        # Distribution
        fast = sum(1 for l in latencies if l < 0.5)
        normal = sum(1 for l in latencies if 0.5 <= l < 1.0)
        slow = sum(1 for l in latencies if l >= 1.0)

        stats['distribution'] = {
            'fast_(<0.5s)': f"{fast} ({fast/len(latencies)*100:.1f}%)",
            'normal_(0.5-1s)': f"{normal} ({normal/len(latencies)*100:.1f}%)",
            'slow_(>1s)': f"{slow} ({slow/len(latencies)*100:.1f}%)"
        }

        print("\n=== PERFORMANCE STATISTICS ===")
        print(f"Total subtitles: {stats['total_subtitles']}")
        print(f"Subtitles/min: {stats['subtitles_per_minute']:.1f}")
        print(f"\nLatency:")
        print(f"  Min: {stats['latency_min']:.2f}s")
        print(f"  Avg: {stats['latency_avg']:.2f}s")
        print(f"  Max: {stats['latency_max']:.2f}s")
        print(f"  Median: {stats['latency_median']:.2f}s")
        print(f"\nDistribution:")
        print(f"  Fast (<0.5s): {stats['distribution']['fast_(<0.5s)']}")
        print(f"  Normal (0.5-1s): {stats['distribution']['normal_(0.5-1s)']}")
        print(f"  Slow (>1s): {stats['distribution']['slow_(>1s)']}")

        return stats, subtitles, logs
    else:
        print("\n⚠️  WARNING: No subtitles captured during monitoring period!")
        return None, [], logs


def capture_audio_sample():
    """Capture a 2-minute audio sample from the system"""
    import subprocess

    print(f"\n=== CAPTURING AUDIO SAMPLE ({MONITOR_DURATION}s) ===")
    print("This will record audio from VB-Cable for reference transcription...\n")

    try:
        # Record audio using WSL arecord (same as subtitle system uses)
        # Get audio device from docker-compose environment
        result = subprocess.run(
            ["wsl", "bash", "-c", f"cd /mnt/c/Projects/priority/JifeSubtitles/jife-windows && docker compose exec -T subtitle-server python3 -c \"from app.config import get_config; print(get_config().AUDIO_DEVICE)\""],
            capture_output=True,
            text=True,
            timeout=10
        )
        audio_device = result.stdout.strip() or "plughw:2,0"

        print(f"Recording from device: {audio_device}")
        print(f"Duration: {MONITOR_DURATION} seconds")
        print("Recording...")

        # Record audio
        subprocess.run(
            ["wsl", "bash", "-c", f"arecord -D {audio_device} -f S16_LE -r 16000 -c 1 -d {MONITOR_DURATION} /tmp/captured_audio.wav"],
            timeout=MONITOR_DURATION + 10
        )

        # Copy to Windows
        subprocess.run(
            ["wsl", "bash", "-c", f"cp /tmp/captured_audio.wav /mnt/c/Projects/priority/JifeSubtitles/{AUDIO_OUTPUT_FILE}"],
            timeout=5
        )

        print(f"✓ Audio saved to {AUDIO_OUTPUT_FILE}")
        return True

    except Exception as e:
        print(f"✗ Audio capture failed: {e}")
        return False


def transcribe_with_openai_whisper(audio_file: str):
    """
    Transcribe audio using OpenAI Whisper API (reference transcription).
    Requires OPENAI_API_KEY environment variable.
    """
    import os

    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("\n⚠️  OPENAI_API_KEY not set. Skipping reference transcription.")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        return None

    print("\n=== REFERENCE TRANSCRIPTION (OpenAI Whisper API) ===")
    print("Uploading audio to OpenAI for reference transcription...")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        with open(audio_file, 'rb') as f:
            transcript = client.audio.translations.create(
                model="whisper-1",
                file=f,
                language="ja",  # Japanese
                response_format="verbose_json"
            )

        print(f"✓ Reference transcription completed")
        print(f"Duration: {transcript.duration:.1f}s")
        print(f"\nReference text:\n{transcript.text}\n")

        return {
            'text': transcript.text,
            'duration': transcript.duration,
            'segments': transcript.segments if hasattr(transcript, 'segments') else []
        }

    except ImportError:
        print("⚠️  'openai' package not installed. Install with: pip install openai")
        return None
    except Exception as e:
        print(f"✗ Reference transcription failed: {e}")
        return None


def compare_transcriptions(system_subtitles, reference_text):
    """Compare system output with reference transcription"""
    print("\n=== QUALITY COMPARISON ===")

    # Combine system subtitles
    system_text = ' '.join([s['text'] for s in system_subtitles])

    print(f"\nSystem output ({len(system_subtitles)} subtitles):")
    print(f"{system_text}\n")

    if reference_text:
        print(f"Reference (OpenAI Whisper):")
        print(f"{reference_text}\n")

        # Simple word-level comparison
        system_words = system_text.lower().split()
        reference_words = reference_text.lower().split()

        # Calculate rough similarity
        common_words = set(system_words) & set(reference_words)
        similarity = len(common_words) / max(len(set(system_words)), len(set(reference_words))) if reference_words else 0

        print(f"\nWord overlap: {len(common_words)} common words")
        print(f"Rough similarity: {similarity*100:.1f}%")

        # Check for hallucinations (words in system but not in reference)
        system_only = set(system_words) - set(reference_words)
        if system_only:
            print(f"\nPotential hallucinations (in system but not reference):")
            print(f"  {', '.join(sorted(system_only)[:20])}")

        # Check for missing words (words in reference but not in system)
        missing = set(reference_words) - set(system_words)
        if missing:
            print(f"\nMissing words (in reference but not in system):")
            print(f"  {', '.join(sorted(missing)[:20])}")

    return {
        'system_text': system_text,
        'reference_text': reference_text,
        'system_word_count': len(system_text.split()),
        'reference_word_count': len(reference_text.split()) if reference_text else 0
    }


def main():
    print("=" * 70)
    print("  SUBTITLE SYSTEM MONITORING & QUALITY COMPARISON")
    print("=" * 70)
    print()
    print("This script will:")
    print("1. Monitor the subtitle system for 2 minutes")
    print("2. Capture the raw audio stream")
    print("3. Transcribe with OpenAI Whisper API (reference)")
    print("4. Compare system output vs reference")
    print("5. Identify quality issues and optimization opportunities")
    print()
    input("Press ENTER to start monitoring...")

    # Step 1: Monitor system
    stats, subtitles, logs = monitor_system()

    # Step 2: Capture audio (optional - if user wants reference comparison)
    print("\n" + "=" * 70)
    response = input("\nCapture audio for reference transcription? (y/n): ").lower()

    reference_data = None
    if response == 'y':
        if capture_audio_sample():
            # Step 3: Reference transcription
            reference_data = transcribe_with_openai_whisper(AUDIO_OUTPUT_FILE)

    # Step 4: Comparison
    if subtitles and reference_data:
        comparison = compare_transcriptions(subtitles, reference_data['text'])
    else:
        comparison = None

    # Step 5: Save results
    results = {
        'timestamp': datetime.now().isoformat(),
        'monitoring_duration': MONITOR_DURATION,
        'performance': stats,
        'subtitles': subtitles,
        'reference': reference_data,
        'comparison': comparison
    }

    with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Results saved to {RESULTS_FILE}")
    print("\n" + "=" * 70)
    print("  MONITORING COMPLETE")
    print("=" * 70)


if __name__ == '__main__':
    main()
