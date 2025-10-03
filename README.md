================================================================================
WORD-LEVEL JSON TO SRT CONVERTER
================================================================================

OVERVIEW
--------
json_to_srt.py is a production-ready subtitle generation tool that converts
word-level JSON transcripts into properly formatted SRT files.

KEY FEATURES
------------
1. INTELLIGENT BUFFER ALLOCATION
   - Analyzes actual gaps between speech segments
   - Distributes available buffer space (50/50 split)
   - Preserves 10ms safety gap between subtitles
   - Only applies buffers when gap exceeds safety threshold

2. DATA-DRIVEN TIMING CORRECTIONS
   - Builds duration statistics from actual audio data
   - Corrects anomalous word durations based on:
     * Vowel/syllable count (Norwegian language support)
     * Punctuation type (hard/soft/none)
     * Word position (first/middle/last)
   - Hard punctuation constraint (never exceeds typical duration)

3. ORPHAN WORD PREVENTION
   - Detects sentence starts at end of subtitles
   - Moves short fragments (<=15 chars) to next subtitle
   - Ensures complete thoughts remain together
   - Improves readability and comprehension

4. DURATION CAP ENFORCEMENT
   - Default: 15 seconds maximum per subtitle
   - Caps buffer-extended segments
   - Configurable via --max-subtitle-duration

5. ADVANCED HYPHENATION
   - Hard punctuation (. ! ?) = NO hyphens
   - Soft punctuation (, : ;) = NO trailing hyphens
   - Regular words/ellipsis = YES hyphens for continuation
   - Speaker-aware hyphenation

6. SEGMENT MERGING
   - Merges very short segments (<0.5s)
   - Speaker-aware merging
   - Reduces fragmentation

USAGE
-----
Basic usage:
  python json_to_srt.py transcript.json

With custom settings:
  python json_to_srt.py transcript.json \
    --output-dir ./output \
    --max-subtitle-duration 20.0 \
    --speaker-gap 0.2 \
    --safety-gap-ms 50

Disable advanced features:
  python json_to_srt.py transcript.json \
    --no-timing-corrections \
    --no-prevent-orphans \
    --no-hyphens

COMMAND-LINE OPTIONS
--------------------
  --output-dir                    Output directory for SRT files
  --pause-threshold              Pause threshold for breaks (default: 3.0s)
  --speaker-gap                  Speaker change threshold (default: 0.150s)
  --safety-gap-ms                Safety gap between segments (default: 10ms)
  --max-chars-per-line           Characters per line (default: 40)
  --max-lines                    Lines per subtitle (default: 2)
  --overflow-tolerance           Character overflow tolerance (default: 4)
  --max-subtitle-duration        Maximum duration (default: 15.0s)
  --correction-threshold         Timing correction threshold (default: 3.0s)
  --orphan-move-threshold        Orphan detection limit (default: 15 chars)
  
  --no-timing-corrections        Disable timing corrections
  --no-prevent-orphans          Disable orphan prevention
  --no-hyphens                  Disable continuation hyphens
  --no-break-on-speaker-change  Disable speaker change breaks

OUTPUT
------
Two SRT files are generated:
  1. *_with_speakers.srt - Includes speaker labels [SPEAKER_NAME]:
  2. *_clean.srt - Clean subtitles without speaker labels

STATISTICS
----------
The script reports comprehensive statistics:
  - Words processed
  - Segments created
  - Speaker changes detected
  - Pause breaks detected
  - Intelligent buffers applied
  - Segments capped by duration
  - Orphan breaks prevented
  - Timing corrections applied

COMPATIBILITY
-------------
  - Python 3.7+
  - Windows/Linux/macOS
  - Norwegian language support (æ, ø, å)
  - UTF-8 encoding

TESTING
-------
Comprehensive testing performed on:
  - Large dataset (19,275 words, 1,799 segments)
  - All command-line options verified
  - Duration caps enforced correctly
  - Hyphenation logic validated
  - Buffer allocation tested with various gap sizes

UTILITY TOOLS
-------------
Additional tools are provided for analysis and validation:

1. analyze_timings.py
   Purpose: Analyzes word duration patterns from JSON transcripts
   Usage: python analyze_timings.py <json_file> [--csv output.csv]
   Features:
   - Groups words by character count and punctuation type
   - Calculates average durations for different word categories
   - Exports statistics to CSV for further analysis
   - Helps understand timing patterns in your transcript data

2. view_transcript.py
   Purpose: Display word-level JSON transcript data in readable format
   Usage: python view_transcript.py <json_file> [--time HH:MM:SS]
   Features:
   - Shows word-by-word timing information
   - Displays gaps between words
   - Optional time filtering to jump to specific sections
   - Useful for inspecting raw transcript data

3. preview_subtitles.py
   Purpose: Display SRT subtitle files in columnar format
   Usage: python preview_subtitles.py <srt_file> [--time HH:MM:SS]
   Features:
   - Shows subtitle timing and text in organized columns
   - Optional time filtering
   - Easier to read than raw SRT format
   - Quick preview of generated subtitles

4. validate_subtitles.py
   Purpose: Comprehensive validation of SRT subtitle files
   Usage: python validate_subtitles.py <srt_file>
   Features:
   - Detects overlapping subtitles
   - Finds double hyphen issues
   - Identifies timing problems (too short/long/negative)
   - Checks text flow issues
   - Reports detailed statistics and specific problem locations

REFERENCE IMPLEMENTATIONS
--------------------------
Two previous iterations are kept for reference:

1. reference_timing_corrections.py
   - Original implementation of timing corrections
   - Orphan prevention algorithm
   - Segment merging features

2. reference_buffer_allocation.py
   - Original intelligent buffer allocation
   - Safety gap preservation
   - Clean production implementation

These files serve as documentation of the development process and can be
consulted to understand specific feature implementations.

================================================================================
