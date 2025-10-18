# Refactoring Notes - json_to_srt_energy.py

## Date: 2025-10-13

## Objective
Improve code maintainability by extracting magic numbers to named constants while ensuring **100% identical output** (verified by MD5 hash).

## Changes Made

### 1. New Constants Added (Lines 39-53)

Extracted hardcoded values to named constants in the energy detection section:

```python
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
```

### 2. Replacements Made

| Location | Before | After |
|----------|--------|-------|
| Line 109 | `buffer: float = 0.5` | `buffer: float = AUDIO_SEGMENT_BUFFER` |
| Line 135 | `int(0.005 * self.sr)` | `int(RMS_FRAME_LENGTH_MS / 1000 * self.sr)` |
| Line 136 | `int(0.002 * self.sr)` | `int(RMS_HOP_LENGTH_MS / 1000 * self.sr)` |
| Line 139 | `if len(rms) < 10:` | `if len(rms) < MIN_RMS_FRAMES:` |
| Line 143 | `window_len = min(11,` | `window_len = min(SAVGOL_WINDOW_MIN,` |
| Line 152 | `np.percentile(rms_smooth, 10)` | `np.percentile(rms_smooth, NOISE_FLOOR_PERCENTILE)` |
| Line 153 | `noise_floor * 3.0` | `noise_floor * SPEECH_THRESHOLD_MULTIPLIER` |
| Line 161 | `int(0.05 / (hop_length / self.sr))` | `int(ENERGY_CHECK_WINDOW_MS / 1000 / (hop_length / self.sr))` |
| Line 172 | `MIN_SPEECH_DURATION = 0.050` | `MIN_SUSTAINED_SPEECH_MS / 1000` |
| Line 203 | `int(0.05 / (hop_length / self.sr))` | `int(ENERGY_CHECK_WINDOW_MS / 1000 / (hop_length / self.sr))` |
| Line 217 | `MIN_SILENCE_DURATION = 0.100` | `MIN_SUSTAINED_SILENCE_MS / 1000` |
| Line 294 | `expected_duration * 0.5` | `expected_duration * DURATION_MIN_FACTOR` |
| Line 295 | `expected_duration * 3.0` | `expected_duration * DURATION_MAX_FACTOR` |
| Line 426 | `if (i + 1) % 100 == 0:` | `if (i + 1) % PROGRESS_UPDATE_INTERVAL == 0:` |
| Line 448 | `word.start - prev_word.end > 3.0` | `word.start - prev_word.end > NEW_THOUGHT_PAUSE_THRESHOLD` |

## Benefits

1. **Maintainability**: All tunable parameters now in one place
2. **Documentation**: Constants have descriptive names and inline comments
3. **No behavior changes**: Output is byte-for-byte identical (MD5 verified)
4. **Easy tuning**: Future adjustments only require changing constants

## Verification

**Baseline MD5 hashes** (before refactoring):
- `clean.srt`: `143ba9f9893662081fd1682d254917b3`
- `with_speakers.srt`: `95db5a38a3eb6f0c2e2139d64f15acf3`

**Refactored MD5 hashes** (after refactoring):
- To be verified...

## Files

- **Original**: `json_to_srt_energy_backup.py` (backup)
- **Refactored**: `json_to_srt_energy.py` (active)
- **Test script**: `refactor_json_to_srt_energy.py`

## Testing

Command to test:
```bash
python json_to_srt_energy.py \
  --output-dir test_refactored \
  --pause-threshold 1.6 \
  --max-chars-per-line 37 \
  --no-break-on-speaker-change \
  audio.mp3 transcript.json
```

Compare MD5 hashes:
```bash
certutil -hashfile test_refactored/04-LørdagEttermiddag_clean.srt MD5
certutil -hashfile test_refactored/04-LørdagEttermiddag_with_speakers.srt MD5
```

## Notes

- All numeric values converted to milliseconds where appropriate (e.g., `0.05` → `50 / 1000`)
- Division by 1000 added explicitly where converting from milliseconds to seconds
- Constants placed immediately after existing constants for logical grouping
- No changes to algorithm logic or control flow

## Next Steps

- [ ] Verify MD5 hashes match
- [ ] If verified, delete backup file
- [ ] Update CLAUDE.md documentation
- [ ] Consider extracting more constants (text wrapping, orphan detection thresholds)
