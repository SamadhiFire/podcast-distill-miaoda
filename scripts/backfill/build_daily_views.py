#!/usr/bin/env python3
"""Build date-based YouTube-only draft views from cached summaries.

This script does not call models and does not publish anything. It creates:

    backfill/daily/YYYY/YYYY-MM/YYYY-MM-DD/items.json
    backfill/daily/YYYY/YYYY-MM/YYYY-MM-DD/manifest.json

The output is intentionally marked as youtube_only_draft so it can be reviewed
before Xiaoyuzhou phase D/E catches up.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.backfill.db import get_conn


ITEMS_DIR = ROOT / "backfill" / "items"
DAILY_DIR = ROOT / "backfill" / "daily"
MODE = "youtube_only_draft"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_json(data: Any) -> str:
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def query_rows(
    conn: sqlite3.Connection, platform: str, month: str | None, date: str | None
) -> list[sqlite3.Row]:
    clauses = ["i.platform = ?"]
    params: list[Any] = [platform]
    if month:
        clauses.append("substr(i.report_date, 1, 7) = ?")
        params.append(month)
    if date:
        clauses.append("i.report_date = ?")
        params.append(date)
    sql = f"""
        SELECT
            i.item_id, i.platform, i.platform_id, i.source_id, i.category,
            i.title, i.url, i.published_at, i.report_date, i.duration_seconds,
            i.language, s.name AS source_name,
            e.status AS extraction_status, e.sha256 AS transcript_sha256,
            e.error_type, e.error_message
        FROM items i
        LEFT JOIN extractions e ON e.item_id = i.item_id
        LEFT JOIN sources s ON s.source_id = i.source_id
        WHERE {" AND ".join(clauses)}
        ORDER BY i.report_date, i.published_at, i.item_id
    """
    return list(conn.execute(sql, params))


def daily_path(report_date: str) -> Path:
    year = report_date[:4]
    month = report_date[:7]
    return DAILY_DIR / year / month / report_date


def summary_status(row: sqlite3.Row) -> tuple[bool, str, Path | None]:
    out_dir = ITEMS_DIR / row["platform"] / row["platform_id"]
    summary_path = out_dir / "summary.json"
    status = row["extraction_status"]
    duration = int(row["duration_seconds"] or 0)
    if status is None:
        return False, "short_no_extraction" if duration <= 300 else "no_extraction", None
    if status != "success":
        return False, status, None
    summary = read_json(summary_path)
    if not summary:
        return False, "missing_summary", summary_path
    expected_hash = row["transcript_sha256"]
    if expected_hash and summary.get("transcript_sha256") != expected_hash:
        return False, "stale_summary", summary_path
    if not isinstance(summary.get("digest"), dict):
        return False, "invalid_summary", summary_path
    digest = summary.get("digest") or {}
    generation = summary.get("generation") if isinstance(summary.get("generation"), dict) else {}
    quality = str(digest.get("quality") or summary.get("generator") or "").lower()
    script = str(generation.get("script") or "").lower()
    if "fallback" in quality or "deterministic" in quality or "deterministic" in script:
        return False, "fallback_summary", summary_path
    return True, "ready", summary_path


def item_ref(row: sqlite3.Row, summary_path: Path) -> dict[str, Any]:
    out_dir = ITEMS_DIR / row["platform"] / row["platform_id"]
    return {
        "item_id": row["item_id"],
        "platform": row["platform"],
        "platform_id": row["platform_id"],
        "source_id": row["source_id"],
        "source_name": row["source_name"] or row["source_id"],
        "category": row["category"] or "待分类",
        "title": row["title"] or "",
        "url": row["url"] or "",
        "published_at": row["published_at"] or "",
        "report_date": row["report_date"] or "",
        "duration_seconds": int(row["duration_seconds"] or 0),
        "item_path": rel(out_dir),
        "summary_path": rel(summary_path),
        "transcript_path": rel(out_dir / "transcript.txt"),
    }


def build_one(report_date: str, rows: list[sqlite3.Row], dry_run: bool) -> dict[str, Any]:
    ready: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    reasons: Counter[str] = Counter()

    for row in rows:
        ok, reason, summary_path = summary_status(row)
        reasons[reason] += 1
        if ok and summary_path:
            ready.append(item_ref(row, summary_path))
            continue
        skipped.append(
            {
                "item_id": row["item_id"],
                "platform": row["platform"],
                "platform_id": row["platform_id"],
                "title": row["title"] or "",
                "duration_seconds": int(row["duration_seconds"] or 0),
                "extraction_status": row["extraction_status"],
                "error_type": row["error_type"],
                "reason": reason,
            }
        )

    items_payload = {
        "schema_version": 1,
        "mode": MODE,
        "platform_scope": ["youtube"],
        "report_date": report_date,
        "generated_at": utc_now(),
        "item_count": len(ready),
        "items": ready,
    }
    manifest = {
        "schema_version": 1,
        "mode": MODE,
        "platform_scope": ["youtube"],
        "report_date": report_date,
        "generated_at": utc_now(),
        "total_platform_items": len(rows),
        "ready_items": len(ready),
        "skipped_items": len(skipped),
        "status_counts": dict(sorted(reasons.items())),
        "skip_reasons": dict(sorted((k, v) for k, v in reasons.items() if k != "ready")),
        "skipped": skipped,
        "items_hash": sha256_json(items_payload),
        "status": "ready" if ready and not skipped else "partial" if ready else "empty",
    }

    out_dir = daily_path(report_date)
    if dry_run:
        print(f"[DRY] {report_date}: ready={len(ready)}, skipped={len(skipped)} -> {out_dir}")
    else:
        write_json(out_dir / "items.json", items_payload)
        write_json(out_dir / "manifest.json", manifest)
        print(f"[OK] {report_date}: ready={len(ready)}, skipped={len(skipped)} -> {out_dir}")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build YouTube-only draft daily views.")
    parser.add_argument("--platform", default="youtube", help="Platform scope, default: youtube")
    parser.add_argument("--month", help="Only build report_date month YYYY-MM")
    parser.add_argument("--date", help="Only build one report_date YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = get_conn()
    rows = query_rows(conn, args.platform, args.month, args.date)
    grouped: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        if row["report_date"]:
            grouped[row["report_date"]].append(row)

    print(f"Build daily views: mode={MODE}, dates={len(grouped)}, rows={len(rows)}")
    totals = Counter()
    for report_date in sorted(grouped):
        manifest = build_one(report_date, grouped[report_date], args.dry_run)
        totals["dates"] += 1
        totals["ready"] += manifest["ready_items"]
        totals["skipped"] += manifest["skipped_items"]
    print(f"Done: dates={totals['dates']}, ready={totals['ready']}, skipped={totals['skipped']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
