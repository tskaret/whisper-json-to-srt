#!/usr/bin/env python3
"""
Refactoring script: Extract constants and test MD5 identity

This script creates a refactored version of json_to_srt_energy.py with:
1. Magic numbers extracted to named constants
2. Complex methods split into smaller helper methods
3. Better documentation
4. Identical output verified by MD5 hash
"""

import subprocess
import hashlib
import sys
from pathlib import Path

# Test configuration
TEST_AUDIO = r"D:\stevner\2025\regionalt\Lørdag\04-LørdagEttermiddag\04-LørdagEttermiddag.mp3"
TEST_JSON = r"D:\stevner\2025\regionalt\Lørdag\04-LørdagEttermiddag\04-LørdagEttermiddag.json"
TEST_OUTPUT_ORIGINAL = r"D:\stevner\2025\regionalt\Lørdag\04-LørdagEttermiddag\test_pause_1.6"
TEST_OUTPUT_REFACTORED = r"D:\stevner\2025\regionalt\Lørdag\04-LørdagEttermiddag\test_refactored"
TEST_ARGS = ["--pause-threshold", "1.6", "--max-chars-per-line", "37", "--no-break-on-speaker-change"]

BASELINE_MD5_CLEAN = "143ba9f9893662081fd1682d254917b3"
BASELINE_MD5_SPEAKERS = "95db5a38a3eb6f0c2e2139d64f15acf3"

def calculate_md5(filepath):
    """Calculate MD5 hash of file"""
    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5.update(chunk)
    return md5.hexdigest()

def run_test(script_name, output_dir):
    """Run script and return MD5 hashes"""
    cmd = [
        "python", script_name,
        TEST_AUDIO, TEST_JSON,
        "--output-dir", output_dir
    ] + TEST_ARGS

    print(f"\nRunning: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"ERROR: {result.stderr}")
        return None, None

    clean_srt = Path(output_dir) / "04-LørdagEttermiddag_clean.srt"
    speakers_srt = Path(output_dir) / "04-LørdagEttermiddag_with_speakers.srt"

    md5_clean = calculate_md5(clean_srt)
    md5_speakers = calculate_md5(speakers_srt)

    return md5_clean, md5_speakers

def main():
    print("="*60)
    print("REFACTORING VERIFICATION TEST")
    print("="*60)

    print("\nBaseline MD5 hashes:")
    print(f"  clean.srt:        {BASELINE_MD5_CLEAN}")
    print(f"  with_speakers.srt: {BASELINE_MD5_SPEAKERS}")

    # Test refactored version
    print("\n" + "="*60)
    print("Testing REFACTORED version...")
    print("="*60)

    md5_clean, md5_speakers = run_test("json_to_srt_energy.py", TEST_OUTPUT_REFACTORED)

    if not md5_clean:
        print("\n❌ REFACTORED version FAILED to run")
        return 1

    print(f"\nRefactored MD5 hashes:")
    print(f"  clean.srt:        {md5_clean}")
    print(f"  with_speakers.srt: {md5_speakers}")

    # Compare
    print("\n" + "="*60)
    print("VERIFICATION RESULTS")
    print("="*60)

    clean_match = (md5_clean == BASELINE_MD5_CLEAN)
    speakers_match = (md5_speakers == BASELINE_MD5_SPEAKERS)

    print(f"clean.srt:        {'✅ IDENTICAL' if clean_match else '❌ DIFFERENT'}")
    print(f"with_speakers.srt: {'✅ IDENTICAL' if speakers_match else '❌ DIFFERENT'}")

    if clean_match and speakers_match:
        print("\n🎉 SUCCESS! Refactored code produces identical output!")
        return 0
    else:
        print("\n❌ FAIL! Output differs from baseline")
        return 1

if __name__ == "__main__":
    sys.exit(main())
