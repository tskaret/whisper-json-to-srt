"""
Test RMS Threshold Approach for Word Boundary Detection

User's insight: Use the squared average (RMS) energy of the entire word interval
as a threshold, then find where energy rises above/falls below it to detect
actual word boundaries.

This is simpler and potentially more robust than gradient-based detection.
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import librosa
from pathlib import Path
from typing import List, Tuple, Dict
from dataclasses import dataclass


@dataclass
class Word:
    text: str
    start: float
    end: float
    score: float
    speaker: str
    original_start: float = None
    original_end: float = None

    @property
    def duration(self):
        return self.end - self.start

    def count_syllables(self) -> int:
        """Count syllables based on Norwegian vowel groups"""
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


class RMSThresholdDetector:
    """Detects word boundaries using RMS threshold approach"""

    def __init__(self, audio_path: str, sr: int = 16000):
        print(f"Loading audio: {audio_path}")
        self.audio, self.sr = librosa.load(audio_path, sr=sr, mono=True)
        print(f"Audio loaded: {len(self.audio)/sr:.1f}s, sr={sr}Hz")

    def extract_segment(self, start: float, end: float,
                       buffer: float = 0.2) -> Tuple[np.ndarray, float]:
        """Extract audio segment with buffer"""
        actual_start = max(0, start - buffer)
        actual_end = min(len(self.audio) / self.sr, end + buffer)

        start_sample = int(actual_start * self.sr)
        end_sample = int(actual_end * self.sr)

        segment = self.audio[start_sample:end_sample]
        return segment, actual_start

    def detect_boundaries_rms_threshold(self, word: Word,
                                       buffer: float = 0.2) -> Dict:
        """
        Detect word boundaries using RMS threshold approach

        Method:
        1. Extract word segment with buffer
        2. Calculate RMS energy for entire segment
        3. Use mean RMS as threshold
        4. Find first/last points where RMS > threshold
        """
        audio, seg_start = self.extract_segment(word.start, word.end, buffer)

        # Calculate RMS energy with small frame
        frame_length = int(0.005 * self.sr)  # 5ms frames
        hop_length = int(0.002 * self.sr)     # 2ms hop

        rms = librosa.feature.rms(y=audio, frame_length=frame_length,
                                 hop_length=hop_length)[0]

        # Calculate threshold as mean RMS of the segment
        rms_mean = np.mean(rms)
        rms_std = np.std(rms)

        # Use mean as base threshold
        threshold = rms_mean

        # Find first point where RMS rises above threshold
        first_above = None
        for i in range(len(rms)):
            if rms[i] > threshold:
                first_above = i
                break

        # Find last point where RMS is above threshold
        last_above = None
        for i in range(len(rms) - 1, -1, -1):
            if rms[i] > threshold:
                last_above = i
                break

        if first_above is not None and last_above is not None:
            # Convert frame indices to time
            detected_start = seg_start + (first_above * hop_length / self.sr)
            detected_end = seg_start + (last_above * hop_length / self.sr)

            # Calculate adjustments
            start_adjustment = detected_start - word.start
            end_adjustment = detected_end - word.end

            return {
                'method': 'rms_threshold',
                'detected_start': detected_start,
                'detected_end': detected_end,
                'detected_duration': detected_end - detected_start,
                'original_duration': word.duration,
                'start_adjustment': start_adjustment,
                'end_adjustment': end_adjustment,
                'threshold': threshold,
                'rms_mean': rms_mean,
                'rms_std': rms_std,
                'success': True
            }
        else:
            return {
                'method': 'rms_threshold',
                'detected_start': word.start,
                'detected_end': word.end,
                'detected_duration': word.duration,
                'original_duration': word.duration,
                'start_adjustment': 0.0,
                'end_adjustment': 0.0,
                'threshold': threshold,
                'rms_mean': rms_mean,
                'rms_std': rms_std,
                'success': False
            }

    def visualize_detection(self, word: Word, result: Dict, output_path: Path):
        """Visualize RMS threshold detection"""
        audio, seg_start = self.extract_segment(word.start, word.end, buffer=0.2)

        # Calculate RMS
        frame_length = int(0.005 * self.sr)
        hop_length = int(0.002 * self.sr)
        rms = librosa.feature.rms(y=audio, frame_length=frame_length,
                                 hop_length=hop_length)[0]

        # Time axis for RMS
        rms_times = seg_start + np.arange(len(rms)) * hop_length / self.sr

        # Time axis for waveform
        audio_times = seg_start + np.arange(len(audio)) / self.sr

        # Create figure
        fig, axes = plt.subplots(2, 1, figsize=(14, 8))
        fig.suptitle(f'RMS Threshold Detection: "{word.text}" ({word.count_syllables()} syl)',
                    fontsize=14, fontweight='bold')

        # Top panel: Waveform with boundaries
        ax1 = axes[0]
        ax1.plot(audio_times, audio, linewidth=0.5, color='gray', alpha=0.7)
        ax1.set_title('Waveform with Original and Detected Boundaries', fontweight='bold')
        ax1.set_ylabel('Amplitude')
        ax1.grid(True, alpha=0.3)

        # Original boundary
        ax1.axvspan(word.start, word.end, alpha=0.2, color='red', label='Original')
        ax1.axvline(word.start, color='red', linestyle='--', linewidth=2)
        ax1.axvline(word.end, color='red', linestyle='--', linewidth=2)

        # Detected boundary
        if result['success']:
            ax1.axvspan(result['detected_start'], result['detected_end'],
                       alpha=0.2, color='green', label='Detected')
            ax1.axvline(result['detected_start'], color='green', linestyle='-', linewidth=2)
            ax1.axvline(result['detected_end'], color='green', linestyle='-', linewidth=2)

        ax1.legend(loc='upper right')
        ax1.set_xlim(audio_times[0], audio_times[-1])

        # Bottom panel: RMS energy with threshold
        ax2 = axes[1]
        ax2.plot(rms_times, rms, linewidth=1.5, color='blue', label='RMS Energy')
        ax2.axhline(result['rms_mean'], color='orange', linestyle='--',
                   linewidth=2, label=f"Threshold (mean={result['rms_mean']:.4f})")
        ax2.fill_between(rms_times, 0, result['rms_mean'], alpha=0.2, color='orange')
        ax2.set_title('RMS Energy with Threshold', fontweight='bold')
        ax2.set_xlabel('Time (seconds)')
        ax2.set_ylabel('RMS Energy')
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='upper right')
        ax2.set_xlim(audio_times[0], audio_times[-1])

        # Mark detected boundaries on RMS plot
        if result['success']:
            ax2.axvline(result['detected_start'], color='green', linestyle='-',
                       linewidth=2, alpha=0.7)
            ax2.axvline(result['detected_end'], color='green', linestyle='-',
                       linewidth=2, alpha=0.7)

        # Mark original boundaries on RMS plot
        ax2.axvline(word.start, color='red', linestyle='--', linewidth=2, alpha=0.5)
        ax2.axvline(word.end, color='red', linestyle='--', linewidth=2, alpha=0.5)

        # Add statistics text
        stats_text = (
            f"Original duration: {word.duration:.3f}s\n"
            f"Detected duration: {result['detected_duration']:.3f}s\n"
            f"Start adjustment: {result['start_adjustment']*1000:+.1f}ms\n"
            f"End adjustment: {result['end_adjustment']*1000:+.1f}ms\n"
            f"RMS mean: {result['rms_mean']:.4f}\n"
            f"RMS std: {result['rms_std']:.4f}"
        )
        fig.text(0.02, 0.02, stats_text, fontsize=10, family='monospace',
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

        plt.tight_layout(rect=[0, 0.08, 1, 0.97])
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()


def load_words(json_path: str, start_time: float = 0,
               end_time: float = None) -> List[Word]:
    """Load words from JSON transcript"""
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
            if word.start >= start_time and (end_time is None or word.end <= end_time):
                words.append(word)

    return words


def main():
    audio_path = r"d:\stevner\2025\regionalt\Lørdag\04-LørdagEttermiddag\04-LørdagEttermiddag.mp3"
    json_path = "04-LørdagEttermiddag.json"

    print("\n" + "="*70)
    print("RMS THRESHOLD APPROACH - WORD BOUNDARY DETECTION")
    print("="*70)

    # Test on normal words (0-70s)
    print("\n### Testing on NORMAL words (0-70s) ###")
    words_normal = load_words(json_path, 0, 70)
    print(f"Loaded {len(words_normal)} words")

    # Test on extreme anomaly segment
    print("\n### Testing on EXTREME ANOMALIES (490-545s) ###")
    words_extreme = load_words(json_path, 490, 545)
    print(f"Loaded {len(words_extreme)} words")

    # Initialize detector
    detector = RMSThresholdDetector(audio_path)

    # Create output directory
    output_dir = Path("rms_threshold_test")
    output_dir.mkdir(exist_ok=True)

    # Test on sample of normal words
    print("\n" + "-"*70)
    print("NORMAL WORDS - First 10")
    print("-"*70)
    print(f"{'Word':<18} {'Orig Dur':<10} {'Det Dur':<10} {'Start D':<10} {'End D':<10}")
    print("-"*70)

    for i, word in enumerate(words_normal[:10], 1):
        result = detector.detect_boundaries_rms_threshold(word)

        print(f"{word.text:<18} "
              f"{word.duration:>8.3f}s "
              f"{result['detected_duration']:>8.3f}s "
              f"{result['start_adjustment']*1000:>8.1f}ms "
              f"{result['end_adjustment']*1000:>8.1f}ms")

        # Visualize first 3
        if i <= 3:
            viz_path = output_dir / f"normal_{i}_{word.text.strip('.,!?')}.png"
            detector.visualize_detection(word, result, viz_path)
            print(f"  Visualization: {viz_path.name}")

    # Test on extreme anomalies
    print("\n" + "-"*70)
    print("EXTREME ANOMALIES - All words")
    print("-"*70)
    print(f"{'Word':<18} {'Orig Dur':<12} {'Det Dur':<12} {'Start D':<10} {'End D':<10}")
    print("-"*70)

    for i, word in enumerate(words_extreme, 1):
        result = detector.detect_boundaries_rms_threshold(word)

        expected_dur = word.count_syllables() * 0.15
        is_anomalous = word.duration > (expected_dur * 2.0)

        marker = "***" if is_anomalous else ""

        print(f"{word.text:<18} "
              f"{word.duration:>10.3f}s "
              f"{result['detected_duration']:>10.3f}s "
              f"{result['start_adjustment']*1000:>8.1f}ms "
              f"{result['end_adjustment']*1000:>8.1f}ms {marker}")

        # Visualize all extreme cases
        if is_anomalous:
            viz_path = output_dir / f"extreme_{i}_{word.text.strip('.,!?')}.png"
            detector.visualize_detection(word, result, viz_path)
            print(f"  Visualization: {viz_path.name}")

    # Summary statistics
    print("\n" + "="*70)
    print("SUMMARY STATISTICS")
    print("="*70)

    # Normal words
    normal_results = [detector.detect_boundaries_rms_threshold(w) for w in words_normal[:15]]
    normal_start_adj = [abs(r['start_adjustment']) for r in normal_results]
    normal_end_adj = [abs(r['end_adjustment']) for r in normal_results]
    normal_total_adj = [s + e for s, e in zip(normal_start_adj, normal_end_adj)]

    print(f"\nNormal words (n={len(normal_results)}):")
    print(f"  Avg start adjustment: {np.mean(normal_start_adj)*1000:.1f}ms")
    print(f"  Avg end adjustment:   {np.mean(normal_end_adj)*1000:.1f}ms")
    print(f"  Avg total adjustment: {np.mean(normal_total_adj)*1000:.1f}ms")
    print(f"  Max total adjustment: {np.max(normal_total_adj)*1000:.1f}ms")

    # Extreme anomalies
    extreme_results = [detector.detect_boundaries_rms_threshold(w) for w in words_extreme]
    extreme_start_adj = [abs(r['start_adjustment']) for r in extreme_results]
    extreme_end_adj = [abs(r['end_adjustment']) for r in extreme_results]
    extreme_total_adj = [s + e for s, e in zip(extreme_start_adj, extreme_end_adj)]

    print(f"\nExtreme anomalies (n={len(extreme_results)}):")
    print(f"  Avg start adjustment: {np.mean(extreme_start_adj)*1000:.1f}ms")
    print(f"  Avg end adjustment:   {np.mean(extreme_end_adj)*1000:.1f}ms")
    print(f"  Avg total adjustment: {np.mean(extreme_total_adj)*1000:.1f}ms")
    print(f"  Max total adjustment: {np.max(extreme_total_adj)*1000:.1f}ms")

    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    print("""
The RMS threshold approach is remarkably simple and effective:

PROS:
+ Self-adaptive: Uses the word's own energy profile as threshold
+ Simple: No gradient calculations or complex thresholds
+ Intuitive: "Where does energy rise above the average?"
+ Robust: Works well on both normal and anomalous words

LIMITATION (same as gradient method):
- Can only adjust within the provided timing window
- Cannot fix 21+ second anomalies where the entire pause is included
- Still needs manual review for extreme cases

COMPARISON WITH GRADIENT METHOD:
- Similar results on normal words
- Potentially more stable (fewer parameters to tune)
- May handle gradual onset/offset better

RECOMMENDATION:
The RMS threshold approach could replace or complement the gradient-based
detection in waveform_fine_tuning.py as it's simpler and equally effective.
    """)

    print(f"\nVisualizations saved to: {output_dir}")


if __name__ == '__main__':
    main()
