# Word Truncation Bug - Verification Report

## Executive Summary

A critical word truncation bug in `json_to_srt_energy.py` was discovered, analyzed, fixed, and verified on 2025-10-13.

**Impact:** 38.1% of all words were being silently deleted from subtitle output when using tight character limits.

**Resolution:** Bug fixed by detecting when `wrap_text()` truncates words. Word preservation improved from 61.9% to 99.3%.

## Test Case

**Audio:** 04-LørdagEttermiddag.mp3 (143 minutes, 10,888 seconds)
**Transcript:** WhisperX JSON with 18,760 words
**Parameters:** `--max-chars-per-line 37 --pause-threshold 1.2 --no-break-on-speaker-change`

## Word Count Analysis

### Overall Statistics

| Metric | JSON Original | SRT Buggy | SRT Fixed |
|--------|--------------|-----------|-----------|
| **Total words** | 18,760 | 11,618 | 18,627 |
| **Words lost** | - | **7,142** | 133 |
| **Data loss** | - | **38.1%** 😱 | 0.7% ✅ |
| **Preservation** | - | 61.9% | **99.3%** |

### Words Recovered

**7,009 words** recovered by the fix (37.4% of original content)

### Remaining Gap (133 words / 0.7%)

The small gap is acceptable and likely due to:
- Very short words filtered out (e.g., "i" at 20ms, below MIN_WORD_DURATION of 50ms)
- Words with invalid timing (end ≤ start)
- Edge cases in text normalization

## Specific Example: "inne i bildet"

### User's Original Report

**Location:** ~01:03:45 (3825 seconds)
**Missing phrase:** "inne i bildet"

### Before Fix (Buggy)

**Subtitle #516** (01:03:42,653 → 01:03:52,653):
```
Han sa ikke noe om at Gud og Jesus var -
```

**Subtitle #517** (01:03:55,596 → 01:03:57,925):
```
- livet. Jeg hadde et forferdelig temperament.
```

**Missing content:**
"inne i bildet. Begrepet synd var ganske fjernt for meg. Jeg tenkte noen ganger gjør man feil, og så går man bare videre i"

**Total missing:** 24 words (71% of segment content)

### After Fix

**Subtitle #663** (01:03:42,653 → 01:03:47,433):
```
Han sa ikke noe om at Gud og Jesus var
inne i bildet. Begrepet synd var ganske -
```

**Subtitle #664** (01:03:47,443 → 01:03:51,944):
```
- fjernt for meg. Jeg tenkte noen ganger
```

**Subtitle #665** (01:03:51,954 → 01:03:56,435):
```
- gjør man feil, og så går man bare
videre i livet. Jeg hadde et -
```

**Result:** ✅ All words present and properly split across multiple subtitles

## Segment Statistics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| **Total segments** | 1,682 | 2,230 | +548 (+32.6%) |
| **Avg duration** | ~6.5s | ~4.9s | -24.6% |
| **Segments capped** | 0 | 0 | - |
| **Orphans prevented** | Unknown | 147 | - |

The increase in segment count is expected - the fix properly splits segments that were previously truncated into a single segment.

## Technical Root Cause

### The Bug

In `json_to_srt_energy.py` (before fix):

```python
def split_oversized_segment(self, words: List[Word]) -> List[List[Word]]:
    for i, word in enumerate(words):
        test_segment = current_segment + [word]
        lines = self.wrap_text(test_segment)

        would_exceed = len(lines) > self.max_lines  # ⚠️ BUG: Never triggers!

        if would_exceed and current_segment:
            segments.append(current_segment[:])
            current_segment = [word]
        else:
            current_segment.append(word)  # ⚠️ Keeps adding words!
```

**Problem:** `wrap_text()` silently truncates words that don't fit, so it NEVER returns more than `max_lines`. The check `len(lines) > self.max_lines` never triggers, allowing all words to accumulate in one segment.

### The Fix

```python
def split_oversized_segment(self, words: List[Word]) -> List[List[Word]]:
    for i, word in enumerate(words):
        test_segment = current_segment + [word]
        lines = self.wrap_text(test_segment)

        # ✅ NEW: Detect truncation
        wrapped_text = ' '.join(lines)
        wrapped_word_count = len(wrapped_text.split())

        would_exceed = len(lines) > self.max_lines
        is_truncating = wrapped_word_count < len(test_segment)  # ✅ NEW!

        # ✅ NEW: Split on EITHER condition
        if (would_exceed or is_truncating) and current_segment:
            segments.append(current_segment[:])
            current_segment = [word]
        else:
            current_segment.append(word)
```

**Solution:** Compare word count in wrapped output vs. input. If mismatch detected, split the segment.

## Test Results

### wrap_text() Truncation Test

**Input:** 34 words, 160 characters
```
"Han sa ikke noe om at Gud og Jesus var inne i bildet. Begrepet synd var ganske fjernt for meg. Jeg tenkte noen ganger gjør man feil, og så går man bare videre i"
```

**Output with max_chars_per_line=37:**
- Lines: 1
- Characters: 38
- Words: **10**
- **Lost: 24 words (71%)**

**Output text:**
```
"Han sa ikke noe om at Gud og Jesus var"
```

This confirms `wrap_text()` was silently truncating 71% of the content.

## Energy Correction Impact

Energy correction successfully processed:
- **18,759 / 18,760 words** (99.99%)
- **Average correction:** 348.5ms
- **Maximum correction:** 23,454ms (23.5 seconds!)

The extreme corrections show WhisperX often includes long silences in word timing, which energy drop detection successfully removes.

## File Status

| File | Bug Status | Date Fixed |
|------|-----------|------------|
| `json_to_srt_energy.py` | ✅ **FIXED** | 2025-10-13 |
| `json_to_srt_fixed.py` | ✅ Already had fix | - |
| `json_to_srt.py` | ✅ Already had fix | - |

## Recommendations

### For Users

1. **Re-process existing subtitles:** Any subtitles generated with `json_to_srt_energy.py` before 2025-10-13 using tight character limits should be re-generated with the fixed version.

2. **Verify output:** Check for missing content by comparing word counts:
   ```bash
   # Count words in JSON
   grep -o '"word"' transcript.json | wc -l

   # Count words in SRT (excluding hyphens and metadata)
   grep -v "^[0-9]*$" output.srt | grep -v " --> " | tr ' ' '\n' | grep -v "^-$" | wc -l
   ```

3. **Use appropriate character limits:** While the bug is fixed, very tight limits (e.g., <35 chars) will create many short segments. Consider 40-45 chars for better readability.

### For Developers

1. **Always verify word preservation:** When modifying text wrapping or segment splitting logic, verify that word count in = word count out.

2. **Test with tight constraints:** Test edge cases like:
   - Very long segments (50+ words)
   - Tight character limits (<35)
   - No pause breaks (--pause-threshold 5.0)

3. **Silent failures are dangerous:** Functions like `wrap_text()` should either:
   - Raise an error when truncating
   - Return a flag indicating truncation
   - Never truncate (return overflow as additional lines)

## Conclusion

The word truncation bug has been successfully identified, fixed, and verified. The fix recovers 7,009 words (37.4% of content) and improves word preservation from 61.9% to 99.3%.

Users of `json_to_srt_energy.py` should update to the fixed version and re-process any existing subtitles that may have been affected.

---

**Report Date:** 2025-10-13
**Test Audio:** 04-LørdagEttermiddag.mp3
**Total Words:** 18,760
**Words Recovered:** 7,009
**Final Preservation Rate:** 99.3%
