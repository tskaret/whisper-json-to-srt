#!/usr/bin/env python3
"""
Word-Level JSON to SRT Converter - V4 Final
============================================

This script incorporates all fixes and implements the Intelligent Buffer
Allocation algorithm as specified in the project documentation to ensure
professional, accurately timed subtitles.

- V4 Fix: Corrected hyphenation logic to be compliant with validator.
- V3 Fix: Correctly trims word lists when capping subtitle duration.
- Corrected segmentation logic to handle speaker change heuristics.
- Implemented Intelligent Buffer Allocation for precise timing.
- All known bugs addressed.
"""

import json
import argparse
import os
import sys
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Word:
    """Represents a word with timing and metadata"""
    text: str
    start: float
    end: float
    speaker: str
    score: float = 1.0

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
    segments_created: int = 0
    speaker_changes_detected: int = 0
    pause_breaks: int = 0
    intelligent_buffers_applied: int = 0
    segments_capped: int = 0

class WordLevelToSRTConverter:
    """Converts word-level JSON to SRT with intelligent heuristics"""

    def __init__(self, pause_threshold: float = 3.0, max_chars_per_line: int = 40,
                 max_lines: int = 2, overflow_tolerance: int = 4, add_hyphens: bool = True,
                 max_subtitle_duration: float = 10.0, speaker_change_threshold: float = 0.150,
                 safety_gap_ms: int = 10):

        self.pause_threshold = pause_threshold
        self.max_chars_per_line = max_chars_per_line
        self.max_lines = max_lines
        self.overflow_tolerance = overflow_tolerance
        self.add_hyphens = add_hyphens
        self.max_subtitle_duration = max_subtitle_duration
        self.speaker_change_threshold = speaker_change_threshold
        self.safety_gap = safety_gap_ms / 1000.0
        self.stats = ProcessingStats()

    def load_json_data(self, file_path: str) -> List[Word]:
        """Load and parse JSON file into Word objects"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Input file not found: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")

        if not isinstance(data, dict):
            raise ValueError("JSON root must be an object")
        segments = data.get('segments', [])
        if not segments:
            raise ValueError("No 'segments' found in JSON data")

        words = []
        for segment in segments:
            segment_speaker = segment.get('speaker', 'UNKNOWN')
            for word_data in segment.get('words', []):
                word_text = word_data.get('word', '').strip()
                if not word_text: continue
                words.append(Word(
                    text=word_text,
                    start=float(word_data['start']),
                    end=float(word_data['end']),
                    speaker=word_data.get('speaker', segment_speaker),
                    score=float(word_data.get('score', 1.0))
                ))
        
        words.sort(key=lambda w: w.start)
        self.stats.words_processed = len(words)
        return words

    def detect_segment_breaks(self, words: List[Word]) -> List[int]:
        """Detect where subtitle segments should break"""
        breaks = []
        for i in range(1, len(words)):
            current_word = words[i]
            prev_word = words[i - 1]
            pause_duration = current_word.start - prev_word.end

            is_speaker_change = prev_word.speaker != current_word.speaker
            break_on_long_pause = pause_duration > self.pause_threshold
            break_on_speaker_change = is_speaker_change and pause_duration > self.speaker_change_threshold

            if break_on_long_pause or break_on_speaker_change:
                if break_on_long_pause: self.stats.pause_breaks += 1
                if is_speaker_change: self.stats.speaker_changes_detected += 1
                breaks.append(i)
        return breaks

    def wrap_text(self, words: List[Word]) -> List[str]:
        """Wrap text into lines with balanced line lengths"""
        if not words: return []
        word_texts = [word.text for word in words]
        full_text = " ".join(word_texts)
        effective_limit = self.max_chars_per_line + self.overflow_tolerance

        if len(full_text) <= effective_limit:
            return [full_text]
        if self.max_lines == 1:
            line = ""
            for word in word_texts:
                if len(line + " " + word) <= effective_limit:
                    line += (" " if line else "") + word
                else:
                    break
            return [line]

        # Balance for two lines
        total_len = len(full_text)
        best_split = -1
        min_diff = float('inf')
        for i in range(1, len(word_texts)):
            line1 = " ".join(word_texts[:i])
            line2 = " ".join(word_texts[i:])
            if len(line1) <= effective_limit and len(line2) <= effective_limit:
                diff = abs(len(line1) - len(line2))
                if diff < min_diff:
                    min_diff = diff
                    best_split = i
        
        if best_split != -1:
            return [" ".join(word_texts[:best_split]), " ".join(word_texts[best_split:])]
        else: # Fallback to greedy wrap
            lines = []
            line = ""
            for word in word_texts:
                if len(line + " " + word) > effective_limit and line:
                    lines.append(line)
                    line = word
                else:
                    line += (" " if line else "") + word
            if line: lines.append(line)
            return lines[:self.max_lines]

    def create_segments(self, words: List[Word]) -> List[SubtitleSegment]:
        """Create subtitle segments from words"""
        break_indices = self.detect_segment_breaks(words)
        segments = []
        all_breaks = sorted(list(set([0] + break_indices + [len(words)])))

        for i in range(len(all_breaks) - 1):
            start_idx, end_idx = all_breaks[i], all_breaks[i+1]
            segment_words = words[start_idx:end_idx]
            if not segment_words: continue

            segments.append(SubtitleSegment(
                words=segment_words,
                start_time=segment_words[0].start,
                end_time=segment_words[-1].end,
                speaker=segment_words[0].speaker
            ))
        self.stats.segments_created = len(segments)
        return segments

    def apply_intelligent_buffers_and_caps(self, segments: List[SubtitleSegment]) -> List[SubtitleSegment]:
        """Applies buffers and duration caps to segments."""
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
        
        # Apply max duration cap and split segments if necessary
        final_segments = []
        for seg in segments:
            duration = seg.end_time - seg.start_time
            if duration > self.max_subtitle_duration:
                self.stats.segments_capped += 1
                current_words = []
                current_start_time = seg.start_time
                for word in seg.words:
                    if not current_words or (word.end - current_start_time) <= self.max_subtitle_duration:
                        current_words.append(word)
                    else:
                        final_segments.append(SubtitleSegment(
                            words=current_words,
                            start_time=current_start_time,
                            end_time=current_words[-1].end,
                            speaker=current_words[0].speaker
                        ))
                        current_words = [word]
                        current_start_time = word.start
                if current_words:
                    final_segments.append(SubtitleSegment(
                        words=current_words,
                        start_time=current_start_time,
                        end_time=current_words[-1].end,
                        speaker=current_words[0].speaker
                    ))
            else:
                final_segments.append(seg)

        return final_segments

    def apply_subtitle_continuation_hyphens(self, text: str, subtitle_index: int, all_segments: List[SubtitleSegment]) -> str:
        """Apply continuation hyphens between subtitles according to validation rules."""
        if not self.add_hyphens:
            return text

        processed_text = text
        current_segment = all_segments[subtitle_index - 1]

        # Add LEADING hyphen if the previous segment continues to this one
        if subtitle_index > 1:
            prev_segment = all_segments[subtitle_index - 2]
            gap_from_prev = current_segment.start_time - prev_segment.end_time
            is_same_speaker = (prev_segment.speaker == current_segment.speaker) or (gap_from_prev < self.speaker_change_threshold)
            
            prev_text_wrapped = '\n'.join(self.wrap_text(prev_segment.words))
            if not prev_text_wrapped.strip().endswith(('.', '!', '?')) and is_same_speaker:
                processed_text = '- ' + processed_text

        # Add TRAILING hyphen if this segment continues to the next one
        if subtitle_index < len(all_segments):
            next_segment = all_segments[subtitle_index]
            gap_to_next = next_segment.start_time - current_segment.end_time
            is_same_speaker = (current_segment.speaker == next_segment.speaker) or (gap_to_next < self.speaker_change_threshold)

            if not text.strip().endswith(('.', '!', '?')) and is_same_speaker:
                processed_text = processed_text + ' -'
                
        return processed_text

    def format_srt_time(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def generate_srt_content(self, segments: List[SubtitleSegment], include_speakers: bool = False) -> str:
        srt_lines = []
        for i, segment in enumerate(segments, 1):
            start_time_str = self.format_srt_time(segment.start_time)
            end_time_str = self.format_srt_time(segment.end_time)
            text = '\n'.join(self.wrap_text(segment.words))
            if include_speakers and segment.speaker != 'UNKNOWN':
                text = f"[{segment.speaker}]: {text}"
            text = self.apply_subtitle_continuation_hyphens(text, i, segments)
            srt_lines.extend([str(i), f"{start_time_str} --> {end_time_str}", text, ""])
        return '\n'.join(srt_lines)

    def process_file(self, input_path: str, output_dir: str = None) -> tuple:
        if output_dir is None:
            output_dir = os.path.dirname(input_path) or '.'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_with_speakers = os.path.join(output_dir, f"{base_name}_with_speakers.srt")
        output_clean = os.path.join(output_dir, f"{base_name}_clean.srt")

        words = self.load_json_data(input_path)
        segments = self.create_segments(words)
        final_segments = self.apply_intelligent_buffers_and_caps(segments)
        
        srt_with_speakers = self.generate_srt_content(final_segments, include_speakers=True)
        srt_clean = self.generate_srt_content(final_segments, include_speakers=False)

        with open(output_with_speakers, 'w', encoding='utf-8') as f: f.write(srt_with_speakers)
        with open(output_clean, 'w', encoding='utf-8') as f: f.write(srt_clean)
        
        return output_with_speakers, output_clean

    def print_stats(self):
        print("\n📊 Processing Statistics:")
        print(f"{ '='*50}")
        print(f"Words Processed: {self.stats.words_processed}")
        print(f"Initial Segments Created: {self.stats.segments_created}")
        print(f"- Pause Breaks: {self.stats.pause_breaks}")
        print(f"- Speaker Change Breaks: {self.stats.speaker_changes_detected}")
        print(f"Segments Capped/Split by Duration: {self.stats.segments_capped}")
        print(f"Intelligent Buffers Applied: {self.stats.intelligent_buffers_applied}")

def main():
    parser = argparse.ArgumentParser(
        description="Word-Level JSON to SRT Converter - V4 Final",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script converts word-level JSON from a transcription process into professional SRT subtitle files.
It uses intelligent heuristics for segmentation and timing to produce a high-quality result.

Example:
    python word_level_to_srt_v4_final.py your_transcript.json --output-dir ./subs
        """
    )
    parser.add_argument('input_json', help='Input JSON file with word-level data')
    parser.add_argument('--output-dir', help='Output directory for SRT files (default: same as input)')
    parser.add_argument('--pause-threshold', type=float, default=3.0, help='Pause threshold for segment breaks in seconds (default: 3.0)')
    parser.add_argument('--speaker-gap', type=float, default=0.150, dest='speaker_change_threshold', help='Time gap below which speaker changes are ignored (default: 0.150s)')
    parser.add_argument('--max-chars-per-line', type=int, default=40, help='Maximum characters per line (default: 40)')
    parser.add_argument('--max-lines', type=int, default=2, help='Maximum lines per subtitle (default: 2)')
    parser.add_argument('--max-subtitle-duration', type=float, default=10.0, help='Maximum subtitle duration in seconds (default: 10.0)')
    
    args = parser.parse_args()

    try:
        converter = WordLevelToSRTConverter(
            pause_threshold=args.pause_threshold,
            max_chars_per_line=args.max_chars_per_line,
            max_lines=args.max_lines,
            max_subtitle_duration=args.max_subtitle_duration,
            speaker_change_threshold=args.speaker_change_threshold
        )
        output_with_speakers, output_clean = converter.process_file(args.input_json, args.output_dir)
        print("\n✅ Conversion completed successfully!")
        print(f"📄 SRT with speakers: {output_with_speakers}")
        print(f"📄 SRT without speakers: {output_clean}")
        converter.print_stats()
    except Exception as e:
        print(f"❌ Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
