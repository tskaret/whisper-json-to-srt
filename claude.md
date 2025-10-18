# JSON to SRT Converter

## Quick Start (Get Results in 2 Minutes)

**Most users just need this:**

```bash
# Step 1: Generate transcript with WhisperX
whisperx audio.mp3 --model large-v3 --language no

# Step 2: Generate corrected subtitles with energy detection
python json_to_srt_energy.py audio.mp3 transcript.json

# Step 3: Use the output
# → output_energy/transcript_clean.srt (recommended for final use)
# → output_energy/transcript_with_speakers.srt (includes speaker labels)
```

**That's it!** For advanced features, troubleshooting, or understanding how it works, see the sections below.

---

## Overview

`json_to_srt.py` is an advanced subtitle conversion tool that transforms word-level JSON transcripts into properly formatted SRT subtitle files. This tool combines intelligent timing corrections, buffer allocation, and text formatting to produce high-quality, readable subtitles.

## Critical Bug Fix (2025-10-13)

**⚠️ IMPORTANT: Word Truncation Bug Fixed in json_to_srt_energy.py**

A critical bug was discovered and fixed where words would be **silently deleted** from subtitle output when using tight character limits (e.g., `--max-chars-per-line 37`).

**Issue:** The `wrap_text()` function would truncate words that didn't fit within character limits, but `split_oversized_segment()` wasn't detecting this truncation. Result: Up to 24 words (71% of content!) could be lost from a single subtitle.

**Example:**
- Expected: "Han sa ikke noe om at Gud og Jesus var **inne i bildet**. Begrepet synd var ganske fjernt..."
- Before fix: "Han sa ikke noe om at Gud og Jesus var -" (24 words missing!)
- After fix: All words preserved, properly split across multiple subtitles

**Fix:** Modified `split_oversized_segment()` to detect when `wrap_text()` truncates words by comparing input word count vs. output word count.

**Status:**
- ✅ `json_to_srt_energy.py` - FIXED (2025-10-13)
- ✅ `json_to_srt.py` - Already had fix
- ✅ `json_to_srt_fixed.py` - Already had fix

See `BUG_FIX_SUMMARY.md` for complete technical details.

**Action Required:** Users who previously generated subtitles with `json_to_srt_energy.py` using tight character limits should re-process their files with the fixed version.

## Mandatory Testing ⚠️

**IMPORTANT:** This project includes mandatory testing procedures that must be followed after any code changes.

📋 **See `MANDATORY_TESTING.md` for complete testing requirements**

**Quick summary:**
- **Word Preservation Test:** MUST pass with ≥99% after any code changes
- **Why:** Critical bug (2025-10-13) caused 38.1% word loss - this prevents regression
- **Runtime:** 5-10 minutes for full test suite
- **When to run:** After ANY changes to `json_to_srt*.py` or text processing logic

**For developers setting up a new project:** Create a `MANDATORY_TESTING.md` file during project initialization that defines required tests for your specific codebase. Run these tests after each code change before committing.

## Key Features

### 1. Data-Driven Timing Corrections

The converter analyzes the actual duration patterns in your transcript data to intelligently correct anomalous word timings:

- **Vowel/Syllable Analysis**: Estimates typical word duration based on vowel groups (syllable approximation)
- **Position-Aware Corrections**:
  - First words: Removes pre-speech silence/pauses
  - Last words: Removes post-speech silence/pauses
  - Middle words: Centers typical duration around word midpoint
- **Hard Punctuation Constraint**: Words ending with `.`, `!`, or `?` never exceed their typical duration
- **Statistics Table**: Prints duration statistics organized by syllable count and punctuation type

### 2. Reading Time Buffers

Provides extra reading time by keeping subtitles visible slightly longer after speech ends:

- **Fixed Reading Buffer**: Adds a small fixed amount (~0.3s) after speech for comfortable reading
- **Silence Preservation**: For large pauses (>3s), preserves the silence instead of filling with subtitle
- **Smart Buffer Application**:
  - Small gaps: Distributes available space for reading time (capped at 0.3s)
  - Large pauses: Adds minimal buffer, keeps most silence empty
- **Safety Gap**: Maintains 10ms minimum gap between segments to prevent overlap
- **Duration Caps**: Enforces maximum subtitle duration (default: 15 seconds)

