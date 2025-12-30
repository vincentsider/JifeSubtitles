# New Jetson Setup Guide

## Requirements

- Jetson Orin NX or Orin Nano
- JetPack 6.x (6.0, 6.1, 6.2, or 6.2.1) - **NOT JetPack 7.x**
- USB drive (32GB or larger) to transfer the Docker image

## Hardware Needed

- USB audio adapter with microphone INPUT (pink jack) - **NOT output-only adapters**
- HDMI audio extractor
- 3.5mm audio cable

---

## Step 1: Flash JetPack 6.x

Use NVIDIA SDK Manager on a Linux PC to flash JetPack 6.2.1 (or any 6.x) to your new Jetson.

---

## Step 2: Copy Docker Image to USB Drive

On your source Jetson (or wherever the image file is):

```bash
cp /home/vincent/JIFE/jife-faster-whisper.tar.gz /media/USB_DRIVE/
```

The file is approximately 13GB compressed (26GB uncompressed).

---

## Step 3: On New Jetson - Clone Repository

Open terminal and run:

```bash
cd /home/$USER
git clone https://github.com/vincentsider/JifeSubtitles.git
```

---

## Step 4: Copy Docker Image from USB to Jetson

```bash
cp /media/USB_DRIVE/jife-faster-whisper.tar.gz /home/$USER/JifeSubtitles/
```

---

## Step 5: Run Setup Script

```bash
cd /home/$USER/JifeSubtitles/subtitle-product
sudo ./setup.sh
```

Wait 5-10 minutes for Docker image to load.

---

## Step 6: Done

The service is now running and will auto-start on boot.

Open in browser: `http://JETSON_IP:5000`

To find the IP address:
```bash
hostname -I
```

---

## Troubleshooting

Check if service is running:
```bash
sudo systemctl status jife-subtitles
```

View logs:
```bash
docker logs subtitle-server --tail 50
```

Restart service:
```bash
sudo systemctl restart jife-subtitles
```

---

## Hardware Setup

1. Connect HDMI source -> HDMI audio extractor IN
2. Connect HDMI audio extractor OUT -> TV
3. Connect 3.5mm cable from extractor's headphone output -> USB audio adapter's **pink/microphone input**
4. Plug USB audio adapter into Jetson

---

## Web Interface

The web interface allows you to:
- View live subtitles
- Switch between Whisper models (small, medium, large-v3, large-v3-turbo)
- Default model is **large-v3** with INT8 quantization for best accuracy

---

## Models

Available models (selectable from web interface):
- **Small INT8** - Fastest, lowest memory, lower accuracy
- **Medium INT8** - Good balance of speed and accuracy (recommended for slower Jetsons)
- **Large-v3 Turbo INT8** - Fast large model
- **Large-v3 INT8** - Best accuracy, highest memory (default)

All models are included in the Docker image - no internet required.
