import json, os
base = r"d:/Users/AS/Desktop/podcast-distill"

with open(os.path.join(base, "pending_july.txt"), "r", encoding="utf-8") as f:
    pending = [l.strip() for l in f if l.strip()]

vid = pending[0]
print(f"=== Video: {vid} ===")
req_path = os.path.join(base, "backfill", "summary_jobs", "youtube", vid, "request.json")
with open(req_path, "r", encoding="utf-8") as f:
    req = json.load(f)
print(f"Title: {req['item']['title']}")
print(f"Source: {req['item']['source_name']}")
print(f"Date: {req['item']['report_date']}")
print(f"Duration: {req['item']['duration_seconds']}s")

trans_path = os.path.join(base, "backfill", "items", "youtube", vid, "transcript.txt")
with open(trans_path, "r", encoding="utf-8") as f:
    trans = f.read()
print(f"\nTranscript length: {len(trans)} chars")
print(f"\nFirst 2000 chars of transcript:/n{trans[:2000]}")
