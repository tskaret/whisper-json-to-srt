#!/usr/bin/env python3
"""
Test what wrap_text returns for segment 516
"""

import sys
sys.path.insert(0, 'D:\\Kreativitet\\subtitle-processing-experiments')

from json_to_srt_energy import SRTConverter, Word

# Create converter with same parameters as user
audio_path = '/mnt/d/stevner/2025/regionalt/Lørdag/04-LørdagEttermiddag/04-LørdagEttermiddag.mp3'
converter = SRTConverter(
    audio_path=audio_path,
    max_chars_per_line=37,  # User's parameter
    pause_threshold=1.2,
    break_on_speaker_change=False
)

# Create fake words for segment 516
segment_text = "Han sa ikke noe om at Gud og Jesus var inne i bildet. Begrepet synd var ganske fjernt for meg. Jeg tenkte noen ganger gjør man feil, og så går man bare videre i"
word_texts = segment_text.split()

# Create Word objects
words = []
t = 3822.954
for text in word_texts:
    words.append(Word(
        text=text,
        start=t,
        end=t + 0.2,
        speaker='SPEAKER_00'
    ))
    t += 0.25

print(f"Segment has {len(words)} words")
print(f"Full text ({len(segment_text)} chars): \"{segment_text}\"")
print()

# Test wrap_text
wrapped_lines = converter.wrap_text(words)

print(f"wrap_text() returned {len(wrapped_lines)} lines:")
for i, line in enumerate(wrapped_lines, 1):
    print(f"  Line {i} ({len(line)} chars): \"{line}\"")

print()

# Show how many words were included
wrapped_text = ' '.join(wrapped_lines)
wrapped_words = wrapped_text.split()
print(f"\nWords included in wrapped text: {len(wrapped_words)}/{len(words)}")
print(f"Words LOST: {len(words) - len(wrapped_words)}")

if len(wrapped_words) < len(words):
    print(f"\nMissing words: {word_texts[len(wrapped_words):]}")
