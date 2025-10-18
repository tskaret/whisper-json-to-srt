#!/usr/bin/env python3
"""
Analyze the pause region around 6395-6399s

Shows what energy detection sees during the long pause
"""

import numpy as np
import librosa
import matplotlib.pyplot as plt
from scipy import signal


def analyze_pause_region(audio_path: str, start: float, end: float,
                         output_path: str = 'pause_analysis.png'):
    """Analyze energy in a specific region"""

    # Load audio
    print(f"Loading audio: {audio_path}")
    audio, sr = librosa.load(audio_path, sr=16000, mono=True)
    print(f"Audio loaded: {len(audio)/sr:.1f}s")

    # Extract segment
    buffer = 2.0  # More buffer to see context
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
    rms_smooth = signal.savgol_filter(rms, window_length=window_len, polyorder=2)

    # Calculate derivative
    derivative = np.gradient(rms_smooth)

    # Time arrays
    audio_times = actual_start + np.arange(len(segment)) / sr
    rms_times = actual_start + np.arange(len(rms_smooth)) * hop_length / sr

    # Create visualization
    fig, axes = plt.subplots(3, 1, figsize=(16, 10))
    fig.suptitle(f'Pause Region Analysis: {start:.1f}s - {end:.1f}s',
                fontsize=16, fontweight='bold')

    # Panel 1: Waveform
    ax1 = axes[0]
    ax1.plot(audio_times, segment, linewidth=0.5, color='gray')
    ax1.fill_between(audio_times, segment, color='lightgray', alpha=0.3)

    # Highlight the pause region
    ax1.axvspan(start, end, alpha=0.2, color='yellow', label='Pause Region')

    # Mark original word boundaries
    ax1.axvline(6392.336, color='red', linestyle='--', linewidth=2,
               label='Original Word Start', alpha=0.7)
    ax1.axvline(6409.480, color='red', linestyle='--', linewidth=2,
               label='Original Word End', alpha=0.7)

    ax1.set_title('Waveform with Pause Region Highlighted', fontsize=13, fontweight='bold')
    ax1.set_ylabel('Amplitude', fontsize=11)
    ax1.legend(loc='upper right', fontsize=9)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(audio_times[0], audio_times[-1])

    # Panel 2: RMS Energy (zoomed to see detail)
    ax2 = axes[1]
    ax2.plot(rms_times, rms, linewidth=0.8, color='blue', alpha=0.4, label='RMS (raw)')
    ax2.plot(rms_times, rms_smooth, linewidth=2, color='blue', label='RMS (smoothed)')

    # Highlight the pause region
    ax2.axvspan(start, end, alpha=0.2, color='yellow')

    # Calculate mean/max energy in pause region
    pause_mask = (rms_times >= start) & (rms_times <= end)
    pause_energy = rms_smooth[pause_mask]

    if len(pause_energy) > 0:
        mean_pause_energy = np.mean(pause_energy)
        max_pause_energy = np.max(pause_energy)

        ax2.axhline(mean_pause_energy, color='orange', linestyle='--', linewidth=1.5,
                   label=f'Mean Pause Energy: {mean_pause_energy:.4f}')

        # Show energy threshold for comparison
        overall_max = np.max(rms_smooth)
        threshold_10pct = overall_max * 0.1
        ax2.axhline(threshold_10pct, color='red', linestyle=':', linewidth=1.5,
                   label=f'10% of Max Energy: {threshold_10pct:.4f}')

    ax2.set_title('RMS Energy During Pause', fontsize=13, fontweight='bold')
    ax2.set_ylabel('RMS Energy', fontsize=11)
    ax2.legend(loc='upper right', fontsize=9)
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(audio_times[0], audio_times[-1])

    # Panel 3: Energy Derivative
    ax3 = axes[2]
    ax3.plot(rms_times, derivative, linewidth=1.5, color='purple', label='Energy Derivative')
    ax3.axhline(0, color='black', linestyle='-', linewidth=0.8)

    # Highlight the pause region
    ax3.axvspan(start, end, alpha=0.2, color='yellow')

    # Calculate derivative statistics in pause
    pause_deriv = derivative[pause_mask]
    if len(pause_deriv) > 0:
        max_rise_in_pause = np.max(pause_deriv)
        max_drop_in_pause = np.min(pause_deriv)

        ax3.axhline(max_rise_in_pause, color='green', linestyle=':', linewidth=1,
                   label=f'Max Rise in Pause: {max_rise_in_pause:.6f}')
        ax3.axhline(max_drop_in_pause, color='orange', linestyle=':', linewidth=1,
                   label=f'Max Drop in Pause: {max_drop_in_pause:.6f}')

    ax3.set_title('Energy Derivative During Pause', fontsize=13, fontweight='bold')
    ax3.set_xlabel('Time (seconds)', fontsize=11, fontweight='bold')
    ax3.set_ylabel('Rate of Change', fontsize=11)
    ax3.legend(loc='upper right', fontsize=9)
    ax3.grid(True, alpha=0.3)
    ax3.set_xlim(audio_times[0], audio_times[-1])

    # Add statistics box
    if len(pause_energy) > 0:
        stats_text = (
            f"Pause Region: {start:.1f}s - {end:.1f}s ({end-start:.1f}s)\n"
            f"Mean Energy: {mean_pause_energy:.6f}\n"
            f"Max Energy: {max_pause_energy:.6f}\n"
            f"Overall Max: {overall_max:.6f}\n"
            f"Pause/Max Ratio: {(mean_pause_energy/overall_max)*100:.1f}%\n"
            f"Max Rise: {max_rise_in_pause:.6f}\n"
            f"Max Drop: {max_drop_in_pause:.6f}"
        )
    else:
        stats_text = "No data in pause region"

    fig.text(0.02, 0.02, stats_text, fontsize=11, family='monospace',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))

    plt.tight_layout(rect=[0, 0.10, 1, 0.97])
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"\nAnalysis saved to: {output_path}")

    if len(pause_energy) > 0:
        print(f"\nPause Statistics:")
        print(f"  Mean Energy: {mean_pause_energy:.6f}")
        print(f"  Max Energy in Pause: {max_pause_energy:.6f}")
        print(f"  Overall Max Energy: {overall_max:.6f}")
        print(f"  Pause is {(mean_pause_energy/overall_max)*100:.1f}% of max energy")


if __name__ == "__main__":
    audio_path = r"d:\stevner\2025\regionalt\Lørdag\04-LørdagEttermiddag\04-LørdagEttermiddag.mp3"

    # Analyze the pause region around 6395-6399
    analyze_pause_region(
        audio_path,
        start=6394.0,
        end=6400.0,
        output_path='pause_region_analysis.png'
    )
