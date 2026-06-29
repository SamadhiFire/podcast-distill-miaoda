"""
历史回填 — 来源盘点 (阶段 B/C)
支持 YouTube (yt-dlp flat-playlist) 和 小宇宙 (RSS优先)
每集去重、状态持久化、可中断续跑。
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from scripts.backfill.db import get_conn

TZ_SHANGHAI = timezone(timedelta(hours=8))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

BLOCKED_ERRORS = [
    "sign in to confirm", "not a bot", "captcha",
    "requestblocked", "ipblocked", "too many requests",
]


def load_sources() -> list[dict]:
    path = ROOT / "backfill" / "config" / "sources.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data.get("sources", [])


def report_date_from_published(published_str: str) -> str:
    """按北京时间 06:00 边界计算日报日期."""
    try:
        dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return ""
    shanghai = dt.astimezone(TZ_SHANGHAI)
    adjusted = shanghai - timedelta(hours=6)
    return (adjusted + timedelta(days=1)).strftime("%Y-%m-%d")


def parse_yt_date(date_str: str) -> str | None:
    """yt-dlp upload_date (YYYYMMDD) -> ISO 8601."""
    if not date_str or len(date_str) != 8:
        return None
    try:
        dt = datetime.strptime(date_str, "%Y%m%d")
        return dt.replace(tzinfo=TZ_SHANGHAI).isoformat()
    except ValueError:
        return None


def is_blocked_error(output: str) -> bool:
    lower = output.lower()
    return any(b in lower for b in BLOCKED_ERRORS)


# ──────────────────────── YouTube inventory ────────────────────────

def _resolve_youtube_api_playlist(source: dict) -> str | None:
    """解析 uploads playlist ID (channels -> playlist)."""
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        return None

    discovery = source.get("discovery", {})
    playlist_id = discovery.get("playlist_id")
    if playlist_id:
        return playlist_id

    handle = discovery.get("handle")
    if not handle:
        return None

    # Resolve channel handle -> uploads playlist
    import requests as req
    try:
        resp = req.get(
            "https://www.googleapis.com/youtube/v3/channels",
            headers={"x-goog-api-key": api_key, "Accept": "application/json"},
            params={"part": "contentDetails", "forHandle": handle},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items") or []
        if not items:
            print(f"    无法解析 channel: {handle}")
            return None
        uploads_id = items[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
        return uploads_id
    except Exception as e:
        print(f"    Channel 解析失败: {e}")
        return None


def inventory_youtube_api(source: dict, conn) -> dict | None:
    """使用 YouTube Data API v3 盘点."""
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        return None

    playlist_id = _resolve_youtube_api_playlist(source)
    if not playlist_id:
        return None

    source_id = source["source_id"]
    min_dur = source.get("min_duration_seconds", 0)
    cur = conn.cursor()

    print(f"    使用 YouTube Data API ...")

    import requests as req
    items_seen = set()
    new_items = 0
    pages_fetched = 0
    page_token = None
    oldest_date = None
    newest_date = None

    while True:
        params: dict = {
            "part": "snippet,contentDetails",
            "playlistId": playlist_id,
            "maxResults": 50,
            "fields": "nextPageToken,items(contentDetails(videoId,videoPublishedAt),snippet(title,description,channelTitle))",
        }
        if page_token:
            params["pageToken"] = page_token

        try:
            resp = req.get(
                "https://www.googleapis.com/youtube/v3/playlistItems",
                headers={"x-goog-api-key": api_key, "Accept": "application/json"},
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"    API 请求失败: {e}")
            return {"status": "retryable", "error": str(e)[:200]}

        pages_fetched += 1
        page_items = data.get("items") or []
        print(f"    page {pages_fetched}: {len(page_items)} items")

        for pi in page_items:
            details = pi.get("contentDetails") or {}
            snippet = pi.get("snippet") or {}
            video_id = details.get("videoId")
            if not video_id or video_id in items_seen:
                continue

            title = snippet.get("title", video_id)
            published_raw = details.get("videoPublishedAt", "")
            channel_title = snippet.get("channelTitle", "")

            # Parse date
            try:
                dt = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
                published_iso = dt.isoformat()
                upload_date = dt.astimezone(TZ_SHANGHAI).strftime("%Y%m%d")
            except ValueError:
                published_iso = published_raw
                upload_date = ""

            report_dt = report_date_from_published(published_iso)
            item_id = f"youtube:{video_id}"

            cur.execute(
                """INSERT OR IGNORE INTO items
                (item_id, platform, platform_id, source_id, category, title, url,
                 published_at, report_date, duration_seconds, language)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (item_id, "youtube", video_id, source_id,
                 source["category"], title,
                 f"https://www.youtube.com/watch?v={video_id}",
                 published_iso, report_dt, 0,
                 "en" if channel_title.isascii() else "auto"),
            )
            if cur.rowcount > 0:
                new_items += 1
            items_seen.add(video_id)

            if upload_date:
                if not oldest_date or upload_date < oldest_date:
                    oldest_date = upload_date
                if not newest_date or upload_date > newest_date:
                    newest_date = upload_date

        page_token = data.get("nextPageToken")
        if not page_token or not page_items:
            break

    conn.commit()

    # Enrich with video details (durations)
    video_ids = list(items_seen)
    if video_ids:
        _enrich_durations(video_ids, conn, source_id)

    cur.execute("SELECT COUNT(*) FROM items WHERE source_id=?", (source_id,))
    total = cur.fetchone()[0]

    cur.execute(
        """UPDATE sources SET status=?, items_in_range=?, pages_fetched=?,
           oldest_seen=?, newest_seen=?, stop_reason=?, updated_at=datetime('now')
           WHERE source_id=?""",
        ("complete", total, pages_fetched, oldest_date, newest_date,
         f"api_paginated_{pages_fetched}p", source_id),
    )
    conn.commit()

    print(f"    new={new_items} total={total} pages={pages_fetched} oldest={oldest_date} newest={newest_date}")
    return {"status": "complete", "items": total, "new": new_items,
            "oldest": oldest_date, "newest": newest_date, "pages": pages_fetched}


