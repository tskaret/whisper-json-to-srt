#!/usr/bin/env python3
"""
Create PowerPoint Presentation Comparing Original vs Energy-Corrected Timing

Generates slides with waveform visualizations showing:
- Original WhisperX timing (red)
- Energy-corrected timing (green)
- Statistics and improvements
"""

import json
import numpy as np
import librosa
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pptx import Presentation
from pptx.util import Inches, Pt
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
import argparse


@dataclass
class Word:
    text: str
    original_start: float
    original_end: float
    corrected_start: float
    corrected_end: float
    speaker: str

    @property
    def original_duration(self):
        return self.original_end - self.original_start

    @property
    def corrected_duration(self):
        return self.corrected_end - self.corrected_start

    @property
    def time_saved(self):
        return self.original_duration - self.corrected_duration

    @property
    def correction_magnitude(self):
        return max(
            abs(self.corrected_start - self.original_start),
            abs(self.corrected_end - self.original_end)
        )


class TimingComparisonPPTX:
    """Generate PowerPoint comparing original vs corrected timing"""

    def __init__(self, audio_path: str, original_json: str, output_dir: str = "timing_comparison"):
        self.audio_path = audio_path
        self.original_json = original_json
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Load audio
        print(f"Loading audio: {audio_path}")
        self.audio, self.sr = librosa.load(audio_path, sr=16000, mono=True)
        print(f"Audio loaded: {len(self.audio)/self.sr:.1f}s")

        # Create presentation
        self.prs = Presentation()
        self.prs.slide_width = Inches(10)
        self.prs.slide_height = Inches(7.5)

    def load_words_from_json(self, json_path: str) -> List[Dict]:
        """Load words from WhisperX JSON"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        words = []
        for segment in data.get('segments', []):
            speaker = segment.get('speaker', 'UNKNOWN')
            for word_data in segment.get('words', []):
                words.append({
                    'text': word_data.get('word', '').strip(),
                    'start': float(word_data.get('start', 0.0)),
                    'end': float(word_data.get('end', 0.0)),
                    'speaker': speaker
                })
        return words

    def create_waveform_comparison(self, word: Word, output_path: Path, buffer: float = 0.5):
        """Create waveform visualization comparing original vs corrected timing"""
        # Extract audio segment
        start = min(word.original_start, word.corrected_start) - buffer
        end = max(word.original_end, word.corrected_end) + buffer
        start = max(0, start)
        end = min(len(self.audio) / self.sr, end)

        start_sample = int(start * self.sr)
        end_sample = int(end * self.sr)
        audio_segment = self.audio[start_sample:end_sample]

        # Create time array
        times = np.arange(len(audio_segment)) / self.sr + start

        # Create figure
        fig, ax = plt.subplots(figsize=(14, 4))

        # Plot waveform
        ax.plot(times, audio_segment, color='gray', linewidth=0.5, alpha=0.7)
        ax.fill_between(times, audio_segment, color='lightgray', alpha=0.3)

        # Highlight original timing (red)
        ax.axvspan(word.original_start, word.original_end,
                   alpha=0.2, color='red', label='Original (WhisperX)')
        ax.axvline(word.original_start, color='red', linestyle='--', linewidth=2, alpha=0.7)
        ax.axvline(word.original_end, color='red', linestyle='--', linewidth=2, alpha=0.7)

        # Highlight corrected timing (green)
        ax.axvspan(word.corrected_start, word.corrected_end,
                   alpha=0.2, color='green', label='Energy-Corrected')
        ax.axvline(word.corrected_start, color='green', linestyle='-', linewidth=2)
        ax.axvline(word.corrected_end, color='green', linestyle='-', linewidth=2)

        # Labels and title
        ax.set_xlabel('Time (seconds)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Amplitude', fontsize=12, fontweight='bold')
        ax.set_title(f'Word: "{word.text}" (Speaker: {word.speaker})',
                    fontsize=14, fontweight='bold', pad=15)
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3)

        # Add statistics box
        stats_text = (
            f"Original:  {word.original_duration:.3f}s\n"
            f"Corrected: {word.corrected_duration:.3f}s\n"
            f"Saved:     {word.time_saved:.3f}s\n"
            f"Correction: {word.correction_magnitude*1000:.1f}ms"
        )
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
               fontsize=11, family='monospace', verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

    def add_title_slide(self):
        """Add title slide"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])  # Blank layout

        # Title
        left = Inches(1)
        top = Inches(2.5)
        width = Inches(8)
        height = Inches(1)

        title_box = slide.shapes.add_textbox(left, top, width, height)
        text_frame = title_box.text_frame
        text_frame.text = "Energy Drop Detection:\nTiming Correction Results"

        p = text_frame.paragraphs[0]
        p.font.size = Pt(44)
        p.font.bold = True
        p.alignment = 1  # Center

        # Subtitle
        subtitle_box = slide.shapes.add_textbox(Inches(1), Inches(4), Inches(8), Inches(0.5))
        text_frame = subtitle_box.text_frame
        text_frame.text = "Original WhisperX vs Energy-Corrected Timing"
        p = text_frame.paragraphs[0]
        p.font.size = Pt(24)
        p.alignment = 1  # Center

    def add_statistics_slide(self, words: List[Word]):
        """Add statistics overview slide"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])

        # Title
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(0.6))
        text_frame = title_box.text_frame
        text_frame.text = "Processing Statistics"
        p = text_frame.paragraphs[0]
        p.font.size = Pt(36)
        p.font.bold = True

        # Calculate statistics
        total_words = len(words)
        corrections = [w.correction_magnitude * 1000 for w in words]  # Convert to ms
        time_saved = [w.time_saved for w in words if w.time_saved > 0]

        avg_correction = np.mean(corrections) if corrections else 0
        max_correction = np.max(corrections) if corrections else 0
        total_time_saved = sum(time_saved)

        # Find extreme cases
        extreme_words = sorted(words, key=lambda w: w.time_saved, reverse=True)[:5]

        # Statistics text
        stats_text = f"""Total Words Processed: {total_words}

