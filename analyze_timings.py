#!/usr/bin/env python3
"""
Word Length and Duration Statistics Analyzer
=============================================

Analyzes words from JSON transcription files, grouping by character count
and calculating average durations based on punctuation type.

Groups words by:
- Character count (exact count)
- Punctuation type: none, soft (,;:), hard (.!?)

Outputs statistics per character count group.
"""

import json
import sys
import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict
import statistics


@dataclass
class WordData:
    """Individual word data"""
    text: str
    char_count: int
    duration: float
    punctuation_type: str  # 'none', 'soft', 'hard'
    position: str
    start_time: float
    end_time: float


def classify_punctuation(word: str) -> str:
    """Classify word by punctuation type"""
    word = word.strip()
    if not word:
        return 'none'

    # Hard punctuation: . ! ?
    if word.endswith(('.', '!', '?')):
        return 'hard'

    # Soft punctuation: , ; :
    if word.endswith((',', ';', ':')):
        return 'soft'

    return 'none'


def get_char_count(word: str) -> int:
    """Get character count excluding punctuation"""
    clean_word = re.sub(r'[^\w]', '', word)
    return len(clean_word)


def load_json_data(file_path: str) -> Dict[str, Any]:
    """Load JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: File not found: {file_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON format: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        sys.exit(1)


def analyze_words_by_length(data: Dict[str, Any]) -> Dict[int, Dict[str, List[float]]]:
    """Analyze words grouped by character count and punctuation type

    Returns:
        Dict with structure:
        {
            char_count: {
                'none': [duration1, duration2, ...],
                'soft': [duration1, duration2, ...],
                'hard': [duration1, duration2, ...]
            }
        }
    """

    # Structure: char_count -> punctuation_type -> list of durations
    word_groups = defaultdict(lambda: {'none': [], 'soft': [], 'hard': []})

    segments = data.get('segments', [])
    total_words = 0
    skipped_words = 0

    for segment in segments:
        words = segment.get('words', [])
        if not words:
            continue

        for word_idx, word_data in enumerate(words):
            if not isinstance(word_data, dict):
                continue

            word_text = word_data.get('word', '').strip()
            if not word_text:
                skipped_words += 1
                continue

            try:
                start_time = float(word_data.get('start', 0.0))
                end_time = float(word_data.get('end', 0.0))
                duration = end_time - start_time
            except (ValueError, TypeError):
                skipped_words += 1
                continue

            # Skip invalid durations
            if duration <= 0 or duration > 30.0:  # Max 30s per word is reasonable
                skipped_words += 1
                continue

            # Get character count (without punctuation)
            char_count = get_char_count(word_text)
            if char_count == 0:
                skipped_words += 1
                continue

            # Classify punctuation
            punct_type = classify_punctuation(word_text)

            # Add to appropriate group
            word_groups[char_count][punct_type].append(duration)
            total_words += 1

    return dict(word_groups)


def calculate_statistics(durations: List[float]) -> Dict[str, float]:
    """Calculate statistics for a list of durations"""
    if not durations:
        return {
            'count': 0,
            'min': 0.0,
            'max': 0.0,
            'avg': 0.0,
            'median': 0.0,
            'std': 0.0
        }

    return {
        'count': len(durations),
        'min': min(durations),
        'max': max(durations),
        'avg': statistics.mean(durations),
        'median': statistics.median(durations),
        'std': statistics.stdev(durations) if len(durations) > 1 else 0.0
    }


def print_statistics_table(word_groups: Dict[int, Dict[str, List[float]]]):
    """Print simple statistics table - only averages by character count and punctuation"""

    # Header
    print(f"chars | no punct | soft punct | hard punct")
    print("-" * 50)

    # Sort by character count
    sorted_chars = sorted(word_groups.keys())

    for char_count in sorted_chars:
        punct_groups = word_groups[char_count]

        # Calculate statistics for each punctuation type
        none_stats = calculate_statistics(punct_groups['none'])
        soft_stats = calculate_statistics(punct_groups['soft'])
        hard_stats = calculate_statistics(punct_groups['hard'])

        # Format averages (show dash if no data)
        none_avg = f"{none_stats['avg']:.2f}" if none_stats['count'] > 0 else "-"
        soft_avg = f"{soft_stats['avg']:.2f}" if soft_stats['count'] > 0 else "-"
        hard_avg = f"{hard_stats['avg']:.2f}" if hard_stats['count'] > 0 else "-"

        # Format row
        print(f"{char_count:<5} | {none_avg:<10} | {soft_avg:<11} | {hard_avg:<11}")

    print("-" * 50)


def print_summary_statistics(word_groups: Dict[int, Dict[str, List[float]]]):
    """Print overall summary statistics"""

    print(f"📊 SUMMARY STATISTICS")
    print(f"{'='*60}")

    # Collect all durations by punctuation type
    all_none = []
    all_soft = []
    all_hard = []

    for punct_groups in word_groups.values():
        all_none.extend(punct_groups['none'])
        all_soft.extend(punct_groups['soft'])
        all_hard.extend(punct_groups['hard'])

    total_words = len(all_none) + len(all_soft) + len(all_hard)

    print(f"Total words analyzed: {total_words:,}")
    print(f"Character count range: {min(word_groups.keys())} - {max(word_groups.keys())} characters")
    print()

    # Overall statistics by punctuation type
    print(f"{'Punctuation Type':<20} {'Count':<10} {'Avg Duration':<15} {'Median Duration':<15}")
    print("-" * 60)

    if all_none:
        print(f"{'No punctuation':<20} {len(all_none):<10,} {statistics.mean(all_none):<15.3f} {statistics.median(all_none):<15.3f}")

    if all_soft:
        print(f"{'Soft (,:;)':<20} {len(all_soft):<10,} {statistics.mean(all_soft):<15.3f} {statistics.median(all_soft):<15.3f}")

    if all_hard:
        print(f"{'Hard (.!?)':<20} {len(all_hard):<10,} {statistics.mean(all_hard):<15.3f} {statistics.median(all_hard):<15.3f}")

    print()

    # Insights
    print(f"💡 KEY INSIGHTS:")
    if all_soft and all_none:
        soft_avg = statistics.mean(all_soft)
        none_avg = statistics.mean(all_none)
        diff = soft_avg - none_avg
        print(f"   • Words with soft punctuation are {diff:+.3f}s {'longer' if diff > 0 else 'shorter'} on average")

    if all_hard and all_none:
        hard_avg = statistics.mean(all_hard)
        none_avg = statistics.mean(all_none)
        diff = hard_avg - none_avg
        print(f"   • Words with hard punctuation are {diff:+.3f}s {'longer' if diff > 0 else 'shorter'} on average")

    print()


def export_to_csv(word_groups: Dict[int, Dict[str, List[float]]], output_file: str):
    """Export statistics to CSV file"""

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # Header
            f.write("char_count,punct_type,word_count,avg_duration,median_duration,min_duration,max_duration,std_duration\n")

            # Data rows
            sorted_chars = sorted(word_groups.keys())
            for char_count in sorted_chars:
                punct_groups = word_groups[char_count]

                for punct_type in ['none', 'soft', 'hard']:
                    stats = calculate_statistics(punct_groups[punct_type])
                    if stats['count'] > 0:
                        f.write(f"{char_count},{punct_type},{stats['count']},{stats['avg']:.4f},{stats['median']:.4f},{stats['min']:.4f},{stats['max']:.4f},{stats['std']:.4f}\n")

        print(f"✅ Statistics exported to: {output_file}")
        print()
    except Exception as e:
        print(f"⚠️  Warning: Could not export to CSV: {e}")
        print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_word_length_duration_stats.py <json_file> [--csv output.csv]")
        print()
        print("Example:")
        print("  python analyze_word_length_duration_stats.py 02-FredagEttermiddag.json")
        print("  python analyze_word_length_duration_stats.py 02-FredagEttermiddag.json --csv stats.csv")
        sys.exit(1)

    json_file = sys.argv[1]

    # Check for CSV export option
    export_csv = False
    csv_file = None
    if len(sys.argv) >= 4 and sys.argv[2] == '--csv':
        export_csv = True
        csv_file = sys.argv[3]

    # Load and analyze data
    data = load_json_data(json_file)
    word_groups = analyze_words_by_length(data)

    if not word_groups:
        print("❌ No valid words found in the JSON file")
        sys.exit(1)

    # Print statistics table only
    print_statistics_table(word_groups)

    # Export to CSV if requested
    if export_csv and csv_file:
        export_to_csv(word_groups, csv_file)


if __name__ == "__main__":
    main()
