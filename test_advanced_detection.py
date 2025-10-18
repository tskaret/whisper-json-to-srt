"""
Advanced Detection Methods for Word Boundaries

Based on user insight: Humans can visually identify the correct word in the waveform,
so the information is there. We need smarter algorithms.

Methods to test:
1. Percentile-based threshold (use 75th percentile instead of mean)
2. Peak detection (find the concentrated energy region)
3. Sliding window maximum (find window with highest average energy)
4. Energy clustering (group consecutive high-energy frames)
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import librosa
from pathlib import Path
from typing import List, Tuple, Dict
from dataclasses import dataclass
from scipy import signal


@dataclass
class Word:
    text: str
    start: float
    end: float
    score: float
    speaker: str

    @property
    def duration(self):
        return self.end - self.start

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


class AdvancedDetector:
    """Advanced detection methods for word boundaries"""

    def __init__(self, audio_path: str, sr: int = 16000):
        print(f"Loading audio: {audio_path}")
        self.audio, self.sr = librosa.load(audio_path, sr=sr, mono=True)
        print(f"Audio loaded: {len(self.audio)/sr:.1f}s, sr={sr}Hz")

    def extract_segment(self, start: float, end: float,
                       buffer: float = 0.5) -> Tuple[np.ndarray, float]:
        """Extract audio segment with buffer"""
        actual_start = max(0, start - buffer)
        actual_end = min(len(self.audio) / self.sr, end + buffer)
        start_sample = int(actual_start * self.sr)
        end_sample = int(actual_end * self.sr)
        segment = self.audio[start_sample:end_sample]
        return segment, actual_start

    def method1_percentile_threshold(self, word: Word, percentile: float = 75) -> Dict:
        """
        Method 1: Use percentile instead of mean
        Theory: Speech is a minority of frames, so 75th percentile better represents
        the boundary between silence and speech
        """
        audio, seg_start = self.extract_segment(word.start, word.end, buffer=0.5)

        frame_length = int(0.005 * self.sr)
        hop_length = int(0.002 * self.sr)
        rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]

        # Use percentile instead of mean
        threshold = np.percentile(rms, percentile)

        # Find first/last above threshold
        above_threshold = rms > threshold
        if not any(above_threshold):
            return {'success': False, 'method': 'percentile'}

        first_idx = np.argmax(above_threshold)
        last_idx = len(above_threshold) - 1 - np.argmax(above_threshold[::-1])

        detected_start = seg_start + (first_idx * hop_length / self.sr)
        detected_end = seg_start + (last_idx * hop_length / self.sr)

        return {
            'method': 'percentile',
            'detected_start': detected_start,
            'detected_end': detected_end,
            'detected_duration': detected_end - detected_start,
            'threshold': threshold,
            'percentile': percentile,
            'success': True
        }

    def method2_peak_detection(self, word: Word) -> Dict:
        """
        Method 2: Find the peak energy region
        Theory: Speech is the region with maximum concentrated energy
        """
        audio, seg_start = self.extract_segment(word.start, word.end, buffer=0.5)

        frame_length = int(0.005 * self.sr)
        hop_length = int(0.002 * self.sr)
        rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]

        # Find the peak
        peak_idx = np.argmax(rms)
        peak_energy = rms[peak_idx]

        # Use 40% of peak as threshold (speech should be above this)
        threshold = peak_energy * 0.4

        # Find continuous region around peak that stays above threshold
        above_threshold = rms > threshold

        # Find the continuous region containing the peak
        first_idx = peak_idx
        while first_idx > 0 and above_threshold[first_idx - 1]:
            first_idx -= 1

        last_idx = peak_idx
        while last_idx < len(above_threshold) - 1 and above_threshold[last_idx + 1]:
            last_idx += 1

        detected_start = seg_start + (first_idx * hop_length / self.sr)
        detected_end = seg_start + (last_idx * hop_length / self.sr)

        return {
            'method': 'peak_detection',
            'detected_start': detected_start,
            'detected_end': detected_end,
            'detected_duration': detected_end - detected_start,
            'threshold': threshold,
            'peak_energy': peak_energy,
            'success': True
        }

    def method3_sliding_window(self, word: Word, window_duration: float = None) -> Dict:
        """
        Method 3: Sliding window to find highest energy concentration
        Theory: Find the time window that contains the most energy
        """
        audio, seg_start = self.extract_segment(word.start, word.end, buffer=0.5)

        frame_length = int(0.005 * self.sr)
        hop_length = int(0.002 * self.sr)
        rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]

        # Use expected duration as window size
        if window_duration is None:
            expected_duration = word.count_syllables() * 0.15
            window_duration = max(0.1, min(expected_duration * 2, word.duration * 0.5))

        window_frames = int(window_duration / (hop_length / self.sr))
        window_frames = max(5, min(window_frames, len(rms) // 2))

        # Find window with maximum average energy
        max_avg = 0
        max_idx = 0

        for i in range(len(rms) - window_frames + 1):
            window_avg = np.mean(rms[i:i + window_frames])
            if window_avg > max_avg:
                max_avg = window_avg
                max_idx = i

        detected_start = seg_start + (max_idx * hop_length / self.sr)
        detected_end = seg_start + ((max_idx + window_frames) * hop_length / self.sr)

        return {
            'method': 'sliding_window',
            'detected_start': detected_start,
            'detected_end': detected_end,
            'detected_duration': detected_end - detected_start,
            'window_duration': window_duration,
            'max_energy': max_avg,
            'success': True
        }

    def method4_energy_clustering(self, word: Word) -> Dict:
        """
        Method 4: Cluster high-energy frames and find largest cluster
        Theory: Speech forms a continuous cluster of high-energy frames
        """
        audio, seg_start = self.extract_segment(word.start, word.end, buffer=0.5)

        frame_length = int(0.005 * self.sr)
        hop_length = int(0.002 * self.sr)
        rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]

        # Use high percentile as threshold (speech is in top energy frames)
        threshold = np.percentile(rms, 85)

        above_threshold = rms > threshold

        # Find all clusters (continuous regions above threshold)
        clusters = []
        in_cluster = False
        cluster_start = 0

        for i, val in enumerate(above_threshold):
            if val and not in_cluster:
                cluster_start = i
                in_cluster = True
            elif not val and in_cluster:
                clusters.append((cluster_start, i - 1))
                in_cluster = False

        if in_cluster:
            clusters.append((cluster_start, len(above_threshold) - 1))

        if not clusters:
            return {'success': False, 'method': 'energy_clustering'}

        # Find cluster with highest total energy
        best_cluster = max(clusters, key=lambda c: np.sum(rms[c[0]:c[1]+1]))

        detected_start = seg_start + (best_cluster[0] * hop_length / self.sr)
        detected_end = seg_start + (best_cluster[1] * hop_length / self.sr)

        return {
            'method': 'energy_clustering',
            'detected_start': detected_start,
            'detected_end': detected_end,
            'detected_duration': detected_end - detected_start,
            'num_clusters': len(clusters),
            'threshold': threshold,
            'success': True
        }

    def visualize_all_methods(self, word: Word, output_path: Path):
        """Compare all detection methods visually"""
        methods = [
            ('Percentile (75%)', self.method1_percentile_threshold(word)),
            ('Peak Detection', self.method2_peak_detection(word)),
            ('Sliding Window', self.method3_sliding_window(word)),
            ('Energy Clustering', self.method4_energy_clustering(word))
        ]

        audio, seg_start = self.extract_segment(word.start, word.end, buffer=0.5)
        frame_length = int(0.005 * self.sr)
        hop_length = int(0.002 * self.sr)
        rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]

        audio_times = seg_start + np.arange(len(audio)) / self.sr
        rms_times = seg_start + np.arange(len(rms)) * hop_length / self.sr

        # Create figure with 5 subplots
        fig, axes = plt.subplots(5, 1, figsize=(16, 14))
        fig.suptitle(f'Detection Methods Comparison: "{word.text}" '
                    f'({word.count_syllables()} syl, orig: {word.duration:.3f}s)',
                    fontsize=14, fontweight='bold')

        colors = ['orange', 'green', 'purple', 'cyan']

        # Top panel: Waveform with all detections
        ax = axes[0]
        ax.plot(audio_times, audio, linewidth=0.5, color='gray', alpha=0.7)
        ax.axvspan(word.start, word.end, alpha=0.15, color='red', label='Original')

        for (name, result), color in zip(methods, colors):
            if result.get('success', False):
                ax.axvspan(result['detected_start'], result['detected_end'],
                          alpha=0.2, color=color, label=name[:15])

        ax.set_title('Waveform with All Detection Methods', fontweight='bold')
        ax.set_ylabel('Amplitude')
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(audio_times[0], audio_times[-1])

        # Individual method panels
        for i, ((name, result), color) in enumerate(zip(methods, colors), 1):
            ax = axes[i]
            ax.plot(rms_times, rms, linewidth=1, color='blue', alpha=0.5)

            if result.get('success', False):
                # Highlight detected region
                ax.axvspan(result['detected_start'], result['detected_end'],
                          alpha=0.3, color=color)
                ax.axvline(result['detected_start'], color=color, linestyle='-', linewidth=2)
                ax.axvline(result['detected_end'], color=color, linestyle='-', linewidth=2)

                # Show threshold if available
                if 'threshold' in result:
                    ax.axhline(result['threshold'], color='red', linestyle='--',
                              linewidth=1, alpha=0.7, label=f"Threshold")

                duration = result['detected_duration']
                ax.set_title(f"{name}: {duration:.3f}s "
                           f"(Δ start:{(result['detected_start']-word.start)*1000:+.0f}ms, "
                           f"end:{(result['detected_end']-word.end)*1000:+.0f}ms)",
                           fontweight='bold')
            else:
                ax.set_title(f"{name}: FAILED", fontweight='bold')

            ax.axvline(word.start, color='red', linestyle='--', linewidth=1, alpha=0.5)
            ax.axvline(word.end, color='red', linestyle='--', linewidth=1, alpha=0.5)
            ax.set_ylabel('RMS Energy')
            ax.grid(True, alpha=0.3)
            ax.set_xlim(audio_times[0], audio_times[-1])

        axes[-1].set_xlabel('Time (seconds)')

        plt.tight_layout(rect=[0, 0, 1, 0.98])
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  Saved: {output_path.name}")


def load_words(json_path: str, start_time: float, end_time: float) -> List[Word]:
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
            if word.start >= start_time and word.end <= end_time:
                words.append(word)

    return words


def main():
    audio_path = r"d:\stevner\2025\regionalt\Lørdag\04-LørdagEttermiddag\04-LørdagEttermiddag.mp3"
    json_path = "04-LørdagEttermiddag.json"

    print("\n" + "="*70)
    print("ADVANCED DETECTION METHODS - Finding What Humans Can See")
    print("="*70)

    # Test on extreme anomalies
    words_extreme = load_words(json_path, 490, 545)
    print(f"\nLoaded {len(words_extreme)} words from extreme anomaly segment")

    detector = AdvancedDetector(audio_path)

    output_dir = Path("advanced_detection_test")
    output_dir.mkdir(exist_ok=True)

    print("\n" + "-"*70)
    print("Testing All Methods on Extreme Anomalies")
    print("-"*70)

    results_table = []

    for i, word in enumerate(words_extreme, 1):
        print(f"\n[{i}] '{word.text}' (original: {word.duration:.3f}s, expected: ~{word.count_syllables()*0.15:.3f}s)")

        # Test all methods
        result1 = detector.method1_percentile_threshold(word)
        result2 = detector.method2_peak_detection(word)
        result3 = detector.method3_sliding_window(word)
        result4 = detector.method4_energy_clustering(word)

        print(f"  Percentile:     {result1['detected_duration']:.3f}s")
        print(f"  Peak Detection: {result2['detected_duration']:.3f}s")
        print(f"  Sliding Window: {result3['detected_duration']:.3f}s")
        print(f"  Energy Cluster: {result4['detected_duration']:.3f}s")

        results_table.append({
            'word': word,
            'percentile': result1,
            'peak': result2,
            'sliding': result3,
            'cluster': result4
        })

        # Create comparison visualization
        viz_path = output_dir / f"compare_{i}_{word.text.strip('.,!?')}.png"
        detector.visualize_all_methods(word, viz_path)

    # Summary comparison
    print("\n" + "="*70)
    print("SUMMARY - Which Method Best Finds the Actual Word?")
    print("="*70)

    print(f"\n{'Word':<15} {'Original':<12} {'Percentile':<12} {'Peak':<12} {'Sliding':<12} {'Cluster':<12}")
    print("-"*90)

    for res in results_table:
        word = res['word']
        expected = word.count_syllables() * 0.15

        print(f"{word.text:<15} "
              f"{word.duration:>10.3f}s "
              f"{res['percentile']['detected_duration']:>10.3f}s "
              f"{res['peak']['detected_duration']:>10.3f}s "
              f"{res['sliding']['detected_duration']:>10.3f}s "
              f"{res['cluster']['detected_duration']:>10.3f}s")

        # Show expected for reference
        print(f"{'  (expected ~'+str(expected)+'s)':>27}")

    print("\n" + "="*70)
    print("RECOMMENDATION")
    print("="*70)
    print("""
Based on visual inspection of the generated comparison images, identify which
method best matches what you visually identified as the correct word boundary.

LIKELY WINNER: Sliding Window or Peak Detection
- These methods look for CONCENTRATED energy regions
- Less affected by long silence periods
- Better match human visual perception

Next step: Review the comparison visualizations in advanced_detection_test/
and let me know which method(s) work best!
    """)

    print(f"\nVisualizations saved to: {output_dir}/")


if __name__ == '__main__':
    main()
