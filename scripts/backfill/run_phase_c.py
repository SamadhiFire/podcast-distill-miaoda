"""
阶段 C: 41 源完整盘点
只生成节目总清单+来源审计，不抓字幕。
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from scripts.backfill.db import get_conn, init_db
import yaml

TZ_SHANGHAI = timezone(timedelta(hours=8))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def load_sources():
    path = ROOT / "backfill" / "config" / "sources.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))["sources"]


def parse_yt_date(d):
    if not d or len(d) != 8:
        return None
    try:
        return datetime.strptime(d, "%Y%m%d").replace(tzinfo=TZ_SHANGHAI).isoformat()
    except:
        return None


def report_date_from_published(s):
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except:
        return ""
    sh = dt.astimezone(TZ_SHANGHAI) - timedelta(hours=6)
    return (sh + timedelta(days=1)).strftime("%Y-%m-%d")


def estimate_asr_needed(item):
    """Estimate if this item needs ASR (no native captions)."""
    platform = item.get("platform", "")
    if platform == "xiaoyuzhou":
        return True  # Most Xiaoyuzhou episodes need ASR
    if platform == "youtube":
        # About 30% of YouTube podcasts have auto-captions
        return True  # Conservative: assume all need
    return False


def inventory_youtube_simple(source, conn):
    """yt-dlp flat-playlist inventory for any YouTube source."""
    sid = source["source_id"]
    disc = source.get("discovery", {})
    playlist_id = disc.get("playlist_id")
    handle = disc.get("handle")

    if playlist_id:
        url = f"https://www.youtube.com/playlist?list={playlist_id}"
    elif handle:
        url = f"https://www.youtube.com/{handle}/videos"
    else:
        return {"status": "terminal", "error": "no handle or playlist"}

    print(f"  [{sid}] {source['name']}")
    print(f"    yt-dlp: {url[:80]}...")

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--flat-playlist",
        "--playlist-end", "2000",
        "--print", "%(id)s\t%(title)s\t%(duration)s\t%(upload_date)s",
        "--ignore-errors",
        url,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900,
                           encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return {"status": "retryable", "error": "timeout"}

    if r.returncode != 0 and not r.stdout.strip():
        err = (r.stderr or "")[-200:]
        return {"status": "retryable", "error": err}

    cur = conn.cursor()
    items_seen = set()
    new_count = 0
    total_dur = 0
    oldest = newest = None

    for line in r.stdout.strip().split("\n"):
        parts = line.strip().split("\t")
        if len(parts) < 4:
            continue
        vid, title, dur_s, upload_date = parts[0], parts[1], parts[2], parts[3]
        if not vid or vid in items_seen:
            continue
        items_seen.add(vid)

        try:
            dur = int(float(dur_s)) if dur_s and dur_s != "NA" else 0
        except:
            dur = 0

        published = parse_yt_date(upload_date)
        if not published:
            continue
        rdate = report_date_from_published(published)

        item_id = f"youtube:{vid}"
        cur.execute(
            """INSERT OR IGNORE INTO items
            (item_id,platform,platform_id,source_id,category,title,url,
             published_at,report_date,duration_seconds,language)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (item_id, "youtube", vid, sid, source["category"], title,
             f"https://www.youtube.com/watch?v={vid}",
             published, rdate, dur, "en"),
        )
        if cur.rowcount > 0:
            new_count += 1

        total_dur += dur
        if upload_date and upload_date != "NA":
            if not oldest or upload_date < oldest:
                oldest = upload_date
            if not newest or upload_date > newest:
                newest = upload_date

    cur.execute("SELECT COUNT(*), COALESCE(SUM(duration_seconds),0) FROM items WHERE source_id=?", (sid,))
    total, sum_dur = cur.fetchone()
    cur.execute(
        """UPDATE sources SET status=?,items_in_range=?,pages_fetched=?,
           oldest_seen=?,newest_seen=?,updated_at=datetime('now')
           WHERE source_id=?""",
        ("complete", total, 1, oldest, newest, sid),
    )
    conn.commit()
    print(f"    items={total} duration={sum_dur//3600}h range={oldest}~{newest}")
    return {"status": "complete", "items": total, "duration": sum_dur,
            "oldest": oldest, "newest": newest}


