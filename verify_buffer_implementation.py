#!/usr/bin/env python3
"""
Verify POST_SPEECH_BUFFER implementation matches manual corrections
"""

import re

def parse_srt_time(time_str):
    """Convert SRT timestamp to seconds"""
    h, m, s = time_str.replace(',', '.').split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)

def parse_srt(filepath):
    """Parse SRT file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})'
    matches = re.findall(pattern, content)

    subtitles = []
    for num, start_str, end_str in matches:
        subtitles.append({
            'num': int(num),
            'start': parse_srt_time(start_str),
            'end': parse_srt_time(end_str)
        })
    return subtitles

# Load files
corrected = parse_srt(r"D:\stevner\2025\regionalt\Lørdag\04-LørdagEttermiddag\04-LørdagEttermiddag_corrected.srt")
with_buffer = parse_srt(r"D:\stevner\2025\regionalt\Lørdag\04-LørdagEttermiddag\test_with_buffer\04-LørdagEttermiddag_clean.srt")

print("="*70)
print("VERIFICATION: POST_SPEECH_BUFFER Implementation")
print("="*70)
print(f"\nCorrected SRT: {len(corrected)} subtitles")
print(f"With Buffer:   {len(with_buffer)} subtitles")

print("\n" + "="*70)
print("First 5 Subtitles - End Time Comparison")
print("="*70)
print(f"{'Sub':<5} {'Corrected':<12} {'With Buffer':<12} {'Diff':<10} {'Status'}")
print("-"*70)

for i in range(min(5, len(corrected), len(with_buffer))):
    c = corrected[i]
    b = with_buffer[i]

    diff = abs(c['end'] - b['end'])
    status = "✓ MATCH" if diff < 0.050 else f"Δ {diff*1000:.0f}ms"

    print(f"#{i+1:<4} {c['end']:7.3f}s     {b['end']:7.3f}s     {(b['end']-c['end'])*1000:+6.0f}ms   {status}")

# Calculate statistics
diffs = [abs(corrected[i]['end'] - with_buffer[i]['end']) for i in range(min(5, len(corrected), len(with_buffer)))]

print("\n" + "="*70)
print("Statistics")
print("="*70)
print(f"Average difference: {sum(diffs)/len(diffs)*1000:.0f}ms")
print(f"Max difference:     {max(diffs)*1000:.0f}ms")
print(f"\nTarget: < 50ms difference")
print(f"Result: {'✓ PASS' if max(diffs) < 0.050 else '✗ FAIL'}")
