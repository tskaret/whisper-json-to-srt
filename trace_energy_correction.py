#!/usr/bin/env python3
"""
Trace what happens to 'inne i bildet' after energy correction
"""

import json
import sys
sys.path.insert(0, 'D:\\Kreativitet\\subtitle-processing-experiments')

from json_to_srt_energy import SRTConverter, Word

# Load JSON data
json_path = r'd:\stevner\2025\regionalt\Lørdag\04-LørdagEttermiddag\04-LørdagEttermiddag.json'
audio_path = r'd:\stevner\2025\regionalt\Lørdag\04-LørdagEttermiddag\04-LørdagEttermiddag.mp3'

print("Creating converter...")
converter = SRTConverter(
    audio_path=audio_path,
    pause_threshold=1.2,
    break_on_speaker_change=False,
    energy_sensitivity='high'
)

print("Loading JSON data...")
words = converter.load_json_data(json_path)

# Find original words around 3824-3826s
print("\n" + "="*70)
print("ORIGINAL WORDS (Before Energy Correction)")
print("="*70)

target_indices = []
for i, word in enumerate(words):
    if 3824.0 <= word.start <= 3826.0:
        print(f"[{i}] {word.start:.3f}-{word.end:.3f} ({word.end-word.start:.3f}s): \"{word.text}\"")
        target_indices.append(i)

# Apply energy corrections
print("\n" + "="*70)
print("APPLYING ENERGY CORRECTIONS...")
print("="*70)

corrected_words = converter.apply_energy_corrections(words)

# Find corrected words
print("\n" + "="*70)
print("CORRECTED WORDS (After Energy Correction)")
print("="*70)

for idx in target_indices:
    if idx < len(corrected_words):
        word = corrected_words[idx]
        print(f"[{idx}] {word.start:.3f}-{word.end:.3f} ({word.end-word.start:.3f}s): \"{word.text}\"")

# Check if words still exist
print("\n" + "="*70)
print("CHECKING SPECIFIC WORDS")
print("="*70)

target_texts = ['var', 'inne', 'i', 'bildet.']
for target in target_texts:
    found = False
    for idx in target_indices:
        if idx < len(corrected_words) and corrected_words[idx].text == target:
            word = corrected_words[idx]
            print(f"+ Found '{target}': {word.start:.3f}-{word.end:.3f} ({word.end-word.start:.3f}s)")
            found = True
            break

    if not found:
        print(f"- NOT FOUND: '{target}'")

# Check what happens during segment creation
print("\n" + "="*70)
print("CREATING SEGMENTS...")
print("="*70)

segments = converter.create_segments(corrected_words)

# Find which segment contains our target time
print(f"\nTotal segments created: {len(segments)}")
print("\nSearching for segments in 3822-3838s range (subtitle #516-517 area)...")

for i, seg in enumerate(segments):
    if seg.start_time <= 3838.0 and seg.end_time >= 3822.0:
        print(f"\nSegment {i+1}:")
        print(f"  Time: {seg.start_time:.3f}-{seg.end_time:.3f} ({seg.end_time-seg.start_time:.3f}s)")
        print(f"  Words: {len(seg.words)}")
        print(f"  First word: \"{seg.words[0].text}\" at {seg.words[0].start:.3f}")
        print(f"  Last word: \"{seg.words[-1].text}\" at {seg.words[-1].end:.3f}")

        # Check if our target words are in this segment
        segment_text = ' '.join(w.text for w in seg.words)
        print(f"  Full text: \"{segment_text}\"")

        contains = []
        for target in target_texts:
            if any(w.text == target for w in seg.words):
                contains.append(target)

        if contains:
            print(f"  >>> CONTAINS: {', '.join(contains)}")
