"""
历史回填 — 字幕提取批处理 (阶段 B/D)
从 SQLite 取 pending 任务，提取字幕，更新状态。
可中断续跑：在同一节目上最多重试 max_attempts 次。
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from scripts.backfill.db import get_conn

ITEMS_DIR = ROOT / "backfill" / "items"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def classify_error(message: str) -> tuple[str, bool]:
    """返回 (error_type, retryable)."""
    text = (message or "").lower()
    if "sign in to confirm" in text or "not a bot" in text or "captcha" in text:
        return "youtube_bot_check", True
    if "429" in text or "too many requests" in text:
        return "rate_limited", True
    if "403" in text or "requestblocked" in text:
        return "blocked", True
    if "timeout" in text or "timed out" in text:
        return "timeout", True
    if "transcriptsdisabled" in text:
        return "transcripts_disabled", False
    if "notranscriptfound" in text:
        return "no_transcript", False
    if "video unavailable" in text or "private" in text:
        return "video_unavailable", False
    return "unknown", True


def extract_youtube(item: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    """使用 yt-dlp 提取 YouTube 字幕."""
    video_id = item["platform_id"]
    url = item["url"]
    lang = item.get("language", "en")

    print(f"    字幕: yt-dlp {video_id}")

    vtt_path = output_dir / "transcript.vtt"
    txt_path = output_dir / "transcript.txt"

    # Write metadata
    meta = {
        "schema_version": 1,
        "item_id": item["item_id"],
        "platform": "youtube",
        "platform_id": video_id,
        "source_id": item["source_id"],
        "title": item["title"],
        "url": url,
        "published_at": item["published_at"],
        "report_date": item["report_date"],
        "duration_seconds": item["duration_seconds"],
        "language": lang,
    }
    (output_dir / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # Try yt-dlp --write-auto-subs
    lang_arg = lang[:2] if lang else "en"
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--skip-download",
        "--write-auto-subs",
        "--sub-lang", lang_arg,
        "--convert-subs", "vtt",
        "-o", str(output_dir / "raw.%(ext)s"),
        url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                                encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return {"status": "retryable", "error_type": "timeout", "error_message": "yt-dlp timeout"}

    # Find the downloaded VTT
    vtt_files = sorted(output_dir.glob("*.vtt"))
    if not vtt_files:
        # try --write-subs (manual captions)
        cmd2 = [
            sys.executable, "-m", "yt_dlp",
            "--skip-download", "--write-subs",
            "--sub-lang", lang_arg, "--convert-subs", "vtt",
            "-o", str(output_dir / "raw-manual.%(ext)s"), url,
        ]
        try:
            subprocess.run(cmd2, capture_output=True, text=True, timeout=120,
                           encoding="utf-8", errors="replace")
        except Exception:
            pass
        vtt_files = sorted(output_dir.glob("*.vtt"))

    if vtt_files:
        # Rename to standard name
        raw_vtt = vtt_files[0]
        content = raw_vtt.read_text(encoding="utf-8", errors="replace")
        vtt_path.write_text(content, encoding="utf-8", newline="\n")
        # Clean raw files
        for f in output_dir.glob("raw*"):
            if f != vtt_path:
                f.unlink(missing_ok=True)

        # Generate plain text
        text_lines = _vtt_to_text(content)
        txt_path.write_text("\n".join(text_lines), encoding="utf-8", newline="\n")

        # Quality check
        text_chars = sum(len(line) for line in text_lines)
        duration = item["duration_seconds"]
        coverage = _estimate_coverage(content, duration) if duration > 0 else 1.0

        return {
            "status": "success",
            "method": "yt-dlp",
            "language": lang,
            "text_chars": text_chars,
            "coverage_ratio": coverage,
            "sha256": sha256_hex(content),
        }

    # Check for block/error
    stderr = result.stderr or ""
    error_type, retryable = classify_error(stderr)
    if not retryable:
        return {"status": "blocked", "error_type": error_type, "error_message": stderr[:300]}

    return {
        "status": "retryable",
        "error_type": error_type,
        "error_message": stderr[:300] or "no captions found",
    }


def _vtt_to_text(vtt_content: str) -> list[str]:
    """VTT -> 纯文本行 (去重)."""
    lines = []
    prev = None
    for line in vtt_content.splitlines():
        line = line.strip()
        if not line or "-->" in line or line == "WEBVTT":
            continue
        if re.fullmatch(r"\d+", line):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        line = re.sub(r"\{[^}]*\}", "", line)
        line = re.sub(r"\s+", " ", line).strip()
        if line and line != prev:
            lines.append(line)
            prev = line
    return lines


def _estimate_coverage(vtt_content: str, total_seconds: int) -> float:
    """从 VTT 估算覆盖率."""
    if total_seconds <= 0:
        return 1.0
    last_ts = 0
    for line in vtt_content.splitlines():
        m = re.match(r"(\d+):(\d+):(\d+)\.(\d+)\s*-->", line)
        if m:
            h, mi, s, ms = int(m[1]), int(m[2]), int(m[3]), int(m[4])
            ts = h * 3600 + mi * 60 + s + ms / 1000.0
            last_ts = max(last_ts, ts)
    return min(1.0, last_ts / total_seconds) if total_seconds > 0 else 1.0


def extract_xiaoyuzhou(item: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    """提取小宇宙字幕 (官方 API / ASR)."""
    eid = item["platform_id"]
    url = item["url"]

    print(f"    字幕: xiaoyuzhou {eid}")

    # Write metadata
    meta = {
        "schema_version": 1,
        "item_id": item["item_id"],
        "platform": "xiaoyuzhou",
        "platform_id": eid,
        "source_id": item["source_id"],
        "title": item["title"],
        "url": url,
        "published_at": item["published_at"],
        "report_date": item["report_date"],
        "duration_seconds": item["duration_seconds"],
        "language": "zh",
    }
    (output_dir / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # Try official transcript API
    token = os.getenv("XIAOYUZHOU_ACCESS_TOKEN") or os.getenv("X_JIKE_ACCESS_TOKEN") or ""
    if token:
        result = _try_official_transcript(eid, item, output_dir)
        if result["status"] == "success":
            return result
        print(f"    官方 API 失败: {result.get('error_message', '')[:100]}")

    # Check existing official data in page
    result = _try_webpage_transcript(url, eid, output_dir)
    if result:
        return result

    # ASR not configured
    return {"status": "needs_asr", "error_type": "needs_asr",
            "error_message": "no transcript available, ASR not configured"}


def _try_official_transcript(eid: str, item: dict, output_dir: Path) -> dict:
    """小宇宙官方逐字稿 API."""
    token = os.getenv("XIAOYUZHOU_ACCESS_TOKEN") or os.getenv("X_JIKE_ACCESS_TOKEN") or ""

    import requests as req
    headers = {
        **HEADERS,
        "x-jike-access-token": token,
        "Content-Type": "application/json",
    }
    payloads = [
        {"eid": eid, "version": "release"},
        {"eid": eid, "version": "asr"},
    ]
    for payload in payloads:
        try:
            resp = req.post(
                "https://podcast-api.midway.run/management/episode-transcript/get",
                headers=headers, json=payload, timeout=30,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            sentences = _find_sentences(data)
            if not sentences:
                continue
            _write_srt_vtt_txt(sentences, output_dir)
            content = (output_dir / "transcript.txt").read_text(encoding="utf-8")
            return {
                "status": "success",
                "method": "official_api",
                "language": "zh",
                "text_chars": len(content),
                "coverage_ratio": 1.0,
                "sha256": sha256_hex(content),
            }
        except Exception:
            continue
    return {"status": "retryable", "error_type": "transcript_fetch_failed",
            "error_message": "official API returned no sentences"}


def _try_webpage_transcript(url: str, eid: str, output_dir: Path) -> dict | None:
    """从网页 __NEXT_DATA__ 中读 transcriptMediaId."""
    import requests as req
    try:
        resp = req.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        html = resp.content.decode("utf-8", errors="replace")
        match = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        if not match:
            return None
        data = json.loads(match.group(1))
        episode = data.get("props", {}).get("pageProps", {}).get("episode") or {}
        transcript_data = episode.get("transcript") or {}
        sentences = transcript_data.get("sentences") or []
        if not sentences:
            return None
        _write_srt_vtt_txt(sentences, output_dir)
        content = (output_dir / "transcript.txt").read_text(encoding="utf-8")
        return {
            "status": "success",
            "method": "webpage_embedded",
            "language": "zh",
            "text_chars": len(content),
            "coverage_ratio": 1.0,
            "sha256": sha256_hex(content),
        }
    except Exception:
        return None


def _find_sentences(obj: Any) -> list | None:
    """递归查找 sentences 列表."""
    if isinstance(obj, dict):
        s = obj.get("sentences")
        if isinstance(s, list) and s:
            return s
        for v in obj.values():
            r = _find_sentences(v)
            if r:
                return r
    elif isinstance(obj, list):
        if obj and all(isinstance(x, dict) and "text" in x for x in obj):
            return obj
        for v in obj:
            r = _find_sentences(v)
            if r:
                return r
    return None


def _write_srt_vtt_txt(sentences: list, output_dir: Path):
    """写入 SRT + TXT."""
    srt_lines = []
    txt_lines = []
    prev_text = None

    for i, seg in enumerate(sentences):
        text = str(seg.get("text", "")).strip()
        if not text:
            continue

        # Time
        if "startMs" in seg:
            start = float(seg["startMs"]) / 1000.0
            end = float(seg.get("endMs", seg["startMs"] + 1000)) / 1000.0
        elif "start" in seg:
            start = float(seg["start"])
            end = float(seg.get("end", start + 1))
        else:
            continue

        srt_lines.append(str(i + 1))
        srt_lines.append(f"{_fmt_srt(start)} --> {_fmt_srt(end)}")
        srt_lines.append(text)
        srt_lines.append("")

        if text != prev_text:
            txt_lines.append(text)
            prev_text = text

    (output_dir / "transcript.srt").write_text("\n".join(srt_lines), encoding="utf-8", newline="\n")
    (output_dir / "transcript.txt").write_text("\n".join(txt_lines), encoding="utf-8", newline="\n")


def _fmt_srt(seconds: float) -> str:
    s = max(0, float(seconds))
    ms = int(round(s * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    secs, ms_rem = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{secs:02d},{ms_rem:03d}"


# ──────────────────────── 主逻辑 ────────────────────────

def cmd_extract(source_id: str, limit: int = 3, max_attempts: int = 3):
    """提取指定来源的 pending 节目字幕."""
    conn = get_conn()
    cur = conn.cursor()

    # 获取 pending items
    cur.execute(
        """SELECT i.* FROM items i
           LEFT JOIN extractions e ON i.item_id = e.item_id
           WHERE i.source_id = ?
             AND (e.status IS NULL OR e.status = 'pending' OR (e.status = 'retryable' AND e.attempts < ?))
           ORDER BY i.published_at DESC
           LIMIT ?""",
        (source_id, max_attempts, limit),
    )
    items = cur.fetchall()

    if not items:
        print(f"[{source_id}] 没有待提取的节目")
        conn.close()
        return 0

    print("=" * 60)
    print(f"  字幕提取: {source_id} (limit={limit})")
    print("=" * 60)

    results = []
    for item in items:
        item_dict = dict(item)
        item_id = item_dict["item_id"]
        platform = item_dict["platform"]

        # Skip if already successful
        cur.execute("SELECT status FROM extractions WHERE item_id=? AND status='success'", (item_id,))
        if cur.fetchone():
            print(f"  [SKIP] {item_id} 已完成")
            continue

        # Check attempts
        cur.execute("SELECT attempts FROM extractions WHERE item_id=?", (item_id,))
        row = cur.fetchone()
        attempts = row["attempts"] if row else 0

        if attempts >= max_attempts:
            cur.execute(
                "UPDATE extractions SET status='blocked', error_type='max_retries', error_message=? WHERE item_id=?",
                (f"exceeded {max_attempts} attempts", item_id),
            )
            conn.commit()
            print(f"  [TERMINAL] {item_id} 超过最大重试次数")
            continue

        # Create output dir
        if platform == "youtube":
            vid = item_dict["platform_id"]
            output_dir = ITEMS_DIR / "youtube" / vid
        else:
            eid = item_dict["platform_id"]
            output_dir = ITEMS_DIR / "xiaoyuzhou" / eid
        output_dir.mkdir(parents=True, exist_ok=True)

        # Insert/update extraction record
        cur.execute(
            """INSERT OR REPLACE INTO extractions(item_id, status, attempts)
               VALUES(?, 'running', ?)""",
            (item_id, attempts + 1),
        )
        conn.commit()

        # Extract
        try:
            if platform == "youtube":
                r = extract_youtube(item_dict, output_dir)
                time.sleep(2)  # rate-limit
            else:
                r = extract_xiaoyuzhou(item_dict, output_dir)
        except Exception as e:
            r = {"status": "retryable", "error_type": "exception", "error_message": str(e)}

        # Write extraction.json
        extraction_record = {
            "status": r["status"],
            "method": r.get("method", ""),
            "language": r.get("language", ""),
            "attempts": attempts + 1,
            "duration_seconds": item_dict["duration_seconds"],
            "last_timestamp_seconds": None,
            "coverage_ratio": r.get("coverage_ratio"),
            "text_chars": r.get("text_chars"),
            "sha256": r.get("sha256"),
            "completed_at": datetime.now().isoformat(),
            "error_type": r.get("error_type"),
            "error_message": r.get("error_message"),
        }
        (output_dir / "extraction.json").write_text(
            json.dumps(extraction_record, ensure_ascii=False, indent=2), encoding="utf-8")

        # Update DB
        cur.execute(
            """UPDATE extractions SET status=?, method=?, language=?, attempts=?,
               duration_seconds=?, coverage_ratio=?, text_chars=?, sha256=?,
               error_type=?, error_message=?, completed_at=datetime('now'),
               updated_at=datetime('now')
               WHERE item_id=?""",
            (r["status"], r.get("method"), r.get("language"),
             attempts + 1, item_dict["duration_seconds"],
             r.get("coverage_ratio"), r.get("text_chars"), r.get("sha256"),
             r.get("error_type"), r.get("error_message"), item_id),
        )
        conn.commit()

        marker = "[OK]" if r["status"] == "success" else f"[{r['status'].upper()}]"
        safe_title = item_dict['title'][:60].encode('ascii', errors='replace').decode('ascii')
        print(f"  {marker} {safe_title}")
        results.append(r)

    # Summary
    ok = sum(1 for r in results if r["status"] == "success")
    print(f"\n  Result: {ok}/{len(items)} success")
    conn.close()
    return 0 if ok == len(items) else 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="提取字幕批处理")
    parser.add_argument("--source", required=True, help="source_id")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--max-attempts", type=int, default=3)
    args = parser.parse_args()
    raise SystemExit(cmd_extract(args.source, args.limit, args.max_attempts))
