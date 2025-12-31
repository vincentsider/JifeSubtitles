"""
FINAL QUALITY TEST - Record audio, capture translations, compare with OpenAI
"""
import subprocess
import time
import re
import json
import os
from pathlib import Path

DURATION = 120
AUDIO_FILE = "test_audio.wav"
SYSTEM_OUTPUT_FILE = "system_translations.txt"
COMPARISON_FILE = "quality_comparison.json"

def load_env():
    """Load .env file"""
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

def record_and_monitor():
    """Record audio in Docker container while monitoring translations"""
    print("=" * 70)
    print("  FINAL QUALITY TEST - 2 MINUTE RECORDING")
    print("=" * 70)

    # Start audio recording in container (background)
    print(f"\nStarting {DURATION}s audio recording in Docker container...")
    record_process = subprocess.Popen(
        ["wsl", "bash", "-c",
         f"docker exec subtitle-server python3 /app/app/record_for_test.py {DURATION} /tmp/recorded_audio.wav"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    # Monitor for duration
    print("Monitoring system translations...\n")
    start_time = time.time()

    while time.time() - start_time < DURATION:
        # Read output from recording process
        line = record_process.stdout.readline()
        if line:
            print(f"\r{line.strip()}", end='', flush=True)
        else:
            remaining = int(DURATION - (time.time() - start_time))
            if remaining > 0:
                print(f"\rRecording... {remaining}s remaining", end='', flush=True)
            time.sleep(1)

    print("\n\nWaiting for recording to finish...")
    record_process.wait()

    # Copy audio file from container
    print("Copying audio file...")
    subprocess.run(
        ["wsl", "bash", "-c",
         f"docker cp subtitle-server:/tmp/recorded_audio.wav /mnt/c/Projects/priority/JifeSubtitles/{AUDIO_FILE}"],
        timeout=30
    )

    # Get system translations from logs
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
        f.write(f"System Translations\n")
        f.write(f"Duration: {DURATION} seconds\n")
        f.write(f"Total Subtitles: {len(subtitles)}\n\n")
        for i, s in enumerate(subtitles, 1):
            f.write(f"{i}. [{s['latency']:.2f}s] {s['text']}\n")
        f.write(f"\n--- COMBINED TEXT ---\n")
        f.write(' '.join([s['text'] for s in subtitles]))

    print(f"[OK] Audio saved to: {AUDIO_FILE}")
    print(f"[OK] System translations saved to: {SYSTEM_OUTPUT_FILE}")
    print(f"[OK] Captured {len(subtitles)} subtitles")

    # Check audio file
    if Path(AUDIO_FILE).exists():
        size = Path(AUDIO_FILE).stat().st_size
        print(f"[OK] Audio file size: {size:,} bytes ({size/1024/1024:.1f} MB)")
    else:
        print("[ERROR] Audio file not found!")
        return None, subtitles

    return AUDIO_FILE, subtitles


def transcribe_with_openai(audio_file):
    """Transcribe with OpenAI Whisper API"""
    api_key = os.environ.get('OPENAI_API_KEY')

    if not api_key:
        print("\n" + "=" * 70)
        print("  ERROR: OPENAI_API_KEY not found in .env file")
        print("=" * 70)
        print("\nMake sure .env file exists with:")
        print("OPENAI_API_KEY=your-key-here")
        return None

    print("\n" + "=" * 70)
    print("  TRANSCRIBING WITH OPENAI WHISPER API")
    print("=" * 70)
    print(f"\nAPI Key: {api_key[:10]}...")
    print("Uploading audio to OpenAI...")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        with open(audio_file, 'rb') as f:
            print("Processing with Whisper large-v3...")
            transcript = client.audio.translations.create(
                model="whisper-1",
                file=f,
                response_format="verbose_json"
            )

        print(f"[OK] OpenAI transcription completed")
        print(f"  Duration: {transcript.duration:.1f}s")

        return {
            'text': transcript.text,
            'duration': transcript.duration,
        }

    except ImportError:
        print("\n[ERROR] 'openai' package not installed")
        print("Install with: pip install openai")
        return None
    except Exception as e:
        print(f"\n[ERROR] OpenAI API error: {e}")
        import traceback
        traceback.print_exc()
        return None


def compare_results(system_subtitles, openai_result):
    """Compare system vs OpenAI"""
    print("\n" + "=" * 70)
    print("  QUALITY COMPARISON")
    print("=" * 70)

    system_text = ' '.join([s['text'] for s in system_subtitles])
    system_words = system_text.lower().split()

    print(f"\n--- OUR SYSTEM (faster-whisper large-v3) ---")
    print(f"Subtitles: {len(system_subtitles)}")
    print(f"Words: {len(system_words)}")
    print(f"Avg latency: {sum(s['latency'] for s in system_subtitles)/len(system_subtitles):.2f}s")
    print(f"\nText:\n{system_text}\n")

    if not openai_result:
        return None

    openai_text = openai_result['text']
    openai_words = openai_text.lower().split()

    print(f"--- OPENAI WHISPER (large-v3, cloud) ---")
    print(f"Words: {len(openai_words)}")
    print(f"\nText:\n{openai_text}\n")

    # Word-level comparison
    system_set = set(system_words)
    openai_set = set(openai_words)

    common = system_set & openai_set
    system_only = system_set - openai_set
    openai_only = openai_set - system_set

    similarity = len(common) / len(system_set | openai_set) if system_set or openai_set else 0

    print("=" * 70)
    print("  ANALYSIS")
    print("=" * 70)
    print(f"\nWord overlap: {len(common)} words")
    print(f"Jaccard similarity: {similarity*100:.1f}%")

    if system_only:
        print(f"\n--- In OUR system but NOT in OpenAI ---")
        print(f"Count: {len(system_only)}")
        print(f"{', '.join(sorted(system_only)[:30])}")

    if openai_only:
        print(f"\n--- In OpenAI but NOT in our system ---")
        print(f"Count: {len(openai_only)}")
        print(f"{', '.join(sorted(openai_only)[:30])}")

    return {
        'system': {
            'text': system_text,
            'words': len(system_words),
            'subtitles': len(system_subtitles),
            'avg_latency': sum(s['latency'] for s in system_subtitles)/len(system_subtitles)
        },
        'openai': {
            'text': openai_text,
            'words': len(openai_words),
            'duration': openai_result['duration']
        },
        'comparison': {
            'similarity': similarity,
            'common_words': len(common),
            'system_unique': sorted(list(system_only)),
            'openai_unique': sorted(list(openai_only))
        }
    }


def main():
    # Load .env
    load_env()

    print("\nStarting in 3 seconds...")
    print("Make sure your TV audio is playing!\n")
    time.sleep(3)

    # Step 1: Record audio + monitor system
    audio_file, system_subtitles = record_and_monitor()

    if not system_subtitles:
        print("\n[ERROR] No subtitles captured!")
        return

    if not audio_file or not Path(audio_file).exists():
        print("\n[ERROR] Audio recording failed!")
        return

    # Step 2: Transcribe with OpenAI
    openai_result = transcribe_with_openai(audio_file)

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
