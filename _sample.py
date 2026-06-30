import json, os
base = r"d:/Users/AS/Desktop/podcast-distill"

# Read a completed example
with open(os.path.join(base, "pending_july.txt"), "r", encoding="utf-8") as f:
    pending = [l.strip() for l in f if l.strip()]

print(f"Pending count: {len(pending)}")
print(f"First 5 pending: {pending[:5]}")

# Try to find a completed july summary
jobs_dir = os.path.join(base, "backfill", "summary_jobs", "youtube")
items_dir = os.path.join(base, "backfill", "items", "youtube")
sample_done = None
for vid in os.listdir(jobs_dir):
    req_path = os.path.join(jobs_dir, vid, "request.json")
    if not os.path.exists(req_path):
        continue
    with open(req_path, "r", encoding="utf-8") as f:
        req = json.load(f)
    if req.get("item", {}).get("report_date", "").startswith("2025-07"):
        sp = os.path.join(items_dir, vid, "summary.json")
        if os.path.exists(sp):
            sample_done = (vid, req, sp)
            break

if sample_done:
    vid, req, sp = sample_done
    print(f"\n=== Sample done: {vid} ===")
    print(f"Title: {req['item']['title']}")
    print(f"Source: {req['item']['source_name']}")
    with open(sp, "r", encoding="utf-8") as f:
        summ = json.load(f)
    print(f"\nSummary keys: {list(summ.keys())}")
    print(f"\nDigest keys: {list(summ['digest'].keys())}")
    print(f"\nshort_title: {summ['digest'].get('short_title')}")
    print(f"one_liner: {summ['digest'].get('one_liner')}")
    print(f"importance_score: {summ['digest'].get('importance_score')}")
    print(f"content_density: {summ['digest'].get('content_density')}")
    print(f"quality: {summ['digest'].get('quality')}")
    print(f"\ncore_points: {json.dumps(summ['digest'].get('core_points'), ensure_ascii=False, indent=2)[:500]}")
