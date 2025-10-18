"""
Verification Report Generator

Creates comprehensive verification materials for manual review of timing adjustments:
1. Sentence-level grouping
2. 3-panel visualizations (original/waveform/adjusted)
3. Video generation with synchronized playback bar
4. PowerPoint presentation with embedded videos
5. HTML interactive viewer with audio playback
6. JSON retiming database

Usage:
    python generate_verification_report.py audio.mp3 adjusted_transcript.json --output-dir verification/
"""

import json
import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
import librosa
import librosa.display
from datetime import datetime


@dataclass
class Word:
    """Word with timing information"""
    text: str
    start: float
    end: float
    score: float
    speaker: str
    original_start: float = None
    original_end: float = None
    adjustment_magnitude: float = 0.0
    adjustment_reason: str = ""

    @property
    def duration(self):
        return self.end - self.start

    @property
    def original_duration(self):
        if self.original_start and self.original_end:
            return self.original_end - self.original_start
        return self.duration

    def count_syllables(self) -> int:
        """Count syllables based on Norwegian vowel groups"""
        vowels = 'aeiouyæøå'
        text_lower = self.text.lower().strip('.,!?;:-')
        count = 0
        prev_was_vowel = False
        for char in text_lower:
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                count += 1
            prev_was_vowel = is_vowel
        return max(1, count)

    def is_sentence_end(self) -> bool:
        """Check if word ends a sentence"""
        return self.text.rstrip().endswith(('.', '!', '?'))

    def is_anomalous(self, threshold: float = 2.0) -> bool:
        """Check if original duration is anomalous"""
        if not self.original_start or not self.original_end:
            return False
        expected = self.count_syllables() * 0.15
        return self.original_duration > (expected * threshold)


@dataclass
class Sentence:
    """Group of words forming a sentence"""
    id: int
    words: List[Word]
    speaker: str

    @property
    def text(self) -> str:
        """Full sentence text"""
        return ' '.join(w.text for w in self.words)

    @property
    def start(self) -> float:
        """Sentence start time (adjusted)"""
        return self.words[0].start if self.words else 0.0

    @property
    def end(self) -> float:
        """Sentence end time (adjusted)"""
        return self.words[-1].end if self.words else 0.0

    @property
    def original_start(self) -> float:
        """Original sentence start time"""
        if self.words and self.words[0].original_start:
            return self.words[0].original_start
        return self.start

    @property
    def original_end(self) -> float:
        """Original sentence end time"""
        if self.words and self.words[-1].original_end:
            return self.words[-1].original_end
        return self.end

    @property
    def duration(self) -> float:
        """Adjusted duration"""
        return self.end - self.start

    @property
    def original_duration(self) -> float:
        """Original duration"""
        return self.original_end - self.original_start

    @property
    def total_adjustment(self) -> float:
        """Total adjustment magnitude"""
        return sum(w.adjustment_magnitude for w in self.words)

    @property
    def max_adjustment(self) -> float:
        """Maximum single word adjustment"""
        return max((w.adjustment_magnitude for w in self.words), default=0.0)

    @property
    def has_anomalies(self) -> bool:
        """Check if sentence contains anomalous words"""
        return any(w.is_anomalous() for w in self.words)

    @property
    def needs_review(self) -> bool:
        """Flag if sentence needs manual review"""
        # Flag if any single adjustment >200ms or total >500ms or has anomalies
        return (self.max_adjustment > 0.200 or
                self.total_adjustment > 0.500 or
                self.has_anomalies)

    @property
    def priority(self) -> str:
        """Priority level for review"""
        if any(w.adjustment_magnitude > 0.150 for w in self.words):
            return "critical"
        elif self.has_anomalies:
            return "high"
        elif self.max_adjustment > 0.100:
            return "medium"
        else:
            return "low"


