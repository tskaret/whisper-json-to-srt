#!/usr/bin/env python3
"""
Security Test Suite for json_to_srt_energy.py

Tests for critical and high-priority security vulnerabilities:
- Path traversal prevention
- Audio file validation
- JSON deserialization security
- Safe file write operations
"""

import pytest
import os
import json
import tempfile
from pathlib import Path
from json_to_srt_energy import (
    validate_file_path,
    validate_audio_file,
    safe_json_load,
    safe_write_file,
    MAX_AUDIO_FILE_SIZE,
    MAX_JSON_FILE_SIZE,
    MAX_SEGMENTS,
    MAX_WORDS_PER_SEGMENT,
)


class TestPathTraversalPrevention:
    """Test path traversal attack prevention."""

    def test_relative_path_traversal(self, tmp_path):
        """Test that ../ sequences in relative paths are rejected."""
        with pytest.raises(ValueError, match="(Path traversal detected|outside allowed directory)"):
            validate_file_path("../../etc/passwd", base_dir=str(tmp_path))

    def test_absolute_path_outside_base(self, tmp_path):
        """Test that absolute paths outside base_dir are rejected."""
        with pytest.raises(ValueError, match="outside allowed directory"):
            validate_file_path("/etc/passwd", base_dir=str(tmp_path))

    def test_symlink_outside_base(self, tmp_path):
        """Test that symlinks pointing outside base_dir are rejected."""
        # Create a file outside tmp_path
        outside_dir = tmp_path.parent / "outside"
        outside_dir.mkdir(exist_ok=True)
        outside_file = outside_dir / "target.json"
        outside_file.write_text("test")

        # Create symlink inside tmp_path pointing outside
        link = tmp_path / "link.json"
        link.symlink_to(outside_file)

        with pytest.raises(ValueError, match="outside allowed directory"):
            validate_file_path(str(link), base_dir=str(tmp_path))

    def test_valid_path_within_base(self, tmp_path):
        """Test that valid paths within base_dir are accepted."""
        file_path = tmp_path / "valid.json"
        file_path.touch()

        result = validate_file_path(str(file_path), base_dir=str(tmp_path))
        assert result == file_path.resolve()

    def test_valid_path_no_base_restriction(self, tmp_path):
        """Test that valid paths work without base_dir restriction."""
        file_path = tmp_path / "test.json"
        file_path.touch()

        result = validate_file_path(str(file_path))
        assert result == file_path.resolve()

    def test_nonexistent_file_with_must_exist(self, tmp_path):
        """Test that nonexistent files are rejected when must_exist=True."""
        nonexistent = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            validate_file_path(str(nonexistent), must_exist=True)

    def test_invalid_characters_in_path(self):
        """Test that invalid path characters are handled safely."""
        # This should not crash, but may raise ValueError
        try:
            validate_file_path("\x00invalid")
        except (ValueError, OSError):
            pass  # Expected


class TestAudioFileValidation:
    """Test audio file validation and size limits."""

    def test_unsupported_extension(self, tmp_path):
        """Test that unsupported file extensions are rejected."""
        bad_file = tmp_path / "audio.xyz"
        bad_file.touch()

        with pytest.raises(ValueError, match="Unsupported audio format"):
            validate_audio_file(str(bad_file))

    def test_supported_extensions(self, tmp_path):
        """Test that all supported extensions are accepted."""
        supported = ['.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.wma']

        for ext in supported:
            audio_file = tmp_path / f"audio{ext}"
            audio_file.write_bytes(b'fake audio data')

            result = validate_audio_file(str(audio_file))
            assert result == audio_file.resolve()

            # Clean up
            audio_file.unlink()

    def test_file_too_large(self, tmp_path):
        """Test that files exceeding size limit are rejected."""
        large_file = tmp_path / "audio.mp3"

        # Create file slightly over limit (501MB)
        with open(large_file, 'wb') as f:
            f.seek(MAX_AUDIO_FILE_SIZE + 1024 - 1)
            f.write(b'\0')

        with pytest.raises(ValueError, match="Audio file too large"):
            validate_audio_file(str(large_file))

    def test_valid_audio_file(self, tmp_path):
        """Test that valid audio files are accepted."""
        audio_file = tmp_path / "audio.mp3"
        audio_file.write_bytes(b'fake audio data' * 1000)

        result = validate_audio_file(str(audio_file))
        assert result == audio_file.resolve()

    def test_nonexistent_audio_file(self, tmp_path):
        """Test that nonexistent audio files are rejected."""
        nonexistent = tmp_path / "nonexistent.mp3"

        with pytest.raises(FileNotFoundError):
            validate_audio_file(str(nonexistent))


