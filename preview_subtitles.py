import argparse
import re
from datetime import datetime, timedelta

def parse_srt_time(time_str):
    """Converts an SRT time string (HH:MM:SS,ms) to a timedelta object."""
    try:
        parts = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})', time_str)
        return timedelta(hours=int(parts.group(1)), minutes=int(parts.group(2)), seconds=int(parts.group(3)), milliseconds=int(parts.group(4)))
    except AttributeError:
        # Handle cases where the time format might be slightly different or invalid
        print(f"Warning: Could not parse time: {time_str}")
        return None

def main():
    """
    Parses and displays SRT subtitle files in a columnar format with an optional start time filter.
    """
    parser = argparse.ArgumentParser(description='List subtitle entries from an SRT file, with an optional start time filter.')
    parser.add_argument('filepath', help='The path to the .srt file.')
    parser.add_argument('--time', help='Optional start time filter in HH:MM:SS format. Defaults to 00:00:00.', default='00:00:00', nargs='?')
    args = parser.parse_args()

    try:
        filter_time_obj = datetime.strptime(args.time, '%H:%M:%S').time()
        filter_timedelta = timedelta(hours=filter_time_obj.hour, minutes=filter_time_obj.minute, seconds=filter_time_obj.second)
    except ValueError:
        print("Error: Invalid --time format. Please use HH:MM:SS.")
        return

    try:
        with open(args.filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {args.filepath}")
        return
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        return

    # Regex to find all subtitle blocks. This is more robust for parsing.
    subtitle_pattern = re.compile(r'\d+\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\n|\Z)', re.DOTALL | re.MULTILINE)
    matches = subtitle_pattern.findall(content)

    TEXT_WIDTH = 80
    print(f"{'Start Time':<15}{'Text':<{TEXT_WIDTH}}{'End Time'}")
    print(f"{'-'*14:<15}{'-'*(TEXT_WIDTH-1):<{TEXT_WIDTH}}{'-'*14}")

    for start_time_str, end_time_str, text in matches:
        text = text.replace('\n', ' ').strip()
        start_timedelta = parse_srt_time(start_time_str)

        if start_timedelta is None:
            continue

        if start_timedelta >= filter_timedelta:
            # Truncate text if it's longer than the column width to maintain alignment
            display_text = (text[:TEXT_WIDTH-3] + '...') if len(text) > TEXT_WIDTH else text
            print(f"{start_time_str:<15}{display_text:<{TEXT_WIDTH}}{end_time_str}")

if __name__ == '__main__':
    main()
