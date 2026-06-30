#!/usr/bin/env python3
"""Check completion status for YouTube 2026-05 summary generation."""
import json
import os
import sys

ROOT = r'd:\Users\AS\Desktop\podcast-distill\backfill'
SJ = os.path.join(ROOT, 'summary_jobs', 'youtube')
ITEMS = os.path.join(ROOT, 'items', 'youtube')

may_vids = []
total_dirs = 0
errors = 0

for vid in sorted(os.listdir(SJ)):
    total_dirs += 1
    rq_path = os.path.join(SJ, vid, 'request.json')
    if not os.path.isfile(rq_path):
        continue
    try:
        with open(rq_path, 'r', encoding='utf-8') as f:
            rq = json.load(f)
        # report_date is inside rq['item']['report_date']
        item = rq.get('item', {})
        rd = item.get('report_date', '')
        if rd.startswith('2026-05'):
            has_summary = os.path.isfile(os.path.join(ITEMS, vid, 'summary.json'))
            may_vids.append((vid, rd, has_summary))
    except Exception as e:
        errors += 1
        if errors <= 3:
            print(f'  Error reading {vid}: {e}', file=sys.stderr)

done = [v for v in may_vids if v[2]]
todo = [v for v in may_vids if not v[2]]

print(f'Total directories in summary_jobs/youtube: {total_dirs}')
print(f'2026-05 entries found: {len(may_vids)}')
print(f'Already completed (summary.json exists): {len(done)}')
print(f'Remaining to process: {len(todo)}')
print(f'Errors during scan: {errors}')
print()

if done:
    print(f'=== COMPLETED ({len(done)}) ===')
    for vid, rd, _ in done[:10]:
        print(f'  {vid}  {rd}')
    if len(done) > 10:
        print(f'  ... and {len(done)-10} more')

if todo:
    print(f'\n=== TODO ({len(todo)}) ===')
    for vid, rd, _ in todo[:20]:
        print(f'  {vid}  {rd}')
    if len(todo) > 20:
        print(f'  ... and {len(todo)-20} more')
