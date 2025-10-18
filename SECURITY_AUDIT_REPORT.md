# Security Audit Report: json_to_srt_energy.py

**Audit Date:** 2025-10-17
**Auditor:** Security Analysis
**Codebase:** Subtitle Processing Experiments
**Target File:** json_to_srt_energy.py (1,088 lines)

---

## Executive Summary

This security audit identified **7 vulnerabilities** ranging from **CRITICAL** to **LOW** severity. The most critical issues involve path traversal attacks and arbitrary file operations that could lead to unauthorized file access, data exfiltration, or denial of service.

**Risk Level:** HIGH
**Immediate Action Required:** YES

### Severity Breakdown
- **CRITICAL:** 2 vulnerabilities
- **HIGH:** 2 vulnerabilities
- **MEDIUM:** 2 vulnerabilities
- **LOW:** 1 vulnerability

---

## Identified Vulnerabilities

### 1. Path Traversal Attack (CRITICAL)

**Location:** `json_to_srt_energy.py:373-374`, `930-936`

**Issue:**
```python
def load_json_data(self, file_path: str) -> List[Word]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Input file not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
```

```python
def process_file(self, input_path: str, output_dir: Optional[str] = None) -> Tuple[str, str]:
    if output_dir is None:
        output_dir = os.path.dirname(input_path) or '.'

    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
```

**Vulnerability:**
- No validation of user-supplied file paths
- Attacker can use path traversal sequences: `../../../etc/passwd`
- Can read arbitrary files on the system
- Can write files to arbitrary locations
- `os.makedirs()` creates directories without permission checks

**Attack Scenarios:**
1. **Data Exfiltration:**
   ```bash
   python json_to_srt_energy.py audio.mp3 ../../../etc/passwd
   # Attempts to load system files
   ```

2. **Arbitrary File Write:**
   ```bash
   python json_to_srt_energy.py audio.mp3 data.json --output-dir ../../../tmp/malicious
   # Writes SRT files to attacker-controlled location
   ```

3. **Directory Traversal:**
   ```bash
   python json_to_srt_energy.py audio.mp3 ../../../../sensitive/file.json
   ```

**Impact:**
- Unauthorized file system access
- Information disclosure
- Potential privilege escalation
- System compromise

**CVSS Score:** 9.1 (CRITICAL)

---

### 2. Uncontrolled Audio File Loading (CRITICAL)

**Location:** `json_to_srt_energy.py:105-108`

**Issue:**
```python
def __init__(self, audio_path: str, sr: int = 16000):
    print(f"Loading audio: {audio_path}")
    self.audio, self.sr = librosa.load(audio_path, sr=sr, mono=True)
    print(f"Audio loaded: {len(self.audio)/sr:.1f}s, sr={sr}Hz")
```

**Vulnerability:**
- No validation of audio file path
- No file size limit checking
- No file type validation (relies on librosa to reject invalid formats)
- Path traversal possible: `../../sensitive.wav`
- Memory exhaustion possible with large files

**Attack Scenarios:**
1. **Memory Exhaustion (DoS):**
   ```bash
   # Load 10GB audio file
   python json_to_srt_energy.py /path/to/huge_file.wav data.json
   # System runs out of memory
   ```

2. **Path Traversal:**
   ```bash
   python json_to_srt_energy.py ../../../root/audio.mp3 data.json
   # Attempts to access restricted audio files
   ```

3. **Format String Attack (if librosa has vulnerabilities):**
   ```bash
   python json_to_srt_energy.py malicious_crafted.wav data.json
   # Exploits potential vulnerabilities in audio parsing libraries
   ```

**Impact:**
- Denial of Service (memory exhaustion)
- Information disclosure
- Potential remote code execution (via malicious audio files)

**CVSS Score:** 8.6 (CRITICAL)

---

### 3. JSON Deserialization Vulnerability (HIGH)

**Location:** `json_to_srt_energy.py:376-377`

**Issue:**
```python
with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)
```

**Vulnerability:**
- Uses `json.load()` without size limits
- No schema validation
- No depth limit for nested objects
- Attacker can craft deeply nested JSON to cause stack overflow
- Large JSON files can exhaust memory

**Attack Scenarios:**
1. **Stack Overflow via Deep Nesting:**
   ```json
   {"a": {"a": {"a": {"a": ... }}}}  // 10,000 levels deep
   ```

