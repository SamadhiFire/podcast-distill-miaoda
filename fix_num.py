"""
Auto-fix key_facts numbers to match transcript verbatim.
Removes or replaces any digit sequences in key_facts value/context 
that don't appear literally in the transcript.
"""
import json, re, os, sys

NUMBER_RE = re.compile(r'\d[\d,.]*(?:%|亿|万|千|百)?')

def find_digits(text):
    """Return set of digit sequences found in text."""
    return set(NUMBER_RE.findall(text or ''))

def fix_video(items_dir, vid):
    spath = os.path.join(items_dir, vid, 'summary.json')
    tpath = os.path.join(items_dir, vid, 'transcript.txt')
    
    if not os.path.exists(spath):
        print(f'{vid}: SKIP (no summary)')
        return False
    if not os.path.exists(tpath):
        print(f'{vid}: SKIP (no transcript)')
        return False
    
    with open(tpath, 'r', encoding='utf-8', errors='replace') as f:
        transcript = f.read()
    
    with open(spath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    facts = data['digest']['key_facts']
    changed = False
    
    for fact in facts:
        for field in ['value', 'context']:
            text = str(fact.get(field, ''))
            digits = find_digits(text)
            for d in sorted(digits, key=len, reverse=True):
                if d not in transcript:
                    # Replace with English word form or remove
                    fact[field] = fact[field].replace(d, '')
                    changed = True
        # Clean up whitespace/punctuation
        for field in ['value', 'context']:
            fact[field] = re.sub(r'\s{2,}', ' ', fact.get(field, ''))
            fact[field] = fact[field].strip(' ,;，；.')
            if not fact[field]:
                fact[field] = '(见字幕)'
    
    if changed:
        with open(spath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n')
        return True
    return False


if __name__ == '__main__':
    items_dir = sys.argv[1] if len(sys.argv) > 1 else 'backfill/items/youtube'
    vids = sys.argv[2:] if len(sys.argv) > 2 else []
    
    if not vids:
        print('Usage: python fix_num.py [items_dir] <vid1> <vid2> ...')
        sys.exit(1)
    
    for vid in vids:
        if fix_video(items_dir, vid):
            print(f'{vid}: FIXED')
        else:
            print(f'{vid}: already clean')
