import re
NUMBER_RE = re.compile(r"(?<![A-Za-z])\$?\d[\d,]*(?:\.\d+)?%?")
texts = [
  'functionally a dead fish',
  'CFPB目前functionally是dead fish',
  'currently is dead fish',
  'Chopra认为CFPB目前functionally是dead fish',
  '对资产超过10 billion的银行',
]
for t in texts:
    print(repr(t), '->', NUMBER_RE.findall(t))
