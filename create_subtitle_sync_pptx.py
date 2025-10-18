#!/usr/bin/env python3
"""
Create PowerPoint Showing Subtitle Synchronization Results

For each subtitle, shows:
- GREEN: Final corrected subtitle timing (entire subtitle)
- BLUE: Original timing of FIRST and LAST words (shows what needed correction)

This demonstrates how energy drop detection properly identifies subtitle boundaries.
"""

import json
import numpy as np
import librosa
import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.util import Inches, Pt
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import argparse
import re


@dataclass
class SRTSubtitle:
    """Represents a subtitle from SRT file"""
    index: int
    start_time: float
    end_time: float
    text: str

    @property
    def duration(self):
        return self.end_time - self.start_time


def parse_srt_time(time_str: str) -> float:
    """Convert SRT time format to seconds"""
    # Format: HH:MM:SS,mmm
    match = re.match(r'(\d+):(\d+):(\d+),(\d+)', time_str)
    if match:
        hours, minutes, seconds, milliseconds = map(int, match.groups())
        return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000
    return 0.0


def load_srt_file(srt_path: str) -> List[SRTSubtitle]:
    """Load subtitles from SRT file"""
    subtitles = []

    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by double newline to get subtitle blocks
    blocks = content.strip().split('\n\n')

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue

        try:
            index = int(lines[0])
            time_line = lines[1]
            text = '\n'.join(lines[2:])

            # Parse timing
            start_str, end_str = time_line.split(' --> ')
            start_time = parse_srt_time(start_str.strip())
            end_time = parse_srt_time(end_str.strip())

            subtitles.append(SRTSubtitle(
                index=index,
                start_time=start_time,
                end_time=end_time,
                text=text
            ))
        except (ValueError, IndexError):
            continue

    return subtitles


