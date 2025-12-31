"""
Simple script to get OpenAI transcription for comparison
"""
import os
import sys

# Check for API key
api_key = os.environ.get('OPENAI_API_KEY')
if not api_key:
    print("ERROR: OPENAI_API_KEY not set!")
    print("Set it with: set OPENAI_API_KEY=your-key-here")
    sys.exit(1)

print(f"API Key found: {api_key[:10]}...")

# Try to import and use OpenAI
try:
    from openai import OpenAI
    print("OpenAI package imported successfully")

    client = OpenAI(api_key=api_key)
    print("OpenAI client created")

    # Test with a simple request
    print("\nTesting API connection...")
    models = client.models.list()
    print(f"API connection successful! Found {len(list(models.data))} models")

except ImportError:
    print("\nERROR: openai package not installed")
    print("Install with: pip install openai")
    sys.exit(1)
except Exception as e:
    print(f"\nERROR: {e}")
    sys.exit(1)

print("\nReady to transcribe audio files!")