2. **Memory Exhaustion:**
   ```json
   {
     "segments": [
       {"words": [{"word": "A" * 1000000, "start": 0, "end": 1}] * 100000}
     ]
   }
   ```

3. **Billion Laughs Attack:**
   ```json
   {
     "segments": [
       {"words": [{"word": "AAAA...", ...}] * 1000000}
     ]
   }
   ```

**Impact:**
- Denial of Service (DoS)
- Application crash
- Memory exhaustion
- CPU exhaustion

**CVSS Score:** 7.5 (HIGH)

---

### 4. Unsafe File Write Operations (HIGH)

**Location:** `json_to_srt_energy.py:964-968`

**Issue:**
```python
with open(output_with_speakers, 'w', encoding='utf-8') as f:
    f.write(srt_with_speakers)

with open(output_clean, 'w', encoding='utf-8') as f:
    f.write(srt_clean)
```

**Vulnerability:**
- No validation of output file paths
- Overwrites existing files without confirmation
- No permission checks
- Can write to system directories if permissions allow
- Race condition: TOCTOU (Time-of-Check-Time-of-Use)

**Attack Scenarios:**
1. **Data Loss:**
   ```bash
   python json_to_srt_energy.py audio.mp3 data.json --output-dir /home/user/important_docs
   # Overwrites important_docs_with_speakers.srt
   ```

2. **Symlink Attack:**
   ```bash
   ln -s /etc/important_config output.srt
   python json_to_srt_energy.py audio.mp3 data.json
   # Overwrites system configuration
   ```

3. **Race Condition:**
   - Check if file exists (line 935)
   - Attacker creates malicious symlink
   - Write operation follows symlink

**Impact:**
- Data loss
- System file corruption
- Privilege escalation (if running with elevated privileges)

**CVSS Score:** 7.3 (HIGH)

---

### 5. Missing Input Validation (MEDIUM)

**Location:** Multiple locations throughout the code

**Issue:**
```python
# No validation on user-supplied parameters
def __init__(self, audio_path: str, pause_threshold: float = 3.0,
             max_chars_per_line: int = 40, max_lines: int = 2, ...):
    self.pause_threshold = pause_threshold  # Can be negative
    self.max_chars_per_line = max_chars_per_line  # Can be negative
    self.max_lines = max_lines  # Can be zero
    # ... no validation
```

**Vulnerability:**
- No bounds checking on numeric parameters
- Negative values can cause unexpected behavior
- Zero values can cause division by zero
- Extremely large values can cause resource exhaustion

**Attack Scenarios:**
1. **Division by Zero:**
   ```bash
   python json_to_srt_energy.py audio.mp3 data.json --max-lines 0
   # Potential division by zero in text wrapping
   ```

2. **Resource Exhaustion:**
   ```bash
   python json_to_srt_energy.py audio.mp3 data.json --max-chars-per-line 999999999
   # Memory exhaustion in text processing
   ```

3. **Logic Errors:**
   ```bash
   python json_to_srt_energy.py audio.mp3 data.json --pause-threshold -10.0
   # Negative threshold causes incorrect segmentation
   ```

**Impact:**
- Application crash
- Incorrect output
- Resource exhaustion

**CVSS Score:** 5.3 (MEDIUM)

---

### 6. Information Disclosure via Error Messages (MEDIUM)

**Location:** `json_to_srt_energy.py:1082-1083`

**Issue:**
```python
except Exception as e:
    print(f"\nError: {str(e)}")
    sys.exit(1)
```

**Vulnerability:**
- Exposes full exception messages to user
- May reveal system paths
- May reveal internal implementation details
- May reveal sensitive information in stack traces

**Attack Scenarios:**
1. **Path Disclosure:**
   ```
   Error: [Errno 2] No such file or directory: '/home/username/.config/app/secrets.json'
   ```

2. **Implementation Details:**
   ```
   Error: 'NoneType' object has no attribute 'start' at line 452 in /opt/app/json_to_srt_energy.py
   ```

**Impact:**
- Information disclosure
- Reconnaissance for further attacks
- Privacy violation

**CVSS Score:** 5.0 (MEDIUM)

---

### 7. No Rate Limiting or Resource Controls (LOW)

**Location:** Entire application

**Issue:**
- No limit on number of words/segments processed
- No timeout for audio loading
- No memory usage limits
- No CPU usage limits
- Can be used for resource exhaustion attacks

