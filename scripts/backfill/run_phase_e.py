"""
Phase E: YouTube-only Single-episode Summaries & Daily Views
=============================================================
- Deterministic extractive fallback (no external LLM API required).
- sha256-gated caching: summary.json only regenerated when transcript changes.
- Daily views grouped by report_date with platform_scope='youtube'.
- Blocked / skipped / no-transcript items tracked in manifest.
"""
import json, hashlib, os, re, sqlite3, sys, time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path("D:/Users/AS/Desktop/podcast-distill")
sys.path.insert(0, str(ROOT))

from scripts.backfill.db import get_conn
from scripts.report_contract import (
    build_report, normalize_digest, report_to_markdown,
    CATEGORIES, clean_text, chinese_spacing, fmt_time, fmt_duration,
)

ITEMS_DIR = ROOT / "backfill" / "items"
DAILY_DIR = ROOT / "backfill" / "daily"
STATE_DIR = ROOT / "backfill" / "state"

# ─── helpers ───────────────────────────────────────────────────

def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def clean_transcript(text: str) -> str:
    """Remove VTT headers and metadata lines from transcript."""
    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        # Skip VTT metadata
        if line in ("WEBVTT", "Kind: captions", "Kind: subtitles", "Language: en", "Language: zh"):
            continue
        if re.match(r"^\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->", line):
            continue
        if re.fullmatch(r"\d+", line):
            continue
        # Skip HTML-like tags
        line = re.sub(r"<[^>]+>", "", line)
        line = re.sub(r"\{[^}]*\}", "", line)
        if line:
            cleaned_lines.append(line)
    return " ".join(cleaned_lines)

