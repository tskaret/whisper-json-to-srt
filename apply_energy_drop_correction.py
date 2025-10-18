"""
Apply Energy Drop Detection to Entire Transcript

Generates corrected timings for:
1. All words (with original and corrected timings)
2. All sentences (grouped with corrected boundaries)
3. JSON output with complete timing corrections
"""

import json
import numpy as np
import librosa
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict
from scipy import signal
import argparse


@dataclass
class Word:
    text: str
    start: float
    end: float
    score: float
    speaker: str
    original_start: float = None
    original_end: float = None
    adjustment_magnitude: float = 0.0
    adjustment_reason: str = ""

    def __post_init__(self):
        if self.original_start is None:
            self.original_start = self.start
        if self.original_end is None:
            self.original_end = self.end

    @property
    def duration(self):
        return self.end - self.start

    @property
    def original_duration(self):
        return self.original_end - self.original_start

    def count_syllables(self) -> int:
        vowels = 'aeiouyæøå'
        text_lower = self.text.lower().strip('.,!?;:-')
        count = 0
        prev_was_vowel = False
        for char in text_lower:
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                count += 1
            prev_was_vowel = is_vowel
        return max(1, count)


@dataclass
class Sentence:
    id: int
    words: List[Word]
    speaker: str

    @property
    def text(self) -> str:
        return ' '.join(w.text for w in self.words)

    @property
    def start(self) -> float:
        return self.words[0].start if self.words else 0.0

    @property
    def end(self) -> float:
        return self.words[-1].end if self.words else 0.0

    @property
    def original_start(self) -> float:
        return self.words[0].original_start if self.words else 0.0

    @property
    def original_end(self) -> float:
        return self.words[-1].original_end if self.words else 0.0


