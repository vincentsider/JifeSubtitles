"""
Capture 2 minutes of audio, save system translations, compare with OpenAI Whisper API.
"""
import subprocess
import time
import re
import json
import os
from datetime import datetime

DURATION = 120  # 2 minutes
AUDIO_FILE = "test_audio.wav"
SYSTEM_OUTPUT_FILE = "system_translations.txt"
COMPARISON_FILE = "quality_comparison.json"

def capture_audio_and_monitor():
    """Capture audio while monitoring system output"""
    print("=" * 70)
    print("  AUDIO QUALITY TEST - 2 MINUTE CAPTURE")
    print("=" * 70)
    print(f"\nCapturing {DURATION} seconds of audio...")
    print("System translations will be saved simultaneously.\n")

    # Use same audio device as subtitle system
    # Get from docker-compose environment or use default
    audio_device = "hw:2,0"  # VB-Cable on Windows
    print(f"Audio device: {audio_device}")

    # Start audio capture in background
    print(f"\nStarting audio recording for {DURATION} seconds...")
    audio_process = subprocess.Popen(
        ["wsl", "bash", "-c",
         f"arecord -D {audio_device} -f S16_LE -r 16000 -c 1 -d {DURATION} /tmp/test_audio.wav 2>/dev/null"],
    )

    # Monitor system output
    print("Monitoring system translations...\n")
    start_time = time.time()

    # Wait for capture to complete
    while time.time() - start_time < DURATION:
        remaining = int(DURATION - (time.time() - start_time))
        print(f"\rCapturing... {remaining}s remaining", end="", flush=True)
        time.sleep(1)

    print("\n\nWaiting for audio capture to finish...")
    audio_process.wait()

    # Copy audio file to Windows
    print("Copying audio file...")
    subprocess.run(
        ["wsl", "bash", "-c", f"cp /tmp/test_audio.wav /mnt/c/Projects/priority/JifeSubtitles/{AUDIO_FILE}"],
        timeout=10
    )

    # Get system logs from the capture period
    print("Extracting system translations...")
    result = subprocess.run(
        ["wsl", "bash", "-c", "docker logs subtitle-server 2>&1 | tail -300"],
        capture_output=True,
        text=True,
        timeout=30
    )

    logs = result.stdout

    # Extract subtitles
    subtitles = []
    for line in logs.split('\n'):
        match = re.search(r'\[(\d+\.\d+)s\] (.+)$', line)
        if match and 'subtitle-system:' in line:
            latency = float(match.group(1))
            text = match.group(2).strip()
            subtitles.append({'latency': latency, 'text': text})

    # Save system output
    with open(SYSTEM_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"System Translations - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Duration: {DURATION} seconds\n")
        f.write(f"Total Subtitles: {len(subtitles)}\n\n")
        for i, s in enumerate(subtitles, 1):
            f.write(f"{i}. [{s['latency']:.2f}s] {s['text']}\n")
        f.write(f"\n--- COMBINED TEXT ---\n")
        f.write(' '.join([s['text'] for s in subtitles]))

    print(f"[OK] Audio saved to: {AUDIO_FILE}")
    print(f"[OK] System translations saved to: {SYSTEM_OUTPUT_FILE}")
    print(f"[OK] Captured {len(subtitles)} subtitles")

    return subtitles


def transcribe_with_openai(audio_file):
    """Transcribe with OpenAI Whisper API (state-of-the-art)"""
    api_key = os.environ.get('OPENAI_API_KEY')

    if not api_key:
        print("\n" + "=" * 70)
        print("  ERROR: OPENAI_API_KEY not set")
        print("=" * 70)
        print("\nTo use OpenAI Whisper API for comparison:")
        print("1. Get API key from: https://platform.openai.com/api-keys")
        print("2. Set environment variable:")
        print("   Windows: set OPENAI_API_KEY=your-key-here")
        print("   PowerShell: $env:OPENAI_API_KEY='your-key-here'")
        print("\nSkipping OpenAI comparison...")
        return None

    print("\n" + "=" * 70)
    print("  TRANSCRIBING WITH OPENAI WHISPER API")
    print("=" * 70)
    print("\nUploading audio to OpenAI...")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        # Use translations endpoint (Japanese -> English)
        with open(audio_file, 'rb') as f:
            print("Processing with Whisper (large-v3)...")
            transcript = client.audio.translations.create(
                model="whisper-1",  # OpenAI's large-v3 model
                file=f,
                response_format="verbose_json"
            )

        print(f"[OK] OpenAI transcription completed")
        print(f"  Duration: {transcript.duration:.1f}s")
        print(f"  Language detected: {transcript.language if hasattr(transcript, 'language') else 'ja'}")

        return {
            'text': transcript.text,
            'duration': transcript.duration,
            'language': transcript.language if hasattr(transcript, 'language') else 'ja'
        }

    except ImportError:
        print("\n[ERROR] 'openai' package not installed")
        print("  Install with: pip install openai")
        return None
    except Exception as e:
        print(f"\n[ERROR] OpenAI API error: {e}")
        return None