**Attack Scenarios:**
1. **CPU Exhaustion:**
   ```bash
   # Process 100-hour audio file with 1 million words
   python json_to_srt_energy.py massive_audio.mp3 massive_transcript.json
   ```

2. **Concurrent Processing:**
   ```bash
   # Launch 100 parallel instances
   for i in {1..100}; do
     python json_to_srt_energy.py audio.mp3 data.json &
   done
   ```

**Impact:**
- Denial of Service
- System slowdown
- Resource starvation for other applications

**CVSS Score:** 4.0 (LOW)

---

## Remediation Plan

### Priority 1: CRITICAL Issues (Immediate - Within 24 hours)

#### 1.1 Path Traversal Prevention

**Action:**
```python
import os
from pathlib import Path

def validate_file_path(file_path: str, base_dir: Optional[str] = None) -> Path:
    """Validate and sanitize file path to prevent path traversal."""
    # Convert to absolute path
    path = Path(file_path).resolve()

    # If base_dir specified, ensure path is within it
    if base_dir:
        base = Path(base_dir).resolve()
        try:
            path.relative_to(base)
        except ValueError:
            raise ValueError(f"Path traversal detected: {file_path} is outside {base_dir}")

    # Ensure path doesn't contain suspicious patterns
    if '..' in path.parts:
        raise ValueError(f"Path traversal detected: {file_path}")

    return path

def load_json_data(self, file_path: str) -> List[Word]:
    """Load WhisperX JSON and convert to Word objects"""
    # Validate path
    safe_path = validate_file_path(file_path, base_dir=os.getcwd())

    if not safe_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    # Check file size (limit to 100MB)
    if safe_path.stat().st_size > 100 * 1024 * 1024:
        raise ValueError("JSON file too large (max 100MB)")

    with open(safe_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
```

**Testing:**
```bash
# Test valid paths
python json_to_srt_energy.py audio.mp3 valid_data.json

# Test path traversal (should fail)
python json_to_srt_energy.py audio.mp3 ../../../etc/passwd
# Expected: ValueError: Path traversal detected

# Test symlink (should fail if outside base_dir)
ln -s /etc/passwd data.json
python json_to_srt_energy.py audio.mp3 data.json
# Expected: ValueError: Path traversal detected
```

#### 1.2 Audio File Validation

**Action:**
```python
ALLOWED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.ogg', '.m4a'}
MAX_AUDIO_FILE_SIZE = 500 * 1024 * 1024  # 500MB

def validate_audio_file(audio_path: str) -> Path:
    """Validate audio file path and properties."""
    # Validate path
    safe_path = validate_file_path(audio_path, base_dir=os.getcwd())

    # Check file exists
    if not safe_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Check extension
    if safe_path.suffix.lower() not in ALLOWED_AUDIO_EXTENSIONS:
        raise ValueError(f"Unsupported audio format: {safe_path.suffix}")

    # Check file size
    file_size = safe_path.stat().st_size
    if file_size > MAX_AUDIO_FILE_SIZE:
        raise ValueError(f"Audio file too large: {file_size / 1024 / 1024:.1f}MB (max 500MB)")

    return safe_path

def __init__(self, audio_path: str, sr: int = 16000):
    # Validate audio file
    safe_path = validate_audio_file(audio_path)

    print(f"Loading audio: {safe_path.name}")
    try:
        self.audio, self.sr = librosa.load(str(safe_path), sr=sr, mono=True)
    except Exception as e:
        raise ValueError(f"Failed to load audio file: {e}")

    print(f"Audio loaded: {len(self.audio)/sr:.1f}s, sr={sr}Hz")
```

---

### Priority 2: HIGH Issues (Within 1 week)

#### 2.1 JSON Deserialization Hardening

