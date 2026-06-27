#!/usr/bin/env python3
"""Run subtitle extraction repeatedly and stop after a bounded number of tries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", required=True, help="initial URL file")
    parser.add_argument("--max-attempts", type=int, default=5)
    parser.add_argument("--retry-delays", default="60,180,300,600", help="seconds between attempts")
    parser.add_argument("--results-json", default="subtitles/extraction_results.json")
    parser.add_argument("--failed-urls", default="subtitles/failed_urls.txt")
    parser.add_argument("--extractor", default=str(BASE_DIR / "extract_subtitles.py"))
    args, extractor_args = parser.parse_known_args()
    if extractor_args and extractor_args[0] == "--":
        extractor_args = extractor_args[1:]
    return args, extractor_args


def read_urls(path: Path) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        url = line.strip()
        if url and not url.startswith("#") and url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def read_records(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [row for row in data if isinstance(row, dict) and row.get("url")] if isinstance(data, list) else []


def main() -> int:
    args, extractor_args = parse_args()
    max_attempts = max(1, min(5, args.max_attempts))
    delays = [max(0, int(value.strip())) for value in args.retry_delays.split(",") if value.strip()]
    if not delays:
        delays = [0]

    all_urls = read_urls(Path(args.batch))
    pending = list(all_urls)
    state: dict[str, dict[str, Any]] = {}
    results_path = Path(args.results_json)
    failed_path = Path(args.failed_urls)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    failed_path.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, max_attempts + 1):
        if not pending:
            break
        attempt_batch = results_path.parent / f"attempt_{attempt}_urls.txt"
        attempt_results = results_path.parent / f"attempt_{attempt}_results.json"
        attempt_retry = results_path.parent / f"attempt_{attempt}_retry_urls.txt"
        attempt_asr = results_path.parent / f"attempt_{attempt}_asr_urls.txt"
        attempt_batch.write_text("".join(f"{url}\n" for url in pending), encoding="utf-8")

        print(f"\n=== Subtitle attempt {attempt}/{max_attempts}: {len(pending)} URL(s) ===", flush=True)
        command = [
            sys.executable,
            args.extractor,
            "--batch",
            str(attempt_batch),
            "--results-json",
            str(attempt_results),
            "--retry-urls",
            str(attempt_retry),
            "--asr-urls",
            str(attempt_asr),
            "--allow-partial",
            *extractor_args,
        ]
        completed = subprocess.run(command, cwd=str(BASE_DIR), check=False)
        records = read_records(attempt_results)
        by_url = {str(row["url"]): row for row in records}
        next_pending: list[str] = []
        for url in pending:
            record = dict(by_url.get(url) or {})
            if not record:
                record = {
                    "url": url,
                    "ok": False,
                    "reason_code": "extractor_no_result",
                    "message": f"extractor exited {completed.returncode} without a result record",
                    "retryable": True,
                }
            record["attempt"] = attempt
            state[url] = record
            if not record.get("ok"):
                next_pending.append(url)
        pending = next_pending

        if pending and attempt < max_attempts:
            delay = delays[min(attempt - 1, len(delays) - 1)]
            print(f"Attempt {attempt} left {len(pending)} failure(s); retrying in {delay}s", flush=True)
            if delay:
                time.sleep(delay)

    final_records = [state.get(url, {"url": url, "ok": False, "reason_code": "not_attempted"}) for url in all_urls]
    results_path.write_text(json.dumps(final_records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failed_path.write_text("".join(f"{url}\n" for url in pending), encoding="utf-8")
    succeeded = sum(1 for row in final_records if row.get("ok"))
    print(f"\nSubtitle extraction complete: {succeeded}/{len(all_urls)} succeeded")
    print(f"Final results: {results_path}")
    print(f"Final failures: {failed_path}")
    if pending:
        print(f"Giving up after {max_attempts} attempts for {len(pending)} URL(s)")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
