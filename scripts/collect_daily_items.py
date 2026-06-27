#!/usr/bin/env python3
"""Collect newly published YouTube and Xiaoyuzhou items for the daily digest."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import requests


BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BASE_DIR / "config"
REPORTS_DIR = BASE_DIR / "reports"
TZ_SHANGHAI = timezone(timedelta(hours=8))
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


class SourceFetchError(RuntimeError):
    """A source failed without making the whole collection unrecoverable."""


class YouTubeDataAPI:
    def __init__(self, api_key: str, timeout: int = 20) -> None:
        self.api_key = api_key
        self.timeout = timeout

    def get(self, resource: str, **params: Any) -> dict[str, Any]:
        try:
            response = requests.get(
                f"{YOUTUBE_API_BASE}/{resource}",
                headers={"x-goog-api-key": self.api_key, "Accept": "application/json"},
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            detail = ""
            if exc.response is not None:
                try:
                    payload = exc.response.json()
                    detail = payload.get("error", {}).get("message", "")
                except Exception:
                    detail = exc.response.text[:300]
            raise SourceFetchError(detail or str(exc)) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--date",
        help=(
            "Exclusive window end in Asia/Shanghai. Supports YYYY-MM-DD, "
            "YYYY-MM-DDTHH:MM and ISO 8601 offsets; default: now"
        ),
    )
    parser.add_argument("--lookback-hours", type=int, default=24)
    parser.add_argument("--youtube-scan-limit", type=int, default=25)
    parser.add_argument(
        "--youtube-backend",
        choices=("auto", "api", "yt-dlp"),
        default="auto",
        help="auto uses Data API when YOUTUBE_API_KEY is set, otherwise yt-dlp",
    )
    parser.add_argument("--youtube-api-timeout", type=int, default=20)
    parser.add_argument("--channel-cache", default="config/youtube_channel_cache.json")
    parser.add_argument("--output-json", default=None)
    parser.add_argument("--output-urls", default="config/daily_urls.txt")
    parser.add_argument("--manifest-json", default=None)
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="return success when some sources failed; failures remain recorded in the manifest",
    )
    return parser.parse_args()


def report_date(value: str | None) -> datetime:
    if not value:
        return datetime.now(TZ_SHANGHAI)
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Cannot parse date: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=TZ_SHANGHAI)
    return parsed.astimezone(TZ_SHANGHAI)


def normalize_playlist_url(url: str) -> str:
    parsed = urlparse(url.strip())
    qs = parse_qs(parsed.query)
    if "list" in qs:
        return "https://www.youtube.com/playlist?" + urlencode({"list": qs["list"][0]})
    return url.strip()


def parse_category_file(path: Path) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    category = ""
    platform = ""
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("## "):
            category = re.sub(r"^##\s*\d+\.\s*", "", line).strip()
            continue
        if line == "### Xiaoyuzhou":
            platform = "xiaoyuzhou"
            continue
        if line == "### YouTube":
            platform = "youtube"
            continue
        if not line.startswith("- "):
            continue
        parts = [part.strip() for part in line[2:].strip().split("|")]
        if len(parts) < 2:
            continue
        name, url = parts[0], parts[1]
        if not url.startswith("http"):
            continue
        opts = ",".join(parts[2:])
        match = re.search(r"min_duration=(\d+)", opts)
        min_duration = int(match.group(1)) if match else 0
        if platform == "youtube":
            url = normalize_playlist_url(url)
        sources.append(
            {
                "category": category,
                "platform": platform,
                "name": name,
                "url": url,
                "min_duration": min_duration,
            }
        )
    return sources


def parse_next_data(html: str) -> dict[str, Any] | None:
    match = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not match:
        return None
    return json.loads(match.group(1))


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, timezone.utc)
    text = str(value)
    if re.fullmatch(r"\d{8}", text):
        return datetime.strptime(text, "%Y%m%d").replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def in_window(value: datetime | None, start_utc: datetime, end_utc: datetime) -> bool:
    return bool(value and start_utc <= value < end_utc)


def fetch_xiaoyuzhou_source(
    source: dict[str, Any], start_utc: datetime, end_utc: datetime
) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    try:
        response = None
        for attempt in range(3):
            try:
                response = requests.get(source["url"], headers=HEADERS, timeout=30)
                response.raise_for_status()
                break
            except requests.RequestException as exc:
                last_error = exc
                status = exc.response.status_code if exc.response is not None else None
                if status is not None and status < 500:
                    raise
                if attempt < 2:
                    time.sleep(2 ** attempt)
        if response is None or last_error is not None and not response.ok:
            raise last_error or SourceFetchError("empty Xiaoyuzhou response")
        # Xiaoyuzhou serves UTF-8 HTML but does not always declare a charset.
        # requests then falls back to ISO-8859-1 and silently mojibakes Chinese
        # podcast/episode titles. Decode the page bytes explicitly.
        html = response.content.decode("utf-8", errors="replace")
        data = parse_next_data(html)
        if not data:
            raise SourceFetchError("__NEXT_DATA__ not found")
        podcast = data.get("props", {}).get("pageProps", {}).get("podcast") or {}
        episodes = podcast.get("episodes") or []
    except (requests.RequestException, ValueError, SourceFetchError) as exc:
        raise SourceFetchError(str(exc)) from exc

    items: list[dict[str, Any]] = []
    for episode in episodes:
        published = parse_datetime(episode.get("pubDate"))
        if not in_window(published, start_utc, end_utc):
            continue
        items.append(
            {
                "platform": "xiaoyuzhou",
                "category": source["category"],
                "source_name": podcast.get("title") or source["name"],
                "source_url": source["url"],
                "title": episode.get("title") or "",
                "original_title": episode.get("title") or "",
                "url": f"https://www.xiaoyuzhoufm.com/episode/{episode.get('eid')}",
                "published_at": published.isoformat(),
                "duration": episode.get("duration"),
                "description": episode.get("description") or "",
            }
        )
    return items


def youtube_source_reference(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    playlist_id = parse_qs(parsed.query).get("list")
    if playlist_id:
        return "playlist", playlist_id[0]
    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        raise SourceFetchError(f"Unsupported YouTube source URL: {url}")
    if parts[0] == "channel" and len(parts) > 1:
        return "channel", parts[1]
    if parts[0].startswith("@"):
        return "handle", parts[0]
    raise SourceFetchError(f"Unsupported YouTube source URL: {url}")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return default


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temp_path.write_text(text, encoding="utf-8")
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def resolve_uploads_playlist(
    source: dict[str, Any], api: YouTubeDataAPI, cache: dict[str, Any]
) -> str:
    kind, identifier = youtube_source_reference(source["url"])
    if kind == "playlist":
        return identifier
    cached = cache.get(source["url"]) or {}
    if cached.get("uploads_playlist_id"):
        return cached["uploads_playlist_id"]
    params: dict[str, Any] = {"part": "contentDetails,snippet"}
    if kind == "handle":
        params["forHandle"] = identifier
    else:
        params["id"] = identifier
    data = api.get("channels", **params)
    channels = data.get("items") or []
    if not channels:
        raise SourceFetchError(f"Channel not found: {identifier}")
    channel = channels[0]
    uploads_id = (
        channel.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    )
    if not uploads_id:
        raise SourceFetchError(f"Uploads playlist missing: {identifier}")
    cache[source["url"]] = {
        "channel_id": channel.get("id"),
        "channel_title": channel.get("snippet", {}).get("title"),
        "uploads_playlist_id": uploads_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    return uploads_id


def fetch_youtube_source_api(
    source: dict[str, Any],
    start_utc: datetime,
    end_utc: datetime,
    scan_limit: int,
    api: YouTubeDataAPI,
    cache: dict[str, Any],
) -> list[dict[str, Any]]:
    playlist_id = resolve_uploads_playlist(source, api, cache)
    remaining = max(1, scan_limit)
    page_token: str | None = None
    items: list[dict[str, Any]] = []
    while remaining > 0:
        params: dict[str, Any] = {
            "part": "snippet,contentDetails",
            "playlistId": playlist_id,
            "maxResults": min(50, remaining),
            "fields": (
                "nextPageToken,items(contentDetails(videoId,videoPublishedAt),"
                "snippet(title,description,videoOwnerChannelTitle,videoOwnerChannelId))"
            ),
        }
        if page_token:
            params["pageToken"] = page_token
        data = api.get("playlistItems", **params)
        page_items = data.get("items") or []
        for playlist_item in page_items:
            details = playlist_item.get("contentDetails") or {}
            snippet = playlist_item.get("snippet") or {}
            video_id = details.get("videoId")
            published = parse_datetime(details.get("videoPublishedAt"))
            if not video_id or not in_window(published, start_utc, end_utc):
                continue
            items.append(
                {
                    "platform": "youtube",
                    "category": source["category"],
                    "source_name": snippet.get("videoOwnerChannelTitle") or source["name"],
                    "source_url": source["url"],
                    "title": snippet.get("title") or "",
                    "original_title": snippet.get("title") or "",
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "published_at": published.isoformat(),
                    "description": snippet.get("description") or "",
                    "_video_id": video_id,
                    "_min_duration": source.get("min_duration", 0),
                }
            )
        remaining -= len(page_items)
        page_token = data.get("nextPageToken")
        if not page_token or not page_items:
            break
    return items


def parse_iso8601_duration(value: str | None) -> int:
    if not value:
        return 0
    match = re.fullmatch(
        r"P(?:(?P<days>\d+)D)?T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?",
        value,
    )
    if not match:
        return 0
    parts = {key: int(number or 0) for key, number in match.groupdict().items()}
    return parts["days"] * 86400 + parts["hours"] * 3600 + parts["minutes"] * 60 + parts["seconds"]


def enrich_youtube_items(
    candidates: list[dict[str, Any]], api: YouTubeDataAPI
) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    video_ids = list(dict.fromkeys(item["_video_id"] for item in candidates))
    for start in range(0, len(video_ids), 50):
        batch = video_ids[start : start + 50]
        data = api.get(
            "videos",
            part="snippet,contentDetails,statistics",
            id=",".join(batch),
            fields=(
                "items(id,snippet(title,description,channelTitle,publishedAt),"
                "contentDetails(duration,caption),statistics(viewCount,likeCount,commentCount))"
            ),
        )
        by_id.update({item["id"]: item for item in data.get("items") or [] if item.get("id")})

    enriched: list[dict[str, Any]] = []
    for candidate in candidates:
        detail = by_id.get(candidate["_video_id"])
        if not detail:
            continue
        snippet = detail.get("snippet") or {}
        content = detail.get("contentDetails") or {}
        stats = detail.get("statistics") or {}
        duration = parse_iso8601_duration(content.get("duration"))
        if candidate.get("_min_duration", 0) and duration < candidate["_min_duration"]:
            continue
        item = {key: value for key, value in candidate.items() if not key.startswith("_")}
        item.update(
            {
                "source_name": snippet.get("channelTitle") or item["source_name"],
                "title": snippet.get("title") or item["title"],
                "original_title": snippet.get("title") or item["original_title"],
                "description": snippet.get("description") or item["description"],
                "duration": duration,
                "view_count": _optional_int(stats.get("viewCount")),
                "like_count": _optional_int(stats.get("likeCount")),
                "comment_count": _optional_int(stats.get("commentCount")),
                "caption_available": content.get("caption") == "true",
            }
        )
        enriched.append(item)
    return enriched


def _optional_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def video_url_from_entry(entry: dict[str, Any]) -> str | None:
    url = entry.get("webpage_url") or entry.get("url")
    if url and url.startswith("http"):
        return url
    video_id = entry.get("id")
    return f"https://www.youtube.com/watch?v={video_id}" if video_id else None


def fetch_youtube_source_ytdlp(
    source: dict[str, Any],
    start_utc: datetime,
    end_utc: datetime,
    scan_limit: int,
    cookies: str | None,
) -> list[dict[str, Any]]:
    from yt_dlp import YoutubeDL

    flat_options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "playlistend": scan_limit,
        "lazy_playlist": True,
        "skip_download": True,
        "socket_timeout": 15,
        "retries": 1,
        "extractor_retries": 1,
        "ignoreerrors": True,
    }
    detail_options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "socket_timeout": 15,
        "retries": 1,
        "extractor_retries": 1,
        "ignoreerrors": True,
    }
    if cookies:
        flat_options["cookiefile"] = cookies
        detail_options["cookiefile"] = cookies
    try:
        with YoutubeDL(flat_options) as downloader:
            info = downloader.extract_info(source["url"], download=False) or {}
            entries = [entry for entry in (info.get("entries") or []) if entry]
    except Exception as exc:
        raise SourceFetchError(str(exc)) from exc

    items: list[dict[str, Any]] = []
    with YoutubeDL(detail_options) as downloader:
        for entry in entries:
            url = video_url_from_entry(entry)
            if not url:
                continue
            try:
                detail = downloader.extract_info(url, download=False) or entry
            except Exception:
                continue
            duration = detail.get("duration") or entry.get("duration") or 0
            if source.get("min_duration", 0) and duration < source["min_duration"]:
                continue
            published = parse_datetime(
                detail.get("timestamp") or detail.get("upload_date") or detail.get("release_timestamp")
            )
            if not in_window(published, start_utc, end_utc):
                continue
            items.append(
                {
                    "platform": "youtube",
                    "category": source["category"],
                    "source_name": detail.get("channel") or detail.get("uploader") or source["name"],
                    "source_url": source["url"],
                    "title": detail.get("title") or entry.get("title") or "",
                    "original_title": detail.get("title") or entry.get("title") or "",
                    "url": detail.get("webpage_url") or url,
                    "published_at": published.isoformat(),
                    "duration": duration,
                    "description": detail.get("description") or "",
                    "view_count": detail.get("view_count"),
                    "like_count": detail.get("like_count"),
                    "comment_count": detail.get("comment_count"),
                    "chapters": detail.get("chapters") or [],
                    "subtitles": sorted((detail.get("subtitles") or {}).keys()),
                    "automatic_captions": sorted((detail.get("automatic_captions") or {}).keys()),
                }
            )
    return items


def deduplicate_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduplicated: dict[str, dict[str, Any]] = {}
    for item in items:
        key = item.get("url") or f"{item.get('platform')}:{item.get('title')}:{item.get('published_at')}"
        deduplicated.setdefault(key, item)
    return list(deduplicated.values())


def retain_failed_source_items(
    existing: list[dict[str, Any]],
    failed_urls: set[str],
    start_utc: datetime,
    end_utc: datetime,
) -> list[dict[str, Any]]:
    retained: list[dict[str, Any]] = []
    for item in existing:
        if item.get("source_url") not in failed_urls:
            continue
        if in_window(parse_datetime(item.get("published_at")), start_utc, end_utc):
            retained.append(item)
    return retained


def main() -> int:
    args = parse_args()
    window_end = report_date(args.date)
    end_utc = window_end.astimezone(timezone.utc)
    start_utc = end_utc - timedelta(hours=args.lookback_hours)
    sources = parse_category_file(CONFIG_DIR / "sources_by_category.md")
    cookies = "cookies.txt" if Path("cookies.txt").exists() else None
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    backend = args.youtube_backend
    if backend == "auto":
        backend = "api" if api_key else "yt-dlp"
    if backend == "api" and not api_key:
        print("YOUTUBE_API_KEY is required for --youtube-backend api")
        return 2

    out_json = (
        Path(args.output_json)
        if args.output_json
        else REPORTS_DIR / f"daily_items_{window_end:%Y-%m-%d}.json"
    )
    out_urls = Path(args.output_urls)
    manifest_path = (
        Path(args.manifest_json)
        if args.manifest_json
        else out_json.with_name(f"{out_json.stem}.manifest.json")
    )
    cache_path = Path(args.channel_cache)
    channel_cache: dict[str, Any] = load_json(cache_path, {})
    api = YouTubeDataAPI(api_key, args.youtube_api_timeout) if backend == "api" else None

    all_items: list[dict[str, Any]] = []
    youtube_candidates: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    successful_sources = 0
    youtube_sources = [source for source in sources if source["platform"] == "youtube"]

    print(f"Window: {start_utc.isoformat()} <= published_at < {end_utc.isoformat()}")
    print(f"YouTube backend: {backend}")
    for source in sources:
        try:
            if source["platform"] == "xiaoyuzhou":
                fetched = fetch_xiaoyuzhou_source(source, start_utc, end_utc)
                all_items.extend(fetched)
            elif backend == "api":
                assert api is not None
                fetched = fetch_youtube_source_api(
                    source, start_utc, end_utc, args.youtube_scan_limit, api, channel_cache
                )
                youtube_candidates.extend(fetched)
            else:
                fetched = fetch_youtube_source_ytdlp(
                    source, start_utc, end_utc, args.youtube_scan_limit, cookies
                )
                all_items.extend(fetched)
            successful_sources += 1
            print(f"[{source['platform']}] {source['name']}: {len(fetched)} item(s)")
        except Exception as exc:
            failure = {
                "platform": source["platform"],
                "name": source["name"],
                "url": source["url"],
                "error": str(exc),
            }
            failures.append(failure)
            print(f"[{source['platform']}] {source['name']} failed: {exc}")

    if backend == "api" and youtube_candidates:
        try:
            assert api is not None
            all_items.extend(enrich_youtube_items(youtube_candidates, api))
        except Exception as exc:
            print(f"[youtube] video enrichment failed: {exc}")
            failed_youtube_urls = {failure["url"] for failure in failures}
            for source in youtube_sources:
                if source["url"] not in failed_youtube_urls:
                    failures.append(
                        {
                            "platform": "youtube",
                            "name": source["name"],
                            "url": source["url"],
                            "error": f"video enrichment failed: {exc}",
                        }
                    )

    existing = load_json(out_json, [])
    if not isinstance(existing, list):
        existing = []
    failed_urls = {failure["url"] for failure in failures}
    if failed_urls:
        retained = retain_failed_source_items(existing, failed_urls, start_utc, end_utc)
        if retained:
            print(f"Retained {len(retained)} existing item(s) for failed sources")
            all_items.extend(retained)

    all_items = deduplicate_items(all_items)
    all_items.sort(key=lambda item: item.get("published_at") or "", reverse=True)
    if backend == "api":
        atomic_write_text(cache_path, json.dumps(channel_cache, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(out_json, json.dumps(all_items, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(
        out_urls,
        "\n".join(["# Auto-generated daily extraction URLs"] + [item["url"] for item in all_items])
        + "\n",
    )

    counts: dict[str, int] = {}
    for item in all_items:
        counts[item.get("platform", "unknown")] = counts.get(item.get("platform", "unknown"), 0) + 1
    manifest = {
        "status": "complete" if not failures else "partial",
        "youtube_backend": backend,
        "window_start": start_utc.isoformat(),
        "window_end": end_utc.isoformat(),
        "source_count": len(sources),
        "successful_source_count": successful_sources,
        "failure_count": len(failures),
        "item_count": len(all_items),
        "counts_by_platform": counts,
        "failures": failures,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    print(f"Collected {len(all_items)} items: {counts}")
    print(f"Items: {out_json}")
    print(f"URLs: {out_urls}")
    print(f"Manifest: {manifest_path} ({manifest['status']})")
    return 0 if not failures or args.allow_partial else 2


if __name__ == "__main__":
    raise SystemExit(main())
