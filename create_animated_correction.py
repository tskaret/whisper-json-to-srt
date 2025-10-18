#!/usr/bin/env python3
"""
Create animated GIF showing before/after energy correction on MFCC

Shows:
- Frame 1: Original WhisperX timing with word boundaries
- Frame 2: Energy-corrected timing with word boundaries
- Frame 3: Overlay showing the difference (correction magnitude)
"""

import json
import sys
import librosa
import librosa.display
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from PIL import Image


def load_json_transcript(json_path):
    """Load WhisperX format JSON"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

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
    """Extract a sentence from words based on punctuation"""
    sentences = []
    current_sentence = []

    for word in words:
        current_sentence.append(word)
        text = word['text'].strip()
        if text.endswith('.') or text.endswith('!') or text.endswith('?'):
            sentences.append(current_sentence)
            current_sentence = []

    if current_sentence:
        sentences.append(current_sentence)

    if sentence_number >= len(sentences):
        sentence_number = min(sentence_number, len(sentences) - 1)

    return sentences[sentence_number]


def create_mfcc_frame(audio_segment, sr, sentence_words, start_time, title,
                      highlight_corrections=False, original_words=None):
    """
    Create a single frame of MFCC visualization

    Args:
        audio_segment: Audio data
        sr: Sample rate
        sentence_words: List of word dictionaries with timing
        start_time: Start time of the segment (for relative positioning)
        title: Frame title
        highlight_corrections: If True, highlight corrected words in orange
        original_words: Original word timings (for comparison)
    """
    # Compute MFCC
    mfcc = librosa.feature.mfcc(y=audio_segment, sr=sr, n_mfcc=20,
                                n_fft=400, hop_length=160)

    # Create figure
    fig, ax = plt.subplots(figsize=(16, 6))

    # Display MFCC
    img = librosa.display.specshow(mfcc, x_axis='time', sr=sr, hop_length=160,
                                    ax=ax, cmap='viridis')
    plt.colorbar(img, ax=ax, format='%+2.0f dB')

    # Determine which words were corrected (if comparison mode)
    corrected_indices = set()
    if highlight_corrections and original_words:
        for i, (orig, corr) in enumerate(zip(original_words, sentence_words)):
            # If start or end changed by more than 50ms, it was corrected
            start_diff = abs(orig['start'] - corr['start'])
            end_diff = abs(orig['end'] - corr['end'])
            if start_diff > 0.05 or end_diff > 0.05:
                corrected_indices.add(i)

    # Add word boundaries
    for i, word in enumerate(sentence_words):
        word_start = word['start'] - start_time
        word_end = word['end'] - start_time

        # Choose color based on whether word was corrected
        if i in corrected_indices:
            start_color = 'orange'
            end_color = 'darkorange'
            alpha = 1.0
            linewidth = 2
        else:
            start_color = 'red'
            end_color = 'orange'
            alpha = 0.7
            linewidth = 1

        # Vertical lines at word boundaries
        ax.axvline(x=word_start, color=start_color, linestyle='--',
                   linewidth=linewidth, alpha=alpha)
        ax.axvline(x=word_end, color=end_color, linestyle=':',
                   linewidth=linewidth, alpha=alpha * 0.7)

        # Word text
        mid_time = (word_start + word_end) / 2
        bbox_color = start_color if i in corrected_indices else 'red'
        ax.text(mid_time, -2, word['text'], ha='center', va='top',
                fontsize=9, color='white',
                bbox=dict(boxstyle='round,pad=0.3', facecolor=bbox_color, alpha=0.8))

    # Add duration annotations for corrected words
    if highlight_corrections and original_words:
        for i in corrected_indices:
            word = sentence_words[i]
            orig = original_words[i]

            orig_dur = orig['end'] - orig['start']
            corr_dur = word['end'] - word['start']
            reduction = orig_dur - corr_dur

            mid_time = (word['start'] - start_time + word['end'] - start_time) / 2

            ax.text(mid_time, 18,
                    f"Before: {orig_dur*1000:.0f}ms\nAfter: {corr_dur*1000:.0f}ms\n↓ {reduction*1000:.0f}ms",
                    ha='center', va='bottom', fontsize=8,
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.9),
                    color='black', weight='bold')

    # Formatting
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel('MFCC Coefficient', fontsize=12)
    ax.set_title(title, fontsize=14, pad=20, weight='bold')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    # Convert to image
    fig.canvas.draw()
    image = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
    image = image.reshape(fig.canvas.get_width_height()[::-1] + (4,))
    image = image[:, :, :3]  # Remove alpha channel

    plt.close()

    return Image.fromarray(image)


def create_overlay_frame(audio_segment, sr, original_words, corrected_words,
                         start_time, title):
    """
    Create overlay frame showing both original and corrected boundaries
    """
    # Compute MFCC
    mfcc = librosa.feature.mfcc(y=audio_segment, sr=sr, n_mfcc=20,
                                n_fft=400, hop_length=160)

    fig, ax = plt.subplots(figsize=(16, 6))

    # Display MFCC
    img = librosa.display.specshow(mfcc, x_axis='time', sr=sr, hop_length=160,
                                    ax=ax, cmap='viridis')
    plt.colorbar(img, ax=ax, format='%+2.0f dB')

    # Add BOTH sets of boundaries
    for i, (orig, corr) in enumerate(zip(original_words, corrected_words)):
        # Original boundaries (red, dashed)
        orig_start = orig['start'] - start_time
        orig_end = orig['end'] - start_time
        ax.axvline(x=orig_start, color='red', linestyle='--', linewidth=1, alpha=0.5)
        ax.axvline(x=orig_end, color='red', linestyle='--', linewidth=2, alpha=0.7,
                   label='Original' if i == 0 else '')

        # Corrected boundaries (lime green, solid)
        corr_start = corr['start'] - start_time
        corr_end = corr['end'] - start_time
        ax.axvline(x=corr_start, color='lime', linestyle='-', linewidth=1, alpha=0.7)
        ax.axvline(x=corr_end, color='lime', linestyle='-', linewidth=2, alpha=0.9,
                   label='Corrected' if i == 0 else '')

        # Add arrows showing correction direction (for significant changes)
        start_diff = abs(orig['start'] - corr['start'])
        end_diff = abs(orig['end'] - corr['end'])

        if end_diff > 0.05:  # Significant correction
            # Arrow from original to corrected
            arrow_y = 10
            ax.annotate('', xy=(corr_end, arrow_y), xytext=(orig_end, arrow_y),
                       arrowprops=dict(arrowstyle='<->', color='yellow', lw=2))

            # Show time saved
            mid_x = (orig_end + corr_end) / 2
            ax.text(mid_x, arrow_y + 2, f"-{end_diff*1000:.0f}ms",
                   ha='center', fontsize=9, color='yellow', weight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.7))

        # Word text (corrected position)
        mid_time = (corr_start + corr_end) / 2
        ax.text(mid_time, -2, corr['text'], ha='center', va='top',
                fontsize=9, color='white',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='lime', alpha=0.8))

    ax.legend(loc='upper right', fontsize=10)
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel('MFCC Coefficient', fontsize=12)
    ax.set_title(title, fontsize=14, pad=20, weight='bold')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    # Convert to image
    fig.canvas.draw()
    image = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
    image = image.reshape(fig.canvas.get_width_height()[::-1] + (4,))
    image = image[:, :, :3]  # Remove alpha channel

    plt.close()

    return Image.fromarray(image)


def create_animated_correction(audio_path, original_json, corrected_json,
                               sentence_number=0, output_gif=None,
                               buffer_before=0.5, buffer_after=0.5,
                               frame_duration=2000):
    """
    Create animated GIF showing energy correction process

    Args:
        audio_path: Path to audio file
        original_json: Path to original WhisperX JSON
        corrected_json: Path to energy-corrected JSON
        sentence_number: Which sentence to visualize
        output_gif: Output GIF path
        buffer_before: Seconds before sentence
        buffer_after: Seconds after sentence
        frame_duration: Milliseconds per frame
    """
    print(f"Loading audio: {audio_path}")
    audio, sr = librosa.load(audio_path, sr=16000)

    print(f"Loading original transcript: {original_json}")
    original_words = load_json_transcript(original_json)

    print(f"Loading corrected transcript: {corrected_json}")
    corrected_words = load_json_transcript(corrected_json)

    # Extract sentences
    original_sentence = find_sentence(original_words, sentence_number)
    corrected_sentence = find_sentence(corrected_words, sentence_number)

    sentence_text = ' '.join(w['text'] for w in corrected_sentence)
    print(f"\nSentence {sentence_number}: {sentence_text}")
    print(f"Words: {len(corrected_sentence)}")

    # Get time range (use corrected sentence for boundaries)
    sentence_start = corrected_sentence[0]['start']
    sentence_end = corrected_sentence[-1]['end']

    start_time = max(0, sentence_start - buffer_before)
    end_time = min(len(audio) / sr, sentence_end + buffer_after)

    print(f"Time range: {start_time:.2f}s - {end_time:.2f}s")

    # Extract audio segment
    start_sample = int(start_time * sr)
    end_sample = int(end_time * sr)
    audio_segment = audio[start_sample:end_sample]

    print("\nCreating frames...")

    # Frame 1: Original timing
    print("  Frame 1: Original WhisperX timing")
    frame1 = create_mfcc_frame(
        audio_segment, sr, original_sentence, start_time,
        f"FRAME 1: Original WhisperX Timing\nSentence: \"{sentence_text}\""
    )

    # Frame 2: Corrected timing with highlights
    print("  Frame 2: Energy-corrected timing")
    frame2 = create_mfcc_frame(
        audio_segment, sr, corrected_sentence, start_time,
        f"FRAME 2: Energy-Corrected Timing\nSentence: \"{sentence_text}\"",
        highlight_corrections=True,
        original_words=original_sentence
    )

    # Frame 3: Overlay comparison
    print("  Frame 3: Overlay comparison")
    frame3 = create_overlay_frame(
        audio_segment, sr, original_sentence, corrected_sentence, start_time,
        f"FRAME 3: Comparison (Red=Original, Green=Corrected)\nSentence: \"{sentence_text}\""
    )

    # Save as animated GIF
    if output_gif is None:
        output_gif = Path(f"animated_correction_sentence_{sentence_number}.gif")

    frames = [frame1, frame2, frame3]

    print(f"\nSaving animated GIF: {output_gif}")
    frames[0].save(
        output_gif,
        save_all=True,
        append_images=frames[1:],
        duration=frame_duration,  # ms per frame
        loop=0  # Loop forever
    )

    print(f"✓ Animated GIF created: {output_gif}")
    print(f"  3 frames, {frame_duration}ms per frame")

    # Also save individual frames as static images
    frame1.save(str(output_gif).replace('.gif', '_frame1_original.png'))
    frame2.save(str(output_gif).replace('.gif', '_frame2_corrected.png'))
    frame3.save(str(output_gif).replace('.gif', '_frame3_overlay.png'))
    print(f"✓ Individual frames saved as PNG")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python create_animated_correction.py <audio> <original_json> <corrected_json> [sentence_num] [output_gif]")
        print("\nExample:")
        print("  python create_animated_correction.py audio.mp3 original.json corrected.json 0 sentence_0.gif")
        sys.exit(1)

    audio_file = sys.argv[1]
    original_json = sys.argv[2]
    corrected_json = sys.argv[3]
    sentence_num = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    output_gif = sys.argv[5] if len(sys.argv) > 5 else None

    create_animated_correction(
        audio_file, original_json, corrected_json,
        sentence_number=sentence_num,
        output_gif=output_gif,
        buffer_before=0.5,
        buffer_after=0.5,
        frame_duration=2500  # 2.5 seconds per frame
    )
