import json, re, sys

path = 'd:/Users/AS/Desktop/podcast-distill/backfill/items/youtube/iRhAEqPfqO4/summary.json'
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)
d = data['digest']
errors = []

def check(cond, msg):
    if not cond:
        errors.append(msg)
        print('FAIL:', msg)

def has_cjk(s):
    return bool(re.search(r'[\u4e00-\u9fff]', s))

st = d['short_title']
print(f'short_title: {len(st)} chars (max 18)')
check(len(st) <= 18, f'short_title too long: {len(st)}')
check(has_cjk(st), 'short_title no CJK')

ol = d['one_liner']
print(f'one_liner: {len(ol)} chars (max 30)')
check(len(ol) <= 30, f'one_liner too long: {len(ol)}')
check(has_cjk(ol), 'one_liner no CJK')

wm = d['why_it_matters']
print(f'why_it_matters: {len(wm)} chars (max 60)')
check(len(wm) <= 60, f'why_it_matters too long: {len(wm)}')
check(has_cjk(wm), 'why_it_matters no CJK')

print(f'summary: {len(d["summary"])} paragraphs')
check(2 <= len(d['summary']) <= 6, 'summary count wrong')
for i, p in enumerate(d['summary']):
    print(f'  para {i}: {len(p)} chars')
    check(len(p) <= 150, f'summary[{i}] too long: {len(p)}')
    check(has_cjk(p), f'summary[{i}] no CJK')

print(f'core_points: {len(d["core_points"])} items')
check(3 <= len(d['core_points']) <= 7, 'core_points count wrong')
for i, cp in enumerate(d['core_points']):
    print(f'  cp {i}: {len(cp)} chars')
    check(len(cp) <= 90, f'core_points[{i}] too long: {len(cp)}')
    check(has_cjk(cp), f'core_points[{i}] no CJK')

print(f'key_facts: {len(d["key_facts"])} items')
check(len(d['key_facts']) <= 8, 'key_facts too many')
for i, kf in enumerate(d['key_facts']):
    for k in ['label', 'value', 'context', 'source_refs']:
        check(k in kf, f'key_facts[{i}] missing {k}')
    check(kf.get('source_refs') == ['youtube:iRhAEqPfqO4'], f'key_facts[{i}] wrong source_refs')

print(f'takeaways: {len(d["takeaways"])} items')
check(1 <= len(d['takeaways']) <= 2, 'takeaways count wrong')
for i, t in enumerate(d['takeaways']):
    print(f'  ta {i}: {len(t)} chars')
    check(len(t) <= 70, f'takeaways[{i}] too long: {len(t)}')
    check('?' not in t, f'takeaways[{i}] has ?')
    check('\uff1f' not in t, f'takeaways[{i}] has fullwidth ?')
    check(has_cjk(t), f'takeaways[{i}] no CJK')

print(f'guests: {len(d["guests"])} items')
check(len(d['guests']) <= 5, 'guests too many')
for g in d['guests']:
    check(len(g) <= 90, f'guest too long: {len(g)}')

print(f'topics: {len(d["topics"])} items')
check(len(d['topics']) <= 3, 'topics too many')
for t in d['topics']:
    print(f'  topic: {t} ({len(t)} chars)')
    check(len(t) <= 12, f'topic too long: {len(t)}')
    check(has_cjk(t), f'topic no CJK')

print(f'tensions: {len(d["tensions"])} items')
check(len(d['tensions']) <= 3, 'tensions too many')
for i, t in enumerate(d['tensions']):
    print(f'  tension {i}: {len(t)} chars')
    check(len(t) <= 90, f'tensions[{i}] too long')
    check(has_cjk(t), f'tensions[{i}] no CJK')

q = d['quote']
print(f'quote text: {len(q["text"])} chars (max 46)')
check(len(q['text']) <= 46, f'quote text too long: {len(q["text"])}')
check(q['kind'] in ('verbatim', 'paraphrase'), 'quote kind invalid')

check(isinstance(d['importance_score'], int) and 1 <= d['importance_score'] <= 5, 'importance_score invalid')
check(d['content_density'] == 'standard', 'content_density invalid')
check(d['quality'] == 'trae_agent_validated', 'quality invalid')

if errors:
    print(f'\n=== {len(errors)} ERRORS ===')
    for e in errors:
        print(' -', e)
    sys.exit(1)
else:
    print('\n=== ALL VALIDATIONS PASSED ===')