def compare_results(system_subtitles, openai_result):
    """Compare system output vs OpenAI reference"""
    print("\n" + "=" * 70)
    print("  QUALITY COMPARISON")
    print("=" * 70)

    # System output
    system_text = ' '.join([s['text'] for s in system_subtitles])
    system_words = system_text.lower().split()

    print(f"\n--- OUR SYSTEM (faster-whisper large-v3) ---")
    print(f"Total subtitles: {len(system_subtitles)}")
    print(f"Total words: {len(system_words)}")
    print(f"Average latency: {sum(s['latency'] for s in system_subtitles)/len(system_subtitles):.2f}s")
    print(f"\nText:\n{system_text}\n")

    if not openai_result:
        print("(No OpenAI comparison - API key not set)")
        return None

    # OpenAI reference
    openai_text = openai_result['text']
    openai_words = openai_text.lower().split()

    print(f"--- OPENAI WHISPER (large-v3, cloud) ---")
    print(f"Total words: {len(openai_words)}")
    print(f"\nText:\n{openai_text}\n")

    # Word-level comparison
    system_word_set = set(system_words)
    openai_word_set = set(openai_words)

    common_words = system_word_set & openai_word_set
    system_only = system_word_set - openai_word_set
    openai_only = openai_word_set - system_word_set

    # Calculate similarity
    union_size = len(system_word_set | openai_word_set)
    jaccard_similarity = len(common_words) / union_size if union_size > 0 else 0

    print("=" * 70)
    print("  ANALYSIS")
    print("=" * 70)
    print(f"\nWord overlap: {len(common_words)} words")
    print(f"Jaccard similarity: {jaccard_similarity*100:.1f}%")

    if system_only:
        print(f"\n--- Words in OUR system but NOT in OpenAI (potential hallucinations) ---")
        print(f"Count: {len(system_only)}")
        print(f"Words: {', '.join(sorted(system_only)[:30])}")

    if openai_only:
        print(f"\n--- Words in OpenAI but NOT in our system (missed content) ---")
        print(f"Count: {len(openai_only)}")
        print(f"Words: {', '.join(sorted(openai_only)[:30])}")

    # Sentence-level comparison
    print(f"\n--- SIDE-BY-SIDE COMPARISON ---")
    print(f"OUR SYSTEM:\n  {system_text[:200]}...")
    print(f"\nOPENAI:\n  {openai_text[:200]}...")

    results = {
        'system': {
            'text': system_text,
            'word_count': len(system_words),
            'subtitle_count': len(system_subtitles),
            'avg_latency': sum(s['latency'] for s in system_subtitles)/len(system_subtitles)
        },
        'openai': {
            'text': openai_text,
            'word_count': len(openai_words),
            'duration': openai_result['duration']
        },
        'comparison': {
            'common_words': len(common_words),
            'system_only_words': len(system_only),
            'openai_only_words': len(openai_only),
            'jaccard_similarity': jaccard_similarity,
            'system_unique': sorted(list(system_only)),
            'openai_unique': sorted(list(openai_only))
        }
    }

    return results


def main():
    print("\nStarting in 3 seconds...")
    print("Make sure your TV audio is playing!")
    time.sleep(3)

    # Step 1: Capture audio + system output
    system_subtitles = capture_audio_and_monitor()

    if not system_subtitles:
        print("\n[ERROR] No subtitles captured! Is the system running?")
        return

    # Step 2: Transcribe with OpenAI
    openai_result = transcribe_with_openai(AUDIO_FILE)

    # Step 3: Compare
    comparison = compare_results(system_subtitles, openai_result)

    # Step 4: Save results
    if comparison:
        with open(COMPARISON_FILE, 'w', encoding='utf-8') as f:
            json.dump(comparison, f, indent=2, ensure_ascii=False)
        print(f"\n[OK] Comparison saved to: {COMPARISON_FILE}")

    print("\n" + "=" * 70)
    print("  TEST COMPLETE")
    print("=" * 70)


if __name__ == '__main__':
    main()
