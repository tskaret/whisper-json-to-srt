#!/usr/bin/env python3
"""
Comprehensive Subtitle Validation Tool
=====================================

Finds and reports specific issues with subtitle files:
1. Overlapping subtitles
2. Double hyphen problems
3. Timing issues
4. Text flow problems
"""

import sys
import re
from typing import List, Dict, Any


def parse_srt_time(time_str: str) -> float:
    """Parse SRT time format to seconds"""
    time_part, ms_part = time_str.split(',')
    h, m, s = map(int, time_part.split(':'))
    ms = int(ms_part)
    return h * 3600 + m * 60 + s + ms / 1000.0


def format_time(seconds: float) -> str:
    """Format time as HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def parse_srt_file(file_path: str) -> List[Dict]:
    """Parse SRT file into structured data"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    subtitles = []
    blocks = content.strip().split('\n\n')

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            try:
                number = int(lines[0])
                timing_line = lines[1]
                start_str, end_str = timing_line.split(' --> ')
                start_time = parse_srt_time(start_str)
                end_time = parse_srt_time(end_str)
                text_lines = lines[2:]

                subtitles.append({
                    'number': number,
                    'start': start_time,
                    'end': end_time,
                    'duration': end_time - start_time,
                    'timing_line': timing_line,
                    'text_lines': text_lines,
                    'full_text': '\n'.join(text_lines)
                })
            except (ValueError, IndexError) as e:
                print(f"⚠️  Warning: Could not parse subtitle block: {e}")
                continue

    return subtitles


def find_overlapping_subtitles(subtitles: List[Dict]) -> List[Dict]:
    """Find overlapping subtitles"""
    overlaps = []

    for i in range(len(subtitles) - 1):
        current = subtitles[i]
        next_sub = subtitles[i + 1]

        if current['end'] > next_sub['start']:
            overlap_duration = current['end'] - next_sub['start']
            overlaps.append({
                'current_number': current['number'],
                'next_number': next_sub['number'],
                'current_end': current['end'],
                'next_start': next_sub['start'],
                'overlap_duration': overlap_duration,
                'current_timing': current['timing_line'],
                'next_timing': next_sub['timing_line'],
                'current_text': current['full_text'][:50] + "..." if len(current['full_text']) > 50 else current['full_text'],
                'next_text': next_sub['full_text'][:50] + "..." if len(next_sub['full_text']) > 50 else next_sub['full_text']
            })

    return overlaps


def find_double_hyphen_issues(subtitles: List[Dict]) -> List[Dict]:
    """Find double hyphen issues (both lines have hyphens)"""
    issues = []

    for sub in subtitles:
        text_lines = sub['text_lines']

        if len(text_lines) == 2:
            line1 = text_lines[0].strip()
            line2 = text_lines[1].strip()

            # Case 1: First line ends with " -" AND second line starts with "- "
            if line1.endswith(' -') and line2.startswith('- '):
                issues.append({
                    'type': 'double_continuation_hyphen',
                    'subtitle_number': sub['number'],
                    'timing': sub['timing_line'],
                    'line1': line1,
                    'line2': line2,
                    'description': 'Both lines have continuation hyphens (wrong!)'
                })

            # Case 2: Both lines end with " -"
            elif line1.endswith(' -') and line2.endswith(' -'):
                issues.append({
                    'type': 'both_lines_end_with_hyphen',
                    'subtitle_number': sub['number'],
                    'timing': sub['timing_line'],
                    'line1': line1,
                    'line2': line2,
                    'description': 'Both lines end with hyphens (wrong!)'
                })

            # Case 3: Second line starts and ends with hyphens
            elif line2.startswith('- ') and line2.endswith(' -'):
                issues.append({
                    'type': 'line2_double_hyphen',
                    'subtitle_number': sub['number'],
                    'timing': sub['timing_line'],
                    'line1': line1,
                    'line2': line2,
                    'description': 'Second line starts AND ends with hyphens (wrong!)'
                })

    return issues


def find_timing_issues(subtitles: List[Dict]) -> List[Dict]:
    """Find various timing issues"""
    issues = []

    for sub in subtitles:
        # Very short subtitles (less than 0.3 seconds) - only flag extremely short ones
        if sub['duration'] < 0.3:
            issues.append({
                'type': 'too_short',
                'subtitle_number': sub['number'],
                'duration': sub['duration'],
                'timing': sub['timing_line'],
                'text': sub['full_text'],
                'description': f'Subtitle too short ({sub["duration"]:.3f}s)'
            })

        # Very long subtitles (more than 20 seconds) - more lenient for this content type
        if sub['duration'] > 20.0:
            issues.append({
                'type': 'too_long',
                'subtitle_number': sub['number'],
                'duration': sub['duration'],
                'timing': sub['timing_line'],
                'text': sub['full_text'][:50] + "..." if len(sub['full_text']) > 50 else sub['full_text'],
                'description': f'Subtitle very long ({sub["duration"]:.1f}s)'
            })

        # Negative duration
        if sub['duration'] <= 0:
            issues.append({
                'type': 'negative_duration',
                'subtitle_number': sub['number'],
                'duration': sub['duration'],
                'timing': sub['timing_line'],
                'text': sub['full_text'],
                'description': f'Negative or zero duration ({sub["duration"]:.3f}s)'
            })

    return issues


