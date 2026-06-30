import json, os, sys
base = r"d:/Users/AS/Desktop/podcast-distill"

with open(os.path.join(base, "pending_july.txt"), "r", encoding="utf-8") as f:
    pending = [l.strip() for l in f if l.strip()]

idx = int(sys.argv[1])
vid = pending[idx]
print(f"### Item {idx+1}: {vid}")
req_path = os.path.join(base, "backfill", "summary_jobs", "youtube", vid, "request.json")
trans_path = os.path.join(base, "backfill", "items", "youtube", vid, "transcript.txt")
with open(req_path, "r", encoding="utf-8") as f:
    req = json.load(f)
with open(trans_path, "r", encoding="utf-8") as f:
    trans = f.read()
item = req["item"]
print(f"Title: {item['title']}")
print(f"Source: {item.get('source_name','')}")
print(f"Date: {item.get('report_date','')}")
print(f"Duration: {item.get('duration_seconds',0)}s")
print(f"\n--- TRANSCRIPT ({len(trans)} chars) ---")
print(trans)
