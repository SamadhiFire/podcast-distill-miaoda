import json, os

base = r"d:/Users/AS/Desktop/podcast-distill"
jobs_dir = os.path.join(base, "backfill", "summary_jobs", "youtube")
items_dir = os.path.join(base, "backfill", "items", "youtube")

all_vids = [d for d in os.listdir(jobs_dir) if os.path.isdir(os.path.join(jobs_dir, d))]
print(f"Total video_ids in summary_jobs: {len(all_vids)}")

july_items = []
completed = []
pending = []

for vid in all_vids:
    req_path = os.path.join(jobs_dir, vid, "request.json")
    if not os.path.exists(req_path):
        continue
    try:
        with open(req_path, "r", encoding="utf-8") as f:
            req = json.load(f)
    except:
        continue
    rd = req.get("report_date", "")
    if not rd.startswith("2025-07"):
        continue
    july_items.append(vid)
    summary_path = os.path.join(items_dir, vid, "summary.json")
    if os.path.exists(summary_path):
        completed.append(vid)
    else:
        pending.append(vid)

print(f"\n=== 2025-07 Status ===")
print(f"Total July items: {len(july_items)}")
print(f"Completed: {len(completed)}")
print(f"Pending: {len(pending)}")

with open(os.path.join(base, "pending_july.txt"), "w", encoding="utf-8") as f:
    for vid in pending:
        f.write(vid + "\n")
print(f"\nPending list saved. First 10:")
for v in pending[:10]:
    print(f"  {v}")
