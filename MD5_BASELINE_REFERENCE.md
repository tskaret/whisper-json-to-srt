# MD5 Baseline Reference

**Purpose:** Quick reference for verifying code changes don't alter output
**Last Updated:** 2025-10-17
**Status:** ✅ VERIFIED

---

## Baseline MD5 Hashes

### Test Configuration

```bash
python json_to_srt_energy.py \
  /mnt/d/stevner/2025/regionalt/Lørdag/04-LørdagEttermiddag/04-LørdagEttermiddag.mp3 \
  04-Lørdagettermiddag.json \
  --output-dir test_output \
  --pause-threshold 1.6 \
  --max-chars-per-line 37 \
  --no-break-on-speaker-change
```

### Expected MD5 Hashes (with CRLF line endings)

```
143ba9f9893662081fd1682d254917b3  04-Lørdagettermiddag_clean.srt
95db5a38a3eb6f0c2e2139d64f15acf3  04-Lørdagettermiddag_with_speakers.srt
```

---

## Quick Verification

### On Linux/WSL:

```bash
# Run test
python json_to_srt_energy.py [audio] [json] --output-dir test_md5 [options]

# Convert to CRLF (required!)
unix2dos test_md5/*.srt

# Check MD5
md5sum test_md5/*.srt

# Expected output:
# 143ba9f9893662081fd1682d254917b3  test_md5/04-Lørdagettermiddag_clean.srt
# 95db5a38a3eb6f0c2e2139d64f15acf3  test_md5/04-Lørdagettermiddag_with_speakers.srt
```

### On Windows:

```powershell
# Run test
python json_to_srt_energy.py [audio] [json] --output-dir test_md5 [options]

# Check MD5
certutil -hashfile test_md5\04-Lørdagettermiddag_clean.srt MD5
certutil -hashfile test_md5\04-Lørdagettermiddag_with_speakers.srt MD5

# Expected:
# 143ba9f9893662081fd1682d254917b3
# 95db5a38a3eb6f0c2e2139d64f15acf3
```

---

## File Details

### Input Files

| File | Path | Size |
|------|------|------|
| **Audio** | `/mnt/d/stevner/2025/regionalt/Lørdag/04-LørdagEttermiddag/04-LørdagEttermiddag.mp3` | 174,214,558 bytes |
| **JSON** | `04-Lørdagettermiddag.json` | 3,803,630 bytes |

### Output Files

| File | Size | Line Ending | MD5 |
|------|------|-------------|-----|
| **clean.srt** | 166,384 bytes | CRLF | `143ba9f9893662081fd1682d254917b3` |
| **with_speakers.srt** | 188,226 bytes | CRLF | `95db5a38a3eb6f0c2e2139d64f15acf3` |

---

## Processing Statistics

```
Total words processed: 18760
Words corrected by energy detection: 18664
  Average correction: 262.7ms
  Maximum correction: 24024.0ms

Subtitle segments created: 1624
Speaker changes detected: 84
Pause breaks detected: 613
Short segments merged: 49
Reading buffers applied: 1562
Segments capped by duration: 0
Orphan breaks prevented: 67
```

---

## Critical: Line Ending Requirement

**⚠️ IMPORTANT:** MD5 hashes are **line-ending sensitive**

- Baseline uses **CRLF** (Windows: `\r\n`)
- Linux/WSL generates **LF** (`\n`) by default
- **Must convert to CRLF** before comparing MD5

### Conversion Commands

```bash
# Linux/WSL: Convert LF → CRLF
unix2dos file.srt

# Windows: Convert CRLF → LF (if needed)
dos2unix file.srt
```

### Why This Matters

Same content, different line endings = **Different MD5**:

- LF endings: `0e852f2e7fc4f869d3118ef0687775ed`
- CRLF endings: `143ba9f9893662081fd1682d254917b3`

---

## Verification History

### 2025-10-17: Security Fixes Applied ✅

