"""Process all pending November 2025 YouTube summaries."""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"d:\Users\AS\Desktop\podcast-distill")
JOBS_DIR = ROOT / "backfill" / "summary_jobs" / "youtube"
ITEMS_DIR = ROOT / "backfill" / "items" / "youtube"
VALIDATE_SCRIPT = ROOT / "scripts" / "backfill" / "validate_summary_outputs.py"
PROGRESS_FILE = ROOT / "backfill" / "nov2025_progress.json"

BATCH_SIZE = 3  # per user instruction


def get_pending_ids():
    """Get all November 2025 video IDs that don't have summary.json yet."""
    pending = []
    for d in sorted(os.listdir(JOBS_DIR)):
        rj = JOBS_DIR / d / "request.json"
        if rj.is_file():
            with open(rj, "r", encoding="utf-8") as f:
                data = json.load(f)
            item = data.get("item", {})
            date = item.get("report_date", "")
            if date.startswith("2025-11"):
                summary_path = ITEMS_DIR / d / "summary.json"
                if not summary_path.is_file():
                    pending.append(d)
    return pending


def load_progress():
    if PROGRESS_FILE.is_file():
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed": [], "failed": [], "batches_done": 0}


def save_progress(progress):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def process_item(video_id):
    """Read request.json + transcript.txt, generate summary.json."""
    job_dir = JOBS_DIR / video_id
    item_dir = ITEMS_DIR / video_id
    
    # Read request.json
    with open(job_dir / "request.json", "r", encoding="utf-8") as f:
        request = json.load(f)
    
    item = request["item"]
    transcript_info = request["transcript"]
    
    # Read transcript
    transcript_path = item_dir / "transcript.txt"
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = f.read()
    
    # Build the summary JSON
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    
    summary = {
        "schema_version": 1,
        "item_id": item["item_id"],
        "platform": item["platform"],
        "platform_id": item["platform_id"],
        "source_id": item["source_id"],
        "source_name": item["source_name"],
        "category": item["category"],
        "title": item["title"],
        "url": item["url"],
        "published_at": item["published_at"],
        "report_date": item["report_date"],
        "duration_seconds": item["duration_seconds"],
        "transcript_sha256": transcript_info["sha256"],
        "transcript_text_chars": transcript_info["text_chars"],
        "extraction": {
            "method": transcript_info.get("extraction_method", "yt-dlp"),
            "language": transcript_info.get("language", item.get("language", "en")),
            "coverage_ratio": transcript_info.get("coverage_ratio", 0),
            "text_chars": transcript_info.get("text_chars", 0),
            "completed_at": transcript_info.get("extraction_completed_at", "")
        },
        "generation": {
            "script": "trae_agent",
            "generated_at": now,
            "llm_configured": False,
            "model": "trae_agent",
            "base_url": "",
            "max_attempts": 1
        },
        "digest": None  # Will be filled by LLM
    }
    
    return summary, transcript, item


def validate_item(video_id):
    """Run validation for a single item."""
    result = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), "--platform", "youtube", "--item-id", f"youtube:{video_id}"],
        capture_output=True, text=True, cwd=str(ROOT)
    )
    return result.returncode == 0, result.stdout + result.stderr


if __name__ == "__main__":
    pending = get_pending_ids()
    progress = load_progress()
    
    # Filter out already completed (from progress file)
    pending = [v for v in pending if v not in progress["completed"]]
    
    print(f"Total pending: {len(pending)}")
    print(f"Already completed (progress): {len(progress['completed'])}")
    print(f"Failed: {len(progress['failed'])}")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        print("\nPending IDs (first 10):")
        for vid in pending[:10]:
            print(f"  {vid}")
        sys.exit(0)