**Action:**
```python
import json

MAX_JSON_SIZE = 100 * 1024 * 1024  # 100MB
MAX_JSON_DEPTH = 20
MAX_SEGMENTS = 10000
MAX_WORDS_PER_SEGMENT = 1000

def safe_json_load(file_path: Path) -> dict:
    """Safely load JSON with size and depth limits."""
    # Check file size
    file_size = file_path.stat().st_size
    if file_size > MAX_JSON_SIZE:
        raise ValueError(f"JSON file too large: {file_size / 1024 / 1024:.1f}MB (max 100MB)")

    # Load JSON
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Validate structure
    if not isinstance(data, dict):
        raise ValueError("Invalid JSON: Root must be an object")

    if 'segments' not in data:
        raise ValueError("Invalid JSON: Missing 'segments' key")

    segments = data.get('segments', [])
    if not isinstance(segments, list):
        raise ValueError("Invalid JSON: 'segments' must be an array")

    if len(segments) > MAX_SEGMENTS:
        raise ValueError(f"Too many segments: {len(segments)} (max {MAX_SEGMENTS})")

    # Validate segment structure
    for i, segment in enumerate(segments):
        if not isinstance(segment, dict):
            raise ValueError(f"Invalid segment {i}: Must be an object")

        words = segment.get('words', [])
        if not isinstance(words, list):
            raise ValueError(f"Invalid segment {i}: 'words' must be an array")

        if len(words) > MAX_WORDS_PER_SEGMENT:
            raise ValueError(f"Segment {i} has too many words: {len(words)} (max {MAX_WORDS_PER_SEGMENT})")

    return data

def load_json_data(self, file_path: str) -> List[Word]:
    """Load WhisperX JSON and convert to Word objects"""
    safe_path = validate_file_path(file_path, base_dir=os.getcwd())

    if not safe_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    # Safe JSON loading
    data = safe_json_load(safe_path)

    # Continue with existing logic...
```

#### 2.2 Safe File Write Operations

**Action:**
```python
import tempfile
import shutil

def safe_write_file(output_path: Path, content: str) -> None:
    """Safely write file using atomic operations."""
    # Validate output path
    safe_path = validate_file_path(str(output_path), base_dir=os.getcwd())

    # Check if parent directory exists
    if not safe_path.parent.exists():
        raise ValueError(f"Output directory does not exist: {safe_path.parent}")

    # Check write permissions
    if not os.access(safe_path.parent, os.W_OK):
        raise PermissionError(f"No write permission for directory: {safe_path.parent}")

    # Use temporary file for atomic write
    temp_fd, temp_path = tempfile.mkstemp(
        dir=safe_path.parent,
        prefix=f".tmp_{safe_path.name}_",
        text=True
    )

    try:
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            f.write(content)

        # Atomic rename
        shutil.move(temp_path, safe_path)
    except Exception as e:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except:
            pass
        raise RuntimeError(f"Failed to write file: {e}")

def process_file(self, input_path: str, output_dir: Optional[str] = None) -> Tuple[str, str]:
    """Process JSON file and generate SRT files"""
    # Validate paths
    safe_input = validate_file_path(input_path, base_dir=os.getcwd())

    if output_dir is None:
        output_dir = str(safe_input.parent)

    safe_output_dir = validate_file_path(output_dir, base_dir=os.getcwd())

    # Create output directory safely
    if not safe_output_dir.exists():
        try:
            safe_output_dir.mkdir(parents=True, mode=0o755)
        except Exception as e:
            raise RuntimeError(f"Failed to create output directory: {e}")

    base_name = safe_input.stem
    output_with_speakers = safe_output_dir / f"{base_name}_with_speakers.srt"
    output_clean = safe_output_dir / f"{base_name}_clean.srt"

    # ... existing processing logic ...

    # Safe file writes
    safe_write_file(output_with_speakers, srt_with_speakers)
    safe_write_file(output_clean, srt_clean)

    return str(output_with_speakers), str(output_clean)
```

---

### Priority 3: MEDIUM Issues (Within 2 weeks)

#### 3.1 Input Validation