**Test:** Security-hardened code vs backup code
**Result:** ✅ MD5 MATCH (after removing POST_SPEECH_BUFFER)
**Files:** `md5_baseline_outputs/`

**Changes Made:**
1. Added input validation functions
2. Added security logging
3. Added atomic file writes
4. **Removed** POST_SPEECH_BUFFER (was causing MD5 mismatch)

**Verification:**
- Backup code: `143ba9f9...` / `95db5a38...` ✅
- Security code: `143ba9f9...` / `95db5a38...` ✅
- **Match confirmed**

---

## When MD5 Should Match

MD5 hashes **MUST match** after:

✅ Refactoring (extracting constants, renaming variables)
✅ Code comments and documentation
✅ Security validation (input checking only)
✅ Error handling improvements (no functional changes)
✅ Performance optimizations (same output)

---

## When MD5 Can Differ

MD5 hashes **MAY differ** after:

⚠️ Algorithm improvements
⚠️ Bug fixes that change timing
⚠️ New features
⚠️ Parameter changes
⚠️ Buffer/timing adjustments

**Action Required:** Document why MD5 changed and establish new baseline

---

## Troubleshooting

### Problem: MD5 Doesn't Match

**Step 1:** Check line endings
```bash
file output.srt
# Should show: "with CRLF line terminators"
```

**Step 2:** Convert if needed
```bash
unix2dos output.srt
md5sum output.srt
```

**Step 3:** Compare content
```bash
diff -u baseline.srt output.srt | head -50
```

**Step 4:** Identify what changed
- Timing differences?
- Text wrapping differences?
- Hyphenation differences?
- Segment splitting differences?

### Problem: NumPy Version Error

```
Error: Numba needs NumPy 1.24 or greater
```

**Solution:**
```bash
pip install --upgrade numpy>=1.24
# or
pip install -U numpy
```

---

## Reference Files

### Baseline Outputs (Verified)

**Location:** `md5_baseline_outputs/`

```
04-Lørdagettermiddag_clean.srt          (166,384 bytes, CRLF)
04-Lørdagettermiddag_with_speakers.srt  (188,226 bytes, CRLF)
```

**Generated By:** `json_to_srt_energy.py` (with security fixes, POST_SPEECH_BUFFER removed)
**Date:** 2025-10-17
**Verified:** ✅ Matches baseline MD5

### Backup Code

**File:** `json_to_srt_energy_backup.py`
**Date:** 2025-10-13 18:18
**Purpose:** Pre-security-fixes version
**Status:** ✅ Produces correct baseline MD5

---

## Testing Checklist

Before committing code changes:

- [ ] Run processing with test configuration (above)
- [ ] Convert output to CRLF: `unix2dos test_md5/*.srt`
- [ ] Calculate MD5: `md5sum test_md5/*.srt`
- [ ] Compare with baseline:
  - `143ba9f9893662081fd1682d254917b3` (clean) ✅
  - `95db5a38a3eb6f0c2e2139d64f15acf3` (with speakers) ✅
- [ ] If different: Document reason and get approval
- [ ] If matches: Safe to commit ✅

---

## Quick Reference Table

| Check | Expected Result |
|-------|----------------|
| **clean.srt MD5** | `143ba9f9893662081fd1682d254917b3` |
| **with_speakers.srt MD5** | `95db5a38a3eb6f0c2e2139d64f15acf3` |
| **Word count** | 18,760 |
| **Words corrected** | 18,664 |
| **Subtitles created** | 1,624 |
| **Line ending** | CRLF (Windows) |

---

## Notes

1. **Always test on same input files** - Different audio/JSON = different MD5
2. **Line endings matter** - Convert to CRLF before comparing
3. **Security fixes preserved MD5** - Input validation doesn't change output
4. **POST_SPEECH_BUFFER removed** - Was adding 265ms, breaking MD5
5. **Backup code verified** - Produces correct baseline

---

**Last Verified:** 2025-10-17
**Verified By:** MD5 testing after security fixes
**Status:** ✅ BASELINE CONFIRMED
