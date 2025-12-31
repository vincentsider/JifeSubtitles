"""Quick 2-minute monitoring of subtitle system"""
import subprocess
import time
import re

print("=== MONITORING SUBTITLE SYSTEM FOR 120 SECONDS ===\n")
print("Monitoring started...")

# Wait 120 seconds
time.sleep(120)

print("\n=== COLLECTING RESULTS ===\n")

# Get logs from last 2 minutes
result = subprocess.run(
    ["wsl", "bash", "-c", "docker logs subtitle-server 2>&1 | tail -300"],
    capture_output=True,
    text=True,
    timeout=30
)

logs = result.stdout

# Extract subtitles with latency
subtitles = []
for line in logs.split('\n'):
    match = re.search(r'\[(\d+\.\d+)s\] (.+)$', line)
    if match and 'subtitle-system:' in line:
        latency = float(match.group(1))
        text = match.group(2).strip()
        subtitles.append({'latency': latency, 'text': text})

if not subtitles:
    print("⚠️  No subtitles captured!")
    exit(1)

# Calculate stats
latencies = [s['latency'] for s in subtitles]

print(f"=== PERFORMANCE RESULTS ===\n")
print(f"Total Subtitles: {len(subtitles)}")
print(f"Subtitles/min: {len(subtitles)/2:.1f}")
print(f"\nLatency Statistics:")
print(f"  Min: {min(latencies):.2f}s")
print(f"  Avg: {sum(latencies)/len(latencies):.2f}s")
print(f"  Max: {max(latencies):.2f}s")
print(f"  Median: {sorted(latencies)[len(latencies)//2]:.2f}s")

# Distribution
fast = sum(1 for l in latencies if l < 0.5)
normal = sum(1 for l in latencies if 0.5 <= l < 1.0)
slow = sum(1 for l in latencies if l >= 1.0)

print(f"\nDistribution:")
print(f"  Fast (<0.5s): {fast} ({fast/len(latencies)*100:.1f}%)")
print(f"  Normal (0.5-1s): {normal} ({normal/len(latencies)*100:.1f}%)")
print(f"  Slow (>1s): {slow} ({slow/len(latencies)*100:.1f}%)")

# Show all subtitles
print(f"\n=== ALL SUBTITLES ===\n")
for i, s in enumerate(subtitles, 1):
    print(f"{i:3}. [{s['latency']:.2f}s] {s['text']}")

# Check for hallucination patterns
thank_you_count = sum(1 for s in subtitles if 'thank you' in s['text'].lower() or 'thanks' in s['text'].lower())
print(f"\n=== QUALITY CHECK ===")
print(f"'Thank you' phrases: {thank_you_count} ({thank_you_count/len(subtitles)*100:.1f}%)")

# Save results
with open('monitoring_results.txt', 'w', encoding='utf-8') as f:
    f.write(f"Monitoring Results - {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    f.write(f"Total Subtitles: {len(subtitles)}\n")
    f.write(f"Avg Latency: {sum(latencies)/len(latencies):.2f}s\n\n")
    for s in subtitles:
        f.write(f"[{s['latency']:.2f}s] {s['text']}\n")

print(f"\n✓ Results saved to monitoring_results.txt")
