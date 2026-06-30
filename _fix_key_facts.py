import json, os, re
base = r"d:/Users/AS/Desktop/podcast-distill"

# Issue 1: Item 1 - "99.99%" not in transcript. The transcript says "99.99%" or "99.9%" or "99%". Let me check
# Issue 2: Item 2 - "4" (from "4" in "red 3" was in original "red dye 3" - but here it says "4" was wrong). Let me check key_facts[5] for item 2

# First check
for vid in ["4g4PKzP4x98", "4IfT6ZBuGAI"]:
    req_path = os.path.join(base, "backfill", "summary_jobs", "youtube", vid, "request.json")
    summ_path = os.path.join(base, "backfill", "items", "youtube", vid, "summary.json")
    with open(req_path, "r", encoding="utf-8") as f:
        req = json.load(f)
    trans_path = os.path.join(base, "backfill", "items", "youtube", vid, "transcript.txt")
    with open(trans_path, "r", encoding="utf-8") as f:
        trans = f.read()
    with open(summ_path, "r", encoding="utf-8") as f:
        summ = json.load(f)
    print(f"\n=== {vid} ===")
    print(f"Title: {req['item']['title']}")
    for i, fact in enumerate(summ["digest"]["key_facts"]):
        val = fact.get("value", "")
        ctx = fact.get("context", "")
        # Check numbers
        num_re = re.compile(r"(?<![A-Za-z])\$?\d[\d,]*(?:\.\d+)?%?")
        trans_nums = set()
        for raw in num_re.findall(trans):
            trans_nums.add(raw.replace(",", "").lstrip("$"))
        val_ctx = f"{val} {ctx}"
        val_nums = set()
        for raw in num_re.findall(val_ctx):
            val_nums.add(raw.replace(",", "").lstrip("$"))
        missing = val_nums - trans_nums
        if missing:
            print(f"  Fact {i+1} MISSING: {missing} | val='{val}' ctx='{ctx[:80]}'")
