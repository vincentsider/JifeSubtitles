# New Jetson Setup Guide

## Requirements

- Jetson Orin NX or Orin Nano
- JetPack 6.x (6.0, 6.1, 6.2, or 6.2.1) - **NOT JetPack 7.x**
- USB drive (16GB or larger) to transfer the Docker image

## Hardware Needed

- USB audio adapter with microphone INPUT (pink jack) - **NOT output-only adapters**
- HDMI audio extractor
- 3.5mm audio cable

---

## Step 1: Flash JetPack 6.x

Use NVIDIA SDK Manager on a Linux PC to flash JetPack 6.2.1 (or any 6.x) to your new Jetson.

---

## Step 2: Copy Docker Image to USB Drive

On your OLD Jetson (or wherever the image file is):

```bash
cp /home/vincent/JIFE/whisper_trt_image.tar.gz /media/USB_DRIVE/
```

The file is approximately 10-15GB.

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
cp /media/USB_DRIVE/whisper_trt_image.tar.gz /home/$USER/JifeSubtitles/
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

1. Connect HDMI source → HDMI audio extractor IN
2. Connect HDMI audio extractor OUT → TV
3. Connect 3.5mm cable from extractor's headphone output → USB audio adapter's **pink/microphone input**
4. Plug USB audio adapter into Jetson
