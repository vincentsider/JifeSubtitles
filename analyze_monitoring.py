import re

# Read monitoring data
with open(r'C:\Users\Owner\AppData\Local\Temp\claude\c--Projects-priority-JifeSubtitles\tasks\b4a747f.output', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Extract latencies
latencies = []
for match in re.finditer(r'\[(\d+\.\d+)s\]', content):
    latencies.append(float(match.group(1)))

# Count "thank you" occurrences
thank_you_count = content.lower().count('thank you')
total_lines = len(re.findall(r'subtitle-system:', content))

print(f"=== 120-SECOND MONITORING RESULTS ===\n")
print(f"Total Subtitles: {total_lines}")
print(f"'Thank you' count: {thank_you_count} ({thank_you_count/total_lines*100:.1f}%)")

print(f"\n=== LATENCY STATS ===")
if latencies:
    print(f"Samples: {len(latencies)}")
    print(f"Min: {min(latencies):.2f}s")
    print(f"Max: {max(latencies):.2f}s")
    print(f"Avg: {sum(latencies)/len(latencies):.2f}s")
    print(f"Median: {sorted(latencies)[len(latencies)//2]:.2f}s")

    fast = sum(1 for l in latencies if l < 0.4)
    normal = sum(1 for l in latencies if 0.4 <= l < 1.0)
    slow = sum(1 for l in latencies if l >= 1.0)

    print(f"\nDistribution:")
    print(f"  Fast (<0.4s): {fast} ({fast/len(latencies)*100:.1f}%)")
    print(f"  Normal (0.4-1s): {normal} ({normal/len(latencies)*100:.1f}%)")
    print(f"  Slow (>1s): {slow} ({slow/len(latencies)*100:.1f}%)")

# Quality examples
print(f"\n=== QUALITY SAMPLES ===")
good_samples = [
    "The Glittering Japan Record Awards were held today",
    "There is a fear that it will be heavy snow",
    "The north wind is blowing all over the country",
    "This is the first time in a long time that I have been confirmed to be infected",
    "The eggs of the Tokyo district in February"
]
print("Good translations found:")
for s in good_samples:
    if s.lower() in content.lower():
        print(f"  ✓ {s}")
