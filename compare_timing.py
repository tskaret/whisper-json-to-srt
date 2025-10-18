#!/usr/bin/env python3
"""
Compare timing differences between manually corrected SRT and energy-generated SRT
"""

import re
from pathlib import Path

def parse_srt_time(time_str):
    """Convert SRT timestamp to seconds"""
    h, m, s = time_str.replace(',', '.').split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)

def parse_srt(filepath):
    """Parse SRT file and return list of subtitle entries"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Match subtitle blocks
    pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\d+\n|\Z)'
    matches = re.findall(pattern, content, re.DOTALL)

    subtitles = []
    for num, start_str, end_str, text in matches:
        subtitles.append({
            'num': int(num),
            'start': parse_srt_time(start_str),
            'end': parse_srt_time(end_str),
            'text': text.strip()
        })

    return subtitles

# Load files
corrected_path = r"D:\stevner\2025\regionalt\Lørdag\04-LørdagEttermiddag\04-LørdagEttermiddag_corrected.srt"
energy_path = r"D:\stevner\2025\regionalt\Lørdag\04-LørdagEttermiddag\test_refactored\04-LørdagEttermiddag_clean.srt"

print("Loading SRT files...")
corrected_subs = parse_srt(corrected_path)
energy_subs = parse_srt(energy_path)

print(f"Corrected SRT: {len(corrected_subs)} subtitles")
print(f"Energy SRT: {len(energy_subs)} subtitles")

# Compare first 20 subtitles
print("\n" + "="*80)
print("TIMING COMPARISON - First 20 Subtitles")
print("="*80)

start_diffs = []
end_diffs = []

for i in range(min(20, len(corrected_subs), len(energy_subs))):
    corr = corrected_subs[i]
    enrg = energy_subs[i]

    start_diff = enrg['start'] - corr['start']
    end_diff = corr['end'] - enrg['end']  # How much LATER corrected ends
    duration_corr = corr['end'] - corr['start']
    duration_enrg = enrg['end'] - enrg['start']

    start_diffs.append(start_diff)
    end_diffs.append(end_diff)

    print(f"\nSubtitle #{i+1}")
    print(f"  Text: {corr['text'][:50]}...")
    print(f"  Corrected:  {corr['start']:.3f}s -> {corr['end']:.3f}s (duration: {duration_corr:.3f}s)")
    print(f"  Energy:     {enrg['start']:.3f}s -> {enrg['end']:.3f}s (duration: {duration_enrg:.3f}s)")
    print(f"  Start diff: {start_diff:+.3f}s (energy - corrected)")
    print(f"  End diff:   {end_diff:+.3f}s (corrected - energy, BUFFER needed)")

# Calculate statistics
print("\n" + "="*80)
print("STATISTICS - First 20 Subtitles")
print("="*80)

import statistics

print(f"\nStart time differences (energy - corrected):")
print(f"  Average: {statistics.mean(start_diffs):+.3f}s")
print(f"  Median:  {statistics.median(start_diffs):+.3f}s")
print(f"  Min:     {min(start_diffs):+.3f}s")
print(f"  Max:     {max(start_diffs):+.3f}s")

print(f"\nEnd time buffer needed (corrected - energy):")
print(f"  Average: {statistics.mean(end_diffs):+.3f}s")
print(f"  Median:  {statistics.median(end_diffs):+.3f}s")
print(f"  Min:     {min(end_diffs):+.3f}s")
print(f"  Max:     {max(end_diffs):+.3f}s")

# Analyze gap to next subtitle
print("\n" + "="*80)
print("GAP ANALYSIS - Can we extend end times?")
print("="*80)

for i in range(min(10, len(energy_subs) - 1)):
    current = energy_subs[i]
    next_sub = energy_subs[i+1]

    gap = next_sub['start'] - current['end']
    buffer_needed = end_diffs[i]
    can_extend = gap >= buffer_needed

    print(f"\nSubtitle #{i+1} -> #{i+2}")
    print(f"  Current ends: {current['end']:.3f}s")
    print(f"  Next starts:  {next_sub['start']:.3f}s")
    print(f"  Gap:          {gap:.3f}s")
    print(f"  Buffer needed: {buffer_needed:+.3f}s")
    print(f"  Can extend?   {'YES' if can_extend else 'NO - would overlap'}")

print("\n" + "="*80)
print("RECOMMENDATION")
print("="*80)
avg_buffer = statistics.mean(end_diffs)
median_buffer = statistics.median(end_diffs)
print(f"\nAverage buffer needed: {avg_buffer:.3f}s ({avg_buffer*1000:.0f}ms)")
print(f"Median buffer needed:  {median_buffer:.3f}s ({median_buffer*1000:.0f}ms)")
print(f"\nSuggested implementation:")
print(f"  1. Add {avg_buffer:.3f}s to end time of each subtitle")
print(f"  2. Check if next subtitle would be blocked (gap < {avg_buffer:.3f}s)")
print(f"  3. If blocked, only extend to leave minimum 10ms gap")