Average Correction: {avg_correction:.1f}ms
Maximum Correction: {max_correction:.1f}ms
Total Time Saved: {total_time_saved:.1f}s ({total_time_saved/60:.1f} minutes)

Top 5 Extreme Corrections:"""

        for i, word in enumerate(extreme_words, 1):
            stats_text += f"\n  {i}. \"{word.text}\" - {word.original_duration:.3f}s → {word.corrected_duration:.3f}s (saved {word.time_saved:.3f}s)"

        # Add text box
        text_box = slide.shapes.add_textbox(Inches(1), Inches(1.5), Inches(8), Inches(5))
        text_frame = text_box.text_frame
        text_frame.text = stats_text

        for paragraph in text_frame.paragraphs:
            paragraph.font.size = Pt(18)
            paragraph.font.name = 'Courier New'

    def add_comparison_slide(self, word: Word, slide_number: int):
        """Add a comparison slide for a specific word"""
        # Generate waveform
        img_path = self.output_dir / f"comparison_{slide_number}_{word.text.strip('.,!?')}.png"
        self.create_waveform_comparison(word, img_path)

        # Create slide
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])

        # Add title
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(9), Inches(0.5))
        text_frame = title_box.text_frame
        text_frame.text = f"Example {slide_number}: \"{word.text}\""
        p = text_frame.paragraphs[0]
        p.font.size = Pt(28)
        p.font.bold = True

        # Add waveform image
        left = Inches(0.5)
        top = Inches(1)
        height = Inches(3.5)
        slide.shapes.add_picture(str(img_path), left, top, height=height)

        # Add comparison table
        table_top = Inches(4.8)
        table_left = Inches(1)

        comparison_text = f"""Timing Comparison:

Original:   {word.original_start:.3f}s - {word.original_end:.3f}s  (duration: {word.original_duration:.3f}s)
Corrected:  {word.corrected_start:.3f}s - {word.corrected_end:.3f}s  (duration: {word.corrected_duration:.3f}s)

