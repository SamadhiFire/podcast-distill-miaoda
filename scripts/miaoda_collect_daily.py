#!/usr/bin/env python3
"""Create a Miaoda daily collection job, poll it, and download artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, time as datetime_time, timedelta, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import time
from typing import Any
from urllib.parse import urljoin
import zipfile

import requests

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python 3.11 is expected in CI.
    ZoneInfo = None  # type: ignore[assignment]


SUCCESS_STATES = {"success"}
FAILED_STATES = {"failed", "failure", "partial_failed", "partial-failed"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the thin GitHub Actions side of Miaoda daily collection."
    )
    parser.add_argument("--date", help="Report date in YYYY-MM-DD. Defaults to today in timezone.")
    parser.add_argument("--timezone", default="Asia/Shanghai")
    parser.add_argument("--window-start", help="Explicit ISO 8601 window start.")
    parser.add_argument("--window-end", help="Explicit ISO 8601 window end.")
    parser.add_argument("--sources-profile", default="podcast-distill-default")
    parser.add_argument("--api-base", default=os.getenv("MIAODA_API_BASE"))
    parser.add_argument("--api-token", default=os.getenv("MIAODA_API_TOKEN"))
    parser.add_argument(
        "--api-style",
        choices=("edge", "legacy"),
        default=os.getenv("MIAODA_API_STYLE", "edge"),
        help="edge uses Supabase Edge Functions paths; legacy uses the old /v1/daily/collect paths.",
    )
    parser.add_argument("--poll-interval", type=int, default=30)
    parser.add_argument("--timeout-seconds", type=int, default=5 * 60 * 60)
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--subtitles-dir", default="subtitles")
    parser.add_argument("--items-json")
    parser.add_argument("--manifest-json")
    parser.add_argument("--bundle-path", default="subtitles_bundle.zip")
    parser.add_argument("--status-json")
    parser.add_argument(
        "--require-transcripts",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--allow-asr",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    return parser.parse_args()


def load_timezone(name: str) -> timezone:
    if ZoneInfo is not None:
        try:
            return ZoneInfo(name)  # type: ignore[return-value]
        except Exception:
            pass
    if name == "Asia/Shanghai":
        return timezone(timedelta(hours=8))
    raise RuntimeError(f"Unsupported timezone without zoneinfo data: {name}")


def resolve_report_date(value: str | None, tz: timezone) -> str:
    if not value:
        return datetime.now(tz).strftime("%Y-%m-%d")
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError as exc:
        raise RuntimeError(f"Invalid --date, expected YYYY-MM-DD: {value}") from exc


def resolve_window(
    report_date: str,
    tz: timezone,
    explicit_start: str | None,
    explicit_end: str | None,
) -> tuple[str, str]:
    if bool(explicit_start) != bool(explicit_end):
        raise RuntimeError("--window-start and --window-end must be provided together")
    if explicit_start and explicit_end:
        return explicit_start, explicit_end
    end_date = datetime.strptime(report_date, "%Y-%m-%d").date()
    end = datetime.combine(end_date, datetime_time(6, 0), tzinfo=tz)
    start = end - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def api_url(base: str, href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return urljoin(base.rstrip("/") + "/", href.lstrip("/"))


def request_json(
    session: requests.Session,
    method: str,
    url: str,
    *,
    retries: int = 3,
    timeout: int = 30,
    **kwargs: Any,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = session.request(method, url, timeout=timeout, **kwargs)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise RuntimeError(f"Expected JSON object from {url}")
            return data
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(min(2**attempt, 10))
    raise RuntimeError(f"{method} {url} failed: {last_error}") from last_error


def download_file(
    session: requests.Session,
    url: str,
    target: Path,
    headers: dict[str, str],
    *,
    retries: int = 3,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with session.get(url, headers=headers, timeout=300, stream=True) as response:
                response.raise_for_status()
                temp_path = target.with_name(f".{target.name}.{os.getpid()}.tmp")
                with temp_path.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            handle.write(chunk)
                temp_path.replace(target)
                return
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(min(2**attempt, 10))
    raise RuntimeError(f"Download failed for {url}: {last_error}") from last_error


def require_workspace_child(path: Path, label: str) -> Path:
    resolved = path.resolve()
    workspace = Path.cwd().resolve()
    if resolved == workspace or not resolved.is_relative_to(workspace):
        raise RuntimeError(f"Refusing to operate on {label} outside workspace: {resolved}")
    return resolved


def clean_subtitles_dir(path: Path) -> None:
    resolved = require_workspace_child(path, "subtitles directory")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)


def safe_extract(zip_path: Path, destination: Path) -> None:
    destination_resolved = destination.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            member_path = destination_resolved / member.filename
            if not member_path.resolve().is_relative_to(destination_resolved):
                raise RuntimeError(f"Unsafe zip member path: {member.filename}")
        archive.extractall(destination_resolved)


def daily_path(api_style: str) -> str:
    return "/daily-collect" if api_style == "edge" else "/v1/daily/collect"


def artifact_urls(status: dict[str, Any], job_id: str, api_style: str) -> dict[str, str]:
    files = status.get("files") if isinstance(status.get("files"), dict) else {}
    base_path = daily_path(api_style)
    return {
        "daily_items_json": files.get("daily_items_json")
        or files.get("daily_items")
        or files.get("daily_items_url")
        or f"{base_path}/{job_id}/files/daily_items.json",
        "manifest_json": files.get("manifest_json")
        or files.get("manifest")
        or files.get("manifest_url")
        or f"{base_path}/{job_id}/files/manifest.json",
        "subtitles_bundle_zip": files.get("subtitles_bundle_zip")
        or files.get("subtitles_bundle")
        or files.get("subtitles_bundle_url")
        or f"{base_path}/{job_id}/files/subtitles_bundle.zip",
    }


def poll_job(
    session: requests.Session,
    base: str,
    job_id: str,
    headers: dict[str, str],
    poll_interval: int,
    timeout_seconds: int,
    status_path: Path,
    status_record: dict[str, Any],
    api_style: str,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while True:
        status = request_json(
            session,
            "GET",
            api_url(base, f"{daily_path(api_style)}/{job_id}"),
            headers=headers,
        )
        status_record["last_status"] = status
        write_json(status_path, status_record)

        state = str(status.get("status", "")).lower()
        item_count = status.get("item_count", 0)
        success_count = status.get("success_count", "")
        failure_count = status.get("failure_count", "")
        print(
            f"Miaoda job {job_id}: status={state} "
            f"items={item_count} success={success_count} failure={failure_count}",
            flush=True,
        )

        if state in SUCCESS_STATES:
            return status
        if state in FAILED_STATES:
            raise RuntimeError(f"Miaoda job failed: {json.dumps(status, ensure_ascii=False)}")
        if time.monotonic() >= deadline:
            raise RuntimeError(f"Miaoda job timed out after {timeout_seconds} seconds")
        time.sleep(max(1, poll_interval))


def main() -> int:
    args = parse_args()
    if not args.api_base:
        print("MIAODA_API_BASE is required", file=sys.stderr)
        return 2
    if not args.api_token:
        print("MIAODA_API_TOKEN is required", file=sys.stderr)
        return 2

    tz = load_timezone(args.timezone)
    report_date = resolve_report_date(args.date, tz)
    window_start, window_end = resolve_window(
        report_date,
        tz,
        args.window_start,
        args.window_end,
    )
    reports_dir = Path(args.reports_dir)
    items_path = Path(args.items_json or reports_dir / f"daily_items_{report_date}.json")
    manifest_path = Path(args.manifest_json or reports_dir / f"daily_items_{report_date}.manifest.json")
    bundle_path = Path(args.bundle_path)
    status_path = Path(args.status_json or reports_dir / f"miaoda_collect_{report_date}.status.json")
    subtitles_dir = Path(args.subtitles_dir)

    body = {
        "date": report_date,
        "window_start": window_start,
        "window_end": window_end,
        "sources_profile": args.sources_profile,
        "require_transcripts": bool(args.require_transcripts),
        "allow_asr": bool(args.allow_asr),
    }
    if args.api_style == "legacy":
        body["timezone"] = args.timezone
    status_record: dict[str, Any] = {
        "request": body,
        "created_job": None,
        "last_status": None,
        "downloads": {
            "daily_items_json": str(items_path),
            "manifest_json": str(manifest_path),
            "subtitles_bundle_zip": str(bundle_path),
        },
    }
    write_json(status_path, status_record)

    session = requests.Session()
    auth_headers = {"Authorization": f"Bearer {args.api_token}"}
    json_headers = {**auth_headers, "Content-Type": "application/json"}

    try:
        created = request_json(
            session,
            "POST",
            api_url(args.api_base, daily_path(args.api_style)),
            headers=json_headers,
            json=body,
        )
        job_id = str(created.get("job_id") or "").strip()
        if not job_id:
            raise RuntimeError(f"Miaoda create response has no job_id: {created}")
        status_record["created_job"] = created
        write_json(status_path, status_record)
        print(f"Miaoda job created: {job_id}", flush=True)

        final_status = poll_job(
            session,
            args.api_base,
            job_id,
            auth_headers,
            args.poll_interval,
            args.timeout_seconds,
            status_path,
            status_record,
            args.api_style,
        )

        urls = artifact_urls(final_status, job_id, args.api_style)
        download_file(
            session,
            api_url(args.api_base, urls["daily_items_json"]),
            items_path,
            auth_headers,
        )
        download_file(
            session,
            api_url(args.api_base, urls["manifest_json"]),
            manifest_path,
            auth_headers,
        )
        download_file(
            session,
            api_url(args.api_base, urls["subtitles_bundle_zip"]),
            bundle_path,
            auth_headers,
        )

        clean_subtitles_dir(subtitles_dir)
        safe_extract(bundle_path, Path("."))
        if not subtitles_dir.exists():
            raise RuntimeError("subtitles_bundle.zip did not extract a subtitles/ directory")

        status_record["completed"] = True
        write_json(status_path, status_record)
        print(f"Downloaded: {items_path}")
        print(f"Downloaded: {manifest_path}")
        print(f"Downloaded: {bundle_path}")
        return 0
    except Exception as exc:
        status_record["completed"] = False
        status_record["error"] = str(exc)
        write_json(status_path, status_record)
        print(f"Miaoda collection failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
