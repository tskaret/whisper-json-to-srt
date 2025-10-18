#!/usr/bin/env python3
"""
Security Attack Scenario Tests
Tests that common attack vectors are properly blocked
"""

import tempfile
import json
from pathlib import Path
from json_to_srt_energy import (
    validate_file_path,
    validate_audio_file,
    safe_json_load,
)

def test_attack_scenarios():
    """Run manual security attack tests"""

    print("="*50)
    print("Security Attack Scenario Tests")
    print("="*50)
    print()

    success_count = 0
    fail_count = 0

    # Test 1: Path Traversal Attack
    print("Test 1: Path Traversal via Relative Path")
    print("-" * 50)
    try:
        validate_file_path("../../etc/passwd", base_dir="/tmp")
        print("❌ FAIL: Path traversal not blocked!")
        fail_count += 1
    except ValueError as e:
        print(f"✅ PASS: Blocked with: {e}")
        success_count += 1
    print()

    # Test 2: Absolute Path Outside Base
    print("Test 2: Absolute Path Outside Base Directory")
    print("-" * 50)
    try:
        validate_file_path("/etc/passwd", base_dir="/tmp")
        print("❌ FAIL: Absolute path escape not blocked!")
        fail_count += 1
    except ValueError as e:
        print(f"✅ PASS: Blocked with: {e}")
        success_count += 1
    print()

    # Test 3: Symlink Attack
    print("Test 3: Symlink Attack")
    print("-" * 50)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create symlink to /etc/passwd
        outside_file = Path("/etc/passwd")
        if outside_file.exists():
            link = tmpdir / "evil_link.json"
            try:
                link.symlink_to(outside_file)
                try:
                    validate_file_path(str(link), base_dir=str(tmpdir))
                    print("❌ FAIL: Symlink attack not blocked!")
                    fail_count += 1
                except ValueError as e:
                    print(f"✅ PASS: Blocked with: {e}")
                    success_count += 1
            except OSError:
                print("⚠️  SKIP: Cannot create symlink (permission denied)")
        else:
            print("⚠️  SKIP: /etc/passwd not available for testing")
    print()

    # Test 4: Invalid Audio Extension
    print("Test 4: Invalid Audio File Extension")
    print("-" * 50)
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_audio = Path(tmpdir) / "audio.xyz"
        bad_audio.touch()

        try:
            validate_audio_file(str(bad_audio))
            print("❌ FAIL: Invalid extension not blocked!")
            fail_count += 1
        except ValueError as e:
            print(f"✅ PASS: Blocked with: {e}")
            success_count += 1
    print()

    # Test 5: Oversized Audio File
    print("Test 5: Oversized Audio File")
    print("-" * 50)
    with tempfile.TemporaryDirectory() as tmpdir:
        from json_to_srt_energy import MAX_AUDIO_FILE_SIZE

        large_audio = Path(tmpdir) / "huge.mp3"
        # Create file slightly over limit
        with open(large_audio, 'wb') as f:
            f.seek(MAX_AUDIO_FILE_SIZE + 1024 - 1)
            f.write(b'\0')

        try:
            validate_audio_file(str(large_audio))
            print("❌ FAIL: Oversized file not blocked!")
            fail_count += 1
        except ValueError as e:
            print(f"✅ PASS: Blocked with: {e}")
            success_count += 1
    print()

    # Test 6: Too Many Segments
    print("Test 6: Too Many Segments in JSON")
    print("-" * 50)
    with tempfile.TemporaryDirectory() as tmpdir:
        from json_to_srt_energy import MAX_SEGMENTS

        many_segments = Path(tmpdir) / "many_segments.json"
        data = {"segments": [{"words": []} for _ in range(MAX_SEGMENTS + 1)]}
        many_segments.write_text(json.dumps(data))

        try:
            safe_json_load(many_segments)
            print("❌ FAIL: Too many segments not blocked!")
            fail_count += 1
        except ValueError as e:
            print(f"✅ PASS: Blocked with: {e}")
            success_count += 1
    print()

    # Test 7: Invalid JSON Structure
    print("Test 7: Invalid JSON Syntax")
    print("-" * 50)
    with tempfile.TemporaryDirectory() as tmpdir:
        invalid_json = Path(tmpdir) / "invalid.json"
        invalid_json.write_text("{invalid json")

        try:
            safe_json_load(invalid_json)
            print("❌ FAIL: Invalid JSON not blocked!")
            fail_count += 1
        except ValueError as e:
            print(f"✅ PASS: Blocked with: {e}")
            success_count += 1
    print()

    # Test 8: Missing Required Fields
    print("Test 8: Missing Required JSON Fields")
    print("-" * 50)
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_json = Path(tmpdir) / "no_segments.json"
        bad_json.write_text('{}')

        try:
            safe_json_load(bad_json)
            print("❌ FAIL: Missing segments not detected!")
            fail_count += 1
        except ValueError as e:
            print(f"✅ PASS: Blocked with: {e}")
            success_count += 1
    print()

    # Test 9: Oversized JSON File
    print("Test 9: Oversized JSON File")
    print("-" * 50)
    with tempfile.TemporaryDirectory() as tmpdir:
        from json_to_srt_energy import MAX_JSON_FILE_SIZE

        huge_json = Path(tmpdir) / "huge.json"
        with open(huge_json, 'wb') as f:
            f.seek(MAX_JSON_FILE_SIZE + 1024 - 1)
            f.write(b'\0')

        try:
            safe_json_load(huge_json)
            print("❌ FAIL: Oversized JSON not blocked!")
            fail_count += 1
        except ValueError as e:
            print(f"✅ PASS: Blocked with: {e}")
            success_count += 1
    print()

    # Test 10: Segments Not Array
    print("Test 10: Invalid Segment Structure")
    print("-" * 50)
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_structure = Path(tmpdir) / "bad_structure.json"
        bad_structure.write_text('{"segments": "not_an_array"}')

        try:
            safe_json_load(bad_structure)
            print("❌ FAIL: Invalid structure not blocked!")
            fail_count += 1
        except ValueError as e:
            print(f"✅ PASS: Blocked with: {e}")
            success_count += 1
    print()

    # Summary
    print("="*50)
    print("Test Summary")
    print("="*50)
    print(f"✅ Passed: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print(f"Total: {success_count + fail_count}")
    print()

    if fail_count == 0:
        print("🎉 ALL SECURITY TESTS PASSED!")
        print("All attack vectors are properly blocked.")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED!")
        print("Security vulnerabilities may still exist.")
        return 1


if __name__ == "__main__":
    exit(test_attack_scenarios())