def extract_sentences(text: str, limit: int = 10) -> list[str]:
    """Deterministic sentence extraction from transcript."""
    cleaned = clean_transcript(text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    parts = re.split(
        r"(?<=[。！？!?])\s+|(?<=[。！？!?])|(?<=[.!?])\s+(?=[A-Z0-9\u4e00-\u9fff])",
        cleaned,
    )
    sentences: list[str] = []
    seen: set[str] = set()
    for part in parts:
        sentence = part.strip(" -\t\r\n")
        if len(sentence) < 20 or sentence in seen:
            continue
        seen.add(sentence)
        sentences.append(sentence[:320])
        if len(sentences) >= limit:
            break
    return sentences

def short_title(item: dict[str, Any]) -> str:
    title = item.get("title") or "未命名内容"
    title = re.sub(r"\s+", " ", title).strip()
    return title[:60]

def extractive_digest(item: dict[str, Any], transcript: str) -> dict[str, Any]:
    """Deterministic extractive digest, no LLM required."""
    sentences = extract_sentences(transcript, limit=9)
    if len(sentences) < 3:
        compact_source = re.sub(r"\s+", " ", clean_transcript(transcript)).strip()
        for start in range(0, min(len(compact_source), 720), 180):
            fragment = compact_source[start: start + 180].strip()
            if len(fragment) >= 20 and fragment not in sentences:
                sentences.append(fragment)
            if len(sentences) >= 3:
                break
    fallback = sentences or ["已取得完整字幕，但规则模式未能提取可靠语义摘要。"]
    raw = {
        "short_title": short_title(item),
        "one_liner": fallback[0],
        "why_it_matters": fallback[1] if len(fallback) > 1 else fallback[0],
        "summary": fallback[1:3] or fallback[:1],
        "core_points": fallback[:3],
        "key_facts": [],
        "takeaways": [
            "先用30秒结论判断是否值得打开原节目。",
            "涉及数据或决策时回到原字幕核对上下文。",
        ],
        "guests": [],
        "topics": [item.get("category", "今日更新").split(" /")[0]],
        "quote": None,
        "importance_score": 3,
        "quality": "deterministic_fallback",
    }
    return normalize_digest(raw, item)

def build_item_for_report(item: dict[str, Any]) -> dict[str, Any]:
    """Map backfill item to report_contract format."""
    return {
        "url": item["url"],
        "original_title": item["title"],
        "title": item["title"],
        "source_name": item.get("source_name", item.get("source_id", "")),
        "platform": item["platform"],
        "published_at": item["published_at"],
        "duration": item["duration_seconds"],
        "category": item["category"] or "待分类",
    }

# ─── main ──────────────────────────────────────────────────────

def run_phase_e():
    print("=" * 60)
    print("  Phase E: YouTube-only Summaries & Daily Views")
    print("=" * 60)
    t0 = time.time()

    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ── 1. Load source names ──
    cur.execute("SELECT source_id, name FROM sources")
    source_names = {r["source_id"]: r["name"] for r in cur.fetchall()}

    # ── 2. Load all YouTube items ──
    cur.execute("""
        SELECT i.*, e.status as ext_status, e.sha256 as transcript_sha256,
               e.text_chars, e.coverage_ratio, e.method, e.error_type, e.error_message
        FROM items i
        LEFT JOIN extractions e ON i.item_id = e.item_id
        WHERE i.platform = 'youtube'
        ORDER BY i.report_date, i.published_at
    """)
    all_items = [dict(r) for r in cur.fetchall()]
    print(f"\nTotal YouTube items: {len(all_items)}")

    success_items = [i for i in all_items if i["ext_status"] == "success"]
    blocked_items = [i for i in all_items if i["ext_status"] == "blocked"]
    short_items = [i for i in all_items if i["ext_status"] is None and i["duration_seconds"] < 300]
    other_items = [i for i in all_items if i["ext_status"] not in ("success", "blocked") and i["duration_seconds"] >= 300]

    print(f"  success (will summarize): {len(success_items)}")
    print(f"  blocked (no transcript):  {len(blocked_items)}")
    print(f"  short (<5min, skipped):   {len(short_items)}")
    print(f"  other (no extraction):    {len(other_items)}")

    # ── 3. Generate single-episode summaries ──
    print(f"\n--- Generating single-episode summaries ---")
    digest_cache: dict[str, dict[str, Any]] = {}
    summary_count = 0
    skip_count = 0

    for idx, item in enumerate(success_items):
        item_id = item["item_id"]
        video_id = item["platform_id"]
        output_dir = ITEMS_DIR / "youtube" / video_id
        summary_path = output_dir / "summary.json"
        txt_path = output_dir / "transcript.txt"
        transcript_sha = item["transcript_sha256"] or ""

        # sha256-gated skip
        if summary_path.exists():
            try:
                existing = json.loads(summary_path.read_text(encoding="utf-8"))
                if existing.get("transcript_sha256") == transcript_sha:
                    digest_cache[item_id] = existing["digest"]
                    skip_count += 1
                    continue
            except Exception:
                pass

        # Read transcript
        if not txt_path.exists():
            print(f"  [SKIP] {video_id}: no transcript.txt", flush=True)
            continue

        transcript = txt_path.read_text(encoding="utf-8", errors="replace")
        if not transcript.strip():
            print(f"  [SKIP] {video_id}: empty transcript", flush=True)
            continue

        # Generate digest
        item_with_source = {**item, "source_name": source_names.get(item["source_id"], item["source_id"])}
        try:
            digest = extractive_digest(item_with_source, transcript)
        except Exception as e:
            print(f"  [ERROR] {video_id}: {e}", flush=True)
            continue

        # Write summary.json
        summary = {
            "schema_version": 1,
            "item_id": item_id,
            "platform": "youtube",
            "platform_id": video_id,
            "transcript_sha256": transcript_sha,
            "generated_at": datetime.now().isoformat(),
            "generator": "deterministic_extractive",
            "digest": digest,
        }
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        digest_cache[item_id] = digest
        summary_count += 1

        if (idx + 1) % 100 == 0:
            print(f"  ... {idx + 1}/{len(success_items)} summaries, {skip_count} cached", flush=True)

    print(f"  Generated: {summary_count}, Cached: {skip_count}, Total: {summary_count + skip_count}")

    # ── 4. Build daily views ──
    print(f"\n--- Building daily views ---")

    # Group items by report_date
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    all_skipped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for item in success_items:
        date = item["report_date"]
        if item["item_id"] in digest_cache:
            by_date[date].append(item)

    # Collect skipped items by date
    for item in blocked_items:
        all_skipped[item["report_date"] or "unknown"].append(item)
    for item in short_items:
        all_skipped[item["report_date"] or "unknown"].append(item)
    for item in other_items:
        all_skipped[item["report_date"] or "unknown"].append(item)

    # Also track items without digest
    for item in success_items:
        if item["item_id"] not in digest_cache:
            all_skipped[item["report_date"]].append(item)

    dates = sorted(by_date.keys())
    print(f"  Dates with content: {len(dates)}")
    print(f"  Dates with skipped: {len(all_skipped)}")
    print(f"  Range: {dates[0]} to {dates[-1]}")

    daily_count = 0
    for date in dates:
        date_items = by_date[date]
        if not date_items:
            continue

        date_dir = DAILY_DIR / date[:4] / f"{date[:4]}-{date[5:7]}" / date
        date_dir.mkdir(parents=True, exist_ok=True)

        # Prepare items + digests for build_report
        item_digests: list[tuple[dict[str, Any], dict[str, Any]]] = []
        item_refs: list[dict[str, Any]] = []
        for item in date_items:
            digest = digest_cache.get(item["item_id"])
            if not digest:
                continue
            report_item = build_item_for_report(item)
            report_item["source_name"] = source_names.get(item["source_id"], item["source_id"])
            item_digests.append((report_item, digest))
            item_refs.append({
                "item_id": item["item_id"],
                "platform_id": item["platform_id"],
                "title": item["title"],
                "url": item["url"],
                "source_id": item["source_id"],
                "source_name": source_names.get(item["source_id"], item["source_id"]),
                "category": item["category"],
                "duration_seconds": item["duration_seconds"],
                "published_at": item["published_at"],
                "relative_path": f"../../items/youtube/{item['platform_id']}/",
            })

        if not item_digests:
            continue

        # Build report
        report = build_report(date, item_digests)
        report["platform_scope"] = "youtube"
        report["mode"] = "youtube_only_draft"
        report["title"] = f"{date} YouTube 更新日报（草稿）"

        # Write digest.json
        digest_json_path = date_dir / "digest.json"
        digest_json_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # Write digest.md
        digest_md_path = date_dir / "digest.md"
        digest_md_path.write_text(report_to_markdown(report), encoding="utf-8")

        # Write items.json
        items_json_path = date_dir / "items.json"
        items_json_path.write_text(
            json.dumps(item_refs, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # Write manifest.json
        skipped_for_date = all_skipped.get(date, [])
        skipped_refs = []
        for s in skipped_for_date:
            skipped_refs.append({
                "item_id": s.get("item_id", ""),
                "platform_id": s.get("platform_id", ""),
                "title": s.get("title", ""),
                "reason": (
                    "no_subtitles" if s.get("ext_status") == "blocked"
                    else "short_clip" if s.get("duration_seconds", 0) < 300
                    else "no_extraction" if s.get("ext_status") is None
                    else "no_digest"
                ),
                "error_type": s.get("error_type"),
                "error_message": (s.get("error_message") or "")[:200],
            })

        manifest = {
            "schema_version": 1,
            "date": date,
            "platform_scope": "youtube",
            "mode": "youtube_only_draft",
            "total_items_in_window": len(date_items) + len(skipped_for_date),
            "included_items": len(item_refs),
            "skipped_items": len(skipped_refs),
            "skipped": skipped_refs,
            "completeness": "partial" if skipped_refs else "complete",
            "generated_at": datetime.now().isoformat(),
        }
        manifest_path = date_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        daily_count += 1

    print(f"  Daily views generated: {daily_count}")

    # ── 5. Global summary ──
    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"  Phase E complete")
    print(f"  Summaries: {summary_count + skip_count} ({summary_count} new, {skip_count} cached)")
    print(f"  Daily views: {daily_count} dates")
    print(f"  Blocked items: {len(blocked_items)}")
    print(f"  Short items skipped: {len(short_items)}")
    print(f"  Elapsed: {elapsed:.1f}s ({elapsed / 60:.1f}m)")
    print(f"{'=' * 60}")

    conn.close()


if __name__ == "__main__":
    run_phase_e()