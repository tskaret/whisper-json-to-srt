#!/usr/bin/env python3
"""
Compare different transcription approaches:
1. WhisperX (original timing)
2. WhisperX + Energy Correction
3. whisper-timestamped (original timing)
4. whisper-timestamped + Energy Correction

Analyzes timing accuracy, word durations, and correction magnitudes
"""

import json
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict
import statistics


@dataclass
class WordTiming:
    """Word timing information"""
    text: str
    start: float
    end: float
    duration: float
    confidence: float
    source: str  # "whisperx", "whisperx_energy", "wt", "wt_energy"


def load_whisperx_json(json_path):
    """Load WhisperX format JSON"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    words = []
    for segment in data.get('segments', []):
        for word_obj in segment.get('words', []):
            words.append({
                'text': word_obj.get('word', ''),
                'start': word_obj.get('start', 0.0),
                'end': word_obj.get('end', 0.0),
                'score': word_obj.get('score', 1.0)
            })
    return words


def analyze_word_durations(words, source_name):
    """Analyze word duration statistics"""
    durations = [w['end'] - w['start'] for w in words if w['end'] > w['start']]

    if not durations:
        return None

    stats = {
        'source': source_name,
        'total_words': len(words),
        'mean_duration': statistics.mean(durations),
        'median_duration': statistics.median(durations),
        'min_duration': min(durations),
        'max_duration': max(durations),
        'std_deviation': statistics.stdev(durations) if len(durations) > 1 else 0,
        # Anomaly detection (duration > 2 seconds is suspicious)
        'anomalous_words': len([d for d in durations if d > 2.0]),
        'extreme_anomalies': len([d for d in durations if d > 5.0]),
    }

    return stats


def compare_word_timings(words1, words2, name1, name2):
    """
    Compare timing differences between two transcripts

    Assumes words are in same order (same text)
    """
    if len(words1) != len(words2):
        print(f"WARNING: Word count mismatch: {name1}={len(words1)}, {name2}={len(words2)}")
        return None

    start_diffs = []
    end_diffs = []
    duration_diffs = []

    for w1, w2 in zip(words1, words2):
        if w1['text'].strip() == w2['text'].strip():
            start_diff = abs(w1['start'] - w2['start'])
            end_diff = abs(w1['end'] - w2['end'])
            dur_diff = abs((w1['end'] - w1['start']) - (w2['end'] - w2['start']))

            start_diffs.append(start_diff)
            end_diffs.append(end_diff)
            duration_diffs.append(dur_diff)

    if not start_diffs:
        return None

    comparison = {
        'name1': name1,
        'name2': name2,
        'words_compared': len(start_diffs),
        'start_diff_mean': statistics.mean(start_diffs),
        'start_diff_median': statistics.median(start_diffs),
        'start_diff_max': max(start_diffs),
        'end_diff_mean': statistics.mean(end_diffs),
        'end_diff_median': statistics.median(end_diffs),
        'end_diff_max': max(end_diffs),
        'duration_diff_mean': statistics.mean(duration_diffs),
        'duration_diff_median': statistics.median(duration_diffs),
        'duration_diff_max': max(duration_diffs),
    }

    return comparison


def print_statistics(stats):
    """Print duration statistics"""
    print(f"\n{'='*60}")
    print(f"Source: {stats['source']}")
    print(f"{'='*60}")
    print(f"Total words: {stats['total_words']}")
    print(f"Mean duration: {stats['mean_duration']*1000:.1f}ms")
    print(f"Median duration: {stats['median_duration']*1000:.1f}ms")
    print(f"Min duration: {stats['min_duration']*1000:.1f}ms")
    print(f"Max duration: {stats['max_duration']*1000:.1f}ms")
    print(f"Std deviation: {stats['std_deviation']*1000:.1f}ms")
    print(f"Anomalous words (>2s): {stats['anomalous_words']} ({stats['anomalous_words']/stats['total_words']*100:.1f}%)")
    print(f"Extreme anomalies (>5s): {stats['extreme_anomalies']} ({stats['extreme_anomalies']/stats['total_words']*100:.1f}%)")


def print_comparison(comp):
    """Print timing comparison"""
    print(f"\n{'='*60}")
    print(f"Comparison: {comp['name1']} vs {comp['name2']}")
    print(f"{'='*60}")
    print(f"Words compared: {comp['words_compared']}")
    print(f"\nStart time differences:")
    print(f"  Mean: {comp['start_diff_mean']*1000:.1f}ms")
    print(f"  Median: {comp['start_diff_median']*1000:.1f}ms")
    print(f"  Max: {comp['start_diff_max']*1000:.1f}ms")
    print(f"\nEnd time differences:")
    print(f"  Mean: {comp['end_diff_mean']*1000:.1f}ms")
    print(f"  Median: {comp['end_diff_median']*1000:.1f}ms")
    print(f"  Max: {comp['end_diff_max']*1000:.1f}ms")
    print(f"\nDuration differences:")
    print(f"  Mean: {comp['duration_diff_mean']*1000:.1f}ms")
    print(f"  Median: {comp['duration_diff_median']*1000:.1f}ms")
    print(f"  Max: {comp['duration_diff_max']*1000:.1f}ms")


def main():
    """
    Compare four transcription approaches
    """
    if len(sys.argv) < 5:
        print("Usage: python compare_transcription_approaches.py <whisperx_json> <whisperx_energy_json> <wt_json> <wt_energy_json>")
        sys.exit(1)

    whisperx_json = sys.argv[1]
    whisperx_energy_json = sys.argv[2]
    wt_json = sys.argv[3]
    wt_energy_json = sys.argv[4]

    print("Loading transcripts...")
    whisperx_words = load_whisperx_json(whisperx_json)
    whisperx_energy_words = load_whisperx_json(whisperx_energy_json)
    wt_words = load_whisperx_json(wt_json)
    wt_energy_words = load_whisperx_json(wt_energy_json)

    print(f"\nLoaded:")
    print(f"  WhisperX: {len(whisperx_words)} words")
    print(f"  WhisperX + Energy: {len(whisperx_energy_words)} words")
    print(f"  whisper-timestamped: {len(wt_words)} words")
    print(f"  whisper-timestamped + Energy: {len(wt_energy_words)} words")

    # Analyze duration statistics for each approach
    print("\n" + "="*60)
    print("DURATION STATISTICS")
    print("="*60)

    wx_stats = analyze_word_durations(whisperx_words, "WhisperX")
    print_statistics(wx_stats)

    wx_energy_stats = analyze_word_durations(whisperx_energy_words, "WhisperX + Energy")
    print_statistics(wx_energy_stats)

    wt_stats = analyze_word_durations(wt_words, "whisper-timestamped")
    print_statistics(wt_stats)

    wt_energy_stats = analyze_word_durations(wt_energy_words, "whisper-timestamped + Energy")
    print_statistics(wt_energy_stats)

    # Compare approaches
    print("\n" + "="*60)
    print("PAIRWISE COMPARISONS")
    print("="*60)

    # Compare original methods
    if len(whisperx_words) == len(wt_words):
        comp1 = compare_word_timings(whisperx_words, wt_words, "WhisperX", "whisper-timestamped")
        if comp1:
            print_comparison(comp1)

    # Compare energy-corrected methods
    if len(whisperx_energy_words) == len(wt_energy_words):
        comp2 = compare_word_timings(whisperx_energy_words, wt_energy_words,
                                     "WhisperX+Energy", "whisper-timestamped+Energy")
        if comp2:
            print_comparison(comp2)

    # Compare effect of energy correction on WhisperX
    if len(whisperx_words) == len(whisperx_energy_words):
        comp3 = compare_word_timings(whisperx_words, whisperx_energy_words,
                                     "WhisperX", "WhisperX+Energy")
        if comp3:
            print_comparison(comp3)

    # Compare effect of energy correction on whisper-timestamped
    if len(wt_words) == len(wt_energy_words):
        comp4 = compare_word_timings(wt_words, wt_energy_words,
                                     "whisper-timestamped", "whisper-timestamped+Energy")
        if comp4:
            print_comparison(comp4)

    print("\n" + "="*60)
    print("COMPARISON COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
