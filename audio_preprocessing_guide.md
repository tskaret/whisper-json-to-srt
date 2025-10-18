# Audio Preprocessing Guide for Better ASR Recognition

These preprocessing techniques IMPROVE speech recognition without distorting the natural speech tempo.

---

## ✅ RECOMMENDED PREPROCESSING TECHNIQUES

### 1. **Noise Reduction** (removes background noise)

**Tool:** FFmpeg with afftdn filter

```bash
ffmpeg -i input.mp3 -af "afftdn=nf=-25" output_clean.mp3
```

**Benefits:**
- Removes hiss, hum, ambient noise
- Makes speech clearer without changing tempo
- Especially helpful for low-quality recordings

---

### 2. **Audio Normalization** (balances volume levels)

**Tool:** FFmpeg with loudnorm filter

```bash
ffmpeg -i input.mp3 -af loudnorm output_normalized.mp3
```

**Benefits:**
- Brings quiet parts up, loud parts down
- Prevents whispers from being missed
- Prevents loud sections from clipping
- Consistent volume throughout

---

### 3. **High-Pass Filter** (removes low-frequency rumble)

**Tool:** FFmpeg with highpass filter

```bash
ffmpeg -i input.mp3 -af "highpass=f=200" output_filtered.mp3
```

**Benefits:**
- Removes rumble, wind noise, AC hum
- Clears up speech frequencies (200Hz and above)
- Human speech is primarily 200Hz-8000Hz

---

### 4. **Voice Isolation** (separate speech from music)

**Tool:** Demucs or Spleeter

```bash
# Using Demucs
demucs --two-stems=vocals input.mp3

# Using Spleeter
spleeter separate -p spleeter:2stems input.mp3 -o output/
```

**Benefits:**
- Separates vocals from instrumental music
- Useful for sections with background music
- Transcribe the vocals-only track
- Solves the "grønne dalen" music problem!

---

### 5. **Combined Preprocessing Pipeline** (recommended)

```bash
# All-in-one preprocessing
ffmpeg -i input.mp3 \
  -af "highpass=f=200,afftdn=nf=-25,loudnorm" \
  output_preprocessed.mp3
```

Then run WhisperX:
```bash
whisperx output_preprocessed.mp3 --model large-v3 --language no --output_dir ./output
```

---

## ❌ AVOID THESE (they degrade ASR quality)

### 1. **Time Stretching** (slowing down audio)
```bash
# DON'T DO THIS!
ffmpeg -i input.mp3 -filter:a "atempo=0.8" slowed.mp3
```
**Why avoid:** Introduces artifacts, changes acoustic patterns ASR expects

### 2. **Pitch Shifting**
```bash
# DON'T DO THIS!
ffmpeg -i input.mp3 -af "asetrate=44100*0.8,aresample=44100" pitched.mp3
```
**Why avoid:** Makes voices unnatural, confuses acoustic model

### 3. **Heavy Compression/Limiting**
**Why avoid:** Can introduce artifacts that confuse ASR

---

## PRACTICAL EXAMPLE WORKFLOW

### For your Norwegian meeting audio:

```bash
# Step 1: Separate vocals from music (solves "grønne dalen" problem)
demucs --two-stems=vocals meeting.mp3

# Step 2: Clean up the vocals track
ffmpeg -i "meeting/vocals.mp3" \
  -af "highpass=f=200,afftdn=nf=-25,loudnorm" \
  meeting_clean.mp3

# Step 3: Run Norwegian ASR (NB-Whisper or WhisperX)
whisperx meeting_clean.mp3 --model large-v3 --language no --output_dir ./output

# Step 4: Process JSON to SRT
python json_to_srt_fixed.py output/meeting_clean.json
```

---

## TOOLS INSTALLATION

### FFmpeg (for audio filtering)
```bash
# Windows (via Chocolatey)
choco install ffmpeg

# Or download from: https://ffmpeg.org/download.html
```

### Demucs (for vocal separation)
```bash
pip install demucs
```

### Spleeter (alternative to Demucs)
```bash
pip install spleeter
```

---

## WHEN TO USE EACH TECHNIQUE

| Problem | Solution |
|---------|----------|
| Background noise/hiss | Noise reduction (`afftdn`) |
| Inconsistent volume | Normalization (`loudnorm`) |
| Rumble/low-frequency noise | High-pass filter |
| Music mixed with speech | Voice isolation (Demucs/Spleeter) |
| Fast/unclear speech | Use larger model, accept limitation |
| Low confidence scores | Manual review after transcription |

---

## Notes

- **Voice isolation (Demucs)** would likely solve your "grønne dalen" music transcription problem
- These techniques clean the audio WITHOUT changing speech tempo
- Always keep original audio as backup
- Preprocessing takes time but significantly improves ASR accuracy
- For best results: preprocess → use large model → use NB-Whisper for Norwegian
