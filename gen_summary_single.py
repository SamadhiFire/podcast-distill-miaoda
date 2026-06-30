#!/usr/bin/env python3
"""Generate summary.json for a single YouTube item. Called by the workflow orchestrator."""

import json
import os
import sys

def main():
    video_id = sys.argv[1]
    base_jobs = 'd:/Users/AS/Desktop/podcast-distill/backfill/summary_jobs/youtube'
    base_items = 'd:/Users/AS/Desktop/podcast-distill/backfill/items/youtube'

    # Read request.json
    req_path = os.path.join(base_jobs, video_id, 'request.json')
    req = json.load(open(req_path, encoding='utf-8'))
    item = req['item']
    transcript_info = req['transcript']

    print(f"Processing: {video_id}")
    print(f"  Title: {item['title']}")
    print(f"  Source: {item['source_name']}")
    print(f"  Duration: {item['duration_seconds']}s")
    print(f"  Date: {item['report_date']}")

    # Check if already done
    summary_path = os.path.join(base_items, video_id, 'summary.json')
    if os.path.exists(summary_path):
        print(f"  SKIP: summary.json already exists")
        return

    # Read transcript
    transcript_path = os.path.join(base_items, video_id, 'transcript.txt')
    try:
        transcript = open(transcript_path, encoding='utf-8').read()
    except FileNotFoundError:
        print(f"  ERROR: transcript.txt not found")
        return

    print(f"  Transcript: {len(transcript)} chars")
    print(f"  Need to generate summary via agent")

if __name__ == '__main__':
    main()