### 3. Orphan Word Prevention

Improves readability by preventing awkward sentence fragments created by technical splitting:

- **Pause-Aware Prevention**: Only merges orphans when there's NO natural speech pause (gap <3s)
- **Respects Speaker Rhythm**: Preserves orphans created by natural pauses to follow speaker's timing
- **Sentence Start Detection**: Identifies new sentences based on capitalization and punctuation
- **Fragment Moving**: Moves short sentence starts (≤15 chars default) created by line overflow
- **Trailing Orphan Detection**: Detects and moves 1-2 orphan words stranded at end of lines (e.g., "...text, spør -")
- **Complete Thoughts**: Ensures related content stays together when technically split

### 4. Advanced Hyphenation Logic

Applies continuation hyphens intelligently between subtitles:

**Rules:**
- **NO trailing hyphen** if ends with hard punctuation (`.`, `!`, `?`)
- **NO trailing hyphen** if ends with soft punctuation (`,`, `:`, `;`) - punctuation implies continuation
- **YES trailing hyphen** for regular words or ellipsis continuing to next subtitle
- **NO leading hyphen** if previous subtitle ended with hard punctuation
- **YES leading hyphen** if previous subtitle ended with soft punctuation or regular word
- **Speaker changes ignored**: Hyphens applied based on punctuation only, regardless of speaker changes
- **Pause-independent**: Hyphens bind sentence continuations together regardless of gap length
- **JSON hyphens preserved**: Hyphens present in the original JSON transcription are preserved with space (e.g., "- gavmildhet")

### 5. Text Wrapping & Line Balancing

Creates visually balanced subtitle lines:

- **Two-Line Optimization**: Balances text evenly across two lines when possible
- **Word Boundary Breaking**: Breaks only at natural word boundaries
- **Character Limits**: Respects maximum characters per line (default: 40 + 4 tolerance)

## Usage

### Basic Usage

```bash
python json_to_srt.py transcript.json
```

This generates two SRT files:
- `transcript_with_speakers.srt` - Includes speaker labels
- `transcript_clean.srt` - Clean subtitles without speaker labels

### Common Options

```bash
# Disable timing corrections
python json_to_srt.py transcript.json --no-timing-corrections

# Custom correction threshold (only correct words longer than 5s)
python json_to_srt.py transcript.json --correction-threshold 5.0

# Specify output directory
python json_to_srt.py transcript.json --output-dir ./output/

# Disable orphan prevention
python json_to_srt.py transcript.json --no-prevent-orphans

# Custom pause threshold for segment breaks
python json_to_srt.py transcript.json --pause-threshold 2.5

# Disable continuation hyphens
python json_to_srt.py transcript.json --no-hyphens
```

### All Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `--output-dir` | Same as input | Output directory for SRT files |
| `--pause-threshold` | 3.0 | Pause threshold for segment breaks (seconds) |
| `--speaker-gap` | 0.150 | Minimum gap for speaker change breaks (seconds) |
| `--safety-gap-ms` | 10 | Safety gap between segments (milliseconds) |
| `--max-chars-per-line` | 40 | Maximum characters per line |
| `--max-lines` | 2 | Maximum lines per subtitle |
| `--overflow-tolerance` | 4 | Extra characters allowed beyond max |
| `--max-subtitle-duration` | 15.0 | Maximum subtitle duration (seconds) |
| `--correction-threshold` | 3.0 | Minimum duration for timing correction (seconds) |
| `--orphan-move-threshold` | 15 | Max characters to move to next subtitle |
| `--no-timing-corrections` | - | Disable intelligent timing corrections |
| `--no-hyphens` | - | Disable continuation hyphens |
| `--no-prevent-orphans` | - | Disable orphan prevention |
| `--no-break-on-speaker-change` | - | Disable breaking on speaker changes |

## Input Format

The script expects a JSON file with the following structure:

```json
{
  "segments": [
    {
      "speaker": "SPEAKER_00",
      "words": [
        {
          "word": "Hello",
          "start": 0.0,
          "end": 0.5,
          "score": 0.95
        },
        {
          "word": "world.",
          "start": 0.6,
          "end": 1.2,
          "score": 0.98
        }
      ]
    }
  ]
}
```