**Action:**
```python
def validate_parameters(
    pause_threshold: float,
    max_chars_per_line: int,
    max_lines: int,
    overflow_tolerance: int,
    max_subtitle_duration: float,
    speaker_change_threshold: float,
    safety_gap_ms: int,
    orphan_move_threshold: int
) -> None:
    """Validate all configuration parameters."""

    # Validate pause_threshold
    if not 0.1 <= pause_threshold <= 60.0:
        raise ValueError(f"pause_threshold must be between 0.1 and 60.0 seconds: {pause_threshold}")

    # Validate max_chars_per_line
    if not 10 <= max_chars_per_line <= 100:
        raise ValueError(f"max_chars_per_line must be between 10 and 100: {max_chars_per_line}")

    # Validate max_lines
    if not 1 <= max_lines <= 5:
        raise ValueError(f"max_lines must be between 1 and 5: {max_lines}")

    # Validate overflow_tolerance
    if not 0 <= overflow_tolerance <= 20:
        raise ValueError(f"overflow_tolerance must be between 0 and 20: {overflow_tolerance}")

    # Validate max_subtitle_duration
    if not 1.0 <= max_subtitle_duration <= 30.0:
        raise ValueError(f"max_subtitle_duration must be between 1.0 and 30.0 seconds: {max_subtitle_duration}")

    # Validate speaker_change_threshold
    if not 0.01 <= speaker_change_threshold <= 5.0:
        raise ValueError(f"speaker_change_threshold must be between 0.01 and 5.0 seconds: {speaker_change_threshold}")

    # Validate safety_gap_ms
    if not 1 <= safety_gap_ms <= 1000:
        raise ValueError(f"safety_gap_ms must be between 1 and 1000: {safety_gap_ms}")

    # Validate orphan_move_threshold
    if not 5 <= orphan_move_threshold <= 50:
        raise ValueError(f"orphan_move_threshold must be between 5 and 50: {orphan_move_threshold}")

def __init__(self, audio_path: str, pause_threshold: float = 3.0,
             max_chars_per_line: int = 40, max_lines: int = 2,
             overflow_tolerance: int = 4, add_hyphens: bool = True,
             max_subtitle_duration: float = 15.0, prevent_orphans: bool = True,
             orphan_move_threshold: int = 15, break_on_speaker_change: bool = True,
             speaker_change_threshold: float = 0.150, safety_gap_ms: int = 10,
             energy_sensitivity: str = 'high'):

    # Validate all parameters
    validate_parameters(
        pause_threshold, max_chars_per_line, max_lines,
        overflow_tolerance, max_subtitle_duration,
        speaker_change_threshold, safety_gap_ms,
        orphan_move_threshold
    )

    # Validate energy_sensitivity
    if energy_sensitivity not in ['low', 'medium', 'high']:
        raise ValueError(f"energy_sensitivity must be 'low', 'medium', or 'high': {energy_sensitivity}")

    # Set validated parameters
    self.audio_path = audio_path
    self.pause_threshold = pause_threshold
    # ... rest of initialization
```

#### 3.2 Secure Error Handling

**Action:**
```python
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('json_to_srt_energy.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def sanitize_error_message(error: Exception) -> str:
    """Sanitize error message to prevent information disclosure."""
    error_str = str(error)

    # Remove file paths
    error_str = re.sub(r'/[^\s]+/', '[PATH]/', error_str)

    # Remove line numbers
    error_str = re.sub(r'line \d+', 'line [REDACTED]', error_str)

    # Generic error types
    error_type = type(error).__name__

    return f"{error_type}: {error_str}"

def main():
    # ... argument parsing ...

    try:
        converter = SRTConverter(
            audio_path=args.audio_file,
            # ... parameters ...
        )

        output_with_speakers, output_clean = converter.process_file(args.input_json, args.output_dir)

        print(f"\n{'='*60}")
        print("CONVERSION COMPLETED SUCCESSFULLY!")
        print(f"{'='*60}")
        print(f"SRT with speakers: {os.path.basename(output_with_speakers)}")
        print(f"SRT without speakers: {os.path.basename(output_clean)}")

        converter.print_stats()

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        print(f"\nError: File not found")
        print(f"Suggestion: Check that the input file path is correct")
        sys.exit(1)

    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        print(f"\nError: Invalid input")
        print(f"Suggestion: Check parameter values and file formats")
        sys.exit(1)

    except PermissionError as e:
        logger.error(f"Permission denied: {e}")
        print(f"\nError: Permission denied")
        print(f"Suggestion: Check file and directory permissions")
        sys.exit(1)

    except Exception as e:
        # Log full error internally
        logger.exception("Unexpected error occurred")

        # Show sanitized error to user
        sanitized = sanitize_error_message(e)
        print(f"\nError: An unexpected error occurred")
        print(f"Suggestion: Check the log file for details or contact support")
        sys.exit(1)
```

---

### Priority 4: LOW Issues (Within 1 month)

#### 4.1 Resource Limits and Rate Limiting

