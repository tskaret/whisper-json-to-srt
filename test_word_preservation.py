#!/usr/bin/env python3
"""
MANDATORY WORD PRESERVATION TEST

This test MUST be run after ANY changes to:
- json_to_srt.py
- json_to_srt_fixed.py
- json_to_srt_energy.py
- Any text wrapping or segment splitting logic

Purpose: Verify that no words are silently lost during SRT generation.

Usage:
    python test_word_preservation.py <json_file> <srt_file>

Exit codes:
    0 = PASS (word preservation >= 99%)
    1 = FAIL (word preservation < 99%)
    2 = ERROR (invalid files or parameters)
"""

import json
import re
import sys
import os
from typing import Tuple


def count_json_words(json_path: str) -> int:
    """Count total words in JSON transcript"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        word_count = 0
        for segment in data.get('segments', []):
            words = segment.get('words', [])
            # Count words with valid text
            for word_data in words:
                word_text = word_data.get('word', '').strip()
                if word_text:  # Only count non-empty words
                    word_count += 1

        return word_count

    except Exception as e:
        print(f"ERROR reading JSON file: {e}")
        return -1


def count_srt_words(srt_path: str) -> int:
    """Count total words in SRT subtitle file"""
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse line by line to extract only text content
        lines = content.split('\n')
        text_lines = []

        for line in lines:
            line = line.strip()

            # Skip subtitle numbers (standalone numbers)
            if re.match(r'^\d+$', line):
                continue

            # Skip timestamps
            if '-->' in line:
                continue

            # Skip empty lines
            if not line:
                continue

            text_lines.append(line)

        # Join all text lines
        text_content = ' '.join(text_lines)

        # Remove speaker labels [SPEAKER_XX]:
        text_content = re.sub(r'\[SPEAKER_\d+\]:\s*', '', text_content)

        # Split into words
        words = text_content.split()

        # Filter out standalone hyphens (continuation markers)
        content_words = [w for w in words if w.strip() not in ['-', '–', '—']]

        return len(content_words)

    except Exception as e:
        print(f"ERROR reading SRT file: {e}")
        return -1


def test_word_preservation(json_path: str, srt_path: str, min_preservation: float = 99.0) -> Tuple[bool, dict]:
    """
    Test word preservation between JSON and SRT

    Args:
        json_path: Path to input JSON file
        srt_path: Path to output SRT file
        min_preservation: Minimum acceptable preservation percentage (default: 99%)

    Returns:
        (passed, stats_dict)
    """

    # Validate files exist
    if not os.path.exists(json_path):
        return False, {'error': f'JSON file not found: {json_path}'}

    if not os.path.exists(srt_path):
        return False, {'error': f'SRT file not found: {srt_path}'}

    # Count words
    json_words = count_json_words(json_path)
    srt_words = count_srt_words(srt_path)

    if json_words < 0 or srt_words < 0:
        return False, {'error': 'Failed to count words'}

    # Calculate statistics
    words_lost = json_words - srt_words
    preservation_pct = (srt_words / json_words * 100) if json_words > 0 else 0
    loss_pct = 100 - preservation_pct

    # Determine pass/fail
    passed = preservation_pct >= min_preservation

    stats = {
        'json_words': json_words,
        'srt_words': srt_words,
        'words_lost': words_lost,
        'preservation_pct': preservation_pct,
        'loss_pct': loss_pct,
        'min_required': min_preservation,
        'passed': passed
    }

    return passed, stats


def print_test_results(stats: dict, verbose: bool = True):
    """Print formatted test results"""

    if 'error' in stats:
        print(f"\n{'='*60}")
        print("❌ TEST ERROR")
        print(f"{'='*60}")
        print(f"Error: {stats['error']}")
        print(f"{'='*60}\n")
        return

    # Determine status symbol
    status = "✅ PASS" if stats['passed'] else "❌ FAIL"

    print(f"\n{'='*60}")
    print(f"WORD PRESERVATION TEST - {status}")
    print(f"{'='*60}")
    print(f"JSON words:           {stats['json_words']:,}")
    print(f"SRT words:            {stats['srt_words']:,}")
    print(f"Words lost:           {stats['words_lost']:,}")
    print(f"{'='*60}")
    print(f"Preservation rate:    {stats['preservation_pct']:.2f}%")
    print(f"Loss rate:            {stats['loss_pct']:.2f}%")
    print(f"Minimum required:     {stats['min_required']:.1f}%")
    print(f"{'='*60}")

    if stats['passed']:
        print(f"✅ TEST PASSED")
        print(f"Word preservation is acceptable (>={stats['min_required']:.1f}%)")
    else:
        print(f"❌ TEST FAILED")
        print(f"Word preservation is below threshold!")
        print(f"Expected: >= {stats['min_required']:.1f}%")
        print(f"Actual:   {stats['preservation_pct']:.2f}%")
        print(f"\nWARNING: {stats['words_lost']:,} words are missing from output!")

    print(f"{'='*60}\n")

    if verbose and not stats['passed']:
        print("DEBUGGING TIPS:")
        print("1. Check split_oversized_segment() for truncation detection")
        print("2. Verify wrap_text() isn't silently dropping words")
        print("3. Look for word filtering logic (duration, invalid timing)")
        print("4. Check overlap resolution isn't removing words")
        print("5. Run with --max-chars-per-line 50 to test if it's a wrapping issue")
        print()


def main():
    """Main test entry point"""

    if len(sys.argv) < 3:
        print(__doc__)
        print("\nERROR: Missing required arguments")
        print("\nUsage:")
        print(f"    python {os.path.basename(__file__)} <json_file> <srt_file>")
        print("\nExample:")
        print(f"    python {os.path.basename(__file__)} transcript.json output.srt")
        sys.exit(2)

    json_path = sys.argv[1]
    srt_path = sys.argv[2]

    # Optional: custom minimum preservation threshold
    min_preservation = 99.0
    if len(sys.argv) >= 4:
        try:
            min_preservation = float(sys.argv[3])
        except ValueError:
            print(f"WARNING: Invalid preservation threshold '{sys.argv[3]}', using default 99.0%")

    # Run test
    passed, stats = test_word_preservation(json_path, srt_path, min_preservation)

    # Print results
    print_test_results(stats, verbose=True)

    # Exit with appropriate code
    if 'error' in stats:
        sys.exit(2)  # Error
    elif passed:
        sys.exit(0)  # Pass
    else:
        sys.exit(1)  # Fail


if __name__ == '__main__':
    main()
