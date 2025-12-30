# SSH Commands Reference

Commands to manage JIFE when connected via SSH from your Mac.

---

## Connect to Jetson

```bash
ssh vincent@192.168.1.34
# Password: 3009inxs
```

---

## Service Management

```bash
# Check if service is running
sudo systemctl status jife-subtitles

# Restart service
sudo systemctl restart jife-subtitles

# Stop service
sudo systemctl stop jife-subtitles

# Start service
sudo systemctl start jife-subtitles

# View logs (live)
sudo journalctl -u jife-subtitles -f

# View container logs
docker logs subtitle-server -f

# View last 50 lines
docker logs subtitle-server --tail 50
```

---

## Change Model via Command Line

### See Available Models

```bash
curl -s http://localhost:5000/models | python3 -m json.tool
```

Output:
```json
{
    "models": [
        {"id": "large-v3:int8:1", "name": "Large-v3 INT8 (Best)"},
        {"id": "medium:int8:3", "name": "Medium INT8"},
        {"id": "small:int8:3", "name": "Small (Fastest)"}
    ],
    "current": "large-v3:int8:1",
    "switching": false
}
```

### Switch to Large-v3 (Best Quality)

```bash
curl -X POST http://localhost:5000/models/switch \
  -H "Content-Type: application/json" \
  -d '{"model": "large-v3:int8:1"}'
```

### Switch to Medium (Balanced)

```bash
curl -X POST http://localhost:5000/models/switch \
  -H "Content-Type: application/json" \
  -d '{"model": "medium:int8:3"}'
```

### Switch to Small (Fastest)

```bash
curl -X POST http://localhost:5000/models/switch \
  -H "Content-Type: application/json" \
  -d '{"model": "small:int8:3"}'
```

---

## Health Check

```bash
# Basic health
curl http://localhost:5000/health

# Full stats
curl -s http://localhost:5000/stats | python3 -m json.tool
```

---

## System Monitoring

```bash
# GPU/CPU/Memory usage (live)
sudo tegrastats

# Memory only
free -h

# Disk space
df -h

# Running processes
htop

# Docker containers
docker ps

# Docker resource usage
docker stats subtitle-server
```

---

## Audio Device

```bash
# List audio devices
arecord -l

# Test recording (5 seconds)
arecord -D hw:2,0 -f S16_LE -r 16000 -c 1 -d 5 /tmp/test.wav

# Play back test
aplay /tmp/test.wav
```

---

## Disable/Enable GUI

### Boot to Command Line Only (Saves ~500MB RAM)

```bash
sudo systemctl set-default multi-user.target
sudo reboot
```

### Start GUI Manually When Needed

```bash
sudo systemctl start gdm3
```

### Re-enable GUI on Boot

```bash
sudo systemctl set-default graphical.target
sudo reboot
```

---

## Quick Reference

| Task | Command |
|------|---------|
| SSH in | `ssh vincent@192.168.1.34` |
| Check status | `sudo systemctl status jife-subtitles` |
| View logs | `docker logs subtitle-server -f` |
| Switch to large-v3 | `curl -X POST localhost:5000/models/switch -H "Content-Type: application/json" -d '{"model":"large-v3:int8:1"}'` |
| Switch to medium | `curl -X POST localhost:5000/models/switch -H "Content-Type: application/json" -d '{"model":"medium:int8:3"}'` |
| Restart service | `sudo systemctl restart jife-subtitles` |
| Monitor GPU | `sudo tegrastats` |
| Disable GUI | `sudo systemctl set-default multi-user.target && sudo reboot` |

---

*Last updated: December 30, 2025*
