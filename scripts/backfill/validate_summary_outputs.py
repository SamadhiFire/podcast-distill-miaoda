#!/usr/bin/env python3
"""Validate summary.json files produced by Trae or another agent."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.backfill.db import get_conn
from scripts.report_contract import clean_text, normalize_digest


ITEMS_DIR = ROOT / "backfill" / "items"
REPORT_PATH = ROOT / "backfill" / "summary_jobs" / "validation_report.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


BOILERPLATE_RE = re.compile(
    r"\bWEBVTT\b|\bKind:\s*(captions|subtitles)\b|\bLanguage:\s*[a-z-]+\b|\[music\]|&gt;&gt;",
    re.I,
)
FORBIDDEN_FORMAT_RE = re.compile(
    r"```|\*\*|</?(?:callout|grid|column|table|thead|tbody|tr|td|th|h[1-6]|whiteboard|p|ul|ol|li|blockquote|span)\b"
    r"|flowchart\s+(?:LR|TB|TD|RL)|^\s{0,3}#{1,6}\s+|^\s*\|.*\|\s*$",
    re.I | re.M,
)
CJK_RE = re.compile(r"[\u3400-\u9fff]")
NUMBER_RE = re.compile(r"(?<![A-Za-z])\$?\d[\d,]*(?:\.\d+)?%?")


def read_transcript(row: sqlite3.Row) -> str:
    path = ITEMS_DIR / row["platform"] / row["platform_id"] / "transcript.txt"
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def numbers(text: str) -> set[str]:
    found = set()
    for raw in NUMBER_RE.findall(text or ""):
        normalized = raw.replace(",", "").lstrip("$")
        if normalized:
            found.add(normalized)
    return found


def compact_for_match(text: str) -> str:
    return re.sub(r"\s+", "", clean_text(text)).lower()


def text_quality_error(label: str, value: Any, require_cjk: bool = True) -> str | None:
    text = clean_text(value)
    if not text:
        return f"{label}_empty"
    if BOILERPLATE_RE.search(text):
        return f"{label}_looks_like_transcript_boilerplate"
    if require_cjk and not CJK_RE.search(text):
        return f"{label}_must_be_chinese"
    return None


def iter_strings(value: Any, prefix: str = "digest") -> list[tuple[str, str]]:
    if isinstance(value, str):
        return [(prefix, value)]
    if isinstance(value, list):
        output: list[tuple[str, str]] = []
        for idx, item in enumerate(value):
            output.extend(iter_strings(item, f"{prefix}_{idx}"))
        return output
    if isinstance(value, dict):
        output = []
        for key, item in value.items():
            output.extend(iter_strings(item, f"{prefix}_{key}"))
        return output
    return []


def format_pollution_error(digest: dict[str, Any]) -> str | None:
    for label, text in iter_strings(digest):
        if FORBIDDEN_FORMAT_RE.search(text or ""):
            return f"{label}_contains_forbidden_format_markup"
    return None


def required_counts(row: sqlite3.Row, digest: dict[str, Any]) -> dict[str, int]:
    duration = int(row["duration_seconds"] or 0)
    density = clean_text(digest.get("content_density") or "standard").lower()
    if duration >= 3600 or density == "high":
        return {"summary": 4, "core_points": 5}
    if duration >= 1800 or density == "standard":
        return {"summary": 3, "core_points": 4}
    return {"summary": 2, "core_points": 3}


def quality_gate_error(row: sqlite3.Row, digest: dict[str, Any], transcript: str) -> str | None:
    if not transcript.strip():
        return "transcript_missing_for_quality_gate"

    for field in ("short_title", "one_liner", "why_it_matters"):
        error = text_quality_error(field, digest.get(field))
        if error:
            return error

    for field, minimum in required_counts(row, digest).items():
        values = digest.get(field)
        if not isinstance(values, list) or len(values) < minimum:
            return f"{field}_too_few_for_duration"
        for idx, value in enumerate(values, 1):
            error = text_quality_error(f"{field}_{idx}", value)
            if error:
                return error

    takeaways = digest.get("takeaways")
    if not isinstance(takeaways, list) or not 1 <= len(takeaways) <= 2:
        return "takeaways_count_invalid"
    for idx, value in enumerate(takeaways, 1):
        error = text_quality_error(f"takeaways_{idx}", value)
        if error:
            return error
        if "?" in clean_text(value) or "？" in clean_text(value):
            return "takeaways_must_not_be_questions"

    transcript_numbers = numbers(transcript)
    for idx, fact in enumerate(digest.get("key_facts", []) or [], 1):
        if not isinstance(fact, dict):
            return f"key_facts_{idx}_invalid"
        for key in ("label", "value", "context"):
            error = text_quality_error(f"key_facts_{idx}_{key}", fact.get(key), require_cjk=False)
            if error:
                return error
        missing = numbers(f"{fact.get('value', '')} {fact.get('context', '')}") - transcript_numbers
        if missing:
            return f"key_facts_{idx}_number_not_found_in_transcript:{','.join(sorted(missing))}"

    quote = digest.get("quote")
    if isinstance(quote, dict) and quote.get("text"):
        error = text_quality_error("quote_text", quote.get("text"), require_cjk=False)
        if error:
            return error
        kind = clean_text(quote.get("kind") or "").lower()
        if kind == "verbatim" and compact_for_match(quote.get("text")) not in compact_for_match(transcript):
            return "quote_verbatim_not_found_in_transcript"

    return None


def query_items(
    conn: sqlite3.Connection,
    platform: str,
    month: str | None,
    date: str | None,
    item_id: str | None,
    limit: int | None,
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
            e.sha256 AS transcript_sha256, e.text_chars, e.coverage_ratio,
            e.method AS extraction_method, e.language AS extraction_language,
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


def normalizer_item(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "title": row["title"] or "",
        "category": row["category"] or "待分类",
        "platform": row["platform"],
        "source_name": row["source_name"] or row["source_id"],
        "published_at": row["published_at"] or "",
        "duration": int(row["duration_seconds"] or 0),
        "url": row["url"] or "",
    }


def validate_one(row: sqlite3.Row, write_normalized: bool) -> tuple[str, dict[str, Any]]:
    summary_path = ITEMS_DIR / row["platform"] / row["platform_id"] / "summary.json"
    payload = read_json(summary_path)
    detail = {
        "item_id": row["item_id"],
        "summary_path": str(summary_path.relative_to(ROOT)).replace("\\", "/"),
    }
    if not payload:
        detail["error"] = "missing_or_invalid_json"
        return "missing", detail

    expected = {
        "item_id": row["item_id"],
        "platform": row["platform"],
        "platform_id": row["platform_id"],
        "transcript_sha256": row["transcript_sha256"],
    }
    for key, value in expected.items():
        if value and payload.get(key) != value:
            detail["error"] = f"{key}_mismatch"
            detail["expected"] = value
            detail["actual"] = payload.get(key)
            return "invalid", detail

    digest = payload.get("digest")
    if not isinstance(digest, dict):
        detail["error"] = "digest_missing"
        return "invalid", detail
    format_error = format_pollution_error(digest)
    if format_error:
        detail["error"] = format_error
        return "invalid", detail
    generation = payload.get("generation") if isinstance(payload.get("generation"), dict) else {}
    quality = str(digest.get("quality") or payload.get("generator") or "").lower()
    script = str(generation.get("script") or "").lower()
    if "fallback" in quality or "deterministic" in quality or "deterministic" in script:
        detail["error"] = "fallback_summary_not_accepted"
        return "invalid", detail
    try:
        normalized = normalize_digest(digest, normalizer_item(row))
    except Exception as exc:
        detail["error"] = str(exc)
        return "invalid", detail
    gate_error = quality_gate_error(row, normalized, read_transcript(row))
    if gate_error:
        detail["error"] = gate_error
        return "invalid", detail

    if write_normalized and normalized != digest:
        payload["digest"] = normalized
        payload.setdefault("generation", {})
        payload["generation"]["normalized_at"] = utc_now()
        write_json(summary_path, payload)
        detail["normalized"] = True
    return "valid", detail


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Trae-generated backfill summary.json files.")
    parser.add_argument("--platform", default="youtube")
    parser.add_argument("--month", help="Only validate report_date month YYYY-MM")
    parser.add_argument("--date", help="Only validate one report_date YYYY-MM-DD")
    parser.add_argument("--item-id", help="Only validate one item_id")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--write-normalized", action="store_true")
    args = parser.parse_args()

    conn = get_conn()
    rows = query_items(conn, args.platform, args.month, args.date, args.item_id, args.limit)
    print(f"Validate summaries: platform={args.platform}, candidates={len(rows)}")

    counts: dict[str, int] = {}
    details: list[dict[str, Any]] = []
    for row in rows:
        status, detail = validate_one(row, args.write_normalized)
        counts[status] = counts.get(status, 0) + 1
        if status != "valid":
            details.append(detail)
            print(f"[{status.upper()}] {detail['item_id']}: {detail.get('error')}")

    report = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "platform": args.platform,
        "month": args.month,
        "date": args.date,
        "item_id": args.item_id,
        "counts": dict(sorted(counts.items())),
        "invalid_or_missing": details,
    }
    write_json(REPORT_PATH, report)
    print("Validation result:")
    for key in sorted(counts):
        print(f"  {key}: {counts[key]}")
    print(f"Report: {REPORT_PATH}")
    return 0 if counts.get("invalid", 0) == 0 and counts.get("missing", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
