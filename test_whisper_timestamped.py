#!/usr/bin/env python3
"""
Test whisper-timestamped on audio file
Generates word-level timestamps using DTW on cross-attention weights
"""

import whisper_timestamped as whisper
import json
import sys
from pathlib import Path

def transcribe_with_whisper_timestamped(audio_path, output_path=None, model_size="large-v3", language="no"):
    """
    Transcribe audio using whisper-timestamped

    Args:
        audio_path: Path to audio file
        output_path: Path to save JSON output (optional)
        model_size: Whisper model size (default: large-v3)
        language: Language code (default: no for Norwegian)

    Returns:
        dict: Transcription result with word-level timestamps
    """
    print(f"Loading Whisper model: {model_size}")
    audio = whisper.load_audio(audio_path)
    model = whisper.load_model(model_size)

    print(f"Transcribing: {audio_path}")
    print(f"Language: {language}")

    result = whisper.transcribe(
        model,
        audio,
        language=language,
        # Timing precision parameters
        min_word_duration=0.02,  # 20ms minimum (matches their docs)
        refine_whisper_precision=0.5,  # Refine by 0.5s increments
        # Quality parameters
        remove_empty_words=True,  # Remove zero-duration words
        trust_whisper_timestamps=True,  # Trust initial segment positions
    )

    # Save if output path specified
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nTranscript saved to: {output_path}")

    # Print statistics
    total_words = sum(len(seg.get('words', [])) for seg in result.get('segments', []))
    print(f"\n=== Transcription Statistics ===")
    print(f"Total segments: {len(result.get('segments', []))}")
    print(f"Total words: {total_words}")
    print(f"Audio duration: {result.get('segments', [-1])[-1].get('end', 0):.2f}s")

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_whisper_timestamped.py <audio_file> [output_json]")
        sys.exit(1)

    audio_file = sys.argv[1]
    output_json = sys.argv[2] if len(sys.argv) > 2 else None

    # Auto-generate output path if not specified
    if output_json is None:
        audio_path = Path(audio_file)
        output_json = audio_path.parent / f"{audio_path.stem}_whisper_timestamped.json"

    result = transcribe_with_whisper_timestamped(audio_file, output_json)
