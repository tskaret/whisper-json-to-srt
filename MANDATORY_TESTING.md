# Mandatory Testing Procedures

## For New Projects

**⚠️ IMPORTANT:** When starting a new project that processes or transforms data:

1. **Create `MANDATORY_TESTING.md` during project initialization**
   - Define what needs to be tested (e.g., data preservation, output correctness)
   - Set minimum quality thresholds (e.g., ≥99% data preservation)
   - Document test commands and pass/fail criteria

2. **Run tests after EVERY code change**
   - Before committing to version control
   - After merging branches
   - Before deploying to production

3. **Use the provided template**
   - Copy `MANDATORY_TESTING_TEMPLATE.md` to your project
   - Customize for your specific testing needs
   - Fill in your test commands, thresholds, and criteria
   - Add to version control alongside your code

**Why this matters:** A critical bug in this project caused 38.1% data loss because no mandatory testing was in place. Mandatory testing catches catastrophic bugs before they reach users.

---

## Overview (This Project)

**ALL code changes** to subtitle generation scripts MUST pass these tests before being committed or deployed.

Affected files:
- `json_to_srt.py`
- `json_to_srt_fixed.py`
- `json_to_srt_energy.py`
- Any functions related to text wrapping, segment splitting, or word filtering

## Test 1: Word Preservation Test (CRITICAL)

**Purpose:** Verify that no words are silently lost during SRT generation

**Reason:** A critical bug (2025-10-13) caused 38.1% word loss due to silent truncation

**Minimum threshold:** 99.0% word preservation

### Running the Test

```bash
# Basic test
python test_word_preservation.py <input_json> <output_srt>

# With custom threshold
python test_word_preservation.py <input_json> <output_srt> 99.5
```

### Example

```bash
cd subtitle-processing-experiments

# Test json_to_srt_energy.py output
python test_word_preservation.py \
    test_data/transcript.json \
    test_output/transcript_clean.srt

# Expected output:
# ============================================================
# WORD PRESERVATION TEST - ✅ PASS
# ============================================================
# JSON words:           18,760
# SRT words:            18,627
# Words lost:           133
# ============================================================
# Preservation rate:    99.29%
# Loss rate:            0.71%
# Minimum required:     99.0%
# ============================================================
# ✅ TEST PASSED
# Word preservation is acceptable (>=99.0%)
# ============================================================
```

### Pass/Fail Criteria

| Result | Preservation Rate | Action |
|--------|------------------|--------|
| ✅ PASS | ≥ 99.0% | Continue to next test |
| ❌ FAIL | < 99.0% | **DO NOT COMMIT** - Fix word loss bug |
| ⚠️ WARNING | 98.0-99.0% | Review carefully, document reason |
| 🔴 CRITICAL | < 95.0% | **STOP** - Major bug, revert changes |

### Acceptable Word Loss

Small word loss (0-1%) may be acceptable if caused by:
- Very short words (< 50ms MIN_WORD_DURATION)
- Invalid timing (end ≤ start)
- Extremely long words (> 10s anomalous timing)

Use `analyze_missing_words_detailed.py` to investigate any missing words.

---

## Test 2: Timing Accuracy Verification

**Purpose:** Verify timestamps are updated correctly (especially for energy correction)

### Running the Test

```bash
# Compare energy-corrected vs non-corrected output
python -c "
def get_subtitle_start(srt_path, search_text):
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    blocks = content.split('\n\n')
    for block in blocks:
        if search_text.lower() in block.lower():
            lines = block.split('\n')
            if len(lines) >= 2 and '-->' in lines[1]:
                return lines[1].split(' --> ')[0]
    return None

# Test on known phrase
no_energy_start = get_subtitle_start('output_no_energy.srt', 'inne i bildet')
with_energy_start = get_subtitle_start('output_energy.srt', 'inne i bildet')

print(f'No energy:   {no_energy_start}')
print(f'With energy: {with_energy_start}')
print(f'Same: {no_energy_start == with_energy_start}')
"
```

