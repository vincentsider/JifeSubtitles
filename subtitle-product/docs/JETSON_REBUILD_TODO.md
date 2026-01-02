# Jetson Orin NX - Rebuild Required

## What Changed

A new model option was added to the Jetson version:

**New Option: Large-v3 FP16 (Test)**
- Added to `subtitle-product/app/web/server.py`
- Uses `float16` precision instead of `int8`
- May use more VRAM but potentially better quality
- Allows testing FP16 vs INT8 to compare quality/performance

```python
{
    'id': 'large-v3:float16:1',
    'model': 'large-v3',
    'name': 'Large-v3 FP16 (Test)',
    'description': 'FP16 precision - may use more VRAM but potentially better quality',
    'compute_type': 'float16',
    'beam_size': 1,
},
```

## Why Rebuild is Needed

The Docker container on the Jetson contains the old version of `server.py`. To make the new FP16 option available in the web UI dropdown, you need to rebuild the container with the updated code.

## Prerequisites

1. The Jetson Orin NX is at IP `192.168.1.34`
2. SSH access is configured
3. The `subtitle-product` folder is synced to the Jetson (or mounted)

## Step-by-Step Instructions

### 1. Connect to the Jetson

```bash
ssh vincent@192.168.1.34
```

### 2. Navigate to the project directory

```bash
cd /home/vincent/JIFE/subtitle-product
# OR wherever your subtitle-product folder is located
```

### 3. Pull the latest code (if using git)

```bash
git pull origin main
```

Or if you're copying files manually, ensure `app/web/server.py` has the new FP16 option.

### 4. Stop the running container (if any)

```bash
docker compose down
```

### 5. Rebuild the Docker image

```bash
docker compose build --no-cache
```

This will:
- Download any base image updates if needed (~3.4GB for L4T base if not cached)
- Install Python dependencies
- Copy the updated `server.py` with the new FP16 option

**Expected build time:** 5-15 minutes depending on what's cached

### 6. Start the container (when ready to use)

```bash
docker compose up -d
```

### 7. Verify the new option appears

1. Open browser to `http://192.168.1.34:5000`
2. Check the model dropdown in the top-right corner
3. You should see "Large-v3 FP16 (Test)" as a new option

## Available Models After Rebuild

| Model | Compute Type | Beam Size | VRAM Usage | Notes |
|-------|--------------|-----------|------------|-------|
| Large-v3 INT8 (Default) | int8 | 1 | ~2GB | Best for 8GB Jetson |
| Large-v3 INT8 (Accurate) | int8 | 3 | ~2.5GB | More accurate, slower |
| Large-v3 INT8 (Quality) | int8 | 5 | ~3GB | Highest quality INT8 |
| **Large-v3 FP16 (Test)** | float16 | 1 | ~3-4GB | **NEW** - Test option |

## Troubleshooting

### Build fails with disk space error
```bash
docker system prune -a  # Cleans old images
```

### Container won't start (OOM)
FP16 uses more VRAM. If it crashes, switch back to INT8:
1. Access the web UI
2. Select one of the INT8 options from the dropdown

### Can't see the new option
1. Force refresh the browser (Ctrl+F5)
2. Check container logs: `docker logs subtitle-server`
3. Verify server.py was copied correctly in the container

## Notes

- The Windows version (`jife-windows`) is separate and already has Option E (Enhanced Whisper with audio preprocessing)
- This Jetson rebuild only adds the FP16 test option
- INT8 is still recommended for 8GB Jetson - FP16 is for testing quality comparison