class SentenceGrouper:
    """Groups words into sentences"""

    def __init__(self, pause_threshold: float = 3.0):
        """
        Args:
            pause_threshold: Minimum pause to split sentences (seconds)
        """
        self.pause_threshold = pause_threshold

    def group_sentences(self, words: List[Word]) -> List[Sentence]:
        """Group words into sentences"""
        if not words:
            return []

        sentences = []
        current_words = []
        current_speaker = words[0].speaker
        sentence_id = 0

        for i, word in enumerate(words):
            # Add word to current sentence
            current_words.append(word)

            # Check if we should end the sentence
            should_end = False

            # End on hard punctuation
            if word.is_sentence_end():
                should_end = True

            # End on large pause
            if i < len(words) - 1:
                gap = words[i + 1].start - word.end
                if gap > self.pause_threshold:
                    should_end = True

            # End on speaker change
            if i < len(words) - 1:
                if words[i + 1].speaker != current_speaker:
                    should_end = True

            # Last word
            if i == len(words) - 1:
                should_end = True

            # Create sentence
            if should_end and current_words:
                sentence = Sentence(
                    id=sentence_id,
                    words=current_words.copy(),
                    speaker=current_speaker
                )
                sentences.append(sentence)

                current_words = []
                sentence_id += 1
                if i < len(words) - 1:
                    current_speaker = words[i + 1].speaker

        return sentences


class WaveformVisualizer:
    """Creates waveform visualizations"""

    def __init__(self, audio_path: str, sr: int = 16000):
        """Load audio for visualization"""
        print(f"Loading audio: {audio_path}")
        self.audio, self.sr = librosa.load(audio_path, sr=sr, mono=True)
        self.duration = len(self.audio) / self.sr
        print(f"Audio loaded: {self.duration:.1f}s, sr={sr}Hz")

    def extract_segment(self, start: float, end: float,
                       buffer_before: float = 3.0,
                       buffer_after: float = 3.0) -> Tuple[np.ndarray, float, float]:
        """
        Extract audio segment with buffer

        Returns:
            audio_segment, actual_start, actual_end
        """
        actual_start = max(0, start - buffer_before)
        actual_end = min(self.duration, end + buffer_after)

        start_sample = int(actual_start * self.sr)
        end_sample = int(actual_end * self.sr)

        segment = self.audio[start_sample:end_sample]
        return segment, actual_start, actual_end

    def create_3panel_visualization(self, sentence: Sentence,
                                   output_path: Path,
                                   buffer_before: float = 3.0,
                                   buffer_after: float = 3.0):
        """
        Create 3-panel visualization:
        - Top: Original timing
        - Middle: Waveform with buffer
        - Bottom: Adjusted timing
        """
        # Extract audio segment
        audio_segment, seg_start, seg_end = self.extract_segment(
            sentence.original_start, sentence.original_end,
            buffer_before, buffer_after
        )

        # Create figure with 3 panels
        fig, axes = plt.subplots(3, 1, figsize=(16, 10))
        fig.suptitle(f'Sentence {sentence.id}: "{sentence.text[:60]}..."',
                    fontsize=14, fontweight='bold')

        # Time axis
        time_axis = np.linspace(seg_start, seg_end, len(audio_segment))

        # Panel 1: Original timing
        ax1 = axes[0]
        ax1.plot(time_axis, audio_segment, linewidth=0.5, color='gray', alpha=0.7)
        ax1.set_title('Original Timing', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Amplitude')
        ax1.set_xlim(seg_start, seg_end)
        ax1.grid(True, alpha=0.3)

        # Highlight original word boundaries
        for word in sentence.words:
            if word.original_start and word.original_end:
                rect = patches.Rectangle(
                    (word.original_start, ax1.get_ylim()[0]),
                    word.original_duration,
                    ax1.get_ylim()[1] - ax1.get_ylim()[0],
                    linewidth=1, edgecolor='red', facecolor='red', alpha=0.2
                )
                ax1.add_patch(rect)

                # Add word label
                ax1.text(
                    word.original_start + word.original_duration/2,
                    ax1.get_ylim()[1] * 0.8,
                    word.text,
                    ha='center', va='top', fontsize=8,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7)
                )

        # Panel 2: Waveform with buffer
        ax2 = axes[1]
        ax2.plot(time_axis, audio_segment, linewidth=0.5, color='black')
        ax2.set_title(f'Waveform ({buffer_before}s buffer before/after)',
                     fontsize=12, fontweight='bold')
        ax2.set_ylabel('Amplitude')
        ax2.set_xlim(seg_start, seg_end)
        ax2.grid(True, alpha=0.3)

        # Highlight actual speech region
        rect = patches.Rectangle(
            (sentence.original_start, ax2.get_ylim()[0]),
            sentence.original_duration,
            ax2.get_ylim()[1] - ax2.get_ylim()[0],
            linewidth=2, edgecolor='blue', facecolor='none', linestyle='--'
        )
        ax2.add_patch(rect)
        ax2.text(
            sentence.original_start, ax2.get_ylim()[1] * 0.9,
            'Original sentence boundary',
            fontsize=9, color='blue'
        )

        # Panel 3: Adjusted timing
        ax3 = axes[2]
        ax3.plot(time_axis, audio_segment, linewidth=0.5, color='gray', alpha=0.7)
        ax3.set_title('Adjusted Timing', fontsize=12, fontweight='bold')
        ax3.set_xlabel('Time (seconds)')
        ax3.set_ylabel('Amplitude')
        ax3.set_xlim(seg_start, seg_end)
        ax3.grid(True, alpha=0.3)

        # Highlight adjusted word boundaries with color coding
        for word in sentence.words:
            # Color based on adjustment magnitude
            if word.adjustment_magnitude > 0.100:
                color = 'red'      # Large adjustment
            elif word.adjustment_magnitude > 0.050:
                color = 'orange'   # Moderate adjustment
            elif word.adjustment_magnitude > 0.020:
                color = 'yellow'   # Small adjustment
            else:
                color = 'green'    # Minimal adjustment

            rect = patches.Rectangle(
                (word.start, ax3.get_ylim()[0]),
                word.duration,
                ax3.get_ylim()[1] - ax3.get_ylim()[0],
                linewidth=1, edgecolor=color, facecolor=color, alpha=0.3
            )
            ax3.add_patch(rect)

            # Add word label with adjustment info
            adj_ms = word.adjustment_magnitude * 1000
            label = f"{word.text}\n({adj_ms:.0f}ms)"
            ax3.text(
                word.start + word.duration/2,
                ax3.get_ylim()[1] * 0.8,
                label,
                ha='center', va='top', fontsize=8,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7)
            )

        # Add metadata
        metadata_text = (
            f"Speaker: {sentence.speaker}  |  "
            f"Priority: {sentence.priority.upper()}  |  "
            f"Max adjustment: {sentence.max_adjustment*1000:.1f}ms  |  "
            f"Total adjustment: {sentence.total_adjustment*1000:.1f}ms  |  "
            f"Needs review: {'YES' if sentence.needs_review else 'NO'}"
        )
        fig.text(0.5, 0.02, metadata_text, ha='center', fontsize=10,
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow'))

        plt.tight_layout(rect=[0, 0.03, 1, 0.97])
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"  Created visualization: {output_path.name}")


