import re, json
from pathlib import Path

NUMBER_RE = re.compile(r"(?<![A-Za-z])\$?\d[\d,]*(?:\.\d+)?%?")

def numbers(text):
    found = set()
    for raw in NUMBER_RE.findall(text or ""):
        normalized = raw.replace(",", "").lstrip("$")
        if normalized:
            found.add(normalized)
    return found

for vid in ["tEH9qXxNCto", "2lJdRmBGHGE"]:
    t = Path(f"backfill/items/youtube/{vid}/transcript.txt").read_text(encoding="utf-8", errors="replace")
    s = Path(f"backfill/items/youtube/{vid}/summary.json").read_text(encoding="utf-8")
    summary = json.loads(s)
    tn = numbers(t)
    print(f"=== {vid} ===")
    print(f'  "12.8" in transcript: {"12.8" in tn}')
    print(f'  "50.4" in transcript: {"50.4" in tn}')
    # Find what numbers close to 12.8 and 50.4 are in transcript
    close_12 = [n for n in tn if "12" in n]
    close_50 = [n for n in tn if "50" in n]
    print(f'  numbers containing "12": {sorted(close_12)[:10]}')
    print(f'  numbers containing "50": {sorted(close_50)[:10]}')
    for idx, fact in enumerate(summary["digest"]["key_facts"], 1):
        val = fact.get("value", "")
        ctx = fact.get("context", "")
        fact_nums = numbers(f"{val} {ctx}")
        missing = fact_nums - tn
        if missing:
            print(f"  fact {idx}: MISSING {sorted(missing)}")
            print(f"    value={val!r}, context={ctx!r}")
            print(f"    fact_nums={sorted(fact_nums)}")
