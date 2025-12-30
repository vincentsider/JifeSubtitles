# JIFE Subtitles - Windows GPU Edition

Real-time Japanese → English subtitle system for Windows PCs with NVIDIA GPUs.

## Quick Start

### 1. System Requirements
- Windows 10/11 with WSL2
- NVIDIA GPU (RTX 20xx/30xx/40xx or newer)
- Docker Desktop
- 10GB disk space

### 2. Build the System
```bash
cd jife-windows
./build.sh
```

### 3. Start the Container
```bash
./run.sh
```

### 4. Access Subtitles
Open http://localhost:5000 in your browser

---

## Audio Input Options

### Option 1: Hardware HDMI Audio
**For:** Game consoles, set-top boxes, external devices

Uses HDMI audio extractor + USB adapter to capture audio from external HDMI sources.

📖 [See AUDIO_SETUP_GUIDE.md - Option 1](AUDIO_SETUP_GUIDE.md#option-1-hardware-hdmi-audio-original-design-)

### Option 2: Virtual Audio Cable ⭐ NEW
**For:** YouTube, Netflix, browser content, PC games

Uses VB-CABLE to capture any audio playing on your Windows PC.

📖 [See AUDIO_SETUP_GUIDE.md - Option 2](AUDIO_SETUP_GUIDE.md#option-2-virtual-audio-cable-software-routing-)

---

## Documentation

- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Complete setup instructions for AI assistants
- **[AUDIO_SETUP_GUIDE.md](AUDIO_SETUP_GUIDE.md)** - Detailed audio configuration for both methods
- **[next_steps.md](next_steps.md)** - Post-installation next steps

---

## Key Features

✅ **Multiple Model Sizes** - Choose between tiny, base, small, medium, large-v3
✅ **GPU Accelerated** - Uses NVIDIA CUDA for fast inference
✅ **Two Audio Input Methods** - Hardware HDMI or virtual audio cable
✅ **Mobile Friendly** - Access subtitles from iPad, phone, any device
✅ **Offline** - No cloud dependencies, runs 100% locally
✅ **Low Latency** - Sub-500ms from speech to subtitle display

---

## Architecture

```
┌──────────────────┐         ┌──────────────────┐
│  Audio Source    │         │  Windows Apps    │
│  (HDMI Device)   │         │ (YouTube/etc.)   │
└────────┬─────────┘         └────────┬─────────┘
         │                            │
         v                            v
   USB Audio Adapter            VB-CABLE
         │                            │
         └────────────┬───────────────┘
                      │
                      v
              ┌───────────────┐
              │  WSL2 Ubuntu  │
              │  /dev/snd     │
              └───────┬───────┘
                      │
                      v
         ┌────────────────────────┐
         │  Docker Container      │
         │  - faster-whisper      │
         │  - GPU (CUDA 12.1)     │
         │  - Flask WebSocket     │
         └────────────┬───────────┘
                      │
                      v
              http://PC_IP:5000
                      │
         ┌────────────┴────────────┐
         │                         │
         v                         v
    ┌─────────┐              ┌─────────┐
    │  Phone  │              │  Tablet │
    │ Browser │              │ Browser │
    └─────────┘              └─────────┘
```

---

## Common Commands

```bash
# View logs
docker logs subtitle-server -f

# Restart container
docker compose restart

# Stop container
docker compose down

# Check GPU usage
wsl nvidia-smi

# Health check
curl http://localhost:5000/health
```

---

## Configuration

Edit `docker-compose.yml` to change:

| Variable | Default | Options | Description |
|----------|---------|---------|-------------|
| `WHISPER_MODEL` | `large-v3` | `tiny`, `base`, `small`, `medium`, `large-v3` | Model size |
| `WHISPER_COMPUTE_TYPE` | `float16` | `float16`, `float32`, `int8` | Precision |
| `WHISPER_BEAM_SIZE` | `5` | `1`-`10` | Accuracy (higher = better/slower) |
| `AUDIO_DEVICE` | `plughw:1,0` | `plughw:X,0` | Audio capture device |

After changes: `docker compose restart`

---

## Troubleshooting

### Container starts but no subtitles appear
1. Check audio is configured: [AUDIO_SETUP_GUIDE.md](AUDIO_SETUP_GUIDE.md)
2. Verify audio device: `wsl bash -c "arecord -l"`
3. Check logs: `docker logs subtitle-server -f`

### GPU not detected
1. Verify: `wsl nvidia-smi`
2. Reinstall NVIDIA Container Toolkit (see IMPLEMENTATION_GUIDE.md)

### Poor translation quality
1. Try `large-v3` model (best quality)
2. Increase `WHISPER_BEAM_SIZE` to 5 or 7
3. Ensure audio quality is good (test with `arecord`)

### High latency
1. Try `medium` or `small` model (faster)
2. Reduce `WHISPER_BEAM_SIZE` to 1 or 3
3. Check GPU isn't overloaded: `nvidia-smi`

---

## Performance Guide

| Model | VRAM | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| `tiny` | ~1GB | Very Fast | Poor | Testing only |
| `base` | ~1GB | Fast | Fair | Quick demos |
| `small` | ~2GB | Medium | Good | Balanced |
| `medium` | ~3GB | Slow | Very Good | Quality focused |
| `large-v3` | ~4GB | Slowest | Excellent | Best quality (recommended) |

**Recommended for RTX 4080:** `large-v3` with `float16` and `beam_size=5`

---

## License

MIT License - See main repository for details

---

## Support

For issues and questions:
- Check [AUDIO_SETUP_GUIDE.md](AUDIO_SETUP_GUIDE.md) for audio problems
- Review container logs: `docker logs subtitle-server -f`
- Verify GPU access: `wsl nvidia-smi`

---

**Made for translating Japanese content in real-time. Perfect for anime, games, and live streams! 🎌→🇬🇧**
