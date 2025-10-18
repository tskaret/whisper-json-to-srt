#!/usr/bin/env python3
"""
Analyze Energy Detection for a Specific Word

Shows detailed visualization of what the energy drop algorithm sees:
- Waveform
- RMS energy curve
- Energy derivative (rises and drops)
- Detection points
"""

import json
import numpy as np
import librosa
import matplotlib.pyplot as plt
from scipy import signal
from pathlib import Path


def count_syllables(word: str) -> int:
    """Count syllables using vowel groups"""
    import re
    vowels = 'aeiouyæøå'
    clean_word = re.sub(r'[^\w]', '', word)
    vowel_groups = re.findall(rf'[{vowels}]+', clean_word.lower())
    return max(1, len(vowel_groups))


def analyze_word_energy(audio_path: str, word_text: str,
                        start: float, end: float,
                        sensitivity: str = 'high',
                        output_path: str = 'energy_analysis.png'):
    """Analyze energy detection for a specific word"""

    # Load audio
    print(f"Loading audio: {audio_path}")
    audio, sr = librosa.load(audio_path, sr=16000, mono=True)
    print(f"Audio loaded: {len(audio)/sr:.1f}s")

    # Extract segment with buffer
    buffer = 0.5
    actual_start = max(0, start - buffer)
    actual_end = min(len(audio) / sr, end + buffer)
    start_sample = int(actual_start * sr)
    end_sample = int(actual_end * sr)
    segment = audio[start_sample:end_sample]

    # Calculate RMS energy
    frame_length = int(0.005 * sr)  # 5ms
    hop_length = int(0.002 * sr)    # 2ms
    rms = librosa.feature.rms(y=segment, frame_length=frame_length, hop_length=hop_length)[0]

    # Smooth RMS
    window_len = min(11, len(rms) // 2 * 2 + 1)
    if window_len < 3:
        print("Segment too short")
        return

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
    else:  # 'low'
        rise_threshold = np.percentile(derivative, 70)
        drop_threshold = np.percentile(derivative, 30)

    rises, _ = signal.find_peaks(derivative, height=rise_threshold, distance=5)
    drops, _ = signal.find_peaks(-derivative, height=-drop_threshold, distance=5)

    # Time arrays
    audio_times = actual_start + np.arange(len(segment)) / sr
    rms_times = actual_start + np.arange(len(rms_smooth)) * hop_length / sr

    # Find best rise/drop pair (same logic as in corrector)
    expected_duration = count_syllables(word_text) * 0.15
    min_duration = expected_duration * 0.5
    max_duration = expected_duration * 3.0

    best_start_idx = None
    best_end_idx = None
    best_score = 0

    for rise_idx in rises:
        for drop_idx in drops:
            if drop_idx <= rise_idx:
                continue

            duration = (drop_idx - rise_idx) * hop_length / sr

            if duration < min_duration or duration > max_duration:
                continue

            rise_strength = derivative[rise_idx]
            drop_strength = -derivative[drop_idx]
            duration_score = 1.0 - abs(duration - expected_duration) / expected_duration

            score = (rise_strength + drop_strength) * duration_score

            if score > best_score:
                best_score = score
                best_start_idx = rise_idx
                best_end_idx = drop_idx

    if best_start_idx is None or best_end_idx is None:
        # Fallback
        best_start_idx = rises[np.argmax(derivative[rises])] if len(rises) > 0 else 0
        best_end_idx = drops[np.argmax(-derivative[drops])] if len(drops) > 0 else len(derivative) - 1

    detected_start = actual_start + (best_start_idx * hop_length / sr)
    detected_end = actual_start + (best_end_idx * hop_length / sr)

    # Create detailed visualization
    fig, axes = plt.subplots(3, 1, figsize=(16, 12))
    fig.suptitle(f'Energy Detection Analysis: "{word_text}" (Expected: ~{expected_duration:.3f}s)',
                fontsize=16, fontweight='bold')

    # Panel 1: Waveform with boundaries
    ax1 = axes[0]
    ax1.plot(audio_times, segment, linewidth=0.5, color='gray', alpha=0.7)
    ax1.fill_between(audio_times, segment, color='lightgray', alpha=0.3)

    # Original timing (red)
    ax1.axvspan(start, end, alpha=0.15, color='red', label='Original (WhisperX)')
    ax1.axvline(start, color='red', linestyle='--', linewidth=2, alpha=0.8, label='Original Start')
    ax1.axvline(end, color='red', linestyle='--', linewidth=2, alpha=0.8)

    # Detected timing (green)
    ax1.axvspan(detected_start, detected_end, alpha=0.2, color='green', label='Energy-Detected')
    ax1.axvline(detected_start, color='green', linestyle='-', linewidth=3, label='Detected Start (Rise)')
    ax1.axvline(detected_end, color='orange', linestyle='-', linewidth=3, label='Detected End (Drop)')

    ax1.set_title('Waveform with Detection Results', fontsize=13, fontweight='bold')
    ax1.set_ylabel('Amplitude', fontsize=11)
    ax1.legend(loc='upper right', fontsize=9)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(audio_times[0], audio_times[-1])

    # Panel 2: RMS Energy (smoothed)
    ax2 = axes[1]
    ax2.plot(rms_times, rms, linewidth=0.8, color='blue', alpha=0.3, label='RMS (raw)')
    ax2.plot(rms_times, rms_smooth, linewidth=2, color='blue', label='RMS (smoothed)')

    # Mark original boundaries
    ax2.axvline(start, color='red', linestyle='--', linewidth=1.5, alpha=0.7, label='Original Start')
    ax2.axvline(end, color='red', linestyle='--', linewidth=1.5, alpha=0.7)

    # Mark detected boundaries
    ax2.axvline(detected_start, color='green', linestyle='-', linewidth=2.5)
    ax2.axvline(detected_end, color='orange', linestyle='-', linewidth=2.5)

    # Highlight the chosen rise and drop points
    if best_start_idx is not None:
        ax2.plot(rms_times[best_start_idx], rms_smooth[best_start_idx],
                'go', markersize=12, label='Chosen Rise Point')
    if best_end_idx is not None:
        ax2.plot(rms_times[best_end_idx], rms_smooth[best_end_idx],
                'o', color='orange', markersize=12, label='Chosen Drop Point')

    ax2.set_title('RMS Energy Curve', fontsize=13, fontweight='bold')
    ax2.set_ylabel('RMS Energy', fontsize=11)
    ax2.legend(loc='upper right', fontsize=9)
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(audio_times[0], audio_times[-1])

    # Panel 3: Energy Derivative (showing rises and drops)
    ax3 = axes[2]
    ax3.plot(rms_times, derivative, linewidth=1.5, color='purple', label='Energy Derivative')
    ax3.axhline(0, color='black', linestyle='-', linewidth=0.8)
    ax3.axhline(rise_threshold, color='green', linestyle='--', linewidth=1.5,
               label=f'Rise Threshold ({sensitivity})')
    ax3.axhline(drop_threshold, color='orange', linestyle='--', linewidth=1.5,
               label=f'Drop Threshold ({sensitivity})')

    # Mark ALL detected rises (positive peaks above threshold)
    for rise_idx in rises:
        rise_time = rms_times[rise_idx]
        ax3.axvline(rise_time, color='green', alpha=0.2, linewidth=1)
        ax3.plot(rise_time, derivative[rise_idx], 'g^', markersize=8, alpha=0.5)

    # Mark ALL detected drops (negative peaks below threshold)
    for drop_idx in drops:
        drop_time = rms_times[drop_idx]
        ax3.axvline(drop_time, color='orange', alpha=0.2, linewidth=1)
        ax3.plot(drop_time, derivative[drop_idx], 'v', color='orange', markersize=8, alpha=0.5)

    # Highlight the CHOSEN rise and drop
    if best_start_idx is not None:
        best_rise_time = rms_times[best_start_idx]
        ax3.axvline(best_rise_time, color='green', linestyle='-', linewidth=3, alpha=0.8)
        ax3.plot(best_rise_time, derivative[best_start_idx], 'g^',
                markersize=15, label='Chosen Rise', zorder=10)

    if best_end_idx is not None:
        best_drop_time = rms_times[best_end_idx]
        ax3.axvline(best_drop_time, color='orange', linestyle='-', linewidth=3, alpha=0.8)
        ax3.plot(best_drop_time, derivative[best_end_idx], 'v',
                color='orange', markersize=15, label='Chosen Drop', zorder=10)

    # Mark original start
    ax3.axvline(start, color='red', linestyle='--', linewidth=1.5, alpha=0.7,
               label='Original Start')

    ax3.set_title('Energy Derivative (Positive=Rise, Negative=Drop)',
                 fontsize=13, fontweight='bold')
    ax3.set_xlabel('Time (seconds)', fontsize=11, fontweight='bold')
    ax3.set_ylabel('Rate of Change', fontsize=11)
    ax3.legend(loc='upper right', fontsize=9)
    ax3.grid(True, alpha=0.3)
    ax3.set_xlim(audio_times[0], audio_times[-1])

    # Add statistics
    stats_text = (
        f"Original: {start:.3f}s - {end:.3f}s ({end-start:.3f}s)\n"
        f"Detected: {detected_start:.3f}s - {detected_end:.3f}s ({detected_end-detected_start:.3f}s)\n"
        f"Start Shift: {(detected_start-start)*1000:+.0f}ms\n"
        f"Rises Found: {len(rises)}\n"
        f"Drops Found: {len(drops)}\n"
        f"Sensitivity: {sensitivity}"
    )

    fig.text(0.02, 0.02, stats_text, fontsize=11, family='monospace',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))

    plt.tight_layout(rect=[0, 0.08, 1, 0.97])
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"\nAnalysis saved to: {output_path}")
    print(f"\nResults:")
    print(f"  Original Start: {start:.3f}s")
    print(f"  Detected Start: {detected_start:.3f}s")
    print(f"  Start Shift: {(detected_start-start)*1000:+.0f}ms")
    print(f"  Rises Detected: {len(rises)}")
    print(f"  Drops Detected: {len(drops)}")


if __name__ == "__main__":
    # Analyze the "117." word
    audio_path = r"d:\stevner\2025\regionalt\Lørdag\04-LørdagEttermiddag\04-LørdagEttermiddag.mp3"

    # Word "117." from example 18
    word_text = "117."
    original_start = 6392.336
    original_end = 6409.480

    analyze_word_energy(
        audio_path,
        word_text,
        original_start,
        original_end,
        sensitivity='high',
        output_path='energy_analysis_117.png'
    )
