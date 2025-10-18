#!/usr/bin/env python3
"""
Generate MFCC visualization with word boundaries from JSON transcript
Similar to the whisper-timestamped visualization
"""

import json
import sys
import librosa
import librosa.display
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


def load_json_transcript(json_path):
    """Load WhisperX format JSON"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Flatten all words
    all_words = []
    for segment in data.get('segments', []):
        for word_obj in segment.get('words', []):
            all_words.append({
                'text': word_obj.get('word', '').strip(),
                'start': word_obj.get('start', 0.0),
                'end': word_obj.get('end', 0.0),
            })
    return all_words


def find_sentence(words, sentence_number=0):
    """
    Extract a sentence from words based on punctuation

    Args:
        words: List of word dictionaries
        sentence_number: Which sentence to extract (0-indexed)

    Returns:
        List of words in the sentence
    """
    sentences = []
    current_sentence = []

    for word in words:
        current_sentence.append(word)

        # End of sentence markers
        text = word['text'].strip()
        if text.endswith('.') or text.endswith('!') or text.endswith('?'):
            sentences.append(current_sentence)
            current_sentence = []

    # Add remaining words as last sentence
    if current_sentence:
        sentences.append(current_sentence)

    if sentence_number >= len(sentences):
        print(f"Warning: Only {len(sentences)} sentences found, requested sentence {sentence_number}")
        sentence_number = min(sentence_number, len(sentences) - 1)

    return sentences[sentence_number], len(sentences)


def visualize_mfcc_with_words(audio_path, json_path, sentence_number=0,
                               buffer_before=0.5, buffer_after=0.5,
                               output_path=None):
    """
    Generate MFCC visualization with word boundaries

    Args:
        audio_path: Path to audio file
        json_path: Path to JSON transcript
        sentence_number: Which sentence to visualize (0-indexed)
        buffer_before: Seconds of audio before sentence start
        buffer_after: Seconds of audio after sentence end
        output_path: Where to save the image
    """
    print(f"Loading audio: {audio_path}")
    audio, sr = librosa.load(audio_path, sr=16000)

    print(f"Loading transcript: {json_path}")
    all_words = load_json_transcript(json_path)
    print(f"Total words loaded: {len(all_words)}")

    # Extract sentence
    sentence_words, total_sentences = find_sentence(all_words, sentence_number)
    print(f"\nFound {total_sentences} sentences")
    print(f"Extracting sentence {sentence_number}:")
    sentence_text = ' '.join(w['text'] for w in sentence_words)
    print(f"  Text: {sentence_text}")
    print(f"  Words: {len(sentence_words)}")

    # Get time range
    sentence_start = sentence_words[0]['start']
    sentence_end = sentence_words[-1]['end']

    # Add buffer
    start_time = max(0, sentence_start - buffer_before)
    end_time = min(len(audio) / sr, sentence_end + buffer_after)

    print(f"  Time range: {start_time:.2f}s - {end_time:.2f}s (duration: {end_time - start_time:.2f}s)")

    # Extract audio segment
    start_sample = int(start_time * sr)
    end_sample = int(end_time * sr)
    audio_segment = audio[start_sample:end_sample]

    # Compute MFCC
    print("Computing MFCC...")
    mfcc = librosa.feature.mfcc(y=audio_segment, sr=sr, n_mfcc=20,
                                n_fft=400, hop_length=160)  # 10ms frames, 25ms window

    # Create figure
    fig, ax = plt.subplots(figsize=(16, 6))

    # Display MFCC
    img = librosa.display.specshow(mfcc, x_axis='time', sr=sr, hop_length=160,
                                    ax=ax, cmap='viridis')

    # Add colorbar
    plt.colorbar(img, ax=ax, format='%+2.0f dB')

    # Add word boundaries as vertical lines
    for i, word in enumerate(sentence_words):
        word_start = word['start'] - start_time
        word_end = word['end'] - start_time

        # Vertical line at word start
        ax.axvline(x=word_start, color='red', linestyle='--', linewidth=1, alpha=0.7)

        # Vertical line at word end (lighter)
        ax.axvline(x=word_end, color='orange', linestyle=':', linewidth=1, alpha=0.5)

        # Add word text below
        mid_time = (word_start + word_end) / 2
        ax.text(mid_time, -2, word['text'], ha='center', va='top',
                fontsize=9, color='white',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='red', alpha=0.7))

    # Mark actual sentence boundaries with thicker lines
    sentence_start_rel = sentence_start - start_time
    sentence_end_rel = sentence_end - start_time
    ax.axvline(x=sentence_start_rel, color='lime', linestyle='-', linewidth=2, alpha=0.9,
               label='Sentence Start')
    ax.axvline(x=sentence_end_rel, color='cyan', linestyle='-', linewidth=2, alpha=0.9,
               label='Sentence End')

    # Formatting
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel('MFCC Coefficient', fontsize=12)
    ax.set_title(f'MFCC with Word Boundaries\nSentence {sentence_number}: "{sentence_text}"',
                 fontsize=14, pad=20)
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)

    # Save or show
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\nVisualization saved to: {output_path}")
    else:
        plt.tight_layout()
        plt.show()

    plt.close()

    # Print word timing details
    print("\nWord timing details:")
    print(f"{'Word':<20} {'Start':<10} {'End':<10} {'Duration':<10}")
    print("-" * 50)
    for word in sentence_words:
        duration = word['end'] - word['start']
        print(f"{word['text']:<20} {word['start']:<10.3f} {word['end']:<10.3f} {duration:<10.3f}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python visualize_mfcc_with_words.py <audio_file> <json_file> [sentence_number] [output_image]")
        print("\nExample:")
        print("  python visualize_mfcc_with_words.py audio.mp3 transcript.json 0")
        print("  python visualize_mfcc_with_words.py audio.mp3 transcript.json 5 sentence_5.png")
        sys.exit(1)

    audio_file = sys.argv[1]
    json_file = sys.argv[2]
    sentence_num = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    output_image = sys.argv[4] if len(sys.argv) > 4 else None

    visualize_mfcc_with_words(audio_file, json_file, sentence_num,
                              buffer_before=0.5, buffer_after=0.5,
                              output_path=output_image)
