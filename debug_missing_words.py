#!/usr/bin/env python3
"""
Comprehensive diagnostic to find where words disappear during processing
"""

import json
import sys

# Simulate the entire pipeline step by step

def load_words():
    """Load original words"""
    with open('04-LørdagEttermiddag.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    words = []
    for segment in data['segments']:
        for word_data in segment.get('words', []):
            words.append({
                'text': word_data.get('word', '').strip(),
                'start': float(word_data.get('start', 0.0)),
                'end': float(word_data.get('end', 0.0)),
                'speaker': segment.get('speaker', 'UNKNOWN')
            })

    return words

# Load all words
all_words = load_words()

# Find our target words
target_range_start = 3824.0
target_range_end = 3826.0

print("="*70)
print("STEP 1: ORIGINAL WORDS FROM JSON")
print("="*70)

target_words = [w for w in all_words if target_range_start <= w['start'] <= target_range_end]
print(f"\nWords in range {target_range_start}-{target_range_end}s:")
for i, w in enumerate(target_words):
    print(f"  [{i}] {w['start']:.3f}-{w['end']:.3f} ({w['end']-w['start']:.3f}s): \"{w['text']}\"")

# Find indices in full list
target_indices = []
for tw in target_words:
    for i, w in enumerate(all_words):
        if w['start'] == tw['start'] and w['text'] == tw['text']:
            target_indices.append(i)
            break

print(f"\nIndices in full word list: {target_indices}")

# Check what's around them
print(f"\n\nWords BEFORE target range (3820-3824s):")
before_words = [w for w in all_words if 3820 <= w['start'] < target_range_start]
for w in before_words[-5:]:
    print(f"  {w['start']:.3f}-{w['end']:.3f}: \"{w['text']}\"")

print(f"\n\nWords AFTER target range (3826-3840s):")
after_words = [w for w in all_words if target_range_end < w['start'] <= 3840]
for w in after_words[:10]:
    print(f"  {w['start']:.3f}-{w['end']:.3f}: \"{w['text']}\"")

# Check word "i" specifically
print("\n" + "="*70)
print("CHECKING WORD 'i' (0.020s duration)")
print("="*70)

word_i = [w for w in target_words if w['text'] == 'i']
if word_i:
    w = word_i[0]
    print(f"Found: {w['start']:.3f}-{w['end']:.3f} ({w['end']-w['start']:.3f}s)")
    print(f"Duration: {(w['end']-w['start'])*1000:.1f}ms")
    print(f"This is BELOW MIN_WORD_DURATION (0.05s = 50ms)")
    print(f"But json_to_srt_energy.py doesn't filter based on duration at load time")
    print(f"So it SHOULD be loaded")
else:
    print("NOT FOUND in target range!")

# Now let's check the segment boundaries
print("\n" + "="*70)
print("STEP 2: SEGMENT BOUNDARIES")
print("="*70)

print("\nWith pause_threshold=1.2s, breaks occur when gap > 1.2s")
print("\nChecking gaps around our target words:")

for i in range(len(target_words) - 1):
    curr = target_words[i]
    next = target_words[i + 1]
    gap = next['start'] - curr['end']
    break_flag = " <<< BREAK!" if gap > 1.2 else ""
    print(f"  After \"{curr['text']}\": gap = {gap:.3f}s{break_flag}")

# Check gap to next word after target range
if target_words and after_words:
    last_target = target_words[-1]
    first_after = after_words[0]
    gap = first_after['start'] - last_target['end']
    break_flag = " <<< BREAK!" if gap > 1.2 else ""
    print(f"  After \"{last_target['text']}\" to \"{first_after['text']}\": gap = {gap:.3f}s{break_flag}")

# Check the full sequence to understand segment structure
print("\n" + "="*70)
print("STEP 3: FULL SEQUENCE 3822-3838s (subtitle #516-517 range)")
print("="*70)

full_sequence = [w for w in all_words if 3822 <= w['start'] <= 3838]
print(f"\nTotal words in range: {len(full_sequence)}")
print("\nShowing all words with gaps:")

for i in range(len(full_sequence)):
    w = full_sequence[i]
    print(f"{w['start']:7.3f}-{w['end']:7.3f} ({w['end']-w['start']:5.3f}s): \"{w['text']}\"", end='')

    if i < len(full_sequence) - 1:
        next_w = full_sequence[i + 1]
        gap = next_w['start'] - w['end']
        if gap > 1.2:
            print(f"  [GAP: {gap:.3f}s] <<< SEGMENT BREAK", end='')
        elif gap > 0.5:
            print(f"  [gap: {gap:.3f}s]", end='')

    print()

# Identify where segment breaks would occur
print("\n" + "="*70)
print("STEP 4: WHERE SEGMENT BREAKS OCCUR")
print("="*70)

breaks = []
for i in range(len(full_sequence) - 1):
    curr = full_sequence[i]
    next_w = full_sequence[i + 1]
    gap = next_w['start'] - curr['end']
    if gap > 1.2:
        breaks.append(i + 1)  # Break BEFORE next word
        print(f"Break {len(breaks)}: After \"{curr['text']}\" (index {i}), before \"{next_w['text']}\" (gap={gap:.3f}s)")

print(f"\nTotal breaks: {len(breaks)}")
print(f"This creates {len(breaks) + 1} segments")

# Show which words belong to which segment
print("\n" + "="*70)
print("STEP 5: WORDS BY SEGMENT")
print("="*70)

all_breaks = [0] + breaks + [len(full_sequence)]
for seg_num in range(len(all_breaks) - 1):
    start_idx = all_breaks[seg_num]
    end_idx = all_breaks[seg_num + 1]

    segment_words = full_sequence[start_idx:end_idx]
    if not segment_words:
        continue

    seg_start = segment_words[0]['start']
    seg_end = segment_words[-1]['end']
    seg_duration = seg_end - seg_start
    word_count = len(segment_words)

    print(f"\nSegment {seg_num + 1}:")
    print(f"  Timing: {seg_start:.3f}-{seg_end:.3f} ({seg_duration:.3f}s)")
    print(f"  Words: {word_count}")
    print(f"  Text preview: \"{' '.join(w['text'] for w in segment_words[:10])}{'...' if word_count > 10 else ''}\"")

    # Check if this segment contains our target words
    contains_var = any(w['text'] == 'var' for w in segment_words)
    contains_inne = any(w['text'] == 'inne' for w in segment_words)
    contains_bildet = any(w['text'] == 'bildet.' for w in segment_words)

    if contains_var or contains_inne or contains_bildet:
        print(f"  >>> CONTAINS TARGET WORDS: var={contains_var}, inne={contains_inne}, bildet={contains_bildet}")
        print(f"  All words in segment:")
        for w in segment_words:
            marker = " <<<" if w['text'] in ['var', 'inne', 'i', 'bildet.'] else ""
            print(f"    {w['start']:.3f}-{w['end']:.3f}: \"{w['text']}\"{marker}")

print("\n" + "="*70)
print("ANALYSIS COMPLETE")
print("="*70)
