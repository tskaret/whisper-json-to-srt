#!/usr/bin/env python3
"""
Convert whisper-timestamped JSON format to WhisperX format

This allows us to use the same json_to_srt_energy.py script on both formats
"""

import json
import sys
from pathlib import Path


def convert_whisper_timestamped_to_whisperx(input_json, output_json=None):
    """
    Convert whisper-timestamped format to WhisperX format

    whisper-timestamped format:
    {
      "segments": [
        {
          "id": 0,
          "seek": 0,
          "start": 0.031,
          "end": 5.238,
          "text": " God ettermiddag, brødre og søstre.",
          "tokens": [...],
          "temperature": 0.0,
          "avg_logprob": -0.25,
          "compression_ratio": 1.15,
          "no_speech_prob": 0.0,
          "confidence": 0.90,
          "words": [
            {"text": "God", "start": 0.031, "end": 0.271, "confidence": 0.95},
            {"text": "ettermiddag,", "start": 0.331, "end": 1.173, "confidence": 0.92},
            ...
          ]
        }
      ]
    }

    WhisperX format:
    {
      "segments": [
        {
          "speaker": "SPEAKER_00",  # We'll use "SPEAKER_00" for all (no diarization)
          "words": [
            {"word": "God", "start": 0.031, "end": 0.271, "score": 0.95},
            {"word": "ettermiddag,", "start": 0.331, "end": 1.173, "score": 0.92},
            ...
          ]
        }
      ]
    }
    """
    print(f"Loading whisper-timestamped JSON: {input_json}")
    with open(input_json, 'r', encoding='utf-8') as f:
        wt_data = json.load(f)

    # Convert format
    whisperx_data = {"segments": []}

    for segment in wt_data.get('segments', []):
        words = []
        for word_obj in segment.get('words', []):
            words.append({
                "word": word_obj['text'],
                "start": word_obj['start'],
                "end": word_obj['end'],
                "score": word_obj.get('confidence', 1.0)
            })

        if words:  # Only add segments with words
            whisperx_data['segments'].append({
                "speaker": "SPEAKER_00",  # Default speaker (no diarization)
                "words": words
            })

    # Save converted format
    if output_json is None:
        input_path = Path(input_json)
        output_json = input_path.parent / f"{input_path.stem}_whisperx_format.json"

    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(whisperx_data, f, indent=2, ensure_ascii=False)

    print(f"Converted JSON saved to: {output_json}")
    print(f"\nStatistics:")
    print(f"  Segments: {len(whisperx_data['segments'])}")
    total_words = sum(len(seg['words']) for seg in whisperx_data['segments'])
    print(f"  Total words: {total_words}")

    return whisperx_data


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_whisper_timestamped_to_whisperx_format.py <input_json> [output_json]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    convert_whisper_timestamped_to_whisperx(input_file, output_file)