## Important Concepts

### Timing Corrections vs. Reading Buffers

The script applies two distinct timing adjustments:

1. **Timing Corrections** (during word processing):
   - Adjusts individual word durations to remove anomalous silence
   - Based on syllable count and punctuation type
   - Example: A word lasting 2.9s corrected to 1.2s (typical duration)
   - These corrections affect gap calculations between words

2. **Reading Buffers** (after segment creation):
   - Adds small fixed time (~0.3s) for comfortable reading
   - Applied AFTER speech ends, not during
   - Purpose: Give readers time to finish reading before subtitle disappears
   - Does NOT fill large pauses - preserves silence for natural rhythm

### Orphans and Natural Pauses

The script distinguishes between:

- **Technical orphans**: Created by line length limits or duration caps → MERGED back
- **Natural orphans**: Created by speaker pauses (>3s) → PRESERVED to respect timing

Example:
```
"program." with 0.18s gap before it → merges (technical split)
"program." with 3.5s gap before it → keeps separate (natural pause)
```

## Statistics Output

After processing, the script prints detailed statistics:

- **Syllable/Vowel Duration Table**: Shows average durations by syllable count and punctuation type
- **Processing Statistics**:
  - Words processed/skipped
  - Subtitle segments created
  - Speaker changes detected
  - Pause breaks detected
  - Short segments merged
  - Intelligent buffers applied
  - Segments capped by duration
  - Orphan breaks prevented
  - Timing corrections (first/last/total)

## Technical Details

### Word Object

```python
@dataclass
class Word:
    text: str
    start: float
    end: float
    speaker: str
    score: float = 1.0
    is_ellipsis: bool = False
    original_duration: Optional[float] = None
```

### SubtitleSegment Object

```python
@dataclass
class SubtitleSegment:
    words: List[Word]
    start_time: float
    end_time: float
    speaker: str
```

## Processing Pipeline

1. **Load JSON** → Parse word-level data
2. **Build Statistics** → Analyze duration patterns from all words (syllable-based)
3. **Apply Timing Corrections** → Fix anomalous word durations using statistics
   - Global overlap resolution (ensures minimum 10ms gap between all words)
4. **Detect Segment Breaks** → Identify subtitle boundaries based on corrected timings (pauses >pause_threshold, speaker changes)
5. **Split Oversized Segments** → Handle segments exceeding line/duration limits
   - Trailing orphan detection during splitting
6. **Merge Leading Orphans** → Merge orphans created by technical splitting (gap <pause_threshold), preserve natural pauses
7. **Apply Reading Buffers & Caps** → Add small fixed reading time (~0.3s), preserve silence in large pauses
   - Final overlap check and gap enforcement
8. **Merge Short Segments** → Combine very short fragments
9. **Generate SRT** → Format as SRT with text wrapping and hyphens (speaker-independent)

## Error Handling

The script includes comprehensive error handling:

- File not found validation
- JSON parsing error detection
- Invalid timing range checks
- Proper exception messages with suggestions

## Best Practices

1. **Use default settings first** - They work well for most Norwegian speech
2. **Check the statistics table** - Verify that duration estimates make sense for your data
3. **Adjust correction threshold** - If too many corrections, increase threshold
4. **Adjust pause threshold** - Use `--pause-threshold 1.4` for more frequent subtitle breaks on shorter pauses
5. **Review orphan prevention** - May need adjustment based on content style
6. **Test with/without hyphens** - Some content reads better without continuation hyphens
7. **Understand buffer behavior** - Reading buffers (~0.3s) provide reading time, large pauses preserve silence
8. **Timing corrections affect gaps** - Word duration corrections can create or remove pauses, affecting segment breaks
9. **Clean SRT recommended** - Use the `_clean.srt` output for final delivery (no speaker labels)

## Norwegian Language Support

The vowel detection specifically includes Norwegian characters:
- Standard vowels: `a`, `e`, `i`, `o`, `u`, `y`
- Norwegian vowels: `æ`, `ø`, `å`

## Quality Assurance

The script includes comprehensive quality checks:

