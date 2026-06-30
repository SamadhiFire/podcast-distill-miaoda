import re
NUMBER_RE = re.compile(r"(?<![A-Za-z])\$?\d[\d,]*(?:\.\d+)?%?")
text = "2023年3月8日（March 8）是SVB危机的关键trigger日"
print(NUMBER_RE.findall(text))
text2 = "2023年3月8日是"
print(NUMBER_RE.findall(text2))
text3 = "March 8 2023"
print(NUMBER_RE.findall(text3))
