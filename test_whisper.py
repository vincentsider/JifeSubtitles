#!/usr/bin/env python3
"""Test Whisper translation with Japanese audio"""
import whisper

print('Loading Whisper small model...')
model = whisper.load_model('small')
print('Model loaded, transcribing Japanese audio...')
result = model.transcribe('/data/subtitle-product/docs/japanese.mp3', task='translate', language='ja')
print('=' * 60)
print('TRANSLATION:')
print(result['text'])
print('=' * 60)
