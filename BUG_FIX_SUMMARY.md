# Critical Bug Fix: Word Truncation in json_to_srt_energy.py

## Bug Description

**Severity:** CRITICAL - Complete data loss (words silently deleted from output)

**Affected Files:**
- `json_to_srt_energy.py` (FIXED)
- `json_to_srt.py` (already had fix)
- `json_to_srt_fixed.py` (already had fix)

## The Problem

When using `--max-chars-per-line` parameter with longer segments, the `wrap_text()` function would **silently truncate** words that didn't fit within the character limit, causing complete content loss.

### Example from User's Report

**Command:**
```bash
python json_to_srt_energy.py --output-dir 05Transcribe.energy \
  --max-chars-per-line 37 --pause-threshold 1.2 \
  --no-break-on-speaker-change \
  04-LørdagEttermiddag.mp3 04-LørdagEttermiddag.json
```

**Result:**
- Subtitle #516: "Han sa ikke noe om at Gud og Jesus var -"
- **MISSING:** "inne i bildet" + 23 additional words completely deleted!

### Root Cause Analysis

1. **Segment Creation:** Energy correction created segments with many words
   - Example: Segment with 34 words starting at 3822.653s

2. **Text Wrapping:** `wrap_text()` function called with `max_chars_per_line=37`
   - Effective limit: 37 + 4 (tolerance) - 2 (hyphen reserve) = **39 characters**
   - Full text: 160 characters (way over limit)

3. **Silent Truncation:** In `_balance_two_lines()` function (line 369-377):
   ```python
   if best_split == 0:  # Can't fit in two lines
       current_line = ""
       for word_text in word_texts:
           test_line = current_line + (" " if current_line else "") + word_text
           if len(test_line) <= effective_limit:
               current_line = test_line
           else:
               break  # ⚠️ STOPS HERE - remaining words LOST!
       return [current_line] if current_line else [word_texts[0]]
   ```

4. **No Split Detection:** `split_oversized_segment()` didn't detect truncation:
   ```python
   # OLD CODE - only checked line count, not word count!
   would_exceed = len(lines) > self.max_lines  # Always False when truncating!
   ```

### Test Results

**With 34-word segment and max_chars_per_line=37:**
- Input: 34 words, 160 characters
- Output from wrap_text(): 1 line, **10 words**, 38 characters
- **Result: 24 words LOST** (71% data loss!)

## The Fix

### Modified Function: `split_oversized_segment()` (line 400-428)

**Added truncation detection:**

```python
def split_oversized_segment(self, words: List[Word]) -> List[List[Word]]:
    """Split segments that are too long"""
    if not words:
        return []

    segments = []
    current_segment = []

    for i, word in enumerate(words):
        test_segment = current_segment + [word]
        lines = self.wrap_text(test_segment)

        # ✅ NEW: Check if wrap_text is truncating words
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

    if current_segment:
        segments.append(current_segment)

    return segments
```

**Key changes:**
1. Count words in wrapped output: `wrapped_word_count = len(wrapped_text.split())`
2. Detect truncation: `is_truncating = wrapped_word_count < len(test_segment)`
3. Split on either condition: `if (would_exceed or is_truncating) and current_segment:`

## Verification

### Before Fix:
```
Subtitle #516 (01:03:42,653 → 01:03:52,653):
"Han sa ikke noe om at Gud og Jesus var -"

Total segments: 1682
Missing: "inne i bildet. Begrepet synd var ganske fjernt for meg. Jeg tenkte noen ganger gjør man feil, og så går man bare videre i"
```

### After Fix:
```
Subtitle #663 (01:03:42,653 → 01:03:47,433):
"Han sa ikke noe om at Gud og Jesus var inne i bildet. Begrepet synd var ganske -"

Subtitle #664 (01:03:47,443 → 01:03:51,944):
"- fjernt for meg. Jeg tenkte noen ganger"

Total segments: 2230 (548 more segments created due to proper splitting)
All words present! ✓
```

## Impact

**Statistics Comparison:**

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total segments | 1,682 | 2,230 | +548 (+33%) |
| Segments capped | 0 | 0 | - |
| Words lost | Unknown | 0 | Fixed! |

**Benefits:**
- ✅ No more silent word loss
- ✅ All content preserved
- ✅ Proper segment splitting when character limits are tight
- ✅ Maintains reading time and duration constraints

## Files Status

| File | Status | Notes |
|------|--------|-------|
| `json_to_srt_energy.py` | ✅ FIXED | Applied fix on 2025-10-13 |
| `json_to_srt_fixed.py` | ✅ Already had fix | Line 702: `would_truncate = wrapped_word_count < expected_word_count` |
| `json_to_srt.py` | ✅ Already had fix | Line 635: `would_truncate = wrapped_word_count < expected_word_count` |

## Testing

To test the fix:

```bash
# Run with tight character limit
python json_to_srt_energy.py --output-dir test_output \
  --max-chars-per-line 37 --pause-threshold 1.2 \
  audio.mp3 transcript.json

# Check for "inne i bildet" at ~01:03:42
grep -B 2 -A 1 "inne i bildet" test_output/*_clean.srt
```

## Related Issues

This bug would affect any subtitle with:
- Long segments (many words)
- Tight character limits (--max-chars-per-line <40)
- No natural pause breaks (--pause-threshold >1.0)

Users should re-process any subtitles generated with `json_to_srt_energy.py` before this fix.

## Date Fixed

2025-10-13

## Credits

Bug discovered and reported by user testing Norwegian speech transcription with tight character constraints.

Root cause identified through comprehensive debugging including:
- Segment creation tracing
- Energy correction analysis
- Text wrapping behavior testing
- Word count verification
