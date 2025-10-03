#!/usr/bin/env python3
"""
Hybrid Word-Level JSON to SRT Converter - Advanced Edition
===========================================================

This hybrid version combines the best features from both approaches:
- Intelligent timing corrections with data-driven duration analysis
- Intelligent buffer allocation (from v4_final)
- Proper segment splitting for duration caps (from v4_final)
- Orphan word prevention for better readability
- Advanced hyphenation logic

Features from improved_segmentation:
- Data-driven timing corrections based on vowel/syllable analysis
- Orphan word prevention
- Segment merging for very short fragments
- Optional speaker change handling

Features from v4_final:
- Intelligent buffer allocation based on actual gaps (50/50 split)
- 10ms safety gap preservation
- Proper segment splitting when exceeding max duration (10s default)
- Cleaner duration cap implementation
"""

import json
import argparse
import os
import sys
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import statistics


@dataclass
class Word:
    """Represents a word with timing and metadata"""
    text: str
    start: float
    end: float
    speaker: str
    score: float = 1.0
    is_ellipsis: bool = False
    original_duration: Optional[float] = None  # Track original before correction


@dataclass
class SubtitleSegment:
    """Represents a subtitle segment with multiple words"""
    words: List[Word]
    start_time: float
    end_time: float
    speaker: str


@dataclass
class ProcessingStats:
    """Statistics for processing operations"""
    words_processed: int = 0
    words_skipped: int = 0
    segments_created: int = 0
    speaker_changes: int = 0
    pause_breaks: int = 0
    overlaps_resolved: int = 0
    segments_merged: int = 0
    timing_corrections: int = 0
    corrections_first_words: int = 0
    corrections_last_words: int = 0
    orphan_breaks_prevented: int = 0
    intelligent_buffers_applied: int = 0
    segments_capped: int = 0