class RetimingDatabase:
    """JSON database for tracking all retimings"""

    def __init__(self):
        self.sentences = []
        self.manual_corrections = []
        self.metadata = {
            'created': datetime.now().isoformat(),
            'version': '1.0',
            'tool': 'generate_verification_report.py'
        }

    def add_sentence(self, sentence: Sentence):
        """Add sentence to database"""
        sentence_data = {
            'id': sentence.id,
            'text': sentence.text,
            'speaker': sentence.speaker,
            'original_timing': {
                'start': sentence.original_start,
                'end': sentence.original_end,
                'duration': sentence.original_duration
            },
            'adjusted_timing': {
                'start': sentence.start,
                'end': sentence.end,
                'duration': sentence.duration
            },
            'priority': sentence.priority,
            'needs_review': sentence.needs_review,
            'max_adjustment': sentence.max_adjustment,
            'total_adjustment': sentence.total_adjustment,
            'words': []
        }

        # Add word-level details
        for word in sentence.words:
            word_data = {
                'text': word.text,
                'original_start': word.original_start or word.start,
                'original_end': word.original_end or word.end,
                'adjusted_start': word.start,
                'adjusted_end': word.end,
                'adjustment_magnitude': word.adjustment_magnitude,
                'adjustment_reason': word.adjustment_reason,
                'score': word.score,
                'is_anomalous': word.is_anomalous()
            }
            sentence_data['words'].append(word_data)

        self.sentences.append(sentence_data)

    def save(self, output_path: Path):
        """Save database to JSON"""
        data = {
            'metadata': self.metadata,
            'sentences': self.sentences,
            'manual_corrections': self.manual_corrections,
            'statistics': {
                'total_sentences': len(self.sentences),
                'needs_review': sum(1 for s in self.sentences if s['needs_review']),
                'priority_critical': sum(1 for s in self.sentences if s['priority'] == 'critical'),
                'priority_high': sum(1 for s in self.sentences if s['priority'] == 'high'),
                'priority_medium': sum(1 for s in self.sentences if s['priority'] == 'medium'),
                'priority_low': sum(1 for s in self.sentences if s['priority'] == 'low'),
            }
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\nRetiming database saved: {output_path}")


class PowerPointGenerator:
    """Generates PowerPoint presentation with embedded visualizations"""

    def __init__(self):
        from pptx import Presentation
        from pptx.util import Inches, Pt
        self.prs = Presentation()
        self.prs.slide_width = Inches(16)
        self.prs.slide_height = Inches(9)

    def add_title_slide(self, title: str, subtitle: str):
        """Add title slide"""
        from pptx.util import Inches, Pt
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])  # Blank layout

        # Add title
        txBox = slide.shapes.add_textbox(Inches(1), Inches(3), Inches(14), Inches(1.5))
        tf = txBox.text_frame
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(54)
        p.font.bold = True
        p.alignment = 1  # Center

        # Add subtitle
        txBox = slide.shapes.add_textbox(Inches(1), Inches(5), Inches(14), Inches(1))
        tf = txBox.text_frame
        p = tf.paragraphs[0]
        p.text = subtitle
        p.font.size = Pt(28)
        p.alignment = 1  # Center

    def add_sentence_slide(self, sentence: Sentence, viz_path: Path):
        """Add sentence slide with visualization"""
        from pptx.util import Inches, Pt
        from pptx.enum.shapes import MSO_SHAPE

        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])  # Blank layout

        # Add title
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(15), Inches(0.6))
        tf = title_box.text_frame
        p = tf.paragraphs[0]
        p.text = f"Sentence {sentence.id}: \"{sentence.text[:80]}...\""
        p.font.size = Pt(20)
        p.font.bold = True

        # Add visualization image
        if viz_path.exists():
            slide.shapes.add_picture(str(viz_path), Inches(0.5), Inches(1.2),
                                    width=Inches(15))

        # Add metadata box
        metadata_box = slide.shapes.add_textbox(Inches(0.5), Inches(7.8), Inches(15), Inches(0.8))
        tf = metadata_box.text_frame
        tf.word_wrap = True

        # Priority indicator
        priority_color = {
            'critical': 'RED',
            'high': 'ORANGE',
            'medium': 'YELLOW',
            'low': 'GREEN'
        }.get(sentence.priority, 'GRAY')

        p = tf.paragraphs[0]
        p.text = (
            f"Priority: {sentence.priority.upper()} [{priority_color}]  |  "
            f"Speaker: {sentence.speaker}  |  "
            f"Max Adj: {sentence.max_adjustment*1000:.1f}ms  |  "
            f"Total Adj: {sentence.total_adjustment*1000:.1f}ms  |  "
            f"Review: {'YES' if sentence.needs_review else 'NO'}"
        )
        p.font.size = Pt(14)

    def save(self, output_path: Path):
        """Save PowerPoint presentation"""
        self.prs.save(str(output_path))
        print(f"PowerPoint saved: {output_path}")