- **No overlaps**: Global overlap detection and resolution with minimum 10ms gaps
- **Duration control**: Maximum subtitle duration capping (default 15.0s)
- **Line balancing**: Two-line subtitles balanced to within 15 characters difference
- **Line length**: Maximum 40 chars per line with 4-character overflow tolerance
- **Orphan prevention**: Both leading sentence orphans and trailing word orphans detected and moved
- **Gap enforcement**: Minimum safety gap between all subtitles to prevent touching

## Related Files

- `json_to_srt_fixed.py` - Main production script with all improvements
- `waveform_fine_tuning.py` - **NEW:** Advanced waveform-based timing optimization
- `generate_verification_report.py` - **NEW:** Interactive verification system with PowerPoint and HTML
- `view_timing_corrections.py` - View word-level timing corrections
- `validate_subtitles.py` - Subtitle validation tool
- `preview_subtitles.py` - SRT subtitle viewer
- `analyze_timings.py` - Duration analysis tool
- `view_transcript.py` - JSON transcript viewer
- `README.md` - Main project documentation

---

# Waveform-Based Fine-Tuning System

## Overview

The waveform fine-tuning system provides advanced timing optimization by analyzing actual audio waveforms to detect and correct anomalous word timing, particularly for first and last words in sentences which often include pre/post-speech silence.

## Problem Addressed

WhisperX alignment often includes silence in word timing:
- **First words**: Include pre-speech pause (breathing, hesitation)
- **Last words**: Include post-speech silence (trailing pause)
- **Longer segments**: More severe anomalies (up to 20+ seconds!)

**Example from analysis:**
- "søstre." → 2.924s for 2 syllables (should be ~0.3s)
- "ut." → 21.364s for 1 syllable (should be ~0.15s)
- Rate: 73.9% of last words anomalous, 58.7% of first words

## Key Components

### 1. `waveform_fine_tuning.py`

**Advanced Waveform Analysis with Priority-Based Adjustment**

#### Features:
- **Gradient-based onset detection**: Finds actual speech start
- **Decay-based offset detection**: Finds actual speech end with hysteresis
- **Priority system**: Critical/High/Medium/Low based on anomaly severity
- **Adaptive thresholds**: More aggressive for extreme cases
- **Syllable-based anomaly detection**: Duration >2x expected = anomalous
- **Position-aware**: Special handling for first/last words
- **Confidence-based**: Respects high-confidence alignments

#### Priority Levels:
| Priority | Criteria | Max Adjustment | Use Case |
|----------|----------|----------------|----------|
| **CRITICAL** | >5x expected duration | 150ms | Extreme cases (20+ sec) |
| **HIGH** | First/last + >2x expected | 100ms | Common anomalies |
| **MEDIUM** | Low confidence (<0.7) | 80ms | Uncertain alignments |
| **LOW** | Normal words | 30-50ms | Fine-tuning |

#### Usage:

```bash
# Test on 30-second segment
python waveform_fine_tuning.py \
  audio.mp3 transcript.json \
  --start-time 492 \
  --end-time 522 \
  --output-dir output/

# Full processing
python waveform_fine_tuning.py \
  audio.mp3 transcript.json \
  --output-dir output/
```

#### Output:
- `*_adjusted.json` - Timing corrections with metadata
- `*_visualization.png` - Before/after comparison
- Detailed statistics with priority breakdown

---

### 2. `generate_verification_report.py`

**Interactive Verification System for Manual Review**

Creates comprehensive verification materials:
1. **PowerPoint Presentation** - Professional review slides
2. **HTML Interactive Viewer** - Audio playback with sync
3. **JSON Retiming Database** - Complete timing history

#### Features:

**Sentence-Level Analysis:**
- Groups words into sentences (punctuation + capitalization)
- 3-panel visualization per sentence:
  - Original timing (top)
  - Waveform with 3s buffer (middle)
  - Adjusted timing (bottom)
- Color-coded adjustments (green/yellow/orange/red)

**PowerPoint Generation:**
- One slide per sentence
- Embedded waveform video with synchronized playback bar
- Metadata: speaker, adjustment statistics, priority level
- Automatic flagging of sentences needing manual review

**HTML Interactive Viewer:**
- Audio playback synchronized with visual bar
- Manual adjustment sliders for each word
- Save corrections to JSON
- Navigate between sentences
- Export final corrected JSON

