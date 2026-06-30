#!/usr/bin/env python3
"""Generate cached item summaries for historical backfill items.

This is phase E's first step. It reads completed transcript extractions from
backfill/state/backfill.sqlite and writes one cache file per item:

    backfill/items/<platform>/<platform_id>/summary.json

The cache key is the transcript sha256 from the extraction record. Re-running
the command skips existing summaries when the transcript hash has not changed.

LLM adapter contract
--------------------
By default this script uses the same OpenAI-compatible environment variables as
scripts/generate_daily_report.py:

    LLM_BASE_URL   e.g. http://localhost:8000/v1
    LLM_MODEL      model name
    LLM_API_KEY    optional
    LLM_TIMEOUT    optional, seconds

If these are not set, the imported summarizer falls back to deterministic
extractive summaries. For real phase E work, pass --require-llm so the command
fails fast instead of silently producing fallback drafts.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.backfill.db import get_conn
from scripts.generate_daily_report import llm_configured, summarize_item_contract


ITEMS_DIR = ROOT / "backfill" / "items"
DEFAULT_PLATFORM = "youtube"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def item_dir(platform: str, platform_id: str) -> Path:
    return ITEMS_DIR / platform / platform_id


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def query_items(
    conn: sqlite3.Connection,
    platform: str,
    month: str | None,
    date: str | None,
    limit: int | None,
    item_id: str | None,
) -> list[sqlite3.Row]:
    clauses = ["i.platform = ?", "e.status = 'success'"]
    params: list[Any] = [platform]
    if month:
        clauses.append("substr(i.report_date, 1, 7) = ?")
        params.append(month)
    if date:
        clauses.append("i.report_date = ?")
        params.append(date)
    if item_id:
        clauses.append("i.item_id = ?")
        params.append(item_id)

    sql = f"""
        SELECT
            i.item_id, i.platform, i.platform_id, i.source_id, i.category,
            i.title, i.url, i.published_at, i.report_date, i.duration_seconds,
            i.language, s.name AS source_name,
            e.method AS extraction_method, e.language AS extraction_language,
            e.sha256 AS transcript_sha256, e.text_chars, e.coverage_ratio,
            e.completed_at AS extraction_completed_at
        FROM items i
        JOIN extractions e ON e.item_id = i.item_id
        LEFT JOIN sources s ON s.source_id = i.source_id
        WHERE {" AND ".join(clauses)}
        ORDER BY i.report_date, i.published_at, i.item_id
    """
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    return list(conn.execute(sql, params))


def to_summarizer_item(row: sqlite3.Row) -> dict[str, Any]:
    duration = int(row["duration_seconds"] or 0)
    return {
        "item_id": row["item_id"],
        "platform": row["platform"],
        "platform_id": row["platform_id"],
        "source_id": row["source_id"],
        "source_name": row["source_name"] or row["source_id"],
        "category": row["category"] or "待分类",
        "title": row["title"] or "",
        "original_title": row["title"] or "",
        "url": row["url"] or "",
        "published_at": row["published_at"] or "",
        "report_date": row["report_date"] or "",
        "duration": duration,
        "duration_seconds": duration,
        "language": row["language"] or row["extraction_language"] or "",
    }


def existing_cache_valid(summary_path: Path, transcript_sha256: str, force: bool) -> bool:
    if force:
        return False
    existing = read_json(summary_path)
    if not existing:
        return False
    return existing.get("transcript_sha256") == transcript_sha256 and isinstance(
        existing.get("digest"), dict
    )


def record_failure(conn: sqlite3.Connection, item_id: str, error_type: str, message: str) -> None:
    conn.execute(
        """
        INSERT INTO failures(item_id, stage, error_type, error_message, retry_count, max_retries, is_terminal)
        VALUES(?, 'summary', ?, ?, 0, 3, 0)
        """,
        (item_id, error_type, message[:1000]),
    )
    conn.commit()


def summarize_one(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    max_attempts: int,
    force: bool,
    dry_run: bool,
) -> str:
    platform = row["platform"]
    platform_id = row["platform_id"]
    out_dir = item_dir(platform, platform_id)
    transcript_path = out_dir / "transcript.txt"
    summary_path = out_dir / "summary.json"

    if not transcript_path.exists():
        record_failure(conn, row["item_id"], "missing_transcript", str(transcript_path))
        return "failed_missing_transcript"

    transcript = transcript_path.read_text(encoding="utf-8", errors="replace")
    transcript_sha256 = row["transcript_sha256"] or sha256_text(transcript)
    if existing_cache_valid(summary_path, transcript_sha256, force):
        return "skipped_cached"

    item = to_summarizer_item(row)
    if dry_run:
        print(f"[DRY] would summarize {row['item_id']} -> {summary_path}")
        return "dry_run"

    try:
        digest = summarize_item_contract(item, transcript, max_attempts=max_attempts)
    except Exception as exc:  # Keep going; phase E is batch-oriented.
        record_failure(conn, row["item_id"], "summary_failed", str(exc))
        print(f"[FAIL] {row['item_id']}: {exc}", flush=True)
        return "failed_summary"

    payload = {
        "schema_version": 1,
        "item_id": row["item_id"],
        "platform": platform,
        "platform_id": platform_id,
        "source_id": row["source_id"],
        "source_name": row["source_name"] or row["source_id"],
        "category": row["category"] or "待分类",
        "title": row["title"] or "",
        "url": row["url"] or "",
        "published_at": row["published_at"] or "",
        "report_date": row["report_date"] or "",
        "duration_seconds": int(row["duration_seconds"] or 0),
        "transcript_sha256": transcript_sha256,
        "transcript_text_chars": len(transcript),
        "extraction": {
            "method": row["extraction_method"],
            "language": row["extraction_language"],
            "coverage_ratio": row["coverage_ratio"],
            "text_chars": row["text_chars"],
            "completed_at": row["extraction_completed_at"],
        },
        "generation": {
            "script": "scripts/backfill/summarize_batch.py",
            "generated_at": utc_now(),
            "llm_configured": llm_configured(),
            "model": os.getenv("LLM_MODEL", ""),
            "base_url": os.getenv("LLM_BASE_URL", ""),
            "max_attempts": max_attempts,
        },
        "digest": digest,
    }
    write_json(summary_path, payload)
    print(f"[OK] {row['item_id']} -> {summary_path}", flush=True)
    return "success"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate cached phase-E item summaries for backfill transcripts."
    )
    parser.add_argument("--platform", default=DEFAULT_PLATFORM, help="Platform scope, default: youtube")
    parser.add_argument("--month", help="Only summarize report_date month YYYY-MM")
    parser.add_argument("--date", help="Only summarize one report_date YYYY-MM-DD")
    parser.add_argument("--item-id", help="Only summarize one item_id, e.g. youtube:VIDEO_ID")
    parser.add_argument("--limit", type=int, help="Maximum items to scan")
    parser.add_argument("--max-attempts", type=int, default=int(os.getenv("LLM_MAX_ATTEMPTS", "2")))
    parser.add_argument("--force", action="store_true", help="Regenerate even when cache hash matches")
    parser.add_argument("--dry-run", action="store_true", help="Print work without writing summaries")
    parser.add_argument(
        "--require-llm",
        action="store_true",
        help="Fail if LLM_BASE_URL and LLM_MODEL are not configured",
    )
    args = parser.parse_args()

    if args.require_llm and not llm_configured():
        print(
            "LLM is not configured. Set LLM_BASE_URL and LLM_MODEL, and optionally LLM_API_KEY.",
            file=sys.stderr,
        )
        return 2

    conn = get_conn()
    rows = query_items(conn, args.platform, args.month, args.date, args.limit, args.item_id)
    print(
        f"Phase E summaries: platform={args.platform}, items={len(rows)}, "
        f"llm_configured={llm_configured()}, model={os.getenv('LLM_MODEL', '') or '<fallback>'}"
    )

    counts: dict[str, int] = {}
    for row in rows:
        status = summarize_one(conn, row, args.max_attempts, args.force, args.dry_run)
        counts[status] = counts.get(status, 0) + 1

    print("Summary result:")
    for key in sorted(counts):
        print(f"  {key}: {counts[key]}")
    return 0 if not any(key.startswith("failed") for key in counts) else 1


if __name__ == "__main__":
    raise SystemExit(main())