class HTMLViewerGenerator:
    """Generates interactive HTML viewer with audio playback"""

    def __init__(self, audio_path: Path):
        self.audio_path = audio_path

    def generate(self, sentences: List[Sentence], output_dir: Path,
                viz_dir: Path, database_path: Path):
        """Generate HTML interactive viewer"""
        html_dir = output_dir / 'html_viewer'
        html_dir.mkdir(exist_ok=True)

        # Copy or link audio file
        import shutil
        audio_dest = html_dir / self.audio_path.name
        if not audio_dest.exists():
            shutil.copy(self.audio_path, audio_dest)

        # Generate HTML
        html_content = self._generate_html(sentences, viz_dir, database_path,
                                          audio_dest.name)

        html_path = html_dir / 'index.html'
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"HTML viewer saved: {html_path}")
        return html_path

    def _generate_html(self, sentences: List[Sentence], viz_dir: Path,
                      database_path: Path, audio_filename: str) -> str:
        """Generate HTML content"""

        # Create sentence list HTML
        sentences_html = ""
        for s in sentences:
            priority_class = f"priority-{s.priority}"
            review_badge = '<span class="badge-review">REVIEW</span>' if s.needs_review else ''

            sentences_html += f'''
            <div class="sentence-item {priority_class}" data-sentence-id="{s.id}">
                <div class="sentence-header">
                    <span class="sentence-id">#{s.id}</span>
                    <span class="sentence-priority">{s.priority.upper()}</span>
                    {review_badge}
                    <span class="sentence-time">{s.start:.2f}s - {s.end:.2f}s</span>
                </div>
                <div class="sentence-text">{s.text}</div>
                <div class="sentence-stats">
                    Max adj: {s.max_adjustment*1000:.1f}ms |
                    Total adj: {s.total_adjustment*1000:.1f}ms |
                    Words: {len(s.words)}
                </div>
            </div>
            '''

        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Timing Verification Viewer</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #1a1a1a;
            color: #ffffff;
        }}

        .container {{
            display: grid;
            grid-template-columns: 400px 1fr;
            height: 100vh;
        }}

        .sidebar {{
            background: #2a2a2a;
            padding: 20px;
            overflow-y: auto;
            border-right: 2px solid #444;
        }}

        .main-content {{
            padding: 20px;
            overflow-y: auto;
        }}

        h1 {{
            margin-bottom: 20px;
            color: #4CAF50;
        }}

        .audio-player {{
            background: #333;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}

        audio {{
            width: 100%;
        }}

        .sentence-item {{
            background: #333;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s;
            border-left: 4px solid #555;
        }}

        .sentence-item:hover {{
            background: #3a3a3a;
            transform: translateX(5px);
        }}

        .sentence-item.active {{
            background: #2d4a2d;
            border-left-color: #4CAF50;
        }}

        .sentence-item.priority-critical {{
            border-left-color: #f44336;
        }}

        .sentence-item.priority-high {{
            border-left-color: #ff9800;
        }}

        .sentence-item.priority-medium {{
            border-left-color: #ffeb3b;
        }}

        .sentence-item.priority-low {{
            border-left-color: #4CAF50;
        }}

        .sentence-header {{
            display: flex;
            gap: 10px;
            align-items: center;
            margin-bottom: 8px;
            font-size: 12px;
        }}

        .sentence-id {{
            font-weight: bold;
            color: #4CAF50;
        }}

        .sentence-priority {{
            background: #555;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 10px;
        }}

        .badge-review {{
            background: #f44336;
            color: white;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: bold;
        }}

        .sentence-time {{
            margin-left: auto;
            color: #999;
            font-size: 11px;
        }}

        .sentence-text {{
            margin-bottom: 8px;
            line-height: 1.4;
        }}

        .sentence-stats {{
            font-size: 11px;
            color: #999;
        }}

        .visualization {{
            background: #2a2a2a;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}

        .visualization img {{
            width: 100%;
            border-radius: 4px;
        }}

        .word-editor {{
            background: #2a2a2a;
            padding: 20px;
            border-radius: 8px;
        }}

        .word-item {{
            background: #333;
            padding: 10px;
            margin-bottom: 8px;
            border-radius: 4px;
        }}

        .word-controls {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 8px;
        }}

        input[type="number"] {{
            background: #444;
            border: 1px solid #555;
            color: white;
            padding: 5px;
            border-radius: 4px;
            width: 100%;
        }}

        button {{
            background: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.3s;
        }}

        button:hover {{
            background: #45a049;
        }}

        .controls {{
            margin-top: 20px;
            display: flex;
            gap: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <h1>Sentences</h1>
            <div class="audio-player">
                <audio id="audioPlayer" controls>
                    <source src="{audio_filename}" type="audio/mpeg">
                    Your browser does not support the audio element.
                </audio>
            </div>
            <div id="sentenceList">
                {sentences_html}
            </div>
        </div>

        <div class="main-content">
            <div class="visualization" id="visualization">
                <h2>Select a sentence to view details</h2>
            </div>

            <div class="word-editor" id="wordEditor" style="display: none;">
                <h2>Word-level Timing</h2>
                <div id="wordList"></div>
                <div class="controls">
                    <button onclick="saveCorrections()">Save Corrections</button>
                    <button onclick="exportJSON()">Export JSON</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        let sentences = {json.dumps([asdict(s) for s in sentences], default=str)};
        let currentSentence = null;
        let audioPlayer = document.getElementById('audioPlayer');

        // Sentence click handler
        document.querySelectorAll('.sentence-item').forEach(item => {{
            item.addEventListener('click', function() {{
                const sentenceId = parseInt(this.dataset.sentenceId);
                loadSentence(sentenceId);
            }});
        }});

        function loadSentence(sentenceId) {{
            // Update active state
            document.querySelectorAll('.sentence-item').forEach(item => {{
                item.classList.remove('active');
            }});
            document.querySelector(`[data-sentence-id="${{sentenceId}}"]`).classList.add('active');

            // Find sentence
            currentSentence = sentences.find(s => s.id === sentenceId);
            if (!currentSentence) return;

            // Load visualization
            const viz = document.getElementById('visualization');
            viz.innerHTML = `
                <h2>Sentence ${{sentenceId}}</h2>
                <img src="../visualizations/sentence_${{String(sentenceId).padStart(4, '0')}}.png" alt="Sentence ${{sentenceId}}">
            `;

            // Load word editor
            loadWordEditor(currentSentence);

            // Seek audio
            audioPlayer.currentTime = currentSentence.start;
        }}

        function loadWordEditor(sentence) {{
            const editor = document.getElementById('wordEditor');
            const wordList = document.getElementById('wordList');
            editor.style.display = 'block';

            wordList.innerHTML = '';
            sentence.words.forEach((word, index) => {{
                const div = document.createElement('div');
                div.className = 'word-item';
                div.innerHTML = `
                    <strong>${{word.text}}</strong>
                    <span style="color: #999;">(adj: ${{(word.adjustment_magnitude * 1000).toFixed(0)}}ms)</span>
                    <div class="word-controls">
                        <div>
                            <label>Start: </label>
                            <input type="number" step="0.001" value="${{word.start}}"
                                   onchange="updateWord(${{sentence.id}}, ${{index}}, 'start', this.value)">
                        </div>
                        <div>
                            <label>End: </label>
                            <input type="number" step="0.001" value="${{word.end}}"
                                   onchange="updateWord(${{sentence.id}}, ${{index}}, 'end', this.value)">
                        </div>
                    </div>
                `;
                wordList.appendChild(div);
            }});
        }}

        function updateWord(sentenceId, wordIndex, field, value) {{
            const sentence = sentences.find(s => s.id === sentenceId);
            if (sentence && sentence.words[wordIndex]) {{
                sentence.words[wordIndex][field] = parseFloat(value);
                console.log('Updated:', sentenceId, wordIndex, field, value);
            }}
        }}

        function saveCorrections() {{
            localStorage.setItem('timing_corrections', JSON.stringify(sentences));
            alert('Corrections saved to browser storage!');
        }}

        function exportJSON() {{
            const dataStr = JSON.stringify(sentences, null, 2);
            const dataBlob = new Blob([dataStr], {{type: 'application/json'}});
            const url = URL.createObjectURL(dataBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = 'corrected_timing.json';
            link.click();
        }}

        // Load first sentence
        if (sentences.length > 0) {{
            loadSentence(sentences[0].id);
        }}
    </script>
</body>
</html>'''

        return html


def load_adjusted_transcript(json_path: str) -> List[Word]:
    """Load words from adjusted transcript JSON"""
    print(f"\nLoading adjusted transcript: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    words = []
    for segment in data['segments']:
        speaker = segment.get('speaker', 'UNKNOWN')
        for word_data in segment.get('words', []):
            word = Word(
                text=word_data['word'],
                start=word_data['start'],
                end=word_data['end'],
                score=word_data.get('score', 1.0),
                speaker=speaker,
                original_start=word_data.get('original_start'),
                original_end=word_data.get('original_end'),
                adjustment_magnitude=word_data.get('adjustment_magnitude', 0.0),
                adjustment_reason=word_data.get('adjustment_reason', '')
            )
            words.append(word)

    print(f"  Loaded {len(words)} words")
    return words


def main():
    parser = argparse.ArgumentParser(
        description='Generate verification report for timing adjustments'
    )
    parser.add_argument('audio_path', type=str, help='Path to audio file')
    parser.add_argument('json_path', type=str, help='Path to adjusted JSON transcript')
    parser.add_argument('--output-dir', type=str, default='verification_output',
                       help='Output directory (default: verification_output)')
    parser.add_argument('--pause-threshold', type=float, default=3.0,
                       help='Pause threshold for sentence breaks (seconds)')
    parser.add_argument('--buffer-before', type=float, default=3.0,
                       help='Buffer before each sentence (seconds)')
    parser.add_argument('--buffer-after', type=float, default=3.0,
                       help='Buffer after each sentence (seconds)')
    parser.add_argument('--max-sentences', type=int, default=None,
                       help='Limit number of sentences to process (for testing)')

    args = parser.parse_args()

    # Setup paths
    audio_path = Path(args.audio_path)
    json_path = Path(args.json_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    viz_dir = output_dir / 'visualizations'
    viz_dir.mkdir(exist_ok=True)

    print("\n" + "="*70)
    print("VERIFICATION REPORT GENERATOR")
    print("="*70)

    # Load words
    words = load_adjusted_transcript(str(json_path))

    # Group into sentences
    print(f"\nGrouping words into sentences (pause threshold: {args.pause_threshold}s)...")
    grouper = SentenceGrouper(pause_threshold=args.pause_threshold)
    sentences = grouper.group_sentences(words)
    print(f"  Created {len(sentences)} sentences")

    # Limit for testing
    if args.max_sentences:
        sentences = sentences[:args.max_sentences]
        print(f"  Limited to {len(sentences)} sentences for testing")

    # Initialize visualizer
    visualizer = WaveformVisualizer(str(audio_path))

    # Initialize retiming database
    database = RetimingDatabase()

    # Process each sentence
    print(f"\nGenerating visualizations...")
    for i, sentence in enumerate(sentences, 1):
        print(f"[{i}/{len(sentences)}] Sentence {sentence.id}: {len(sentence.words)} words, "
              f"priority={sentence.priority}, needs_review={sentence.needs_review}")

        # Create visualization
        viz_path = viz_dir / f"sentence_{sentence.id:04d}.png"
        visualizer.create_3panel_visualization(
            sentence, viz_path,
            buffer_before=args.buffer_before,
            buffer_after=args.buffer_after
        )

        # Add to database
        database.add_sentence(sentence)

    # Save retiming database
    db_path = output_dir / 'retimings.json'
    database.save(db_path)

    # Calculate statistics
    needs_review = sum(1 for s in sentences if s.needs_review)
    critical = sum(1 for s in sentences if s.priority == 'critical')
    high = sum(1 for s in sentences if s.priority == 'high')
    medium = sum(1 for s in sentences if s.priority == 'medium')
    low = sum(1 for s in sentences if s.priority == 'low')

    # Generate PowerPoint presentation
    print("\nGenerating PowerPoint presentation...")
    pptx_gen = PowerPointGenerator()
    pptx_gen.add_title_slide(
        "Timing Verification Report",
        f"{len(sentences)} sentences | {needs_review} need review"
    )

    for sentence in sentences:
        viz_path = viz_dir / f"sentence_{sentence.id:04d}.png"
        pptx_gen.add_sentence_slide(sentence, viz_path)

    pptx_path = output_dir / 'verification_report.pptx'
    pptx_gen.save(pptx_path)

    # Generate HTML interactive viewer
    print("\nGenerating HTML interactive viewer...")
    html_gen = HTMLViewerGenerator(audio_path)
    html_path = html_gen.generate(sentences, output_dir, viz_dir, db_path)

    # Print summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    print(f"\nTotal sentences: {len(sentences)}")
    print(f"Sentences needing review: {needs_review} ({100*needs_review/len(sentences):.1f}%)")
    print(f"\nPriority breakdown:")
    print(f"  Critical: {critical} ({100*critical/len(sentences):.1f}%)")
    print(f"  High:     {high} ({100*high/len(sentences):.1f}%)")
    print(f"  Medium:   {medium} ({100*medium/len(sentences):.1f}%)")
    print(f"  Low:      {low} ({100*low/len(sentences):.1f}%)")

    print(f"\n" + "="*70)
    print("OUTPUT FILES")
    print("="*70)
    print(f"Visualizations:      {viz_dir}")
    print(f"Retiming database:   {db_path}")
    print(f"PowerPoint:          {pptx_path}")
    print(f"HTML viewer:         {html_path}")

    print(f"\n*** Verification report complete! ***")
    print(f"\nNext steps:")
    print(f"1. Open PowerPoint: {pptx_path}")
    print(f"2. Open HTML viewer in browser: {html_path}")
    print(f"3. Review sentences flagged for manual review")
    print(f"4. Make corrections in HTML viewer and export JSON")

    return 0


if __name__ == '__main__':
    main()
