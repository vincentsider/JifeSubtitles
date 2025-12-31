# JIFE Windows GPU - AI Implementation Guide

**PURPOSE**: This document tells an AI coding assistant EXACTLY how to set up JIFE on Windows with an NVIDIA GPU. Follow these instructions precisely.

---

## OVERVIEW

JIFE (Japanese In-Flight Entertainment) runs real-time Japanese to English speech translation. This Windows version uses:
- **faster-whisper** with CTranslate2 for GPU inference
- **Docker Desktop** with NVIDIA GPU support via WSL2
- **large-v3** model with float16 (no memory constraints on desktop GPU)

**Expected Result**: Sub-0.5 second latency, best quality transcription.

---

## ARCHITECTURE

### Hardware HDMI Audio (Option 1)
```
HDMI Audio Source
       |
       v
USB Audio Adapter --> Windows PC (RTX GPU)
                           |
                      Docker Container:
                      - Audio capture (sounddevice)
                      - faster-whisper large-v3 float16
                      - Flask WebSocket server
                           |
                           v
                      http://PC_IP:5000 --> iPad/Phone browser
```

### Virtual Audio Cable (Option 2 - NEW)
```
Windows Apps (YouTube/Netflix/etc.)
       |
       v
VB-CABLE + VoiceMeeter --> Windows PC (RTX GPU)
       |                         |
       └─> Speakers         Docker Container:
                            - Audio capture (sounddevice)
                            - faster-whisper large-v3 float16
                            - Flask WebSocket server
                                   |
                                   v
                            http://PC_IP:5000 --> iPad/Phone browser
```

**See [AUDIO_SETUP_GUIDE.md](AUDIO_SETUP_GUIDE.md) for detailed audio configuration instructions.**

---

## PREREQUISITES (User must do manually)

1. **Windows 10/11 with WSL2**
   ```powershell
   wsl --install
   # Restart computer after
   ```

2. **Docker Desktop**
   - Download: https://www.docker.com/products/docker-desktop/
   - Enable "Use WSL 2 based engine" in settings

3. **NVIDIA Container Toolkit** (in WSL2 Ubuntu terminal)
   ```bash
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
   sudo apt-get update
   sudo apt-get install -y nvidia-container-toolkit
   sudo systemctl restart docker
   ```

4. **Verify GPU access**
   ```bash
   docker run --rm --gpus all nvidia/cuda:12.1-base-ubuntu22.04 nvidia-smi
   ```

---

## FILES IN THIS FOLDER

| File | Purpose |
|------|---------|
| `Dockerfile` | Builds the Windows x86_64 Docker image |
| `docker-compose.yml` | Runs the container with GPU + audio |
| `app/` | Application code (symlinked or copied from main) |
| `requirements.txt` | Python dependencies |
| `build.sh` | Build script (run in WSL2) |
| `run.sh` | Run script (run in WSL2) |

---

## STEP-BY-STEP IMPLEMENTATION

### Step 1: Clone the repository (on Windows in WSL2)

```bash
cd ~
git clone https://github.com/vincentsider/JifeSubtitles.git
cd JifeSubtitles/jife-windows
```

### Step 2: Build the Docker image

```bash
./build.sh
# OR manually:
docker compose build
```

This downloads ~8GB of dependencies and builds the image. Takes 10-20 minutes.

### Step 3: Configure audio device

**IMPORTANT:** Audio setup depends on your use case. See [AUDIO_SETUP_GUIDE.md](AUDIO_SETUP_GUIDE.md) for complete instructions.

**Quick summary:**
- **Hardware HDMI audio** (for external devices): See "Option 1" in AUDIO_SETUP_GUIDE.md
- **YouTube/browser audio** (for PC applications): See "Option 2" in AUDIO_SETUP_GUIDE.md

You can skip audio configuration for now and enable it later - the container will still run and the web interface will be accessible.

### Step 4: Run

```bash
./run.sh
# OR manually:
docker compose up -d
docker logs subtitle-server -f
```

### Step 5: Access subtitles

Find PC's IP:
```powershell
ipconfig  # Look for IPv4 Address
```

Open on iPad: `http://YOUR_PC_IP:5000`

---

## KEY DIFFERENCES FROM JETSON VERSION

| Aspect | Jetson | Windows |
|--------|--------|---------|
| Architecture | ARM64 (aarch64) | x86_64 |
| Base image | `nvidia/cuda:12.6-runtime-ubuntu22.04` (arm) | `nvidia/cuda:12.1-cudnn8-runtime-ubuntu22.04` (x86) |
| Model precision | INT8 (memory constrained) | float16 (full precision) |
| Beam size | 1 (speed) | 5 (accuracy) |
| VRAM needed | <4GB | ~4GB |
| GPU runtime | `runtime: nvidia` | `deploy.resources.reservations.devices` |

---

## TROUBLESHOOTING

### GPU not detected in Docker

```bash
# Check NVIDIA driver in WSL2
nvidia-smi

# Reinstall container toolkit
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### Audio device not found

```bash
# Check if USB passthrough is working
lsusb  # Should show your audio adapter

# List ALSA devices
arecord -l

# Try different device string
AUDIO_DEVICE=plughw:0,0 docker compose up
```

### Container won't start

```bash
# Check logs
docker logs subtitle-server

# Rebuild
docker compose build --no-cache
```

---

## CONFIGURATION OPTIONS

Environment variables in `docker-compose.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `AUDIO_DEVICE` | `plughw:1,0` | ALSA device name |
| `WHISPER_MODEL` | `large-v3` | Whisper model |
| `WHISPER_COMPUTE_TYPE` | `float16` | Precision (float16 best on desktop) |
| `WHISPER_BEAM_SIZE` | `5` | Accuracy (higher = better, slower) |

---

## TESTING

1. Build completes without error
2. Container starts and shows "SYSTEM READY"
3. GPU is being used (`nvidia-smi` shows process)
4. Web UI loads at http://localhost:5000
5. Speaking Japanese shows English subtitles

---

*This guide assumes the AI assistant has full access to create/edit files and run commands.*