Time Saved: {word.time_saved:.3f}s
Correction Magnitude: {word.correction_magnitude*1000:.1f}ms"""

        text_box = slide.shapes.add_textbox(table_left, table_top, Inches(8), Inches(2))
        text_frame = text_box.text_frame
        text_frame.text = comparison_text

        for paragraph in text_frame.paragraphs:
            paragraph.font.size = Pt(16)
            paragraph.font.name = 'Courier New'

    def generate_presentation(self, output_name: str = "timing_comparison.pptx",
                            num_examples: int = 15):
        """Generate the complete presentation"""
        print(f"\nGenerating PowerPoint presentation...")

        # Load original words
        print("Loading original timing data...")
        original_words = self.load_words_from_json(self.original_json)

        # Run energy correction to get corrected timing
        print("Running energy correction...")
        from json_to_srt_energy import EnergyDropCorrector, Word as EnergyWord

        corrector = EnergyDropCorrector(self.audio_path)

        words_with_corrections = []
        for i, orig_word in enumerate(original_words):
            if (i + 1) % 500 == 0:
                print(f"  Processing word {i+1}/{len(original_words)}...")

            # Create word object for correction
            word = EnergyWord(
                text=orig_word['text'],
                start=orig_word['start'],
                end=orig_word['end'],
                speaker=orig_word['speaker'],
                original_start=orig_word['start'],
                original_end=orig_word['end']
            )

            # Apply correction
            corrected_word = corrector.correct_word_timing(word, sensitivity='high')

            # Store comparison
            if corrected_word.adjustment_magnitude:
                comparison_word = Word(
                    text=orig_word['text'],
                    original_start=orig_word['start'],
                    original_end=orig_word['end'],
                    corrected_start=corrected_word.start,
                    corrected_end=corrected_word.end,
                    speaker=orig_word['speaker']
                )
                words_with_corrections.append(comparison_word)

        print(f"Collected {len(words_with_corrections)} corrected words")

        # Sort by time saved (most dramatic corrections first)
        words_with_corrections.sort(key=lambda w: w.time_saved, reverse=True)

        # Add slides
        print("\nCreating slides...")
        self.add_title_slide()
        self.add_statistics_slide(words_with_corrections)

        # Add example slides
        examples_to_show = min(num_examples, len(words_with_corrections))
        print(f"Adding {examples_to_show} example slides...")

        for i in range(examples_to_show):
            word = words_with_corrections[i]
            print(f"  Creating slide {i+1}/{examples_to_show}: \"{word.text}\"")
            self.add_comparison_slide(word, i + 1)

        # Save presentation
        output_path = self.output_dir / output_name
        self.prs.save(str(output_path))
        print(f"\n{'='*60}")
        print(f"PowerPoint created successfully!")
        print(f"{'='*60}")
        print(f"Output: {output_path}")
        print(f"Slides: {len(self.prs.slides)} total")
        print(f"  - 1 title slide")
        print(f"  - 1 statistics slide")
        print(f"  - {examples_to_show} example slides")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Create PowerPoint comparing original vs energy-corrected timing",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('audio_file', help='Audio file (MP3, WAV, etc.)')
    parser.add_argument('json_file', help='Original WhisperX JSON file')
    parser.add_argument('--output-dir', default='timing_comparison',
                       help='Output directory (default: timing_comparison)')
    parser.add_argument('--output-name', default='timing_comparison.pptx',
                       help='Output PowerPoint filename (default: timing_comparison.pptx)')
    parser.add_argument('--num-examples', type=int, default=15,
                       help='Number of example slides to create (default: 15)')

    args = parser.parse_args()

    print("="*60)
    print("Timing Comparison PowerPoint Generator")
    print("="*60)
    print(f"Audio: {args.audio_file}")
    print(f"JSON: {args.json_file}")
    print(f"Examples: {args.num_examples}")

    generator = TimingComparisonPPTX(args.audio_file, args.json_file, args.output_dir)
    generator.generate_presentation(args.output_name, args.num_examples)


if __name__ == "__main__":
    main()
