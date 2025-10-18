# Waveform-Based Fine-Tuning for Norwegian Speech

## Oversikt

`waveform_fine_tuning.py` er et avansert verktøy for å finjustere word-level timing basert på faktisk waveform-analyse av norsk tale. Scriptet bruker intelligent onset/offset-deteksjon for å oppnå 9-10/10 kvalitet.

## Nøkkelfunksjoner

### 1. **Gradient-Basert Onset Detection**
Finner faktisk start av ord ved å analysere hvor amplituden stiger bratt:
- Bruker energi-gradient (derivat) for å detektere raske stigninger
- Dynamiske terskler basert på confidence-score
- Løser problemet med "Vi" og "La" som starter for tidlig

### 2. **Decay-Basert Offset Detection**
Finner faktisk slutt av ord ved å analysere energi-nedgang med hysterese:
- Tillater etterklong for ord som slutter med vokal (a, e, i, o, u, y, æ, ø, å)
- Spesialhåndtering av ord som slutter med ":" (som "tre:")
- Strekker ord til waveformen faktisk slutter

### 3. **Konservative Justeringer**
Dynamiske maksgrenser basert på ordtype:
- **Korte funksjonsord** (og, i, er, å, etc.): max ±30ms
- **Normale ord**: max ±50ms
- **Lange/avsluttende ord**: max ±80ms

### 4. **Confidence-Basert Strategi**
- **Høy confidence (>0.9)**: Minimal justering - original timing er trolig god
- **Middels confidence (0.7-0.9)**: Normal justering
- **Lav confidence (<0.7)**: Mer aggressiv justering

### 5. **Overlap Prevention**
- Minimum 20ms gap mellom alle ord (konfigurerbart)
- Intelligent konfliktløsning: Justerer ordet med lavest confidence eller størst tidligere justering
- Garanterer ingen overlapp i output

### 6. **Fargekodet Visualisering**
- **Grønn**: Uendret (original timing var god)
- **Gul**: Liten justering (<30ms)
- **Oransje**: Moderat justering (30-60ms)
- **Rød**: Stor justering (>60ms)

## Installasjon

```bash
# Installer nødvendige avhengigheter
pip install numpy librosa matplotlib
```

## Bruk

### Grunnleggende Bruk (Test på 15-sekunders segment)

```bash
python waveform_fine_tuning.py \
  "D:\Stevner\2025\Regionalt\Søndag\05-SøndagFormiddag.mp3" \
  "D:\Stevner\2025\Regionalt\Søndag\05Transcribe.json" \
  --start-time 300 \
  --end-time 315 \
  --visualize-start 300 \
  --visualize-end 315
```

Dette behandler 15 sekunder fra 05:00 til 05:15 (300-315 sekunder).

### Full Prosessering (143 minutter)

```bash
python waveform_fine_tuning.py \
  "D:\Stevner\2025\Regionalt\Søndag\05-SøndagFormiddag.mp3" \
  "D:\Stevner\2025\Regionalt\Søndag\05Transcribe.json" \
  --output-dir "D:\Stevner\2025\Regionalt\Søndag\05-SøndagFormiddag" \
  --visualize-start 300 \
  --visualize-end 315
```

### Alle Parametere

| Parameter | Standard | Beskrivelse |
|-----------|----------|-------------|
| `audio_path` | - | Sti til lydfil (MP3/WAV) |
| `json_path` | - | Sti til WhisperX JSON-transkripsjon |
| `--output-dir` | Same as JSON | Output-mappe |
| `--start-time` | 0 | Start-tid for prosessering (sekunder) |
| `--end-time` | None | Slutt-tid for prosessering (sekunder) |
| `--min-gap` | 0.020 | Minimum gap mellom ord (sekunder) |
| `--confidence-threshold` | 0.7 | Terskel for aggressiv justering |
| `--visualize-start` | 0 | Start-tid for visualisering (sekunder) |
| `--visualize-end` | 15 | Slutt-tid for visualisering (sekunder) |

## Output

Scriptet genererer to filer:

1. **`*_adjusted.json`**: Justert transkripsjon med metadata
   - Original timing bevart for sammenligning
   - Justeringsmagnitude for hvert ord
   - Justeringsårsak (f.eks. "Waveform analysis (conf=0.65)")

2. **`*_visualization.png`**: 3-panels visualisering
   - Panel 1: Original timing (WhisperX)
   - Panel 2: Justert timing (fargekodet)
   - Panel 3: Statistikk

## Eksempel: 05-SøndagFormiddag

### Test på 15-sekunders segment (05:00-05:15)