class EnergyDropCorrector:
    """Applies energy drop detection to correct word timings"""

    def __init__(self, audio_path: str, sr: int = 16000):
        print(f"Loading audio: {audio_path}")
        self.audio, self.sr = librosa.load(audio_path, sr=sr, mono=True)
        print(f"Audio loaded: {len(self.audio)/sr:.1f}s, sr={sr}Hz")

    def extract_segment(self, start: float, end: float,
                       buffer: float = 0.5) -> Tuple[np.ndarray, float]:
        actual_start = max(0, start - buffer)
        actual_end = min(len(self.audio) / self.sr, end + buffer)
        start_sample = int(actual_start * self.sr)
        end_sample = int(actual_end * self.sr)
        segment = self.audio[start_sample:end_sample]
        return segment, actual_start

    def correct_word_timing(self, word: Word, sensitivity: str = 'high') -> Word:
        """Apply energy drop detection to correct a single word"""
        audio, seg_start = self.extract_segment(word.original_start, word.original_end, buffer=0.5)

        # Calculate RMS energy
        frame_length = int(0.005 * self.sr)
        hop_length = int(0.002 * self.sr)
        rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]

        if len(rms) < 10:
            # Too short, keep original
            return word

        # Smooth RMS
        window_len = min(11, len(rms) // 2 * 2 + 1)
        if window_len < 3:
            rms_smooth = rms
        else:
            rms_smooth = signal.savgol_filter(rms, window_length=window_len, polyorder=2)

        # Calculate derivative
        derivative = np.gradient(rms_smooth)

        # Find rises and drops
        if sensitivity == 'high':
            rise_threshold = np.percentile(derivative, 80)
            drop_threshold = np.percentile(derivative, 20)
        elif sensitivity == 'medium':
            rise_threshold = np.percentile(derivative, 75)
            drop_threshold = np.percentile(derivative, 25)
        else:
            rise_threshold = np.percentile(derivative, 70)
            drop_threshold = np.percentile(derivative, 30)

        rises, _ = signal.find_peaks(derivative, height=rise_threshold, distance=5)
        drops, _ = signal.find_peaks(-derivative, height=-drop_threshold, distance=5)

        if len(rises) == 0 or len(drops) == 0:
            # Fallback: keep original
            return word

        # Find best rise/drop pair
        expected_duration = word.count_syllables() * 0.15
        min_duration = expected_duration * 0.5
        max_duration = expected_duration * 3.0

        best_start_idx = None
        best_end_idx = None
        best_score = 0

        for rise_idx in rises:
            for drop_idx in drops:
                if drop_idx <= rise_idx:
                    continue

                duration = (drop_idx - rise_idx) * hop_length / self.sr

                if duration < min_duration or duration > max_duration:
                    continue

                rise_strength = derivative[rise_idx]
                drop_strength = -derivative[drop_idx]
                duration_score = 1.0 - abs(duration - expected_duration) / max(expected_duration, 0.01)

                score = (rise_strength + drop_strength) * duration_score

                if score > best_score:
                    best_score = score
                    best_start_idx = rise_idx
                    best_end_idx = drop_idx

        if best_start_idx is None or best_end_idx is None:
            # Fallback: steepest rise and drop
            best_start_idx = rises[np.argmax(derivative[rises])]
            best_end_idx = drops[np.argmax(-derivative[drops])]

        # Apply correction
        corrected_start = seg_start + (best_start_idx * hop_length / self.sr)
        corrected_end = seg_start + (best_end_idx * hop_length / self.sr)

        # Calculate adjustment
        start_adj = abs(corrected_start - word.original_start)
        end_adj = abs(corrected_end - word.original_end)
        adjustment_magnitude = max(start_adj, end_adj)

        # Update word
        word.start = corrected_start
        word.end = corrected_end
        word.adjustment_magnitude = adjustment_magnitude
        word.adjustment_reason = f"Energy drop detection (sens={sensitivity})"

        return word

    def correct_all_words(self, words: List[Word],
                         sensitivity: str = 'high') -> List[Word]:
        """Apply energy drop correction to all words"""
        print(f"\nCorrecting {len(words)} words using energy drop detection...")

        corrected = []
        for i, word in enumerate(words, 1):
            if i % 100 == 0:
                print(f"  Processed {i}/{len(words)} words...")

            corrected_word = self.correct_word_timing(word, sensitivity)
            corrected.append(corrected_word)

        print(f"  Completed: {len(corrected)} words corrected")
        return corrected


class SentenceGrouper:
    """Groups words into sentences"""

    def __init__(self, pause_threshold: float = 3.0):
        self.pause_threshold = pause_threshold

    def group_sentences(self, words: List[Word]) -> List[Sentence]:
        """Group words into sentences"""
        if not words:
            return []

        sentences = []
        current_words = []
        current_speaker = words[0].speaker
        sentence_id = 0

        for i, word in enumerate(words):
            current_words.append(word)

            should_end = False

            # End on punctuation
            if word.text.rstrip().endswith(('.', '!', '?')):
                should_end = True

            # End on large pause
            if i < len(words) - 1:
                gap = words[i + 1].start - word.end
                if gap > self.pause_threshold:
                    should_end = True

            # End on speaker change
            if i < len(words) - 1:
                if words[i + 1].speaker != current_speaker:
                    should_end = True

            # Last word
            if i == len(words) - 1:
                should_end = True

            if should_end and current_words:
                sentence = Sentence(
                    id=sentence_id,
                    words=current_words.copy(),
                    speaker=current_speaker
                )
                sentences.append(sentence)

                current_words = []
                sentence_id += 1
                if i < len(words) - 1:
                    current_speaker = words[i + 1].speaker

        return sentences


def load_transcript(json_path: str, start_time: float = None,
                   end_time: float = None) -> List[Word]:
    """Load words from JSON transcript"""
    print(f"\nLoading transcript: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    words = []
    for segment in data['segments']:
        speaker = segment.get('speaker', 'UNKNOWN')
        for word_data in segment.get('words', []):
            word = Word(
                text=word_data['word'],
                start=word_data['start'],
                end=word_data['end'],
                score=word_data.get('score', 1.0),
                speaker=speaker
            )

            if start_time is not None and word.start < start_time:
                continue
            if end_time is not None and word.end > end_time:
                continue

            words.append(word)

    print(f"  Loaded {len(words)} words")
    return words


def save_corrected_json(words: List[Word], sentences: List[Sentence],
                       output_path: Path):
    """Save corrected timings to JSON"""
    data = {
        'metadata': {
            'method': 'energy_drop_detection',
            'total_words': len(words),
            'total_sentences': len(sentences)
        },
        'sentences': []
    }

    for sentence in sentences:
        sentence_data = {
            'id': sentence.id,
            'text': sentence.text,
            'speaker': sentence.speaker,
            'original_timing': {
                'start': sentence.original_start,
                'end': sentence.original_end,
                'duration': sentence.original_end - sentence.original_start
            },
            'corrected_timing': {
                'start': sentence.start,
                'end': sentence.end,
                'duration': sentence.end - sentence.start
            },
            'words': []
        }

        for word in sentence.words:
            word_data = {
                'text': word.text,
                'speaker': word.speaker,
                'score': word.score,
                'original_timing': {
                    'start': word.original_start,
                    'end': word.original_end,
                    'duration': word.original_duration
                },
                'corrected_timing': {
                    'start': word.start,
                    'end': word.end,
                    'duration': word.duration
                },
                'adjustment': {
                    'magnitude': word.adjustment_magnitude,
                    'start_delta': word.start - word.original_start,
                    'end_delta': word.end - word.original_end,
                    'reason': word.adjustment_reason
                }
            }
            sentence_data['words'].append(word_data)

        data['sentences'].append(sentence_data)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nCorrected timings saved: {output_path}")


def print_correction_report(words: List[Word], sentences: List[Sentence]):
    """Print detailed correction report"""
    print("\n" + "="*80)
    print("CORRECTION REPORT - Energy Drop Detection")
    print("="*80)

    # Word-level statistics
    adjustments = [w.adjustment_magnitude for w in words if w.adjustment_magnitude > 0]
    total_start_delta = sum(abs(w.start - w.original_start) for w in words)
    total_end_delta = sum(abs(w.end - w.original_end) for w in words)

    print(f"\nWord-level corrections:")
    print(f"  Total words: {len(words)}")
    print(f"  Words adjusted: {len(adjustments)}")
    print(f"  Avg adjustment magnitude: {np.mean(adjustments)*1000:.1f}ms" if adjustments else "  No adjustments")
    print(f"  Max adjustment magnitude: {np.max(adjustments)*1000:.1f}ms" if adjustments else "")
    print(f"  Total start adjustments: {total_start_delta:.1f}s")
    print(f"  Total end adjustments: {total_end_delta:.1f}s")

    # Find extreme corrections
    large_corrections = [w for w in words if w.adjustment_magnitude > 1.0]
    if large_corrections:
        print(f"\nExtreme corrections (>1s):")
        for w in large_corrections[:10]:
            print(f"  '{w.text}': {w.original_duration:.3f}s -> {w.duration:.3f}s "
                  f"(D {w.adjustment_magnitude*1000:.0f}ms)")

    # Sentence-level statistics
    print(f"\nSentence-level corrections:")
    print(f"  Total sentences: {len(sentences)}")

    sentence_time_saved = sum(
        (s.original_end - s.original_start) - (s.end - s.start)
        for s in sentences
    )
    print(f"  Total time saved: {sentence_time_saved:.1f}s")

    # Show sample sentences
    print(f"\nSample sentence corrections (first 5):")
    print("-"*80)
    print(f"{'ID':<5} {'Text':<40} {'Original':<15} {'Corrected':<15}")
    print("-"*80)

    for s in sentences[:5]:
        text = s.text[:37] + "..." if len(s.text) > 40 else s.text
        orig = f"{s.original_start:.2f}-{s.original_end:.2f}s"
        corr = f"{s.start:.2f}-{s.end:.2f}s"
        print(f"{s.id:<5} {text:<40} {orig:<15} {corr:<15}")


def main():
    parser = argparse.ArgumentParser(
        description='Apply energy drop detection to correct word timings'
    )
    parser.add_argument('audio_path', type=str, help='Path to audio file')
    parser.add_argument('json_path', type=str, help='Path to JSON transcript')
    parser.add_argument('--output-dir', type=str, default='corrected_output',
                       help='Output directory')
    parser.add_argument('--sensitivity', type=str, default='high',
                       choices=['low', 'medium', 'high'],
                       help='Detection sensitivity')
    parser.add_argument('--pause-threshold', type=float, default=3.0,
                       help='Pause threshold for sentence breaks (seconds)')
    parser.add_argument('--start-time', type=float, default=None,
                       help='Start time for processing (seconds)')
    parser.add_argument('--end-time', type=float, default=None,
                       help='End time for processing (seconds)')

    args = parser.parse_args()

    # Setup
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*80)
    print("ENERGY DROP CORRECTION - Applying to Transcript")
    print("="*80)

    # Load transcript
    words = load_transcript(args.json_path, args.start_time, args.end_time)

    # Apply energy drop correction
    corrector = EnergyDropCorrector(args.audio_path)
    corrected_words = corrector.correct_all_words(words, sensitivity=args.sensitivity)

    # Group into sentences
    print(f"\nGrouping into sentences (pause threshold: {args.pause_threshold}s)...")
    grouper = SentenceGrouper(pause_threshold=args.pause_threshold)
    sentences = grouper.group_sentences(corrected_words)
    print(f"  Created {len(sentences)} sentences")

    # Save corrected JSON
    json_name = Path(args.json_path).stem
    output_json = output_dir / f"{json_name}_energy_corrected.json"
    save_corrected_json(corrected_words, sentences, output_json)

    # Print report
    print_correction_report(corrected_words, sentences)

    # Print detailed sentence report
    print("\n" + "="*80)
    print("DETAILED SENTENCE TIMINGS")
    print("="*80)

    for sentence in sentences[:20]:  # Show first 20
        print(f"\n[Sentence {sentence.id}] Speaker: {sentence.speaker}")
        print(f"Text: {sentence.text}")
        print(f"Original timing: {sentence.original_start:.3f}s - {sentence.original_end:.3f}s "
              f"(duration: {sentence.original_end - sentence.original_start:.3f}s)")
        print(f"Corrected timing: {sentence.start:.3f}s - {sentence.end:.3f}s "
              f"(duration: {sentence.end - sentence.start:.3f}s)")
        print(f"Time saved: {(sentence.original_end - sentence.original_start) - (sentence.end - sentence.start):.3f}s")

        print(f"  Words ({len(sentence.words)}):")
        for word in sentence.words:
            orig = f"{word.original_start:.3f}-{word.original_end:.3f}s"
            corr = f"{word.start:.3f}-{word.end:.3f}s"
            delta = f"D{word.adjustment_magnitude*1000:+.0f}ms"
            print(f"    {word.text:15s} {orig:20s} -> {corr:20s} {delta}")

    print("\n" + "="*80)
    print("COMPLETED")
    print("="*80)
    print(f"Output saved to: {output_json}")
    print(f"\nNext steps:")
    print(f"1. Review corrected timings in: {output_json}")
    print(f"2. Generate SRT: python json_to_srt_fixed.py {output_json}")


if __name__ == '__main__':
    main()