class TestJSONSecurity:
    """Test JSON deserialization security."""

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

    def test_json_too_large(self, tmp_path):
        """Test that JSON files exceeding size limit are rejected."""
        large_json = tmp_path / "large.json"

        # Create file slightly over limit
        with open(large_json, 'wb') as f:
            f.seek(MAX_JSON_FILE_SIZE + 1024 - 1)
            f.write(b'\0')

        with pytest.raises(ValueError, match="JSON file too large"):
            safe_json_load(large_json)

    def test_too_many_segments(self, tmp_path):
        """Test that JSON with too many segments is rejected."""
        bad_json = tmp_path / "many_segments.json"

        segments = [{"words": []} for _ in range(MAX_SEGMENTS + 1)]
        bad_json.write_text(json.dumps({"segments": segments}))

        with pytest.raises(ValueError, match="Too many segments"):
            safe_json_load(bad_json)

    def test_too_many_words_in_segment(self, tmp_path):
        """Test that segments with too many words are rejected."""
        bad_json = tmp_path / "many_words.json"

        words = [{"word": "test", "start": 0.0, "end": 0.1} for _ in range(MAX_WORDS_PER_SEGMENT + 1)]
        data = {"segments": [{"words": words}]}
        bad_json.write_text(json.dumps(data))

        with pytest.raises(ValueError, match="too many words"):
            safe_json_load(bad_json)

    def test_invalid_json_syntax(self, tmp_path):
        """Test that invalid JSON syntax is rejected."""
        bad_json = tmp_path / "invalid.json"
        bad_json.write_text("{invalid json")

        with pytest.raises(ValueError, match="Invalid JSON format"):
            safe_json_load(bad_json)

    def test_json_not_object(self, tmp_path):
        """Test that JSON root must be an object."""
        bad_json = tmp_path / "array.json"
        bad_json.write_text("[]")

        with pytest.raises(ValueError, match="Root element must be an object"):
            safe_json_load(bad_json)

    def test_json_missing_segments(self, tmp_path):
        """Test that JSON must have 'segments' key."""
        bad_json = tmp_path / "no_segments.json"
        bad_json.write_text("{}")

        with pytest.raises(ValueError, match="Missing required 'segments' key"):
            safe_json_load(bad_json)

    def test_segments_not_array(self, tmp_path):
        """Test that 'segments' must be an array."""
        bad_json = tmp_path / "bad_segments.json"
        bad_json.write_text('{"segments": "not an array"}')

        with pytest.raises(ValueError, match="'segments' must be an array"):
            safe_json_load(bad_json)

    def test_segment_not_object(self, tmp_path):
        """Test that each segment must be an object."""
        bad_json = tmp_path / "bad_segment.json"
        bad_json.write_text('{"segments": ["not an object"]}')

        with pytest.raises(ValueError, match="segment 0: Must be an object"):
            safe_json_load(bad_json)

    def test_words_not_array(self, tmp_path):
        """Test that 'words' in segment must be an array."""
        bad_json = tmp_path / "bad_words.json"
        bad_json.write_text('{"segments": [{"words": "not an array"}]}')

        with pytest.raises(ValueError, match="'words' must be an array"):
            safe_json_load(bad_json)


class TestSafeFileWrite:
    """Test safe file write operations."""

    def test_successful_write(self, tmp_path):
        """Test that valid writes succeed."""
        output_file = tmp_path / "output.srt"
        content = "Test content\nLine 2"

        safe_write_file(output_file, content)

        assert output_file.exists()
        assert output_file.read_text() == content

    def test_atomic_write_on_error(self, tmp_path):
        """Test that failed writes don't leave partial files."""
        output_file = tmp_path / "output.srt"

        # Create a scenario where write will fail (e.g., permission issues)
        # For testing, we'll use a mock that raises an exception
        original_content = "Original"
        output_file.write_text(original_content)

        # Make directory read-only to cause write failure
        original_mode = output_file.parent.stat().st_mode
        try:
            output_file.parent.chmod(0o555)

            with pytest.raises((RuntimeError, PermissionError)):
                safe_write_file(output_file, "New content")

            # Original file should still exist with original content
            # or not exist at all (not partial)
            if output_file.exists():
                assert output_file.read_text() == original_content

        finally:
            # Restore permissions
            output_file.parent.chmod(original_mode)

    def test_write_to_nonexistent_directory(self, tmp_path):
        """Test that writes to nonexistent directories fail gracefully."""
        nonexistent_dir = tmp_path / "nonexistent"
        output_file = nonexistent_dir / "output.srt"

        with pytest.raises(ValueError, match="Output directory does not exist"):
            safe_write_file(output_file, "content")

    def test_overwrite_existing_file(self, tmp_path):
        """Test that existing files are overwritten atomically."""
        output_file = tmp_path / "output.srt"
        output_file.write_text("Old content")

        new_content = "New content"
        safe_write_file(output_file, new_content)

        assert output_file.read_text() == new_content

    def test_no_leftover_temp_files(self, tmp_path):
        """Test that temporary files are cleaned up."""
        output_file = tmp_path / "output.srt"

        # Count temp files before
        temp_files_before = list(tmp_path.glob(".tmp_*"))

        safe_write_file(output_file, "content")

        # Count temp files after
        temp_files_after = list(tmp_path.glob(".tmp_*"))

        # Should have same number (or fewer) temp files
        assert len(temp_files_after) <= len(temp_files_before)


class TestIntegration:
    """Integration tests for combined security features."""

    def test_path_traversal_in_output_directory(self, tmp_path):
        """Test that output directory path traversal is prevented."""
        # This would be caught by validate_file_path in process_file
        from json_to_srt_energy import validate_file_path

        with pytest.raises(ValueError, match="(Path traversal detected|outside allowed directory)"):
            validate_file_path("../../malicious/", base_dir=str(tmp_path))

    def test_large_but_valid_json(self, tmp_path):
        """Test that large but valid JSON files work."""
        # Create a large but valid JSON (under limit)
        json_file = tmp_path / "large.json"

        # Create 1000 segments with 10 words each = 10,000 words
        segments = []
        for i in range(100):
            words = [
                {"word": f"word{j}", "start": j * 0.1, "end": j * 0.1 + 0.05, "score": 0.9}
                for j in range(10)
            ]
            segments.append({"speaker": "SPEAKER_00", "words": words})

        data = {"segments": segments}
        json_file.write_text(json.dumps(data))

        result = safe_json_load(json_file)
        assert len(result["segments"]) == 100


def test_security_constants():
    """Test that security constants are set to reasonable values."""
    assert MAX_AUDIO_FILE_SIZE == 500 * 1024 * 1024  # 500MB
    assert MAX_JSON_FILE_SIZE == 100 * 1024 * 1024  # 100MB
    assert MAX_SEGMENTS == 10000
    assert MAX_WORDS_PER_SEGMENT == 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
