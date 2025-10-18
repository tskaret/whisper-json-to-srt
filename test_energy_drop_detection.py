"""
Energy Drop Detection for Word Boundaries

User insight: Look for energy DROPS to identify where words end
(and energy RISES for where words start)

Theory:
- Word START = significant energy RISE (silence → speech)
- Word END = significant energy DROP (speech → silence)
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


class EnergyDropDetector:
    """Detects word boundaries by finding energy rises and drops"""

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

    def detect_by_energy_drops(self, word: Word, sensitivity: str = 'high') -> Dict:
        """
        Detect word boundaries by finding energy rises (start) and drops (end)

        Args:
            sensitivity: 'low', 'medium', 'high' - how aggressive to detect drops
        """
        audio, seg_start = self.extract_segment(word.start, word.end, buffer=0.5)

        # Calculate RMS energy
        frame_length = int(0.005 * self.sr)  # 5ms
        hop_length = int(0.002 * self.sr)    # 2ms
        rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]

        # Smooth RMS to reduce noise
        rms_smooth = signal.savgol_filter(rms, window_length=min(11, len(rms)//2*2+1), polyorder=2)

        # Calculate derivative (rate of change)
        derivative = np.gradient(rms_smooth)

        # Find significant rises and drops
        if sensitivity == 'high':
            rise_threshold = np.percentile(derivative, 80)   # Top 20% of rises
            drop_threshold = np.percentile(derivative, 20)   # Bottom 20% (drops)
        elif sensitivity == 'medium':
            rise_threshold = np.percentile(derivative, 75)
            drop_threshold = np.percentile(derivative, 25)
        else:  # 'low'
            rise_threshold = np.percentile(derivative, 70)
            drop_threshold = np.percentile(derivative, 30)

        # Find peaks in derivative (for rises) and valleys (for drops)
        rises, _ = signal.find_peaks(derivative, height=rise_threshold, distance=5)
        drops, _ = signal.find_peaks(-derivative, height=-drop_threshold, distance=5)

        if len(rises) == 0 or len(drops) == 0:
            return {'success': False, 'method': 'energy_drops'}

        # Strategy: Find the steepest rise and steepest drop
        # that are within reasonable distance of expected word duration

        expected_duration = word.count_syllables() * 0.15
        min_duration = expected_duration * 0.5
        max_duration = expected_duration * 3.0

        best_start_idx = None
        best_end_idx = None
        best_score = 0

        # Try all combinations of rise + drop
        for rise_idx in rises:
            for drop_idx in drops:
                if drop_idx <= rise_idx:
                    continue  # End must be after start

                # Calculate duration
                duration = (drop_idx - rise_idx) * hop_length / self.sr

                # Check if duration is reasonable
                if duration < min_duration or duration > max_duration:
                    continue

                # Score based on:
                # 1. Steepness of rise and drop
                # 2. How close duration is to expected
                rise_strength = derivative[rise_idx]
                drop_strength = -derivative[drop_idx]
                duration_score = 1.0 - abs(duration - expected_duration) / expected_duration

                score = (rise_strength + drop_strength) * duration_score

                if score > best_score:
                    best_score = score
                    best_start_idx = rise_idx
                    best_end_idx = drop_idx

        if best_start_idx is None or best_end_idx is None:
            # Fallback: Use steepest rise and steepest drop regardless of duration
            best_start_idx = rises[np.argmax(derivative[rises])]
            best_end_idx = drops[np.argmax(-derivative[drops])]

        detected_start = seg_start + (best_start_idx * hop_length / self.sr)
        detected_end = seg_start + (best_end_idx * hop_length / self.sr)

        return {
            'method': 'energy_drops',
            'sensitivity': sensitivity,
            'detected_start': detected_start,
            'detected_end': detected_end,
            'detected_duration': detected_end - detected_start,
            'original_duration': word.duration,
            'start_adjustment': detected_start - word.start,
            'end_adjustment': detected_end - word.end,
            'rise_threshold': rise_threshold,
            'drop_threshold': drop_threshold,
            'num_rises': len(rises),
            'num_drops': len(drops),
            'best_score': best_score,
            'rms_smooth': rms_smooth,
            'derivative': derivative,
            'rises': rises,
            'drops': drops,
            'best_rise_idx': best_start_idx,
            'best_drop_idx': best_end_idx,
            'success': True
        }

    def visualize_energy_drops(self, word: Word, result: Dict, output_path: Path):
        """Visualize energy drop detection"""
        audio, seg_start = self.extract_segment(word.start, word.end, buffer=0.5)

        frame_length = int(0.005 * self.sr)
        hop_length = int(0.002 * self.sr)
        rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]

        audio_times = seg_start + np.arange(len(audio)) / self.sr
        rms_times = seg_start + np.arange(len(rms)) * hop_length / self.sr

        # Create figure with 3 panels
        fig, axes = plt.subplots(3, 1, figsize=(16, 10))
        fig.suptitle(f'Energy Drop Detection: "{word.text}" '
                    f'(expected: ~{word.count_syllables()*0.15:.3f}s)',
                    fontsize=14, fontweight='bold')

        # Panel 1: Waveform with boundaries
        ax1 = axes[0]
        ax1.plot(audio_times, audio, linewidth=0.5, color='gray', alpha=0.7)
        ax1.axvspan(word.start, word.end, alpha=0.2, color='red', label='Original')

        if result['success']:
            ax1.axvspan(result['detected_start'], result['detected_end'],
                       alpha=0.2, color='green', label='Detected')
            ax1.axvline(result['detected_start'], color='green', linestyle='-',
                       linewidth=2, label='Detected Start (Rise)')
            ax1.axvline(result['detected_end'], color='orange', linestyle='-',
                       linewidth=2, label='Detected End (Drop)')

        ax1.set_title('Waveform with Original and Detected Boundaries', fontweight='bold')
        ax1.set_ylabel('Amplitude')
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim(audio_times[0], audio_times[-1])

        # Panel 2: RMS Energy (smoothed)
        ax2 = axes[1]
        ax2.plot(rms_times, rms, linewidth=0.5, color='blue', alpha=0.3, label='RMS (raw)')
        ax2.plot(rms_times, result['rms_smooth'], linewidth=1.5, color='blue',
                label='RMS (smoothed)')

        if result['success']:
            # Mark detected boundaries
            ax2.axvline(result['detected_start'], color='green', linestyle='-',
                       linewidth=2, alpha=0.7)
            ax2.axvline(result['detected_end'], color='orange', linestyle='-',
                       linewidth=2, alpha=0.7)

        # Mark original boundaries
        ax2.axvline(word.start, color='red', linestyle='--', linewidth=1, alpha=0.5)
        ax2.axvline(word.end, color='red', linestyle='--', linewidth=1, alpha=0.5)

        ax2.set_title('RMS Energy (Smoothed)', fontweight='bold')
        ax2.set_ylabel('RMS Energy')
        ax2.legend(loc='upper right')
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim(audio_times[0], audio_times[-1])

        # Panel 3: Derivative (showing rises and drops)
        ax3 = axes[2]
        ax3.plot(rms_times, result['derivative'], linewidth=1, color='purple',
                label='Energy derivative')
        ax3.axhline(0, color='black', linestyle='-', linewidth=0.5)
        ax3.axhline(result['rise_threshold'], color='green', linestyle='--',
                   linewidth=1, label=f"Rise threshold")
        ax3.axhline(result['drop_threshold'], color='orange', linestyle='--',
                   linewidth=1, label=f"Drop threshold")

        # Mark all rises and drops
        for rise_idx in result['rises']:
            time = seg_start + (rise_idx * hop_length / self.sr)
            ax3.axvline(time, color='green', alpha=0.2, linewidth=0.5)

        for drop_idx in result['drops']:
            time = seg_start + (drop_idx * hop_length / self.sr)
            ax3.axvline(time, color='orange', alpha=0.2, linewidth=0.5)

        # Mark the chosen rise and drop
        if result['success']:
            best_rise_time = seg_start + (result['best_rise_idx'] * hop_length / self.sr)
            best_drop_time = seg_start + (result['best_drop_idx'] * hop_length / self.sr)

            ax3.axvline(best_rise_time, color='green', linestyle='-',
                       linewidth=2, label='Chosen Rise')
            ax3.axvline(best_drop_time, color='orange', linestyle='-',
                       linewidth=2, label='Chosen Drop')

        ax3.set_title('Energy Derivative (Positive=Rise, Negative=Drop)', fontweight='bold')
        ax3.set_xlabel('Time (seconds)')
        ax3.set_ylabel('Rate of Change')
        ax3.legend(loc='upper right', fontsize=8)
        ax3.grid(True, alpha=0.3)
        ax3.set_xlim(audio_times[0], audio_times[-1])

        # Add statistics
        stats_text = (
            f"Original: {word.duration:.3f}s\n"
            f"Detected: {result['detected_duration']:.3f}s\n"
            f"Start Δ: {result['start_adjustment']*1000:+.1f}ms\n"
            f"End Δ: {result['end_adjustment']*1000:+.1f}ms\n"
            f"Rises found: {result['num_rises']}\n"
            f"Drops found: {result['num_drops']}\n"
            f"Sensitivity: {result['sensitivity']}"
        )
        fig.text(0.02, 0.02, stats_text, fontsize=10, family='monospace',
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

        plt.tight_layout(rect=[0, 0.08, 1, 0.97])
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()


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
    print("ENERGY DROP DETECTION - Finding Rises and Drops")
    print("="*70)

    # Test on extreme anomalies
    words_extreme = load_words(json_path, 490, 545)
    print(f"\nLoaded {len(words_extreme)} words from extreme anomaly segment")

    detector = EnergyDropDetector(audio_path)

    output_dir = Path("energy_drop_test")
    output_dir.mkdir(exist_ok=True)

    # Test different sensitivity levels
    sensitivities = ['high', 'medium', 'low']

    print("\n" + "-"*70)
    print("Testing Energy Drop Detection on Extreme Anomalies")
    print("-"*70)

    for i, word in enumerate(words_extreme, 1):
        expected = word.count_syllables() * 0.15
        print(f"\n[{i}] '{word.text}' (original: {word.duration:.3f}s, expected: ~{expected:.3f}s)")

        for sens in sensitivities:
            result = detector.detect_by_energy_drops(word, sensitivity=sens)

            if result['success']:
                print(f"  {sens:8s}: {result['detected_duration']:.3f}s "
                      f"(start: {result['start_adjustment']*1000:+.0f}ms, "
                      f"end: {result['end_adjustment']*1000:+.0f}ms)")

        # Visualize with high sensitivity
        result_high = detector.detect_by_energy_drops(word, sensitivity='high')
        viz_path = output_dir / f"drop_{i}_{word.text.strip('.,!?')}.png"
        detector.visualize_energy_drops(word, result_high, viz_path)
        print(f"  Visualization: {viz_path.name}")

    # Focus on "ut." word
    ut_word = next((w for w in words_extreme if w.text == 'ut.'), None)
    if ut_word:
        print("\n" + "="*70)
        print("DETAILED ANALYSIS: 'ut.' word (21.364s anomaly)")
        print("="*70)

        for sens in sensitivities:
            result = detector.detect_by_energy_drops(ut_word, sensitivity=sens)
            print(f"\nSensitivity: {sens.upper()}")
            print(f"  Detected duration: {result['detected_duration']:.3f}s")
            print(f"  Rises detected: {result['num_rises']}")
            print(f"  Drops detected: {result['num_drops']}")
            print(f"  Start adjustment: {result['start_adjustment']*1000:+.1f}ms")
            print(f"  End adjustment: {result['end_adjustment']*1000:+.1f}ms")

    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    print("""
Energy Drop Detection looks for:
- RISES in energy (silence -> speech) to find word START
- DROPS in energy (speech -> silence) to find word END

This directly addresses what humans see when looking at waveforms!

Review the visualizations in energy_drop_test/ to see:
- Panel 1: Waveform with detected boundaries
- Panel 2: RMS energy curve
- Panel 3: Energy derivative showing all rises/drops and the chosen ones

The bottom panel shows the "signature" of speech - rises and drops in energy.
This should match what you visually identified in the waveform!
    """)

    print(f"\nVisualizations saved to: {output_dir}/")


if __name__ == '__main__':
    main()
