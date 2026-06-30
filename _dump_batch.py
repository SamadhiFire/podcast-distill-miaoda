"""Dump metadata+transcript first 2000 chars for items N to M (1-indexed in pending_july.txt)"""
import sys, os
import json

idx_start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
idx_end = int(sys.argv[2]) if len(sys.argv) > 2 else idx_start + 1

with open('pending_july.txt','r',encoding='utf-8') as f:
    pending = [l.strip() for l in f if l.strip()]

for i in range(idx_start, min(idx_end, len(pending))):
    vid = pending[i]
    req_path = f'backfill/summary_jobs/youtube/{vid}/request.json'
    if not os.path.exists(req_path):
        print(f'\n### {i+1}. {vid} | NO REQUEST\n')
        continue
    with open(req_path,'r',encoding='utf-8') as f:
        r = json.load(f)
    item = r['item']
    t = r['transcript']
    print(f'\n### {i+1}. {vid} | dur={item.get("duration_seconds",0)}s | {t.get("text_chars",0)}c')
    print(f'Title: {item.get("title","")[:90]}')
    print(f'Source: {item.get("source_name","")} | {item.get("upload_date","")}')
    print(f'SHA: {t.get("sha256","")} | chars: {t.get("text_chars",0)}')
    # dump first 2000 chars of transcript
    tp = f'backfill/items/youtube/{vid}/transcript.txt'
    if os.path.exists(tp):
        with open(tp,'r',encoding='utf-8') as f:
            content = f.read()[:1800]
        # safe print
        try:
            print('--- T1 ---')
            print(content)
            print('--- /T1 ---')
        except UnicodeEncodeError:
            print('--- T1 (partial, contains unicode) ---')
            print(content[:1500])
            print('--- /T1 ---')
