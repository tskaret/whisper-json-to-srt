# Quick Start: Waveform-Based Fine-Tuning

## 🚀 Rask Start (15-sekunders test)

### Steg 1: Installer avhengigheter

```bash
pip install numpy librosa matplotlib
```

### Steg 2: Kjør testscript

Dobbeltklikk på: **`test_waveform_tuning.bat`**

Eller kjør manuelt:

```bash
python waveform_fine_tuning.py ^
  "D:\Stevner\2025\Regionalt\Søndag\05-SøndagFormiddag.mp3" ^
  "D:\Stevner\2025\Regionalt\Søndag\05Transcribe.json" ^
  --start-time 300 ^
  --end-time 315 ^
  --visualize-start 300 ^
  --visualize-end 315 ^
  --output-dir "D:\Stevner\2025\Regionalt\Søndag\05-SøndagFormiddag"
```

### Steg 3: Sjekk resultatet

Åpne visualiseringen:
```
D:\Stevner\2025\Regionalt\Søndag\05-SøndagFormiddag\05Transcribe_visualization.png
```

**Forventet resultat (9-10/10 kvalitet):**
- ✅ 70-80% av ord justert
- ✅ Maksimal justering <80ms
- ✅ Ingen overlapp
- ✅ "Vi", "La", "tre:" perfekt tilpasset waveform

### Steg 4: Full prosessering (hvis test OK)

Dobbeltklikk på: **`run_full_waveform_tuning.bat`**

Eller kjør manuelt:

```bash
python waveform_fine_tuning.py ^
  "D:\Stevner\2025\Regionalt\Søndag\05-SøndagFormiddag.mp3" ^
  "D:\Stevner\2025\Regionalt\Søndag\05Transcribe.json" ^
  --output-dir "D:\Stevner\2025\Regionalt\Søndag\05-SøndagFormiddag"
```

⏱️ **Tidsforbruk:** ~15-30 minutter for 143 minutter audio

---

## 🎯 Hva gjør scriptet?

### 1. **Gradient-basert onset detection**
Finner faktisk start av ord basert på energi-stigning i waveform.

**Løser:**
- "Vi" og "La" som starter for tidlig

### 2. **Decay-basert offset detection**
Finner faktisk slutt av ord basert på energi-nedgang med hysterese.

**Løser:**
- "tre:" som slutter for tidlig
- Ord med vokal-lyder som kuttes for raskt

### 3. **Konservative justeringer**
Dynamiske maksgrenser basert på ordtype:
- Korte funksjonsord: max ±30ms
- Normale ord: max ±50ms
- Lange ord: max ±80ms

### 4. **Overlap prevention**
- Minimum 20ms gap mellom alle ord
- Intelligent konfliktløsning basert på confidence

### 5. **Leading/trailing buffers**
- 10ms buffer før og etter hvert ord (konfigurerbart)
- Forhindrer "tight timing"

---

## ⚙️ Parametere

### Grunnleggende

| Parameter | Standard | Beskrivelse |
|-----------|----------|-------------|
| `--start-time` | 0 | Start-tid (sekunder) |
| `--end-time` | None | Slutt-tid (sekunder) |
| `--output-dir` | Same as JSON | Output-mappe |

### Finjustering

| Parameter | Standard | Beskrivelse |
|-----------|----------|-------------|
| `--min-gap` | 0.020 | Minimum gap mellom ord (sekunder) |
| `--confidence-threshold` | 0.7 | Terskel for aggressiv justering |
| `--leading-buffer` | 0.010 | Buffer før hvert ord (sekunder) |
| `--trailing-buffer` | 0.010 | Buffer etter hvert ord (sekunder) |
| `--no-buffers` | - | Deaktiver buffers |

### Visualisering

| Parameter | Standard | Beskrivelse |
|-----------|----------|-------------|
| `--visualize-start` | 0 | Start-tid for visualisering |
| `--visualize-end` | 15 | Slutt-tid for visualisering |

---

## 📊 Output-filer

### 1. `*_adjusted.json`
Justert transkripsjon med metadata:

```json
{
  "segments": [
    {
      "speaker": "SPEAKER_05",
      "start": 0.031,
      "end": 5.238,
      "text": "God ettermiddag...",
      "words": [
        {
          "word": "God",
          "start": 0.031,
          "end": 0.291,
          "score": 0.277,
          "original_start": 0.031,
          "original_end": 0.291,
          "adjustment_magnitude": 0.0,
          "adjustment_reason": ""
        },
        ...
      ]
    }
  ]
}
```

