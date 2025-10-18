#!/usr/bin/env python3
"""
Debug why sustained pause detection isn't finding silence for "søstre."
"""

import json
import numpy as np
import sys
sys.path.insert(0, '.')

from json_to_srt_energy import EnergyDropCorrector, Word

# Load audio and JSON
audio_path = r'd:\stevner\2025\regionalt\Lørdag\04-LørdagEttermiddag\04-LørdagEttermiddag.mp3'
json_path = r'd:\stevner\2025\regionalt\Lørdag\04-LørdagEttermiddag\04-LørdagEttermiddag.json'

print("Loading audio...")
corrector = EnergyDropCorrector(audio_path)

print("\nLoading JSON to find 'søstre.'...")
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Find "søstre." word (first occurrence)
sostre_word = None
for segment in data['segments']:
    for word_data in segment.get('words', []):
        text = word_data.get('word', '').strip()
        if 'søstre' in text.lower() and text.endswith('.'):
            sostre_word = Word(
                text=text,
                start=float(word_data['start']),
                end=float(word_data['end']),
                speaker=segment.get('speaker', 'UNKNOWN'),
                score=float(word_data.get('score', 1.0)),
                original_start=float(word_data['start']),
                original_end=float(word_data['end'])
            )
            break
    if sostre_word:
        break

if not sostre_word:
    print("ERROR: Could not find 'søstre.' in JSON")
    sys.exit(1)

print(f"\nFound word: '{sostre_word.text}'")
print(f"Original timing: {sostre_word.original_start:.3f}s -> {sostre_word.original_end:.3f}s")

# Apply correction with detailed debug
print("\n" + "="*70)
print("APPLYING CORRECTION (is_last_before_punct=True)")
print("="*70)

corrected = corrector.correct_word_timing(sostre_word, sensitivity='high', is_last_before_punct=True)

print(f"\nCorrected timing: {corrected.start:.3f}s -> {corrected.end:.3f}s")
print(f"Adjustment magnitude: {corrected.adjustment_magnitude*1000:.1f}ms" if corrected.adjustment_magnitude else "No adjustment (0ms)")
print(f"Adjustment reason: {corrected.adjustment_reason}")

if corrected.adjustment_magnitude and corrected.adjustment_magnitude > 0.001:
    print("\n✅ SUCCESS: Sustained pause detection made an adjustment")
else:
    print("\n❌ ISSUE: No adjustment made - sustained pause detection didn't find silence")
    print("\nDEBUGGING: Let's manually check the energy in this region...")

    # Manual energy check
    import librosa
    from scipy import signal

    audio, seg_start = corrector.extract_segment(sostre_word.original_start, sostre_word.original_end, buffer=0.5)
    frame_length = int(0.005 * corrector.sr)
    hop_length = int(0.002 * corrector.sr)
    rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]

    window_len = min(11, len(rms) // 2 * 2 + 1)
    rms_smooth = signal.savgol_filter(rms, window_length=window_len, polyorder=2)
    rms_times = seg_start + np.arange(len(rms_smooth)) * hop_length / corrector.sr

    noise_floor = np.percentile(rms_smooth, 10)
    speech_threshold = noise_floor * 3.0

    print(f"\nNoise floor: {noise_floor:.6f}")
    print(f"Speech threshold (3x): {speech_threshold:.6f}")

    # Find where energy is below threshold
    print(f"\nSearching for sustained silence (100ms = {int(0.100 / (hop_length / corrector.sr))} frames)...")

    MIN_SILENCE_DURATION = 0.100
    silence_frames = int(MIN_SILENCE_DURATION / (hop_length / corrector.sr))

    start_idx = np.argmin(np.abs(rms_times - sostre_word.original_start))

    found_silence = False
    for i in range(start_idx, len(rms_smooth) - silence_frames):
        if np.all(rms_smooth[i:i+silence_frames] < speech_threshold):
            silence_time = rms_times[i]
            print(f"✓ Found sustained silence at {silence_time:.3f}s")
            found_silence = True
            break

    if not found_silence:
        print("✗ No sustained silence found in search range")
        print(f"\nEnergy samples around expected pause (2.6-2.8s):")
        for i, (t, e) in enumerate(zip(rms_times, rms_smooth)):
            if 2.5 <= t <= 3.0:
                status = "SPEECH" if e > speech_threshold else "silence"
                print(f"  {t:.3f}s: {e:.6f} ({status})")
