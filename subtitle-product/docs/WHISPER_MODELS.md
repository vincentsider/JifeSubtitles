# Whisper Models - What to Know and Monitor

## Who Created What

### OpenAI Created the Whisper MODEL

OpenAI created **Whisper** - the neural network (the "brain") trained on 680,000 hours of multilingual audio. This is the actual AI that understands speech.

- **Release**: September 2022
- **License**: MIT (fully open source)
- **Repository**: https://github.com/openai/whisper
- **Models on HuggingFace**: https://huggingface.co/openai

### faster-whisper is a RUNTIME (Not a Model)

**faster-whisper** runs the exact same OpenAI model using CTranslate2 (optimized C++ code) instead of PyTorch. Same brain, faster body.

- **Creator**: Guillaume Klein (Systran)
- **Repository**: https://github.com/SYSTRAN/faster-whisper
- **Benefit**: 2-4x faster, 50% less memory

```
OpenAI Whisper MODEL (the weights/brain)
         |
         +---> PyTorch runtime (original OpenAI code, slow)
         |
         +---> faster-whisper/CTranslate2 (same model, 2-4x faster) <-- WE USE THIS
         |
         +---> WhisperTRT/TensorRT (same model, NVIDIA GPU optimized)
         |
         +---> whisper.cpp (same model, CPU optimized)
```

**JIFE uses**: OpenAI's large-v3 model running on faster-whisper runtime.

---

## Model Sizes Comparison

| Model | Parameters | VRAM | Japanese Quality | Speed | Translation |
|-------|-----------|------|------------------|-------|-------------|
| tiny | 39M | ~1GB | Poor | Fastest | Yes |
| base | 74M | ~1GB | OK | Very fast | Yes |
| small | 244M | ~2GB | Good | Fast | Yes |
| **medium** | 769M | ~3GB | Very good | Medium | **Yes** |
| large-v2 | 1.5B | ~4GB | Excellent | Slow | Yes |
| **large-v3** | 1.5B | ~4GB | **Best** | Slow | **Yes** |
| large-v3-turbo | 809M | ~3GB | Excellent | Fast | **NO!** |

### Why large-v3-turbo Does NOT Work for Translation

large-v3-turbo was fine-tuned ONLY on transcription data, NOT translation data. When you use `task='translate'`, it ignores the task and returns the original language.

> "Unlike Distil-Whisper, Whisper turbo was fine-tuned for two more epochs over multilingual transcription data, **excluding translation data**, on which they don't expect turbo to perform well."

**Source**: https://github.com/SYSTRAN/faster-whisper/issues/1237

---

## What Models JIFE Supports

For Japanese-to-English translation, only these models work:

| Model ID | Name | Use Case |
|----------|------|----------|
| `large-v3:int8:1` | Large-v3 INT8 | Best accuracy (default) |
| `medium:int8:3` | Medium INT8 | Good balance |
| `small:int8:3` | Small INT8 | Fastest, lower quality |

---

## What to Monitor for Improvements

### 1. faster-whisper Releases

https://github.com/SYSTRAN/faster-whisper/releases

Watch for:
- New optimizations
- Better quantization (int4?)
- New model support

### 2. OpenAI Whisper Updates

https://github.com/openai/whisper

Watch for:
- New model versions (large-v4?)
- Improved Japanese support

### 3. HuggingFace Japanese Models

https://huggingface.co/models?search=whisper+japanese

Interesting models to watch:
- `kotoba-tech/kotoba-whisper-v2.0` - Fine-tuned for Japanese
- `distil-whisper/*` - Faster distilled versions

### 4. Groq API (for Cloud Version)

https://console.groq.com/docs/models

Watch for:
- New models
- Price changes
- Speed improvements

### 5. NVIDIA TensorRT-LLM

https://github.com/NVIDIA/TensorRT-LLM

Watch for:
- Optimized Whisper for Jetson
- Better INT8/INT4 support

---

## Key Metrics to Track

When evaluating new models or runtimes:

| Metric | Current (large-v3 INT8) | Goal |
|--------|-------------------------|------|
| RTF (Real-Time Factor) | 0.5-1.0 | < 0.3 |
| Latency (speech to text) | 3-4 seconds | < 2 seconds |
| VRAM usage | ~4GB | < 3GB |
| WER (Word Error Rate) | ~5% Japanese | < 3% |
| Translation accuracy | Good | Better |

**RTF**: Time to process / Audio duration. RTF < 1.0 means faster than real-time.

---

## Sources

- [OpenAI Whisper GitHub](https://github.com/openai/whisper)
- [faster-whisper GitHub](https://github.com/SYSTRAN/faster-whisper)
- [HuggingFace whisper-large-v3](https://huggingface.co/openai/whisper-large-v3)
- [HuggingFace whisper-large-v3-turbo](https://huggingface.co/openai/whisper-large-v3-turbo)
- [faster-whisper turbo translation issue](https://github.com/SYSTRAN/faster-whisper/issues/1237)

---

*Last updated: December 30, 2025*