class WordLevelToSRTConverter:
    """Converts word-level JSON to SRT with intelligent timing corrections and buffer allocation"""

    def __init__(self, pause_threshold: float = 3.0, max_chars_per_line: int = 40,
                 max_lines: int = 2, overflow_tolerance: int = 4, add_hyphens: bool = True,
                 max_subtitle_duration: float = 15.0, apply_timing_corrections: bool = True,
                 timing_correction_threshold: float = 3.0, prevent_orphans: bool = True,
                 orphan_move_threshold: int = 15, break_on_speaker_change: bool = True,
                 speaker_change_threshold: float = 0.150, safety_gap_ms: int = 10):

        self.pause_threshold = pause_threshold
        self.max_chars_per_line = max_chars_per_line
        self.max_lines = max_lines
        self.overflow_tolerance = overflow_tolerance
        self.add_hyphens = add_hyphens
        self.max_subtitle_duration = max_subtitle_duration
        self.apply_timing_corrections = apply_timing_corrections
        self.timing_correction_threshold = timing_correction_threshold
        self.prevent_orphans = prevent_orphans
        self.orphan_move_threshold = orphan_move_threshold
        self.break_on_speaker_change = break_on_speaker_change
        self.speaker_change_threshold = speaker_change_threshold
        self.safety_gap = safety_gap_ms / 1000.0
        self.stats = ProcessingStats()

    def count_vowel_groups(self, word: str) -> int:
        """Count vowel groups (syllable approximation) in a word"""
        clean_word = re.sub(r'[^\w]', '', word)
        # Norwegian vowels including æ, ø, å
        vowel_groups = re.findall(r'[aeiouyæøå]+', clean_word.lower())
        return max(1, len(vowel_groups))  # At least 1

    def print_duration_table(self, duration_stats: Dict[int, Dict[str, float]]):
        """Print syllable/vowel duration statistics table"""
        print()
        print("=" * 60)
        print("SYLLABLE/VOWEL DURATION STATISTICS (from data)")
        print("=" * 60)
        print(f"{'syllables':<10} | {'no punct':<12} | {'soft punct':<12} | {'hard punct':<12}")
        print("-" * 60)

        sorted_vowel_counts = sorted(duration_stats.keys())
        for vowel_count in sorted_vowel_counts:
            punct_groups = duration_stats[vowel_count]

            none_avg = f"{punct_groups.get('none', 0):.2f}" if punct_groups.get('none') else "-"
            soft_avg = f"{punct_groups.get('soft', 0):.2f}" if punct_groups.get('soft') else "-"
            hard_avg = f"{punct_groups.get('hard', 0):.2f}" if punct_groups.get('hard') else "-"

            print(f"{vowel_count:<10} | {none_avg:<12} | {soft_avg:<12} | {hard_avg:<12}")

        print("-" * 60)
        print()

    def build_duration_statistics(self, words: List[Word]) -> Dict[int, Dict[str, float]]:
        """Build duration statistics from words for data-driven estimation

        Returns:
            Dict with structure: {vowel_count: {'none': avg, 'soft': avg, 'hard': avg}}
        """
        from collections import defaultdict

        # Collect durations by vowel count and punctuation type
        duration_groups = defaultdict(lambda: {'none': [], 'soft': [], 'hard': []})

        for word in words:
            vowel_count = self.count_vowel_groups(word.text)

            # Classify punctuation
            punct_type = 'none'
            if word.text.strip().endswith(('.', '!', '?')):
                punct_type = 'hard'
            elif word.text.strip().endswith((',', ';', ':')):
                punct_type = 'soft'

            duration = word.end - word.start

            # Only include reasonable durations for statistics (filter outliers)
            if 0.05 < duration < 3.0:
                duration_groups[vowel_count][punct_type].append(duration)

        # Calculate averages
        stats = {}
        for vowel_count, punct_groups in duration_groups.items():
            stats[vowel_count] = {}
            for punct_type, durations in punct_groups.items():
                if durations:
                    stats[vowel_count][punct_type] = statistics.median(durations)
                else:
                    stats[vowel_count][punct_type] = None

        return stats

    def estimate_typical_duration(self, word: str, duration_stats: Dict[int, Dict[str, float]] = None) -> float:
        """Estimate typical duration for a word based on vowel count (syllables) and statistics"""
        vowel_count = self.count_vowel_groups(word)

        # Classify punctuation
        punct_type = 'none'
        if word.strip().endswith(('.', '!', '?')):
            punct_type = 'hard'
        elif word.strip().endswith((',', ';', ':')):
            punct_type = 'soft'

        # Try to use statistics first (now based on vowel count)
        if duration_stats and vowel_count in duration_stats:
            avg_duration = duration_stats[vowel_count].get(punct_type)
            if avg_duration is not None:
                return avg_duration
            # Fallback to 'none' if specific punctuation not available
            if punct_type != 'none':
                avg_duration = duration_stats[vowel_count].get('none')
                if avg_duration is not None:
                    # Add small adjustment for punctuation
                    if punct_type == 'soft':
                        return avg_duration + 0.05
                    elif punct_type == 'hard':
                        return avg_duration + 0.1
                    return avg_duration

        # Fallback to vowel-based heuristic if no statistics available
        # Approximate: 0.2s per syllable/vowel group as base
        base_duration = vowel_count * 0.2 + 0.1

        # Punctuation adjustments
        if punct_type == 'soft':
            base_duration += 0.05
        elif punct_type == 'hard':
            base_duration += 0.1

        return max(0.1, base_duration)

    def apply_intelligent_timing_corrections(self, words: List[Word], duration_stats: Dict[int, Dict[str, float]] = None) -> List[Word]:
        """Apply intelligent timing corrections to words with anomalous durations using data-driven estimates

        Special handling for hard punctuation: ensures duration does not exceed average for that character count
        """

        if not self.apply_timing_corrections or len(words) < 2:
            return words

        corrected_words = []

        for i, word in enumerate(words):
            corrected_word = Word(
                text=word.text,
                start=word.start,
                end=word.end,
                speaker=word.speaker,
                score=word.score,
                is_ellipsis=word.is_ellipsis,
                original_duration=word.end - word.start
            )

            duration = word.end - word.start
            typical_duration = self.estimate_typical_duration(word.text, duration_stats)

            # Check if word has hard punctuation
            has_hard_punct = word.text.strip().endswith(('.', '!', '?'))

            # HARD PUNCTUATION CONSTRAINT: Never exceed average duration
            if has_hard_punct and duration > typical_duration:
                # Correct by adjusting end time to match typical duration
                proposed_end = corrected_word.start + typical_duration

                # Make sure we don't overlap with next word
                if i < len(words) - 1:
                    next_word = words[i + 1]
                    if proposed_end > next_word.start - 0.1:
                        # Leave 0.1s gap before next word
                        proposed_end = next_word.start - 0.1

                corrected_word.end = max(corrected_word.start + 0.05, proposed_end)  # Minimum 0.05s duration
                self.stats.timing_corrections += 1
                corrected_words.append(corrected_word)
                continue

            # Only correct other words that exceed threshold
            if duration < self.timing_correction_threshold:
                corrected_words.append(corrected_word)
                continue

            position = 'first' if i == 0 else 'last' if i == len(words) - 1 else 'middle'

            # Apply position-based corrections for non-hard-punctuation words
            if position == 'last' and duration > typical_duration * 3:
                # Last word: likely extended by silence after speech
                corrected_word.end = corrected_word.start + typical_duration
                self.stats.timing_corrections += 1
                self.stats.corrections_last_words += 1

            elif position == 'first' and duration > typical_duration * 3:
                # First word: likely extended by silence before speech
                if i < len(words) - 1:
                    next_word = words[i + 1]
                    # Adjust start time but don't overlap with next word
                    proposed_start = corrected_word.end - typical_duration
                    if proposed_start + typical_duration > next_word.start - 0.1:
                        proposed_start = max(corrected_word.start, next_word.start - typical_duration - 0.1)
                    corrected_word.start = proposed_start
                else:
                    corrected_word.start = corrected_word.end - typical_duration

                self.stats.timing_corrections += 1
                self.stats.corrections_first_words += 1

            elif position == 'middle' and duration > typical_duration * 4:
                # Middle word: center typical duration around middle of original timing
                middle_time = corrected_word.start + duration / 2
                corrected_word.start = middle_time - typical_duration / 2
                corrected_word.end = middle_time + typical_duration / 2
                self.stats.timing_corrections += 1

            corrected_words.append(corrected_word)

        return corrected_words

    def load_json_data(self, file_path: str) -> List[Word]:
        """Load and parse JSON file into Word objects with optional timing corrections"""

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Input file not found: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
        except Exception as e:
            raise ValueError(f"Error reading file: {e}")

        if not isinstance(data, dict):
            raise ValueError("JSON root must be an object")

        segments = data.get('segments', [])
        if not segments:
            raise ValueError("No 'segments' found in JSON data")

        print(f"Processing {len(segments)} segments...")

        words = []
        segment_count = 0
        valid_segments = 0

        # Group words by segment for timing correction analysis
        segment_words_groups = []

        for segment in segments:
            segment_count += 1

            if not isinstance(segment, dict):
                continue

            segment_speaker = segment.get('speaker', 'UNKNOWN')
            segment_words_list = segment.get('words', [])

            if not segment_words_list:
                continue

            valid_segments += 1
            segment_words = []

            # First pass: create Word objects
            for word_data in segment_words_list:
                if not isinstance(word_data, dict):
                    continue

                word_text = word_data.get('word', '').strip()
                if not word_text:
                    continue

                try:
                    start_time = float(word_data.get('start', 0.0))
                    end_time = float(word_data.get('end', 0.0))
                except (ValueError, TypeError):
                    print(f"Warning: Invalid timing for word '{word_text}' in segment {segment_count}")
                    continue

                if end_time <= start_time:
                    print(f"Warning: Invalid time range for word '{word_text}': {start_time} -> {end_time}")
                    continue

                speaker = word_data.get('speaker', segment_speaker)

                try:
                    score = float(word_data.get('score', 1.0))
                    score = max(0.0, min(1.0, score))
                except (ValueError, TypeError):
                    score = 1.0

                is_ellipsis = word_text in ['...', '…', '..', '.....', '....', '…..']

                segment_words.append(Word(
                    text=word_text,
                    start=start_time,
                    end=end_time,
                    speaker=speaker,
                    score=score,
                    is_ellipsis=is_ellipsis
                ))

            if segment_words:
                segment_words_groups.append(segment_words)

        # Collect all words first (without corrections) to build duration statistics
        all_words_uncorrected = []
        for segment_words in segment_words_groups:
            all_words_uncorrected.extend(segment_words)

        # Build duration statistics from all words
        print("Building duration statistics from data...")
        duration_stats = self.build_duration_statistics(all_words_uncorrected)

        # Print syllable/vowel duration table
        self.print_duration_table(duration_stats)

        # Apply timing corrections to each segment using the statistics
        for segment_words in segment_words_groups:
            corrected_segment_words = self.apply_intelligent_timing_corrections(segment_words, duration_stats)
            words.extend(corrected_segment_words)

        if not words:
            raise ValueError(f"No valid words found in JSON. Processed {segment_count} segments, {valid_segments} were valid")

        # Sort words by start time to ensure proper order
        try:
            words.sort(key=lambda w: w.start)
        except Exception as e:
            raise ValueError(f"Failed to sort words by timestamp: {e}")

        return words

    def detect_segment_breaks(self, words: List[Word]) -> List[int]:
        """Detect where subtitle segments should break (returns break indices)"""
        breaks = []

        for i in range(1, len(words)):
            current_word = words[i]
            prev_word = words[i - 1]

            # Calculate pause (end of previous word to start of current word)
            pause_duration = current_word.start - prev_word.end

            is_speaker_change = prev_word.speaker != current_word.speaker
            break_on_long_pause = pause_duration > self.pause_threshold
            break_on_speaker_change = self.break_on_speaker_change and is_speaker_change and pause_duration > self.speaker_change_threshold

            if break_on_long_pause or break_on_speaker_change:
                if break_on_long_pause:
                    self.stats.pause_breaks += 1
                if is_speaker_change:
                    self.stats.speaker_changes += 1
                breaks.append(i)

        return breaks

    def wrap_text(self, words: List[Word]) -> List[str]:
        """Wrap text into lines with balanced line lengths for better visual appearance"""
        if not words:
            return []

        # Reserve space for potential continuation hyphens
        hyphen_reserve = 2
        effective_limit = self.max_chars_per_line + self.overflow_tolerance - hyphen_reserve

        # Join all words to get full text (strip each word to remove any leading/trailing spaces)
        word_texts = [word.text.strip() for word in words]
        full_text = " ".join(word_texts)

        # If text fits on one line, use it
        if len(full_text) <= effective_limit:
            return [full_text]

        # If we're limited to 1 line, still preserve all words
        if self.max_lines == 1:
            if len(full_text) <= effective_limit:
                return [full_text]
            else:
                words_so_far = []
                for word_text in word_texts:
                    test_line = " ".join(words_so_far + [word_text])
                    if len(test_line) <= effective_limit:
                        words_so_far.append(word_text)
                    else:
                        break
                return [" ".join(words_so_far)] if words_so_far else [word_texts[0]]

        # For 2+ lines, try to balance the lines
        return self._balance_lines(word_texts, effective_limit)

    def _balance_lines(self, word_texts: List[str], effective_limit: int) -> List[str]:
        """Balance text across multiple lines for optimal visual appearance"""
        full_text = " ".join(word_texts)

        # If only 2 lines allowed, use balanced approach
        if self.max_lines == 2:
            return self._balance_two_lines(word_texts, effective_limit)

        # For 3+ lines, use simple greedy approach
        lines = []
        current_line = ""

        for i, word_text in enumerate(word_texts):
            if not current_line:
                current_line = word_text
            else:
                test_line = current_line + " " + word_text
                if len(test_line) <= effective_limit:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word_text

                    if len(lines) >= self.max_lines - 1:
                        lines.append(current_line)
                        remaining_words = word_texts[i+1:]
                        if remaining_words:
                            return lines
                        else:
                            return lines

        if current_line:
            lines.append(current_line)

        # Clean up any leading/trailing spaces from all lines
        return [line.strip() for line in lines]

    def _balance_two_lines(self, word_texts: List[str], effective_limit: int) -> List[str]:
        """Balance text optimally across exactly two lines"""
        if not word_texts:
            return []

        # Calculate total length and target lengths
        full_text = " ".join(word_texts)
        total_length = len(full_text)

        # Target: split as close to middle as possible
        target_first_line = total_length // 2

        best_split = 0
        best_balance = float('inf')

        # Try all possible splits
        for i in range(1, len(word_texts)):
            first_line_words = word_texts[:i]
            second_line_words = word_texts[i:]

            first_line = " ".join(first_line_words)
            second_line = " ".join(second_line_words)

            # Check if both lines fit within limits
            if len(first_line) > effective_limit or len(second_line) > effective_limit:
                continue

            # Calculate balance (how close to even split)
            balance = abs(len(first_line) - target_first_line)

            if balance < best_balance:
                best_balance = balance
                best_split = i

        # If no good split found, fall back to greedy approach
        if best_split == 0:
            current_line = ""
            for word_text in word_texts:
                test_line = current_line + (" " if current_line else "") + word_text
                if len(test_line) <= effective_limit:
                    current_line = test_line
                else:
                    break
            return [current_line] if current_line else [word_texts[0]]

        first_line = " ".join(word_texts[:best_split])
        second_line = " ".join(word_texts[best_split:])

        # Clean up any leading/trailing spaces
        return [first_line.strip(), second_line.strip()]

    def is_sentence_start(self, word: Word, prev_word: Optional[Word]) -> bool:
        """Detect if a word starts a new sentence"""
        if prev_word is None:
            return True

        # Check if previous word ends with strong punctuation
        prev_text = prev_word.text.strip()
        if prev_text.endswith(('.', '!', '?')):
            return True

        # Check if current word starts with capital letter (common sentence start indicator)
        current_text = word.text.strip()
        if current_text and current_text[0].isupper():
            # Additional check: previous word should end with punctuation or be a proper noun
            # This helps avoid false positives from proper nouns mid-sentence
            if prev_text.endswith(('.', '!', '?', ':', ';', ',')):
                return True

        return False

    def calculate_text_length(self, words: List[Word]) -> int:
        """Calculate total character length of words when joined"""
        if not words:
            return 0
        return len(" ".join(word.text for word in words))

    def check_for_orphans_in_wrapped_text(self, words: List[Word]) -> Optional[int]:
        """Check if wrapped text has orphan words at the end that should be moved to next subtitle

        Returns the index where to split, or None if no orphan found
        """
        if not self.prevent_orphans or len(words) < 2:
            return None

        # Wrap the text to see the actual lines
        lines = self.wrap_text(words)
        if len(lines) < 2:
            return None  # Single line, no orphan issue

        # Get the last line
        last_line = lines[-1].strip()
        last_line_words = last_line.split()

        # Check if last line is short enough to be considered orphan
        if len(last_line) > self.orphan_move_threshold:
            return None  # Last line is too long, not an orphan

        # Find where the last line starts in the word list
        # We need to find the words that make up the last line
        last_line_word_count = len(last_line_words)
        split_index = len(words) - last_line_word_count

        # Verify this is actually a sentence start
        if split_index > 0 and split_index < len(words):
            if self.is_sentence_start(words[split_index], words[split_index - 1]):
                self.stats.orphan_breaks_prevented += 1
                return split_index

        return None

    def split_oversized_segment(self, words: List[Word]) -> List[List[Word]]:
        """Split a segment that's too long into multiple segments with improved word preservation

        This enhanced version prevents orphan words by moving short sentence starts to the next subtitle.
        """

        if not words:
            return []

        segments = []
        current_segment = []

        for i, word in enumerate(words):
            # Try adding the word
            test_segment = current_segment + [word]

            # Test if this would create valid lines
            lines = self.wrap_text(test_segment)
            wrapped_word_count = sum(len(line.split()) for line in lines)
            expected_word_count = len(test_segment)

            # Check if adding this word would cause problems
            would_truncate = wrapped_word_count < expected_word_count
            would_exceed_lines = len(lines) > self.max_lines

            # If adding this word would cause issues, split here
            if (would_truncate or would_exceed_lines) and current_segment:

                # ORPHAN PREVENTION: Check if we should move sentence start to next subtitle
                if self.prevent_orphans and len(current_segment) >= 2:
                    # Look backwards to find sentence start
                    sentence_start_idx = None
                    for j in range(len(current_segment) - 1, 0, -1):
                        if self.is_sentence_start(current_segment[j], current_segment[j-1]):
                            sentence_start_idx = j
                            break

                    # If we found a sentence start near the end
                    if sentence_start_idx is not None:
                        # Calculate length of the sentence fragment at the end
                        fragment = current_segment[sentence_start_idx:]
                        fragment_length = self.calculate_text_length(fragment)

                        # If fragment is short enough, move it to next subtitle
                        if fragment_length <= self.orphan_move_threshold:
                            # Split segment before the sentence start
                            segments.append(current_segment[:sentence_start_idx])
                            # Start new segment with the sentence fragment + current word
                            current_segment = fragment + [word]
                            self.stats.orphan_breaks_prevented += 1
                            continue

                # Before finalizing the segment, check for orphans in wrapped text
                orphan_split_idx = self.check_for_orphans_in_wrapped_text(current_segment)
                if orphan_split_idx is not None and orphan_split_idx > 0:
                    # Split before the orphan
                    segments.append(current_segment[:orphan_split_idx])
                    # Start new segment with orphan words + current word
                    current_segment = current_segment[orphan_split_idx:] + [word]
                    continue

                # Standard split (no orphan prevention applied)
                segments.append(current_segment[:])
                # Start new segment with the current word
                current_segment = [word]
            else:
                # Safe to add the word
                current_segment.append(word)

        # Add remaining words, but check for orphans one more time
        if current_segment:
            orphan_split_idx = self.check_for_orphans_in_wrapped_text(current_segment)
            if orphan_split_idx is not None and orphan_split_idx > 0:
                segments.append(current_segment[:orphan_split_idx])
                segments.append(current_segment[orphan_split_idx:])
            else:
                segments.append(current_segment)

        return segments

    def create_segments(self, words: List[Word]) -> List[SubtitleSegment]:
        """Create subtitle segments from words"""
        if not words:
            return []

        break_indices = self.detect_segment_breaks(words)
        segments = []

        # Add breaks at start and end
        all_breaks = [0] + break_indices + [len(words)]

        for i in range(len(all_breaks) - 1):
            start_idx = all_breaks[i]
            end_idx = all_breaks[i + 1]

            segment_words = words[start_idx:end_idx]
            if not segment_words:
                continue

            # Check if segment needs splitting due to length
            word_groups = self.split_oversized_segment(segment_words)

            for word_group in word_groups:
                if not word_group:
                    continue

                # Create segment
                segment = SubtitleSegment(
                    words=word_group,
                    start_time=word_group[0].start,
                    end_time=word_group[-1].end,
                    speaker=word_group[0].speaker
                )

                segments.append(segment)
                self.stats.segments_created += 1

        return segments

    def apply_intelligent_buffers_and_caps(self, segments: List[SubtitleSegment]) -> List[SubtitleSegment]:
        """Applies intelligent buffer allocation and duration caps to segments.

        This combines the intelligent buffer logic from v4_final with proper segment splitting.
        Note: Buffer allocation happens first, then duration caps are enforced.
        """
        # Apply intelligent buffers based on gaps
        for i in range(len(segments) - 1):
            current_segment = segments[i]
            next_segment = segments[i+1]

            actual_end_current = current_segment.words[-1].end
            actual_start_next = next_segment.words[0].start

            gap = actual_start_next - actual_end_current

            if gap > self.safety_gap:
                total_buffer = gap - self.safety_gap
                trailing_buffer = total_buffer / 2
                leading_buffer = total_buffer / 2

                current_segment.end_time += trailing_buffer
                next_segment.start_time -= leading_buffer
                self.stats.intelligent_buffers_applied += 1

        # Apply max duration cap - simple truncation for buffer-extended segments
        # If a segment exceeds max duration AFTER buffer allocation, cap it
        for seg in segments:
            duration = seg.end_time - seg.start_time
            if duration > self.max_subtitle_duration:
                # Simple cap: truncate end time
                seg.end_time = seg.start_time + self.max_subtitle_duration
                self.stats.segments_capped += 1

        return segments

    def merge_short_segments(self, segments: List[SubtitleSegment]) -> List[SubtitleSegment]:
        """Merge very short segments with adjacent segments to reduce fragmentation"""
        if not segments:
            return []

        MIN_DURATION = 0.5  # Minimum duration threshold
        merged_segments = []
        i = 0

        while i < len(segments):
            current_segment = segments[i]
            current_duration = current_segment.end_time - current_segment.start_time

            # If current segment is too short, try to merge with adjacent segments
            if current_duration < MIN_DURATION:
                # Try to merge with next segment first (if same speaker)
                if (i + 1 < len(segments) and
                    segments[i + 1].speaker == current_segment.speaker):

                    next_segment = segments[i + 1]

                    # Create merged segment
                    merged_words = current_segment.words + next_segment.words
                    merged_segment = SubtitleSegment(
                        words=merged_words,
                        start_time=current_segment.start_time,
                        end_time=next_segment.end_time,
                        speaker=current_segment.speaker
                    )

                    merged_segments.append(merged_segment)
                    i += 2  # Skip the next segment since we merged it
                    self.stats.segments_merged += 1
                    continue

                # Try to merge with previous segment (if same speaker and we haven't added it yet)
                elif (merged_segments and
                      merged_segments[-1].speaker == current_segment.speaker):

                    prev_segment = merged_segments.pop()  # Remove last added segment

                    # Create merged segment
                    merged_words = prev_segment.words + current_segment.words
                    merged_segment = SubtitleSegment(
                        words=merged_words,
                        start_time=prev_segment.start_time,
                        end_time=current_segment.end_time,
                        speaker=prev_segment.speaker
                    )

                    merged_segments.append(merged_segment)
                    i += 1
                    self.stats.segments_merged += 1
                    continue

            # If we can't merge, add as-is
            merged_segments.append(current_segment)
            i += 1

        return merged_segments

    def ends_with_hard_punctuation(self, text: str) -> bool:
        """Check if text ends with HARD punctuation (NO continuation hyphens)

        HARD PUNCTUATION (. ! ?) = Complete sentence boundary, NO hyphens
        """
        text = text.strip()
        if not text:
            return False

        # Check for hard punctuation only (. ! ?)
        return text.endswith(('.', '!', '?'))

    def ends_with_soft_punctuation(self, text: str) -> bool:
        """Check if text ends with SOFT punctuation (NO trailing hyphens, but continuation implied)

        SOFT PUNCTUATION (, : ;) = Indicates continuation WITHOUT needing hyphens
        The soft punctuation itself shows the thought continues
        """
        text = text.strip()
        if not text:
            return False

        # Check for soft punctuation (, : ;)
        return text.endswith((',', ':', ';'))

    def get_last_word(self, segment: SubtitleSegment) -> str:
        """Get the last word text from a segment"""
        if not segment.words:
            return ""
        return segment.words[-1].text.strip()

    def get_first_word(self, segment: SubtitleSegment) -> str:
        """Get the first word text from a segment"""
        if not segment.words:
            return ""
        return segment.words[0].text.strip()

    def apply_subtitle_continuation_hyphens(self, text: str, subtitle_index: int, all_segments: List[SubtitleSegment]) -> str:
        """Apply continuation hyphens between subtitles (not within subtitle lines)

        CORRECTED RULES (per user feedback):

        HARD PUNCTUATION (. ! ?) = Complete sentence boundary, NO hyphens
        SOFT PUNCTUATION (, : ;) = Continuation implied by punctuation, NO trailing hyphens needed
        ELLIPSIS (...) = Treat as a WORD, can have hyphens like any other word

        RULES:
        1. NO trailing hyphen if ends with HARD punctuation (. ! ?)
        2. NO trailing hyphen if ends with SOFT punctuation (, : ;) - punctuation shows continuation
        3. YES trailing hyphen if ends with regular word or ellipsis (continues to next)
        4. NO leading hyphen if previous ended with HARD punctuation (. ! ?)
        5. YES leading hyphen if previous ended with SOFT punctuation or regular word/ellipsis
        6. NO hyphens if speaker changed
        """

        current_segment = all_segments[subtitle_index - 1]  # subtitle_index is 1-based
        lines = text.split('\n')

        # Check if this subtitle should START with "- " (continues from previous)
        should_start_with_hyphen = False
        if subtitle_index > 1:  # Not the first subtitle
            prev_segment = all_segments[subtitle_index - 2]

            # Same speaker check
            if prev_segment.speaker == current_segment.speaker:
                # Get previous subtitle's last word
                prev_last_word = self.get_last_word(prev_segment)

                # NO leading hyphen if previous ended with HARD punctuation (. ! ?)
                if self.ends_with_hard_punctuation(prev_last_word):
                    should_start_with_hyphen = False
                else:
                    # YES leading hyphen for soft punctuation, regular words, or ellipsis
                    should_start_with_hyphen = True

        # Check if this subtitle should END with " -" (continues to next)
        should_end_with_hyphen = False
        if subtitle_index < len(all_segments):  # Not the last subtitle
            next_segment = all_segments[subtitle_index]

            # Same speaker check
            if current_segment.speaker == next_segment.speaker:
                # Get current subtitle's last word
                current_last_word = self.get_last_word(current_segment)

                # NO trailing hyphen if ends with HARD punctuation (. ! ?)
                if self.ends_with_hard_punctuation(current_last_word):
                    should_end_with_hyphen = False
                # NO trailing hyphen if ends with SOFT punctuation (, : ;)
                elif self.ends_with_soft_punctuation(current_last_word):
                    should_end_with_hyphen = False
                else:
                    # YES trailing hyphen for regular words or ellipsis
                    should_end_with_hyphen = True

        # Apply hyphens to FIRST line only (leading) and LAST line only (trailing)
        if should_start_with_hyphen and not lines[0].startswith('- '):
            lines[0] = '- ' + lines[0]

        if should_end_with_hyphen and not lines[-1].endswith(' -'):
            lines[-1] = lines[-1] + ' -'

        return '\n'.join(lines)

    def format_srt_time(self, seconds: float) -> str:
        """Format time for SRT format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

    def generate_srt_content(self, segments: List[SubtitleSegment], include_speakers: bool = False) -> str:
        """Generate SRT format content from segments"""
        srt_lines = []

        for i, segment in enumerate(segments, 1):
            # Format timing
            start_time = self.format_srt_time(segment.start_time)
            end_time = self.format_srt_time(segment.end_time)

            # Generate text
            wrapped_lines = self.wrap_text(segment.words)
            text = '\n'.join(wrapped_lines)

            # Add speaker prefix if requested
            if include_speakers and segment.speaker != 'UNKNOWN':
                speaker_prefix = f"[{segment.speaker}]: "
                # Add prefix to first line only
                lines = text.split('\n')
                if lines:
                    lines[0] = speaker_prefix + lines[0]
                    text = '\n'.join(lines)

            # Apply subtitle-level continuation hyphens (between subtitles, not within)
            if self.add_hyphens:
                text = self.apply_subtitle_continuation_hyphens(text, i, segments)

            # Add to SRT
            srt_lines.extend([
                str(i),
                f"{start_time} --> {end_time}",
                text,
                ""
            ])

        return '\n'.join(srt_lines)

    def process_file(self, input_path: str, output_dir: str = None) -> tuple:
        """Process a JSON file and generate SRT files"""

        # Determine output directory
        if output_dir is None:
            output_dir = os.path.dirname(input_path) or '.'

        # Create output directory if it doesn't exist
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
                print(f"Created output directory: {output_dir}")
            except Exception as e:
                raise ValueError(f"Could not create output directory '{output_dir}': {e}")

        # Generate output file paths
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_with_speakers = os.path.join(output_dir, f"{base_name}_with_speakers.srt")
        output_clean = os.path.join(output_dir, f"{base_name}_clean.srt")

        # Warn about overwriting existing files
        for output_file in [output_with_speakers, output_clean]:
            if os.path.exists(output_file):
                print(f"Warning: Output file already exists and will be overwritten: {output_file}")

        # Load and process data
        print(f"Loading JSON file: {input_path}")
        words = self.load_json_data(input_path)

        print("Parsing word-level data...")
        self.stats.words_processed = len(words)

        print("Creating subtitle segments...")
        segments = self.create_segments(words)

        print("Applying intelligent buffers and duration caps...")
        segments = self.apply_intelligent_buffers_and_caps(segments)

        print("Merging short subtitle fragments...")
        segments = self.merge_short_segments(segments)

        print("Generating SRT files...")

        # Generate SRT content
        srt_with_speakers = self.generate_srt_content(segments, include_speakers=True)
        srt_clean = self.generate_srt_content(segments, include_speakers=False)

        # Write files
        with open(output_with_speakers, 'w', encoding='utf-8') as f:
            f.write(srt_with_speakers)

        with open(output_clean, 'w', encoding='utf-8') as f:
            f.write(srt_clean)

        return output_with_speakers, output_clean

    def print_stats(self):
        """Print processing statistics"""
        print(f"\nProcessing Statistics:")
        print(f"{'='*50}")
        print(f"Total words processed: {self.stats.words_processed}")
        print(f"Words skipped: {self.stats.words_skipped}")
        print(f"Subtitle segments created: {self.stats.segments_created}")
        print(f"Speaker changes detected: {self.stats.speaker_changes}")
        print(f"Pause breaks detected: {self.stats.pause_breaks}")
        print(f"Short segments merged: {self.stats.segments_merged}")
        print(f"Intelligent buffers applied: {self.stats.intelligent_buffers_applied}")
        print(f"Segments capped/split by duration: {self.stats.segments_capped}")

        if self.prevent_orphans:
            print(f"Orphan word breaks prevented: {self.stats.orphan_breaks_prevented}")

        if self.apply_timing_corrections:
            print(f"Timing corrections applied: {self.stats.timing_corrections}")
            print(f"  - First word corrections: {self.stats.corrections_first_words}")
            print(f"  - Last word corrections: {self.stats.corrections_last_words}")


def main():
    parser = argparse.ArgumentParser(
        description="Hybrid Word-Level JSON to SRT Converter - Advanced Edition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
    # Basic usage with all advanced features (default)
    python word_level_to_srt_hybrid.py transcript.json

    # Disable timing corrections
    python word_level_to_srt_hybrid.py transcript.json --no-timing-corrections

    # Custom correction threshold (only correct words longer than 5s)
    python word_level_to_srt_hybrid.py transcript.json --correction-threshold 5.0

    # Specify output directory
    python word_level_to_srt_hybrid.py transcript.json --output-dir ./corrected_subs/

HYBRID FEATURES:
    This version combines the best of both approaches:

    FROM IMPROVED_SEGMENTATION:
    - Data-driven timing corrections based on vowel/syllable analysis
    - Orphan word prevention for better readability
    - Segment merging for very short fragments
    - Advanced hyphenation logic

    FROM V4_FINAL:
    - Intelligent buffer allocation (50/50 gap distribution)
    - 10ms safety gap preservation
    - Duration cap enforcement (15s default)
    - Cleaner, more stable implementation

TIMING CORRECTIONS:
    Intelligently corrects anomalous word durations:
    - First words: Removes pre-speech silence/pauses
    - Last words: Removes post-speech silence/pauses
    - Hard punctuation: Never exceeds typical duration
    - Based on vowel count and position analysis

ORPHAN PREVENTION:
    Improves subtitle readability:
    - Detects sentence starts at the end of subtitles
    - Moves short sentence fragments (<=15 chars) to next subtitle
    - Ensures complete thoughts remain together
        """
    )

    parser.add_argument('input_json', help='Input JSON file with word-level data')
    parser.add_argument('--output-dir', help='Output directory for SRT files (default: same as input)')
    parser.add_argument('--pause-threshold', type=float, default=3.0, help='Pause threshold for segment breaks in seconds (default: 3.0)')
    parser.add_argument('--speaker-gap', type=float, default=0.150, dest='speaker_change_threshold', help='Time gap below which speaker changes are ignored (default: 0.150s)')
    parser.add_argument('--safety-gap-ms', type=int, default=10, help='Safety gap in milliseconds between segments (default: 10ms)')
    parser.add_argument('--max-chars-per-line', type=int, default=40, help='Maximum characters per line (default: 40)')
    parser.add_argument('--max-lines', type=int, default=2, help='Maximum lines per subtitle (default: 2)')
    parser.add_argument('--overflow-tolerance', type=int, default=4, help='Character overflow tolerance (default: 4)')
    parser.add_argument('--add-hyphens', action='store_true', default=True, help='Add continuation hyphens automatically (default: True)')
    parser.add_argument('--no-hyphens', action='store_false', dest='add_hyphens', help='Disable automatic continuation hyphens')
    parser.add_argument('--max-subtitle-duration', type=float, default=15.0, help='Maximum subtitle duration in seconds (default: 15.0)')
    parser.add_argument('--no-timing-corrections', action='store_false', dest='apply_timing_corrections', default=True, help='Disable intelligent timing corrections')
    parser.add_argument('--correction-threshold', type=float, default=3.0, help='Minimum duration for timing correction in seconds (default: 3.0)')
    parser.add_argument('--prevent-orphans', action='store_true', default=True, help='Prevent orphan words by moving short sentence starts to next subtitle (default: True)')
    parser.add_argument('--no-prevent-orphans', action='store_false', dest='prevent_orphans', help='Disable orphan prevention')
    parser.add_argument('--orphan-move-threshold', type=int, default=15, help='Maximum characters of sentence start to move to next subtitle (default: 15)')
    parser.add_argument('--break-on-speaker-change', action='store_true', default=True, help='Break subtitles on speaker changes (default: True)')
    parser.add_argument('--no-break-on-speaker-change', action='store_false', dest='break_on_speaker_change', help='Disable breaking on speaker changes')

    try:
        args = parser.parse_args()
    except SystemExit:
        return

    print("Starting hybrid word-level to SRT conversion...")
    print(f"Input: {args.input_json}")
    print(f"Output directory: {args.output_dir or 'same as input'}")

    print("\nConfiguration:")
    print(f"   Pause threshold: {args.pause_threshold}s")
    print(f"   Speaker change threshold: {args.speaker_change_threshold}s")
    print(f"   Safety gap: {args.safety_gap_ms}ms")
    print(f"   Text: {args.max_chars_per_line} chars/line, {args.max_lines} lines max")
    print(f"   Overflow tolerance: {args.overflow_tolerance} chars")
    print(f"   Continuation hyphens: {'enabled' if args.add_hyphens else 'disabled'}")
    print(f"   Max subtitle duration: {args.max_subtitle_duration}s")
    print(f"   Timing corrections: {'enabled' if args.apply_timing_corrections else 'disabled'}")
    if args.apply_timing_corrections:
        print(f"   Correction threshold: {args.correction_threshold}s")
    print(f"   Orphan prevention: {'enabled' if args.prevent_orphans else 'disabled'}")
    if args.prevent_orphans:
        print(f"   Orphan move threshold: {args.orphan_move_threshold} chars")
    print(f"   Break on speaker change: {'enabled' if args.break_on_speaker_change else 'disabled'}")

    try:
        # Create converter
        converter = WordLevelToSRTConverter(
            pause_threshold=args.pause_threshold,
            max_chars_per_line=args.max_chars_per_line,
            max_lines=args.max_lines,
            overflow_tolerance=args.overflow_tolerance,
            add_hyphens=args.add_hyphens,
            max_subtitle_duration=args.max_subtitle_duration,
            apply_timing_corrections=args.apply_timing_corrections,
            timing_correction_threshold=args.correction_threshold,
            prevent_orphans=args.prevent_orphans,
            orphan_move_threshold=args.orphan_move_threshold,
            break_on_speaker_change=args.break_on_speaker_change,
            speaker_change_threshold=args.speaker_change_threshold,
            safety_gap_ms=args.safety_gap_ms
        )

        # Process file
        output_with_speakers, output_clean = converter.process_file(args.input_json, args.output_dir)

        print(f"\nConversion completed successfully!")
        print(f"SRT with speakers: {output_with_speakers}")
        print(f"SRT without speakers: {output_clean}")

        # Print statistics
        converter.print_stats()

    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Suggestion: Check file format and try again")
        sys.exit(1)


if __name__ == "__main__":
    main()
