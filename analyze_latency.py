import re
import subprocess

# Get logs
result = subprocess.run(
    ['wsl', 'bash', '-c', "docker logs subtitle-server 2>&1 | grep -E '\\[[0-9]+\\.[0-9]+s\\]' | tail -100"],
    capture_output=True,
    text=True
)

# Extract latencies
latencies = []
for line in result.stdout.strip().split('\n'):
    match = re.search(r'\[(\d+\.\d+)s\]', line)
    if match:
        latencies.append(float(match.group(1)))

if latencies:
    print(f"Latency Statistics (n={len(latencies)} samples):")
    print(f"  Min: {min(latencies):.2f}s")
    print(f"  Max: {max(latencies):.2f}s")
    print(f"  Avg: {sum(latencies)/len(latencies):.2f}s")
    print(f"  Median: {sorted(latencies)[len(latencies)//2]:.2f}s")

    # Distribution
    fast = sum(1 for l in latencies if l < 0.5)
    normal = sum(1 for l in latencies if 0.5 <= l < 1.0)
    slow = sum(1 for l in latencies if l >= 1.0)

    print(f"\nDistribution:")
    print(f"  Fast (<0.5s):  {fast} ({fast/len(latencies)*100:.1f}%)")
    print(f"  Normal (0.5-1s): {normal} ({normal/len(latencies)*100:.1f}%)")
    print(f"  Slow (>1s):    {slow} ({slow/len(latencies)*100:.1f}%)")
