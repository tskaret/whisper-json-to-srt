#!/usr/bin/env python3
"""
Visualize the timing issue with "søstre."
Shows why original start + pause-based end is better
"""

import numpy as np
import librosa
from scipy import signal
import matplotlib.pyplot as plt

# Load audio around "søstre."
print('Loading audio...')
audio, sr = librosa.load(
    r'd:\stevner\2025\regionalt\Lørdag\04-LørdagEttermiddag\04-LørdagEttermiddag.mp3',
    sr=16000, mono=True, offset=1.5, duration=5.0
)

# Calculate RMS energy
frame_length = int(0.005 * sr)
hop_length = int(0.002 * sr)
rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]

# Smooth
window_len = min(11, len(rms) // 2 * 2 + 1)
rms_smooth = signal.savgol_filter(rms, window_length=window_len, polyorder=2)

# Time arrays
audio_times = 1.5 + np.arange(len(audio)) / sr
rms_times = 1.5 + np.arange(len(rms_smooth)) * hop_length / sr

# Thresholds
noise_floor = np.percentile(rms_smooth, 10)
speech_threshold = noise_floor * 3

# Find sustained silence after 2.314s
start_time = 2.314
start_idx = np.argmin(np.abs(rms_times - start_time))

MIN_SILENCE_DURATION = 0.100
silence_frames = int(MIN_SILENCE_DURATION / (hop_length / sr))

actual_end = None
for i in range(start_idx, len(rms_smooth) - silence_frames):
    if np.all(rms_smooth[i:i+silence_frames] < speech_threshold):
        actual_end = rms_times[i]
        break

if actual_end is None:
    actual_end = 2.9  # fallback

# Create visualization
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))

# Panel 1: Waveform
ax1.plot(audio_times, audio, linewidth=0.5, color='gray', alpha=0.7)
ax1.fill_between(audio_times, audio, color='lightgray', alpha=0.3)

# Mark timings
# Original WhisperX (includes silence)
ax1.axvspan(2.314, 5.238, alpha=0.15, color='red', label='Original WhisperX (WRONG)')
ax1.axvline(2.314, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Original start (GOOD)')
ax1.axvline(5.238, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Original end (BAD - includes 2.6s silence)')

# Correct timing (keep start, fix end)
ax1.axvspan(2.314, actual_end, alpha=0.25, color='green', label='Correct Timing')
ax1.axvline(actual_end, color='green', linestyle='-', linewidth=2.5, alpha=0.9, label=f'Correct end ({actual_end:.3f}s)')

# Next word
ax1.axvline(5.258, color='blue', linestyle='-.', linewidth=1.5, alpha=0.7, label='Next word "Om" starts')

ax1.set_xlim(1.5, 6.5)
ax1.set_ylabel('Amplitude', fontsize=11)
ax1.set_title('Waveform: "søstre." - Original vs Correct Timing', fontsize=13, fontweight='bold')
ax1.legend(loc='upper right', fontsize=9)
ax1.grid(True, alpha=0.3)

# Panel 2: Energy with threshold
ax2.plot(rms_times, rms_smooth, linewidth=2, color='purple', label='RMS Energy')
ax2.axhline(speech_threshold, color='orange', linestyle='--', linewidth=1.5,
            label=f'Speech threshold ({speech_threshold:.4f})')
ax2.axhline(noise_floor, color='gray', linestyle=':', linewidth=1,
            label=f'Noise floor ({noise_floor:.4f})')

# Mark same timings
ax2.axvline(2.314, color='red', linestyle='--', linewidth=2, alpha=0.7)
ax2.axvline(5.238, color='red', linestyle='--', linewidth=2, alpha=0.7)
ax2.axvline(actual_end, color='green', linestyle='-', linewidth=2.5, alpha=0.9)
ax2.axvline(5.258, color='blue', linestyle='-.', linewidth=1.5, alpha=0.7)

# Shade silence region
silence_mask = rms_smooth < speech_threshold
ax2.fill_between(rms_times, 0, rms_smooth.max(), where=silence_mask,
                 alpha=0.1, color='gray', label='Below threshold (silence)')

ax2.set_xlim(1.5, 6.5)
ax2.set_xlabel('Time (seconds)', fontsize=11, fontweight='bold')
ax2.set_ylabel('RMS Energy', fontsize=11)
ax2.set_title('Energy Analysis: Finding the Actual Pause', fontsize=13, fontweight='bold')
ax2.legend(loc='upper right', fontsize=9)
ax2.grid(True, alpha=0.3)

# Add text annotations
fig.text(0.5, 0.95, '"søstre." - Last Word Before Punctuation',
         ha='center', fontsize=15, fontweight='bold')

stats_text = (
    f'Original timing: 2.314s → 5.238s (2.924s duration)\n'
    f'Problem: Includes 2.61s of SILENCE after word ends\n'
    f'\n'
    f'Correct timing: 2.314s → {actual_end:.3f}s ({actual_end-2.314:.3f}s duration)\n'
    f'Solution: Keep original START, end at sustained silence\n'
    f'\n'
    f'Algorithm:\n'
    f'  1. Keep original start (speech begins)\n'
    f'  2. Find where energy drops below threshold\n'
    f'  3. Verify it STAYS low for 100ms+\n'
    f'  4. Use that as the end (pause begins)'
)

fig.text(0.02, 0.02, stats_text, fontsize=10, family='monospace',
         bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9),
         verticalalignment='bottom')

plt.tight_layout(rect=[0, 0.15, 1, 0.93])
plt.savefig(r'd:\stevner\2025\regionalt\Lørdag\04-LørdagEttermiddag\sostre_timing_analysis.png',
            dpi=150, bbox_inches='tight')
print(f'\nVisualization saved to: sostre_timing_analysis.png')

# Print summary
print(f'\n{"="*70}')
print('TIMING ANALYSIS SUMMARY')
print(f'{"="*70}')
print(f'Word: "søstre." (last word before punctuation)')
print(f'\nOriginal WhisperX timing:')
print(f'  Start: 2.314s ✓ CORRECT (actual speech start)')
print(f'  End:   5.238s ✗ WRONG (includes 2.61s of silence)')
print(f'\nCorrect timing (keep start + pause detection):')
print(f'  Start: 2.314s ✓ (original)')
print(f'  End:   {actual_end:.3f}s ✓ (sustained silence begins)')
print(f'  Duration: {actual_end-2.314:.3f}s (reasonable for 2-syllable word)')
print(f'\nNext word "Om" starts at: 5.258s')
print(f'Pause duration: {5.258 - actual_end:.3f}s')
print(f'{"="*70}')

plt.close()
