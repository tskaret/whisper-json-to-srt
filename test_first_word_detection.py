#!/usr/bin/env python3
"""
Test first word detection (sustained energy rise)
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

print("\nLoading JSON to find first word 'God'...")
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Find "God" (first word)
god_word = None
for segment in data['segments']:
    for word_data in segment.get('words', []):
        text = word_data.get('word', '').strip()
        if text.lower() == 'god':
            god_word = Word(
                text=text,
                start=float(word_data['start']),
                end=float(word_data['end']),
                speaker=segment.get('speaker', 'UNKNOWN'),
                score=float(word_data.get('score', 1.0)),
                original_start=float(word_data['start']),
                original_end=float(word_data['end'])
            )
            break
    if god_word:
        break

if not god_word:
    print("ERROR: Could not find 'God' in JSON")
    sys.exit(1)

print(f"\nFound word: '{god_word.text}'")
print(f"Original timing: {god_word.original_start:.3f}s -> {god_word.original_end:.3f}s")
print(f"Original duration: {god_word.original_end - god_word.original_start:.3f}s")
print(f"Syllables: {god_word.count_syllables()}")

# Test WITHOUT first word detection (is_first_in_sentence=False)
print("\n" + "="*70)
print("TEST 1: Regular detection (NOT marked as first word)")
print("="*70)
corrected_regular = corrector.correct_word_timing(god_word, sensitivity='high',
                                                   is_last_before_punct=False,
                                                   is_first_in_sentence=False)
print(f"Corrected timing: {corrected_regular.start:.3f}s -> {corrected_regular.end:.3f}s")
print(f"Corrected duration: {corrected_regular.end - corrected_regular.start:.3f}s")
print(f"Adjustment magnitude: {corrected_regular.adjustment_magnitude*1000:.1f}ms")
print(f"Adjustment reason: {corrected_regular.adjustment_reason}")

# Reset the word
god_word.start = god_word.original_start
god_word.end = god_word.original_end

# Test WITH first word detection (is_first_in_sentence=True)
print("\n" + "="*70)
print("TEST 2: First word detection (IS marked as first word)")
print("="*70)
corrected_first = corrector.correct_word_timing(god_word, sensitivity='high',
                                                is_last_before_punct=False,
                                                is_first_in_sentence=True)
print(f"Corrected timing: {corrected_first.start:.3f}s -> {corrected_first.end:.3f}s")
print(f"Corrected duration: {corrected_first.end - corrected_first.start:.3f}s")
print(f"Adjustment magnitude: {corrected_first.adjustment_magnitude*1000:.1f}ms")
print(f"Adjustment reason: {corrected_first.adjustment_reason}")

print("\n" + "="*70)
print("COMPARISON")
print("="*70)
print(f"Original:           {god_word.original_start:.3f}s -> {god_word.original_end:.3f}s ({god_word.original_end - god_word.original_start:.3f}s)")
print(f"Regular detection:  {corrected_regular.start:.3f}s -> {corrected_regular.end:.3f}s ({corrected_regular.end - corrected_regular.start:.3f}s)")
print(f"First word (new):   {corrected_first.start:.3f}s -> {corrected_first.end:.3f}s ({corrected_first.end - corrected_first.start:.3f}s)")

print("\n" + "="*70)
print("EVALUATION")
print("="*70)

# Expected: Keep original END at 0.291s (or close), find earlier START
expected_end = 0.291
expected_start_max = 0.100  # Should start before 0.1s (before original 0.031s or around it)

print(f"Expected end: ~{expected_end}s (original end, validated)")
print(f"Expected start: Earlier than original if pre-speech silence detected")
print()

# Check regular detection
reg_end_ok = abs(corrected_regular.end - expected_end) < 0.1
print(f"Regular detection:")
print(f"  End: {corrected_regular.end:.3f}s ({'GOOD' if reg_end_ok else 'OFF'})")
print(f"  Uses validated start approach: {'YES' if 'Validated start' in corrected_regular.adjustment_reason else 'NO'}")

# Check first word detection
first_end_ok = abs(corrected_first.end - expected_end) < 0.1
first_start_reasonable = corrected_first.start <= god_word.original_start + 0.05  # Within 50ms or earlier
print(f"\nFirst word detection (new):")
print(f"  End: {corrected_first.end:.3f}s ({'GOOD' if first_end_ok else 'OFF'} - should keep original)")
print(f"  Start: {corrected_first.start:.3f}s ({'GOOD' if first_start_reasonable else 'OFF'} - should find energy rise)")
print(f"  Uses sustained energy rise: {'YES' if 'Sustained energy rise' in corrected_first.adjustment_reason else 'NO'}")

if first_end_ok and 'Sustained energy rise' in corrected_first.adjustment_reason:
    print("\n" + "="*70)
    print("SUCCESS: First word detection finds energy rise and keeps end!")
    print("="*70)
else:
    print("\n" + "="*70)
    print("INFO: First word detection behavior")
    print("="*70)