```bash
# Kjør test
python waveform_fine_tuning.py \
  "D:\Stevner\2025\Regionalt\Søndag\05-SøndagFormiddag.mp3" \
  "D:\Stevner\2025\Regionalt\Søndag\05Transcribe.json" \
  --start-time 300 \
  --end-time 315 \
  --visualize-start 300 \
  --visualize-end 315 \
  --output-dir "D:\Stevner\2025\Regionalt\Søndag\05-SøndagFormiddag"
```

**Forventet resultat:**
- 70-80% av ord justert
- Maksimal justering: <80ms
- "Vi", "La", "tre:" perfekt tilpasset waveform
- Ingen overlapp

### Full prosessering (143 minutter)

```bash
# Kjør full prosessering
python waveform_fine_tuning.py \
  "D:\Stevner\2025\Regionalt\Søndag\05-SøndagFormiddag.mp3" \
  "D:\Stevner\2025\Regionalt\Søndag\05Transcribe.json" \
  --output-dir "D:\Stevner\2025\Regionalt\Søndag\05-SøndagFormiddag"
```

## Algoritmedetaljer

### Onset Detection (Start av ord)

```python
1. Ekstraher audio-segment med ±150ms buffer
2. Beregn RMS-energi med 5ms vinduer og 2ms hop
3. Beregn energi-gradient (derivat)
4. Finn noise floor (10. persentil)
5. Sett dynamisk terskel basert på confidence:
   - Lav conf (<0.7): noise * 2.0 eller max * 0.10
   - Normal conf: noise * 2.5 eller max * 0.15
6. Søk etter første signifikante energistigning
7. Begrens justering til max_adjustment (30/50/80ms)
```

### Offset Detection (Slutt av ord)

```python
1. Ekstraher audio-segment med ±150ms buffer
2. Beregn RMS-energi
3. Sjekk om ord slutter med vokal eller ":"
   - Hvis ja: Reduser terskel med 30% (tillat etterklong)
4. Søk bakover fra forventet slutt
5. Bruk hysterese: Trenger 3 påfølgende stille frames for å bekrefte slutt
6. Begrens justering til max_adjustment
```

### Overlap Resolution

```python
1. For hvert par av nabord:
   - Sjekk gap = next.start - current.end
   - Hvis gap < min_gap (20ms):
     a. Sammenlign confidence og eksisterende justeringer
     b. Juster ordet med lavest confidence eller størst justering
     c. Behold minimum 20ms gap
```

## Kvalitetsmål (9-10/10)

- ✅ **70-80% av ord justert** (ikke 93% som v1)
- ✅ **Maksimal justering <80ms** for de fleste ord
- ✅ **Ingen overlapp** mellom ord
- ✅ **Minimal gaps** (20ms standard)
- ✅ **Respekterer høy confidence** (>0.9 = minimal justering)

## Feilsøking

### Problem: For mange/få justeringer

**Løsning 1: Juster confidence-terskel**
```bash
# Mer aggressive justeringer
--confidence-threshold 0.8

# Mindre aggressive justeringer
--confidence-threshold 0.6
```

**Løsning 2: Manuell inspeksjon**
Sjekk `*_adjusted.json` for `adjustment_reason` og `score` for hvert ord.

### Problem: Justeringer er for store

Dette bør ikke skje (hardkodet max 80ms), men hvis det gjør:
1. Sjekk at lydkvaliteten er god (bruk audio preprocessing først)
2. Reduser `--confidence-threshold` for å aktivere færre justeringer

### Problem: Ord overlapper fortsatt

Ikke mulig med scriptet - minimum 20ms gap er hardkodet. Hvis du ser overlapp:
1. Sjekk at du bruker riktig output-fil (`*_adjusted.json`)
2. Verifiser med visualiseringen

## Tekniske Spesifikasjoner

- **Sample rate**: 16 kHz (optimal for tale)
- **Window size**: 5ms (høy tidsoppløsning)
- **Hop size**: 2ms (finkornet analyse)
- **Buffer**: ±150ms rundt hvert ord
- **Minimum gap**: 20ms (konfigurerbart)

## Integrasjon med json_to_srt_fixed.py

Etter finjustering, bruk `json_to_srt_fixed.py` for å generere SRT:

```bash
# Generer SRT fra justert transkripsjon
python json_to_srt_fixed.py \
  "D:\Stevner\2025\Regionalt\Søndag\05-SøndagFormiddag\05Transcribe_adjusted.json"
```

Dette gir deg høykvalitets undertekster med perfekt timing!

## Ytelse

- **15-sekunders segment**: ~5-10 sekunder
- **143 minutters audio**: ~15-30 minutter (avhengig av CPU)

Tips: Test på 15-sekunders segment først for å verifisere parametere før full kjøring.

## Lisens

MIT License - samme som resten av subtitle-processing-experiments prosjektet.

## Bidragsytere

Utviklet for norsk tale (predikant-tale) med fokus på høy nøyaktighet og konservative justeringer.
