"""Test a quote candidate against transcript - reports if verbatim matches and length"""
import sys, os
sys.path.insert(0, os.getcwd())
from scripts.backfill.validate_summary_outputs import compact_for_match

vid = sys.argv[1]
with open(f'backfill/items/youtube/{vid}/transcript.txt','r',encoding='utf-8') as f:
    text = f.read()
ct = compact_for_match(text)

# Quotes to try
candidates = []
i = 2
while i < len(sys.argv):
    candidates.append(sys.argv[i])
    i += 1

for c in candidates:
    cc = compact_for_match(c)
    nw = sum(1 for ch in c if not ch.isspace())
    in_trans = cc in ct
    print(f'{nw} ns | in={in_trans} | {c[:60]}')
