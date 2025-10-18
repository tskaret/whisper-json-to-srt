"""
Test VAD approaches on NORMAL words (not extreme anomalies)
"""

import sys
sys.path.append('.')
from compare_vad_approaches import VADComparator, load_words
import numpy as np


def main():
    audio_path = r"d:\stevner\2025\regionalt\Lørdag\04-LørdagEttermiddag\04-LørdagEttermiddag.mp3"
    json_path = "04-LørdagEttermiddag.json"

    print("\n" + "="*70)
    print("TESTING ON NORMAL WORDS (0-70s segment)")
    print("="*70)

    words = load_words(json_path, start_time=0, end_time=70)
    print(f"\nLoaded {len(words)} words")

    comparator = VADComparator(audio_path)

    # Test on first 10 words
    print("\n" + "-"*70)
    print(f"{'Word':<18} {'Orig':<8} {'VAD':<8} {'Grad':<8} {'VAD D':<8} {'Grad D'}")
    print("-"*70)

    vad_improvements = []
    gradient_improvements = []

    for word in words[:15]:
        vad_result = comparator.webrtc_vad_detect(word)
        gradient_result = comparator.gradient_based_detect(word)

        vad_delta = abs(vad_result['start_adjustment']) + abs(vad_result['end_adjustment'])
        grad_delta = abs(gradient_result['start_adjustment']) + abs(gradient_result['end_adjustment'])

        vad_improvements.append(vad_delta)
        gradient_improvements.append(grad_delta)

        syllables = word.count_syllables()

        print(f"{word.text:<18} "
              f"{word.duration:>6.3f}s "
              f"{vad_result['adjusted_duration']:>6.3f}s "
              f"{gradient_result['adjusted_duration']:>6.3f}s "
              f"{vad_delta*1000:>6.1f}ms "
              f"{grad_delta*1000:>6.1f}ms")

    print("\n" + "="*70)
    print("STATISTICS FOR NORMAL WORDS")
    print("="*70)
    print(f"Average VAD adjustment:      {np.mean(vad_improvements)*1000:.1f}ms")
    print(f"Average Gradient adjustment: {np.mean(gradient_improvements)*1000:.1f}ms")
    print(f"\nMax VAD adjustment:      {np.max(vad_improvements)*1000:.1f}ms")
    print(f"Max Gradient adjustment: {np.max(gradient_improvements)*1000:.1f}ms")

    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    print("""
For NORMAL words:
- Both methods provide similar adjustments (~400-1000ms total)
- Gradient-based is slightly more conservative
- Both are suitable for fine-tuning normal word boundaries

For EXTREME anomalies (21+ seconds):
- NEITHER method can correct the fundamental timing error
- The issue is that WhisperX includes massive silence in the word window
- Waveform analysis works within the provided window only

SOLUTION:
- Use waveform fine-tuning for normal cases (works well!)
- Flag extreme cases (>2s anomaly) for MANUAL review
- Verification system with PowerPoint + HTML viewer is ESSENTIAL
    """)


if __name__ == '__main__':
    main()
