#!/usr/bin/env python3
"""Create a sample corrected JSON for demonstration"""

import json
import copy

# Load original
with open('D:/stevner/2025/regionalt/Lørdag/04-LørdagEttermiddag/04-LørdagEttermiddag.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Make a deep copy
corrected = copy.deepcopy(data)

# Fix the first sentence's last word
# "søstre." goes from 2.314-5.238 (2.924s) to 2.314-2.514 (0.2s)
first_seg = corrected['segments'][0]
last_word = first_seg['words'][-1]

print(f'Original last word: {last_word["word"]}')
print(f'  Start: {last_word["start"]:.3f}s')
print(f'  End: {last_word["end"]:.3f}s')
print(f'  Duration: {last_word["end"] - last_word["start"]:.3f}s')

# Apply correction (based on MFCC showing speech ends at ~2.5s)
last_word['end'] = 2.514

print(f'\nCorrected last word: {last_word["word"]}')
print(f'  Start: {last_word["start"]:.3f}s')
print(f'  End: {last_word["end"]:.3f}s')
print(f'  Duration: {last_word["end"] - last_word["start"]:.3f}s')
print(f'  Reduction: {2.924 - (last_word["end"] - last_word["start"]):.3f}s')

# Save
output_path = '04-LordagEttermiddag_corrected_demo.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(corrected, f, indent=2, ensure_ascii=False)

print(f'\n✓ Saved corrected JSON: {output_path}')
