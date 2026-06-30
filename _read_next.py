import json, os, sys
base = r"d:/Users/AS/Desktop/podcast-distill"

with open(os.path.join(base, "pending_july.txt"), "r", encoding="utf-8") as f:
    pending = [l.strip() for l in f if l.strip()]

start = int(sys.argv[1])
end = int(sys.argv[2]) if len(sys.argv) > 2 else start + 1
for idx in range(start, min(end, len(pending))):
    vid = pending[idx]
    req_path = os.path.join(base, "backfill", "summary_jobs", "youtube", vid, "request.json")
    trans_path = os.path.join(base, "backfill", "items", "youtube", vid, "transcript.txt")
    with open(req_path, "r", encoding="utf-8") as f:
        req = json.load(f)
    try:
        with open(trans_path, "r", encoding="utf-8") as f:
            trans = f.read()
    except:
        trans = "(missing)"
    item = req["item"]
    print(f"\n{'='*80}")
    print(f"### {idx+1}. {vid} | dur={item.get('duration_seconds',0)}s")
    print(f"Title: {item['title']}")
    print(f"Source: {item.get('source_name','')} | Date: {item.get('report_date','')}")
    print(f"--- TRANSCRIPT ({len(trans)} chars) ---")
    print(trans)
