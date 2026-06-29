"""Quick YouTube batch inventory."""
import sys; sys.path.insert(0, ".")
from scripts.backfill.run_phase_c import inventory_youtube_simple, load_sources
from scripts.backfill.db import get_conn, init_db

init_db()
c = get_conn()
for t in ["failures", "extractions", "items", "sources", "daily_views", "run_log"]:
    c.execute(f"DELETE FROM {t}")
c.commit()

srcs = [s for s in load_sources() if s["enabled"] and s["platform"] == "youtube"]
srcs = srcs[:3]  # START: first 3 only
print(f"YouTube: {len(srcs)} sources (test batch)")
for i, s in enumerate(srcs):
    try:
        r = inventory_youtube_simple(s, c)
        print(f"[{i+1}/{len(srcs)}] {s['source_id']}: {r['status']} items={r.get('items',0)} dur={r.get('duration',0)//3600}h")
    except Exception as e:
        print(f"[{i+1}/{len(srcs)}] {s['source_id']}: ERROR {e}")

cur = c.cursor()
cur.execute("SELECT COUNT(*), COALESCE(SUM(duration_seconds),0) FROM items WHERE platform='youtube'")
items, dur = cur.fetchone()
print(f"\nTotal YouTube: {items} items, {round(dur/3600,1)}h")
c.close()
