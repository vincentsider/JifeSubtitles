"""
FINAL COMPARISON TEST
Runs subtitle system in recording mode, then compares with OpenAI.
"""
import subprocess
import time
import json
import os
from pathlib import Path

# Load .env
env_file = Path('.env')
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

print("=" * 70)
print("  FINAL QUALITY COMPARISON TEST")
print("=" * 70)
print("\nThis will:")
print("1. Stop current subtitle system")
print("2. Run in RECORDING MODE for 120 seconds")
print("3. Extract system translations from logs")
print("4. Compare recorded audio with OpenAI Whisper")
print("\n" + "=" * 70)
input("\nPress ENTER to continue...")

# Step 1: Stop current system
print("\nStopping current subtitle system...")
subprocess.run(["wsl", "bash", "-c", "cd /mnt/c/Projects/priority/JifeSubtitles/jife-windows && docker compose down"], timeout=30)

# Step 2: Run in recording mode
print("\nStarting system in RECORDING MODE...")
print("This will run for 120 seconds, then auto-stop.\n")

subprocess.run([
    "wsl", "bash", "-c",
    "cd /mnt/c/Projects/priority/JifeSubtitles/jife-windows && docker compose run --rm subtitle-server python3 /app/app/main_with_recording.py"
], timeout=180)

# Step 3: Get recorded audio
print("\nCopying recorded audio...")
subprocess.run([
    "wsl", "bash", "-c",
    "docker cp subtitle-server:/tmp/recorded_audio.wav /mnt/c/Projects/priority/JifeSubtitles/test_audio.wav"
], timeout=30)

if not Path('test_audio.wav').exists():
    print("ERROR: Audio file not found!")
    exit(1)

size = Path('test_audio.wav').stat().st_size
print(f"[OK] Audio file: {size:,} bytes ({size/1024/1024:.1f} MB)")

# Step 4: Get system translations from container logs
print("\nExtracting system translations...")
result = subprocess.run([
    "wsl", "bash", "-c",
    "docker logs $(docker ps -alq) 2>&1 | grep 'subtitle-system:' | grep -E '\\[.*s\\]'"
], capture_output=True, text=True, timeout=30)

import re
subtitles = []
for line in result.stdout.split('\n'):
    match = re.search(r'\[(\d+\.\d+)s\] (.+)$', line)
    if match:
        subtitles.append({'latency': float(match.group(1)), 'text': match.group(2).strip()})

print(f"[OK] Captured {len(subtitles)} subtitles")

system_text = ' '.join([s['text'] for s in subtitles])
print(f"\nSystem output ({len(system_text.split())} words):")
print(f"{system_text[:200]}...\n")

# Step 5: Transcribe with OpenAI
api_key = os.environ.get('OPENAI_API_KEY')
if not api_key:
    print("ERROR: OPENAI_API_KEY not set")
    exit(1)

print("Uploading to OpenAI Whisper API...")
try:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    with open('test_audio.wav', 'rb') as f:
        response = client.audio.translations.create(
            model="whisper-1",
            file=f,
        )

    openai_text = response.text
    print(f"[OK] OpenAI transcription completed")
    print(f"\nOpenAI output ({len(openai_text.split())} words):")
    print(f"{openai_text[:200]}...\n")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Step 6: Compare
print("=" * 70)
print("  COMPARISON")
print("=" * 70)

system_words = set(system_text.lower().split())
openai_words = set(openai_text.lower().split())

common = system_words & openai_words
similarity = len(common) / len(system_words | openai_words) if system_words or openai_words else 0

print(f"\nWord overlap: {len(common)}")
print(f"Similarity: {similarity*100:.1f}%")
print(f"System unique: {len(system_words - openai_words)}")
print(f"OpenAI unique: {len(openai_words - system_words)}")

# Save results
results = {
    'system': {'text': system_text, 'words': len(system_words), 'subtitles': len(subtitles)},
    'openai': {'text': openai_text, 'words': len(openai_words)},
    'comparison': {'similarity': similarity, 'common_words': len(common)}
}

with open('final_comparison.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\n[OK] Results saved to final_comparison.json")

# Step 7: Restart normal system
print("\nRestarting normal subtitle system...")
subprocess.run(["wsl", "bash", "-c", "cd /mnt/c/Projects/priority/JifeSubtitles/jife-windows && docker compose up -d"], timeout=60)

print("\n" + "=" * 70)
print("  TEST COMPLETE")
print("=" * 70)