**JSON Retiming Database:**
```json
{
  "sentences": [
    {
      "id": 0,
      "text": "God ettermiddag, brødre og søstre.",
      "original_timing": {"start": 0.031, "end": 5.238},
      "adjusted_timing": {"start": 0.031, "end": 2.314},
      "priority": "high",
      "needs_review": true,
      "words": [...]
    }
  ],
  "manual_corrections": [...]
}
```

#### Usage:

```bash
# Generate verification materials
python generate_verification_report.py \
  audio.mp3 \
  adjusted_transcript.json \
  --output-dir verification/

# Output:
#   verification.pptx
#   verification_viewer/index.html
#   retimings.json
```

#### Workflow:

```
1. Run waveform_fine_tuning.py
   ↓
2. Generate verification report
   ↓
3. Review PowerPoint (overview)
   ↓
4. Verify in HTML viewer (detailed)
   ↓
5. Make manual corrections if needed
   ↓
6. Export final JSON
   ↓
7. Generate SRT with json_to_srt.py
```

---

## Complete Workflow Example

### Step 1: Initial Transcription
```bash
# Using WhisperX or similar
whisperx audio.mp3 --model large-v3 --language no --output_dir ./
```

### Step 2: Waveform Fine-Tuning
```bash
# Analyze and correct timing
python waveform_fine_tuning.py \
  audio.mp3 \
  transcript.json \
  --output-dir ./fine_tuned/
```

### Step 3: Generate Verification Report
```bash
# Create PowerPoint and HTML viewer
python generate_verification_report.py \
  audio.mp3 \
  ./fine_tuned/transcript_adjusted.json \
  --output-dir ./verification/
```

### Step 4: Review and Correct
- Open `verification.pptx` for overview
- Open `verification_viewer/index.html` for detailed review
- Play audio and verify synchronization
- Make manual adjustments if needed
- Export corrected JSON

### Step 5: Generate Final Subtitles
```bash
# Convert to SRT
python json_to_srt_fixed.py \
  ./verification/transcript_corrected.json
```

---

## Quality Metrics

**Expected Improvements:**

| Metric | Before | After Waveform | After Manual |
|--------|--------|----------------|--------------|
| Anomalous last words | 73.9% | <10% | <1% |
| Anomalous first words | 58.7% | <15% | <1% |
| Max anomaly duration | 21+ seconds | <0.5s | <0.2s |
| Quality score | 6/10 | 9/10 | 10/10 |

**Flagging Criteria for Manual Review:**
- Any adjustment >200ms
- Any word adjustment >1 second
- Critical priority cases
- Visual inspection shows clear mismatch

---

## Technical Specifications

### Waveform Analysis:
- **Sample rate**: 16 kHz (speech optimized)
- **Window size**: 5ms
- **Hop size**: 2ms
- **Buffer**: ±150-250ms (priority-dependent)
- **Energy threshold**: Dynamic (noise-floor + percentage of max)
- **Hysteresis**: 3-5 frames (stricter for high priority)

### Sentence Grouping:
- **Hard boundaries**: `.`, `!`, `?` + capital/pause
- **Pause threshold**: >3.0s between words
- **Buffer**: 3s before/after for context

### Video Generation (for PowerPoint):
- **Format**: MP4 with H.264
- **Resolution**: 1920x400px (waveform panel)
- **FPS**: 30
- **Synchronized bar**: Red vertical line moving with playback

---

## Installation

```bash
# Core dependencies (already installed)
pip install numpy librosa matplotlib

# For verification system
pip install python-pptx  # PowerPoint generation
pip install pydub        # Audio manipulation
pip install Pillow       # Image processing

# Optional: ffmpeg for video generation
# Download from: https://ffmpeg.org/
```

---

## Configuration

All tools support extensive configuration:

**Waveform Fine-Tuning:**
- `--min-gap`: Minimum gap between words (default: 20ms)
- `--confidence-threshold`: Threshold for aggressive adjustment (default: 0.7)
- `--leading-buffer`: Buffer before each word (default: 10ms)
- `--trailing-buffer`: Buffer after each word (default: 10ms)