def _enrich_durations(video_ids: list, conn, source_id: str):
    """批量获取 video durations."""
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        return
    import requests as req
    cur = conn.cursor()
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        try:
            resp = req.get(
                "https://www.googleapis.com/youtube/v3/videos",
                headers={"x-goog-api-key": api_key, "Accept": "application/json"},
                params={"part": "contentDetails", "id": ",".join(batch)},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            for v in data.get("items") or []:
                vid = v["id"]
                dur_str = v.get("contentDetails", {}).get("duration", "PT0S")
                dur = _parse_duration(dur_str)
                cur.execute(
                    "UPDATE items SET duration_seconds=? WHERE item_id=?",
                    (dur, f"youtube:{vid}"),
                )
        except Exception as e:
            print(f"    duration enrich failed: {e}")
    conn.commit()


def _parse_duration(pt_str: str) -> int:
    """PT1H2M3S -> seconds."""
    import re
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", pt_str)
    if not m:
        return 0
    d, h, mi, s = (int(v or 0) for v in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def inventory_youtube_ytdlp(source: dict, conn) -> dict:
    """yt-dlp 备选方案."""
    source_id = source["source_id"]
    playlist_id = source.get("discovery", {}).get("playlist_id")
    handle = source.get("discovery", {}).get("handle")

    if playlist_id:
        url = f"https://www.youtube.com/playlist?list={playlist_id}"
    elif handle:
        url = f"https://www.youtube.com/{handle}/videos"
    else:
        return {"status": "terminal", "error": "no playlist_id or handle"}

    print(f"    URL: {url}")
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--flat-playlist", "--playlist-end", "50",
        "--print", "%(id)s\t%(title)s\t%(duration)s\t%(upload_date)s",
        "--ignore-errors", url,
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600,
            encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired:
        return {"status": "retryable", "error": "yt-dlp timeout"}

    if result.returncode != 0 and not result.stdout.strip():
        return {"status": "retryable", "error": (result.stderr or "")[:200]}

    cur = conn.cursor()
    items_seen = set()
    new_items = 0
    oldest_date = None
    newest_date = None

    for line in result.stdout.strip().split("\n"):
        parts = line.strip().split("\t")
        if len(parts) < 4:
            continue
        video_id, title, dur_raw, upload_date = parts[0], parts[1], parts[2], parts[3]
        if not video_id or video_id in items_seen:
            continue
        try:
            duration = int(float(dur_raw)) if dur_raw and dur_raw != "NA" else 0
        except ValueError:
            duration = 0

        published_iso = parse_yt_date(upload_date) or datetime.now(TZ_SHANGHAI).isoformat()
        report_dt = report_date_from_published(published_iso)
        item_id = f"youtube:{video_id}"

        cur.execute(
            """INSERT OR IGNORE INTO items
            (item_id, platform, platform_id, source_id, category, title, url,
             published_at, report_date, duration_seconds, language)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (item_id, "youtube", video_id, source_id,
             source["category"], title or video_id,
             f"https://www.youtube.com/watch?v={video_id}",
             published_iso, report_dt, duration, "en"),
        )
        if cur.rowcount > 0:
            new_items += 1
        items_seen.add(video_id)

        if upload_date and upload_date != "NA":
            if not oldest_date or upload_date < oldest_date:
                oldest_date = upload_date
            if not newest_date or upload_date > newest_date:
                newest_date = upload_date

    cur.execute("SELECT COUNT(*) FROM items WHERE source_id=?", (source_id,))
    total = cur.fetchone()[0]
    cur.execute(
        """UPDATE sources SET status=?, items_in_range=?, pages_fetched=?,
           oldest_seen=?, newest_seen=?, stop_reason=?, updated_at=datetime('now')
           WHERE source_id=?""",
        ("complete", total, 1, oldest_date, newest_date, "ytdlp_flat", source_id),
    )
    conn.commit()
    print(f"    new={new_items} total={total} oldest={oldest_date} newest={newest_date}")
    return {"status": "complete", "items": total, "new": new_items}


def inventory_youtube(source: dict, coverage_start: str, conn) -> dict:
    """YouTube 盘点: API 优先，yt-dlp 备选."""
    source_id = source["source_id"]
    cur = conn.cursor()
    cur.execute("SELECT status, items_in_range FROM sources WHERE source_id=?", (source_id,))
    row = cur.fetchone()
    if row and row["status"] == "complete":
        return {"status": "complete", "items": row["items_in_range"]}

    if row and row["status"] == "running":
        print(f"  [CONTINUE] {source_id} 续跑")

    cur.execute(
        "INSERT OR REPLACE INTO sources(source_id, platform, category, name, status) VALUES(?,?,?,?,?)",
        (source_id, source["platform"], source["category"], source["name"], "running"),
    )
    conn.commit()

    print(f"\n  [{source_id}] 盘点: {source['name']}")

    # 1. 尝试 API
    result = inventory_youtube_api(source, conn)
    if result and result["status"] == "complete":
        return result

    # 2. API 失败，试 yt-dlp
    if result:
        print(f"    API 失败: {result.get('error', '')}, 回退 yt-dlp")
    else:
        print(f"    YOUTUBE_API_KEY 未设置，使用 yt-dlp")

    return inventory_youtube_ytdlp(source, conn)


# ──────────────────────── Xiaoyuzhou inventory ────────────────────────

def inventory_xiaoyuzhou(source: dict, coverage_start: str, conn) -> dict:
    """用 RSS (优先) 或网页解析盘点小宇宙播客."""
    source_id = source["source_id"]
    url = source["source_url"]

    cur = conn.cursor()
    cur.execute("SELECT status, items_in_range, stop_reason FROM sources WHERE source_id=?", (source_id,))
    row = cur.fetchone()
    if row and row["status"] == "complete":
        return {"status": "complete", "items": row["items_in_range"]}

    cur.execute(
        "INSERT OR REPLACE INTO sources(source_id, platform, category, name, status) VALUES(?,?,?,?,?)",
        (source_id, source["platform"], source["category"], source["name"], "running"),
    )
    conn.commit()

    print(f"\n  [{source_id}] 盘点: {source['name']}")
    print(f"    URL: {url}")

    # 从 URL 提取 podcast ID
    podcast_id_match = re.search(r"/podcast/([a-f0-9]+)", url)
    podcast_id = podcast_id_match.group(1) if podcast_id_match else None
    if not podcast_id:
        return {"status": "terminal", "error": "cannot extract podcast_id"}

    # 尝试 RSS
    items = _fetch_xiaoyuzhou_rss(source_id, podcast_id)
    if not items:
        print(f"    RSS 失败，回退到网页解析...")
        items = _fetch_xiaoyuzhou_web(source, source_id, podcast_id, url)

    if not items:
        return {"status": "retryable", "error": "no items fetched"}

    # 写入数据库
    new_count = 0
    items_seen = set()
    for item in items:
        episode_id = item.get("eid") or item.get("guid")
        if not episode_id or episode_id in items_seen:
            continue

        published_iso = item.get("published_at", "")
        dur = item.get("duration", 0)
        title = item.get("title", "")
        episode_url = item.get("url", "")

        item_id = f"xiaoyuzhou:{episode_id}"
        report_dt = report_date_from_published(published_iso)

        # 提取纯数字 duration
        if isinstance(dur, str):
            try:
                dur = int(float(dur))
            except ValueError:
                dur = 0

        cur.execute(
            """INSERT OR IGNORE INTO items
            (item_id, platform, platform_id, source_id, category, title, url,
             published_at, report_date, duration_seconds, language)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (item_id, "xiaoyuzhou", episode_id, source_id,
             source["category"], title, episode_url,
             published_iso, report_dt, dur, "zh"),
        )
        if cur.rowcount > 0:
            new_count += 1
        items_seen.add(episode_id)

    cur.execute("SELECT COUNT(*) FROM items WHERE source_id=?", (source_id,))
    total = cur.fetchone()[0]

    oldest = min((i.get("published_at", "") for i in items if i.get("published_at")), default=None)
    newest = max((i.get("published_at", "") for i in items if i.get("published_at")), default=None)

    pages = len(items) // 20 + 1  # estimate

    cur.execute(
        """UPDATE sources SET status=?, items_in_range=?, pages_fetched=?,
           oldest_seen=?, newest_seen=?, stop_reason=?, updated_at=datetime('now')
           WHERE source_id=?""",
        ("complete", total, pages, oldest, newest, "fetch_complete", source_id),
    )
    conn.commit()

    print(f"    new={new_count} total={total} oldest={oldest} newest={newest}")
    return {"status": "complete", "items": total, "new": new_count}


def _fetch_xiaoyuzhou_rss(source_id: str, podcast_id: str) -> list[dict]:
    """尝试小宇宙 RSS feed."""
    # Common RSS patterns for Xiaoyuzhou
    rss_urls = [
        f"https://www.xiaoyuzhoufm.com/podcast/{podcast_id}/rss.xml",
        f"https://www.xiaoyuzhoufm.com/podcast/{podcast_id}",
        f"https://feed.xiaoyuzhoufm.com/podcasts/{podcast_id}/episodes",
    ]
    for rss_url in rss_urls:
        try:
            print(f"    尝试 RSS: {rss_url}")
            resp = requests.get(rss_url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            text = resp.text

            # Check if it's XML/RSS
            if text.strip().startswith("<?xml") or "<rss" in text[:500]:
                return _parse_rss(text)
            if "<channel>" in text[:1000]:
                return _parse_rss(text)

            # Maybe it's JSON API
            try:
                data = resp.json()
                return _parse_xiaoyuzhou_json(data)
            except (json.JSONDecodeError, ValueError):
                pass
        except Exception as e:
            print(f"    RSS 尝试失败: {e}")
            continue
    return []


def _parse_rss(xml_text: str) -> list[dict]:
    """解析 RSS/XML 获取节目列表."""
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    ns = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"}

    items = []
    for item_el in root.iter("item"):
        title_el = item_el.find("title")
        link_el = item_el.find("link")
        pubdate_el = item_el.find("pubDate")
        guid_el = item_el.find("guid")
        dur_el = item_el.find("itunes:duration", ns)

        title = title_el.text if title_el is not None else ""
        link = link_el.text if link_el is not None else ""

        # Extract eid from link
        eid_match = re.search(r"/episode/([a-f0-9]+)", link) if link else None
        eid = eid_match.group(1) if eid_match else (guid_el.text if guid_el is not None else "")

        pubdate = pubdate_el.text if pubdate_el is not None else ""
        duration_str = dur_el.text if dur_el is not None else "0"

        # Parse duration
        duration = 0
        try:
            parts = duration_str.split(":")
            if len(parts) == 3:
                duration = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                duration = int(parts[0]) * 60 + int(parts[1])
            else:
                duration = int(float(duration_str))
        except (ValueError, AttributeError):
            duration = 0

        # Parse pubDate to ISO
        published_at = ""
        if pubdate:
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(pubdate)
                published_at = dt.isoformat()
            except Exception:
                published_at = pubdate

        items.append({
            "eid": eid,
            "guid": guid_el.text if guid_el is not None else "",
            "title": title,
            "url": link or f"https://www.xiaoyuzhoufm.com/episode/{eid}",
            "published_at": published_at,
            "duration": duration,
        })

    return items


def _parse_xiaoyuzhou_json(data: dict) -> list[dict]:
    """解析小宇宙 JSON API 响应."""
    items = []
    entries = data.get("data") or data.get("items") or data.get("episodes") or []
    if isinstance(data, list):
        entries = data

    for ep in entries:
        if not isinstance(ep, dict):
            continue
        eid = ep.get("eid") or ep.get("id") or ""
        pub_date = ep.get("pubDate") or ep.get("publishedAt") or ep.get("pub_date") or ""
        dur = ep.get("duration") or ep.get("durationInSeconds") or 0

        # Parse pubDate
        published_at = ""
        if isinstance(pub_date, (int, float)):
            published_at = datetime.fromtimestamp(pub_date, timezone.utc).isoformat()
        elif isinstance(pub_date, str):
            try:
                dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                published_at = dt.isoformat()
            except ValueError:
                published_at = pub_date

        items.append({
            "eid": eid,
            "title": ep.get("title", ""),
            "url": ep.get("url") or f"https://www.xiaoyuzhoufm.com/episode/{eid}",
            "published_at": published_at,
            "duration": dur,
        })
    return items


def _fetch_xiaoyuzhou_web(source: dict, source_id: str, podcast_id: str, url: str) -> list[dict]:
    """网页解析 (__NEXT_DATA__) 作为兜底."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        html = resp.content.decode("utf-8", errors="replace")

        match = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        if not match:
            print(f"    __NEXT_DATA__ not found")
            return []

        data = json.loads(match.group(1))
        podcast = data.get("props", {}).get("pageProps", {}).get("podcast") or {}
        episodes = podcast.get("episodes") or []

        items = []
        for ep in episodes:
            eid = ep.get("eid") or ""
            pub_date = ep.get("pubDate") or ""
            if isinstance(pub_date, (int, float)):
                published_at = datetime.fromtimestamp(pub_date, timezone.utc).isoformat()
            else:
                published_at = str(pub_date)

            items.append({
                "eid": eid,
                "title": ep.get("title", ""),
                "url": f"https://www.xiaoyuzhoufm.com/episode/{eid}",
                "published_at": published_at,
                "duration": ep.get("duration", 0),
            })
        return items
    except Exception as e:
        print(f"    网页解析失败: {e}")
        return []


# ──────────────────────── CLI ────────────────────────

def cmd_inventory(source_id: str = None, lookback_days: int = 90):
    """盘点来源的节目清单."""
    import sqlite3
    sources = load_sources()
    conn = get_conn()

    if source_id:
        sources = [s for s in sources if s["source_id"] == source_id]
        if not sources:
            print(f"未找到来源: {source_id}")
            conn.close()
            return 1

    print("=" * 60)
    print(f"  Backfill 盘点 (lookback >= {lookback_days} days)")
    print("=" * 60)

    results = {}
    for src in sources:
        if not src.get("enabled", True):
            continue
        try:
            if src["platform"] == "youtube":
                r = inventory_youtube(src, "", conn)
            else:
                r = inventory_xiaoyuzhou(src, "", conn)
            results[src["source_id"]] = r

            # Check for block
            if r.get("status") == "blocked":
                print(f"\n  [BLOCKED] {src['source_id']} 被拦截，暂停 YouTube 队列")
                if src["platform"] == "youtube":
                    break
        except Exception as e:
            print(f"  [ERROR] {src['source_id']}: {e}")
            results[src["source_id"]] = {"status": "retryable", "error": str(e)}

    # Summary
    print("\n" + "=" * 60)
    print("  Summary:")
    for sid, r in results.items():
        status = r.get("status", "unknown")
        items = r.get("items", 0)
        err = r.get("error", "")
        marker = "[OK]" if status == "complete" else f"[{status}]"
        print(f"  {marker} {sid}: {items} items" + (f" ({err})" if err else ""))
    print("=" * 60)

    conn.close()
    return 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="盘点来源节目清单")
    parser.add_argument("--source", help="source_id (不指定则全部)")
    parser.add_argument("--lookback-days", type=int, default=90)
    args = parser.parse_args()
    raise SystemExit(cmd_inventory(args.source, args.lookback_days))
