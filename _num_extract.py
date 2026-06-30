"""Extract numbers from transcript for a video_id"""
import re, sys, os

vid = sys.argv[1]
tp = f'backfill/items/youtube/{vid}/transcript.txt'
if not os.path.exists(tp):
    print(f'No transcript for {vid}')
    sys.exit(1)
with open(tp, 'r', encoding='utf-8') as f:
    text = f.read()

# Strip boilerplate
text = re.sub(r'Kind:\s*captions', '', text, flags=re.I)
text = re.sub(r'Language:\s*[a-z-]+', '', text, flags=re.I)
text = re.sub(r'\[music\]', '', text, flags=re.I)
text = re.sub(r'\[&nbsp;__&nbsp;\]', '', text)
text = re.sub(r'\[.*?\]', '', text)
text = re.sub(r'\n\s*\n+', '\n', text)
text = re.sub(r'^\s+', '', text, flags=re.M)

# Numbers via the same regex as the validator (negative lookbehind for letter)
nums = re.findall(r'(?<![A-Za-z])\$?\d[\d,]*(?:\.\d+)?%?', text)
unique = sorted(set(n.replace(',', '').lstrip('$') for n in nums if n))
print('Unique numbers in transcript:')
for n in unique:
    print(f'  {n}')
print(f'\nTotal unique: {len(unique)}')

# Also show text length
print(f'\nCleaned text length: {len(text)}')
print(f'Original text length: {len(open(tp, encoding="utf-8").read())}')

# Show 100 chars of cleaned text
print('\n--- CLEANED TEXT PREVIEW (first 3000 chars) ---')
print(text[:3000])