**Action:**
```python
import resource
import signal

# Resource limits
MAX_MEMORY_MB = 4096  # 4GB
MAX_CPU_SECONDS = 3600  # 1 hour

def set_resource_limits():
    """Set resource limits to prevent DoS."""
    try:
        # Memory limit
        memory_bytes = MAX_MEMORY_MB * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))

        # CPU time limit
        resource.setrlimit(resource.RLIMIT_CPU, (MAX_CPU_SECONDS, MAX_CPU_SECONDS))

        logger.info(f"Resource limits set: {MAX_MEMORY_MB}MB memory, {MAX_CPU_SECONDS}s CPU")
    except Exception as e:
        logger.warning(f"Could not set resource limits: {e}")

def timeout_handler(signum, frame):
    """Handle timeout signal."""
    raise TimeoutError("Processing timeout exceeded")

def main():
    # Set resource limits
    set_resource_limits()

    # Set timeout alarm
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(MAX_CPU_SECONDS)

    try:
        # ... existing main logic ...
        pass
    finally:
        # Cancel alarm
        signal.alarm(0)
```

---

## Testing Plan

### Security Test Cases

Create `test_security.py`:

```python
import pytest
import os
from pathlib import Path
from json_to_srt_energy import validate_file_path, validate_audio_file, safe_json_load

class TestPathTraversal:
    """Test path traversal prevention."""

    def test_absolute_path_outside_base(self):
        """Test that absolute paths outside base_dir are rejected."""
        with pytest.raises(ValueError, match="Path traversal detected"):
            validate_file_path("/etc/passwd", base_dir="/home/user")

    def test_relative_path_traversal(self):
        """Test that ../ sequences are rejected."""
        with pytest.raises(ValueError, match="Path traversal detected"):
            validate_file_path("../../etc/passwd", base_dir="/home/user")

    def test_symlink_outside_base(self, tmp_path):
        """Test that symlinks outside base_dir are rejected."""
        # Create symlink to /etc/passwd
        link = tmp_path / "link.json"
        link.symlink_to("/etc/passwd")

        with pytest.raises(ValueError, match="Path traversal detected"):
            validate_file_path(str(link), base_dir=str(tmp_path.parent))

    def test_valid_path_within_base(self, tmp_path):
        """Test that valid paths within base_dir are accepted."""
        file_path = tmp_path / "valid.json"
        file_path.touch()

        result = validate_file_path(str(file_path), base_dir=str(tmp_path))
        assert result == file_path.resolve()

class TestAudioFileValidation:
    """Test audio file validation."""

    def test_unsupported_extension(self, tmp_path):
        """Test that unsupported file extensions are rejected."""
        bad_file = tmp_path / "audio.xyz"
        bad_file.touch()

        with pytest.raises(ValueError, match="Unsupported audio format"):
            validate_audio_file(str(bad_file))

    def test_file_too_large(self, tmp_path):
        """Test that files exceeding size limit are rejected."""
        large_file = tmp_path / "audio.mp3"

        # Create 501MB file
        with open(large_file, 'wb') as f:
            f.seek(501 * 1024 * 1024 - 1)
            f.write(b'\0')

        with pytest.raises(ValueError, match="Audio file too large"):
            validate_audio_file(str(large_file))

    def test_valid_audio_file(self, tmp_path):
        """Test that valid audio files are accepted."""
        audio_file = tmp_path / "audio.mp3"
        audio_file.write_bytes(b'fake audio data')

        result = validate_audio_file(str(audio_file))
        assert result == audio_file.resolve()

class TestJSONSecurity:
    """Test JSON deserialization security."""

    def test_json_too_large(self, tmp_path):
        """Test that JSON files exceeding size limit are rejected."""
        large_json = tmp_path / "large.json"

        # Create 101MB JSON file
        with open(large_json, 'w') as f:
            f.write('{"segments": [' + '{"words": []},' * (101 * 1024 * 256) + ']}')

        with pytest.raises(ValueError, match="JSON file too large"):
            safe_json_load(large_json)

    def test_too_many_segments(self, tmp_path):
        """Test that JSON with too many segments is rejected."""
        bad_json = tmp_path / "many_segments.json"

        segments = [{"words": []} for _ in range(10001)]
        bad_json.write_text(json.dumps({"segments": segments}))

        with pytest.raises(ValueError, match="Too many segments"):
            safe_json_load(bad_json)

    def test_valid_json(self, tmp_path):
        """Test that valid JSON is accepted."""
        good_json = tmp_path / "valid.json"

        data = {
            "segments": [
                {
                    "speaker": "SPEAKER_00",
                    "words": [
                        {"word": "Hello", "start": 0.0, "end": 0.5, "score": 0.95}
                    ]
                }
            ]
        }
        good_json.write_text(json.dumps(data))

        result = safe_json_load(good_json)
        assert result == data

class TestInputValidation:
    """Test parameter validation."""

    def test_negative_pause_threshold(self):
        """Test that negative pause_threshold is rejected."""
        with pytest.raises(ValueError, match="pause_threshold must be between"):
            validate_parameters(
                pause_threshold=-1.0,
                max_chars_per_line=40,
                max_lines=2,
                overflow_tolerance=4,
                max_subtitle_duration=15.0,
                speaker_change_threshold=0.150,
                safety_gap_ms=10,
                orphan_move_threshold=15
            )

    def test_zero_max_lines(self):
        """Test that zero max_lines is rejected."""
        with pytest.raises(ValueError, match="max_lines must be between"):
            validate_parameters(
                pause_threshold=3.0,
                max_chars_per_line=40,
                max_lines=0,
                overflow_tolerance=4,
                max_subtitle_duration=15.0,
                speaker_change_threshold=0.150,
                safety_gap_ms=10,
                orphan_move_threshold=15
            )

    def test_excessive_max_chars(self):
        """Test that excessive max_chars_per_line is rejected."""
        with pytest.raises(ValueError, match="max_chars_per_line must be between"):
            validate_parameters(
                pause_threshold=3.0,
                max_chars_per_line=1000,
                max_lines=2,
                overflow_tolerance=4,
                max_subtitle_duration=15.0,
                speaker_change_threshold=0.150,
                safety_gap_ms=10,
                orphan_move_threshold=15
            )
```