### Pass/Fail Criteria

| Script | Expected Behavior |
|--------|------------------|
| `json_to_srt_energy.py` | Timestamps MUST differ from original (energy correction applied) |
| `json_to_srt.py` | May differ slightly (syllable-based correction) |
| `json_to_srt_fixed.py` | May differ slightly (syllable-based correction) |

**FAIL if:** Energy correction script produces identical timestamps to non-correction script (indicates correction not applied).

---

## Test 3: No Silent Truncation

**Purpose:** Verify `split_oversized_segment()` detects when `wrap_text()` truncates words

### Running the Test

```bash
python test_wrap_text.py
```

### Expected Behavior

When segment text exceeds character limits:
- ✅ Segment is split into multiple subtitles
- ✅ All words preserved across split subtitles
- ❌ Words are NOT silently truncated

### Test Case

```python
# Segment with 34 words, max_chars_per_line=37
text = "Han sa ikke noe om at Gud og Jesus var inne i bildet. Begrepet synd var ganske fjernt for meg. Jeg tenkte noen ganger gjør man feil, og så går man bare videre i"

# Expected: Multiple subtitles created
# Actual before fix: Only first 10 words shown (24 words LOST!)
# Actual after fix: All 34 words preserved across subtitles
```

---

## Test 4: Subtitle Statistics Verification

**Purpose:** Verify subtitle creation produces reasonable results

### Running the Test

After generating SRT, check statistics:

```bash
python -c "
import re

with open('output.srt', 'r', encoding='utf-8') as f:
    content = f.read()

blocks = [b for b in content.split('\n\n') if b.strip()]
print(f'Total subtitles: {len(blocks)}')

# Check for anomalies
capped = []
for block in blocks:
    lines = block.split('\n')
    if len(lines) >= 2 and '-->' in lines[1]:
        times = lines[1].split(' --> ')
        def parse_time(t):
            p = t.replace(',', ':').split(':')
            return int(p[0])*3600 + int(p[1])*60 + int(p[2]) + float(p[3])/1000

        duration = parse_time(times[1]) - parse_time(times[0])
        if duration >= 9.9:
            capped.append((lines[0], duration))

print(f'Capped subtitles (>= 9.9s): {len(capped)}')
if capped:
    print('Examples:')
    for num, dur in capped[:5]:
        print(f'  #{num}: {dur:.2f}s')
"
```

### Expected Ranges

| Metric | Acceptable Range | Concern If |
|--------|-----------------|------------|
| **Total subtitles** | Varies by content | < 100 for 2+ hour audio |
| **Avg duration** | 2-5 seconds | > 7s (too long) |
| **Capped subtitles** | < 5% of total | > 10% (many oversized) |
| **Max duration** | ≤ 15s (default cap) | > 15s (cap not working) |

---

## Test 5: Character Limit Stress Test

**Purpose:** Verify handling of tight character limits

### Running the Test

```bash
# Test with very tight character limit
python json_to_srt_energy.py \
    audio.mp3 transcript.json \
    --output-dir test_tight \
    --max-chars-per-line 30 \
    --pause-threshold 1.2

# Run word preservation test
python test_word_preservation.py \
    transcript.json \
    test_tight/transcript_clean.srt
```

### Pass Criteria

- Word preservation ≥ 99%
- No truncation errors
- Segments properly split (more subtitles created)

---

## Test 6: Missing Words Investigation

**Purpose:** Analyze and explain any missing words

### Running the Test

```bash
python analyze_missing_words_detailed.py \
    transcript.json \
    output.srt
```

### Expected Output

