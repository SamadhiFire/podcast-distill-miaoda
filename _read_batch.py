import json, os
base = r"d:/Users/AS/Desktop/podcast-distill"

with open(os.path.join(base, "pending_july.txt"), "r", encoding="utf-8") as f:
    pending = [l.strip() for l in f if l.strip()]

# Read first 3 items
for i, vid in enumerate(pending[:3]):
    req_path = os.path.join(base, "backfill", "summary_jobs", "youtube", vid, "request.json")
    trans_path = os.path.join(base, "backfill", "items", "youtube", vid, "transcript.txt")
    with open(req_path, "r", encoding="utf-8") as f:
        req = json.load(f)
    with open(trans_path, "r", encoding="utf-8") as f:
        trans = f.read()
    item = req["item"]
    print(f"\n{'='*80}")
    print(f"### Item {i+1}: {vid}")
    print(f"Title: {item['title']}")
    print(f"Source: {item.get('source_name','')}")
    print(f"Date: {item.get('report_date','')}")
    print(f"Duration: {item.get('duration_seconds',0)}s")
    print(f"\n--- FULL TRANSCRIPT ({len(trans)} chars) ---")
    print(trans)
    print(f"\n--- END TRANSCRIPT ---")
