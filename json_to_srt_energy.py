#!/usr/bin/env python3
"""
JSON to SRT Converter with Energy Drop Detection
================================================

Combines WhisperX word-level transcripts with waveform-based energy drop detection
to produce accurate, well-formatted SRT subtitle files.

Features:
- Energy drop detection for precise word boundary correction
- Intelligent segment breaking (pauses, speaker changes)
- Text wrapping and line balancing
- Orphan word prevention
- Continuation hyphens
- Reading time buffers
"""

import json
import argparse
import os
import sys
import re
import numpy as np
import librosa
from scipy import signal
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import tempfile
import shutil
import logging

# Constants - General
NORWEGIAN_VOWELS = 'aeiouyæøå'
HARD_PUNCTUATION = ('.', '!', '?')
SOFT_PUNCTUATION = (',', ':', ';')
MIN_WORD_DURATION = 0.05
MIN_SEGMENT_DURATION = 0.5
DEFAULT_READING_BUFFER = 0.3

# Constants - Energy Detection
AUDIO_SEGMENT_BUFFER = 0.5  # seconds of buffer before/after word
RMS_FRAME_LENGTH_MS = 5  # milliseconds
RMS_HOP_LENGTH_MS = 2  # milliseconds
MIN_RMS_FRAMES = 10  # minimum RMS frames for analysis
SAVGOL_WINDOW_MIN = 11  # Savitzky-Golay filter window length
NOISE_FLOOR_PERCENTILE = 10  # percentile for noise floor calculation
SPEECH_THRESHOLD_MULTIPLIER = 3.0  # multiply noise floor by this
ENERGY_CHECK_WINDOW_MS = 50  # milliseconds to check around timestamp
MIN_SUSTAINED_SILENCE_MS = 100  # milliseconds of silence to confirm word end
MIN_SUSTAINED_SPEECH_MS = 50  # milliseconds of speech to confirm word start
DURATION_MIN_FACTOR = 0.5  # minimum duration = expected × this
DURATION_MAX_FACTOR = 3.0  # maximum duration = expected × this
PROGRESS_UPDATE_INTERVAL = 100  # update progress bar every N words
NEW_THOUGHT_PAUSE_THRESHOLD = 3.0  # seconds - pause indicating new sentence

# Constants - Security
ALLOWED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.wma'}
MAX_AUDIO_FILE_SIZE = 500 * 1024 * 1024  # 500MB
MAX_JSON_FILE_SIZE = 100 * 1024 * 1024  # 100MB
MAX_SEGMENTS = 10000  # Maximum number of segments in JSON
MAX_WORDS_PER_SEGMENT = 1000  # Maximum words per segment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('json_to_srt_energy.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def validate_file_path(file_path: str, base_dir: Optional[str] = None, must_exist: bool = False) -> Path:
    """Validate and sanitize file path to prevent path traversal attacks.

    Args:
        file_path: User-supplied file path
        base_dir: Optional base directory to restrict access to
        must_exist: If True, raise error if file doesn't exist

    Returns:
        Validated Path object

    Raises:
        ValueError: If path traversal detected or path is invalid
        FileNotFoundError: If must_exist=True and file doesn't exist
    """
    try:
        # Convert to Path and resolve to absolute path
        path = Path(file_path).resolve()
    except (OSError, RuntimeError) as e:
        logger.warning(f"Invalid file path: {file_path}")
        raise ValueError(f"Invalid file path: {file_path}") from e

    # Check for suspicious patterns
    if '..' in path.parts:
        logger.warning(f"Path traversal attempt detected: {file_path}")
        raise ValueError(f"Path traversal detected: {file_path}")

    # If base_dir specified, ensure path is within it
    if base_dir:
        try:
            base = Path(base_dir).resolve()
            path.relative_to(base)
        except ValueError:
            logger.warning(f"Path outside base directory: {file_path} not in {base_dir}")
            raise ValueError(f"Path {file_path} is outside allowed directory {base_dir}")

    # Check existence if required
    if must_exist and not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    return path


def validate_audio_file(audio_path: str, base_dir: Optional[str] = None) -> Path:
    """Validate audio file path and properties.

    Args:
        audio_path: User-supplied audio file path
        base_dir: Optional base directory to restrict access to

    Returns:
        Validated Path object

    Raises:
        ValueError: If file is invalid
        FileNotFoundError: If file doesn't exist
    """
    # Validate path
    safe_path = validate_file_path(audio_path, base_dir=base_dir, must_exist=True)

    # Check extension
    if safe_path.suffix.lower() not in ALLOWED_AUDIO_EXTENSIONS:
        logger.warning(f"Unsupported audio format: {safe_path.suffix}")
        raise ValueError(
            f"Unsupported audio format: {safe_path.suffix}. "
            f"Allowed formats: {', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}"
        )

    # Check file size
    try:
        file_size = safe_path.stat().st_size
    except OSError as e:
        logger.error(f"Cannot access audio file: {safe_path}")
        raise ValueError(f"Cannot access audio file: {audio_path}") from e

    if file_size > MAX_AUDIO_FILE_SIZE:
        size_mb = file_size / 1024 / 1024
        max_mb = MAX_AUDIO_FILE_SIZE / 1024 / 1024
        logger.warning(f"Audio file too large: {size_mb:.1f}MB (max {max_mb:.0f}MB)")
        raise ValueError(
            f"Audio file too large: {size_mb:.1f}MB (maximum {max_mb:.0f}MB)"
        )

    return safe_path


