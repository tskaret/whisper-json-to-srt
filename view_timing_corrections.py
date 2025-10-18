#!/usr/bin/env python3
"""
View word timings with original and calculated (corrected) values from JSON transcript.

Usage:
    python view_timing_corrections.py input.json
    python view_timing_corrections.py input.json -s 01:02:03
    python view_timing_corrections.py input.json --start-time 00:30:00
    python view_timing_corrections.py input.json -s 01:02:03 -n 50
"""

import json
import re
import argparse
import sys


def count_vowel_groups(word: str) -> int:
    """Count vowel groups (syllable approximation) in a word"""
    clean_word = re.sub(r'[^\w]', '', word)
    vowel_groups = re.findall(r'[aeiouyæøå]+', clean_word.lower())
    return max(1, len(vowel_groups))


def estimate_typical_duration(word_text: str) -> float:
    """Estimate typical duration for a word based on syllable count and punctuation"""
    vowel_count = count_vowel_groups(word_text)

    punct_type = 'none'
    if word_text.strip().endswith(('.', '!', '?')):
        punct_type = 'hard'
    elif word_text.strip().endswith((',', ';', ':')):
        punct_type = 'soft'

    # Duration stats from actual data analysis
    stats = {
        1: {'none': 0.14, 'soft': 0.26, 'hard': 0.30},
        2: {'none': 0.30, 'soft': 0.42, 'hard': 0.42},
        3: {'none': 0.48, 'soft': 0.54, 'hard': 0.54},
        4: {'none': 0.60, 'soft': 0.71, 'hard': 0.70},
        5: {'none': 0.76, 'soft': 0.80, 'hard': 0.88},
        6: {'none': 0.90, 'soft': 0.98, 'hard': 1.08},
        7: {'hard': 1.48},
        8: {'none': 1.04},
    }

    if vowel_count in stats and punct_type in stats[vowel_count]:
        return stats[vowel_count][punct_type]

    # Fallback heuristic
    base = vowel_count * 0.2 + 0.1
    if punct_type == 'soft':
        base += 0.05
    elif punct_type == 'hard':
        base += 0.1
    return base


def apply_timing_correction(word_text: str, start: float, end: float,
                           position: str = 'middle',
                           correction_threshold: float = 3.0) -> tuple:
    """Apply timing correction logic

    Returns: (calc_start, calc_end, calc_duration, was_corrected)
    """
    original_duration = end - start
    typical_duration = estimate_typical_duration(word_text)

    # Check if correction needed
    if original_duration <= typical_duration * correction_threshold:
        return start, end, original_duration, False  # No correction

    # Apply position-based correction
    corrected = True
    if position == 'first':
        # First word: keep start time, adjust end
        corrected_end = start + typical_duration
        return start, corrected_end, typical_duration, corrected
    elif position == 'last':
        # Last word: handle hard punctuation specially
        if word_text.strip().endswith(('.', '!', '?')):
            corrected_end = start + typical_duration
            return start, corrected_end, typical_duration, corrected
        else:
            corrected_start = end - typical_duration
            return corrected_start, end, typical_duration, corrected
    else:
        # Middle word: center typical duration around midpoint
        midpoint = start + original_duration / 2
        corrected_start = midpoint - typical_duration / 2
        corrected_end = midpoint + typical_duration / 2
        return corrected_start, corrected_end, typical_duration, corrected


def parse_time(time_str: str) -> float:
    """Parse time string (HH:MM:SS) to seconds"""
    try:
        parts = time_str.split(':')
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        elif len(parts) == 2:
            m, s = parts
            return int(m) * 60 + float(s)
        else:
            return float(time_str)
    except (ValueError, IndexError) as e:
        print(f"❌ Error: Invalid time format '{time_str}'. Use HH:MM:SS or MM:SS or seconds")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='View word timings with original and calculated corrections',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python view_timing_corrections.py transcript.json
  python view_timing_corrections.py transcript.json -s 01:02:03
  python view_timing_corrections.py transcript.json --start-time 00:30:00 -n 50
  python view_timing_corrections.py transcript.json -s 125 -n 30
        """
    )

    parser.add_argument('json_file', help='Input JSON transcript file')
    parser.add_argument('-s', '--start-time', type=str, default='0',
                       help='Start time (HH:MM:SS, MM:SS, or seconds)')
    parser.add_argument('-n', '--num-words', type=int, default=30,
                       help='Number of words to display (default: 30)')
    parser.add_argument('--show-all-corrections', action='store_true',
                       help='Show all corrections instead of sequential words')

    args = parser.parse_args()

    # Parse start time
    start_seconds = parse_time(args.start_time)

    # Load JSON
    try:
        with open(args.json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: File not found: {args.json_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON format: {e}")
        sys.exit(1)

    # Print header with two-line column names
    print("=" * 110)
    print(f"{'Word':<20} {'Pos':<6} {'Syl':<4} {'Start':<24} {'End':<24} {'Duration':<20} {'Corr':<5}")
    print(f"{'':<20} {'':<6} {'':<4} {'Orig':<12}{'Calc':<12} {'Orig':<12}{'Calc':<12} {'Orig':<10}{'Calc':<10} {'':<5}")
    print("=" * 110)

    words_shown = 0
    corrections_shown = 0
    skipped_words = 0

    for segment_idx, segment in enumerate(data['segments']):
        words = segment.get('words', [])

        for word_idx, word_data in enumerate(words):
            word_text = word_data.get('word', '')
            orig_start = word_data.get('start', 0)
            orig_end = word_data.get('end', 0)
            orig_duration = orig_end - orig_start

            # Skip words before start time
            if orig_start < start_seconds:
                skipped_words += 1
                continue

            # Determine position
            position = 'middle'
            if word_idx == 0:
                position = 'first'
            elif word_idx == len(words) - 1:
                position = 'last'

            # Apply correction
            calc_start, calc_end, calc_duration, was_corrected = apply_timing_correction(
                word_text, orig_start, orig_end, position
            )

            # Filter based on mode
            if args.show_all_corrections:
                # Only show corrected words
                if not was_corrected:
                    continue
                if corrections_shown >= args.num_words:
                    break
            else:
                # Show sequential words
                if words_shown >= args.num_words:
                    break

            syllables = count_vowel_groups(word_text)
            corr_marker = "YES" if was_corrected else ""

            print(f"{word_text:<20} {position:<6} {syllables:<4} "
                  f"{orig_start:<12.3f} {calc_start:<12.3f} "
                  f"{orig_end:<12.3f} {calc_end:<12.3f} "
                  f"{orig_duration:<10.3f} {calc_duration:<10.3f} {corr_marker:<5}")

            if was_corrected:
                corrections_shown += 1
            words_shown += 1

        if (args.show_all_corrections and corrections_shown >= args.num_words) or \
           (not args.show_all_corrections and words_shown >= args.num_words):
            break

    print("=" * 110)
    print(f"\nSkipped {skipped_words} words before start time {args.start_time}")
    print(f"Displayed {words_shown} words")
    if corrections_shown > 0:
        print(f"Corrections shown: {corrections_shown}")


if __name__ == '__main__':
    main()