```
======================================================================
MISSING WORDS ANALYSIS
======================================================================

1. VERY SHORT DURATION (< 0.05s = 50ms)
   Count: 0 (0.0% of missing)

2. INVALID TIMING (duration <= 0)
   Count: 0 (0.0% of missing)

3. SINGLE CHARACTER (normalized, valid duration)
   Count: 0 (0.0% of missing)

4. EXTREMELY LONG DURATION (> 5s)
   Count: 0 (0.0% of missing)

5. REASONABLE WORDS (valid duration, multi-char)
   Count: 9 (100.0% of missing)

======================================================================
SUMMARY BY CATEGORY
======================================================================
Very short (< 50ms):        0 (  0.0%)
Invalid timing:             0 (  0.0%)
Single character:           0 (  0.0%)
Extremely long (> 5s):      0 (  0.0%)
Reasonable (unexpected):    9 (100.0%)
======================================================================
TOTAL MISSING:              9
======================================================================

*** WARNING: 9 words unexpectedly missing - investigate! ***
```

### Action Required

- If "Reasonable (unexpected)" > 0: **Investigate each word**
- Use `trace_missing_9_words.py` to see if words survived energy correction
- Document findings in `MISSING_WORDS_ANALYSIS_YYYYMMDD.md`

---

## Complete Test Workflow

### Before Committing Code Changes

```bash
#!/bin/bash
# Run this script before committing changes

set -e  # Exit on first error

echo "Running mandatory tests..."
echo

# Test 1: Word Preservation (CRITICAL)
echo "Test 1: Word Preservation"
python test_word_preservation.py test_data/transcript.json test_output/transcript_clean.srt
if [ $? -ne 0 ]; then
    echo "❌ FAILED: Word preservation test"
    exit 1
fi

# Test 2: No truncation
echo "Test 2: Wrap Text Behavior"
python test_wrap_text.py
if [ $? -ne 0 ]; then
    echo "❌ FAILED: Truncation test"
    exit 1
fi

# Test 3: Statistics check
echo "Test 3: Statistics Verification"
python -c "
# Statistics check code here
"

echo
echo "✅ All mandatory tests PASSED"
echo "Safe to commit"
```

---

## Bug Report Template

If any test fails, create a bug report:

### Template: `BUG_REPORT_YYYYMMDD.md`

```markdown
# Bug Report: [Brief Description]

**Date:** YYYY-MM-DD
**Severity:** [CRITICAL / HIGH / MEDIUM / LOW]
**Status:** [OPEN / FIXED / WONTFIX]

## Problem

[Describe what went wrong]

## Test Results

**Word Preservation:**
- JSON words: X
- SRT words: Y
- Words lost: Z
- Preservation: XX.X%
- Status: ❌ FAIL

**Missing Words:**
[List specific words]

## Root Cause

[Technical explanation]

## Fix Applied

[Describe the fix]

## Verification

[Retest results showing fix works]
```

---

## Historical Reference

### Bug: Silent Word Truncation (2025-10-13)

**Issue:** `wrap_text()` silently truncated words, `split_oversized_segment()` didn't detect it

**Impact:** 38.1% word loss (7,142 words from 18,760)

**Fix:** Added truncation detection in `split_oversized_segment()`:
```python
wrapped_word_count = len(' '.join(lines).split())
is_truncating = wrapped_word_count < len(test_segment)
if (would_exceed or is_truncating) and current_segment:
    segments.append(current_segment[:])
```

**Result:** Word preservation improved from 61.9% to 99.3%

---

## Summary Checklist

Before committing changes to subtitle generation code:

- [ ] Run `test_word_preservation.py` - ✅ PASS (≥ 99%)
- [ ] Run `test_wrap_text.py` - ✅ No truncation
- [ ] Check subtitle statistics - ✅ Reasonable ranges
- [ ] Test with tight character limits (30-35 chars) - ✅ PASS
- [ ] Investigate any unexpected missing words - ✅ Documented
- [ ] Compare timestamps (for energy correction) - ✅ Different from original
- [ ] Update `claude.md` with any new findings
- [ ] Document breaking changes in `CHANGELOG.md`

**Minimum test time:** 5-10 minutes for full test suite

**Test data:** Use `04-LørdagEttermiddag.json` (18,760 words, 143 minutes) as reference

---

**Remember:** A single undiscovered bug can cause thousands of words to disappear silently. These tests are mandatory for a reason!