### 2. `*_visualization.png`
3-panels visualisering:
- **Panel 1:** Original timing (WhisperX)
- **Panel 2:** Justert timing (fargekodet)
- **Panel 3:** Statistikk

**Fargekoding:**
- 🟢 Grønn: Uendret
- 🟡 Gul: Liten justering (<30ms)
- 🟠 Oransje: Moderat justering (30-60ms)
- 🔴 Rød: Stor justering (>60ms)

---

## 🔧 Feilsøking

### Problem: For mange justeringer (>80%)

**Løsning:**
```bash
--confidence-threshold 0.8  # Mer konservativ (justerer kun lav confidence)
```

### Problem: For få justeringer (<70%)

**Løsning:**
```bash
--confidence-threshold 0.6  # Mer aggressiv
```

### Problem: Justeringer er for store (>80ms)

Dette bør ikke skje (hardkodet max 80ms). Hvis det gjør:
1. Sjekk lydkvaliteten - bruk audio preprocessing først
2. Reduser `--confidence-threshold`

### Problem: Overlapp mellom ord

Dette bør ikke skje (hardkodet min 20ms gap). Hvis du ser overlapp:
1. Sjekk at du bruker riktig fil (`*_adjusted.json`)
2. Åpne visualiseringen for å verifisere

### Problem: "Tight timing" (ord for tett på hverandre)

**Løsning:**
```bash
--min-gap 0.030           # Øk minimum gap til 30ms
--leading-buffer 0.015    # Øk leading buffer til 15ms
--trailing-buffer 0.015   # Øk trailing buffer til 15ms
```

---

## 📈 Forventet Kvalitet

### Målsetting: 9-10/10

- ✅ **70-80% av ord justert** (ikke 93% som tidligere)
- ✅ **Max justering <80ms** for de fleste ord
- ✅ **Ingen overlapp**
- ✅ **Minimum 20ms gap** mellom ord
- ✅ **Perfekt timing** for problematiske ord (Vi, La, tre:)

### Tidligere versjon (6/10):
- ❌ 93% av ord justert (for aggressivt)
- ❌ Opptil 180ms justeringer
- ❌ "Vi" og "La" startet for tidlig
- ❌ "tre:" sluttet for tidlig

### Denne versjonen (9-10/10):
- ✅ 70-80% av ord justert
- ✅ Max 80ms justeringer
- ✅ "Vi" og "La" starter ved waveform-onset
- ✅ "tre:" strekker seg til waveform-offset
- ✅ Respekterer høy confidence (>0.9 = minimal justering)

---

## 🔗 Neste Steg

### Generer SRT-filer

```bash
python json_to_srt_fixed.py "D:\Stevner\2025\Regionalt\Søndag\05-SøndagFormiddag\05Transcribe_adjusted.json"
```

Dette genererer:
- `05Transcribe_adjusted_with_speakers.srt`
- `05Transcribe_adjusted_clean.srt`

### Se SRT-filer

```bash
python preview_subtitles.py "05Transcribe_adjusted_clean.srt"
```

---

## 📚 Mer Informasjon

Se `WAVEFORM_TUNING_README.md` for:
- Detaljert algoritme-forklaring
- Tekniske spesifikasjoner
- Avanserte brukseksempler
- Integrasjon med andre verktøy

---

## 🎓 Tips

1. **Test alltid på 15-sekunders segment først!**
   - Sjekk visualiseringen
   - Verifiser at justeringene gir mening
   - Juster parametere hvis nødvendig

2. **Bruk audio preprocessing for best resultat:**
   - Noise reduction (afftdn)
   - Normalization (loudnorm)
   - High-pass filter (200Hz)

3. **Respekter high-confidence timing:**
   - Standard threshold (0.7) er god for de fleste tilfeller
   - Hvis original alignment er veldig bra, bruk 0.8+

4. **Sjekk statistikk-output:**
   - Mål: 70-80% justert
   - Hvis utenfor range: juster `--confidence-threshold`

---

## ✅ Sjekkliste før full kjøring

- [ ] Installert numpy, librosa, matplotlib
- [ ] Test-kjøring på 15-sekunders segment utført
- [ ] Visualisering ser bra ut
- [ ] Statistikk innenfor målområde (70-80%)
- [ ] Max justering <80ms
- [ ] Ingen overlapp i visualisering
- [ ] Audio-fil er av god kvalitet

---

**Happy fine-tuning!** 🚀
