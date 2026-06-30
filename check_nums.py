import re

NUMBER_RE = re.compile(r'(?<![A-Za-z])\$?\d[\d,]*(?:\.\d+)?%?')
t = open('d:/Users/AS/Desktop/podcast-distill/backfill/items/youtube/-Epp6VmpezI/transcript.txt', encoding='utf-8').read()
nums = set()
for raw in NUMBER_RE.findall(t):
    n = raw.replace(',', '').lstrip('$')
    if n:
        nums.add(n)

checks = ['16', '70%', '70', '1.4', '3', '5', '10', '100', '50', '5000']
for c in checks:
    print(f'{c}: {c in nums}')

# Find "sixteen" or "16" context
for m in re.finditer(r'sixteen|\b16\b', t, re.I):
    ctx = t[max(0, m.start()-40):m.end()+40]
    print(f'16 ctx: {repr(ctx)}')

# Find "70" context
for m in re.finditer(r'70|seventy', t, re.I):
    ctx = t[max(0, m.start()-40):m.end()+40]
    print(f'70 ctx: {repr(ctx)}')

# Find "five" or "5" context
for m in re.finditer(r'\bfive\b|\b5\b', t, re.I):
    ctx = t[max(0, m.start()-40):m.end()+40]
    print(f'5 ctx: {repr(ctx)}')

# Find "10" context
for m in re.finditer(r'\b10\b|\bten\b', t, re.I):
    ctx = t[max(0, m.start()-40):m.end()+40]
    print(f'10 ctx: {repr(ctx)}')
