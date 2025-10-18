#!/usr/bin/env python3
"""
Analyze what happened to 'var' and 'inne i bildet' around 3824s
"""

import json
import numpy as np
import librosa
import matplotlib.pyplot as plt
from scipy import signal


def analyze_var_region():
    """Analyze the region around 'var' at 3824s"""

    # Load audio
    audio_path = r"d:\stevner\2025\regionalt\Lørdag\04-LørdagEttermiddag\04-LørdagEttermiddag.mp3"
    print(f"Loading audio...")
    audio, sr = librosa.load(audio_path, sr=16000, mono=True)

    # Extract region around "var" through "bildet."
    start_time = 3824.0
    end_time = 3826.0

    start_sample = int(start_time * sr)
    end_sample = int(end_time * sr)
    segment = audio[start_sample:end_sample]

    # Calculate RMS
    frame_length = int(0.005 * sr)
    hop_length = int(0.002 * sr)
    rms = librosa.feature.rms(y=segment, frame_length=frame_length, hop_length=hop_length)[0]

    # Smooth
    window_len = min(11, len(rms) // 2 * 2 + 1)
    rms_smooth = signal.savgol_filter(rms, window_length=window_len, polyorder=2)

    # Derivative
    derivative = np.gradient(rms_smooth)

    # Time arrays
    audio_times = start_time + np.arange(len(segment)) / sr
    rms_times = start_time + np.arange(len(rms_smooth)) * hop_length / sr

    # Original word boundaries
    words = [
        ("Jesus", 3824.138, 3824.518),
        ("var", 3824.538, 3824.678),
        ("inne", 3824.698, 3824.779),
        ("i", 3824.839, 3824.859),
        ("bildet.", 3824.899, 3825.199),
        ("Begrepet", 3825.840, 3826.340),
    ]

    # Create visualization
    fig, axes = plt.subplots(3, 1, figsize=(16, 12))
    fig.suptitle('Analysis: "var" and "inne i bildet" Region', fontsize=16, fontweight='bold')

    # Panel 1: Waveform
    ax1 = axes[0]
    ax1.plot(audio_times, segment, linewidth=0.5, color='gray')
    ax1.fill_between(audio_times, segment, color='lightgray', alpha=0.3)

    colors = ['red', 'orange', 'yellow', 'green', 'blue', 'purple']
    for (word, w_start, w_end), color in zip(words, colors):
        ax1.axvspan(w_start, w_end, alpha=0.2, color=color, label=f'"{word}"')
        ax1.axvline(w_start, color=color, linestyle='--', linewidth=1.5, alpha=0.7)
        ax1.axvline(w_end, color=color, linestyle='--', linewidth=1.5, alpha=0.7)

    # Mark where subtitle ends (from user report: 01:03:52,653 = 3832.653)
    # Actually that's way later, let me focus on immediate area

    ax1.set_title('Waveform with Original Word Boundaries', fontsize=13, fontweight='bold')
    ax1.set_ylabel('Amplitude', fontsize=11)
    ax1.legend(loc='upper right', fontsize=8, ncol=3)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(audio_times[0], audio_times[-1])

    # Panel 2: RMS Energy
    ax2 = axes[1]
    ax2.plot(rms_times, rms_smooth, linewidth=2, color='blue', label='RMS Energy')

    for (word, w_start, w_end), color in zip(words, colors):
        ax2.axvline(w_start, color=color, linestyle='--', linewidth=1.5, alpha=0.7)
        ax2.axvline(w_end, color=color, linestyle='--', linewidth=1.5, alpha=0.7)
        ax2.axvspan(w_start, w_end, alpha=0.15, color=color)

    ax2.set_title('RMS Energy', fontsize=13, fontweight='bold')
    ax2.set_ylabel('Energy', fontsize=11)
    ax2.legend(loc='upper right', fontsize=9)
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(audio_times[0], audio_times[-1])

    # Panel 3: Derivative
    ax3 = axes[2]
    ax3.plot(rms_times, derivative, linewidth=1.5, color='purple', label='Energy Derivative')
    ax3.axhline(0, color='black', linestyle='-', linewidth=0.8)

    # Mark thresholds
    rise_threshold = np.percentile(derivative, 80)
    drop_threshold = np.percentile(derivative, 20)
    ax3.axhline(rise_threshold, color='green', linestyle='--', linewidth=1.5, label='Rise Threshold')
    ax3.axhline(drop_threshold, color='orange', linestyle='--', linewidth=1.5, label='Drop Threshold')

    for (word, w_start, w_end), color in zip(words, colors):
        ax3.axvline(w_start, color=color, linestyle='--', linewidth=1.5, alpha=0.7)
        ax3.axvline(w_end, color=color, linestyle='--', linewidth=1.5, alpha=0.7)

    # Find all rises and drops
    rises, _ = signal.find_peaks(derivative, height=rise_threshold, distance=5)
    drops, _ = signal.find_peaks(-derivative, height=-drop_threshold, distance=5)

    for rise_idx in rises:
        ax3.plot(rms_times[rise_idx], derivative[rise_idx], 'g^', markersize=8, alpha=0.5)

    for drop_idx in drops:
        ax3.plot(rms_times[drop_idx], derivative[drop_idx], 'v', color='orange', markersize=8, alpha=0.5)

    ax3.set_title('Energy Derivative (Rises and Drops)', fontsize=13, fontweight='bold')
    ax3.set_xlabel('Time (seconds)', fontsize=11, fontweight='bold')
    ax3.set_ylabel('Rate of Change', fontsize=11)
    ax3.legend(loc='upper right', fontsize=9)
    ax3.grid(True, alpha=0.3)
    ax3.set_xlim(audio_times[0], audio_times[-1])

    # Statistics
    var_start, var_end = 3824.538, 3824.678
    var_mask = (rms_times >= var_start) & (rms_times <= var_end)
    var_energy = np.mean(rms_smooth[var_mask]) if np.any(var_mask) else 0

    bildet_start, bildet_end = 3824.899, 3825.199
    bildet_mask = (rms_times >= bildet_start) & (rms_times <= bildet_end)
    bildet_energy = np.mean(rms_smooth[bildet_mask]) if np.any(bildet_mask) else 0

    gap_start, gap_end = 3825.199, 3825.840
    gap_mask = (rms_times >= gap_start) & (rms_times <= gap_end)
    gap_energy = np.mean(rms_smooth[gap_mask]) if np.any(gap_mask) else 0

    stats_text = (
        f"Word Durations:\n"
        f"  var: 0.140s (1 syllable, expected 0.15s)\n"
        f"  inne: 0.081s\n"
        f"  i: 0.020s (too short!)\n"
        f"  bildet.: 0.300s\n"
        f"  Gap after bildet.: 0.641s\n"
        f"\n"
        f"Average Energy:\n"
        f"  'var': {var_energy:.4f}\n"
        f"  'bildet.': {bildet_energy:.4f}\n"
        f"  Gap: {gap_energy:.4f}\n"
        f"\n"
        f"Rises found: {len(rises)}\n"
        f"Drops found: {len(drops)}"
    )

    fig.text(0.02, 0.02, stats_text, fontsize=10, family='monospace',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))

    plt.tight_layout(rect=[0, 0.15, 1, 0.97])
    plt.savefig('var_issue_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()

    print("\nAnalysis saved to: var_issue_analysis.png")
    print(f"\nStatistics:")
    print(stats_text)


if __name__ == "__main__":
    analyze_var_region()
