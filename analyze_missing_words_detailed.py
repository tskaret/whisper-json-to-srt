#!/usr/bin/env python3
"""
Detailed analysis of missing words between JSON and SRT
Handles punctuation and word forms correctly
"""

import json
import re
import sys
from typing import List, Tuple


def load_json_words_sequence(json_path: str) -> List[Tuple[int, str, float, float]]:
    """Load words as ordered sequence: (index, text, start, end)"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    words = []
    idx = 0

    for segment in data.get('segments', []):
        for word_data in segment.get('words', []):
            text = word_data.get('word', '').strip()
            if text:
                start = float(word_data.get('start', 0.0))
                end = float(word_data.get('end', 0.0))
                words.append((idx, text, start, end))
                idx += 1

    return words


def load_srt_words_sequence(srt_path: str) -> List[str]:
    """Load words from SRT as ordered sequence"""
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    text_lines = []

    for line in lines:
        line = line.strip()
        # Skip numbers, timestamps, empty
        if re.match(r'^\d+$', line) or '-->' in line or not line:
            continue
        text_lines.append(line)

    # Join all text
    text = ' '.join(text_lines)

    # Remove speaker labels
    text = re.sub(r'\[SPEAKER_\d+\]:\s*', '', text)

    # Split into words (keep punctuation attached)
    words = text.split()

    # Filter standalone hyphens
    words = [w for w in words if w not in ['-', '–', '—']]

    return words


def normalize_word(word: str) -> str:
    """Normalize word for comparison (remove punctuation)"""
    # Remove leading/trailing punctuation
    word = word.strip('.,!?;:-"\'()[]{}')
    return word.lower()


def find_missing_words_detailed(json_path: str, srt_path: str):
    """Find missing words with detailed analysis"""

    print("Loading JSON words...")
    json_words = load_json_words_sequence(json_path)

    print("Loading SRT words...")
    srt_words = load_srt_words_sequence(srt_path)

    print(f"\nJSON words: {len(json_words)}")
    print(f"SRT words:  {len(srt_words)}")

    # Create lookup set of normalized SRT words
    srt_normalized = set(normalize_word(w) for w in srt_words)

    # Find missing
    missing = []
    for idx, text, start, end in json_words:
        normalized = normalize_word(text)
        if normalized and normalized not in srt_normalized:
            duration = end - start
            missing.append((idx, text, start, end, duration))

    print(f"Missing:    {len(missing)} ({len(missing)/len(json_words)*100:.2f}%)")

    if not missing:
        print("\nNo missing words!")
        return

    # Analyze categories
    print(f"\n{'='*70}")
    print("MISSING WORDS ANALYSIS")
    print(f"{'='*70}\n")

    MIN_DURATION = 0.050  # 50ms

    # 1. Very short (< 50ms)
    very_short = [w for w in missing if w[4] < MIN_DURATION]
    print(f"1. VERY SHORT DURATION (< {MIN_DURATION}s = 50ms)")
    print(f"   Count: {len(very_short)} ({len(very_short)/len(missing)*100:.1f}% of missing)")
    print(f"   Reason: Below MIN_WORD_DURATION threshold in code")
    if very_short:
        print(f"   Examples:")
        for idx, text, start, end, dur in very_short[:10]:
            print(f"     [{idx:5d}] {start:8.3f}s: \"{text}\" ({dur*1000:.1f}ms)")
    print()

    # 2. Invalid timing
    invalid = [w for w in missing if w[4] <= 0]
    print(f"2. INVALID TIMING (duration <= 0)")
    print(f"   Count: {len(invalid)} ({len(invalid)/len(missing)*100:.1f}% of missing)")
    print(f"   Reason: Corrupted timestamp data")
    if invalid:
        print(f"   Examples:")
        for idx, text, start, end, dur in invalid[:5]:
            print(f"     [{idx:5d}] {start:.3f}-{end:.3f}: \"{text}\"")
    print()

    # 3. Single character
    single_char = [w for w in missing if len(normalize_word(w[1])) == 1 and w[4] >= MIN_DURATION]
    print(f"3. SINGLE CHARACTER (normalized, valid duration)")
    print(f"   Count: {len(single_char)} ({len(single_char)/len(missing)*100:.1f}% of missing)")
    print(f"   Reason: Filtered as noise or continuation markers")
    if single_char:
        print(f"   Examples:")
        for idx, text, start, end, dur in single_char[:10]:
            print(f"     [{idx:5d}] {start:8.3f}s: \"{text}\" (normalized: \"{normalize_word(text)}\", {dur*1000:.0f}ms)")
    print()

    # 4. Extremely long
    very_long = [w for w in missing if w[4] > 5.0]
    print(f"4. EXTREMELY LONG DURATION (> 5s)")
    print(f"   Count: {len(very_long)} ({len(very_long)/len(missing)*100:.1f}% of missing)")
    print(f"   Reason: Anomalous timing, corrected/filtered by energy detection")
    if very_long:
        print(f"   Examples:")
        for idx, text, start, end, dur in very_long[:5]:
            print(f"     [{idx:5d}] {start:8.3f}s: \"{text}\" ({dur:.2f}s)")
    print()

    # 5. Reasonable words (should be investigated)
    reasonable = [w for w in missing
                  if w[4] >= MIN_DURATION
                  and w[4] <= 5.0
                  and len(normalize_word(w[1])) > 1]

    print(f"5. REASONABLE WORDS (valid duration, multi-char)")
    print(f"   Count: {len(reasonable)} ({len(reasonable)/len(missing)*100:.1f}% of missing)")
    print(f"   Reason: UNEXPECTED - needs investigation!")
    if reasonable:
        print(f"   WARNING: These should be in the output:")
        for idx, text, start, end, dur in reasonable[:20]:
            print(f"     [{idx:5d}] {start:8.3f}-{end:8.3f}s: \"{text}\" ({dur*1000:.0f}ms)")
    print()

    # Summary
    print(f"{'='*70}")
    print("SUMMARY BY CATEGORY")
    print(f"{'='*70}")
    total = len(missing)
    print(f"Very short (< 50ms):     {len(very_short):4d} ({len(very_short)/total*100:5.1f}%)")
    print(f"Invalid timing:          {len(invalid):4d} ({len(invalid)/total*100:5.1f}%)")
    print(f"Single character:        {len(single_char):4d} ({len(single_char)/total*100:5.1f}%)")
    print(f"Extremely long (> 5s):   {len(very_long):4d} ({len(very_long)/total*100:5.1f}%)")
    print(f"Reasonable (unexpected): {len(reasonable):4d} ({len(reasonable)/total*100:5.1f}%)")
    print(f"{'='*70}")
    print(f"TOTAL MISSING:           {total:4d}")
    print(f"{'='*70}\n")

    # Verdict
    expected = len(very_short) + len(invalid) + len(single_char) + len(very_long)
    print(f"Expected missing (filtered for valid reasons): {expected}")
    print(f"Unexpected missing (potential bugs):           {len(reasonable)}")

    if len(reasonable) == 0:
        print("\n*** All missing words are EXPECTED (legitimately filtered) ***")
    else:
        print(f"\n*** WARNING: {len(reasonable)} words unexpectedly missing - investigate! ***")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python analyze_missing_words_detailed.py <json_file> <srt_file>")
        sys.exit(1)

    find_missing_words_detailed(sys.argv[1], sys.argv[2])