def safe_json_load(file_path: Path) -> dict:
    """Safely load JSON with size and structure validation.

    Args:
        file_path: Validated Path to JSON file

    Returns:
        Parsed JSON data

    Raises:
        ValueError: If JSON is invalid or exceeds limits
    """
    # Check file size
    try:
        file_size = file_path.stat().st_size
    except OSError as e:
        logger.error(f"Cannot access JSON file: {file_path}")
        raise ValueError(f"Cannot access JSON file: {file_path}") from e

    if file_size > MAX_JSON_FILE_SIZE:
        size_mb = file_size / 1024 / 1024
        max_mb = MAX_JSON_FILE_SIZE / 1024 / 1024
        logger.warning(f"JSON file too large: {size_mb:.1f}MB (max {max_mb:.0f}MB)")
        raise ValueError(
            f"JSON file too large: {size_mb:.1f}MB (maximum {max_mb:.0f}MB)"
        )

    # Load JSON
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format in {file_path}: {e}")
        raise ValueError(f"Invalid JSON format: {e}") from e
    except OSError as e:
        logger.error(f"Error reading JSON file {file_path}: {e}")
        raise ValueError(f"Error reading file: {e}") from e

    # Validate structure
    if not isinstance(data, dict):
        logger.error("Invalid JSON: Root must be an object")
        raise ValueError("Invalid JSON: Root element must be an object")

    if 'segments' not in data:
        logger.error("Invalid JSON: Missing 'segments' key")
        raise ValueError("Invalid JSON: Missing required 'segments' key")

    segments = data.get('segments', [])
    if not isinstance(segments, list):
        logger.error("Invalid JSON: 'segments' must be an array")
        raise ValueError("Invalid JSON: 'segments' must be an array")

    if len(segments) > MAX_SEGMENTS:
        logger.warning(f"Too many segments: {len(segments)} (max {MAX_SEGMENTS})")
        raise ValueError(
            f"Too many segments in JSON: {len(segments)} (maximum {MAX_SEGMENTS})"
        )

    # Validate segment structure
    for i, segment in enumerate(segments):
        if not isinstance(segment, dict):
            logger.error(f"Invalid segment {i}: Must be an object")
            raise ValueError(f"Invalid segment {i}: Must be an object")

        words = segment.get('words', [])
        if not isinstance(words, list):
            logger.error(f"Invalid segment {i}: 'words' must be an array")
            raise ValueError(f"Invalid segment {i}: 'words' must be an array")

        if len(words) > MAX_WORDS_PER_SEGMENT:
            logger.warning(f"Segment {i} has too many words: {len(words)}")
            raise ValueError(
                f"Segment {i} has too many words: {len(words)} (maximum {MAX_WORDS_PER_SEGMENT})"
            )

    return data


def safe_write_file(output_path: Path, content: str) -> None:
    """Safely write file using atomic operations.

    Args:
        output_path: Validated Path to output file
        content: Content to write

    Raises:
        ValueError: If cannot write file
        PermissionError: If no write permission
    """
    # Check if parent directory exists
    if not output_path.parent.exists():
        logger.error(f"Output directory does not exist: {output_path.parent}")
        raise ValueError(f"Output directory does not exist: {output_path.parent}")

    # Check write permissions
    if not os.access(output_path.parent, os.W_OK):
        logger.error(f"No write permission for directory: {output_path.parent}")
        raise PermissionError(f"No write permission for directory: {output_path.parent}")

    # Use temporary file for atomic write
    temp_fd = None
    temp_path = None
    try:
        temp_fd, temp_path = tempfile.mkstemp(
            dir=output_path.parent,
            prefix=f".tmp_{output_path.name}_",
            text=True
        )

        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            f.write(content)
        temp_fd = None  # File is now closed

        # Atomic rename
        shutil.move(temp_path, output_path)
        logger.info(f"Successfully wrote file: {output_path.name}")

    except Exception as e:
        logger.error(f"Failed to write file {output_path}: {e}")
        # Clean up temp file on error
        if temp_fd is not None:
            try:
                os.close(temp_fd)
            except:
                pass
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass
        raise RuntimeError(f"Failed to write file: {e}") from e


@dataclass
class Word:
    """Represents a word with timing and metadata"""
    text: str
    start: float
    end: float
    speaker: str
    score: float = 1.0
    original_start: Optional[float] = None
    original_end: Optional[float] = None
    adjustment_magnitude: Optional[float] = None
    adjustment_reason: Optional[str] = None

    def count_syllables(self) -> int:
        """Count syllables using vowel groups"""
        clean_word = re.sub(r'[^\w]', '', self.text)
        vowel_groups = re.findall(rf'[{NORWEGIAN_VOWELS}]+', clean_word.lower())
        return max(1, len(vowel_groups))


@dataclass
class SubtitleSegment:
    """Represents a subtitle segment with multiple words"""
    words: List[Word]
    start_time: float
    end_time: float
    speaker: str


@dataclass
class ProcessingStats:
    """Statistics for processing operations"""
    words_processed: int = 0
    words_corrected: int = 0
    segments_created: int = 0
    speaker_changes: int = 0
    pause_breaks: int = 0
    segments_merged: int = 0
    orphan_breaks_prevented: int = 0
    buffers_applied: int = 0
    segments_capped: int = 0
    avg_correction_ms: float = 0.0
    max_correction_ms: float = 0.0


