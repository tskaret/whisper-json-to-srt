#!/usr/bin/env python3
"""
Test sustained pause detection on "søstre." case
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

print("\nLoading JSON to find 'søstre.'...")
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Find "søstre." word
sostre_word = None
for segment in data['segments']:
    for word_data in segment.get('words', []):
        text = word_data.get('word', '').strip()
        if 'søstre' in text.lower() and text.endswith('.'):
            sostre_word = Word(
                text=text,
                start=float(word_data['start']),
                end=float(word_data['end']),
                speaker=segment.get('speaker', 'UNKNOWN'),
                score=float(word_data.get('score', 1.0)),
                original_start=float(word_data['start']),
                original_end=float(word_data['end'])
            )
            break
    if sostre_word:
        break

if not sostre_word:
    print("ERROR: Could not find 'søstre.' in JSON")
    sys.exit(1)

print(f"\nFound word: '{sostre_word.text}'")
print(f"Original timing: {sostre_word.original_start:.3f}s -> {sostre_word.original_end:.3f}s")
print(f"Original duration: {sostre_word.original_end - sostre_word.original_start:.3f}s")
print(f"Syllables: {sostre_word.count_syllables()}")

# Test WITHOUT sustained pause detection (is_last_before_punct=False)
print("\n" + "="*70)
print("TEST 1: Normal energy drop detection (old method)")
print("="*70)
corrected_normal = corrector.correct_word_timing(sostre_word, sensitivity='high', is_last_before_punct=False)
print(f"Corrected timing: {corrected_normal.start:.3f}s -> {corrected_normal.end:.3f}s")
print(f"Corrected duration: {corrected_normal.end - corrected_normal.start:.3f}s")
print(f"Adjustment magnitude: {corrected_normal.adjustment_magnitude*1000:.1f}ms")
print(f"Adjustment reason: {corrected_normal.adjustment_reason}")

# Reset the word
sostre_word.start = sostre_word.original_start
sostre_word.end = sostre_word.original_end

# Test WITH sustained pause detection (is_last_before_punct=True)
print("\n" + "="*70)
print("TEST 2: Sustained pause detection (new method)")
print("="*70)
corrected_sustained = corrector.correct_word_timing(sostre_word, sensitivity='high', is_last_before_punct=True)
print(f"Corrected timing: {corrected_sustained.start:.3f}s -> {corrected_sustained.end:.3f}s")
print(f"Corrected duration: {corrected_sustained.end - corrected_sustained.start:.3f}s")
print(f"Adjustment magnitude: {corrected_sustained.adjustment_magnitude*1000:.1f}ms")
print(f"Adjustment reason: {corrected_sustained.adjustment_reason}")

print("\n" + "="*70)
print("COMPARISON")
print("="*70)
print(f"Original:              {sostre_word.original_start:.3f}s -> {sostre_word.original_end:.3f}s ({sostre_word.original_end - sostre_word.original_start:.3f}s)")
print(f"Energy drop (old):     {corrected_normal.start:.3f}s -> {corrected_normal.end:.3f}s ({corrected_normal.end - corrected_normal.start:.3f}s)")
print(f"Sustained pause (new): {corrected_sustained.start:.3f}s -> {corrected_sustained.end:.3f}s ({corrected_sustained.end - corrected_sustained.start:.3f}s)")

print("\n" + "="*70)
print("EVALUATION")
print("="*70)

# Expected: Start at 2.314s, end around 2.6-2.7s
expected_start = 2.314
expected_end_min = 2.6
expected_end_max = 2.8

print(f"Expected start: ~{expected_start}s")
print(f"Expected end: ~{expected_end_min}s - {expected_end_max}s")
print()

# Check old method
old_start_ok = abs(corrected_normal.start - expected_start) < 0.5
old_end_ok = expected_end_min <= corrected_normal.end <= expected_end_max
print(f"Energy drop (old):")
print(f"  Start correct: {'YES' if old_start_ok else 'NO'} (off by {abs(corrected_normal.start - expected_start):.3f}s)")
print(f"  End correct: {'YES' if old_end_ok else 'NO'} (off by {abs(corrected_normal.end - expected_end_min):.3f}s)")

# Check new method
new_start_ok = abs(corrected_sustained.start - expected_start) < 0.1
new_end_ok = expected_end_min <= corrected_sustained.end <= expected_end_max
print(f"\nSustained pause (new):")
print(f"  Start correct: {'YES' if new_start_ok else 'NO'} (off by {abs(corrected_sustained.start - expected_start):.3f}s)")
print(f"  End correct: {'YES' if new_end_ok else 'NO'} (off by {min(abs(corrected_sustained.end - expected_end_min), abs(corrected_sustained.end - expected_end_max)):.3f}s)")

if new_start_ok and new_end_ok:
    print("\n" + "="*70)
    print("SUCCESS: Sustained pause detection correctly identifies word boundaries!")
    print("="*70)
else:
    print("\n" + "="*70)
    print("ISSUE: Timing still not optimal")
    print("="*70)
