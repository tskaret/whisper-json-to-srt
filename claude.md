# JSON to SRT Converter

## Overview

`json_to_srt.py` is an advanced subtitle conversion tool that transforms word-level JSON transcripts into properly formatted SRT subtitle files. This tool combines intelligent timing corrections, buffer allocation, and text formatting to produce high-quality, readable subtitles.

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

### 2. Intelligent Buffer Allocation

Optimizes subtitle display time by distributing gaps between words:

- **50/50 Gap Distribution**: Splits available time gaps evenly between trailing and leading buffers
- **Safety Gap Preservation**: Maintains a 10ms safety gap between segments to prevent overlap
- **Duration Caps**: Enforces maximum subtitle duration (default: 15 seconds)

### 3. Orphan Word Prevention

Improves readability by preventing awkward sentence fragments:

- **Sentence Start Detection**: Identifies new sentences based on capitalization and punctuation
- **Fragment Moving**: Moves short sentence starts (≤15 chars default) to the next subtitle
- **Complete Thoughts**: Ensures related content stays together

### 4. Advanced Hyphenation Logic

Applies continuation hyphens intelligently between subtitles:

**Rules:**
- **NO trailing hyphen** if ends with hard punctuation (`.`, `!`, `?`)
- **NO trailing hyphen** if ends with soft punctuation (`,`, `:`, `;`) - punctuation implies continuation
- **YES trailing hyphen** for regular words or ellipsis continuing to next subtitle
- **NO leading hyphen** if previous subtitle ended with hard punctuation
- **YES leading hyphen** if previous subtitle ended with soft punctuation or regular word
- **NO hyphens** if speaker changed

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
2. **Build Statistics** → Analyze duration patterns from all words
3. **Apply Timing Corrections** → Fix anomalous word durations using statistics
4. **Detect Segment Breaks** → Identify subtitle boundaries (pauses, speaker changes)
5. **Split Oversized Segments** → Handle segments exceeding line/duration limits
6. **Apply Buffers & Caps** → Optimize display time and enforce duration limits
7. **Merge Short Segments** → Combine very short fragments
8. **Generate SRT** → Format as SRT with text wrapping and hyphens

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
4. **Review orphan prevention** - May need adjustment based on content style
5. **Test with/without hyphens** - Some content reads better without continuation hyphens

## Norwegian Language Support

The vowel detection specifically includes Norwegian characters:
- Standard vowels: `a`, `e`, `i`, `o`, `u`, `y`
- Norwegian vowels: `æ`, `ø`, `å`

## Related Files

- `reference_timing_corrections.py` - Original timing correction approach
- `reference_buffer_allocation.py` - Original intelligent buffer approach
- `analyze_timings.py` - Duration analysis tool
- `view_transcript.py` - JSON transcript viewer
- `preview_subtitles.py` - SRT subtitle viewer
- `validate_subtitles.py` - Subtitle validation tool
- `README.md` - Main project documentation
