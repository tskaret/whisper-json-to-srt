# Analysis: `ffmpeg -af "dynaudnorm,loudnorm=I=-16:TP=-1.5:LRA=11"`

## Overview

This combines TWO normalization filters in sequence for comprehensive audio leveling.

---

## FILTER 1: `dynaudnorm` (Dynamic Audio Normalizer)

### What it does:
- Dynamically adjusts volume over time
- Brings up quiet sections, reduces loud sections
- Works on SHORT time windows (adaptive)
- Makes volume more consistent throughout

### Benefits for ASR:
- ✅ Prevents quiet speech from being missed
- ✅ Prevents loud sections from distorting
- ✅ Good for recordings with varying speaker distance
- ✅ Handles multiple speakers at different volumes

### Potential issues:
- ⚠️ Can amplify background noise during quiet parts
- ⚠️ May reduce dynamic range too much if aggressive

---

## FILTER 2: `loudnorm=I=-16:TP=-1.5:LRA=11` (EBU R128 Loudness Normalization)

### Parameters explained:

| Parameter | Value | Meaning |
|-----------|-------|---------|
| `I=-16` | -16 LUFS | **Integrated loudness target**<br>Industry standard for broadcast/streaming<br>Comfortable listening level |
| `TP=-1.5` | -1.5 dBFS | **True Peak limit**<br>Prevents clipping/distortion<br>Leaves 1.5dB headroom for safety |
| `LRA=11` | 11 LU | **Loudness Range target**<br>Preserves some dynamic variation<br>Not too flat, not too dynamic |

### Benefits for ASR:
- ✅ Standardized loudness level across entire file
- ✅ No clipping/distortion
- ✅ Consistent output meeting broadcast standards
- ✅ Preserves reasonable dynamic range (LRA=11)

---

## COMBINED EFFECT: `dynaudnorm → loudnorm`

### Processing order:
1. **dynaudnorm** adjusts volume dynamically (adaptive, time-based)
2. **loudnorm** then normalizes to broadcast standard (overall file)

### Overall result:
- ✅ Very consistent volume throughout entire recording
- ✅ Quiet speakers boosted, loud speakers controlled
- ✅ No clipping or distortion
- ✅ Industry-standard loudness level (-16 LUFS)
- ✅ Maintains some dynamic range (not completely flat)

---

## FOR ASR (WhisperX/NB-Whisper): RATING

### ⭐⭐⭐⭐ (4/5) - VERY GOOD

### Pros:
- ✅ Excellent for multi-speaker recordings
- ✅ Handles varying microphone distance well
- ✅ Prevents quiet speech from being missed
- ✅ Prevents distortion from loud speakers
- ✅ Standard broadcast-quality output
- ✅ Works well with Norwegian meeting recordings

### Cons:
- ⚠️ Double normalization might be overkill for some recordings
- ⚠️ `dynaudnorm` can amplify background noise during pauses
- ⚠️ Slight risk of over-compression if source is already normalized

---

## RECOMMENDATIONS

### CURRENT (your command):
```bash
ffmpeg -i input.mp3 -af "dynaudnorm,loudnorm=I=-16:TP=-1.5:LRA=11" output.mp3
```
**Rating:** Very good! ⭐⭐⭐⭐

---

### BETTER (add noise reduction):
```bash
ffmpeg -i input.mp3 \
  -af "afftdn=nf=-25,dynaudnorm,loudnorm=I=-16:TP=-1.5:LRA=11" \
  output.mp3
```
**Why better:** Reduces background noise BEFORE normalization, so you don't amplify the noise

---

### BEST (comprehensive preprocessing):
```bash
ffmpeg -i input.mp3 \
  -af "highpass=f=200,afftdn=nf=-25,dynaudnorm,loudnorm=I=-16:TP=-1.5:LRA=11" \
  output.mp3
```

**Filter order explanation:**
1. `highpass=f=200` - Remove low-frequency rumble first
2. `afftdn=nf=-25` - Remove noise on clean frequency range
3. `dynaudnorm` - Dynamically balance levels
4. `loudnorm` - Final standardization to broadcast spec

---

## ALTERNATIVE: Simpler Approaches

If double normalization seems excessive:

### Option A (simpler, faster):
```bash
ffmpeg -i input.mp3 -af "loudnorm=I=-16:TP=-1.5:LRA=11" output.mp3
```
- Just the broadcast-standard normalization
- Good for already well-recorded audio

### Option B (better for varying speakers):
```bash
ffmpeg -i input.mp3 -af "dynaudnorm" output.mp3
```
- Just the dynamic normalization
- Good for live recordings with multiple speakers

---

## CONCLUSION

**Your current filter chain is EXCELLENT for ASR!**

The combination of `dynaudnorm` + `loudnorm` is particularly well-suited for:
- ✅ Religious meetings/conferences (multiple speakers)
- ✅ Varying microphone distances
- ✅ Mix of quiet and loud speakers
- ✅ Long recordings requiring consistent levels

**Bottom line:** This will definitely improve ASR recognition compared to raw audio, especially for quiet speakers and sections with varying volume. The parameters you chose are industry-standard and well-balanced.

**Recommended next step:** Add noise reduction before the normalization chain for even better results.
