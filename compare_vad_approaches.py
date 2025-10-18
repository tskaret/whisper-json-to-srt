"""
Comparative Analysis: WebRTC VAD vs. Our Gradient-Based Approach

This script compares how different voice activity detection methods handle
long-duration words (anomalies) in the Norwegian speech transcript.
"""

import json
import numpy as np
import librosa
import webrtcvad
import struct
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

    def is_anomalous(self, threshold=2.0) -> bool:
        """Check if duration is anomalous (>threshold * expected)"""
        expected = self.count_syllables() * 0.15
        return self.duration > (expected * threshold)


class VADComparator:
    """Compare different VAD approaches"""

    def __init__(self, audio_path: str, sr: int = 16000):
        print(f"Loading audio: {audio_path}")
        self.audio, self.sr = librosa.load(audio_path, sr=sr, mono=True)
        print(f"Audio loaded: {len(self.audio)/sr:.1f}s, sr={sr}Hz")

        # Initialize WebRTC VAD
        self.vad = webrtcvad.Vad(2)  # Moderate aggressiveness (0-3)

    def extract_segment(self, start: float, end: float) -> Tuple[np.ndarray, int]:
        """Extract audio segment"""
        start_sample = int(start * self.sr)
        end_sample = int(end * self.sr)
        segment = self.audio[start_sample:end_sample]
        return segment, start_sample

    def webrtc_vad_detect(self, word: Word) -> Dict:
        """Use WebRTC VAD to find speech boundaries"""
        audio, start_sample = self.extract_segment(word.start - 0.5, word.end + 0.5)

        # WebRTC VAD requires 16-bit PCM at 16kHz
        # Frame must be 10, 20, or 30ms
        frame_duration_ms = 10
        frame_length = int(self.sr * frame_duration_ms / 1000)

        # Find first and last speech frames
        first_speech = None
        last_speech = None

        for i in range(0, len(audio) - frame_length, frame_length):
            frame = audio[i:i + frame_length]

            # Convert to 16-bit PCM
            frame_int16 = (frame * 32767).astype(np.int16)
            frame_bytes = struct.pack(f'{len(frame_int16)}h', *frame_int16)

            # Check if speech
            try:
                is_speech = self.vad.is_speech(frame_bytes, self.sr)

                if is_speech:
                    if first_speech is None:
                        first_speech = i
                    last_speech = i + frame_length
            except:
                pass

        if first_speech is not None and last_speech is not None:
            # Convert to absolute timing
            adjusted_start = word.start - 0.5 + (first_speech / self.sr)
            adjusted_end = word.start - 0.5 + (last_speech / self.sr)

            return {
                'method': 'webrtc_vad',
                'original_duration': word.duration,
                'adjusted_duration': adjusted_end - adjusted_start,
                'start_adjustment': adjusted_start - word.start,
                'end_adjustment': adjusted_end - word.end,
                'speech_detected': True
            }
        else:
            return {
                'method': 'webrtc_vad',
                'original_duration': word.duration,
                'adjusted_duration': word.duration,
                'start_adjustment': 0.0,
                'end_adjustment': 0.0,
                'speech_detected': False
            }

    def gradient_based_detect(self, word: Word) -> Dict:
        """Use our gradient-based approach (simplified)"""
        audio, start_sample = self.extract_segment(word.start - 0.2, word.end + 0.2)

        # Calculate RMS energy
        frame_length = int(0.005 * self.sr)  # 5ms frames
        hop_length = int(0.002 * self.sr)    # 2ms hop

        rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]

        # Compute gradient
        if len(rms) < 2:
            return {
                'method': 'gradient_based',
                'original_duration': word.duration,
                'adjusted_duration': word.duration,
                'start_adjustment': 0.0,
                'end_adjustment': 0.0,
                'speech_detected': False
            }
        gradient = np.gradient(rms)

        # Find onset (strong positive gradient)
        noise_level = np.percentile(rms, 10)
        max_energy = np.max(rms)
        energy_threshold = max(noise_level * 2.0, max_energy * 0.10)
        gradient_threshold = np.percentile(gradient, 75)

        first_speech = None
        last_speech = None

        for i in range(len(rms)):
            if rms[i] > energy_threshold:
                if first_speech is None and gradient[i] > gradient_threshold:
                    first_speech = i
                last_speech = i

        if first_speech is not None and last_speech is not None:
            # Convert frames to time
            adjusted_start = word.start - 0.2 + (first_speech * hop_length / self.sr)
            adjusted_end = word.start - 0.2 + (last_speech * hop_length / self.sr)

            return {
                'method': 'gradient_based',
                'original_duration': word.duration,
                'adjusted_duration': adjusted_end - adjusted_start,
                'start_adjustment': adjusted_start - word.start,
                'end_adjustment': adjusted_end - word.end,
                'speech_detected': True
            }
        else:
            return {
                'method': 'gradient_based',
                'original_duration': word.duration,
                'adjusted_duration': word.duration,
                'start_adjustment': 0.0,
                'end_adjustment': 0.0,
                'speech_detected': False
            }