def find_text_flow_issues(subtitles: List[Dict]) -> List[Dict]:
    """Find text flow and formatting issues"""
    issues = []

    for sub in subtitles:
        text_lines = sub['text_lines']

        # Check for orphaned continuation hyphens
        for i, line in enumerate(text_lines):
            line = line.strip()

            # Line starts with "- " but there's no previous continuation
            if line.startswith('- ') and i == 0:
                # Check if previous subtitle ends with continuation
                prev_sub = None
                for prev in subtitles:
                    if prev['number'] == sub['number'] - 1:
                        prev_sub = prev
                        break

                if not prev_sub or not prev_sub['text_lines'][-1].strip().endswith(' -'):
                    issues.append({
                        'type': 'orphaned_start_hyphen',
                        'subtitle_number': sub['number'],
                        'line_number': i + 1,
                        'line': line,
                        'description': 'Line starts with "- " but no previous continuation'
                    })

        # NOTE: Removed missing continuation hyphen check within subtitles
        # According to new rules, hyphens only mark continuation BETWEEN subtitles,
        # not within the lines of a single subtitle. This check was causing false positives.

    return issues


def main():
    if len(sys.argv) != 2:
        print("Usage: python validate_subtitles.py <srt_file>")
        print("Example: python validate_subtitles.py final_subtitles/02-FredagEttermiddag_clean.srt")
        sys.exit(1)

    srt_file = sys.argv[1]

    print(f"🔍 COMPREHENSIVE SUBTITLE VALIDATION")
    print(f"{'='*60}")
    print(f"File: {srt_file}")
    print()

    # Parse subtitles
    subtitles = parse_srt_file(srt_file)
    print(f"📊 Loaded {len(subtitles)} subtitles")
    print()

    # 1. Check for overlapping subtitles
    print(f"⏱️  CHECKING FOR OVERLAPPING SUBTITLES...")
    overlaps = find_overlapping_subtitles(subtitles)

    if overlaps:
        print(f"❌ Found {len(overlaps)} overlapping subtitles:")
        for i, overlap in enumerate(overlaps[:5]):  # Show first 5
            print(f"  {i+1}. Subtitles #{overlap['current_number']} and #{overlap['next_number']}")
            print(f"     Current: {format_time(overlap['current_end'])} (ends)")
            print(f"     Next:    {format_time(overlap['next_start'])} (starts)")
            print(f"     Overlap: {overlap['overlap_duration']:.3f} seconds")
            print(f"     Current text: \"{overlap['current_text']}\"")
            print(f"     Next text:    \"{overlap['next_text']}\"")
            print()
    else:
        print("✅ No overlapping subtitles found")
    print()

    # 2. Check for double hyphen issues
    print(f"🔗 CHECKING FOR DOUBLE HYPHEN ISSUES...")
    hyphen_issues = find_double_hyphen_issues(subtitles)

    if hyphen_issues:
        print(f"❌ Found {len(hyphen_issues)} double hyphen issues:")
        for i, issue in enumerate(hyphen_issues[:5]):  # Show first 5
            print(f"  {i+1}. Subtitle #{issue['subtitle_number']} - {issue['description']}")
            print(f"     Timing: {issue['timing']}")
            print(f"     Line 1: \"{issue['line1']}\"")
            print(f"     Line 2: \"{issue['line2']}\"")
            print()
    else:
        print("✅ No double hyphen issues found")
    print()

    # 3. Check for timing issues
    print(f"⏲️  CHECKING FOR TIMING ISSUES...")
    timing_issues = find_timing_issues(subtitles)

    if timing_issues:
        print(f"❌ Found {len(timing_issues)} timing issues:")
        # Group by type
        timing_types = {}
        for issue in timing_issues:
            t = issue['type']
            if t not in timing_types:
                timing_types[t] = []
            timing_types[t].append(issue)

        for issue_type, issues in timing_types.items():
            print(f"  {issue_type.replace('_', ' ').title()}: {len(issues)} cases")
            for issue in issues[:5]:  # Show first 5 of each type with content
                print(f"    Subtitle #{issue['subtitle_number']}: {issue['description']}")
                print(f"       Content: \"{issue['text']}\"")
                print(f"       Timing: {issue['timing']}")
        print()
    else:
        print("✅ No timing issues found")
    print()

    # 4. Check for text flow issues
    print(f"📝 CHECKING FOR TEXT FLOW ISSUES...")
    text_issues = find_text_flow_issues(subtitles)

    if text_issues:
        print(f"❌ Found {len(text_issues)} text flow issues:")
        # Group by type
        text_types = {}
        for issue in text_issues:
            t = issue['type']
            if t not in text_types:
                text_types[t] = []
            text_types[t].append(issue)

        for issue_type, issues in text_types.items():
            print(f"  {issue_type.replace('_', ' ').title()}: {len(issues)} cases")
            for issue in issues[:3]:  # Show first 3 of each type
                if 'line1' in issue:
                    print(f"    Subtitle #{issue['subtitle_number']}: \"{issue['line1']}\" / \"{issue['line2']}\"")
                else:
                    print(f"    Subtitle #{issue['subtitle_number']}: {issue['description']}")
        print()
    else:
        print("✅ No text flow issues found")
    print()

    # Summary
    total_issues = len(overlaps) + len(hyphen_issues) + len(timing_issues) + len(text_issues)
    if total_issues == 0:
        print("🎉 ALL VALIDATIONS PASSED! Subtitle file looks good.")
    else:
        print(f"📊 SUMMARY: Found {total_issues} total issues")
        print(f"   - Overlapping subtitles: {len(overlaps)}")
        print(f"   - Double hyphen issues: {len(hyphen_issues)}")
        print(f"   - Timing issues: {len(timing_issues)}")
        print(f"   - Text flow issues: {len(text_issues)}")


if __name__ == "__main__":
    main()