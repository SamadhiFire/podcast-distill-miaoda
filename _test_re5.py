import re
NUMBER_RE = re.compile(r"(?<![A-Za-z])\$?\d[\d,]*(?:\.\d+)?%?")
text = "March 8 2023 2023年3月8日是SVB危机的关键trigger日，SVB和Silvergate Bank同日发布公告"
print('matches:', NUMBER_RE.findall(text))