def load_words(json_path: str, start_time: float = 0, end_time: float = None) -> List[Word]:
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
    # Test on the extreme anomaly segment
    audio_path = r"d:\stevner\2025\regionalt\Lørdag\04-LørdagEttermiddag\04-LørdagEttermiddag.mp3"
    json_path = "04-LørdagEttermiddag.json"

    # Load words
    print("\n" + "="*70)
    print("COMPARATIVE ANALYSIS: WebRTC VAD vs. Gradient-Based Detection")
    print("="*70)

    words = load_words(json_path, start_time=490, end_time=545)
    print(f"\nLoaded {len(words)} words in extreme anomaly segment (490-545s)")

    # Initialize comparator
    comparator = VADComparator(audio_path)

    # Analyze each word
    results = []

    print("\n" + "-"*70)
    print(f"{'Word':<15} {'Original':<12} {'WebRTC VAD':<12} {'Gradient':<12} {'Anomaly'}")
    print("-"*70)

    for word in words:
        # Test both methods
        vad_result = comparator.webrtc_vad_detect(word)
        gradient_result = comparator.gradient_based_detect(word)

        is_anomalous = word.is_anomalous()
        syllables = word.count_syllables()
        expected = syllables * 0.15

        print(f"{word.text:<15} "
              f"{word.duration:>5.3f}s ({syllables}syl) "
              f"{vad_result['adjusted_duration']:>5.3f}s     "
              f"{gradient_result['adjusted_duration']:>5.3f}s     "
              f"{'***' if is_anomalous else ''}")

        results.append({
            'word': word,
            'vad': vad_result,
            'gradient': gradient_result,
            'is_anomalous': is_anomalous,
            'expected_duration': expected
        })

    # Summary statistics
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    anomalous_words = [r for r in results if r['is_anomalous']]
    normal_words = [r for r in results if not r['is_anomalous']]

    print(f"\nTotal words: {len(results)}")
    print(f"Anomalous words (>2x expected): {len(anomalous_words)}")
    print(f"Normal words: {len(normal_words)}")

    if anomalous_words:
        print("\n--- ANOMALOUS WORDS ---")
        for r in anomalous_words:
            w = r['word']
            print(f"\n'{w.text}' ({w.count_syllables()} syllable{'' if w.count_syllables() == 1 else 's'})")
            print(f"  Original duration:   {r['vad']['original_duration']:>6.3f}s (expected ~{r['expected_duration']:.3f}s)")
            print(f"  WebRTC VAD adjusted: {r['vad']['adjusted_duration']:>6.3f}s (D start:{r['vad']['start_adjustment']:+.3f}s, end:{r['vad']['end_adjustment']:+.3f}s)")
            print(f"  Gradient adjusted:   {r['gradient']['adjusted_duration']:>6.3f}s (D start:{r['gradient']['start_adjustment']:+.3f}s, end:{r['gradient']['end_adjustment']:+.3f}s)")
            print(f"  Speech detected:     VAD:{r['vad']['speech_detected']}, Gradient:{r['gradient']['speech_detected']}")

    # Calculate average corrections
    if normal_words:
        avg_vad_normal = np.mean([abs(r['vad']['start_adjustment']) + abs(r['vad']['end_adjustment'])
                                   for r in normal_words])
        avg_gradient_normal = np.mean([abs(r['gradient']['start_adjustment']) + abs(r['gradient']['end_adjustment'])
                                        for r in normal_words])

        print(f"\n--- NORMAL WORDS ---")
        print(f"Average total adjustment (VAD):      {avg_vad_normal*1000:.1f}ms")
        print(f"Average total adjustment (Gradient): {avg_gradient_normal*1000:.1f}ms")

    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    print("""
Both WebRTC VAD and gradient-based detection can detect speech boundaries,
but neither can fully correct extreme anomalies (21+ seconds) because the
adjustment window is limited.

KEY INSIGHTS:
1. WebRTC VAD: Binary speech/silence classification
   - Fast and reliable for detecting speech presence
   - Good for finding speech regions in large pauses

2. Gradient-based: Detects speech onset/offset by energy changes
   - More sensitive to gradual speech starts
   - Can detect subtle boundaries

3. LIMITATION: Both methods work within the provided timing window.
   When WhisperX includes 21 seconds of silence in the word timing,
   neither method can "know" the actual word ended 21 seconds earlier.

RECOMMENDATION: Use hybrid approach:
   - WebRTC VAD to find general speech regions
   - Gradient detection for precise boundaries
   - Manual verification for extreme cases (>2s anomaly)
    """)


if __name__ == '__main__':
    main()
