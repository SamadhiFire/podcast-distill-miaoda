import re
from pathlib import Path

NUMBER_RE = re.compile(r"(?<![A-Za-z])\$?\d[\d,]*(?:\.\d+)?%?")

def numbers(text):
    found = set()
    for raw in NUMBER_RE.findall(text or ""):
        normalized = raw.replace(",", "").lstrip("$")
        if normalized:
            found.add(normalized)
    return found

# Check all transcript numbers for key numbers we need
for vid in ["tEH9qXxNCto", "2lJdRmBGHGE", "33UBffKatgg"]:
    t = Path(f"backfill/items/youtube/{vid}/transcript.txt").read_text(encoding="utf-8", errors="replace")
    tn = numbers(t)
    print(f"=== {vid} ===")
    # Check specific numbers we need
    for n in ["140", "100", "1400", "200", "850", "122", "50", "80", "90", "2500", "5000", "12.8", "50.4", "50.8", "170000", "170,000", "126", "4500", "115", "60", "15", "40"]:
        print(f"  {n}: {n in tn}")
    # Search for context around "billion loss" and "Vanke"
    for phrase in ["billion loss", "Vanke", "12.8", "record loss"]:
        idx = t.lower().find(phrase.lower())
        if idx >= 0:
            print(f"  Found '{phrase}' at pos {idx}: ...{t[max(0,idx-20):idx+40]}...")
    print()
