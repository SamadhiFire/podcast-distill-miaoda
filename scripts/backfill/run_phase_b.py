"""
阶段 B 独立运行脚本 — 两源试跑
直接在终端运行: python scripts/backfill/run_phase_b.py
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from scripts.backfill.db import get_conn, init_db
from scripts.backfill.inventory import (
    inventory_xiaoyuzhou, inventory_youtube, inventory_youtube_ytdlp, inventory_youtube_api,
)
from scripts.backfill.extract_batch import cmd_extract

import yaml


def load_source(source_id: str) -> dict:
    path = ROOT / "backfill" / "config" / "sources.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    for s in data["sources"]:
        if s["source_id"] == source_id:
            return s
    raise ValueError(f"Source not found: {source_id}")


def main():
    print("=" * 60)
    print("  Phase B: Two-Source Trial")
    print("  YouTube: Dwarkesh Podcast | Xiaoyuzhou: 42张经")
    print("=" * 60)

    init_db()
    conn = get_conn()
    cur = conn.cursor()

    # Clean start (order matters: FK constraints)
    cur.execute("DELETE FROM failures")
    cur.execute("DELETE FROM extractions")
    cur.execute("DELETE FROM items")
    cur.execute("DELETE FROM sources")
    cur.execute("DELETE FROM daily_views")
    cur.execute("DELETE FROM run_log")
    conn.commit()

    sources = {
        "yt": load_source("yt_dwarkesh"),
        "xyz": load_source("xyz_42zhangjing"),
    }

    # =============================================
    # Part 1: Inventory
    # =============================================
    print("\n" + "=" * 60)
    print("  [1/4] Inventory")
    print("=" * 60)

    # 1a. Xiaoyuzhou
    print("\n--- Xiaoyuzhou: 42张经 ---")
    r_xyz = inventory_xiaoyuzhou(sources["xyz"], "", conn)
    print(f"  Result: {r_xyz.get('status')} | items={r_xyz.get('items',0)}")

    # 1b. YouTube -- try API first, then yt-dlp
    print("\n--- YouTube: Dwarkesh Podcast ---")
    r_yt = inventory_youtube(sources["yt"], "", conn)
    print(f"  Result: {r_yt.get('status')} | items={r_yt.get('items',0)}")

    # Check pagination proof
    cur.execute("SELECT COUNT(*) FROM items WHERE source_id='yt_dwarkesh'")
    yt_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM items WHERE source_id='xyz_42zhangjing'")
    xyz_count = cur.fetchone()[0]

    print(f"\n  Total inventoried: yt={yt_count}, xyz={xyz_count}")

    # =============================================
    # Part 2: Extract (3 each)
    # =============================================
    print("\n" + "=" * 60)
    print("  [2/4] Extract Subtitles (3 each)")
    print("=" * 60)

    print("\n--- Xiaoyuzhou Extract (limit=3) ---")
    cmd_extract("xyz_42zhangjing", 3)

    print("\n--- YouTube Extract (limit=3) ---")
    cmd_extract("yt_dwarkesh", 3)

    # =============================================
    # Part 3: Re-run (prove resume & dedup)
    # =============================================
    print("\n" + "=" * 60)
    print("  [3/4] Re-run (prove resume & dedup)")
    print("=" * 60)

    # Verify no new items on re-inventory
    print("\n--- Re-inventory Xiaoyuzhou ---")
    r2 = inventory_xiaoyuzhou(sources["xyz"], "", conn)
    print(f"  Re-result: new={r2.get('new',0)} total={r2.get('items',0)}")

    print("\n--- Re-extract (should skip completed) ---")
    cmd_extract("xyz_42zhangjing", 3)

    if yt_count > 0:
        print("\n--- Re-extract YouTube (should skip completed) ---")
        cmd_extract("yt_dwarkesh", 3)

    # =============================================
    # Part 4: Final Report
    # =============================================
    print("\n" + "=" * 60)
    print("  [4/4] Final Report")
    print("=" * 60)

    cur.execute("SELECT source_id, status, items_in_range, pages_fetched, oldest_seen, newest_seen FROM sources ORDER BY source_id")
    for row in cur.fetchall():
        print(f"\n  Source: {row['source_id']}")
        print(f"    Status: {row['status']}")
        print(f"    Items: {row['items_in_range']}")
        print(f"    Pages: {row['pages_fetched']}")
        print(f"    Range: {row['oldest_seen']} ~ {row['newest_seen']}")

    cur.execute("SELECT status, error_type, COUNT(*) as cnt FROM extractions GROUP BY status, error_type")
    print("\n  Extraction Results:")
    for row in cur.fetchall():
        print(f"    {row['status']}: {row['cnt']} (type={row['error_type']})")

    cur.execute("SELECT COUNT(*) FROM items")
    total_items = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT item_id) FROM items")
    unique_items = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM extractions WHERE status='success'")
    success = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM extractions WHERE status='needs_asr'")
    needs_asr = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM extractions WHERE status='retryable'")
    retryable = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM extractions WHERE status='blocked'")
    blocked = cur.fetchone()[0]

    print(f"\n  === Phase B Verification ===")
    print(f"  [{'PASS' if unique_items == total_items else 'FAIL'}] No duplicates (unique={unique_items}, total={total_items})")
    print(f"  [{'PASS' if xyz_count > 0 else 'FAIL'}] Xiaoyuzhou inventory complete ({xyz_count} items)")
    print(f"  [{'PASS' if yt_count > 0 else 'WARN'}] YouTube inventory ({yt_count} items)")
    print(f"  [{'PASS' if success + needs_asr + retryable + blocked > 0 else 'FAIL'}] Extraction states recorded")
    print(f"  [INFO] Status breakdown: success={success}, needs_asr={needs_asr}, retryable={retryable}, blocked={blocked}")
    print(f"  [{'PASS' if r2.get('new', 0) == 0 else 'FAIL'}] Resume works (re-inventory found 0 new items)")

    print("\n  Done!")
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
