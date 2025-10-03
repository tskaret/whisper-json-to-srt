import argparse
import json
from datetime import datetime, timedelta

def format_seconds(sec):
    """Converts seconds (float) to HH:MM:SS,ms string format."""
    if sec is None:
        return "N/A"
    td = timedelta(seconds=sec)
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = td.microseconds // 1000
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

def main():
    parser = argparse.ArgumentParser(description='List word-level subtitles from a WhisperX JSON file.')
    parser.add_argument('filepath', help='The path to the .json file.')
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
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at {args.filepath}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {args.filepath}")
        return

    all_words = []
    if 'segments' in data and isinstance(data['segments'], list):
        for segment in data['segments']:
            if 'words' in segment and isinstance(segment['words'], list):
                all_words.extend(segment['words'])

    WORD_WIDTH = 25
    print(f"{'Start Time':<15}{'Word':<{WORD_WIDTH}}{'End Time':<15}{'Gap to Next (ms)'}")
    print(f"{'-'*14:<15}{'-'*(WORD_WIDTH-1):<{WORD_WIDTH}}{'-'*14:<15}{'-'*20}")

    for i, word_info in enumerate(all_words):
        if all(k in word_info for k in ['start', 'end', 'word']):
            start_sec = word_info['start']
            start_timedelta = timedelta(seconds=start_sec)

            if start_timedelta >= filter_timedelta:
                start_str = format_seconds(start_sec)
                end_str = format_seconds(word_info['end'])
                word = word_info['word']

                gap_ms = "N/A"
                if i + 1 < len(all_words):
                    next_word_info = all_words[i+1]
                    if 'start' in next_word_info:
                        gap_sec = next_word_info['start'] - word_info['end']
                        gap_ms = int(gap_sec * 1000)

                print(f"{start_str:<15}{word:<{WORD_WIDTH}}{end_str:<15}{gap_ms}")

if __name__ == '__main__':
    main()