def inventory_xiaoyuzhou_simple(source, conn):
    """Web __NEXT_DATA__ inventory."""
    sid = source["source_id"]
    url = source["source_url"]

    print(f"  [{sid}] {source['name']}")
    pid_match = re.search(r"/podcast/([a-f0-9]+)", url)
    if not pid_match:
        return {"status": "terminal", "error": "no podcast id"}

    import requests as req
    try:
        resp = req.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        html = resp.content.decode("utf-8", errors="replace")
        m = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        if not m:
            return {"status": "retryable", "error": "no NEXT_DATA"}
        data = json.loads(m.group(1))
        podcast = data.get("props", {}).get("pageProps", {}).get("podcast") or {}
        episodes = podcast.get("episodes") or []
    except Exception as e:
        return {"status": "retryable", "error": str(e)[:200]}

    cur = conn.cursor()
    items_seen = set()
    new_count = 0
    total_dur = 0
    oldest = newest = None

    for ep in episodes:
        eid = ep.get("eid", "")
        if not eid or eid in items_seen:
            continue
        items_seen.add(eid)

        title = ep.get("title", "")
        pub_ts = ep.get("pubDate")
        dur = ep.get("duration", 0)
        if isinstance(dur, str):
            try:
                dur = int(float(dur))
            except:
                dur = 0

        if isinstance(pub_ts, (int, float)):
            published = datetime.fromtimestamp(pub_ts, timezone.utc).isoformat()
            yyyymmdd = datetime.fromtimestamp(pub_ts, TZ_SHANGHAI).strftime("%Y%m%d")
        elif isinstance(pub_ts, str):
            try:
                dt = datetime.fromisoformat(pub_ts.replace("Z", "+00:00"))
                published = dt.isoformat()
                yyyymmdd = dt.astimezone(TZ_SHANGHAI).strftime("%Y%m%d")
            except:
                published = pub_ts
                yyyymmdd = ""
        else:
            continue

        rdate = report_date_from_published(published)
        item_id = f"xiaoyuzhou:{eid}"
        episode_url = f"https://www.xiaoyuzhoufm.com/episode/{eid}"

        cur.execute(
            """INSERT OR IGNORE INTO items
            (item_id,platform,platform_id,source_id,category,title,url,
             published_at,report_date,duration_seconds,language)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (item_id, "xiaoyuzhou", eid, sid, source["category"], title,
             episode_url, published, rdate, dur, "zh"),
        )
        if cur.rowcount > 0:
            new_count += 1
        total_dur += dur

        if yyyymmdd:
            if not oldest or yyyymmdd < oldest:
                oldest = yyyymmdd
            if not newest or yyyymmdd > newest:
                newest = yyyymmdd

    cur.execute("SELECT COUNT(*), COALESCE(SUM(duration_seconds),0) FROM items WHERE source_id=?", (sid,))
    total, sum_dur = cur.fetchone()
    cur.execute(
        """UPDATE sources SET status=?,items_in_range=?,pages_fetched=?,
           oldest_seen=?,newest_seen=?,updated_at=datetime('now')
           WHERE source_id=?""",
        ("complete", total, 1, oldest, newest, sid),
    )
    conn.commit()
    print(f"    items={total} duration={sum_dur//3600}h range={oldest}~{newest}")
    return {"status": "complete", "items": total, "duration": sum_dur,
            "oldest": oldest, "newest": newest}


def generate_audit_report(conn):
    """Generate audit summary."""
    cur = conn.cursor()

    # Source audit
    cur.execute(
        """SELECT s.source_id, s.name, s.platform, s.status, s.items_in_range,
           s.oldest_seen, s.newest_seen, s.error_message
           FROM sources s ORDER BY s.platform, s.category, s.source_id"""
    )
    sources = [dict(r) for r in cur.fetchall()]

    # Totals
    cur.execute("SELECT COUNT(*), COALESCE(SUM(duration_seconds),0) FROM items")
    total_items, total_dur = cur.fetchone()

    cur.execute("SELECT COUNT(*), COALESCE(SUM(duration_seconds),0) FROM items WHERE platform='youtube'")
    yt_items, yt_dur = cur.fetchone()
    cur.execute("SELECT COUNT(*), COALESCE(SUM(duration_seconds),0) FROM items WHERE platform='xiaoyuzhou'")
    xyz_items, xyz_dur = cur.fetchone()

    # Monthly breakdown
    cur.execute(
        "SELECT substr(report_date,1,7) as month, COUNT(*), COALESCE(SUM(duration_seconds),0) FROM items WHERE report_date != '' GROUP BY month ORDER BY month"
    )
    monthly = [(r[0], r[1], r[2]) for r in cur.fetchall()]

    # Unique days covered
    cur.execute("SELECT COUNT(DISTINCT report_date) FROM items WHERE report_date != ''")
    days_covered = cur.fetchone()[0]

    # Per-category
    cur.execute(
        "SELECT category, COUNT(*), COALESCE(SUM(duration_seconds),0) FROM items GROUP BY category ORDER BY category"
    )
    by_category = [(r[0], r[1], r[2]) for r in cur.fetchall()]

    # ASR estimate: all xiaoyuzhou + YouTube without captions
    cur.execute("SELECT COUNT(*) FROM items WHERE platform='xiaoyuzhou'")
    xyz_asr = cur.fetchone()[0]
    # YouTube: estimate ~60% have auto-captions, so ~40% need ASR based on unknown status
    yt_estimated_asr = int(yt_items * 0.6)

    report = {
        "generated_at": datetime.now().isoformat(),
        "total_items": total_items,
        "total_duration_seconds": total_dur,
        "total_duration_hours": round(total_dur / 3600, 1) if total_dur else 0,
        "youtube_items": yt_items,
        "youtube_duration_hours": round(yt_dur / 3600, 1) if yt_dur else 0,
        "xiaoyuzhou_items": xyz_items,
        "xiaoyuzhou_duration_hours": round(xyz_dur / 3600, 1) if xyz_dur else 0,
        "days_covered": days_covered,
        "estimated_asr_count": xyz_asr + yt_estimated_asr,
        "sources": [],
        "monthly_breakdown": [{"month": m, "count": c, "duration_hours": round(d/3600,1)} for m,c,d in monthly],
        "by_category": [{"category": c, "count": n, "duration_hours": round(d/3600,1)} for c,n,d in by_category],
    }

    for src in sources:
        report["sources"].append({
            "source_id": src["source_id"],
            "name": src["name"],
            "platform": src["platform"],
            "status": src["status"],
            "items": src["items_in_range"],
            "oldest": src["oldest_seen"],
            "newest": src["newest_seen"],
            "error": src["error_message"],
        })

    return report


def main():
    print("=" * 60)
    print("  Phase C: 41-Source Full Inventory")
    print("=" * 60)

    init_db()
    conn = get_conn()
    cur = conn.cursor()

    # Clean start
    for t in ["failures", "extractions", "items", "sources", "daily_views", "run_log"]:
        cur.execute(f"DELETE FROM {t}")
    conn.commit()

    sources = [s for s in load_sources() if s.get("enabled", True)]
    yt_sources = [s for s in sources if s["platform"] == "youtube"]
    xyz_sources = [s for s in sources if s["platform"] == "xiaoyuzhou"]

    print(f"\nSources: {len(yt_sources)} YouTube + {len(xyz_sources)} Xiaoyuzhou = {len(sources)} total\n")

    results = {}
    start_time = datetime.now()

    # YouTube first (most data)
    print("--- YouTube Inventory ---")
    for i, src in enumerate(yt_sources):
        sid = src["source_id"]
        # Check if already done
        cur.execute("SELECT status FROM sources WHERE source_id=? AND status='complete'", (sid,))
        if cur.fetchone():
            print(f"  [{i+1}/{len(yt_sources)}] {sid}: already complete, skip")
            continue
        try:
            r = inventory_youtube_simple(src, conn)
            results[sid] = r
            print(f"  [{i+1}/{len(yt_sources)}] {sid}: {r['status']} ({r.get('items',0)} items)")
        except Exception as e:
            results[sid] = {"status": "error", "error": str(e)[:200]}
            print(f"  [{i+1}/{len(yt_sources)}] {sid}: ERROR {e}")
        # Rate limit delay
        time.sleep(1)

    # Xiaoyuzhou
    print("\n--- Xiaoyuzhou Inventory ---")
    for i, src in enumerate(xyz_sources):
        sid = src["source_id"]
        cur.execute("SELECT status FROM sources WHERE source_id=? AND status='complete'", (sid,))
        if cur.fetchone():
            print(f"  [{i+1}/{len(xyz_sources)}] {sid}: already complete, skip")
            continue
        try:
            r = inventory_xiaoyuzhou_simple(src, conn)
            results[sid] = r
            print(f"  [{i+1}/{len(xyz_sources)}] {sid}: {r['status']} ({r.get('items',0)} items)")
        except Exception as e:
            results[sid] = {"status": "error", "error": str(e)[:200]}
            print(f"  [{i+1}/{len(xyz_sources)}] {sid}: ERROR {e}")

    elapsed = (datetime.now() - start_time).total_seconds()

    # Generate audit
    print("\n" + "=" * 60)
    print("  Generating Audit Report...")
    report = generate_audit_report(conn)

    # Save report
    audit_path = ROOT / "backfill" / "catalog" / "source_audit.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Print summary
    statuses = defaultdict(int)
    for r in results.values():
        statuses[r.get("status", "unknown")] += 1

    complete_sources = statuses.get("complete", 0)

    print(f"\n  Elapsed: {elapsed:.0f}s ({elapsed/60:.1f}m)")
    print(f"  Sources: {complete_sources}/{len(sources)} complete")
    print(f"  Status breakdown: {dict(statuses)}")
    print(f"  Total items: {report['total_items']}")
    print(f"  Total duration: {report['total_duration_hours']} hours")
    print(f"  YouTube: {report['youtube_items']} items, {report['youtube_duration_hours']}h")
    print(f"  Xiaoyuzhou: {report['xiaoyuzhou_items']} items, {report['xiaoyuzhou_duration_hours']}h")
    print(f"  Days covered: {report['days_covered']}")
    print(f"  Estimated ASR needed: {report['estimated_asr_count']} episodes")
    print(f"  Monthly breakdown: {len(report['monthly_breakdown'])} months")

    # Per-category
    print(f"\n  By Category:")
    for c in report["by_category"]:
        print(f"    {c['category']}: {c['count']} items, {c['duration_hours']}h")

    # Per-source status
    incomplete = [s for s in sources if s["source_id"] not in results or results.get(s["source_id"], {}).get("status") != "complete"]
    if incomplete:
        print(f"\n  Incomplete sources ({len(incomplete)}):")
        for s in incomplete:
            r = results.get(s["source_id"], {})
            print(f"    {s['source_id']}: {r.get('status','unknown')} - {r.get('error','')}")

    print(f"\n  Audit saved: {audit_path}")
    print(f"\n  [{'PASS' if complete_sources == len(sources) else 'PARTIAL'}] {complete_sources}/{len(sources)} sources complete")
    print("=" * 60)

    conn.close()
    return 0 if complete_sources == len(sources) else 1


if __name__ == "__main__":
    sys.exit(main())
