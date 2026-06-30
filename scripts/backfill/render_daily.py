#!/usr/bin/env python3
"""Render YouTube-only backfill daily reports from cached summaries."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.report_contract import build_report, report_to_markdown


DAILY_DIR = ROOT / "backfill" / "daily"
MODE = "youtube_only_draft"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_json(data: Any) -> str:
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def iter_daily_dirs(month: str | None, date: str | None) -> list[Path]:
    if date:
        path = DAILY_DIR / date[:4] / date[:7] / date
        return [path] if (path / "items.json").exists() else []
    if month:
        month_dir = DAILY_DIR / month[:4] / month
        if not month_dir.exists():
            return []
        return sorted(path for path in month_dir.iterdir() if (path / "items.json").exists())
    return sorted(path.parent for path in DAILY_DIR.glob("*/*/*/items.json"))


def load_summary(ref: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    summary_path = ROOT / ref["summary_path"]
    summary = read_json(summary_path)
    item = {
        "url": summary.get("url") or ref.get("url", ""),
        "title": summary.get("title") or ref.get("title", ""),
        "original_title": summary.get("title") or ref.get("title", ""),
        "source_name": summary.get("source_name") or ref.get("source_name", ""),
        "platform": summary.get("platform") or ref.get("platform", ""),
        "published_at": summary.get("published_at") or ref.get("published_at", ""),
        "duration": summary.get("duration_seconds") or ref.get("duration_seconds", 0),
        "category": summary.get("category") or ref.get("category", "待分类"),
    }
    digest = summary.get("digest")
    if not isinstance(digest, dict):
        raise ValueError(f"summary has no digest: {summary_path}")
    return item, digest


def draft_markdown(report: dict[str, Any], manifest: dict[str, Any]) -> str:
    rendered = report_to_markdown(report).splitlines()
    if rendered and rendered[0].startswith("# "):
        rendered[0] = f"# {report['date']} YouTube-only 播客 / 视频更新日报（草稿）"
    preamble = [
        "",
        "> 范围：本稿只包含 YouTube 已成功字幕的历史回填条目；小宇宙仍在阶段 D/E 流水线外。",
        (
            f"> 本日 YouTube 条目 {manifest.get('total_platform_items', 0)} 条，"
            f"纳入 {manifest.get('ready_items', 0)} 条，"
            f"跳过 {manifest.get('skipped_items', 0)} 条；明细见同目录 manifest.json。"
        ),
        "",
    ]
    return "\n".join(rendered[:1] + preamble + rendered[1:]).rstrip() + "\n"


def render_one(day_dir: Path, dry_run: bool) -> str:
    items_path = day_dir / "items.json"
    manifest_path = day_dir / "manifest.json"
    items_payload = read_json(items_path)
    manifest = read_json(manifest_path) if manifest_path.exists() else {}

    if items_payload.get("mode") != MODE:
        return "skipped_wrong_mode"
    refs = items_payload.get("items", [])
    if not refs:
        return "skipped_empty"

    item_digests = [load_summary(ref) for ref in refs]
    report = build_report(items_payload["report_date"], item_digests)
    report["title"] = f"{items_payload['report_date']} YouTube-only 播客与视频更新日报（草稿）"
    report["mode"] = MODE
    report["platform_scope"] = ["youtube"]
    report["coverage"] = {
        "total_platform_items": manifest.get("total_platform_items", len(refs)),
        "ready_items": manifest.get("ready_items", len(refs)),
        "skipped_items": manifest.get("skipped_items", 0),
        "skip_reasons": manifest.get("skip_reasons", {}),
    }
    report["generation"] = {
        "script": "scripts/backfill/render_daily.py",
        "generated_at": utc_now(),
        "source_items": str(items_path.relative_to(ROOT)).replace("\\", "/"),
        "source_manifest": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
    }

    digest_hash = sha256_json(report)
    markdown = draft_markdown(report, manifest)

    if dry_run:
        print(f"[DRY] would render {day_dir} items={len(refs)} hash={digest_hash[:12]}")
        return "dry_run"

    write_json(day_dir / "digest.json", report)
    (day_dir / "digest.md").write_text(markdown, encoding="utf-8")
    if manifest:
        manifest["digest_hash"] = digest_hash
        manifest["digest_generated_at"] = report["generation"]["generated_at"]
        manifest["digest_path"] = str((day_dir / "digest.json").relative_to(ROOT)).replace("\\", "/")
        manifest["markdown_path"] = str((day_dir / "digest.md").relative_to(ROOT)).replace("\\", "/")
        manifest["status"] = "rendered_partial" if manifest.get("skipped_items", 0) else "rendered"
        write_json(manifest_path, manifest)
    print(f"[OK] rendered {day_dir} items={len(refs)} hash={digest_hash[:12]}")
    return "rendered"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render YouTube-only draft daily digests.")
    parser.add_argument("--month", help="Only render report_date month YYYY-MM")
    parser.add_argument("--date", help="Only render one report_date YYYY-MM-DD")
    parser.add_argument("--limit-days", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    dirs = iter_daily_dirs(args.month, args.date)
    if args.limit_days is not None:
        dirs = dirs[: args.limit_days]
    print(f"Render daily reports: mode={MODE}, dates={len(dirs)}")

    counts: dict[str, int] = {}
    for day_dir in dirs:
        status = render_one(day_dir, args.dry_run)
        counts[status] = counts.get(status, 0) + 1
    print("Render result:")
    for key in sorted(counts):
        print(f"  {key}: {counts[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
