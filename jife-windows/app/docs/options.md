My “ultimate” offline recommendation on an RTX 4080 (16GB)


Option B (best quality/robustness for your use case): 
SeamlessM4T v2 (speech→text translation)


Run Meta SeamlessM4T v2 directly as speech-to-text translation (Japanese audio → English text). It’s specifically built for multimodal translation (speech↔text) rather than “ASR model + translation hack.” 



Why it’s the best fit for Japanese TV audio

Designed for speech translation, not just transcription. 

Generally more robust than a two-model pipeline when audio is messy (TV often is). (Still not magic, but usually a clear step up.)



Latency reality: you’ll still want ~2–4s buffering (sliding window) for coherent subtitles.

#####

Option C (best controllability; often excellent if your ASR is solid): 
Whisper (JA ASR) + dedicated MT : SeamlessM4T v2 in text-to-text mode (JA text → EN text) 


Whisper only for Japanese transcription

Force language=ja

Use transcribe, not translate

Keep condition_on_previous_text=true so it doesn’t lose context between chunks

Translate the Japanese text with a real MT model

Best offline candidates (quality vs speed tradeoffs):  SeamlessM4T v2



