"""Test OpenAI API directly with the recorded audio"""
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

api_key = os.environ.get('OPENAI_API_KEY')
if not api_key:
    print("ERROR: OPENAI_API_KEY not found in .env")
    exit(1)

print(f"API Key: {api_key[:15]}...")

# Check audio file
audio_file = 'test_audio.wav'
if not Path(audio_file).exists():
    print(f"ERROR: {audio_file} not found")
    exit(1)

size = Path(audio_file).stat().st_size
print(f"Audio file: {audio_file} ({size:,} bytes)")

# Call OpenAI
try:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    print("\nUploading to OpenAI Whisper API...")
    with open(audio_file, 'rb') as f:
        response = client.audio.translations.create(
            model="whisper-1",
            file=f,
        )

    print(f"\nResponse type: {type(response)}")
    print(f"Response: {response}")
    print(f"\nText: '{response.text}'")
    print(f"Text length: {len(response.text)}")

    if not response.text:
        print("\nWARNING: OpenAI returned empty text!")
        print("This usually means:")
        print("1. Audio file contains only silence/music")
        print("2. Audio format is incompatible")
        print("3. File is corrupted")

        # Try transcription instead of translation
        print("\nTrying transcription (Japanese output)...")
        with open(audio_file, 'rb') as f:
            response2 = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="ja"
            )
        print(f"Japanese text: '{response2.text}'")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
