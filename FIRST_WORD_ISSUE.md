# First Word Issue - Additional Problem Discovered

**Date:** 2025-10-13
**Context:** After implementing sustained pause detection for last words

---

## Problem

### Sustained Pause Detection Fixed Last Words ✓

**"søstre."** now correctly detected:
- Original: 2.314s → 5.238s (includes 2.6s silence)
- Corrected: 2.314s → 2.628s ✓ (actual speech)

### But Created New Problem with First Words ✗

**"God"** incorrectly detected:
- Original: 0.031s → 0.311s (likely correct)
- Corrected: 0.598s → 1.110s ✗ (WRONG - too late!)

**Result:**
```srt
1
00:00:00,598 --> 00:00:01,110
God ettermiddag,

2
00:00:01,336 --> 00:00:02,927
- brødre og søstre.
```

**User wanted:**
```srt
1
00:00:00,031 --> 00:00:03,034
God ettermiddag, brødre og søstre.
```

---

## Root Cause

Energy drop detection for regular words (not ending with punctuation):
- Still looks for **strongest** rise/drop pair
- Picks later, stronger energy event over earlier, softer onset
- "God" has soft consonant onset at 0.031s
- Algorithm picks louder vowel at 0.598s instead

**The insight from last words applies to first words too!**
- **First words**: Original START often correct (WhisperX detected speech beginning)
- **First words**: Original END may include pre-pause silence

---

## Solution Approach

### Option 1: Apply Start Validation to ALL Words

For **every word**:
1. Validate original start has speech energy (±50ms)
2. If YES: Keep original start
3. Use energy drop detection only for END

**Pros:**
- Respects WhisperX start timestamps (often accurate)
- Prevents "too late" start errors
- Consistent approach

**Cons:**
- May keep some bad starts (if WhisperX failed)
- More conservative

### Option 2: Detect First Words After Punctuation

Add `is_first_after_punct` parameter:
- Detect words that follow `.`, `!`, `?`, or start of transcript
- Apply same logic as last words: validate and keep original start

**Pros:**
- Targets specific problematic cases
- More surgical fix

**Cons:**
- Need to track previous word
- More complex logic

### Option 3: Hybrid - Validate Start for Soft Onsets

Detect soft onsets (consonants like "G", "J", numbers):
- Check if word starts with soft consonant
- If YES: Validate and keep original start
- If NO: Use energy drop detection normally

**Pros:**
- Handles actual problematic cases
- Preserves energy detection benefits for words with strong onsets

**Cons:**
- Requires consonant classification
- Language-specific

---

## Recommended Solution

**Option 1** - Validate start for ALL words:

### Rationale

1. **WhisperX start timestamps are generally accurate**
   - Whisper model detects speech onset well
   - Start errors are less common than end errors (which include silence)

2. **Energy drop detection has known issues with soft onsets**
   - Prefers loud peaks over early onsets
   - Struggles with consonants, whispers, numbers

3. **Consistency with sustained pause approach**
   - Last words: Keep start, correct end
   - All words: Keep start (if validated), correct end

4. **User's observation confirms this**
   - "The original timestamps was better" (for start)
   - "Find where energy drops and STAYS low" (for end)

---

## Implementation Plan

### Modify: `EnergyDropCorrector.correct_word_timing()`

**Current behavior:**
- `is_last_before_punct=True`: Validate start, find sustained silence for end
- `is_last_before_punct=False`: Use energy drop detection for both start and end

**New behavior:**
- **ALWAYS** validate original start first
- If start validated: Keep it, use energy drop detection for end only
- If start NOT validated: Use energy drop detection for both

### Code Changes

```python
def correct_word_timing(self, word: Word, sensitivity: str = 'high',
                       is_last_before_punct: bool = False) -> Word:
    """
    Apply energy-based timing correction

    Strategy:
    1. ALWAYS validate original start (±50ms window)
    2. If start has speech energy: KEEP IT
    3. For END:
       - If last before punct: Find sustained silence (100ms+ low energy)
       - Otherwise: Use energy drop detection
    4. If start has NO energy: Use full energy drop detection
    """

    # [Calculate RMS, smooth, get times and threshold - same as before]

    # STEP 1: ALWAYS validate original start
    start_idx = np.argmin(np.abs(rms_times - word.original_start))
    check_window = int(0.05 / (hop_length / sr))  # ±50ms
    start_range = slice(max(0, start_idx - check_window),
                      min(len(rms_smooth), start_idx + check_window))

    energy_at_start = np.max(rms_smooth[start_range])
    start_validated = energy_at_start > speech_threshold

    if start_validated:
        # Original start has speech - KEEP IT
        corrected_start = word.original_start

        # STEP 2: Determine how to correct END
        if is_last_before_punct:
            # Find sustained silence for last words
            MIN_SILENCE_DURATION = 0.100
            silence_frames = int(MIN_SILENCE_DURATION / (hop_length / sr))

            corrected_end = word.original_end  # fallback

            for i in range(start_idx, len(rms_smooth) - silence_frames):
                if np.all(rms_smooth[i:i+silence_frames] < speech_threshold):
                    corrected_end = rms_times[i]
                    break

            word.adjustment_reason = "Validated start + sustained pause end"
        else:
            # Use energy drop for end (find drop after validated start)
            derivative = np.gradient(rms_smooth)

            # Find drops AFTER start_idx
            drop_threshold = np.percentile(derivative, 20)
            drops, _ = signal.find_peaks(-derivative[start_idx:],
                                        height=-drop_threshold, distance=5)

            if len(drops) > 0:
                # Adjust indices (drops are relative to start_idx)
                best_end_idx = start_idx + drops[np.argmax(-derivative[start_idx + drops])]
                corrected_end = rms_times[best_end_idx]
            else:
                corrected_end = word.original_end  # fallback

            word.adjustment_reason = "Validated start + energy drop end"

        word.start = corrected_start
        word.end = corrected_end
        return word

    # STEP 3: If start NOT validated, use full energy drop detection
    # [Existing energy drop detection code - unchanged]
```

---

## Expected Results After Fix

### First Subtitle

**Before (current broken):**
```srt
1
00:00:00,598 --> 00:00:01,110
God ettermiddag,

2
00:00:01,336 --> 00:00:02,927
- brødre og søstre.
```

**After (with start validation):**
```srt
1
00:00:00,031 --> 00:00:03,034
God ettermiddag, brødre og søstre.
```

### Statistics Expected

- Sustained pause detection: ~2000-3000 words (last before punct)
- Start validated (kept original): ~16000-18000 words (most words)
- Full energy drop: ~0-2000 words (where start had no energy)

---

## Testing Plan

1. **Implement start validation for all words**
2. **Test on "God" word** - Should keep 0.031s start
3. **Test on "søstre." word** - Should keep 2.314s start, find 2.628s end
4. **Run full pipeline** - Check first subtitle is combined correctly
5. **Verify statistics** - Count start validations vs full energy drop

---

## Summary

**Root issue:** Energy drop detection prefers **strong** events over **early** events

**User insight:** "The original timestamps was better" (for starts)

**Solution:** Validate ALL word starts, keep if energy present

**Implementation:** ~30 lines of code modification

**Expected improvement:**
- ✅ First words: Correct start times (keep original)
- ✅ Last words: Correct end times (sustained silence)
- ✅ All words: Better overall accuracy
