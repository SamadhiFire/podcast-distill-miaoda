import re

NUMBER_RE = re.compile(r'(?<![A-Za-z])\$?\d[\d,]*(?:\.\d+)?%?')

files = {
    'BRcVDhOkij4': 'backfill/items/youtube/BRcVDhOkij4/transcript.txt',
    'E0Q96IKXx6Q': 'backfill/items/youtube/E0Q96IKXx6Q/transcript.txt',
    'IZ17lGAUAbE': 'backfill/items/youtube/IZ17lGAUAbE/transcript.txt',
}

for vid, path in files.items():
    with open(path, encoding='utf-8') as f:
        t = f.read()
    nums = set()
    for raw in NUMBER_RE.findall(t):
        n = raw.replace(',', '').lstrip('$')
        if n:
            nums.add(n)
    print(f'=== {vid} ===')
    for check in ['10000', '1000', '100', '8', '80', '25', '250', '350', '75', '70', '30', '6', '5']:
        print(f'  has {check}: {check in nums}')
    sorted_nums = sorted(nums, key=lambda x: (len(x), x))
    print(f'  all numbers ({len(nums)}): {sorted_nums}')
    print()