class SubtitleSyncPPTX:
    """Generate PowerPoint showing subtitle synchronization"""

    def __init__(self, audio_path: str, original_json: str, srt_path: str,
                 output_dir: str = "subtitle_sync"):
        self.audio_path = audio_path
        self.original_json = original_json
        self.srt_path = srt_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Load audio
        print(f"Loading audio: {audio_path}")
        self.audio, self.sr = librosa.load(audio_path, sr=16000, mono=True)
        print(f"Audio loaded: {len(self.audio)/self.sr:.1f}s")

        # Load original words
        print(f"Loading original timing: {original_json}")
        self.original_words = self.load_original_words()

        # Load SRT subtitles
        print(f"Loading SRT subtitles: {srt_path}")
        self.subtitles = load_srt_file(srt_path)
        print(f"Loaded {len(self.subtitles)} subtitles")

        # Create presentation
        self.prs = Presentation()
        self.prs.slide_width = Inches(10)
        self.prs.slide_height = Inches(7.5)

    def load_original_words(self) -> List[Dict]:
        """Load original words from WhisperX JSON"""
        with open(self.original_json, 'r', encoding='utf-8') as f:
            data = json.load(f)

        words = []
        for segment in data.get('segments', []):
            for word_data in segment.get('words', []):
                words.append({
                    'text': word_data.get('word', '').strip(),
                    'start': float(word_data.get('start', 0.0)),
                    'end': float(word_data.get('end', 0.0))
                })

        # Sort by start time
        words.sort(key=lambda w: w['start'])
        return words

    def get_words_in_subtitle_range(self, subtitle: SRTSubtitle) -> List[Dict]:
        """Get all original words that fall within this subtitle's time range"""
        words_in_range = []

        for word in self.original_words:
            # Check if word overlaps with subtitle timing
            # Word is in range if it starts within the subtitle or ends within the subtitle
            if (subtitle.start_time <= word['start'] <= subtitle.end_time or
                subtitle.start_time <= word['end'] <= subtitle.end_time or
                (word['start'] <= subtitle.start_time and word['end'] >= subtitle.end_time)):
                words_in_range.append(word)

        return words_in_range

    def find_first_last_original_timing(self, subtitle: SRTSubtitle) -> Tuple[Optional[Dict], Optional[Dict]]:
        """Find original timing for first and last words of the subtitle

        Returns: (first_word_original, last_word_original)
        """
        # Get subtitle text and clean it
        text = subtitle.text
        text = re.sub(r'\[.*?\]:\s*', '', text)  # Remove speaker labels
        text = text.replace('- ', '').replace(' -', '')  # Remove continuation hyphens

        subtitle_words = text.split()
        if not subtitle_words:
            return None, None

        # Get all original words in the subtitle's time range
        words_in_range = self.get_words_in_subtitle_range(subtitle)

        if not words_in_range:
            return None, None

        # Match first word
        first_word_text = subtitle_words[0].strip().lower().strip('.,!?;:-')
        first_original = None

        for orig_word in words_in_range:
            orig_clean = orig_word['text'].strip().lower().strip('.,!?;:-')
            if orig_clean == first_word_text:
                first_original = orig_word
                break

        # Match last word
        last_word_text = subtitle_words[-1].strip().lower().strip('.,!?;:-')
        last_original = None

        # Search from end backwards
        for orig_word in reversed(words_in_range):
            orig_clean = orig_word['text'].strip().lower().strip('.,!?;:-')
            if orig_clean == last_word_text:
                last_original = orig_word
                break

        return first_original, last_original

    def create_subtitle_waveform(self, subtitle: SRTSubtitle, output_path: Path, buffer: float = 1.0):
        """Create waveform showing subtitle sync with original first/last word timing"""

        # Find original timing for first and last words of THIS subtitle
        first_original, last_original = self.find_first_last_original_timing(subtitle)

        # Get word text for labels
        text = subtitle.text
        text = re.sub(r'\[.*?\]:\s*', '', text)
        text = text.replace('- ', '').replace(' -', '')
        subtitle_words = text.split()

        first_word = subtitle_words[0] if subtitle_words else None
        last_word = subtitle_words[-1] if subtitle_words else None

        # Extract audio segment
        start = subtitle.start_time - buffer
        end = subtitle.end_time + buffer
        start = max(0, start)
        end = min(len(self.audio) / self.sr, end)

        start_sample = int(start * self.sr)
        end_sample = int(end * self.sr)
        audio_segment = self.audio[start_sample:end_sample]

        # Create time array
        times = np.arange(len(audio_segment)) / self.sr + start

        # Create figure
        fig, ax = plt.subplots(figsize=(14, 5))

        # Plot waveform
        ax.plot(times, audio_segment, color='gray', linewidth=0.5, alpha=0.7)
        ax.fill_between(times, audio_segment, color='lightgray', alpha=0.3)

        # BLUE: Show original first word timing
        if first_original:
            ax.axvspan(first_original['start'], first_original['end'],
                      alpha=0.25, color='blue', label='Original First/Last Words')
            ax.axvline(first_original['start'], color='blue', linestyle='--', linewidth=2, alpha=0.7)
            ax.axvline(first_original['end'], color='blue', linestyle='--', linewidth=2, alpha=0.7)

            # Label first word
            ax.text(first_original['start'], ax.get_ylim()[1] * 0.9,
                   f"First: \"{first_word}\"", fontsize=9, color='blue',
                   bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))

        # BLUE: Show original last word timing
        if last_original:
            ax.axvspan(last_original['start'], last_original['end'],
                      alpha=0.25, color='blue')
            ax.axvline(last_original['start'], color='blue', linestyle='--', linewidth=2, alpha=0.7)
            ax.axvline(last_original['end'], color='blue', linestyle='--', linewidth=2, alpha=0.7)

            # Label last word
            ax.text(last_original['end'], ax.get_ylim()[1] * 0.9,
                   f"Last: \"{last_word}\"", fontsize=9, color='blue',
                   bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7),
                   horizontalalignment='right')

        # GREEN: Show corrected subtitle timing (full subtitle)
        ax.axvspan(subtitle.start_time, subtitle.end_time,
                  alpha=0.2, color='green', label='Corrected Subtitle Timing')
        ax.axvline(subtitle.start_time, color='green', linestyle='-', linewidth=3)
        ax.axvline(subtitle.end_time, color='green', linestyle='-', linewidth=3)

        # Labels and title
        ax.set_xlabel('Time (seconds)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Amplitude', fontsize=12, fontweight='bold')

        # Truncate text if too long
        display_text = subtitle.text.replace('\n', ' ')
        if len(display_text) > 60:
            display_text = display_text[:57] + "..."

        ax.set_title(f'Subtitle #{subtitle.index}: "{display_text}"',
                    fontsize=13, fontweight='bold', pad=15)
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3)

        # Add statistics box
        stats_lines = [f"Subtitle Duration: {subtitle.duration:.3f}s"]

        if first_original:
            first_diff = subtitle.start_time - first_original['start']
            stats_lines.append(f"First Word Shift: {first_diff*1000:+.0f}ms")

        if last_original:
            last_diff = subtitle.end_time - last_original['end']
            stats_lines.append(f"Last Word Shift: {last_diff*1000:+.0f}ms")

        stats_text = '\n'.join(stats_lines)

        ax.text(0.02, 0.02, stats_text, transform=ax.transAxes,
               fontsize=10, family='monospace', verticalalignment='bottom',
               bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

    def add_title_slide(self):
        """Add title slide"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])

        # Title
        title_box = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(8), Inches(1.5))
        text_frame = title_box.text_frame
        text_frame.text = "Subtitle Synchronization\nwith Energy Drop Detection"

        p = text_frame.paragraphs[0]
        p.font.size = Pt(44)
        p.font.bold = True
        p.alignment = 1

        # Subtitle
        subtitle_box = slide.shapes.add_textbox(Inches(1), Inches(4.2), Inches(8), Inches(1))
        text_frame = subtitle_box.text_frame
        text_frame.text = "GREEN = Final Corrected Subtitle\nBLUE = Original First/Last Word Boundaries"
        p = text_frame.paragraphs[0]
        p.font.size = Pt(20)
        p.alignment = 1

    def add_subtitle_slide(self, subtitle: SRTSubtitle):
        """Add a slide for a subtitle"""
        # Generate waveform
        img_path = self.output_dir / f"subtitle_{subtitle.index}.png"
        self.create_subtitle_waveform(subtitle, img_path)

        # Create slide
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])

        # Add title
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(9), Inches(0.5))
        text_frame = title_box.text_frame
        text_frame.text = f"Subtitle #{subtitle.index}"
        p = text_frame.paragraphs[0]
        p.font.size = Pt(28)
        p.font.bold = True

        # Add waveform image
        left = Inches(0.5)
        top = Inches(0.9)
        height = Inches(4)
        slide.shapes.add_picture(str(img_path), left, top, height=height)

        # Add subtitle text
        text_box = slide.shapes.add_textbox(Inches(0.8), Inches(5.2), Inches(8.4), Inches(1.8))
        text_frame = text_box.text_frame
        text_frame.word_wrap = True

        # Format subtitle text
        subtitle_text = subtitle.text.replace('- ', '').replace(' -', '')  # Remove hyphens
        subtitle_text = re.sub(r'\[.*?\]:\s*', '', subtitle_text)  # Remove speaker labels

        text_frame.text = f'"{subtitle_text}"'

        for paragraph in text_frame.paragraphs:
            paragraph.font.size = Pt(18)
            paragraph.font.bold = True
            paragraph.alignment = 1  # Center

        # Add timing info
        timing_box = slide.shapes.add_textbox(Inches(0.8), Inches(6.8), Inches(8.4), Inches(0.5))
        text_frame = timing_box.text_frame
        text_frame.text = f"Timing: {subtitle.start_time:.3f}s - {subtitle.end_time:.3f}s  |  Duration: {subtitle.duration:.3f}s"

        p = text_frame.paragraphs[0]
        p.font.size = Pt(14)
        p.font.name = 'Courier New'
        p.alignment = 1

    def generate_presentation(self, start_subtitle: int = 100, end_subtitle: int = 120,
                            output_name: str = "subtitle_sync.pptx"):
        """Generate the presentation"""
        print(f"\nGenerating PowerPoint for subtitles {start_subtitle}-{end_subtitle}...")

        # Filter subtitles
        selected_subtitles = [s for s in self.subtitles
                             if start_subtitle <= s.index <= end_subtitle]

        if not selected_subtitles:
            print(f"Warning: No subtitles found in range {start_subtitle}-{end_subtitle}")
            print(f"Available range: {self.subtitles[0].index} - {self.subtitles[-1].index}")
            return

        print(f"Creating slides for {len(selected_subtitles)} subtitles...")

        # Add title slide
        self.add_title_slide()

        # Add subtitle slides
        for i, subtitle in enumerate(selected_subtitles, 1):
            print(f"  Creating slide {i}/{len(selected_subtitles)}: Subtitle #{subtitle.index}")
            self.add_subtitle_slide(subtitle)

        # Save presentation
        output_path = self.output_dir / output_name
        self.prs.save(str(output_path))

        print(f"\n{'='*60}")
        print(f"PowerPoint created successfully!")
        print(f"{'='*60}")
        print(f"Output: {output_path}")
        print(f"Slides: {len(self.prs.slides)} total")
        print(f"  - 1 title slide")
        print(f"  - {len(selected_subtitles)} subtitle slides")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Create PowerPoint showing subtitle synchronization results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
    # Show subtitles 100-120
    python create_subtitle_sync_pptx.py audio.mp3 original.json output.srt --start 100 --end 120

    # Show first 20 subtitles
    python create_subtitle_sync_pptx.py audio.mp3 original.json output.srt --start 1 --end 20

VISUALIZATION:
    Each slide shows:
    - GREEN: Final corrected subtitle timing (full subtitle boundary)
    - BLUE: Original timing of first and last words (what needed correction)

    This demonstrates how energy drop detection properly identifies
    where subtitles should begin and end.
        """
    )

    parser.add_argument('audio_file', help='Audio file (MP3, WAV, etc.)')
    parser.add_argument('original_json', help='Original WhisperX JSON file')
    parser.add_argument('srt_file', help='Generated SRT file (corrected)')
    parser.add_argument('--start', type=int, default=100,
                       help='Start subtitle number (default: 100)')
    parser.add_argument('--end', type=int, default=120,
                       help='End subtitle number (default: 120)')
    parser.add_argument('--output-dir', default='subtitle_sync',
                       help='Output directory (default: subtitle_sync)')
    parser.add_argument('--output-name', default='subtitle_sync.pptx',
                       help='Output filename (default: subtitle_sync.pptx)')

    args = parser.parse_args()

    print("="*60)
    print("Subtitle Synchronization PowerPoint Generator")
    print("="*60)
    print(f"Audio: {args.audio_file}")
    print(f"Original JSON: {args.original_json}")
    print(f"SRT File: {args.srt_file}")
    print(f"Subtitle Range: {args.start}-{args.end}")

    generator = SubtitleSyncPPTX(
        args.audio_file,
        args.original_json,
        args.srt_file,
        args.output_dir
    )

    generator.generate_presentation(
        args.start,
        args.end,
        args.output_name
    )


if __name__ == "__main__":
    main()
