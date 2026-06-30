import json, os
base = r"d:/Users/AS/Desktop/podcast-distill"

with open(os.path.join(base, "pending_july.txt"), "r", encoding="utf-8") as f:
    pending = [l.strip() for l in f if l.strip()]

# Get metadata for all pending
out = []
for vid in pending:
    req_path = os.path.join(base, "backfill", "summary_jobs", "youtube", vid, "request.json")
    trans_path = os.path.join(base, "backfill", "items", "youtube", vid, "transcript.txt")
    with open(req_path, "r", encoding="utf-8") as f:
        req = json.load(f)
    try:
        with open(trans_path, "r", encoding="utf-8") as f:
            trans = f.read()
    except:
        trans = ""
    item = req["item"]
    out.append({
        "video_id": vid,
        "title": item["title"],
        "source_name": item.get("source_name", ""),
        "source_id": item.get("source_id", ""),
        "category": item.get("category", ""),
        "url": item.get("url", ""),
        "report_date": item.get("report_date", ""),
        "duration_seconds": item.get("duration_seconds", 0),
        "language": item.get("language", "en"),
        "transcript_sha256": req.get("transcript", {}).get("sha256", ""),
        "transcript_text_chars": req.get("transcript", {}).get("text_chars", 0),
        "transcript_path": f"backfill/items/youtube/{vid}/transcript.txt",
        "extraction": req.get("transcript", {}),
    })

with open(os.path.join(base, "_july_meta.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(f"Saved metadata for {len(out)} items")
print(f"\nDuration distribution:")
durs = [x["duration_seconds"] for x in out]
print(f"  < 1800s (brief, need 2 summary): {sum(1 for d in durs if d < 1800)}")
print(f"  1800-3600s (standard, need 3): {sum(1 for d in durs if 1800 <= d < 3600)}")
print(f"  >= 3600s (high, need 4): {sum(1 for d in durs if d >= 3600)}")

# Group by source
from collections import Counter
sources = Counter(x["source_name"] for x in out)
print(f"\nSource distribution:")
for s, c in sources.most_common():
    print(f"  {s}: {c}")