**Verification Report:**
- `--sentence-max-duration`: Split long sentences (default: 30s)
- `--buffer-before`: Context before sentence (default: 3s)
- `--buffer-after`: Context after sentence (default: 3s)
- `--flag-threshold`: Adjustment size to flag review (default: 200ms)

---

## Troubleshooting

**Issue:** Too many words flagged for review
- **Solution:** Increase `--flag-threshold` to 300-500ms

**Issue:** Adjustments still too aggressive
- **Solution:** Increase `--confidence-threshold` to 0.8-0.9

**Issue:** PowerPoint videos don't play
- **Solution:** Ensure ffmpeg is installed and in PATH

**Issue:** HTML viewer audio doesn't sync
- **Solution:** Check browser console for errors, ensure audio files are accessible

---

## Advanced Features

### Custom Priority Thresholds

Modify in `waveform_fine_tuning.py`:
```python
# Adjust anomaly detection threshold
is_anomalous = actual_duration > (expected_duration * 3.0)  # Default: 2.0

# Adjust critical threshold
is_critical = (actual_duration / expected_duration) > 10.0  # Default: 5.0
```

### Custom Sentence Grouping

Modify in `generate_verification_report.py`:
```python
# Add soft punctuation as sentence breaks
if word.text.endswith((',', ';', '-')):
    # Custom logic
```

---

## Best Practices

1. **Always run waveform fine-tuning first** - Catch 90%+ of issues automatically
2. **Use verification report for QA** - Visual confirmation builds confidence
3. **Flag extreme cases** - Manual review for >1s adjustments
4. **Test on sample first** - Use 30-60s segment to verify parameters
5. **Document corrections** - Use JSON retiming database for audit trail
6. **Iterate if needed** - Refine thresholds based on results

---

---

# Energy Drop Detection System (NEW)

## Overview

**Breakthrough insight:** Looking for energy DROPS (speech → silence) to identify word boundaries, rather than using threshold-based methods.

The energy drop detection system provides the most accurate timing correction by analyzing actual audio waveforms to detect speech onset and offset.

## Key Components

### 1. `json_to_srt_energy.py` - Complete End-to-End Solution

**All-in-one tool** that combines WhisperX transcription with energy drop detection and SRT generation.

#### Features:
- **Energy drop detection** for precise word boundary correction
- **Waveform analysis** using RMS energy and derivative
- **Automatic correction** of all words (18,760+ words in minutes)
- **Full SRT generation** with all formatting features
- **Statistics reporting** showing correction magnitudes

#### Usage:

```bash
# Basic usage - audio + JSON → corrected SRT
python json_to_srt_energy.py audio.mp3 transcript.json

# Custom output directory
python json_to_srt_energy.py audio.mp3 transcript.json --output-dir output/

# Adjust sensitivity (low/medium/high)
python json_to_srt_energy.py audio.mp3 transcript.json --sensitivity medium

# Custom pause threshold for subtitle breaks
python json_to_srt_energy.py audio.mp3 transcript.json --pause-threshold 2.0
```

#### Output:
- `transcript_with_speakers.srt` - With speaker labels
- `transcript_clean.srt` - Clean version (recommended for final use)
- Console statistics showing corrections applied

#### Performance:
- **18,760 words processed** in ~15 minutes
- **99.99% correction rate** (18,759 words corrected)
- **Average correction: 348.5ms**
- **Maximum correction: 23,454ms** (23.5 seconds!)

---

## How Energy Drop Detection Works

### Theory

**User insight:** "I was looking for energy drops to see where the word would most likely have to end."

The algorithm identifies word boundaries by detecting discrete events in the audio:

1. **Energy RISE** (silence → speech) = Word START
2. **Energy DROP** (speech → silence) = Word END

### Algorithm Steps

```python
# 1. Calculate RMS energy
rms = librosa.feature.rms(audio, frame_length=5ms, hop_length=2ms)

# 2. Smooth the energy curve
rms_smooth = savgol_filter(rms)

# 3. Calculate derivative (rate of change)
derivative = gradient(rms_smooth)

# 4. Find rises and drops
rises = find_peaks(derivative, height=percentile_80)  # Top 20% of rises
drops = find_peaks(-derivative, height=percentile_20)  # Bottom 20% of drops

# 5. Score rise/drop pairs
for rise, drop in combinations:
    duration = drop - rise
    if min_duration <= duration <= max_duration:
        rise_strength = derivative[rise]
        drop_strength = -derivative[drop]
        duration_score = 1.0 - abs(duration - expected) / expected
        score = (rise_strength + drop_strength) * duration_score

        # Choose pair with highest score
```

