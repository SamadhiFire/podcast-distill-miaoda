import re
from pathlib import Path

NUMBER_RE = re.compile(r"(?<![A-Za-z])\$?\d[\d,]*(?:\.\d+)?%?")

t = Path("backfill/items/youtube/tEH9qXxNCto/transcript.txt").read_text(encoding="utf-8", errors="replace")

# Find context around "$12.8"
idx = t.find("$12.8")
if idx >= 0:
    snippet = t[max(0,idx-30):idx+30]
    print(f"Found '$12.8' at pos {idx}")
    print(f"Snippet: {snippet!r}")
    print(f"Snippet bytes: {snippet.encode('utf-8')!r}")
    # Check what NUMBER_RE finds in this snippet
    matches = NUMBER_RE.findall(snippet)
    print(f"Regex matches in snippet: {matches}")
    for m in matches:
        normalized = m.replace(",", "").lstrip("$")
        print(f"  {m!r} -> {normalized!r}")
else:
    print("'$12.8' NOT found in transcript")
    # Search for "12.8" without $
    idx2 = t.find("12.8")
    if idx2 >= 0:
        snippet = t[max(0,idx2-30):idx2+30]
        print(f"Found '12.8' at pos {idx2}")
        print(f"Snippet: {snippet!r}")
        print(f"Snippet bytes: {snippet.encode('utf-8')!r}")
        matches = NUMBER_RE.findall(snippet)
        print(f"Regex matches: {matches}")
    else:
        print("'12.8' also NOT found")
        # Search for "12" near "billion"
        for m in re.finditer(r"12\.\d", t):
            print(f"Found 12.X at pos {m.start()}: {t[m.start()-10:m.end()+10]!r}")

# Also check for 50.4 in the second transcript
print("\n=== 2lJdRmBGHGE ===")
t2 = Path("backfill/items/youtube/2lJdRmBGHGE/transcript.txt").read_text(encoding="utf-8", errors="replace")
idx3 = t2.find("50.4")
if idx3 >= 0:
    snippet = t2[max(0,idx3-30):idx3+30]
    print(f"Found '50.4' at pos {idx3}")
    print(f"Snippet: {snippet!r}")
    matches = NUMBER_RE.findall(snippet)
    print(f"Regex matches: {matches}")
    for m in matches:
        normalized = m.replace(",", "").lstrip("$")
        print(f"  {m!r} -> {normalized!r}")
else:
    print("'50.4' NOT found")
    for m in re.finditer(r"50\.\d", t2):
        print(f"Found 50.X: {t2[m.start()-10:m.end()+10]!r}")

# Also check 1400 in first transcript
print("\n=== tEH9qXxNCto - 1400 ===")
idx4 = t.find("1,400")
if idx4 >= 0:
    snippet = t[max(0,idx4-20):idx4+20]
    print(f"Found '1,400' at pos {idx4}: {snippet!r}")
    matches = NUMBER_RE.findall(snippet)
    print(f"Regex matches: {matches}")
    for m in matches:
        normalized = m.replace(",", "").lstrip("$")
        print(f"  {m!r} -> {normalized!r}")
else:
    print("'1,400' NOT found")
    idx5 = t.find("1400")
    if idx5 >= 0:
        print(f"Found '1400' at pos {idx5}")
    else:
        print("'1400' also NOT found")
