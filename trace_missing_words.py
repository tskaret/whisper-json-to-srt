#!/usr/bin/env python3
"""
Trace what happens to 'inne i bildet' words during processing
"""

import json
import sys

# Simulate the processing to see where words disappear

def load_words_from_json(json_path):
    """Load words from JSON"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    words = []
    for segment in data['segments']:
        speaker = segment.get('speaker', 'UNKNOWN')
        for word_data in segment.get('words', []):
            word_text = word_data.get('word', '').strip()
            if not word_text:
                continue

            start_time = float(word_data.get('start', 0.0))
            end_time = float(word_data.get('end', 0.0))

            if end_time <= start_time:
                print(f"SKIPPED (invalid timing): {word_text} {start_time}-{end_time}")
                continue

            words.append({
                'text': word_text,
                'start': start_time,
                'end': end_time,
                'speaker': speaker
            })

    return words


def find_words_in_range(words, start, end):
    """Find words in a time range"""
    return [w for w in words if start <= w['start'] <= end]


# Load all words
words = load_words_from_json('04-LørdagEttermiddag.json')
print(f"Total words loaded: {len(words)}\n")

# Find the problematic sequence
target_words = find_words_in_range(words, 3824.0, 3826.0)

print("Words in 3824-3826s range:")
for w in target_words:
    print(f"  {w['start']:.3f}-{w['end']:.3f} ({w['end']-w['start']:.3f}s): \"{w['text']}\"")

# Check if these words exist
target_texts = ['var', 'inne', 'i', 'bildet.']
print(f"\nSearching for target words: {target_texts}")

for target in target_texts:
    matches = [w for w in target_words if w['text'] == target]
    if matches:
        for m in matches:
            print(f"  FOUND: {target} at {m['start']:.3f}-{m['end']:.3f}")
    else:
        print(f"  NOT FOUND: {target}")

# Now simulate what happens after energy correction
# Let's assume energy correction extends "var" and see what happens

print(f"\n{'='*60}")
print("SIMULATING ENERGY CORRECTION")
print(f"{'='*60}\n")

# Simulate: energy correction might extend "var"
# Let's say it extends to where it finds the next big drop

# From the analysis, we know:
# - "var" ends at 3824.678
# - Energy stays high through "inne i bildet"
# - First big drop after "bildet." at 3825.199

print("Hypothesis: Energy detection extends 'var' to capture the energy drop")
print("If 'var' gets extended to 3825.199 (after 'bildet.'), then:")
print("  - Original 'var': 3824.538-3824.678 (0.140s)")
print("  - Extended 'var': 3824.538-3825.199 (0.661s)")
print("  - This would OVERLAP with 'inne', 'i', and 'bildet.'")

# Check for overlaps if var extended to 3825.199
hypothetical_var_end = 3825.199

print(f"\nChecking which words would overlap with extended 'var':")
for w in target_words:
    if w['text'] == 'var':
        continue

    # Check if this word would be inside the extended var boundary
    if w['start'] >= 3824.538 and w['start'] < hypothetical_var_end:
        print(f"  OVERLAP: '{w['text']}' ({w['start']:.3f}-{w['end']:.3f})")

# Now check what the overlap resolution would do
print(f"\n{'='*60}")
print("OVERLAP RESOLUTION (safety_gap=0.010s)")
print(f"{'='*60}\n")

# After overlap resolution, words get pushed forward
safety_gap = 0.010
min_word_duration = 0.050

simulated_words = []
for w in target_words[:]:
    new_word = w.copy()
    simulated_words.append(new_word)

# Simulate overlap resolution if var was extended
if simulated_words[0]['text'] != 'Jesus':
    print("ERROR: Expected first word to be 'Jesus'")
    sys.exit(1)

# Find var
var_idx = next(i for i, w in enumerate(simulated_words) if w['text'] == 'var')
print(f"Found 'var' at index {var_idx}")
print(f"Original: {simulated_words[var_idx]['start']:.3f}-{simulated_words[var_idx]['end']:.3f}")

# Extend it hypothetically
simulated_words[var_idx]['end'] = 3825.199
print(f"Extended: {simulated_words[var_idx]['start']:.3f}-{simulated_words[var_idx]['end']:.3f}\n")

# Now apply overlap resolution
print("Applying overlap resolution...")
for i in range(var_idx + 1, len(simulated_words)):
    prev_word = simulated_words[i - 1]
    curr_word = simulated_words[i]

    if curr_word['start'] < prev_word['end'] + safety_gap:
        old_start = curr_word['start']
        curr_word['start'] = prev_word['end'] + safety_gap

        if curr_word['end'] < curr_word['start'] + min_word_duration:
            old_end = curr_word['end']
            curr_word['end'] = curr_word['start'] + min_word_duration
            print(f"  '{curr_word['text']}': start {old_start:.3f} -> {curr_word['start']:.3f}, " +
                  f"end {old_end:.3f} -> {curr_word['end']:.3f}")
        else:
            print(f"  '{curr_word['text']}': start {old_start:.3f} -> {curr_word['start']:.3f}")

print("\nFinal timing after overlap resolution:")
for w in simulated_words[var_idx:var_idx+5]:
    duration = w['end'] - w['start']
    print(f"  {w['start']:.3f}-{w['end']:.3f} ({duration:.3f}s): \"{w['text']}\"")
