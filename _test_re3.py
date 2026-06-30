import re
NUMBER_RE = re.compile(r"(?<![A-Za-z])\$?\d[\d,]*(?:\.\d+)?%?")
text = "March 8 2023"
print('matches:', NUMBER_RE.findall(text))
text2 = "2023年3月8日是SVB危机的关键trigger日"
print('matches2:', NUMBER_RE.findall(text2))
text3 = "2023年3月8日是"
print('matches3:', NUMBER_RE.findall(text3))
