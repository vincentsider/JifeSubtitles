"""
Compare system translations with OpenAI Whisper
Reads from system_translations.txt and test_audio.wav (if available)
"""
import json
import subprocess
import os

print("=" * 70)
print("  OPENAI WHISPER COMPARISON")
print("=" * 70)

# Read our system translations
print("\nReading system translations...")
with open('system_translations.txt', 'r', encoding='utf-8') as f:
    content = f.read()

# Extract text
lines = content.split('\n')
combined_line = [l for l in lines if l.startswith('--- COMBINED TEXT ---')]
if combined_line:
    idx = lines.index(combined_line[0])
    system_text = lines[idx + 1] if idx + 1 < len(lines) else ""
else:
    system_text = ""

print(f"System output ({len(system_text.split())} words):")
print(f"{system_text[:200]}...\n")

# Get API key
print("Enter your OpenAI API key (or press Enter to skip):")
api_key = input("> ").strip()

if not api_key:
    print("\nSkipping OpenAI comparison.")
    exit(0)

# Check for audio file
if not os.path.exists('test_audio.wav'):
    print("\nERROR: test_audio.wav not found!")
    print("Audio capture failed. Cannot compare with OpenAI.")
    exit(1)

print(f"\nAudio file size: {os.path.getsize('test_audio.wav')} bytes")

# Call OpenAI API
print("\nUploading to OpenAI Whisper API...")
try:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)

    with open('test_audio.wav', 'rb') as f:
        print("Transcribing with Whisper large-v3...")
        transcript = client.audio.translations.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json"
        )

    openai_text = transcript.text
    duration = transcript.duration

    print(f"\n[OK] OpenAI transcription completed")
    print(f"Duration: {duration:.1f}s")
    print(f"OpenAI output ({len(openai_text.split())} words):")
    print(f"{openai_text[:200]}...\n")

    # Compare
    print("=" * 70)
    print("  COMPARISON")
    print("=" * 70)

    system_words = set(system_text.lower().split())
    openai_words = set(openai_text.lower().split())

    common = system_words & openai_words
    system_only = system_words - openai_words
    openai_only = openai_words - system_words

    similarity = len(common) / len(system_words | openai_words) if system_words or openai_words else 0

    print(f"\nWord overlap: {len(common)} words")
    print(f"Similarity: {similarity*100:.1f}%")
    print(f"\nWords in OUR system but NOT OpenAI: {len(system_only)}")
    if system_only:
        print(f"  {', '.join(sorted(system_only)[:20])}")
    print(f"\nWords in OpenAI but NOT our system: {len(openai_only)}")
    if openai_only:
        print(f"  {', '.join(sorted(openai_only)[:20])}")

    # Save comparison
    results = {
        'system': {'text': system_text, 'words': len(system_text.split())},
        'openai': {'text': openai_text, 'words': len(openai_text.split()), 'duration': duration},
        'comparison': {
            'common_words': len(common),
            'similarity': similarity,
            'system_unique': sorted(list(system_only)),
            'openai_unique': sorted(list(openai_only))
        }
    }

    with open('openai_comparison.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Results saved to openai_comparison.json")

except ImportError:
    print("\nERROR: openai package not installed")
    print("Install with: pip install openai")
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