### Integration with Syllable Counting

The two methods work **synergistically**:

| Method | Purpose |
|--------|---------|
| **Syllable counting** (0.15s per syllable) | Provides EXPECTED duration to guide search |
| **Energy drop detection** | Finds ACTUAL boundaries in waveform |
| **Scoring** | Combines acoustic strength + syllable consistency |

**Example - Word "ut." (1 syllable):**
```
Expected duration: 1 × 0.15s = 0.15s
Search range: 0.075s - 0.45s (±50% to 3×)

Original WhisperX: 21.364s (extreme anomaly!)
Energy corrected: 0.150s ✓ (exactly as expected!)
```

---

## Verification Tools

### 2. `create_timing_comparison_pptx.py`

Generates PowerPoint showing **word-level** timing corrections.

#### Features:
- Shows most dramatic corrections first
- Waveform visualization for each word
- RED = Original WhisperX timing (with silence)
- GREEN = Energy-corrected timing (actual speech)
- Statistics box with correction magnitudes

#### Usage:

```bash
python create_timing_comparison_pptx.py audio.mp3 original.json \
  --output-dir timing_comparison \
  --num-examples 20
```

#### Output:
- `timing_comparison.pptx` - PowerPoint with 20+ example slides
- PNG visualizations for each word

---

### 3. `create_subtitle_sync_pptx.py`

Generates PowerPoint showing **subtitle-level** synchronization results.

#### Features:
- Shows complete subtitle boundaries
- GREEN = Final corrected subtitle timing (entire subtitle)
- BLUE = Original first/last word boundaries (what needed correction)
- Demonstrates how energy detection identifies subtitle start/end points

#### Usage:

```bash
# Show subtitles 100-120
python create_subtitle_sync_pptx.py audio.mp3 original.json corrected.srt \
  --start 100 --end 120 \
  --output-dir subtitle_sync
```

#### Output:
- `subtitle_sync.pptx` - PowerPoint with subtitle visualizations
- Each slide shows one complete subtitle with waveform

**Interpretation:**
- **GREEN area** = Where the subtitle should be displayed
- **BLUE areas** = Where WhisperX originally thought first/last words were
- **Shift statistics** = How much correction was needed

---

## Known Limitations and Issues

### 1. Soft Onset Detection

**Issue:** Algorithm prioritizes **strongest energy rise** over **earliest onset**

**Example (Word "117."):**
- Correct start: 6392.336s (soft consonant onset)
- Detected start: 6393.576s (louder vowel peak)
- Error: +1240ms too late

**Cause:**
- Soft consonants (like numbers "117") have gentle onset
- Algorithm picks the secondary, louder peak instead of initial rise
- Scoring favors strength over earliness

**Potential fixes:**
- Prefer FIRST significant rise above threshold (not strongest)
- Lower rise threshold to catch softer onsets
- Hybrid: Keep original start if within ~200ms of detected rise

### 2. Number/Spelled-out Words

**Issue:** Simple vowel counting fails for numbers

**Example:**
- Text: "117."
- Simple count: 1 syllable (sees one word)
- Actual: 5 syllables ("ett-hun-dre-syv-ten" in Norwegian)
- Expected duration: 0.15s (wrong) vs 0.75s (correct)

**Impact:** Duration constraints become too tight, algorithm may miss valid boundaries

**Potential fix:**
- Detect numbers and expand them to written form before syllable counting
- Use language-specific number-to-word conversion

### 3. Duration Cap Interactions

**Issue:** Some subtitles hit 15-second maximum duration cap