class EnergyDropCorrector:
    """Applies energy drop detection to correct word timings"""

    def __init__(self, audio_path: str, sr: int = 16000):
        # Validate audio file
        safe_path = validate_audio_file(audio_path)

        print(f"Loading audio: {safe_path.name}")
        try:
            self.audio, self.sr = librosa.load(str(safe_path), sr=sr, mono=True)
            logger.info(f"Audio loaded successfully: {len(self.audio)/sr:.1f}s, sr={sr}Hz")
        except Exception as e:
            logger.error(f"Failed to load audio file: {e}")
            raise ValueError(f"Failed to load audio file: {e}") from e

        print(f"Audio loaded: {len(self.audio)/sr:.1f}s, sr={sr}Hz")

    def extract_segment(self, start: float, end: float, buffer: float = AUDIO_SEGMENT_BUFFER) -> Tuple[np.ndarray, float]:
        """Extract audio segment with buffer"""
        actual_start = max(0, start - buffer)
        actual_end = min(len(self.audio) / self.sr, end + buffer)
        start_sample = int(actual_start * self.sr)
        end_sample = int(actual_end * self.sr)
        segment = self.audio[start_sample:end_sample]
        return segment, actual_start

    def correct_word_timing(self, word: Word, sensitivity: str = 'high', is_last_before_punct: bool = False, is_first_in_sentence: bool = False) -> Word:
        """Apply energy-based timing correction

        Strategy:
        1. For FIRST word in sentence:
           - Keep original END (if energy validated)
           - Find START by detecting sustained energy rise (speech begins)
        2. For LAST word before punctuation:
           - Keep original START (if energy validated)
           - Find END by detecting sustained silence (100ms+ low energy)
        3. For regular words:
           - Validate and keep original START (if energy present)
           - Use energy drop detection for END
        4. If validation fails: Use full energy drop detection
        """
        audio, seg_start = self.extract_segment(word.original_start, word.original_end, buffer=AUDIO_SEGMENT_BUFFER)

        frame_length = int(RMS_FRAME_LENGTH_MS / 1000 * self.sr)
        hop_length = int(RMS_HOP_LENGTH_MS / 1000 * self.sr)
        rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]

        if len(rms) < MIN_RMS_FRAMES:
            return word  # Too short, keep original

        # Smooth RMS
        window_len = min(SAVGOL_WINDOW_MIN, len(rms) // 2 * 2 + 1)
        if window_len < 3:
            return word
        rms_smooth = signal.savgol_filter(rms, window_length=window_len, polyorder=2)

        # Time array for RMS frames
        rms_times = seg_start + np.arange(len(rms_smooth)) * hop_length / self.sr

        # Calculate speech threshold
        noise_floor = np.percentile(rms_smooth, NOISE_FLOOR_PERCENTILE)
        speech_threshold = noise_floor * SPEECH_THRESHOLD_MULTIPLIER

        # SPECIAL CASE: First word in sentence - validate END and find START
        if is_first_in_sentence:
            # Validate original end has speech energy
            end_idx = np.argmin(np.abs(rms_times - word.original_end))

            # Check energy at original end ±ENERGY_CHECK_WINDOW_MS
            check_window = int(ENERGY_CHECK_WINDOW_MS / 1000 / (hop_length / self.sr))
            end_range = slice(max(0, end_idx - check_window),
                            min(len(rms_smooth), end_idx + check_window))

            energy_at_end = np.max(rms_smooth[end_range])

            if energy_at_end > speech_threshold:
                # Original end is valid - KEEP IT
                corrected_end = word.original_end

                # Find sustained energy RISE for start (speech begins)
                speech_frames = int(MIN_SUSTAINED_SPEECH_MS / 1000 / (hop_length / self.sr))

                corrected_start = word.original_start  # fallback

                # Search backwards from end to find where energy rises and STAYS high
                for i in range(end_idx - speech_frames, -1, -1):
                    # Check if energy STAYS above threshold for MIN_SPEECH_DURATION
                    if i + speech_frames < len(rms_smooth):
                        if np.all(rms_smooth[i:i+speech_frames] > speech_threshold):
                            corrected_start = rms_times[i]
                            # Don't break - keep searching backwards to find earliest sustained speech
                        else:
                            # Found the start - where sustained speech begins
                            if corrected_start != word.original_start:
                                break

                word.start = corrected_start
                word.end = corrected_end
                word.adjustment_magnitude = max(
                    abs(corrected_start - word.original_start),
                    abs(corrected_end - word.original_end)
                )
                word.adjustment_reason = "Sustained energy rise start + validated end"

                return word
            # If no energy at original end, fall through to normal detection

        # STEP 1: ALWAYS validate original start
        start_idx = np.argmin(np.abs(rms_times - word.original_start))

        # Check energy at original start +/- ENERGY_CHECK_WINDOW_MS
        check_window = int(ENERGY_CHECK_WINDOW_MS / 1000 / (hop_length / self.sr))
        start_range = slice(max(0, start_idx - check_window),
                          min(len(rms_smooth), start_idx + check_window))

        energy_at_start = np.max(rms_smooth[start_range])
        start_validated = energy_at_start > speech_threshold

        if start_validated:
            # Original start has speech - KEEP IT
            corrected_start = word.original_start

            # STEP 2: Determine how to correct END
            if is_last_before_punct:
                # Find sustained silence for last words before punctuation
                silence_frames = int(MIN_SUSTAINED_SILENCE_MS / 1000 / (hop_length / self.sr))

                corrected_end = word.original_end  # fallback

                # Search from start onwards for sustained silence
                for i in range(start_idx, len(rms_smooth) - silence_frames):
                    # Check if energy stays below threshold for MIN_SILENCE_DURATION
                    if np.all(rms_smooth[i:i+silence_frames] < speech_threshold):
                        corrected_end = rms_times[i]
                        break

                word.start = corrected_start
                word.end = corrected_end
                word.adjustment_magnitude = max(
                    abs(corrected_start - word.original_start),
                    abs(corrected_end - word.original_end)
                )
                word.adjustment_reason = "Validated start + sustained pause end"

                return word
            else:
                # Regular word: Use energy drop detection for END only
                derivative = np.gradient(rms_smooth)

                # Find drops AFTER validated start
                if sensitivity == 'high':
                    drop_threshold = np.percentile(derivative, 20)
                elif sensitivity == 'medium':
                    drop_threshold = np.percentile(derivative, 25)
                else:
                    drop_threshold = np.percentile(derivative, 30)

                # Look for drops after start_idx
                drops_after_start = []
                for i in range(start_idx, len(derivative)):
                    if -derivative[i] > -drop_threshold:
                        drops_after_start.append(i)

                if drops_after_start:
                    # Find steepest drop
                    best_end_idx = drops_after_start[np.argmax(-derivative[drops_after_start])]
                    corrected_end = rms_times[best_end_idx]
                else:
                    corrected_end = word.original_end  # fallback

                word.start = corrected_start
                word.end = corrected_end
                word.adjustment_magnitude = max(
                    abs(corrected_start - word.original_start),
                    abs(corrected_end - word.original_end)
                )
                word.adjustment_reason = "Validated start + energy drop end"

                return word

        # STEP 3: If start NOT validated, use full energy drop detection
        derivative = np.gradient(rms_smooth)

        # Find rises and drops based on sensitivity
        if sensitivity == 'high':
            rise_threshold = np.percentile(derivative, 80)
            drop_threshold = np.percentile(derivative, 20)
        elif sensitivity == 'medium':
            rise_threshold = np.percentile(derivative, 75)
            drop_threshold = np.percentile(derivative, 25)
        else:  # 'low'
            rise_threshold = np.percentile(derivative, 70)
            drop_threshold = np.percentile(derivative, 30)

        rises, _ = signal.find_peaks(derivative, height=rise_threshold, distance=5)
        drops, _ = signal.find_peaks(-derivative, height=-drop_threshold, distance=5)

        if len(rises) == 0 or len(drops) == 0:
            return word

        # Find best rise/drop pair
        expected_duration = word.count_syllables() * 0.15
        min_duration = expected_duration * DURATION_MIN_FACTOR
        max_duration = expected_duration * DURATION_MAX_FACTOR

        best_start_idx = None
        best_end_idx = None
        best_score = 0

        for rise_idx in rises:
            for drop_idx in drops:
                if drop_idx <= rise_idx:
                    continue

                duration = (drop_idx - rise_idx) * hop_length / self.sr

                if duration < min_duration or duration > max_duration:
                    continue

                rise_strength = derivative[rise_idx]
                drop_strength = -derivative[drop_idx]
                duration_score = 1.0 - abs(duration - expected_duration) / expected_duration

                score = (rise_strength + drop_strength) * duration_score

                if score > best_score:
                    best_score = score
                    best_start_idx = rise_idx
                    best_end_idx = drop_idx

        if best_start_idx is None or best_end_idx is None:
            # Fallback: Use steepest rise and steepest drop
            best_start_idx = rises[np.argmax(derivative[rises])]
            best_end_idx = drops[np.argmax(-derivative[drops])]

        corrected_start = seg_start + (best_start_idx * hop_length / self.sr)
        corrected_end = seg_start + (best_end_idx * hop_length / self.sr)

        word.start = corrected_start
        word.end = corrected_end
        word.adjustment_magnitude = max(
            abs(corrected_start - word.original_start),
            abs(corrected_end - word.original_end)
        )
        word.adjustment_reason = f"Energy drop detection (sens={sensitivity})"

        return word


class SRTConverter:
    """Converts word-level JSON to SRT with energy drop correction"""

    def __init__(self, audio_path: str, pause_threshold: float = 3.0,
                 max_chars_per_line: int = 40, max_lines: int = 2,
                 overflow_tolerance: int = 4, add_hyphens: bool = True,
                 max_subtitle_duration: float = 15.0, prevent_orphans: bool = True,
                 orphan_move_threshold: int = 15, break_on_speaker_change: bool = True,
                 speaker_change_threshold: float = 0.150, safety_gap_ms: int = 10,
                 energy_sensitivity: str = 'high'):

        self.audio_path = audio_path
        self.pause_threshold = pause_threshold
        self.max_chars_per_line = max_chars_per_line
        self.max_lines = max_lines
        self.overflow_tolerance = overflow_tolerance
        self.add_hyphens = add_hyphens
        self.max_subtitle_duration = max_subtitle_duration
        self.prevent_orphans = prevent_orphans
        self.orphan_move_threshold = orphan_move_threshold
        self.break_on_speaker_change = break_on_speaker_change
        self.speaker_change_threshold = speaker_change_threshold
        self.safety_gap = safety_gap_ms / 1000.0
        self.energy_sensitivity = energy_sensitivity
        self.stats = ProcessingStats()

        # Initialize energy drop corrector
        self.corrector = EnergyDropCorrector(audio_path)

    def load_json_data(self, file_path: str) -> List[Word]:
        """Load WhisperX JSON and convert to Word objects"""
        # Validate and load JSON safely
        safe_path = validate_file_path(file_path, must_exist=True)
        data = safe_json_load(safe_path)

        segments = data.get('segments', [])
        if not segments:
            raise ValueError("No 'segments' found in JSON data")

        print(f"Processing {len(segments)} segments...")

        words = []
        for segment in segments:
            speaker = segment.get('speaker', 'UNKNOWN')
            segment_words = segment.get('words', [])

            for word_data in segment_words:
                word_text = word_data.get('word', '').strip()
                if not word_text:
                    continue

                start_time = float(word_data.get('start', 0.0))
                end_time = float(word_data.get('end', 0.0))

                if end_time <= start_time:
                    continue

                word = Word(
                    text=word_text,
                    start=start_time,
                    end=end_time,
                    speaker=speaker,
                    score=float(word_data.get('score', 1.0)),
                    original_start=start_time,
                    original_end=end_time
                )
                words.append(word)

        words.sort(key=lambda w: w.start)
        return words

    def apply_energy_corrections(self, words: List[Word]) -> List[Word]:
        """Apply energy drop correction to all words"""
        print(f"\nApplying energy drop correction to {len(words)} words...")

        corrected_words = []
        corrections = []
        sustained_pause_count = 0
        sustained_rise_count = 0
        validated_start_count = 0
        full_energy_drop_count = 0

        for i, word in enumerate(words):
            if (i + 1) % PROGRESS_UPDATE_INTERVAL == 0:
                # Progress bar: [=========>          ] 50% (5000/10000)
                percent = (i + 1) * 100 // len(words)
                bar_length = 40
                filled = bar_length * (i + 1) // len(words)
                bar = '=' * filled + '>' + ' ' * (bar_length - filled - 1)
                print(f"\r  [{bar}] {percent}% ({i+1}/{len(words)})", end='', flush=True)

            # Check if this is the last word before punctuation
            is_last_before_punct = word.text.strip().endswith(HARD_PUNCTUATION)

            # Check if this is the first word in a sentence
            is_first_in_sentence = False
            if i == 0:
                # First word of entire transcript
                is_first_in_sentence = True
            else:
                prev_word = words[i - 1]
                # First word after punctuation
                if prev_word.text.strip().endswith(HARD_PUNCTUATION):
                    is_first_in_sentence = True
                # Or first word after long pause (>3s = new thought)
                elif word.start - prev_word.end > NEW_THOUGHT_PAUSE_THRESHOLD:
                    is_first_in_sentence = True

            corrected_word = self.corrector.correct_word_timing(
                word,
                self.energy_sensitivity,
                is_last_before_punct=is_last_before_punct,
                is_first_in_sentence=is_first_in_sentence
            )
            corrected_words.append(corrected_word)

            if corrected_word.adjustment_magnitude:
                corrections.append(corrected_word.adjustment_magnitude * 1000)  # Convert to ms
                self.stats.words_corrected += 1

                # Count correction types
                if corrected_word.adjustment_reason:
                    if "Sustained pause" in corrected_word.adjustment_reason:
                        sustained_pause_count += 1
                    if "Sustained energy rise" in corrected_word.adjustment_reason:
                        sustained_rise_count += 1
                    if "Validated start" in corrected_word.adjustment_reason:
                        validated_start_count += 1
                    if "Energy drop detection" in corrected_word.adjustment_reason and "Validated" not in corrected_word.adjustment_reason:
                        full_energy_drop_count += 1

        # Calculate statistics
        if corrections:
            self.stats.avg_correction_ms = np.mean(corrections)
            self.stats.max_correction_ms = np.max(corrections)

        print()  # Newline after progress bar
        print(f"  Corrected {self.stats.words_corrected}/{len(words)} words")
        print(f"  Sustained energy rise (first words): {sustained_rise_count} words")
        print(f"  Sustained pause detection (last words): {sustained_pause_count} words")
        print(f"  Validated start (kept original): {validated_start_count} words")
        print(f"  Full energy drop detection: {full_energy_drop_count} words")
        print(f"  Average correction: {self.stats.avg_correction_ms:.1f}ms")
        print(f"  Maximum correction: {self.stats.max_correction_ms:.1f}ms")

        # Ensure no overlaps
        for i in range(1, len(corrected_words)):
            prev_word = corrected_words[i - 1]
            curr_word = corrected_words[i]

            if curr_word.start < prev_word.end + self.safety_gap:
                curr_word.start = prev_word.end + self.safety_gap
                if curr_word.end < curr_word.start + MIN_WORD_DURATION:
                    curr_word.end = curr_word.start + MIN_WORD_DURATION

        return corrected_words

    def detect_segment_breaks(self, words: List[Word]) -> List[int]:
        """Detect where subtitle segments should break"""
        breaks = []

        for i in range(1, len(words)):
            current_word = words[i]
            prev_word = words[i - 1]

            pause_duration = current_word.start - prev_word.end
            is_speaker_change = prev_word.speaker != current_word.speaker

            break_on_long_pause = pause_duration > self.pause_threshold
            break_on_speaker_change = (self.break_on_speaker_change and
                                       is_speaker_change and
                                       pause_duration > self.speaker_change_threshold)

            if break_on_long_pause or break_on_speaker_change:
                if break_on_long_pause:
                    self.stats.pause_breaks += 1
                if is_speaker_change:
                    self.stats.speaker_changes += 1
                breaks.append(i)

        return breaks

    def wrap_text(self, words: List[Word]) -> List[str]:
        """Wrap text into balanced lines"""
        if not words:
            return []

        word_texts = [word.text.strip() for word in words]
        full_text = " ".join(word_texts)

        hyphen_reserve = 2
        effective_limit = self.max_chars_per_line + self.overflow_tolerance - hyphen_reserve

        if len(full_text) <= effective_limit:
            return [full_text]

        if self.max_lines == 1:
            return [full_text[:effective_limit]]

        return self._balance_two_lines(word_texts, effective_limit)

    def _balance_two_lines(self, word_texts: List[str], effective_limit: int) -> List[str]:
        """Balance text across exactly two lines"""
        if not word_texts:
            return []

        full_text = " ".join(word_texts)
        total_length = len(full_text)
        target_first_line = total_length // 2

        best_split = 0
        best_balance = float('inf')

        for i in range(1, len(word_texts)):
            first_line = " ".join(word_texts[:i])
            second_line = " ".join(word_texts[i:])

            if len(first_line) > effective_limit or len(second_line) > effective_limit:
                continue

            balance = abs(len(first_line) - target_first_line)

            if balance < best_balance:
                best_balance = balance
                best_split = i

        if best_split == 0:
            current_line = ""
            for word_text in word_texts:
                test_line = current_line + (" " if current_line else "") + word_text
                if len(test_line) <= effective_limit:
                    current_line = test_line
                else:
                    break
            return [current_line] if current_line else [word_texts[0]]

        first_line = " ".join(word_texts[:best_split])
        second_line = " ".join(word_texts[best_split:])

        return [first_line.strip(), second_line.strip()]

    def is_sentence_start(self, word: Word, prev_word: Optional[Word]) -> bool:
        """Detect if a word starts a new sentence"""
        if prev_word is None:
            return True

        prev_text = prev_word.text.strip()
        if prev_text.endswith(('.', '!', '?')):
            return True

        current_text = word.text.strip()
        if current_text and current_text[0].isupper():
            if prev_text.endswith(('.', '!', '?', ':', ';', ',')):
                return True

        return False

    def split_oversized_segment(self, words: List[Word]) -> List[List[Word]]:
        """Split segments that are too long"""
        if not words:
            return []

        segments = []
        current_segment = []

        for i, word in enumerate(words):
            test_segment = current_segment + [word]
            lines = self.wrap_text(test_segment)

            # Check if wrap_text is truncating words
            wrapped_text = ' '.join(lines)
            wrapped_word_count = len(wrapped_text.split())

            would_exceed = len(lines) > self.max_lines
            is_truncating = wrapped_word_count < len(test_segment)

            if (would_exceed or is_truncating) and current_segment:
                segments.append(current_segment[:])
                current_segment = [word]
            else:
                current_segment.append(word)

        if current_segment:
            segments.append(current_segment)

        return segments

    def merge_leading_orphans(self, segments: List[SubtitleSegment]) -> List[SubtitleSegment]:
        """Merge short orphan words back to previous segment"""
        if not self.prevent_orphans or len(segments) < 2:
            return segments

        merged_segments = []
        i = 0

        while i < len(segments):
            current_segment = segments[i]

            if i > 0 and len(current_segment.words) <= 3:
                first_words_text = ' '.join(word.text for word in current_segment.words[:2])
                first_words_length = len(first_words_text)

                if first_words_length <= self.orphan_move_threshold:
                    prev_segment = merged_segments[-1]

                    if prev_segment.speaker == current_segment.speaker:
                        gap = current_segment.words[0].start - prev_segment.words[-1].end

                        if gap <= self.pause_threshold:
                            merged_words = prev_segment.words + current_segment.words
                            merged_segments.pop()

                            word_groups = self.split_oversized_segment(merged_words)

                            for word_group in word_groups:
                                if word_group:
                                    resplit_segment = SubtitleSegment(
                                        words=word_group,
                                        start_time=word_group[0].start,
                                        end_time=word_group[-1].end,
                                        speaker=word_group[0].speaker
                                    )
                                    merged_segments.append(resplit_segment)

                            self.stats.orphan_breaks_prevented += 1
                            i += 1
                            continue

            merged_segments.append(current_segment)
            i += 1

        return merged_segments

    def create_segments(self, words: List[Word]) -> List[SubtitleSegment]:
        """Create subtitle segments from words"""
        if not words:
            return []

        break_indices = self.detect_segment_breaks(words)
        segments = []

        all_breaks = [0] + break_indices + [len(words)]

        for i in range(len(all_breaks) - 1):
            start_idx = all_breaks[i]
            end_idx = all_breaks[i + 1]

            segment_words = words[start_idx:end_idx]
            if not segment_words:
                continue

            word_groups = self.split_oversized_segment(segment_words)

            for word_group in word_groups:
                if not word_group:
                    continue

                segment = SubtitleSegment(
                    words=word_group,
                    start_time=word_group[0].start,
                    end_time=word_group[-1].end,
                    speaker=word_group[0].speaker
                )

                segments.append(segment)
                self.stats.segments_created += 1

        segments = self.merge_leading_orphans(segments)
        return segments

    def apply_buffers_and_caps(self, segments: List[SubtitleSegment]) -> None:
        """Apply reading time buffers and duration caps"""
        # Apply reading buffers
        for i in range(len(segments) - 1):
            current_segment = segments[i]
            next_segment = segments[i + 1]

            actual_end_current = current_segment.words[-1].end
            actual_start_next = next_segment.words[0].start

            gap = actual_start_next - actual_end_current

            # Check if current segment ends with hard punctuation
            # If so, DON'T extend end time - sustained pause detection already found accurate boundary
            last_word_text = current_segment.words[-1].text.strip()
            ends_with_hard_punct = last_word_text.endswith(HARD_PUNCTUATION)

            # Check if next segment starts with capital letter (new sentence)
            # If so, DON'T move start time back - sustained energy rise detection already found accurate boundary
            first_word_text = next_segment.words[0].text.strip()
            starts_with_capital = first_word_text and first_word_text[0].isupper()

            if gap > self.pause_threshold:
                max_trailing_buffer = min(DEFAULT_READING_BUFFER, gap / 2)
                max_leading_buffer = min(DEFAULT_READING_BUFFER, gap / 2)

                if max_trailing_buffer + max_leading_buffer + self.safety_gap < gap:
                    # Only apply trailing buffer if NOT hard punctuation
                    if not ends_with_hard_punct:
                        current_segment.end_time += max_trailing_buffer
                    # Only apply leading buffer if NOT new sentence
                    if not starts_with_capital:
                        next_segment.start_time -= max_leading_buffer
                    self.stats.buffers_applied += 1
            elif gap > self.safety_gap:
                available_buffer = gap - self.safety_gap
                trailing_buffer = min(DEFAULT_READING_BUFFER, available_buffer / 2)
                leading_buffer = min(DEFAULT_READING_BUFFER, available_buffer / 2)

                # Only apply trailing buffer if NOT hard punctuation
                if not ends_with_hard_punct:
                    current_segment.end_time += trailing_buffer
                # Only apply leading buffer if NOT new sentence
                if not starts_with_capital:
                    next_segment.start_time -= leading_buffer
                self.stats.buffers_applied += 1

        # Apply duration caps
        for seg in segments:
            duration = seg.end_time - seg.start_time
            if duration > self.max_subtitle_duration:
                seg.end_time = seg.start_time + self.max_subtitle_duration
                self.stats.segments_capped += 1

        # Ensure safety gaps
        for i in range(len(segments) - 1):
            current_segment = segments[i]
            next_segment = segments[i + 1]

            gap = next_segment.start_time - current_segment.end_time

            if gap < self.safety_gap:
                current_segment.end_time = next_segment.start_time - self.safety_gap

                if current_segment.end_time < current_segment.start_time + 0.1:
                    next_segment.start_time = current_segment.end_time + self.safety_gap

    def merge_short_segments(self, segments: List[SubtitleSegment]) -> List[SubtitleSegment]:
        """Merge very short segments"""
        if not segments:
            return []

        merged_segments = []
        i = 0

        while i < len(segments):
            current_segment = segments[i]
            current_duration = current_segment.end_time - current_segment.start_time

            if current_duration < MIN_SEGMENT_DURATION:
                if (i + 1 < len(segments) and
                    segments[i + 1].speaker == current_segment.speaker):

                    next_segment = segments[i + 1]
                    merged_segment = SubtitleSegment(
                        words=current_segment.words + next_segment.words,
                        start_time=current_segment.start_time,
                        end_time=next_segment.end_time,
                        speaker=current_segment.speaker
                    )

                    merged_segments.append(merged_segment)
                    i += 2
                    self.stats.segments_merged += 1
                    continue

                elif (merged_segments and
                      merged_segments[-1].speaker == current_segment.speaker):

                    prev_segment = merged_segments.pop()
                    merged_segment = SubtitleSegment(
                        words=prev_segment.words + current_segment.words,
                        start_time=prev_segment.start_time,
                        end_time=current_segment.end_time,
                        speaker=prev_segment.speaker
                    )

                    merged_segments.append(merged_segment)
                    i += 1
                    self.stats.segments_merged += 1
                    continue

            merged_segments.append(current_segment)
            i += 1

        return merged_segments

    @staticmethod
    def ends_with_hard_punctuation(text: str) -> bool:
        return text.strip().endswith(HARD_PUNCTUATION) if text.strip() else False

    @staticmethod
    def ends_with_soft_punctuation(text: str) -> bool:
        return text.strip().endswith(SOFT_PUNCTUATION) if text.strip() else False

    def apply_hyphens(self, text: str, subtitle_index: int, all_segments: List[SubtitleSegment]) -> str:
        """Apply continuation hyphens between subtitles"""
        current_segment = all_segments[subtitle_index - 1]
        lines = text.split('\n')

        # Leading hyphen
        should_start_with_hyphen = False
        if subtitle_index > 1:
            prev_segment = all_segments[subtitle_index - 2]
            prev_last_word = prev_segment.words[-1].text.strip()

            if not self.ends_with_hard_punctuation(prev_last_word):
                should_start_with_hyphen = True

        # Trailing hyphen
        should_end_with_hyphen = False
        if subtitle_index < len(all_segments):
            current_last_word = current_segment.words[-1].text.strip()

            if (not self.ends_with_hard_punctuation(current_last_word) and
                not self.ends_with_soft_punctuation(current_last_word)):
                should_end_with_hyphen = True

        if should_start_with_hyphen and not lines[0].startswith('- '):
            lines[0] = '- ' + lines[0]

        if should_end_with_hyphen and not lines[-1].endswith(' -'):
            lines[-1] = lines[-1] + ' -'

        return '\n'.join(lines)

    @staticmethod
    def format_srt_time(seconds: float) -> str:
        """Format time for SRT (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

    def generate_srt_content(self, segments: List[SubtitleSegment], include_speakers: bool = False) -> str:
        """Generate SRT format content"""
        srt_lines = []

        for i, segment in enumerate(segments, 1):
            start_time = self.format_srt_time(segment.start_time)
            end_time = self.format_srt_time(segment.end_time)

            wrapped_lines = self.wrap_text(segment.words)
            text = '\n'.join(wrapped_lines)

            if include_speakers and segment.speaker != 'UNKNOWN':
                speaker_prefix = f"[{segment.speaker}]: "
                lines = text.split('\n')
                if lines:
                    lines[0] = speaker_prefix + lines[0]
                    text = '\n'.join(lines)

            if self.add_hyphens:
                text = self.apply_hyphens(text, i, segments)

            srt_lines.extend([
                str(i),
                f"{start_time} --> {end_time}",
                text,
                ""
            ])

        return '\n'.join(srt_lines)

    def process_file(self, input_path: str, output_dir: Optional[str] = None) -> Tuple[str, str]:
        """Process JSON file and generate SRT files"""
        # Validate input path
        safe_input = validate_file_path(input_path, must_exist=True)

        # Determine and validate output directory
        if output_dir is None:
            output_dir = str(safe_input.parent)

        safe_output_dir = validate_file_path(output_dir)

        # Create output directory safely
        if not safe_output_dir.exists():
            try:
                safe_output_dir.mkdir(parents=True, mode=0o755)
                logger.info(f"Created output directory: {safe_output_dir}")
            except Exception as e:
                logger.error(f"Failed to create output directory: {e}")
                raise RuntimeError(f"Failed to create output directory: {e}") from e

        base_name = safe_input.stem
        output_with_speakers = safe_output_dir / f"{base_name}_with_speakers.srt"
        output_clean = safe_output_dir / f"{base_name}_clean.srt"

        # Load and process
        print(f"\nLoading JSON file: {input_path}")
        words = self.load_json_data(input_path)
        self.stats.words_processed = len(words)

        # Apply energy corrections
        words = self.apply_energy_corrections(words)

        # Create segments
        print("\nCreating subtitle segments...")
        segments = self.create_segments(words)

        print("Applying buffers and duration caps...")
        self.apply_buffers_and_caps(segments)

        print("Merging short segments...")
        segments = self.merge_short_segments(segments)

        print("\nGenerating SRT files...")
        srt_with_speakers = self.generate_srt_content(segments, include_speakers=True)
        srt_clean = self.generate_srt_content(segments, include_speakers=False)

        # Write files safely
        safe_write_file(output_with_speakers, srt_with_speakers)
        safe_write_file(output_clean, srt_clean)

        return str(output_with_speakers), str(output_clean)

    def print_stats(self):
        """Print processing statistics"""
        print(f"\n{'='*60}")
        print("PROCESSING STATISTICS")
        print(f"{'='*60}")
        print(f"Total words processed: {self.stats.words_processed}")
        print(f"Words corrected by energy detection: {self.stats.words_corrected}")
        print(f"  Average correction: {self.stats.avg_correction_ms:.1f}ms")
        print(f"  Maximum correction: {self.stats.max_correction_ms:.1f}ms")
        print(f"\nSubtitle segments created: {self.stats.segments_created}")
        print(f"Speaker changes detected: {self.stats.speaker_changes}")
        print(f"Pause breaks detected: {self.stats.pause_breaks}")
        print(f"Short segments merged: {self.stats.segments_merged}")
        print(f"Reading buffers applied: {self.stats.buffers_applied}")
        print(f"Segments capped by duration: {self.stats.segments_capped}")
        print(f"Orphan breaks prevented: {self.stats.orphan_breaks_prevented}")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="JSON to SRT Converter with Energy Drop Detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
    # Basic usage
    python json_to_srt_energy.py audio.mp3 transcript.json

    # Specify output directory
    python json_to_srt_energy.py audio.mp3 transcript.json --output-dir ./output/

    # Adjust sensitivity
    python json_to_srt_energy.py audio.mp3 transcript.json --sensitivity medium

    # Custom pause threshold
    python json_to_srt_energy.py audio.mp3 transcript.json --pause-threshold 2.0

FEATURES:
    - Energy drop detection for accurate word boundaries
    - Automatic timing correction for anomalous durations
    - Intelligent text wrapping and line balancing
    - Continuation hyphens between subtitles
    - Orphan word prevention
    - Reading time buffers
        """
    )

    parser.add_argument('audio_file', help='Audio file (MP3, WAV, etc.)')
    parser.add_argument('input_json', help='Input JSON file (WhisperX format)')
    parser.add_argument('--output-dir', help='Output directory for SRT files')
    parser.add_argument('--sensitivity', choices=['low', 'medium', 'high'], default='high',
                       help='Energy detection sensitivity (default: high)')
    parser.add_argument('--pause-threshold', type=float, default=3.0,
                       help='Pause threshold for breaks (default: 3.0s)')
    parser.add_argument('--speaker-gap', type=float, default=0.150,
                       help='Min gap for speaker change breaks (default: 0.150s)')
    parser.add_argument('--safety-gap-ms', type=int, default=10,
                       help='Safety gap between segments (default: 10ms)')
    parser.add_argument('--max-chars-per-line', type=int, default=40,
                       help='Max characters per line (default: 40)')
    parser.add_argument('--max-lines', type=int, default=2,
                       help='Max lines per subtitle (default: 2)')
    parser.add_argument('--overflow-tolerance', type=int, default=4,
                       help='Character overflow tolerance (default: 4)')
    parser.add_argument('--max-subtitle-duration', type=float, default=15.0,
                       help='Max subtitle duration (default: 15.0s)')
    parser.add_argument('--no-hyphens', action='store_false', dest='add_hyphens',
                       help='Disable continuation hyphens')
    parser.add_argument('--no-prevent-orphans', action='store_false', dest='prevent_orphans',
                       help='Disable orphan prevention')
    parser.add_argument('--no-break-on-speaker-change', action='store_false',
                       dest='break_on_speaker_change', help='Disable speaker change breaks')

    args = parser.parse_args()

    print("="*60)
    print("JSON to SRT Converter with Energy Drop Detection")
    print("="*60)
    print(f"Audio file: {args.audio_file}")
    print(f"JSON file: {args.input_json}")
    print(f"Energy sensitivity: {args.sensitivity}")
    print(f"Pause threshold: {args.pause_threshold}s")

    try:
        converter = SRTConverter(
            audio_path=args.audio_file,
            pause_threshold=args.pause_threshold,
            max_chars_per_line=args.max_chars_per_line,
            max_lines=args.max_lines,
            overflow_tolerance=args.overflow_tolerance,
            add_hyphens=args.add_hyphens,
            max_subtitle_duration=args.max_subtitle_duration,
            prevent_orphans=args.prevent_orphans,
            break_on_speaker_change=args.break_on_speaker_change,
            speaker_change_threshold=args.speaker_gap,
            safety_gap_ms=args.safety_gap_ms,
            energy_sensitivity=args.sensitivity
        )

        output_with_speakers, output_clean = converter.process_file(args.input_json, args.output_dir)

        print(f"\n{'='*60}")
        print("CONVERSION COMPLETED SUCCESSFULLY!")
        print(f"{'='*60}")
        print(f"SRT with speakers: {Path(output_with_speakers).name}")
        print(f"SRT without speakers: {Path(output_clean).name}")

        converter.print_stats()

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        print(f"\nError: File not found")
        print(f"Suggestion: Check that the input file path is correct")
        sys.exit(1)

    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        print(f"\nError: Invalid input - {e}")
        print(f"Suggestion: Check parameter values and file formats")
        sys.exit(1)

    except PermissionError as e:
        logger.error(f"Permission denied: {e}")
        print(f"\nError: Permission denied")
        print(f"Suggestion: Check file and directory permissions")
        sys.exit(1)

    except RuntimeError as e:
        logger.error(f"Runtime error: {e}")
        print(f"\nError: {e}")
        sys.exit(1)

    except Exception as e:
        # Log full error internally
        logger.exception("Unexpected error occurred")

        # Show generic error to user
        print(f"\nError: An unexpected error occurred")
        print(f"Suggestion: Check the log file 'json_to_srt_energy.log' for details")
        sys.exit(1)


if __name__ == "__main__":
    main()
