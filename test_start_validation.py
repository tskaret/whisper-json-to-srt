#!/usr/bin/env python3
"""
Test start validation for ALL words
"""

import json
import sys
sys.path.insert(0, '.')

from json_to_srt_energy import EnergyDropCorrector, Word

# Load audio and JSON
audio_path = r'd:\stevner\2025\regionalt\Lørdag\04-LørdagEttermiddag\04-LørdagEttermiddag.mp3'
json_path = r'd:\stevner\2025\regionalt\Lørdag\04-LørdagEttermiddag\04-LørdagEttermiddag.json'

print("Loading audio...")
corrector = EnergyDropCorrector(audio_path)

print("\nLoading JSON...")
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Find test words
test_words = []

# 1. Find "God" (first word)
# 2. Find "søstre." (last word before punct)
for segment in data['segments']:
    for word_data in segment.get('words', []):
        text = word_data.get('word', '').strip()

        if text.lower() == 'god':
            test_words.append(('God', Word(
                text=text,
                start=float(word_data['start']),
                end=float(word_data['end']),
                speaker=segment.get('speaker', 'UNKNOWN'),
                score=float(word_data.get('score', 1.0)),
                original_start=float(word_data['start']),
                original_end=float(word_data['end'])
            )))

        if 'søstre' in text.lower() and text.endswith('.'):
            test_words.append(('søstre.', Word(
                text=text,
                start=float(word_data['start']),
                end=float(word_data['end']),
                speaker=segment.get('speaker', 'UNKNOWN'),
                score=float(word_data.get('score', 1.0)),
                original_start=float(word_data['start']),
                original_end=float(word_data['end'])
            )))

if len(test_words) < 2:
    print("ERROR: Could not find test words")
    sys.exit(1)

print(f"\nFound {len(test_words)} test words")

# Test each word
for name, word in test_words:
    print("\n" + "="*70)
    print(f"TEST: {name}")
    print("="*70)

    print(f"Original timing: {word.original_start:.3f}s -> {word.original_end:.3f}s")
    print(f"Original duration: {word.original_end - word.original_start:.3f}s")
    print(f"Syllables: {word.count_syllables()}")

    # Determine if last before punctuation
    is_last_before_punct = word.text.strip().endswith(('.', '!', '?'))
    print(f"Last before punctuation: {is_last_before_punct}")

    # Apply correction
    corrected = corrector.correct_word_timing(word, sensitivity='high', is_last_before_punct=is_last_before_punct)

    print(f"\nCorrected timing: {corrected.start:.3f}s -> {corrected.end:.3f}s")
    print(f"Corrected duration: {corrected.end - corrected.start:.3f}s")
    print(f"Adjustment magnitude: {corrected.adjustment_magnitude*1000:.1f}ms")
    print(f"Adjustment reason: {corrected.adjustment_reason}")

    # Evaluate
    if name == 'God':
        # Expected: Keep start at 0.031s (or very close)
        expected_start = 0.031
        start_ok = abs(corrected.start - expected_start) < 0.1

        print(f"\nExpected start: ~{expected_start}s")
        print(f"Start correct: {'YES' if start_ok else 'NO'} (off by {abs(corrected.start - expected_start):.3f}s)")

        if start_ok:
            print("\n" + "="*70)
            print("SUCCESS: Start validation working - kept original 0.031s!")
            print("="*70)
        else:
            print("\n" + "="*70)
            print("ISSUE: Start moved away from original")
            print("="*70)

    elif name == 'søstre.':
        # Expected: Start at 2.314s, end around 2.6-2.7s
        expected_start = 2.314
        expected_end_min = 2.6
        expected_end_max = 2.8

        start_ok = abs(corrected.start - expected_start) < 0.1
        end_ok = expected_end_min <= corrected.end <= expected_end_max

        print(f"\nExpected start: ~{expected_start}s")
        print(f"Expected end: ~{expected_end_min}s - {expected_end_max}s")
        print(f"Start correct: {'YES' if start_ok else 'NO'} (off by {abs(corrected.start - expected_start):.3f}s)")
        print(f"End correct: {'YES' if end_ok else 'NO'} (off by {min(abs(corrected.end - expected_end_min), abs(corrected.end - expected_end_max)):.3f}s)")

        if start_ok and end_ok:
            print("\n" + "="*70)
            print("SUCCESS: Sustained pause detection working perfectly!")
            print("="*70)
        else:
            print("\n" + "="*70)
            print("ISSUE: Timing not as expected")
            print("="*70)

print("\n" + "="*70)
print("OVERALL SUMMARY")
print("="*70)
print("Both words should have:")
print("  - Original START preserved (energy validated)")
print("  - Corrected END (sustained pause for 'søstre.', energy drop for 'God')")