**Example (Subtitle #100):**
- Actual speech ends at ~3952.5s
- Subtitle extended to 3963.0s (15-second cap)
- Creates +11.7s shift for last word

**Cause:** Multiple short sentences grouped into one subtitle exceeding cap

**Not necessarily wrong:** May indicate the subtitle should be split earlier, or cap should be increased

---

## Quality Metrics

### Results from Full Processing (143-minute audio)

| Metric | Value |
|--------|-------|
| **Total words** | 18,760 |
| **Words corrected** | 18,759 (99.99%) |
| **Average correction** | 348.5ms |
| **Maximum correction** | 23,454ms (23.5 seconds!) |
| **Subtitles created** | 320 |
| **Speaker changes** | 108 |
| **Pause breaks** | 281 |

### Extreme Corrections (Top 5)

| Word | Original Duration | Corrected Duration | Time Saved |
|------|------------------|-------------------|------------|
| "2-4." | 23.5s | 0.2s | 23.3s |
| "ut." | 21.4s | 0.2s | 21.2s |
| "." | 21.3s | 0.1s | 21.2s |
| "medfølende." | 20.9s | 0.6s | 20.3s |
| "..." | 19.8s | 0.2s | 19.6s |

**Pattern:** Last words of sentences most affected (post-speech silence included)

---

## Analysis Tools

### 4. `analyze_energy_detection.py`

Deep-dive analysis tool for debugging specific words.

#### Shows:
- Waveform with original vs detected boundaries
- RMS energy curve (what algorithm "sees")
- Energy derivative with ALL rises/drops detected
- Chosen rise/drop pair highlighted
- Statistics and thresholds

#### Usage:

```bash
python analyze_energy_detection.py
# (Edit script to set specific word timing)
```

#### Use cases:
- Understand why algorithm chose specific boundaries
- Debug problematic words
- Tune sensitivity parameters

---

### 5. `analyze_pause_region.py`

Analyzes energy in pause/silence regions.

#### Shows:
- Energy level during pause vs active speech
- Mean/max energy in pause region
- Pause-to-max energy ratio
- Derivative activity (should be near-zero)

#### Output example:
```
Pause Region: 6394.0s - 6400.0s
Mean Energy: 0.013258
Pause/Max Ratio: 8.0% (correctly identified as silence)
```

---

## Best Practices

### Processing Workflow

1. **Generate transcript** with WhisperX:
   ```bash
   whisperx audio.mp3 --model large-v3 --language no
   ```

2. **Apply energy correction and generate SRT**:
   ```bash
   python json_to_srt_energy.py audio.mp3 transcript.json
   ```

3. **Generate verification PowerPoints**:
   ```bash
   # Word-level corrections
   python create_timing_comparison_pptx.py audio.mp3 transcript.json

   # Subtitle synchronization
   python create_subtitle_sync_pptx.py audio.mp3 transcript.json output_energy/transcript_clean.srt
   ```

4. **Review in PowerPoint** to verify quality

5. **Use clean SRT** for final delivery:
   ```
   output_energy/transcript_clean.srt
   ```

### Tuning Parameters

**Sensitivity** (energy detection aggressiveness):
- `--sensitivity high` (default) - Catches top 20% of rises/drops
- `--sensitivity medium` - Top 25% (less aggressive)
- `--sensitivity low` - Top 30% (most conservative)

**Pause threshold** (subtitle breaks):
- `--pause-threshold 3.0` (default) - Break on 3+ second pauses
- `--pause-threshold 1.5` - More frequent breaks (shorter subtitles)
- `--pause-threshold 5.0` - Fewer breaks (longer subtitles)

**Duration caps**:
- `--max-subtitle-duration 15.0` (default) - 15 second maximum
- Increase if subtitles are being artificially split

---

## Future Enhancements

Planned improvements:
- [ ] **Fix soft onset detection** - Prefer earliest rise over strongest
- [ ] **Number-to-word expansion** for Norwegian (correct syllable counting)
- [ ] **Adaptive thresholds** based on local context
- [ ] **Manual correction interface** in HTML viewer
- [ ] **Batch processing** for multiple files
- [ ] **Confidence scoring** per word/subtitle
- [ ] **Integration with video editors** (Premiere, DaVinci Resolve)

---

## Credits

Developed for Norwegian speech (predikant-tale) with focus on:
- Acoustic accuracy (waveform-based energy detection)
- Practical usability (complete end-to-end pipeline)
- Quality assurance (PowerPoint verification system)
- Auditability (complete timing history)

**Key insight:** User observation that "energy drops" identify word boundaries led to breakthrough in timing accuracy.
