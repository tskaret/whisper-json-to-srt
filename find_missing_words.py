#!/usr/bin/env python3
"""
Find and analyze missing words between JSON and SRT output
"""

import json
import re
import sys
from dataclasses import dataclass
from typing import List, Set, Dict


@dataclass
class Word:
    text: str
    start: float
    end: float
    duration: float
    speaker: str
    index: int


def load_json_words(json_path: str) -> List[Word]:
    """Load all words from JSON with metadata"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    words = []
    word_index = 0

    for segment in data.get('segments', []):
        speaker = segment.get('speaker', 'UNKNOWN')
        for word_data in segment.get('words', []):
            text = word_data.get('word', '').strip()
            if not text:
                continue

            start = float(word_data.get('start', 0.0))
            end = float(word_data.get('end', 0.0))

            words.append(Word(
                text=text,
                start=start,
                end=end,
                duration=end - start,
                speaker=speaker,
                index=word_index
            ))
            word_index += 1

    return words


def load_srt_words(srt_path: str) -> Set[str]:
    """Load all words from SRT as a set (for membership testing)"""
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract only text lines
    lines = content.split('\n')
    text_lines = []

    for line in lines:
        line = line.strip()
        # Skip numbers, timestamps, empty lines
        if re.match(r'^\d+$', line) or '-->' in line or not line:
            continue
        text_lines.append(line)

    # Join and clean
    text_content = ' '.join(text_lines)
    text_content = re.sub(r'\[SPEAKER_\d+\]:\s*', '', text_content)

    # Extract words (excluding standalone hyphens)
    words = text_content.split()
    words = [w for w in words if w.strip() not in ['-', '–', '—']]

    return set(words)


def analyze_missing_words(json_path: str, srt_path: str):
    """Find and analyze missing words"""

    print("Loading JSON words...")
    json_words = load_json_words(json_path)

    print("Loading SRT words...")
    srt_word_set = load_srt_words(srt_path)

    print(f"\nTotal JSON words: {len(json_words)}")
    print(f"Total SRT words: {len(srt_word_set)}")

    # Find missing words
    missing_words = []
    for word in json_words:
        if word.text not in srt_word_set:
            missing_words.append(word)

    print(f"Missing words: {len(missing_words)}")

    if not missing_words:
        print("\n✅ No missing words found!")
        return

    # Analyze missing words by category
    print(f"\n{'='*70}")
    print("ANALYSIS OF MISSING WORDS")
    print(f"{'='*70}\n")

    # 1. Very short words (< 50ms)
    MIN_WORD_DURATION = 0.050
    very_short = [w for w in missing_words if w.duration < MIN_WORD_DURATION]

    print(f"1. VERY SHORT WORDS (duration < {MIN_WORD_DURATION}s = 50ms)")
    print(f"   Count: {len(very_short)}")
    print(f"   Reason: Below MIN_WORD_DURATION threshold\n")
    if very_short:
        print("   Examples (first 10):")
        for w in very_short[:10]:
            print(f"     [{w.index:5d}] {w.start:8.3f}s: \"{w.text}\" ({w.duration*1000:.1f}ms)")
        print()

    # 2. Invalid timing (end <= start)
    invalid_timing = [w for w in missing_words if w.duration <= 0]

    print(f"2. INVALID TIMING (end <= start)")
    print(f"   Count: {len(invalid_timing)}")
    print(f"   Reason: Corrupt timing data\n")
    if invalid_timing:
        print("   Examples:")
        for w in invalid_timing[:10]:
            print(f"     [{w.index:5d}] {w.start:.3f}-{w.end:.3f}: \"{w.text}\"")
        print()

    # 3. Single-character words
    single_char = [w for w in missing_words if len(w.text) == 1 and w.duration >= MIN_WORD_DURATION]

    print(f"3. SINGLE-CHARACTER WORDS (with valid duration)")
    print(f"   Count: {len(single_char)}")
    print(f"   Reason: May be filtered as noise or edge cases\n")
    if single_char:
        print("   Examples:")
        for w in single_char[:10]:
            print(f"     [{w.index:5d}] {w.start:8.3f}s: \"{w.text}\" ({w.duration*1000:.1f}ms)")
        print()

    # 4. Extremely long words (> 10s)
    extremely_long = [w for w in missing_words if w.duration > 10.0]

    print(f"4. EXTREMELY LONG WORDS (duration > 10s)")
    print(f"   Count: {len(extremely_long)}")
    print(f"   Reason: Anomalous timing, may be filtered by energy correction\n")
    if extremely_long:
        print("   Examples:")
        for w in extremely_long[:10]:
            print(f"     [{w.index:5d}] {w.start:8.3f}s: \"{w.text}\" ({w.duration:.1f}s)")
        print()

    # 5. Empty or whitespace words
    empty_words = [w for w in missing_words if not w.text.strip()]

    print(f"5. EMPTY/WHITESPACE WORDS")
    print(f"   Count: {len(empty_words)}")
    print(f"   Reason: No actual content\n")

    # 6. Other missing words
    other_missing = [w for w in missing_words
                     if w.duration >= MIN_WORD_DURATION
                     and w.duration <= 10.0
                     and len(w.text) > 1
                     and w.text.strip()]

    print(f"6. OTHER MISSING WORDS (valid duration, multi-char)")
    print(f"   Count: {len(other_missing)}")
    print(f"   Reason: UNEXPECTED - needs investigation\n")
    if other_missing:
        print("   WARNING: THESE SHOULD BE INVESTIGATED:")
        for w in other_missing[:20]:
            print(f"     [{w.index:5d}] {w.start:8.3f}-{w.end:8.3f}: \"{w.text}\" ({w.duration*1000:.0f}ms)")
        print()

    # Summary
    print(f"{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Very short words (< 50ms):        {len(very_short):5d} ({len(very_short)/len(missing_words)*100:.1f}%)")
    print(f"Invalid timing (end <= start):    {len(invalid_timing):5d} ({len(invalid_timing)/len(missing_words)*100:.1f}%)")
    print(f"Single-character words:           {len(single_char):5d} ({len(single_char)/len(missing_words)*100:.1f}%)")
    print(f"Extremely long words (> 10s):     {len(extremely_long):5d} ({len(extremely_long)/len(missing_words)*100:.1f}%)")
    print(f"Empty/whitespace words:           {len(empty_words):5d} ({len(empty_words)/len(missing_words)*100:.1f}%)")
    print(f"Other (unexpected):               {len(other_missing):5d} ({len(other_missing)/len(missing_words)*100:.1f}%)")
    print(f"{'='*70}")
    print(f"TOTAL MISSING:                    {len(missing_words):5d}")
    print(f"{'='*70}\n")

    # Expected vs unexpected
    expected_missing = len(very_short) + len(invalid_timing) + len(empty_words)
    unexpected_missing = len(missing_words) - expected_missing

    if unexpected_missing == 0:
        print("✅ All missing words are EXPECTED (filtered for valid reasons)")
    else:
        print(f"⚠️  {unexpected_missing} words are UNEXPECTEDLY missing - needs investigation")

    # Distribution by time
    print(f"\n{'='*70}")
    print("TEMPORAL DISTRIBUTION OF MISSING WORDS")
    print(f"{'='*70}\n")

    # Group by 5-minute intervals
    if missing_words:
        time_bins: Dict[int, int] = {}
        for w in missing_words:
            bin_minutes = int(w.start // 300)  # 5-minute bins
            time_bins[bin_minutes] = time_bins.get(bin_minutes, 0) + 1

        print("Missing words by 5-minute interval:")
        for bin_num in sorted(time_bins.keys())[:20]:  # Show first 20 bins
            start_min = bin_num * 5
            end_min = start_min + 5
            count = time_bins[bin_num]
            bar = '#' * min(count, 50)
            print(f"  {start_min:3d}-{end_min:3d} min: {count:3d} {bar}")

        if len(time_bins) > 20:
            print(f"  ... ({len(time_bins) - 20} more intervals)")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python find_missing_words.py <json_file> <srt_file>")
        sys.exit(1)

    analyze_missing_words(sys.argv[1], sys.argv[2])