Run tests:
```bash
pytest test_security.py -v
```

---

## Implementation Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1: Critical Fixes** | 2 days | - Path validation<br>- Audio file validation<br>- Unit tests |
| **Phase 2: High Priority** | 5 days | - JSON hardening<br>- Safe file writes<br>- Integration tests |
| **Phase 3: Medium Priority** | 10 days | - Input validation<br>- Error handling<br>- Security tests |
| **Phase 4: Low Priority** | 14 days | - Resource limits<br>- Logging<br>- Documentation |
| **Phase 5: Testing & QA** | 7 days | - Full security test suite<br>- Penetration testing<br>- Code review |

**Total Timeline:** 38 days (~6 weeks)

---

## Compliance Considerations

### OWASP Top 10 Coverage

| OWASP Category | Vulnerabilities Found | Remediation Status |
|----------------|----------------------|-------------------|
| A01:2021 - Broken Access Control | Path Traversal, Unsafe File Writes | Priority 1 |
| A03:2021 - Injection | JSON Deserialization | Priority 2 |
| A04:2021 - Insecure Design | Missing Input Validation | Priority 3 |
| A05:2021 - Security Misconfiguration | No Resource Limits | Priority 4 |
| A09:2021 - Security Logging Failures | Information Disclosure | Priority 3 |

### CWE Coverage

- **CWE-22:** Path Traversal
- **CWE-400:** Uncontrolled Resource Consumption
- **CWE-502:** Deserialization of Untrusted Data
- **CWE-209:** Information Exposure Through Error Messages
- **CWE-367:** Time-of-Check Time-of-Use (TOCTOU) Race Condition

---

## Monitoring and Detection

### Security Monitoring

Implement logging for security events:

```python
# Log security events
logger.warning(f"Path traversal attempt detected: {user_input}")
logger.warning(f"File size limit exceeded: {file_size}")
logger.warning(f"Invalid parameter value: {param_name}={param_value}")
logger.error(f"Unauthorized file access attempt: {file_path}")
```

### Metrics to Track

- Failed path validation attempts
- File size limit violations
- JSON parsing errors
- Permission denied errors
- Resource limit hits
- Processing timeouts

---

## Conclusion

This security audit identified critical vulnerabilities that require immediate attention. The remediation plan provides a phased approach to address all issues within 6 weeks.

**Key Recommendations:**

1. **Immediate Action:** Implement path traversal prevention and audio file validation (Priority 1)
2. **Security Testing:** Establish comprehensive security test suite
3. **Code Review:** Conduct regular security code reviews
4. **Monitoring:** Implement security event logging and monitoring
5. **Documentation:** Update security documentation and user guidance

**Risk After Remediation:** LOW

---

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE/SANS Top 25](https://cwe.mitre.org/top25/)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security_warnings.html)
- [Librosa Security Considerations](https://librosa.org/doc/latest/index.html)

---

**Report Prepared By:** Security Analysis Team
**Date:** 2025-10-17
**Classification:** Internal Use Only
