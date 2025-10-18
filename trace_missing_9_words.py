#!/usr/bin/env python3
"""
Trace what happened to the 9 missing words during processing
"""

import sys
sys.path.insert(0, 'D:\\Kreativitet\\subtitle-processing-experiments')

from json_to_srt_energy import SRTConverter

# Setup
json_path = r'd:\stevner\2025\regionalt\Lørdag\04-LørdagEttermiddag\04-LørdagEttermiddag.json'
audio_path = r'd:\stevner\2025\regionalt\Lørdag\04-LørdagEttermiddag\04-LørdagEttermiddag.mp3'

missing_words = [
    ('nedfelt', 2356.045, 2356.766),
    ('lone', 2393.753, 2394.113),
    ('misfornøyd,', 3600.298, 3600.979),
    ('opphøylt,', 5554.389, 5554.932),
    ('skinte', 5555.172, 5555.614),
    ('gallerier.', 5556.558, 5557.562),
    ('tornebusker', 6996.763, 6997.644),
    ("'Fortsett", 7859.892, 7860.373),
    ('velsignelsene', 10492.894, 10493.735),
]

print("Creating converter...")
converter = SRTConverter(
    audio_path=audio_path,
    pause_threshold=1.2,
    max_chars_per_line=37,
    break_on_speaker_change=False,
    energy_sensitivity='high'
)

print("Loading JSON...")
words = converter.load_json_data(json_path)

print(f"\nOriginal word count: {len(words)}")
print("\nSearching for target words in ORIGINAL JSON...")

for target_text, target_start, target_end in missing_words:
    found = False
    for i, word in enumerate(words):
        if abs(word.start - target_start) < 0.1 and word.text.strip() == target_text.strip():
            print(f"\n[{i:5d}] FOUND: \"{word.text}\"")
            print(f"  Original: {word.start:.3f}-{word.end:.3f} ({word.end-word.start:.3f}s)")
            found = True
            break

    if not found:
        print(f"\nNOT FOUND: \"{target_text}\" near {target_start:.3f}s")

print("\n" + "="*70)
print("APPLYING ENERGY CORRECTION...")
print("="*70)

corrected_words = converter.apply_energy_corrections(words)

print(f"\nCorrected word count: {len(corrected_words)}")
print("\nSearching for target words in CORRECTED words...")

for target_text, target_start, target_end in missing_words:
    found = False
    # Search near original time AND anywhere in corrected list
    for i, word in enumerate(corrected_words):
        if word.text.strip() == target_text.strip():
            if abs(word.start - target_start) < 5.0:  # Within 5 seconds
                print(f"\n[{i:5d}] FOUND: \"{word.text}\"")
                print(f"  Original: {target_start:.3f}-{target_end:.3f}")
                print(f"  Corrected: {word.start:.3f}-{word.end:.3f} ({word.end-word.start:.3f}s)")
                print(f"  Shift: {word.start - target_start:+.3f}s")
                found = True
                break

    if not found:
        print(f"\nNOT FOUND: \"{target_text}\" (searched all corrected words)")

print("\n" + "="*70)
print("CHECKING IF WORDS EXIST ANYWHERE IN CORRECTED LIST...")
print("="*70)

for target_text, target_start, target_end in missing_words:
    matches = [i for i, w in enumerate(corrected_words) if w.text.strip() == target_text.strip()]

    if matches:
        print(f"\n\"{target_text}\" appears {len(matches)} time(s) in corrected words:")
        for idx in matches[:3]:  # Show first 3
            word = corrected_words[idx]
            print(f"  [{idx:5d}] at {word.start:.3f}-{word.end:.3f} ({word.end-word.start:.3f}s)")
    else:
        print(f"\n\"{target_text}\" - COMPLETELY MISSING from corrected words!")
