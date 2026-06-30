import json, os
base = r"d:/Users/AS/Desktop/podcast-distill"

with open(os.path.join(base, "pending_july.txt"), "r", encoding="utf-8") as f:
    pending = [l.strip() for l in f if l.strip()]

# Fix items 7-9 (index 6-8)
for vid in pending[6:9]:
    req_path = os.path.join(base, "backfill", "summary_jobs", "youtube", vid, "request.json")
    summ_path = os.path.join(base, "backfill", "items", "youtube", vid, "summary.json")
    if not os.path.exists(summ_path):
        continue
    with open(req_path, "r", encoding="utf-8") as f:
        req = json.load(f)
    with open(summ_path, "r", encoding="utf-8") as f:
        summ = json.load(f)
    real_sha = req["transcript"]["sha256"]
    real_text_chars = req["transcript"]["text_chars"]
    summ["transcript_sha256"] = real_sha
    summ["transcript_text_chars"] = real_text_chars
    with open(summ_path, "w", encoding="utf-8") as f:
        json.dump(summ, f, ensure_ascii=False, indent=2)
    print(f"Fixed {vid}: chars={real_text_chars}")
